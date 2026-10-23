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
            "version": driver.VERSION, "expected_release_files": 112, "minimum_backend_passed": 1443,
            "required_backend_tests": [{"class": "tests.test_one", "function": "test_regression_one"},
                                       {"class": "tests.test_two", "function": "test_regression_two"}],
            "frontend_tests": 126,"package_sha256":"e"*64,"package_inventory_sha256":"f"*64,
            "canonical_package_sha256":"1"*64,"requirements_helper_sha256":"2"*64}

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
        for key, value in (("source_files", True), ("source_files", 0), ("expected_release_files", 111),
                           ("frontend_tests", 121), ("minimum_backend_passed", 1442),
                           ("version", "0.0.0-unreviewed"), ("candidate_source_prefix", "../private/")):
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
        repository=self.root/'repository';repository.mkdir()
        commit='a'*40
        def respond(command,**kwargs):
            self.assertEqual(command[:3],['git','-C',str(repository)])
            self.assertEqual(kwargs['stdin'],subprocess.DEVNULL)
            self.assertEqual(kwargs['env']['GIT_CONFIG_GLOBAL'],'/dev/null')
            operation=command[3:]
            if operation==['rev-parse','--verify',commit+'^{commit}']:
                return subprocess.CompletedProcess(command,0,(commit+'\n').encode())
            self.assertEqual(operation,['cat-file','blob',commit+':example.txt'])
            return subprocess.CompletedProcess(command,0,b'canonical')
        with patch.object(driver,'SOURCE_COMMIT',commit),patch.object(driver,'SOURCE_PREFIX',''), \
                patch.object(driver.subprocess,'run',side_effect=respond) as calls:
            self.assertEqual(driver.verify_git_source({'example.txt':b'canonical'},repository)
                ['canonical_commit_blobs_verified'],1)
            with self.assertRaisesRegex(driver.Refused,'source_git_blob_mismatch'):
                driver.verify_git_source({'example.txt':b'tampered'},repository)
        self.assertEqual(calls.call_count,4)


