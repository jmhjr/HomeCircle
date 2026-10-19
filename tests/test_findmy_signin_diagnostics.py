"""Request-local GSA metadata without native calls, private data or network."""

import asyncio
import plistlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.homecircle._vendor_findmy.errors import AppleServiceUnavailableError
from custom_components.homecircle._vendor_findmy.reports.account import AsyncAppleAccount
from custom_components.homecircle._vendor_findmy.reports.endpoint_policy import (
    MAC_COREADI_V1,
    WINDOWS_ONBOARDING_V1,
)
from custom_components.homecircle._vendor_findmy.util.http import HttpResponse
from tests.test_findmy_endpoint_policy import StaticProvider


def account(policy=MAC_COREADI_V1):
    value = AsyncAppleAccount(StaticProvider(), endpoint_policy=policy)
    value._anisette.get_cpd = AsyncMock(return_value={"synthetic": True})
    return value


def reply(ec=0, hsc=200):
    return HttpResponse(200, plistlib.dumps({
        "Response": {"Status": {"ec": ec, "hsc": hsc, "em": "private-response-canary"}},
    }))


@pytest.mark.parametrize("phase", ["init", "complete"])
async def test_429_carries_request_phase_without_parsing_or_retry(phase, caplog):
    value = account()
    response = SimpleNamespace(
        status_code=429, ok=False, content=b"private-body-canary",
        headers={"Content-Type": "text/html; private-header-canary=private-value-canary"},
        plist=Mock(side_effect=AssertionError("Refusals must retain existing no-parse behavior")),
    )
    value._http.post = AsyncMock(return_value=response)
    try:
        with pytest.raises(AppleServiceUnavailableError) as caught:
            await value._gsa_request({"o": phase, "u": "private-email-canary"})
        assert caught.value.phase == phase
        assert caught.value.status_code == 429 and caught.value.retry_after is None
        value._http.post.assert_awaited_once()
        response.plist.assert_not_called()
        assert value.signin_diagnostics() == {
            "schema": 1, "phase": phase, "request_count": 1, "http": 429,
            "apple_code": None, "apple_hsc": None, "profile": "mac_coreadi_v1",
            "media_type": "html", "body_size": "small",
        }
        assert "canary" not in repr(value.signin_diagnostics()) + caplog.text
    finally:
        await value.close()


@pytest.mark.parametrize("second", ["http", "timeout", "cancelled"])
async def test_complete_failure_cannot_inherit_successful_init_metadata(second):
    value = account()
    error = TimeoutError() if second == "timeout" else asyncio.CancelledError()
    next_response = HttpResponse(429, b"private-body-canary") if second == "http" else error
    value._http.post = AsyncMock(side_effect=[reply(), next_response])
    try:
        await value._gsa_request({"o": "init"})
        assert value.signin_diagnostics()["apple_hsc"] == 200
        expected_error = AppleServiceUnavailableError if second == "http" else type(error)
        with pytest.raises(expected_error):
            await value._gsa_request({"o": "complete"})
        assert value.signin_diagnostics() == {
            "schema": 1, "phase": "complete", "request_count": 2,
            "http": 429 if second == "http" else None,
            "apple_code": None, "apple_hsc": None, "profile": "mac_coreadi_v1",
            "media_type": "missing" if second == "http" else None,
            "body_size": "small" if second == "http" else None,
        }
        assert value._http.post.await_count == 2
    finally:
        await value.close()


async def test_plist_apple_rejection_retains_only_bounded_status_fields():
    value = account()
    value._http.post = AsyncMock(return_value=reply(-80045, 500))
    try:
        response = await value._gsa_request({"o": "init", "u": "private-email-canary"})
        assert response["Status"]["em"] == "private-response-canary"
        assert value.signin_diagnostics() == {
            "schema": 1, "phase": "init", "request_count": 1, "http": 200,
            "apple_code": -80045, "apple_hsc": 500, "profile": "mac_coreadi_v1",
            "media_type": "missing", "body_size": "small",
        }
        assert "canary" not in repr(value.signin_diagnostics())
    finally:
        await value.close()


@pytest.mark.parametrize("bad", [True, "private-status-canary", 1.5, 1000001, -1000001])
async def test_non_numeric_or_out_of_range_apple_status_is_not_exposed(bad):
    value = account()
    value._http.post = AsyncMock(return_value=reply(bad, bad))
    try:
        await value._gsa_request({"o": "init"})
        assert value.signin_diagnostics()["apple_code"] is None
        assert value.signin_diagnostics()["apple_hsc"] is None
    finally:
        await value.close()


