"""Provider startup failures preserve independent clients without network calls."""

import asyncio
from dataclasses import replace
from unittest.mock import Mock

import pytest
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.homecircle import (
    HomeCircleRuntime,
    device_tracker as tracker_platform,
)
from custom_components.homecircle import findmy_provider, tracker_providers
from custom_components.homecircle.const import DOMAIN
from custom_components.homecircle.diagnostics import async_get_config_entry_diagnostics
from custom_components.homecircle.tracker_providers import ProviderHealth


PRIVATE_ERROR_CANARY = "synthetic-private-startup-error"
BASE_PROVIDERS = tracker_providers.TRACKER_PROVIDERS


class SyntheticClient:
    """Own a real background task so cleanup assertions observe resources."""

    def __init__(self, hass, *, start_error=None, stop_error=None, block_start=False):
        self.hass = hass
        self.start_error = start_error
        self.stop_error = stop_error
        self.block_start = block_start
        self.started = asyncio.Event()
        self.task = None
        self.stop_calls = 0

    async def async_start(self):
        self.task = self.hass.async_create_background_task(
            asyncio.Event().wait(), "Synthetic managed tracker task", eager_start=False
        )
        self.started.set()
        if self.block_start:
            await asyncio.Event().wait()
        if self.start_error:
            raise self.start_error

    async def async_stop(self):
        self.stop_calls += 1
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
        if self.stop_error:
            raise self.stop_error

    def health_snapshot(self):
        return ProviderHealth(state="connected")


def provider(provider_id, factory):
    return replace(
        BASE_PROVIDERS[0],
        id=provider_id,
        display_name=f"Synthetic {provider_id}",
        account_key=f"{provider_id}_account",
        client_factory=factory,
    )


def entry_with_runtime(hass, config):
    entry = MockConfigEntry(domain=DOMAIN, title="Synthetic HomeCircle", data=config)
    entry.add_to_hass(hass)
    entry.runtime_data = HomeCircleRuntime(config=config)
    return entry


def issue_id(entry, provider_id):
    return f"tracker_provider_start_{entry.entry_id}_{provider_id}"


async def stop_clients(*clients):
    await asyncio.gather(
        *(client.async_stop() for client in clients), return_exceptions=True
    )


async def test_real_findmy_sdk_import_failure_preserves_life360_and_later_provider(
    hass, monkeypatch, caplog
):
    life360 = SyntheticClient(hass)
    later = SyntheticClient(hass)
    descriptors = (
        replace(BASE_PROVIDERS[0], client_factory=lambda *_: life360),
        BASE_PROVIDERS[1],
        provider("later", lambda *_: later),
    )
    monkeypatch.setattr(tracker_providers, "TRACKER_PROVIDERS", descriptors)
    sdk = Mock(side_effect=ImportError(PRIVATE_ERROR_CANARY))
    monkeypatch.setattr(findmy_provider, "sdk", sdk)
    vault_root = Mock(side_effect=AssertionError("No account storage may be read"))
    monkeypatch.setattr(findmy_provider, "account_root", vault_root)
    stopped_findmy = []
    original_stop = findmy_provider.DirectFindMy.async_stop

    async def observe_stop(client):
        stopped_findmy.append(client)
        await original_stop(client)

    monkeypatch.setattr(findmy_provider.DirectFindMy, "async_stop", observe_stop)
    config = {
        "life360_account": {"method": "token", "secret": "example"},
        "findmy_accounts": {
            "a" * 32: {
                "label": "Synthetic account",
                "storage_id": "a" * 32,
                "items": {
                    "example": {
                        "name": "Synthetic accessory",
                        "type": "airtag",
                        "unique_id": "homecircle_findmy_example",
                    }
                },
            }
        },
        "later_account": {"configured": True},
    }
    entry = entry_with_runtime(hass, config)
    registry = er.async_get(hass)
    registered = registry.async_get_or_create(
        "device_tracker", DOMAIN, "homecircle_findmy_example", config_entry=entry
    )
    registry_before = dict(registry.entities)
    try:
        # Exercise the actual shared platform and actual Find My async_start.
        # The Life360 transport is synthetic; sdk() fails before Apple/vault work.
        await tracker_platform.async_setup_entry(hass, entry, lambda _: None)
        assert entry.runtime_data.managed_trackers == {
            "life360": life360,
            "later": later,
        }
        assert life360.stop_calls == later.stop_calls == 0
        assert life360.task is not None and not life360.task.done()
        assert later.task is not None and not later.task.done()
        sdk.assert_called_once_with()
        vault_root.assert_not_called()
        assert len(stopped_findmy) == 1
        assert stopped_findmy[0].stopped and not stopped_findmy[0].clients
        issue = ir.async_get(hass).issues[(DOMAIN, issue_id(entry, "findmy"))]
        assert issue.translation_key == "tracker_provider_start_failed"
        assert issue.translation_placeholders == {"provider": "Apple Find My"}
        diagnostics = await async_get_config_entry_diagnostics(hass, entry)
        assert diagnostics["providers"]["life360"]["state"] == "connected"
        assert diagnostics["providers"]["findmy"]["state"] == "not_loaded"
        assert PRIVATE_ERROR_CANARY not in caplog.text + repr(diagnostics) + repr(issue)
        # Startup never deletes existing registry rows. Recorder history is not
        # exercised here, so this test makes no claim about recorded history.
        assert dict(registry.entities) == registry_before
        assert registry.async_get(registered.entity_id) is registered
    finally:
        await stop_clients(life360, later)
        await entry._async_process_on_unload(hass)


