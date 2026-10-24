"""Fixed recovery group bounds precede the installed backend's integer parser."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.homecircle._vendor_findmy.keychain import recovery
from custom_components.homecircle._vendor_findmy.keychain.escrow import (
    build_keyvault_message,
    parse_keyvault_message,
)


IDENTITY = "10000000000000001"
PASSCODE = "synthetic-owner-passcode"
RECORD = SimpleNamespace(is_recovery_candidate=True, label="synthetic-record")


class GeneratedSrpProxy:
    """Generated verifier and authenticated server proof, without Apple traffic."""

    def __init__(self, public=None, sign_octet=False):
        self._account = SimpleNamespace(_homecircle_recovery_guard_required=True)
        self.public, self.sign_octet = public, sign_octet
        self.proofs_sent = 0

    async def srp_init(self, label, client_public, transaction):
        srp = recovery.srp
        salt, verifier = srp.create_salted_verification_key(
            IDENTITY, PASSCODE, hash_alg=srp.SHA256, ng_type=srp.NG_2048,
            salt_len=64,
        )
        self.verifier = srp.Verifier(
            IDENTITY, salt, verifier, client_public,
            hash_alg=srp.SHA256, ng_type=srp.NG_2048,
        )
        salt, public = self.verifier.get_challenge()
        if self.public is not None:
            public = self.public
        else:
            public = public.rjust(256, b"\0")
            if self.sign_octet:
                public = b"\0" + public
        return {"dsid": IDENTITY, "respBlob": build_keyvault_message(
            b"\0" * 24, [b"12345678", salt, public],
        )}

    async def recover(self, label, proof_blob, transaction, *, dsid):
        self.proofs_sent += 1
        _, sections = parse_keyvault_message(proof_blob, 24, 2)
        server_proof = self.verifier.verify_session(sections[1])
        assert server_proof is not None
        return {"respBlob": build_keyvault_message(
            b"\0" * 24, [server_proof, b"IV", b"ciphertext"],
        )}


@pytest.mark.parametrize("public", [
    b"", b"\xff" * 257, b"\0" * 258,
    b"\xff" * 4096, b"\xff" * 65536, b"\xff" * 262144,
])
async def test_oversized_public_never_reaches_backend_or_submits_proof(monkeypatch, public):
    current = GeneratedSrpProxy(public=public)
    convert = Mock(side_effect=AssertionError("Unbounded public value reached SRP conversion"))
    # User construction also converts fixed-size inputs. Spy at the challenge
    # boundary so legitimate client ephemeral generation remains real.
    monkeypatch.setattr(recovery.srp.User, "process_challenge", convert)
    with pytest.raises(recovery.RecoveryProtocolError) as caught:
        await recovery.recover_bottled_peer(current, RECORD, PASSCODE)
    assert (caught.value.stage, caught.value.dispatch_state) == ("preproof", "not_dispatched")
    assert current.proofs_sent == 0
    convert.assert_not_called()


@pytest.mark.parametrize("sign_octet", [False, True])
async def test_real_srp_proof_accepts_group_width_and_optional_zero_sign_octet(monkeypatch, sign_octet):
    current = GeneratedSrpProxy(sign_octet=sign_octet)
    monkeypatch.setattr(recovery, "unwrap_outer_blob", lambda *args, **kwargs: b"synthetic-inner")
    monkeypatch.setattr(recovery, "_unwrap_inner_off_loop", AsyncMock(return_value=b"synthetic-material"))
    # This test exercises an unguarded library caller. The guarded transport's
    # reservation lifetime is covered by the actual proxy integration tests.
    current._account._homecircle_recovery_guard_required = False
    assert await recovery.recover_bottled_peer(current, RECORD, PASSCODE) == b"synthetic-material"
    assert current.proofs_sent == 1 and current.verifier.authenticated()
