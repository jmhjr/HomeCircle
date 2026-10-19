"""Migration preflight must preserve identities and refuse ambiguous mappings."""

from types import SimpleNamespace
import pytest
from custom_components.homecircle.findmy_migration import migration_payload
from custom_components.homecircle.findmy_vault import VaultError


def fixture_data():
    old = SimpleNamespace(
        entry_id="example_entry", data={}, options={"item_types": {"legacy": "airtag"}}
    )
    data = {
        "version": 1,
        "session": {
            "account": {"username": "example@example.invalid", "password": None}
        },
        "accessory": {"name": "Example item"},
        "report": {"last_seen": "2026-10-01T12:00:00+00:00"},
    }
    entities = [SimpleNamespace(unique_id="example_entry_accessory")]
    return old, data, entities


def test_legacy_migration_preserves_unique_identity_and_session():
    old, data, entities = fixture_data()
    metadata = migration_payload(data, old, entities)
    assert metadata["storage_id"] == "legacy"
    assert (
        metadata["items"]["legacy"]["unique_id"]
        == "homecircle_findmy_example_entry_accessory"
    )
    assert metadata["items"]["legacy"]["type"] == "airtag"
    assert data["report"]["last_seen"] == "2026-10-01T12:00:00+00:00"
    assert "session" not in metadata and "example@example.invalid" not in str(metadata)


@pytest.mark.parametrize(
    "entities",
    [
        [],
        [SimpleNamespace(unique_id="unrelated")],
        [
            SimpleNamespace(unique_id="example_entry_accessory"),
            SimpleNamespace(unique_id="example_entry_accessory"),
        ],
    ],
)
def test_migration_refuses_missing_or_ambiguous_entities(entities):
    old, data, _ = fixture_data()
    with pytest.raises(VaultError):
        migration_payload(data, old, entities)


async def test_interrupted_migration_restores_registry_and_prototype(hass):
    from unittest.mock import AsyncMock, patch
    from homeassistant.helpers import entity_registry as er
    from homeassistant.helpers.storage import Store
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.homecircle.findmy_migration import recover_pending

    source = MockConfigEntry(domain="homecircle_findmy", title="Example prototype")
    target = MockConfigEntry(domain="homecircle", title="HomeCircle")
    source.add_to_hass(hass)
    target.add_to_hass(hass)
    registry = er.async_get(hass)
    entity = registry.async_get_or_create(
        "device_tracker",
        "homecircle",
        "homecircle_findmy_example_accessory",
        config_entry=target,
    )
    store = Store(hass, 1, f"homecircle_findmy_migration_{target.entry_id}")
    await store.async_save(
        {
            "source": source.entry_id,
            "disabled_by": None,
            "entities": [
                {
                    "entity_id": entity.entity_id,
                    "unique_id": "example_accessory",
                    "disabled_by": None,
                }
            ],
        }
    )
    with patch.object(
        hass.config_entries, "async_set_disabled_by", new=AsyncMock(return_value=True)
    ) as enable:
        await recover_pending(hass, target)
        enable.assert_awaited_once_with(source.entry_id, None)
    restored = registry.async_get(entity.entity_id)
    assert restored.platform == "homecircle_findmy"
    assert restored.config_entry_id == source.entry_id
    assert restored.unique_id == "example_accessory"
    assert await store.async_load() is None


async def test_completed_migration_retains_entity_identity_on_restart(hass):
    from unittest.mock import AsyncMock, patch
    from homeassistant.helpers import entity_registry as er
    from homeassistant.helpers.storage import Store
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.homecircle.findmy_migration import recover_pending

    target = MockConfigEntry(
        domain="homecircle",
        title="HomeCircle",
        options={
            "findmy_accounts": {"example-account": {"migrated_from": "example-source"}}
        },
    )
    target.add_to_hass(hass)
    registry = er.async_get(hass)
    entity = registry.async_get_or_create(
        "device_tracker",
        "homecircle",
        "homecircle_findmy_example_accessory",
        config_entry=target,
    )
    store = Store(hass, 1, f"homecircle_findmy_migration_{target.entry_id}")
    await store.async_save(
        {
            "source": "example-source",
            "disabled_by": None,
            "entities": [
                {
                    "entity_id": entity.entity_id,
                    "unique_id": "example_accessory",
                    "disabled_by": None,
                }
            ],
        }
    )
    with patch.object(
        hass.config_entries, "async_set_disabled_by", new=AsyncMock()
    ) as enable:
        await recover_pending(hass, target)
        enable.assert_not_awaited()
    assert registry.async_get(entity.entity_id).unique_id == entity.unique_id
    assert await store.async_load() is None


