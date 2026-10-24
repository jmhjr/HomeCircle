"""Synthetic continuity survives omission without preserving tracking capability."""

import asyncio
import base64
from contextlib import nullcontext
from copy import deepcopy
from datetime import UTC, datetime
import json
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.homecircle._vendor_findmy import FindMyAccessory
from custom_components.homecircle.findmy_flow import FindMyFlow
from custom_components.homecircle.findmy_identity import (
    IdentityError,
    authenticated_identity,
    prepare_state,
    previous_metadata,
    resolve_identifier,
)
from custom_components.homecircle.findmy_provider import account_root, tracker_unique_id
from custom_components.homecircle.findmy_setup import (
    FindMySetup,
    FindMySetupError,
    accessory_id,
    sdk,
)
from custom_components.homecircle.findmy_vault import (
    Vault,
    VaultError,
    account_identity,
)


ACCOUNT = "a" * 32


def session(dsid="synthetic-owner"):
    return {
        "account": {"username": "owner@example.invalid", "password": None},
        "login": {
            "state": 3,
            "data": {
                "dsid": dsid,
                "mobileme_data": {
                    "tokens": {"searchPartyToken": "synthetic-report-grant"}
                },
            },
        },
    }


def accessory(
    identifier="synthetic-apple-id",
    *,
    master=1,
    primary=2,
    secondary=3,
    name="Example item",
):
    return FindMyAccessory(
        master_key=bytes([master]) * 28,
        skn=bytes([primary]) * 32,
        sks=bytes([secondary]) * 32,
        paired_at=datetime(2026, 1, 1, tzinfo=UTC),
        identifier=identifier,
        name=name,
        model="AirTag",
    )


def item(value):
    return {
        "accessory": value.to_json(),
        "report": {"last_seen": "2026-10-01T12:00:00+00:00"},
    }


def setup_for(found, previous=None, state=None, saved_session=None):
    saved_session = saved_session or session()
    account = SimpleNamespace(
        to_json=lambda: deepcopy(saved_session),
        service_tokens={"searchPartyToken": "synthetic-report-grant"},
        _recovery_diagnostics={},
        close=AsyncMock(),
        _password=None,
    )
    setup = FindMySetup(
        account, AsyncMock(), SimpleNamespace(LOGGED_IN=3, REQUIRE_2FA=1)
    )
    setup.client = SimpleNamespace(
        accessories=AsyncMock(return_value=found), unlock=AsyncMock(), close=AsyncMock()
    )
    setup.keys_recovered = True
    setup.previous_items = deepcopy(previous or {})
    setup.identity_state = deepcopy(state)
    return setup


class Flow(FindMyFlow):
    def async_show_form(self, **kwargs):
        return kwargs

    def async_create_entry(self, **kwargs):
        return {"saved": True, **kwargs}

    def save(self):
        self.hass.config_entries.async_update_entry(
            self.config_entry, data=deepcopy(self.draft), options=deepcopy(self.draft)
        )
        return self.async_create_entry(title="", data=self.draft)


def flow_for(hass, setup, metadata, *, saved_only=True):
    current = {"findmy_accounts": {ACCOUNT: deepcopy(metadata)}, "members": {}}
    entry = MockConfigEntry(
        domain="homecircle", data=deepcopy(current), options=deepcopy(current)
    )
    entry.add_to_hass(hass)
    paused = SimpleNamespace(close=AsyncMock())
    provider = SimpleNamespace(
        pause_account=AsyncMock(return_value=paused), resume_account=Mock()
    )
    entry.runtime_data = SimpleNamespace(managed_trackers={"findmy": provider})
    flow = Flow()
    flow.hass, flow.config_entry = hass, entry
    flow.draft = deepcopy(current)
    flow.pending_connections = []
    flow.findmy_setup = setup
    flow.findmy_account_id, flow.findmy_label = ACCOUNT, "Example account"
    flow.findmy_selected = list(setup.accessories)
    flow.findmy_types = {identifier: "airtag" for identifier in setup.accessories}
    flow.findmy_saved_only = saved_only
    flow.findmy_saved_metadata = deepcopy(metadata)
    return flow, provider, paused


def metadata_for(items):
    return {
        "storage_id": ACCOUNT,
        "account_identity": account_identity(session()),
        "label": "Example account",
        "items": items,
    }


@pytest.fixture(autouse=True)
def no_reload(hass, tmp_path):
    # HA's lightweight fixture otherwise shares its synthetic config directory.
    # These tests exercise real encrypted files and need independent stores.
    hass.config.config_dir = str(tmp_path)
    with patch.object(hass.config_entries, "async_schedule_reload") as reload:
        yield reload


@pytest.mark.parametrize("field", ["master_key", "skn", "sks"])
def test_all_three_secrets_are_required_and_names_are_not_proof(field):
    original = accessory()
    previous = {"legacy": item(original)}
    state = prepare_state(
        session(), previous, {"legacy": {"unique_id": "homecircle_findmy_original"}}
    )
    changed = original.to_json()
    changed[field] = (b"\x09" * (28 if field == "master_key" else 32)).hex()
    assert resolve_identifier(changed, "candidate", previous, state) == "candidate"
    assert previous_metadata(state, "candidate") == {}
    assert (
        resolve_identifier(original.to_json(), "changed-apple-identifier", {}, state)
        == "legacy"
    )


def test_changed_apple_identifier_same_name_and_reused_old_identifier_are_conservative():
    original = accessory()
    identifier = accessory_id(original)
    previous = {identifier: item(original)}
    state = prepare_state(session(), previous, {})
    renamed = accessory("new-apple-id", name="Renamed item")
    assert (
        resolve_identifier(renamed.to_json(), accessory_id(renamed), {}, state)
        == identifier
    )
    unrelated = accessory(master=4)
    replacement = resolve_identifier(
        unrelated.to_json(), accessory_id(unrelated), previous, state
    )
    assert replacement != identifier
    assert (
        resolve_identifier(
            unrelated.to_json(), accessory_id(unrelated), previous, state
        )
        == replacement
    )


def test_ambiguous_previous_proof_is_rejected_instead_of_choosing_by_name():
    old = item(accessory())
    with pytest.raises(IdentityError, match="findmy_duplicate_item"):
        prepare_state(session(), {"first": old, "second": old}, {})
    with pytest.raises(IdentityError, match="findmy_duplicate_item"):
        resolve_identifier(old["accessory"], "new", {"first": old, "second": old}, None)


