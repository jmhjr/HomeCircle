"""Disposable enabled saved-storage readback with a pre-start transport boundary."""
from __future__ import annotations
import sys
if sys.platform != "linux":
    raise RuntimeError("qa_linux_required")
import asyncio, secrets
import base64
import importlib.metadata as metadata
import importlib.util

import aiohttp
from . import startup_boundary, failure_diagnostics
from functools import partial
import hashlib
import json
import logging
import os
from pathlib import Path, PurePosixPath
import re
import stat
import probatio as vol
from sqlalchemy import text
from homeassistant.components.backup import async_get_manager
from homeassistant.components.recorder import get_instance, history
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, __version__ as CORE_VERSION
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from homeassistant.util import dt as dt_util
DOMAIN = "homecircle_safe_restore_qa"
CONTROL = "homecircle-safe-restore-qa-control"
RESULTS = "homecircle-safe-restore-qa-results"
CANDIDATE = None
VERIFIED_TITLE = "Synthetic saved storage verified"
PHASES = ("baseline_enabled", "mutated_enabled", "automatic_restored_enabled", "restart_enabled")
TRACKERS = ("device_tracker.homecircle_safe_restore_qa_a", "device_tracker.homecircle_safe_restore_qa_b")
SENTINEL = "sensor.homecircle_safe_restore_qa_sentinel"
RAW_KEYS = {"config_sha256", "key_sha256", "vault_sha256", "selection_sha256", "credentials_sha256"}
SETUP_STEPS = frozenset({"raw_storage", "explicit_registry", "recorder", "unclassified"})
PHOTO_ID = "c" * 32
PHOTO_PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAD0lEQVR4nGNgmPAAhCAUACTOBcF1AlBBAAAAAElFTkSuQmCC")
PHOTO_SHA256 = "3a51cbff9fe4d3958488319741b290925e0a0e22447ef2a03309427cfc7d3f0d"
IMAGE_API_SHA256 = "cf857fb233a858f3af5774fa9d1c87ef855b65fa3827216fd515ed4d9fe115ab"
_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({vol.Required("disposable"): vol.Boolean()})}, extra=vol.ALLOW_EXTRA)
class Refused(RuntimeError):
    """A fixed literal, never input material."""
def check(ok, code):
    if not ok:
        raise Refused(code)

def read_json(path):
    info = path.lstat()
    check(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
          and stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1
          and info.st_size <= 2 * 1024**2, "qa_private_input_path")
    return json.loads(path.read_bytes())

