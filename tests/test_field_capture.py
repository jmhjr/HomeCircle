"""Privacy and missing-evidence checks for the offline field recorder."""

import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "field_capture", Path(__file__).parents[1] / "scripts/retain_field_states.py"
)
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


def test_source_projection_drops_coordinates_and_unknown_places():
    result = capture.project_state(
        {"state": "Private address", "last_updated": "2026-01-01T00:00:00Z",
         "attributes": {"latitude": float(44), "longitude": float(-93), "source": "device_tracker.example_phone",
                        "access_token": "secret", "friendly_name": "Private name"}},
        {"phone": "device_tracker.example_phone"},
    )
    assert result["state"] == "other_place"
    assert result["active_source"] == "phone"
    assert result["reported_at"] is None
    assert not any(value in json.dumps(result) for value in ("latitude", "longitude", "secret", "Private"))


def test_snapshot_retains_status_and_evidence_without_location_or_portrait():
    result = capture.project_member({"members": [
        {"id": "person.example_fixture", "name": "Private", "presence": "away", "picture": "/private.jpg",
         "place": "Private address", "location": {"latitude": float(44), "longitude": float(-93),
         "evidence": {"reported_at": None, "freshness": "unknown", "source_label": "Tracker: Fixture"}}}
    ], "counts": {"away": 1}}, "person.example_fixture")
    assert result["status"] == "away"
    assert result["reported_at"] is None
    assert result["map_source"] == "Tracker: Fixture"
    assert not any(value in json.dumps(result) for value in ("latitude", "longitude", "Private", "picture"))


def test_missing_member_is_not_reported_home():
    assert capture.project_member({"members": []}, "person.example_fixture") == {"status": "missing"}
    assert capture.project_state(None, {}) == {"state": "missing"}


def test_coordinates_require_opt_in_and_reject_invalid_points():
    state = {"state": "home", "attributes": {"latitude": float(0), "longitude": float(0)}}
    assert "coordinates" not in capture.project_state(state, {})
    assert capture.project_state(state, {}, True)["coordinates"] == {"latitude": float(0), "longitude": float(0)}
    assert capture.point({"latitude": float("nan"), "longitude": float(0)}) is None
    assert capture.point({"latitude": float(91), "longitude": float(0)}) is None


def test_source_metadata_distinguishes_associations_updates_and_zones():
    result = capture.project_state(
        {"state": "home", "last_changed": "change", "last_updated": "update", "last_reported": "report",
         "attributes": {"source_type": "gps", "tracking_type": "gps", "gps_accuracy": 20,
                        "source": "device_tracker.example_phone", "device_trackers": ["device_tracker.example_phone", "device_tracker.example_other"],
                        "in_zones": ["zone.home", "zone.example_private"], "last_seen": "fix", "driving": False}},
        {"phone": "device_tracker.example_phone"}, zones={"primary_home": "zone.home"},
    )
    assert result["ha_changed_at"] == "change"
    assert result["ha_updated_at"] == "update"
    assert result["ha_reported_at"] == "report"
    assert result["reported_at"] == "fix"
    assert result["configured_trackers"] == ["phone", "other"]
    assert result["zone_membership"] == ["primary_home", "other"]
    assert result["gps_accuracy_m"] == 20
    assert "zone.example_private" not in json.dumps(result)


def test_withheld_position_retains_conflict_and_request_evidence():
    result = capture.project_member({"members": [{"id": "person.example_member", "presence": "home", "location": None,
        "focusable": False, "issues": ["tracker_presence_conflict"],
        "diagnostics": {"active_source": "device_tracker.example_source", "selected_trackers": [{"entity_id": "device_tracker.example_source"}]},
        "location_request": {"enabled": True, "status": "waiting", "requested_at": "request", "private": "secret"}}]},
        "person.example_member", entities={"phone": "device_tracker.example_source"})
    assert result["issues"] == ["tracker_presence_conflict"]
    assert result["location_present"] is False
    assert result["active_source"] == "phone"
    assert result["selected_trackers"] == ["phone"]
    assert result["location_request"]["status"] == "waiting"
    assert "secret" not in json.dumps(result)


def test_supporting_projection_rejects_private_strings_and_nonfinite_values():
    assert capture.project_supporting({"state": "Private address"})["value"] is None
    assert capture.project_supporting({"state": "nan"})["value"] is None
    assert capture.project_supporting({"state": "12"})["value"] == 12
    assert capture.project_supporting({"state": "2026-01-01T00:00:00+00:00"})["value"] == "2026-01-01T00:00:00+00:00"
    assert capture.project_supporting({"state": "2026-01-01T00:00:00"})["value"] is None


def test_explicit_deadline_preserves_original_end_and_rejects_extension():
    from datetime import datetime, timezone
    import pytest
    now = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    assert capture.capture_deadline(now, 48, "2026-01-02T12:00:00+00:00").isoformat() == "2026-01-02T12:00:00+00:00"
    for end in ["2026-01-01T11:00:00+00:00", "2026-01-05T12:00:00+00:00", "2026-01-02T12:00:00"]:
        with pytest.raises(ValueError):
            capture.capture_deadline(now, 48, end)


async def test_missing_tracker_and_failed_snapshot_keep_other_source_evidence(monkeypatch):
    class Context:
        def __init__(self, value): self.value = value
        async def __aenter__(self): return self.value
        async def __aexit__(self, *args): pass
    class Response:
        def __init__(self, status): self.status = status
        def raise_for_status(self): assert self.status == 200
        async def json(self): return {"state": "home", "attributes": {"source_type": "gps"}}
    class Socket:
        def __init__(self): self.messages = iter([{"type": "auth_required"}, {"type": "auth_ok"}, {"success": False}])
        async def receive_json(self): return next(self.messages)
        async def send_json(self, value): pass
    class Session:
        def get(self, url): return Context(Response(404 if url.endswith("missing") else 200))
        def ws_connect(self, url): return Context(Socket())
    monkeypatch.setattr(capture.aiohttp, "ClientSession", lambda **kwargs: Context(Session()))
    result = await capture.capture({"base_url": "http://localhost", "access_token": "test", "member_id": "person.example_member", "entities": {"phone": "device_tracker.example_phone", "cloud": "device_tracker.example_missing"}})
    assert result["sources"]["phone"]["state"] == "home"
    assert result["sources"]["cloud"]["capture_status"] == "not_found"
    assert result["homecircle"]["capture_status"] == "snapshot_failed"
