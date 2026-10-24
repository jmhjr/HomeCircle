"""Account isolation and shutdown, using synthetic sessions and report clients."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.homecircle.findmy_provider import DirectFindMy
from custom_components.homecircle.findmy_reports import ReauthenticationRequired


def test_cold_startup_imports_sdk_off_event_loop():
    """A fresh interpreter exposes dependency imports hidden by test collection."""
    from pathlib import Path
    import subprocess
    import sys

    code = """
import asyncio
import importlib.abc
import socket
import sys
import threading
from types import SimpleNamespace

loop_thread = threading.get_ident()
imports = []

class RequireWorkerImport(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'anisette':
            current = threading.get_ident()
            imports.append(current)
            assert current != loop_thread, 'cold anisette import ran on the event loop'

def no_network(*args, **kwargs):
    raise AssertionError('startup import must not contact a provider')

socket.socket.connect = no_network
socket.socket.connect_ex = no_network
socket.create_connection = no_network
socket.getaddrinfo = no_network
assert 'anisette' not in sys.modules
sys.meta_path.insert(0, RequireWorkerImport())
from custom_components.homecircle import findmy_provider
assert not imports

class SyntheticHass:
    config_entries = SimpleNamespace(async_get_entry=lambda _: None)

    async def async_add_executor_job(self, target, *args):
        return await asyncio.get_running_loop().run_in_executor(None, target, *args)

async def controls(*args):
    return SimpleNamespace(paused=lambda *args: False)

findmy_provider.async_get_controls = controls
findmy_provider.er.async_get = lambda _: None
findmy_provider.async_track_time_interval = lambda *args: lambda: None

async def main():
    provider = findmy_provider.DirectFindMy(SyntheticHass(), {}, lambda _: None, 'synthetic')
    try:
        await provider.async_start()
        assert imports and all(current != loop_thread for current in imports)
        assert not provider.clients and not provider.tasks and not provider.trackers
    finally:
        await provider.async_stop()

asyncio.run(main())
"""
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c",
         "import sys; sys.path.insert(0, sys.argv[1]); " + code,
         str(Path(__file__).resolve().parents[1])],
        capture_output=True, timeout=60, check=False,
    )
    assert result.returncode == 0, "cold Find My SDK import must run off the event loop"


async def test_one_expired_account_does_not_stop_other_accounts(hass):
    entry = MockConfigEntry(domain="homecircle", title="HomeCircle")
    entry.add_to_hass(hass)
    first, second = "a" * 32, "b" * 32
    accounts = {
        key: {
            "label": "Example account",
            "storage_id": key,
            "items": {"example_item": {"name": "Example item", "type": "airtag"}},
        }
        for key in (first, second)
    }
    data = {
        "version": 2,
        "session": {"account": {"password": None}},
        "items": {
            "example_item": {"accessory": {}, "report": None},
            "example_unselected": {"accessory": {}, "report": None},
        },
    }
    clients = []

    def restore(selected, _):
        assert set(selected["items"]) == {"example_item"}
        client = SimpleNamespace(
            account=SimpleNamespace(to_json=lambda: selected["session"]),
            items=selected["items"],
            close=AsyncMock(),
            poll=AsyncMock(
                side_effect=ReauthenticationRequired() if not clients else None,
                return_value={
                    "example_item": {
                        "latitude": float(0),
                        "longitude": float(0),
                        "gps_accuracy": 5,
                        "last_seen": "2026-10-01T12:00:00+00:00",
                    }
                },
            ),
        )
        clients.append(client)
        return client

    entities = []
    provider = DirectFindMy(hass, accounts, entities.extend, entry.entry_id)
    with (
        patch.object(hass.config_entries, "async_reload", new=AsyncMock(return_value=True)),
        patch(
            "custom_components.homecircle.findmy_provider.Vault.load", return_value=data
        ),
        patch(
            "custom_components.homecircle.findmy_provider.Vault.save_account"
        ) as save,
        patch(
            "custom_components.homecircle.findmy_reports.AccountClient.restore",
            side_effect=restore,
        ),
    ):
        await provider.async_start()
        await asyncio.wait_for(asyncio.gather(*provider.tasks.values()), 5)
        await hass.async_block_till_done()
        assert provider.states[first] == "paused"
        assert provider.states[second] == "connected"
        assert provider.health_snapshot().state == "partial"
        assert len(entities) == 2
        save.assert_called_once()
        provider.interval()
        await asyncio.wait_for(asyncio.gather(*provider.tasks.values()), 5)
        await hass.async_block_till_done()
        assert clients[0].poll.await_count == 1
        assert clients[1].poll.await_count == 2
        await provider.async_stop()
        assert all(client.close.await_count == 1 for client in clients)
        assert not provider.clients


async def test_pause_reconnect_waits_for_old_poll_and_resumes_only_its_account(hass):
    import asyncio

    provider = DirectFindMy(hass, {}, lambda _: None, "example-entry")
    first, second = SimpleNamespace(), SimpleNamespace()
    finished = []

    async def poll():
        try:
            await asyncio.Future()
        finally:
            finished.append(True)

    task = hass.async_create_background_task(
        poll(), "Synthetic poll", eager_start=False
    )
    await asyncio.sleep(0)
    provider.clients = {"example-first": first, "example-second": second}
    provider.tasks = {"example-first": task}
    paused = await provider.pause_account("example-first")
    assert paused is first and finished == [True]
    assert provider.clients == {"example-second": second}
    with patch.object(provider, "interval"):
        provider.resume_account("example-first", paused)
    assert provider.clients["example-first"] is first


async def test_cleanup_failure_does_not_stop_homecircle_household(hass):
    from homeassistant.helpers import issue_registry as ir
    from custom_components.homecircle.findmy_vault import VaultError

    entry = MockConfigEntry(
        domain="homecircle",
        title="HomeCircle",
        data={"people": [], "members": {}, "primary_home": "zone.home", "places": []},
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.homecircle.findmy_storage.prune_orphans",
        side_effect=VaultError("synthetic unsafe file"),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert ("homecircle", "findmy_storage_cleanup") in ir.async_get(hass).issues
        assert entry.runtime_data.household is not None
    await hass.config_entries.async_unload(entry.entry_id)


async def test_explicit_pet_role_and_picture_survive_item_projection(hass):
    from homeassistant.helpers import entity_registry as er
    from custom_components.homecircle.findmy_items import item_config

    entry = MockConfigEntry(domain="homecircle", title="HomeCircle")
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    entity = registry.async_get_or_create(
        "device_tracker",
        "homecircle",
        "homecircle_findmy_example_item",
        config_entry=entry,
    )
    config = {
        "findmy_accounts": {
            "example": {"items": {"example_item": {"unique_id": entity.unique_id}}}
        },
        "pets": [entity.entity_id],
        "members": {
            entity.entity_id: {"kind": "pet", "picture_id": "synthetic-picture"}
        },
    }
    result = item_config(hass, config)
    assert result["pets"] == [entity.entity_id]
    assert result["items"] == []
    assert result["members"][entity.entity_id]["kind"] == "pet"
    assert result["members"][entity.entity_id]["picture_id"] == "synthetic-picture"
