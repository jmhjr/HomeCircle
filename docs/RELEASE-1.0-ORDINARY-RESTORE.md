# Ordinary enabled restore — scoped validation passed

Recorded October 21, 2026. [Native R5 run 39721983991](https://github.com/jmhjr/HomeCircle/actions/runs/39721983991)
passed an ordinary, enabled, synthetic same-host Home Assistant partial restore.
All four phases passed with the unchanged 113-file product and manifest, normal
managed requirements and default Supervisor conditions. On the first automatic
restored startup and the following restart, the real account-bound guard required
review and refused the attempt before its body ran. No manual guard repair or
post-restore acknowledgment was used.

The [machine-readable record](RELEASE-1.0-ORDINARY-RESTORE.json) binds the five raw
receipts, GitHub metadata and independent audits. [Retained public evidence](https://github.com/jmhjr/HomeCircle/blob/8f28d5da33b7094355e84d5c8a23ee78463cecf3/native-ordinary-rollback-evidence/INDEX.md),
including a [portable offline replay](https://github.com/jmhjr/HomeCircle/blob/8f28d5da33b7094355e84d5c8a23ee78463cecf3/native-ordinary-rollback-evidence/REPLAY.md), preserves the exact packet.
The four earlier failed trials remain below with their original limitations.

## Retained trials and fixture correction

| Trial | Native result | Accepted phases / backup requests | Cleanup |
|---|---|---|---|
| [R1: 39714666021](https://github.com/jmhjr/HomeCircle/actions/runs/39714666021), QA `6045b759` | `ordinary_phase_receipt_refused`; guest cause unidentified in its narrow record | 0 / 0 | Passed |
| [R2: 39716881615](https://github.com/jmhjr/HomeCircle/actions/runs/39716881615), QA `fe8cac9a` | Baseline observer `qa_enabled_runtime_settings` at `runtime_details` line 532 | 0 / 0 | Passed |
| [R3: 39717938959](https://github.com/jmhjr/HomeCircle/actions/runs/39717938959), QA `0abfc5f3` | Two pre-restore phases and backup/restore jobs passed; no automatic restored receipt before deadline | 2 / 2 (one create, one restore) | Passed |
| [R4: 39720944024](https://github.com/jmhjr/HomeCircle/actions/runs/39720944024), QA `cf0ba6c8` | Two pre-restore phases and backup/restore jobs passed; fresh automatic observer failed `qa_startup_boundary_shape` after verified grant | 2 / 2 (one create, one restore) | Passed |

R1 and R2 provide no backup or restore acceptance. R2 reached its runtime comparison
after the unchanged package, ordinary dependency, guard and raw-storage checks;
its failure remains recorded as a fixture investigation.

A separate controlled replay executed the exact canonical `item_config` and
`tracker_unique_id` function bodies with an explicit synthetic entity registry.
A forced reversed identifier creation order survives in the seed's `items` list,
while canonical JSON sorts the nested account dictionary. Product projection
rebuilds the native item list in that dictionary order. The old strict runtime
comparison then fails with only `items` order changed: selected IDs, member
settings, picture and saved input bytes remain unchanged.

Sorting synthetic accessory identifiers before constructing metadata, joins and
settings makes the strict comparison pass and the projection idempotent. Four
controls still reject an altered display name, picture, item selection or member.
R3 applies that fixture correction and retains strict runtime equality and raw
fingerprints; product bytes are unchanged. Replay receipt SHA256:
`a92d371b83444b6c44b991dc91be53d0eb4b91508db7f72088900b4ae4ab7a64`.
This establishes a sufficient fixture defect. The exact random ordering in the
cleaned-up R2 guest is unavailable and is not asserted.

## R3 partial result and separate handshake correction

R3's actual artifact is
`20289b54ec5a2db7a483dbaa78c868d9dafc5abf438335a53d5598bea761059b`.
Its accepted baseline and mutation counters were two and three, with no recovery
dispatch. The actual archive excluded the cache witness and preserved the exact
package/manifest, saved data and database. Backup and restore jobs finished
without reported errors. Default Supervisor conditions, acknowledged network
closure and zero jobs/options mutations passed.

The run then failed with `ordinary_automatic_restored_receipt_deadline` after
writing the closed-boot grant. There is no automatic restored-startup or restart
receipt and no verification of restored guard admission. Owned cleanup passed.
R3 is retained partial evidence and does not itself qualify ordinary restore.

Independent source-schedule replays reproduced an input-publication interleaving
and a pregrant diagnostic blind spot. An in-place rewrite can expose incomplete
JSON; a stale observer snapshot can also miss newly published proof. These are
confirmed fixture defects, while the actual failure cause in the removed native
guest remains undetermined. R4 publishes inputs with an owned same-parent atomic
replacement, reloads and binds input identity after grant consumption, and writes
a bounded fixed-field failure receipt for pregrant errors. Product bytes,
deadlines and success gates are unchanged.

The independent R4 replay passed three schedules: a reader sees complete old JSON
during temporary publication and complete new JSON after replacement; post-grant
reload receives new proof and refuses changed identity; malformed pregrant input
writes a failure barrier without a passing barrier. R4 preparation passed 33 root
fixture contracts and eight frozen consumer contracts, bound to 27 inputs including
the workflow. These preparation passes do not supply a native restore result.

## R4 failed observer and narrow R5 correction

R4 retained two accepted pre-restore phases, successful backup/restore jobs,
actual cache exclusion and default Supervisor conditions. Its artifact is
`cca1fdb7d0786b59a8f0c7c1a87389fb6f35989da8133bbe61c9ec696c819a2f`.
A fresh automatic restored failure receipt identified `qa_startup_boundary_shape`
in `runtime_details`, after the closed-boot grant was verified. Owned cleanup
passed. There is no accepted restored guard-admission or restart result.

Verified source shows that the normal phase path reads the guard before checking
runtime startup hooks, while the automatic path checked runtime first. The guard
module is lazy-loaded. Independent schedules reproduce the automatic path
missing its guard hook, and guard-first ordering passes the same six-target gate.
The removed native loaded-kind snapshot is unavailable; the exact deleted set is
not presented as recovered evidence.

A separate discriminator uses the actual import finder and exact canonical guard
source. Importing that guard installs the real before-dispatch wrapper; the
unchanged strict startup-shape check refuses the missing-hook control and passes
after import. These are source-level controls, not native restore receipts.
R5 runs the existing real guard receipt before `runtime_details`, retaining its
actual status/attempt refusal and every startup gate. Only observer order, its
regression contract and README change; product bytes remain unchanged.

## R5 accepted result and exact identity

[R5 run 39721983991](https://github.com/jmhjr/HomeCircle/actions/runs/39721983991)
completed successfully on amd64/KVM HAOS 18.3, Core 2026.10.2 and Supervisor
2026.10.3. QA head is `4957b3f44e84837e01af731286c0728a4127aea3`; workflow
SHA256 is `277104fa67c7ff6e321cb0e7de5182dc13a89c9be4822d1de691e963694926e7`.
The downloaded artifact is 10,038 bytes, ID `12401877265`, SHA256
`d87250aef1cb73fce9d5de778f005ec9e678732044b11c96c0890442469c956a`.

| Actual phase | Guard count | Review required | Real attempt refused before body | Normal requirement installs |
|---|---:|---|---|---:|
| Baseline enabled | 2 | No | Not probed | 2 |
| Mutated enabled | 3 | No | Not probed | 0 |
| Automatic restored enabled | 2 | Yes | Yes | 2 |
| Restart enabled | 2 | Yes | Yes | 0 |

The actual archive excluded the cache witness. It was absent on both restored
startup and restart. Guard identity matched the saved SDK account in every
phase. The restored older count therefore did not silently grant recovery:
review remained required, and the real guarded attempt was refused before its
body. Guard exports, manual imports and owner acknowledgments after restore
were all zero. All recovery command, before-dispatch and recovery transport
seams remained zero. Ordinary saved-session transport attempts were separately
intercepted and counted; no live provider proof was sent.

Both Supervisor jobs completed without errors under default conditions, with
zero jobs/options mutations. All 113 product members and the manifest remained
unchanged. Normal requirements used the unmodified installer, with a verified
24-distribution closure per phase and install counts two, zero, two, zero; no
prepared dependency preload was used. Four explicit tracker joins, saved
selection/settings/place, encrypted storage, synthetic photo and exact served
frontend bytes passed through restore and restart. Four owned offline storage
contexts passed, including negative storage checks.

Recorder retained the exact six baseline rows, removed six post-backup mutation
rows after restore, and preserved six new post-restore rows across restart.
Database integrity, backup hooks and recording checks passed. Host elapsed time
was 461.542 seconds. The owned VM stopped and private workspace was removed;
cleanup reported no failure.

The exact 113-file runtime ZIP is
`98a754ff2025761c2eb63d6422c9b17b76e2bdef2965c96fe353ab6c2c21fb20`
(620,228 bytes), with inventory
`370a0036f03bd2b7185afc7a9ddcf7d6545e41cfb6394f00fc699a2973db33aa`.
Runtime source `012a7e88d13970b2683b27d0824dac246c858179` and the native package
suite's tests-only source `57b0aaa5c2c4b1a022e547347640173412e840f5` produce the
same package. The [rollback record](RELEASE-1.0-ROLLBACK-PROTECTION.md) contains
its separate 1,728 backend and 122 frontend results.

Preparation passed 34 root fixture contracts and eight frozen consumer
contracts, bound to 27 inputs including the workflow. Frozen consumer SHA256 is
`71e10bc211f6ed954b956e3165048865ddaace6d7e9fe00d09ab329093494a1f`.
The independent consumer accepted all five actual receipts, metadata, frozen
inputs and source/package bindings without importing the fixture or repeating
the native trial. Root and peer outputs matched byte-for-byte at SHA256
`a0ba3a1340c72e9a7add31bf472a0cf63caadd48e8620e53eafa96369cd32209`;
the detailed peer audit is
`f7e8857f449ba36a8a4ca08fe5915e9891e512f9f4a51034cf2851c68cc10b1c`.
Replay from the 20 committed public evidence files passed as well.

## Scope and remaining gates

The accepted scope is a synthetic same-host Home Assistant partial restore with
the unchanged product and manifest, ordinary requirement installation and default
Supervisor conditions. External transport instrumentation keeps provider calls
inside this account-free trial; it does not prove live authentication or renewal.

The fixture uses tracker-only person-kind members, so complete Home Assistant
Person associations remain separate. Recorder history continuity does not qualify
HomeCircle activity history. Fresh-machine, full-system/add-on, encrypted/cloud
restore and HACS delivery remain outside this result. A full VM or configuration
snapshot that restores both an older ledger and its matching cache witness needs
an independent external monotonic anchor for detection. Pre-fix archives can also
restore old integration code; install the patched candidate before recovery.

The working owner instance remains on source
`91ae59106a661143b770d7a3564d363c7c11a7dd` and is unchanged. These trials use no
real credential or recovery proof, alter no family-refresh setting, and reopen
no remote access. Stable release approval remains open.
