"""Managed provider contract with two fictional, independent connections."""

from dataclasses import replace
from types import SimpleNamespace

from homeassistant.helpers import entity_registry as er

from custom_components.homecircle import device_tracker as tracker_platform
from custom_components.homecircle import tracker_providers
from custom_components.homecircle.api import provider_alerts
from custom_components.homecircle.config_flow import SelectionFlow
from custom_components.homecircle.const import DOMAIN
from custom_components.homecircle.selection import household_errors
from custom_components.homecircle.tracker_providers import ProviderHealth


def test_provider_first_setup_uses_registry_not_life360_key(hass, monkeypatch):
    hass.states.async_set("zone.home", "zoning")
    provider = replace(
        tracker_providers.TRACKER_PROVIDERS[0],
        id="example",
        enabled_key="example_direct",
        account_key="example_account",
    )
    monkeypatch.setattr(tracker_providers, "TRACKER_PROVIDERS", (provider,))
    selection = {"primary_home": "zone.home", "people": [], "pets": []}
    assert household_errors(hass, selection)["base"] == "no_members"
    assert household_errors(hass, {**selection, "life360_direct": True})["base"] == (
        "no_members"
    )
    assert household_errors(hass, {**selection, "example_direct": True}) == {}


def test_reauth_selects_only_the_failing_registered_provider(monkeypatch):
    first = replace(
        tracker_providers.TRACKER_PROVIDERS[0],
        id="first",
        account_key="first_account",
        reauth_step="async_step_first_reauth",
    )
    second = replace(
        first,
        id="second",
        account_key="second_account",
        reauth_step="async_step_second_reauth",
    )
    monkeypatch.setattr(tracker_providers, "TRACKER_PROVIDERS", (first, second))
    config = {"first_account": {"secret": "example"}, "second_account": {"secret": "example"}}
    assert tracker_providers.reauth_provider(config, "second") is second
    assert tracker_providers.reauth_provider(config, "first") is first
    assert tracker_providers.reauth_provider(config, None) is None
    assert tracker_providers.reauth_provider(config, "unknown") is None
    assert tracker_providers.reauth_provider({"first_account": config["first_account"]}, None) is first
    monkeypatch.setattr(
        tracker_providers, "TRACKER_PROVIDERS", (first, replace(second, reauth_step=None))
    )
    assert tracker_providers.reauth_provider(config, None) is None


async def test_multiple_managed_trackers_start_and_disconnect_independently(
    hass, monkeypatch
):
    events = []

    class FakeClient:
        def __init__(self, provider_id):
            self.provider_id = provider_id

        async def async_start(self):
            events.append(("start", self.provider_id))

        async def async_stop(self):
            events.append(("stop", self.provider_id))

    def provider(provider_id):
        return tracker_providers.TrackerProvider(
            id=provider_id,
            display_name=provider_id.title(),
            account_key=f"{provider_id}_account",
            enabled_key=f"{provider_id}_enabled",
            replace_key=f"replace_{provider_id}_login",
            setup_step=f"async_step_{provider_id}_account",
            unique_id_prefix=f"homecircle_{provider_id}_",
            platform="device_tracker",
            client_factory=lambda _hass, _account, _add, _entry_id: FakeClient(
                provider_id
            ),
        )

    monkeypatch.setattr(
        tracker_providers, "TRACKER_PROVIDERS", (provider("first"), provider("second"))
    )
    config = {
        "first_account": {"secret": "example"},
        "second_account": {"secret": "example"},
    }
    runtime = SimpleNamespace(config=config, managed_trackers={})
    entry = SimpleNamespace(runtime_data=runtime, entry_id="example-entry")
    await tracker_platform.async_setup_entry(hass, entry, lambda _: None)
    assert events == [("start", "first"), ("start", "second")]
    assert set(runtime.managed_trackers) == {"first", "second"}

    registry = er.async_get(hass)
    first = registry.async_get_or_create(
        "device_tracker", DOMAIN, "homecircle_first_member"
    )
    second = registry.async_get_or_create(
        "device_tracker", DOMAIN, "homecircle_second_member"
    )
    selected = {first.entity_id, second.entity_id}
    assert (
        tracker_providers.disconnected_owned_entities(registry, config, selected)
        == set()
    )
    assert tracker_providers.disconnected_owned_entities(
        registry, {"second_account": config["second_account"]}, selected
    ) == {first.entity_id}

    for client in runtime.managed_trackers.values():
        await client.async_stop()
    assert events[-2:] == [("stop", "first"), ("stop", "second")]


