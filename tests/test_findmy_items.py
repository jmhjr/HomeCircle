"""Explicit Person assignments replace only duplicate native item displays."""

from copy import deepcopy

import pytest
from homeassistant.helpers import entity_registry as er

from custom_components.homecircle.findmy_items import item_config
from custom_components.homecircle.findmy_provider import tracker_unique_id
from custom_components.homecircle.normalize import normalize_household
from homeassistant.util import dt as dt_util


@pytest.fixture
def configured_items(hass):
    registry = er.async_get(hass)
    account_id = "a" * 32
    items = {
        "assigned": {"name": "Example", "unique_id": "homecircle_findmy_migrated"},
        "backpack": {"name": "Example backpack"},
        "vehicle": {"name": "Example vehicle"},
    }
    entity_ids = {
        identifier: registry.async_get_or_create(
            "device_tracker", "homecircle", tracker_unique_id(account_id, identifier, item),
        ).entity_id
        for identifier, item in items.items()
    }
    external = registry.async_get_or_create("device_tracker", "mqtt", "synthetic_external").entity_id
    item_preferences = {
        "kind": "item", "trackers": [entity_ids["assigned"]],
        "additional_residences": [], "display_name": "Custom item label",
        "show_on_map": False, "picture_id": "b" * 32,
        "supporting": {"battery": "sensor.example_battery"},
    }
    config = {
        "people": ["person.example_pet"], "people_trackers": [], "pets": [],
        "primary_home": "zone.home", "places": [],
        "items": [*entity_ids.values(), external],
        "findmy_accounts": {account_id: {"items": items}},
        "members": {
            "person.example_pet": {
                "kind": "pet", "trackers": ["device_tracker.example_phone", entity_ids["assigned"]],
                "additional_residences": [], "show_on_map": True,
                "pet_home_minutes": 120, "pet_away_minutes": 15,
            },
            entity_ids["assigned"]: deepcopy(item_preferences),
            external: {"kind": "item", "trackers": [external], "additional_residences": []},
        },
    }
    return config, entity_ids, external, item_preferences


def test_explicit_person_assignment_suppresses_one_card_and_preserves_account_and_other_items(hass, configured_items):
    config, ids, external, preferences = configured_items
    before = deepcopy(config)
    result = item_config(hass, config)
    assert config == before
    expected_accounts = deepcopy(before["findmy_accounts"])
    expected_accounts["a" * 32]["items"]["assigned"]["display_preferences"] = preferences
    assert result["findmy_accounts"] == expected_accounts
    assert result["items"] == [external, ids["backpack"], ids["vehicle"]]
    assert result["members"]["person.example_pet"] == before["members"]["person.example_pet"]
    assert ids["assigned"] not in result["members"]
    assert result["members"][external] == before["members"][external]
    assert result["members"][ids["backpack"]]["kind"] == "item"
    assert result["members"][ids["vehicle"]]["trackers"] == [ids["vehicle"]]
    now = dt_util.utcnow()
    for entity in ["device_tracker.example_phone", *ids.values(), external]:
        hass.states.async_set(entity, "not_home", {"source_type": "gps", "latitude": float(0),
                                                  "longitude": float(0), "last_seen": now.isoformat()})
    hass.states.async_set("person.example_pet", "not_home", {
        "source": "device_tracker.example_phone", "latitude": float(0), "longitude": float(0),
    })
    states = {state.entity_id: state for state in hass.states.async_all()}
    household = normalize_household(result, states, now, {})
    assert {member.id for member in household.members} == {
        "person.example_pet", ids["backpack"], ids["vehicle"], external,
    }
    assert sum(household.counts[key] for key in ("home", "away", "driving", "unavailable")) == 1
    assert household.counts["items"] == 3
    assert "person.example_pet" in household.focus_ids["overview"]
    assert ids["assigned"] not in household.focus_ids["overview"]


