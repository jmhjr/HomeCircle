"""Generated crypto material exercises actual recovery trust and local CPU limits."""

import asyncio
from dataclasses import replace
import hashlib
import plistlib
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from custom_components.homecircle._vendor_findmy.cloudkit.proto import (
    cuttlefish_pb2 as cf,
)
from custom_components.homecircle._vendor_findmy.keychain import (
    bottle,
    recovery,
    session,
    shares,
)
from custom_components.homecircle._vendor_findmy.keychain.escrow import (
    build_keyvault_message,
)
from custom_components.homecircle._vendor_findmy.keychain.peers import (
    Peer,
    PeerDirectory,
)
from tests.test_findmy_recovery_protocol import PASSCODE, RECORD, actual_srp_proxy


def peer_for(signing, encryption, identifier="synthetic-peer"):
    def public(key):
        return key.public_key().public_bytes(
            Encoding.DER, PublicFormat.SubjectPublicKeyInfo
        )

    return Peer(
        hash=identifier,
        signing_key=public(signing),
        encryption_key=public(encryption),
        machine_id="synthetic-machine",
        model_id="synthetic-model",
    )


@pytest.fixture
def sealed_bottle():
    signing = ec.generate_private_key(ec.SECP384R1())
    encryption = ec.generate_private_key(ec.SECP384R1())
    created = bottle.seal_bottle(
        peer_id="synthetic-peer",
        signing_key=signing,
        encryption_key=encryption,
        entropy=b"\x11" * 72,
        adsid="synthetic-adsid",
        bottle_id="synthetic-bottle",
    )
    return created, signing, encryption, peer_for(signing, encryption)


def recovered_session(created, sponsor):
    current = session.AsyncKeychainSession.__new__(session.AsyncKeychainSession)
    current._account = SimpleNamespace(
        adsid="synthetic-adsid", dsid="synthetic-dsid", _recovery_diagnostics={}
    )
    current._bottles = SimpleNamespace(
        entries=[SimpleNamespace(id=created.bottle_id, bottle=created.bottle)]
    )
    current.peer_directory = AsyncMock(
        return_value=PeerDirectory({sponsor.hash: sponsor} if sponsor else {})
    )
    record = SimpleNamespace(label=created.bottle_id, peer_id="synthetic-peer")
    material = plistlib.dumps({session.ENTROPY_FIELD: created.entropy})
    return current, record, material


@pytest.mark.parametrize("signature", ["escrowed_key_signature", "peer_key_signature"])
@pytest.mark.parametrize("bad", [b"", b"synthetic-invalid-signature"])
async def test_actual_recovery_rejects_missing_or_invalid_signatures(
    sealed_bottle, signature, bad
):
    created, _, _, sponsor = sealed_bottle
    setattr(created.bottle, signature, bad)
    current, record, material = recovered_session(created, sponsor)
    with pytest.raises(bottle.BottleError, match="signature"):
        await current._recovered_material(record, material)


async def test_valid_bottle_and_departed_sponsor_fallback_remain_distinct(
    sealed_bottle,
):
    created, _, _, sponsor = sealed_bottle
    current, record, material = recovered_session(created, sponsor)
    recovered = await current._recovered_material(record, material)
    assert recovered.bottle.escrowed_key_verified and recovered.bottle.sponsor_verified
    current, record, material = recovered_session(created, None)
    recovered = await current._recovered_material(record, material)
    assert recovered.bottle.escrowed_key_verified
    assert not recovered.bottle.sponsor_known and not recovered.bottle.sponsor_verified
    assert recovered.bottle.peer_key_verified
    created.bottle.peer_key_signature = b"unverifiable departed sponsor signature"
    with pytest.raises(bottle.BottleError, match="signature"):
        await current._recovered_material(record, material)


def test_diagnostic_bottle_helper_can_still_report_failed_signatures(sealed_bottle):
    created, _, _, sponsor = sealed_bottle
    created.bottle.escrowed_key_signature = b"invalid"
    keys = bottle.derive_bottle_keys(created.entropy, "synthetic-adsid")
    opened = bottle.open_bottle(created.bottle, keys, sponsor=sponsor)
    assert not opened.escrowed_key_verified and opened.sponsor_verified


