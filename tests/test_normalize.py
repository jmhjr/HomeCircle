"""Behavioral contract using exclusively fictional entities and coordinates."""

from copy import deepcopy
from datetime import datetime, timedelta, UTC

import pytest
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.core import State

from custom_components.homecircle.normalize import membership, normalize_household

NOW = datetime(2026, 1, 1, 12, tzinfo=UTC)
PERSON = "person.example_member"
SECOND = "person.example_second"
GPS = "device_tracker.example_phone"
OTHER_GPS = "device_tracker.example_other"
ROUTER = "device_tracker.example_router"
RESIDENCE = "zone.example_residence"
WORK = "zone.example_work"


def state(entity_id, value, **attributes):
    return State(entity_id, value, attributes, last_updated=NOW)


def gps(entity_id=GPS, value="home", zones=None, coords=(0.0, 0.0)):
    return state(
        entity_id,
        value,
        source_type="gps",
        in_zones=zones or ["zone.home"],
        **{ATTR_LATITUDE: coords[0], ATTR_LONGITUDE: coords[1]},
    )


@pytest.fixture
def snapshot():
    config = {
        "people": [PERSON, SECOND],
        "primary_home": "zone.home",
        "places": [WORK],
        "members": {
            PERSON: {"trackers": [GPS], "additional_residences": [RESIDENCE]},
            SECOND: {"trackers": [ROUTER], "additional_residences": []},
        },
    }
    states = {
        PERSON: state(
            PERSON,
            "home",
            source=GPS,
            in_zones=["zone.home"],
            **{ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0},
        ),
        SECOND: state(SECOND, "home", source=ROUTER, in_zones=["zone.home"]),
        GPS: gps(),
        ROUTER: state(ROUTER, "home", source_type="router", in_zones=["zone.home"]),
        "zone.home": state("zone.home", "0", friendly_name="Home"),
        RESIDENCE: state(RESIDENCE, "0", friendly_name="Example Residence"),
        WORK: state(WORK, "0", friendly_name="Example Work"),
    }
    return config, states


def member(snapshot, now=NOW):
    return normalize_household(*snapshot, now).members[0]


def test_locationless_home_counts_but_cannot_focus(snapshot):
    result = normalize_household(*snapshot, NOW)
    assert result.counts == {"home": 2, "away": 0, "driving": 0, "unavailable": 0}
    assert result.primary_home_ids == (PERSON, SECOND)
    assert result.focus_ids["home"] == (PERSON,)
    assert result.members[1].location is None
    assert result.members[0].location.latitude == 0.0
    assert result.members[0].location.longitude == 0.0
    assert result.members[0].location.evidence.freshness == "unknown"


def test_residence_counts_home_but_house_focus_excludes_it(snapshot):
    config, states = snapshot
    states[PERSON] = state(
        PERSON,
        "Example Residence",
        source=GPS,
        in_zones=[RESIDENCE],
        **{ATTR_LATITUDE: 1.0, ATTR_LONGITUDE: 0.0},
    )
    states[GPS] = gps(value="Example Residence", zones=[RESIDENCE], coords=(1.0, 0.0))
    result = normalize_household(config, states, NOW)
    assert result.counts["home"] == 2
    assert result.members[0].residence == RESIDENCE
    assert not result.members[0].primary_home
    assert result.focus_ids["home"] == ()
    assert result.primary_home_ids == (SECOND,)
    assert result.focus_ids["all_residences"] == (PERSON,)
    assert result.focus_ids["overview"] == (PERSON,)
    config["members"][PERSON]["additional_residences"] = []
    assert member(snapshot).presence == "away"


