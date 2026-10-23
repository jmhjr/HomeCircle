"""Actual HACS release transport, installed activation, removal and rollback."""
from __future__ import annotations

import asyncio
import importlib.metadata
import os
import re
import stat
import sys

import aiohttp
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.util import dt as dt_util
from custom_components import provider_requests_denied

from . import donor as d
from .protocol import (ACTIVE, BASELINE, BASE_TAG, BASE_VERSION, CANDIDATE, CORE,
                       DISK, DOWNLOADS, HACS, INVENTORY, LOADED, PHASES, PHASE_KEYS,
                       SOURCE, TAG, VERSION, digest)

DOMAIN, CONTROL, RESULTS = d.DOMAIN, d.CONTROL, d.RESULTS
CONFIG_SCHEMA = d.CONFIG_SCHEMA
IDENTITY = "a" * 64
LEDGER = ".storage/homecircle_findmy/recovery_guard"
WITNESS = ".cache/homecircle_findmy/recovery_guard"
d.PHASES = PHASES
d.CANDIDATE = CANDIDATE
d.BASELINE = BASELINE
d.RELEASE_VERSION = VERSION
d.RELEASE_TAG = TAG
d.RELEASE_COMMIT = SOURCE
d.TAG = BASE_TAG
d.UNRELATED = "/local/example_hacs_unrelated.js"
d.TRACKERS = ("device_tracker.example_hacs_release_a", "device_tracker.example_hacs_release_b")
d.TRACKER_UIDS = ("example-hacs-release-a", "example-hacs-release-b")
check = d.check


def inputs_at(directory):
    value = d.read_json(directory / CONTROL / "inputs.json")
    check(set(value) == {"schema", "source_commit", "candidate_sha256", "baseline_sha256", "inventory_sha256",
          "anchor", "anchor_sha256", "candidate_inventory", "baseline_inventory", "core_version", "branch", "branch_commit"}, "qa_inputs_shape")
    check(value["schema"] == 1 and value["source_commit"] == SOURCE and value["candidate_sha256"] == CANDIDATE
          and value["baseline_sha256"] == BASELINE and value["inventory_sha256"] == INVENTORY
          and value["core_version"] == CORE, "qa_inputs_identity")
    check(re.fullmatch(r"[0-9a-f]{40}", value["branch_commit"]) and value["branch"] == d.REPOSITORY, "qa_inputs_branch")
    for key in ("candidate_inventory", "baseline_inventory"):
        check(isinstance(value[key], dict) and len(value[key]) == 112, "qa_inputs_inventory")
    return value


def guard_pair(directory, generation=None):
    """Only deterministic synthetic byte preservation; no guard API is called."""
    entry = {"rejected": 1 if generation == 1 else 2, "uncertain": 0, "verified": 0,
             "pending": None, "generation": str(generation or 2) * 32}
    paths = [directory / LEDGER / "ledger.json", directory / WITNESS / ("account-" + IDENTITY + ".json")]
    if generation is not None:
        for path in paths:
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.chmod(path.parent, 0o700)
            os.chmod(path.parent.parent, 0o700)
        ledger = {"version": 2, "accounts": {IDENTITY: entry}}
        witness = {"version": 1, "digest": digest({"identity": IDENTITY, "entry": entry})}
        for path, value in zip(paths, (ledger, witness), strict=True):
            d.write_json(path, value)
    for path in paths:
        check(path.is_file() and not path.is_symlink() and stat.S_IMODE(path.stat().st_mode) == 0o600, "qa_guard_fixture_file")
    ledger, witness = (d.read_json(path) for path in paths)
    check(set(ledger) == {"version", "accounts"} and ledger["version"] == 2 and set(ledger["accounts"]) == {IDENTITY}, "qa_guard_fixture_ledger")
    actual = ledger["accounts"][IDENTITY]
    check(actual == entry or (generation is None and actual == {**entry, "rejected": 1, "generation": "1" * 32}), "qa_guard_fixture_entry")
    check(witness == {"version": 1, "digest": digest({"identity": IDENTITY, "entry": actual})}, "qa_guard_fixture_witness")
    return {"generation": int(actual["generation"][0]), "ledger_sha256": digest(paths[0].read_bytes()),
            "witness_sha256": digest(paths[1].read_bytes()), "byte_preservation_only": True}


