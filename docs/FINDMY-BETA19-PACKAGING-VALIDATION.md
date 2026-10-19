# Find My beta 19 packaging validation

Date: October 19, 2026. Branch: `codex/findmy-beta`.
This technical record tracks the pre-release checkpoints for beta 19. Use the
[beta 19 validation summary](BETA19-VALIDATION.md) for the release scope.

## What is promoted

The research integration independently demonstrated HA OS authentication,
item-key recovery and automatic AirTag report polling. Its controlled report
comparison isolated a report-header compatibility issue: the same account,
identity, OTP and singleton request body returned reports with the report-service
headers and no results with the older headers. The HomeCircle candidate now uses
that profile and bounded gzip decoding without changing SDK report request bodies.

Research success is separate from acceptance of the packaged HomeCircle setup.
An accepted cloud request, or an encrypted report count, does not prove a current
physical position. HomeCircle retains the source report timestamp and estimated
accuracy separately from the HA poll time.

## Packaged implementation

- Every new Apple account setup receives independent identifiers and local Mac
  identity provisioning. The identity remains bound to its own report credential.
  A saved Mac account restores that identity without provisioning or another
  password. Explicit reconnect of an older development identity prepares the new
  runtime while leaving the saved connection intact until confirmation and
  authenticated account matching.
- Setup acquires the public runtime before asking for a password. Apple library
  bytes are fetched from the pinned Apple installer, hash verified and cached
  locally. Fixed byte ranges and hashes replace external extraction commands.
  No archive paths are materialized.
- The MIT emulator source and license are packaged. Unicorn is a pinned HA
  requirement. The release contains no Apple binary, emulator wheel, SDK wheel,
  laboratory checkout, machine state, account data or item keys.
- A child process handles the native engine with private bounded IPC, real time,
  operation timeouts, resource limits and cancellation/reaping. Provisioning
  transport verifies TLS and permits only lookup/start/finish. Errors expose
  fixed categories rather than protected response data.
- Discovery uses a separately authenticated unused recovery credential, matched
  to the current Apple account and borrowed identity. It does not delegate that
  credential, request a new verification, or transfer ownership of the provider.
- CloudKit uses the retained host UUID for its hardware identifier; the Apple
  device identifier is not parsed as a UUID. Mac GSA, verification and delegation
  declarations match the working profile. Binary and XML plist replies are
  supported without changing legacy XML-fragment handling.
- Account passwords, verification codes and device passcodes remain transient.
  Only explicit item selections and the minimized passwordless account session,
  including provisioning material, enter the encrypted local vault.
- Public prototype migration and Undo menus are removed. Protected local
  research assets are retained outside the release. Existing household and V2
  behavior remain outside this change.
- Sign-in failures retain only fixed phase/profile categories and bounded HTTP,
  Apple status, request-count and response media/size metadata. Authentication
  bodies are excluded. This diagnostic update changes no authentication body or
  automatic retry behavior. Dependency logging uses namespace sinks instead of
  scanning module files on HA's event loop.

See the packaged
[runtime provenance](../custom_components/homecircle/_findmy_runtime/PROVENANCE.md)
for source revisions, licenses and public-library hashes.

## Validation record

The frozen candidate has passed:

- 1019 HomeCircle backend regression tests in the current full suite, including
  real HA config/options flows and passive poll-observation controls.
- 48 focused progress/lifecycle and grant-security tests; this is a separate
  run, not an additional count of distinct backend tests.
- 109 frontend regression tests from the unchanged frontend packaging baseline,
  including Find My progress and explicit selection.
- 873 upstream SDK tests against the vendored namespace at the packaging
  baseline. The SDK runner allows loopback fixtures and denies external network
  connections. Neither this SDK suite nor the frontend suite was rerun after the
  later diagnostic Python updates; they retain the prior feature coverage.
- Current ZIP installation, upgrade, restart, removal and post-removal restart
  in separate disposable HA Core processes. These are local Core tests, not
  physical HA OS acceptance.
- ZIP inventory, deterministic metadata, allowlisted recursive runtime packaging,
  import closure, traversal/symlink/duplicate refusal and private-state exclusion.
- Isolated actual-ZIP imports in a fresh process whose working directory is
  outside the checkout; the packaged provider, bootstrap, worker and emulator
  import without a development tree or SDK wheel.
- Bootstrap fixtures verifying the exact retained public installer bytes, all
  intermediate hashes, Range/full-response handling, TLS settings, corrupt-cache
  refusal, atomic permissions and cancellation cleanup.
- Synthetic account independence, fresh provisioning, same-identity restoration,
  OTP rollover, unused recovery credential binding, 600 encrypted report
  decryption, fixed empty-response handling, gzip bounds and worker lifetime.
- Public-file privacy scanning of 280 files, Ruff and `git diff --check`.

The earlier runtime-proof ZIP passed fresh runtime acquisition and anonymous
provisioning in an isolated process. One public Apple download and three provisioning requests
completed; the final HTTP status was 200 and Apple status was zero. The native
worker generated an OTP, an ephemeral encrypted vault round-trip passed, and a
cold provider restored the same identifiers and machine ID. Four owned workers
were reaped and temporary storage was removed. No Apple account was signed in,
and no existing account state, item keys or locations were read by that check.

