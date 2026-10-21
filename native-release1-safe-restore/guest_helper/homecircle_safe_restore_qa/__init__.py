"""Disposable native HAOS Supervisor-backup and Recorder acceptance helper.

Never package with HomeCircle. A backed-up disabled entry stays disabled through
restore's automatic boot. Only fresh controller instructions permit activation.
"""
from __future__ import annotations

import sys

if sys.platform != "linux":
    raise RuntimeError("qa_linux_required")

import asyncio
import base64
import io
from copy import deepcopy
from functools import partial
import hashlib
import json
import logging
import os
from pathlib import Path, PurePosixPath
import re
import stat

import aiohttp
from aiohttp.web_request import FileField
from multidict import CIMultiDict, CIMultiDictProxy
from homeassistant.components import image_upload as image_component, person as person_component
import probatio as vol
from .dependency_probe import observe
from sqlalchemy import text

from homeassistant.components.backup import async_get_manager
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.person import async_create_person, entities_in_person
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder import history
from homeassistant.config_entries import ConfigEntryDisabler, ConfigEntryState, SOURCE_USER
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, __version__ as CORE_VERSION
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from homeassistant.util import dt as dt_util

DOMAIN = "homecircle_safe_restore_qa"
CONTROL = "homecircle-safe-restore-qa-control"
RESULTS = "homecircle-safe-restore-qa-results"
CANDIDATE = "004c9bc4a968ad395e18033837cb42f5bd1d8719a8d90fc778fd20be4ff08f97"
PHASES = ("initialize", "initial_restart", "quarantine", "mutate", "automatic_disabled", "repaired_disabled", "reenabled", "restart")
TRACKERS = ("device_tracker.homecircle_safe_restore_qa_a", "device_tracker.homecircle_safe_restore_qa_b")
TRACKER_UIDS = ("homecircle-safe-restore-qa-synthetic-a", "homecircle-safe-restore-qa-synthetic-b")
PERSON_NAMES = ("Synthetic Backup Member A", "Synthetic Backup Member B")
SENTINEL = "sensor.homecircle_safe_restore_qa_sentinel"
UNRELATED = "/local/homecircle_safe_restore_qa_unrelated.js"
OWNED_URL = "/homecircle_static/homecircle-card.js"
GUARD_IDENTITY = "a" * 64
PLACE = 'zone.synthetic_park'
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAD0lEQVR4nGNgmPAAhCAUACTOBcF1AlBBAAAAAElFTkSuQmCC')
PNG_SHA = '3a51cbff9fe4d3958488319741b290925e0a0e22447ef2a03309427cfc7d3f0d'
API_SOURCES = {'image_upload':'cf857fb233a858f3af5774fa9d1c87ef855b65fa3827216fd515ed4d9fe115ab',
               'person':'de930932cb411f2ab60bb27919bd50c8b82aecb815b1dae7a004c71ce19277a7'}
_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({vol.Required("disposable"): vol.Boolean()})}, extra=vol.ALLOW_EXTRA)

class Refused(RuntimeError):
    """Only a fixed label, never provider or file contents."""


def check(condition, label):
    if not condition:
        raise Refused(label)


SETUP_STEPS = frozenset({'active_details', 'active_http_bundle', 'active_http_portrait', 'flow_assign_tracker', 'flow_confirm_save', 'flow_entry_loaded', 'flow_household', 'flow_member', 'flow_user', 'options_city_form', 'options_entry_loaded', 'options_save', 'options_start', 'person_create', 'person_registry', 'person_sources', 'person_states', 'portrait_api_sources', 'portrait_image_create', 'portrait_person_update', 'portrait_state', 'resource_initialization', 'snapshot', 'unclassified', 'unrelated_resource_create'})


def setup_mark(progress, step):
    """Only finite setup labels; never runtime values or entry metadata."""
    if progress is not None:
        progress["step"] = step if type(step) is str and step in SETUP_STEPS else "unclassified"


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


def read_json(path):
    check(path.is_file() and not path.is_symlink() and path.stat().st_size < 2 * 1024**2, "qa_input_path")
    return json.loads(path.read_text())


