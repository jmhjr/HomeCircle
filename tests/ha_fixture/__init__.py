"""Synthetic sources, loaded ONLY by scripts/disposable_ha.py in temporary HA."""

from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
import voluptuous as vol


async def async_setup(hass, config):
    def scenario(name):
        phone = {
            "friendly_name": "Example GPS phone",
            "source_type": "gps",
            ATTR_LATITUDE: 0.0,
            ATTR_LONGITUDE: 0.0,
            "in_zones": ["zone.home"],
        }
        router = {
            "friendly_name": "Example locationless presence",
            "source_type": "router",
            "in_zones": ["zone.home"],
        }
        state = "home"
        if name == "residence":
            state = "Example Residence"
            phone.update({ATTR_LATITUDE: 1.0, "in_zones": ["zone.example_residence"]})
        elif name == "away":
            state = "not_home"
            phone.update({ATTR_LATITUDE: 2.0, "in_zones": []})
        elif name == "unavailable":
            state = "unavailable"
        elif name == "overlap":
            router.update(
                {"source_type": "gps", ATTR_LATITUDE: 0.0, ATTR_LONGITUDE: 0.0}
            )
        hass.states.async_set("device_tracker.example_phone", state, phone)
        hass.states.async_set("device_tracker.example_router", "home", router)

    scenario("home")

    async def remove_residence(call):
        hass.states.async_remove("zone.example_residence")

    async def set_scenario(call):
        scenario(call.data["scenario"])

    hass.services.async_register(
        "example_sources", "remove_residence", remove_residence
    )
    hass.services.async_register(
        "example_sources",
        "set_scenario",
        set_scenario,
        schema=vol.Schema(
            {
                vol.Required("scenario"): vol.In(
                    ["home", "residence", "away", "unavailable", "overlap"]
                )
            }
        ),
    )
    return True
