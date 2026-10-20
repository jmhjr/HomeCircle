"""Standalone refusal/continuity contracts; no Docker, real HA or native import."""

import asyncio
import ast
import json
import logging
import re
import shutil
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

    def test_actual_resolved_origins_allow_exact_pinned_cache_system_and_mixed(self):
        cache = Path("/config/deps/lib/python3.14/site-packages")
        system = Path("/usr/local/lib/python3.14/site-packages")
        versions = (
            self.original["dependency_versions"] | self.original["startup_versions"]
        )
        names = sorted(versions)
        index = 11
        bad_name = names[index]
        for case in (
            "all_cache",
            "all_system",
            "mixed",
            "other",
            "stale",
            "stale_system",
            "missing",
        ):
            called = []
            diagnostic = {}

            def distribution(name):
                called.append(name)
                if name == bad_name and case == "missing":
                    raise LookupError("PRIVATE-CANARY")
                path = (
                    system
                    if case == "all_system"
                    or (case in {"mixed", "stale_system"} and name == bad_name)
                    else Path("/owner/PRIVATE-CANARY")
                    if name == bad_name and case == "other"
                    else cache
                )
                version = (
                    "999.1"
                    if name == bad_name and case in {"stale", "stale_system"}
                    else versions[name]
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
            actual = self.guest_function("resolved_origins", namespace)
            with self.subTest(case=case):
                if case in {"all_cache", "all_system", "mixed"}:
                    counts = actual()
                    self.assertEqual(called, names)
                    self.assertEqual(diagnostic, {})
                    self.assertEqual(set(counts), {"cache", "system"})
                    self.assertEqual(sum(counts.values()), 45)
                    self.assertEqual(
                        counts["system"],
                        45 if case == "all_system" else 1 if case == "mixed" else 0,
                    )
                else:
                    error = LookupError if case == "missing" else c.Refused
                    with self.assertRaises(error):
                        actual()
                    self.assertEqual(called, names[: index + 1])
                    self.assertEqual(diagnostic["sorted_package_index"], index)
                    self.assertEqual(
                        diagnostic["origin"],
                        "cache"
                        if case == "stale"
                        else "system"
                        if case == "stale_system"
                        else case,
                    )
                    self.assertEqual(
                        diagnostic["expected_version_matches"],
                        case == "other",
                    )
                    self.assertNotIn("PRIVATE-CANARY", json.dumps(diagnostic))

    def test_actual_cache_presence_gate_and_corrected_predicate_are_exact(self):
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
            'distribution.version == expected and (origin := Path(distribution.locate_file("")).resolve()) in {cache, system}',
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
        actual = self.guest_function("resolved_origins", namespace)
        with self.assertRaisesRegex(c.Refused, "^normal_config_cache_not_mounted$"):
            actual()
        self.assertEqual(namespace["distribution_check"], {})

    def test_resolved_metadata_roots_follow_symlinks_but_refuse_foreign_targets(self):
        control = self.root.resolve() / "config/.homecircle-consumer-qa"
        cache = control.parent / "deps/lib/python3.14/site-packages"
        cache.mkdir(parents=True)
        system = Path("/usr/local/lib/python3.14/site-packages")
        foreign = self.root / "PRIVATE-CANARY"
        foreign.mkdir()
        aliases = {
            "cache": self.root / "cache-alias",
            "system": self.root / "system-alias",
            "foreign": cache / "foreign-alias",
        }
        for name, target in (
            ("cache", cache),
            ("system", system),
            ("foreign", foreign),
        ):
            aliases[name].symlink_to(target, target_is_directory=True)
        versions = (
            self.original["dependency_versions"] | self.original["startup_versions"]
        )
        first = sorted(versions)[0]
        for kind, alias in aliases.items():
            diagnostic = {}

            def distribution(name):
                return SimpleNamespace(
                    version=versions[name],
                    locate_file=lambda _name: alias if name == first else cache,
                )

            namespace = {
                "Path": Path,
                "runtime": {"cache_site": str(cache)},
                "control": control,
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
            actual = self.guest_function("resolved_origins", namespace)
            with self.subTest(kind=kind):
                if kind == "foreign":
                    with self.assertRaises(c.Refused):
                        actual()
                    self.assertEqual(diagnostic["origin"], "other")
                    self.assertEqual(diagnostic["sorted_package_index"], 0)
                    self.assertNotIn("PRIVATE-CANARY", json.dumps(diagnostic))
                else:
                    counts = actual()
                    self.assertEqual(
                        counts,
                        {
                            "cache": 44 if kind == "system" else 45,
                            "system": 1 if kind == "system" else 0,
                        },
                    )
                    self.assertEqual(diagnostic, {})

    def test_success_receipt_reports_resolved_counts_without_requiring_a_mix(self):
        tree = ast.parse((HERE / "guest.py").read_bytes())
        receipt = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Dict)
            and any(
                isinstance(key, ast.Constant)
                and key.value == "resolved_distributions_origin_checked"
                for key in node.keys
            )
        )
        for counts in (
            {"cache": 45, "system": 0},
            {"cache": 0, "system": 45},
            {"cache": 7, "system": 38},
        ):
            namespace = {
                "c": c,
                "values": self.original,
                "phase": "first",
                "runtime": {"token": "synthetic"},
                "versions": self.original["dependency_versions"]
                | self.original["startup_versions"],
                "origin_counts": counts,
                "inventory": {"frontend/homecircle-card.js": {"sha256": "0" * 64}},
                "snapshot": {"synthetic": True},
            }
            actual = eval(
                compile(ast.Expression(body=receipt), "actual-guest-receipt", "eval"),
                namespace,
            )
            self.assertNotIn("cached_distributions_origin_checked", actual)
            self.assertEqual(actual["resolved_distributions_origin_checked"], 45)
            self.assertEqual(actual["resolved_distributions_origin_counts"], counts)
            self.assertEqual(
                sum(actual["resolved_distributions_origin_counts"].values()), 45
            )

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


