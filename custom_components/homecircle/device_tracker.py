"""HomeCircle-owned trackers from optional managed provider connections."""

from .tracker_providers import connected_providers


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = entry.runtime_data
    try:
        for provider in connected_providers(runtime.config):
            if provider.platform != "device_tracker":
                continue
            client = provider.client_factory(
                hass,
                runtime.config[provider.account_key],
                async_add_entities,
                entry.entry_id,
            )
            runtime.managed_trackers[provider.id] = client
            await client.async_start()
    except Exception:
        for client in reversed(list(runtime.managed_trackers.values())):
            await client.async_stop()
        runtime.managed_trackers.clear()
        raise