async def repository_for(hacs, candidate):
    from custom_components.hacs.enums import HacsCategory

    tag, version = (TAG, VERSION) if candidate else (BASE_TAG, BASE_VERSION)
    repository = hacs.repositories.get_by_full_name(d.REPOSITORY)
    if repository is None:
        await hacs.async_register_repository(d.REPOSITORY, category=HacsCategory.INTEGRATION)
        repository = hacs.repositories.get_by_full_name(d.REPOSITORY)
    check(repository is not None, "qa_hacs_repository")
    repository.data.show_beta = True
    repository.data.selected_tag = tag
    await repository.update_repository(force=True)
    repository.state = None
    await hacs.data.async_write()
    check(tag in repository.data.published_tags and repository.version_to_download() == tag, "qa_catalog_selected_tag")
    check(repository.repository_manifest.zip_release is True and repository.repository_manifest.filename == "homecircle.zip", "qa_hacs_zip_manifest")
    releases = [release for release in repository.releases.objects or [] if release.tag_name == tag]
    check(len(releases) == 1 and releases[0].draft is False and releases[0].prerelease is True, "qa_catalog_prerelease")
    release = releases[0]
    assets = [asset for asset in release.assets or [] if asset.name == "homecircle.zip"]
    check(len(assets) == 1, "qa_catalog_asset_count")
    asset = assets[0]
    anchor = hacs.hass.data[DOMAIN + "_inputs"]["anchor"]
    expected = (anchor["release_id"], anchor["asset_id"], 628136, SOURCE) if candidate else (
        418643687, 659912694, 604937, "d02a9bdb9027cb51c99165a09ba50d5b175f5fb9")
    check((release.id, asset.id, asset.size, release.target_commitish) == expected, "qa_catalog_asset_identity")
    check(asset.browser_download_url == f"https://github.com/{d.REPOSITORY}/releases/download/{tag}/homecircle.zip", "qa_catalog_asset_url")
    manifest = await repository.get_integration_manifest(version=tag)
    check(manifest.get("version") == version and manifest.get("domain") == "homecircle", "qa_catalog_manifest")
    return repository


async def removal_status(hass, directory, *, after_restart):
    check(not hass.config_entries.async_entries("homecircle"), "qa_removed_entry")
    check(not (directory / "custom_components/homecircle").exists(), "qa_removed_package")
    saved = await hass.async_add_executor_job(d.read_json, directory / CONTROL / "baseline.json")
    check(not await d.path_exists(hass, directory / (".storage/homecircle.activity." + saved["entry_id"])), "qa_removed_activity_store")
    resources = hass.data[LOVELACE_DATA].resources
    await resources.async_get_info()
    items = list(resources.async_items())
    check(not any(item["url"].split("?")[0] == d.OWNED_URL for item in items), "qa_removed_resource")
    check(len([item for item in items if item["url"] == d.UNRELATED]) == 1, "qa_unrelated_resource_retained")
    check("dashboard-homecircle" not in hass.data[LOVELACE_DATA].dashboards, "qa_removed_dashboard")
    if after_restart:
        check(not any(name == "custom_components.homecircle" or name.startswith("custom_components.homecircle.") for name in sys.modules), "qa_removed_loaded_module")
    port = hass.http.server_port
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30), trust_env=False) as session:
        async with session.get(f"http://127.0.0.1:{port}" + d.OWNED_URL, allow_redirects=False) as response:
            check(response.status == 404, "qa_removed_static_route")
        async with session.get(f"http://127.0.0.1:{port}" + d.UNRELATED, allow_redirects=False) as response:
            check(response.status == 200 and await response.read() == b"/* synthetic unrelated HACS asset */\n", "qa_unrelated_static_retained")


