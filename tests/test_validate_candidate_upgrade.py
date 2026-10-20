"""Guard real-source transitions and coherent synthetic-state rollback."""

import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "validate_candidate_upgrade_test", ROOT / "scripts/validate_candidate_upgrade.py"
)
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)


def test_hash_mismatch_does_not_inspect_or_replace_installed_source(
    tmp_path, monkeypatch
):
    archive = tmp_path / "baseline.zip"
    archive.write_bytes(b"untrusted archive")
    target = tmp_path / "config/custom_components/homecircle"
    target.mkdir(parents=True)
    (target / "original.py").write_text("saved = True\n")

    def unexpected_inspect(path):
        pytest.fail("Hash validation must happen before archive processing")

    monkeypatch.setattr(subject, "inspect_archive", unexpected_inspect)
    with pytest.raises(ValueError, match="recorded source"):
        subject.install_archive(archive, tmp_path / "config", expected_sha256="0" * 64)
    assert (target / "original.py").read_text() == "saved = True\n"


def test_rollback_replaces_source_instead_of_leaving_new_modules(tmp_path, monkeypatch):
    archive = tmp_path / "baseline.zip"
    archive.write_bytes(b"synthetic archive transport")
    target = tmp_path / "config/custom_components/homecircle"
    target.mkdir(parents=True)
    (target / "candidate_only.py").write_text("candidate = True\n")
    (target / "__pycache__").mkdir()
    (target / "__pycache__/candidate.pyc").write_bytes(b"old bytecode")
    payload = {
        "manifest.json": b'{"version":"synthetic"}',
        "original.py": b"original = True\n",
    }
    monkeypatch.setattr(subject, "inspect_archive", lambda path: payload)
    result = subject.install_archive(archive, tmp_path / "config")
    assert result["files"] == 2
    assert sorted(path.name for path in target.iterdir()) == [
        "manifest.json",
        "original.py",
    ]
    assert (target / "original.py").read_bytes() == payload["original.py"]


def test_stopped_snapshot_restores_coherent_storage_and_portrait_without_source(
    tmp_path,
):
    config = tmp_path / "config"
    account = config / ".storage/homecircle_findmy/homecircle_accounts/example"
    account.mkdir(parents=True)
    (account / "session.key").write_bytes(b"synthetic original key")
    (account / "session.vault").write_bytes(b"synthetic matching encrypted vault")
    (config / ".storage/core.config_entries").write_text("original options")
    portrait = config / "image/example"
    portrait.mkdir(parents=True)
    (portrait / "original").write_bytes(b"synthetic portrait")
    component = config / "custom_components/homecircle"
    component.mkdir(parents=True)
    (component / "source.py").write_text("candidate source")
    backup = tmp_path / "backup"
    subject.persistent_snapshot(config, backup)
    (account / "session.key").write_bytes(b"changed key")
    (account / "session.vault").write_bytes(b"changed vault")
    (config / ".storage/unmatched_writer").write_bytes(b"later state")
    (portrait / "original").write_bytes(b"changed portrait")
    subject.persistent_restore(config, backup)
    assert (account / "session.key").read_bytes() == b"synthetic original key"
    assert (
        account / "session.vault"
    ).read_bytes() == b"synthetic matching encrypted vault"
    assert (config / ".storage/core.config_entries").read_text() == "original options"
    assert not (config / ".storage/unmatched_writer").exists()
    assert (portrait / "original").read_bytes() == b"synthetic portrait"
    assert (component / "source.py").read_text() == "candidate source"


def test_restore_retains_later_guard_observations_instead_of_older_backup(tmp_path):
    config = tmp_path / "config"
    guard = config / ".storage/homecircle_findmy/recovery_guard"
    guard.mkdir(parents=True)
    ledger = guard / "ledger.json"
    ledger.write_text("earlier backup observations")
    (config / ".storage/core.config_entries").write_text("earlier account")
    backup = tmp_path / "backup"
    subject.persistent_snapshot(config, backup)
    ledger.write_text("later refused and uncertain exchanges")
    (config / ".storage/core.config_entries").write_text("later account")
    subject.persistent_restore(config, backup)
    assert ledger.read_text() == "later refused and uncertain exchanges"
    assert (config / ".storage/core.config_entries").read_text() == "earlier account"
    assert (
        backup / ".storage/homecircle_findmy/recovery_guard/ledger.json"
    ).read_text() == "earlier backup observations"


def test_missing_latest_guard_refuses_restore_before_storage_mutation(tmp_path):
    config = tmp_path / "config"
    guard = config / ".storage/homecircle_findmy/recovery_guard"
    guard.mkdir(parents=True)
    (guard / "ledger.json").write_text("older observations")
    entry = config / ".storage/core.config_entries"
    entry.write_text("earlier account")
    backup = tmp_path / "backup"
    subject.persistent_snapshot(config, backup)
    (guard / "ledger.json").unlink()
    guard.rmdir()
    entry.write_text("latest account must remain")
    with pytest.raises(ValueError, match="Latest recovery safeguard unavailable"):
        subject.persistent_restore(config, backup)
    assert entry.read_text() == "latest account must remain"
