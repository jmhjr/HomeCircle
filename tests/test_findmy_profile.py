"""New endpoint policy is isolated from legacy report restoration."""
from unittest.mock import AsyncMock
import pytest

from custom_components.homecircle.findmy_setup import FindMySetup, sdk
from custom_components.homecircle.findmy_reports import AccountClient
from custom_components.homecircle.findmy_profile import ANDROID_CLIENT_INFO


@pytest.mark.parametrize('restore', [False, True])
async def test_all_native_label_builders_and_recovery_use_android(tmp_path, restore):
    from custom_components.homecircle._vendor_findmy.cloudkit.client import AsyncCloudKitClient
    from custom_components.homecircle._vendor_findmy.keychain.escrow import AsyncEscrowProxy
    original, provider, _, _ = sdk()
    seed = original(provider(libs_path=tmp_path / 'unused.bin'))
    state = seed.to_json()
    await seed.close()
    flow = FindMySetup.create(tmp_path / 'unused.bin', state if restore else None, onboarding=False)
    account = flow.account
    ids = account.to_json()['ids'].copy()
    account.get_anisette_headers = AsyncMock(return_value={})
    cloudkit = AsyncCloudKitClient(account)
    proxy = AsyncEscrowProxy(account, 'https://p01-escrowproxy.icloud.com', 'synthetic-pet')
    try:
        labels = [account.client_info, account._anisette.client_akd, account.gsa_client_info]
        assert account.endpoint_policy is None
        assert not getattr(account._anisette, '_bounded_onboarding', False)
        labels += [account.identity.client_info(bundle) for bundle in ['com.apple.accountsd', 'com.apple.sbd']]
        service_label = (await cloudkit._cloudkit_headers())['x-mme-client-info']
        assert 'iPhone' in service_label and 'Mac' not in service_label
        labels.append((await proxy._headers())['X-Mme-Client-Info'])
        assert all('Android' in label and 'Pixel 8' in label for label in labels)
        assert all('Mac OS X' not in label and 'macOS' not in label and 'MacBook' not in label for label in labels)
        assert account.gsa_client_info == ANDROID_CLIENT_INFO
        assert account.client_info == ANDROID_CLIENT_INFO
        assert "Xcode" not in account.client_info
        assert 'CloudKitDaemon' in service_label
        assert 'com.apple.sbd' in labels[-1]
        assert cloudkit._identity.os_version == '9.0.1'
        assert account.to_json()['ids'] == ids
    finally:
        await cloudkit.close()
        await proxy.close()
        await flow.close()


async def test_saved_report_session_cannot_restore_mac_client_label(tmp_path):
    account_type, provider, _, _ = sdk()
    seed = account_type(provider(libs_path=tmp_path / 'unused.bin'))
    state = seed.to_json()
    ids = state['ids'].copy()
    await seed.close()
    client = AccountClient.restore({'version': 2, 'session': state, 'items': {}}, tmp_path / 'unused.bin')
    try:
        assert 'Android' in client.account.client_info
        assert 'Mac' not in client.account.client_info
        assert client.account.to_json()['ids'] == ids
    finally:
        await client.close()


async def test_recovery_diagnostics_never_log_response_fields(tmp_path, caplog):
    flow = FindMySetup.create(tmp_path / 'unused.bin')
    async def fail(account):
        account._recovery_diagnostics.update({
            'phase': 'cloudkit_container', 'cloudkit_http': 403,
            'mme_token_present': True, 'cloudkit_token_present': False,
            'extra': 'synthetic-private-token',
        })
        raise RuntimeError('synthetic-private-response')
    flow.client_factory = fail
    try:
        with pytest.raises(RuntimeError):
            await flow.open_recovery()
        assert 'cloudkit_container' in caplog.text
        assert '403' in caplog.text
        assert 'synthetic-private' not in caplog.text
    finally:
        await flow.close()


