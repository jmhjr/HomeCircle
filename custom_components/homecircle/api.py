"""Authenticated, permission-checked snapshots and bounded activity."""

from urllib.parse import unquote, urlsplit
from datetime import datetime

from homeassistant.util import dt as dt_util

from homeassistant.auth.permissions.const import POLICY_READ
from homeassistant.components import websocket_api
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
import voluptuous as vol

from .city_lookup import address_parts
from .pictures import picture_url
from .const import CONF_MEMBERS, CONF_SHOW_ON_MAP, CONF_TRACKERS, DOMAIN
from .normalize import coordinates
from .location_requests import available_notification_entity, request_status
from .selection import selected_entities
from .tracker_providers import TRACKER_PROVIDERS, connected_providers


TRACKER_PLATFORM_NAMES = {"life360_pet": "Life360 Pet GPS"}


def tracker_integration_label(registry, entity_id):
    """Identify a tracker's integration from HA registration, never its name."""
    if registry is None or (entity := registry.async_get(entity_id)) is None:
        return None
    if entity.platform == DOMAIN:
        return next(
            (
                provider.display_name
                for provider in TRACKER_PROVIDERS
                if provider.owns_entity(registry, entity_id)
            ),
            "HomeCircle",
        )
    for provider in TRACKER_PROVIDERS:
        if entity.platform in provider.external_platforms:
            return provider.display_name
    return TRACKER_PLATFORM_NAMES.get(
        entity.platform, entity.platform.replace("_", " ").title()
    )


def location_source_label(runtime, source_entity, registry=None):
    """Name only the exact Person or selected tracker behind this map point."""
    if not source_entity:
        return None
    source = runtime.states.get(source_entity)
    name = source.name if source else source_entity
    if source_entity.startswith("device_tracker."):
        trackers = (
            state
            for entity_id, state in runtime.states.items()
            if entity_id.startswith("device_tracker.") and state is not None
        )
        if sum(state.name.casefold() == name.casefold() for state in trackers) > 1:
            name = f"{name} ({source_entity})"
        integration = tracker_integration_label(registry, source_entity)
        if integration and not name.casefold().startswith(f"{integration} ".casefold()):
            return f"Tracker: {name} · {integration}"
        return f"Tracker: {name}"
    if source_entity.startswith("person."):
        return f"HA Person: {name}"
    return name


def proof(value, runtime, registry=None):
    source_entity = value.source_entity
    card_label = None
    if source_entity and source_entity.startswith("device_tracker."):
        integration = tracker_integration_label(registry, source_entity)
        if integration == "Mobile App":
            integration = "Home Assistant"
        card_label = f"Tracker: {integration or 'Home Assistant tracker'}"
    elif source_entity and source_entity.startswith("person."):
        card_label = "Source: HA Person"
    return {
        "reported_at": value.reported_at.isoformat() if value.reported_at else None,
        "observed_at": value.observed_at.isoformat() if value.observed_at else None,
        "freshness": value.freshness,
        "report_status": value.report_status,
        "source_label": location_source_label(runtime, value.source_entity, registry),
        "card_source_label": card_label,
    }


def member_arrival(member, runtime, registry=None):
    """Prefer actual provider arrival evidence from the exact selected map tracker."""
    fallback = (
        runtime.activity.arrival(member.id, member.place)
        if getattr(runtime, "activity", None) and member.focusable
        else None
    )
    if (
        not member.focusable
        or not member.location
        or member.presence == "driving"
        or registry is None
    ):
        return fallback
    source = member.location.evidence.source_entity
    if source not in runtime.config[CONF_MEMBERS][member.id][CONF_TRACKERS]:
        return fallback
    entity = registry.async_get(source)
    genuine = entity and (
        entity.platform == "life360"
        or any(
            provider.id == "life360" and provider.owns_entity(registry, source)
            for provider in TRACKER_PROVIDERS
        )
    )
    state = runtime.states.get(source)
    if not genuine or state is None or state.state in {"unknown", "unavailable"}:
        return fallback
    raw = state.attributes.get("at_loc_since")
    since = (
        raw
        if isinstance(raw, datetime)
        else dt_util.parse_datetime(raw)
        if isinstance(raw, str)
        else None
    )
    raw_report = state.attributes.get("last_seen")
    report = (
        raw_report
        if isinstance(raw_report, datetime)
        else dt_util.parse_datetime(raw_report)
        if isinstance(raw_report, str)
        else None
    )
    if (
        since is None
        or since.tzinfo is None
        or since > dt_util.utcnow()
        or report is None
        or report.tzinfo is None
        or since > report
    ):
        return fallback
    return {
        "since": since.isoformat(),
        "source": "tracker",
        "continuity_unconfirmed": False,
        "persistent": True,
    }


