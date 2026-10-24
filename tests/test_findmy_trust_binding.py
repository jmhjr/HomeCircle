"""Generated identities and real wire parsers test trust at the point of key use."""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from custom_components.homecircle._vendor_findmy.cloudkit.proto import (
    cloudkit_pb2 as ck,
    cuttlefish_pb2 as cf,
)
from custom_components.homecircle._vendor_findmy.keychain import bottle, join, peers, session, shares


def spki(key):
    return key.public_key().public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)


def identity(signing, encryption, *, claimed=None, invalid_signature=False):
    info = cf.PeerPermanentInfo(
        epoch=1, signing_key=spki(signing), encryption_key=spki(encryption),
        machine_id="synthetic-machine", model_id="Synthetic1,1", creation_time=1,
    ).SerializeToString()
    signature = signing.sign(join.TYPE_PERMANENT_INFO + info, ec.ECDSA(hashes.SHA384()))
    if invalid_signature:
        signature = b"invalid-permanent-signature"
    return cf.CuttlefishPeer(
        hash=claimed or peers.peer_identifier(info, signature),
        permanent_info=cf.SignedInfo(info=info, signature=signature),
    )


def record(fields, *, name="synthetic-record", parent=None):
    output = ck.Record()
    output.record_identifier.value.name = name
    for key, value in fields.items():
        field = output.record_field.add()
        field.identifier.name = key
        if isinstance(value, str):
            field.value.string_value = value
        elif isinstance(value, bytes):
            field.value.bytes_value = value
        else:
            field.value.signed_value = value
    if parent is not None:
        field = output.record_field.add()
        field.identifier.name = "parentkeyref"
        reference = ck.Reference()
        reference.record_identifier.value.name = parent
        field.value.reference_value = reference.SerializeToString()
    return output


def plaintext(*, uuid="synthetic-tlk", view="Manatee"):
    return cf.TlkKeyMaterial(
        uuid=uuid, zone_name=view, key_class="tlk", key=b"\x61" * 64,
    ).SerializeToString()


def signed_share(sender, signer, receiver_id, encryption, payload):
    raw = shares.ShareRecord(
        sender=sender, receiver=receiver_id,
        receiver_public_encryption_key=shares.public_point(encryption),
        wrapped_key=shares.archive_sfies(shares.sfies_encrypt(encryption.public_key(), payload)),
        signature=b"", curve=4, epoch=1, poisoned=0, version=0,
    )
    return replace(raw, signature=signer.sign(shares.share_signed_data(raw), ec.ECDSA(hashes.SHA256())))


def wire_share(raw, *, view="Manatee", tlk_uuid="synthetic-tlk", parent="synthetic-tlk"):
    raw_record = record({
        "sender": raw.sender, "receiver": raw.receiver,
        "receiverPublicEncryptionKey": raw.receiver_public_encryption_key,
        "wrappedkey": raw.wrapped_key, "signature": raw.signature,
        "curve": raw.curve, "epoch": raw.epoch,
        "poisoned": raw.poisoned, "version": raw.version,
    }, parent=parent)
    tlk = record({"class": "tlk", "uploadver": 1}, name=tlk_uuid)
    return cf.RecoverableTlkShare(
        service=view, share=cf.RecordWrapper(record=raw_record.SerializeToString()),
        viewkeys=cf.ViewKeySet(tlk=cf.RecordWrapper(record=tlk.SerializeToString())),
    ).SerializeToString()


class SyntheticTransport:
    """Exercise the production directory and share decoders, without any network."""

    def __init__(self, peer_list, entries):
        self.peer_list = peer_list
        self.entries = entries
        self.fetches = 0

    async def function_invoke(self, service, method, request):
        if method == "fetchChanges":
            response = cf.FetchChangesResponse()
            if not self.fetches:
                for peer in self.peer_list:
                    response.changes.changes.add().add.CopyFrom(peer)
            self.fetches += 1
            return response.SerializeToString()
        assert method == "fetchRecoverableTLKShares"
        return cf.FetchRecoverableTlkSharesResponse(shares=self.entries).SerializeToString()

    async def close(self):
        pass


