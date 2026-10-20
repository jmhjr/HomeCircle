"""Owned startup cleanup never logs a shielded failure after caller cancellation."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.homecircle import device_tracker

PRIVATE = 'synthetic-private-cleanup-exception-canary'


class FailingCollection:
    """Inject a task-level failure after each owned client has been stopped."""

    def __init__(self, clients, failure):
        self.clients, self.failure = clients, failure

    def __iter__(self):
        yield from self.clients
        raise self.failure


@pytest.mark.parametrize('repeat', [False, True])
async def test_cancelled_shield_drains_all_cleanup_without_automatic_private_log(caplog, repeat):
    entered, release = asyncio.Event(), asyncio.Event()
    events = []
    failure = RuntimeError(PRIVATE)

    async def blocked():
        events.append('first entered')
        entered.set()
        await release.wait()
        events.append('first stopped')

    async def last():
        events.append('last stopped')

    clients = FailingCollection([
        ('first', SimpleNamespace(async_stop=blocked)),
        ('last', SimpleNamespace(async_stop=last)),
    ], failure)
    cleanup = asyncio.create_task(device_tracker._async_stop_after_startup(clients))
    try:
        await asyncio.wait_for(entered.wait(), 2)
        cleanup.cancel()
        await asyncio.sleep(0)
        if repeat:
            cleanup.cancel()
            await asyncio.sleep(0)
        assert not cleanup.done() and events == ['first entered']
        release.set()
        with pytest.raises(RuntimeError) as caught:
            await cleanup
        assert caught.value is failure  # Cleanup failure keeps its existing precedence.
        await asyncio.sleep(0)
        assert events == ['first entered', 'first stopped', 'last stopped']
        assert PRIVATE not in caplog.text
    finally:
        release.set()
        if not cleanup.done():
            cleanup.cancel()
        await asyncio.gather(cleanup, return_exceptions=True)


async def test_failure_without_cancellation_propagates_the_same_exception(caplog):
    failure = RuntimeError(PRIVATE)
    stop = AsyncMock()
    with pytest.raises(RuntimeError) as caught:
        await device_tracker._async_stop_after_startup(
            FailingCollection([('only', SimpleNamespace(async_stop=stop))], failure)
        )
    assert caught.value is failure
    stop.assert_awaited_once()
    assert PRIVATE not in caplog.text


async def test_owned_stop_failures_are_sanitized_and_siblings_finish_after_cancel(caplog):
    entered, release = asyncio.Event(), asyncio.Event()
    failure = RuntimeError(PRIVATE)
    sibling = AsyncMock()

    async def broken():
        entered.set()
        await release.wait()
        raise failure

    cleanup = asyncio.create_task(device_tracker._async_stop_after_startup([
        ('failed', SimpleNamespace(async_stop=broken)),
        ('sibling', SimpleNamespace(async_stop=sibling)),
    ]))
    try:
        await asyncio.wait_for(entered.wait(), 2)
        cleanup.cancel()
        await asyncio.sleep(0)
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await cleanup
        sibling.assert_awaited_once()
        assert PRIVATE not in caplog.text
        assert 'failed cleanup failed (RuntimeError)' in caplog.text
    finally:
        release.set()
        if not cleanup.done():
            cleanup.cancel()
        await asyncio.gather(cleanup, return_exceptions=True)