def reported_address(member, runtime):
    """Read only the address of the exact usable selected map tracker."""
    if member.place or not member.focusable or member.location is None:
        return None
    source = member.location.evidence.source_entity
    if source not in runtime.config[CONF_MEMBERS][member.id][CONF_TRACKERS]:
        return None
    state = runtime.states.get(source)
    if state is None or state.state in {"unknown", "unavailable"}:
        return None
    value = state.attributes.get("address")
    lookup = getattr(runtime, "city_lookup", None)
    if (
        runtime.config.get("city_lookup_enabled")
        and lookup
        and not address_parts(value)[1]
    ):
        found = lookup.cached(member.location.latitude, member.location.longitude)
        if found:
            street = address_parts(value)[0] or found.get("street")
            return f"{street}, {found['city']}" if street else found["city"]
    if not isinstance(value, str) or len(value) > 240:
        return None
    if any(ord(char) < 32 and char not in "\r\n\t" for char in value):
        return None
    value = " ".join(value.split())
    if not value or value.casefold() in {"unknown", "unavailable", "none", "null"}:
        return None
    return value


def reported_city(member, runtime):
    """Retain a structured lookup city even when its name also names a region."""
    if not reported_address(member, runtime):
        return None
    lookup = getattr(runtime, "city_lookup", None)
    if not runtime.config.get("city_lookup_enabled") or not lookup:
        return None
    state = runtime.states.get(member.location.evidence.source_entity)
    if state and not address_parts(state.attributes.get("address"))[1]:
        found = lookup.cached(member.location.latitude, member.location.longitude)
        return found.get("city") if found else None
    return None


def member_diagnostics(member, runtime, registry=None, admin=False):
    """Project only selected tracker states and the Person's active-source ID."""

    def position(state):
        point = coordinates(state)
        return (
            {"latitude": point[0], "longitude": point[1], "accuracy": point[2]}
            if point
            else None
        )

    selected = runtime.config[CONF_MEMBERS][member.id][CONF_TRACKERS]
    person_state = runtime.states.get(member.id)
    active = member.active_source_entity
    return {
        "source_selection_reason": member.source_selection_reason,
        "person_entity": member.person_entity,
        "person_state": person_state.state if person_state else None,
        "person_updated_at": (
            person_state.last_updated.isoformat() if person_state else None
        ),
        "person_position": position(person_state),
        "active_source": (
            active if admin or active in selected else "other" if active else None
        ),
        "selected_trackers": [
            {
                "entity_id": tracker_id,
                "label": location_source_label(runtime, tracker_id, registry),
                "state": state.state if state else None,
                "updated_at": state.last_updated.isoformat() if state else None,
                "position": position(state),
                "active": tracker_id == active,
            }
            for tracker_id in selected
            for state in [runtime.states.get(tracker_id)]
        ],
    }


def allowed_picture(value):
    """Expose HA portraits and Life360's user-image endpoint only."""
    if not isinstance(value, str) or any(
        ord(char) < 32 or char == "\\" for char in value
    ):
        return None
    if value.startswith(("/api/image/serve/", "/local/")):
        return value
    try:
        url = urlsplit(value)
    except ValueError:
        return None
    decoded_path = unquote(url.path)
    if (
        any(part in (".", "..") for part in decoded_path.split("/"))
        or "%2e" in decoded_path.lower()
    ):
        return None
    life360_image = (
        url.netloc == "www.life360.com" and decoded_path.startswith("/img/user_images/")
    ) or (
        url.netloc == "life360-images-pub.life360.com"
        and decoded_path.endswith((".jpeg", ".jpg", ".png", ".webp"))
    )
    if url.scheme == "https" and life360_image and not url.fragment:
        return value
    return None