def read_managed_json(directory, name):
    check(name in {"core.config_entries", "core.entity_registry"}, "qa_managed_store_name")
    descriptor = os.open(directory / ".storage" / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        check(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_nlink == 1
              and stat.S_IMODE(info.st_mode) in {0o600, 0o644} and 1 <= info.st_size <= 2 * 1024**2,
              "qa_managed_store_path")
        stream = os.fdopen(descriptor, "rb")
        descriptor = None
        with stream:
            raw = stream.read(2 * 1024**2 + 1)
    finally:
        if descriptor is not None:
            os.close(descriptor)
    check(1 <= len(raw) <= 2 * 1024**2, "qa_managed_store_size")
    return json.loads(raw)

def write_json(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    check(not temporary.exists() and not temporary.is_symlink(), "qa_private_temp_collision")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)

def inputs_at(directory):
    global CANDIDATE
    value = read_json(directory / CONTROL / "inputs.json")
    candidate = value.get("candidate_sha256")
    check(value.get("schema") == 1 and value.get("core_version") == "2026.10.2"
          and type(candidate) is str and re.fullmatch("[0-9a-f]{64}", candidate)
          and CANDIDATE in (None, candidate), "qa_input_binding")
    CANDIDATE = candidate
    check(type(value.get("branch_commit")) is str and re.fullmatch("[0-9a-f]{40}", value["branch_commit"])
          and value.get("generation") in {"before_restore", "after_restore"}, "qa_input_identity")
    inventory = value.get("candidate_inventory")
    check(type(inventory) is dict and 100 <= len(inventory) <= 128, "qa_inventory_count")
    for name, item in inventory.items():
        path = PurePosixPath(name)
        check(type(name) is str and name == path.as_posix() and not path.is_absolute()
              and ".." not in path.parts and "\\" not in name and type(item) is dict
              and set(item) == {"bytes", "sha256"} and type(item["bytes"]) is int
              and 0 <= item["bytes"] < 16 * 1024**2 and type(item["sha256"]) is str
              and re.fullmatch("[0-9a-f]{64}", item["sha256"]), "qa_inventory_member")
    check(value.get("dependency_fixture") is None and value.get("dependency_inventory") is None,
          "qa_dependency_injection_refused")
    if value["generation"] == "after_restore":
        for key in ("latest_guard_sha256", "backup_guard_sha256", "expected_joins_sha256"):
            check(type(value.get(key)) is str and re.fullmatch("[0-9a-f]{64}", value[key]), "qa_after_restore_binding")
    return value

def package_at(directory, inputs):
    package = directory / "custom_components/homecircle"
    actual = {}
    for path in package.rglob("*"):
        check(not path.is_symlink(), "qa_package_symlink")
        if path.is_file() and "__pycache__" not in path.parts:
            raw = path.read_bytes()
            actual[path.relative_to(package).as_posix()] = {"bytes": len(raw), "sha256": digest(raw)}
    original = inputs["candidate_inventory"]
    check(actual == original, "qa_exact_unmodified_package_bytes")
    manifest = json.loads((package / "manifest.json").read_bytes())
    check(DOMAIN not in manifest.get("dependencies", []), "qa_no_product_qa_dependency")
    return {"package_files_count": len(original), "package_payload_sha256": digest(original),
        "candidate_archive_sha256": CANDIDATE, "qa_manifest_only_difference": False,
        "product_manifest_unchanged": True, "qa_manifest_sha256": original['manifest.json']['sha256']}


def assert_enabled(hass, entry):
    check(entry.disabled_by is None and entry.state is ConfigEntryState.LOADED, "qa_enabled_entry_required")
    module = sys.modules.get("custom_components.homecircle")
    check(module is not None and getattr(module, "HomeCircleRuntime", None) is not None,
          "qa_managed_candidate_imported")
    check("homecircle" in hass.config.components, "qa_managed_candidate_state")
    runtime = getattr(entry, "runtime_data", None)
    check(isinstance(runtime, module.HomeCircleRuntime) and runtime.household is not None,
          "qa_product_runtime_required")
    check(set(runtime.managed_trackers) == {"life360", "findmy"}, "qa_actual_provider_lifecycles_required")

def current_entry(hass):
    entries = hass.config_entries.async_entries("homecircle")
    check(len(entries) == 1, "qa_one_enabled_entry")
    entry = entries[0]
    assert_enabled(hass, entry)
    return entry

async def persist_verified_entry(hass, directory, entry, update=False):
    assert_enabled(hass, entry)
    before = json.loads(json.dumps({"data": dict(entry.data), "options": dict(entry.options)}))
    if update:
        check(entry.title != VERIFIED_TITLE, "qa_discriminating_title_required")
        check(hass.config_entries.async_update_entry(entry, title=VERIFIED_TITLE) is True, "qa_actual_entry_update_required")
    else:
        check(entry.title == VERIFIED_TITLE, "qa_verified_title_required")
    async with asyncio.timeout(120):
        while True:
            check({"data": dict(entry.data), "options": dict(entry.options)} == before, "qa_title_update_changed_configuration")
            saved = await hass.async_add_executor_job(read_managed_json, directory, "core.config_entries")
            matches = [row for row in saved["data"]["entries"] if row.get("domain") == "homecircle"]
            check(len(matches) == 1 and matches[0].get("entry_id") == entry.entry_id
                  and matches[0].get("disabled_by") is None, "qa_title_store_identity")
            if (entry.title == VERIFIED_TITLE and matches[0].get("title") == VERIFIED_TITLE
                    and matches[0].get("data") == before["data"] and matches[0].get("options") == before["options"]):
                break
            await asyncio.sleep(0.25)
    assert_enabled(hass, entry)
    return True

def selected_mapping(directory, entry):
    selection = read_json(directory / CONTROL / "storage-selection-private.json")
    check(type(selection) is dict and set(selection) == {"schema", "entry_id", "joins"}
          and selection["schema"] == 1 and selection["entry_id"] == entry.entry_id
          and type(selection["joins"]) is list and len(selection["joins"]) == 4, "qa_explicit_selection_shape")
    ids, unique, kinds = set(), set(), {"person": 0, "item": 0}
    for row in selection["joins"]:
        check(type(row) is dict and set(row) == {"entity_id", "unique_id", "config_entry_id", "kind"}
              and row["config_entry_id"] == entry.entry_id and row["kind"] in kinds
              and type(row["entity_id"]) is str and re.fullmatch("device_tracker[.][a-z0-9_]{1,100}", row["entity_id"])
              and type(row["unique_id"]) is str and re.fullmatch("homecircle_(?:findmy|life360)_[A-Za-z0-9_]{1,160}", row["unique_id"])
              and row["entity_id"] not in ids and row["unique_id"] not in unique, "qa_explicit_selection_join")
        ids.add(row["entity_id"]); unique.add(row["unique_id"]); kinds[row["kind"]] += 1
    config = dict(entry.options)
    check(kinds == {"person": 2, "item": 2} and dict(entry.data) == config
          and config.get("people") == [] and config.get("pets") == [], "qa_config_snapshot_shape")
    check(config.get("primary_home") == "zone.home" and config.get("places") == ["zone.example_saved_storage"]
          and type(config.get("members")) is dict and set(config["members"]) == ids, "qa_product_household_shape")
    for row in selection["joins"]:
        member = config["members"][row["entity_id"]]
        check(type(member) is dict and member.get("kind") == row["kind"]
              and member.get("trackers") == [row["entity_id"]] and member.get("additional_residences") == []
              and type(member.get("show_on_map")) is bool, "qa_product_member_shape")
    check(set(config.get("items", [])) == {row["entity_id"] for row in selection["joins"] if row["kind"] == "item"}
          and set(config.get("people_trackers", [])) == {row["entity_id"] for row in selection["joins"] if row["kind"] == "person"},
          "qa_explicit_config_selection")
    return selection

async def ensure_selected_registry(hass, entry, selection, create=False):
    registry = er.async_get(hass)
    for row in selection["joins"]:
        record = registry.async_get(row["entity_id"])
        if record is None:
            check(create, "qa_selected_registry_missing")
            record = registry.async_get_or_create("device_tracker", "homecircle", row["unique_id"],
                config_entry=entry, disabled_by=None, suggested_object_id=row["entity_id"].split(".", 1)[1], original_name="Synthetic saved tracker")
        check(record.entity_id == row["entity_id"] and record.unique_id == row["unique_id"]
              and record.config_entry_id == row["config_entry_id"] and record.platform == "homecircle"
              and record.disabled_by is None, "qa_selected_registry_identity")
    assert_enabled(hass, entry)
    expected = sorted([{key: row[key] for key in ("entity_id", "unique_id", "config_entry_id")}
                       for row in selection["joins"]], key=lambda row: row["entity_id"])
    async with asyncio.timeout(120):
        while True:
            try:
                saved = await hass.async_add_executor_job(read_managed_json, Path(hass.config.config_dir), "core.entity_registry")
            except FileNotFoundError:
                await asyncio.sleep(0.25)
                continue
            records = saved["data"]["entities"]
            actual = sorted([{key: item.get(key) for key in ("entity_id", "unique_id", "config_entry_id")}
                             for item in records if item.get("entity_id") in {row["entity_id"] for row in expected}],
                            key=lambda row: row["entity_id"])
            if actual == expected:
                check(all(item.get("disabled_by") is None for item in records
                          if item.get("entity_id") in {row["entity_id"] for row in expected}), "qa_saved_registry_enabled")
                break
            await asyncio.sleep(0.25)
    return digest(expected)

def raw_storage(directory, entry):
    saved = read_managed_json(directory, "core.config_entries")
    matches = [item for item in saved["data"]["entries"] if item.get("domain") == "homecircle"]
    check(len(matches) == 1 and matches[0]["entry_id"] == entry.entry_id and matches[0]["disabled_by"] is None
          and matches[0].get("title") == entry.title == VERIFIED_TITLE
          and matches[0]["data"] == dict(entry.data) and matches[0]["options"] == dict(entry.options), "qa_config_entry_persisted")
    config = dict(entry.options)
    accounts = config.get("findmy_accounts")
    check(type(accounts) is dict and len(accounts) == 1, "qa_one_apple_account")
    metadata = next(iter(accounts.values()))
    storage_id = metadata.get("storage_id")
    check(type(storage_id) is str and re.fullmatch("[0-9a-f]{32}", storage_id), "qa_owned_storage_id")
    parent = directory / ".storage/homecircle_findmy/homecircle_accounts" / storage_id
    for path in (parent.parent.parent, parent.parent, parent):
        info = path.lstat()
        check(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid()
              and stat.S_IMODE(info.st_mode) == 0o700, "qa_owned_storage_directory")
    pair = {}
    for name in ("session.key", "session.vault"):
        path = parent / name; info = path.lstat()
        check(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_nlink == 1
              and stat.S_IMODE(info.st_mode) == 0o600 and 0 < info.st_size <= 1024 * 1024, "qa_owned_pair_file")
        pair[name] = digest(path.read_bytes())
    selection = selected_mapping(directory, entry)
    account = config.get("life360_account")
    check(type(account) is dict and account.get("method") == "token" and type(account.get("secret")) is str
          and bool(account["secret"]) and type(account.get("account_id_hash")) is str, "qa_life360_saved_credential")
    return {"config_sha256": digest({"data": dict(entry.data), "options": config}), "key_sha256": pair["session.key"],
            "vault_sha256": pair["session.vault"], "selection_sha256": digest(selection), "credentials_sha256": digest(account)}

async def record_window(hass, people, marker):
    start = dt_util.utcnow().timestamp()
    for index, state in enumerate(("not_home", "home")):
        tracker_state(hass, state, marker + str(index))
        hass.states.async_set(SENTINEL, marker + str(index), {"friendly_name": "Synthetic backup sentinel"})
        await get_instance(hass).async_block_till_done()
        await asyncio.sleep(0.02)
    end = dt_util.utcnow().timestamp()
    rows = await rows_for(hass, [], start, end)
    check(5 <= len(rows) <= 128 and {row["entity_id"] for row in rows} == {*TRACKERS, SENTINEL}, "qa_history_not_recorded")
    check([row["state"] for row in rows if row["entity_id"] == SENTINEL] == [marker + "0", marker + "1"], "qa_history_marker")
    return {"start": start, "end": end, "rows": rows}


def entry_scope(entries):
    """Count only fixed categories; permit the normal enabled system entries."""
    check(type(entries) is list and len(entries) <= 16, 'qa_entry_count_bound')
    domains = dict.fromkeys(('homecircle', 'hassio', 'backup', 'analytics', 'other'), 0)
    sources = dict.fromkeys(('system', 'user', 'other'), 0)
    allowed = True
    for entry in entries:
        domain = entry.domain if entry.domain in domains else 'other'
        source = entry.source if entry.source in sources else 'other'
        domains[domain] += 1
        sources[source] += 1
        if domain == 'homecircle':
            allowed = allowed and source == 'user'
            continue
        if domain not in {'hassio', 'backup', 'analytics'} or source != 'system' or entry.disabled_by is not None:
            allowed = False
    allowed = allowed and all(domains[name] <= 1 for name in ('homecircle', 'hassio', 'backup', 'analytics'))
    return {'total': len(entries), 'domains': domains, 'sources': sources,
            'system_entries_ready': allowed and domains['hassio'] == domains['backup'] == domains['analytics'] == 1,
            'entry_scope_allowed': allowed}

async def ensure_entry_scope(hass, receipt):
    """The normal discovery dispatcher creates system entries at the started event."""
    def ready():
        value = entry_scope(hass.config_entries.async_entries())
        receipt['entry_scope'] = value
        check(value['entry_scope_allowed'], 'qa_only_owned_or_system_entries')
        return value['system_entries_ready']
    await wait_for(ready, 60)

def digest(value):
    if not isinstance(value, bytes):
        value = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(value).hexdigest()

def process():
    fields = Path("/proc/self/stat").read_text().rsplit(")", 1)[1].split()
    return {"pid": os.getpid(), "start_ticks": int(fields[19])}

def guard_files(directory):
    root = directory / ".storage/homecircle_findmy/recovery_guard"
    check(root.is_dir() and not root.is_symlink(), "qa_guard_path")
    values = {}
    for path in root.rglob("*"):
        check(not path.is_symlink(), "qa_guard_symlink")
        if path.is_file():
            check(stat.S_IMODE(path.stat().st_mode) == 0o600, "qa_guard_file_mode")
            raw = path.read_bytes()
            values[path.relative_to(root).as_posix()] = {"bytes": len(raw), "sha256": digest(raw)}
    check(bool(values), "qa_guard_empty")
    return digest(values)

async def wait_for(predicate, seconds=120):
    async with asyncio.timeout(seconds):
        while not predicate():
            await asyncio.sleep(0.2)

def tracker_state(hass, state, marker):
    for index, tracker in enumerate(TRACKERS):
        hass.states.async_set(tracker, state,
            {"friendly_name": f"Synthetic Backup tracker {index + 1}", "source_type": "gps",
             "latitude": 0.0, "longitude": 0.0, "gps_accuracy": 5,
             "qa_backup_marker": marker})

def integrity(hass):
    from homeassistant.components.recorder.util import session_scope

    with session_scope(hass=hass, read_only=True) as session:
        rows = session.execute(text("PRAGMA integrity_check")).fetchall()
    return len(rows) == 1 and tuple(rows[0]) == ("ok",)

async def recorder_ready(hass):
    instance = get_instance(hass)
    check(instance.async_db_ready.done() and instance.async_db_ready.result() is True
          and instance.recording and instance.enabled and instance.is_running
          and str(instance.dialect_name) == "sqlite", "qa_recorder_ready")
    manager = async_get_manager(hass)
    platform = manager.platforms.get("recorder")
    check(platform is not None and platform.__name__ == "homeassistant.components.recorder.backup"
          and platform.async_pre_backup.__module__ == platform.async_post_backup.__module__ == platform.__name__,
          "qa_recorder_backup_platform")
    await instance.async_block_till_done()
    check(await instance.async_add_executor_job(integrity, hass), "qa_recorder_integrity")
    check(not any(domain == "recorder" and issue_id == "backup_failed_out_of_resources"
                  for domain, issue_id in ir.async_get(hass).issues), "qa_recorder_backup_issue")
    return instance

async def rows_for(hass, people, start, end):
    instance = await recorder_ready(hass)
    values = await instance.async_add_executor_job(partial(history.get_significant_states,
        hass, dt_util.utc_from_timestamp(start), dt_util.utc_from_timestamp(end),
        entity_ids=[*people, *TRACKERS, SENTINEL], include_start_time_state=False,
        significant_changes_only=False, minimal_response=False, no_attributes=False))
    check(set(values) <= {*people, *TRACKERS, SENTINEL}, "qa_history_entities")
    result = []
    for entity_id, states in sorted(values.items()):
        check(len(states) <= 128, "qa_history_bound")
        for state in states:
            result.append({"entity_id": entity_id, "state": state.state,
                           "last_updated": state.last_updated.timestamp(),
                           "last_changed": state.last_changed.timestamp(),
                           "attributes_sha256": digest(dict(state.attributes))})
    return result

async def recorder_receipt(hass, baseline, inputs, postrestore=None):
    people, expected = baseline["active"]["people"], baseline["history"]
    actual = await rows_for(hass, people, expected["start"], expected["end"])
    check(actual == expected["rows"], "qa_prebackup_history_changed")
    later = []
    if inputs["generation"] == "after_restore":
        window = inputs["external_proof"]["postbackup_window"]
        check(inputs["external_proof"]["token"] == baseline["token"]
              and window["start"] > expected["end"], "qa_external_history_window")
        later = await rows_for(hass, people, window["start"], window["end"])
        check(not later, "qa_postbackup_history_not_rolled_back")
    restored = None
    if postrestore is not None:
        restored = await rows_for(hass, people, postrestore["start"], postrestore["end"])
        check(restored == postrestore["rows"], "qa_postrestore_history_changed")
    return {"ready": True, "prebackup_rows": len(actual), "prebackup_sha256": digest(actual),
            "prebackup_exact_match": True, "postbackup_marker_rows": len(later),
            "postbackup_marker_absent": not later,
            "postrestore_rows": len(restored) if restored is not None else None,
            "postrestore_sha256": digest(restored) if restored is not None else None,
            "postrestore_exact_match": True if restored is not None else None,
            "integrity_ok": True, "backup_platform_registered": True, "commit_proven": True,
            "no_backup_failure_issue": True}


DEPS_SITE = Path("/config/deps/lib/python3.14/site-packages")
REQUIREMENTS = ("life360==7.2.0", "protobuf>=6.32.0,<8.0.0", "anisette==1.2.4",
                "unicorn==2.1.4", "srp==1.0.22", "beautifulsoup4==4.13.3")
MODULES = {"life360": "life360", "protobuf": "google.protobuf", "anisette": "anisette",
           "unicorn": "unicorn", "srp": "srp", "beautifulsoup4": "bs4"}
ENTRY_STATES = {"loaded", "not_loaded", "setup_in_progress", "setup_error", "setup_retry",
                "migration_error", "failed_unload", "unload_in_progress"}


def dependency_packages():
    """Metadata and import-spec probes only; never import a native/provider package."""
    from packaging.requirements import Requirement

    result = {}
    for raw in REQUIREMENTS:
        requirement = Requirement(raw)
        name = requirement.name.lower().replace("_", "-")
        item = {"available": False, "satisfies_requirement": False, "origin_config_deps": False,
                "metadata_error": False, "version": None, "loaded_module_present": False,
                "origin_probe": "unavailable"}
        try:
            package = metadata.distribution(requirement.name)
            version = package.version
            check(isinstance(version, str) and re.fullmatch(r"[A-Za-z0-9_.+-]{1,64}", version),
                  "qa_dependency_version_metadata")
            item.update(available=True, version=version,
                        satisfies_requirement=requirement.specifier.contains(version, prereleases=True))
            loaded = sys.modules.get(MODULES[name])
            if loaded is not None:
                item["loaded_module_present"] = True
                item["origin_probe"] = "loaded_module"
                origin = getattr(loaded, "__file__", None)
            else:
                item["origin_probe"] = "import_spec"
                spec = importlib.util.find_spec(MODULES[name])
                origin = spec.origin if spec is not None else None
            item["origin_config_deps"] = Path(package.locate_file("")).resolve() == DEPS_SITE \
                and origin is not None and Path(origin).resolve().is_relative_to(DEPS_SITE)
        except metadata.PackageNotFoundError:
            pass
        except Exception:
            item["metadata_error"] = True
        result[name] = item
    return result


def dependency_fixture_at(directory, inputs, skip_pip):
    from .dependency_probe import observe
    check(inputs.get('dependency_fixture') is None and inputs.get('dependency_inventory') is None,
        'qa_no_prepared_dependency_inputs')
    value = observe()
    check(type(skip_pip) is bool and skip_pip is False, "qa_normal_requirements_enabled")
    value["skip_pip"] = skip_pip
    check(value['config_deps_empty'] and value['ordinary_pip_target_unset']
        and value['constraints_match'] and value['docker_environment'] and value['closure_graph_checked'],
        'qa_normal_managed_requirement_environment')
    check(all(item['available'] and item['metadata_system_origin'] and item['constraints_satisfied']
        and item['python_satisfied'] for item in value['closure'].values()), 'qa_normal_dependency_closure')
    check(all(item['satisfies_requirement'] and item['module_system_origin']
        for item in value['direct'].values()), 'qa_normal_direct_dependencies')
    return value


async def guard_receipt(hass, entry, *, restored):
    from custom_components.homecircle.findmy_recovery_guard import (
        get_recovery_guard, RecoveryGuardReviewRequired)
    accounts = entry.options['findmy_accounts']
    check(len(accounts) == 1, 'qa_one_saved_account_guard')
    identity = next(iter(accounts.values()))['account_identity']
    from custom_components.homecircle.findmy_identity import authenticated_identity
    clients = entry.runtime_data.managed_trackers['findmy'].clients
    check(len(clients) == 1 and authenticated_identity(next(iter(clients.values())).account.to_json()) == identity,
        'qa_guard_actual_sdk_identity')
    guard = get_recovery_guard(hass)
    status = await guard.status(identity)
    check(type(status) is dict and set(status) == {'rejected','uncertain','pending','verified',
        'unresolved','limit','blocked','review_required'}, 'qa_guard_status_shape')
    check(status['uncertain'] == status['pending'] == status['verified'] == 0
        and status['unresolved'] == status['rejected'] and status['limit'] == 3
        and type(status['rejected']) is int and status['rejected'] in {2,3}
        and status['review_required'] is restored
        and status['blocked'] is (restored or status['rejected'] >= 3), 'qa_guard_rollback_state')
    witness = Path(hass.config.path('.cache/homecircle_findmy/recovery_guard'))
    refused_before_body = False
    if restored:
        check(status['rejected'] == 2 and not witness.exists(), 'qa_guard_missing_restore_witness')
        entered = False
        try:
            async with guard.attempt(identity):
                entered = True
        except RecoveryGuardReviewRequired:
            refused_before_body = not entered
        check(refused_before_body, 'qa_guard_real_attempt_refused_before_body')
    return {'identity_matches_saved_sdk_account': True, 'counter': status['rejected'],
        'blocked': status['blocked'], 'review_required': status['review_required'],
        'witness_absent': not witness.exists(), 'attempt_refused_before_body': refused_before_body,
        'manual_guard_imports': 0, 'owner_acknowledgments_after_restore': 0}


def startup_receipt():
    """Require nonvacuous real startup attempts at the installed denial seams."""
    value = startup_boundary.snapshot()
    booleans = ('installed_before_product_import', 'patches_intact', 'deny_all_external_aiohttp',
        'python_socket_audit_installed', 'product_manifest_unchanged', 'normal_requirement_subprocesses_unmodified')
    from custom_components._ordinary_boundary import COUNTERS, TARGETS
    check(type(value) is dict and set(value) == {'schema','boundary_revision','loaded_target_kinds',*booleans,*COUNTERS}
        and type(value['schema']) is int and value['schema'] == 2
        and type(value['boundary_revision']) is int and value['boundary_revision'] == 2
        and all(value[key] is True for key in booleans)
        and value['loaded_target_kinds'] == sorted(TARGETS.values())
        and all(type(value[key]) is int and 0 <= value[key] <= 1000000 for key in COUNTERS), 'qa_startup_boundary_shape')
    check(value['life360_sessions_created'] >= 1 and value['life360_requests_denied'] >= 1
        and sum(value[key] for key in ('apple_legacy_requests_denied','apple_bounded_requests_denied',
        'apple_report_requests_denied')) >= 1, 'qa_real_provider_attempts_required')
    check(all(value[key] == 0 for key in ('recovery_before_dispatch_calls','recovery_command_calls',
        'recovery_transport_attempts_denied')), 'qa_no_recovery_attempts_required')
    return value


async def runtime_details(hass, entry, selection, inputs):
    """Read the actual enabled source91 runtime after the closed-boot grant."""
    assert_enabled(hass, entry)
    module = sys.modules["custom_components.homecircle"]
    expected = Path(hass.config.path("custom_components/homecircle/__init__.py"))
    source_sha = await hass.async_add_executor_job(lambda: digest(Path(module.__file__).read_bytes()))
    check(await hass.async_add_executor_job(lambda: Path(module.__file__).resolve() == expected.resolve())
          and source_sha == inputs["candidate_inventory"]["__init__.py"]["sha256"], "qa_loaded_source")
    runtime = entry.runtime_data
    check(runtime.config == dict(entry.options), "qa_enabled_runtime_settings")
    from custom_components.homecircle import api, frontend
    from custom_components.homecircle.findmy_provider import DirectFindMy
    from custom_components.homecircle.life360_direct import DirectLife360
    findmy = runtime.managed_trackers["findmy"]
    life360 = runtime.managed_trackers["life360"]
    check(type(findmy) is DirectFindMy and type(life360) is DirectLife360,
          "qa_actual_provider_instances")
    life360_unique = {row["unique_id"] for row in selection["joins"] if row["kind"] == "person"}
    check(len(life360.trackers) == 2
          and set(life360.trackers) == {value.removeprefix("homecircle_life360_") for value in life360_unique}
          and {tracker.unique_id for tracker in life360.trackers.values()} == life360_unique,
          "qa_actual_life360_registry_restore")
    check(all(hass.states.get(row["entity_id"]) is not None for row in selection["joins"]),
          "qa_actual_selected_tracker_states")
    check(len(findmy.clients) == 1 and len(findmy.vaults) == 1 and len(findmy.trackers) == 1
          and sum(len(items) for items in findmy.trackers.values()) == 2
          and sum(bool(tracker.report) for items in findmy.trackers.values() for tracker in items.values()) == 2,
          "qa_actual_findmy_session_restore")
    projected = api.snapshot(runtime)["members"]
    expected_ids = {row["entity_id"] for row in selection["joins"]}
    check(len(projected) == 4 and {row["id"] for row in projected} == expected_ids, "qa_runtime_selection")
    for row in projected:
        setting = entry.options["members"][row["id"]]
        check(row["name"] == setting["display_name"] and row["kind"] == setting["kind"]
              and row["map_visible"] is setting["show_on_map"], "qa_runtime_member_settings")
    photo_member = next(row["entity_id"] for row in selection["joins"] if row["kind"] == "person")
    check(entry.options["members"][photo_member].get("picture_id") == PHOTO_ID
          and next(row["picture"] for row in projected if row["id"] == photo_member) == "/api/image/serve/" + PHOTO_ID + "/512x512",
          "qa_runtime_seeded_photo")
    from homeassistant.components import image_upload
    check(await hass.async_add_executor_job(lambda: digest(Path(image_upload.__file__).read_bytes())) == IMAGE_API_SHA256,
          "qa_pinned_image_api")
    collection = hass.data["image_upload"]
    records = list(collection.async_items())
    check(len(records) == 1 and records[0] == {"id": PHOTO_ID, "filesize": len(PHOTO_PNG), "content_type": "image/png",
          "name": "synthetic.png", "uploaded_at": "2026-01-01T00:00:00+00:00"}, "qa_seeded_image_metadata")
    photo = collection.image_dir / PHOTO_ID / "original"
    check(await hass.async_add_executor_job(lambda: photo.is_file() and not photo.is_symlink()
          and digest(photo.read_bytes()) == PHOTO_SHA256), "qa_seeded_image_original")
    bundle = await hass.async_add_executor_job(Path(hass.config.path("custom_components/homecircle/frontend/homecircle-card.js")).read_bytes)
    url = await hass.async_add_executor_job(frontend.resource_url)
    port = hass.http.server_port
    check(type(port) is int and 1 <= port <= 65535 and hass.http.context is None, "qa_http_fixture")
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30), trust_env=False) as session:
        for suffix, expected_body in ((url, bundle), ("/api/image/serve/" + PHOTO_ID + "/original", PHOTO_PNG)):
            async with session.get(f"http://127.0.0.1:{port}" + suffix, allow_redirects=False) as response:
                check(response.status == 200, "qa_seeded_http_status")
                body = bytearray()
                async for chunk in response.content.iter_chunked(65536):
                    body.extend(chunk)
                    check(len(body) <= len(expected_body), "qa_seeded_http_bound")
                check(bytes(body) == expected_body, "qa_seeded_http_bytes")
    # Background startup polls may be scheduled after the entry becomes loaded.
    async def attempts_ready():
        async with asyncio.timeout(60):
            while True:
                value = startup_boundary.snapshot()
                if value.get("life360_requests_denied", 0) and sum(value.get(key, 0) for key in
                    ("apple_legacy_requests_denied", "apple_bounded_requests_denied", "apple_report_requests_denied")):
                    return
                await asyncio.sleep(0.2)
    await attempts_ready()
    return {"runtime_loaded_source_sha256": source_sha, "runtime_selection_checked": True,
            "actual_findmy_session_restored": True, "synthetic_photo_preserved": True,
            "static_served_bundle_matches": True, "startup_boundary": startup_receipt()}