def test_account_binding_is_authenticated_dsid_only_and_ledger_is_keyed():
    old = {"legacy": item(accessory())}
    first = prepare_state(session(), old, {})
    second = prepare_state(session(), old, {})
    assert next(iter(first["records"])) != next(iter(second["records"]))
    for bad in (
        session("another-owner"),
        {"account": {"username": "owner@example.invalid"}},
        {**session(), "login": {"state": 1, "data": {"dsid": "synthetic-owner"}}},
    ):
        with pytest.raises(IdentityError, match="findmy_identity_unavailable"):
            prepare_state(bad, old, {}, first)
    assert authenticated_identity(session()) == account_identity(session())
    assert (
        authenticated_identity({"account": {"username": "owner@example.invalid"}})
        is None
    )


def test_ledger_contains_only_commitments_and_allowed_preferences():
    old = {"legacy": item(accessory())}
    metadata = {
        "legacy": {
            "name": "Example",
            "unique_id": "homecircle_findmy_legacy",
            "accessory": old["legacy"]["accessory"],
            "report": old["legacy"]["report"],
            "display_preferences": {
                "kind": "item",
                "show_on_map": False,
                "private_material": "discard",
            },
        }
    }
    state = prepare_state(session(), old, metadata)
    encoded = json.dumps(state)
    assert "master_key" not in encoded and "skn" not in encoded and "sks" not in encoded
    assert "last_seen" not in encoded and "discard" not in encoded
    assert previous_metadata(state, "legacy")["display_preferences"] == {
        "kind": "item",
        "show_on_map": False,
    }


def test_vault_preserves_ledger_across_polling_and_discards_raw_unselected_keys(
    tmp_path,
):
    first, second = accessory(), accessory("second", master=4, primary=5, secondary=6)
    original = {"legacy": item(first), "second": item(second)}
    state = prepare_state(
        session(), original, {"legacy": {"unique_id": "homecircle_findmy_legacy"}}
    )
    vault = Vault(tmp_path / "account")
    vault.save_account(session(), original, identity_state=state)
    vault.save_account(session(), {"second": original["second"]})
    loaded = vault.load()
    assert set(loaded["items"]) == {"second"}
    assert loaded["identity_state"] == state
    assert first.to_json()["master_key"] not in json.dumps(loaded)
    assert first.to_json()["skn"] not in json.dumps(loaded)
    assert first.to_json()["sks"] not in json.dumps(loaded)
    assert (
        previous_metadata(loaded["identity_state"], "legacy")["unique_id"]
        == "homecircle_findmy_legacy"
    )
    assert b"synthetic-owner" not in vault.data_path.read_bytes()
    with pytest.raises(IdentityError):
        vault.save_account(session("another-owner"), loaded["items"])
    assert vault.load() == loaded


def test_vault_rejects_malformed_ledger_without_replacing_previous(tmp_path):
    original = {"legacy": item(accessory())}
    state = prepare_state(session(), original, {})
    vault = Vault(tmp_path / "account")
    vault.save_account(session(), original, identity_state=state)
    before = vault.data_path.read_bytes()
    bad = deepcopy(state)
    bad["records"][next(iter(bad["records"]))]["metadata"]["master_key"] = "not-allowed"
    with pytest.raises(IdentityError):
        vault.save_account(session(), original, identity_state=bad)
    assert vault.data_path.read_bytes() == before
    # Read-side validation also rejects an otherwise decryptable malformed ledger.
    vault._write(
        {"version": 2, "session": session(), "items": original, "identity_state": bad}
    )
    with pytest.raises(VaultError):
        vault.load()


async def test_real_saved_commit_omit_restart_rediscover_reselect_preserves_id_and_preferences(
    hass,
):
    original = accessory()
    other = accessory("other", master=4, primary=5, secondary=6)
    items = {"migrated": item(original), "other": item(other)}
    preferences = {
        "kind": "item",
        "display_name": "My custom label",
        "show_on_map": False,
        "picture_id": "b" * 32,
        "pet_home_minutes": 120,
        "pet_away_minutes": 15,
    }
    metadata = metadata_for(
        {
            "migrated": {
                "name": "Example item",
                "type": "airtag",
                "unique_id": "homecircle_findmy_proven_original",
                "display_preferences": preferences,
            },
            "other": {"name": "Other", "type": "airtag"},
        }
    )
    root = account_root(hass, metadata, True)
    Vault(root).save_account(session(), items)
    setup = setup_for([original, other], items)
    setup.accessories = {"migrated": original, "other": other}
    setup.discover_new = False
    flow, provider, paused = flow_for(hass, setup, metadata)
    flow.findmy_selected = ["other"]
    with patch(
        "custom_components.homecircle.findmy_flow.FindMySetup.create"
    ) as authenticate:
        assert (await flow.async_step_findmy_confirm({"confirm": True}))["saved"]
        authenticate.assert_not_called()
    setup.client.unlock.assert_not_awaited() if setup.client else None
    loaded = Vault(root).load()
    assert set(loaded["items"]) == {"other"}
    assert (
        "migrated" not in flow.config_entry.options["findmy_accounts"][ACCOUNT]["items"]
    )
    provider.pause_account.assert_awaited_once()
    paused.close.assert_awaited_once()
    rediscovered = setup_for(
        [accessory("changed-apple-id", name="Renamed item"), other],
        loaded["items"],
        loaded["identity_state"],
    )
    choices = await rediscovered.discover(None, None)
    assert {entry["value"] for entry in choices} == {"migrated", "other"}
    current = flow.config_entry.options["findmy_accounts"][ACCOUNT]
    next_flow, _, _ = flow_for(hass, rediscovered, current, saved_only=False)
    next_flow.findmy_previous = loaded
    result = await next_flow.async_step_findmy_confirm({"confirm": True})
    assert result["saved"]
    restored = next_flow.config_entry.options["findmy_accounts"][ACCOUNT]["items"][
        "migrated"
    ]
    assert restored["unique_id"] == "homecircle_findmy_proven_original"
    assert restored["display_preferences"] == preferences
    assert (
        tracker_unique_id(ACCOUNT, "migrated", restored)
        == "homecircle_findmy_proven_original"
    )
    assert set(Vault(root).load()["items"]) == {"migrated", "other"}


