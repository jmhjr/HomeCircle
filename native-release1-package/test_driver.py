"""Standalone configuration/provenance contracts; no HA or native libraries."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import driver


class DriverContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.config = {
            "schema": 1, "candidate_source_commit": "a" * 40, "candidate_source_prefix": "",
            "source_sha256": "b" * 64, "source_inventory_sha256": "c" * 64, "source_files": 330,
            "driver_sha256": driver.sha(Path(driver.__file__).read_bytes()), "checker_sha256": "d" * 64,
            "version": driver.VERSION, "expected_release_files": 113, "minimum_backend_passed": 1443,
            "required_backend_tests": [{"class": "tests.test_one", "function": "test_regression_one"},
                                       {"class": "tests.test_two", "function": "test_regression_two"}],
            "frontend_tests": 122}

    def load(self, value=None):
        path = self.root / "config.json"
        raw = json.dumps(self.config if value is None else value).encode()
        path.write_bytes(raw)
        return driver.load_pins(path, driver.sha(raw))

    def test_reviewed_configuration_is_accepted_without_fixed_old_source_count(self):
        self.assertEqual(self.load()["source_files"], 330)

    def test_placeholder_and_wrong_driver_are_refused(self):
        for field in ("source_sha256", "source_inventory_sha256", "candidate_source_commit", "checker_sha256", "driver_sha256"):
            config = dict(self.config, **{field: "FILL_LATER"})
            with self.subTest(field=field), self.assertRaises(driver.Refused):
                self.load(config)
        with self.assertRaisesRegex(driver.Refused, "driver_pin_refused"):
            self.load(dict(self.config, driver_sha256="1" * 64))

    def test_source_config_and_version_cannot_silently_change_scope(self):
        for key, value in (("source_files", True), ("source_files", 0), ("expected_release_files", 112),
                           ("frontend_tests", 121), ("minimum_backend_passed", 1442),
                           ("version", "1.0.0"), ("candidate_source_prefix", "../private/")):
            with self.subTest(key=key), self.assertRaises(driver.Refused):
                self.load(dict(self.config, **{key: value}))

    def test_duplicate_config_keys_and_tampered_config_hash_are_refused(self):
        raw = json.dumps(self.config).encode().replace(b'"schema": 1', b'"schema": 1, "schema": 1')
        path = self.root / "config.json"
        path.write_bytes(raw)
        with self.assertRaisesRegex(driver.Refused, "duplicate_config_key_refused"):
            driver.load_pins(path, driver.sha(raw))
        with self.assertRaisesRegex(driver.Refused, "input_hash_refused"):
            driver.load_pins(path, "0" * 64)

    def test_required_regressions_are_named_unique_tests(self):
        for required in ([], [self.config["required_backend_tests"][0]] * 2,
                         [{"class": "PRIVATE-CANARY", "function": "test_regression"}] * 2):
            with self.subTest(required=required), self.assertRaises(driver.Refused):
                self.load(dict(self.config, required_backend_tests=required))

    def xml(self, content):
        path = self.root / "tests.xml"
        path.write_text('<testsuites><testsuite>' + content + '</testsuite></testsuites>')
        return path

    def test_backend_parser_records_passing_required_regression_and_real_counts(self):
        path = self.xml('<testcase classname="tests.test_one" name="test_regression_one[True]"/>'
                        '<testcase classname="tests.test_two" name="test_regression_two"/>'
                        '<testcase classname="tests.test_optional" name="test_optional"><skipped/></testcase>')
        with patch.object(driver, "PINS", self.config):
            result, skipped = driver.backend_result(path)
        self.assertEqual((result["passed"], result["failed"], result["skipped"]), (2, 0, 1))
        self.assertTrue(all(item["passed"] for item in result["required_regressions"]))
        self.assertEqual(len(skipped), 1)

    def test_failed_skipped_or_missing_required_regression_never_counts_as_passed(self):
        for outcome in ('<failure>PRIVATE-CANARY</failure>', '<skipped/>', '<error/>'):
            path = self.xml('<testcase classname="tests.test_one" name="test_regression_one">' + outcome + '</testcase>')
            with patch.object(driver, "PINS", self.config):
                result, _ = driver.backend_result(path)
            self.assertFalse(any(item["passed"] for item in result["required_regressions"]))
            self.assertNotIn("PRIVATE-CANARY", json.dumps(result))

    def test_duplicate_or_ambiguous_junit_cases_are_refused(self):
        for xml in ('<testcase classname="tests.test_one" name="test_x"/>' * 2,
                    '<testcase classname="tests.test_one" name="test_x"><failure/><skipped/></testcase>'):
            with patch.object(driver, "PINS", self.config), self.assertRaises(driver.Refused):
                driver.backend_result(self.xml(xml))

    def test_frontend_hash_check_requires_exact_current_bytes(self):
        root = self.root / "custom_components/homecircle/frontend"
        root.mkdir(parents=True)
        for name in driver.FRONTEND:
            (root / name).write_bytes(name.encode())
        expected = driver.frontend_inventory(self.root)
        driver.frontend_matches(self.root, expected)
        (root / driver.FRONTEND[0]).write_bytes(b"changed")
        with self.assertRaisesRegex(driver.Refused, "frontend_bundle_bytes_changed"):
            driver.frontend_matches(self.root, expected)

    def test_launcher_extracts_real_config_fields_before_any_docker_operation(self):
        payload = self.root / "payload"
        payload.mkdir()
        (payload / "config.json").write_text(json.dumps(self.config))
        script = Path(driver.__file__).with_name("run_host.sh").read_text()
        start = script.index("parsed_driver_sha=$(jq")
        end = script.index("[[ $(sha256sum \"$script_dir/driver.py\"", start)
        fragment = script[start:end]
        command = ('set -euo pipefail; payload=$1; ' + fragment
                   + '\nprintf "%s\\n" "$driver_sha" "$source_sha" "$inventory_sha" "$source_commit" '
                     '"$source_count" "$minimum_backend" "$required_regression_count"')
        result = subprocess.run(["bash", "-c", command, "qa", str(payload)], stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        self.assertEqual(result.stdout.decode().splitlines(), [self.config["driver_sha256"],
                         self.config["source_sha256"], self.config["source_inventory_sha256"],
                         self.config["candidate_source_commit"], "330", "1443", "2"])

    def test_source_git_comparison_is_bound_to_the_exact_commit_and_blob(self):
        repository = self.root / "repository"
        repository.mkdir()
        env = {"PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"}
        def git(*args):
            return subprocess.run(["git", "-C", str(repository), *args], env=env, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout
        git("init", "--template=", "--initial-branch=qa")
        (repository / "example.txt").write_bytes(b"canonical")
        git("add", "example.txt")
        git("-c", "user.name=HomeCircle QA", "-c", "user.email=qa@example.invalid", "commit", "-m", "Synthetic source")
        commit = git("rev-parse", "HEAD").decode().strip()
        with patch.object(driver, "SOURCE_COMMIT", commit), patch.object(driver, "SOURCE_PREFIX", ""):
            result = driver.verify_git_source({"example.txt": b"canonical"}, repository)
            self.assertEqual(result["canonical_commit_blobs_verified"], 1)
            with self.assertRaisesRegex(driver.Refused, "source_git_blob_mismatch"):
                driver.verify_git_source({"example.txt": b"tampered"}, repository)
        self.assertEqual(git("status", "--porcelain"), b"")


if __name__ == "__main__":
    unittest.main()
