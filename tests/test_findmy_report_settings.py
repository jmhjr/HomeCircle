"""Acquire a missing report grant through the existing bounded settings hop."""

from copy import deepcopy
import asyncio
import plistlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.homecircle.findmy_setup import FindMySetup, FindMySetupError
from custom_components.homecircle._vendor_findmy.errors import UnhandledProtocolError
from custom_components.homecircle._vendor_findmy.reports.state import LoginState
from custom_components.homecircle._vendor_findmy.util.http import HttpResponse


def setup(tmp_path, response, status=200):
    transient = FindMySetup.create(tmp_path / "unused-libraries", onboarding=False)
    transient.align_new_identity = False
    account = transient.account
    account._username = "example@example.invalid"
    account._password = "synthetic-private-password"
    account._recovery_pet = "synthetic-private-pet"
    account._set_login_state(
        LoginState.LOGGED_IN,
        {
            "dsid": "synthetic-dsid",
            "mobileme_data": {"tokens": {"mmeAuthToken": "synthetic-mme"}},
        },
    )
    account._anisette._get_ani = AsyncMock()
    account.get_anisette_headers = AsyncMock(
        return_value={"X-Mme-Device-Id": "synthetic-device"}
    )
    account._http.post = AsyncMock(
        return_value=HttpResponse(status, plistlib.dumps(response))
    )
    account._gsa_authenticate = AsyncMock(
        side_effect=AssertionError("unexpected authentication")
    )
    transient.client_factory = AsyncMock(
        side_effect=AssertionError("unexpected recovery")
    )
    return transient, account


@pytest.mark.parametrize("cloudkit", [False, True])
async def test_settings_tracking_grant_allows_reconnect_and_never_repeats_the_hop(
    tmp_path, cloudkit
):
    tokens = {"searchPartyToken": "synthetic-report"}
    if cloudkit:
        tokens.update(
            cloudKitToken="synthetic-ck", mmeAuthToken="synthetic-settings-mme"
        )
    transient, account = setup(
        tmp_path, {"status": 0, "dsid": "synthetic-dsid", "tokens": tokens}
    )
    account.login = AsyncMock(return_value=LoginState.LOGGED_IN)
    transient.previous_items = {"existing": {"accessory": {}, "report": None}}
    transient.discover_new = False
    transient.restore_selected_items = Mock()
    try:
        assert (
            await transient.login(
                "example@example.invalid", "synthetic-private-password"
            )
            == "select"
        )
        transient.restore_selected_items.assert_called_once()
        assert account.service_tokens["searchPartyToken"] == "synthetic-report"
        assert account.service_tokens["mmeAuthToken"] == "synthetic-mme"
        if cloudkit:
            await account.ensure_cloudkit_token({})
            assert account._settings_cloudkit_pair == {
                "mmeAuthToken": "synthetic-settings-mme",
                "cloudKitToken": "synthetic-ck",
            }
        else:
            with pytest.raises(UnhandledProtocolError):
                await account.ensure_cloudkit_token({})
        await account.ensure_report_token()
        account._http.post.assert_awaited_once()
        request = account._http.post.await_args
        assert request.args == ("https://setup.icloud.com/setup/get_account_settings",)
        assert request.kwargs["auth"] == ("synthetic-dsid", "synthetic-mme")
        assert request.kwargs["auto_retry"] is False
        assert request.kwargs["allow_redirects"] is False
        assert request.kwargs["data"] == b""
        assert (
            request.kwargs["headers"]["x-mme-client-info"]
            == account.cloudkit_client_info
        )
        assert request.kwargs["headers"]["user-agent"] == "CloudKit/479 (13A404)"
        assert request.kwargs["headers"]["x-cloudkit-containerid"]
        transient.client_factory.assert_not_awaited()
        account._gsa_authenticate.assert_not_awaited()
    finally:
        await transient.close()


