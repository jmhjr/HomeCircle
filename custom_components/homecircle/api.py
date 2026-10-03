"""Authenticated, permission-checked snapshot API; no raw states or history."""

from urllib.parse import unquote, urlsplit

from homeassistant.auth.permissions.const import POLICY_READ
from homeassistant.components import websocket_api
from homeassistant.core import callback
import voluptuous as vol

from .const import CONF_MEMBERS, CONF_TRACKERS, DOMAIN
from .selection import selected_entities


def proof(value):
    return {
        "reported_at": value.reported_at.isoformat() if value.reported_at else None,
        "observed_at": value.observed_at.isoformat() if value.observed_at else None,
        "freshness": value.freshness,
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


def snapshot(runtime):
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
                "location": {
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                    "accuracy": location.accuracy,
                    "origin": location.origin,
                    "evidence": proof(location.evidence),
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
    connection.send_result(msg["id"], snapshot(runtime))
