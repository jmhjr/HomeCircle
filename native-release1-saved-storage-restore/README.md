# Disabled-entry synthetic saved-storage partial restore

This is a separate qualification procedure, prepared for candidate source
`91ae59106a661143b770d7a3564d363c7c11a7dd`. Preparation and local contracts are
not a successful restore receipt. The previously accepted eight-phase fixture
and its evidence remain unchanged.

The disposable HAOS 18.3 guest must begin with Core 2026.10.2 and Supervisor
2026.10.3. The reviewed package must first pass the independent native package
gate: 1698 backend cases, 122 frontend cases, all 36 required functions, and
14 source-bound old-vault failures with their expected causes. Its 113 runtime
members differ from the prior candidate only in `findmy_vault.py`.

The five phases are `baseline_disabled`, `mutated_disabled`,
`automatic_restored_disabled`, `repaired_storage_disabled`, and
`restart_disabled`. The HomeCircle entry remains disabled and the managed
integration remains unimported throughout. The guest NIC closes before seeding
and stays closed for all seed/mutation, guard, and vault contexts. A single
restore-only network window is described below. The direct providers remain
unimported; no real owner records, device passcodes, or account login are used.
Provider request counts remain unmeasured.

The stopped-entry seed writes one schema 1.5 Home Assistant config entry with
synthetic Apple account metadata and a real encrypted Fernet key/vault pair,
plus Life360 credentials in their actual HA config-entry storage. Life360 has
no separate HomeCircle encrypted vault. Four private, explicit selection joins
bind two Apple items and two Life360 trackers. Managed Home Assistant loads the
disabled record, registers those explicit disabled registry entries, and saves
a title-only config-entry update through its actual API. The title must persist
without changing data/options, and must survive restore and restart. No Person,
picture, map, active tracker, or provider authentication result is claimed.

The actual Supervisor partial backup must include the saved pair, both
config-entry snapshots, selection and registry joins, package, guard, and
independent synthetic Recorder history. A discriminating mutation changes all
seven private fingerprints, including credentials, pair, ledger and selection,
and advances the local synthetic recovery guard from 2 to 3. The newest guard
is exported outside the entire guest. Backup inspection does not decrypt.

Every QA helper boot waits in its existing background task for a one-use host
grant targeting that exact process and phase. It publishes only boot metadata
before receiving a grant; no baseline, selection, key, vault or guard read can
run first. Grants are private, exact-source/token/branch/generation/process bound,
and consumed before dispatch. An unexpected restart receives no automatic grant.

Automatic restored boot is observed only after the network is closed through raw saved state: the baseline
pair/config/selection returns alongside old guard 2. A fresh, strictly newer
process and an absent pre-restore marker are required. Managed Core then stops;
the separate retained guard is imported through the existing bounded guard
context before any restored vault load. Four separate offline Core-image
contexts execute the actual SHA-bound Vault and identity modules without
executing HomeCircle's package initializer. Each context has no network,
dropped capabilities, a read-only root filesystem, one private configuration
mount, bounded execution, and matching stopped managed-Core identity before
and after that context.

Both post-repair contexts require actual restored decryption and identity
checks, an unchanged valid main pair on no-op load, and 18 cloned negative
cases. Missing, wrong or malformed keys; damaged ciphertext; unsafe pair paths;
foreign ledger/metadata; divergent snapshots; and invalid registry joins must
refuse. Clone cleanup and main-store preservation are mandatory. Only private
hashes cross the guest boundary; uploaded receipts contain fixed checks and
counts. Independent QA-only Recorder entities prove old history restoration,
post-backup marker removal, and new post-restore history surviving restart.

This procedure qualifies only the explicit disabled-entry saved-storage partial
restore it actually completes. It does not qualify automatic rollback
protection, ordinary enabled-entry restore, provider authentication after
restore, full-system or encrypted cloud backup, stable release approval, or
HACS acceptance. A valid older vault pair remains a valid encrypted snapshot;
the separate guard repair is explicit and must not be described as automatic
anti-rollback protection.

## HA-managed store mode compatibility revision

The first saved-storage trial, run 39685990663 at controls `630fb69`, failed
before the seed completed, with zero accepted phases and no backup or restore.
The owned context and disposable guest were cleaned up. Its safe inner failure
stage was discarded by the old controller, so the precise runtime cause remains
unproven; the negative record stays negative.

