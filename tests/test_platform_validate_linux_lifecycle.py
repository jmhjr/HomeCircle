"""Pure guard/parser checks; native execution belongs only in disposable Linux."""

import hashlib
import importlib.util
from pathlib import Path
import struct
import subprocess
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "platform_validate_linux_lifecycle_test",
    ROOT / "scripts/platform_validate_linux_lifecycle.py",
)
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)


def test_non_linux_refused_before_file_access_or_process(monkeypatch):
    monkeypatch.setattr(subject.sys, "platform", "darwin")
    monkeypatch.setattr(Path, "read_bytes", lambda *_: pytest.fail("Mac read candidate"))
    monkeypatch.setattr(subprocess, "Popen", lambda *_a, **_k: pytest.fail("Mac launched child"))
    with pytest.raises(ValueError, match="^linux_lifecycle_linux_required$"):
        subject.run_validation("unused.zip")


def test_wrong_candidate_refused_before_process(tmp_path, monkeypatch):
    monkeypatch.setattr(subject.sys, "platform", "linux")
    candidate = tmp_path / "wrong.zip"
    candidate.write_bytes(b"wrong candidate")
    monkeypatch.setattr(subprocess, "Popen", lambda *_a, **_k: pytest.fail("wrong candidate launched"))
    with pytest.raises(ValueError, match="^linux_lifecycle_candidate_hash_refused$"):
        subject.run_validation(candidate)


def test_linux_proc_limits_require_exact_soft_hard_and_units():
    raw = (
        "Limit                     Soft Limit           Hard Limit           Units\n"
        "Max cpu time              90                   90                   seconds\n"
        "Max core file size        0                    0                    bytes\n"
        "Max address space         3221225472           3221225472           bytes\n"
    )
    assert subject.linux_limits(raw) == {
        "cpu_seconds": {"soft": 90, "hard": 90, "units": "seconds"},
        "core_bytes": {"soft": 0, "hard": 0, "units": "bytes"},
        "address_space_bytes": {"soft": 3221225472, "hard": 3221225472, "units": "bytes"},
    }
    with pytest.raises(ValueError, match="^linux_lifecycle_limits_refused$"):
        subject.linux_limits(raw.replace("3221225472", "unlimited"))
    with pytest.raises(ValueError, match="^linux_lifecycle_limits_refused$"):
        subject.linux_limits(raw.replace("Max core file size", "Different limit"))


def test_cancel_fixture_declares_complete_segment_and_specific_native_loop():
    image = subject.synthetic_cancel_image()
    assert struct.unpack_from("<Q", image, 80)[0] == len(image)
    assert image[0x979A0:0x979A8] == bytes.fromhex("81 ff 6c d8 6b 71 74 fe")
    assert image.endswith(bytes.fromhex("48 8b 06 c7 00 00 00 00 00 31 c0 c3"))


@pytest.mark.parametrize("failure", ["exited_probe", "interrupted_communication"])
def test_every_failed_probe_kills_owned_group_even_after_leader_exit(
    tmp_path, monkeypatch, failure
):
    """An exited probe can still own an orphaned, busy native worker."""
    monkeypatch.setattr(subject.sys, "platform", "linux")
    archive = tmp_path / "candidate.zip"
    archive.write_bytes(b"synthetic archive envelope")
    monkeypatch.setattr(subject, "CANDIDATE_SHA256", hashlib.sha256(archive.read_bytes()).hexdigest())
    monkeypatch.setattr(subject, "CANDIDATE_MEMBERS", 1)
    monkeypatch.setitem(
        subject.sys.modules, "validate_release",
        SimpleNamespace(inspect_archive=lambda *_: {"fixture.py": b"fixture"}),
    )
    calls, killed = [], []

    def communicate(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1 and failure == "interrupted_communication":
            raise KeyboardInterrupt
        return "", '{"failure_stage":"cleanup","failure_type":"ValueError"}'

    # The leader has already exited; cleanup must still kill its session group.
    child = SimpleNamespace(pid=12345, returncode=1, communicate=communicate)

    def popen(*args, **kwargs):
        assert kwargs["start_new_session"] is True
        return child

    monkeypatch.setattr(subject.subprocess, "Popen", popen)
    monkeypatch.setattr(subject.os, "killpg", lambda pid, signum: killed.append((pid, signum)))
    expected = KeyboardInterrupt if failure == "interrupted_communication" else ValueError
    with pytest.raises(expected):
        subject.run_validation(archive)
    assert killed == [(12345, subject.signal.SIGKILL)]
    assert calls == [{"timeout": 60}, {}]
