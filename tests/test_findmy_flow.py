"""Native HA flow lifecycle with synthetic Apple responses only."""

from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import pytest
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.homecircle.findmy_setup import FindMySetup, FindMySetupError


async def finish_background_progress(manager, result):
    """Durable recovery work may span several real progress notifications."""
    import asyncio

    async with asyncio.timeout(5):
        while result["type"] in (
            FlowResultType.SHOW_PROGRESS, FlowResultType.SHOW_PROGRESS_DONE
        ):
            await asyncio.sleep(.005)
            result = await manager.async_configure(result["flow_id"])
    return result


def fake_setup():
    account = SimpleNamespace(
        login=AsyncMock(return_value=3),
        close=AsyncMock(),
        _password=None,
        service_tokens={"searchPartyToken": "example-report-token"},
        to_json=lambda: {
            "account": {"username": "example@example.invalid", "password": None},
            "login": {
                "state": 3,
                "data": {
                    "dsid": "example-dsid",
                    "mobileme_data": {
                        "tokens": {"searchPartyToken": "example-report-token"}
                    },
                },
            },
        },
    )
    accessory = SimpleNamespace(
        identifier="example-item",
        name="Example item",
        model="AirTag",
        to_json=lambda: {"identifier": "example-item", "master_key": "example-key"},
    )
    client = SimpleNamespace(
        close=AsyncMock(),
        unlock=AsyncMock(return_value=[object()]),
        recovery_options=AsyncMock(
            return_value=SimpleNamespace(
                recoverable=[
                    SimpleNamespace(
                        device_name="Example iPhone",
                        device_model="iPhone",
                        serial="EXAMPLE1234",
                    )
                ]
            )
        ),
        accessories=AsyncMock(return_value=[accessory]),
    )
    flow = FindMySetup(
        account,
        AsyncMock(return_value=client),
        SimpleNamespace(REQUIRE_2FA=1, LOGGED_IN=3),
    )
    flow.zone_checker = AsyncMock()
    return flow


async def options(hass):
    entry = MockConfigEntry(
        domain="homecircle",
        title="HomeCircle",
        data={
            "people": [],
            "members": {},
            "primary_home": "zone.home",
            "places": [],
        },
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "findmy_accounts"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "findmy_add"}
    )
    return entry, result


async def test_native_findmy_requires_consent_and_cleans_up_on_abort(hass):
    _, result = await options(hass)
    fake = fake_setup()
    with patch(
        "custom_components.homecircle.findmy_flow.FindMySetup.create", return_value=fake
    ) as create:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"label": "Example account", "consent": False}
        )
        assert result["errors"] == {"base": "findmy_consent_required"}
        create.assert_not_called()
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"label": "Example account", "consent": True}
        )
        assert result["step_id"] == "findmy_login"
        assert create.call_args.kwargs == {"onboarding": True}
        hass.config_entries.options.async_abort(result["flow_id"])
        await hass.async_block_till_done()
        fake.account.close.assert_awaited_once()
        assert fake.closed


@pytest.mark.parametrize(
    "failure",
    [
        "findmy_code_signin_failed",
        "findmy_code_delegate_failed",
        "findmy_verification_limit",
        "findmy_signin_state",
        "findmy_account_mismatch",
        "findmy_initial_refused",
    ],
)
async def test_consumed_authentication_ends_without_code_retry_or_saved_connection(
    hass, failure
):
    entry, result = await options(hass)
    fake = fake_setup()
    fake.account.login.side_effect = FindMySetupError(failure)
    manager = hass.config_entries.options
    with (
        patch("custom_components.homecircle.findmy_flow.FindMySetup.create", return_value=fake),
        patch("custom_components.homecircle.findmy_flow.Vault.save_account") as save,
    ):
        result = await manager.async_configure(
            result["flow_id"], {"label": "Example account", "consent": True}
        )
        result = await manager.async_configure(
            result["flow_id"],
            {"username": "example@example.invalid", "password": "example-secret"},
        )
        if result["type"] is FlowResultType.SHOW_PROGRESS:
            await hass.async_block_till_done()
            result = await manager.async_configure(result["flow_id"])
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == failure
        assert fake.closed
        assert not entry.options
        save.assert_not_called()
        fake.zone_checker.assert_not_awaited()
        fake.client_factory.assert_not_awaited()


