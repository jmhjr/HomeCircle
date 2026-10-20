# First stable release checklist

Updated October 20, 2026. This is a release preparation checklist, not approval to
publish. The published release remains experimental beta 19. No stable version or
final provider scope has been chosen. Preserve the existing Ruby fix, installed
settings and history, and the frozen V2 reference.

## Implemented local candidate

- [x] Resolve the two endpoint-policy fixture digest failures through official
  wheel/provenance verification; keep fixture bodies unchanged.
- [x] Preserve the Ruby Person/item projection and strict-save fix and its tests.
- [x] Preserve valid polling reports and completed historical progress across
  later batch failures, isolate items, keep cached coordinates and genuine source
  times, and persist progress before reconnect/unload releases writer ownership.
- [x] Isolate corrupt report records while retaining authenticated older and
  neighboring reports; retain batch-envelope and account-auth error boundaries.
- [x] Isolate GSA and recovery SRP modes, including RFC5054 behavior, without
  changing ordinary `srp._pysrp` globals used by other integrations. Private
  namespaces execute the installed pure-Python dependency; file-backed loading is
  tested, while zipped/non-file installations remain unqualified.
- [x] Isolate provider construction/startup failures, preserve working siblings,
  report an actionable Repair issue, and drain startup cleanup on cancellation.
- [x] Restore the complete inherited OpenTagViewer MIT notice and test the archive
  path. Other provenance, license and service-use findings remain open.
- [x] Add a durable recovery submission guard outside selected-item storage,
  account serialization, fixed stage/outcome errors, explicit local acknowledgment,
  and verified-material retries that do not resubmit the recovery proof.
- [x] Preselect current items and disclose removal; retain account-bound accessory
  commitments and safe display settings without omitted tracking keys. Preserve
  proven IDs across identifier changes and reselection, reject ambiguous matches,
  and serialize/guard selection, disconnect, cancellation and stale-dialog saves.
- [x] Complete focused source triage and fix confirmed worker discovery/verified-byte,
  unchanged-vault, emulator entropy/bounds, recovery signature/tag/work-limit and
  cleanup defects with isolated regressions. Preserve separate native and
  cryptographic acceptance gates.
- [x] Complete an independent source and synthetic cryptographic review of the
  local candidate; fix confirmed peer/key binding, protected-record authentication,
  recovery resource/cancellation and saved account/session binding issues. See
  [independent review validation](INDEPENDENT-CRYPTO-VALIDATION.md) for evidence and limits.

See [polling checkpoint](STABLE-MILESTONE1-VALIDATION.md) and the
[combined isolation validation](STABLE-ISOLATION-VALIDATION.md), followed by the
[recovery and identity validation](RECOVERY-IDENTITY-VALIDATION.md). These checks are
synthetic/local evidence, not live movement or broad platform acceptance. The
[focused hardening validation](FOCUSED-HARDENING-VALIDATION.md) records the next
local fixes and their limits. The subsequent [independent cryptographic review](INDEPENDENT-CRYPTO-VALIDATION.md) records further fixes and the final local candidate.

- [x] Rehearse the exact published beta 19 and reconstructed recorded-patch
  upgrades/restarts/backup rollbacks on both local Core targets; verify the
  independent recovery guard and interrupted migration across fresh processes.
  Document package-only rollback's identity-ledger loss and latest-guard retention.
- [x] Validate the exact packaged native worker on both local Core environments,
  fresh anonymous Apple runtime on this Mac, and official dependency wheels for
  Linux amd64/aarch64 glibc/musl. Correct the development dependency mismatch;
  retain actual Linux/HAOS candidate execution as a separate gate.
- [x] Validate the unchanged exact candidate in official ARM64 Core 2026.9.4 and
  2026.10.2 QA containers on fresh HAOS 18.3: each passed dependency closure and
  constraints, native worker/lifecycle, 1,443 backend tests, both upgrade baselines
  and full synthetic recovery/repair. Public anonymous Apple runtime also passed
  on Core 2026.10.2. See [Linux/HAOS validation](LINUX-HAOS-VALIDATION.md).
- [x] Install the exact candidate through the fresh HAOS-managed Core 2026.10.2
  dependency path on ARM64 and emulated AMD64, create an explicitly selected
  synthetic Person/tracker through the real flow, and verify all 112 installed
  hashes plus each instance's saved entry, Person, tracker, resource and dashboard
  identities/configuration across actual restart. Native checks also passed in
  both managed Core containers.
- [x] Complete the final backend suite on emulated AMD64 Core 2026.10.2:
  1,443 passed and one optional fixture skipped after correcting the QA wrapper's
  aggregate deadline. Retain the first failed invocation and unchanged inner
  process limits in the validation record.
