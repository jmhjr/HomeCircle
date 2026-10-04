"""HA websocket authorization and owned-resource lifecycle acceptance."""

from unittest.mock import patch
from types import SimpleNamespace

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.resources import ResourceYAMLCollection
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

from custom_components.homecircle import dashboard_setup, frontend
from custom_components.homecircle.api import (
    allowed_picture,
    location_source_label,
    snapshot,
)
from custom_components.homecircle.tracker_providers import ProviderHealth
from test_config_flow import start, finish


async def setup(hass, household):
    result = await finish(hass, await start(hass, household))
    await hass.async_block_till_done()
    return result["result"]


async def test_first_setup_creates_one_dashboard_and_card(hass, household):
    entry = await setup(hass, household)
    dashboards = hass.data[LOVELACE_DATA].dashboards
    assert "dashboard-homecircle" in dashboards
    config = await dashboards["dashboard-homecircle"].async_load(False)
    assert config == {
        "views": [
            {
                "title": "HomeCircle",
                "type": "panel",
                "cards": [
                    {
                        "type": "custom:homecircle-card",
                        "fill_screen": True,
                        "map_tiles": "osm",
                    }
                ],
            }
        ]
    }
    assert await hass.config_entries.async_reload(entry.entry_id)
    assert [path for path in dashboards if path == "dashboard-homecircle"] == [
        "dashboard-homecircle"
    ]
    await hass.config_entries.async_remove(entry.entry_id)
    assert "dashboard-homecircle" not in dashboards


async def test_edited_homecircle_dashboard_survives_integration_removal(
    hass, household
):
    entry = await setup(hass, household)
    dashboards = hass.data[LOVELACE_DATA].dashboards
    dashboard = dashboards["dashboard-homecircle"]
    config = await dashboard.async_load(False)
    config["views"][0]["cards"].append(
        {"type": "entities", "entities": ["person.example_member"]}
    )
    await dashboard.async_save(config)
    await hass.config_entries.async_remove(entry.entry_id)
    assert "dashboard-homecircle" in dashboards
    assert await dashboard.async_load(False) == config


async def test_existing_card_dashboard_is_left_unchanged(hass, household):
    assert await async_setup_component(hass, "lovelace", {"lovelace": {}})
    collection = dashboard_setup._active_collection(hass)
    assert collection is not None
    await collection.async_create_item(
        {"title": "Family", "url_path": "dashboard-family", "show_in_sidebar": True}
    )
    existing = hass.data[LOVELACE_DATA].dashboards["dashboard-family"]
    config = {
        "views": [
            {
                "title": "Family",
                "cards": [
                    {"type": "entities", "entities": ["person.example_member"]},
                    {"type": "custom:homecircle-card"},
                ],
            }
        ]
    }
    await existing.async_save(config)
    await setup(hass, household)
    assert "dashboard-homecircle" not in hass.data[LOVELACE_DATA].dashboards
    assert await existing.async_load(False) == config


async def test_existing_named_homecircle_dashboard_is_not_replaced(hass, household):
    assert await async_setup_component(hass, "lovelace", {"lovelace": {}})
    collection = dashboard_setup._active_collection(hass)
    assert collection is not None
    await collection.async_create_item(
        {
            "title": "HomeCircle",
            "url_path": "dashboard-family-map",
            "show_in_sidebar": True,
        }
    )
    existing = hass.data[LOVELACE_DATA].dashboards["dashboard-family-map"]
    config = {"views": [{"title": "Household", "cards": []}]}
    await existing.async_save(config)
    await setup(hass, household)
    assert "dashboard-homecircle" not in hass.data[LOVELACE_DATA].dashboards
    assert await existing.async_load(False) == config


