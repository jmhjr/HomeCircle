"""Bounded Find My report polling with explicit session expiration."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import math

from ._vendor_findmy import AsyncAppleAccount, FindMyAccessory
from .findmy_profile import configure_account
from .findmy_report_service import configure_report_account
from ._vendor_findmy.errors import (
    InvalidCredentialsError,
    InvalidStateError,
    UnauthorizedError,
)

POLL_LIMIT = 1000000
POLL_STATUSES = ("not_polled", "in_progress", "success", "failed", "cancelled")
POLL_COUNTERS = (
    "fetch_calls", "decoded_reports", "selected_items",
    "items_with_returned_valid_reports", "items_with_advanced_reports",
    "items_retaining_previous_report", "items_without_report",
)
_ITEM_OUTCOMES = POLL_COUNTERS[3:]


def _new_poll_diagnostics(selected_items):
    return {
        "schema": 1, "status": "not_polled", **dict.fromkeys(POLL_COUNTERS, 0),
        "selected_items": min(selected_items, POLL_LIMIT),
    }


def validated_poll_diagnostics(value):
    """Copy only a complete fixed scalar observation; never return item values."""
    if (type(value) is not dict
            or set(value) != {"schema", "status", *POLL_COUNTERS}
            or type(value["schema"]) is not int or value["schema"] != 1
            or type(value["status"]) is not str or value["status"] not in POLL_STATUSES
            or any(type(value[key]) is not int or not 0 <= value[key] <= POLL_LIMIT
                   for key in POLL_COUNTERS)
            or any(value[key] > value["selected_items"] for key in _ITEM_OUTCOMES)
            or value["items_with_advanced_reports"] > value["items_with_returned_valid_reports"]
            or value["items_retaining_previous_report"] + value["items_without_report"] > value["selected_items"]
            or (value["status"] != "success" and any(value[key] for key in _ITEM_OUTCOMES))):
        return None
    return {"schema": 1, "status": value["status"], **{key: value[key] for key in POLL_COUNTERS}}


@asynccontextmanager
async def _observe_poll(client):
    """Observe the existing locked operation without changing its request lifecycle."""
    current = _new_poll_diagnostics(len(client.clients))
    current["status"] = "in_progress"
    client._poll_diagnostics = current
    try:
        yield current
    except asyncio.CancelledError:
        current["status"] = "cancelled"
        for key in _ITEM_OUTCOMES:
            current[key] = 0
        raise
    except Exception:
        current["status"] = "failed"
        for key in _ITEM_OUTCOMES:
            current[key] = 0
        raise
    else:
        current["status"] = "success"


class ReauthenticationRequired(RuntimeError):
    pass


def report_mapping(report) -> dict:
    timestamp = report.timestamp
    latitude, longitude = float(report.latitude), float(report.longitude)
    accuracy = float(report.horizontal_accuracy)
    now = datetime.now(timezone.utc)
    if (
        timestamp.tzinfo is None
        or timestamp > now + timedelta(seconds=60)
        or not all(math.isfinite(v) for v in (latitude, longitude, accuracy))
        or not -90 <= latitude <= 90
        or not -180 <= longitude <= 180
        or accuracy < 0
    ):
        raise ValueError("Invalid location report")
    # FindMy.py's AirTag example decodes bits 6-7 of the decrypted report status.
    status = getattr(report, "status", None)
    battery = None
    if type(status) is int and 0 <= status <= 255:
        battery = ("full", "medium", "low", "very_low")[(status >> 6) & 3]
    return {
        "battery_status": battery,
        "latitude": latitude,
        "longitude": longitude,
        "gps_accuracy": accuracy,
        "last_seen": timestamp.isoformat(),
    }


def report_window(accessory, now):
    """Cover both possible primary-key buckets after an ambiguous secondary-key alignment."""
    first = accessory.get_min_index(now - timedelta(days=7))
    last = accessory.get_max_index(now)
    # A secondary key can match two 96-index primary buckets. Aligning its report to the
    # lowest matching index can underestimate the current primary index.
    # Fixed-key exports have no rotating-index ambiguity.
    if isinstance(accessory, FindMyAccessory):
        last += 192
    return first, last


class Client:
    def __init__(self, account, accessory, previous=None):
        self.account = account
        self.accessory = accessory
        self.report = previous
        self.lock = asyncio.Lock()

    @classmethod
    def restore(cls, data, libraries):
        if data.get("version") == 2:
            return AccountClient.restore(data, libraries)
        return cls(
            configure_report_account(configure_account(
                AsyncAppleAccount.from_json(data["session"], anisette_libs_path=libraries)
            )),
            FindMyAccessory.from_json(data["accessory"]),
            data.get("report"),
        )

    async def poll(self):
        async with self.lock:
            now = datetime.now(timezone.utc)
            first, last = report_window(self.accessory, now)
            if last < first or last - first > 8192:
                raise ValueError(
                    "Accessory key window is outside bounded polling limits"
                )
            keys = set()
            for index in range(first, last + 1):
                keys.update(self.accessory.keys_at(index))
            try:
                async with asyncio.timeout(120):
                    found = await self.account.fetch_location(list(keys))
            except (InvalidCredentialsError, InvalidStateError, UnauthorizedError):
                raise ReauthenticationRequired("Apple session expired") from None
            except ValueError as error:
                if str(error) == "No username or password specified":
                    raise ReauthenticationRequired("Apple session expired") from None
                raise
            newest = max(
                (r for r in found.values() if r is not None),
                key=lambda r: r.timestamp,
                default=None,
            )
            if newest is not None:
                candidate = report_mapping(newest)
                if self.report is None or datetime.fromisoformat(
                    candidate["last_seen"]
                ) >= datetime.fromisoformat(self.report["last_seen"]):
                    self.report = candidate
            return self.report

    async def close(self):
        await self.account.close()


def account_items(data):
    """Keep the original entity identifier when upgrading a single-item vault."""
    if data.get("version") == 2:
        return data["items"]
    return {"legacy": {"accessory": data["accessory"], "report": data.get("report")}}


def indexed_keys(accessory, indices):
    """Derivation can be expensive after restore; keep it off HA's event loop."""
    mapping = {}
    for index in indices:
        for key in accessory.keys_at(index):
            mapping[key] = min(index, mapping.get(key, index))
    return mapping