def write_json(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as output:
        json.dump(value, output, sort_keys=True, indent=2)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def inputs_at(directory):
    root = directory / CONTROL
    check(root.is_dir() and not root.is_symlink(), "qa_control_path")
    value = read_json(root / "inputs.json")
    check(value.get("schema") == 1 and value.get("core_version") == "2026.10.2", "qa_input_schema")
    check(value.get("candidate_sha256") == CANDIDATE, "qa_input_hashes")
    check(re.fullmatch(r"[0-9a-f]{40}", value.get("branch_commit", "")), "qa_branch")
    check(value.get("generation") in {"before_restore", "after_restore"}, "qa_generation")
    inventory = value.get("candidate_inventory")
    check(isinstance(inventory, dict) and len(inventory) == 113, "qa_inventory_count")
    for name, item in inventory.items():
        path = PurePosixPath(name)
        check(name == path.as_posix() and not path.is_absolute() and ".." not in path.parts
              and "\\" not in name and isinstance(item, dict) and set(item) == {"bytes", "sha256"}
              and type(item["bytes"]) is int and 0 <= item["bytes"] < 16 * 1024**2
              and re.fullmatch(r"[0-9a-f]{64}", item["sha256"]), "qa_inventory_member")
    if value["generation"] == "after_restore":
        for key in ("latest_guard_sha256", "backup_guard_sha256", "expected_snapshot_sha256",
                    "expected_quarantine_sha256", "expected_prebackup_sha256"):
            check(re.fullmatch(r"[0-9a-f]{64}", value.get(key, "")), "qa_external_hash")
        proof = value.get("external_proof")
        check(isinstance(proof, dict) and set(proof) == {"schema", "token", "generation", "branch_commit", "postbackup_window"}
              and proof["schema"] == 1 and proof["generation"] == "before_restore"
              and proof["branch_commit"] == value["branch_commit"]
              and re.fullmatch(r"[0-9a-f]{32,64}", proof["token"]), "qa_external_proof")
        window = proof["postbackup_window"]
        check(isinstance(window, dict) and set(window) == {"start", "end", "rows", "sha256"}
              and type(window["start"]) in (int, float) and type(window["end"]) in (int, float)
              and 0 < window["end"] - window["start"] < 120
              and type(window["rows"]) is int and 5 <= window["rows"] <= 128
              and re.fullmatch(r"[0-9a-f]{64}", window["sha256"]), "qa_external_window")
    return value


def package_at(directory, inputs):
    package = directory / "custom_components/homecircle"
    check(package.is_dir() and not package.is_symlink(), "qa_package_path")
    actual = {}
    for path in package.rglob("*"):
        check(not path.is_symlink(), "qa_package_symlink")
        if path.is_file() and "__pycache__" not in path.parts:
            raw = path.read_bytes()
            actual[path.relative_to(package).as_posix()] = {"bytes": len(raw), "sha256": digest(raw)}
    check(actual == inputs["candidate_inventory"], "qa_package_bytes")
    check(json.loads((package / "manifest.json").read_text())["version"] == "0.1.0-beta.20", "qa_package_version")
    return {"package_files_count": len(actual), "package_payload_sha256": digest(actual),
            "candidate_archive_sha256": CANDIDATE}


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


async def path_exists(hass, path):
    return await hass.async_add_executor_job(path.exists)


def checked_step(result, step):
    check(result.get("step_id") == step and not result.get("errors"), "qa_config_flow_step")
    return result


async def create_homecircle(hass, registry, progress=None):
    check(not hass.config_entries.async_entries("homecircle"), "qa_existing_homecircle")
    before = {item.entity_id for item in registry.entities.values() if item.domain == "person"}
    check(not any(state.name in PERSON_NAMES for state in hass.states.async_all("person")), "qa_person_collision")
    setup_mark(progress, "person_create")
    for name in PERSON_NAMES:
        await async_create_person(hass, name, device_trackers=[])
    setup_mark(progress, "person_registry")
    await wait_for(lambda: len([item for item in registry.entities.values()
                               if item.domain == "person" and item.entity_id not in before]) == 2)
    setup_mark(progress, "person_states")
    await wait_for(lambda: sum(state.name in PERSON_NAMES for state in hass.states.async_all("person")) == 2)
    people = []
    for name in PERSON_NAMES:
        matches = [state.entity_id for state in hass.states.async_all("person") if state.name == name]
        check(len(matches) == 1, "qa_created_person")
        people.append(matches[0])
    manager = hass.config_entries.flow
    setup_mark(progress, "flow_user")
    flow = checked_step(await manager.async_init("homecircle", context={"source": SOURCE_USER}), "household")
    setup_mark(progress, "flow_household")
    flow = checked_step(await manager.async_configure(flow["flow_id"],
                        {"people": people, "primary_home": "zone.home", "places": [PLACE]}), "assign_tracker")
    for index, tracker in enumerate(TRACKERS):
        setup_mark(progress, "flow_assign_tracker")
        flow = checked_step(await manager.async_configure(flow["flow_id"], {"tracker": tracker}), "member")
        setup_mark(progress, "flow_member")
        flow = checked_step(await manager.async_configure(flow["flow_id"],
                            {"trackers": [tracker], "additional_residences": [], "kind": "person"}),
                            "assign_tracker" if index == 0 else "confirm")
    setup_mark(progress, "flow_confirm_save")
    flow = await manager.async_configure(flow["flow_id"], {"next_step_id": "confirm_save"})
    check(flow.get("type") == "create_entry" and not flow.get("errors"), "qa_config_flow_save")
    entry = flow["result"]
    setup_mark(progress, "flow_entry_loaded")
    await wait_for(lambda: entry.state == ConfigEntryState.LOADED)
    previous_runtime = entry.runtime_data
    options = hass.config_entries.options
    setup_mark(progress, "options_start")
    flow = checked_step(await options.async_init(entry.entry_id), "init")
    setup_mark(progress, "options_city_form")
    flow = checked_step(await options.async_configure(flow["flow_id"], {"next_step_id": "city_lookup"}), "city_lookup")
    setup_mark(progress, "options_save")
    result = await options.async_configure(flow["flow_id"], {"city_lookup_enabled": False})
    check(result.get("type") == "create_entry" and not result.get("errors"), "qa_options_save")
    setup_mark(progress, "options_entry_loaded")
    await wait_for(lambda: entry.state == ConfigEntryState.LOADED and bool(entry.options)
                   and entry.runtime_data is not previous_runtime)
    check(entry.options.get("city_lookup_enabled") is False, "qa_nonempty_options")
    return entry, people


async def create_portrait(hass,people,registry, progress=None):
    setup_mark(progress, "portrait_api_sources")
    for name,module in [('image_upload',image_component),('person',person_component)]:
        check(await hass.async_add_executor_job(lambda: digest(Path(module.__file__).read_bytes())) == API_SOURCES[name],
              'qa_pinned_image_person_api')
    check(not list(hass.data['image_upload'].async_items()), 'qa_image_collision')
    setup_mark(progress, "portrait_image_create")
    with io.BytesIO(PNG) as source:
        uploaded = FileField('file','synthetic.png',source,'image/png',CIMultiDictProxy(CIMultiDict()))
        record = await hass.data['image_upload'].async_create_item({'file':uploaded})
    person_id = registry.async_get(people[0]).unique_id
    url = '/api/image/serve/'+record['id']+'/512x512'
    setup_mark(progress, "portrait_person_update")
    selected_trackers = entities_in_person(hass, people[0])
    check(selected_trackers == [TRACKERS[0]], 'qa_portrait_person_selection')
    await hass.data['person'][1].async_update_item(person_id,
        {'picture':url, 'device_trackers':list(selected_trackers)})
    setup_mark(progress, "portrait_state")
    await wait_for(lambda: hass.states.get(people[0]) is not None
                   and hass.states.get(people[0]).attributes.get('entity_picture') == url)


async def portrait_snapshot(hass,people):
    collection = hass.data['image_upload']
    records = list(collection.async_items())
    check(len(records) == 1 and re.fullmatch(r'[0-9a-f]{32}',records[0].get('id','')), 'qa_one_real_image')
    record = records[0]
    path = collection.image_dir/record['id']/'original'
    check(await hass.async_add_executor_job(lambda: path.is_file() and not path.is_symlink()
          and digest(path.read_bytes()) == PNG_SHA), 'qa_original_image_bytes')
    pictures = {person:hass.states.get(person).attributes.get('entity_picture')
                for person in people if hass.states.get(person) is not None}
    check(pictures.get(people[0]) == '/api/image/serve/'+record['id']+'/512x512', 'qa_saved_person_picture')
    return {'record':deepcopy(record),'original_sha256':PNG_SHA,'person_pictures':pictures}


def tracker_state(hass, state, marker):
    for index, tracker in enumerate(TRACKERS):
        hass.states.async_set(tracker, state,
            {"friendly_name": f"Synthetic Backup tracker {index + 1}", "source_type": "gps",
             "latitude": 0.0, "longitude": 0.0, "gps_accuracy": 5,
             "qa_backup_marker": marker})


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


def observe_person_sources(hass, people):
    """Read the same two selections without returning names, IDs or values."""
    if type(people) is not list or len(people) != 2 or len(TRACKERS) != 2:
        return None
    result = {}
    for index, (person, tracker) in enumerate(zip(people, TRACKERS, strict=True)):
        person_state = hass.states.get(person)
        tracker_state = hass.states.get(tracker)
        result[str(index)] = {
            'person_present': person_state is not None,
            'tracker_present': tracker_state is not None,
            'person_home': person_state is not None and person_state.state == 'home',
            'tracker_home': tracker_state is not None and tracker_state.state == 'home',
            'source_matches_selected': person_state is not None
                and person_state.attributes.get('source') == tracker,
            'configured_link_matches_selected': entities_in_person(hass, person) == [tracker],
        }
    return public_person_sources(result)


async def person_sources(hass, people, state="home", progress=None):
    setup_mark(progress, "person_sources")
    try:
        await wait_for(lambda: all(hass.states.get(person) is not None
            and hass.states.get(person).attributes.get("source") == tracker
            and hass.states.get(person).state == state
            for person, tracker in zip(people, TRACKERS, strict=True)))
    except TimeoutError:
        if progress is not None:
            try:
                observation = observe_person_sources(hass, people)
            except Exception:
                observation = None
            if observation is not None:
                progress['person_sources'] = observation
        raise


async def stable_snapshot(hass, entry, people, registry):
    active = dict(entry.options or entry.data)
    check(not hass.config_entries.async_entries('homecircle_findmy'), 'qa_no_prototype_entries')
    migration = Path(hass.config.path('.storage','homecircle_findmy_migration_'+entry.entry_id))
    check(not await path_exists(hass,migration), 'qa_no_pending_migration')
    check(active.get("people") == people and not active.get("findmy_accounts")
          and not active.get("life360_account") and active.get("city_lookup_enabled") is False,
          "qa_provider_config")
    check(active.get('places') == [PLACE] and hass.states.get(PLACE) is not None, 'qa_nonempty_place')
    picture = await portrait_snapshot(hass,people)
    for person, tracker in zip(people, TRACKERS, strict=True):
        check(entities_in_person(hass, person) == [tracker]
              and active["members"][person]["trackers"] == [tracker], "qa_person_selection")
    resources = hass.data[LOVELACE_DATA].resources
    await resources.async_get_info()
    unrelated = [item for item in resources.async_items() if item["url"] == UNRELATED]
    check(len(unrelated) == 1, "qa_unrelated_resource")
    dashboard = hass.data[LOVELACE_DATA].dashboards.get("dashboard-homecircle")
    check(dashboard is not None and dashboard.config and dashboard.config.get("id"), "qa_dashboard")
    config = await dashboard.async_load(False)
    records = {}
    for entity_id in [*people, *TRACKERS, SENTINEL]:
        item = registry.async_get(entity_id)
        check(item is not None, "qa_registry_record")
        records[entity_id] = {"id": item.id, "unique_id": item.unique_id}
    return {'picture':picture, "entry_id": entry.entry_id, "entry_data": deepcopy(dict(entry.data)),
            "entry_options": deepcopy(dict(entry.options)), "people": people,
            "registry": records,
            "homecircle_registry": {item.entity_id: {"id": item.id, "unique_id": item.unique_id}
                for item in registry.entities.values() if item.platform == "homecircle"},
            "unrelated_resource": unrelated[0], "dashboard_id": dashboard.config["id"],
            "dashboard_sha256": digest(config)}


async def active_details(hass, entry, people, inputs, progress=None):
    setup_mark(progress, "active_details")
    from custom_components.homecircle import api, frontend

    check(entry.disabled_by is None and entry.state == ConfigEntryState.LOADED, "qa_entry_loaded")
    runtime = entry.runtime_data
    check(runtime.household is not None and not runtime.managed_trackers, "qa_external_provider")
    check([item["id"] for item in api.snapshot(runtime)["members"]] == people, "qa_snapshot_people")
    module = sys.modules.get("custom_components.homecircle")
    check(module is not None and module.__file__, "qa_loaded_origin")
    expected = Path(hass.config.path("custom_components/homecircle/__init__.py"))
    source_sha = await hass.async_add_executor_job(lambda: digest(Path(module.__file__).read_bytes()))
    check(await hass.async_add_executor_job(lambda: Path(module.__file__).resolve() == expected.resolve())
          and source_sha == inputs["candidate_inventory"]["__init__.py"]["sha256"], "qa_loaded_source")
    resources = hass.data[LOVELACE_DATA].resources
    owned = [item for item in resources.async_items() if item["url"].split("?")[0] == OWNED_URL]
    url = await hass.async_add_executor_job(frontend.resource_url)
    check(len(owned) == 1 and owned[0]["url"] == url and owned[0].get("type") == "module", "qa_owned_resource")
    bundle = await hass.async_add_executor_job(
        Path(hass.config.path("custom_components/homecircle/frontend/homecircle-card.js")).read_bytes)
    port = hass.http.server_port
    check(type(port) is int and 1 <= port <= 65535 and hass.http.context is None, "qa_http_fixture")
    setup_mark(progress, "active_http_bundle")
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30), trust_env=False) as session:
        async with session.get(f"http://127.0.0.1:{port}" + url, allow_redirects=False) as response:
            check(response.status == 200, "qa_served_bundle_status")
            body = bytearray()
            async for chunk in response.content.iter_chunked(65536):
                body.extend(chunk)
                check(len(body) <= len(bundle), "qa_served_bundle_size")
            check(bytes(body) == bundle, "qa_served_bundle")
    portrait = await portrait_snapshot(hass,people)
    image_url = '/api/image/serve/'+portrait['record']['id']+'/original'
    setup_mark(progress, "active_http_portrait")
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20),trust_env=False) as session:
        async with session.get(f'http://127.0.0.1:{port}'+image_url,allow_redirects=False) as response:
            check(response.status == 200, 'qa_picture_response_status')
            image_body = bytearray()
            async for chunk in response.content.iter_chunked(65536):
                image_body.extend(chunk)
                check(len(image_body) <= len(PNG), 'qa_picture_response_bound')
            check(bytes(image_body) == PNG, 'qa_actual_picture_response')
    check(api.snapshot(runtime)['members'][0]['picture'] == '/api/image/serve/'+portrait['record']['id']+'/512x512',
          'qa_homecircle_uses_real_portrait')
    return {'resource_url_type_sha256':digest({'url':url,'type':owned[0]['type']}), 'picture_original_sha256':PNG_SHA,'nonempty_place_and_picture':True,"loaded_source_sha256": source_sha, "runtime_config_sha256": digest(runtime.config),
            "served_bundle_sha256": digest(bundle), "static_served_bundle_matches": True,
            "owned_resource_id_sha256": digest(owned[0]["id"]), "owned_resources": 1}


