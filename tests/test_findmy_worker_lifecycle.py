"""Owned emulator child lifetime with fake processes; no native calls or network."""

import asyncio
import base64
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.homecircle._findmy_runtime import provider as runtime


class Child:
    def __init__(self, wait_gate=None):
        self.returncode = None
        self.kills = self.waits = 0
        self.wait_gate = wait_gate
        self.wait_started = asyncio.Event()
        self.stdin = SimpleNamespace(write=lambda raw: None, drain=AsyncMock())
        self.stdout = SimpleNamespace(readline=AsyncMock(return_value=b'{"provisioned":false}\n'))

    def kill(self):
        self.kills += 1

    async def wait(self):
        self.waits += 1
        self.wait_started.set()
        if self.wait_gate is not None:
            await self.wait_gate.wait()
        self.returncode = -9
        return self.returncode


async def test_cancelled_spawn_is_not_abandoned_and_late_child_is_reaped(monkeypatch):
    started, finish_spawn = asyncio.Event(), asyncio.Event()
    child = Child()
    async def spawn(*args, **kwargs):
        started.set()
        await finish_spawn.wait()
        return child
    monkeypatch.setattr(runtime.asyncio, "create_subprocess_exec", spawn)
    worker = runtime.Worker()
    opening = asyncio.create_task(worker.open("public-library", {"host_uuid": "a" * 32}, {}))
    await started.wait()
    opening.cancel()
    await asyncio.sleep(0)
    assert not opening.done()
    finish_spawn.set()
    with pytest.raises(asyncio.CancelledError):
        await opening
    assert child.kills == child.waits == 1 and worker.process is None
    assert worker._spawn is None and worker._closed


async def test_repeated_cancel_during_close_retains_child_until_reaped():
    finish_wait = asyncio.Event()
    child = Child(finish_wait)
    worker = runtime.Worker()
    worker.process = child
    closing = asyncio.create_task(worker.close())
    await child.wait_started.wait()
    closing.cancel()
    await asyncio.sleep(0)
    closing.cancel()
    await asyncio.sleep(0)
    assert worker.process is child and not closing.done()
    finish_wait.set()
    with pytest.raises(asyncio.CancelledError):
        await closing
    assert child.kills == child.waits == 1 and worker.process is None
    await worker.close()
    assert child.waits == 1


async def test_cancelled_ipc_also_drains_repeated_cancel_and_refuses_reuse():
    reading = asyncio.Event()
    finish_wait = asyncio.Event()
    child = Child(finish_wait)
    async def readline():
        reading.set()
        await asyncio.Future()
    child.stdout.readline = readline
    worker = runtime.Worker()
    worker.process = child
    calling = asyncio.create_task(worker.call({"op": "fixture"}))
    await reading.wait()
    calling.cancel()
    await child.wait_started.wait()
    calling.cancel()
    finish_wait.set()
    with pytest.raises(asyncio.CancelledError):
        await calling
    assert worker.process is None and child.kills == child.waits == 1
    with pytest.raises(runtime.IdentityUnavailable, match="^identity_worker_unavailable$"):
        await worker.call({"op": "fixture"})


async def test_failed_wait_retains_ownership_for_an_explicit_cleanup_retry():
    child = Child()
    wait = child.wait
    child.wait = AsyncMock(side_effect=OSError("private-wait-fixture"))
    worker = runtime.Worker()
    worker.process = child
    with pytest.raises(runtime.IdentityUnavailable, match="^identity_worker_cleanup_failed$"):
        await worker.close()
    assert worker.process is child
    child.wait = wait
    await worker.close()
    assert worker.process is None and child.waits == 1


async def test_transport_close_failure_still_reaps_and_preserves_original_failure(monkeypatch, tmp_path):
    worker = SimpleNamespace(open=AsyncMock(side_effect=ValueError("private-native-fixture")), close=AsyncMock())
    transport = SimpleNamespace(close=AsyncMock(side_effect=OSError("private-transport-fixture")))
    monkeypatch.setattr(runtime, "Worker", lambda: worker)
    monkeypatch.setattr(runtime, "BoundedHttpSession", lambda **kwargs: transport)
    provider = runtime.MacAnisetteProvider(libs_path=tmp_path)
    monkeypatch.setattr(provider, "_library", AsyncMock(return_value=tmp_path / "public-library"))
    with pytest.raises(runtime.IdentityUnavailable, match="^identity_provisioning_unavailable$"):
        await provider._get_ani()
    transport.close.assert_awaited_once()
    worker.close.assert_awaited_once()
    assert provider._worker is None
    await provider.close()


async def test_header_worker_close_failure_does_not_mask_original_failure(monkeypatch, tmp_path):
    identity = runtime.new_identity()
    identity["routing"] = 17106176
    machine = {"identity": identity, "store": {"fixture": base64.b64encode(b"fixture").decode()}}
    provider = runtime.MacAnisetteProvider(libs_path=tmp_path, state=machine)
    worker = SimpleNamespace(open=AsyncMock(side_effect=ValueError("private-native-fixture")),
                             close=AsyncMock(side_effect=OSError("private-cleanup-fixture")))
    monkeypatch.setattr(runtime, "Worker", lambda: worker)
    monkeypatch.setattr(provider, "_library", AsyncMock(return_value=tmp_path / "public-library"))
    with pytest.raises(runtime.IdentityUnavailable, match="^identity_headers_unavailable$"):
        await provider.get_headers(provider.local_user_uuid, provider.device_uuid)
    worker.close.assert_awaited_once()
    # Failed close retains ownership so the final provider close can retry it.
    assert provider._worker is worker
    worker.close.side_effect = None
    await provider.close()
    assert provider._worker is None and worker.close.await_count == 2
