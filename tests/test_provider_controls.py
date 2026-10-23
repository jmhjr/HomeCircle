"""Stop controls survive restart and close concurrent provider work."""

import asyncio
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.homecircle import device_tracker as tracker_platform, tracker_providers
from custom_components.homecircle.const import DOMAIN
from custom_components.homecircle.provider_controls import (
    ProviderControls,
    ProviderControlsError,
    ProviderPaused,
    async_get_controls,
)


async def test_pause_survives_actual_store_reload_and_resume_is_explicit(hass):
    controls = await async_get_controls(hass, "example-controls")
    with patch.object(hass.config_entries, "async_reload", new=AsyncMock()):
        await controls.async_pause_denied("life360")
        await hass.async_block_till_done()
        restored = ProviderControls(hass, "example-controls")
        await restored.async_load()
        assert restored.paused("life360")
        assert not restored.paused("findmy")
        await restored.async_set_paused("life360", False)
        restarted = ProviderControls(hass, "example-controls")
        await restarted.async_load()
        assert not restarted.paused("life360")


async def test_account_denial_preserves_findmy_sibling_and_explicit_resume(hass):
    controls = await async_get_controls(hass, "example-accounts")
    with patch.object(hass.config_entries, "async_reload", new=AsyncMock()):
        await controls.async_pause_denied("findmy", "example-account-a")
        await hass.async_block_till_done()
        restored = ProviderControls(hass, "example-accounts")
        await restored.async_load()
        assert restored.paused("findmy", "example-account-a")
        assert not restored.paused("findmy", "example-account-b")
        assert not restored.paused("findmy")
        await restored.async_set_paused("findmy", False)
        assert not restored.paused("findmy", "example-account-a")


async def test_manual_pause_cancels_and_drains_registered_fetch(hass):
    controls = await async_get_controls(hass, "example-fetch")
    entered, drained = asyncio.Event(), asyncio.Event()

    async def fetch():
        async with controls.operation("life360"):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                await asyncio.sleep(0)
                drained.set()

    task = asyncio.create_task(fetch())
    await entered.wait()
    with patch.object(hass.config_entries, "async_reload", new=AsyncMock()):
        await controls.async_set_paused("life360", True)
    assert drained.is_set() and isinstance(task.exception(), ProviderPaused)
    assert not controls._operations
    with pytest.raises(ProviderPaused):
        async with controls.operation("life360"):
            pytest.fail("paused provider entered a new request")


async def test_denial_inside_operation_never_stops_itself_or_publishes_result(hass):
    controls = await async_get_controls(hass, "example-self")
    with patch.object(hass.config_entries, "async_reload", new=AsyncMock()):
        with pytest.raises(ProviderPaused):
            async with controls.operation("life360"):
                await controls.async_pause_denied("life360")
                assert not asyncio.current_task().cancelling()
        await hass.async_block_till_done()
    assert not controls._operations


async def test_pause_blocks_before_save_finishes_and_save_failure_never_reloads(hass):
    controls = await async_get_controls(hass, "example-failure")
    entered, release = asyncio.Event(), asyncio.Event()

    async def failed_save(_data):
        entered.set()
        await release.wait()
        raise OSError("fictional disk failure")

    with (
        patch.object(controls.store, "async_save", side_effect=failed_save),
        patch.object(hass.config_entries, "async_reload", new=AsyncMock()) as reload,
    ):
        task = asyncio.create_task(controls.async_pause_denied("life360"))
        await entered.wait()
        assert controls.paused("life360")
        with pytest.raises(ProviderPaused):
            async with controls.operation("life360"):
                pytest.fail("request entered while stop persistence was pending")
        release.set()
        with pytest.raises(ProviderControlsError):
            await task
        assert controls.paused("life360") and controls.paused("findmy")
        reload.assert_not_awaited()


async def test_new_denial_during_resume_save_never_exposes_unpaused_window(hass):
    controls = await async_get_controls(hass, "example-resume-race")
    with patch.object(hass.config_entries, "async_reload", new=AsyncMock()):
        await controls.async_set_paused("life360", True)
    entered, release = asyncio.Event(), asyncio.Event()
    denied_entered, denied_release = asyncio.Event(), asyncio.Event()
    save = controls.store.async_save
    calls = 0

    async def scheduled_save(data):
        nonlocal calls
        calls += 1
        if calls == 1:
            entered.set()
            await release.wait()
        else:
            denied_entered.set()
            await denied_release.wait()
        await save(data)

    with (
        patch.object(controls.store, "async_save", side_effect=scheduled_save),
        patch.object(hass.config_entries, "async_reload", new=AsyncMock()),
    ):
        resume = asyncio.create_task(controls.async_set_paused("life360", False))
        await entered.wait()
        denied = asyncio.create_task(controls.async_pause_denied("life360"))
        await asyncio.sleep(0)
        release.set()
        await denied_entered.wait()
        # The resumed disk snapshot may already exist; the newer denial still
        # fences I/O while its own durable save is waiting.
        assert controls.paused("life360")
        with pytest.raises(ProviderPaused):
            async with controls.operation("life360"):
                pytest.fail("resume overrode a newer denial")
        denied_release.set()
        await denied
        with pytest.raises(ProviderPaused):
            await resume
        await hass.async_block_till_done()
    restored = ProviderControls(hass, "example-resume-race")
    await restored.async_load()
    assert restored.paused("life360")


@pytest.mark.parametrize("bad_saved", [{"providers": {}}, {"revision": True, "providers": {}}])
async def test_corrupt_controls_fail_closed_without_overwriting(hass, bad_saved):
    store = SimpleNamespace(async_load=AsyncMock(return_value=bad_saved), async_save=AsyncMock())
    controls = ProviderControls(hass, "example-corrupt", store)
    await controls.async_load()
    assert controls.paused("life360") and controls.paused("findmy")
    store.async_save.assert_not_awaited()


