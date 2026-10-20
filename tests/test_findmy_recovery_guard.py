"""Synthetic durable recovery accounting without Apple or owner credentials."""

import asyncio
import json
import os
import subprocess
import sys
import threading

import pytest

from custom_components.homecircle.findmy_recovery_guard import (
    RecoveryGuard,
    RecoveryGuardBlocked,
    RecoveryGuardStorageError,
    get_recovery_guard,
)

IDENTITY = "a" * 64
OTHER = "b" * 64


def guard(tmp_path):
    return RecoveryGuard(tmp_path / "guard")


async def reject(service, identity=IDENTITY):
    async with service.attempt(identity) as attempt:
        assert attempt.outcome is None
        await attempt.before_dispatch()
        await attempt.refused()
        assert attempt.finished and attempt.outcome == "rejected"


async def test_pre_proof_failure_and_context_entry_do_not_reserve(tmp_path):
    service = guard(tmp_path)
    async with service.attempt(IDENTITY):
        assert (await service.status(IDENTITY))["unresolved"] == 0
    with pytest.raises(TimeoutError):
        async with service.attempt(IDENTITY):
            raise TimeoutError
    assert (await service.status(IDENTITY))["unresolved"] == 0
    assert not (service.root / "ledger.json").exists()


async def test_attempt_callbacks_cannot_reserve_after_context_releases_lock(tmp_path):
    service = guard(tmp_path)
    async with service.attempt(IDENTITY) as attempt:
        pass
    with pytest.raises(RuntimeError):
        await attempt.before_dispatch()
    assert (await service.status(IDENTITY))["unresolved"] == 0


async def test_new_storage_directory_creation_must_be_durable(tmp_path, monkeypatch):
    service = guard(tmp_path)
    monkeypatch.setattr(
        os,
        "fsync",
        lambda *args: (_ for _ in ()).throw(OSError("synthetic fsync failure")),
    )
    with pytest.raises(RecoveryGuardStorageError):
        async with service.attempt(IDENTITY):
            pytest.fail("Unsafe storage entered unlock")
    assert not (service.root / "ledger.json").exists()


async def test_verified_submission_does_not_clear_prior_unresolved(tmp_path):
    service = guard(tmp_path)
    await reject(service)
    async with service.attempt(IDENTITY) as attempt:
        await attempt.before_dispatch()
        assert (await service.status(IDENTITY))["pending"] == 1
        await attempt.verified()
        assert attempt.finished and attempt.outcome == "verified"
    assert attempt.outcome == "verified"
    assert await service.status(IDENTITY) == {
        "rejected": 1,
        "uncertain": 0,
        "pending": 0,
        "verified": 1,
        "unresolved": 1,
        "limit": 3,
        "blocked": False,
    }
    assert "a" * 64 in (service.root / "ledger.json").read_text()
    assert set(
        json.loads((service.root / "ledger.json").read_text())["accounts"][IDENTITY]
    ) == {
        "rejected",
        "uncertain",
        "pending",
        "verified",
    }


async def test_refusal_unknown_outcome_limit_and_explicit_reset(tmp_path):
    service = guard(tmp_path)
    await reject(service)
    with pytest.raises(TimeoutError):
        async with service.attempt(IDENTITY) as attempt:
            await attempt.before_dispatch()
            raise TimeoutError
    async with service.attempt(IDENTITY) as attempt:
        await attempt.before_dispatch()
        await attempt.verified()
    await reject(service)
    expected = {
        "rejected": 2,
        "uncertain": 1,
        "pending": 0,
        "verified": 1,
        "unresolved": 3,
        "limit": 3,
        "blocked": True,
    }
    assert await service.status(IDENTITY) == expected
    with pytest.raises(RecoveryGuardBlocked) as blocked:
        async with RecoveryGuard(service.root).attempt(IDENTITY) as attempt:
            await attempt.before_dispatch()
    assert blocked.value.code == "recovery_guard_blocked"
    assert await service.status(IDENTITY) == expected
    reset = await service.reset(IDENTITY)
    assert reset["unresolved"] == 0 and reset["verified"] == 1
    await reject(service)
    assert (await service.status(IDENTITY))["rejected"] == 1


