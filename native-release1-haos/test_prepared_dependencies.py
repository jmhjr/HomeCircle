"""Prepared-library and diagnostic projection contracts, with standard-library fixtures."""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
from types import SimpleNamespace
import unittest

import controller
import prepare_dependencies


def preload():
    data = b"prepared dependency"
    files = {"lib/python3.14/site-packages/example.py": {"bytes": len(data), "sha256": controller.sha(data)}}
    closure = {name: "1.0" for name in controller.PACKAGE_NAMES}
    closure.update({"package" + str(index): "1.0" for index in range(18)})
    return {"schema": 1, "outcome": "passed", "core": controller.CORE, "python": "3.14.6",
            "constraints_sha256": controller.CONSTRAINTS_SHA, "site": controller.DEPS_SITE,
            "normal_bootstrap_library": True, "virtual_env": False, "requirements": controller.REQUIREMENTS,
            "closure": closure, "closure_count": 24, "inventory": files,
            "inventory_sha256": controller.sha(controller.canonical(files)),
            "inventory_files": len(files), "inventory_bytes": len(data),
            "inventory_scope": "dependency_regular_files_excluding_generated_bytecode"}


def diagnostic():
    packages = {name: {"available": True, "satisfies_requirement": True, "origin_config_deps": True,
                      "metadata_error": False, "version": "1.0", "loaded_module_present": False,
                      "origin_probe": "import_spec"} for name in controller.PACKAGE_NAMES}
    return {"entry_state": "setup_retry", "entry_disabled": False, "skip_pip": False,
            "tracker_states_present": 2, "person_states_present": 2, "person_sources_match": 0,
            "config_deps_on_path": True, "packages": packages, "PRIVATE-CANARY": "PRIVATE-CANARY"}


