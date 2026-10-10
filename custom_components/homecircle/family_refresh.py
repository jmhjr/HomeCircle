"""Explicit, bounded Circle refresh for compatible external Life360 trackers.

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

from .const import CONF_MEMBERS, CONF_TRACKERS
from .location_requests import MAX_REQUESTS, async_reserve_requests


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
    if hass is None or registry is None or runtime.household is None:
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


def family_status(hass, runtime, registry=None):
    """Only same-source newer evidence counts; restart clears the observation."""
    try:
        operation = plan(hass, runtime, registry)
        available = operation is not None
    except (AttributeError, KeyError, TypeError):
        available = False
        operation = None
    saved = getattr(runtime, "family_refresh", {})
    status = saved.get("status", "idle")
    members = []
    started = saved.get("started")
    complete = bool(started and (dt_util.utcnow() - started).total_seconds() >= 120)
    current = {m.id: m for m in runtime.household.members}
    for target in saved.get("targets", []):
        member = current.get(target["id"])
        selected = (
            runtime.config.get(CONF_MEMBERS, {})
            .get(target["id"], {})
            .get(CONF_TRACKERS, [])
        )
        stamp = (
            report_time(runtime, member, target["source"], dt_util.utcnow())
            if member
            else None
        )
        outcome = "waiting"
        if member is None or target["source"] not in selected:
            outcome = "source_changed"
        elif stamp is not None and stamp > (target["reported_at"] or started):
            outcome = "updated"
        elif complete:
            outcome = "unchanged"
        members.append({"id": target["id"], "status": outcome})
    if status == "requested" and (
        complete or all(m["status"] == "updated" for m in members)
    ):
        status = "complete"
    retry = (
        next_available(runtime, key_for(*operation[:2]), dt_util.utcnow())
        if operation
        else None
    )
    return {
        "available": available,
        "status": status,
        "members": members,
        "next_available_at": retry.isoformat() if retry else None,
    }


async def async_refresh_family(hass, runtime, user):
    """Authorize the full Circle before persisting a shared request reservation."""
    try:
        operation = plan(hass, runtime, er.async_get(hass))
    except (AttributeError, KeyError, TypeError):
        operation = None
    if operation is None:
        return {"status": "unsupported"}
    entry_id, cid, authorization, targets = operation
    if not all(
        user.permissions.check_entity(source, POLICY_CONTROL)
        for _, source, _ in targets
    ):
        return {"status": "not_allowed"}
    now = dt_util.utcnow()
    circle_key = key_for(entry_id, cid)
    reserved = await async_reserve_requests(
        runtime,
        [circle_key],
        now,
        max_requests=MANUAL_MAX_REQUESTS,
        retry_period=MANUAL_INTERVAL,
    )
    if reserved != "reserved":
        retry = next_available(runtime, circle_key, now)
        return {"status": reserved, "retry_at": retry.isoformat() if retry else None}
    # Configuration/source changes during the disk save must not dispatch old scope.
    current = plan(hass, runtime, er.async_get(hass))

    def identity(items):
        return [(m.id, source, registered.unique_id) for m, source, registered in items]

    if (
        current is None
        or current[:2] != operation[:2]
        or identity(current[3]) != identity(targets)
    ):
        return {"status": "unsupported"}
    authorization = current[2]
    runtime.family_refresh = {
        "status": "checking",
        "started": now,
        "targets": [
            {
                "id": m.id,
                "source": source,
                "reported_at": report_time(runtime, m, source, now),
            }
            for m, source, _ in targets
        ],
    }
    try:
        accepted = await async_send(hass, cid, authorization)
    except Exception:
        accepted = False
    runtime.family_refresh["status"] = "requested" if accepted else "send_failed"
    if not accepted:
        runtime.family_refresh["targets"] = []
    return {"status": runtime.family_refresh["status"]}