Primary Core 2026.10.2 storage code and an execution of its exact stdlib file
writer establish a separate fixture incompatibility: ordinary HA-managed stores
use mode 0644, while the fixture required 0600. This revision admits only 0600
or 0644 for the two exact owned HA stores, `core.config_entries` and
`core.entity_registry`, with unchanged no-follow, regular-file, ownership,
single-link and size checks. Existing config-entry replacement admits 0644 but
writes a new 0600 file atomically. Private keys, ciphertext, guard state and
proof files remain subject to their unchanged 0600 checks.

A failed storage context can now retain only its fixed action and allowlisted
stage from the helper's exact bounded three-field failure response. This adds no
raw stderr, exception text, account data or paths and does not change success
acceptance. All 97 offline contracts must pass. Product source, the 113-member
candidate ZIP, both context security boundaries, five phases, 18 cloned negative
cases, closed NIC and cleanup requirements are unchanged. This revision is
prepared for a fresh trial; it does not reclassify the failed run as successful.

## Retained trial history and new default-conditions procedure

Run 39688084686 at `e44ae2a` passed actual synthetic seed and mutation (including
Fernet), two managed phases, backup creation/archive inspection and newest-guard
export. Supervisor then refused restore with `host_internet_unavailable` while
the NIC was closed. Its negative record `117beac4…` retains those positive
observations and the refusal. This differs from the first trial's unknown cause.

The separately authorized R4 run 39691770592 at `3c1e9e72` passed all five phases,
four storage and two guard contexts under a temporary global, persisted,
unsupported two-internet-condition override. Its independent audit `cb2cae2d…`
qualifies that experimental procedure only; it does not become normal/default
Supervisor evidence. R4 source and receipts remain frozen and unchanged.

This R5 child uses Supervisor's ordinary restore conditions. It contains no
jobs/options POST, reset, apply/clear action or global override. The read-only
CLI bridge permits only fixed GET jobs/info and network/info. Its existing token
stays inside the owned CLI container and reaches curl only through header stdin;
there is no credential discovery, client install or alternative transport.
Effective ignore_conditions must be exactly empty and the fixed persisted store
must be empty or absent before and after the window. Unknown/foreign state
refuses without writes. Visible relevant backup/Core jobs must be idle before
opening; this is not a claim that hidden jobs or arbitrary requests are idle.

Before opening, Core is stopped, the exact disabled/unimported mutated phase and
single saved USER-disabled record are checked, all 113 package bytes and cached
same-Core image are rechecked, and the already inspected local archive is bound.
The controller reserves 90 seconds outside the normal deadline. It marks an
opening attempt before one QMP up request, proves external connectivity with an
independent TCP control, then waits at most 90 seconds/18 GETs with five-second
spacing for network/info host_internet and supervisor_internet to be exactly
true. No force/refresh/reload endpoint is called; failure stops cleanly.

The unchanged synchronous Supervisor restore operation is invoked once. FINALLY
always makes one bounded QMP down attempt after any opening attempt, including
lost opening ACK, positive-probe failure, restore refusal, cancellation or lost
restore response. A confirmed close, independent negative TCP probe, guest-agent
ping and default-empty effective/persisted observations are required within the
reserved deadline. Any uncertainty prevents postrestore grants and acceptance;
owned guest cleanup still follows. There is no restore retry.

Only an affirmative completed restore followed by verified closure/defaults can
authorize the automatic restored process. Its metadata request must have a
strictly newer start tick; stale requests carried by the archive cannot qualify.
The private grant and its temporary path must be absent from both the inspected
backup and the prewindow state. Its atomic writer verifies its own temporary
bytes before publication; the helper may consume immediately, so the host does
not assume the grant remains for a second read. The helper receipt proves grant
consumption. This blanket gate also covers partial failures that boot old
mutated controls or controls without a baseline file.

All 116 zero-skip contracts are required: the original 97 applicable core/storage/
guard cases plus 19 default-window/grant cases replace R4's 15 override-specific
cases. All 32 protected infrastructure method ASTs, both context security
boundaries, product bytes and 18 cloned negative cases remain unchanged.
Successful scope is exactly a default-conditions DISABLED synthetic saved-account
partial restore with explicit newest-guard repair. The precise accepted flag is
`default_conditions_disabled_synthetic_restore_qualified`, with
`default_supervisor_conditions_used` and `manual_newest_guard_repair_required`.
Generic enabled/provider/automatic rollback/full-system/cloud/HACS/stable gates
remain false. Preparation and contracts are not an actual R5 result.