async def test_picker_defaults_keep_existing_selection_and_confirm_lists_removals(hass):
    first, second = accessory(), accessory("second", master=4)
    setup = setup_for([first, second], {"old": item(first)})
    setup.accessories = {"old": first, "new": second}
    setup.discover_new = True
    flow, _, _ = flow_for(
        hass, setup, metadata_for({"old": {"name": "Existing item"}}), saved_only=False
    )
    result = await flow.async_step_findmy_select()
    marker = next(iter(result["data_schema"].schema))
    assert marker.default() == ["old"]
    flow.findmy_selected = ["new"]
    form = await flow.async_step_findmy_confirm()
    assert form["description_placeholders"]["removed_items"] == "Existing item"
    assert (await flow.async_step_findmy_select({"items": ["old", "old"]}))[
        "errors"
    ] == {"base": "findmy_select_items"}
    assert (await flow.async_step_findmy_select({"items": ["unknown"]}))["errors"] == {
        "base": "findmy_select_items"
    }
    await setup.close()


async def test_staged_initial_confirmation_does_not_write_and_expiry_drops_state(hass):
    first = accessory()
    setup = setup_for([first])
    setup.accessories = {"new": first}
    setup.discover_new = True
    flow = Flow()
    flow.hass, flow.draft = hass, {}
    flow.findmy_setup = setup
    flow.findmy_account_id, flow.findmy_label = ACCOUNT, "Example"
    flow.findmy_selected, flow.findmy_types = ["new"], {"new": "airtag"}
    flow.pending_connections = [object()]
    flow.connection_saved = AsyncMock(return_value={"staged": True})
    with patch("custom_components.homecircle.findmy_flow.Vault.save_account") as write:
        assert (await flow.async_step_findmy_confirm({"confirm": True}))["staged"]
        write.assert_not_called()
        assert flow.findmy_staged[ACCOUNT][3]["records"]
        flow.findmy_expire()
        flow.findmy_expire = None
        flow.findmy_staged = {}
    assert setup.closed
    assert not flow.findmy_staged


async def test_saved_metadata_failure_rolls_back_keys_and_exact_original_ledger(hass):
    original = accessory()
    items = {"legacy": item(original)}
    metadata = metadata_for({"legacy": {"name": "Example", "type": "airtag"}})
    root = account_root(hass, metadata, True)
    Vault(root).save_account(session(), items)
    before = Vault(root).load()
    setup = setup_for([original], items)
    setup.accessories = {"legacy": original}
    flow, provider, paused = flow_for(hass, setup, metadata)
    with patch.object(
        hass.config_entries,
        "async_update_entry",
        side_effect=RuntimeError("synthetic metadata failure"),
    ):
        result = await flow.async_step_findmy_confirm({"confirm": True})
    assert result["errors"] == {"base": "findmy_storage_failed"}
    assert Vault(root).load() == before
    provider.resume_account.assert_called_once_with(ACCOUNT, paused)
    await setup.close()


async def test_actual_options_saved_picker_and_confirmation_persist_ledger_without_apple_auth(
    hass,
):
    from homeassistant.data_entry_flow import FlowResultType

    account_type, provider_type, _, _ = sdk()
    account = account_type(
        provider_type(), uid="synthetic-local-user", devid="synthetic-device"
    )
    saved_session = account.to_json()
    await account.close()
    saved_session["account"].update(session()["account"])
    saved_session["login"] = session()["login"]
    items = {"legacy": item(accessory()), "other": item(accessory("other", master=4))}
    metadata = metadata_for(
        {
            "legacy": {
                "name": "First",
                "type": "airtag",
                "unique_id": "homecircle_findmy_migrated_original",
            },
            "other": {"name": "Other", "type": "airtag"},
        }
    )
    root = account_root(hass, metadata, True)
    Vault(root).save_account(saved_session, items)
    entry = MockConfigEntry(
        domain="homecircle",
        title="HomeCircle",
        data={
            "people": [],
            "members": {},
            "primary_home": "zone.home",
            "places": [],
            "findmy_accounts": {ACCOUNT: metadata},
        },
    )
    entry.add_to_hass(hass)
    manager = hass.config_entries.options
    result = await manager.async_init(entry.entry_id)
    with patch(
        "custom_components.homecircle.findmy_flow.FindMySetup.create"
    ) as authenticate:
        for data in (
            {"next_step_id": "findmy_accounts"},
            {"next_step_id": "findmy_manage"},
            {"account": ACCOUNT},
            {"next_step_id": "findmy_saved_items"},
            {"consent": True},
        ):
            result = await manager.async_configure(result["flow_id"], data)
        assert result["step_id"] == "findmy_select", result.get("errors")
        marker = next(iter(result["data_schema"].schema))
        assert marker.default() == ["legacy", "other"]
        result = await manager.async_configure(result["flow_id"], {"items": ["other"]})
        result = await manager.async_configure(result["flow_id"], {"type_0": "airtag"})
        assert result["description_placeholders"]["removed_items"] == "First"
        result = await manager.async_configure(result["flow_id"], {"confirm": True})
        assert result["type"] is FlowResultType.CREATE_ENTRY
        authenticate.assert_not_called()
    loaded = Vault(root).load()
    assert set(loaded["items"]) == {"other"}
    assert (
        previous_metadata(loaded["identity_state"], "legacy")["unique_id"]
        == "homecircle_findmy_migrated_original"
    )
    assert set(entry.options["findmy_accounts"][ACCOUNT]["items"]) == {"other"}


def fresh_flow(hass, metadata, items, entry=None):
    first, second = accessory("new-apple-id"), accessory("other", master=4)
    setup = setup_for([first, second], items)
    setup.accessories = {"legacy": first, "other": second}
    setup.identity_state = prepare_state(session(), items, metadata["items"])
    flow, provider, paused = flow_for(hass, setup, metadata, saved_only=False)
    if entry is not None:
        flow.config_entry = entry
        provider = entry.runtime_data.managed_trackers["findmy"]
        paused = provider.pause_account.return_value
    flow.findmy_previous = {
        "version": 2,
        "session": session(),
        "items": deepcopy(items),
    }
    flow.findmy_selected = ["other"]
    return flow, provider, paused


