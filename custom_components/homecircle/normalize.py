"""Pure, provider-independent normalization of current HA state snapshots.

No I/O, provider attribute heuristics, history, or HA tracker priority emulation.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Any

from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.core import State
from homeassistant.util import dt as dt_util

from .const import (
    CONF_MEMBERS,
    CONF_PEOPLE,
    CONF_PLACES,
    CONF_PRIMARY_HOME,
    CONF_RESIDENCES,
    CONF_TRACKERS,
)

STALE_AFTER_SECONDS = 300
UNKNOWN_STATES = {"unknown", "unavailable"}


@dataclass(frozen=True)
class Evidence:
    source_entity: str | None
    observed_at: datetime | None
    reported_at: datetime | None = None
    report_entity: str | None = None
    freshness: str = "unknown"
    report_status: str = "not_configured"


@dataclass(frozen=True)
class Location:
    latitude: float
    longitude: float
    accuracy: float | None
    origin: str
    evidence: Evidence


@dataclass(frozen=True)
class OptionalValue:
    value: float | bool | None
    evidence: Evidence
    unit: str | None = None


@dataclass(frozen=True)
class Member:
    id: str
    display_name: str
    kind: str
    person_entity: str
    source_entity: str
    active_source_entity: str | None
    presence: str
    presence_evidence: Evidence
    residence: str | None
    place: str | None
    primary_home: bool
    location: Location | None
    driving: OptionalValue
    driving_status: str
    battery: OptionalValue
    charging: OptionalValue
    speed: OptionalValue
    issues: tuple[str, ...]

    @property
    def focusable(self) -> bool:
        return (
            self.presence != "unavailable"
            and self.location is not None
            and not {
                "tracker_presence_conflict",
                "person_tracker_location_conflict",
            }.intersection(self.issues)
        )


@dataclass(frozen=True)
class Household:
    members: tuple[Member, ...]
    counts: dict[str, int]
    primary_home_ids: tuple[str, ...]
    focus_ids: dict[str, tuple[str, ...]]


def available(state: State | None) -> bool:
    return state is not None and state.state not in UNKNOWN_STATES


def number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if isfinite(result) else None


def coordinates(state: State | None) -> tuple[float, float, float | None] | None:
    if not available(state):
        return None
    lat = number(state.attributes.get(ATTR_LATITUDE))
    lon = number(state.attributes.get(ATTR_LONGITUDE))
    if lat is None or lon is None or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        return None
    accuracy = number(state.attributes.get("gps_accuracy"))
    if accuracy is not None and accuracy < 0:
        accuracy = None
    return lat, lon, accuracy


def evidence(
    source: State | None,
    report: State | None,
    now: datetime,
    report_id: str | None = None,
) -> Evidence:
    base = dict(
        source_entity=source.entity_id if source else None,
        observed_at=source.last_updated if source else None,
        report_entity=report_id,
    )
    if report_id is None:
        return Evidence(**base)
    if not available(source) or not available(report):
        return Evidence(**base, report_status="unavailable")
    parsed = dt_util.parse_datetime(report.state)
    if parsed is None or parsed.tzinfo is None:
        return Evidence(**base, report_status="invalid")
    parsed = dt_util.as_utc(parsed)
    age = (now - parsed).total_seconds()
    if age < -60:
        return Evidence(**base, report_status="future")
    return Evidence(
        **base,
        reported_at=parsed,
        report_status="explicit_sensor",
        freshness="fresh" if age <= STALE_AFTER_SECONDS else "stale",
    )


def optional_value(states, entity_id, now, kind, report_id=None) -> OptionalValue:
    state = states.get(entity_id)
    proof = evidence(state, states.get(report_id), now, report_id)
    value = None
    unit = None
    if available(state):
        if kind == "boolean":
            value = {"on": True, "off": False}.get(state.state)
        else:
            unit = state.attributes.get("unit_of_measurement")
            parsed = number(state.state)
            if (
                kind == "battery"
                and unit == "%"
                and parsed is not None
                and 0 <= parsed <= 100
            ):
                value = parsed
            elif (
                kind == "speed"
                and unit in {"m/s", "km/h", "mph"}
                and parsed is not None
                and parsed >= 0
            ):
                value = parsed
            if value is None:
                unit = None
    return OptionalValue(value, proof, unit)


def membership(
    person_state: State, selected: list[str], states, zone_names
) -> tuple[list[str], list[str]]:
    """Resolve IDs first; legacy names only if globally unique in HA's zone catalog."""
    issues = []
    raw = person_state.attributes.get("in_zones")
    if isinstance(raw, (list, tuple)) and all(isinstance(item, str) for item in raw):
        matches = [item for item in selected if item in raw]
        if raw:
            return matches, issues
    if person_state.state == "home":
        return (["zone.home"] if "zone.home" in selected else []), [
            "legacy_home_membership"
        ]
    if person_state.state == "not_home":
        return [], issues
    matches = [key for key, name in zone_names.items() if name == person_state.state]
    if len(matches) == 1 and matches[0] in selected:
        return matches, ["legacy_zone_name"]
    return [], ["ambiguous_zone_name" if len(matches) > 1 else "unresolved_place"]


