"""
Recovering a bottled peer from an escrow record, using a device passcode.

Implements Stage 3 §6.1 to §6.5 of the Find My key-export protocol specification: the SRP
exchange in which the passcode is the password, and the two layers of blob it unwraps.

What comes out is **not the keychain**. It is a bottled peer -- the sealed identity of a
device that was already in the user's trust circle -- which :mod:`findmy.keychain.bottle`
turns into keys and which is then used to vouch for a new identity of our own. This module
stops at the sealed material.

.. warning::
    **The passcode is the most sensitive value this library touches.** It is the key to
    the user's entire keychain, and unlike an Apple ID password it cannot be rotated
    without physical access to the device. It is read, used twice, and discarded: nothing
    here stores it, logs it, or keeps it past the call it was passed to. Callers should
    hold it no longer.

    Nothing in this module writes to the account. Recovery reads escrowed material; it is
    *joining* that creates a peer and an escrow record, and that is elsewhere.
"""

from __future__ import annotations

import base64
import asyncio
import binascii
import hashlib
import logging
import secrets
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from aiohttp import ClientError
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from custom_components.homecircle._vendor_findmy.errors import (
    AppleServiceUnavailableError, UnauthorizedError, UnhandledProtocolError,
)
from custom_components.homecircle._vendor_findmy.util.srp import recovery as srp

from .escrow import (
    EscrowError,
    EscrowRecoveryError,
    KeyVaultSection,
    build_keyvault_message,
    parse_keyvault_message,
    split_keyvault_message,
    recovery_attempt,
)

if TYPE_CHECKING:
    from .escrow import AsyncEscrowProxy, EscrowRecord

logger = logging.getLogger(__name__)

# §6.2: the header of an srp_init reply is two 32-bit values then a 16-byte request id.
SRP_INIT_HEADER_LENGTH = 24
SRP_INIT_SECTIONS = 3

# §6.3: the two values rewritten into that header before it is sent back.
RECOVERY_MAGIC = 165
RECOVERY_CLUB_TYPE = 1

# §6.3: the exchange token goes back in a section that occupies twenty bytes -- its
# four-byte length prefix, its eight bytes, and eight zeros. Why twenty is not
# established; the service expects it.
EXCHANGE_TOKEN_FOOTPRINT = 20

# §6.4: the reply header is longer when a club type is in play.
RECOVER_HEADER_LENGTH = 24
RECOVER_HEADER_LENGTH_CLUB = 40
RECOVER_SECTIONS = 3

# §6.5: the innermost blob.
INNER_HEADER_LENGTH = 16
INNER_SECTIONS = 6
INNER_KEY_LENGTH = 16
INNER_IV_LENGTH = 16

# A local CPU-work ceiling, not a claimed Apple protocol maximum. The bundled
# enrollment writer uses 10,000 rounds; allow 100 times that work while refusing
# an authenticated response that asks for up to 2**32-1 synchronous rounds.
MAX_PBKDF2_ITERATIONS = 1_000_000

# §6.4's cipher table.
BLOB_VERSION_CBC = 0
BLOB_VERSION_UNKNOWN = 1
BLOB_VERSION_GCM = 2
GCM_NONCE_LENGTH = 16
GCM_TAG_LENGTH = 16

# §6.2: a 32-byte client secret. pysrp wants exactly 256 bytes and reads them as an
# integer, so the value is left-padded rather than lengthened.
CLIENT_SECRET_LENGTH = 32
_PYSRP_SECRET_LENGTH = 256
SRP_MODULUS_BYTES = 256


class RecoveryError(UnhandledProtocolError):
    """Raised when a recovery cannot be completed."""



