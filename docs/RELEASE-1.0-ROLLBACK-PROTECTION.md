# Recovery-guard rollback protection — validated

Recorded October 21, 2026. The product correction, exact-source native package
checks and ordinary enabled synthetic partial restore have passed. The scoped
restore safeguards are accepted; broader Person/activity-history and backup
variants remain open in Stage 4.

## Confirmed defect and implemented correction

The earlier [enabled saved-account trial](RELEASE-1.0-ENABLED-RESTORE.md) restored
an older ledger at two after the running installation had reached three. Its
explicit newest-ledger import repaired that trial, while automatic rollback
protection remained absent. That historical result and its separate fictional
guard identity remain unchanged.

The candidate now pairs each authenticated account's ledger entry with a digest
witness under `config/.cache/homecircle_findmy/recovery_guard`. The witness binds
the account identity and exact canonical entry. Ledger version 2 gives every
changed account entry a fresh generation, so resetting and returning to the same
counter values cannot make an older entry match the newer witness.

A missing, mismatched or legacy unwitnessed entry requires explicit review.
Fresh accounts require the same review before their first guarded unlock.
Untrusted status reads preserve the restored counters and pending reservation;
they do not repair a witness or silently create a new allowance. Attempt entry,
the before-dispatch reservation and outcome callbacks enforce continuity.
Filesystem modes, ownership, symlink/hardlink refusal, bounded reads, account
locks and the shared ledger lock remain enforced. Proof readiness follows the
durable ledger and per-account witness writes; failed or interrupted work cannot
automatically enroll an untrusted account.

The existing explicit acknowledgment resets only that authenticated account's
local unresolved counters and establishes only its witness. Other accounts stay
blocked when their continuity is unknown. Acknowledgment sends no proof, performs
no authentication and does not reset Apple's server allowance. A matching witness
survives an ordinary restart. Cache eviction safely requests review again.

The mechanism does not recover a lost higher counter. Its restore protection
comes from refusing further guarded recovery when continuity is unavailable.

## Exact-source native validation

