"""Fresh policy compositional parity and legacy isolation; no native or network calls."""
from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
import plistlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.homecircle._vendor_findmy.errors import (
    AppleServiceUnavailableError,
    InvalidStateError,
    MobileMeDelegateError,
    UnauthorizedError,
    UnhandledProtocolError,
)
from custom_components.homecircle._vendor_findmy.reports.account import AsyncAppleAccount
from custom_components.homecircle._vendor_findmy.reports.anisette import (
    BaseAnisetteProvider,
    LocalAnisetteProvider,
)
from custom_components.homecircle._vendor_findmy.reports.endpoint_policy import (
    EndpointPolicy,
    POLICY_ID,
    WINDOWS_ONBOARDING_V1,
)
from custom_components.homecircle._vendor_findmy.reports.state import LoginState
from custom_components.homecircle._vendor_findmy.util.http import HttpResponse

REFERENCE = Path(__file__).parent / 'fixtures' / 'findmy_0102_gsa_reference.py'


class StaticProvider(BaseAnisetteProvider):
    """Inherited real CPD/header composers, with public synthetic properties only."""

    timestamp = '2026-10-16T12:34:56+00:00Z'
    timezone = 'UTC'
    locale = 'en_US'
    otp = 'Zml4dHVyZS1vdHA='
    machine = 'Zml4dHVyZS1tYWNoaW5l'

    async def close(self):
        pass

    def to_json(self):
        return {'type': 'fixture'}

    @classmethod
    def from_json(cls, _value):
        return cls()


def make_account(policy=WINDOWS_ONBOARDING_V1):
    return AsyncAppleAccount(StaticProvider(), endpoint_policy=policy)


@pytest.mark.parametrize('parameters', [
    {'u': 'fixture@example.invalid', 'A2k': b'\x03' * 256, 'ps': ['s2k', 's2k_fo'], 'o': 'init'},
    {'u': 'fixture@example.invalid', 'c': 'fixture-challenge', 'M1': b'\x04' * 32, 'o': 'complete'},
])
async def test_new_policy_matches_published_gsa_bytes_with_only_windows_declaration(parameters):
    # These are actual published composer bodies, extracted from the verified wheel;
    # the fixture digest makes accidental edits explicit rather than silently mirroring
    # a runtime implementation change. See fixtures/findmy_0102_gsa_reference.provenance.md.
    assert hashlib.sha256(REFERENCE.read_bytes()).hexdigest() == '059fb9d6f6b9dfcc813961db6435e3bf71b21e782bdf47dacf2be8def94b4705'
    spec = importlib.util.spec_from_file_location('published_gsa_reference', REFERENCE)
    reference = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reference)
    published = reference.PublishedProvider()
    account = make_account()
    for name in ('timestamp', 'timezone', 'locale', 'otp', 'machine', 'router'):
        setattr(published, name, getattr(account._anisette, name))
    published.client = WINDOWS_ONBOARDING_V1.profile('gsa').client_info
    response = HttpResponse(200, plistlib.dumps({'Response': {'Status': {'ec': 0}}}))
    reference_http = SimpleNamespace(post=AsyncMock(return_value=response))
    account._http.post = AsyncMock(return_value=response)
    # Fixed account identities, independent of any native engine identity.
    account._uid = '63858f3f-c32d-42f1-8be7-11d289699147'
    account._devid = '0d78e843-d640-4490-b032-819c066fb121'
    ref_account = reference.PublishedAccount()
    ref_account._uid, ref_account._devid = account._uid, account._devid
    ref_account._anisette, ref_account._http = published, reference_http
    ref_account._ENDPOINT_GSA = account._ENDPOINT_GSA
    try:
        await reference.PublishedAccount._gsa_request(ref_account, parameters)
        await account._gsa_request(parameters)
        actual = account._http.post.call_args
        expected = reference_http.post.call_args
        assert actual.args == expected.args
        assert actual.kwargs['data'] == expected.kwargs['data']
        assert actual.kwargs['headers'] == expected.kwargs['headers']
        assert actual.kwargs['auto_retry'] is False
        assert actual.kwargs['allow_redirects'] is False
        assert plistlib.loads(actual.kwargs['data'])['Request']['cpd']['X-Apple-I-SRL-NO'] == '0'
    finally:
        await account.close()