class RecoveryProtocolError(RecoveryError):
    """Safe structured recovery outcome, independent of stale diagnostics or text."""

    def __init__(
        self, stage: str, dispatch_state: str, *, http_status: object = None,
        service_code: object = None, reason: str = "protocol",
    ) -> None:
        self.reason = reason if reason in {"transient", "protocol"} else "protocol"
        self.stage = stage if stage in {"preproof", "dispatch", "refusal", "serverproof", "material"} else "preproof"
        self.dispatch_state = dispatch_state if dispatch_state in {
            "not_dispatched", "uncertain", "refused", "verified",
        } else "uncertain"
        self.server_verified = self.dispatch_state == "verified"
        self.http_status = http_status if type(http_status) is int and 100 <= http_status <= 599 else None
        self.service_code = service_code if type(service_code) is int and abs(service_code) <= 1000000 else None
        super().__init__("Recovery exchange " + self.stage)


def _blob_bytes(value: object, name: str) -> bytes:
    """
    Read a blob from a property-list response.

    The escrow proxy carries these as **base64 in a string**, not as plist `data`, which
    is the same encoding the request uses in the other direction. Raw bytes are accepted
    too, so that a response using `data` would not need a second code path.
    """
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        try:
            return base64.b64decode(value)
        except (ValueError, binascii.Error) as e:
            msg = f"{name} is a string but not valid base64: {e}"
            raise RecoveryError(msg) from None

    msg = f"{name} is a {type(value).__name__}, which is neither bytes nor base64 text"
    raise RecoveryError(msg)


@dataclass(frozen=True)
class RecoveryChallenge:
    """What the escrow proxy answers `srp_init` with."""

    label: str
    """The record being recovered, by its own label."""

    transaction_id: str
    """Shared with the `recover` call that completes the exchange."""

    prefix: bytes
    """
    The four leading bytes of the reply's framing: its own total length.

    Kept for diagnosis only. A reply computes its own rather than echoing this one.
    """

    header: bytes
    """The reply's 24-byte header, rewritten and sent back in the proof."""

    exchange_token: bytes
    """
    Section 0, and the value re-sent as a section in the proof.

    **Not** the transaction id, which is the sixteen bytes inside the header and travels
    back there untouched. The reply carries two identifiers and only this one is re-sent
    as a section of its own.
    """

    salt: bytes
    server_public: bytes

    dsid: str
    """The SRP identity. Not the Apple ID, and not the `adsid` from authentication."""

    club_type_id: int | None


def parse_challenge(response: dict[str, Any], label: str, transaction_id: str) -> RecoveryChallenge:
    """Read an `srp_init` reply."""
    blob = response.get("respBlob")
    if not blob:
        msg = "srp_init returned no respBlob"
        raise RecoveryError(msg)

    dsid = response.get("dsid")
    if not dsid:
        msg = "srp_init returned no dsid, which is the SRP identity"
        raise RecoveryError(msg)

    prefix, header, sections = split_keyvault_message(
        _blob_bytes(blob, "srp_init's respBlob"),
        SRP_INIT_HEADER_LENGTH,
        SRP_INIT_SECTIONS,
    )
    # This exchange always uses the fixed 2048-bit group. The installed backend
    # converts B a byte at a time with growing integers before checking its
    # width; an oversized unauthenticated challenge would block HA's event loop.
    # Retain one optional zero sign octet, which has the same integer value.
    server_public = sections[2]
    if not (1 <= len(server_public) <= SRP_MODULUS_BYTES or (
        len(server_public) == SRP_MODULUS_BYTES + 1 and server_public[0] == 0
    )):
        raise RecoveryError("The recovery public value exceeds the supported fixed group")
    logger.debug(
        "srp_init framing: prefix %s, header %s, section lengths %s",
        prefix.hex(),
        header.hex(),
        [len(section) for section in sections],
    )

    return RecoveryChallenge(
        label=label,
        transaction_id=transaction_id,
        prefix=prefix,
        header=header,
        exchange_token=sections[0],
        salt=sections[1],
        server_public=server_public,
        dsid=str(dsid),
        club_type_id=response.get("clubTypeID"),
    )