async def test_committed_options_finish_registry_move_after_crash(hass):
    from unittest.mock import AsyncMock, patch
    from homeassistant.helpers import entity_registry as er
    from homeassistant.helpers.storage import Store
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.homecircle.findmy_migration import recover_pending

    source = MockConfigEntry(domain="homecircle_findmy", title="Example prototype")
    source.add_to_hass(hass)
    target = MockConfigEntry(
        domain="homecircle",
        title="HomeCircle",
        options={
            "findmy_accounts": {"example-account": {"migrated_from": source.entry_id}}
        },
    )
    target.add_to_hass(hass)
    registry = er.async_get(hass)
    original = registry.async_get_or_create(
        "device_tracker", "homecircle_findmy", "example_accessory", config_entry=source
    )
    store = Store(hass, 1, f"homecircle_findmy_migration_{target.entry_id}")
    await store.async_save(
        {
            "source": source.entry_id,
            "disabled_by": None,
            "entities": [
                {
                    "entity_id": original.entity_id,
                    "unique_id": original.unique_id,
                    "disabled_by": None,
                }
            ],
        }
    )
    with patch.object(
        hass.config_entries, "async_set_disabled_by", new=AsyncMock(return_value=True)
    ):
        await recover_pending(hass, target)
    moved = registry.async_get(original.entity_id)
    assert moved.entity_id == original.entity_id
    assert moved.platform == "homecircle"
    assert moved.unique_id == "homecircle_findmy_example_accessory"
    assert moved.config_entry_id == target.entry_id
    assert len(registry.entities) == 1


async def test_migration_validates_sdk_and_keeps_original_vault_unchanged(
    hass, tmp_path, monkeypatch
):
    from datetime import datetime, UTC
    from unittest.mock import AsyncMock, patch
    from homeassistant.helpers import entity_registry as er
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.homecircle._vendor_findmy import (
        FindMyAccessory,
        AsyncAppleAccount,
        LocalAnisetteProvider,
    )
    from custom_components.homecircle.findmy_vault import Vault
    from custom_components.homecircle.findmy_migration import migrate_account

    monkeypatch.setattr(
        hass.config, "path", lambda *parts: str(tmp_path.joinpath(*parts))
    )
    old = MockConfigEntry(domain="homecircle_findmy", title="Example prototype")
    target = MockConfigEntry(domain="homecircle", title="HomeCircle")
    old.add_to_hass(hass)
    target.add_to_hass(hass)
    registry = er.async_get(hass)
    original = registry.async_get_or_create(
        "device_tracker",
        "homecircle_findmy",
        f"{old.entry_id}_accessory",
        config_entry=old,
    )
    root = tmp_path / ".storage" / "homecircle_findmy"
    account = AsyncAppleAccount(LocalAnisetteProvider())
    session = account.to_json()
    session["account"]["username"] = "example@example.invalid"
    session["login"] = {
        "state": 3,
        "data": {
            "dsid": "example-dsid",
            "mobileme_data": {"tokens": {"searchPartyToken": "example-token"}},
        },
    }
    accessory = FindMyAccessory(
        master_key=bytes([1]) * 28,
        skn=bytes([2]) * 32,
        sks=bytes([3]) * 32,
        paired_at=datetime(2026, 1, 1, tzinfo=UTC),
        name="Example item",
    )
    Vault(root).save(session, accessory.to_json())
    before = (root / "session.vault").read_bytes()
    with patch.object(
        hass.config_entries, "async_set_disabled_by", new=AsyncMock(return_value=True)
    ):
        metadata = await migrate_account(hass, target, old, {})
    assert (root / "session.vault").read_bytes() == before
    assert Vault(root).load()["version"] == 1
    assert metadata["storage_id"] != "legacy"
    native = Vault(root / "homecircle_accounts" / metadata["storage_id"]).load()
    assert native["version"] == 2
    assert (
        native["items"]["legacy"]["accessory"]["master_key"]
        == accessory.to_json()["master_key"]
    )
    assert registry.async_get(original.entity_id).platform == "homecircle"
    await account.close()


