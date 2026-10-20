"""Temporary bounded normal-managed minimum-Core witness; never distribute with product."""
from __future__ import annotations
import sys
if sys.platform != "linux":
    raise RuntimeError("qa_linux_required")
import asyncio
from copy import deepcopy
import hashlib
import json
import logging
import os
from pathlib import Path, PurePosixPath
import re
import aiohttp
import probatio as vol
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.person import async_create_person, entities_in_person
from homeassistant.config_entries import ConfigEntryState, SOURCE_USER
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, __version__ as CORE_VERSION
from homeassistant.helpers import entity_registry as er
from .dependency_probe import observe

DOMAIN = "homecircle_minimum_haos_qa"
CONTROL = "homecircle-minimum-haos-qa-control"
RESULTS = "homecircle-minimum-haos-qa-results"
CANDIDATE = "c4530d94be3b2996f8d6c8948db88a51868566047d68558eefde7967f270a861"
PHASES = ("initialize", "restart")
TRACKERS = ("device_tracker.homecircle_minimum_haos_qa_a", "device_tracker.homecircle_minimum_haos_qa_b")
TRACKER_UIDS = ("homecircle-minimum-haos-synthetic-a", "homecircle-minimum-haos-synthetic-b")
PERSON_NAMES = ("Synthetic Minimum Core Member A", "Synthetic Minimum Core Member B")
SENTINEL = "sensor.homecircle_minimum_haos_qa_sentinel"
UNRELATED = "/local/homecircle_minimum_haos_qa_unrelated.js"
OWNED_URL = "/homecircle_static/homecircle-card.js"
_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({vol.Required("disposable"): vol.Boolean()})}, extra=vol.ALLOW_EXTRA)

class Refused(RuntimeError):
    """Only a fixed label, never provider or file contents."""


def check(condition, label):
    if not condition:
        raise Refused(label)


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


async def wait_for(predicate, seconds=120):
    async with asyncio.timeout(seconds):
        while not predicate():
            await asyncio.sleep(0.2)


async def path_exists(hass, path):
    return await hass.async_add_executor_job(path.exists)


def checked_step(result, step):
    check(result.get("step_id") == step and not result.get("errors"), "qa_config_flow_step")
    return result


async def create_homecircle(hass, registry):
    check(not hass.config_entries.async_entries("homecircle"), "qa_existing_homecircle")
    before = {item.entity_id for item in registry.entities.values() if item.domain == "person"}
    check(not any(state.name in PERSON_NAMES for state in hass.states.async_all("person")), "qa_person_collision")
    for name in PERSON_NAMES:
        await async_create_person(hass, name, device_trackers=[])
    await wait_for(lambda: len([item for item in registry.entities.values()
                               if item.domain == "person" and item.entity_id not in before]) == 2)
    await wait_for(lambda: sum(state.name in PERSON_NAMES for state in hass.states.async_all("person")) == 2)
    people = []
    for name in PERSON_NAMES:
        matches = [state.entity_id for state in hass.states.async_all("person") if state.name == name]
        check(len(matches) == 1, "qa_created_person")
        people.append(matches[0])
    manager = hass.config_entries.flow
    flow = checked_step(await manager.async_init("homecircle", context={"source": SOURCE_USER}), "household")
    flow = checked_step(await manager.async_configure(flow["flow_id"],
                        {"people": people, "primary_home": "zone.home", "places": []}), "assign_tracker")
    for index, tracker in enumerate(TRACKERS):
        flow = checked_step(await manager.async_configure(flow["flow_id"], {"tracker": tracker}), "member")
        flow = checked_step(await manager.async_configure(flow["flow_id"],
                            {"trackers": [tracker], "additional_residences": [], "kind": "person"}),
                            "assign_tracker" if index == 0 else "confirm")
    flow = await manager.async_configure(flow["flow_id"], {"next_step_id": "confirm_save"})
    check(flow.get("type") == "create_entry" and not flow.get("errors"), "qa_config_flow_save")
    entry = flow["result"]
    await wait_for(lambda: entry.state == ConfigEntryState.LOADED)
    previous_runtime = entry.runtime_data
    options = hass.config_entries.options
    flow = checked_step(await options.async_init(entry.entry_id), "init")
    flow = checked_step(await options.async_configure(flow["flow_id"], {"next_step_id": "city_lookup"}), "city_lookup")
    result = await options.async_configure(flow["flow_id"], {"city_lookup_enabled": False})
    check(result.get("type") == "create_entry" and not result.get("errors"), "qa_options_save")
    await wait_for(lambda: entry.state == ConfigEntryState.LOADED and bool(entry.options)
                   and entry.runtime_data is not previous_runtime)
    check(entry.options.get("city_lookup_enabled") is False, "qa_nonempty_options")
    return entry, people


