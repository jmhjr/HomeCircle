"""Cancelled sign-in owns its password worker until bounded native work finishes."""

import asyncio
import threading
from unittest.mock import AsyncMock

import pytest

from custom_components.homecircle._vendor_findmy.reports import account
from custom_components.homecircle._vendor_findmy.reports.anisette import BaseAnisetteProvider
from custom_components.homecircle._vendor_findmy.reports.endpoint_policy import WINDOWS_ONBOARDING_V1


class StaticProvider(BaseAnisetteProvider):
    """No engine, Apple traffic, account state or private inputs."""

    otp = "c3ludGhldGlj"
    machine = "c3ludGhldGlj"

    async def close(self):
        pass

    def to_json(self):
        return {"type": "synthetic"}

    @classmethod
    def from_json(cls, value):
        return cls()


@pytest.mark.parametrize("worker_fails", [False, True])
async def test_actual_gsa_drains_repeated_cancel_before_releasing_password(
    monkeypatch, caplog, worker_fails,
):
    current = account.AsyncAppleAccount(StaticProvider(), endpoint_policy=WINDOWS_ONBOARDING_V1)
    current._gsa_request = AsyncMock(return_value={
        "Status": {"ec": 0}, "sp": "s2k", "s": b"synthetic-salt",
        "B": b"\x02", "i": 10000, "c": "synthetic-challenge",
    })
    loop = asyncio.get_running_loop()
    entered, finished = asyncio.Event(), asyncio.Event()
    release = threading.Event()
    original = account.util.crypto.encrypt_password
    failure = ValueError("synthetic-private-derivation-canary")
    unhandled = []
    previous_handler = loop.get_exception_handler()
    loop.set_exception_handler(lambda _loop, context: unhandled.append(context))

    def derive(*args):
        loop.call_soon_threadsafe(entered.set)
        try:
            assert release.wait(3)
            if worker_fails:
                raise failure
            return original(*args)
        finally:
            loop.call_soon_threadsafe(finished.set)

    monkeypatch.setattr(account.util.crypto, "encrypt_password", derive)
    task = asyncio.create_task(current._gsa_authenticate(
        "synthetic@example.invalid", "synthetic-password",
    ))
    try:
        await asyncio.wait_for(entered.wait(), 2)
        task.cancel("first synthetic cancellation")
        await asyncio.sleep(0)
        assert not task.done() and not finished.is_set()
        task.cancel("later synthetic cancellation")
        await asyncio.sleep(0)
        assert not task.done() and not finished.is_set()
        release.set()
        with pytest.raises(asyncio.CancelledError, match="first synthetic cancellation"):
            await task
        await asyncio.wait_for(finished.wait(), 2)
        assert current._gsa_request.await_count == 1
        assert not unhandled
        assert "synthetic-private-derivation-canary" not in caplog.text
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)
        await current.close()
        loop.set_exception_handler(previous_handler)


async def test_password_worker_success_and_failure_propagate_without_cancellation(monkeypatch):
    original = account.util.crypto.encrypt_password
    expected = original("synthetic-password", b"synthetic-salt", 10000, "s2k")
    assert await account._encrypt_password_off_loop(
        "synthetic-password", b"synthetic-salt", 10000, "s2k",
    ) == expected
    failure = ValueError("synthetic-derivation-failure")

    def fail(*args):
        raise failure

    monkeypatch.setattr(account.util.crypto, "encrypt_password", fail)
    with pytest.raises(ValueError) as caught:
        await account._encrypt_password_off_loop(
            "synthetic-password", b"synthetic-salt", 10000, "s2k",
        )
    assert caught.value is failure
