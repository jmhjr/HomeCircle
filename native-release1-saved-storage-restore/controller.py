"""Native Linux KVM HAOS partial backup/Recorder restore with a disabled-entry gate.

This is a controller for one newly created guest. It does not connect to UTM,
SSH, an existing VM, a production Home Assistant, or a human GitHub account.
"""

from __future__ import annotations

from guard_transfer import decode as decode_guard, fingerprint as guard_fingerprint
from guard_transfer import export_failure_labels, parse_export_failure
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

from guard_context import Context, accept_contexts as accept_guard_contexts
from storage_context import Context as StorageContext, accept_contexts as accept_storage_contexts, digest_value


HAOS_URL = "https://github.com/home-assistant/operating-system/releases/download/18.3/haos_ova-18.3.qcow2.xz"
HAOS_XZ_SHA = "fae6a728768cc10aff60d4820bfcd40d64cd77fab82c8bd92af13b3d9d414090"
CANDIDATE_SHA = "004c9bc4a968ad395e18033837cb42f5bd1d8719a8d90fc778fd20be4ff08f97"
BRANCH = "codex/native-amd64-validation"
CORE = "2026.10.2"
HA = "/usr/bin/docker exec hassio_cli ha"
GUEST_ROOT = "/mnt/data/homecircle-safe-restore-qa"
CONTROL = "homecircle-safe-restore-qa-control"
RESULTS = "homecircle-safe-restore-qa-results"
PHASES = ("baseline_disabled", "mutated_disabled", "automatic_restored_disabled", "repaired_storage_disabled", "restart_disabled")
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
            r"[0-9]{4}\.[0-9]{1,2}\.[0-9]{1,2}", value)):
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


def public_entry_scope(value):
    """A finite count-only projection; unknown names and private fields never leave."""
    keys = {'total', 'domains', 'sources', 'system_entries_ready', 'entry_scope_allowed'}
    if type(value) is not dict or set(value) != keys or type(value['total']) is not int or not 0 <= value['total'] <= 16:
        return None
    for key, names in (('domains', {'homecircle', 'hassio', 'backup', 'analytics', 'other'}), ('sources', {'system', 'user', 'other'})):
        counts = value[key]
        if (type(counts) is not dict or set(counts) != names
                or any(type(x) is not int or not 0 <= x <= 16 for x in counts.values())
                or sum(counts.values()) != value['total']):
            return None
    if any(type(value[key]) is not bool for key in ('system_entries_ready', 'entry_scope_allowed')):
        return None
    return {'total': value['total'], 'domains': dict(value['domains']), 'sources': dict(value['sources']),
            'system_entries_ready': value['system_entries_ready'], 'entry_scope_allowed': value['entry_scope_allowed']}


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


FINGERPRINT_FIELDS = frozenset({'config_sha256', 'ledger_sha256', 'key_sha256', 'vault_sha256', 'payload_sha256', 'selection_sha256', 'credentials_sha256'})
RAW_STORAGE_FIELDS = FINGERPRINT_FIELDS - {"payload_sha256", "ledger_sha256"}
STORAGE_ACTIONS = ('seed', 'mutate', 'validate_restored', 'validate_restart')
STORAGE_CHECKS = {'seed': {'pair_matches_baseline': True, 'discriminating_mutation': False, 'no_op_pair_preserved': False, 'main_store_preserved': False, 'clones_removed': False, 'negative_cases': 0, 'selected_items': 2, 'deselected_commitments': 1, 'guard_counter': 2}, 'mutate': {'pair_matches_baseline': False, 'discriminating_mutation': True, 'no_op_pair_preserved': False, 'main_store_preserved': False, 'clones_removed': False, 'negative_cases': 0, 'selected_items': 2, 'deselected_commitments': 1, 'guard_counter': 3}, 'validate_restored': {'pair_matches_baseline': True, 'discriminating_mutation': False, 'no_op_pair_preserved': True, 'main_store_preserved': True, 'clones_removed': True, 'negative_cases': 18, 'selected_items': 2, 'deselected_commitments': 1, 'guard_counter': 3}, 'validate_restart': {'pair_matches_baseline': True, 'discriminating_mutation': False, 'no_op_pair_preserved': True, 'main_store_preserved': True, 'clones_removed': True, 'negative_cases': 18, 'selected_items': 2, 'deselected_commitments': 1, 'guard_counter': 3}}
COMMON_STORAGE_CHECKS = ('actual_fernet', 'account_identity_bound', 'selection_and_ledger_bound', 'pair_private', 'passwordless_session', 'config_snapshots_equal', 'baseline_proof_preserved')

def private_fingerprints(value):
    require(type(value) is dict and set(value) == FINGERPRINT_FIELDS
            and all(digest_value(item) for item in value.values()), "private_fingerprint_shape_refused")
    return dict(value)

def private_proof(value):
    require(type(value) is dict and set(value) == {"schema", "baseline", "mutation"}
            and type(value["schema"]) is int and value["schema"] == 1, "private_proof_shape_refused")
    return {"schema": 1, "baseline": private_fingerprints(value["baseline"]),
            "mutation": None if value["mutation"] is None else private_fingerprints(value["mutation"])}

STORAGE_FAILURE_STAGES = frozenset({"platform", "arguments", "job", "sources", "seed_preconditions", "seed",
    "mutation_preconditions", "mutation", "guard", "private_state", "restored_baseline", "consistency",
    "negative_cases", "no_op", "preservation", "result", "unrecognized"})

