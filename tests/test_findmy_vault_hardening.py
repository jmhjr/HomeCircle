"""Unchanged polling preserves encrypted bytes without bypassing validation."""

import base64
from contextlib import nullcontext
from copy import deepcopy
import os
from unittest.mock import patch

import pytest

from custom_components.homecircle.findmy_identity import prepare_state
from custom_components.homecircle.findmy_vault import Vault, VaultError


def selected_state():
    session = {
        "account": {"username": "owner@example.invalid", "password": "discarded"},
        "login": {
            "state": 3,
            "data": {
                "dsid": "synthetic-hardening-account",
                "mobileme_data": {"tokens": {"searchPartyToken": "synthetic-report"}},
            },
        },
    }
    items = {
        "selected": {
            "accessory": {
                "master_key": (b"a" * 28).hex(),
                "skn": (b"b" * 32).hex(),
                "sks": (b"c" * 32).hex(),
            },
            "report": {"battery_charging": True},
        }
    }
    ledger = prepare_state(session, items, {"selected": {"name": "Synthetic item"}})
    return session, items, ledger


@pytest.mark.parametrize("legacy", [False, True])
def test_unchanged_payload_does_not_encrypt_create_or_replace_files(tmp_path, legacy):
    vault = Vault(tmp_path / "account")
    session, items, ledger = selected_state()

    def save():
        if legacy:
            return vault.save(session, items["selected"]["accessory"])
        return vault.save_account(session, items, identity_state=ledger)

    save()
    ciphertext, key = vault.data_path.read_bytes(), vault.key_path.read_bytes()
    before = vault.data_path.stat()
    session["account"]["password"] = "another-discarded-password"
    session["account"]["info"] = {"name": "Discarded profile"}
    # Object insertion order is not a persisted state change.
    items["selected"]["accessory"] = dict(
        reversed(list(items["selected"]["accessory"].items()))
    )
    with (
        patch("custom_components.homecircle.findmy_vault.Fernet.encrypt") as encrypt,
        patch("custom_components.homecircle.findmy_vault.tempfile.mkstemp") as create,
        patch("custom_components.homecircle.findmy_vault.os.replace") as replace,
    ):
        save()
        if not legacy:
            vault.save_account(session, items)  # Default preserves the ledger, too.
    encrypt.assert_not_called()
    create.assert_not_called()
    replace.assert_not_called()
    after = vault.data_path.stat()
    assert (after.st_ino, after.st_mtime_ns) == (before.st_ino, before.st_mtime_ns)
    assert vault.data_path.read_bytes() == ciphertext
    assert vault.key_path.read_bytes() == key
    if not legacy:
        assert vault.load()["identity_state"] == ledger


@pytest.mark.parametrize(
    "change",
    ["report", "cursor", "token", "selection", "identity_metadata", "json_type"],
)
def test_real_persisted_changes_still_replace_the_vault(tmp_path, change):
    vault = Vault(tmp_path / "account")
    session, items, ledger = selected_state()
    vault.save_account(session, items, identity_state=ledger)
    before = vault.data_path.read_bytes()
    if change == "report":
        items["selected"]["report"]["last_seen"] = "2026-01-01T00:00:00+00:00"
    elif change == "cursor":
        items["selected"]["search_before"] = 42
    elif change == "token":
        session["login"]["data"]["mobileme_data"]["tokens"]["searchPartyToken"] += (
            "-new"
        )
    elif change == "selection":
        items["additional"] = deepcopy(items["selected"])
    elif change == "identity_metadata":
        next(iter(ledger["records"].values()))["metadata"]["name"] = "Updated name"
    else:
        # Python equality alone conflates True and 1; JSON persists distinct types.
        items["selected"]["report"]["battery_charging"] = 1
    with patch(
        "custom_components.homecircle.findmy_vault.os.replace", wraps=os.replace
    ) as replace:
        vault.save_account(session, items, identity_state=ledger)
    replace.assert_called_once()
    assert vault.data_path.read_bytes() != before
    loaded = vault.load()
    assert loaded["items"] == items
    assert loaded["identity_state"] == ledger
    assert loaded["session"]["login"]["data"] == session["login"]["data"]
    if change == "json_type":
        assert type(loaded["items"]["selected"]["report"]["battery_charging"]) is int


@pytest.mark.parametrize("fault", ["ciphertext", "permissions", "missing_key"])
def test_unchanged_candidate_never_bypasses_storage_validation(tmp_path, fault):
    vault = Vault(tmp_path / "account")
    session, items, ledger = selected_state()
    vault.save_account(session, items, identity_state=ledger)
    if fault == "ciphertext":
        vault.data_path.write_bytes(b"unreadable synthetic ciphertext")
    elif fault == "permissions":
        vault.data_path.chmod(0o644)
    else:
        vault.key_path.unlink()
    before = vault.data_path.read_bytes()
    with pytest.raises(VaultError):
        vault.save_account(session, items, identity_state=ledger)
    assert vault.data_path.read_bytes() == before


@pytest.mark.parametrize(
    "key", [b"not-base64!", base64.urlsafe_b64encode(b"short")],
    ids=["invalid_base64", "short_decoded"],
)
@pytest.mark.parametrize("operation", ["load", "save", "save_account"])
def test_malformed_key_refuses_load_and_save_without_replacement(tmp_path, key, operation):
    vault = Vault(tmp_path / "account")
    session, items, ledger = selected_state()
    vault.save_account(session, items, identity_state=ledger)
    vault.key_path.write_bytes(key)
    before = {
        child.name: (child.read_bytes(), child.stat().st_mode)
        for child in vault.root.iterdir()
    }
    call = {
        "load": vault.load,
        "save": lambda: vault.save(session, items["selected"]["accessory"]),
        "save_account": lambda: vault.save_account(session, items, identity_state=ledger),
    }[operation]
    with pytest.raises(VaultError) as error:
        call()
    assert str(error.value) == "Session encryption key is invalid; it was not replaced"
    assert error.value.__suppress_context__ is True
    assert {
        child.name: (child.read_bytes(), child.stat().st_mode)
        for child in vault.root.iterdir()
    } == before


@pytest.mark.parametrize("fault", ["missing_directory", "missing_vault", "key_read_error"])
def test_missing_or_unreadable_store_load_is_redacted_without_creating_files(tmp_path, fault):
    vault = Vault(tmp_path / "account")
    session, items, ledger = selected_state()
    vault.save_account(session, items, identity_state=ledger)
    if fault == "missing_directory":
        vault.key_path.unlink()
        vault.data_path.unlink()
        vault.root.rmdir()
    elif fault == "missing_vault":
        vault.data_path.unlink()
    before = {
        child.name: (child.read_bytes(), child.stat().st_mode)
        for child in vault.root.iterdir()
    } if vault.root.exists() else None
    read_bytes = type(vault.key_path).read_bytes

    def read(path):
        if path == vault.key_path:
            raise PermissionError("private-read-error-canary")
        return read_bytes(path)

    boundary = (
        patch.object(type(vault.key_path), "read_bytes", read)
        if fault == "key_read_error" else nullcontext()
    )
    with boundary, pytest.raises(VaultError) as error:
        vault.load()
    assert str(error.value) == "Session store is unreadable; it was not replaced"
    assert error.value.__suppress_context__ is True
    after = {
        child.name: (child.read_bytes(), child.stat().st_mode)
        for child in vault.root.iterdir()
    } if vault.root.exists() else None
    assert after == before