@pytest.mark.parametrize('onboarding', [False])
async def test_provisioning_cannot_restore_old_client_label(monkeypatch, tmp_path, onboarding):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from custom_components.homecircle._vendor_findmy.reports import anisette as module
    from custom_components.homecircle.findmy_profile import NATIVE_CLIENT_INFO
    expected = NATIVE_CLIENT_INFO if onboarding else ANDROID_CLIENT_INFO
    flow = FindMySetup.create(tmp_path / 'libraries.bin', onboarding=onboarding)
    (tmp_path / 'libraries.bin').write_bytes(b'synthetic-library-cache')
    device = SimpleNamespace(
        _server_friendly_description='synthetic-old-label',
        unique_device_identifier='synthetic-device-id', local_user_uuid='synthetic-local-id',
        adi_identifier='synthetic-adi-id', write=Mock(),
    )
    profiles = []
    engine = SimpleNamespace(
        _ani_provider=SimpleNamespace(device=device, provisioning_session=SimpleNamespace(
            _http=SimpleNamespace(connection_pool_kw={}))), is_provisioned=True,
        provision=lambda: profiles.append(device._server_friendly_description),
    )
    seen = []
    def load(*_args, default_device_config):
        seen.append(default_device_config.server_friendly_description)
        if onboarding:
            import re
            from uuid import UUID
            assert re.fullmatch('[0-9A-F]{64}', default_device_config.local_user_uuid)
            assert str(UUID(default_device_config.unique_device_id)).upper() == default_device_config.unique_device_id
            assert UUID(default_device_config.unique_device_id).version == 4
            assert re.fullmatch('[0-9a-f]{16}', default_device_config.adi_id)
        return engine
    monkeypatch.setattr(module.Anisette, 'load', load)
    try:
        assert await flow.account._anisette._get_ani() is engine
        assert seen == profiles == [expected]
        import ssl
        transport = engine._ani_provider.provisioning_session._http
        context = (transport.http._context if onboarding else transport.connection_pool_kw["ssl_context"])
        assert context.check_hostname is True
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert device.unique_device_identifier == 'synthetic-device-id'
        assert device.local_user_uuid == 'synthetic-local-id'
        assert device.adi_identifier == 'synthetic-adi-id'
        device.write.assert_called_once()
    finally:
        flow.account._anisette._ani = None
        await flow.close()


def test_native_trust_includes_verified_apple_g3_without_disabling_tls(monkeypatch):
    import ssl
    from custom_components.homecircle._vendor_findmy.util import tls
    context = tls.apple_trust_context()
    names = {v for cert in context.get_ca_certs() for group in cert['subject'] for k,v in group if k == 'commonName'}
    assert 'Apple Root CA' in names
    assert 'Apple Root CA - G3' in names
    assert context.check_hostname is True
    assert context.verify_mode == ssl.CERT_REQUIRED
    monkeypatch.setattr(tls, 'APPLE_ROOT_G3_SHA256', bytes(32))
    with pytest.raises(tls.TlsError, match='fingerprint mismatch'):
        tls._verified_g3_root()


async def test_new_onboarding_binds_account_to_its_own_mac_identity(tmp_path):
    import re
    from custom_components.homecircle._findmy_runtime.provider import CLIENT_INFO
    from custom_components.homecircle._vendor_findmy.reports.endpoint_policy import MAC_COREADI_V1

    flow = FindMySetup.create(tmp_path / 'unused.bin')
    account = flow.account
    provider = account._anisette
    ids = (account.local_user_uuid, account.device_uuid)
    provider._get_ani = AsyncMock(return_value=provider)
    account.login = AsyncMock(return_value=flow.states.REQUIRE_2FA)
    account.get_2fa_methods = AsyncMock(return_value=[])
    try:
        assert account.endpoint_policy is MAC_COREADI_V1
        assert provider._homecircle_mac
        assert re.fullmatch('[0-9A-F]{32}', ids[0])
        assert re.fullmatch('00006000-[0-9A-F]{16}', ids[1])
        assert ids == (provider.local_user_uuid, provider.device_uuid)
        assert await flow.login('example@example.invalid', 'example-secret') == 'factor'
        assert (account.local_user_uuid, account.device_uuid) == ids
        assert provider.client == CLIENT_INFO
        assert all('MacBookPro13,2' in account.endpoint_policy.profile(stage).client_info
                   for stage in ('gsa', 'settings', 'escrow', 'cloudkit'))
    finally:
        await flow.close()


