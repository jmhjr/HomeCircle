"""Generated PCS controls; no account state, network or Apple-format acceptance proof.

The independent fixture writer follows the producer/consumer distinction in
OpenBubbles/rustpush b3c96c23e1aae78d1229ebaccb12027624f1eaff,
src/icloud/pcs.rs: raw key for inner signatures; derived key for shared fields,
meta and full SHA-256 HMAC; field header selects among current and extra keys.
"""

from dataclasses import replace
import hashlib
import hmac
import logging
import struct
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.keywrap import aes_key_wrap
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from custom_components.homecircle._vendor_findmy.cloudkit import pcs


def tlv(tag, body):
    if len(body) < 128:
        length = bytes([len(body)])
    else:
        encoded = len(body).to_bytes((len(body).bit_length() + 7) // 8, "big")
        length = bytes([0x80 | len(encoded)]) + encoded
    return bytes([tag]) + length + body


def sequence(*members):
    return tlv(0x30, b"".join(members))


def octets(value):
    return tlv(4, value)


def integer(value):
    return tlv(2, bytes([value]))


def kdf(key, label):
    return hmac.digest(key, struct.pack(">I", 1) + label + b"\0\0\0\0\x80", "sha256")[:16]


def key_id(key):
    return hmac.digest(kdf(key, b"master key id labell"), b"M key input data 2 u", "sha256")


def seal_field(key, plaintext, context=b""):
    identifier = key_id(key)
    header = b"\x03" + identifier[:2] + b"\x02" + identifier[2:4]
    iv = b"\x21" * 12
    encryptor = Cipher(algorithms.AES(kdf(key, b"encryption key key m")), modes.GCM(iv)).encryptor()
    encryptor.authenticate_additional_data(header + context)
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    return header + iv + encryptor.tag[:12] + ciphertext


def signed_fixture(
    *, version=5, read_only=False, extra_keys=(), valid_signature=True,
    receiver=None, raw_key=b"\x42" * 16, outer_signature=None, owner_review=False,
    inner_digest=1, additional_receivers=(), outer_signer=None,
):
    field_key = raw_key if version == 5 else kdf(raw_key, b"MsaeEooevaX fooo 012")
    if receiver is None:
        receiver = ec.generate_private_key(ec.SECP256R1())
    wrapped_key = field_key if read_only else raw_key
    frame = b"\x01" + wrapped_key + sum(wrapped_key).to_bytes(2, "big") + b"\x05" * 5
    rfc6637 = (
        b"\x08\x2a\x86\x48\xce\x3d\x03\x01\x07\x12\x03\x01\x08\x07"
        + b"Anonymous Sender    " + b"fingerprint".ljust(20, b"\0")
    )
    def wrapped_recipient(recipient):
        ephemeral = ec.generate_private_key(ec.SECP256R1())
        shared = ephemeral.exchange(ec.ECDH(), recipient.public_key())
        kek = hashlib.sha256(b"\0\0\0\x01" + shared + rfc6637).digest()[:16]
        wrapped = aes_key_wrap(kek, frame)
        ephemeral_x = ephemeral.public_key().public_numbers().x.to_bytes(32, "big")
        wire_wrapped = b"\x01\x00" + ephemeral_x + bytes([len(wrapped)]) + wrapped
        recipient_public = recipient.public_key().public_bytes(Encoding.X962, PublicFormat.CompressedPoint)
        return sequence(
            sequence(integer(3), octets(recipient_public)), octets(wire_wrapped),
            *([integer(1)] if read_only else []),
        )

    shares = sorted(wrapped_recipient(key) for key in [receiver, *additional_receivers])
    keyset = sequence(integer(0), tlv(0x31, b"".join(shares)))
    meta_members = [tlv(0xA1, sequence(integer(0), octets(b"")))]
    if extra_keys:
        meta_members.insert(0, tlv(0xA0, tlv(0x31, b"".join(sorted(octets(key) for key in extra_keys)))))
    meta = seal_field(field_key, sequence(*meta_members))

    # PBKDF output is consumed little-endian, then reduced to P-256 as in the producer.
    order = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
    scalar = int.from_bytes(hashlib.pbkdf2_hmac("sha256", raw_key, b"full master key", 10, 128)[:32], "little")
    if scalar > order:
        scalar -= order
    signing = ec.derive_private_key(scalar, ec.SECP256R1())
    public = signing.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    outer_type = 3 if outer_signature is not None else 0
    signed = keyset + meta + struct.pack(">IIII", outer_type, 1, len(extra_keys), 1) + public
    signature = signing.sign(signed, ec.ECDSA(hashes.SHA256())) if valid_signature else b"invalid"
    object_signature = sequence(
        integer(1), integer(outer_type), sequence(integer(1), octets(public)),
        sequence(octets(b""), integer(inner_digest), octets(signature)),
        *([tlv(0xA0, integer(len(extra_keys)))] if extra_keys else []),
    )
    mac = hmac.digest(kdf(field_key, b"hmackey-of-masterkey"), keyset + meta + object_signature, "sha256")
    def external_signature(signer, *, digest=1, invalid=False):
        signer_public = signer.public_key().public_bytes(Encoding.X962, PublicFormat.CompressedPoint)
        value = b"invalid" if invalid else signer.sign(signed, ec.ECDSA(hashes.SHA256()))
        return sequence(octets(signer_public), integer(digest), octets(value))

    optional = []
    if outer_signature is not None:
        if outer_signature == "unknown":
            outer_signer = ec.generate_private_key(ec.SECP256R1())
        elif outer_signer is None:
            outer_signer = receiver
        outer = external_signature(
            outer_signer, digest=2 if outer_signature == "unsupported_digest" else 1,
            invalid=outer_signature == "invalid",
        )
        optional.append(tlv(0xA3, outer))
    if owner_review:
        owner_signer = ec.generate_private_key(ec.SECP256R1())
        review = external_signature(owner_signer)
        optional.append(tlv(0xA4, sequence(sequence(integer(7), octets(review)))))
    encoded = tlv(0x61, sequence(
        keyset, tlv(0xA0, octets(meta)),
        tlv(0xA1, sequence(integer(version), octets(object_signature))),
        octets(mac), tlv(0xA2, octets(key_id(field_key)[:4])),
        *optional,
    ))
    return SimpleNamespace(
        protection=pcs.ShareProtection.from_der(encoded), encoded=encoded,
        receiver=receiver, raw_key=raw_key, field_key=field_key,
        outer_signer=outer_signer if outer_signature is not None else None,
    )


@pytest.mark.parametrize(("version", "read_only"), [(5, False), (4, False), (4, True)])
def test_strict_unwrap_accepts_generated_current_shared_and_read_only_controls(version, read_only):
    control = signed_fixture(version=version, read_only=read_only)
    opened = pcs.unwrap_protection(control.protection, [control.receiver], require_hmac=True, require_signature=True)
    assert opened.master_key == control.field_key
    assert opened.hmac_verified
    assert opened.signature_verified is (None if read_only else True)


@pytest.mark.parametrize("length", [0, 1, 12, 31, 33, 64])
def test_hmac_requires_full_sha256_length(length):
    control = signed_fixture()
    mac = (control.protection.hmac + b"\0" * 32)[:length]
    protection = replace(control.protection, hmac=mac)
    assert not pcs.verify_protection_hmac(protection, control.field_key)
    with pytest.raises(pcs.PCSError, match="HMAC"):
        pcs.unwrap_protection(protection, [control.receiver], require_hmac=True)


@pytest.mark.parametrize("version", [4, 5])
def test_valid_hmac_does_not_replace_inner_signature_check(version):
    control = signed_fixture(version=version, valid_signature=False)
    assert pcs.verify_protection_hmac(control.protection, control.field_key)
    with pytest.raises(pcs.PCSError, match="signature"):
        pcs.unwrap_protection(control.protection, [control.receiver], require_hmac=True, require_signature=True)


@pytest.mark.parametrize("unwrap", [pcs.unwrap_zone, pcs.unwrap_zone_record_defaults])
@pytest.mark.parametrize("version", [4, 5])
def test_actual_zone_key_use_accepts_generated_signed_controls(unwrap, version):
    control = signed_fixture(version=version)
    assert unwrap(control.encoded, [control.receiver])


@pytest.mark.parametrize("unwrap", [pcs.unwrap_zone, pcs.unwrap_zone_record_defaults])
def test_actual_zone_key_use_rejects_invalid_signature_with_valid_hmac(unwrap):
    control = signed_fixture(valid_signature=False)
    with pytest.raises(pcs.PCSError, match="signature"):
        unwrap(control.encoded, [control.receiver])


@pytest.mark.parametrize("unwrap", [pcs.unwrap_zone, pcs.unwrap_zone_record_defaults])
def test_actual_zone_key_use_requires_hmac(unwrap):
    control = signed_fixture()
    damaged = control.encoded.replace(control.protection.hmac, b"\0" * 32)
    with pytest.raises(pcs.PCSError, match="HMAC"):
        unwrap(damaged, [control.receiver])


def test_field_header_selects_authenticated_extra_symmetric_key():
    old_key = b"\x73" * 16
    control = signed_fixture(extra_keys=[old_key])
    opened = pcs.unwrap_protection(control.protection, [control.receiver], require_hmac=True, require_signature=True)
    assert opened.meta.symmetric_keys == [old_key]
    context = pcs.FieldContext("synthetic-zone", "synthetic-record", "value")
    field = seal_field(old_key, b"synthetic-old-key-value", context.as_bytes())
    assert pcs.decrypt_field(field, opened, context) == b"synthetic-old-key-value"
    with pytest.raises(pcs.PCSError, match="authenticate"):
        pcs.decrypt_field(field, opened, pcs.FieldContext("synthetic-zone", "other-record", "value"))


def test_unknown_field_key_does_not_fall_back_to_current_key():
    control = signed_fixture()
    opened = pcs.unwrap_protection(control.protection, [control.receiver], require_hmac=True, require_signature=True)
    field = seal_field(b"\x74" * 16, b"synthetic-other-key-value")
    with pytest.raises(pcs.PCSError, match="none of the keys"):
        pcs.decrypt_field(field, opened, pcs.FieldContext.none())


@pytest.mark.parametrize(("version", "read_only"), [(5, False), (4, False), (4, True)])
def test_strict_unwrap_accepts_outer_signature_from_matched_local_key(version, read_only):
    control = signed_fixture(version=version, read_only=read_only, outer_signature="valid")
    assert pcs.describe_outer_protection_signature(control.protection, control.receiver.public_key()) is None
    opened = pcs.unwrap_protection(control.protection, [control.receiver], require_hmac=True, require_signature=True)
    assert opened.master_key == control.field_key


@pytest.mark.parametrize("outer_signature", ["invalid", "unknown", "unsupported_digest"])
@pytest.mark.parametrize("read_only", [False, True])
def test_strict_unwrap_rejects_bad_or_unknown_outer_signature_even_with_valid_inner_hmac(outer_signature, read_only):
    control = signed_fixture(version=4, read_only=read_only, outer_signature=outer_signature)
    assert pcs.verify_protection_hmac(control.protection, control.field_key)
    if not read_only:
        assert pcs.verify_protection_signature(control.protection, control.raw_key)
    with pytest.raises(pcs.PCSError, match="outer authentication"):
        pcs.unwrap_protection(control.protection, [control.receiver], require_hmac=True, require_signature=True)


@pytest.mark.parametrize("unwrap", [pcs.unwrap_zone, pcs.unwrap_zone_record_defaults])
@pytest.mark.parametrize("outer_signature", [None, "valid"])
def test_actual_zone_use_accepts_optional_outer_signature(unwrap, outer_signature):
    control = signed_fixture(outer_signature=outer_signature)
    assert unwrap(control.encoded, [control.receiver])


@pytest.mark.parametrize("unwrap", [pcs.unwrap_zone, pcs.unwrap_zone_record_defaults])
@pytest.mark.parametrize("outer_signature", ["invalid", "unknown", "unsupported_digest"])
def test_actual_zone_use_rejects_unverified_supplied_outer_signature(unwrap, outer_signature):
    control = signed_fixture(outer_signature=outer_signature)
    with pytest.raises(pcs.PCSError, match="outer authentication"):
        unwrap(control.encoded, [control.receiver])


@pytest.mark.parametrize("unwrap", [pcs.unwrap_zone, pcs.unwrap_zone_record_defaults])
@pytest.mark.parametrize("outer_signature", [None, "valid"])
def test_actual_zone_use_rejects_owner_review_without_distinct_trusted_context(unwrap, outer_signature):
    control = signed_fixture(outer_signature=outer_signature, owner_review=True)
    assert pcs.verify_protection_hmac(control.protection, control.field_key)
    with pytest.raises(pcs.PCSError, match="separate trusted signer context"):
        unwrap(control.encoded, [control.receiver])


def test_diagnostic_unwrap_can_report_outer_failure_without_enforcing_it(caplog, monkeypatch):
    monkeypatch.setattr(pcs.logger, "disabled", False)
    monkeypatch.setattr(pcs.logger, "handlers", [caplog.handler])
    caplog.set_level(logging.WARNING, logger=pcs.__name__)
    control = signed_fixture(outer_signature="invalid")
    opened = pcs.unwrap_protection(control.protection, [control.receiver])
    assert opened.hmac_verified and opened.signature_verified
    assert "outer authentication was not confirmed" in caplog.text


def test_unknown_outer_signer_is_not_trusted_because_record_names_it():
    control = signed_fixture(outer_signature="unknown")
    assert control.protection.signature.key_id
    with pytest.raises(pcs.PCSError, match="other than the matched local key"):
        pcs.unwrap_protection(control.protection, [control.receiver], require_signature=True)


def test_outer_signer_does_not_fall_back_to_unrelated_supplied_local_key():
    control = signed_fixture(outer_signature="unknown")
    with pytest.raises(pcs.PCSError, match="other than the matched local key"):
        pcs.unwrap_protection(control.protection, [control.receiver, control.outer_signer], require_signature=True)


def test_strict_unwrap_rejects_unsupported_inner_digest_even_with_valid_hmac():
    control = signed_fixture(inner_digest=2)
    assert pcs.verify_protection_hmac(control.protection, control.field_key)
    with pytest.raises(pcs.PCSError, match="signature was not confirmed"):
        pcs.unwrap_protection(control.protection, [control.receiver], require_hmac=True, require_signature=True)


def multi_recipient_fixture(*, version=5, read_only=False):
    def compressed(key):
        return key.public_key().public_bytes(Encoding.X962, PublicFormat.CompressedPoint)

    first, signer = sorted(
        [ec.generate_private_key(ec.SECP256R1()), ec.generate_private_key(ec.SECP256R1())],
        key=compressed,
    )
    control = signed_fixture(
        version=version, read_only=read_only, receiver=first,
        additional_receivers=[signer], outer_signature="valid", outer_signer=signer,
    )
    # The independently written keyset is a canonical DER SET, with the nonsigner
    # recipient first. Success therefore cannot depend on which recipient was first.
    keyset, _ = pcs.der.parse_one(control.protection.keyset_der)
    entries = [entry.raw for entry in keyset.children()[1].children()]
    assert entries == sorted(entries)
    assert control.protection.keys[0].public_key == compressed(first)
    assert control.protection.keys[1].public_key == compressed(signer)
    return control, first, signer


@pytest.mark.parametrize(("version", "read_only"), [(5, False), (4, False), (4, True)])
@pytest.mark.parametrize("held", ["both", "reversed", "signer_only"])
def test_outer_signer_selects_actual_local_recipient_independent_of_order(version, read_only, held):
    control, first, signer = multi_recipient_fixture(version=version, read_only=read_only)
    keys = {"both": [first, signer], "reversed": [signer, first], "signer_only": [signer]}[held]
    opened = pcs.unwrap_protection(control.protection, keys, require_hmac=True, require_signature=True)
    assert opened.master_key == control.field_key
    assert opened.hmac_verified


@pytest.mark.parametrize("unwrap", [pcs.unwrap_zone, pcs.unwrap_zone_record_defaults])
def test_actual_zone_use_accepts_outer_signer_after_another_locally_held_recipient(unwrap):
    control, first, signer = multi_recipient_fixture()
    assert unwrap(control.encoded, [first, signer])


def test_outer_signer_must_be_a_recipient_as_well_as_locally_available():
    receiver = ec.generate_private_key(ec.SECP256R1())
    unrelated_signer = ec.generate_private_key(ec.SECP256R1())
    control = signed_fixture(receiver=receiver, outer_signature="valid", outer_signer=unrelated_signer)
    assert pcs.describe_outer_protection_signature(control.protection, unrelated_signer.public_key()) is None
    with pytest.raises(pcs.PCSError, match="other than the matched local key"):
        pcs.unwrap_protection(control.protection, [receiver, unrelated_signer], require_hmac=True, require_signature=True)


@pytest.mark.parametrize("case,expected", [
    ("owner_review", "owner_review_context_required"),
    ("unsupported_digest", "outer_digest_unsupported"),
    ("unknown", "outer_signer_mismatch"),
    ("covered_data", "outer_covered_data_unreadable"),
    ("invalid", "outer_signature_rejected"),
])
def test_strict_outer_auth_failure_exposes_fixed_reason_before_key_unwrap(case, expected, monkeypatch):
    from unittest.mock import Mock

    control = signed_fixture(
        outer_signature=None if case == "owner_review" else "valid" if case == "covered_data" else case,
        owner_review=case == "owner_review",
    )
    protection = control.protection
    if case == "covered_data":
        protection = replace(protection, signature_data=replace(protection.signature_data, data=b"\x00"))
    original_reason = pcs.describe_outer_protection_signature(protection, control.receiver.public_key())
    blocked = Mock(side_effect=AssertionError("key unwrap must not execute after outer refusal"))
    monkeypatch.setattr(pcs, "unwrap_share_key", blocked)
    with pytest.raises(pcs.PCSError) as caught:
        pcs.unwrap_protection(protection, [control.receiver], require_hmac=True, require_signature=True)
    assert type(caught.value) is pcs.PCSError
    assert caught.value.__dict__["_homecircle_outer_auth_reason"] == expected
    assert str(caught.value) == "Protection structure's outer authentication was not confirmed: " + original_reason + "."
    blocked.assert_not_called()
