"""Explicit, bounded refresh of assigned trackers across supported providers.

The Circle viewing operation was observed on the native app. It is unofficial;
unsupported layouts fail closed and no cloud credentials cross the household API.
"""

from datetime import timedelta
from hashlib import sha256
import ssl

import aiohttp
from homeassistant.auth.permissions.const import POLICY_CONTROL
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .const import (
    CONF_MEMBERS,
    CONF_TRACKERS,
    CONF_FAMILY_REFRESH_ENABLED,
    CONF_AUTO_REQUEST_LOCATION,
)
from .location_requests import (
    MAX_REQUESTS,
    async_reserve_requests,
    available_notification_entity,
)
from .tracker_providers import TRACKER_PROVIDERS


OBSERVATION_WINDOW = timedelta(minutes=2)
FEEDBACK_RETENTION = timedelta(minutes=5)

MANUAL_INTERVAL = timedelta(minutes=1)
MANUAL_MAX_REQUESTS = MAX_REQUESTS


def next_available(runtime, circle_key, now):
    """Exact expiry of the manual rolling limit, independently of phone requests."""
    recent = sorted(
        t
        for t in runtime.location_request_times.get(circle_key, [])
        if now - t < timedelta(days=1)
    )
    if not recent:
        return None
    expiry = recent[-1] + MANUAL_INTERVAL
    if len(recent) >= MANUAL_MAX_REQUESTS:
        expiry = max(expiry, recent[-MANUAL_MAX_REQUESTS] + timedelta(days=1))
    return expiry if expiry > now else None


def key_for(entry_id, cid):
    return "family:" + sha256(f"{entry_id}:{cid}".encode()).hexdigest()


def plan(hass, runtime, registry):
    """Require a single loaded Circle whose complete membership is selected."""
    if (
        hass is None
        or registry is None
        or runtime.household is None
        or runtime.config.get(CONF_FAMILY_REFRESH_ENABLED) is not True
    ):
        return None
    targets = []
    for member in runtime.household.members:
        configured = runtime.config[CONF_MEMBERS][member.id][CONF_TRACKERS]
        choices = [(source, registry.async_get(source)) for source in configured]
        choices = [
            (source, registered)
            for source, registered in choices
            if registered is not None and registered.platform == "life360"
        ]
        if len(choices) > 1:
            return None
        if not choices:
            continue
        source, registered = choices[0]
        if registered.disabled:
            return None
        targets.append((member, source, registered))
    if not targets or len({r.config_entry_id for _, _, r in targets}) != 1:
        return None
    entry = hass.config_entries.async_get_entry(targets[0][2].config_entry_id)
    coordinator = getattr(getattr(entry, "runtime_data", None), "coordinator", None)
    circles = getattr(getattr(coordinator, "data", None), "circles", {})
    mids = {r.unique_id for _, _, r in targets}
    matches = [(cid, circle) for cid, circle in circles.items() if circle.mids == mids]
    if len(matches) != 1:
        return None
    cid, circle = matches[0]
    accounts = entry.options.get("accounts", {})
    enabled = [
        accounts[aid]
        for aid in circle.aids
        if aid in accounts and accounts[aid].get("enabled", True)
    ]
    if len(enabled) != 1 or not isinstance(enabled[0].get("authorization"), str):
        return None
    return entry.entry_id, cid, enabled[0]["authorization"], targets


async def async_send(hass, cid, authorization):
    """One request, owned TLS context, no retries or raw reply logging."""
    from life360.const import HOST, USER_AGENT

    if HOST != "api-cloudfront.life360.com":
        return False
    context = await hass.async_add_executor_job(ssl.create_default_context)
    connector = aiohttp.TCPConnector(ssl=context)
    async with aiohttp.ClientSession(
        connector=connector, timeout=aiohttp.ClientTimeout(total=20)
    ) as session:
        async with session.post(
            f"https://{HOST}/v3/circles/{cid}/smartRealTime/start",
            headers={
                "authorization": authorization,
                "accept": "application/json",
                "cache-control": "no-cache",
                "user-agent": USER_AGENT,
            },
            json={"requestTrace": False},
            allow_redirects=False,
        ) as response:
            return 200 <= response.status < 300


