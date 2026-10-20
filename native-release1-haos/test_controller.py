"""Standalone controller contracts: no Home Assistant or native libraries imported."""

from __future__ import annotations

import base64
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

    def test_nested_backup_failure_diagnostics_exclude_raw_messages_and_unknown_types(self):
        self.job["child_jobs"] = [{"uuid": "b" * 32, "name": "backup_store_homeassistant", "done": True,
            "errors": [{"type": "HomeAssistantBackupError", "message":
                "Preparing backup of Home Assistant Core failed due to: Error during pre-backup: "
                "Could not lock database within 30 PRIVATE-CANARY"},
                {"type": "PRIVATE-CANARY", "message": "PRIVATE-CANARY"}], "child_jobs": []}]
        result = controller.public_backup_failure_jobs(self.value, self.identifier, self.job["name"])
        self.assertEqual(result[0]["binding"], "exact_operation")
        errors = result[0]["nodes"][1]["errors"]
        self.assertEqual(errors[0], {"type": "HomeAssistantBackupError", "categories": [
            "core_backup_start_rejected", "core_pre_backup_hook_failed", "recorder_lock_timeout"]})
        self.assertEqual(errors[1], {"type": "unclassified", "categories": []})
        self.assertNotIn("PRIVATE-CANARY", json.dumps(result))

    def test_recent_failure_jobs_are_labeled_without_an_exact_returned_id(self):
        result = controller.public_backup_failure_jobs(self.value, None, self.job["name"])
        self.assertEqual(result[0]["binding"], "recent_backup_job")

    def test_backup_failure_diagnostic_tree_is_bounded_without_silent_truncation(self):
        self.job["child_jobs"] = [{"uuid": "b" * 32, "done": True, "errors": []}] * 256
        with self.assertRaises(controller.Refused):
            controller.public_backup_failure_jobs(self.value, self.identifier, self.job["name"])

    def test_cli_and_condition_categories_never_copy_dynamic_arguments_or_reasons(self):
        for message, expected in (
            ('unknown command "PRIVATE-CANARY"', "cli_unexpected_positional_or_command"),
            ("accepts 1 arg(s), received 2 PRIVATE-CANARY", "cli_positional_count"),
            ("unexpected non-JSON response PRIVATE-CANARY", "cli_http_non_json"),
            ("Not enough free space PRIVATE-CANARY", "supervisor_free_space"),
        ):
            result = controller.backup_error_categories({"message": message})
            with self.subTest(expected=expected):
                self.assertEqual(result["categories"], [expected])
                self.assertNotIn("PRIVATE-CANARY", json.dumps(result))


