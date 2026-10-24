"""An older household dialog cannot restore a newer connection selection."""

from copy import deepcopy

import pytest
from homeassistant.config_entries import SOURCE_RECONFIGURE
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.homecircle.const import DOMAIN


@pytest.mark.parametrize("disconnect", [False, True])
async def test_stale_reconfigure_cannot_restore_newer_findmy_selection(
    hass, disconnect
):
    old = {
        "findmy_enabled": True,
        "findmy_accounts": {
            "example": {
                "account_identity": "a" * 64,
                "storage_id": "b" * 32,
                "session_revision": 1,
                "items": {"first": {"name": "First"}, "removed": {"name": "Removed"}},
            }
        },
        "people": [],
        "members": {},
        "primary_home": "zone.home",
        "places": [],
    }
    entry = MockConfigEntry(domain=DOMAIN, data=deepcopy(old), options=deepcopy(old))
    entry.add_to_hass(hass)
    manager = hass.config_entries.flow
    result = await manager.async_init(
        DOMAIN,
        context={
            "source": SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )
    result = await manager.async_configure(
        result["flow_id"],
        {
            "people": [],
            "primary_home": "zone.home",
            "places": [],
        },
    )
    assert result["step_id"] == "confirm"
    newer = deepcopy(old)
    if disconnect:
        newer["findmy_accounts"] = {}
        newer["findmy_enabled"] = False
    else:
        newer["findmy_accounts"]["example"]["session_revision"] = 2
        newer["findmy_accounts"]["example"]["items"].pop("removed")
    hass.config_entries.async_update_entry(
        entry, data=deepcopy(newer), options=deepcopy(newer)
    )
    result = await manager.async_configure(
        result["flow_id"], {"next_step_id": "confirm_save"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "findmy_settings_changed"
    assert dict(entry.data) == dict(entry.options) == newer


async def test_stale_household_save_cannot_restore_deselected_items(hass):
    old = {
        "findmy_enabled": True,
        "findmy_accounts": {
            "example": {
                "account_identity": "a" * 64,
                "storage_id": "b" * 32,
                "session_revision": 1,
                "items": {"first": {"name": "First"}, "removed": {"name": "Removed"}},
            }
        },
        "people": [],
        "members": {},
        "primary_home": "zone.home",
        "places": [],
    }
    entry = MockConfigEntry(domain=DOMAIN, data=deepcopy(old), options=deepcopy(old))
    entry.add_to_hass(hass)
    manager = hass.config_entries.options
    result = await manager.async_init(entry.entry_id)
    result = await manager.async_configure(
        result["flow_id"], {"next_step_id": "city_lookup"}
    )
    newer = deepcopy(old)
    newer["findmy_accounts"]["example"]["session_revision"] = 2
    newer["findmy_accounts"]["example"]["items"].pop("removed")
    hass.config_entries.async_update_entry(
        entry, data=deepcopy(newer), options=deepcopy(newer)
    )
    result = await manager.async_configure(
        result["flow_id"], {"city_lookup_enabled": True}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "findmy_settings_changed"
    assert dict(entry.data) == dict(entry.options) == newer


async def test_stale_household_save_cannot_reconnect_disconnected_account(hass):
    old = {
        "findmy_enabled": True,
        "findmy_accounts": {
            "example": {"account_identity": "a" * 64, "session_revision": 1}
        },
        "people": [],
        "members": {},
        "primary_home": "zone.home",
        "places": [],
    }
    entry = MockConfigEntry(domain=DOMAIN, data=deepcopy(old), options=deepcopy(old))
    entry.add_to_hass(hass)
    manager = hass.config_entries.options
    result = await manager.async_init(entry.entry_id)
    result = await manager.async_configure(
        result["flow_id"], {"next_step_id": "city_lookup"}
    )
    newer = {**old, "findmy_accounts": {}, "findmy_enabled": False}
    hass.config_entries.async_update_entry(
        entry, data=deepcopy(newer), options=deepcopy(newer)
    )
    result = await manager.async_configure(
        result["flow_id"], {"city_lookup_enabled": True}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "findmy_settings_changed"
    assert dict(entry.data) == dict(entry.options) == newer
