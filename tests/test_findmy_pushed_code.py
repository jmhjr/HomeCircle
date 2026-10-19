"""Handle Apple's pushed-code response without skipping proof or requesting SMS."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.homecircle.findmy_setup import FindMySetup, sdk


async def authenticate(monkeypatch, tmp_path, status, proof_valid=True):
    account_type, provider_type, states, _ = sdk()
    from custom_components.homecircle._vendor_findmy.reports import account as module
    account = account_type(provider_type(libs_path=tmp_path / 'unused.bin'))
    user = SimpleNamespace(
        start_authentication=lambda: (None, b'synthetic-public'),
        process_challenge=lambda *_: b'synthetic-proof',
        verify_session=Mock(), authenticated=lambda: proof_valid,
        get_session_key=lambda: b'synthetic-session',
    )
    monkeypatch.setattr(module.srp, 'User', lambda *_args, **_kwargs: user)
    monkeypatch.setattr(module.util.crypto, 'encrypt_password', lambda *_: b'synthetic-password-key')
    monkeypatch.setattr(module.util.crypto, 'decrypt_spd_aes_cbc', lambda *_: b'synthetic-spd')
    monkeypatch.setattr(module.util.parsers, 'decode_plist', lambda *_: {
        'adsid': 'synthetic-account-id', 'GsIdmsToken': 'synthetic-token',
        't': {'com.apple.gs.idms.pet': {'token': 'synthetic-pet'}},
    })
    account._gsa_request = AsyncMock(side_effect=[
        {'Status': {'ec': 0}, 'sp': 's2k', 's': b'salt', 'i': 1, 'B': b'public', 'c': 'challenge'},
        {'Status': status, 'M2': b'server-proof', 'spd': b'encrypted'},
    ])
    return account, states, user


async def test_pushed_code_reaches_entry_without_sms_or_duplicate_request(monkeypatch, tmp_path):
    account, states, user = await authenticate(monkeypatch, tmp_path, {'ec': 0, 'hsc': 409})
    try:
        account._login_mobileme = AsyncMock()
        account._sms_2fa_request = AsyncMock()
        assert await account.login('example@example.invalid', 'synthetic-password') == states.REQUIRE_2FA
        user.verify_session.assert_called_once_with(b'server-proof')
        methods = await account.get_2fa_methods()
        assert len(methods) == 1
        assert 'TrustedDevice' in type(methods[0]).__name__
        flow = FindMySetup(account, AsyncMock(), states)
        flow.methods = list(methods)
        await flow.request_code('0')
        assert flow.factor is methods[0]
        account._sms_2fa_request.assert_not_awaited()
        account._login_mobileme.assert_not_awaited()
    finally:
        await account.close()


async def test_pushed_code_does_not_bypass_invalid_server_proof(monkeypatch, tmp_path):
    account, _, _ = await authenticate(monkeypatch, tmp_path, {'ec': 0, 'hsc': 409}, False)
    try:
        from custom_components.homecircle._vendor_findmy.errors import UnhandledProtocolError
        with pytest.raises(UnhandledProtocolError, match='verify session'):
            await account.login('example@example.invalid', 'synthetic-password')
        assert not account._pushed_code_pending
    finally:
        await account.close()


async def test_pushed_code_does_not_override_apple_rejection(monkeypatch, tmp_path):
    account, _, user = await authenticate(monkeypatch, tmp_path, {'ec': -20101, 'hsc': 409, 'em': 'synthetic'})
    try:
        from custom_components.homecircle._vendor_findmy.errors import InvalidCredentialsError
        with pytest.raises(InvalidCredentialsError):
            await account.login('example@example.invalid', 'synthetic-password')
        user.verify_session.assert_not_called()
        assert not account._pushed_code_pending
    finally:
        await account.close()


@pytest.mark.parametrize('status,expected_2fa', [
    ({'ec': 0, 'au': 'trustedDeviceSecondaryAuth'}, True),
    ({'ec': 0, 'au': 'secondaryAuth'}, True),
    ({'ec': 0}, False),
])
async def test_legacy_authentication_states_remain_distinct(monkeypatch, tmp_path, status, expected_2fa):
    account, states, _ = await authenticate(monkeypatch, tmp_path, status)
    try:
        result = await account._gsa_authenticate('example@example.invalid', 'synthetic-password')
        assert result == (states.REQUIRE_2FA if expected_2fa else states.AUTHENTICATED)
        assert not account._pushed_code_pending
    finally:
        await account.close()


async def test_verification_keeps_gsa_label_and_requires_code_submission(tmp_path):
    flow = FindMySetup.create(tmp_path / 'unused.bin', onboarding=False)
    account = flow.account
    try:
        account._login_state_data = {'adsid': 'synthetic-id', 'idms_token': 'synthetic-token'}
        account.get_anisette_headers = AsyncMock(return_value={'X-Mme-Client-Info': 'legacy-label'})
        account._http.request = AsyncMock(return_value=SimpleNamespace(status_code=200, ok=True, text=lambda: ''))
        await account._sms_2fa_request('GET', account._ENDPOINT_2FA_TD_SUBMIT,
                                       headers={'security-code': 'synthetic-code'})
        call = account._http.request.call_args
        assert call.kwargs['headers']['X-Mme-Client-Info'] == account.gsa_client_info
        assert call.kwargs['headers']['security-code'] == 'synthetic-code'
        assert account._login_state_data == {'adsid': 'synthetic-id', 'idms_token': 'synthetic-token'}
    finally:
        await flow.close()


@pytest.mark.parametrize('state_name,phase', [('AUTHENTICATED', 'delegate')])
async def test_post_code_failures_keep_stage_and_state_without_code(tmp_path, state_name, phase):
    flow = FindMySetup.create(tmp_path / 'unused.bin')
    account = flow.account
    try:
        states = flow.states
        account._set_login_state(states.REQUIRE_2FA, {'adsid': 'synthetic-id', 'idms_token': 'synthetic-token'})
        account._sms_2fa_request = AsyncMock()
        account._gsa_authenticate = AsyncMock(return_value=getattr(states, state_name))
        account._login_mobileme = AsyncMock(side_effect=RuntimeError('synthetic-private-response'))
        with pytest.raises(RuntimeError):
            await account.td_2fa_submit('synthetic-private-code')
        assert account._verification_stage == phase
        assert account._verification_login_state == state_name
        assert not hasattr(account, '_verification_code')
        if state_name == 'REQUIRE_2FA':
            account._login_mobileme.assert_not_awaited()
    finally:
        await flow.close()


@pytest.mark.parametrize('method', ['td', 'sms'])
async def test_additional_verification_returns_control_without_delegate_or_code_delivery(tmp_path, method):
    flow = FindMySetup.create(tmp_path / 'unused.bin')
    account = flow.account
    states = flow.states
    account._set_login_state(states.REQUIRE_2FA, {'adsid': 'synthetic', 'idms_token': 'synthetic'})
    account._sms_2fa_request = AsyncMock()
    account._gsa_authenticate = AsyncMock(return_value=states.REQUIRE_2FA)
    account._login_mobileme = AsyncMock()
    try:
        result = await (account.td_2fa_submit('synthetic-code') if method == 'td'
                        else account.sms_2fa_submit(1, 'synthetic-code'))
        assert result == states.REQUIRE_2FA
        assert account._sms_2fa_request.await_count == 1
        account._gsa_authenticate.assert_awaited_once()
        account._login_mobileme.assert_not_awaited()
        assert not hasattr(account, '_verification_code')
    finally:
        await flow.close()


async def test_homecircle_uses_new_challenge_methods_without_auto_submitting(tmp_path):
    flow = FindMySetup.create(tmp_path / 'unused.bin')
    account = flow.account
    method = SimpleNamespace(request=AsyncMock(), submit=AsyncMock(return_value=flow.states.REQUIRE_2FA))
    new_method = SimpleNamespace(request=AsyncMock(), submit=AsyncMock())
    flow.factor = method
    account.get_2fa_methods = AsyncMock(return_value=[new_method])
    flow.zone_checker = AsyncMock()
    flow.client_factory = AsyncMock()
    try:
        assert await flow.verify_code('synthetic-code') == 'factor'
        assert flow.additional_verification
        assert flow.factor is None
        assert flow.methods == [new_method]
        new_method.request.assert_not_awaited()
        new_method.submit.assert_not_awaited()
        flow.zone_checker.assert_not_awaited()
        flow.client_factory.assert_not_awaited()
    finally:
        await flow.close()


@pytest.mark.parametrize('failure', ['empty', 'error'])
async def test_new_challenge_never_keeps_old_factor_when_methods_unavailable(tmp_path, failure):
    from custom_components.homecircle.findmy_setup import FindMySetupError
    flow = FindMySetup.create(tmp_path / 'unused.bin')
    flow.factor = SimpleNamespace(submit=AsyncMock(return_value=flow.states.REQUIRE_2FA))
    flow.account.get_2fa_methods = AsyncMock(return_value=[])
    if failure == 'error':
        flow.account.get_2fa_methods.side_effect = RuntimeError('synthetic-private')
    try:
        with pytest.raises(FindMySetupError):
            await flow.verify_code('synthetic-code')
        assert flow.factor is None
        assert flow.additional_verification
    finally:
        await flow.close()


async def test_additional_challenges_are_bounded_and_never_retried_automatically(tmp_path):
    from custom_components.homecircle.findmy_setup import FindMySetupError
    flow = FindMySetup.create(tmp_path / 'unused.bin')
    method = SimpleNamespace(request=AsyncMock(), submit=AsyncMock(return_value=flow.states.REQUIRE_2FA))
    flow.account.get_2fa_methods = AsyncMock(return_value=[method])
    try:
        for _ in range(2):
            flow.factor = method
            assert await flow.verify_code('synthetic-code') == 'factor'
        flow.factor = method
        with pytest.raises(FindMySetupError, match='findmy_verification_limit'):
            await flow.verify_code('synthetic-code')
        before = method.submit.await_count
        with pytest.raises(FindMySetupError, match='findmy_verification_limit'):
            await flow.verify_code('synthetic-code')
        assert method.submit.await_count == before == 3
        method.request.assert_not_awaited()
        assert flow.account.get_2fa_methods.await_count == 2
    finally:
        await flow.close()
