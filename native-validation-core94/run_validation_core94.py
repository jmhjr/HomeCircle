"""Bounded, Linux-only exact-input AMD64 upgrade and recovery rehearsal driver."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time
import zipfile

ARCHIVES = {
    "published-homecircle.zip": "5f20d536e1b5378bef7f0b972bbfbc7ced911063aea16a0a8f56d2ffa1210cd2",
    "recorded-patch.zip": "0362a71b0d12e12bbe38c20192f130f505011500e9a1d31a3531547c5055d80a",
    "homecircle-candidate.zip": "f0477a91e78181fe1f8d80ada176a1739e10a7502abe7ee6ee2240571280d1f5",
}
SCRIPTS = {
    "scripts/validate_candidate_upgrade.py": "c1c0b903d47e3fee90a4c377e493ee555e6df3bf5f75b2d3cbce394fb30e2bdf",
    "scripts/validate_recovery_restart.py": "acb71afbf58424939ab736e350bbef9b37f582af15c4eb508186ea3f54509e1f",
    "scripts/validate_release.py": "20c0466b4fa70a83c5f282bfcd07b0d2e6f5a3a1a09bf90072649441b2ad7f37",
    "scripts/build_release.py": "0c1ac7f979817bd5fc2cd4a4101571931488d6972bc6f181a26ac21edcf8c7d0",
}
UPGRADE_PHASES = (
    "published_install", "candidate_upgrade", "candidate_restart", "candidate_ledger",
    "candidate_ledger_restart", "package_only_rollback", "package_only_reupgrade",
    "candidate_backup_restore", "published_backup_rollback", "final_candidate_upgrade",
)
RECOVERY_PHASES = (
    "guard_verified", "guard_crash", "guard_restarted", "guard_limit", "guard_blocked",
    "guard_acknowledged", "guard_holding", "guard_observe_live", "guard_killed_restart",
    "guard_ack_retry", "guard_corrupt", "guard_repaired", "storage_crash_committed",
    "storage_recover", "storage_corrupt", "storage_restored", "storage_foreign",
    "storage_wrong_key", "storage_restored", "guard_retained",
)
UPGRADE_SECONDS = 2100
RECOVERY_SECONDS = 1200
REAP_SECONDS = 15
CANDIDATE = ARCHIVES["homecircle-candidate.zip"]
VERSION = "0.1.0-beta.19"


class Refused(RuntimeError):
    """Diagnostics are fixed labels only, never command output or fixture state."""


class Terminated(BaseException):
    def __init__(self, signum):
        self.signum = signum


@contextmanager
def termination_guard():
    """Route external termination through the owned-session cleanup path."""
    previous = {}

    def terminate(signum, _frame):
        raise Terminated(signum)

    try:
        for signum in (signal.SIGTERM, signal.SIGHUP):
            previous[signum] = signal.signal(signum, terminate)
        yield
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def require_linux():
    if sys.platform != "linux":
        raise Refused("linux_required")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path):
    if path.stat().st_size > 2 * 1024**2:
        raise Refused("receipt_size_refused")
    return json.loads(path.read_text())


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as output:
        json.dump(value, output, indent=2, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(path)


def check(condition, label):
    if not condition:
        raise Refused(label)


def check_inputs(qa):
    """Check all fixed archives/scripts and each exact candidate inventory entry."""
    for name, expected in {**ARCHIVES, **SCRIPTS}.items():
        check(digest((qa / name).read_bytes()) == expected, "input_hash_refused")
    inventory_path = qa / "homecircle-inventory.json"
    inventory = read_json(inventory_path)
    check(inventory.get("archive_sha256") == CANDIDATE, "inventory_archive_refused")
    files = inventory.get("files")
    check(isinstance(files, dict) and len(files) == 112, "inventory_count_refused")
    with zipfile.ZipFile(qa / "homecircle-candidate.zip") as archive:
        names = archive.namelist()
        check(len(names) == len(set(names)) == 112 and set(names) == set(files), "inventory_names_refused")
        for name, expected in files.items():
            raw = archive.read(name)
            check(expected == {"bytes": len(raw), "sha256": digest(raw)}, "inventory_bytes_refused")
        check(json.loads(archive.read("manifest.json"))["version"] == VERSION, "candidate_version_refused")
    # The recovery CLI imports this tree directly, while upgrade phases extract
    # the ZIP themselves. Bind both execution paths to the same candidate bytes.
    package = qa / "custom_components/homecircle"
    check(not package.is_symlink(), "candidate_source_symlink_refused")
    actual = {}
    for path in package.rglob("*"):
        check(not path.is_symlink(), "candidate_source_symlink_refused")
        if path.is_file() and "__pycache__" not in path.parts:
            raw = path.read_bytes()
            actual[path.relative_to(package).as_posix()] = {"bytes": len(raw), "sha256": digest(raw)}
    check(actual == files, "candidate_source_bytes_refused")
    return {
        "archive_sha256": dict(ARCHIVES), "script_sha256": dict(SCRIPTS),
        "inventory_sha256": digest(inventory_path.read_bytes()), "candidate_members": 112,
        "candidate_source_file_match": True,
    }


def verify_upgrade(path, label, baseline_name, baseline_payload):
    value = read_json(path)
    check(value.get("result") == "passed_with_package_only_rollback_limit", "upgrade_outcome_refused")
    check(value.get("baseline_label") == label and value.get("core_version") == "2026.9.4", "upgrade_metadata_refused")
    check(value.get("disposable_configuration_removed") is True, "upgrade_cleanup_refused")
    baseline = value.get("published", {})
    candidate = value.get("candidate", {})
    check(baseline == {
        "archive_sha256": ARCHIVES[baseline_name], "files": 109,
        "payload_sha256": baseline_payload, "version": VERSION,
    }, "upgrade_baseline_refused")
    check(candidate == {
        "archive_sha256": CANDIDATE, "files": 112,
        "payload_sha256": "f608cc7d655c500daf46959c1e1c6190fc297afc6fd77916ccaf54ad505fa76e",
        "version": VERSION,
    }, "upgrade_candidate_refused")
    phases = value.get("phases", [])
    check([item.get("phase") for item in phases] == list(UPGRADE_PHASES), "upgrade_phases_refused")
    snapshots = {item.get("preserved_state_sha256") for item in phases}
    check(len(snapshots) == 1 and all(isinstance(item, str) and len(item) == 64 for item in snapshots), "upgrade_persistence_refused")
    ledger = None
    for item in phases:
        phase = item["phase"]
        old = phase in {"published_install", "package_only_rollback", "published_backup_rollback"}
        check(item.get("result") == "passed" and item.get("loaded_version") == VERSION, "upgrade_phase_result_refused")
        check(item.get("installed_package_files") == (109 if old else 112), "upgrade_phase_files_refused")
        check(item.get("installed_package_sha256") == (baseline_payload if old else candidate["payload_sha256"]), "upgrade_phase_payload_refused")
        check((item.get("selected_people"), item.get("selected_items"), item.get("accounts")) == (2, 2, 1), "upgrade_selection_refused")
        check(type(item.get("blocked_external_connections")) is int and item["blocked_external_connections"] >= 0, "upgrade_network_receipt_refused")
        check(type(item.get("synthetic_report_fetch_calls")) is int and item["synthetic_report_fetch_calls"] > 0, "upgrade_transport_refused")
        expected_ledger = phase in {"candidate_ledger", "candidate_ledger_restart", "candidate_backup_restore"}
        check(item.get("identity_ledger") == ("present" if expected_ledger else "absent"), "upgrade_ledger_refused")
        if expected_ledger:
            current = item.get("identity_ledger_sha256")
            check(isinstance(current, str) and len(current) == 64, "upgrade_ledger_digest_refused")
            ledger = ledger or current
            check(current == ledger, "upgrade_ledger_restore_refused")
    check("External sockets denied." in value.get("transport", ""), "upgrade_network_scope_refused")
    check(value.get("rollback_limit", "").startswith("Published beta19 polling drops the candidate identity ledger."), "upgrade_rollback_limit_refused")
    check("complete persistent-state backup restores" in value["rollback_limit"], "upgrade_coherent_restore_refused")
    return {"phases": 10, "coherent_backup_restore": True, "package_only_rollback_limit_retained": True}


def verify_recovery(path):
    value = read_json(path)
    for name in (
        "completed", "synthetic_storage_removed", "core_storage_runtime_started",
        "account_backup_repair_completed", "manual_account_backup_excludes_recovery_guard",
        "restoring_stale_guard_ledger_is_undetectable",
    ):
        check(value.get(name) is True, "recovery_acceptance_refused")
    check(value.get("outcome") == "passed", "recovery_outcome_refused")
    check(value.get("storage_smoke_only") is False and value.get("full_integration_lifecycle") is False, "recovery_scope_refused")
    check((value.get("processes"), value.get("distinct_processes"), value.get("network_probes_blocked")) == (20, 20, 40), "recovery_counts_refused")
    check(value.get("unexpected_network_attempts") == value.get("apple_requests") == 0, "recovery_network_refused")
    receipts = value.get("receipts", [])
    check([item.get("phase") for item in receipts] == list(RECOVERY_PHASES), "recovery_phases_refused")
    check(len({item.get("pid") for item in receipts}) == 20, "recovery_distinct_processes_refused")
    for item in receipts:
        check(item.get("completed") is True and item.get("failed") is False, "recovery_child_refused")
        check(item.get("network_probes_blocked") == 2 and item.get("unexpected_network_attempts") == 0, "recovery_probe_refused")
        phase, code = item["phase"], item.get("exit_code")
        if phase in {"guard_crash", "storage_crash_committed"}:
            check(code == 73 and item.get("expected_fault_exit") is True, "recovery_crash_refused")
        elif phase == "guard_holding":
            check(type(code) is int and code < 0 and item.get("expected_fault_exit") is True, "recovery_holder_refused")
        else:
            check(code == 0 and item.get("expected_fault_exit") is False, "recovery_exit_refused")
        if phase.startswith("storage_") and phase != "storage_crash_committed":
            check(item.get("recovery_guard_unchanged") is True, "recovery_guard_restore_refused")
    check(sum(item["network_probes_blocked"] for item in receipts) == 40, "recovery_probe_total_refused")
    return {"processes": 20, "distinct_processes": 20, "network_probes_blocked": 40, "coherent_backup_restore": True}


def run_owned_job(command, *, cwd, log_path, limit, validate):
    """Own the entire CLI session through output validation and post-input checks."""
    started = time.monotonic()
    with log_path.open("x") as log:
        child = None
        try:
            child = subprocess.Popen(
                command, cwd=cwd, stdin=subprocess.DEVNULL, stdout=log,
                stderr=subprocess.STDOUT, text=True, start_new_session=True,
            )
            child.communicate(timeout=limit)
            check(child.returncode == 0, "job_exit_refused")
            result = validate()
            return {"pid": child.pid, "exit_code": child.returncode,
                    "seconds": round(time.monotonic() - started, 3), "limit_seconds": limit, **result}
        except BaseException:
            # The CLI leader may have exited while descendants still own the group.
            if child is not None:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.communicate(timeout=REAP_SECONDS)
            raise


def run_validation(qa_root, output):
    require_linux()  # Must precede file inspection, metadata imports and spawning.
    check(platform.machine() == "x86_64", "amd64_required")
    qa, output = Path(qa_root).resolve(), Path(output).resolve()
    check(not output.exists(), "fresh_output_required")
    output.mkdir(parents=True, mode=0o700)
    receipt = {"schema": 1, "outcome": "in_progress", "completed": False,
               "candidate_sha256": CANDIDATE, "candidate_changed": False,
               "owner_accounts_used": False, "account_requests": 0,
               "current_stage": "inputs", "jobs": []}
    driver_path = output / "driver.json"
    stage = "inputs"
    try:
        print(json.dumps({"stage": stage, "outcome": "started"}), flush=True)
        write_json(driver_path, receipt)
        receipt["inputs_before"] = check_inputs(qa)
        receipt["driver_sha256"] = digest(Path(__file__).read_bytes())
        stage = "metadata"
        core = importlib.metadata.version("homeassistant")
        check(core == "2026.9.4", "core_version_refused")
        receipt["environment"] = {
            "system": platform.system(), "machine": platform.machine(),
            "python": platform.python_version(), "core": core,
            "libc": list(platform.libc_ver()), "kernel": platform.release(),
        }
        write_json(driver_path, receipt)
        print(json.dumps({"stage": "inputs", "outcome": "passed", "machine": "x86_64", "core": core}), flush=True)
        specs = (
            ("upgrade-published", "canonical_published_beta19", "published-homecircle.zip", "46b5792ef506ce0fe40a67849c14a94ecc1ba215d08ed232f8c71d6a21677495"),
            ("upgrade-recorded", "reconstructed_recorded_patch", "recorded-patch.zip", "2519d623e2186016bd14a153a330de33034711d7bd499dc26aacdadc5994d8c3"),
            ("recovery", None, None, None),
        )
        for name, label, baseline, payload in specs:
            stage = name
            receipt["current_stage"] = stage
            write_json(driver_path, receipt)
            check(check_inputs(qa) == receipt["inputs_before"], "inputs_changed")
            if baseline:
                job_output = output / name
                path = job_output / "summary.json"
                command = [sys.executable, "-B", str(qa / "scripts/validate_candidate_upgrade.py"),
                           "--published-zip", str(qa / baseline), "--baseline-sha256", ARCHIVES[baseline],
                           "--baseline-label", label, "--candidate-zip", str(qa / "homecircle-candidate.zip"),
                           "--output-dir", str(job_output)]
                limit = UPGRADE_SECONDS
            else:
                path = output / "recovery.json"
                command = [sys.executable, "-B", str(qa / "scripts/validate_recovery_restart.py"),
                           "--include-storage", "--receipt", str(path)]
                limit = RECOVERY_SECONDS

            def validate():
                details = verify_upgrade(path, label, baseline, payload) if baseline else verify_recovery(path)
                check(check_inputs(qa) == receipt["inputs_before"], "inputs_changed")
                return {**details, "receipt": path.relative_to(output).as_posix(),
                        "receipt_sha256": digest(path.read_bytes())}

            print(json.dumps({"job": name, "outcome": "started", "limit_seconds": limit}), flush=True)
            result = run_owned_job(command, cwd=qa, log_path=output / (name + ".log"), limit=limit, validate=validate)
            receipt["jobs"].append({"job": name, "outcome": "passed", "log": name + ".log", **result})
            write_json(driver_path, receipt)
            print(json.dumps({"job": name, "outcome": "passed", "seconds": result["seconds"]}), flush=True)
        receipt["inputs_after"] = check_inputs(qa)
        check(receipt["inputs_after"] == receipt["inputs_before"], "inputs_changed")
        check(digest(Path(__file__).read_bytes()) == receipt["driver_sha256"], "driver_changed")
        receipt.update({"outcome": "passed", "completed": True, "current_stage": "complete", "upgrade_phases": 20,
                        "recovery_processes": 20, "network_probes_blocked": 40,
                        "full_managed_core_lifecycle": False, "apple_authentication": False,
                        "production_backup_acceptance": False})
        write_json(driver_path, receipt)
        return receipt
    except BaseException as error:
        receipt.update({"outcome": "failed", "completed": False, "current_stage": stage, "failure_stage": stage,
                        "failure_type": type(error).__name__})
        if isinstance(error, Refused):
            receipt["failure_code"] = str(error)
        try:
            write_json(driver_path, receipt)
        except OSError:
            pass
        raise


def main():
    # No argument-supplied files or processes are touched on an unsupported host.
    require_linux()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qa-root", type=Path, default=Path("/qa"))
    parser.add_argument("--output", type=Path, default=Path("/qa/results/amd64-upgrade-recovery"))
    args = parser.parse_args()
    try:
        with termination_guard():
            result = run_validation(args.qa_root, args.output)
    except BaseException as error:
        print(json.dumps({"outcome": "failed", "failure_type": type(error).__name__}), flush=True)
        if isinstance(error, Terminated):
            return 128 + error.signum
        return 130 if isinstance(error, KeyboardInterrupt) else 1
    print(json.dumps({"outcome": result["outcome"], "completed": True,
                      "upgrade_phases": 20, "recovery_processes": 20}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
