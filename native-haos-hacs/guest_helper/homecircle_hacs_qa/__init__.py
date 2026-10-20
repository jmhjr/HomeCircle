"""Temporary bounded helper for one fresh, synthetic HAOS/HACS rehearsal.

Never distribute with HomeCircle. All state and token files remain in this
disposable /config. The external controller owns restarts and stopped backups.
"""

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
import stat
from types import MappingProxyType
from urllib.parse import urlsplit

import aiohttp
import probatio as vol

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.person import async_create_person, entities_in_person
from homeassistant.config_entries import ConfigEntry, ConfigEntryState, SOURCE_USER
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, __version__ as CORE_VERSION
from homeassistant.helpers import entity_registry as er

DOMAIN = "homecircle_hacs_qa"
CONTROL = "homecircle-hacs-qa-control"
RESULTS = "homecircle-hacs-qa-results"
CANDIDATE = "f0477a91e78181fe1f8d80ada176a1739e10a7502abe7ee6ee2240571280d1f5"
BASELINE = "5f20d536e1b5378bef7f0b972bbfbc7ced911063aea16a0a8f56d2ffa1210cd2"
HACS = "97be6b824a4f38e683728cc6dd72367f6b8bad0a43428b1b3b987a3087adf413"
TAG = "v0.1.0-beta.19"
REPOSITORY = "jmhjr/HomeCircle"
PHASES = ("bootstrap_hacs", "baseline", "candidate_install", "candidate",
          "rollback_download", "rollback", "final_install", "final")
TRACKERS = ("device_tracker.homecircle_hacs_qa_a", "device_tracker.homecircle_hacs_qa_b")
TRACKER_UIDS = ("homecircle-hacs-qa-synthetic-a", "homecircle-hacs-qa-synthetic-b")
PERSON_NAMES = ("Synthetic HACS Member A", "Synthetic HACS Member B")
UNRELATED = "/local/homecircle_hacs_qa_unrelated.js"
GUARD_IDENTITY = "a" * 64
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


def inputs_at(directory):
    root = directory / CONTROL
    check(root.is_dir() and not root.is_symlink(), "qa_control_path")
    value = read_json(root / "inputs.json")
    check(value.get("schema") == 1 and value.get("core_version") == "2026.10.2", "qa_input_schema")
    check(value.get("candidate_sha256") == CANDIDATE and value.get("baseline_sha256") == BASELINE
          and value.get("hacs_zip_sha256") == HACS, "qa_input_hashes")
    check(value.get("branch") == "codex/native-amd64-validation" and
          re.fullmatch(r"[0-9a-f]{40}", value.get("branch_commit", "")), "qa_branch")
    for key, count in (("candidate_inventory", 112), ("baseline_inventory", 109)):
        inventory = value.get(key)
        check(isinstance(inventory, dict) and len(inventory) == count, "qa_inventory_count")
        for name, item in inventory.items():
            path = PurePosixPath(name)
            check(name == path.as_posix() and not path.is_absolute() and ".." not in path.parts
                  and "\\" not in name and isinstance(item, dict) and set(item) == {"bytes", "sha256"}
                  and type(item["bytes"]) is int and 0 <= item["bytes"] < 16 * 1024**2
                  and re.fullmatch(r"[0-9a-f]{64}", item["sha256"]), "qa_inventory_member")
    return value


def package_at(directory, inputs, candidate):
    package = directory / "custom_components/homecircle"
    check(package.is_dir() and not package.is_symlink(), "qa_package_path")
    actual = {}
    for path in package.rglob("*"):
        check(not path.is_symlink(), "qa_package_symlink")
        if path.is_file() and "__pycache__" not in path.parts:
            raw = path.read_bytes()
            actual[path.relative_to(package).as_posix()] = {"bytes": len(raw), "sha256": digest(raw)}
    expected = inputs["candidate_inventory" if candidate else "baseline_inventory"]
    check(actual == expected, "qa_package_bytes")
    check(json.loads((package / "manifest.json").read_text())["version"] == "0.1.0-beta.19", "qa_package_version")
    return {"package_files_count": len(actual), "package_payload_sha256": digest(actual),
            "package_archive_sha256": CANDIDATE if candidate else BASELINE}


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


