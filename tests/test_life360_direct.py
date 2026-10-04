"""Contract tests for direct Life360 projection using fictional server data."""

import asyncio
from datetime import datetime, timedelta, timezone
import threading
from unittest.mock import AsyncMock, Mock, patch

import pytest
from life360 import Life360Error, LoginError, NotModified, RateLimited, Unauthorized
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE

from custom_components.homecircle.life360_direct import (
    DirectLife360,
    Life360DirectTracker,
    member_name,
    new_session,
    parse_location,
    validate_account,
)


def test_direct_report_projection_keeps_only_needed_fields():
    raw = {
        "id": "example-member-id",
        "firstName": "Example",
        "lastName": "Member",
        "avatar": "https://example.invalid/private.png",
        "features": {"shareLocation": "1"},
        "location": {
            ATTR_LATITUDE: str(1),
            ATTR_LONGITUDE: str(2),
            "accuracy": "10",
            "timestamp": "1760000000",
            "battery": "42",
            "charge": "1",
            "isDriving": "0",
            "speed": "2",
            "address1": "private address excluded",
        },
    }
    assert member_name(raw) == "Example Member"
    projected = parse_location(raw)
    assert projected["latitude"] == 1
    assert projected["longitude"] == 2
    assert projected["accuracy"] == 3.048
    assert projected["battery_level"] == 42
    assert projected["battery_charging"] is True
    assert "address" not in str(projected)
    tracker = Life360DirectTracker("example-member-id", raw)
    assert tracker.name == "Life360 Example Member"
    assert tracker.available
    assert tracker.extra_state_attributes["last_seen"]
    assert "private" not in str(tracker.extra_state_attributes)


def test_direct_report_rejects_nonsharing_and_bad_coordinates():
    raw = {
        "features": {"shareLocation": "0"},
        "location": {ATTR_LATITUDE: str(1), ATTR_LONGITUDE: str(2)},
    }
    assert parse_location(raw) is None
    raw["features"]["shareLocation"] = "1"
    raw["location"][ATTR_LATITUDE] = str(999)
    assert parse_location(raw) is None
    raw["location"][ATTR_LATITUDE] = True
    assert parse_location(raw) is None


def test_direct_missing_flags_stay_unknown():
    raw = {"location": {ATTR_LATITUDE: str(1), ATTR_LONGITUDE: str(2)}}
    projected = parse_location(raw)
    assert projected["battery_charging"] is None
    assert projected["driving"] is None


def test_disabled_tracker_does_not_write_or_interrupt_other_trackers():
    raw = {"location": {ATTR_LATITUDE: "1", ATTR_LONGITUDE: "2"}}
    disabled = Life360DirectTracker("example-disabled", raw)
    disabled.entity_id = "device_tracker.example_disabled"
    disabled.hass = None  # HA clears this when a registered entity is disabled.
    disabled.update(raw)
    disabled.mark_unavailable()

    enabled = Life360DirectTracker("example-enabled", raw)
    enabled.entity_id = "device_tracker.example_enabled"
    enabled.hass = Mock()
    with patch.object(enabled, "async_write_ha_state") as write:
        enabled.update(raw)
    write.assert_called_once()


async def test_tls_context_is_created_outside_event_loop():
    event_loop_thread = threading.get_ident()
    created_on = []
    from custom_components.homecircle import life360_direct

    real_create = life360_direct.ssl.create_default_context

    def record_thread():
        created_on.append(threading.get_ident())
        return real_create()

    with patch.object(life360_direct.ssl, "create_default_context", record_thread):
        session = await new_session()
    await session.close()
    assert created_on and created_on[0] != event_loop_thread