async def test_discovered_concurrent_confirmations_reject_stale_revision(hass):
    items = {"legacy": item(accessory()), "other": item(accessory("other", master=4))}
    metadata = metadata_for({"legacy": {"name": "First"}, "other": {"name": "Other"}})
    root = account_root(hass, metadata, True)
    Vault(root).save_account(session(), items)
    first, provider, _ = fresh_flow(hass, metadata, items)
    second, _, _ = fresh_flow(hass, metadata, items, first.config_entry)
    entered, release = threading.Event(), threading.Event()
    original_save = Vault.save_account

    def blocked_save(vault, saved_session, chosen, **kwargs):
        entered.set()
        assert release.wait(3)
        return original_save(vault, saved_session, chosen, **kwargs)

    with patch.object(Vault, "save_account", new=blocked_save):
        first_task = asyncio.create_task(
            first.async_step_findmy_confirm({"confirm": True})
        )
        assert await asyncio.wait_for(asyncio.to_thread(entered.wait, 2), 3)
        second_task = asyncio.create_task(
            second.async_step_findmy_confirm({"confirm": True})
        )
        await asyncio.sleep(0)
        assert provider.pause_account.await_count == 1
        release.set()
        first_result, second_result = await asyncio.gather(first_task, second_task)
    assert first_result["saved"]
    assert second_result["errors"] == {"base": "findmy_storage_failed"}
    assert set(Vault(root).load()["items"]) == {"other"}
    assert (
        first.config_entry.options["findmy_accounts"][ACCOUNT]["session_revision"] == 1
    )
    await second.finish_findmy_setup()


async def test_discovered_cancelled_confirmation_finishes_matching_vault_and_metadata(
    hass,
):
    items = {"legacy": item(accessory()), "other": item(accessory("other", master=4))}
    metadata = metadata_for({"legacy": {"name": "First"}, "other": {"name": "Other"}})
    root = account_root(hass, metadata, True)
    Vault(root).save_account(session(), items)
    flow, _, paused = fresh_flow(hass, metadata, items)
    entered, release = threading.Event(), threading.Event()
    original_save = Vault.save_account

    def blocked_save(vault, saved_session, chosen, **kwargs):
        entered.set()
        assert release.wait(3)
        return original_save(vault, saved_session, chosen, **kwargs)

    with patch.object(Vault, "save_account", new=blocked_save):
        task = asyncio.create_task(flow.async_step_findmy_confirm({"confirm": True}))
        assert await asyncio.wait_for(asyncio.to_thread(entered.wait, 2), 3)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert set(Vault(root).load()["items"]) == {"other"}
    assert set(flow.config_entry.options["findmy_accounts"][ACCOUNT]["items"]) == {
        "other"
    }
    assert flow.findmy_setup is None
    paused.close.assert_awaited_once()


async def test_discovered_metadata_failure_restores_original_keys_ledger_and_draft(
    hass,
):
    items = {"legacy": item(accessory()), "other": item(accessory("other", master=4))}
    metadata = metadata_for({"legacy": {"name": "First"}, "other": {"name": "Other"}})
    root = account_root(hass, metadata, True)
    Vault(root).save_account(session(), items)
    flow, provider, paused = fresh_flow(hass, metadata, items)
    before = Vault(root).load()
    draft = deepcopy(flow.draft)
    with patch.object(
        hass.config_entries,
        "async_update_entry",
        side_effect=RuntimeError("synthetic metadata failure"),
    ):
        result = await flow.async_step_findmy_confirm({"confirm": True})
    assert result["errors"] == {"base": "findmy_storage_failed"}
    assert Vault(root).load() == before
    assert flow.draft == draft
    provider.resume_account.assert_called_once_with(ACCOUNT, paused)
    await flow.finish_findmy_setup()


async def test_discovery_refuses_same_key_material_under_two_apple_ids():
    setup = setup_for([accessory("first-apple-id"), accessory("second-apple-id")])
    with pytest.raises(FindMySetupError, match="findmy_duplicate_item"):
        await setup.discover(None, None)
    assert setup.accessories == {}
    await setup.close()


async def test_discovery_does_not_apply_other_accounts_ledger_even_for_identical_keys():
    previous = {"legacy": item(accessory())}
    state = prepare_state(
        session(), previous, {"legacy": {"unique_id": "homecircle_findmy_original"}}
    )
    setup = setup_for([accessory("changed-id")], {}, state, session("another-owner"))
    with pytest.raises(FindMySetupError, match="findmy_identity_unavailable"):
        await setup.discover(None, None)
    assert setup.accessories == {}
    await setup.close()


async def test_pending_initial_commit_persists_only_selected_keys_and_identity_record(
    hass,
):
    chosen, unselected = accessory(), accessory("unselected", master=4)
    setup = setup_for([chosen, unselected])
    setup.accessories = {"chosen": chosen, "unselected": unselected}
    flow = Flow()
    flow.hass, flow.draft = hass, {}
    flow.findmy_setup = setup
    flow.findmy_account_id, flow.findmy_label = ACCOUNT, "Example"
    flow.findmy_selected, flow.findmy_types = ["chosen"], {"chosen": "airtag"}
    flow.pending_connections = [object()]
    flow.connection_saved = AsyncMock(return_value={"staged": True})
    assert (await flow.async_step_findmy_confirm({"confirm": True}))["staged"]
    metadata = flow.draft["findmy_accounts"][ACCOUNT]
    root = account_root(hass, metadata)
    assert not root.exists()
    await flow.async_commit_findmy()
    loaded = Vault(root).load()
    assert set(loaded["items"]) == {"chosen"}
    assert {
        record["identifier"] for record in loaded["identity_state"]["records"].values()
    } == {"chosen"}
    assert unselected.to_json()["master_key"] not in json.dumps(loaded)
    assert not flow.findmy_staged


