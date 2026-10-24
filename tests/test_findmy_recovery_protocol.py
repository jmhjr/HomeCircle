"""Synthetic recovery boundaries, with actual SRP server-proof verification."""
from __future__ import annotations

import asyncio
import base64
import plistlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.homecircle._findmy_runtime import onboarding
from custom_components.homecircle._vendor_findmy.errors import (
    AppleServiceUnavailableError, InvalidCredentialsError,
)
from custom_components.homecircle._vendor_findmy.keychain import recovery
from custom_components.homecircle._vendor_findmy.keychain.escrow import (
    AsyncEscrowProxy, EscrowRecoveryError, build_keyvault_message, parse_keyvault_message,
)
from custom_components.homecircle._vendor_findmy.util.http import HttpResponse
from tests.test_findmy_mac_onboarding import original_account

RECORD = SimpleNamespace(is_recovery_candidate=True, label="synthetic-record")
PASSCODE = "synthetic-owner-passcode-canary"


class Attempt:
    """Model callback events; persistence is tested by the guard's own tests."""

    def __init__(self, events):
        self.events = events
        self.state = "ready"

    async def before_dispatch(self):
        self.events.append("reserved")
        self.state = "pending"

    async def refused(self):
        self.events.append("refused")
        self.state = "refused"

    async def verified(self):
        self.events.append("verified")
        self.state = "verified"


def proxy_for(post=None, *, required=True, guarded=True):
    events = []
    attempt = Attempt(events)
    account = SimpleNamespace(account_name="test@example.invalid")
    account._homecircle_recovery_guard_required = required
    # Deliberately poisoned old diagnostics must never classify the new outcome.
    account._recovery_diagnostics = {"escrow_http": 401, "escrow_code": -42}
    if guarded:
        account._homecircle_recovery_attempt = attempt
    proxy = AsyncEscrowProxy.__new__(AsyncEscrowProxy)
    proxy._account, proxy._host, proxy._pet = account, "https://example.icloud.com", "synthetic-private-pet"

    async def headers():
        events.append("headers")
        return {"synthetic-header": "prepared"}

    proxy._headers = headers
    proxy._http = SimpleNamespace(post=post or AsyncMock(return_value=reply({"success": True})))
    return proxy, attempt, events


def reply(data, code=200):
    return HttpResponse(code, plistlib.dumps(data))


async def submit(proxy):
    return await proxy.recover(RECORD.label, b"synthetic-private-proof", "synthetic-transaction")


async def test_reservation_follows_all_headers_and_body_preparation():
    proxy, attempt, events = proxy_for()

    async def post(url, **kwargs):
        events.append("post")
        assert attempt.state == "pending"
        assert kwargs["headers"] == {"synthetic-header": "prepared"}
        assert plistlib.loads(kwargs["data"])["command"] == "RECOVER"
        assert kwargs["auto_retry"] is kwargs["allow_redirects"] is False
        return reply({"success": True})

    proxy._http.post = post
    assert await submit(proxy) == {"success": True}
    assert events == ["headers", "reserved", "post"]
    assert attempt.state == "pending"  # Response alone is not a verified server proof.


@pytest.mark.parametrize("failure", [OSError("private-transport-canary"), ValueError("private-header-canary")])
async def test_header_failure_does_not_reserve(failure):
    proxy, attempt, events = proxy_for()
    proxy._headers = AsyncMock(side_effect=failure)
    with pytest.raises(EscrowRecoveryError) as raised:
        await submit(proxy)
    assert (raised.value.stage, raised.value.dispatch_state) == ("preproof", "not_dispatched")
    assert not raised.value.server_verified
    assert raised.value.reason == ("transient" if isinstance(failure, OSError) else "protocol")
    assert attempt.state == "ready" and events == []
    proxy._http.post.assert_not_awaited()
    assert "private-" not in str(raised.value)


async def test_srp_init_never_reserves():
    proxy, attempt, events = proxy_for()
    await proxy.srp_init(RECORD.label, b"public", "transaction")
    assert events == ["headers"] and attempt.state == "ready"


