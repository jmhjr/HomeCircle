# Current preview: explicit disabled-entry partial restore

Verified October 21, 2026. [Run 39674846677](https://github.com/jmhjr/HomeCircle/actions/runs/39674846677)
passed all eight phases of the account-free, explicit disabled-entry partial
restore procedure. Acceptance depends on retaining the newest guard outside the
entire guest and verifying its repair before re-enabling HomeCircle. Ordinary
enabled-entry restore safety and automatic guard antirollback remain unaccepted.

## Tested input and environment

Tested product source is `f4da650e6e460382c6ee1f70827bddac43bf2780`; validation
controls are `2d7fcbb40b021d84a21de7457222ef8f7191197d`. All 147 offline contracts
passed without skips. The fresh native amd64/KVM guest ran HAOS 18.3, managed
Core 2026.10.2, Supervisor 2026.10.3 and CPython 3.14.6. Both the API and container
reported the exact Core version.

The unreleased beta 20 development preview contained 113 runtime files, 617,757
ZIP bytes, SHA-256
`6fb180fc1f5c7de70382f95f8fe9e718f94841598dfc96d1afe233c8f21495db`.
The [machine-readable record](RELEASE-1.0-EXPLICIT-RESTORE.json) retains inventory,
source, served-asset and receipt fingerprints. Home Assistant installed ordinary
managed requirements with skip-pip false and no prepared dependency preload.

## Observed procedure

The local synthetic guard was 2 at backup and 3 after deliberate mutation.

| Phase | HomeCircle | Synthetic guard | External network |
|---|---|---:|---|
| initialize | loaded | 2 | open |
| initial_restart | loaded | 2 | open |
| quarantine | disabled and unloaded | 2 | open |
| mutate | disabled and unloaded | 3, blocked | open |
| automatic_disabled | disabled and unimported | restored older 2 | closed |
| repaired_disabled | disabled and unloaded | newest 3, blocked | closed |
| reenabled | loaded | 3, blocked | reopened |
| restart | loaded | 3, blocked | closed |

Supervisor completed actual partial-backup and partial-restore jobs without
reported job errors. The backup contained the disabled entry, exact candidate,
database and older guard. The controller retained the newer guard outside the
entire guest before restore. Automatic restore still returned the older 2;
the disabled entry and closed network prevented activation before repair.
This successful procedure therefore preserves the automatic antirollback
limitation observed in the historical experiments.

Guard export and import each passed in a separate owned, nonce-bound local
Core-image context. For each individual context, managed Core had the same
stopped process identity before and after that context. Each context retained
its 60-second bound, network isolation, dropped capabilities,
read-only image root, fixed owned bind and cleanup checks. The exact product
guard and strict three-rejection predicate were preserved. Repair was checked
before enable and the blocked status survived the final restart. These local
fixture counters do not measure Apple allowances or live recovery submissions.

Explicit Person/tracker selections, identities, nonempty settings, place,
portrait, dashboard and resource continuity passed. The saved snapshot was
identical in all non-mutation phases. All ten prebackup Recorder rows returned;
the ten postbackup marker rows disappeared; ten new postrestore rows persisted
through restart. Package and served frontend fingerprints matched.

## Retained evidence and limits

The sanitized artifact `12382106055` contains exactly nine JSON receipts, 14,328
bytes, SHA-256
`42625be11611f7db48e7e3f7d80116e0c5d652412390b999df349a380d4cdc37`.
Its API digest and size matched. Independent replay accepted all eight phases,
both contexts and cleanup. Both context containers were removed, the disposable
Linux guest stopped and its private workspace removed after 388.491 host seconds. No owner
credentials, provider accounts or production configuration were used. This
record publishes fingerprints and bounded observations, without raw guard,
private backup, account data or logs.

Saved Apple/Life360 credential and encrypted session-vault restore, authenticated
provider recovery, full-system/add-on/encrypted/cloud restore, production data,
HACS/release-ZIP transport, final RC acceptance and stable-release approval remain
separate gates. Provider request and recovery-proof attempt counts are unmeasured.
No provider report advancement follows from this test.

The [historical enabled-entry investigation](RELEASE-1.0-HAOS-RESTORE.md) and its
[negative safety record](RELEASE-1.0-HAOS-RESTORE.json) remain unchanged apart from
the crosslink in the historical prose. Earlier failed attempts remain failed;
their unretained guest ownership and precise filesystem cause are not measured
retroactively. A documentation child records this result; it does not change
the tested f4da650 runtime or establish runtime validation of a later source head.


## Vault-error candidate and saved-storage evidence

See [the vault-error candidate and restore requalification](RELEASE-1.0-VAULT-RESTORE-REQUALIFICATION.md)
for the separately tested source, retained negative trials, and experimental offline restore limits.
