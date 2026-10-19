"""Setup exposes bounded sign-in evidence without echoing account data."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.homecircle._vendor_findmy.errors import AppleServiceUnavailableError
from custom_components.homecircle.findmy_setup import (
    FindMySetupError,
    log_signin_failure,
)
from tests.test_findmy_setup import setup


def snapshot(phase="init"):
    return {
        "schema": 1,
        "phase": phase,
        "request_count": 1 if phase == "init" else 2,
        "http": 429,
        "apple_code": None,
        "apple_hsc": None,
        "profile": "mac_coreadi_v1",
        "media_type": "html",
        "body_size": "small",
    }


@pytest.mark.parametrize("phase", ["init", "complete"])
async def test_real_setup_failure_exposes_phase_without_password_or_response(phase, caplog):
    flow, account, _ = setup()
    account.signin_diagnostics = lambda: {**snapshot(phase), "response": "private-detail"}
    account.login.side_effect = AppleServiceUnavailableError(
        429, "The Grand Slam request", phase=phase
    )
    try:
        with pytest.raises(FindMySetupError, match="findmy_apple_unavailable"):
            await flow.login("example@example.invalid", "example-secret")
        records = [r for r in caplog.records if r.msg == "Find My sign-in diagnostics: %s"]
        assert len(records) == 1 and records[0].args == snapshot(phase)
        assert f"http=429 retry_after_seconds=None phase={phase}" in caplog.text
        assert all(value not in caplog.text for value in (
            "example@example.invalid", "example-secret", "private-detail"
        ))
        account.login.assert_awaited_once()
    finally:
        await flow.close()


def test_projection_rejects_malformed_values_and_unknown_fields(caplog):
    raw = {
        "schema": "private-detail", "phase": ["private-detail"],
        "request_count": True, "http": 600, "apple_code": 1.5,
        "apple_hsc": 1000001, "profile": {"private-detail": 1},
        "media_type": "private-detail", "body_size": ["private-detail"],
        "headers": "private-detail", "account": "private-detail",
    }
    log_signin_failure(SimpleNamespace(signin_diagnostics=lambda: raw))
    record = next(r for r in caplog.records if r.msg == "Find My sign-in diagnostics: %s")
    assert record.args == {"schema": 1, **{key: None for key in snapshot() if key != "schema"}}
    assert "private-detail" not in caplog.text
    assert raw["schema"] == "private-detail"


@pytest.mark.parametrize("getter", [None, lambda: ["private-detail"],
                                      lambda: (_ for _ in ()).throw(RuntimeError("private-detail"))])
def test_missing_or_broken_getter_does_not_obscure_original_failure(getter, caplog):
    log_signin_failure(SimpleNamespace(signin_diagnostics=getter))
    assert not caplog.records


async def test_verification_reauthentication_failure_retains_gsa_phase(caplog):
    flow, account, _ = setup()
    account._verification_stage = "reauthentication"
    account.signin_diagnostics = lambda: snapshot("complete")
    flow.factor = SimpleNamespace(submit=AsyncMock(side_effect=AppleServiceUnavailableError(
        429, "The Grand Slam request", phase="complete"
    )))
    try:
        with pytest.raises(FindMySetupError, match="findmy_code_signin_failed"):
            await flow.verify_code("example-code")
        record = next(r for r in caplog.records if r.msg == "Find My sign-in diagnostics: %s")
        assert record.args == snapshot("complete")
        assert "apple_code=None srp=complete" in caplog.text
        assert "example-code" not in caplog.text
        flow.factor.submit.assert_awaited_once()
    finally:
        await flow.close()
