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


class BaselineContracts(unittest.TestCase):
    setUp = DriverContracts.setUp
    load = DriverContracts.load
    xml = DriverContracts.xml

    def red_xml(self, outcome="failure", identities=None):
        return self.xml("".join('<testcase classname="' + classname + '" name="' + name + '">' +
                        ('<' + outcome + '>PRIVATE-CANARY</' + outcome + '>' if outcome else '') +
                        '</testcase>' for classname, name in
                        (driver.BASELINE_RED_CASES if identities is None else identities)))

    def baseline_fixture(self):
        from types import SimpleNamespace
        tree, payload, results = (self.root / name for name in ("green", "payload", "results"))
        payload.mkdir()
        results.mkdir()
        baseline = b"original baseline"
        (payload / "baseline-vault.py").write_bytes(baseline)
        files = {driver.BASELINE_VAULT_NAME: b"fixed vault", "tests/test_public.py": b"public"}
        driver.extract(files, tree)
        frontend = tree / "custom_components/homecircle/frontend"
        frontend.mkdir(parents=True)
        for name in driver.FRONTEND:
            (payload / name).write_bytes(name.encode())
            (frontend / name).write_bytes(name.encode())
        private = tree / "node_modules/private"
        private.parent.mkdir()
        private.write_bytes(b"PRIVATE-CANARY")
        return SimpleNamespace(tree=tree, payload=payload, results=results), files, baseline, driver.frontend_inventory(tree)

    def test_required_function_bound_accepts_36_and_refuses_37(self):
        required = [{"class": "tests.test_limit", "function": "test_case_" + str(index)} for index in range(37)]
        self.assertEqual(len(self.load(dict(self.config, required_backend_tests=required[:36]))["required_backend_tests"]), 36)
        with self.assertRaisesRegex(driver.Refused, "required_tests_config_refused"):
            self.load(dict(self.config, required_backend_tests=required))

    def test_baseline_parser_requires_all_fourteen_expected_failures_without_raw_text(self):
        result = driver.baseline_red_result(self.red_xml(), 1)
        self.assertEqual(result["expected_failure_cases"], 14)
        self.assertTrue(result["all_expected_regressions_observed"])
        self.assertNotIn("PRIVATE-CANARY", json.dumps(result))

    def test_baseline_parser_refuses_success_errors_skips_or_unexpected_exit(self):
        for outcome, code in (("", 0), ("error", 1), ("skipped", 1), ("", 1), ("failure", 0), ("failure", 2)):
            with self.subTest(outcome=outcome, code=code), self.assertRaises(driver.Refused):
                driver.baseline_red_result(self.red_xml(outcome), code)

    def test_baseline_parser_refuses_missing_extra_duplicate_or_wrong_identity(self):
        identities = list(driver.BASELINE_RED_CASES)
        for selected in (identities[:-1], identities + [identities[0]],
                         identities[:-1] + [("tests.test_wrong", "test_wrong")]):
            with self.subTest(selected=selected), self.assertRaises(driver.Refused):
                driver.baseline_red_result(self.red_xml(identities=selected), 1)

    def test_baseline_parser_refuses_absent_and_symlink_xml(self):
        path = self.root / "missing.xml"
        with self.assertRaises(driver.Refused):
            driver.baseline_red_result(path, 1)
        actual = self.red_xml()
        path.symlink_to(actual)
        with self.assertRaises(driver.Refused):
            driver.baseline_red_result(path, 1)

    def test_combined_budget_uses_only_remaining_time_and_refuses_expiry(self):
        with patch.object(driver.time, "monotonic", return_value=100):
            self.assertEqual(driver.backend_budget(125, 120), 25)
            self.assertEqual(driver.backend_budget(1000, 120), 120)
            for deadline in (99, 100, 100.9):
                with self.subTest(deadline=deadline), self.assertRaises(driver.Refused):
                    driver.backend_budget(deadline)

    def test_baseline_copy_is_public_only_pinned_and_removed_without_touching_green(self):
        args, files, baseline, bundle = self.baseline_fixture()
        def run(command, *, cwd, log, limit):
            self.assertNotEqual(cwd, args.tree)
            self.assertFalse((cwd / "node_modules").exists())
            self.assertEqual((cwd / driver.BASELINE_VAULT_NAME).read_bytes(), baseline)
            expected = set(files) | {"custom_components/homecircle/frontend/" + name for name in driver.FRONTEND}
            self.assertEqual({path.relative_to(cwd).as_posix() for path in cwd.rglob("*") if path.is_file()}, expected)
            self.assertEqual(len(command) - 6, 14)
            self.assertLessEqual(limit, 120)
            xml = Path(command[5])
            xml.write_bytes(self.red_xml().read_bytes())
            return 1
        with patch.object(driver, "BASELINE_VAULT_SHA", driver.sha(baseline)), patch.object(driver, "run_owned", side_effect=run):
            result = driver.baseline_red(args, files, bundle, driver.time.monotonic() + 900)
        self.assertTrue(result["private_copy_removed"] and result["fixed_source_unchanged"])
        self.assertFalse((args.results / "baseline-private-source").exists())
        self.assertEqual((args.tree / driver.BASELINE_VAULT_NAME).read_bytes(), b"fixed vault")
        self.assertNotIn("PRIVATE-CANARY", json.dumps(result))

    def test_baseline_private_copy_is_removed_when_runner_fails(self):
        args, files, baseline, bundle = self.baseline_fixture()
        with patch.object(driver, "BASELINE_VAULT_SHA", driver.sha(baseline)), patch.object(driver, "run_owned", side_effect=RuntimeError("synthetic")):
            with self.assertRaisesRegex(RuntimeError, "synthetic"):
                driver.baseline_red(args, files, bundle, driver.time.monotonic() + 900)
        self.assertFalse((args.results / "baseline-private-source").exists())
        driver.source_unchanged(files, args.tree)

    def test_baseline_private_copy_is_removed_when_expected_failures_are_missing(self):
        args, files, baseline, bundle = self.baseline_fixture()
        def run(command, **_kwargs):
            Path(command[5]).write_bytes(self.red_xml(identities=[]).read_bytes())
            return 1
        with patch.object(driver, "BASELINE_VAULT_SHA", driver.sha(baseline)), patch.object(driver, "run_owned", side_effect=run):
            with self.assertRaisesRegex(driver.Refused, "baseline_red_exact_cases_refused"):
                driver.baseline_red(args, files, bundle, driver.time.monotonic() + 900)
        self.assertFalse((args.results / "baseline-private-source").exists())

    def test_baseline_refuses_tampered_original_before_runner(self):
        args, files, _baseline, bundle = self.baseline_fixture()
        with patch.object(driver, "run_owned") as run, self.assertRaisesRegex(driver.Refused, "input_hash_refused"):
            driver.baseline_red(args, files, bundle, driver.time.monotonic() + 900)
        run.assert_not_called()

    def test_launcher_keeps_offline_deadline_and_four_member_payload_contract(self):
        script = Path(driver.__file__).with_name("run_host.sh").read_text()
        self.assertIn("printf '%s\\n' baseline-vault.py config.json source-inventory.json source.tgz", script)
        self.assertEqual(script.count("for source in baseline-vault.py config.json source-inventory.json source.tgz; do"), 2)
        self.assertIn('bounded 940 "${DOCKER[@]}" exec', script)
        self.assertEqual(script.count(".baseline_red.expected_failure_cases==14"), 2)
        self.assertEqual(script.count(".baseline_red.private_copy_removed==true"), 2)


if __name__ == "__main__":
    unittest.main()