def test_recent_gps_well_inside_new_zone_counts_as_home_while_ha_is_behind():
    tracker = state(
        GPS,
        "not_home",
        source_type="gps",
        in_zones=[],
        **{ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0},
        gps_accuracy=15,
        last_seen=NOW,
    )
    zone = state(
        RESIDENCE,
        "0",
        **{ATTR_LATITUDE: 0.0001, ATTR_LONGITUDE: 0.0},
        radius=100,
    )
    states = {GPS: tracker, RESIDENCE: zone}
    expected = ([RESIDENCE], ["gps_inside_zone_ha_pending"])
    assert membership(tracker, [RESIDENCE], states, {}, tracker, NOW) == expected

    stale = state(
        GPS,
        "not_home",
        source_type="gps",
        in_zones=[],
        **{ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0},
        gps_accuracy=15,
        last_seen=NOW - timedelta(minutes=16),
    )
    assert membership(stale, [RESIDENCE], {GPS: stale, RESIDENCE: zone}, {}, stale, NOW) == ([], [])
    small_zone = state(
        RESIDENCE,
        "0",
        radius=20,
        **{ATTR_LATITUDE: 0.0001, ATTR_LONGITUDE: 0.0},
    )
    assert membership(tracker, [RESIDENCE], {GPS: tracker, RESIDENCE: small_zone}, {}, tracker, NOW) == ([], [])


def test_tracker_only_member_at_new_residence_counts_home_and_remains_focusable(snapshot):
    config, states = snapshot
    config["people"].append(GPS)
    config["members"][GPS] = {
        "trackers": [GPS],
        "additional_residences": [RESIDENCE],
        "kind": "person",
    }
    states[GPS] = state(
        GPS,
        "not_home",
        source_type="gps",
        in_zones=[],
        **{ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0},
        gps_accuracy=15,
        last_seen=NOW,
    )
    states[RESIDENCE] = state(
        RESIDENCE,
        "0",
        friendly_name="Example Residence",
        **{ATTR_LATITUDE: 0.0001, ATTR_LONGITUDE: 0.0},
        radius=100,
    )
    result = normalize_household(config, states, NOW)
    added = result.members[-1]
    assert added.presence == "home"
    assert added.residence == RESIDENCE
    assert added.focusable
    assert "gps_inside_zone_ha_pending" in added.issues
    assert "tracker_presence_conflict" not in added.issues
    assert result.counts["home"] == 3
    assert GPS not in result.focus_ids["home"]
    assert GPS in result.focus_ids["all_residences"]


def test_ordinary_place_and_overlap_precedence(snapshot):
    _, states = snapshot
    states[PERSON] = state(PERSON, "Example Work", in_zones=[WORK])
    assert member(snapshot).presence == "away"
    assert member(snapshot).place == WORK
    states[PERSON] = state(
        PERSON, "Example Residence", in_zones=[WORK, RESIDENCE, "zone.home"]
    )
    current = member(snapshot)
    assert current.presence == "home"
    assert current.residence == "zone.home"
    assert current.place == "zone.home"
    assert current.primary_home


@pytest.mark.parametrize("value", ["unknown", "unavailable", None])
def test_unavailable_person_never_rescued_by_gps_or_driving(snapshot, value):
    config, states = snapshot
    states[PERSON] = state(PERSON, value) if value else None
    config["members"][PERSON]["supporting"] = {
        "driving": "binary_sensor.example_driving",
        "driving_reported_at": "sensor.example_driving_report",
    }
    states["binary_sensor.example_driving"] = state(
        "binary_sensor.example_driving", "on"
    )
    states["sensor.example_driving_report"] = state(
        "sensor.example_driving_report", NOW.isoformat()
    )
    current = member(snapshot)
    assert current.presence == "unavailable"
    assert current.location is None
    assert not current.focusable


@pytest.mark.parametrize(
    "coords",
    [
        (None, 0),
        (0, None),
        (float("nan"), 0),
        (0, float("inf")),
        (91, 0),
        (-91, 0),
        (0, 181),
        (0, -181),
        (False, 0),
        ("bad", 0),
    ],
)
def test_invalid_coordinates_stay_null_without_losing_presence(snapshot, coords):
    _, states = snapshot
    states[GPS] = gps(coords=coords)
    states[PERSON] = state(
        PERSON,
        "home",
        source=GPS,
        **{ATTR_LATITUDE: coords[0], ATTR_LONGITUDE: coords[1]},
    )
    current = member(snapshot)
    assert current.presence == "home"
    assert current.location is None
    assert not current.focusable