Fresh provisioning exposed a storage-format regression: the native store
legitimately includes empty files alongside its credential file. The candidate
now preserves those files in serialization and cold restoration, while requiring
at least one nonempty store file and retaining all size/path validation.

The anonymous runtime proof used archive SHA-256
`519fd7cbafa3df8c2d6e202f49302c5a0855cc470c9d5fceac1909dfb082e2a6`.
The prior installed candidate added only `strings.json` and `translations/en.json`
changes, producing SHA-256
`0f6c4d07f820ce94b3baedc1eb67f40390d40233412f2a84be55a594b44d9fdf`.
All 109 files of that artifact were verified after installation on the actual
HA OS Raspberry Pi. Following an HA restart, normal HomeCircle setup prepared
the native identity and reached an empty Apple login form. The translation
correction's HA restart completed: the browser disconnected and reconnected, HomeCircle
loaded as `0.1.0-beta.19`, and Configure opened options initialization.

Two later phone sign-in attempts on that installed artifact received GSA HTTP
429 without `Retry-After`. Their SRP phase was not recorded. The refusal does not
establish its scope or cause; no account or locations were saved by either attempt.

Installed acceptance archive: 109 files, version `0.1.0-beta.19`.
SHA-256: `5aef22dd4dffaca961041d585280bdb8de14f268d16c449ce1725e9baff9ca46`.
It changes only `findmy_setup.py`, `_vendor_findmy/errors.py` and
`_vendor_findmy/reports/account.py` from the prior installed artifact. The native
emulator, provider, bootstrap and worker are unchanged from the anonymous proof.
Actual-ZIP readiness and disposable Core lifecycle checks pass. All 109 files of
this diagnostic artifact are installed and verified on the actual HA OS Pi,
with a source rollback copy. Deployment left configuration entries, account
vaults, the research FindMy component and V2 unchanged. Its HA restart completed;
the integration loaded as `0.1.0-beta.19` with Configure available. The earlier
SDK filesystem-scan warning was absent from the observed startup logs.

The user's subsequent phone **Reconnect existing items** completed and saved
successfully on this artifact. Provider diagnostics showed connected status,
two discovered and two available trackers, successful API poll transport and no error.
A read-only in-memory check independently confirmed one saved `aniMac` account,
two selected items and two valid retained GPS reports with estimated accuracy of 25–63 m.
The login state retained only the DSID and report grant; no password or
account-info payload was present. Both selected items matched their existing registry
entries exactly, with no duplicates. No exact coordinates, keys or report times
were retained in the validation evidence.

These retained reports are older: one was under two hours old and the other under
24 hours old. Polling preserves earlier reports when Apple returns no new rows;
successful transport and valid retained reports therefore do not prove that the
packaged session received and decoded report rows. At that checkpoint, newly
decoded rows had not been observed. No fresh movement or current physical
position was proven.
The flow reused existing item selections, so fresh
item discovery and key recovery were unvalidated at that checkpoint. Success
after the earlier 429 refusals does not establish that diagnostics changed
Apple's acceptance behavior.

Passwordless reuse after an actual HA restart passed. An automatic API poll
after restart returned connected status with both retained trackers available and no
error, without another login. A RAM-only comparison verified unchanged account
metadata, client identifiers, machine state, report grant, vault encryption key,
accessory keys, entity registry and configured associations. Password and
transient grants remained absent, both GPS reports remained valid and source
times did not go backward. No duplicate trackers appeared. The comparison key
was discarded and only aggregate checks were saved. History rows were not read,
so history continuity is not claimed. No newer source report arrived during
this restart check; freshness and movement acceptance remain pending.

The intermediate, never-installed passive-observation archive has SHA-256
`2186f070d2a57b738dbbe6fedbfb9696b0fe52f718fa5dec91a67f8265b8ed94`
and 109 files. It differs from the installed `5aef22dd…` artifact only in
`diagnostics.py`, `findmy_provider.py` and `findmy_reports.py`. It adds fixed
passive observations of the latest account polls without additional requests or
changes to request data, timing or saved reports. Logical SDK fetch calls are
separate from HTTP counts. Decoded counts represent non-null latest-per-key
values returned by the SDK, not every historical or raw report. Returned valid
item reports, first/newer reports and retained previous reports have separate
counters; a returned report can be older than the retained one. Failure and
cancellation replace prior success status and clear item-outcome counts while
preserving observed partial fetch counts. Success describes the account client's
poll, separately from later vault writes and tracker updates. Diagnostics export
only validated, bounded counts and fixed status categories, with no account/item identifiers,
coordinates, keys, report times or exception bodies.

That archive passed 1013 backend and 42 focused tests, actual-ZIP zero-network
readiness and all five disposable Core lifecycle phases. It was not installed.
The reconnect and passwordless-restart acceptance above applies to `5aef22dd…`;
newly decoded rows and full fresh discovery were still unobserved at that checkpoint.

