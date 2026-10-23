"""The replacement's onboarding boundary uses only transient, synthetic secrets."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from copy import deepcopy

import pytest

from custom_components.homecircle.findmy_setup import (
    FindMySetup,
    FindMySetupError,
    device_label,
)

STATES = SimpleNamespace(REQUIRE_2FA=1, LOGGED_IN=3)


def setup():
    session = {
        "account": {
            "username": "example@example.invalid",
            "password": "example-secret",
        },
        "login": {
            "state": 3,
            "data": {
                "dsid": "example-dsid",
                "mobileme_data": {
                    "tokens": {"searchPartyToken": "example-report-token"}
                },
            },
        },
    }
    account = SimpleNamespace(
        login=AsyncMock(return_value=1),
        get_2fa_methods=AsyncMock(return_value=[]),
        close=AsyncMock(),
        _password="example-secret",
        service_tokens={"searchPartyToken": "example-report-token"},
        to_json=lambda: deepcopy(session),
    )
    record = SimpleNamespace(
        device_name="Example iPhone", device_model="iPhone", serial="EXAMPLE-1234"
    )
    first = SimpleNamespace(
        name="Example item",
        identifier="synthetic-item-a",
        to_json=lambda: {"name": "Example item"},
    )
    second = SimpleNamespace(
        name="Second item",
        identifier="synthetic-item-b",
        to_json=lambda: {"name": "Second item"},
    )
    client = SimpleNamespace(
        recovery_options=AsyncMock(return_value=SimpleNamespace(recoverable=[record])),
        unlock=AsyncMock(return_value=[object()]),
        accessories=AsyncMock(return_value=[first, second]),
        close=AsyncMock(),
    )
    flow = FindMySetup(account, AsyncMock(return_value=client), STATES)
    flow.zone_checker = AsyncMock()
    return flow, account, client


async def test_login_discovery_saves_only_selected_keys_without_password():
    flow, account, client = setup()
    assert await flow.login("example@example.invalid", "example-secret") == "factor"
    await flow.open_recovery()
    choices = await flow.discover("0", "synthetic-passcode")
    assert len(choices) == 2
    session, selected = flow.selected_payload([choices[0]["value"]])
    assert len(selected) == 1
    assert session["account"]["password"] is None
    assert account._password is None
    assert flow.device_choices()[0]["label"] == "Example iPhone (ending 1234)"
    assert not hasattr(client, "join") and not hasattr(client, "rename")
    await flow.close()
    assert not flow.accessories and not flow.records
    client.close.assert_awaited_once()
    account.close.assert_awaited_once()


async def test_close_drops_transient_auth_even_if_dependency_close_fails():
    flow, account, _ = setup()
    account._login_state_data = {"idms_pet": "synthetic-pet"}
    account._account_info = {"account_name": "example@example.invalid"}
    account._username = "example@example.invalid"
    account._recovery_pet = "synthetic-pet"
    account._recovery_pet_at = account._gsa_pet_at = 1
    account._anisette = SimpleNamespace(
        _ani_data={"X-Apple-I-MD": "synthetic-otp"},
        _ani=object(), _state_blob=object(),
    )
    account.close.side_effect = RuntimeError("synthetic-private-response")
    await flow.close()
    assert account._login_state_data == {}
    assert account._account_info is account._username is account._password is None
    assert account._recovery_pet is account._recovery_pet_at is account._gsa_pet_at is None
    assert account._anisette._ani_data is account._anisette._ani is account._anisette._state_blob is None
    await flow.close()
    account.close.assert_awaited_once()


async def test_factor_verification_uses_selected_method_and_never_auto_accepts_terms():
    flow, account, client = setup()
    method = SimpleNamespace(request=AsyncMock(), submit=AsyncMock(return_value=3))
    flow.methods = [method]
    await flow.request_code("0")
    await flow.verify_code("synthetic-code")
    method.request.assert_awaited_once()
    method.submit.assert_awaited_once_with("synthetic-code")
    assert flow.client is client
    method.submit.return_value = 2
    with pytest.raises(FindMySetupError, match="findmy_account_attention"):
        await flow.verify_code("synthetic-code")
    await flow.close()


async def test_failed_recovery_is_bounded_and_never_returns_exception_secrets():
    flow, account, client = setup()
    await flow.open_recovery()
    client.unlock.side_effect = ValueError("synthetic-private-response")
    for _ in range(3):
        with pytest.raises(FindMySetupError, match="findmy_recovery_failed") as caught:
            await flow.discover("0", "synthetic-passcode")
        assert "private-response" not in str(caught.value)
        assert account._password is None
    with pytest.raises(FindMySetupError, match="findmy_recovery_limit"):
        await flow.discover("0", "synthetic-passcode")
    assert client.unlock.await_count == 3
    await flow.close()


@pytest.mark.parametrize("keys", [[], None])
async def test_empty_recovery_cannot_mark_success_or_retry_discovery(keys, caplog):
    flow, account, client = setup()
    await flow.open_recovery()
    client.unlock.return_value = keys
    account._recovery_diagnostics["recovered_keys_present"] = True
    with pytest.raises(FindMySetupError, match="findmy_recovery_failed"):
        await flow.discover("0", "synthetic-private-passcode")
    assert flow.keys_recovered is False
    assert flow.unlock_attempts == 1
    assert account._recovery_diagnostics["recovered_keys_present"] is False
    assert account._recovery_diagnostics["unlock_phase"] == "pcs_keys"
    client.unlock.assert_awaited_once()
    client.accessories.assert_not_awaited()
    with pytest.raises(FindMySetupError, match="findmy_setup_closed"):
        await flow.retry_discovery()
    client.unlock.assert_awaited_once()
    assert account._password is None
    assert "synthetic-private-passcode" not in caplog.text
    assert "'recovered_keys_present': False" in caplog.text
    await flow.close()


async def test_unselected_and_duplicate_item_ids_are_not_persisted():
    flow, _, _ = setup()
    await flow.open_recovery()
    choices = await flow.discover("0", "synthetic-passcode")
    for chosen in ([], ["unknown"], [choices[0]["value"]] * 2):
        with pytest.raises(FindMySetupError, match="findmy_select_items"):
            flow.selected_payload(chosen)
    await flow.close()
    with pytest.raises(FindMySetupError, match="findmy_select_items"):
        flow.selected_payload([choices[0]["value"]])


def test_device_labels_explain_missing_names_without_inventing_association():
    assert (
        device_label(
            SimpleNamespace(device_name=None, device_model=None, serial="EXAMPLE-5678")
        )
        == "Trusted Apple device (ending 5678)"
    )


def test_replacement_namespace_and_logs_are_isolated():
    import logging
    from pathlib import Path
    import subprocess
    import sys
    from custom_components.homecircle.findmy_setup import sdk

    _, _, _, client = sdk()
    assert client.__module__ == "custom_components.homecircle._vendor_findmy.icloud"
    assert logging.getLogger(
        "custom_components.homecircle._vendor_findmy.reports.account"
    ).disabled
    # A fresh interpreter proves the supported SDK does not rely on cached
    # imports of the retired local-Mac CLI/decryptor.
    code = """