async def test_explicit_legacy_reconnect_uses_fresh_mac_without_rewriting_saved_connection(tmp_path):
    import base64
    from copy import deepcopy
    from custom_components.homecircle._vendor_findmy.reports.endpoint_policy import MAC_COREADI_V1

    account_type, provider, _, _ = sdk()
    seed = account_type(provider(libs_path=tmp_path / 'unused.bin'))
    from custom_components.homecircle.findmy_profile import configure_account
    configure_account(seed)
    state = seed.to_json()
    state['anisette']['prov_data'] = base64.b64encode(b'synthetic-vfs').decode()
    state['anisette']['serial'] = 'synthetic-serial'
    before = deepcopy(state)
    await seed.close()
    flow = FindMySetup.create(tmp_path / 'unused.bin', state)
    try:
        account = flow.account
        assert state == before
        assert (account.local_user_uuid, account.device_uuid) != (before['ids']['uid'], before['ids']['devid'])
        assert account.endpoint_policy is MAC_COREADI_V1
        assert account._anisette._homecircle_mac
        assert account.login_state.value == 0 and account._login_state_data == {}
        assert account._password is None
        assert 'endpoint_policy' not in state
        # Restoring the still-active old report connection keeps its old IDs.
        old = AccountClient.restore({'version': 2, 'session': state, 'items': {}}, tmp_path / 'unused.bin')
        try:
            assert old.account.to_json()['ids'] == before['ids']
            assert old.account.to_json()['anisette'] == before['anisette']
        finally:
            await old.close()
    finally:
        await flow.close()


async def test_marked_saved_report_restores_endpoint_policy(tmp_path):
    from tests.test_findmy_mac_onboarding import original_account
    from custom_components.homecircle._findmy_runtime.provider import CLIENT_INFO
    from custom_components.homecircle._vendor_findmy.reports.endpoint_policy import MAC_COREADI_V1

    account = await original_account(tmp_path)
    state = account.to_json()
    state['account']['password'] = None
    await account.close()
    client = AccountClient.restore({'version': 2, 'session': state, 'items': {}}, tmp_path / 'unused.bin')
    try:
        assert client.account.endpoint_policy is MAC_COREADI_V1
        assert client.account.to_json()['ids'] == state['ids']
        assert client.account.client_info == CLIENT_INFO
    finally:
        await client.close()


async def test_onboarding_cloudkit_and_escrow_profiles_ignore_global_gsa_label(tmp_path):
    from custom_components.homecircle._vendor_findmy.cloudkit.client import AsyncCloudKitClient
    from custom_components.homecircle._vendor_findmy.keychain.escrow import AsyncEscrowProxy
    from custom_components.homecircle._vendor_findmy.util.onboarding_http import BoundedHttpSession

    flow = FindMySetup.create(tmp_path / 'unused.bin')
    account = flow.account
    account.gsa_client_info = '<SYNTHETIC> <Android;0;0> <synthetic>'
    account.cloudkit_client_info = '<SYNTHETIC> <Windows;0;0> <synthetic>'
    account.get_anisette_headers = AsyncMock(return_value={'X-MMe-Client-Info': 'synthetic-other'})
    cloudkit = AsyncCloudKitClient(account)
    proxy = AsyncEscrowProxy(account, 'https://p01-escrowproxy.icloud.com', 'synthetic-pet')
    try:
        assert all(isinstance(client._http, BoundedHttpSession) for client in (account, cloudkit, proxy))
        ck = await cloudkit._cloudkit_headers()
        escrow = await proxy._headers()
        assert ck['x-mme-client-info'] == account.endpoint_policy.profile('cloudkit').client_info
        assert 'MacBookPro13,2' in ck['x-mme-client-info'] and 'Windows' not in ck['x-mme-client-info']
        assert escrow['X-Mme-Client-Info'] == account.endpoint_policy.profile('escrow').client_info
        assert 'MacBookPro13,2' in escrow['X-Mme-Client-Info'] and 'com.apple.sbd' in escrow['X-Mme-Client-Info']
        assert sum(key.lower() == 'x-mme-client-info' for key in ck) == 1
        assert sum(key.lower() == 'x-mme-client-info' for key in escrow) == 1
        assert account.gsa_client_info.startswith('<SYNTHETIC>')
    finally:
        await cloudkit.close()
        await proxy.close()
        await flow.close()
