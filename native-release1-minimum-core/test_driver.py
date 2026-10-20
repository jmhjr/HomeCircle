"""Standalone refusal and scope contracts: no HA, Docker, native or account runtime."""

import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import driver


class MinimumCoreContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pins = {
            "schema": 1,
            "architecture": "amd64",
            "machine": "x86_64",
            "image_repository": "ghcr.io/home-assistant/qemux86-64-homeassistant",
            "image_digest": "sha256:" + "a" * 64,
            "image_id": "sha256:" + "b" * 64,
            "driver_sha256": driver.sha(Path(driver.__file__).read_bytes()),
            "requirements_support_sha256": "c" * 64,
        }

    def config(self, values=None):
        raw = json.dumps(self.pins if values is None else values).encode()
        path = self.root / "pins.json"
        path.write_bytes(raw)
        return driver.configuration(path, driver.sha(raw))

    def test_architecture_mapping_is_explicit_and_native(self):
        self.assertEqual(self.config()["machine"], "x86_64")
        arm = dict(
            self.pins,
            architecture="arm64",
            machine="aarch64",
            image_repository="ghcr.io/home-assistant/qemuarm-64-homeassistant",
        )
        self.assertEqual(self.config(arm)["architecture"], "arm64")
        for values in (
            dict(self.pins, machine="aarch64"),
            dict(self.pins, architecture="emulated"),
        ):
            with self.assertRaises(driver.Refused):
                self.config(values)

    def test_unknown_or_ambiguous_config_does_not_expand_scope(self):
        for values in (
            dict(self.pins, schema=True),
            dict(self.pins, other="private canary"),
            dict(self.pins, driver_sha256="0" * 64),
            dict(self.pins, image_repository="unknown.example/unsafe"),
            dict(self.pins, image_digest="latest"),
        ):
            with self.assertRaises(driver.Refused):
                self.config(values)
        raw = (
            json.dumps(self.pins)
            .replace('"schema": 1', '"schema": 1, "schema": 1')
            .encode()
        )
        path = self.root / "duplicate.json"
        path.write_bytes(raw)
        with self.assertRaises(driver.Refused):
            driver.configuration(path, driver.sha(raw))

    def test_tampered_file_and_symlink_are_refused_before_import(self):
        path = self.root / "helper.py"
        path.write_bytes(b"raise RuntimeError('private canary')")
        with self.assertRaises(driver.Refused):
            driver.load_module("untrusted", path, "0" * 64)
        link = self.root / "link.py"
        link.symlink_to(path)
        with self.assertRaises(driver.Refused):
            driver.read(link)

    def xml(self, bad=None, missing=False, duplicate=False):
        entries = []
        for selector, count in driver.TESTS.items():
            path, *classes, name = selector.split("::")
            classname = path[:-3].replace("/", ".") + (
                "." + ".".join(classes) if classes else ""
            )
            for i in range(count):
                case_name = name + (f"[case{i}]" if count > 1 else "")
                child = (
                    "" if bad is None else "<" + bad + ">PRIVATE-CANARY</" + bad + ">"
                )
                entries.append(
                    f'<testcase classname="{classname}" name="{case_name}">{child}</testcase>'
                )
        if missing:
            entries.pop()
        if duplicate:
            entries.append(entries[0])
        path = self.root / "focused.xml"
        path.write_text(
            "<testsuites><testsuite>" + "".join(entries) + "</testsuite></testsuites>"
        )
        return path

    def test_focused_scope_requires_all_twelve_cases(self):
        result = driver.focused_result(self.xml())
        self.assertEqual(result["passed"], 12)
        self.assertFalse(result["full_backend_suite_repeated"])

    def test_failed_skipped_duplicate_or_missing_case_never_passes(self):
        for options in (
            {"bad": "failure"},
            {"bad": "error"},
            {"bad": "skipped"},
            {"missing": True},
            {"duplicate": True},
        ):
            with self.subTest(options=options), self.assertRaises(driver.Refused):
                driver.focused_result(self.xml(**options))

    def test_exact_installed_inventory_rejects_extra_and_changed_files(self):
        target = self.root / "custom_components/homecircle"
        body = {"manifest.json": b"{}", "frontend/card.js": b"synthetic"}
        driver.install(target, body)
        driver.exact_installed(target, body)
        (target / "extra.py").write_text("private canary")
        with self.assertRaises(driver.Refused):
            driver.exact_installed(target, body)
        (target / "extra.py").unlink()
        (target / "manifest.json").write_bytes(b"changed")
        with self.assertRaises(driver.Refused):
            driver.exact_installed(target, body)

    def test_current_runtime_cannot_silently_become_another_core_or_python(self):
        with (
            patch.object(driver.sys, "platform", "darwin"),
            self.assertRaises(driver.Refused),
        ):
            driver.runtime(self.pins)
        with (
            patch.object(driver.sys, "platform", "linux"),
            patch.object(driver.platform, "machine", return_value="aarch64"),
            self.assertRaises(driver.Refused),
        ):
            driver.runtime(self.pins)

    def test_minimum_target_and_auth_pin_cannot_silently_reuse_current_core(self):
        self.assertEqual(driver.CORE, "2026.9.4")
        self.assertEqual(
            driver.CONSTRAINTS_SHA,
            "962c9ccaf398e0b92b10ac9f765ac0f17e22238adc4e768deebc051ee8b60651",
        )
        script = Path(driver.__file__).with_name("run_host.sh").read_text()
        self.assertIn(
            '"pytest-homeassistant-custom-component==0.13.367"',
            Path(driver.__file__).read_text(),
        )
        self.assertNotIn("2026.10.2", script)
        helper = self.requirements_helper()
        config = (
            "auth_conf = [{'type': 'homeassistant'}]\n"
            "mfa_conf = config.get(CONF_AUTH_MFA_MODULES, "
            "[{'type': 'totp', 'id': 'totp', 'name': 'Authenticator app'}])\n"
        )
        expected = helper.default_auth_declarations(
            config, "", "REQUIREMENTS = ['pyotp==2.9.0', 'PyQRCode==1.2.1']"
        )
        self.assertEqual(
            expected["homeassistant.auth.mfa_modules.totp"],
            ["pyotp==2.9.0", "PyQRCode==1.2.1"],
        )
        with self.assertRaises(helper.Refused):
            helper.default_auth_declarations(
                config, "", "REQUIREMENTS = ['pyotp==2.10.0', 'PyQRCode==1.2.1']"
            )

    def test_unchanged_helpers_and_package_pins_are_explicit(self):
        self.assertEqual(
            driver.SOURCE_COMMIT, "9bf03eb45d2cf43274074534e9dfe2de841f4011"
        )
        self.assertEqual(driver.PHASES, ("create", "restart", "remove", "removed"))
        self.assertEqual(
            driver.sha(
                (Path(driver.__file__).parent / "package_support.py").read_bytes()
            ),
            driver.SUPPORT_SHA,
        )
        self.assertEqual(
            driver.RELEASE_SHA,
            "c4530d94be3b2996f8d6c8948db88a51868566047d68558eefde7967f270a861",
        )

    def test_launcher_preserves_local_ownership_and_offline_boundaries(self):
        script = Path(driver.__file__).with_name("run_host.sh").read_text()
        for required in (
            "unix:///*",
            "io.homecircle.minimum-core",
            "--cap-drop ALL",
            "--security-opt no-new-privileges",
            "network disconnect bridge",
            "NetworkSettings.Networks|length)==0",
            "Mounts|length)==0",
            "PortBindings|length)==0",
            "expected_image_id",
            "deadline=$((SECONDS + 2100))",
            "private_workspace_removed",
            "source_verified=true",
        ):
            self.assertIn(required, script)
        self.assertNotIn("--privileged", script)
        self.assertNotIn("--network host", script)
        self.assertNotIn("--volume", script)
        self.assertNotIn("--mount", script)

    def test_child_failure_projection_drops_raw_canary_and_unknown_fields(self):
        result = driver.project_failure(
            {
                "failure_type": "OSError",
                "failure_code": "private_storage_canary",
                "mode": "startup-child",
                "message": "PRIVATE CANARY",
                "path": "/owner/private",
            }
        )
        self.assertEqual(result, {"failure_type": "OSError", "mode": "startup-child"})
        result = driver.project_failure(
            {"failure_type": "Refused", "failure_code": "core_phase_child_refused"}
        )
        self.assertEqual(result["failure_code"], "core_phase_child_refused")

    def test_focused_failure_keeps_only_fixed_selector_and_drops_canary(self):
        path = self.xml(bad="failure")
        document = driver.ET.parse(path)
        first = next(document.getroot().iter("testcase"))
        first.set("name", first.attrib["name"].split("[", 1)[0] + "[PRIVATE-CANARY]")
        first.find("failure").text = "PRIVATE-CANARY raw exception /owner/private"
        document.write(path)
        with self.assertRaises(driver.Refused) as caught:
            driver.focused_result(path)
        error = caught.exception
        selector = next(iter(driver.TESTS))
        self.assertEqual(error.focused_selector, selector)
        result = driver.project_failure(
            {
                "failure_type": type(error).__name__,
                "failure_code": driver.refusal_code(error),
                "focused_selector": error.focused_selector,
                "raw": first.attrib["name"],
                "exception": first.find("failure").text,
            }
        )
        self.assertEqual(
            result,
            {
                "failure_type": "Refused",
                "failure_code": "focused_test_failed_or_skipped",
                "focused_selector": selector,
            },
        )
        self.assertNotIn("PRIVATE-CANARY", json.dumps(result))
        self.assertEqual(
            driver.project_failure({"focused_selector": selector + "[PRIVATE-CANARY]"}),
            {},
        )

    def requirements_helper(self):
        path = Path(driver.__file__).with_name("requirements_support.py")
        return driver.load_module(
            "synthetic_requirements", path, driver.sha(path.read_bytes())
        )

    def test_requirement_graph_executes_against_synthetic_core_sources(self):
        helper = self.requirements_helper()
        core = self.root / "homeassistant"
        core.mkdir()
        (core / "__init__.py").write_text("")
        (core / "bootstrap.py").write_text(
            "from .components import preimported\n"
            "CORE_INTEGRATIONS = {*BASE_PLATFORMS, 'root'}\n"
            "DEFAULT_INTEGRATIONS = {'root', 'http'} - {'root'}\n"
        )
        (core / "requirements.py").write_text(
            "DISCOVERY_INTEGRATIONS = {'dhcp': ('dhcp',), 'mqtt': ('mqtt',), "
            "'ssdp': ('ssdp',), 'zeroconf': ('zeroconf', 'homekit')}\n"
        )
        sources = {
            "core_config.py": (
                "auth_conf = [{'type': 'homeassistant'}]\n"
                "mfa_conf = config.get(CONF_AUTH_MFA_MODULES, "
                "[{'type': 'totp', 'id': 'totp', 'name': 'Authenticator app'}])\n"
            ),
            "auth/providers/homeassistant.py": "",
            "auth/mfa_modules/totp.py": "REQUIREMENTS = ['pyotp==2.9.0', 'PyQRCode==1.2.1']\n",
        }
        for name, raw in sources.items():
            path = core / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(raw)
        domains = {
            "base",
            "root",
            "http",
            "person",
            "zone",
            "dependency",
            "preimported",
        }
        for domain in domains:
            manifest = {"domain": domain, "requirements": []}
            if domain == "root":
                manifest.update(
                    dependencies=["dependency"], requirements=["synthetic==1.0"]
                )
            path = core / "components" / domain / "manifest.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(manifest))
        const = types.ModuleType("homeassistant.const")
        const.BASE_PLATFORMS = {"base"}
        with (
            patch.object(
                helper.importlib.util,
                "find_spec",
                return_value=types.SimpleNamespace(origin=str(core / "__init__.py")),
            ),
            patch.dict(driver.sys.modules, {"homeassistant.const": const}),
        ):
            result = helper.core_component_requirements(
                {"manifest.json": b'{"dependencies": []}'}
            )
        self.assertEqual(result["domains"], sorted(domains - {"preimported"}))
        self.assertEqual(result["preimport_own_requirements_modules"], ["preimported"])
        self.assertEqual(
            result["requirements"],
            ["PyQRCode==1.2.1", "pyotp==2.9.0", "synthetic==1.0"],
        )
        self.assertEqual(
            set(result["source_sha256"]),
            set(sources) | {"bootstrap.py", "requirements.py"},
        )

    def test_requirement_refusal_preserves_only_fixed_allowlisted_code(self):
        helper = self.requirements_helper()
        with patch.object(
            driver,
            "SAFE_CODES",
            driver.SAFE_CODES | driver.literal_codes(Path(helper.__file__)),
        ):
            try:
                helper.declared_requirements(["PRIVATE-CANARY"])
            except helper.Refused as error:
                self.assertEqual(
                    driver.refusal_code(error, helper), "declared_requirements_refused"
                )
                self.assertIsNone(driver.refusal_code(error))
            else:
                self.fail(
                    "The actual requirement helper must refuse an unpinned requirement"
                )
            self.assertIsNone(
                driver.refusal_code(helper.Refused("PRIVATE-CANARY"), helper)
            )
            self.assertIsNone(
                driver.refusal_code(
                    RuntimeError("declared_requirements_refused"), helper
                )
            )


if __name__ == "__main__":
    unittest.main()
