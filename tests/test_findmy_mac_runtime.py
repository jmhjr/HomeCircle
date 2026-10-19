"""Fresh identities and passwordless restoration use only synthetic machine material."""
from __future__ import annotations

import base64
from copy import deepcopy
from pathlib import Path
import plistlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.homecircle._findmy_runtime import provider as module
from custom_components.homecircle._findmy_runtime.provider import (
    IdentityUnavailable, MacAnisetteProvider, new_identity, validate_machine,
)
from custom_components.homecircle._vendor_findmy.reports.anisette import get_provider_from_mapping
from custom_components.homecircle._vendor_findmy import AsyncAppleAccount, LoginState
from custom_components.homecircle.findmy_profile import configure_account
from custom_components.homecircle.findmy_setup import FindMySetup


def machine():
    identity = new_identity()
    identity["routing"] = 17106176
    return {"identity": identity, "store": {"adi-state": base64.b64encode(b"synthetic-private-machine").decode()}}


def responses():
    return [
        {"urls": {
            "midStartProvisioning": "https://gsa.apple.com/grandslam/MidService/startMachineProvisioning",
            "midFinishProvisioning": "https://gsa.apple.com/grandslam/MidService/finishMachineProvisioning",
        }},
        {"Response": {"Status": {"ec": 0}, "spim": "c3BpbQ=="}},
        {"Response": {"Status": {"ec": 0}, "ptm": "cHRt", "tk": "dGs=", "X-Apple-I-MD-RINFO": "17106176"}},
    ]


def fakes(monkeypatch, packets=None, status=200):
    packets = deepcopy(responses() if packets is None else packets)
    calls, workers = [], []

    class Transport:
        async def request(self, method, url, **options):
            calls.append((method, url, deepcopy(options)))
            packet = packets.pop(0)
            return SimpleNamespace(status_code=status, plist=lambda: packet)

        async def close(self):
            pass

    class Worker:
        def __init__(self):
            self.closed = False
            self.calls = []
            workers.append(self)

        async def open(self, library, identity, stores):
            self.calls.append(("open", deepcopy(identity), deepcopy(stores)))
            return {"provisioned": bool(stores)}

        async def call(self, packet):
            self.calls.append(deepcopy(packet))
            if packet["op"] == "start":
                return {"cpim": "Y3BpbQ=="}
            if packet["op"] == "finish":
                return {"store": {"adi-state": base64.b64encode(b"synthetic-private-machine").decode()}}
            return {"otp": "b3Rw", "mid": "bWlk"}

        async def close(self):
            self.closed = True

    monkeypatch.setattr(module, "BoundedHttpSession", lambda **_: Transport())
    monkeypatch.setattr(module, "Worker", Worker)
    monkeypatch.setattr(module.MacAnisetteProvider, "_library", AsyncMock(return_value=Path("/synthetic/CoreADI")))
    return calls, workers


async def test_fresh_accounts_have_independent_identity_and_no_public_lab_paths(tmp_path):
    a, b = MacAnisetteProvider(libs_path=tmp_path / "cache"), MacAnisetteProvider(libs_path=tmp_path / "cache")
    try:
        assert a.device_uuid != b.device_uuid
        assert a.local_user_uuid != b.local_user_uuid
        assert a.host_uuid != b.host_uuid
        assert a.serial != b.serial
        assert a._machine_state is b._machine_state is None
        with pytest.raises(IdentityUnavailable, match="serialization_refused"):
            a.to_json()
        with pytest.raises(IdentityUnavailable):
            a.to_json(tmp_path / "never-written")
        assert not list(tmp_path.iterdir())
    finally:
        await a.close()
        await b.close()


async def test_fresh_provision_uses_only_lookup_start_finish_then_own_ten_headers(monkeypatch, tmp_path):
    calls, workers = fakes(monkeypatch)
    provider = MacAnisetteProvider(libs_path=tmp_path / "cache")
    try:
        await provider._get_ani()
        await provider._get_ani()
        headers = await provider.get_headers(provider.local_user_uuid, provider.device_uuid)
        assert len(calls) == 3
        assert [c[0] for c in calls] == ["GET", "POST", "POST"]
        assert plistlib.loads(calls[2][2]["data"])["Request"] == {"cpim": "Y3BpbQ=="}
        assert all(c[2]["headers"]["X-Mme-Device-Id"] == provider.device_uuid for c in calls)
        assert len(headers) == 10
        assert headers["X-Apple-I-MD-LU"] == base64.b64encode(provider.local_user_uuid.encode()).decode()
        assert headers["X-Apple-I-SRL-NO"] == provider.serial
        assert headers["X-Apple-I-Client-Time"].endswith("Z")
        assert "+00:00" not in headers["X-Apple-I-Client-Time"]
        assert headers["X-Apple-I-TimeZone"] == "UTC"
        assert all(w.closed for w in workers)
        assert not list(tmp_path.iterdir())
    finally:
        await provider.close()


async def test_restore_uses_same_identity_and_never_reprovisions_or_borrows_another_account(monkeypatch, tmp_path):
    calls, workers = fakes(monkeypatch)
    state = machine()
    provider = MacAnisetteProvider(libs_path=tmp_path / "cache", state=state)
    restored = None
    try:
        saved = provider.to_json()
        restored = get_provider_from_mapping(saved, libs_path=tmp_path / "cache")
        assert restored.device_uuid == state["identity"]["device_id"]
        first = await restored.get_headers(restored.local_user_uuid, restored.device_uuid)
        second = await restored.get_headers(restored.local_user_uuid, restored.device_uuid)
        assert first == second
        assert len(workers) == 1 and not calls
        with pytest.raises(IdentityUnavailable, match="account_mismatch"):
            await restored.get_headers(provider.local_user_uuid, new_identity()["device_id"])
        assert saved == provider.to_json() and state == machine_value(saved)
    finally:
        await provider.close()
        if restored:
            await restored.close()


