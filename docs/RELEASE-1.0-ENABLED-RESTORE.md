# Enabled saved-account restore investigation

Recorded October 21, 2026. [Native run 39708377110](https://github.com/jmhjr/HomeCircle/actions/runs/39708377110)
passed all 186 zero-skip contracts and five enabled managed phases on disposable
amd64/KVM HAOS 18.3, Core 2026.10.2 and Supervisor 2026.10.3. Host execution took
523.964 seconds and owned guest/private-workspace cleanup passed.

This qualifies an instrumented synthetic Home Assistant partial restore with
prepared dependencies and explicit newest-guard repair. The ordinary restore
safety release gate remains open. The [machine-readable record](RELEASE-1.0-ENABLED-RESTORE.json)
and [retained replay inputs](https://github.com/jmhjr/HomeCircle/blob/7b6bc8697e8eee06c9e53b6751a51fda4c483255/native-release1-enabled-evidence/README.md) preserve the exact scope.

## Candidate and isolation

Tested runtime source is `91ae59106a661143b770d7a3564d363c7c11a7dd`.
The original 113-member package remains ZIP
`004c9bc4a968ad395e18033837cb42f5bd1d8719a8d90fc778fd20be4ff08f97`.
Staging retained 112 members unchanged and appended one QA dependency to
`manifest.json`. That dependency installed the transport fence synchronously
before HomeCircle component/runtime setup. The original and adapted manifests,
all helper files and disposable configuration were bound in the actual archive
before the restore network window opened.

Real SDK clients restored fictional saved sessions. Four explicit registry
joins bound two selected Find My items and two tracker-only person-kind members.
Actual Find My session restoration and its two saved reports passed in every
enabled process. Each process made two attempts through the legacy Find My HTTP
path to the fictional Anisette endpoint, and one Life360 request. All were denied
before DNS/transport; Find My report HTTP was not reached. Recovery dispatch,
command and recovery-HTTP seam counters stayed zero. No successful provider
authentication or new cloud location was simulated or claimed.

The 24-package config-local dependency closure was prepared under the actual
Core constraints. Its 1,002 non-bytecode files, 71,691,807 bytes and metadata
origins were checked in the archive and managed phases. This is prepared-library
evidence; fresh dependency resolution remains separate.

## Restore, preservation and guard outcome

Supervisor used its ordinary conditions with zero jobs/options mutations and
no global override. One restore-only network window had acknowledged opening
and closure, one read-only readiness observation, and confirmed host/Supervisor
internet readiness. Thirty-two closed-link observations and guest-agent checks
bounded the private contexts and restored observation.

The five distinct Core processes preserved saved configuration, explicit tracker
identities/selections, account/session and encrypted pair consistency, display
settings, place and member picture. The actual image collection, original PNG,
served image and frontend bundle passed. Independent Recorder checks restored
six pre-backup rows, removed six post-backup markers and retained six new rows
after restart. No Home Assistant Person entry was seeded; complete Person
associations and HomeCircle activity-history acceptance remain separate.

The synthetic guard sequence was **2 → 3 → 2 → 3 → 3**. The first automatic
enabled restored startup brought back the older ledger bytes and loaded its
saved Find My vault before manual repair. Normal provider startup did not use
the recovery API. After Core stopped, the newest ledger retained outside the
entire guest was imported; its actual local API reported the fictional identity
blocked at three, and that state survived restart. The guard's fixed fictional
identity is separate from the SDK session account identity. This witnesses
ledger restoration/API/repair persistence, without proving account-bound
recovery authentication or automatic rollback detection.

Four offline Core-image storage contexts and two separate guard contexts
retained network-none isolation, dropped capabilities, read-only roots and
stopped-Core ownership. Both post-repair validators passed the original 18
cloned fault cases, unchanged main-store/no-op checks and clone cleanup.

## Evidence checker correction

Review confirmed that the earlier scoped consumer accepted coordinated
self-reported manifest/payload hashes, a loose count type and an extra nested
field. The separate [hardened consumer](https://github.com/jmhjr/HomeCircle/blob/7b6bc8697e8eee06c9e53b6751a51fda4c483255/native-release1-enabled-evidence/independent_evidence.py)
binds every source/tool hash and exact nested schema to the frozen inputs and
separately verified GitHub metadata. All 32 checker contracts passed. In-memory
mutations of the actual receipts reproduce all five old acceptances and new
refusals; the unchanged original artifact passes the corrected replay.
The native fixture and its result remain frozen; the checker performed no new
VM or provider execution.

The [independent native audit](https://github.com/jmhjr/HomeCircle/blob/7b6bc8697e8eee06c9e53b6751a51fda4c483255/native-release1-enabled-evidence/evidence/peer-native-audit.json)
also verified the six original receipt bytes, source bindings, restore/guard/
history boundaries, cleanup and 30 rejected mutations of the actual packet.
The exact 10,239-byte public synthetic artifact is retained with its GitHub
digest so replay remains available after the temporary artifact expires.

## Remaining gates

Ordinary unmodified enabled restore, automatic guard antirollback, account
authentication/renewal after restore, full-system/encrypted/cloud variants and
stable release approval remain unqualified. The disabled-entry safe procedure,
this instrumented trial and the [real ARM64 saved-connection restart witness](RELEASE-1.0-ENABLED-CANDIDATE.md)
remain separate evidence. No existing test/everyday instance, real credential,
device passcode, recovery proof, refresh setting or remote-access state changed
for this trial. The [release plan](RELEASE-1.0-PLAN.md) retains the open gates.
