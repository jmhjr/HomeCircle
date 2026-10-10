"""Exercise HA's actual flow manager, selectors, persistence and runtime."""

from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    SOURCE_REAUTH,
    SOURCE_USER,
    ConfigEntryState,
)
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from life360 import Unauthorized
from pytest_homeassistant_custom_component.common import MockConfigEntry

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
    return await configure_empty(manager, result)


async def configure_empty(manager, result):
    """Submit an empty form or choose Save at the review menu."""
    user_input = (
        {"next_step_id": "confirm_save"}
        if result["type"] == FlowResultType.MENU
        and result["step_id"] in ("confirm", "confirm_remove")
        else {}
    )
    return await manager.async_configure(result["flow_id"], user_input)


async def create(hass, household):
    result = await finish(hass, await start(hass, household))
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    entry = result["result"]
    assert entry.state == ConfigEntryState.LOADED
    return entry


async def legacy_tracker_entry(hass, tracker, *, kind="pet", reports=None):
    """Load a beta-12 tracker-only household to test upgrade compatibility."""
    data = {
        "people": [],
        "people_trackers": [tracker] if kind == "person" else [],
        "pets": [tracker] if kind == "pet" else [],
        "primary_home": "zone.home",
        "places": [],
        "members": {
            tracker: {
                "trackers": [tracker],
                "additional_residences": [],
                "kind": kind,
                "pet_home_minutes": 1440,
                "pet_away_minutes": 5,
                **({"location_reports": reports} if reports else {}),
            }
        },
    }
    entry = MockConfigEntry(
        domain=DOMAIN, title="HomeCircle", data=data, unique_id=DOMAIN
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_new_pet_person_is_created_and_tracker_linked_on_save(hass):
    """A new pet goes through HA Person before HomeCircle tracker settings."""
    from homeassistant.components.person import entities_in_person
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, "zone", {})
    hass.states.async_set(
        "device_tracker.example_pet", "not_home", {"source_type": "gps"}
    )
    manager = hass.config_entries.flow
    result = await manager.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await manager.async_configure(
        result["flow_id"], {"create_person": True, "primary_home": "zone.home"}
    )
    assert result["step_id"] == "create_person"
    result = await manager.async_configure(result["flow_id"], {"name": "Example Pet"})
    assert result["step_id"] == "household"
    assert "people_trackers" not in [str(key) for key in result["data_schema"].schema]
    person_id = next(
        state.entity_id
        for state in hass.states.async_all("person")
        if state.name == "Example Pet"
    )
    result = await manager.async_configure(
        result["flow_id"], {"people": [person_id], "primary_home": "zone.home"}
    )
    assert result["step_id"] == "assign_tracker"
    result = await manager.async_configure(
        result["flow_id"], {"tracker": "device_tracker.example_pet"}
    )
    assert result["step_id"] == "member"
    result = await manager.async_configure(
        result["flow_id"],
        {"kind": "pet"},
    )
    assert result["step_id"] == "pet_freshness"
    result = await manager.async_configure(result["flow_id"], {})
    assert result["step_id"] == "confirm"
    assert (
        "Will link to this HA Person" in result["description_placeholders"]["members"]
    )
    assert entities_in_person(hass, person_id) == []
    result = await configure_empty(manager, result)
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entities_in_person(hass, person_id) == ["device_tracker.example_pet"]
    assert result["data"]["members"][person_id]["kind"] == "pet"


async def test_saved_tracker_only_pet_can_move_to_person_without_losing_settings(hass):
    from homeassistant.components.person import async_create_person, entities_in_person
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, "zone", {})
    assert await async_setup_component(hass, "person", {"person": []})
    pet = "device_tracker.example_pet"
    hass.states.async_set(pet, "not_home", {"source_type": "gps"})
    entry = await legacy_tracker_entry(hass, pet)
    await async_create_person(hass, "Example Pet")
    person_id = next(
        state.entity_id
        for state in hass.states.async_all("person")
        if state.name == "Example Pet"
    )
    manager = hass.config_entries.options
    result = await start_options(manager, entry, "convert_legacy_member")
    assert result["step_id"] == "convert_legacy_member"
    result = await manager.async_configure(
        result["flow_id"], {"person": person_id, "legacy_tracker": pet}
    )
    assert result["step_id"] == "member"
    result = await manager.async_configure(result["flow_id"], {})
    assert result["step_id"] == "confirm"
    assert entities_in_person(hass, person_id) == []
    await configure_empty(manager, result)
    await hass.async_block_till_done()
    assert pet not in entry.options["pets"]
    assert entry.options["members"][person_id]["kind"] == "pet"
    assert entry.options["members"][person_id]["trackers"] == [pet]
    assert entities_in_person(hass, person_id) == [pet]


async def test_review_back_and_edit_member_preserve_two_member_draft(hass, household):
    manager = hass.config_entries.flow
    result = await start(hass, household)
    result = await manager.async_configure(
        result["flow_id"], {"trackers": ["device_tracker.example_phone"]}
    )
    result = await manager.async_configure(
        result["flow_id"], {"trackers": ["device_tracker.example_router"]}
    )
    assert result["type"] == FlowResultType.MENU
    assert result["menu_options"] == [
        "confirm_back",
        "confirm_edit_member",
        "confirm_save",
    ]

    result = await manager.async_configure(
        result["flow_id"], {"next_step_id": "confirm_back"}
    )
    assert result["step_id"] == "member"
    assert result["description_placeholders"]["number"] == "2"
    result = await manager.async_configure(
        result["flow_id"], {"trackers": ["device_tracker.example_router"]}
    )
    assert result["step_id"] == "confirm"

    result = await manager.async_configure(
        result["flow_id"], {"next_step_id": "confirm_edit_member"}
    )
    assert result["step_id"] == "confirm_edit_member"
    result = await manager.async_configure(
        result["flow_id"], {"member": "person.example_member"}
    )
    assert result["step_id"] == "member"
    assert result["description_placeholders"]["number"] == "1"
    result = await manager.async_configure(
        result["flow_id"], {"trackers": ["device_tracker.example_phone"]}
    )
    assert result["step_id"] == "confirm"
    result = await configure_empty(manager, result)
    assert result["type"] == FlowResultType.CREATE_ENTRY
    members = result["data"]["members"]
    assert members["person.example_member"]["trackers"] == [
        "device_tracker.example_phone"
    ]
    assert members["person.example_second"]["trackers"] == [
        "device_tracker.example_router"
    ]


async def test_create_place_zone_keeps_household_draft(hass, household):
    manager = hass.config_entries.flow
    result = await manager.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await manager.async_configure(
        result["flow_id"], {**household, "create_zone": True}
    )
    assert result["step_id"] == "create_zone"
    result = await manager.async_configure(
        result["flow_id"],
        {
            "name": "Example Office",
            "location": {ATTR_LATITUDE: 0.1, ATTR_LONGITUDE: 0.1, "radius": 100},
            "use": "place",
        },
    )
    assert result["step_id"] == "household"
    assert (
        "Created Example Office" in result["description_placeholders"]["new_zone_hint"]
    )
    zone_id = next(
        state.entity_id
        for state in hass.states.async_all("zone")
        if state.name == "Example Office"
    )
    prefill = {
        str(field): (field.description or {}).get("suggested_value")
        for field in result["data_schema"].schema
    }
    assert prefill["people"] == household["people"]
    assert prefill["places"] == [*household["places"], zone_id]
    result = await manager.async_configure(
        result["flow_id"], {**household, "places": [*household["places"], zone_id]}
    )
    assert result["step_id"] == "member"
    result = await manager.async_configure(
        result["flow_id"], {"trackers": ["device_tracker.example_phone"]}
    )
    result = await manager.async_configure(
        result["flow_id"], {"trackers": ["device_tracker.example_router"]}
    )
    result = await configure_empty(manager, result)
    assert zone_id in result["data"]["places"]


