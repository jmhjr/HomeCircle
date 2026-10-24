"""Real rotating accessories retain completed work across synthetic failures.

Only the account transport is replaced. Key derivation, secondary-key overlap,
stale-window paging, report acceptance and accessory serialization are real.
"""

from datetime import datetime, timedelta, UTC
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.homecircle._vendor_findmy import FindMyAccessory
from custom_components.homecircle._vendor_findmy.errors import UnauthorizedError
from custom_components.homecircle import findmy_reports
from custom_components.homecircle.findmy_reports import (
    AccountClient,
    ReauthenticationRequired,
    report_mapping,
    report_window,
)


SYNTHETIC_COORDINATE = 0.0


@pytest.fixture
def now(monkeypatch):
    value = datetime(2026, 10, 19, 18, tzinfo=UTC)

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return value if tz is not None else value.replace(tzinfo=None)

    monkeypatch.setattr(findmy_reports, "datetime", FrozenDatetime)
    return value


def synthetic_accessory(now, *, age_days, seed):
    """Deterministic public-test key material; never imported household data."""
    return FindMyAccessory(
        master_key=bytes([seed]) * 28,
        skn=bytes([seed + 1]) * 32,
        sks=bytes([seed + 2]) * 32,
        paired_at=now - timedelta(days=age_days),
        name=f"Synthetic accessory {seed}",
        identifier=f"synthetic-accessory-{seed}",
    )


def synthetic_report(timestamp):
    return SimpleNamespace(
        timestamp=timestamp,
        latitude=SYNTHETIC_COORDINATE,
        longitude=SYNTHETIC_COORDINATE,
        horizontal_accuracy=12.0,
        status=0,
    )


def account_client(accessories, previous=None):
    previous = previous or {}
    account = SimpleNamespace(fetch_location=AsyncMock(), close=AsyncMock())
    items = {
        identifier: {
            "accessory": accessory.to_json(),
            "report": previous.get(identifier),
        }
        for identifier, accessory in accessories.items()
    }
    return AccountClient(account, items)


@pytest.mark.parametrize("age_days", [100, 180])
async def test_later_batch_timeout_preserves_cursor_without_skipping_failed_keys(
    now, age_days
):
    accessory = synthetic_accessory(now, age_days=age_days, seed=1)
    first, last = report_window(accessory, now)
    assert first == 0
    assert last - first > 8192
    cached = report_mapping(synthetic_report(now - timedelta(minutes=1)))
    value = account_client({"stale": accessory}, {"stale": cached})
    requests = []

    async def interrupted_fetch(keys):
        requests.append(set(keys))
        if len(requests) == 3:
            raise TimeoutError("synthetic later-batch timeout")
        # Historical results must not replace a newer retained report or realign
        # the accessory to an older location merely because a batch completed.
        return {keys[0]: synthetic_report(now - timedelta(days=30))}

    value.account.fetch_location.side_effect = interrupted_fetch
    assert (await value.poll())["stale"] == cached
    assert value.failed_items == {"stale"}
    assert value.poll_diagnostics()["status"] == "partial"
    cursor = value.items["stale"].get("search_before", last + 1)
    assert first < cursor < last + 1
    completed = requests[0] | requests[1]
    # Every skipped index must have all its primary AND possible secondary
    # lookup keys in completed responses, not just its primary lookup key.
    for index in range(cursor, last + 1):
        assert accessory.keys_at(index) <= completed
    assert not accessory.keys_at(cursor - 1) <= completed
    failed_batch = requests[-1]
    interrupted_state = value.items["stale"].copy()

    resumed = []

    async def resumed_fetch(keys):
        resumed.append(set(keys))
        return {}

    # Reconstruct from persisted item state, so progress cannot exist solely in
    # an in-memory client or key cache.
    restored = AccountClient(value.account, {"stale": interrupted_state})
    value.account.fetch_location.side_effect = resumed_fetch
    assert (await restored.poll())["stale"] == cached
    assert failed_batch <= set().union(*resumed)
    assert restored.items["stale"]["search_before"] < cursor
    assert restored.poll_diagnostics()["status"] == "success"
    assert restored.items["stale"]["accessory"]["alignment_date"] == (
        accessory.to_json()["alignment_date"]
    )
    assert all(len(batch) <= 200 for batch in requests + resumed)


