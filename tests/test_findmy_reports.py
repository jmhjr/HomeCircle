"""Actual report time and conservative battery states, without Apple requests."""

from datetime import datetime, timedelta, UTC
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from custom_components.homecircle.findmy_reports import (
    AccountClient,
    Client,
    report_mapping,
)


SYNTHETIC_COORDINATE = 0.0
MAX_LONGITUDE = 180


def report(time, status=0):
    return SimpleNamespace(
        timestamp=time,
        latitude=SYNTHETIC_COORDINATE,
        longitude=SYNTHETIC_COORDINATE,
        horizontal_accuracy=12.0,
        status=status,
    )


@pytest.mark.parametrize(
    "status,expected",
    [
        (0, "full"),
        (64, "medium"),
        (128, "low"),
        (192, "very_low"),
        (None, None),
        (True, None),
        (256, None),
    ],
)
def test_coarse_battery_never_implies_a_percentage(status, expected):
    result = report_mapping(report(datetime.now(UTC), status))
    assert result["battery_status"] == expected
    assert "battery_level" not in result


@pytest.mark.parametrize(
    "changes",
    [
        {"latitude": float("nan")},
        {"longitude": MAX_LONGITUDE + 1},
        {"horizontal_accuracy": -1},
        {"timestamp": datetime.now(UTC) + timedelta(days=1)},
        {"timestamp": datetime.now()},
    ],
)
def test_invalid_location_reports_are_rejected(changes):
    value = report(datetime.now(UTC))
    for field, item in changes.items():
        setattr(value, field, item)
    with pytest.raises(ValueError):
        report_mapping(value)


async def test_empty_and_older_reports_keep_actual_time_and_newer_report_advances():
    previous = report_mapping(report(datetime.now(UTC) - timedelta(minutes=10)))
    account = SimpleNamespace(
        fetch_location=AsyncMock(return_value={}), close=AsyncMock()
    )
    accessory = SimpleNamespace(
        get_min_index=lambda _: 0,
        get_max_index=lambda _: 1,
        keys_at=lambda i: [f"example-key-{i}"],
    )
    value = AccountClient.__new__(AccountClient)
    import asyncio

    value.account, value.lock = account, asyncio.Lock()
    value.clients = {"example-item": Client(account, accessory, previous)}
    value.items = {"example-item": {"accessory": {}, "report": previous}}
    assert (await value.poll())["example-item"] == previous
    account.fetch_location.return_value = {
        "example-key-0": report(datetime.now(UTC) - timedelta(hours=1))
    }
    assert (await value.poll())["example-item"] == previous
    newer = report(datetime.now(UTC) - timedelta(minutes=2))
    account.fetch_location.return_value = {"example-key-1": newer}
    assert (await value.poll())["example-item"][
        "last_seen"
    ] == newer.timestamp.isoformat()


def test_old_sdk_exports_restore_without_changing_keys_or_namespace():
    import findmy as original
    from custom_components.homecircle._vendor_findmy import FindMyAccessory

    accessory = original.FindMyAccessory(
        master_key=bytes([1]) * 28,
        skn=bytes([2]) * 32,
        sks=bytes([3]) * 32,
        paired_at=datetime(2026, 1, 1, tzinfo=UTC),
        name="Example item",
        identifier="synthetic-id",
    )
    before = accessory.to_json()
    restored = FindMyAccessory.from_json(before)
    assert restored.to_json()["master_key"] == before["master_key"]
    assert restored.to_json()["identifier"] == "synthetic-id"
    assert original.FindMyAccessory is not FindMyAccessory
    assert original.FindMyAccessory.__module__.startswith("findmy.")
    assert FindMyAccessory.__module__.startswith(
        "custom_components.homecircle._vendor_findmy."
    )


async def test_invalid_item_report_does_not_hide_another_valid_item():
    import asyncio

    account = SimpleNamespace(
        fetch_location=AsyncMock(
            return_value={
                "example-key-first": report(datetime.now(UTC) + timedelta(days=1)),
                "example-key-second": report(datetime.now(UTC) - timedelta(minutes=1)),
            }
        )
    )
    value = AccountClient.__new__(AccountClient)
    value.account, value.lock = account, asyncio.Lock()
    value.items = {
        key: {"accessory": {}, "report": None} for key in ("first", "second")
    }
    value.clients = {
        key: Client(
            account,
            SimpleNamespace(
                get_min_index=lambda _: 0,
                get_max_index=lambda _: 0,
                keys_at=lambda _, key=key: [f"example-key-{key}"],
            ),
        )
        for key in value.items
    }
    reports = await value.poll()
    assert reports["first"] is None
    assert reports["second"]["last_seen"]