async def test_create_other_home_zone_preserves_member_choices(hass, household):
    manager = hass.config_entries.flow
    result = await start(hass, {**household, "people": ["person.example_member"]})
    result = await manager.async_configure(
        result["flow_id"],
        {"trackers": ["device_tracker.example_phone"], "create_zone": True},
    )
    assert result["step_id"] == "create_zone"
    result = await manager.async_configure(
        result["flow_id"],
        {
            "name": "Example Second Home",
            "location": {ATTR_LATITUDE: 0.2, ATTR_LONGITUDE: 0.2, "radius": 150},
        },
    )
    assert result["step_id"] == "member"
    assert (
        "Created Example Second Home"
        in result["description_placeholders"]["new_zone_hint"]
    )
    zone_id = next(
        state.entity_id
        for state in hass.states.async_all("zone")
        if state.name == "Example Second Home"
    )
    prefill = {
        str(field): (field.description or {}).get("suggested_value")
        for field in result["data_schema"].schema
    }
    assert prefill["trackers"] == ["device_tracker.example_phone"]
    assert prefill["additional_residences"] == [zone_id]
    result = await manager.async_configure(
        result["flow_id"],
        {
            "trackers": ["device_tracker.example_phone"],
            "additional_residences": [zone_id],
        },
    )
    result = await configure_empty(manager, result)
    assert result["data"]["members"]["person.example_member"][
        "additional_residences"
    ] == [zone_id]


async def test_create_primary_zone_rejects_duplicate_name(hass, household):
    manager = hass.config_entries.flow
    result = await manager.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await manager.async_configure(
        result["flow_id"], {**household, "create_zone": True}
    )
    location = {ATTR_LATITUDE: 0.3, ATTR_LONGITUDE: 0.3, "radius": 120}
    result = await manager.async_configure(
        result["flow_id"],
        {
            "name": hass.states.get("zone.home").name,
            "location": location,
            "use": "primary",
        },
    )
    assert result["step_id"] == "create_zone"
    assert result["errors"]["name"] == "zone_already_exists"
    result = await manager.async_configure(
        result["flow_id"],
        {"name": "Example Family Home", "location": location, "use": "primary"},
    )
    assert result["step_id"] == "household"
    zone_id = next(
        state.entity_id
        for state in hass.states.async_all("zone")
        if state.name == "Example Family Home"
    )
    prefill = {
        str(field): (field.description or {}).get("suggested_value")
        for field in result["data_schema"].schema
    }
    assert prefill["primary_home"] == zone_id
    assert prefill["people"] == household["people"]
    manager.async_abort(result["flow_id"])


async def start_options(manager, entry, next_step="household"):
    """Choose an explicit task from the options menu."""
    result = await manager.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    return await manager.async_configure(result["flow_id"], {"next_step_id": next_step})


async def test_options_battery_task_shows_only_member_then_sensors(hass, household):
    entry = await create(hass, household)
    original_second = deepcopy(entry.data["members"]["person.example_second"])
    hass.states.async_set("sensor.example_battery", "78", {"unit_of_measurement": "%"})
    hass.states.async_set("sensor.example_backup", "2026-10-04T00:00:00+00:00")
    hass.states.async_set(
        "sensor.example_humidity",
        "55",
        {"unit_of_measurement": "%", "device_class": "humidity"},
    )
    manager = hass.config_entries.options
    result = await start_options(manager, entry, "tracker_member_choice")
    assert result["step_id"] == "tracker_member_choice"
    assert {str(field) for field in result["data_schema"].schema} == {
        "member",
        "setting",
    }
    result = await manager.async_configure(
        result["flow_id"], {"member": "person.example_member", "setting": "sensors"}
    )
    assert result["step_id"] == "supporting"
    battery_field = next(
        value
        for key, value in result["data_schema"].schema.items()
        if str(key) == "battery"
    )
    assert battery_field.config["include_entities"] == ["sensor.example_battery"]
    result = await manager.async_configure(
        result["flow_id"], {"battery": "sensor.example_battery"}
    )
    assert result["step_id"] == "confirm"
    await configure_empty(manager, result)
    await hass.async_block_till_done()
    assert (
        entry.options["members"]["person.example_member"]["supporting"]["battery"]
        == "sensor.example_battery"
    )
    assert entry.options["members"]["person.example_second"] == original_second


async def test_options_person_settings_open_selected_members_details(hass, household):
    entry = await create(hass, household)
    manager = hass.config_entries.options
    result = await start_options(manager, entry, "tracker_member_choice")
    result = await manager.async_configure(
        result["flow_id"], {"member": "person.example_second", "setting": "details"}
    )
    assert result["step_id"] == "member"
    manager.async_abort(result["flow_id"])


async def test_options_remove_tracker_is_scoped_to_selected_person(hass, household):
    entry = await create(hass, household)
    manager = hass.config_entries.options
    result = await start_options(manager, entry, "tracker_member_choice")
    result = await manager.async_configure(
        result["flow_id"], {"member": "person.example_member", "setting": "remove"}
    )
    assert result["step_id"] == "remove_tracker_choice"
    tracker_field = next(
        value
        for key, value in result["data_schema"].schema.items()
        if str(key) == "remove_tracker"
    )
    assert [option["value"] for option in tracker_field.config["options"]] == [
        "device_tracker.example_phone"
    ]
    with pytest.raises(InvalidData):
        await manager.async_configure(
            result["flow_id"], {"remove_tracker": "device_tracker.example_router"}
        )
    result = await manager.async_configure(
        result["flow_id"], {"remove_tracker": "device_tracker.example_phone"}
    )
    assert result["step_id"] == "confirm_remove"
    assert result["menu_options"] == ["confirm_back_remove", "confirm_save"]
    result = await manager.async_configure(
        result["flow_id"], {"next_step_id": "confirm_back_remove"}
    )
    assert result["step_id"] == "remove_tracker_choice"
    result = await manager.async_configure(
        result["flow_id"], {"remove_tracker": "device_tracker.example_phone"}
    )
    assert result["step_id"] == "confirm_remove"
    await configure_empty(manager, result)
    await hass.async_block_till_done()
    assert entry.options["members"]["person.example_member"]["trackers"] == []
    assert entry.options["members"]["person.example_second"]["trackers"] == [
        "device_tracker.example_router"
    ]


async def test_options_add_tracker_task_uses_short_form(hass, household):
    from homeassistant.components.person import async_create_person, entities_in_person
    from homeassistant.setup import async_setup_component

    entry = await create(hass, household)
    tracker = "device_tracker.example_bike"
    hass.states.async_set(tracker, "not_home", {"source_type": "gps"})
    assert await async_setup_component(hass, "person", {"person": []})
    await async_create_person(hass, "Example Bike")
    person_id = next(
        state.entity_id
        for state in hass.states.async_all("person")
        if state.name == "Example Bike"
    )
    manager = hass.config_entries.options
    result = await start_options(manager, entry, "add_tracker_choice")
    assert result["step_id"] == "add_tracker_choice"
    assert {str(field) for field in result["data_schema"].schema} == {
        "person",
        "create_person",
    }
    result = await manager.async_configure(result["flow_id"], {"person": person_id})
    assert result["step_id"] == "add_tracker_assign"
    assert {str(field) for field in result["data_schema"].schema} == {
        "add_tracker",
        "add_tracker_kind",
    }
    result = await manager.async_configure(
        result["flow_id"], {"add_tracker": tracker, "add_tracker_kind": "person"}
    )
    assert result["step_id"] == "member"
    result = await configure_empty(manager, result)
    assert result["step_id"] == "confirm"
    assert "Example Bike" in result["description_placeholders"]["members"]
    assert entities_in_person(hass, person_id) == []
    await configure_empty(manager, result)
    await hass.async_block_till_done()
    assert person_id in entry.options["people"]
    assert entry.options["members"][person_id]["trackers"] == [tracker]
    assert entities_in_person(hass, person_id) == [tracker]


async def test_options_create_pet_person_before_assigning_tracker(hass, household):
    from homeassistant.components.person import entities_in_person
    from homeassistant.setup import async_setup_component

    entry = await create(hass, household)
    tracker = "device_tracker.example_pet_collar"
    hass.states.async_set(tracker, "not_home", {"source_type": "gps"})
    assert await async_setup_component(hass, "person", {"person": []})
    manager = hass.config_entries.options
    result = await start_options(manager, entry, "add_tracker_choice")
    result = await manager.async_configure(result["flow_id"], {"create_person": True})
    assert result["step_id"] == "create_person"
    result = await manager.async_configure(result["flow_id"], {"name": "Example Pet"})
    assert result["step_id"] == "add_tracker_choice"
    person_id = next(
        state.entity_id
        for state in hass.states.async_all("person")
        if state.name == "Example Pet"
    )
    result = await manager.async_configure(result["flow_id"], {"person": person_id})
    assert result["step_id"] == "add_tracker_assign"
    result = await manager.async_configure(
        result["flow_id"], {"add_tracker": tracker, "add_tracker_kind": "pet"}
    )
    assert result["step_id"] == "member"
    result = await configure_empty(manager, result)
    assert result["step_id"] == "confirm"
    assert entities_in_person(hass, person_id) == []
    await configure_empty(manager, result)
    await hass.async_block_till_done()
    assert entry.options["members"][person_id]["kind"] == "pet"
    assert entities_in_person(hass, person_id) == [tracker]