async def key_use(peer_list, raw, receiver, **metadata):
    transport = SyntheticTransport(peer_list, [wire_share(raw, **metadata)])
    current = session.AsyncKeychainSession(
        SimpleNamespace(adsid="synthetic-account", dsid="synthetic-dsid"),
        transport, transport, transport, transport,
    )
    recipient = SimpleNamespace(
        peer_id="synthetic-receiver", encryption_key=lambda: receiver,
        signing_key=lambda: receiver,
    )
    try:
        return (await current.key_shares(recipient))[0]
    finally:
        await current.close()


@pytest.fixture
def crypto():
    signing = ec.generate_private_key(ec.SECP384R1())
    encryption = ec.generate_private_key(ec.SECP384R1())
    receiver = ec.generate_private_key(ec.SECP384R1())
    peer = identity(signing, encryption)
    raw = signed_share(peer.hash, signing, "synthetic-receiver", receiver, plaintext())
    return signing, encryption, receiver, peer, raw


async def test_real_directory_and_share_positive_control(crypto):
    _, _, receiver, peer, raw = crypto
    result = await key_use([peer], raw, receiver)
    assert result.sender_verified and result.plaintext == plaintext()
    assert result.key_id == "synthetic-tlk"
    assert result.view_keys.by_uuid == {"synthetic-tlk": b"\x61" * 64}


@pytest.mark.parametrize("mismatch", ["claimed_id", "self_signature", "signature_context"])
async def test_directory_identity_cannot_substitute_signing_key(crypto, mismatch):
    _, _, receiver, peer, _ = crypto
    attacker = ec.generate_private_key(ec.SECP384R1())
    forged = identity(
        attacker, receiver,
        claimed=peer.hash if mismatch == "claimed_id" else None,
        invalid_signature=mismatch == "self_signature",
    )
    if mismatch == "signature_context":
        forged.permanent_info.signature = attacker.sign(
            join.TYPE_STABLE_INFO + forged.permanent_info.info, ec.ECDSA(hashes.SHA384())
        )
        forged.hash = peers.peer_identifier(forged.permanent_info.info, forged.permanent_info.signature)
    raw = signed_share(forged.hash, attacker, "synthetic-receiver", receiver, plaintext())
    result = await key_use([forged], raw, receiver)
    assert not result.sender_known and not result.sender_verified
    assert result.error and result.plaintext is None and not result.view_keys


@pytest.mark.parametrize("mismatch", ["view", "wrapper_uuid", "share_uuid", "missing_uuid", "missing_view"])
async def test_authenticated_tlk_metadata_must_match_key_use(crypto, mismatch):
    signing, _, receiver, peer, _ = crypto
    payload = plaintext(
        view="Passwords" if mismatch == "view" else "" if mismatch == "missing_view" else "Manatee",
        uuid="" if mismatch == "missing_uuid" else "synthetic-tlk",
    )
    raw = signed_share(peer.hash, signing, "synthetic-receiver", receiver, payload)
    result = await key_use(
        [peer], raw, receiver,
        tlk_uuid="unsigned-alias" if mismatch == "wrapper_uuid" else "synthetic-tlk",
        parent="unsigned-alias" if mismatch == "share_uuid" else "synthetic-tlk",
    )
    assert result.sender_verified
    assert result.error and result.plaintext is None and not result.view_keys


def test_diagnostic_keyring_cannot_alias_authenticated_uuid():
    wrapper = shares.ViewKey("tlk", b"", 1, uuid="unsigned-alias", slot="tlk")
    ring = shares.unwrap_view_keys([wrapper], plaintext())
    assert ring.by_uuid == {"synthetic-tlk": b"\x61" * 64}


async def test_valid_signature_with_wrong_receiver_is_rejected(crypto):
    signing, _, receiver, peer, _ = crypto
    raw = signed_share(peer.hash, signing, "different-receiver", receiver, plaintext())
    result = await key_use([peer], raw, receiver)
    assert result.sender_verified and result.plaintext is None and result.error


