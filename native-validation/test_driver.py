"""Host-only refusal contracts; no HA, pytest or provider imports."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("focused_driver_contract", HERE / "driver.py")
DRIVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DRIVER)


class FocusedContracts(unittest.TestCase):
    def receipt(self, path, change=None):
        root = ET.Element("testsuites")
        suite = ET.SubElement(root, "testsuite")
        for name in sorted(DRIVER.REQUIRED):
            ET.SubElement(suite, "testcase", classname="tests.test_activity_projection", name=name)
        for index in range(28):
            ET.SubElement(suite, "testcase", classname="tests.test_activity", name=f"test_existing_{index}")
        if change is not None:
            change(suite)
        ET.ElementTree(root).write(path)

    def test_pending_config_never_opens_payload(self):
        with self.assertRaisesRegex(DRIVER.Refused, "final_config_pin_required"):
            DRIVER.configuration(HERE / "payload", "PENDING")

    def test_only_focused_scope_claims_are_issued(self):
        value = DRIVER.common({"source_commit": "a" * 40, "source_sha256": "b" * 64,
                               "package_sha256": "c" * 64})
        self.assertFalse(value["upgrade_validated"])
        self.assertFalse(value["kvm_used"])
        self.assertFalse(value["full_backend_suite_repeated"])

    def test_all_required_cases_are_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "junit.xml"
            self.receipt(path)
            cases, required = DRIVER.focused_result(path)
            self.assertEqual(len(cases), 32)
            self.assertEqual(required, DRIVER.REQUIRED)

    def test_setup_test_cannot_be_omitted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "junit.xml"
            self.receipt(path, lambda suite: suite.remove(next(child for child in suite
                if child.attrib["name"].startswith("test_setup_"))))
            with self.assertRaisesRegex(DRIVER.Refused, "focused_required_cases_missing"):
                DRIVER.focused_result(path)

    def test_duplicate_case_never_inflates_count(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "junit.xml"
            self.receipt(path, lambda suite: ET.SubElement(suite, "testcase",
                classname="tests.test_activity", name="test_existing_0"))
            with self.assertRaisesRegex(DRIVER.Refused, "focused_case_identity_refused"):
                DRIVER.focused_result(path)

    def test_failure_error_skip_and_collection_error_are_refused(self):
        for tag in ("failure", "error", "skipped"):
            with self.subTest(tag=tag), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "junit.xml"
                self.receipt(path, lambda suite: ET.SubElement(suite[0], tag))
                with self.assertRaisesRegex(DRIVER.Refused, "focused_failure_or_skip_refused"):
                    DRIVER.focused_result(path)
                root = ET.parse(path).getroot()
                next(root.iter(tag)).text = "private_exception_text_must_never_escape"
                ET.ElementTree(root).write(path)
                diagnostic = DRIVER.focused_diagnostic(path, 1)
                self.assertTrue(diagnostic["junit_parsed"])
                self.assertEqual(diagnostic["observed_cases"], 32)
                self.assertEqual(diagnostic["failed_cases"], int(tag != "skipped"))
                self.assertEqual(diagnostic["skipped_cases"], int(tag == "skipped"))
                self.assertNotIn("private_exception_text", json.dumps(diagnostic))

    def test_unrelated_module_cannot_supply_extra_cases(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "junit.xml"
            self.receipt(path, lambda suite: ET.SubElement(suite, "testcase",
                classname="tests.test_unrelated", name="test_extra"))
            with self.assertRaisesRegex(DRIVER.Refused, "focused_case_identity_refused"):
                DRIVER.focused_result(path)


if __name__ == "__main__":
    unittest.main()
