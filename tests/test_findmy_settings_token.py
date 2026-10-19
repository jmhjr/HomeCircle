"""The missing-token settings hop must not overwrite a working report session."""
import plistlib
from unittest.mock import AsyncMock

import pytest

from custom_components.homecircle.findmy_setup import FindMySetup
from custom_components.homecircle._vendor_findmy.reports.state import LoginState
from custom_components.homecircle._vendor_findmy.util.http import HttpResponse
from custom_components.homecircle._vendor_findmy.errors import UnauthorizedError, UnhandledProtocolError


@pytest.mark.parametrize('payload,status,error', [
    ({'tokens': {'cloudKitToken': 'synthetic-ck', 'mmeAuthToken': 'synthetic-settings-mme', 'searchPartyToken': 'unwanted'}}, 200, None),
    ({'tokens': {}}, 200, UnhandledProtocolError),
    ({'tokens': {'cloudKitToken': 123}}, 200, UnhandledProtocolError),
    ({}, 401, UnauthorizedError),
    ({}, 503, UnhandledProtocolError),
])
async def test_missing_token_hop_preserves_session(tmp_path, payload, status, error):
    flow = FindMySetup.create(tmp_path / 'unused.bin', onboarding=False)
    account = flow.account
    account.cloudkit_client_info = None
    account._set_login_state(LoginState.LOGGED_IN, {
        'dsid': 'synthetic-dsid', 'mobileme_data': {'tokens': {
            'mmeAuthToken': 'synthetic-mme', 'searchPartyToken': 'synthetic-reports'}}})
    account._http.post = AsyncMock(return_value=HttpResponse(status, plistlib.dumps(payload)))
    headers = {'x-mme-client-info': account.gsa_client_info}
    try:
        if error:
            with pytest.raises(error):
                await account.ensure_cloudkit_token(headers)
            assert 'cloudKitToken' not in account.service_tokens
        else:
            await account.ensure_cloudkit_token(headers)
            assert account.service_tokens['cloudKitToken'] == 'synthetic-ck'
            await account.ensure_cloudkit_token(headers)
        assert account._http.post.await_count == (2 if status == 200 and error else 1)
        account._http.post.assert_any_await(
            'https://setup.icloud.com/setup/get_account_settings',
            auth=('synthetic-dsid', 'synthetic-mme'), headers=headers, data=b'', auto_retry=False,
            allow_redirects=False)
        assert account.service_tokens['searchPartyToken'] == 'synthetic-reports'
        assert account.service_tokens['mmeAuthToken'] == 'synthetic-mme'
        if payload.get('tokens', {}).get('mmeAuthToken'):
            assert account._settings_cloudkit_pair == {'mmeAuthToken': 'synthetic-settings-mme', 'cloudKitToken': 'synthetic-ck'}
            assert 'synthetic-settings-mme' not in str(account.to_json())
        assert account._recovery_diagnostics['settings_http'] == status
        assert all('synthetic' not in str(value) for value in account._recovery_diagnostics.values())
    finally:
        await flow.close()
        assert account._settings_cloudkit_pair is None


@pytest.mark.parametrize('report_token,present', [
    (None, False), ('', False), (123, False), ('synthetic-private-report', True),
])
async def test_settings_can_fill_missing_report_token_without_logging_it(tmp_path, report_token, present):
    flow = FindMySetup.create(tmp_path / 'unused.bin', onboarding=False)
    account = flow.account
    account._set_login_state(LoginState.LOGGED_IN, {'dsid': 'synthetic', 'mobileme_data': {
        'tokens': {'mmeAuthToken': 'synthetic-mme'}}})
    tokens = {'cloudKitToken': 'synthetic-ck'}
    if report_token is not None:
        tokens['searchPartyToken'] = report_token
    account._http.post = AsyncMock(return_value=HttpResponse(200, plistlib.dumps({'tokens': tokens})))
    try:
        await account.ensure_cloudkit_token({})
        assert account._recovery_diagnostics['settings_searchparty_token_present'] is present
        if present:
            assert account.service_tokens['searchPartyToken'] == report_token
        else:
            assert 'searchPartyToken' not in account.service_tokens
        assert 'synthetic-private-report' not in str(account._recovery_diagnostics)
        account._http.post.assert_awaited_once()
    finally:
        await flow.close()


