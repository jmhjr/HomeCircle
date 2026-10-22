# HomeCircle 1.0 release plan

Started October 20, 2026. The target is `v1.0.0`; the current published release
remains experimental `v0.1.0-beta.20`. This is an execution tracker, not a stable
release declaration. Check a task only after linking its exact evidence. Retain
failed attempts and record any accepted scope change instead of deleting a gate.

## Current fixed candidate evidence

Source `ad9b83676bdfafcfc3848cc9a974b63c8742a020` and package `f181e6300f15d8977817a552db90d35caf0edc869067ebeea815c7be1df0248e` include the activity initialization
correction. The [private upgrade record](RELEASE-1.0-PRIVATE-UPGRADE.md) retains
its scoped ARM64 installation-copy upgrade/restart and separate 35-test focused
native result. [Fixed-candidate ordinary restore](RELEASE-1.0-FIXED-ORDINARY-RESTORE.md)
now binds run 39824890930: 45 fixture contracts, four managed amd64 HAOS phases and
17 independent consumer contracts passed for these exact bytes. Person links,
explicit source selections, activity/Recorder cohorts and automatic guard
review/refusal survived ordinary partial restore and restart.

Earlier source/package results below retain their original scopes. The full
native package suite has not yet been repeated for f181; that is the next
engineering gate. Advertised backup variants and other acceptance/disposition
gates remain open. This evidence is not a stable release declaration.

## Starting point and support proposal

- Public main: `bfabadd0b7a6b7c6c6a5a6583130d4fde4fef7ba`.
- Published beta 20: `d02a9bdb9027cb51c99165a09ba50d5b175f5fb9`; ZIP SHA-256
  `fc0b365d9688459504f874af5c38393e24145d657f15f1def8ada9184f363285`.
  Its hardening is not yet consolidated onto main.
- Separate notice correction: `9466eef45ecac16f05f25d4455d705383f7c91ff`.
  Five text files change; runtime bytes remain unchanged. Its archive check
  passed, but it is not a published release or legal clearance.
