"""Bounded, opt-in requests for quiet HA Mobile App trackers."""

from datetime import UTC, datetime, timedelta
import logging

from homeassistant.helpers import entity_registry as er

from .const import CONF_AUTO_REQUEST_LOCATION, CONF_MEMBERS, CONF_TRACKERS

QUIET_PERIOD = timedelta(minutes=15)
RETRY_PERIOD = timedelta(minutes=1)
MAX_REQUESTS = 50
REQUEST_WINDOW = timedelta(days=1)
MAX_UNANSWERED_AUTOMATIC_ATTEMPTS = 3
_LOGGER = logging.getLogger(__name__)


def notification_entity(registry, tracker_id: str) -> str | None:
    """Find the Mobile App notification entity on the tracker's HA device."""
    tracker = registry.async_get(tracker_id)
    if tracker is None or tracker.platform != "mobile_app" or not tracker.device_id:
        return None
    return next(
        (
            entry.entity_id
            for entry in registry.entities.values()
            if entry.device_id == tracker.device_id
            and entry.domain == "notify"
            and entry.platform == "mobile_app"
            and not entry.disabled
        ),
        None,
    )


def available_notification_entity(hass, registry, tracker_id: str) -> str | None:
    """Return a live notification target, if HA has one."""
    entity_id = notification_entity(registry, tracker_id)
    state = hass.states.get(entity_id) if entity_id else None
    # A new NotifyEntity is normally "unknown" until its first send.
    return entity_id if state and state.state != "unavailable" else None


async def async_reserve_request(runtime, tracker_id: str, now: datetime) -> str:
    """Share the atomic reservation path with family requests."""
    return await async_reserve_requests(runtime, [tracker_id], now)


async def async_reserve_requests(
    runtime,
    keys: list[str],
    now: datetime,
    *,
    max_requests: int = MAX_REQUESTS,
    retry_period: timedelta = RETRY_PERIOD,
    automatic_reported_at: datetime | None = None,
) -> str:
    """Reserve all affected sources atomically, including concurrent viewers."""
    import asyncio

    if runtime.location_request_store is None:
        return "unavailable"
    lock = getattr(runtime, "location_request_lock", None)
    if lock is None:
        runtime.location_request_lock = lock = asyncio.Lock()
    async with lock:
        keys = list(dict.fromkeys(keys))
        automatic_before = dict(getattr(runtime, "automatic_location_requests", {}))
        automatic = dict(automatic_before)
        if automatic_reported_at is not None:
            for key in keys:
                previous = automatic.get(key, {})
                last = previous.get("last_attempt_at")
                last = datetime.fromisoformat(last) if last else None
                attempts = previous.get("attempts", 0)
                if last and automatic_reported_at > last:
                    attempts = 0
                if attempts >= MAX_UNANSWERED_AUTOMATIC_ATTEMPTS:
                    return "paused"
                if last and now - last < QUIET_PERIOD:
                    return "cooldown"
                automatic[key] = {
                    "last_attempt_at": now.isoformat(),
                    "attempts": attempts + 1,
                }
        for key in keys:
            recent = [
                t
                for t in runtime.location_request_times.get(key, [])
                if now - t < REQUEST_WINDOW
            ]
            if len(recent) >= max_requests:
                return "limited"
            if recent and now - max(recent) < retry_period:
                return "cooldown"
        before_times = {k: list(v) for k, v in runtime.location_request_times.items()}
        before_last = dict(runtime.last_location_request)
        for key in keys:
            runtime.location_request_times[key] = [
                t
                for t in runtime.location_request_times.get(key, [])
                if now - t < REQUEST_WINDOW
            ] + [now]
            runtime.last_location_request[key] = now
        runtime.automatic_location_requests = automatic
        try:
            await runtime.location_request_store.async_save(
                {
                    "requests": {
                        key: [stamp.isoformat() for stamp in times]
                        for key, times in runtime.location_request_times.items()
                    },
                    "automatic": automatic,
                }
            )
        except Exception:
            for key in keys:
                before_times.setdefault(key, [])
            runtime.location_request_times = before_times
            runtime.last_location_request = before_last
            runtime.automatic_location_requests = automatic_before
            _LOGGER.warning("HomeCircle could not save its location request limit")
            return "unavailable"
        for key in keys:
            runtime.restored_location_requests.discard(key)
        return "reserved"


