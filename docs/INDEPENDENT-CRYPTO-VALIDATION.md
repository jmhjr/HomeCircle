# Independent Find My cryptographic validation

October 19, 2026. This review found and corrected failures in peer identity
binding, recovered-key metadata binding, bottle validation, recovery resource
limits, PCS enforcement, accessory secret-field authentication, and saved-account
binding. The corrected paths pass generated positive and negative controls.
These results establish local behavior under the tested inputs; they do not
establish live Apple acceptance or complete protocol correctness.

## Candidate and review boundary

The starting artifact was the **112-file** local integration ZIP with manifest
version **`0.1.0-beta.19`** and SHA-256:

`b52097c6f6f88e206ca9ef48618ad00984a95c49d4b588da883232981ab7f2de`

The input archive was inventoried by file size and hash. It was a local candidate
on top of `373203a85da0e1f9c4d7d3c2eabfd31663475bee`, with existing uncommitted
work, rather than a clean checkout identified by that commit alone. The fixes
described here are subsequent candidate changes. Earlier validation documents
remain historical records of their own artifacts.

The final local candidate contains **112 files**, retains manifest
**`0.1.0-beta.19`**, and has ZIP SHA-256: `f0477a91e78181fe1f8d80ada176a1739e10a7502abe7ee6ee2240571280d1f5`.

Three fresh completed AI code-review passes examined trust and key use, the
recovery exchange, and PCS. The coordinating review separately exercised record
and report consumers, storage, and configured account ownership. Reciprocal
review checked the resulting changes. These passes inspected the actual source
and installed dependencies and used local controls without depending on the
prior implementation author's explanation. “Independent” describes that review
process. This is **not a human cryptographic audit or an external formal security
audit**.

The controls used generated EC keys, verifiers, SRP transcripts, signatures,
encrypted records, and disposable Home Assistant storage. They exercised actual
parsers and consumer paths, including peer-directory and share responses,
recovery, PCS zone and record unwrapping, accessory discovery, and provider
startup. Positive controls accompanied mutations so a rejection alone could not
be mistaken for a working implementation. Fixture assembly included separate
wire and cryptographic construction from pinned source descriptions; selected
controls also used existing library producer helpers. Such a round trip is not
an independent interoperability oracle.

No independent Apple-producer fixture was obtained or executed. Published Apple
and third-party producer/consumer source was inspected, but inspecting that source
is different from accepting its output on an Apple account. The review made no
Apple requests, used no real account secrets or private records, and performed no
deployment or release publication.

## Trust model

HTTPS and account authentication establish the service channel and the account
under which records were returned. They do not replace record signatures, field
authentication, or the binding between a record's identity and the key used to
read it. Conversely, a valid self-signature establishes an identity's internal
binding; it does not independently establish that identity's current account
membership.

The reader still relies on the authenticated Cuttlefish service for the account's
peer listing. This review does **not** validate the complete Octagon membership
graph, every stable/dynamic-info signature, voucher, exclusion, revocation, or
membership-history transition. It therefore does not claim an independently
verified chain of current trust-circle membership.

The record mutations test behavior if a consumer encounters malformed or
substituted data, including mistakes by an authenticated service. They do not
demonstrate that an ordinary network attacker can inject those inputs through
the configured HTTPS transport.

## Confirmed findings and resulting checks

### Peer identities, shares, and bottles

The baseline directory reader could accept permanent information whose claimed
peer identifier or self-signature did not authenticate the supplied signing key.
A generated share signed by that substituted key could then appear verified.
The reader now derives the identifier from the original permanent-info bytes and
signature and verifies the typed permanent-info signature before admitting the
peer to the directory. Wrong identifiers, wrong signature contexts, and invalid
self-signatures cannot supply a trusted share-verification key.

