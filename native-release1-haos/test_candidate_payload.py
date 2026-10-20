"""Bind the local unreleased preview to its exact source, inventory and gate pins."""

import ast
import hashlib
import json
from pathlib import Path
import unittest
import zipfile

import accept_investigation as gate
import controller
import prepare_dependencies

ROOT = Path(__file__).resolve().parent


class CandidatePayload(unittest.TestCase):
    def test_local_payload_matches_exact_sha_and_all_member_bytes(self):
        raw = (ROOT / "payload/homecircle.zip").read_bytes()
        self.assertEqual(len(raw), 614209)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), gate.EXPECTED_ZIP)
        inventory = json.loads((ROOT / "payload/inventory.json").read_bytes())
        self.assertEqual(inventory["archive_sha256"], gate.EXPECTED_ZIP)
        actual = controller.check_archive(ROOT / "payload/homecircle.zip", gate.EXPECTED_ZIP, 113)
        self.assertEqual(actual, inventory["files"])

    def test_manifest_version_and_dependency_requirements_are_unchanged(self):
        with zipfile.ZipFile(ROOT / "payload/homecircle.zip") as archive:
            manifest = json.loads(archive.read("manifest.json"))
        self.assertEqual(manifest["version"], "0.1.0-beta.20")
        self.assertEqual(manifest["requirements"], controller.REQUIREMENTS)
        self.assertEqual(manifest["requirements"], list(prepare_dependencies.REQUIREMENTS))

    def test_exact_preview_provenance_is_consistent_with_gate(self):
        value = json.loads((ROOT / "payload/provenance.json").read_bytes())
        self.assertEqual(value["schema"], 1)
        self.assertEqual(value["candidate_zip_sha256"], gate.EXPECTED_ZIP)
        self.assertEqual(value["candidate_source_commit"], gate.EXPECTED_SOURCE)
        self.assertEqual(value["candidate_files"], gate.EXPECTED_FILES)
        self.assertEqual(value["candidate_version"], gate.EXPECTED_VERSION)
        self.assertEqual(value["candidate_zip_bytes"], 614209)
        self.assertEqual(value["candidate_package_validation_run"], 39490732759)
        self.assertEqual(value["candidate_input_kind"], "pinned_local_unreleased_preview_zip")
        self.assertIs(value["same_version_unreleased_development_preview"], True)
        self.assertIs(value["release_published"], False)
        self.assertIs(value["source_match_independently_verified"], True)

    def test_guest_candidate_pin_is_equal_without_importing_home_assistant(self):
        tree = ast.parse((ROOT / "guest_helper/homecircle_enabled_restore_qa/__init__.py").read_bytes())
        pins = [node.value.value for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "CANDIDATE" for target in node.targets)]
        self.assertEqual(pins, [controller.CANDIDATE_SHA])
        self.assertEqual(controller.CANDIDATE_SHA, gate.EXPECTED_ZIP)


if __name__ == "__main__":
    unittest.main()
