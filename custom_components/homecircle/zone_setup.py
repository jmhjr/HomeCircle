"""Create user-requested Home Assistant zones during HomeCircle setup."""

import math

from homeassistant.components.zone import DATA_ZONE_STORAGE_COLLECTION
from homeassistant.helpers import entity_registry as er


def zone_error(hass, name: str, location: dict) -> str | None:
    """Validate the fields HA needs without changing its zone collection."""
    if (
        not isinstance(name, str)
        or not name.strip()
        or len(name.strip()) > 60
        or any(ord(char) < 32 for char in name)
    ):
        return "invalid_zone_name"
    if any(
        state.name.casefold() == name.strip().casefold()
        for state in hass.states.async_all("zone")
    ):
        return "zone_already_exists"
    if not isinstance(location, dict):
        return "invalid_zone_location"
    for key, lower, upper in (
        ("latitude", -90, 90),
        ("longitude", -180, 180),
        ("radius", 1, 100000),
    ):
        value = location.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return "invalid_zone_location"
        if not math.isfinite(value) or not lower <= value <= upper:
            return "invalid_zone_location"
    return None


async def async_create_zone(hass, name: str, location: dict) -> str | None:
    """Return the actual entity ID, including any registry collision suffix."""
    collection = hass.data.get(DATA_ZONE_STORAGE_COLLECTION)
    if collection is None:
        return None
    item = await collection.async_create_item(
        {
            "name": name.strip(),
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "radius": location["radius"],
            "passive": False,
        }
    )
    return er.async_get(hass).async_get_entity_id("zone", "zone", item["id"])