async def test_native_progress_device_selection_and_explicit_selected_store(hass):
    import asyncio

    entry, result = await options(hass)
    fake = fake_setup()

    async def delayed_login(_username, _password):
        await asyncio.sleep(0)
        return 3

    # Keep this test on the genuinely pending branch. Instant restored work has
    # its own regression requiring the next form in the original response.
    fake.account.login.side_effect = delayed_login
    manager = hass.config_entries.options
    with (
        patch(
            "custom_components.homecircle.findmy_flow.FindMySetup.create",
            return_value=fake,
        ),
        patch("custom_components.homecircle.findmy_flow.Vault.save_account") as save,
    ):
        result = await manager.async_configure(
            result["flow_id"], {"label": "Example account", "consent": True}
        )
        from custom_components.homecircle.findmy_recovery_guard import get_recovery_guard
        assert fake.recovery_guard is get_recovery_guard(hass)
        assert fake.recovery_guard_required
        result = await manager.async_configure(
            result["flow_id"],
            {"username": "example@example.invalid", "password": "example-secret"},
        )
        assert result["type"] == FlowResultType.SHOW_PROGRESS
        await hass.async_block_till_done()
        result = await finish_background_progress(
            manager, await manager.async_configure(result["flow_id"])
        )
        assert result["step_id"] == "findmy_device"
        result = await manager.async_configure(result["flow_id"], {"device": "0"})
        result = await manager.async_configure(
            result["flow_id"], {"passcode": "synthetic-passcode"}
        )
        await hass.async_block_till_done()
        result = await finish_background_progress(
            manager, await manager.async_configure(result["flow_id"])
        )
        assert result["step_id"] == "findmy_select"
        result = await manager.async_configure(result["flow_id"], {"items": []})
        assert result["errors"]["base"] == "findmy_select_items"
        selected = fake.item_choices()[0]["value"]
        result = await manager.async_configure(result["flow_id"], {"items": [selected]})
        result = await manager.async_configure(result["flow_id"], {"type_0": "airtag"})
        result = await manager.async_configure(result["flow_id"], {"confirm": True})
        assert result["type"] == FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()
        account = next(iter(entry.options["findmy_accounts"].values()))
        assert account["items"][selected]["type"] == "airtag"
        assert (
            account["account_identity"]
            == sha256(b"dsid:example-dsid").hexdigest()
        )
        assert "example-secret" not in str(entry.options)
        assert save.call_args.args[0]["account"]["password"] is None
        assert list(save.call_args.args[1]) == [selected]
        assert fake.closed


