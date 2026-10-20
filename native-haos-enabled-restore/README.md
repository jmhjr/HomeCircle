# Prepared-dependency native HAOS enabled partial-restore investigation

This disposable Linux x86_64/KVM experiment uses HAOS 18.3 and observed Core/Supervisor 2026.10.2. It retains an enabled HomeCircle entry in a genuine Supervisor partial Home Assistant backup, including Recorder. Supervisor performs its supported restore and automatic Core startup; the harness does not disable/re-enable the entry around restore.

This followup explicitly supplies **prepared config-local dependencies** for offline startup. It does not validate ordinary default online dependency reinstallation, a full-system/apps backup, owner/provider-account restoration or production recovery. Both Life360 and Find My remain within the intended product scope; this fixture configures neither account.

The exact product is published `v0.1.0-beta.20`, source `d02a9bdb9027cb51c99165a09ba50d5b175f5fb9`, 112-file ZIP SHA-256 `fc0b365d9688459504f874af5c38393e24145d657f15f1def8ada9184f363285`. Product bytes, manifest requirements, guard implementation, Core image, declared dependencies and loading sequence remain unchanged. There is no `skip-pip`, loader patch or network-response stub.

## Preserved first attempt

[Run 39488244403](https://github.com/jmhjr/HomeCircle/actions/runs/39488244403) used the original unprepared fixture. Real Supervisor backup/restore completed with an enabled entry. The first restored helper observation read actual guard count **two/unblocked**, byte-bound to the old archive, after the newer installation had reached **three/blocked**. That is a genuinely observed local-counter rollback limitation.

The operational phase then timed out at a stage covering both entry loading and Person source readiness. Its retained receipts cannot determine which wait failed. Container-local dependency loss during Core replacement is a source-supported hypothesis, not a proven sole cause. The failed/incomplete attempt, exact source, five JSON receipts and artifact SHA `d1e79854b7c749dd19c9fac09f328f4a953061afc555b5a361a5a4a17659bac6` remain distinct evidence; no manual repair completed in that run.

## Prepared library and byte inventory

Before deploying the fictional configuration, a bounded child in the owned official Core container:

1. Requires actual Linux/x86_64, CPython 3.14.6, Core 2026.10.2, a non-virtualenv runtime and Core constraints SHA-256 `7baa9a8f39ddeb9c5bb60a1036f6d5e33f4b84267f151f53cc2b95ef031a21b5`.
2. Computes the config-local user-site using Core's actual `async_get_user_site`, then calls its normal `async_mount_local_lib_path`. It verifies the resulting `/config/deps/lib/python3.14/site-packages` precedes system package paths.
3. Makes one bounded `uv` installation of the six unchanged manifest requirements, constrained by that actual Core file. Installation uses binary wheels and copy mode into the fresh config-local target. It changes no image or source, and performs no identity or provider operation.
4. Records all 24 dependency closure names/versions, checks Python/requirement/Core constraints and metadata origins, and inventories the resulting regular files.

The dependency inventory covers **all regular dependency files except generated `__pycache__/*.pyc` files**. Those compiled caches are deliberately excluded because ordinary imports create them and Supervisor excludes cache contents. Unrecognized cache contents are refused; legacy `.pyc` files outside `__pycache__` remain inventoried. Symlinks, hardlinks and special files are refused. Bounds are 8,192 inventoried files, 96 MiB total dependency bytes and 64 MiB per member. The measured inventory digest/count/bytes are retained; the real backup must contain every inventoried byte exactly. The actual archive keeps the existing 128 MiB bound.

Every accepted fixture phase checks these inventoried non-bytecode bytes again. The real restored Core process must use its normal config-local path with ordinary requirement checking enabled. All 24 closure records are metadata/version/origin checks, not a claim that every package was imported. For each of the six direct packages, an already loaded module's actual `sys.modules` file is distinguished from an unloaded module's prospective import-spec origin. A loaded module from another origin cannot be relabeled as loaded from the prepared library.

## Six phases and separate outcomes

1. `initialize`: actual config/options flows create two fictional Persons with explicit registered trackers, city lookup disabled and no provider/prototype/migration entry. Record committed history and actual settings/registry/dashboard/frontend identities. Seed exactly two fictional local guard refusals; no passcode or proof is submitted.
2. `prebackup`: keep the entry enabled and loaded, await real persisted storage and create one genuine live partial backup with the database included. Inspect the actual archive for the enabled entry, exact candidate, database, guard count two and exact prepared dependency inventory.
3. `mutate`: change an option through its real flow, record post-backup-only history and add one local fictional refusal so count three is blocked. Retain the newest guard and history proof outside `/config`.
4. Close the sole external VM NIC through QMP, then perform one supported Supervisor restore. Its automatic startup is observed before any repair. `restored` proves enabled/loaded state, restored identities/settings, exact pre-backup history, absent post-backup markers, usable frontend and newly committed history. The earliest helper guard API observation is explicitly not an assertion that the helper preceded HomeCircle import/setup.
5. `repair`: only after automatic startup and operational evidence, stop Core, verify the observed restored guard, copy the separately retained newest guard and start Core. Check blocked count three and exact data continuity.
6. `restart`: another genuine managed stop/start checks identities, history, prepared dependency bytes and guard persistence. Recheck the closed external link, then stop and destroy the owned VM/private state.

Results remain separate:

- `operational_restore_passed`: normal startup/data/history/frontend acceptance within this prepared fixture.
- `automatic_guard_antirollback_passed`: whether the latest guard survives the older restore without repair.
- `manual_newest_guard_repair_passed`: the separately tested repair procedure.
- `prepared_enabled_restore_safety_accepted`: safety result for this observed prepared scope only.

Count two after count three is a safety finding. The controller continues the separate repair experiment if operational checks pass, then emits **`outcome=confirmed_safety_issue`, exit 1**. The gate may recognize an exactly completed investigation while keeping the safety result false. Unexpected errors or failed cleanup remain `failed_or_incomplete`, exit 1. Exit 0 requires all acceptance conditions including protection. `ordinary_enabled_restore_safety_accepted` and `ordinary_default_dependency_reinstallation_tested` remain false; this prepared fixture does not establish either broader result. Stable release approval is always false in the diagnostic gate.

## Diagnostics, network, bounds and privacy

Entry loading and Person-source waits now have distinct stage labels. Before waiting and on failure, narrow diagnostics retain only fixed entry-state labels, state/source-match counts for the two fictional members, skip-pip/path booleans and the six public dependencies' bounded version/availability/satisfaction/origin results. No entity IDs, raw attributes, exception messages, dependency error bodies or environment values are exported.

Initial official software installation and account-free setup use outbound NAT. Before restore, a bounded connection to fixed non-provider `1.1.1.1:443` must succeed. One QMP `set_link` closes explicitly named NIC `qa-net0`; identical probes must then fail while private QGA remains available. The link stays closed through automatic restoration, observation, repair and restart, covering both IPv4 and IPv6 through that sole NIC. Supervisor's own external access is also interrupted. No request-attempt counters are instrumented, so those counts remain explicitly **unmeasured**; closed egress does not mean no attempted requests.

There are no owner credentials, provider accounts, recovery proofs, GitHub tokens, production state, forwarded ports, host mounts or existing-HA connections. Actual KVM, independently pinned HAOS disk, private QMP/QGA sockets, exact returned backup job trees, one-shot mutations and owned-process cleanup remain mandatory. Existing Core/backup/restore/phase/global deadlines are unchanged; dependency preparation has a separate bounded child within the same controller deadline. The helper is never included in HomeCircle's installable ZIP.

Only fixed labels, versions, hashes, counts and booleans leave the guest. Archives, database, logs, configuration/state, identifiers, timestamps, account values and tokens stay private and are destroyed. Fresh QA controls use atomic replacement and token/generation checks; stale restored instructions cannot count as progress.

Run all standalone contracts with `python3 -B -m unittest discover -s native-haos-enabled-restore -p 'test_*.py'`. They execute standard-library controller/preparer/gate helpers, with no Core/native imports on the Mac. The actual Linux run is still required before claiming a prepared operational restore.

Primary contracts: [Core bootstrap](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/bootstrap.py), [Core requirements](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/requirements.py), [Core package helper](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/util/package.py), [Supervisor restore payload](https://github.com/home-assistant/supervisor/blob/2026.10.2/supervisor/backups/backup.py), [Supervisor archive module](https://github.com/home-assistant/supervisor/blob/2026.10.2/supervisor/homeassistant/module.py), [Recorder](https://github.com/home-assistant/core/tree/2026.10.2/homeassistant/components/recorder) and [QMP `set_link`](https://www.qemu.org/docs/master/interop/qemu-qmp-ref.html#command-set_link).
