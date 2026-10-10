"""Bounded local observations, without coordinates or reconstructed journeys."""

from datetime import timedelta
from hashlib import sha256
import json

from homeassistant.util import dt as dt_util

from .selection import selected_entities

RETENTION_DAYS = 7
MAX_EVENTS = 100
MAX_FRESHNESS_EVENTS = 25
KINDS = {"started", "presence", "source", "freshness", "refresh", "automatic_refresh"}
VALUES = {
    "automatic_refresh": {"requested", "send_failed"},
    "presence": {"home", "away", "driving", "unavailable"},
    "freshness": {"fresh", "stale", "unknown", "unavailable"},
    "refresh": {
        "requested",
        "checked",
        "cooldown",
        "busy",
        "limited",
        "disabled",
        "not_allowed",
        "unsupported",
        "no_position",
        "fresh",
        "send_failed",
        "unavailable",
    },
}


class ActivityLog:
    """Retain only allowlisted observations for the current input configuration."""

    def __init__(self, config, store=None):
        self.store = store
        self.closed = False
        self.members = set(config.get("members", {}))
        self.sources = selected_entities(config)
        self.fingerprint = sha256(
            json.dumps(config, sort_keys=True, default=str).encode()
        ).hexdigest()
        self.events = {member: [] for member in self.members}
        self.previous = {}

    def prune(self, now):
        changed = False
        cutoff = now - timedelta(days=RETENTION_DAYS)
        for member, events in self.events.items():
            self.events[member] = [
                event
                for event in events
                if (time := dt_util.parse_datetime(event["observed_at"])) is not None
                and time.tzinfo is not None
                and cutoff <= time <= now
            ]
            retained = self.events[member]
            freshness = [event for event in retained if event["kind"] == "freshness"]
            discard = {id(event) for event in freshness[:-MAX_FRESHNESS_EVENTS]}
            retained = [event for event in retained if id(event) not in discard]
            excess = max(0, len(retained) - MAX_EVENTS)
            discard = {
                id(event)
                for event in [e for e in retained if e["kind"] == "freshness"][:excess]
            }
            self.events[member] = [
                event for event in retained if id(event) not in discard
            ][-MAX_EVENTS:]
            changed |= len(events) != len(self.events[member])
        return changed

    def payload(self):
        self.prune(dt_util.utcnow())
        return {
            "fingerprint": self.fingerprint,
            "events": {
                member: [dict(event) for event in events]
                for member, events in self.events.items()
            },
        }

    async def load(self):
        if self.store is None:
            return
        try:
            saved = await self.store.async_load()
        except Exception:
            # Do not overwrite an unreadable history store.
            self.store = None
            return
        if not isinstance(saved, dict) or saved.get("fingerprint") != self.fingerprint:
            return
        groups = saved.get("events", {})
        if not isinstance(groups, dict):
            return
        for member in self.members:
            events = groups.get(member, [])
            if not isinstance(events, list):
                continue
            for raw in events[-MAX_EVENTS:]:
                if (
                    not isinstance(raw, dict)
                    or not isinstance(raw.get("kind"), str)
                    or raw["kind"] not in KINDS
                ):
                    continue
                kind, value = raw["kind"], raw.get("value")
                if kind in VALUES and (
                    not isinstance(value, str) or value not in VALUES[kind]
                ):
                    continue
                if (
                    kind == "source"
                    and value is not None
                    and (not isinstance(value, str) or value not in self.sources)
                ):
                    continue
                observed = raw.get("observed_at")
                if not isinstance(observed, str):
                    continue
                event = {"kind": kind, "observed_at": observed}
                if kind != "started":
                    event["value"] = value
                reported = raw.get("reported_at")
                parsed = (
                    dt_util.parse_datetime(reported)
                    if isinstance(reported, str)
                    else None
                )
                if parsed is not None and parsed.tzinfo is not None:
                    event["reported_at"] = parsed.isoformat()
                self.events[member].append(event)
        self.prune(dt_util.utcnow())

    def append(self, member, kind, value, now, reported_at=None):
        if self.closed or member not in self.members:
            return
        event = {"kind": kind, "observed_at": now.isoformat()}
        if kind != "started":
            event["value"] = value
        if reported_at is not None:
            event["reported_at"] = reported_at.isoformat()
        self.events[member].append(event)
        self.prune(now)
        if self.store is not None:
            self.store.async_delay_save(self.payload, 5)

    def observe(self, household, now):
        if self.closed:
            return
        if self.prune(now) and self.store is not None:
            self.store.async_delay_save(self.payload, 5)
        for member in household.members:
            evidence = (
                member.location.evidence
                if member.location and member.focusable
                else None
            )
            current = {
                "presence": member.presence,
                "source": evidence.source_entity if evidence else None,
                "freshness": evidence.freshness if evidence else "unavailable",
            }
            previous = self.previous.get(member.id)
            if previous is None:
                # A restart is an observation boundary, never an inferred trip.
                self.append(member.id, "started", None, now)
            for kind, value in current.items():
                if previous is None or previous[kind] != value:
                    self.append(
                        member.id,
                        kind,
                        value,
                        now,
                        evidence.reported_at
                        if evidence and kind == "freshness"
                        else None,
                    )
            self.previous[member.id] = current

    def project(self, member, label):
        self.prune(dt_util.utcnow())
        return {
            "retention_days": RETENTION_DAYS,
            "max_events": MAX_EVENTS,
            "persistent": self.store is not None,
            "events": [
                {**event, "value": label(event["value"])}
                if event["kind"] == "source"
                else dict(event)
                for event in reversed(self.events.get(member, []))
            ],
        }

    async def close(self):
        """Stop late callbacks from recreating history after removal."""
        self.closed = True
        await self.save()

    async def save(self):
        if self.store is not None:
            try:
                await self.store.async_save(self.payload())
            except Exception:
                self.store = None
