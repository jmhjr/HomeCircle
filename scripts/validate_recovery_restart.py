"""Exercise synthetic recovery and coherent backup repair in fresh processes.

Every child denies socket connections and name resolution before importing HA.
Only newly created disposable storage is used. The default runs guard processes.
The optional HA storage extension passed on Core 2026.10.2; it never runs unless
explicitly selected. An earlier manually assembled runtime crashed at Python
shutdown and its native cause remains unattributed. This extension starts Core
normally and drives its synthetic provider separately, rather than loading the
full HomeCircle integration. This is not Apple acceptance or a repair tool.
An account backup deliberately excludes the independent recovery guard. Manually
restoring an older guard ledger cannot be detected by this local-only safeguard.
"""

from __future__ import annotations

import argparse
import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
from types import MappingProxyType
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = hashlib.sha256(b"dsid:synthetic-restart-owner").hexdigest()
OTHER = hashlib.sha256(b"dsid:synthetic-independent-owner").hexdigest()
ACCOUNT = "a" * 32
SOURCE = "synthetic_restart_prototype"
TARGET = "synthetic_restart_homecircle"
UNIQUE = f"{SOURCE}_accessory"
TRACKER = "device_tracker.example_recovery_restart_item"
CRASH_EXIT = 73
PROBES = 2
CHILD_TIMEOUT_SECONDS = 45
CHILD_REAP_TIMEOUT_SECONDS = 10
CHILD_WATCHDOG_SECONDS = 60
GUARD_PROCESS_COUNT = 13
# Twelve ordinary children, the held-lock child's watchdog/reap, and one
# watchdog interval for outer CLI/startup overhead. Individual limits stay fixed.
GUARD_CLI_TIMEOUT_SECONDS = (
    (GUARD_PROCESS_COUNT - 1)
    * (CHILD_TIMEOUT_SECONDS + CHILD_REAP_TIMEOUT_SECONDS)
    + CHILD_WATCHDOG_SECONDS
    + CHILD_REAP_TIMEOUT_SECONDS
    + CHILD_WATCHDOG_SECONDS
)


def _deny_network():
    """Use CPython audit hooks, including DNS, rather than an HTTP-only mock."""
    counts = {"blocked": 0}

    def deny(event, _args):
        if event in {
            "socket.connect",
            "socket.getaddrinfo",
            "socket.gethostbyname",
            "socket.gethostbyaddr",
            "socket.sendto",
            "socket.sendmsg",
        }:
            counts["blocked"] += 1
            raise OSError("synthetic validation denies network")

    sys.addaudithook(deny)
    for operation in (
        lambda: socket.getaddrinfo("network-probe.invalid", 443),
        lambda: _probe_connect(),
    ):
        try:
            operation()
        except OSError:
            pass
        else:
            raise AssertionError("network denial was ineffective")
    assert counts["blocked"] == PROBES
    return counts


def _probe_connect():
    with socket.socket() as connection:
        connection.connect(("192.0.2.1", 443))


def _emit(phase, counts, **result):
    assert counts["blocked"] == PROBES, "unexpected attempted network access"
    print(
        json.dumps(
            {
                "phase": phase,
                "pid": os.getpid(),
                "network_probes_blocked": PROBES,
                "unexpected_network_attempts": 0,
                **result,
            },
            sort_keys=True,
        ),
        flush=True,
    )


def _guard_path(directory):
    return directory / "config/.storage/homecircle_findmy/recovery_guard"


