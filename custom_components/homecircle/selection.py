"""Read-only discovery and selection validation. No provider-specific access."""

from collections.abc import Mapping
from typing import Any

from homeassistant.components.person import entities_in_person
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_MEMBERS,
    CONF_PEOPLE,
    CONF_TRACKER_PEOPLE,
    CONF_PETS,
    CONF_PLACES,
    CONF_PRIMARY_HOME,
    CONF_RESIDENCES,
    CONF_TRACKERS,
    CONF_DISPLAY_NAME,
    CONF_SHOW_ON_MAP,
    CONF_AUTO_REQUEST_LOCATION,
)
from .location_requests import available_notification_entity
from .tracker_providers import connection_requested


@callback
def selectable(hass: HomeAssistant, entity_id: str, domain: str) -> bool:
    """Allow loaded or registered sources, including temporarily unavailable ones."""
    if not isinstance(entity_id, str) or not entity_id.startswith(f"{domain}."):
        return False
    registered = er.async_get(hass).async_get(entity_id)
    if registered is not None:
        return not registered.disabled
    return hass.states.get(entity_id) is not None


@callback
def tracker_suggestions(
    hass: HomeAssistant, entity_id: str
) -> tuple[list[str], str | None]:
    """Distinguish configured associations from the currently active source."""
    linked, active = person_tracker_references(hass, entity_id)
    associated = [item for item in linked if selectable(hass, item, "device_tracker")]
    if not selectable(hass, active, "device_tracker"):
        active = None
    return associated, active


def person_tracker_references(
    hass: HomeAssistant, entity_id: str
) -> tuple[list[str], str | None]:
    """Read exact HA Person links, including disabled or unavailable trackers."""
    linked = list(entities_in_person(hass, entity_id))
    state = hass.states.get(entity_id)
    active = state.attributes.get("source") if state else None
    return linked, active if isinstance(active, str) else None


def selected_entities(config: Mapping[str, Any]) -> set[str]:
    """Return only explicitly selected entities, never inferred sources."""
    result = {
        config[CONF_PRIMARY_HOME],
        *config[CONF_PLACES],
        *config.get(CONF_PEOPLE, []),
        *config.get(CONF_TRACKER_PEOPLE, []),
        *config.get(CONF_PETS, []),
    }
    for member in config[CONF_MEMBERS].values():
        result.update(member[CONF_TRACKERS])
        result.update(member[CONF_RESIDENCES])
        result.update(member.get("supporting", {}).values())
        result.update(member.get("location_reports", {}).values())
        result.update(member.get("location_reports", {}))
    return result


def trackers_assigned_elsewhere(config: Mapping[str, Any], member_id: str) -> set[str]:
    """Find explicit tracker assignments belonging to another household member."""
    assigned = {
        tracker
        for tracker in (
            *config.get(CONF_TRACKER_PEOPLE, []),
            *config.get(CONF_PETS, []),
        )
        if tracker != member_id
    }
    for other_id, member in config.get(CONF_MEMBERS, {}).items():
        if other_id != member_id:
            assigned.update(member.get(CONF_TRACKERS, []))
    return assigned


@callback
def household_errors(hass: HomeAssistant, values: Mapping[str, Any]) -> dict[str, str]:
    """Validate household selections again at submission time."""
    errors = {}
    people = values.get(CONF_PEOPLE, [])
    tracker_people = values.get(CONF_TRACKER_PEOPLE, [])
    pets = values.get(CONF_PETS, [])
    places = values.get(CONF_PLACES, [])
    primary = values.get(CONF_PRIMARY_HOME)
    if (
        not people
        and not tracker_people
        and not pets
        and not connection_requested(values)
    ):
        errors["base"] = "no_members"
    if len(people) != len(set(people)):
        errors[CONF_PEOPLE] = "duplicate_selection"
    elif any(not selectable(hass, item, "person") for item in people):
        errors[CONF_PEOPLE] = "invalid_entity"
    if len(tracker_people) != len(set(tracker_people)) or set(tracker_people) & set(
        pets
    ):
        errors[CONF_TRACKER_PEOPLE] = "duplicate_selection"
    elif any(not selectable(hass, item, "device_tracker") for item in tracker_people):
        errors[CONF_TRACKER_PEOPLE] = "invalid_entity"
    if len(pets) != len(set(pets)):
        errors[CONF_PETS] = "duplicate_selection"
    elif any(not selectable(hass, item, "device_tracker") for item in pets):
        errors[CONF_PETS] = "invalid_entity"
    if people and (tracker_people or pets) and CONF_PEOPLE not in errors:
        configured_trackers = {
            tracker for person in people for tracker in entities_in_person(hass, person)
        }
        active_trackers = {
            state.attributes["source"]
            for person in people
            if (state := hass.states.get(person)) is not None
            and isinstance(state.attributes.get("source"), str)
        }
        for field, trackers in (
            (CONF_TRACKER_PEOPLE, tracker_people),
            (CONF_PETS, pets),
        ):
            if field not in errors and (
                configured_trackers | active_trackers
            ).intersection(trackers):
                errors[field] = "tracker_already_in_person"
    if not selectable(hass, primary, "zone"):
        errors[CONF_PRIMARY_HOME] = "invalid_entity"
    if len(places) != len(set(places)):
        errors[CONF_PLACES] = "duplicate_selection"
    elif any(not selectable(hass, item, "zone") for item in places):
        errors[CONF_PLACES] = "invalid_entity"
    elif primary in places:
        errors[CONF_PLACES] = "primary_in_places"
    return errors


