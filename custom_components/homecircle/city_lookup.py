"""Opt-in, bounded Photon city lookup without sending identity or credentials."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from hashlib import sha256
import math
import json
import re

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

REGIONS = set(
    "Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming|District of Columbia|Puerto Rico".lower().split(
        "|"
    )
)
CODES = set(
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC PR".split()
)


def text(value, limit=160):
    if (
        not isinstance(value, str)
        or len(value) > limit
        or any(ord(c) < 32 for c in value)
    ):
        return None
    value = value.strip()
    return (
        value
        if value and value.casefold() not in ("unknown", "unavailable", "none", "null")
        else None
    )


def region(value):
    value = re.sub(r"\s+\d{5}(?:-\d{4})?$", "", value).strip()
    return value.lower() in REGIONS or value.upper() in CODES


def address_parts(value):
    value = text(value, 240)
    if not value:
        return None, None
    parts = [part.strip() for part in value.split(",") if part.strip()]
    ambiguous = {"new york", "washington"}
    if not parts or (region(parts[0]) and parts[0].casefold() not in ambiguous):
        return None, None
    city = (
        parts[1]
        if len(parts) > 1
        and (
            not region(parts[1])
            or parts[1].casefold() in ambiguous
            or (len(parts) > 2 and region(parts[2]))
        )
        else None
    )
    return parts[0], city


def point_key(latitude, longitude):
    if (
        not all(
            isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
            for v in (latitude, longitude)
        )
        or not -90 <= latitude <= 90
        or not -180 <= longitude <= 180
    ):
        return None
    return sha256(f"{latitude:.4f},{longitude:.4f}".encode()).hexdigest()


def parse_result(data):
    if not isinstance(data, dict) or not isinstance(data.get("features"), list):
        return None
    for feature in data["features"][:3]:
        if not isinstance(feature, dict):
            continue
        props = feature.get("properties")
        if not isinstance(props, dict):
            continue
        city = text(props.get("city"))
        if (
            not city
            and props.get("osm_key") == "place"
            and props.get("osm_value") in ("city", "town", "village")
        ):
            city = text(props.get("name"))
        if city:
            return {"city": city, "street": text(props.get("street"))}
    return None


class CityLookup:
    def __init__(self, hass, store):
        self.hass, self.store = hass, store
        self.cache, self.requests, self.attempts = {}, [], {}
        self.task = None
        self.save_task = None
        self.closed = False

    async def load(self):
        try:
            data = await self.store.async_load() or {}
            self.cache = (
                data.get("cache", {}) if isinstance(data.get("cache"), dict) else {}
            )
            self.requests = (
                data.get("requests", [])
                if isinstance(data.get("requests"), list)
                else []
            )
        except Exception:
            # Fail closed if limits cannot be loaded; no unbounded retry after restart.
            self.closed = True
        self.prune(dt_util.utcnow())

    def prune(self, now):
        def date(value):
            parsed = dt_util.parse_datetime(value) if isinstance(value, str) else None
            return parsed if parsed and parsed.tzinfo else None

        self.cache = {
            key: item
            for key, item in self.cache.items()
            if isinstance(key, str)
            and re.fullmatch(r"[0-9a-f]{64}", key)
            and isinstance(item, dict)
            and text(item.get("city"))
            and (item.get("street") is None or text(item.get("street")))
            and (saved := date(item.get("saved_at")))
            and timedelta(0) <= now - saved < timedelta(days=7)
        }
        self.cache = dict(list(self.cache.items())[-256:])
        self.requests = [
            raw
            for raw in self.requests
            if (saved := date(raw)) and now - saved < timedelta(days=1)
        ][-200:]

    def cached(self, latitude, longitude):
        self.prune(dt_util.utcnow())
        return self.cache.get(point_key(latitude, longitude))

    def schedule(self, runtime):
        if (
            self.closed
            or not runtime.config.get("city_lookup_enabled")
            or (self.task and not self.task.done())
        ):
            return
        self.task = self.hass.async_create_background_task(
            self.update(runtime), "HomeCircle city lookup", eager_start=False
        )

    async def update(self, runtime):
        for member in runtime.household.members:
            if self.closed or not runtime.config.get("city_lookup_enabled"):
                return
            if member.place or not member.focusable or not member.location:
                continue
            point = member.location
            key = point_key(point.latitude, point.longitude)
            source = point.evidence.source_entity
            if source not in runtime.config.get("members", {}).get(member.id, {}).get(
                "trackers", []
            ):
                continue
            state = runtime.states.get(source)
            if (
                not key
                or not state
                or state.attributes.get("source_type") != "gps"
                or address_parts(state.attributes.get("address"))[1]
            ):
                continue
            now = dt_util.utcnow()
            self.prune(now)
            if key in self.cache or now - self.attempts.get(
                member.id, now - timedelta(days=1)
            ) < timedelta(minutes=5):
                continue
            recent = [
                raw
                for raw in self.requests
                if now - dt_util.parse_datetime(raw) < timedelta(hours=1)
            ]
            if len(recent) >= 20 or len(self.requests) >= 200:
                return
            self.attempts[member.id] = now
            self.requests.append(now.isoformat())
            # Persist the limit before transmitting. A failed save stops the service.
            try:
                await self.save()
            except Exception:
                self.closed = True
                return
            result = await self.fetch(point.latitude, point.longitude)
            if result:
                self.cache[key] = {**result, "saved_at": now.isoformat()}
                self.prune(now)
                try:
                    await self.save()
                except Exception:
                    self.closed = True
                    return
            await asyncio.sleep(1)

    async def fetch(self, latitude, longitude):
        try:
            session = async_get_clientsession(self.hass)
            async with asyncio.timeout(8):
                async with session.get(
                    "https://photon.komoot.io/reverse",
                    params={"lat": latitude, "lon": longitude, "limit": 3},
                    headers={
                        "User-Agent": "HomeCircle (https://github.com/jmhjr/HomeCircle)"
                    },
                    allow_redirects=False,
                ) as response:
                    if response.status != 200:
                        return None
                    raw = bytearray()
                    async for chunk in response.content.iter_chunked(8192):
                        raw.extend(chunk)
                        if len(raw) > 65536:
                            return None
                    return parse_result(json.loads(raw))
        except Exception:
            # Never log request URLs, coordinates or response bodies.
            return None

    async def save(self):
        self.save_task = self.hass.async_create_task(
            self.store.async_save({"cache": self.cache, "requests": self.requests}),
            "HomeCircle city cache save",
        )
        # A non-raising outcome also prevents noisy shield callbacks after cancellation.
        outcome = asyncio.gather(self.save_task, return_exceptions=True)
        result = (await asyncio.shield(outcome))[0]
        if isinstance(result, BaseException):
            raise result

    async def close(self):
        self.closed = True
        caller_cancelled = False
        if self.task and not self.task.done():
            self.task.cancel()
            outcome = asyncio.gather(self.task, return_exceptions=True)
            while True:
                try:
                    result = (await asyncio.shield(outcome))[0]
                    break
                except asyncio.CancelledError:
                    caller_cancelled = True
            if isinstance(result, BaseException) and not isinstance(
                result, asyncio.CancelledError
            ):
                raise result

        if self.save_task:
            # Finish the owned write before propagating cancellation of close().
            outcome = asyncio.gather(self.save_task, return_exceptions=True)
            while True:
                try:
                    result = (await asyncio.shield(outcome))[0]
                    break
                except asyncio.CancelledError:
                    caller_cancelled = True
            if isinstance(result, BaseException) and not isinstance(
                result, (Exception, asyncio.CancelledError)
            ):
                raise result
        if caller_cancelled:
            raise asyncio.CancelledError
