"""Contract for optional HomeCircle-managed tracker connections.

Every provider creates ordinary HA device trackers. Household selection and
normalization consume those entities exactly like trackers from other integrations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Protocol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import CONF_LIFE360_ACCOUNT, CONF_LIFE360_DIRECT, DOMAIN

HEALTH_STATES = frozenset(
    {
        "not_loaded",
        "starting",
        "discovering",
        "connected",
        "partial",
        "auth_required",
        "rate_limited",
        "network_error",
        "api_error",
        "unexpected_response",
    }
)
REAUTH_PROVIDER_KEY = "_homecircle_reauth_provider"


class TrackerClient(Protocol):
    """Minimum lifecycle shared by managed tracker providers."""

    async def async_start(self) -> None: ...

    async def async_stop(self) -> None: ...

    def health_snapshot(self) -> ProviderHealth:
        """Return only safe status codes, counts, and operation times."""
        ...


@dataclass(frozen=True)
class ProviderHealth:
    """Allowlisted diagnostics shared by current and future providers."""

    state: str
    discovered_trackers: int = 0
    available_trackers: int = 0
    last_api_success: datetime | None = None
    last_error: datetime | None = None
    retry_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.state not in HEALTH_STATES:
            raise ValueError("Unknown tracker provider health state")

    def as_dict(self) -> dict[str, str | int | None]:
        return {
            "state": self.state,
            "discovered_trackers": self.discovered_trackers,
            "available_trackers": self.available_trackers,
            "last_api_success": self.last_api_success.isoformat()
            if self.last_api_success
            else None,
            "last_error": self.last_error.isoformat() if self.last_error else None,
            "retry_at": self.retry_at.isoformat() if self.retry_at else None,
        }


type ClientFactory = Callable[[HomeAssistant, dict[str, str], Any, str], TrackerClient]


@dataclass(frozen=True)
class TrackerProvider:
    """Stable identity, storage key, and HA entity ownership for one provider."""

    id: str
    display_name: str
    account_key: str
    enabled_key: str
    replace_key: str
    setup_step: str
    unique_id_prefix: str
    platform: str
    client_factory: ClientFactory
    external_platforms: tuple[str, ...] = ()
    reauth_step: str | None = None

    def connected(self, config: dict[str, Any]) -> bool:
        return bool(config.get(self.account_key))

    def owns_entity(self, registry: er.EntityRegistry, entity_id: str) -> bool:
        entity = registry.async_get(entity_id)
        return bool(
            entity
            and entity.platform == DOMAIN
            and entity.unique_id.startswith(self.unique_id_prefix)
        )


def _life360_client(hass, account, add_entities, entry_id):
    from .life360_direct import DirectLife360

    return DirectLife360(hass, account, add_entities, entry_id)


TRACKER_PROVIDERS = (
    TrackerProvider(
        id="life360",
        display_name="Life360",
        account_key=CONF_LIFE360_ACCOUNT,
        enabled_key=CONF_LIFE360_DIRECT,
        replace_key="replace_life360_login",
        setup_step="async_step_life360_account",
        unique_id_prefix="homecircle_life360_",
        platform="device_tracker",
        client_factory=_life360_client,
        external_platforms=("life360",),
        reauth_step="async_step_reauth_confirm",
    ),
)


def connected_providers(config: dict[str, Any]) -> tuple[TrackerProvider, ...]:
    """Connections are independent; an entry may use more than one provider."""
    return tuple(
        provider for provider in TRACKER_PROVIDERS if provider.connected(config)
    )


def connection_requested(config: dict[str, Any]) -> bool:
    """Allow provider-first setup before its trackers exist in Home Assistant."""
    return any(config.get(provider.enabled_key) for provider in TRACKER_PROVIDERS)


def reauth_provider(config: dict[str, Any], provider_id: str | None) -> TrackerProvider | None:
    """Route repair to the failing connection, including old single-provider flows."""
    providers = connected_providers(config)
    if provider_id is not None:
        return next(
            (
                provider
                for provider in providers
                if provider.id == provider_id and provider.reauth_step
            ),
            None,
        )
    return providers[0] if len(providers) == 1 and providers[0].reauth_step else None


def disconnected_owned_entities(
    registry: er.EntityRegistry, config: dict[str, Any], selected: set[str]
) -> set[str]:
    """Do not remove a provider while household members use its trackers."""
    return {
        entity_id
        for entity_id in selected
        if any(
            not provider.connected(config) and provider.owns_entity(registry, entity_id)
            for provider in TRACKER_PROVIDERS
        )
    }


def setup_status(
    hass: HomeAssistant,
    config: dict[str, Any],
    clients: dict[str, TrackerClient] | None = None,
) -> str:
    """Give Options a credential-free summary of managed tracker discovery."""
    registry = er.async_get(hass)
    lines = []
    for provider in TRACKER_PROVIDERS:
        if any(
            any(
                entry.disabled_by is None
                for entry in hass.config_entries.async_entries(platform)
            )
            or any(
                entity.platform == platform
                and entity.disabled_by is None
                and hass.states.get(entity.entity_id) is not None
                for entity in registry.entities.values()
            )
            for platform in provider.external_platforms
        ):
            lines.append(
                f"A separate {provider.display_name} integration is present. "
                "Its trackers can be selected here. Connecting the account in "
                "HomeCircle too may create duplicate trackers and additional "
                "provider requests. Select one tracker per member."
            )
    providers = connected_providers(config)
    if not providers:
        lines.append(
            "No built in tracker account connected. Existing HA trackers are available."
        )
        return " ".join(lines)
    guidance = {
        "auth_required": "sign-in needs attention; open the Home Assistant repair prompt",
        "rate_limited": "temporarily rate limited; HomeCircle will retry",
        "network_error": "network request failed; HomeCircle will retry",
        "api_error": "provider request failed; check diagnostics if it continues",
        "unexpected_response": "unexpected provider response; check diagnostics if it continues",
        "partial": "some member requests failed; check diagnostics if it continues",
    }
    for provider in providers:
        state = (
            clients[provider.id].health_snapshot().state
            if clients and provider.id in clients
            else None
        )
        if state in guidance:
            lines.append(f"{provider.display_name}: {guidance[state]}.")
        states = [
            state
            for state in hass.states.async_all(provider.platform)
            if provider.owns_entity(registry, state.entity_id)
        ]
        if not states:
            if state not in guidance:
                lines.append(
                    f"{provider.display_name}: waiting for trackers. Reopen Options after discovery."
                )
            continue
        available = sum(
            state.state not in ("unknown", "unavailable") for state in states
        )
        lines.append(
            f"{provider.display_name}: {len(states)} tracker(s) found, "
            f"{available} reporting. Choose members under People trackers or Pet trackers."
        )
    return " ".join(lines)
