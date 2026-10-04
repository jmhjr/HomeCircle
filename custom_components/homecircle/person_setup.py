"""Create and update Home Assistant Person records selected in setup."""

from homeassistant.components.person import DOMAIN as PERSON_DOMAIN
from homeassistant.components.person import persons_with_entity
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component


def person_name_error(hass, name):
    if (
        not isinstance(name, str)
        or not name.strip()
        or len(name.strip()) > 60
        or any(ord(char) < 32 for char in name)
    ):
        return "invalid_person_name"
    if any(
        state.name.casefold() == name.strip().casefold()
        for state in hass.states.async_all("person")
    ):
        return "person_already_exists"
    return None


def editable_person_collection(hass, person_id):
    """Return HA's storage collection only for an editable Person entity."""
    data = hass.data.get(PERSON_DOMAIN)
    if data is None:
        return None
    collection, component = data[1], data[2]
    entity = component.get_entity(person_id)
    if entity is None or not entity.editable:
        return None
    return collection, entity.unique_id


def has_person_entity(hass, person_id):
    """Distinguish real HA Person entities from synthetic state fixtures."""
    data = hass.data.get(PERSON_DOMAIN)
    return data is not None and data[2].get_entity(person_id) is not None


async def async_create_person(hass, name):
    """Return the entity ID created by HA, including any collision suffix."""
    if PERSON_DOMAIN not in hass.data:
        if not await async_setup_component(hass, PERSON_DOMAIN, {}):
            return None
    data = hass.data.get(PERSON_DOMAIN)
    if data is None:
        return None
    item = await data[1].async_create_item(
        {"name": name.strip(), "user_id": None, "device_trackers": []}
    )
    return er.async_get(hass).async_get_entity_id(
        PERSON_DOMAIN, PERSON_DOMAIN, item["id"]
    )


def tracker_link_error(hass, person_id, tracker_id):
    """Reject associations HA cannot save or that belong to another Person."""
    if editable_person_collection(hass, person_id) is None:
        return "person_not_editable"
    if any(other != person_id for other in persons_with_entity(hass, tracker_id)):
        return "tracker_linked_elsewhere"
    return None


async def async_link_tracker(hass, person_id, tracker_id):
    """Add one tracker without replacing a Person's other HA tracker links."""
    target = editable_person_collection(hass, person_id)
    if target is None:
        raise ValueError("Person is not editable")
    collection, item_id = target
    item = next(item for item in collection.async_items() if item["id"] == item_id)
    linked = item["device_trackers"]
    if tracker_id not in linked:
        await collection.async_update_item(
            item_id, {"device_trackers": [*linked, tracker_id]}
        )
