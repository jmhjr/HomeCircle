"""Durable local stop controls, independent of editable account settings."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
import logging

from homeassistant.helpers.storage import Store

from .const import DOMAIN

PROVIDERS = ("life360", "findmy")
REASONS = ("manual", "access_denied", "storage_error")
_DATA_KEY = f"{DOMAIN}_provider_controls"
_LOGGER = logging.getLogger(__name__)
_PAUSE_CANCEL = object()


class ProviderPaused(Exception):
    """A local stop control refused an operation before it could continue."""


class ProviderControlsError(Exception):
    """The durable stop controls could not be safely loaded or saved."""


def _initial_state():
    return {
        "revision": 0,
        "providers": {
            provider: {"paused": False, "reason": None, "accounts": {}}
            for provider in PROVIDERS
        },
    }


def _validate(state):
    if (
        not isinstance(state, dict)
        or set(state) != {"revision", "providers"}
        or type(state["revision"]) is not int
        or not 0 <= state["revision"] < 2**63
        or not isinstance(state["providers"], dict)
        or set(state["providers"]) != set(PROVIDERS)
    ):
        raise ProviderControlsError("provider_controls_storage_failed")
    for provider, record in state["providers"].items():
        if (
            not isinstance(record, dict)
            or set(record) != {"paused", "reason", "accounts"}
            or type(record["paused"]) is not bool
            or record["reason"] not in (None, *REASONS)
            or (record["reason"] is not None) != record["paused"]
            or not isinstance(record["accounts"], dict)
            or len(record["accounts"]) > 256
            or (provider == "life360" and record["accounts"])
            or any(
                not isinstance(account_id, str)
                or not 1 <= len(account_id) <= 256
                or reason not in REASONS
                for account_id, reason in record["accounts"].items()
            )
        ):
            raise ProviderControlsError("provider_controls_storage_failed")
    return deepcopy(state)


async def _owned_result(awaitable):
    """Observe an owned operation fully, including repeated caller cancellation."""
    task = asyncio.create_task(awaitable)
    drained = asyncio.gather(task, return_exceptions=True)
    cancelled = None
    while not drained.done():
        try:
            await asyncio.shield(drained)
        except asyncio.CancelledError as error:
            if cancelled is None or error.args != (_PAUSE_CANCEL,):
                cancelled = error
    return drained.result()[0], cancelled


class ProviderControls:
    """Shared entry-local state; a stale options draft cannot change it."""

    def __init__(self, hass, entry_id, store=None):
        self.hass = hass
        self.entry_id = entry_id
        self.store = store or Store(hass, 1, f"{DOMAIN}.provider_controls.{entry_id}")
        self._data = _initial_state()
        self._loaded = False
        self._failed = False
        self._lock = asyncio.Lock()
        self._pending = {}
        self._epochs = dict.fromkeys(PROVIDERS, 0)
        self._operations = {}
        self._control_cancelled = set()
        self._reload_task = None
        self._stop_task = None

    def _storage_failed(self):
        self._failed = True
        for record in self._data["providers"].values():
            record.update(paused=True, reason="storage_error")

    async def async_load(self):
        async with self._lock:
            if self._loaded:
                return
            try:
                saved = await self.store.async_load()
                if saved is None:
                    # Establish writable controls before any provider startup.
                    await self.store.async_save(self._data)
                else:
                    self._data = _validate(saved)
            except Exception:
                self._storage_failed()
            self._loaded = True

    def paused(self, provider_id, account_id=None):
        if provider_id not in PROVIDERS:
            raise ValueError("Unknown tracker provider")
        record = self._data["providers"][provider_id]
        return bool(
            not self._loaded
            or self._failed
            or record["paused"]
            or (provider_id, None) in self._pending
            or (
                account_id is not None
                and (
                    account_id in record["accounts"]
                    or (provider_id, account_id) in self._pending
                )
            )
        )

    def summary(self, provider_id):
        """Expose status only, never account identifiers or credentials."""
        record = self._data["providers"][provider_id]
        return {
            "paused": self.paused(provider_id),
            "paused_accounts": len(record["accounts"]),
            "storage_available": self._loaded and not self._failed,
        }

    @asynccontextmanager
    async def operation(self, provider_id, account_id=None):
        """Fence and register standalone I/O, including cancellation on Pause."""
        if self.paused(provider_id, account_id):
            raise ProviderPaused("provider_paused")
        task = asyncio.current_task()
        key = (provider_id, account_id)
        tasks = self._operations.setdefault(key, {})
        tasks[task] = tasks.get(task, 0) + 1
        try:
            try:
                yield
            except asyncio.CancelledError as error:
                if task in self._control_cancelled and error.args == (_PAUSE_CANCEL,):
                    raise ProviderPaused("provider_paused") from None
                raise
            # A denied callback may run inside this task. Do not publish its
            # late result even when that caller deliberately was not cancelled.
            if self.paused(provider_id, account_id):
                raise ProviderPaused("provider_paused")
        finally:
            tasks[task] -= 1
            if not tasks[task]:
                del tasks[task]
            if not tasks:
                self._operations.pop(key, None)
            if not any(task in registered for registered in self._operations.values()):
                if task in self._control_cancelled:
                    self._control_cancelled.discard(task)
                    # Convert only our own cancellation. Any independently
                    # requested unload/shutdown cancellation remains intact.
                    task.uncancel()

    def _cancel_operations(self, provider_id=None, account_id=None, *, exclude=()):
        current = asyncio.current_task()
        tasks = {
            task
            for (provider, account), registered in self._operations.items()
            if provider_id is None
            or (provider == provider_id and (account_id is None or account == account_id))
            for task in registered
            if task is not current and task not in exclude
        }
        for task in tasks:
            if not task.done() and task not in self._control_cancelled:
                self._control_cancelled.add(task)
                task.cancel(_PAUSE_CANCEL)
        return tasks

    async def _drain_operations(self, provider_id=None, account_id=None, *, already_cancelled=(), exclude=()):
        tasks = self._cancel_operations(provider_id, account_id, exclude=exclude) | set(already_cancelled)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _schedule_reload(self):
        if self._reload_task is None or self._reload_task.done():
            async def reload_entry():
                # The task is deliberately distinct from a provider's denial
                # callback, whose polling task can be stopped during unload.
                try:
                    from . import frontend

                    frontend.preserve_for_reload(self.hass, self.entry_id)
                    loaded = await self.hass.config_entries.async_reload(self.entry_id)
                    if loaded is False:
                        await self._schedule_stop_only()
                except Exception as error:
                    _LOGGER.warning("HomeCircle paused connection reload failed (%s)", type(error).__name__)
                    await self._schedule_stop_only()

            self._reload_task = self.hass.async_create_task(
                reload_entry(), f"HomeCircle connection controls {self.entry_id}"
            )
        return self._reload_task

    def _schedule_stop_only(self):
        """A failed write must stop clients without reloading stale disk state."""
        if self._stop_task is None or self._stop_task.done():
            async def stop_clients():
                entry = self.hass.config_entries.async_get_entry(self.entry_id)
                runtime = getattr(entry, "runtime_data", None) if entry else None
                for client in list(getattr(runtime, "managed_trackers", {}).values()):
                    try:
                        await client.async_stop()
                    except Exception as error:
                        _LOGGER.warning("HomeCircle stopped connection cleanup failed (%s)", type(error).__name__)

            self._stop_task = self.hass.async_create_task(
                stop_clients(), f"HomeCircle fail-closed connection cleanup {self.entry_id}"
            )
        return self._stop_task

    async def _change(self, provider_id, paused, reason, account_id, *, wait_reload):
        if provider_id not in PROVIDERS or type(paused) is not bool or reason not in REASONS:
            raise ValueError("Invalid provider control")
        if account_id is not None and (
            provider_id != "findmy" or not isinstance(account_id, str)
            or not 1 <= len(account_id) <= 256
        ):
            raise ValueError("Invalid provider account control")
        key = (provider_id, account_id)
        if paused:
            # No await may precede this stop: concurrent I/O sees it at once.
            self._epochs[provider_id] += 1
            self._pending[key] = self._epochs[provider_id]
        stopping = self._cancel_operations(provider_id, account_id) if paused else set()
        epoch = self._epochs[provider_id]

        async def persist():
            if not paused and self._stop_task and not self._stop_task.done():
                await asyncio.shield(self._stop_task)
            async with self._lock:
                if not paused and self._epochs[provider_id] != epoch:
                    raise ProviderPaused("provider_paused")
                updated = deepcopy(self._data)
                record = updated["providers"][provider_id]
                if account_id is None:
                    record.update(paused=paused, reason=reason if paused else None)
                    if not paused:
                        record["accounts"] = {}
                elif paused:
                    record["accounts"][account_id] = reason
                else:
                    record["accounts"].pop(account_id, None)
                updated["revision"] += 1
                try:
                    _validate(updated)
                    await self.store.async_save(updated)
                except (Exception, asyncio.CancelledError) as error:
                    self._storage_failed()
                    raise ProviderControlsError("provider_controls_storage_failed") from error
                self._data = updated
                self._failed = False
                if paused:
                    if self._pending.get(key) == epoch:
                        self._pending.pop(key)
                elif self._epochs[provider_id] == epoch:
                    self._pending = {
                        pending: generation
                        for pending, generation in self._pending.items()
                        if pending[0] != provider_id or (account_id is not None and pending != key)
                    }

        # Cancellation of a poller must not abandon its durable stop, even if
        # it is waiting for a sibling's write lock when unload cancels it.
        outcome, cancelled = await _owned_result(persist())
        caller = asyncio.current_task()

        async def finish():
            if isinstance(outcome, ProviderControlsError):
                await self._drain_operations(already_cancelled=stopping, exclude=(caller,))
                stop_task = self._schedule_stop_only()
                if wait_reload:
                    await asyncio.shield(stop_task)
                return
            if isinstance(outcome, BaseException):
                return
            if paused:
                await self._drain_operations(
                    provider_id, account_id, already_cancelled=stopping, exclude=(caller,)
                )
            reload_task = self._schedule_reload()
            if wait_reload:
                await asyncio.shield(reload_task)
            if not paused and self.paused(provider_id, account_id):
                raise ProviderPaused("provider_paused")

        final_outcome, final_cancelled = await _owned_result(finish())
        if cancelled is not None or final_cancelled is not None:
            cancellation = final_cancelled if final_cancelled is not None else cancelled
            if cancelled is not None and cancelled.args != (_PAUSE_CANCEL,):
                cancellation = cancelled
            raise cancellation
        if isinstance(outcome, BaseException):
            raise outcome
        if isinstance(final_outcome, BaseException):
            raise final_outcome

    async def async_pause_denied(self, provider_id, account_id=None):
        await self._change(provider_id, True, "access_denied", account_id, wait_reload=False)

    async def async_set_paused(self, provider_id, paused, *, reason="manual", account_id=None):
        await self._change(provider_id, paused, reason, account_id, wait_reload=True)

    async def async_remove(self):
        if self._reload_task and not self._reload_task.done():
            self._reload_task.cancel()
            await asyncio.gather(self._reload_task, return_exceptions=True)
        if self._stop_task and not self._stop_task.done():
            await asyncio.gather(self._stop_task, return_exceptions=True)
        await self._drain_operations()
        await self.store.async_remove()


def get_loaded_controls(hass, entry_id):
    """Return the single shared object; only setup/flow helpers may load it."""
    return hass.data.get(_DATA_KEY, {}).get(entry_id)


async def async_get_controls(hass, entry_id):
    controls = hass.data.setdefault(_DATA_KEY, {}).setdefault(
        entry_id, ProviderControls(hass, entry_id)
    )
    await controls.async_load()
    return controls


async def async_remove_controls(hass, entry_id):
    controls = await async_get_controls(hass, entry_id)
    await controls.async_remove()
    hass.data.get(_DATA_KEY, {}).pop(entry_id, None)
