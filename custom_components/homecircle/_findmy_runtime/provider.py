"""Account-bound Mac identity with transient provisioning and encrypted serialization."""
from __future__ import annotations

import asyncio
import base64
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import plistlib
import re
import secrets
import sys
import time

from .._vendor_findmy.reports.anisette import BaseAnisetteProvider, DeviceIdentity
from .._vendor_findmy.util.onboarding_anisette import _provision_url
from .._vendor_findmy.util.onboarding_http import BoundedHttpSession

PROFILE = DeviceIdentity(
    model="MacBookPro13,2", os_name="macOS", os_version="13.1", os_build="22C65",
    cfnetwork="1404.0.5", darwin="22.2.0",
)
CLIENT_INFO = PROFILE.client_info("com.apple.AuthKit/1 (com.apple.akd/1.0)")
LOOKUP = "https://gsa.apple.com/grandslam/GsService2/lookup"
MAX_IPC = 2 * 1024 * 1024
PROVISION_STAGES = frozenset({
    "runtime", "library", "initialize", "lookup", "start_request", "start_native",
    "finish_request", "finish_native", "validate_state", "complete",
})
PROVISION_FAILURES = frozenset({
    "library_unavailable", "native_unavailable", "http_refused", "response_shape",
    "apple_refused", "state_refused", "cleanup_failed", "cancelled", "timeout", "other",
})


class IdentityUnavailable(RuntimeError):
    """Fixed diagnostics only, never native input or provisioning response text."""


