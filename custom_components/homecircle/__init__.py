"""HomeCircle normalization lifecycle. No recorder entities or location history."""

from dataclasses import dataclass, field
from datetime import timedelta
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
from homeassistant.util import dt as dt_util

from .normalize import Household, normalize_household

from .const import DOMAIN
from .selection import selected_entities
from . import api, frontend
from homeassistant.components import websocket_api


CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass
class HomeCircleRuntime:
    """In-memory selected state references, cleared on unload; no history store."""

    config: dict[str, Any]
    household: Household | None = None
    states: dict[str, State | None] = field(default_factory=dict)
    missing: set[str] = field(default_factory=set)
    unavailable: set[str] = field(default_factory=set)


type HomeCircleEntry = ConfigEntry[HomeCircleRuntime]


async def async_setup(hass, config):
    websocket_api.async_register_command(hass, api.websocket_snapshot)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: HomeCircleEntry) -> bool:
    """Track only selected HA entities without writing to their integrations."""
    await frontend.async_register(hass)
    runtime = entry.runtime_data = HomeCircleRuntime(dict(entry.options or entry.data))
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
    # Reports age even when no state changes. This timer does no network work.
    entry.async_on_unload(
        async_track_time_interval(hass, refresh, timedelta(seconds=30))
    )
    entry.async_on_unload(lambda: ir.async_delete_issue(hass, DOMAIN, issue_id))
    refresh()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HomeCircleEntry) -> bool:
    """HA removes registered listeners after this successful unload."""
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
    return True


async def async_remove_entry(hass: HomeAssistant, entry: HomeCircleEntry) -> None:
    """Clean up an owned resource even when the entry was not loaded."""
    await frontend.async_unregister(hass)