def machine_value(value):
    return value["machine"]


@pytest.mark.parametrize("mutation", [
    lambda m: m["identity"].update(routing=True),
    lambda m: m["identity"].update(device_id="../foreign"),
    lambda m: m["identity"].update(host_uuid="x" * 32),
    lambda m: m.update(password="test-secret"),
    lambda m: m["store"].update({"../state": "YWJj"}),
    lambda m: m["store"].update({"adi.pb": "YWJj"}),
    lambda m: m["store"].update({"adi-state": "!"}),
    lambda m: m.update(store={}),
])
def test_corrupt_machine_is_refused_before_worker_or_network(mutation):
    state = machine()
    mutation(state)
    with pytest.raises(IdentityUnavailable, match="state_refused"):
        validate_machine(state)


@pytest.mark.parametrize("status", [401, 429, 503])
async def test_provision_refusal_is_one_attempt_and_cleanup(monkeypatch, tmp_path, status, caplog):
    calls, workers = fakes(monkeypatch, status=status)
    provider = MacAnisetteProvider(libs_path=tmp_path / "cache")
    try:
        with pytest.raises(IdentityUnavailable, match="provisioning_unavailable"):
            await provider._get_ani()
        with pytest.raises(IdentityUnavailable, match="already_attempted"):
            await provider._get_ani()
        assert len(calls) == 1 and all(w.closed for w in workers)
        assert provider._machine_state is None
        assert "synthetic-private" not in caplog.text
    finally:
        await provider.close()


async def test_foreign_provisioning_url_never_sent(monkeypatch, tmp_path):
    packets = responses()
    packets[0]["urls"]["midFinishProvisioning"] = "https://example.invalid/leak"
    calls, workers = fakes(monkeypatch, packets)
    provider = MacAnisetteProvider(libs_path=tmp_path / "cache")
    try:
        with pytest.raises(IdentityUnavailable):
            await provider._get_ani()
        assert len(calls) == 1 and all(w.closed for w in workers)
    finally:
        await provider.close()


async def test_close_clears_private_state_and_refuses_future_headers(monkeypatch, tmp_path):
    calls, _ = fakes(monkeypatch)
    provider = MacAnisetteProvider(libs_path=tmp_path / "cache", state=machine())
    uid, devid = provider.local_user_uuid, provider.device_uuid
    await provider.get_headers(uid, devid)
    await provider.close()
    assert provider._cache is provider._machine_state is provider._machine_id is None
    assert provider._machine_identity == {}
    with pytest.raises(IdentityUnavailable):
        await provider._get_ani()
    assert not calls


async def test_fresh_setup_binds_account_ids_to_machine_and_provisions_before_password(monkeypatch, tmp_path):
    calls, _ = fakes(monkeypatch)
    setup = FindMySetup.create(tmp_path / "cache")
    try:
        provider = setup.account._anisette
        assert (setup.account.local_user_uuid, setup.account.device_uuid) == (provider.local_user_uuid, provider.device_uuid)
        assert setup.account.endpoint_policy.identifier == "mac_coreadi_v1"
        assert setup.account.gsa_client_info == module.CLIENT_INFO
        assert setup.account._password is None
        await setup.prepare_identity()
        assert len(calls) == 3 and setup.account._password is None
        state = setup.account.to_json()
        state["account"]["password"] = None
        state["login"] = {"state": LoginState.LOGGED_IN.value, "data": {
            "dsid": "1234", "mobileme_data": {"tokens": {"searchPartyToken": "synthetic-report-token"}},
        }}
        restored = configure_account(AsyncAppleAccount.from_json(state, anisette_libs_path=tmp_path / "cache"))
        try:
            assert restored.to_json()["ids"] == state["ids"]
            assert restored.to_json()["anisette"] == state["anisette"]
            assert restored._password is None
            await restored.get_anisette_headers()
            assert len(calls) == 3
        finally:
            await restored.close()
    finally:
        await setup.close()


async def test_otp_rollover_uses_real_clock_and_same_machine(monkeypatch, tmp_path):
    calls, workers = fakes(monkeypatch)
    clock = [90]
    monkeypatch.setattr(module.time, "time", lambda: clock[0])
    provider = MacAnisetteProvider(libs_path=tmp_path / "cache", state=machine())
    try:
        await provider.get_headers(provider.local_user_uuid, provider.device_uuid)
        clock[0] += 31
        await provider.get_headers(provider.local_user_uuid, provider.device_uuid)
        assert len(workers) == 2 and not calls
        assert workers[0].calls[0][1:] == workers[1].calls[0][1:]
    finally:
        await provider.close()


async def test_machine_store_preserves_empty_native_files_across_serialization(tmp_path):
    from custom_components.homecircle._findmy_runtime.worker import blob

    state = machine()
    state["store"].update({"empty-a": "", "empty-b": "", "empty-c": ""})
    provider = MacAnisetteProvider(libs_path=tmp_path / "cache", state=state)
    try:
        saved = provider.to_json()
        restored = get_provider_from_mapping(saved, libs_path=tmp_path / "cache")
        try:
            assert restored.to_json() == saved
            assert saved["machine"]["store"] == state["store"]
            assert blob("", allow_empty=True) == b""
            with pytest.raises(ValueError):
                blob("")  # SPIM/PTM/TK still require actual protocol data.
        finally:
            await restored.close()
    finally:
        await provider.close()
    state["store"] = {"only-empty": ""}
    with pytest.raises(IdentityUnavailable, match="state_refused"):
        validate_machine(state)