import importlib.abc
import sys
retired = {
    'custom_components.homecircle._vendor_findmy.plist',
    'custom_components.homecircle._vendor_findmy.__main__',
}
class RejectRetired(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in retired:
            raise AssertionError('retired local-Mac module imported')
sys.meta_path.insert(0, RejectRetired())
from custom_components.homecircle.findmy_setup import sdk
*_, client = sdk()
assert client.__module__ == 'custom_components.homecircle._vendor_findmy.icloud'
assert not retired.intersection(sys.modules)
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", "import sys; sys.path.insert(0, sys.argv[1]); " + code,
         str(Path(__file__).resolve().parents[1])],
        capture_output=True, timeout=30, check=False,
    )
    assert result.returncode == 0, "supported SDK must import without retired local-Mac modules"


async def test_missing_accessory_ids_use_distinct_stable_keys():
    flow, _, client = setup()
    client.accessories.return_value = [
        SimpleNamespace(
            identifier=None,
            name="Same name",
            to_json=lambda: {"master_key": "example-key-a"},
        ),
        SimpleNamespace(
            identifier=None,
            name="Same name",
            to_json=lambda: {"master_key": "example-key-b"},
        ),
    ]
    await flow.open_recovery()
    choices = await flow.discover("0", "synthetic-passcode")
    assert len({item["value"] for item in choices}) == 2
    assert choices == await flow.discover("0", "synthetic-passcode")
    await flow.close()


async def test_duplicate_identity_does_not_silently_drop_an_item():
    flow, _, client = setup()
    first = client.accessories.return_value[0]
    client.accessories.return_value = [first, first]
    await flow.open_recovery()
    with pytest.raises(FindMySetupError, match="findmy_duplicate_item"):
        await flow.discover("0", "synthetic-passcode")
    assert not flow.accessories
    await flow.close()


def test_reconnection_reuses_identity_and_discards_old_login(monkeypatch):
    from custom_components.homecircle import findmy_setup

    seen = {}

    class Account:
        @classmethod
        def from_json(cls, state, **kwargs):
            seen.update(state)
            return SimpleNamespace()

    monkeypatch.setattr(
        findmy_setup, "sdk", lambda: (Account, None, STATES, SimpleNamespace(open=None))
    )
    session = {
        "ids": {"uid": "example-user", "devid": "example-device"},
        "account": {
            "username": "example@example.invalid",
            "password": None,
            "info": {"example": True},
        },
        "login": {"state": 3, "data": {"example": True}},
        "anisette": {},
    }
    created = FindMySetup.create("example-libraries", session)
    assert created.recovery_guard_required
    assert seen["ids"] == session["ids"]
    assert seen["login"] == {"state": 0, "data": {}}
    assert seen["account"]["info"] is None
    assert session["login"]["state"] == 3