async def test_actual_options_fresh_cancel_publishes_both_snapshots_and_reload(
    hass, no_reload
):
    from custom_components.homecircle.config_flow import HomeCircleOptionsFlow

    items = {"legacy": item(accessory()), "other": item(accessory("other", master=4))}
    metadata = metadata_for({"legacy": {"name": "First"}, "other": {"name": "Other"}})
    root = account_root(hass, metadata, True)
    Vault(root).save_account(session(), items)
    prepared, _, paused = fresh_flow(hass, metadata, items)
    flow = HomeCircleOptionsFlow()
    flow.__dict__.update(
        {key: value for key, value in vars(prepared).items() if key != "config_entry"}
    )
    flow.handler = prepared.config_entry.entry_id
    entered, release = threading.Event(), threading.Event()
    original_save = Vault.save_account

    def blocked_save(vault, saved_session, chosen, **kwargs):
        entered.set()
        assert release.wait(3)
        return original_save(vault, saved_session, chosen, **kwargs)

    with patch.object(Vault, "save_account", new=blocked_save):
        task = asyncio.create_task(flow.async_step_findmy_confirm({"confirm": True}))
        assert await asyncio.wait_for(asyncio.to_thread(entered.wait, 2), 3)
        task.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert set(Vault(root).load()["items"]) == {"other"}
    assert set(flow.config_entry.options["findmy_accounts"][ACCOUNT]["items"]) == {
        "other"
    }
    assert (
        flow.config_entry.data["findmy_accounts"]
        == flow.config_entry.options["findmy_accounts"]
    )
    no_reload.assert_called_once_with(flow.config_entry.entry_id)
    paused.close.assert_awaited_once()


@pytest.mark.parametrize("saved_only", [True, False])
@pytest.mark.parametrize(
    "superseding_action", ["new_selection", "disconnect", "data_only_disconnect"]
)
async def test_postwrite_newer_revision_is_never_overwritten_or_resurrected(
    hass, saved_only, superseding_action
):
    from custom_components.homecircle.findmy_storage import delete_account

    items = {"legacy": item(accessory()), "other": item(accessory("other", master=4))}
    metadata = metadata_for({"legacy": {"name": "First"}, "other": {"name": "Other"}})
    root = account_root(hass, metadata, True)
    Vault(root).save_account(session(), items)
    flow, provider, paused = fresh_flow(hass, metadata, items)
    flow.findmy_saved_only = saved_only
    entered, release = threading.Event(), threading.Event()
    original_save = Vault.save_account
    writes = []

    def blocked_save(vault, saved_session, chosen, **kwargs):
        writes.append(deepcopy(chosen))
        original_save(vault, saved_session, chosen, **kwargs)
        entered.set()
        assert release.wait(3)

    with patch.object(Vault, "save_account", new=blocked_save):
        task = asyncio.create_task(flow.async_step_findmy_confirm({"confirm": True}))
        assert await asyncio.wait_for(asyncio.to_thread(entered.wait, 2), 3)
        current = deepcopy(dict(flow.config_entry.options))
        if superseding_action == "new_selection":
            newer_items = {"legacy": items["legacy"]}
            newer_state = prepare_state(session(), newer_items, metadata["items"])
            await hass.async_add_executor_job(
                lambda: original_save(
                    Vault(root), session(), newer_items, identity_state=newer_state
                )
            )
            current["findmy_accounts"][ACCOUNT] = {
                **metadata,
                "session_revision": 99,
                "items": {"legacy": metadata["items"]["legacy"]},
            }
        else:
            await hass.async_add_executor_job(delete_account, hass, metadata)
            current["findmy_accounts"] = {}
        entry = flow.config_entry
        if superseding_action == "data_only_disconnect":
            hass.config_entries.async_update_entry(entry, data=current)
        else:
            hass.config_entries.async_update_entry(entry, data=current, options=current)
        release.set()
        result = await task
    assert result["errors"] == {"base": "findmy_storage_failed"}
    assert len(writes) == 1
    provider.resume_account.assert_not_called()
    paused.close.assert_awaited_once()
    if superseding_action == "new_selection":
        assert set(Vault(root).load()["items"]) == {"legacy"}
        assert entry.options["findmy_accounts"][ACCOUNT]["session_revision"] == 99
    else:
        assert not root.exists()
        assert not entry.data["findmy_accounts"]
    await flow.finish_findmy_setup()


async def test_disconnect_waits_for_selection_and_rejects_its_stale_confirmation(hass):
    items = {"legacy": item(accessory()), "other": item(accessory("other", master=4))}
    metadata = metadata_for({"legacy": {"name": "First"}, "other": {"name": "Other"}})
    root = account_root(hass, metadata, True)
    Vault(root).save_account(session(), items)
    selection, provider, _ = fresh_flow(hass, metadata, items)
    disconnect, _, _ = fresh_flow(hass, metadata, items, selection.config_entry)
    disconnect.async_abort = lambda **kwargs: kwargs
    entered, release = threading.Event(), threading.Event()
    original_save = Vault.save_account

    def blocked_save(vault, saved_session, chosen, **kwargs):
        entered.set()
        assert release.wait(3)
        return original_save(vault, saved_session, chosen, **kwargs)

    with patch.object(Vault, "save_account", new=blocked_save):
        selecting = asyncio.create_task(
            selection.async_step_findmy_confirm({"confirm": True})
        )
        assert await asyncio.wait_for(asyncio.to_thread(entered.wait, 2), 3)
        disconnecting = asyncio.create_task(
            disconnect.async_step_findmy_disconnect({"confirm": True})
        )
        await asyncio.sleep(0)
        assert provider.pause_account.await_count == 1
        release.set()
        assert (await selecting)["saved"]
        assert (await disconnecting)["reason"] == "findmy_storage_failed"
    assert set(Vault(root).load()["items"]) == {"other"}
    await disconnect.finish_findmy_setup()
    disconnect.draft = deepcopy(dict(selection.config_entry.options))
    assert (await disconnect.async_step_findmy_disconnect({"confirm": True}))["saved"]
    assert not root.exists()
    assert not selection.config_entry.options["findmy_accounts"]
    assert not selection.config_entry.data["findmy_accounts"]


def staged_options(hass, metadata, items):
    from custom_components.homecircle.config_flow import HomeCircleOptionsFlow

    prepared, provider, paused = fresh_flow(hass, metadata, items)
    saved_session, chosen = prepared.findmy_setup.selected_payload(["other"])
    selected, state = prepared._findmy_selection_metadata(
        saved_session, chosen, metadata
    )
    replacement = {**metadata, "session_revision": 1, "items": selected}
    prepared.draft["findmy_accounts"][ACCOUNT] = replacement
    prepared.findmy_staged = {
        ACCOUNT: (replacement, saved_session, chosen, state, metadata)
    }
    flow = HomeCircleOptionsFlow()
    flow.__dict__.update(
        {key: value for key, value in vars(prepared).items() if key != "config_entry"}
    )
    flow.handler = prepared.config_entry.entry_id
    flow._reset_findmy_snapshot()
    return flow, provider, paused


