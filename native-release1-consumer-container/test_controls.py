"""Standalone refusal/continuity contracts; no Docker, real HA or native import."""

import asyncio
import ast
import json
from pathlib import Path
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
            {"constraints_sha256": "0" * 64},
            {
                "startup_versions": dict(
                    self.original["startup_versions"], pyotp="2.9.0"
                )
            },
        ):
            with self.subTest(changes=changes), self.assertRaises(c.Refused):
                self.read_pins(self.original | changes)

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


if __name__ == "__main__":
    unittest.main()