async def async_request_quiet_locations(
    hass,
    runtime,
    now: datetime,
    *,
    member_id: str | None = None,
    on_selection: bool = False,
) -> None:
    """Space automatic attempts by 15 minutes and pause after three unanswered."""
    if runtime.location_request_store is None or not hass.services.has_service(
        "notify", "send_message"
    ):
        return
    registry = er.async_get(hass)
    for member in runtime.household.members if runtime.household else ():
        if member_id is not None and member.id != member_id:
            continue
        if (
            runtime.config[CONF_MEMBERS][member.id].get(CONF_AUTO_REQUEST_LOCATION)
            is not True
        ):
            continue
        location = member.location
        tracker_id = location.evidence.source_entity if location else None
        if (
            not tracker_id
            or tracker_id not in runtime.config[CONF_MEMBERS][member.id][CONF_TRACKERS]
        ):
            continue
        state = runtime.states.get(tracker_id)
        if state is None or state.state in {"unknown", "unavailable"}:
            continue
        notify_entity = available_notification_entity(hass, registry, tracker_id)
        if notify_entity is None:
            continue
        updated_at = max(
            state.last_updated,
            getattr(state, "last_reported", None) or state.last_updated,
        )
        if not on_selection:
            if now - updated_at < QUIET_PERIOD:
                continue
            recent = runtime.location_request_times.get(tracker_id, [])
            # Use persisted shared attempts: manual requests also give the phone
            # a chance to respond, and must not immediately trigger an auto retry.
            if recent and now - max(recent) < QUIET_PERIOD:
                continue
        if (
            await async_reserve_requests(
                runtime,
                [tracker_id],
                now,
                automatic_reported_at=None if on_selection else updated_at,
            )
            != "reserved"
        ):
            continue
        try:
            await hass.services.async_call(
                "notify",
                "send_message",
                {"entity_id": notify_entity, "message": "request_location_update"},
                blocking=True,
            )
        except Exception:
            # Keep the persisted attempt counted to protect the daily cap.
            _LOGGER.warning("A HomeCircle location request could not be sent")
            runtime.location_request_failures.add(tracker_id)
            outcome = "send_failed"
        else:
            runtime.location_request_failures.discard(tracker_id)
            outcome = "requested"
        if not on_selection and getattr(runtime, "activity", None) is not None:
            runtime.activity.append(
                member.id, "automatic_refresh", outcome, datetime.now(UTC)
            )


def request_status(
    runtime,
    member,
    now: datetime | None = None,
    registry=None,
    service_available=True,
    notify_available=True,
) -> dict:
    """Expose request delivery separately from tracker response."""
    now = now or datetime.now(UTC)
    enabled = (
        runtime.config[CONF_MEMBERS][member.id].get(CONF_AUTO_REQUEST_LOCATION) is True
    )
    if not enabled:
        return {"enabled": False, "requested_at": None, "status": "disabled"}
    location = member.location
    tracker_id = location.evidence.source_entity if location else None
    selected = runtime.config[CONF_MEMBERS][member.id][CONF_TRACKERS]
    mobile_trackers = (
        [tracker for tracker in selected if notification_entity(registry, tracker)]
        if registry is not None
        else []
    )
    if not mobile_trackers:
        return {"enabled": True, "requested_at": None, "status": "unsupported"}
    if tracker_id not in mobile_trackers:
        return {
            "enabled": True,
            "requested_at": None,
            "status": "not_selected" if tracker_id else "no_position",
        }
    if (
        runtime.location_request_store is None
        or not service_available
        or not notify_available
    ):
        return {"enabled": True, "requested_at": None, "status": "unavailable"}
    requested_at = runtime.last_location_request.get(tracker_id)
    state = runtime.states.get(tracker_id) if tracker_id else None
    recent = [
        stamp
        for stamp in runtime.location_request_times.get(tracker_id, [])
        if now - stamp < REQUEST_WINDOW
    ]
    limit_reached = len(recent) >= MAX_REQUESTS
    next_request_at = (
        (min(recent) + REQUEST_WINDOW).isoformat() if limit_reached else None
    )
    if requested_at is None:
        observed = (
            max(
                state.last_updated,
                getattr(state, "last_reported", None) or state.last_updated,
            )
            if state is not None
            else None
        )
        status = (
            "quiet_pending"
            if observed is not None and now - observed < QUIET_PERIOD
            else "request_pending"
        )
        return {
            "enabled": True,
            "requested_at": None,
            "status": status,
            "next_request_at": next_request_at,
        }
    if tracker_id in runtime.restored_location_requests:
        return {
            "enabled": True,
            "requested_at": requested_at.isoformat(),
            "status": "response_unverified",
            "next_request_at": next_request_at,
        }
    if tracker_id in runtime.location_request_failures:
        return {
            "enabled": enabled,
            "requested_at": requested_at.isoformat(),
            "status": "send_failed",
            "next_request_at": next_request_at,
        }
    reported_at = getattr(state, "last_reported", None) if state else None
    responded = reported_at is not None and reported_at > requested_at
    return {
        "enabled": enabled,
        "requested_at": requested_at.isoformat(),
        "status": (
            "tracker_responded"
            if responded
            else "no_response"
            if now - requested_at >= QUIET_PERIOD
            else "waiting"
        ),
        "next_request_at": next_request_at,
    }


def restore_automatic_requests(saved) -> dict:
    """Restore retry pauses independently of the rolling daily budget."""
    result = {}
    if not isinstance(saved, dict):
        return result
    for key, value in saved.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            continue
        attempts = value.get("attempts")
        try:
            stamp = datetime.fromisoformat(value.get("last_attempt_at", ""))
        except (ValueError, TypeError):
            continue
        if stamp.tzinfo and type(attempts) is int and 1 <= attempts <= 3:
            result[key] = {"attempts": attempts, "last_attempt_at": stamp.isoformat()}
    return result
