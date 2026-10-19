"""Report-only service profile, actual SDK parsing and bounded synthetic HTTPS."""

import asyncio
import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import io
import json
import socket
import ssl
import struct
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock
import zlib

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import pytest

from custom_components.homecircle import findmy_report_service as service
from custom_components.homecircle._vendor_findmy import AsyncAppleAccount, FindMyAccessory
from custom_components.homecircle._vendor_findmy.errors import UnauthorizedError
from custom_components.homecircle._vendor_findmy.keys import KeyPair
from custom_components.homecircle._vendor_findmy.util.http import HttpResponse
from custom_components.homecircle.findmy_reports import AccountClient, Client


def provider_headers():
    return {
        "X-Apple-I-Client-Time": "2026-10-19T03:36:22Z", "X-Apple-I-TimeZone": "UTC",
        "loc": "en_US", "X-Apple-Locale": "en_US", "X-Apple-I-MD": "fixture-otp",
        "X-Apple-I-MD-M": "fixture-machine", "X-Apple-I-MD-LU": "fixture-local-user",
        "X-Apple-I-MD-RINFO": "17106176", "X-Mme-Device-Id": "fixture-device",
        "X-Apple-I-SRL-NO": "0",
    }


def gzip(value):
    return zlib.compress(value, wbits=16 + zlib.MAX_WBITS)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("a synthetic report test attempted a real socket")
    monkeypatch.setattr(socket, "socket", forbidden)


@pytest.fixture
async def dns(monkeypatch):
    resolver = AsyncMock(return_value=[(2, 1, 6, "", ("192.0.2.1", 443))])
    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", resolver)
    return resolver


class Response:
    def __init__(self, body=b"{}", headers=(), status=200):
        self.body = io.BytesIO(body)
        self.headers, self.status, self.closed = headers, status, False
    def getheaders(self):
        return self.headers
    def read(self, size):
        return self.body.read(size)
    def close(self):
        self.closed = True


def fake_connection(monkeypatch, response):
    class Connection:
        requests = []
        contexts = []
        def __init__(self, host, context, addresses, active):
            self.sock = None
            self.contexts.append(context)
            assert host == "gateway.icloud.com"
        def request(self, method, path, *, body, headers):
            self.requests.append((method, path, body, headers))
        def getresponse(self):
            return response
        def close(self):
            pass
    monkeypatch.setattr(service.bounded, "_Connection", Connection)
    return Connection


def test_report_headers_keep_exact_owned_snapshot_and_basic_auth():
    raw = provider_headers()
    before = dict(raw)
    result = service.headers(raw, "123", "fixture-token")
    assert {key: result[key] for key in raw} == before and raw == before
    assert result["X-MMe-Client-Info"] == (
        "<MacBookPro13,2> <macOS;13.1;22C65> <com.apple.icloud.searchpartyuseragent/1.0>"
    )
    assert result["User-Agent"] == "searchpartyuseragent/1 iMac13,1/13.6.4"
    assert result["x-apple-setup-proxy-request"] == "true"
    assert result["accept-version"] == "4" and result["x-apple-i-device-type"] == "1"
    assert result["Accept-Language"] == "en-US,en;q=0.9"
    assert result["Accept"] == "*/*" and result["Accept-Encoding"] == "gzip"
    assert base64.b64decode(result["Authorization"][6:]) == b"123:fixture-token"
    assert "Cookie" not in result


@pytest.mark.parametrize("change", [{"Cookie": "private"}, {"Authorization": "private"},
                                   {"X-Apple-I-MD": "private\r\ninjected"}])
def test_ambient_or_invalid_report_headers_are_refused(change):
    with pytest.raises(service.ReportProfileError, match="^invalid_report_request$"):
        service.headers({**provider_headers(), **change}, "123", "fixture-token")


def test_gzip_and_identity_enforce_both_exact_two_mib_limits():
    maximum = b"A" * service.MAX_RESPONSE_BYTES
    assert service.decode_response(maximum) == maximum
    assert service.decode_response(gzip(maximum), " GZip ") == maximum
    for raw, encoding in ((maximum + b"A", "identity"), (gzip(maximum + b"A"), "gzip")):
        with pytest.raises(service.ReportProfileError, match="^report_response_too_large$"):
            service.decode_response(raw, encoding)


@pytest.mark.parametrize("transform", [lambda raw: raw[:-1], lambda raw: raw + b"trailing",
                                      lambda raw: raw + raw, lambda raw: raw[:-8] + b"\0" * 8])
def test_gzip_requires_one_complete_member_and_valid_checksum(transform):
    with pytest.raises(service.ReportProfileError, match="^invalid_report_encoding$"):
        service.decode_response(transform(gzip(b"fixture")), "gzip")


