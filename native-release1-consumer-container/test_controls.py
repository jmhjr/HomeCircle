"""Standalone refusal/continuity contracts; no Docker, real HA or native import."""

import asyncio
import ast
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from types import MappingProxyType, SimpleNamespace
import unittest
from unittest.mock import patch

import common as c
import driver
import guest
import process_probe

HERE = Path(__file__).resolve().parent


class Contracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = json.loads((HERE / "pins-current-amd64.json").read_bytes())

    def read_pins(self, values):
        path = self.root / "pins.json"
        path.write_text(json.dumps(values))
        return c.pins(path, c.sha(path.read_bytes()))

    def test_all_four_frozen_targets_and_controls_validate(self):
        for path in HERE.glob("pins-*.json"):
            values = c.pins(path, c.sha(path.read_bytes()))
            c.controls(HERE, values)
            self.assertEqual(
                values["image_repository"], "ghcr.io/home-assistant/home-assistant"
            )
            self.assertEqual(len(values["dependency_versions"]), 24)
            self.assertEqual(len(values["startup_versions"]), 21)

    def test_target_constraint_auth_cpu_and_unknown_scope_are_refused(self):
        for changes in (
            {"machine": "aarch64"},
            {"architecture": "emulated"},
            {"image_repository": "ghcr.io/home-assistant/qemux86-64-homeassistant"},
            {"schema": True},
            {"unknown": "PRIVATE-CANARY"},
            {"index_url": "https://private.invalid/simple"},
            {"extra_index_url": "https://private.invalid/simple"},
            {"constraints_sha256": "0" * 64},
            {
                "startup_versions": dict(
                    self.original["startup_versions"], pyotp="2.9.0"
                )
            },
        ):
            with self.subTest(changes=changes), self.assertRaises(c.Refused):
                self.read_pins(self.original | changes)

    def test_cache_argv_uses_only_both_fixed_sources_and_exact_pins(self):
        wanted = (
            self.original["dependency_versions"] | self.original["startup_versions"]
        )
        command = driver.cache_command(
            wanted,
            "/usr/local/bin/python",
            Path("/reviewed/core/package_constraints.txt"),
        )
        self.assertEqual(
            command[:16],
            [
                "uv",
                "pip",
                "install",
                "--no-config",
                "--prefix",
                "/config/deps",
                "--python",
                "/usr/local/bin/python",
                "--index-url",
                "https://pypi.org/simple",
                "--extra-index-url",
                "https://wheels.home-assistant.io/musllinux-index/",
                "--index-strategy",
                "unsafe-first-match",
                "--constraint",
                "/reviewed/core/package_constraints.txt",
            ],
        )
        self.assertEqual(len(command), 61)
        self.assertEqual(
            command[16:],
            sorted(name + "==" + version for name, version in wanted.items()),
        )
        self.assertEqual(
            [value for value in command if value.startswith("https://")],
            [
                "https://pypi.org/simple",
                "https://wheels.home-assistant.io/musllinux-index/",
            ],
        )

    def test_retargeted_cache_index_control_is_refused_before_execution(self):
        for name in self.original["controls"]:
            (self.root / name).write_bytes((HERE / name).read_bytes())
        c.controls(self.root, self.original)
        target = self.root / "driver.py"
        target.write_text(
            target.read_text().replace(
                "https://wheels.home-assistant.io/musllinux-index/",
                "https://private.invalid/simple",
            )
        )
        with self.assertRaisesRegex(c.Refused, "^input_hash_refused$"):
            c.controls(self.root, self.original)

    def test_hash_duplicate_pin_and_input_symlink_are_refused(self):
        path = self.root / "pins.json"
        path.write_text(json.dumps(self.original))
        with self.assertRaises(c.Refused):
            c.pins(path, "0" * 64)
        path.write_text(
            json.dumps(self.original).replace('"schema": 1', '"schema": 1, "schema": 1')
        )
        with self.assertRaises(c.Refused):
            c.pins(path, c.sha(path.read_bytes()))
        link = self.root / "link"
        link.symlink_to(path)
        with self.assertRaises(c.Refused):
            c.read(link)

    def test_exact_113_files_rejects_extra_changed_and_symlink(self):
        target = self.root / "homecircle"
        target.mkdir()
        inventory = {}
        for index in range(113):
            raw = str(index).encode()
            name = f"file{index}.py"
            (target / name).write_bytes(raw)
            inventory[name] = {"bytes": len(raw), "sha256": c.sha(raw)}
        c.installed(target, inventory)
        (target / "extra").write_text("PRIVATE-CANARY")
        with self.assertRaises(c.Refused):
            c.installed(target, inventory)
        (target / "extra").unlink()
        (target / "file0.py").write_text("changed")
        with self.assertRaises(c.Refused):
            c.installed(target, inventory)
        (target / "file0.py").unlink()
        (target / "file0.py").symlink_to(target / "file1.py")
        with self.assertRaises(c.Refused):
            c.installed(target, inventory)

    def test_real_core_command_does_not_count_controller_or_alternate_launcher(self):
        expected = ["python3", "-P", "-m", "homeassistant", "--config", "/config"]
        self.assertTrue(process_probe.is_core(expected))
        for command in (
            ["python3", "-I", "-B", "/config/control.py"],
            ["python3", "-m", "homeassistant", "--config", "/config"],
            expected + ["--skip-pip"],
            expected[:-1] + ["/owner/config"],
            ["sh", "-c", "python3 -P -m homeassistant"],
        ):
            self.assertFalse(process_probe.is_core(command))
        self.assertEqual(
            process_probe.command(
                b"python3\0-P\0-m\0homeassistant\0--config\0/config\0"
            ),
            expected,
        )

    def control_fixture(self, phase="restart", token="a" * 64):
        folder = self.root / c.CONTROL
        folder.mkdir(exist_ok=True)
        c.atomic(folder / "runtime-inputs.json", {"token": "a" * 64})
        c.atomic(folder / "phase.json", {"phase": "first", "token": "a" * 64})
        c.atomic(folder / "first-receipt.json", {"outcome": "passed"})
        c.atomic(
            folder / "restart-receipt.json",
            {
                "outcome": "passed",
                "phase": phase,
                "package_sha256": c.ARCHIVE,
                "target": "current-amd64",
                "token_sha256": c.sha(token.encode()),
            },
        )
        return folder

    def test_wait_for_restart_receipt_does_not_issue_restart_or_rewrite_phase(self):
        folder = self.control_fixture()
        before = (folder / "phase.json").read_bytes()
        with patch.object(driver, "Path", return_value=self.root):
            driver.control(
                c, self.original, SimpleNamespace(mode="wait", action="restart")
            )
        self.assertEqual((folder / "phase.json").read_bytes(), before)

    def test_stale_wrong_phase_or_foreign_receipt_is_refused(self):
        for phase, token in (("first", "a" * 64), ("restart", "b" * 64)):
            self.control_fixture(phase, token)
            with (
                patch.object(driver, "Path", return_value=self.root),
                self.assertRaises(c.Refused),
            ):
                driver.control(
                    c, self.original, SimpleNamespace(mode="wait", action="restart")
                )

    def test_private_restart_control_requires_first_and_writes_only_fixed_phase(self):
        folder = self.control_fixture()
        with patch.object(driver, "Path", return_value=self.root):
            driver.control(
                c, self.original, SimpleNamespace(mode="restart", action="restart")
            )
        self.assertEqual(
            json.loads((folder / "phase.json").read_bytes()),
            {"phase": "restart", "token": "a" * 64},
        )
        (folder / "first-receipt.json").unlink()
        with (
            patch.object(driver, "Path", return_value=self.root),
            self.assertRaises(c.Refused),
        ):
            driver.control(
                c, self.original, SimpleNamespace(mode="restart", action="restart")
            )

    def test_saved_settings_and_explicit_sources_are_part_of_identity(self):
        entry = SimpleNamespace(
            entry_id="synthetic",
            unique_id=None,
            version=1,
            minor_version=1,
            data=MappingProxyType(
                {
                    "people": ["person.example"],
                    "members": {
                        "person.example": {"trackers": ["device_tracker.example"]}
                    },
                }
            ),
            options=MappingProxyType({"city_lookup_enabled": False}),
        )
        first = guest.identity(entry)
        self.assertEqual(first["options"], {"city_lookup_enabled": False})
        entry.options = MappingProxyType({"city_lookup_enabled": True})
        self.assertNotEqual(first, guest.identity(entry))
        entry.data = MappingProxyType({"members": {"person.example": {"trackers": []}}})
        self.assertNotEqual(first["data"], guest.identity(entry)["data"])

    def test_fixed_failure_code_survives_but_private_exception_text_does_not(self):
        known = c.safe_failure(c.Refused("consumer_phase_receipt_refused"), HERE)
        self.assertEqual(known["failure_code"], "consumer_phase_receipt_refused")
        for error in (
            c.Refused("PRIVATE-CANARY /owner/private"),
            RuntimeError("PRIVATE-CANARY"),
            OSError("PRIVATE-CANARY"),
        ):
            result = c.safe_failure(error, HERE)
            self.assertNotIn("failure_code", result)
            self.assertNotIn("PRIVATE-CANARY", json.dumps(result))

    def test_support_fixed_failure_catalog_is_hash_bound(self):
        support = c.load(
            "consumer_diagnostic_support", HERE / "package_support.py", c.SUPPORT
        )
        value = c.safe_failure(
            support.Refused("owned_child_descendants_not_reaped"), HERE
        )
        self.assertEqual(value["failure_code"], "owned_child_descendants_not_reaped")
        for message in ("PRIVATE-CANARY /owner/private", "bare_private_canary"):
            value = c.safe_failure(support.Refused(message), HERE)
            self.assertNotIn("failure_code", value)
            self.assertNotIn(message, json.dumps(value))
        for name in (
            "common.py",
            "driver.py",
            "guest.py",
            "process_probe.py",
            "package_support.py",
        ):
            (self.root / name).write_bytes((HERE / name).read_bytes())
        with (self.root / "package_support.py").open("ab") as output:
            output.write(b'\nraise RuntimeError("bare_private_canary")\n')
        with self.assertRaisesRegex(c.Refused, "^input_hash_refused$"):
            c.safe_failure(support.Refused("bare_private_canary"), self.root)
        (self.root / "package_support.py").unlink()
        value = c.safe_failure(c.Refused("consumer_phase_receipt_refused"), self.root)
        self.assertEqual(value["failure_code"], "consumer_phase_receipt_refused")

    def test_setup_stage_projection_requires_exact_fixed_catalog(self):
        value = c.safe_failure(
            RuntimeError("PRIVATE-CANARY"), HERE, setup_stage="cache_install"
        )
        self.assertEqual(value["setup_stage"], "cache_install")
        self.assertNotIn("PRIVATE-CANARY", json.dumps(value))
        for stage in (
            "bare_private_canary",
            "cache_install/PRIVATE-CANARY",
            {"private": "canary"},
            None,
        ):
            value = c.safe_failure(
                RuntimeError("PRIVATE-CANARY"), HERE, setup_stage=stage
            )
            self.assertNotIn("setup_stage", value)
            self.assertNotIn("canary", json.dumps(value).lower())

    def test_actual_main_retains_setup_stage_and_support_label(self):
        support = c.load(
            "consumer_diagnostic_wire_support", HERE / "package_support.py", c.SUPPORT
        )

        def fail(_common, _values, args):
            args.setup_stage = "cache_install"
            raise support.Refused("owned_child_descendants_not_reaped")

        with (
            patch.object(driver, "bootstrap", return_value=(c, self.original)),
            patch.object(driver, "setup", side_effect=fail),
            patch.object(
                driver.sys,
                "argv",
                ["driver", "setup", "--pins", "synthetic", "--pins-sha", "a" * 64],
            ),
            patch.object(driver.sys, "platform", "linux"),
            patch.object(driver.platform, "machine", return_value="x86_64"),
            patch.object(c, "atomic") as saved,
            self.assertRaises(support.Refused),
        ):
            driver.main()
        self.assertEqual(saved.call_args.args[1]["setup_stage"], "cache_install")
        self.assertEqual(
            saved.call_args.args[1]["failure_code"],
            "owned_child_descendants_not_reaped",
        )

    def test_guest_has_no_new_core_instance_import_path_or_alternate_service(self):
        source = (HERE / "guest.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, {"HomeAssistant", "exec", "eval"})
        self.assertNotIn("sys.path.insert", source)
        self.assertNotIn("async_from_config_dict", source)
        self.assertIn('"http://127.0.0.1:18123"', source)

    def test_launcher_retains_original_service_and_exact_owned_volume_boundary(self):
        source = (HERE / "run_host.sh").read_text()
        consumer = source.split("consumer_id=$(call create", 1)[1].split("\n", 1)[0]
        self.assertNotIn("--entrypoint", consumer)
        self.assertTrue(consumer.endswith('"$image_id")'))
        self.assertNotIn("--init", consumer)
        preparer = next(
            line
            for line in source.splitlines()
            if line.startswith("prep_id=$(call create")
        )
        self.assertIn("--init --entrypoint /bin/sh", preparer)
        for required in (
            "--network none",
            '"type=volume,source=$volume,target=/config"',
            ".Mounts|length)==1",
            '.Mounts[0].Type=="volume"',
            ".Mounts[0].Name==$volume",
            '.Config.Labels["io.homecircle.consumer-witness"]==$token',
            "network disconnect bridge",
            "stop --time 260",
            ".State.ExitCode==0",
            "deadline=$((SECONDS + 2100))",
            'volume rm "$volume"',
            "private_workspace_removed",
        ):
            self.assertIn(required, source)
        for forbidden in (
            "--privileged",
            "--network host",
            "--pid host",
            "--volume /",
            "docker build",
            "docker commit",
            "pytest",
            "PYTHONPATH=",
        ):
            self.assertNotIn(forbidden, source)


class DistributionContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = json.loads((HERE / "pins-current-amd64.json").read_bytes())

    @staticmethod
    def guest_function(name, namespace):
        tree = ast.parse((HERE / "guest.py").read_bytes())
        node = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == name
        )
        exec(
            compile(
                ast.Module(body=[node], type_ignores=[]),
                "actual-guest-function",
                "exec",
            ),
            namespace,
        )
        return namespace[name]

    def test_numeric_distribution_version_projection_excludes_private_text(self):
        wanted = (
            self.original["dependency_versions"] | self.original["startup_versions"]
        )
        for version in wanted.values():
            self.assertEqual(guest.public_distribution_version(version), version)
        for canary in (
            "PRIVATE-CANARY /owner/private",
            "bare_private_canary",
            "1.0+private.canary",
            "1.0rc1",
            "1",
            "1.2.3.4.5",
            "123456789.1",
            "1.2\nPRIVATE-CANARY",
            "",
            None,
            True,
            {"PRIVATE-CANARY": "body"},
        ):
            with self.subTest(canary=canary):
                self.assertEqual(
                    guest.public_distribution_version(canary), "unavailable"
                )

    def test_distribution_projection_exact_paths_order_and_index_bounds(self):
        cache = Path("/config/deps/lib/python3.14/site-packages")
        system = Path("/usr/local/lib/python3.14/site-packages")
        fields = {
            "sorted_package_index",
            "observed_version",
            "expected_version_matches",
            "origin",
            "cache_precedes_system",
            "system_precedes_cache",
        }
        for origin, path in (
            ("cache", cache),
            ("system", system),
            ("other", Path("/owner/PRIVATE-CANARY")),
        ):
            distribution = SimpleNamespace(
                version="1.0+private.canary", locate_file=lambda _name, path=path: path
            )
            value = guest.distribution_failure(
                44, "1.0", distribution, cache, [str(cache), str(system)]
            )
            self.assertEqual(set(value), fields)
            self.assertEqual(value["origin"], origin)
            self.assertEqual(value["observed_version"], "unavailable")
            self.assertFalse(value["expected_version_matches"])
            self.assertTrue(value["cache_precedes_system"])
            self.assertFalse(value["system_precedes_cache"])
            self.assertNotIn("private", json.dumps(value).lower())
            self.assertNotIn("/owner", json.dumps(value))
        missing = guest.distribution_failure(
            0, "1.0", None, cache, [str(system), str(cache)]
        )
        self.assertEqual(missing["origin"], "missing")
        self.assertTrue(missing["system_precedes_cache"])
        self.assertFalse(missing["cache_precedes_system"])
        absent = guest.distribution_failure(0, "1.0", None, cache, [str(cache)])
        self.assertFalse(absent["system_precedes_cache"])
        self.assertFalse(absent["cache_precedes_system"])
        for index in (-1, 45, True, "0", None, 2.0):
            with (
                self.subTest(index=index),
                self.assertRaisesRegex(
                    RuntimeError, "^distribution_diagnostic_index_refused$"
                ),
            ):
                guest.distribution_failure(index, "1.0", None, cache, [])

    def test_actual_cached_origin_predicate_refuses_system_other_stale_missing(self):
        cache = Path("/config/deps/lib/python3.14/site-packages")
        system = Path("/usr/local/lib/python3.14/site-packages")
        versions = (
            self.original["dependency_versions"] | self.original["startup_versions"]
        )
        names = sorted(versions)
        index = 11
        bad_name = names[index]
        for case in ("all_cache", "system", "other", "stale", "missing"):
            called = []
            diagnostic = {}

            def distribution(name):
                called.append(name)
                if name == bad_name and case == "missing":
                    raise LookupError("PRIVATE-CANARY")
                path = (
                    system
                    if name == bad_name and case == "system"
                    else Path("/owner/PRIVATE-CANARY")
                    if name == bad_name and case == "other"
                    else cache
                )
                version = (
                    "999.1" if name == bad_name and case == "stale" else versions[name]
                )
                return SimpleNamespace(version=version, locate_file=lambda _name: path)

            namespace = {
                "Path": Path,
                "runtime": {"cache_site": str(cache)},
                "control": Path("/config/.homecircle-consumer-qa"),
                "versions": versions,
                "sys": SimpleNamespace(path=[str(cache), str(system)]),
                "c": c,
                "distribution_check": diagnostic,
                "distribution_failure": guest.distribution_failure,
                "importlib": SimpleNamespace(
                    metadata=SimpleNamespace(
                        distribution=distribution, PackageNotFoundError=LookupError
                    )
                ),
            }
            actual = self.guest_function("cached_origins", namespace)
            with self.subTest(case=case):
                if case == "all_cache":
                    actual()
                    self.assertEqual(called, names)
                    self.assertEqual(diagnostic, {})
                else:
                    error = LookupError if case == "missing" else c.Refused
                    with self.assertRaises(error):
                        actual()
                    self.assertEqual(called, names[: index + 1])
                    self.assertEqual(diagnostic["sorted_package_index"], index)
                    self.assertEqual(
                        diagnostic["origin"], "cache" if case == "stale" else case
                    )
                    self.assertEqual(
                        diagnostic["expected_version_matches"],
                        case in {"system", "other"},
                    )
                    self.assertNotIn("PRIVATE-CANARY", json.dumps(diagnostic))

    def test_actual_cache_presence_gate_and_predicate_are_unchanged(self):
        tree = ast.parse((HERE / "guest.py").read_bytes())
        checks = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and len(node.args) == 2
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value == "guest_cached_distribution_origin_refused"
        ]
        self.assertEqual(len(checks), 1)
        expected = ast.parse(
            'distribution.version == expected and Path(distribution.locate_file("")).resolve() == cache',
            mode="eval",
        ).body
        self.assertEqual(ast.dump(checks[0].args[0]), ast.dump(expected))
        namespace = {
            "Path": Path,
            "runtime": {"cache_site": "/config/deps/lib/python3.14/site-packages"},
            "control": Path("/config/.homecircle-consumer-qa"),
            "sys": SimpleNamespace(path=[]),
            "c": c,
            "distribution_check": {},
        }
        actual = self.guest_function("cached_origins", namespace)
        with self.assertRaisesRegex(c.Refused, "^normal_config_cache_not_mounted$"):
            actual()
        self.assertEqual(namespace["distribution_check"], {})

    def test_guest_failure_retains_only_bounded_distribution_diagnostic(self):
        for name in (
            "common.py",
            "driver.py",
            "guest.py",
            "process_probe.py",
            "package_support.py",
        ):
            (self.root / name).write_bytes((HERE / name).read_bytes())
        cache = Path("/config/deps/lib/python3.14/site-packages")
        projected = guest.distribution_failure(
            3,
            "1.0",
            SimpleNamespace(
                version="1.0+private.canary",
                locate_file=lambda _name: "/owner/PRIVATE-CANARY",
            ),
            cache,
            [str(cache)],
        )

        async def exercise():
            raise c.Refused("guest_cached_distribution_origin_refused")

        async def execute(function, *args):
            return function(*args)

        namespace = {
            "asyncio": asyncio,
            "hass": SimpleNamespace(async_add_executor_job=execute),
            "c": c,
            "control": self.root,
            "distribution_check": projected,
            "exercise": exercise,
        }
        actual = self.guest_function("run", namespace)
        asyncio.run(actual())
        raw = (self.root / "guest-failure.json").read_text()
        value = json.loads(raw)
        self.assertEqual(
            set(value),
            {"schema", "outcome", "failure_type", "failure_code", "distribution_check"},
        )
        self.assertEqual(
            value["failure_code"], "guest_cached_distribution_origin_refused"
        )
        self.assertEqual(value["distribution_check"], projected)
        self.assertNotIn("private", raw.lower())
        self.assertNotIn("/owner", raw)


