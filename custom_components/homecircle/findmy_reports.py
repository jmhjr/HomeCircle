"""Bounded Find My report polling with explicit session expiration."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
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
POLL_STATUSES = ("not_polled", "in_progress", "success", "partial", "failed", "cancelled")
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
            or (value["status"] not in ("success", "partial") and any(value[key] for key in _ITEM_OUTCOMES))):
        return None
    return {"schema": 1, "status": value["status"], **{key: value[key] for key in POLL_COUNTERS}}


@asynccontextmanager
async def _observe_poll(client):
    """Observe one serialized account poll without exporting item or error values."""
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
        current["status"] = "partial" if client.failed_items else "success"


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


@dataclass
class _ItemSearch:
    key_indices: dict
    historical_indices: dict
    first: int
    last: int
    before: int | None = None
    lower: int | None = None

    def cursor_after(self, completed_keys):
        """Advance only past indices whose primary AND secondary keys completed."""
        remaining = (index for key, index in self.historical_indices.items()
                     if key not in completed_keys)
        position = max(remaining, default=self.lower - 1) + 1
        return position if position > max(0, self.first) else self.last + 1


def _item_search(accessory, now, saved_cursor):
    """Prepare bounded key batches and conservative cursor requirements off-loop."""
    first, last = report_window(accessory, now)
    if last < first:
        raise ValueError("Accessory key window is outside bounded polling limits")
    before = lower = None
    indices = range(max(0, first), last + 1)
    if last - first > 8192:
        before = saved_cursor
        if type(before) is not int or not first < before <= last + 1:
            before = last + 1
        lower = max(0, first, before - 4096)
        indices = sorted(set(range(lower, before)) | set(
            range(max(0, first, last - 671), last + 1)
        ))
    mapping, historical = {}, {}
    for index in indices:
        for key in accessory.keys_at(index):
            # A secondary key may match two primary buckets: keep alignment low,
            # but require every historical occurrence before skipping an index.
            mapping[key] = min(index, mapping.get(key, index))
            if before is not None and lower <= index < before:
                historical[key] = max(index, historical.get(key, index))
    return _ItemSearch(mapping, historical, first, last, before, lower)


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
        self.failed_items = set()
        self.poll_progress = False

    def poll_diagnostics(self):
        """Describe only the latest poll, not tracker availability or location age.

        Fetch calls count SDK invocations, not HTTP requests. Decoded reports count
        non-null latest-per-key values returned by that SDK, not all historical
        records. An equal timestamp can be returned again without advancing it.
        Partial status means at least one item failed after some batch completed;
        cached locations and valid completed results are still retained.
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
            self.failed_items = set()
            self.poll_progress = False
            completed_batches = 0
            last_error = None
            now = datetime.now(timezone.utc)
            results = {}
            for identifier, client in self.clients.items():
                found = {}
                search = None
                completed_keys = set()
                try:
                    search = await asyncio.to_thread(
                        _item_search, client.accessory, now,
                        self.items[identifier].get("search_before"),
                    )
                    # Descending batches retain the completed prefix of a stale
                    # search, while the recent window is checked on every poll.
                    keys = sorted(search.key_indices, key=search.key_indices.get, reverse=True)
                    async with asyncio.timeout(120):
                        for offset in range(0, len(keys), 200):
                            batch = keys[offset:offset + 200]
                            observation["fetch_calls"] = min(observation["fetch_calls"] + 1, POLL_LIMIT)
                            found.update(await self.account.fetch_location(batch))
                            completed_keys.update(batch)
                            completed_batches += 1
                            self.poll_progress = True
                except (InvalidCredentialsError, InvalidStateError, UnauthorizedError):
                    raise ReauthenticationRequired("Apple session expired") from None
                except ValueError as error:
                    if str(error) == "No username or password specified":
                        raise ReauthenticationRequired("Apple session expired") from None
                    self.failed_items.add(identifier)
                    last_error = error
                except Exception as error:
                    self.failed_items.add(identifier)
                    last_error = error
                finally:
                    # Commit completed batches even if a later batch, authentication
                    # exchange or cancellation interrupts this item. Never skip keys
                    # from a failed batch when advancing the historical cursor.
                    if search is not None and completed_keys:
                        if search.before is None:
                            self.items[identifier].pop("search_before", None)
                        else:
                            self.items[identifier]["search_before"] = search.cursor_after(completed_keys)
                    mapping = search.key_indices if search is not None else {}
                    candidates = []
                    valid = {}
                    for key, value in found.items():
                        if key not in mapping or value is None:
                            continue
                        observation["decoded_reports"] = min(observation["decoded_reports"] + 1, POLL_LIMIT)
                        try:
                            candidate = report_mapping(value)
                        except (ValueError, TypeError, AttributeError, OverflowError):
                            continue
                        candidates.append(candidate)
                        valid[key] = value
                    candidate = max(candidates, key=lambda value: datetime.fromisoformat(value["last_seen"]), default=None)
                    previous = client.report
                    accepted = candidate is not None and (
                        previous is None or datetime.fromisoformat(candidate["last_seen"]) >= datetime.fromisoformat(previous["last_seen"])
                    )
                    if candidate is not None:
                        observation["items_with_returned_valid_reports"] += 1
                        if previous is None or datetime.fromisoformat(candidate["last_seen"]) > datetime.fromisoformat(previous["last_seen"]):
                            observation["items_with_advanced_reports"] += 1
                    if accepted:
                        client.report = candidate
                    elif previous is not None:
                        observation["items_retaining_previous_report"] += 1
                    if client.report is None:
                        observation["items_without_report"] += 1
                    results[identifier] = client.report
                    self.items[identifier]["report"] = client.report
                    if accepted and hasattr(client.accessory, "update_alignment"):
                        matches = [(value.timestamp, mapping[key]) for key, value in valid.items()
                                   if value.timestamp.isoformat() == candidate["last_seen"]]
                        for timestamp, index in sorted(matches):
                            client.accessory.update_alignment(timestamp, index)
                        self.items[identifier]["accessory"] = client.accessory.to_json()
            if last_error is not None and not completed_batches:
                raise last_error
            return results

    async def close(self):
        await self.account.close()