def project_storage_failure(result, action):
    # Retain only the source-bound fixed stage after a clean helper failure.
    if (type(action) is not str or action not in STORAGE_ACTIONS or type(result) is not dict
            or set(result) != {"exitcode", "signal", "stdout", "stderr", "truncated"}
            or type(result["exitcode"]) is not int or result["exitcode"] != 1
            or not (result["signal"] is None or type(result["signal"]) is int and result["signal"] == 0)
            or type(result["stderr"]) is not bytes or result["stderr"] != b""
            or result["truncated"] is not False or type(result["stdout"]) is not bytes
            or not 0 < len(result["stdout"]) <= 512):
        return None
    def unique_failure(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError
            value[key] = item
        return value
    try:
        value = json.loads(result["stdout"], object_pairs_hook=unique_failure)
    except (UnicodeError, ValueError, TypeError, RecursionError):
        return None
    if (type(value) is dict and set(value) == {"schema", "outcome", "stage"}
            and type(value["schema"]) is int and value["schema"] == 1
            and type(value["outcome"]) is str and value["outcome"] == "failed"
            and type(value["stage"]) is str and value["stage"] in STORAGE_FAILURE_STAGES):
        return {"schema": 1, "action": action, "stage": value["stage"]}
    return None

def project_storage_result(value, action):
    require(action in STORAGE_ACTIONS and type(value) is dict and set(value) == {"schema", "action", "outcome",
        "entry_disabled", "managed_candidate_imported", "synthetic_only", "source_files_verified", "storage_checks", "private_proof_written"},
        "storage_public_shape_refused")
    expected = {"schema": 1, "action": action, "outcome": "passed", "entry_disabled": True,
        "managed_candidate_imported": False, "synthetic_only": True, "source_files_verified": True,
        "private_proof_written": action in {"seed", "mutate"},
        "storage_checks": {**dict.fromkeys(COMMON_STORAGE_CHECKS, True), **STORAGE_CHECKS[action]}}
    require(type(value["schema"]) is int and value["schema"] == 1, "storage_public_schema_refused")
    require(type(value["storage_checks"]) is dict and set(value["storage_checks"]) == set(expected["storage_checks"]), "storage_checks_shape_refused")
    for key, wanted in expected.items():
        if key == "storage_checks":
            for name, check_value in wanted.items():
                require(type(value[key][name]) is type(check_value) and value[key][name] == check_value, "storage_check_refused")
        else:
            require(type(value[key]) is type(wanted) and value[key] == wanted, "storage_public_value_refused")
    return expected

def project_recorder(value):
    keys = {"ready", "prebackup_rows", "prebackup_sha256", "prebackup_exact_match", "postbackup_marker_rows",
            "postbackup_marker_absent", "postrestore_rows", "postrestore_sha256", "postrestore_exact_match",
            "integrity_ok", "backup_platform_registered", "commit_proven", "no_backup_failure_issue"}
    require(type(value) is dict and set(value) == keys, "recorder_shape_refused")
    for key in ("ready", "prebackup_exact_match", "integrity_ok", "backup_platform_registered", "commit_proven", "no_backup_failure_issue"):
        require(value[key] is True, "recorder_required_gate_refused")
    require(type(value["prebackup_rows"]) is int and 5 <= value["prebackup_rows"] <= 128
            and digest_value(value["prebackup_sha256"]) and type(value["postbackup_marker_rows"]) is int
            and 0 <= value["postbackup_marker_rows"] <= 128 and type(value["postbackup_marker_absent"]) is bool,
            "recorder_count_refused")
    require(value["postrestore_rows"] is None or type(value["postrestore_rows"]) is int and 5 <= value["postrestore_rows"] <= 128,
            "postrestore_count_refused")
    require(value["postrestore_sha256"] is None or digest_value(value["postrestore_sha256"]), "postrestore_digest_refused")
    require(value["postrestore_exact_match"] is None or type(value["postrestore_exact_match"]) is bool,
            "postrestore_boolean_refused")
    return dict(value)

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


def parse_core_container_state(result):
    """Only a successful daemon listing proves absence; errors remain unknown."""
    if not isinstance(result, dict) or type(result.get('exitcode')) is not int or result['exitcode'] != 0 \
            or result.get('signal') is not None or result.get('truncated') is not False \
            or result.get('stderr') != b'' or not isinstance(result.get('stdout'), bytes) \
            or len(result['stdout']) > 64 * 1024:
        return 'unknown'
    try:
        lines = result['stdout'].decode().splitlines()
        if len(lines) > 32:
            return 'unknown'
        records = []
        for line in lines:
            value = json.loads(line)
            if type(value) is not dict or set(value) != {'id', 'name', 'state'} \
                    or not isinstance(value['id'], str) or not re.fullmatch(r'[0-9a-f]{64}', value['id']) \
                    or not isinstance(value['name'], str) or len(value['name']) > 256 \
                    or not isinstance(value['state'], str):
                return 'unknown'
            names = [item.strip().removeprefix('/') for item in value['name'].split(',')]
            if 'homeassistant' in names:
                records.append(value)
    except (UnicodeError, ValueError, TypeError):
        return 'unknown'
    if not records:
        return 'not_created'
    if len(records) != 1:
        return 'unknown'
    return {'running': 'running', 'created': 'stopped', 'exited': 'stopped'}.get(records[0]['state'], 'unknown')


def verify_stored_image_chain(container, image, daemon, blobs):
    """Bind Docker29's index identity to the actual stored, pinned OCI config."""
    require(type(container) is dict and container.get('reference') == IMAGE_REFERENCE
            and container.get('image_id') == IMAGE_INDEX_DIGEST, 'minimum_container_index_identity_refused')
    require(type(daemon) is dict and daemon.get('Address') == CONTAINERD_ADDRESS
            and type(daemon.get('Namespaces')) is dict
            and daemon['Namespaces'].get('Containers') == CONTAINERD_NAMESPACE, 'minimum_containerd_location_refused')
    require(type(image) is dict and image.get('Id') == IMAGE_INDEX_DIGEST
            and image.get('Architecture') == 'amd64' and image.get('Os') == 'linux', 'minimum_image_platform_identity_refused')
    require(type(image.get('RepoTags')) is list and IMAGE_REFERENCE in image['RepoTags']
            and type(image.get('RepoDigests')) is list
            and IMAGE_REFERENCE.rsplit(':', 1)[0] + '@' + IMAGE_INDEX_DIGEST in image['RepoDigests'],
            'minimum_image_repository_binding_refused')
    descriptor = image.get('Descriptor')
    require(type(descriptor) is dict and descriptor.get('digest') == IMAGE_INDEX_DIGEST
            and descriptor.get('mediaType') == 'application/vnd.oci.image.index.v1+json'
            and descriptor.get('size') == IMAGE_OBJECTS['index'][1], 'minimum_image_descriptor_refused')
    require(type(blobs) is dict and set(blobs) == set(IMAGE_OBJECTS), 'minimum_stored_object_names_refused')
    objects = {}
    for label, (expected_digest, expected_size) in IMAGE_OBJECTS.items():
        raw = blobs[label]
        require(isinstance(raw, bytes) and len(raw) == expected_size
                and 'sha256:' + sha(raw) == expected_digest, 'minimum_stored_object_digest_refused')
        objects[label] = json.loads(raw)
        require(type(objects[label]) is dict, 'minimum_stored_object_schema_refused')
    index, manifest, config = (objects[name] for name in ('index', 'manifest', 'config'))
    require(index.get('schemaVersion') == 2 and index.get('mediaType') == 'application/vnd.oci.image.index.v1+json'
            and type(index.get('manifests')) is list, 'minimum_stored_index_schema_refused')
    selected = [item for item in index['manifests'] if type(item) is dict
                and item.get('platform') == {'os': 'linux', 'architecture': 'amd64'}]
    require(len(selected) == 1 and selected[0].get('digest') == IMAGE_MANIFEST_DIGEST
            and selected[0].get('size') == IMAGE_OBJECTS['manifest'][1]
            and selected[0].get('mediaType') == 'application/vnd.oci.image.manifest.v1+json',
            'minimum_stored_index_platform_link_refused')
    require(manifest.get('schemaVersion') == 2 and manifest.get('mediaType') == 'application/vnd.oci.image.manifest.v1+json'
            and type(manifest.get('config')) is dict and manifest['config'].get('digest') == IMAGE_CONFIG_ID
            and manifest['config'].get('size') == IMAGE_OBJECTS['config'][1]
            and manifest['config'].get('mediaType') == 'application/vnd.oci.image.config.v1+json',
            'minimum_stored_manifest_config_link_refused')
    require(config.get('architecture') == 'amd64' and config.get('os') == 'linux'
            and type(config.get('config')) is dict and type(config['config'].get('Labels')) is dict,
            'minimum_stored_config_platform_refused')
    labels = config['config']['Labels']
    require(all(labels.get(key) == value for key, value in {'io.hass.arch': 'amd64', 'io.hass.machine': 'qemux86-64',
                'io.hass.type': 'core', 'io.hass.version': CORE}.items()), 'minimum_stored_config_target_refused')
    rootfs = config.get('rootfs')
    require(type(rootfs) is dict, 'minimum_stored_rootfs_schema_refused')
    layers = rootfs.get('diff_ids')
    require(rootfs.get('type') == 'layers' and type(layers) is list and len(layers) == 22
            and all(isinstance(value, str) and re.fullmatch(r'sha256:[0-9a-f]{64}', value) for value in layers)
            and type(manifest.get('layers')) is list and len(manifest['layers']) == len(layers), 'minimum_stored_layer_schema_refused')
    require(type(image.get('RootFS')) is dict and image['RootFS'].get('Type') == 'layers'
            and image['RootFS'].get('Layers') == layers, 'minimum_image_rootfs_config_binding_refused')
    return {'reference': IMAGE_REFERENCE, 'identity_model': 'containerd_index_with_verified_stored_oci_chain',
            'observed_container_image_id': IMAGE_INDEX_DIGEST, 'observed_image_inspect_id': IMAGE_INDEX_DIGEST,
            'official_index_digest': IMAGE_INDEX_DIGEST, 'selected_manifest_digest': IMAGE_MANIFEST_DIGEST,
            'verified_oci_config_digest': IMAGE_CONFIG_ID, 'stored_objects_hashed': 3,
            'object_bytes': {name: value[1] for name, value in IMAGE_OBJECTS.items()},
            'containerd_address': CONTAINERD_ADDRESS, 'containerd_namespace': CONTAINERD_NAMESPACE,
            'platform': {'os': 'linux', 'architecture': 'amd64'}, 'rootfs_layers': 22,
            'image_rootfs_matches_verified_config': True, 'repository_digest_checked': True}


DEFAULT_API_CLIENT = 'set -eu\nset +x\n[ "$#" -eq 1 ] || exit 70\ncommand -v curl >/dev/null 2>&1 || exit 70\n[ -n "${SUPERVISOR_TOKEN:-}" ] || exit 70\ncase "$SUPERVISOR_TOKEN" in\n  *\'\n\'*|*\'\r\'*) exit 70 ;;\nesac\ncase "$1" in\n  info) endpoint=http://supervisor/jobs/info ;;\n  network) endpoint=http://supervisor/network/info ;;\n  *) exit 70 ;;\nesac\nprintf \'Authorization: Bearer %s\\nContent-Type: application/json\\n\' "$SUPERVISOR_TOKEN" |\n  curl -q --silent --show-error --fail --header @- --noproxy \'*\' --proto \'=http\' --proto-redir \'=http\' --max-redirs 0 --connect-timeout 3 --max-time 8 --request GET "$endpoint"\n'
JOB_OPTIONS_PERSISTENCE_PROGRAM = "import json,os,stat\nfrom pathlib import Path\npath=Path('/data/jobs.json')\nOWNER=0\ndef unique(pairs):\n    value={}\n    for key,item in pairs:\n        if key in value:raise ValueError\n        value[key]=item\n    return value\ndef identity(info):\n    return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_mode,info.st_uid,info.st_nlink)\nstate='refused'\nfd=None\ntry:\n    if os.geteuid()!=OWNER:raise ValueError\n    try:\n        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)\n    except FileNotFoundError:\n        state='absent'\n    else:\n        info=os.fstat(fd)\n        if not (stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_uid==OWNER\n                and stat.S_IMODE(info.st_mode) in {0o600,0o644} and 0<info.st_size<=16384):raise ValueError\n        raw=os.read(fd,16385)\n        after=os.fstat(fd)\n        current=path.lstat()\n        if identity(info)!=identity(after) or identity(after)!=identity(current) or not stat.S_ISREG(current.st_mode):raise ValueError\n        if not 0<len(raw)<=16384:raise ValueError\n        value=json.loads(raw,object_pairs_hook=unique)\n        if type(value)is not dict or set(value)!={'ignore_conditions'} or type(value['ignore_conditions'])is not list:raise ValueError\n        conditions=value['ignore_conditions']\n        if any(type(item)is not str for item in conditions):raise ValueError\n        if conditions==[]:state='empty'\n        elif conditions==['internet_host','internet_system']:state='owned_two'\n        else:state='foreign'\nexcept (OSError,ValueError,TypeError,UnicodeError,RecursionError):\n    pass\nfinally:\n    if fd is not None:os.close(fd)\nprint(json.dumps({'schema':1,'state':state},sort_keys=True))\n"
OFFLINE_INTERNET_CONDITIONS = ["internet_host", "internet_system"]
DEFAULT_RECEIPT_BOOL_KEYS = frozenset({'network_open_positive_control', 'supervisor_internet_true', 'candidate113_archive_verified', 'final_effective_empty_observed', 'original_persisted_empty_or_absent', 'cleanup_failed', 'original_effective_empty', 'network_close_acknowledged', 'restore_completed', 'foreign_options_refused', 'closed_boot_grant_written', 'cached_same_core_image_verified_before', 'cached_same_core_image_verified_after', 'network_open_acknowledged', 'network_closed_before', 'network_closed_after', 'final_persisted_empty_or_absent', 'disabled_unimported_config_verified', 'supervisor_host_internet_true', 'relevant_visible_jobs_idle_before'})

def new_default_receipt():
    result = {key: False for key in DEFAULT_RECEIPT_BOOL_KEYS}
    result.update(schema=1, mode="default_conditions_disabled_saved_storage", jobs_option_mutation_requests=0,
        global_persisted_override=False, unsupported_conditions_override=False,
        network_open_requests=0, network_close_requests=0, network_info_requests=0,
        maximum_cleanup_seconds=90, maximum_network_readiness_seconds=90)
    return result

def project_default_receipt(value, complete=False):
    expected = new_default_receipt()
    require(type(value) is dict and set(value) == set(expected) and type(value['schema']) is int and value['schema'] == 1
        and value['mode'] == 'default_conditions_disabled_saved_storage'
        and value['global_persisted_override'] is False and value['unsupported_conditions_override'] is False
        and type(value['jobs_option_mutation_requests']) is int and value['jobs_option_mutation_requests'] == 0
        and all(type(value[key]) is bool for key in DEFAULT_RECEIPT_BOOL_KEYS)
        and type(value['maximum_cleanup_seconds']) is int and value['maximum_cleanup_seconds'] == 90
        and type(value['maximum_network_readiness_seconds']) is int and value['maximum_network_readiness_seconds'] == 90,
        'default_conditions_receipt_refused')
    for key in ('network_open_requests','network_close_requests','network_info_requests'):
        require(type(value[key]) is int and 0 <= value[key] <= (18 if key == 'network_info_requests' else 1), 'default_conditions_receipt_refused')
    if complete:
        require(all(value[key] is (key not in {'foreign_options_refused','cleanup_failed'}) for key in DEFAULT_RECEIPT_BOOL_KEYS)
            and value['network_open_requests'] == value['network_close_requests'] == 1
            and 1 <= value['network_info_requests'] <= 18, 'default_conditions_complete_proof_required')
    return dict(value)

def offline_jobs_info(raw):
    def unique(pairs):
        result = {}
        for key, item in pairs:
            require(key not in result, "offline_options_duplicate_key_refused")
            result[key] = item
        return result
    require(type(raw) is bytes and 0 < len(raw) <= 2 * 1024**2, "offline_options_response_refused")
    value = json.loads(raw, object_pairs_hook=unique)
    require(type(value) is dict and value.get("result") == "ok" and type(value.get("data")) is dict
            and set(value["data"]) == {"ignore_conditions", "jobs"}, "offline_options_response_refused")
    ignored = value["data"]["ignore_conditions"]
    require(type(ignored) is list and len(ignored) <= 64 and all(type(item) is str for item in ignored),
            "offline_options_response_refused")
    state = "empty" if ignored == [] else "owned_two" if ignored == OFFLINE_INTERNET_CONDITIONS else "foreign"
    jobs = public_jobs(value)
    idle = not any(job["name"] in BACKUP_DIAGNOSTIC_JOBS and job["done"] is not True for job in jobs)
    return state, idle

def offline_api_ack(result, info=False):
    if (type(result) is not dict or set(result) != {"exitcode", "signal", "stdout", "stderr", "truncated"}
            or type(result.get("exitcode")) is not int or result["exitcode"] != 0
            or not (result.get("signal") is None or type(result.get("signal")) is int and result["signal"] == 0)
            or result.get("truncated") is not False or type(result.get("stderr")) is not bytes or result["stderr"] != b""
            or type(result.get("stdout")) is not bytes or not 0 < len(result["stdout"]) <= (2 * 1024**2 if info else 65536)):
        return False
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value: raise ValueError
            value[key] = item
        return value
    try:
        value = json.loads(result["stdout"], object_pairs_hook=unique)
    except (UnicodeError, ValueError, TypeError, RecursionError):
        return False
    return (type(value) is dict and set(value) == {"result", "data"} and value["result"] == "ok"
            and type(value["data"]) is dict and (info or value["data"] == {}))


def source_failure_catalog():
    """Finite literal labels from only these reviewed, hash-bound QA sources."""
    paths = (ROOT / 'controller.py', ROOT / 'reset_fresh_config.py',
             ROOT / 'guest_helper/homecircle_safe_restore_qa/__init__.py',
             ROOT / 'guest_helper/homecircle_safe_restore_qa/dependency_probe.py', ROOT/'guard_transfer.py', ROOT/'storage_context.py', ROOT/'storage_transfer.py')
    codes, stages = set(), set(PHASES) | {"supervisor_partial_create", "supervisor_partial_restore"}
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


def source_setup_catalog():
    """Read only the literal diagnostic catalog from the frozen helper source."""
    tree = ast.parse((ROOT / 'guest_helper/homecircle_safe_restore_qa/__init__.py').read_bytes())
    values = [node.value for node in tree.body if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == 'SETUP_STEPS' for target in node.targets)]
    require(len(values) == 1 and isinstance(values[0], ast.Call)
            and isinstance(values[0].func, ast.Name) and values[0].func.id == 'frozenset'
            and len(values[0].args) == 1 and not values[0].keywords, 'setup_catalog_refused')
    labels = ast.literal_eval(values[0].args[0])
    require(type(labels) is set and 1 <= len(labels) <= 32
            and all(type(item) is str and re.fullmatch(r'[a-z_]{1,40}', item) for item in labels),
            'setup_catalog_refused')
    return frozenset(labels)


