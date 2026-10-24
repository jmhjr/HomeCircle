"""Returned reports and retained reports are different passive observations."""

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, UTC
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.homecircle.diagnostics import async_get_config_entry_diagnostics
from custom_components.homecircle.findmy_provider import DirectFindMy, validated_polling_snapshot
from custom_components.homecircle.findmy_reports import (
    AccountClient, Client, ReauthenticationRequired, report_mapping,
    validated_poll_diagnostics,
)
from custom_components.homecircle._vendor_findmy.errors import UnauthorizedError
from tests.test_findmy_reports import report


def make_client(previous=None, count=1):
    account = SimpleNamespace(fetch_location=AsyncMock(return_value={}), close=AsyncMock())
    accessory = SimpleNamespace(
        get_min_index=lambda _: 0, get_max_index=lambda _: count - 1,
        keys_at=lambda index: [f"private-key-canary-{index}"],
    )
    value = AccountClient.__new__(AccountClient)
    value.account, value.lock = account, asyncio.Lock()
    value.clients = {"private-item-canary": Client(account, accessory, previous)}
    value.items = {"private-item-canary": {"accessory": {}, "report": previous}}
    return value


def observation(**changes):
    return {
        "schema": 1, "status": "success", "fetch_calls": 1, "decoded_reports": 0,
        "selected_items": 1, "items_with_returned_valid_reports": 0,
        "items_with_advanced_reports": 0, "items_retaining_previous_report": 1,
        "items_without_report": 0, **changes,
    }


async def test_returned_equal_older_and_advanced_reports_are_distinct_from_empty_cache():
    previous_time = datetime.now(UTC) - timedelta(minutes=10)
    previous = report_mapping(report(previous_time))
    value = make_client(previous)
    assert value.poll_diagnostics()["status"] == "not_polled"
    cases = [
        ({}, (0, 0, 0, 1)),
        ({"private-key-canary-0": report(previous_time)}, (1, 1, 0, 0)),
        ({"private-key-canary-0": report(previous_time - timedelta(minutes=1))}, (1, 1, 0, 1)),
        ({"private-key-canary-0": report(previous_time + timedelta(minutes=1))}, (1, 1, 1, 0)),
    ]
    for returned, (decoded, valid, advanced, retained) in cases:
        value.account.fetch_location.return_value = returned
        result = await value.poll()
        assert value.poll_diagnostics() == observation(
            decoded_reports=decoded, items_with_returned_valid_reports=valid,
            items_with_advanced_reports=advanced, items_retaining_previous_report=retained,
        )
        assert result["private-item-canary"]["last_seen"] == (
            previous_time + timedelta(minutes=1) if advanced else previous_time
        ).isoformat()
        detached = value.poll_diagnostics()
        detached["status"] = "failed"
        assert value.poll_diagnostics()["status"] == "success"
        assert "canary" not in repr(value.poll_diagnostics())
    assert value.account.fetch_location.await_count == 4


async def test_missing_and_invalid_returned_reports_do_not_count_as_valid_or_advanced():
    value = make_client()
    await value.poll()
    assert value.poll_diagnostics() == observation(
        items_retaining_previous_report=0, items_without_report=1,
    )
    value.account.fetch_location.return_value = {
        "private-key-canary-0": report(datetime.now(UTC) + timedelta(days=1)),
    }
    assert (await value.poll())["private-item-canary"] is None
    assert value.poll_diagnostics() == observation(
        decoded_reports=1, items_retaining_previous_report=0, items_without_report=1,
    )


async def test_fetch_calls_observe_existing_batching_without_extra_calls_or_key_changes():
    value = make_client(count=201)
    requests = []

    async def fetch(keys):
        requests.append(list(keys))
        return {keys[0]: report(datetime.now(UTC) - timedelta(minutes=1))}

    value.account.fetch_location.side_effect = fetch
    await value.poll()
    assert [len(keys) for keys in requests] == [200, 1]
    assert set().union(*map(set, requests)) == {f"private-key-canary-{index}" for index in range(201)}
    assert value.poll_diagnostics() == observation(
        fetch_calls=2, decoded_reports=2, items_with_returned_valid_reports=1,
        items_with_advanced_reports=1, items_retaining_previous_report=0,
    )


@pytest.mark.parametrize("failure,expected", [
    (RuntimeError("private-error-canary"), "failed"),
    (TimeoutError("private-error-canary"), "failed"),
    (UnauthorizedError("private-error-canary"), "failed"),
    (asyncio.CancelledError(), "cancelled"),
])
async def test_failure_or_cancellation_does_not_reuse_previous_success(failure, expected, caplog):
    previous = report_mapping(report(datetime.now(UTC) - timedelta(minutes=1)))
    value = make_client(previous)
    await value.poll()
    value.account.fetch_location.side_effect = failure
    raised = ReauthenticationRequired if isinstance(failure, UnauthorizedError) else type(failure)
    with pytest.raises(raised):
        await value.poll()
    assert value.poll_diagnostics() == observation(
        status=expected, items_retaining_previous_report=0,
    )
    assert value.clients["private-item-canary"].report == previous
    assert "canary" not in repr(value.poll_diagnostics()) + caplog.text


async def test_partial_fetch_failure_retains_committed_item_success():
    value = make_client(count=201)
    calls = 0

    async def fetch(keys):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("private-error-canary")
        return {keys[0]: report(datetime.now(UTC) - timedelta(minutes=1))}

    value.account.fetch_location.side_effect = fetch
    result = await value.poll()
    assert value.poll_diagnostics() == observation(
        status="partial", fetch_calls=2, decoded_reports=1,
        items_retaining_previous_report=0, items_with_returned_valid_reports=1,
        items_with_advanced_reports=1,
    )
    assert result["private-item-canary"] == value.clients["private-item-canary"].report
    assert value.clients["private-item-canary"].report is not None
    assert value.failed_items == {"private-item-canary"}