async def test_snapshot_authorization_and_projection(
    hass, household, hass_ws_client, hass_admin_user
):
    entry = await setup(hass, household)
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "homecircle/snapshot"})
    result = await client.receive_json()
    assert result["success"]
    data = result["result"]
    assert data["schema_version"] == 1
    assert data["counts"]["home"] == 2
    assert data["members"][0]["location"]["evidence"]["reported_at"] is None
    assert data["members"][0]["location"]["evidence"]["source_label"].startswith(
        "Tracker:"
    )
    assert data["members"][1]["location"] is None
    assert "states" not in data and "config" not in data
    assert "active_source_entity" not in data["members"][0]
    assert data["members"][0]["picture"] is None
    hass.states.async_set(
        "person.example_member",
        "home",
        {
            "source": "device_tracker.example_phone",
            ATTR_LATITUDE: 0.0,
            ATTR_LONGITUDE: 0.0,
            "entity_picture": "/api/image/serve/example/512x512",
        },
    )
    await hass.async_block_till_done()
    await client.send_json({"id": 2, "type": "homecircle/snapshot"})
    portrait_result = await client.receive_json()
    assert portrait_result["result"]["members"][0]["picture"] == (
        "/api/image/serve/example/512x512"
    )
    hass.states.async_set(
        "person.example_member",
        "home",
        {
            "source": "device_tracker.example_phone",
            ATTR_LATITUDE: 0.0,
            ATTR_LONGITUDE: 0.0,
        },
    )
    hass.states.async_set(
        "device_tracker.example_phone",
        "home",
        {
            "source_type": "gps",
            ATTR_LATITUDE: 0.0,
            ATTR_LONGITUDE: 0.0,
            "entity_picture": "https://www.life360.com/img/user_images/example/portrait.jpeg?fd=2",
        },
    )
    await hass.async_block_till_done()
    await client.send_json({"id": 3, "type": "homecircle/snapshot"})
    assert (await client.receive_json())["result"]["members"][0]["picture"] == (
        "https://www.life360.com/img/user_images/example/portrait.jpeg?fd=2"
    )
    # Even an otherwise readable person cannot expose a denied supporting input.
    permissions = type(hass_admin_user.permissions)
    with patch.object(
        permissions,
        "check_entity",
        side_effect=lambda entity, policy: entity != "zone.example_residence",
    ):
        await client.send_json({"id": 4, "type": "homecircle/snapshot"})
        denied = await client.receive_json()
        assert denied["error"]["code"] == "unauthorized"
        assert "result" not in denied
    await hass.config_entries.async_unload(entry.entry_id)
    await client.send_json({"id": 5, "type": "homecircle/snapshot"})
    assert (await client.receive_json())["error"]["code"] == "not_ready"


async def test_location_source_label_follows_actual_map_source(hass, household):
    entry = await setup(hass, household)
    hass.states.async_set(
        "device_tracker.example_phone",
        "home",
        {
            "friendly_name": "Example Phone",
            "source_type": "gps",
            ATTR_LATITUDE: 0.0,
            ATTR_LONGITUDE: 0.0,
        },
    )
    await hass.async_block_till_done()
    evidence = snapshot(entry.runtime_data)["members"][0]["location"]["evidence"]
    assert evidence["source_label"] == "Tracker: Example Phone"
    assert evidence["reported_at"] is None

    assert location_source_label(
        entry.runtime_data, "person.example_member"
    ).startswith("HA Person:")


async def test_tracker_label_uses_registered_integration_not_friendly_name(
    hass, household
):
    entry = await setup(hass, household)
    registry = er.async_get(hass)
    pet = registry.async_get_or_create("device_tracker", "life360_pet", "ruby")
    hass.states.async_set(pet.entity_id, "home", {"friendly_name": "Ruby"})
    entry.runtime_data.states[pet.entity_id] = hass.states.get(pet.entity_id)
    assert location_source_label(entry.runtime_data, pet.entity_id, registry) == (
        "Tracker: Ruby · Life360 Pet GPS"
    )

    phone = registry.async_get_or_create("device_tracker", "life360", "example_phone")
    hass.states.async_set(
        phone.entity_id, "home", {"friendly_name": "Life360 Example Phone"}
    )
    entry.runtime_data.states[phone.entity_id] = hass.states.get(phone.entity_id)
    assert location_source_label(entry.runtime_data, phone.entity_id, registry) == (
        "Tracker: Life360 Example Phone"
    )