def tracker_state(hass, state, marker):
    for index, tracker in enumerate(TRACKERS):
        hass.states.async_set(tracker, state,
            {"friendly_name": f"Synthetic Backup tracker {index + 1}", "source_type": "gps",
             "latitude": 0.0, "longitude": 0.0, "gps_accuracy": 5,
             "qa_backup_marker": marker})


async def person_sources(hass, people, state="home"):
    await wait_for(lambda: all(hass.states.get(person) is not None
        and hass.states.get(person).attributes.get("source") == tracker
        and hass.states.get(person).state == state
        for person, tracker in zip(people, TRACKERS, strict=True)))


async def stable_snapshot(hass, entry, people, registry):
    active = dict(entry.options or entry.data)
    check(not hass.config_entries.async_entries("homecircle_findmy"), "qa_no_prototype_entries")
    migration = Path(hass.config.path(".storage", "homecircle_findmy_migration_" + entry.entry_id))
    check(not await path_exists(hass, migration), "qa_no_pending_migration")
    check(active.get("people") == people and not active.get("findmy_accounts")
          and not active.get("life360_account") and active.get("city_lookup_enabled") is False,
          "qa_provider_config")
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
    return {"entry_id": entry.entry_id, "entry_data": deepcopy(dict(entry.data)),
            "entry_options": deepcopy(dict(entry.options)), "people": people,
            "registry": records,
            "homecircle_registry": {item.entity_id: {"id": item.id, "unique_id": item.unique_id}
                for item in registry.entities.values() if item.platform == "homecircle"},
            "unrelated_resource": unrelated[0], "dashboard_id": dashboard.config["id"],
            "dashboard_sha256": digest(config)}


async def active_details(hass, entry, people, inputs):
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
    check(len(owned) == 1 and owned[0]["url"] == url, "qa_owned_resource")
    bundle = await hass.async_add_executor_job(
        Path(hass.config.path("custom_components/homecircle/frontend/homecircle-card.js")).read_bytes)
    port = hass.http.server_port
    check(type(port) is int and 1 <= port <= 65535 and hass.http.context is None, "qa_http_fixture")
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30), trust_env=False) as session:
        async with session.get(f"http://127.0.0.1:{port}" + url, allow_redirects=False) as response:
            check(response.status == 200, "qa_served_bundle_status")
            body = bytearray()
            async for chunk in response.content.iter_chunked(65536):
                body.extend(chunk)
                check(len(body) <= len(bundle), "qa_served_bundle_size")
            check(bytes(body) == bundle, "qa_served_bundle")
    return {"loaded_source_sha256": source_sha, "runtime_config_sha256": digest(runtime.config),
            "served_bundle_sha256": digest(bundle), "static_served_bundle_matches": True,
            "owned_resource_id_sha256": digest(owned[0]["id"]), "owned_resources": 1}


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
    if unrelated != [expected["unrelated_resource"]]:
        return False
    resources_owned = [value for value in resources["items"] if isinstance(value.get("url"), str) and value["url"].split("?")[0] == OWNED_URL]
    if resources_owned != expected["owned_resources"]:
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
    expected = {"people": people,
                "registry": {**stable["registry"], **stable["homecircle_registry"]},
                "unrelated_resource": stable["unrelated_resource"],
                "dashboard_record": dashboard_record, "dashboard_sha256": stable["dashboard_sha256"],
                "owned_resources": [deepcopy(value) for value in hass.data[LOVELACE_DATA].resources.async_items()
                                    if value["url"].split("?")[0] == OWNED_URL]}
    async with asyncio.timeout(120):
        while not await hass.async_add_executor_job(persisted_snapshot_matches, directory, expected):
            await asyncio.sleep(0.25)