async def assert_quarantine(hass, entry, require_fresh_process=False):
    check(entry.disabled_by == ConfigEntryDisabler.USER and entry.state == ConfigEntryState.NOT_LOADED,
          "qa_disabled_entry_barrier")
    runtime = getattr(entry, "runtime_data", None)
    check(runtime is None or (runtime.household is None and not runtime.managed_trackers
          and not runtime.states), "qa_unloaded_runtime")
    resources = hass.data[LOVELACE_DATA].resources
    await resources.async_get_info()
    check(not any(item["url"].split("?")[0] == OWNED_URL for item in resources.async_items()),
          "qa_quarantine_owned_resource")
    if require_fresh_process:
        check(not any(name == "custom_components.homecircle" or name.startswith("custom_components.homecircle.")
                      for name in sys.modules), "qa_restored_candidate_imported_early")


def stored_entry(directory, entry_id):
    path = directory / ".storage/core.config_entries"
    check(not path.is_symlink(), "qa_stored_entry_path")
    if not path.exists():
        return None
    values = read_json(path)["data"]["entries"]
    matches = [value for value in values if value.get("entry_id") == entry_id]
    check(len(matches) <= 1, "qa_stored_entry_ambiguous")
    return matches[0] if matches else None


async def wait_entry_saved(hass, directory, entry):
    async with asyncio.timeout(120):
        while True:
            saved = await hass.async_add_executor_job(stored_entry, directory, entry.entry_id)
            disabled = entry.disabled_by.value if entry.disabled_by is not None else None
            if saved is not None and saved.get("disabled_by") == disabled and saved.get("data") == dict(entry.data) \
                    and saved.get("options") == dict(entry.options):
                return
            await asyncio.sleep(0.25)