async def activity_markers(hass, directory, name, entry_id):
    """Two explicit local test markers, not provider reports or journey proof."""
    entry = hass.config_entries.async_get_entry(entry_id)
    log = entry.runtime_data.activity
    check(log is not None and log.store is not None and not log.closed, "qa_activity_available")
    cohort_path = directory / CONTROL / "activity-markers.json"
    if name == "baseline":
        now = dt_util.utcnow()
        cohort = {}
        for person in sorted(log.members):
            log.append(person, "refresh", "checked", now)
            cohort[person] = dict(log.events[person][-1])
        check(len(cohort) == 2, "qa_activity_marker_members")
        await log.save()
        check(log.store is not None, "qa_activity_marker_save")
        await hass.async_add_executor_job(d.write_json, cohort_path, cohort)
    else:
        cohort = await hass.async_add_executor_job(d.read_json, cohort_path)
    check(set(cohort) == log.members and len(cohort) == 2, "qa_activity_cohort_identity")
    stored = await hass.async_add_executor_job(d.read_json, directory / (".storage/homecircle.activity." + entry_id))
    check(stored["data"]["fingerprint"] == log.fingerprint, "qa_activity_saved_fingerprint")
    for person, event in cohort.items():
        check(set(event) == {"kind", "value", "observed_at"} and event["kind"] == "refresh"
              and event["value"] == "checked" and event in log.events[person]
              and event in stored["data"]["events"][person], "qa_activity_marker_retained")
    return {"count": 2, "cohort_sha256": digest(cohort), "retained": True}