async def test_findmy_in_household_flow_continues_member_setup_and_abort_leaves_no_vault(
    hass, household
):
    entry = MockConfigEntry(
        domain="homecircle",
        title="HomeCircle",
        data={"people": [], "members": {}, "primary_home": "zone.home", "places": []},
    )
    entry.add_to_hass(hass)
    manager = hass.config_entries.options
    result = await manager.async_init(entry.entry_id)
    result = await manager.async_configure(
        result["flow_id"], {"next_step_id": "household"}
    )
    result = await manager.async_configure(
        result["flow_id"],
        {
            **household,
            "people": ["person.example_member"],
            "findmy_enabled": True,
        },
    )
    assert result["step_id"] == "findmy_accounts"
    result = await manager.async_configure(
        result["flow_id"], {"next_step_id": "findmy_add"}
    )
    fake = fake_setup()
    with (
        patch(
            "custom_components.homecircle.findmy_flow.FindMySetup.create",
            return_value=fake,
        ),
        patch("custom_components.homecircle.findmy_flow.Vault.save_account") as save,
    ):
        result = await manager.async_configure(
            result["flow_id"], {"label": "Example account", "consent": True}
        )
        result = await manager.async_configure(
            result["flow_id"],
            {"username": "example@example.invalid", "password": "example-secret"},
        )
        await hass.async_block_till_done()
        result = await finish_background_progress(
            manager, await manager.async_configure(result["flow_id"])
        )
        result = await manager.async_configure(result["flow_id"], {"device": "0"})
        result = await manager.async_configure(
            result["flow_id"], {"passcode": "synthetic-passcode"}
        )
        await hass.async_block_till_done()
        result = await finish_background_progress(
            manager, await manager.async_configure(result["flow_id"])
        )
        result = await manager.async_configure(
            result["flow_id"], {"items": [fake.item_choices()[0]["value"]]}
        )
        result = await manager.async_configure(result["flow_id"], {"type_0": "airtag"})
        result = await manager.async_configure(result["flow_id"], {"confirm": True})
        assert result["step_id"] == "member"
        save.assert_not_called()
        assert fake.closed
        manager.async_abort(result["flow_id"])
        await hass.async_block_till_done()
        save.assert_not_called()
        assert not entry.options


async def test_reconnect_changes_session_revision_for_framework_reload(hass):
    from copy import deepcopy
    from custom_components.homecircle.findmy_flow import FindMyFlow

    identifier = "example_item"
    account_id = "a" * 32
    metadata = {
        "label": "Example account",
        "account_identity": sha256(b"example@example.invalid").hexdigest(),
        "storage_id": account_id,
        "items": {identifier: {"name": "Example item", "type": "airtag"}},
    }
    initial = {"findmy_accounts": {account_id: metadata}, "findmy_enabled": True}
    paused = SimpleNamespace(close=AsyncMock())
    provider = SimpleNamespace(
        pause_account=AsyncMock(return_value=paused), resume_account=lambda *_: None
    )
    entry = MockConfigEntry(domain="homecircle", data=deepcopy(initial), options=deepcopy(initial))
    entry.add_to_hass(hass)
    entry.runtime_data = SimpleNamespace(managed_trackers={"findmy": provider})
    fake = SimpleNamespace(
        accessories={identifier: SimpleNamespace(name="Example item")},
        close=AsyncMock(),
        selected_payload=lambda _: (
            {"account": {"username": "example@example.invalid", "password": None}},
            {identifier: {"accessory": {}, "report": None}},
        ),
    )

    class Flow(FindMyFlow):
        def async_create_entry(self, **kwargs):
            return {"saved": True}

    flow = Flow()
    flow.hass = hass
    flow.config_entry = entry
    flow.draft = deepcopy(initial)
    flow.pending_connections = []
    flow.findmy_setup = fake
    flow.findmy_selected = [identifier]
    flow.findmy_types = {identifier: "airtag"}
    flow.findmy_account_id = account_id
    flow.findmy_label = "Example account"
    previous_session, previous_items = fake.selected_payload([identifier])
    with (
        patch("custom_components.homecircle.findmy_flow.Vault.save_account"),
        patch("custom_components.homecircle.findmy_flow.Vault.load", return_value={"version": 2, "session": previous_session, "items": previous_items}),
        patch.object(hass.config_entries, "async_schedule_reload") as reload,
    ):
        assert await flow.async_step_findmy_confirm({"confirm": True}) == {
            "saved": True
        }
        assert flow.draft["findmy_accounts"][account_id]["session_revision"] == 1
        assert flow.draft == entry.options
        reload.assert_called_once_with(entry.entry_id)
        paused.close.assert_awaited_once()
        fake.close.assert_awaited_once()


