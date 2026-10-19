"""Saved-item management must preserve live auth and concurrent poll results."""

from copy import deepcopy
import asyncio
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.homecircle.findmy_flow import FindMyFlow
from custom_components.homecircle.findmy_vault import account_identity


def saved(token="synthetic-report-token", report=None):
    return {
        "version": 2,
        "session": {
            "account": {"username": "example@example.invalid", "password": None},
            "login": {
                "state": 3,
                "data": {
                    "dsid": "synthetic-dsid",
                    "mobileme_data": {"tokens": {"searchPartyToken": token}},
                },
            },
        },
        "items": {"item": {"accessory": {"alignment": token}, "report": report}},
    }


class ParentFlow:
    def async_remove(self):
        self.removed = True


class Flow(FindMyFlow, ParentFlow):
    def async_show_form(self, **kwargs):
        return kwargs

    def async_abort(self, **kwargs):
        return kwargs

    def async_create_entry(self, **kwargs):
        return {"saved": True, **kwargs}


@pytest.fixture(autouse=True)
def reload_after_commit(hass):
    with patch.object(hass.config_entries, "async_schedule_reload") as reload:
        yield reload


def flow_for(hass, entry=None):
    current = saved()
    metadata = {
        "label": "Example account",
        "storage_id": "a" * 32,
        "account_identity": account_identity(current["session"]),
        "items": {
            "item": {
                "name": "Example item",
                "type": "airtag",
                "unique_id": "homecircle_findmy_kept",
            }
        },
    }
    paused = SimpleNamespace(close=AsyncMock())
    provider = SimpleNamespace(
        pause_account=AsyncMock(return_value=paused), resume_account=Mock()
    )
    flow = Flow()
    flow.hass = hass
    if entry is None:
        configuration = {"findmy_accounts": {"a" * 32: metadata}}
        entry = MockConfigEntry(
            domain="homecircle",
            data=deepcopy(configuration),
            options=deepcopy(configuration),
        )
        entry.add_to_hass(hass)
        entry.runtime_data = SimpleNamespace(managed_trackers={"findmy": provider})
    else:
        provider = entry.runtime_data.managed_trackers["findmy"]
        paused = provider.pause_account.return_value
    flow.config_entry = entry
    flow.draft = {"findmy_accounts": {"a" * 32: metadata}}
    flow.pending_connections = []
    flow.findmy_account_id = "a" * 32
    flow.findmy_label = "Example account"
    flow.findmy_selected = ["item"]
    flow.findmy_types = {"item": "airtag"}
    setup = SimpleNamespace(
        accessories={"item": SimpleNamespace(name="Example item")},
        previous_items=current["items"],
        discover_new=False,
        close=AsyncMock(),
        item_choices=lambda: [{"value": "item", "label": "Example item"}],
        selected_payload=lambda chosen: (
            deepcopy(current["session"]),
            deepcopy(current["items"]),
        ),
    )
    return flow, setup, provider, paused, current


async def test_saved_selection_needs_consent_and_never_reauthenticates(hass):
    flow, setup, _, _, current = flow_for(hass)
    with (
        patch(
            "custom_components.homecircle.findmy_flow.Vault.load", return_value=current
        ) as load,
        patch(
            "custom_components.homecircle.findmy_flow.prepare_saved_setup",
            return_value=setup,
        ) as prepare,
        patch(
            "custom_components.homecircle.findmy_flow.FindMySetup.create"
        ) as login_setup,
    ):
        result = await flow.async_step_findmy_saved_items({"consent": False})
        assert result["errors"] == {"base": "findmy_consent_required"}
        load.assert_not_called()
        result = await flow.async_step_findmy_saved_items({"consent": True})
        assert result["step_id"] == "findmy_select"
        prepare.assert_called_once()
        login_setup.assert_not_called()
        assert flow.findmy_saved_only is True
        await flow.finish_findmy_setup()


async def test_saved_commit_keeps_latest_token_keys_reports_and_unique_id(hass):
    flow, setup, provider, paused, current = flow_for(hass)
    newest = saved("newer-synthetic-token", {"last_seen": "2026-10-15T00:00:00+00:00"})
    with (
        patch(
            "custom_components.homecircle.findmy_flow.Vault.load",
            side_effect=[current, newest],
        ),
        patch(
            "custom_components.homecircle.findmy_flow.prepare_saved_setup",
            return_value=setup,
        ),
        patch("custom_components.homecircle.findmy_flow.Vault.save_account") as write,
    ):
        await flow.async_step_findmy_saved_items({"consent": True})
        result = await flow.async_step_findmy_confirm({"confirm": True})
        assert result["saved"] is True
        assert write.call_args.args == (newest["session"], newest["items"])
        assert (
            flow.draft["findmy_accounts"]["a" * 32]["items"]["item"]["unique_id"]
            == "homecircle_findmy_kept"
        )
        provider.pause_account.assert_awaited_once()
        provider.resume_account.assert_not_called()
        paused.close.assert_awaited_once()
        setup.close.assert_awaited_once()