class PreparedLibraryContracts(unittest.TestCase):
    def test_valid_library_inventory_is_bound_to_exact_size_hash_and_public_scope(self):
        public, inventory = controller.checked_dependency_preload(preload())
        self.assertEqual(public["closure_count"], 24)
        self.assertEqual(public["inventory_files"], len(inventory))
        self.assertNotIn("inventory", public)

    def test_library_fingerprints_and_path_cannot_be_substituted(self):
        for mutate in (
            lambda value: value.update(inventory_sha256="a" * 64),
            lambda value: value.update(inventory_bytes=1),
            lambda value: value.update(site="/private"),
            lambda value: value.update(virtual_env=True),
            lambda value: value.update(normal_bootstrap_library=False),
            lambda value: value["inventory"].update({"../../private": {"bytes": 0, "sha256": "a" * 64}}),
        ):
            value = preload()
            mutate(value)
            with self.subTest(value=value), self.assertRaises(controller.Refused):
                controller.checked_dependency_preload(value)

    def test_direct_requirements_must_exist_in_the_24_package_closure(self):
        value = preload()
        value["closure"].pop("unicorn")
        value["closure"]["replacement"] = "1.0"
        with self.assertRaisesRegex(controller.Refused, "direct_closure"):
            controller.checked_dependency_preload(value)

    def test_runtime_bytecode_is_the_only_permitted_unfingerprinted_cache_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "module.py").write_bytes(b"source")
            cache = root / "__pycache__"
            cache.mkdir()
            (cache / "module.cpython-314.pyc").write_bytes(b"compiled")
            actual, total = prepare_dependencies.inventory(root)
            self.assertEqual(set(actual), {"module.py"})
            self.assertEqual(total, 6)
            (cache / "unrecognized.txt").write_bytes(b"not a known cache")
            with self.assertRaisesRegex(RuntimeError, "unrecognized_cache_file"):
                prepare_dependencies.inventory(root)

    def test_legacy_pyc_outside_cache_is_fingerprinted_and_symlinks_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "module.pyc").write_bytes(b"legacy compiled")
            actual, _ = prepare_dependencies.inventory(root)
            self.assertIn("module.pyc", actual)
            (root / "symlink").symlink_to(root / "module.pyc")
            with self.assertRaisesRegex(RuntimeError, "dependency_symlink"):
                prepare_dependencies.inventory(root)

    def test_installed_hardlinks_cannot_become_unsupported_backup_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "module.py"
            source.write_bytes(b"source")
            os.link(source, root / "hardlink.py")
            with self.assertRaisesRegex(RuntimeError, "dependency_hardlink"):
                prepare_dependencies.inventory(root)

    def test_startup_projection_retains_only_safe_state_and_package_metadata(self):
        public = controller.public_startup_diagnostics({"before_entry_wait": diagnostic(), "failure": diagnostic()})
        self.assertEqual(public["failure"]["entry_state"], "setup_retry")
        self.assertEqual(public["failure"]["person_sources_match"], 0)
        self.assertNotIn("PRIVATE-CANARY", json.dumps(public))
        self.assertEqual(public["failure"]["packages"]["unicorn"]["origin_probe"], "import_spec")

    def test_startup_diagnostic_refuses_raw_error_versions_and_unknown_states(self):
        for mutate in (
            lambda value: value.update(entry_state="PRIVATE-CANARY"),
            lambda value: value.update(person_sources_match=True),
            lambda value: value["packages"]["unicorn"].update(version="https://PRIVATE-CANARY.invalid"),
            lambda value: value["packages"]["unicorn"].update(origin_probe="PRIVATE-CANARY"),
        ):
            value = diagnostic()
            mutate(value)
            with self.subTest(value=value), self.assertRaises(controller.Refused):
                controller.public_startup_diagnostics({"failure": value})

    def archive_host(self, root, change_dependency=False):
        value = preload()
        config = root / "homeassistant"
        config.mkdir()
        control = config / controller.CONTROL
        control.mkdir()
        candidate = {"__init__.py": b"candidate"}
        candidate_inventory = {name: {"bytes": len(raw), "sha256": controller.sha(raw)}
                               for name, raw in candidate.items()}
        (control / "inputs.json").write_bytes(controller.canonical({"candidate_inventory": candidate_inventory,
            "dependency_inventory": value["inventory"], "dependency_fixture": controller.public_dependency_preload(value)}))
        ledger = controller.canonical({"version": 1, "accounts": {"a" * 64:
            {"rejected": 2, "uncertain": 0, "verified": 0, "pending": None}}})
        guard = {"ledger.json": {"bytes": len(ledger), "sha256": controller.sha(ledger)}}
        members = {"data/custom_components/homecircle/__init__.py": b"candidate",
            "data/.storage/core.config_entries": controller.canonical({"data": {"entries": [
                {"domain": "homecircle", "disabled_by": None}]}}),
            "data/.storage/homecircle_findmy/recovery_guard/ledger.json": ledger,
            "data/home-assistant_v2.db": b"SQLite format 3\x00" + bytes(4096),
            "data/deps/lib/python3.14/site-packages/example.py":
                b"changed dependency" if change_dependency else b"prepared dependency"}
        inner = io.BytesIO()
        with tarfile.open(fileobj=inner, mode="w") as archive:
            for name, data in members.items():
                item = tarfile.TarInfo(name)
                item.size = len(data)
                archive.addfile(item, io.BytesIO(data))
        path = root / "backup.tar"
        with tarfile.open(path, "w") as archive:
            data = inner.getvalue()
            item = tarfile.TarInfo("homeassistant.tar")
            item.size = len(data)
            archive.addfile(item, io.BytesIO(data))
        host = controller.Controller(SimpleNamespace(branch_commit="a" * 40))
        host.backup = {}
        host.backup_guard_sha256 = controller.sha(controller.canonical(guard))
        host.dependency_fixture = controller.public_dependency_preload(value)
        script = []
        host.guest_write = lambda _path, raw: script.append(raw.decode())
        def guest(_command, _timeout):
            source = script[-1].replace('/data/homeassistant', str(config)) \
                .replace('/data/backup/homecircle-enabled-restore-qa.tar', str(path))
            output = io.StringIO()
            try:
                with redirect_stdout(output):
                    exec(compile(source, "owned-archive-proof", "exec"), {})
            except RuntimeError:
                raise controller.Refused("guest_command_failed") from None
            return output.getvalue().encode()
        host.guest = guest
        return host

    def test_actual_backup_inspection_requires_exact_prepared_dependency_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            host = self.archive_host(Path(temporary))
            host.inspect_backup()
            self.assertEqual(host.backup["archive"]["prepared_dependency_sha256"],
                             host.dependency_fixture["inventory_sha256"])
            self.assertEqual(host.backup["archive"]["guard_unresolved"], 2)
        with tempfile.TemporaryDirectory() as temporary:
            host = self.archive_host(Path(temporary), change_dependency=True)
            with self.assertRaises(controller.Refused):
                host.inspect_backup()
            self.assertNotIn("archive", host.backup)


if __name__ == "__main__":
    unittest.main()