async def test_staged_actual_options_cancel_finishes_full_draft_and_native_publication(
    hass, no_reload
):
    items = {"legacy": item(accessory()), "other": item(accessory("other", master=4))}
    metadata = metadata_for({"legacy": {"name": "First"}, "other": {"name": "Other"}})
    root = account_root(hass, metadata, True)
    Vault(root).save_account(session(), items)
    flow, _, paused = staged_options(hass, metadata, items)
    flow.draft["city_lookup_enabled"] = True
    entered, release = threading.Event(), threading.Event()
    original_save = Vault.save_account

    def blocked_save(vault, saved_session, chosen, **kwargs):
        entered.set()
        assert release.wait(3)
        return original_save(vault, saved_session, chosen, **kwargs)

    async def finalize():
        return flow.save()

    with patch.object(Vault, "save_account", new=blocked_save):
        task = asyncio.create_task(flow.async_commit_findmy(finalizer=finalize))
        assert await asyncio.wait_for(asyncio.to_thread(entered.wait, 2), 3)
        task.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert set(Vault(root).load()["items"]) == {"other"}
    assert set(flow.config_entry.options["findmy_accounts"][ACCOUNT]["items"]) == {
        "other"
    }
    assert flow.config_entry.options["city_lookup_enabled"] is True
    assert (
        flow.config_entry.data["findmy_accounts"]
        == flow.config_entry.options["findmy_accounts"]
    )
    assert not flow.findmy_staged
    no_reload.assert_called_once_with(flow.config_entry.entry_id)
    paused.close.assert_awaited_once()
    await flow.finish_findmy_setup()


async def test_staged_finalizer_failure_restores_vault_and_resumes_account(hass):
    items = {"legacy": item(accessory()), "other": item(accessory("other", master=4))}
    metadata = metadata_for({"legacy": {"name": "First"}, "other": {"name": "Other"}})
    root = account_root(hass, metadata, True)
    Vault(root).save_account(session(), items)
    before = Vault(root).load()
    flow, provider, paused = staged_options(hass, metadata, items)

    async def fail_finalize():
        raise ValueError("synthetic finalizer failure")

    with pytest.raises(ValueError, match="synthetic finalizer failure"):
        await flow.async_commit_findmy(finalizer=fail_finalize)
    assert Vault(root).load() == before
    assert set(flow.config_entry.options["findmy_accounts"][ACCOUNT]["items"]) == {
        "legacy",
        "other",
    }
    provider.resume_account.assert_called_once_with(ACCOUNT, paused)
    await flow.finish_findmy_setup()


async def test_cancelled_initial_create_result_removes_unattached_capabilities(hass):
    from homeassistant.data_entry_flow import FlowResultType

    metadata = metadata_for({"new": {"name": "Example", "type": "airtag"}})
    items = {"new": item(accessory())}
    state = prepare_state(session(), items, metadata["items"])
    flow = Flow()
    flow.hass, flow.draft = hass, {"findmy_accounts": {ACCOUNT: metadata}}
    flow.findmy_staged = {ACCOUNT: (metadata, session(), items, state, None)}
    entered, release = threading.Event(), threading.Event()
    original_save = Vault.save_account

    def blocked_save(vault, saved_session, chosen, **kwargs):
        entered.set()
        assert release.wait(3)
        return original_save(vault, saved_session, chosen, **kwargs)

    async def finalize():
        return {
            "type": FlowResultType.CREATE_ENTRY,
            "title": "HomeCircle",
            "data": flow.draft,
        }

    with patch.object(Vault, "save_account", new=blocked_save):
        task = asyncio.create_task(flow.async_commit_findmy(finalizer=finalize))
        assert await asyncio.wait_for(asyncio.to_thread(entered.wait, 2), 3)
        task.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert not account_root(hass, metadata).exists()


async def test_staged_postwrite_newer_revision_keeps_its_vault_and_metadata(hass):
    items = {"legacy": item(accessory()), "other": item(accessory("other", master=4))}
    metadata = metadata_for({"legacy": {"name": "First"}, "other": {"name": "Other"}})
    root = account_root(hass, metadata, True)
    Vault(root).save_account(session(), items)
    flow, provider, paused = staged_options(hass, metadata, items)
    entered, release = threading.Event(), threading.Event()
    original_save = Vault.save_account
    writes = []

    def blocked_save(vault, saved_session, chosen, **kwargs):
        writes.append(chosen)
        original_save(vault, saved_session, chosen, **kwargs)
        entered.set()
        assert release.wait(3)

    async def finalize():
        return flow.save()

    with patch.object(Vault, "save_account", new=blocked_save):
        task = asyncio.create_task(flow.async_commit_findmy(finalizer=finalize))
        assert await asyncio.wait_for(asyncio.to_thread(entered.wait, 2), 3)
        newer = {"legacy": items["legacy"]}
        await hass.async_add_executor_job(
            lambda: original_save(
                Vault(root),
                session(),
                newer,
                identity_state=prepare_state(session(), newer, metadata["items"]),
            )
        )
        current = deepcopy(dict(flow.config_entry.options))
        current["findmy_accounts"][ACCOUNT] = {
            **metadata,
            "session_revision": 99,
            "items": {"legacy": metadata["items"]["legacy"]},
        }
        hass.config_entries.async_update_entry(
            flow.config_entry, data=current, options=current
        )
        release.set()
        with pytest.raises(FindMySetupError, match="findmy_settings_changed"):
            await task
    assert len(writes) == 1
    assert set(Vault(root).load()["items"]) == {"legacy"}
    assert (
        flow.config_entry.options["findmy_accounts"][ACCOUNT]["session_revision"] == 99
    )
    provider.resume_account.assert_not_called()
    paused.close.assert_awaited_once()
    await flow.finish_findmy_setup()