class Rehearsal:
    def __init__(self, hass):
        self.hass = hass
        self.directory = Path(hass.config.config_dir)
        self.control = self.directory / CONTROL

    async def raw_snapshot(self, entry, create=False):
        selection = await self.hass.async_add_executor_job(selected_mapping, self.directory, entry)
        joins = await ensure_selected_registry(self.hass, entry, selection, create=create)
        observed = await self.hass.async_add_executor_job(raw_storage, self.directory, entry)
        return observed, joins

    async def run(self, phase, inputs):
        hass, directory, name = self.hass, self.directory, phase["phase"]
        receipt = {"schema": 1, "token": phase["token"], "generation": inputs["generation"],
                   "branch_commit": inputs["branch_commit"], "phase": name, "core_version": CORE_VERSION,
                   "entry_disabled": False, "entry_loaded": True, "candidate_imported": True,
                   "owner_accounts_used": False, "production_configuration_used": False,
                   "provider_request_attempt_counts_measured": False, "recovery_proof_attempt_counts_measured": False}
        stage = "raw_storage"
        try:
            check(getattr(self, "closed_boot_grant_verified", False) is True, "qa_closed_boot_grant_required")
            receipt["closed_boot_grant_verified"] = True
            check(CORE_VERSION == "2026.10.2", "qa_core_version")
            users = await hass.auth.async_get_users()
            check(not any(not user.system_generated for user in users), "qa_no_owner_accounts")
            await ensure_entry_scope(hass, receipt)
            entry = current_entry(hass)
            stage = "package_bytes"
            receipt.update(await hass.async_add_executor_job(package_at, directory, inputs))
            stage = "normal_dependencies"
            receipt["normal_dependencies"] = await hass.async_add_executor_job(dependency_fixture_at, directory, inputs, hass.config.skip_pip)
            stage = "recovery_guard"
            receipt["recovery_guard"] = await guard_receipt(hass, entry, restored=name == "restart_enabled")
            receipt["process"] = process()
            stage = "saved_configuration"
            receipt["ha_config_entry_saved"] = await persist_verified_entry(hass, directory, entry, update=name == "baseline_enabled")
            stage = "selected_storage"
            observed, joins = await self.raw_snapshot(entry)
            proof = await hass.async_add_executor_job(read_json, self.control / "storage-proof-private.json")
            expected = proof["mutation"] if name == "mutated_enabled" else proof["baseline"]
            check(type(expected) is dict and all(observed[key] == expected[key] for key in RAW_KEYS), "qa_raw_saved_storage_changed")
            receipt["observed_storage"] = observed
            receipt["joins_sha256"] = joins
            receipt["guard_sha256"] = await hass.async_add_executor_job(guard_files, directory)
            receipt["nonempty_options"] = bool(entry.options)
            receipt["nonempty_place"] = bool(entry.options.get("places"))
            selection = await hass.async_add_executor_job(selected_mapping, directory, entry)
            stage = "runtime_details"
            receipt.update(await runtime_details(hass, entry, selection, inputs))
            receipt["provider_request_attempt_counts_measured"] = True
            receipt["recovery_proof_attempt_counts_measured"] = True
            stage = "recorder"
            await recorder_ready(hass)
            baseline_path = self.control / "baseline.json"
            if name == "baseline_enabled":
                check(not baseline_path.exists(), "qa_baseline_collision")
                recorded = await record_window(hass, [], "before_backup_")
                baseline = {"schema": 1, "token": phase["token"], "active": {"people": []}, "history": recorded,
                    "observed_storage": observed, "joins_sha256": joins, "guard_sha256": receipt["guard_sha256"]}
                await hass.async_add_executor_job(write_json, baseline_path, baseline)
                await hass.async_add_executor_job(write_json, self.control / "storage-joins-private.json", {"schema": 1, "sha256": joins})
            else:
                baseline = await hass.async_add_executor_job(read_json, baseline_path)
            postrestore = None
            if name == "mutated_enabled":
                check(observed != baseline["observed_storage"], "qa_mutation_missing")
                recorded = await record_window(hass, [], "after_backup_")
                external = {"schema": 1, "token": phase["token"], "generation": "before_restore", "branch_commit": inputs["branch_commit"],
                    "postbackup_window": {"start": recorded["start"], "end": recorded["end"], "rows": len(recorded["rows"]), "sha256": digest(recorded["rows"])}}
                await hass.async_add_executor_job(write_json, self.control / "external-proof.json", external)
            if name == "restart_enabled":
                check(observed == baseline["observed_storage"] and joins == baseline["joins_sha256"] == inputs["expected_joins_sha256"], "qa_restored_selected_join_changed")
                check(receipt["guard_sha256"] == inputs["backup_guard_sha256"], "qa_restored_old_guard_unchanged")
                if False:
                    postrestore = await record_window(hass, [], "after_restore_")
                    await hass.async_add_executor_job(write_json, self.control / "postrestore-history.json", postrestore)
                else:
                    postrestore = await hass.async_add_executor_job(read_json, self.control / "postrestore-history.json")
            receipt["recorder"] = await recorder_receipt(hass, baseline, inputs, postrestore)
            if name == "mutated_enabled":
                receipt["recorder"]["postbackup_marker_rows"] = len(recorded["rows"])
                receipt["recorder"]["postbackup_marker_absent"] = False
            assert_enabled(hass, entry)
            receipt["outcome"] = "passed"
        except Exception as error:
            details = await hass.async_add_executor_job(failure_diagnostics.project, error, Path(__file__).parent, Refused)
            if stage == "normal_dependencies":
                from .dependency_probe import diagnostic_metadata
                details["dependency_metadata"] = await hass.async_add_executor_job(diagnostic_metadata)
            receipt.update(outcome="failed", stage=stage, **details)
            _LOGGER.error("Disposable saved-storage phase failed at %s (%s)", stage, type(error).__name__)
        await hass.async_add_executor_job(write_json, directory / RESULTS / (name + ".json"), receipt)

    async def poll(self):
        seen, observed_boot, boot_request = set(), False, None
        stage = "control"
        while self.hass.is_running:
            try:
                inputs = await self.hass.async_add_executor_job(inputs_at, self.directory)
                path = self.control / "phase.json"
                if path.exists():
                    phase = await self.hass.async_add_executor_job(read_json, path)
                    name, token, generation = phase.get("phase"), phase.get("token"), phase.get("generation")
                    check(type(phase) is dict and set(phase) == {"schema", "token", "phase", "generation", "branch_commit"}
                          and phase["schema"] == 1 and name in PHASES and name != "automatic_restored_enabled"
                          and type(token) is str and re.fullmatch("[0-9a-f]{32}", token)
                          and generation == inputs["generation"] and phase["branch_commit"] == inputs["branch_commit"]
                          and generation == ("before_restore" if name in PHASES[:2] else "after_restore"), "qa_phase_identity")
                    nonce_path = self.control / "job-nonce.json"
                    if nonce_path.exists():
                        prior = await self.hass.async_add_executor_job(read_json, nonce_path)
                        check(type(prior) is dict and set(prior) == {"token", "generation"}
                              and prior == {"token": token, "generation": generation}, "qa_job_nonce")
                    else:
                        check(name in {"baseline_enabled", "restart_enabled"}, "qa_first_phase")
                        await self.hass.async_add_executor_job(write_json, nonce_path, {"token": token, "generation": generation})
                    if not observed_boot:
                        entry = current_entry(self.hass)
                        baseline_path = self.control / "baseline.json"
                        automatic = generation == "before_restore" and name == "baseline_enabled" and baseline_path.exists()
                        if boot_request is None:
                            boot_request = closed_boot_request(phase, inputs, automatic)
                            await self.hass.async_add_executor_job(write_json, self.control / "boot-request.json", boot_request)
                        check(boot_request['token'] == token and boot_request['generation'] == generation
                              and boot_request['phase'] == name and boot_request['branch_commit'] == inputs['branch_commit'], 'qa_boot_request_control_changed')
                        assert_enabled(self.hass, entry)
                        if not await self.hass.async_add_executor_job(consume_closed_boot_grant, self.control, boot_request):
                            await asyncio.sleep(0.5)
                            continue
                        self.closed_boot_grant_verified = True
                        inputs = await reload_granted_inputs(self.hass, self.directory, boot_request, phase)
                        assert_enabled(self.hass, entry)
                        if generation == "before_restore" and name == "baseline_enabled" and baseline_path.exists():
                            entry = current_entry(self.hass)
                            baseline = await self.hass.async_add_executor_job(read_json, baseline_path)
                            observed, joins = await self.raw_snapshot(entry)
                            guard_sha = await self.hass.async_add_executor_job(guard_files, self.directory)
                            stage = "package_bytes"
                            package = await self.hass.async_add_executor_job(package_at, self.directory, inputs)
                            stage = "normal_dependencies"
                            dependencies = await self.hass.async_add_executor_job(dependency_fixture_at, self.directory, inputs, self.hass.config.skip_pip)
                            selection = await self.hass.async_add_executor_job(selected_mapping, self.directory, entry)
                            stage = "runtime_details"
                            runtime = await runtime_details(self.hass, entry, selection, inputs)
                            check(observed == baseline["observed_storage"] and joins == baseline["joins_sha256"]
                                  and guard_sha == baseline["guard_sha256"], "qa_automatic_raw_baseline_changed")
                            stage = "recovery_guard"
                            recovery = await guard_receipt(self.hass, entry, restored=True)
                            stage = "recorder"
                            postrestore = await record_window(self.hass, [], "after_restore_")
                            await self.hass.async_add_executor_job(write_json, self.control / "postrestore-history.json", postrestore)
                            history_inputs = {**inputs, 'generation': 'after_restore'}
                            recorder = await recorder_receipt(self.hass, baseline, history_inputs, postrestore)
                            await self.hass.async_add_executor_job(write_json, self.control / "restore-barrier.json",
                                {"schema": 1, "token": token, "generation": generation, "branch_commit": inputs["branch_commit"],
                                 "core_version": CORE_VERSION, "phase": "automatic_restored_enabled", "outcome": "passed",
                                 "owner_accounts_used": False, "production_configuration_used": False,
                                 "process": process(), "entry_disabled": False, "entry_loaded": True, "candidate_imported": True,
                                 "ha_config_entry_saved": True, "closed_boot_grant_verified": True, "observed_storage": observed, "joins_sha256": joins, "guard_sha256": guard_sha,
                                 **package, **runtime, "recorder": recorder, "normal_dependencies": dependencies, "recovery_guard": recovery,
                                 "provider_request_attempt_counts_measured": True, "recovery_proof_attempt_counts_measured": True})
                            seen.add((generation, name))
                        observed_boot = True
                    check(boot_request["token"] == token and boot_request["generation"] == generation
                          and boot_request["phase"] == name and boot_request["branch_commit"] == inputs["branch_commit"]
                          and boot_request["process"] == process(), "qa_consumed_grant_control_changed")
                    identity = (generation, name)
                    if identity not in seen:
                        seen.add(identity)
                        result_path = self.directory / RESULTS / (name + ".json")
                        check(not result_path.exists(), "qa_phase_receipt_collision")
                        await self.run(phase, inputs)
            except Exception as error:
                if (boot_request is not None and boot_request.get('purpose') == 'automatic_restore'
                        and boot_request.get('process') == process()):
                    details = await self.hass.async_add_executor_job(
                        failure_diagnostics.project, error, Path(__file__).parent, Refused)
                    if stage == 'normal_dependencies':
                        from .dependency_probe import diagnostic_metadata
                        details['dependency_metadata'] = await self.hass.async_add_executor_job(diagnostic_metadata)
                    await self.hass.async_add_executor_job(write_json, self.control / 'restore-barrier.json',
                        {'schema':1,'phase':'automatic_restored_enabled','outcome':'failed',
                         'token':boot_request['token'],'generation':boot_request['generation'],
                         'branch_commit':boot_request['branch_commit'],'process':process(),
                         'closed_boot_grant_verified':getattr(self,'closed_boot_grant_verified',False) is True,
                         'stage':stage,**details})
                _LOGGER.error("Disposable saved-storage control refused (%s)", type(error).__name__)
                return
            await asyncio.sleep(0.5)


