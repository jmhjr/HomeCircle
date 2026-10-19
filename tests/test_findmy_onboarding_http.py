"""New-policy HTTPS is bounded and instance-scoped, using synthetic transports only."""
from __future__ import annotations

import asyncio
import io
import socket
import ssl
import threading
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.homecircle._vendor_findmy.util import onboarding_http as http


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("test attempted a real socket")
    monkeypatch.setattr(socket, "socket", forbidden)


@pytest.fixture
async def dns(monkeypatch):
    resolver = AsyncMock(return_value=[(2, 1, 6, "", ("192.0.2.1", 443))])
    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", resolver)
    return resolver


class Response:
    def __init__(self, body=b"ok", headers=(), status=200):
        self.body = io.BytesIO(body)
        self.headers, self.status, self.closed = headers, status, False
    def getheaders(self):
        return self.headers
    def read(self, size):
        return self.body.read(size)
    def close(self):
        self.closed = True


class Connection:
    response = None
    requests = None
    def __init__(self, host, context, addresses, active):
        self.sock = None
        self.active = active
    def request(self, method, path, *, body, headers):
        self.requests.append((method, path, body, headers))
    def getresponse(self):
        return self.response
    def close(self):
        pass


def fake_connection(monkeypatch, response):
    cls = type("FakeConnection", (Connection,), {"response": response, "requests": []})
    monkeypatch.setattr(http, "_Connection", cls)
    return cls


@pytest.mark.parametrize("url", [
    "http://gsa.apple.com/", "https://gsa.apple.com.evil.invalid/", "https://apple.com@evil.invalid/",
    "https://u:p@gsa.apple.com/", "https://gsa.apple.com:444/", "https://gsa.apple.com/#x",
    "https://gsa.apple.com/\n", "https://gsa.app\tle.com/", " https://gsa.apple.com/",
    "https://gsa.apple.com\\@evil.invalid/", "https://gsa.apple.com./", "https://icloud.com.evil/",
])
def test_unsafe_url_never_reaches_transport(url):
    with pytest.raises(http.OnboardingTransportError, match="^url_refused$"):
        http._target(url)


def test_apple_report_hosts_and_caps():
    assert http._target("https://gateway.icloud.com/acsnservice/fetch")[2] == http.BODY_LIMIT
    assert http._target("https://p123-ckdatabase.icloud.com/database/1?ckEnv=production")[1].endswith("?ckEnv=production")
    assert http._target("https://gsa.apple.com/grandslam/GsService2")[2] == http.AUTH_BODY_LIMIT


def test_body_auth_and_forced_unpooled_headers():
    headers, body = http._prepare({"headers": {"accept-encoding": "gzip", "connection": "keep-alive"},
                                   "auth": ("synthetic-user", "synthetic-token"), "json": {"a": 1}})
    assert body == b'{"a": 1}'
    assert headers["Authorization"].startswith("Basic ")
    assert headers["Accept-Encoding"] == "identity" and headers["Connection"] == "close"
    assert "accept-encoding" not in headers and "connection" not in headers


@pytest.mark.parametrize("body,content_type", [
    (b"plist", "application/octet-stream"),
    ("text", "text/plain; charset=utf-8"),
])
def test_sdk_implicit_payload_headers_and_explicit_values(body, content_type):
    headers, _ = http._prepare({"data": body})
    assert headers["Content-Type"] == content_type
    assert headers["Accept"] == "*/*"
    explicit, _ = http._prepare({"data": body, "headers": {
        "content-type": "application/x-plist", "accept": "application/x-plist"}})
    assert explicit["content-type"] == explicit["accept"] == "application/x-plist"
    assert "Content-Type" not in explicit and "Accept" not in explicit


def test_connection_prefers_ipv4_without_second_attempt(monkeypatch):
    calls = []
    raw = SimpleNamespace(
        settimeout=lambda value: None,
        connect=lambda address: calls.append(address),
        close=lambda: None,
    )
    secured = SimpleNamespace(settimeout=lambda value: None, do_handshake=lambda: None)
    monkeypatch.setattr(socket, "socket", lambda *args: raw)
    context = ssl.create_default_context()
    connection = http._Connection("gsa.apple.com", context, [
        (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2001:db8::1", 443, 0, 0)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.1", 443)),
    ], http._Active(time.monotonic() + 1))
    connection._context = SimpleNamespace(wrap_socket=lambda *args, **kwargs: secured)
    connection.connect()
    assert calls == [("192.0.2.1", 443)]


