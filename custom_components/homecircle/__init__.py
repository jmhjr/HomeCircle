"""HomeCircle normalization and bounded activity lifecycle."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from asyncio import Task
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .activity import ActivityLog
from .normalize import Household, normalize_household
from .location_requests import async_request_quiet_locations, restore_automatic_requests

from .const import DOMAIN
from .selection import selected_entities
from .tracker_providers import TrackerClient, connected_providers
from . import api, dashboard_setup, frontend
from homeassistant.components import websocket_api


CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
_LOGGER = logging.getLogger(__name__)


@dataclass
class HomeCircleRuntime:
    """Selected state references and bounded local activity."""

    config: dict[str, Any]
    activity: ActivityLog | None = None
    household: Household | None = None
    states: dict[str, State | None] = field(default_factory=dict)
    missing: set[str] = field(default_factory=set)
    unavailable: set[str] = field(default_factory=set)
    managed_trackers: dict[str, TrackerClient] = field(default_factory=dict)
    last_location_request: dict[str, datetime] = field(default_factory=dict)
    location_request_times: dict[str, list[datetime]] = field(default_factory=dict)
    automatic_location_requests: dict[str, dict] = field(default_factory=dict)
    location_request_failures: set[str] = field(default_factory=set)
    restored_location_requests: set[str] = field(default_factory=set)
    location_request_store: Store | None = None
    location_request_task: Task | None = None
    family_refresh: dict = field(default_factory=dict)
    location_request_lock: Any = None
    selection_refresh_times: dict[str, datetime] = field(default_factory=dict)
    selection_refresh_results: dict[str, dict[str, str]] = field(default_factory=dict)


type HomeCircleEntry = ConfigEntry[HomeCircleRuntime]


async def async_setup(hass, config):
    websocket_api.async_register_command(hass, api.websocket_snapshot)
    websocket_api.async_register_command(hass, api.websocket_refresh_location)
    websocket_api.async_register_command(hass, api.websocket_refresh_family)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: HomeCircleEntry) -> bool:
    """Track selected HA entities and optional HomeCircle-owned Life360 trackers."""
    await frontend.async_register(hass)
    try:
        await dashboard_setup.async_ensure_dashboard(hass)
    except Exception:
        # Dashboard creation is optional; the integration and existing views
        # must still work when Lovelace storage cannot be changed.
        _LOGGER.exception("Could not create the optional HomeCircle dashboard")
    runtime = entry.runtime_data = HomeCircleRuntime(dict(entry.options or entry.data))
    runtime.activity = ActivityLog(
        runtime.config, Store(hass, 1, f"{DOMAIN}.activity.{entry.entry_id}")
    )
    await runtime.activity.load()
    runtime.location_request_store = Store(
        hass, 1, f"{DOMAIN}.location_requests.{entry.entry_id}"
    )
    try:
        saved_requests = await runtime.location_request_store.async_load() or {}
    except Exception:
        _LOGGER.warning("HomeCircle could not load its location request limits")
        runtime.location_request_store = None
        saved_requests = {}
    runtime.automatic_location_requests = restore_automatic_requests(
        saved_requests.get("automatic", {}) if isinstance(saved_requests, dict) else {}
    )
    saved_times = (
        saved_requests.get("requests", {}) if isinstance(saved_requests, dict) else {}
    )
    if not isinstance(saved_times, dict):
        saved_times = {}
    now = dt_util.utcnow()
    for tracker_id, raw_times in saved_times.items():
        if not isinstance(tracker_id, str) or not isinstance(raw_times, list):
            continue
        times = []
        for raw_time in raw_times:
            parsed = (
                dt_util.parse_datetime(raw_time) if isinstance(raw_time, str) else None
            )
            if (
                parsed is not None
                and parsed.tzinfo is not None
                and now - parsed < timedelta(days=1)
            ):
                times.append(parsed)
        if times:
            runtime.location_request_times[tracker_id] = times
            runtime.last_location_request[tracker_id] = max(times)
            runtime.restored_location_requests.add(tracker_id)
    entity_ids = selected_entities(runtime.config)
    issue_id = f"missing_entities_{entry.entry_id}"

    @callback
    def refresh(event=None):
        registry = er.async_get(hass)
        runtime.states = {}
        for entity_id in entity_ids:
            registered = registry.async_get(entity_id)
            runtime.states[entity_id] = (
                None
                if registered and registered.disabled
                else hass.states.get(entity_id)
            )
        runtime.missing = {
            key for key, value in runtime.states.items() if value is None
        }
        runtime.unavailable = {
            key
            for key, value in runtime.states.items()
            if value is None or value.state in (STATE_UNKNOWN, STATE_UNAVAILABLE)
        }
        runtime.household = normalize_household(
            runtime.config,
            runtime.states,
            dt_util.utcnow(),
            {item.entity_id: item.name for item in hass.states.async_all("zone")},
        )
        runtime.activity.observe(runtime.household, dt_util.utcnow())
        from .family_refresh import observe_family_refresh

        observe_family_refresh(runtime, dt_util.utcnow())
        if runtime.missing:
            ir.async_create_issue(
                hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="missing_entities",
                translation_placeholders={"count": str(len(runtime.missing))},
            )
        else:
            ir.async_delete_issue(hass, DOMAIN, issue_id)

    @callback
    def registry_filter(data):
        return (
            data["entity_id"] in entity_ids
            or data.get("changes", {}).get("entity_id") in entity_ids
        )

    entry.async_on_unload(async_track_state_change_event(hass, entity_ids, refresh))
    entry.async_on_unload(
        hass.bus.async_listen(
            er.EVENT_ENTITY_REGISTRY_UPDATED,
            refresh,
            event_filter=registry_filter,
        )
    )

    @callback
    def other_zone_filter(data):
        return (
            data["entity_id"].startswith("zone.")
            and data["entity_id"] not in entity_ids
        )

    # Unselected zone names are needed only to reject ambiguous legacy names.
    entry.async_on_unload(
        hass.bus.async_listen(
            EVENT_STATE_CHANGED,
            refresh,
            event_filter=other_zone_filter,
        )
    )

    @callback
    def periodic_refresh(event=None):
        refresh()
        if (
            runtime.location_request_task is None
            or runtime.location_request_task.done()
        ):
            runtime.location_request_task = hass.async_create_task(
                async_request_quiet_locations(hass, runtime, dt_util.utcnow()),
                f"HomeCircle quiet location requests {entry.entry_id}",
            )

    entry.async_on_unload(
        async_track_time_interval(hass, periodic_refresh, timedelta(seconds=30))
    )
    entry.async_on_unload(lambda: ir.async_delete_issue(hass, DOMAIN, issue_id))
    refresh()
    platforms = sorted(
        {provider.platform for provider in connected_providers(runtime.config)}
    )
    if platforms:
        await hass.config_entries.async_forward_entry_setups(entry, platforms)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HomeCircleEntry) -> bool:
    """HA removes registered listeners after this successful unload."""
    runtime = entry.runtime_data
    if runtime.activity is not None:
        await runtime.activity.close()
    if runtime.location_request_task is not None:
        runtime.location_request_task.cancel()
    for client in runtime.managed_trackers.values():
        await client.async_stop()
    platforms = sorted(
        {provider.platform for provider in connected_providers(runtime.config)}
    )
    if platforms:
        await hass.config_entries.async_unload_platforms(entry, platforms)
    runtime.managed_trackers.clear()
    if frontend.consume_reload_preservation(hass, entry.entry_id):

        async def cleanup_failed_reload():
            # The reload holds setup_lock through both unload and setup. If
            # setup fails, remove the resource after the lock is released.
            async with entry.setup_lock:
                if entry.state is not ConfigEntryState.LOADED:
                    await frontend.async_unregister(hass)

        hass.async_create_task(
            cleanup_failed_reload(),
            f"HomeCircle resource cleanup after reload {entry.entry_id}",
            eager_start=False,
        )
    else:
        await frontend.async_unregister(hass)
    entry.runtime_data.household = None
    entry.runtime_data.states.clear()
    entry.runtime_data.missing.clear()
    entry.runtime_data.unavailable.clear()
    entry.runtime_data.last_location_request.clear()
    entry.runtime_data.location_request_times.clear()
    entry.runtime_data.location_request_failures.clear()
    return True


async def async_remove_entry(hass: HomeAssistant, entry: HomeCircleEntry) -> None:
    """Clean up an owned resource even when the entry was not loaded."""
    await frontend.async_unregister(hass)
    await dashboard_setup.async_remove_untouched_dashboard(hass)
    await Store(hass, 1, f"{DOMAIN}.location_requests.{entry.entry_id}").async_remove()
    await Store(hass, 1, f"{DOMAIN}.activity.{entry.entry_id}").async_remove()
