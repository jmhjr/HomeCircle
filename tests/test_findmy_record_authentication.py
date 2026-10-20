"""Locally generated encrypted records exercise the actual accessory reader."""

from copy import deepcopy
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from custom_components.homecircle._vendor_findmy.cloudkit import beacons, pcs
from custom_components.homecircle._vendor_findmy.cloudkit.constants import (
    BEACON_STORE_ZONE,
    RecordType,
    ValueType,
)
from custom_components.homecircle._vendor_findmy.cloudkit.proto import (
    cloudkit_pb2 as ck,
)
from custom_components.homecircle._vendor_findmy.cloudkit.records import CloudKitRecord
from custom_components.homecircle._vendor_findmy.icloud import AsyncFindMyClient
from tests.test_findmy_pcs_hardening import seal_field, signed_fixture


@pytest.fixture(autouse=True)
def dependency_logging(monkeypatch):
    # Production suppresses this dependency namespace, including expected skips.
    monkeypatch.setattr(beacons.logger, "disabled", True)


def record_fixture(*, secondary="sharedSecret2", invalid_signature=False):
    zone_fixture = signed_fixture()
    zone_key = ec.derive_private_key(
        pcs.derive_master_ec_private_key(zone_fixture.field_key), ec.SECP256R1()
    )
    protected = signed_fixture(
        receiver=zone_key,
        raw_key=b"\x54" * 16,
        valid_signature=not invalid_signature,
    )
    record = ck.Record()
    record.record_identifier.value.name = "synthetic-beacon"
    record.type.name = RecordType.MASTER_BEACON
    record.protection_info.protection_info = protected.encoded
    values = {
        "privateKey": (ValueType.ENCRYPTED_BYTES_TYPE, b"\x11" * 28),
        "sharedSecret": (ValueType.ENCRYPTED_BYTES_TYPE, b"\x22" * 32),
        secondary: (ValueType.ENCRYPTED_BYTES_TYPE, b"\x33" * 32),
        "pairingDate": (ValueType.DATE_TYPE, datetime(2026, 1, 1, tzinfo=UTC)),
    }
    for name, (kind, value) in values.items():
        field = record.record_field.add()
        field.identifier.name = name
        field.value.type = kind
        field.value.is_encrypted = True
        context = pcs.FieldContext(
            BEACON_STORE_ZONE, record.record_identifier.value.name, name
        )
        field.value.bytes_value = seal_field(
            protected.field_key,
            (
                ck.EncryptedValue(
                    date_value=ck.Date(time=value.timestamp())
                ).SerializeToString()
                if kind == ValueType.DATE_TYPE
                else value
            ),
            context.as_bytes(),
        )
    return SimpleNamespace(zone_fixture=zone_fixture, protected=protected, record=record, values=values)


class LocalCloud:
    """In-memory responses only; no transport or Apple account is constructed."""

    def __init__(self, fixture, record):
        self.record = record
        self.close = AsyncMock()
        self.target = SimpleNamespace(
            zone_identifier=SimpleNamespace(
                value=SimpleNamespace(name=BEACON_STORE_ZONE)
            ),
            protection_info=SimpleNamespace(protection_info=fixture.zone_fixture.encoded),
            record_protection_info=SimpleNamespace(protection_info=b""),
            HasField=lambda name: name == "protection_info",
        )

    async def zone_retrieve(self, zone):
        assert zone == BEACON_STORE_ZONE
        return [SimpleNamespace(target_zone=self.target)]

    async def iter_records(self, zone, **_kwargs):
        assert zone == BEACON_STORE_ZONE
        change = ck.RecordChange()
        change.record.CopyFrom(self.record)
        yield change


async def discover(fixture, record):
    cloud = LocalCloud(fixture, record)
    store = beacons.AsyncBeaconStore(SimpleNamespace(), client=cloud)
    client = AsyncFindMyClient(
        SimpleNamespace(), SimpleNamespace(close=AsyncMock()), store
    )
    client.use_keys([fixture.zone_fixture.receiver])
    try:
        return [value.to_json() for value in await client.accessories()]
    finally:
        await client.close()


@pytest.mark.parametrize("secondary", ["sharedSecret2", "secureLocationsSharedSecret"])
async def test_actual_reader_accepts_generated_protected_accessory(secondary):
    fixture = record_fixture(secondary=secondary)
    records = await discover(fixture, fixture.record)
    assert len(records) == 1
    assert records[0]["master_key"] == (b"\x11" * 28).hex()
    assert records[0]["skn"] == (b"\x22" * 32).hex()
    assert records[0]["sks"] == (b"\x33" * 32).hex()


@pytest.mark.parametrize(
    "name",
    ["privateKey", "sharedSecret", "sharedSecret2", "secureLocationsSharedSecret"],
)
async def test_required_secret_fields_cannot_skip_field_authentication(name):
    secondary = (
        "secureLocationsSharedSecret"
        if name == "secureLocationsSharedSecret"
        else "sharedSecret2"
    )
    fixture = record_fixture(secondary=secondary)
    changed = deepcopy(fixture.record)
    for field in changed.record_field:
        if field.identifier.name == name:
            field.value.is_encrypted = False
            field.value.bytes_value = fixture.values[name][1]
    assert await discover(fixture, changed) == []
    parsed = CloudKitRecord.from_proto(changed, BEACON_STORE_ZONE)
    opened = beacons.decrypt_record(parsed, [fixture.protected.receiver])
    assert name not in opened.values and name not in opened.raw_values
    assert (
        opened.undecryptable[name] == "secret field requires authenticated encryption"
    )


async def test_authenticated_key_bytes_still_reject_a_modified_tag():
    fixture = record_fixture()
    changed = deepcopy(fixture.record)
    field = next(
        field for field in changed.record_field if field.identifier.name == "privateKey"
    )
    field.value.bytes_value = field.value.bytes_value[:-1] + bytes(
        [field.value.bytes_value[-1] ^ 1]
    )
    assert await discover(fixture, changed) == []


async def test_actual_record_reader_requires_signature_even_with_valid_hmac():
    fixture = record_fixture(invalid_signature=True)
    assert pcs.verify_protection_hmac(
        fixture.protected.protection, fixture.protected.field_key
    )
    assert await discover(fixture, fixture.record) == []


async def test_actual_record_reader_requires_hmac():
    fixture = record_fixture()
    changed = deepcopy(fixture.record)
    changed.protection_info.protection_info = fixture.protected.encoded.replace(
        fixture.protected.protection.hmac, b"\0" * 32
    )
    assert await discover(fixture, changed) == []


def test_plain_public_metadata_remains_available():
    fixture = record_fixture()
    field = fixture.record.record_field.add()
    field.identifier.name = "publicMetadata"
    field.value.type = ValueType.BYTES_TYPE
    field.value.is_encrypted = False
    field.value.bytes_value = b"synthetic-public-value"
    parsed = CloudKitRecord.from_proto(fixture.record, BEACON_STORE_ZONE)
    opened = beacons.decrypt_record(parsed, [fixture.protected.receiver])
    assert opened.values["publicMetadata"] == b"synthetic-public-value"
    assert "privateKey" in opened.raw_values