def normalize_member(
    person_id, member_config, config, states, zone_names, now
) -> Member:
    person_state = states.get(person_id)
    selected_trackers = member_config[CONF_TRACKERS]
    supporting = member_config.get("supporting", {})
    issues = []
    active = person_state.attributes.get("source") if person_state else None
    if not isinstance(active, str) or not active.startswith("device_tracker."):
        active = None
    source = states.get(active) if active in selected_trackers else None
    driving = optional_value(
        states,
        supporting.get("driving"),
        now,
        "boolean",
        supporting.get("driving_reported_at"),
    )
    battery = optional_value(states, supporting.get("battery"), now, "battery")
    charging = optional_value(states, supporting.get("charging"), now, "boolean")
    speed = optional_value(states, supporting.get("speed"), now, "speed")
    driving_status = "unknown"
    if driving.value is not None:
        driving_status = {
            "fresh": "current",
            "stale": "last_reported",
            "unknown": "unverified",
        }[driving.evidence.freshness]
    residence = place = None
    primary_home = False
    location = None
    presence = "unavailable"
    if available(person_state):
        residences = [config[CONF_PRIMARY_HOME], *member_config[CONF_RESIDENCES]]
        selected_zones = list(dict.fromkeys([*residences, *config[CONF_PLACES]]))
        matched, zone_issues = membership(
            person_state, selected_zones, states, zone_names
        )
        issues.extend(zone_issues)
        valid = [item for item in matched if available(states.get(item))]
        residence = next((item for item in residences if item in valid), None)
        primary_home = config[CONF_PRIMARY_HOME] in valid
        place = residence or next(iter(valid), None)
        presence = "home" if residence else "away"
        if not residence and any(
            item in residences for item in matched if item not in valid
        ):
            presence = "unavailable"
            issues.append("residence_zone_unavailable")
        elif driving.value is True and driving_status == "current":
            presence = "driving"

        point = coordinates(person_state)
        location_source = person_state
        origin = "ha_person"
        # HA can borrow Home coordinates for a locationless legacy tracker.
        # Only inspect explicitly selected sources; do not silently widen selection.
        if active in selected_trackers:
            if not available(source):
                point = None
                issues.append("active_source_unavailable")
            elif coordinates(source) is None:
                point = None
                issues.append("active_source_locationless")
            elif point is not None and source.attributes.get("source_type") == "gps":
                if point[:2] == coordinates(source)[:2]:
                    origin = "active_gps"
                    location_source = source
                else:
                    issues.append("person_tracker_location_conflict")
        elif point is not None:
            issues.append("location_source_unverified")
        if point is None:
            candidates = [
                states.get(item)
                for item in selected_trackers
                if available(states.get(item))
                and states[item].attributes.get("source_type") == "gps"
                and coordinates(states[item]) is not None
            ]
            # An available HA active GPS source is authoritative among selected sources.
            candidate = (
                source
                if source in candidates
                else (candidates[0] if len(candidates) == 1 else None)
            )
            if candidate is not None:
                point = coordinates(candidate)
                location_source = candidate
                origin = "supplemental_gps"
                if candidate.state != person_state.state or (
                    isinstance(candidate.attributes.get("in_zones"), (list, tuple))
                    and isinstance(
                        person_state.attributes.get("in_zones"), (list, tuple)
                    )
                    and all(
                        isinstance(item, str)
                        for item in candidate.attributes["in_zones"]
                    )
                    and all(
                        isinstance(item, str)
                        for item in person_state.attributes["in_zones"]
                    )
                    and set(candidate.attributes["in_zones"])
                    != set(person_state.attributes["in_zones"])
                ):
                    issues.append("tracker_presence_conflict")
            elif len(candidates) > 1:
                issues.append("ambiguous_gps_sources")
        if point is not None and presence != "unavailable":
            report_id = supporting.get("location_reported_at")
            if supporting.get("location_report_source") != location_source.entity_id:
                if report_id:
                    issues.append("location_report_source_mismatch")
                report_id = None
            proof = evidence(location_source, states.get(report_id), now, report_id)
            location = Location(*point, origin=origin, evidence=proof)
    else:
        issues.append("person_unavailable")
    return Member(
        id=person_id,
        display_name=person_state.name if person_state else person_id,
        kind="person",
        person_entity=person_id,
        source_entity=person_id,
        active_source_entity=active,
        presence=presence,
        presence_evidence=evidence(person_state, None, now),
        residence=residence,
        place=place,
        primary_home=primary_home,
        location=location,
        driving=driving,
        driving_status=driving_status,
        battery=battery,
        charging=charging,
        speed=speed,
        issues=tuple(issues),
    )


def normalize_household(
    config: Mapping[str, Any],
    states: Mapping[str, State | None],
    now: datetime,
    zone_names: Mapping[str, str] | None = None,
) -> Household:
    """Make counts and focus subsets from the same normalized records."""
    if now.tzinfo is None:
        raise ValueError("Normalization requires an aware timestamp")
    names = (
        zone_names
        if zone_names is not None
        else {
            key: value.name
            for key, value in states.items()
            if key.startswith("zone.") and value is not None
        }
    )
    members = tuple(
        normalize_member(item, config[CONF_MEMBERS][item], config, states, names, now)
        for item in config[CONF_PEOPLE]
    )
    categories = ("home", "away", "driving", "unavailable")
    counts = {
        category: sum(item.presence == category for item in members)
        for category in categories
    }
    primary_ids = tuple(
        item.id for item in members if item.presence == "home" and item.primary_home
    )
    focus = {
        category: tuple(
            item.id
            for item in members
            if item.presence == category
            and item.focusable
            and (category != "home" or item.primary_home)
        )
        for category in categories
    }
    focus["overview"] = tuple(item.id for item in members if item.focusable)
    focus["all_residences"] = tuple(
        item.id for item in members if item.presence == "home" and item.focusable
    )
    return Household(members, counts, primary_ids, focus)
