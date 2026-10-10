"""Selection refresh uses exact ownership, permission checks and shared limits."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from custom_components.homecircle.selection_refresh import async_refresh_selected


def scenario(platform="homecircle"):
    source = "device_tracker.example_phone"
    member = SimpleNamespace(
        id="person.example_member",
        focusable=True,
        location=SimpleNamespace(
            evidence=SimpleNamespace(source_entity=source, freshness="stale")
        ),
    )
    registered = SimpleNamespace(
        platform=platform,
        disabled=False,
        config_entry_id="example-entry",
        device_id="example-device",
        unique_id="homecircle_life360_example",
    )
    registry = SimpleNamespace(async_get=lambda _: registered)
    client = SimpleNamespace(
        async_refresh_on_selection=AsyncMock(return_value="checked")
    )
    runtime = SimpleNamespace(
        config={
            "members": {
                member.id: {"trackers": [source], "auto_request_location": True}
            }
        },
        location_request_store=SimpleNamespace(async_save=AsyncMock()),
        restored_location_requests=set(),
        selection_refresh_times={},
        managed_trackers={"life360": client},
        location_request_times={},
        last_location_request={},
        location_request_failures=set(),
    )
    user = SimpleNamespace(permissions=SimpleNamespace(check_entity=lambda *_: True))
    hass = SimpleNamespace(services=SimpleNamespace(has_service=lambda *_: True))
    return hass, runtime, member, user, registry, client


async def test_cloud_check_is_shared_and_reserved_before_await():
    hass, runtime, member, user, registry, client = scenario()

    async def check():
        assert runtime.selection_refresh_times
        return "checked"

    client.async_refresh_on_selection.side_effect = check
    with patch(
        "custom_components.homecircle.selection_refresh.er.async_get",
        return_value=registry,
    ):
        assert (
            await async_refresh_selected(hass, runtime, member, user, "example-entry")
        )["status"] == "checked"
        assert (
            await async_refresh_selected(hass, runtime, member, user, "example-entry")
        )["status"] == "cooldown"
    assert client.async_refresh_on_selection.await_count == 1


async def test_fresh_unselected_and_other_entry_never_poll():
    hass, runtime, member, user, registry, client = scenario()
    with patch(
        "custom_components.homecircle.selection_refresh.er.async_get",
        return_value=registry,
    ):
        member.location.evidence.freshness = "fresh"
        assert (
            await async_refresh_selected(hass, runtime, member, user, "example-entry")
        )["status"] == "fresh"
        member.location.evidence.freshness = "stale"
        assert (
            await async_refresh_selected(hass, runtime, member, user, "other-entry")
        )["status"] == "unsupported"
        runtime.config["members"][member.id]["trackers"] = []
        assert (
            await async_refresh_selected(hass, runtime, member, user, "example-entry")
        )["status"] == "unsupported"
    client.async_refresh_on_selection.assert_not_awaited()


async def test_phone_requires_opt_in_control_permission_and_shared_limits():
    hass, runtime, member, user, registry, _client = scenario("mobile_app")
    source = member.location.evidence.source_entity
    now = datetime.now(UTC)
    with (
        patch(
            "custom_components.homecircle.selection_refresh.er.async_get",
            return_value=registry,
        ),
        patch(
            "custom_components.homecircle.selection_refresh.available_notification_entity",
            return_value="notify.example_phone",
        ),
        patch(
            "custom_components.homecircle.selection_refresh.async_request_quiet_locations",
            new_callable=AsyncMock,
        ) as send,
    ):
        runtime.config["members"][member.id]["auto_request_location"] = False
        assert (
            await async_refresh_selected(hass, runtime, member, user, "example-entry")
        )["status"] == "disabled"
        runtime.config["members"][member.id]["auto_request_location"] = True
        user.permissions.check_entity = lambda *_: False
        assert (
            await async_refresh_selected(hass, runtime, member, user, "example-entry")
        )["status"] == "not_allowed"
        user.permissions.check_entity = lambda *_: True
        runtime.location_request_times[source] = [now - timedelta(seconds=30)]
        assert (
            await async_refresh_selected(hass, runtime, member, user, "example-entry")
        )["status"] == "cooldown"
        runtime.location_request_times[source] = [
            now - timedelta(hours=2, seconds=i) for i in range(50)
        ]
        assert (
            await async_refresh_selected(hass, runtime, member, user, "example-entry")
        )["status"] == "limited"
        send.assert_not_awaited()
        runtime.location_request_times.clear()

        async def request(_hass, _runtime, stamp, **kwargs):
            assert kwargs == {"member_id": member.id, "on_selection": True}
            runtime.last_location_request[source] = stamp

        send.side_effect = request
        assert (
            await async_refresh_selected(hass, runtime, member, user, "example-entry")
        )["status"] == "requested"


async def test_direct_cloud_check_respects_backoff_and_existing_work(hass):
    from custom_components.homecircle.life360_direct import DirectLife360

    client = DirectLife360(hass, {}, lambda _: None)
    client.async_refresh = AsyncMock()
    client._retry_at = datetime.now(UTC) + timedelta(minutes=2)
    assert await client.async_refresh_on_selection() == "cooldown"
    client._retry_at = datetime.now(UTC) - timedelta(minutes=2)
    await client._lock.acquire()
    assert await client.async_refresh_on_selection() == "busy"
    client._lock.release()
    client._auth_blocked = True
    assert await client.async_refresh_on_selection() == "unavailable"
    client.async_refresh.assert_not_awaited()


async def test_external_life360_uses_exact_supported_target_and_persisted_limits():
    hass, runtime, member, user, registry, _client = scenario("life360")
    runtime.location_request_store = SimpleNamespace(async_save=AsyncMock())
    runtime.restored_location_requests = set()
    hass.services.async_call = AsyncMock()
    source = member.location.evidence.source_entity
    with patch(
        "custom_components.homecircle.selection_refresh.er.async_get",
        return_value=registry,
    ):
        assert (
            await async_refresh_selected(hass, runtime, member, user, "example-entry")
        )["status"] == "requested"
        assert (
            await async_refresh_selected(hass, runtime, member, user, "example-entry")
        )["status"] == "cooldown"
    hass.services.async_call.assert_awaited_once_with(
        "life360", "update_location", {"entity_id": [source]}, blocking=True
    )
    saved = runtime.location_request_store.async_save.call_args.args[0]
    assert list(saved["requests"]) == [source]
    assert len(saved["requests"][source]) == 1


async def test_external_life360_requires_control_and_persistence_before_dispatch():
    hass, runtime, member, user, registry, _client = scenario("life360")
    runtime.location_request_store = SimpleNamespace(
        async_save=AsyncMock(side_effect=RuntimeError("save failed"))
    )
    runtime.restored_location_requests = set()
    hass.services.async_call = AsyncMock()
    with patch(
        "custom_components.homecircle.selection_refresh.er.async_get",
        return_value=registry,
    ):
        user.permissions.check_entity = lambda *_: False
        assert (
            await async_refresh_selected(hass, runtime, member, user, "example-entry")
        )["status"] == "not_allowed"
        user.permissions.check_entity = lambda *_: True
        assert (
            await async_refresh_selected(hass, runtime, member, user, "example-entry")
        )["status"] == "unavailable"
    hass.services.async_call.assert_not_awaited()
    assert not runtime.last_location_request