async def _guard_phase(directory, phase, counts):
    from custom_components.homecircle.findmy_recovery_guard import (
        RecoveryGuard,
        RecoveryGuardBlocked,
        RecoveryGuardStorageError,
    )

    guard = RecoveryGuard(_guard_path(directory))

    async def proof(outcome, identity=IDENTITY):
        async with guard.attempt(identity) as attempt:
            await attempt.before_dispatch()
            if outcome == "verified":
                await attempt.verified()
            elif outcome == "rejected":
                await attempt.refused()
            elif outcome == "crash":
                _emit(phase, counts, pending=1)
                os._exit(CRASH_EXIT)
            elif outcome == "hold":
                _emit(phase, counts, pending=1)
                await asyncio.Event().wait()

    if phase == "guard_verified":
        await proof("verified")
    elif phase == "guard_crash":
        await proof("crash")
    elif phase == "guard_restarted":
        status = await guard.status(IDENTITY)
        assert status["uncertain"] == 1 and status["pending"] == 0
        assert status["verified"] == 1
    elif phase == "guard_limit":
        await proof("rejected")
        await proof("rejected")
        status = await guard.status(IDENTITY)
        assert status["blocked"] and status["unresolved"] == 3
    elif phase == "guard_blocked":
        before = (_guard_path(directory) / "ledger.json").read_bytes()
        try:
            await proof("verified")
        except RecoveryGuardBlocked:
            pass
        else:
            raise AssertionError("restart lost the unresolved threshold")
        assert (_guard_path(directory) / "ledger.json").read_bytes() == before
    elif phase == "guard_acknowledged":
        result = await guard.reset(IDENTITY)
        assert result["unresolved"] == 0 and result["verified"] == 1
    elif phase == "guard_holding":
        await proof("hold")
    elif phase == "guard_observe_live":
        status = await guard.status(IDENTITY)
        assert status["pending"] == 1 and status["uncertain"] == 0
        try:
            await guard.reset(IDENTITY)
        except RecoveryGuardBlocked:
            pass
        else:
            raise AssertionError("acknowledgment entered another process's proof")
        await proof("verified", OTHER)
    elif phase == "guard_killed_restart":
        status = await guard.status(IDENTITY)
        assert status["uncertain"] == 1 and status["pending"] == 0
        assert status["verified"] == 1
        assert (await guard.status(OTHER))["verified"] == 1
    elif phase == "guard_ack_retry":
        status = await guard.reset(IDENTITY)
        assert status["unresolved"] == 0 and status["verified"] == 1
        await proof("verified")
    elif phase == "guard_corrupt":
        before = (_guard_path(directory) / "ledger.json").read_bytes()
        refused = 0
        for operation in (
            guard.status(IDENTITY),
            proof("verified"),
            guard.reset(IDENTITY),
        ):
            try:
                await operation
            except RecoveryGuardStorageError:
                refused += 1
            else:
                raise AssertionError("corrupt safeguard storage was accepted")
        assert refused == 3
        assert (_guard_path(directory) / "ledger.json").read_bytes() == before
        _emit(phase, counts, storage_operations_refused=refused)
        return
    elif phase == "guard_repaired":
        status = await guard.status(IDENTITY)
        assert status["verified"] == 2 and status["unresolved"] == 0
        await proof("rejected")
        await proof("uncertain")
    elif phase == "guard_retained":
        status = await guard.status(IDENTITY)
        assert status["rejected"] == status["uncertain"] == 1
        assert status["verified"] == 2 and status["pending"] == 0
    else:
        raise ValueError("unknown synthetic guard phase")
    _emit(phase, counts, status=await guard.status(IDENTITY))


@asynccontextmanager
async def _ha_storage(directory):
    from homeassistant import bootstrap, loader
    from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
    from homeassistant.core import HomeAssistant

    hass = HomeAssistant(str(directory / "config"))
    loader.async_setup(hass)
    config = {
        "homeassistant": {
            "name": "Synthetic recovery storage",
            ATTR_LATITUDE: 0.0,
            ATTR_LONGITUDE: 0.0,
            "elevation": 0,
            "unit_system": "metric",
            "time_zone": "UTC",
        },
        "http": {
            "server_host": "127.0.0.1",
            "server_port": int((directory / "http-port.txt").read_text()),
        },
        "zone": [],
    }
    # Core queries its source address with UDP connect during startup. Supply a
    # synthetic loopback answer without allowing even that route-probe socket.
    with patch(
        "homeassistant.components.network.util.async_get_source_ip",
        return_value="127.0.0.1",
    ):
        initialized = await bootstrap.async_from_config_dict(config, hass)
        try:
            assert initialized
            await hass.async_start()
            await hass.async_block_till_done()
            yield hass
        finally:
            await hass.async_stop()