async def test_recovery_preserves_migrated_identifiers_and_actual_report():
    flow, _, client = setup()
    material = {"master_key": "01" * 28, "skn": "02" * 32, "sks": "03" * 32}
    client.accessories.return_value = [
        SimpleNamespace(
            identifier="new-sdk-identity",
            name="Renamed item",
            to_json=lambda: deepcopy(material),
        )
    ]
    flow.previous_items = {
        "legacy": {
            "accessory": deepcopy(material),
            "report": {"last_seen": "2026-10-01T12:00:00+00:00"},
        }
    }
    await flow.open_recovery()
    assert (await flow.discover("0", "synthetic-passcode"))[0]["value"] == "legacy"
    _, payload = flow.selected_payload(["legacy"])
    assert payload["legacy"]["report"]["last_seen"] == "2026-10-01T12:00:00+00:00"
    await flow.close()


def test_adi_dependency_cannot_log_persistent_tokens():
    import logging
    from custom_components.homecircle.findmy_setup import sdk

    sdk()
    assert logging.getLogger("anisette._adi").disabled
    assert logging.getLogger("anisette._session").disabled


async def test_close_still_closes_account_when_keychain_cleanup_fails():
    flow, account, client = setup()
    await flow.open_recovery()
    client.close.side_effect = RuntimeError("synthetic protected response")
    await flow.close()
    account.close.assert_awaited_once()
    assert flow.closed and not flow.accessories


async def test_reconnect_uses_existing_keys_without_keychain_recovery(monkeypatch):
    flow, account, client = setup()
    account.login.return_value = STATES.LOGGED_IN
    flow.discover_new = False
    flow.previous_items = {
        "legacy": {"accessory": {"type": "accessory"}, "report": None}
    }
    from custom_components.homecircle import _vendor_findmy

    accessory = SimpleNamespace(identifier="synthetic-id", name="Example item")
    monkeypatch.setattr(
        _vendor_findmy.FindMyAccessory, "from_json", lambda _: accessory
    )
    assert await flow.login("example@example.invalid", "example-secret") == "select"
    flow.client_factory.assert_not_awaited()
    client.unlock.assert_not_awaited()
    assert list(flow.accessories) == ["legacy"]
    assert account._password is None
    await flow.close()


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (TimeoutError("synthetic-private-response"), "findmy_signin_timeout"),
        (OSError("synthetic-private-response"), "findmy_signin_network"),
        (RuntimeError("synthetic-private-response"), "findmy_signin_failed"),
    ],
)
async def test_signin_errors_do_not_blame_credentials_or_log_private_text(
    failure, expected, caplog
):
    flow, account, _ = setup()
    account.login.side_effect = failure
    with pytest.raises(FindMySetupError, match=expected):
        await flow.login("example@example.invalid", "example-secret")
    assert expected in caplog.text
    assert "synthetic-private-response" not in caplog.text
    assert "example-secret" not in caplog.text
    assert "example@example.invalid" not in caplog.text


async def test_identity_failure_happens_before_credentials_are_submitted(caplog):
    flow, account, _ = setup()
    account._anisette = SimpleNamespace(
        _get_ani=AsyncMock(side_effect=RuntimeError("synthetic-private-response"))
    )
    with pytest.raises(FindMySetupError, match="findmy_identity_failed"):
        await flow.login("example@example.invalid", "example-secret")
    account.login.assert_not_awaited()
    assert "synthetic-private-response" not in caplog.text


@pytest.mark.parametrize('status,what,retry,expected', [
    (503, 'The Grand Slam request', None, 'request=gsa http=503 retry_after_seconds=None'),
    (429, 'The two-factor request', 65.5, 'request=verification http=429 retry_after_seconds=65'),
    (503, 'synthetic-private-request', float('nan'), 'request=unknown http=503 retry_after_seconds=None'),
    (503, 'The Grand Slam request', float('inf'), 'request=gsa http=503 retry_after_seconds=None'),
])
def test_service_refusal_retains_only_bounded_diagnostics(status, what, retry, expected, caplog):
    from custom_components.homecircle.findmy_setup import signin_error
    from custom_components.homecircle._vendor_findmy.errors import AppleServiceUnavailableError
    error = AppleServiceUnavailableError(status, what)
    error.retry_after = retry
    assert signin_error(error, 'signin') == 'findmy_apple_unavailable'
    assert expected in caplog.text
    assert 'synthetic-private-request' not in caplog.text


