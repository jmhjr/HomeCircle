"""Offline controller contracts; run only on the native Linux CI runner."""

from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock
import zipfile

import controller


class ArchiveContracts(unittest.TestCase):
    def archive(self, members):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for name, value in members:
                archive.writestr(name, value)
        return buffer.getvalue()

    def inspect(self, raw, count):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input.zip"
            path.write_bytes(raw)
            return controller.check_archive(path, controller.sha(raw), count)

    def test_exact_inventory_is_derived_from_bytes(self):
        self.assertEqual(self.inspect(self.archive([("__init__.py", b"example")]), 1),
                         {"__init__.py": {"bytes": 7, "sha256": controller.sha(b"example")}})

    def test_parent_and_absolute_names_are_refused(self):
        for name in ("../outside", "/outside", "normal\\outside"):
            with self.subTest(name=name), self.assertRaises(controller.Refused):
                self.inspect(self.archive([(name, b"example")]), 1)

    def test_duplicate_members_cannot_hide_archive_contents(self):
        with self.assertWarns(UserWarning):
            raw = self.archive([("one", b"first"), ("one", b"second")])
        with self.assertRaises(controller.Refused):
            self.inspect(raw, 1)

    def test_archive_pin_is_mandatory(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input.zip"
            path.write_bytes(self.archive([("one", b"example")]))
            with self.assertRaises(controller.Refused):
                controller.check_archive(path, "0" * 64, 1)


class PublicDiagnostics(unittest.TestCase):
    def test_core_version_projection_excludes_arbitrary_response_strings(self):
        for value in ("2026.10.2", "2026.10.0b1", "landingpage"):
            self.assertEqual(controller.public_core_version(value), value)
        for value in (None, {}, "private-value", "2026.10.2 private-value", "https://example.invalid"):
            self.assertIsNone(controller.public_core_version(value))

    def test_supervisor_projection_excludes_arbitrary_private_fields(self):
        value = {"result": "ok", "data": {"healthy": True, "supported": False, "state": "running",
                 "ip_address": "PRIVATE-CANARY", "token": "PRIVATE-CANARY", "version": "PRIVATE-CANARY"}}
        projected = controller.public_supervisor_state(value)
        self.assertEqual(projected, {"result": "ok", "healthy": True, "supported": False, "state": "running"})
        self.assertNotIn("PRIVATE-CANARY", json.dumps(projected))


class PhaseContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.host = controller.Controller(SimpleNamespace(branch_commit="a" * 40))
        self.host.public = Path(self.temporary.name)
        self.host.config_path = "/mnt/data/supervisor/homeassistant"
        self.host.guest_write = Mock()
        self.host.guest = Mock(return_value=b"")
        self.inventory = {"__init__.py": {"bytes": 7, "sha256": controller.sha(b"example")}}
        self.host.inventories = {"baseline": self.inventory, "candidate": self.inventory}
        self.receipt = {
            "schema": 1, "token": self.host.nonce, "phase": "baseline", "outcome": "passed",
            "package_files_count": 1, "package_payload_sha256": controller.sha(controller.canonical(self.inventory)),
            "loaded_source_sha256": self.inventory["__init__.py"]["sha256"],
            "snapshot_sha256": "b" * 64, "process": {"pid": 123, "start_ticks": 456},
            "hacs": {"enabled": True, "pending_tasks": 0, "installed_version": "v0.1.0-beta.19"},
        }

    def read(self):
        self.host.guest_read = Mock(return_value=controller.canonical(self.receipt))

    def test_phase_instructions_are_atomic_and_secret_projection_is_narrow(self):
        self.receipt["hacs"]["private_token"] = "PRIVATE-CANARY"
        self.receipt["process"]["private_state"] = "PRIVATE-CANARY"
        self.receipt["snapshot"] = {"private_state": "PRIVATE-CANARY"}
        self.read()
        self.host.phase("baseline")
        write_path = self.host.guest_write.call_args.args[0]
        self.assertNotEqual(Path(write_path).name, "phase.json")
        self.assertIn("; mv ", self.host.guest.call_args.args[0])
        public = (self.host.public / "baseline.json").read_text()
        self.assertNotIn("PRIVATE-CANARY", public)
        self.assertNotIn(self.host.nonce, public)

    def test_passing_guest_receipt_cannot_override_package_pin(self):
        self.receipt["package_payload_sha256"] = "0" * 64
        self.read()
        with self.assertRaises(controller.Refused):
            self.host.phase("baseline")
        self.assertFalse((self.host.public / "baseline.json").exists())

    def test_unexpected_global_hacs_queue_refuses_acceptance(self):
        self.receipt["hacs"]["pending_tasks"] = 1
        self.read()
        with self.assertRaises(controller.Refused):
            self.host.phase("baseline")

    def test_candidate_installed_by_controller_keeps_hacs_metadata_honest(self):
        self.receipt.update(phase="candidate", guard={"blocked": True, "unresolved": 3, "sha256": "c" * 64})
        self.read()
        self.host.phase("candidate")
        result = json.loads((self.host.public / "candidate.json").read_text())
        self.assertEqual(result["hacs"]["installed_version"], "v0.1.0-beta.19")

    def test_candidate_without_blocked_guard_is_refused(self):
        self.receipt.update(phase="candidate", guard={"blocked": False, "unresolved": 0})
        self.read()
        with self.assertRaises(controller.Refused):
            self.host.phase("candidate")

    def test_failure_before_vm_launch_still_cleans_private_workspace(self):
        private = self.host.public / "owned-private"
        private.mkdir()
        self.host.private = private
        self.host.cleanup_vm()
        self.assertFalse(private.exists())
        self.assertEqual(self.host.cleanup, {"qemu_stopped": True, "private_workspace_removed": True,
                                             "cleanup_failed": False})


if __name__ == "__main__":
    unittest.main()