async def _save_core(hass):
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    await registry._store.async_save(registry._data_to_save())
    await hass.config_entries._store.async_save(hass.config_entries._data_to_save())


async def _session(owner="synthetic-restart-owner"):
    from custom_components.homecircle._vendor_findmy import (
        AsyncAppleAccount,
        LocalAnisetteProvider,
    )

    account = AsyncAppleAccount(LocalAnisetteProvider())
    session = account.to_json()
    session["account"]["username"] = "synthetic-restart@example.invalid"
    session["login"] = {
        "state": 3,
        "data": {
            "dsid": owner,
            "mobileme_data": {
                "tokens": {"searchPartyToken": "synthetic-restart-report-token"}
            },
        },
    }
    await account.close()
    return session


async def _prepare_migration(directory):
    """Save committed config plus an interrupted registry move in real HA Stores."""
    from homeassistant.config_entries import ConfigEntry, ConfigEntryDisabler
    from homeassistant.helpers import entity_registry as er
    from homeassistant.helpers.storage import Store
    from custom_components.homecircle._vendor_findmy import FindMyAccessory
    from custom_components.homecircle.findmy_identity import prepare_state
    from custom_components.homecircle.findmy_migration import (
        account_items_for_migration,
        migration_payload,
    )
    from custom_components.homecircle.findmy_provider import account_root
    from custom_components.homecircle.findmy_reports import AccountClient
    from custom_components.homecircle.findmy_vault import Vault

    async with _ha_storage(directory) as hass:
        entries = []
        for identifier, domain in (
            (SOURCE, "homecircle_findmy"),
            (TARGET, "homecircle"),
        ):
            entry = ConfigEntry(
                domain=domain,
                entry_id=identifier,
                data={},
                options={},
                title="Synthetic storage restart",
                unique_id=None,
                version=1,
                minor_version=1,
                source="user",
                discovery_keys=MappingProxyType({}),
                subentries_data=[],
                disabled_by=ConfigEntryDisabler.USER,
            )
            # Both entries are disabled, so the supported add API persists them
            # without loading either integration or an Apple provider.
            await hass.config_entries.async_add(entry)
            entries.append(entry)
        source, target = entries
        registry = er.async_get(hass)
        original = registry.async_get_or_create(
            "device_tracker",
            "homecircle_findmy",
            UNIQUE,
            config_entry=source,
            suggested_object_id="example_recovery_restart_item",
        )
        assert original.entity_id == TRACKER
        session = await _session()
        accessory = FindMyAccessory(
            master_key=bytes([17]) * 28,
            skn=bytes([18]) * 32,
            sks=bytes([19]) * 32,
            paired_at=datetime(2026, 1, 1, tzinfo=UTC),
            name="Synthetic restart item",
        ).to_json()
        legacy = Vault(account_root(hass, {"storage_id": "legacy"}, True))
        legacy.save(session, accessory)
        original_bytes = legacy.data_path.read_bytes()
        data = legacy.load()
        metadata = migration_payload(data, source, [original])
        metadata["storage_id"] = ACCOUNT
        metadata["items"]["legacy"]["display_preferences"] = {
            "kind": "item",
            "display_name": "Synthetic retained label",
            "show_on_map": False,
        }
        items = account_items_for_migration(data)
        restored = AccountClient.restore(data, legacy.root / "unused-libs.bin")
        assert set(restored.items) == {"legacy"}
        await restored.close()
        identity_state = prepare_state(session, items, metadata["items"])
        native = Vault(account_root(hass, metadata, True))
        native.save_account(session, items, identity_state=identity_state)
        assert legacy.data_path.read_bytes() == original_bytes
        effective = {
            "findmy_enabled": True,
            "findmy_accounts": {ACCOUNT: metadata},
            "people": [],
            "members": {},
            "places": [],
            "primary_home": "zone.home",
        }
        hass.config_entries.async_update_entry(
            target, data=deepcopy(effective), options=deepcopy(effective)
        )
        await Store(hass, 1, f"homecircle_findmy_migration_{TARGET}").async_save(
            {
                "source": SOURCE,
                "action": "migrate",
                "storage_id": ACCOUNT,
                "disabled_by": None,
                "entities": [
                    {"entity_id": TRACKER, "unique_id": UNIQUE, "disabled_by": None}
                ],
            }
        )
        await _save_core(hass)
        assert registry.async_get(TRACKER).platform == "homecircle_findmy"


