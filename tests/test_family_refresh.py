"""Full Circle scope, atomic request limits and evidence feedback."""

import asyncio
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.homecircle.family_refresh import (
    async_refresh_family,
    family_status,
)
from custom_components.homecircle.location_requests import (
    MAX_REQUESTS,
    async_reserve_request,
)


def fixture():
    now = datetime.now(UTC)
    members = [
        NS(
            id=f"person.example_member{i}",
            location=NS(
                evidence=NS(
                    source_entity=f"device_tracker.example_member{i}",
                    reported_at=now - timedelta(minutes=20),
                )
            ),
        )
        for i in range(2)
    ]
    registered = {
        f"device_tracker.example_member{i}": NS(
            platform="life360",
            disabled=False,
            config_entry_id="external",
            unique_id=f"member-{i}",
        )
        for i in range(2)
    }
    circle = NS(mids={"member-0", "member-1"}, aids={"account"})
    entry = NS(
        entry_id="external",
        options={
            "accounts": {"account": {"authorization": "fictional", "enabled": True}}
        },
        runtime_data=NS(coordinator=NS(data=NS(circles={"fictional-circle": circle}))),
    )
    registry = NS(async_get=registered.get)
    hass = NS(config_entries=NS(async_get_entry=lambda _: entry))
    runtime = NS(
        household=NS(members=members),
        config={
            "family_refresh_enabled": True,
            "members": {
                m.id: {"trackers": [m.location.evidence.source_entity]} for m in members
            },
        },
        location_request_store=NS(async_save=AsyncMock()),
        location_request_times={},
        last_location_request={},
        restored_location_requests=set(),
        family_refresh={},
        provider_controls=NS(paused=lambda *_: False, operation=lambda *_: nullcontext()),
    )
    user = NS(permissions=NS(check_entity=lambda *_: True))
    return hass, runtime, user, registry, circle


async def test_complete_circle_permission_and_scope_fail_before_send():
    h, r, u, reg, c = fixture()
    with (
        patch(
            "custom_components.homecircle.family_refresh.er.async_get", return_value=reg
        ),
        patch(
            "custom_components.homecircle.family_refresh.async_send",
            new_callable=AsyncMock,
        ) as send,
    ):
        c.mids.add("unselected")
        assert (await async_refresh_family(h, r, u))["status"] == "unsupported"
        c.mids.remove("unselected")
        u.permissions.check_entity = lambda entity, *_: entity.endswith("0")
        assert (await async_refresh_family(h, r, u))["status"] == "not_allowed"
        assert not r.location_request_times
        send.assert_not_awaited()


async def test_concurrent_clicks_single_send_and_shared_individual_limit():
    h, r, u, reg, c = fixture()
    with (
        patch(
            "custom_components.homecircle.family_refresh.er.async_get", return_value=reg
        ),
        patch(
            "custom_components.homecircle.family_refresh.async_send",
            new_callable=AsyncMock,
            return_value=True,
        ) as send,
    ):
        results = await asyncio.gather(
            async_refresh_family(h, r, u), async_refresh_family(h, r, u)
        )
        assert sorted(x["status"] for x in results) == ["cooldown", "requested"]
        assert send.await_count == 1
        assert (
            await async_reserve_request(
                r, "device_tracker.example_member0", datetime.now(UTC)
            )
            == "reserved"
        )
        assert len(r.location_request_times) == 2


async def test_save_failure_rolls_back_every_source_and_failed_send_consumes_cap():
    h, r, u, reg, c = fixture()
    with (
        patch(
            "custom_components.homecircle.family_refresh.er.async_get", return_value=reg
        ),
        patch(
            "custom_components.homecircle.family_refresh.async_send",
            new_callable=AsyncMock,
            return_value=False,
        ) as send,
    ):
        r.location_request_store.async_save.side_effect = OSError
        assert (await async_refresh_family(h, r, u))["status"] == "unavailable"
        assert not any(r.location_request_times.values())
        send.assert_not_awaited()
        r.location_request_store.async_save.side_effect = None
        assert (await async_refresh_family(h, r, u))["status"] == "send_failed"
        assert (await async_refresh_family(h, r, u))["status"] == "cooldown"
        assert send.await_count == 1