def test_negative_accuracy_does_not_invalidate_valid_position(snapshot):
    _, states = snapshot
    states[PERSON] = state(
        PERSON,
        "home",
        source=GPS,
        gps_accuracy=-1,
        **{ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0},
    )
    assert member(snapshot).location.accuracy is None


def test_legacy_synthesized_home_coordinates_are_not_reported_gps(snapshot):
    config, states = snapshot
    config["members"][PERSON]["trackers"] = [ROUTER]
    states[PERSON] = state(
        PERSON,
        "home",
        source=ROUTER,
        in_zones=["zone.home"],
        **{ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0},
    )
    current = member(snapshot)
    assert current.presence == "home"
    assert current.location is None
    assert "active_source_locationless" in current.issues


def test_supplemental_gps_keeps_person_authority_and_exposes_conflict(snapshot):
    config, states = snapshot
    config["members"][PERSON]["trackers"] = [ROUTER, GPS]
    states[PERSON] = state(PERSON, "home", source=ROUTER, in_zones=["zone.home"])
    states[GPS] = gps(value="not_home", zones=[WORK], coords=(2.0, 0.0))
    current = member(snapshot)
    assert current.presence == "home"
    assert current.location.origin == "supplemental_gps"
    assert current.location.evidence.source_entity == GPS
    assert "tracker_presence_conflict" in current.issues
    assert not current.focusable
    assert normalize_household(*snapshot, NOW).focus_ids["home"] == ()


def test_borrowed_home_coordinates_do_not_hide_selected_phone_conflict(snapshot):
    config, states = snapshot
    states[PERSON] = state(
        PERSON,
        "home",
        source=ROUTER,
        in_zones=["zone.home"],
        **{ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0},
    )
    states[GPS] = gps(value="not_home", zones=[WORK], coords=(2.0, 0.0))
    current = member(snapshot)
    assert current.presence == "home"
    assert current.active_source_entity == ROUTER
    assert "tracker_presence_conflict" in current.issues
    assert not current.focusable
    assert normalize_household(config, states, NOW).focus_ids["home"] == ()

    states[GPS] = gps(value="home", coords=(0.0, 0.0))
    assert "tracker_presence_conflict" not in member(snapshot).issues


def test_ambiguous_fallback_does_not_guess_tracker_priority(snapshot):
    config, states = snapshot
    config["members"][PERSON]["trackers"] = [ROUTER, GPS, OTHER_GPS]
    states[PERSON] = state(PERSON, "home", source=ROUTER)
    states[OTHER_GPS] = gps(OTHER_GPS, coords=(1.0, 0.0))
    assert member(snapshot).location is None
    assert "ambiguous_gps_sources" in member(snapshot).issues


def test_location_report_timestamp_binding_and_source_switch(snapshot):
    config, states = snapshot
    config["members"][PERSON]["supporting"] = {
        "location_reported_at": "sensor.example_report",
        "location_report_source": GPS,
    }
    states["sensor.example_report"] = state(
        "sensor.example_report", (NOW - timedelta(seconds=30)).isoformat()
    )
    before = member(snapshot)
    assert before.location.evidence.freshness == "fresh"
    assert before.location.evidence.reported_at == NOW - timedelta(seconds=30)
    assert before.location.evidence.observed_at == NOW
    assert before.presence_evidence.freshness == "unknown"
    config["members"][PERSON]["trackers"].append(OTHER_GPS)
    states[OTHER_GPS] = gps(OTHER_GPS)
    states[PERSON] = state(
        PERSON, "home", source=OTHER_GPS, **{ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0}
    )
    after = member(snapshot)
    assert after.active_source_entity == OTHER_GPS
    assert after.location.evidence.freshness == "unknown"
    assert after.location.evidence.reported_at is None
    assert "location_report_source_mismatch" in after.issues


@pytest.mark.parametrize(
    ("stamp", "status", "freshness"),
    [
        ("not-a-date", "invalid", "unknown"),
        ("2026-01-01T12:00:00", "invalid", "unknown"),
        ((NOW + timedelta(minutes=3)).isoformat(), "future", "unknown"),
        ((NOW - timedelta(minutes=6)).isoformat(), "explicit_sensor", "stale"),
        ("unavailable", "unavailable", "unknown"),
    ],
)
def test_timestamp_quality_is_not_ha_observation_time(
    snapshot, stamp, status, freshness
):
    config, states = snapshot
    config["members"][PERSON]["supporting"] = {
        "location_reported_at": "sensor.example_report",
        "location_report_source": GPS,
    }
    states["sensor.example_report"] = state("sensor.example_report", stamp)
    proof = member(snapshot).location.evidence
    assert proof.report_status == status
    assert proof.freshness == freshness