@callback
def member_errors(
    hass: HomeAssistant,
    values: Mapping[str, Any],
    primary: str,
    person_id: str | None = None,
) -> dict[str, str]:
    """An ordinary place may be a residence for one member only."""
    errors = {}
    if values.get("kind", "person") not in ("person", "pet"):
        errors["kind"] = "invalid_kind"
    if CONF_DISPLAY_NAME in values:
        name = values[CONF_DISPLAY_NAME]
        if (
            not isinstance(name, str)
            or not name.strip()
            or len(name.strip()) > 60
            or any(ord(char) < 32 for char in name)
        ):
            errors[CONF_DISPLAY_NAME] = "invalid_display_name"
    if CONF_SHOW_ON_MAP in values and not isinstance(values[CONF_SHOW_ON_MAP], bool):
        errors[CONF_SHOW_ON_MAP] = "invalid_map_visibility"
    if CONF_AUTO_REQUEST_LOCATION in values and not isinstance(
        values[CONF_AUTO_REQUEST_LOCATION], bool
    ):
        errors[CONF_AUTO_REQUEST_LOCATION] = "invalid_auto_request_location"
    elif values.get(CONF_AUTO_REQUEST_LOCATION) is True and (
        not hass.services.has_service("notify", "send_message")
        or not any(
            available_notification_entity(hass, er.async_get(hass), tracker_id)
            for tracker_id in values.get(CONF_TRACKERS, [])
        )
    ):
        errors[CONF_AUTO_REQUEST_LOCATION] = "mobile_app_notify_required"
    if person_id and person_id.startswith("device_tracker."):
        if values.get(CONF_TRACKERS) != [person_id]:
            errors["base"] = "invalid_tracker_source"
    for key, default in (("pet_home_minutes", 1440), ("pet_away_minutes", 5)):
        value = values.get(key, default)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not 1 <= value <= 10080
        ):
            errors[key] = "invalid_freshness"

    for key, domain in ((CONF_TRACKERS, "device_tracker"), (CONF_RESIDENCES, "zone")):
        items = values.get(key, [])
        if len(items) != len(set(items)):
            errors[key] = "duplicate_selection"
        elif any(not selectable(hass, item, domain) for item in items):
            errors[key] = "invalid_entity"
    if primary in values.get(CONF_RESIDENCES, []):
        errors[CONF_RESIDENCES] = "primary_in_residences"
    if values.get("supporting"):
        errors.update(
            supporting_errors(
                hass, values["supporting"], person_id, values.get(CONF_TRACKERS, [])
            )
        )
    for source, sensor in values.get("location_reports", {}).items():
        if source not in [person_id, *values.get(CONF_TRACKERS, [])]:
            errors["base"] = "invalid_report_source"
        elif not selectable(hass, sensor, "sensor"):
            errors["base"] = "invalid_entity"
    return errors


SUPPORTING_DOMAINS = {
    "battery": "sensor",
    "charging": "binary_sensor",
    "speed": "sensor",
    "driving": "binary_sensor",
    "driving_reported_at": "sensor",
    "location_reported_at": "sensor",
}


@callback
def supporting_errors(hass, values, person_id, trackers):
    """Mappings are explicit; timestamps must be bound to their actual source."""
    errors = {}
    for key, domain in SUPPORTING_DOMAINS.items():
        if key in values and not selectable(hass, values[key], domain):
            errors[key] = "invalid_entity"
    if bool(values.get("location_reported_at")) != bool(
        values.get("location_report_source")
    ):
        errors["base"] = "report_source_required"
    if values.get("location_report_source") and values[
        "location_report_source"
    ] not in [person_id, *trackers]:
        errors["location_report_source"] = "invalid_report_source"
    if values.get("driving_reported_at") and not values.get("driving"):
        errors["driving"] = "driving_required"
    return errors
