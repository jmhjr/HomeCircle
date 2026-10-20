# HomeCircle 1.0 release plan

Started October 20, 2026. The target is `v1.0.0`; the current published release
remains experimental `v0.1.0-beta.20`. This is an execution tracker, not a stable
release declaration. Check a task only after linking its exact evidence. Retain
failed attempts and record any accepted scope change instead of deleting a gate.

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
| 2. Consolidate release source and blockers | Product-only branch prepared; focused fixes reviewed; native full-suite acceptance pending | Agent; maintainer review | Clean canonical release branch, reviewed product-only diff, notices included, recorded defect dispositions |
| 3. Close provenance and provider decisions | Open; inventory and notice preview complete; depends on stage 1 for final scope | Maintainer/specialist, agent supplies evidence | Exact-source/installed-dependency notices and obligations disposition; source/permission/service/name decisions for shipped scope |
| 4. Enabled backup/restore safety | First native experiment incomplete; bounded diagnosis underway | Agent | Ordinary enabled startup after restore, restored data/identities, stale-backup safeguard result and bounded request evidence |
| 5. Cryptographic and format assurance | Synthetic independent source review complete; external assurance open if Find My ships | Specialist, agent fixes; owner only for controlled acceptance | Review disposition, independent format vectors, authenticated rejection/recovery cases and fixes rechecked |
| 6. Advertised compatibility | Partial target evidence complete; depends on stage 1 and consolidated candidate | Agent | All advertised cells have candidate dependency/install/start/restart evidence; unsupported cells excluded explicitly |
| 7. Real-account acceptance | Open for included providers; requires stages 3/5 disposition and owner participation | Owner, agent guides/records | Controlled setup, discovery, selections, session lifecycle and successful recovery receipts without deliberately wrong passcodes |
| 8. Sustained field acceptance | Earlier observations exist; final scope incomplete; depends on stages 6/7 as applicable | Owner observes, agent analyzes | Agreed observation window and movement/outage/renewal/staleness cases with genuine source-report times |
| 9. Dashboard, access and privacy | Existing checks retained; final candidate acceptance open | Agent plus owner for real displays | Desktop/mobile/physical display, admin/household permissions, privacy/deletion, real attribution/request checks |
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

- [ ] Create a clean release branch using the actual main/product ancestry.
  Review and consolidate accepted beta 20 hardening plus the notice correction.
  Do not merge the validation branch wholesale: it also carries CI payloads,
  runner workarounds and evidence that require separate disposition.
- [x] Inventory remaining tracked work and distinguish confirmed defect,
  acceptance case and optional enhancement. The [roadmap triage](RELEASE-1.0-TRIAGE.md) records these dispositions; unrelated working changes are preserved.
- [x] Fix the confirmed picture-picker filename continuity issue: beta 20's
  `settings-dialog.js` clears the file input after successful decoding while the
  crop remains active. Verify filename while cropping, failed upload retention,
  save/remove/cancel clearing and selection of the same file again. The [focused validation](PICTURE-FILENAME-VALIDATION.md) records before/after failure proof and 110 passing frontend tests; real-browser acceptance remains open.
- [x] Triage the roadmap's source oscillation, passive-zone legacy fallback,
  cached-city projection and shutdown cache-save cases against the consolidated
  code. The [triage record](RELEASE-1.0-TRIAGE.md) distinguishes the confirmed corrections from retained policies. Real-Core qualification remains open.

Status icons, additional landscape polish, trip trails, traffic/ETA, adaptive
freshness and additional providers remain optional post-1.0 work unless the
maintainer changes the scope. Do not convert the old wishlist into new blockers.

### 3. Notices, source obligations and permission

- [ ] Carry the GrandSlam, Unicorn supplemental and Construct notice correction
  into the actual candidate; verify their installed paths after dependency setup.
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

- [ ] Rehearse an ordinary Supervisor backup with HomeCircle enabled, restore
  it, and observe the first automatic startup in a disposable synthetic HAOS
  instance. Preserve entry/Person/tracker/settings/places/pictures/history and
  frontend-resource identities; compare Recorder contents where applicable.
- [ ] Restore an older snapshot after a newer recovery submission guard exists.
  Record guard rollback and attempted startup requests with a network-denying
  synthetic fixture; do not submit a live recovery proof.
- [ ] Fix any confirmed startup/recovery/request issue and repeat its cases.
  Either qualify stronger rollback protection or establish a tested explicit
  safe-restore procedure and disclose its limits.
- [ ] Validate full-system/add-on/encrypted/cloud backup variants only where
  advertised, or record the exact unsupported variants. Existing prepared
  disabled-entry partial-restore evidence remains separate.

### 5. Independent security and format acceptance

- [ ] Give the independent reviewer the identified source, prior findings,
  limits, threat boundaries and exact unresolved questions.
- [ ] Add independently sourced supported-format cases and safe unsupported/
  malformed rejection cases; retain authenticated peer/account/key binding,
  record integrity, resource bounds and cancellation checks.
- [ ] Resolve and recheck confirmed findings. Record residual risks and the
  explicit disposition of each; do not describe generated synthetic fixtures as
  independent real-format proof.

### 6. Compatibility qualification

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

Enabled synthetic restore validation, canonical source preparation, confirmed
picture-picker correction, roadmap case triage and documentation drafts do not
depend on an owner account prompt or a provider-scope answer. Provider-specific
shipping claims, account recovery exercises, externally qualified assurance and
stable publication remain conditional on the corresponding evidence and
maintainer decisions above.