async def test_failed_settings_request_clears_stale_token_presence(tmp_path):
    flow = FindMySetup.create(tmp_path / 'unused.bin', onboarding=False)
    account = flow.account
    account._set_login_state(LoginState.LOGGED_IN, {'dsid': 'synthetic', 'mobileme_data': {
        'tokens': {'mmeAuthToken': 'synthetic-mme'}}})
    account._recovery_diagnostics['settings_searchparty_token_present'] = True
    account._http.post = AsyncMock(return_value=HttpResponse(401, b''))
    try:
        with pytest.raises(UnauthorizedError):
            await account.ensure_cloudkit_token({})
        assert 'settings_searchparty_token_present' not in account._recovery_diagnostics
    finally:
        await flow.close()


async def test_no_mme_token_does_not_send_request(tmp_path):
    flow = FindMySetup.create(tmp_path / 'unused.bin', onboarding=False)
    account = flow.account
    account._set_login_state(LoginState.LOGGED_IN, {'dsid': 'synthetic', 'mobileme_data': {'tokens': {}}})
    account._http.post = AsyncMock()
    try:
        with pytest.raises(UnauthorizedError):
            await account.ensure_cloudkit_token({})
        account._http.post.assert_not_awaited()
    finally:
        await flow.close()


async def test_native_uses_successful_ios_settings_profile_directly(tmp_path):
    flow = FindMySetup.create(tmp_path / 'unused.bin', onboarding=False)
    account = flow.account
    account._set_login_state(LoginState.LOGGED_IN, {'dsid': 'synthetic', 'mobileme_data': {
        'tokens': {'mmeAuthToken': 'synthetic-mme', 'searchPartyToken': 'synthetic-report'}}})
    account._http.post = AsyncMock(return_value=HttpResponse(200, plistlib.dumps({
        'tokens': {'cloudKitToken': 'synthetic-ck'}})))
    original_profile = account.gsa_client_info
    try:
        await account.ensure_cloudkit_token({'x-mme-client-info': original_profile})
        account._http.post.assert_awaited_once()
        request = account._http.post.await_args.kwargs
        assert request['headers']['x-mme-client-info'] == account.cloudkit_client_info
        assert 'iPhone' in request['headers']['x-mme-client-info']
        assert 'Mac' not in request['headers']['x-mme-client-info']
        assert request['auto_retry'] is False
        assert account.gsa_client_info == original_profile
        assert account.service_tokens['searchPartyToken'] == 'synthetic-report'
        assert account.service_tokens['cloudKitToken'] == 'synthetic-ck'
        assert account._recovery_diagnostics['settings_candidate'] == 'ios_settings'
    finally:
        await flow.close()


async def test_http_success_with_service_rejection_cannot_grant_access(tmp_path):
    flow = FindMySetup.create(tmp_path / 'unused.bin', onboarding=False)
    account = flow.account
    account._set_login_state(LoginState.LOGGED_IN, {'dsid': 'synthetic', 'mobileme_data': {
        'tokens': {'mmeAuthToken': 'synthetic-mme'}}})
    account._http.post = AsyncMock(return_value=HttpResponse(200, plistlib.dumps({
        'status': 1, 'tokens': {'cloudKitToken': 'synthetic-rejected'}})))
    try:
        with pytest.raises(UnhandledProtocolError):
            await account.ensure_cloudkit_token({})
        assert 'cloudKitToken' not in account.service_tokens
        account._http.post.assert_awaited_once()
    finally:
        await flow.close()


@pytest.mark.parametrize('body,accepted', [
    (b'', False), (b'[]', False), (b'{"cloudKitUserId": 123}', False),
    (b'{"cloudKitUserId": "synthetic-user", "cloudKitDatabaseUrl": "https://p01-ckdatabase.icloud.com"}', True),
])
async def test_native_container_uses_service_profile_and_validates_response(tmp_path, body, accepted):
    from custom_components.homecircle._vendor_findmy.cloudkit.client import AsyncCloudKitClient
    flow = FindMySetup.create(tmp_path / 'unused.bin', onboarding=False)
    account = flow.account
    account._set_login_state(LoginState.LOGGED_IN, {'dsid': 'synthetic', 'mobileme_data': {
        'tokens': {'mmeAuthToken': 'synthetic-mme', 'cloudKitToken': 'synthetic-ck'}}})
    account.get_anisette_headers = AsyncMock(return_value={})
    client = AsyncCloudKitClient(account)
    client._http.post = AsyncMock(return_value=HttpResponse(200, body))
    try:
        if accepted:
            assert (await client.open_container()).partition == '01'
        else:
            with pytest.raises(UnhandledProtocolError):
                await client.open_container()
        request = client._http.post.await_args.kwargs
        assert 'iPhone' in request['headers']['x-mme-client-info']
        assert 'CloudKitDaemon/1970' in request['headers']['x-mme-client-info']
        assert request['headers']['user-agent'] == 'CloudKit/1970 (19H384)'
        assert request['headers']['accept'] == 'application/json'
        assert 'Android' in account.gsa_client_info
        assert account._recovery_diagnostics['cloudkit_body_present'] == bool(body)
        assert all('synthetic' not in str(value) for value in account._recovery_diagnostics.values())
    finally:
        await client.close()
        await flow.close()