async def reload_granted_inputs(hass, directory, request, phase):
    # The host commits complete inputs before publishing its grant. Re-read after
    # consuming that grant so no earlier local snapshot can omit external proof.
    value = await hass.async_add_executor_job(inputs_at, directory)
    current_phase = await hass.async_add_executor_job(read_json, directory / CONTROL / 'phase.json')
    check(current_phase == phase and request['process'] == process(), 'qa_granted_control_changed')
    check(all(value.get(key) == request[key] for key in
        ('source_commit','candidate_sha256','branch_commit','generation')), 'qa_granted_inputs_changed')
    check(phase['token'] == request['token'] and phase['phase'] == request['phase']
        and phase['generation'] == request['generation'] and phase['branch_commit'] == request['branch_commit'],
        'qa_granted_phase_changed')
    if request['purpose'] == 'automatic_restore':
        check(type(value.get('external_proof')) is dict, 'qa_granted_external_proof_missing')
    return value


def closed_boot_request(phase, inputs, automatic):
    return {'schema':1,'source_commit':inputs['source_commit'],'candidate_sha256':CANDIDATE,
        'token':phase['token'],'generation':phase['generation'],'branch_commit':inputs['branch_commit'],
        'phase':phase['phase'],'purpose':'automatic_restore' if automatic else 'phase',
        'process':process(),'boot_nonce':secrets.token_hex(16)}

