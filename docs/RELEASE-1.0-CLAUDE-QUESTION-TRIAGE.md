# Independent source disposition of Claude's six questions

Review input: `RELEASE-1.0-CLAUDE-REVIEW.json`, SHA-256
`f443e1fff6159f44bad50df0b9b841ceba4d6083b308dccce2bb315e256dc1c3`.
Canonical source: `c31c220563ae55d469bbf530fa77dd2f80583910`.
This follow-up read current source and relevant test bodies. It ran no tests,
provider requests or product code and changed no product bytes. Claude's review
remains an independent AI review with partial coverage, not qualified external
assurance. No confirmed actionable defect was established by these questions.

## 1. Compact P-256 signature key identifier

Disposition: interoperability/provenance question remains open; no demonstrated
authentication bypass. `cloudkit/pcs.py::_signature_key_id_matches` begins at
line 552. The identifier filters a locally held key, while signature verification
still uses that full held key (inner lines 823–835; outer lines 863–878).
`tests/test_findmy_pcs_hardening.py` lines 455–499 include positive exact-encoding
controls and inverse-y negative cases: a matching bare x does not bypass ECDSA.
These are generated/local controls. Their `producer32` fixture label is not an
independent Apple-produced vector. Retain the independent-format question.

## 2. Backup exclusion of the witness cache

Disposition: already disclosed support boundary. Current wiring is
`findmy_recovery_guard.py` lines 602–608: ledger under `.storage`, witness under
`.cache`. The exact ordinary Supervisor partial-restore packet observed witness
exclusion and automatic review/refusal for its pinned versions. Future/add-on,
encrypted/cloud/full-system or complete joint snapshots are not qualified by
that observation. A backup containing both ledger and witness inherits the
documented joint-snapshot limitation; it is not evidence of a new bypass in the
accepted ordinary experiment. Broader variants may be explicitly unsupported.

## 3. Per-account rather than whole-ledger witness

Disposition: intentional account isolation, not a defect. The digest covers
identity and the account entry/generation; each mutation sets a fresh generation
before writing ledger and witness (`findmy_recovery_guard.py` lines 299–341,
471–480). An exact unchanged account entry introduces no lost account history;
a same-counter ABA rollback has a different generation. Read test bodies for
account-isolated review/reset and
`test_rollback_with_retained_witness_and_same_counter_aba_is_detected` (line 582).
Do not expand the safeguard into a whole-ledger monotonicity promise.

## 4. Persistence failure after an authenticated proof

Disposition: conservative storage-failure handling; no proven unsafe retry.
Claude's statement that unwind always records uncertainty is too broad.

`keychain/recovery.py` lines 492–511 awaits `attempt.verified()` before obtaining
the session key or decrypting/caching material. A failure propagates unchanged.
`findmy_setup.py` lines 834–847 records an in-memory conservative outcome and
unsets the active attempt; storage/review error mapping stops this setup path.
The transaction writes ledger first and witness second (guard lines 471–480).
If a ledger write failed before commit, pending state may be reclassified as
uncertain when cleanup can persist it. If ledger commit succeeded but witness
failed, the mismatch requires review; unwind explicitly refuses auto-repair
(lines 521–530). Some I/O failures occur after replace, so the exact durable
state depends on the failure boundary. It is inaccurate to assert one universal
durable uncertain count. No new proof is automatically dispatched.

Existing test bodies cover unchanged verified-hook error propagation
(`test_findmy_recovery_protocol.py` lines 269–275), cancellation after durable
verified commit (`test_findmy_recovery_guard.py` lines 380–404), conservative
storage failures (407–451), missing-witness refusal at verified completion
(622–636), and witness commit failure before dispatch (639–678). The precise
combined post-authenticated-proof disk-fault matrix was not newly executed in
this review. That is a coverage limit, not a confirmed defect or a reason for a
broad suite rerun.

## 5. PCS diagnostic reason propagation

Disposition: the hypothesized wrapper loss was not found on the primary zone
discovery failure path. `pcs.py` lines 999–1007 creates the exact PCSError with
fixed reason metadata. `beacons.py::zone_keys` returns `unwrap_zone` directly at
869; `fetch_accessories` awaits it at 887; `icloud.py::accessories` awaits the
store at 318–321. None wraps that exception before `findmy_setup.py::discover`
logs its fixed reason at 917–935.

Per-record decryption errors are deliberately counted/skipped to preserve
unaffected records (`beacons.py` 1191–1207); absent/unreadable zone defaults
return no defaults (991–999). Those paths do not promise an aggregate exact
outer-auth diagnostic exception. `records.py` represents record values and
adds no exception wrapper on this route. Exact-type reason filtering is a
deliberate redaction boundary, not an accidental subclass bug: tests at
`test_findmy_setup.py` 785–827 explicitly reject subclass/property/impostor
metadata, and 831–851 verify fixed reason logging without reproof. Do not
relax that sanitizer merely to obtain more diagnostic detail.

## 6. sys.exception during cleanup

Disposition: supported language/runtime mechanism, not a new defect. The use
is explicit in runtime onboarding lines 101–112 and guard lines 511–530. It
preserves a primary error while deciding whether a cleanup exception may
replace it. [Python's sys.exception documentation](https://docs.python.org/3.14/library/sys.html#sys.exception)
and [finally-clause reference](https://docs.python.org/3.14/reference/compound_stmts.html#finally-clause)
describe the handled-exception and exception-cleanup context; the API was added
in Python 3.11 and exists in the recorded 3.14 runtime. The existing cleanup
failure regression at `test_findmy_recovery_protocol.py` 410–432 requires the
original structured transient outcome to survive a clone-close failure.
No new Mac Python/provider import or compatibility test was run here.

## Remaining assurance

The six changed paths have received a second-model source review with concrete
coverage disclosures, and this follow-up found no confirmed fix. Independently
produced format vectors, full membership/revocation trust assurance, final
target runtime-version capture remain separate. The maintainer accepted Claude AI review with these documented limits for 1.0 on October 22, 2026; no qualified-human assurance or producer-vector evidence is claimed. Source/license/service
permission decisions are not changed by the review result.
