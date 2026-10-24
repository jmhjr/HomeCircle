"""Explicit, reversible migration of one private prototype account."""

import asyncio
import json
from pathlib import Path
from uuid import uuid4

from homeassistant.config_entries import ConfigEntryDisabler
from homeassistant.helpers import entity_registry as er
import voluptuous as vol
from homeassistant.helpers import selector
from homeassistant.helpers.storage import Store

from .const import CONF_FINDMY_ACCOUNTS, CONF_FINDMY_ENABLED
from .findmy_provider import account_root, PREFIX, tracker_unique_id
from .findmy_storage import delete_account
from .findmy_setup import safe_label
from .findmy_vault import Vault, VaultError, account_identity


def migration_payload(data, old, entities):
    """Preflight identities without changing keys, reports, registry or sessions."""
    identity = account_identity(data["session"])
    items = (
        data["items"]
        if data.get("version") == 2
        else {"legacy": {"accessory": data["accessory"], "report": data.get("report")}}
    )
    selected = {}
    for identifier, item in items.items():
        suffix = "accessory" if identifier == "legacy" else identifier
        original_id = f"{old.entry_id}_{suffix}"
        matches = [entity for entity in entities if entity.unique_id == original_id]
        if len(matches) != 1:
            raise VaultError("Prototype tracker identity could not be matched")
        selected[identifier] = {
            "name": safe_label(item["accessory"].get("name"), "Find My item"),
            "type": old.options.get("item_types", {}).get(identifier, "other"),
            "unique_id": PREFIX + original_id,
        }
    if len(entities) != len(selected):
        raise VaultError("Prototype selection does not match its registered trackers")
    return {
        "label": "Apple Find My account",
        "account_identity": identity,
        "storage_id": old.data.get("storage_id", "legacy"),
        "items": selected,
        "migrated_from": old.entry_id,
    }