async def test_explicit_disconnect_can_remove_an_unreadable_owned_vault(hass):
    items = {"legacy": item(accessory()), "other": item(accessory("other", master=4))}
    metadata = metadata_for({"legacy": {"name": "First"}, "other": {"name": "Other"}})
    root = account_root(hass, metadata, True)
    Vault(root).save_account(session(), items)
    Vault(root).data_path.write_bytes(b"synthetic unreadable ciphertext")
    flow, provider, paused = fresh_flow(hass, metadata, items)
    assert (await flow.async_step_findmy_disconnect({"confirm": True}))["saved"]
    assert not root.exists()
    assert flow.config_entry.options["findmy_accounts"] == {}
    provider.resume_account.assert_not_called()
    paused.close.assert_awaited_once()
    await flow.finish_findmy_setup()


def _account_tree_snapshot(base):
    result = {}
    for path in (base, *base.rglob("*")):
        kind = "link" if path.is_symlink() else "file" if path.is_file() else "directory"
        contents = (
            str(path.readlink()) if kind == "link"
            else path.read_bytes() if kind == "file" else None
        )
        result[str(path.relative_to(base))] = (path.lstat().st_mode, kind, contents)
    return result


@pytest.mark.parametrize("fault", [
    "invalid_base64_key", "short_decoded_key", "missing_directory", "missing_vault", "key_read_error",
])
async def test_explicit_disconnect_removes_only_confirmed_malformed_or_missing_owned_store(hass, fault):
    items = {"legacy": item(accessory()), "other": item(accessory("other", master=4))}
    metadata = metadata_for({"legacy": {"name": "First"}, "other": {"name": "Other"}})
    root = account_root(hass, metadata, True)
    vault = Vault(root)
    vault.save_account(session(), items)
    base = root.parent.parent
    guard = base / "recovery_guard"
    guard.mkdir(mode=0o700)
    guard_file = guard / "ledger.json"
    guard_file.write_bytes(b"synthetic separate guard retained")
    guard_file.chmod(0o600)
    if fault == "invalid_base64_key":
        vault.key_path.write_bytes(b"not-base64!")
    elif fault == "short_decoded_key":
        vault.key_path.write_bytes(base64.urlsafe_b64encode(b"short"))
    elif fault == "missing_directory":
        vault.key_path.unlink()
        vault.data_path.unlink()
        root.rmdir()
    elif fault == "missing_vault":
        vault.data_path.unlink()
    flow, provider, paused = fresh_flow(hass, metadata, items)
    flow.async_abort = Mock(return_value={"type": "abort", "reason": "findmy_storage_failed"})
    before = _account_tree_snapshot(base)
    configuration = deepcopy((dict(flow.config_entry.data), dict(flow.config_entry.options), flow.draft))
    read_bytes = type(vault.key_path).read_bytes

    def read(path):
        if path == vault.key_path:
            raise PermissionError("private-read-error-canary")
        return read_bytes(path)

    boundary = (
        patch.object(type(vault.key_path), "read_bytes", read)
        if fault == "key_read_error" else nullcontext()
    )
    with boundary:
        assert (await flow.async_step_findmy_disconnect())["step_id"] == "findmy_disconnect"
    assert _account_tree_snapshot(base) == before
    assert (flow.config_entry.data, flow.config_entry.options, flow.draft) == configuration
    with boundary:
        assert (await flow.async_step_findmy_disconnect({"confirm": True})).get("saved") is True
    flow.async_abort.assert_not_called()
    assert not root.exists()
    assert flow.config_entry.data["findmy_accounts"] == {}
    assert flow.config_entry.options["findmy_accounts"] == {}
    assert guard_file.read_bytes() == b"synthetic separate guard retained"
    provider.pause_account.assert_awaited_once_with(ACCOUNT)
    provider.resume_account.assert_not_called()
    paused.close.assert_awaited_once()
    await flow.finish_findmy_setup()


@pytest.mark.parametrize("fault", [
    "directory_link", "key_link", "vault_link", "key_permissions", "directory_permissions", "legacy",
])
async def test_explicit_disconnect_preserves_unsafe_or_legacy_store_and_metadata(hass, fault):
    items = {"legacy": item(accessory()), "other": item(accessory("other", master=4))}
    metadata = metadata_for({"legacy": {"name": "First"}, "other": {"name": "Other"}})
    if fault == "legacy":
        metadata["storage_id"] = "legacy"
    root = account_root(hass, metadata, True)
    vault = Vault(root)
    vault.save_account(session(), items)
    base = root if fault == "legacy" else root.parent.parent
    if fault == "directory_link":
        target = base / "synthetic-directory-target"
        root.rename(target)
        root.symlink_to(target, target_is_directory=True)
    elif fault in ("key_link", "vault_link"):
        path = vault.key_path if fault == "key_link" else vault.data_path
        target = base / "synthetic-file-target"
        path.rename(target)
        path.symlink_to(target)
    elif fault == "key_permissions":
        vault.key_path.chmod(0o644)
    elif fault == "directory_permissions":
        root.chmod(0o755)
    flow, provider, paused = fresh_flow(hass, metadata, items)
    flow.async_abort = Mock(return_value={"type": "abort", "reason": "findmy_storage_failed"})
    before = _account_tree_snapshot(base)
    configuration = deepcopy((dict(flow.config_entry.data), dict(flow.config_entry.options), flow.draft))
    assert (await flow.async_step_findmy_disconnect({"confirm": True}))["reason"] == "findmy_storage_failed"
    flow.async_abort.assert_called_once_with(reason="findmy_storage_failed")
    assert _account_tree_snapshot(base) == before
    assert (flow.config_entry.data, flow.config_entry.options, flow.draft) == configuration
    provider.pause_account.assert_awaited_once_with(ACCOUNT)
    provider.resume_account.assert_called_once_with(ACCOUNT, paused)
    paused.close.assert_not_awaited()
    await flow.finish_findmy_setup()


async def test_staged_actual_options_publish_failure_keeps_both_old_snapshots_and_vault(
    hass,
):
    items = {"legacy": item(accessory()), "other": item(accessory("other", master=4))}
    metadata = metadata_for({"legacy": {"name": "First"}, "other": {"name": "Other"}})
    root = account_root(hass, metadata, True)
    Vault(root).save_account(session(), items)
    before = Vault(root).load()
    flow, provider, paused = staged_options(hass, metadata, items)
    data_before, options_before = (
        deepcopy(dict(flow.config_entry.data)),
        deepcopy(dict(flow.config_entry.options)),
    )

    async def finalize():
        return flow.save()

    with patch.object(
        hass.config_entries,
        "async_update_entry",
        side_effect=RuntimeError("synthetic publish failure"),
    ) as publish:
        with pytest.raises(RuntimeError, match="synthetic publish failure"):
            await flow.async_commit_findmy(finalizer=finalize)
    assert publish.call_count == 1
    assert flow.config_entry.data == data_before
    assert flow.config_entry.options == options_before
    assert Vault(root).load() == before
    provider.resume_account.assert_called_once_with(ACCOUNT, paused)
    await flow.finish_findmy_setup()


