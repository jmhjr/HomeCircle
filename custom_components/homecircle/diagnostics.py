"""Safe provider diagnostics for unsupported API troubleshooting.

Never export account configuration, member IDs, coordinates, addresses, or raw
provider responses. Home Assistant's diagnostics download may be shared.
"""

from .tracker_providers import ProviderHealth, connected_providers


async def async_get_config_entry_diagnostics(hass, entry) -> dict:
    """Report only allowlisted connection state and aggregate counts."""
    config = dict(entry.options or entry.data)
    runtime = getattr(entry, "runtime_data", None)
    clients = runtime.managed_trackers if runtime else {}
    return {
        "schema": 1,
        "providers": {
            provider.id: (
                clients[provider.id].health_snapshot()
                if provider.id in clients
                else ProviderHealth(state="not_loaded")
            ).as_dict()
            for provider in connected_providers(config)
        },
    }