async def test_unsigned_receiver_public_key_is_only_a_hint(crypto):
    _, encryption, receiver, peer, raw = crypto
    raw = replace(raw, receiver_public_encryption_key=shares.public_point(encryption))
    result = await key_use([peer], raw, receiver)
    assert result.sender_verified and result.plaintext == plaintext()


def sealed(crypto):
    signing, encryption, _, peer, _ = crypto
    created = bottle.seal_bottle(
        peer_id=peer.hash, signing_key=signing, encryption_key=encryption,
        entropy=b"\x71" * 72, adsid="synthetic-account", bottle_id="synthetic-bottle",
    )
    keys = bottle.derive_bottle_keys(created.entropy, "synthetic-account")
    return created.bottle, keys, peers._peer_from_proto(peer)


@pytest.mark.parametrize("field", ["peer_signing_key", "peer_encryption_key"])
def test_bottle_rejects_signed_public_keys_that_disagree_with_private_keys(crypto, field):
    signing, _, receiver, _, _ = crypto
    wrapped, keys, sponsor = sealed(crypto)
    inner = cf.OTBottle.FromString(wrapped.bottle)
    setattr(inner, field, spki(receiver))
    wrapped.bottle = inner.SerializeToString()
    wrapped.escrowed_key_signature = keys.signing.sign(wrapped.bottle, ec.ECDSA(hashes.SHA384()))
    wrapped.peer_key_signature = signing.sign(wrapped.bottle, ec.ECDSA(hashes.SHA384()))
    with pytest.raises(bottle.BottleError, match="public keys"):
        bottle.open_bottle(wrapped, keys, sponsor=sponsor, require_signatures=True)


@pytest.mark.parametrize("field", ["signing_key", "encryption_key"])
def test_bottle_rejects_valid_ciphertext_containing_wrong_private_key(crypto, field):
    signing, encryption, receiver, _, _ = crypto
    wrapped, keys, sponsor = sealed(crypto)
    inner = cf.OTBottle.FromString(wrapped.bottle)
    contents = cf.OTInternalBottle(
        signing_key=cf.OTPrivateKey(key_type=1, key_data=bottle.peer_key_material(signing)),
        encryption_key=cf.OTPrivateKey(key_type=1, key_data=bottle.peer_key_material(encryption)),
    )
    getattr(contents, field).key_data = bottle.peer_key_material(receiver)
    encryptor = Cipher(algorithms.AES(keys.symmetric), modes.GCM(b"\x81" * 32)).encryptor()
    inner.ciphertext.ciphertext = encryptor.update(contents.SerializeToString()) + encryptor.finalize()
    inner.ciphertext.authentication_code = encryptor.tag
    inner.ciphertext.initialization_vector = b"\x81" * 32
    wrapped.bottle = inner.SerializeToString()
    wrapped.escrowed_key_signature = keys.signing.sign(wrapped.bottle, ec.ECDSA(hashes.SHA384()))
    wrapped.peer_key_signature = signing.sign(wrapped.bottle, ec.ECDSA(hashes.SHA384()))
    with pytest.raises(bottle.BottleError, match="public keys"):
        bottle.open_bottle(wrapped, keys, sponsor=sponsor, require_signatures=True)


def test_known_sponsor_encryption_key_must_match(crypto):
    _, _, receiver, _, _ = crypto
    wrapped, keys, sponsor = sealed(crypto)
    sponsor = replace(sponsor, encryption_key=spki(receiver))
    with pytest.raises(bottle.BottleError, match="directory peer"):
        bottle.open_bottle(wrapped, keys, sponsor=sponsor, require_signatures=True)


def test_account_salt_cannot_substitute_another_accounts_bottle(crypto):
    wrapped, _, _ = sealed(crypto)
    inner = cf.OTBottle.FromString(wrapped.bottle)
    with pytest.raises(bottle.BottleError, match="candidate salt"):
        bottle.find_bottle_keys(
            b"\x71" * 72, ["different-account", "different-dsid"],
            inner.escrowed_signing_key, inner.escrowed_encryption_key,
        )
