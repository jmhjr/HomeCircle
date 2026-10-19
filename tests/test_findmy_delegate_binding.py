"""Delegate credentials use the verified account identity and reject service failures."""
import plistlib
from unittest.mock import AsyncMock

import pytest

from custom_components.homecircle.findmy_setup import FindMySetup
from custom_components.homecircle._vendor_findmy.reports.state import LoginState
from custom_components.homecircle._vendor_findmy.util.http import HttpResponse
from custom_components.homecircle._vendor_findmy.errors import MobileMeDelegateError


@pytest.mark.parametrize('canonical', ['canonical@example.invalid', None])
@pytest.mark.parametrize('status', [0, 1])
async def test_canonical_delegate_identity_and_partial_failure(tmp_path, canonical, status):
    flow = FindMySetup.create(tmp_path / 'unused.bin')
    account = flow.account
    account._username = 'alias@example.invalid'
    account._account_info = {'account_name': canonical}
    account._set_login_state(LoginState.AUTHENTICATED, {'idms_pet': 'synthetic-pet', 'adsid': 'synthetic'})
    account.get_anisette_headers = AsyncMock(return_value={})
    payload = {'status': 0, 'dsid': '1234', 'delegates': {'com.apple.mobileme': {
        'status': status, 'service-data': {'tokens': {'mmeAuthToken': 'synthetic-mme',
          'cloudKitToken': 'synthetic-ck', 'searchPartyToken': 'synthetic-report'}}}}}
    account._http.post = AsyncMock(return_value=HttpResponse(200, plistlib.dumps(payload)))
    try:
        if status:
            with pytest.raises(MobileMeDelegateError):
                await account._login_mobileme()
            assert account.login_state == LoginState.AUTHENTICATED
        else:
            assert await account._login_mobileme() == LoginState.LOGGED_IN
            assert account._recovery_diagnostics['cloudkit_token_source'] == 'delegate'
            assert account._recovery_diagnostics['delegate_service_status'] == 0
        sent = account._http.post.await_args.kwargs
        username = canonical or 'alias@example.invalid'
        assert sent['auth'] == (username, 'synthetic-pet')
        assert plistlib.loads(sent['data'])['apple-id'] == username
        assert account._recovery_diagnostics['canonical_account_present'] is bool(canonical)
        assert account._recovery_diagnostics['canonical_matches_input'] is (False if canonical else None)
        assert 'example.invalid' not in str(account._recovery_diagnostics)
        assert 'synthetic-pet' not in str(account._recovery_diagnostics)
    finally:
        await flow.close()


async def test_delegate_actor_override_changes_only_service_header(tmp_path):
    from copy import deepcopy
    flow = FindMySetup.create(tmp_path / 'unused.bin', onboarding=False)
    account = flow.account
    account._username = 'synthetic@example.invalid'
    account._account_info = {'account_name': 'synthetic@example.invalid'}
    original_gsa = account.gsa_client_info
    original_identity = account.identity
    original_ids = account.to_json()['ids'].copy()
    account.get_anisette_headers = AsyncMock(return_value={'X-Apple-I-MD': 'synthetic-adi'})
    payload = {'status': 0, 'dsid': 'synthetic', 'delegates': {'com.apple.mobileme': {
        'status': 0, 'service-data': {'tokens': {'mmeAuthToken': 'synthetic-mme'}}}}}
    account._http.post = AsyncMock(return_value=HttpResponse(200, plistlib.dumps(payload)))
    calls = []
    try:
        for actor in (None, account._anisette.client_akd):
            account.delegate_client_info = actor
            account._set_login_state(LoginState.AUTHENTICATED, {
                'idms_pet': 'synthetic-pet', 'adsid': 'synthetic', 'idms_hb': 'synthetic-hb'})
            assert await account._login_mobileme() == LoginState.LOGGED_IN
            calls.append(deepcopy(account._http.post.await_args.kwargs))
            assert account.gsa_client_info == original_gsa
            assert account.identity == original_identity
            assert account.to_json()['ids'] == original_ids
            assert account._recovery_diagnostics['delegate_searchparty_token_present'] is False
            assert account._recovery_diagnostics['delegate_cloudkit_token_present'] is False
        assert calls[0]['headers'].pop('X-Mme-Client-Info') == original_gsa
        variant = calls[1]['headers'].pop('X-Mme-Client-Info')
        assert variant == account._anisette.client_akd
        assert 'Android' in variant and 'com.apple.akd' in variant
        assert 'Mac' not in variant and 'music' not in variant
        assert calls[0] == calls[1]
        assert account._http.post.await_count == 2
        assert 'delegate_client_info' not in account.to_json()
    finally:
        await flow.close()
