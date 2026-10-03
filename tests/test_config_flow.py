"""Exercise HA's actual flow manager, selectors, persistence and runtime."""

from copy import deepcopy
from unittest.mock import patch

import pytest
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    SOURCE_USER,
    ConfigEntryState,
)
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er, issue_registry as ir

from custom_components.homecircle.const import DOMAIN
from custom_components.homecircle import frontend
from custom_components.homecircle.selection import tracker_suggestions


async def start(hass, household):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["step_id"] == "household"
    return await hass.config_entries.flow.async_configure(result["flow_id"], household)


async def finish(hass, result, manager=None):
    manager = manager or hass.config_entries.flow
    result = await manager.async_configure(
        result["flow_id"],
        {
            "trackers": ["device_tracker.example_phone"],
            "additional_residences": ["zone.example_residence"],
        },
    )
    result = await manager.async_configure(
        result["flow_id"],
        {
            "trackers": ["device_tracker.example_router"],
        },
    )
    assert result["step_id"] == "confirm"
    return await manager.async_configure(result["flow_id"], {})


async def create(hass, household):
    result = await finish(hass, await start(hass, household))
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    entry = result["result"]
    assert entry.state == ConfigEntryState.LOADED
    return entry


async def test_setup_persistence_sources_and_unload(hass, household):
    entry = await create(hass, household)
    saved = deepcopy(dict(entry.data))
    assert entry.unique_id == DOMAIN
    assert saved["members"]["person.example_member"]["additional_residences"] == [
        "zone.example_residence"
    ]
    assert saved["primary_home"] == "zone.home"
    assert saved["places"] == ["zone.example_work"]
    runtime = entry.runtime_data
    assert not runtime.unavailable
    assert "latitude" not in runtime.states["person.example_second"].attributes
    assert runtime.states["person.example_member"].attributes["latitude"] == 0
    assert "life360" not in hass.config.components
    hass.states.async_set("person.example_second", "not_home")
    await hass.async_block_till_done()
    assert runtime.states["person.example_second"].state == "not_home"
    assert await hass.config_entries.async_unload(entry.entry_id)
    hass.states.async_set("person.example_second", "home")
    await hass.async_block_till_done()
    assert not runtime.states
    assert await hass.config_entries.async_setup(entry.entry_id)
    assert dict(entry.data) == saved
    assert entry.runtime_data is not runtime
    assert entry.runtime_data.states["person.example_second"].state == "home"


async def test_cancel_and_duplicate_flow(hass, household):
    result = await start(hass, household)
    duplicate = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert duplicate["type"] == FlowResultType.ABORT
    hass.config_entries.flow.async_abort(result["flow_id"])
    assert not hass.config_entries.async_entries(DOMAIN)
    entry = await create(hass, household)
    duplicate = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert duplicate["reason"] == "single_instance_allowed"
    saved = deepcopy(dict(entry.data))
    options = await hass.config_entries.options.async_init(entry.entry_id)
    options = await hass.config_entries.options.async_configure(
        options["flow_id"],
        {
            **household,
            "people": ["person.example_second"],
        },
    )
    hass.config_entries.options.async_abort(options["flow_id"])
    assert dict(entry.data) == saved
    assert not entry.options


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("people", [], "no_people"),
        ("people", ["person.example_deleted"], "invalid_entity"),
        ("people", ["person.example_member"] * 2, "duplicate_selection"),
        ("primary_home", "zone.example_deleted", "invalid_entity"),
        ("places", ["zone.home"], "primary_in_places"),
    ],
)
async def test_invalid_household(hass, household, field, value, error):
    result = await start(hass, {**household, field: value})
    assert result["step_id"] == "household"
    assert result["errors"][field] == error
    assert not hass.config_entries.async_entries(DOMAIN)


async def test_invalid_members_and_deleted_during_flow(hass, household):
    result = await start(hass, household)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "trackers": ["device_tracker.example_deleted"],
            "additional_residences": ["zone.home"],
        },
    )
    assert result["errors"] == {
        "trackers": "invalid_entity",
        "additional_residences": "primary_in_residences",
    }
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    hass.states.async_remove("person.example_member")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["step_id"] == "household"
    assert result["errors"] == {"base": "entities_changed"}
    assert not hass.config_entries.async_entries(DOMAIN)