async def test_changed_identity_during_selection_never_overwrites_and_resumes(hass):
    flow, setup, provider, paused, current = flow_for(hass)
    other = saved("different-token")
    other["session"]["login"]["data"]["dsid"] = "different-account"
    with (
        patch(
            "custom_components.homecircle.findmy_flow.Vault.load",
            side_effect=[current, other],
        ),
        patch(
            "custom_components.homecircle.findmy_flow.prepare_saved_setup",
            return_value=setup,
        ),
        patch("custom_components.homecircle.findmy_flow.Vault.save_account") as write,
    ):
        await flow.async_step_findmy_saved_items({"consent": True})
        result = await flow.async_step_findmy_confirm({"confirm": True})
        assert result["errors"] == {"base": "findmy_storage_failed"}
        write.assert_not_called()
        provider.resume_account.assert_called_once_with(flow.findmy_account_id, paused)
        paused.close.assert_not_awaited()
        await flow.finish_findmy_setup()


async def prepare(flow, setup, current):
    with (
        patch(
            "custom_components.homecircle.findmy_flow.Vault.load",
            return_value=deepcopy(current),
        ),
        patch(
            "custom_components.homecircle.findmy_flow.prepare_saved_setup",
            return_value=setup,
        ),
    ):
        return await flow.async_step_findmy_saved_items({"consent": True})


async def wait_for_worker(event):
    assert await asyncio.wait_for(asyncio.to_thread(event.wait, 2), 3)


async def test_simultaneous_saved_flows_reject_stale_confirmation(
    hass, reload_after_commit
):
    first, setup, provider, paused, current = flow_for(hass)
    second, other_setup, _, _, _ = flow_for(hass, first.config_entry)
    await prepare(first, setup, current)
    await prepare(second, other_setup, current)
    entered, release = threading.Event(), threading.Event()
    store = [deepcopy(current)]
    writes = []

    def write(_vault, session, items):
        entered.set()
        assert release.wait(3)
        writes.append(deepcopy((session, items)))
        store[0] = {
            "version": 2,
            "session": deepcopy(session),
            "items": deepcopy(items),
        }

    with (
        patch(
            "custom_components.homecircle.findmy_flow.Vault.load",
            side_effect=lambda: deepcopy(store[0]),
        ),
        patch(
            "custom_components.homecircle.findmy_flow.Vault.save_account",
            new=write,
        ),
    ):
        first_task = asyncio.create_task(
            first.async_step_findmy_confirm({"confirm": True})
        )
        await wait_for_worker(entered)
        second_task = asyncio.create_task(
            second.async_step_findmy_confirm({"confirm": True})
        )
        await asyncio.sleep(0)
        assert provider.pause_account.await_count == 1
        release.set()
        first_result, second_result = await asyncio.gather(first_task, second_task)
    assert first_result["saved"] is True
    assert second_result["errors"] == {"base": "findmy_storage_failed"}
    assert len(writes) == 1
    assert (
        first.config_entry.options["findmy_accounts"]["a" * 32]["session_revision"] == 1
    )
    paused.close.assert_awaited_once()
    provider.resume_account.assert_not_called()
    reload_after_commit.assert_called_once_with(first.config_entry.entry_id)
    await second.finish_findmy_setup()


async def test_cancelled_client_waits_for_committed_vault_and_options(
    hass, reload_after_commit
):
    flow, setup, provider, paused, current = flow_for(hass)
    await prepare(flow, setup, current)
    entered, release = threading.Event(), threading.Event()
    written = []

    def write(_vault, session, items):
        entered.set()
        assert release.wait(3)
        written.append(deepcopy((session, items)))

    with (
        patch(
            "custom_components.homecircle.findmy_flow.Vault.load",
            return_value=deepcopy(current),
        ),
        patch(
            "custom_components.homecircle.findmy_flow.Vault.save_account",
            new=write,
        ),
    ):
        task = asyncio.create_task(flow.async_step_findmy_confirm({"confirm": True}))
        await wait_for_worker(entered)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert written == [(current["session"], current["items"])]
    assert (
        flow.config_entry.options["findmy_accounts"]["a" * 32]["session_revision"] == 1
    )
    assert (
        flow.config_entry.data["findmy_accounts"]
        == flow.config_entry.options["findmy_accounts"]
    )
    provider.resume_account.assert_not_called()
    paused.close.assert_awaited_once()
    setup.close.assert_awaited_once()
    reload_after_commit.assert_called_once()