def build_recovery_proof(challenge: RecoveryChallenge, proof: bytes) -> bytes:
    """
    Frame an SRP proof the way the `recover` command expects it.

    Two sections and no others: the exchange token from section 0, then the proof.

    The token's section occupies twenty bytes while declaring the eight it holds -- zeros
    are appended after the data, and the offsets account for the larger footprint. Padding
    the data itself to twenty and declaring twenty produces a message that parses and is
    rejected.

    The header's sixteen-byte transaction id is a different value and travels back inside
    the header, untouched.
    """
    header = bytearray(challenge.header)
    header[0:4] = RECOVERY_MAGIC.to_bytes(4, "big")
    header[4:8] = (2 if challenge.club_type_id == RECOVERY_CLUB_TYPE else 0).to_bytes(4, "big")

    token = KeyVaultSection(challenge.exchange_token, footprint=EXCHANGE_TOKEN_FOOTPRINT)

    return build_keyvault_message(bytes(header), [token, proof])


def unwrap_outer_blob(blob: bytes, session_key: bytes, *, club_type_id: int | None) -> bytes:
    """
    Decrypt the outer blob a successful `recover` returns.

    Its header length depends on the club type, and a version field four bytes into that
    header selects the cipher.

    :returns: The inner blob, still wrapped -- see :func:`unwrap_inner_blob`.
    :raises RecoveryError: If the version is one this specification does not describe.
    """
    header_length = (
        RECOVER_HEADER_LENGTH_CLUB if club_type_id == RECOVERY_CLUB_TYPE else RECOVER_HEADER_LENGTH
    )
    header, sections = parse_keyvault_message(blob, header_length, RECOVER_SECTIONS)

    version = int.from_bytes(header[4:8], "big")
    iv, ciphertext = sections[1], sections[2]

    if version == BLOB_VERSION_CBC:
        decryptor = Cipher(algorithms.AES(session_key), modes.CBC(iv)).decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        return _strip_padding(plaintext)

    if version == BLOB_VERSION_GCM:
        # A 16-byte nonce, not GCM's usual 12. The tag's position is not stated; it is
        # taken from the end of the ciphertext, which is where every other construction in
        # this protocol puts it.
        if len(iv) != GCM_NONCE_LENGTH:
            logger.warning(
                "Expected a %d-byte GCM nonce, got %d",
                GCM_NONCE_LENGTH,
                len(iv),
            )
        body, tag = ciphertext[:-GCM_TAG_LENGTH], ciphertext[-GCM_TAG_LENGTH:]
        decryptor = Cipher(algorithms.AES(session_key), modes.GCM(iv, tag)).decryptor()
        try:
            return decryptor.update(body) + decryptor.finalize()
        except InvalidTag:
            msg = "Outer blob failed to authenticate under the SRP session key"
            raise RecoveryError(msg) from None

    if version == BLOB_VERSION_UNKNOWN:
        msg = (
            "The outer blob announces version 1, which this specification does not"
            " describe. Refusing rather than guessing at a cipher."
        )
        raise RecoveryError(msg)

    msg = f"The outer blob announces unknown version {version}"
    raise RecoveryError(msg)


def _strip_padding(plaintext: bytes) -> bytes:
    """Remove PKCS#7 padding if it is there, and leave the data alone if it is not."""
    try:
        unpadder = padding.PKCS7(128).unpadder()
        return unpadder.update(plaintext) + unpadder.finalize()
    except ValueError:
        # The padding scheme is not stated. Returning the plaintext unaltered is better
        # than failing, since the next layer will reject it if this was wrong.
        logger.debug("Outer blob plaintext is not PKCS#7 padded; using it as-is")
        return plaintext


