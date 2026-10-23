# First-release scope and qualification

The maintainer accepted the HAOS-first support target on October 22, 2026, based on canonical source `c31c220563ae55d469bbf530fa77dd2f80583910`. The installation scope is accepted; final-candidate qualification is still pending and 1.0 has not shipped. The reviewed baseline identifies itself as 0.1.0-beta.20; the unpublished qualification candidate is being prepared as 1.0.0-rc.1. Final version, artifact, release-candidate checks and approval remain open.

## Accepted first-release target

| Area | First-release target | Qualification boundary |
| --- | --- | --- |
| Installation | Official Home Assistant OS on amd64 and ARM64, through HACS using the named HomeCircle release ZIP | Final RC and genuine HACS delivery checks remain pending. HAOS 18.3 is the managed reference environment. |
| Home Assistant Core | Minimum 2026.9.4; current qualification target 2026.10.2 | Fold the focused minimum-Core startup/activity/restart check into the one final RC pass. Reuse existing architecture evidence; do not repeat a broad two-CPU matrix. Future Core versions are not automatically qualified. |
| Dashboard | Home Assistant storage-mode dashboards and resources, with the included HomeCircle card and visual setup | YAML-managed resource/dashboard collections are preserved but outside the first-release UI-only support path. A physical display or mobile browser is accepted separately from a desktop check. |
| Members and sources | Standard HA People and explicitly selected trackers, including pets and supporting sensors; existing tracker-only members remain compatible | Names alone never establish an association. Configured Person links, the Person's active source and HomeCircle's selected sources remain distinct. |
| Direct connections | Keep both optional Apple Find My and Life360 | The maintainer requested the [no-contact source-only distribution approach](RELEASE-1.0-NO-OUTREACH-DECISION.md); factual terms/basis and residual-risk scope decisions, affected control results are source-bound, and bounded owner acceptance remains pending. No provider permission or legal clearance is claimed. The maintainer accepted the completed Claude AI technical review with its documented limits; no qualified-human or independent producer-format assurance is claimed. |
| Find My scope | Explicitly discovered and selected items, with the tested AirTag path as the reference | AirPods/Other are available type labels, not proof that every Apple device or key format is supported. No Find My People service or phone-equivalence promise is made. |
| Core display | Home/Away/Driving, named places and additional homes, source report age/accuracy, pictures, bounded local activity and implemented optional map layers | No real-time GPS, guaranteed refresh, trip reconstruction, routing/ETA or background phone-reporting guarantee. |
| Upgrade baseline | Unmodified published beta 20 to the final named RC/release, after a backup | The private installation-copy rehearsal and older transport tests are useful evidence, not final HACS installed-state acceptance. Earlier betas and locally patched/development packages need a separate migration disposition. |
| Backup restore | Scoped ordinary same-host HAOS Home Assistant partial restore, including configuration and Recorder database, using fixed code | Accepted synthetic trials used uncompressed, unprotected partial archives with normal requirements/default Supervisor conditions. Restored guard continuity requires explicit account-specific review. |

Home Assistant Container has compatibility evidence, including earlier CPU/Core lifecycle cells. Keep it **experimental/not yet qualified for the first-release consumer support path** for this release; earlier compatibility evidence remains available for future support qualification. This does not erase that evidence or declare Container permanently unsupported. Supervised/Core-only installations, Windows/macOS runtime hosts and untested architectures are outside this first-release support target.

Encrypted/compressed variants, cloud restore, full-system/add-on restore, fresh-machine migration and complete filesystem/VM snapshots are not qualified by the scoped ordinary restore result. Do not disable backup encryption simply to imitate a test. Use Home Assistant's normal backup protection and treat a different restore variant as a separate recovery case. A full snapshot can restore both guard ledger and witness; local continuity is not an external monotonic counter.

## What the present evidence establishes

The exact f181 candidate passed the current-Core native container/package suite: 1,732 backend cases, 54 required functions, 122 frontend cases and privacy checks over 381 canonical source files. The harness passed 42 contracts; the corrected independent consumer passed 20 and retained its initial schema refusal. That result does not qualify a managed HAOS lifecycle, HACS delivery, live provider authentication or a release candidate.

Separate records retain the fixed candidate's ordinary HAOS Person/activity/Recorder restore and the private ARM64 installation-copy upgrade. The earlier minimum-Core complete suite belongs to old012a/98a bytes. Reuse these scopes honestly and check the final artifact's changes; none is a blanket approval of a later package.

See the [seven-item execution tracker](RELEASE-1.0-FIRST-RELEASE-TRACKER.md), [package record](RELEASE-1.0-FIXED-PACKAGE-VALIDATION.md), [ordinary restore record](RELEASE-1.0-FIXED-ORDINARY-RESTORE.md) and [private upgrade record](RELEASE-1.0-PRIVATE-UPGRADE.md).

The unused local macOS decryptor/CLI is [excluded from the new candidate](RELEASE-1.0-LOCAL-MACOS-EXCLUSION.md); supported HAOS CloudKit discovery and report paths remain unchanged.