class AccountClient:
    """One session per account, with separately attributed accessory reports."""

    def __init__(self, account, items):
        self.account = account
        self.items = items
        self.clients = {
            identifier: Client(
                account,
                FindMyAccessory.from_json(item["accessory"]),
                item.get("report"),
            )
            for identifier, item in items.items()
        }
        self.lock = asyncio.Lock()
        self._poll_diagnostics = _new_poll_diagnostics(len(self.clients))

    def poll_diagnostics(self):
        """Describe only the latest poll, not tracker availability or location age.

        Fetch calls count SDK invocations, not HTTP requests. Decoded reports count
        non-null latest-per-key values returned by that SDK, not all historical
        records. An equal timestamp can be returned again without advancing it.
        """
        return (
            validated_poll_diagnostics(getattr(self, "_poll_diagnostics", None))
            or _new_poll_diagnostics(len(self.clients))
        )

    @classmethod
    def restore(cls, data, libraries):
        return cls(
            configure_report_account(configure_account(
                AsyncAppleAccount.from_json(data["session"], anisette_libs_path=libraries)
            )),
            account_items(data),
        )

    async def poll(self):
        async with self.lock, _observe_poll(self) as observation:
            # Query bounded batches so a growing item count never creates a giant request.
            now = datetime.now(timezone.utc)
            item_keys = {}
            key_indices = {}
            cursors = {}
            for identifier, client in self.clients.items():
                first, last = report_window(client.accessory, now)
                if last < first:
                    raise ValueError(
                        "Accessory key window is outside bounded polling limits"
                    )
                indices = range(max(0, first), last + 1)
                cursor = None
                if last - first > 8192:
                    # A stale alignment is uncertainty, not a reason to query
                    # years of keys at once. Resume a descending bounded search
                    # and also check the estimated recent window on each poll.
                    before = self.items[identifier].get("search_before", last + 1)
                    if type(before) is not int or not first < before <= last + 1:
                        before = last + 1
                    lower = max(0, first, before - 4096)
                    indices = set(range(lower, before)) | set(
                        range(max(0, first, last - 671), last + 1)
                    )
                    cursor = lower if lower > first else last + 1
                # Secondary keys cover several indices. Use the lowest match
                # so recovered alignment stays conservative.
                mapping = await asyncio.to_thread(
                    indexed_keys, client.accessory, indices
                )
                item_keys[identifier] = set(mapping)
                key_indices[identifier] = mapping
                cursors[identifier] = cursor
            combined = list(set().union(*item_keys.values()))
            found = {}
            try:
                async with asyncio.timeout(120):
                    for offset in range(0, len(combined), 200):
                        observation["fetch_calls"] = min(observation["fetch_calls"] + 1, POLL_LIMIT)
                        found.update(
                            await self.account.fetch_location(
                                combined[offset : offset + 200]
                            )
                        )
            except (InvalidCredentialsError, InvalidStateError, UnauthorizedError):
                raise ReauthenticationRequired("Apple session expired") from None
            except ValueError as error:
                if str(error) == "No username or password specified":
                    raise ReauthenticationRequired("Apple session expired") from None
                raise
            finally:
                observation["decoded_reports"] = min(
                    sum(value is not None for value in found.values()), POLL_LIMIT
                )
            results = {}
            # Commit results together only after all item reports validate successfully.
            for identifier, client in self.clients.items():
                candidates = []
                for key in item_keys[identifier]:
                    if found.get(key) is None:
                        continue
                    try:
                        candidates.append(report_mapping(found[key]))
                    except (ValueError, TypeError, AttributeError, OverflowError):
                        continue
                candidate = max(
                    candidates,
                    key=lambda value: datetime.fromisoformat(value["last_seen"]),
                    default=None,
                )
                previous = client.report
                accepted = False
                if candidate is not None:
                    observation["items_with_returned_valid_reports"] += 1
                    if previous is None or datetime.fromisoformat(candidate["last_seen"]) > datetime.fromisoformat(previous["last_seen"]):
                        observation["items_with_advanced_reports"] += 1
                if candidate is not None and (
                    previous is None
                    or datetime.fromisoformat(candidate["last_seen"])
                    >= datetime.fromisoformat(previous["last_seen"])
                ):
                    previous = candidate
                    accepted = True
                if previous is not None and not accepted:
                    observation["items_retaining_previous_report"] += 1
                if previous is None:
                    observation["items_without_report"] += 1
                results[identifier] = previous
            for identifier, report in results.items():
                self.clients[identifier].report = report
                self.items[identifier]["report"] = report
                client = self.clients[identifier]
                if report is not None and hasattr(client.accessory, "update_alignment"):
                    matches = [
                        (value.timestamp, key_indices[identifier][key])
                        for key, value in found.items()
                        if key in key_indices[identifier]
                        and value is not None
                        and value.timestamp.isoformat() == report["last_seen"]
                    ]
                    for timestamp, index in sorted(matches):
                        client.accessory.update_alignment(timestamp, index)
                    self.items[identifier]["accessory"] = client.accessory.to_json()
                if cursors[identifier] is None:
                    self.items[identifier].pop("search_before", None)
                else:
                    self.items[identifier]["search_before"] = cursors[identifier]
            return results

    async def close(self):
        await self.account.close()