@pytest.mark.parametrize("options", [
    {"headers": {"Cookie": "secret"}}, {"headers": {"X": "secret\r\nInjected: true"}},
    {"headers": {"Host": "elsewhere"}}, {"headers": {"Content-Length": "0"}},
    {"headers": {"Authorization": "secret"}, "auth": ("a", "b")},
    {"auth": ("colon:user", "secret")}, {"data": object()}, {"data": b"a", "json": {}},
    {"headers": {"X": "a", "x": "b"}}, {"proxy": "https://example.invalid"},
])
def test_injection_and_ambiguous_bodies_refused(options):
    with pytest.raises(http.OnboardingTransportError) as caught:
        http._prepare(options)
    assert "secret" not in str(caught.value)


async def test_redirect_is_returned_once_cookies_not_retained(monkeypatch, dns):
    cls = fake_connection(monkeypatch, Response(status=302, headers=(("Location", "https://evil.invalid/"),
                                                                  ("Set-Cookie", "synthetic"))))
    session = http.BoundedHttpSession()
    first = await session.post("https://gsa.apple.com/grandslam/GsService2", data=b"t", auto_retry=True)
    second = await session.get("https://gsa.apple.com/")
    assert first.status_code == second.status_code == 302
    assert len(cls.requests) == 2 and all("Cookie" not in call[3] for call in cls.requests)
    await session.close()


@pytest.mark.parametrize("headers,body,category", [
    ((("Content-Encoding", "gzip"),), b"compressed", "response_encoding_refused"),
    ((("Content-Length", str(http.AUTH_BODY_LIMIT + 1)),), b"", "response_body_oversize"),
    ((("Content-Length", "1"), ("Content-Length", "1")), b"a", "response_body_oversize"),
    ((("Transfer-Encoding", "gzip"),), b"", "response_framing_refused"),
    ((("Transfer-Encoding", "chunked"), ("Content-Length", "0")), b"", "response_framing_refused"),
    ((), b"x" * (http.AUTH_BODY_LIMIT + 1), "response_body_oversize"),
], ids=["gzip", "length", "duplicate", "transfer", "conflicting", "stream-overflow"])
async def test_response_limits(monkeypatch, dns, headers, body, category):
    fake_connection(monkeypatch, Response(body, headers))
    session = http.BoundedHttpSession()
    with pytest.raises(http.OnboardingTransportError, match="^" + category + "$"):
        await session.post("https://gsa.apple.com/")
    await session.close()


def test_aggregate_headers_refused_before_parser_completes():
    payload = b"HTTP/1.1 200 OK\r\n" + (b"X: " + b"x" * 16000 + b"\r\n") * 9 + b"\r\n"
    fake_socket = SimpleNamespace(makefile=lambda *args: io.BytesIO(payload))
    response = http._Response(fake_socket)
    with pytest.raises(http.OnboardingTransportError, match="^response_headers_oversize$"):
        response.begin()
    response.close()


async def test_cancellation_stops_and_joins_sensitive_worker(monkeypatch, dns):
    entered, exited = threading.Event(), threading.Event()
    def exchange(*args):
        active = args[-1]
        entered.set()
        assert active.stopped.wait(1)
        exited.set()
        raise TimeoutError("synthetic-private-detail")
    monkeypatch.setattr(http, "_exchange", exchange)
    session = http.BoundedHttpSession()
    task = asyncio.create_task(session.post("https://gsa.apple.com/", data=b"synthetic-secret"))
    while not entered.is_set():
        await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert exited.is_set() and not session._active
    await session.close()


async def test_timeout_stops_worker_and_sanitizes_exception(monkeypatch, dns):
    stopped = threading.Event()
    def exchange(*args):
        active = args[-1]
        assert active.stopped.wait(1)
        stopped.set()
        raise TimeoutError("synthetic-private-detail")
    monkeypatch.setattr(http, "_exchange", exchange)
    session = http.BoundedHttpSession(timeout=0.02)
    with pytest.raises(TimeoutError) as caught:
        await session.get("https://gsa.apple.com/")
    assert stopped.is_set() and "private" not in str(caught.value)
    await session.close()


