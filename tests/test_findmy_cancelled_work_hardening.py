"""Cancelled local transactions drain late failures without asyncio error logging."""

import asyncio
import threading
from types import SimpleNamespace

import pytest

from custom_components.homecircle.findmy_flow import _finish_saved_transaction
from custom_components.homecircle.findmy_provider import DirectFindMy


PRIVATE_ERROR = "synthetic-private-background-failure"


@pytest.mark.parametrize("fails", [False, True])
async def test_confirmed_commit_drains_cancelled_failure_without_logging(
    hass, caplog, fails
):
    entered, release, finished = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def commit():
        entered.set()
        await release.wait()
        finished.set()
        if fails:
            raise RuntimeError(PRIVATE_ERROR)
        return {"committed": True}

    inner = asyncio.create_task(commit())
    outer = asyncio.create_task(_finish_saved_transaction(inner))
    try:
        await asyncio.wait_for(entered.wait(), 2)
        outer.cancel("first cancellation")
        await asyncio.sleep(0)
        outer.cancel("later cancellation")
        await asyncio.sleep(0)
        assert not outer.done() and not finished.is_set()
        release.set()
        with pytest.raises(asyncio.CancelledError, match="first cancellation"):
            await outer
        assert finished.is_set() and inner.done()
        await asyncio.sleep(0)
        assert PRIVATE_ERROR not in caplog.text
    finally:
        release.set()
        await asyncio.gather(outer, return_exceptions=True)


@pytest.mark.parametrize("fails", [False, True])
async def test_poll_vault_write_drains_cancelled_executor_failure_without_logging(
    hass, caplog, fails
):
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()

    def write(*_args):
        entered.set()
        assert release.wait(3), "Synthetic test write was not released"
        finished.set()
        if fails:
            raise RuntimeError(PRIVATE_ERROR)

    provider = DirectFindMy(hass, {}, lambda _: None, "synthetic-entry")
    provider.vaults = {"synthetic": SimpleNamespace(save_account=write)}
    client = SimpleNamespace(account=SimpleNamespace(to_json=lambda: {}), items={})
    task = asyncio.create_task(provider.save_poll_progress("synthetic", client))
    try:
        assert await asyncio.to_thread(entered.wait, 2)
        task.cancel("first cancellation")
        await asyncio.sleep(0)
        task.cancel("later cancellation")
        await asyncio.sleep(0)
        assert not task.done() and not finished.is_set()
        release.set()
        with pytest.raises(asyncio.CancelledError, match="first cancellation"):
            await task
        assert finished.is_set()
        await asyncio.sleep(0)
        assert PRIVATE_ERROR not in caplog.text
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)


async def test_commit_failure_without_cancellation_is_preserved(hass):
    error = RuntimeError(PRIVATE_ERROR)

    async def commit():
        raise error

    with pytest.raises(RuntimeError) as raised:
        await _finish_saved_transaction(asyncio.create_task(commit()))
    assert raised.value is error


async def test_poll_write_failure_without_cancellation_is_preserved(hass):
    error = RuntimeError(PRIVATE_ERROR)

    def write(*_args):
        raise error

    provider = DirectFindMy(hass, {}, lambda _: None, "synthetic-entry")
    provider.vaults = {"synthetic": SimpleNamespace(save_account=write)}
    client = SimpleNamespace(account=SimpleNamespace(to_json=lambda: {}), items={})
    with pytest.raises(RuntimeError) as raised:
        await provider.save_poll_progress("synthetic", client)
    assert raised.value is error