class Rehearsal(d.Rehearsal):
    async def run(self, phase, inputs):
        name = phase["phase"]
        receipt = {"schema": 1, "phase": name, "outcome": "failed", "source_commit": SOURCE,
            "candidate_sha256": CANDIDATE, "baseline_sha256": BASELINE, "anchor_sha256": inputs["anchor_sha256"],
            "branch_commit": inputs["branch_commit"], "nonce_sha256": digest(phase["token"].encode()),
            "core_version": CORE, "process": d.process(), "hacs": None, "disk": None, "loaded": None,
            "frontend": None, "snapshot_sha256": None, "persisted_store_checked": False,
            "download_tag": None, "release_proof": False, "removed": False, "guard": None,
            "activity": None, "removed_activity_store": False,
            "provider_requests_denied": 0, "provider_accounts": 0, "recovery_api_calls": 0,
            "normal_requirements": None}
        stage = "inputs"
        try:
            async with asyncio.timeout(600):
                self.hass.data[DOMAIN + "_inputs"] = inputs
                check(d.CORE_VERSION == CORE and os.uname().machine == "x86_64", "qa_core_platform")
                stage = "hacs_ready"
                hacs = await d.ensure_hacs(self.hass, self.directory)
                if name == "bootstrap_hacs":
                    check(not (self.directory / "custom_components/homecircle").exists()
                          and not self.hass.config_entries.async_entries("homecircle"), "qa_bootstrap_clean")
                    repository = None
                elif name in {"fresh_remove", "fresh_removed"}:
                    repository = hacs.repositories.get_by_full_name(d.REPOSITORY)
                    check(repository is not None, "qa_removal_repository")
                    if name == "fresh_remove":
                        stage = "config_entry_remove"
                        entries = self.hass.config_entries.async_entries("homecircle")
                        check(len(entries) == 1, "qa_removal_entry_count")
                        await self.loaded(inputs, True)
                        await self.hass.config_entries.async_remove(entries[0].entry_id)
                        stage = "hacs_uninstall"
                        await repository.uninstall()
                        await hacs.data.async_write()
                    await removal_status(self.hass, self.directory, after_restart=name == "fresh_removed")
                    check(repository.data.installed is False and repository.data.installed_version is None, "qa_hacs_uninstalled")
                    receipt["removed"] = True
                    receipt["removed_activity_store"] = True
                else:
                    candidate = DISK[name] == "candidate"
                    stage = "hacs_catalog"
                    repository = await repository_for(hacs, candidate)
                    receipt["release_proof"] = True
                    if name in ACTIVE:
                        stage = "persistent_state"
                        if name == "baseline":
                            await self.hass.async_add_executor_job(guard_pair, self.directory, 1)
                        current, details = await self.persistent("baseline" if name in {"baseline", "fresh"} else name, inputs, {})
                        await self.loaded(inputs, LOADED[name] == "candidate")
                        receipt["snapshot_sha256"] = digest(current)
                        receipt["frontend"] = {"bundle_sha256": details["served_bundle_sha256"],
                            "url": details["frontend_resource_url"], "served": details["static_served_bundle_matches"]}
                        if name in {"baseline", "fresh"}:
                            receipt["persisted_store_checked"] = True
                        if name != "fresh":
                            receipt["guard"] = await self.hass.async_add_executor_job(guard_pair, self.directory, 2 if name == "upgraded" else None)
                            receipt["activity"] = await activity_markers(self.hass, self.directory, name, current["entry_id"])
                    if name in DOWNLOADS:
                        stage = "hacs_download"
                        was_installed = repository.data.installed
                        await repository.async_download_repository(ref=DOWNLOADS[name])
                        if not was_installed:
                            from custom_components.hacs.enums import HacsDispatchEvent
                            hacs.async_dispatch(HacsDispatchEvent.RELOAD, {"force": True})
                            await hacs.async_recreate_entities()
                        await hacs.data.async_write()
                        await d.wait_for(lambda: not hacs.queue.running and hacs.queue.pending_tasks == 0)
                        ref = repository.ref.removeprefix("tags/")
                        check(ref == DOWNLOADS[name], "qa_actual_download_ref")
                        receipt["download_tag"] = ref
                        if LOADED[name] is not None:
                            await self.loaded(inputs, LOADED[name] == "candidate")
                    stage = "installed_bytes"
                    result = await self.hass.async_add_executor_job(d.package_at, self.directory, inputs, candidate)
                    receipt["disk"] = {"version": result["disk_manifest_version"], "files": result["package_files_count"],
                                       "payload_sha256": result["package_payload_sha256"]}
                    expected_tag = TAG if candidate else BASE_TAG
                    check(repository.data.installed is True and repository.data.installed_version == expected_tag, "qa_hacs_installed_identity")
                if LOADED[name] is not None:
                    receipt["loaded"] = {"version": self.loaded_frontend_version, "source_sha256": self.loaded_source_sha}
                receipt["hacs"] = {"version": hacs.version, "enabled": not hacs.system.disabled,
                    "queue_pending": hacs.queue.pending_tasks, "installed": bool(repository and repository.data.installed),
                    "installed_version": repository.data.installed_version if repository else None}
                check(hacs.version == HACS and not hacs.system.disabled and not hacs.queue.pending_tasks, "qa_hacs_idle")
                if LOADED[name] == "candidate":
                    versions = {key: importlib.metadata.version(key) for key in ("cryptography", "srp", "unicorn")}
                    check(versions == {"cryptography": "50.0.1", "srp": "1.0.22", "unicorn": "2.1.4"}, "qa_candidate_requirements")
                    check(self.hass.config.skip_pip is False, "qa_normal_requirement_handling")
                    receipt["normal_requirements"] = versions
                receipt["provider_requests_denied"] = provider_requests_denied()
                check(receipt["provider_requests_denied"] == 0, "qa_provider_request_attempted")
                check(set(receipt) == PHASE_KEYS, "qa_receipt_schema")
                receipt["outcome"] = "passed"
        except Exception as error:
            receipt["failure"] = {"stage": stage, "type": type(error).__name__,
                "code": str(error) if isinstance(error, d.Refused) and re.fullmatch(r"[a-z0-9_]{1,80}", str(error)) else None}
        await self.hass.async_add_executor_job(d.write_json, self.directory / RESULTS / (name + ".json"), receipt)

    async def loaded(self, inputs, candidate):
        # The executed donor compares the baseline label to beta19. Rebind its
        # VERSION constant only while reading the already loaded frontend.
        await super().loaded(inputs, candidate)


d.inputs_at = inputs_at
# Donor methods use explicit old baseline literals; the preparation verifies and
# replaces those two version literals in its private donor copy only.


async def async_setup(hass, config):
    if config.get(DOMAIN, {}).get("disposable") is not True:
        return False

    async def started(_event):
        hass.async_create_task(Rehearsal(hass).poll(), DOMAIN)

    if hass.is_running:
        await started(None)
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, started)
    return True