def ephemeral_token(path):
    check(not path.is_symlink() and stat.S_IMODE(path.stat().st_mode) == 0o600, "qa_ephemeral_token_mode")
    value = path.read_text().strip()
    check(bool(value) and len(value) < 512 and not any(character.isspace() for character in value), "qa_ephemeral_token")
    return value


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


def location_category(value):
    if not value:
        return "absent"
    try:
        path = urlsplit(value).path
    except (TypeError, ValueError):
        return "other"
    return "onboarding" if path in {"/onboarding", "/onboarding.html"} else "other"


async def snapshot(hass, entry, people, registry, http_probe):
    from custom_components.homecircle import api, frontend

    check(entry.state == ConfigEntryState.LOADED and bool(entry.options), "qa_entry_loaded")
    active = dict(entry.options or entry.data)
    check(active.get("people") == people and not active.get("findmy_accounts")
          and not active.get("life360_account") and active.get("city_lookup_enabled") is False,
          "qa_provider_config")
    runtime = entry.runtime_data
    check(not runtime.managed_trackers, "qa_external_provider")
    for person, tracker in zip(people, TRACKERS, strict=True):
        check(entities_in_person(hass, person) == [tracker] and
              active["members"][person]["trackers"] == [tracker], "qa_person_selection")
    projected = api.snapshot(runtime)
    check([item["id"] for item in projected["members"]] == people, "qa_snapshot_people")
    resources = hass.data[LOVELACE_DATA].resources
    await resources.async_get_info()
    items = list(resources.async_items())
    owned = [item for item in items if item["url"].split("?")[0] == frontend.URL]
    unrelated = [item for item in items if item["url"] == UNRELATED]
    check(len(owned) == len(unrelated) == 1, "qa_resources")
    url = await hass.async_add_executor_job(frontend.resource_url)
    check(owned[0]["url"] == url, "qa_resource_url")
    bundle = await hass.async_add_executor_job((Path(hass.config.path("custom_components/homecircle/frontend/homecircle-card.js"))).read_bytes)
    port = hass.http.server_port
    tls = hass.http.context is not None
    http_probe.update({"tls": tls, "expected_bytes": len(bundle), "expected_sha256": digest(bundle)})
    check(type(port) is int and 1 <= port <= 65535, "qa_http_active_port")
    http_probe["active_port"] = port
    check(not tls, "qa_http_fixture_tls")
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30), trust_env=False) as session:
        async with session.get(f"http://127.0.0.1:{port}" + url, allow_redirects=False) as response:
            http_probe.update({"status": response.status,
                               "location_category": location_category(response.headers.get("Location"))})
            chunks, received = [], 0
            async for chunk in response.content.iter_chunked(65536):
                received += len(chunk)
                check(received <= 32 * 1024**2, "qa_served_bundle_size")
                chunks.append(chunk)
            body = b"".join(chunks)
            http_probe.update({"response_bytes": len(body), "response_sha256": digest(body),
                               "body_matches": body == bundle})
            check(response.status == 200 and body == bundle, "qa_served_bundle")
    dashboard = hass.data[LOVELACE_DATA].dashboards.get("dashboard-homecircle")
    check(dashboard is not None and dashboard.config and dashboard.config.get("id"), "qa_dashboard")
    config = await dashboard.async_load(False)
    records = {}
    for entity_id in [*people, *TRACKERS]:
        item = registry.async_get(entity_id)
        check(item is not None, "qa_registry_record")
        records[entity_id] = {"id": item.id, "unique_id": item.unique_id}
    stable = {"entry_id": entry.entry_id, "entry_data": deepcopy(dict(entry.data)),
              "entry_options": deepcopy(dict(entry.options)), "runtime_config_sha256": digest(runtime.config),
              "people": people, "registry": records,
              "homecircle_registry": {item.entity_id: {"id": item.id, "unique_id": item.unique_id}
                                       for item in registry.entities.values() if item.platform == "homecircle"},
              "frontend_resource_id": owned[0]["id"], "unrelated_resource": unrelated[0],
              "dashboard_id": dashboard.config["id"], "dashboard_sha256": digest(config)}
    return stable, {"served_bundle_sha256": digest(bundle), "frontend_resource_url": url,
                    "static_served_bundle_matches": True, "nonempty_options": True,
                    "persistent_people": 2, "explicit_trackers": 2}


