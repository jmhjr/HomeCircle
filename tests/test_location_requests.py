"""Quiet Mobile App requests must stay opt-in and bounded."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from custom_components.homecircle.location_requests import (
    MAX_REQUESTS,
    available_notification_entity,
    async_request_quiet_locations,
    request_status,
)


async def test_quiet_mobile_tracker_request_is_bounded():
    start = datetime(2026, 1, 1, 8, 0, tzinfo=UTC)
    tracker_id = "device_tracker.example_phone"
    notify_id = "notify.example_phone"
    member_id = "person.example_member"
    member = SimpleNamespace(
        id=member_id,
        location=SimpleNamespace(evidence=SimpleNamespace(source_entity=tracker_id)),
    )
    state = SimpleNamespace(state="not_home", last_updated=start, last_reported=start)
    runtime = SimpleNamespace(
        household=SimpleNamespace(members=[member]),
        config={
            "members": {
                member_id: {"trackers": [tracker_id], "auto_request_location": True}
            }
        },
        states={tracker_id: state},
        last_location_request={},
        location_request_times={},
        restored_location_requests=set(),
    )
    registry = SimpleNamespace(
        async_get=lambda entity_id: (
            SimpleNamespace(platform="mobile_app", device_id="phone-device")
            if entity_id == tracker_id
            else None
        ),
        entities={
            notify_id: SimpleNamespace(
                entity_id=notify_id,
                device_id="phone-device",
                domain="notify",
                platform="mobile_app",
                disabled=False,
            )
        },
    )
    calls = []
    saved = []

    async def save(value):
        saved.append(value)

    async def call(domain, service, data, blocking):
        calls.append((domain, service, data, blocking))

    hass = SimpleNamespace(
        states=SimpleNamespace(
            get=lambda entity_id: (
                SimpleNamespace(state="ok") if entity_id == notify_id else None
            )
        ),
        services=SimpleNamespace(
            has_service=lambda domain, service: True,
            async_call=call,
        ),
    )
    runtime.location_request_store = SimpleNamespace(async_save=save)
    runtime.location_request_failures = set()
    runtime.activity = SimpleNamespace(append=Mock())
    assert (
        request_status(runtime, member, start + timedelta(minutes=14), registry)[
            "status"
        ]
        == "quiet_pending"
    )
    with patch(
        "custom_components.homecircle.location_requests.er.async_get",
        return_value=registry,
    ):
        await async_request_quiet_locations(
            hass, runtime, start + timedelta(minutes=14)
        )
        assert not calls
        await async_request_quiet_locations(
            hass, runtime, start + timedelta(minutes=16)
        )
        assert len(calls) == 1
        assert calls[0][2] == {
            "entity_id": notify_id,
            "message": "request_location_update",
        }
        assert (
            request_status(runtime, member, start + timedelta(minutes=32), registry)[
                "status"
            ]
            == "no_response"
        )
        await async_request_quiet_locations(
            hass, runtime, start + timedelta(minutes=16, seconds=30)
        )
        assert len(calls) == 1
        await async_request_quiet_locations(
            hass, runtime, start + timedelta(minutes=77)
        )
        assert len(calls) == 2
        assert len(saved) == 2
        runtime.location_request_times[tracker_id] = [
            start + timedelta(minutes=16)
        ] * MAX_REQUESTS
        await async_request_quiet_locations(hass, runtime, start + timedelta(hours=4))
        assert len(calls) == 2
        assert runtime.activity.append.call_count == 2
        assert all(
            call.args[1:3] == ("automatic_refresh", "requested")
            for call in runtime.activity.append.call_args_list
        )
        limited = request_status(runtime, member, start + timedelta(hours=4), registry)
        assert (
            limited["next_request_at"]
            == (start + timedelta(minutes=16) + timedelta(days=1)).isoformat()
        )

    assert (
        request_status(runtime, member, start + timedelta(minutes=93), registry)[
            "status"
        ]
        == "no_response"
    )
    state.last_reported = start + timedelta(minutes=94)
    assert (
        request_status(runtime, member, start + timedelta(minutes=95), registry)[
            "status"
        ]
        == "tracker_responded"
    )
    member.location.evidence.source_entity = "device_tracker.example_other"
    assert (
        request_status(runtime, member, start + timedelta(minutes=95), registry)[
            "status"
        ]
        == "not_selected"
    )


async def test_quiet_request_requires_opt_in_and_mobile_app_device():
    start = datetime(2026, 1, 1, 8, 0, tzinfo=UTC)
    tracker_id = "device_tracker.example_phone"
    member_id = "person.example_member"
    member = SimpleNamespace(
        id=member_id,
        location=SimpleNamespace(evidence=SimpleNamespace(source_entity=tracker_id)),
    )
    runtime = SimpleNamespace(
        household=SimpleNamespace(members=[member]),
        config={"members": {member_id: {"trackers": [tracker_id]}}},
        states={tracker_id: SimpleNamespace(state="not_home", last_updated=start)},
        last_location_request={},
        location_request_times={},
        location_request_failures=set(),
        restored_location_requests=set(),
        location_request_store=SimpleNamespace(),
    )
    calls = []

    async def call(*args, **kwargs):
        calls.append((args, kwargs))

    hass = SimpleNamespace(
        services=SimpleNamespace(
            has_service=lambda domain, service: True, async_call=call
        )
    )
    registry = SimpleNamespace(
        async_get=lambda entity_id: SimpleNamespace(
            platform="life360", device_id="other"
        ),
        entities={},
    )
    with patch(
        "custom_components.homecircle.location_requests.er.async_get",
        return_value=registry,
    ):
        await async_request_quiet_locations(hass, runtime, start + timedelta(hours=1))
        runtime.config["members"][member_id]["auto_request_location"] = True
        await async_request_quiet_locations(hass, runtime, start + timedelta(hours=1))
    assert not calls


async def test_unavailable_notify_and_failed_save_do_not_send():
    now = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    tracker_id = "device_tracker.example_phone"
    notify_id = "notify.example_phone"
    member_id = "person.example_member"
    member = SimpleNamespace(
        id=member_id,
        location=SimpleNamespace(evidence=SimpleNamespace(source_entity=tracker_id)),
    )
    registry = SimpleNamespace(
        async_get=lambda entity_id: (
            SimpleNamespace(platform="mobile_app", device_id="phone")
            if entity_id == tracker_id
            else None
        ),
        entities={
            notify_id: SimpleNamespace(
                entity_id=notify_id,
                device_id="phone",
                domain="notify",
                platform="mobile_app",
                disabled=False,
            )
        },
    )
    notify_state = SimpleNamespace(state="unavailable")
    calls = []

    async def call(*args, **kwargs):
        calls.append((args, kwargs))

    async def failed_save(value):
        raise OSError("storage unavailable")

    hass = SimpleNamespace(
        states=SimpleNamespace(get=lambda entity_id: notify_state),
        services=SimpleNamespace(has_service=lambda *args: True, async_call=call),
    )
    runtime = SimpleNamespace(
        household=SimpleNamespace(members=[member]),
        config={
            "members": {
                member_id: {"trackers": [tracker_id], "auto_request_location": True}
            }
        },
        states={
            tracker_id: SimpleNamespace(
                state="not_home",
                last_updated=now - timedelta(hours=1),
                last_reported=now - timedelta(hours=1),
            )
        },
        location_request_store=SimpleNamespace(async_save=failed_save),
        location_request_times={},
        last_location_request={},
        location_request_failures=set(),
        restored_location_requests=set(),
    )
    assert available_notification_entity(hass, registry, tracker_id) is None
    assert (
        request_status(runtime, member, now, registry, notify_available=False)["status"]
        == "unavailable"
    )
    with patch(
        "custom_components.homecircle.location_requests.er.async_get",
        return_value=registry,
    ):
        await async_request_quiet_locations(hass, runtime, now)
        assert not calls
        notify_state.state = "unknown"
        assert available_notification_entity(hass, registry, tracker_id) == notify_id
        await async_request_quiet_locations(hass, runtime, now)
    assert not calls
    assert runtime.location_request_times[tracker_id] == []
    assert tracker_id not in runtime.last_location_request


def test_restored_request_does_not_claim_startup_tracker_report():
    now = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    tracker_id = "device_tracker.example_phone"
    member_id = "person.example_member"
    member = SimpleNamespace(
        id=member_id,
        location=SimpleNamespace(evidence=SimpleNamespace(source_entity=tracker_id)),
    )
    registry = SimpleNamespace(
        async_get=lambda entity_id: (
            SimpleNamespace(platform="mobile_app", device_id="phone")
            if entity_id == tracker_id
            else None
        ),
        entities={
            "notify.example_phone": SimpleNamespace(
                entity_id="notify.example_phone",
                device_id="phone",
                domain="notify",
                platform="mobile_app",
                disabled=False,
            )
        },
    )
    runtime = SimpleNamespace(
        config={
            "members": {
                member_id: {"trackers": [tracker_id], "auto_request_location": True}
            }
        },
        states={tracker_id: SimpleNamespace(last_updated=now, last_reported=now)},
        location_request_store=SimpleNamespace(),
        last_location_request={tracker_id: now - timedelta(hours=1)},
        location_request_times={tracker_id: [now - timedelta(hours=1)]},
        location_request_failures=set(),
        restored_location_requests={tracker_id},
    )
    assert (
        request_status(runtime, member, now, registry)["status"]
        == "response_unverified"
    )


def request_fixture():
    from copy import deepcopy

    tracker = "device_tracker.example_phone"
    member_id = "person.example_member"
    notify = "notify.example_phone"
    now = datetime(2026, 1, 1, 12, tzinfo=UTC)
    member = SimpleNamespace(
        id=member_id,
        location=SimpleNamespace(
            evidence=SimpleNamespace(
                source_entity=tracker, reported_at=now - timedelta(hours=2)
            )
        ),
    )
    registry = SimpleNamespace(
        async_get=lambda entity: (
            SimpleNamespace(platform="mobile_app", device_id="example-device")
            if entity == tracker
            else None
        ),
        entities={
            notify: SimpleNamespace(
                entity_id=notify,
                device_id="example-device",
                domain="notify",
                platform="mobile_app",
                disabled=False,
            )
        },
    )
    saved, sent = [], []

    async def save(data):
        saved.append(deepcopy(data))

    async def send(*args, **kwargs):
        sent.append(kwargs.get("data", args[2] if len(args) > 2 else None))

    runtime = SimpleNamespace(
        household=SimpleNamespace(members=[member]),
        config={
            "members": {
                member_id: {"trackers": [tracker], "auto_request_location": True}
            }
        },
        states={
            tracker: SimpleNamespace(
                state="home",
                last_updated=now - timedelta(hours=2),
                last_reported=now - timedelta(hours=2),
            )
        },
        location_request_store=SimpleNamespace(async_save=save),
        location_request_times={},
        last_location_request={},
        restored_location_requests=set(),
        location_request_failures=set(),
    )
    hass = SimpleNamespace(
        states=SimpleNamespace(
            get=lambda entity: (
                SimpleNamespace(state="unknown") if entity == notify else None
            )
        ),
        services=SimpleNamespace(has_service=lambda *args: True, async_call=send),
    )
    return now, tracker, member, registry, runtime, hass, saved, sent


async def test_unchanged_state_heartbeat_prevents_unnecessary_request():
    now, tracker, _, registry, runtime, hass, _, sent = request_fixture()
    runtime.states[tracker].last_reported = now - timedelta(minutes=1)
    with patch(
        "custom_components.homecircle.location_requests.er.async_get",
        return_value=registry,
    ):
        await async_request_quiet_locations(hass, runtime, now)
    assert sent == []


async def test_failed_dispatch_still_counts_against_persisted_daily_limit():
    now, tracker, member, registry, runtime, hass, saved, sent = request_fixture()

    async def failed_send(*args, **kwargs):
        sent.append("attempt")
        raise RuntimeError("synthetic failure")

    runtime.location_request_times[tracker] = [now - timedelta(hours=2)] * (
        MAX_REQUESTS - 1
    )
    hass.services.async_call = failed_send
    with patch(
        "custom_components.homecircle.location_requests.er.async_get",
        return_value=registry,
    ):
        await async_request_quiet_locations(hass, runtime, now)
        await async_request_quiet_locations(hass, runtime, now + timedelta(hours=1))
        await async_request_quiet_locations(hass, runtime, now + timedelta(hours=2))
    assert len(sent) == 1
    assert len(saved[-1]["requests"][tracker]) == MAX_REQUESTS
    assert (
        request_status(runtime, member, now + timedelta(hours=2), registry)["status"]
        == "send_failed"
    )


async def test_persisted_cap_survives_restored_runtime_and_rolls_off_at_24_hours():
    now, tracker, _, registry, runtime, hass, saved, sent = request_fixture()
    with patch(
        "custom_components.homecircle.location_requests.er.async_get",
        return_value=registry,
    ):
        await async_request_quiet_locations(hass, runtime, now)
        await async_request_quiet_locations(hass, runtime, now + timedelta(hours=1))
    _, _, member, _, restored, _, _, _ = request_fixture()
    times = [datetime.fromisoformat(saved[-1]["requests"][tracker][0])] * MAX_REQUESTS
    restored.location_request_times[tracker] = times
    restored.last_location_request[tracker] = max(times)
    restored.restored_location_requests.add(tracker)
    with patch(
        "custom_components.homecircle.location_requests.er.async_get",
        return_value=registry,
    ):
        await async_request_quiet_locations(
            hass, restored, now + timedelta(hours=23, minutes=59)
        )
        assert len(sent) == 2
        assert (
            request_status(restored, member, now + timedelta(hours=23), registry)[
                "status"
            ]
            == "response_unverified"
        )
        await async_request_quiet_locations(hass, restored, now + timedelta(hours=24))
        assert len(sent) == 3
        assert len(restored.location_request_times[tracker]) == 1


async def test_later_ha_report_is_not_proof_of_a_new_gps_fix():
    now, tracker, member, registry, runtime, hass, _, _ = request_fixture()
    with patch(
        "custom_components.homecircle.location_requests.er.async_get",
        return_value=registry,
    ):
        await async_request_quiet_locations(hass, runtime, now)
    assert (
        request_status(runtime, member, now + timedelta(seconds=1), registry)["status"]
        == "waiting"
    )
    assert (
        request_status(runtime, member, now + timedelta(minutes=15), registry)["status"]
        == "no_response"
    )
    runtime.states[tracker].last_reported = now + timedelta(minutes=16)
    assert (
        request_status(runtime, member, now + timedelta(minutes=17), registry)["status"]
        == "tracker_responded"
    )
    assert member.location.evidence.reported_at == now - timedelta(hours=2)


async def test_card_selection_targets_one_phone_and_retains_persisted_caps():
    from unittest.mock import AsyncMock

    source = "device_tracker.example_phone"
    other = "device_tracker.example_other"
    now = datetime(2026, 1, 1, 8, 0, tzinfo=UTC)
    members = [
        SimpleNamespace(
            id=member_id,
            location=SimpleNamespace(evidence=SimpleNamespace(source_entity=tracker)),
        )
        for member_id, tracker in [
            ("person.example_member", source),
            ("person.example_other", other),
        ]
    ]
    store = SimpleNamespace(async_save=AsyncMock())
    runtime = SimpleNamespace(
        household=SimpleNamespace(members=members),
        config={
            "members": {
                member.id: {
                    "trackers": [member.location.evidence.source_entity],
                    "auto_request_location": True,
                }
                for member in members
            }
        },
        states={
            tracker: SimpleNamespace(state="home", last_updated=now, last_reported=now)
            for tracker in (source, other)
        },
        location_request_store=store,
        last_location_request={},
        location_request_times={},
        location_request_failures=set(),
        restored_location_requests=set(),
    )
    registry = SimpleNamespace(
        async_get=lambda entity_id: SimpleNamespace(
            platform="mobile_app", device_id=entity_id
        ),
        entities={
            f"notify.example_{index}": SimpleNamespace(
                entity_id=f"notify.example_{index}",
                device_id=tracker,
                domain="notify",
                platform="mobile_app",
                disabled=False,
            )
            for index, tracker in enumerate((source, other))
        },
    )
    calls = []

    async def send(*args, **kwargs):
        assert store.async_save.await_count == 1
        calls.append(args)

    hass = SimpleNamespace(
        services=SimpleNamespace(has_service=lambda *_: True, async_call=send),
        states=SimpleNamespace(get=lambda _: SimpleNamespace(state="unknown")),
    )
    with patch(
        "custom_components.homecircle.location_requests.er.async_get",
        return_value=registry,
    ):
        await async_request_quiet_locations(
            hass,
            runtime,
            now + timedelta(minutes=6),
            member_id=members[0].id,
            on_selection=True,
        )
        await async_request_quiet_locations(
            hass,
            runtime,
            now + timedelta(minutes=6, seconds=59),
            member_id=members[0].id,
            on_selection=True,
        )
    assert len(calls) == 1
    assert calls[0][2] == {
        "entity_id": "notify.example_0",
        "message": "request_location_update",
    }
    assert other not in runtime.last_location_request
    assert runtime.location_request_times[source] == [now + timedelta(minutes=6)]


async def test_fifty_attempt_cap_and_one_minute_cooldown_exact_boundaries():
    from custom_components.homecircle.location_requests import async_reserve_request

    now, tracker, _, _, runtime, _, saved, _ = request_fixture()
    assert await async_reserve_request(runtime, tracker, now) == "reserved"
    assert (
        await async_reserve_request(runtime, tracker, now + timedelta(seconds=59))
        == "cooldown"
    )
    for i in range(1, 50):
        assert (
            await async_reserve_request(runtime, tracker, now + timedelta(minutes=i))
            == "reserved"
        )
    assert len(saved[-1]["requests"][tracker]) == 50
    assert (
        await async_reserve_request(runtime, tracker, now + timedelta(minutes=50))
        == "limited"
    )
    assert (
        await async_reserve_request(runtime, tracker, now + timedelta(days=1))
        == "reserved"
    )
    assert len(saved[-1]["requests"][tracker]) == 50


async def test_silent_phone_automatic_backoff_persists_and_manual_request_survives():
    from custom_components.homecircle.location_requests import (
        restore_automatic_requests,
    )

    now, tracker, member, registry, runtime, hass, saved, sent = request_fixture()
    with patch(
        "custom_components.homecircle.location_requests.er.async_get",
        return_value=registry,
    ):
        for seconds in range(0, 90 * 60 + 1, 30):
            await async_request_quiet_locations(
                hass, runtime, now + timedelta(seconds=seconds)
            )
        assert len(sent) == 3
        assert runtime.location_request_times[tracker] == [
            now,
            now + timedelta(minutes=15),
            now + timedelta(minutes=30),
        ]
        assert len(saved[-1]["requests"][tracker]) == 3
        _, _, _, _, restored, _, _, _ = request_fixture()
        restored.automatic_location_requests = restore_automatic_requests(
            saved[-1]["automatic"]
        )
        # The pause must survive even after the rolling request budget expires.
        await async_request_quiet_locations(hass, restored, now + timedelta(days=2))
        assert len(sent) == 3
        await async_request_quiet_locations(
            hass,
            runtime,
            now + timedelta(minutes=90),
            member_id=member.id,
            on_selection=True,
        )
        assert len(sent) == 4
        # A new HA tracker report permits automatic attempts again after 15 quiet minutes.
        runtime.states[tracker].last_reported = now + timedelta(minutes=91)
        await async_request_quiet_locations(hass, runtime, now + timedelta(minutes=106))
        assert len(sent) == 5
        assert runtime.automatic_location_requests[tracker]["attempts"] == 1


async def test_automatic_backoff_is_not_committed_when_request_storage_fails():
    now, tracker, _, registry, runtime, hass, _, sent = request_fixture()

    async def fail(data):
        raise OSError("synthetic storage failure")

    runtime.location_request_store.async_save = fail
    with patch(
        "custom_components.homecircle.location_requests.er.async_get",
        return_value=registry,
    ):
        await async_request_quiet_locations(hass, runtime, now)
    assert sent == []
    assert runtime.automatic_location_requests == {}


async def test_real_entry_reload_restores_automatic_pause(hass, household):
    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.homecircle.location_requests import async_reserve_requests

    config = {
        **household,
        "members": {
            "person.example_member": {
                "trackers": ["device_tracker.example_phone"],
                "additional_residences": [],
            },
            "person.example_second": {
                "trackers": ["device_tracker.example_router"],
                "additional_residences": [],
            },
        },
    }
    entry = MockConfigEntry(
        domain="homecircle", title="HomeCircle", data=config, unique_id="homecircle"
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    runtime = entry.runtime_data
    now = dt_util.utcnow()
    tracker = "device_tracker.example_phone"
    for index in range(3):
        assert (
            await async_reserve_requests(
                runtime,
                [tracker],
                now + timedelta(minutes=15 * index),
                automatic_reported_at=now - timedelta(hours=1),
            )
            == "reserved"
        )
    assert await hass.config_entries.async_reload(entry.entry_id)
    restored = entry.runtime_data
    assert restored is not runtime
    assert restored.automatic_location_requests[tracker]["attempts"] == 3
    assert (
        await async_reserve_requests(
            restored,
            [tracker],
            now + timedelta(days=2),
            automatic_reported_at=now - timedelta(hours=1),
        )
        == "paused"
    )
