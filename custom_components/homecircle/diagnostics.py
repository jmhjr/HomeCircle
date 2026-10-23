"""Safe provider diagnostics for unsupported API troubleshooting.

Never export account configuration, member IDs, coordinates, addresses, or raw
provider responses. Home Assistant's diagnostics download may be shared.
"""

from .tracker_providers import ProviderHealth, connected_providers
from .provider_controls import PROVIDERS


async def async_get_config_entry_diagnostics(hass, entry) -> dict:
    """Report only allowlisted connection state and aggregate counts."""
    config = dict(entry.options or entry.data)
    runtime = getattr(entry, "runtime_data", None)
    clients = runtime.managed_trackers if runtime else {}
    result = {
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
    controls = getattr(runtime, "provider_controls", None)
    if controls is not None:
        result["connection_controls"] = {
            provider.id: controls.summary(provider.id)
            for provider in connected_providers(config)
            if provider.id in PROVIDERS
        }
        for provider_id, status in result["connection_controls"].items():
            if status["paused"]:
                result["providers"][provider_id] = ProviderHealth(state="paused").as_dict()
    findmy = clients.get("findmy")
    getter = getattr(findmy, "polling_snapshot", None)
    if callable(getter):
        from .findmy_provider import validated_polling_snapshot

        try:
            polling = validated_polling_snapshot(getter())
        except Exception:
            polling = None
        if polling is not None:
            result["findmy_polling"] = polling
    return result
