"""Native Linux KVM HAOS partial backup/Recorder restore with a disabled-entry gate.

This is a controller for one newly created guest. It does not connect to UTM,
SSH, an existing VM, a production Home Assistant, or a human GitHub account.
"""

from __future__ import annotations

from guard_transfer import decode as decode_guard, fingerprint as guard_fingerprint
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


HAOS_URL = "https://github.com/home-assistant/operating-system/releases/download/18.3/haos_ova-18.3.qcow2.xz"
HAOS_XZ_SHA = "fae6a728768cc10aff60d4820bfcd40d64cd77fab82c8bd92af13b3d9d414090"
CANDIDATE_SHA = "c4530d94be3b2996f8d6c8948db88a51868566047d68558eefde7967f270a861"
BRANCH = "codex/native-amd64-validation"
CORE = "2026.10.2"
HA = "/usr/bin/docker exec hassio_cli ha"
GUEST_ROOT = "/mnt/data/homecircle-safe-restore-qa"
CONTROL = "homecircle-safe-restore-qa-control"
RESULTS = "homecircle-safe-restore-qa-results"
PHASES = ("initialize", "initial_restart", "quarantine", "mutate", "automatic_disabled", "repaired_disabled", "reenabled", "restart")
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


def source_failure_catalog():
    """Finite literal labels from only these reviewed, hash-bound QA sources."""
    paths = (ROOT / 'controller.py', ROOT / 'reset_fresh_config.py',
             ROOT / 'guest_helper/homecircle_safe_restore_qa/__init__.py',
             ROOT / 'guest_helper/homecircle_safe_restore_qa/dependency_probe.py', ROOT/'guard_transfer.py')
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

SOURCE_COMMIT = "9bf03eb45d2cf43274074534e9dfe2de841f4011"

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


