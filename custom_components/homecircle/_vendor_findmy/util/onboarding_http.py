"""Finite, unpooled Apple HTTPS for explicitly selected onboarding policies.

This transport is instance-scoped. It never changes the legacy HttpSession or a
process-wide TLS/proxy/cookie setting. DNS receives only a public hostname; the
credential-bearing worker connects only to the addresses resolved beforehand.
"""
from __future__ import annotations

import asyncio
import base64
import http.client
import json as json_module
import math
import re
import socket
import ssl
import threading
import time
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from .abc import Closable
from .http import HttpResponse, HttpSession
from .tls import apple_trust_context

HEADER_LIMIT = 128 * 1024
AUTH_BODY_LIMIT = 1024 * 1024
BODY_LIMIT = 8 * 1024 * 1024
SOCKET_TIMEOUT = 15.0
TOTAL_TIMEOUT = 30.0
_TOKEN = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")


class OnboardingTransportError(OSError):
    """A fixed category, never a remote response or credential-bearing URL."""


def _refuse(category: str) -> None:
    raise OnboardingTransportError(category) from None


def _target(url: str) -> tuple[str, str, int]:
    if not isinstance(url, str) or len(url) > 8192 or any(ord(c) <= 32 or ord(c) >= 127 for c in url) or "\\" in url:
        _refuse("url_refused")
    try:
        parsed = urlsplit(url)
        host, port = parsed.hostname, parsed.port
    except ValueError:
        _refuse("url_refused")
    if (parsed.scheme != "https" or not host or parsed.username is not None or parsed.password is not None
            or port not in (None, 443) or parsed.fragment or not re.fullmatch(r"[a-z0-9.-]+", host)
            or ".." in host or host.startswith((".", "-")) or host.endswith((".", "-"))
            or not any(host == root or host.endswith("." + root) for root in ("apple.com", "icloud.com"))):
        _refuse("url_refused")
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    limit = AUTH_BODY_LIMIT if host in {"gsa.apple.com", "gsas.apple.com", "setup.icloud.com"} else BODY_LIMIT
    return host, path, limit


def _prepare(options: Mapping[str, Any]) -> tuple[dict[str, str], bytes | None]:
    if set(options) - {"headers", "auth", "data", "json", "auto_retry", "allow_redirects"}:
        _refuse("options_refused")
    supplied = options.get("headers") or {}
    if not isinstance(supplied, Mapping) or len(supplied) > 100:
        _refuse("headers_refused")
    headers: dict[str, str] = {}
    seen: set[str] = set()
    for name, value in supplied.items():
        if (not isinstance(name, str) or not _TOKEN.fullmatch(name) or not isinstance(value, str)
                or any(ord(c) < 32 or ord(c) == 127 or ord(c) > 255 for c in value)):
            _refuse("headers_refused")
        lower = name.lower()
        if lower in seen or lower in {"cookie", "host", "transfer-encoding", "content-length", "proxy-authorization"}:
            _refuse("headers_refused")
        seen.add(lower)
        if lower not in {"accept-encoding", "connection"}:
            headers[name] = value
    data, json = options.get("data"), options.get("json")
    if json is not None:
        if data is not None:
            _refuse("body_refused")
        try:
            body = json_module.dumps(json, allow_nan=False).encode("utf-8")
        except (ValueError, TypeError, OverflowError, RecursionError):
            _refuse("body_refused")
        if "content-type" not in seen:
            headers["Content-Type"] = "application/json"
    elif data is None:
        body = None
    elif isinstance(data, str):
        body = data.encode("utf-8")
        if "content-type" not in seen:
            headers["Content-Type"] = "text/plain; charset=utf-8"
    elif isinstance(data, (bytes, bytearray)):
        body = bytes(data)
        if "content-type" not in seen:
            headers["Content-Type"] = "application/octet-stream"
    else:
        _refuse("body_refused")
    if body is not None and len(body) > BODY_LIMIT:
        _refuse("body_oversize")
    auth = options.get("auth")
    if auth is not None:
        if (not isinstance(auth, tuple) or len(auth) != 2 or not all(isinstance(x, str) for x in auth)
                or ":" in auth[0] or "authorization" in seen):
            _refuse("auth_refused")
        try:
            token = (auth[0] + ":" + auth[1]).encode("latin-1")
        except UnicodeEncodeError:
            _refuse("auth_refused")
        if len(token) > HEADER_LIMIT:
            _refuse("headers_refused")
        headers["Authorization"] = "Basic " + base64.b64encode(token).decode("ascii")
    headers["Accept-Encoding"] = "identity"
    headers["Connection"] = "close"
    if "accept" not in seen:
        headers["Accept"] = "*/*"
    if sum(len(k) + len(v) + 4 for k, v in headers.items()) > HEADER_LIMIT:
        _refuse("headers_refused")
    return headers, body


