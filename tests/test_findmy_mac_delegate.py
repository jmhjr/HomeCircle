"""Mac delegation preserves the proven plist declaration through HTTP preparation."""

import base64
import plistlib
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.homecircle._findmy_runtime.provider import (
    MacAnisetteProvider,
    PROFILE,
    new_identity,
)
from custom_components.homecircle._vendor_findmy import AsyncAppleAccount, LoginState
from custom_components.homecircle._vendor_findmy.reports.endpoint_policy import (
    MAC_COREADI_V1,
    WINDOWS_ONBOARDING_V1,
)
from custom_components.homecircle._vendor_findmy.util.http import HttpResponse
from custom_components.homecircle._vendor_findmy.util.onboarding_http import _prepare
from custom_components.homecircle.findmy_profile import configure_account


def delegate_response(encoding, dsid="1234"):
    return HttpResponse(
        200,
        plistlib.dumps(
            {
                "status": 0,
                "dsid": dsid,
                "delegates": {
                    "com.apple.mobileme": {
                        "status": 0,
                        "service-data": {"tokens": {"searchPartyToken": "synthetic-report-grant"}},
                    }
                },
            },
            fmt=encoding,
        ),
    )


def authenticated(account):
    account._username = "input-alias@example.invalid"
    account._account_info = {"account_name": "canonical@example.invalid"}
    account._set_login_state(
        LoginState.AUTHENTICATED,
        {"adsid": "1234", "idms_pet": "example-pet"},
    )
    return account


@pytest.mark.parametrize("encoding", [plistlib.FMT_XML, plistlib.FMT_BINARY])
@pytest.mark.parametrize("dsid", ["1234", 1234])
async def test_mac_actual_delegate_keeps_proven_headers_body_and_identity(monkeypatch, tmp_path, encoding, dsid):
    identity = new_identity()
    identity["routing"] = 17106176
    provider = MacAnisetteProvider(
        libs_path=tmp_path / "unused-cache",
        state={"identity": identity, "store": {"synthetic": base64.b64encode(b"synthetic").decode()}},
    )
    provider._cache = {"otp": "b3Rw", "mid": "bWlk"}
    provider._cache_window = int(time.time()) // 30
    account = authenticated(configure_account(AsyncAppleAccount(
        provider, uid=provider.local_user_uuid, devid=provider.device_uuid,
        endpoint_policy=MAC_COREADI_V1,
    )))
    calls = []

    async def post(url, **options):
        headers, body = _prepare(options)
        calls.append((url, headers, plistlib.loads(body)))
        assert options["auto_retry"] is options["allow_redirects"] is False
        return delegate_response(encoding, dsid)

    monkeypatch.setattr(account._http, "post", post)
    try:
        assert await account._login_mobileme() == LoginState.LOGGED_IN
        assert len(calls) == 1
        url, headers, body = calls[0]
        assert url == "https://setup.icloud.com/setup/iosbuddy/loginDelegates"
        assert headers["Content-Type"] == "text/x-xml-plist"
        assert headers["Accept"] == "*/*"
        assert headers["User-Agent"] == "com.apple.iCloudHelper/282 CFNetwork/1404.0.5 Darwin/22.2.0"
        assert headers["X-Mme-Client-Info"] == MAC_COREADI_V1.profile("delegate").client_info
        assert headers["X-Mme-Device-Id"] == provider.device_uuid
        assert headers["X-Apple-I-SRL-NO"] == provider.serial
        assert headers["X-Apple-I-MD-LU"] == base64.b64encode(provider.local_user_uuid.encode()).decode()
        assert headers["Authorization"] == "Basic " + base64.b64encode(
            b"canonical@example.invalid:example-pet"
        ).decode()
        assert body == {
            "apple-id": "canonical@example.invalid",
            "password": "example-pet",
            "client-id": provider.local_user_uuid,
            "delegates": {"com.apple.mobileme": {}},
        }
        assert account.service_tokens["searchPartyToken"] == "synthetic-report-grant"
        assert account.dsid == "1234"
    finally:
        await account.close()


@pytest.mark.parametrize("policy", [None, WINDOWS_ONBOARDING_V1])
async def test_non_mac_actual_delegate_keeps_existing_content_type(monkeypatch, policy):
    provider = SimpleNamespace(
        identity=PROFILE,
        get_headers=AsyncMock(return_value={}),
        close=AsyncMock(),
    )
    account = authenticated(AsyncAppleAccount(provider, endpoint_policy=policy))
    prepared = []

    async def post(_url, **options):
        headers, _body = _prepare(options)
        prepared.append(headers)
        return delegate_response(plistlib.FMT_XML)

    monkeypatch.setattr(account._http, "post", post)
    try:
        assert await account._login_mobileme() == LoginState.LOGGED_IN
        assert len(prepared) == 1
        assert prepared[0]["Content-Type"] == "application/octet-stream"
    finally:
        await account.close()