def test_projection_is_idempotent_and_unassignment_restores_saved_item_preferences(hass, configured_items):
    config, ids, _, preferences = configured_items
    projected = item_config(hass, config)
    assert item_config(hass, projected) == projected
    changed = deepcopy(projected)
    changed["members"]["person.example_pet"]["trackers"].remove(ids["assigned"])
    restored = item_config(hass, changed)
    assert ids["assigned"] in restored["items"]
    assert restored["members"][ids["assigned"]] == preferences
    assert restored["findmy_accounts"] == projected["findmy_accounts"]
    assert item_config(hass, restored) == restored


@pytest.mark.parametrize("case", ["unselected_person", "active_source_only", "same_name_only", "item_self_assignment"])
def test_only_selected_person_explicit_trackers_suppress_items(hass, configured_items, case):
    config, ids, _, _ = configured_items
    if case == "unselected_person":
        config["people"] = []
    else:
        config["members"]["person.example_pet"]["trackers"] = []
    if case == "active_source_only":
        hass.states.async_set("person.example_pet", "home", {"source": ids["assigned"]})
    elif case == "same_name_only":
        hass.states.async_set("person.example_pet", "home", {"friendly_name": "Example"})
    elif case == "item_self_assignment":
        config["people"] = []
    result = item_config(hass, config)
    assert ids["assigned"] in result["items"]


@pytest.mark.parametrize("field,kind", [("pets", "pet"), ("people_trackers", "person")])
def test_tracker_only_members_keep_their_existing_projection_and_settings(hass, configured_items, field, kind):
    config, ids, _, _ = configured_items
    config["people"] = []
    config[field] = [ids["assigned"]]
    previous = {"kind": kind, "trackers": [ids["assigned"]], "additional_residences": [],
                "picture_id": "c" * 32, "show_on_map": False}
    config["members"][ids["assigned"]] = deepcopy(previous)
    result = item_config(hass, config)
    assert ids["assigned"] not in result["items"]
    assert result["members"][ids["assigned"]] == previous
    assert result[field] == [ids["assigned"]]


def test_assignment_without_previous_item_preferences_does_not_create_a_standalone_member(hass, configured_items):
    config, ids, _, _ = configured_items
    config["items"].remove(ids["assigned"])
    config["members"].pop(ids["assigned"])
    result = item_config(hass, config)
    assert ids["assigned"] not in result["items"]
    assert ids["assigned"] not in result["members"]
    assert ids["assigned"] in result["members"]["person.example_pet"]["trackers"]


def test_automatic_item_preferences_do_not_retain_deselected_native_items(hass, configured_items):
    config, ids, _, _ = configured_items
    config["findmy_accounts"]["a" * 32]["items"].pop("assigned")
    result = item_config(hass, config)
    assert ids["assigned"] not in result["items"]
    assert ids["assigned"] not in result["members"]