async def test_create_person_with_existing_yaml_person(hass, household):
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(
        hass, "person", {"person": [{"id": "existing", "name": "Existing"}]}
    )
    entry = await create(hass, household)
    manager = hass.config_entries.options
    result = await start_options(manager, entry, "add_tracker_choice")
    result = await manager.async_configure(result["flow_id"], {"create_person": True})
    assert result["step_id"] == "create_person"
    result = await manager.async_configure(result["flow_id"], {"name": "Example Pet"})
    assert result["step_id"] == "add_tracker_choice"


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
    options = await start_options(hass.config_entries.options, entry)
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
    ("field", "value", "error_field", "error"),
    [
        ("people", [], "base", "no_members"),
        ("people", ["person.example_deleted"], "people", "invalid_entity"),
        ("people", ["person.example_member"] * 2, "people", "duplicate_selection"),
        ("primary_home", "zone.example_deleted", "primary_home", "invalid_entity"),
        ("places", ["zone.home"], "places", "primary_in_places"),
    ],
)
async def test_invalid_household(hass, household, field, value, error_field, error):
    result = await start(hass, {**household, field: value})
    assert result["step_id"] == "household"
    assert result["errors"][error_field] == error
    assert not hass.config_entries.async_entries(DOMAIN)


async def test_tracker_only_pet_setup_and_options(hass, household):
    """A saved beta-12 pet remains usable and editable during migration."""
    pet = "device_tracker.example_pet"
    report = "sensor.example_pet_report"
    hass.states.async_set(
        pet,
        "home",
        {"source_type": "gps", ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0},
    )
    hass.states.async_set(report, "2026-01-01T00:00:00+00:00")
    entry = await legacy_tracker_entry(hass, pet, reports={pet: report})
    assert entry.state == ConfigEntryState.LOADED
    assert entry.data["members"][pet]["location_reports"] == {pet: report}
    assert entry.runtime_data.household.members[0].id == pet
    assert entry.runtime_data.household.members[0].person_entity is None
    assert entry.runtime_data.household.counts["home"] == 1
    assert entry.runtime_data.household.focus_ids["home"] == (pet,)
    assert entry.runtime_data.household.members[0].location.evidence.report_entity == (
        report
    )
    from custom_components.homecircle.api import snapshot

    assert snapshot(entry.runtime_data)["members"][0]["kind"] == "pet"
    hass.states.async_set(
        pet,
        "home",
        {
            "source_type": "gps",
            ATTR_LATITUDE: 0.0,
            ATTR_LONGITUDE: 0.0,
            "entity_picture": "/local/example-pet.png",
        },
    )
    await hass.async_block_till_done()
    assert snapshot(entry.runtime_data)["members"][0]["picture"] == (
        "/local/example-pet.png"
    )

    options = hass.config_entries.options
    flow = await start_options(options, entry)
    flow = await options.async_configure(
        flow["flow_id"],
        {"pets": [pet], "primary_home": household["primary_home"]},
    )
    assert flow["step_id"] == "pet_member"
    flow = await options.async_configure(
        flow["flow_id"],
        {"additional_residences": ["zone.example_residence"], "configure_timing": True},
    )
    assert flow["step_id"] == "pet_freshness"
    flow = await options.async_configure(
        flow["flow_id"], {"pet_home_minutes": 720, "pet_away_minutes": 10}
    )
    assert flow["step_id"] == "confirm"
    await configure_empty(options, flow)
    await hass.async_block_till_done()
    assert entry.options["members"][pet]["pet_home_minutes"] == 720
    assert entry.runtime_data.household.members[0].id == pet


async def test_add_hide_and_remove_one_tracker_without_reconfirming_household(
    hass, household
):
    from homeassistant.components.person import async_create_person, entities_in_person
    from homeassistant.setup import async_setup_component
    from custom_components.homecircle.api import snapshot

    entry = await create(hass, household)
    original_members = deepcopy(dict(entry.data["members"]))
    tracker = "device_tracker.example_bike"
    hass.states.async_set(
        tracker,
        "home",
        {"source_type": "gps", ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0},
    )
    assert await async_setup_component(hass, "person", {"person": []})
    await async_create_person(hass, "Example Bike")
    person_id = next(
        state.entity_id
        for state in hass.states.async_all("person")
        if state.name == "Example Bike"
    )
    options = hass.config_entries.options
    result = await start_options(options, entry, "add_tracker_choice")
    result = await options.async_configure(result["flow_id"], {"person": person_id})
    assert result["step_id"] == "add_tracker_assign"
    result = await options.async_configure(result["flow_id"], {"add_tracker": tracker})
    assert result["step_id"] == "member"
    result = await options.async_configure(
        result["flow_id"],
        {
            "trackers": [tracker],
            "show_on_map": False,
            "auto_request_location": True,
        },
    )
    assert result["step_id"] == "member"
    assert result["errors"]["auto_request_location"] == "mobile_app_notify_required"
    result = await options.async_configure(
        result["flow_id"], {"trackers": [tracker], "show_on_map": False}
    )
    assert result["step_id"] == "confirm"
    assert (
        "Everyone map: marker hidden; selecting this member or a status category "
        "still shows their position" in result["description_placeholders"]["members"]
    )
    await configure_empty(options, result)
    await hass.async_block_till_done()
    assert all(
        entry.options["members"][key] == value
        for key, value in original_members.items()
    )
    assert entities_in_person(hass, person_id) == [tracker]
    bike = next(
        member
        for member in snapshot(entry.runtime_data)["members"]
        if member["id"] == person_id
    )
    assert bike["name"] == "Example Bike"
    assert bike["map_visible"] is False
    assert "auto_request_location" not in entry.options["members"][person_id]

    result = await start_options(options, entry, "tracker_member_choice")
    result = await options.async_configure(
        result["flow_id"], {"member": person_id, "setting": "details"}
    )
    result = await options.async_configure(
        result["flow_id"],
        {"trackers": [tracker], "show_on_map": True, "auto_request_location": False},
    )
    await configure_empty(options, result)
    await hass.async_block_till_done()
    assert snapshot(entry.runtime_data)["members"][-1]["map_visible"] is True
    assert "auto_request_location" not in entry.options["members"][person_id]

    result = await start_options(options, entry, "tracker_member_choice")
    result = await options.async_configure(
        result["flow_id"], {"member": person_id, "setting": "remove"}
    )
    result = await options.async_configure(
        result["flow_id"], {"remove_tracker": tracker}
    )
    assert result["step_id"] == "confirm_remove"
    await configure_empty(options, result)
    await hass.async_block_till_done()
    assert entry.options["members"][person_id]["trackers"] == []
    assert all(
        entry.options["members"][key] == value
        for key, value in original_members.items()
    )


async def test_remove_selected_person_tracker_preserves_person(hass, household):
    entry = await create(hass, household)
    options = hass.config_entries.options
    result = await start_options(options, entry)
    result = await options.async_configure(
        result["flow_id"], {"remove_tracker": "device_tracker.example_phone"}
    )
    assert result["step_id"] == "confirm"
    await configure_empty(options, result)
    await hass.async_block_till_done()
    member = entry.options["members"]["person.example_member"]
    assert member["trackers"] == []
    assert "person.example_member" in {
        item.id for item in entry.runtime_data.household.members
    }


async def test_tracker_shortcuts_reject_conflicts_before_member_form(hass, household):
    entry = await create(hass, household)
    manager = hass.config_entries.options
    result = await start_options(manager, entry)
    assert "add_tracker" not in {str(field) for field in result["data_schema"].schema}
    result = await manager.async_configure(
        result["flow_id"],
        {"edit_member": "person.example_member", "places": []},
    )
    assert result["errors"]["base"] == "shortcut_conflict"
    result = await manager.async_configure(
        result["flow_id"],
        {"edit_member": "person.example_member", "life360_direct": True},
    )
    assert result["errors"]["base"] == "shortcut_conflict"
    manager.async_abort(result["flow_id"])
    assert not entry.options