async def test_denied_zone_access_routes_to_passcode_free_retry(hass):
    from custom_components.homecircle._vendor_findmy.errors import UnauthorizedError
    _, result = await options(hass)
    fake = fake_setup()
    fake.account._recovery_diagnostics = {'operation_http': 401}
    fake.zone_checker.side_effect = UnauthorizedError('synthetic-private-response')
    manager = hass.config_entries.options
    with patch('custom_components.homecircle.findmy_flow.FindMySetup.create', return_value=fake):
        result = await manager.async_configure(result['flow_id'], {'label': 'Example', 'consent': True})
        result = await manager.async_configure(result['flow_id'], {'username': 'example@example.invalid', 'password': 'synthetic'})
        await hass.async_block_till_done()
        result = await manager.async_configure(result['flow_id'])
        assert result['step_id'] == 'findmy_zone'
        assert result['errors'] == {'base': 'findmy_zone_denied'}
        fake.client_factory.assert_not_awaited()
        assert fake.unlock_attempts == 0
        fake.zone_checker.side_effect = None
        result = await manager.async_configure(result['flow_id'], {})
        await hass.async_block_till_done()
        result = await manager.async_configure(result['flow_id'])
        assert result['step_id'] == 'findmy_device'
        assert fake.unlock_attempts == 0
        manager.async_abort(result['flow_id'])
        await hass.async_block_till_done()


async def test_discovery_error_routes_to_retry_without_another_passcode(hass):
    _, result = await options(hass)
    fake = fake_setup()
    manager = hass.config_entries.options
    with patch('custom_components.homecircle.findmy_flow.FindMySetup.create', return_value=fake):
        result = await manager.async_configure(result['flow_id'], {'label': 'Example', 'consent': True})
        result = await manager.async_configure(result['flow_id'], {'username': 'example@example.invalid', 'password': 'synthetic'})
        await hass.async_block_till_done()
        result = await finish_background_progress(
            manager, await manager.async_configure(result["flow_id"])
        )
        result = await manager.async_configure(result['flow_id'], {'device': '0'})
        fake.client.accessories.side_effect = RuntimeError('synthetic-private-response')
        result = await manager.async_configure(result['flow_id'], {'passcode': 'synthetic'})
        await hass.async_block_till_done()
        result = await finish_background_progress(
            manager, await manager.async_configure(result["flow_id"])
        )
        assert result['step_id'] == 'findmy_discovery'
        fake.client.accessories.side_effect = None
        result = await manager.async_configure(result['flow_id'], {})
        await hass.async_block_till_done()
        result = await finish_background_progress(
            manager, await manager.async_configure(result["flow_id"])
        )
        assert result['step_id'] == 'findmy_select'
        fake.client.unlock.assert_awaited_once()
        assert fake.unlock_attempts == 1
        manager.async_abort(result['flow_id'])
        await hass.async_block_till_done()
        assert fake.keys_recovered is False


async def test_additional_code_challenge_returns_to_method_form_without_recovery(hass):
    _, result = await options(hass)
    fake = fake_setup()
    initial = SimpleNamespace(request=AsyncMock(), submit=AsyncMock(return_value=1))
    renewed = SimpleNamespace(request=AsyncMock(), submit=AsyncMock())
    fake.account.login.return_value = 1
    fake.account.get_2fa_methods = AsyncMock(side_effect=[[initial], [renewed]])
    manager = hass.config_entries.options
    flow_id = result['flow_id']

    async def finish_progress(value):
        for _ in range(3):
            if value['type'] == FlowResultType.FORM:
                return value
            await hass.async_block_till_done()
            value = await manager.async_configure(flow_id)
        return value

    with patch('custom_components.homecircle.findmy_flow.FindMySetup.create', return_value=fake):
        try:
            await manager.async_configure(flow_id, {'label': 'Example account', 'consent': True})
            result = await manager.async_configure(flow_id, {'username': 'example@example.invalid', 'password': 'example-secret'})
            result = await finish_progress(result)
            assert result['step_id'] == 'findmy_factor'
            result = await finish_progress(await manager.async_configure(flow_id, {'method': '0'}))
            assert result['step_id'] == 'findmy_code'
            result = await finish_progress(await manager.async_configure(flow_id, {'code': 'synthetic-code'}))
            assert result['step_id'] == 'findmy_factor'
            assert not result.get('errors')
            assert 'another verification' in result['description_placeholders']['verification_notice']
            renewed.request.assert_not_awaited()
            renewed.submit.assert_not_awaited()
            fake.zone_checker.assert_not_awaited()
            fake.client_factory.assert_not_awaited()
            result = await finish_progress(await manager.async_configure(flow_id, {'method': '0'}))
            assert result['step_id'] == 'findmy_code'
            assert 'Enter the newest code' in result['description_placeholders']['verification_notice']
        finally:
            manager.async_abort(flow_id)
            await hass.async_block_till_done()