async def test_recovery_failure_is_distinct_from_invalid_credentials(caplog):
    flow, account, client = setup()
    account.login.return_value = STATES.LOGGED_IN
    client.recovery_options.side_effect = RuntimeError("synthetic-private-response")
    with pytest.raises(FindMySetupError, match="findmy_recovery_failed"):
        await flow.login("example@example.invalid", "example-secret")
    assert account._password is None
    assert "synthetic-private-response" not in caplog.text


@pytest.mark.parametrize('phase, expected', [
    ('init', 'findmy_initial_refused'),
    ('complete', 'findmy_credentials_rejected'),
])
async def test_apple_rejection_logs_only_numeric_code_and_fixed_phase(caplog, phase, expected):
    from custom_components.homecircle._vendor_findmy.errors import (
        InvalidCredentialsError,
    )

    flow, account, _ = setup()
    account.login.side_effect = InvalidCredentialsError(
        "synthetic-private-response", status_code=-12345, phase=phase
    )
    with pytest.raises(FindMySetupError, match=expected):
        await flow.login("  example@example.invalid  ", "example-secret")
    account.login.assert_awaited_once_with("example@example.invalid", "example-secret")
    assert f"phase={phase} apple_code=-12345" in caplog.text
    assert "synthetic-private-response" not in caplog.text
    assert "example-secret" not in caplog.text
    assert "example@example.invalid" not in caplog.text
    invalid = InvalidCredentialsError(
        "synthetic-private-response",
        status_code="synthetic-private-code",
        phase="private",
    )
    assert invalid.status_code is None and invalid.phase is None


async def test_real_sdk_initial_rejection_retains_safe_status():
    from custom_components.homecircle.findmy_setup import sdk
    from custom_components.homecircle._vendor_findmy.errors import (
        InvalidCredentialsError,
    )

    account_type, provider_type, _, _ = sdk()
    account = account_type(provider_type())
    account._gsa_request = AsyncMock(
        return_value={"Status": {"ec": -12345, "em": "synthetic-private-response"}}
    )
    try:
        with pytest.raises(InvalidCredentialsError) as caught:
            await account._gsa_authenticate("example@example.invalid", "example-secret")
        assert caught.value.status_code == -12345
        assert caught.value.phase == "init"
    finally:
        await account.close()


async def test_account_identity_pair_is_never_replaced_by_native_provisioning():
    flow, account, _ = setup()
    account._uid = "synthetic-saved-local-user"
    account._devid = "synthetic-saved-device"
    device = SimpleNamespace(
        local_user_uuid="synthetic-provisioned-local-user",
        unique_device_identifier="synthetic-provisioned-device",
    )
    account._anisette = SimpleNamespace(
        _get_ani=AsyncMock(
            return_value=SimpleNamespace(_ani_provider=SimpleNamespace(device=device))
        )
    )
    observed = []

    async def sign_in(username, password):
        observed.append((account._uid, account._devid))
        return STATES.REQUIRE_2FA

    account.login.side_effect = sign_in
    await flow.login("example@example.invalid", "example-secret")
    expected = ("synthetic-saved-local-user", "synthetic-saved-device")
    assert observed == [expected]
    await flow.login("example@example.invalid", "example-secret")
    assert observed == [expected, expected]


@pytest.mark.parametrize('phase,expected', [
    ('validation', 'findmy_code_failed'),
    ('reauthentication', 'findmy_code_signin_failed'),
    ('delegate', 'findmy_code_delegate_failed'),
])
async def test_verification_failure_reports_stage_without_blaming_code(phase, expected, caplog):
    flow, account, _ = setup()
    account._verification_stage = phase
    account._verification_http_status = 200
    flow.factor = SimpleNamespace(submit=AsyncMock(side_effect=RuntimeError('synthetic-private-response')))
    with pytest.raises(FindMySetupError, match=expected):
        await flow.verify_code('synthetic-private-code')
    assert f'phase={phase}' in caplog.text
    assert 'validation_http=200' in caplog.text
    assert 'synthetic-private' not in caplog.text
    await flow.close()


async def test_recovery_failure_after_verification_is_not_a_code_failure(caplog):
    flow, account, _ = setup()
    account._verification_stage = 'complete'
    flow.factor = SimpleNamespace(submit=AsyncMock(return_value=3))
    flow.open_recovery = AsyncMock(side_effect=RuntimeError('synthetic-secret-response'))
    with pytest.raises(FindMySetupError, match='findmy_recovery_failed'):
        await flow.verify_code('synthetic-secret-code')
    assert 'stage=recovery' in caplog.text
    assert 'synthetic-secret' not in caplog.text
    await flow.close()