class EnabledRestoreContracts(unittest.TestCase):
    def controller(self):
        value = controller.Controller(SimpleNamespace(branch_commit="c" * 40))
        value.inventories = {"candidate": {"__init__.py": {"bytes": 1, "sha256": "d" * 64}}}
        value.dependency_fixture = {"inventory_sha256": "6" * 64}
        return value

    def receipt(self, name, restored_count=2):
        seeded = name in {"mutate", "repair", "restart"}
        count = restored_count if name == "restored" else (3 if seeded else 2)
        guard = {"sha256": ("b" if count == 3 else "a") * 64,
                 "api_status_checked": True, "retained_bytes_checked": True,
                 "blocked": count == 3, "unresolved": count, "rejected": count, "pending": 0, "uncertain": 0}
        after = name in {"restored", "repair", "restart"}
        value = {"core_version": controller.CORE, "candidate_archive_sha256": controller.CANDIDATE_SHA,
                 "owner_accounts_used": False, "production_configuration_used": False,
                 "provider_accounts_configured": False, "entry_disabled": False, "entry_loaded": True,
                 "nonempty_options": True, "package_files_count": 113,
                 "prepared_dependencies": {"inventoried_non_bytecode_bytes_checked": True, "origins_config_deps": True,
                     "normal_bootstrap_library": True, "skip_pip": False, "inventory_sha256": "6" * 64,
                     "inventory_scope": "dependency_regular_files_excluding_generated_bytecode"},
                 "package_payload_sha256": controller.sha(controller.canonical(self.controller().inventories["candidate"])),
                 "loaded_source_sha256": "d" * 64, "runtime_config_sha256": "e" * 64,
                 "served_bundle_sha256": "f" * 64, "static_served_bundle_matches": True,
                 "owned_resource_id_sha256": "7" * 64,
                 "process": {"pid": 1, "start_ticks": 100 + controller.PHASES.index(name)},
                 "snapshot_sha256": ("2" if name == "mutate" else "1") * 64,
                 "persisted_storage_checked": True, "guard": guard,
                 "startup_guard_unchanged_after_load": True, "rollback_protection_passed": count == 3,
                 "PRIVATE-CANARY": "PRIVATE-CANARY",
                 "recorder": {"prebackup_rows": 10, "postbackup_marker_rows": 10 if name == "mutate" else 0,
                    "postrestore_rows": 10 if after else None, "prebackup_sha256": "4" * 64,
                    "postrestore_sha256": "5" * 64 if after else None, "prebackup_exact_match": True,
                    "postbackup_marker_absent": name != "mutate", "postrestore_exact_match": True if after else None,
                    "integrity_ok": True, "backup_platform_registered": True, "commit_proven": True,
                    "no_backup_failure_issue": True}}
        return value

    def through(self, value, name, restored_count=2):
        for phase in controller.PHASES[:controller.PHASES.index(name) + 1]:
            if phase == "restored":
                value.generation = "after_restore"
                value.automatic_boot = {"guard": self.receipt("restored", restored_count)["guard"]}
            item = value.accept_phase(phase, self.receipt(phase, restored_count))
            value.phases.append(item)
        return value.phases[-1]

    def test_ordinary_enabled_restore_can_work_while_rollback_safety_fails(self):
        item = self.through(self.controller(), "restored")
        self.assertTrue(item["operational_restore_passed"])
        self.assertFalse(item["automatic_guard_antirollback_passed"])
        self.assertEqual(item["guard"]["unresolved"], 2)

    def test_repair_needs_the_external_newest_guard_and_preserves_history(self):
        value = self.controller()
        self.through(value, "restored")
        for key, replacement in (("sha256", "a" * 64), ("unresolved", 2), ("blocked", False)):
            receipt = self.receipt("repair")
            receipt["guard"][key] = replacement
            with self.subTest(key=key), self.assertRaises(controller.Refused):
                value.accept_phase("repair", receipt)
        self.through(self.controller(), "restart")

    def test_enabled_or_nonempty_options_missing_is_refused(self):
        for key, value in (("entry_loaded", False), ("entry_disabled", True), ("nonempty_options", False)):
            receipt = self.receipt("initialize")
            receipt[key] = value
            with self.subTest(key=key), self.assertRaises(controller.Refused):
                self.controller().accept_phase("initialize", receipt)

    def test_prebackup_requires_real_persisted_storage(self):
        value = self.controller()
        self.through(value, "initialize")
        receipt = self.receipt("prebackup")
        receipt.pop("persisted_storage_checked")
        with self.assertRaisesRegex(controller.Refused, "prebackup_persisted_storage_required"):
            value.accept_phase("prebackup", receipt)

    def test_guard_counts_reject_booleans_and_inconsistent_blocked_state(self):
        for key, replacement in (("unresolved", True), ("pending", 1), ("uncertain", 1),
                                 ("rejected", 1), ("blocked", True), ("api_status_checked", False)):
            receipt = self.receipt("initialize")
            receipt["guard"][key] = replacement
            with self.subTest(key=key), self.assertRaises(controller.Refused):
                self.controller().accept_phase("initialize", receipt)

    def test_public_projection_drops_unknown_private_fields(self):
        item = self.through(self.controller(), "restart")
        self.assertNotIn("PRIVATE-CANARY", json.dumps(item))

    def test_restored_guard_must_match_actual_early_startup_and_archive_hash(self):
        value = self.controller()
        self.through(value, "mutate")
        value.generation = "after_restore"
        receipt = self.receipt("restored")
        value.automatic_boot = {"guard": dict(receipt["guard"])}
        for field, replacement in (("startup_guard_unchanged_after_load", False),
                                   ("rollback_protection_passed", True)):
            damaged = dict(receipt, **{field: replacement})
            with self.subTest(field=field), self.assertRaises(controller.Refused):
                value.accept_phase("restored", damaged)
        receipt["guard"] = dict(receipt["guard"], sha256="9" * 64)
        value.automatic_boot = {"guard": receipt["guard"]}
        with self.assertRaisesRegex(controller.Refused, "restored_guard_not_linked"):
            value.accept_phase("restored", receipt)

    def test_restart_must_preserve_owned_resource_and_exact_new_history(self):
        value = self.controller()
        self.through(value, "repair")
        for key, replacement in (("owned_resource_id_sha256", "8" * 64),):
            receipt = self.receipt("restart")
            receipt[key] = replacement
            with self.assertRaises(controller.Refused):
                value.accept_phase("restart", receipt)
        receipt = self.receipt("restart")
        receipt["recorder"]["postrestore_sha256"] = "9" * 64
        with self.assertRaisesRegex(controller.Refused, "postrestore_restart_history_changed"):
            value.accept_phase("restart", receipt)

    def test_stale_phase_receipt_cannot_count_as_progress(self):
        value = self.controller()
        value.config_path = "/mnt/data/supervisor/homeassistant"
        value.guest_write = Mock()
        value.guest = Mock()
        value.guest_read = Mock(return_value=controller.canonical({"schema": 1, "token": "old"}))
        with self.assertRaisesRegex(controller.Refused, "phase_receipt_identity_refused"):
            value.phase("initialize")
        self.assertFalse(value.phases)

    def test_live_generation_controls_are_atomic_and_ownership_nonce_is_preserved(self):
        value = self.controller()
        self.through(value, "mutate")
        value.config_path = "/mnt/data/supervisor/homeassistant"
        value.automatic_boot = {"guard": self.receipt("restored")["guard"]}
        value.inputs = {}
        value.external_proof = {}
        value.guest_write = Mock()
        value.guest = Mock()
        value.verify_candidate = Mock()
        nonce, token = value.nonce, value.phase_token
        value.fresh_restore_control()
        self.assertEqual(value.nonce, nonce)
        self.assertNotEqual(value.phase_token, token)
        target = value.guest_write.call_args.args[0]
        self.assertIn("/.inputs-", target)
        self.assertNotEqual(target, value.config_path + "/" + controller.CONTROL + "/inputs.json")
        commands = " ".join(call.args[0] for call in value.guest.call_args_list)
        self.assertIn("mv " + target, commands)
        self.assertIn("/inputs.json", commands)
        self.assertNotIn("rm -f", commands)

    def test_repair_cannot_happen_before_operational_observation(self):
        value = self.controller()
        value.guest = Mock()
        with self.assertRaisesRegex(controller.Refused, "restore_observation_before_repair_required"):
            value.repair_from_external_newest_guard()
        value.guest.assert_not_called()

    def test_automatic_enabled_boot_rejects_stale_receipts(self):
        value = self.controller()
        self.through(value, "mutate")
        value.config_path = "/mnt/data/supervisor/homeassistant"
        value.assert_network_closed = Mock()
        value.guest_read = Mock(return_value=controller.canonical({"schema": 1, "token": "stale"}))
        with self.assertRaisesRegex(controller.Refused, "restored_boot_identity_refused"):
            value.restored_boot_observation()

    def test_network_close_requires_positive_control_and_is_not_retried(self):
        value = self.controller()
        value.connectivity_probe = Mock(return_value=False)
        with patch.object(controller.socket, "socket") as constructor:
            with self.assertRaisesRegex(controller.Refused, "network_positive_control_refused"):
                value.disconnect_external_network()
            constructor.assert_not_called()
        self.assertFalse(value.network_boundary["link_closed"])

    def test_qmp_closes_explicit_nic_once_and_retains_qga_access(self):
        value = self.controller()
        value.qmp_path = Path("/private/qmp.sock")
        value.connectivity_probe = Mock(side_effect=[True, False])
        value.qga = Mock()
        stream = Mock()
        stream.readline.side_effect = [b'{"QMP":{}}\n', b'{"return":{},"id":"capabilities"}\n',
                                      b'{"return":{},"id":"close_network"}\n']
        connection = Mock()
        connection.makefile.return_value = stream
        with patch.object(controller.socket, "socket") as constructor:
            constructor.return_value.__enter__.return_value = connection
            value.disconnect_external_network()
        sent = [json.loads(call.args[0]) for call in stream.write.call_args_list]
        self.assertEqual(sent[-1], {"execute": "set_link", "arguments": {"name": "qa-net0", "up": False},
                                   "id": "close_network"})
        self.assertEqual(sum(item["execute"] == "set_link" for item in sent), 1)
        self.assertTrue(value.network_boundary["link_closed"])
        self.assertFalse(value.network_boundary["closed_probe_connected"])
        value.qga.call.assert_called_once_with("guest-ping")

    def test_false_network_closed_probe_refuses_restore_boundary(self):
        value = self.controller()
        value.network_boundary["link_closed"] = True
        value.connectivity_probe = Mock(return_value=True)
        with self.assertRaisesRegex(controller.Refused, "external_network_not_closed"):
            value.assert_network_closed()

    def test_confirmed_rollback_is_nonzero_even_after_successful_operations_and_cleanup(self):
        value = self.controller()
        self.through(value, "restart")
        value.acceptance = value.operational_restore_passed = value.manual_guard_repair_passed = True
        value.automatic_guard_antirollback_passed = False
        with tempfile.TemporaryDirectory() as directory:
            value.public = Path(directory)
            result = value.finish(None)
            receipt = json.loads((value.public / "host.json").read_bytes())
        self.assertEqual(result, 1)
        self.assertEqual(receipt["outcome"], "confirmed_safety_issue")
        self.assertTrue(receipt["diagnostic_completed"])
        self.assertFalse(receipt["ordinary_enabled_restore_safety_accepted"])
        self.assertTrue(receipt["operational_restore_passed"])
        self.assertTrue(receipt["manual_newest_guard_repair_passed"])
        self.assertFalse(receipt["provider_request_attempt_counts_measured"])
        self.assertFalse(receipt["recovery_proof_attempt_counts_measured"])

    def test_cleanup_or_unexpected_failure_never_becomes_known_safety_issue(self):
        value = self.controller()
        value.acceptance = True
        value.automatic_guard_antirollback_passed = False
        with tempfile.TemporaryDirectory() as directory:
            value.public = Path(directory)
            self.assertEqual(value.finish(controller.Refused("unexpected_failure")), 1)
            receipt = json.loads((value.public / "host.json").read_bytes())
        self.assertEqual(receipt["outcome"], "failed_or_incomplete")
        self.assertIsNone(receipt["confirmed_issue"])


class InheritedOneShotMutationContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.host = controller.Controller(SimpleNamespace(branch_commit="a" * 40))
        self.host.public = Path(self.temporary.name)
        self.host.config_path = "/mnt/data/supervisor/homeassistant"
        self.host.guest_write = Mock()
        self.host.guest = Mock(return_value=b"")

    def captured(self, value, exitcode=0, error=b""):
        return {"exitcode": exitcode, "signal": None, "stdout": controller.canonical(value),
                "stderr": error, "truncated": False}

    def test_supported_backup_cli_mutation_is_not_retried_after_api_error(self):
        self.host.management_ready = Mock(return_value=True)
        failure = {"result": "error", "message": "PRIVATE-CANARY", "job_id": "a" * 32}
        jobs = {"result": "ok", "data": {"jobs": [{"uuid": "a" * 32, "name": "backup_manager_partial_backup",
                "done": True, "errors": [{"type": "BackupFileExistError", "message": "PRIVATE-CANARY"}]}]}}
        self.host.guest = Mock(side_effect=[self.captured(failure, exitcode=1), controller.canonical(jobs)])
        with self.assertRaises(controller.Refused):
            self.host.backup_operation()
        commands = [call.args[0] for call in self.host.guest.call_args_list]
        self.assertEqual(sum(" backups new " in command for command in commands), 1)
        self.assertIn("--homeassistant-exclude-database=false", commands[0])
        self.assertIn("--location=.local", commands[0])
        self.assertNotIn("--location .local", commands[0])
        self.assertEqual(self.host.backup_requests[0]["exit_code"], 1)
        self.assertEqual(self.host.backup_requests[0]["result"], "error")
        self.assertEqual(self.host.backup_requests[0]["jobs"][0]["binding"], "exact_operation")
        self.assertNotIn("PRIVATE-CANARY", json.dumps(self.host.backup_requests))
        self.assertIsNone(self.host.backup)

    def test_successful_backup_accepts_a_normally_returning_void_core_validator(self):
        self.host.management_ready = Mock(return_value=True)
        self.host.managed_core = Mock(return_value=None)
        self.host.remaining = Mock(return_value=30)
        self.host.wait_backup_job = Mock(return_value={"done": True, "error_count": 0, "nodes": 1})
        self.host.guest = Mock(side_effect=[
            self.captured({"result": "ok", "data": {"job_id": "a" * 32, "slug": "abcd1234"}}),
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
        self.host.guest = Mock(side_effect=[self.captured({"result": "error"}, exitcode=1),
                                           b'{"result":"ok","data":{"jobs":[]}}'])
        with self.assertRaises(controller.Refused):
            self.host.backup_operation(restore=True)
        commands = [call.args[0] for call in self.host.guest.call_args_list]
        self.assertIn("--homeassistant=true", commands[0])
        self.assertIn("--location=.local", commands[0])
        self.assertNotIn("--location .local", commands[0])
        self.assertEqual(sum(" backups restore " in command for command in commands), 1)

    def test_nonzero_child_with_ok_json_remains_a_failed_request(self):
        self.host.management_ready = Mock(return_value=True)
        self.host.guest = Mock(side_effect=[self.captured({"result": "ok", "data": {}}, exitcode=2),
                                           b'{"result":"ok","data":{"jobs":[]}}'])
        with self.assertRaises(controller.Refused):
            self.host.backup_operation()
        self.assertEqual(self.host.backup_requests[0]["exit_code"], 2)
        self.assertEqual(self.host.backup_requests[0]["result"], "ok")
        self.assertIsNone(self.host.backup)

    def test_guest_capture_preserves_nonzero_exit_without_exporting_its_response(self):
        self.host.qga = Mock()
        self.host.qga.call.side_effect = [{"pid": 9}, {"exited": True, "exitcode": 7,
            "out-data": base64.b64encode(b'{"result":"error"}').decode(),
            "err-data": base64.b64encode(b"PRIVATE-CANARY").decode()}]
        result = controller.Controller.guest(self.host, "fixed-synthetic-command", capture=True)
        self.assertEqual(result["exitcode"], 7)
        self.assertEqual(json.loads(result["stdout"])["result"], "error")
        self.assertEqual(self.host.backup_requests, [])

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