A separately signed share for another keychain view could also acquire a
`Manatee` label or UUID alias from surrounding response metadata. Strict key use
now requires the authenticated TLK plaintext to carry its view and UUID, checks
them against the selected view and supplied references, and prevents unsigned
wrappers from creating a second alias for the recovered key. Wrong recipients
and invalid share signatures remain rejected. The advertised receiver public key
remains a hint rather than a new trust anchor; Apple's signing construction
deliberately excludes that field. See the pinned
[CKKSTLKShare signing and verification code](https://github.com/apple-oss-distributions/Security/blob/db15acbe6a7f257a859ad9a3bb86097bfe0679d9/keychain/ckks/CKKSTLKShare.m).

Bottle recovery retains the existing complete GCM tag and escrow-signature
checks and now requires the recovered peer's signature and agreement between
decrypted private keys and the bottle's public keys. A known directory peer must
also agree. The baseline's missing-directory case could return keys despite an
invalid peer signature; it now rejects that input. A valid bottle from a departed
peer can still be read using the recovered signing key, without claiming that the
peer remains a known current member. This follows Apple's
[BottledPeer reader](https://github.com/apple-oss-distributions/Security/blob/db15acbe6a7f257a859ad9a3bb86097bfe0679d9/keychain/TrustedPeersHelper/BottledPeer/BottledPeer.swift),
which verifies the peer signature after decrypting and matching the peer keys.

Controls include valid wire responses, forged directory identities, signatures
under the wrong typed context, relabeled views and UUIDs, recipient mismatch,
validly signed bottles containing mismatched keys, invalid departed-peer
signatures, and the wrong account salt. The main regressions are
[trust binding](../tests/test_findmy_trust_binding.py) and
[cryptographic key use](../tests/test_findmy_crypto_hardening.py).

### Recovery proof, resources, and cancellation

Actual SRP controls confirmed that a valid server proof is required before the
session key is obtained or recovery material is decrypted. A changed server proof
and a previous exchange's proof fail before material use. Modified GCM tags fail
authentication. GSA and recovery use separate namespaces for the installed SRP
implementation's different username-hashing modes, without changing the shared
dependency's global mode.

The review reproduced an availability defect before recovery proof submission:
an oversized server public value reached the pure-Python SRP integer parser on
Home Assistant's event loop. A 262,144-byte generated value blocked that loop for
**12.67 seconds** before rejection, despite fitting within the transport's body
limit. Recovery now rejects values exceeding the fixed 2048-bit group width
before invoking that parser, while allowing one harmless leading zero sign
octet. Generated valid 256-byte and zero-prefixed 257-byte encodings still verify;
oversized controls never invoke challenge processing or submit a proof.

The marked onboarding GSA path could also return cancellation while its password
derivation worker continued to hold the password. It now drains bounded native
work before returning, preserves the first cancellation through repeated
cancellation, and consumes a worker failure without logging the private error.
The existing unmarked legacy sign-in path is unchanged. The recovery PBKDF2 limit,
off-loop derivation, and cancellation drain remain in force. This bounds input
lifetime to the completing call; it does not promise Python memory zeroization.

The account-bound recovery guard reserves before the possible proof dispatch,
disables automatic replay and redirects, and distinguishes refused, uncertain,
and server-verified exchanges. A verified proof followed by a material failure
is not classified as another rejected passcode. Cached recovery material remains
limited to the same authenticated account and exact record. These controls make
no claim about Apple's remaining retry allowance.

See [recovery public-value bounds](../tests/test_findmy_recovery_public_bounds.py),
[GSA worker lifetime](../tests/test_findmy_gsa_work_lifetime.py),
[recovery protocol](../tests/test_findmy_recovery_protocol.py), and
[SRP isolation](../tests/test_findmy_srp_isolation.py).

### PCS and accessory records

The baseline PCS consumers could continue after failed structure authentication.
The actual zone and record key-use paths now require the full SHA-256 HMAC and
the applicable structure signature. A valid HMAC does not excuse an invalid
inner signature. Diagnostic helpers may still expose verification results
without enforcing them; those permissive defaults are not used to authorize
production key use.

The implementation also separates the raw recovered key used for the inner
signature from the derived share key used by shared writable structures for
HMAC, metadata, and field decryption. Encrypted field headers select among the
authenticated current and extra symmetric keys. An unknown key identifier is
rejected rather than silently falling back to the current key. Field GCM
authentication includes the encrypted header and the composed zone, record,
and field context. The tested context mutations reject an otherwise valid field;
this is not a proof that every possible composed context is unambiguous.

These distinctions were checked against the pinned
[rustpush PCS producer and consumer](https://github.com/OpenBubbles/rustpush/blob/b3c96c23e1aae78d1229ebaccb12027624f1eaff/src/icloud/pcs.rs).
Its producer makes the outer signature optional and supplies a derived key to a
read-only participant. The supported policy therefore preserves an absent outer
signature, verifies a supplied outer signature under the matched local key, and
skips the raw-master-key inner signature only for the read-only case where that
key is unavailable. The full HMAC and field authentication remain required.

Reciprocal review found a compatibility regression in the initial strict outer
signature check: choosing the first locally held recipient could reject a valid
structure whose outer signer was a different locally held recipient. Selection
now considers only actual keyset recipients and, when an outer signature is
supplied, chooses a recipient whose local key verifies that signature. Adding
another matching recipient or reordering the local keys cannot break the valid
case. A locally available signer absent from the keyset remains ineligible.
Generated canonical-DER multi-recipient controls cover both orders, the signer
alone, writable/read-only forms, and both strict zone consumers.

Unsupported outer-signature digests, an untrusted supplied signer, and owner
review/custom signer attribute **7** are refused in strict key use. This reader
does not have the separate trusted signer context needed for that attribute and
does not manufacture it from a public key supplied by the record. Compatibility
with those unsupported sharing forms is not claimed.

The actual accessory reader also previously trusted the transport's unencrypted
field flag for secret key material. It now requires field authentication for
`privateKey`, `sharedSecret`, `sharedSecret2`, and
`secureLocationsSharedSecret`. Clearing the flag and inserting plaintext cannot
export an accessory. Public metadata remains readable. Ten generated
[record-authentication controls](../tests/test_findmy_record_authentication.py)
exercise valid records, both secondary-secret names, flag bypasses, a modified
tag, and failed structure HMAC/signature. The broader
[PCS controls](../tests/test_findmy_pcs_hardening.py) cover writable and read-only
branches, optional outer signatures, key selection, and strict consumer calls.

### Configured account and saved session

When configuration records an authenticated account fingerprint, provider startup
now compares it with the decrypted vault session before restoring the client or
polling. A valid encrypted vault containing another account's session is refused;
another correctly bound account continues independently. Failure leaves the
stored vault unchanged. The two new provider cases in
[account binding](../tests/test_findmy_account_binding.py) cover matching and
substituted sessions, alongside the existing account-identity tests. Legacy
configuration without a recorded fingerprint retains its existing compatibility
behavior; this check does not retroactively create missing identity evidence.

## Remaining limits

- KeyVault framing still accepts some inconsistent declared lengths, terminal
  offsets, and trailing bytes. Controls changed those ignored bytes while
  retaining a valid SRP proof and GCM payload, without demonstrating substituted
  key acceptance. No unproven Apple framing or padding requirement was imposed.
- CBC recovery envelopes do not intrinsically authenticate ciphertext, and the
  reader retains its non-PKCS#7 fallback. Later material and bottle checks remain
  necessary. A valid 12-byte GCM nonce also remains accepted; it is not a
  cryptographic failure merely because the current wire comment expects 16.
- Location coordinates are authenticated by the report's GCM payload, but the
  report timestamp and some outer metadata lie outside that payload's
  authentication scope. Successful coordinate decryption does not cryptographically
  prove report freshness, physical accuracy, or the integrity of all surrounding
  metadata. Poll time and source report time must retain their separate meanings.
- Generated success does not prove that every Apple encoding, historical key
  rotation, sharing mode, or legacy record remains compatible. The zone-default
  fallback, in particular, still lacks live acceptance evidence. Conservative
  rejection may expose previously hidden unsupported records.

## Validation and evidence

The focused exchange/GSA/SRP group passed **138 tests**. The completed PCS group,
including the reciprocal multi-recipient regressions, passed **60 tests**. The
accessory record group passed **10 tests**, and the two
new provider binding cases passed within the account-binding validation group.
These groups overlap with the full suite and must not be added together as an
independent total.

Final full backend suite: **1,421 passed**, with one optional Apple-installer
fixture test skipped because the public fixture is not retained. This adds
**101 regressions** to the 1,320-test starting checkpoint. Network sockets are
disabled by default; only explicitly scoped disposable local lifecycle tests use
loopback connections.

The public-file guard checked **315 files** without flagged patterns after two
synthetic fixture labels were clarified; the affected **18 controls** passed
again. No production payload changed during that clarification. Automated
scanning does not replace manual privacy review. Final frontend build,
**110 frontend tests**, Prettier, integration/test Ruff,
archive/inventory/source matching, and whitespace checks passed. Fresh-process
imports of **16 selected modules** from the extracted candidate passed with
network connections prohibited and ordinary shared SRP flags unchanged. The
packaged disposable Core lifecycle passed install, version-fixture upgrade,
restart, removal and post-removal restart; unrelated resources were preserved
and the temporary configuration was removed. This is not a canonical beta-19
upgrade or HACS acceptance. Four fresh processes also revalidated encrypted-vault
identity continuity, including omission/reselection and changed-key/foreign-account
controls. The Ruby source, frozen published beta-19 archive and prior review
summary retain their recorded hashes.

Baseline and corrected synthetic
receipts, the archive inventory, downloaded primary-source hashes, and local
reproduction scripts were retained outside the release artifact. Public
regression tests provide the repeatable controls without account data.

The primary-source snapshots used for this review are pinned to Apple Security
commit `db15acbe6a7f257a859ad9a3bb86097bfe0679d9` and rustpush commit
`b3c96c23e1aae78d1229ebaccb12027624f1eaff`. Additional inspected Apple sources
include the
[peer conversion helpers](https://github.com/apple-oss-distributions/Security/blob/db15acbe6a7f257a859ad9a3bb86097bfe0679d9/keychain/TrustedPeersHelper/Utils.swift),
[trusted peer container](https://github.com/apple-oss-distributions/Security/blob/db15acbe6a7f257a859ad9a3bb86097bfe0679d9/keychain/TrustedPeersHelper/Container.swift),
and [CKKS key reader](https://github.com/apple-oss-distributions/Security/blob/db15acbe6a7f257a859ad9a3bb86097bfe0679d9/keychain/ckks/CKKSKeychainBackedKey.m).
The separate
[rustpush keychain implementation](https://github.com/OpenBubbles/rustpush/blob/b3c96c23e1aae78d1229ebaccb12027624f1eaff/src/icloud/keychain.rs)
was also inspected. These are source evidence for specific constructions and
consumer checks, not an endorsement or an Apple protocol specification.

Installed dependency behavior was inspected with Python **3.14.7**, `srp`
**1.0.22**, and `cryptography` **48.0.1**. Relevant primary references are
[RFC 5054](https://www.rfc-editor.org/rfc/rfc5054),
[cryptography's GCM API](https://cryptography.io/en/48.0.1/hazmat/primitives/symmetric-encryption/),
and [Python cancellation semantics](https://docs.python.org/3.14/library/asyncio-task.html#shielding-from-cancellation).
RFC 5054 informs the fixed-group arithmetic and safety checks; Apple recovery is
not asserted to use its TLS wire format.
