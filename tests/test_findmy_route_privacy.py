"""A route diagnostic must change only destination and never disclose account data."""
import logging
from unittest.mock import AsyncMock

import pytest

from custom_components.homecircle.findmy_setup import FindMySetup
from custom_components.homecircle._vendor_findmy.cloudkit.client import AsyncCloudKitClient
from custom_components.homecircle._vendor_findmy.errors import UnauthorizedError, UnhandledProtocolError
from custom_components.homecircle._vendor_findmy.reports.account import _refused, logger
from custom_components.homecircle._vendor_findmy.reports.state import LoginState
from custom_components.homecircle._vendor_findmy.util.http import HttpResponse


@pytest.mark.parametrize('route,status', [
    ('https://p24-ckdatabase.icloud.com', 200),
    ('https://p24-ckdatabase.icloud.com', 401),
    ('https://p24-ckdatabase.icloud.com', 302),
    ('https://gateway.icloud.com/ckdatabase', None),
    ('https://not-apple.invalid/ckdatabase', None),
    ('https://p24-ckdatabase.icloud.com.evil.invalid', None),
    ('https://secret@p24-ckdatabase.icloud.com', None),
    ('https://p24-ckdatabase.icloud.com?token=secret', None),
    ('http://p24-ckdatabase.icloud.com', None),
    (None, None),
])
async def test_route_comparison_reuses_exact_request_without_promoting(tmp_path, route, status):
    import json
    flow = FindMySetup.create(tmp_path / 'unused.bin')
    account = flow.account
    account._set_login_state(LoginState.LOGGED_IN, {'dsid': 'synthetic', 'mobileme_data': {
        'tokens': {'mmeAuthToken': 'synthetic-mme', 'cloudKitToken': 'synthetic-ck',
                   'searchPartyToken': 'synthetic-report'}}})
    account.get_anisette_headers = AsyncMock(return_value={'x-synthetic': 'synthetic-identity'})
    client = AsyncCloudKitClient(account, compare_zone_route=True)
    container = {'cloudKitUserId': 'synthetic-user', 'cloudKitDatabaseUrl': route}
    responses = [HttpResponse(200, json.dumps(container).encode()), HttpResponse(401, b'')]
    if status is not None:
        responses.append(HttpResponse(status, b'synthetic-private-response', {'Location': 'https://evil.invalid'}))
    responses.append(HttpResponse(401, b''))
    client._http.post = AsyncMock(side_effect=responses)
    original = dict(account.service_tokens)
    try:
        with pytest.raises(UnauthorizedError):
            await client.zone_retrieve('BeaconStore')
        calls = list(client._http.post.await_args_list)
        assert len(calls) == (3 if status is not None else 2)
        if status is not None:
            assert calls[2].args[0] == 'https://p24-ckdatabase.icloud.com/api/client/zone/retrieve'
            assert calls[1].kwargs == calls[2].kwargs
            assert calls[2].kwargs['auto_retry'] is False
            assert calls[2].kwargs['allow_redirects'] is False
            assert account._recovery_diagnostics['route_http'] == status
        expected_kind = 'partition' if status is not None else 'shared' if route == 'https://gateway.icloud.com/ckdatabase' else 'missing'
        assert account._recovery_diagnostics['route_kind'] == expected_kind
        assert account._recovery_diagnostics['route_error'] == ('none' if status is not None else 'same_route' if expected_kind == 'shared' else 'unavailable')
        assert account._recovery_diagnostics['route_profile'] == '1970'
        assert account.service_tokens == original
        assert account._recovery_diagnostics['operation_http'] == 401
        assert 'synthetic' not in str(account._recovery_diagnostics)
        assert 'p24' not in str(account._recovery_diagnostics)
        with pytest.raises(UnauthorizedError):
            await client.zone_retrieve('BeaconStore')
        assert client._http.post.await_count == len(calls) + 1
    finally:
        await client.close()
        await flow.close()


async def test_route_comparison_exception_does_not_replace_baseline(tmp_path):
    flow = FindMySetup.create(tmp_path / 'unused.bin')
    account = flow.account
    account._set_login_state(LoginState.LOGGED_IN, {'dsid': 'synthetic', 'mobileme_data': {
        'tokens': {'mmeAuthToken': 'synthetic-mme', 'cloudKitToken': 'synthetic-ck'}}})
    account.get_anisette_headers = AsyncMock(return_value={})
    client = AsyncCloudKitClient(account, compare_zone_route=True)
    client._http.post = AsyncMock(side_effect=[
        HttpResponse(200, b'{"cloudKitUserId":"synthetic-user","cloudKitDatabaseUrl":"https://p24-ckdatabase.icloud.com"}'),
        HttpResponse(401, b''), RuntimeError('synthetic-private-exception')])
    try:
        with pytest.raises(UnauthorizedError, match='Apple rejected'):
            await client.zone_retrieve('BeaconStore')
        assert account._recovery_diagnostics['route_error'] == 'request_failed'
        assert account._recovery_diagnostics['operation_http'] == 401
        assert 'synthetic' not in str(account._recovery_diagnostics)
    finally:
        await client.close()
        await flow.close()