def provider_alerts(hass, runtime):
    """Allowlisted status for the account holder, without provider details."""
    alerts = []
    registry = er.async_get(hass)
    selected = selected_entities(runtime.config)
    for provider in connected_providers(runtime.config):
        controls = getattr(runtime, "provider_controls", None)
        if controls is not None and controls.paused(provider.id):
            alerts.append({"name": provider.display_name, "state": "paused"})
            continue
        client = runtime.managed_trackers.get(provider.id)
        if client is None:
            continue
        health = client.health_snapshot()
        state = health.state
        if (
            state == "connected"
            and health.available_trackers > 0
            and not any(
                provider.owns_entity(registry, entity_id) for entity_id in selected
            )
        ):
            alerts.append({"name": provider.display_name, "state": "selection_needed"})
            continue
        if state not in ("connected", "not_loaded"):
            alerts.append({"name": provider.display_name, "state": state})
    return alerts


def snapshot(
    runtime,
    alerts=(),
    registry=None,
    admin=False,
    request_service_available=True,
    hass=None,
):
    """Explicit public projection. Never serialize the state cache or config."""
    household = runtime.household
    members = []
    for member in household.members:
        location = member.location
        place = runtime.states.get(member.place)
        person_state = runtime.states.get(member.id)
        picture = (
            picture_url(runtime.config[CONF_MEMBERS][member.id].get("picture_id"))
            if member.id.startswith("device_tracker.")
            else None
        )
        if picture is None:
            picture = (
                allowed_picture(person_state.attributes.get("entity_picture"))
                if person_state
                else None
            )
        if picture is None:
            for tracker_id in runtime.config[CONF_MEMBERS][member.id][CONF_TRACKERS]:
                tracker_state = runtime.states.get(tracker_id)
                picture = (
                    allowed_picture(tracker_state.attributes.get("entity_picture"))
                    if tracker_state
                    else None
                )
                if picture:
                    break
        members.append(
            {
                "id": member.id,
                "name": member.display_name,
                "picture": picture,
                "kind": member.kind,
                "presence": member.presence,
                "primary_home": member.primary_home,
                "place": place.name if place else None,
                "reported_address": reported_address(member, runtime),
                "reported_city": reported_city(member, runtime),
                "focusable": member.focusable,
                "map_visible": runtime.config[CONF_MEMBERS][member.id].get(
                    CONF_SHOW_ON_MAP, True
                ),
                "location": {
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                    "accuracy": location.accuracy,
                    "origin": location.origin,
                    "evidence": proof(location.evidence, runtime, registry),
                }
                if location and member.focusable
                else None,
                "battery": member.battery.value,
                "battery_status": {
                    "value": member.battery_status.value,
                    "reported_at": member.battery_status.evidence.reported_at.isoformat()
                    if member.battery_status.evidence.reported_at
                    else None,
                }
                if member.battery_status
                else None,
                "charging": member.charging.value,
                "speed": {"value": member.speed.value, "unit": member.speed.unit},
                "driving": {
                    "value": member.driving.value,
                    "status": member.driving_status,
                },
                "issues": list(member.issues),
                "diagnostics": member_diagnostics(member, runtime, registry, admin),
                "arrival": member_arrival(member, runtime, registry),
                "activity": runtime.activity.project(
                    member.id,
                    lambda source: location_source_label(runtime, source, registry),
                )
                if getattr(runtime, "activity", None)
                else None,
                "selection_refresh": getattr(
                    runtime, "selection_refresh_results", {}
                ).get(member.id),
                "location_request": request_status(
                    runtime,
                    member,
                    registry=registry,
                    service_available=request_service_available,
                    notify_available=bool(
                        hass is not None
                        and registry is not None
                        and member.location
                        and available_notification_entity(
                            hass,
                            registry,
                            member.location.evidence.source_entity,
                        )
                    ),
                ),
            }
        )
    from .family_refresh import family_status

    return {
        "family_refresh": family_status(hass, runtime, registry),
        "schema_version": 1,
        "city_lookup_enabled": bool(runtime.config.get("city_lookup_enabled")),
        "members": members,
        "counts": household.counts,
        "focus_ids": household.focus_ids,
        "provider_alerts": list(alerts),
    }