@pytest.mark.parametrize("length", [0, 1, 4, 12, 15, 17])
async def test_bottle_requires_full_tag_even_when_new_outer_signatures_are_valid(
    sealed_bottle, length
):
    created, signing, _, sponsor = sealed_bottle
    keys = bottle.derive_bottle_keys(created.entropy, "synthetic-adsid")
    inner = cf.OTBottle.FromString(created.bottle.bottle)
    original = inner.ciphertext.authentication_code
    inner.ciphertext.authentication_code = (
        original[:length] if length <= 16 else original + b"x"
    )
    created.bottle.bottle = inner.SerializeToString()
    created.bottle.escrowed_key_signature = keys.signing.sign(
        created.bottle.bottle, ec.ECDSA(hashes.SHA384())
    )
    created.bottle.peer_key_signature = signing.sign(
        created.bottle.bottle, ec.ECDSA(hashes.SHA384())
    )
    current, record, material = recovered_session(created, sponsor)
    with pytest.raises(bottle.BottleError, match="tag"):
        await current._recovered_material(record, material)


def share_material(*, invalid=False):
    sender = ec.generate_private_key(ec.SECP384R1())
    receiver = ec.generate_private_key(ec.SECP384R1())
    plaintext = cf.TlkKeyMaterial(
        uuid="synthetic-view-key", zone_name="Manatee", key=b"\x22" * 32
    ).SerializeToString()
    wrapped = shares.archive_sfies(
        shares.sfies_encrypt(receiver.public_key(), plaintext)
    )
    record = shares.ShareRecord(
        sender="synthetic-sender",
        receiver="synthetic-receiver",
        receiver_public_encryption_key=shares.public_point(receiver),
        wrapped_key=wrapped,
        signature=b"",
        curve=384,
        epoch=0,
        poisoned=0,
        version=1,
    )
    record = replace(
        record,
        signature=b"invalid"
        if invalid
        else sender.sign(shares.share_signed_data(record), ec.ECDSA(hashes.SHA256())),
    )
    peer = peer_for(sender, receiver, "synthetic-sender")
    return (
        shares.ShareEntry(view="Manatee", share=record, view_keys=[]),
        receiver,
        plaintext,
        peer,
    )


@pytest.mark.parametrize(
    "directory_kind",
    ["invalid_signature", "missing_signature", "empty", "unknown_sender"],
)
async def test_actual_key_use_rejects_unverified_shares(monkeypatch, directory_kind):
    entry, receiver, _, sender = share_material(
        invalid=directory_kind == "invalid_signature"
    )
    if directory_kind == "missing_signature":
        entry = replace(entry, share=replace(entry.share, signature=b""))
    directory = PeerDirectory({sender.hash: sender})
    if directory_kind == "empty":
        directory = PeerDirectory()
    elif directory_kind == "unknown_sender":
        directory = PeerDirectory({"different-sender": sender})
    current = session.AsyncKeychainSession.__new__(session.AsyncKeychainSession)
    current._cuttlefish = object()
    current.peer_directory = AsyncMock(return_value=directory)
    monkeypatch.setattr(
        session, "fetch_recoverable_shares", AsyncMock(return_value=[entry])
    )
    decrypt = Mock(
        side_effect=AssertionError("Unverified shares must not reach decryption")
    )
    monkeypatch.setattr(shares, "sfies_decrypt_archive", decrypt)
    peer = SimpleNamespace(
        peer_id="synthetic-receiver",
        encryption_key=lambda: receiver,
        signing_key=lambda: receiver,
    )
    result = (await current.key_shares(peer))[0]
    assert result.error and result.plaintext is None and not result.view_keys
    decrypt.assert_not_called()


async def test_valid_signed_share_yields_key_and_diagnostic_mode_is_preserved(
    monkeypatch,
):
    entry, receiver, plaintext, sender = share_material()
    directory = PeerDirectory({sender.hash: sender})
    current = session.AsyncKeychainSession.__new__(session.AsyncKeychainSession)
    current._cuttlefish = object()
    current.peer_directory = AsyncMock(return_value=directory)
    monkeypatch.setattr(
        session, "fetch_recoverable_shares", AsyncMock(return_value=[entry])
    )
    peer = SimpleNamespace(
        peer_id="synthetic-receiver",
        encryption_key=lambda: receiver,
        signing_key=lambda: receiver,
    )
    result = (await current.key_shares(peer))[0]
    assert result.sender_verified and result.plaintext == plaintext
    assert result.view_keys.get("synthetic-view-key") == b"\x22" * 32
    invalid = replace(entry, share=replace(entry.share, signature=b"invalid"))
    diagnostic = shares.unwrap_share(
        invalid, receiver, directory, expected_receiver=peer.peer_id
    )
    assert diagnostic.plaintext == plaintext and not diagnostic.sender_verified