def public_guard_export(value):
    keys = {'exit_code', 'signal', 'output_truncated', 'stdout_present', 'stderr_present', 'helper_failure'}
    if type(value) is not dict or set(value) != keys or type(value['output_truncated']) is not bool:
        return None
    code, signal_value = value['exit_code'], value['signal']
    if not (type(code) is int and 0 <= code <= 255 and signal_value is None
            or code is None and type(signal_value) is int and 1 <= signal_value <= 64):
        return None
    for key in ('stdout_present', 'stderr_present'):
        if value['output_truncated']:
            if value[key] is not None:
                return None
        elif type(value[key]) is not bool:
            return None
    labels = value['helper_failure']
    if labels is not None:
        labels = export_failure_labels(labels)
        if labels is None:
            return None
    return {key: labels if key == 'helper_failure' else value[key] for key in (
        'exit_code', 'signal', 'output_truncated', 'stdout_present', 'stderr_present', 'helper_failure')}


def guard_export_observation(result, token):
    if type(result) is not dict or set(result) != {'exitcode', 'signal', 'stdout', 'stderr', 'truncated'} \
            or type(result['stdout']) is not bytes or type(result['stderr']) is not bytes \
            or type(result['truncated']) is not bool:
        return None
    return public_guard_export({'exit_code': result['exitcode'], 'signal': result['signal'],
        'output_truncated': result['truncated'],
        'stdout_present': None if result['truncated'] else bool(result['stdout']),
        'stderr_present': None if result['truncated'] else bool(result['stderr']),
        'helper_failure': None if result['truncated'] else parse_export_failure(result['stderr'], token)})


def public_person_sources(value):
    """Only two fixed indices and strict boolean observations may leave QA."""
    fields = ('person_present', 'tracker_present', 'person_home', 'tracker_home',
              'source_matches_selected', 'configured_link_matches_selected')
    if type(value) is not dict or set(value) != {'0', '1'}:
        return None
    result = {}
    for index in ('0', '1'):
        row = value[index]
        if type(row) is not dict or set(row) != set(fields) \
                or any(type(row[field]) is not bool for field in fields):
            return None
        result[index] = {field: row[field] for field in fields}
    return result


def public_setup_step(value):
    return value if type(value) is str and value in SETUP_STEPS else None


def failure_projection(value):
    stage, kind, code = value.get('stage'), value.get('failure_type'), value.get('failure_code')
    return {'stage': stage if isinstance(stage, str) and stage in FAILURE_STAGES else 'unrecognized_stage',
            'failure_type': kind if isinstance(kind, str) and kind in FAILURE_TYPES else 'unrecognized_failure_type',
            'failure_code': code if isinstance(code, str) and code in FAILURE_CODES else None}


def checked_reset(value):
    require(type(value) is dict and set(value) == {'files', 'bytes', 'children', 'owner_accounts_found',
        'candidate_previously_present', 'fresh_config_reset', 'mount_directory_preserved'}, 'fresh_reset_projection_refused')
    for key, upper in (('files', 8192), ('bytes', 64 * 1024**2), ('children', 128)):
        require(type(value[key]) is int and 0 <= value[key] <= upper, 'fresh_reset_bounds_refused')
    require(value['owner_accounts_found'] is False and value['candidate_previously_present'] is False
            and value['fresh_config_reset'] is True and value['mount_directory_preserved'] is True,
            'fresh_reset_proof_refused')
    return dict(value)


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

SOURCE_COMMIT = "91ae59106a661143b770d7a3564d363c7c11a7dd"

CONSTRAINTS_SHA = "7baa9a8f39ddeb9c5bb60a1036f6d5e33f4b84267f151f53cc2b95ef031a21b5"

IMAGE_REFERENCE = "ghcr.io/home-assistant/qemux86-64-homeassistant:2026.10.2"

IMAGE_INDEX_DIGEST = "sha256:45f009d6ff1061971102e81f0802cf2762bdd5c5007231c938bd36030cbd0a12"

IMAGE_CONFIG_ID = "sha256:e1acee126eee45b3007494ad7f806d12535dc7d733624b681ed29a505f8c2b98"

IMAGE_MANIFEST_DIGEST = "sha256:e2efc1351b54b15dd3232fc9987316aa3e3cb22c15e6e369e73fd595b4338f2c"

IMAGE_OBJECTS = {'index': (IMAGE_INDEX_DIGEST, 856), 'manifest': (IMAGE_MANIFEST_DIGEST, 4488),
                 'config': (IMAGE_CONFIG_ID, 11042)}

CONTAINERD_ADDRESS = '/run/containerd/containerd.sock'

CONTAINERD_NAMESPACE = 'moby'

DIRECT = {'life360': '7.2.0', 'protobuf': '7.36.0', 'anisette': '1.2.4',
          'unicorn': '2.1.4', 'srp': '1.0.22', 'beautifulsoup4': '4.13.3'}

CLOSURE = frozenset(('aiohappyeyeballs', 'aiohttp', 'aiosignal', 'anisette', 'appdirs', 'attrs',
    'beautifulsoup4', 'certifi', 'frozenlist', 'fs', 'idna', 'life360', 'multidict', 'propcache',
    'protobuf', 'pyelftools', 'setuptools', 'six', 'soupsieve', 'srp', 'typing-extensions',
    'unicorn', 'urllib3', 'yarl'))


SETUP_STEPS = source_setup_catalog()
FAILURE_CODES, FAILURE_STAGES = source_failure_catalog()
FAILURE_TYPES = frozenset({"Refused", "RuntimeError", "OSError", "ValueError", "TypeError", "AttributeError", "KeyError", "JSONDecodeError", "TimeoutError", "TimeoutExpired", "FileNotFoundError", "PermissionError", "ImportError", "ModuleNotFoundError", "PackageNotFoundError", "ClientError", "ClientConnectorError", "ClientResponseError", "CancelledError"})

