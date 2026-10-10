"""Bounded, read-only HA/HomeCircle field capture; coordinates are opt-in.

Run with --config pointing to a private JSON file containing base_url,
access_token, member_id, and entities (a mapping of anonymous slots to IDs).
Requires aiohttp. This samples current states; it is not an event history.
"""

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import time

import aiohttp


def category(value):
    allowed = {"home", "not_home", "away", "driving", "unknown", "unavailable"}
    return value if value in allowed else "other_place"


def point(attrs):
    values = [attrs.get("latitude"), attrs.get("longitude")]
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in values):
        return None
    if not -90 <= values[0] <= 90 or not -180 <= values[1] <= 180:
        return None
    return {"latitude": values[0], "longitude": values[1]}


def finite(value, minimum=None):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and (minimum is None or value >= minimum) else None


def slot(entity_id, entities):
    return next((name for name, entity in entities.items() if entity == entity_id), "other" if entity_id else None)


def project_state(state, entities, include_coordinates=False, zones=None):
    if not isinstance(state, dict):
        return {"state": "missing"}
    attrs = state.get("attributes", {})
    return {
        **({"coordinates": point(attrs)} if include_coordinates else {}),
        "state": category(state.get("state")),
        "active_source": next(
            (slot for slot, entity in entities.items() if entity == attrs.get("source")),
            "other" if attrs.get("source") else None,
        ),
        "ha_changed_at": state.get("last_changed"),
        "ha_updated_at": state.get("last_updated"),
        "ha_reported_at": state.get("last_reported"),
        "source_type": attrs.get("source_type") if attrs.get("source_type") in {"gps", "router", "bluetooth", "bluetooth_le"} else None,
        "tracking_type": attrs.get("tracking_type") if attrs.get("tracking_type") in {"gps", "connection"} else None,
        "gps_accuracy_m": finite(attrs.get("gps_accuracy"), 0),
        "battery_percent": finite(attrs.get("battery_level"), 0),
        "driving": attrs.get("driving") if isinstance(attrs.get("driving"), bool) else None,
        "speed_raw": finite(attrs.get("speed"), 0),
        "zone_membership": [slot(entity, zones or {}) for entity in attrs.get("in_zones", []) if isinstance(entity, str)] if isinstance(attrs.get("in_zones"), (list, tuple)) else None,
        "configured_trackers": [slot(entity, entities) for entity in attrs.get("device_trackers", []) if isinstance(entity, str)] if isinstance(attrs.get("device_trackers"), (list, tuple)) else None,
        "reported_at": attrs.get("last_seen")
        if isinstance(attrs.get("last_seen"), (str, int, float)) else None,
    }


def project_member(snapshot, member_id, include_coordinates=False, entities=None):
    member = next((m for m in snapshot.get("members", []) if m.get("id") == member_id), None)
    if member is None:
        return {"status": "missing"}
    evidence = (member.get("location") or {}).get("evidence") or {}
    diagnostics = member.get("diagnostics") or {}
    request = member.get("location_request") or {}
    selection_refresh = member.get("selection_refresh") or {}
    return {
        "issues": [issue for issue in member.get("issues", []) if isinstance(issue, str)],
        "location_present": member.get("location") is not None,
        "map_origin": (member.get("location") or {}).get("origin"),
        "report_status": evidence.get("report_status"),
        "card_source": evidence.get("card_source_label"),
        "active_source": slot(diagnostics.get("active_source"), entities or {}),
        "selected_trackers": [slot(t.get("entity_id"), entities or {}) for t in diagnostics.get("selected_trackers", [])],
        "driving_status": member.get("driving", {}).get("status"),
        "battery_percent": finite(member.get("battery"), 0),
        "charging": member.get("charging"),
        "speed": member.get("speed"),
        "selection_refresh": {key: selection_refresh.get(key) for key in ("status", "checked_at", "trigger")},
        "location_request": {key: request.get(key) for key in ("enabled", "status", "requested_at", "next_request_at")},
        **({"coordinates": point(member.get("location") or {})} if include_coordinates else {}),
        "status": category(member.get("presence")),
        "primary_home": member.get("primary_home"),
        "focusable": member.get("focusable"),
        "map_visible": member.get("map_visible"),
        "reported_at": evidence.get("reported_at"),
        "observed_at": evidence.get("observed_at"),
        "freshness": evidence.get("freshness"),
        "map_source": evidence.get("source_label"),
        "driving": member.get("driving", {}).get("value"),
        "counts": snapshot.get("counts"),
    }



def project_supporting(state):
    raw = state.get("state")
    value = raw if raw in {"on", "off", "unknown", "unavailable"} else None
    if value is None:
        try:
            value = finite(float(raw))
        except (TypeError, ValueError):
            try:
                parsed = datetime.fromisoformat(raw)
                value = parsed.isoformat() if parsed.tzinfo else None
            except (TypeError, ValueError):
                pass
    return {"value": value, "ha_updated_at": state.get("last_updated"), "ha_changed_at": state.get("last_changed")}


