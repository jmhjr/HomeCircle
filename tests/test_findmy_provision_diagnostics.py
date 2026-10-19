"""Bounded provisioning observations use fakes and never retain response fields."""

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from custom_components.homecircle._findmy_runtime import provider as module
from tests.test_findmy_mac_runtime import fakes, machine, responses

CANARY = "PRIVATE_RESPONSE_CANARY"
KEYS = {"schema", "stage", "request_count", "last_http", "last_apple_code", "last_apple_hsc", "failure"}


def initial():
    return {"schema": 1, "stage": "runtime", "request_count": 0,
            "last_http": None, "last_apple_code": None, "last_apple_hsc": None,
            "failure": None}


@pytest.mark.parametrize("restored", [False, True])
async def test_diagnostics_start_inert_are_detached_and_remain_after_close(tmp_path, restored):
    provider = module.MacAnisetteProvider(libs_path=tmp_path, state=machine() if restored else None)
    assert provider.safe_diagnostics() == initial()
    snapshot = provider.safe_diagnostics()
    snapshot["stage"] = CANARY
    assert provider.safe_diagnostics() == initial()
    if restored:
        await provider._get_ani()
        assert provider.safe_diagnostics() == initial()  # No new provisioning claim.
    await provider.close()
    assert provider.safe_diagnostics() == initial()


async def test_success_observes_each_operation_before_await_and_records_only_fixed_fields(monkeypatch, tmp_path):
    packets = responses()
    packets[-1]["Response"]["Status"].update(hsc=200, em=CANARY)
    calls, workers = fakes(monkeypatch, packets)
    provider = module.MacAnisetteProvider(libs_path=tmp_path)
    transport = module.BoundedHttpSession()
    request = transport.request
    seen = []

    async def observed_request(method, url, **kwargs):
        snapshot = provider.safe_diagnostics()
        seen.append(snapshot)
        assert snapshot["stage"] == ("lookup", "start_request", "finish_request")[len(seen) - 1]
        assert snapshot["request_count"] == len(seen) and snapshot["last_http"] is None
        assert snapshot["last_apple_code"] is snapshot["last_apple_hsc"] is None
        return await request(method, url, **kwargs)

    transport.request = observed_request
    monkeypatch.setattr(module, "BoundedHttpSession", lambda **kwargs: transport)
    worker_type = module.Worker

    class ObservedWorker(worker_type):
        async def open(self, *args):
            assert provider.safe_diagnostics()["stage"] == "initialize"
            return await super().open(*args)
        async def call(self, packet):
            snapshot = provider.safe_diagnostics()
            assert snapshot["stage"] == ("start_native" if packet["op"] == "start" else "finish_native")
            assert snapshot["last_http"] == 200 and snapshot["last_apple_code"] == 0
            return await super().call(packet)

    monkeypatch.setattr(module, "Worker", ObservedWorker)
    try:
        await provider._get_ani()
        result = provider.safe_diagnostics()
        assert result == {"schema": 1, "stage": "complete", "request_count": 3,
                          "last_http": 200, "last_apple_code": 0, "last_apple_hsc": 200,
                          "failure": None}
        assert set(result) == KEYS and CANARY not in json.dumps(result)
        assert len(calls) == 3 and all(worker.closed for worker in workers)
    finally:
        await provider.close()


@pytest.mark.parametrize("status", [401, 429, 503])
async def test_http_failure_retains_exact_lookup_status_without_retry(monkeypatch, tmp_path, status):
    calls, workers = fakes(monkeypatch, status=status)
    provider = module.MacAnisetteProvider(libs_path=tmp_path)
    try:
        with pytest.raises(module.IdentityUnavailable):
            await provider._get_ani()
        expected = {**initial(), "stage": "lookup", "request_count": 1,
                    "last_http": status, "failure": "http_refused"}
        assert provider.safe_diagnostics() == expected
        with pytest.raises(module.IdentityUnavailable):
            await provider._get_ani()
        assert provider.safe_diagnostics() == expected and len(calls) == 1
        assert all(worker.closed for worker in workers)
    finally:
        await provider.close()


@pytest.mark.parametrize("code,expected", [(-80045, -80045), (True, None), (1.5, None), (1000001, None)])
async def test_apple_rejection_records_only_bounded_numeric_status(monkeypatch, tmp_path, code, expected):
    packets = responses()
    packets[-1]["Response"]["Status"] = {"ec": code, "hsc": 500, "em": CANARY, "detail": CANARY}
    calls, _ = fakes(monkeypatch, packets)
    provider = module.MacAnisetteProvider(libs_path=tmp_path)
    try:
        with pytest.raises(module.IdentityUnavailable):
            await provider._get_ani()
        result = provider.safe_diagnostics()
        assert result["stage"] == "finish_request" and result["failure"] == "apple_refused"
        assert result["last_apple_code"] == expected and result["last_apple_hsc"] == 500
        assert result["last_http"] == 200 and result["request_count"] == len(calls) == 3
        assert CANARY not in json.dumps(result)
    finally:
        await provider.close()


