"""Projected Find My members retain observations and prior household history."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from custom_components.homecircle.activity import ActivityLog


PERSON = "person.example_member"
PHONE = "device_tracker.example_phone"
TAG = "device_tracker.example_tag"
HOME = "zone.example_residence"
NOW = datetime.now(UTC)
EXAMPLE_POINT = (0.0, 0.0)
SAVED = {
    "primary_home": HOME,
    "places": [],
    "people": [PERSON],
    "members": {PERSON: {"trackers": [PHONE], "additional_residences": []}},
}


def projected():
    result = deepcopy(SAVED)
    result["items"] = [TAG]
    result["members"][TAG] = {
        "kind": "item", "trackers": [TAG], "additional_residences": [],
    }
    return result


def member(entity, source):
    return SimpleNamespace(
        id=entity, place=HOME, presence="home", focusable=True,
        location=SimpleNamespace(evidence=SimpleNamespace(
            source_entity=source, freshness="fresh", reported_at=NOW)),
    )


async def test_projected_item_observes_named_place_without_losing_saved_history():
    first = ActivityLog(SAVED)
    first.observe(SimpleNamespace(members=[member(PERSON, PHONE)]), NOW)
    with patch("custom_components.homecircle.activity.dt_util.utcnow", return_value=NOW):
        original = first.payload()
    store = SimpleNamespace(async_load=AsyncMock(return_value=original),
        async_delay_save=Mock(), async_save=AsyncMock())
    expanded = ActivityLog(projected(), store, fingerprint_config=SAVED)
    await expanded.load()
    assert expanded.fingerprint == first.fingerprint
    assert expanded.events[PERSON] == original["events"][PERSON]
    assert expanded.events[TAG] == []
    expanded.observe(SimpleNamespace(members=[member(PERSON, PHONE), member(TAG, TAG)]), NOW)
    assert [event["kind"] for event in expanded.events[TAG]] == [
        "started", "presence", "source", "freshness",
    ]
    assert expanded.arrivals[TAG]["place"] == HOME
    assert expanded.events[TAG][2]["value"] == TAG
    assert expanded.events[PERSON][:len(original["events"][PERSON])] == original["events"][PERSON]


async def test_projected_item_and_original_member_history_survive_next_restart():
    store = SimpleNamespace(async_load=AsyncMock(), async_delay_save=Mock(), async_save=AsyncMock())
    first = ActivityLog(projected(), store, fingerprint_config=SAVED)
    first.observe(SimpleNamespace(members=[member(PERSON, PHONE), member(TAG, TAG)]), NOW)
    with patch("custom_components.homecircle.activity.dt_util.utcnow", return_value=NOW):
        original = first.payload()
    store.async_load.return_value = original
    restored = ActivityLog(projected(), store, fingerprint_config=SAVED)
    await restored.load()
    assert restored.events == original["events"]
    restored.observe(SimpleNamespace(members=[member(PERSON, PHONE), member(TAG, TAG)]),
        NOW + timedelta(seconds=1))
    assert all(len(restored.events[entity]) == 8 for entity in (PERSON, TAG))
    assert restored.arrival(TAG, HOME)["continuity_unconfirmed"] is True


async def test_changed_saved_selection_still_invalidates_prior_projected_history():
    first = ActivityLog(projected(), fingerprint_config=SAVED)
    first.observe(SimpleNamespace(members=[member(PERSON, PHONE), member(TAG, TAG)]), NOW)
    with patch("custom_components.homecircle.activity.dt_util.utcnow", return_value=NOW):
        original = first.payload()
    changed = deepcopy(SAVED)
    changed["members"][PERSON]["trackers"] = ["device_tracker.example_other"]
    store = SimpleNamespace(async_load=AsyncMock(return_value=original))
    restored = ActivityLog(projected(), store, fingerprint_config=changed)
    await restored.load()
    assert restored.fingerprint != first.fingerprint
    assert restored.events == {PERSON: [], TAG: []}
    assert restored.arrivals == {}


async def test_setup_projects_new_item_before_loading_and_observing_activity(hass, hass_storage):
    """Exercise real setup ordering, projection, normalization and HA Store load."""
    from homeassistant.helpers import entity_registry as er
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.homecircle import async_setup_entry
    from custom_components.homecircle.findmy_provider import tracker_unique_id

    config = deepcopy(SAVED)
    config.update({"people_trackers": [], "pets": [], "items": [],
        "findmy_accounts": {"a" * 32: {"items": {"tag": {"name": "Example tag"}}}}})
    registry = er.async_get(hass)
    item = registry.async_get_or_create("device_tracker", "homecircle",
        tracker_unique_id("a" * 32, "tag", {"name": "Example tag"}))
    entry = MockConfigEntry(domain="homecircle", title="HomeCircle", data=config)
    entry.add_to_hass(hass)
    original = ActivityLog(config)
    original.observe(SimpleNamespace(members=[member(PERSON, PHONE)]), NOW)
    with patch("custom_components.homecircle.activity.dt_util.utcnow", return_value=NOW):
        saved = original.payload()
    hass_storage["homecircle.activity." + entry.entry_id] = {
        "version": 1, "minor_version": 1,
        "key": "homecircle.activity." + entry.entry_id, "data": saved,
    }
    hass.states.async_set(HOME, "0", {"latitude": EXAMPLE_POINT[0], "longitude": EXAMPLE_POINT[1], "radius": 100})
    for entity in (PHONE, item.entity_id):
        hass.states.async_set(entity, "home", {"source_type": "gps", "latitude": EXAMPLE_POINT[0],
            "longitude": EXAMPLE_POINT[1], "last_seen": NOW.isoformat(), "in_zones": [HOME]})
    hass.states.async_set(PERSON, "home", {"source": PHONE, "latitude": EXAMPLE_POINT[0], "longitude": EXAMPLE_POINT[1],
        "in_zones": [HOME]})
    with (
        patch("custom_components.homecircle.findmy_migration.recover_pending", new=AsyncMock()),
        patch("custom_components.homecircle.findmy_storage.prune_orphans"),
        patch("custom_components.homecircle.frontend.async_register", new=AsyncMock()),
        patch("custom_components.homecircle.dashboard_setup.async_ensure_dashboard", new=AsyncMock()),
        patch("custom_components.homecircle.CityLookup.load", new=AsyncMock()),
        patch("custom_components.homecircle.connected_providers", return_value=[]),
        patch("custom_components.homecircle.dt_util.utcnow", return_value=NOW),
    ):
        assert await async_setup_entry(hass, entry)
    runtime = entry.runtime_data
    try:
        assert set(runtime.activity.members) == {PERSON, item.entity_id}
        assert runtime.activity.fingerprint == original.fingerprint
        assert runtime.activity.events[PERSON][:len(saved["events"][PERSON])] == saved["events"][PERSON]
        assert [event["kind"] for event in runtime.activity.events[item.entity_id]] == [
            "started", "presence", "source", "freshness",
        ]
        assert runtime.activity.arrivals[item.entity_id]["place"] == HOME
        assert entry.data == config
    finally:
        # Direct setup bypasses the framework that normally runs these callbacks.
        await entry._async_process_on_unload(hass)
        await runtime.activity.close()
        await runtime.city_lookup.close()
