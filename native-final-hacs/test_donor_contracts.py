"""Offline controller contracts; run only on the native Linux CI runner."""

from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

import donor_host as controller


class ArchiveContracts(unittest.TestCase):
    def archive(self, members):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for name, value in members:
                archive.writestr(name, value)
        return buffer.getvalue()

    def inspect(self, raw, count):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input.zip"
            path.write_bytes(raw)
            return controller.check_archive(path, controller.sha(raw), count)

    def test_exact_inventory_is_derived_from_bytes(self):
        self.assertEqual(self.inspect(self.archive([("__init__.py", b"example")]), 1),
                         {"__init__.py": {"bytes": 7, "sha256": controller.sha(b"example")}})

    def test_parent_and_absolute_names_are_refused(self):
        for name in ("../outside", "/outside", "normal\\outside"):
            with self.subTest(name=name), self.assertRaises(controller.Refused):
                self.inspect(self.archive([(name, b"example")]), 1)

    def test_duplicate_members_cannot_hide_archive_contents(self):
        with self.assertWarns(UserWarning):
            raw = self.archive([("one", b"first"), ("one", b"second")])
        with self.assertRaises(controller.Refused):
            self.inspect(raw, 1)

    def test_archive_pin_is_mandatory(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input.zip"
            path.write_bytes(self.archive([("one", b"example")]))
            with self.assertRaises(controller.Refused):
                controller.check_archive(path, "0" * 64, 1)


class PublicDiagnostics(unittest.TestCase):
    def test_core_version_projection_excludes_arbitrary_response_strings(self):
        for value in ("2026.10.2", "2026.10.0b1", "landingpage"):
            self.assertEqual(controller.public_core_version(value), value)
        for value in (None, {}, "private-value", "2026.10.2 private-value", "https://example.invalid"):
            self.assertIsNone(controller.public_core_version(value))

    def test_supervisor_projection_excludes_arbitrary_private_fields(self):
        value = {"result": "ok", "data": {"healthy": True, "supported": False, "state": "running",
                 "ip_address": "PRIVATE-CANARY", "token": "PRIVATE-CANARY", "version": "PRIVATE-CANARY"}}
        projected = controller.public_supervisor_state(value)
        self.assertEqual(projected, {"result": "ok", "healthy": True, "supported": False, "state": "running"})
        self.assertNotIn("PRIVATE-CANARY", json.dumps(projected))

    def test_root_info_state_and_version_exclude_host_identifiers(self):
        value = {"result": "ok", "data": {"state": "running", "supervisor": "2026.10.0",
                 "supported": True, "hostname": "PRIVATE-CANARY", "machine_id": "PRIVATE-CANARY"}}
        self.assertEqual(controller.public_root_state(value), {
            "result": "ok", "state": "running", "supervisor_version": "2026.10.0", "supported": True})

    def test_http_projection_refuses_invalid_types_and_unbounded_values(self):
        self.assertEqual(controller.public_http_probe({
            "active_port": True, "status": 600, "response_bytes": -1, "expected_bytes": 32 * 1024**2 + 1,
            "tls": "PRIVATE-CANARY", "body_matches": 1, "response_sha256": "PRIVATE-CANARY",
            "expected_sha256": "A" * 64, "location_category": "https://PRIVATE-CANARY/",
        }), {})
        for value in (None, [], "PRIVATE-CANARY"):
            self.assertEqual(controller.public_http_probe(value), {})


class ManagementJobs(unittest.TestCase):
    def project(self, jobs):
        return controller.public_jobs({"result": "ok", "data": {"jobs": jobs}})

    def test_not_started_nested_core_job_blocks_readiness(self):
        jobs = self.project([{"name": "unrelated_background_task", "done": False, "child_jobs": [
            {"name": "home_assistant_core_start", "done": None, "child_jobs": []}]}])
        self.assertFalse(controller.core_jobs_idle(jobs))

    def test_unrelated_perpetual_job_does_not_block_completed_core(self):
        jobs = self.project([{"name": "unrelated_background_task", "done": False},
                             {"name": "home_assistant_core_install", "done": True}])
        self.assertTrue(controller.core_jobs_idle(jobs))

    def test_unknown_job_identity_is_not_silently_accepted_as_idle(self):
        with self.assertRaises(controller.Refused):
            self.project([{"name": None, "done": False}])

    def test_large_tree_is_refused_instead_of_truncated(self):
        with self.assertRaises(controller.Refused):
            self.project([{"name": "unrelated_background_task", "done": True}] * 257)


class PinnedRelease(unittest.TestCase):
    def setUp(self):
        self.pins = patch.multiple(controller, CANDIDATE_SHA="c" * 64,
            RELEASE_COMMIT="d" * 40, RELEASE_ID=123, RELEASE_ASSET_ID=456, RELEASE_ASSET_BYTES=789)
        self.pins.start()
        self.addCleanup(self.pins.stop)

    def metadata(self):
        return {"id": 123, "tag_name": controller.RELEASE_TAG, "target_commitish": "d" * 40,
                "prerelease": True, "draft": False, "assets": [{"name": "homecircle.zip", "id": 456,
                "size": 789, "state": "uploaded", "digest": "sha256:" + "c" * 64,
                "browser_download_url": "https://github.com/jmhjr/HomeCircle/releases/download/"
                                        + controller.RELEASE_TAG + "/homecircle.zip"}]}

    def test_unpublished_placeholder_pins_fail_closed(self):
        for key in ("CANDIDATE_SHA", "RELEASE_COMMIT", "RELEASE_ID", "RELEASE_ASSET_ID", "RELEASE_ASSET_BYTES"):
            with self.subTest(key=key), patch.object(controller, key, None), self.assertRaises(controller.Refused):
                controller.finalized_release_pins()

    def test_final_release_pins_are_required_before_guest_creation(self):
        controller.finalized_release_pins()
        self.assertEqual(controller.validate_release_metadata(self.metadata())["asset_id"], 456)

    def test_draft_stable_or_wrong_tag_is_not_the_pinned_prerelease(self):
        for key, value in (("draft", True), ("prerelease", False), ("tag_name", "main"),
                           ("target_commitish", "main"), ("id", 124)):
            raw = self.metadata()
            raw[key] = value
            with self.subTest(key=key), self.assertRaises(controller.Refused):
                controller.validate_release_metadata(raw)

    def test_release_asset_requires_exact_identity_bytes_digest_and_public_url(self):
        for key, value in (("id", 457), ("size", 790), ("digest", "sha256:" + "0" * 64),
                           ("browser_download_url", "https://PRIVATE-CANARY/"), ("state", "new")):
            raw = self.metadata()
            raw["assets"][0][key] = value
            with self.subTest(key=key), self.assertRaises(controller.Refused):
                controller.validate_release_metadata(raw)

    def test_duplicate_named_assets_are_refused(self):
        raw = self.metadata()
        raw["assets"] *= 2
        with self.assertRaises(controller.Refused):
            controller.validate_release_metadata(raw)

    def test_authenticated_api_redirect_never_transfers_token(self):
        with self.assertRaisesRegex(controller.Refused, "github_api_redirect_refused"):
            controller.NoAPIRedirect().redirect_request(None, None, 302, "", {}, "https://github.com/")

    def test_public_asset_redirect_rejects_other_hosts_and_credentials(self):
        for url in ("http://github.com/", "https://PRIVATE-CANARY/", "https://user@github.com/"):
            with self.subTest(url=url), self.assertRaises(controller.Refused):
                controller.PublicAssetRedirect().redirect_request(None, None, 302, "", {}, url)


class VersionOnlyPackage(unittest.TestCase):
    def setUp(self):
        self.base = {"file" + str(index): b"unchanged" for index in range(109)}
        self.base.update({name: b"runtime 0.1.0-beta.19" for name in
                          ("manifest.json", "frontend.py", "frontend/homecircle-card.js")})
        self.versioned = {name: value.replace(b"0.1.0-beta.19", b"0.1.0-beta.20")
                          for name, value in self.base.items()}

    def test_exact_three_version_changes_and_109_identical_files(self):
        self.assertEqual(controller.version_only_delta(self.base, self.versioned)["unchanged_files"], 109)

    def test_extra_behavior_change_is_refused(self):
        self.versioned["frontend.py"] += b"behavior change"
        with self.assertRaises(controller.Refused):
            controller.version_only_delta(self.base, self.versioned)

    def test_rebuilt_bundle_must_carry_new_version(self):
        self.versioned["frontend/homecircle-card.js"] = self.base["frontend/homecircle-card.js"]
        with self.assertRaises(controller.Refused):
            controller.version_only_delta(self.base, self.versioned)

    def test_file_set_or_nonversion_member_change_is_refused(self):
        for name in ("file1", "new-file"):
            changed = dict(self.versioned)
            changed[name] = b"different"
            with self.subTest(name=name), self.assertRaises(controller.Refused):
                controller.version_only_delta(self.base, changed)


class PhaseContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.pins = patch.multiple(controller, CANDIDATE_SHA="c" * 64,
            RELEASE_COMMIT="d" * 40, RELEASE_ID=123, RELEASE_ASSET_ID=456, RELEASE_ASSET_BYTES=789)
        self.pins.start()
        self.addCleanup(self.pins.stop)
        self.host = controller.Controller(SimpleNamespace(branch_commit="a" * 40))
        self.host.public = Path(self.temporary.name)
        self.host.config_path = "/mnt/data/supervisor/homeassistant"
        self.host.guest_write = Mock()
        self.host.guest = Mock(return_value=b"")
        # __init__ can be identical while frontend.VERSION differs: loaded source
        # alone must never qualify activation of the separately versioned ZIP.
        self.inventory = {"__init__.py": {"bytes": 7, "sha256": controller.sha(b"example")},
                          "frontend/homecircle-card.js": {"bytes": 6, "sha256": "f" * 64}}
        self.host.inventories = {"baseline": self.inventory, "candidate": self.inventory}

    def receipt(self, name):
        new = name in {"upgrade_download", "upgraded", "reupgrade_download", "final"}
        loaded_new = name in {"upgraded", "rollback_download", "final"}
        bootstrap = name == "bootstrap_hacs"
        result = {"schema": 1, "token": self.host.nonce, "phase": name, "outcome": "passed",
            "branch_commit": "a" * 40, "core_version": controller.CORE,
            "candidate_archive_sha256": "c" * 64, "base_candidate_archive_sha256": controller.BASE_CANDIDATE_SHA,
            "package_files_count": 2, "package_payload_sha256": controller.sha(controller.canonical(self.inventory)),
            "package_archive_sha256": "c" * 64 if new else controller.BASELINE_SHA,
            "disk_manifest_version": controller.RELEASE_VERSION if new else controller.BASELINE_VERSION,
            "loaded_source_sha256": None if bootstrap else self.inventory["__init__.py"]["sha256"],
            "loaded_frontend_version": None if bootstrap else
                (controller.RELEASE_VERSION if loaded_new else controller.BASELINE_VERSION),
            "snapshot_sha256": None if bootstrap else "b" * 64,
            "process": {"pid": 123, "start_ticks": 456},
            "hacs": {"enabled": True, "pending_tasks": 0,
                     "installed_version": controller.RELEASE_TAG if new else controller.BASELINE_TAG},
            "candidate_hacs_tested": new, "candidate_transport": "hacs_release_zip",
            "hacs_download_backend": "async_download_repository",
            "download_release_ref": controller.RELEASE_TAG if new else controller.BASELINE_TAG,
            "persisted_storage_checked": True}
        if not bootstrap:
            version = controller.RELEASE_VERSION if loaded_new else controller.BASELINE_VERSION
            result.update(served_bundle_sha256="f" * 64, static_served_bundle_matches=True,
                frontend_resource_url="/homecircle_static/homecircle-card.js?v=" + version + "&asset=" + "f" * 12,
                nonempty_options=True, persistent_people=2, explicit_trackers=2)
        if new:
            result["release"] = {"tag": controller.RELEASE_TAG, "version": controller.RELEASE_VERSION,
                "commit": "d" * 40, "release_id": 123, "asset_id": 456, "asset_bytes": 789,
                "asset_sha256": "c" * 64, "filename": "homecircle.zip", "zip_release": True,
                "prerelease": True, "draft": False, "catalog_tag_present": True,
                "selected_tag_resolved": True, "release_asset_metadata_checked": True,
                "asset_sha256_source": "controller_verified_github_release_asset"}
        if name in {"upgraded", "rollback_download", "rollback", "reupgrade_download", "final"}:
            result["guard"] = {"blocked": True, "unresolved": 3, "rejected": 3, "sha256": "e" * 64,
                "api_status_checked": name in {"upgraded", "final"}, "retained_bytes_checked": True}
        return result

    def project(self, name, value=None):
        return self.host.project_receipt(name, value if value is not None else self.receipt(name))

    def test_all_eight_disk_and_loaded_versions_follow_real_restart_boundaries(self):
        expected = [(None, "19"), ("19", "19"), ("19", "20"), ("20", "20"),
                    ("20", "19"), ("19", "19"), ("19", "20"), ("20", "20")]
        for name, (loaded, disk) in zip(controller.PHASES, expected, strict=True):
            with self.subTest(name=name):
                result = self.project(name)
                self.assertEqual(result["disk_manifest_version"], "0.1.0-beta." + disk)
                self.assertEqual(result["loaded_frontend_version"], None if loaded is None else "0.1.0-beta." + loaded)

    def test_same_init_hash_cannot_hide_stale_loaded_frontend_version(self):
        value = self.receipt("upgraded")
        value["loaded_frontend_version"] = controller.BASELINE_VERSION
        with self.assertRaisesRegex(controller.Refused, "phase_loaded_version_refused"):
            self.project("upgraded", value)

    def test_loaded_bundle_must_match_pinned_bytes_and_versioned_resource(self):
        for key, bad in (("served_bundle_sha256", "0" * 64), ("static_served_bundle_matches", False),
                         ("frontend_resource_url", "/homecircle_static/homecircle-card.js?v=0.1.0-beta.19")):
            value = self.receipt("upgraded")
            value[key] = bad
            with self.subTest(key=key), self.assertRaisesRegex(controller.Refused, "phase_served_active_bundle_refused"):
                self.project("upgraded", value)

    def test_passing_receipt_cannot_override_exact_disk_inventory(self):
        value = self.receipt("upgraded")
        value["package_payload_sha256"] = "0" * 64
        with self.assertRaises(controller.Refused):
            self.project("upgraded", value)

    def test_no_manual_install_or_branch_fallback_can_claim_release_transport(self):
        for key, bad in (("candidate_transport", "stopped_verified_zip_files"),
                         ("hacs_download_backend", "manual_zip"), ("download_release_ref", "main")):
            value = self.receipt("upgrade_download")
            value[key] = bad
            with self.subTest(key=key), self.assertRaises(controller.Refused):
                self.project("upgrade_download", value)

    def test_every_new_release_phase_requires_actual_catalog_asset_metadata(self):
        for name in ("upgrade_download", "upgraded", "reupgrade_download", "final"):
            value = self.receipt(name)
            del value["release"]["release_asset_metadata_checked"]
            with self.subTest(name=name), self.assertRaises(controller.Refused):
                self.project(name, value)

    def test_beta20_must_not_leave_hacs_installed_version_at_beta19(self):
        value = self.receipt("upgraded")
        value["hacs"]["installed_version"] = controller.BASELINE_TAG
        with self.assertRaises(controller.Refused):
            self.project("upgraded", value)

    def test_hacs_queue_must_be_empty_at_every_phase(self):
        for name in controller.PHASES:
            value = self.receipt(name)
            value["hacs"]["pending_tasks"] = 1
            with self.subTest(name=name), self.assertRaises(controller.Refused):
                self.project(name, value)

    def test_baseline_requires_actual_delayed_stores_flushed_before_backup(self):
        value = self.receipt("baseline")
        value["persisted_storage_checked"] = False
        with self.assertRaises(controller.Refused):
            self.project("baseline", value)

    def test_rollback_preserves_bytes_without_claiming_published_guard_api(self):
        result = self.project("rollback")
        self.assertIs(result["guard"]["api_status_checked"], False)
        self.assertIs(result["guard"]["retained_bytes_checked"], True)

    def test_rollback_cannot_claim_unexercised_guard_api(self):
        value = self.receipt("rollback")
        value["guard"]["api_status_checked"] = True
        with self.assertRaises(controller.Refused):
            self.project("rollback", value)

    def test_upgraded_and_final_require_blocked_real_guard_api(self):
        for name in ("upgraded", "final"):
            for key, bad in (("api_status_checked", False), ("unresolved", 0), ("blocked", False)):
                value = self.receipt(name)
                value["guard"][key] = bad
                with self.subTest(name=name, key=key), self.assertRaises(controller.Refused):
                    self.project(name, value)

    def test_public_projection_excludes_private_nested_fields(self):
        value = self.receipt("upgraded")
        value["hacs"]["token"] = "PRIVATE-CANARY"
        value["snapshot"] = {"private": "PRIVATE-CANARY"}
        self.assertNotIn("PRIVATE-CANARY", json.dumps(self.project("upgraded", value)))
        self.assertNotIn(self.host.nonce, json.dumps(self.project("upgraded", value)))

    def test_phase_instructions_are_atomic_and_nonce_bound(self):
        self.host.guest_read = Mock(return_value=controller.canonical(self.receipt("bootstrap_hacs")))
        self.host.phase("bootstrap_hacs")
        path, content = self.host.guest_write.call_args.args
        self.assertNotEqual(Path(path).name, "phase.json")
        self.assertEqual(json.loads(content)["token"], self.host.nonce)
        self.assertIn("; mv ", self.host.guest.call_args.args[0])

    def test_stale_nonce_receipt_is_refused(self):
        value = self.receipt("bootstrap_hacs")
        value["token"] = "0" * 32
        self.host.guest_read = Mock(return_value=controller.canonical(value))
        with self.assertRaisesRegex(controller.Refused, "phase_receipt_identity_refused"):
            self.host.phase("bootstrap_hacs")

    def test_failed_static_probe_remains_failure_with_only_fixed_diagnostics(self):
        value = self.receipt("bootstrap_hacs")
        value.update(outcome="failed", stage="persistent_snapshot", failure_type="Refused",
            failure_code="qa_served_bundle", http_probe={"status": 307, "location_category": "other",
            "body": "PRIVATE-CANARY", "location": "https://PRIVATE-CANARY"})
        self.host.guest_read = Mock(return_value=controller.canonical(value))
        with self.assertRaisesRegex(controller.Refused, "guest_acceptance_failed"):
            self.host.phase("bootstrap_hacs")
        public = json.loads((self.host.public / "bootstrap_hacs.json").read_text())
        self.assertEqual(public["http_probe"], {"status": 307, "location_category": "other"})
        self.assertEqual(self.host.phases, [])
        self.assertNotIn("PRIVATE-CANARY", json.dumps(public))

    def complete(self):
        self.host.phases = [self.project(name) for name in controller.PHASES]
        for index, receipt in enumerate(self.host.phases):
            receipt["process"]["start_ticks"] = 100 + index

    def test_all_persistent_identities_and_newest_guard_survive_roundtrip(self):
        self.complete()
        self.host.verify_continuity()

    def test_download_without_real_restart_is_refused(self):
        self.complete()
        self.host.phases[3]["process"]["start_ticks"] = self.host.phases[2]["process"]["start_ticks"]
        with self.assertRaisesRegex(controller.Refused, "new_managed_core_process_required"):
            self.host.verify_continuity()

    def test_changed_identity_or_guard_is_refused(self):
        self.complete()
        self.host.phases[-1]["snapshot_sha256"] = "0" * 64
        with self.assertRaisesRegex(controller.Refused, "persistent_identity_continuity_refused"):
            self.host.verify_continuity()
        self.complete()
        self.host.phases[-1]["guard"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(controller.Refused, "newest_guard_continuity_refused"):
            self.host.verify_continuity()

    def test_failure_before_vm_launch_still_cleans_owned_private_workspace(self):
        private = self.host.public / "owned-private"
        private.mkdir()
        self.host.private = private
        self.host.cleanup_vm()
        self.assertFalse(private.exists())
        self.assertEqual(self.host.cleanup, {"qemu_stopped": True, "private_workspace_removed": True,
                                             "cleanup_failed": False})

    def test_core_stop_uses_one_request_then_actual_transition(self):
        self.host.management_ready = Mock(return_value=True)
        self.host.core_running = Mock(side_effect=[True, True, False])
        self.host.guest = Mock(return_value=b'{"result":"ok","data":{}}')
        with patch.object(controller.time, "sleep"):
            self.host.core_action("stop")
        self.assertEqual(self.host.guest.call_count, 1)
        self.assertIs(self.host.core_actions[-1]["running_after"], False)

    def test_core_api_error_is_not_retried_even_with_successful_cli_exit(self):
        self.host.management_ready = Mock(return_value=True)
        self.host.core_running = Mock(return_value=True)
        self.host.guest = Mock(return_value=b'{"result":"error","message":"PRIVATE-CANARY"}')
        with self.assertRaises(controller.Refused):
            self.host.core_action("stop")
        self.assertEqual(self.host.guest.call_count, 1)
        self.assertNotIn("PRIVATE-CANARY", json.dumps(self.host.core_actions))


if __name__ == "__main__":
    unittest.main()