@pytest.mark.parametrize(
    ("seconds", "presence", "status"),
    [
        (0, "driving", "current"),
        (301, "home", "last_reported"),
        (None, "home", "unverified"),
    ],
)
def test_driving_evidence_precedence_and_aging(snapshot, seconds, presence, status):
    config, states = snapshot
    config["members"][PERSON]["supporting"] = {
        "driving": "binary_sensor.example_driving"
    }
    states["binary_sensor.example_driving"] = state(
        "binary_sensor.example_driving", "on"
    )
    if seconds is not None:
        config["members"][PERSON]["supporting"]["driving_reported_at"] = (
            "sensor.example_driving_report"
        )
        states["sensor.example_driving_report"] = state(
            "sensor.example_driving_report",
            (NOW - timedelta(seconds=seconds)).isoformat(),
        )
    current = member(snapshot)
    assert current.presence == presence
    assert current.driving_status == status
    assert current.residence == "zone.home"
    if seconds == 0:
        assert normalize_household(*snapshot, NOW).counts["home"] == 1
        assert member(snapshot, NOW + timedelta(seconds=301)).presence == "home"


@pytest.mark.parametrize(
    ("report_age", "presence", "status"),
    [
        (0, "driving", "current"),
        (301, "away", "last_reported"),
        (None, "away", "unverified"),
    ],
)
def test_selected_tracker_driving_flag_uses_its_report_time(
    snapshot, report_age, presence, status
):
    _, states = snapshot
    states[PERSON] = state(
        PERSON,
        "not_home",
        source=GPS,
        in_zones=[],
        **{ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0},
    )
    attributes = {
        "source_type": "gps",
        "driving": True,
        ATTR_LATITUDE: 0.0,
        ATTR_LONGITUDE: 0.0,
    }
    if report_age is not None:
        attributes["last_seen"] = (NOW - timedelta(seconds=report_age)).isoformat()
    states[GPS] = state(GPS, "not_home", **attributes)
    current = member(snapshot)
    assert current.presence == presence
    assert current.driving.value is True
    assert current.driving_status == status
    assert current.driving.evidence.source_entity == GPS


def test_selected_tracker_and_person_reporting_driving(snapshot):
    """A provider driving state is an away state, not an unknown place."""
    _, states = snapshot
    states[PERSON] = state(
        PERSON,
        "driving",
        source=GPS,
        in_zones=[],
        **{ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0},
    )
    states[GPS] = state(
        GPS,
        "driving",
        source_type="gps",
        driving=True,
        last_seen=NOW,
        **{ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0},
    )
    current = member(snapshot)
    assert current.presence == "driving"
    assert current.driving_status == "current"
    assert current.driving.evidence.reported_at == NOW
    assert "unresolved_place" not in current.issues


def test_explicit_driving_sensor_overrides_tracker_flag(snapshot):
    config, states = snapshot
    config["members"][PERSON]["supporting"] = {
        "driving": "binary_sensor.example_driving",
        "driving_reported_at": "sensor.example_driving_report",
    }
    states["binary_sensor.example_driving"] = state(
        "binary_sensor.example_driving", "off"
    )
    states["sensor.example_driving_report"] = state(
        "sensor.example_driving_report", NOW.isoformat()
    )
    states[GPS] = state(
        GPS,
        "home",
        source_type="gps",
        driving=True,
        last_seen=NOW.isoformat(),
        **{ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0},
    )
    current = member(snapshot)
    assert current.presence == "home"
    assert current.driving.value is False
    assert current.driving.evidence.source_entity == "binary_sensor.example_driving"