@pytest.mark.parametrize("encoding", ["deflate", "br", "gzip, gzip"])
def test_unknown_or_combined_encoding_is_refused(encoding):
    with pytest.raises(service.ReportProfileError, match="^invalid_report_encoding$"):
        service.decode_response(b"fixture", encoding)


async def test_nonreport_endpoints_delegate_unchanged_and_close_refuses_late_report():
    expected = HttpResponse(200, b"fixture")
    original = SimpleNamespace(timeout=5, request=AsyncMock(return_value=expected), close=AsyncMock())
    adapter = service.ReportHttpAdapter(original)
    assert await adapter.post("https://setup.icloud.com/setup/iosbuddy/loginDelegates", data=b"fixture") is expected
    original.request.assert_awaited_once_with("POST", "https://setup.icloud.com/setup/iosbuddy/loginDelegates", data=b"fixture")
    assert adapter._reports is None and adapter.timeout == 5
    await adapter.close()
    with pytest.raises(service.ReportProfileError, match="^report_session_closed$"):
        await adapter.post(service.REPORT_URL)
    original.close.assert_awaited_once()


@pytest.mark.parametrize("headers,body,category", [
    ((("Content-Length", "2"),), b"a", "invalid_report_framing"),
    ((("Content-Length", "1"), ("Content-Length", "1")), b"a", "report_response_too_large"),
    ((("Content-Encoding", "gzip"), ("Content-Encoding", "gzip")), b"a", "invalid_report_encoding"),
    ((("Transfer-Encoding", "chunked"), ("Content-Length", "0")), b"", "invalid_report_framing"),
    ((), b"x" * (service.MAX_RESPONSE_BYTES + 1), "report_response_too_large"),
])
async def test_report_response_framing_limits(monkeypatch, dns, headers, body, category):
    fake_connection(monkeypatch, Response(body, headers))
    transport = service._ReportTransport()
    with pytest.raises(service.ReportProfileError, match="^" + category + "$"):
        await transport.post(service.REPORT_URL, headers=provider_headers(), auth=("123", "fixture"), json={})
    await transport.close()


@pytest.mark.parametrize("status,headers", [(401, ()), (403, ()), (200, (("WWW-Authenticate", "fixture"),))])
async def test_report_auth_refusal_is_terminal_without_reauthentication(monkeypatch, dns, status, headers):
    connection = fake_connection(monkeypatch, Response(status=status, headers=headers))
    transport = service._ReportTransport()
    with pytest.raises(UnauthorizedError, match="^Apple rejected report access$"):
        await transport.post(service.REPORT_URL, headers=provider_headers(), auth=("123", "fixture"), json={})
    assert len(connection.requests) == 1
    await transport.close()


async def test_redirect_is_not_followed_and_set_cookie_is_not_reused(monkeypatch, dns):
    connection = fake_connection(monkeypatch, Response(status=302, headers=(
        ("Location", "https://example.invalid/"), ("Set-Cookie", "private-fixture"))))
    transport = service._ReportTransport()
    response = await transport.post(service.REPORT_URL, headers=provider_headers(), auth=("123", "fixture"), json={})
    assert response.status_code == 302 and len(connection.requests) == 1
    assert "Cookie" not in connection.requests[0][3]
    await transport.close()


async def test_unverified_tls_is_refused_before_connect(monkeypatch, dns):
    connection = fake_connection(monkeypatch, Response())
    transport = service._ReportTransport()
    transport._context = ssl._create_unverified_context()
    with pytest.raises(service.ReportProfileError, match="^report_tls_refused$"):
        await transport.post(service.REPORT_URL, headers=provider_headers(), auth=("123", "fixture"), json={})
    assert not connection.requests
    await transport.close()


async def test_other_report_url_refused_before_dns(dns):
    transport = service._ReportTransport()
    with pytest.raises(service.ReportProfileError, match="^invalid_report_request$"):
        await transport.post("https://gateway.icloud.com/findmyservice/v2/fetch?other", headers=provider_headers(), auth=("123", "fixture"), json={})
    dns.assert_not_awaited()
    await transport.close()


@pytest.mark.parametrize("version", [1, 2])
async def test_both_restore_paths_install_report_adapter_without_mutating_saved_state(monkeypatch, version):
    original = SimpleNamespace(timeout=5, close=AsyncMock())
    account = SimpleNamespace(_http=original)
    monkeypatch.setattr(AsyncAppleAccount, "from_json", lambda *args, **kwargs: account)
    accessory = FindMyAccessory(master_key=b"\1" * 28, skn=b"\2" * 32, sks=b"\3" * 32,
                               paired_at=datetime(2026, 1, 1, tzinfo=timezone.utc), identifier="fixture")
    row = {"accessory": accessory.to_json(), "report": None}
    saved = {"version": version, "session": {"private-fixture": True}}
    saved.update({"items": {"fixture": row}} if version == 2 else row)
    before = deepcopy(saved)
    client = Client.restore(saved, None)
    assert isinstance(account._http, service.ReportHttpAdapter)
    assert account._http.original is original and saved == before
    assert (version == 2) == isinstance(client, AccountClient)
    await account._http.close()