def report_time(runtime, member, source, now):
    """Read evidence from the explicit selected tracker even during Person fallback."""
    from .normalize import location_evidence

    states = getattr(runtime, "states", None)
    if states is None:
        ev = member.location.evidence if member.location else None
        return ev.reported_at if ev and ev.source_entity == source else None
    state = states.get(source)
    if state is None or state.state in {"unknown", "unavailable"}:
        return None
    report_id = (
        runtime.config[CONF_MEMBERS][member.id].get("location_reports", {}).get(source)
    )
    return location_evidence(
        state, states.get(report_id), now, report_id, 300
    ).reported_at


def assigned_plan(hass, runtime, registry):
    """Plan only explicitly assigned sources; unsupported sources remain visible."""
    if (
        hass is None
        or registry is None
        or runtime.household is None
        or runtime.config.get(CONF_FAMILY_REFRESH_ENABLED) is not True
    ):
        return [], []
    try:
        circle = plan(hass, runtime, registry)
    except (AttributeError, KeyError, TypeError):
        circle = None
    actions = []
    targets = []
    covered = set()
    if circle:
        covered = {source for _, source, _ in circle[3]}
        actions.append(
            {
                "kind": "circle",
                "key": key_for(*circle[:2]),
                "circle": circle,
                "sources": sorted(covered),
                "controls": sorted(covered),
            }
        )
    services = getattr(hass, "services", None)

    def has_service(domain, name):
        return bool(services and services.has_service(domain, name))

    for member in runtime.household.members:
        config = runtime.config[CONF_MEMBERS][member.id]
        for source in dict.fromkeys(config[CONF_TRACKERS]):
            registered = registry.async_get(source)
            target = {"id": member.id, "source": source, "outcome": "unsupported"}
            targets.append(target)
            if registered is None or registered.disabled:
                target["outcome"] = "unavailable"
                continue
            if source in covered:
                target["outcome"] = "waiting"
                continue
            action = None
            if registered.platform == "mobile_app":
                target["provider"] = "Home Assistant"
                if config.get(CONF_AUTO_REQUEST_LOCATION) is not True:
                    target["outcome"] = "disabled"
                    continue
                notify = available_notification_entity(hass, registry, source)
                if notify and has_service("notify", "send_message"):
                    action = {
                        "kind": "phone",
                        "key": source,
                        "notify": notify,
                        "sources": [source],
                        "controls": [source, notify],
                    }
                else:
                    target["outcome"] = "unavailable"
            elif registered.platform == "life360":
                target["provider"] = "Life360"
                if has_service("life360", "update_location"):
                    action = {
                        "kind": "entity",
                        "key": source,
                        "sources": [source],
                        "controls": [source],
                    }
            else:
                provider = next(
                    (
                        item
                        for item in TRACKER_PROVIDERS
                        if item.owns_entity(registry, source)
                    ),
                    None,
                )
                client = (
                    getattr(runtime, "managed_trackers", {}).get(provider.id)
                    if provider
                    else None
                )
                if (
                    client
                    and registered.config_entry_id == getattr(client, "entry_id", None)
                    and callable(getattr(client, "async_refresh_on_selection", None))
                ):
                    target["provider"] = provider.display_name
                    key = "provider:" + provider.id
                    action = next((a for a in actions if a["key"] == key), None)
                    if action:
                        action["sources"].append(source)
                        action["controls"].append(source)
                        target["outcome"] = "waiting"
                        continue
                    action = {
                        "kind": "provider",
                        "key": key,
                        "client": client,
                        "provider_id": provider.id,
                        "sources": [source],
                        "controls": [source],
                    }
            if action:
                target["outcome"] = "waiting"
                if not any(a["key"] == action["key"] for a in actions):
                    actions.append(action)
    for target in targets:
        target.setdefault(
            "provider", "Life360" if target["source"] in covered else "Tracker"
        )
    for action in actions:
        action["registry_identity"] = [
            (
                source,
                getattr(registry.async_get(source), "unique_id", None),
                getattr(registry.async_get(source), "config_entry_id", None),
                getattr(registry.async_get(source), "device_id", None),
            )
            for source in action["controls"]
        ]
    return actions, targets


