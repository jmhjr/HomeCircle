"""HA websocket authorization and owned-resource lifecycle acceptance."""

from unittest.mock import patch
from types import SimpleNamespace

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.resources import ResourceYAMLCollection
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE

from custom_components.homecircle import frontend
from custom_components.homecircle.api import allowed_picture
from custom_components.homecircle.tracker_providers import ProviderHealth
from test_config_flow import start, finish


async def setup(hass, household):
    result = await finish(hass, await start(hass, household))
    await hass.async_block_till_done()
    return result["result"]


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


async def test_tracker_only_pet_requires_permission_to_read_tracker(
    hass, household, hass_ws_client, hass_admin_user
):
    pet = "device_tracker.example_pet"
    hass.states.async_set(pet, "home", {"source_type": "gps"})
    result = await start(
        hass,
        {"people": [], "pets": [pet], "primary_home": household["primary_home"]},
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
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
