"""Early, external QA transport interception without a product manifest change.

HA-managed requirement installation stays ordinary. Its new ``python -m uv``
process does not import custom_components and does not inherit Python hooks.
The running Core interpreter refuses provider HTTP before DNS. A socket audit
hook additionally refuses nonlocal direct Python socket traffic. These are
synthetic trial controls, not a product security boundary or a native sandbox.
"""
import importlib.abc
import importlib.machinery
import os
import sys
from urllib.parse import parse_qsl, urlsplit
from weakref import WeakSet

LIMIT = 1_000_000
COUNTERS = ("life360_sessions_created", "life360_requests_denied",
    "apple_legacy_requests_denied", "apple_bounded_requests_denied",
    "apple_report_requests_denied", "other_external_requests_denied",
    "recovery_before_dispatch_calls", "recovery_command_calls",
    "recovery_transport_attempts_denied", "supervisor_requests_allowed",
    "qa_static_requests_allowed", "socket_external_attempts_denied", "ordinary_uv_installs_observed")
TARGETS = {
    "custom_components.homecircle.life360_direct": "life360",
    "custom_components.homecircle._vendor_findmy.util.http": "legacy",
    "custom_components.homecircle._vendor_findmy.util.onboarding_http": "bounded",
    "custom_components.homecircle.findmy_report_service": "report",
    "custom_components.homecircle.findmy_recovery_guard": "guard",
    "custom_components.homecircle._vendor_findmy.keychain.escrow": "escrow",
}
_state = None


class StartupBoundaryRefused(OSError):
    """Fixed diagnostics only; no URL, secret or exception text is retained."""


def require(ok):
    if not ok:
        raise StartupBoundaryRefused("qa_ordinary_startup_boundary_refused")


def increment(name):
    value = _state["counts"][name]
    require(type(value) is int and 0 <= value < LIMIT)
    _state["counts"][name] = value + 1


def ambient_proxy():
    return any(key.lower() in {"http_proxy", "https_proxy", "all_proxy"}
               and value for key, value in os.environ.items())


def target(value):
    try:
        raw = str(value)
        require(len(raw) <= 4096)
        parsed = urlsplit(raw)
        port = parsed.port
        if parsed.username is not None or parsed.password is not None or parsed.fragment:
            return None
        return parsed, port
    except Exception:
        return None


def local_kind(method, value):
    result = target(value)
    if result is None:
        return None
    parsed, port = result
    if parsed.scheme != "http":
        return None
    if parsed.hostname in {"supervisor", "172.30.32.2"} and port in {None, 80}:
        return "supervisor_requests_allowed"
    if method != "GET" or parsed.hostname != "127.0.0.1" or port != 8123:
        return None
    if (parsed.path == "/api/image/serve/cccccccccccccccccccccccccccccccc/original"
            and not parsed.query):
        return "qa_static_requests_allowed"
    if parsed.path != "/homecircle_static/homecircle-card.js":
        return None
    try:
        query = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        return None
    if (len(query) != 2 or {key for key, _ in query} != {"v", "asset"}
            or dict(query)["v"] != "0.1.0-beta.20"):
        return None
    asset = dict(query)["asset"]
    return ("qa_static_requests_allowed" if len(asset) == 12
            and all(char in "0123456789abcdef" for char in asset) else None)


def deny(counter, value=None):
    increment(counter)
    parsed = target(value) if value is not None else None
    if parsed is not None and parsed[0].path.rstrip("/").endswith("/escrowproxy/api/recover"):
        increment("recovery_transport_attempts_denied")
    raise StartupBoundaryRefused("qa_synthetic_provider_transport_denied")


def patch(owner, name, replacement):
    require(callable(getattr(owner, name, None)))
    setattr(owner, name, replacement)
    _state["patches"].append((owner, name, replacement))