async def test_load_failure_and_missing_initial_write_fail_closed(hass):
    for load in (AsyncMock(side_effect=OSError()), AsyncMock(return_value=None)):
        store = SimpleNamespace(async_load=load, async_save=AsyncMock(side_effect=OSError()))
        controls = ProviderControls(hass, "example-unavailable", store)
        await controls.async_load()
        assert controls.paused("life360") and controls.paused("findmy")


async def test_paused_startup_keeps_registered_entity_without_loading_client(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={
        "life360_account": {"method": "token", "secret": "fictional-private-token"},
    })
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    registered = registry.async_get_or_create(
        "device_tracker", DOMAIN, "homecircle_life360_example-paused-member",
        config_entry=entry, suggested_object_id="example_paused_member",
    )
    controls = await async_get_controls(hass, entry.entry_id)
    with patch.object(hass.config_entries, "async_reload", new=AsyncMock()):
        await controls.async_set_paused("life360", True)
    entry.runtime_data = SimpleNamespace(config=deepcopy(entry.data), managed_trackers={})
    entities = []
    with patch("custom_components.homecircle.life360_direct.DirectLife360") as constructor:
        await tracker_platform.async_setup_entry(hass, entry, entities.extend)
    constructor.assert_not_called()
    assert len(entities) == 1
    assert entities[0].entity_id == registered.entity_id
    assert entities[0].unique_id == registered.unique_id
    assert not entities[0].available
    assert entry.runtime_data.managed_trackers["life360"].health_snapshot().state == "paused"
    assert tracker_providers.connected_providers(entry.runtime_data.config)


async def test_factory_second_client_sees_actual_persisted_pause_before_sdk(hass):
    controls = await async_get_controls(hass, "example-factory")
    provider = tracker_providers.TRACKER_PROVIDERS[0]
    with patch.object(hass.config_entries, "async_reload", new=AsyncMock()):
        await controls.async_set_paused("life360", True)
    # A new cache is what a Core restart would have. Load the same real Store.
    hass.data.pop("homecircle_provider_controls")
    await async_get_controls(hass, "example-factory")
    with patch("custom_components.homecircle.life360_direct.authorized_client", new=AsyncMock()) as authorize:
        client = provider.client_factory(hass, {"method": "token", "secret": "fictional"}, lambda _: None, "example-factory")
        await client.async_start()
        await client.async_stop()
    authorize.assert_not_awaited()
    assert client.session is None


async def test_nested_operation_registration_is_drained_once(hass):
    controls = await async_get_controls(hass, "example-nested")
    entered = asyncio.Event()

    async def nested():
        async with controls.operation("findmy", "example-a"):
            async with controls.operation("findmy", "example-a"):
                entered.set()
                await asyncio.Event().wait()

    task = asyncio.create_task(nested())
    await entered.wait()
    with patch.object(hass.config_entries, "async_reload", new=AsyncMock()):
        await controls.async_set_paused("findmy", True, account_id="example-a")
    assert isinstance(task.exception(), ProviderPaused)
    assert not controls._operations
    assert not controls.paused("findmy", "example-b")


async def test_pause_save_drains_repeated_caller_cancellation_before_restart(hass):
    controls = await async_get_controls(hass, "example-cancel-save")
    entered, release = asyncio.Event(), asyncio.Event()
    save = controls.store.async_save

    async def delayed_save(data):
        entered.set()
        await release.wait()
        await save(data)

    with (
        patch.object(controls.store, "async_save", side_effect=delayed_save),
        patch.object(hass.config_entries, "async_reload", new=AsyncMock()),
    ):
        task = asyncio.create_task(controls.async_pause_denied("life360"))
        await entered.wait()
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done() and controls.paused("life360")
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        await hass.async_block_till_done()
    fresh = ProviderControls(hass, "example-cancel-save")
    await fresh.async_load()
    assert fresh.paused("life360")


@pytest.mark.parametrize("reload_outcome", [False, OSError("fictional")])
async def test_failed_reload_still_stops_loaded_clients(hass, reload_outcome):
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    client = SimpleNamespace(async_stop=AsyncMock())
    entry.runtime_data = SimpleNamespace(managed_trackers={"life360": client})
    controls = await async_get_controls(hass, entry.entry_id)
    reload = AsyncMock()
    if isinstance(reload_outcome, Exception):
        reload.side_effect = reload_outcome
    else:
        reload.return_value = reload_outcome
    with patch.object(hass.config_entries, "async_reload", new=reload):
        await controls.async_set_paused("life360", True)
    client.async_stop.assert_awaited_once()
    assert controls.paused("life360")


async def test_pause_cancellation_returns_disabled_but_unrelated_cancel_propagates(hass):
    controls = await async_get_controls(hass, "example-cancel-origin")
    entered, drained = asyncio.Event(), asyncio.Event()

    async def caller():
        try:
            async with controls.operation("life360"):
                entered.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    await asyncio.sleep(0)
                    drained.set()
        except ProviderPaused:
            assert asyncio.current_task().cancelling() == 0
            return "disabled"

    task = asyncio.create_task(caller())
    await entered.wait()
    with patch.object(hass.config_entries, "async_reload", new=AsyncMock()):
        await controls.async_set_paused("life360", True)
    assert await task == "disabled" and drained.is_set()
    with patch.object(hass.config_entries, "async_reload", new=AsyncMock()):
        await controls.async_set_paused("life360", False)
    entered.clear()
    task = asyncio.create_task(caller())
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