class AsyncContracts(unittest.IsolatedAsyncioTestCase):
    async def test_guest_wait_awaits_async_predicates_and_propagates_cancellation(self):
        calls = []

        async def predicate():
            calls.append(True)
            return True

        await guest.wait(predicate)
        self.assertEqual(calls, [True])
        task = asyncio.create_task(guest.wait(lambda: False))
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task

    async def test_guest_wait_has_fixed_deadline(self):
        with self.assertRaisesRegex(RuntimeError, "^guest_condition_deadline$"):
            await guest.wait(lambda: False, limit=0)


@unittest.skipUnless(sys.platform == "linux", "actual Linux subreaper/pidfd probe")
class LinuxOwnedChildContracts(unittest.TestCase):
    def probe(self, command, *, command_seconds=1, drain_seconds=0.2, owned_note=None):
        code = (
            "import importlib.util,json,sys; "
            "s=importlib.util.spec_from_file_location('owned_cache_child',sys.argv[1]); "
            "m=importlib.util.module_from_spec(s);s.loader.exec_module(m); "
            "v=m.run(json.loads(sys.argv[2]),command_seconds=float(sys.argv[3]),"
            "drain_seconds=float(sys.argv[4]),cleanup_seconds=0.5); "
            "print(json.dumps(v,sort_keys=True))"
        )
        process = subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-B",
                "-c",
                code,
                str(HERE / "cache_child.py"),
                json.dumps(command),
                str(command_seconds),
                str(drain_seconds),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        undrained_escaped = False
        try:
            output, error = process.communicate(timeout=5)
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate(timeout=2)
            if owned_note is not None and owned_note.exists():
                identity = json.loads(owned_note.read_text())
                descriptor = None
                try:
                    descriptor = os.pidfd_open(identity["pid"])
                    fields = (
                        Path(f"/proc/{identity['pid']}/stat")
                        .read_text()
                        .rsplit(")", 1)[1]
                        .split()
                    )
                    if int(fields[19]) == identity["start_ticks"]:
                        undrained_escaped = True
                        signal.pidfd_send_signal(descriptor, signal.SIGKILL)
                except (ProcessLookupError, FileNotFoundError):
                    pass
                finally:
                    if descriptor is not None:
                        os.close(descriptor)
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                pass
            else:
                os.killpg(process.pid, signal.SIGKILL)
                self.fail("owned synthetic process group was not drained")
            self.assertFalse(
                undrained_escaped, "owned escaped synthetic child was not drained"
            )
        self.assertEqual(process.returncode, 0, "synthetic wrapper process failed")
        self.assertEqual(error, b"")
        value = json.loads(output)
        self.assertEqual(value["stage"], "cache_install")
        self.assertTrue(value["subreaper_verified"])
        self.assertTrue(value["owned_descendants_drained"])
        return value

    def test_linux_primary_success_has_no_remaining_children(self):
        value = self.probe([sys.executable, "-c", "pass"])
        self.assertEqual(value["outcome"], "passed")
        self.assertEqual(value["primary_exit_code"], 0)
        self.assertEqual(value["adopted_children_reaped"], 0)

    def test_linux_exited_orphan_is_adopted_and_reaped_before_success(self):
        value = self.probe([sys.executable, "-c", "import os; os.fork(); os._exit(0)"])
        self.assertEqual(value["outcome"], "passed")
        self.assertGreaterEqual(value["adopted_children_reaped"], 1)

    def test_linux_transient_live_orphan_drains_before_success(self):
        code = "import os,time; child=os.fork(); time.sleep(0.05) if child==0 else None; os._exit(0)"
        value = self.probe([sys.executable, "-c", code])
        self.assertEqual(value["outcome"], "passed")
        self.assertGreaterEqual(value["adopted_children_reaped"], 1)

    def test_linux_escaped_persistent_owned_child_is_reaped_and_still_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            note = Path(temporary) / "owned-child.json"
            code = (
                "import json,os,pathlib,signal,sys,time\n"
                "child=os.fork()\n"
                "if child==0:\n"
                " os.setsid()\n"
                " signal.signal(signal.SIGTERM,signal.SIG_IGN)\n"
                " fields=pathlib.Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()\n"
                " note=pathlib.Path(sys.argv[1]); temporary=note.with_suffix('.tmp')\n"
                " temporary.write_text(json.dumps({'pid':os.getpid(),'start_ticks':int(fields[19])})); os.replace(temporary,note)\n"
                " time.sleep(30)\n"
                "else:\n"
                " while not pathlib.Path(sys.argv[1]).exists(): time.sleep(0.01)\n"
                "os._exit(0)\n"
            )
            value = self.probe(
                [sys.executable, "-c", code, str(note)],
                drain_seconds=0.05,
                owned_note=note,
            )
        self.assertEqual(value["outcome"], "failed")
        self.assertTrue(value["descendant_deadline_exceeded"])
        self.assertGreaterEqual(value["adopted_children_reaped"], 1)

    def test_linux_primary_failure_remains_failed(self):
        value = self.probe([sys.executable, "-c", "raise SystemExit(7)"])
        self.assertEqual(value["outcome"], "failed")
        self.assertEqual(value["primary_exit_code"], 7)

    def test_linux_primary_deadline_drains_owned_child_and_remains_failed(self):
        code = "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(30)"
        value = self.probe([sys.executable, "-c", code], command_seconds=0.05)
        self.assertEqual(value["outcome"], "failed")
        self.assertTrue(value["primary_timed_out"])

    def test_linux_child_argv_is_preserved_exactly(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "argv.json"
            code = "import json,pathlib,sys; pathlib.Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:]))"
            arguments = ["two words", "--literal", "synthetic/only"]
            value = self.probe([sys.executable, "-c", code, str(target), *arguments])
            self.assertEqual(value["outcome"], "passed")
            self.assertEqual(json.loads(target.read_text()), arguments)


if __name__ == "__main__":
    unittest.main()
