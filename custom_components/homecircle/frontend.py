"""Versioned static code and owned Lovelace resource lifecycle (no member data)."""

from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.helpers.storage import Store

URL = "/homecircle_static/homecircle-card.js"
VERSION = "0.1.0-beta.11"
KEY = "homecircle_frontend"
RELOAD_ENTRY = "reload_entry"


def preserve_for_reload(hass, entry_id):
    """Keep the owned resource while a saved selection reloads its entry."""
    hass.data.setdefault(KEY, {})[RELOAD_ENTRY] = entry_id


def consume_reload_preservation(hass, entry_id):
    """Consume the one-shot marker set by the HomeCircle selection flow."""
    state = hass.data.get(KEY, {})
    if state.get(RELOAD_ENTRY) != entry_id:
        return False
    state.pop(RELOAD_ENTRY)
    return True


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
    state = hass.data.get(KEY, {})
    owned_id = state.pop("owned_id", None)
    resources = hass.data[LOVELACE_DATA].resources
    if not isinstance(resources, ResourceStorageCollection):
        return  # Leave storage ownership intact if resources are YAML-managed.
    store = Store(hass, 1, KEY)
    if not owned_id:
        owned_id = (await store.async_load() or {}).get("id")
    if owned_id:
        await resources.async_get_info()
        item = next(
            (item for item in resources.async_items() if item["id"] == owned_id), None
        )
        if item and item["url"].split("?")[0] == URL:
            await resources.async_delete_item(owned_id)
        await store.async_remove()