async def test_options_reconfigure_and_listener_replacement(hass, household):
    entry = await create(hass, household)
    resources = hass.data[LOVELACE_DATA].resources
    owned_before = next(
        item for item in resources.async_items() if item["url"].startswith(frontend.URL)
    )
    old_runtime = entry.runtime_data
    manager = hass.config_entries.options
    result = await manager.async_init(entry.entry_id)
    result = await manager.async_configure(
        result["flow_id"],
        {
            **household,
            "people": ["person.example_second"],
            "places": [],
        },
    )
    result = await manager.async_configure(result["flow_id"], {})
    result = await manager.async_configure(result["flow_id"], {})
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    owned_after_options = next(
        item for item in resources.async_items() if item["url"].startswith(frontend.URL)
    )
    assert owned_after_options["id"] == owned_before["id"]
    assert entry.options["members"] == {
        "person.example_second": {
            "trackers": [],
            "additional_residences": [],
            "kind": "person",
            "pet_home_minutes": 1440,
            "pet_away_minutes": 5,
        }
    }
    assert not old_runtime.states
    assert "person.example_member" not in entry.runtime_data.states
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], household
    )
    result = await finish(hass, result)
    await hass.async_block_till_done()
    owned_after_reconfigure = next(
        item for item in resources.async_items() if item["url"].startswith(frontend.URL)
    )
    assert owned_after_reconfigure["id"] == owned_before["id"]
    assert result["reason"] == "reconfigure_successful"
    assert not entry.options
    assert entry.runtime_data.config["people"] == household["people"]


async def test_unchanged_reconfigure_keeps_owned_resource(hass, household):
    entry = await create(hass, household)
    resources = hass.data[LOVELACE_DATA].resources
    owned_before = next(
        item for item in resources.async_items() if item["url"].startswith(frontend.URL)
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], household
    )
    result = await finish(hass, result)
    await hass.async_block_till_done()
    owned_after = next(
        item for item in resources.async_items() if item["url"].startswith(frontend.URL)
    )
    assert result["reason"] == "reconfigure_successful"
    assert owned_after["id"] == owned_before["id"]
    assert (
        len(
            [
                item
                for item in resources.async_items()
                if item["url"].startswith(frontend.URL)
            ]
        )
        == 1
    )


async def test_missing_unavailable_recovery_and_repair(hass, household):
    entry = await create(hass, household)
    runtime = entry.runtime_data
    hass.states.async_remove("device_tracker.example_phone")
    hass.states.async_set("person.example_second", "unavailable")
    await hass.async_block_till_done()
    assert runtime.missing == {"device_tracker.example_phone"}
    assert runtime.unavailable == {
        "device_tracker.example_phone",
        "person.example_second",
    }
    issues = ir.async_get(hass)
    issue_id = f"missing_entities_{entry.entry_id}"
    assert issues.async_get_issue(DOMAIN, issue_id)
    hass.states.async_set("device_tracker.example_phone", "not_home")
    await hass.async_block_till_done()
    assert not runtime.missing
    assert issues.async_get_issue(DOMAIN, issue_id) is None
    await hass.config_entries.async_unload(entry.entry_id)
    assert issues.async_get_issue(DOMAIN, issue_id) is None


async def test_registry_disabled_and_rename_require_reselection(hass, household):
    registry = er.async_get(hass)
    hass.states.async_remove("device_tracker.example_router")
    entity = registry.async_get_or_create(
        "device_tracker", "demo", "example_router", suggested_object_id="example_router"
    )
    hass.states.async_set(entity.entity_id, "home")
    entry = await create(hass, household)
    registry.async_update_entity(
        entity.entity_id, disabled_by=er.RegistryEntryDisabler.USER
    )
    await hass.async_block_till_done()
    assert entity.entity_id in entry.runtime_data.missing
    registry.async_update_entity(entity.entity_id, disabled_by=None)
    hass.states.async_remove(entity.entity_id)
    registry.async_update_entity(
        entity.entity_id, new_entity_id="device_tracker.example_renamed"
    )
    await hass.async_block_till_done()
    assert entity.entity_id in entry.runtime_data.missing
    assert entry.data["members"]["person.example_second"]["trackers"] == [
        entity.entity_id
    ]


async def test_discovery_does_not_guess_from_names(hass, household):
    # Association helper and active source are separate, neither guesses from names.
    with patch(
        "custom_components.homecircle.selection.entities_in_person",
        return_value=["device_tracker.example_router"],
    ):
        assert tracker_suggestions(hass, "person.example_member") == (
            ["device_tracker.example_router"],
            "device_tracker.example_phone",
        )
    hass.states.async_set("person.example_member", "home")
    assert tracker_suggestions(hass, "person.example_member") == ([], None)


