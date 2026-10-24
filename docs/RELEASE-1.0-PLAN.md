# HomeCircle 1.0 release plan

Started October20, 2026. The target is `v1.0.0`; the current published
prerelease is `v1.0.0-rc.2`. Published beta20 remains the historical upgrade
baseline. This is an execution tracker, not a stable-release declaration. Check a task only after linking its exact evidence. Retain
failed attempts and record any accepted scope change instead of deleting a gate.

## First-release decisions and active checklist

The maintainer accepted official HAOS on amd64 and ARM64 as the first-release
support target on October 22, 2026; Home Assistant Container remains experimental
for this release. Both direct Apple Find My and Life360 remain included.
The proposed minimum Core 2026.9.4/current Core 2026.10.2 endpoints remain the
qualification targets. The maintainer also explicitly accepted the completed
Claude AI technical review with its documented partial coverage and missing
independent producer-format evidence. This supersedes the earlier human-specialist
assurance gate for 1.0; no such human assurance is claimed.

Use the [seven-item first-release tracker](RELEASE-1.0-FIRST-RELEASE-TRACKER.md) for
current work and the [accepted support target and exclusions](RELEASE-1.0-SUPPORT-PROPOSAL.md)
for launch scope. [Current AI review and source bindings](RELEASE-1.0-ASSURANCE-CURRENT.md)
and [distribution questions](RELEASE-1.0-DISTRIBUTION-QUESTIONS.md) retain separate
technical and distribution outcomes. On October 23 the maintainer requested a
[no-contact implementation](RELEASE-1.0-NO-OUTREACH-DECISION.md): source-only HACS
delivery, actual public OSS grants, complete retained notices, optional unofficial
providers and local privacy/support. No permission letters or mandatory outreach
are required. Exact Apple binary/service and Unicorn terms retain their factual
basis and residual uncertainty, accepted by the maintainer for the exact scope
in the [approved release disposition](RELEASE-1.0-PROPOSED-DISPOSITION.md); technical
review does not manufacture permission or legal clearance. Administrator
Manage direct connections, Pause/Resume and stop-on-access-denial are implemented in the source candidate; affected runtime results remain tied to their exact recorded source.

The bounded RC2 phone display check passed. Unobserved field-case limits remain.
On October 24, 2026 UTC (October 23 in America/Chicago), the maintainer explicitly
replied “Do it” to final approval to publish 1.0 with both optional, unofficial
providers and the documented limits. This approves prepared source
`89e25a406d893f99e9f6a173b149e3e7aaca4483`, ZIP
`a21aa690ed45aaa1e293fe33c6c9780f6a95ba6e7faa868e49856d4cd7fce932`
and inventory `fb5098b327e656a44156b0634e9521c46ed68cd46dd883a2d86590b89a44808f`.
The [approved disposition](RELEASE-1.0-PROPOSED-DISPOSITION.md) records the accepted
inclusion/support scope and residual limits. Merge, tag and stable publication
remain pending; no everyday HA upgrade, extra provider tests, recovery actions
or outreach are authorized by this release decision.
The frozen-RC engineering qualification, including the focused minimum-Core
check and genuine HACS delivery, is accepted. Reuse existing architecture
evidence; do not reopen completed ordinary restore, private-copy upgrade or
current-Core checks for documentation edits.
Final RC1 current/minimum qualification, public prerelease byte verification and genuine fourteen-phase HACS installed delivery passed at their recorded source/package scope. The RC2 phone confirmation is bounded display acceptance; the separate final maintainer approval does not create new runtime evidence. Stable publication remains pending. The detailed thirteen-stage history below retains
its dated outcomes; superseded scope/assurance proposals are historical.

## Final candidate qualification status

The prepared stable1.0 package has version-only differences from RC2 and is now approved at the exact source/artifact binding above. Its [preparation record](RELEASE-1.0-STABLE-PREPARATION.json) preserves the checks; the [approved final release decision](RELEASE-1.0-PROPOSED-DISPOSITION.md) records the subsequent maintainer inclusion/support and residual-scope disposition. Merge and publication are pending.