[Native run 39715519894](https://github.com/jmhjr/HomeCircle/actions/runs/39715519894)
passed on Linux x86-64, Core 2026.9.4 and Python 3.14.6:

- 1,728 backend tests passed, zero failed; one existing optional public Apple DMG
  fixed-range fixture remained skipped. All 50 required functions passed.
- 122 frontend tests passed. Reproducible frontend output and release bytes passed.
- All 371 source members matched canonical Git blobs; the canonical privacy
  checker reported zero flags. Owned container/private-workspace cleanup passed.

The packet retained 14 cause-verified red cases for the earlier vault
failure/redaction/disconnect corrections, followed by the passing full candidate
suite. Those cases have their own baseline scope; the new rollback behavior is
covered by the required guard and review-flow regressions. These include retained
newer witnesses, cache loss, per-account acknowledgment, same-counter generation
changes, legacy/empty ledgers, storage failures, interrupted reservations and
filesystem rejection cases.

A first native attempt exposed HA test isolation: the plugin's shared physical
configuration directory retained a witness between flow tests, beyond mocked HA
Store state. The passing revision changes only `tests/test_findmy_flow.py` to use
`hass_tmp_config_dir` for each test. Product runtime bytes remain identical.

Canonical source is `57b0aaa5c2c4b1a022e547347640173412e840f5`, a tests-only child of
runtime source `012a7e88d13970b2683b27d0824dac246c858179`. The 113-file development ZIP
is `98a754ff2025761c2eb63d6422c9b17b76e2bdef2965c96fe353ab6c2c21fb20`
(620,228 bytes); the inventory file is
`370a0036f03bd2b7185afc7a9ddcf7d6545e41cfb6394f00fc699a2973db33aa`.
All 111 literal runtime inputs match both source commits, and two generated
frontend outputs match the native receipt. This exact ZIP is also the ordinary
trial's payload. Its retained version remains an unreleased development preview.

The independent backend audit checked downloaded GitHub metadata and artifact
digest, all six receipt hashes, frozen QA inputs, canonical source blobs, the
exact test-only delta and ordinary-payload equality. Its receipt SHA256 is
`8dfcacc4ff08823381e3e2d5b4eb73404908f96403c88898bb3534a8ca6bf728`.
The [machine-readable record](RELEASE-1.0-ROLLBACK-PROTECTION.json) binds these facts.

## Ordinary restore result — passed

The [ordinary restore record](RELEASE-1.0-ORDINARY-RESTORE.md) retains failed R1
[39714666021](https://github.com/jmhjr/HomeCircle/actions/runs/39714666021) and R2
[39716881615](https://github.com/jmhjr/HomeCircle/actions/runs/39716881615), each
with zero accepted phases and no backup request. R2's fixed diagnostic and a
separate forced-order replay established a sufficient synthetic-seed defect;
exact deleted guest values are not inferred.

R3 [39717938959](https://github.com/jmhjr/HomeCircle/actions/runs/39717938959)
passed baseline/mutation, actual archive omission and successful backup/restore
jobs under default conditions, then timed out without an automatic restored
receipt. All three trials passed owned cleanup. R3's missing receipt left
restored guard admission and ordinary qualification unverified in that trial.

Separate source replays confirmed control-publication and pregrant diagnostic
fixture defects. R4's atomic publication, post-grant input reload and bound
failure diagnostics passed 33 fixture contracts, eight frozen consumer contracts
and three independent schedules. The deleted native guest's exact cause remains
undetermined; product bytes, deadlines and success gates are unchanged.

R4 [39720944024](https://github.com/jmhjr/HomeCircle/actions/runs/39720944024)
repeated those pre-restore, archive and job passes, then produced a fresh
`qa_startup_boundary_shape` failure after a verified closed-boot grant. Cleanup
passed; no restored guard-admission result is accepted. Independent source
schedules and a real guard-import discriminator narrow a lazy guard-hook order
defect. The deleted native loaded-kind set was not recovered. R5 moves the
existing guard receipt before the unchanged six-target runtime gate; product
bytes remain unchanged.

[R5 39721983991](https://github.com/jmhjr/HomeCircle/actions/runs/39721983991),
QA head `4957b3f44e84837e01af731286c0728a4127aea3`, passed all four enabled phases
on amd64/KVM HAOS 18.3, Core 2026.10.2 and Supervisor 2026.10.3. Actual guard
counts were two, three, two, two; review flags were false, false, true, true.
The archive excluded the witness, which was absent on automatic restored startup
and restart. Both real restored attempts were refused before their bodies ran,
bound to the actual saved SDK identity, with no manual repair or post-restore
acknowledgment. All measured recovery seams remained zero.

The unchanged 113-file product and manifest used normal managed requirements,
with install counts two, zero, two, zero and a verified 24-distribution closure.
Default Supervisor backup/restore jobs completed without errors or jobs/options
mutations. Saved selection/settings/place, four explicit tracker joins, pictures,
served frontend bytes and encrypted storage passed. Recorder restored six exact
baseline rows, removed the six post-backup mutations and kept six new restored
rows through restart. All four owned offline storage contexts and cleanup passed;
elapsed host time was 461.542 seconds.

Artifact SHA256 is `d87250aef1cb73fce9d5de778f005ec9e678732044b11c96c0890442469c956a`
(10,038 bytes, ID `12401877265`). The independent frozen consumer accepted the
five actual receipts, metadata, all 27 inputs and source/package bindings.
Root and peer review output matched at
`a0ba3a1340c72e9a7add31bf472a0cf63caadd48e8620e53eafa96369cd32209`;
detailed peer audit SHA256 is
`f7e8857f449ba36a8a4ca08fe5915e9891e512f9f4a51034cf2851c68cc10b1c`.
The [retained public evidence](https://github.com/jmhjr/HomeCircle/blob/8f28d5da33b7094355e84d5c8a23ee78463cecf3/native-ordinary-rollback-evidence/INDEX.md),
including a [portable replay](https://github.com/jmhjr/HomeCircle/blob/8f28d5da33b7094355e84d5c8a23ee78463cecf3/native-ordinary-rollback-evidence/REPLAY.md),
preserves the exact accepted packet. Replay of its committed 20 files passed.
This closes the scoped ordinary partial-restore and automatic recovery-block
cases while retaining every failed trial above.

## Protection boundaries and preservation

The pinned [Core backup filters](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/components/backup/const.py) and
[Supervisor backup/restore implementation](https://github.com/home-assistant/supervisor/blob/2026.10.3/supervisor/homeassistant/module.py)
exclude `.cache/*`; ordinary configuration restore removes the destination cache. R5 verified
actual archive exclusion and witness absence on the first restored startup and
restart. Both required review and refused the guarded attempt before its body. A partial ledger rollback that retains a newer
witness is also refused by its digest mismatch.

A full VM or complete configuration snapshot can capture and restore both the
old ledger and its matching cache witness. Detecting that rollback requires an
independent external monotonic anchor. Cache eviction therefore costs an explicit
review, and no missing newer counter or Apple server allowance is inferred.
A pre-fix backup may also restore old integration code; install the patched
candidate before using recovery after such a restore.

The working owner test instance remains on source
`91ae59106a661143b770d7a3564d363c7c11a7dd` and was not updated. No owner instance,
real credential, device passcode, recovery proof, refresh setting or remote-access
state changed for these checks. Provider authentication/renewal, full-system or
encrypted/cloud restore, full Person/activity-history acceptance, HACS delivery
and stable release approval remain separate gates.