# Exact process_ha_config_upgrade AST extracted from both pinned config.py files.
# NumericVersionFixture only models the fixed numeric fixture comparisons; it
# does not import HA or replace the real Core version parser during acceptance.
CORE_UPGRADE_SOURCE = 'def process_ha_config_upgrade(hass: HomeAssistant) -> None:\n    """Upgrade configuration if necessary.\n\n    This method needs to run in an executor.\n    """\n    version_path = hass.config.path(VERSION_FILE)\n\n    try:\n        with open(version_path, encoding="utf8") as inp:\n            conf_version = inp.readline().strip()\n    except FileNotFoundError:\n        # Last version to not have this file\n        conf_version = "0.7.7"\n\n    if conf_version == __version__:\n        return\n\n    _LOGGER.info(\n        "Upgrading configuration directory from %s to %s", conf_version, __version__\n    )\n\n    version_obj = AwesomeVersion(conf_version)\n\n    if version_obj < AwesomeVersion("0.50"):\n        # 0.50 introduced persistent deps dir.\n        lib_path = hass.config.path("deps")\n        if os.path.isdir(lib_path):\n            shutil.rmtree(lib_path)\n\n    if version_obj < AwesomeVersion("0.92"):\n        # 0.92 moved google/tts.py to google_translate/tts.py\n        config_path = hass.config.path(YAML_CONFIG_FILE)\n\n        with open(config_path, encoding="utf-8") as config_file:\n            config_raw = config_file.read()\n\n        if TTS_PRE_92 in config_raw:\n            _LOGGER.info("Migrating google tts to google_translate tts")\n            config_raw = config_raw.replace(TTS_PRE_92, TTS_92)\n            try:\n                with open(config_path, "w", encoding="utf-8") as config_file:\n                    config_file.write(config_raw)\n            except OSError:\n                _LOGGER.exception("Migrating to google_translate tts failed")\n\n    if version_obj < AwesomeVersion("0.94") and is_docker_env():\n        # In 0.94 we no longer install packages inside the deps folder when\n        # running inside a Docker container.\n        lib_path = hass.config.path("deps")\n        if os.path.isdir(lib_path):\n            shutil.rmtree(lib_path)\n\n    with open(version_path, "w", encoding="utf8") as outp:\n        outp.write(__version__)\n'
CORE_CONFIG_SHA256 = {
    "2026.10.2": "c196cf81792f2d8d998b2595ff9d5d3ed8be3628327dde1d4720860c4f3bba2b",
    "2026.9.4": "7f62be48f6030f63abc59c73afbbf69f6d4c6dda2a081f60e6382554e9c53d35",
}


class NumericVersionFixture:
    def __init__(self, value):
        if re.fullmatch(r"[0-9]+(?:\.[0-9]+)+", value) is None:
            raise ValueError("numeric_fixture_only")
        self.parts = tuple(int(part) for part in value.split("."))

    def __lt__(self, other):
        return self.parts < other.parts