async def test_public_actions_omit_undo_and_preserve_existing_tracker_and_fallback(
    hass,
):
    from unittest.mock import AsyncMock, patch
    from homeassistant.config_entries import ConfigEntryDisabler, ConfigEntryState
    from homeassistant.helpers import entity_registry as er
    from homeassistant.helpers.entity import entity_sources
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    source = MockConfigEntry(
        domain="homecircle_findmy",
        title="Example prototype",
        disabled_by=ConfigEntryDisabler.USER,
    )
    source.add_to_hass(hass)
    account_id = "a" * 32
    metadata = {
        "label": "Example account",
        "storage_id": account_id,
        "migrated_from": source.entry_id,
        "items": {
            "legacy": {
                "name": "Example item",
                "type": "airtag",
                "unique_id": "homecircle_findmy_example_original",
            }
        },
        "migration_entities": [
            {
                "entity_id": "device_tracker.example_item",
                "unique_id": "example_original",
                "disabled_by": None,
            }
        ],
    }
    target = MockConfigEntry(
        domain="homecircle",
        title="HomeCircle",
        data={
            "people": [],
            "members": {},
            "primary_home": "zone.home",
            "places": [],
            "findmy_enabled": True,
            "findmy_accounts": {account_id: metadata},
        },
    )
    target.add_to_hass(hass)
    registry = er.async_get(hass)
    entity = registry.async_get_or_create(
        "device_tracker",
        "homecircle",
        "homecircle_findmy_example_original",
        config_entry=target,
        suggested_object_id="example_item",
    )
    data = {
        "version": 2,
        "session": {"account": {"password": None}},
        "items": {"legacy": {"accessory": {}, "report": None}},
    }
    client = SimpleNamespace(
        account=SimpleNamespace(to_json=lambda: data["session"]),
        items=data["items"],
        close=AsyncMock(),
        poll=AsyncMock(return_value={}),
    )
    with (
        patch(
            "custom_components.homecircle.findmy_provider.Vault.load", return_value=data
        ),
        patch("custom_components.homecircle.findmy_provider.Vault.save_account"),
        patch(
            "custom_components.homecircle.findmy_reports.AccountClient.restore",
            return_value=client,
        ),
        patch.object(
            hass.config_entries,
            "async_set_disabled_by",
            new=AsyncMock(return_value=True),
        ),
    ):
        assert await hass.config_entries.async_setup(target.entry_id)
        await hass.async_block_till_done()
        assert entity.entity_id in entity_sources(hass)
        manager = hass.config_entries.options
        result = await manager.async_init(target.entry_id)
        result = await manager.async_configure(
            result["flow_id"], {"next_step_id": "findmy_accounts"}
        )
        result = await manager.async_configure(
            result["flow_id"], {"next_step_id": "findmy_manage"}
        )
        result = await manager.async_configure(
            result["flow_id"], {"account": account_id}
        )
        assert result["step_id"] == "findmy_account_actions"
        assert "findmy_undo_migration" not in result["menu_options"]
        assert "findmy_disconnect" in result["menu_options"]
        assert "findmy_reconnect" in result["menu_options"]
        flow = manager.async_get(result["flow_id"])
        assert not hasattr(flow, "async_step_findmy_undo_migration")
        assert not hasattr(flow, "async_step_findmy_migrate")
        manager.async_abort(result["flow_id"])
        assert target.state == ConfigEntryState.LOADED
        retained = registry.async_get(entity.entity_id)
        assert retained.platform == "homecircle"
        assert retained.unique_id == "homecircle_findmy_example_original"
        assert retained.config_entry_id == target.entry_id
        assert entity.entity_id in entity_sources(hass)
        assert source.disabled_by == ConfigEntryDisabler.USER
        assert not target.options
        assert target.data["findmy_accounts"][account_id] == metadata
        client.close.assert_not_awaited()
        await hass.config_entries.async_unload(target.entry_id)
        client.close.assert_awaited_once()


async def test_public_findmy_accounts_omit_migration_even_with_active_prototype(hass):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    source = MockConfigEntry(domain="homecircle_findmy", title="Example prototype")
    source.add_to_hass(hass)
    target = MockConfigEntry(
        domain="homecircle",
        title="HomeCircle",
        data={"people": [], "members": {}, "primary_home": "zone.home", "places": []},
    )
    target.add_to_hass(hass)
    manager = hass.config_entries.options
    result = await manager.async_init(target.entry_id)
    result = await manager.async_configure(
        result["flow_id"], {"next_step_id": "findmy_accounts"}
    )
    assert result["menu_options"] == ["findmy_add"]
    assert source.disabled_by is None
    assert not hasattr(
        manager.async_get(result["flow_id"]), "async_step_findmy_migrate"
    )
    manager.async_abort(result["flow_id"])


def test_public_translations_omit_obsolete_migration_routes():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "custom_components/homecircle"
    for path in (root / "strings.json", root / "translations/en.json"):
        values = json.loads(path.read_text())
        for section in ("config", "options"):
            steps = values[section]["step"]
            assert "findmy_migrate" not in steps
            assert "findmy_undo_migration" not in steps
            assert "findmy_migrate" not in steps["findmy_accounts"]["menu_options"]
            assert (
                "findmy_undo_migration"
                not in steps["findmy_account_actions"]["menu_options"]
            )
