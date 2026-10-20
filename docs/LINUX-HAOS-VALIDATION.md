# Linux and HAOS candidate validation

October 19–20, 2026. **ARM64 QA checks passed on both Core targets; actual
HAOS-managed Core 2026.10.2 loading/restart and native checks passed on ARM64 and
emulated AMD64. All four recorded Linux backend targets, including native AMD64
Core 2026.9.4, passed the final suite.** Native AMD64 HAOS also passes the
eight-phase synthetic HACS-baseline, stopped candidate activation and rollback
rehearsal [recorded below](#october-20-native-haos-and-hacs-rehearsal).
A separate [prepared Supervisor partial-backup and Recorder restore](#october-20-guarded-supervisor-backup-and-recorder-restore)
also passed six phases, with manual newest-guard preservation.
The October 19 emulated AMD64 upgrade/rollback and recovery attempts **failed
their bounded checks**. The separate [October 20 native AMD64 container run](#october-20-native-amd64-container-upgrade-and-recovery)
**passed both exact-baseline upgrade/rollback sequences and full synthetic recovery**.
This continues the [platform, upgrade and recovery validation](PLATFORM-UPGRADE-RECOVERY-VALIDATION.md)
for the same unreleased 112-file candidate, manifest `0.1.0-beta.19`:

`f0477a91e78181fe1f8d80ada176a1739e10a7502abe7ee6ee2240571280d1f5`

The earlier Linux evidence covered official-wheel resolution and ELF inspection.
The October 19 phase used new disposable HAOS virtual machines to obtain actual
Linux process evidence. October 20 adds an authorized public validation branch
and a disposable native Linux CI runner. Production Home Assistant, owner
accounts and the published release package remain unchanged. No additional Mac
Python is part of either Linux phase.

## Runner and acceptance scope

The fresh runner is official Home Assistant OS **18.3 Generic aarch64**, with
managed Home Assistant Core **2026.10.2** observed running at that checkpoint. Its Core environment is
**Python 3.14.6**, **Alpine 3.24.1**, **musl**, **ARM64/aarch64**. The separate
disposable QA container uses the same official qemuarm64 image, recorded SHA-256:

`5958cd8bcf451966db72682c2d715db1e5a10d66f0e2c3d580dccffd86124e23`

A parallel official ARM64 Core **2026.9.4** container uses Python **3.14.6**,
Alpine **3.24.1** and musl, recorded image digest:

`dd1ad589936601cacb1b4797d17e27ce762b5147fb46b0e8e3d5486ab95e56c3`

The second fresh HAOS 18.3 guest runs actual x86_64 Linux under QEMU/TCG on the
Mac ARM host. Its official qemux86-64 Core **2026.10.2** image is recorded as:

`45f009d6ff1061971102e81f0802cf2762bdd5c5007231c938bd36030cbd0a12`

| Scope | Current evidence | Candidate acceptance |
| --- | --- | --- |
| Fresh HAOS 18.3 ARM64 runner | Managed Core 2026.10.2 booted; target environment identified; the local VM was later stopped | Environment preparation only |
| Separate ARM64 Core 2026.10.2 QA container | Exact candidate verified; active dependency closure, native runtime, regression suites, upgrade and recovery checks passed | Qualified QA-container scope below |
| Parallel ARM64 Core 2026.9.4 container | Same exact candidate passed native/lifecycle, 1,443 backend tests and both upgrade/recovery sequences | Container scope; no managed Core 2026.9.4 service claim |
| HAOS-managed Core 2026.10.2 process | Core installed manifest dependencies, loaded the exact candidate through its real flow, then restarted with the saved configuration intact | Passed for the explicit synthetic Person/tracker setup below |
| Fresh HAOS 18.3 x86_64 guest under QEMU/TCG, Core 2026.10.2 | Actual Linux native/lifecycle, 1,443 backend tests and managed Core installation/flow/restart/native checks passed | Emulated CPU scope; separate full AMD64 upgrade/recovery follow-up failed its bounds and remains unqualified below |
| Native x86_64 Ubuntu 24.04 CI host, pinned Alpine/musl Core 2026.10.2 Docker container | Both ten-phase exact-baseline upgrade/rollback sequences and twenty-process full synthetic recovery passed | Native AMD64 container scope; no native HAOS-managed service, glibc Core, backend-suite or separate worker/lifecycle rerun claim |
| Native x86_64 Ubuntu 24.04 CI host, pinned Alpine/musl Core 2026.9.4 Docker container | Full 1,443-test backend suite plus one optional skip, native worker/lifecycle, both upgrades and full recovery passed | Minimum-Core native AMD64 container scope; see the October 20 result below |
| Native x86_64/KVM HAOS 18.3, managed Core 2026.10.2, HACS 2.0.5 | Eight phases passed: genuine HACS published install/rollback, two stopped exact-candidate installs, restart/selection/identity persistence and latest-guard continuity | Synthetic managed service; candidate HACS delivery and OAuth remain open. This run excluded Supervisor backups/Recorder; the prepared partial scope is recorded separately below |
| Native x86_64/KVM HAOS 18.3, managed Core/Supervisor 2026.10.2, prepared disabled-entry partial backup | Six phases passed genuine Supervisor backup/restore including Recorder, exact history rollback/new recording, saved selections/identities and manually retained newest guard | Prepared synthetic partial scope; ordinary enabled-entry/full-system restore and automatic anti-rollback remain open |
| Linux glibc and additional targets | Earlier official-wheel and ELF checks retain their dated scope | Actual runtime acceptance pending |

A QA-container result establishes behavior in the recorded image and architecture.
Actual loading by the separate HAOS-managed Core process is a further check of
manifest dependency installation and integration startup. Neither result alone
establishes a different recorded target, libc, Core version, live Apple recovery,
production upgrade or physical-display acceptance.

## Offline native and worker checks

The existing [platform validator](../scripts/platform_validate_candidate.py)
binds its receipt to the exact candidate archive, checks the active installed
dependency closure against Core constraints, and runs the packaged worker with
a generated Mach-O dispatcher. It separately requires the unchanged production
library verifier to refuse that synthetic image. It uses no Apple binary,
account, owner configuration or external request.

The new Linux-only [worker lifecycle validator](../scripts/platform_validate_linux_lifecycle.py)
additionally imports the actual `provider.Worker` from the extracted candidate
and exercises its real asyncio pipe and process-ownership paths. It requires:

- Successful open/check/close, repeated close, cleared process handles and absence
  of each reaped PID from `/proc`.
- The actual Unicorn 2.1.4 package copied into a disposable dependency directory
  visible only to the parent; the child must use the worker's explicit package
  loader to load that copy.
- Observed live child limits of 90 CPU seconds, zero core-dump bytes and 3 GiB
  address space.
- Cancellation after CPU progress proves an active synthetic native call, followed
  by the real provider's kill/wait cleanup and PID disappearance.
- Unchanged extracted candidate files, denied external networking and complete
  disposable-storage cleanup.

The validator refuses non-Linux execution before inspecting an archive or
launching a child. Only its in-memory synthetic library digest/length and loader
observation are substituted; candidate source and package bytes remain unchanged.
The outer probe owns a new process group and tears it down on unsuccessful
outcomes, including interruption or an exited probe with surviving workers.

Source review found and corrected two cleanup defects in this new validator
before execution: suppressed close errors and incomplete process-group cleanup
after probe failure/interruption. Six focused guard/parser/fixture/cleanup test
cases cover these checks. These are harness changes, not confirmed candidate defects.
All six cases passed in the completed Linux backend suite.

The exact-archive native check passed with **24 installed dependencies** in its
active closure and **no Core constraint mismatch**. Mandatory imports, synthetic
native dispatch and production-hash refusal passed. The lifecycle check passed
with the parent-only Unicorn copy, verified live limits and active native
cancellation. Both owned workers were killed by the provider's normal close
path, reaped and absent from `/proc`; temporary storage was removed. These are
synthetic guest instructions, not an Apple binary or provisioning acceptance.

## Public anonymous Apple runtime

A separate exact-candidate runtime check completed with outcome **ready** on
ARM64 Core **2026.10.2**. It verified the pinned public installer/library, made one public
download and three anonymous provisioning requests, generated OTP headers,
round-tripped the encrypted vault and restored the same identity with a stable
machine ID in a cold worker. All four workers were reaped and disposable storage
was removed. It made **zero Apple-account requests**, read no owner data and
accessed no locations. This check does not sign into an owner account or perform
Keychain recovery.

## Regression, upgrade and recovery results

The final ARM64 Core **2026.10.2** backend run passed **1,443 tests**, with **one optional public
installer fixture skipped**, in **41.76 seconds**. This is the expanded Linux suite;
the earlier 1,430-test Mac checkpoints retain their own dated scope. Ruff passed,
and the public-file guard checked **326 files** without flagged patterns. The
automated privacy scan does not replace manual review.

Both exact upgrade baselines passed ten phases each: the immutable published
beta 19 archive and the reconstructed recorded-patch archive, for **20 separate
Linux Core processes**. These cover upgrade, restart, identity-ledger persistence,
package-only rollback, re-upgrade and matching complete-backup restoration. Saved
people/items, options, places, entity IDs, encrypted account material, HomeCircle
activity, request reservations, portrait bytes and HTTP delivery, dashboard,
resource identity and served card bytes were preserved within the documented
scope. Only the final report transport was replaced with an empty response;
external connections were denied. The existing package-only rollback limitation
remains: published beta 19 polling drops the newer identity ledger, while the
matching stopped package and complete storage backup restore its recorded state.

The full synthetic recovery/repair sequence also passed in **20 distinct Linux
processes**. All **40 network-denial probes** were blocked, with **zero unexpected
network attempts and zero Apple requests**. It covered interrupted migration,
guard locks/acknowledgment/corruption, encrypted-vault corruption/wrong-key/foreign
account refusal, matching backup restoration and retained newer guard state.
All ordinary children exited zero; explicitly expected fault exits remained
separate. This exercises the Core storage lifecycle and recovery functions,
not a live owner recovery or a full integration lifecycle in each recovery child.
Synthetic recovery storage was removed.

Two confirmed QA setup defects were fixed before these final runs. The official
image's distribution metadata did not identify the imported Core source tree, so
the platform validator now reads constraints beside the active imported Core and
has origin-selection regressions. The installed `tests` package also collided
with the checkout's namespace; a local `tests/__init__.py` and consistent helper
imports make collection explicit. These were validation-environment defects;
the exact candidate archive and runtime source remain unchanged.

### First AMD64 full-suite invocation and recovery-test deadline

The first full AMD64 run returned **one failed, 1,439 passed and one skipped** in
**528.05 seconds**. That is a failed invocation. Its sole failure was the
recovery test wrapper's 90-second aggregate subprocess deadline. The retained
receipt contains 12 completed guard phases with their expected exits/statuses;
the thirteenth started about 83 seconds after the first and had no completed
receipt when the parent deadline expired. No guard assertion failure appears in
those partial records, and the incomplete phase is not a passing result.

The reviewed QA-only correction derives a **790-second aggregate allowance**
from the 13-process plan: `12 * (45 + 10) + 60 + 10 + 60`. Individual child limits remain **45 seconds**, bounded
reaping remains **10 seconds**, and the held child's watchdog remains **60
seconds**. The test wrapper also owns a fresh process group and kills/drains it
on failed exit, timeout, interruption or receipt-validation failure, including
descendants whose leader already exited. Three fake-process regressions cover
timeout, an exited probe and invalid receipt cleanup. The complete ARM64 suites
were rerun after these validation changes; their final counts above and below
include the three new cases. No candidate runtime limit or source changed. The
focused AMD64 rerun passed the actual 13-phase guard plus the three cleanup
regressions: **four tests passed in 94.44 seconds**. The corrected full AMD64 run
then passed **1,443 tests**, with **one optional public installer fixture
skipped**, in **473.70 seconds**. Its job exited zero. The first failed invocation
remains retained as failed evidence.

## ARM64 Core 2026.9.4 container

The parallel official Core 2026.9.4 container completed the same exact-candidate
native and lifecycle checks with **24 installed dependencies** and **no Core
constraint mismatch**, including setuptools **81.0.0** and protobuf **6.32.0**.
The native worker executed, the production verifier refused the synthetic image,
and the real provider's dependency-path, live-limit, cancellation and reaping
checks all passed.

Its final full backend run passed **1,443 tests**, with **one optional public installer
fixture skipped**, in **41.31 seconds**. Both exact upgrade baselines completed
ten phases each, for **20 additional Core processes**. The full recovery/repair
sequence passed in **20 distinct processes**, with **40 blocked network probes**,
zero unexpected network attempts and zero Apple requests. The same rollback and
synthetic-storage scope limits apply. The bounded QA container's main job exited
zero when complete.

Each result runs the same expanded test suite on a separate target.
This qualifies the recorded Linux ARM64 Core 2026.9.4 **container** environment;
the HAOS-managed Core service remained 2026.10.2. No managed 2026.9.4 setup or
owner-account acceptance is claimed.

## Actual HAOS-managed Core loading and restart

The exact candidate was also installed into the fresh HAOS-managed Core
**2026.10.2** instances on **ARM64 and x86_64**, separately from their QA
containers. The latter is the emulated QEMU/TCG guest. Core installed mandatory
manifest dependencies through the normal integration-loading path; the managed
instances did not receive the QA containers' test SDKs or pytest extras.

The exact-ZIP native validator then also passed inside both managed Core
containers: all mandatory imports, each 24-dependency active closure, imported-Core
constraints, synthetic native dispatch, production-hash refusal and process
reaping. The ARM64 managed closure differs from its QA container for unpinned
transitive dependencies: managed Core resolved certifi 2026.10.18 and multidict
7.1.0, while QA retained certifi 2026.7.22 and multidict 6.9.1. Both complete
inventories are retained and both satisfy the active Core constraints. The
x86_64 managed closure also passed with certifi 2026.10.18 and multidict 7.1.0.

A temporary helper integration outside the candidate used Home Assistant's
supported persistent-Person creation API and the actual HomeCircle configuration
flow. It explicitly selected that synthetic Person and a synthetic tracker at
0,0, assigned the tracker, confirmed the member settings and saved. The candidate
loaded with its real frontend resource and automatically created dashboard.
No owner user, API credential, Apple account or direct provider was used, and no
HomeCircle code or service was patched.

The helper recorded all **112 installed file hashes** against the exact candidate
inventory before and after a normal managed-Core restart on **each architecture**.
Each fresh process had a different Linux start token. Within each instance, the
stored entry ID, selected Person/tracker and
their registry IDs, entry data, empty options, runtime-configuration digest,
owned frontend resource ID/URL and dashboard ID/configuration digest were
identical. The helper found and verified the saved entry and Person after
restart; it did not recreate them or repeat the configuration flow. All four before/after receipts
passed. These are independent synthetic instances, not shared registry IDs
between architectures.

This proves fresh managed installation, explicit provider-independent selection
and restart retention for that synthetic setup. It is separate from the fuller
QA upgrade/recovery scenarios and does not claim a current production/HACS
upgrade, nonempty options coverage in this managed check, owner-account access,
live location reports or physical-display acceptance.

## Results and remaining work

| Check | Status |
| --- | --- |
| Exact candidate archive/inventory in Linux | Passed; same 112-file SHA-256 |
| Manifest dependency installation and Core constraint agreement | Passed in QA container; 24 installed dependencies, no mismatch |
| Packaged native dispatcher and production-hash refusal | Passed |
| Real provider worker limits, dependency path, cancellation and reaping | Passed |
| Public anonymous Apple runtime | Ready; four workers reaped, no owner/account/location access |
| ARM64 backend regression suites | 1,443 passed and one optional fixture skipped on each of Core 2026.9.4 and 2026.10.2; 41.31/41.76 seconds respectively |
| Emulated AMD64 Core 2026.10.2 backend suite | 1,443 passed and one optional fixture skipped; 473.70 seconds |
| Exact candidate loaded by HAOS-managed Core after restart | Passed on ARM64 and emulated x86_64; all 112 hashes and each instance's saved identity/configuration/resource/dashboard snapshot retained |
| Native execution and installed closure inside managed Core containers | Passed on ARM64 and emulated x86_64; 24 dependencies each, no active Core constraint mismatch |
| ARM64 exact-baseline upgrade/rollback and recovery restart sequences | Passed on each Core target within the synthetic scope above |
| Linux amd64 execution | Native/lifecycle, full backend suite and managed setup/restart/native checks passed under QEMU/TCG |
| Native AMD64 Core 2026.10.2 container upgrade/rollback and full recovery | Passed October 20: 20 upgrade phases across both exact baselines, 20 recovery processes and 40 blocked probes; unchanged frozen candidate and CLI limits |
| Native AMD64 Core 2026.9.4 container full suite and acceptance | Passed October 20: 1,443 backend tests plus one optional skip, native/lifecycle, both upgrades and full recovery; unchanged frozen candidate and child limits |
| Prepared native HAOS Supervisor partial backup and Recorder restore | Passed six phases: actual database/history rollback, renewed recording across restart, application-state continuity and manual newest-guard preservation |

Each backend result runs the same expanded suite on a separate target. The full
emulated AMD64 upgrade/recovery follow-up below failed its bounded checks. The
later native AMD64 container runs passed those synthetic scenarios separately;
the minimum-Core run also passed the full backend and native/lifecycle checks.
Native AMD64 HAOS synthetic activation, persistence and rollback now pass below.
Glibc and additional runtime scopes remain unqualified; candidate HACS delivery
and ordinary enabled-entry/full-system Supervisor restoration remain open. The
prepared disabled-entry partial-backup protocol and synthetic Recorder continuity
pass in the later record below. The previous Mac
finalization crashes remain unattributed; this phase does not claim to repair
their cause. Live recovery, long-term report behavior, current production installed-state
and HACS upgrade, production Recorder continuity, physical DAKboard acceptance and the
remaining license/service-use gates remain separate.

Ignored runner records, exact-input receipts and Linux outputs are retained
under `work/linux-haos-validation/`. Public reports contain no owner records,
credentials, private identifiers or locations.

## October 19 follow-up: AMD64 upgrade, rollback and full recovery

**These emulated attempts failed; no passing upgrade/rollback or recovery result
from this follow-up.** The [later native container run](#october-20-native-amd64-container-upgrade-and-recovery)
provides separate passing evidence. This
milestone reused the disposable HAOS 18.3 x86_64 guest and its official Core 2026.10.2
image under QEMU/TCG. It keeps the same frozen 112-file candidate digest above.
The earlier completed checks and first failed AMD64 backend invocation retain
their recorded results and limits.

The upgrade/rollback inputs were the same two exact 109-file baselines:

- Published beta 19: `5f20d536e1b5378bef7f0b972bbfbc7ced911063aea16a0a8f56d2ffa1210cd2`.
- Reconstructed recorded patch: `0362a71b0d12e12bbe38c20192f130f505011500e9a1d31a3531547c5055d80a`.
  This remains a reconstruction from retained hashes, not a fresh production
  installed-state snapshot.

| Follow-up check | Requested scope | Observed result |
| --- | --- | --- |
| Published-baseline upgrade/restart/rollback | Ten phases with exact package, loaded-version and saved-state checks | Two affected-clock attempts and the corrected-clock attempt failed at the first child deadline; zero completed phases |
| Reconstructed-baseline upgrade/restart/rollback | Ten phases with the same checks; 20 Core processes requested across both baselines | Not reached; unqualified |
| Full synthetic recovery/repair | Twenty distinct processes; guard, interrupted migration, vault refusal and matching backup restore checks | The affected-clock and corrected-clock attempts failed at the first child deadline; zero completed phases |
| Recovery isolation and cleanup | Complete probe accounting, retained-guard and temporary-storage acceptance | Unqualified; no complete 20-process/40-blocked-probe result |

### Failed follow-up invocation audits

The initial driver invocation and its quiet retry both **failed** in the older
published baseline's first `published_install` child at the unchanged
**180-second** deadline. Neither produced a completed phase receipt or assertion
result. Both drivers recorded `completed: false`, `outcome: failed` and no
completed jobs. Neither invocation counts as a passing upgrade, rollback or
recovery scenario; both input receipts still matched the frozen candidate and
both exact baselines.

Managed Core and Matter startup were observed concurrently under QEMU/TCG during
the first attempt. Both services were stopped before the quiet retry, and the QA
process list contained only its sleep process with no Python child. The second
attempt used a fresh result directory, the same pinned scripts and unchanged
**180-second child / 2,100-second complete-upgrade** limits. The timeout cause
remains unconfirmed. Both driver receipts and published-stage logs are retained
under `work/linux-haos-validation/amd64-upgrade-recovery/`.

The independent full recovery/repair attempt also **failed**. Its first
`guard_verified` child exceeded the unchanged **45-second** bound and was killed
with exit **-9**. The receipt marks `timed_out: true`, `completed: false`,
`failed: true` and `expected_fault_exit: false`; this was not one of the deliberate
fault phases. **Zero recovery phases completed.** The attempt does not establish
the requested 20-process sequence, 40 blocked probes or final recovery/cleanup
acceptance. It used the unchanged frozen CLI and reviewed owned-session runner
with a **1,200-second** outer bound; the existing **10-second reap** and
**60-second held-process watchdog** bounds were unchanged. Its driver, partial
receipt and inner log are retained alongside the two failed upgrade attempts.

### Bounded diagnostic and disposition

A separate diagnostic stopped after **203.737 seconds**, retaining the
**180-second phase** deadline and a **240-second total** bound. It recorded
`diagnostic_only: true`, `acceptance_pass: false` and `TimeoutExpired` for the
older published baseline's `published_install` phase. The candidate upgrade
phase was not reached. Repeated 30-second stack captures sampled Core and
SQLAlchemy imports at 30/60 seconds, startup translation/dependency-metadata and
mashumaro work at 90/120 seconds, and the published baseline's `indexed_keys`
elliptic-curve work at 150 seconds. These samples identify observed execution
paths; they do not establish the timeout cause or a candidate runtime defect.

The diagnostic verified all three archive digests, validation-script pins and
the exact 112-file candidate source inventory **before and after**. The
candidate, both baselines and public validation scripts remain unchanged.
Diagnostic outputs are retained under
`work/linux-haos-validation/amd64-upgrade-diagnostic/`. Seven synthetic driver
regression cases passed in Linux in **5.34 seconds**; these qualify the ignored
orchestrator's guards and cleanup, not either failed acceptance scenario. That
new helper's corrections bound the recovery source to the frozen candidate and
route SIGTERM/SIGHUP through owned-process cleanup; they do not change runtime
code.

No additional blind reruns or relaxed limits were part of this follow-up. Its
disposition required a faster/native AMD64 runner or a confirmed runner issue
and fix before another acceptance attempt. The native runner result below is
recorded separately.
The existing package-only rollback identity-ledger limitation and requirement to
retain the newest recovery guard still apply. These are synthetic QA-container
scenarios, separate from the already verified managed-Core setup/restart checks.
They do not add owner sign-in, live Apple recovery, current production/HACS,
Recorder or physical-display acceptance. Glibc, AMD64 Core 2026.9.4 and other
runtime targets remained unqualified at that checkpoint. No Mac Python or production/owner data is
part of this follow-up.

### Runner clock incident and gated retry

Cleanup exposed a confirmed clock-integrity problem in that emulated guest
boot: guest wall time froze while host time advanced, and guest uptime nearly
stalled and then moved backward. The kernel had marked TSC unstable and fallen
back to the 24-bit `acpi_pm` clock, with a reported maximum idle interval of about
2.085 seconds; the VM had HPET disabled. The failed attempts above remain failed
and incomplete. Their configured deadlines and guest-reported elapsed times,
including the diagnostic's 203.737 seconds, are retained audit values, not
independently validated host durations. This runner issue does not establish the
sole cause of any earlier timeout or a candidate defect.

Only the stopped disposable AMD64 VM's supported UTM setting
`QEMU.MachinePropertyOverride = hpet=on` was changed. The before/after
configuration comparison found no other semantic change; the generated machine
arguments include `q35,hpet=on,vmport=off`. The next boot selected `tsc`, with
`tsc hpet acpi_pm` available. Candidate code, the three frozen archives and the
pinned validation scripts were not changed.

The first host-clock gate **failed overall** because its QA criterion rejected
a guest sleep of 5.81 seconds above a fixed 5.5-second ceiling, although it
completed within a 6.463-second host observation envelope and both clock-rate
interval checks passed. That receipt is retained. The reviewed second criterion
separates clock rate/drift from timer liveness: two 30-second host/guest timestamp
intervals check clock rate, and three minimum-wait probes must complete within
independent 15-second host bounds. It does not require exact five-second
scheduler performance. Seven host Ruby regression cases cover the corrected
gate criteria separately from the seven Linux orchestrator cases above.

The second gate **passed for runner clock behavior only**, in about **78.83 host
seconds**. TSC stayed selected, both interval comparisons passed and all three
timer-liveness probes completed within their host bounds. Its receipt explicitly
records `outcome: passed_clock_gate_only`; it does not record candidate acceptance.
Both gate receipts, raw host/guest brackets and helper hashes are retained under
`work/linux-haos-validation/amd64-clock-fix/`.

The confirmed runner change and this bounded gate supported a new acceptance
attempt with the unchanged exact-input driver, independent host watchdog and
30-second host/guest clock monitoring. The gate adds no candidate acceptance
pass. Earlier failed attempts and all owner, production, rollback and other
platform limits remain in force.

### Corrected-clock upgrade and recovery outcomes

The corrected-clock full upgrade attempt **failed** after **260.377106 host
seconds**, measured by the independent host monitor. All **eight workload clock
checks passed**, with TSC selected throughout. Nevertheless, the older published
baseline's first `published_install` child still exceeded its unchanged
**180-second** deadline. The driver recorded `completed: false`, `outcome: failed`
and no completed jobs. There was no valid phase JSON or candidate phase result;
the reconstructed baseline was not reached. Both baselines' full upgrade/rollback
acceptance in this emulated attempt therefore remains **unqualified**, and no candidate
runtime defect or sole timeout cause is established.

The same official QA image, exact-input driver and frozen candidate/baseline
inputs were retained. The host monitor confirmed the exact QA container stopped
after the failure, with no host cleanup failures. The host receipt, guest driver
and published-stage log are retained under
`work/linux-haos-validation/amd64-clock-fix/`, including
`host-monitor-20261020T043333Z-fd9f36390ff4664917556f90/host-monitor.json`.

The one separate corrected-clock full recovery attempt also **failed**, after
**110.627503 host seconds**. All **three workload clock checks passed**, with
TSC selected. Its first `guard_verified` child exceeded the unchanged
**45-second** deadline and was killed with exit **-9**. The single partial
receipt records `timed_out: true`, `completed: false`, `failed: true` and
`expected_fault_exit: false`. **Zero recovery phases completed**, and the driver
recorded no completed jobs. This is no full recovery, 20-process or
40-blocked-probe acceptance result.

The recovery driver's archive/script pins and exact 112-file source inventory
matched before and after execution, with `candidate_changed: false`. Its exact
QA container was confirmed stopped, with no unresolved container cleanup or
host cleanup failures. The host receipt is retained under
`host-monitor-20261020T044327Z-4a96a26653de349c07532360/host-monitor.json`, alongside
`hpet-recovery-driver.json`, `hpet-recovery.json` and `hpet-recovery.log` in the
same ignored clock-fix evidence directory.

Both full upgrade/rollback and full recovery in these emulated attempts remain **unqualified**. The
corrected-clock failures do not establish a candidate bug or a sole timeout
cause. **No further emulated retries were part of this milestone.** Earlier failed
attempts, the clock incident and gate failure, and all prior passing scopes and
remaining release limits are preserved.

## October 20 native AMD64 container upgrade and recovery

The authorized [GitHub Actions run 39426549335](https://github.com/jmhjr/HomeCircle/actions/runs/39426549335)
**passed** on a native x86_64 Ubuntu 24.04 host, kernel
`6.17.0-1022-azure`, at validation revision
`50f9fa38ca3f88e68a9734637ec1ec84203ce8dc`. The host wrapper measured
**223.990 seconds**, including preparation, acceptance and owned-container
cleanup. This is a new native runner result; it does not convert the earlier
QEMU/TCG attempts into passes or identify their sole timeout cause.

Acceptance ran inside the same pinned official **Core 2026.10.2** image,
**Python 3.14.6**, **Alpine 3.24.1/musl**, with actual container architecture
`x86_64`. The registry reference was
`ghcr.io/home-assistant/qemux86-64-homeassistant@sha256:45f009d6ff1061971102e81f0802cf2762bdd5c5007231c938bd36030cbd0a12`.
Docker separately recorded local image ID
`sha256:e1acee126eee45b3007494ad7f806d12535dc7d733624b681ed29a505f8c2b98`;
the registry digest and local image ID are different identifiers. All **24
manifest dependency-closure packages** satisfied the active Core constraints,
whose SHA-256 remained
`7baa9a8f39ddeb9c5bb60a1036f6d5e33f4b84267f151f53cc2b95ef031a21b5`.
Only the six manifest requirements were requested; their 24-package closure was
verified. The test plugin and reference SDK were unnecessary for these standalone CLIs.

The frozen exact-input driver retained SHA-256
`c910ef815d34eb4379bf3f0e1fd6dad31d95986a287b9e32263f9b87b60de373`.
The candidate digest, all **112 files**, both exact **109-file baselines**,
inventory and validation-script pins matched. Setup verified fixed hashes before
extracting or importing candidate code. Dependency downloads were confined to
setup; the container had **no connected Docker network** during acceptance and
no host bind mounts or Docker socket. The existing **180-second upgrade child**,
**45-second recovery child**, **10-second reap** and **60-second held-process
watchdog** limits were unchanged; the native outer acceptance bound was
**5,520 seconds**.

| Native container check | Result |
| --- | --- |
| Canonical published beta 19 → candidate, restart, rollback and coherent backup restoration | Ten phases passed |
| Reconstructed recorded patch → candidate and the same rollback/restoration checks | Ten phases passed; this code reconstruction remains separate from current production installed state |
| Full synthetic recovery and repair | Twenty distinct processes passed, including the expected deliberate fault exits and held-lock kill |
| Recovery network accounting | All 40 probes blocked; zero unexpected network attempts or Apple requests |
| Exact source, package and persistence assertions | Passed through the frozen driver, with final input/source matching |
| Host outcome and ownership cleanup | Acceptance and runner exited zero; exact owned container stopped and removed; `cleanup_failed: false` |

The package-only rollback identity-ledger limitation remains: published beta 19
can drop the newer ledger. Coherent matching backup restoration and retention of
the newest independent recovery guard are still required. No candidate runtime
fix, package rebuild, version change or production deployment was needed.

With explicit authorization, only the isolated public branch
`codex/native-amd64-validation` received the payload and workflow commits
(`2623de5` and `50f9fa3`). The main branch and the local working checkout/HEAD
were unchanged by that publication; no release or tag was created. The Actions
job completed successfully. Its upload action produced a nonblocking Node 20
deprecation/forced-Node-24 annotation; the artifact upload still succeeded.

Only **three sanitized JSON summaries** were uploaded and downloaded:
`host.json`, `setup-summary.json` and `candidate-summary.json`. The artifact is
**2,026 bytes**, retained by GitHub for **seven days**, with archive digest
`sha256:de782349ac77e0f9bcc08fc08961a395bf35cb67d580ab73972ddd4e466abc6a`.
Downloaded summaries and run/artifact metadata are retained under
`work/linux-haos-validation/native-amd64/`. Raw synthetic configurations,
per-phase receipts and logs were collected locally inside the ephemeral runner
for the bounded run, then were **not persisted in the uploaded artifact**. The
public summaries report the frozen driver's validated outcome; they are not a
retained raw per-phase archive. An independent read-only cross-check found the
three downloaded summaries, successful CI status and artifact archive digest
consistent with one another.

This closes the two-baseline upgrade/rollback and full synthetic recovery scope
for this native AMD64 **Core 2026.10.2 musl container**. The 1,443-test backend
suite, separate packaged-worker/native lifecycle validators and anonymous Apple
runtime were **not rerun** on this CI host. Native AMD64 HAOS-managed Core,
Supervisor/HACS behavior, glibc Core runtime and additional targets remain
unqualified at this checkpoint. The subsequent Core 2026.9.4 native AMD64
container result is recorded below. Ubuntu's host libc does not establish glibc
acceptance for Python running inside the musl container. Owner sign-in/live
Apple recovery, current production installed-state/HACS upgrade, Recorder
continuity, long-term field behavior, physical DAKboard acceptance, external
assurance and remaining licensing/service-use gates remain open. No Mac Python
or owner/production configuration was used.

## October 20 minimum-Core native AMD64 validation

[Actions run 39433931788](https://github.com/jmhjr/HomeCircle/actions/runs/39433931788)
**passed** at validation revision `c92a0c579ea7c03dd0ed238dfb5ede2c7661d73b`,
closing the native AMD64 container scope for the **Core 2026.9.4 minimum in
`hacs.json`**. The native x86_64 Ubuntu 24.04 host used kernel
`6.17.0-1022-azure`; total preparation, acceptance and cleanup took **534.500
host seconds**. Python ran only in Linux.

The official image reference was
`ghcr.io/home-assistant/qemux86-64-homeassistant@sha256:414dce485b4eebd9f929f293f7252340bada5715fc4a48b2b954d79195ed3019`;
Docker's distinct local image ID was
`sha256:560be76a9ee5019c1b557241db8d1127550f21fba952a1a976c3d186f9b2cd9e`.
Actual Core **2026.9.4**, Python **3.14.6**, x86_64 and the **24-package
manifest closure** were checked against Core constraints SHA-256
`962c9ccaf398e0b92b10ac9f765ac0f17e22238adc4e768deebc051ee8b60651`.
The test plugin was `pytest-homeassistant-custom-component==0.13.367` and the
test-reference SDK was `findmy==0.10.2`. Neither changes the candidate manifest.
The Python runtime remains Alpine/musl; the Ubuntu host does not qualify glibc Core.

| Minimum-Core native container check | Result |
| --- | --- |
| Complete backend suite from the 326-file public source snapshot | **1,443 passed**, one explicitly named optional public-installer fixture skipped |
| Actual packaged native worker and production-hash refusal | Passed; worker reaped, no Apple binary executed |
| Provider lifecycle and active native cancellation | Passed, including parent-only dependency, production process/pipe contracts and child limits |
| Published beta 19 and reconstructed recorded patch → candidate, restart, rollback and matching stopped backup restoration | Both ten-phase sequences passed |
| Full synthetic recovery | Twenty distinct processes and all 40 blocked network probes passed |
| Exact package/input/source verification | Frozen candidate `f0477a91e78181fe1f8d80ada176a1739e10a7502abe7ee6ee2240571280d1f5`, all 112 files, baseline/script pins and post-run inputs matched |
| Isolation and cleanup | Docker networking disconnected during acceptance; no host binds/socket; acceptance and runner exited zero; owned container stopped and removed |

The separately hashed Core 9.4 driver
`b5868eb974456b36f1fedbccea59f3b9a76a4bddba264806dc9c4c481ad8877c`
differs from the frozen Core 10.2 driver only in its two Core-version checks.
The existing 180-second upgrade child, 45-second recovery child, 10-second reap
and 60-second held-process watchdog limits remain unchanged. The full-suite
wrapper adds bounded native/lifecycle/backend stages rather than relaxing those
children. Zero unexpected network attempts or Apple requests were accepted.

Preparation review removed Mac extended metadata from the public-source archive
before upload and retained the source-only README outside the installed component,
preserving its exact 112 files. Two initial CI runs
([39432817188](https://github.com/jmhjr/HomeCircle/actions/runs/39432817188),
[39433370019](https://github.com/jmhjr/HomeCircle/actions/runs/39433370019))
failed during source staging with `PermissionError`, before candidate acceptance.
The diagnostic located a new test-source file write in the scripts directory.
The host wrapper now creates root-owned writable parents inside the restricted
container and copies fixed files individually. Both failed attempts retained
clean stop/removal receipts and remain failed setup attempts. No candidate code,
dependency pin, container capability or inner deadline was changed for the pass.

Only three sanitized JSON summaries were persisted in the **2,121-byte**,
seven-day CI artifact, whose downloaded ZIP matched SHA-256
`e89d6ad1835d6ef07d187396bdbd4c2edae742e196250a48bd734a5e9f3c94fe`.
Local copies, run metadata, CI logs and both setup-failure records are retained
under `work/linux-haos-validation/native-amd64-core94/`. Raw synthetic configs
and per-phase logs/receipts were collected inside the ephemeral runner but were
not uploaded. The 1,443 tests are the same suite used on earlier targets, not
additional unique test cases.

This result adds minimum-Core native AMD64 container acceptance. It does not
rerun the separate Core 10.2 backend/native/lifecycle scope, anonymous Apple
runtime, managed HAOS/HACS, Supervisor backups, owner recovery or production.
Package-only rollback's identity-ledger limitation and preservation of the newest
independent recovery guard still apply. Release/version/tag, main, production,
owner accounts and the frozen V2 reference remain unchanged.

## October 20 native HAOS and HACS rehearsal

[Actions run 39441631322](https://github.com/jmhjr/HomeCircle/actions/runs/39441631322)
**passed all eight phases in 344.041 host seconds** at validation revision
80af07bb829c68bda93269c2726d8549aca3338a. All **23 offline controller
contracts** also passed in the Linux job. This qualifies the synthetic native
AMD64 managed-service scope described here, with a separate limitation for
candidate HACS delivery.

The fresh native x86_64/KVM guest used official **HAOS 18.3**, actual managed
**Core 2026.10.2**, observed **Supervisor 2026.10.2** and **CLI 2026.09.0**,
with unchanged official **HACS 2.0.5**. QMP confirmed KVM was enabled. The pinned
HAOS compressed image SHA-256 was
`fae6a728768cc10aff60d4820bfcd40d64cd77fab82c8bd92af13b3d9d414090`;
the HACS asset SHA-256 was
`97be6b824a4f38e683728cc6dd72367f6b8bad0a43428b1b3b987a3087adf413`.

The rehearsal distinguishes actual HACS transport from local candidate staging.
Unmodified HACS installed the canonical published beta 19 and later downloaded
that release again for rollback, each checked against all **109 exact files**.
HACS's prerelease-only catalog resolved the requested nondefault candidate branch
back to `main`; no catalog entry, downloader or quota response was patched.
Consequently the exact frozen candidate's **112 ZIP files** were installed twice
only while Core was stopped, with every byte verified before Core restarted.
Candidate HACS branch/release selection and release-ZIP transport remain open.
HACS metadata intentionally continued to record the published beta 19 throughout
the manually staged candidate phases.

The disposable HACS entry used only the job's temporary read-only repository
token, kept inside the private guest. Official OAuth/browser onboarding was not
tested. The guest used public NAT downloads without host directory mounts or
forwarded ports. No owner, Apple, production or household account was configured.
Each management action required Supervisor's running lifecycle state and idle
relevant Core jobs, sent one supported CLI request, checked its result, and
observed the actual container transition within its unchanged 180-second bound.

Before this result, five preparation/fixture attempts remained incomplete:

| Run | Retained outcome |
| --- | --- |
| [39434815755](https://github.com/jmhjr/HomeCircle/actions/runs/39434815755) | 48.118 host seconds, zero phases; managed Core version refused |
| [39435778433](https://github.com/jmhjr/HomeCircle/actions/runs/39435778433) | 64.305 seconds, zero phases; update refused while the landing page was observed |
| [39436791538](https://github.com/jmhjr/HomeCircle/actions/runs/39436791538) | 114.209 seconds, zero phases; required stopped Core state not reached; raw stop result was not captured |
| [39438686151](https://github.com/jmhjr/HomeCircle/actions/runs/39438686151) | 183.041 seconds; genuine HACS 109-file install passed, then the post-restart catalog lacked the published tag |
| [39439983656](https://github.com/jmhjr/HomeCircle/actions/runs/39439983656) | 192.054 seconds; genuine HACS install passed, then the served-bundle assertion failed before any candidate install; HTTP status was not retained |

Confirmed harness corrections wait for a real non-landing-page Core and idle
Supervisor jobs, use normal guest HTTP binding for Supervisor health checks,
refresh a missing tag through HACS's supported API, and use the active
`hass.http.server_port` instead of assuming port 8123. Official Core defaults
Supervisor installations to port 80 and can redirect legacy 8123 during
onboarding; the earlier receipt does not prove that redirect was the sole cause.
The final probe still requires HTTP 200 and exact bundle bytes, with bounded
reads and only numeric/hash/category diagnostics on failure. Atomic phase
instructions and narrow failure projections also prevent helper races or raw
log disclosure. Independent review cleared these changes; no candidate code,
dependency pin, inner timeout or acceptance condition was weakened.

The real HomeCircle flow created two persistent fictional Persons with explicit
registered tracker selections. A nonempty OptionsFlow save disabled city lookup
and reloaded the integration. Config-entry data/options, runtime configuration,
Person/tracker registry identities, owned and unrelated resources, dashboard
identity/content and exact served bundle checks passed through candidate,
rollback and reinstallation. The persistent snapshot hash remained identical.
Required restart pairs had different actual Core process start times. The
initializer source itself is unchanged between these packages; the evidence is
the new process, exact installed package and actual candidate safeguard API.

Three local synthetic refusals seeded the candidate recovery guard without a
provider exchange. Rollback restored the matching stopped storage/image snapshot
while retaining the newest independent guard. The older release's rollback
check verified retained bytes, not the newer guard API. Reinstalling the
candidate confirmed the same guard hash and actual API status **blocked with
three unresolved attempts**. HACS stayed enabled with zero queued tasks at every
phase. This managed check did not repeat the container's forty blocked probes.

All thirteen one-shot Core stop/start requests returned ok and reached their
required actual state. The final Core was stopped, the exact owned QEMU process
was stopped and the entire private VM/token/configuration/backup/log workspace
was removed, with no cleanup failure. Only **eleven sanitized JSON receipts**
were uploaded as a **5,976-byte**, seven-day artifact. The downloaded ZIP matched
SHA-256 196a571eeda1b672e50d415bb3c7c1391164d20e4208712bc0489a7458feef50.
Raw synthetic state and guest logs were not uploaded. Run metadata, CI logs,
sanitized receipts and verified artifact are retained under the ignored
native-haos-hacs evidence directory.

This is synthetic managed-service activation, persistence and local safeguard
continuity. It does not rerun the complete backend/native-worker suites inside
managed Core or the container's twenty-process recovery scenarios. Matching
stopped `.storage` and `image` copies are not Supervisor backup/restore or
Recorder continuity proof. Owner/live recovery, current production installed
state, candidate HACS delivery, long-term field behavior, physical DAKboard,
glibc and the remaining license/service-use gates stay open. No Mac Python,
release, tag, version change, main update or production deployment was involved.

## October 20 guarded Supervisor backup and Recorder restore

[Run 39452393848](https://github.com/jmhjr/HomeCircle/actions/runs/39452393848),
at revision `a11542b52d1b2020586da57b091978cd8176f4fb`, **passed all six
phases in 309.430 host seconds**, including preparation and cleanup. All **42
offline controller contracts** passed separately in 0.023 seconds. This is an
actual Supervisor backup/restore, distinct from the earlier stopped filesystem
restoration.

This separate native x86_64/KVM rehearsal uses a fresh official HAOS 18.3 guest
and actual managed Core 2026.10.2. It observed Supervisor 2026.10.2 and
CLI 2026.09.0, and checks the supported command flags before
issuing exactly one backup and one restore request. The unchanged candidate ZIP
retains SHA-256 `f0477a91e78181fe1f8d80ada176a1739e10a7502abe7ee6ee2240571280d1f5`
and all 112 files. There is no HACS operation or GitHub token inside the guest.

The operation is a genuine **Supervisor partial Home Assistant backup and
restore, including Recorder's database**. The controller checks the exact
returned backup/restore jobs and their bounded child trees for completion and
errors. It inspects the private uncompressed archive for the database, exact
candidate package, persisted disabled entry and older recovery guard. The
archive, database, configuration and raw history never become public artifacts.

Supervisor automatically starts Core before restore returns. The test therefore
deliberately disables HomeCircle through the supported config-entry API, waits
for unload and the actual saved disabled/options state, and backs up that
quarantined installation while Core and Recorder remain running. It verifies
the registered genuine Recorder backup platform and uses the actual live hooks.
After backup, a real options-flow change, committed history markers and three
local synthetic recovery refusals create distinguishable newer state.

The newest guard and the private post-backup history window are independently
retained outside the replaced configuration. After Supervisor restore, a fresh
automatic-boot observation must show HomeCircle disabled, not loaded and not
imported. Core is then stopped. The controller proves the restored guard equals
the older backup, separately proves the retained newest guard differs, and
promotes/checks the newest bytes before another disabled boot. Fresh QA
generation/nonce controls prevent restored stale receipts from counting as
progress. Only the explicit final phase may re-enable the entry after the
disabled-state and newest-guard checks.

The exact returned backup and restore jobs both completed with zero errors,
with three and four checked job-tree nodes respectively. The **2,846,720-byte**
partial archive matched SHA-256
`7c4deee95f409d60916d22ba12e401baadce26bd7d2cd2159eaa9d802ca17143`.
Archive inspection confirmed the database, exact 112-file package, saved disabled
entry and old guard. The actual pre-backup saved-store gate passed.

| Actual acceptance | Result |
| --- | --- |
| Pre-backup Recorder history | Ten committed timestamped rows retained exactly through restore and restart; closed-window SHA-256 `19d1c392555f452fa4744de05a1fbbebfbb9f9a09c261a30ce3367c7adee16ba` |
| Post-backup mutation | A changed options snapshot rolled back; ten separately committed marker rows were absent after restore |
| Renewed recording | Ten new committed post-restore rows remained exactly after another Core restart; SHA-256 `ec7e2006659a1b5727da7f776691443a3a96b2584eec12ed2b0d7bf9c75a6b37` |
| Recorder operation | Genuine backup platform registered, actual commit and history API checks passed, SQLite integrity passed and no backup-failure issue appeared |
| Restored application state | Entry/options, selections and Person/registry/dashboard/unrelated-resource snapshot returned exactly: SHA-256 `da0088837e6521ff860485c2c2baf31c7a7ecff008bd9fa2281e7e0b48c216ca` |
| Automatic restored boot | Fresh process observed disabled, unloaded and with no candidate import before any guard promotion |
| Guard ordering | Old guard `87e066171f45017a4a64fe53f0f6e54255a056460d4a11d60054a7d6f854967b` actually restored; separately retained newest guard `6a539827f2c55dc92c6221bc2edee2ad3e18ada0a2bccf607f2f502b9c309106` promoted while Core was stopped |
| Guard after explicit enable and restart | Actual candidate API remained blocked, with three unresolved and three rejected local synthetic submissions |
| Current resource | Owned ID changed on re-enable as expected, then remained stable through restart; exactly one current resource served the unchanged bundle |
| Cleanup | Owned QEMU process stopped, private workspace removed and no cleanup failure |

These are synthetic local recovery refusals; no passcode proof, Apple request,
provider account or owner data was used. The restored-quarantine phase verifies
the retained guard bytes without importing the candidate's guard API.

The guarded procedure preserves entry/options, Person/tracker/registry, dashboard
and unrelated-resource identity. Normal disable intentionally deletes HomeCircle's
owned card resource; re-enable must create exactly one current resource serving
the exact bundle. Its newly created ID must then survive the final restart.

Preparation review corrected a controller condition that treated a successful
void validation as a false boolean, preventing completion of a successful
operation. Its focused success-path contract uses the actual void-return
behavior. The HTTP probe requires status 200 and bounded exact decoded bytes,
without assuming compressed Content-Length equals decoded length. These are
validation-helper corrections; candidate code and the original bounds are
unchanged. Linux contract execution is separate from the timed VM rehearsal.

The first live attempt, [run 39450320492](https://github.com/jmhjr/HomeCircle/actions/runs/39450320492), failed after 174.772 host seconds at the backup CLI child, with initialize/quarantine passed and no restore reached. Its 35 offline contracts passed separately. The missing child error body prevents assigning a sole runtime cause. Its 2,726-byte sanitized artifact ZIP matched SHA-256 `313b1eb19198e7a1952be1a12822daf7f5775fbeb30ffdc1c155ad19b2ec18f9`.

Follow-up source review found that the CLI optional-value local-storage flag can leave a separate value as a rejected positional argument; both calls now use explicit `--location=.local`. Failed commands preserve bounded numeric exit/API/job error categories, with no raw text. The helper also waits for actual saved Person, registry and Lovelace stores because genuine live backup hooks do not flush all delayed collection writes. The added checks read disk and never force or rewrite Core stores. Candidate bytes, the 600-second guest phases, 180-second Core actions, 900/1,200-second backup/restore operations and 5,520-second controller bound remain unchanged.

The downloaded seven-JSON sanitized artifact is **6,221 bytes**, SHA-256
`79c7ec7c77e4fe2282b8d5593687a0c0cb2b17262edc693f7ffb7f773107c3a0`.
Its exact names and every member byte were independently verified against the
retained receipts. The full raw backup, database and configuration stayed private
inside the disposable runner and were removed. The archive is uncompressed and
unprotected because it contains synthetic data only; this does not qualify
encrypted-backup handling.

Executed controller SHA-256:
`0bf19f86e565c1b6a49392559d184537b8199c47c9a6a8356ad0709f8c9d5b0a`.
Executed guest helper SHA-256:
`9f037ee3ec7e2c8eff49229a67dba4cbd3432d7576c67bbe77956020180bd5cb`.
The fresh official HAOS image and candidate inputs matched their recorded pins.

This qualifies the deliberately prepared disabled-entry partial-backup protocol
for synthetic data. It does not qualify ordinary enabled-entry backups, full OS/
Supervisor/add-on restoration, encrypted/cloud portability, automatic guard
anti-rollback, owner/Apple recovery or current production data. Recorder's
synthetic rollback and renewed recording are separate from production history,
long-term retention and field acceptance. Candidate HACS delivery, live owner/
field/physical-display, other platform and remaining licensing/service gates
remain open. The newest guard is manually retained; Apple service allowance is
neither established nor reset. No Mac Python, production or V2 change, release,
tag or version change is part of this rehearsal.