async def test_existing_lock_serializes_observations_and_active_cancel_is_terminal():
    value = make_client()
    entered, release = asyncio.Event(), asyncio.Event()

    async def fetch(_keys):
        entered.set()
        await release.wait()
        return {}

    value.account.fetch_location.side_effect = fetch
    first = asyncio.create_task(value.poll())
    await entered.wait()
    assert value.poll_diagnostics() == observation(
        status="in_progress", items_retaining_previous_report=0,
    )
    waiting = asyncio.create_task(value.poll())
    await asyncio.sleep(0)
    assert value.account.fetch_location.await_count == 1
    waiting.cancel()
    await asyncio.gather(waiting, return_exceptions=True)
    assert value.poll_diagnostics()["status"] == "in_progress"
    first.cancel()
    await asyncio.gather(first, return_exceptions=True)
    assert value.poll_diagnostics()["status"] == "cancelled"
    release.set()
    await value.poll()
    assert value.poll_diagnostics()["status"] == "success"
    assert value.account.fetch_location.await_count == 2


@pytest.mark.parametrize("change", [
    {"raw": "private-value-canary"}, {"status": "private-value-canary"},
    {"decoded_reports": True}, {"fetch_calls": -1}, {"selected_items": 1000001},
    {"items_with_advanced_reports": 1}, {"status": "cancelled"},
])
def test_account_observation_requires_exact_strict_scalars(change):
    assert validated_poll_diagnostics(observation(**change)) is None


def make_provider(hass, clients):
    value = DirectFindMy(hass, {key: {} for key in clients}, lambda _: None, "private-entry-canary")
    value.clients = {key: client for key, client in clients.items() if client is not None}
    return value


async def test_provider_aggregate_has_no_account_item_location_time_or_error_values(hass):
    good = make_client(report_mapping(report(datetime.now(UTC) - timedelta(minutes=1))))
    await good.poll()
    cold = make_client()
    failed = make_client()
    failed.account.fetch_location.side_effect = RuntimeError("private-error-canary")
    with pytest.raises(RuntimeError):
        await failed.poll()
    provider = make_provider(hass, {
        "private-account-canary-1": good, "private-account-canary-2": cold,
        "private-account-canary-3": failed, "private-account-canary-4": None,
        "private-account-canary-5": SimpleNamespace(poll_diagnostics=lambda: {"raw": "private-value-canary"}),
    })
    result = provider.polling_snapshot()
    assert result == {
        "schema": 1, "accounts": 5, "accounts_without_observation": 2,
        "status_counts": {"not_polled": 1, "in_progress": 0, "success": 1, "partial": 0, "failed": 1, "cancelled": 0},
        "fetch_calls": 2, "decoded_reports": 0, "selected_items": 3,
        "items_with_returned_valid_reports": 0, "items_with_advanced_reports": 0,
        "items_retaining_previous_report": 1, "items_without_report": 0,
    }
    assert "canary" not in repr(result)
    result["status_counts"]["success"] = 99
    assert provider.polling_snapshot()["status_counts"]["success"] == 1
    assert set(provider.health_snapshot().as_dict()) == {
        "state", "discovered_trackers", "available_trackers", "last_api_success", "last_error", "retry_at",
    }


async def test_optional_diagnostics_exports_only_valid_aggregate_without_triggering_poll(hass):
    value = make_client()
    provider = make_provider(hass, {"private-account-canary": value})
    entry = SimpleNamespace(
        options={"findmy_accounts": provider.accounts}, data={},
        runtime_data=SimpleNamespace(managed_trackers={"findmy": provider}),
    )
    result = await async_get_config_entry_diagnostics(hass, entry)
    assert result["findmy_polling"]["status_counts"]["not_polled"] == 1
    assert "canary" not in repr(result)
    value.account.fetch_location.assert_not_awaited()
    original = provider.polling_snapshot()
    bad = deepcopy(original)
    bad["status_counts"]["private-status-canary"] = 1
    provider.polling_snapshot = lambda: bad
    assert "findmy_polling" not in await async_get_config_entry_diagnostics(hass, entry)
    assert validated_polling_snapshot(bad) is None


@pytest.mark.parametrize("change", [
    {"accounts": True}, {"accounts_without_observation": 1000001},
    {"raw": "private-value-canary"}, {"decoded_reports": "private-value-canary"},
    {"status_counts": {"success": 1}},
])
async def test_invalid_aggregate_cannot_export_raw_or_ambiguous_counts(hass, change):
    value = make_provider(hass, {}).polling_snapshot()
    assert validated_polling_snapshot({**value, **change}) is None


async def test_paused_diagnostics_expose_only_fixed_controls_and_aggregate_counts(hass):
    from custom_components.homecircle.provider_controls import ProviderControls

    controls = ProviderControls(hass, "example-entry")
    await controls.async_load()
    with patch.object(hass.config_entries, "async_reload", new=AsyncMock(return_value=True)):
        await controls.async_pause_denied("findmy", "private-account-canary")
        await hass.async_block_till_done()
    entry = SimpleNamespace(
        data={"findmy_accounts": {"private-account-canary": {"items": {}}}},
        options={},
        runtime_data=SimpleNamespace(managed_trackers={}, provider_controls=controls),
    )
    result = await async_get_config_entry_diagnostics(hass, entry)
    assert result["connection_controls"] == {
        "findmy": {"paused": False, "paused_accounts": 1, "storage_available": True},
    }
    assert "private" not in repr(result)
    assert "canary" not in repr(result)