async def test_separate_process_reads_counts_and_crash_pending_becomes_uncertain(
    tmp_path,
):
    service = guard(tmp_path)
    await reject(service)
    code = """
import asyncio, json, os, sys
from pathlib import Path
from custom_components.homecircle.findmy_recovery_guard import RecoveryGuard
async def run():
    service = RecoveryGuard(Path(sys.argv[1]))
    assert (await service.status('a' * 64))['rejected'] == 1
    async with service.attempt('a' * 64) as attempt:
        await attempt.before_dispatch()
        os._exit(0)
asyncio.run(run())
"""
    result = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-c", code, str(service.root)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    persisted = json.loads((service.root / "ledger.json").read_text())["accounts"][
        IDENTITY
    ]
    assert persisted["pending"] is not None and persisted["uncertain"] == 0
    status = await RecoveryGuard(service.root).status(IDENTITY)
    assert (
        status["rejected"] == 1 and status["uncertain"] == 1 and status["pending"] == 0
    )


async def test_same_account_serializes_across_guard_instances_other_account_runs(
    tmp_path,
):
    first, second = guard(tmp_path), guard(tmp_path)
    entered, release, same_entered, other_entered = [asyncio.Event() for _ in range(4)]

    async def holding():
        async with first.attempt(IDENTITY) as attempt:
            await attempt.before_dispatch()
            entered.set()
            await release.wait()
            await attempt.refused()

    async def waiting():
        async with second.attempt(IDENTITY) as attempt:
            same_entered.set()
            await attempt.before_dispatch()
            await attempt.refused()

    async def independent():
        async with second.attempt(OTHER) as attempt:
            other_entered.set()
            await attempt.before_dispatch()
            await attempt.verified()

    owner = asyncio.create_task(holding())
    await entered.wait()
    waiter = asyncio.create_task(waiting())
    independent_task = asyncio.create_task(independent())
    await asyncio.wait_for(other_entered.wait(), 1)
    assert not same_entered.is_set()
    assert (await first.status(IDENTITY))["pending"] == 1
    with pytest.raises(RecoveryGuardBlocked):
        await second.reset(IDENTITY)
    release.set()
    await asyncio.gather(owner, waiter, independent_task)
    assert (await first.status(IDENTITY))["rejected"] == 2
    assert (await first.status(OTHER))["verified"] == 1