class _HeaderReader:
    """Enforce the aggregate budget before http.client parses header lines."""

    def __init__(self, stream: Any) -> None:
        self.stream, self.remaining, self.active = stream, HEADER_LIMIT, True

    def readline(self, limit: int = -1) -> bytes:
        if not self.active:
            return self.stream.readline(limit)
        bound = self.remaining + 1 if limit < 0 else min(limit, self.remaining + 1)
        line = self.stream.readline(bound)
        self.remaining -= len(line)
        if self.remaining < 0:
            _refuse("response_headers_oversize")
        return line

    def __getattr__(self, name: str) -> Any:
        return getattr(self.stream, name)


class _Response(http.client.HTTPResponse):
    def begin(self) -> None:
        reader = _HeaderReader(self.fp)
        self.fp = reader
        try:
            super().begin()
        finally:
            reader.active = False

    def _read_and_discard_trailer(self) -> None:
        # http.client normally discards an unbounded number of trailer lines.
        reader = self.fp
        remaining = reader.remaining
        count = len(self.headers.items())
        while True:
            line = reader.readline(min(65537, remaining + 1))
            remaining -= len(line)
            count += 1
            if remaining < 0 or len(line) > 65536 or count > 101:
                _refuse("response_headers_oversize")
            if line in (b"\r\n", b"\n", b""):
                return


class _Active:
    def __init__(self, deadline: float) -> None:
        self.deadline = deadline
        self.lock = threading.Lock()
        self.stopped = threading.Event()
        self.sock: socket.socket | None = None

    def remaining(self) -> float:
        remaining = self.deadline - time.monotonic()
        if self.stopped.is_set() or remaining <= 0:
            raise TimeoutError("request_timeout")
        return min(SOCKET_TIMEOUT, remaining)

    def stop(self) -> None:
        self.stopped.set()
        with self.lock:
            sock = self.sock
            self.sock = None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass

    def attach(self, sock: socket.socket) -> None:
        with self.lock:
            if self.stopped.is_set():
                sock.close()
                raise TimeoutError("request_timeout")
            self.sock = sock


class _Connection(http.client.HTTPSConnection):
    def __init__(self, host: str, context: ssl.SSLContext, addresses: list[Any], active: _Active) -> None:
        super().__init__(host, port=443, context=context, timeout=active.remaining())
        self.addresses, self.active = addresses, active
        self.response_class = _Response

    def connect(self) -> None:
        # No proxy, tunnel, DNS, redirect or connection-retry path lives in this worker.
        # Use one resolved address, so a failed connection consumes exactly one attempt.
        if not self.addresses:
            _refuse("connection_unavailable")
        # HA hosts can have an IPv6 address without a usable public IPv6 route.
        # Prefer IPv4 when present, still making exactly one connection attempt.
        selected = next((item for item in self.addresses if item[0] == socket.AF_INET), self.addresses[0])
        family, kind, protocol, _, sockaddr = selected
        raw = socket.socket(family, kind, protocol)
        self.active.attach(raw)
        raw.settimeout(self.active.remaining())
        raw.connect(sockaddr)
        # Register the wrapped socket before a blocking TLS handshake can start.
        with self.active.lock:
            if self.active.stopped.is_set():
                raw.close()
                raise TimeoutError("request_timeout")
            secured = self._context.wrap_socket(raw, server_hostname=self.host, do_handshake_on_connect=False)
            self.active.sock = secured
        secured.settimeout(self.active.remaining())
        secured.do_handshake()
        self.sock = secured


def _exchange(method: str, host: str, path: str, headers: dict[str, str], body: bytes | None,
              cap: int, context: ssl.SSLContext, addresses: list[Any], active: _Active) -> HttpResponse:
    connection = None
    response = None
    try:
        if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
            _refuse("tls_refused")
        connection = _Connection(host, context, addresses, active)
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        values = tuple(response.getheaders())
        if len(values) > 100 or sum(len(k) + len(v) + 4 for k, v in values) > HEADER_LIMIT:
            _refuse("response_headers_oversize")
        encodings = [v.strip().lower() for k, v in values if k.lower() == "content-encoding"]
        if len(encodings) > 1 or encodings and encodings[0] not in {"", "identity"}:
            _refuse("response_encoding_refused")
        lengths = [v.strip() for k, v in values if k.lower() == "content-length"]
        if (len(lengths) > 1 or lengths and (not lengths[0].isascii() or not lengths[0].isdigit()
                                           or len(lengths[0]) > 10 or int(lengths[0]) > cap)):
            _refuse("response_body_oversize")
        transfer = [v.strip().lower() for k, v in values if k.lower() == "transfer-encoding"]
        if len(transfer) > 1 or transfer and (transfer[0] != "chunked" or lengths):
            _refuse("response_framing_refused")
        result = bytearray()
        while True:
            if connection.sock is not None:
                connection.sock.settimeout(active.remaining())
            else:
                active.remaining()
            part = response.read(min(65536, cap + 1 - len(result)))
            if not part:
                break
            result.extend(part)
            if len(result) > cap:
                _refuse("response_body_oversize")
        if lengths and len(result) != int(lengths[0]):
            _refuse("response_body_truncated")
        return HttpResponse(response.status, bytes(result), dict(values), values)
    except OnboardingTransportError:
        raise
    except (TimeoutError, socket.timeout):
        raise TimeoutError("request_timeout") from None
    except Exception:
        # No raw exception: DNS/HTTP/TLS exceptions can contain URLs or remote data.
        raise OnboardingTransportError("transport_unavailable") from None
    finally:
        active.stop()
        if response is not None:
            response.close()
        if connection is not None:
            connection.close()