def test_refusal_logs_no_header_values_even_when_logger_enabled(caplog, monkeypatch):
    # Capture this dependency directly: production sinks its entire namespace.
    monkeypatch.setattr(logger, 'disabled', False)
    monkeypatch.setattr(logger, 'level', logging.DEBUG)
    monkeypatch.setattr(logger, 'handlers', [caplog.handler])
    monkeypatch.setattr(logger, 'propagate', False)
    sent = {'X-Mme-Device-Id': 'private-device', 'X-Apple-I-MD-LU': 'private-user',
            'X-Apple-I-SRL-NO': 'private-serial', 'Authorization': 'private-credential',
            'Unexpected-Header': 'private-future-secret'}
    response = HttpResponse(429, b'private-body', {'Set-Cookie': 'private-cookie',
                            'Unexpected-Header': 'private-response', 'Retry-After': '45'})
    with caplog.at_level(logging.WARNING):
        error = _refused(response, sent, 'The Grand Slam request')
    assert 'HTTP 429' in caplog.text
    assert 'private-' not in caplog.text
    assert error.retry_after == 45


async def test_announce_refusal_never_logs_body_or_headers(tmp_path, caplog, monkeypatch):
    flow = FindMySetup.create(tmp_path / 'unused.bin')
    account = flow.account
    account._set_login_state(LoginState.LOGGED_IN, {'adsid': 'synthetic', 'idms_hb': 'synthetic'})
    account.get_anisette_headers = AsyncMock(return_value={})
    account._http.post = AsyncMock(return_value=HttpResponse(401, b'private-body',
                                   {'Set-Cookie': 'private-cookie'}))
    monkeypatch.setattr(logger, 'disabled', False)
    monkeypatch.setattr(logger, 'level', logging.DEBUG)
    monkeypatch.setattr(logger, 'handlers', [caplog.handler])
    monkeypatch.setattr(logger, 'propagate', False)
    try:
        with caplog.at_level(logging.DEBUG), pytest.raises(UnhandledProtocolError) as error:
            await account.announce_device()
        assert 'postdata refused with HTTP 401' in caplog.text
        assert 'private-' not in caplog.text
        assert 'private-' not in str(error.value)
    finally:
        await flow.close()


async def test_http_transport_does_not_follow_redirects(socket_enabled):
    from aiohttp import web
    from custom_components.homecircle._vendor_findmy.util.http import HttpSession
    received = []

    async def start(request):
        raise web.HTTPFound('/destination')

    async def destination(request):
        received.append(dict(request.headers))
        return web.Response()

    app = web.Application()
    app.router.add_post('/start', start)
    app.router.add_route('*', '/destination', destination)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    client = HttpSession(timeout=3)
    try:
        response = await client.post(f'http://127.0.0.1:{port}/start',
            headers={'X-CloudKit-AuthToken': 'synthetic-secret'},
            data=b'synthetic', auto_retry=False, allow_redirects=False)
        assert response.status_code == 302
        assert received == []
    finally:
        await client.close()
        await runner.cleanup()


async def test_route_diagnostic_internal_error_is_contained(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from custom_components.homecircle._vendor_findmy.cloudkit import client as module
    flow = FindMySetup.create(tmp_path / 'unused.bin')
    client = AsyncCloudKitClient(flow.account, compare_zone_route=True)
    def invalid(*args):
        raise ValueError('private-parser-error')
    monkeypatch.setattr(module, '_routing_url', invalid)
    try:
        await client._compare_route(SimpleNamespace(database_gateway_url='synthetic'),
            'synthetic', {}, b'')
        assert flow.account._recovery_diagnostics['route_error'] == 'request_failed'
        assert 'private-parser-error' not in str(flow.account._recovery_diagnostics)
        flow.account._recovery_diagnostics = None
        await client._compare_route(None, 'synthetic', {}, b'')
    finally:
        await client.close()
        await flow.close()


async def test_route_guard_blocks_unsanitized_url(tmp_path):
    from types import SimpleNamespace
    flow = FindMySetup.create(tmp_path / 'unused.bin')
    client = AsyncCloudKitClient(flow.account, compare_zone_route=True)
    client._http.post = AsyncMock()
    try:
        await client._compare_route(SimpleNamespace(database_gateway_url='https://evil.invalid'),
            'https://gateway.icloud.com/ckdatabase/api/client/zone/retrieve', {}, b'')
        client._http.post.assert_not_awaited()
        assert flow.account._recovery_diagnostics['route_kind'] == 'blocked'
        assert flow.account._recovery_diagnostics['route_error'] == 'unavailable'
    finally:
        await client.close()
        await flow.close()


async def test_native_retry_cannot_report_stale_route_success(tmp_path, monkeypatch, caplog):
    from types import SimpleNamespace
    from custom_components.homecircle.findmy_setup import FindMySetupError
    from custom_components.homecircle._vendor_findmy.cloudkit import client as module
    flow = FindMySetup.create(tmp_path / 'unused.bin')
    account = flow.account
    account._set_login_state(LoginState.LOGGED_IN, {'dsid': 'synthetic', 'mobileme_data': {
        'tokens': {'mmeAuthToken': 'synthetic-mme', 'cloudKitToken': 'synthetic-ck'}}})
    account._recovery_diagnostics.update({'route_http': 200, 'route_kind': 'partition',
        'route_profile': '1970', 'route_token_pair': 'original', 'route_error': 'none'})
    account._zone_route_tested = True
    async def rejected(name):
        account._recovery_diagnostics['operation_http'] = 401
        raise UnauthorizedError('synthetic-private')
    monkeypatch.setattr(module, 'AsyncCloudKitClient', lambda *args, **kwargs:
        SimpleNamespace(zone_retrieve=rejected, close=AsyncMock()))
    try:
        with pytest.raises(FindMySetupError):
            await flow.check_zone_access()
        assert not any(key.startswith('route_') for key in account._recovery_diagnostics)
        assert "'route_http': None" in caplog.text
        assert 'synthetic-private' not in caplog.text
    finally:
        await flow.close()