async def test_quiet_real_accessory_does_not_prevent_healthy_item_polling(now):
    quiet = synthetic_accessory(now, age_days=180, seed=10)
    healthy = synthetic_accessory(now, age_days=1, seed=20)
    healthy_key = next(iter(healthy.keys_at(healthy.get_max_index(now))))
    fresh_report = synthetic_report(now - timedelta(minutes=2))
    value = account_client({"quiet": quiet, "healthy": healthy})
    requests = []

    async def fetch(keys):
        requests.append(set(keys))
        return {healthy_key: fresh_report} if healthy_key in keys else {}

    value.account.fetch_location.side_effect = fetch
    result = await value.poll()
    assert result["quiet"] is None
    assert result["healthy"]["last_seen"] == fresh_report.timestamp.isoformat()
    assert value.items["quiet"]["search_before"] > 0
    assert value.failed_items == set()
    assert value.poll_diagnostics()["status"] == "success"
    assert any(healthy_key in batch for batch in requests)
    assert all(len(batch) <= 200 for batch in requests)


async def test_quiet_item_transport_failure_keeps_cache_and_other_item_succeeds(now):
    quiet = synthetic_accessory(now, age_days=180, seed=30)
    healthy = synthetic_accessory(now, age_days=1, seed=40)
    healthy_key = next(iter(healthy.keys_at(healthy.get_max_index(now))))
    old_report = report_mapping(synthetic_report(now - timedelta(days=45)))
    fresh_report = synthetic_report(now - timedelta(minutes=1))
    value = account_client({"quiet": quiet, "healthy": healthy}, {"quiet": old_report})
    calls = 0

    async def fetch(keys):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise TimeoutError("synthetic quiet-item transport failure")
        return {healthy_key: fresh_report} if healthy_key in keys else {}

    value.account.fetch_location.side_effect = fetch
    result = await value.poll()
    assert result["quiet"] == old_report
    assert result["healthy"]["last_seen"] == fresh_report.timestamp.isoformat()
    assert value.failed_items == {"quiet"}
    assert value.poll_diagnostics()["status"] == "partial"
    assert value.items["quiet"]["search_before"] < report_window(quiet, now)[1] + 1


async def test_auth_expiry_aborts_account_but_keeps_completed_reports_and_cursor(now):
    healthy = synthetic_accessory(now, age_days=1, seed=50)
    stale = synthetic_accessory(now, age_days=100, seed=60)
    untouched = synthetic_accessory(now, age_days=1, seed=70)
    healthy_key = next(iter(healthy.keys_at(healthy.get_max_index(now))))
    untouched_key = next(iter(untouched.keys_at(untouched.get_max_index(now))))
    healthy_keys = set().union(*(
        healthy.keys_at(index)
        for index in range(report_window(healthy, now)[1] + 1)
    ))
    fresh_report = synthetic_report(now - timedelta(minutes=1))
    cached = report_mapping(synthetic_report(now - timedelta(minutes=2)))
    value = account_client(
        {"healthy": healthy, "stale": stale, "untouched": untouched},
        {"stale": cached},
    )
    stale_requests = []
    requests = []

    async def fetch(keys):
        requests.append(set(keys))
        if set(keys) <= healthy_keys:
            return {healthy_key: fresh_report} if healthy_key in keys else {}
        # The successful first item's location must survive an account
        # expiration while paging the next item.
        stale_requests.append(set(keys))
        if len(stale_requests) == 3:
            raise UnauthorizedError("synthetic expired account")
        return {keys[0]: synthetic_report(now - timedelta(days=40))}

    value.account.fetch_location.side_effect = fetch
    with pytest.raises(ReauthenticationRequired):
        await value.poll()
    assert value.clients["healthy"].report["last_seen"] == fresh_report.timestamp.isoformat()
    assert value.items["healthy"]["report"] == value.clients["healthy"].report
    assert value.clients["stale"].report == cached
    assert value.items["stale"]["report"] == cached
    cursor = value.items["stale"]["search_before"]
    assert 0 < cursor < report_window(stale, now)[1] + 1
    assert not any(untouched_key in batch for batch in requests)
    assert value.clients["untouched"].report is None
    assert value.poll_diagnostics()["status"] == "failed"


async def test_auth_expiry_commits_new_report_from_current_items_completed_batch(now):
    stale = synthetic_accessory(now, age_days=180, seed=80)
    value = account_client({"stale": stale})
    returned = synthetic_report(now - timedelta(minutes=5))
    requests = []

    async def fetch(keys):
        requests.append(set(keys))
        if len(requests) == 3:
            raise UnauthorizedError("synthetic expired account after useful work")
        return {keys[0]: returned} if len(requests) == 1 else {}

    value.account.fetch_location.side_effect = fetch
    with pytest.raises(ReauthenticationRequired):
        await value.poll()
    expected = report_mapping(returned)
    assert value.clients["stale"].report == expected
    assert value.items["stale"]["report"] == expected
    cursor = value.items["stale"]["search_before"]
    assert 0 < cursor < report_window(stale, now)[1] + 1
    completed = requests[0] | requests[1]
    for index in range(cursor, report_window(stale, now)[1] + 1):
        assert stale.keys_at(index) <= completed