async def migrate_account(hass, target, old, accounts):
    """Adopt an existing vault only after consent, compensating registry failures."""
    registry = er.async_get(hass)
    originals = list(er.async_entries_for_config_entry(registry, old.entry_id))
    if not originals or any(entity.domain != "device_tracker" for entity in originals):
        raise VaultError("Unexpected prototype entities")

    def prototype_root():
        base = account_root(hass, {"storage_id": "legacy"})
        storage_id = old.data.get("storage_id")
        if storage_id is None:
            return base
        import re

        if not isinstance(storage_id, str) or not re.fullmatch(
            r"[a-f0-9]{32}", storage_id
        ):
            raise VaultError("Invalid prototype store")
        parent = base / "accounts"
        Vault(parent)._check(parent, directory=True)
        return parent / storage_id

    root = await hass.async_add_executor_job(prototype_root)
    # A running helper can still hold a pending recovery. Require it to be closed
    # rather than taking its state away midway through a protected operation.
    socket = Path(hass.config.path(".storage", "homecircle_findmy", "helper.sock"))
    if socket.exists():
        writer = None
        try:
            async with asyncio.timeout(5):
                reader, writer = await asyncio.open_unix_connection(
                    str(socket), limit=4096
                )
                writer.write(b'{"action":"health"}\n')
                await writer.drain()
                health = json.loads(await reader.readline())
                if health.get("busy") is not False:
                    raise VaultError("findmy_migration_busy")
        except (OSError, ValueError, TimeoutError):
            raise VaultError("findmy_migration_busy") from None
        finally:
            if writer:
                writer.close()
                await writer.wait_closed()
    data = await hass.async_add_executor_job(Vault(root).load)
    metadata = migration_payload(data, old, originals)
    if any(
        account.get("account_identity") == metadata["account_identity"]
        for account in accounts.values()
    ):
        raise VaultError("Account is already connected")
    for item in metadata["items"].values():
        if registry.async_get_entity_id(
            "device_tracker", "homecircle", item["unique_id"]
        ):
            raise VaultError("Tracker identity already exists")
    report_auth = data["session"].get("login", {}).get("data", {})
    if (
        data["session"].get("login", {}).get("state") != 3
        or not report_auth.get("dsid")
        or not report_auth.get("mobileme_data", {})
        .get("tokens", {})
        .get("searchPartyToken")
    ):
        raise VaultError("Prototype report session needs sign-in")
    # Validate SDK restoration and every future unique ID before changing registry.
    from .findmy_setup import sdk

    await hass.async_add_executor_job(sdk)
    from .findmy_reports import AccountClient

    restored = await hass.async_add_executor_job(
        AccountClient.restore, data, root.parent / "anisette-libs.bin"
    )
    await restored.close()
    for identifier, item in metadata["items"].items():
        tracker_unique_id("migration", identifier, item)
    metadata["storage_id"] = uuid4().hex
    original_disabled = old.disabled_by
    ledger = Store(hass, 1, f"homecircle_findmy_migration_{target.entry_id}")
    if await ledger.async_load():
        raise VaultError("An interrupted migration must be recovered first")
    await ledger.async_save(
        {
            "source": old.entry_id,
            "action": "migrate",
            "storage_id": metadata["storage_id"],
            "disabled_by": original_disabled.value if original_disabled else None,
            "entities": [
                {
                    "entity_id": entity.entity_id,
                    "unique_id": entity.unique_id,
                    "disabled_by": entity.disabled_by.value
                    if entity.disabled_by
                    else None,
                }
                for entity in originals
            ],
        }
    )
    metadata["migration_entities"] = [
        {
            "entity_id": entity.entity_id,
            "unique_id": entity.unique_id,
            "disabled_by": entity.disabled_by.value if entity.disabled_by else None,
        }
        for entity in originals
    ]
    changed = []
    try:
        new_root = await hass.async_add_executor_job(account_root, hass, metadata, True)
        await hass.async_add_executor_job(
            Vault(new_root).save_account,
            data["session"],
            account_items_for_migration(data),
        )
        if not await hass.config_entries.async_set_disabled_by(
            old.entry_id, ConfigEntryDisabler.USER
        ):
            raise VaultError("Prototype could not be unloaded")
        for original in originals:
            registry.async_update_entity_platform(
                original.entity_id,
                "homecircle",
                new_config_entry_id=target.entry_id,
                new_unique_id=PREFIX + original.unique_id,
            )
            changed.append(original)
            registry.async_update_entity(
                original.entity_id, disabled_by=original.disabled_by
            )
    except BaseException:
        # Cancellation must compensate too; identities/history remain in place.
        for original in reversed(changed):
            registry.async_update_entity_platform(
                original.entity_id,
                original.platform,
                new_config_entry_id=original.config_entry_id,
                new_unique_id=original.unique_id,
            )
            registry.async_update_entity(
                original.entity_id, disabled_by=original.disabled_by
            )
        await hass.config_entries.async_set_disabled_by(old.entry_id, original_disabled)
        await hass.async_add_executor_job(delete_account, hass, metadata)
        await ledger.async_remove()
        raise
    return metadata


async def migrate_form(flow, user_input):
    errors = {}
    entries = {
        entry.entry_id: entry
        for entry in flow.hass.config_entries.async_entries("homecircle_findmy")
        if entry.disabled_by is None
    }
    if not getattr(flow, "config_entry", None):
        return flow.async_abort(reason="findmy_migration_failed")
    if user_input is not None:
        old = entries.get(user_input.get("entry"))
        if not user_input.get("consent"):
            errors["base"] = "findmy_consent_required"
        elif old is None:
            errors["base"] = "findmy_migration_failed"
        else:
            try:
                accounts = flow.draft.setdefault(CONF_FINDMY_ACCOUNTS, {})
                metadata = await migrate_account(
                    flow.hass, flow.config_entry, old, accounts
                )
            except Exception as error:
                errors["base"] = (
                    "findmy_migration_busy"
                    if str(error) == "findmy_migration_busy"
                    else "findmy_migration_failed"
                )
            else:
                accounts[uuid4().hex] = metadata
                flow.draft[CONF_FINDMY_ENABLED] = True
                return flow.save()
    return flow.async_show_form(
        step_id="findmy_migrate",
        data_schema=vol.Schema(
            {
                vol.Required("entry"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {
                                "value": key,
                                "label": safe_label(entry.title, "Prototype account"),
                            }
                            for key, entry in entries.items()
                        ],
                        custom_value=False,
                    )
                ),
                vol.Required("consent", default=False): selector.BooleanSelector(),
            }
        ),
        errors=errors,
    )