async def test_delegate_diagnostics_filter_every_field_before_logging(caplog):
    flow, account, _ = setup()
    account._verification_stage = 'delegate'
    account._delegate_diagnostics = {
        'http': 403, 'top_status': 'synthetic-private-status', 'service_status': 1000001,
        'pet_present': True, 'localized_error_present': True,
        'unauthorized': 'synthetic-private-token', 'extra': 'synthetic-private-response',
    }
    flow.factor = SimpleNamespace(submit=AsyncMock(side_effect=RuntimeError('synthetic-private-error')))
    with pytest.raises(FindMySetupError, match='findmy_code_delegate_failed'):
        await flow.verify_code('synthetic-private-code')
    assert '403' in caplog.text
    assert 'synthetic-private' not in caplog.text
    assert '1000001' not in caplog.text
    await flow.close()


async def test_signin_without_factor_keeps_transient_password_for_pet_bootstrap():
    flow, account, client = setup()
    account.login.return_value = STATES.LOGGED_IN
    observed = []
    async def open_client(acc):
        observed.append(acc._password)
        return client
    flow.client_factory = open_client
    assert await flow.login('example@example.invalid', 'example-secret') == 'device'
    assert observed == ['example-secret']
    await flow.close()
    assert account._password is None


async def test_preflight_rejection_does_not_recover_or_log_response(caplog):
    flow, account, _ = setup()
    account._recovery_diagnostics = {'operation_http': 401, 'operation_server_code': 'synthetic-private-server-message'}
    flow.zone_checker.side_effect = RuntimeError('synthetic-private-response')
    with pytest.raises(FindMySetupError, match='findmy_zone_denied'):
        await flow.prepare_recovery()
    flow.client_factory.assert_not_awaited()
    assert flow.unlock_attempts == 0
    assert 'synthetic-private' not in caplog.text
    await flow.close()



@pytest.mark.parametrize('accepted', [True, False])
async def test_settings_pair_comparison_restores_rejected_tokens_and_never_recovers(monkeypatch, accepted):
    from custom_components.homecircle._vendor_findmy.cloudkit import client as module
    from custom_components.homecircle._vendor_findmy.errors import UnauthorizedError
    flow, account, _ = setup()
    flow.zone_checker = None
    original = {'mmeAuthToken': 'original-mme', 'cloudKitToken': 'settings-ck', 'searchPartyToken': 'original-report'}
    account._login_state_data = {'mobileme_data': {'tokens': original}}
    # SimpleNamespace does not expose the SDK property; update it through a tiny wrapper.
    class Account(SimpleNamespace):
        @property
        def service_tokens(self):
            return self._login_state_data['mobileme_data']['tokens']
    account = Account(**account.__dict__)
    flow.account = account
    account._recovery_diagnostics = {}
    account._settings_cloudkit_pair = {'mmeAuthToken': 'settings-mme', 'cloudKitToken': 'settings-ck'}
    seen, clients = [], []
    def factory(acc, **kwargs):
        async def retrieve(name):
            assert name == 'BeaconStore'
            seen.append(dict(acc.service_tokens))
            status = 200 if accepted and acc.service_tokens['mmeAuthToken'] == 'settings-mme' else 401
            acc._recovery_diagnostics['operation_http'] = status
            if status == 401:
                raise UnauthorizedError('synthetic-private-response')
            return [object()]
        opened = SimpleNamespace(zone_retrieve=retrieve, close=AsyncMock())
        clients.append(opened)
        return opened
    monkeypatch.setattr(module, 'AsyncCloudKitClient', factory)
    try:
        if accepted:
            await flow.check_zone_access()
            assert account.service_tokens['mmeAuthToken'] == 'settings-mme'
        else:
            with pytest.raises(FindMySetupError):
                await flow.check_zone_access()
            assert account.service_tokens is original
            with pytest.raises(FindMySetupError):
                await flow.check_zone_access()
            assert len(seen) == 3  # Manual retry never repeats the candidate pair.
        assert seen[0] == original
        assert seen[1]['mmeAuthToken'] == 'settings-mme'
        assert account.service_tokens['searchPartyToken'] == 'original-report'
        for opened in clients:
            opened.close.assert_awaited_once()
        flow.client_factory.assert_not_awaited()
        assert flow.unlock_attempts == 0
    finally:
        await flow.close()