async def test_separate_process_cannot_enter_or_reset_held_account(tmp_path):
    service = guard(tmp_path)
    async with service.attempt(IDENTITY):
        code = """
import asyncio, json, sys
from pathlib import Path
from custom_components.homecircle.findmy_recovery_guard import RecoveryGuard, RecoveryGuardBlocked
async def run():
    service = RecoveryGuard(Path(sys.argv[1]))
    try:
        await service.reset('a' * 64)
    except RecoveryGuardBlocked:
        pass
    else:
        raise AssertionError('reset entered live proof')
    async def enter():
        async with service.attempt('a' * 64):
            raise AssertionError('entered live proof')
    task = asyncio.create_task(enter())
    await asyncio.sleep(0.1)
    assert not task.done()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
asyncio.run(run())
"""
        result = await asyncio.to_thread(
            subprocess.run,
            [sys.executable, "-c", code, str(service.root)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("_iteration", range(5))
async def test_concurrent_submissions_cannot_oversubscribe(tmp_path, _iteration):
    services = [guard(tmp_path) for _ in range(7)]
    results = await asyncio.gather(
        *(reject(service) for service in services), return_exceptions=True
    )
    assert sum(result is None for result in results) == 3
    assert sum(isinstance(result, RecoveryGuardBlocked) for result in results) == 4, (
        results
    )
    assert (await services[0].status(IDENTITY))["unresolved"] == 3


async def test_cancelled_reservation_drains_and_clears_proven_undispatched_submission(
    tmp_path, monkeypatch
):
    service = guard(tmp_path)
    started, finish = threading.Event(), threading.Event()
    original = service._write
    attempts = []

    def slow_write(root, payload):
        started.set()
        assert finish.wait(3)
        return original(root, payload)

    monkeypatch.setattr(service, "_write", slow_write)

    async def recovering():
        async with service.attempt(IDENTITY) as attempt:
            attempts.append(attempt)
            await attempt.before_dispatch()

    task = asyncio.create_task(recovering())
    assert await asyncio.to_thread(started.wait, 2)
    task.cancel()
    await asyncio.sleep(0.03)
    assert not task.done()
    finish.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    status = await service.status(IDENTITY)
    assert status["uncertain"] == 0 and status["pending"] == 0
    assert attempts[0].finished and attempts[0].outcome == "abandoned"
    await reject(service)
    assert (await service.status(IDENTITY))["unresolved"] == 1


async def test_cancellation_after_process_lock_acquisition_does_not_strand_lock(
    tmp_path, monkeypatch
):
    service = guard(tmp_path)
    acquired, finish = threading.Event(), threading.Event()
    original = service._try_account_lock

    def slow_acquire(identity):
        descriptor = original(identity)
        acquired.set()
        assert finish.wait(3)
        return descriptor

    monkeypatch.setattr(service, "_try_account_lock", slow_acquire)

    async def recovering():
        async with service.attempt(IDENTITY):
            pytest.fail("Cancelled lock acquisition entered unlock")

    task = asyncio.create_task(recovering())
    assert await asyncio.to_thread(acquired.wait, 2)
    task.cancel()
    finish.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.wait_for(reject(RecoveryGuard(service.root)), 1)


async def test_cancelled_failed_reservation_never_logs_executor_failure(
    tmp_path, monkeypatch, caplog
):
    service = guard(tmp_path)
    entered, release = threading.Event(), threading.Event()

    def fail_write(*args):
        entered.set()
        assert release.wait(3)
        raise OSError("synthetic private storage failure canary")

    monkeypatch.setattr(service, "_write", fail_write)

    async def recover():
        async with service.attempt(IDENTITY) as attempt:
            await attempt.before_dispatch()

    task = asyncio.create_task(recover())
    assert await asyncio.to_thread(entered.wait, 2)
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()
    release.set()
    # Storage failure remains authoritative, as before outcome shielding.
    with pytest.raises(RecoveryGuardStorageError):
        await task
    await asyncio.sleep(0)
    assert "synthetic private storage failure canary" not in caplog.text
    assert (await service.status(IDENTITY))["unresolved"] == 0


async def test_cancellation_after_dispatch_hook_returns_is_uncertain(tmp_path):
    service = guard(tmp_path)
    dispatched = asyncio.Event()
    attempts = []

    async def recovering():
        async with service.attempt(IDENTITY) as attempt:
            attempts.append(attempt)
            await attempt.before_dispatch()
            dispatched.set()
            await asyncio.Event().wait()

    task = asyncio.create_task(recovering())
    await dispatched.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    status = await service.status(IDENTITY)
    assert status["uncertain"] == 1 and status["pending"] == 0
    assert attempts[0].finished and attempts[0].outcome == "uncertain"


async def test_cancelled_verified_write_publishes_durable_outcome_before_reraising(
    tmp_path, monkeypatch
):
    service = guard(tmp_path)
    started, finish = threading.Event(), threading.Event()
    original = service._transaction

    def delayed_transaction(identity, action, *args):
        if action == "verified":
            started.set()
            assert finish.wait(3)
        return original(identity, action, *args)

    monkeypatch.setattr(service, "_transaction", delayed_transaction)
    async with service.attempt(IDENTITY) as attempt:
        await attempt.before_dispatch()
        task = asyncio.create_task(attempt.verified())
        assert await asyncio.to_thread(started.wait, 2)
        task.cancel()
        finish.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert attempt.finished and attempt.outcome == "verified"
    status = await service.status(IDENTITY)
    assert status["verified"] == 1 and status["unresolved"] == 0


@pytest.mark.parametrize("fault", ["write", "replace", "file_fsync", "directory_fsync"])
async def test_storage_failure_prevents_dispatch_and_preserves_conservative_counts(
    tmp_path, monkeypatch, fault
):
    service = guard(tmp_path)
    await reject(service)
    original_fsync = os.fsync
    calls = []

    def failing_fsync(descriptor):
        calls.append(descriptor)
        if fault == "file_fsync" or len(calls) == 2:
            raise OSError("synthetic local storage failure")
        original_fsync(descriptor)

    with monkeypatch.context() as patch:
        if fault == "write":
            patch.setattr(
                json,
                "dump",
                lambda *args, **kwargs: (_ for _ in ()).throw(
                    OSError("synthetic write failure")
                ),
            )
        elif fault == "replace":
            patch.setattr(
                os,
                "replace",
                lambda *args, **kwargs: (_ for _ in ()).throw(
                    OSError("synthetic replace failure")
                ),
            )
        else:
            patch.setattr(os, "fsync", failing_fsync)
        dispatched = False
        with pytest.raises(RecoveryGuardStorageError) as failure:
            async with service.attempt(IDENTITY) as attempt:
                await attempt.before_dispatch()
                dispatched = True
        assert failure.value.code == "recovery_guard_storage"
        assert not dispatched
    status = await service.status(IDENTITY)
    assert status["rejected"] == 1
    assert status["unresolved"] in (1, 2)
    assert not list(service.root.glob(".ledger-*"))


@pytest.mark.parametrize(
    "fault",
    [
        "corrupt",
        "schema",
        "ledger_permissions",
        "root_permissions",
        "file_symlink",
        "lock_symlink",
        "parent_symlink",
        "hardlink",
    ],
)
async def test_unsafe_storage_fails_closed_without_overwriting(tmp_path, fault):
    service = guard(tmp_path)
    await reject(service)
    ledger = service.root / "ledger.json"
    if fault == "corrupt":
        ledger.write_bytes(b"invalid synthetic json")
    elif fault == "schema":
        ledger.write_text('{"version":1,"accounts":{"bad":{"rejected":false}}}')
    elif fault == "ledger_permissions":
        ledger.chmod(0o644)
    elif fault == "root_permissions":
        service.root.chmod(0o755)
    elif fault == "file_symlink":
        target = tmp_path / "saved"
        ledger.rename(target)
        ledger.symlink_to(target)
    elif fault == "lock_symlink":
        lock = service.root / "ledger.lock"
        target = tmp_path / "saved"
        lock.rename(target)
        lock.symlink_to(target)
    elif fault == "parent_symlink":
        original = tmp_path / "original"
        service.root.rename(original)
        service.root.symlink_to(original, target_is_directory=True)
    else:
        os.link(ledger, tmp_path / "linked")
    before = ledger.read_bytes()
    with pytest.raises(RecoveryGuardStorageError):
        async with service.attempt(IDENTITY) as attempt:
            await attempt.before_dispatch()
    assert ledger.read_bytes() == before


@pytest.mark.parametrize(
    "identity", ["A" * 64, "a" * 63, "g" * 64, "synthetic@example.invalid", None, 123]
)
async def test_identity_must_be_validated_hash_no_username_fallback(tmp_path, identity):
    service = guard(tmp_path)
    with pytest.raises(ValueError):
        await service.status(identity)
    with pytest.raises(ValueError):
        async with service.attempt(identity):
            pass
    assert not service.root.exists()


async def test_hass_service_is_shared_outside_account_namespace(
    hass, tmp_path, monkeypatch
):
    monkeypatch.setattr(
        hass.config, "path", lambda *parts: str(tmp_path.joinpath(*parts))
    )
    service = get_recovery_guard(hass)
    assert get_recovery_guard(hass) is service
    assert (
        service.root == tmp_path / ".storage" / "homecircle_findmy" / "recovery_guard"
    )
    await reject(service)
    for path in (service.root.parent, service.root):
        assert path.stat().st_mode & 0o777 == 0o700
    for path in service.root.iterdir():
        assert path.stat().st_mode & 0o777 == 0o600
    assert (await RecoveryGuard(service.root).status(IDENTITY))["rejected"] == 1