async def _start_provider(hass, *, accepted):
    """Restore actual SDK session/accessories; substitute only remote report polling."""
    from custom_components.homecircle.findmy_provider import DirectFindMy
    from custom_components.homecircle.findmy_reports import AccountClient

    target = hass.config_entries.async_get_entry(TARGET)
    accounts = target.options["findmy_accounts"]
    provider = DirectFindMy(hass, accounts, lambda _entities: None, TARGET)
    polls = []

    async def local_poll(client):
        polls.append(client)
        return {
            identifier: item.get("report") for identifier, item in client.items.items()
        }

    with patch.object(AccountClient, "poll", local_poll):
        try:
            await provider.async_start()
            await asyncio.gather(*provider.tasks.values())
            await hass.async_block_till_done()
            if accepted:
                assert provider.states[ACCOUNT] == "connected"
                assert len(polls) == 1
                assert set(provider.clients[ACCOUNT].items) == {"legacy"}
                assert provider.trackers[ACCOUNT]["legacy"].entity_id == TRACKER
                assert (
                    provider.trackers[ACCOUNT]["legacy"].unique_id
                    == "homecircle_findmy_" + UNIQUE
                )
            else:
                assert provider.states[ACCOUNT] == "unexpected_response"
                assert not provider.clients and not polls
        finally:
            await provider.async_stop()
            await hass.async_block_till_done()


async def _storage_phase(directory, phase, counts):
    from homeassistant.helpers import entity_registry as er
    from homeassistant.helpers.storage import Store
    from custom_components.homecircle.findmy_identity import prepare_state
    from custom_components.homecircle.findmy_migration import recover_pending
    from custom_components.homecircle.findmy_provider import account_root
    from custom_components.homecircle.findmy_vault import Vault

    if phase == "storage_crash_committed":
        await _prepare_migration(directory)
        _emit(phase, counts, committed_config=True, registry_move_pending=True)
        os._exit(CRASH_EXIT)
    async with _ha_storage(directory) as hass:
        target = hass.config_entries.async_get_entry(TARGET)
        metadata = target.options["findmy_accounts"][ACCOUNT]
        vault = Vault(account_root(hass, metadata))
        guard_before = (_guard_path(directory) / "ledger.json").read_bytes()
        if phase == "storage_recover":
            await recover_pending(hass, target)
            assert (
                await Store(
                    hass, 1, f"homecircle_findmy_migration_{TARGET}"
                ).async_load()
                is None
            )
            registered = er.async_get(hass).async_get(TRACKER)
            assert registered.platform == "homecircle"
            assert registered.unique_id == "homecircle_findmy_" + UNIQUE
            assert registered.config_entry_id == TARGET
            assert vault.load()["version"] == 2
            await _start_provider(hass, accepted=True)
            await _save_core(hass)
        elif phase in {"storage_corrupt", "storage_wrong_key"}:
            before = vault.data_path.read_bytes()
            await _start_provider(hass, accepted=False)
            assert vault.data_path.read_bytes() == before
        elif phase == "storage_foreign":
            original = vault.load()
            foreign = Vault(directory / "foreign_account")
            session = await _session("synthetic-foreign-owner")
            foreign.save_account(
                session,
                original["items"],
                identity_state=prepare_state(
                    session, original["items"], metadata["items"]
                ),
            )
            for name in ("session.key", "session.vault"):
                shutil.copyfile(foreign.root / name, vault.root / name)
            before = vault.data_path.read_bytes()
            await _start_provider(hass, accepted=False)
            assert vault.data_path.read_bytes() == before
        elif phase == "storage_restored":
            before = vault.load()
            assert before["identity_state"]["account_identity"] == IDENTITY
            record = next(iter(before["identity_state"]["records"].values()))
            assert record["metadata"] == metadata["items"]["legacy"]
            await _start_provider(hass, accepted=True)
            assert vault.load() == before
            registered = er.async_get(hass).async_get(TRACKER)
            assert registered.unique_id == "homecircle_findmy_" + UNIQUE
            assert dict(target.data) == dict(target.options)
        else:
            raise ValueError("unknown synthetic storage phase")
        assert (_guard_path(directory) / "ledger.json").read_bytes() == guard_before
        _emit(
            phase,
            counts,
            selected_keys_restored=phase in {"storage_recover", "storage_restored"},
            provider_refused=phase
            in {"storage_corrupt", "storage_wrong_key", "storage_foreign"},
            recovery_guard_unchanged=True,
        )


