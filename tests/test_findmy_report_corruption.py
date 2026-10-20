"""Actual SDK parsing/decryption retains healthy reports beside corrupt records."""

import base64
from datetime import datetime, timezone
import json
import socket
from types import SimpleNamespace
from unittest.mock import AsyncMock

from cryptography.exceptions import InvalidTag
import pytest

from custom_components.homecircle._vendor_findmy import AsyncAppleAccount
from custom_components.homecircle._vendor_findmy.errors import UnhandledProtocolError
from custom_components.homecircle._vendor_findmy.keys import KeyPair
from custom_components.homecircle._vendor_findmy.reports.reports import LocationReport
from custom_components.homecircle._vendor_findmy.util.http import HttpResponse
from tests.test_findmy_report_service import encrypted_payload


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("a synthetic corruption test attempted a real socket")

    monkeypatch.setattr(socket, "socket", forbidden)


def encoded_report(key, payload):
    return {
        "id": key.hashed_adv_key_b64,
        "locationInfo": [base64.b64encode(payload).decode()],
    }


@pytest.mark.parametrize("corruption", ["gcm_tag", "ec_point", "unknown_hash", "all"])
async def test_actual_sdk_keeps_older_valid_and_other_item_reports(
    monkeypatch, caplog, corruption,
):
    """A newer corrupt record cannot replace an authenticated older observation."""
    selected, healthy, unknown = [KeyPair(bytes([value]) * 28) for value in (1, 3, 4)]
    timestamp = int(datetime(2026, 10, 18, tzinfo=timezone.utc).timestamp()) - 978307200
    older = encrypted_payload(selected, timestamp - 120)
    other = encrypted_payload(healthy, timestamp - 60)
    newer = encrypted_payload(selected, timestamp)
    bad_tag = newer[:-1] + bytes([newer[-1] ^ 1])
    bad_point = newer[:5] + b"\x04" + b"\0" * 56 + newer[62:]
    corruptions = {
        "gcm_tag": (bad_tag, InvalidTag),
        "ec_point": (bad_point, ValueError),
    }
    # Prove these fixtures exercise cryptographic rejection rather than merely
    # constructing records that the parser silently never sees.
    for payload, expected_error in corruptions.values():
        with pytest.raises(expected_error):
            LocationReport(payload, selected.hashed_adv_key_bytes).decrypt(selected)

    rows = [encoded_report(selected, older)]
    for category, (payload, _) in corruptions.items():
        if corruption in (category, "all"):
            rows.append(encoded_report(selected, payload))
    if corruption in ("unknown_hash", "all"):
        rows.append(encoded_report(unknown, encrypted_payload(unknown, timestamp + 30)))
    rows.append(encoded_report(healthy, other))
    body = json.dumps({"acsnLocations": {"statusCode": "200", "locationPayload": rows}}).encode()
    provider = SimpleNamespace(get_headers=AsyncMock(return_value={}), close=AsyncMock())
    account = AsyncAppleAccount(provider)
    account._login_state = type(account.login_state)(3)
    account._login_state_data = {
        "dsid": "fixture-account",
        "mobileme_data": {"tokens": {"searchPartyToken": "fixture-token"}},
    }
    request = AsyncMock(return_value=HttpResponse(200, body))
    monkeypatch.setattr(account._http, "post", request)
    authenticate = AsyncMock(side_effect=AssertionError("corrupt reports must not sign in"))
    monkeypatch.setattr(account, "_gsa_authenticate", authenticate)
    try:
        history = await account.fetch_location_history([selected, healthy])
        assert set(history) == {selected, healthy}
        assert [value.payload for value in history[selected]] == [older]
        assert [value.payload for value in history[healthy]] == [other]
        assert all(value.is_decrypted for values in history.values() for value in values)

        latest = await account.fetch_location([selected, healthy])
        assert latest[selected].payload == older
        assert latest[healthy].payload == other
        assert latest[selected].timestamp < latest[healthy].timestamp
        for value in latest.values():
            assert value.latitude == value.longitude == 0.0
            assert value.horizontal_accuracy == 12 and value.status == 64
        assert request.await_count == 2
        for call in request.await_args_list:
            assert {identifier for row in call.kwargs["json"]["fetch"]
                    for identifier in row["primaryIds"]} == {
                        selected.hashed_adv_key_b64, healthy.hashed_adv_key_b64,
                    }
        authenticate.assert_not_awaited()
    finally:
        await account.close()

    # Neither failed record contents nor account credentials belong in logs.
    for private in ("fixture-account", "fixture-token", body.decode(),
                    *(key.hashed_adv_key_b64 for key in (selected, healthy, unknown)),
                    *(row["locationInfo"][0] for row in rows)):
        assert private not in caplog.text


