"""Instance-scoped report-service profile and bounded verified report transport.

Public headers follow rustpush b3c96c23e1aae78d1229ebaccb12027624f1eaff,
findmy.rs make_searchparty_request. TLS, account/provider binding, request bodies,
report selection and request budgets remain the caller's responsibility.
"""

import base64
import asyncio
import json
import socket
import ssl
import time
import zlib

from ._vendor_findmy.errors import EmptyResponseError, UnauthorizedError
from ._vendor_findmy.util import onboarding_http as bounded
from ._vendor_findmy.util.http import HttpResponse

MAX_RESPONSE_BYTES = 2 * 1024**2
PROVIDER_HEADERS = frozenset({
    "X-Apple-I-Client-Time", "X-Apple-I-TimeZone", "loc", "X-Apple-Locale",
    "X-Apple-I-MD", "X-Apple-I-MD-M", "X-Apple-I-MD-LU",
    "X-Apple-I-MD-RINFO", "X-Mme-Device-Id", "X-Apple-I-SRL-NO",
})
CLIENT_INFO = "<MacBookPro13,2> <macOS;13.1;22C65> <com.apple.icloud.searchpartyuseragent/1.0>"
USER_AGENT = "searchpartyuseragent/1 iMac13,1/13.6.4"
REPORT_URL = "https://gateway.icloud.com/findmyservice/v2/fetch"


class ReportProfileError(ValueError):
    """Fixed failure category; input or response values never enter the message."""


def _refuse():
    raise ReportProfileError("invalid_report_request")


def _header_value(value, maximum=12288):
    return (type(value) is str and 0 < len(value) <= maximum and value.isascii()
            and all(32 <= ord(char) <= 126 for char in value))


def headers(provider_headers, dsid, token):
    """Use one caller-bound provider snapshot and its own account's report grant.

    The exact input field set refuses Cookie, Authorization, or other ambient HTTP
    state. It cannot establish account ownership itself; callers must retain their
    existing same-account check and must never borrow another identity's headers.
    """
    if (type(provider_headers) is not dict or set(provider_headers) != PROVIDER_HEADERS
            or any(not _header_value(value) for value in provider_headers.values())
            or type(dsid) is not str or not 1 <= len(dsid) <= 32
            or not dsid.isascii() or not dsid.isdigit()
            or not _header_value(token, 8192)):
        _refuse()
    return {
        **provider_headers,
        "X-MMe-Client-Info": CLIENT_INFO,
        "x-apple-setup-proxy-request": "true",
        "accept-version": "4",
        "User-Agent": USER_AGENT,
        "x-apple-i-device-type": "1",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "*/*",
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip",
        "Authorization": "Basic " + base64.b64encode((dsid + ":" + token).encode("utf-8")).decode("ascii"),
    }


def decode_response(raw, content_encoding="identity"):
    """Decode one bounded response; reject extra gzip members and damaged framing.

    The transport must also cap its encoded read at MAX_RESPONSE_BYTES + 1.
    No unbounded flush/decompress call or fallback decoder is used here.
    """
    if type(raw) is not bytes or type(content_encoding) is not str:
        raise ReportProfileError("invalid_report_encoding")
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ReportProfileError("report_response_too_large")
    encoding = content_encoding.strip().lower()
    if encoding in {"", "identity"}:
        return raw
    if encoding != "gzip":
        raise ReportProfileError("invalid_report_encoding")
    try:
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
        decoded = decoder.decompress(raw, MAX_RESPONSE_BYTES + 1)
    except zlib.error:
        raise ReportProfileError("invalid_report_encoding") from None
    if len(decoded) > MAX_RESPONSE_BYTES or decoder.unconsumed_tail:
        raise ReportProfileError("report_response_too_large")
    if not decoder.eof or decoder.unused_data:
        raise ReportProfileError("invalid_report_encoding")
    return decoded


