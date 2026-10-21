"""Fresh-guest disabled saved-storage readback; never load the product integration."""
from __future__ import annotations
import sys
if sys.platform != "linux":
    raise RuntimeError("qa_linux_required")
import asyncio
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
from homeassistant.config_entries import ConfigEntryDisabler, ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, __version__ as CORE_VERSION
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from homeassistant.util import dt as dt_util
DOMAIN = "homecircle_safe_restore_qa"
CONTROL = "homecircle-safe-restore-qa-control"
RESULTS = "homecircle-safe-restore-qa-results"
CANDIDATE = "004c9bc4a968ad395e18033837cb42f5bd1d8719a8d90fc778fd20be4ff08f97"
VERIFIED_TITLE = "Synthetic saved storage verified"
PHASES = ("baseline_disabled", "mutated_disabled", "automatic_restored_disabled", "repaired_storage_disabled", "restart_disabled")
TRACKERS = ("device_tracker.homecircle_safe_restore_qa_a", "device_tracker.homecircle_safe_restore_qa_b")
SENTINEL = "sensor.homecircle_safe_restore_qa_sentinel"
RAW_KEYS = {"config_sha256", "key_sha256", "vault_sha256", "selection_sha256", "credentials_sha256"}
SETUP_STEPS = frozenset({"raw_storage", "explicit_registry", "recorder", "unclassified"})
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
    value = read_json(directory / CONTROL / "inputs.json")
    check(value.get("schema") == 1 and value.get("core_version") == "2026.10.2"
          and value.get("candidate_sha256") == CANDIDATE, "qa_input_binding")
    check(type(value.get("branch_commit")) is str and re.fullmatch("[0-9a-f]{40}", value["branch_commit"])
          and value.get("generation") in {"before_restore", "after_restore"}, "qa_input_identity")
    inventory = value.get("candidate_inventory")
    check(type(inventory) is dict and len(inventory) == 113, "qa_inventory_count")
    for name, item in inventory.items():
        path = PurePosixPath(name)
        check(type(name) is str and name == path.as_posix() and not path.is_absolute()
              and ".." not in path.parts and "\\" not in name and type(item) is dict
              and set(item) == {"bytes", "sha256"} and type(item["bytes"]) is int
              and 0 <= item["bytes"] < 16 * 1024**2 and type(item["sha256"]) is str
              and re.fullmatch("[0-9a-f]{64}", item["sha256"]), "qa_inventory_member")
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
    check(actual == inputs["candidate_inventory"] and len(actual) == 113, "qa_package_bytes")
    return {"package_files_count": 113, "package_payload_sha256": digest(actual), "candidate_archive_sha256": CANDIDATE}

def assert_unimported(hass, entry):
    check(entry.disabled_by is ConfigEntryDisabler.USER and entry.state is ConfigEntryState.NOT_LOADED,
          "qa_disabled_entry_required")
    check(not any(name == "custom_components.homecircle" or name.startswith("custom_components.homecircle.")
                  for name in sys.modules), "qa_managed_candidate_imported")
    check("homecircle" not in hass.config.components and "homecircle" not in hass.data,
          "qa_managed_candidate_state")
    check(getattr(entry, "runtime_data", None) is None, "qa_product_runtime_present")

def current_entry(hass):
    entries = hass.config_entries.async_entries("homecircle")
    check(len(entries) == 1, "qa_one_disabled_entry")
    entry = entries[0]
    assert_unimported(hass, entry)
    return entry

async def persist_verified_entry(hass, directory, entry, update=False):
    assert_unimported(hass, entry)
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
                  and matches[0].get("disabled_by") == "user", "qa_title_store_identity")
            if (entry.title == VERIFIED_TITLE and matches[0].get("title") == VERIFIED_TITLE
                    and matches[0].get("data") == before["data"] and matches[0].get("options") == before["options"]):
                break
            await asyncio.sleep(0.25)
    assert_unimported(hass, entry)
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
                config_entry=entry, disabled_by=er.RegistryEntryDisabler.CONFIG_ENTRY, suggested_object_id=row["entity_id"].split(".", 1)[1], original_name="Synthetic saved tracker")
        check(record.entity_id == row["entity_id"] and record.unique_id == row["unique_id"]
              and record.config_entry_id == row["config_entry_id"] and record.platform == "homecircle"
              and record.disabled_by is er.RegistryEntryDisabler.CONFIG_ENTRY, "qa_selected_registry_identity")
    assert_unimported(hass, entry)
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
                break
            await asyncio.sleep(0.25)
    return digest(expected)

