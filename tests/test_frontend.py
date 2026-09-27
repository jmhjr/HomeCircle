"""HA websocket authorization and owned-resource lifecycle acceptance."""

from unittest.mock import patch

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.resources import ResourceYAMLCollection

from custom_components.homecircle import frontend
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
    # Even an otherwise readable person cannot expose a denied supporting input.
    permissions = type(hass_admin_user.permissions)
    with patch.object(
        permissions,
        "check_entity",
        side_effect=lambda entity, policy: entity != "zone.example_residence",
    ):
        await client.send_json({"id": 2, "type": "homecircle/snapshot"})
        denied = await client.receive_json()
        assert denied["error"]["code"] == "unauthorized"
        assert "result" not in denied
    await hass.config_entries.async_unload(entry.entry_id)
    await client.send_json({"id": 3, "type": "homecircle/snapshot"})
    assert (await client.receive_json())["error"]["code"] == "not_ready"


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