- [x] Rehearse both exact upgrade/rollback baselines and full synthetic recovery
  on a native AMD64 Core 2026.10.2 musl container. The [October 20 CI run](LINUX-HAOS-VALIDATION.md#october-20-native-amd64-container-upgrade-and-recovery)
  passed 20 upgrade phases, 20 recovery processes and all 40 blocked probes in
  223.990 host seconds, with unchanged candidate/input pins, offline acceptance
  and confirmed owned-container stop/removal. This did not rerun the backend
  suite or separate worker/lifecycle checks, or qualify native HAOS-managed service.
- [x] Validate the advertised minimum Core 2026.9.4 in a native AMD64 container.
  [Run 39433931788](https://github.com/jmhjr/HomeCircle/actions/runs/39433931788)
  passed 1,443 backend tests with the one named optional fixture skipped, actual
  packaged native worker/lifecycle checks, both ten-phase upgrades/rollbacks and
  full twenty-process recovery with all 40 probes blocked. The frozen 112-file
  candidate and 24-package constraint closure matched; offline acceptance and
  owned-container cleanup passed in 534.500 host seconds. Two earlier source
  staging failures remain recorded separately. See the [minimum-Core record](LINUX-HAOS-VALIDATION.md#october-20-minimum-core-native-amd64-validation).

- [x] Complete a fresh native AMD64 HAOS/HACS synthetic rehearsal. [Run 39441631322](https://github.com/jmhjr/HomeCircle/actions/runs/39441631322)
  passed eight phases in 344.041 host seconds; all 23 controller contracts also passed:
  genuine published beta 19 HACS install/rollback, two stopped exact-112-file
  candidate installs, real restart/options/selection/identity/served-bundle
  continuity and latest-guard preservation through matching stopped state
  restoration. The actual candidate API stayed blocked at three after reinstall;
  the older rollback verified guard bytes only. Owned VM/private cleanup passed.
  Candidate HACS delivery/release transport and OAuth remain open. This HACS run
  excluded Supervisor backups/Recorder; the prepared partial scope is recorded
  separately below. See the [native HAOS record](LINUX-HAOS-VALIDATION.md#october-20-native-haos-and-hacs-rehearsal).

- [x] Rehearse a prepared disabled-entry Supervisor partial Home Assistant
  backup/restore including Recorder on fresh native HAOS. [Run 39452393848](https://github.com/jmhjr/HomeCircle/actions/runs/39452393848)
  passed six phases in 309.430 host seconds and 42 offline contracts. Original
  committed history returned exactly, post-backup markers disappeared and new
  recording survived restart. Saved selections/options/identities and unrelated
  resources were restored; the owned resource was recreated and retained across
  restart. Automatic restore boot stayed disabled/unloaded without candidate
  import; the independently retained newest guard was manually restored before
  enable and remained blocked at three. Owned VM/private cleanup passed.
  Ordinary enabled-entry/full-system/add-on/encrypted/cloud restore, automatic
  anti-rollback and production history remain open. See the [guarded restore record](LINUX-HAOS-VALIDATION.md#october-20-guarded-supervisor-backup-and-recorder-restore).

See [platform, upgrade and recovery validation](PLATFORM-UPGRADE-RECOVERY-VALIDATION.md)
for the exact evidence, replacement harness and recorded shutdown failures,
and remaining limits.

## Remaining review and acceptance

1. **Platform and cryptographic assurance.** The independent source review and
   synthetic controls are complete for this local candidate. They do not provide
   an external specialist audit, independent Apple-produced format fixtures, live Apple
   account recovery acceptance, or full voucher/dynamic circle-membership
   verification. Qualify entropy, memory bounds, exact-byte loading and supported
   protected-record formats on the final native platform scope. Separate-owner
   signer formats without trusted context currently fail closed.
2. **Recovery and identity acceptance.** Local source and synthetic review covers
   the durable guard, proof boundary, verified-material lifetime, commitment ledger
   and configured account/session binding. The local exact-artifact and recorded-patch rehearsals now pass; complete real
   production installed-state, HACS and live recovery acceptance below without deliberate
   wrong owner passcodes.
   This does not establish Apple's server-side attempt policy or prove continuity
   for a previously omitted item whose original keys were never retained in a ledger.

## Release acceptance still required

- [ ] Choose supported platforms/Core versions and qualify dependency resolution,
  imports and native execution on the advertised amd64/Container/HAOS targets.
  ARM64 container checks pass on Core 2026.9.4/2026.10.2, with actual managed-Core
  synthetic install/setup/restart/native checks on 2026.10.2 for ARM64 and emulated
  AMD64, whose final full suite also passes. The [October 19 emulated AMD64 upgrade/recovery follow-up](LINUX-HAOS-VALIDATION.md#october-19-follow-up-amd64-upgrade-rollback-and-full-recovery)
  failed and remains unqualified within that emulated scope: both attempts timed out in the older published
  baseline's first child at the unchanged 180-second bound, without a completed
  phase receipt; the reconstructed baseline was not reached. Independent
  recovery timed out in its first child at the unchanged 45-second bound, with
  zero completed phases and no full 20-process/40-probe result. The bounded
  diagnostic did not pass acceptance or confirm a cause. Its disposition required
  a faster/native AMD64 runner or confirmed runner issue and fix before another
  full qualification attempt; no blind rerun or relaxed limit was used for the
  separate native result below.
  A subsequently confirmed guest clock-integrity issue led to an HPET-only
  disposable-VM change and a passed runner-only host-clock gate. The earlier
  failures and first gate's QA-criterion failure remain recorded. The
  corrected-clock upgrade attempt failed after 260.377106 host seconds despite
  eight passed workload clock checks/TSC retained: its first published-baseline
  child still exceeded the unchanged 180-second deadline, with no completed
  phase or candidate result. QA-container stop was confirmed without host
  cleanup failures. Full upgrade/rollback in that emulated attempt remains unqualified, without
  establishing a candidate defect or sole timeout cause. The single
  corrected-clock recovery attempt also failed after 110.627503 host seconds:
  three workload clock checks passed/TSC retained, but the first child hit the
  unchanged 45-second bound and was killed with exit -9. Zero phases completed;
  no 20-process/40-probe acceptance is claimed. Input pins matched before/after
  and exact-container stop was confirmed without host cleanup failures. Both
  emulated full scopes remain unqualified, with no further emulated retries.
  The [corrected-clock outcomes](LINUX-HAOS-VALIDATION.md#corrected-clock-upgrade-and-recovery-outcomes)
  add no candidate acceptance pass.
  The separate [native AMD64 container run](https://github.com/jmhjr/HomeCircle/actions/runs/39426549335)
  now passes both ten-phase exact-baseline upgrades/rollbacks and twenty-process
  full recovery on pinned Core 2026.10.2/Python 3.14.6 Alpine/musl, with all 40
  probes blocked, no unexpected/Apple request, matching 112-file candidate/input
  pins and confirmed cleanup. It does not requalify the historical emulated
  attempts. The later minimum-Core native AMD64 run passes the full backend,
  native/lifecycle, both upgrade and full-recovery scopes on Core 2026.9.4.
  The later native AMD64 HAOS rehearsal also passes synthetic managed-service
  activation, persistence and rollback. A prepared disabled-entry Supervisor
  partial backup/Recorder restore also passes; candidate HACS delivery and
  ordinary enabled-entry/full-system restore remain open. Glibc Core and additional runtime scopes remain unqualified. The earlier Core
  2026.10.2 native CI run
  did not rerun the backend suite, separate worker/lifecycle checks or anonymous
  Apple runtime; Ubuntu's host libc does not establish glibc Core acceptance.
  All manifest requirements remain mandatory before integration startup; provider
  isolation cannot contain a prior dependency-install failure. Do not invent a
  lazy-install API. Current compatible pins/wheel metadata are not runtime proof.
- [ ] Run long multi-item quiet/stale/failure/renewal/cancellation field acceptance;
  retain genuine report time separately from poll time. Complete movement/parity,
  departure/return and away-from-LAN phone evidence without manufacturing freshness
  or physical ground truth from successful polls or Home state.
- [ ] Validate upgrade from canonical published beta 19 AND the locally patched
  installed state, retaining keys, identities, history, settings, places, pictures
  and source choices. Verify loaded version after real restart, exact package and
  HACS bytes/resources, rollback, and physical DAKboard acceptance where relevant.
  Exact-artifact local rehearsals now pass on Core 2026.9.4/2026.10.2; the older
  version-only fixture is separate. The recorded-patch code baseline is not a
  fresh inspection or copy of current production storage. The native AMD64
  container rehearsals also pass on Core 2026.10.2, but do not close this real
  installed-state/HACS/Recorder/physical-display gate. Package-only rollback's
  ledger loss and latest independent recovery-guard retention still apply. The
  native HAOS rehearsal adds published-release HACS install/rollback and stopped
  candidate activation with synthetic identities; it does not close candidate
  HACS release transport, current production storage/Recorder or physical acceptance.
- [ ] Close the remaining [licensing/service terms checklist](STABLE-SCOPE-AUDIT.md#licensing-and-service-terms-release-checklist)
  for the exact selected provider scope. Restoring one inherited notice does not
  settle the separate provenance, dependency, software/service or branding gates.
- [ ] Reconcile onboarding/disconnect/backup limitations, privacy, support scope
  and release notes; build and revalidate the exact final candidate. Choose the
  stable version and maintainer release disposition before tagging/publication.