@pytest.mark.parametrize("route", ["details", "add"])
async def test_real_options_flow_saves_person_assignment_without_duplicate_item(hass, configured_items, route):
    from unittest.mock import patch
    from homeassistant.components.person import async_create_person, entities_in_person
    from homeassistant.data_entry_flow import FlowResultType
    from homeassistant.setup import async_setup_component
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    config, ids, external, preferences = configured_items
    phone = "device_tracker.example_phone"
    native = ids["assigned"]
    person = "person.example_pet"
    config["members"][person]["trackers"] = [phone]
    assert await async_setup_component(hass, "zone", {})
    assert await async_setup_component(hass, "person", {"person": []})
    for entity in [phone, *ids.values(), external]:
        hass.states.async_set(entity, "not_home", {"source_type": "gps"})
    await async_create_person(hass, "Example Pet", device_trackers=[phone, native] if route == "details" else [phone])
    assert hass.states.get(person)
    entry = MockConfigEntry(domain="homecircle", title="HomeCircle", data=config)
    entry.add_to_hass(hass)
    manager = hass.config_entries.options
    result = await manager.async_init(entry.entry_id)
    with (
        patch.object(hass.config_entries, "async_schedule_reload") as reload,
        patch("custom_components.homecircle.findmy_flow.FindMySetup.create") as authenticate,
        patch("custom_components.homecircle.findmy_flow.Vault.save_account") as store,
    ):
        result = await manager.async_configure(result["flow_id"], {"next_step_id": "tracker_member_choice" if route == "details" else "add_tracker_choice"})
        if route == "details":
            result = await manager.async_configure(result["flow_id"], {"member": person, "setting": "details"})
        else:
            result = await manager.async_configure(result["flow_id"], {"person": person})
            result = await manager.async_configure(result["flow_id"], {"add_tracker": native, "add_tracker_kind": "pet"})
        assert result["step_id"] == "member"
        result = await manager.async_configure(result["flow_id"], {"trackers": [phone, native], "kind": "pet"})
        assert result["step_id"] == "confirm"
        result = await manager.async_configure(result["flow_id"], {"next_step_id": "confirm_save"})
        assert result["type"] is FlowResultType.CREATE_ENTRY
        authenticate.assert_not_called()
        store.assert_not_called()
        reload.assert_called_once()
    saved = dict(entry.options)
    assert saved["members"][person]["trackers"] == [phone, native]
    assert saved["members"][person]["kind"] == "pet"
    assert saved["members"][person]["pet_home_minutes"] == 120
    assert saved["members"][person]["pet_away_minutes"] == 15
    assert native not in saved["items"] and native not in saved["members"]
    assert {ids["backpack"], ids["vehicle"], external} == set(saved["items"])
    account_items = saved["findmy_accounts"]["a" * 32]["items"]
    assert set(account_items) == {"assigned", "backpack", "vehicle"}
    assert account_items["assigned"]["display_preferences"] == preferences
    assert set(entities_in_person(hass, person)) == {phone, native}
    assert item_config(hass, saved) == saved
    # Unassigning only in HomeCircle returns the standalone display and settings.
    unassigned = deepcopy(saved)
    unassigned["members"][person]["trackers"] = [phone]
    restored = item_config(hass, unassigned)
    assert native in restored["items"] and restored["members"][native] == preferences
    assert set(entities_in_person(hass, person)) == {phone, native}


async def test_projection_does_not_bypass_duplicate_person_validation(hass, configured_items):
    from unittest.mock import patch
    from homeassistant.data_entry_flow import FlowResultType
    from homeassistant.setup import async_setup_component
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    config, ids, external, _ = configured_items
    assert await async_setup_component(hass, "zone", {})
    for entity in ["device_tracker.example_phone", *ids.values(), external]:
        hass.states.async_set(entity, "not_home", {"source_type": "gps"})
    for person in ("person.example_pet", "person.example_other"):
        hass.states.async_set(person, "not_home", {})
    config["people"].append("person.example_other")
    config["members"]["person.example_other"] = {
        "kind": "person", "trackers": [ids["assigned"]], "additional_residences": [],
    }
    entry = MockConfigEntry(domain="homecircle", title="HomeCircle", data=config)
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    flow = hass.config_entries.options._progress[result["flow_id"]]
    with patch.object(hass.config_entries, "async_update_entry") as update:
        result = await flow.async_step_confirm_save()
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "entities_changed"}
        update.assert_not_called()
    hass.config_entries.options.async_abort(flow.flow_id)


def test_removing_person_selection_restores_item_preferences_from_account_metadata(hass, configured_items):
    config, ids, _, preferences = configured_items
    saved = item_config(hass, config)
    saved["people"] = []
    saved["members"].pop("person.example_pet")
    restored = item_config(hass, saved)
    assert ids["assigned"] in restored["items"]
    assert restored["members"][ids["assigned"]] == preferences
    assert item_config(hass, restored) == restored
