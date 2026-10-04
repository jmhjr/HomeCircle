"""Optional Life360 client used only when the user connects an account.

The Life360 API is unofficial. Keep credentials and raw responses out of logs.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from math import isfinite
import ssl
from typing import Any

from aiohttp import ClientSession, ClientTimeout, TCPConnector
from life360 import (
    Life360,
    Life360Error,
    LoginError,
    NotModified,
    RateLimited,
    Unauthorized,
)

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers import entity_registry as er, issue_registry as ir

from .const import DOMAIN

from .tracker_providers import ProviderHealth, REAUTH_PROVIDER_KEY


POLL_INTERVAL = timedelta(seconds=60)
DISCOVERY_RETRY = timedelta(minutes=10)
UNAVAILABLE_AFTER = timedelta(minutes=5)


async def new_session() -> ClientSession:
    """Use a private TLS context, as required by current Life360 transport behavior."""
    ssl_context = await asyncio.to_thread(ssl.create_default_context)
    return ClientSession(
        connector=TCPConnector(ssl=ssl_context),
        timeout=ClientTimeout(sock_connect=15, total=60),
    )


async def _login_client(
    session: ClientSession, account: dict[str, str]
) -> tuple[Life360, dict[str, Any] | None]:
    """Authenticate and retain a token user's already fetched profile."""
    method = account["method"]
    if method == "token":
        api = Life360(session, 1, authorization=f"Bearer {account['secret']}")
        profile = await api.get_me()
    elif method == "password":
        api = Life360(session, 1)
        await api.login_by_username(account["username"], account["secret"])
        profile = None
    else:
        raise ValueError("Unsupported Life360 authorization method")
    return api, profile


async def authorized_client(session: ClientSession, account: dict[str, str]) -> Life360:
    """Create a client from either a password or a user supplied access token."""
    api, _profile = await _login_client(session, account)
    return api


async def validate_account(account: dict[str, str]) -> str:
    """Return a private stable account fingerprint, never the provider account ID."""
    async with await new_session() as session:
        api, profile = await _login_client(session, account)
        if profile is None:
            profile = await api.get_me()
        if not isinstance(profile, dict) or not isinstance(profile.get("id"), str):
            raise ValueError("Life360 account identity missing")
        account_id = profile["id"]
        if not account_id:
            raise ValueError("Life360 account identity missing")
        return sha256(f"homecircle:life360:{account_id}".encode()).hexdigest()


def member_name(raw: dict[str, Any]) -> str:
    name = " ".join(
        part.strip()
        for part in (raw.get("firstName"), raw.get("lastName"))
        if isinstance(part, str) and part.strip()
    )
    return name or "Life360 member"


def number(value: Any, minimum: float, maximum: float) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if isfinite(result) and minimum <= result <= maximum else None


def boolean_flag(value: Any) -> bool | None:
    """Preserve missing or malformed provider flags as unknown."""
    if str(value) == "1":
        return True
    if str(value) == "0":
        return False
    return None


