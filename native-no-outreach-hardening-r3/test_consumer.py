"""Independent consumer mutation contracts; synthetic receipts only."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("affected_consumer_contract", HERE / "verify_results.py")
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)


class Contracts(unittest.TestCase):
    def fixture(self):
        config = {"schema": 1, "frozen": True, "source_commit": "a" * 40, "source_files": 402,
            "source_sha256": "b" * 64, "source_inventory_sha256": "c" * 64,
            "source_export_sha256": "d" * 64, "driver_sha256": "e" * 64,
            "package_sha256": "f" * 64, "package_inventory_sha256": "0" * 64,
            "version": "1.0.0-rc.1", "release_files": 112, "selected_modules": ["tests/test_controls.py"],
            "expected_functions": [{"class": "tests.test_controls", "function": "test_pause"}]}
        graph = json.loads((HERE / "CORE-GRAPH.json").read_bytes())
        common = C.common(config)
        runtime = {"homeassistant": "2026.10.2", "pytest-homeassistant-custom-component": "0.13.373",
            "life360": "7.2.0", "anisette": "1.2.4", "unicorn": "2.1.4", "srp": "1.0.22",
            "beautifulsoup4": "4.13.3", "cryptography": "50.0.1", "protobuf": "6.33.0"}
        startup = {raw.split("==")[0].lower().replace("_", "-"): raw.split("==")[1] for raw in graph["requirements"]}
        setup = {**common, "outcome": "passed", "completed": True, "python": "3.14.6", "machine": "x86_64",
            "constraints_sha256": C.CONSTRAINTS, "pytest_homeassistant_custom_component": "0.13.373",
            "core_requirement_graph": graph, "startup_requirement_versions": startup,
            "runtime_versions": runtime, "source_unchanged": True}
        candidate = {**common, "outcome": "passed", "completed": True, "passed": 2, "failed": 0, "skipped": 0,
            "collected_cases_match_junit": True, "selected_base_functions": [{**config["expected_functions"][0], "variants_passed": 2}],
            "selected_base_function_count": 1, "selected_modules": config["selected_modules"], "runtime_versions": runtime,
            "core_requirement_graph": graph, "startup_requirement_versions": startup, "source_unchanged": True}
        diagnostic = {"schema": 1, "scope": "unaccepted_focused_pytest_diagnostics", "acceptance_qualified": False,
            "pytest_exit": 0, "junit_available": True, "junit_parsed": True,
            "cases": [{**config["expected_functions"][0], "failed": False, "skipped": False, "failure_locations": []} for _ in range(2)],
            "observed_cases": 2, "failed_cases": 0, "skipped_cases": 0, "unmapped_case_count": 0, "error_nodes": 0, "failure_nodes": 0}
        host = {"schema": 1, "scope": C.SCOPE, "outcome": "passed", "runner_exit": 0, "failure_or_final_stage": "complete",
            "source_commit": config["source_commit"], "config_sha256": "1" * 64, "image_digest": C.IMAGE_DIGEST,
            "expected_image_id": C.IMAGE_ID, "host_elapsed_seconds": 100.0, "host_system": "Linux", "host_architecture": "x86_64",
            "core": "2026.10.2", "source_git_verified": True, "backend_network_disconnected": True, "container_stopped": True,
            "container_removed": True, "cleanup_failed": False, "private_workspace_removed": True,
            "full_backend_suite_repeated": False, "full_managed_core_lifecycle": False, "upgrade_validated": False,
            "kvm_used": False, "owner_accounts_used": False, "production_configuration_used": False, "release_published": False}
        receipts = {"source-summary.json": {**common, "outcome": "passed", "source_git_verified": True,
            "complete_canonical_tree_verified": True}, "setup-summary.json": setup, "candidate-summary.json": candidate,
            "focused-diagnostic.json": diagnostic, "host.json": host}
        return config, receipts, graph

    def test_success_is_narrow_and_does_not_claim_transport(self):
        config, receipts, graph = self.fixture()
        result = C.verify(config, "1" * 64, receipts, graph)
        self.assertEqual(result["passed"], 2)
        self.assertFalse(result["artifact_transport_verified_by_consumer"])
        self.assertFalse(result["upgrade_validated"])

    def test_frozen_config_and_extra_receipt_rejected(self):
        config, receipts, _ = self.fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "config.json"
            config["frozen"] = False
            path.write_text(json.dumps(config))
            with self.assertRaisesRegex(C.Refused, "frozen_config_required"):
                C.config_read(path, C.sha(path.read_bytes()))
            config["frozen"] = True
            path.write_text(json.dumps(config))
            results = root / "results"
            results.mkdir()
            for name, value in receipts.items():
                (results / name).write_text(json.dumps(value))
            (results / "private.log").write_text("PRIVATE_CANARY")
            with self.assertRaisesRegex(C.Refused, "exact_public_receipt_set_required"):
                C.consume(path, C.sha(path.read_bytes()), results)

    def test_hash_scope_runtime_graph_success_and_cleanup_mutations_refused(self):
        changes = [
            ("source-summary.json", "source_export_sha256", "0" * 64),
            ("source-summary.json", "complete_canonical_tree_verified", False),
            ("setup-summary.json", "python", "3.13.0"),
            ("setup-summary.json", "constraints_sha256", "0" * 64),
            ("candidate-summary.json", "outcome", "failed"),
            ("candidate-summary.json", "failed", 1),
            ("candidate-summary.json", "skipped", 1),
            ("candidate-summary.json", "collected_cases_match_junit", False),
            ("candidate-summary.json", "source_unchanged", False),
            ("candidate-summary.json", "full_backend_suite_repeated", True),
            ("candidate-summary.json", "passed", 1),
            ("candidate-summary.json", "passed", True),
            ("host.json", "image_digest", "sha256:" + "0" * 64),
            ("host.json", "backend_network_disconnected", False),
            ("host.json", "container_stopped", False),
            ("host.json", "container_removed", False),
            ("host.json", "private_workspace_removed", False),
            ("host.json", "cleanup_failed", True),
            ("host.json", "config_sha256", "0" * 64),
        ]
        for filename, key, value in changes:
            with self.subTest(filename=filename, key=key):
                config, receipts, graph = self.fixture()
                receipts[filename][key] = value
                with self.assertRaises(C.Refused):
                    C.verify(config, "1" * 64, receipts, graph)

    def test_missing_extra_reordered_functions_and_variant_changes_refused(self):
        for change in (lambda x: x.pop(), lambda x: x.append(copy.deepcopy(x[0])),
                       lambda x: x[0].update(function="test_unselected"),
                       lambda x: x[0].update(variants_passed=0),
                       lambda x: x[0].update(variants_passed=True)):
            config, receipts, graph = self.fixture()
            change(receipts["candidate-summary.json"]["selected_base_functions"])
            with self.assertRaises(C.Refused):
                C.verify(config, "1" * 64, receipts, graph)

    def test_default_auth_and_actual_runtime_drift_refused(self):
        for key in ("core_requirement_graph", "runtime_versions", "startup_requirement_versions"):
            config, receipts, graph = self.fixture()
            receipts["setup-summary.json"][key] = copy.deepcopy(receipts["setup-summary.json"][key])
            receipts["setup-summary.json"][key].pop(next(iter(receipts["setup-summary.json"][key])))
            with self.assertRaises(C.Refused):
                C.verify(config, "1" * 64, receipts, graph)

    def test_diagnostic_counts_and_privacy_shape_refused(self):
        for key, value in (("observed_cases", 1), ("failure_nodes", 1), ("pytest_exit", 1), ("raw_response", "PRIVATE_CANARY")):
            config, receipts, graph = self.fixture()
            receipts["focused-diagnostic.json"][key] = value
            with self.assertRaises(C.Refused):
                C.verify(config, "1" * 64, receipts, graph)


if __name__ == "__main__":
    unittest.main()