async def ensure_hacs(hass, directory):
    from custom_components.hacs.enums import HacsStage

    entries = hass.config_entries.async_entries("hacs")
    if not entries:
        path = directory / CONTROL / "github-token"
        token = await hass.async_add_executor_job(ephemeral_token, path)
        entry = ConfigEntry(version=1, minor_version=1, domain="hacs", title="Disposable HACS",
                            data={"token": token}, options={"experimental": True}, source=SOURCE_USER,
                            unique_id=None, discovery_keys=MappingProxyType({}), subentries_data=[])
        # Core's supported add API awaits setup itself; do not set up twice.
        await hass.config_entries.async_add(entry)
        await wait_for(lambda: entry.state == ConfigEntryState.LOADED)
        token = None
    else:
        check(len(entries) == 1, "qa_hacs_entry_count")
        await wait_for(lambda: entries[0].state == ConfigEntryState.LOADED)
    await wait_for(lambda: (hacs := hass.data.get("hacs")) is not None and
                   hacs.stage == HacsStage.RUNNING and not hacs.system.disabled and
                   hacs.queue is not None and not hacs.queue.running and hacs.queue.pending_tasks == 0, 420)
    check(hass.data["hacs"].version == "2.0.5", "qa_hacs_version")
    return hass.data["hacs"]


async def repository_for(hacs):
    from custom_components.hacs.enums import HacsCategory

    repository = hacs.repositories.get_by_full_name(REPOSITORY)
    if repository is None:
        await hacs.async_register_repository(REPOSITORY, category=HacsCategory.INTEGRATION)
        repository = hacs.repositories.get_by_full_name(REPOSITORY)
    check(repository is not None and repository.data.full_name == REPOSITORY, "qa_hacs_repository")
    if not repository.data.show_beta or TAG not in repository.data.published_tags:
        # Match the official hacs/repository/beta websocket backend exactly.
        repository.data.show_beta = True
        await repository.update_repository(force=True)
        repository.state = None
        await hacs.data.async_write()
    check(TAG in repository.data.published_tags, "qa_published_beta_unavailable")
    return repository