async def test_offline_tracker_still_gets_report_time_prompt(hass, household):
    tracker = "device_tracker.example_offline"
    hass.states.async_set(tracker, "unavailable")
    selection = {
        "people": ["person.example_member"],
        "primary_home": household["primary_home"],
        "places": [],
    }
    result = await start(hass, selection)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"trackers": [tracker], "configure_reports": True}
    )
    assert result["step_id"] == "source_report"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["step_id"] == "source_report"
    assert result["description_placeholders"]["source"] == "example offline"
    assert (
        "used only if this tracker drives the map"
        in result["description_placeholders"]["purpose"]
    )


async def test_person_offline_tracker_and_no_source_report_steps(hass, household):
    hass.states.async_set("device_tracker.example_phone", "unavailable")
    hass.states.async_set(
        "person.example_member", "home", {"source": "device_tracker.example_phone"}
    )
    result = await start(hass, household)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"trackers": ["device_tracker.example_phone"], "configure_reports": True},
    )
    assert result["step_id"] == "source_report"
    assert result["description_placeholders"]["source"] == "example phone"
    hass.config_entries.flow.async_abort(result["flow_id"])

    result = await start(hass, household)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"trackers": [], "configure_reports": True}
    )
    assert result["step_id"] == "no_report_sources"
    result = await configure_empty(hass.config_entries.flow, result)
    assert result["step_id"] == "member"


async def test_full_household_options_keeps_people_and_hides_legacy_additions(
    hass, household
):
    entry = await create(hass, household)
    manager = hass.config_entries.options
    result = await start_options(manager, entry)
    fields = {str(field) for field in result["data_schema"].schema}
    assert "people_trackers" not in fields
    assert "pets" not in fields
    result = await manager.async_configure(result["flow_id"], household)
    assert result["step_id"] == "member"
    result = await manager.async_configure(
        result["flow_id"], {"trackers": ["device_tracker.example_phone"]}
    )
    result = await manager.async_configure(
        result["flow_id"], {"trackers": ["device_tracker.example_router"]}
    )
    assert result["step_id"] == "confirm"
    await configure_empty(manager, result)
    await hass.async_block_till_done()
    assert entry.options["people"] == household["people"]
    assert entry.options["members"]["person.example_member"]["trackers"] == [
        "device_tracker.example_phone"
    ]
    assert "add_tracker_kind" not in entry.options


async def test_direct_life360_account_and_tracker_person_setup(hass, household):
    """An account can start empty, then its tracker can be chosen in Options."""
    selection = {
        "people": [],
        "primary_home": household["primary_home"],
        "places": [],
        "life360_direct": True,
    }
    flow = await start(hass, selection)
    assert flow["step_id"] == "life360_account"
    with patch(
        "custom_components.homecircle.config_flow.validate_account",
        new_callable=AsyncMock,
        return_value="same-account-fingerprint",
    ) as verify:
        flow = await hass.config_entries.flow.async_configure(
            flow["flow_id"],
            {"method": "token", "secret": "example-token"},
        )
    verify.assert_awaited_once()
    assert flow["step_id"] == "confirm"
    with patch(
        "custom_components.homecircle.life360_direct.DirectLife360.async_start",
        new_callable=AsyncMock,
    ):
        flow = await configure_empty(hass.config_entries.flow, flow)
        await hass.async_block_till_done()
    entry = flow["result"]
    assert entry.data["life360_account"] == {
        "method": "token",
        "username": "",
        "secret": "example-token",
        "account_id_hash": "same-account-fingerprint",
    }
    from custom_components.homecircle.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostics["providers"]["life360"]["state"] == "starting"
    assert "example-token" not in str(diagnostics)
    assert entry.runtime_data.household.members == ()

    from homeassistant.components.person import async_create_person
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, "person", {"person": []})
    await async_create_person(hass, "Example Direct Member")
    person_id = next(
        state.entity_id
        for state in hass.states.async_all("person")
        if state.name == "Example Direct Member"
    )
    options = hass.config_entries.options
    flow = await start_options(options, entry)
    assert "waiting for trackers" in flow["description_placeholders"]["tracker_status"]
    options.async_abort(flow["flow_id"])
    flow = await start_options(options, entry, "add_tracker_choice")
    flow = await options.async_configure(flow["flow_id"], {"person": person_id})
    assert flow["step_id"] == "add_tracker_assign"
    flow = await options.async_configure(
        flow["flow_id"], {"add_tracker": "device_tracker.example_phone"}
    )
    assert flow["step_id"] == "member"
    flow = await configure_empty(options, flow)
    assert flow["step_id"] == "confirm"
    with patch(
        "custom_components.homecircle.life360_direct.DirectLife360.async_start",
        new_callable=AsyncMock,
    ):
        await configure_empty(options, flow)
        await hass.async_block_till_done()
    assert entry.options["life360_account"]["secret"] == "example-token"
    member = entry.runtime_data.household.members[0]
    assert member.id == person_id
    assert member.kind == "person"
    assert member.person_entity == person_id
    from custom_components.homecircle.api import snapshot

    assert "example-token" not in str(snapshot(entry.runtime_data))
    flow = await start_options(options, entry)
    flow = await options.async_configure(
        flow["flow_id"],
        {
            **selection,
            "people": [person_id],
            "replace_life360_login": True,
        },
    )
    assert flow["step_id"] == "life360_account"
    with patch(
        "custom_components.homecircle.config_flow.validate_account",
        new_callable=AsyncMock,
        return_value="same-account-fingerprint",
    ):
        flow = await options.async_configure(
            flow["flow_id"], {"method": "token", "secret": "replacement-example"}
        )
    assert flow["step_id"] == "member"
    flow = await configure_empty(options, flow)
    with patch(
        "custom_components.homecircle.life360_direct.DirectLife360.async_start",
        new_callable=AsyncMock,
    ):
        await configure_empty(options, flow)
        await hass.async_block_till_done()
    assert entry.options["life360_account"]["secret"] == "replacement-example"
    assert entry.data["life360_account"]["secret"] == "replacement-example"
    assert "replacement-example" not in str(snapshot(entry.runtime_data))
    flow = await start_options(options, entry)
    flow = await options.async_configure(
        flow["flow_id"],
        {
            **selection,
            "life360_direct": False,
            "people": [person_id],
        },
    )
    assert flow["step_id"] == "member"
    flow = await configure_empty(options, flow)
    await configure_empty(options, flow)
    await hass.async_block_till_done()
    assert "life360_account" not in entry.options
    assert "life360_account" not in entry.data
    assert entry.runtime_data.managed_trackers == {}
    assert entry.runtime_data.household.members[0].id == person_id


async def test_disabled_direct_tracker_does_not_interrupt_other_members(
    hass, household
):
    for zone_id in ("zone.example_residence", "zone.example_work"):
        hass.states.async_set(
            zone_id,
            "0",
            {ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0, "radius": 100},
        )
    registry = er.async_get(hass)
    disabled = registry.async_get_or_create(
        "device_tracker",
        DOMAIN,
        "homecircle_life360_example-disabled",
        disabled_by=er.RegistryEntryDisabler.USER,
    )

    class FakeAPI:
        position = 1

        async def get_circles(self):
            return [{"id": "example-circle"}]

        async def get_circle_members(self, _circle):
            return [{"id": "example-disabled"}, {"id": "example-enabled"}]

        async def get_circle_member(self, _circle, member):
            return {
                "id": member,
                "location": {ATTR_LATITUDE: str(self.position), ATTR_LONGITUDE: "2"},
            }

    selection = {
        "people": [],
        "primary_home": household["primary_home"],
        "life360_direct": True,
    }
    flow = await start(hass, selection)
    with (
        patch(
            "custom_components.homecircle.config_flow.validate_account",
            new_callable=AsyncMock,
            return_value="same-account-fingerprint",
        ),
        patch(
            "custom_components.homecircle.life360_direct.authorized_client",
            new_callable=AsyncMock,
            return_value=FakeAPI(),
        ),
    ):
        flow = await hass.config_entries.flow.async_configure(
            flow["flow_id"], {"method": "token", "secret": "example-token"}
        )
        flow = await configure_empty(hass.config_entries.flow, flow)
        await hass.async_block_till_done()
        entry = flow["result"]
        client = entry.runtime_data.managed_trackers["life360"]
        assert client.trackers["example-disabled"].entity_id == disabled.entity_id
        assert client.trackers["example-disabled"].hass is None
        assert hass.states.get(disabled.entity_id) is None
        enabled_id = client.trackers["example-enabled"].entity_id
        assert hass.states.get(enabled_id) is not None
        client.api.position = 3
        await client.async_refresh()
        assert hass.states.get(enabled_id).attributes[ATTR_LATITUDE] == 3
        assert client.health_snapshot().state == "connected"