def persisted_store(directory, key):
    """Read the actual disk document, without Store's pending-write cache."""
    root = directory / ".storage"
    check(root.is_dir() and not root.is_symlink(), "qa_persisted_storage_path")
    path = root / key
    check(not path.is_symlink(), "qa_persisted_storage_member")
    if not path.exists():
        return None
    try:
        value = read_json(path)
    except json.JSONDecodeError:
        # Non-atomic Core collection stores can be observed during a normal
        # delayed write. A complete exact document is still required to pass.
        return None
    return value.get("data") if isinstance(value, dict) else None


def persisted_snapshot_matches(directory, expected):
    people = persisted_store(directory, "person")
    image = persisted_store(directory,'image')
    if not isinstance(image,dict) or image.get('items') != [expected['picture']['record']]:
        return False
    registry = persisted_store(directory, "core.entity_registry")
    resources = persisted_store(directory, "lovelace_resources")
    dashboards = persisted_store(directory, "lovelace_dashboards")
    dashboard = persisted_store(directory, "lovelace." + expected["dashboard_record"]["id"])
    if not all(isinstance(value, dict) for value in (people, registry, resources, dashboards, dashboard)):
        return False
    if not all(isinstance(value, list) and all(isinstance(item, dict) for item in value)
               for value in (people.get("items"), registry.get("entities"), resources.get("items"), dashboards.get("items"))):
        return False
    for person_id, item in expected["people"].items():
        matches = [value for value in people["items"] if value.get("id") == person_id]
        if matches != [item]:
            return False
    for entity_id, item in expected["registry"].items():
        matches = [value for value in registry["entities"] if value.get("entity_id") == entity_id]
        if len(matches) != 1 or {key: matches[0].get(key) for key in ("id", "unique_id")} != item:
            return False
    unrelated = [value for value in resources["items"] if value.get("url") == UNRELATED]
    if unrelated != [expected["unrelated_resource"]] or any(
            isinstance(value.get("url"), str) and value["url"].split("?")[0] == OWNED_URL
            for value in resources["items"]):
        return False
    owned = [value for value in dashboards["items"] if value.get("id") == expected["dashboard_record"]["id"]]
    return owned == [expected["dashboard_record"]] and digest(dashboard.get("config")) == expected["dashboard_sha256"]


