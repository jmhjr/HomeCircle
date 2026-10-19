"""Selected native callback gate uses synthetic engines and HTTP only."""
from __future__ import annotations

import asyncio
import plistlib
import socket
import threading
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.homecircle._vendor_findmy.util import onboarding_anisette as module
from custom_components.homecircle._vendor_findmy.util.http import HttpResponse

START = "https://gsd.apple.com/grandslam/MidService/startMachineProvisioning"
FINISH = "https://gsd.apple.com/grandslam/MidService/finishMachineProvisioning"
LOOKUP_BODY = plistlib.dumps({"urls": {"midStartProvisioning": START, "midFinishProvisioning": FINISH}})


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch):
    # Patch only actual connect, preserving the event loop's local wakeup socket.
    monkeypatch.setattr(socket.socket, "connect", lambda *args: pytest.fail("real network forbidden"))


@pytest.fixture
def transport(monkeypatch):
    value = SimpleNamespace(request=AsyncMock(side_effect=[HttpResponse(200, LOOKUP_BODY),
                                                          HttpResponse(200, b"start"), HttpResponse(200, b"finish")]),
                            close=AsyncMock())
    monkeypatch.setattr(module, "BoundedHttpSession", lambda **kwargs: value)
    return value


async def test_exact_returned_three_callback_batch_and_no_retry(transport):
    gate = module.ProvisioningGate()
    def provision():
        for method, url, body in (("GET", module._LOOKUP, None), ("POST", START, b"one"), ("POST", FINISH, b"two")):
            response = gate.request(method, url, headers={"X-Synthetic": "private"}, body=body, timeout=5)
            assert response.status == 200
    await gate.run(provision)
    assert gate.count == 3 and transport.request.await_count == 3
    with pytest.raises(module.OnboardingTransportError, match="^native_request_unavailable$"):
        await gate.run(lambda: gate.request("GET", module._LOOKUP, headers={}))
    assert gate.closed and transport.request.await_count == 3
    await gate.close()


async def test_bad_lookup_bag_refuses_start_without_following_remote_urls(transport):
    transport.request.side_effect = None
    transport.request.return_value = HttpResponse(200, plistlib.dumps({"urls": {
        "midStartProvisioning": "https://evil.invalid/path", "midFinishProvisioning": FINISH}}))
    gate = module.ProvisioningGate()
    with pytest.raises(module.OnboardingTransportError, match="^native_request_unavailable$"):
        await gate.run(lambda: gate.request("GET", module._LOOKUP, headers={}))
    assert transport.request.await_count == gate.count == 1 and gate.closed


async def test_failed_request_consumes_budget_and_closes_gate(transport):
    transport.request.side_effect = None
    transport.request.return_value = HttpResponse(503, b"synthetic-private-response")
    gate = module.ProvisioningGate()
    with pytest.raises(module.OnboardingTransportError) as caught:
        await gate.run(lambda: gate.request("GET", module._LOOKUP, headers={}))
    assert "private-response" not in str(caught.value)
    assert transport.request.await_count == gate.count == 1 and gate.closed


async def test_restored_engine_pool_replaced_without_device_access(transport):
    gate = module.ProvisioningGate()
    previous = SimpleNamespace(clear=Mock())
    class Provider:
        provisioning_session = SimpleNamespace(_http=previous)
        @property
        def device(self):
            pytest.fail("restored device must not be edited")
    engine = SimpleNamespace(_ani_provider=Provider())
    await gate.run(lambda: gate.install(engine))
    assert engine._ani_provider.provisioning_session._http is gate
    previous.clear.assert_called_once()
    transport.request.assert_not_awaited()
    await gate.close()


async def test_user_form_wait_does_not_expire_local_get_data(transport):
    gate = module.ProvisioningGate()
    gate.deadline = time.monotonic() - 1000
    assert await gate.run(lambda: "synthetic-otp") == "synthetic-otp"
    transport.request.assert_not_awaited()
    await gate.close()


async def test_cleanup_error_does_not_replace_native_cancellation(transport):
    gate = module.ProvisioningGate()
    gate.close = AsyncMock(side_effect=module.OnboardingTransportError("native_worker_close_timeout"))
    def cancelled():
        raise asyncio.CancelledError
    with pytest.raises(asyncio.CancelledError):
        await gate.run(cancelled)
    gate.close.assert_awaited_once()


async def test_cancellation_closes_http_before_native_callback_can_continue(transport):
    entered, release = threading.Event(), threading.Event()
    gate = module.ProvisioningGate()
    def operation():
        entered.set()
        assert release.wait(1)
        assert gate.closed
        with pytest.raises(module.OnboardingTransportError, match="^native_gate_closed$"):
            gate.request("GET", module._LOOKUP, headers={})
    task = asyncio.create_task(gate.run(operation))
    while not entered.is_set():
        await asyncio.sleep(0)
    task.cancel()
    while not gate.closed:
        await asyncio.sleep(0)
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    transport.close.assert_awaited()
    assert not gate._native
    transport.request.assert_not_awaited()


@pytest.mark.parametrize("url", [START.replace("gsd.apple.com", "evil.invalid"), START + "?q=1",
                                 START + "\n", START.replace("gsd", "g\tsd"), START.replace("https", "http")])
def test_provision_url_is_strict(url):
    with pytest.raises(module.OnboardingTransportError):
        module._provision_url(url, "start")