def consume_closed_boot_grant(control, request):
    path=control/'closed-boot-grant.json'
    try:descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    except FileNotFoundError:return False
    try:
        before=os.fstat(descriptor)
        check(stat.S_ISREG(before.st_mode) and before.st_uid==os.getuid() and before.st_nlink==1
            and stat.S_IMODE(before.st_mode)==0o600 and 0<before.st_size<=4096, 'qa_closed_grant_path')
        raw=os.read(descriptor,4097)
        after=os.fstat(descriptor);now=path.lstat()
        identity=lambda st:(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_mode,st.st_uid,st.st_nlink)
        check(identity(before)==identity(after)==identity(now) and len(raw)==before.st_size, 'qa_closed_grant_stable')
        def unique(pairs):
            value={}
            for key,item in pairs:
                check(key not in value,'qa_closed_grant_duplicate');value[key]=item
            return value
        value=json.loads(raw,object_pairs_hook=unique)
        expected={**request,'external_network_closed':True,'default_conditions_verified':request['purpose']=='automatic_restore'}
        check(type(value)is dict and set(value)==set(expected) and value==expected
            and type(value['schema'])is int and value['schema']==1
            and type(value['external_network_closed'])is bool and type(value['default_conditions_verified'])is bool
            and type(value['process'])is dict and set(value['process'])=={'pid','start_ticks'}
            and all(type(v)is int and v>0 for v in value['process'].values())
            and type(request['source_commit']) is str and re.fullmatch('[0-9a-f]{40}',request['source_commit'])
            and request['candidate_sha256']==CANDIDATE and request['process']==process(), 'qa_closed_grant_identity')
        # No second read after consume; the exact opened inode is checked first.
        check(identity(path.lstat())==identity(before),'qa_closed_grant_replaced')
        path.unlink()
        check(not path.exists() and not path.is_symlink(),'qa_closed_grant_consumed')
        return True
    finally:os.close(descriptor)

async def async_setup(hass, config):
    if config.get(DOMAIN, {}).get("disposable") is not True:
        return False
    try:
        startup_boundary.install(hass)
    except startup_boundary.StartupBoundaryRefused:
        # Metadata only: failure must not turn a dependency setup refusal into
        # an unexplained host grant timeout, or disclose an import/SDK exception.
        write_json(Path(hass.config.config_dir) / CONTROL / "startup-install-failure.json",
                   {"schema": 1, "outcome": "failed", "stage": "startup_boundary_install",
                    "failure_type": "StartupBoundaryRefused",
                    "failure_code": "qa_startup_boundary_install_failed", "process": process()})
        return False
    async def started(_event):
        hass.async_create_task(Rehearsal(hass).poll(), DOMAIN)
    if hass.is_running:
        hass.async_create_task(Rehearsal(hass).poll(), DOMAIN)
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, started)
    return True