FAILURE_CODES, FAILURE_STAGES = source_failure_catalog()
FAILURE_TYPES = frozenset({"Refused", "RuntimeError", "OSError", "ValueError", "TypeError", "AttributeError", "KeyError", "JSONDecodeError", "TimeoutError", "TimeoutExpired", "FileNotFoundError", "PermissionError", "ImportError", "ModuleNotFoundError", "PackageNotFoundError", "ClientError", "ClientConnectorError", "ClientResponseError", "CancelledError"})

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
        self.guest("umask 077; mkdir -m 700 " + GUEST_ROOT, 30)
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
                  "frontend": {}, "http": {}, "lovelace": {}, "person": {}, "zone": [{"name":"Synthetic Park","latitude":0.01,"longitude":0.01,"radius":50}],
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
        require(len(self.phases) < len(PHASES) and name == PHASES[len(self.phases)], "phase_order_refused")
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
                failure.update(failure_projection(receipt))
                if probe := public_http_probe(receipt.get("http_probe")):
                    failure["http_probe"] = probe
                write_json(self.public / (name + ".json"), failure)
                raise Refused("guest_acceptance_failed")
            projected = self.accept_phase(name, receipt)
            write_json(self.public / (name + ".json"), projected)
            if name in {'quarantine','mutate'}:
                require(projected['process'] == self.phases[1]['process'], 'prebackup_process_changed')
            if name == 'reenabled':
                require(projected['process'] == self.phases[5]['process'], 'repair_to_enable_process_changed')
            self.phases.append(projected)
            return
        raise Refused("phase_receipt_deadline_exceeded")

    def accept_phase(self, name, receipt):
        def fingerprint(value):
            require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value), "phase_fingerprint_refused")
            return value

        active = name in {"initialize", "initial_restart", "reenabled", "restart"}
        require(receipt.get("core_version") == CORE and receipt.get("candidate_archive_sha256") == CANDIDATE_SHA
                and receipt.get("owner_accounts_used") is False and receipt.get("production_configuration_used") is False
                and receipt.get("provider_request_attempt_counts_measured") is False
                and receipt.get("recovery_proof_attempt_counts_measured") is False, "phase_fixture_scope_refused")
        require(receipt.get("entry_disabled") is (not active) and receipt.get("entry_loaded") is active,
                "phase_disabled_entry_gate_refused")
        expected = self.inventories["candidate"]
        require(receipt.get("package_files_count") == 113
                and receipt.get("package_payload_sha256") == sha(canonical(expected)), "phase_package_projection_refused")
        loaded = receipt.get("loaded_source_sha256")
        require(loaded in (None, expected["__init__.py"]["sha256"])
                and (not active or loaded == expected["__init__.py"]["sha256"]), "phase_loaded_source_refused")
        process = receipt.get("process", {})
        require(type(process.get("pid")) is int and process["pid"] > 0
                and type(process.get("start_ticks")) is int and process["start_ticks"] > 0,
                "phase_process_identity_refused")
        snapshot = fingerprint(receipt.get("snapshot_sha256"))
        owned_resource = fingerprint(receipt.get("owned_resource_id_sha256")) if active else None
        quarantine = receipt.get("quarantine_snapshot_sha256")
        if name == "quarantine":
            require(receipt.get("persisted_storage_checked") is True, "prebackup_persisted_storage_required")
        if name in {"quarantine", "repaired_disabled"}:
            quarantine = fingerprint(quarantine)
        elif quarantine is not None:
            quarantine = fingerprint(quarantine)
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
        require(type(public_recorder["prebackup_rows"]) is int and public_recorder["prebackup_rows"] >= 4
                and public_recorder["prebackup_sha256"] is not None
                and public_recorder["prebackup_exact_match"] is True, "phase_prebackup_history_refused")
        previous = {phase["phase"]: phase for phase in self.phases}
        if name != "initialize":
            baseline = previous["initialize"]
            require(public_recorder["prebackup_rows"] == baseline["recorder"]["prebackup_rows"]
                    and public_recorder["prebackup_sha256"] == baseline["recorder"]["prebackup_sha256"],
                    "phase_prebackup_history_changed")
            if name != "mutate":
                require(snapshot == baseline["snapshot_sha256"], "phase_identity_snapshot_changed")
        if name == "mutate":
            require(snapshot != previous["initialize"]["snapshot_sha256"]
                    and type(public_recorder["postbackup_marker_rows"]) is int
                    and public_recorder["postbackup_marker_rows"] >= 1
                    and public_recorder["postbackup_marker_absent"] is False,
                    "postbackup_mutation_not_proven")
        else:
            require(public_recorder["postbackup_marker_rows"] == 0
                    and public_recorder["postbackup_marker_absent"] is True, "postbackup_marker_not_absent")
        if name == "repaired_disabled":
            require(self.after_restore_barrier and quarantine == previous["quarantine"]["quarantine_snapshot_sha256"],
                    "restored_quarantine_snapshot_changed")
        if name in {"reenabled", "restart"}:
            require(type(public_recorder["postrestore_rows"]) is int and public_recorder["postrestore_rows"] >= 1
                    and public_recorder["postrestore_sha256"] is not None
                    and public_recorder["postrestore_exact_match"] is True, "postrestore_recording_not_proven")
            if name == "restart":
                before = previous["reenabled"]["recorder"]
                require(public_recorder["postrestore_rows"] == before["postrestore_rows"]
                        and public_recorder["postrestore_sha256"] == before["postrestore_sha256"],
                        "postrestore_restart_history_changed")
                require(owned_resource == previous["reenabled"]["owned_resource_id_sha256"],
                        "recreated_resource_restart_identity_changed")
        guard = receipt.get("guard", {})
        fingerprint(guard.get("sha256"))
        seeded = name in {"mutate", "repaired_disabled", "reenabled", "restart"}
        api_checked = name in {"initialize", "initial_restart", "mutate", "repaired_disabled", "reenabled", "restart"}
        require(type(guard.get("unresolved")) is int and guard["unresolved"] == (3 if seeded else 2)
                and type(guard.get("rejected")) is int and guard["rejected"] == (3 if seeded else 2)
                and guard.get("blocked") is seeded and guard.get("api_status_checked") is api_checked
                and type(guard.get("pending")) is int and guard["pending"] == 0
                and type(guard.get("uncertain")) is int and guard["uncertain"] == 0,
                "phase_guard_evidence_refused")
        if not api_checked:
            require(guard.get("retained_bytes_checked") is True, "phase_guard_bytes_required")
        if name == "quarantine":
            self.backup_guard_sha256 = guard["sha256"]
        if name == "mutate":
            self.latest_guard_sha256 = guard["sha256"]
            require(self.latest_guard_sha256 != self.backup_guard_sha256, "newest_guard_not_distinct")
        if name in {"repaired_disabled", "reenabled", "restart"}:
            require(guard["sha256"] == self.latest_guard_sha256, "newest_guard_not_retained")
        public_guard = {key: guard[key] for key in ("sha256", "blocked", "unresolved", "rejected", "pending", "uncertain", "api_status_checked")}
        if not api_checked:
            public_guard["retained_bytes_checked"] = True
        public = {"schema": 1, "phase": name, "generation": self.generation, "outcome": "passed",
                "package_files_count": 113, "package_payload_sha256": sha(canonical(expected)),
                "loaded_source_sha256": loaded, "snapshot_sha256": snapshot,
                "owned_resource_id_sha256": owned_resource,
                "quarantine_snapshot_sha256": quarantine, "entry_disabled": not active, "entry_loaded": active,
                "process": {key: process[key] for key in ("pid", "start_ticks")},
                "recorder": public_recorder, "guard": public_guard}
        if name == "quarantine":
            public["persisted_storage_checked"] = True
        public.update(provider_request_attempt_counts_measured=False, recovery_proof_attempt_counts_measured=False,
                      nonempty_options=receipt.get('nonempty_options') is True)
        require(public['nonempty_options'] and receipt.get('nonempty_place_and_picture') is True, 'nonempty_options_place_picture_required')
        public['nonempty_place_and_picture'] = True
        if active:
            require(receipt.get('static_served_bundle_matches') is True
                    and receipt.get('served_bundle_sha256') == expected['frontend/homecircle-card.js']['sha256'],
                    'actual_served_bundle_required')
            public.update(served_bundle_sha256=receipt['served_bundle_sha256'],
                          static_served_bundle_matches=True,
                          runtime_config_sha256=fingerprint(receipt.get('runtime_config_sha256')),
                          resource_url_type_sha256=fingerprint(receipt.get('resource_url_type_sha256')),
                          normal_dependencies=project_dependencies(receipt.get('normal_dependencies'), complete=True))
        if active and name != 'initialize':
            require(public['resource_url_type_sha256'] == previous['initialize']['resource_url_type_sha256'],
                    'owned_resource_url_type_changed')
        if name == 'repaired_disabled':
            require(self.guard_repaired and self.network_boundary['link_closed'], 'repaired_disabled_before_network_required')
            public['normal_dependencies_before_enable'] = project_dependencies(receipt.get('normal_dependencies_before_enable'), complete=False)
            self.repaired_disabled = True
        if name == 'initial_restart':
            require(process['start_ticks'] != previous['initialize']['process']['start_ticks'], 'initial_restart_process_required')
        if name == 'restart':
            require(process['start_ticks'] != previous['reenabled']['process']['start_ticks'], 'final_restart_process_required')
        return public

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
inputs=json.loads((root/"homecircle-safe-restore-qa-control/inputs.json").read_bytes())
path=Path("/data/backup/homecircle-safe-restore-qa.tar")
require(path.is_file() and not path.is_symlink() and 0<path.stat().st_size<=128*1024**2)
package,guard,entry,db={},{},None,False
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
            require(name!="data/homecircle-safe-restore-qa-control/restore-barrier.json")
            if name=="data/.storage/core.config_entries":
                entries=json.loads(data)["data"]["entries"]
                selected=[e for e in entries if e.get("domain")=="homecircle"]
                require(len(selected)==1 and selected[0].get("disabled_by")=="user")
                entry=True
            if name=="data/home-assistant_v2.db":
                require(data[:16]==b"SQLite format 3\x00" and len(data)>4096)
                db=True
