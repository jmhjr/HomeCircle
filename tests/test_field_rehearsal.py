"""Fictional trip through recorder projections, JSONL storage and report CLI."""

from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("rehearsal_capture", ROOT / "scripts/retain_field_states.py")
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


def write_trip(directory):
    directory.mkdir(parents=True, exist_ok=True)
    directory.chmod(0o700)
    path = directory / "field-states-synthetic.jsonl"
    base = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    entities = {"phone": "device_tracker.example_phone", "cloud": "device_tracker.example_cloud", "person": "person.example_member"}
    def at(seconds):
        return (base + timedelta(seconds=seconds)).isoformat()
    capture.save(path, {"type": "start", "at": at(0), "schema_version": 2, "context": {"integration_version": "synthetic-rehearsal"}})
    # Phone leaves first, flips home briefly, then cloud and Person catch up.
    # A later conflict withholds the position; return occurs during a gap.
    stages = [(0, "home", "home", "home", False),
              (15, "not_home", "home", "home", True),
              (30, "home", "home", "home", False),
              (45, "not_home", "not_home", "not_home", False),
              (60, "not_home", "not_home", "not_home", False),
              (75, "home", "not_home", "not_home", True),
              (120, "home", "home", "home", False),
              (135, "home", "home", "home", False)]
    for seconds, phone, cloud, person, conflict in stages:
        if seconds == 120:
            capture.save(path, {"type": "gap", "at": at(90), "reason": "synthetic_connection_failure"})
        sources = {}
        for slot, state in (("phone", phone), ("cloud", cloud), ("person", person)):
            attrs = {"source_type": "gps", "latitude": float(0), "longitude": float(0)}
            if slot == "person":
                attrs["source"] = entities["cloud" if seconds < 60 else "phone"]
            sources[slot] = {**capture.project_state({"state": state, "attributes": attrs}, entities, True), "sampled_at": at(seconds), "capture_status": "ok"}
        location = None if conflict else {"latitude": float(0), "longitude": float(0), "origin": "active_gps", "evidence": {"freshness": "fresh", "source_label": "Tracker: Synthetic", "card_source_label": "Tracker: Home Assistant"}}
        member = {"id": entities["person"], "presence": "home" if person == "home" else "away", "location": location,
                  "issues": ["tracker_presence_conflict"] if conflict else [], "location_request": {"enabled": False, "status": "disabled"}}
        capture.save(path, {"type": "sample", "at": at(seconds), "completed_at": at(seconds), "snapshot_sampled_at": at(seconds),
                            "sources": sources, "homecircle": capture.project_member({"members": [member]}, entities["person"], True, entities)})
    capture.save(path, {"type": "end", "at": at(140), "reason": "synthetic_complete"})
    return path


def test_recorded_trip_cli_preserves_flips_conflicts_and_unbounded_return(tmp_path):
    records = write_trip(tmp_path / "records")
    output = tmp_path / "synthetic-trip.md"
    subprocess.run([sys.executable, str(ROOT / "scripts/analyze_field_capture.py"), "--records", str(records.parent),
                    "--output", str(output), "--departure", "2026-01-01T12:00:10+00:00", "--return", "2026-01-01T12:01:40+00:00",
                    "--uncertainty-seconds", "2"], check=True, capture_output=True, text=True)
    report = json.loads(output.with_suffix(".json").read_text())
    assert report["sample_count"] == 8
    assert report["explicit_gap_count"] == 1
    assert len(report["coverage_breaks"]) == 1
    phone = [e for e in report["transitions"] if e["stream"] == "phone"]
    assert [e["to"] for e in phone] == ["not_home", "home", "not_home", "home"]
    departures = [e for e in report["timing"] if e["observation"] == "departure"]
    assert departures[0]["delay_bounds"] == {"lower_seconds": -12, "upper_seconds": 7}
    assert departures[1]["delay_bounds"] == {"lower_seconds": 18, "upper_seconds": 37}
    returns = [e for e in report["timing"] if e["observation"] == "return"]
    assert returns[0]["transition"] is None  # Phone already home before the physical return.
    assert all(e["transition"]["crosses_gap_or_missing"] and e["delay_bounds"] is None for e in returns[1:])
    assert any(e["kind"] == "position_withheld" and e["value"] is True for e in report["signals"])
    assert any(e["kind"] == "active_source" and e["value"] == "phone" for e in report["signals"])
    text = output.read_text()
    assert "tracker_presence_conflict" in text
    assert "no bounded delay calculated" in text
    assert "latitude" not in text and "longitude" not in text
    assert "coordinates" not in json.dumps(report)
    for path in (records, output, output.with_suffix(".json")):
        assert path.stat().st_mode & 0o777 == 0o600