def _command(directory, phase):
    return [
        sys.executable,
        "-B",
        str(Path(__file__).resolve()),
        "--child",
        phase,
        "--directory",
        str(directory),
    ]


def _receipt(stdout, phase):
    # Child diagnostics are allowlisted JSON, never arbitrary SDK logs.
    lines = stdout.splitlines()
    assert len(lines) == 1 and len(lines[0]) < 4096, f"invalid child output: {phase}"
    result = json.loads(lines[0])
    assert result["phase"] == phase
    assert result["network_probes_blocked"] == PROBES
    assert result["unexpected_network_attempts"] == 0
    return result


def _progress(path, receipts, *, failure=None):
    if path is None:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if failure is None:
        for record in receipts:
            if record.get("failed"):
                failure = {key: record[key] for key in ("phase", "pid", "exit_code")}
                break
    path.write_text(
        json.dumps(
            {
                "schema": 1,
                "outcome": "failed" if failure else "in_progress",
                "completed": False,
                "receipts": receipts,
                "failure": failure,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def _run(directory, phase, receipts, *, crash=False, receipt_path=None):
    started = datetime.now(UTC).isoformat()
    child = subprocess.Popen(
        _command(directory, phase),
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    result = {
        "phase": phase,
        "pid": child.pid,
        "started_at_utc": started,
        "exit_code": None,
        "expected_fault_exit": crash,
    }
    receipts.append(result)
    _progress(receipt_path, receipts)
    try:
        stdout, stderr = child.communicate(timeout=CHILD_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        child.kill()
        stdout, stderr = child.communicate(timeout=CHILD_REAP_TIMEOUT_SECONDS)
        result["timed_out"] = True
    result["exit_code"] = child.returncode
    if stdout:
        try:
            observed = _receipt(stdout, phase)
            assert observed["pid"] == child.pid
            result.update(observed)
        except (AssertionError, ValueError, KeyError):
            result["invalid_child_output"] = True
    expected = CRASH_EXIT if crash else 0
    failed = (
        child.returncode != expected
        or result.get("timed_out")
        or result.get("invalid_child_output")
        or not stdout
    )
    result["failed"] = bool(failed)
    result["completed"] = not failed
    if receipt_path is not None and stderr:
        log = Path(receipt_path).parent / f"{len(receipts):02d}-{phase}-stderr.log"
        log.write_text(stderr)
        result["stderr_log"] = log.name
    _progress(
        receipt_path,
        receipts,
        failure={"phase": phase, "pid": child.pid, "exit_code": child.returncode}
        if failed
        else None,
    )
    assert not failed, f"synthetic child failed: {phase} exit={child.returncode}"
    return result


def _backup_account(directory):
    """Snapshot coherent local account/entry/registry state after all writers stop."""
    base = directory / "config/.storage"
    account = Path("homecircle_findmy/homecircle_accounts") / ACCOUNT
    names = (
        Path("core.config_entries"),
        Path("core.entity_registry"),
        account / "session.key",
        account / "session.vault",
    )
    backup = directory / "consistent_account_backup"
    for name in names:
        destination = backup / name
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        shutil.copy2(base / name, destination)
    assert not (backup / "homecircle_findmy/recovery_guard").exists()
    return names


def _restore_account(directory, names):
    """Harness-only manual repair, never restore the independent recovery guard."""
    ledger = _guard_path(directory) / "ledger.json"
    before = ledger.read_bytes()
    for name in names:
        shutil.copy2(
            directory / "consistent_account_backup" / name,
            directory / "config/.storage" / name,
        )
    assert ledger.read_bytes() == before


def run_validation(*, receipt_path=None, include_storage=False, storage_smoke=False):
    """Run reproducible destructive synthetic faults; delete all synthetic keys."""
    if storage_smoke:
        return _storage_smoke(receipt_path)
    receipts = []
    with tempfile.TemporaryDirectory(
        prefix="homecircle-recovery-restart-"
    ) as temporary:
        directory = Path(temporary).resolve()
        (directory / "config").mkdir(mode=0o700)
        if include_storage:
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                port = listener.getsockname()[1]
            (directory / "http-port.txt").write_text(str(port))
        for phase in (
            "guard_verified",
            "guard_crash",
            "guard_restarted",
            "guard_limit",
            "guard_blocked",
            "guard_acknowledged",
        ):
            _run(
                directory,
                phase,
                receipts,
                crash=phase == "guard_crash",
                receipt_path=receipt_path,
            )
        holder = subprocess.Popen(
            _command(directory, "guard_holding"),
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            assert holder.stdout is not None
            # A bounded child watchdog also bounds this pipe read.
            holding = {
                "phase": "guard_holding",
                "pid": holder.pid,
                "started_at_utc": datetime.now(UTC).isoformat(),
                "exit_code": None,
                "expected_fault_exit": True,
            }
            receipts.append(holding)
            _progress(receipt_path, receipts)
            holding.update(_receipt(holder.stdout.readline(), "guard_holding"))
            _run(directory, "guard_observe_live", receipts, receipt_path=receipt_path)
        except BaseException:
            if "network_probes_blocked" not in holding:
                holding["failed"] = True
            raise
        finally:
            holder.kill()
            holder.communicate(timeout=CHILD_REAP_TIMEOUT_SECONDS)
            holding["exit_code"] = holder.returncode
            holding.setdefault("failed", False)
            holding["completed"] = not holding["failed"]
            _progress(receipt_path, receipts)
        for phase in ("guard_killed_restart", "guard_ack_retry"):
            _run(directory, phase, receipts, receipt_path=receipt_path)
        ledger = _guard_path(directory) / "ledger.json"
        latest = ledger.read_bytes()
        ledger.write_bytes(b'{"version":1,"accounts":')
        _run(directory, "guard_corrupt", receipts, receipt_path=receipt_path)
        ledger.write_bytes(latest)
        _run(directory, "guard_repaired", receipts, receipt_path=receipt_path)
        if include_storage:
            _run(
                directory,
                "storage_crash_committed",
                receipts,
                crash=True,
                receipt_path=receipt_path,
            )
            _run(directory, "storage_recover", receipts, receipt_path=receipt_path)
            names = _backup_account(directory)
            account = (
                directory
                / "config/.storage/homecircle_findmy/homecircle_accounts"
                / ACCOUNT
            )
            (account / "session.vault").write_bytes(
                b"synthetic corrupted encrypted store"
            )
            _run(directory, "storage_corrupt", receipts, receipt_path=receipt_path)
            _restore_account(directory, names)
            _run(directory, "storage_restored", receipts, receipt_path=receipt_path)
            _run(directory, "storage_foreign", receipts, receipt_path=receipt_path)
            foreign_key = (account / "session.key").read_bytes()
            _restore_account(directory, names)
            (account / "session.key").write_bytes(foreign_key)
            _run(directory, "storage_wrong_key", receipts, receipt_path=receipt_path)
            _restore_account(directory, names)
            _run(directory, "storage_restored", receipts, receipt_path=receipt_path)
        _run(directory, "guard_retained", receipts, receipt_path=receipt_path)
    assert not directory.exists()
    return _finish(receipts, receipt_path, storage=include_storage)


def _storage_smoke(receipt_path):
    """Two children only: interrupted fixture, then one normal Core recovery."""
    receipts = []
    with tempfile.TemporaryDirectory(prefix="homecircle-recovery-smoke-") as temporary:
        directory = Path(temporary).resolve()
        (directory / "config").mkdir(mode=0o700)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        (directory / "http-port.txt").write_text(str(port))
        # A nonempty independent guard is retained through the account migration.
        # This fixture is written directly, without another process/proof.
        guard = _guard_path(directory)
        guard.mkdir(mode=0o700, parents=True)
        guard.parent.chmod(0o700)
        ledger = guard / "ledger.json"
        ledger.write_text(
            json.dumps(
                {
                    "version": 1,
                    "accounts": {
                        IDENTITY: {
                            "rejected": 1,
                            "uncertain": 1,
                            "verified": 2,
                            "pending": None,
                        }
                    },
                }
            )
        )
        ledger.chmod(0o600)
        _run(
            directory,
            "storage_crash_committed",
            receipts,
            crash=True,
            receipt_path=receipt_path,
        )
        _run(directory, "storage_recover", receipts, receipt_path=receipt_path)
    assert not directory.exists()
    return _finish(receipts, receipt_path, storage=True, smoke=True)


def _finish(receipts, receipt_path, *, storage=False, smoke=False):
    summary = {
        "schema": 1,
        "outcome": "passed",
        "completed": True,
        "processes": len(receipts),
        "distinct_processes": len({item["pid"] for item in receipts}),
        "network_probes_blocked": sum(
            item["network_probes_blocked"] for item in receipts
        ),
        "unexpected_network_attempts": 0,
        "synthetic_storage_removed": True,
        "core_storage_runtime_started": storage,
        "storage_smoke_only": smoke,
        "full_integration_lifecycle": False,
        "apple_requests": 0,
        "account_backup_repair_completed": storage and not smoke,
        "manual_account_backup_excludes_recovery_guard": storage and not smoke,
        "restoring_stale_guard_ledger_is_undetectable": True,
        "receipts": receipts,
    }
    if receipt_path is not None:
        receipt_path = Path(receipt_path)
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--include-storage",
        action="store_true",
        help="Opt in to the HA storage restart/repair extension",
    )
    mode.add_argument(
        "--storage-smoke",
        action="store_true",
        help="One interrupted fixture child and one normal Core child; no retry",
    )
    parser.add_argument("--child", help=argparse.SUPPRESS)
    parser.add_argument("--directory", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        import faulthandler

        faulthandler.enable()
        counts = _deny_network()
        # A stalled child, including a held account lock, has a hard upper bound.
        import signal

        signal.alarm(CHILD_WATCHDOG_SECONDS)
        sys.path.insert(0, str(ROOT))
        operation = _guard_phase if args.child.startswith("guard_") else _storage_phase
        asyncio.run(operation(args.directory, args.child, counts))
    else:
        result = run_validation(
            receipt_path=args.receipt,
            include_storage=args.include_storage,
            storage_smoke=args.storage_smoke,
        )
        print(
            json.dumps(
                {key: value for key, value in result.items() if key != "receipts"},
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