def parse_location(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Keep only fields HomeCircle needs; never retain addresses or raw replies."""
    if not isinstance(raw, dict):
        return None
    features = raw.get("features")
    features = features if isinstance(features, dict) else {}
    if str(features.get("shareLocation", "1")) == "0":
        return None
    location = raw.get("location")
    if not isinstance(location, dict):
        return None
    latitude = number(location.get("latitude"), -90, 90)
    longitude = number(location.get("longitude"), -180, 180)
    if latitude is None or longitude is None:
        return None
    timestamp = number(location.get("timestamp"), 0, 4102444800)
    last_seen = (
        datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
        if timestamp is not None
        else None
    )
    accuracy_feet = number(location.get("accuracy"), 0, 1000000)
    battery = number(location.get("battery"), 0, 100)
    speed = number(location.get("speed"), 0, 10000)
    return {
        "latitude": latitude,
        "longitude": longitude,
        "accuracy": accuracy_feet * 0.3048 if accuracy_feet is not None else 0,
        "last_seen": last_seen,
        "battery_level": battery,
        "battery_charging": boolean_flag(location.get("charge")),
        "driving": boolean_flag(location.get("isDriving")),
        "speed": speed * 2.25 if speed is not None else None,
    }


def malformed_location_reply(raw: dict[str, Any]) -> bool:
    """Distinguish changed location fields from an intentionally absent fix."""
    features = raw.get("features")
    if isinstance(features, dict) and str(features.get("shareLocation", "1")) == "0":
        return False
    location = raw.get("location")
    if location is None:
        return False
    return not isinstance(location, dict) or any(
        number(location.get(key), minimum, maximum) is None
        for key, minimum, maximum in (
            ("latitude", -90, 90),
            ("longitude", -180, 180),
        )
    )


class Life360DirectTracker(TrackerEntity):
    """A Life360 Member exposed as an ordinary HA device tracker."""

    _attr_source_type = SourceType.GPS
    _attr_should_poll = False

    def __init__(self, member_id: str, raw: dict[str, Any]) -> None:
        self.member_id = member_id
        self._attr_unique_id = f"homecircle_life360_{member_id}"
        self._attr_name = f"Life360 {member_name(raw)}"
        self._attr_available = False
        self._details: dict[str, Any] = {}
        self.update(raw)

    def update(self, raw: dict[str, Any]) -> None:
        """Project one report without recording private API response fields."""
        self._attr_name = f"Life360 {member_name(raw)}"
        details = parse_location(raw)
        self._attr_available = details is not None
        self._details = details or {}
        self._attr_latitude = self._details.get("latitude")
        self._attr_longitude = self._details.get("longitude")
        self._attr_location_accuracy = self._details.get("accuracy", 0)
        if self.entity_id and getattr(self, "hass", None) is not None:
            self.async_write_ha_state()

    def mark_unavailable(self) -> None:
        """Do not keep displaying a last known location as live after a long outage."""
        self._attr_available = False
        self._details = {}
        self._attr_latitude = None
        self._attr_longitude = None
        if self.entity_id and getattr(self, "hass", None) is not None:
            self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in self._details.items()
            if key not in ("latitude", "longitude", "accuracy") and value is not None
        }


class DirectLife360:
    """Discover members and poll their reports without storing location history."""

    def __init__(
        self,
        hass: HomeAssistant,
        account: dict[str, str],
        add_entities,
        entry_id: str = "",
    ):
        self.hass = hass
        self.account = account
        self.add_entities = add_entities
        self.entry_id = entry_id
        self.trackers: dict[str, Life360DirectTracker] = {}
        self.circles: dict[str, list[str]] = {}
        self.session: ClientSession | None = None
        self.api: Life360 | None = None
        self._unsub = None
        self._task: asyncio.Task | None = None
        self._interval_tasks: set[asyncio.Task] = set()
        self._stopping = False
        self._auth_blocked = False
        self._next_discovery = datetime.min.replace(tzinfo=timezone.utc)
        self._next_access_probe = datetime.min.replace(tzinfo=timezone.utc)
        self._retry_at = datetime.min.replace(tzinfo=timezone.utc)
        self._access_denied = False
        self._last_success: dict[str, datetime] = {}
        self._health_state = "starting"
        self._last_api_success: datetime | None = None
        self._last_error: datetime | None = None
        self._lock = asyncio.Lock()

    def health_snapshot(self) -> ProviderHealth:
        """Expose diagnosis data without IDs, locations, credentials, or replies."""
        return ProviderHealth(
            state=self._health_state,
            discovered_trackers=len(self.trackers),
            available_trackers=sum(
                tracker.available for tracker in self.trackers.values()
            ),
            last_api_success=self._last_api_success,
            last_error=self._last_error,
            retry_at=self._retry_at
            if self._retry_at > datetime.min.replace(tzinfo=timezone.utc)
            else None,
        )

    async def async_start(self) -> None:
        # Earlier development builds used a non-actionable custom auth issue.
        if self.entry_id:
            ir.async_delete_issue(self.hass, DOMAIN, f"life360_auth_{self.entry_id}")
        self.session = await new_session()
        if self.entry_id:
            self._restore_registered_trackers()
        self._unsub = async_track_time_interval(
            self.hass, self._interval, POLL_INTERVAL
        )
        self._task = self.hass.async_create_task(
            self.async_refresh(), "HomeCircle Life360 refresh"
        )

    def _restore_registered_trackers(self) -> None:
        """Expose saved tracker entities as unavailable until discovery succeeds."""
        prefix = "homecircle_life360_"
        saved = er.async_entries_for_config_entry(
            er.async_get(self.hass), self.entry_id
        )
        restored = []
        for entity in saved:
            if (
                entity.domain != "device_tracker"
                or entity.platform != DOMAIN
                or not entity.unique_id.startswith(prefix)
            ):
                continue
            member_id = entity.unique_id[len(prefix) :]
            if not member_id or member_id in self.trackers:
                continue
            tracker = Life360DirectTracker(member_id, {})
            tracker._attr_name = entity.original_name or tracker.name
            self.trackers[member_id] = tracker
            restored.append(tracker)
        if restored:
            self.add_entities(restored)

    async def _interval(self, _now) -> None:
        task = asyncio.current_task()
        if task is not None:
            self._interval_tasks.add(task)
        try:
            await self.async_refresh()
        finally:
            if task is not None:
                self._interval_tasks.discard(task)

    async def async_refresh(self) -> None:
        if self._stopping or self._lock.locked():
            return
        if self._auth_blocked:
            self._mark_stale()
            return
        if datetime.now(timezone.utc) < self._retry_at:
            self._mark_stale()
            return
        async with self._lock:
            authenticating = False
            self._access_denied = False
            try:
                if self.api is None:
                    assert self.session is not None
                    authenticating = True
                    self.api = await authorized_client(self.session, self.account)
                    authenticating = False
                now = datetime.now(timezone.utc)
                discovery_failed = discovery_malformed = 0
                if now >= self._next_discovery:
                    discovery_failed, discovery_malformed = await self._discover()
                    if not discovery_failed and not discovery_malformed:
                        self._last_api_success = datetime.now(timezone.utc)
                if self.circles:
                    succeeded, failed, malformed = await self._poll_members()
                    if succeeded:
                        self._last_api_success = datetime.now(timezone.utc)
                    failed += discovery_failed
                    malformed += discovery_malformed
                else:
                    succeeded = 0
                    failed = discovery_failed
                    malformed = discovery_malformed
                if (
                    not succeeded
                    and self._access_denied
                    and now >= self._next_access_probe
                ):
                    self._next_access_probe = now + DISCOVERY_RETRY
                    try:
                        await self.api.get_me()
                    except (LoginError, Unauthorized):
                        self.api = None
                        assert self.session is not None
                        authenticating = True
                        self.api = await authorized_client(self.session, self.account)
                        authenticating = False
                        self._next_discovery = datetime.min.replace(tzinfo=timezone.utc)
                self._health_state = (
                    "unexpected_response"
                    if malformed
                    else "partial"
                    if failed and succeeded
                    else "api_error"
                    if failed
                    else "connected"
                    if self.circles
                    else "discovering"
                )
                if failed or malformed:
                    self._last_error = datetime.now(timezone.utc)
                self._retry_at = datetime.min.replace(tzinfo=timezone.utc)
            except asyncio.CancelledError:
                raise
            except RateLimited as err:
                seconds = max(err.retry_after or 0, DISCOVERY_RETRY.total_seconds())
                self._retry_at = datetime.now(timezone.utc) + timedelta(seconds=seconds)
                self._health_state = "rate_limited"
                self._last_error = datetime.now(timezone.utc)
            except (LoginError, Unauthorized):
                self.api = None
                self._auth_blocked = authenticating
                self._retry_at = (
                    datetime.min.replace(tzinfo=timezone.utc)
                    if authenticating
                    else datetime.now(timezone.utc) + DISCOVERY_RETRY
                )
                self._health_state = "auth_required" if authenticating else "api_error"
                self._last_error = datetime.now(timezone.utc)
                if (
                    authenticating
                    and self.entry_id
                    and (
                        entry := self.hass.config_entries.async_get_entry(self.entry_id)
                    )
                ):
                    entry.async_start_reauth(
                        self.hass, data={REAUTH_PROVIDER_KEY: "life360"}
                    )
            except (AttributeError, KeyError, TypeError, ValueError):
                self._retry_at = datetime.now(timezone.utc) + POLL_INTERVAL
                self._health_state = "unexpected_response"
                self._last_error = datetime.now(timezone.utc)
            except (TimeoutError, OSError):
                self._retry_at = datetime.now(timezone.utc) + POLL_INTERVAL
                self._health_state = "network_error"
                self._last_error = datetime.now(timezone.utc)
            except Life360Error:
                self._retry_at = datetime.now(timezone.utc) + POLL_INTERVAL
                self._health_state = "api_error"
                self._last_error = datetime.now(timezone.utc)
            self._mark_stale()

    def _mark_stale(self) -> None:
        now = datetime.now(timezone.utc)
        for member_id, tracker in self.trackers.items():
            last_success = self._last_success.get(member_id)
            if last_success and now - last_success >= UNAVAILABLE_AFTER:
                tracker.mark_unavailable()

    async def _discover(self) -> tuple[int, int]:
        assert self.api is not None
        circles = await self.api.get_circles()
        candidates: dict[str, dict[str, Any]] = {}
        memberships: dict[str, list[str]] = {}
        failed = malformed = 0
        for circle in circles:
            if not isinstance(circle, dict) or not circle.get("id"):
                malformed += 1
                continue
            circle_id = str(circle["id"])
            try:
                members = await self.api.get_circle_members(circle_id)
            except RateLimited:
                raise
            except (LoginError, Unauthorized):
                failed += 1
                self._access_denied = True
                continue
            except NotModified:
                members = []
                for member_id, previous in self.circles.items():
                    if circle_id in previous:
                        memberships.setdefault(member_id, []).append(circle_id)
                continue
            except Life360Error:
                failed += 1
                continue
            except (AttributeError, KeyError, TypeError, ValueError):
                malformed += 1
                continue
            if not isinstance(members, list):
                malformed += 1
                continue
            for raw in members:
                if not isinstance(raw, dict) or not raw.get("id"):
                    malformed += 1
                    continue
                member_id = str(raw["id"])
                memberships.setdefault(member_id, []).append(circle_id)
                if member_id not in candidates or parse_location(raw):
                    candidates[member_id] = raw
        if failed or malformed:
            for member_id, previous in self.circles.items():
                known = memberships.setdefault(member_id, [])
                for circle_id in previous:
                    if circle_id not in known:
                        known.append(circle_id)
        self.circles = memberships
        new = []
        for member_id, raw in candidates.items():
            if member_id not in self.trackers:
                tracker = Life360DirectTracker(member_id, raw)
                self.trackers[member_id] = tracker
                if tracker.available:
                    self._last_success[member_id] = datetime.now(timezone.utc)
                new.append(tracker)
            else:
                self.trackers[member_id].update(raw)
                if self.trackers[member_id].available:
                    self._last_success[member_id] = datetime.now(timezone.utc)
        if new:
            self.add_entities(new)
        self._next_discovery = datetime.now(timezone.utc) + (
            POLL_INTERVAL if failed or malformed else DISCOVERY_RETRY
        )
        return failed, malformed

    async def _poll_members(self) -> tuple[int, int, int]:
        assert self.api is not None
        succeeded = failed = malformed = 0
        for member_id, circle_ids in self.circles.items():
            had_error = bad_shape = False
            for circle_id in circle_ids:
                try:
                    raw = await self.api.get_circle_member(circle_id, member_id)
                except NotModified:
                    self._last_success[member_id] = datetime.now(timezone.utc)
                    succeeded += 1
                    if self.trackers[member_id].available:
                        break
                    continue
                except RateLimited:
                    raise
                except (LoginError, Unauthorized):
                    had_error = True
                    self._access_denied = True
                    continue
                except Life360Error:
                    had_error = True
                    continue
                if not isinstance(raw, dict):
                    had_error = bad_shape = True
                    continue
                if malformed_location_reply(raw):
                    had_error = bad_shape = True
                    continue
                if parse_location(raw) is not None:
                    self.trackers[member_id].update(raw)
                    self._last_success[member_id] = datetime.now(timezone.utc)
                    succeeded += 1
                    break
                if circle_id == circle_ids[-1]:
                    self.trackers[member_id].update(raw)
                    self._last_success[member_id] = datetime.now(timezone.utc)
                    succeeded += 1
            else:
                if had_error:
                    failed += 1
                    malformed += bad_shape
        return succeeded, failed, malformed

    async def async_stop(self) -> None:
        self._stopping = True
        if self._unsub:
            self._unsub()
            self._unsub = None
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        interval_tasks = tuple(self._interval_tasks)
        for task in interval_tasks:
            task.cancel()
        if interval_tasks:
            await asyncio.gather(*interval_tasks, return_exceptions=True)
        if self.session:
            await self.session.close()
            self.session = None
