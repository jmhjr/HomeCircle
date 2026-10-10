"""Offline report behavior using fictional trips and UTC timestamps."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("field_analysis", Path(__file__).parents[1] / "scripts/analyze_field_capture.py")
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


def sample(seconds, state="home", **extra):
    at = f"2026-01-01T12:00:{seconds:02d}+00:00"
    return {"type": "sample", "at": at, "completed_at": at,
            "sources": {name: {"state": state, "sampled_at": at} for name in ("phone", "person", "cloud")},
            "homecircle": {"status": "away" if state == "not_home" else state, **extra}}


def test_trip_delays_are_intervals_with_observation_uncertainty():
    result = report.analyze([sample(0), sample(15, "not_home"), sample(30, "home")],
        departure="2026-01-01T12:00:05+00:00", returned="2026-01-01T12:00:25+00:00", uncertainty=2)
    assert len(result["timing"]) == 8
    assert result["timing"][0]["delay_bounds"] == {"lower_seconds": -7, "upper_seconds": 12}
    assert result["timing"][4]["delay_bounds"] == {"lower_seconds": -12, "upper_seconds": 7}


def test_gap_crossing_never_produces_a_bounded_delay():
    rows = [sample(0), {"type": "gap", "at": "2026-01-01T12:00:10+00:00"}, sample(30, "not_home")]
    result = report.analyze(rows, departure="2026-01-01T12:00:05+00:00")
    assert result["explicit_gap_count"] == 1
    assert result["coverage_breaks"]
    assert all(item["delay_bounds"] is None for item in result["timing"])
    assert "timing is unbounded" in report.render(result)


def test_missing_source_does_not_invent_a_departure():
    rows = [sample(0), sample(15, "unavailable"), sample(30, "not_home")]
    result = report.analyze(rows, departure="2026-01-01T12:00:05+00:00")
    assert all(item["transition"] is None for item in result["timing"])


def test_no_trip_does_not_imply_departure_or_return_acceptance():
    result = report.analyze([sample(0), sample(15)])
    assert not result["transitions"]
    assert "No completed trip" in report.render(result)
    assert "No physical-to-recorded delays" in report.render(result)


def test_conflicts_source_switches_and_requests_are_reported_without_coordinates():
    first = sample(0, issues=[], location_present=True, freshness="fresh", map_origin="active_gps")
    second = sample(15, issues=["tracker_presence_conflict"], location_present=False,
                    freshness="stale", location_request={"status": "waiting"})
    first["sources"]["person"]["active_source"] = "cloud"
    second["sources"]["person"]["active_source"] = "phone"
    second["sources"]["phone"]["coordinates"] = {"latitude": float(0), "longitude": float(0)}
    result = report.analyze([first, second])
    assert {event["kind"] for event in result["signals"]} >= {"active_source", "conflict_flags", "position_withheld", "request_outcome"}
    text = report.render(result)
    assert "tracker_presence_conflict" in text
    assert "waiting" in text
    assert "latitude" not in text
    assert "longitude" not in text


def test_restart_and_long_sampling_holes_are_unbounded():
    rows = [sample(0), {"type": "start", "at": "2026-01-01T12:00:05+00:00"}, sample(15, "not_home")]
    assert all(e["crosses_gap_or_missing"] for e in report.analyze(rows)["transitions"])
    later = sample(15, "not_home")
    later["at"] = later["completed_at"] = "2026-01-01T12:10:00+00:00"
    for state in later["sources"].values():
        state["sampled_at"] = later["at"]
    assert report.analyze([sample(0), later])["coverage_breaks"]


def test_reading_partial_jsonl_warns_and_keeps_valid_records(tmp_path):
    path = tmp_path / "field-states-fixture.jsonl"
    path.write_text('{"type":"sample","at":"2026-01-01T12:00:00+00:00"}\n{"partial"')
    rows, warnings = report.load_records(tmp_path)
    assert len(rows) == 2
    assert rows[-1]["type"] == "gap"
    assert len(warnings) == 1
    assert "partial" not in warnings[0]


def test_naive_or_reversed_observations_are_rejected():
    with pytest.raises(ValueError):
        report.analyze([], departure="2026-01-01T12:00:00")
    with pytest.raises(ValueError):
        report.analyze([], departure="2026-01-01T13:00:00+00:00", returned="2026-01-01T12:00:00+00:00")


def test_report_output_is_owner_only_even_when_replacing_public_file(tmp_path):
    path = tmp_path / "report.md"
    path.write_text("old")
    path.chmod(0o644)
    report.write_private(path, "new")
    assert path.stat().st_mode & 0o777 == 0o600


def test_invalid_uncertainty_is_rejected():
    for value in [float("nan"), float("inf"), -1]:
        with pytest.raises(ValueError):
            report.analyze([], uncertainty=value)