class BoundedHttpSession(Closable):
    """Independent direct HTTPS exchanges for a selected new account policy."""

    def __init__(self, *, timeout: float = TOTAL_TIMEOUT) -> None:
        super().__init__()
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
            _refuse("timeout_refused")
        self._timeout = min(float(timeout), TOTAL_TIMEOUT)
        self._context = apple_trust_context()
        self._closed = False
        self._active: dict[_Active, asyncio.Task[HttpResponse]] = {}

    @property
    def timeout(self) -> float:
        """Finite total request deadline, at most thirty seconds."""
        return self._timeout

    async def request(self, method: str, url: str, **kwargs: Any) -> HttpResponse:
        """Send once, bounded; remote statuses are returned without following them."""
        if self._closed:
            _refuse("session_closed")
        if method not in {"GET", "POST", "PUT", "DELETE"}:
            _refuse("method_refused")
        host, path, cap = _target(url)
        # Authentication material is prepared only after DNS; resolver workers see no secrets.
        deadline = time.monotonic() + self.timeout
        try:
            addresses = await asyncio.wait_for(
                asyncio.get_running_loop().getaddrinfo(host, 443, type=socket.SOCK_STREAM), self.timeout,
            )
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            raise TimeoutError("request_timeout") from None
        except Exception:
            raise OnboardingTransportError("resolution_unavailable") from None
        if self._closed:
            _refuse("session_closed")
        headers, body = _prepare(kwargs)
        if body is not None and len(body) > cap:
            _refuse("body_oversize")
        active = _Active(deadline)
        active.remaining()
        task = asyncio.create_task(asyncio.to_thread(
            _exchange, method, host, path, headers, body, cap, self._context, addresses, active,
        ))
        self._active[active] = task
        def completed(finished: asyncio.Task[HttpResponse]) -> None:
            self._active.pop(active, None)
            # Cancellation can outlive this caller's cleanup wait; always consume
            # a late fixed-category failure, without handing it to HA's logger.
            if not finished.cancelled():
                finished.exception()
        task.add_done_callback(completed)
        try:
            done, _ = await asyncio.wait({task}, timeout=max(0.001, deadline - time.monotonic()))
            if not done:
                raise TimeoutError("request_timeout")
            return task.result()
        except (TimeoutError, asyncio.CancelledError):
            active.stop()
            # Closing the tracked socket interrupts the finite blocking worker.
            # If cancellation interrupts cleanup again, it remains tracked until
            # its done callback consumes the result; close() can still join it.
            await asyncio.wait({task}, timeout=SOCKET_TIMEOUT + 1)
            raise
        finally:
            active.stop()

    async def get(self, url: str, **kwargs: Any) -> HttpResponse:
        """Make one GET request."""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> HttpResponse:
        """Make one POST request."""
        return await self.request("POST", url, **kwargs)

    async def close(self) -> None:
        """Stop live exchanges and join their socket-bound workers."""
        self._closed = True
        live = list(self._active.items())
        for active, _ in live:
            active.stop()
        if live:
            try:
                _, pending = await asyncio.wait({task for _, task in live}, timeout=SOCKET_TIMEOUT + 1)
                if pending:
                    raise OnboardingTransportError("worker_close_timeout")
            except asyncio.CancelledError:
                # Active sockets were already stopped. Their callbacks remain
                # installed, and the next close() can finish the join.
                raise


def http_session_for(account: Any, *, timeout: float | None = None) -> HttpSession | BoundedHttpSession:
    """Choose once per client; unmarked existing accounts keep the legacy transport."""
    selected_timeout = account.timeout if timeout is None else timeout
    if getattr(account, "endpoint_policy", None) is None:
        return HttpSession(timeout=selected_timeout)
    return BoundedHttpSession(timeout=selected_timeout)