@pytest.mark.parametrize("reason,expected", [
    ("missing_password", "findmy_recovery_signin_required"),
    ("factor_required", "findmy_recovery_signin_required"),
    ("credentials", "findmy_recovery_signin_required"),
    ("identity_mismatch", "findmy_account_mismatch"),
    ("transient", "findmy_recovery_transient"),
    ("protocol", "findmy_recovery_protocol"),
])
async def test_recovery_credential_failure_after_verification_keeps_actionable_error(reason, expected, caplog):
    from custom_components.homecircle._findmy_runtime.onboarding import RecoveryPETError

    flow, account, client = setup()
    flow.factor = SimpleNamespace(submit=AsyncMock(return_value=STATES.LOGGED_IN))
    factor = flow.factor
    flow.prepare_recovery = AsyncMock(side_effect=RecoveryPETError(reason))
    with pytest.raises(FindMySetupError, match="^" + expected + "$"):
        await flow.verify_code("synthetic-private-code")
    factor.submit.assert_awaited_once_with("synthetic-private-code")
    flow.prepare_recovery.assert_awaited_once_with()
    account.login.assert_not_awaited()
    client.unlock.assert_not_awaited()
    assert "synthetic-private-code" not in caplog.text
    await flow.close()


@pytest.mark.parametrize("reason", [
    "missing_password", "factor_required", "credentials", "identity_mismatch", "transient", "protocol",
])
async def test_recovery_bootstrap_logs_only_fixed_credential_reason_and_status(reason, caplog):
    from custom_components.homecircle._findmy_runtime.onboarding import RecoveryPETError

    flow, account, client = setup()
    error = RecoveryPETError(reason, http_status=503)
    async def open_client(current):
        current._recovery_diagnostics.update(phase="pet_refresh", private="synthetic-private-response")
        raise error
    flow.client_factory = AsyncMock(side_effect=open_client)
    with pytest.raises(RecoveryPETError) as caught:
        await flow.open_recovery()
    assert caught.value is error
    flow.client_factory.assert_awaited_once_with(account)
    assert "'recovery_credential_reason': '" + reason + "'" in caplog.text
    assert "'recovery_credential_http': 503" in caplog.text
    assert "'error_class': 'RecoveryPETError'" in caplog.text
    assert "synthetic-private" not in caplog.text
    assert account._password is None
    assert account._recovery_pet is None
    account.login.assert_not_awaited()
    client.unlock.assert_not_awaited()
    await flow.close()


async def test_recovery_bootstrap_rejects_unknown_credential_metadata(caplog):
    from custom_components.homecircle._findmy_runtime.onboarding import RecoveryPETError

    flow, account, client = setup()
    error = RecoveryPETError("protocol")
    error.reason = "synthetic-private-reason"
    error.http_status = True
    flow.client_factory = AsyncMock(side_effect=error)
    with pytest.raises(RecoveryPETError) as caught:
        await flow.open_recovery()
    assert caught.value is error
    assert "'recovery_credential_reason': None" in caplog.text
    assert "'recovery_credential_http': None" in caplog.text
    assert "synthetic-private" not in caplog.text
    account.login.assert_not_awaited()
    client.unlock.assert_not_awaited()
    await flow.close()


@pytest.mark.parametrize("phase", ["init", "complete"])
async def test_recovery_bootstrap_logs_current_pet_phase_and_bounded_retry_only(phase, caplog):
    from custom_components.homecircle._findmy_runtime.onboarding import RecoveryPETError

    flow, account, _ = setup()
    error = RecoveryPETError("transient", http_status=429, auth_phase=phase, retry_after=12.25)
    account._signin_diagnostics = {"phase": "init", "http": 200, "retry_after": 999,
                                    "body": "synthetic-private-response-canary"}
    flow.client_factory.side_effect = error
    with pytest.raises(RecoveryPETError) as caught:
        await flow.open_recovery()
    assert caught.value is error
    assert "'recovery_credential_phase': '" + phase + "'" in caplog.text
    assert "'recovery_credential_http': 429" in caplog.text
    assert "'recovery_credential_retry_after_seconds': 13" in caplog.text
    assert "synthetic-private" not in caplog.text and "999" not in caplog.text
    await flow.close()


@pytest.mark.parametrize("phase,retry", [
    (True, True), ("synthetic-private-phase", "synthetic-private-header"),
    ("init", -1), ("complete", 86401), (None, float("nan")), (None, 1.0),
])
async def test_recovery_bootstrap_revalidates_mutated_pet_error_context(phase, retry, caplog):
    from custom_components.homecircle._findmy_runtime.onboarding import RecoveryPETError

    flow, _, _ = setup()
    error = RecoveryPETError("transient", http_status=429)
    error.auth_phase, error.retry_after_seconds = phase, retry
    flow.client_factory.side_effect = error
    with pytest.raises(RecoveryPETError) as caught:
        await flow.open_recovery()
    assert caught.value is error
    expected = phase if type(phase) is str and phase in ("init", "complete") else None
    assert "'recovery_credential_phase': " + repr(expected) in caplog.text
    assert "'recovery_credential_retry_after_seconds': None" in caplog.text
    assert "synthetic-private" not in caplog.text
    await flow.close()


