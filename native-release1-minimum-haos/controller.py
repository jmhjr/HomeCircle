"""Owned native managed HAOS minimum-Core install/start/restart witness."""
from __future__ import annotations
import argparse
import ast
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

ROOT = Path(__file__).resolve().parent
HAOS_URL = "https://github.com/home-assistant/operating-system/releases/download/18.3/haos_ova-18.3.qcow2.xz"
HAOS_XZ_SHA = "fae6a728768cc10aff60d4820bfcd40d64cd77fab82c8bd92af13b3d9d414090"
CANDIDATE_SHA = "c4530d94be3b2996f8d6c8948db88a51868566047d68558eefde7967f270a861"
SOURCE_COMMIT = "9bf03eb45d2cf43274074534e9dfe2de841f4011"
CORE = "2026.9.4"
CONSTRAINTS_SHA = "962c9ccaf398e0b92b10ac9f765ac0f17e22238adc4e768deebc051ee8b60651"
BRANCH = "codex/native-amd64-validation"
IMAGE_REFERENCE = "ghcr.io/home-assistant/qemux86-64-homeassistant:2026.9.4"
IMAGE_INDEX_DIGEST = "sha256:414dce485b4eebd9f929f293f7252340bada5715fc4a48b2b954d79195ed3019"
IMAGE_CONFIG_ID = "sha256:560be76a9ee5019c1b557241db8d1127550f21fba952a1a976c3d186f9b2cd9e"
HA = "/usr/bin/docker exec hassio_cli ha"
GUEST_ROOT = "/mnt/data/homecircle-minimum-haos-qa"
CONTROL = "homecircle-minimum-haos-qa-control"
RESULTS = "homecircle-minimum-haos-qa-results"
PHASES = ("initialize", "restart")
CORE_MANAGEMENT_JOBS = frozenset({
    "home_assistant_core_install_landing_page", "home_assistant_core_install",
    "home_assistant_core_start", "home_assistant_core_update", "home_assistant_core_stop",
    "home_assistant_core_restart", "home_assistant_core_rebuild",
})

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


def source_failure_catalog():
    """Finite literal labels from only these reviewed, hash-bound QA sources."""
    paths = (ROOT / 'controller.py', ROOT / 'reset_fresh_config.py',
             ROOT / 'guest_helper/homecircle_minimum_haos_qa/__init__.py',
             ROOT / 'guest_helper/homecircle_minimum_haos_qa/dependency_probe.py')
    codes, stages = set(), set(PHASES)
    for path in paths:
        tree = ast.parse(path.read_bytes())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                    and node.func.id in {'check', 'require', 'Refused'} and node.args:
                label = node.args[-1]
                if isinstance(label, ast.Constant) and isinstance(label.value, str):
                    codes.add(label.value)
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == 'stage'
                or isinstance(target, ast.Attribute) and target.attr == 'stage' for target in node.targets
            ) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                stages.add(node.value.value)
    return frozenset(codes), frozenset(stages)


FAILURE_CODES, FAILURE_STAGES = source_failure_catalog()
FAILURE_TYPES = frozenset({'Refused', 'TimeoutError', 'ValueError', 'TypeError', 'KeyError', 'IndexError',
    'AttributeError', 'RuntimeError', 'OSError', 'FileNotFoundError', 'PermissionError', 'JSONDecodeError',
    'UnicodeDecodeError', 'BrokenPipeError', 'ConnectionError', 'ConnectionResetError', 'ProcessLookupError',
    'ChildProcessError', 'TimeoutExpired', 'CancelledError', 'KeyboardInterrupt', 'SystemExit', 'Exception'})


def failure_projection(value):
    stage, kind, code = value.get('stage'), value.get('failure_type'), value.get('failure_code')
    return {'stage': stage if isinstance(stage, str) and stage in FAILURE_STAGES else 'unrecognized_stage',
            'failure_type': kind if isinstance(kind, str) and kind in FAILURE_TYPES else 'unrecognized_failure_type',
            'failure_code': code if isinstance(code, str) and code in FAILURE_CODES else None}


