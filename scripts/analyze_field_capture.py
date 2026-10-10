"""Offline, private report of sampled tracker transitions; never exact trip timing."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
from zoneinfo import ZoneInfo

STREAMS = ("phone", "person", "cloud", "homecircle")
MISSING = {None, "missing", "unknown", "unavailable"}


def stamp(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None


def presence(value):
    if value == "home":
        return "home"
    if value in {"not_home", "away", "driving", "other_place"}:
        return "away"
    return None


def load_records(directory):
    rows, warnings = [], []
    for path in sorted(Path(directory).glob("field-states-*.jsonl")):
        for number, line in enumerate(path.read_text().splitlines(), 1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                warnings.append(f"Skipped malformed record {path.name}:{number}")
                if rows:
                    rows.append({"type": "gap", "at": rows[-1]["at"], "reason": "malformed_record"})
                continue
            if not isinstance(row, dict) or stamp(row.get("at")) is None:
                warnings.append(f"Skipped record without a valid timestamp {path.name}:{number}")
                if rows:
                    rows.append({"type": "gap", "at": rows[-1]["at"], "reason": "invalid_timestamp"})
                continue
            rows.append(row)
    return sorted(rows, key=lambda r: stamp(r["at"])), warnings


def analyze(records, departure=None, returned=None, uncertainty=60):
    if not math.isfinite(uncertainty) or uncertainty < 0:
        raise ValueError("Observation uncertainty must be finite and nonnegative")
    for value in (departure, returned):
        if value is not None and stamp(value) is None:
            raise ValueError("Physical observation times require an ISO timestamp with timezone")
    if departure and returned and stamp(returned) <= stamp(departure):
        raise ValueError("Return must be after departure")
    result = {"sample_count": 0, "explicit_gap_count": 0, "coverage_breaks": [], "transitions": [], "signals": [], "sample_status_counts": {}, "timing": [], "baselines": []}
    previous = {}
    dirty = True
    last_sample = None
    signals = {}
    counts = {name: Counter() for name in STREAMS}
    for record in records:
        at = stamp(record.get("at"))
        if at is None:
            continue
        kind = record.get("type")
        if kind == "start":
            result["baselines"].append({"at": record["at"], "schema_version": record.get("schema_version", 1), "context": record.get("context", {})})
            dirty = True
            continue
        if kind != "sample":
            if kind == "gap":
                result["explicit_gap_count"] += 1
            dirty = True
            continue
        end = stamp(record.get("completed_at")) or at
        if last_sample and (dirty or (at - last_sample).total_seconds() > 90):
            dirty = True
            result["coverage_breaks"].append({"from": last_sample.isoformat(), "to": end.isoformat(), "reason": "restart/failure or interval longer than 90 seconds"})
        result["sample_count"] += 1
        sources = record.get("sources", {})
        member = record.get("homecircle", {})
        for name in STREAMS:
            data = member if name == "homecircle" else sources.get(name, {})
            value = data.get("status" if name == "homecircle" else "state", "missing")
            counts[name][value] += 1
            observed = stamp(record.get("snapshot_sampled_at")) if name == "homecircle" else stamp(data.get("sampled_at"))
            observed = observed or end
            old = previous.get(name)
            if old and value != old["state"]:
                interrupted = dirty or (at - (last_sample or at)).total_seconds() > 90 or value in MISSING or old["state"] in MISSING or old["interrupted"]
                result["transitions"].append({"stream": name, "from": old["state"], "to": value, "after": old["at"].isoformat(), "by": observed.isoformat(), "crosses_gap_or_missing": interrupted, "presence_change": presence(old["state"]) != presence(value) and presence(value) is not None and presence(old["state"]) is not None})
            previous[name] = {"state": value, "at": observed, "interrupted": value in MISSING}
        values = {
            "active_source": sources.get("person", {}).get("active_source"),
            "freshness": member.get("freshness"),
            "conflict_flags": tuple(sorted(member.get("issues", []))) if "issues" in member else None,
            "map_origin": member.get("map_origin"),
            "position_withheld": (member.get("location_present") is False and any("conflict" in issue for issue in member.get("issues", []))) if "location_present" in member else None,
            "request_outcome": member.get("location_request", {}).get("status"),
        }
        for key, value in values.items():
            if key not in signals or value != signals[key]:
                result["signals"].append({"at": end.isoformat(), "kind": key, "value": value, "after_gap": dirty})
                signals[key] = value
        last_sample = end
        dirty = False
    result["sample_status_counts"] = {k: dict(v) for k, v in counts.items()}
    for label, reference, destination in (("departure", departure, "away"), ("return", returned, "home")):
        if reference is None:
            continue
        physical = stamp(reference)
        for stream in STREAMS:
            matches = [e for e in result["transitions"] if e["stream"] == stream and e["presence_change"] and presence(e["to"]) == destination and (stamp(e["by"]) - physical).total_seconds() >= -uncertainty]
            event = matches[0] if matches else None
            delay = None
            if event and not event["crosses_gap_or_missing"]:
                delay = {"lower_seconds": (stamp(event["after"]) - physical).total_seconds() - uncertainty, "upper_seconds": (stamp(event["by"]) - physical).total_seconds() + uncertainty}
            result["timing"].append({"observation": label, "stream": stream, "physical_at": reference, "uncertainty_seconds": uncertainty, "transition": event, "delay_bounds": delay})
    return result


def render(report, warnings=(), timezone_name="America/Chicago"):
    zone = ZoneInfo(timezone_name)
    def local(value):
        return stamp(value).astimezone(zone).strftime("%b %d %H:%M:%S %Z")
    lines = ["# Private field-test report", "", "Sampled transitions are observation bounds, not exact events or a reconstructed route. Reads are sequential; inspect boundary flips and gaps before interpreting delays. Life360 remains selected, so combined-source success does not prove iPhone-only tracking.", "", f"Successful sample rounds: {report['sample_count']}; explicit gap records: {report['explicit_gap_count']}; coverage breaks: {len(report['coverage_breaks'])}.", "", "## Source state sample counts", "", "These are sample counts, not time spent in each state.", "", "| Source | Recorded states |", "| --- | --- |"]
    for name, counts in report["sample_status_counts"].items():
        lines.append(f"| {name} | {', '.join(f'{k}: {v}' for k, v in counts.items())} |")
    lines += ["", "## Capture baselines", ""]
    for baseline in report["baselines"]:
        context = baseline["context"]
        lines.append(f"- {local(baseline['at'])}: schema {baseline['schema_version']}; integration {context.get('integration_version', 'not recorded')}; card fingerprint {context.get('card_sha256', 'not recorded')}; settings fingerprint {context.get('settings_sha256', 'not recorded')}.")
    lines += ["", "## Presence and state transitions", ""]
    if not report["transitions"]:
        lines.append("No state transitions observed. No completed trip is established by these samples.")
    for e in report["transitions"]:
        lines.append(f"- {e['stream']}: {e['from']} → {e['to']}; after {local(e['after'])}, observed by {local(e['by'])}. " + ("Crosses missing evidence; timing is unbounded." if e["crosses_gap_or_missing"] else "Sample-bound interval."))
    lines += ["", "## Source, conflict, map and request signals", ""]
    for e in report["signals"]:
        lines.append(f"- {local(e['at'])}: {e['kind']} = {json.dumps(e['value'])}" + (" (baseline/after gap)" if e["after_gap"] else ""))
    lines += ["", "## Physical-observation comparison", ""]
    if not report["timing"]:
        lines.append("Physical departure/return times were not supplied. No physical-to-recorded delays calculated.")
    for item in report["timing"]:
        bounds = item["delay_bounds"]
        text = "No matching transition observed." if item["transition"] is None else "Matching transition crosses a gap; no bounded delay calculated." if bounds is None else f"Delay bounds {bounds['lower_seconds']:.1f} to {bounds['upper_seconds']:.1f} seconds, including ±{item['uncertainty_seconds']} seconds of physical-observation uncertainty."
        lines.append(f"- {item['observation']} / {item['stream']} (physical observation {local(item['physical_at'])}): {text}")
    lines += ["", "## Coverage breaks", ""]
    for gap in report["coverage_breaks"]:
        lines.append(f"- {local(gap['from'])} to {local(gap['to'])}: {gap['reason']}. Unobserved; do not infer a path.")
    if warnings:
        lines += ["", "## Input warnings", "", *warnings]
    return "\n".join(lines) + "\n"


def write_private(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--departure", help="Physical time, ISO with timezone")
    parser.add_argument("--return", dest="returned", help="Physical time, ISO with timezone")
    parser.add_argument("--uncertainty-seconds", type=float, default=60)
    args = parser.parse_args()
    rows, warnings = load_records(args.records)
    if not rows:
        parser.error("No valid capture records")
    try:
        report = analyze(rows, args.departure, args.returned, args.uncertainty_seconds)
    except ValueError as error:
        parser.error(str(error))
    write_private(args.output, render(report, warnings))
    write_private(Path(args.output).with_suffix(".json"), json.dumps(report, indent=2) + "\n")
    print(f"Private report written; {report['sample_count']} sample rounds analyzed.")


if __name__ == "__main__":
    main()
