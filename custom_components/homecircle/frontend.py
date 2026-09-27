"""Versioned static code and owned Lovelace resource lifecycle (no member data)."""

from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.helpers.storage import Store

URL = "/homecircle_static/homecircle-card.js"
VERSION = "0.1.0-beta.1"
KEY = "homecircle_frontend"


async def async_register(hass):
    state = hass.data.setdefault(KEY, {})
    if not state.get("static"):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    "/homecircle_static", str(Path(__file__).parent / "frontend"), False
                )
            ]
        )
        state["static"] = True
    resources = hass.data[LOVELACE_DATA].resources
    if not isinstance(resources, ResourceStorageCollection):
        # Never rewrite a user's YAML resource collection.
        return
    await resources.async_get_info()
    store = Store(hass, 1, KEY)
    owned = await store.async_load() or {}
    items = resources.async_items()
    item = next(
        (
            item
            for item in items
            if item["id"] == owned.get("id") and item["url"].split("?")[0] == URL
        ),
        None,
    )
    if item:
        await resources.async_update_item(
            item["id"], {"url": f"{URL}?v={VERSION}", "res_type": "module"}
        )
    elif any(item["url"].split("?")[0] == URL for item in items):
        return  # Existing user-owned registration is not ours to change/remove.
    else:
        item = await resources.async_create_item(
            {"url": f"{URL}?v={VERSION}", "res_type": "module"}
        )
        await store.async_save({"id": item["id"]})
    state["owned_id"] = item["id"]


async def async_unregister(hass):
    owned_id = hass.data.get(KEY, {}).pop("owned_id", None)
    resources = hass.data[LOVELACE_DATA].resources
    if owned_id and isinstance(resources, ResourceStorageCollection):
        await resources.async_get_info()
        item = next(
            (item for item in resources.async_items() if item["id"] == owned_id), None
        )
        if item and item["url"].split("?")[0] == URL:
            await resources.async_delete_item(owned_id)
        await Store(hass, 1, KEY).async_remove()