- The [October 20 readiness audit](https://github.com/jmhjr/HomeCircle/blob/35d4c3d184b810694c1bdd66778587f08a6d2e5b/docs/BETA20-READINESS-PROVENANCE-AUDIT.md)
  and [detailed checklist](https://github.com/jmhjr/HomeCircle/blob/35d4c3d184b810694c1bdd66778587f08a6d2e5b/docs/STABLE-RELEASE-CHECKLIST.md)
  retain completed and historical evidence. This plan does not repeat every
  earlier result or broaden its scope.

Proposed 1.0 core: UI setup using explicitly selected HA People/trackers,
household/place rules, dashboard/map, existing picture/history interfaces and
implemented opt-in map services. No new feature family is required. Advertised
installation targets would be official **HAOS and Home Assistant Container on
amd64 and ARM64**, with minimum Core **2026.9.4** and qualification against
**2026.10.2**, the current recorded target. This is a proposed support contract;
existing evidence does not qualify every combination or future Core release.
The Ubuntu/glibc test remains a separately identified reference environment.

On October 20, 2026 the maintainer selected **both direct Apple Find My and
direct Life360 for 1.0**, with their validation to be completed. Provider-independent
HA entity selection remains the core. This shipping-scope decision activates
both providers' account, dependency, permission and applicable cryptographic
gates; it does not assert those gates have passed. The proposed platform matrix
and installed-upgrade baseline policy still need final acceptance.

## Execution and evidence rules

Agent means implementation, local/disposable validation and documentation.
Maintainer means product/support decisions and final acceptance. Owner means
the account/device participant. Specialist means an independent qualified
reviewer for the identified cryptographic or licensing question; another agent
review does not silently substitute for that requirement. Owner/specialist
inputs may remain pending while independent engineering work proceeds.

Every acceptance receipt records source revision, ZIP/inventory hashes, target,
versions, named cases, outcome and cleanup. Evidence remains attached to its
tested bytes. Reuse applicable historical evidence, then run affected checks for
new changes. Run the complete final suite once on the frozen RC baseline;
repeat only after changes or a specific unresolved failure justifies it.
Infrastructure failures receive one bounded diagnosis before any reasoned retry.

## Ordered tracker

| Stage | Current status / dependency | Responsible | Completion evidence |
| --- | --- | --- | --- |
| 1. Freeze scope and support | Both direct providers selected October 20; platform/support proposal open | Maintainer, agent records | Signed-off feature/provider list, supported target matrix, upgrade baselines, exclusions and `1.0.0` naming |
| 2. Consolidate release source and blockers | Clean source in draft PR #36; focused fixes independently reviewed; exact-source native suite passed | Agent; maintainer review | Clean canonical release branch, reviewed product-only diff, notices included, recorded defect dispositions |
| 3. Close provenance and provider decisions | Open; inventory and notice preview complete; depends on stage 1 for final scope | Maintainer/specialist, agent supplies evidence | Exact-source/installed-dependency notices and obligations disposition; source/permission/service/name decisions for shipped scope |
| 4. Enabled backup/restore safety | Recovery-guard and scoped ordinary Person/activity partial restore passed; advertised backup variants remain open | Agent | Actual Person identities/links and product activity B/M/R preserved under normal requirements/default conditions; arrival-gap/pending-shutdown and broader variants remain unqualified |
| 5. Cryptographic and format assurance | Synthetic independent source review complete; external assurance open if Find My ships | Specialist, agent fixes; owner only for controlled acceptance | Review disposition, independent format vectors, authenticated rejection/recovery cases and fixes rechecked |
| 6. Advertised compatibility | Four native QA-container lifecycle cells and both scoped managed ARM endpoints passed; fresh consumer/RC support gates open | Agent | All advertised cells have candidate dependency/install/start/restart evidence; unsupported cells excluded explicitly |
| 7. Real-account acceptance | Initial connections and saved-session restart witnessed; remaining lifecycle and stages 3/5 disposition open | Owner, agent guides/records | Controlled setup, discovery, selections, session lifecycle and successful recovery receipts without deliberately wrong passcodes |
| 8. Sustained field acceptance | Earlier observations exist; final scope incomplete; depends on stages 6/7 as applicable | Owner observes, agent analyzes | Agreed observation window and movement/outage/renewal/staleness cases with genuine source-report times |
| 9. Dashboard, access and privacy | Exact-source privacy and scoped desktop Safari picture checks passed; remaining final acceptance open | Agent plus owner for real displays | Desktop/mobile/physical display, admin/household permissions, privacy/deletion, real attribution/request checks |
| 10. Real installed-state upgrade | Synthetic published-beta transport complete; fresh installed-state acceptance open | Agent, owner/maintainer for actual instance | Fresh baseline inspection/backup, upgrade/rollback/removal receipts, preserved storage/Recorder/resource identities |
| 11. Finish user and support documents | Open; draft in parallel, finalize after scope/results | Agent, maintainer accepts | Consistent installation/privacy/support/migration/recovery documents and known limitations |
| 12. Freeze and qualify RC | Pending stages 1–11 or explicit tested exclusions | Agent, maintainer accepts | Identified RC, exact artifact, final check receipt and bounded RC acceptance with no unresolved blockers |
| 13. Publish and verify 1.0.0 | Pending RC acceptance | Agent executes, maintainer release disposition | Stable tag/package/inventory/release notes, public-byte verification and genuine HACS install/upgrade restart proof |

### 1. Scope and support decision

- [ ] Record included features, both direct-provider dispositions and the
  compatibility matrix. Identify what is experimental, deferred or unsupported.
- [ ] Set `1.0.0` consistently in current planning and later release metadata.
  Preserve older `0.1.0` milestones as dated history.
- [ ] Choose the supported upgrade baselines and define treatment of locally
  patched installations. Define the support/security-reporting route.

### 2. Canonical source and defect triage

- [x] Create a clean release branch using the actual main/product ancestry: [draft PR #36](https://github.com/jmhjr/HomeCircle/pull/36), tested source `9bf03eb45d2cf43274074534e9dfe2de841f4011`.
  Review and consolidate accepted beta 20 hardening plus the notice correction.
  Do not merge the validation branch wholesale: it also carries CI payloads,
  runner workarounds and evidence that require separate disposition.
- [x] Inventory remaining tracked work and distinguish confirmed defect,
  acceptance case and optional enhancement. The [roadmap triage](RELEASE-1.0-TRIAGE.md) records these dispositions; unrelated working changes are preserved.
- [x] Fix the confirmed picture-picker filename continuity issue: beta 20's
  `settings-dialog.js` clears the file input after successful decoding while the
  crop remains active. Verify filename while cropping, failed upload retention,
  save/remove/cancel clearing and selection of the same file again. The [focused validation](PICTURE-FILENAME-VALIDATION.md) records before/after failure proof and 110 passing frontend tests. The [scoped Safari check](PICTURE-BROWSER-VALIDATION.md) also passed; native-picker completion, mobile and physical-display acceptance remain open.
- [x] Triage the roadmap's source oscillation, passive-zone legacy fallback,
  cached-city projection and shutdown cache-save cases against the consolidated
  code. The [triage record](RELEASE-1.0-TRIAGE.md) distinguishes the confirmed corrections from retained policies. The [exact-source Linux qualification](RELEASE-1.0-CORE-VALIDATION.md) passed all 1,452 backend tests, including the new regressions.

Status icons, additional landscape polish, trip trails, traffic/ETA, adaptive
freshness and additional providers remain optional post-1.0 work unless the
maintainer changes the scope. Do not convert the old wishlist into new blockers.

### 3. Notices, source obligations and permission

- [x] Carry the GrandSlam, Unicorn supplemental and Construct notice correction
  into the actual candidate and verify its installed integration paths:
  [exact-package notice witness](RELEASE-1.0-NOTICE-INSTALLATION.md). Individual
  dependency-wheel layouts and source/permission obligations remain separate.
- [ ] Record disposition of the unlicensed gist ancestry/independent
  implementation basis and GrandSlam's literal unfilled license fields.
- [ ] Resolve Unicorn binding/core attribution and applicable GPLv2 source or
  distribution obligations; address the fetched wheel's missing material.
  Retaining supplemental text alone does not close these questions.
- [ ] Resolve fetched pyelftools/Construct notice placement and any upstream
  distribution remedy. Bind the final inventory to the actual resolved artifacts.
- [ ] For shipped providers, record assessment of the pinned Apple software's
  accompanying agreement, extraction/emulated use, applicable iCloud/Life360
  service permissions and public branding. Technical inventory is not permission.
- [ ] If an unresolved component is deferred, demonstrate its real exclusion
  and validate the resulting package/dependency behavior.

### 4. Enabled restore and rollback safety

The [first native attempt](ENABLED-RESTORE-VALIDATION.md) genuinely observed an
older enabled backup replacing guard three with its exact earlier two. Real
Supervisor backup/restore completed, but the operational phase timed out and
manual repair was not reached. That failure is retained; it is not restore
safety acceptance. The [prepared followup](ENABLED-RESTORE-PREPARED.md) completed all six operational
phases and manual repair, but automatic guard protection still failed. That
account-free offline partial scope is separate from default dependency
reinstallation and full-system recovery. The [exact development-artifact
investigation](RELEASE-1.0-HAOS-RESTORE.md) then completed the same six managed
phases and manual repair with C, independently reproducing guard rollback.

- [x] Complete and independently verify the exact-C prepared-dependency managed
  experiment, preserving all six phase, identity/history, byte and cleanup
  receipts and explicit negative automatic-safety disposition.

The subsequent [explicit-procedure investigations](RELEASE-1.0-INCOMPLETE-PILOTS.md#explicit-restore-procedure-eight-incomplete-runs) retain seven prior zero-phase negatives. The eighth run passed initialize,
initial restart, quarantine and mutate, including normal requirements and the
portrait correction, then failed host-held newest-guard retention. Its cause
remains unidentified; the full procedure is unaccepted at the October 21,
01:02 UTC cutoff. No product defect is inferred.

The October 21 [enabled saved-account investigation](RELEASE-1.0-ENABLED-RESTORE.md)
completed five enabled managed phases using real SDK-restorable fictional
sessions, a manifest-only QA dependency and prepared libraries. Four explicit
tracker joins, settings/place/picture, encrypted storage and independent Recorder
checks passed. Startup transport attempts were counted and denied; measured
recovery seams stayed zero. Older ledger bytes still returned before manual
external newest-guard repair. At that pre-fix checkpoint, the ordinary
unmodified/Person/activity-history and automatic rollback gates remained open.

- [x] Complete and independently replay the exact-source instrumented enabled
  saved-account trial, preserving default Supervisor conditions, original
  artifact and explicit negative automatic-safety disposition. The standalone
  evidence-consumer correction passed 32 contracts and the actual retained run.

The [recovery-guard correction](RELEASE-1.0-ROLLBACK-PROTECTION.md) records
per-account cache witnesses and fresh ledger generations. Missing or mismatched
continuity blocks guarded unlock until explicit account-specific review; normal
restart preserves a matching witness. Exact-source native run 39715519894 passed
1,728 backend tests (one existing optional skip), all 50 required functions and
122 frontend tests. Its 113-file runtime package is identical across source
`012a7e8` and tests-only isolation revision `57b0aaa`.

The [ordinary restore record](RELEASE-1.0-ORDINARY-RESTORE.md) retains R1–R4
failures and their bounded fixture investigations. [R5 run 39721983991](https://github.com/jmhjr/HomeCircle/actions/runs/39721983991)
passed all four enabled phases on amd64 HAOS/Core 2026.10.2/Supervisor 2026.10.3,
with the unchanged product and manifest, normal requirements and default
Supervisor conditions. Actual guard counts two, three, two, two did not regain
allowance: missing witnesses required review and both restored attempts were
refused before their bodies, including after restart. No manual guard repair,
post-restore acknowledgment or recovery dispatch occurred. Four explicit tracker
joins, settings/place/picture, encrypted storage, frontend bytes and Recorder
rollback/new recording survived. Independent frozen-consumer and peer audits
accepted the actual five-receipt packet; [public evidence and portable replay](https://github.com/jmhjr/HomeCircle/blob/8f28d5da33b7094355e84d5c8a23ee78463cecf3/native-ordinary-rollback-evidence/INDEX.md)
retain its bytes. All owned cleanup passed. A joint ledger/cache VM or complete
configuration snapshot still requires an external monotonic anchor.

- [x] Implement and independently verify the per-account continuity correction
  and native guard/review-flow regressions. Preserve the old rollback evidence
  and disclose the joint-snapshot limit; the linked ordinary trial now validates
  automatic restored review and refusal.
- [x] Rehearse an ordinary Supervisor partial backup with HomeCircle enabled,
  restore it and observe its first automatic startup and later restart in the
  disposable synthetic HAOS instance. Verify ordinary requirements, unchanged
  product bytes, four explicit tracker joins, settings/place/picture, encrypted
  storage, served frontend and Recorder continuity with no manual guard repair.
- [x] Verify genuine HA Person associations and product-generated HomeCircle
  activity through an ordinary synthetic partial restore and restart. The
  [Person/activity record](RELEASE-1.0-PERSON-ACTIVITY-RESTORE.md) binds native
  run 39777059627: one editable Person, two configured links versus one selected
  tracker, distinct active source, baseline/mutation/restored cohorts and normal
  durable stores. The original recovery, request, byte and cleanup gates passed.
  Native arrival-gap and deliberately pending-on-shutdown writes remain
  unqualified; other backup variants and real-account acceptance stay separate.
- [x] Restore an older snapshot after a newer fictional recovery guard exists
  in the explicitly instrumented synthetic fixture. [Run 39708377110](RELEASE-1.0-ENABLED-RESTORE.md)
  bound older ledger restoration and counted denied startup requests without a
  live recovery proof. Account-bound recovery authentication remains separate.
- [x] Fix the confirmed recovery-guard rollback issue and repeat its affected
  native and ordinary restore cases. The local continuity safeguard now refuses
  recovery after ordinary rollback; documented explicit review does not infer
  lost newer counts or reset Apple's allowance.
- [ ] Validate full-system/add-on/encrypted/cloud backup variants only where
  advertised, or record the exact unsupported variants. Existing prepared
  disabled-entry partial-restore evidence remains separate.

### 5. Independent security and format acceptance

The [assurance handoff](RELEASE-1.0-ASSURANCE-HANDOFF.md) identifies the exact
source, all 74 unchanged Find My Python members and the remaining trust/format
questions. It is prepared evidence, not completion of external assurance.

- [ ] Give the independent reviewer the identified source, prior findings,
  limits, threat boundaries and exact unresolved questions.
- [ ] Add independently sourced supported-format cases and safe unsupported/
  malformed rejection cases; retain authenticated peer/account/key binding,
  record integrity, resource bounds and cancellation checks.
- [ ] Resolve and recheck confirmed findings. Record residual risks and the
  explicit disposition of each; do not describe generated synthetic fixtures as
  independent real-format proof.

### 6. Compatibility qualification

The [exact-source minimum-Core amd64 run](RELEASE-1.0-CORE-VALIDATION.md) passed
1,452 backend and 110 frontend tests, 337-file privacy and the deterministic
113-file preview package. Its runtime scope is one official Container image;
it does not qualify the remaining advertised matrix by itself.
The [compatibility disposition](RELEASE-1.0-COMPATIBILITY.md) now records
minimum/current QA-container lifecycle passes on both CPUs, the exact-C
managed amd64 restore investigation and the [minimum-Core amd64 managed
startup/restart pass](RELEASE-1.0-MINIMUM-HAOS.md). The [eight consumer and seven
local ARM negatives](RELEASE-1.0-INCOMPLETE-PILOTS.md) remain preserved. The
subsequent [four native consumer entrypoint witnesses](RELEASE-1.0-INCOMPLETE-PILOTS.md#scoped-consumer-followup-four-native-cells-passed) passed prepared-cache startup/stop/restart at both
Core endpoints on both CPUs. Subsequent [ARM managed followups](RELEASE-1.0-INCOMPLETE-PILOTS.md#scoped-arm-managed-followup-both-core-endpoints-passed) passed normal requirements and startup/restart at both endpoints.
Fresh online consumer and broader release gates remain open.

- [x] Qualify exact-C scripted native Core lifecycle on amd64 and ARM64 at
  2026.9.4 and 2026.10.2: 12 focused cases and four separate Core processes per
  cell, preserved settings/source identity, exact served bytes and owned cleanup.

- [x] Verify normal managed dependency installation and exact-C enabled startup/
  restart on native amd64 HAOS 18.3/Supervisor 2026.10.2/Core 2026.9.4.
  Run 39504506480 preserved explicit selections, nonempty settings, identities
  and served bytes across a real restart with the external NIC closed.
  HACS, historical migration, removal and backup/restore were outside this run.

- [x] Witness the original consumer entrypoint on both native CPUs and both Core
  endpoints with prepared normal-config dependencies. Runs 39516737435 and
  39517742934 passed eight service starts with clean stops, exact installed/served
  bytes, settings/source/resource continuity, legitimate unload/setup, offline
  acceptance and owned cleanup. Fresh online resolution and provider/native-worker
  acceptance remain outside these witnesses.

- [x] Verify scoped native ARM64 HAOS normal-requirements startup/restart at
  Core 2026.9.4 and 2026.10.2. Current attempt 7 and minimum attempt 4 preserved
  exact C453 loaded/served bytes, explicit selections, nonempty saved settings
  and identities; graceful cleanup passed. Provider/native-worker, HACS, restore
  and final-RC scope remain separate.

- [ ] Freeze the advertised matrix. The current proposal has eight cells:
  HAOS/Container × amd64/ARM64 × Core 2026.9.4/2026.10.2.
- [ ] For each cell, verify actual requirements installation, exact candidate
  files, setup/load, restart, native worker where shipped, provider failure
  isolation and removal. Record HAOS/Supervisor/HACS versions where relevant.
- [ ] Use the minimum/current Core and both architecture suite coverage already
  available to target missing work; avoid running the entire suite separately
  for every installation wrapper. Recheck changed runtime/native paths on each
  affected architecture and the final RC's representative full-suite targets.
- [ ] Publish exact supported combinations and limits. Keep additional glibc
  distributions and future Core versions outside the claim until qualified.

### 7. Controlled owner account acceptance

Current scoped account evidence is in the [enabled-candidate record](RELEASE-1.0-ENABLED-CANDIDATE.md):
both initial connections and the selected saved-session restart were witnessed.
Full lifecycle, renewal and account restore acceptance remain open. The following
preparation cutoff is retained as dated history.

The [controlled account protocol](RELEASE-1.0-ACCOUNT-ACCEPTANCE.md) is ready.
The maintainer delegated target selection; a separate new dedicated test
instance was chosen, preserving original instances. A corrected explicit network
record passed stopped-export readback with one loopback-bound NAT forward;
online startup succeeded. Normal Core boot was active in the latest root
observation at October 21, 00:58 UTC. At the 01:02 UTC cutoff, UI onboarding,
owner accounts and HACS readiness have not been
accepted. No owner account attempt has started during this preparation.

- [ ] For each included direct provider, accept sign-in/verification, discovery,
  explicit item/member selection, cancel/abandon, reconnect, disconnect and
  expiration/renewal behavior with owner participation.
- [ ] For included Find My recovery, complete successful recovery using correct
  owner credentials, account-bound identity continuity and safe retry behavior.
  Never deliberately consume wrong-passcode attempts for testing.
- [ ] Retain only sanitized receipts. Establish a recovery/cleanup endpoint for
  the session and confirm secrets do not enter logs, artifacts or release files.

### 8. Finite field window

- [ ] Agree and record the observation period and pass criteria before starting.
  Proposal: seven consecutive days plus at least one genuine departure/return,
  away-from-Wi-Fi background phone interval, multi-item quiet/stale interval,
  controlled network outage/recovery and provider renewal observation. If a
  required natural event does not occur, record it as pending or use a separately
  identified controlled case rather than silently extending the test forever.
- [ ] Compare source report time, HA observation time and HomeCircle display.
  Successful polls and Home state do not establish new physical coordinates.
- [ ] Verify one failing item/provider leaves siblings working; verify cached
  data and stale/unavailable explanations remain truthful across recovery.
- [ ] Record the Person-source conflict warning against an actual applicable
  case, including independently configured sources and no inferred associations.

### 9. Final UI, privacy and access

The [Safari check](PICTURE-BROWSER-VALIDATION.md) passed actual image decoding,
canvas, filename/upload/navigation and native chooser cancellation. A bounded
plain-input versus hidden-input A/B reproduced the same native picker automation
limitation in both; it did not demonstrate a hidden-input regression. Native
selection completion and the remaining mobile/display/access cases stay open.


- [ ] Accept setup with no provider account or manual YAML, desktop/mobile
  layouts, selected-member following, overlap expansion, keyboard/touch and
  multiple-card isolation. Check the filename fix in a real browser.
- [ ] Accept the intended physical wall-display build with visible attribution
  and usable navigation; browser-only evidence does not substitute for it.
- [ ] Verify administrator versus household-user controls, history access,
  photo privacy, disconnect/removal/data retention and secret-redacted errors.
- [ ] Observe actual OSM Referer/cache behavior and final OSM/USGS/IEM credits;
  verify opt-in city lookup's outgoing coordinates, bounds and privacy disclosure.
  Retain truthful stale/report labels and no raw-coordinate fallback where the
  product contract excludes one.

### 10. Installed-state migration acceptance

- [ ] Freshly inspect and back up the actual installed version, local patches,
  configuration, storage/Recorder, frontend and resource registration.
- [ ] Rehearse supported published and freshly captured patched baselines in
  isolation, then accept the planned real upgrade. Preserve stable identities,
  selections, places, photos, settings, keys and history.
- [ ] Verify loaded version and exact served files after a real restart;
  exercise documented rollback and removal. Explain package-only rollback's
  identity-ledger limitations and safe recovery-guard handling.

### 11. User documentation and support

- [x] Enable and verify private GitHub vulnerability reporting and prepare the
  [security/support route](SECURITY.md), without promising an unstaffed response
  deadline or declaring a stable release.
- [ ] Reconcile UI setup, included providers, platform/version matrix, dependency
  and network scope, privacy/retention, unsupported formats and service limits.
- [ ] Publish installation, upgrade, rollback, backup/restore, troubleshooting
  and removal procedures validated against the candidate.
- [ ] Prepare migration/release notes, known limitations, attribution/license
  locations and a clear support/security-reporting route.

### 12. Release candidate

- [ ] Freeze `v1.0.0-rc.1` (or the next numbered RC) with source revision,
  deterministic package, inventory and hashes. No pending blocker may be hidden
  by a successful build or passing test count.
- [ ] Run backend/frontend checks, HACS and HA manifest validation, package/
  public-byte checks, privacy/history review and final installed notice checks.
  Reuse prior evidence only where source, artifact and scope support the claim.
- [ ] Perform the agreed RC acceptance window. Fix confirmed blockers, increment
  the RC when its bytes change, and retest affected areas plus the final required
  checks. Record maintainer acceptance and every explicit scope exclusion.

### 13. Stable publication and handoff

- [ ] After acceptance, publish the identified stable source/tag, `homecircle.zip`,
  inventory and release notes as `v1.0.0`; keep earlier release artifacts intact.
- [ ] Independently download the public assets and verify hashes/member bytes.
  Complete genuine HACS install/upgrade, restart and loaded/served version proof.
- [ ] Record the final supported matrix, open non-blocking issues, recovery
  procedure and support route. Establish normal issue review and `1.0.x` patch
  releases; a completed release is not an instruction for endless retesting.

## Work that can proceed now

The scoped ordinary Person/activity partial restore and automatic recovery-guard
block are complete, alongside the earlier initial account/saved-session restart
and compatibility evidence. Both direct providers remain included. Continue
advertised backup-variant acceptance, provider lifecycle/renewal,
assurance/provenance dispositions, remaining compatibility cells, finite
field/mobile/display checks and real installed-state upgrade acceptance before
freezing an RC. Arrival-gap and deliberately pending-on-shutdown writes are not
qualified by the scoped restore. Earlier failed attempts and narrower passes
retain their recorded outcomes. Stable release approval remains open.