async def test_account_validation_keeps_only_fingerprint():
    profile = {"id": "fictional-account", "firstName": "Private"}
    with (
        patch("custom_components.homecircle.life360_direct.new_session") as session,
        patch("custom_components.homecircle.life360_direct.Life360") as life360,
    ):
        session.return_value.__aenter__ = AsyncMock(return_value=Mock())
        session.return_value.__aexit__ = AsyncMock(return_value=None)
        life360.return_value.get_me = AsyncMock(return_value=profile)
        fingerprint = await validate_account(
            {"method": "token", "username": "", "secret": "fictional-token"}
        )
    assert len(fingerprint) == 64
    assert "fictional-account" not in fingerprint


async def test_discovery_and_poll_do_not_require_third_party_entities(hass):
    raw = {
        "id": "example-member-id",
        "firstName": "Example",
        "lastName": "Member",
        "features": {"shareLocation": "1"},
        "location": {
            ATTR_LATITUDE: str(1),
            ATTR_LONGITUDE: str(2),
            "timestamp": "1760000000",
        },
    }

    class FakeAPI:
        async def get_circles(self):
            return [{"id": "example-circle"}]

        async def get_circle_members(self, _circle):
            return [raw]

        async def get_circle_member(self, _circle, _member):
            return raw

    added = []
    client = DirectLife360(hass, {}, added.extend)
    client.api = FakeAPI()
    await client.async_refresh()
    assert len(added) == 1
    assert added[0].member_id == "example-member-id"
    assert added[0].available
    await client.async_refresh()
    assert len(added) == 1


async def test_rate_limit_pauses_requests(hass):
    class LimitedAPI:
        calls = 0

        async def get_circles(self):
            self.calls += 1
            raise RateLimited("limited", 600)

    client = DirectLife360(hass, {}, lambda _: None)
    client.api = LimitedAPI()
    await client.async_refresh()
    await client.async_refresh()
    assert client.api.calls == 1
    assert client.health_snapshot().state == "rate_limited"


async def test_member_shared_in_two_circles_uses_visible_location(hass):
    hidden = {
        "id": "example-member-id",
        "firstName": "Example",
        "features": {"shareLocation": "0"},
        "location": None,
    }
    visible = {
        **hidden,
        "features": {"shareLocation": "1"},
        "location": {ATTR_LATITUDE: str(1), ATTR_LONGITUDE: str(2)},
    }

    class FakeAPI:
        async def get_circles(self):
            return [{"id": "example-first"}, {"id": "example-second"}]

        async def get_circle_members(self, circle):
            return [hidden if circle == "example-first" else visible]

        async def get_circle_member(self, circle, _member):
            return hidden if circle == "example-first" else visible

    added = []
    client = DirectLife360(hass, {}, added.extend)
    client.api = FakeAPI()
    await client.async_refresh()
    assert len(added) == 1
    assert added[0].available
    assert added[0].latitude == 1


async def test_nonsharing_member_is_unavailable_without_api_shape_error(hass):
    hidden = {
        "id": "example-member-id",
        "features": {"shareLocation": "0"},
        "location": {ATTR_LATITUDE: "invalid", ATTR_LONGITUDE: "invalid"},
    }

    class FakeAPI:
        async def get_circles(self):
            return [{"id": "example-circle"}]

        async def get_circle_members(self, _circle):
            return [hidden]

        async def get_circle_member(self, _circle, _member):
            return hidden

    client = DirectLife360(hass, {}, lambda _: None)
    client.api = FakeAPI()
    await client.async_refresh()
    assert not client.trackers["example-member-id"].available
    assert client.health_snapshot().state == "connected"


async def test_unchanged_report_keeps_connection_fresh(hass):
    raw = {
        "id": "example-member-id",
        "location": {ATTR_LATITUDE: str(1), ATTR_LONGITUDE: str(2)},
    }

    class FakeAPI:
        async def get_circles(self):
            return [{"id": "example-circle"}]

        async def get_circle_members(self, _circle):
            return [raw]

        async def get_circle_member(self, _circle, _member):
            raise NotModified()

    client = DirectLife360(hass, {}, lambda _: None)
    client.api = FakeAPI()
    await client.async_refresh()
    client._last_success["example-member-id"] -= timedelta(minutes=4)
    old_success = client._last_success["example-member-id"]
    await client.async_refresh()
    assert client._last_success["example-member-id"] > old_success


