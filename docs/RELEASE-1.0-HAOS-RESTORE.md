# Exact development preview: managed HAOS restore investigation

Verified October 20, 2026. [Run 39494958171](https://github.com/jmhjr/HomeCircle/actions/runs/39494958171)
completed all six phases on native amd64/KVM, **HAOS 18.3**, **Core and Supervisor
2026.10.2**. Prepared operational restore and subsequent manual newest-guard
repair passed. **Automatic guard anti-rollback failed; ordinary and prepared
enabled-restore safety remain unaccepted.** The successful workflow means the
bounded diagnostic completed and retained that finding. Its actual controller
returned exit 1 with `confirmed_safety_issue`.

## Identified input

Product source is `9bf03eb45d2cf43274074534e9dfe2de841f4011`; validation controls
are `37308aa1edb5b8e6f971751f01f82398120c3c26`. The development ZIP contains
113 files and has SHA-256
`c4530d94be3b2996f8d6c8948db88a51868566047d68558eefde7967f270a861`.
Its inventory SHA-256 is
`9bdfba997d5437d354673a98c8b78d3875d459499281bca3e20bc629369dcb6b`.
All 111 direct runtime source members match the canonical Git source; two
generated frontend members match the prior native build. The same beta 20
version label is retained for this **unreleased preview**. It is not the
published beta 20 ZIP, a HACS download or an RC.

## Observed behavior

The six phases were initialization, prebackup recording, postbackup mutation,
actual Supervisor partial restore, manual safeguard repair and restart.
They used an enabled synthetic entry, explicitly selected People/trackers,
nonempty settings, a dashboard, real Recorder and exact package/frontend bytes.
Supervisor's actual partial-backup and partial-restore jobs completed with no
reported job errors. Core automatically loaded the enabled entry after restore.
Selections, entry/entity/dashboard/resource identities, settings and exact
served bundle returned to their saved state. Ten prebackup history rows
returned; ten postbackup marker rows disappeared; ten new postrestore rows
persisted through repair and restart.

The local synthetic unresolved count was **2** at backup, then **3** in the
newest safeguard. Automatic restore brought back the exact older **2** before
manual intervention and it stayed unchanged after the entry loaded. Manually
returning the separately retained newest safeguard restored **3**, including its
blocked status, which survived restart. These are local fixture observations,
not Apple's retry allowance or proof of any live recovery submission.

The dependency fixture placed the actual 24-distribution closure in Core's
normal config-local dependency path before backup, with skip-pip false. All
1,002 non-bytecode files / 71,689,643 bytes matched inventory SHA-256
`b20c91d32d02a2436003779a1ef0369f4f7da45e0975044469acc365e336d85f`.
The backup actually contained those dependencies, the package, database and old
guard. The restored Life360 module was observed loaded from that path; five
other direct-package origins were import-spec observations, not execution of
their provider/native paths. Default online dependency reinstallation was not
tested.

Before restore the owned VM's sole external network link was closed after a
positive connection control. Four negative controls confirmed denial while
guest-agent control remained available. Request/proof attempt counts were
**not measured**. No owner credentials or provider account was configured.
The newest guard was outside the replaced config on the same guest disk;
this does not establish host-external or full-system-backup preservation.

## Disposition and retained evidence

Use the established [prepared disabled-entry procedure](FINDMY-SETUP.md#prepared-supervisor-backups),
including separate newest-guard preservation before restoration and verified
repair before re-enabling HomeCircle. This experiment demonstrates a limitation,
not a new automatic anti-rollback mechanism. Full-system, add-on, encrypted/cloud
restore, owner recovery, current production and final RC/HACS delivery remain
separate acceptance work.

The downloaded sanitized artifact `12298495220` was 9,973 bytes, SHA-256
`9cddebc2d5dc8bdea640e44969fd4dfc8e897824e26c9d005a6a6c25128d780f`.
Its digest, exactly eight JSON members, source/helper hashes, phases and cleanup
were independently verified. [Permanent narrow receipts](RELEASE-1.0-HAOS-RESTORE.json)
retain the negative safety results. The VM was stopped and the private workspace
removed after 343.119 host seconds. No private backup, raw log or account data
was exported or downloaded.

The earlier [published beta 20 investigation](ENABLED-RESTORE-PREPARED.md)
and [incomplete first attempt](ENABLED-RESTORE-VALIDATION.md) remain separate
historical results. This new run does not retroactively prove the first
timeout's sole cause.
