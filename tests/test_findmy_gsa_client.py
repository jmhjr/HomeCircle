"""Verify the candidate GSA label is isolated from saved device identity."""
from types import SimpleNamespace
from unittest.mock import AsyncMock
import plistlib

import pytest

from custom_components.homecircle.findmy_setup import FindMySetup, sdk


@pytest.mark.parametrize('restored', [False, True])
async def test_android_gsa_label_preserves_cpd_and_saved_identity(tmp_path, restored):
    account_type, provider_type, _, _ = sdk()
    original = account_type(provider_type(libs_path=tmp_path / 'unused.bin'))
    state = original.to_json() if restored else None
    await original.close()
    flow = FindMySetup.create(tmp_path / 'unused.bin', session=state, onboarding=False)
    account = flow.account
    before = account.to_json()['ids'].copy()
    cpd = {'X-Mme-Device-Id': before['devid'], 'X-Apple-I-MD-LU': 'synthetic-user-id'}
    account._anisette.get_cpd = AsyncMock(return_value=cpd)
    account._http.post = AsyncMock(return_value=SimpleNamespace(
        status_code=200, ok=True, plist=lambda: {'Response': {'Status': {'ec': -20101}}}
    ))
    response = await account._gsa_request({'o': 'init', 'u': 'example@example.invalid'})
    assert response['Status']['ec'] == -20101
    call = account._http.post.call_args
    assert call.kwargs['headers']['X-MMe-Client-Info'] == (
        '<Pixel 8><Android; 14; UQ1A.240205.004>'
        '<com.apple.AuthKit/1 (com.apple.android.music/4.9.6)>'
    )
    assert plistlib.loads(call.kwargs['data'])['Request']['cpd'] == cpd
    assert account.to_json()['ids'] == before
    assert account._anisette.client_akd != account.gsa_client_info
    await flow.close()


async def test_delegate_uses_authenticated_client_label_without_changing_ids(tmp_path):
    flow = FindMySetup.create(tmp_path / 'unused.bin', onboarding=False)
    account = flow.account
    try:
        before = account.to_json()['ids'].copy()
        account._username = 'example@example.invalid'
        account._set_login_state(flow.states.AUTHENTICATED, {'adsid': 'synthetic-id', 'idms_pet': 'synthetic-pet'})
        account.get_anisette_headers = AsyncMock(return_value={'X-Mme-Device-Id': before['devid']})
        account._http.post = AsyncMock(return_value=SimpleNamespace(status_code=200, plist=lambda: {
            'status': 0, 'dsid': 'synthetic-dsid',
            'delegates': {'com.apple.mobileme': {'status': 0, 'service-data': {'tokens': {}}}},
        }))
        assert await account._login_mobileme() == flow.states.LOGGED_IN
        call = account._http.post.call_args
        assert call.kwargs['headers']['X-Mme-Client-Info'] == account.gsa_client_info
        assert call.kwargs['auth'] == ('example@example.invalid', 'synthetic-pet')
        assert plistlib.loads(call.kwargs['data'])['password'] == 'synthetic-pet'
        assert account.to_json()['ids'] == before
        assert account._delegate_diagnostics['pet_present'] is True
        assert account._delegate_diagnostics['http'] == 200
    finally:
        await flow.close()


async def test_missing_pet_stops_before_sending_empty_credential(tmp_path):
    from custom_components.homecircle._vendor_findmy.errors import UnhandledProtocolError
    flow = FindMySetup.create(tmp_path / 'unused.bin', onboarding=False)
    account = flow.account
    try:
        account._set_login_state(flow.states.AUTHENTICATED, {'adsid': 'synthetic-id', 'idms_pet': ''})
        account._http.post = AsyncMock()
        with pytest.raises(UnhandledProtocolError, match='password-equivalent'):
            await account._login_mobileme()
        account._http.post.assert_not_awaited()
        assert account._delegate_diagnostics == {'pet_present': False}
    finally:
        await flow.close()
