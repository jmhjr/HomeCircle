"""Linux-only stdlib contracts; no package imports, native execution or network."""

import ast
import importlib.util
import io
import json
from pathlib import Path
import struct
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

if sys.platform != "linux":
    raise SystemExit("linux_required")

SPEC = importlib.util.spec_from_file_location("glibc_driver_contracts", Path(__file__).with_name("driver.py"))
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)


class DriverContracts(unittest.TestCase):
    def temporary(self):
        directory = tempfile.TemporaryDirectory(prefix="glibc-contract-")
        self.addCleanup(directory.cleanup)
        return Path(directory.name)

    def write_json(self, name, value):
        path = self.temporary() / name
        path.write_text(json.dumps(value))
        return path

    def native_receipt(self):
        return {"outcome": "passed", "core_version": subject.CORE,
                "package_sha256": subject.RELEASE_SHA, "package_members": 112,
                "machine": "x86_64", "system": "Linux", "python_version": "3.14.6",
                "core_constraints_sha256": subject.CONSTRAINTS_SHA,
                "core_constraint_mismatches": [], "installed_dependency_closure": {str(i): "1" for i in range(24)},
                "mandatory_imports": True, "synthetic_native_worker": True, "production_hash_refusal": True,
                "worker_processes_reaped": True, "cleanup_ok": True, "network_allowed": False,
                "apple_binary_executed": False, "owner_data_read": False,
                "account_requests": 0, "unicorn_version": "2.1.4"}

    def lifecycle_receipt(self):
        value = {"outcome": "passed", "package_sha256": subject.RELEASE_SHA, "package_members": 112,
                 "machine": "x86_64", "system": "Linux", "python_version": "3.14.6",
                 "candidate_files_modified": False, "network_allowed": False,
                 "apple_binary_executed": False, "owner_data_read": False,
                 "account_requests": 0, "unicorn_version": "2.1.4",
                 "approved_posix_spawn_events": 2, "denied_unknown_spawn_events": 0,
                 "worker_children": [{"proc_absent": True, "exit_code": 0}, {"proc_absent": True, "exit_code": -9}],
                 "child_limits": {key: {"soft": count, "hard": count} for key, count in
                                  (("cpu_seconds", 90), ("core_bytes", 0), ("address_space_bytes", 3 * 1024**3))}}
        value.update({name: True for name in ("normal_open_check_close", "active_native_cancellation",
                      "parent_only_dependency_used", "production_spawn_contract", "production_pipe_contract",
                      "worker_processes_reaped", "cleanup_ok")})
        return value

    def backend_xml(self, *, skip_name="test_retained_public_apple_dmg_fixed_ranges", errors=0):
        path = self.temporary() / "backend.xml"
        path.write_text(f'<testsuite errors="{errors}" failures="0">' +
                        '<testcase classname="tests.example" name="test_example"/>' * 1443 +
                        '<testcase classname="tests.test_findmy_runtime_bootstrap" name="' + skip_name +
                        '"><skipped/></testcase></testsuite>')
        return path

    def test_source_hash_refused_before_archive_parsing(self):
        directory = self.temporary()
        (directory / "source.tgz").write_bytes(b"unreviewed source")
        with patch.object(subject.gzip, "GzipFile", side_effect=AssertionError("parsed unpinned input")):
            with self.assertRaisesRegex(subject.Refused, "^input_hash_refused$"):
                subject.inputs(directory)

    def test_pinned_input_symlink_is_refused(self):
        directory = self.temporary()
        target = directory / "actual"
        target.write_bytes(b"public bytes")
        link = directory / "input"
        link.symlink_to(target)
        with self.assertRaisesRegex(subject.Refused, "^input_path_refused$"):
            subject.read_pinned(link, subject.sha(target.read_bytes()))

    def test_ustar_link_refused_before_extraction(self):
        directory = self.temporary()
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz", format=tarfile.USTAR_FORMAT) as archive:
            info = tarfile.TarInfo("public.py")
            info.type = tarfile.SYMTYPE
            info.linkname = "outside"
            archive.addfile(info)
        source = buffer.getvalue()
        inventory = json.dumps({"public.py": {"bytes": 0, "sha256": subject.sha(b"")}}).encode()
        (directory / "source.tgz").write_bytes(source)
        (directory / "source-inventory.json").write_bytes(inventory)
        with patch.object(subject, "SOURCE_SHA", subject.sha(source)), \
                patch.object(subject, "INVENTORY_SHA", subject.sha(inventory)), patch.object(subject, "COUNT", 1):
            with self.assertRaisesRegex(subject.Refused, "^source_tar_metadata_refused$"):
                subject.inputs(directory)

    def test_runtime_overlay_uses_only_release_integration(self):
        source = {"README.md": b"public", "custom_components/homecircle/old.py": b"unpublished"}
        result = subject.runtime_files(source, {"manifest.json": b"published", "LICENSE": b"notice"})
        self.assertEqual(result, {"README.md": b"public", "custom_components/homecircle/manifest.json": b"published",
                                  "custom_components/homecircle/LICENSE": b"notice"})

    def test_tree_verification_refuses_added_integration_file(self):
        directory = self.temporary() / "tree"
        subject.extract({"manifest.json": b"published"}, directory)
        (directory / "unpublished.py").write_bytes(b"extra")
        with self.assertRaisesRegex(subject.Refused, "^tree_bytes_changed$"):
            subject.tree_unchanged({"manifest.json": b"published"}, directory)

    def test_elf_rejects_arm64(self):
        path = self.temporary() / "python"
        raw = bytearray(64)
        raw[:6] = b"\x7fELF\x02\x01"
        struct.pack_into("<H", raw, 18, 183)
        path.write_bytes(raw)
        with self.assertRaisesRegex(subject.Refused, "^native_elf_amd64_refused$"):
            subject.elf(path)

    def test_active_glibc_wrong_version_refused(self):
        libc = SimpleNamespace(gnu_get_libc_version=Mock(return_value=b"2.38"))
        with patch.object(subject.platform, "system", return_value="Linux"), \
                patch.object(subject.platform, "machine", return_value="x86_64"), \
                patch.object(subject.platform, "python_version", return_value="3.14.6"), \
                patch.object(Path, "read_text", return_value='ID=ubuntu\nVERSION_ID="24.04"\n'), \
                patch.object(subject.ctypes, "CDLL", return_value=libc):
            with self.assertRaisesRegex(subject.Refused, "^active_glibc_version_refused$"):
                subject.environment(dependencies=False)

    def test_python_version_refused_before_loading_libc(self):
        with patch.object(subject.platform, "python_version", return_value="3.12.0"), \
                patch.object(subject.ctypes, "CDLL", side_effect=AssertionError("wrong Python proceeded")):
            with self.assertRaisesRegex(subject.Refused, "^linux_runtime_refused$"):
                subject.environment(dependencies=False)

    def test_hash_adapter_changes_only_one_literal(self):
        directory = self.temporary()
        original = (b'# unchanged\nCANDIDATE_SHA256 = "' + subject.OLD_SHA.encode() + b'"\nCOUNT = 112\n'
                    + subject.ORIGINAL_PROCESS_GUARD.encode())
        files = {"scripts/platform_validate_linux_lifecycle.py": original,
                 **{"scripts/" + name: b"unchanged" for name in
                    ("platform_validate_candidate.py", "validate_release.py", "build_release.py", "validate_ha_restart.py")}}
        path, receipt = subject.lifecycle_copy(SimpleNamespace(results=directory), files)
        expected = original.replace(subject.OLD_SHA.encode(), subject.RELEASE_SHA.encode()).replace(
            subject.ORIGINAL_PROCESS_GUARD.encode(), subject.OWNED_PROCESS_GUARD.encode())
        self.assertEqual(path.read_bytes(), expected)
        self.assertEqual(files["scripts/platform_validate_linux_lifecycle.py"], original)
        self.assertEqual(receipt["archive_hash_literal_substitutions"], 1)
        self.assertEqual(receipt["spawn_audit_block_substitutions"], 1)
        self.assertEqual(receipt["semantic_adaptations"], ["published_archive_hash", "exact_owned_posix_spawn_audit"])

    def test_adapter_includes_actual_tagged_local_import_closure(self):
        archive = Path(__file__).resolve().parents[1] / "native-beta20-package/payload/source.tgz"
        raw = archive.read_bytes()
        self.assertEqual(subject.sha(raw), subject.SOURCE_SHA)
        files = {}
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as source:
            for member in source.getmembers():
                if member.name.startswith("scripts/") and member.name.endswith(".py"):
                    with source.extractfile(member) as stream:
                        files[member.name] = stream.read()
        path, _ = subject.lifecycle_copy(SimpleNamespace(results=self.temporary()), files)
        pending, visited = [path], set()
        while pending:
            script = pending.pop()
            if script.name in visited:
                continue
            visited.add(script.name)
            for node in ast.walk(ast.parse(script.read_bytes())):
                if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    name = node.module.split(".")[0] + ".py"
                    if "scripts/" + name in files:
                        sibling = script.parent / name
                        self.assertTrue(sibling.is_file(), "missing exact tagged helper: " + name)
                        self.assertEqual(sibling.read_bytes(), files["scripts/" + name])
                        pending.append(sibling)
        self.assertIn("validate_ha_restart.py", visited)

    def test_hash_adapter_refuses_ambiguous_literals(self):
        raw = ('CANDIDATE_SHA256 = "' + subject.OLD_SHA + '"\n').encode() * 2
        with self.assertRaisesRegex(subject.Refused, "^lifecycle_hash_adapter_count_refused$"):
            subject.lifecycle_copy(SimpleNamespace(results=self.temporary()),
                                   {"scripts/platform_validate_linux_lifecycle.py": raw})

    def test_native_receipt_refuses_old_candidate(self):
        value = self.native_receipt()
        value["package_sha256"] = subject.OLD_SHA
        with self.assertRaisesRegex(subject.Refused, "^native_identity_refused$"):
            subject.native_result(self.write_json("native.json", value))

    def test_native_receipt_requires_every_mandatory_import(self):
        value = self.native_receipt()
        value["mandatory_imports"] = False
        with self.assertRaisesRegex(subject.Refused, "^native_contract_refused$"):
            subject.native_result(self.write_json("native.json", value))

    def test_lifecycle_receipt_refuses_changed_child_limit(self):
        value = self.lifecycle_receipt()
        value["child_limits"]["cpu_seconds"]["hard"] = 180
        with self.assertRaisesRegex(subject.Refused, "^lifecycle_limits_refused$"):
            subject.lifecycle_result(self.write_json("lifecycle.json", value))

    def test_lifecycle_receipt_requires_actual_reap_boolean(self):
        value = self.lifecycle_receipt()
        value["worker_children"][0]["proc_absent"] = False
        with self.assertRaisesRegex(subject.Refused, "^lifecycle_reap_refused$"):
            subject.lifecycle_result(self.write_json("lifecycle.json", value))

    def test_backend_exact_count_and_named_optional_skip_accepted(self):
        self.assertEqual(subject.backend_result(self.backend_xml(), require_pass=True)["passed"], 1443)

    def test_backend_unapproved_skip_refused(self):
        with self.assertRaisesRegex(subject.Refused, "^backend_skip_refused$"):
            subject.backend_result(self.backend_xml(skip_name="test_some_other_skip"), require_pass=True)

    def test_backend_collection_error_cannot_pass(self):
        with self.assertRaisesRegex(subject.Refused, "^backend_suite_errors_refused$"):
            subject.backend_result(self.backend_xml(errors=1), require_pass=True)

    def test_startup_failure_projection_drops_private_canary(self):
        value = {"failure_type": "ModuleNotFoundError", "failure_code": "unknown_private_canary",
                 "missing_module": "homeassistant.public_module", "message": "PRIVATE_CANARY",
                 "public_frames": [{"script": "validate_ha_restart.py", "function": "run_phase", "line": 25,
                                    "locals": "PRIVATE_CANARY"},
                                   {"script": "/private/path.py", "function": "secret", "line": 1}]}
        result = subject.project_child_failure(value)
        self.assertNotIn("CANARY", json.dumps(result))
        self.assertEqual(result["public_frames"], [{"script": "validate_ha_restart.py", "function": "run_phase", "line": 25}])
        self.assertEqual(result["missing_module"], "homeassistant.public_module")

    def test_startup_failure_projection_rejects_malformed_fields(self):
        result = subject.project_child_failure({"failure_type": "raw error text", "failure_code": [],
                                                "missing_module": "/private/path", "public_frames": {"locals": "CANARY"}})
        self.assertEqual(result, {"public_frames": []})

    def test_probe_failure_retains_fixed_lifecycle_phase_and_type(self):
        log = self.temporary() / "private.log"
        log.write_text('  File "/discarded/private/platform_validate_linux_lifecycle.py", line 340, in run_validation\n'
                       'ValueError: linux_lifecycle_probe_refused:dependency_copy:PermissionError\n')
        result = subject.probe_failure(log, "lifecycle", 1)
        self.assertEqual(result, {"stage": "lifecycle", "exit_code": 1, "failure_type": "ValueError",
                                  "failure_code": "linux_lifecycle_probe_refused", "probe_phase": "dependency_copy",
                                  "probe_failure_type": "PermissionError",
                                  "public_frames": [{"script": "platform_validate_linux_lifecycle.py", "line": 340}]})

    def test_probe_failure_retains_only_allowlisted_missing_module(self):
        log = self.temporary() / "private.log"
        log.write_text('  File "/private/validate_release.py", line 17, in <module>\n'
                       "ModuleNotFoundError: No module named 'validate_ha_restart'\n")
        result = subject.probe_failure(log, "lifecycle", 1)
        self.assertEqual(result["missing_module"], "validate_ha_restart")
        self.assertEqual(result["failure_type"], "ModuleNotFoundError")
        self.assertNotIn("/private", json.dumps(result))

    def test_probe_failure_drops_unknown_message_module_and_frame(self):
        log = self.temporary() / "private.log"
        log.write_text('  File "/private/CANARY.py", line 17, in CANARY\n'
                       "ModuleNotFoundError: No module named 'CANARY'\n"
                       "ValueError: linux_lifecycle_probe_refused:CANARY:PermissionError\n"
                       "ValueError: CANARY token/private/response\n")
        result = subject.probe_failure(log, "native", 1)
        self.assertNotIn("CANARY", json.dumps(result))
        self.assertEqual(result["public_frames"], [])

    def process_guard(self):
        command = ("/approved/python", "-I", "-B", "-c", "public fixture")
        context = {"sys": SimpleNamespace(executable=command[0]), "launches": {command}, "counters": {}}
        # Compile only the adapter's pure guard block; install no audit hook,
        # spawn no process and import no runtime package in this contract suite.
        exec("def guard(event, args):\n" + subject.OWNED_PROCESS_GUARD, context)
        return context["guard"], context["counters"], command

    def test_posix_spawn_exact_owned_executable_and_argv_allowed(self):
        guard, counters, command = self.process_guard()
        guard("os.posix_spawn", (command[0], list(command), {"IGNORED_PRIVATE_ENV": "CANARY"}))
        self.assertEqual(counters, {"approved_posix_spawn_events": 1, "denied_unknown_spawn_events": 0})
        value = self.lifecycle_receipt()
        self.assertEqual(subject.lifecycle_result(self.write_json("lifecycle.json", value))["approved_posix_spawn_events"], 2)
        for approved, denied in ((0, 0), (2, 1)):
            with self.subTest(approved=approved, denied=denied):
                value["approved_posix_spawn_events"], value["denied_unknown_spawn_events"] = approved, denied
                with self.assertRaisesRegex(subject.Refused, "^lifecycle_spawn_audit_refused$"):
                    subject.lifecycle_result(self.write_json("lifecycle.json", value))

    def test_posix_spawn_wrong_executable_refused(self):
        guard, counters, command = self.process_guard()
        with self.assertRaisesRegex(PermissionError, "^linux_lifecycle_process_refused$"):
            guard("os.posix_spawn", ("/unapproved/python", list(command), {}))
        self.assertEqual(counters, {"approved_posix_spawn_events": 0, "denied_unknown_spawn_events": 1})

    def test_posix_spawn_wrong_argv_refused(self):
        guard, counters, command = self.process_guard()
        with self.assertRaisesRegex(PermissionError, "^linux_lifecycle_process_refused$"):
            guard("os.posix_spawn", (command[0], [command[0], "-c", "unapproved"], {}))
        self.assertEqual(counters, {"approved_posix_spawn_events": 0, "denied_unknown_spawn_events": 1})

    def test_unknown_popen_launch_refused(self):
        guard, counters, command = self.process_guard()
        with self.assertRaisesRegex(PermissionError, "^linux_lifecycle_process_refused$"):
            guard("subprocess.Popen", (command[0], [command[0], "-c", "unapproved"], None, None))
        self.assertEqual(counters["denied_unknown_spawn_events"], 1)

    def test_system_and_exec_stay_refused(self):
        guard, counters, command = self.process_guard()
        for event in ("os.system", "os.exec"):
            with self.subTest(event=event):
                with self.assertRaisesRegex(PermissionError, "^linux_lifecycle_process_refused$"):
                    guard(event, (command[0], list(command), {}))
        self.assertEqual(counters["approved_posix_spawn_events"], 0)
        self.assertEqual(counters["denied_unknown_spawn_events"], 2)


if __name__ == "__main__":
    unittest.main()
