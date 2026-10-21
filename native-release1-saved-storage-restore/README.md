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
and stays closed through cleanup. No provider factories, account login, real
owner records, device passcodes, or provider requests are used.

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

Automatic restored boot is observed only through raw saved state: the baseline
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