async def test_policy_roundtrip_and_legacy_state_are_distinct(tmp_path):
    legacy = AsyncAppleAccount(LocalAnisetteProvider(libs_path=tmp_path / 'unused.bin'))
    marked = AsyncAppleAccount(LocalAnisetteProvider(libs_path=tmp_path / 'unused.bin'), endpoint_policy=WINDOWS_ONBOARDING_V1)
    restored = None
    try:
        old = legacy.to_json()
        assert 'endpoint_policy' not in old
        state = marked.to_json()
        assert state['endpoint_policy'] == POLICY_ID
        restored = AsyncAppleAccount.from_json(state, anisette_libs_path=tmp_path / 'unused.bin')
        assert restored.endpoint_policy is WINDOWS_ONBOARDING_V1
        assert restored.to_json() == state
        assert legacy.to_json() == old and legacy.endpoint_policy is None
        assert type(marked._http).__name__ == 'BoundedHttpSession'
        assert type(legacy._http).__name__ == 'HttpSession'
        bad = deepcopy(old)
        bad['endpoint_policy'] = 'not-a-supported-policy'
        with pytest.raises(ValueError, match='Unknown saved endpoint policy'):
            AsyncAppleAccount.from_json(bad, anisette_libs_path=tmp_path / 'unused.bin')
        with pytest.raises(ValueError, match='cannot be replaced'):
            AsyncAppleAccount(StaticProvider(), state_info=old, endpoint_policy=WINDOWS_ONBOARDING_V1)
    finally:
        await legacy.close()
        await marked.close()
        if restored:
            await restored.close()


def test_policy_has_no_service_fallback_and_removes_duplicate_header_names():
    policy = WINDOWS_ONBOARDING_V1
    assert policy.name == POLICY_ID
    assert 'Windows' in policy.profile('gsa').client_info
    assert 'accountsd' in policy.profile('delegate').client_info
    assert 'Windows' in policy.profile('delegate').client_info
    assert 'MacBook' in policy.profile('settings').client_info
    assert 'accountsd' in policy.profile('settings').client_info
    assert 'Windows' in policy.profile('escrow').client_info and 'sbd' in policy.profile('escrow').client_info
    assert 'MacBook' in policy.profile('cloudkit').client_info and 'CloudKitDaemon/1970' in policy.profile('cloudkit').client_info
    with pytest.raises(ValueError, match='Unknown endpoint stage'):
        policy.profile('other')
    with pytest.raises(ValueError, match='Unknown endpoint policy'):
        EndpointPolicy('other').profile('gsa')
    original = {'x-mme-client-info': 'old', 'X-MMe-Client-Info': 'other', 'User-Agent': 'old', 'USER-AGENT': 'other', 'unchanged': 'fixture'}
    result = policy.profile('gsa').apply(original)
    assert original['User-Agent'] == 'old'
    assert len([x for x in result if x.lower() == 'x-mme-client-info']) == 1
    assert len([x for x in result if x.lower() == 'user-agent']) == 1
    assert result['unchanged'] == 'fixture'


@pytest.mark.parametrize('status', [200, 401, 503])
async def test_delegate_uses_distinct_profile_and_checks_http_before_tokens(status):
    account = make_account()
    account._username = 'fixture@example.invalid'
    account.gsa_client_info = 'gsa-must-not-leak'
    account._set_login_state(LoginState.AUTHENTICATED, {'adsid': 'fixture-id', 'idms_pet': 'fixture-pet'})
    good = {'status': 0, 'dsid': '12345', 'delegates': {'com.apple.mobileme': {'status': 0, 'service-data': {'tokens': {'searchPartyToken': 'fixture-report'}}}}}
    account._http.post = AsyncMock(return_value=HttpResponse(status, plistlib.dumps(good)))
    try:
        if status != 200:
            with pytest.raises((MobileMeDelegateError, AppleServiceUnavailableError)):
                await account._login_mobileme()
            assert account.login_state == LoginState.AUTHENTICATED
        else:
            assert await account._login_mobileme() == LoginState.LOGGED_IN
            assert account.service_tokens['searchPartyToken'] == 'fixture-report'
        account._http.post.assert_awaited_once()
        sent = account._http.post.call_args.kwargs
        assert sent['headers']['X-Mme-Client-Info'] == WINDOWS_ONBOARDING_V1.profile('delegate').client_info
        assert 'accountsd' in sent['headers']['X-Mme-Client-Info']
        assert sent['auto_retry'] is False and sent['allow_redirects'] is False
    finally:
        await account.close()