def test_tracker_false_driving_flag_is_not_overridden_by_speed(snapshot):
    _, states = snapshot
    states[PERSON] = state(
        PERSON,
        "not_home",
        source=GPS,
        in_zones=[],
        **{ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0},
    )
    states[GPS] = state(
        GPS,
        "not_home",
        source_type="gps",
        driving=False,
        speed=35,
        last_seen=NOW.isoformat(),
        **{ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0},
    )
    current = member(snapshot)
    assert current.presence == "away"
    assert current.driving.value is False
    assert current.driving_status == "current"


def test_optional_battery_zero_units_and_missing_data(snapshot):
    config, states = snapshot
    current = member(snapshot)
    assert (
        current.battery.value is current.charging.value is current.speed.value is None
    )
    config["members"][PERSON]["supporting"] = {
        "battery": "sensor.example_battery",
        "charging": "binary_sensor.example_charging",
        "speed": "sensor.example_speed",
    }
    states["sensor.example_battery"] = state(
        "sensor.example_battery", "0", unit_of_measurement="%"
    )
    states["binary_sensor.example_charging"] = state(
        "binary_sensor.example_charging", "off"
    )
    states["sensor.example_speed"] = state(
        "sensor.example_speed", "60", unit_of_measurement="mph"
    )
    current = member(snapshot)
    assert current.battery.value == 0
    assert current.charging.value is False
    assert current.speed.value == 60
    assert current.speed.unit == "mph"
    assert current.presence == "home"  # Speed is never driving evidence.
    states["sensor.example_battery"] = state(
        "sensor.example_battery", "101", unit_of_measurement="%"
    )
    states["sensor.example_speed"] = state(
        "sensor.example_speed", "60", unit_of_measurement="unknown"
    )
    assert member(snapshot).battery.value is None
    assert member(snapshot).speed.value is None


def test_deleted_residence_and_ambiguous_legacy_zone_are_not_guessed(snapshot):
    config, states = snapshot
    states[PERSON] = state(PERSON, "Example Residence", in_zones=[RESIDENCE])
    states[RESIDENCE] = None
    assert member(snapshot).presence == "unavailable"
    states[RESIDENCE] = state(RESIDENCE, "0", friendly_name="Example Residence")
    states[PERSON] = state(PERSON, "Example Residence", in_zones=[])
    assert member(snapshot).residence == RESIDENCE
    catalog = {
        RESIDENCE: "Example Residence",
        "zone.example_duplicate": "Example Residence",
    }
    ambiguous = normalize_household(config, states, NOW, catalog).members[0]
    assert ambiguous.residence is None
    assert "ambiguous_zone_name" in ambiguous.issues


def test_non_default_primary_home_and_input_immutability(snapshot):
    config, _ = snapshot
    config["primary_home"] = RESIDENCE
    config["members"][PERSON]["additional_residences"] = []
    before = deepcopy(config)
    assert (
        member(snapshot).presence == "away"
    )  # HA Home is not a different selected primary.
    assert config == before


def test_pet_location_threshold_changes_with_residence_without_faking_report(snapshot):
    config, states = snapshot
    cfg = config["members"][PERSON]
    cfg.update(kind="pet", pet_home_minutes=1440, pet_away_minutes=5)
    cfg["supporting"] = {
        "location_reported_at": "sensor.example_report",
        "location_report_source": GPS,
    }
    stamp = NOW - timedelta(hours=22)
    states["sensor.example_report"] = state("sensor.example_report", stamp.isoformat())
    result = member(snapshot)
    assert result.kind == "pet"
    assert result.location.evidence.freshness == "fresh"
    assert result.location.evidence.reported_at == stamp
    assert (
        member(snapshot, NOW + timedelta(hours=3)).location.evidence.freshness
        == "stale"
    )
    states[PERSON] = state(PERSON, "not_home", source=GPS, in_zones=[])
    states[GPS] = state(
        GPS,
        "not_home",
        source_type="gps",
        in_zones=[],
        **{ATTR_LATITUDE: 2.0, ATTR_LONGITUDE: 0.0},
    )
    assert member(snapshot).location.evidence.freshness == "stale"
    cfg["kind"] = "person"
    states[PERSON] = state(PERSON, "home", source=GPS, in_zones=["zone.home"])
    states[GPS] = gps()
    assert member(snapshot).location.evidence.freshness == "stale"
    states.pop("sensor.example_report")
    cfg["kind"] = "pet"
    assert member(snapshot).location.evidence.freshness == "unknown"