async def test_failed_tracker_platform_setup_can_retry_cleanly(hass, household):
    selection = {
        "people": [],
        "primary_home": household["primary_home"],
        "life360_direct": True,
    }
    flow = await start(hass, selection)
    with (
        patch(
            "custom_components.homecircle.config_flow.validate_account",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.homecircle.life360_direct.DirectLife360.async_start",
            new_callable=AsyncMock,
            side_effect=OSError("fictional startup failure"),
        ),
    ):
        flow = await hass.config_entries.flow.async_configure(
            flow["flow_id"], {"method": "token", "secret": "example-token"}
        )
        flow = await configure_empty(hass.config_entries.flow, flow)
        await hass.async_block_till_done()
    entry = flow["result"]
    # HA keeps the parent entry loaded even when a forwarded platform fails.
    assert entry.state is ConfigEntryState.LOADED
    assert not entry.runtime_data.managed_trackers

    class EmptyAPI:
        async def get_circles(self):
            return []

    with patch(
        "custom_components.homecircle.life360_direct.authorized_client",
        new_callable=AsyncMock,
        return_value=EmptyAPI(),
    ):
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert "life360" in entry.runtime_data.managed_trackers
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_saved_direct_tracker_is_unavailable_during_offline_reload(
    hass, household
):
    for zone_id in ("zone.example_residence", "zone.example_work"):
        hass.states.async_set(
            zone_id,
            "0",
            {ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0, "radius": 100},
        )
    raw = {
        "id": "example-member-id",
        "location": {ATTR_LATITUDE: "1", ATTR_LONGITUDE: "2"},
    }

    class FakeAPI:
        async def get_circles(self):
            return [{"id": "example-circle"}]

        async def get_circle_members(self, _circle):
            return [raw]

        async def get_circle_member(self, _circle, _member):
            return raw

    selection = {
        "people": [],
        "primary_home": household["primary_home"],
        "life360_direct": True,
    }
    flow = await start(hass, selection)
    with (
        patch(
            "custom_components.homecircle.config_flow.validate_account",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.homecircle.life360_direct.authorized_client",
            new_callable=AsyncMock,
            return_value=FakeAPI(),
        ),
    ):
        flow = await hass.config_entries.flow.async_configure(
            flow["flow_id"], {"method": "token", "secret": "example-token"}
        )
        flow = await configure_empty(hass.config_entries.flow, flow)
        await hass.async_block_till_done()
    entry = flow["result"]
    original = entry.runtime_data.managed_trackers["life360"].trackers[
        "example-member-id"
    ]
    assert hass.states.get(original.entity_id).attributes[ATTR_LATITUDE] == 1

    with patch(
        "custom_components.homecircle.life360_direct.authorized_client",
        new_callable=AsyncMock,
        side_effect=OSError("fictional network outage"),
    ):
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
    client = entry.runtime_data.managed_trackers["life360"]
    restored = client.trackers["example-member-id"]
    assert restored.entity_id == original.entity_id
    assert hass.states.get(restored.entity_id).state == "unavailable"
    assert client.health_snapshot().state == "network_error"

    client._retry_at = datetime.min.replace(tzinfo=timezone.utc)
    with patch(
        "custom_components.homecircle.life360_direct.authorized_client",
        new_callable=AsyncMock,
        return_value=FakeAPI(),
    ):
        await client.async_refresh()
    assert hass.states.get(restored.entity_id).attributes[ATTR_LATITUDE] == 1
    assert client.health_snapshot().state == "connected"


async def test_life360_reauth_replaces_secret_and_preserves_household(hass, household):
    selection = {
        "people": [],
        "primary_home": household["primary_home"],
        "places": [],
        "life360_direct": True,
    }
    flow = await start(hass, selection)
    with (
        patch(
            "custom_components.homecircle.config_flow.validate_account",
            new_callable=AsyncMock,
            return_value="same-account-fingerprint",
        ),
        patch(
            "custom_components.homecircle.life360_direct.DirectLife360.async_start",
            new_callable=AsyncMock,
        ),
    ):
        flow = await hass.config_entries.flow.async_configure(
            flow["flow_id"], {"method": "token", "secret": "old-example-secret"}
        )
        flow = await configure_empty(hass.config_entries.flow, flow)
        await hass.async_block_till_done()
    entry = flow["result"]
    original_home = entry.data["primary_home"]
    client = entry.runtime_data.managed_trackers["life360"]
    client.session = AsyncMock()
    with patch(
        "custom_components.homecircle.life360_direct.authorized_client",
        new_callable=AsyncMock,
        side_effect=Unauthorized("fictional rejection", None),
    ):
        await client.async_refresh()
        await hass.async_block_till_done()
    active = hass.config_entries.flow.async_progress_by_handler(
        DOMAIN, match_context={"entry_id": entry.entry_id}
    )
    assert len(active) == 1
    assert active[0]["context"]["source"] == SOURCE_REAUTH
    reauth = active[0]
    with (
        patch(
            "custom_components.homecircle.config_flow.validate_account",
            new_callable=AsyncMock,
            return_value="same-account-fingerprint",
        ) as verify,
        patch(
            "custom_components.homecircle.life360_direct.DirectLife360.async_start",
            new_callable=AsyncMock,
        ),
    ):
        verify.side_effect = ValueError("fictional changed response")
        failed = await hass.config_entries.flow.async_configure(
            reauth["flow_id"], {"method": "token", "secret": "new-example-secret"}
        )
        assert failed["errors"] == {"base": "unexpected_response"}
        assert entry.data["life360_account"]["secret"] == "old-example-secret"
        verify.side_effect = None
        result = await hass.config_entries.flow.async_configure(
            reauth["flow_id"], {"method": "token", "secret": "new-example-secret"}
        )
        await hass.async_block_till_done()
    assert result["reason"] == "reauth_successful"
    assert entry.data["life360_account"]["secret"] == "new-example-secret"
    assert entry.data["primary_home"] == original_home
    assert entry.state == ConfigEntryState.LOADED


async def test_reconnect_rejects_a_different_life360_account(hass, household):
    selection = {
        "people": [],
        "primary_home": household["primary_home"],
        "life360_direct": True,
    }
    flow = await start(hass, selection)
    with (
        patch(
            "custom_components.homecircle.config_flow.validate_account",
            new_callable=AsyncMock,
            return_value="original-account-fingerprint",
        ),
        patch(
            "custom_components.homecircle.life360_direct.DirectLife360.async_start",
            new_callable=AsyncMock,
        ),
    ):
        flow = await hass.config_entries.flow.async_configure(
            flow["flow_id"], {"method": "token", "secret": "original-token"}
        )
        flow = await configure_empty(hass.config_entries.flow, flow)
        await hass.async_block_till_done()
    entry = flow["result"]
    assert entry.data["life360_account"]["account_id_hash"] == (
        "original-account-fingerprint"
    )
    from custom_components.homecircle.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert "original-account-fingerprint" not in str(diagnostics)

    entry.async_start_reauth(hass, data={"_homecircle_reauth_provider": "life360"})
    await hass.async_block_till_done()
    active = hass.config_entries.flow.async_progress_by_handler(
        DOMAIN, match_context={"entry_id": entry.entry_id}
    )
    assert len(active) == 1
    with patch(
        "custom_components.homecircle.config_flow.validate_account",
        new_callable=AsyncMock,
        return_value="different-account-fingerprint",
    ):
        rejected = await hass.config_entries.flow.async_configure(
            active[0]["flow_id"], {"method": "token", "secret": "different-token"}
        )
    assert rejected["errors"] == {"base": "different_account"}
    assert entry.data["life360_account"]["secret"] == "original-token"
    hass.config_entries.flow.async_abort(active[0]["flow_id"])

    options = hass.config_entries.options
    flow = await start_options(options, entry)
    flow = await options.async_configure(
        flow["flow_id"], {**selection, "replace_life360_login": True}
    )
    assert flow["step_id"] == "life360_account"
    with patch(
        "custom_components.homecircle.config_flow.validate_account",
        new_callable=AsyncMock,
        return_value="different-account-fingerprint",
    ):
        rejected = await options.async_configure(
            flow["flow_id"], {"method": "token", "secret": "different-token"}
        )
    assert rejected["errors"] == {"base": "different_account"}
    assert entry.data["life360_account"]["secret"] == "original-token"
    options.async_abort(flow["flow_id"])