async def test_close_interrupts_active_request(monkeypatch, dns):
    entered = threading.Event()
    def exchange(*args):
        entered.set()
        assert args[-1].stopped.wait(1)
        raise TimeoutError("request_timeout")
    monkeypatch.setattr(http, "_exchange", exchange)
    session = http.BoundedHttpSession()
    task = asyncio.create_task(session.get("https://gsa.apple.com/"))
    while not entered.is_set():
        await asyncio.sleep(0)
    await session.close()
    with pytest.raises(TimeoutError):
        await task
    with pytest.raises(http.OnboardingTransportError, match="^session_closed$"):
        await session.get("https://gsa.apple.com/")


async def test_cancelled_dns_cannot_start_exchange(monkeypatch):
    entered, release = asyncio.Event(), asyncio.Event()
    async def resolve(*args, **kwargs):
        entered.set()
        await release.wait()
        return []
    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", resolve)
    monkeypatch.setattr(http, "_exchange", lambda *args: pytest.fail("exchange after canceled DNS"))
    session = http.BoundedHttpSession()
    task = asyncio.create_task(session.get("https://gsa.apple.com/"))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    release.set()
    await session.close()


async def test_factory_preserves_legacy_and_new_policy():
    legacy = http.http_session_for(SimpleNamespace(timeout=5, endpoint_policy=None))
    selected = http.http_session_for(SimpleNamespace(timeout=50, endpoint_policy=object()))
    assert type(legacy) is http.HttpSession
    assert type(selected) is http.BoundedHttpSession and selected.timeout == 30
    await legacy.close()
    await selected.close()


def test_live_socket_shutdown_precedes_close():
    calls = []
    sock = SimpleNamespace(shutdown=lambda how: calls.append("shutdown"), close=lambda: calls.append("close"))
    active = http._Active(time.monotonic() + 1)
    active.attach(sock)
    active.stop()
    assert calls == ["shutdown", "close"]


async def test_raw_transport_exception_never_escapes(monkeypatch, dns):
    cls = fake_connection(monkeypatch, Response())
    def fail(*args, **kwargs):
        raise ssl.SSLError("synthetic-password-and-response")
    monkeypatch.setattr(cls, "request", fail)
    session = http.BoundedHttpSession()
    with pytest.raises(http.OnboardingTransportError, match="^transport_unavailable$"):
        await session.get("https://gsa.apple.com/")
    await session.close()


async def test_declared_body_truncation_refused(monkeypatch, dns):
    fake_connection(monkeypatch, Response(b"short", (("Content-Length", "20"),)))
    session = http.BoundedHttpSession()
    with pytest.raises(http.OnboardingTransportError, match="^response_body_truncated$"):
        await session.get("https://gsa.apple.com/")
    await session.close()


def test_chunked_trailers_share_header_budget():
    payload = (b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n"
               + (b"X: " + b"x" * 16000 + b"\r\n") * 9 + b"\r\n")
    fake_socket = SimpleNamespace(makefile=lambda *args: io.BytesIO(payload))
    response = http._Response(fake_socket)
    response.begin()
    with pytest.raises(http.OnboardingTransportError, match="^response_headers_oversize$"):
        response.read()
    response.close()


async def test_repeated_cancellation_retains_late_worker_until_close(monkeypatch, dns):
    entered, release, exited = threading.Event(), threading.Event(), threading.Event()
    def exchange(*args):
        active = args[-1]
        entered.set()
        assert active.stopped.wait(1)
        assert release.wait(1)
        exited.set()
        raise http.OnboardingTransportError("transport_unavailable")
    monkeypatch.setattr(http, "_exchange", exchange)
    session = http.BoundedHttpSession()
    task = asyncio.create_task(session.get("https://gsa.apple.com/"))
    while not entered.is_set():
        await asyncio.sleep(0)
    task.cancel()
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert session._active
    release.set()
    await session.close()
    await asyncio.sleep(0)
    assert exited.is_set() and not session._active


async def test_auth_request_body_is_capped_before_exchange(monkeypatch, dns):
    monkeypatch.setattr(http, "_exchange", lambda *args: pytest.fail("oversize body sent"))
    session = http.BoundedHttpSession()
    with pytest.raises(http.OnboardingTransportError, match="^body_oversize$"):
        await session.post("https://gsa.apple.com/", data=b"x" * (http.AUTH_BODY_LIMIT + 1))
    await session.close()