async def test_actual_reconfigure_staged_commit_resolves_entry_and_preserves_success_abort(
    hass, no_reload
):
    from homeassistant.data_entry_flow import FlowResultType

    items = {"legacy": item(accessory()), "other": item(accessory("other", master=4))}
    metadata = metadata_for({"legacy": {"name": "First"}, "other": {"name": "Other"}})
    root = account_root(hass, metadata, True)
    Vault(root).save_account(session(), items)
    prepared, _, paused = staged_options(hass, metadata, items)
    entry = prepared.config_entry
    initial = {**entry.data, "people": [], "primary_home": "zone.home", "places": []}
    hass.config_entries.async_update_entry(entry, data=initial, options=initial)
    manager = hass.config_entries.flow
    result = await manager.async_init(
        "homecircle", context={"source": "reconfigure", "entry_id": entry.entry_id}
    )
    flow = manager._progress[result["flow_id"]]
    flow.draft = {**initial, **deepcopy(prepared.draft), "city_lookup_enabled": True}
    flow.findmy_staged = prepared.findmy_staged

    async def finalize():
        return flow.save()

    result = await flow.async_commit_findmy(finalizer=finalize)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.options == {}
    assert set(entry.data["findmy_accounts"][ACCOUNT]["items"]) == {"other"}
    assert entry.data["city_lookup_enabled"] is True
    assert set(Vault(root).load()["items"]) == {"other"}
    no_reload.assert_called_once_with(entry.entry_id)
    paused.close.assert_awaited_once()
    manager.async_abort(flow.flow_id)
    await prepared.finish_findmy_setup()


@pytest.mark.parametrize("same_dsid", [False, True])
async def test_concurrent_new_accounts_merge_latest_and_discard_rejected_duplicate_store(
    hass, same_dsid
):
    entry = MockConfigEntry(
        domain="homecircle",
        data={"findmy_accounts": {}},
        options={"findmy_accounts": {}},
    )
    entry.add_to_hass(hass)
    flows = []
    for index, account_id in enumerate(("a" * 32, "b" * 32)):
        owner = "same-owner" if same_dsid else f"synthetic-owner-{index}"
        value = accessory(f"synthetic-{index}")
        setup = setup_for([value], saved_session=session(owner))
        setup.accessories = {"item": value}
        flow = Flow()
        flow.hass, flow.config_entry = hass, entry
        flow.draft = deepcopy(dict(entry.options))
        flow.findmy_setup = setup
        flow.findmy_account_id, flow.findmy_label = (
            account_id,
            f"Example account {index}",
        )
        flow.findmy_selected, flow.findmy_types = ["item"], {"item": "airtag"}
        flow.pending_connections = []
        flows.append(flow)
    entered, release = threading.Event(), threading.Event()
    count_lock = threading.Lock()
    writes = []
    original_save = Vault.save_account

    def blocked_save(vault, saved_session, chosen, **kwargs):
        original_save(vault, saved_session, chosen, **kwargs)
        with count_lock:
            writes.append(vault.root)
            if len(writes) == 2:
                entered.set()
        assert release.wait(3)

    with patch.object(Vault, "save_account", new=blocked_save):
        tasks = [
            asyncio.create_task(flow.async_step_findmy_confirm({"confirm": True}))
            for flow in flows
        ]
        assert await asyncio.wait_for(asyncio.to_thread(entered.wait, 2), 3)
        release.set()
        results = await asyncio.gather(*tasks)
    accounts = entry.options["findmy_accounts"]
    assert len(accounts) == (1 if same_dsid else 2)
    assert sum(bool(result.get("saved")) for result in results) == len(accounts)
    assert entry.data["findmy_accounts"] == accounts
    for flow in flows:
        root = account_root(hass, {"storage_id": flow.findmy_account_id})
        if flow.findmy_account_id in accounts:
            assert set(Vault(root).load()["items"]) == {"item"}
        else:
            assert not root.exists()
        await flow.finish_findmy_setup()


@pytest.mark.parametrize("restore_saved", [False, True])
async def test_contradictory_ledger_closes_new_local_setup_before_fixed_error(
    hass, restore_saved
):
    original = {"legacy": item(accessory())}
    changed = {"legacy": item(accessory(master=4))}
    metadata = metadata_for(
        {
            "legacy": {
                "name": "Example",
                "type": "airtag",
                "unique_id": "homecircle_findmy_original",
            }
        }
    )
    state = prepare_state(session(), original, metadata["items"])
    root = account_root(hass, metadata, True)
    Vault(root).save_account(session(), changed, identity_state=state)
    before = Vault(root).data_path.read_bytes()
    local = setup_for([], changed)
    local.account._password = "synthetic-transient-password"
    client = local.client
    flow, _, _ = flow_for(hass, local, metadata, saved_only=restore_saved)
    flow.findmy_setup = None
    flow.async_abort = lambda **kwargs: kwargs
    with (
        patch(
            "custom_components.homecircle.findmy_flow.FindMySetup.create",
            return_value=local,
        ) as authenticate,
        patch(
            "custom_components.homecircle.findmy_flow.prepare_saved_setup",
            return_value=local,
        ),
        patch.object(Vault, "save_account") as write,
    ):
        if restore_saved:
            result = await flow.async_step_findmy_saved_items({"consent": True})
            assert result["errors"] == {"base": "findmy_duplicate_item"}
            authenticate.assert_not_called()
        else:
            result = await flow.async_step_findmy_add({"consent": True})
            assert result["reason"] == "findmy_duplicate_item"
            authenticate.assert_called_once()
        write.assert_not_called()
    assert local.closed
    assert local.account._password is None
    assert not local.previous_items and not local.accessories
    client.close.assert_awaited_once()
    local.account.close.assert_awaited_once()
    assert flow.findmy_setup is None and flow.findmy_expire is None
    assert Vault(root).data_path.read_bytes() == before