Current published prerelease RC2 is source `ae8081313cb4060123e200e0356a598c5a72d145`, ZIP `41240a77eb0f5950b47e3e926097751b243e3ace8161de948650b648910c865c`. Its [acceptance record](RELEASE-1.0-RC2-ACCEPTANCE.json) records exact public bytes, 126 frontend cases, 51 focused exact-package Linux cases and the real owner-instance cold restart. The owner confirmed both the Life360 person and AirTag display correctly on the iPhone map and both details open. Desktop observation also showed both members and details without HomeCircle conflicts, retaining stale source ages. This is bounded mobile/desktop display acceptance, with no separate physical-position recheck, forced refresh, reconnect or other manual provider action. New GPS reports, natural renewal and real-photo persistence remain unclaimed. Final stable approval is recorded separately above; publication remains pending.

The earlier RC1 [final qualification record](RELEASE-1.0-FINAL-QUALIFICATION.md) identifies frozen source b906 and the unchanged 112-member RC1 ZIP4f94. Focused minimum-Core run40002540583 is accepted with its actual C7 source: 20 tests, four real Core processes, matching runtime/package and verified cleanup. Full current-Core R3 run40010260549 passed 1,779 backend/126 frontend cases, exact collection, privacy and cleanup. The tagged RC1 and both public assets are verified. Genuine HACS R1 remains failed after four phases and a confirmed helper-only post-uninstall expectation. Corrected R2 run40013210859 passed all14 phases/23 normal Core actions with root/peer/CI agreement and cleanup. Product/RC1 bytes were unchanged within that qualification. Failed full and diagnostic attempts retain their actual scopes. The final b906 change is one test fixture correction; no runtime or package bytes changed. These results remain RC1 evidence, not a full RC2 rerun. Historical records below remain dated evidence.

## Current fixed candidate evidence

Source `3c33160c67e53956ab52298ffc10ccc9992132f0` and package `f181e6300f15d8977817a552db90d35caf0edc869067ebeea815c7be1df0248e` include the activity initialization
correction. The [complete fixed-candidate package record](RELEASE-1.0-FIXED-PACKAGE-VALIDATION.md)
binds native run 39865496620: current Core 2026.10.2, all 1,732 backend cases and 54
required functions passed, exactly one named optional installer skip, 122 frontend
cases, privacy over 381 canonical files, 42 harness contracts and 20 corrected independent
consumer contracts (with the original consumer-only refusal retained). The original f181 candidate remained the tested/exported
archive; the same-payload canonical level-9 acfc rebuild has a separate identity.
All 113 candidate members were checked in the source/test tree with one additional
Git-bound source-only README.

[Fixed-candidate ordinary restore](RELEASE-1.0-FIXED-ORDINARY-RESTORE.md) separately
retains the four-phase amd64 HAOS Person/activity/Recorder and automatic guard
review/refusal result. The [private upgrade record](RELEASE-1.0-PRIVATE-UPGRADE.md)
retains its scoped ARM64 installation-copy upgrade/restart and focused setup
result. Earlier minimum-Core full-suite evidence remains tied to old012a/98a;
this current-Core run does not broaden it. These scopes do not close other
advertised compatibility, provider/security/permission, real-account/field,
HACS delivery, RC or stable-release gates.

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
both providers' recorded account/dependency evidence and service/assurance scope decisions; it did not assert that all acceptance was complete. The later accepted no-contact approach and limited Claude review remain as described above. Final current/minimum-Core qualification, public RC verification and genuine HACS installed-upgrade acceptance have now passed; owner/maintainer dispositions remain separate.

## Execution and evidence rules

Agent means implementation, local/disposable validation and documentation.
Maintainer means product/support and residual-uncertainty scope decisions plus
final acceptance. Owner means the account/device participant. Identify any
actually commissioned specialist review by role and scope; no external lawyer
or qualified-human assurance is invented. The earlier human cryptographic gate
was superseded by the accepted Claude method above. The no-contact approach
does not require provider/author correspondence before preparation proceeds.

Every acceptance receipt records source revision, ZIP/inventory hashes, target,
versions, named cases, outcome and cleanup. Evidence remains attached to its
tested bytes. Reuse applicable historical evidence, then run affected checks for
new changes. Run the complete final suite once on the frozen RC baseline;
repeat only after changes or a specific unresolved failure justifies it.
Infrastructure failures receive one bounded diagnosis before any reasoned retry.

## Ordered tracker