@pytest.mark.parametrize('value,expected', [
    ('https://p24-ckdatabase.icloud.com:443', '24'),
    ({'url': 'https://p24-ckdatabase.icloud.com:443'}, '24'),
    ({'url': 42}, None), (['unexpected'], None), (42, None),
])
def test_partition_descriptor_shapes_never_crash(value, expected):
    from custom_components.homecircle._vendor_findmy.cloudkit.client import CloudKitContainerInfo
    info = CloudKitContainerInfo('synthetic', value, None, None, None, {'cloudKitShareUrl': value})
    assert info.partition == expected


@pytest.mark.parametrize('age,use_cached', [(0, True), (239, True), (240, False), (-1, False)])
async def test_recent_login_pet_is_transient_and_age_bounded(tmp_path, monkeypatch, age, use_cached):
    from custom_components.homecircle._vendor_findmy.reports import account as module
    flow = FindMySetup.create(tmp_path / 'unused.bin', onboarding=False)
    account = flow.account
    account._set_login_state(LoginState.LOGGED_IN, {'dsid': 'synthetic', 'mobileme_data': {'tokens': {}}})
    account._recovery_pet = 'synthetic-transient-pet'
    account._recovery_pet_at = 1000
    monkeypatch.setattr(module.time, 'monotonic', lambda: 1000 + age)
    account._gsa_authenticate = AsyncMock(side_effect=UnauthorizedError('synthetic-refresh-rejected'))
    try:
        if use_cached:
            assert await account.request_pet() == 'synthetic-transient-pet'
            account._gsa_authenticate.assert_not_awaited()
        else:
            with pytest.raises(UnauthorizedError):
                await account.request_pet()
            account._gsa_authenticate.assert_awaited_once()
            assert account._recovery_pet is None
        assert 'synthetic-transient-pet' not in str(account.to_json())
    finally:
        await flow.close()
    assert account._recovery_pet is None
    assert account._recovery_pet_at is None


async def test_native_delegate_retains_only_transient_pet_copy(tmp_path, monkeypatch):
    from custom_components.homecircle._vendor_findmy.reports import account as module
    flow = FindMySetup.create(tmp_path / 'unused.bin', onboarding=False)
    account = flow.account
    account._username = 'synthetic@example.test'
    account._set_login_state(LoginState.AUTHENTICATED, {
        'idms_pet': 'synthetic-transient-pet', 'adsid': 'synthetic-adsid'})
    account._gsa_pet_at = 1000
    account.get_anisette_headers = AsyncMock(return_value={})
    account._http.post = AsyncMock(return_value=HttpResponse(200, plistlib.dumps({
        'dsid': 'synthetic', 'delegates': {'com.apple.mobileme': {'service-data': {
            'tokens': {'mmeAuthToken': 'synthetic-mme'}}}}})))
    monkeypatch.setattr(module.time, 'monotonic', lambda: 1002)
    try:
        assert await account._login_mobileme() == LoginState.LOGGED_IN
        assert account._recovery_pet_at == 1000
        account._gsa_authenticate = AsyncMock()
        assert await account.request_pet() == 'synthetic-transient-pet'
        account._gsa_authenticate.assert_not_awaited()
        assert 'synthetic-transient-pet' not in str(account.to_json())
    finally:
        await flow.close()