@pytest.mark.parametrize("data,code,service", [
    ({"success": False, "errorMessage": "private-server-canary", "errorCode": -6015}, 409, -6015),
    ({"errorCode": -42}, 200, -42),
    ({"status": -6015}, 409, -6015),
    ({"success": False, "errorCode": 2**40}, 403, None),
])
async def test_only_explicit_refusal_resolves_pending(data, code, service):
    proxy, attempt, events = proxy_for(AsyncMock(return_value=reply(data, code)))
    with pytest.raises(EscrowRecoveryError) as raised:
        await submit(proxy)
    assert (raised.value.stage, raised.value.dispatch_state) == ("refusal", "refused")
    assert raised.value.http_status == code and raised.value.service_code == service
    assert events == ["headers", "reserved", "refused"]
    assert attempt.state == "refused" and "private-" not in str(raised.value)


@pytest.mark.parametrize("response", [
    HttpResponse(429, b"private-html-canary"), reply({}, 503), reply({"message": "private-canary"}, 409),
    reply({"errorCode": "-42"}, 401),
])
async def test_unknown_or_malformed_response_remains_uncertain(response):
    proxy, attempt, events = proxy_for(AsyncMock(return_value=response))
    with pytest.raises(EscrowRecoveryError) as raised:
        await submit(proxy)
    assert (raised.value.stage, raised.value.dispatch_state) == ("dispatch", "uncertain")
    assert raised.value.service_code is None and attempt.state == "pending"
    assert events == ["headers", "reserved"] and "private-" not in str(raised.value)


async def test_transport_timeout_remains_pending_without_retry():
    post = AsyncMock(side_effect=TimeoutError("private-response-canary"))
    proxy, attempt, _ = proxy_for(post)
    with pytest.raises(EscrowRecoveryError) as raised:
        await submit(proxy)
    assert raised.value.dispatch_state == "uncertain" and attempt.state == "pending"
    post.assert_awaited_once()