class Rehearsal:
    def __init__(self, hass):
        self.hass = hass
        self.directory = Path(hass.config.config_dir)
        self.control = self.directory / CONTROL
        self.loaded_source_sha = None
        self.loaded_module = None

    async def loaded(self, inventory):
        module = sys.modules.get("custom_components.homecircle")
        check(module is not None, "qa_loaded_origin")
        check(await self.hass.async_add_executor_job(lambda: Path(module.__file__).resolve() ==
              (self.directory / "custom_components/homecircle/__init__.py").resolve()), "qa_loaded_origin")
        if self.loaded_module is None:
            self.loaded_module = module
            self.loaded_source_sha = await self.hass.async_add_executor_job(
                lambda: digest(Path(module.__file__).read_bytes()))
        check(module is self.loaded_module and self.loaded_source_sha == inventory["__init__.py"]["sha256"],
              "qa_loaded_source")

    async def run(self, phase, inputs):
        hass, directory = self.hass, self.directory
        name = phase["phase"]
        stage = "platform"
        http_probe = {}
        receipt = {"schema": 1, "token": phase["token"], "phase": name, "outcome": "failed",
                   "process": process(), "owner_accounts_used": False, "oauth_tested": False,
                   "core_version": CORE_VERSION, "production_configuration_used": False,
                   "branch": inputs["branch"], "branch_commit": inputs["branch_commit"],
                   "candidate_hacs_tested": False, "candidate_transport": "stopped_verified_zip_files",
                   "apple_or_provider_requests": 0}
        try:
            async with asyncio.timeout(600):
                check(CORE_VERSION == "2026.10.2" and os.uname().machine == "x86_64", "qa_platform")
                stage = "hacs"
                hacs = await ensure_hacs(hass, directory)
                repository = await repository_for(hacs)
                if name in {"bootstrap_hacs", "rollback_download"}:
                    candidate = False
                    if name != "bootstrap_hacs":
                        before_candidate = name == "rollback_download"
                        await hass.async_add_executor_job(package_at, directory, inputs, before_candidate)
                        await self.loaded(inputs["candidate_inventory" if before_candidate else "baseline_inventory"])
                    stage = "hacs_download"
                    ref = TAG
                    was_installed = repository.data.installed
                    await repository.async_download_repository(ref=ref)
                    if not was_installed:
                        from custom_components.hacs.enums import HacsDispatchEvent

                        hacs.async_dispatch(HacsDispatchEvent.RELOAD, {"force": True})
                        await hacs.async_recreate_entities()
                    await hacs.data.async_write()
                    await wait_for(lambda: not hacs.queue.running and hacs.queue.pending_tasks == 0)
                    package = await hass.async_add_executor_job(package_at, directory, inputs, candidate)
                    check(repository.data.installed_version == ref, "qa_hacs_download_version")
                    receipt.update(package)
                    receipt["snapshot_sha256"] = None
                    receipt["hacs_download_backend"] = "async_download_repository"
                else:
                    candidate = name in {"candidate", "final"}
                    package = await hass.async_add_executor_job(package_at, directory, inputs, candidate)
                    if name != "baseline":
                        await self.loaded(inputs["candidate_inventory" if candidate else "baseline_inventory"])
                    stage = "persistent_setup"
                    registry = er.async_get(hass)
                    baseline_path = self.control / "baseline.json"
                    baseline = await hass.async_add_executor_job(read_json, baseline_path) if await path_exists(hass, baseline_path) else None
                    if name == "baseline":
                        check(baseline is None and not hass.config_entries.async_entries("homecircle"), "qa_baseline_fresh")
                        for uid, entity_id in zip(TRACKER_UIDS, TRACKERS, strict=True):
                            check(registry.async_get_entity_id("device_tracker", DOMAIN, uid) is None, "qa_tracker_collision")
                            item = registry.async_get_or_create("device_tracker", DOMAIN, uid,
                                                               suggested_object_id=entity_id.split(".", 1)[1])
                            check(item.entity_id == entity_id, "qa_tracker_identity")
                    for index, tracker in enumerate(TRACKERS):
                        check(registry.async_get(tracker) is not None, "qa_tracker_missing")
                        hass.states.async_set(tracker, "home", {"friendly_name": f"Synthetic HACS tracker {index + 1}",
                                              "source_type": "gps", "latitude": 0.0, "longitude": 0.0, "gps_accuracy": 5})
                    if name == "baseline":
                        entry, people = await create_homecircle(hass, registry)
                        resources = hass.data[LOVELACE_DATA].resources
                        await resources.async_get_info()
                        check(not any(item["url"] == UNRELATED for item in resources.async_items()), "qa_unrelated_collision")
                        await resources.async_create_item({"res_type": "module", "url": UNRELATED})
                    else:
                        check(baseline is not None, "qa_baseline_missing")
                        entries = hass.config_entries.async_entries("homecircle")
                        check(len(entries) == 1 and entries[0].entry_id == baseline["entry_id"], "qa_entry_identity")
                        entry, people = entries[0], baseline["people"]
                    await wait_for(lambda: entry.state == ConfigEntryState.LOADED and all(
                        hass.states.get(person) is not None and hass.states.get(person).attributes.get("source") == tracker
                        for person, tracker in zip(people, TRACKERS, strict=True)))
                    if name == "baseline":
                        await self.loaded(inputs["baseline_inventory"])
                    stage = "persistent_snapshot"
                    current, details = await snapshot(hass, entry, people, registry, http_probe)
                    if name == "baseline":
                        await hass.async_add_executor_job(write_json, baseline_path, current)
                    else:
                        check(current == baseline, "qa_persistent_snapshot_changed")
                    receipt.update(package)
                    receipt.update(details)
                    receipt["snapshot_sha256"] = digest(current)
                    stage = "guard"
                    if candidate:
                        from custom_components.homecircle.findmy_recovery_guard import get_recovery_guard

                        guard = get_recovery_guard(hass)
                        guard_path = self.control / "guard.json"
                        previous = await hass.async_add_executor_job(read_json, guard_path) if await path_exists(hass, guard_path) else None
                        if name == "candidate":
                            check(previous is None, "qa_guard_seed_repeat")
                            check((await guard.status(GUARD_IDENTITY))["unresolved"] == 0, "qa_guard_seed_fresh")
                            for _ in range(3):
                                async with guard.attempt(GUARD_IDENTITY) as attempt:
                                    await attempt.before_dispatch()
                                    await attempt.refused()
                        status = await guard.status(GUARD_IDENTITY)
                        check(status["blocked"] is True and status["unresolved"] == status["rejected"] == 3
                              and status["pending"] == status["uncertain"] == 0, "qa_guard_status")
                        current_guard = await hass.async_add_executor_job(guard_files, directory)
                        if name == "candidate":
                            await hass.async_add_executor_job(write_json, guard_path,
                                {"sha256": current_guard, "blocked": True, "unresolved": 3, "rejected": 3})
                        else:
                            check(previous is not None and previous["sha256"] == current_guard, "qa_guard_restored")
                        receipt["guard"] = {"blocked": True, "unresolved": 3, "rejected": 3,
                                            "sha256": current_guard, "api_status_checked": True}
                    elif name in {"rollback", "final_install"}:
                        previous = await hass.async_add_executor_job(read_json, self.control / "guard.json")
                        current_guard = await hass.async_add_executor_job(guard_files, directory)
                        check(previous["sha256"] == current_guard, "qa_guard_rollback_changed")
                        receipt["guard"] = {"sha256": current_guard, "retained_bytes_checked": True,
                                            "blocked": previous["blocked"], "unresolved": previous["unresolved"],
                                            "api_status_checked": False}
                    if name in {"candidate_install", "final_install"}:
                        stage = "catalog_preflight"
                        saved_selection = repository.data.selected_tag
                        try:
                            repository.data.selected_tag = inputs["branch"]
                            resolved = repository.version_to_download()
                        finally:
                            repository.data.selected_tag = saved_selection
                        check(isinstance(resolved, str) and resolved in {inputs["branch"], repository.data.default_branch},
                              "qa_hacs_catalog_resolution")
                        receipt["candidate_install_preflight"] = True
                        receipt["candidate_install_performed"] = False
                        receipt["hacs_catalog"] = {
                            "requested_branch": inputs["branch"], "resolved_manifest_ref": resolved,
                            "default_branch": repository.data.default_branch,
                            "stable_release_available": repository.data.last_version is not None,
                            "branch_catalog_limitation_observed": resolved != inputs["branch"],
                            "selected_tag_restored": repository.data.selected_tag == saved_selection,
                        }
                check(repository.data.installed_version == TAG, "qa_hacs_published_metadata")
                receipt["hacs"] = {"version": hacs.version, "enabled": not hacs.system.disabled, "pending_tasks": hacs.queue.pending_tasks,
                                   "beta_enabled": repository.data.show_beta,
                                   "installed_version": repository.data.installed_version}
                receipt["loaded_source_sha256"] = self.loaded_source_sha
                receipt["outcome"] = "passed"
        except Exception as error:
            receipt.update({"outcome": "failed", "stage": stage, "failure_type": type(error).__name__})
            if isinstance(error, Refused):
                receipt["failure_code"] = str(error)
            if http_probe:
                receipt["http_probe"] = http_probe
            _LOGGER.error("Disposable HACS rehearsal failed at %s (%s)", stage, type(error).__name__)
        await hass.async_add_executor_job(write_json, directory / RESULTS / (name + ".json"), receipt)

    async def poll(self):
        seen = set()
        while self.hass.is_running:
            try:
                inputs = await self.hass.async_add_executor_job(inputs_at, self.directory)
                path = self.control / "phase.json"
                if await path_exists(self.hass, path):
                    phase = await self.hass.async_add_executor_job(read_json, path)
                    name = phase.get("phase")
                    token = phase.get("token", "")
                    check(phase.get("schema") == 1 and name in PHASES and re.fullmatch(r"[0-9a-f]{32,64}", token)
                          and phase.get("branch") == inputs["branch"] and
                          phase.get("branch_commit") == inputs["branch_commit"], "qa_phase")
                    nonce_path = self.control / "job-nonce.json"
                    if await path_exists(self.hass, nonce_path):
                        check((await self.hass.async_add_executor_job(read_json, nonce_path))["token"] == token, "qa_job_nonce")
                    else:
                        check(name == "bootstrap_hacs", "qa_first_phase")
                        await self.hass.async_add_executor_job(write_json, nonce_path, {"token": token})
                    result_path = self.directory / RESULTS / (name + ".json")
                    if name not in seen:
                        seen.add(name)
                        if await path_exists(self.hass, result_path):
                            old = await self.hass.async_add_executor_job(read_json, result_path)
                            check(old.get("token") == token and old.get("phase") == name, "qa_phase_receipt_collision")
                        else:
                            await self.run(phase, inputs)
            except Exception as error:
                _LOGGER.error("Disposable HACS controller input refused (%s)", type(error).__name__)
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