@pytest.mark.parametrize('value,service,expected', [
    ('https://p24-ckdatabase.icloud.com:443', 'ckdatabase', 'https://p24-ckdatabase.icloud.com:443'),
    ({'url': 'https://p24-ckcoderouter.icloud.com'}, 'ckcoderouter', 'https://p24-ckcoderouter.icloud.com'),
    ('https://gateway.icloud.com/ckcoderouter', 'ckcoderouter', 'https://gateway.icloud.com/ckcoderouter'),
    ('http://p24-ckcoderouter.icloud.com', 'ckcoderouter', None),
    ('https://untrusted.example/ckcoderouter', 'ckcoderouter', None),
    ('https://gateway.icloud.com@untrusted.example', 'ckcoderouter', None),
    ('https://gateway.icloud.com/ckcoderouter?secret=value', 'ckcoderouter', None),
    ('https://p24-ckdatabase.icloud.com', 'ckcoderouter', None),
])
def test_only_apple_service_routes_are_usable(value, service, expected):
    from custom_components.homecircle._vendor_findmy.cloudkit.client import _routing_url
    assert _routing_url(value, service) == expected


async def test_direct_and_settings_routes_fill_missing_gateways(tmp_path):
    from custom_components.homecircle._vendor_findmy.cloudkit.client import AsyncCloudKitClient
    flow = FindMySetup.create(tmp_path / 'unused.bin', onboarding=False)
    account = flow.account
    account._set_login_state(LoginState.LOGGED_IN, {'dsid': 'synthetic', 'mobileme_data': {
        'tokens': {'mmeAuthToken': 'synthetic-mme'}}})
    account._http.post = AsyncMock(return_value=HttpResponse(200, plistlib.dumps({
        'tokens': {'cloudKitToken': 'synthetic-ck'}, 'webservices': {
            'CKCodeService': {'url': 'https://p24-ckcoderouter.icloud.com:443'}}})))
    account.get_anisette_headers = AsyncMock(return_value={})
    client = AsyncCloudKitClient(account)
    client._http.post = AsyncMock(return_value=HttpResponse(200, b'{"cloudKitUserId":"synthetic-user", "cloudKitDatabaseUrl":"https://p24-ckdatabase.icloud.com"}'))
    try:
        info = await client.open_container()
        assert info.database_gateway_url == 'https://p24-ckdatabase.icloud.com'
        assert info.code_gateway_url == 'https://p24-ckcoderouter.icloud.com:443'
        assert account._recovery_diagnostics['code_gateway_present'] is True
        assert '_cloudkit_routes' not in str(account.to_json())
    finally:
        await client.close()
        await flow.close()
    assert account._cloudkit_routes == {}


async def test_valid_container_without_code_routes_uses_shared_apple_gateway(tmp_path):
    from custom_components.homecircle._vendor_findmy.cloudkit.client import AsyncCloudKitClient
    flow = FindMySetup.create(tmp_path / 'unused.bin', onboarding=False)
    account = flow.account
    account._set_login_state(LoginState.LOGGED_IN, {'dsid': 'synthetic', 'mobileme_data': {
        'tokens': {'mmeAuthToken': 'synthetic-mme', 'cloudKitToken': 'synthetic-ck'}}})
    account.get_anisette_headers = AsyncMock(return_value={})
    client = AsyncCloudKitClient(account)
    client._http.post = AsyncMock(side_effect=[
        HttpResponse(200, b'{"cloudKitUserId":"synthetic-user", "cloudKitDatabaseUrl":"https://p24-ckdatabase.icloud.com"}'),
        HttpResponse(400, b''),
    ])
    try:
        with pytest.raises(UnhandledProtocolError):
            await client.function_invoke('Cuttlefish', 'fetchViableBottles', b'')
        assert client._http.post.await_count == 2
        request = client._http.post.await_args
        assert request.args[0] == 'https://gateway.icloud.com/ckcoderouter/api/client/code/invoke'
        assert request.kwargs['headers']['x-cloudkit-authtoken'] == 'synthetic-ck'
        assert request.kwargs['headers']['x-cloudkit-userid'] == 'synthetic-user'
        assert account._recovery_diagnostics['operation_http'] == 400
        assert account._recovery_diagnostics['code_gateway_present'] is True
    finally:
        await client.close()
        await flow.close()