@pytest.mark.parametrize("malformation", [
    "row_type", "missing_id", "id_none", "id_number", "id_base64", "id_length",
    "info_none", "info_string", "info_mapping", "payload_base64", "payload_none",
    "payload_mapping", "payload_truncated",
])
async def test_actual_sdk_isolates_malformed_record_between_valid_neighbors(
    monkeypatch, caplog, malformation,
):
    selected, healthy = [KeyPair(bytes([value]) * 28) for value in (1, 3)]
    timestamp = int(datetime(2026, 10, 18, tzinfo=timezone.utc).timestamp()) - 978307200
    older = encrypted_payload(selected, timestamp - 120)
    other = encrypted_payload(healthy, timestamp - 60)
    malformed = encoded_report(selected, encrypted_payload(selected, timestamp))
    if malformation == "row_type":
        malformed = "invalid-record-fixture"
    elif malformation == "missing_id":
        malformed.pop("id")
    elif malformation.startswith("id_"):
        malformed["id"] = {
            "id_none": None, "id_number": 42, "id_base64": "a",
            "id_length": base64.b64encode(b"short").decode(),
        }[malformation]
    elif malformation.startswith("info_"):
        malformed["locationInfo"] = {
            "info_none": None, "info_string": "a", "info_mapping": {"a": "invalid"},
        }[malformation]
    else:
        malformed["locationInfo"] = [{
            "payload_base64": "a", "payload_none": None,
            "payload_mapping": {}, "payload_truncated": base64.b64encode(b"\0" * 10).decode(),
        }[malformation]]
    rows = [encoded_report(selected, older), malformed, encoded_report(healthy, other)]
    body = json.dumps({"acsnLocations": {"statusCode": "200", "locationPayload": rows}}).encode()
    provider = SimpleNamespace(get_headers=AsyncMock(return_value={}), close=AsyncMock())
    account = AsyncAppleAccount(provider)
    account._login_state = type(account.login_state)(3)
    account._login_state_data = {
        "dsid": "fixture-account",
        "mobileme_data": {"tokens": {"searchPartyToken": "fixture-token"}},
    }
    request = AsyncMock(return_value=HttpResponse(200, body))
    monkeypatch.setattr(account._http, "post", request)
    authenticate = AsyncMock(side_effect=AssertionError("malformed reports must not sign in"))
    monkeypatch.setattr(account, "_gsa_authenticate", authenticate)
    try:
        latest = await account.fetch_location([selected, healthy])
        assert set(latest) == {selected, healthy}
        assert latest[selected].payload == older
        assert latest[healthy].payload == other
        assert all(value.is_decrypted for value in latest.values())
        request.assert_awaited_once()
        authenticate.assert_not_awaited()
    finally:
        await account.close()
    for private in ("fixture-account", "fixture-token", body.decode(),
                    selected.hashed_adv_key_b64, healthy.hashed_adv_key_b64):
        assert private not in caplog.text


@pytest.mark.parametrize("payload_envelope", [None, {}, "invalid-envelope-fixture"])
async def test_invalid_report_envelope_is_a_batch_error_without_reauth(
    monkeypatch, payload_envelope,
):
    """A malformed batch cannot masquerade as a successful quiet poll."""
    body = json.dumps({"acsnLocations": {
        "statusCode": "200", "locationPayload": payload_envelope,
    }}).encode()
    provider = SimpleNamespace(get_headers=AsyncMock(return_value={}), close=AsyncMock())
    account = AsyncAppleAccount(provider)
    account._login_state = type(account.login_state)(3)
    account._login_state_data = {
        "dsid": "fixture-account",
        "mobileme_data": {"tokens": {"searchPartyToken": "fixture-token"}},
    }
    request = AsyncMock(return_value=HttpResponse(200, body))
    monkeypatch.setattr(account._http, "post", request)
    authenticate = AsyncMock(side_effect=AssertionError("malformed envelopes must not sign in"))
    monkeypatch.setattr(account, "_gsa_authenticate", authenticate)
    try:
        with pytest.raises(UnhandledProtocolError, match="^Invalid report response envelope$"):
            await account.fetch_location([KeyPair(b"\1" * 28)])
        request.assert_awaited_once()
        authenticate.assert_not_awaited()
    finally:
        await account.close()
