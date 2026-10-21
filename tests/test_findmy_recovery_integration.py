"""The real local guard and setup/UI boundaries never automatically replay proof."""

import asyncio
from pathlib import Path

import pytest

from custom_components.homecircle.findmy_flow import FindMyFlow
from custom_components.homecircle.findmy_identity import authenticated_identity
from custom_components.homecircle.findmy_recovery_guard import RecoveryGuard
from custom_components.homecircle.findmy_setup import FindMySetupError, recovery_error
from custom_components.homecircle._findmy_runtime.onboarding import RecoveryPETError
from custom_components.homecircle._vendor_findmy.keychain.recovery import (
    RecoveryProtocolError,
)
from tests.test_findmy_setup import setup


def guarded_setup(tmp_path):
    value, account, client = setup()
    value.recovery_guard = RecoveryGuard(Path(tmp_path) / "guard")
    value.recovery_guard_required = True
    return value, account, client


async def submit(value, expected):
    await value.open_recovery()
    with pytest.raises(FindMySetupError, match=expected):
        await value.discover("0", "synthetic-passcode")


@pytest.mark.parametrize(
    "failure,expected",
    [
        (RecoveryPETError("missing_password"), "findmy_recovery_signin_required"),
        (RecoveryPETError("factor_required"), "findmy_recovery_signin_required"),
        (RecoveryPETError("identity_mismatch"), "findmy_account_mismatch"),
        (RecoveryPETError("transient"), "findmy_recovery_transient"),
        (TimeoutError("private-error-canary"), "findmy_recovery_transient"),
        (
            RecoveryProtocolError("preproof", "not_dispatched", reason="transient"),
            "findmy_recovery_transient",
        ),
        (
            RecoveryProtocolError("preproof", "not_dispatched"),
            "findmy_recovery_protocol",
        ),
    ],
)
async def test_preproof_failure_consumes_no_local_submission(
    tmp_path, failure, expected, caplog
):
    value, account, client = guarded_setup(tmp_path)
    client.unlock.side_effect = failure
    try:
        await submit(value, expected)
        status = await value.recovery_guard.status(
            authenticated_identity(account.to_json())
        )
        assert status["unresolved"] == status["verified"] == 0
        assert account._homecircle_recovery_attempt is None
        assert account._password is None
        assert "private-error-canary" not in caplog.text
    finally:
        await value.close()


async def test_new_setups_share_limit_and_local_reset_does_not_submit(tmp_path):
    calls = 0
    for _ in range(3):
        value, account, client = guarded_setup(tmp_path)

        async def refused(*_args):
            nonlocal calls
            calls += 1
            attempt = account._homecircle_recovery_attempt
            assert account._homecircle_recovery_guard_required
            await attempt.before_dispatch()
            await attempt.refused()
            raise RecoveryProtocolError("refusal", "refused")

        client.unlock.side_effect = refused
        await submit(value, "findmy_recovery_refused")
        await value.close()
    value, account, client = guarded_setup(tmp_path)
    identity = authenticated_identity(account.to_json())
    await value.open_recovery()

    async def would_dispatch(*_args):
        await account._homecircle_recovery_attempt.before_dispatch()
        raise AssertionError("proof must be blocked")

    client.unlock.side_effect = would_dispatch
    with pytest.raises(FindMySetupError, match="findmy_recovery_limit"):
        await value.discover("0", "synthetic-passcode")
    assert calls == 3
    assert (await value.recovery_guard.status(identity))["rejected"] == 3

    class UI(FindMyFlow):
        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}

        def async_abort(self, **kwargs):
            return {"type": "abort", **kwargs}

    ui = UI()
    ui.findmy_setup, ui.findmy_device = value, "0"
    result = await ui.async_step_findmy_passcode()
    assert result["step_id"] == "findmy_recovery_reset"
    assert result["description_placeholders"] == {"rejected": "3", "uncertain": "0"}
    result = await ui.async_step_findmy_recovery_reset({"acknowledge": False})
    assert result["errors"]["base"] == "findmy_recovery_acknowledge"
    before_calls = client.unlock.await_count
    result = await ui.async_step_findmy_recovery_reset({"acknowledge": True})
    assert result["step_id"] == "findmy_passcode"
    assert client.unlock.await_count == before_calls
    assert (await value.recovery_guard.status(identity))["unresolved"] == 0
    await value.close()


async def test_account_mismatch_prevents_guarded_unlock(tmp_path):
    value, _, client = guarded_setup(tmp_path)
    value.account_guard = lambda _: False
    await submit(value, "findmy_account_mismatch")
    client.unlock.assert_not_awaited()
    await value.close()


async def test_product_setup_without_guard_fails_closed():
    value, _, client = setup()
    value.recovery_guard_required = True
    await submit(value, "findmy_recovery_storage")
    client.unlock.assert_not_awaited()
    await value.close()