async def test_item_recovery_failure_logs_only_safe_phase_metadata(tmp_path, caplog):
    from types import SimpleNamespace
    from custom_components.homecircle.findmy_setup import FindMySetupError
    flow = FindMySetup.create(tmp_path / 'unused.bin', onboarding=False)
    flow.records = [object()]
    async def failed_unlock(*args):
        flow.account._recovery_diagnostics.update({
            'unlock_phase': 'inner_decrypt', 'escrow_http': 200, 'escrow_code': -42,
            'private': 'synthetic-secret-payload'})
        raise ValueError('synthetic-private-passcode-or-response')
    flow.client = SimpleNamespace(unlock=failed_unlock, close=AsyncMock())
    try:
        with pytest.raises(FindMySetupError):
            await flow.discover(0, 'synthetic-private-passcode')
        assert 'inner_decrypt' in caplog.text
        assert '-42' in caplog.text
        assert 'synthetic-private' not in caplog.text
        assert 'synthetic-secret' not in caplog.text
        assert flow.unlock_attempts == 1
    finally:
        await flow.close()


async def test_direct_record_sync_does_not_add_gateway_routing_segment(tmp_path):
    from custom_components.homecircle._vendor_findmy.cloudkit.client import AsyncCloudKitClient
    flow = FindMySetup.create(tmp_path / 'unused.bin', onboarding=False)
    account = flow.account
    account._set_login_state(LoginState.LOGGED_IN, {'dsid': 'synthetic', 'mobileme_data': {
        'tokens': {'mmeAuthToken': 'synthetic-mme', 'cloudKitToken': 'synthetic-ck'}}})
    account.get_anisette_headers = AsyncMock(return_value={})
    client = AsyncCloudKitClient(account)
    client._http.post = AsyncMock(side_effect=[
        HttpResponse(200, b'{"cloudKitUserId":"synthetic-user", "cloudKitDatabaseUrl":"https://p24-ckdatabase.icloud.com"}'),
        HttpResponse(400, b''),
    ])
    try:
        with pytest.raises(UnhandledProtocolError):
            await client.record_sync('synthetic-zone')
        assert client._http.post.await_args.args[0] == 'https://p24-ckdatabase.icloud.com/api/client/record/sync'
        assert client._http.post.await_count == 2
    finally:
        await client.close()
        await flow.close()


async def test_unauthorized_operation_metadata_excludes_realm_and_response_values(tmp_path):
    from custom_components.homecircle._vendor_findmy.cloudkit.client import AsyncCloudKitClient
    flow = FindMySetup.create(tmp_path / 'unused.bin', onboarding=False)
    account = flow.account
    account._set_login_state(LoginState.LOGGED_IN, {'dsid': 'synthetic', 'mobileme_data': {
        'tokens': {'mmeAuthToken': 'synthetic-mme', 'cloudKitToken': 'synthetic-ck'}}})
    account.get_anisette_headers = AsyncMock(return_value={})
    client = AsyncCloudKitClient(account)
    client._http.post = AsyncMock(side_effect=[
        HttpResponse(200, b'{"cloudKitUserId":"synthetic-user", "cloudKitDatabaseUrl":"https://p24-ckdatabase.icloud.com"}'),
        HttpResponse(401, b'{"serverErrorCode":"AUTHENTICATION_FAILED","reason":"synthetic-private-response"}', {'WWW-Authenticate': 'Basic realm="synthetic-private-realm"'}),
    ])
    try:
        with pytest.raises(UnauthorizedError):
            await client.zone_retrieve()
        assert account._recovery_diagnostics['operation_auth_scheme'] == 'Basic'
        assert account._recovery_diagnostics['operation_server_code'] == 'AUTHENTICATION_FAILED'
        assert 'synthetic-private' not in str(account._recovery_diagnostics)
    finally:
        await client.close()
        await flow.close()