def raw_storage(directory, entry):
    saved = read_managed_json(directory, "core.config_entries")
    matches = [item for item in saved["data"]["entries"] if item.get("domain") == "homecircle"]
    check(len(matches) == 1 and matches[0]["entry_id"] == entry.entry_id and matches[0]["disabled_by"] == "user"
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
                   "entry_disabled": True, "entry_loaded": False, "candidate_imported": False,
                   "owner_accounts_used": False, "production_configuration_used": False,
                   "provider_request_attempt_counts_measured": False, "recovery_proof_attempt_counts_measured": False}
        stage = "raw_storage"
        try:
            check(CORE_VERSION == "2026.10.2", "qa_core_version")
            users = await hass.auth.async_get_users()
            check(not any(not user.system_generated for user in users), "qa_no_owner_accounts")
            await ensure_entry_scope(hass, receipt)
            entry = current_entry(hass)
            receipt.update(await hass.async_add_executor_job(package_at, directory, inputs))
            receipt["process"] = process()
            receipt["ha_config_entry_saved"] = await persist_verified_entry(hass, directory, entry, update=name == "baseline_disabled")
            observed, joins = await self.raw_snapshot(entry, create=name in {"baseline_disabled", "mutated_disabled"})
            proof = await hass.async_add_executor_job(read_json, self.control / "storage-proof-private.json")
            expected = proof["mutation"] if name == "mutated_disabled" else proof["baseline"]
            check(type(expected) is dict and all(observed[key] == expected[key] for key in RAW_KEYS), "qa_raw_saved_storage_changed")
            receipt["observed_storage"] = observed
            receipt["joins_sha256"] = joins
            receipt["guard_sha256"] = await hass.async_add_executor_job(guard_files, directory)
            receipt["nonempty_options"] = bool(entry.options)
            receipt["nonempty_place"] = bool(entry.options.get("places"))
            stage = "recorder"
            await recorder_ready(hass)
            baseline_path = self.control / "baseline.json"
            if name == "baseline_disabled":
                check(not baseline_path.exists(), "qa_baseline_collision")
                recorded = await record_window(hass, [], "before_backup_")
                baseline = {"schema": 1, "token": phase["token"], "active": {"people": []}, "history": recorded,
                    "observed_storage": observed, "joins_sha256": joins, "guard_sha256": receipt["guard_sha256"]}
                await hass.async_add_executor_job(write_json, baseline_path, baseline)
                await hass.async_add_executor_job(write_json, self.control / "storage-joins-private.json", {"schema": 1, "sha256": joins})
            else:
                baseline = await hass.async_add_executor_job(read_json, baseline_path)
            postrestore = None
            if name == "mutated_disabled":
                check(observed != baseline["observed_storage"], "qa_mutation_missing")
                recorded = await record_window(hass, [], "after_backup_")
                external = {"schema": 1, "token": phase["token"], "generation": "before_restore", "branch_commit": inputs["branch_commit"],
                    "postbackup_window": {"start": recorded["start"], "end": recorded["end"], "rows": len(recorded["rows"]), "sha256": digest(recorded["rows"])}}
                await hass.async_add_executor_job(write_json, self.control / "external-proof.json", external)
            if name in {"repaired_storage_disabled", "restart_disabled"}:
                check(observed == baseline["observed_storage"] and joins == baseline["joins_sha256"] == inputs["expected_joins_sha256"], "qa_restored_selected_join_changed")
                check(receipt["guard_sha256"] == inputs["latest_guard_sha256"], "qa_latest_guard_before_storage")
                if name == "repaired_storage_disabled":
                    postrestore = await record_window(hass, [], "after_restore_")
                    await hass.async_add_executor_job(write_json, self.control / "postrestore-history.json", postrestore)
                else:
                    postrestore = await hass.async_add_executor_job(read_json, self.control / "postrestore-history.json")
            receipt["recorder"] = await recorder_receipt(hass, baseline, inputs, postrestore)
            if name == "mutated_disabled":
                receipt["recorder"]["postbackup_marker_rows"] = len(recorded["rows"])
                receipt["recorder"]["postbackup_marker_absent"] = False
            assert_unimported(hass, entry)
            receipt["outcome"] = "passed"
        except Exception as error:
            receipt.update(outcome="failed", stage=stage, failure_type=type(error).__name__)
            if isinstance(error, Refused):
                receipt["failure_code"] = str(error)
            _LOGGER.error("Disposable saved-storage phase failed at %s (%s)", stage, type(error).__name__)
        await hass.async_add_executor_job(write_json, directory / RESULTS / (name + ".json"), receipt)

    async def poll(self):
        seen, observed_boot = set(), False
        while self.hass.is_running:
            try:
                inputs = await self.hass.async_add_executor_job(inputs_at, self.directory)
                path = self.control / "phase.json"
                if path.exists():
                    phase = await self.hass.async_add_executor_job(read_json, path)
                    name, token, generation = phase.get("phase"), phase.get("token"), phase.get("generation")
                    check(type(phase) is dict and set(phase) == {"schema", "token", "phase", "generation", "branch_commit"}
                          and phase["schema"] == 1 and name in PHASES and name != "automatic_restored_disabled"
                          and type(token) is str and re.fullmatch("[0-9a-f]{32}", token)
                          and generation == inputs["generation"] and phase["branch_commit"] == inputs["branch_commit"]
                          and generation == ("before_restore" if name in PHASES[:2] else "after_restore"), "qa_phase_identity")
                    nonce_path = self.control / "job-nonce.json"
                    if nonce_path.exists():
                        prior = await self.hass.async_add_executor_job(read_json, nonce_path)
                        check(type(prior) is dict and set(prior) == {"token", "generation"}
                              and prior == {"token": token, "generation": generation}, "qa_job_nonce")
                    else:
                        check(name in {"baseline_disabled", "repaired_storage_disabled"}, "qa_first_phase")
                        await self.hass.async_add_executor_job(write_json, nonce_path, {"token": token, "generation": generation})
                    if not observed_boot:
                        observed_boot = True
                        baseline_path = self.control / "baseline.json"
                        if generation == "before_restore" and name == "baseline_disabled" and baseline_path.exists():
                            entry = current_entry(self.hass)
                            baseline = await self.hass.async_add_executor_job(read_json, baseline_path)
                            observed, joins = await self.raw_snapshot(entry)
                            guard_sha = await self.hass.async_add_executor_job(guard_files, self.directory)
                            check(observed == baseline["observed_storage"] and joins == baseline["joins_sha256"]
                                  and guard_sha == baseline["guard_sha256"], "qa_automatic_raw_baseline_changed")
                            await self.hass.async_add_executor_job(write_json, self.control / "restore-barrier.json",
                                {"schema": 1, "token": token, "generation": generation, "branch_commit": inputs["branch_commit"],
                                 "process": process(), "entry_disabled": True, "entry_loaded": False, "candidate_imported": False,
                                 "ha_config_entry_saved": True, "observed_storage": observed, "joins_sha256": joins, "guard_sha256": guard_sha})
                            seen.add((generation, name))
                    identity = (generation, name)
                    if identity not in seen:
                        seen.add(identity)
                        result_path = self.directory / RESULTS / (name + ".json")
                        check(not result_path.exists(), "qa_phase_receipt_collision")
                        await self.run(phase, inputs)
            except Exception as error:
                _LOGGER.error("Disposable saved-storage control refused (%s)", type(error).__name__)
                return
            await asyncio.sleep(0.5)

async def async_setup(hass, config):
    if config.get(DOMAIN, {}).get("disposable") is not True:
        return False
    async def started(_event):
        hass.async_create_task(Rehearsal(hass).poll(), DOMAIN)
    if hass.is_running:
        hass.async_create_task(Rehearsal(hass).poll(), DOMAIN)
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, started)
    return True
