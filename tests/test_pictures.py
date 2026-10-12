"""Native HA uploads and per-tracker picture persistence, without private files."""

from io import BytesIO
from PIL import Image
from aiohttp import FormData
from homeassistant.data_entry_flow import FlowResultType
from custom_components.homecircle.api import snapshot
from custom_components.homecircle.pictures import picture_url
from test_config_flow import legacy_tracker_entry, start_options, configure_empty

TRACKER = "device_tracker.example_picture_tag"


async def tracker(hass):
    hass.states.async_set(TRACKER, "home", {"source_type": "gps"})
    return await legacy_tracker_entry(hass, TRACKER)


async def picture_flow(hass, entry):
    manager = hass.config_entries.options
    flow = await start_options(manager, entry, "tracker_member_choice")
    return await manager.async_configure(
        flow["flow_id"], {"member": TRACKER, "setting": "picture"}
    )


def test_picture_urls_accept_only_ha_image_ids():
    assert picture_url("a" * 32) == f"/api/image/serve/{'a' * 32}/512x512"
    for bad in (None, "", "https://example.org/photo.png", "../original", "a" * 33):
        assert picture_url(bad) is None


async def test_native_upload_apply_preserve_and_remove(hass, hass_client):
    entry = await tracker(hass)
    client = await hass_client()
    buffer = BytesIO()
    Image.new("RGB", (8, 8), "white").save(buffer, format="PNG")
    data = FormData()
    data.add_field(
        "file",
        buffer.getvalue(),
        filename="example-picture.png",
        content_type="image/png",
    )
    response = await client.post("/api/image/upload", data=data)
    assert response.status == 200
    image_id = (await response.json())["id"]
    flow = await picture_flow(hass, entry)
    flow = await hass.config_entries.options.async_configure(
        flow["flow_id"], {"picture_id": image_id}
    )
    await hass.async_block_till_done()
    assert flow["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options["members"][TRACKER]["picture_id"] == image_id
    assert snapshot(entry.runtime_data)["members"][0]["picture"] == picture_url(
        image_id
    )
    thumbnail = await client.get(picture_url(image_id))
    assert thumbnail.status == 200
    manager = hass.config_entries.options
    flow = await start_options(manager, entry, "tracker_member_choice")
    flow = await manager.async_configure(
        flow["flow_id"], {"member": TRACKER, "setting": "details"}
    )
    flow = await configure_empty(manager, flow)
    flow = await configure_empty(manager, flow)
    await hass.async_block_till_done()
    assert entry.options["members"][TRACKER]["picture_id"] == image_id
    flow = await picture_flow(hass, entry)
    flow = await manager.async_configure(flow["flow_id"], {"picture_id": ""})
    await hass.async_block_till_done()
    assert "picture_id" not in entry.options["members"][TRACKER]
    assert snapshot(entry.runtime_data)["members"][0]["picture"] is None
    # Clearing a mapping does not delete HA's reusable uploaded asset.
    assert image_id in hass.data["image_upload"].data


async def test_bad_or_missing_image_reference_does_not_change_settings(hass):
    entry = await tracker(hass)
    flow = await picture_flow(hass, entry)
    for value in ("https://example.org/photo.png", "a" * 32):
        flow = await hass.config_entries.options.async_configure(
            flow["flow_id"], {"picture_id": value}
        )
        assert flow["errors"] == {"base": "invalid_tracker_picture"}
    assert "picture_id" not in entry.data["members"][TRACKER]