def inner_blob(
    iterations=10000,
    *,
    salt=b"\x33" * 64,
    plaintext=b"synthetic recovered material",
    encrypted=None,
):
    if encrypted is None:
        derived = hashlib.pbkdf2_hmac("sha256", PASSCODE.encode(), salt, iterations, 16)
        padder = padding.PKCS7(128).padder()
        encryptor = Cipher(algorithms.AES(derived), modes.CBC(salt[:16])).encryptor()
        encrypted = (
            encryptor.update(padder.update(plaintext) + padder.finalize())
            + encryptor.finalize()
        )
    header = b"\0" * 8 + iterations.to_bytes(4, "big") + b"\0" * 4
    return build_keyvault_message(header, [b"", salt, b"", encrypted, b"", b""])


def test_inner_blob_keeps_writer_10000_iteration_cbc_format():
    assert (
        recovery.unwrap_inner_blob(inner_blob(), PASSCODE)
        == b"synthetic recovered material"
    )


@pytest.mark.parametrize("iterations", [0, 1000001, 2**32 - 1])
def test_untrusted_iteration_count_rejected_before_pbkdf(monkeypatch, iterations):
    blob = inner_blob(iterations, encrypted=b"\0" * 16)
    derive = Mock(
        side_effect=AssertionError("PBKDF2 must not run for an unsupported work factor")
    )
    monkeypatch.setattr(recovery.hashlib, "pbkdf2_hmac", derive)
    with pytest.raises(recovery.RecoveryError, match="iterations"):
        recovery.unwrap_inner_blob(blob, PASSCODE)
    derive.assert_not_called()


def test_local_work_ceiling_accepts_its_boundary_without_changing_the_count(
    monkeypatch,
):
    known_key = b"\x44" * 16
    plaintext = b"synthetic boundary material"
    salt = b"\x33" * 64
    padder = padding.PKCS7(128).padder()
    encryptor = Cipher(algorithms.AES(known_key), modes.CBC(salt[:16])).encryptor()
    ciphertext = (
        encryptor.update(padder.update(plaintext) + padder.finalize())
        + encryptor.finalize()
    )
    derive = Mock(return_value=known_key)
    monkeypatch.setattr(recovery.hashlib, "pbkdf2_hmac", derive)
    assert (
        recovery.unwrap_inner_blob(inner_blob(1000000, encrypted=ciphertext), PASSCODE)
        == plaintext
    )
    assert derive.call_args.args[3] == 1000000


@pytest.mark.parametrize(
    "salt,ciphertext",
    [(b"short", b"\0" * 16), (b"\x33" * 64, b""), (b"\x33" * 64, b"\0" * 17)],
)
def test_invalid_cbc_parameters_are_rejected_before_key_derivation(
    monkeypatch, salt, ciphertext
):
    derive = Mock(
        side_effect=AssertionError("Malformed CBC input must not invoke PBKDF2")
    )
    monkeypatch.setattr(recovery.hashlib, "pbkdf2_hmac", derive)
    with pytest.raises(recovery.RecoveryError, match="CBC parameters"):
        recovery.unwrap_inner_blob(
            inner_blob(salt=salt, encrypted=ciphertext), PASSCODE
        )
    derive.assert_not_called()


async def test_actual_authenticated_recovery_derives_off_loop(monkeypatch):
    proxy, attempt, _ = actual_srp_proxy()
    blob = inner_blob()
    monkeypatch.setattr(recovery, "unwrap_outer_blob", lambda *args, **kwargs: blob)
    original = recovery.hashlib.pbkdf2_hmac
    threads = []

    def derive(*args):
        threads.append(threading.get_ident())
        return original(*args)

    monkeypatch.setattr(recovery.hashlib, "pbkdf2_hmac", derive)
    loop_thread = threading.get_ident()
    assert (
        await recovery.recover_bottled_peer(proxy, RECORD, PASSCODE)
        == b"synthetic recovered material"
    )
    assert (
        attempt.state == "verified"
        and threads
        and all(value != loop_thread for value in threads)
    )


