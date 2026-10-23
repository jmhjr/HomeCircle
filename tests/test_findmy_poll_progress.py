"""Completed polls survive errors, cancellation and provider persistence boundaries."""

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, UTC
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from custom_components.homecircle.findmy_provider import DirectFindMy, FindMyTracker
from custom_components.homecircle._vendor_findmy.errors import UnauthorizedError
from tests.test_findmy_polling_diagnostics import make_client
from tests.test_findmy_reports import report


def provider_for(hass, client, save):
    provider = DirectFindMy(hass, {"example": {}}, lambda _: None, "example-entry")
    provider.clients = {"example": client}
    client.account.to_json = lambda: {"account": {"password": None}}
    provider.vaults = {"example": SimpleNamespace(save_account=save)}
    provider.trackers = {"example": {
        key: FindMyTracker("homecircle_findmy_example", "Example item")
        for key in client.items
    }}
    return provider


async def test_auth_expiry_persists_completed_report_and_requires_reauth(hass):
    client = make_client(count=201)
    saves = []
    provider = provider_for(hass, client, lambda _session, items: saves.append(deepcopy(items)))
    calls = 0

    async def fetch(keys):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise UnauthorizedError("private-error-canary")
        return {keys[0]: report(datetime.now(UTC) - timedelta(minutes=1))}

    client.account.fetch_location.side_effect = fetch
    with patch.object(hass.config_entries, "async_reload", new=AsyncMock(return_value=True)):
        await provider.poll("example")
        await hass.async_block_till_done()
    assert provider.states["example"] == "paused"
    assert len(saves) == 1
    identifier = next(iter(client.items))
    retained = saves[0][identifier]["report"]
    assert retained == client.clients[identifier].report
    tracker = provider.trackers["example"][identifier]
    assert tracker.available and tracker.report == retained
    assert tracker.status == "account_unavailable"
    assert calls == 2


async def test_cancelled_poll_drains_repeated_cancellation_before_reconnect(hass):
    client = make_client(count=201)
    second_fetch = asyncio.Event()
    write_started, release_write = threading.Event(), threading.Event()
    saves = []

    def save(_session, items):
        write_started.set()
        assert release_write.wait(5), "test failed to release write"
        saves.append(deepcopy(items))

    provider = provider_for(hass, client, save)
    calls = 0

    async def fetch(keys):
        nonlocal calls
        calls += 1
        if calls == 2:
            second_fetch.set()
            await asyncio.Future()
        return {keys[0]: report(datetime.now(UTC) - timedelta(minutes=1))}

    client.account.fetch_location.side_effect = fetch
    task = asyncio.create_task(provider.poll("example"))
    provider.tasks["example"] = task
    try:
        await asyncio.wait_for(second_fetch.wait(), 5)
        pausing = asyncio.create_task(provider.pause_account("example"))
        assert await asyncio.to_thread(write_started.wait, 5)
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done() and not pausing.done()
    finally:
        release_write.set()
    paused = await asyncio.wait_for(pausing, 5)
    assert paused is client and task.cancelled()
    assert len(saves) == 1
    identifier = next(iter(client.items))
    assert saves[0][identifier]["report"] == client.clients[identifier].report
    assert saves[0][identifier]["report"] is not None


async def test_partial_item_failure_preserves_health_for_other_item(hass):
    client = make_client()
    old_identifier = next(iter(client.items))
    from custom_components.homecircle.findmy_reports import Client
    good_accessory = SimpleNamespace(
        get_min_index=lambda _: 0, get_max_index=lambda _: 0,
        keys_at=lambda _: ["example-healthy-key"],
    )
    client.clients["healthy"] = Client(client.account, good_accessory)
    client.items["healthy"] = {"accessory": {}, "report": None}
    save = Mock()
    provider = provider_for(hass, client, save)

    async def fetch(keys):
        if keys == ["example-healthy-key"]:
            return {keys[0]: report(datetime.now(UTC) - timedelta(minutes=1))}
        raise TimeoutError("private-error-canary")

    client.account.fetch_location.side_effect = fetch
    await provider.poll("example")
    assert provider.states["example"] == provider.health_snapshot().state == "partial"
    assert provider.trackers["example"]["healthy"].available
    assert provider.trackers["example"]["healthy"].status == "last_report"
    assert provider.trackers["example"][old_identifier].status == "account_unavailable"
    save.assert_called_once()


async def test_vault_failure_is_not_reported_as_success_and_is_not_retried(hass):
    client = make_client()
    client.account.fetch_location.return_value = {
        "private-key-canary-0": report(datetime.now(UTC) - timedelta(minutes=1))
    }
    save = Mock(side_effect=OSError("private-error-canary"))
    provider = provider_for(hass, client, save)
    await provider.poll("example")
    assert provider.states["example"] == "network_error"
    assert provider.last_success is None
    save.assert_called_once()
