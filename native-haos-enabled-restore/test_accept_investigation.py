"""The diagnostic gate must never treat an incomplete or unsafe restore as a safety pass."""

from copy import deepcopy
import unittest

import accept_investigation as gate


def receipt():
    return {
        "schema": 1, "diagnostic_completed": True, "operational_restore_passed": True,
        "prepared_dependency_enabled_partial_restore": True, "ordinary_default_dependency_reinstallation_tested": False,
        "prepared_enabled_restore_safety_accepted": False,
        "prepared_dependency_fixture": {"outcome": "passed", "core": "2026.10.2", "closure_count": 24,
            "constraints_sha256": "7baa9a8f39ddeb9c5bb60a1036f6d5e33f4b84267f151f53cc2b95ef031a21b5",
            "inventory_scope": "dependency_regular_files_excluding_generated_bytecode",
            "inventory_sha256": "d" * 64, "inventory_files": 123},
        "backup": {"archive": {"prepared_dependency_sha256": "d" * 64, "prepared_dependency_files": 123}},
        "manual_newest_guard_repair_passed": True, "actual_kvm_confirmed": True,
        "qemu_stopped": True, "private_workspace_removed": True, "cleanup_failed": False,
        "enabled_entry_restore_tested": True, "automatic_guard_antirollback_tested": True,
        "provider_accounts_configured": False, "owner_credentials_used": False,
        "production_configuration_used": False, "guard_repair_before_first_enabled_boot": False,
        "phases": 6, "failure_type": None, "failure_code": None,
        "provenance": {"candidate_zip_sha256": gate.EXPECTED_ZIP},
        "network_boundary": {"before_probe_connected": True, "link_closed": True,
            "closed_probe_connected": False, "guest_agent_remained_available": True,
            "closed_probe_observations": 4},
        "automatic_guard_antirollback_passed": False,
        "ordinary_enabled_restore_safety_accepted": False, "outcome": "confirmed_safety_issue",
    }


class DiagnosticGate(unittest.TestCase):
    def test_completed_known_rollback_is_never_a_safety_acceptance(self):
        result = gate.evaluate(receipt(), 1)
        self.assertTrue(result["investigation_completed"])
        self.assertFalse(result["ordinary_enabled_restore_safety_accepted"])
        self.assertFalse(result["stable_release_approval"])
        self.assertIn("requires_release_disposition", result["interpretation"])

    def test_failed_cleanup_or_unfinished_repair_cannot_be_accepted_as_known_rollback(self):
        for field, value in (("cleanup_failed", True), ("private_workspace_removed", False),
                             ("manual_newest_guard_repair_passed", False), ("phases", 5),
                             ("failure_type", "TimeoutExpired"), ("failure_code", "unresolved_failure")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                body = receipt()
                body[field] = value
                gate.evaluate(body, 1)

    def test_no_crash_timeout_or_unexpected_success_is_accepted_for_a_safety_finding(self):
        for code in (-9, 0, 2, 124, True):
            with self.subTest(code=code), self.assertRaises(ValueError):
                gate.evaluate(receipt(), code)

    def test_egress_denial_must_have_both_controls_and_persisted_observations(self):
        for field, value in (("before_probe_connected", False), ("link_closed", False),
                             ("closed_probe_connected", True), ("guest_agent_remained_available", False),
                             ("closed_probe_observations", 1)):
            body = deepcopy(receipt())
            body["network_boundary"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                gate.evaluate(body, 1)

    def test_controller_cannot_relabel_an_observed_rollback_as_safe(self):
        body = receipt()
        body["ordinary_enabled_restore_safety_accepted"] = True
        with self.assertRaises(ValueError):
            gate.evaluate(body, 1)

    def test_prepared_dependency_fixture_and_archive_hash_are_mandatory(self):
        for mutate in (
            lambda body: body.update(prepared_dependency_enabled_partial_restore=False),
            lambda body: body.update(ordinary_default_dependency_reinstallation_tested=True),
            lambda body: body["prepared_dependency_fixture"].update(closure_count=23),
            lambda body: body["backup"]["archive"].update(prepared_dependency_sha256="a" * 64),
        ):
            body = deepcopy(receipt())
            mutate(body)
            with self.subTest(body=body), self.assertRaises(ValueError):
                gate.evaluate(body, 1)

    def test_actual_protection_requires_matching_result_and_exit_status(self):
        body = receipt()
        body.update(automatic_guard_antirollback_passed=True,
                    prepared_enabled_restore_safety_accepted=True, outcome="passed")
        result = gate.evaluate(body, 0)
        self.assertTrue(result["prepared_enabled_restore_safety_accepted"])
        self.assertFalse(result["ordinary_enabled_restore_safety_accepted"])
        self.assertFalse(result["stable_release_approval"])
        with self.assertRaises(ValueError):
            gate.evaluate(body, 1)


if __name__ == "__main__":
    unittest.main()