async def test_new_circle_member_appears_on_periodic_discovery(hass):
    first = {
        "id": "example-first",
        "location": {ATTR_LATITUDE: str(1), ATTR_LONGITUDE: str(2)},
    }
    second = {**first, "id": "example-second"}

    class FakeAPI:
        def __init__(self):
            self.members = [first]
            self.discoveries = 0

        async def get_circles(self):
            self.discoveries += 1
            return [{"id": "example-circle"}]

        async def get_circle_members(self, _circle):
            return self.members

        async def get_circle_member(self, _circle, member_id):
            return next(raw for raw in self.members if raw["id"] == member_id)

    added = []
    client = DirectLife360(hass, {}, added.extend)
    client.api = FakeAPI()
    await client.async_refresh()
    assert [tracker.member_id for tracker in added] == ["example-first"]
    client.api.members.append(second)
    await client.async_refresh()
    assert client.api.discoveries == 1
    client._next_discovery = datetime.min.replace(tzinfo=timezone.utc)
    await client.async_refresh()
    assert client.api.discoveries == 2
    assert {tracker.member_id for tracker in added} == {
        "example-first",
        "example-second",
    }


async def test_one_circle_discovery_failure_keeps_known_members_polling(hass):
    first = {
        "id": "example-first",
        "location": {ATTR_LATITUDE: str(1), ATTR_LONGITUDE: str(2)},
    }
    second = {**first, "id": "example-second"}

    class FakeAPI:
        mode = "normal"
        polled = []

        async def get_circles(self):
            return [{"id": "example-first-circle"}, {"id": "example-second-circle"}]

        async def get_circle_members(self, circle):
            if circle == "example-first-circle":
                if self.mode == "malformed":
                    return [{"unexpected": "shape"}]
                if self.mode == "failed":
                    raise Life360Error("fictional Circle failure")
                return [first]
            return [second]

        async def get_circle_member(self, _circle, member_id):
            self.polled.append(member_id)
            return first if member_id == "example-first" else second

    client = DirectLife360(hass, {}, lambda _: None)
    client.api = FakeAPI()
    await client.async_refresh()
    assert len(client.trackers) == 2

    for mode, expected in (
        ("malformed", "unexpected_response"),
        ("failed", "partial"),
        ("normal", "connected"),
    ):
        client.api.mode = mode
        client.api.polled.clear()
        client._next_discovery = datetime.min.replace(tzinfo=timezone.utc)
        await client.async_refresh()
        assert client.health_snapshot().state == expected
        assert set(client.api.polled) == {"example-first", "example-second"}
        assert all(tracker.available for tracker in client.trackers.values())
        if mode != "normal":
            assert client._next_discovery - datetime.now(timezone.utc) <= timedelta(
                seconds=60
            )


async def test_one_failed_member_becomes_unavailable_independently(hass):
    first = {
        "id": "example-first",
        "location": {ATTR_LATITUDE: str(1), ATTR_LONGITUDE: str(2)},
    }
    second = {**first, "id": "example-second"}

    class FakeAPI:
        async def get_circles(self):
            return [{"id": "example-circle"}]

        async def get_circle_members(self, _circle):
            return [first, second]

        async def get_circle_member(self, _circle, member_id):
            if member_id == "example-second":
                raise Life360Error("fictional failure")
            return first

    client = DirectLife360(hass, {}, lambda _: None)
    client.api = FakeAPI()
    await client.async_refresh()
    client._last_success["example-second"] -= timedelta(minutes=6)
    await client.async_refresh()
    assert client.trackers["example-first"].available
    assert not client.trackers["example-second"].available
    assert client.health_snapshot().state == "partial"


