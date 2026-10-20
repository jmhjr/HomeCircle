# Disposable native HAOS guarded partial backup restore

This separate harness tests a genuine Supervisor **partial Home Assistant backup and restore**, including the Recorder database, on a fresh native Linux x86_64 KVM guest. It uses HAOS 18.3, managed Core 2026.10.2 and requires observed Supervisor 2026.10.2. The exact frozen 112-file candidate ZIP remains `f0477a91e78181fe1f8d80ada176a1739e10a7502abe7ee6ee2240571280d1f5`; no candidate code, version, release, tag, default branch, production configuration or prior rehearsal evidence is changed.

No owner account, provider account or GitHub token is placed in the guest. The workflow checkout has read-only repository permission with persisted credentials disabled. The guest has outbound NAT for official software installation, with no forwarded ports, host-directory mounts, SSH or connection to an existing Home Assistant. The launcher refuses macOS and non-x86_64 Linux; all Python executes on the native Linux runner or inside its owned Linux guest.

## Restore barrier and scope

Supervisor's supported restore operation automatically starts Core before returning. The backed-up HomeCircle entry is therefore deliberately disabled through the supported config-entry API and actually unloaded before backup. The helper waits for the real stored disabled state and nonempty options to reach disk. The backup includes that disabled entry, exact candidate files, saved identities and the real Recorder database.

After backup, the fixture makes a genuine options-flow change while the entry stays disabled, records committed post-backup history and creates three local synthetic recovery refusals. It keeps the newest guard outside `/config`. Supervisor then performs the genuine partial restore, which boots with HomeCircle still disabled. While Core is stopped, the controller verifies the restored disabled entry, reattaches the separately retained newest guard, and installs fresh QA generation/nonce controls. The helper checks the restored state and guard bytes before the only explicit re-enable.

This is an explicit guarded recovery procedure. It does **not** establish automatic guard anti-rollback under storage replacement, ordinary enabled-entry restoration, a full Supervisor/apps restore, encrypted/cloud backup portability or live provider recovery. The backup archive and database remain private inside the disposable guest and are removed with it; only size/digest/presence proofs leave the guest.

## Six phases

1. `initialize`: create two persistent synthetic Persons with explicitly selected registered trackers, actual HomeCircle config/options flows and an unrelated frontend resource. Record real Person/tracker/sentinel transitions, prove committed timestamped Recorder history, backup-platform registration and SQLite integrity, and capture guard status zero.
2. `quarantine`: disable HomeCircle through Core's supported config-entry API, await unload and the persisted disabled/options store, and capture the exact quarantined state. The owned frontend resource is intentionally deleted by normal unload.
3. The controller creates exactly one genuine live partial backup with database exclusion explicitly false. It verifies the exact returned job and every child completed without errors, backup metadata, and the actual uncompressed archive's database, exact candidate package, disabled entry and old guard bytes. `mutate` then changes saved options, records a post-backup-only history window and seeds guard status three while the entry remains disabled.
4. The controller independently retains the latest guard and private synthetic history window, performs exactly one supported partial restore, and reattaches the latest guard while stopped and disabled. `restored_quarantine` verifies the exact backed-up disabled state, identical pre-backup timestamped history, absent post-backup records and retained latest guard bytes, without a candidate guard API call.
5. `final`: only after the guard proof, explicitly re-enable HomeCircle. Verify unchanged entry/options/Person/registry/dashboard/unrelated-resource identities and exactly one newly owned resource serving current bytes. The candidate guard API must remain blocked at three. Record and commit new post-restore history.
6. `restart`: after a real managed Core stop/start, verify candidate activation, identities, guard status and exact post-restore history persistence again.

The owned HomeCircle resource ID is expected to be recreated after supported disable/re-enable; the unrelated resource and dashboard IDs must persist. This lifecycle is distinguished from resource identity continuity across a simple restart.

## Bounds and evidence

The controller requires actual KVM confirmation, an independently pinned HAOS base disk and a fresh overlay/UEFI variable store. QGA/QMP use private sockets. Every stop/start is one API request with an explicit successful JSON result and observed actual state within a shared 180-second bound. Initial managed readiness requires root lifecycle `running`, relevant Core jobs idle, the expected mount and actual installed Core version; initial and target windows retain the trusted 1500/1200-second bounds. Backup and restore are each one request, with total bounds of 900/1200 seconds. There are no mutating retries.

The whole controller has 5520 seconds plus a reserved cleanup interval; the outer launcher has a 5700-second timeout and 45-second kill grace. The workflow has enough separate preparation/upload allowance. Cleanup can signal only its actual QEMU child process group whose start identity and VM nonce still match. Candidate files and the helper never enter the production release artifact.

Public JSON contains only fixed labels, versions, hashes, counts and booleans. No archive, DB, raw state, entity IDs, history timestamps, raw HTTP bodies/headers, backup names/slugs, account data or token is uploaded. New post-restore instructions and receipts must match the fresh generation/token; restored stale control files cannot count as progress. The VM ownership nonce never rotates when the phase token changes.

## Primary source contract

The implementation was checked against these official pinned sources; the actual runtime versions and CLI capabilities are separately observed before mutation:

- [Supervisor 2026.10.2 backup API](https://github.com/home-assistant/supervisor/blob/2026.10.2/supervisor/api/backups.py): partial backup/restore fields and `homeassistant_exclude_database` metadata.
- [Supervisor 2026.10.2 backup manager](https://github.com/home-assistant/supervisor/blob/2026.10.2/supervisor/backups/manager.py): genuine backup jobs and unconditional Core start in restore's final stage.
- [Supervisor 2026.10.2 backup payload](https://github.com/home-assistant/supervisor/blob/2026.10.2/supervisor/backups/backup.py) and [Home Assistant module](https://github.com/home-assistant/supervisor/blob/2026.10.2/supervisor/homeassistant/module.py): full Home Assistant config replacement, live backup start/end hooks, DB/WAL inclusion and exclusions.
- [CLI create](https://github.com/home-assistant/cli/blob/bf6d59ff097e6da6aca179a4bac1b6cba133d1ba/cmd/backups_new.go) and [restore](https://github.com/home-assistant/cli/blob/bf6d59ff097e6da6aca179a4bac1b6cba133d1ba/cmd/backups_restore.go): `--folders homeassistant` selects partial creation; explicitly setting `--homeassistant=true` selects partial restoration. The guest's bounded read-only help must expose every used flag.
- [Core 2026.10.2 Recorder](https://github.com/home-assistant/core/tree/2026.10.2/homeassistant/components/recorder): real commit, read-only history queries, backup-platform hooks and integrity checks. Closed time windows are retained privately; identical pre-backup and post-restore projections must survive restoration/restart, and the post-backup-only window must disappear.

Pending: execution on the approved isolated branch and independent review of its exact sanitized receipts. A source review or passing offline contract alone does not qualify the live restore.