async def test_unrelated_options_changed_during_vault_write_are_preserved(hass):
    flow, setup, _, _, current = flow_for(hass)
    await prepare(flow, setup, current)
    entered, release = threading.Event(), threading.Event()

    def write(_vault, _session, _items):
        entered.set()
        assert release.wait(3)

    with (
        patch(
            "custom_components.homecircle.findmy_flow.Vault.load",
            return_value=deepcopy(current),
        ),
        patch(
            "custom_components.homecircle.findmy_flow.Vault.save_account",
            new=write,
        ),
    ):
        task = asyncio.create_task(flow.async_step_findmy_confirm({"confirm": True}))
        await wait_for_worker(entered)
        hass.config_entries.async_update_entry(
            flow.config_entry,
            options={
                **flow.config_entry.options,
                "display_name": "Newest household name",
            },
        )
        release.set()
        result = await task
    assert result["data"]["display_name"] == "Newest household name"
    assert flow.config_entry.options["display_name"] == "Newest household name"


async def test_newer_data_revision_is_rejected_before_pause_even_if_options_are_old(
    hass,
):
    flow, setup, provider, _, current = flow_for(hass)
    await prepare(flow, setup, current)
    changed = deepcopy(dict(flow.config_entry.data))
    changed["findmy_accounts"]["a" * 32]["session_revision"] = 1
    hass.config_entries.async_update_entry(flow.config_entry, data=changed)
    with patch("custom_components.homecircle.findmy_flow.Vault.save_account") as write:
        result = await flow.async_step_findmy_confirm({"confirm": True})
    assert result["errors"] == {"base": "findmy_storage_failed"}
    provider.pause_account.assert_not_awaited()
    write.assert_not_called()
    await flow.finish_findmy_setup()


async def test_failed_metadata_publish_restores_vault_and_resumes_client(hass):
    flow, setup, provider, paused, current = flow_for(hass)
    await prepare(flow, setup, current)
    with (
        patch(
            "custom_components.homecircle.findmy_flow.Vault.load",
            return_value=deepcopy(current),
        ),
        patch("custom_components.homecircle.findmy_flow.Vault.save_account") as write,
        patch.object(
            hass.config_entries,
            "async_update_entry",
            side_effect=ValueError("synthetic failure"),
        ),
    ):
        result = await flow.async_step_findmy_confirm({"confirm": True})
    assert result["errors"] == {"base": "findmy_storage_failed"}
    assert write.call_count == 2
    assert write.call_args.args == (current["session"], current["items"])
    provider.resume_account.assert_called_once_with(flow.findmy_account_id, paused)
    paused.close.assert_not_awaited()
    assert (
        "session_revision" not in flow.config_entry.options["findmy_accounts"]["a" * 32]
    )
    await flow.finish_findmy_setup()


async def test_flow_removal_waits_for_authorized_commit_before_closing_setup(hass):
    flow, setup, provider, paused, current = flow_for(hass)
    await prepare(flow, setup, current)
    entered, release = threading.Event(), threading.Event()

    def write(_vault, _session, _items):
        entered.set()
        assert release.wait(3)

    with (
        patch(
            "custom_components.homecircle.findmy_flow.Vault.load",
            return_value=deepcopy(current),
        ),
        patch(
            "custom_components.homecircle.findmy_flow.Vault.save_account",
            new=write,
        ),
    ):
        task = asyncio.create_task(flow.async_step_findmy_confirm({"confirm": True}))
        await wait_for_worker(entered)
        flow.async_remove()
        await asyncio.sleep(0)
        setup.close.assert_not_awaited()
        release.set()
        await task
        await hass.async_block_till_done()
    assert flow.removed
    setup.close.assert_awaited_once()
    paused.close.assert_awaited_once()
    provider.resume_account.assert_not_called()


async def test_real_options_manager_does_not_schedule_a_second_reload(
    hass, reload_after_commit
):
    from custom_components.homecircle.config_flow import HomeCircleOptionsFlow

    prepared, setup, _, _, current = flow_for(hass)
    flow = HomeCircleOptionsFlow()
    flow.__dict__.update(
        {key: value for key, value in vars(prepared).items() if key != "config_entry"}
    )
    flow.handler = prepared.config_entry.entry_id
    await prepare(flow, setup, current)
    with (
        patch(
            "custom_components.homecircle.findmy_flow.Vault.load",
            return_value=deepcopy(current),
        ),
        patch("custom_components.homecircle.findmy_flow.Vault.save_account"),
    ):
        result = await flow.async_step_findmy_confirm({"confirm": True})
    assert result["data"] == dict(flow.config_entry.options)
    await hass.config_entries.options.async_finish_flow(flow, result)
    reload_after_commit.assert_called_once_with(flow.config_entry.entry_id)
