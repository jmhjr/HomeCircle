"""Guard-only process checks; the pending Core storage extension is opt-in."""

from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "recovery_restart_cli_test", ROOT / "scripts/validate_recovery_restart.py"
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


@contextmanager
def owned_recovery_cli(receipt, directory):
    """Keep CLI fault isolation and own every descendant on failed acceptance."""
    command = [
        sys.executable,
        "-B",
        str(ROOT / "scripts/validate_recovery_restart.py"),
        "--receipt",
        str(receipt),
    ]
    child = subprocess.Popen(
        command,
        cwd=directory,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = child.communicate(timeout=runner.GUARD_CLI_TIMEOUT_SECONDS)
        assert child.returncode == 0, f"recovery CLI failed: exit={child.returncode}"
        yield subprocess.CompletedProcess(command, child.returncode, stdout, stderr)
    except BaseException:
        # The leader may already have exited while its held-lock child survives.
        # Also cover interruption and assertion/JSON failures after CLI completion.
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.communicate(timeout=runner.CHILD_REAP_TIMEOUT_SECONDS)
        raise


@pytest.mark.parametrize("failure", ["timeout", "exited_probe", "receipt_failure"])
def test_failed_cli_kills_owned_group_and_drains_process(
    tmp_path, monkeypatch, failure
):
    calls, killed = [], []

    def communicate(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1 and failure == "timeout":
            raise subprocess.TimeoutExpired("synthetic-recovery-cli", kwargs["timeout"])
        return "{}", ""

    child = SimpleNamespace(
        pid=12345,
        returncode=1 if failure == "exited_probe" else 0,
        communicate=communicate,
    )

    def popen(*args, **kwargs):
        assert kwargs["start_new_session"] is True
        assert kwargs["stdout"] == kwargs["stderr"] == subprocess.PIPE
        return child

    monkeypatch.setattr(subprocess, "Popen", popen)
    monkeypatch.setattr(os, "killpg", lambda pid, signum: killed.append((pid, signum)))
    expected = {
        "timeout": subprocess.TimeoutExpired,
        "exited_probe": AssertionError,
        "receipt_failure": ValueError,
    }[failure]
    with pytest.raises(expected):
        with owned_recovery_cli(tmp_path / "receipt.json", tmp_path):
            if failure == "receipt_failure":
                raise ValueError("synthetic invalid receipt")
    assert killed == [(12345, signal.SIGKILL)]
    assert calls == [
        {"timeout": runner.GUARD_CLI_TIMEOUT_SECONDS},
        {"timeout": runner.CHILD_REAP_TIMEOUT_SECONDS},
    ]


def test_guard_accounting_survives_process_restart_and_explicit_acknowledgment(
    tmp_path,
):
    receipt = tmp_path / "recovery.json"
    with owned_recovery_cli(receipt, tmp_path) as completed:
        summary = json.loads(completed.stdout)
        detailed = json.loads(receipt.read_text())
        assert summary == {
            key: value for key, value in detailed.items() if key != "receipts"
        }
        assert summary["outcome"] == "passed" and summary["completed"]
        assert summary["processes"] == summary["distinct_processes"] == runner.GUARD_PROCESS_COUNT
        assert summary["network_probes_blocked"] == 26
        assert summary["unexpected_network_attempts"] == summary["apple_requests"] == 0
        assert summary["synthetic_storage_removed"]
        assert not summary["core_storage_runtime_started"]
        assert not summary["account_backup_repair_completed"]
        assert not summary["full_integration_lifecycle"]
        assert all(
            item["completed"] and not item["failed"] for item in detailed["receipts"]
        )
        phases = {item["phase"]: item for item in detailed["receipts"]}
        assert phases["guard_crash"]["exit_code"] == 73
        assert phases["guard_holding"]["exit_code"] < 0
        assert phases["guard_restarted"]["status"]["uncertain"] == 1
        assert phases["guard_blocked"]["status"]["unresolved"] == 3
        assert phases["guard_acknowledged"]["status"]["verified"] == 1
        assert phases["guard_observe_live"]["status"]["pending"] == 1
        assert phases["guard_killed_restart"]["status"]["uncertain"] == 1
        assert phases["guard_corrupt"]["storage_operations_refused"] == 3
        assert phases["guard_retained"]["status"] == {
            "rejected": 1,
            "uncertain": 1,
            "verified": 2,
            "pending": 0,
            "unresolved": 2,
            "limit": 3,
            "blocked": False,
            "review_required": False,
        }
