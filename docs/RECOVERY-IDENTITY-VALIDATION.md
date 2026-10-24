# Stable preparation: recovery safeguards and identity continuity

October 19, 2026. Local uncommitted candidate on `codex/ruby-person-card`, based
on `373203a85da0e1f9c4d7d3c2eabfd31663475bee`. This follows the
[combined isolation checkpoint](STABLE-ISOLATION-VALIDATION.md). The published
experimental release remains beta 19. No live HA configuration, Apple account,
version, tag, commit, push or publication was changed.

## Recovery safeguards

Actual recovery setup now requires a durable local guard bound to the
authenticated account DSID. It reserves a submission after PET, challenge and
headers are prepared, immediately before the recovery-proof POST. Refused,
uncertain and server-verified outcomes are recorded separately; pre-dispatch
failures do not consume the unresolved threshold. Same-account attempts serialize
across flows/processes, and different accounts remain independent. Redirects and
automatic retries are disabled for that proof POST.

The owner-only ledger uses restrictive permissions, no-follow filesystem checks,
atomic replacement, file/directory synchronization and cancellation-safe storage
completion. Unsafe, corrupt or unwritable storage prevents another proof.
Crashes, cancellation and ambiguous responses after potential submission remain
uncertain. Its local threshold of three unresolved exchanges persists across
new flows, reconnect, restart, Disconnect and integration removal. An explicit
administrator acknowledgment clears local unresolved counts, retaining verified
counts; it never submits a proof and says nothing about Apple's remaining retry
allowance. Existing report polling does not depend on guard availability.

Fixed structured errors distinguish credential/PET, pre-proof network/protocol,
refused, uncertain and verified-material failures. A verified recovery can finish
a failed material/directory/PCS download using in-memory cached material only for
the same authenticated account and exact escrow record. The resume form submits
no new passcode proof. Setup close/expiry releases those caches; memory
zeroization is not claimed. Accessory discovery retries after keys are recovered
also retain the existing no-new-proof behavior.

## Selection and identity

The item picker preselects current items and the confirmation lists removals.
An encrypted account-bound ledger retains keyed commitments of the exact master
key and both rolling-key seeds, plus allowlisted identity/display settings. It
does not retain omitted tracking keys, coordinates or reports. Matching requires
all three secrets under the authenticated account. Changed names or Apple record
identifiers cannot by themselves transfer identity. Ambiguous proofs are refused;
a reused record identifier with different keys receives a different identity.

Proven legacy tracker IDs, unique IDs, Person references and display preferences
survive omission/reselection and identifier changes when sufficient original key
evidence exists. No retrospective match is inferred from names, registry history
or private prototype state. Disconnect removes this identity ledger with its
account vault; backup copies and the separate recovery guard have different
retention, documented in [privacy](PRIVACY.md) and [setup](FINDMY-SETUP.md).

Confirmed fresh/saved/staged selection and Disconnect serialize account writes,
check current ownership/revisions and publish coherent HA data/options. Cancellation
drains the transaction, rollback restores only an owned snapshot, and a superseded
connection is not resurrected. Staged household saves lock accounts in order and
keep the final household result in the same transaction. Concurrent new accounts
merge the latest confirmed account map and reject duplicate authenticated
accounts. Older household/options/reconfigure dialogs cannot restore later
removed items or disconnected accounts.

## Validation

The final 112-file local ZIP retains manifest `0.1.0-beta.19` because final
versioning is undecided. Its SHA-256 is:

`12920d496da1417b813fe301cddca12a6fb7b940dcc02378930194e39cc17970`

Final checks passed:

- **1,221 backend tests**, with one optional test skipped because its public Apple
  installer fixture is not retained. The suite disables network sockets by
  default. Recovery, identity, actual HA options/reconfigure, rollback,
  cancellation, concurrent-account and transient-secret cleanup cases are covered.
- **110 frontend tests**, a frontend build and Prettier. The new picker regression
  verifies retained preselection and deliberate clearing; frontend production
  source is unchanged.
- Ruff across integration/tests, whitespace checks, and the public-file guard
  across 301 files, with no flagged patterns. Automated scans do not replace
  manual privacy review.
- Exact archive/inventory/source matching and fresh-process imports of eight
  entry/provider/SDK/safeguard modules from the extracted ZIP with network
  connections prohibited; private SRP modes load without changing ordinary flags.
- Separate-process disposable Core install, version-fixture upgrade, restart,
  removal and post-removal restart. Unrelated frontend resources survive and the
  removed integration's static bundle is absent. Temporary configurations are
  removed. The older version-only fixture is not a canonical published-beta
  upgrade or HACS test.
- Independent source review of recovery boundaries and selection transactions,
  with focused suites repeated after the resulting fixes. This is not a formal
  cryptographic or external platform audit.

An independent four-process encrypted-vault test saved two synthetic accessories,
omitted one, rediscovered it under a changed Apple identifier/name, and reloaded
the final vault. The same tracker ID, unique ID and display preferences survived.
Omitted raw keys were absent; changing any one of the three secrets prevented
aliasing, and a foreign account could not reuse the ledger. Each process blocked
network connections/resolution and the temporary vault was removed. This tests
helper/vault persistence, not an actual HA upgrade or Apple acceptance.

The Ruby Person/item projection fix remains covered. The frozen published ZIP
and review inputs retain their prior hashes. No private account, key, coordinate
or research-history data was copied into source or package. Development receipts,
logs, reproducible persistence/import scripts, source snapshot and candidate
archive/inventory remain in `work/stable-recovery-identity-validation/`.

## Limits and remaining gates

These checks use synthetic data and the local macOS arm64/Core 2026.9.4 runtime.
They do not establish Apple's server-side allowance, live recovery acceptance,
a formal cryptographic review, broad native platform support, long-term polling
or movement parity, a canonical published-beta/locally-patched-state upgrade,
HACS acceptance or physical DAKboard acceptance. No deliberate wrong owner
passcodes were tested. The private SRP loader still requires a file-backed
installed dependency. The [stable checklist](STABLE-RELEASE-CHECKLIST.md) retains
hardening, independent review, platform, field, upgrade, licensing/service-use
and final release decisions.