async def test_feedback_new_report_same_source_only_and_observation_expires():
    h, r, u, reg, c = fixture()
    with (
        patch(
            "custom_components.homecircle.family_refresh.er.async_get", return_value=reg
        ),
        patch(
            "custom_components.homecircle.family_refresh.async_send",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        await async_refresh_family(h, r, u)
    assert [m["status"] for m in family_status(h, r, reg)["members"]] == [
        "waiting",
        "waiting",
    ]
    r.household.members[0].location.evidence.reported_at = datetime.now(UTC)
    family_status(h, r, reg)  # Latch the report while the observation is open.
    r.family_refresh["started"] -= timedelta(seconds=121)
    status = family_status(h, r, reg)
    assert status["status"] == "complete"
    assert [m["status"] for m in status["members"]] == ["updated", "unchanged"]
    r.config["members"][r.household.members[0].id]["trackers"] = [
        "device_tracker.example_other"
    ]
    assert family_status(h, r, reg)["members"][0]["status"] == "updated"


async def test_saved_limits_survive_new_runtime_and_enforce_daily_cap():
    h, r, u, reg, c = fixture()
    with (
        patch(
            "custom_components.homecircle.family_refresh.er.async_get", return_value=reg
        ),
        patch(
            "custom_components.homecircle.family_refresh.async_send",
            new_callable=AsyncMock,
            return_value=True,
        ) as send,
    ):
        await async_refresh_family(h, r, u)
        persisted = r.location_request_store.async_save.call_args.args[0]["requests"]
        _, other, _, _, _ = fixture()
        other.location_request_times = {
            k: [datetime.fromisoformat(t) - timedelta(hours=2) for t in v]
            for k, v in persisted.items()
        }
        assert (await async_refresh_family(h, other, u))["status"] == "requested"
        for key in other.location_request_times:
            other.location_request_times[key] = [
                t - timedelta(hours=2) for t in other.location_request_times[key]
            ]
        for key in other.location_request_times:
            other.location_request_times[key] += [
                datetime.now(UTC) - timedelta(hours=3, minutes=i)
                for i in range(MAX_REQUESTS - 2)
            ]
        blocked = await async_refresh_family(h, other, u)
        assert blocked["status"] == "limited"
        assert datetime.fromisoformat(blocked["retry_at"]) > datetime.now(UTC)
        assert send.await_count == 2


async def test_source_change_during_limit_save_prevents_old_circle_dispatch():
    h, r, u, reg, c = fixture()

    async def save(_):
        r.config["members"][r.household.members[0].id]["trackers"] = [
            "device_tracker.example_other"
        ]

    r.location_request_store.async_save.side_effect = save
    with (
        patch(
            "custom_components.homecircle.family_refresh.er.async_get", return_value=reg
        ),
        patch(
            "custom_components.homecircle.family_refresh.async_send",
            new_callable=AsyncMock,
        ) as send,
    ):
        assert (await async_refresh_family(h, r, u))["status"] == "unsupported"
        send.assert_not_awaited()


async def test_person_fallback_still_uses_explicit_selected_life360_tracker():
    h, r, u, reg, c = fixture()
    for member in r.household.members:
        member.location.evidence.source_entity = member.id
    assert family_status(h, r, reg)["available"] is True
    with (
        patch(
            "custom_components.homecircle.family_refresh.er.async_get", return_value=reg
        ),
        patch(
            "custom_components.homecircle.family_refresh.async_send",
            new_callable=AsyncMock,
            return_value=True,
        ) as send,
    ):
        assert (await async_refresh_family(h, r, u))["status"] == "requested"
        assert send.await_count == 1
        assert all(
            t["source"].startswith("device_tracker.")
            for t in r.family_refresh["targets"]
        )


async def test_manual_request_ignores_existing_individual_caps_and_preserves_them():
    h, r, u, reg, c = fixture()
    prior = [
        *[
            datetime.now(UTC) - timedelta(hours=2, seconds=i)
            for i in range(MAX_REQUESTS)
        ],
    ]
    for member in r.household.members:
        r.location_request_times[member.location.evidence.source_entity] = list(prior)
    with (
        patch(
            "custom_components.homecircle.family_refresh.er.async_get", return_value=reg
        ),
        patch(
            "custom_components.homecircle.family_refresh.async_send",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        assert (await async_refresh_family(h, r, u))["status"] == "requested"
    for member in r.household.members:
        assert r.location_request_times[member.location.evidence.source_entity] == prior
        assert (
            await async_reserve_request(
                r, member.location.evidence.source_entity, datetime.now(UTC)
            )
            == "limited"
        )
    status = family_status(h, r, reg)
    assert datetime.fromisoformat(status["next_available_at"]) == r.family_refresh[
        "started"
    ] + timedelta(minutes=1)


def test_manual_next_available_rolls_over_at_exact_boundary():
    from custom_components.homecircle.family_refresh import next_available

    now = datetime.now(UTC)
    r = NS(location_request_times={"family:example": [now - timedelta(minutes=1)]})
    assert next_available(r, "family:example", now) is None
    r.location_request_times["family:example"] = [
        now - timedelta(hours=23, minutes=i) for i in range(MAX_REQUESTS)
    ]
    assert next_available(r, "family:example", now) == min(
        r.location_request_times["family:example"]
    ) + timedelta(days=1)


async def test_family_allows_fiftieth_attempt_and_one_minute_boundary():
    h, r, u, reg, _ = fixture()
    now = datetime.now(UTC)
    with (
        patch(
            "custom_components.homecircle.family_refresh.er.async_get", return_value=reg
        ),
        patch(
            "custom_components.homecircle.family_refresh.dt_util.utcnow",
            return_value=now,
        ),
        patch(
            "custom_components.homecircle.family_refresh.async_send",
            new_callable=AsyncMock,
            return_value=True,
        ) as send,
    ):
        assert (await async_refresh_family(h, r, u))["status"] == "requested"
        key = next(k for k in r.location_request_times if k.startswith("family:"))
        r.location_request_times[key] = [
            now - timedelta(hours=2, seconds=i) for i in range(48)
        ] + [now - timedelta(seconds=59)]
        assert (await async_refresh_family(h, r, u))["status"] == "cooldown"
        r.location_request_times[key][-1] = now - timedelta(minutes=1)
        assert (await async_refresh_family(h, r, u))["status"] == "requested"
        assert len(r.location_request_times[key]) == 50
        assert (await async_refresh_family(h, r, u))["status"] == "limited"
        assert send.await_count == 2


async def test_late_reports_cannot_rewrite_results_and_feedback_expires():
    h, r, u, reg, _ = fixture()
    now = datetime.now(UTC)
    with (
        patch(
            "custom_components.homecircle.family_refresh.er.async_get", return_value=reg
        ),
        patch(
            "custom_components.homecircle.family_refresh.async_send",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "custom_components.homecircle.family_refresh.dt_util.utcnow",
            return_value=now,
        ),
    ):
        await async_refresh_family(h, r, u)
    # No open dashboard is required: the state observer latches a timely report.
    from custom_components.homecircle.family_refresh import observe_family_refresh

    r.household.members[0].location.evidence.reported_at = now + timedelta(seconds=10)
    observe_family_refresh(r, now + timedelta(seconds=15))
    r.household.members[1].location.evidence.reported_at = now + timedelta(seconds=30)
    # Even a backdated report first observed at the deadline is too late.
    with patch(
        "custom_components.homecircle.family_refresh.dt_util.utcnow",
        return_value=now + timedelta(minutes=2),
    ):
        result = family_status(h, r, reg)
    assert result["status"] == "complete"
    assert [m["status"] for m in result["members"]] == ["updated", "unchanged"]
    with patch(
        "custom_components.homecircle.family_refresh.dt_util.utcnow",
        return_value=now + timedelta(minutes=6, seconds=59),
    ):
        assert family_status(h, r, reg)["members"] == result["members"]
    with patch(
        "custom_components.homecircle.family_refresh.dt_util.utcnow",
        return_value=now + timedelta(minutes=7),
    ):
        result = family_status(h, r, reg)
    assert result["status"] == "idle"
    assert not result["members"]
    assert r.location_request_times  # Expiry never resets the request budget.


async def test_failed_family_feedback_also_expires():
    h, r, u, reg, _ = fixture()
    now = datetime.now(UTC)
    with (
        patch(
            "custom_components.homecircle.family_refresh.er.async_get", return_value=reg
        ),
        patch(
            "custom_components.homecircle.family_refresh.async_send",
            new_callable=AsyncMock,
            return_value=False,
        ),
        patch(
            "custom_components.homecircle.family_refresh.dt_util.utcnow",
            return_value=now,
        ),
    ):
        assert (await async_refresh_family(h, r, u))["status"] == "send_failed"
    with patch(
        "custom_components.homecircle.family_refresh.dt_util.utcnow",
        return_value=now + timedelta(minutes=5),
    ):
        assert family_status(h, r, reg)["status"] == "idle"


async def test_family_refresh_requires_explicit_opt_in_before_credentials_or_send():
    h, r, u, reg, _ = fixture()
    for enabled in (None, False, "true"):
        r.config["family_refresh_enabled"] = enabled
        with (
            patch(
                "custom_components.homecircle.family_refresh.er.async_get",
                return_value=reg,
            ),
            patch(
                "custom_components.homecircle.family_refresh.async_send",
                new_callable=AsyncMock,
            ) as send,
        ):
            assert family_status(h, r, reg)["available"] is False
            assert (await async_refresh_family(h, r, u))["status"] == "unsupported"
            assert not r.location_request_times
            send.assert_not_awaited()


def mixed_fixture():
    h, r, u, reg, circle = fixture()
    phone = "device_tracker.example_phone"
    notify = "notify.example_phone"
    registry = {
        source: reg.async_get(source)
        for source in r.config["members"][r.household.members[0].id]["trackers"]
        + r.config["members"][r.household.members[1].id]["trackers"]
    }
    for entry in registry.values():
        entry.device_id = None
    registry[phone] = NS(
        platform="mobile_app",
        disabled=False,
        config_entry_id="phone-entry",
        unique_id="phone",
        device_id="phone-device",
        domain="device_tracker",
    )
    registry[notify] = NS(
        platform="mobile_app",
        disabled=False,
        domain="notify",
        device_id="phone-device",
        entity_id=notify,
    )
    reg.entities = registry
    reg.async_get = registry.get
    r.config["members"][r.household.members[0].id].update(
        trackers=[phone], auto_request_location=True
    )
    h.states = NS(get=lambda entity: NS(state="unknown") if entity == notify else None)
    h.services = NS(has_service=lambda *_: True, async_call=AsyncMock())
    r.selection_refresh_times = {}
    return h, r, u, reg, circle, phone, notify


async def test_mixed_assigned_sources_refresh_without_map_source_or_full_circle():
    h, r, u, reg, _, phone, notify = mixed_fixture()
    # The phone is assigned even though the normalized map still uses another source.
    with (
        patch(
            "custom_components.homecircle.family_refresh.er.async_get", return_value=reg
        ),
        patch(
            "custom_components.homecircle.family_refresh.async_send",
            new_callable=AsyncMock,
        ) as circle_send,
    ):
        assert family_status(h, r, reg)["available"]
        assert (await async_refresh_family(h, r, u))["status"] == "requested"
    assert h.services.async_call.await_args_list[0].args == (
        "notify",
        "send_message",
        {"entity_id": notify, "message": "request_location_update"},
    )
    assert h.services.async_call.await_args_list[1].args == (
        "life360",
        "update_location",
        {"entity_id": ["device_tracker.example_member1"]},
    )
    circle_send.assert_not_awaited()
    assert {t["source"] for t in r.family_refresh["targets"]} == {
        phone,
        "device_tracker.example_member1",
    }


async def test_mixed_concurrency_and_individual_phone_budget_are_shared():
    h, r, u, reg, _, phone, _ = mixed_fixture()
    with patch(
        "custom_components.homecircle.family_refresh.er.async_get", return_value=reg
    ):
        results = await asyncio.gather(
            async_refresh_family(h, r, u), async_refresh_family(h, r, u)
        )
    assert sorted(result["status"] for result in results) == ["cooldown", "requested"]
    assert h.services.async_call.await_count == 2
    assert await async_reserve_request(r, phone, datetime.now(UTC)) == "cooldown"


async def test_one_limited_or_failed_source_does_not_block_other_provider():
    h, r, u, reg, _, phone, _ = mixed_fixture()
    r.location_request_times[phone] = [
        datetime.now(UTC) - timedelta(hours=2, seconds=i) for i in range(MAX_REQUESTS)
    ]
    with patch(
        "custom_components.homecircle.family_refresh.er.async_get", return_value=reg
    ):
        assert (await async_refresh_family(h, r, u))["status"] == "requested"
    assert h.services.async_call.await_count == 1
    assert h.services.async_call.await_args.args[0] == "life360"
    assert r.family_refresh["members"][0]["status"] == "limited"
    h, r, u, reg, _, phone, _ = mixed_fixture()
    h.services.async_call.side_effect = [OSError(), None]
    with patch(
        "custom_components.homecircle.family_refresh.er.async_get", return_value=reg
    ):
        assert (await async_refresh_family(h, r, u))["status"] == "requested"
    assert r.family_refresh["members"][0]["status"] == "send_failed"
    assert len(r.location_request_times[phone]) == 1


async def test_disabled_phone_and_unknown_provider_are_explicitly_skipped():
    h, r, u, reg, _, phone, _ = mixed_fixture()
    r.config["members"][r.household.members[0].id]["auto_request_location"] = False
    reg.async_get("device_tracker.example_member1").platform = "unsupported_provider"
    # Keep one supported target and show disabled/unsupported results alongside it.
    extra = "device_tracker.example_extra"
    reg.entities[extra] = NS(
        platform="life360",
        disabled=False,
        config_entry_id="external",
        unique_id="extra",
    )
    r.config["members"][r.household.members[1].id]["trackers"].append(extra)
    with patch(
        "custom_components.homecircle.family_refresh.er.async_get", return_value=reg
    ):
        assert (await async_refresh_family(h, r, u))["status"] == "requested"
    assert h.services.async_call.await_count == 1
    assert h.services.async_call.await_args.args[2] == {"entity_id": [extra]}
    assert r.family_refresh["members"][0]["status"] == "disabled"
    assert [t["outcome"] for t in r.family_refresh["targets"]] == [
        "disabled",
        "unsupported",
        "waiting",
    ]


async def test_phone_notification_permission_prevents_every_dispatch():
    h, r, u, reg, _, _, notify = mixed_fixture()
    u.permissions.check_entity = lambda entity, *_: entity != notify
    with patch(
        "custom_components.homecircle.family_refresh.er.async_get", return_value=reg
    ):
        assert (await async_refresh_family(h, r, u))["status"] == "not_allowed"
    assert not r.location_request_times
    h.services.async_call.assert_not_awaited()


async def test_config_change_during_second_reservation_never_sends_removed_phone():
    h, r, u, reg, _, phone, _ = mixed_fixture()
    saves = 0

    async def save(_):
        nonlocal saves
        saves += 1
        if saves == 2:
            r.config["members"][r.household.members[0].id]["trackers"] = []

    r.location_request_store.async_save.side_effect = save
    with patch(
        "custom_components.homecircle.family_refresh.er.async_get", return_value=reg
    ):
        assert (await async_refresh_family(h, r, u))["status"] == "requested"
    assert h.services.async_call.await_count == 1
    assert h.services.async_call.await_args.args[0] == "life360"
    assert r.family_refresh["members"][0]["status"] == "source_changed"


async def test_ha_receipt_is_not_a_gps_report_and_late_receipts_do_not_count():
    from homeassistant.core import State
    from custom_components.homecircle.family_refresh import observe_family_refresh

    h, r, u, reg, _, phone, _ = mixed_fixture()
    now = datetime.now(UTC)
    r.states = {
        phone: State(
            phone,
            "home",
            {"source_type": "gps"},
            last_updated=now - timedelta(minutes=20),
            last_reported=now - timedelta(minutes=20),
        )
    }
    with (
        patch(
            "custom_components.homecircle.family_refresh.er.async_get", return_value=reg
        ),
        patch(
            "custom_components.homecircle.family_refresh.dt_util.utcnow",
            return_value=now,
        ),
    ):
        await async_refresh_family(h, r, u)
    r.states[phone] = State(
        phone,
        "home",
        {"source_type": "gps"},
        last_updated=now + timedelta(seconds=10),
        last_reported=now + timedelta(seconds=10),
    )
    observe_family_refresh(r, now + timedelta(seconds=11))
    observe_family_refresh(r, now + timedelta(minutes=2))
    assert r.family_refresh["members"][0]["status"] == "ha_updated"
    assert r.family_refresh["members"][1]["status"] == "unchanged"
    r.states[phone] = State(phone, "away", {}, last_updated=now + timedelta(minutes=3))
    observe_family_refresh(r, now + timedelta(minutes=3))
    assert r.family_refresh["members"][0]["status"] == "ha_updated"


async def test_complete_circle_and_phone_are_combined_without_duplicate_circle_calls():
    h, r, u, reg, _, phone, _ = mixed_fixture()
    r.config["members"][r.household.members[0].id]["trackers"].append(
        "device_tracker.example_member0"
    )
    with (
        patch(
            "custom_components.homecircle.family_refresh.er.async_get", return_value=reg
        ),
        patch(
            "custom_components.homecircle.family_refresh.async_send",
            new_callable=AsyncMock,
            return_value=True,
        ) as send,
    ):
        assert (await async_refresh_family(h, r, u))["status"] == "requested"
    assert send.await_count == 1
    assert h.services.async_call.await_count == 1
    assert h.services.async_call.await_args.args[0] == "notify"
    assert len(r.family_refresh["members"][0]["trackers"]) == 2


async def test_managed_cloud_connection_checks_once_for_multiple_assigned_sources():
    h, r, u, reg, _, _, _ = mixed_fixture()
    r.config["members"][r.household.members[0].id]["trackers"] = [
        "device_tracker.example_member0"
    ]
    client = NS(
        entry_id="owned-entry",
        async_refresh_on_selection=AsyncMock(return_value="checked"),
    )
    r.managed_trackers = {"life360": client}
    for i in range(2):
        registered = reg.async_get(f"device_tracker.example_member{i}")
        registered.platform = "homecircle"
        registered.unique_id = f"homecircle_life360_{i}"
        registered.config_entry_id = "owned-entry"
    with patch(
        "custom_components.homecircle.family_refresh.er.async_get", return_value=reg
    ):
        assert (await async_refresh_family(h, r, u))["status"] == "requested"
    assert client.async_refresh_on_selection.await_count == 1
    h.services.async_call.assert_not_awaited()
    assert all(t["request_status"] == "checked" for t in r.family_refresh["targets"])


async def test_mixed_button_daily_limit_exact_expiry_and_storage_failure():
    h, r, u, reg, _, _, _ = mixed_fixture()
    now = datetime.now(UTC)
    r.location_request_times["family:assigned"] = [
        now - timedelta(hours=23, seconds=i) for i in range(MAX_REQUESTS)
    ]
    with (
        patch(
            "custom_components.homecircle.family_refresh.er.async_get", return_value=reg
        ),
        patch(
            "custom_components.homecircle.family_refresh.dt_util.utcnow",
            return_value=now,
        ),
    ):
        result = await async_refresh_family(h, r, u)
        assert result["status"] == "limited"
        assert datetime.fromisoformat(result["retry_at"]) == min(
            r.location_request_times["family:assigned"]
        ) + timedelta(days=1)
        h.services.async_call.assert_not_awaited()
        r.location_request_times.clear()
        r.location_request_store.async_save.side_effect = OSError()
        assert (await async_refresh_family(h, r, u))["status"] == "unavailable"
        h.services.async_call.assert_not_awaited()
        assert not any(r.location_request_times.values())


async def test_all_skipped_sources_still_explain_results_without_spending_budget():
    h, r, u, reg, _, _, _ = mixed_fixture()
    r.config["members"][r.household.members[0].id]["auto_request_location"] = False
    reg.async_get("device_tracker.example_member1").platform = "unsupported_provider"
    with patch(
        "custom_components.homecircle.family_refresh.er.async_get", return_value=reg
    ):
        assert family_status(h, r, reg)["available"]
        assert (await async_refresh_family(h, r, u))["status"] == "unsupported"
        assert [m["status"] for m in family_status(h, r, reg)["members"]] == [
            "disabled",
            "unsupported",
        ]
    h.services.async_call.assert_not_awaited()
    assert not r.location_request_times


async def test_registry_rebinding_during_save_cannot_redirect_phone_request():
    h, r, u, reg, _, phone, _ = mixed_fixture()

    async def save(_):
        reg.async_get(phone).unique_id = "different-phone"

    r.location_request_store.async_save.side_effect = save
    with patch(
        "custom_components.homecircle.family_refresh.er.async_get", return_value=reg
    ):
        assert (await async_refresh_family(h, r, u))["status"] == "unsupported"
    h.services.async_call.assert_not_awaited()


async def test_paused_family_never_reads_or_sends_circle_credentials():
    h, runtime, user, registry, _circle = fixture()
    runtime.provider_controls.paused = lambda *_: True
    with (
        patch("custom_components.homecircle.family_refresh.er.async_get", return_value=registry),
        patch("custom_components.homecircle.family_refresh.async_send", new=AsyncMock()) as send,
    ):
        assert (await async_refresh_family(h, runtime, user))["status"] == "unsupported"
    send.assert_not_awaited()
    assert not runtime.location_request_times


async def test_pause_during_family_reservation_prevents_circle_send(hass):
    from custom_components.homecircle.provider_controls import async_get_controls

    h, runtime, user, registry, _circle = fixture()
    controls = runtime.provider_controls = await async_get_controls(hass, "example-family-reservation")

    async def save(_data):
        await controls.async_set_paused("life360", True)

    runtime.location_request_store.async_save.side_effect = save
    with (
        patch.object(hass.config_entries, "async_reload", new=AsyncMock()),
        patch("custom_components.homecircle.family_refresh.er.async_get", return_value=registry),
        patch("custom_components.homecircle.family_refresh.async_send", new=AsyncMock()) as send,
    ):
        assert (await async_refresh_family(h, runtime, user))["status"] == "unsupported"
    send.assert_not_awaited()


@pytest.mark.parametrize("http_status", [401, 403])
async def test_exact_family_http_denial_persists_pause_and_never_sends_again(hass, http_status):
    from unittest.mock import Mock
    from custom_components.homecircle.provider_controls import ProviderControls, async_get_controls

    h, runtime, user, registry, _circle = fixture()
    controls = runtime.provider_controls = await async_get_controls(hass, "example-family-denial")
    response_context = AsyncMock()
    response_context.__aenter__.return_value = NS(status=http_status)
    session = NS(post=Mock(return_value=response_context))
    session_context = AsyncMock()
    session_context.__aenter__.return_value = session
    h.async_add_executor_job = AsyncMock(return_value=None)
    with (
        patch.object(hass.config_entries, "async_reload", new=AsyncMock()),
        patch("custom_components.homecircle.family_refresh.er.async_get", return_value=registry),
        patch("custom_components.homecircle.family_refresh.aiohttp.TCPConnector"),
        patch("custom_components.homecircle.family_refresh.aiohttp.ClientSession", return_value=session_context),
    ):
        assert (await async_refresh_family(h, runtime, user))["status"] == "send_failed"
        assert runtime.family_refresh["members"][0]["status"] == "disabled"
        assert controls.paused("life360")
        assert (await async_refresh_family(h, runtime, user))["status"] == "unsupported"
        await hass.async_block_till_done()
    session.post.assert_called_once()
    assert session.post.call_args.kwargs["allow_redirects"] is False
    restored = ProviderControls(hass, "example-family-denial")
    await restored.async_load()
    assert restored.paused("life360")