def loaded(module, kind):
    require(kind not in _state["loaded"])
    if kind == "life360":
        original = module.new_session
        async def new_session():
            session = await original()
            _state["life360_sessions"].add(session)
            increment("life360_sessions_created")
            return session
        patch(module, "new_session", new_session)
    elif kind in {"legacy", "bounded"}:
        owner = module.HttpSession if kind == "legacy" else module.BoundedHttpSession
        async def request(self, method, url, **kwargs):
            deny("apple_legacy_requests_denied" if kind == "legacy"
                 else "apple_bounded_requests_denied", url)
        patch(owner, "request", request)
    elif kind == "report":
        async def post(self, url, **kwargs):
            deny("apple_report_requests_denied", url)
        patch(module._ReportTransport, "post", post)
    elif kind == "guard":
        original = module.RecoveryAttempt.before_dispatch
        async def before_dispatch(self):
            increment("recovery_before_dispatch_calls")
            # Observe the real guard. Never replace rollback refusal with QA.
            return await original(self)
        patch(module.RecoveryAttempt, "before_dispatch", before_dispatch)
    else:
        require(kind == "escrow")
        original = module.AsyncEscrowProxy._command
        async def command(self, command, *args, **kwargs):
            if command == "recover":
                increment("recovery_command_calls")
                raise StartupBoundaryRefused("qa_synthetic_recovery_command_denied")
            return await original(self, command, *args, **kwargs)
        patch(module.AsyncEscrowProxy, "_command", command)
    _state["loaded"].add(kind)


class BoundaryLoader(importlib.abc.Loader):
    def __init__(self, wrapped, kind):
        self.wrapped, self.kind = wrapped, kind

    def create_module(self, spec):
        return self.wrapped.create_module(spec)

    def exec_module(self, module):
        self.wrapped.exec_module(module)
        loaded(module, self.kind)


class BoundaryFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname not in TARGETS:
            return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        require(spec is not None and spec.loader is not None)
        spec.loader = BoundaryLoader(spec.loader, TARGETS[fullname])
        return spec


def audit(event, args):
    if event == "subprocess.Popen":
        # Observe the ordinary HA installer without changing its argv or env.
        argv = args[1]
        if (isinstance(argv, (list, tuple)) and len(argv) >= 7
                and list(argv[:5]) == [sys.executable, "-m", "uv", "pip", "install"]
                and argv[5] == "--quiet" and argv[6] in {
                    "life360==7.2.0", "protobuf>=6.32.0,<8.0.0", "anisette==1.2.4",
                    "unicorn==2.1.4", "srp==1.0.22", "beautifulsoup4==4.13.3"}):
            increment("ordinary_uv_installs_observed")
        return
    if event == "socket.getaddrinfo":
        allowed = args[0] in {"supervisor", "172.30.32.2", "127.0.0.1"}
    elif event in {"socket.connect", "socket.sendto"}:
        address = args[1]
        allowed = (isinstance(address, tuple) and len(address) >= 2
            and ((address[0] == "127.0.0.1" and address[1] == 8123)
                 or (address[0] == "172.30.32.2" and address[1] == 80)
                 or (address[0] == "172.30.32.3" and address[1] == 53)))
        allowed = allowed or address == "/run/dbus/system_bus_socket"
    else:
        return
    if not allowed:
        deny("socket_external_attempts_denied")


def snapshot():
    require(type(_state) is dict and _state.get("installed") is True)
    require(_state["finder"] in sys.meta_path
        and all(getattr(owner, name, None) is wrapper for owner, name, wrapper in _state["patches"]))
    counts = _state["counts"]
    require(set(counts) == set(COUNTERS)
        and all(type(value) is int and 0 <= value <= LIMIT for value in counts.values()))
    return {"schema": 2, "boundary_revision": 2,
        "installed_before_product_import": True, "patches_intact": True,
        "deny_all_external_aiohttp": True, "python_socket_audit_installed": True,
        "product_manifest_unchanged": True, "normal_requirement_subprocesses_unmodified": True,
        "loaded_target_kinds": sorted(_state["loaded"]), **counts}


def install():
    global _state
    require(_state is None and sys.platform == "linux" and not ambient_proxy())
    require(not any(name == "custom_components.homecircle"
        or name.startswith("custom_components.homecircle.") for name in sys.modules))
    from aiohttp import ClientSession
    original = ClientSession._request
    _state = {"installed": False, "counts": dict.fromkeys(COUNTERS, 0),
        "patches": [], "loaded": set(), "life360_sessions": WeakSet(), "finder": BoundaryFinder()}
    async def request(self, method, str_or_url, *args, **kwargs):
        if self in _state["life360_sessions"]:
            deny("life360_requests_denied", str_or_url)
        local = local_kind(method, str_or_url)
        if local is not None and kwargs.get("proxy") is None and not ambient_proxy():
            increment(local)
            kwargs["allow_redirects"] = False
            return await original(self, method, str_or_url, *args, **kwargs)
        deny("other_external_requests_denied", str_or_url)
    patch(ClientSession, "_request", request)
    sys.meta_path.insert(0, _state["finder"])
    sys.addaudithook(audit)
    _state["installed"] = True
    return snapshot()
