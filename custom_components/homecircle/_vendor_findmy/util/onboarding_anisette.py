"""Opt-in bounded provisioning callbacks, without changing saved native identities.

Native execution remains in its existing executor. Closing this gate stops HTTP
and refuses any subsequent callback; it cannot forcibly terminate a stuck VM.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import plistlib
import time
from types import SimpleNamespace
from typing import Any, Callable

from .onboarding_http import BoundedHttpSession, OnboardingTransportError, _target

_LOOKUP = "https://gsa.apple.com/grandslam/GsService2/lookup"
_NATIVE_TIMEOUT = 75.0
_JOIN_TIMEOUT = 16.0


def _provision_url(value: Any, operation: str) -> str:
    host, path, _ = _target(value)
    if host not in {"gsa.apple.com", "gsd.apple.com"} or path != f"/grandslam/MidService/{operation}MachineProvisioning":
        raise OnboardingTransportError("provisioning_url_refused")
    return value


class ProvisioningGate:
    """At most one verified lookup/start/finish batch per provider instance."""

    def __init__(self) -> None:
        self.loop = asyncio.get_running_loop()
        self.http = BoundedHttpSession(timeout=30)
        self.closed = False
        self.count = 0
        self.urls: tuple[str, str] | None = None
        self.deadline = time.monotonic() + _NATIVE_TIMEOUT
        self._native: set[asyncio.Task[Any]] = set()
        self._serial = asyncio.Lock()
        self._pending: set[concurrent.futures.Future[Any]] = set()

    def install(self, engine: Any) -> None:
        """Called in the native executor, before provision or get_data."""
        if self.closed:
            raise OnboardingTransportError("native_gate_closed")
        session = engine._ani_provider.provisioning_session
        previous = session._http
        session._http = self
        clear = getattr(previous, "clear", None)
        if clear is not None:
            clear()

    async def _send(self, method: str, url: str, headers: dict[str, str], body: Any) -> Any:
        if self.closed or time.monotonic() >= self.deadline:
            raise OnboardingTransportError("native_gate_closed")
        if self.count == 0:
            allowed = method == "GET" and url == _LOOKUP and body is None
        elif self.count in {1, 2} and self.urls is not None:
            allowed = method == "POST" and url == self.urls[self.count - 1]
        else:
            allowed = False
        if not allowed:
            raise OnboardingTransportError("provisioning_budget_refused")
        self.count += 1  # Failure consumes the request; no hidden retry.
        response = await self.http.request(method, url, headers=headers, data=body)
        if response.status_code != 200:
            raise OnboardingTransportError("provisioning_http_refused")
        if self.count == 1:
            try:
                packet = plistlib.loads(response.content)
                bag = packet["urls"]
                self.urls = (_provision_url(bag["midStartProvisioning"], "start"),
                             _provision_url(bag["midFinishProvisioning"], "finish"))
            except Exception:
                raise OnboardingTransportError("provisioning_bag_refused") from None
        return SimpleNamespace(data=response.content, status=response.status_code)

    def request(self, method: str, url: str, *, headers: dict[str, str], body: Any = None,
                timeout: Any = None, **options: Any) -> Any:
        """Pool-compatible synchronous callback; all networking runs on the owner loop."""
        if self.closed or options or time.monotonic() >= self.deadline:
            raise OnboardingTransportError("native_gate_closed")
        # This function is called by the VM executor, never the event-loop thread.
        try:
            if asyncio.get_running_loop() is self.loop:
                raise OnboardingTransportError("native_executor_required")
        except RuntimeError:
            pass
        future = asyncio.run_coroutine_threadsafe(self._send(method, url, headers, body), self.loop)
        self._pending.add(future)
        try:
            return future.result(timeout=max(0.001, min(31.0, self.deadline - time.monotonic())))
        except concurrent.futures.TimeoutError:
            future.cancel()
            raise TimeoutError("native_request_timeout") from None
        except Exception:
            raise OnboardingTransportError("native_request_unavailable") from None
        finally:
            self._pending.discard(future)

    async def run(self, operation: Callable[[], Any]) -> Any:
        """Bound a native call; retain late workers for close and consume failures."""
        async with self._serial:
            if self.closed:
                raise OnboardingTransportError("native_gate_closed")
            # A user may legitimately wait minutes at the 2FA/recovery form.
            # The deadline applies to this operation, not that interaction time.
            self.deadline = time.monotonic() + _NATIVE_TIMEOUT
            task = asyncio.create_task(asyncio.to_thread(operation))
            self._native.add(task)
            def completed(finished: asyncio.Task[Any]) -> None:
                self._native.discard(finished)
                if not finished.cancelled():
                    finished.exception()
            task.add_done_callback(completed)
            try:
                done, _ = await asyncio.wait({task}, timeout=_NATIVE_TIMEOUT)
                if not done:
                    raise TimeoutError("native_operation_timeout")
                return task.result()
            except asyncio.CancelledError:
                # Closing marks the gate closed before any awaited cleanup.
                # A cleanup timeout must not replace the caller's cancellation.
                try:
                    await self.close()
                except Exception:
                    pass
                raise
            except Exception:
                # Never permit this provider to continue callbacks after failure.
                await self.close()
                raise

    async def close(self) -> None:
        """Stop HTTP first; bounded wait does not promise to kill a stuck VM."""
        self.closed = True
        for future in tuple(self._pending):
            future.cancel()
        await self.http.close()
        # Exclude the just-finished current operation; callbacks remove done tasks.
        active = {task for task in self._native if not task.done()}
        if active:
            _, pending = await asyncio.wait(active, timeout=_JOIN_TIMEOUT)
            if pending:
                raise OnboardingTransportError("native_worker_close_timeout")
