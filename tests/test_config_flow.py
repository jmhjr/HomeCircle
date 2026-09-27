"""Exercise HA's actual flow manager, selectors, persistence and runtime."""

from copy import deepcopy
from unittest.mock import patch

import pytest
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    SOURCE_USER,
    ConfigEntryState,
)
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er, issue_registry as ir

from custom_components.homecircle.const import DOMAIN
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
    assert result["reason"] == "reconfigure_successful"
    assert not entry.options
    assert entry.runtime_data.config["people"] == household["people"]


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


async def test_supporting_flow_validation_persistence_and_clear(hass, household):
    hass.states.async_set("sensor.example_battery", "0", {"unit_of_measurement": "%"})
    hass.states.async_set("sensor.example_report", "2026-01-01T00:00:00+00:00")
    result = await start(hass, household)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "trackers": ["device_tracker.example_phone"],
            "configure_sensors": True,
        },
    )
    assert result["step_id"] == "supporting"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "location_reported_at": "sensor.example_report",
        },
    )
    assert result["errors"]["base"] == "report_source_required"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "battery": "sensor.example_battery",
            "location_reported_at": "sensor.example_report",
            "location_report_source": "device_tracker.example_phone",
        },
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    entry = result["result"]
    await hass.async_block_till_done()
    assert entry.runtime_data.household.members[0].battery.value == 0
    assert "sensor.example_battery" in entry.runtime_data.states
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
    flow = await manager.async_configure(
        flow["flow_id"],
        {
            "trackers": ["device_tracker.example_phone"],
            "kind": "pet",
            "pet_home_minutes": 720,
            "pet_away_minutes": 10,
        },
    )
    flow = await manager.async_configure(flow["flow_id"], {})
    await hass.async_block_till_done()
    assert flow["type"] == FlowResultType.CREATE_ENTRY
    member = entry.options["members"]["person.example_member"]
    assert member["kind"] == "pet"
    assert member["pet_home_minutes"] == 720
    assert member["pet_away_minutes"] == 10
    assert entry.runtime_data.config["members"]["person.example_member"] == member
