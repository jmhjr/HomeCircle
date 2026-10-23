"""HomeCircle-owned trackers from optional managed provider connections."""

import asyncio
from functools import partial
import logging

from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers import entity_registry as er
from homeassistant.components.device_tracker import TrackerEntity, SourceType

from .const import DOMAIN
from .tracker_providers import ProviderHealth, connected_providers
from .provider_controls import PROVIDERS, async_get_controls


_LOGGER = logging.getLogger(__name__)


class _PausedTracker(TrackerEntity):
    """Keep an already registered tracker unavailable, with its exact identity."""

    _attr_available = False
    _attr_should_poll = False

    def __init__(self, record):
        self.entity_id = record.entity_id
        self._attr_unique_id = record.unique_id
        self._attr_name = record.original_name or record.name

    @property
    def source_type(self):
        return SourceType.GPS


class _PausedClient:
    """A saved connection stays connected locally without loading its SDK."""

    def __init__(self, hass, entry_id, provider, add_entities):
        self.hass, self.entry_id = hass, entry_id
        self.provider, self.add_entities = provider, add_entities
        self.count = 0

    async def async_start(self):
        registry = er.async_get(self.hass)
        trackers = [
            _PausedTracker(record)
            for record in er.async_entries_for_config_entry(registry, self.entry_id)
            if record.domain == self.provider.platform
            and self.provider.owns_entity(registry, record.entity_id)
        ]
        self.count = len(trackers)
        self.add_entities(trackers)

    async def async_stop(self):
        return None

    def health_snapshot(self):
        return ProviderHealth("paused", discovered_trackers=self.count)


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
    controls = runtime.provider_controls = await async_get_controls(hass, entry.entry_id)
    started = []
    current = None
    try:
        for provider in connected_providers(runtime.config):
            if provider.platform != "device_tracker":
                continue
            issue_id = f"tracker_provider_start_{entry.entry_id}_{provider.id}"
            try:
                if provider.id in PROVIDERS and controls.paused(provider.id):
                    client = _PausedClient(hass, entry.entry_id, provider, async_add_entities)
                else:
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
