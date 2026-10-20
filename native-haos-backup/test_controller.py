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

import controller


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


class BackupContracts(unittest.TestCase):
    def setUp(self):
        self.identifier = "a" * 32
        self.job = {"uuid": self.identifier, "name": "backup_manager_partial_backup", "done": True,
                    "errors": [], "child_jobs": []}
        self.value = {"result": "ok", "data": {"jobs": [self.job]}}

    def test_matching_completed_job_excludes_error_messages(self):
        self.job["private"] = "PRIVATE-CANARY"
        self.assertEqual(controller.exact_job(self.value, self.identifier, self.job["name"]), {
            "name": self.job["name"], "done": True, "error_count": 0, "nodes": 1})

    def test_nested_error_is_not_hidden_by_successful_parent(self):
        self.job["child_jobs"] = [{"uuid": "b" * 32, "name": "backup_store_homeassistant", "done": True,
                                   "errors": [{"message": "PRIVATE-CANARY"}], "child_jobs": []}]
        result = controller.exact_job(self.value, self.identifier, self.job["name"])
        self.assertEqual(result["error_count"], 1)
        self.assertNotIn("PRIVATE-CANARY", json.dumps(result))

    def test_legacy_error_field_and_unstarted_child_are_observed(self):
        self.job["child_jobs"] = [{"uuid": "b" * 32, "done": None, "errors": [], "error": {"secret": "PRIVATE-CANARY"}}]
        result = controller.exact_job(self.value, self.identifier, self.job["name"])
        self.assertFalse(result["done"])
        self.assertEqual(result["error_count"], 1)

    def test_other_completed_backup_cannot_replace_exact_operation(self):
        with self.assertRaises(controller.Refused):
            controller.exact_job(self.value, "b" * 32, self.job["name"])

    def test_duplicate_job_id_is_refused(self):
        self.value["data"]["jobs"].append(dict(self.job))
        with self.assertRaises(controller.Refused):
            controller.exact_job(self.value, self.identifier, self.job["name"])

    def test_database_exclusion_or_full_scope_is_refused(self):
        info = {"result": "ok", "data": {"slug": "abcd1234", "type": "partial", "homeassistant": controller.CORE,
                "homeassistant_exclude_database": False, "protected": False, "compressed": False}}
        self.assertTrue(controller.backup_info(info, "abcd1234")["database_included"])
        for key, invalid in (("type", "full"), ("homeassistant_exclude_database", True), ("homeassistant", "landingpage")):
            changed = {"result": "ok", "data": {**info["data"], key: invalid}}
            with self.subTest(key=key), self.assertRaises(controller.Refused):
                controller.backup_info(changed, "abcd1234")


class PhaseContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.host = controller.Controller(SimpleNamespace(branch_commit="a" * 40))
        self.host.public = Path(self.temporary.name)
        self.host.config_path = "/mnt/data/supervisor/homeassistant"
        self.host.guest_write = Mock()
        self.host.guest = Mock(return_value=b"")
        self.inventory = {"__init__.py": {"bytes": 7, "sha256": controller.sha(b"example")}}
        self.host.inventories = {"candidate": self.inventory}
        self.receipt = {
            "schema": 1, "token": self.host.phase_token, "generation": self.host.generation,
            "branch_commit": "a" * 40, "core_version": controller.CORE,
            "candidate_archive_sha256": controller.CANDIDATE_SHA,
            "phase": "initialize", "outcome": "passed", "owner_accounts_used": False,
            "production_configuration_used": False, "apple_or_provider_requests": 0,
            "package_files_count": 112, "package_payload_sha256": controller.sha(controller.canonical(self.inventory)),
            "loaded_source_sha256": self.inventory["__init__.py"]["sha256"],
            "snapshot_sha256": "b" * 64, "quarantine_snapshot_sha256": None,
            "owned_resource_id_sha256": "1" * 64,
            "process": {"pid": 123, "start_ticks": 456}, "entry_disabled": False, "entry_loaded": True,
            "guard": {"sha256": "c" * 64, "blocked": False, "unresolved": 0, "rejected": 0, "api_status_checked": True},
            "recorder": {"prebackup_rows": 12, "prebackup_sha256": "d" * 64, "prebackup_exact_match": True,
                         "postbackup_marker_rows": 0, "postbackup_marker_absent": True, "postrestore_rows": None,
                         "postrestore_sha256": None, "postrestore_exact_match": None, "integrity_ok": True,
                         "backup_platform_registered": True, "commit_proven": True, "no_backup_failure_issue": True},
        }

    def read(self):
        self.host.guest_read = Mock(return_value=controller.canonical(self.receipt))

    def initialize(self):
        self.host.phases.append(self.host.accept_phase("initialize", self.receipt))

    def test_phase_atomicity_and_secret_projection_remain_narrow(self):
        self.receipt["private"] = self.receipt["guard"]["private"] = "PRIVATE-CANARY"
        self.read()
        self.host.phase("initialize")
        self.assertNotEqual(Path(self.host.guest_write.call_args.args[0]).name, "phase.json")
        self.assertIn("; mv ", self.host.guest.call_args.args[0])
        public = (self.host.public / "initialize.json").read_text()
        self.assertNotIn("PRIVATE-CANARY", public)
        self.assertNotIn(self.host.phase_token, public)

    def test_stale_backup_generation_or_nonce_cannot_count_as_progress(self):
        for key in ("generation", "token"):
            with self.subTest(key=key):
                original = self.receipt[key]
                self.receipt[key] = "stale"
                self.read()
                with self.assertRaises(controller.Refused):
                    self.host.phase("initialize")
                self.receipt[key] = original
        self.assertEqual(self.host.phases, [])

    def test_disabled_phase_cannot_report_loaded_homecircle(self):
        self.initialize()
        self.receipt.update(phase="quarantine", quarantine_snapshot_sha256="e" * 64)
        with self.assertRaises(controller.Refused):
            self.host.accept_phase("quarantine", self.receipt)

    def test_missing_disabled_boolean_cannot_satisfy_quarantine(self):
        self.initialize()
        self.receipt.update(entry_disabled=None, entry_loaded=False, quarantine_snapshot_sha256="e" * 64)
        with self.assertRaises(controller.Refused):
            self.host.accept_phase("quarantine", self.receipt)

    def test_recorder_hook_and_committed_history_are_required(self):
        for key in ("backup_platform_registered", "commit_proven", "integrity_ok"):
            original = self.receipt["recorder"][key]
            self.receipt["recorder"][key] = False
            with self.subTest(key=key), self.assertRaises(controller.Refused):
                self.host.accept_phase("initialize", self.receipt)
            self.receipt["recorder"][key] = original

    def test_candidate_inventory_is_required_even_with_passing_helper(self):
        self.receipt["package_payload_sha256"] = "0" * 64
        with self.assertRaises(controller.Refused):
            self.host.accept_phase("initialize", self.receipt)

    def test_postrestore_guard_cannot_use_backed_up_zero_counter(self):
        self.initialize()
        self.host.latest_guard_sha256 = "f" * 64
        self.receipt.update(entry_disabled=False, entry_loaded=True)
        self.receipt["owned_resource_id_sha256"] = "2" * 64
        self.receipt["recorder"].update(postrestore_rows=4, postrestore_sha256="e" * 64, postrestore_exact_match=True)
        with self.assertRaises(controller.Refused):
            self.host.accept_phase("final", self.receipt)

    def test_restarted_recorder_rows_must_equal_postrestore_committed_rows(self):
        self.initialize()
        self.host.latest_guard_sha256 = "f" * 64
        self.receipt["owned_resource_id_sha256"] = "2" * 64
        self.receipt["guard"].update(sha256="f" * 64, unresolved=3, rejected=3, blocked=True)
        self.receipt["recorder"].update(postrestore_rows=4, postrestore_sha256="e" * 64, postrestore_exact_match=True)
        self.host.phases.append(self.host.accept_phase("final", self.receipt))
        self.receipt["recorder"]["postrestore_sha256"] = "9" * 64
        with self.assertRaises(controller.Refused):
            self.host.accept_phase("restart", self.receipt)

    def test_recreated_owned_resource_id_must_survive_restart(self):
        self.initialize()
        self.host.latest_guard_sha256 = "f" * 64
        self.receipt["owned_resource_id_sha256"] = "2" * 64
        self.receipt["guard"].update(sha256="f" * 64, unresolved=3, rejected=3, blocked=True)
        self.receipt["recorder"].update(postrestore_rows=4, postrestore_sha256="e" * 64, postrestore_exact_match=True)
        self.host.phases.append(self.host.accept_phase("final", self.receipt))
        self.receipt["owned_resource_id_sha256"] = "3" * 64
        with self.assertRaisesRegex(controller.Refused, "^recreated_resource_restart_identity_changed$"):
            self.host.accept_phase("restart", self.receipt)

    def test_supported_backup_cli_mutation_is_not_retried_after_api_error(self):
        self.host.management_ready = Mock(return_value=True)
        self.host.guest = Mock(return_value=b'{"result":"error","message":"PRIVATE-CANARY"}')
        with self.assertRaises(controller.Refused):
            self.host.backup_operation()
        self.assertEqual(self.host.guest.call_count, 1)
        self.assertIn("--homeassistant-exclude-database=false", self.host.guest.call_args.args[0])
        self.assertIsNone(self.host.backup)

    def test_successful_backup_accepts_a_normally_returning_void_core_validator(self):
        self.host.management_ready = Mock(return_value=True)
        self.host.managed_core = Mock(return_value=None)
        self.host.remaining = Mock(return_value=30)
        self.host.wait_backup_job = Mock(return_value={"done": True, "error_count": 0, "nodes": 1})
        self.host.guest = Mock(side_effect=[
            b'{"result":"ok","data":{"job_id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","slug":"abcd1234"}}',
            controller.canonical({"result": "ok", "data": {"slug": "abcd1234", "type": "partial",
                "homeassistant": controller.CORE, "homeassistant_exclude_database": False,
                "protected": False, "compressed": False}}),
        ])
        # The next tick would exhaust the operation if a void validator were
        # incorrectly used as a false readiness predicate.
        with patch.object(controller.time, "monotonic", side_effect=[0] * 5 + [31]):
            self.host.backup_operation()
        self.host.managed_core.assert_called_once_with()
        self.assertEqual(self.host.guest.call_count, 2)
        self.assertTrue(self.host.backup["database_included"])

    def test_explicit_homeassistant_flag_selects_partial_restore(self):
        self.host.backup = {"slug": "abcd1234"}
        self.host.management_ready = Mock(return_value=True)
        self.host.guest = Mock(return_value=b'{"result":"error"}')
        with self.assertRaises(controller.Refused):
            self.host.backup_operation(restore=True)
        self.assertIn("--homeassistant=true", self.host.guest.call_args.args[0])
        self.assertEqual(self.host.guest.call_count, 1)

    def test_restored_automatic_boot_must_be_disabled_without_candidate_import(self):
        self.initialize()
        self.host.restore = {}
        barrier = {"schema": 1, "token": self.host.phase_token, "generation": "before_restore",
                   "branch_commit": "a" * 40, "entry_disabled": True, "entry_loaded": False,
                   "candidate_imported": False, "process": {"pid": 123, "start_ticks": 999}}
        self.host.guest_read = Mock(return_value=controller.canonical(barrier))
        self.host.restored_boot_barrier()
        self.assertFalse(self.host.restore["automatic_boot_barrier"]["candidate_imported"])
        barrier["candidate_imported"] = True
        self.host.guest_read = Mock(return_value=controller.canonical(barrier))
        with self.assertRaises(controller.Refused):
            self.host.restored_boot_barrier()

    def test_restored_guard_must_match_old_archive_before_new_guard_promotion(self):
        self.initialize()
        self.host.phases.append({"quarantine_snapshot_sha256": "e" * 64})
        self.host.backup_guard_sha256 = "c" * 64
        self.host.latest_guard_sha256 = "f" * 64
        self.host.stop_core = Mock()
        self.host.guest_read = Mock(return_value=b'{"data":{"entries":[{"domain":"homecircle","disabled_by":"user"}]}}')
        self.host.guard_fingerprint = Mock(return_value="9" * 64)
        with self.assertRaises(controller.Refused):
            self.host.fresh_restore_control()
        self.host.guest.assert_not_called()

    def test_fresh_phase_token_rotation_preserves_vm_ownership_nonce(self):
        self.initialize()
        self.host.phases.append({"quarantine_snapshot_sha256": "e" * 64})
        self.host.backup_guard_sha256 = "c" * 64
        self.host.latest_guard_sha256 = "f" * 64
        self.host.restore = {}
        self.host.inputs = {}
        self.host.external_proof = {"private": "synthetic-window"}
        self.host.stop_core = Mock()
        self.host.verify_candidate = Mock()
        self.host.guest_read = Mock(return_value=b'{"data":{"entries":[{"domain":"homecircle","disabled_by":"user"}]}}')
        self.host.guard_fingerprint = Mock(side_effect=["c" * 64, "f" * 64, "f" * 64])
        vm_nonce, phase_token = self.host.nonce, self.host.phase_token
        self.host.fresh_restore_control()
        self.assertEqual(self.host.nonce, vm_nonce)
        self.assertNotEqual(self.host.phase_token, phase_token)
        self.assertEqual(self.host.generation, "after_restore")
        self.assertEqual(self.host.inputs["latest_guard_sha256"], "f" * 64)
        self.assertTrue(self.host.restore["restored_old_guard_verified_before_promotion"])

    def test_core_stop_uses_one_request_then_observes_actual_transition(self):
        self.host.management_ready = Mock(return_value=True)
        self.host.core_running = Mock(side_effect=[True, True, False])
        self.host.guest = Mock(return_value=b'{"result":"ok","data":{}}')
        with patch.object(controller.time, "sleep"):
            self.host.core_action("stop")
        self.assertEqual(self.host.guest.call_count, 1)
        self.assertIs(self.host.core_actions[-1]["running_after"], False)

    def test_cleanup_before_vm_launch_removes_owned_private_workspace(self):
        private = self.host.public / "owned-private"
        private.mkdir()
        self.host.private = private
        self.host.cleanup_vm()
        self.assertFalse(private.exists())
        self.assertFalse(self.host.cleanup["cleanup_failed"])


if __name__ == "__main__":
    unittest.main()