@pytest.mark.parametrize(
    "changed_reply",
    [
        ["changed response shape"],
        {"id": "example-first", "location": {ATTR_LATITUDE: "invalid", ATTR_LONGITUDE: "2"}},
        {"id": "example-first", "location": {ATTR_LATITUDE: True, ATTR_LONGITUDE: "2"}},
    ],
)
async def test_changed_member_response_does_not_stop_other_trackers(
    hass, changed_reply
):
    first = {
        "id": "example-first",
        "location": {ATTR_LATITUDE: str(1), ATTR_LONGITUDE: str(2)},
    }
    second = {**first, "id": "example-second"}

    class FakeAPI:
        malformed = True

        async def get_circles(self):
            return [{"id": "example-circle"}]

        async def get_circle_members(self, _circle):
            return [first, second]

        async def get_circle_member(self, _circle, member_id):
            if member_id == "example-first" and self.malformed:
                return changed_reply
            return first if member_id == "example-first" else second

    client = DirectLife360(hass, {}, lambda _: None)
    client.api = FakeAPI()
    await client.async_refresh()
    assert client.health_snapshot().state == "unexpected_response"
    client._last_success["example-first"] -= timedelta(minutes=6)
    await client.async_refresh()
    assert not client.trackers["example-first"].available
    assert client.trackers["example-second"].available
    assert client.health_snapshot().state == "unexpected_response"

    client.api.malformed = False
    await client.async_refresh()
    assert client.trackers["example-first"].available
    assert client.health_snapshot().state == "connected"


async def test_unexpected_api_shape_has_safe_health_code(hass):
    class ChangedAPI:
        async def get_circles(self):
            return [{"unexpected": "shape"}]

    client = DirectLife360(hass, {"secret": "example-secret"}, lambda _: None)
    client.api = ChangedAPI()
    await client.async_refresh()
    health = client.health_snapshot().as_dict()
    assert health["state"] == "unexpected_response"
    assert "example-secret" not in str(health)


async def test_authorization_failure_starts_repair_flow(hass):
    entry = Mock()
    client = DirectLife360(hass, {}, lambda _: None, entry_id="example-entry")
    client.session = Mock()
    with (
        patch(
            "custom_components.homecircle.life360_direct.authorized_client",
            new_callable=AsyncMock,
            side_effect=Unauthorized("fictional rejection", None),
        ),
        patch.object(hass.config_entries, "async_get_entry", return_value=entry),
    ):
        await client.async_refresh()
    entry.async_start_reauth.assert_called_once_with(
        hass, data={"_homecircle_reauth_provider": "life360"}
    )
    assert client.health_snapshot().state == "auth_required"


async def test_rejected_credentials_wait_for_repair_without_retrying(hass):
    entry = Mock()
    client = DirectLife360(hass, {}, lambda _: None, entry_id="example-entry")
    client.session = Mock()
    with (
        patch(
            "custom_components.homecircle.life360_direct.authorized_client",
            new_callable=AsyncMock,
            side_effect=Unauthorized("fictional rejection", None),
        ) as authorize,
        patch.object(hass.config_entries, "async_get_entry", return_value=entry),
    ):
        await client.async_refresh()
        await client.async_refresh()
    assert authorize.await_count == 1
    entry.async_start_reauth.assert_called_once()


@pytest.mark.parametrize("failure", [Unauthorized, LoginError])
async def test_one_circle_access_failure_keeps_other_members_fresh(hass, failure):
    raw = {
        "id": "example-member",
        "location": {ATTR_LATITUDE: "1", ATTR_LONGITUDE: "2"},
    }

    class RestrictedAPI:
        async def get_circles(self):
            return [{"id": "restricted"}, {"id": "accessible"}]

        async def get_circle_members(self, circle):
            if circle == "restricted":
                if failure is Unauthorized:
                    raise failure("fictional access rejection", None)
                raise failure("fictional access rejection")
            return [raw]

        async def get_circle_member(self, _circle, _member):
            return raw

    client = DirectLife360(hass, {}, lambda _: None)
    client.api = RestrictedAPI()
    await client.async_refresh()
    assert client.trackers["example-member"].available
    assert client.health_snapshot().state == "partial"
    assert client.api is not None


