"""Activity records actual observations and never reconstructs a journey."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from custom_components.homecircle.activity import ActivityLog, MAX_EVENTS

NOW = datetime.now(UTC)
CONFIG = {
    "primary_home": "zone.example_residence",
    "places": [],
    "people": ["person.example_member"],
    "members": {
        "person.example_member": {
            "trackers": ["device_tracker.example_phone"],
            "additional_residences": [],
        }
    },
}
MEMBER = "person.example_member"


def household(
    presence="home", freshness="fresh", source="device_tracker.example_phone"
):
    evidence = SimpleNamespace(
        source_entity=source,
        freshness=freshness,
        reported_at=NOW - timedelta(minutes=2),
    )
    return SimpleNamespace(
        members=[
            SimpleNamespace(
                id=MEMBER,
                presence=presence,
                focusable=True,
                location=SimpleNamespace(evidence=evidence),
            )
        ]
    )


def test_changes_only_and_report_time_separate_from_observation():
    log = ActivityLog(CONFIG)
    log.observe(household(), NOW)
    assert len(log.events[MEMBER]) == 4
    log.observe(household(), NOW + timedelta(seconds=30))
    assert len(log.events[MEMBER]) == 4
    log.observe(household("away", "stale"), NOW + timedelta(minutes=5))
    events = log.events[MEMBER]
    assert [event["kind"] for event in events[-2:]] == ["presence", "freshness"]
    assert events[-1]["reported_at"] != events[-1]["observed_at"]
    assert not any("latitude" in event or "longitude" in event for event in events)


def test_retention_cap_and_source_projection():
    log = ActivityLog(CONFIG)
    for index in range(MAX_EVENTS + 5):
        log.append(MEMBER, "refresh", "cooldown", NOW + timedelta(seconds=index))
    assert len(log.events[MEMBER]) == MAX_EVENTS
    log.append(
        MEMBER, "source", "device_tracker.example_phone", NOW + timedelta(minutes=5)
    )
    with patch(
        "custom_components.homecircle.activity.dt_util.utcnow",
        return_value=NOW + timedelta(minutes=5),
    ):
        result = log.project(MEMBER, lambda _: "Example tracker")
    assert result["events"][0]["value"] == "Example tracker"
    log.prune(NOW + timedelta(days=8))
    assert not log.events[MEMBER]


async def test_reload_keeps_history_but_starts_new_observation_boundary():
    store = SimpleNamespace(
        async_load=AsyncMock(), async_save=AsyncMock(), async_delay_save=Mock()
    )
    first = ActivityLog(CONFIG, store)
    first.observe(household(), NOW)
    store.async_load.return_value = first.payload()
    restored = ActivityLog(CONFIG, store)
    await restored.load()
    count = len(restored.events[MEMBER])
    restored.observe(household("away"), NOW)
    assert restored.events[MEMBER][count]["kind"] == "started"
    assert restored.events[MEMBER][count + 1]["value"] == "away"
    await restored.save()
    assert store.async_save.await_count == 1
    changed = ActivityLog(
        {**CONFIG, "members": {MEMBER: {"trackers": [], "additional_residences": []}}},
        store,
    )
    await changed.load()
    assert not changed.events[MEMBER]


async def test_load_allowlists_fields_members_and_values():
    log = ActivityLog(CONFIG)
    store = SimpleNamespace(
        async_load=AsyncMock(
            return_value={
                "fingerprint": log.fingerprint,
                "events": {
                    MEMBER: [
                        {
                            "kind": "presence",
                            "value": "home",
                            "observed_at": NOW.isoformat(),
                            "secret": "do not project",
                        },
                        {
                            "kind": "source",
                            "value": "device_tracker.example_other",
                            "observed_at": NOW.isoformat(),
                        },
                        {
                            "kind": "presence",
                            "value": "invalid",
                            "observed_at": NOW.isoformat(),
                        },
                        {
                            "kind": "refresh",
                            "value": "requested",
                            "observed_at": "invalid",
                        },
                    ],
                    "person.example_other": [
                        {"kind": "started", "observed_at": NOW.isoformat()}
                    ],
                },
            }
        )
    )
    log.store = store
    await log.load()
    assert log.events == {
        MEMBER: [{"kind": "presence", "value": "home", "observed_at": NOW.isoformat()}]
    }


async def test_failed_load_disables_persistence_without_overwrite():
    store = SimpleNamespace(
        async_load=AsyncMock(side_effect=OSError), async_save=AsyncMock()
    )
    log = ActivityLog(CONFIG, store)
    await log.load()
    log.observe(household(), NOW)
    await log.save()
    store.async_save.assert_not_awaited()
    assert log.store is None


def test_withheld_position_clears_map_source_and_does_not_publish_coordinates():
    log = ActivityLog(CONFIG)
    members = household()
    log.observe(members, NOW)
    members.members[0].focusable = False
    log.observe(members, NOW + timedelta(seconds=1))
    assert log.events[MEMBER][-2]["kind"] == "source"
    assert log.events[MEMBER][-2]["value"] is None
    assert log.events[MEMBER][-1]["value"] == "unavailable"


def test_quiet_retention_cleanup_is_scheduled_without_new_events():
    store = SimpleNamespace(async_delay_save=Mock())
    log = ActivityLog(CONFIG, store)
    log.observe(household(), NOW)
    store.async_delay_save.reset_mock()
    log.observe(household(), NOW + timedelta(days=8))
    assert not log.events[MEMBER]
    store.async_delay_save.assert_called_once()


async def test_close_ignores_late_request_results_and_state_callbacks():
    store = SimpleNamespace(async_save=AsyncMock(), async_delay_save=Mock())
    log = ActivityLog(CONFIG, store)
    log.observe(household(), NOW)
    count = len(log.events[MEMBER])
    await log.close()
    store.async_delay_save.reset_mock()
    log.append(MEMBER, "refresh", "requested", NOW)
    log.observe(household("away"), NOW)
    assert len(log.events[MEMBER]) == count
    store.async_delay_save.assert_not_called()


async def test_freshness_churn_preserves_arrivals_requests_and_reload():
    from custom_components.homecircle.activity import MAX_FRESHNESS_EVENTS

    log = ActivityLog(CONFIG)
    log.append(MEMBER, "presence", "away", NOW)
    log.append(MEMBER, "refresh", "requested", NOW + timedelta(seconds=1))
    log.append(MEMBER, "presence", "home", NOW + timedelta(seconds=2))
    for index in range(200):
        log.append(
            MEMBER,
            "freshness",
            "fresh" if index % 2 else "stale",
            NOW + timedelta(seconds=3 + index),
        )
    assert [e["kind"] for e in log.events[MEMBER][:3]] == [
        "presence",
        "refresh",
        "presence",
    ]
    assert (
        sum(e["kind"] == "freshness" for e in log.events[MEMBER])
        == MAX_FRESHNESS_EVENTS
    )
    with patch(
        "custom_components.homecircle.activity.dt_util.utcnow",
        return_value=NOW + timedelta(minutes=5),
    ):
        saved = log.payload()
        store = SimpleNamespace(async_load=AsyncMock(return_value=saved))
        restored = ActivityLog(CONFIG, store)
        await restored.load()
    assert restored.events == log.events
    restored.prune(NOW + timedelta(days=8))
    assert not restored.events[MEMBER]


def test_total_cap_evicts_freshness_before_significant_events():
    log = ActivityLog(CONFIG)
    log.append(MEMBER, "presence", "away", NOW)
    log.append(MEMBER, "freshness", "stale", NOW)
    for index in range(MAX_EVENTS - 1):
        log.append(MEMBER, "refresh", "requested", NOW + timedelta(seconds=index))
    assert len(log.events[MEMBER]) == MAX_EVENTS
    assert log.events[MEMBER][0]["kind"] == "presence"
    assert not any(e["kind"] == "freshness" for e in log.events[MEMBER])