@pytest.mark.parametrize("reason,status,expected", [
    ("missing_password", None, "findmy_recovery_signin_required"),
    ("factor_required", None, "findmy_recovery_signin_required"),
    ("identity_mismatch", None, "findmy_account_mismatch"),
    ("credentials", None, "findmy_recovery_signin_required"),
    ("protocol", None, "findmy_recovery_protocol"),
    ("transient", 503, "findmy_recovery_transient"),
    ("transient", 429, "findmy_recovery_rate_limited"),
])
async def test_recovery_bootstrap_after_consumed_code_closes_real_flow_without_replay(hass, reason, status, expected):
    from custom_components.homecircle._findmy_runtime.onboarding import RecoveryPETError

    entry, result = await options(hass)
    manager = hass.config_entries.options
    fake = fake_setup()
    fake.login = AsyncMock(return_value="factor")
    factor = SimpleNamespace(request=AsyncMock(), submit=AsyncMock(return_value=3))
    fake.methods = [factor]
    unused_client = fake.client_factory.return_value
    fake.client_factory.side_effect = RecoveryPETError(reason, http_status=status)
    with (
        patch("custom_components.homecircle.findmy_flow.FindMySetup.create", return_value=fake),
        patch("custom_components.homecircle.findmy_flow.Vault.save_account") as save,
    ):
        result = await manager.async_configure(result["flow_id"], {"label":"Example account","consent":True})
        result = await manager.async_configure(result["flow_id"], {"username":"example@example.invalid","password":"example-secret"})
        result = await finish_background_progress(manager, result)
        assert result["step_id"] == "findmy_factor"
        result = await manager.async_configure(result["flow_id"], {"method":"0"})
        result = await finish_background_progress(manager, result)
        assert result["step_id"] == "findmy_code"
        result = await manager.async_configure(result["flow_id"], {"code":"synthetic-private-code"})
        result = await finish_background_progress(manager, result)
        assert result["type"] is FlowResultType.ABORT and result["reason"] == expected
        assert fake.closed and not entry.options
        factor.request.assert_awaited_once_with()
        factor.submit.assert_awaited_once_with("synthetic-private-code")
        fake.client_factory.assert_awaited_once_with(fake.account)
        fake.login.assert_awaited_once()
        fake.account.login.assert_not_awaited()
        unused_client.unlock.assert_not_awaited()
        save.assert_not_called()


@pytest.mark.parametrize("error,expected", [
    ("findmy_recovery_failed", True),
    ("findmy_recovery_transient", True),
    ("findmy_recovery_protocol", True),
    ("findmy_recovery_storage", True),
    ("findmy_no_recovery_device", True),
    ("findmy_code_failed", False),
    ("findmy_code_request_failed", False),
    ("synthetic-private-error", False),
    (None, False),
])
def test_consumed_code_recovery_routing_is_finite_and_stage_specific(error, expected):
    from custom_components.homecircle.findmy_flow import _ends_signin

    assert _ends_signin(error, "findmy_code") is expected
    for step in (None,"findmy_login","findmy_passcode","findmy_discovery","findmy_zone"):
        assert _ends_signin(error, step) is False