async def wait_snapshot_saved(hass, directory, stable):
    """Require the supported creates/deletes to have reached disk before backup."""
    person_ids = {stable["registry"][person]["unique_id"] for person in stable["people"]}
    people = {value["id"]: deepcopy(value) for value in hass.data["person"][1].async_items()
              if value["id"] in person_ids}
    check(set(people) == person_ids and len(people) == 2, "qa_persisted_people_expected")
    for person, tracker in zip(stable["people"], TRACKERS, strict=True):
        check(people[stable["registry"][person]["unique_id"]].get("device_trackers") == [tracker],
              "qa_persisted_person_selection_expected")
    dashboard = hass.data[LOVELACE_DATA].dashboards["dashboard-homecircle"]
    dashboard_record = deepcopy(dashboard.config)
    check(isinstance(dashboard_record, dict) and re.fullmatch(r"[a-z0-9_]{1,128}", dashboard_record.get("id", "")),
          "qa_persisted_dashboard_key")
    expected = {'picture':stable['picture'], "people": people,
                "registry": {**stable["registry"], **stable["homecircle_registry"]},
                "unrelated_resource": stable["unrelated_resource"],
                "dashboard_record": dashboard_record, "dashboard_sha256": stable["dashboard_sha256"]}
    async with asyncio.timeout(120):
        while not await hass.async_add_executor_job(persisted_snapshot_matches, directory, expected):
            await asyncio.sleep(0.25)


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


async def record_window(hass, people, marker):
    start = dt_util.utcnow().timestamp()
    for index, state in enumerate(("not_home", "home")):
        tracker_state(hass, state, marker + str(index))
        hass.states.async_set(SENTINEL, marker + str(index), {"friendly_name": "Synthetic backup sentinel"})
        await person_sources(hass, people, state)
        # Each barrier forces the genuine event queue through a committed DB write.
        await get_instance(hass).async_block_till_done()
        await asyncio.sleep(0.02)
    end = dt_util.utcnow().timestamp()
    rows = await rows_for(hass, people, start, end)
    check(5 <= len(rows) <= 128 and {row["entity_id"] for row in rows} == {*people, *TRACKERS, SENTINEL},
          "qa_history_not_recorded")
    check([row["state"] for row in rows if row["entity_id"] == SENTINEL] == [marker + "0", marker + "1"],
          "qa_history_marker")
    return {"start": start, "end": end, "rows": rows}


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


async def mutate_options(hass, entry, people):
    options = hass.config_entries.options
    flow = checked_step(await options.async_init(entry.entry_id), "init")
    flow = checked_step(await options.async_configure(flow["flow_id"],
                        {"next_step_id": "tracker_member_choice"}), "tracker_member_choice")
    flow = checked_step(await options.async_configure(flow["flow_id"],
                        {"member": people[0], "setting": "details"}), "member")
    flow = checked_step(await options.async_configure(flow["flow_id"],
                        {"trackers": [TRACKERS[0]], "additional_residences": [], "kind": "person", "show_on_map": False}), "confirm")
    flow = await options.async_configure(flow["flow_id"], {"next_step_id": "confirm_save"})
    check(flow.get("type") == "create_entry" and not flow.get("errors"), "qa_mutated_options_save")
    check(entry.options["members"][people[0]].get("show_on_map") is False, "qa_mutated_option")