class BaselineContracts(unittest.TestCase):
    setUp = DriverContracts.setUp
    load = DriverContracts.load
    xml = DriverContracts.xml

    def red_xml(self, outcome="failure", identities=None):
        return self.xml("".join('<testcase classname="' + classname + '" name="' + name + '">' +
                        '<properties><property name="' + driver.BASELINE_PROPERTY + '" value="verified"/></properties>' +
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

    def test_required_function_bound_accepts_54_and_refuses_55(self):
        required = [{"class": "tests.test_limit", "function": "test_case_" + str(index)} for index in range(55)]
        self.assertEqual(len(self.load(dict(self.config, required_backend_tests=required[:54]))["required_backend_tests"]), 54)
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
            self.assertEqual(len(command) - 7, 14)
            self.assertLessEqual(limit, 120)
            xml = Path(command[6])
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
            Path(command[6]).write_bytes(self.red_xml(identities=[]).read_bytes())
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

    def test_launcher_keeps_offline_deadline_and_six_member_payload_contract(self):
        script = Path(driver.__file__).with_name("run_host.sh").read_text()
        self.assertIn("printf '%s\\n' baseline-vault.py config.json homecircle.zip inventory.json source-inventory.json source.tgz", script)
        self.assertEqual(script.count("for source in baseline-vault.py config.json homecircle.zip inventory.json source-inventory.json source.tgz; do"), 2)
        self.assertIn('bounded 940 "${DOCKER[@]}" exec', script)
        self.assertEqual(script.count(".baseline_red.expected_failure_cases==14"), 2)
        self.assertEqual(script.count(".baseline_red.private_copy_removed==true"), 2)


class CauseContracts(unittest.TestCase):
    setUp = DriverContracts.setUp
    xml = DriverContracts.xml
    red_xml = BaselineContracts.red_xml

    def test_cause_trace_requires_exact_builtin_type_and_bound_code(self):
        def failure():
            raise ValueError("PRIVATE-CAUSE-CANARY")
        def unrelated():
            pass
        try:
            failure()
        except ValueError as error:
            self.assertTrue(driver.baseline_trace_matches(error, ValueError, (failure.__code__,)))
            self.assertFalse(driver.baseline_trace_matches(error, TypeError, (failure.__code__,)))
            self.assertFalse(driver.baseline_trace_matches(error, ValueError, (unrelated.__code__,)))
        class CustomError(ValueError):
            pass
        self.assertFalse(driver.baseline_trace_matches(CustomError("PRIVATE-CAUSE-CANARY"), ValueError, ()))

    def test_cause_trace_requires_exact_assertion_line(self):
        def failure():
            assert False, "PRIVATE-CAUSE-CANARY"
        try:
            failure()
        except AssertionError as error:
            current = error.__traceback__
            while current.tb_next is not None:
                current = current.tb_next
            site = (failure.__code__, current.tb_lineno)
            self.assertTrue(driver.baseline_trace_matches(error, AssertionError, (), (site,)))
            self.assertFalse(driver.baseline_trace_matches(error, AssertionError, (), ((site[0], site[1] + 1),)))
            self.assertFalse(driver.baseline_trace_matches(error, TypeError, (), (site,)))

    def test_cause_parser_requires_one_fixed_property_for_every_case(self):
        source = self.red_xml().read_text()
        tag = '<property name="' + driver.BASELINE_PROPERTY + '" value="verified"/>'
        for changed in (source.replace(tag, "", 1), source.replace(tag, tag * 2, 1),
                        source.replace(tag, '<property name="PRIVATE-CAUSE-CANARY" value="verified"/>', 1),
                        source.replace(tag, tag.replace('"verified"', '"refused"'), 1),
                        source.replace(tag, tag.replace('/>', '>PRIVATE-CAUSE-CANARY</property>'), 1)):
            path = self.root / "cause.xml"
            path.write_text(changed)
            with self.subTest(), self.assertRaisesRegex(driver.Refused, "baseline_red_cause_refused"):
                driver.baseline_red_result(path, 1)
        result = driver.baseline_red_result(self.red_xml(), 1)
        self.assertTrue(result["cause_verified"])
        self.assertNotIn("PRIVATE-CAUSE-CANARY", json.dumps(result))

    def test_cause_unwrap_preserves_async_source_and_refuses_cycles_or_properties(self):
        import asyncio
        import functools
        async def original():
            assert False, "PRIVATE-CAUSE-CANARY"
        @functools.wraps(original)
        def wrapper():
            return asyncio.run(original())
        self.assertIs(driver.baseline_unwrap(wrapper), original)
        try:
            wrapper()
        except AssertionError as error:
            self.assertTrue(driver.baseline_trace_matches(error, AssertionError, (driver.baseline_unwrap(wrapper).__code__,)))
            self.assertFalse(driver.baseline_trace_matches(error, TypeError, (original.__code__,)))
        wrapper.__wrapped__ = wrapper
        self.assertIsNone(driver.baseline_unwrap(wrapper))
        class Trap:
            @property
            def __wrapped__(self):
                raise AssertionError("custom property must not execute")
        self.assertIsNone(driver.baseline_unwrap(Trap()))

    def test_unknown_cause_identity_refuses_before_any_read(self):
        with patch.object(driver, "read_pinned") as read:
            self.assertFalse(driver.baseline_failure_cause(lambda: None, ("tests.test_private", "test_private"), TypeError()))
        read.assert_not_called()

    def test_cause_hook_emits_only_call_phase_fixed_property_and_fails_closed(self):
        import sys
        from types import SimpleNamespace
        seen = []
        def main(arguments, plugins):
            self.assertEqual(arguments, ["synthetic-case"])
            probe = plugins[0]
            item = SimpleNamespace(function=lambda: None, name="synthetic-case", user_properties=[])
            for phase in ("setup", "teardown"):
                probe.pytest_runtest_makereport(item, SimpleNamespace(when=phase))
            self.assertEqual(item.user_properties, [])
            with patch.object(driver, "baseline_failure_cause", return_value=True):
                probe.pytest_runtest_makereport(item, SimpleNamespace(when="call", excinfo=SimpleNamespace(value=ValueError())))
            with patch.object(driver, "baseline_failure_cause", side_effect=TypeError("PRIVATE-CAUSE-CANARY")):
                probe.pytest_runtest_makereport(item, SimpleNamespace(when="call", excinfo=SimpleNamespace(value=TypeError())))
            seen.extend(item.user_properties)
            return 1
        fake = SimpleNamespace(hookimpl=lambda **kwargs: (lambda function: function), main=main)
        with patch.dict(sys.modules, {"pytest": fake}), patch.object(sys, "path", list(sys.path)):
            self.assertEqual(driver.baseline_pytest(["synthetic-case"]), 1)
        self.assertEqual(seen, [(driver.BASELINE_PROPERTY, "verified"), (driver.BASELINE_PROPERTY, "refused")])
        self.assertNotIn("PRIVATE-CAUSE-CANARY", json.dumps(seen))

    def test_cause_wrapper_loads_only_existing_absolute_driver_without_extra_copy_file(self):
        import ast
        source = Path(driver.__file__).read_text()
        self.assertIn('"-c", BASELINE_WRAPPER, str(Path(__file__).resolve())', source)
        self.assertIn("spec_from_file_location('homecircle_baseline_driver',sys.argv[1])", driver.BASELINE_WRAPPER)
        self.assertIn("m.baseline_pytest(sys.argv[2:])", driver.BASELINE_WRAPPER)
        tree = ast.parse(driver.BASELINE_WRAPPER)
        self.assertEqual({node.func.attr for node in ast.walk(tree)
                          if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)},
                         {"spec_from_file_location", "module_from_spec", "exec_module", "baseline_pytest"})


class DiagnosticContracts(unittest.TestCase):
    setUp = DriverContracts.setUp
    xml = DriverContracts.xml

    def test_duplicate_teardown_error_is_reported_before_unchanged_refusal(self):
        source = {"tests/test_public.py": b"async def test_break(): pass\n"}
        path = self.xml('<testcase classname="tests.test_public" name="test_break[PRIVATE-CANARY]"/>'
                        '<testcase classname="tests.test_public" name="test_break[PRIVATE-CANARY]">'
                        '<error>PRIVATE-TRACE-CANARY</error></testcase>')
        output = self.root / "package-summary.json"
        result = {"schema": 1, "outcome": "failed", "completed": False}
        with self.assertRaisesRegex(driver.Refused, "duplicate_backend_case_refused"):
            driver.backend_with_diagnostics(path, source, result, output)
        actual = json.loads(output.read_bytes())
        diagnostic = actual["backend_diagnostics"]
        self.assertEqual({key: diagnostic[key] for key in
                         ("case_records", "passed", "failed", "skipped", "error_records",
                          "failure_records", "duplicate_records", "duplicate_identities")},
                         {"case_records": 2, "passed": 1, "failed": 1, "skipped": 0,
                          "error_records": 1, "failure_records": 0,
                          "duplicate_records": 1, "duplicate_identities": 1})
        self.assertEqual(diagnostic["failure_labels"],
                         [{"class": "tests.test_public", "function": "test_break", "case_records": 1}])
        self.assertEqual(diagnostic["duplicate_labels"],
                         [{"class": "tests.test_public", "function": "test_break", "case_records": 2}])
        self.assertFalse(diagnostic["acceptance_qualified"])
        self.assertNotIn("PRIVATE", output.read_text())

    def test_unknown_junit_names_and_trace_text_never_become_public_labels(self):
        path = self.xml('<testcase classname="tests.PRIVATE_CANARY" name="test_PRIVATE_CANARY">'
                        '<failure>PRIVATE-TRACE-CANARY</failure></testcase>' * 2)
        diagnostic = driver.backend_diagnostics(path, {("tests.test_public", "test_known")})
        self.assertEqual(diagnostic["unclassified_failure_records"], 2)
        self.assertEqual(diagnostic["unclassified_duplicate_identities"], 1)
        self.assertEqual(diagnostic["failure_labels"], [])
        self.assertEqual(diagnostic["duplicate_labels"], [])
        self.assertNotIn("PRIVATE", json.dumps(diagnostic))

    def test_catalog_uses_only_source_test_functions_and_class_methods(self):
        source = {"tests/test_public.py": b"""async def test_direct(): pass
class PublicTests:
    def test_method(self): pass
def helper():
    def test_private_nested(): pass
""", "work/test_private.py": b"def test_not_public(): pass\n"}
        self.assertEqual(driver.public_test_catalog(source),
                         {("tests.test_public", "test_direct"),
                          ("tests.test_public.PublicTests", "test_method")})

    def test_ambiguous_outcomes_counted_but_still_refused(self):
        path = self.xml('<testcase classname="tests.test_public" name="test_known">'
                        '<error>PRIVATE-TRACE-CANARY</error><skipped/></testcase>')
        diagnostic = driver.backend_diagnostics(path, {("tests.test_public", "test_known")})
        self.assertEqual(diagnostic["ambiguous_outcome_records"], 1)
        self.assertEqual(diagnostic["failed"], 1)
        self.assertEqual(diagnostic["skipped"], 1)
        with patch.object(driver, "PINS", self.config), self.assertRaisesRegex(
                driver.Refused, "ambiguous_backend_outcome_refused"):
            driver.backend_result(path)


if __name__ == "__main__":
    unittest.main()


class ExactCandidateContracts(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name).resolve()
        self.payload=Path(driver.__file__).with_name('payload')
        config=json.loads((self.payload/'config.json').read_bytes())
        driver.configure(config)
        self.files=driver.inputs(self.payload)

    def test_original_zip_all_members_and_git_bindings_are_exact(self):
        raw,inventory,body=driver.candidate_inputs(self.payload,self.files)
        self.assertEqual(len(body),112)
        self.assertEqual(driver.sha(raw),driver.PINS['package_sha256'])
        self.assertEqual(driver.sha(inventory),driver.PINS['package_inventory_sha256'])
        changed=dict(self.files);changed['custom_components/homecircle/activity.py']=b'changed'
        with self.assertRaisesRegex(driver.Refused,'candidate_git_source_refused'):
            driver.candidate_inputs(self.payload,changed)

    def test_candidate_pin_rejects_a_different_archive_before_open(self):
        target=self.root/'payload';target.mkdir()
        (target/'homecircle.zip').write_bytes(b'a distinct canonical archive')
        with self.assertRaisesRegex(driver.Refused,'input_hash_refused'):
            driver.candidate_inputs(target,self.files)

    def prepared(self):
        from types import SimpleNamespace
        tree=self.root/'tree';results=self.root/'results';results.mkdir()
        driver.extract(self.files,tree)
        _raw,_inventory,body=driver.candidate_inputs(self.payload,self.files)
        driver.install_candidate(tree,body,self.files)
        return SimpleNamespace(tree=tree,results=results,payload=self.payload),body,driver.frontend_inventory(tree)

    def test_canonical_input_stays_installed_exported_and_rebuild_is_identical(self):
        args,body,bundle=self.prepared()
        result=driver.build(args,self.files,bundle)
        self.assertEqual(result['release_sha256'],driver.PINS['package_sha256'])
        self.assertEqual(result['canonical_rebuild_sha256'],driver.PINS['canonical_package_sha256'])
        self.assertEqual(result['release_sha256'],result['canonical_rebuild_sha256'])
        self.assertFalse(result['candidate_archive_rebuilt'])
        self.assertTrue(result['canonical_reproducible_archive'])
        self.assertEqual((args.results/'release/homecircle.zip').read_bytes(),(self.payload/'homecircle.zip').read_bytes())
        self.assertEqual((args.results/'release/inventory.json').read_bytes(),(self.payload/'inventory.json').read_bytes())
        driver.candidate_installed(args.tree,body,self.files)
        again=driver.build(args,self.files,bundle)
        self.assertEqual(again,result)

    def test_installed_byte_or_rebuilt_frontend_mismatch_refuses(self):
        args,body,bundle=self.prepared()
        altered=dict(bundle);altered['homecircle-card.js']={'bytes':1,'sha256':'a'*64}
        with self.assertRaisesRegex(driver.Refused,'candidate_rebuilt_frontend_refused'):
            driver.candidate_inputs(self.payload,self.files,altered)
        (args.tree/'custom_components/homecircle/activity.py').write_bytes(b'changed')
        with self.assertRaisesRegex(driver.Refused,'exact_candidate_install_refused'):
            driver.candidate_installed(args.tree,body,self.files)

    def test_current_core_fixture_and_requirement_helper_are_explicit(self):
        self.assertEqual(driver.CORE,'2026.10.2')
        self.assertEqual(driver.MINIMUM_CORE,'2026.9.4')
        self.assertEqual(driver.sha(Path(driver.__file__).with_name('requirements_support.py').read_bytes()),
            driver.PINS['requirements_helper_sha256'])
        graph=driver.requirements_helper()
        self.assertTrue(callable(graph.core_component_requirements))
        self.assertEqual(len(driver.PINS['required_backend_tests']),54)

    def test_optional_skip_identity_is_public_fixed_and_unknown_is_redacted(self):
        path=self.root/'junit.xml'
        path.write_text('<testsuites><testsuite><testcase classname="tests.test_findmy_runtime_bootstrap" '
            'name="test_retained_public_apple_dmg_fixed_ranges"><skipped/></testcase></testsuite></testsuites>')
        result,_=driver.backend_result(path)
        self.assertEqual(result['skip_identities'],[{'class':'tests.test_findmy_runtime_bootstrap',
            'function':'test_retained_public_apple_dmg_fixed_ranges'}])
        path.write_text('<testsuites><testsuite><testcase classname="PRIVATE-CANARY" name="PRIVATE-CANARY">'
            '<skipped/></testcase></testsuite></testsuites>')
        result,_=driver.backend_result(path)
        self.assertNotIn('PRIVATE-CANARY',json.dumps(result))


    def test_source_only_readme_is_exact_and_every_other_extra_refuses(self):
        args,body,_bundle=self.prepared()
        package=args.tree/'custom_components/homecircle'
        (package/'unreviewed_extra.txt').write_text('extra')
        with self.assertRaisesRegex(driver.Refused,'exact_candidate_install_refused'):
            driver.candidate_installed(args.tree,body,self.files)
        (package/'unreviewed_extra.txt').unlink()
        (package/'README.md').write_text('changed')
        with self.assertRaisesRegex(driver.Refused,'source_only_readme_refused'):
            driver.candidate_installed(args.tree,body,self.files)

    def test_requirement_helper_wrong_pin_refuses_before_first_import(self):
        with patch.object(driver,'PINS',{**driver.PINS,'requirements_helper_sha256':'a'*64}), \
                patch.object(driver.importlib.util,'spec_from_file_location') as importer:
            with self.assertRaisesRegex(driver.Refused,'input_hash_refused'):
                driver.requirements_helper()
        importer.assert_not_called()


    def test_launcher_finish_requires_explicit_original_and_canonical_identities(self):
        import re
        script=Path(driver.__file__).with_name('run_host.sh').read_text()
        self.assertNotIn('.reproducible_archive',script)
        finish=script[script.index('finish() {'):script.index('trap finish EXIT')]
        predicate=re.search(r"'(\.outcome==\"passed\".*?release_candidate_validation==true)'",finish,re.S).group(1)
        value={'outcome':'passed','completed':True,'backend':{'passed':1732,'failed':0,'skipped':1,
            'required_regressions':[{'passed':True}]*54},'release_version':driver.VERSION,'release_files':112,
            'release_sha256':driver.PINS['package_sha256'],'release_inventory_sha256':driver.PINS['package_inventory_sha256'],
            'canonical_rebuild_sha256':driver.PINS['canonical_package_sha256'],
            'canonical_reproducible_archive':True,'candidate_archive_rebuilt':False,
            'exact_candidate_bytes_installed':True,'candidate_payload_equals_canonical_payload':True,
            'candidate_compression_level':9,'canonical_compression_level':9,
            'candidate_source_commit':driver.PINS['candidate_source_commit'],
            'release_candidate_validation':True,
            'baseline_red':{'outcome':'passed','expected_failure_cases':14,'all_expected_regressions_observed':True,
                'cause_verified':True,'collection_errors':0,'skipped':0,'public_files_only_copy':True,
                'private_copy_removed':True,'fixed_source_unchanged':True,'provider_or_owner_accounts_used':False,
                'combined_red_green_deadline_seconds':900}}
        command=['jq','-e','--argjson','minimum','1732','--argjson','required','54',
            '--arg','candidate',driver.PINS['package_sha256'],'--arg','inventory',driver.PINS['package_inventory_sha256'],
            '--arg','canonical',driver.PINS['canonical_package_sha256'],'--arg','commit',driver.PINS['candidate_source_commit'],predicate]
        self.assertEqual(subprocess.run(command,input=json.dumps(value),text=True,capture_output=True).returncode,0)
        value['release_sha256']='0'*64
        self.assertNotEqual(subprocess.run(command,input=json.dumps(value),text=True,capture_output=True).returncode,0)


class TechnicalDependencyContracts(unittest.TestCase):
    def test_actual_versions_are_captured_and_any_wrong_target_version_refuses(self):
        expected = {"cryptography": "50.0.1", "srp": "1.0.22", "unicorn": "2.1.4"}
        with patch.object(driver.importlib.metadata, "version", side_effect=expected.__getitem__):
            self.assertEqual(driver.technical_versions(), expected)
        for name in expected:
            changed = {**expected, name: "0.0.0"}
            with patch.object(driver.importlib.metadata, "version", side_effect=changed.__getitem__), self.assertRaisesRegex(driver.Refused, "technical_dependency_version_refused"):
                driver.technical_versions()


class FullCollectionContracts(unittest.TestCase):
    setUp = DriverContracts.setUp
    xml = DriverContracts.xml

    def full_fixture(self):
        name = "test_regression_one[" + "x" * 65537 + "::suffix]"
        from xml.sax.saxutils import quoteattr
        xml = self.xml('<testcase classname="tests.test_one" name=' + quoteattr(name) + '/>'
                       '<testcase classname="tests.test_two" name="test_regression_two"/>')
        collection = self.root / "collection.json"
        value = {"schema": 1, "cases": [{"class": "tests.test_one", "name": name},
            {"class": "tests.test_two", "name": "test_regression_two"}], "deselected": 0}
        collection.write_text(json.dumps(value))
        expected = {("tests.test_one", "test_regression_one"), ("tests.test_two", "test_regression_two")}
        return xml, collection, value, expected

    def test_all_private_variants_match_exactly_and_public_result_omits_parameters(self):
        xml, collection, _, expected = self.full_fixture()
        with patch.object(driver, "PINS", self.config):
            result, _ = driver.backend_result(xml, collection=collection, expected=expected)
        self.assertEqual(result["collection"], {"collected_cases": 2, "declared_base_functions": 2,
            "deselected": 0, "exact_identities_match_junit": True, "raw_parameter_ids_exported": False})
        self.assertNotIn("x" * 100, json.dumps(result))
        self.assertNotIn("::suffix", json.dumps(result))

    def test_missing_duplicate_changed_long_identity_and_deselection_refuse(self):
        changes = [lambda value: value["cases"].pop(),
                   lambda value: value["cases"].append(value["cases"][0]),
                   lambda value: value["cases"][0].update(name=value["cases"][0]["name"][:-2] + "Y]"),
                   lambda value: value.update(deselected=1),
                   lambda value: value["cases"][0].update(name="test_regression_one[" + "x" * (128 * 1024) + "]")]
        for change in changes:
            xml, collection, value, expected = self.full_fixture()
            change(value); collection.write_text(json.dumps(value))
            with patch.object(driver, "PINS", self.config), self.assertRaises(driver.Refused):
                driver.backend_result(xml, collection=collection, expected=expected)

    def test_complete_frozen_ast_declares_testcase_methods_but_not_nested_helpers(self):
        files = {"tests/test_one.py": b"def test_direct(): pass\ndef helper():\n def test_nested(): pass\nclass Checks(unittest.TestCase):\n def test_method(self): pass\nclass Ordinary:\n def test_not_collected(self): pass\n"}
        self.assertEqual(driver.full_expected_functions(files),
            {("tests.test_one", "test_direct"), ("tests.test_one.Checks", "test_method")})

    def test_collection_probe_preserves_separator_inside_parameter_and_no_deselection(self):
        import sys
        from types import SimpleNamespace
        collection = self.root / "probe.json"
        def main(arguments, plugins):
            self.assertEqual(arguments, ["--junitxml", "private.xml"])
            probe = plugins[0]
            probe.pytest_collection_finish(SimpleNamespace(items=[SimpleNamespace(
                nodeid="tests/test_one.py::TestClass::test_case[synthetic::value]")]))
            return 0
        with patch.dict(sys.modules, {"pytest": SimpleNamespace(main=main)}), patch.object(driver, "constraints"):
            self.assertEqual(driver.full_pytest(str(collection), ["--junitxml", "private.xml"]), 0)
        self.assertEqual(json.loads(collection.read_bytes()), {"schema": 1, "deselected": 0,
            "cases": [{"class": "tests.test_one.TestClass", "name": "test_case[synthetic::value]"}]})