async def test_older_account_replacement_compares_valid_old_sign_in(hass, household):
    selection = {
        "people": [],
        "primary_home": household["primary_home"],
        "life360_direct": True,
    }
    flow = await start(hass, selection)
    with (
        patch(
            "custom_components.homecircle.config_flow.validate_account",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.homecircle.life360_direct.DirectLife360.async_start",
            new_callable=AsyncMock,
        ),
    ):
        flow = await hass.config_entries.flow.async_configure(
            flow["flow_id"], {"method": "token", "secret": "old-fictional-token"}
        )
        flow = await configure_empty(hass.config_entries.flow, flow)
        await hass.async_block_till_done()
    entry = flow["result"]
    assert "account_id_hash" not in entry.data["life360_account"]

    options = hass.config_entries.options
    flow = await start_options(options, entry)
    flow = await options.async_configure(
        flow["flow_id"], {**selection, "replace_life360_login": True}
    )
    assert flow["step_id"] == "life360_account"
    assert "confirm_same_account" in {
        str(field) for field in flow["data_schema"].schema
    }

    async def identity(account):
        return (
            "old-fingerprint"
            if account["secret"] == "old-fictional-token"
            else "different-fingerprint"
        )

    with patch(
        "custom_components.homecircle.config_flow.validate_account",
        new_callable=AsyncMock,
        side_effect=identity,
    ):
        rejected = await options.async_configure(
            flow["flow_id"],
            {
                "method": "token",
                "secret": "different-fictional-token",
                "confirm_same_account": True,
            },
        )
    assert rejected["errors"] == {"base": "different_account"}
    assert entry.data["life360_account"]["secret"] == "old-fictional-token"

    async def expired_old_identity(account):
        if account["secret"] == "old-fictional-token":
            raise Unauthorized("fictional expired token", None)
        return "old-fingerprint"

    with patch(
        "custom_components.homecircle.config_flow.validate_account",
        new_callable=AsyncMock,
        side_effect=expired_old_identity,
    ):
        rejected = await options.async_configure(
            flow["flow_id"],
            {"method": "token", "secret": "replacement-fictional-token"},
        )
    assert rejected["errors"] == {
        "confirm_same_account": "same_account_confirmation_required"
    }
    assert entry.data["life360_account"]["secret"] == "old-fictional-token"

    with (
        patch(
            "custom_components.homecircle.config_flow.validate_account",
            new_callable=AsyncMock,
            return_value="old-fingerprint",
        ),
        patch(
            "custom_components.homecircle.life360_direct.DirectLife360.async_start",
            new_callable=AsyncMock,
        ),
    ):
        flow = await options.async_configure(
            flow["flow_id"],
            {"method": "token", "secret": "replacement-fictional-token"},
        )
        assert flow["step_id"] == "confirm"
        await configure_empty(options, flow)
        await hass.async_block_till_done()
    assert entry.options["life360_account"]["account_id_hash"] == "old-fingerprint"
    assert entry.data["life360_account"]["account_id_hash"] == "old-fingerprint"


async def test_older_reauth_requires_confirmation_if_old_sign_in_expired(
    hass, household
):
    selection = {
        "people": [],
        "primary_home": household["primary_home"],
        "life360_direct": True,
    }
    flow = await start(hass, selection)
    with (
        patch(
            "custom_components.homecircle.config_flow.validate_account",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.homecircle.life360_direct.DirectLife360.async_start",
            new_callable=AsyncMock,
        ),
    ):
        flow = await hass.config_entries.flow.async_configure(
            flow["flow_id"], {"method": "token", "secret": "expired-fictional-token"}
        )
        flow = await configure_empty(hass.config_entries.flow, flow)
        await hass.async_block_till_done()
    entry = flow["result"]
    entry.async_start_reauth(hass, data={"_homecircle_reauth_provider": "life360"})
    await hass.async_block_till_done()
    active = hass.config_entries.flow.async_progress_by_handler(
        DOMAIN, match_context={"entry_id": entry.entry_id}
    )
    assert len(active) == 1
    flow_id = active[0]["flow_id"]

    async def identity(account):
        if account["secret"] == "expired-fictional-token":
            raise Unauthorized("fictional expired token", None)
        return "same-account-fingerprint"

    with patch(
        "custom_components.homecircle.config_flow.validate_account",
        new_callable=AsyncMock,
        side_effect=identity,
    ) as verify:
        rejected = await hass.config_entries.flow.async_configure(
            flow_id, {"method": "token", "secret": "replacement-fictional-token"}
        )
    assert [call.args[0]["secret"] for call in verify.await_args_list] == [
        "replacement-fictional-token"
    ]
    assert rejected["errors"] == {
        "confirm_same_account": "same_account_confirmation_required"
    }
    assert entry.data["life360_account"]["secret"] == "expired-fictional-token"

    with (
        patch(
            "custom_components.homecircle.config_flow.validate_account",
            new_callable=AsyncMock,
            side_effect=identity,
        ) as verify,
        patch(
            "custom_components.homecircle.life360_direct.DirectLife360.async_start",
            new_callable=AsyncMock,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            flow_id,
            {
                "method": "token",
                "secret": "replacement-fictional-token",
                "confirm_same_account": True,
            },
        )
        await hass.async_block_till_done()
    assert [call.args[0]["secret"] for call in verify.await_args_list] == [
        "replacement-fictional-token"
    ]
    assert result["reason"] == "reauth_successful"
    assert entry.data["life360_account"]["account_id_hash"] == (
        "same-account-fingerprint"
    )


async def test_direct_life360_creates_selectable_tracker(hass, household):
    """Exercise the real HA tracker platform with a fictional API response."""
    registry = er.async_get(hass)
    existing = registry.async_get_or_create(
        "device_tracker", "life360", "example-existing-id"
    )
    hass.states.async_set(
        existing.entity_id,
        "home",
        {"friendly_name": "Life360 Existing Member", "source_type": "gps"},
    )
    for entity_id, latitude in (
        ("zone.example_residence", 2.0),
        ("zone.example_work", 3.0),
    ):
        hass.states.async_set(
            entity_id,
            "0",
            {
                ATTR_LATITUDE: latitude,
                ATTR_LONGITUDE: 0.0,
                "radius": 100,
                "passive": False,
            },
        )
    raw = {
        "id": "example-direct-id",
        "firstName": "Direct",
        "lastName": "Member",
        "features": {"shareLocation": "1"},
        "location": {
            ATTR_LATITUDE: str(0),
            ATTR_LONGITUDE: str(0),
            "accuracy": "10",
            "timestamp": "1760000000",
        },
    }

    class FakeAPI:
        async def get_circles(self):
            return [{"id": "example-circle"}]

        async def get_circle_members(self, _circle):
            return [raw]

        async def get_circle_member(self, _circle, _member):
            return raw

    selection = {
        "people": [],
        "primary_home": household["primary_home"],
        "places": [],
        "life360_direct": True,
    }
    flow = await start(hass, selection)
    with (
        patch(
            "custom_components.homecircle.config_flow.validate_account",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.homecircle.life360_direct.authorized_client",
            new_callable=AsyncMock,
            return_value=FakeAPI(),
        ),
    ):
        flow = await hass.config_entries.flow.async_configure(
            flow["flow_id"], {"method": "token", "secret": "example-token"}
        )
        flow = await configure_empty(hass.config_entries.flow, flow)
        await hass.async_block_till_done()
        entry = flow["result"]
        states = [
            state
            for state in hass.states.async_all("device_tracker")
            if state.name == "Life360 Direct Member"
        ]
        assert len(states) == 1
        tracker = states[0].entity_id
        assert tracker != existing.entity_id
        assert hass.states.get(existing.entity_id).state == "home"
        options = hass.config_entries.options
        flow = await start_options(options, entry)
        assert (
            "duplicate trackers" in flow["description_placeholders"]["tracker_status"]
        )
        assert (
            "1 tracker(s) found" in flow["description_placeholders"]["tracker_status"]
        )
        options.async_abort(flow["flow_id"])
        from homeassistant.components.person import (
            async_create_person,
            entities_in_person,
        )
        from homeassistant.setup import async_setup_component

        assert await async_setup_component(hass, "person", {"person": []})
        await async_create_person(hass, "Direct Member")
        person_id = next(
            state.entity_id
            for state in hass.states.async_all("person")
            if state.name == "Direct Member"
        )
        flow = await start_options(options, entry, "add_tracker_choice")
        flow = await options.async_configure(flow["flow_id"], {"person": person_id})
        assert flow["step_id"] == "add_tracker_assign"
        flow = await options.async_configure(flow["flow_id"], {"add_tracker": tracker})
        assert flow["step_id"] == "member"
        flow = await configure_empty(options, flow)
        await configure_empty(options, flow)
        await hass.async_block_till_done()
        assert entities_in_person(hass, person_id) == [tracker]
        flow = await start_options(options, entry)
        flow = await options.async_configure(
            flow["flow_id"],
            {
                **selection,
                "life360_direct": False,
                "people": [person_id],
            },
        )
        flow = await configure_empty(options, flow)
        flow = await configure_empty(options, flow)
        assert flow["step_id"] == "household"
        assert flow["errors"] == {"base": "direct_trackers_selected"}
        options.async_abort(flow["flow_id"])
    assert entry.runtime_data.household.members[0].id == person_id
    assert entry.runtime_data.household.counts["away"] == 1


async def test_new_setup_requires_a_person_for_pet_tracker(hass, household):
    flow = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    fields = {str(field) for field in flow["data_schema"].schema}
    assert "pets" not in fields
    assert "people_trackers" not in fields
    with pytest.raises(InvalidData):
        await hass.config_entries.flow.async_configure(
            flow["flow_id"],
            {"pets": ["device_tracker.example_phone"], "primary_home": "zone.home"},
        )


async def test_tracker_linked_to_another_ha_person_is_rejected(hass):
    from homeassistant.components.person import async_create_person
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, "zone", {})
    assert await async_setup_component(hass, "person", {"person": []})
    tracker = "device_tracker.example_phone"
    hass.states.async_set(tracker, "home", {"source_type": "gps"})
    await async_create_person(hass, "Example Owner", device_trackers=[tracker])
    await async_create_person(hass, "Example Other")
    other = next(
        state.entity_id
        for state in hass.states.async_all("person")
        if state.name == "Example Other"
    )
    flow = await start(hass, {"people": [other], "primary_home": "zone.home"})
    assert flow["step_id"] == "assign_tracker"
    flow = await hass.config_entries.flow.async_configure(
        flow["flow_id"], {"tracker": tracker}
    )
    assert flow["step_id"] == "assign_tracker"
    assert flow["errors"]["tracker"] == "tracker_linked_elsewhere"