@websocket_api.websocket_command({vol.Required("type"): "homecircle/snapshot"})
@callback
def websocket_snapshot(hass, connection, msg):
    """Fail closed unless every configured input is readable by this HA user.

    Per-input authorization prevents leaking supporting sensor or residence data
    through derived fields. A view's hidden-member setting is not authorization.
    """
    entries = hass.config_entries.async_entries(DOMAIN)
    runtime = next((getattr(entry, "runtime_data", None) for entry in entries), None)
    if runtime is None or runtime.household is None:
        connection.send_error(msg["id"], "not_ready", "HomeCircle is not loaded.")
        return
    user = connection.user
    if (
        user is None
        or not user.is_active
        or not all(
            user.permissions.check_entity(entity, POLICY_READ)
            for entity in selected_entities(runtime.config)
        )
    ):
        connection.send_error(
            msg["id"], "unauthorized", "Household access is not allowed."
        )
        return
    lookup = getattr(runtime, "city_lookup", None)
    if lookup:
        lookup.schedule(runtime)
    connection.send_result(
        msg["id"],
        snapshot(
            runtime,
            provider_alerts(hass, runtime) if user.is_admin else (),
            er.async_get(hass),
            user.is_admin,
            hass.services.has_service("notify", "send_message"),
            hass,
        ),
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homecircle/refresh_location",
        vol.Required("member_id"): str,
    }
)
@websocket_api.async_response
async def websocket_refresh_location(hass, connection, msg):
    """Authorize all household inputs before any tracker or provider operation."""
    from .selection_refresh import async_refresh_selected

    entry = next(iter(hass.config_entries.async_entries(DOMAIN)), None)
    runtime = getattr(entry, "runtime_data", None)
    if runtime is None or runtime.household is None:
        connection.send_error(msg["id"], "not_ready", "HomeCircle is not loaded.")
        return
    user = connection.user
    if (
        user is None
        or not user.is_active
        or not all(
            user.permissions.check_entity(entity, POLICY_READ)
            for entity in selected_entities(runtime.config)
        )
    ):
        connection.send_error(
            msg["id"], "unauthorized", "Household access is not allowed."
        )
        return
    member = next(
        (item for item in runtime.household.members if item.id == msg["member_id"]),
        None,
    )
    if member is None:
        connection.send_error(msg["id"], "not_found", "Selected member is unavailable.")
        return
    from homeassistant.util import dt as dt_util

    checked_at = dt_util.utcnow().isoformat()
    runtime.selection_refresh_results[member.id] = {
        "status": "checking",
        "checked_at": checked_at,
        "trigger": "card_selection",
    }
    try:
        result = await async_refresh_selected(
            hass, runtime, member, user, entry.entry_id
        )
    except Exception:
        # Provider errors and account details never cross the household API.
        result = {"status": "unavailable"}
    runtime.selection_refresh_results[member.id] = {
        **result,
        "checked_at": checked_at,
        "trigger": "card_selection",
    }
    if getattr(runtime, "activity", None) is not None and result["status"] in {
        "requested",
        "checked",
        "send_failed",
    }:
        runtime.activity.append(
            member.id, "refresh", result["status"], dt_util.utcnow()
        )
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({vol.Required("type"): "homecircle/refresh_family"})
@websocket_api.async_response
async def websocket_refresh_family(hass, connection, msg):
    """Explicit family operation; household read access is required first."""
    from .family_refresh import async_refresh_family

    entry = next(iter(hass.config_entries.async_entries(DOMAIN)), None)
    runtime = getattr(entry, "runtime_data", None)
    if runtime is None or runtime.household is None:
        connection.send_error(msg["id"], "not_ready", "HomeCircle is not loaded.")
        return
    user = connection.user
    if (
        user is None
        or not user.is_active
        or not all(
            user.permissions.check_entity(entity, POLICY_READ)
            for entity in selected_entities(runtime.config)
        )
    ):
        connection.send_error(
            msg["id"], "unauthorized", "Household access is not allowed."
        )
        return
    try:
        result = await async_refresh_family(hass, runtime, user)
    except Exception:
        result = {"status": "unavailable"}
    connection.send_result(msg["id"], result)