| Stage | Current status / dependency | Responsible | Completion evidence |
| --- | --- | --- | --- |
| 1. Freeze scope and support | Both providers selected; HAOS-first target accepted October22; current/minimum RC and genuine HACS baseline checks passed; owner/maintainer dispositions retain their scope | Maintainer, agent records | Signed-off feature/provider list, supported target matrix, upgrade baselines, exclusions and `1.0.0` naming |
| 2. Consolidate release source and blockers | Clean source in draft PR #36; focused fixes independently reviewed; exact-source native suite passed | Agent; maintainer review | Clean canonical release branch, reviewed product-only diff, notices included, recorded defect dispositions |
| 3. Record provenance and provider scope decisions | No-contact source-only implementation requested October23; retained grants/notices and Mac exclusion recorded; final factual checks and residual decisions pending | Maintainer decides scope; agent supplies evidence | Exact source/package/dependency notice checks, actual terms/basis, residual uncertainty or real exclusions; no invented permission letter or legal clearance |
| 4. Enabled backup/restore safety | Recovery-guard and scoped ordinary Person/activity partial restore passed; advertised backup variants remain open | Agent | Actual Person identities/links and product activity B/M/R preserved under normal requirements/default conditions; arrival-gap/pending-shutdown and broader variants remain unqualified |
| 5. Cryptographic and format assurance | Maintainer accepted completed Claude AI source review with documented limits on October 22; no confirmed actionable findings | Agent records; maintainer accepted method | Current source bindings, Claude partial coverage and unresolved format limits retained; no qualified-human or producer-vector assurance claimed |
| 6. Advertised compatibility | Historical lifecycle/ARM evidence retained; final current/minimum RC and native amd64 HAOS genuine HACS consumer delivery passed | Agent | All advertised cells have candidate dependency/install/start/restart evidence; unsupported cells excluded explicitly |
| 7. Real-account acceptance | Initial connections and saved-session restart witnessed; remaining lifecycle and stages 3/5 disposition open | Owner, agent guides/records | Controlled setup, discovery, selections, session lifecycle and successful recovery receipts without deliberately wrong passcodes |
| 8. Sustained field acceptance | Earlier observations exist; final scope incomplete; depends on stages 6/7 as applicable | Owner observes, agent analyzes | Agreed observation window and movement/outage/renewal/staleness cases with genuine source-report times |
| 9. Dashboard, access and privacy | Exact-source privacy and scoped desktop Safari picture checks passed; remaining final acceptance open | Agent plus owner for real displays | Desktop/mobile/physical display, admin/household permissions, privacy/deletion, real attribution/request checks |
| 10. Real installed-state upgrade | Genuine published-beta20 HACS upgrade/restart/coherent rollback/reupgrade passed with synthetic state; private-copy and owner observations retain separate scopes | Agent, owner/maintainer for actual instance | Fresh baseline inspection/backup, upgrade/rollback/removal receipts, preserved storage/Recorder/resource identities |
| 11. Finish user and support documents | Open; draft in parallel, finalize after scope/results | Agent, maintainer accepts | Consistent installation/privacy/support/migration/recovery documents and known limitations |
| 12. Freeze and qualify RC | Exact RC current/minimum/HACS engineering checks and public prerelease verified; remaining bounded owner/maintainer acceptance separate | Agent, maintainer accepts | Identified RC, exact artifact, final check receipt and bounded RC acceptance with no unresolved blockers |
| 13. Publish and verify 1.0.0 | Pending RC acceptance | Agent executes, maintainer release disposition | Stable tag/package/inventory/release notes, public-byte verification and genuine HACS install/upgrade restart proof |

### 1. Scope and support decision

- [x] Record included features, both direct-provider dispositions and the
  first-release HAOS support target and explicit experimental/excluded variants.
  Final candidate qualification remains separate; see the current seven-item tracker.
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

### 3. Notices, distribution basis and provider scope

- [x] Carry the GrandSlam, Unicorn supplemental and Construct notice correction
  into the actual candidate and verify its installed integration paths:
  [exact-package notice witness](RELEASE-1.0-NOTICE-INSTALLATION.md). That dated
  result stays tied to its package; repeat changed-candidate notice checks.
- [x] Record the October23 no-contact implementation direction, public OSS
  grant basis and source-only distribution limits in the
  [decision record](RELEASE-1.0-NO-OUTREACH-DECISION.md). This closes the choice of
  preparation approach, not the outstanding terms questions or final release.
- [ ] Verify that the changed candidate excludes the unused Mac utility/CLI,
  retains complete inherited notices and introduces no bundled dependency/native
  or Apple payload. Preserve dated provenance instead of inventing attribution.
