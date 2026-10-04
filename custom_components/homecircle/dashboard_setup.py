"""Create a first-run Lovelace dashboard without changing existing dashboards."""

from copy import deepcopy
import logging

from homeassistant.components.frontend import async_panel_exists
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.dashboard import (
    ConfigNotFound,
    DashboardsCollection,
    LovelaceStorage,
)
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)
_CARD_TYPE = "custom:homecircle-card"
_TITLE = "HomeCircle"
_PATH = "dashboard-homecircle"
_STORE_KEY = "homecircle_dashboard"
_DASHBOARD_CONFIG = {
    "views": [
        {
            "title": _TITLE,
            "type": "panel",
            "cards": [{"type": _CARD_TYPE, "fill_screen": True, "map_tiles": "osm"}],
        }
    ]
}


def _has_card(value):
    if isinstance(value, dict):
        return value.get("type") == _CARD_TYPE or any(
            _has_card(child) for child in value.values()
        )
    if isinstance(value, list):
        return any(_has_card(child) for child in value)
    return False


def _active_collection(hass):
    """Use Lovelace's loaded collection so its panel listener stays in sync."""
    command = hass.data.get("websocket_api", {}).get("lovelace/dashboards/list")
    owner = getattr(command[0], "__self__", None) if command else None
    collection = getattr(owner, "storage_collection", None)
    return collection if isinstance(collection, DashboardsCollection) else None


async def async_ensure_dashboard(hass):
    """Add one HomeCircle dashboard after first setup; preserve every existing view."""
    if hass.config.recovery_mode:
        return None
    lovelace = hass.data.get(LOVELACE_DATA)
    collection = _active_collection(hass)
    if (
        lovelace is None
        or not isinstance(lovelace.resources, ResourceStorageCollection)
        or collection is None
    ):
        _LOGGER.info("HomeCircle dashboard creation is unavailable in this HA setup")
        return None

    for path, dashboard in lovelace.dashboards.items():
        metadata = dashboard.config or {}
        if (
            path == _PATH
            or metadata.get("title", "").strip().casefold() == _TITLE.casefold()
        ):
            return path
        try:
            config = await dashboard.async_load(False)
        except ConfigNotFound:
            continue
        except HomeAssistantError:
            _LOGGER.warning(
                "Could not inspect a dashboard; leaving dashboards unchanged"
            )
            return None
        if _has_card(config):
            return path

    path = _PATH
    if async_panel_exists(hass, path):
        _LOGGER.info(
            "HomeCircle dashboard path is in use; leaving dashboards unchanged"
        )
        return None

    item = await collection.async_create_item(
        {
            "title": _TITLE,
            "url_path": path,
            "icon": "mdi:account-group",
            "show_in_sidebar": True,
        }
    )
    try:
        created = lovelace.dashboards[path]
        if not isinstance(created, LovelaceStorage):
            raise HomeAssistantError("Created dashboard is not storage managed")
        await created.async_save(deepcopy(_DASHBOARD_CONFIG))
        await Store(hass, 1, _STORE_KEY).async_save({"id": item["id"]})
    except Exception:
        await collection.async_delete_item(item["id"])
        raise
    _LOGGER.info("Created HomeCircle dashboard at /%s", path)
    return path


async def async_remove_untouched_dashboard(hass):
    """Remove only the dashboard HomeCircle created if nobody edited it."""
    store = Store(hass, 1, _STORE_KEY)
    owned = await store.async_load() or {}
    item_id = owned.get("id")
    if not item_id:
        return
    collection = _active_collection(hass)
    lovelace = hass.data.get(LOVELACE_DATA)
    if collection is None or lovelace is None:
        return
    item = next(
        (item for item in collection.async_items() if item["id"] == item_id), None
    )
    dashboard = lovelace.dashboards.get(_PATH)
    if (
        item
        and dashboard
        and all(
            (
                item.get("url_path") == _PATH,
                item.get("title") == _TITLE,
                item.get("icon") == "mdi:account-group",
                item.get("show_in_sidebar") is True,
            )
        )
    ):
        try:
            config = await dashboard.async_load(False)
        except ConfigNotFound:
            config = None
        if config == _DASHBOARD_CONFIG:
            await collection.async_delete_item(item_id)
    await store.async_remove()