async def test_provider_status_is_visible_only_to_admin(
    hass, household, hass_ws_client, hass_read_only_access_token
):
    entry = await setup(hass, household)
    runtime = entry.runtime_data
    runtime.config["life360_account"] = {
        "method": "token",
        "secret": "example-private-token",
    }
    runtime.managed_trackers["life360"] = SimpleNamespace(
        health_snapshot=lambda: ProviderHealth(state="auth_required")
    )

    admin = await hass_ws_client(hass)
    await admin.send_json({"id": 1, "type": "homecircle/snapshot"})
    admin_result = (await admin.receive_json())["result"]
    assert admin_result["provider_alerts"] == [
        {"name": "Life360", "state": "auth_required"}
    ]
    assert "example-private-token" not in str(admin_result)

    viewer = await hass_ws_client(hass, hass_read_only_access_token)
    try:
        await viewer.send_json({"id": 1, "type": "homecircle/snapshot"})
        viewer_result = await viewer.receive_json()
        assert viewer_result["success"]
        assert viewer_result["result"]["provider_alerts"] == []
    finally:
        runtime.managed_trackers.clear()
        runtime.config.pop("life360_account")


async def test_pet_person_requires_permission_to_read_tracker(
    hass, household, hass_ws_client, hass_admin_user
):
    from homeassistant.components.person import async_create_person
    from homeassistant.setup import async_setup_component

    pet = "device_tracker.example_pet"
    hass.states.async_set(pet, "home", {"source_type": "gps"})
    assert await async_setup_component(hass, "person", {"person": []})
    await async_create_person(hass, "Example Pet")
    pet_person = next(
        state.entity_id
        for state in hass.states.async_all("person")
        if state.name == "Example Pet"
    )
    result = await start(
        hass,
        {"people": [pet_person], "primary_home": household["primary_home"]},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"tracker": pet}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"kind": "pet"}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["step_id"] == "confirm"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "confirm_save"}
    )
    await hass.async_block_till_done()
    client = await hass_ws_client(hass)
    permissions = type(hass_admin_user.permissions)
    with patch.object(
        permissions,
        "check_entity",
        side_effect=lambda entity, policy: entity != pet,
    ):
        await client.send_json({"id": 1, "type": "homecircle/snapshot"})
        result = await client.receive_json()
    assert result["error"]["code"] == "unauthorized"
    assert "result" not in result


def test_portraits_use_ha_or_life360_images_only():
    assert allowed_picture("/api/image/serve/example/512x512")
    assert allowed_picture("/local/portrait.png")
    assert allowed_picture(
        "https://www.life360.com/img/user_images/example/portrait.jpeg?fd=2"
    )
    assert allowed_picture("https://life360-images-pub.life360.com/example/pet.jpeg")
    assert allowed_picture("https://example.com/portrait.png") is None
    assert (
        allowed_picture("https://www.life360.com.evil.test/img/user_images/x") is None
    )
    assert allowed_picture("http://www.life360.com/img/user_images/x") is None
    assert (
        allowed_picture("https://life360-images-pub.life360.com.evil.test/pet.jpeg")
        is None
    )
    assert (
        allowed_picture("https://www.life360.com/img/user_images/%2e%2e/other.jpeg")
        is None
    )
    assert (
        allowed_picture("https://life360-images-pub.life360.com/../other.jpeg") is None
    )
    assert allowed_picture("//www.life360.com/img/user_images/x") is None
    assert allowed_picture("/local/portrait.png\nHost: example.com") is None