@pytest.mark.parametrize('case', ['accepted', 'service_refusal', 'wrong_dsid', 'http_refusal'])
async def test_settings_policy_single_request_keeps_import_guards(case):
    account = make_account()
    account._set_login_state(LoginState.LOGGED_IN, {'dsid': '12345', 'mobileme_data': {'tokens': {'mmeAuthToken': 'fixture-mme', 'searchPartyToken': 'held-report'}}})
    response = {'status': 1 if case == 'service_refusal' else 0, 'dsid': '67890' if case == 'wrong_dsid' else '12345', 'tokens': {'searchPartyToken': 'new-report', 'cloudKitToken': 'fixture-cloudkit'}}
    account._http.post = AsyncMock(return_value=HttpResponse(401 if case == 'http_refusal' else 200, plistlib.dumps(response)))
    try:
        if case == 'accepted':
            await account._fetch_account_settings({'user-agent': 'wrong-stage', 'x-mme-client-info': 'wrong-stage'})
            assert account.service_tokens['cloudKitToken'] == 'fixture-cloudkit'
        else:
            with pytest.raises((UnauthorizedError, UnhandledProtocolError)):
                await account._fetch_account_settings({'user-agent': 'wrong-stage', 'x-mme-client-info': 'wrong-stage'})
            assert 'cloudKitToken' not in account.service_tokens
        assert account.service_tokens['searchPartyToken'] == 'held-report'
        await account._fetch_account_settings({})
        account._http.post.assert_awaited_once()
        sent = account._http.post.call_args.kwargs
        assert sent['headers']['x-mme-client-info'] == WINDOWS_ONBOARDING_V1.profile('settings').client_info
        assert sent['headers']['User-Agent'].startswith('com.apple.iCloudHelper/282 ')
        assert sent['headers']['accept'] == 'application/x-plist'
        assert sent['auto_retry'] is False and sent['allow_redirects'] is False
    finally:
        await account.close()


@pytest.mark.parametrize('factor', ['td', 'sms'])
async def test_verification_profile_and_one_bounded_continuation(factor):
    account = make_account()
    account.gsa_client_info = 'untrusted-old-override'
    account._set_login_state(LoginState.REQUIRE_2FA, {'adsid': 'fixture-id', 'idms_token': 'fixture-idms'})
    account._http.request = AsyncMock(return_value=HttpResponse(200, b''))
    account._gsa_authenticate = AsyncMock(return_value=LoginState.REQUIRE_2FA)
    account._login_mobileme = AsyncMock()
    try:
        if factor == 'td':
            state = await account.td_2fa_submit('123456')
        else:
            state = await account.sms_2fa_submit(1, '123456')
        assert state == LoginState.REQUIRE_2FA
        assert account._verification_continuations == 1
        account._gsa_authenticate.assert_awaited_once()
        account._login_mobileme.assert_not_awaited()
        sent = account._http.request.call_args.kwargs
        assert sent['headers']['X-Mme-Client-Info'] == WINDOWS_ONBOARDING_V1.profile('verification').client_info
        assert sent['headers']['User-Agent'] == WINDOWS_ONBOARDING_V1.profile('gsa').user_agent
        assert sent['headers']['X-Apple-App-Info'] == 'com.apple.gs.xcode.auth'
        assert 'X-Apple-Identity-Token' in sent['headers']
        assert sent['auto_retry'] is False and sent['allow_redirects'] is False
        with pytest.raises(InvalidStateError, match='already attempted'):
            await account._verification_srp_continuation()
        account._gsa_authenticate.assert_awaited_once()
        with pytest.raises(InvalidStateError, match='Unknown verification endpoint'):
            await account._sms_2fa_request('POST', 'https://example.invalid')
        account._http.request.assert_awaited_once()
    finally:
        await account.close()