async def test_outer_timeout_after_dispatch_retains_uncertainty(tmp_path, monkeypatch):
    value, account, client = guarded_setup(tmp_path)

    async def lost_response(*_args):
        await account._homecircle_recovery_attempt.before_dispatch()
        outer.reschedule(asyncio.get_running_loop().time())
        await asyncio.Future()

    client.unlock.side_effect = lost_response
    real_timeout = asyncio.timeout
    outer = real_timeout(None)
    monkeypatch.setattr(asyncio, "timeout", lambda _seconds: outer)
    await submit(value, "findmy_recovery_uncertain")
    assert (
        await value.recovery_guard.status(authenticated_identity(account.to_json()))
    )["uncertain"] == 1
    assert account._homecircle_recovery_attempt is None
    await value.close()


async def test_verified_material_retry_and_accessory_retry_send_no_new_proof(tmp_path):
    value, account, client = guarded_setup(tmp_path)
    calls = 0
    record = None

    async def finish(_record, passcode):
        nonlocal calls, record
        calls += 1
        if calls == 1:
            record = _record
            attempt = account._homecircle_recovery_attempt
            await attempt.before_dispatch()
            await attempt.verified()
            raise RecoveryProtocolError("material", "verified")
        assert passcode == "" and _record is record
        return [object()]

    client.unlock.side_effect = finish
    client.can_resume_unlock = lambda selected: record is selected
    await submit(value, "findmy_recovery_resume")
    assert value.can_resume_recovery("0")
    client.accessories.side_effect = RuntimeError("private-error-canary")
    with pytest.raises(FindMySetupError, match="findmy_recovery_failed"):
        await value.discover("0", "")
    assert value.keys_recovered
    client.accessories.side_effect = None
    assert await value.retry_discovery()
    assert calls == 2
    status = await value.recovery_guard.status(
        authenticated_identity(account.to_json())
    )
    assert status["verified"] == 1 and status["unresolved"] == 0
    await value.close()


@pytest.mark.parametrize("reason", ["unknown-private-error", "protocol"])
def test_unknown_pet_reason_stays_fixed(reason):
    assert recovery_error(RecoveryPETError(reason)) == "findmy_recovery_protocol"


async def test_reset_refuses_active_other_flow(tmp_path):
    value, account, _ = guarded_setup(tmp_path)
    identity = authenticated_identity(account.to_json())

    class UI(FindMyFlow):
        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}

    ui = UI()
    ui.findmy_setup = value
    async with value.recovery_guard.attempt(identity):
        result = await ui.async_step_findmy_recovery_reset({"acknowledge": True})
        assert result["errors"]["base"] == "findmy_recovery_busy"
    await value.close()


async def test_empty_keys_after_verified_peer_routes_to_safe_resume(tmp_path):
    value, account, client = guarded_setup(tmp_path)

    async def empty_keys(*_args):
        attempt = account._homecircle_recovery_attempt
        await attempt.before_dispatch()
        await attempt.verified()
        return []

    client.unlock.side_effect = empty_keys
    client.can_resume_unlock = lambda _: True
    await submit(value, "findmy_recovery_resume")
    status = await value.recovery_guard.status(
        authenticated_identity(account.to_json())
    )
    assert status["verified"] == 1 and status["unresolved"] == 0
    await value.close()


async def test_accessory_timeout_keeps_verified_keys_for_discovery(tmp_path):
    value, account, client = guarded_setup(tmp_path)

    async def verified_keys(*_args):
        attempt = account._homecircle_recovery_attempt
        await attempt.before_dispatch()
        await attempt.verified()
        return [object()]

    client.unlock.side_effect = verified_keys
    client.accessories.side_effect = TimeoutError()
    await submit(value, "findmy_recovery_transient")
    assert value.keys_recovered
    client.accessories.side_effect = None
    assert await value.retry_discovery()
    client.unlock.assert_awaited_once()
    status = await value.recovery_guard.status(
        authenticated_identity(account.to_json())
    )
    assert status["verified"] == 1 and status["unresolved"] == 0
    await value.close()


async def test_outer_timeout_after_verified_material_routes_to_resume(
    tmp_path, monkeypatch
):
    value, account, client = guarded_setup(tmp_path)
    real_timeout = asyncio.timeout
    outer = real_timeout(None)
    monkeypatch.setattr(asyncio, "timeout", lambda _seconds: outer)

    async def interrupted_material(*_args):
        attempt = account._homecircle_recovery_attempt
        await attempt.before_dispatch()
        await attempt.verified()
        outer.reschedule(asyncio.get_running_loop().time())
        await asyncio.Future()

    client.unlock.side_effect = interrupted_material
    client.can_resume_unlock = lambda _: True
    await submit(value, "findmy_recovery_resume")
    status = await value.recovery_guard.status(
        authenticated_identity(account.to_json())
    )
    assert status["verified"] == 1 and status["unresolved"] == 0
    await value.close()


@pytest.mark.parametrize("reason,status,expected", [
    ("transient", 429, "findmy_recovery_rate_limited"),
    ("transient", 503, "findmy_recovery_transient"),
    ("transient", None, "findmy_recovery_transient"),
    ("transient", "429", "findmy_recovery_transient"),
    ("transient", True, "findmy_recovery_transient"),
    ("protocol", 429, "findmy_recovery_protocol"),
])
def test_recovery_rate_limit_requires_exact_preproof_transient_status(reason, status, expected):
    assert recovery_error(RecoveryPETError(reason, http_status=status)) == expected
