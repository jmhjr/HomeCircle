"""Disposable startup transport fence; never include this module in HomeCircle.

The staged manifest makes this QA component a HomeCircle dependency. Installation
is synchronous and precedes HomeCircle component/runtime setup. The providers,
their saved-session restoration and their SDK clients remain the real code; only
their outgoing transports are refused. Counters describe seam invocations, not
network bytes or successful provider authentication.
"""

import os
import sys
from urllib.parse import parse_qsl, urlsplit
from weakref import WeakSet


LIMIT = 1000000
COUNTERS = (
    "life360_sessions_created", "life360_requests_denied",
    "apple_legacy_requests_denied", "apple_bounded_requests_denied",
    "apple_report_requests_denied", "other_external_requests_denied",
    "recovery_before_dispatch_calls", "recovery_command_calls",
    "recovery_transport_attempts_denied", "supervisor_requests_allowed",
    "qa_static_requests_allowed",
)
CHECKS = (
    "installed_before_runtime_setup", "patches_intact",
    "deny_all_external_aiohttp", "deny_all_apple_transports",
    "provider_transport_attempts_measured", "recovery_attempt_seams_measured",
)
_state = None


class StartupBoundaryRefused(OSError):
    """Only fixed messages; inputs and transport errors are never retained."""


def _require(value):
    if not value:
        raise StartupBoundaryRefused("qa_startup_boundary_refused")


def _increment(state, name):
    value = state["counts"][name]
    _require(type(value) is int and 0 <= value < LIMIT)
    state["counts"][name] = value + 1


def _ambient_proxy():
    return any(key.lower() in {"http_proxy", "https_proxy", "all_proxy"} and value
               for key, value in os.environ.items())


def _target(value):
    try:
        raw = str(value)
        if len(raw) > 4096:
            return None
        parsed = urlsplit(raw)
        # Accessing port also rejects malformed ports before any forwarding.
        port = parsed.port
        if parsed.username is not None or parsed.password is not None or parsed.fragment:
            return None
        return parsed, port
    except Exception:
        return None


def _local_kind(hass, method, value):
    target = _target(value)
    if target is None:
        return None
    parsed, port = target
    if parsed.scheme != "http":
        return None
    if parsed.hostname in {"supervisor", "172.30.32.2"} and port in {None, 80}:
        return "supervisor_requests_allowed"
    try:
        server_port = hass.http.server_port
    except AttributeError:
        return None
    if (method != "GET" or type(server_port) is not int
            or not 1 <= server_port <= 65535 or port != server_port
            or parsed.hostname != "127.0.0.1"):
        return None
    if (parsed.path == "/api/image/serve/cccccccccccccccccccccccccccccccc/original"
            and not parsed.query):
        return "qa_static_requests_allowed"
    if parsed.path != "/homecircle_static/homecircle-card.js":
        return None
    # This single public static asset is the fixture's optional loopback check.
    # No general loopback, arbitrary private host, image or auth URL is allowed.
    try:
        query = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        return None
    if (len(query) != 2 or {key for key, _ in query} != {"v", "asset"}
            or dict(query)["v"] != "0.1.0-beta.20"):
        return None
    asset = dict(query)["asset"]
    if len(asset) != 12 or any(char not in "0123456789abcdef" for char in asset):
        return None
    return "qa_static_requests_allowed"


def _recovery_target(value):
    target = _target(value)
    return target is not None and target[0].path.rstrip("/").endswith("/escrowproxy/api/recover")


def _deny(state, counter, value=None):
    _increment(state, counter)
    if value is not None and _recovery_target(value):
        _increment(state, "recovery_transport_attempts_denied")
    raise StartupBoundaryRefused("qa_synthetic_provider_transport_denied")


def snapshot():
    """Return a fixed scalar schema, refusing removed or replaced interceptions."""
    _require(type(_state) is dict and _state.get("installed") is True)
    _require(all(getattr(owner, name, None) is wrapper
                 for owner, name, wrapper in _state["patches"]))
    counts = _state["counts"]
    _require(set(counts) == set(COUNTERS)
             and all(type(value) is int and 0 <= value <= LIMIT for value in counts.values()))
    return {"schema": 1, "boundary_revision": 1,
            **{name: True for name in CHECKS}, **{name: counts[name] for name in COUNTERS}}