async def test_factory_failure_does_not_prevent_later_provider_start(hass, monkeypatch):
    later = SyntheticClient(hass)
    failing_factory = Mock(side_effect=ImportError(PRIVATE_ERROR_CANARY))
    monkeypatch.setattr(
        tracker_providers,
        "TRACKER_PROVIDERS",
        (provider("first", failing_factory), provider("later", lambda *_: later)),
    )
    entry = entry_with_runtime(
        hass,
        {"first_account": {"configured": True}, "later_account": {"configured": True}},
    )
    try:
        await tracker_platform.async_setup_entry(hass, entry, lambda _: None)
        assert entry.runtime_data.managed_trackers == {"later": later}
        assert later.stop_calls == 0
        assert (DOMAIN, issue_id(entry, "first")) in ir.async_get(hass).issues
    finally:
        await stop_clients(later)
        await entry._async_process_on_unload(hass)


@pytest.mark.parametrize("cleanup_failure", [None, RuntimeError, asyncio.CancelledError])
async def test_partial_start_is_cleaned_and_cleanup_failure_does_not_stop_siblings(
    hass, monkeypatch, caplog, cleanup_failure
):
    earlier = SyntheticClient(hass)
    failed = SyntheticClient(
        hass,
        start_error=RuntimeError(PRIVATE_ERROR_CANARY),
        stop_error=cleanup_failure(PRIVATE_ERROR_CANARY) if cleanup_failure else None,
    )
    later = SyntheticClient(hass)
    monkeypatch.setattr(
        tracker_providers,
        "TRACKER_PROVIDERS",
        tuple(
            provider(name, lambda *_, client=client: client)
            for name, client in (
                ("earlier", earlier),
                ("failed", failed),
                ("later", later),
            )
        ),
    )
    entry = entry_with_runtime(
        hass,
        {
            f"{name}_account": {"configured": True}
            for name in ("earlier", "failed", "later")
        },
    )
    try:
        await tracker_platform.async_setup_entry(hass, entry, lambda _: None)
        assert entry.runtime_data.managed_trackers == {
            "earlier": earlier,
            "later": later,
        }
        assert earlier.stop_calls == later.stop_calls == 0
        assert failed.stop_calls == 1
        assert failed.task is not None and failed.task.done()
        assert PRIVATE_ERROR_CANARY not in caplog.text
        assert (DOMAIN, issue_id(entry, "failed")) in ir.async_get(hass).issues
    finally:
        await stop_clients(earlier, later)
        await entry._async_process_on_unload(hass)