@pytest.mark.parametrize('marker', [None, False, 1, {}, 'unknown'])
async def test_present_invalid_policy_marker_cannot_downgrade_to_legacy(tmp_path, marker):
    seed = AsyncAppleAccount(LocalAnisetteProvider(libs_path=tmp_path / 'unused.bin'))
    try:
        state = seed.to_json()
        state['endpoint_policy'] = marker
        with pytest.raises(ValueError, match='Unknown saved endpoint policy'):
            AsyncAppleAccount.from_json(state, anisette_libs_path=tmp_path / 'unused.bin')
    finally:
        await seed.close()


async def test_expired_pet_and_report_refusal_never_start_hidden_authentication():
    account = make_account()
    account.reuse_recent_pet = True
    account._username, account._password = 'fixture@example.invalid', 'private-fixture-password'
    account._set_login_state(LoginState.LOGGED_IN, {'dsid': '12345', 'mobileme_data': {'tokens': {'searchPartyToken': 'fixture-report'}}})
    account._gsa_authenticate = AsyncMock()
    account._http.post = AsyncMock(return_value=HttpResponse(401, b''))
    try:
        with pytest.raises(UnauthorizedError, match='expired'):
            await account.request_pet()
        with pytest.raises(UnauthorizedError, match='sign in again'):
            await account.fetch_raw_reports([])
        account._http.post.assert_awaited_once()
        account._gsa_authenticate.assert_not_awaited()
        assert account.login_state == LoginState.LOGGED_IN
    finally:
        await account.close()


@pytest.mark.parametrize('case', ['init_refusal', 'complete_refusal', 'invalid_server_proof', 'accepted_pushed_2fa'])
async def test_fresh_login_no_retry_and_server_proof_before_state(monkeypatch, case):
    from custom_components.homecircle._vendor_findmy.errors import InvalidCredentialsError
    from custom_components.homecircle._vendor_findmy.reports import account as module

    account = make_account()
    user = SimpleNamespace(
        start_authentication=lambda: (None, b'fixture-public'),
        process_challenge=lambda *_: b'fixture-proof',
        verify_session=lambda *_: None,
        authenticated=lambda: case != 'invalid_server_proof',
        get_session_key=lambda: b'fixture-session',
    )
    monkeypatch.setattr(module.srp, 'User', lambda *_args, **_kwargs: user)
    monkeypatch.setattr(module.util.crypto, 'encrypt_password', lambda *_: b'fixture-password-key')
    decrypted = []
    monkeypatch.setattr(module.util.crypto, 'decrypt_spd_aes_cbc', lambda *_: decrypted.append(True) or b'fixture-spd')
    monkeypatch.setattr(module.util.parsers, 'decode_plist', lambda *_: {'adsid': 'fixture-id', 'GsIdmsToken': 'fixture-token'})
    replies = [
        {'Status': {'ec': -80045, 'em': 'private-response-value'}} if case == 'init_refusal' else {'Status': {'ec': 0}, 'sp': 's2k', 's': b'salt', 'i': 1, 'B': b'fixture-public', 'c': 'fixture-challenge'},
        {'Status': {'ec': -20101, 'em': 'private-response-value'}} if case == 'complete_refusal' else {'Status': {'ec': 0, 'hsc': 409}, 'M2': b'fixture-server-proof', 'spd': b'fixture-encrypted'},
    ]
    account._gsa_request = AsyncMock(side_effect=replies)
    account._login_mobileme = AsyncMock()
    try:
        if case in ('init_refusal', 'complete_refusal'):
            with pytest.raises(InvalidCredentialsError) as caught:
                await account.login('fixture@example.invalid', 'private-fixture-password')
            assert 'private-response-value' not in str(caught.value)
            assert caught.value.phase == ('init' if case == 'init_refusal' else 'complete')
        elif case == 'invalid_server_proof':
            with pytest.raises(UnhandledProtocolError, match='verify session'):
                await account.login('fixture@example.invalid', 'private-fixture-password')
        else:
            assert await account.login('fixture@example.invalid', 'private-fixture-password') == LoginState.REQUIRE_2FA
            assert account._pushed_code_pending is True
        assert account._gsa_request.await_count == (1 if case == 'init_refusal' else 2)
        assert decrypted == ([True] if case == 'accepted_pushed_2fa' else [])
        account._login_mobileme.assert_not_awaited()
    finally:
        await account.close()


