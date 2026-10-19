"""Exercise code-validation credentials without another authentication exchange."""
import base64
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from multidict import CIMultiDict

from custom_components.homecircle.findmy_setup import sdk
from custom_components.homecircle._vendor_findmy.util.http import HttpResponse, HttpSession


def header(value):
    return base64.b64encode(value.encode()).decode()


@pytest.mark.parametrize('method', ['td', 'sms'])
@pytest.mark.parametrize('kind', ['complete', 'absent', 'malformed', 'conflict', 'rejected', 'heartbeat_only', 'prior_heartbeat', 'opaque_identifier', 'principal_conflict', 'hb_conflict'])
async def test_verification_headers(method, kind, tmp_path):
    account_type, provider_type, states, _ = sdk()
    account = account_type(provider_type(libs_path=tmp_path / 'unused.bin'))
    account._set_login_state(states.REQUIRE_2FA, {'adsid': 'example-id', 'idms_token': 'example-idms'})
    account._account_info = {'account_name': 'example@example.invalid'}
    headers = CIMultiDict()
    if kind == 'prior_heartbeat':
        account._login_state_data['idms_hb'] = 'example-hb'
    if kind in ('complete', 'conflict', 'rejected', 'prior_heartbeat'):
        headers.add('X-Apple-PE-Token', header('example-id:example-pet'))
        headers.add('X-Apple-PE-Token', header('example-id:example-pet'))
    if kind == 'opaque_identifier':
        headers.add('X-Apple-PE-Token', header('other-id:example-pet'))
    if kind == 'principal_conflict':
        headers.add('X-Apple-PE-Token', header('example-id:example-pet'))
        headers.add('X-Apple-PE-Token', header('other-id:example-pet'))
    if kind == 'hb_conflict':
        headers.add('X-Apple-HB-Token', header('com.apple.gs.idms.hb:example-hb'))
        headers.add('X-Apple-HB-Token', header('com.apple.gs.idms.hb:different-hb'))
    if kind == 'conflict':
        headers.add('X-Apple-PE-Token', header('example-id:different-pet'))
    if kind == 'malformed':
        headers.add('X-Apple-PE-Token', 'invalid-base64!')
    if kind in ('complete', 'heartbeat_only'):
        headers.add('X-Apple-HB-Token', header('unrelated:wrong-heartbeat'))
        headers.add('x-apple-hb-token', header('com.apple.gs.idms.hb:example-hb'))
    account._recovery_diagnostics.update(verification_token_source='stale', verification_pet_header_usable=True)
    account._http.request = AsyncMock(return_value=HttpResponse(401 if kind == 'rejected' else 200, b'', headers))
    account.get_anisette_headers = AsyncMock(return_value={})

    async def authenticate():
        return account._set_login_state(states.AUTHENTICATED, {'adsid': 'example-id', 'idms_pet': 'fallback-pet'})

    account._gsa_authenticate = AsyncMock(side_effect=authenticate)
    async def delegate():
        assert account.login_state == states.AUTHENTICATED
        assert account._login_state_data['idms_pet'] == ('example-pet' if kind in ('complete', 'prior_heartbeat', 'opaque_identifier') else 'fallback-pet')
        if kind in ('complete', 'heartbeat_only', 'prior_heartbeat'):
            assert account._login_state_data['idms_hb'] == 'example-hb'
        if kind == 'hb_conflict':
            assert not account._login_state_data.get('idms_hb')
        return states.LOGGED_IN
    account._login_mobileme = AsyncMock(side_effect=delegate)
    try:
        submit = account.td_2fa_submit('000000') if method == 'td' else account.sms_2fa_submit(1, '000000')
        if kind == 'rejected':
            with pytest.raises(Exception):
                await submit
            account._gsa_authenticate.assert_not_awaited()
            account._login_mobileme.assert_not_awaited()
            assert account.login_state == states.REQUIRE_2FA
            assert 'verification_token_source' not in account._recovery_diagnostics
            assert 'verification_pet_header_usable' not in account._recovery_diagnostics
        else:
            assert await submit == states.LOGGED_IN
            if kind in ('complete', 'prior_heartbeat', 'opaque_identifier'):
                account._gsa_authenticate.assert_not_awaited()
                assert account._recovery_diagnostics['verification_token_source'] == 'response_headers'
            else:
                account._gsa_authenticate.assert_awaited_once()
                assert account._recovery_diagnostics['verification_token_source'] == 'srp'
            account._login_mobileme.assert_awaited_once()
            expected = {
                'complete': 'usable', 'prior_heartbeat': 'usable', 'absent': 'absent',
                'heartbeat_only': 'absent', 'hb_conflict': 'absent', 'malformed': 'malformed',
                'conflict': 'conflicting', 'principal_conflict': 'conflicting',
                'opaque_identifier': 'usable',
            }
            assert account._recovery_diagnostics['verification_pet_header_result'] == expected[kind]
        assert 'example-pet' not in str(account._recovery_diagnostics)
        assert 'example-hb' not in str(account._recovery_diagnostics)
        account._http.request.assert_awaited_once()
    finally:
        await account.close()