## Pre-password progress fix

Fresh discovery on the installed `5aef22dd…` build stalled before the email and
password form. The owner reproduced this on the phone, and an independent
unsaved browser flow reproduced it and was closed without saving. No password
or code was submitted for those attempts, and an Apple cause was not established.
A restored native identity completes preparation without library, worker or
network calls or an event-loop suspension in the synthetic control.

The fix starts setup work eagerly and opens the next form directly when work
has already completed, passing no input to that form. This avoids both a late
frontend progress subscription and replay of consent or code input. Work that
actually waits retains HA's progress callback path. Missing or cancelled work
ends with the fixed sign-in-state error instead of advancing to an uncompleted
step. Real HA FlowManager regression tests cover the immediate login form with
no authentication calls, asynchronous completion, cancellation and expiry;
existing grant and vault security checks remain enforced.

Live-acceptance archive SHA-256:
`545115488bb37b81faeaefd7a85a41136616a1c7c086bfdf7221d28c34889e21`.
It contains 109 files and differs from `2186f070…` only in `findmy_flow.py`.
It passed 1019 backend tests, 48 focused tests, actual-ZIP zero-network readiness,
all five disposable Core lifecycle phases, Ruff and the 280-file privacy scan.
The full-suite duration was not collected.

All 109 files of `54511548…` are now installed and verified on the actual Pi,
with a rollback copy. After an authorized HA restart, HomeCircle loaded as beta
19 with Configure available. The same Manage existing account → Discover →
consent path immediately opened the Apple sign-in form with both fields empty.
No password or code was entered, and the proof flow was closed without saving.
This passes live acceptance of the pre-password fix; that UI-only check did not
itself establish successful fresh authentication or recovery.

A RAM-only comparison across that restart passed for account metadata, client
identifiers, machine state, report grant, vault encryption key, accessory keys,
selections, registry identities and configured associations. Two retained GPS
reports remained valid and nondecreasing, without duplicate trackers or a newer
source report during the comparison. Password and transient grants remained
absent. The observer discarded its comparison material. History continuity was
not checked.

The subsequent allowlisted diagnostics download confirms actual report delivery
on `54511548…`. Its automatic startup poll completed successfully using the
unchanged saved identity and report grant: nine logical SDK fetch calls returned
106 non-null latest-per-key decoded values, with valid returned reports for both
selected items. These are SDK return-value counts, not 106 distinct physical
reports or an HTTP request count. Neither item's source report advanced, no item
fell back to a retained previous report in that poll, and neither lacked a
report. No extra or manual poll was used. This passes packaged report-delivery
and passwordless restart acceptance. Full fresh recovery/discovery and movement
freshness were still pending at that startup checkpoint.

The owner then confirmed completing and saving the requested full **Discover /
change selected items** flow on the phone. An independent in-memory state check
confirmed one native account, two selected items, two valid saved reports, exact
registry matches and no duplicate trackers. Password and transient grants were
absent, and the vault write occurred after the fix restart. The new client then
completed an automatic poll with nine logical SDK fetch calls, 105 latest-per-key
decoded values and valid returned reports for both selected items. No item used
a cached fallback in that poll. This combines owner confirmation of full recovery
and discovery with independent saved-state and post-save delivery evidence;
the functional beta acceptance gates have passed.

## Canonical release artifact

The canonical release ZIP contains 109 files and has SHA-256
`5f20d536e1b5378bef7f0b972bbfbc7ced911063aea16a0a8f56d2ffa1210cd2`.
It differs from the live-accepted `545115488bb37b81faeaefd7a85a41136616a1c7c086bfdf7221d28c34889e21`
archive only by removal of extra empty EOF lines in
`_findmy_runtime/__init__.py` and `_findmy_runtime/PROVENANCE.md`.
Python ASTs, including line attributes, are identical; the provenance text also
differs only at EOF. No runtime behavior or executable line positions changed.
The safe equivalence receipt is retained in ignored local work storage as
`work/beta19-release-validation/eof-format-equivalence.json`.
The historical archive hashes above retain their original proof scope.

The ignored `work/beta19-native-package-validation/` directory holds safe
machine-readable runtime receipts. It contains no account credentials or
provisioned machine state. The exact archive inventory and SHA-256 are generated
in `release/inventory.json`.

## Release preparation and known limitations

Fresh recovery/discovery, explicit selection, saved identity/session reuse,
restart preservation and actual decoded report delivery have passed for the
tested HA OS setup. The clean public-source snapshot and aligned release
documentation are prepared separately from the retained research history.
GitHub asset and HACS distribution checks follow prerelease creation and are
recorded separately from these pre-tag acceptance checks.

Neither selected item's source report advanced in the observed post-save poll.
New physical movement, current-position freshness and delivery latency are not
proven. These remain disclosed experimental-beta limitations, not a requirement
for another mandatory movement cycle before this beta can be published.

No movement acceptance is inferred from synthetic fixtures, anonymous
provisioning, report counts or the older research integration.
