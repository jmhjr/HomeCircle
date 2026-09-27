"""Disposable HA fixtures. No production configuration or network access."""

import pytest

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    """Load the working-tree integration using HA's real loader."""


@pytest.fixture
async def household(hass):
    """Fictional state sources; zero coordinates are synthetic Gulf-of-Guinea data."""
    from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, "zone", {})
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
        },
    )
    hass.states.async_set(
        "person.example_second", "home", {"source": "device_tracker.example_router"}
    )
    hass.states.async_set(
        "device_tracker.example_router", "home", {"source_type": "router"}
    )
    for entity_id in ("zone.example_residence", "zone.example_work"):
        hass.states.async_set(entity_id, "0")
    return {
        "people": ["person.example_member", "person.example_second"],
        "primary_home": "zone.home",
        "places": ["zone.example_work"],
    }
