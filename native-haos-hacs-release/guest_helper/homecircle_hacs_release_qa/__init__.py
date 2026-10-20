"""Temporary bounded helper for one genuine published-release HAOS/HACS rehearsal.

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

DOMAIN = "homecircle_hacs_release_qa"
CONTROL = "homecircle-hacs-release-qa-control"
RESULTS = "homecircle-hacs-release-qa-results"
CANDIDATE = "fc0b365d9688459504f874af5c38393e24145d657f15f1def8ada9184f363285"
BASE_CANDIDATE = "f0477a91e78181fe1f8d80ada176a1739e10a7502abe7ee6ee2240571280d1f5"
RELEASE_VERSION = "0.1.0-beta.20"
RELEASE_TAG = "v0.1.0-beta.20"
RELEASE_COMMIT = "d02a9bdb9027cb51c99165a09ba50d5b175f5fb9"
RELEASE_ID = 418643687
RELEASE_ASSET_ID = 659912694
RELEASE_ASSET_BYTES = 604937
BASELINE = "5f20d536e1b5378bef7f0b972bbfbc7ced911063aea16a0a8f56d2ffa1210cd2"
HACS = "97be6b824a4f38e683728cc6dd72367f6b8bad0a43428b1b3b987a3087adf413"
TAG = "v0.1.0-beta.19"
REPOSITORY = "jmhjr/HomeCircle"
PHASES = ("bootstrap_hacs", "baseline", "upgrade_download", "upgraded",
          "rollback_download", "rollback", "reupgrade_download", "final")
TRACKERS = ("device_tracker.homecircle_hacs_release_qa_a", "device_tracker.homecircle_hacs_release_qa_b")
TRACKER_UIDS = ("homecircle-hacs-release-qa-synthetic-a", "homecircle-hacs-release-qa-synthetic-b")
PERSON_NAMES = ("Synthetic Release Member A", "Synthetic Release Member B")
UNRELATED = "/local/homecircle_hacs_release_qa_unrelated.js"
OWNED_URL = "/homecircle_static/homecircle-card.js"
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
    check(re.fullmatch(r"[0-9a-f]{64}", CANDIDATE) is not None
          and re.fullmatch(r"[0-9a-f]{40}", RELEASE_COMMIT) is not None
          and RELEASE_ID > 0 and RELEASE_ASSET_ID > 0 and RELEASE_ASSET_BYTES > 0,
          "qa_release_pins_pending")
    check(value.get("schema") == 1 and value.get("core_version") == "2026.10.2", "qa_input_schema")
    check(value.get("candidate_sha256") == CANDIDATE and value.get("baseline_sha256") == BASELINE
          and value.get("hacs_zip_sha256") == HACS, "qa_input_hashes")
    check(value.get("base_candidate_sha256") == BASE_CANDIDATE
          and value.get("release_version") == RELEASE_VERSION and value.get("release_tag") == RELEASE_TAG
          and value.get("release_commit") == RELEASE_COMMIT
          and value.get("release_id") == RELEASE_ID and value.get("release_asset_id") == RELEASE_ASSET_ID
          and value.get("release_asset_sha256") == CANDIDATE
          and value.get("release_asset_bytes") == RELEASE_ASSET_BYTES
          and value.get("baseline_tag") == TAG and value.get("baseline_version") == "0.1.0-beta.19",
          "qa_release_input_pins")
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
    version = json.loads((package / "manifest.json").read_text())["version"]
    check(version == (RELEASE_VERSION if candidate else "0.1.0-beta.19"), "qa_package_version")
    return {"package_files_count": len(actual), "package_payload_sha256": digest(actual),
            "package_archive_sha256": CANDIDATE if candidate else BASELINE,
            "disk_manifest_version": version}


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
    owned_resources = [value for value in resources["items"]
                       if isinstance(value.get("url"), str) and value["url"].split("?")[0] == OWNED_URL]
    if unrelated != [expected["unrelated_resource"]] or owned_resources != [expected["owned_resource"]]:
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
                "dashboard_record": dashboard_record, "dashboard_sha256": stable["dashboard_sha256"]}
    resources = hass.data[LOVELACE_DATA].resources
    owned = [value for value in resources.async_items() if value["url"].split("?")[0] == OWNED_URL]
    check(len(owned) == 1 and owned[0]["id"] == stable["frontend_resource_id"], "qa_persisted_owned_resource_expected")
    expected["owned_resource"] = deepcopy(owned[0])
    async with asyncio.timeout(120):
        while not await hass.async_add_executor_job(persisted_snapshot_matches, directory, expected):
            await asyncio.sleep(0.25)


async def repository_for(hacs, tag):
    from custom_components.hacs.enums import HacsCategory

    repository = hacs.repositories.get_by_full_name(REPOSITORY)
    if repository is None:
        await hacs.async_register_repository(REPOSITORY, category=HacsCategory.INTEGRATION)
        repository = hacs.repositories.get_by_full_name(REPOSITORY)
    check(repository is not None and repository.data.full_name == REPOSITORY, "qa_hacs_repository")
    if not repository.data.show_beta or tag not in repository.data.published_tags \
            or not any(release.tag_name == tag for release in repository.releases.objects or []):
        # Official hacs/repository/beta backend; a fresh catalog is required after restart.
        repository.data.show_beta = True
        await repository.update_repository(force=True)
        repository.state = None
        await hacs.data.async_write()
    check(tag in repository.data.published_tags, "qa_published_tag_unavailable")
    # Official hacs/repository/version backend. Select a real published tag, never
    # a fabricated release or a branch aliased to the catalog's default branch.
    repository.data.selected_tag = tag
    await repository.update_repository(force=True)
    repository.state = None
    await hacs.data.async_write()
    check(repository.version_to_download() == tag and tag in repository.data.published_tags,
          "qa_selected_release_resolution")
    check(repository.repository_manifest.zip_release is True
          and repository.repository_manifest.filename == "homecircle.zip", "qa_release_zip_manifest")
    releases = [release for release in repository.releases.objects or [] if release.tag_name == tag]
    check(len(releases) == 1 and releases[0].draft is False and releases[0].prerelease is True,
          "qa_real_prerelease_required")
    release = releases[0]
    assets = [asset for asset in release.assets or [] if asset.name == "homecircle.zip"]
    check(len(assets) == 1, "qa_single_release_asset_required")
    asset = assets[0]
    url = f"https://github.com/{REPOSITORY}/releases/download/{tag}/homecircle.zip"
    check(asset.browser_download_url == url and type(asset.id) is int and asset.id > 0
          and type(asset.size) is int and asset.size > 0, "qa_release_asset_metadata")
    version = RELEASE_VERSION if tag == RELEASE_TAG else "0.1.0-beta.19"
    manifest = await repository.get_integration_manifest(version=tag)
    check(isinstance(manifest, dict) and manifest.get("domain") == "homecircle"
          and manifest.get("version") == version, "qa_tag_integration_manifest")
    proof = None
    if tag == RELEASE_TAG:
        check(release.id == RELEASE_ID and asset.id == RELEASE_ASSET_ID and asset.size == RELEASE_ASSET_BYTES,
              "qa_pinned_release_asset_identity")
        check(release.target_commitish == RELEASE_COMMIT, "qa_pinned_release_target")
        # The controller separately validates the real tag ref and downloads this
        # immutable asset to prove the ZIP SHA. HACS exposes its metadata here;
        # exact installed member hashes are checked after its genuine download.
        proof = {"tag": RELEASE_TAG, "version": RELEASE_VERSION, "commit": RELEASE_COMMIT,
                 "release_id": release.id, "asset_id": asset.id, "asset_bytes": asset.size,
                 "asset_sha256": CANDIDATE, "filename": asset.name, "zip_release": True,
                 "prerelease": True, "draft": False, "catalog_tag_present": True,
                 "selected_tag_resolved": True, "release_asset_metadata_checked": True,
                 "asset_sha256_source": "controller_verified_github_release_asset"}
    else:
        check(tag == TAG and asset.size == 575816, "qa_canonical_baseline_asset")
    return repository, proof


class Rehearsal:
    def __init__(self, hass):
        self.hass = hass
        self.directory = Path(hass.config.config_dir)
        self.control = self.directory / CONTROL
        self.loaded_source_sha = None
        self.loaded_module = None
        self.loaded_frontend = None
        self.loaded_frontend_version = None

    async def loaded(self, inputs, candidate):
        module = sys.modules.get("custom_components.homecircle")
        frontend = sys.modules.get("custom_components.homecircle.frontend")
        check(module is not None and frontend is not None, "qa_loaded_origin")
        expected = self.directory / "custom_components/homecircle/__init__.py"
        check(await self.hass.async_add_executor_job(lambda: Path(module.__file__).resolve() == expected.resolve()),
              "qa_loaded_origin")
        if self.loaded_module is None:
            self.loaded_module = module
            self.loaded_frontend = frontend
            self.loaded_frontend_version = frontend.VERSION
            self.loaded_source_sha = await self.hass.async_add_executor_job(
                lambda: digest(Path(module.__file__).read_bytes()))
        inventory = inputs["candidate_inventory" if candidate else "baseline_inventory"]
        check(module is self.loaded_module and frontend is self.loaded_frontend
              and frontend.VERSION == self.loaded_frontend_version
              and self.loaded_frontend_version == (RELEASE_VERSION if candidate else "0.1.0-beta.19")
              and self.loaded_source_sha == inventory["__init__.py"]["sha256"], "qa_loaded_release_identity")

    async def persistent(self, name, inputs, http_probe):
        hass = self.hass
        registry = er.async_get(hass)
        path = self.control / "baseline.json"
        baseline = await hass.async_add_executor_job(read_json, path) if await path_exists(hass, path) else None
        if name == "baseline":
            check(baseline is None and not hass.config_entries.async_entries("homecircle"), "qa_baseline_fresh")
            for uid, entity_id in zip(TRACKER_UIDS, TRACKERS, strict=True):
                check(registry.async_get_entity_id("device_tracker", DOMAIN, uid) is None, "qa_tracker_collision")
                item = registry.async_get_or_create("device_tracker", DOMAIN, uid,
                    suggested_object_id=entity_id.split(".", 1)[1])
                check(item.entity_id == entity_id, "qa_tracker_identity")
        for index, tracker in enumerate(TRACKERS):
            check(registry.async_get(tracker) is not None, "qa_tracker_missing")
            hass.states.async_set(tracker, "home", {"friendly_name": f"Synthetic Release tracker {index + 1}",
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
        current, details = await snapshot(hass, entry, people, registry, http_probe)
        if name == "baseline":
            await wait_entry_saved(hass, self.directory, entry)
            await wait_snapshot_saved(hass, self.directory, current)
            await hass.async_add_executor_job(write_json, path, current)
            details["persisted_storage_checked"] = True
        else:
            check(current == baseline, "qa_persistent_snapshot_changed")
        return current, details

    async def guard(self, name):
        hass = self.hass
        path = self.control / "guard.json"
        previous = await hass.async_add_executor_job(read_json, path) if await path_exists(hass, path) else None
        if name in {"upgraded", "final"}:
            from custom_components.homecircle.findmy_recovery_guard import get_recovery_guard

            guard = get_recovery_guard(hass)
            if name == "upgraded":
                check(previous is None and (await guard.status(GUARD_IDENTITY))["unresolved"] == 0,
                      "qa_guard_seed_fresh")
                for _ in range(3):
                    async with guard.attempt(GUARD_IDENTITY) as attempt:
                        await attempt.before_dispatch()
                        await attempt.refused()
            status = await guard.status(GUARD_IDENTITY)
            check(status["blocked"] is True and status["unresolved"] == status["rejected"] == 3
                  and status["pending"] == status["uncertain"] == 0, "qa_guard_status")
            fingerprint = await hass.async_add_executor_job(guard_files, self.directory)
            if name == "upgraded":
                await hass.async_add_executor_job(write_json, path,
                    {"sha256": fingerprint, "blocked": True, "unresolved": 3, "rejected": 3})
            else:
                check(previous is not None and previous["sha256"] == fingerprint, "qa_guard_restored")
            return {"blocked": True, "unresolved": 3, "rejected": 3, "sha256": fingerprint,
                    "api_status_checked": True, "retained_bytes_checked": True}
        check(previous is not None, "qa_prior_guard_required")
        fingerprint = await hass.async_add_executor_job(guard_files, self.directory)
        check(previous["sha256"] == fingerprint, "qa_guard_retained_bytes_changed")
        return {"blocked": previous["blocked"], "unresolved": previous["unresolved"],
                "rejected": previous["rejected"], "sha256": fingerprint,
                "api_status_checked": False, "retained_bytes_checked": True}

    async def run(self, phase, inputs):
        hass, directory = self.hass, self.directory
        name = phase["phase"]
        stage, http_probe = "platform", {}
        disk_candidate = name in {"upgrade_download", "upgraded", "reupgrade_download", "final"}
        loaded_candidate = name in {"upgraded", "rollback_download", "final"}
        tag = RELEASE_TAG if disk_candidate else TAG
        receipt = {"schema": 1, "token": phase["token"], "phase": name, "outcome": "failed",
                   "process": process(), "owner_accounts_used": False, "oauth_tested": False,
                   "core_version": CORE_VERSION, "production_configuration_used": False,
                   "branch": inputs["branch"], "branch_commit": inputs["branch_commit"],
                   "candidate_archive_sha256": CANDIDATE, "base_candidate_archive_sha256": BASE_CANDIDATE,
                   "candidate_hacs_tested": disk_candidate, "candidate_transport": "hacs_release_zip",
                   "apple_or_provider_requests": 0}
        try:
            async with asyncio.timeout(600):
                check(CORE_VERSION == "2026.10.2" and os.uname().machine == "x86_64", "qa_platform")
                stage = "hacs_catalog"
                hacs = await ensure_hacs(hass, directory)
                repository, release_proof = await repository_for(hacs, tag)
                if release_proof is not None:
                    receipt["release"] = release_proof
                downloading = name in {"bootstrap_hacs", "upgrade_download", "rollback_download", "reupgrade_download"}
                if name != "bootstrap_hacs":
                    stage = "loaded_before_download" if downloading else "loaded_after_restart"
                    await hass.async_add_executor_job(package_at, directory, inputs,
                        loaded_candidate if downloading else disk_candidate)
                    if name != "baseline":
                        await self.loaded(inputs, loaded_candidate)
                    stage = "persistent_snapshot"
                    # Before a download, all Python modules and served resources still
                    # belong to the existing runtime. Inspect before HACS replaces files.
                    current, details = await self.persistent(name, inputs, http_probe)
                    if name == "baseline":
                        await self.loaded(inputs, False)
                    receipt.update(details)
                    receipt["snapshot_sha256"] = digest(current)
                    if name in {"upgraded", "rollback", "reupgrade_download", "final", "rollback_download"}:
                        stage = "guard"
                        receipt["guard"] = await self.guard(name)
                else:
                    receipt["snapshot_sha256"] = None
                if downloading:
                    stage = "hacs_release_download"
                    was_installed = repository.data.installed
                    await repository.async_download_repository(ref=tag)
                    if not was_installed:
                        from custom_components.hacs.enums import HacsDispatchEvent

                        hacs.async_dispatch(HacsDispatchEvent.RELOAD, {"force": True})
                        await hacs.async_recreate_entities()
                    await hacs.data.async_write()
                    await wait_for(lambda: not hacs.queue.running and hacs.queue.pending_tasks == 0)
                    # Module identities/constants must remain the pre-download ones.
                    # Only a controller-owned real Core restart may activate new code.
                    if name != "bootstrap_hacs":
                        await self.loaded(inputs, loaded_candidate)
                    actual_ref = repository.ref
                    if isinstance(actual_ref, str) and actual_ref.startswith("tags/"):
                        actual_ref = actual_ref[len("tags/"):]
                    check(actual_ref == tag, "qa_downloaded_release_ref")
                    receipt["hacs_download_backend"] = "async_download_repository"
                    receipt["download_release_ref"] = actual_ref
                stage = "disk_release_identity"
                receipt.update(await hass.async_add_executor_job(package_at, directory, inputs, disk_candidate))
                check(repository.data.installed_version == tag and repository.data.installed is True,
                      "qa_hacs_installed_metadata")
                check(repository.repository_manifest.zip_release is True
                      and repository.repository_manifest.filename == "homecircle.zip", "qa_hacs_zip_transport_changed")
                receipt["hacs"] = {"version": hacs.version, "enabled": not hacs.system.disabled,
                                   "pending_tasks": hacs.queue.pending_tasks, "beta_enabled": repository.data.show_beta,
                                   "installed_version": repository.data.installed_version,
                                   "zip_release": True, "filename": repository.repository_manifest.filename}
                receipt["loaded_source_sha256"] = self.loaded_source_sha
                receipt["loaded_frontend_version"] = self.loaded_frontend_version
                receipt["outcome"] = "passed"
        except Exception as error:
            receipt.update({"outcome": "failed", "stage": stage, "failure_type": type(error).__name__})
            if isinstance(error, Refused):
                receipt["failure_code"] = str(error)
            if http_probe:
                receipt["http_probe"] = http_probe
            _LOGGER.error("Disposable release HACS rehearsal failed at %s (%s)", stage, type(error).__name__)
        await hass.async_add_executor_job(write_json, directory / RESULTS / (name + ".json"), receipt)

    async def poll(self):
        seen = set()
        while self.hass.is_running:
            try:
                inputs = await self.hass.async_add_executor_job(inputs_at, self.directory)
                path = self.control / "phase.json"
                if await path_exists(self.hass, path):
                    phase = await self.hass.async_add_executor_job(read_json, path)
                    name, token = phase.get("phase"), phase.get("token", "")
                    check(phase.get("schema") == 1 and name in PHASES and re.fullmatch(r"[0-9a-f]{32,64}", token)
                          and phase.get("branch") == inputs["branch"]
                          and phase.get("branch_commit") == inputs["branch_commit"], "qa_phase")
                    nonce_path = self.control / "job-nonce.json"
                    if await path_exists(self.hass, nonce_path):
                        check((await self.hass.async_add_executor_job(read_json, nonce_path))["token"] == token, "qa_job_nonce")
                    else:
                        check(name == "bootstrap_hacs", "qa_first_phase")
                        await self.hass.async_add_executor_job(write_json, nonce_path, {"token": token})
                    if name not in seen:
                        seen.add(name)
                        result_path = self.directory / RESULTS / (name + ".json")
                        if await path_exists(self.hass, result_path):
                            old = await self.hass.async_add_executor_job(read_json, result_path)
                            check(old.get("token") == token and old.get("phase") == name, "qa_phase_receipt_collision")
                        else:
                            await self.run(phase, inputs)
            except Exception as error:
                _LOGGER.error("Disposable release HACS controller input refused (%s)", type(error).__name__)
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