async def test_member_setup_explains_suggestions_without_changing_them(hass, household):
    hass.states.async_set(
        "person.example_member",
        "home",
        {
            "friendly_name": "Example Member",
            "source": "device_tracker.example_phone",
        },
    )
    hass.states.async_set(
        "device_tracker.example_phone", "home", {"friendly_name": "Example Phone"}
    )
    with patch(
        "custom_components.homecircle.selection.entities_in_person",
        return_value=["device_tracker.example_phone"],
    ):
        result = await start(hass, household)
    assert result["step_id"] == "member"
    placeholders = result["description_placeholders"]
    assert {key: placeholders[key] for key in ("person", "number", "total", "active")} == {
        "person": "Example Member", "number": "1", "total": "2", "active": "Example Phone"
    }
    assert "Suggested tracker: **Example Phone**" in placeholders["tracker_guidance"]
    assert "not a measure of update reliability" in placeholders["tracker_guidance"]
    tracker_field = next(
        field for field in result["data_schema"].schema if str(field) == "trackers"
    )
    assert tracker_field.description["suggested_value"] == [
        "device_tracker.example_phone"
    ]


async def test_tracker_guide_prefers_position_over_home_only_presence(hass, household):
    hass.states.async_set(
        "person.example_member", "home", {"source": "device_tracker.example_router"}
    )
    with patch(
        "custom_components.homecircle.selection.entities_in_person",
        return_value=["device_tracker.example_router", "device_tracker.example_phone"],
    ):
        result = await start(hass, household)
    guide = result["description_placeholders"]["tracker_guidance"]
    assert "Suggested tracker: **example phone**" in guide
    assert "Home/Away presence only" in guide
    assert "GPS position available" in guide
    tracker_field = next(
        field for field in result["data_schema"].schema if str(field) == "trackers"
    )
    assert tracker_field.description["suggested_value"] == [
        "device_tracker.example_phone"
    ]


async def test_tracker_guide_does_not_guess_between_equal_sources(hass, household):
    hass.states.async_set("person.example_member", "home")
    with patch(
        "custom_components.homecircle.selection.entities_in_person",
        return_value=["device_tracker.example_phone", "device_tracker.example_router"],
    ):
        hass.states.async_set("device_tracker.example_phone", "home")
        result = await start(hass, household)
    guide = result["description_placeholders"]["tracker_guidance"]
    assert "equally suitable" in guide
    tracker_field = next(
        field for field in result["data_schema"].schema if str(field) == "trackers"
    )
    assert tracker_field.description["suggested_value"] == []


async def test_duplicate_tracker_names_are_distinct_in_hint_and_review(hass, household):
    current = "device_tracker.example_phone"
    stale = "device_tracker.example_phone_old"
    hass.states.async_set(current, "home", {"friendly_name": "Example Phone"})
    hass.states.async_set(stale, "home", {"friendly_name": "Example Phone"})
    hass.states.async_set(
        "person.example_member",
        "home",
        {"friendly_name": "Example Member", "source": current},
    )
    with patch(
        "custom_components.homecircle.selection.entities_in_person",
        return_value=[current],
    ):
        result = await start(hass, household)
    assert result["description_placeholders"]["active"] == (
        "Example Phone (device_tracker.example_phone)"
    )
    tracker_field = next(
        field for field in result["data_schema"].schema if str(field) == "trackers"
    )
    picker = result["data_schema"].schema[tracker_field]
    assert {option["value"]: option["label"] for option in picker.config["options"]}[
        stale
    ] == "Example Phone (device_tracker.example_phone_old)"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"trackers": [stale]}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["step_id"] == "confirm"
    assert (
        "- Trackers: Example Phone (device\\_tracker.example\\_phone\\_old)"
        in result["description_placeholders"]["members"]
    )
    hass.config_entries.flow.async_abort(result["flow_id"])


async def test_final_review_shows_draft_and_cancel_keeps_it_unsaved(hass, household):
    hass.states.async_set(
        "person.example_member", "home", {"friendly_name": "Example *Member*"}
    )
    hass.states.async_set(
        "device_tracker.example_phone", "home", {"friendly_name": "Example Phone"}
    )
    hass.states.async_set(
        "zone.example_residence", "0", {"friendly_name": "Other Home"}
    )
    result = await start(hass, household)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "trackers": ["device_tracker.example_phone"],
            "additional_residences": ["zone.example_residence"],
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"trackers": ["device_tracker.example_router"]}
    )
    assert result["step_id"] == "confirm"
    review = result["description_placeholders"]
    assert review["primary_home"]
    assert review["places"]
    assert "**Example \\*Member\\***" in review["members"]
    assert "- Trackers: Example Phone" in review["members"]
    assert "- Other homes: Other Home" in review["members"]
    assert review["members"].count("- Status sensors: None mapped") == 2
    assert review["members"].count("- Location report times: None mapped") == 2
    hass.config_entries.flow.async_abort(result["flow_id"])
    assert not hass.config_entries.async_entries(DOMAIN)