def new_identity():
    return {
        "device_id": "00006000-" + secrets.token_hex(8).upper(),
        "local_user_uuid": secrets.token_hex(16).upper(),
        "host_uuid": secrets.token_hex(16),
        "serial": "C02" + "".join(secrets.choice("0123456789ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(9)),
        "routing": None,
    }


def validate_machine(value):
    """Validate encrypted, versioned machine material before invoking any worker."""
    if type(value) is not dict or set(value) != {"identity", "store"}:
        raise IdentityUnavailable("identity_state_refused")
    identity, stores = value["identity"], value["store"]
    patterns = {
        "device_id": r"00006000-[0-9A-F]{16}",
        "local_user_uuid": r"[0-9A-F]{32}",
        "host_uuid": r"[0-9a-f]{32}",
        "serial": r"C02[0-9A-HJ-NP-Z]{9}",
    }
    if type(identity) is not dict or set(identity) != set(patterns) | {"routing"}:
        raise IdentityUnavailable("identity_state_refused")
    if any(type(identity[k]) is not str or re.fullmatch(pattern, identity[k]) is None for k, pattern in patterns.items()):
        raise IdentityUnavailable("identity_state_refused")
    routing = identity["routing"]
    if type(routing) is not int or not 0 < routing < 2**64:
        raise IdentityUnavailable("identity_state_refused")
    if type(stores) is not dict or not 0 < len(stores) <= 32:
        raise IdentityUnavailable("identity_state_refused")
    total = 0
    for name, encoded in stores.items():
        if type(name) is not str or re.fullmatch(r"[A-Za-z0-9._-]{1,100}", name) is None or name in (".", "..", "adi.pb"):
            raise IdentityUnavailable("identity_state_refused")
        if type(encoded) is not str or len(encoded) > 1400000:
            raise IdentityUnavailable("identity_state_refused")
        try:
            decoded = base64.b64decode(encoded, validate=True)
        except Exception:
            raise IdentityUnavailable("identity_state_refused") from None
        total += len(decoded)
        if len(decoded) > 1024**2 or total > 1024**2:
            raise IdentityUnavailable("identity_state_refused")
    if total == 0:
        raise IdentityUnavailable("identity_state_refused")
    return deepcopy(value)


class Worker:
    """One owned child; bounded lines, wall time, output, cancellation and reaping."""

    def __init__(self):
        self.process = None
        self._spawn = None
        self._close_task = None
        self._closed = False

    async def open(self, library, identity, stores):
        if self._closed or self.process is not None or self._spawn is not None:
            raise IdentityUnavailable("identity_worker_unavailable")
        self._spawn = asyncio.create_task(asyncio.create_subprocess_exec(
            sys.executable, "-B", str(Path(__file__).with_name("worker.py")),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL, limit=MAX_IPC + 1,
        ))
        try:
            self.process = await asyncio.shield(self._spawn)
            self._spawn = None
            if self._closed:
                await self.close()
                raise IdentityUnavailable("identity_worker_unavailable")
            return await self.call({"op": "open", "library": str(library), "host_uuid": identity["host_uuid"], "store": stores})
        except asyncio.CancelledError:
            try:
                await self.close()
            except BaseException:
                pass  # The original cancellation remains authoritative after cleanup.
            raise
        except Exception:
            try:
                await self.close()
            except Exception:
                pass
            raise IdentityUnavailable("identity_worker_unavailable") from None

    async def call(self, packet):
        child = self.process
        if self._closed or child is None or child.returncode is not None:
            raise IdentityUnavailable("identity_worker_unavailable")
        try:
            raw = json.dumps(packet, separators=(",", ":")).encode() + b"\n"
            if len(raw) > MAX_IPC:
                raise ValueError
            async with asyncio.timeout(30):
                child.stdin.write(raw)
                await child.stdin.drain()
                result = await child.stdout.readline()
            if not result or len(result) > MAX_IPC or not result.endswith(b"\n"):
                raise ValueError
            result = json.loads(result)
            if type(result) is not dict:
                raise ValueError
            return result
        except asyncio.CancelledError:
            try:
                await self.close()
            except BaseException:
                pass
            raise
        except Exception:
            try:
                await self.close()
            except Exception:
                pass
            raise IdentityUnavailable("identity_worker_unavailable") from None

    async def _finish_close(self):
        if self._spawn is not None:
            try:
                child = await self._spawn
                if self.process is None:
                    self.process = child
            except Exception:
                pass
            finally:
                self._spawn = None
        child = self.process
        if child is None:
            return
        if child.returncode is None:
            try:
                child.kill()
            except ProcessLookupError:
                pass
        await child.wait()
        # Never discard the only process handle until wait() has settled.
        self.process = None

    async def close(self):
        self._closed = True
        if self._close_task is None or (
            self._close_task.done() and (
                self._close_task.cancelled() or self._close_task.exception() is not None
            )
        ):
            self._close_task = asyncio.create_task(self._finish_close())
        task = self._close_task
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            while not task.done():
                try:
                    await asyncio.shield(task)
                except asyncio.CancelledError:
                    continue
                except Exception:
                    break
            if task.done() and not task.cancelled():
                task.exception()
            raise
        except Exception:
            raise IdentityUnavailable("identity_worker_cleanup_failed") from None


class MacAnisetteProvider(BaseAnisetteProvider):
    """Own a fresh identity for new setup; restore only the same saved identity."""

    _homecircle_mac = True

    def __init__(self, *, libs_path, state=None):
        self._libraries = Path(libs_path) if libs_path is not None else None
        if self._libraries is None:
            raise IdentityUnavailable("identity_cache_required")
        machine = validate_machine(state) if state is not None else None
        self._machine_state = machine
        self._machine_identity = deepcopy(machine["identity"]) if machine else new_identity()
        super().__init__(serial=self._machine_identity["serial"], identity=PROFILE)
        self._is_new_session = machine is None
        self._attempted = False
        self._closed = False
        self._lock = asyncio.Lock()
        self._worker = None
        self._cache = None
        self._cache_window = None
        self._machine_id = None
        self._provision_diagnostics = {
            "schema": 1, "stage": "runtime", "request_count": 0,
            "last_http": None, "last_apple_code": None, "last_apple_hsc": None,
            "failure": None,
        }

    def safe_diagnostics(self):
        """Detached provisioning metadata only; count includes attempted transports."""
        value = self._provision_diagnostics
        if type(value) is not dict:
            value = {}

        def number(name, low, high):
            candidate = value.get(name)
            return candidate if type(candidate) is int and low <= candidate <= high else None

        count = number("request_count", 0, 3)
        return {
            "schema": 1,
            "stage": value.get("stage") if type(value.get("stage")) is str and value["stage"] in PROVISION_STAGES else "runtime",
            "request_count": count if count is not None else 0,
            "last_http": number("last_http", 100, 599),
            "last_apple_code": number("last_apple_code", -1000000, 1000000),
            "last_apple_hsc": number("last_apple_hsc", -1000000, 1000000),
            "failure": value.get("failure") if type(value.get("failure")) is str and value["failure"] in PROVISION_FAILURES else None,
        }

    @property
    def local_user_uuid(self):
        return self._machine_identity["local_user_uuid"]

    @property
    def device_uuid(self):
        return self._machine_identity["device_id"]

    @property
    def host_uuid(self):
        return self._machine_identity["host_uuid"]

    @property
    def otp(self):
        if self._cache is None:
            raise IdentityUnavailable("identity_headers_unavailable")
        return self._cache["otp"]

    @property
    def machine(self):
        if self._cache is None:
            raise IdentityUnavailable("identity_headers_unavailable")
        return self._cache["mid"]

    @property
    def router(self):
        return str(self._machine_identity["routing"])

    @property
    def client(self):
        return CLIENT_INFO

    async def _library(self):
        from .bootstrap import ensure_library
        return await ensure_library(self._libraries)

    async def _get_ani(self):
        async with self._lock:
            await self._initialize()
        return self

    async def _initialize(self):
        if self._closed:
            raise IdentityUnavailable("identity_closed")
        if self._machine_state is not None:
            return
        if self._attempted:
            raise IdentityUnavailable("identity_provisioning_already_attempted")
        self._attempted = True
        diagnostics = self._provision_diagnostics
        worker, transport = Worker(), BoundedHttpSession(timeout=30)
        self._worker = worker
        try:
            async with asyncio.timeout(660):
                diagnostics["stage"] = "library"
                library = await self._library()
                diagnostics["stage"] = "initialize"
                opened = await worker.open(library, self._machine_identity, {})
                if opened != {"provisioned": False}:
                    diagnostics["failure"] = "state_refused"
                    raise IdentityUnavailable("identity_existing_state_refused")
                headers = {
                    "User-Agent": PROFILE.user_agent("akd/1.0"),
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "*/*", "X-Mme-Device-Id": self.device_uuid,
                    "X-MMe-Client-Info": CLIENT_INFO,
                    "X-Apple-I-MD-LU": self.local_user_uuid,
                    "X-Apple-I-SRL-NO": self.serial,
                    "X-Apple-Client-App-Name": "Setup",
                }

                async def request(method, url, body=None):
                    if self._closed:
                        diagnostics["failure"] = "state_refused"
                        raise IdentityUnavailable("identity_closed")
                    if diagnostics["request_count"] >= 3:
                        diagnostics["failure"] = "state_refused"
                        raise IdentityUnavailable("identity_provisioning_refused")
                    diagnostics["request_count"] += 1
                    diagnostics["last_http"] = diagnostics["last_apple_code"] = diagnostics["last_apple_hsc"] = None
                    response = await transport.request(method, url, headers=headers, data=body)
                    status = response.status_code
                    if type(status) is int and 100 <= status <= 599:
                        diagnostics["last_http"] = status
                    if response.status_code != 200:
                        diagnostics["failure"] = "http_refused"
                        raise IdentityUnavailable("identity_provisioning_refused")
                    try:
                        value = response.plist()
                    except Exception:
                        diagnostics["failure"] = "response_shape"
                        raise IdentityUnavailable("identity_provisioning_refused") from None
                    if type(value) is not dict:
                        diagnostics["failure"] = "response_shape"
                        raise IdentityUnavailable("identity_provisioning_refused")
                    return value

                diagnostics["stage"] = "lookup"
                bag = (await request("GET", LOOKUP))["urls"]
                start = _provision_url(bag["midStartProvisioning"], "start")
                finish = _provision_url(bag["midFinishProvisioning"], "finish")

                async def provision(url, payload, stage):
                    diagnostics["stage"] = stage
                    headers["X-Apple-I-Client-Time"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    value = (await request("POST", url, plistlib.dumps({"Header": {}, "Request": payload})))["Response"]
                    status = value.get("Status", {})
                    if type(status) is dict:
                        for source, target in (("ec", "last_apple_code"), ("hsc", "last_apple_hsc")):
                            code = status.get(source)
                            if type(code) is int and -1000000 <= code <= 1000000:
                                diagnostics[target] = code
                    if type(status) is not dict or status.get("ec", 0) != 0 or status.get("hsc", 200) != 200:
                        diagnostics["failure"] = "apple_refused" if type(status) is dict else "response_shape"
                        raise IdentityUnavailable("identity_provisioning_refused")
                    return value

                first = await provision(start, {}, "start_request")
                diagnostics["stage"] = "start_native"
                result = await worker.call({"op": "start", "spim": first["spim"]})
                last = await provision(finish, {"cpim": result["cpim"]}, "finish_request")
                routing = last["X-Apple-I-MD-RINFO"]
                if type(routing) is str and routing.isdecimal():
                    routing = int(routing)
                if type(routing) is not int or not 0 < routing < 2**64:
                    diagnostics["failure"] = "response_shape"
                    raise IdentityUnavailable("identity_provisioning_refused")
                diagnostics["stage"] = "finish_native"
                result = await worker.call({"op": "finish", "ptm": last["ptm"], "tk": last["tk"], "routing": routing})
                if self._closed:
                    diagnostics["failure"] = "state_refused"
                    raise IdentityUnavailable("identity_closed")
                diagnostics["stage"] = "validate_state"
                self._machine_identity["routing"] = routing
                self._machine_state = validate_machine({"identity": self._machine_identity, "store": result["store"]})
        except asyncio.CancelledError:
            if diagnostics["failure"] is None:
                diagnostics["failure"] = "cancelled"
            raise
        except Exception as error:
            if diagnostics["failure"] is None:
                if isinstance(error, TimeoutError):
                    failure = "timeout"
                elif isinstance(error, (KeyError, TypeError)):
                    failure = "response_shape"
                elif diagnostics["stage"] == "library":
                    failure = "library_unavailable"
                elif diagnostics["stage"] in {"initialize", "start_native", "finish_native"}:
                    failure = "native_unavailable"
                elif diagnostics["stage"] == "validate_state":
                    failure = "state_refused"
                elif diagnostics["stage"] in {"lookup", "start_request", "finish_request"}:
                    failure = "response_shape"
                else:
                    failure = "other"
                diagnostics["failure"] = failure
            raise IdentityUnavailable("identity_provisioning_unavailable") from None
        finally:
            unwinding = sys.exc_info()[0] is not None

            async def cleanup():
                try:
                    await transport.close()
                finally:
                    await worker.close()
                    self._worker = None

            closing = asyncio.create_task(cleanup())
            try:
                await asyncio.shield(closing)
            except asyncio.CancelledError:
                if diagnostics["failure"] is None:
                    diagnostics["failure"] = "cancelled"
                while not closing.done():
                    try:
                        await asyncio.shield(closing)
                    except asyncio.CancelledError:
                        continue
                    except Exception:
                        break
                if closing.done() and not closing.cancelled():
                    closing.exception()
                raise
            except Exception:
                if not unwinding:
                    diagnostics["failure"] = "cleanup_failed"
                    raise IdentityUnavailable("identity_worker_cleanup_failed") from None
        diagnostics["stage"] = "complete"

    async def get_headers(self, user_id, device_id, serial=None, with_client_info=False):
        async with self._lock:
            if user_id != self.local_user_uuid or device_id.upper() != self.device_uuid:
                raise IdentityUnavailable("identity_account_mismatch")
            await self._initialize()
            window = int(time.time()) // 30
            if self._cache is None or self._cache_window != window:
                worker = Worker()
                self._worker = worker
                try:
                    library = await self._library()
                    opened = await worker.open(library, self._machine_identity, self._machine_state["store"])
                    if opened != {"provisioned": True}:
                        raise IdentityUnavailable("identity_state_refused")
                    output = await worker.call({"op": "otp", "routing": self._machine_identity["routing"]})
                    if set(output) != {"otp", "mid"}:
                        raise IdentityUnavailable("identity_output_refused")
                    for value in output.values():
                        if type(value) is not str or not 0 < len(value) <= 2048 or not base64.b64decode(value, validate=True):
                            raise IdentityUnavailable("identity_output_refused")
                    if self._machine_id is not None and self._machine_id != output["mid"]:
                        raise IdentityUnavailable("identity_binding_changed")
                    if self._closed:
                        raise IdentityUnavailable("identity_closed")
                    self._machine_id = output["mid"]
                    self._cache, self._cache_window = output, window
                except asyncio.CancelledError:
                    raise
                except Exception:
                    raise IdentityUnavailable("identity_headers_unavailable") from None
                finally:
                    unwinding = sys.exc_info()[0] is not None
                    try:
                        await worker.close()
                    except Exception:
                        if not unwinding:
                            raise IdentityUnavailable("identity_worker_cleanup_failed") from None
                    else:
                        self._worker = None
            # Matching the proven wire profile includes UTC and a base64 local UID.
            headers = {
                "X-Apple-I-Client-Time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "X-Apple-I-TimeZone": "UTC", "loc": "en_US", "X-Apple-Locale": "en_US",
                "X-Apple-I-MD": self.otp, "X-Apple-I-MD-M": self.machine,
                "X-Apple-I-MD-LU": base64.b64encode(self.local_user_uuid.encode()).decode(),
                "X-Apple-I-MD-RINFO": self.router,
                "X-Mme-Device-Id": self.device_uuid, "X-Apple-I-SRL-NO": self.serial,
            }
            if with_client_info:
                headers["X-Mme-Client-Info"] = CLIENT_INFO
            return headers

    def to_json(self, path=None):
        if path is not None or self._machine_state is None or self._closed:
            raise IdentityUnavailable("identity_serialization_refused")
        # The caller embeds this in its already encrypted selected-item vault.
        return {"type": "aniMac", "version": 1, "machine": deepcopy(self._machine_state)}

    @classmethod
    def from_json(cls, mapping, *, libs_path):
        if type(mapping) is not dict or set(mapping) != {"type", "version", "machine"} or mapping["type"] != "aniMac" or type(mapping["version"]) is not int or mapping["version"] != 1:
            raise IdentityUnavailable("identity_state_refused")
        return cls(libs_path=libs_path, state=mapping["machine"])

    async def close(self):
        self._closed = True
        if self._worker is not None:
            await self._worker.close()
            self._worker = None
        async with self._lock:
            self._cache = self._machine_id = self._cache_window = None
            self._machine_state = None
            self._machine_identity.clear()
