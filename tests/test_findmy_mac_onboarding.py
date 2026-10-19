"""Recovery credentials are fresh, unused and bound to the signed-in account."""
from copy import deepcopy
from unittest.mock import AsyncMock

import pytest

from custom_components.homecircle._findmy_runtime.onboarding import fresh_recovery_pet
from custom_components.homecircle._findmy_runtime.provider import MacAnisetteProvider
from custom_components.homecircle._vendor_findmy import AsyncAppleAccount, LoginState
from custom_components.homecircle._vendor_findmy.errors import UnauthorizedError
from custom_components.homecircle._vendor_findmy.reports.endpoint_policy import MAC_COREADI_V1
from custom_components.homecircle._vendor_findmy.util.http import HttpResponse
from custom_components.homecircle.findmy_profile import configure_account
from tests.test_findmy_mac_runtime import machine


async def original_account(tmp_path):
    provider = MacAnisetteProvider(libs_path=tmp_path / "cache", state=machine())
    account = AsyncAppleAccount(
        provider, uid=provider.local_user_uuid, devid=provider.device_uuid,
        endpoint_policy=MAC_COREADI_V1, device_name="HomeCircle Find My",
    )
    account._username = "example@example.invalid"
    account._password = "synthetic-password"
    account._account_info = {"account_name": "example@example.invalid"}
    account._login_state = LoginState.LOGGED_IN
    account._login_state_data = {"adsid": "1234", "dsid": "1234", "mobileme_data": {"tokens": {"searchPartyToken": "synthetic-report-grant"}}}
    return configure_account(account)


async def test_recovery_pet_uses_separate_two_request_account_and_preserves_report_session(monkeypatch, tmp_path):
    account = await original_account(tmp_path)
    original = deepcopy(account.to_json())
    clones = []

    async def authenticate(clone):
        clones.append(clone)
        assert clone._anisette.owner is account._anisette
        assert clone.endpoint_policy == MAC_COREADI_V1
        assert clone._password == account._password
        assert (clone.local_user_uuid, clone.device_uuid) == (account.local_user_uuid, account.device_uuid)
        # _gsa_authenticate performs init/complete only. No login/delegate wrapper
        # is called by the recovery adapter.
        clone._login_state_data = {"adsid": "1234", "idms_pet": "fresh-unused-synthetic-pet"}
        clone._account_info = {"account_name": "EXAMPLE@example.invalid"}
        return LoginState.AUTHENTICATED

    monkeypatch.setattr(AsyncAppleAccount, "_gsa_authenticate", authenticate)
    try:
        assert await account.request_pet() == "fresh-unused-synthetic-pet"
        assert len(clones) == 1
        assert clones[0]._password is clones[0]._username is clones[0]._account_info is None
        assert clones[0]._login_state_data == {}
        assert clones[0]._closed
        assert account.to_json() == original
        assert not account._anisette._closed
    finally:
        await account.close()


@pytest.mark.parametrize("change", ["adsid", "name", "missing_pet", "verification", "failed"])
async def test_recovery_refuses_foreign_missing_or_verification_material_and_cleans_up(monkeypatch, tmp_path, change, caplog):
    account = await original_account(tmp_path)
    original = deepcopy(account.to_json())
    clones = []

    async def authenticate(clone):
        clones.append(clone)
        clone._login_state_data = {"adsid": "foreign" if change == "adsid" else "1234", "idms_pet": "" if change == "missing_pet" else "synthetic-private-pet"}
        clone._account_info = {"account_name": "foreign@example.invalid" if change == "name" else "example@example.invalid"}
        if change == "failed":
            raise RuntimeError("synthetic-private-response")
        return LoginState.REQUIRE_2FA if change == "verification" else LoginState.AUTHENTICATED

    monkeypatch.setattr(AsyncAppleAccount, "_gsa_authenticate", authenticate)
    try:
        with pytest.raises((UnauthorizedError, RuntimeError)):
            await fresh_recovery_pet(account)
        assert account.to_json() == original
        assert clones[0]._password is clones[0]._username is None
        assert clones[0]._login_state_data == {} and clones[0]._closed
        assert not account._anisette._closed
        assert "synthetic-private" not in caplog.text
    finally:
        await account.close()


async def test_mac_gsa_uses_proven_profile_and_bound_cpd_without_changing_legacy(monkeypatch, tmp_path):
    import plistlib
    account = await original_account(tmp_path)
    provider = account._anisette
    provider._cache = {"otp": "b3Rw", "mid": "bWlk"}
    import time
    provider._cache_window = int(time.time()) // 30
    account._http.post = AsyncMock(return_value=HttpResponse(200, plistlib.dumps({"Response": {"Status": {"ec": 0}}}), {}))
    try:
        await account._gsa_request({"o": "init", "u": "example@example.invalid", "A2k": b"synthetic", "ps": ["s2k"]})
        call = account._http.post.call_args
        headers = call.kwargs["headers"]
        cpd = plistlib.loads(call.kwargs["data"])["Request"]["cpd"]
        assert headers["User-Agent"] == "akd/1.0 CFNetwork/1404.0.5 Darwin/22.2.0"
        assert headers["X-MMe-Client-Info"] == provider.client_akd
        assert "Windows" not in headers["X-MMe-Client-Info"]
        assert cpd["X-Apple-I-SRL-NO"] == provider.serial
        assert cpd["X-Mme-Device-Id"] == provider.device_uuid
        assert all(type(cpd[k]) is bool for k in ["bootstrap", "icscrec", "pbe", "prkgen"])
        assert cpd["svct"] == "iCloud"
        assert call.kwargs["auto_retry"] is call.kwargs["allow_redirects"] is False
    finally:
        await account.close()


@pytest.mark.parametrize("trusted", [False, True])
async def test_mac_verification_keeps_native_headers_and_sms_json(monkeypatch, tmp_path, trusted):
    import plistlib
    import time
    from custom_components.homecircle._vendor_findmy.util.onboarding_http import _prepare

    account = await original_account(tmp_path)
    provider = account._anisette
    provider._cache = {"otp": "b3Rw", "mid": "bWlk"}
    provider._cache_window = int(time.time()) // 30
    account._login_state_data.update(idms_token="synthetic-identity-token")
    response = HttpResponse(200, plistlib.dumps({"Status": {"ec": 0}}))
    account._http.request = AsyncMock(return_value=response)
    url = account._ENDPOINT_2FA_TD_SUBMIT if trusted else account._ENDPOINT_2FA_SMS_SUBMIT
    data = None if trusted else {"securityCode": {"code": "123456"}}
    try:
        await account._sms_2fa_request("GET" if trusted else "POST", url, data=data)
        options = account._http.request.call_args.kwargs
        headers, _ = _prepare(options)
        assert headers["X-Mme-Client-Info"] == provider.client_akd
        assert headers["User-Agent"] == provider.akd_user_agent
        assert headers["X-Apple-I-SRL-NO"] == provider.serial
        assert not any("xcode" in key.casefold() or "xcode" in str(value).casefold() for key, value in headers.items())
        assert headers["Content-Type"] == ("text/x-xml-plist" if trusted else "application/json")
        if trusted:
            assert headers["Accept"] == "text/x-xml-plist"
    finally:
        await account.close()
