"""Bounded stdlib-only acceptance and lifecycle controls; no HA or VM imports."""
import ast
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import protocol as p
import verify_results as v

HERE = Path(__file__).resolve().parent


def fictional():
    inventories = {kind: {"__init__.py": {"bytes": 1, "sha256": char * 64},
                  "frontend/homecircle-card.js": {"bytes": 2, "sha256": char * 64}}
                   for kind, char in (("rc", "a"), ("base", "b"))}
    for value in inventories.values():
        value.update({f"example_fixture_{index}.txt": {"bytes": 1, "sha256": "0" * 64} for index in range(110)})
    anchor, branch, nonce = "c" * 64, "d" * 40, "e" * 64
    inputs = {"source_commit": v.SOURCE, "source_files": 402, "candidate_sha256": v.CANDIDATE,
        "inventory_sha256": p.INVENTORY, "baseline_sha256": v.BASELINE,
        "baseline_inventory_sha256": p.BASE_INVENTORY, "hacs_sha256": p.HACS_SHA,
        "haos_sha256": "f" * 64, "helper_files": {"example.py": {"bytes": 1, "sha256": "a" * 64}},
        "controller_sha256": "b" * 64, "donor_host_sha256": "c" * 64, "anchor_sha256": anchor}
    common = {"schema": 1, "source_commit": v.SOURCE, "candidate_sha256": v.CANDIDATE,
              "baseline_sha256": v.BASELINE, "anchor_sha256": anchor, "branch_commit": branch,
              "nonce_sha256": nonce, "core_version": "2026.10.2"}
    host = {**common, "outcome": "passed", "phase_count": 14, "hacs_version": "2.0.5",
        "actual_kvm": True, "provenance": deepcopy(inputs), "ephemeral_job_token": True, "oauth_onboarding": False,
        "direct_candidate_installs": 0, "provider_accounts": 0, "owner_accounts": 0, "recovery_api_calls": 0,
        "supervisor_backup_restore": False, "stopped_configuration_rollback": True,
        "guard_claim": "synthetic_opaque_byte_preservation_only", "host_elapsed_seconds": 100,
        "failure": None, "qemu_stopped": True, "private_workspace_removed": True, "cleanup_failed": False,
        "core_actions": [{"action": "stop" if i % 2 == 0 else "start", "result": "ok", "supervisor_running": True,
            "relevant_core_jobs_idle": True, "running_before": i % 2 == 0, "running_after": i % 2 == 1} for i in range(23)]}
    versions = {"rc": p.VERSION, "base": p.BASE_VERSION}
    active = p.ACTIVE
    receipts = {}
    for index, name in enumerate(v.PHASES):
        disk, loaded, downloaded = v.SPEC[name]
        guard = None
        if name in active - {"fresh"}:
            generation = 1 if name in {"baseline", "upgrade_download"} else 2
            guard = {"generation": generation, "ledger_sha256": str(generation) * 64,
                "witness_sha256": str(generation + 2) * 64, "byte_preservation_only": True}
        receipts[name] = {**common, "phase": name, "outcome": "passed",
            "process": {"pid": 10 + index, "start_ticks": 100 + index},
            "hacs": {"version": "2.0.5", "enabled": True, "queue_pending": 0, "installed": disk is not None,
                     "installed_version": "v" + versions[disk] if disk else None},
            "disk": None if not disk else {"version": versions[disk], "files": 112, "payload_sha256": v.sha(v.encoded(inventories[disk]))},
            "loaded": None if not loaded else {"version": versions[loaded], "source_sha256": inventories[loaded]["__init__.py"]["sha256"]},
            "frontend": None if name not in active else {"bundle_sha256": inventories[loaded]["frontend/homecircle-card.js"]["sha256"],
                "url": "/homecircle_static/homecircle-card.js?v=" + versions[loaded] + "&asset=" + inventories[loaded]["frontend/homecircle-card.js"]["sha256"][:12], "served": True},
            "snapshot_sha256": "f" * 64 if name in active else None,
            "persisted_store_checked": name in {"fresh", "baseline"}, "download_tag": "v" + versions[disk] if downloaded else None,
            "release_proof": disk is not None, "removed": name in {"fresh_remove", "fresh_removed"}, "guard": guard,
            "activity": {"count": 2, "cohort_sha256": "9" * 64, "retained": True} if name in active - {"fresh"} else None,
            "removed_activity_store": name in {"fresh_remove", "fresh_removed"},
            "provider_requests_denied": 0, "provider_accounts": 0, "recovery_api_calls": 0,
            "normal_requirements": {"cryptography": "50.0.1", "srp": "1.0.22", "unicorn": "2.1.4"} if loaded == "rc" else None}
    return host, receipts, inventories, {"anchor_sha": anchor, "branch": branch, "inputs": inputs}