require(package==inputs["candidate_inventory"] and entry is True and db and guard)
print(json.dumps({"archive_bytes":path.stat().st_size,"archive_sha256":sha(path.read_bytes()),"database_included":db,"candidate_match":True,"disabled_entry":True,"guard_sha256":sha(canonical(guard))},sort_keys=True))
'''
        self.guest_write(GUEST_ROOT + "/inspect-backup.py", script.encode())
        value = json.loads(self.guest("/usr/bin/docker exec -i hassio_supervisor python3 - < "
                                      + GUEST_ROOT + "/inspect-backup.py", 120))
        require(value.get("database_included") is True and value.get("candidate_match") is True
                and value.get("disabled_entry") is True and value.get("guard_sha256") == self.backup_guard_sha256,
                "backup_archive_proof_refused")
        require(type(value.get("archive_bytes")) is int and 0 < value["archive_bytes"] <= 128 * 1024**2
                and isinstance(value.get("archive_sha256"), str)
                and re.fullmatch(r"[0-9a-f]{64}", value["archive_sha256"]), "backup_archive_receipt_refused")
        self.backup["archive"] = value

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
        raw = self.guest('/usr/bin/docker exec -i hassio_supervisor python3 - export < ' + GUEST_ROOT + '/guard-transfer.py',60)
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

    def restored_boot_barrier(self):
        self.stage = 'automatic_disabled_restore_observation'
        require(self.network_boundary['link_closed'] and self.host_guard_retained
                and len(self.phases) == 4, 'automatic_observation_order_refused')
        limit = time.monotonic() + self.remaining(180)
        while time.monotonic() < limit:
            try:
                value = json.loads(self.guest_read(self.config_path+'/'+CONTROL+'/restore-barrier.json'))
            except (Refused,OSError,ValueError):
                time.sleep(1)
                continue
            require(type(value.get('schema')) is int and value['schema'] == 1
                    and value.get('token') == self.phase_token and value.get('generation') == 'before_restore'
                    and value.get('branch_commit') == self.args.branch_commit, 'automatic_boot_binding_refused')
            require(value.get('entry_disabled') is True and value.get('entry_loaded') is False
                    and value.get('candidate_imported') is False, 'automatic_disabled_entry_required')
            process = value.get('process',{})
            require(set(process) == {'pid','start_ticks'} and all(type(x) is int and x > 0 for x in process.values())
                    and process['start_ticks'] != self.phases[-1]['process']['start_ticks'], 'automatic_distinct_process_required')
            require(value.get('snapshot_sha256') == self.phases[0]['snapshot_sha256']
                    and value.get('quarantine_snapshot_sha256') == self.phases[2]['quarantine_snapshot_sha256']
                    and value.get('guard_sha256') == self.backup_guard_sha256
                    and self.guard_fingerprint(self.config_path+'/.storage/homecircle_findmy/recovery_guard') == self.backup_guard_sha256,
                    'automatic_old_guard_and_snapshot_required')
            self.after_restore_barrier = True
            public = {'schema':1,'phase':'automatic_disabled','outcome':'passed','entry_disabled':True,
                'entry_loaded':False,'candidate_imported':False,'process':process,
                'snapshot_sha256':value['snapshot_sha256'],'quarantine_snapshot_sha256':value['quarantine_snapshot_sha256'],
                'guard':{'sha256':self.backup_guard_sha256,'unresolved':2,'rejected':2,'pending':0,'uncertain':0,'blocked':False,
                         'api_status_checked':False,'retained_bytes_checked':True},
                'provider_request_attempt_counts_measured':False,'recovery_proof_attempt_counts_measured':False}
            self.restore['automatic_boot_barrier'] = public
            write_json(self.public/'automatic_disabled.json',public)
            self.phases.append(public)
            self.assert_network_closed()
            return
        raise Refused('automatic_disabled_receipt_deadline')

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
        self.stage = 'host_guard_repair_before_enable'
        require(self.after_restore_barrier and len(self.phases) == 5 and self.host_guard_retained
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
        result = json.loads(self.guest('/usr/bin/docker exec -i hassio_supervisor python3 - import '
            + '/data/homeassistant/homecircle-safe-restore-qa-control/.newest-guard-private.json '+sha(raw)+' '+self.backup_guard_sha256
            +' '+self.latest_guard_sha256+' < '+GUEST_ROOT+'/guard-transfer.py',60))
        require(result == {'schema':1,'outcome':'passed','newest_guard_sha256':self.latest_guard_sha256,
                           'blocked_api_status_checked':True,'private_guest_transfer_removed':True}, 'host_guard_transfer_refused')
        require(self.guard_fingerprint(self.config_path+'/.storage/homecircle_findmy/recovery_guard') == self.latest_guard_sha256,
                'repaired_guest_guard_bytes_refused')
        self.guard_repaired = True
        self.restore.update(restored_old_guard_sha256=self.backup_guard_sha256,
                            promoted_newest_guard_sha256=self.latest_guard_sha256,
                            host_copy_outside_entire_guest=True, repaired_before_enable=True)
        self.phase_token = secrets.token_hex(16)
        self.generation = 'after_restore'
        self.inputs.update(generation=self.generation, latest_guard_sha256=self.latest_guard_sha256,
            backup_guard_sha256=self.backup_guard_sha256,external_proof=self.external_proof,
            expected_snapshot_sha256=self.phases[0]['snapshot_sha256'],
            expected_quarantine_sha256=self.phases[2]['quarantine_snapshot_sha256'],
            expected_prebackup_sha256=self.phases[0]['recorder']['prebackup_sha256'])
        control = self.config_path+'/'+CONTROL
        self.guest_write(control+'/.inputs-new',canonical(self.inputs))
        self.guest('set -eu; chmod 600 '+control+'/.inputs-new; mv '+control+'/.inputs-new '+control+'/inputs.json; rm -f '
            +control+'/phase.json '+control+'/job-nonce.json; rm -f '+self.config_path+'/'+RESULTS+'/*.json',30)
        self.verify_candidate()

    def run(self):
        require(sys.platform == 'linux' and os.uname().machine == 'x86_64', 'native_linux_amd64_required')
        require(Path('/dev/kvm').exists() and os.access('/dev/kvm',os.R_OK|os.W_OK),'accessible_kvm_required')
        require(re.fullmatch(r'[0-9a-f]{40}',self.args.branch_commit),'branch_commit_refused')
        require(not self.args.output.exists() and not self.args.output.is_symlink(),'fresh_output_required')
        self.args.output.mkdir(mode=0o700,parents=True)
        self.public=self.args.output.resolve()/'public-summary'
        self.public.mkdir(mode=0o700)
        self.private=Path(tempfile.mkdtemp(prefix='private-',dir=self.args.output.resolve()))
        inventory=check_archive(self.args.candidate_zip,CANDIDATE_SHA,113)
        self.inventories={'candidate':inventory}
        self.provenance={'candidate_source_commit':SOURCE_COMMIT,'candidate_zip_sha256':CANDIDATE_SHA,'candidate_files':113,
            'candidate_version':'0.1.0-beta.20','release_published':False,'controller_branch_commit':self.args.branch_commit,
            'controller_sha256':sha(Path(__file__).read_bytes()),'haos_version':'18.3','haos_xz_sha256':HAOS_XZ_SHA,
            'helper_files_sha256':{p.relative_to(ROOT/'guest_helper').as_posix():sha(p.read_bytes())
                for p in (ROOT/'guest_helper').rglob('*') if p.is_file() and '__pycache__' not in p.parts},
            'guard_transfer_sha256':sha((ROOT/'guard_transfer.py').read_bytes()),
            'reset_sha256':sha((ROOT/'reset_fresh_config.py').read_bytes())}
        self.start_vm(self.download_haos())
        self.wait_initial_managed()
        require(self.core_version_before == self.container_core_version_before == CORE
                and self.supervisor_version_observed == '2026.10.2','current_managed_environment_required')
        self.core_version_after=self.container_core_version_after=CORE
        self.verify_cli()
        self.backup_cli_capabilities()
        self.guest('umask 077; mkdir -m 700 '+GUEST_ROOT,30)
        self.stop_core()
        self.guest_write(GUEST_ROOT+'/reset.py',(ROOT/'reset_fresh_config.py').read_bytes())
        self.reset_receipt=checked_reset(json.loads(self.guest('/usr/bin/docker exec -i hassio_supervisor python3 -B - '
            +self.nonce+' < '+GUEST_ROOT+'/reset.py',90)))
        self.start_core()
        self.minimum_core_image=self.actual_core_image()
        self.target_environment=project_dependencies(self.observe_dependencies(),complete=False)
        require(any(not x['available'] for x in self.target_environment['direct'].values()),'normal_install_missing_dependency_required')
        self.prepare(inventory)
        self.phase('initialize',start=True)
        self.stop_core()
        self.phase('initial_restart',start=True)
        require(self.actual_core_image()==self.minimum_core_image,'initial_restart_image_changed')
        self.phase('quarantine')
        self.backup_operation()
        self.inspect_backup()
        self.phase('mutate')
        self.preserve_latest_guard()
        self.disconnect_external_network()
        self.network_transitions.append('closed_before_restore')
        self.backup_operation(restore=True)
        self.restored_boot_barrier()
        require(self.actual_core_image()==self.minimum_core_image,'automatic_restore_image_changed')
        self.fresh_restore_control()
        self.phase('repaired_disabled',start=True)
        self.assert_network_closed()
        self.reopen_after_repaired_disabled()
        self.phase('reenabled')
        require(self.actual_core_image()==self.minimum_core_image,'reenabled_image_changed')
        self.disconnect_external_network()
        self.network_transitions.append('closed_before_final_restart')
        self.stop_core()
        self.phase('restart',start=True)
        self.assert_network_closed()
        require(self.actual_core_image()==self.minimum_core_image,'final_restart_image_changed')
        self.verify_candidate()
        self.stop_core()
        require([p['phase'] for p in self.phases]==list(PHASES),'all_eight_procedure_phases_required')
        self.stage='safe_disabled_restore_complete'
        self.acceptance=True

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

    def finish(self,failure):
        self.cleanup_vm()
        passed=self.acceptance and failure is None and not self.cleanup['cleanup_failed'] and len(self.phases)==8
        labels=failure_projection({'stage':self.stage,'failure_type':type(failure).__name__ if failure else None,
                                  'failure_code':str(failure) if type(failure) is Refused else None})
        value={'schema':1,'outcome':'passed' if passed else 'failed_or_incomplete','phases':len(self.phases),
            'failure_or_final_stage':labels['stage'],'failure_type':labels['failure_type'] if failure else None,
            'failure_code':labels['failure_code'],'provenance':self.provenance,'actual_kvm_confirmed':self.kvm_confirmed,
            'actual_core':self.core_version_after,'actual_supervisor':self.supervisor_version_observed,
            'core_actions':self.core_actions,'cli_capabilities':self.cli_capabilities,'fresh_owned_config':self.reset_receipt,
            'current_core_image':self.minimum_core_image,'dependencies_before_candidate':self.target_environment,
            'backup_requests':self.backup_requests,'backup':{k:v for k,v in (self.backup or {}).items() if k!='slug'},
            'restore':self.restore,'host_newest_guard_retained':self.host_guard_retained,
            'guard_repaired_before_enable':self.guard_repaired and self.repaired_disabled,
            'network_boundary':self.network_boundary,'network_transitions':self.network_transitions,
            'normal_managed_dependencies':passed,'prepared_dependency_preload_used':False,
            'tested_disabled_entry_partial_restore_procedure':passed,'ordinary_enabled_restore_safety_accepted':False,
            'automatic_guard_antirollback':False,'provider_request_attempt_counts_measured':False,
            'recovery_proof_attempt_counts_measured':False,'owner_credentials_used':False,'provider_accounts_configured':False,
            'production_configuration_used':False,'full_encrypted_cloud_backup_tested':False,'stable_release_approval':False,
            'candidate_hacs_download_tested':False,'candidate_release_zip_transport_tested':False,
            'candidate_transport':'stopped_verified_zip_files','direct_candidate_installs':self.direct_installs,
            'host_elapsed_seconds':round(time.monotonic()-self.started,3),**self.cleanup}
        if self.public is not None:write_json(self.public/'host.json',value)
        print('safe_restore_outcome='+value['outcome'],flush=True)
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