def _synthetic_discovery_exception(error_type=RuntimeError, *, filename="pcs.py",
                                   function="unwrap_zone", module=None, offset=0):
    """Actual tracebacks with synthetic private data; no provider code executes."""
    import ast

    module = module or "custom_components.homecircle._vendor_findmy.cloudkit." + filename[:-3]
    source = "/synthetic-private-path/custom_components/homecircle/_vendor_findmy/cloudkit/" + filename
    program = ast.parse("def " + function + "():\n"
                        "    private_key = 'synthetic-private-key-canary'\n"
                        "    raise error_type('synthetic-private-response-canary')\n")
    ast.increment_lineno(program, offset)
    namespace = {"__name__": module, "error_type": error_type}
    exec(compile(program, source, "exec"), namespace)
    try:
        namespace[function]()
    except Exception as error:
        return error
    raise AssertionError("synthetic exception was not raised")


@pytest.mark.parametrize("filename,function", [("pcs.py", "unwrap_zone"), ("beacons.py", "zone_keys")])
def test_discovery_error_site_reports_only_bound_own_source(filename, function):
    from custom_components.homecircle.findmy_setup import _discovery_failure_site

    safe = _discovery_failure_site(_synthetic_discovery_exception(filename=filename, function=function))
    assert safe == {
        "error_module": "custom_components.homecircle._vendor_findmy.cloudkit." + filename[:-3],
        "error_file": filename, "error_function": function, "error_line": 3,
    }
    assert "synthetic-private" not in repr(safe)


@pytest.mark.parametrize("change", ["module", "filename", "function", "line"])
def test_discovery_error_site_rejects_unbound_or_oversized_sites(change):
    from custom_components.homecircle.findmy_setup import _discovery_failure_site

    arguments = {
        "module": {"module": "synthetic.private.module"},
        "filename": {"filename": "synthetic-private-file.py",
                     "module": "custom_components.homecircle._vendor_findmy.cloudkit.pcs"},
        "function": {"function": "synthetic_private_function"},
        "line": {"offset": 100000},
    }[change]
    safe = _discovery_failure_site(_synthetic_discovery_exception(**arguments))
    assert safe == {"error_module": None, "error_file": None,
                    "error_function": None, "error_line": None}
    assert "synthetic-private" not in repr(safe)


def test_discovery_error_site_prefers_innermost_allowlisted_frame():
    from custom_components.homecircle.findmy_setup import _discovery_failure_site

    namespace = {"__name__": "custom_components.homecircle._vendor_findmy.cloudkit.pcs"}
    source = "/synthetic-private-path/custom_components/homecircle/_vendor_findmy/cloudkit/pcs.py"
    exec(compile("def unwrap_protection():\n    return unwrap_zone()\n"
                 "def unwrap_zone():\n    raise RuntimeError('synthetic-private-response-canary')\n",
                 source, "exec"), namespace)
    try:
        namespace["unwrap_protection"]()
    except RuntimeError as error:
        safe = _discovery_failure_site(error)
    assert safe["error_function"] == "unwrap_zone" and safe["error_line"] == 4
    assert "synthetic-private" not in repr(safe)


@pytest.mark.parametrize("name", ["PCSError", "MissingKeyError", "BeaconExportError", "SyntheticPrivateError"])
async def test_discovery_logs_fixed_pcs_subclass_and_site_without_retry(name, caplog):
    flow, account, client = setup()
    await flow.open_recovery()
    flow.keys_recovered = True
    account._recovery_diagnostics.update(recovered_keys_present=True, operation_http=200,
                                         operation_type=201, private="synthetic-private-diagnostic-canary")
    error_type = type(name, (RuntimeError,), {})
    client.accessories.side_effect = _synthetic_discovery_exception(error_type)
    with pytest.raises(FindMySetupError, match="^findmy_recovery_failed$"):
        await flow.retry_discovery()
    expected = name if name != "SyntheticPrivateError" else "other"
    assert "'error_class': '" + expected + "'" in caplog.text
    assert "'error_file': 'pcs.py'" in caplog.text
    assert "'error_function': 'unwrap_zone'" in caplog.text
    assert "'error_line': 3" in caplog.text
    assert "'recovered_keys_present': True" in caplog.text
    assert "synthetic-private" not in caplog.text
    assert "SyntheticPrivateError" not in caplog.text
    assert flow.keys_recovered is True and account._password is None
    assert flow.unlock_attempts == 0
    client.unlock.assert_not_awaited()
    client.accessories.assert_awaited_once_with()
    account.login.assert_not_awaited()
    await flow.close()


_OUTER_AUTH_TEST_CODES = (
    "owner_review_context_required", "outer_digest_unsupported", "outer_signer_mismatch",
    "outer_covered_data_unreadable", "outer_signature_rejected",
)