async def test_supporting_flow_validation_persistence_and_clear(hass, household):
    hass.states.async_set(
        "sensor.example_battery",
        "0",
        {"friendly_name": "Example Battery", "unit_of_measurement": "%"},
    )
    hass.states.async_set(
        "sensor.example_report",
        "2026-01-01T00:00:00+00:00",
        {"friendly_name": "Example Report"},
    )
    result = await start(hass, household)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "trackers": ["device_tracker.example_phone"],
            "configure_sensors": True,
            "configure_reports": True,
        },
    )
    assert result["step_id"] == "supporting"
    assert {str(field) for field in result["data_schema"].schema} == {
        "battery",
        "charging",
        "speed",
        "driving",
        "driving_reported_at",
    }
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"battery": "sensor.example_missing"},
    )
    assert result["errors"]["battery"] == "invalid_entity"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"battery": "sensor.example_battery"},
    )
    assert result["step_id"] == "source_report"
    assert result["description_placeholders"]["number"] == "1"
    assert result["description_placeholders"]["total"] == "2"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["description_placeholders"]["number"] == "2"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"timestamp": "sensor.example_report"}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["step_id"] == "confirm"
    review = result["description_placeholders"]["members"]
    assert "Battery: Example Battery" in review
    assert "Example Report" in review
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    entry = result["result"]
    await hass.async_block_till_done()
    assert entry.runtime_data.household.members[0].battery.value == 0
    assert "sensor.example_battery" in entry.runtime_data.states
    assert entry.data["members"]["person.example_member"]["location_reports"] == {
        "device_tracker.example_phone": "sensor.example_report"
    }
    options = hass.config_entries.options
    result = await options.async_init(entry.entry_id)
    result = await options.async_configure(result["flow_id"], household)
    result = await options.async_configure(
        result["flow_id"],
        {
            "trackers": ["device_tracker.example_phone"],
            "configure_sensors": True,
        },
    )
    result = await options.async_configure(result["flow_id"], {})
    result = await options.async_configure(result["flow_id"], {})
    await options.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()
    assert entry.runtime_data.household.members[0].battery.value is None
    assert "sensor.example_battery" not in entry.runtime_data.states
    assert entry.options["members"]["person.example_member"]["location_reports"] == {
        "device_tracker.example_phone": "sensor.example_report"
    }


async def test_runtime_report_aging_source_changes_and_unload(hass, household, freezer):
    from datetime import timedelta
    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    now = dt_util.utcnow()
    hass.states.async_set("binary_sensor.example_driving", "on")
    hass.states.async_set("sensor.example_driving_report", now.isoformat())
    result = await start(hass, household)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "trackers": ["device_tracker.example_phone"],
            "configure_sensors": True,
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "driving": "binary_sensor.example_driving",
            "driving_reported_at": "sensor.example_driving_report",
        },
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    entry = result["result"]
    await hass.async_block_till_done()
    runtime = entry.runtime_data
    assert runtime.household.members[0].presence == "driving"
    later = now + timedelta(minutes=6)
    freezer.move_to(later)
    async_fire_time_changed(hass, later)
    await hass.async_block_till_done()
    assert runtime.household.members[0].presence == "home"
    assert runtime.household.members[0].driving_status == "last_reported"
    hass.states.async_set("person.example_member", "unavailable")
    await hass.async_block_till_done()
    assert runtime.household.counts["unavailable"] == 1
    assert not runtime.household.members[0].focusable
    await hass.config_entries.async_unload(entry.entry_id)
    freezer.move_to(later + timedelta(minutes=1))
    async_fire_time_changed(hass, later + timedelta(minutes=1))
    hass.states.async_set("binary_sensor.example_driving", "off")
    await hass.async_block_till_done()
    assert runtime.household is None
    assert runtime.states == {}


