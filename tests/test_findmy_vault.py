"""Password-free, owner-only, tamper-resistant persistence across processes."""

import json
import subprocess
import sys
import pytest
from custom_components.homecircle.findmy_vault import Vault, VaultError


def payload():
    return (
        {
            "account": {
                "username": "example@example.invalid",
                "password": "example-secret",
            }
        },
        {
            "example_item": {
                "accessory": {"master_key": "synthetic-example-key"},
                "report": None,
            }
        },
    )


def test_passwordless_encrypted_session_survives_a_separate_process(tmp_path):
    root = tmp_path / "account"
    vault = Vault(root)
    session, items = payload()
    vault.save_account(session, items)
    encrypted = vault.data_path.read_bytes()
    assert b"example-secret" not in encrypted
    assert b"synthetic-example-key" not in encrypted
    assert vault.key_path.stat().st_mode & 0o077 == 0
    assert vault.data_path.stat().st_mode & 0o077 == 0
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from pathlib import Path; from custom_components.homecircle.findmy_vault import Vault; "
            "import sys,json; d=Vault(Path(sys.argv[1])).load(); print(json.dumps({'password_removed':d['session']['account']['password'] is None,'selected':list(d['items'])}))",
            str(root),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == {
        "password_removed": True,
        "selected": ["example_item"],
    }
    assert session["account"]["password"] == "example-secret"


@pytest.mark.parametrize(
    "fault", ["missing_key", "tampered", "open_permissions", "key_symlink"]
)
def test_recovery_state_is_not_overwritten_when_unsafe(tmp_path, fault):
    root = tmp_path / "account"
    vault = Vault(root)
    session, items = payload()
    vault.save_account(session, items)
    if fault == "missing_key":
        vault.key_path.unlink()
    elif fault == "tampered":
        vault.data_path.write_bytes(b"tampered synthetic data")
    elif fault == "open_permissions":
        vault.data_path.chmod(0o644)
    else:
        moved = root / "original-key"
        vault.key_path.rename(moved)
        vault.key_path.symlink_to(moved)
    before = vault.data_path.read_bytes()
    with pytest.raises(VaultError):
        vault.save_account(session, items)
    assert vault.data_path.read_bytes() == before


def test_only_report_service_token_and_no_profile_are_persisted(tmp_path):
    vault = Vault(tmp_path / "account")
    session, items = payload()
    session["account"]["info"] = {"first_name": "Example", "last_name": "Account"}
    session["login"] = {
        "state": 3,
        "data": {
            "dsid": "synthetic-account-id",
            "adsid": "unneeded",
            "idms_hb": "unneeded",
            "mobileme_data": {
                "tokens": {
                    "searchPartyToken": "example-report-token",
                    "otherService": "example-other-token",
                },
                "profile": "unneeded",
            },
        },
    }
    vault.save_account(session, items)
    saved = vault.load()["session"]
    assert saved["account"]["info"] is None
    assert saved["login"]["data"] == {
        "dsid": "synthetic-account-id",
        "mobileme_data": {"tokens": {"searchPartyToken": "example-report-token"}},
    }
    assert "example-other-token" not in str(saved)


async def test_delete_and_orphan_cleanup_leave_prototype_stores_intact(
    hass, tmp_path, monkeypatch
):
    from custom_components.homecircle.findmy_storage import (
        delete_account,
        prune_orphans,
    )

    monkeypatch.setattr(
        hass.config, "path", lambda *parts: str(tmp_path.joinpath(*parts))
    )
    base = tmp_path / ".storage" / "homecircle_findmy"
    prototype = base / "accounts" / ("c" * 32)
    session, items = payload()
    Vault(prototype).save_account(session, items)
    # The provider requires every parent namespace to be owner-only.
    base.chmod(0o700)
    prototype.parent.chmod(0o700)
    own = base / "homecircle_accounts"
    own.mkdir(mode=0o700)
    retained = own / ("a" * 32)
    removed = own / ("b" * 32)
    Vault(retained).save_account(session, items)
    Vault(removed).save_account(session, items)
    prune_orphans(hass, {"example": {"storage_id": "a" * 32}})
    assert retained.exists() and not removed.exists() and prototype.exists()
    delete_account(hass, {"storage_id": "a" * 32})
    assert not retained.exists() and prototype.exists()


async def test_native_crash_temporary_files_are_deleted_safely(
    hass, tmp_path, monkeypatch
):
    from custom_components.homecircle.findmy_storage import delete_account

    monkeypatch.setattr(
        hass.config, "path", lambda *parts: str(tmp_path.joinpath(*parts))
    )
    base = tmp_path / ".storage" / "homecircle_findmy"
    base.mkdir(parents=True, mode=0o700)
    parent = base / "homecircle_accounts"
    parent.mkdir(mode=0o700)
    root = parent / ("a" * 32)
    session, items = payload()
    Vault(root).save_account(session, items)
    temporary = root / ".session-example_crash"
    temporary.write_bytes(b"synthetic encrypted temporary bytes")
    temporary.chmod(0o600)
    delete_account(hass, {"storage_id": "a" * 32})
    assert not root.exists()