async def test_cancellation_is_terminal_and_cleans_current_and_newly_started_clients(
    hass, monkeypatch
):
    earlier = SyntheticClient(hass)
    pending = SyntheticClient(hass, block_start=True)
    later = SyntheticClient(hass)
    monkeypatch.setattr(
        tracker_providers,
        "TRACKER_PROVIDERS",
        tuple(
            provider(name, lambda *_, client=client: client)
            for name, client in (
                ("earlier", earlier),
                ("pending", pending),
                ("later", later),
            )
        ),
    )
    entry = entry_with_runtime(
        hass,
        {
            f"{name}_account": {"configured": True}
            for name in ("earlier", "pending", "later")
        },
    )
    task = asyncio.create_task(
        tracker_platform.async_setup_entry(hass, entry, lambda _: None)
    )
    await pending.started.wait()
    task.cancel()
    try:
        with pytest.raises(asyncio.CancelledError):
            await task
        assert earlier.stop_calls == pending.stop_calls == 1
        assert earlier.task is not None and earlier.task.done()
        assert pending.task is not None and pending.task.done()
        assert later.task is None
        assert not entry.runtime_data.managed_trackers
        assert (DOMAIN, issue_id(entry, "pending")) not in ir.async_get(hass).issues
    finally:
        await stop_clients(earlier, pending, later)


async def test_success_clears_stale_startup_issue_and_unload_clears_current_issue(
    hass, monkeypatch
):
    good = SyntheticClient(hass)
    failed = SyntheticClient(hass, start_error=ImportError(PRIVATE_ERROR_CANARY))
    monkeypatch.setattr(
        tracker_providers,
        "TRACKER_PROVIDERS",
        (provider("good", lambda *_: good), provider("failed", lambda *_: failed)),
    )
    entry = entry_with_runtime(
        hass,
        {"good_account": {"configured": True}, "failed_account": {"configured": True}},
    )
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id(entry, "good"),
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="tracker_provider_start_failed",
        translation_placeholders={"provider": "Synthetic good"},
    )
    try:
        await tracker_platform.async_setup_entry(hass, entry, lambda _: None)
        assert (DOMAIN, issue_id(entry, "good")) not in ir.async_get(hass).issues
        assert (DOMAIN, issue_id(entry, "failed")) in ir.async_get(hass).issues
        await entry._async_process_on_unload(hass)
        assert (DOMAIN, issue_id(entry, "failed")) not in ir.async_get(hass).issues
    finally:
        await stop_clients(good)


@pytest.mark.parametrize("during_failed_cleanup", [False, True])
async def test_repeated_cancellation_drains_cleanup_before_releasing_started_clients(
    hass, monkeypatch, during_failed_cleanup
):
    cleanup_entered, release_cleanup = asyncio.Event(), asyncio.Event()
    events = []

    class EarlierClient(SyntheticClient):
        async def async_stop(self):
            events.append("earlier cleanup")
            await super().async_stop()

    class GatedCleanupClient(SyntheticClient):
        async def async_stop(self):
            events.append("current cleanup entered")
            cleanup_entered.set()
            await release_cleanup.wait()
            await super().async_stop()
            events.append("current cleanup completed")

    earlier = EarlierClient(hass)
    current = GatedCleanupClient(
        hass,
        start_error=ImportError(PRIVATE_ERROR_CANARY)
        if during_failed_cleanup
        else None,
        block_start=not during_failed_cleanup,
    )
    later = SyntheticClient(hass)
    monkeypatch.setattr(
        tracker_providers,
        "TRACKER_PROVIDERS",
        tuple(
            provider(name, lambda *_, client=client: client)
            for name, client in (
                ("earlier", earlier),
                ("current", current),
                ("later", later),
            )
        ),
    )
    entry = entry_with_runtime(
        hass,
        {
            f"{name}_account": {"configured": True}
            for name in ("earlier", "current", "later")
        },
    )
    task = asyncio.create_task(
        tracker_platform.async_setup_entry(hass, entry, lambda _: None)
    )
    try:
        if during_failed_cleanup:
            await cleanup_entered.wait()
            task.cancel()
        else:
            await current.started.wait()
            task.cancel()
            await cleanup_entered.wait()
        for _ in range(2):
            await asyncio.sleep(0)
            task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        assert events == ["current cleanup entered"]
        assert entry.runtime_data.managed_trackers == {"earlier": earlier}
        assert earlier.stop_calls == 0
        assert later.task is None
        release_cleanup.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert events == [
            "current cleanup entered",
            "current cleanup completed",
            "earlier cleanup",
        ]
        assert current.stop_calls == earlier.stop_calls == 1
        assert current.task is not None and current.task.done()
        assert earlier.task is not None and earlier.task.done()
        assert not entry.runtime_data.managed_trackers
        assert (DOMAIN, issue_id(entry, "current")) not in ir.async_get(hass).issues
    finally:
        release_cleanup.set()
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await stop_clients(earlier, current, later)