def unwrap_inner_blob(blob: bytes, passcode: str) -> bytes:
    """
    Decrypt the innermost blob, which is where the passcode is spent a second time.

    Note that one section serves as **both** the PBKDF2 salt and, in its first sixteen
    bytes, the CBC initialisation vector -- and that the iteration count is carried in the
    blob's own header rather than being fixed.

    :param blob: The plaintext from :func:`unwrap_outer_blob`.
    :param passcode: The device passcode. Not retained.
    :returns: The bottled peer, sealed.
    """
    header, sections = parse_keyvault_message(blob, INNER_HEADER_LENGTH, INNER_SECTIONS)

    iterations = int.from_bytes(header[8:12], "big")
    if not 1 <= iterations <= MAX_PBKDF2_ITERATIONS:
        msg = "The inner blob's PBKDF2 iterations exceed the supported local work policy"
        raise RecoveryError(msg)

    salt = sections[1]
    if len(salt) < INNER_IV_LENGTH or not sections[3] or len(sections[3]) % INNER_IV_LENGTH:
        raise RecoveryError("The inner blob carries invalid CBC parameters")
    derived = hashlib.pbkdf2_hmac("sha256", passcode.encode(), salt, iterations, INNER_KEY_LENGTH)

    decryptor = Cipher(algorithms.AES(derived), modes.CBC(salt[:INNER_IV_LENGTH])).decryptor()
    plaintext = decryptor.update(sections[3]) + decryptor.finalize()

    return _strip_padding(plaintext)


async def _unwrap_inner_off_loop(blob: bytes, passcode: str) -> bytes:
    """Drain bounded local work before propagating cancellation or releasing inputs."""
    # Shield the outcome container, not a task that can raise: Python 3.14 logs
    # exceptions from a shielded task after caller cancellation even if drained.
    task = asyncio.gather(asyncio.to_thread(unwrap_inner_blob, blob, passcode), return_exceptions=True)
    cancellation = None
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError as error:
            if cancellation is None:
                cancellation = error
    if cancellation is not None:
        if not task.cancelled():
            task.result()  # Consume a worker failure when cancellation takes priority.
        raise cancellation
    result = task.result()[0]
    if isinstance(result, BaseException):
        raise result
    return result