async def test_same_tracker_cannot_be_assigned_to_two_people(hass, household):
    flow = await start(hass, household)
    assert flow["step_id"] == "member"
    flow = await hass.config_entries.flow.async_configure(
        flow["flow_id"], {"trackers": ["device_tracker.example_phone"]}
    )
    assert flow["step_id"] == "member"
    flow = await hass.config_entries.flow.async_configure(
        flow["flow_id"], {"trackers": ["device_tracker.example_phone"]}
    )
    assert flow["step_id"] == "member"
    assert flow["errors"]["trackers"] == "duplicate_selection"


async def test_person_and_pet_person_share_household_flow(hass, household):
    from homeassistant.components.person import async_create_person, entities_in_person
    from homeassistant.setup import async_setup_component

    pet = "device_tracker.example_pet"
    hass.states.async_set(
        pet,
        "not_home",
        {"source_type": "gps", ATTR_LATITUDE: 1.0, ATTR_LONGITUDE: 0.0},
    )
    assert await async_setup_component(hass, "person", {"person": []})
    await async_create_person(hass, "Example Pet")
    pet_person = next(
        state.entity_id
        for state in hass.states.async_all("person")
        if state.name == "Example Pet"
    )
    flow = await start(
        hass,
        {
            **household,
            "people": ["person.example_member", pet_person],
        },
    )
    assert flow["step_id"] == "member"
    flow = await hass.config_entries.flow.async_configure(
        flow["flow_id"], {"trackers": ["device_tracker.example_phone"]}
    )
    assert flow["step_id"] == "assign_tracker"
    flow = await hass.config_entries.flow.async_configure(
        flow["flow_id"], {"tracker": pet}
    )
    assert flow["step_id"] == "member"
    flow = await hass.config_entries.flow.async_configure(
        flow["flow_id"], {"kind": "pet"}
    )
    assert flow["step_id"] == "pet_freshness"
    flow = await configure_empty(hass.config_entries.flow, flow)
    assert flow["step_id"] == "confirm"
    flow = await configure_empty(hass.config_entries.flow, flow)
    await hass.async_block_till_done()
    household_view = flow["result"].runtime_data.household
    assert [member.id for member in household_view.members] == [
        "person.example_member",
        pet_person,
    ]
    assert household_view.members[1].kind == "pet"
    assert entities_in_person(hass, pet_person) == [pet]


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
    result = await configure_empty(hass.config_entries.flow, result)
    result = await configure_empty(hass.config_entries.flow, result)
    hass.states.async_remove("person.example_member")
    result = await configure_empty(hass.config_entries.flow, result)
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
    result = await start_options(manager, entry)
    result = await manager.async_configure(
        result["flow_id"],
        {
            **household,
            "people": ["person.example_second"],
            "places": [],
        },
    )
    result = await configure_empty(manager, result)
    result = await configure_empty(manager, result)
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
    assert "add_tracker_kind" not in entry.options
    assert "edit_member" not in entry.options
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
    assert {
        key: placeholders[key] for key in ("person", "number", "total", "active")
    } == {
        "person": "Example Member",
        "number": "1",
        "total": "2",
        "active": "Example Phone",
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


async def test_map_source_guidance_and_report_prompts_follow_effective_source(
    hass, household
):
    hass.states.async_set(
        "person.example_member",
        "home",
        {
            "source": "device_tracker.example_router",
            ATTR_LATITUDE: 0.0,
            ATTR_LONGITUDE: 0.0,
        },
    )
    with patch(
        "custom_components.homecircle.selection.entities_in_person",
        return_value=["device_tracker.example_phone", "device_tracker.example_router"],
    ):
        result = await start(hass, household)
    guidance = result["description_placeholders"]["position_guidance"]
    assert "Home Assistant Person" in guidance
    assert "example router" in guidance
    assert "selected tracker's report-time sensor will be used only if" in guidance
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"trackers": ["device_tracker.example_phone"], "configure_reports": True},
    )
    assert result["step_id"] == "source_report"
    assert result["description_placeholders"]["source"] == "example member"
    assert result["description_placeholders"]["purpose"] == "Current map source"
    result = await configure_empty(hass.config_entries.flow, result)
    assert result["step_id"] == "source_report"
    assert result["description_placeholders"]["source"] == "example phone"
    assert (
        "used only if this tracker drives the map"
        in result["description_placeholders"]["purpose"]
    )
    result = await configure_empty(hass.config_entries.flow, result)
    result = await configure_empty(hass.config_entries.flow, result)
    assert result["step_id"] == "confirm"
    assert (
        "Current map position comes from the Home Assistant Person"
        in result["description_placeholders"]["members"]
    )


async def test_borrowed_home_position_warns_in_setup_and_options(hass, household):
    person = "person.example_member"
    phone = "device_tracker.example_phone"
    router = "device_tracker.example_router"
    hass.states.async_set(
        person,
        "home",
        {"source": router, ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0},
    )
    hass.states.async_set(
        phone,
        "not_home",
        {"source_type": "gps", ATTR_LATITUDE: 2.0, ATTR_LONGITUDE: 0.0},
    )
    with patch(
        "custom_components.homecircle.selection.entities_in_person",
        return_value=[phone, router],
    ):
        result = await start(hass, household)
        assert (
            "Tracker conflict"
            in result["description_placeholders"]["position_guidance"]
        )
        hass.config_entries.flow.async_abort(result["flow_id"])

        entry = await create(hass, household)
        result = await start_options(
            hass.config_entries.options, entry, "tracker_member_choice"
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"member": person, "setting": "details"}
        )
        guidance = result["description_placeholders"]["position_guidance"]
        assert "Tracker conflict" in guidance
        assert "example phone" in guidance
        assert "example router" in guidance
        assert "[Home Assistant People settings](/config/person)" in guidance
        hass.config_entries.options.async_abort(result["flow_id"])