def _exchange_report(prepared, body, context, addresses, active):
    """One fixed report POST using the existing bounded TLS/framing primitives."""
    connection = response = None
    try:
        if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
            raise ReportProfileError("report_tls_refused")
        connection = bounded._Connection("gateway.icloud.com", context, addresses, active)
        connection.request("POST", "/findmyservice/v2/fetch", body=body, headers=prepared)
        response = connection.getresponse()
        values = tuple(response.getheaders())
        if len(values) > 100 or sum(len(k) + len(v) + 4 for k, v in values) > bounded.HEADER_LIMIT:
            raise ReportProfileError("report_headers_too_large")
        encodings = [value.strip().lower() for name, value in values if name.lower() == "content-encoding"]
        if len(encodings) > 1:
            raise ReportProfileError("invalid_report_encoding")
        lengths = [value.strip() for name, value in values if name.lower() == "content-length"]
        if (len(lengths) > 1 or lengths and (not lengths[0].isascii() or not lengths[0].isdigit()
                                           or len(lengths[0]) > 10 or int(lengths[0]) > MAX_RESPONSE_BYTES)):
            raise ReportProfileError("report_response_too_large")
        transfer = [value.strip().lower() for name, value in values if name.lower() == "transfer-encoding"]
        if len(transfer) > 1 or transfer and (transfer[0] != "chunked" or lengths):
            raise ReportProfileError("invalid_report_framing")
        raw = bytearray()
        while True:
            if connection.sock is not None:
                connection.sock.settimeout(active.remaining())
            else:
                active.remaining()
            part = response.read(min(65536, MAX_RESPONSE_BYTES + 1 - len(raw)))
            if not part:
                break
            raw.extend(part)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ReportProfileError("report_response_too_large")
        if lengths and len(raw) != int(lengths[0]):
            raise ReportProfileError("invalid_report_framing")
        if response.status in {401, 403} or any(
            name.lower() in {"www-authenticate", "x-apple-i-md-data"} for name, _ in values
        ):
            raise UnauthorizedError("Apple rejected report access")
        content = decode_response(bytes(raw), encodings[0] if encodings else "identity")
        if response.status == 200 and not content.strip():
            # The SDK otherwise retries an empty body several times inside one poll.
            raise EmptyResponseError("Apple returned an empty report response")
        return HttpResponse(response.status, content, dict(values), values)
    except (ReportProfileError, EmptyResponseError, UnauthorizedError):
        raise
    except (TimeoutError, socket.timeout):
        raise TimeoutError("report_request_timeout") from None
    except Exception:
        raise ReportProfileError("report_transport_unavailable") from None
    finally:
        active.stop()
        if response is not None:
            response.close()
        if connection is not None:
            connection.close()


class _ReportTransport(bounded.BoundedHttpSession):
    """Report-only transport; retains the existing socket cancellation lifecycle."""

    async def post(self, url, **options):
        if self._closed or url != REPORT_URL or set(options) != {"headers", "auth", "json"}:
            raise ReportProfileError("invalid_report_request")
        auth = options["auth"]
        if type(auth) is not tuple or len(auth) != 2 or type(options["json"]) is not dict:
            raise ReportProfileError("invalid_report_request")
        prepared = headers(options["headers"], *auth)
        try:
            body = json.dumps(options["json"], allow_nan=False).encode("utf-8")
        except (ValueError, TypeError, OverflowError, RecursionError):
            raise ReportProfileError("invalid_report_request") from None
        if len(body) > MAX_RESPONSE_BYTES:
            raise ReportProfileError("invalid_report_request")
        deadline = time.monotonic() + self.timeout
        try:
            addresses = await asyncio.wait_for(asyncio.get_running_loop().getaddrinfo(
                "gateway.icloud.com", 443, type=socket.SOCK_STREAM), self.timeout)
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            raise TimeoutError("report_request_timeout") from None
        except Exception:
            raise ReportProfileError("report_resolution_unavailable") from None
        if self._closed:
            raise ReportProfileError("report_session_closed")
        active = bounded._Active(deadline)
        active.remaining()
        task = asyncio.create_task(asyncio.to_thread(
            _exchange_report, prepared, body, self._context, addresses, active,
        ))
        self._active[active] = task

        def completed(finished):
            self._active.pop(active, None)
            if not finished.cancelled():
                finished.exception()

        task.add_done_callback(completed)
        try:
            done, _ = await asyncio.wait({task}, timeout=max(0.001, deadline - time.monotonic()))
            if not done:
                raise TimeoutError("report_request_timeout")
            return task.result()
        except (TimeoutError, asyncio.CancelledError):
            active.stop()
            await asyncio.wait({task}, timeout=bounded.SOCKET_TIMEOUT + 1)
            raise
        finally:
            active.stop()


class ReportHttpAdapter:
    """Change only the fixed report endpoint on this owned account instance."""

    def __init__(self, original):
        self.original = original
        self._reports = None
        self._closed = False

    @property
    def timeout(self):
        return self.original.timeout

    async def request(self, method, url, **options):
        if self._closed:
            raise ReportProfileError("report_session_closed")
        if url != REPORT_URL:
            return await self.original.request(method, url, **options)
        if method != "POST":
            raise ReportProfileError("invalid_report_request")
        if self._reports is None:
            self._reports = _ReportTransport()
            # Reuse the account's verified Apple context without changing it.
            context = getattr(self.original, "_context", getattr(self.original, "_ssl", None))
            if isinstance(context, ssl.SSLContext):
                self._reports._context = context
        return await self._reports.post(url, **options)

    async def post(self, url, **options):
        return await self.request("POST", url, **options)

    async def get(self, url, **options):
        return await self.request("GET", url, **options)

    async def close(self):
        self._closed = True
        try:
            if self._reports is not None:
                await self._reports.close()
        finally:
            await self.original.close()


def configure_report_account(account):
    """Install once after restore, keeping the SDK body builder and parser intact."""
    if not isinstance(account._http, ReportHttpAdapter):
        account._http = ReportHttpAdapter(account._http)
    return account