def encrypted_payload(key, timestamp):
    ephemeral = ec.derive_private_key(2, ec.SECP224R1())
    public = ephemeral.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    symmetric = hashlib.sha256(key.dh_exchange(ephemeral.public_key()) + b"\0\0\0\1" + public).digest()
    plaintext = struct.pack(">iiBB", 0, 0, 12, 64)
    encrypted = AESGCM(symmetric[:16]).encrypt(symmetric[16:], plaintext, None)
    return struct.pack(">I", timestamp) + b"\1" + public + encrypted


async def test_actual_sdk_body_and_parser_keep_all_six_hundred_gzip_reports(monkeypatch, dns):
    key = KeyPair(b"\1" * 28)
    newest = int(datetime.now(timezone.utc).timestamp()) - 60 - 978307200
    payloads = [base64.b64encode(encrypted_payload(key, newest - index * 60)).decode() for index in range(600)]
    data = json.dumps({"acsnLocations": {"statusCode": "200", "locationPayload": [
        {"id": key.hashed_adv_key_b64, "locationInfo": payloads}]}}).encode()
    response = Response(gzip(data), (("Content-Encoding", "gzip"),))
    connection = fake_connection(monkeypatch, response)
    provider = SimpleNamespace(get_headers=AsyncMock(return_value=provider_headers()), close=AsyncMock())
    account = AsyncAppleAccount(provider)
    account._login_state = type(account.login_state)(3)
    account._login_state_data = {"dsid": "123", "mobileme_data": {"tokens": {"searchPartyToken": "fixture"}}}
    identity = (account._uid, account._devid, deepcopy(account._login_state_data))
    original_context = account._http._ssl
    service.configure_report_account(account)
    try:
        found = await account.fetch_location_history([key])
        assert len(found[key]) == 600 and all(value.is_decrypted for value in found[key])
        assert found[key][-1].latitude == found[key][-1].longitude == 0.0
        assert found[key][-1].horizontal_accuracy == 12
        assert len(connection.requests) == 1
        method, path, body, headers = connection.requests[0]
        assert method == "POST" and path == "/findmyservice/v2/fetch"
        packet = json.loads(body)
        row, = packet["fetch"]
        assert row["primaryIds"] == [key.hashed_adv_key_b64] and row["secondaryIds"] == []
        assert row["ownedDeviceIds"] == [] and "sharedFetch" not in packet
        assert row["endDate"] - row["startDate"] == 7 * 86400000
        assert headers["Accept-Encoding"] == "gzip" and "Cookie" not in headers
        assert connection.contexts == [original_context]
        assert identity == (account._uid, account._devid, account._login_state_data)
    finally:
        await account.close()
    assert response.closed


async def test_sdk_empty_report_response_does_not_retry_or_sign_in(monkeypatch, dns):
    key = KeyPair(b"\1" * 28)
    connection = fake_connection(monkeypatch, Response(b""))
    provider = SimpleNamespace(get_headers=AsyncMock(return_value=provider_headers()), close=AsyncMock())
    account = AsyncAppleAccount(provider)
    account._login_state = type(account.login_state)(3)
    account._login_state_data = {"dsid": "123", "mobileme_data": {"tokens": {"searchPartyToken": "fixture"}}}
    authenticate = AsyncMock(side_effect=AssertionError("reports must not sign in"))
    monkeypatch.setattr(account, "_gsa_authenticate", authenticate)
    service.configure_report_account(account)
    try:
        assert await account.fetch_location([key]) == {key: None}
        assert len(connection.requests) == 1
        authenticate.assert_not_awaited()
    finally:
        await account.close()


async def test_cancelled_report_worker_is_stopped_and_joined(monkeypatch, dns):
    entered, exited = threading.Event(), threading.Event()
    def exchange(*args):
        active = args[-1]
        entered.set()
        assert active.stopped.wait(1)
        exited.set()
        raise TimeoutError("private-fixture-error")
    monkeypatch.setattr(service, "_exchange_report", exchange)
    transport = service._ReportTransport()
    task = asyncio.create_task(transport.post(service.REPORT_URL, headers=provider_headers(), auth=("123", "fixture"), json={}))
    while not entered.is_set():
        await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await transport.close()
    assert exited.is_set() and not transport._active