class Rehearsal:
    def __init__(self, hass):
        self.hass = hass
        self.directory = Path(hass.config.config_dir)
        self.control = self.directory / CONTROL

    async def run(self, phase, inputs):
        hass, directory = self.hass, self.directory
        name = phase["phase"]
        stage = "platform"
        setup_progress = {}
        receipt = {"schema": 1, "token": phase["token"], "generation": phase["generation"],
                   "phase": name, "branch_commit": inputs["branch_commit"], "outcome": "failed",
                   "process": process(), "core_version": CORE_VERSION,
                   "owner_accounts_used": False, "production_configuration_used": False,
                   "provider_request_attempt_counts_measured": False, "recovery_proof_attempt_counts_measured": False, "candidate_hacs_tested": False}
        try:
            async with asyncio.timeout(600):
                check(CORE_VERSION == "2026.10.2" and os.uname().machine == "x86_64", "qa_platform")
                receipt.update(await hass.async_add_executor_job(package_at, directory, inputs))
                users = await hass.auth.async_get_users()
                check(not any(user.is_owner or not user.system_generated for user in users), 'qa_no_owner_accounts')
                stage = 'system_entries_ready'
                await ensure_entry_scope(hass, receipt)
                stage = "recorder"
                await recorder_ready(hass)
                registry = er.async_get(hass)
                baseline_path = self.control / "baseline.json"
                quarantine_path = self.control / "quarantine.json"
                baseline = await hass.async_add_executor_job(read_json, baseline_path) \
                    if await path_exists(hass, baseline_path) else None
                stage = "persistent_setup"
                if name == "initialize":
                    check(baseline is None and not hass.config_entries.async_entries("homecircle"), "qa_initialize_fresh")
                    for uid, entity_id in zip(TRACKER_UIDS, TRACKERS, strict=True):
                        check(registry.async_get_entity_id("device_tracker", DOMAIN, uid) is None, "qa_tracker_collision")
                        item = registry.async_get_or_create("device_tracker", DOMAIN, uid,
                            suggested_object_id=entity_id.split(".", 1)[1])
                        check(item.entity_id == entity_id, "qa_tracker_identity")
                    sensor = registry.async_get_or_create("sensor", DOMAIN, "homecircle-safe-restore-qa-sentinel",
                        suggested_object_id=SENTINEL.split(".", 1)[1])
                    check(sensor.entity_id == SENTINEL, "qa_sentinel_identity")
                    tracker_state(hass, "home", "initial")
                    entry, people = await create_homecircle(hass, registry, progress=setup_progress)
                    await create_portrait(hass,people,registry,progress=setup_progress)
                    resources = hass.data[LOVELACE_DATA].resources
                    setup_mark(setup_progress, "resource_initialization")
                    await resources.async_get_info()
                    check(not any(item["url"] == UNRELATED for item in resources.async_items()), "qa_unrelated_collision")
                    setup_mark(setup_progress, "unrelated_resource_create")
                    await resources.async_create_item({"res_type": "module", "url": UNRELATED})
                    await person_sources(hass, people, progress=setup_progress)
                    setup_mark(setup_progress, "snapshot")
                    active = await stable_snapshot(hass, entry, people, registry)
                    details = await active_details(hass, entry, people, inputs, progress=setup_progress)
                    stage = "guard_two"
                    from custom_components.homecircle.findmy_recovery_guard import get_recovery_guard

                    guard = get_recovery_guard(hass)
                    check((await guard.status(GUARD_IDENTITY))['unresolved'] == 0, 'qa_guard_initial_empty')
                    for _ in range(2):
                        async with guard.attempt(GUARD_IDENTITY) as attempt:
                            await attempt.before_dispatch()
                            await attempt.refused()
                    status = await guard.status(GUARD_IDENTITY)
                    check(status["unresolved"] == status["rejected"] == 2 and not status["blocked"]
                          and status['pending'] == status['uncertain'] == 0, "qa_initial_guard")
                    guard_sha = await hass.async_add_executor_job(guard_files, directory)
                    stage = "prebackup_recording"
                    recorded = await record_window(hass, people, "before_backup_")
                    baseline = {"schema": 1, "token": phase["token"], "active": active,
                                "active_details": details, "history": recorded, "backup_guard_sha256": guard_sha}
                    await hass.async_add_executor_job(write_json, baseline_path, baseline)
                    await wait_entry_saved(hass, directory, entry)
                    receipt.update(details)
                    receipt["guard"] = {"sha256": guard_sha, "api_status_checked": True,
                                        "retained_bytes_checked": True, "blocked": False,
                                        "unresolved": 2, "rejected": 2, "pending": 0, "uncertain": 0}
                else:
                    check(baseline is not None and baseline["schema"] == 1, "qa_baseline_missing")
                    entries = hass.config_entries.async_entries("homecircle")
                    check(len(entries) == 1 and entries[0].entry_id == baseline["active"]["entry_id"], "qa_entry_identity")
                    entry, people = entries[0], baseline["active"]["people"]
                if name == 'initial_restart':
                    tracker_state(hass, 'home', 'initial_restart')
                    await wait_for(lambda: entry.state == ConfigEntryState.LOADED)
                    await person_sources(hass, people)
                    details = await active_details(hass, entry, people, inputs)
                    check(details == baseline['active_details'], 'qa_initial_restart_details')
                    receipt.update(details)
                    from custom_components.homecircle.findmy_recovery_guard import get_recovery_guard
                    status = await get_recovery_guard(hass).status(GUARD_IDENTITY)
                    check(status['unresolved'] == status['rejected'] == 2 and not status['blocked']
                          and status['pending'] == status['uncertain'] == 0, 'qa_initial_restart_guard')
                    receipt['guard'] = {'sha256': await hass.async_add_executor_job(guard_files,directory),
                        'api_status_checked':True,'retained_bytes_checked':True,'blocked':False,'unresolved':2,'rejected':2,'pending':0,'uncertain':0}
                if name == "quarantine":
                    stage = "quarantine_disable"
                    check(entry.disabled_by is None and entry.state == ConfigEntryState.LOADED, "qa_quarantine_active_required")
                    await hass.config_entries.async_set_disabled_by(entry.entry_id, ConfigEntryDisabler.USER)
                    await wait_for(lambda: entry.state == ConfigEntryState.NOT_LOADED)
                    await assert_quarantine(hass, entry)
                    await wait_entry_saved(hass, directory, entry)
                    current = await stable_snapshot(hass, entry, people, registry)
                    check(current == baseline["active"], "qa_quarantine_identity_changed")
                    stage = "quarantine_persisted_storage"
                    await wait_snapshot_saved(hass, directory, current)
                    await assert_quarantine(hass, entry)
                    receipt["persisted_storage_checked"] = True
                    quarantine = {"stable": current, "disabled_by": "user", "loaded": False,
                                  "owned_resources": 0, "runtime_unloaded": True}
                    await hass.async_add_executor_job(write_json, quarantine_path, quarantine)
                    receipt["quarantine_snapshot_sha256"] = digest(quarantine)
                    guard_sha = await hass.async_add_executor_job(guard_files, directory)
                    check(guard_sha == baseline["backup_guard_sha256"], "qa_quarantine_guard_changed")
                    receipt["guard"] = {"sha256": guard_sha, "api_status_checked": False,
                                        "retained_bytes_checked": True, "blocked": False,
                                        "unresolved": 2, "rejected": 2, "pending": 0, "uncertain": 0}
                if name == "mutate":
                    stage = "mutate_disabled_options"
                    await assert_quarantine(hass, entry)
                    await mutate_options(hass, entry, people)
                    await assert_quarantine(hass, entry)
                    await wait_entry_saved(hass, directory, entry)
                    check(await stable_snapshot(hass, entry, people, registry) != baseline["active"], "qa_option_mutation_missing")
                    stage = "postbackup_recording"
                    recorded = await record_window(hass, people, "after_backup_")
                    external = {"schema": 1, "token": phase["token"], "generation": "before_restore",
                                "branch_commit": inputs["branch_commit"],
                                "postbackup_window": {"start": recorded["start"], "end": recorded["end"],
                                                      "rows": len(recorded["rows"]), "sha256": digest(recorded["rows"])}}
                    await hass.async_add_executor_job(write_json, self.control / "external-proof.json", external)
                    stage = "guard_newer_than_backup"
                    from custom_components.homecircle.findmy_recovery_guard import get_recovery_guard

                    guard = get_recovery_guard(hass)
                    check((await guard.status(GUARD_IDENTITY))["unresolved"] == 2, "qa_guard_seed_fresh")
                    for _ in range(1):
                        async with guard.attempt(GUARD_IDENTITY) as attempt:
                            await attempt.before_dispatch()
                            await attempt.refused()
                    status = await guard.status(GUARD_IDENTITY)
                    check(status["blocked"] is True and status["unresolved"] == status["rejected"] == 3
                          and status["pending"] == status["uncertain"] == 0, "qa_guard_seed_status")
                    guard_sha = await hass.async_add_executor_job(guard_files, directory)
                    check(guard_sha != baseline["backup_guard_sha256"], "qa_guard_not_newer")
                    receipt["guard"] = {"sha256": guard_sha, "api_status_checked": True,
                                        "retained_bytes_checked": True, "blocked": True,
                                        "unresolved": 3, "rejected": 3, "pending": 0, "uncertain": 0}
                    receipt["postbackup_history_sha256"] = digest(recorded["rows"])
                if name in {"repaired_disabled", "reenabled", "restart"}:
                    stage = "restored_external_proof"
                    check(digest(baseline["active"]) == inputs["expected_snapshot_sha256"]
                          and digest(baseline["history"]["rows"]) == inputs["expected_prebackup_sha256"]
                          and baseline["backup_guard_sha256"] == inputs["backup_guard_sha256"], "qa_restored_baseline_proof")
                    quarantine = await hass.async_add_executor_job(read_json, quarantine_path)
                    check(digest(quarantine) == inputs["expected_quarantine_sha256"], "qa_restored_quarantine_proof")
                    guard_sha = await hass.async_add_executor_job(guard_files, directory)
                    check(guard_sha == inputs["latest_guard_sha256"]
                          and guard_sha != inputs["backup_guard_sha256"], "qa_latest_guard_required")
                    if name in {"repaired_disabled", "reenabled"}:
                        await assert_quarantine(hass, entry, require_fresh_process=name == 'repaired_disabled')
                        current = await stable_snapshot(hass, entry, people, registry)
                        restored = {"stable": current, "disabled_by": "user", "loaded": False,
                                    "owned_resources": 0, "runtime_unloaded": True}
                        check(restored == quarantine, "qa_restored_quarantine_changed")
                        receipt["quarantine_snapshot_sha256"] = digest(restored)
                    if name == "repaired_disabled":
                        from custom_components.homecircle.findmy_recovery_guard import get_recovery_guard
                        status = await get_recovery_guard(hass).status(GUARD_IDENTITY)
                        check(status['blocked'] is True and status['unresolved'] == status['rejected'] == 3
                              and status['pending'] == status['uncertain'] == 0, 'qa_repaired_guard_before_enable')
                        check(await hass.async_add_executor_job(guard_files, directory) == guard_sha, 'qa_repaired_guard_unchanged')
                        before_enable = await hass.async_add_executor_job(observe)
                        before_enable['skip_pip'] = hass.config.skip_pip
                        receipt['normal_dependencies_before_enable'] = before_enable
                        receipt["guard"] = {"sha256": guard_sha, "api_status_checked": True,
                                            "retained_bytes_checked": True, "blocked": True,
                                            "unresolved": 3, "rejected": 3, "pending": 0, "uncertain": 0}
                    else:
                        stage = "safe_reactivation"
                        tracker_state(hass, "home", "restored")
                        if name == "reenabled":
                            # This is the ONLY postrestore entry-enable operation, after both
                            # external newest-guard bytes and the disabled barrier were proved.
                            from custom_components.homecircle.findmy_recovery_guard import get_recovery_guard
                            status = await get_recovery_guard(hass).status(GUARD_IDENTITY)
                            check(status['blocked'] is True and status['unresolved'] == status['rejected'] == 3
                                  and status['pending'] == status['uncertain'] == 0, 'qa_enable_requires_latest_guard')
                            await hass.config_entries.async_set_disabled_by(entry.entry_id, None)
                        await wait_for(lambda: entry.state == ConfigEntryState.LOADED)
                        await person_sources(hass, people)
                        receipt.update(await active_details(hass, entry, people, inputs))
                        check(receipt["runtime_config_sha256"] == baseline["active_details"]["runtime_config_sha256"],
                              "qa_runtime_config_changed")
                        from custom_components.homecircle.findmy_recovery_guard import get_recovery_guard

                        status = await get_recovery_guard(hass).status(GUARD_IDENTITY)
                        check(status["blocked"] is True and status["unresolved"] == status["rejected"] == 3
                              and status["pending"] == status["uncertain"] == 0, "qa_restored_guard_status")
                        check(await hass.async_add_executor_job(guard_files, directory) == guard_sha, "qa_guard_status_mutated")
                        receipt["guard"] = {"sha256": guard_sha, "api_status_checked": True,
                                            "retained_bytes_checked": True, "blocked": True,
                                            "unresolved": 3, "rejected": 3, "pending": 0, "uncertain": 0}
                        stage = "postrestore_recording"
                        if name == "reenabled":
                            postrestore = await record_window(hass, people, "after_restore_")
                            postrestore["owned_resource_id_sha256"] = receipt["owned_resource_id_sha256"]
                            await hass.async_add_executor_job(write_json, self.control / "postrestore-history.json", postrestore)
                            await wait_entry_saved(hass, directory, entry)
                        else:
                            postrestore = await hass.async_add_executor_job(read_json, self.control / "postrestore-history.json")
                            check(receipt["owned_resource_id_sha256"] == postrestore["owned_resource_id_sha256"],
                                  "qa_recreated_resource_changed_after_restart")
                stage = "final_snapshot"
                stable = await stable_snapshot(hass, entry, people, registry)
                check((stable != baseline["active"]) if name == "mutate" else stable == baseline["active"],
                      "qa_stable_identity_changed")
                receipt['nonempty_place_and_picture'] = True
                receipt["snapshot_sha256"] = digest(stable)
                receipt["active_snapshot_sha256"] = digest(stable)
                receipt["entry_disabled"] = entry.disabled_by == ConfigEntryDisabler.USER
                receipt["entry_loaded"] = entry.state == ConfigEntryState.LOADED
                receipt["nonempty_options"] = bool(entry.options)
                stage = "history_continuity"
                receipt["recorder"] = await recorder_receipt(hass, baseline, inputs,
                    postrestore if name in {"reenabled", "restart"} else None)
                if name == "mutate":
                    receipt["recorder"]["postbackup_marker_rows"] = len(recorded["rows"])
                    receipt["recorder"]["postbackup_marker_absent"] = False
                if name in {'initialize','initial_restart','reenabled','restart'}:
                    dependencies = await hass.async_add_executor_job(observe)
                    dependencies['skip_pip'] = hass.config.skip_pip
                    receipt['normal_dependencies'] = dependencies
                receipt["outcome"] = "passed"
        except Exception as error:
            receipt.update({"outcome": "failed", "stage": stage, "failure_type": type(error).__name__})
            if stage == "persistent_setup" and setup_progress:
                receipt["setup_step"] = setup_progress["step"]
            if stage == 'persistent_setup' and setup_progress.get('step') == 'person_sources' \
                    and name == 'initialize':
                if observation := public_person_sources(setup_progress.get('person_sources')):
                    receipt['person_sources'] = observation
            if isinstance(error, Refused):
                receipt["failure_code"] = str(error)
            # No exception messages, locals, entity IDs, timestamps or account values.
            _LOGGER.error("Disposable backup rehearsal failed at %s (%s)", stage, type(error).__name__)
        await hass.async_add_executor_job(write_json, directory / RESULTS / (name + ".json"), receipt)

    async def poll(self):
        seen = set()
        observed_boot = False
        while self.hass.is_running:
            try:
                inputs = await self.hass.async_add_executor_job(inputs_at, self.directory)
                path = self.control / "phase.json"
                if await path_exists(self.hass, path):
                    phase = await self.hass.async_add_executor_job(read_json, path)
                    name, token, generation = phase.get("phase"), phase.get("token", ""), phase.get("generation")
                    check(phase.get("schema") == 1 and name in PHASES
                          and re.fullmatch(r"[0-9a-f]{32,64}", token)
                          and generation == inputs["generation"]
                          and phase.get("branch_commit") == inputs["branch_commit"]
                          and generation == ("before_restore" if name in PHASES[:4] else "after_restore"), "qa_phase")
                    if not observed_boot:
                        observed_boot = True
                        entries = self.hass.config_entries.async_entries("homecircle")
                        if generation == "before_restore" and len(entries) == 1 \
                                and entries[0].disabled_by == ConfigEntryDisabler.USER:
                            # Restore auto-starts Core. This observation is intentionally
                            # inert: no candidate/status/provider import or enable action.
                            await assert_quarantine(self.hass, entries[0], require_fresh_process=True)
                            baseline = await self.hass.async_add_executor_job(read_json, self.control/'baseline.json')
                            quarantine = await self.hass.async_add_executor_job(read_json, self.control/'quarantine.json')
                            current = await stable_snapshot(self.hass, entries[0], baseline['active']['people'], er.async_get(self.hass))
                            check(current == baseline['active'] and quarantine['stable'] == current, 'qa_automatic_disabled_snapshot')
                            guard_sha = await self.hass.async_add_executor_job(guard_files,self.directory)
                            check(guard_sha == baseline['backup_guard_sha256'], 'qa_automatic_old_guard_bytes')
                            await self.hass.async_add_executor_job(write_json,
                                self.control / "restore-barrier.json",
                                {"schema": 1, "token": token, "generation": generation,
                                 "branch_commit": inputs["branch_commit"], "process": process(),
                                 "entry_disabled": True, "entry_loaded": False,
                                 "candidate_imported": False, 'snapshot_sha256':digest(current),
                                 'quarantine_snapshot_sha256':digest(quarantine),'guard_sha256':guard_sha})
                    nonce_path = self.control / "job-nonce.json"
                    if await path_exists(self.hass, nonce_path):
                        previous = await self.hass.async_add_executor_job(read_json, nonce_path)
                        check(previous == {"token": token, "generation": generation}, "qa_job_nonce")
                    else:
                        check(name in {"initialize", "repaired_disabled"}, "qa_first_phase")
                        await self.hass.async_add_executor_job(write_json, nonce_path,
                            {"token": token, "generation": generation})
                    identity = (generation, name)
                    if identity not in seen:
                        seen.add(identity)
                        result_path = self.directory / RESULTS / (name + ".json")
                        if await path_exists(self.hass, result_path):
                            old = await self.hass.async_add_executor_job(read_json, result_path)
                            check(old.get("token") == token and old.get("phase") == name
                                  and old.get("generation") == generation and old.get("outcome") == "passed",
                                  "qa_phase_receipt_collision")
                        else:
                            await self.run(phase, inputs)
            except Exception as error:
                _LOGGER.error("Disposable backup controller input refused (%s)", type(error).__name__)
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


