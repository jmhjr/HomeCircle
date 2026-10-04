"""Authenticated, permission-checked snapshot API; no raw states or history."""

from urllib.parse import unquote, urlsplit

from homeassistant.auth.permissions.const import POLICY_READ
from homeassistant.components import websocket_api
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
import voluptuous as vol

from .const import CONF_MEMBERS, CONF_SHOW_ON_MAP, CONF_TRACKERS, DOMAIN
from .selection import selected_entities
from .tracker_providers import connected_providers


def location_source_label(runtime, source_entity):
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
        return f"Tracker: {name}"
    if source_entity.startswith("person."):
        return f"HA Person: {name}"
    return name


def proof(value, runtime):
    return {
        "reported_at": value.reported_at.isoformat() if value.reported_at else None,
        "observed_at": value.observed_at.isoformat() if value.observed_at else None,
        "freshness": value.freshness,
        "source_label": location_source_label(runtime, value.source_entity),
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


def snapshot(runtime, alerts=()):
    """Explicit public projection. Never serialize the state cache or config."""
    household = runtime.household
    members = []
    for member in household.members:
        location = member.location
        place = runtime.states.get(member.place)
        person_state = runtime.states.get(member.id)
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
                "focusable": member.focusable,
                "map_visible": runtime.config[CONF_MEMBERS][member.id].get(
                    CONF_SHOW_ON_MAP, True
                ),
                "location": {
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                    "accuracy": location.accuracy,
                    "origin": location.origin,
                    "evidence": proof(location.evidence, runtime),
                }
                if location and member.focusable
                else None,
                "battery": member.battery.value,
                "charging": member.charging.value,
                "speed": {"value": member.speed.value, "unit": member.speed.unit},
                "driving": {
                    "value": member.driving.value,
                    "status": member.driving_status,
                },
                "issues": list(member.issues),
            }
        )
    return {
        "schema_version": 1,
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
    connection.send_result(
        msg["id"],
        snapshot(runtime, provider_alerts(hass, runtime) if user.is_admin else ()),
    )