def test_tracker_only_pet_counts_and_focuses_without_person(snapshot):
    config, states = snapshot
    pet = "device_tracker.example_pet"
    config["pets"] = [pet]
    config["members"][pet] = {
        "trackers": [pet],
        "additional_residences": [RESIDENCE],
        "kind": "pet",
        "pet_home_minutes": 1440,
        "pet_away_minutes": 5,
    }
    states[pet] = gps(pet, value="Example Residence", zones=[RESIDENCE], coords=(1, 0))
    current = normalize_household(config, states, NOW)
    direct_pet = current.members[-1]
    assert direct_pet.person_entity is None
    assert direct_pet.source_entity == pet
    assert direct_pet.kind == "pet"
    assert direct_pet.residence == RESIDENCE
    assert direct_pet.location.evidence.source_entity == pet
    assert current.counts["home"] == 3
    assert current.primary_home_ids == (PERSON, SECOND)
    assert current.focus_ids["home"] == (PERSON,)
    assert current.focus_ids["all_residences"] == (PERSON, pet)
    assert current.focus_ids["overview"] == (PERSON, pet)

    states[pet] = state(pet, "unavailable")
    unavailable = normalize_household(config, states, NOW)
    assert unavailable.members[-1].presence == "unavailable"
    assert "tracker_unavailable" in unavailable.members[-1].issues
    assert pet not in unavailable.focus_ids["overview"]


def test_per_source_report_times_switch_and_missing_evidence(snapshot):
    config, states = snapshot
    settings = config["members"][PERSON]
    settings["trackers"].append(OTHER_GPS)
    settings["location_reports"] = {
        GPS: "sensor.example_report",
        OTHER_GPS: "sensor.example_other_report",
    }
    states["sensor.example_report"] = state(
        "sensor.example_report", (NOW - timedelta(hours=2)).isoformat()
    )
    states["sensor.example_other_report"] = state(
        "sensor.example_other_report", (NOW - timedelta(seconds=20)).isoformat()
    )
    assert member(snapshot).location.evidence.freshness == "stale"
    states[OTHER_GPS] = gps(OTHER_GPS)
    states[PERSON] = state(
        PERSON, "home", source=OTHER_GPS, **{ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0}
    )
    assert member(snapshot).location.evidence.reported_at == NOW - timedelta(seconds=20)
    assert member(snapshot).location.evidence.freshness == "fresh"
    states.pop("sensor.example_other_report")
    assert member(snapshot).location.evidence.reported_at is None
    assert member(snapshot).location.evidence.freshness == "unknown"


def test_selected_gps_tracker_supplies_battery_and_location_report_time(snapshot):
    _, states = snapshot
    stamp = NOW - timedelta(seconds=45)
    states[GPS] = state(
        GPS,
        "home",
        source_type="gps",
        battery_level=0,
        battery_charging=True,
        last_seen=stamp.isoformat(),
        **{ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0},
    )
    current = member(snapshot)
    assert current.battery.value == 0
    assert current.charging.value is True
    assert current.location.evidence.reported_at == stamp
    assert current.location.evidence.report_status == "tracker_attribute"
    assert current.location.evidence.freshness == "fresh"
    assert (
        member(snapshot, NOW + timedelta(seconds=301)).location.evidence.freshness
        == "stale"
    )


def test_explicit_sensors_override_tracker_attributes(snapshot):
    config, states = snapshot
    states[GPS] = state(
        GPS,
        "home",
        source_type="gps",
        battery_level=85,
        battery_charging=True,
        last_seen=(NOW - timedelta(seconds=20)).isoformat(),
        **{ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0},
    )
    config["members"][PERSON]["supporting"] = {
        "battery": "sensor.example_battery",
        "charging": "binary_sensor.example_charging",
    }
    config["members"][PERSON]["location_reports"] = {GPS: "sensor.example_report"}
    states["sensor.example_battery"] = state(
        "sensor.example_battery", "25", unit_of_measurement="%"
    )
    states["binary_sensor.example_charging"] = state(
        "binary_sensor.example_charging", "off"
    )
    current = member(snapshot)
    assert current.battery.value == 25
    assert current.charging.value is False
    assert current.location.evidence.reported_at is None
    assert current.location.evidence.report_status == "unavailable"


