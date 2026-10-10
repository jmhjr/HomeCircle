"""Bounded location checks for an explicitly selected stale household member."""

from datetime import timedelta

from homeassistant.auth.permissions.const import POLICY_CONTROL
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .const import CONF_AUTO_REQUEST_LOCATION, CONF_MEMBERS, CONF_TRACKERS
from .location_requests import (
    MAX_REQUESTS,
    REQUEST_WINDOW,
    RETRY_PERIOD,
    async_request_quiet_locations,
    async_reserve_request,
    available_notification_entity,
)
from .tracker_providers import TRACKER_PROVIDERS

CLOUD_COOLDOWN = timedelta(minutes=1)


async def async_refresh_selected(hass, runtime, member, user, entry_id):
    """Use only the selected map source; never infer another phone association."""
    location = member.location
    if not member.focusable or location is None:
        return {"status": "no_position"}
    if location.evidence.freshness != "stale":
        return {"status": "fresh"}
    source = location.evidence.source_entity
    config = runtime.config[CONF_MEMBERS][member.id]
    if source not in config[CONF_TRACKERS]:
        return {"status": "unsupported"}
    registry = er.async_get(hass)
    registered = registry.async_get(source)
    if registered is None or registered.disabled:
        return {"status": "unsupported"}
    now = dt_util.utcnow()
    if registered.platform == "mobile_app":
        if config.get(CONF_AUTO_REQUEST_LOCATION) is not True:
            return {"status": "disabled"}
        target = available_notification_entity(hass, registry, source)
        if target is None or not hass.services.has_service("notify", "send_message"):
            return {"status": "unavailable"}
        if not all(
            user.permissions.check_entity(entity, POLICY_CONTROL)
            for entity in (source, target)
        ):
            return {"status": "not_allowed"}
        recent = [
            stamp
            for stamp in runtime.location_request_times.get(source, [])
            if now - stamp < REQUEST_WINDOW
        ]
        if len(recent) >= MAX_REQUESTS:
            return {"status": "limited"}
        if recent and now - max(recent) < RETRY_PERIOD:
            return {"status": "cooldown"}
        before = runtime.last_location_request.get(source)
        await async_request_quiet_locations(
            hass, runtime, now, member_id=member.id, on_selection=True
        )
        if runtime.last_location_request.get(source) == before:
            return {"status": "unavailable"}
        return {
            "status": "send_failed"
            if source in runtime.location_request_failures
            else "requested"
        }
    if registered.platform == "life360":
        # Use only the installed integration's supported, entity-targeted action.
        if not hass.services.has_service("life360", "update_location"):
            return {"status": "unsupported"}
        if not user.permissions.check_entity(source, POLICY_CONTROL):
            return {"status": "not_allowed"}
        reserved = await async_reserve_request(runtime, source, now)
        if reserved != "reserved":
            return {"status": reserved}
        try:
            await hass.services.async_call(
                "life360", "update_location", {"entity_id": [source]}, blocking=True
            )
        except Exception:
            runtime.location_request_failures.add(source)
            return {"status": "send_failed"}
        runtime.location_request_failures.discard(source)
        return {"status": "requested"}
    provider = next(
        (item for item in TRACKER_PROVIDERS if item.owns_entity(registry, source)), None
    )
    if provider is None or registered.config_entry_id != entry_id:
        return {"status": "unsupported"}
    client = runtime.managed_trackers.get(provider.id)
    check = getattr(client, "async_refresh_on_selection", None)
    if check is None:
        return {"status": "unsupported"}
    previous = runtime.selection_refresh_times.get(provider.id)
    if previous and now - previous < CLOUD_COOLDOWN:
        return {"status": "cooldown"}
    reserved = await async_reserve_request(runtime, source, now)
    if reserved != "reserved":
        return {"status": reserved}
    # Reserve before awaiting so concurrent viewers cannot multiply cloud calls.
    runtime.selection_refresh_times[provider.id] = now
    return {"status": await check()}