class ConfigMarkerContracts(unittest.TestCase):
    def upgrade(self, root, target):
        tree = ast.parse(CORE_UPGRADE_SOURCE)
        self.assertEqual(
            c.sha(CORE_UPGRADE_SOURCE.encode()),
            "6ba6c3754ec05aa0b5d304513ee638e23555cbcb4adfb0dc8fc61cbf73bf0cd1",
        )
        namespace = {
            "HomeAssistant": SimpleNamespace,
            "VERSION_FILE": ".HA_VERSION",
            "YAML_CONFIG_FILE": "configuration.yaml",
            "__version__": target,
            "_LOGGER": logging.getLogger("consumer_config_fixture"),
            "AwesomeVersion": NumericVersionFixture,
            "os": os,
            "shutil": shutil,
            "is_docker_env": lambda: True,
            "TTS_PRE_92": "unused_numeric_fixture_tts",
            "TTS_92": "unused_numeric_fixture_replacement",
        }
        exec(compile(tree, "exact_pinned_Core_config_upgrade", "exec"), namespace)
        namespace["process_ha_config_upgrade"](
            SimpleNamespace(config=SimpleNamespace(path=lambda name: str(root / name)))
        )

    def config(self, root):
        (root / "configuration.yaml").write_text("homeassistant: {}\n")
        cache = root / "deps/lib/python3.14/site-packages"
        cache.mkdir(parents=True)
        sentinel = cache / "synthetic-metadata-sentinel"
        sentinel.write_text("prepared-cache")
        return sentinel

    def test_actual_upgrade_missing_marker_removes_prepared_cache_at_both_targets(self):
        for target in CORE_CONFIG_SHA256:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                sentinel = self.config(root)
                self.upgrade(root, target)
                self.assertFalse(sentinel.exists())
                self.assertEqual((root / ".HA_VERSION").read_text(), target)

    def test_actual_upgrade_old_docker_marker_removes_cache_at_both_targets(self):
        for target in CORE_CONFIG_SHA256:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                sentinel = self.config(root)
                # 0.93 skips the pre-0.50 branch and takes Docker's pre-0.94 branch.
                (root / ".HA_VERSION").write_text("0.93")
                self.upgrade(root, target)
                self.assertFalse(sentinel.exists())
                self.assertEqual((root / ".HA_VERSION").read_text(), target)

    def test_exact_new_marker_readback_preserves_cache_on_first_and_restart_upgrade(
        self,
    ):
        for target in CORE_CONFIG_SHA256:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                sentinel = self.config(root)
                driver.seed_config_version(c, root, target)
                for _ in range(2):
                    self.upgrade(root, target)
                    self.assertEqual(sentinel.read_text(), "prepared-cache")
                    self.assertEqual((root / ".HA_VERSION").read_text(), target)

    def test_marker_seed_refuses_existing_stale_future_private_symlink_and_unknown_target(
        self,
    ):
        for existing in ("2026.10.2", "0.93", "2099.1.0", "PRIVATE-CANARY"):
            with (
                self.subTest(existing=existing),
                tempfile.TemporaryDirectory() as folder,
            ):
                root = Path(folder)
                marker = root / ".HA_VERSION"
                marker.write_text(existing)
                with self.assertRaisesRegex(
                    c.Refused, "^prepared_config_version_refused$"
                ):
                    driver.seed_config_version(c, root, "2026.10.2")
                self.assertEqual(marker.read_text(), existing)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            foreign = root / "foreign"
            foreign.write_text("PRIVATE-CANARY")
            (root / ".HA_VERSION").symlink_to(foreign)
            with self.assertRaisesRegex(c.Refused, "^prepared_config_version_refused$"):
                driver.seed_config_version(c, root, "2026.10.2")
            self.assertEqual(foreign.read_text(), "PRIVATE-CANARY")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaisesRegex(c.Refused, "^prepared_config_version_refused$"):
                driver.seed_config_version(c, root, "2099.1.0")
            self.assertEqual(list(root.iterdir()), [])

    def test_exact_endpoint_config_source_pin_is_bound_and_retargeting_refused(self):
        for path in HERE.glob("pins-*.json"):
            original = c.pins(path, c.sha(path.read_bytes()))
            self.assertEqual(
                original["startup_sources"]["config.py"],
                CORE_CONFIG_SHA256[original["core"]],
            )
            self.assertEqual(len(original["startup_sources"]), 6)
            original["startup_sources"]["config.py"] = "0" * 64
            with tempfile.TemporaryDirectory() as folder:
                altered = Path(folder) / "pins.json"
                altered.write_text(json.dumps(original))
                with self.assertRaisesRegex(
                    c.Refused, "^endpoint_requirement_pin_refused$"
                ):
                    c.pins(altered, c.sha(altered.read_bytes()))

    def test_actual_setup_seeds_before_cache_install_and_only_reports_after_readback(
        self,
    ):
        tree = ast.parse((HERE / "driver.py").read_bytes())
        setup = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "setup"
        )
        calls = [node for node in ast.walk(setup) if isinstance(node, ast.Call)]
        seed = [
            node
            for node in calls
            if isinstance(node.func, ast.Name) and node.func.id == "seed_config_version"
        ]
        cache = [
            node
            for node in calls
            if isinstance(node.func, ast.Name) and node.func.id == "cache_command"
        ]
        self.assertEqual(len(seed), 1)
        self.assertEqual(
            ast.unparse(seed[0]), "seed_config_version(c, config, values['core'])"
        )
        self.assertEqual(len(cache), 1)
        self.assertLess(seed[0].lineno, cache[0].lineno)
        marker_receipts = [
            node
            for node in ast.walk(setup)
            if isinstance(node, ast.Dict)
            and any(
                isinstance(key, ast.Constant)
                and key.value == "prepared_config_version_verified"
                for key in node.keys
            )
        ]
        self.assertEqual(len(marker_receipts), 1)
        self.assertGreater(marker_receipts[0].lineno, cache[0].lineno)


if __name__ == "__main__":
    unittest.main()
