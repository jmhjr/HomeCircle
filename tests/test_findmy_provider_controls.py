"""Persistent local Find My stops preserve healthy accounts and recovery limits."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.homecircle.findmy_provider import DirectFindMy
from custom_components.homecircle.findmy_reports import ReauthenticationRequired
from custom_components.homecircle.provider_controls import ProviderControls, async_get_controls
from tests.test_findmy_flow import options

ORIGIN = float(0)


async def test_denied_findmy_account_is_persisted_skipped_after_restart_and_sibling_continues(hass):
    entry = MockConfigEntry(domain="homecircle", title="HomeCircle")
    entry.add_to_hass(hass)
    first, second = "a" * 32, "b" * 32
    accounts = {
        key: {"storage_id": key, "items": {
            "example-item": {"name": "Example item", "type": "airtag"},
        }} for key in (first, second)
    }
    data = {"version": 2, "session": {"account": {"password": None}}, "items": {
        "example-item": {"accessory": {}, "report": None},
    }}
    clients = []

    def restore(selected, _libraries):
        client = SimpleNamespace(
            account=SimpleNamespace(to_json=lambda: selected["session"]),
            items=selected["items"], close=AsyncMock(),
            poll=AsyncMock(
                side_effect=ReauthenticationRequired() if not clients else None,
                return_value={},
            ),
        )
        clients.append(client)
        return client

    with (
        patch.object(hass.config_entries, "async_reload", new=AsyncMock()),
        patch("custom_components.homecircle.findmy_provider.sdk"),
        patch("custom_components.homecircle.findmy_provider.Vault.load", return_value=data),
        patch("custom_components.homecircle.findmy_provider.Vault.save_account"),
        patch("custom_components.homecircle.findmy_reports.AccountClient.restore", side_effect=restore) as restore_client,
    ):
        provider = DirectFindMy(hass, accounts, lambda _: None, entry.entry_id)
        await provider.async_start()
        await asyncio.wait_for(asyncio.gather(*provider.tasks.values()), 5)
        await hass.async_block_till_done()
        assert provider.states[first] == "paused"
        assert provider.states[second] == "connected"
        assert provider.controls.paused("findmy", first)
        assert not provider.controls.paused("findmy", second)
        provider.interval()
        await asyncio.wait_for(asyncio.gather(*provider.tasks.values()), 5)
        await hass.async_block_till_done()
        assert clients[0].poll.await_count == 1
        assert clients[1].poll.await_count == 2
        await provider.async_stop()

        # New controls and provider objects read the actual persisted Store.
        hass.data.pop("homecircle_provider_controls")
        restarted = DirectFindMy(hass, accounts, lambda _: None, entry.entry_id)
        await restarted.async_start()
        await asyncio.wait_for(asyncio.gather(*restarted.tasks.values()), 5)
        await hass.async_block_till_done()
        assert set(restarted.clients) == {second}
        assert restarted.states[first] == "paused"
        assert restarted.states[second] == "connected"
        assert restore_client.call_count == 3
        assert clients[2].poll.await_count == 1
        await restarted.async_stop()


async def test_explicit_findmy_resume_never_resets_recovery_guard(hass):
    controls = await async_get_controls(hass, "example-findmy-resume")
    with (
        patch.object(hass.config_entries, "async_reload", new=AsyncMock()),
        patch("custom_components.homecircle.findmy_recovery_guard.RecoveryGuard.reset", new=AsyncMock()) as reset,
        patch("custom_components.homecircle.findmy_setup.FindMySetup.create") as create,
    ):
        await controls.async_pause_denied("findmy", "example-account")
        await hass.async_block_till_done()
        await controls.async_set_paused("findmy", False)
        assert not controls.paused("findmy", "example-account")
    reset.assert_not_awaited()
    create.assert_not_called()
    restored = ProviderControls(hass, "example-findmy-resume")
    await restored.async_load()
    assert not restored.paused("findmy", "example-account")


async def test_paused_findmy_setup_never_creates_or_signs_in(hass):
    entry, flow = await options(hass)
    controls = await async_get_controls(hass, entry.entry_id)
    with (
        patch.object(hass.config_entries, "async_reload", new=AsyncMock()),
        patch("custom_components.homecircle.findmy_flow.FindMySetup.create") as create,
    ):
        await controls.async_set_paused("findmy", True)
        result = await hass.config_entries.options.async_configure(
            flow["flow_id"], {"label": "Example account", "consent": True},
        )
    assert result["reason"] == "provider_paused"
    create.assert_not_called()


async def test_whole_findmy_pause_never_loads_sdk_or_saved_session(hass):
    entry = MockConfigEntry(domain="homecircle", title="HomeCircle")
    entry.add_to_hass(hass)
    controls = await async_get_controls(hass, entry.entry_id)
    with patch.object(hass.config_entries, "async_reload", new=AsyncMock()):
        await controls.async_set_paused("findmy", True)
    with (
        patch("custom_components.homecircle.findmy_provider.sdk") as sdk,
        patch("custom_components.homecircle.findmy_provider.Vault.load") as load,
        patch("custom_components.homecircle.findmy_reports.AccountClient.restore") as restore,
    ):
        provider = DirectFindMy(hass, {"example": {}}, lambda _: None, entry.entry_id)
        await provider.async_start()
        await provider.async_stop()
    sdk.assert_not_called()
    load.assert_not_called()
    restore.assert_not_called()


async def test_completed_batch_is_saved_once_before_denial_reload_closes_client(hass):
    from unittest.mock import Mock

    entry = MockConfigEntry(domain="homecircle", title="HomeCircle")
    entry.add_to_hass(hass)
    controls = await async_get_controls(hass, entry.entry_id)
    account_id = "example-account"
    provider = DirectFindMy(hass, {account_id: {}}, lambda _: None, entry.entry_id)
    provider.controls = controls
    order = []
    batch = {"example-item": {"report": {"latitude": ORIGIN, "longitude": ORIGIN}}}
    session = {"cursor": "example-completed-cursor"}

    async def poll():
        client.poll_progress = True
        raise ReauthenticationRequired()

    client = SimpleNamespace(
        poll_progress=False, items=batch, poll=AsyncMock(side_effect=poll),
        account=SimpleNamespace(to_json=lambda: session),
        close=AsyncMock(side_effect=lambda: order.append("closed")),
    )
    save = Mock(side_effect=lambda *_args: order.append("saved"))
    provider.clients[account_id] = client
    provider.vaults[account_id] = SimpleNamespace(save_account=save)
    provider.trackers[account_id] = {}

    async def reload_entry(_entry_id):
        # Product unload invokes this exact lifecycle method. It cancels the
        # poll while its durable-denial callback is still returning.
        await provider.async_stop()
        return True

    with (
        patch.object(hass.config_entries, "async_reload", side_effect=reload_entry),
        patch.object(provider, "save_poll_progress", wraps=provider.save_poll_progress) as progress,
    ):
        task = asyncio.create_task(provider.poll(account_id))
        provider.tasks[account_id] = task
        await asyncio.gather(task, return_exceptions=True)
        if controls._reload_task:
            await controls._reload_task
        assert task.cancelled()
        progress.assert_awaited_once_with(account_id, client)
        provider.interval()
    assert order == ["saved", "closed"]
    save.assert_called_once_with(session, batch)
    client.poll.assert_awaited_once()
    fresh = ProviderControls(hass, entry.entry_id)
    await fresh.async_load()
    assert fresh.paused("findmy", account_id)
