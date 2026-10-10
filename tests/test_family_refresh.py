"""Full Circle scope, atomic request limits and evidence feedback."""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, patch

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
