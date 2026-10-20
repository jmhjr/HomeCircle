"""HomeCircle-owned trackers from optional managed provider connections."""

import asyncio
from functools import partial
import logging

from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .tracker_providers import connected_providers


_LOGGER = logging.getLogger(__name__)


async def _async_stop_after_startup(clients):
    """Drain owned cleanup before propagating even repeated caller cancellation."""

    async def cleanup():
        for provider_id, client in clients:
            try:
                await client.async_stop()
            except (Exception, asyncio.CancelledError) as error:
                # One provider's own cleanup failure must not abandon siblings.
                _LOGGER.warning(
                    "HomeCircle tracker provider %s cleanup failed (%s)",
                    provider_id,
                    type(error).__name__,
                )

    task = asyncio.create_task(cleanup())
    # Python 3.14 may automatically log a shielded task's later failure after
    # caller cancellation. Observe it as a result, then preserve the original
    # task.result() failure/cancellation precedence after all cleanup is drained.
    drained = asyncio.gather(task, return_exceptions=True)
    cancelled = False
    while True:
        try:
            await asyncio.shield(drained)
            break
        except asyncio.CancelledError:
            cancelled = True
            if drained.done():
                break
    task.result()
    if cancelled:
        raise asyncio.CancelledError


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = entry.runtime_data
    started = []
    current = None
    try:
        for provider in connected_providers(runtime.config):
            if provider.platform != "device_tracker":
                continue
            issue_id = f"tracker_provider_start_{entry.entry_id}_{provider.id}"
            try:
                client = provider.client_factory(
                    hass,
                    runtime.config[provider.account_key],
                    async_add_entities,
                    entry.entry_id,
                )
                current = (provider.id, client)
                await client.async_start()
            except Exception as error:
                if current is not None:
                    failed = current
                    current = None
                    await _async_stop_after_startup([failed])
                _LOGGER.warning(
                    "HomeCircle tracker provider %s could not start (%s)",
                    provider.id,
                    type(error).__name__,
                )
                ir.async_create_issue(
                    hass,
                    DOMAIN,
                    issue_id,
                    is_fixable=False,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key="tracker_provider_start_failed",
                    translation_placeholders={"provider": provider.display_name},
                )
                entry.async_on_unload(
                    partial(ir.async_delete_issue, hass, DOMAIN, issue_id)
                )
                continue
            runtime.managed_trackers[provider.id] = client
            started.append(current)
            current = None
            ir.async_delete_issue(hass, DOMAIN, issue_id)
    except asyncio.CancelledError:
        # Cancellation aborts this platform setup. Drain only resources created
        # by this invocation; ordinary provider failures leave siblings running.
        cleanup = ([current] if current is not None else []) + list(reversed(started))
        try:
            await _async_stop_after_startup(cleanup)
        finally:
            for provider_id, client in started:
                if runtime.managed_trackers.get(provider_id) is client:
                    runtime.managed_trackers.pop(provider_id)
        raise