@pytest.mark.parametrize(
    "body,status",
    [
        ({"status": 1}, 200),
        ({"status": False}, 200),
        ({"dsid": "different-account"}, 200),
        ({"dsInfo": {"dsid": "different-account"}}, 200),
        ({"dsid": False}, 200),
        ({}, 401),
        ({}, 403),
        ({}, 503),
        ({}, 302),
        ({}, 204),
    ],
)
async def test_rejected_settings_cannot_import_any_grant_or_route(
    tmp_path, body, status, caplog
):
    response = {
        **body,
        "tokens": {
            "searchPartyToken": "synthetic-private-report",
            "cloudKitToken": "synthetic-private-ck",
            "mmeAuthToken": "synthetic-private-settings-mme",
        },
        "webservices": {
            "CKDatabaseService": {"url": "https://p24-ckdatabase.icloud.com"}
        },
    }
    transient, account = setup(tmp_path, response, status)
    before = deepcopy(account.service_tokens)
    try:
        with pytest.raises(FindMySetupError, match="findmy_report_access_unavailable"):
            await transient.ensure_report_access()
        assert account.service_tokens == before
        assert account._cloudkit_routes == {}
        assert account._settings_cloudkit_pair is None
        assert account._password is None and account._recovery_pet is None
        account._http.post.assert_awaited_once()
        account._gsa_authenticate.assert_not_awaited()
        assert "synthetic-private" not in caplog.text
        assert "synthetic-private" not in str(account._recovery_diagnostics)
        diagnostics = credential_diagnostics(caplog)
        assert diagnostics["report_grant_accepted"] is False
        assert diagnostics["held_report_token_present"] is False
        assert diagnostics["settings_searchparty_token_present"] is (
            True if status == 200 else None
        )
    finally:
        await transient.close()


async def test_mme_only_reply_is_terminal_after_one_request_even_without_explicit_profile(
    tmp_path,
):
    transient, account = setup(
        tmp_path, {"tokens": {"mmeAuthToken": "synthetic-settings-mme"}}
    )
    account.cloudkit_client_info = None
    try:
        for _ in range(2):
            with pytest.raises(
                FindMySetupError, match="findmy_report_access_unavailable"
            ):
                await transient.ensure_report_access()
        account._http.post.assert_awaited_once()
        assert set(account.service_tokens) == {"mmeAuthToken"}
        transient.client_factory.assert_not_awaited()
    finally:
        await transient.close()


async def test_valid_existing_tracking_grant_makes_no_settings_or_header_request(
    tmp_path, caplog,
):
    transient, account = setup(
        tmp_path, {"tokens": {"searchPartyToken": "unwanted-settings-token"}}
    )
    account.service_tokens["searchPartyToken"] = "synthetic-existing-report"
    try:
        await transient.ensure_report_access()
        assert account.service_tokens["searchPartyToken"] == "synthetic-existing-report"
        account._http.post.assert_not_awaited()
        account.get_anisette_headers.assert_not_awaited()
        assert account._settings_tokens_attempted is False
        assert account._password == "synthetic-private-password"
        assert not any(
            record.msg == "Find My tracking credential unavailable: diagnostics=%s"
            for record in caplog.records
        )
    finally:
        await transient.close()


@pytest.mark.parametrize("method", ["login", "verification"])
async def test_account_identity_guard_precedes_missing_token_settings_request(
    tmp_path, method
):
    transient, account = setup(
        tmp_path, {"tokens": {"searchPartyToken": "synthetic-report"}}
    )
    transient.account_guard = Mock(return_value=False)
    account.login = AsyncMock(return_value=LoginState.LOGGED_IN)
    transient.factor = SimpleNamespace(
        submit=AsyncMock(return_value=LoginState.LOGGED_IN)
    )
    try:
        with pytest.raises(FindMySetupError, match="findmy_account_mismatch"):
            if method == "login":
                await transient.login(
                    "example@example.invalid", "synthetic-private-password"
                )
            else:
                await transient.verify_code("synthetic-private-code")
        account._http.post.assert_not_awaited()
        account.get_anisette_headers.assert_not_awaited()
    finally:
        await transient.close()


@pytest.mark.parametrize("saved", [False, True])
async def test_missing_grant_at_final_confirmation_routes_to_terminal_abort(
    hass, saved
):
    from tests.test_findmy_saved_flow import flow_for

    flow, transient, provider, _, _ = flow_for(hass)
    flow.findmy_setup = transient
    flow.findmy_saved_only = saved
    transient.selected_payload = Mock(
        side_effect=FindMySetupError("findmy_report_access_unavailable")
    )
    result = await flow.async_step_findmy_confirm({"confirm": True})
    assert result == {"reason": "findmy_report_access_unavailable"}
    transient.close.assert_awaited_once()
    provider.pause_account.assert_not_awaited()


def credential_diagnostics(caplog):
    records = [
        record
        for record in caplog.records
        if record.msg == "Find My tracking credential unavailable: diagnostics=%s"
    ]
    assert len(records) == 1
    return records[0].args