@pytest.mark.parametrize(
    "stamp", ["not a time", "2026-01-01T12:02:00+00:00", "2026-01-01T11:59:00"]
)
def test_invalid_tracker_last_seen_does_not_claim_gps_report(snapshot, stamp):
    _, states = snapshot
    states[GPS] = state(
        GPS,
        "home",
        source_type="gps",
        battery_level=101,
        battery_charging="true",
        last_seen=stamp,
        **{ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0},
    )
    current = member(snapshot)
    assert current.location.evidence.reported_at is None
    assert current.battery.value is None
    assert current.charging.value is None


def test_restart_person_fallback_restores_old_report_as_stale(snapshot):
    """Restart state writes must not turn a retained GPS report into a new fix."""
    config, states = snapshot
    config["members"][PERSON]["trackers"] = [GPS, OTHER_GPS]
    stamp = NOW - timedelta(minutes=20)
    states[GPS] = state(
        GPS,
        "home",
        source_type="gps",
        last_seen=stamp.isoformat(),
        in_zones=["zone.home"],
        **{ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0},
    )
    states[OTHER_GPS] = gps(OTHER_GPS, coords=(0.0, 0.0001))
    before = member(snapshot)
    assert before.location.evidence.source_entity == GPS
    assert before.location.evidence.reported_at == stamp
    assert before.location.evidence.freshness == "stale"

    restart_at = NOW + timedelta(minutes=1)
    states[PERSON] = State(
        PERSON,
        "home",
        {"source": PERSON, "in_zones": ["zone.home"],
         ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0},
        last_updated=restart_at,
    )
    fallback = member(snapshot, restart_at)
    assert fallback.presence == "home"
    assert fallback.focusable
    assert fallback.location.evidence.source_entity == PERSON
    assert fallback.location.evidence.observed_at == restart_at
    assert fallback.location.evidence.reported_at is None
    assert fallback.location.evidence.freshness == "unknown"

    recovered_at = NOW + timedelta(minutes=3)
    states[GPS] = State(
        GPS, "home", dict(states[GPS].attributes), last_updated=recovered_at
    )
    states[PERSON] = State(
        PERSON, "home", {**states[PERSON].attributes, "source": GPS},
        last_updated=recovered_at,
    )
    recovered = normalize_household(config, states, recovered_at)
    current = recovered.members[0]
    assert current.presence == "home"
    assert current.focusable
    assert recovered.counts == {"home": 2, "away": 0, "driving": 0, "unavailable": 0}
    assert current.location.evidence.source_entity == GPS
    assert current.location.evidence.observed_at == recovered_at
    assert current.location.evidence.reported_at == stamp
    assert current.location.evidence.freshness == "stale"




def test_departure_return_flips_follow_person_without_conflicting_map(snapshot):
    """Anonymized state ordering observed around departure and return."""
    config, states = snapshot
    # The phone briefly toggles near the boundary while Person remains authoritative.
    for person_value, phone_value in [
        ("home", "not_home"), ("home", "home"), ("not_home", "not_home"),
        ("not_home", "home"), ("not_home", "not_home"), ("home", "home"),
    ]:
        states[PERSON] = state(PERSON, person_value, source=GPS,
                               in_zones=["zone.home"] if person_value == "home" else [WORK])
        states[GPS] = gps(value=phone_value,
                          zones=["zone.home"] if phone_value == "home" else [WORK],
                          coords=(0.0, 0.0) if phone_value == "home" else (2.0, 0.0))
        current = normalize_household(config, states, NOW).members[0]
        assert current.presence == ("home" if person_value == "home" else "away")
        if person_value == "home" and phone_value == "not_home":
            assert "tracker_presence_conflict" in current.issues
            assert not current.focusable
        if person_value == phone_value:
            assert "tracker_presence_conflict" not in current.issues