def button_key(actions):
    """Keep existing Circle budgets; mixed households get a bounded button budget."""
    return (
        actions[0]["key"]
        if len(actions) == 1 and actions[0]["kind"] == "circle"
        else "family:assigned"
    )


def tracker_update(runtime, source):
    """HA receipt time is a separate observation, never a claimed GPS report."""
    state = getattr(runtime, "states", {}).get(source)
    if state is None or state.state in {"unknown", "unavailable"}:
        return None
    return max(
        state.last_updated, getattr(state, "last_reported", None) or state.last_updated
    )


def aggregate_members(targets):
    grouped = {}
    for target in targets:
        grouped.setdefault(target["id"], []).append(target)
    members = []
    for member_id, items in grouped.items():
        outcomes = [t["outcome"] for t in items]
        status = next(
            (
                s
                for s in ("updated", "ha_updated", "waiting", "unchanged")
                if s in outcomes
            ),
            outcomes[0],
        )
        members.append(
            {
                "id": member_id,
                "status": status,
                "trackers": [
                    {"provider": t.get("provider", "Tracker"), "status": t["outcome"]}
                    for t in items
                ],
            }
        )
    return members


def observe_family_refresh(runtime, now):
    """Latch reports and HA receipts separately, only within the observation window."""
    saved = getattr(runtime, "family_refresh", {})
    if not saved:
        return
    completed = saved.get("completed_at")
    if completed is not None:
        if now >= completed + FEEDBACK_RETENTION:
            runtime.family_refresh = {}
        return
    started = saved.get("started")
    if started is None or saved.get("status") != "requested":
        return
    deadline = started + OBSERVATION_WINDOW
    current = {m.id: m for m in runtime.household.members}
    for target in saved.get("targets", []):
        outcome = target.get("outcome", "waiting")
        if now < deadline and outcome == "waiting":
            member = current.get(target["id"])
            selected = (
                runtime.config.get(CONF_MEMBERS, {})
                .get(target["id"], {})
                .get(CONF_TRACKERS, [])
            )
            stamp = (
                report_time(runtime, member, target["source"], now) if member else None
            )
            received = tracker_update(runtime, target["source"])
            if member is None or target["source"] not in selected:
                outcome = "source_changed"
            elif stamp is not None and stamp > (target["reported_at"] or started):
                outcome = "updated"
            elif received is not None and received > (
                target.get("updated_at") or started
            ):
                # May subsequently be upgraded to genuine report evidence.
                target["ha_updated"] = True
        if now >= deadline and outcome == "waiting":
            outcome = "ha_updated" if target.get("ha_updated") else "unchanged"
        target["outcome"] = outcome
    saved["members"] = aggregate_members(saved.get("targets", []))
    if now >= deadline or all(
        t["outcome"] != "waiting" for t in saved.get("targets", [])
    ):
        saved["status"] = "complete"
        saved["completed_at"] = min(now, deadline)
        if now >= saved["completed_at"] + FEEDBACK_RETENTION:
            runtime.family_refresh = {}


def family_status(hass, runtime, registry=None):
    """Expose safe per-person results; restart clears only the observation."""
    now = dt_util.utcnow()
    observe_family_refresh(runtime, now)
    actions, planned_targets = assigned_plan(hass, runtime, registry)
    saved = getattr(runtime, "family_refresh", {})
    retry = next_available(runtime, button_key(actions), now) if actions else None
    return {
        "available": bool(planned_targets),
        "status": saved.get("status", "idle"),
        "members": saved.get("members", []),
        "next_available_at": retry.isoformat() if retry else None,
    }


def action_identity(action):
    identity = (
        action["kind"],
        action["key"],
        sorted(action["sources"]),
        sorted(action["controls"]),
        action["registry_identity"],
    )
    if action["kind"] == "circle":
        identity += (
            [(m.id, source, r.unique_id) for m, source, r in action["circle"][3]],
        )
    if action["kind"] == "provider":
        identity += (id(action["client"]),)
    return identity


