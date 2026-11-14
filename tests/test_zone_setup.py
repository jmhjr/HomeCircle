"""Keep zone setup compatible with real Core and both zone runtime shapes."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.zone import DOMAIN as ZONE_DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

from custom_components.homecircle.const import DOMAIN
from custom_components.homecircle.zone_setup import async_create_zone


# Synthetic Gulf-of-Guinea point; no household or provider location data.
LOCATION = {ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0, "radius": 120}


async def test_config_flow_loads_with_real_ha_zone_component(hass):
    """Core's loader must import the complete flow, including zone setup."""
    assert await async_setup_component(hass, ZONE_DOMAIN, {})

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "household"
    hass.config_entries.flow.async_abort(result["flow_id"])


@pytest.mark.parametrize("wrapped", [False, True], ids=["legacy", "zone-data"])
async def test_create_zone_accepts_supported_storage_shapes(hass, monkeypatch, wrapped):
    """Old Core exposes the collection; 2026.11 stores it inside ZoneData."""
    collection = SimpleNamespace(
        async_create_item=AsyncMock(return_value={"id": "synthetic-zone-id"})
    )
    monkeypatch.setitem(
        hass.data,
        ZONE_DOMAIN,
        SimpleNamespace(storage_collection=collection) if wrapped else collection,
    )
    registered = er.async_get(hass).async_get_or_create(
        ZONE_DOMAIN,
        ZONE_DOMAIN,
        "synthetic-zone-id",
        suggested_object_id="example_office",
    )

    assert await async_create_zone(hass, "  Example Office  ", LOCATION) == (
        registered.entity_id
    )

    collection.async_create_item.assert_awaited_once_with(
        {"name": "Example Office", **LOCATION, "passive": False}
    )


@pytest.mark.parametrize("wrapped", [False, True], ids=["missing", "no-collection"])
async def test_create_zone_without_storage_is_unavailable(hass, monkeypatch, wrapped):
    """An uninitialized zone component must not attempt registry access."""
    if wrapped:
        monkeypatch.setitem(
            hass.data, ZONE_DOMAIN, SimpleNamespace(storage_collection=None)
        )
    else:
        monkeypatch.delitem(hass.data, ZONE_DOMAIN, raising=False)

    with patch("custom_components.homecircle.zone_setup.er.async_get") as get_registry:
        assert await async_create_zone(hass, "Example Office", LOCATION) is None

    get_registry.assert_not_called()


async def test_create_zone_uses_real_core_collection_and_registry_collision(hass):
    """Persist and expose the real zone, returning HA's suffixed entity ID."""
    assert await async_setup_component(hass, ZONE_DOMAIN, {})
    registry = er.async_get(hass)
    existing = registry.async_get_or_create(
        ZONE_DOMAIN,
        ZONE_DOMAIN,
        "synthetic-existing-zone",
        suggested_object_id="example_office",
    )
    assert existing.entity_id == "zone.example_office"

    entity_id = await async_create_zone(hass, "  Example Office  ", LOCATION)
    await hass.async_block_till_done()

    assert entity_id == "zone.example_office_2"
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.name == "Example Office"
    assert {key: state.attributes[key] for key in LOCATION} == LOCATION
    assert state.attributes["passive"] is False

    zone_data = hass.data[ZONE_DOMAIN]
    collection = getattr(zone_data, "storage_collection", zone_data)
    item = next(
        item for item in collection.async_items() if item["name"] == "Example Office"
    )
    assert registry.async_get_entity_id(ZONE_DOMAIN, ZONE_DOMAIN, item["id"]) == entity_id
    assert registry.async_get(existing.entity_id) == existing