class Controller:
    def __init__(self, args):
        self.args = args
        self.started = time.monotonic()
        self.deadline = self.started + 5520
        self.stage = "preflight"
        self.qemu = self.qemu_start_ticks = self.qga = self.config_path = None
        self.kvm_confirmed = False
        self.phases = []
        self.acceptance = False
        self.cleanup = {"qemu_stopped": False, "private_workspace_removed": False, "cleanup_failed": False}
        self.nonce = secrets.token_hex(16)
        self.phase_token = secrets.token_hex(16)
        self.private = self.public = self.provenance = self.inventories = None
        self.network_boundary = {"link_closed": False}
        self.qmp_path = None
        self.direct_installs = 0
        self.core_version_before = self.core_version_after = None
        self.container_core_version_before = self.container_core_version_after = None
        self.core_update_result = "not_requested"
        self.version_change_requests = 0
        self.initial_landingpage_seen = False
        self.initial_boot_observations = {}
        self.management_boundary_observations = {}
        self.supervisor_version_observed = self.cli_version_observed = None
        self.core_actions = []
        self.reset_receipt = self.cli_capabilities = self.dependencies_before = self.target_environment = None
        self.minimum_core_image = None

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
        argv = ["qemu-system-x86_64", "-name", "homecircle-minimum-haos-qa-" + self.nonce,
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


    def wait_initial_managed(self):
        self.stage = 'initial_managed_core_ready'
        limit = time.monotonic() + self.remaining(1500)
        observed = 0.0
        while time.monotonic() < limit:
            try:
                value = json.loads(self.guest(HA + ' core info --raw-json', min(30, limit - time.monotonic())))
                version = value.get('data', {}).get('version')
                self.initial_landingpage_seen |= version == 'landingpage'
                self.core_version_before = public_core_version(version)
                require(value.get('result') == 'ok' and self.core_version_before is not None
                        and version != 'landingpage', 'initial_core_version_not_ready')
                self.managed_core()
                actual = self.real_container_version(min(20, limit - time.monotonic()))
                self.container_core_version_before = public_core_version(actual)
                require(actual == version and self.management_ready(limit), 'initial_managed_core_not_ready')
                return
            except (Refused, OSError, ValueError, TypeError):
                if time.monotonic() - observed >= 30 and time.monotonic() + 25 < limit:
                    self.observe_initial_supervisor(limit)
                    observed = time.monotonic()
                time.sleep(min(3, max(0, limit - time.monotonic())))
        raise Refused('initial_core_boot_deadline_exceeded')

    def verify_cli(self):
        self.stage = 'actual_cli_capabilities'
        require(self.cli_version_observed == '2026.09.0', 'cli_addon_version_refused')
        for command, flags in (('core update', ('--version', '--backup')),
                               ('core start', ()), ('core stop', ())):
            text = self.guest(HA + ' ' + command + ' --help', 20).decode()
            require('Usage:' in text and all(flag in text for flag in flags), 'cli_capability_refused')
        raw = self.guest("/usr/bin/docker exec hassio_cli /bin/sh -c 'binary=$(command -v ha); test -n \"$binary\"; sha256sum \"$binary\"'", 20)
        digest = raw.decode().split()[0]
        require(re.fullmatch(r'[0-9a-f]{64}', digest), 'cli_executable_fingerprint_refused')
        self.cli_capabilities = {'addon_version': '2026.09.0', 'executed_binary_sha256': digest,
                                 'actual_update_version_backup_flags': True, 'actual_start_stop_help': True,
                                 'application_version_not_inferred_from_addon': True}

    def select_minimum_core(self):
        require(self.reset_receipt is None and self.version_change_requests == 0, 'fresh_selection_repeat_refused')
        self.stage = 'fresh_owned_config_before_minimum'
        require(self.kvm_confirmed and self.qemu is not None and self.qemu.poll() is None
                and self.private is not None and self.config_path == '/mnt/data/supervisor/homeassistant',
                'fresh_owned_vm_reset_required')
        self.stop_core()
        require(self.core_running(15) is False, 'stopped_core_before_fresh_reset_required')
        script = (ROOT / 'reset_fresh_config.py').read_bytes()
        self.guest_write(GUEST_ROOT + '/reset-fresh-config.py', script)
        value = json.loads(self.guest('/usr/bin/docker exec -i hassio_supervisor python3 -B - '
                                      + self.nonce + ' < ' + GUEST_ROOT + '/reset-fresh-config.py', 90))
        self.reset_receipt = checked_reset(value)
        limit = time.monotonic() + self.remaining(1200)
        self.stage = 'single_minimum_core_selection'
        if self.core_version_before != CORE:
            require(self.version_change_requests == 0, 'version_mutation_repeat_refused')
            self.version_change_requests += 1
            self.core_update_result = 'response_invalid'
            result = json.loads(self.guest(HA + ' core update --version ' + CORE
                                          + ' --backup=false --raw-json', min(900, limit - time.monotonic())))
            self.core_update_result = result.get('result') if result.get('result') in {'ok', 'error'} else 'response_invalid'
            require(self.core_update_result == 'ok', 'minimum_core_selection_api_refused')
        require(self.core_running(min(15, limit - time.monotonic())) is False,
                'stopped_core_after_selection_required')
        self.start_core()
        while time.monotonic() < limit:
            try:
                value = json.loads(self.guest(HA + ' core info --raw-json', min(20, limit - time.monotonic())))
                self.core_version_after = public_core_version(value.get('data', {}).get('version'))
                self.managed_core()
                self.container_core_version_after = public_core_version(self.real_container_version(min(20, limit - time.monotonic())))
                require(value.get('result') == 'ok' and self.core_version_after == CORE
                        and self.container_core_version_after == CORE and self.management_ready(limit),
                        'actual_minimum_core_not_ready')
                break
            except (Refused, OSError, ValueError, TypeError):
                time.sleep(min(2, max(0, limit - time.monotonic())))
        else:
            raise Refused('actual_minimum_core_deadline_exceeded')
        self.stage = 'minimum_base_dependency_observation'
        self.minimum_core_image = self.actual_core_image()
        self.dependencies_before = self.observe_dependencies()
        self.target_environment = project_dependencies(self.dependencies_before, complete=False)
        require(any(not item['available'] for item in self.target_environment['direct'].values()),
                'normal_dependency_installation_not_demonstrable')

    def actual_core_image(self):
        value = json.loads(self.guest("/usr/bin/docker inspect homeassistant --format "
            + "'{\"reference\":{{json .Config.Image}},\"image_id\":{{json .Image}}}'", 20))
        require(type(value) is dict and value.get('reference') == IMAGE_REFERENCE
                and value.get('image_id') == IMAGE_CONFIG_ID, 'minimum_core_image_identity_refused')
        return {'reference': IMAGE_REFERENCE, 'image_config_id': IMAGE_CONFIG_ID,
                'official_index_digest': IMAGE_INDEX_DIGEST, 'observed_config_id_matches': True}

    def observe_dependencies(self):
        script = (ROOT / 'guest_helper/homecircle_minimum_haos_qa/dependency_probe.py').read_bytes()
        self.guest_write(GUEST_ROOT + '/observe-dependencies.py', script)
        return json.loads(self.guest('/usr/bin/docker exec -i homeassistant python3 -B - < '
                                    + GUEST_ROOT + '/observe-dependencies.py', 60))

    def prepare(self, candidate_inventory):
        self.stage = 'stopped_exact_candidate_staging'
        require(self.container_core_version_after == CORE and self.reset_receipt is not None,
                'minimum_environment_before_candidate_required')
        self.stop_core()
        staging = self.private / 'guest-staging'
        staging.mkdir(mode=0o700)
        components = staging / 'custom_components'
        components.mkdir()
        shutil.copytree(ROOT / 'guest_helper/homecircle_minimum_haos_qa', components / 'homecircle_minimum_haos_qa',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
        with zipfile.ZipFile(self.args.candidate_zip) as archive:
            archive.extractall(components / 'homecircle')
        archive_path = self.private / 'guest-staging.tgz'
        with tarfile.open(archive_path, 'w:gz', format=tarfile.PAX_FORMAT) as archive:
            archive.add(components, arcname='custom_components')
        raw = archive_path.read_bytes()
        self.guest_write(GUEST_ROOT + '/staging.tgz', raw)
        require(self.guest('sha256sum ' + GUEST_ROOT + '/staging.tgz', 30).split()[0].decode() == sha(raw),
                'guest_transport_pin_refused')
        self.guest('set -eu; umask 077; tar -xzf ' + GUEST_ROOT + '/staging.tgz -C ' + self.config_path
                   + '; mkdir -m 700 ' + self.config_path + '/' + CONTROL + ' ' + self.config_path + '/' + RESULTS, 60)
        inputs = {'schema': 1, 'candidate_sha256': CANDIDATE_SHA, 'candidate_inventory': candidate_inventory,
                  'core_version': CORE, 'branch_commit': self.args.branch_commit}
        self.guest_write(self.config_path + '/' + CONTROL + '/inputs.json', canonical(inputs))
        config = {'homeassistant': {'name': 'Disposable HomeCircle Minimum Core QA', 'latitude': 0.0,
                  'longitude': 0.0, 'elevation': 0, 'unit_system': 'metric', 'time_zone': 'UTC'},
                  'frontend': {}, 'http': {}, 'lovelace': {}, 'person': {}, 'zone': {},
                  'websocket_api': {}, 'image_upload': {}, 'hassio': {},
                  'homecircle_minimum_haos_qa': {'disposable': True}}
        self.guest_write(self.config_path + '/configuration.yaml', canonical(config))
        self.guest('set -eu; chmod 600 ' + self.config_path + '/configuration.yaml '
                   + self.config_path + '/' + CONTROL + '/inputs.json; rm ' + GUEST_ROOT + '/staging.tgz', 30)
        self.verify_candidate()

    def phase(self, name):
        require(name in PHASES and len(self.phases) == PHASES.index(name), 'phase_order_refused')
        self.stage = name
        instruction = {'schema': 1, 'phase': name, 'token': self.phase_token, 'branch_commit': self.args.branch_commit}
        temporary = self.config_path + '/' + CONTROL + '/.phase-' + self.phase_token + '-' + name
        self.guest_write(temporary, canonical(instruction))
        self.guest('set -eu; chmod 600 ' + temporary + '; mv ' + temporary + ' '
                   + self.config_path + '/' + CONTROL + '/phase.json', 30)
        self.start_core()
        limit = time.monotonic() + self.remaining(660 if name == 'initialize' else 480)
        while time.monotonic() < limit:
            try:
                raw = self.guest_read(self.config_path + '/' + RESULTS + '/' + name + '.json')
            except (Refused, OSError, ValueError):
                time.sleep(2)
                continue
            receipt = json.loads(raw)
            require(type(receipt.get('schema')) is int and receipt['schema'] == 1 and receipt.get('phase') == name
                    and receipt.get('token') == self.phase_token and receipt.get('branch_commit') == self.args.branch_commit,
                    'phase_receipt_identity_refused')
            if receipt.get('outcome') != 'passed':
                public = {'schema': 1, 'phase': name, 'outcome': 'failed'}
                public.update(failure_projection(receipt))
                if receipt.get('normal_dependencies') is not None:
                    try:
                        public['normal_dependencies'] = project_dependencies(receipt['normal_dependencies'], complete=False)
                    except (Refused, TypeError, ValueError, KeyError):
                        public['dependency_observation_unavailable'] = True
                write_json(self.public / (name + '.json'), public)
                raise Refused('guest_acceptance_failed')
            projected = self.accept_phase(name, receipt)
            write_json(self.public / (name + '.json'), projected)
            self.phases.append(projected)
            return
        failure = {'schema': 1, 'phase': name, 'outcome': 'failed', 'stage': 'receipt_wait_timeout'}
        try:
            failure['normal_dependencies'] = project_dependencies(self.observe_dependencies(), complete=False)
        except (Refused, OSError, TypeError, ValueError, KeyError):
            failure['dependency_observation_unavailable'] = True
        write_json(self.public / (name + '.json'), failure)
        raise Refused('phase_receipt_deadline_exceeded')

    def accept_phase(self, name, receipt):
        expected = self.inventories['candidate']
        require(receipt.get('core_version') == CORE and receipt.get('candidate_archive_sha256') == CANDIDATE_SHA
                and receipt.get('package_files_count') == 113 and receipt.get('package_payload_sha256') == sha(canonical(expected)),
                'phase_exact_package_refused')
        for key in ('entry_loaded', 'nonempty_options', 'static_served_bundle_matches', 'persisted_storage_checked'):
            require(receipt.get(key) is True, 'phase_required_state_refused')
        require(receipt.get('entry_disabled') is False and receipt.get('persistent_people') == 2
                and receipt.get('explicit_trackers') == 2 and receipt.get('provider_accounts_configured') is False
                and receipt.get('owner_accounts_used') is False,
                'phase_selection_scope_refused')
        require(receipt.get('loaded_source_sha256') == expected['__init__.py']['sha256']
                and receipt.get('served_bundle_sha256') == expected['frontend/homecircle-card.js']['sha256'],
                'phase_loaded_served_bytes_refused')
        fields = ('snapshot_sha256', 'runtime_config_sha256', 'owned_resource_id_sha256',
                  'served_bundle_sha256', 'package_payload_sha256', 'loaded_source_sha256')
        for key in fields:
            require(isinstance(receipt.get(key), str) and re.fullmatch(r'[0-9a-f]{64}', receipt[key]), 'phase_fingerprint_refused')
            if self.phases:
                require(receipt[key] == self.phases[0][key], 'restart_identity_or_bytes_changed')
        process = receipt.get('process', {})
        require(type(process) is dict and set(process) == {'pid', 'start_ticks'} and
                all(type(value) is int and value > 0 for value in process.values()), 'phase_process_refused')
        if self.phases:
            require(process['start_ticks'] != self.phases[0]['process']['start_ticks'], 'new_core_process_required')
        dependencies = project_dependencies(receipt.get('normal_dependencies'), complete=True)
        if self.phases:
            require(dependencies['closure'] == self.phases[0]['normal_dependencies']['closure'], 'restart_dependency_versions_changed')
        return {'schema': 1, 'phase': name, 'outcome': 'passed', 'core_version': CORE,
                'candidate_archive_sha256': CANDIDATE_SHA, 'package_files_count': 113,
                **{key: receipt[key] for key in fields}, 'process': process, 'entry_loaded': True,
                'entry_disabled': False, 'nonempty_options': True, 'persistent_people': 2,
                'explicit_trackers': 2, 'provider_accounts_configured': False, 'owner_accounts_used': False, 'persisted_storage_checked': True,
                'static_served_bundle_matches': True, 'normal_dependencies': dependencies}

    def run(self):
        require(sys.platform == 'linux' and os.uname().machine == 'x86_64', 'native_linux_amd64_required')
        require(Path('/dev/kvm').exists() and os.access('/dev/kvm', os.R_OK | os.W_OK), 'accessible_kvm_required')
        require(re.fullmatch(r'[0-9a-f]{40}', self.args.branch_commit), 'branch_commit_refused')
        output = self.args.output
        require(not output.exists() and not output.is_symlink(), 'fresh_output_required')
        output.mkdir(mode=0o700, parents=True)
        output = output.resolve()
        require(re.fullmatch(r'[/A-Za-z0-9_.-]+', str(output)), 'host_output_path_refused')
        self.public = output / 'public-summary'
        self.public.mkdir(mode=0o700)
        self.private = Path(tempfile.mkdtemp(prefix='private-', dir=output))
        inventory = check_archive(self.args.candidate_zip, CANDIDATE_SHA, 113)
        self.inventories = {'candidate': inventory}
        self.provenance = {'candidate_zip_sha256': CANDIDATE_SHA, 'candidate_files': 113,
            'candidate_source_commit': SOURCE_COMMIT, 'candidate_version': '0.1.0-beta.20',
            'same_version_unreleased_development_preview': True, 'release_published': False,
            'controller_branch': BRANCH, 'controller_branch_commit': self.args.branch_commit,
            'controller_sha256': sha(Path(__file__).read_bytes()), 'haos_version': '18.3', 'haos_xz_sha256': HAOS_XZ_SHA,
            'helper_files_sha256': {path.relative_to(ROOT / 'guest_helper').as_posix(): sha(path.read_bytes())
                for path in (ROOT / 'guest_helper/homecircle_minimum_haos_qa').rglob('*')
                if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc'},
            'reset_script_sha256': sha((ROOT / 'reset_fresh_config.py').read_bytes()),
            'expected_machine_image_reference': IMAGE_REFERENCE, 'expected_machine_image_index_digest': IMAGE_INDEX_DIGEST,
            'expected_machine_image_config_id': IMAGE_CONFIG_ID}
        self.start_vm(self.download_haos())
        self.wait_initial_managed()
        require(self.supervisor_version_observed == '2026.10.2', 'pinned_supervisor_required')
        self.verify_cli()
        self.guest('umask 077; mkdir -m 700 ' + GUEST_ROOT, 30)
        self.select_minimum_core()
        self.prepare(inventory)
        self.phase('initialize')
        require(self.actual_core_image() == self.minimum_core_image, 'configured_core_image_changed')
        self.disconnect_external_network()
        self.stop_core()
        self.phase('restart')
        require(self.actual_core_image() == self.minimum_core_image, 'restarted_core_image_changed')
        self.assert_network_closed()
        self.verify_candidate()
        self.stop_core()
        self.stage = 'minimum_managed_witness_complete'
        self.acceptance = True

    def finish(self, failure):
        self.cleanup_vm()
        passed = self.acceptance and failure is None and not self.cleanup['cleanup_failed'] and len(self.phases) == 2
        labels = failure_projection({'stage': self.stage, 'failure_type': type(failure).__name__ if failure else None,
                                     'failure_code': str(failure) if type(failure) is Refused else None})
        receipt = {'schema': 1, 'outcome': 'passed' if passed else 'failed_or_incomplete',
            'failure_or_final_stage': labels['stage'], 'failure_type': labels['failure_type'] if failure else None,
            'failure_code': labels['failure_code'],
            'core_version_target': CORE, 'core_version_before': self.core_version_before,
            'core_version_after': self.core_version_after, 'container_core_version_before': self.container_core_version_before,
            'container_core_version_after': self.container_core_version_after, 'core_update_result': self.core_update_result,
            'version_change_requests': self.version_change_requests, 'initial_landingpage_seen': self.initial_landingpage_seen,
            'initial_boot_observations': self.initial_boot_observations,
            'management_boundary_observations': self.management_boundary_observations,
            'supervisor_version_observed': self.supervisor_version_observed, 'cli_capabilities': self.cli_capabilities,
            'core_actions': self.core_actions, 'fresh_owned_config': self.reset_receipt,
            'dependencies_before_candidate': self.target_environment, 'minimum_core_image': self.minimum_core_image,
            'normal_managed_dependency_installation': passed, 'prepared_dependency_preload_used': False,
            'setup_with_normal_external_access': bool(self.phases), 'restart_with_external_network_closed': passed,
            'network_boundary': self.network_boundary, 'actual_kvm_confirmed': self.kvm_confirmed,
            'phases': len(self.phases), 'host_elapsed_seconds': round(time.monotonic() - self.started, 3),
            'candidate_transport': 'stopped_verified_zip_files', 'direct_candidate_installs': self.direct_installs,
            'candidate_hacs_download_tested': False, 'candidate_release_zip_transport_tested': False,
            'backup_restore_tested': False, 'native_worker_repeated': False, 'provider_accounts_configured': False,
            'owner_credentials_used': False, 'production_configuration_used': False,
            'provider_request_attempt_counts_measured': False, 'recovery_proof_attempt_counts_measured': False,
            'stable_release_approval': False, 'provenance': self.provenance, **self.cleanup}
        if self.public is not None:
            write_json(self.public / 'host.json', receipt)
        print('minimum_managed_haos_outcome=' + receipt['outcome'], flush=True)
        return 0 if passed else 1


def checked_reset(value):
    require(type(value) is dict and set(value) == {'files', 'bytes', 'children', 'owner_accounts_found',
        'candidate_previously_present', 'fresh_config_reset', 'mount_directory_preserved'}, 'fresh_reset_projection_refused')
    for key, upper in (('files', 8192), ('bytes', 64 * 1024**2), ('children', 128)):
        require(type(value[key]) is int and 0 <= value[key] <= upper, 'fresh_reset_bounds_refused')
    require(value['owner_accounts_found'] is False and value['candidate_previously_present'] is False
            and value['fresh_config_reset'] is True and value['mount_directory_preserved'] is True,
            'fresh_reset_proof_refused')
    return dict(value)


DIRECT = {'life360': '7.2.0', 'protobuf': '6.32.0', 'anisette': '1.2.4',
          'unicorn': '2.1.4', 'srp': '1.0.22', 'beautifulsoup4': '4.13.3'}
CLOSURE = frozenset(('aiohappyeyeballs', 'aiohttp', 'aiosignal', 'anisette', 'appdirs', 'attrs',
    'beautifulsoup4', 'certifi', 'frozenlist', 'fs', 'idna', 'life360', 'multidict', 'propcache',
    'protobuf', 'pyelftools', 'setuptools', 'six', 'soupsieve', 'srp', 'typing-extensions',
    'unicorn', 'urllib3', 'yarl'))


def project_dependencies(value, complete):
    require(type(value) is dict and type(value.get('schema')) is int and value['schema'] == 1 and value.get('core') == CORE
            and value.get('python') == '3.14.6' and value.get('constraints_sha256') == CONSTRAINTS_SHA,
            'normal_dependency_environment_refused')
    for key in ('constraints_match', 'docker_environment', 'ordinary_pip_target_unset', 'config_deps_empty'):
        require(value.get(key) is True, 'normal_dependency_boundary_refused')
    require(value.get('provider_or_native_imports_requested_by_probe') is False
            and type(value.get('closure_count')) is int and value['closure_count'] == 24,
            'normal_dependency_scope_refused')
    require(type(value.get('closure_graph_checked')) is bool, 'normal_dependency_graph_type_refused')
    require(type(value.get('closure')) is dict and set(value['closure']) == CLOSURE
            and type(value.get('direct')) is dict and set(value['direct']) == set(DIRECT), 'normal_dependency_names_refused')
    closure, direct = {}, {}
    for name, item in value['closure'].items():
        require(type(item) is dict and all(type(item.get(key)) is bool for key in
            ('available', 'metadata_system_origin', 'constraints_satisfied', 'python_satisfied')), 'normal_dependency_types_refused')
        version = item.get('version')
        require((version is None and item['available'] is False) or (isinstance(version, str)
                and re.fullmatch(r'[0-9]{1,8}(?:\.[0-9]{1,8}){1,3}', version) and item['available'] is True),
                'normal_dependency_version_refused')
        if complete:
            require(item['available'] and item['metadata_system_origin'] and item['constraints_satisfied'] and item['python_satisfied'],
                    'normal_dependency_package_missing_or_wrong_origin')
        closure[name] = {key: item[key] for key in ('available', 'version', 'metadata_system_origin', 'constraints_satisfied', 'python_satisfied')}
    for name, item in value['direct'].items():
        require(type(item) is dict and all(type(item.get(key)) is bool for key in
            ('available', 'satisfies_requirement', 'loaded_module_present', 'module_system_origin')),
            'normal_direct_dependency_types_refused')
        require(item.get('version') == closure[name]['version'] and item['available'] == closure[name]['available']
                and item.get('origin_probe') in
            {'loaded_module', 'import_spec', 'unavailable'}, 'normal_direct_dependency_origin_refused')
        if complete:
            require(item['available'] and item['satisfies_requirement'] and item['module_system_origin']
                    and item['version'] == DIRECT[name] and item['origin_probe'] != 'unavailable'
                    and item['loaded_module_present'] == (item['origin_probe'] == 'loaded_module'),
                    'normal_direct_dependency_not_satisfied')
        direct[name] = {key: item[key] for key in ('available', 'version', 'satisfies_requirement',
                        'loaded_module_present', 'module_system_origin', 'origin_probe')}
    if complete:
        require(value.get('skip_pip') is False and value.get('closure_graph_checked') is True,
                'ordinary_requirements_or_closure_graph_refused')
    return {'schema': 1, 'core': CORE, 'python': '3.14.6', 'constraints_sha256': CONSTRAINTS_SHA,
            'constraints_match': True, 'docker_environment': True, 'ordinary_pip_target_unset': True,
            'config_deps_empty': True, 'direct': direct, 'closure': closure, 'closure_count': 24,
            'closure_graph_checked': value.get('closure_graph_checked') is True,
            'skip_pip': value.get('skip_pip') if type(value.get('skip_pip')) is bool else None,
            'provider_or_native_imports_requested_by_probe': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-zip', type=Path, required=True)
    parser.add_argument('--branch-commit', required=True)
    parser.add_argument('--output', type=Path, required=True)
    controller = Controller(parser.parse_args())
    def stopping(_signal, _frame):
        raise Refused('host_interrupted')
    signal.signal(signal.SIGTERM, stopping)
    signal.signal(signal.SIGHUP, stopping)
    signal.signal(signal.SIGINT, stopping)
    failure = None
    try:
        controller.run()
    except BaseException as error:
        failure = error
    return controller.finish(failure)


if __name__ == '__main__':
    raise SystemExit(main())