async def test_provider_account_steps_run_before_member_setup():
    class FakeFlow(SelectionFlow):
        async def async_step_first_account(self):
            return {"step_id": "first_account"}

        async def async_step_second_account(self):
            return {"step_id": "second_account"}

        async def async_step_confirm(self):
            return {"step_id": "confirm"}

    def provider(provider_id):
        return tracker_providers.TrackerProvider(
            id=provider_id,
            display_name=provider_id.title(),
            account_key=f"{provider_id}_account",
            enabled_key=f"{provider_id}_enabled",
            replace_key=f"replace_{provider_id}_login",
            setup_step=f"async_step_{provider_id}_account",
            unique_id_prefix=f"homecircle_{provider_id}_",
            platform="device_tracker",
            client_factory=lambda *_: None,
        )

    flow = FakeFlow()
    flow.start({})
    flow.pending_connections = [provider("first"), provider("second")]
    assert (await flow.async_step_next_connection())["step_id"] == "first_account"
    assert (await flow.connection_saved("first", {"secret": "example"}))["step_id"] == (
        "second_account"
    )
    assert (await flow.connection_saved("second", {"secret": "example"}))[
        "step_id"
    ] == ("confirm")
    assert flow.draft["first_account"]["secret"] == "example"
    assert flow.draft["second_account"]["secret"] == "example"


async def test_setup_warns_when_external_life360_trackers_already_exist(hass):
    registry = er.async_get(hass)
    plain = tracker_providers.setup_status(hass, {})
    assert "separate Life360 integration" not in plain

    existing = registry.async_get_or_create(
        "device_tracker", "life360", "example-member"
    )
    hass.states.async_set(existing.entity_id, "home")
    status = tracker_providers.setup_status(hass, {})
    assert "separate Life360 integration" in status
    assert "duplicate trackers" in status
    assert "Select one tracker per member" in status

    connected = tracker_providers.setup_status(
        hass, {"life360_account": {"method": "token", "secret": "example"}}
    )
    assert "duplicate trackers" in connected
    assert "waiting for trackers" in connected


def test_ready_trackers_prompt_until_one_owned_tracker_is_explicitly_selected(hass):
    registry = er.async_get(hass)
    external = registry.async_get_or_create(
        "device_tracker", "life360", "example_external"
    )
    owned = registry.async_get_or_create(
        "device_tracker", DOMAIN, "homecircle_life360_example_member"
    )
    hass.states.async_set(
        "person.example_member", "home", {"source": owned.entity_id}
    )
    client = SimpleNamespace(
        health_snapshot=lambda: ProviderHealth(
            state="connected", discovered_trackers=2, available_trackers=2
        )
    )
    runtime = SimpleNamespace(
        config={
            "life360_account": {"method": "token", "secret": "example"},
            "primary_home": "zone.home",
            "places": [],
            "people": ["person.example_member"],
            "members": {
                "person.example_member": {
                    "trackers": [external.entity_id],
                    "additional_residences": [],
                }
            },
        },
        managed_trackers={"life360": client},
        household=SimpleNamespace(members=(SimpleNamespace(id="person.example_member"),)),
    )
    assert provider_alerts(hass, runtime) == [
        {"name": "Life360", "state": "selection_needed"}
    ]
    runtime.config["members"]["person.example_member"]["trackers"] = [
        owned.entity_id
    ]
    assert provider_alerts(hass, runtime) == []
