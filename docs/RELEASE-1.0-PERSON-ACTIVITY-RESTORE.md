# Person and activity ordinary restore — scoped validation passed

Recorded October 22, 2026. [Native run 39777059627](https://github.com/jmhjr/HomeCircle/actions/runs/39777059627)
passed all four enabled phases of the isolated ordinary partial restore. A real
editable HA Person, its saved tracker associations and genuine product-generated
HomeCircle activity survived restore and restart. No product fix was required.
The [machine-readable record](RELEASE-1.0-PERSON-ACTIVITY-RESTORE.json) binds the
five actual receipts, GitHub metadata, source/package identity and observations.

The prior [ordinary partial restore](RELEASE-1.0-ORDINARY-RESTORE.md),
[run 39721983991](https://github.com/jmhjr/HomeCircle/actions/runs/39721983991),
remains passed. This result adds the genuine HA Person and HomeCircle activity
cases that its tracker-only person-kind members and Recorder rows did not cover.
Earlier failed trials retain their original dispositions in that record.

## Exact accepted identity

The native target was amd64/KVM HAOS 18.3, Core 2026.10.2, Supervisor 2026.10.3.
QA head is `4b464723fe63bafc62f92e17e538e566278ee1c0`; workflow SHA256 is
`299362dea2e4f5b7d474ebbc691780a4685ddc921b41da7aa26a1b412dc3eebd`.
Artifact ID `12426130015` is 12,091 bytes, SHA256
`f7d401662e78a7fd39881ec91c5d181a7090a8a09244bcd4fed293f2998b86da`.

Source with documentation entering this milestone was
`08fd5cc65fa93318b211106e013b5b92f49d7f6a`; product runtime source remains
`012a7e88d13970b2683b27d0824dac246c858179`. All 113 product files and the manifest
were unchanged. The ZIP is
`98a754ff2025761c2eb63d6422c9b17b76e2bdef2965c96fe353ab6c2c21fb20`
(620,228 bytes), inventory SHA256
`370a0036f03bd2b7185afc7a9ddcf7d6545e41cfb6394f00fc699a2973db33aa`.

## Person associations and source selection

Every phase verified one actual editable Person storage-collection entity and
its real entity-registry identity. It had two configured HA tracker links while
HomeCircle explicitly selected one. The HA active source was the other linked
tracker: HomeCircle still used only the selected tracker for location evidence,
excluded the nonselected tracker from its state cache, and masked that active
source as `other` in the nonadministrator projection. No Person state was written
directly and no association was inferred from names.

The saved association digest was
`d3e9912eb20a22e45214e4db67af1c91c8305573004e711e5e4be11bc3864215`.
A post-backup mutation changed the linked tracker and digest to
`8f390aaee6365f8bff900c6626170d2391c2c64beeb5776e8134d28adeb7c067`.
Restore and restart returned the original digest and removed the mutation-only
tracker. Actual archive inspection bound the Person v2 store item and its registry
joins, rather than accepting synthetic `person.*` state rows as evidence.

## Product-generated activity and durable cohorts

Only synthetic GPS tracker states were driven. Real Person state updates,
HomeCircle normalization/listeners and `ActivityLog.observe` generated activity;
there were zero direct activity appends or manual activity-store writes.

| Cohort | Actual events | Presence transitions | Result |
|---|---:|---:|---|
| B: durable before backup | 25 | 3 | Retained after restore and restart |
| M: distinct after backup | 28 | 3 | Removed by restoring the older backup |
| R: new after restore | 25 | 3 | Retained across the later restart |

Cohort SHA256 values are:

- B: `aedfabac30abc7535d8e55fd13438625d2b1bb7801da12fa81396c5d5a634aa0`
- M: `70dcbabcb7204699e12120e78f53ae3cb1f79b1a138fa5e0da3325a04f7041b0`
- R: `078d5742425ca19f62d445ff334eff28fa8bdb8a428af1bc1b3ef8dbff25ab76`

The actual `.storage/homecircle.activity.<entry_id>` payload and complete original
configuration fingerprint were bound in the archive. The deliberately changed
post-backup configuration had its own fingerprint/history; restore returned the
original fingerprint and exact retained B prefix, with no M event. R survived
restart with its exact digest. Each new runtime's allowed suffix begins with
`started`, presence, source and freshness observations; later records must stay
allowlisted. The public API projection matched the raw store's source-label and
reversed-order contract. No journey was reconstructed across a stopped gap.

Person collection changes used ordinary ten-second Store persistence and activity
used its ordinary five-second delay. The helper waited for actual on-disk state
to match the real collection/log before accepting it; no fixture-only flush was
substituted. **Native arrival-gap restoration and deliberately pending writes at
shutdown remain unqualified.** Source code marks loaded arrival continuity as
uncertain and registers delayed Store final writes during graceful shutdown;
this run did not specifically test those two behaviors.

## Retained ordinary restore and recovery checks

| Phase | Guard count | Review required | Attempt refused before body | Normal requirement installs |
|---|---:|---|---|---:|
| Baseline enabled | 2 | No | Not probed | 2 |
| Mutated enabled | 3 | No | Not probed | 0 |
| Automatic restored enabled | 2 | Yes | Yes | 2 |
| Restart enabled | 2 | Yes | Yes | 0 |

The actual archive excluded the recovery witness; it was absent after restore
and restart. The real guard identity matched the saved SDK account and refused
both restored attempts before their bodies. No guard export/import/repair,
post-restore acknowledgment or recovery proof was used. All measured recovery
command, before-dispatch and recovery-transport seams remained zero.

Normal managed requirements verified a 24-distribution closure per phase, with
no prepared dependency preload. Both Supervisor jobs completed without errors
under default effective/persisted conditions and zero jobs/options mutations.
Saved provider sessions, selected identities, settings/place/picture and exact
served frontend checks passed. Recorder independently restored six baseline rows,
removed six mutation rows and preserved six new restored rows across restart.
The archive was 2,969,600 bytes. Host elapsed time was 496.499 seconds; the owned
VM stopped, private workspace was removed and cleanup reported no failure.

## Independent acceptance and remaining scope

The frozen consumer accepted the actual five-receipt artifact, original GitHub
metadata, all 30 frozen inputs and source/package bindings without importing the
fixture or repeating the native trial. The producer's 45 contracts and the
independent consumer's 17 contracts passed without skips. Root and peer consumer
output agreed at SHA256
`02fd0b81482dc729824b298f4f82be31607e02b3a2fc6f3a935a41db6a509f86`.
Detailed peer audit SHA256: `1c85c5615c48c55ceb715bcf32cdd46443f290434d5e746a236270aa98d6c7f6`.
The [retained public evidence](https://github.com/jmhjr/HomeCircle/blob/07d50ada0f398c88dee322e5fd1f9c4a7ef9a86e/native-person-activity-evidence/INDEX.md), including its
[portable replay](https://github.com/jmhjr/HomeCircle/blob/07d50ada0f398c88dee322e5fd1f9c4a7ef9a86e/native-person-activity-evidence/REPLAY.md), preserves 13 evidence files.
Re-export and replay of the 30 native inputs plus those 13 actual committed
Git blobs passed with the same byte-identical review output.

Preflight review found that the initial fixture reused Recorder tracker IDs
before registry creation, which would have caused HA to assign collision suffixes.
Separate Person GPS IDs corrected that fixture before R1 was frozen; Recorder
proof remained independent. The first native run passed. Product bytes and
requirements were unchanged.

Acceptance is limited to this synthetic same-host ordinary partial restore and
its measured Person/activity cases. Arrival gaps and pending-on-shutdown writes
remain unqualified as stated above. Full-system/add-on, encrypted/cloud and
fresh-machine restores, live provider authentication/renewal, external
cryptographic/provenance assurance, remaining compatibility, field/display,
installed-state upgrade, HACS and stable release remain separate gates. A full
VM/configuration snapshot restoring both an older ledger and matching witness
still needs an external monotonic anchor for rollback detection. Pre-fix archives
can restore old code; fixed code must be loaded before guarded recovery.

No production configuration or owner credentials were used. The working owner
instance remains on source `91ae59106a661143b770d7a3564d363c7c11a7dd` and was not
changed by this milestone.