async def test_http_session_preserves_duplicate_headers():
    headers = CIMultiDict([('X-Apple-HB-Token', 'first'), ('X-Apple-HB-Token', 'second')])
    response = SimpleNamespace(status=200, headers=headers, content=SimpleNamespace(read=AsyncMock(return_value=b'')))
    class Context:
        async def __aenter__(self):
            return response
        async def __aexit__(self, *_):
            pass
    session = HttpSession()
    session._get_session = AsyncMock(return_value=SimpleNamespace(request=AsyncMock(return_value=Context())))
    try:
        result = await session.request('GET', 'https://example.invalid')
        assert result.headers == dict(headers)
        assert list(result.header_values) == list(headers.items())
    finally:
        await session.close()


async def test_identifier_comparisons_never_expose_values(tmp_path):
    account_type, provider_type, states, _ = sdk()
    account = account_type(provider_type(libs_path=tmp_path / 'unused.bin'))
    account._set_login_state(states.REQUIRE_2FA, {'adsid': 'alternate-id', 'idms_token': 'example-idms'})
    account._account_info = {'account_name': 'example@example.invalid'}
    try:
        headers = CIMultiDict([('X-Apple-PE-Token', header('other-id:example-pet')), ('X-Apple-DSID', 'other-id')])
        account._accept_verification_tokens(HttpResponse(200, b'', headers))
        assert account.login_state == states.AUTHENTICATED
        assert account._login_state_data['adsid'] == 'alternate-id'
        d = account._recovery_diagnostics
        assert d['verification_pet_header_result'] == 'usable'
        assert d['verification_pet_matches_adsid'] is False
        assert d['verification_pet_matches_response_dsid'] is True
        assert d['verification_pet_matches_canonical'] is False
        assert 'other-id' not in str(d)
        assert 'example-pet' not in str(d)
        account._reset_verification_token_diagnostics()
        assert not d
    finally:
        await account.close()


@pytest.mark.parametrize('status,state_name', [(401, 'REQUIRE_2FA'), (200, 'LOGGED_OUT')])
async def test_header_tokens_cannot_promote_rejected_or_unauthenticated_state(status, state_name, tmp_path):
    account_type, provider_type, states, _ = sdk()
    account = account_type(provider_type(libs_path=tmp_path / 'unused.bin'))
    state = getattr(states, state_name)
    account._set_login_state(state, {'adsid': 'example-id', 'idms_token': 'example-idms'})
    try:
        headers = CIMultiDict([('X-Apple-PE-Token', header('opaque:example-pet'))])
        account._accept_verification_tokens(HttpResponse(status, b'', headers))
        assert account.login_state == state
        assert 'idms_pet' not in account._login_state_data
    finally:
        await account.close()
