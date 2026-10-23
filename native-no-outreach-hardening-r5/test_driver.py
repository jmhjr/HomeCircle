"""Standard-library contracts only; no pytest, Home Assistant, native or network imports."""

import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("affected_driver_contract", HERE / "driver.py")
D = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D)
SPEC_P = importlib.util.spec_from_file_location("affected_prepare_contract", HERE / "prepare_inputs.py")
P = importlib.util.module_from_spec(SPEC_P)
SPEC_P.loader.exec_module(P)


class Contracts(unittest.TestCase):
    def control(self):
        return {"schema": 1, "frozen": True, "source_commit": "a" * 40, "source_files": 300,
                "source_sha256": "b" * 64, "source_inventory_sha256": "c" * 64,
                "source_export_sha256": "d" * 64, "driver_sha256": D.sha(D.read(HERE / "driver.py")),
                "package_sha256": "e" * 64, "package_inventory_sha256": "f" * 64,
                "version": "1.0.0-rc.1", "release_files": 112,
                "selected_modules": ["tests/test_controls.py"],
                "expected_functions": [{"class": "tests.test_controls", "function": "test_pause"},
                                       {"class": "tests.test_controls", "function": "test_resume"}]}

    def xml_collection(self, path, change_xml=None, change_collection=None):
        nodes = [{"class": "tests.test_controls", "name": "test_pause[first]"},
                 {"class": "tests.test_controls", "name": "test_pause[second]"},
                 {"class": "tests.test_controls", "name": "test_resume"}]
        root = ET.Element("testsuites")
        suite = ET.SubElement(root, "testsuite")
        for item in nodes:
            ET.SubElement(suite, "testcase", classname=item["class"], name=item["name"])
        if change_xml:
            change_xml(suite)
        xml = path / "junit.xml"
        ET.ElementTree(root).write(xml)
        collection = {"schema": 1, "cases": nodes, "deselected": 0}
        if change_collection:
            change_collection(collection)
        collected = path / "collection.json"
        collected.write_text(json.dumps(collection))
        return xml, collected

    def test_pending_hash_refused_before_payload_read(self):
        with self.assertRaisesRegex(D.Refused, "final_config_pin_required"):
            D.configuration(HERE / "absent-payload", "PENDING")

    def test_unfrozen_control_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            raw = P.encoded({**self.control(), "frozen": False})
            (path / "config.json").write_bytes(raw)
            with self.assertRaisesRegex(D.Refused, "frozen_control_required"):
                D.configuration(path, D.sha(raw))

    def test_valid_final_control_has_exact_source_and_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            raw = P.encoded(self.control())
            (path / "config.json").write_bytes(raw)
            self.assertEqual(D.configuration(path, D.sha(raw)), self.control())

    def test_duplicate_json_key_refused(self):
        with self.assertRaisesRegex(D.Refused, "duplicate_json_key_refused"):
            json.loads('{"schema":1,"schema":1}', object_pairs_hook=D.unique)

    def test_scope_does_not_claim_full_suite_hacs_or_upgrade(self):
        value = D.common(self.control())
        for key in ["full_backend_suite_repeated", "full_managed_core_lifecycle", "hacs_delivery_tested",
                    "upgrade_validated", "owner_accounts_used", "production_configuration_used", "kvm_used"]:
            self.assertIs(value[key], False)

    def test_static_functions_include_async_and_testcase_but_not_nested_helpers(self):
        raw = b"async def test_pause():\n pass\ndef helper():\n def test_hidden(): pass\nclass Other:\n def test_hidden(self): pass\nclass Checks(unittest.TestCase):\n def test_save(self): pass\n"
        self.assertEqual(D.expected_functions({"tests/test_controls.py": raw}, ["tests/test_controls.py"]),
            [{"class": "tests.test_controls", "function": "test_pause"},
             {"class": "tests.test_controls.Checks", "function": "test_save"}])

    def test_all_collected_variants_must_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            xml, collected = self.xml_collection(Path(directory))
            cases, functions = D.focused_result(xml, collected, self.control())
            self.assertEqual(len(cases), 3)
            self.assertEqual([x["variants_passed"] for x in functions], [2, 1])

    def test_long_private_parameter_identity_still_matches_exactly(self):
        name = "test_pause[" + "x" * 65537 + "-suffix]"
        with tempfile.TemporaryDirectory() as directory:
            xml, collected = self.xml_collection(Path(directory),
                lambda suite: suite[0].set("name", name),
                lambda value: value["cases"][0].update(name=name))
            cases, functions = D.focused_result(xml, collected, self.control())
            self.assertEqual(len(cases), 3)
            self.assertEqual([x["variants_passed"] for x in functions], [2, 1])
            public = json.dumps(D.focused_diagnostic(xml, 0, self.control()))
            self.assertNotIn("x" * 100, public)
            self.assertNotIn("-suffix]", public)
            root = ET.parse(xml)
            root.getroot().find("testsuite")[0].set("name", name[:-2] + "Y]")
            root.write(xml)
            with self.assertRaisesRegex(D.Refused, "focused_case_identity_refused"):
                D.focused_result(xml, collected, self.control())

    def test_private_case_name_remains_bounded(self):
        name = "test_pause[" + "x" * (128 * 1024) + "]"
        with tempfile.TemporaryDirectory() as directory:
            xml, collected = self.xml_collection(Path(directory),
                lambda suite: suite[0].set("name", name),
                lambda value: value["cases"][0].update(name=name))
            with self.assertRaisesRegex(D.Refused, "focused_collection_identity_refused"):
                D.focused_result(xml, collected, self.control())

    def test_dropped_variant_cannot_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            xml, collected = self.xml_collection(Path(directory), lambda suite: suite.remove(suite[0]))
            with self.assertRaisesRegex(D.Refused, "focused_collected_cases_missing"):
                D.focused_result(xml, collected, self.control())

    def test_duplicate_or_unexpected_case_refused(self):
        for name in ("test_pause[first]", "test_unexpected"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                xml, collected = self.xml_collection(Path(directory), lambda suite: ET.SubElement(
                    suite, "testcase", classname="tests.test_controls", name=name))
                with self.assertRaisesRegex(D.Refused, "focused_case_identity_refused"):
                    D.focused_result(xml, collected, self.control())

    def test_failure_error_or_skip_refused_without_leaking_text(self):
        for kind in ("failure", "error", "skipped"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                def change(suite):
                    ET.SubElement(suite[0], kind, message="PRIVATE_CANARY").text = "PRIVATE_CANARY"
                xml, collected = self.xml_collection(Path(directory), change)
                with self.assertRaisesRegex(D.Refused, "focused_failure_or_skip_refused"):
                    D.focused_result(xml, collected, self.control())
                self.assertNotIn("PRIVATE_CANARY", json.dumps(D.focused_diagnostic(xml, 1, self.control())))

    def test_deselection_and_missing_base_function_refused(self):
        for change in (lambda x: x.update(deselected=1),
                       lambda x: x["cases"].pop()):
            with tempfile.TemporaryDirectory() as directory:
                xml, collected = self.xml_collection(Path(directory), change_collection=change)
                with self.assertRaises(D.Refused):
                    D.focused_result(xml, collected, self.control())

    def fixture(self, path):
        source = path / "source"
        source.mkdir()
        files = {"LICENSE": b"synthetic license\n", "tests/conftest.py": b"",
                 "pytest.ini": b"[pytest]\n", "tests/test_controls.py": b"def test_pause(): pass\n",
                 "custom_components/homecircle/__init__.py": b"",
                 "custom_components/homecircle/manifest.json": P.encoded({"domain": "homecircle",
                     "version": "1.0.0-rc.1", "requirements": ["example==1.0"]})}
        for index in range(294):
            files[f"custom_components/homecircle/fixture_{index}.py"] = b"# public synthetic\n"
        for name, raw in files.items():
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        export = {"schema": 1, "source": "a" * 40, "count": len(files), "files": {
            name: {**D.fingerprint(raw), "git_blob": D.git_blob(raw)} for name, raw in files.items()}}
        body = {"LICENSE": files["LICENSE"], "__init__.py": files["custom_components/homecircle/__init__.py"],
                "manifest.json": files["custom_components/homecircle/manifest.json"]}
        body.update({f"fixture_{i}.py": files[f"custom_components/homecircle/fixture_{i}.py"] for i in range(97)})
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for name, raw in sorted(body.items()):
                archive.writestr(name, raw)
        package = buffer.getvalue()
        inventory = {"version": "1.0.0-rc.1", "archive_sha256": D.sha(package),
                     "files": {name: D.fingerprint(raw) for name, raw in body.items()}}
        return source, P.encoded(export), package, P.encoded(inventory), P.encoded(["tests/test_controls.py"])

    def test_preparation_is_complete_and_never_executes_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            args = self.fixture(path)
            with patch.object(P.D, "runtime", side_effect=AssertionError("native import refused")):
                result = P.prepare(*args, path / "prepared")
            self.assertEqual(result["source_files"], 300)
            self.assertEqual(result["selected_base_functions"], 1)
            self.assertFalse(result["native_execution_performed"])
            self.assertTrue((path / "prepared/PREPARED.json").is_file())
            self.assertFalse((path / "prepared.preparing").exists())

    def test_extra_or_link_payload_refused_before_copy(self):
        for extra in ("unrelated", "link"):
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                P.prepare(*self.fixture(path), path / "prepared")
                payload = path / "prepared/payload"
                if extra == "link":
                    (payload / "source-export.json").unlink()
                    (payload / "source-export.json").symlink_to(path / "missing")
                else:
                    (payload / extra).write_bytes(b"not public input")
                controls = P.D.configuration(payload, (path / "prepared/CONFIG.sha256").read_text().strip())
                with self.assertRaisesRegex(P.D.Refused, "exact_payload_members_required"):
                    P.D.inputs(payload, controls)

    def test_preparation_failure_removes_only_its_temporary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            args = self.fixture(path)
            sibling = path / "unrelated"
            sibling.write_bytes(b"preserved")
            original = Path.write_bytes
            def fail(target, raw):
                if target.name == "homecircle.zip":
                    raise OSError("injected write failure")
                return original(target, raw)
            with patch.object(Path, "write_bytes", fail), self.assertRaises(OSError):
                P.prepare(*args, path / "prepared")
            self.assertFalse((path / "prepared").exists())
            self.assertFalse((path / "prepared.preparing").exists())
            self.assertEqual(sibling.read_bytes(), b"preserved")

    def test_existing_preparation_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            args = self.fixture(path)
            output = path / "prepared"
            output.mkdir()
            (output / "preserve").write_bytes(b"preserved")
            with self.assertRaisesRegex(P.D.Refused, "fresh_owned_preparation_required"):
                P.prepare(*args, output)
            self.assertEqual((output / "preserve").read_bytes(), b"preserved")


if __name__ == "__main__":
    unittest.main()
