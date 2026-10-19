"""Project explicitly configured Find My items without adding to family counts."""

from copy import deepcopy
from homeassistant.helpers import entity_registry as er
from .const import (
    CONF_FINDMY_ACCOUNTS,
    CONF_ITEMS,
    CONF_MEMBERS,
    CONF_TRACKER_PEOPLE,
    CONF_PETS,
)
from .findmy_provider import tracker_unique_id


def item_config(hass, config):
    result = deepcopy(dict(config))
    registry = er.async_get(hass)
    saved_members = deepcopy(result.get(CONF_MEMBERS, {}))
    existing = []
    for entity_id in result.get(CONF_ITEMS, []):
        entity = registry.async_get(entity_id)
        if (
            entity
            and entity.platform == "homecircle"
            and entity.unique_id.startswith("homecircle_findmy_")
        ):
            result.get(CONF_MEMBERS, {}).pop(entity_id, None)
        else:
            existing.append(entity_id)
    for account_id, account in result.get(CONF_FINDMY_ACCOUNTS, {}).items():
        for identifier, item in account.get("items", {}).items():
            try:
                unique = tracker_unique_id(account_id, identifier, item)
            except (AttributeError, ValueError, RuntimeError):
                continue
            entity_id = registry.async_get_entity_id(
                "device_tracker", "homecircle", unique
            )
            if not entity_id:
                continue
            if entity_id in result.get(
                CONF_TRACKER_PEOPLE, []
            ) or entity_id in result.get(CONF_PETS, []):
                result.setdefault(CONF_MEMBERS, {})[entity_id] = saved_members.get(
                    entity_id, {}
                )
                continue
            if entity_id not in existing:
                existing.append(entity_id)
            members = result.setdefault(CONF_MEMBERS, {})
            previous = saved_members.get(entity_id, {})
            members[entity_id] = {
                "trackers": [entity_id],
                "additional_residences": [],
                "show_on_map": True,
                **previous,
                "kind": "item",
            }
    result[CONF_ITEMS] = existing
    return result