class Acceptance(unittest.TestCase):
    def test_complete_fictional_control_is_accepted(self):
        host, receipts, inventories, kwargs = fictional()
        self.assertEqual(v.accept(host, receipts, inventories, **kwargs)["outcome"], "passed")

    def test_identity_extra_schema_boolean_counts_and_owner_data_refuse(self):
        for key, value in (("source_commit", "0" * 40), ("provider_accounts", False), ("owner_accounts", 1), ("direct_candidate_installs", 1), ("extra", True)):
            host, receipts, inventories, kwargs = fictional()
            host[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                v.accept(host, receipts, inventories, **kwargs)

    def test_disk_download_cannot_claim_loaded_activation(self):
        for name, field in (("upgrade_download", "loaded"), ("upgraded", "disk"), ("restart", "frontend")):
            host, receipts, inventories, kwargs = fictional()
            receipts[name][field] = None
            with self.subTest(name=name), self.assertRaises(ValueError):
                v.accept(host, receipts, inventories, **kwargs)

    def test_removal_requires_uninstall_restart_and_owned_activity_removal(self):
        for field in ("removed", "removed_activity_store"):
            host, receipts, inventories, kwargs = fictional()
            receipts["fresh_removed"][field] = False
            with self.subTest(field=field), self.assertRaises(ValueError):
                v.accept(host, receipts, inventories, **kwargs)

    def test_download_without_fresh_core_process_refuses(self):
        host, receipts, inventories, kwargs = fictional()
        receipts["upgraded"]["process"] = receipts["upgrade_download"]["process"]
        with self.assertRaisesRegex(ValueError, "actual_restart"):
            v.accept(host, receipts, inventories, **kwargs)

    def test_newest_guard_cannot_rollback_with_config(self):
        host, receipts, inventories, kwargs = fictional()
        receipts["rollback"]["guard"]["witness_sha256"] = "1" * 64
        with self.assertRaisesRegex(ValueError, "newest_ledger"):
            v.accept(host, receipts, inventories, **kwargs)

    def test_marker_loss_replacement_or_zero_count_refuses(self):
        for key, value in (("cohort_sha256", "8" * 64), ("count", 0), ("retained", False)):
            host, receipts, inventories, kwargs = fictional()
            receipts["final"]["activity"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                v.accept(host, receipts, inventories, **kwargs)

    def test_provider_attempt_dependency_change_cleanup_and_actions_refuse(self):
        for case in ("provider", "requirements", "cleanup", "actions"):
            host, receipts, inventories, kwargs = fictional()
            if case == "provider":
                receipts["fresh"]["provider_requests_denied"] = 1
            elif case == "requirements":
                receipts["final"]["normal_requirements"]["cryptography"] = "49.0.0"
            elif case == "cleanup":
                host["qemu_stopped"] = False
            else:
                host["core_actions"].pop()
            with self.subTest(case=case), self.assertRaises(ValueError):
                v.accept(host, receipts, inventories, **kwargs)


class Publication(unittest.TestCase):
    def anchor(self):
        return {"schema": 1, "source_commit": p.SOURCE, "tag": p.TAG, "version": p.VERSION,
            "candidate_sha256": p.CANDIDATE, "inventory_sha256": p.INVENTORY,
            "release_id": 1, "asset_id": 2, "asset_bytes": 628136, "inventory_asset_id": 3,
            "inventory_bytes": 16674, "draft": False, "prerelease": True}

    def test_pending_or_mismatched_publication_anchor_refuses(self):
        for field, value in (("asset_id", None), ("draft", True), ("source_commit", "0" * 40), ("schema", True)):
            with tempfile.TemporaryDirectory() as temporary:
                item = self.anchor()
                item[field] = value
                path = Path(temporary) / "anchor.json"
                path.write_bytes(p.canonical(item))
                with self.subTest(field=field), self.assertRaises(ValueError):
                    p.anchor_at(path, p.digest(path.read_bytes()))

    def test_anchor_hash_duplicate_keys_and_symlinks_refuse(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "anchor.json"
            path.write_bytes(p.canonical(self.anchor()))
            self.assertEqual(p.anchor_at(path, p.digest(path.read_bytes()))["asset_id"], 2)
            with self.assertRaises(ValueError):
                p.anchor_at(path, "0" * 64)
            path.write_bytes(b'{"schema":1,"schema":1}')
            with self.assertRaisesRegex(ValueError, "duplicate"):
                p.anchor_at(path, p.digest(path.read_bytes()))
            link = Path(temporary) / "link.json"
            link.symlink_to(path)
            with self.assertRaises(ValueError):
                p.anchor_at(link, p.digest(path.read_bytes()))

    def test_no_producer_imports_in_independent_consumer(self):
        tree = ast.parse((HERE / "verify_results.py").read_text())
        names = {node.names[0].name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)}
        names |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        self.assertTrue(names <= {"argparse", "hashlib", "json", "pathlib", "re"})

    def test_guard_fixture_has_valid_digest_and_preserves_newest_pair(self):
        import os
        import stat
        tree = ast.parse((HERE / "guest_helper/homecircle_hacs_release_qa/__init__.py").read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "guard_pair")
        namespace = {"os": os, "stat": stat, "IDENTITY": "a" * 64,
            "LEDGER": ".storage/homecircle_findmy/recovery_guard", "WITNESS": ".cache/homecircle_findmy/recovery_guard",
            "digest": p.digest, "check": p.check, "d": SimpleNamespace(
                read_json=lambda path: json.loads(path.read_bytes()),
                write_json=lambda path, value: (path.write_bytes(p.canonical(value)), os.chmod(path, 0o600)))}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "<verified-guard-fixture>", "exec"), namespace)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            one = namespace["guard_pair"](root, 1)
            two = namespace["guard_pair"](root, 2)
            self.assertNotEqual(one, two)
            self.assertEqual(namespace["guard_pair"](root), two)
            witness = next((root / namespace["WITNESS"]).glob("account-*.json"))
            witness.write_text("{}")
            with self.assertRaises(ValueError):
                namespace["guard_pair"](root)

    def test_actual_schedule_is_14_phases_with_23_bounded_normal_actions(self):
        import controller as c
        with tempfile.TemporaryDirectory() as temporary:
            host = object.__new__(c.Controller)
            host.args = SimpleNamespace(branch_commit="d" * 40, output=Path(temporary) / "out",
                inventory=Path("example"), candidate_zip=Path("example"), baseline_inventory=Path("example"),
                baseline_zip=Path("example"), hacs_zip=Path("example"), release_anchor_sha256="c" * 64)
            host.phases, host.actions, host.nonce = [], [], "a" * 32
            host.verify_published_release = lambda: None
            host.download_haos = lambda: None
            host.start_vm = lambda _disk: None
            host.wait_managed = lambda: None
            host.stop_core = lambda: host.actions.append("stop")
            host.prepare = lambda *_args: host.stop_core()
            host.profile_copy = lambda *_args, **_kwargs: host.stop_core()
            _oldhost, receipts, _inventories, _kwargs = fictional()
            def phase(name, start=False):
                if start:
                    host.actions.append("start")
                host.phases.append(receipts[name])
            host.phase = phase
            actual_check = c.check
            def virtual_host_check(condition, code):
                if code not in {"native_linux_amd64_required", "accessible_kvm_required"}:
                    actual_check(condition, code)
            with patch.object(c, "check", virtual_host_check), patch.object(c, "inventory_at", return_value={}), patch.object(c.d, "check_archive"):
                host.run()
            self.assertEqual(tuple(item["phase"] for item in host.phases), v.PHASES)
            self.assertEqual(host.actions, ["stop" if i % 2 == 0 else "start" for i in range(23)])
            self.assertTrue(host.acceptance)

    def test_provider_fence_denies_provider_dns_without_blocking_github(self):
        tree = ast.parse((HERE / "guest_helper/__init__.py").read_text())
        selected = [node for node in tree.body if isinstance(node, (ast.Assign, ast.FunctionDef))]
        namespace = {}
        exec(compile(ast.Module(body=selected, type_ignores=[]), "<verified-dns-fence>", "exec"), namespace)
        for host in ("api.life360.com", "gsa.apple.com", "gateway.icloud.com"):
            with self.assertRaises(OSError):
                namespace["_audit"]("socket.getaddrinfo", (host,))
        namespace["_audit"]("socket.getaddrinfo", ("api.github.com",))
        self.assertEqual(namespace["provider_requests_denied"](), 3)

    def test_finalizer_requires_sealed_files_and_renders_frozen_acyclic_packet(self):
        import finalize_packet as f
        import shutil
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            names = (*f.PAYLOAD, "workflow.template.yml", "finalize_packet.py")
            for name in names:
                shutil.copyfile(HERE / name, source / name)
            shutil.copytree(HERE / "guest_helper", source / "guest_helper")
            files = {path.relative_to(source).as_posix(): {"bytes": path.stat().st_size, "sha256": p.digest(path.read_bytes())}
                     for path in source.rglob("*") if path.is_file()}
            manifest = {"schema": 1, "source_commit": p.SOURCE, "contracts": {"donor": 45, "current": 16, "total": 61},
                        "files": files, "donor_provenance": {}, "scope": {}}
            raw = p.canonical(manifest)
            (source / "PREPARATION-MANIFEST.json").write_bytes(raw)
            anchor = root / "anchor.json"
            anchor.write_bytes(p.canonical(self.anchor()))
            with patch.object(f, "HERE", source):
                result = f.finalize(p.digest(raw), anchor, p.digest(anchor.read_bytes()), root / "packet")
                workflow = (root / "packet" / f.WORKFLOW).read_bytes()
                self.assertEqual(p.digest(workflow), result["workflow_sha256"])
                self.assertNotIn(b"__FROZEN_", workflow)
                self.assertNotIn(b"__RELEASE_", workflow)
                inputs = json.loads((root / "packet" / f.PREFIX / "INPUTS.json").read_bytes())
                self.assertNotIn("INPUTS.json", inputs["files"])
                self.assertNotIn(f.WORKFLOW, inputs["files"])
                (source / "unlisted.py").write_text("extra")
                with self.assertRaisesRegex(ValueError, "exact_file_set"):
                    f.finalize(p.digest(raw), anchor, p.digest(anchor.read_bytes()), root / "other")

    def test_actual_removal_branch_accepts_absent_after_restart_but_never_skips_uninstall(self):
        import asyncio
        tree = ast.parse((HERE / "guest_helper/homecircle_hacs_release_qa/__init__.py").read_text())
        run = next(node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef) and node.name == "run")
        branch = next(node for node in ast.walk(run) if isinstance(node, ast.If)
                      and ast.unparse(node.test) == "name in {'fresh_remove', 'fresh_removed'}")
        wrapper = ast.parse("async def check_branch(self, hacs, name, receipt):\n    pass\n").body[0]
        wrapper.body = deepcopy(branch.body) + [ast.Return(value=ast.Name(id="receipt", ctx=ast.Load()))]
        module = ast.fix_missing_locations(ast.Module(body=[wrapper], type_ignores=[]))

        async def case(name, installed=None, version=None, absent=False):
            removal = AsyncMock()
            repository = None if absent else SimpleNamespace(data=SimpleNamespace(installed=installed, installed_version=version))
            if repository is not None:
                async def uninstall():
                    repository.data.installed = False
                    repository.data.installed_version = None
                repository.uninstall = AsyncMock(side_effect=uninstall)
            entries = SimpleNamespace(async_entries=lambda _domain: [SimpleNamespace(entry_id="example-entry")], async_remove=AsyncMock())
            rehearsal = SimpleNamespace(hass=SimpleNamespace(config_entries=entries), directory=Path("example"), loaded=AsyncMock())
            hacs = SimpleNamespace(repositories=SimpleNamespace(get_by_full_name=lambda _name: repository), data=SimpleNamespace(async_write=AsyncMock()))
            namespace = {"check": p.check, "d": SimpleNamespace(REPOSITORY="jmhjr/HomeCircle"), "removal_status": removal, "inputs": {}}
            exec(compile(module, "<actual-removal-branch>", "exec"), namespace)
            result = await namespace["check_branch"](rehearsal, hacs, name, {})
            self.assertEqual(result, {"removed": True, "removed_activity_store": True})
            removal.assert_awaited_once_with(rehearsal.hass, rehearsal.directory, after_restart=name == "fresh_removed")
            if name == "fresh_remove":
                repository.uninstall.assert_awaited_once()
                entries.async_remove.assert_awaited_once_with("example-entry")
                hacs.data.async_write.assert_awaited_once()
            else:
                entries.async_remove.assert_not_called()
                hacs.data.async_write.assert_not_called()
        asyncio.run(case("fresh_removed", absent=True))
        asyncio.run(case("fresh_removed", installed=False, version=None))
        asyncio.run(case("fresh_remove", installed=True, version=p.TAG))
        for name, installed, version, absent in (("fresh_remove", None, None, True),
                ("fresh_removed", True, p.TAG, False), ("fresh_removed", False, "", False),
                ("fresh_removed", 0, None, False)):
            with self.subTest(name=name, installed=installed, version=version, absent=absent), self.assertRaises(ValueError):
                asyncio.run(case(name, installed=installed, version=version, absent=absent))


if __name__ == "__main__":
    unittest.main()