@pytest.mark.parametrize('returned_zone', ['BeaconStore', 'different-zone', None])
@pytest.mark.parametrize('profile', ['1970', '479'])
async def test_named_zone_request_uses_shared_gateway_and_checks_response(tmp_path, returned_zone, profile):
    import gzip
    from custom_components.homecircle._vendor_findmy.cloudkit.client import AsyncCloudKitClient, encode_delimited
    from custom_components.homecircle._vendor_findmy.cloudkit.proto import cloudkit_pb2 as ck
    from custom_components.homecircle._vendor_findmy.cloudkit.constants import ResultCode

    flow = FindMySetup.create(tmp_path / 'unused.bin', onboarding=False)
    account = flow.account
    account._set_login_state(LoginState.LOGGED_IN, {'dsid': 'synthetic', 'mobileme_data': {
        'tokens': {'mmeAuthToken': 'synthetic-mme', 'cloudKitToken': 'synthetic-ck'}}})
    account.get_anisette_headers = AsyncMock(return_value={})
    response = ck.ResponseOperation(result=ck.Result(code=int(ResultCode.SUCCESS)))
    if returned_zone:
        response.zone_retrieve_response.zone_summary.add().target_zone.zone_identifier.value.name = returned_zone
    client = AsyncCloudKitClient(account, protocol_version=profile)
    client._http.post = AsyncMock(side_effect=[
        HttpResponse(200, b'{"cloudKitUserId":"synthetic-user", "cloudKitDatabaseUrl":"https://p24-ckdatabase.icloud.com"}'),
        HttpResponse(200, encode_delimited(response)),
    ])
    try:
        if returned_zone == 'BeaconStore':
            zones = await client.zone_retrieve('BeaconStore')
            assert len(zones) == 1
        else:
            with pytest.raises(UnhandledProtocolError, match='did not return the requested zone'):
                await client.zone_retrieve('BeaconStore')
        assert client._http.post.await_count == 2
        call = client._http.post.await_args
        assert call.args[0] == 'https://gateway.icloud.com/ckdatabase/api/client/zone/retrieve'
        assert call.kwargs['headers']['x-cloudkit-authtoken'] == 'synthetic-ck'
        raw = gzip.decompress(call.kwargs['data'])
        # Request length uses protobuf varint framing; skip that prefix to decode it.
        offset = next(i + 1 for i, byte in enumerate(raw) if byte < 128)
        request = ck.RequestOperation.FromString(raw[offset:])
        identifier = request.zone_retrieve_request.zone_identifier
        assert identifier.value.name == 'BeaconStore'
        assert identifier.owner_identifier.name == 'synthetic-user'
        assert not request.header.HasField('user_token')
        assert request.header.device_library_version == profile
        assert f'CloudKit/{profile}' in call.kwargs['headers']['user-agent']
        assert f'CloudKitDaemon/{profile}' in call.kwargs['headers']['x-mme-client-info']
        import hashlib
        header = request.header
        for name, number in [('device_flow_control_key', 12), ('device_flow_control_budget', 13),
                             ('device_flow_control_budget_cap', 14), ('device_flow_control_regeneration', 15),
                             ('unknown_32', 32)]:
            assert header.DESCRIPTOR.fields_by_name[name].number == number
            assert header.HasField(name)
        assert header.device_flow_control_key == 'CKDFetchRecordZonesOperation-PRIVATE'
        assert header.device_flow_control_budget == header.device_flow_control_budget_cap == 0
        assert header.device_flow_control_regeneration == 0.0
        assert header.unknown_32 == hashlib.sha1(header.device_identifier.name.encode(), usedforsecurity=False).hexdigest()
        assert not header.HasField('group')
        assert not request.request.HasField('synchronous_mode')
        assert not identifier.HasField('environment')
    finally:
        await client.close()
        await flow.close()


@pytest.mark.parametrize('content,media,kind,code', [
    (b'<html>synthetic-private-token</html>', 'text/html; charset=utf-8', 'html', None),
    (b'{"status":-42,"reason":"synthetic-private-token"}', 'application/json', 'json', -42),
    (plistlib.dumps({'status': 17, 'private': 'synthetic-private-token'}), 'application/x-plist', 'plist', 17),
    (b'{"status":true}', 'application/json', 'json', None),
    (b'{"errorCode":1000001}', 'application/json', 'json', None),
    (b'{"status":"synthetic-private-token"}', 'application/json', 'json', None),
    (b'malformed', 'application/x-protobuf', 'unknown', None),
    (b'', '', 'empty', None),
    (b'x' * 65537, 'text/plain', 'unknown', None),
])
def test_rejection_metadata_never_returns_response_or_header_text(content, media, kind, code):
    from custom_components.homecircle._vendor_findmy.cloudkit.client import _rejection_metadata
    result = _rejection_metadata(HttpResponse(401, content, {
        'Content-Type': media, 'Server': 'synthetic-private-server',
        'X-Private-Value': 'synthetic-private-token'}))
    assert result['operation_body_kind'] == kind
    assert result.get('operation_error_code') == code
    assert result['operation_server_family'] == 'other'
    assert 'synthetic-private' not in str(result)
    assert content.decode(errors='ignore') not in str(result) if content else True