def inputs_at(directory):
    value = read_json(directory / CONTROL / 'inputs.json')
    check(value.get('schema') == 1 and value.get('core_version') == '2026.9.4'
          and value.get('candidate_sha256') == CANDIDATE
          and re.fullmatch(r'[0-9a-f]{40}', value.get('branch_commit', '')), 'qa_input_identity')
    inventory = value.get('candidate_inventory')
    check(isinstance(inventory, dict) and len(inventory) == 113, 'qa_input_inventory')
    for name, item in inventory.items():
        path = PurePosixPath(name)
        check(name == path.as_posix() and not path.is_absolute() and '..' not in path.parts and '\\' not in name
              and type(item) is dict and set(item) == {'bytes', 'sha256'} and type(item['bytes']) is int
              and 0 <= item['bytes'] < 32 * 1024**2 and re.fullmatch(r'[0-9a-f]{64}', item['sha256']), 'qa_inventory_member')
    return value


class Witness:
    def __init__(self, hass):
        self.hass = hass
        self.directory = Path(hass.config.config_dir)
        self.control = self.directory / CONTROL

    async def run(self, phase, inputs):
        hass, directory = self.hass, self.directory
        name = phase['phase']
        stage = 'platform'
        receipt = {'schema': 1, 'token': phase['token'], 'phase': name, 'branch_commit': inputs['branch_commit'],
                   'outcome': 'failed', 'process': process(), 'core_version': CORE_VERSION,
                   'provider_accounts_configured': False, 'owner_accounts_used': False}
        try:
            async with asyncio.timeout(600 if name == 'initialize' else 420):
                check(CORE_VERSION == '2026.9.4' and os.uname().machine == 'x86_64'
                      and hass.config.skip_pip is False, 'qa_platform_requirements')
                receipt.update(await hass.async_add_executor_job(package_at, directory, inputs))
                stage = 'owner_scope'
                users = await hass.auth.async_get_users()
                check(not any(user.is_owner or not user.system_generated for user in users), 'qa_no_owner_accounts')
                registry = er.async_get(hass)
                baseline_path = self.control / 'baseline.json'
                baseline = await hass.async_add_executor_job(read_json, baseline_path) \
                    if await path_exists(hass, baseline_path) else None
                stage = 'explicit_selection_setup'
                if name == 'initialize':
                    check(baseline is None and not hass.config_entries.async_entries('homecircle'), 'qa_initialize_fresh')
                    for uid, entity_id in zip(TRACKER_UIDS, TRACKERS, strict=True):
                        check(registry.async_get_entity_id('device_tracker', DOMAIN, uid) is None, 'qa_tracker_collision')
                        item = registry.async_get_or_create('device_tracker', DOMAIN, uid,
                            suggested_object_id=entity_id.split('.', 1)[1])
                        check(item.entity_id == entity_id, 'qa_tracker_identity')
                    item = registry.async_get_or_create('sensor', DOMAIN, 'homecircle-minimum-haos-sentinel',
                        suggested_object_id=SENTINEL.split('.', 1)[1])
                    check(item.entity_id == SENTINEL, 'qa_sentinel_identity')
                    tracker_state(hass, 'home', 'minimum_initialize')
                    entry, people = await create_homecircle(hass, registry)
                    resources = hass.data[LOVELACE_DATA].resources
                    await resources.async_get_info()
                    check(not any(item['url'] == UNRELATED for item in resources.async_items()), 'qa_unrelated_collision')
                    await resources.async_create_item({'res_type': 'module', 'url': UNRELATED})
                else:
                    check(baseline is not None and baseline.get('schema') == 1, 'qa_baseline_missing')
                    entries = hass.config_entries.async_entries('homecircle')
                    check(len(entries) == 1, 'qa_restart_entry_count')
                    entry, people = entries[0], baseline['active']['people']
                    tracker_state(hass, 'home', 'minimum_restart')
                    stage = 'restart_entry_loaded_wait'
                    await wait_for(lambda: entry.state == ConfigEntryState.LOADED)
                stage = 'explicit_person_source_wait'
                await person_sources(hass, people)
                stage = 'persistent_identity_snapshot'
                active = await stable_snapshot(hass, entry, people, registry)
                details = await active_details(hass, entry, people, inputs)
                if name == 'restart':
                    check(active == baseline['active'] and details == baseline['active_details'], 'qa_restart_identity_changed')
                stage = 'actual_disk_persistence'
                await wait_entry_saved(hass, directory, entry)
                await wait_snapshot_saved(hass, directory, active)
                stage = 'ordinary_managed_requirements'
                dependencies = await hass.async_add_executor_job(observe)
                dependencies['skip_pip'] = hass.config.skip_pip
                check(dependencies['core'] == CORE_VERSION and dependencies['python'] == '3.14.6'
                      and dependencies['constraints_match'] is True and dependencies['docker_environment'] is True
                      and dependencies['ordinary_pip_target_unset'] is True and dependencies['config_deps_empty'] is True
                      and dependencies['closure_graph_checked'] is True, 'qa_normal_dependency_environment')
                check(all(item['available'] and item['metadata_system_origin'] and item['constraints_satisfied'] and item['python_satisfied']
                          for item in dependencies['closure'].values()), 'qa_normal_dependency_closure')
                check(all(item['satisfies_requirement'] and item['module_system_origin']
                          for item in dependencies['direct'].values()), 'qa_normal_direct_requirements')
                if name == 'initialize':
                    baseline = {'schema': 1, 'active': active, 'active_details': details}
                    await hass.async_add_executor_job(write_json, baseline_path, baseline)
                receipt.update(details, snapshot_sha256=digest(active), entry_loaded=True, entry_disabled=False,
                               nonempty_options=True, persistent_people=2, explicit_trackers=2,
                               persisted_storage_checked=True, normal_dependencies=dependencies, outcome='passed')
        except Exception as error:
            receipt.update(outcome='failed', stage=stage, failure_type=type(error).__name__)
            if isinstance(error, Refused):
                receipt['failure_code'] = str(error)
            try:
                async with asyncio.timeout(15):
                    receipt['normal_dependencies'] = await hass.async_add_executor_job(observe)
                    receipt['normal_dependencies']['skip_pip'] = hass.config.skip_pip
            except Exception:
                receipt['dependency_observation_unavailable'] = True
            _LOGGER.error('Disposable minimum Core witness refused at %s (%s)', stage, type(error).__name__)
        await hass.async_add_executor_job(write_json, directory / RESULTS / (name + '.json'), receipt)

    async def poll(self):
        seen = set()
        while self.hass.is_running:
            try:
                inputs = await self.hass.async_add_executor_job(inputs_at, self.directory)
                phase = await self.hass.async_add_executor_job(read_json, self.control / 'phase.json')
                name, token = phase.get('phase'), phase.get('token', '')
                check(phase.get('schema') == 1 and name in PHASES and re.fullmatch(r'[0-9a-f]{32}', token)
                      and phase.get('branch_commit') == inputs['branch_commit'], 'qa_phase_identity')
                if name not in seen:
                    seen.add(name)
                    result = self.directory / RESULTS / (name + '.json')
                    if await path_exists(self.hass, result):
                        old = await self.hass.async_add_executor_job(read_json, result)
                        check(old.get('token') == token and old.get('phase') == name and old.get('outcome') == 'passed',
                              'qa_phase_receipt_collision')
                    else:
                        await self.run(phase, inputs)
            except Exception as error:
                _LOGGER.error('Disposable minimum Core control refused (%s)', type(error).__name__)
                return
            await asyncio.sleep(0.5)


async def async_setup(hass, config):
    if config.get(DOMAIN, {}).get('disposable') is not True:
        return False
    async def started(_event):
        hass.async_create_task(Witness(hass).poll(), DOMAIN)
    if hass.is_running:
        hass.async_create_task(Witness(hass).poll(), DOMAIN)
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, started)
    return True
