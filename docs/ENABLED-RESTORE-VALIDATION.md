# Enabled-entry restore investigation: first attempt

[Run 39488244403](https://github.com/jmhjr/HomeCircle/actions/runs/39488244403)
and [permanent sanitized receipts](ENABLED-RESTORE-ATTEMPT1.json).

The run failed/incomplete, not as an accepted diagnostic: `526.898` host seconds, three accepted phases, real Supervisor backup and restore completed, then a fixture timeout in `restored`. Owned QEMU stopped and all private state was removed; `cleanup_failed=false`. No retry was performed.

Source revision: `096df4a0ce14915f52f6177fb1c19bec6fb49895`. Controller SHA `6f0cf91d4c60144cc919cb9d9ab1aa2138b87692cb3cfb985dd316a2a8352bfb`; helper SHA `c7b20692a3b6c43ef581e2f5105fd40a0753e0bd9243642737f5cef9adefab66`. These match the reviewed prepared files. The 52 standalone harness/gate contracts passed before guest execution.

Artifact `12295346050` is 4,872 bytes, SHA-256 `d1e79854b7c749dd19c9fac09f328f4a953061afc555b5a361a5a4a17659bac6`, matching GitHub metadata. Its exact five JSON files were validated and retained with `MEMBER-INVENTORY.json`. The downloaded full workflow log is private diagnostic input, not an artifact proposed for publication.

## What the real receipts establish

- HAOS 18.3, native x86_64 and actual KVM; observed Core/Supervisor 2026.10.2 and CLI 2026.09.0.
- The exact published beta20 ZIP was installed: SHA `fc0b365d9688459504f874af5c38393e24145d657f15f1def8ada9184f363285`, 112 files.
- Initialize, persisted enabled-entry prebackup and mutation passed. Both selected fictional Persons and trackers worked; original settings/identity/history/served frontend checks passed before restore. Ten committed prebackup rows and ten post-backup-only rows were observed.
- The genuine partial backup's actual archive contained the enabled entry, database, exact candidate and guard count two. Both exact returned Supervisor job trees completed without errors: three backup nodes and four restore nodes. Both supported requests exited zero with successful JSON results.
- Before restore the real guard was count three/blocked, SHA `6a539827f2c55dc92c6221bc2edee2ad3e18ada0a2bccf607f2f502b9c309106`.
- The positive external TCP control succeeded, then the sole VM NIC was closed. Two negative controls failed as required while QGA remained available.
- Supervisor automatically created a new Core process. At the earliest helper observation the entry was enabled, not yet loaded, and actual guard status was **two/unblocked**, SHA `9df3bd3987e0b2e070259432ebd8c39b29b23c055e8788364af668907fbb0ba6`, exactly matching the archived old guard.

The local guard rollback limitation is therefore **observed**, despite the incomplete operational phase. There is no basis to mark ordinary enabled restoration safe. No manual repair phase ran.

## Exact failure and causal limits

`restored.json` reports `TimeoutError`, phase `restored`, stage `restored_external_proof`. That stage covers both waiting for HomeCircle `LOADED` and subsequently waiting for the two Person source/state associations. The retained receipt does not distinguish those waits or contain dependency availability, so the sole runtime cause cannot be proven retrospectively. The workflow log contains no additional guest exception/state detail; the private guest was correctly destroyed.

A strong source-supported **harness environment hypothesis** is custom dependency loss during Core replacement. Supervisor [removes the Core container during Home Assistant restore](https://github.com/home-assistant/supervisor/blob/2026.10.2/supervisor/backups/backup.py), while Core's [Docker dependency installation](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/requirements.py) does not use `/config/deps`; its [installer](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/util/package.py) selects a container-local Python target. Closing the whole VM's external link prevents fetching any requirements absent from the replacement image. The original claim that cached image/dependencies necessarily sufficed was not proven by a fresh-container dependency check.

This is not evidence of a HomeCircle selection/identity restoration defect. The separately observed old guard is a real local-counter restore limitation. Both providers remain within the intended 1.0 scope; this fixture uses neither provider account.

## Narrow correction and defensible followup

First add separate `restored_wait_entry_loaded` and `restored_wait_person_sources` stage labels, with sanitized before-wait/at-failure entry state, presence of fictional tracker/Person states, and the six public manifest dependency availability/version/satisfaction results. No raw exceptions, state attributes, identifiers, logs or environment values should leave the guest.

For a fully offline operational followup, explicitly prepare dependencies in Core's supported config-local library before initial candidate boot and backup. [Core bootstrap](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/bootstrap.py) normally prepends the `/config/deps` user-site when not in a virtual environment. Install the exact manifest requirements under actual Core constraints into that directory, require the real runtime to use that normal path, and inventory the complete resulting closure. Prove those exact bytes are in the actual backup and present at restored startup. Keep ordinary requirement checking enabled and leave the Core image, candidate bytes, guard and network boundary unchanged.

That would qualify a **prepared-dependency, offline partial restore**, not default online dependency reinstallation or full-system recovery. A narrow staged diagnostic correction can be reviewed before committing any followup. No published harness or product was changed during this diagnosis.


## Subsequent prepared-dependency investigation

[Run 39492348166](ENABLED-RESTORE-PREPARED.md) completed all six operational
phases on the exact published beta 20 artifact. Settings/selection/identity/
frontend and Recorder restoration passed; manually returning the separately
retained newest guard also passed and persisted across restart. Automatic
startup still restored guard two instead of the newer three. The completed
diagnostic retained `ordinary_enabled_restore_safety_accepted=false`,
`prepared_enabled_restore_safety_accepted=false` and no stable approval.
It does not retrospectively prove the first timeout's sole cause. A separate
check of the newer 113-file development artifact remains distinct work.
