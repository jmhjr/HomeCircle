"""Saved account fingerprints must match before an encrypted store is polled."""

from copy import deepcopy
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.homecircle.findmy_identity import authenticated_identity
from custom_components.homecircle.findmy_provider import DirectFindMy, account_root
from custom_components.homecircle.findmy_vault import Vault


def session(owner):
    return {
        "account": {"username": "owner@example.invalid", "password": None},
        "login": {
            "state": 3,
            "data": {
                "dsid": owner,
                "mobileme_data": {"tokens": {"searchPartyToken": "synthetic-report"}},
            },
        },
    }


@pytest.mark.parametrize("different_owner", [False, True])
async def test_provider_checks_account_binding_before_restoring_or_polling(
    hass, tmp_path, different_owner
):
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain="homecircle", title="HomeCircle")
    entry.add_to_hass(hass)
    accounts, stored = {}, {}
    for account_id, owner in (
        ("a" * 32, "synthetic-first"),
        ("b" * 32, "synthetic-second"),
    ):
        expected = session(owner)
        metadata = {
            "label": "Synthetic account",
            "storage_id": account_id,
            "account_identity": authenticated_identity(expected),
            "items": {"shared_item": {"name": "Synthetic item", "type": "airtag"}},
        }
        actual = (
            session("synthetic-other")
            if different_owner and account_id[0] == "a"
            else expected
        )
        items = {"shared_item": {"accessory": {"synthetic": True}, "report": None}}
        root = account_root(hass, metadata, True)
        Vault(root).save_account(actual, items)
        accounts[account_id], stored[account_id] = metadata, root

    restored = []

    def restore(data, _libraries):
        restored.append(data["session"]["login"]["data"]["dsid"])
        return SimpleNamespace(
            account=SimpleNamespace(to_json=lambda: deepcopy(data["session"])),
            items=data["items"],
            close=AsyncMock(),
            poll=AsyncMock(return_value={}),
        )

    provider = DirectFindMy(hass, accounts, lambda _entities: None, entry.entry_id)
    first_bytes = Vault(stored["a" * 32]).data_path.read_bytes()
    with patch(
        "custom_components.homecircle.findmy_reports.AccountClient.restore",
        side_effect=restore,
    ):
        try:
            await provider.async_start()
            await asyncio.gather(*provider.tasks.values())
            await hass.async_block_till_done()
            if different_owner:
                assert restored == ["synthetic-second"]
                assert "a" * 32 not in provider.clients
                assert provider.states["a" * 32] == "unexpected_response"
                assert not provider.trackers["a" * 32]["shared_item"].available
            else:
                assert restored == ["synthetic-first", "synthetic-second"]
                assert provider.states["a" * 32] == "connected"
            assert provider.states["b" * 32] == "connected"
            assert Vault(stored["a" * 32]).data_path.read_bytes() == first_bytes
        finally:
            await provider.async_stop()