async def recover_bottled_peer(
    proxy: AsyncEscrowProxy,
    record: EscrowRecord,
    passcode: str,
) -> bytes:
    """
    Recover the sealed material an escrow record holds.

    The passcode is used twice and neither use substitutes for the other: once as the SRP
    password, and again as a PBKDF2 input to unwrap the innermost blob. It is not stored,
    logged or retained past this call.

    Nothing here writes to the account.

    :param proxy: An escrow-proxy client.
    :param record: The record to recover from, from a listing. It must carry a bottle.
    :param passcode: The screen-lock passcode of the device that made the record.
    :returns: The bottled peer, still sealed -- :mod:`findmy.keychain.bottle` opens it.
    :raises RecoveryError: If the exchange fails. Note that a wrong passcode and a
        mis-parameterised SRP exchange fail identically, so a failure here is not proof
        the passcode was wrong.
    """
    if not record.is_recovery_candidate:
        raise RecoveryProtocolError("preproof", "not_dispatched")
    if not passcode:
        raise RecoveryProtocolError("preproof", "not_dispatched")

    transaction_id = str(uuid.uuid4()).upper()

    diagnostics = getattr(getattr(proxy, "_account", None), "_recovery_diagnostics", None)
    def mark(phase: str) -> None:
        if isinstance(diagnostics, dict):
            diagnostics["unlock_phase"] = phase

    # A 32-byte secret, left-padded because the library wants 256 bytes and reads
    # them as an integer.
    secret = secrets.token_bytes(CLIENT_SECRET_LENGTH).rjust(_PYSRP_SECRET_LENGTH, b"\x00")
    user = srp.User(
        "",  # replaced below: the identity is only known once srp_init has answered
        passcode,
        hash_alg=srp.SHA256,
        ng_type=srp.NG_2048,
        bytes_a=secret,
    )
    _, client_public = user.start_authentication()

    logger.info("Beginning escrow recovery for %s", record.label)
    mark("srp_init")
    try:
        challenge = parse_challenge(
            await proxy.srp_init(record.label, client_public, transaction_id),
            record.label,
            transaction_id,
        )
    except UnauthorizedError:
        raise
    except EscrowRecoveryError as error:
        raise RecoveryProtocolError(
            error.stage, error.dispatch_state, http_status=error.http_status,
            service_code=error.service_code, reason=error.reason,
        ) from None
    except Exception as error:
        if getattr(getattr(proxy, "_account", None), "_homecircle_recovery_guard_required", False):
            raise RecoveryProtocolError(
                "preproof", "not_dispatched", reason=(
                    "transient" if isinstance(error, (OSError, ClientError, AppleServiceUnavailableError)) else "protocol"
                ),
            ) from None
        raise

    # The identity is the dsid the reply carried, which is why it is set here rather
    # than at construction. The library accepts either a string or bytes and encodes
    # as needed; the annotation says otherwise.
    user.I = challenge.dsid  # pyright: ignore [reportAttributeAccessIssue]

    mark("srp_proof")
    try:
        proof = user.process_challenge(challenge.salt, challenge.server_public)
        if proof is None:
            raise RecoveryError("Invalid recovery challenge")
        proof_blob = build_recovery_proof(challenge, proof)
    except Exception:
        raise RecoveryProtocolError("preproof", "not_dispatched") from None

    try:
        mark("escrow_recover")
        response = await proxy.recover(
            record.label,
            proof_blob,
            transaction_id,
            dsid=challenge.dsid,
        )
    except EscrowRecoveryError as error:
        raise RecoveryProtocolError(
            error.stage, error.dispatch_state, http_status=error.http_status,
            service_code=error.service_code, reason=error.reason,
        ) from None
    except EscrowError:
        # A proxy without structured outcome evidence cannot establish refusal.
        raise RecoveryProtocolError("dispatch", "uncertain") from None

    try:
        blob = _blob_bytes(response.get("respBlob"), "recover's respBlob")
        header_length = (
            RECOVER_HEADER_LENGTH_CLUB
            if challenge.club_type_id == RECOVERY_CLUB_TYPE
            else RECOVER_HEADER_LENGTH
        )
        _, _, sections = split_keyvault_message(blob, header_length, RECOVER_SECTIONS)
    except Exception:
        raise RecoveryProtocolError("serverproof", "uncertain") from None

    # Verify the server before decrypting anything with the session key it implies.
    mark("server_proof")
    try:
        user.verify_session(sections[0])
        authenticated = user.authenticated()
    except Exception:
        raise RecoveryProtocolError("serverproof", "uncertain") from None
    if not authenticated:
        raise RecoveryProtocolError("serverproof", "uncertain")

    # Clear the pending reservation at the first authenticated server proof. Later
    # material/discovery errors are not another rejected passcode exchange.
    try:
        attempt = recovery_attempt(getattr(proxy, "_account", None))
    except EscrowRecoveryError as error:
        raise RecoveryProtocolError(error.stage, "verified") from None
    if attempt is not None:
        await attempt.verified()

    try:
        session_key = user.get_session_key()
        if session_key is None:
            raise RecoveryError("SRP produced no session key")
        mark("outer_decrypt")
        outer = unwrap_outer_blob(blob, session_key, club_type_id=challenge.club_type_id)
        mark("inner_decrypt")
        # Hashlib's PBKDF2 runs to completion in native code. Keep its bounded
        # work off HA's loop and finish it before returning cancellation so the
        # worker cannot keep these inputs after this recovery call has ended.
        material = await _unwrap_inner_off_loop(outer, passcode)
    except Exception:
        raise RecoveryProtocolError("material", "verified") from None

    logger.info("Recovered %d bytes of sealed material from %s", len(material), record.label)
    return material


__all__ = [
    "RecoveryChallenge",
    "RecoveryError",
    "RecoveryProtocolError",
    "build_recovery_proof",
    "parse_challenge",
    "recover_bottled_peer",
    "unwrap_inner_blob",
    "unwrap_outer_blob",
]