async def test_machine_header_failure_is_not_counted_as_an_apple_request():
    value = account()
    value._anisette.get_cpd.side_effect = RuntimeError("private-native-canary")
    value._http.post = AsyncMock()
    try:
        with pytest.raises(RuntimeError):
            await value._gsa_request({"o": "init"})
        assert value.signin_diagnostics()["phase"] == "init"
        assert value.signin_diagnostics()["request_count"] == 0
        assert value.signin_diagnostics()["http"] is None
        value._http.post.assert_not_awaited()
    finally:
        await value.close()


@pytest.mark.parametrize("policy,profile", [
    (None, "legacy"), (MAC_COREADI_V1, "mac_coreadi_v1"),
    (WINDOWS_ONBOARDING_V1, "windows_onboarding_v1"),
])
async def test_diagnostics_are_detached_transient_and_policy_attributed(policy, profile):
    value = account(policy)
    value._http.post = AsyncMock(return_value=reply())
    before = value.to_json()
    try:
        for _ in range(9):
            await value._gsa_request({"o": "init"})
        snapshot = value.signin_diagnostics()
        assert snapshot["profile"] == profile and snapshot["request_count"] == 8
        snapshot["http"] = 599
        assert value.signin_diagnostics()["http"] == 200
        assert value._http.post.await_count == 9  # The observer neither retries nor blocks calls.
        assert value.to_json() == before
    finally:
        await value.close()


async def test_getter_rejects_malformed_private_snapshot_without_values_or_side_effects():
    value = account()
    try:
        value._signin_diagnostics = {
            "schema": "private-schema-canary", "phase": ["private-phase-canary"],
            "request_count": True, "http": 999, "apple_code": "private-code-canary",
            "apple_hsc": False, "profile": "private-profile-canary", "raw": "private-canary",
            "media_type": ["private-media-canary"], "body_size": "private-size-canary",
        }
        assert value.signin_diagnostics() == {
            "schema": 1, "phase": None, "request_count": 0, "http": None,
            "apple_code": None, "apple_hsc": None, "profile": None,
            "media_type": None, "body_size": None,
        }
        assert value._signin_diagnostics["raw"] == "private-canary"
        value._signin_diagnostics = None
        assert value.signin_diagnostics()["request_count"] == 0
    finally:
        await value.close()


@pytest.mark.parametrize("mime,expected", [
    (None, "missing"), ("", "missing"), ("application/x-apple-plist", "plist"),
    ("text/x-xml-plist; charset=utf-8", "plist"), ("APPLICATION/XML", "xml"),
    ("text/html; private=private-header-canary", "html"), ("application/json", "json"),
    ("private-media-canary", "other"), ("text/html;" + "x" * 256, "other"),
])
async def test_response_media_class_never_exports_raw_header(mime, expected):
    value = account()
    headers = {"cOnTeNt-TyPe": mime} if mime is not None else {}
    value._http.post = AsyncMock(return_value=HttpResponse(429, b"private-body-canary", headers))
    try:
        with pytest.raises(AppleServiceUnavailableError):
            await value._gsa_request({"o": "init"})
        assert value.signin_diagnostics()["media_type"] == expected
        assert "canary" not in repr(value.signin_diagnostics())
        value._http.post.assert_awaited_once()
    finally:
        await value.close()


@pytest.mark.parametrize("size,expected", [
    (0, "empty"), (1, "small"), (1024, "small"), (1025, "medium"),
    (16384, "medium"), (16385, "large"),
])
async def test_response_size_is_category_only(size, expected):
    value = account()
    value._http.post = AsyncMock(return_value=HttpResponse(429, b"x" * size))
    try:
        with pytest.raises(AppleServiceUnavailableError):
            await value._gsa_request({"o": "complete"})
        assert value.signin_diagnostics()["body_size"] == expected
        assert set(value.signin_diagnostics()) == {
            "schema", "phase", "request_count", "http", "apple_code", "apple_hsc",
            "profile", "media_type", "body_size",
        }
    finally:
        await value.close()


@pytest.mark.parametrize("phase,expected", [
    ("init", "init"), ("complete", "complete"), (None, None),
    ("private-phase-canary", None), (["init"], None), (True, None),
])
def test_service_exception_phase_is_optional_and_strict(phase, expected):
    error = AppleServiceUnavailableError(429, "The Grand Slam request", phase=phase)
    assert error.phase == expected
    assert "private-phase-canary" not in str(error)