- [ ] Record the actual Unicorn core/binding terms and source-only distribution
  basis, including any remaining combined-work/source-delivery uncertainty.
  No invented BSD text or source offer is acceptable; separate installation and
  IPC alone are not the disposition.
- [ ] Bind the final dependency/notice inventory to actual resolved artifacts.
  Distinguish retained supplemental text from an upstream wheel repair.
- [ ] Record the exact Apple software/service and Life360 terms/basis, remaining
  uncertainty and maintainer include/restrict/defer choice for the shipped
  behavior. No mandatory contact or permission letter is imposed; no grant or
  legal clearance is asserted by this plan.
- [ ] Verify administrator Pause/Resume and stop-on-denial, local privacy/support
  and non-affiliation disclosures against the final implementation. Record any
  actual scope exclusion and affected checks; a checkbox does not resolve terms.

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

- [x] Identify the current source, changed paths, prior findings and threat boundaries.
  The [current assurance handoff](RELEASE-1.0-ASSURANCE-CURRENT.md) binds all 74 primary
  Python files and the six changes since the dated earlier handoff.
- [x] Complete the Claude AI source review and source-based question triage.
  It reported no confirmed actionable defect in its disclosed partial scope.
  The maintainer explicitly accepted this review method with its documented
  limits for 1.0 on October 22, 2026.
- [x] Retain unresolved protocol/format assumptions and residual-risk boundaries
  without relabeling generated fixtures as independent Apple-produced proof.
  The absence of independent producer vectors remains a disclosed limitation.
  No human/external-qualified assurance is asserted; the old human-review
  requirement is superseded by the explicit maintainer decision.

New confirmed defects would require correction and affected rechecks.
Source/license/service-permission decisions remain separately open.

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

- [x] Freeze the first-release target: HAOS × amd64/ARM64 ×
  Core 2026.9.4/2026.10.2. Container stays experimental with historical
  evidence retained. Final scoped engineering qualification now passed: full
  current-Core R3, focused minimum-Core and genuine native amd64 HAOS HACS.
- [x] Record the historical per-cell requirements/startup/restart/native-worker
  evidence with its original source and target. Reuse that evidence only where
  unchanged bytes and the accepted first-release scope support the claim; no
  fresh final-RC execution of every historical cell is asserted.
- [x] Complete the agreed representative full current-Core suite and focused
  minimum check, plus actual HACS delivery, without adding another broad CPU
  matrix. Retain actual loaded/disk/served bytes, identity and cleanup results
  in the final qualification record.
- [x] Record the supported combinations and explicit exclusions in the accepted
  support proposal. Additional glibc distributions and future Core versions
  remain outside the claim until qualified.

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

The active first-release approach is one finite agreed owner round combining
provider, movement/outage/staleness and required display/access checks. The
earlier seven-day proposal below is historical, not an automatic waiting period.
Do not infer unobserved natural renewal or missing events as passed.

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

- [x] Freeze and publish identified prerelease `v1.0.0-rc.1` at b906 with the exact 112-member ZIP4f94 and inventorye4bc; anonymously verify both public assets. This is not stable approval.
- [x] Complete the full current-Core R3 backend/frontend/package/privacy qualification and focused minimum-Core check, retaining actual sources, dependency versions, exact collection and independent cleanup acceptance.
- [x] Complete genuine HACS install/upgrade/restart/removal/coherent rollback delivery against the public RC in run40013210859, with exact installed package/notice bytes, source/identity and cleanup checks. Reuse prior evidence only where source, artifact and scope support the claim.
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

Follow the seven-item tracker and final qualification record: retain the accepted 548-case affected-controls result and focused minimum-Core result; retain accepted full current-Core R3, focused minimum-Core, verified public RC assets and the accepted finite genuine HACS rehearsal. Finish the bounded owner round and remaining maintainer basis/scope decisions without relabelling prior observations. Reuse unchanged architecture/restore/upgrade evidence; do not add a broad matrix or require author/provider correspondence.

The ordinary Person/activity restore, recovery-guard block and private-copy
upgrade keep their recorded scopes. Arrival-gap, pending-on-shutdown and broader
backup/platform variants remain unqualified unless separately accepted; they do
not automatically create a new first-release test matrix. Historical failures,
AI limits and narrower passes stay unchanged. Stable release approval remains
open; neither these documents nor a risk checkbox makes the maintainer's final
distribution/provider decision.