async def recover_pending(hass, target):
    """Resolve an interrupted migration from registry metadata, never Apple keys."""
    from homeassistant.helpers.entity_registry import RegistryEntryDisabler

    store = Store(hass, 1, f"homecircle_findmy_migration_{target.entry_id}")
    pending = await store.async_load()
    if not pending:
        return
    config = target.options or target.data
    if pending.get("action") == "undo":
        from copy import deepcopy

        effective = deepcopy(dict(config))
        effective[CONF_FINDMY_ACCOUNTS] = {
            key: account
            for key, account in effective.get(CONF_FINDMY_ACCOUNTS, {}).items()
            if account.get("migrated_from") != pending["source"]
        }
        effective[CONF_FINDMY_ENABLED] = bool(effective[CONF_FINDMY_ACCOUNTS])
        moved = {record["entity_id"] for record in pending["entities"]}
        effective["items"] = [
            item for item in effective.get("items", []) if item not in moved
        ]
        for item in moved:
            if effective.get("members", {}).get(item, {}).get("kind") == "item":
                effective["members"].pop(item)
        hass.config_entries.async_update_entry(target, options=effective)
        config = effective
    committed = pending.get("action") != "undo" and any(
        account.get("migrated_from") == pending["source"]
        for account in config.get(CONF_FINDMY_ACCOUNTS, {}).values()
    )
    registry = er.async_get(hass)
    if committed:
        source = hass.config_entries.async_get_entry(pending["source"])
        if source and source.disabled_by is None:
            if not await hass.config_entries.async_set_disabled_by(
                source.entry_id, ConfigEntryDisabler.USER
            ):
                raise VaultError("Prototype could not be unloaded")
        for original in pending["entities"]:
            current = registry.async_get(original["entity_id"])
            if current is None:
                raise VaultError("Migration tracker disappeared")
            unique = PREFIX + original["unique_id"]
            if (
                current.platform != "homecircle"
                or current.unique_id != unique
                or current.config_entry_id != target.entry_id
            ):
                if (
                    current.platform != "homecircle_findmy"
                    or current.config_entry_id != pending["source"]
                ):
                    raise VaultError("Unexpected migration ownership")
                registry.async_update_entity_platform(
                    current.entity_id,
                    "homecircle",
                    new_config_entry_id=target.entry_id,
                    new_unique_id=unique,
                )
                registry.async_update_entity(
                    current.entity_id,
                    disabled_by=RegistryEntryDisabler(original["disabled_by"])
                    if original["disabled_by"]
                    else None,
                )
    else:
        for original in pending["entities"]:
            current = registry.async_get(original["entity_id"])
            if (
                current
                and current.platform == "homecircle"
                and current.config_entry_id == target.entry_id
            ):
                registry.async_update_entity_platform(
                    current.entity_id,
                    "homecircle_findmy",
                    new_config_entry_id=pending["source"],
                    new_unique_id=original["unique_id"],
                )
                registry.async_update_entity(
                    current.entity_id,
                    disabled_by=RegistryEntryDisabler(original["disabled_by"])
                    if original["disabled_by"]
                    else None,
                )
        source = hass.config_entries.async_get_entry(pending["source"])
        if source:
            await hass.config_entries.async_set_disabled_by(
                source.entry_id,
                ConfigEntryDisabler(pending["disabled_by"])
                if pending["disabled_by"]
                else None,
            )
    if not committed and pending.get("storage_id"):
        await hass.async_add_executor_job(
            delete_account, hass, {"storage_id": pending["storage_id"]}
        )
    # Force registry persistence before clearing the durable migration ledger.
    await registry._store.async_save(registry._data_to_save())
    await store.async_remove()


def account_items_for_migration(data):
    return (
        data["items"]
        if data.get("version") == 2
        else {"legacy": {"accessory": data["accessory"], "report": data.get("report")}}
    )
