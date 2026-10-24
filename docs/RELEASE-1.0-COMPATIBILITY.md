# HomeCircle 1.0 compatibility disposition

Reviewed October 20, 2026. This maps the proposed eight qualification cells to
existing evidence and identifies remaining runtime checks. It does not
claim the complete matrix is qualified. Both direct Apple Find My and Life360
remain in the intended 1.0 scope; their account, assurance and permission gates
remain separate from platform validation.

## Exact current source and checked artifact

Canonical preparation source is
`9bf03eb45d2cf43274074534e9dfe2de841f4011` (337 inventoried source files).
[Native run 39490732759](https://github.com/jmhjr/HomeCircle/actions/runs/39490732759)
passed on x86_64, Core **2026.9.4**, CPython **3.14.6**, official Alpine/musl
Core container: **1,452 backend passes, zero failures, one named optional skip;
110 frontend passes; 337 privacy-checked files with zero flags**. Required
passive-zone, city cancellation/canary and exact-license privacy regressions
passed. The run is native minimum-Core source/package acceptance, not a full
managed service lifecycle, HACS transport or repeated upgrade/recovery run.

The deterministic development ZIP has **113 files**, **614,209 bytes**, SHA-256
`c4530d94be3b2996f8d6c8948db88a51868566047d68558eefde7967f270a861`;
inventory SHA-256 is
`9bdfba997d5437d354673a98c8b78d3875d459499281bca3e20bc629369dcb6b`.
It intentionally still labels itself `0.1.0-beta.20`, while containing different
development bytes. It is neither the published beta 20 ZIP nor a released RC.
Do not upload it over the published release or describe an installation of it as
a normal beta 20 HACS download.

Independent read-only Node audit in `compatibility-disposition/package-audit.json`
verified both downloaded artifact ZIP digests, central/local names, CRCs and
extracted member bytes. All 113 inner package paths/lengths/hashes match the
inventory; 111 match canonical Git blobs and the two generated frontend files
match their build receipt. Receipt source/target/test counts, required regressions,
offline backend flag and successful owned cleanup agree. The receipt artifact is
`12295263448` (5,007 bytes); preview artifact is `12296685231` (593,292 bytes).
No package code was executed by this independent audit.

## New exact-C runtime witnesses

The endpoint runs and scoped managed witnesses were independently verified:

| Core endpoint | CPUs / result | Scope and receipt |
| --- | --- | --- |
| 2026.9.4 | Native amd64 and ARM64; 12 focused cases and four real Core processes each | [Minimum lifecycle](RELEASE-1.0-MINIMUM-LIFECYCLE.md), run 39495726330 |
| 2026.10.2 | Native amd64 and ARM64; 12 focused cases and four real Core processes each | [Current lifecycle](RELEASE-1.0-CURRENT-LIFECYCLE.md), run 39494419279 |
| Container / Core 2026.9.4 | Native amd64 and ARM64; original entrypoint, stop/restart with prepared normal-config cache | [four native consumer entrypoint witnesses](RELEASE-1.0-INCOMPLETE-PILOTS.md#scoped-consumer-followup-four-native-cells-passed), run 39517742934 |
| Container / Core 2026.10.2 | Native amd64 and ARM64; original entrypoint, stop/restart with prepared normal-config cache | [four native consumer entrypoint witnesses](RELEASE-1.0-INCOMPLETE-PILOTS.md#scoped-consumer-followup-four-native-cells-passed), runs 39516737435 and 39517742934 |
| HAOS 18.3 / Core 2026.9.4 / Supervisor 2026.10.2 | Native amd64/KVM; normal managed dependency setup and two service observations | [Minimum managed witness](RELEASE-1.0-MINIMUM-HAOS.md), run 39504506480 |
| HAOS 18.3 / Core and Supervisor 2026.10.2 | Native amd64/KVM; six managed phases | [Prepared restore investigation](RELEASE-1.0-HAOS-RESTORE.md), run 39494958171 |
| HAOS 18.3 / Core 2026.9.4 / Supervisor 2026.10.2 | Native ARM64/HVF; normal requirements and startup/restart | [Scoped minimum ARM managed witness](RELEASE-1.0-INCOMPLETE-PILOTS.md#scoped-arm-managed-followup-both-core-endpoints-passed), minimum attempt 4 |
| HAOS 18.3 / Core and Supervisor 2026.10.2 | Native ARM64/HVF; normal requirements and startup/restart | [Scoped current ARM managed witness](RELEASE-1.0-INCOMPLETE-PILOTS.md#scoped-arm-managed-followup-both-core-endpoints-passed), current attempt 7 |

The four QA-container cells add 48 executions of the same 12 focused cases,
zero failures/skips and 16 fresh Core processes, with exact loaded/served bytes,
saved settings/source identity, unload/reload and removal verified. They do not
claim the standard consumer Container entrypoint. The HAOS investigation adds
actual managed startup/restart and operational partial restore for C with
prepared dependencies. Manual newest-guard repair passed; automatic guard
anti-rollback failed and both ordinary/prepared restore safety remain false.
The minimum-Core amd64 HAOS witness separately passed normal managed dependency
installation, startup and a real restart with exact bytes/settings/identities;
its restart used a closed external NIC without dependency preloading.
The [eight consumer and seven local ARM negatives](RELEASE-1.0-INCOMPLETE-PILOTS.md)
remain preserved. The subsequent [four native consumer entrypoint witnesses](RELEASE-1.0-INCOMPLETE-PILOTS.md#scoped-consumer-followup-four-native-cells-passed) passed exact-C startup/restart,
loaded/served bytes, settings/source/resource continuity, legitimate unload/setup,
offline acceptance and cleanup at both Core endpoints on both CPUs. They used
prepared normal-config dependencies; fresh online consumer resolution is outside
that scope. The subsequent [two ARM managed witnesses](RELEASE-1.0-INCOMPLETE-PILOTS.md#scoped-arm-managed-followup-both-core-endpoints-passed) passed normal dependency setup, 113-file loaded/served bytes and stable saved
settings/source/resource/dashboard identities through real Core restarts. Both
ran on native HVF/HAOS 18.3/Supervisor 2026.10.2/Python 3.14.6, at Core 2026.9.4
and 2026.10.2. Missing Anisette/Life360/Unicorn before setup and the stable 24-
package metadata closure afterward were observed without preload or skip-pip.
System-site origin does not establish immutable-image provenance or individual
network transactions. All five graceful cleanup gates passed in each. Bootstrap
read-only host-nonzero attempts (seven current, eleven minimum) remain distinct
from zero-failure continuations (368 and 1,404 calls).
No provider account or native Apple worker was exercised by these new runs.

## What can be carried forward

Historical baseline **F** is the unreleased 112-file parent ZIP
`f0477a91e78181fe1f8d80ada176a1739e10a7502abe7ee6ee2240571280d1f5`.
Published beta 20 **B** is the separate 112-file ZIP
`fc0b365d9688459504f874af5c38393e24145d657f15f1def8ada9184f363285`.
B differs from F by three version substitutions. The current preparation
artifact **C** is the 113-file `c453…` ZIP above.

Relative to B, C changes executable product behavior only in `city_lookup.py`,
`normalize.py` and the picture-settings frontend/build output. Notices and
provenance are corrected separately; the privacy checker and tests also change.
The provider/authentication/cryptographic/native worker implementations,
manifest requirements and dependency pins are unchanged. Existing actual native
execution, limits, dependency-path isolation and reaping results remain evidence
for those unchanged inputs on their recorded targets. They are not new C test
runs, current dependency-resolution proof, or approval of owner-account behavior.

The changed `close()` path now has current-candidate integration unload/reload
and focused cancellation/error acceptance in all four QA-container cells. The
passive-zone selection cases passed there, and the exact generated bundle was
served in those processes and the managed HAOS investigation. The scoped
[Safari check](PICTURE-BROWSER-VALIDATION.md) covers picture decoding and upload.
These results do not mean the new ZIP has run through every historical
service/restore procedure or every consumer launcher.

## Eight proposed cells

Core **2026.9.4** is the proposed minimum and **2026.10.2** the recorded current
qualification endpoint. This is a dated proposal, not a claim about future Core
versions. A QA container using an official Core image is identified below as QA;
that does not automatically qualify all end-user Container launcher/network/
volume combinations or an HAOS-managed installation.

| Proposed installation / CPU / Core | Existing target evidence | Current C disposition / missing runtime witness |
| --- | --- | --- |
| Container / amd64 / 2026.9.4 | F: native worker/lifecycle, full 1,443-test suite, both upgrade baselines and full synthetic recovery in [39433931788](https://github.com/jmhjr/HomeCircle/actions/runs/39433931788). B: native 1,443-test package run [39460044306](https://github.com/jmhjr/HomeCircle/actions/runs/39460044306). | C: native full suite/package passed; [minimum lifecycle](RELEASE-1.0-MINIMUM-LIFECYCLE.md) now passed exact-C create/restart/unload/remove, 12 focused cases and dependency setup. The [four native consumer entrypoint witnesses](RELEASE-1.0-INCOMPLETE-PILOTS.md#scoped-consumer-followup-four-native-cells-passed) include this minimum-amd64 cell with prepared dependencies; fresh online consumer resolution remains outside that scope. |
| Container / amd64 / 2026.10.2 | F: native process-level upgrades/rollback and full recovery in [39426549335](https://github.com/jmhjr/HomeCircle/actions/runs/39426549335); full official-image suite/native checks also passed in the separately identified emulated target. | C: [current lifecycle](RELEASE-1.0-CURRENT-LIFECYCLE.md) passed exact-C dependency setup, 12 focused cases and four actual Core processes. The [four native consumer entrypoint witnesses](RELEASE-1.0-INCOMPLETE-PILOTS.md#scoped-consumer-followup-four-native-cells-passed) include this current-amd64 cell after eight preserved negative attempts; exact startup/stop/restart, bytes and identity continuity passed with prepared dependencies. Fresh online resolution remains outside that witness; B's Ubuntu/glibc result does not broaden this musl scope. |
| Container / ARM64 / 2026.9.4 | F: official ARM64 QA container, 24-dependency closure, native worker/lifecycle, 1,443 tests plus one skip, two upgrades and full synthetic recovery. [Detailed scope](https://github.com/jmhjr/HomeCircle/blob/v0.1.0-beta.20/docs/LINUX-HAOS-VALIDATION.md#arm64-core-202694-container) | C: [minimum lifecycle](RELEASE-1.0-MINIMUM-LIFECYCLE.md) passed exact-C dependency setup, loaded/served bytes, 12 focused cases and four Core processes. The [four native consumer entrypoint witnesses](RELEASE-1.0-INCOMPLETE-PILOTS.md#scoped-consumer-followup-four-native-cells-passed) also qualify this cell with prepared dependencies. Native worker evidence is reused only for unchanged historical inputs; neither new run executed that worker. |
| Container / ARM64 / 2026.10.2 | F: official ARM64 QA container, native/lifecycle, full suite, process-level upgrades/recovery and a separately scoped public anonymous runtime check. [Detailed results](https://github.com/jmhjr/HomeCircle/blob/v0.1.0-beta.20/docs/LINUX-HAOS-VALIDATION.md#regression-upgrade-and-recovery-results) | C: [current lifecycle](RELEASE-1.0-CURRENT-LIFECYCLE.md) passed exact-C dependency setup, loaded/served bytes, 12 focused cases and four Core processes. The [four native consumer entrypoint witnesses](RELEASE-1.0-INCOMPLETE-PILOTS.md#scoped-consumer-followup-four-native-cells-passed) separately passed this cell with prepared dependencies. Native worker execution was not repeated. |
| HAOS / amd64 / 2026.9.4 | C: native KVM/HAOS 18.3/Supervisor 2026.10.2, normal managed requirement setup and exact Core 2026.9.4 image/runtime. | [Run 39504506480](RELEASE-1.0-MINIMUM-HAOS.md) passed exact-C enabled startup/restart, 113 installed files and exact loaded/served hashes, nonempty settings and persisted identities; restart external NIC closed and cleanup passed. Direct verified ZIP installation, not HACS, historical migration, native-worker repetition, removal or backup/restore. |
| HAOS / amd64 / 2026.10.2 | F: native KVM HAOS 18.3 managed setup/restart and prepared disabled-entry partial backup/Recorder restore. B: eight genuine HACS phases in [39461573392](https://github.com/jmhjr/HomeCircle/actions/runs/39461573392), preserving synthetic selections/options/identities and exact served bundle. | C: [six-phase managed investigation](RELEASE-1.0-HAOS-RESTORE.md) passed actual startup/restart, exact loaded/served bytes, settings/identity/history restoration and separate manual guard repair with prepared dependencies. Automatic guard protection failed. Default dependency reinstallation, real C/RC HACS delivery and full restore remain separate. Changed city/passive cases passed in the focused QA-container runs. |
| HAOS / ARM64 / 2026.9.4 | C: scoped native HVF/HAOS 18.3/Supervisor 2026.10.2 managed witness. | [Minimum attempt 4](RELEASE-1.0-INCOMPLETE-PILOTS.md#scoped-arm-managed-followup-both-core-endpoints-passed) passed normal requirements, exact C453 startup/restart, loaded/served bytes, nonempty settings and identity continuity. One supported stock 2026.10.2 → 2026.9.4 selection, actual absent-container start and seven completed actions are retained. The earlier minimum negative remains preserved. No provider/native-worker, HACS, restore or final-RC claim. |
| HAOS / ARM64 / 2026.10.2 | F: managed normal install/restart/native evidence for its 112-file input; C: scoped native HVF/HAOS 18.3 current witness. | [Current attempt 7](RELEASE-1.0-INCOMPLETE-PILOTS.md#scoped-arm-managed-followup-both-core-endpoints-passed) passed normal requirements, exact C453 startup/restart, loaded/served bytes, explicit selections and nonempty settings/identities across five completed actions. All six prior current negatives remain preserved. No B/C native ARM genuine-HACS, new provider/native-worker or restore acceptance is asserted. |

Additional native Ubuntu 24.04/amd64 glibc 2.39/Core 2026.10.2 acceptance for B
passed [39474571811](https://github.com/jmhjr/HomeCircle/actions/runs/39474571811):
1,443 backend tests, native/lifecycle and real create/restart. It qualifies that
specific runtime; it does not fill a C cell or every glibc distribution.
Earlier emulated amd64 timeout failures remain failed/unqualified in their own
scope and are not erased by later native results.

At the October 21, 01:02 UTC cutoff, restore-procedure followup 39524048553
passed normal setup/restart, quarantine and mutate after 95 native contracts and
16 published-input checks. Host-held newest-guard retention then failed with no
underlying cause established; the full restore gate remains false. Phase-level
dependency/source/served acceptance does not imply completed restore safety.

## Next compatibility work

The former minimum/current exact-C QA-container lifecycle gap is now closed on
both CPUs within the scripted scope above. Repeating the full suite on every
wrapper is unnecessary. The proposed matrix is still not fully accepted:

- Preserve the four prepared-cache original-entrypoint passes. Qualify fresh
  online installation through the unmodified Core requirements route, followed
  by measured isolated acceptance/restart; new file-only planning is not a pass.
- Preserve the completed minimum-Core amd64 and both ARM managed ordinary-
  requirements startup/restart witnesses. Close only the remaining advertised
  final-RC, provider/native, delivery and removal scope before release.
- Identify a final RC for genuine HACS delivery and freshly inspected
  installed-state migration. The unreleased same-version ZIP cannot supply
  ordinary release-selection acceptance.
- Preserve the guard-rollback finding and use the tested prepared restoration
  ordering; broader backup variants remain unqualified.

## Remaining release qualification

Before an RC/stable claim, identify the final versioned source/package and close
the chosen advertised cells with exact-artifact service install/start/restart/
unload evidence. Reuse backend coverage across equivalent wrapper environments
instead of running 1,452 tests eight times. Recheck a changed native or dependency
path on each affected CPU/libc; do not re-execute Apple/account work just because
a notice or version label changed. A later resolved dependency artifact can
require new import/native qualification even with the same declared version.

Real RC HACS install/upgrade/rollback, current installed-state migration,
ordinary enabled/advertised backup restore, owner-provider acceptance,
specialist/provenance/service decisions, sustained field behavior, native picker
completion, mobile and physical-display acceptance remain separate gates.
This report records completed disposable runs; it publishes no RC or stable release and makes no production change.