def test_protobuf_rejection_records_only_result_code():
    from custom_components.homecircle._vendor_findmy.cloudkit.client import _rejection_metadata, encode_delimited
    from custom_components.homecircle._vendor_findmy.cloudkit.proto import cloudkit_pb2 as ck
    response = ck.ResponseOperation(result=ck.Result(code=42, error=ck.Error(error_description='synthetic-private-response')))
    result = _rejection_metadata(HttpResponse(401, encode_delimited(response), {'Content-Type':'application/x-protobuf'}))
    assert result['operation_body_kind'] == 'protobuf'
    assert result['operation_result_code'] == 42
    assert 'synthetic-private' not in str(result)


@pytest.mark.parametrize('alternate_status', [200, 401])
async def test_transport_replay_keeps_request_and_tls_and_never_promotes_response(tmp_path, monkeypatch, alternate_status):
    import ssl
    from types import SimpleNamespace
    import httpx
    from custom_components.homecircle._vendor_findmy.cloudkit.client import AsyncCloudKitClient
    from custom_components.homecircle._vendor_findmy.util.tls import apple_trust_context
    flow = FindMySetup.create(tmp_path / 'unused.bin', onboarding=False)
    account = flow.account
    account._set_login_state(LoginState.LOGGED_IN, {'dsid': 'synthetic', 'mobileme_data': {
        'tokens': {'mmeAuthToken': 'synthetic-mme', 'cloudKitToken': 'synthetic-ck'}}})
    account.get_anisette_headers = AsyncMock(return_value={})
    import sys
    # The HTTP client is mocked; make the optional runtime dependency available.
    monkeypatch.setitem(sys.modules, 'h2', SimpleNamespace())
    captured = {}
    replay = AsyncMock(return_value=SimpleNamespace(
        status_code=alternate_status, http_version='HTTP/2', content=b'', headers={}))
    class Transport:
        def __init__(self, **kwargs):
            captured.update(kwargs)
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            captured['closed'] = True
        post = replay
    monkeypatch.setattr(httpx, 'AsyncClient', Transport)
    client = AsyncCloudKitClient(account, compare_transport=True)
    client._http.post = AsyncMock(side_effect=[
        HttpResponse(200, b'{"cloudKitUserId":"synthetic-user", "cloudKitDatabaseUrl":"https://p24-ckdatabase.icloud.com"}'),
        HttpResponse(401, b''), HttpResponse(401, b''),
    ])
    try:
        with pytest.raises(UnauthorizedError):
            await client.zone_retrieve('BeaconStore')
        original = client._http.post.await_args
        replay.assert_awaited_once_with(original.args[0], headers=original.kwargs['headers'], content=original.kwargs['data'])
        assert captured['verify'] is not apple_trust_context()
        assert captured['verify'].verify_mode == ssl.CERT_REQUIRED
        assert captured['verify'].check_hostname is True
        assert captured['trust_env'] is False
        assert captured['follow_redirects'] is False
        assert captured['closed'] is True
        assert account._recovery_diagnostics['transport_http'] == alternate_status
        assert account._recovery_diagnostics['transport_protocol'] == 'HTTP/2'
        assert account._recovery_diagnostics['operation_http'] == 401
        assert 'synthetic' not in str(account._recovery_diagnostics)
        with pytest.raises(UnauthorizedError):
            await client.zone_retrieve('BeaconStore')
        assert replay.await_count == 1
    finally:
        await client.close()
        await flow.close()


async def test_zone_alignment_does_not_change_other_operation_headers(tmp_path):
    from custom_components.homecircle._vendor_findmy.cloudkit.client import AsyncCloudKitClient
    from custom_components.homecircle._vendor_findmy.cloudkit.constants import OperationType
    flow = FindMySetup.create(tmp_path / 'unused.bin', onboarding=False)
    client = AsyncCloudKitClient(flow.account)
    try:
        for operation in (OperationType.RECORD_RETRIEVE_CHANGES_TYPE, OperationType.FUNCTION_INVOKE_TYPE):
            request = client._build_request(operation)
            assert request.header.HasField('group')
            assert request.request.HasField('synchronous_mode')
            assert not request.header.HasField('device_flow_control_key')
            assert not request.header.HasField('unknown_32')
    finally:
        await client.close()
        await flow.close()