def install(hass):
    """Install once, without an await, before any configured HomeCircle runtime.

    Native/product imports deliberately occur only here. Local contracts load
    this module with stubbed modules; they never import native dependencies on
    the Mac. Fresh Linux dependencies must be prepared before the closed boot.
    """
    global _state
    _require(_state is None and sys.platform == "linux")
    _require(not _ambient_proxy())
    _require("homecircle" not in hass.config.components
             and "homecircle" not in hass.data)
    entries = hass.config_entries.async_entries("homecircle")
    _require(all(getattr(entry, "runtime_data", None) is None for entry in entries))
    # Mark an attempted installation before importing. A failed import cannot
    # be silently retried into an uncertain mixture of old and new seams.
    state = _state = {"installed": False, "counts": dict.fromkeys(COUNTERS, 0), "patches": []}

    try:
        from aiohttp import ClientSession
        from custom_components.homecircle import life360_direct
        from custom_components.homecircle._vendor_findmy.util.http import HttpSession
        from custom_components.homecircle._vendor_findmy.util.onboarding_http import BoundedHttpSession
        from custom_components.homecircle.findmy_report_service import _ReportTransport
        from custom_components.homecircle.findmy_recovery_guard import RecoveryAttempt
        from custom_components.homecircle._vendor_findmy.keychain.escrow import AsyncEscrowProxy
    except Exception:
        raise StartupBoundaryRefused("qa_startup_boundary_import_refused") from None

    original_aiohttp = ClientSession._request
    original_life360_session = life360_direct.new_session
    _require(all(callable(value) for value in (
        original_aiohttp, original_life360_session, HttpSession.request,
        BoundedHttpSession.request, _ReportTransport.post,
        RecoveryAttempt.before_dispatch, AsyncEscrowProxy._command)))
    life360_sessions = WeakSet()

    async def life360_session():
        session = await original_life360_session()
        life360_sessions.add(session)
        _increment(state, "life360_sessions_created")
        return session

    async def aiohttp_request(self, method, str_or_url, *args, **kwargs):
        if self in life360_sessions:
            _deny(state, "life360_requests_denied", str_or_url)
        local = _local_kind(hass, method, str_or_url)
        # An explicit proxy is not an allowed local target. The disposable Core
        # environment is separately checked to contain no ambient proxy settings.
        if local is not None and kwargs.get("proxy") is None and not _ambient_proxy():
            _increment(state, local)
            # aiohttp follows redirects inside _request, bypassing a second
            # wrapper invocation. Refuse that escape for every forwarded call.
            kwargs["allow_redirects"] = False
            return await original_aiohttp(self, method, str_or_url, *args, **kwargs)
        _deny(state, "other_external_requests_denied", str_or_url)

    async def apple_legacy_request(self, method, url, **kwargs):
        _deny(state, "apple_legacy_requests_denied", url)

    async def apple_bounded_request(self, method, url, **kwargs):
        _deny(state, "apple_bounded_requests_denied", url)

    async def apple_report_post(self, url, **kwargs):
        _deny(state, "apple_report_requests_denied", url)

    async def before_dispatch(self):
        _increment(state, "recovery_before_dispatch_calls")
        # A fixture must never reserve or submit a recovery proof. A successful
        # automatic-startup observation requires this invocation count to be 0.
        raise StartupBoundaryRefused("qa_synthetic_recovery_reservation_denied")

    async def escrow_command(self, command, *args, **kwargs):
        if command == "recover":
            _increment(state, "recovery_command_calls")
            raise StartupBoundaryRefused("qa_synthetic_recovery_command_denied")
        # All escrow commands are ultimately denied by one of the real Apple
        # transport seams. Preserve non-proof local command preparation.
        return await original_escrow_command(self, command, *args, **kwargs)

    original_escrow_command = AsyncEscrowProxy._command
    patches = (
        (ClientSession, "_request", aiohttp_request),
        (life360_direct, "new_session", life360_session),
        (HttpSession, "request", apple_legacy_request),
        (BoundedHttpSession, "request", apple_bounded_request),
        (_ReportTransport, "post", apple_report_post),
        (RecoveryAttempt, "before_dispatch", before_dispatch),
        (AsyncEscrowProxy, "_command", escrow_command),
    )
    for owner, name, wrapper in patches:
        setattr(owner, name, wrapper)
    state["patches"] = patches
    state["installed"] = True
    return snapshot()