async def test_owned_resources_reload_unload_and_preserve_others(hass, household):
    entry = await setup(hass, household)
    resources = hass.data[LOVELACE_DATA].resources
    unrelated = await resources.async_create_item(
        {"url": "/local/example-card.js", "res_type": "module"}
    )
    for _ in range(2):
        await frontend.async_register(hass)
        ours = [
            item
            for item in resources.async_items()
            if item["url"].startswith(frontend.URL)
        ]
        assert len(ours) == 1
    assert await hass.config_entries.async_reload(entry.entry_id)
    ours = [
        item for item in resources.async_items() if item["url"].startswith(frontend.URL)
    ]
    assert len(ours) == 1
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert resources.async_items() == [unrelated]
    # A manually created matching resource remains user-owned.
    manual = await resources.async_create_item(
        {"url": frontend.URL, "res_type": "module"}
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert manual in resources.async_items()
    await hass.config_entries.async_remove(entry.entry_id)
    assert manual in resources.async_items()


async def test_remove_unloaded_entry_cleans_persisted_resource(hass, household):
    entry = await setup(hass, household)
    resources = hass.data[LOVELACE_DATA].resources
    assert await hass.config_entries.async_unload(entry.entry_id)
    # Simulate an owned registration left by a failed setup or interrupted unload.
    await frontend.async_register(hass)
    owned = next(
        item for item in resources.async_items() if item["url"].startswith(frontend.URL)
    )
    hass.data[frontend.KEY].pop("owned_id")  # Force persisted-ID recovery.
    unrelated = await resources.async_create_item(
        {"url": "/local/example-card.js", "res_type": "module"}
    )
    assert (await hass.config_entries.async_remove(entry.entry_id))[
        "require_restart"
    ] is False
    assert owned not in resources.async_items()
    assert resources.async_items() == [unrelated]


async def test_reload_marker_cleans_resource_when_setup_does_not_follow(
    hass, household
):
    entry = await setup(hass, household)
    resources = hass.data[LOVELACE_DATA].resources
    assert any(item["url"].startswith(frontend.URL) for item in resources.async_items())
    frontend.preserve_for_reload(hass, entry.entry_id)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert not any(
        item["url"].startswith(frontend.URL) for item in resources.async_items()
    )


async def test_flagged_reload_failure_cleans_owned_resource(hass, household):
    entry = await setup(hass, household)
    resources = hass.data[LOVELACE_DATA].resources
    assert any(item["url"].startswith(frontend.URL) for item in resources.async_items())
    frontend.preserve_for_reload(hass, entry.entry_id)
    with patch.object(
        frontend, "async_register", side_effect=RuntimeError("test setup failure")
    ):
        assert not await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert not any(
        item["url"].startswith(frontend.URL) for item in resources.async_items()
    )


async def test_yaml_resources_are_never_rewritten(hass, household):
    entry = await setup(hass, household)
    await hass.config_entries.async_unload(entry.entry_id)
    collection = ResourceYAMLCollection(
        [{"url": "/local/example.js", "type": "module"}]
    )
    hass.data[LOVELACE_DATA].resources = collection
    await frontend.async_register(hass)
    await frontend.async_unregister(hass)
    assert collection.async_items() == [{"url": "/local/example.js", "type": "module"}]


async def test_per_source_report_sensor_requires_read_permission(
    hass, household, hass_ws_client, hass_admin_user
):
    from copy import deepcopy

    entry = await setup(hass, household)
    hass.states.async_set("sensor.example_report", "2026-01-01T00:00:00+00:00")
    config = deepcopy(dict(entry.data))
    config["members"][household["people"][0]]["location_reports"] = {
        "device_tracker.example_phone": "sensor.example_report"
    }
    hass.config_entries.async_update_entry(entry, data=config)
    assert await hass.config_entries.async_reload(entry.entry_id)
    client = await hass_ws_client(hass)
    with patch.object(
        type(hass_admin_user.permissions),
        "check_entity",
        side_effect=lambda entity, policy: entity != "sensor.example_report",
    ):
        await client.send_json({"id": 1, "type": "homecircle/snapshot"})
        result = await client.receive_json()
        assert result["error"]["code"] == "unauthorized"
        assert "result" not in result