@pytest.mark.parametrize("status", [200, 401])
async def test_missing_grant_emits_one_safe_stage_result_before_abort(
    tmp_path, status, caplog
):
    transient, account = setup(
        tmp_path,
        {"status": 0, "tokens": {}, "private": "synthetic-private-response"},
        status,
    )
    account._recovery_diagnostics["delegate_searchparty_token_present"] = False
    try:
        with pytest.raises(FindMySetupError, match="findmy_report_access_unavailable"):
            await transient.ensure_report_access()
        assert credential_diagnostics(caplog) == {
            "settings_attempted": True,
            "report_grant_accepted": False,
            "held_report_token_present": False,
            "delegate_searchparty_token_present": False,
            "settings_searchparty_token_present": False if status == 200 else None,
            "settings_http": status,
            "settings_status": 0 if status == 200 else None,
        }
        account._http.post.assert_awaited_once()
        transient.client_factory.assert_not_awaited()
        assert account._password is None and account._recovery_pet is None
        assert "synthetic-private" not in caplog.text
    finally:
        await transient.close()


@pytest.mark.parametrize(
    "http,service_status,expected_http,expected_status",
    [
        (100, -1000000, 100, -1000000),
        (599, 1000000, 599, 1000000),
        (99, -1000001, None, None),
        (600, 1000001, None, None),
        (True, False, None, None),
        (200.0, 0.0, None, None),
        ("synthetic-private-http", "synthetic-private-status", None, None),
    ],
)
async def test_grant_diagnostics_strictly_bound_and_reduce_malformed_values(
    tmp_path, caplog, http, service_status, expected_http, expected_status
):
    transient, account = setup(tmp_path, {})
    account.ensure_report_token = AsyncMock(
        side_effect=RuntimeError("synthetic-private-error")
    )
    account._settings_tokens_attempted = "synthetic-private-attempted"
    account._recovery_diagnostics.update(
        {
            "settings_http": http,
            "settings_status": service_status,
            "delegate_searchparty_token_present": 1,
            "settings_searchparty_token_present": "synthetic-private-token",
            "username": "synthetic-private-username",
            "tokens": {"searchPartyToken": "synthetic-private-token"},
            "response": "synthetic-private-response",
        }
    )
    try:
        with pytest.raises(FindMySetupError, match="findmy_report_access_unavailable"):
            await transient.ensure_report_access()
        assert credential_diagnostics(caplog) == {
            "settings_attempted": None,
            "report_grant_accepted": False,
            "held_report_token_present": False,
            "delegate_searchparty_token_present": None,
            "settings_searchparty_token_present": None,
            "settings_http": expected_http,
            "settings_status": expected_status,
        }
        assert "synthetic-private" not in caplog.text
        account._http.post.assert_not_awaited()
    finally:
        await transient.close()


async def test_new_settings_network_failure_cannot_report_an_older_response(
    tmp_path, caplog
):
    transient, account = setup(tmp_path, {})
    account._recovery_diagnostics.update(
        settings_http=200,
        settings_status=0,
        settings_searchparty_token_present=True,
    )
    account._http.post.side_effect = OSError("synthetic-private-network-error")
    try:
        with pytest.raises(FindMySetupError, match="findmy_report_access_unavailable"):
            await transient.ensure_report_access()
        result = credential_diagnostics(caplog)
        assert result["settings_attempted"] is True
        assert result["held_report_token_present"] is False
        assert result["settings_http"] is None
        assert result["settings_status"] is None
        assert result["settings_searchparty_token_present"] is None
        account._http.post.assert_awaited_once()
        assert "synthetic-private" not in caplog.text
    finally:
        await transient.close()


async def test_grant_cancellation_propagates_without_failure_log_or_retry(
    tmp_path, caplog
):
    transient, account = setup(tmp_path, {})
    account._http.post.side_effect = asyncio.CancelledError(
        "synthetic-private-cancellation"
    )
    try:
        with pytest.raises(asyncio.CancelledError):
            await transient.ensure_report_access()
        assert account._settings_tokens_attempted is True
        account._http.post.assert_awaited_once()
        account._gsa_authenticate.assert_not_awaited()
        transient.client_factory.assert_not_awaited()
        assert not any(
            record.msg == "Find My tracking credential unavailable: diagnostics=%s"
            for record in caplog.records
        )
        assert "synthetic-private" not in caplog.text
    finally:
        await transient.close()