@pytest.mark.parametrize("reason", _OUTER_AUTH_TEST_CODES)
def test_outer_auth_reason_sanitizer_accepts_only_exact_pcs_codes(reason):
    from custom_components.homecircle._vendor_findmy.cloudkit.pcs import PCSError
    from custom_components.homecircle.findmy_setup import _outer_auth_failure_reason

    error = PCSError("synthetic-private-response-canary")
    error._homecircle_outer_auth_reason = reason
    assert _outer_auth_failure_reason(error) == reason


@pytest.mark.parametrize("case", [
    "missing", "none", "bool", "number", "dict", "secret", "unknown",
    "str_subclass", "property_value", "dict_subclass", "name_impostor", "pcs_subclass",
])
def test_outer_auth_reason_sanitizer_redacts_mutated_or_spoofed_metadata(case):
    from custom_components.homecircle._vendor_findmy.cloudkit.pcs import PCSError
    from custom_components.homecircle.findmy_setup import _outer_auth_failure_reason

    calls = []
    def forbidden(*args):
        calls.append("synthetic-private-property-canary")
        raise AssertionError("metadata accessor executed untrusted code")
    class SecretString(str):
        __eq__ = forbidden
    class SecretDict(dict):
        get = forbidden
    error = PCSError("synthetic-private-response-canary")
    if case == "dict_subclass":
        error.__dict__ = SecretDict(_homecircle_outer_auth_reason=_OUTER_AUTH_TEST_CODES[0])
    elif case == "name_impostor":
        error = type("PCSError", (RuntimeError,), {"__getattribute__": forbidden})("synthetic-private-response")
    elif case == "pcs_subclass":
        class Derived(PCSError):
            __getattribute__ = forbidden
            _homecircle_outer_auth_reason = property(forbidden)
        error = Derived("synthetic-private-response")
    elif case != "missing":
        error._homecircle_outer_auth_reason = {
            "none": None, "bool": True, "number": 1, "dict": {"secret": "synthetic-private-key-canary"},
            "secret": "synthetic-private-reason-canary", "unknown": "unknown",
            "str_subclass": SecretString(_OUTER_AUTH_TEST_CODES[0]), "property_value": property(forbidden),
        }[case]
    assert _outer_auth_failure_reason(error) is None
    assert calls == []


@pytest.mark.parametrize("reason", [*_OUTER_AUTH_TEST_CODES, "invalid", "spoofed"])
async def test_discovery_logs_only_fixed_outer_auth_reason_without_reproof(reason, caplog):
    from custom_components.homecircle._vendor_findmy.cloudkit.pcs import PCSError

    flow, account, client = setup()
    await flow.open_recovery()
    flow.keys_recovered = True
    error_type = type("PCSError", (RuntimeError,), {}) if reason == "spoofed" else PCSError
    error = _synthetic_discovery_exception(error_type)
    error._homecircle_outer_auth_reason = reason if reason in _OUTER_AUTH_TEST_CODES else "synthetic-private-reason-canary"
    client.accessories.side_effect = error
    with pytest.raises(FindMySetupError, match="^findmy_recovery_failed$"):
        await flow.retry_discovery()
    expected = reason if reason in _OUTER_AUTH_TEST_CODES else None
    assert "'outer_auth_reason': " + repr(expected) in caplog.text
    assert "synthetic-private" not in caplog.text
    assert flow.keys_recovered is True and flow.unlock_attempts == 0 and account._password is None
    client.unlock.assert_not_awaited()
    client.accessories.assert_awaited_once_with()
    account.login.assert_not_awaited()
    await flow.close()


async def test_outer_auth_import_failure_preserves_original_discovery_failure(monkeypatch, caplog):
    import builtins

    flow, account, client = setup()
    await flow.open_recovery()
    flow.keys_recovered = True
    client.accessories.side_effect = RuntimeError("synthetic-private-original-canary")
    original_import = builtins.__import__
    calls = []
    def unavailable(name, *args, **kwargs):
        if name.endswith("cloudkit.pcs"):
            calls.append(name)
            raise RuntimeError("synthetic-private-dependency-canary")
        return original_import(name, *args, **kwargs)
    with monkeypatch.context() as context:
        context.setattr(builtins, "__import__", unavailable)
        with pytest.raises(FindMySetupError, match="^findmy_recovery_failed$"):
            await flow.retry_discovery()
    assert len(calls) == 1
    assert "'outer_auth_reason': None" in caplog.text
    assert "synthetic-private" not in caplog.text
    assert flow.keys_recovered is True and flow.unlock_attempts == 0 and account._password is None
    client.unlock.assert_not_awaited()
    account.login.assert_not_awaited()
    await flow.close()