async def test_fresh_policy_constructor_keeps_sdk_independent_lowercase_ids(monkeypatch):
    import uuid
    from custom_components.homecircle._vendor_findmy.reports import account as module

    uid = uuid.UUID('63858f3f-c32d-42f1-8be7-11d289699147')
    devid = uuid.UUID('0d78e843-d640-4490-b032-819c066fb121')
    values = iter((uid, devid))
    monkeypatch.setattr(module.uuid, 'uuid4', lambda: next(values))
    account = make_account()
    try:
        assert account.local_user_uuid == str(uid)
        assert account.device_uuid == str(devid)
        headers = await account.get_anisette_headers()
        assert headers['X-Mme-Device-Id'] == str(devid).upper()
        import base64
        assert base64.b64decode(headers['X-Apple-I-MD-LU']).decode() == str(uid)
        assert headers['X-Apple-I-SRL-NO'] == '0'
        assert account.serial == '0FINDMYPY001'  # The provider itself was not mutated.
    finally:
        await account.close()


@pytest.mark.parametrize('field,value', [
    ('s', b''), ('s', b'x' * 1025), ('s', 'salt'),
    ('B', b''), ('B', b'\0' * 256), ('B', b'x' * 257),
    ('i', True), ('i', 0), ('i', 10_000_001), ('i', 1.0),
    ('c', ''), ('c', 'x' * 4097), ('c', b'challenge'), ('sp', 'unsupported-private-value'),
])
async def test_bounded_challenge_stops_before_password_work(monkeypatch, field, value):
    from unittest.mock import Mock
    from custom_components.homecircle._vendor_findmy.reports import account as module

    account = make_account()
    process = Mock(side_effect=AssertionError('Unexpected password proof'))
    user = SimpleNamespace(start_authentication=lambda: (None, b'fixture-public'), process_challenge=process)
    monkeypatch.setattr(module.srp, 'User', lambda *_args, **_kwargs: user)
    encrypt = Mock(side_effect=AssertionError('Unexpected password derivation'))
    monkeypatch.setattr(module.util.crypto, 'encrypt_password', encrypt)
    challenge = {'Status': {'ec': 0}, 'sp': 's2k', 's': b'salt', 'i': 1, 'B': b'public', 'c': 'challenge'}
    challenge[field] = value
    account._gsa_request = AsyncMock(return_value=challenge)
    try:
        with pytest.raises(UnhandledProtocolError) as caught:
            await account._gsa_authenticate('fixture@example.invalid', 'private-fixture-password')
        assert 'unsupported-private-value' not in str(caught.value)
        assert account.login_state == LoginState.LOGGED_OUT
        account._gsa_request.assert_awaited_once()
        encrypt.assert_not_called()
        process.assert_not_called()
    finally:
        await account.close()


async def test_policy_password_derivation_runs_off_event_loop(monkeypatch):
    import threading
    from custom_components.homecircle._vendor_findmy.reports import account as module

    account = make_account()
    on_loop = threading.get_ident()
    workers = []
    def encrypt(*_args):
        workers.append(threading.get_ident())
        return b'fixture-password-key'
    user = SimpleNamespace(start_authentication=lambda: (None, b'public'), process_challenge=lambda *_: b'proof', verify_session=lambda *_: None, authenticated=lambda: False)
    monkeypatch.setattr(module.srp, 'User', lambda *_args, **_kwargs: user)
    monkeypatch.setattr(module.util.crypto, 'encrypt_password', encrypt)
    account._gsa_request = AsyncMock(side_effect=[
        {'Status': {'ec': 0}, 'sp': 's2k', 's': b'salt', 'i': 1, 'B': b'public', 'c': 'challenge'},
        {'Status': {'ec': 0}, 'M2': b'proof'},
    ])
    try:
        with pytest.raises(UnhandledProtocolError, match='verify session'):
            await account._gsa_authenticate('fixture@example.invalid', 'private-fixture-password')
        assert len(workers) == 1 and workers[0] != on_loop
    finally:
        await account.close()
