"""Actual HA progress callbacks, cancellation and expiry; no Apple requests."""

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.data_entry_flow import (
    EVENT_DATA_ENTRY_FLOW_PROGRESSED, FlowResultType, UnknownFlow,
)
from homeassistant.core import callback
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from tests.test_findmy_flow import fake_setup, options


async def begin(hass, fake):
    entry, result = await options(hass)
    manager = hass.config_entries.options
    with patch("custom_components.homecircle.findmy_flow.FindMySetup.create", return_value=fake):
        result = await manager.async_configure(
            result["flow_id"], {"label": "Example account", "consent": True},
        )
    result = await manager.async_configure(
        result["flow_id"], {"username": "example@example.invalid", "password": "example-secret"},
    )
    assert result["type"] is FlowResultType.SHOW_PROGRESS
    return entry, manager, result["flow_id"], manager._progress[result["flow_id"]]


async def test_completion_notifies_and_advances_actual_manager_without_manual_configure(hass):
    fake = fake_setup()
    entered, release = asyncio.Event(), asyncio.Event()
    notices, progressed = [], asyncio.Event()

    async def login(_username, _password):
        entered.set()
        await release.wait()
        return "factor"

    fake.login = AsyncMock(side_effect=login)
    @callback
    def notice(event):
        notices.append(event.data)
        progressed.set()

    unsubscribe = hass.bus.async_listen(EVENT_DATA_ENTRY_FLOW_PROGRESSED, notice)
    entry, manager, flow_id, flow = await begin(hass, fake)
    try:
        await entered.wait()
        assert manager.async_get(flow_id)["step_id"] == "findmy_wait"
        release.set()
        await asyncio.wait_for(progressed.wait(), 1)
        # No async_configure call follows release: HA's registered task callback
        # changes server state and sends the refresh event on its own.
        assert flow.findmy_task.done() and not flow.findmy_task.cancelled()
        assert flow.cur_step["type"] is FlowResultType.SHOW_PROGRESS_DONE
        assert manager.async_get(flow_id)["step_id"] == "findmy_factor"
        assert any(notice["flow_id"] == flow_id and notice["refresh"] for notice in notices)
        assert not entry.options
    finally:
        unsubscribe()
        manager.async_abort(flow_id)
        await hass.async_block_till_done()


async def test_instant_restored_identity_returns_email_form_in_initial_response(hass, tmp_path):
    from custom_components.homecircle._findmy_runtime.provider import MacAnisetteProvider
    from tests.test_findmy_mac_runtime import machine

    fake = fake_setup()
    provider = MacAnisetteProvider(libs_path=tmp_path / "unused", state=machine())
    provider._get_ani = AsyncMock(wraps=provider._get_ani)
    provider._library = AsyncMock(side_effect=AssertionError("Restored preparation must not load software"))
    fake.account._anisette = provider
    fake.request_code = AsyncMock()
    fake.verify_code = AsyncMock()
    _, result = await options(hass)
    manager, flow_id = hass.config_entries.options, result["flow_id"]
    try:
        with patch("custom_components.homecircle.findmy_flow.FindMySetup.create", return_value=fake):
            result = await manager.async_configure(flow_id, {"label": "Example account", "consent": True})
        # A cached identity performs no I/O. Return the next form in this same
        # response, so the frontend need not catch an already-fired progress event.
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "findmy_login"
        flow = manager._progress[flow_id]
        assert flow.cur_step["type"] is FlowResultType.FORM
        assert manager.async_get(flow_id)["step_id"] == "findmy_login"
        provider._get_ani.assert_awaited_once()
        provider._library.assert_not_awaited()
        assert provider._worker is None and provider.safe_diagnostics()["request_count"] == 0
        fake.account.login.assert_not_awaited()
        fake.request_code.assert_not_awaited()
        fake.verify_code.assert_not_awaited()
    finally:
        manager.async_abort(flow_id)
        await hass.async_block_till_done()
        await provider.close()


@pytest.mark.parametrize("remove", ["abort", "expiry"])
async def test_active_work_is_cancelled_and_cleaned_on_abort_or_session_expiry(hass, remove):
    fake = fake_setup()
    entered, finished = asyncio.Event(), asyncio.Event()

    async def login(_username, _password):
        entered.set()
        try:
            await asyncio.Future()
        finally:
            finished.set()

    # Deliberately unbounded fake work lets this test isolate the flow's actual
    # fifteen-minute timer from the setup operation's shorter request deadlines.
    fake.login = AsyncMock(side_effect=login)
    with patch("custom_components.homecircle.findmy_flow.Vault.save_account") as save:
        entry, manager, flow_id, flow = await begin(hass, fake)
        await entered.wait()
        task = flow.findmy_task
        if remove == "abort":
            manager.async_abort(flow_id)
        else:
            async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=16))
        await hass.async_block_till_done()
        assert task.cancelled() and finished.is_set()
        assert fake.closed and flow.findmy_setup is None and flow.findmy_expire is None
        fake.account.close.assert_awaited_once()
        assert fake.account._password is None
        assert not fake.accessories and not fake.records
        with pytest.raises(UnknownFlow):
            manager.async_get(flow_id)
        assert not entry.options
        save.assert_not_called()


async def test_cancelled_background_task_cannot_advance_to_uncompleted_device_step(hass):
    fake = fake_setup()
    entered = asyncio.Event()

    async def login(_username, _password):
        entered.set()
        await asyncio.Future()

    fake.login = AsyncMock(side_effect=login)
    entry, manager, flow_id, flow = await begin(hass, fake)
    progressed = asyncio.Event()

    @callback
    def notice(event):
        if event.data["flow_id"] == flow_id:
            progressed.set()

    unsubscribe = hass.bus.async_listen(EVENT_DATA_ENTRY_FLOW_PROGRESSED, notice)
    try:
        await entered.wait()
        flow.findmy_task.cancel()
        await asyncio.wait_for(progressed.wait(), 1)
        assert manager.async_get(flow_id)["step_id"] == "findmy_signin_ended"
        assert flow.findmy_error == "findmy_signin_state"
        result = await manager.async_configure(flow_id)
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "findmy_signin_state"
        assert fake.closed and not entry.options
        fake.client_factory.assert_not_awaited()
    finally:
        unsubscribe()
        if flow_id in {item["flow_id"] for item in manager.async_progress()}:
            manager.async_abort(flow_id)
        await hass.async_block_till_done()


async def test_missing_progress_task_ends_with_existing_fixed_state_error(hass):
    fake = fake_setup()
    entered = asyncio.Event()

    async def login(_username, _password):
        entered.set()
        await asyncio.Future()

    fake.login = AsyncMock(side_effect=login)
    entry, manager, flow_id, flow = await begin(hass, fake)
    registered_task = flow.findmy_task
    try:
        await entered.wait()
        flow.findmy_task = None
        result = await manager.async_configure(flow_id)
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "findmy_signin_state"
        await hass.async_block_till_done()
        assert registered_task.cancelled() and fake.closed and not entry.options
        fake.client_factory.assert_not_awaited()
    finally:
        if flow_id in {item["flow_id"] for item in manager.async_progress()}:
            manager.async_abort(flow_id)
        await hass.async_block_till_done()