async def test_pet_thresholds_persist_in_options(hass, household):
    entry = await create(hass, household)
    manager = hass.config_entries.options
    flow = await manager.async_init(entry.entry_id)
    flow = await manager.async_configure(
        flow["flow_id"], {**household, "people": ["person.example_member"]}
    )
    assert flow["step_id"] == "member"
    assert "pet_home_minutes" not in {
        str(field) for field in flow["data_schema"].schema
    }
    flow = await manager.async_configure(
        flow["flow_id"],
        {
            "trackers": ["device_tracker.example_phone"],
            "kind": "pet",
        },
    )
    assert flow["step_id"] == "pet_freshness"
    flow = await manager.async_configure(
        flow["flow_id"], {"pet_home_minutes": 720, "pet_away_minutes": 10}
    )
    assert flow["step_id"] == "confirm"
    assert (
        "Pet timing: home 12 hours, away 10 min"
        in flow["description_placeholders"]["members"]
    )
    flow = await manager.async_configure(flow["flow_id"], {})
    await hass.async_block_till_done()
    assert flow["type"] == FlowResultType.CREATE_ENTRY
    member = entry.options["members"]["person.example_member"]
    assert member["kind"] == "pet"
    assert member["pet_home_minutes"] == 720
    assert member["pet_away_minutes"] == 10
    assert entry.runtime_data.config["members"]["person.example_member"] == member

    flow = await manager.async_init(entry.entry_id)
    flow = await manager.async_configure(
        flow["flow_id"], {**household, "people": ["person.example_member"]}
    )
    flow = await manager.async_configure(
        flow["flow_id"],
        {
            "trackers": ["device_tracker.example_phone"],
            "kind": "pet",
            "configure_sensors": True,
        },
    )
    assert flow["step_id"] == "pet_freshness"
    suggested = {
        str(field): field.description.get("suggested_value")
        for field in flow["data_schema"].schema
    }
    assert suggested == {"pet_home_minutes": 720, "pet_away_minutes": 10}
    flow = await manager.async_configure(flow["flow_id"], {})
    assert flow["step_id"] == "supporting"
    manager.async_abort(flow["flow_id"])
    assert entry.options["members"]["person.example_member"] == member


async def test_per_source_flow_migrates_preserves_and_clears(hass, household):
    from custom_components.homecircle.selection import selected_entities

    hass.states.async_set("sensor.example_report", "2026-01-01T00:00:00+00:00")
    entry = await create(hass, household)
    original = deepcopy(dict(entry.data))
    # Use the actual fixture's first member, preserving the original household.
    person = household["people"][0]
    original["members"][person]["supporting"] = {
        "location_report_source": "device_tracker.example_phone",
        "location_reported_at": "sensor.example_report",
    }
    hass.config_entries.async_update_entry(entry, data=original)
    options = hass.config_entries.options
    result = await options.async_init(entry.entry_id)
    result = await options.async_configure(result["flow_id"], household)
    result = await options.async_configure(
        result["flow_id"],
        {"trackers": ["device_tracker.example_phone"]},
    )
    assert result["step_id"] == "source_report"
    result = await options.async_configure(result["flow_id"], {})
    result = await options.async_configure(
        result["flow_id"], {"timestamp": "sensor.example_missing"}
    )
    assert result["errors"]["timestamp"] == "invalid_entity"
    result = await options.async_configure(
        result["flow_id"], {"timestamp": "sensor.example_report"}
    )
    result = await options.async_configure(
        result["flow_id"], {"trackers": ["device_tracker.example_router"]}
    )
    await options.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()
    saved = entry.options["members"][person]
    assert saved["location_reports"] == {
        "device_tracker.example_phone": "sensor.example_report"
    }
    assert "location_reported_at" not in saved.get("supporting", {})
    assert "sensor.example_report" in selected_entities(entry.options)
    assert "sensor.example_report" in entry.runtime_data.states
    assert await hass.config_entries.async_reload(entry.entry_id)
    assert (
        entry.runtime_data.config["members"][person]["location_reports"]
        == saved["location_reports"]
    )
    # Removing a tracker requires explicitly clearing its prior report mapping.
    result = await options.async_init(entry.entry_id)
    result = await options.async_configure(result["flow_id"], household)
    result = await options.async_configure(result["flow_id"], {"trackers": []})
    assert result["step_id"] == "source_report"
    result = await options.async_configure(result["flow_id"], {})
    result = await options.async_configure(
        result["flow_id"], {"timestamp": "sensor.example_report"}
    )
    assert result["errors"]["timestamp"] == "invalid_report_source"
    result = await options.async_configure(result["flow_id"], {})
    result = await options.async_configure(
        result["flow_id"], {"trackers": ["device_tracker.example_router"]}
    )
    await options.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()
    assert entry.options["members"][person]["location_reports"] == {}
    assert "sensor.example_report" not in selected_entities(entry.options)