def guest_staging_owner(info):
    """Normalize only the fresh owned guest staging archive's ownership."""
    require(type(info) is tarfile.TarInfo, 'owned_staging_member_refused')
    path = PurePosixPath(info.name)
    require(info.name == path.as_posix() and not path.is_absolute() and '..' not in path.parts
            and path.parts and path.parts[0] == 'custom_components'
            and (info.isfile() or info.isdir()), 'owned_staging_member_refused')
    info.uid = info.gid = 0
    info.uname = info.gname = ''
    info.pax_headers = {key: value for key, value in info.pax_headers.items()
                        if key not in {'uid', 'gid', 'uname', 'gname'}}
    return info


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
            self.host_guard = None
            self.host_guard_retained = False
            self.guard_repaired = False
            self.repaired_disabled = False
            self.network_boundary = {"link_closed": False}
            self.network_transitions = []
            self.qmp_path = None
            self.cli_capabilities = None
            self.reset_receipt = None
            self.target_environment = None
            self.minimum_core_image = None
            self.version_change_requests = 0
            self.backup_guard_sha256 = None
            self.after_restore_barrier = False
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
            self.guard_transfer_contexts = []
            self.storage_contexts = []
            self.storage_results = {}
            self.storage_proof = None
            self.joins_sha256 = None
            self.raw_phase_receipts = {}
            self.default_restore_conditions = None

    def core_container_state(self, timeout):
        # Docker's documented name filter is a substring match; the parser
        # selects the exact canonical name and exports only one finite state.
        command = "/usr/bin/docker container ls --all --no-trunc --filter name=homeassistant --format " \
            + "'{\"id\":{{json .ID}},\"name\":{{json .Names}},\"state\":{{json .State}}}'"
        return parse_core_container_state(self.guest(command, timeout, capture=True))

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

    def actual_core_image(self):
        self.stage = 'minimum_core_image_content_identity'
        container = json.loads(self.guest("/usr/bin/docker inspect homeassistant --format "
            + "'{\"reference\":{{json .Config.Image}},\"image_id\":{{json .Image}}}'", 20))
        image = json.loads(self.guest('/usr/bin/docker image inspect ' + IMAGE_REFERENCE + ' --format '
            + "'{\"Id\":{{json .Id}},\"RepoTags\":{{json .RepoTags}},\"RepoDigests\":{{json .RepoDigests}},"
              "\"Architecture\":{{json .Architecture}},\"Os\":{{json .Os}},\"RootFS\":{{json .RootFS}},"
              "\"Descriptor\":{{json .Descriptor}}}'", 20))
        daemon = json.loads(self.guest("/usr/bin/docker info --format '{{json .Containerd}}'", 20))
        require(type(daemon) is dict and daemon.get('Address') == CONTAINERD_ADDRESS
                and type(daemon.get('Namespaces')) is dict
                and daemon['Namespaces'].get('Containers') == CONTAINERD_NAMESPACE, 'minimum_containerd_location_refused')
        blobs = {name: self.guest('/usr/bin/ctr --address ' + CONTAINERD_ADDRESS + ' --namespace '
                                 + CONTAINERD_NAMESPACE + ' content get ' + value[0], 20)
                 for name, value in IMAGE_OBJECTS.items()}
        return verify_stored_image_chain(container, image, daemon, blobs)

    def observe_dependencies(self):
        script = (ROOT / 'guest_helper/homecircle_safe_restore_qa/dependency_probe.py').read_bytes()
        self.guest_write(GUEST_ROOT + '/observe-dependencies.py', script)
        return json.loads(self.guest('/usr/bin/docker exec -i homeassistant python3 -B - < '
                                    + GUEST_ROOT + '/observe-dependencies.py', 60))

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

    def reopen_after_repaired_disabled(self):
        self.stage = 'network_reopen_after_guard'
        require(self.guard_repaired and self.repaired_disabled and len(self.phases) == 6
                and self.network_boundary['link_closed'] is True
                and self.phases[-1]['phase'] == 'repaired_disabled'
                and self.guard_fingerprint(self.config_path+'/.storage/homecircle_findmy/recovery_guard') == self.latest_guard_sha256,
                'network_reopen_before_guard_refused')
        deadline = time.monotonic()+self.remaining(30)
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
            connection.settimeout(10)
            connection.connect(str(self.qmp_path))
            stream = connection.makefile('rwb',buffering=0)
            require('QMP' in json.loads(stream.readline(65536)), 'qmp_reopen_greeting_refused')
            for identifier,execute,arguments in [('caps','qmp_capabilities',None),('reopen','set_link',{'name':'qa-net0','up':True})]:
                request={'execute':execute,'id':identifier}
                if arguments is not None:request['arguments']=arguments
                stream.write(canonical(request)+b'\n')
                for _ in range(32):
                    require(time.monotonic()<deadline,'network_reopen_deadline')
                    connection.settimeout(min(10,deadline-time.monotonic()))
                    response=json.loads(stream.readline(65536))
                    if response.get('id')==identifier:
                        require(response.get('return')=={} and 'error' not in response,'network_reopen_refused')
                        break
                else:raise Refused('network_reopen_response_count')
        self.network_boundary['link_closed']=False
        require(self.connectivity_probe() is True,'reopened_network_positive_control_required')
        self.network_transitions.append('reopen_after_repaired_disabled')

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
        argv = ["qemu-system-x86_64", "-name", "homecircle-safe-restore-qa-" + self.nonce,
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
                  "relevant_core_jobs_idle": False, "running_before": None, "running_after": None,
                  "container_state_before": None, "container_state_after": None}
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
        before = self.core_container_state(min(10, deadline - time.monotonic()))
        record['container_state_before'] = before
        record['running_before'] = {'running': True, 'stopped': False}.get(before)
        expected = action == "start"
        require(before in ({'stopped', 'not_created'} if expected else {'running'}), "core_action_initial_state_refused")
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
                after = self.core_container_state(min(10, deadline - time.monotonic()))
                record['container_state_after'] = after
                record['running_after'] = {'running': True, 'stopped': False}.get(after)
                if after == ('running' if expected else 'stopped') and time.monotonic() < deadline:
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
            self.guest("set -eu; test -d " + GUEST_ROOT + "; test ! -L " + GUEST_ROOT
                       + "; test \"$(stat -c '%u:%a' " + GUEST_ROOT + ")\" = 0:700", 30)
            staging = self.private / "guest-staging"
            staging.mkdir(mode=0o700)
            components = staging / "custom_components"
            components.mkdir()
            shutil.copytree(ROOT / "guest_helper/homecircle_safe_restore_qa", components / "homecircle_safe_restore_qa",
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
            with zipfile.ZipFile(self.args.candidate_zip) as archive:
                archive.extractall(components / "homecircle")
            archive_path = self.private / "guest-staging.tgz"
            with tarfile.open(archive_path, "w:gz", format=tarfile.PAX_FORMAT) as archive:
                archive.add(components, arcname="custom_components", filter=guest_staging_owner)
            data = archive_path.read_bytes()
            self.guest_write(GUEST_ROOT + "/staging.tgz", data)
            require(self.guest("sha256sum " + GUEST_ROOT + "/staging.tgz", 30).split()[0].decode() == sha(data),
                    "guest_transport_pin_refused")
            self.guest("set -eu; umask 077; tar -xzf " + GUEST_ROOT + "/staging.tgz -C " + self.config_path
                       + "; mkdir -m 700 " + self.config_path + "/" + CONTROL + " "
                       + self.config_path + "/" + RESULTS, 60)
            self.inputs = {"schema": 1, "candidate_sha256": CANDIDATE_SHA,
                           "candidate_inventory": candidate_inventory, "core_version": CORE,
                           "branch_commit": self.args.branch_commit, "generation": self.generation, "source_commit": SOURCE_COMMIT,
                           "storage_source_sha256": {name: candidate_inventory[name]["sha256"] for name in
                               ("findmy_vault.py", "findmy_identity.py", "findmy_recovery_guard.py")}}
            self.guest_write(self.config_path + "/" + CONTROL + "/inputs.json", canonical(self.inputs))
            config = {"homeassistant": {"name": "Disposable HomeCircle Backup QA", "latitude": 0.0,
                                       "longitude": 0.0, "elevation": 0, "unit_system": "metric", "time_zone": "UTC"},
                      "frontend": {}, "http": {}, "lovelace": {}, "person": {}, "zone": [{"name":"Example Saved Storage","latitude":0.01,"longitude":0.01,"radius":50}],
                      "websocket_api": {}, "image_upload": {}, "backup": {}, "recorder": {}, "hassio": {},
                      "homecircle_safe_restore_qa": {"disposable": True}}
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
        require(len(self.phases) < len(PHASES) and name == PHASES[len(self.phases)]
                and name != "automatic_restored_disabled", "phase_order_refused")
        self.assert_network_closed()
        self.stage = name
        instruction = {"schema": 1, "token": self.phase_token, "phase": name, "generation": self.generation,
                       "branch_commit": self.args.branch_commit}
        control = self.config_path + "/" + CONTROL
        temporary = control + "/.phase-" + self.phase_token + "-" + name
        self.guest_write(temporary, canonical(instruction))
        self.guest("set -eu; chmod 600 " + temporary + "; mv " + temporary + " " + control + "/phase.json", 30)
        if start:
            self.start_core()
        self.grant_closed_boot(name)
        limit = time.monotonic() + self.remaining(660)
        while time.monotonic() < limit:
            try:
                content = self.guest_read(self.config_path + "/" + RESULTS + "/" + name + ".json")
            except (Refused, OSError, ValueError):
                time.sleep(2)
                continue
            receipt = json.loads(content)
            require(type(receipt) is dict and receipt.get("schema") == 1 and receipt.get("token") == self.phase_token
                    and receipt.get("phase") == name and receipt.get("generation") == self.generation
                    and receipt.get("branch_commit") == self.args.branch_commit, "phase_receipt_identity_refused")
            if receipt.get("outcome") != "passed":
                failure = {"schema": 1, "phase": name, "outcome": "failed"}
                failure.update(failure_projection(receipt))
                write_json(self.public / (name + ".json"), failure)
                raise Refused("guest_acceptance_failed")
            if name in {"repaired_storage_disabled", "restart_disabled"}:
                self.stop_core()
                self.run_storage_context("validate_restored" if name == "repaired_storage_disabled" else "validate_restart")
            public = self.accept_phase(name, receipt)
            self.raw_phase_receipts[name] = receipt
            write_json(self.public / (name + ".json"), public)
            self.phases.append(public)
            self.assert_network_closed()
            return
        raise Refused("phase_receipt_deadline_exceeded")

    def accept_phase(self, name, receipt):
        require(type(receipt) is dict and receipt.get("core_version") == CORE
                and receipt.get("candidate_archive_sha256") == CANDIDATE_SHA
                and receipt.get("entry_disabled") is True and receipt.get("entry_loaded") is False
                and receipt.get("candidate_imported") is False and receipt.get("ha_config_entry_saved") is True and receipt.get("closed_boot_grant_verified") is True and receipt.get("owner_accounts_used") is False
                and receipt.get("production_configuration_used") is False
                and receipt.get("provider_request_attempt_counts_measured") is False
                and receipt.get("recovery_proof_attempt_counts_measured") is False, "phase_fixture_scope_refused")
        require(receipt.get("package_files_count") == 113
                and receipt.get("package_payload_sha256") == sha(canonical(self.inventories["candidate"]))
                and receipt.get("nonempty_options") is True and receipt.get("nonempty_place") is True,
                "phase_package_projection_refused")
        process = receipt.get("process")
        require(type(process) is dict and set(process) == {"pid", "start_ticks"}
                and all(type(value) is int and value > 0 for value in process.values()), "phase_process_identity_refused")
        if self.phases:
            require(process["start_ticks"] > self.phases[-1]["process"]["start_ticks"], "distinct_disabled_process_required")
        expected = self.storage_proof["mutation"] if name == "mutated_disabled" else self.storage_proof["baseline"]
        observed = receipt.get("observed_storage")
        require(type(observed) is dict and set(observed) == RAW_STORAGE_FIELDS
                and all(observed[key] == expected[key] for key in RAW_STORAGE_FIELDS), "raw_saved_storage_refused")
        joins = receipt.get("joins_sha256")
        require(digest_value(joins), "registry_joins_fingerprint_refused")
        if name == "baseline_disabled":
            self.joins_sha256 = joins
            self.backup_guard_sha256 = receipt.get("guard_sha256")
        elif name == "mutated_disabled":
            require(joins != self.joins_sha256, "registry_mutation_missing")
            self.latest_guard_sha256 = receipt.get("guard_sha256")
            require(self.latest_guard_sha256 != self.backup_guard_sha256, "newest_guard_not_distinct")
        else:
            require(joins == self.joins_sha256 and self.after_restore_barrier and self.guard_repaired,
                    "restored_registry_identity_changed")
        require(digest_value(receipt.get("guard_sha256"))
                and receipt["guard_sha256"] == (self.backup_guard_sha256 if name == "baseline_disabled" else self.latest_guard_sha256),
                "phase_guard_bytes_refused")
        record = project_recorder(receipt.get("recorder"))
        if self.phases:
            initial = self.phases[0]["recorder"]
            require(record["prebackup_rows"] == initial["prebackup_rows"]
                    and record["prebackup_sha256"] == initial["prebackup_sha256"], "prebackup_history_changed")
        if name == "mutated_disabled":
            require(record["postbackup_marker_rows"] > 0 and record["postbackup_marker_absent"] is False,
                    "postbackup_mutation_missing")
        else:
            require(record["postbackup_marker_rows"] == 0 and record["postbackup_marker_absent"] is True,
                    "postbackup_rows_not_removed")
        if name in {"repaired_storage_disabled", "restart_disabled"}:
            require(record["postrestore_exact_match"] is True and type(record["postrestore_rows"]) is int
                    and record["postrestore_rows"] > 0, "postrestore_history_missing")
            if name == "restart_disabled":
                before = self.phases[3]["recorder"]
                require(record["postrestore_rows"] == before["postrestore_rows"]
                        and record["postrestore_sha256"] == before["postrestore_sha256"], "postrestore_restart_changed")
        if name == "repaired_storage_disabled":
            self.repaired_disabled = True
        return {"schema": 1, "phase": name, "generation": self.generation, "outcome": "passed",
                "entry_disabled": True, "entry_loaded": False, "candidate_imported": False, "ha_config_entry_saved": True, "closed_boot_grant_verified": True, "process": process,
                "package_files_count": 113, "package_payload_sha256": sha(canonical(self.inventories["candidate"])),
                "storage_raw_matches_expected": True, "explicit_registry_joins_checked": True,
                "selected_registry_joins": 4, "nonempty_options": True, "nonempty_place": True,
                "guard_counter": 2 if name == "baseline_disabled" else 3,
                "guard_repaired_before_storage_load": name in {"repaired_storage_disabled", "restart_disabled"},
                "recorder": record, "provider_request_attempt_counts_measured": False,
                "recovery_proof_attempt_counts_measured": False}

    def backup_cli_capabilities(self):
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
                       " --uncompressed --location=.local --name HomeCircleBackupQA --filename homecircle-safe-restore-qa.tar")
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
            self.restore = {"result": "ok", "job": status, "disabled_entry_gate_required": True}
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
        self.stage = "supervisor_saved_storage_archive_proof"
        require(self.storage_proof is not None and self.storage_proof["mutation"] is None
                and self.joins_sha256 is not None, "baseline_before_archive_required")
        script = 'import hashlib,json,re,tarfile\nfrom pathlib import Path,PurePosixPath\n\ndef require(ok):\n    if not ok: raise RuntimeError("saved_storage_archive_refused")\ndef sha(data): return hashlib.sha256(data).hexdigest()\ndef canonical(data): return json.dumps(data,sort_keys=True,separators=(",",":")).encode()\nexpected=__BASELINE__\nexpected_joins=__JOINS__\nroot=Path("/data/homeassistant")\ninputs=json.loads((root/"homecircle-safe-restore-qa-control/inputs.json").read_bytes())\npath=Path("/data/backup/homecircle-safe-restore-qa.tar")\nrequire(path.is_file() and not path.is_symlink() and 0<path.stat().st_size<=128*1024**2)\npackage,guard,pairs,private={}, {}, {}, {}\nentry=selection=registry=None\ndb=False\nwith tarfile.open(path,"r:") as outer:\n    members=outer.getmembers()\n    require(len(members)<=16 and all(not PurePosixPath(m.name).is_absolute() and ".." not in PurePosixPath(m.name).parts for m in members))\n    inner=[m for m in members if m.name.removeprefix("./")=="homeassistant.tar"]\n    require(len(inner)==1 and inner[0].isfile() and inner[0].size<=128*1024**2)\n    with outer.extractfile(inner[0]) as stream,tarfile.open(fileobj=stream,mode="r|") as archive:\n        count,total=0,0\n        for member in archive:\n            count+=1\n            require(count<=16384 and member.size<=64*1024**2)\n            name=member.name.removeprefix("./")\n            require(not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts and not member.issym() and not member.islnk())\n            require(name not in {"data/homecircle-safe-restore-qa-control/restore-barrier.json", "data/homecircle-safe-restore-qa-control/closed-boot-grant.json", "data/homecircle-safe-restore-qa-control/closed-boot-grant.tmp"})\n            if not member.isfile(): continue\n            total+=member.size\n            require(total<=256*1024**2)\n            with archive.extractfile(member) as content:data=content.read(64*1024**2+1)\n            require(len(data)==member.size)\n            prefix="data/custom_components/homecircle/"\n            if name.startswith(prefix) and "__pycache__" not in name and not name.endswith(".pyc"):\n                package[name[len(prefix):]]={"bytes":len(data),"sha256":sha(data)}\n            prefix="data/.storage/homecircle_findmy/recovery_guard/"\n            if name.startswith(prefix):guard[name[len(prefix):]]={"bytes":len(data),"sha256":sha(data)}\n            if name.startswith("data/.storage/homecircle_findmy/homecircle_accounts/"):\n                require(re.fullmatch(r"data/[.]storage/homecircle_findmy/homecircle_accounts/[0-9a-f]{32}/session[.](?:key|vault)",name)\n                        and member.mode==0o600 and member.uid==0 and name not in pairs)\n                pairs[name]=sha(data)\n            if name=="data/.storage/core.config_entries":\n                entries=json.loads(data)["data"]["entries"]\n                found=[e for e in entries if e.get("domain")=="homecircle"]\n                require(len(found)==1 and found[0].get("disabled_by")=="user" and found[0].get("title")=="Synthetic saved storage verified")\n                entry=found[0]\n            if name=="data/.storage/core.entity_registry":registry=json.loads(data)["data"]["entities"]\n            if name=="data/homecircle-safe-restore-qa-control/storage-selection-private.json":selection=json.loads(data)\n            if name=="data/home-assistant_v2.db":\n                require(data[:16]==b"SQLite format 3\\x00" and len(data)>4096);db=True\nrequire(package==inputs["candidate_inventory"] and entry is not None and db and guard and selection is not None and type(registry)is list)\nrequire(entry["data"]==entry["options"] and sha(canonical({"data":entry["data"],"options":entry["options"]}))==expected["config_sha256"])\nrequire(sha(canonical(entry["options"]["life360_account"]))==expected["credentials_sha256"] and sha(canonical(selection))==expected["selection_sha256"])\nrequire(type(selection)is dict and set(selection)=={"schema","entry_id","joins"} and selection["schema"]==1 and selection["entry_id"]==entry["entry_id"]\n        and type(selection["joins"])is list and len(selection["joins"])==4)\nselected=sorted([{k:v[k] for k in ("entity_id","unique_id","config_entry_id")} for v in selection["joins"]],key=lambda x:x["entity_id"])\nrequire(len({v["entity_id"] for v in selected})==len({v["unique_id"] for v in selected})==4 and all(v["config_entry_id"]==entry["entry_id"] for v in selected))\nactual=sorted([{k:v.get(k) for k in ("entity_id","unique_id","config_entry_id")} for v in registry if v.get("entity_id") in {j["entity_id"] for j in selected}],key=lambda x:x["entity_id"])\nrequire(actual==selected and sha(canonical(actual))==expected_joins)\naccounts=entry["options"]["findmy_accounts"]\nrequire(type(accounts)is dict and len(accounts)==1)\nstorage_id=next(iter(accounts.values()))["storage_id"]\nrequire(type(storage_id)is str and re.fullmatch("[0-9a-f]{32}",storage_id))\nprefix="data/.storage/homecircle_findmy/homecircle_accounts/"+storage_id+"/"\nrequire(pairs=={prefix+"session.key":expected["key_sha256"],prefix+"session.vault":expected["vault_sha256"]})\nprint(json.dumps({"archive_bytes":path.stat().st_size,"database_included":True,"candidate_match":True,"disabled_entry":True,\n    "saved_pair_included":True,"saved_config_included":True,"saved_selection_included":True,"saved_registry_joins_included":True,\n    "guard_sha256":sha(canonical(guard))},sort_keys=True))\n\n'
        script = script.replace("__BASELINE__", repr(self.storage_proof["baseline"])).replace("__JOINS__", repr(self.joins_sha256))
        self.guest_write(GUEST_ROOT + "/inspect-backup.py", script.encode())
        value = json.loads(self.guest("/usr/bin/docker exec -i hassio_supervisor python3 - < " + GUEST_ROOT + "/inspect-backup.py", 120))
        keys = {"archive_bytes", "database_included", "candidate_match", "disabled_entry", "saved_pair_included",
                "saved_config_included", "saved_selection_included", "saved_registry_joins_included", "guard_sha256"}
        require(type(value) is dict and set(value)==keys and all(value[key] is True for key in keys-{"archive_bytes","guard_sha256"})
                and value["guard_sha256"]==self.backup_guard_sha256 and type(value["archive_bytes"])is int
                and 0<value["archive_bytes"]<=128*1024**2, "saved_storage_archive_proof_refused")
        self.backup["archive"] = value

    def run_guard_transfer(self, action, arguments=()):
        require(self.config_path == '/mnt/data/supervisor/homeassistant'
                and self.minimum_core_image['official_index_digest'] == 'sha256:45f009d6ff1061971102e81f0802cf2762bdd5c5007231c938bd36030cbd0a12'
                and self.minimum_core_image['verified_oci_config_digest'] == 'sha256:e1acee126eee45b3007494ad7f806d12535dc7d733624b681ed29a505f8c2b98'
                and self.minimum_core_image['stored_objects_hashed'] == 3
                and self.minimum_core_image['image_rootfs_matches_verified_config'] is True
                and [record['action'] for record in self.guard_transfer_contexts]
                    == ([] if action == 'export' else ['export']), 'verified_guard_context_order_required')
        context = Context(self.guest, self.nonce, action, arguments, maximum_seconds=self.remaining(60))
        try:
            return context.run()
        except Exception:
            raise Refused('guard_transfer_context_refused') from None
        finally:
            self.guard_transfer_contexts.append(context.record)

    def preserve_latest_guard(self):
            self.stage = 'host_private_newest_guard'
            self.stop_core()
            proof = json.loads(self.guest_read(self.config_path + '/' + CONTROL + '/external-proof.json'))
            require(type(proof) is dict and set(proof) == {'schema','token','generation','branch_commit','postbackup_window'}
                    and proof['schema'] == 1 and proof['token'] == self.phase_token
                    and proof['generation'] == 'before_restore' and proof['branch_commit'] == self.args.branch_commit,
                    'external_proof_binding_refused')
            window = proof['postbackup_window']
            require(type(window) is dict and set(window) == {'start','end','rows','sha256'}
                    and all(type(window[k]) in {int,float} for k in ('start','end'))
                    and 0 < window['end']-window['start'] < 120 and type(window['rows']) is int
                    and 5 <= window['rows'] <= 128 and re.fullmatch(r'[0-9a-f]{64}',window['sha256']),
                    'external_history_window_refused')
            self.external_proof = proof
            self.guest_write(GUEST_ROOT + '/guard-transfer.py', (ROOT/'guard_transfer.py').read_bytes())
            result = self.run_guard_transfer('export')
            self.guard_export = guard_export_observation(result, self.phase_token)
            require(result['exitcode'] == 0 and not result['truncated'], 'guest_command_failed')
            raw = result['stdout']
            require(guard_fingerprint(decode_guard(raw)) == self.latest_guard_sha256
                    and self.latest_guard_sha256 != self.backup_guard_sha256, 'host_newest_guard_binding_refused')
            path = self.private/'newest-guard-private.json'
            with path.open('xb') as output:
                os.chmod(path,0o600)
                output.write(raw)
                output.flush()
                os.fsync(output.fileno())
            self.host_guard = path
            require(path.parent == self.private and not path.is_symlink()
                    and stat.S_IMODE(path.stat().st_mode) == 0o600 and path.stat().st_nlink == 1,
                    'private_host_guard_path_refused')
            self.host_guard_retained = True

    def require_restore_barrier_absent(self):
        require(self.network_boundary["link_closed"] and self.host_guard_retained and len(self.phases) == 2,
                "restore_barrier_absence_order_refused")
        path = self.config_path + "/" + CONTROL + "/restore-barrier.json"
        require(self.guest("test ! -e " + path + " && test ! -L " + path, 15).strip() == b"",
                "restore_barrier_must_be_absent")
        for suffix in ("closed-boot-grant.json", "closed-boot-grant.tmp"):
            require(self.guest("test ! -e "+self.config_path+"/"+CONTROL+"/"+suffix+" && test ! -L "+self.config_path+"/"+CONTROL+"/"+suffix,15).strip()==b"", "default_grant_must_be_absent")

    def restored_boot_barrier(self):
        self.stage = "automatic_disabled_restore_observation"
        require(self.network_boundary["link_closed"] and self.host_guard_retained and len(self.phases) == 2,
                "automatic_observation_order_refused")
        limit = time.monotonic() + self.remaining(180)
        while time.monotonic() < limit:
            try:
                value = json.loads(self.guest_read(self.config_path + "/" + CONTROL + "/restore-barrier.json"))
            except (Refused, OSError, ValueError):
                time.sleep(1)
                continue
            require(type(value) is dict and value.get("schema") == 1 and value.get("token") == self.phase_token
                    and value.get("generation") == "before_restore" and value.get("branch_commit") == self.args.branch_commit
                    and value.get("entry_disabled") is True and value.get("entry_loaded") is False
                    and value.get("candidate_imported") is False and value.get("ha_config_entry_saved") is True
                    and value.get("closed_boot_grant_verified") is True, "automatic_disabled_entry_required")
            expected = self.storage_proof["baseline"]
            require(type(value.get("observed_storage")) is dict and set(value["observed_storage"]) == RAW_STORAGE_FIELDS
                    and all(value["observed_storage"][key] == expected[key] for key in RAW_STORAGE_FIELDS)
                    and value.get("joins_sha256") == self.joins_sha256
                    and value.get("guard_sha256") == self.backup_guard_sha256
                    and self.guard_fingerprint(self.config_path + "/.storage/homecircle_findmy/recovery_guard") == self.backup_guard_sha256,
                    "automatic_old_storage_and_guard_required")
            process = value.get("process")
            require(type(process) is dict and set(process) == {"pid", "start_ticks"}
                    and all(type(item) is int and item > 0 for item in process.values())
                    and process["start_ticks"] > self.phases[-1]["process"]["start_ticks"], "automatic_distinct_process_required")
            self.after_restore_barrier = True
            public = {"schema": 1, "phase": "automatic_restored_disabled", "generation": "before_restore", "outcome": "passed",
                      "entry_disabled": True, "entry_loaded": False, "candidate_imported": False, "ha_config_entry_saved": True, "closed_boot_grant_verified": True, "process": process,
                      "storage_raw_matches_expected": True, "explicit_registry_joins_checked": True, "selected_registry_joins": 4,
                      "guard_counter": 2, "guard_repaired_before_storage_load": False,
                      "provider_request_attempt_counts_measured": False, "recovery_proof_attempt_counts_measured": False}
            write_json(self.public / "automatic_restored_disabled.json", public)
            self.phases.append(public)
            self.assert_network_closed()
            return
        raise Refused("automatic_disabled_receipt_deadline")

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
            self.stage = 'host_guard_repair_before_storage'
            require(self.after_restore_barrier and len(self.phases) == 3 and self.host_guard_retained
                    and self.network_boundary['link_closed'], 'repair_order_refused')
            self.stop_core()
            stored = json.loads(self.guest_read(self.config_path+'/.storage/core.config_entries'))
            entries = [e for e in stored['data']['entries'] if e.get('domain') == 'homecircle']
            require(len(entries) == 1 and entries[0].get('disabled_by') == 'user', 'disabled_storage_before_repair_required')
            require(self.host_guard.is_file() and not self.host_guard.is_symlink() and self.host_guard.stat().st_nlink == 1
                    and self.host_guard.stat().st_uid == os.geteuid() and stat.S_IMODE(self.host_guard.stat().st_mode) == 0o600
                    and 0 < self.host_guard.stat().st_size <= 1024*1024,
                    'private_host_guard_changed')
            with self.host_guard.open('rb') as stream:
                raw = stream.read(1024*1024+1)
            require(len(raw) <= 1024*1024, 'host_guard_size_refused')
            require(guard_fingerprint(decode_guard(raw)) == self.latest_guard_sha256, 'host_guard_integrity_refused')
            transfer_path = self.config_path+'/'+CONTROL+'/.newest-guard-private.json'
            self.guest('test ! -e '+transfer_path+'; test ! -L '+transfer_path,15)
            self.guest_write(transfer_path,raw)
            self.guest('chmod 600 '+transfer_path,15)
            transfer_result = self.run_guard_transfer('import',
                ('/data/homeassistant/homecircle-safe-restore-qa-control/.newest-guard-private.json',
                 sha(raw), self.backup_guard_sha256, self.latest_guard_sha256))
            require(transfer_result['exitcode'] == 0 and not transfer_result['truncated'], 'guest_command_failed')
            result = json.loads(transfer_result['stdout'])
            require(result == {'schema':1,'outcome':'passed','newest_guard_sha256':self.latest_guard_sha256,
                               'blocked_api_status_checked':True,'private_guest_transfer_removed':True}, 'host_guard_transfer_refused')
            require(self.guard_fingerprint(self.config_path+'/.storage/homecircle_findmy/recovery_guard') == self.latest_guard_sha256,
                    'repaired_guest_guard_bytes_refused')
            self.guard_repaired = True
            self.restore.update(restored_old_guard_sha256=self.backup_guard_sha256,
                                promoted_newest_guard_sha256=self.latest_guard_sha256,
                                host_copy_outside_entire_guest=True, repaired_before_storage_load=True)
            self.phase_token = secrets.token_hex(16)
            self.generation = 'after_restore'
            self.inputs.update(generation=self.generation, latest_guard_sha256=self.latest_guard_sha256,
                backup_guard_sha256=self.backup_guard_sha256, external_proof=self.external_proof,
                expected_joins_sha256=self.joins_sha256)
            control = self.config_path+'/'+CONTROL
            self.guest_write(control+'/.inputs-new',canonical(self.inputs))
            self.guest('set -eu; chmod 600 '+control+'/.inputs-new; mv '+control+'/.inputs-new '+control+'/inputs.json; rm -f '
                +control+'/phase.json '+control+'/job-nonce.json; rm -f '+self.config_path+'/'+RESULTS+'/*.json',30)
            self.verify_candidate()
            self.guest_write(control + "/storage-expected-private.json", canonical(self.storage_proof))
            self.guest("chmod 600 " + control + "/storage-expected-private.json", 15)

    def run(self):
        require(sys.platform == "linux" and os.uname().machine == "x86_64", "native_linux_amd64_required")
        require(Path("/dev/kvm").exists() and os.access("/dev/kvm", os.R_OK | os.W_OK), "accessible_kvm_required")
        require(re.fullmatch("[0-9a-f]{40}", self.args.branch_commit), "branch_commit_refused")
        require(not self.args.output.exists() and not self.args.output.is_symlink(), "fresh_output_required")
        self.args.output.mkdir(mode=0o700, parents=True)
        self.public = self.args.output.resolve() / "public-summary"
        self.public.mkdir(mode=0o700)
        self.private = Path(tempfile.mkdtemp(prefix="private-", dir=self.args.output.resolve()))
        inventory = check_archive(self.args.candidate_zip, CANDIDATE_SHA, 113)
        self.inventories = {"candidate": inventory}
        self.provenance = {"candidate_source_commit": SOURCE_COMMIT, "candidate_zip_sha256": CANDIDATE_SHA,
            "candidate_files": 113, "candidate_payload_sha256": sha(canonical(inventory)), "release_published": False, "controller_branch_commit": self.args.branch_commit,
            "controller_sha256": sha(Path(__file__).read_bytes()), "haos_version": "18.3", "haos_xz_sha256": HAOS_XZ_SHA,
            "helper_files_sha256": {p.relative_to(ROOT / "guest_helper").as_posix(): sha(p.read_bytes())
                for p in (ROOT / "guest_helper").rglob("*") if p.is_file() and "__pycache__" not in p.parts},
            "guard_transfer_sha256": sha((ROOT / "guard_transfer.py").read_bytes()),
            "guard_context_sha256": sha((ROOT / "guard_context.py").read_bytes()),
            "storage_transfer_sha256": sha((ROOT / "storage_transfer.py").read_bytes()),
            "storage_context_sha256": sha((ROOT / "storage_context.py").read_bytes()),
            "reset_sha256": sha((ROOT / "reset_fresh_config.py").read_bytes())}
        self.start_vm(self.download_haos())
        self.wait_initial_managed()
        require(self.core_version_before == self.container_core_version_before == CORE
                and self.supervisor_version_observed == "2026.10.3", "current_managed_environment_required")
        self.core_version_after = self.container_core_version_after = CORE
        self.verify_cli(); self.backup_cli_capabilities()
        self.guest("umask 077; mkdir -m 700 " + GUEST_ROOT, 30)
        self.stop_core()
        self.guest_write(GUEST_ROOT + "/reset.py", (ROOT / "reset_fresh_config.py").read_bytes())
        self.reset_receipt = checked_reset(json.loads(self.guest("/usr/bin/docker exec -i hassio_supervisor python3 -B - "
            + self.nonce + " < " + GUEST_ROOT + "/reset.py", 90)))
        self.start_core()
        self.minimum_core_image = self.actual_core_image()
        self.prepare(inventory)
        self.disconnect_external_network()
        self.network_transitions.append("closed_before_saved_storage")
        self.run_storage_context("seed")
        self.phase("baseline_disabled", start=True)
        self.backup_operation()
        self.inspect_backup()
        self.stop_core()
        self.run_storage_context("mutate")
        self.phase("mutated_disabled", start=True)
        self.preserve_latest_guard()
        self.assert_network_closed()
        self.require_restore_barrier_absent()
        self.default_conditions_restore()
        project_default_receipt(self.default_restore_conditions, complete=True)
        self.restored_boot_barrier()
        require(self.actual_core_image() == self.minimum_core_image, "automatic_restore_image_changed")
        self.fresh_restore_control()
        self.phase("repaired_storage_disabled", start=True)
        self.phase("restart_disabled", start=True)
        self.assert_network_closed()
        require(self.actual_core_image() == self.minimum_core_image, "final_restart_image_changed")
        self.verify_candidate()
        require([p["phase"] for p in self.phases] == list(PHASES), "all_five_storage_phases_required")
        accept_guard_contexts(self.guard_transfer_contexts)
        accept_storage_contexts(self.storage_contexts)
        require(set(self.storage_results) == set(STORAGE_ACTIONS), "all_storage_actions_required")
        self.stage = "default_conditions_saved_storage_restore_complete"
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
        passed = self.acceptance and failure is None and not self.cleanup["cleanup_failed"] and len(self.phases) == 5
        labels = failure_projection({"stage": self.stage, "failure_type": type(failure).__name__ if failure else None,
            "failure_code": str(failure) if type(failure) is Refused else None})
        value = {"schema": 1, "outcome": "passed" if passed else "failed_or_incomplete", "phases": len(self.phases),
            "failure_or_final_stage": labels["stage"], "failure_type": labels["failure_type"] if failure else None,
            "failure_code": labels["failure_code"], "provenance": self.provenance,
            "actual_kvm_confirmed": self.kvm_confirmed, "actual_core": self.core_version_after,
            "actual_supervisor": self.supervisor_version_observed,
            "initial_managed_environment": {"api_core": public_core_version(self.core_version_before),
                "container_core": public_core_version(self.container_core_version_before), "supervisor": public_core_version(self.supervisor_version_observed)},
            "current_core_image": self.minimum_core_image, "fresh_owned_config": self.reset_receipt,
            "core_actions": self.core_actions, "backup_requests": self.backup_requests,
            "backup": {k: v for k, v in (self.backup or {}).items() if k != "slug"}, "restore": self.restore,
            "guard_transfer_contexts": self.guard_transfer_contexts, "storage_contexts": self.storage_contexts,
            "storage_results": self.storage_results, "host_newest_guard_retained": self.host_guard_retained,
            "default_restore_conditions": self.default_restore_conditions, "temporary_global_offline_conditions": False,
            "ordinary_default_supervisor_restore_qualified": False,
            "default_conditions_disabled_synthetic_restore_qualified": passed,
            "default_supervisor_conditions_used": True, "manual_newest_guard_repair_required": True,
            "tested_default_conditions_disabled_saved_storage_restore": passed,
            "unsupported_conditions_override_used": False,
            "guard_repaired_before_storage_load": self.guard_repaired and self.repaired_disabled,
            "network_boundary": self.network_boundary, "network_transitions": self.network_transitions,
            "tested_disabled_entry_saved_storage_restore": passed, "synthetic_saved_accounts_seeded": bool(self.storage_results),
            "real_provider_accounts_configured": False, "owner_credentials_used": False,
            "production_configuration_used": False, "normal_managed_dependencies": False,
            "prepared_dependency_preload_used": False, "ordinary_enabled_restore_safety_accepted": False,
            "automatic_guard_antirollback": False, "provider_activation_after_restore_tested": False,
            "provider_authentication_after_restore_tested": False, "provider_session_renewal_tested": False,
            "provider_request_attempt_counts_measured": False, "recovery_proof_attempt_counts_measured": False,
            "full_system_restore_tested": False, "full_encrypted_cloud_backup_tested": False,
            "stable_release_approval": False, "candidate_hacs_download_tested": False,
            "candidate_release_zip_transport_tested": False, "candidate_transport": "stopped_verified_zip_files",
            "direct_candidate_installs": self.direct_installs, "host_elapsed_seconds": round(time.monotonic() - self.started, 3), **self.cleanup}
        if self.public is not None:
            write_json(self.public / "host.json", value)
        print("saved_storage_outcome=" + value["outcome"], flush=True)
        return 0 if passed else 1

    def default_api(self, action, deadline):
        require(type(action) is str and action in {'info','network'}, 'default_api_action_refused')
        seconds = min(12, deadline-time.monotonic())
        require(seconds > 1, 'default_api_deadline_exceeded')
        result = self.guest('/usr/bin/docker exec -i hassio_cli /bin/sh -s -- '+action+' < '+GUEST_ROOT+'/job-options-client.sh', seconds, capture=True)
        require(time.monotonic() <= deadline, 'default_api_deadline_exceeded')
        return result

    def default_effective_state(self, deadline):
        result = self.default_api("info", deadline)
        require(offline_api_ack(result, info=True), "offline_options_GET_refused")
        return offline_jobs_info(result["stdout"])

    def default_persisted_state(self, deadline):
        seconds = min(10, deadline - time.monotonic())
        require(seconds > 1, "offline_persistence_deadline_exceeded")
        result = self.guest("/usr/bin/docker exec -i --user=0:0 hassio_supervisor python3 -B - < "
            + GUEST_ROOT + "/job-options-persist.py", seconds, capture=True)
        require(type(result) is dict and type(result.get("exitcode")) is int and result["exitcode"] == 0
                and (result.get("signal") is None or type(result.get("signal")) is int and result["signal"] == 0) and result.get("truncated") is False and result.get("stderr") == b""
                and type(result.get("stdout")) is bytes and 0 < len(result["stdout"]) <= 128,
                "offline_persisted_options_refused")
        require(time.monotonic() <= deadline, "offline_persistence_deadline_exceeded")
        value = json.loads(result["stdout"])
        require(type(value) is dict and set(value) == {"schema", "state"} and type(value["schema"]) is int
                and value["schema"] == 1 and type(value["state"]) is str
                and value["state"] in {"absent", "empty", "owned_two", "foreign", "refused"},
                "offline_persisted_options_refused")
        return value["state"]

    def default_conditions_restore(self):
        self.stage = 'default_conditions_preflight'
        record = new_default_receipt()
        self.default_restore_conditions = record
        original_deadline = self.deadline
        require(original_deadline-time.monotonic() > 180, 'default_cleanup_reserve_required')
        self.deadline = original_deadline-90
        attempted = False
        try:
            self.assert_network_closed(); record['network_closed_before'] = True
            require(self.core_container_state(min(10,self.remaining(10))) == 'stopped', 'default_restore_core_must_be_stopped')
            require(self.backup is not None and self.backup.get('homeassistant_version') == CORE
                and type(self.backup.get('archive')) is dict
                and all(self.backup['archive'].get(key) is True for key in ('candidate_match','disabled_entry','database_included',
                    'saved_pair_included','saved_config_included','saved_selection_included','saved_registry_joins_included')),
                'default_same_core_local_archive_required')
            self.verify_candidate(); record['candidate113_archive_verified'] = True
            require(self.actual_core_image() == self.minimum_core_image, 'default_cached_image_before_refused')
            record['cached_same_core_image_verified_before'] = True
            self.verify_disabled_preopen(); record['disabled_unimported_config_verified'] = True
            for name,raw in (('job-options-client.sh',DEFAULT_API_CLIENT.encode()),('job-options-persist.py',JOB_OPTIONS_PERSISTENCE_PROGRAM.encode())):
                self.guest_write(GUEST_ROOT+'/'+name,raw)
                require(self.guest_read(GUEST_ROOT+'/'+name) == raw, 'default_readonly_source_refused')
            state,idle = self.default_effective_state(self.deadline)
            persisted = self.default_persisted_state(self.deadline)
            record['foreign_options_refused'] = state != 'empty' or persisted not in {'empty','absent'}
            require(state == 'empty' and persisted in {'empty','absent'}, 'default_original_options_must_be_empty')
            require(idle, 'default_relevant_visible_jobs_must_be_idle')
            record.update(original_effective_empty=True,original_persisted_empty_or_absent=True,relevant_visible_jobs_idle_before=True)
            self.stage = 'default_restore_network_open'
            attempted = True; record['network_open_requests'] = 1
            self.set_restore_network_link(True)
            record['network_open_acknowledged'] = True
            self.network_boundary['link_closed'] = False
            require(self.connectivity_probe() is True, 'default_network_positive_control_required')
            record['network_open_positive_control'] = True
            self.network_transitions.append('opened_for_default_restore')
            self.wait_default_internet(record)
            self.backup_operation(restore=True)
            record['restore_completed'] = True
        finally:
            previous_stage = self.stage
            self.deadline = original_deadline
            if attempted:
                self.stage = 'default_restore_network_close'
                cleanup_deadline = min(original_deadline,time.monotonic()+90)
                self.deadline = cleanup_deadline
                try:
                    record['network_close_requests'] = 1
                    try:
                        self.set_restore_network_link(False)
                        record['network_close_acknowledged'] = True
                    except Exception:
                        pass
                    connected = self.connectivity_probe()
                    self.qga.call('guest-ping')
                    require(record['network_close_acknowledged'] and connected is False, 'default_network_close_unproven')
                    self.network_boundary.update(link_closed=True,closed_probe_connected=False,guest_agent_remained_available=True)
                    self.network_boundary['closed_probe_observations'] = self.network_boundary.get('closed_probe_observations',0)+1
                    record['network_closed_after'] = True
                    self.network_transitions.append('closed_after_default_restore')
                    state,_idle = self.default_effective_state(cleanup_deadline)
                    persisted = self.default_persisted_state(cleanup_deadline)
                    record['foreign_options_refused'] = state != 'empty' or persisted not in {'empty','absent'}
                    require(state == 'empty' and persisted in {'empty','absent'}, 'default_final_options_not_empty')
                    record.update(final_effective_empty_observed=True,final_persisted_empty_or_absent=True)
                    require(time.monotonic() <= cleanup_deadline, 'default_network_cleanup_deadline_exceeded')
                except BaseException:
                    record['cleanup_failed'] = True
                    raise Refused('default_network_cleanup_failed') from None
                finally:
                    self.deadline = original_deadline
                self.stage = previous_stage
        require(record['restore_completed'] and record['network_closed_after'] and record['final_effective_empty_observed']
            and record['final_persisted_empty_or_absent'], 'default_window_must_close_before_private_reads')
        require(self.actual_core_image() == self.minimum_core_image, 'default_cached_image_after_refused')
        record['cached_same_core_image_verified_after'] = True
        self.verify_candidate()
        self.grant_closed_boot('automatic_restored_disabled')
        record['closed_boot_grant_written'] = True
        project_default_receipt(record,complete=True)

    def set_restore_network_link(self, up):
        require(type(up) is bool, 'default_link_state_refused')
        deadline = time.monotonic()+self.remaining(20)
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
            connection.settimeout(min(10,self.remaining(10)))
            connection.connect(str(self.qmp_path))
            stream=connection.makefile('rwb',buffering=0)
            require('QMP' in json.loads(stream.readline(65536)), 'default_qmp_greeting_refused')
            for identifier,execute,arguments in [('caps','qmp_capabilities',None),('restore_link','set_link',{'name':'qa-net0','up':up})]:
                request={'execute':execute,'id':identifier}
                if arguments is not None:request['arguments']=arguments
                stream.write(canonical(request)+b'\n')
                for _ in range(32):
                    require(time.monotonic()<deadline, 'default_qmp_deadline_exceeded')
                    connection.settimeout(min(10,deadline-time.monotonic()))
                    response=json.loads(stream.readline(65536))
                    if response.get('id')==identifier:
                        require(response.get('return')=={} and 'error' not in response, 'default_qmp_link_refused')
                        break
                else:raise Refused('default_qmp_response_bound_refused')
        require(time.monotonic()<=deadline, 'default_qmp_deadline_exceeded')

    def wait_default_internet(self,record):
        limit=min(self.deadline,time.monotonic()+90)
        for index in range(18):
            require(time.monotonic()<limit, 'default_internet_readiness_deadline')
            record['network_info_requests']+=1
            captured=self.default_api('network',limit)
            require(offline_api_ack(captured,info=True), 'default_network_info_GET_refused')
            value=json.loads(captured['stdout'])
            data=value['data']
            require(type(data.get('host_internet')) in {bool,type(None)} and type(data.get('supervisor_internet')) in {bool,type(None)},
                'default_network_info_shape_refused')
            if data.get('host_internet') is True and data.get('supervisor_internet') is True:
                require(time.monotonic()<=limit, 'default_internet_readiness_deadline')
                record.update(supervisor_host_internet_true=True,supervisor_internet_true=True)
                return
            if index<17:
                require(time.monotonic()+5<limit, 'default_internet_readiness_deadline')
                time.sleep(5)
        raise Refused('default_internet_readiness_bound')

    def verify_disabled_preopen(self):
        require(len(self.phases)==2 and self.phases[-1]['phase']=='mutated_disabled'
            and self.phases[-1]['entry_disabled'] is True and self.phases[-1]['candidate_imported'] is False
            and self.phases[-1]['entry_loaded'] is False and self.host_guard_retained,
            'default_disabled_phase_before_open_required')
        # Only config/selection metadata are read; no key, vault or guard access.
        script = "import hashlib,json,os,stat\nfrom pathlib import Path\nroot=Path('/data/homeassistant')\ndef read(path,managed=False):\n fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)\n try:\n  st=os.fstat(fd)\n  assert stat.S_ISREG(st.st_mode) and st.st_uid==0 and st.st_nlink==1 and stat.S_IMODE(st.st_mode) in ({0o600,0o644} if managed else {0o600}) and 0<st.st_size<=2*1024**2\n  raw=os.read(fd,2*1024**2+1);assert len(raw)==st.st_size\n  return json.loads(raw)\n finally:os.close(fd)\ndef digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()\nrows=read(root/'.storage/core.config_entries',True)['data']['entries']\nfound=[r for r in rows if r.get('domain')=='homecircle']\nassert len(found)==1\ne=found[0]\nassert e.get('disabled_by')=='user' and e.get('title')=='Synthetic saved storage verified' and e['data']==e['options']\nassert digest({'data':e['data'],'options':e['options']})==__CONFIG__\nselection=read(root/'homecircle-safe-restore-qa-control/storage-selection-private.json')\nassert selection['entry_id']==e['entry_id'] and digest(selection)==__SELECTION__\nprint(json.dumps({'schema':1,'verified':True}))\n"
        script=script.replace('__CONFIG__',repr(self.storage_proof['mutation']['config_sha256'])).replace('__SELECTION__',repr(self.storage_proof['mutation']['selection_sha256']))
        self.guest_write(GUEST_ROOT+'/preopen-disabled.py',script.encode())
        require(json.loads(self.guest('/usr/bin/docker exec -i --user=0:0 hassio_supervisor python3 -B - < '+GUEST_ROOT+'/preopen-disabled.py',20))
            == {'schema':1,'verified':True}, 'default_disabled_config_before_open_refused')

    def grant_closed_boot(self,name):
        self.assert_network_closed()
        automatic=name=='automatic_restored_disabled'
        if automatic:
            record=self.default_restore_conditions
            require(record['restore_completed'] and record['network_closed_after'] and record['final_effective_empty_observed']
                and record['final_persisted_empty_or_absent'], 'default_automatic_grant_before_close_refused')
        control=self.config_path+'/'+CONTROL
        for suffix in ('closed-boot-grant.json','closed-boot-grant.tmp'):
            require(self.guest('test ! -e '+control+'/'+suffix+' && test ! -L '+control+'/'+suffix,10).strip()==b'', 'default_grant_collision_refused')
        limit=time.monotonic()+self.remaining(60)
        previous=self.phases[-1]['process']['start_ticks'] if self.phases else 0
        while time.monotonic()<limit:
            try:request=json.loads(self.guest_read(control+'/boot-request.json'))
            except (Refused,OSError,ValueError):
                time.sleep(0.5);continue
            if type(request) is not dict or type(request.get('process')) is not dict:
                raise Refused('default_boot_request_shape_refused')
            proc=request['process']
            if type(proc.get('start_ticks')) is int and proc['start_ticks']<=previous:
                time.sleep(0.5);continue
            expected={'schema':1,'source_commit':SOURCE_COMMIT,'candidate_sha256':CANDIDATE_SHA,'token':self.phase_token,
                'generation':self.generation,'branch_commit':self.args.branch_commit,
                'phase':'baseline_disabled' if automatic else name,'purpose':'automatic_restore' if automatic else 'phase',
                'process':proc,'boot_nonce':request.get('boot_nonce')}
            require(set(request)==set(expected) and request==expected and type(request['schema']) is int
                and set(proc)=={'pid','start_ticks'} and all(type(v)is int and v>0 for v in proc.values())
                and type(request['boot_nonce']) is str and re.fullmatch('[0-9a-f]{32}',request['boot_nonce']), 'default_boot_request_identity_refused')
            grant={**request,'external_network_closed':True,'default_conditions_verified':automatic}
            script='import json,os,stat\nfrom pathlib import Path\np=Path('+repr(control+'/closed-boot-grant.json')+')\nt=p.with_suffix(".tmp")\nraw='+repr(canonical(grant))+'\nassert not p.exists() and not p.is_symlink() and not t.exists() and not t.is_symlink()\nfd=os.open(t,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)\nwith os.fdopen(fd,"wb") as f:\n f.write(raw);f.flush();os.fsync(f.fileno());s=os.fstat(f.fileno());assert s.st_uid==0 and s.st_nlink==1 and stat.S_IMODE(s.st_mode)==0o600\nassert t.read_bytes()==raw\nos.rename(t,p)\nprint(json.dumps({"schema":1,"grant_written":True}))\n'
            self.guest_write(GUEST_ROOT+'/grant-closed-boot.py',script.encode())
            require(json.loads(self.guest('/usr/bin/docker exec -i --user=0:0 hassio_supervisor python3 -B - < '+GUEST_ROOT+'/grant-closed-boot.py',20))
                == {'schema':1,'grant_written':True}, 'default_closed_grant_write_refused')
            self.assert_network_closed()
            return
        raise Refused('default_boot_request_deadline')

    def run_storage_context(self, action):
        require(action in STORAGE_ACTIONS and [item["action"] for item in self.storage_contexts]
                == list(STORAGE_ACTIONS[:STORAGE_ACTIONS.index(action)]), "storage_context_order_refused")
        self.assert_network_closed()
        if action in {"validate_restored", "validate_restart"}:
            require(self.after_restore_barrier and self.guard_repaired and self.generation == "after_restore",
                    "guard_repair_before_storage_required")
        else:
            require(self.generation == "before_restore", "storage_seed_generation_refused")
        self.stage = "standalone_saved_storage"
        transfer = (ROOT / "storage_transfer.py").read_bytes()
        self.guest_write(GUEST_ROOT + "/storage-transfer.py", transfer)
        require(self.guest_read(GUEST_ROOT + "/storage-transfer.py") == transfer, "storage_transfer_source_refused")
        job = {"schema": 1, "action": action, "token": self.phase_token, "generation": self.generation,
               "branch_commit": self.args.branch_commit}
        control = self.config_path + "/" + CONTROL
        self.guest("test ! -L " + control + "/storage-job.json; test ! -e " + control + "/.storage-job-new", 15)
        self.guest_write(control + "/.storage-job-new", canonical(job))
        self.guest("set -eu; chmod 600 " + control + "/.storage-job-new; mv " + control + "/.storage-job-new " + control + "/storage-job.json", 15)
        context = StorageContext(self.guest, self.nonce, action,
            (self.phase_token, self.generation, self.args.branch_commit), maximum_seconds=self.remaining(60))
        try:
            result = context.run()
            failure = project_storage_failure(result, action)
            if failure is not None:
                context.record["storage_transfer_failure"] = failure
            require(result["exitcode"] == 0 and result["stderr"] == b"" and not result["truncated"], "storage_transfer_refused")
            public = project_storage_result(json.loads(result["stdout"]), action)
            private = json.loads(self.guest_read(control + "/storage-result-private.json"))
            require(type(private) is dict and set(private) == {"schema", "action", *FINGERPRINT_FIELDS}
                    and type(private["schema"]) is int and private["schema"] == 1 and private["action"] == action,
                    "storage_private_result_refused")
            actual = private_fingerprints({key: private[key] for key in FINGERPRINT_FIELDS})
            proof = private_proof(json.loads(self.guest_read(control + "/storage-proof-private.json")))
            if action == "seed":
                require(proof["mutation"] is None and actual == proof["baseline"], "storage_seed_proof_refused")
                self.storage_proof = proof
            elif action == "mutate":
                require(proof["baseline"] == self.storage_proof["baseline"] and proof["mutation"] == actual
                        and all(proof["baseline"][key] != actual[key] for key in FINGERPRINT_FIELDS), "storage_mutation_proof_refused")
                self.storage_proof = proof
            else:
                require(proof["baseline"] == self.storage_proof["baseline"] and proof["mutation"] is None
                        and actual == self.storage_proof["baseline"], "storage_restored_proof_refused")
            self.storage_results[action] = public
        finally:
            self.storage_contexts.append(context.record)
        self.assert_network_closed()



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