@pytest.mark.parametrize("worker_fails", [False, True])
async def test_cancellation_during_local_work_keeps_verified_guard_and_never_retries(
    monkeypatch,
    worker_fails,
):
    proxy, attempt, events = actual_srp_proxy()
    blob = inner_blob()
    monkeypatch.setattr(recovery, "unwrap_outer_blob", lambda *args, **kwargs: blob)
    loop = asyncio.get_running_loop()
    entered, finished = asyncio.Event(), asyncio.Event()
    release = threading.Event()
    original = recovery.hashlib.pbkdf2_hmac

    def derive(*args):
        loop.call_soon_threadsafe(entered.set)
        try:
            assert release.wait(3)
            if worker_fails:
                raise ValueError("synthetic local derivation failure")
            return original(*args)
        finally:
            loop.call_soon_threadsafe(finished.set)

    monkeypatch.setattr(recovery.hashlib, "pbkdf2_hmac", derive)
    task = asyncio.create_task(recovery.recover_bottled_peer(proxy, RECORD, PASSCODE))
    try:
        await asyncio.wait_for(entered.wait(), 2)
        assert attempt.state == "verified"
        task.cancel("synthetic cancellation reason")
        await asyncio.sleep(0)
        assert not task.done()
        release.set()
        with pytest.raises(
            asyncio.CancelledError, match="synthetic cancellation reason"
        ):
            await task
        assert (
            events.count("reserved") == 1
            and events.count("server_verified_client") == 1
        )
    finally:
        release.set()
        await asyncio.wait_for(finished.wait(), 2)


def local_session(clients):
    return session.AsyncKeychainSession(SimpleNamespace(), *clients)


async def test_session_close_attempts_all_clients_and_preserves_first_error():
    failure = ValueError("synthetic close failure")
    clients = [
        SimpleNamespace(close=AsyncMock(side_effect=failure if index == 3 else None))
        for index in range(4)
    ]
    current = local_session(clients)
    with pytest.raises(ValueError) as raised:
        await current.close()
    assert raised.value is failure
    for client in clients:
        client.close.assert_awaited_once()
    assert not current._closed
    clients[-1].close.side_effect = None
    await current.close()
    assert current._closed
    for client in clients:
        assert client.close.await_count == 2
    await current.close()
    for client in clients:
        assert client.close.await_count == 2


async def test_cancelled_close_finishes_sibling_cleanup_then_preserves_cancellation():
    entered, release = asyncio.Event(), asyncio.Event()

    async def blocked():
        entered.set()
        await release.wait()

    clients = [SimpleNamespace(close=AsyncMock()) for _ in range(4)]
    clients[-1].close.side_effect = blocked
    current = local_session(clients)
    task = asyncio.create_task(current.close())
    await entered.wait()
    task.cancel("synthetic cancellation reason")
    await asyncio.sleep(0)
    try:
        assert not task.done()
    finally:
        release.set()
    with pytest.raises(asyncio.CancelledError, match="synthetic cancellation reason"):
        await task
    for client in clients:
        client.close.assert_awaited_once()
    assert not current._closed
    await current.close()
    assert current._closed


@pytest.mark.parametrize(
    "failure", [RuntimeError("synthetic bootstrap failure"), asyncio.CancelledError()]
)
async def test_failed_open_closes_all_transports_without_masking_original(
    monkeypatch, failure
):
    clients = [
        SimpleNamespace(
            close=AsyncMock(
                side_effect=ValueError("synthetic cleanup failure")
                if index == 0
                else None
            )
        )
        for index in range(3)
    ]
    clients[0].open_container = AsyncMock(side_effect=failure)
    monkeypatch.setattr(session, "AsyncCloudKitClient", lambda account: clients[0])
    monkeypatch.setattr(session, "make_cuttlefish_client", lambda account: clients[1])
    monkeypatch.setattr(session, "make_securityd_client", lambda account: clients[2])
    with pytest.raises(type(failure)) as raised:
        await session.AsyncKeychainSession.open(SimpleNamespace())
    assert raised.value is failure
    for client in clients:
        client.close.assert_awaited_once()
