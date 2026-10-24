"""HomeCircle-owned Find My trackers with independent account polling and health."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from pathlib import Path
import re

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .findmy_setup import sdk
from .findmy_vault import Vault, VaultError
from .tracker_providers import ProviderHealth
from .provider_controls import ProviderPaused, async_get_controls

PREFIX = "homecircle_findmy_"


def validated_polling_snapshot(value):
    """Accept only fixed aggregate counters for the optional diagnostics export."""
    from .findmy_reports import POLL_COUNTERS, POLL_LIMIT, POLL_STATUSES

    if (type(value) is not dict
            or set(value) != {"schema", "accounts", "accounts_without_observation", "status_counts", *POLL_COUNTERS}
            or type(value["schema"]) is not int or value["schema"] != 1
            or type(value["status_counts"]) is not dict
            or set(value["status_counts"]) != set(POLL_STATUSES)):
        return None
    for key in ("accounts", "accounts_without_observation", *POLL_COUNTERS):
        if type(value[key]) is not int or not 0 <= value[key] <= POLL_LIMIT:
            return None
    statuses = value["status_counts"]
    if (any(type(statuses[key]) is not int or not 0 <= statuses[key] <= POLL_LIMIT
            for key in POLL_STATUSES)
            or sum(statuses.values()) + value["accounts_without_observation"] != value["accounts"]):
        return None
    if (any(value[key] > value["selected_items"] for key in POLL_COUNTERS[3:])
            or value["items_with_advanced_reports"] > value["items_with_returned_valid_reports"]
            or value["items_retaining_previous_report"] + value["items_without_report"] > value["selected_items"]):
        return None
    return {
        "schema": 1, "accounts": value["accounts"],
        "accounts_without_observation": value["accounts_without_observation"],
        "status_counts": {key: statuses[key] for key in POLL_STATUSES},
        **{key: value[key] for key in POLL_COUNTERS},
    }


def account_root(hass, metadata, create=False):
    base = Path(hass.config.path(".storage", "homecircle_findmy"))
    if create:
        base.mkdir(mode=0o700, parents=True, exist_ok=True)
    if base.exists() or base.is_symlink():
        Vault(base)._check(base, directory=True)
    storage_id = metadata["storage_id"]
    if storage_id == "legacy":
        return base
    if not isinstance(storage_id, str) or not re.fullmatch(r"[a-f0-9]{32}", storage_id):
        raise VaultError("Invalid account storage identifier")
    parent = base / "homecircle_accounts"
    if create:
        parent.mkdir(mode=0o700, exist_ok=True)
    if parent.exists() or parent.is_symlink():
        Vault(parent)._check(parent, directory=True)
    return parent / storage_id


def tracker_unique_id(account_id, identifier, item):
    value = item.get("unique_id") or f"{PREFIX}{account_id}_{identifier}"
    if (
        not isinstance(value, str)
        or not value.startswith(PREFIX)
        or not re.fullmatch(r"[A-Za-z0-9_]+", value)
    ):
        raise VaultError("Invalid tracker identity")
    return value


class FindMyTracker(TrackerEntity):
    _attr_source_type = SourceType.GPS
    _attr_should_poll = False

    def __init__(self, unique_id, label, kind="airtag", previous=None):
        self._attr_unique_id = unique_id
        self._attr_name = label
        self.kind = kind
        self.report = previous or {}
        self._attr_available = bool(self.report)
        self.status = "last_report" if previous else "waiting_for_report"

    def update(self, report, failed=False):
        if report:
            self.report = report
        self._attr_available = bool(self.report)
        self.status = (
            "account_unavailable"
            if failed
            else "last_report"
            if self.report
            else "waiting_for_report"
        )
        if self.entity_id and getattr(self, "hass", None):
            self.async_write_ha_state()

    @property
    def latitude(self):
        return self.report.get("latitude")

    @property
    def longitude(self):
        return self.report.get("longitude")

    @property
    def location_accuracy(self):
        value = self.report.get("gps_accuracy")
        return round(value) if value is not None else 0

    @property
    def extra_state_attributes(self):
        return {
            "last_seen": self.report.get("last_seen"),
            "battery_status": self.report.get("battery_status")
            if self.kind == "airtag"
            else None,
            "battery_status_reported_at": self.report.get("last_seen")
            if self.report.get("battery_status")
            else None,
            "accessory_type": self.kind,
            "location_status": self.status,
            "attribution": "Apple Find My",
        }


class DirectFindMy:
    """An account error must never stop other accounts or other tracker providers."""

    def __init__(self, hass, accounts, add_entities, entry_id):
        self.hass, self.accounts, self.add_entities, self.entry_id = (
            hass,
            accounts,
            add_entities,
            entry_id,
        )
        self.clients, self.vaults, self.trackers, self.states, self.tasks = (
            {},
            {},
            {},
            {},
            {},
        )
        self.stopped = False
        self.unsub = None
        self.last_success = None
        self.last_error = None
        self.poll_slots = asyncio.Semaphore(2)
        self.controls = None

    async def async_start(self):
        self.controls = await async_get_controls(self.hass, self.entry_id)
        if self.controls.paused("findmy"):
            return
        # The cold SDK import reads installed-package metadata (anisette).
        await self.hass.async_add_executor_job(sdk)
        from .findmy_reports import AccountClient, account_items

        entry = self.hass.config_entries.async_get_entry(self.entry_id)
        registry = er.async_get(self.hass)
        for account_id, metadata in self.accounts.items():
            blocked = self.controls.paused("findmy", account_id)
            self.states[account_id] = "starting"
            if not isinstance(metadata, dict) or not isinstance(
                metadata.get("items"), dict
            ):
                self.states[account_id] = "unexpected_response"
                continue
            previous = {}
            try:
                if blocked:
                    raise ProviderPaused()
                root = await self.hass.async_add_executor_job(
                    account_root, self.hass, metadata
                )
                vault = Vault(root)
                data = await self.hass.async_add_executor_job(vault.load)
                expected_identity = metadata.get("account_identity")
                if expected_identity is not None:
                    from .findmy_identity import authenticated_identity

                    if authenticated_identity(data.get("session")) != expected_identity:
                        raise VaultError("Stored session belongs to a different account")
                items = account_items(data)
                chosen = metadata["items"]
                if not chosen or any(identifier not in items for identifier in chosen):
                    raise VaultError("Selected items are not in account storage")
                data = {
                    **data,
                    "version": 2,
                    "items": {identifier: items[identifier] for identifier in chosen},
                }
                client = await self.hass.async_add_executor_job(
                    AccountClient.restore,
                    data,
                    Path(
                        self.hass.config.path(
                            ".storage", "homecircle_findmy", "anisette-libs.bin"
                        )
                    ),
                )
                self.vaults[account_id], self.clients[account_id] = vault, client
                previous = {
                    identifier: item.get("report")
                    for identifier, item in data["items"].items()
                }
            except ProviderPaused:
                self.states[account_id] = "paused"
            except Exception:
                self.states[account_id] = "unexpected_response"
                self.last_error = dt_util.utcnow()
            self.trackers[account_id] = {}
            for identifier, item in metadata.get("items", {}).items():
                try:
                    unique = tracker_unique_id(account_id, identifier, item)
                except (AttributeError, VaultError):
                    self.states[account_id] = "unexpected_response"
                    continue
                tracker = FindMyTracker(
                    unique,
                    item.get("name") or "Find My item",
                    item.get("type", "airtag"),
                    previous.get(identifier),
                )
                registered = registry.async_get_or_create(
                    "device_tracker",
                    "homecircle",
                    unique,
                    config_entry=entry,
                    suggested_object_id=tracker.name,
                    original_name=tracker.name,
                )
                tracker.entity_id = registered.entity_id
                self.trackers[account_id][identifier] = tracker
                if account_id not in self.clients:
                    tracker.update(None, failed=True)
            self.add_entities(list(self.trackers[account_id].values()))
        self.unsub = async_track_time_interval(
            self.hass, self.interval, timedelta(minutes=5)
        )
        self.interval()

    @callback
    def interval(self, event=None):
        if self.stopped:
            return
        for account_id in self.clients:
            if self.controls is not None and self.controls.paused("findmy", account_id):
                self.states[account_id] = "paused"
                continue
            if self.states.get(account_id) == "auth_required":
                continue
            task = self.tasks.get(account_id)
            if task is None or task.done():
                self.tasks[account_id] = self.hass.async_create_background_task(
                    self.poll(account_id),
                    "HomeCircle Find My account poll",
                    eager_start=False,
                )

    async def poll(self, account_id):
        if self.controls is None:
            self.controls = await async_get_controls(self.hass, self.entry_id)
        try:
            async with self.controls.operation("findmy", account_id):
                await self._poll_account(account_id)
        except ProviderPaused:
            self.states[account_id] = "paused"

    async def _poll_account(self, account_id):
        from .findmy_reports import ReauthenticationRequired

        client = self.clients[account_id]
        save_attempted = False
        try:
            async with self.poll_slots:
                if self.stopped:
                    return
                reports = await client.poll()
            if self.stopped:
                return
            save_attempted = True
            await self.save_poll_progress(account_id, client)
            failed_items = getattr(client, "failed_items", set())
            self.states[account_id] = "partial" if failed_items else "connected"
            if failed_items:
                self.last_error = dt_util.utcnow()
            ir.async_delete_issue(
                self.hass, "homecircle", f"findmy_auth_{self.entry_id}_{account_id}"
            )
            self.last_success = dt_util.utcnow()
            for identifier, tracker in self.trackers[account_id].items():
                tracker.update(reports.get(identifier), failed=identifier in failed_items)
        except asyncio.CancelledError:
            # Unload/reconnect waits for this task before replacing a session.
            # Retain completed batches before releasing that writer ownership.
            if not save_attempted and getattr(client, "poll_progress", False):
                try:
                    await self.save_poll_progress(account_id, client)
                except Exception:
                    pass
            raise
        except Exception as error:
            self.states[account_id] = (
                "auth_required"
                if isinstance(error, ReauthenticationRequired)
                else "network_error"
            )
            try:
                if isinstance(error, ReauthenticationRequired):
                    try:
                        await self.controls.async_pause_denied("findmy", account_id)
                    except Exception:
                        # The controls object remains blocked on a storage failure.
                        pass
            finally:
                # A durable denial can trigger unload while its callback is
                # still returning. Preserve completed batches even when that
                # unload cancels the poll before the normal error path resumes.
                if not save_attempted and getattr(client, "poll_progress", False):
                    save_attempted = True
                    try:
                        await self.save_poll_progress(account_id, client)
                    except Exception:
                        pass
            self.last_error = dt_util.utcnow()
            if self.states[account_id] == "auth_required":
                ir.async_create_issue(
                    self.hass,
                    "homecircle",
                    f"findmy_auth_{self.entry_id}_{account_id}",
                    is_fixable=False,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key="findmy_account_auth",
                    translation_placeholders={
                        "account": self.accounts[account_id].get(
                            "label", "Apple account"
                        )
                    },
                )
            for identifier, tracker in self.trackers[account_id].items():
                tracker.update(client.items.get(identifier, {}).get("report"), failed=True)

    async def save_poll_progress(self, account_id, client):
        """Drain an atomic vault write before reconnect/unload can replace it."""
        write = self.hass.async_add_executor_job(
            self.vaults[account_id].save_account,
            client.account.to_json(),
            client.items,
        )
        # Never shield a potentially failing executor future directly: on Python
        # 3.14 a failure after cancellation can be logged before it is consumed.
        pending = asyncio.gather(write, return_exceptions=True)
        cancellation = None
        while not pending.done():
            try:
                await asyncio.shield(pending)
            except asyncio.CancelledError as error:
                # An executor write cannot be cancelled; repeated cancellation
                # must not let reconnect begin a second write before it finishes.
                if cancellation is None:
                    cancellation = error
        result = pending.result()[0]
        if cancellation is not None:
            raise cancellation
        if isinstance(result, BaseException):
            raise result

    async def pause_account(self, account_id):
        """Stop this account's poll before replacing its encrypted session."""
        client = self.clients.pop(account_id, None)
        task = self.tasks.pop(account_id, None)
        if task and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self.states[account_id] = "starting"
        return client

    def resume_account(self, account_id, client):
        if client is not None and not self.stopped:
            self.clients[account_id] = client
            self.states[account_id] = (
                "paused"
                if self.controls is not None and self.controls.paused("findmy", account_id)
                else "starting"
            )
            self.interval()

    def health_snapshot(self):
        values = list(self.states.values())
        state = (
            "paused"
            if values and all(v == "paused" for v in values)
            else "connected"
            if values and all(v == "connected" for v in values)
            else "partial"
            if "connected" in values or "partial" in values
            else "auth_required"
            if "auth_required" in values
            else "network_error"
            if "network_error" in values
            else "unexpected_response"
            if "unexpected_response" in values
            else "starting"
        )
        trackers = [
            tracker
            for account in self.trackers.values()
            for tracker in account.values()
        ]
        return ProviderHealth(
            state=state,
            discovered_trackers=len(trackers),
            available_trackers=sum(tracker.available for tracker in trackers),
            last_api_success=self.last_success,
            last_error=self.last_error,
        )

    def polling_snapshot(self):
        """Aggregate the last account polls without account or item identifiers.

        Availability and source age remain separate from these observations.
        Fetch calls are logical SDK calls, not measured HTTP request counts.
        """
        from .findmy_reports import (
            POLL_COUNTERS, POLL_LIMIT, POLL_STATUSES, validated_poll_diagnostics,
        )

        result = {
            "schema": 1, "accounts": len(self.accounts), "accounts_without_observation": 0,
            "status_counts": dict.fromkeys(POLL_STATUSES, 0),
            **dict.fromkeys(POLL_COUNTERS, 0),
        }
        for account_id in self.accounts:
            try:
                getter = getattr(self.clients.get(account_id), "poll_diagnostics", None)
                observation = validated_poll_diagnostics(getter()) if callable(getter) else None
            except Exception:
                observation = None
            if observation is None:
                result["accounts_without_observation"] += 1
                continue
            result["status_counts"][observation["status"]] += 1
            for key in POLL_COUNTERS:
                result[key] = min(result[key] + observation[key], POLL_LIMIT)
        return validated_polling_snapshot(result)

    async def async_stop(self):
        self.stopped = True
        if self.unsub:
            self.unsub()
        for task in self.tasks.values():
            if not task.done():
                task.cancel()
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        await asyncio.gather(
            *(client.close() for client in self.clients.values()),
            return_exceptions=True,
        )
        self.clients.clear()
