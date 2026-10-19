"""Authentication without a tracking grant must never replace a working connection."""

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.homecircle.findmy_setup import (
    FindMySetup,
    FindMySetupError,
    require_nonempty_report_grant,
)
from custom_components.homecircle.findmy_vault import account_identity


FAILURE = "findmy_report_access_unavailable"
STATES = SimpleNamespace(REQUIRE_2FA=1, LOGGED_IN=3)


def session(tokens):
    return {
        "account": {"username": "example@example.invalid", "password": None},
        "login": {
            "state": 3,
            "data": {
                "dsid": "example-dsid",
                "mobileme_data": {"tokens": deepcopy(tokens)},
            },
        },
    }


def setup(tokens):
    account = SimpleNamespace(
        service_tokens=tokens,
        login=AsyncMock(return_value=3),
        get_2fa_methods=AsyncMock(),
        close=AsyncMock(),
        to_json=lambda: session(tokens),
        _password="fixture-secret",
        _recovery_pet="synthetic-private-pet",
        _recovery_pet_at=10,
        _gsa_pet_at=10,
    )
    transient = FindMySetup(account, AsyncMock(), STATES)
    transient.prepare_recovery = AsyncMock()
    transient.restore_selected_items = Mock()
    return transient, account


@pytest.mark.parametrize(
    "tokens",
    [
        None,
        {},
        {"mmeAuthToken": "synthetic-mme"},
        {"searchPartyToken": ""},
        {"searchPartyToken": "  "},
        {"searchPartyToken": None},
        {"searchPartyToken": 1},
        {"searchPartyToken": b"not-a-string"},
    ],
)
def test_tracking_grant_requires_a_nonempty_string_and_clears_transient_secrets(
    tokens, caplog
):
    transient, account = setup(tokens)
    with pytest.raises(FindMySetupError, match=FAILURE):
        require_nonempty_report_grant(account)
    for attribute in ("_password", "_recovery_pet", "_recovery_pet_at", "_gsa_pet_at"):
        assert getattr(account, attribute) is None
    assert "synthetic-private" not in caplog.text
    assert "fixture-secret" not in caplog.text
    transient.client_factory.assert_not_awaited()


def test_unavailable_service_token_property_maps_to_the_fixed_failure():
    from custom_components.homecircle._vendor_findmy.errors import InvalidStateError

    class Unavailable:
        _password = "fixture-secret"

        @property
        def service_tokens(self):
            raise InvalidStateError("synthetic-private-state")

    account = Unavailable()
    with pytest.raises(FindMySetupError, match=FAILURE) as caught:
        require_nonempty_report_grant(account)
    assert "synthetic-private" not in str(caught.value)
    assert account._password is None


@pytest.mark.parametrize("method", ["login", "trusted_device", "sms"])
@pytest.mark.parametrize("reconnect", [False, True])
@pytest.mark.parametrize(
    "tokens", [{"mmeAuthToken": "synthetic-mme"}, {"searchPartyToken": ""}]
)
async def test_every_logged_in_completion_stops_before_selection_or_recovery(
    method, reconnect, tokens
):
    transient, account = setup(tokens)
    transient.previous_items = (
        {"existing": {"accessory": {}, "report": None}} if reconnect else {}
    )
    transient.discover_new = not reconnect
    before = deepcopy(transient.previous_items)
    if method == "login":
        operation = transient.login(
            "example@example.invalid", "fixture-secret"
        )
    else:
        transient.factor = SimpleNamespace(
            submit=AsyncMock(return_value=3), kind=method
        )
        operation = transient.verify_code("synthetic-private-code")
    with pytest.raises(FindMySetupError, match=FAILURE):
        await operation
    transient.restore_selected_items.assert_not_called()
    transient.prepare_recovery.assert_not_awaited()
    transient.client_factory.assert_not_awaited()
    assert transient.unlock_attempts == 0
    assert transient.previous_items == before
    assert account._password is None
    await transient.close()


async def test_valid_report_grant_keeps_pet_and_password_for_recovery():
    transient, account = setup({"searchPartyToken": "synthetic-report-token"})
    assert (
        await transient.login("example@example.invalid", "fixture-secret")
        == "device"
    )
    transient.prepare_recovery.assert_awaited_once()
    assert account._password == "fixture-secret"
    assert account._recovery_pet == "synthetic-private-pet"
    await transient.close()