async def test_one_member_access_failure_keeps_other_members_fresh(hass):
    first = {
        "id": "example-first",
        "location": {ATTR_LATITUDE: "1", ATTR_LONGITUDE: "2"},
    }
    second = {**first, "id": "example-second"}

    class RestrictedAPI:
        async def get_circles(self):
            return [{"id": "example-circle"}]

        async def get_circle_members(self, _circle):
            return [first, second]

        async def get_circle_member(self, _circle, member):
            if member == "example-first":
                raise Unauthorized("fictional access rejection", None)
            return second

    client = DirectLife360(hass, {}, lambda _: None)
    client.api = RestrictedAPI()
    await client.async_refresh()
    assert client.health_snapshot().state == "partial"
    assert client.trackers["example-second"].available
    assert client.api is not None


async def test_all_members_denied_rechecks_sign_in_then_requests_repair(hass):
    class DeniedAPI:
        async def get_circles(self):
            return [{"id": "example-circle"}]

        async def get_circle_members(self, _circle):
            return [{"id": "example-first"}, {"id": "example-second"}]

        async def get_circle_member(self, _circle, _member):
            raise Unauthorized("fictional member denial", None)

        async def get_me(self):
            raise Unauthorized("fictional account denial", None)

    entry = Mock()
    client = DirectLife360(hass, {}, lambda _: None, entry_id="example-entry")
    client.api = DeniedAPI()
    client.session = Mock()
    with (
        patch(
            "custom_components.homecircle.life360_direct.authorized_client",
            new_callable=AsyncMock,
            side_effect=Unauthorized("fictional sign-in rejection", None),
        ) as authorize,
        patch.object(hass.config_entries, "async_get_entry", return_value=entry),
    ):
        await client.async_refresh()
        await client.async_refresh()
    authorize.assert_awaited_once()
    entry.async_start_reauth.assert_called_once()
    assert client.health_snapshot().state == "auth_required"


async def test_all_members_denied_but_account_valid_does_not_request_repair(hass):
    class RestrictedAPI:
        profile_checks = 0

        async def get_circles(self):
            return [{"id": "example-circle"}]

        async def get_circle_members(self, _circle):
            return [{"id": "example-member"}]

        async def get_circle_member(self, _circle, _member):
            raise Unauthorized("fictional member denial", None)

        async def get_me(self):
            self.profile_checks += 1
            return {"id": "fictional-account"}

    entry = Mock()
    client = DirectLife360(hass, {}, lambda _: None, entry_id="example-entry")
    client.api = RestrictedAPI()
    with patch.object(hass.config_entries, "async_get_entry", return_value=entry):
        await client.async_refresh()
        await client.async_refresh()
    assert client.api.profile_checks == 1
    assert client.health_snapshot().state == "api_error"
    entry.async_start_reauth.assert_not_called()


async def test_stop_cancels_interval_refresh_before_closing_session(hass):
    entered = asyncio.Event()
    cancelled = asyncio.Event()

    class SlowAPI:
        async def get_circles(self):
            entered.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                raise

    client = DirectLife360(hass, {}, lambda _: None)
    client.api = SlowAPI()
    client.session = Mock(close=AsyncMock())
    interval = asyncio.create_task(client._interval(None))
    await entered.wait()
    await client.async_stop()
    assert interval.cancelled()
    assert cancelled.is_set()
    assert client.session is None


async def test_circle_access_rejection_rechecks_login_before_repair(hass):
    class RejectedAPI:
        async def get_circles(self):
            raise Unauthorized("fictional circle rejection", None)

    entry = Mock()
    client = DirectLife360(hass, {}, lambda _: None, entry_id="example-entry")
    client.api = RejectedAPI()
    with patch.object(hass.config_entries, "async_get_entry", return_value=entry):
        await client.async_refresh()
    assert client.health_snapshot().state == "api_error"
    assert client.api is None
    entry.async_start_reauth.assert_not_called()