def test_consumed_code_abort_messages_exist_in_both_locales():
    import json
    from pathlib import Path
    from custom_components.homecircle.findmy_flow import _CONSUMED_CODE_RECOVERY_ERRORS

    root = Path(__file__).resolve().parents[1] / "custom_components/homecircle"
    for name in ("strings.json","translations/en.json"):
        value = json.loads((root/name).read_bytes())
        for scope in ("config","options"):
            assert _CONSUMED_CODE_RECOVERY_ERRORS <= set(value[scope]["abort"])
            assert "limited" in value[scope]["abort"]["findmy_recovery_rate_limited"]
            assert "do not reuse" in value[scope]["abort"]["findmy_recovery_rate_limited"]


async def test_later_passcode_transient_keeps_its_retry_stage(hass):
    entry,result = await options(hass)
    manager = hass.config_entries.options
    fake = fake_setup()
    await fake.open_recovery()
    fake.login = AsyncMock(return_value="device")
    fake.discover = AsyncMock(side_effect=FindMySetupError("findmy_recovery_transient"))
    flow_id = result["flow_id"]
    try:
        with patch("custom_components.homecircle.findmy_flow.FindMySetup.create",return_value=fake):
            result = await manager.async_configure(flow_id,{"label":"Example account","consent":True})
        result = await manager.async_configure(flow_id,{"username":"example@example.invalid","password":"example-secret"})
        result = await finish_background_progress(manager,result)
        assert result["step_id"] == "findmy_device"
        result = await manager.async_configure(flow_id,{"device":"0"})
        assert result["step_id"] == "findmy_passcode"
        result = await manager.async_configure(flow_id,{"passcode":"synthetic-passcode"})
        result = await finish_background_progress(manager,result)
        assert result["type"] is FlowResultType.FORM and result["step_id"] == "findmy_passcode"
        assert result["errors"] == {"base":"findmy_recovery_transient"}
        assert not fake.closed and not entry.options
        fake.discover.assert_awaited_once_with("0","synthetic-passcode")
    finally:
        if flow_id in {item["flow_id"] for item in manager.async_progress()}:manager.async_abort(flow_id)
        await hass.async_block_till_done()


async def test_empty_recovery_devices_after_consumed_code_ends_without_replay(hass):
    entry,result = await options(hass)
    manager = hass.config_entries.options
    fake = fake_setup()
    fake.login = AsyncMock(return_value="factor")
    factor = SimpleNamespace(request=AsyncMock(),submit=AsyncMock(return_value=3))
    fake.methods = [factor]
    client = fake.client_factory.return_value
    client.recovery_options = AsyncMock(return_value=SimpleNamespace(recoverable=[]))
    with (
        patch("custom_components.homecircle.findmy_flow.FindMySetup.create",return_value=fake),
        patch("custom_components.homecircle.findmy_flow.Vault.save_account") as save,
    ):
        result = await manager.async_configure(result["flow_id"],{"label":"Example account","consent":True})
        result = await manager.async_configure(result["flow_id"],{"username":"example@example.invalid","password":"example-secret"})
        result = await finish_background_progress(manager,result)
        assert result["step_id"] == "findmy_factor"
        result = await manager.async_configure(result["flow_id"],{"method":"0"})
        result = await finish_background_progress(manager,result)
        result = await manager.async_configure(result["flow_id"],{"code":"synthetic-private-code"})
        result = await finish_background_progress(manager,result)
        assert result["type"] is FlowResultType.ABORT and result["reason"] == "findmy_no_recovery_device"
        assert fake.closed and not entry.options
        factor.submit.assert_awaited_once_with("synthetic-private-code")
        fake.login.assert_awaited_once()
        fake.account.login.assert_not_awaited()
        client.unlock.assert_not_awaited()
        client.close.assert_awaited_once()
        save.assert_not_called()