async def test_saved_person_report_mapping_is_not_labelled_for_deletion(
    hass, household
):
    hass.states.async_set("sensor.example_report", "2026-01-01T00:00:00+00:00")
    entry = await create(hass, household)
    person = "person.example_member"
    data = deepcopy(dict(entry.data))
    data["members"][person]["location_reports"] = {person: "sensor.example_report"}
    hass.config_entries.async_update_entry(entry, data=data)
    manager = hass.config_entries.options
    result = await start_options(manager, entry)
    result = await manager.async_configure(result["flow_id"], {"edit_member": person})
    result = await manager.async_configure(
        result["flow_id"],
        {"trackers": ["device_tracker.example_phone"], "configure_reports": True},
    )
    assert result["step_id"] == "source_report"
    result = await configure_empty(manager, result)
    assert result["description_placeholders"]["source"] == "example member"
    assert (
        "used when the Person drives the map"
        in result["description_placeholders"]["purpose"]
    )
    manager.async_abort(result["flow_id"])


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
        r"Example Phone (device\_tracker.example\_phone)"
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
    result = await configure_empty(hass.config_entries.flow, result)
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
    with pytest.raises(InvalidData):
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"battery": "sensor.example_missing"},
        )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"battery": "sensor.example_battery"},
    )
    assert result["step_id"] == "source_report"
    assert result["description_placeholders"]["number"] == "1"
    assert result["description_placeholders"]["total"] == "1"
    assert result["description_placeholders"]["source"] == "example phone"
    assert result["description_placeholders"]["purpose"] == "Current map source"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"timestamp": "sensor.example_report"}
    )
    result = await configure_empty(hass.config_entries.flow, result)
    assert result["step_id"] == "confirm"
    review = result["description_placeholders"]["members"]
    assert "Battery: Example Battery" in review
    assert "Example Report" in review
    result = await configure_empty(hass.config_entries.flow, result)
    entry = result["result"]
    await hass.async_block_till_done()
    assert entry.runtime_data.household.members[0].battery.value == 0
    assert "sensor.example_battery" in entry.runtime_data.states
    assert entry.data["members"]["person.example_member"]["location_reports"] == {
        "device_tracker.example_phone": "sensor.example_report"
    }
    options = hass.config_entries.options
    result = await start_options(options, entry)
    result = await options.async_configure(result["flow_id"], household)
    result = await options.async_configure(
        result["flow_id"],
        {
            "trackers": ["device_tracker.example_phone"],
            "configure_sensors": True,
        },
    )
    result = await configure_empty(options, result)
    result = await configure_empty(options, result)
    await configure_empty(options, result)
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
    result = await configure_empty(hass.config_entries.flow, result)
    result = await configure_empty(hass.config_entries.flow, result)
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
    flow = await start_options(manager, entry)
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
    flow = await configure_empty(manager, flow)
    await hass.async_block_till_done()
    assert flow["type"] == FlowResultType.CREATE_ENTRY
    member = entry.options["members"]["person.example_member"]
    assert member["kind"] == "pet"
    assert member["pet_home_minutes"] == 720
    assert member["pet_away_minutes"] == 10
    assert entry.runtime_data.config["members"]["person.example_member"] == member

    flow = await start_options(manager, entry)
    flow = await manager.async_configure(
        flow["flow_id"], {**household, "people": ["person.example_member"]}
    )
    flow = await manager.async_configure(
        flow["flow_id"],
        {
            "trackers": ["device_tracker.example_phone"],
            "kind": "pet",
            "configure_sensors": True,
            "configure_timing": True,
        },
    )
    assert flow["step_id"] == "pet_freshness"
    suggested = {
        str(field): (field.description or {}).get("suggested_value")
        for field in flow["data_schema"].schema
    }
    assert suggested == {"pet_home_minutes": 720, "pet_away_minutes": 10}
    flow = await configure_empty(manager, flow)
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
    result = await start_options(options, entry)
    result = await options.async_configure(result["flow_id"], household)
    result = await options.async_configure(
        result["flow_id"],
        {"trackers": ["device_tracker.example_phone"]},
    )
    assert result["step_id"] == "source_report"
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
    await configure_empty(options, result)
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
    result = await start_options(options, entry)
    result = await options.async_configure(result["flow_id"], household)
    result = await options.async_configure(result["flow_id"], {"trackers": []})
    assert result["step_id"] == "source_report"
    result = await configure_empty(options, result)
    result = await options.async_configure(
        result["flow_id"], {"timestamp": "sensor.example_report"}
    )
    assert result["errors"]["timestamp"] == "invalid_report_source"
    result = await configure_empty(options, result)
    result = await options.async_configure(
        result["flow_id"], {"trackers": ["device_tracker.example_router"]}
    )
    await configure_empty(options, result)
    await hass.async_block_till_done()
    assert entry.options["members"][person]["location_reports"] == {}
    assert "sensor.example_report" not in selected_entities(entry.options)


@pytest.mark.parametrize("yaml_person", [False, True])
@pytest.mark.parametrize("already_selected", [False, True])
async def test_details_never_link_trackers_or_block_yaml_person(
    hass, yaml_person, already_selected
):
    from homeassistant.components.person import async_create_person, entities_in_person
    from homeassistant.setup import async_setup_component

    linked = "device_tracker.example_linked"
    unlinked = "device_tracker.example_unlinked"
    assert await async_setup_component(hass, "zone", {})
    for tracker in (linked, unlinked):
        hass.states.async_set(tracker, "home", {"source_type": "gps"})
    config = (
        {
            "person": [
                {
                    "id": "example_member",
                    "name": "Example Member",
                    "device_trackers": [linked],
                }
            ]
        }
        if yaml_person
        else {"person": []}
    )
    assert await async_setup_component(hass, "person", config)
    if not yaml_person:
        await async_create_person(hass, "Example Member", device_trackers=[linked])
    await hass.async_block_till_done()
    person_id = "person.example_member"
    data = {
        "people": [person_id],
        "primary_home": "zone.home",
        "places": [],
        "members": {
            person_id: {
                "trackers": [linked, unlinked] if already_selected else [linked],
                "additional_residences": [],
            }
        },
    }
    entry = MockConfigEntry(
        domain=DOMAIN, title="HomeCircle", data=data, unique_id=DOMAIN
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    manager = hass.config_entries.options
    result = await start_options(manager, entry, "tracker_member_choice")
    result = await manager.async_configure(
        result["flow_id"], {"member": person_id, "setting": "details"}
    )
    result = await manager.async_configure(
        result["flow_id"], {"trackers": [linked, unlinked], "show_on_map": False}
    )
    assert result["step_id"] == "confirm"
    assert "Will link" not in result["description_placeholders"]["members"]
    result = await configure_empty(manager, result)
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entities_in_person(hass, person_id) == [linked]
    assert entry.options["members"][person_id]["trackers"] == [linked, unlinked]
    assert entry.options["members"][person_id]["show_on_map"] is False


async def test_family_refresh_opt_in_is_explicit_and_persisted(hass, household):
    entry = await create(hass, household)
    assert entry.data["family_refresh_enabled"] is False
    manager = hass.config_entries.options
    flow = await start_options(manager, entry)
    flow = await manager.async_configure(
        flow["flow_id"], {**household, "family_refresh_enabled": True}
    )
    result = await finish(hass, flow, manager)
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options["family_refresh_enabled"] is True
    flow = await start_options(manager, entry)
    flow = await manager.async_configure(flow["flow_id"], household)
    result = await finish(hass, flow, manager)
    await hass.async_block_till_done()
    assert entry.options["family_refresh_enabled"] is True
    flow = await start_options(manager, entry)
    flow = await manager.async_configure(
        flow["flow_id"], {**household, "family_refresh_enabled": False}
    )
    await finish(hass, flow, manager)
    await hass.async_block_till_done()
    assert entry.options["family_refresh_enabled"] is False


async def test_member_description_escapes_entity_name(hass, household):
    from custom_components.homecircle.config_flow import markdown_label

    name = "[Example](https://example.invalid) <b>Member</b>"
    state = hass.states.get(household["people"][0])
    hass.states.async_set(
        state.entity_id, state.state, {**state.attributes, "friendly_name": name}
    )
    flow = await start(hass, household)
    assert flow["description_placeholders"]["person"] == markdown_label(name)
    hass.config_entries.flow.async_abort(flow["flow_id"])
