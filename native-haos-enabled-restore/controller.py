"""Native KVM HAOS enabled-entry partial restore and guard rollback diagnostic.

Only one newly created, synthetic and network-closed owned guest is controlled.
Operational continuity and automatic recovery-guard rollback safety are separate.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import zipfile


HAOS_URL = "https://github.com/home-assistant/operating-system/releases/download/18.3/haos_ova-18.3.qcow2.xz"
HAOS_XZ_SHA = "fae6a728768cc10aff60d4820bfcd40d64cd77fab82c8bd92af13b3d9d414090"
CANDIDATE_SHA = "fc0b365d9688459504f874af5c38393e24145d657f15f1def8ada9184f363285"
BRANCH = "codex/native-amd64-validation"
CORE = "2026.10.2"
HA = "/usr/bin/docker exec hassio_cli ha"
GUEST_ROOT = "/mnt/data/homecircle-enabled-restore-qa"
CONTROL = "homecircle-enabled-restore-qa-control"
RESULTS = "homecircle-enabled-restore-qa-results"
PHASES = ("initialize", "prebackup", "mutate", "restored", "repair", "restart")
CORE_MANAGEMENT_JOBS = frozenset({
    "home_assistant_core_install_landing_page", "home_assistant_core_install",
    "home_assistant_core_start", "home_assistant_core_update", "home_assistant_core_stop",
    "home_assistant_core_restart", "home_assistant_core_rebuild",
})
ROOT = Path(__file__).resolve().parent
BACKUP_ERROR_TYPES = frozenset({
    "BackupError", "HomeAssistantBackupError", "BackupJobError", "BackupInvalidError", "BackupPermissionError",
    "BackupFileExistError", "BackupFatalIOError", "BackupDataDiskBadMessageError", "BackupFileNotFoundError",
    "BackupSupervisorVersionError", "BackupSupervisorUpdateInProgressError", "BackupMountDownError",
    "JobConditionException", "JobGroupExecutionLimitExceeded", "HomeAssistantWSError", "ConfigurationFileError",
})
# Fixed literals reviewed in Supervisor 2026.10.2, CLI bf6d59ff,
# Cobra 1.10.2 and pflag 1.0.10. No message fragment or value is copied.
BACKUP_MESSAGE_CATEGORIES = (
    ("Preparing backup of Home Assistant Core failed. Failed to inform HA Core:", "core_backup_start_transport"),
    ("Preparing backup of Home Assistant Core failed due to:", "core_backup_start_rejected"),
    ("Error during pre-backup:", "core_pre_backup_hook_failed"),
    ("Home Assistant is not running", "recorder_core_not_running"),
    ("Database migration in progress", "recorder_database_migrating"),
    ("Could not lock database within ", "recorder_lock_timeout"),
    ("Could not release database write lock", "recorder_unlock_failed"),
    ("Can't backup Home Assistant Core config folder:", "core_config_archive_failed"),
    ("Can't save meta for Home Assistant Core:", "core_metadata_write_failed"),
    ("Can't write tarfile:", "backup_tar_write_failed"),
    ("unexpected non-JSON response", "cli_http_non_json"),
    ("unexpected server response", "cli_http_unexpected_status"),
    ("unauthorized:", "cli_http_unauthorized"),
    ("forbidden:", "cli_http_forbidden"),
    ("bad gateway:", "cli_http_bad_gateway"),
    ("unknown error occurred", "cli_http_internal_error"),
    ("unknown command", "cli_unexpected_positional_or_command"),
    ("unknown flag:", "cli_unknown_flag"),
    ("flag needs an argument:", "cli_flag_value_missing"),
    ("bad flag syntax:", "cli_flag_syntax"),
    ("not enough free space", "supervisor_free_space"),
    ("system is not healthy", "supervisor_unhealthy"),
    ("system is not running", "supervisor_not_running"),
    ("system is not frozen", "supervisor_not_frozen"),
    ("no supervisor internet connection", "supervisor_internet_unavailable"),
    ("no host internet connection", "host_internet_unavailable"),
)
BACKUP_DIAGNOSTIC_JOBS = CORE_MANAGEMENT_JOBS | {
    "backup_manager_partial_backup", "backup_manager_partial_restore", "backup_store_homeassistant",
    "backup_restore_homeassistant", "home_assistant_module_backup", "home_assistant_module_restore",
    "home_assistant_module_begin_backup", "home_assistant_module_end_backup", "backup_store_supervisor_config",
    "backup_restore_supervisor_config", "backup_copy_to_additional_locations", "backup_copy_to_location",
    "backup_store_folders", "backup_restore_folders", "backup_store_apps", "backup_restore_apps",
}


class Refused(RuntimeError):
    """A fixed controller failure with no command, response or secret text."""


def require(condition, reason):
    if not condition:
        raise Refused(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


def public_core_version(value):
    """Only a Core version or the known initial landing-page marker is public."""
    if isinstance(value, str) and (value == "landingpage" or re.fullmatch(
            r"[0-9]{4}\.[0-9]{1,2}\.[0-9]{1,2}(?:[a-z0-9.+-]{0,24})", value)):
        return value
    return None


def public_http_probe(value):
    """Keep only finite static-file diagnostics, never response text or URLs."""
    if not isinstance(value, dict):
        return {}
    projected = {}
    for key, lower, upper in (("active_port", 1, 65535), ("status", 100, 599),
                              ("response_bytes", 0, 32 * 1024**2), ("expected_bytes", 0, 32 * 1024**2)):
        number = value.get(key)
        if type(number) is int and lower <= number <= upper:
            projected[key] = number
    for key in ("tls", "body_matches"):
        if type(value.get(key)) is bool:
            projected[key] = value[key]
    for key in ("response_sha256", "expected_sha256"):
        fingerprint = value.get(key)
        if isinstance(fingerprint, str) and re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            projected[key] = fingerprint
    category = value.get("location_category")
    if isinstance(category, str) and category in {"absent", "legacy_port_transition", "onboarding", "other"}:
        projected["location_category"] = category
    return projected


def public_supervisor_state(value):
    data = value.get("data", {}) if isinstance(value, dict) else {}
    if not isinstance(data, dict):
        data = {}
    result = value.get("result") if isinstance(value, dict) else None
    state = data.get("state")
    allowed = {"initialize", "setup", "startup", "running", "freeze", "shutdown", "stopped", "close"}
    return {"result": result if isinstance(result, str) and result in {"ok", "error"} else "unavailable",
            "healthy": data.get("healthy") if isinstance(data.get("healthy"), bool) else None,
            "supported": data.get("supported") if isinstance(data.get("supported"), bool) else None,
            "state": state if isinstance(state, str) and state in allowed else None}


def public_root_state(value):
    result = public_supervisor_state(value)
    data = value.get("data", {}) if isinstance(value, dict) else {}
    result["supervisor_version"] = public_core_version(data.get("supervisor")) if isinstance(data, dict) else None
    return {key: result[key] for key in ("result", "state", "supported", "supervisor_version")}


def public_jobs(value):
    require(isinstance(value, dict) and value.get("result") == "ok", "jobs_projection_refused")
    jobs = value.get("data", {}).get("jobs")
    require(isinstance(jobs, list), "jobs_projection_refused")
    pending = list(jobs)
    projected = []
    while pending:
        require(len(projected) + len(pending) <= 256, "jobs_projection_refused")
        item = pending.pop(0)
        require(isinstance(item, dict), "jobs_projection_refused")
        name, done = item.get("name"), item.get("done")
        require(isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_]{1,80}", name)
                and (done is None or type(done) is bool), "jobs_projection_refused")
        projected.append({"name": name, "done": done})
        children = item.get("child_jobs", [])
        require(isinstance(children, list), "jobs_projection_refused")
        pending.extend(children)
    return projected


def core_jobs_idle(jobs):
    return not any(job["name"] in CORE_MANAGEMENT_JOBS and job["done"] is not True for job in jobs)


def exact_job(value, identifier, expected_name):
    """Match one returned operation ID and inspect its complete bounded subtree."""
    require(isinstance(value, dict) and value.get("result") == "ok", "backup_jobs_refused")
    roots = value.get("data", {}).get("jobs")
    require(isinstance(roots, list), "backup_jobs_refused")
    pending, matches, count, seen = list(roots), [], 0, set()
    while pending:
        item = pending.pop(0)
        count += 1
        require(count + len(pending) <= 256 and isinstance(item, dict), "backup_jobs_refused")
        uuid = item.get("uuid")
        require(isinstance(uuid, str) and re.fullmatch(r"[0-9a-f]{32}", uuid) and uuid not in seen,
                "backup_jobs_refused")
        seen.add(uuid)
        if uuid == identifier:
            matches.append(item)
        children = item.get("child_jobs", [])
        require(isinstance(children, list), "backup_jobs_refused")
        pending.extend(children)
    require(len(matches) == 1 and matches[0].get("name") == expected_name, "backup_job_identity_refused")
    pending, complete, errors, count = matches, True, 0, 0
    while pending:
        item = pending.pop(0)
        count += 1
        require(count + len(pending) <= 256 and isinstance(item, dict), "backup_jobs_refused")
        done = item.get("done")
        require(done is None or type(done) is bool, "backup_job_state_refused")
        complete = complete and done is True
        failures = item.get("errors")
        require(isinstance(failures, list), "backup_job_errors_refused")
        errors += len(failures)
        error = item.get("error")
        if error is not None and error is not False and error != "" and error != []:
            errors += 1
        children = item.get("child_jobs", [])
        require(isinstance(children, list), "backup_jobs_refused")
        pending.extend(children)
    return {"name": expected_name, "done": complete, "error_count": errors, "nodes": count}


def backup_info(value, slug):
    require(isinstance(value, dict) and value.get("result") == "ok", "backup_info_refused")
    data = value.get("data")
    require(isinstance(data, dict) and data.get("slug") == slug and data.get("type") == "partial"
            and data.get("homeassistant") == CORE and data.get("homeassistant_exclude_database") is False
            and data.get("protected") is False and data.get("compressed") is False,
            "backup_scope_refused")
    return {"type": "partial", "homeassistant_version": CORE, "database_included": True,
            "protected": False, "compressed": False}


def backup_error_categories(value):
    """Classify reviewed public source constants without exporting message text."""
    if not isinstance(value, dict):
        return {"type": "unclassified", "categories": []}
    kind = value.get("type")
    kind = kind if isinstance(kind, str) and kind in BACKUP_ERROR_TYPES else "unclassified"
    message = value.get("message")
    categories = []
    if isinstance(message, str):
        # Nested Core errors are embedded in Supervisor's fixed wrapper, so
        # classify each known literal wherever that nested wrapper places it.
        lowered = message.lower()
        categories = {category for literal, category in BACKUP_MESSAGE_CATEGORIES if literal.lower() in lowered}
        if re.search(r"accepts [0-9]+ arg\(s\), received [0-9]+", message):
            categories.add("cli_positional_count")
        categories = sorted(categories)
    return {"type": kind, "categories": categories}


def public_backup_failure_jobs(value, identifier, expected_name):
    """Return exact/recent backup job diagnostics with complete bounded trees."""
    require(isinstance(value, dict) and value.get("result") == "ok", "backup_failure_jobs_refused")
    roots = value.get("data", {}).get("jobs")
    require(isinstance(roots, list), "backup_failure_jobs_refused")
    pending, all_nodes = list(roots), []
    while pending:
        item = pending.pop(0)
        require(isinstance(item, dict) and len(all_nodes) + len(pending) < 256, "backup_failure_jobs_refused")
        all_nodes.append(item)
        children = item.get("child_jobs", [])
        require(isinstance(children, list), "backup_failure_jobs_refused")
        pending.extend(children)
    exact = [item for item in all_nodes if identifier is not None and item.get("uuid") == identifier]
    if identifier is not None:
        require(len(exact) == 1 and exact[0].get("name") == expected_name, "backup_failure_job_identity_refused")
    selected = exact if identifier is not None else [item for item in all_nodes
        if item.get("name") in {"backup_manager_partial_backup", "backup_manager_partial_restore"}][:3]
    result = []
    for root in selected:
        pending, nodes = [root], []
        while pending:
            item = pending.pop(0)
            done, failures = item.get("done"), item.get("errors")
            require((done is None or type(done) is bool) and isinstance(failures, list), "backup_failure_job_state_refused")
            errors = [backup_error_categories(error) for error in failures]
            legacy = item.get("error")
            if legacy is not None and legacy is not False and legacy != "" and legacy != []:
                errors.append(backup_error_categories(legacy if isinstance(legacy, dict) else {"message": legacy}))
            require(len(errors) <= 32, "backup_failure_job_errors_refused")
            name = item.get("name")
            nodes.append({"name": name if isinstance(name, str) and name in BACKUP_DIAGNOSTIC_JOBS
                          else "unclassified", "done": done, "errors": errors})
            pending.extend(item.get("child_jobs", []))
        result.append({"binding": "exact_operation" if identifier is not None else "recent_backup_job",
                       "nodes": nodes})
    return result


def public_guard(value):
    """Project only bounded counts and validated hashes; never raw ledger fields."""
    require(isinstance(value, dict), "guard_projection_refused")
    fingerprint = value.get("sha256")
    require(isinstance(fingerprint, str) and re.fullmatch(r"[0-9a-f]{64}", fingerprint), "guard_hash_refused")
    for key in ("unresolved", "rejected", "pending", "uncertain"):
        require(type(value.get(key)) is int and 0 <= value[key] <= 3, "guard_count_refused")
    require(value["unresolved"] in {2, 3} and value["unresolved"] == value["rejected"]
            and value["pending"] == value["uncertain"] == 0
            and value.get("blocked") is (value["unresolved"] == 3)
            and value.get("api_status_checked") is True
            and value.get("retained_bytes_checked") is True, "guard_status_refused")
    return {key: value[key] for key in ("sha256", "blocked", "unresolved", "rejected", "pending",
                                        "uncertain", "api_status_checked", "retained_bytes_checked")}


def write_json(path, data):
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("xb") as stream:
        stream.write(canonical(data) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def check_archive(path, expected_sha, expected_files):
    require(path.is_file() and not path.is_symlink(), "input_archive_refused")
    require(path.stat().st_size <= 64 * 1024**2, "input_archive_size_refused")
    require(sha(path.read_bytes()) == expected_sha, "input_archive_hash_refused")
    inventory = {}
    with zipfile.ZipFile(path) as archive:
        require(len(archive.infolist()) <= 4096, "input_archive_members_refused")
        total = 0
        seen = set()
        for item in archive.infolist():
            name = PurePosixPath(item.filename)
            require(not name.is_absolute() and ".." not in name.parts and "\\" not in item.filename,
                    "input_archive_path_refused")
            require(item.filename not in seen, "input_archive_duplicate_refused")
            seen.add(item.filename)
            mode = item.external_attr >> 16
            require(not stat.S_ISLNK(mode), "input_archive_symlink_refused")
            if item.is_dir():
                continue
            require(item.file_size <= 32 * 1024**2, "input_archive_member_size_refused")
            total += item.file_size
            require(total <= 128 * 1024**2, "input_archive_expansion_refused")
            data = archive.read(item)
            inventory[item.filename] = {"bytes": len(data), "sha256": sha(data)}
    if expected_files is not None:
        require(len(inventory) == expected_files, "input_archive_count_refused")
    return inventory


class JSONSocket:
    """One bounded request/response connection to our private UNIX socket."""

    def __init__(self, path, timeout=10):
        self.path = path
        self.timeout = timeout

    def call(self, execute, arguments=None):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(self.timeout)
            connection.connect(str(self.path))
            request = {"execute": execute, "id": secrets.token_hex(12)}
            if arguments is not None:
                request["arguments"] = arguments
            connection.sendall(canonical(request) + b"\n")
            pending = b""
            while True:
                chunk = connection.recv(65536)
                require(bool(chunk), "guest_agent_connection_closed")
                pending += chunk
                require(len(pending) <= 8 * 1024**2, "guest_agent_response_size_refused")
                while b"\n" in pending:
                    line, pending = pending.split(b"\n", 1)
                    if not line.strip():
                        continue
                    response = json.loads(line.lstrip(b"\xff"))
                    if response.get("id") != request["id"]:
                        continue
                    require("error" not in response and "return" in response, "guest_agent_command_refused")
                    return response["return"]


class Controller:
    def __init__(self, args):
        self.args = args
        self.started = time.monotonic()
        self.deadline = self.started + 5520
        self.stage = "preflight"
        self.qemu = None
        self.qemu_start_ticks = None
        self.kvm_confirmed = False
        self.qga = None
        self.config_path = None
        self.phases = []
        self.acceptance = False
        self.cleanup = {"qemu_stopped": False, "private_workspace_removed": False,
                        "cleanup_failed": False}
        self.nonce = secrets.token_hex(16)
        self.phase_token = secrets.token_hex(16)
        self.generation = "before_restore"
        self.private = None
        self.public = None
        self.provenance = None
        self.inventories = None
        self.backup = None
        self.restore = None
        self.latest_guard_sha256 = None
        self.backup_guard_sha256 = None
        self.automatic_boot = None
        self.operational_restore_passed = False
        self.automatic_guard_antirollback_passed = None
        self.manual_guard_repair_passed = False
        self.network_boundary = {"link_closed": False}
        self.qmp_path = None
        self.direct_installs = 0
        self.core_version_before = None
        self.core_version_after = None
        self.container_core_version_after = None
        self.container_core_version_before = None
        self.core_update_result = "not_requested"
        self.initial_landingpage_seen = False
        self.initial_boot_observations = {}
        self.management_boundary_observations = {}
        self.supervisor_version_observed = None
        self.cli_version_observed = None
        self.core_actions = []
        self.backup_requests = []

    def remaining(self, maximum, cleanup=False):
        remaining = self.deadline - time.monotonic() + (120 if cleanup else 0)
        require(remaining > 0, "host_deadline_exceeded")
        return min(maximum, remaining)

    def command(self, argv, timeout=30):
        result = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=self.remaining(timeout),
                                env={"PATH": os.defpath, "LANG": "C.UTF-8"}, check=False)
        require(result.returncode == 0, "host_command_failed")
        return result.stdout

    def guest(self, command, timeout=90, capture=False):
        operation = self.remaining(timeout)
        require(operation > 0, "guest_operation_deadline_exceeded")
        limit = time.monotonic() + operation
        result = self.qga.call("guest-exec", {"path": "/bin/sh", "arg": ["-c", command],
                                              "capture-output": True})
        require(type(result.get("pid")) is int, "guest_process_identity_refused")
        pid = result["pid"]
        while time.monotonic() < limit:
            status = self.qga.call("guest-exec-status", {"pid": pid})
            if status.get("exited"):
                exitcode, child_signal = status.get("exitcode"), status.get("signal")
                truncated = bool(status.get("out-truncated") or status.get("err-truncated"))
                output = base64.b64decode(status.get("out-data", ""), validate=True)
                error = base64.b64decode(status.get("err-data", ""), validate=True)
                require(len(output) <= 4 * 1024**2 and len(error) <= 4 * 1024**2, "guest_command_output_refused")
                if capture:
                    require((type(exitcode) is int and 0 <= exitcode <= 255)
                            or (exitcode is None and type(child_signal) is int and 0 < child_signal <= 64),
                            "guest_exit_status_refused")
                    return {"exitcode": exitcode, "signal": child_signal,
                            "stdout": b"" if truncated else output, "stderr": b"" if truncated else error,
                            "truncated": truncated}
                require(exitcode == 0 and not truncated, "guest_command_failed")
                return output
            time.sleep(0.3)
        raise Refused("guest_command_deadline_exceeded")

    def guest_write(self, path, content):
        descriptor = self.qga.call("guest-file-open", {"path": path, "mode": "w"})
        try:
            for start in range(0, len(content), 256 * 1024):
                self.remaining(1)
                block = content[start:start + 256 * 1024]
                result = self.qga.call("guest-file-write", {
                    "handle": descriptor, "buf-b64": base64.b64encode(block).decode(),
                    "count": len(block)})
                require(result.get("count") == len(block), "guest_file_write_incomplete")
            self.qga.call("guest-file-flush", {"handle": descriptor})
        finally:
            self.qga.call("guest-file-close", {"handle": descriptor})

    def guest_read(self, path):
        descriptor = self.qga.call("guest-file-open", {"path": path, "mode": "r"})
        content = b""
        try:
            while True:
                self.remaining(1)
                result = self.qga.call("guest-file-read", {"handle": descriptor, "count": 256 * 1024})
                block = base64.b64decode(result.get("buf-b64", ""), validate=True)
                require(len(block) == result.get("count"), "guest_file_read_incomplete")
                content += block
                require(len(content) <= 4 * 1024**2, "guest_file_read_size_refused")
                if result.get("eof"):
                    return content
        finally:
            self.qga.call("guest-file-close", {"handle": descriptor})

    def download_haos(self):
        self.stage = "haos_download"
        compressed = self.private / "haos.qcow2.xz"
        download_end = time.monotonic() + self.remaining(900)
        digest = hashlib.sha256()
        count = 0
        with urllib.request.urlopen(HAOS_URL, timeout=30) as response, compressed.open("xb") as output:
            require(response.status == 200, "haos_download_refused")
            while True:
                require(time.monotonic() < download_end, "haos_download_deadline_exceeded")
                self.remaining(1)
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                count += len(chunk)
                require(count <= 520 * 1024**2, "haos_download_size_refused")
                digest.update(chunk)
                output.write(chunk)
        require(count == 510014132 and digest.hexdigest() == HAOS_XZ_SHA, "haos_archive_pin_refused")
        base = self.private / "haos-base.qcow2"
        expanded = 0
        with lzma.open(compressed, "rb") as source, base.open("xb") as output:
            while chunk := source.read(1024 * 1024):
                self.remaining(1)
                expanded += len(chunk)
                require(expanded <= 2 * 1024**3, "haos_expansion_refused")
                output.write(chunk)
        require(expanded == 970326016, "haos_expanded_size_refused")
        require(sha(base.read_bytes()) == "a291cd909262acd540961067afe7d795f3a41d96dfe0b854a23a3ed4dc7abbc3",
                "haos_expanded_pin_refused")
        overlay = self.private / "haos-guest.qcow2"
        self.command(["qemu-img", "create", "-f", "qcow2", "-F", "qcow2", "-b", str(base), str(overlay)])
        compressed.unlink()
        return overlay

    def start_vm(self, disk):
        self.stage = "kvm_boot"
        code = Path("/usr/share/OVMF/OVMF_CODE_4M.fd")
        variables = Path("/usr/share/OVMF/OVMF_VARS_4M.fd")
        require(code.is_file() and variables.is_file(), "matching_uefi_firmware_required")
        copied_vars = self.private / "uefi-vars.fd"
        shutil.copyfile(variables, copied_vars)
        qga_path = self.private / "qga.sock"
        qmp_path = self.private / "qmp.sock"
        self.qmp_path = qmp_path
        argv = ["qemu-system-x86_64", "-name", "homecircle-enabled-restore-qa-" + self.nonce,
                "-machine", "q35,accel=kvm,hpet=on", "-cpu", "host", "-smp", "2", "-m", "4096",
                "-drive", f"if=pflash,format=raw,readonly=on,file={code}",
                "-drive", f"if=pflash,format=raw,file={copied_vars}",
                "-drive", f"if=virtio,format=qcow2,file={disk}", "-device", "virtio-rng-pci",
                "-display", "none", "-monitor", "none", "-serial", f"file:{self.private / 'serial.log'}",
                "-qmp", f"unix:{qmp_path},server=on,wait=off", "-device", "virtio-serial-pci",
                "-chardev", f"socket,path={qga_path},server=on,wait=off,id=qga0",
                "-device", "virtserialport,chardev=qga0,name=org.qemu.guest_agent.0",
                "-netdev", "user,id=net0", "-device", "virtio-net-pci,id=qa-net0,netdev=net0"]
        with (self.private / "qemu.log").open("xb") as log:
            self.qemu = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                         start_new_session=True,
                                         env={"PATH": os.defpath, "LANG": "C.UTF-8"})
        self.qemu_start_ticks = Path(f"/proc/{self.qemu.pid}/stat").read_text().rsplit(")", 1)[1].split()[19]
        limit = time.monotonic() + self.remaining(30)
        while not qmp_path.exists() and time.monotonic() < limit:
            require(self.qemu.poll() is None, "owned_qemu_stopped_early")
            time.sleep(0.2)
        # QMP capabilities are per connection, unlike QGA. Keep this handshake
        # and the KVM query on one private connection.
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(10)
            connection.connect(str(qmp_path))
            stream = connection.makefile("rwb", buffering=0)
            greeting = json.loads(stream.readline(65536))
            require("QMP" in greeting, "qmp_greeting_refused")
            for identifier, execute in (("capabilities", "qmp_capabilities"), ("kvm", "query-kvm")):
                stream.write(canonical({"execute": execute, "id": identifier}) + b"\n")
                while True:
                    response = json.loads(stream.readline(65536))
                    if response.get("id") == identifier:
                        require("error" not in response, "qmp_query_refused")
                        break
            require(response.get("return") == {"enabled": True, "present": True}, "actual_kvm_acceleration_required")
            self.kvm_confirmed = True
        self.qga = JSONSocket(qga_path)
        limit = time.monotonic() + self.remaining(900)
        while time.monotonic() < limit:
            require(self.qemu.poll() is None, "owned_qemu_stopped_early")
            try:
                self.qga.call("guest-ping")
                require(self.guest("uname -s; uname -m", 10).split() == [b"Linux", b"x86_64"],
                        "guest_platform_refused")
                return
            except (Refused, OSError, ValueError):
                time.sleep(3)
        raise Refused("guest_boot_deadline_exceeded")

    def wait_managed(self):
        self.stage = "managed_core_ready"
        limit = time.monotonic() + self.remaining(1500)
        observed_at = 0.0
        while time.monotonic() < limit:
            try:
                info = json.loads(self.guest(HA + " core info --raw-json", min(30, limit - time.monotonic())))
                require(info.get("result") == "ok", "managed_core_info_refused")
                version = info.get("data", {}).get("version")
                self.core_version_before = public_core_version(version)
                self.core_version_after = self.core_version_before
                if version == "landingpage":
                    self.initial_landingpage_seen = True
                require(public_core_version(version) is not None and version != "landingpage",
                        "real_core_version_not_ready")
                self.managed_core()
                actual = self.real_container_version(min(20, limit - time.monotonic()))
                self.container_core_version_before = public_core_version(actual)
                require(actual == version and actual != "landingpage", "real_core_version_not_ready")
                require(self.management_ready(limit), "initial_core_management_not_ready")
                require(time.monotonic() < limit, "managed_core_boot_deadline_exceeded")
                break
            except (Refused, OSError, ValueError):
                if time.monotonic() - observed_at >= 30 and time.monotonic() + 25 < limit:
                    self.observe_initial_supervisor(limit)
                    observed_at = time.monotonic()
                time.sleep(min(5, max(0, limit - time.monotonic())))
        else:
            raise Refused("managed_core_boot_deadline_exceeded")
        before = info.get("data", {}).get("version")
        self.core_version_before = public_core_version(before)
        self.core_version_after = self.core_version_before
        # One update request only. Its complete JSON result must be accepted;
        # successful CLI exit alone does not establish a successful API result.
        # The same monotonic 1,200-second envelope covers update and readiness.
        limit = time.monotonic() + self.remaining(1200)
        if before != CORE:
            self.core_update_result = "response_invalid"
            update = json.loads(self.guest(HA + " core update --version " + CORE + " --raw-json",
                                          min(900, limit - time.monotonic())))
            result = update.get("result")
            self.core_update_result = result if result in {"ok", "error"} else "response_invalid"
            require(result == "ok", "managed_core_update_refused")
        while time.monotonic() < limit:
            try:
                info = json.loads(self.guest(HA + " core info --raw-json",
                                            min(30, limit - time.monotonic())))
                version = info.get("data", {}).get("version")
                self.core_version_after = public_core_version(version)
                require(info.get("result") == "ok" and version == CORE,
                        "managed_core_target_not_ready")
                self.managed_core()
                # Core info can describe the target while an initial landing
                # page is still running. Verify the actual managed container's
                # installed Home Assistant version in a bounded Linux child.
                actual = self.real_container_version(min(20, limit - time.monotonic()))
                self.container_core_version_after = public_core_version(actual)
                require(actual == CORE, "managed_container_core_target_not_ready")
                require(self.management_ready(limit), "target_core_management_not_ready")
                require(time.monotonic() < limit, "managed_core_target_deadline_exceeded")
                return
            except (Refused, OSError, ValueError):
                time.sleep(min(2, max(0, limit - time.monotonic())))
        raise Refused("managed_core_target_deadline_exceeded")

    def real_container_version(self, timeout):
        return self.guest("/usr/bin/docker exec homeassistant python3 -B -c "
                          + "'from homeassistant.const import __version__; print(__version__)'",
                          timeout).decode().strip()

    def observe_initial_supervisor(self, deadline):
        """Retain narrow health/job diagnostics inside the initial boot bound."""
        observations = {}
        try:
            value = json.loads(self.guest(HA + " supervisor info --raw-json",
                                          min(10, deadline - time.monotonic())))
            observations["supervisor"] = public_supervisor_state(value)
        except (Refused, OSError, ValueError, TypeError):
            observations["supervisor"] = {"result": "unavailable"}
        try:
            value = json.loads(self.guest(HA + " jobs info --raw-json",
                                          min(10, deadline - time.monotonic())))
            observations["jobs"] = public_jobs(value)
        except (Refused, OSError, ValueError, TypeError):
            observations["jobs_query"] = "unavailable"
        self.initial_boot_observations = observations

    def management_ready(self, deadline):
        """Read the supported root lifecycle state and the actual Core jobs.

        /info state is the Supervisor lifecycle; /supervisor/info healthy does
        not provide it. Source: Supervisor 2026.10.0 api/root.py and api/jobs.py.
        No token/environment, arbitrary response body or job reference is kept.
        """
        observed = {"root": {"result": "unavailable"}, "jobs_query": "unavailable"}
        self.management_boundary_observations = observed
        value = json.loads(self.guest(HA + " info --raw-json", min(10, deadline - time.monotonic())))
        root = public_root_state(value)
        observed["root"] = root
        if root["supervisor_version"] is not None:
            self.supervisor_version_observed = root["supervisor_version"]
        value = json.loads(self.guest(HA + " jobs info --raw-json", min(10, deadline - time.monotonic())))
        jobs = public_jobs(value)
        observed.pop("jobs_query")
        observed["jobs"] = jobs
        observed["relevant_core_jobs_idle"] = core_jobs_idle(jobs)
        if self.cli_version_observed is None and time.monotonic() + 11 < deadline:
            try:
                value = json.loads(self.guest(HA + " cli info --raw-json", min(10, deadline - time.monotonic())))
                if value.get("result") == "ok":
                    self.cli_version_observed = public_core_version(value.get("data", {}).get("version"))
            except (Refused, OSError, ValueError, TypeError):
                pass
        return root["result"] == "ok" and root["state"] == "running" and core_jobs_idle(jobs)

    def managed_core(self):
        # Never inspect Config.Env: it contains Supervisor's own internal token.
        command = ("docker inspect homeassistant --format "
                   + "'{\"running\":{{.State.Running}},\"mounts\":{{json .Mounts}}}'")
        data = json.loads(self.guest(command, 30))
        require(data.get("running") is True and isinstance(data.get("mounts"), list),
                "running_managed_core_required")
        matching = [item for item in data["mounts"] if item.get("Destination") == "/config"]
        require(len(matching) == 1 and matching[0].get("Source") == "/mnt/data/supervisor/homeassistant",
                "managed_config_mount_refused")
        require(matching[0].get("RW") is True, "writable_managed_config_required")
        self.config_path = matching[0]["Source"]

    def core_running(self, timeout):
        result = self.guest("/usr/bin/docker inspect homeassistant --format '{{.State.Running}}'", timeout).strip()
        require(result in {b"true", b"false"}, "managed_core_state_refused")
        return result == b"true"

    def core_action(self, action):
        require(action in {"stop", "start"}, "core_action_refused")
        deadline = time.monotonic() + self.remaining(180)
        record = {"action": action, "result": "not_requested", "supervisor_running": False,
                  "relevant_core_jobs_idle": False, "running_before": None, "running_after": None}
        self.core_actions.append(record)
        while time.monotonic() < deadline:
            try:
                if self.management_ready(deadline):
                    record.update(supervisor_running=True, relevant_core_jobs_idle=True)
                    break
            except (Refused, OSError, ValueError, TypeError):
                pass
            time.sleep(min(2, max(0, deadline - time.monotonic())))
        else:
            raise Refused("core_management_boundary_deadline_exceeded")
        record["running_before"] = self.core_running(min(10, deadline - time.monotonic()))
        expected = action == "start"
        require(record["running_before"] is not expected, "core_action_initial_state_refused")
        # Exactly one mutating request. The request and state transition share
        # the existing 180-second total envelope; there is no command retry.
        record["result"] = "response_invalid"
        response = json.loads(self.guest(HA + " core " + action + " --raw-json",
                                         deadline - time.monotonic()))
        result = response.get("result")
        record["result"] = result if isinstance(result, str) and result in {"ok", "error"} else "response_invalid"
        require(result == "ok", "core_action_api_refused")
        while time.monotonic() < deadline:
            try:
                record["running_after"] = self.core_running(min(10, deadline - time.monotonic()))
                if record["running_after"] is expected and time.monotonic() < deadline:
                    return
            except (Refused, OSError, ValueError, TypeError):
                pass
            time.sleep(min(1, max(0, deadline - time.monotonic())))
        raise Refused("core_action_state_deadline_exceeded")

    def stop_core(self):
        self.core_action("stop")

    def start_core(self):
        self.core_action("start")

    def prepare(self, candidate_inventory):
        self.stage = "disposable_configuration"
        self.stop_core()
        self.guest("umask 077; mkdir -m 700 " + GUEST_ROOT, 30)
        staging = self.private / "guest-staging"
        staging.mkdir(mode=0o700)
        components = staging / "custom_components"
        components.mkdir()
        shutil.copytree(ROOT / "guest_helper/homecircle_enabled_restore_qa", components / "homecircle_enabled_restore_qa",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
        with zipfile.ZipFile(self.args.candidate_zip) as archive:
            archive.extractall(components / "homecircle")
        archive_path = self.private / "guest-staging.tgz"
        with tarfile.open(archive_path, "w:gz", format=tarfile.PAX_FORMAT) as archive:
            archive.add(components, arcname="custom_components")
        data = archive_path.read_bytes()
        self.guest_write(GUEST_ROOT + "/staging.tgz", data)
        require(self.guest("sha256sum " + GUEST_ROOT + "/staging.tgz", 30).split()[0].decode() == sha(data),
                "guest_transport_pin_refused")
        self.guest("set -eu; umask 077; tar -xzf " + GUEST_ROOT + "/staging.tgz -C " + self.config_path
                   + "; mkdir -m 700 " + self.config_path + "/" + CONTROL + " "
                   + self.config_path + "/" + RESULTS, 60)
        self.inputs = {"schema": 1, "candidate_sha256": CANDIDATE_SHA,
                       "candidate_inventory": candidate_inventory, "core_version": CORE,
                       "branch_commit": self.args.branch_commit, "generation": self.generation}
        self.guest_write(self.config_path + "/" + CONTROL + "/inputs.json", canonical(self.inputs))
        config = {"homeassistant": {"name": "Disposable HomeCircle Backup QA", "latitude": 0.0,
                                   "longitude": 0.0, "elevation": 0, "unit_system": "metric", "time_zone": "UTC"},
                  "frontend": {}, "http": {}, "lovelace": {}, "person": {}, "zone": {},
                  "websocket_api": {}, "image_upload": {}, "backup": {}, "recorder": {}, "hassio": {},
                  "homecircle_enabled_restore_qa": {"disposable": True}}
        self.guest_write(self.config_path + "/configuration.yaml", canonical(config))
        self.guest("set -eu; chmod 600 " + self.config_path + "/configuration.yaml "
                   + self.config_path + "/" + CONTROL + "/inputs.json; rm " + GUEST_ROOT + "/staging.tgz", 30)
        self.verify_candidate()

    def verify_candidate(self):
        target = self.config_path + "/custom_components/homecircle"
        actual = self.guest("set -eu; find " + target + " -type f ! -path '*/__pycache__/*' ! -name '*.pyc'"
                            " | LC_ALL=C sort", 30).decode().splitlines()
        expected = self.inventories["candidate"]
        require(actual == [target + "/" + name for name in sorted(expected)], "candidate_file_set_refused")
        for name, metadata in expected.items():
            require(sha(self.guest_read(target + "/" + name)) == metadata["sha256"],
                    "candidate_file_bytes_refused")
        self.direct_installs = 1

    def phase(self, name, start=False):
        require(name in PHASES and name not in [phase["phase"] for phase in self.phases], "phase_order_refused")
        self.stage = name
        instruction = {"schema": 1, "token": self.phase_token, "phase": name, "generation": self.generation,
                       "branch_commit": self.args.branch_commit}
        control = self.config_path + "/" + CONTROL
        temporary = control + "/.phase-" + self.phase_token + "-" + name
        self.guest_write(temporary, canonical(instruction))
        self.guest("set -eu; chmod 600 " + temporary + "; mv " + temporary + " " + control + "/phase.json", 30)
        if start:
            self.start_core()
        limit = time.monotonic() + self.remaining(660)
        while time.monotonic() < limit:
            try:
                content = self.guest_read(self.config_path + "/" + RESULTS + "/" + name + ".json")
            except (Refused, OSError, ValueError):
                time.sleep(2)
                continue
            receipt = json.loads(content)
            require(receipt.get("schema") == 1 and receipt.get("token") == self.phase_token
                    and receipt.get("phase") == name and receipt.get("generation") == self.generation
                    and receipt.get("branch_commit") == self.args.branch_commit, "phase_receipt_identity_refused")
            if receipt.get("outcome") != "passed":
                failure = {"schema": 1, "phase": name, "generation": self.generation, "outcome": "failed"}
                for key in ("stage", "failure_type", "failure_code"):
                    value = receipt.get(key)
                    if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_]{1,80}", value):
                        failure[key] = value
                if probe := public_http_probe(receipt.get("http_probe")):
                    failure["http_probe"] = probe
                write_json(self.public / (name + ".json"), failure)
                raise Refused("guest_acceptance_failed")
            projected = self.accept_phase(name, receipt)
            write_json(self.public / (name + ".json"), projected)
            self.phases.append(projected)
            return
        raise Refused("phase_receipt_deadline_exceeded")

    def accept_phase(self, name, receipt):
        def fingerprint(value):
            require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value), "phase_fingerprint_refused")
            return value

        require(receipt.get("core_version") == CORE and receipt.get("candidate_archive_sha256") == CANDIDATE_SHA
                and receipt.get("owner_accounts_used") is False and receipt.get("production_configuration_used") is False
                and receipt.get("provider_accounts_configured") is False, "phase_fixture_scope_refused")
        require(receipt.get("entry_disabled") is False and receipt.get("entry_loaded") is True
                and receipt.get("nonempty_options") is True, "phase_enabled_entry_required")
        expected = self.inventories["candidate"]
        require(receipt.get("package_files_count") == 112
                and receipt.get("package_payload_sha256") == sha(canonical(expected)), "phase_package_projection_refused")
        require(receipt.get("loaded_source_sha256") == expected["__init__.py"]["sha256"], "phase_loaded_source_refused")
        fingerprint(receipt.get("runtime_config_sha256"))
        require(receipt.get("static_served_bundle_matches") is True, "phase_served_bundle_required")
        fingerprint(receipt.get("served_bundle_sha256"))
        process = receipt.get("process", {})
        require(type(process.get("pid")) is int and process["pid"] > 0
                and type(process.get("start_ticks")) is int and process["start_ticks"] > 0,
                "phase_process_identity_refused")
        snapshot = fingerprint(receipt.get("snapshot_sha256"))
        owned_resource = fingerprint(receipt.get("owned_resource_id_sha256"))
        if name == "prebackup":
            require(receipt.get("persisted_storage_checked") is True, "prebackup_persisted_storage_required")
        recorder = receipt.get("recorder", {})
        public_recorder = {}
        for key in ("prebackup_rows", "postbackup_marker_rows", "postrestore_rows"):
            value = recorder.get(key)
            require(value is None or type(value) is int and 0 <= value <= 1000000, "phase_recorder_count_refused")
            public_recorder[key] = value
        for key in ("prebackup_sha256", "postrestore_sha256"):
            value = recorder.get(key)
            public_recorder[key] = None if value is None else fingerprint(value)
        for key in ("prebackup_exact_match", "postbackup_marker_absent", "postrestore_exact_match",
                    "integrity_ok", "backup_platform_registered", "commit_proven", "no_backup_failure_issue"):
            value = recorder.get(key)
            require(value is None or type(value) is bool, "phase_recorder_boolean_refused")
            public_recorder[key] = value
        require(all(public_recorder[key] is True for key in (
            "integrity_ok", "backup_platform_registered", "commit_proven", "no_backup_failure_issue")),
            "phase_recorder_runtime_refused")
        require(type(public_recorder["prebackup_rows"]) is int and public_recorder["prebackup_rows"] >= 5
                and public_recorder["prebackup_sha256"] is not None
                and public_recorder["prebackup_exact_match"] is True, "phase_prebackup_history_refused")
        previous = {phase["phase"]: phase for phase in self.phases}
        if name != "initialize":
            baseline = previous["initialize"]
            require(public_recorder["prebackup_rows"] == baseline["recorder"]["prebackup_rows"]
                    and public_recorder["prebackup_sha256"] == baseline["recorder"]["prebackup_sha256"],
                    "phase_prebackup_history_changed")
            if name != "mutate":
                require(snapshot == baseline["snapshot_sha256"]
                        and owned_resource == baseline["owned_resource_id_sha256"], "phase_identity_snapshot_changed")
        if name == "mutate":
            require(snapshot != previous["initialize"]["snapshot_sha256"]
                    and type(public_recorder["postbackup_marker_rows"]) is int
                    and public_recorder["postbackup_marker_rows"] >= 1
                    and public_recorder["postbackup_marker_absent"] is False,
                    "postbackup_mutation_not_proven")
        else:
            require(public_recorder["postbackup_marker_rows"] == 0
                    and public_recorder["postbackup_marker_absent"] is True, "postbackup_marker_not_absent")
        if name in {"restored", "repair", "restart"}:
            require(type(public_recorder["postrestore_rows"]) is int and public_recorder["postrestore_rows"] >= 5
                    and public_recorder["postrestore_sha256"] is not None
                    and public_recorder["postrestore_exact_match"] is True, "postrestore_recording_not_proven")
            if name != "restored":
                before = previous["restored"]["recorder"]
                require(public_recorder["postrestore_rows"] == before["postrestore_rows"]
                        and public_recorder["postrestore_sha256"] == before["postrestore_sha256"],
                        "postrestore_restart_history_changed")
        guard = public_guard(receipt.get("guard"))
        expected_count = 2 if name in {"initialize", "prebackup"} else 3
        if name == "restored":
            require(self.automatic_boot is not None and guard == self.automatic_boot["guard"]
                    and receipt.get("startup_guard_unchanged_after_load") is True,
                    "restored_startup_guard_changed")
            protected = guard["unresolved"] >= 3 and guard["blocked"]
            require(receipt.get("rollback_protection_passed") is protected, "rollback_result_inconsistent")
            expected_sha = self.latest_guard_sha256 if protected else self.backup_guard_sha256
            require(guard["sha256"] == expected_sha, "restored_guard_not_linked_to_retained_evidence")
        else:
            require(guard["unresolved"] == expected_count, "phase_guard_count_refused")
        if name == "initialize":
            self.backup_guard_sha256 = guard["sha256"]
        if name == "prebackup":
            require(guard["sha256"] == self.backup_guard_sha256, "prebackup_guard_changed")
        if name == "mutate":
            self.latest_guard_sha256 = guard["sha256"]
            require(self.latest_guard_sha256 != self.backup_guard_sha256, "newest_guard_not_distinct")
        if name in {"repair", "restart"}:
            require(guard["sha256"] == self.latest_guard_sha256, "newest_guard_not_retained")
        public = {"schema": 1, "phase": name, "generation": self.generation, "outcome": "passed",
                "package_files_count": 112, "package_payload_sha256": sha(canonical(expected)),
                "loaded_source_sha256": receipt["loaded_source_sha256"], "snapshot_sha256": snapshot,
                "runtime_config_sha256": receipt["runtime_config_sha256"],
                "served_bundle_sha256": receipt["served_bundle_sha256"], "static_served_bundle_matches": True,
                "owned_resource_id_sha256": owned_resource, "entry_disabled": False, "entry_loaded": True,
                "nonempty_options": True, "process": {key: process[key] for key in ("pid", "start_ticks")},
                "recorder": public_recorder, "guard": guard}
        if name == "prebackup":
            public["persisted_storage_checked"] = True
        if name == "restored":
            public["operational_restore_passed"] = True
            public["automatic_guard_antirollback_passed"] = protected
            public["startup_guard_unchanged_after_load"] = True
        return public

    def cli_capabilities(self):
        self.stage = "backup_cli_capabilities"
        for command, flags in (("backups new", ("--folders", "--location", "--filename", "--uncompressed",
                                               "--homeassistant-exclude-database")),
                               ("backups restore", ("--homeassistant", "--location"))):
            help_text = self.guest(HA + " " + command + " --help", 20).decode()
            require(all(flag in help_text for flag in flags), "backup_cli_capability_refused")

    def wait_backup_job(self, identifier, name, deadline):
        while time.monotonic() < deadline:
            value = json.loads(self.guest(HA + " jobs info --raw-json", min(15, deadline - time.monotonic())))
            state = exact_job(value, identifier, name)
            require(state["error_count"] == 0, "backup_job_failed")
            if state["done"]:
                return state
            time.sleep(min(2, max(0, deadline - time.monotonic())))
        raise Refused("backup_job_deadline_exceeded")

    def capture_backup_failure(self, record, identifier, name, deadline):
        record["jobs_query"] = "unavailable"
        if time.monotonic() >= deadline:
            record["jobs_query"] = "deadline_exhausted"
            return
        try:
            value = json.loads(self.guest(HA + " jobs info --raw-json", min(20, deadline - time.monotonic())))
            record["jobs"] = public_backup_failure_jobs(value, identifier, name)
            record["jobs_query"] = "ok"
        except (Refused, OSError, ValueError, TypeError, AttributeError):
            pass

    def backup_operation(self, restore=False):
        action = "restore" if restore else "create"
        self.stage = "supervisor_partial_" + action
        deadline = time.monotonic() + self.remaining(1200 if restore else 900)
        while time.monotonic() < deadline:
            if self.management_ready(deadline):
                break
            time.sleep(2)
        else:
            raise Refused("backup_management_boundary_refused")
        if restore:
            require(self.backup is not None, "backup_before_restore_required")
            command = "backups restore " + self.backup["slug"] + " --homeassistant=true --location=.local"
            job_name = "backup_manager_partial_restore"
        else:
            command = ("backups new --folders homeassistant --homeassistant-exclude-database=false"
                       " --uncompressed --location=.local --name HomeCircleBackupQA --filename homecircle-enabled-restore-qa.tar")
            job_name = "backup_manager_partial_backup"
        # Exactly one supported synchronous request, never a retry of a mutation.
        record = {"action": action, "exit_code": None, "signal": None, "result": "unavailable",
                  "stdout_json": False, "output_truncated": False}
        self.backup_requests.append(record)
        captured = self.guest(HA + " " + command + " --raw-json", deadline - time.monotonic(), capture=True)
        record["exit_code"] = captured["exitcode"]
        record["signal"] = captured["signal"] if type(captured["signal"]) is int and 0 < captured["signal"] <= 64 else None
        record["output_truncated"] = captured["truncated"]
        value = None
        try:
            value = json.loads(captured["stdout"])
            record["stdout_json"] = isinstance(value, dict)
        except (ValueError, UnicodeError):
            pass
        if not isinstance(value, dict):
            value = {}
        result = value.get("result")
        record["result"] = result if isinstance(result, str) and result in {"ok", "error"} else "response_invalid"
        record["api_error"] = backup_error_categories(value)
        record["stderr_error"] = backup_error_categories({"message": captured["stderr"].decode(errors="replace")})
        data = value.get("data", {})
        job = value.get("job_id") or (data.get("job_id") if isinstance(data, dict) else None)
        job = job if isinstance(job, str) and re.fullmatch(r"[0-9a-f]{32}", job) else None
        record["exact_job_id_returned"] = job is not None
        if captured["exitcode"] != 0 or captured["truncated"] or result != "ok":
            self.capture_backup_failure(record, job, job_name, deadline)
            raise Refused("backup_operation_api_refused")
        require(isinstance(job, str) and re.fullmatch(r"[0-9a-f]{32}", job), "backup_operation_job_refused")
        try:
            status = self.wait_backup_job(job, job_name, deadline)
        except (Refused, OSError, ValueError, TypeError, AttributeError):
            self.capture_backup_failure(record, job, job_name, deadline)
            raise
        if restore:
            self.restore = {"result": "ok", "job": status, "enabled_entry_restore": True}
        else:
            slug = data.get("slug")
            require(isinstance(slug, str) and re.fullmatch(r"[a-z0-9]{8,64}", slug), "backup_slug_refused")
            info = backup_info(json.loads(self.guest(HA + " backups info " + slug + " --raw-json",
                                                      min(15, deadline - time.monotonic()))), slug)
            self.backup = {"slug": slug, "result": "ok", "job": status, **info}
        while time.monotonic() < deadline:
            if self.management_ready(deadline):
                # managed_core is a void validator: returning normally proves
                # readiness; its return value is deliberately not a predicate.
                self.managed_core()
                return
            time.sleep(2)
        raise Refused("backup_return_readiness_refused")

    def inspect_backup(self):
        self.stage = "supervisor_backup_archive_proof"
        # This script executes only in the owned guest's official Supervisor
        # container. The real archive remains private inside that guest.
        script = r'''import hashlib,json,tarfile
from pathlib import Path,PurePosixPath

def require(ok):
    if not ok: raise RuntimeError("backup_archive_refused")
def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(data): return json.dumps(data,sort_keys=True,separators=(",",":")).encode()
root=Path("/data/homeassistant")
inputs=json.loads((root/"homecircle-enabled-restore-qa-control/inputs.json").read_bytes())
path=Path("/data/backup/homecircle-enabled-restore-qa.tar")
require(path.is_file() and not path.is_symlink() and 0<path.stat().st_size<=128*1024**2)
package,guard,entry,db,guard_count={},{},None,False,None
with tarfile.open(path,"r:") as outer:
    members=outer.getmembers()
    require(len(members)<=16 and all(not PurePosixPath(m.name).is_absolute() and ".." not in PurePosixPath(m.name).parts for m in members))
    inner=[m for m in members if m.name.removeprefix("./")=="homeassistant.tar"]
    require(len(inner)==1 and inner[0].isfile() and inner[0].size<=128*1024**2)
    with outer.extractfile(inner[0]) as stream,tarfile.open(fileobj=stream,mode="r|") as archive:
        count,total=0,0
        for member in archive:
            count+=1
            require(count<=16384 and member.size<=64*1024**2)
            name=member.name.removeprefix("./")
            require(not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts and not member.issym() and not member.islnk())
            if not member.isfile(): continue
            total+=member.size
            require(total<=256*1024**2)
            with archive.extractfile(member) as content: data=content.read(64*1024**2+1)
            require(len(data)==member.size)
            prefix="data/custom_components/homecircle/"
            if name.startswith(prefix) and "__pycache__" not in name and not name.endswith(".pyc"):
                package[name[len(prefix):]]={"bytes":len(data),"sha256":sha(data)}
            prefix="data/.storage/homecircle_findmy/recovery_guard/"
            if name.startswith(prefix): guard[name[len(prefix):]]={"bytes":len(data),"sha256":sha(data)}
            if name=="data/.storage/homecircle_findmy/recovery_guard/ledger.json":
                record=json.loads(data)["accounts"]["a"*64]
                require(record["rejected"]==2 and record["uncertain"]==record["verified"]==0 and record["pending"] is None)
                guard_count=2
            require(name!="data/homecircle-enabled-restore-qa-control/automatic-boot.json")
            if name=="data/.storage/core.config_entries":
                entries=json.loads(data)["data"]["entries"]
                selected=[e for e in entries if e.get("domain")=="homecircle"]
                require(len(selected)==1 and "disabled_by" in selected[0] and selected[0]["disabled_by"] is None)
                entry=True
            if name=="data/home-assistant_v2.db":
                require(data[:16]==b"SQLite format 3\x00" and len(data)>4096)
                db=True
require(package==inputs["candidate_inventory"] and entry is True and db and guard and guard_count==2)
print(json.dumps({"archive_bytes":path.stat().st_size,"archive_sha256":sha(path.read_bytes()),"database_included":db,"candidate_match":True,"enabled_entry":True,"guard_unresolved":guard_count,"guard_sha256":sha(canonical(guard))},sort_keys=True))
'''
        self.guest_write(GUEST_ROOT + "/inspect-backup.py", script.encode())
        value = json.loads(self.guest("/usr/bin/docker exec -i hassio_supervisor python3 - < "
                                      + GUEST_ROOT + "/inspect-backup.py", 120))
        require(value.get("database_included") is True and value.get("candidate_match") is True
                and value.get("enabled_entry") is True and type(value.get("guard_unresolved")) is int
                and value["guard_unresolved"] == 2 and value.get("guard_sha256") == self.backup_guard_sha256,
                "backup_archive_proof_refused")
        require(type(value.get("archive_bytes")) is int and 0 < value["archive_bytes"] <= 128 * 1024**2
                and isinstance(value.get("archive_sha256"), str)
                and re.fullmatch(r"[0-9a-f]{64}", value["archive_sha256"]), "backup_archive_receipt_refused")
        self.backup["archive"] = value

    def preserve_latest_guard(self):
        self.stage = "retain_newest_guard_outside_backup"
        proof = json.loads(self.guest_read(self.config_path + "/" + CONTROL + "/external-proof.json"))
        require(isinstance(proof, dict) and set(proof) == {
            "schema", "token", "generation", "branch_commit", "postbackup_window"}
            and proof.get("schema") == 1 and proof.get("token") == self.phase_token
            and proof.get("generation") == "before_restore" and proof.get("branch_commit") == self.args.branch_commit,
            "external_recording_proof_identity_refused")
        window = proof.get("postbackup_window")
        require(isinstance(window, dict) and set(window) == {"start", "end", "rows", "sha256"},
                "external_recording_proof_refused")
        require(all(type(window.get(key)) in (float, int) and 0 < window[key] < 10000000000
                    for key in ("start", "end")) and window["start"] < window["end"]
                and type(window.get("rows")) is int and 0 < window["rows"] <= 1000000
                and isinstance(window.get("sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", window["sha256"]),
                "external_recording_proof_refused")
        self.external_proof = proof
        guard = self.config_path + "/.storage/homecircle_findmy/recovery_guard"
        self.guest("set -eu; test -d " + guard + "; test ! -L " + guard + "; test ! -e " + GUEST_ROOT
                   + "/newest-guard; cp -a " + guard + " " + GUEST_ROOT + "/newest-guard", 60)
        require(self.guard_fingerprint(guard) == self.latest_guard_sha256
                and self.guard_fingerprint(GUEST_ROOT + "/newest-guard") == self.latest_guard_sha256,
                "independent_newest_guard_copy_not_proven")

    def disconnect_external_network(self):
        """One QMP link mutation, with a real independent before/after TCP probe."""
        self.stage = "close_owned_vm_external_network"
        self.network_boundary["before_probe_connected"] = self.connectivity_probe()
        require(self.network_boundary["before_probe_connected"] is True, "network_positive_control_refused")
        deadline = time.monotonic() + self.remaining(30)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(self.remaining(10))
            connection.connect(str(self.qmp_path))
            stream = connection.makefile("rwb", buffering=0)
            greeting = json.loads(stream.readline(65536))
            require("QMP" in greeting, "qmp_greeting_refused")
            for identifier, execute, arguments in (("capabilities", "qmp_capabilities", None),
                    ("close_network", "set_link", {"name": "qa-net0", "up": False})):
                request = {"execute": execute, "id": identifier}
                if arguments is not None:
                    request["arguments"] = arguments
                stream.write(canonical(request) + b"\n")
                for _ in range(32):
                    require(time.monotonic() < deadline, "qmp_network_close_deadline_exceeded")
                    connection.settimeout(min(10, deadline - time.monotonic()))
                    response = json.loads(stream.readline(65536))
                    if response.get("id") == identifier:
                        require("error" not in response and response.get("return") == {}, "qmp_network_close_refused")
                        break
                else:
                    raise Refused("qmp_network_response_count_refused")
        self.network_boundary["link_closed"] = True
        self.assert_network_closed()

    def connectivity_probe(self):
        # Fixed public non-provider IP; never contact Apple, Life360 or an owner.
        script = '''import json,socket
connected=False
try:
    s=socket.create_connection(("1.1.1.1",443),timeout=3)
    s.close()
    connected=True
except OSError:
    pass
print(json.dumps({"connected":connected}))
'''
        self.guest_write(GUEST_ROOT + "/network-probe.py", script.encode())
        value = json.loads(self.guest("/usr/bin/docker exec -i hassio_supervisor python3 - < "
                                    + GUEST_ROOT + "/network-probe.py", 15))
        require(type(value.get("connected")) is bool, "network_probe_result_refused")
        return value["connected"]

    def assert_network_closed(self):
        require(self.network_boundary["link_closed"] is True, "network_link_not_closed")
        connected = self.connectivity_probe()
        self.network_boundary["closed_probe_connected"] = connected
        self.network_boundary["closed_probe_observations"] = self.network_boundary.get("closed_probe_observations", 0) + 1
        require(connected is False, "external_network_not_closed")
        self.qga.call("guest-ping")
        self.network_boundary["guest_agent_remained_available"] = True

    def restored_boot_observation(self):
        self.stage = "restored_enabled_automatic_boot"
        self.assert_network_closed()
        limit = time.monotonic() + self.remaining(180)
        while time.monotonic() < limit:
            try:
                value = json.loads(self.guest_read(self.config_path + "/" + CONTROL + "/automatic-boot.json"))
            except (Refused, OSError, ValueError):
                time.sleep(1)
                continue
            require(value.get("schema") == 1 and value.get("token") == self.phase_token
                    and value.get("generation") == "before_restore"
                    and value.get("branch_commit") == self.args.branch_commit,
                    "restored_boot_identity_refused")
            require(value.get("entry_disabled") is False
                    and type(value.get("entry_loaded_at_helper_observation")) is bool,
                    "restored_enabled_entry_required")
            process = value.get("process", {})
            require(type(process.get("pid")) is int and process["pid"] > 0
                    and type(process.get("start_ticks")) is int and process["start_ticks"] > 0
                    and process["start_ticks"] != self.phases[-1]["process"]["start_ticks"],
                    "restored_boot_process_refused")
            guard = public_guard(value.get("guard"))
            self.automatic_guard_antirollback_passed = guard["unresolved"] >= 3 and guard["blocked"]
            self.automatic_boot = {"entry_disabled": False,
                "entry_loaded_at_helper_observation": value["entry_loaded_at_helper_observation"],
                "observation_scope": "earliest_helper_setup_not_candidate_import_order",
                "process": {key: process[key] for key in ("pid", "start_ticks")}, "guard": guard,
                "automatic_guard_antirollback_passed": self.automatic_guard_antirollback_passed}
            self.restore["automatic_boot"] = self.automatic_boot
            return
        raise Refused("restored_enabled_boot_deadline_exceeded")

    def guard_fingerprint(self, root):
        require(root.startswith(self.config_path + "/.storage/") or root == GUEST_ROOT + "/newest-guard",
                "guard_inventory_path_refused")
        require(self.guest("test -d " + root + "; test ! -L " + root + "; find " + root + " -type l", 20) == b"",
                "guard_inventory_symlink_refused")
        names = self.guest("find " + root + " -type f | LC_ALL=C sort", 20).decode().splitlines()
        require(0 < len(names) <= 16, "guard_inventory_count_refused")
        inventory = {}
        for path in names:
            require(path.startswith(root + "/") and re.fullmatch(r"[/A-Za-z0-9_.-]+", path),
                    "guard_inventory_member_refused")
            data = self.guest_read(path)
            require(len(data) <= 512 * 1024, "guard_inventory_size_refused")
            inventory[path[len(root) + 1:]] = {"bytes": len(data), "sha256": sha(data)}
        return sha(canonical(inventory))

    def fresh_restore_control(self):
        self.stage = "fresh_control_after_observed_enabled_restore"
        require(self.automatic_boot is not None, "automatic_boot_before_control_required")
        self.phase_token = secrets.token_hex(16)
        self.generation = "after_restore"
        self.inputs.update(generation=self.generation, latest_guard_sha256=self.latest_guard_sha256,
                           backup_guard_sha256=self.backup_guard_sha256, external_proof=self.external_proof,
                           expected_snapshot_sha256=self.phases[0]["snapshot_sha256"],
                           expected_prebackup_sha256=self.phases[0]["recorder"]["prebackup_sha256"])
        control = self.config_path + "/" + CONTROL
        temporary = control + "/.inputs-" + self.phase_token
        self.guest_write(temporary, canonical(self.inputs))
        self.guest("set -eu; chmod 600 " + temporary + "; mv " + temporary + " " + control + "/inputs.json", 30)
        self.verify_candidate()

    def repair_from_external_newest_guard(self):
        self.stage = "separate_manual_newest_guard_repair"
        require(self.operational_restore_passed and self.automatic_boot is not None,
                "restore_observation_before_repair_required")
        self.assert_network_closed()
        self.stop_core()
        guard = self.config_path + "/.storage/homecircle_findmy/recovery_guard"
        observed = self.guard_fingerprint(guard)
        require(observed == self.automatic_boot["guard"]["sha256"], "observed_restore_guard_changed_before_repair")
        require(self.guard_fingerprint(GUEST_ROOT + "/newest-guard") == self.latest_guard_sha256,
                "external_newest_guard_not_proven")
        self.restore["guard_sha256_before_manual_repair"] = observed
        self.guest("set -eu; rm -rf " + guard + "; mkdir -p " + self.config_path
                   + "/.storage/homecircle_findmy; chmod 700 " + self.config_path + "/.storage/homecircle_findmy; cp -a "
                   + GUEST_ROOT + "/newest-guard " + guard, 60)
        require(self.guard_fingerprint(guard) == self.latest_guard_sha256, "repaired_newest_guard_not_proven")
        self.restore["manual_newest_guard_sha256"] = self.latest_guard_sha256
        self.verify_candidate()

    def run(self):
        require(sys.platform == "linux" and os.uname().machine == "x86_64", "native_linux_amd64_required")
        require(Path("/dev/kvm").exists() and os.access("/dev/kvm", os.R_OK | os.W_OK), "accessible_kvm_required")
        require(re.fullmatch(r"[0-9a-f]{40}", self.args.branch_commit), "branch_commit_refused")
        output = self.args.output
        require(not output.exists() and not output.is_symlink(), "fresh_output_required")
        output.mkdir(mode=0o700, parents=True)
        output = output.resolve()
        require(re.fullmatch(r"[/A-Za-z0-9_.-]+", str(output)), "host_output_path_refused")
        self.public = output / "public-summary"
        self.public.mkdir(mode=0o700)
        self.private = Path(tempfile.mkdtemp(prefix="private-", dir=output))
        candidate = check_archive(self.args.candidate_zip, CANDIDATE_SHA, 112)
        self.inventories = {"candidate": candidate}
        self.provenance = {"candidate_zip_sha256": CANDIDATE_SHA, "candidate_files": 112,
                           "haos_xz_sha256": HAOS_XZ_SHA, "haos_version": "18.3",
                           "core_version": CORE, "controller_branch": BRANCH,
                           "controller_branch_commit": self.args.branch_commit,
                           "candidate_source_commit": "d02a9bdb9027cb51c99165a09ba50d5b175f5fb9",
                           "controller_sha256": sha(Path(__file__).read_bytes()),
                           "helper_files_sha256": {
                               path.relative_to(ROOT / "guest_helper").as_posix(): sha(path.read_bytes())
                               for path in (ROOT / "guest_helper/homecircle_enabled_restore_qa").rglob("*")
                               if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
                           }}
        self.start_vm(self.download_haos())
        self.wait_managed()
        require(self.supervisor_version_observed == "2026.10.2", "pinned_supervisor_version_required")
        self.cli_capabilities()
        self.prepare(candidate)
        self.phase("initialize", start=True)
        self.phase("prebackup")
        self.backup_operation()
        self.inspect_backup()
        self.phase("mutate")
        self.preserve_latest_guard()
        self.disconnect_external_network()
        self.backup_operation(restore=True)
        self.restored_boot_observation()
        self.fresh_restore_control()
        self.phase("restored")
        self.operational_restore_passed = True
        self.repair_from_external_newest_guard()
        self.phase("repair", start=True)
        self.stop_core()
        self.phase("restart", start=True)
        by_name = {phase["phase"]: phase for phase in self.phases}
        for before, after in (("mutate", "restored"), ("restored", "repair"), ("repair", "restart")):
            require(by_name[before]["process"]["start_ticks"] != by_name[after]["process"]["start_ticks"],
                    "new_managed_core_process_required")
        self.assert_network_closed()
        self.manual_guard_repair_passed = True
        self.stop_core()
        self.stage = "diagnostic_complete"
        self.acceptance = True


    def cleanup_vm(self):
        if self.qemu is None:
            self.cleanup["qemu_stopped"] = True
        else:
            try:
                if self.qemu.poll() is None:
                    # Only our actual Popen child, whose /proc identity still
                    # matches, can receive a process-group signal.
                    current = Path(f"/proc/{self.qemu.pid}/stat").read_text().rsplit(")", 1)[1].split()[19]
                    command = Path(f"/proc/{self.qemu.pid}/cmdline").read_bytes()
                    require((self.qemu_start_ticks is None or current == self.qemu_start_ticks)
                            and self.nonce.encode() in command,
                            "owned_qemu_cleanup_identity_refused")
                    os.killpg(self.qemu.pid, signal.SIGTERM)
                    try:
                        self.qemu.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        os.killpg(self.qemu.pid, signal.SIGKILL)
                        self.qemu.wait(timeout=10)
                self.cleanup["qemu_stopped"] = self.qemu.poll() is not None
            except (OSError, Refused, subprocess.SubprocessError):
                self.cleanup["cleanup_failed"] = True
        if self.private is not None and self.cleanup["qemu_stopped"]:
            try:
                shutil.rmtree(self.private)
                self.cleanup["private_workspace_removed"] = not self.private.exists()
            except OSError:
                self.cleanup["cleanup_failed"] = True
        else:
            self.cleanup["private_workspace_removed"] = self.private is None
        if not all(self.cleanup[key] for key in ("qemu_stopped", "private_workspace_removed")):
            self.cleanup["cleanup_failed"] = True

    def finish(self, failure):
        self.cleanup_vm()
        completed = self.acceptance and failure is None and not self.cleanup["cleanup_failed"]
        passed = completed and self.automatic_guard_antirollback_passed is True
        outcome = "passed" if passed else ("confirmed_safety_issue" if completed else "failed_or_incomplete")
        receipt = {"schema": 1, "outcome": outcome,
                   "failure_or_final_stage": self.stage,
                   "failure_type": type(failure).__name__ if failure is not None else None,
                   "confirmed_issue": "older_backup_decreased_local_recovery_guard"
                   if completed and self.automatic_guard_antirollback_passed is False else None,
                   "failure_code": str(failure) if type(failure) is Refused
                   and re.fullmatch(r"[a-z0-9_]{1,80}", str(failure)) else None,
                   "core_version_target": CORE, "core_version_before": self.core_version_before,
                   "core_version_after": self.core_version_after,
                   "container_core_version_after": self.container_core_version_after,
                   "container_core_version_before": self.container_core_version_before,
                   "core_update_result": self.core_update_result,
                   "initial_landingpage_seen": self.initial_landingpage_seen,
                   "initial_boot_observations": self.initial_boot_observations,
                   "management_boundary_observations": self.management_boundary_observations,
                   "supervisor_version_observed": self.supervisor_version_observed,
                   "cli_version_observed": self.cli_version_observed,
                   "core_actions": self.core_actions,
                   "backup_requests": self.backup_requests,
                   "host_elapsed_seconds": round(time.monotonic() - self.started, 3),
                   "native_linux_amd64_kvm_required": True, "actual_kvm_confirmed": self.kvm_confirmed,
                   "diagnostic_completed": completed, "ordinary_enabled_restore_safety_accepted": passed,
                   "operational_restore_passed": self.operational_restore_passed,
                   "automatic_guard_antirollback_passed": self.automatic_guard_antirollback_passed,
                   "manual_newest_guard_repair_passed": self.manual_guard_repair_passed,
                   "network_boundary": self.network_boundary, "phases": len(self.phases),
                   "provider_accounts_configured": False, "owner_credentials_used": False,
                   "provider_request_attempt_counts_measured": False,
                   "recovery_proof_attempt_counts_measured": False,
                   "network_scope": "whole_owned_vm_closed_before_restore_until_cleanup",
                   "guest_github_token_used": False,
                   "candidate_transport": "stopped_verified_zip_files",
                   "candidate_hacs_download_tested": False,
                   "candidate_release_zip_transport_tested": False,
                   "direct_candidate_installs": self.direct_installs,
                   "supervisor_partial_homeassistant_backup_tested": self.backup is not None,
                   "supervisor_partial_homeassistant_restore_tested": self.restore is not None,
                   "supervisor_full_backup_restore_tested": False,
                   "enabled_entry_restore_tested": self.operational_restore_passed,
                   "automatic_guard_antirollback_tested": self.automatic_guard_antirollback_passed is not None,
                   "guard_repair_before_first_enabled_boot": False,
                   "backup": {key: value for key, value in (self.backup or {}).items() if key != "slug"},
                   "restore": self.restore,
                   "production_configuration_used": False, "provenance": self.provenance, **self.cleanup}
        if self.public is not None:
            write_json(self.public / "host.json", receipt)
        print("haos_enabled_restore_outcome=" + receipt["outcome"], flush=True)
        return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-zip", type=Path, required=True)
    parser.add_argument("--branch-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    controller = Controller(args)

    def stopping(_signal, _frame):
        raise Refused("host_interrupted")

    signal.signal(signal.SIGTERM, stopping)
    signal.signal(signal.SIGHUP, stopping)
    signal.signal(signal.SIGINT, stopping)
    failure = None
    try:
        controller.run()
    except BaseException as error:
        failure = error
    return controller.finish(failure)


if __name__ == "__main__":
    raise SystemExit(main())