async def async_refresh_family(hass, runtime, user):
    """Authorize assigned targets, reserve before dispatch, and isolate failures."""
    registry = er.async_get(hass)
    actions, targets = assigned_plan(hass, runtime, registry)
    if not actions:
        if targets:
            runtime.family_refresh = {
                "status": "complete",
                "targets": targets,
                "members": aggregate_members(targets),
                "completed_at": dt_util.utcnow(),
            }
        return {"status": "unsupported"}
    if not all(
        user.permissions.check_entity(source, POLICY_CONTROL)
        for action in actions
        for source in action["controls"]
    ):
        return {"status": "not_allowed"}
    now = dt_util.utcnow()
    key = button_key(actions)
    reserved = await async_reserve_requests(runtime, [key], now)
    if reserved != "reserved":
        retry = next_available(runtime, key, now)
        return {"status": reserved, "retry_at": retry.isoformat() if retry else None}
    current, current_targets = assigned_plan(hass, runtime, er.async_get(hass))
    if [action_identity(a) for a in current] != [
        action_identity(a) for a in actions
    ] or [(t["id"], t["source"], t["outcome"]) for t in current_targets] != [
        (t["id"], t["source"], t["outcome"]) for t in targets
    ]:
        return {"status": "unsupported"}
    # Prefer current server-side credentials, never retain them in feedback.
    actions = current
    members = {m.id: m for m in runtime.household.members}
    for target in targets:
        target["reported_at"] = report_time(
            runtime, members[target["id"]], target["source"], now
        )
        target["updated_at"] = tracker_update(runtime, target["source"])
    saved = {
        "status": "checking",
        "started": now,
        "targets": targets,
        "members": aggregate_members(targets),
    }
    runtime.family_refresh = saved
    accepted = False
    for action in actions:
        # Options reloads or selections changed while a previous action awaited.
        latest, _ = assigned_plan(hass, runtime, er.async_get(hass))
        live = next(
            (a for a in latest if action_identity(a) == action_identity(action)), None
        )
        affected = [t for t in targets if t["source"] in action["sources"]]
        if live is None or runtime.family_refresh is not saved:
            for t in affected:
                t["outcome"] = "source_changed"
            continue
        action = live
        keys = [action["key"]] if action["kind"] == "circle" else action["sources"]
        status = (
            "reserved"
            if keys == [key]
            else await async_reserve_requests(runtime, keys, dt_util.utcnow())
        )
        if status == "reserved":
            # Disk I/O also yields; recheck scope and control immediately before send.
            latest, _ = assigned_plan(hass, runtime, er.async_get(hass))
            live = next(
                (a for a in latest if action_identity(a) == action_identity(action)),
                None,
            )
            if (
                live is None
                or runtime.family_refresh is not saved
                or not all(
                    user.permissions.check_entity(s, POLICY_CONTROL)
                    for s in action["controls"]
                )
            ):
                status = "source_changed"
            else:
                try:
                    if action["kind"] == "circle":
                        status = (
                            "requested"
                            if await async_send(
                                hass, live["circle"][1], live["circle"][2]
                            )
                            else "send_failed"
                        )
                    elif action["kind"] == "phone":
                        await hass.services.async_call(
                            "notify",
                            "send_message",
                            {
                                "entity_id": action["notify"],
                                "message": "request_location_update",
                            },
                            blocking=True,
                        )
                        status = "requested"
                    elif action["kind"] == "entity":
                        await hass.services.async_call(
                            "life360",
                            "update_location",
                            {"entity_id": action["sources"]},
                            blocking=True,
                        )
                        status = "requested"
                    else:
                        previous = getattr(runtime, "selection_refresh_times", {}).get(
                            action["provider_id"]
                        )
                        if previous and dt_util.utcnow() - previous < MANUAL_INTERVAL:
                            status = "cooldown"
                        else:
                            runtime.selection_refresh_times[action["provider_id"]] = (
                                dt_util.utcnow()
                            )
                            status = await action["client"].async_refresh_on_selection()
                except Exception:
                    status = "send_failed"
        if status in {"requested", "checked"}:
            accepted = True
        for t in affected:
            t["outcome"] = "waiting" if status in {"requested", "checked"} else status
            t["request_status"] = status
    saved["status"] = "requested" if accepted else "send_failed"
    saved["members"] = aggregate_members(targets)
    if not accepted:
        saved["completed_at"] = dt_util.utcnow()
    observe_family_refresh(runtime, dt_util.utcnow())
    return {"status": "requested" if accepted else "send_failed"}