@pytest.mark.parametrize(
    "source", ["account", "serialized", "different_serialized_token"]
)
async def test_selected_payload_refuses_missing_report_grant_before_storage(source):
    transient, account = setup({"searchPartyToken": "synthetic-report-token"})
    transient.accessories = {
        "existing": SimpleNamespace(to_json=lambda: {"identifier": "synthetic-item"})
    }
    if source == "account":
        account.service_tokens = {"mmeAuthToken": "synthetic-mme"}
    elif source == "serialized":
        account.to_json = lambda: session({"mmeAuthToken": "synthetic-mme"})
    else:
        account.to_json = lambda: session(
            {"searchPartyToken": "different-synthetic-report-token"}
        )
    with pytest.raises(FindMySetupError, match=FAILURE):
        transient.selected_payload(["existing"])
    assert account._password is None
    await transient.close()


@pytest.mark.parametrize("method", ["login", "trusted_device", "sms"])
async def test_real_ha_reconnect_missing_tracking_grant_aborts_without_replacing_existing(
    hass,
    method,
):
    old_session = session({"searchPartyToken": "synthetic-working-token"})
    metadata = {
        "label": "Example account",
        "storage_id": "a" * 32,
        "account_identity": account_identity(old_session),
        "items": {"existing": {"name": "Example item", "type": "airtag"}},
    }
    configuration = {
        "people": [],
        "members": {},
        "primary_home": "zone.home",
        "places": [],
        "findmy_accounts": {"a" * 32: metadata},
    }
    entry = MockConfigEntry(
        domain="homecircle",
        data=deepcopy(configuration),
        options=deepcopy(configuration),
    )
    entry.add_to_hass(hass)
    manager = hass.config_entries.options
    result = await manager.async_init(entry.entry_id)
    for values in (
        {"next_step_id": "findmy_accounts"},
        {"next_step_id": "findmy_manage"},
        {"account": "a" * 32},
        {"next_step_id": "findmy_reconnect"},
    ):
        result = await manager.async_configure(result["flow_id"], values)
    transient, account = setup({"mmeAuthToken": "synthetic-mme"})
    factor = None
    if method != "login":
        account.login.return_value = 1
        factor = SimpleNamespace(request=AsyncMock(), submit=AsyncMock(return_value=3))
        account.get_2fa_methods.return_value = [factor]
    old = {
        "version": 2,
        "session": old_session,
        "items": {"existing": {"accessory": {}, "report": None}},
    }

    async def finish_pending(value):
        if value["type"] is FlowResultType.SHOW_PROGRESS:
            await hass.async_block_till_done()
            return await manager.async_configure(value["flow_id"])
        return value

    with (
        patch(
            "custom_components.homecircle.findmy_flow.Vault.load",
            return_value=deepcopy(old),
        ),
        patch("custom_components.homecircle.findmy_flow.Vault.save_account") as write,
        patch(
            "custom_components.homecircle.findmy_flow.FindMySetup.create",
            return_value=transient,
        ),
    ):
        result = await manager.async_configure(result["flow_id"], {"consent": True})
        result = await manager.async_configure(
            result["flow_id"],
            {
                "username": "example@example.invalid",
                "password": "fixture-secret",
            },
        )
        result = await finish_pending(result)
        if factor is not None:
            assert result["type"] is FlowResultType.FORM
            assert result["step_id"] == "findmy_factor"
            result = await manager.async_configure(result["flow_id"], {"method": "0"})
            result = await finish_pending(result)
            assert result["type"] is FlowResultType.FORM
            assert result["step_id"] == "findmy_code"
            result = await manager.async_configure(
                result["flow_id"], {"code": "synthetic-private-code"}
            )
            result = await finish_pending(result)
            factor.request.assert_awaited_once()
            factor.submit.assert_awaited_once_with("synthetic-private-code")
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == FAILURE
        write.assert_not_called()
    assert dict(entry.options) == configuration and dict(entry.data) == configuration
    transient.prepare_recovery.assert_not_awaited()
    transient.restore_selected_items.assert_not_called()
    account.close.assert_awaited_once()
    assert transient.closed
    assert not manager.async_progress()


def test_missing_grant_message_is_available_for_config_options_errors_and_abort():
    root = Path(__file__).resolve().parents[1] / "custom_components" / "homecircle"
    for name in ("strings.json", "translations/en.json"):
        data = json.loads((root / name).read_text())
        for flow in ("config", "options"):
            for result in ("error", "abort"):
                text = data[flow][result][FAILURE]
                assert "could not obtain a usable" in text
                assert "not replaced" in text
                assert (
                    "password" not in text.lower() and "try again" not in text.lower()
                )