@pytest.mark.parametrize("phase,failure", [("library", "library_unavailable"),
                                         ("initialize", "native_unavailable"),
                                         ("finish_native", "native_unavailable"),
                                         ("validate_state", "state_refused")])
async def test_native_and_state_failure_phase_is_distinct_from_http_rejection(monkeypatch, tmp_path, phase, failure):
    calls, _ = fakes(monkeypatch)
    provider = module.MacAnisetteProvider(libs_path=tmp_path)
    if phase == "library":
        monkeypatch.setattr(provider, "_library", AsyncMock(side_effect=RuntimeError(CANARY)))
    elif phase == "validate_state":
        monkeypatch.setattr(module, "validate_machine", lambda value: (_ for _ in ()).throw(ValueError(CANARY)))
    else:
        worker_type = module.Worker
        class FailedWorker(worker_type):
            async def open(self, *args):
                if phase == "initialize":
                    raise RuntimeError(CANARY)
                return await super().open(*args)
            async def call(self, packet):
                if packet["op"] == "finish":
                    raise RuntimeError(CANARY)
                return await super().call(packet)
        monkeypatch.setattr(module, "Worker", FailedWorker)
    try:
        with pytest.raises(module.IdentityUnavailable):
            await provider._get_ani()
        result = provider.safe_diagnostics()
        assert result["stage"] == phase and result["failure"] == failure
        assert result["request_count"] == len(calls) == (0 if phase in {"library", "initialize"} else 3)
        assert CANARY not in json.dumps(result)
    finally:
        await provider.close()


async def test_cleanup_failure_does_not_claim_complete(monkeypatch, tmp_path):
    _, workers = fakes(monkeypatch)
    transport = module.BoundedHttpSession()
    transport.close = AsyncMock(side_effect=OSError(CANARY))
    monkeypatch.setattr(module, "BoundedHttpSession", lambda **kwargs: transport)
    provider = module.MacAnisetteProvider(libs_path=tmp_path)
    try:
        with pytest.raises(module.IdentityUnavailable, match="cleanup_failed"):
            await provider._get_ani()
        result = provider.safe_diagnostics()
        assert result["stage"] == "validate_state" and result["failure"] == "cleanup_failed"
        assert result["request_count"] == 3 and all(worker.closed for worker in workers)
    finally:
        await provider.close()


async def test_timeout_is_a_fixed_category_without_exception_text(monkeypatch, tmp_path):
    fakes(monkeypatch)
    provider = module.MacAnisetteProvider(libs_path=tmp_path)
    monkeypatch.setattr(provider, "_library", AsyncMock(side_effect=TimeoutError(CANARY)))
    try:
        with pytest.raises(module.IdentityUnavailable):
            await provider._get_ani()
        assert provider.safe_diagnostics() == {**initial(), "stage": "library", "failure": "timeout"}
    finally:
        await provider.close()


async def test_cancelled_native_operation_preserves_phase_and_reaps(monkeypatch, tmp_path):
    _, workers = fakes(monkeypatch)
    worker_type = module.Worker
    class CancelledWorker(worker_type):
        async def call(self, packet):
            if packet["op"] == "finish":
                raise asyncio.CancelledError
            return await super().call(packet)
    monkeypatch.setattr(module, "Worker", CancelledWorker)
    provider = module.MacAnisetteProvider(libs_path=tmp_path)
    try:
        with pytest.raises(asyncio.CancelledError):
            await provider._get_ani()
        result = provider.safe_diagnostics()
        assert result["stage"] == "finish_native" and result["failure"] == "cancelled"
        assert result["request_count"] == 3 and all(worker.closed for worker in workers)
    finally:
        await provider.close()


async def test_malformed_diagnostic_values_cannot_escape_allowlists(tmp_path):
    provider = module.MacAnisetteProvider(libs_path=tmp_path)
    provider._provision_diagnostics = {"stage": [CANARY], "failure": {CANARY: True},
                                       "request_count": True, "last_http": 600,
                                       "last_apple_code": CANARY, "last_apple_hsc": True}
    assert provider.safe_diagnostics() == initial()
    await provider.close()