def save(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a") as stream:
        stream.write(json.dumps(value, separators=(",", ":")) + "\n")


async def capture(config):
    base = config["base_url"].rstrip("/")
    headers = {"Authorization": "Bearer " + config["access_token"]}
    async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as session:
        states = {}
        for slot, entity in config["entities"].items():
            try:
                async with session.get(base + "/api/states/" + entity) as response:
                    if response.status == 404:
                        states[slot] = {"state": "missing", "capture_status": "not_found"}
                    else:
                        response.raise_for_status()
                        states[slot] = project_state(await response.json(), config["entities"], config.get("include_coordinates", False), config.get("zones"))
                        states[slot]["capture_status"] = "ok"
            except (aiohttp.ClientError, asyncio.TimeoutError):
                states[slot] = {"state": "missing", "capture_status": "read_failed"}
            states[slot]["sampled_at"] = datetime.now(timezone.utc).isoformat()
        supporting = {}
        for name, entity in config.get("supporting", {}).items():
            try:
                async with session.get(base + "/api/states/" + entity) as response:
                    response.raise_for_status()
                    supporting[name] = project_supporting(await response.json())
            except (aiohttp.ClientError, asyncio.TimeoutError):
                supporting[name] = {"capture_status": "read_failed"}
        zones = {}
        for name, entity in config.get("zones", {}).items():
            try:
                async with session.get(base + "/api/states/" + entity) as response:
                    response.raise_for_status()
                    raw = await response.json()
                    attrs = raw.get("attributes", {})
                    zones[name] = {"available": raw.get("state") not in {"unknown", "unavailable"}, "radius_m": finite(attrs.get("radius"), 0), "passive": attrs.get("passive") is True, "updated_at": raw.get("last_updated"), **({"coordinates": point(attrs)} if config.get("include_coordinates") else {})}
            except (aiohttp.ClientError, asyncio.TimeoutError):
                zones[name] = {"available": False, "capture_status": "read_failed"}
        async with session.ws_connect(base + "/api/websocket") as ws:
            if (await ws.receive_json())["type"] != "auth_required":
                raise RuntimeError("unexpected_auth")
            await ws.send_json({"type": "auth", "access_token": config["access_token"]})
            if (await ws.receive_json())["type"] != "auth_ok":
                raise RuntimeError("authentication_failed")
            await ws.send_json({"id": 1, "type": "homecircle/snapshot"})
            result = await ws.receive_json()
            if not result.get("success"):
                return {"sources": states, "supporting": supporting, "zones": zones, "homecircle": {"status": "missing", "capture_status": "snapshot_failed"}}
            return {"sources": states, "supporting": supporting, "zones": zones, "snapshot_sampled_at": datetime.now(timezone.utc).isoformat(), "homecircle": project_member(result["result"], config["member_id"], config.get("include_coordinates", False), config["entities"])}



def capture_deadline(now, hours, ends_at=None):
    deadline = datetime.fromisoformat(ends_at) if ends_at else now + timedelta(hours=hours)
    if deadline.tzinfo is None or not 0 < (deadline - now).total_seconds() <= 48 * 3600:
        raise ValueError("End time must be timezone-aware and within the next 48 hours")
    return deadline


async def run(args):
    config_path = Path(args.config)
    if config_path.stat().st_mode & 0o077:
        raise SystemExit("Configuration must be private: chmod 600 the config file")
    config = json.loads(config_path.read_text())
    if not config.get("access_token"):
        raise SystemExit("Add an existing HA access token to the private configuration first")
    if not 1 <= len(config["entities"]) <= 6:
        raise SystemExit("Expected 1-6 explicitly selected entities")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    output.chmod(0o700)
    # Retain only this tool's files; never delete unrelated evidence.
    cutoff = time.time() - 7 * 86400
    for path in output.glob("field-states-*.jsonl"):
        if path.is_file() and not path.is_symlink() and path.stat().st_mtime < cutoff:
            path.unlink()
    now = datetime.now(timezone.utc)
    deadline = capture_deadline(now, args.hours, args.ends_at)
    path = output / ("field-states-" + now.strftime("%Y%m%dT%H%M%S%fZ") + ".jsonl")
    save(path, {"type": "start", "schema_version": 2, "at": now.isoformat(), "context": config.get("capture_context", {}), "ends_at": deadline.isoformat(),
                "include_coordinates": config.get("include_coordinates", False), "sample_seconds": 15, "heartbeat_seconds": 60,
                "limitation": "Sequential source and normalized-state samples; not atomic or exact transitions"})
    previous = None
    last_write = 0
    try:
        while datetime.now(timezone.utc) < deadline:
            started = datetime.now(timezone.utc).isoformat()
            try:
                record = await capture(config)
                record["type"] = "sample"
            except Exception:
                # Never log exception strings, tokens, URLs, or response bodies.
                record = {"type": "gap", "reason": "capture_failed"}
            if record != previous or time.monotonic() - last_write >= 60:
                save(path, {"at": started, "completed_at": datetime.now(timezone.utc).isoformat(), **record})
                previous = record
                last_write = time.monotonic()
            await asyncio.sleep(min(15, max(0, (deadline - datetime.now(timezone.utc)).total_seconds())))
    finally:
        save(path, {"type": "end", "at": datetime.now(timezone.utc).isoformat()})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--ends-at", help="Preserve an existing absolute capture deadline")
    parser.add_argument("--hours", type=float, default=48)
    args = parser.parse_args()
    if not 0 < args.hours <= 48:
        parser.error("Capture must be bounded to at most 48 hours")
    asyncio.run(run(args))