@pytest.mark.parametrize("phase", ["headers", "post"])
async def test_cancellation_distinguishes_before_and_after_reservation(phase):
    entered, release = asyncio.Event(), asyncio.Event()
    proxy, attempt, _ = proxy_for()

    async def blocked(*args, **kwargs):
        entered.set()
        await release.wait()

    if phase == "headers":
        proxy._headers = blocked
    else:
        proxy._http.post = blocked
    task = asyncio.create_task(submit(proxy))
    await asyncio.wait_for(entered.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert attempt.state == ("ready" if phase == "headers" else "pending")


@pytest.mark.parametrize("required", [False, True])
async def test_missing_callback_fails_closed_only_when_guard_required(required):
    proxy, _, _ = proxy_for(required=required, guarded=False)
    if required:
        with pytest.raises(EscrowRecoveryError) as raised:
            await submit(proxy)
        assert raised.value.dispatch_state == "not_dispatched"
        proxy._http.post.assert_not_awaited()
    else:
        assert await submit(proxy) == {"success": True}


async def test_guard_error_identity_propagates_unchanged():
    failure = RuntimeError("synthetic-local-guard-error")
    proxy, attempt, _ = proxy_for()
    attempt.before_dispatch = AsyncMock(side_effect=failure)
    with pytest.raises(RuntimeError) as raised:
        await submit(proxy)
    assert raised.value is failure
    proxy._http.post.assert_not_awaited()


def actual_srp_proxy(*, serverproof=True):
    """Run both sides of actual isolated pysrp; only HTTP is replaced in memory."""
    server = None
    proxy, attempt, events = proxy_for()
    srp = recovery.srp
    salt, verifier_key = srp.create_salted_verification_key(
        "synthetic-dsid", PASSCODE, hash_alg=srp.SHA256, ng_type=srp.NG_2048,
    )

    async def post(url, **kwargs):
        nonlocal server
        packet = plistlib.loads(kwargs["data"])
        if packet["command"] == "SRP_INIT":
            assert attempt.state == "ready"
            client_public = base64.b64decode(packet["blob"])
            server = srp.Verifier("synthetic-dsid", salt, verifier_key, client_public,
                                  hash_alg=srp.SHA256, ng_type=srp.NG_2048)
            server_salt, public = server.get_challenge()
            return reply({"dsid": "synthetic-dsid", "respBlob": build_keyvault_message(
                b"\0" * 24, [b"exchange", server_salt, public],
            )})
        assert packet["command"] == "RECOVER" and attempt.state == "pending"
        _, sections = parse_keyvault_message(base64.b64decode(packet["blob"]), 24, 2)
        proof = server.verify_session(sections[1])
        assert proof is not None and server.authenticated()
        events.append("server_verified_client")
        return reply({"respBlob": build_keyvault_message(
            b"\0" * 24, [proof if serverproof else b"bad-server-proof", b"iv", b"ciphertext"],
        )})

    proxy._http.post = post
    return proxy, attempt, events


async def test_real_serverproof_verified_before_material_work(monkeypatch):
    proxy, attempt, events = actual_srp_proxy()

    def outer(*args, **kwargs):
        assert attempt.state == "verified"
        events.append("material")
        return b"inner"

    monkeypatch.setattr(recovery, "unwrap_outer_blob", outer)
    monkeypatch.setattr(recovery, "unwrap_inner_blob", lambda blob, password: b"material")
    assert await recovery.recover_bottled_peer(proxy, RECORD, PASSCODE) == b"material"
    assert events[-3:] == ["server_verified_client", "verified", "material"]


async def test_bad_actual_serverproof_is_uncertain_without_material_use(monkeypatch):
    proxy, attempt, events = actual_srp_proxy(serverproof=False)
    outer = AsyncMock()
    monkeypatch.setattr(recovery, "unwrap_outer_blob", outer)
    with pytest.raises(recovery.RecoveryProtocolError) as raised:
        await recovery.recover_bottled_peer(proxy, RECORD, PASSCODE)
    assert (raised.value.stage, raised.value.dispatch_state) == ("serverproof", "uncertain")
    assert not raised.value.server_verified and attempt.state == "pending"
    assert "verified" not in events
    outer.assert_not_called()


async def test_postproof_material_failure_does_not_reconsume_reservation(monkeypatch):
    proxy, attempt, events = actual_srp_proxy()

    def broken(*args, **kwargs):
        raise ValueError("private-material-canary")

    monkeypatch.setattr(recovery, "unwrap_outer_blob", broken)
    with pytest.raises(recovery.RecoveryProtocolError) as raised:
        await recovery.recover_bottled_peer(proxy, RECORD, PASSCODE)
    assert (raised.value.stage, raised.value.dispatch_state) == ("material", "verified")
    assert raised.value.server_verified and attempt.state == "verified"
    assert events.count("reserved") == events.count("verified") == 1
    assert "private-" not in str(raised.value)


async def test_guard_verified_error_propagates_unchanged():
    proxy, attempt, _ = actual_srp_proxy()
    failure = RuntimeError("synthetic-local-write-error")
    attempt.verified = AsyncMock(side_effect=failure)
    with pytest.raises(RuntimeError) as raised:
        await recovery.recover_bottled_peer(proxy, RECORD, PASSCODE)
    assert raised.value is failure and attempt.state == "pending"


@pytest.mark.parametrize("cause,reason", [
    (OSError("private-network-canary"), "transient"),
    (AppleServiceUnavailableError(503, "synthetic"), "transient"),
    (InvalidCredentialsError("private-credentials-canary"), "credentials"),
    (RuntimeError("private-protocol-canary"), "protocol"),
])
async def test_pet_errors_are_structured_preproof_and_cleaned(monkeypatch, tmp_path, cause, reason):
    account = await original_account(tmp_path)
    clones = []

    async def authenticate(clone):
        clones.append(clone)
        raise cause

    monkeypatch.setattr(onboarding.AsyncAppleAccount, "_gsa_authenticate", authenticate)
    try:
        with pytest.raises(onboarding.RecoveryPETError) as raised:
            await onboarding.fresh_recovery_pet(account)
        assert raised.value.reason == reason
        assert raised.value.stage == "preproof" and raised.value.dispatch_state == "not_dispatched"
        assert clones[0]._password is None and clones[0]._login_state_data == {} and clones[0]._closed
        assert "private-" not in str(raised.value)
    finally:
        await account.close()


async def test_pet_missing_password_never_authenticates(monkeypatch, tmp_path):
    account = await original_account(tmp_path)
    account._password = None
    authenticate = AsyncMock()
    monkeypatch.setattr(onboarding.AsyncAppleAccount, "_gsa_authenticate", authenticate)
    try:
        with pytest.raises(onboarding.RecoveryPETError) as raised:
            await onboarding.fresh_recovery_pet(account)
        assert raised.value.reason == "missing_password"
        authenticate.assert_not_awaited()
    finally:
        await account.close()


async def test_verified_material_retry_skips_proof_and_pet_and_is_record_bound(monkeypatch):
    from custom_components.homecircle._vendor_findmy.keychain import session as sessions

    def closable():
        return SimpleNamespace(close=AsyncMock())
    account = SimpleNamespace(adsid="synthetic-adsid", dsid="synthetic-dsid")
    session = sessions.AsyncKeychainSession(account, closable(), closable(), closable(), closable())
    session.recovery_options = AsyncMock(return_value=SimpleNamespace(recoverable=[RECORD]))
    session._renew_token_if_stale = AsyncMock()
    recovered = AsyncMock(return_value=b"verified-private-material-canary")
    monkeypatch.setattr(sessions, "recover_bottled_peer", recovered)
    peer = SimpleNamespace(record=RECORD)
    session._recovered_material = AsyncMock(side_effect=[OSError("private-directory-canary"), peer])
    with pytest.raises(recovery.RecoveryProtocolError) as raised:
        await session.recover(RECORD, PASSCODE)
    assert raised.value.dispatch_state == "verified"
    assert session.can_resume_recovery(RECORD)
    assert not session.can_resume_recovery(SimpleNamespace(**vars(RECORD), serial="other"))
    assert await session.recover(RECORD, "") is peer
    recovered.assert_awaited_once()
    session._renew_token_if_stale.assert_awaited_once()
    await session.close()
    assert not session.can_resume_recovery(RECORD)
    assert session._verified_recovery_material is None


async def test_changed_record_cannot_reuse_verified_material(monkeypatch):
    from custom_components.homecircle._vendor_findmy.keychain import session as sessions

    def closable():
        return SimpleNamespace(close=AsyncMock())
    session = sessions.AsyncKeychainSession(SimpleNamespace(adsid="synthetic-adsid", dsid="synthetic-dsid"), closable(), closable(), closable(), closable())
    changed = SimpleNamespace(**vars(RECORD), serial="changed")
    session.recovery_options = AsyncMock(return_value=SimpleNamespace(recoverable=[RECORD, changed]))
    session._renew_token_if_stale = AsyncMock()
    recovered = AsyncMock(return_value=b"material")
    monkeypatch.setattr(sessions, "recover_bottled_peer", recovered)
    session._recovered_material = AsyncMock(return_value=object())
    await session.recover(RECORD, PASSCODE)
    await session.recover(changed, PASSCODE)
    assert recovered.await_count == 2
    assert not session.can_resume_recovery(RECORD) and not session.can_resume_recovery(changed)
    await session.close()


async def test_pcs_retry_reuses_exact_peer_without_passcode_and_close_drops_references():
    from custom_components.homecircle._vendor_findmy.icloud import AsyncFindMyClient

    peer = SimpleNamespace(record=RECORD)
    key = object()
    session = SimpleNamespace(
        recover=AsyncMock(return_value=peer), can_resume_recovery=lambda record: False,
        pcs_keys=AsyncMock(side_effect=[OSError("private-pcs-canary"), [key]]), close=AsyncMock(),
    )
    client = AsyncFindMyClient(SimpleNamespace(adsid="synthetic-adsid", dsid="synthetic-dsid"), session, SimpleNamespace(close=AsyncMock()))
    with pytest.raises(recovery.RecoveryProtocolError) as raised:
        await client.unlock(RECORD, PASSCODE)
    assert raised.value.stage == "material" and raised.value.server_verified
    assert client.can_resume_unlock(RECORD)
    assert not client.can_resume_unlock(SimpleNamespace(**vars(RECORD), serial="other"))
    assert await client.unlock(RECORD) == [key]
    session.recover.assert_awaited_once_with(RECORD, PASSCODE)
    assert client.keychain_keys == [key]
    client._zone_keys = [key]
    await client.close()
    assert client.keychain_keys == [] and client._zone_keys is None
    assert client._recovered_peer is client._recovered_peer_record is None


@pytest.mark.parametrize("change,reason", [
    ("verification", "factor_required"), ("identity", "identity_mismatch"), ("pet", "protocol"),
])
async def test_pet_factor_identity_and_material_failures_are_distinct(monkeypatch, tmp_path, change, reason):
    from custom_components.homecircle._vendor_findmy import LoginState

    account = await original_account(tmp_path)

    async def authenticate(clone):
        clone._login_state_data = {"adsid": "foreign" if change == "identity" else "1234",
                                   "idms_pet": "" if change == "pet" else "synthetic-pet"}
        clone._account_info = {"account_name": "example@example.invalid"}
        return LoginState.REQUIRE_2FA if change == "verification" else LoginState.AUTHENTICATED

    monkeypatch.setattr(onboarding.AsyncAppleAccount, "_gsa_authenticate", authenticate)
    try:
        with pytest.raises(onboarding.RecoveryPETError) as raised:
            await onboarding.fresh_recovery_pet(account)
        assert raised.value.reason == reason
    finally:
        await account.close()


async def test_pet_cleanup_failure_cannot_replace_original_structured_error(monkeypatch, tmp_path):
    account = await original_account(tmp_path)
    original_close = onboarding.AsyncAppleAccount.close
    clones = []

    async def authenticate(clone):
        clones.append(clone)
        raise OSError("private-network-canary")

    async def close(clone):
        if clone in clones:
            raise ValueError("private-cleanup-canary")
        await original_close(clone)

    monkeypatch.setattr(onboarding.AsyncAppleAccount, "_gsa_authenticate", authenticate)
    monkeypatch.setattr(onboarding.AsyncAppleAccount, "close", close)
    try:
        with pytest.raises(onboarding.RecoveryPETError) as raised:
            await onboarding.fresh_recovery_pet(account)
        assert raised.value.reason == "transient"
        assert clones[0]._password is None and clones[0]._login_state_data == {}
    finally:
        await account.close()


@pytest.mark.parametrize("phase", ["init", "complete"])
@pytest.mark.parametrize("status", [429, 503])
async def test_pet_service_failure_preserves_only_current_response_context(monkeypatch, tmp_path, phase, status):
    account = await original_account(tmp_path)
    clones = []
    failure = AppleServiceUnavailableError(
        status, "synthetic-private-request-canary", retry_after=12.25, phase=phase,
    )

    async def authenticate(clone):
        clones.append(clone)
        # A preceding response must not supply the new refusal's metadata.
        clone._signin_diagnostics = {"phase": "init", "http": 200, "retry_after": 999,
                                     "body": "synthetic-private-response-canary"}
        raise failure

    monkeypatch.setattr(onboarding.AsyncAppleAccount, "_gsa_authenticate", authenticate)
    try:
        with pytest.raises(onboarding.RecoveryPETError) as caught:
            await onboarding.fresh_recovery_pet(account)
        error = caught.value
        assert error.reason == "transient" and error.http_status == status
        assert error.auth_phase == phase and error.retry_after_seconds == 13
        assert error.stage == "preproof" and error.dispatch_state == "not_dispatched"
        assert error.server_verified is False
        assert clones[0]._password is None and clones[0]._login_state_data == {} and clones[0]._closed
        assert "synthetic-private" not in str(error)
    finally:
        await account.close()


class PrivatePhase(str):
    pass


class PrivateRetry(float):
    pass


@pytest.mark.parametrize("phase,retry,expected_phase,expected_retry", [
    ("init", 0, "init", 0), ("complete", 86400, "complete", 86400),
    ("complete", 0.01, "complete", 1), ("complete", 12.25, "complete", 13),
    (None, None, None, None), (True, True, None, None),
    (PrivatePhase("init"), PrivateRetry(5), None, None),
    ("synthetic-private-phase", "synthetic-private-header", None, None),
    ("init", -1, "init", None), ("init", 86401, "init", None),
    ("init", float("nan"), "init", None), ("init", float("inf"), "init", None),
    ("init", 10**500, "init", None),
])
def test_pet_error_context_accepts_only_exact_bounded_metadata(phase, retry, expected_phase, expected_retry):
    error = onboarding.RecoveryPETError("transient", auth_phase=phase, retry_after=retry)
    assert error.auth_phase == expected_phase and error.retry_after_seconds == expected_retry
    assert error.http_status is None and error.reason == "transient"
    assert "synthetic-private" not in str(error)


async def test_pet_transport_error_does_not_inherit_preceding_response_context(monkeypatch, tmp_path):
    account = await original_account(tmp_path)

    async def authenticate(clone):
        clone._signin_diagnostics = {"phase": "init", "http": 200, "retry_after": 999}
        raise OSError("synthetic-private-transport-canary")

    monkeypatch.setattr(onboarding.AsyncAppleAccount, "_gsa_authenticate", authenticate)
    try:
        with pytest.raises(onboarding.RecoveryPETError) as caught:
            await onboarding.fresh_recovery_pet(account)
        error = caught.value
        assert error.reason == "transient"
        assert error.http_status is error.auth_phase is error.retry_after_seconds is None
    finally:
        await account.close()


async def test_pet_cancellation_still_propagates_and_cleans_clone(monkeypatch, tmp_path):
    account = await original_account(tmp_path)
    clones = []

    async def authenticate(clone):
        clones.append(clone)
        raise asyncio.CancelledError()

    monkeypatch.setattr(onboarding.AsyncAppleAccount, "_gsa_authenticate", authenticate)
    try:
        with pytest.raises(asyncio.CancelledError):
            await onboarding.fresh_recovery_pet(account)
        assert clones[0]._password is None and clones[0]._login_state_data == {} and clones[0]._closed
    finally:
        await account.close()


async def test_failed_srp_init_is_preproof_without_reservation():
    proxy, attempt, events = proxy_for(AsyncMock(side_effect=TimeoutError("private-init-canary")))
    with pytest.raises(recovery.RecoveryProtocolError) as raised:
        await recovery.recover_bottled_peer(proxy, RECORD, PASSCODE)
    assert raised.value.stage == "preproof" and raised.value.dispatch_state == "not_dispatched"
    assert raised.value.reason == "transient"
    assert events == ["headers"] and attempt.state == "ready"


async def test_account_identity_change_refuses_cached_peer_reuse():
    from custom_components.homecircle._vendor_findmy.icloud import AsyncFindMyClient

    account = SimpleNamespace(adsid="account-a", dsid="account-a-dsid")
    session = SimpleNamespace(
        recover=AsyncMock(return_value=SimpleNamespace(record=RECORD)),
        can_resume_recovery=lambda record: False,
        pcs_keys=AsyncMock(return_value=[object()]), close=AsyncMock(),
    )
    client = AsyncFindMyClient(account, session, SimpleNamespace(close=AsyncMock()))
    await client.unlock(RECORD, PASSCODE)
    assert client.can_resume_unlock(RECORD)
    account.adsid, account.dsid = "account-b", "account-b-dsid"
    assert not client.can_resume_unlock(RECORD)
    await client.unlock(RECORD, PASSCODE)
    assert session.recover.await_count == 2
    await client.close()


@pytest.mark.parametrize("code", [429, 500, 503])
async def test_srp_init_service_unavailability_is_transient_preproof(code):
    proxy, attempt, _ = proxy_for(AsyncMock(return_value=HttpResponse(code, b"private-server-body")))
    with pytest.raises(recovery.RecoveryProtocolError) as raised:
        await recovery.recover_bottled_peer(proxy, RECORD, PASSCODE)
    assert raised.value.reason == "transient" and raised.value.http_status == code
    assert raised.value.dispatch_state == "not_dispatched" and attempt.state == "ready"


async def test_headers_preserve_exact_structured_pet_error():
    proxy, attempt, _ = proxy_for()
    error = onboarding.RecoveryPETError("factor_required")
    proxy._headers = AsyncMock(side_effect=error)
    with pytest.raises(onboarding.RecoveryPETError) as raised:
        await recovery.recover_bottled_peer(proxy, RECORD, PASSCODE)
    assert raised.value is error and attempt.state == "ready"
    proxy._http.post.assert_not_awaited()
