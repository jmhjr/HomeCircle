# Unreleased candidate: prepared-dependency native HAOS enabled partial-restore investigation

This separate disposable Linux x86_64/KVM fixture targets HAOS 18.3 and pinned Core/Supervisor 2026.10.2. Its six-phase Core, Recorder, guard, network and cleanup behavior is inherited from the completed prepared-dependency experiment; the candidate pins, member count and preview provenance are the only runtime differences. It retains an enabled HomeCircle entry in a genuine Supervisor partial Home Assistant backup, including Recorder. Supervisor performs its supported restore and automatic Core startup; the harness does not disable/re-enable the entry around restore.

This candidate fixture explicitly supplies **prepared config-local dependencies** for offline startup. It does not validate ordinary default online dependency reinstallation, a full-system/apps backup, owner/provider-account restoration or production recovery. Both Life360 and Find My remain within the intended product scope; this fixture configures neither account.

The exact input is an **unreleased development preview**, still manifest version `0.1.0-beta.20`, from canonical product source `9bf03eb45d2cf43274074534e9dfe2de841f4011`. Its 614,209-byte, 113-member ZIP has SHA-256 `c4530d94be3b2996f8d6c8948db88a51868566047d68558eefde7967f270a861`. The local `payload/homecircle.zip`, exact per-member `payload/inventory.json` and `payload/provenance.json` retain the package produced and independently matched to that source in [native backend/package run 39490732759](https://github.com/jmhjr/HomeCircle/actions/runs/39490732759). This is neither a published release nor a version 1.0 or release-candidate designation.

This fixture validates HAOS startup, served frontend and prepared restore of the exact package containing the new city-lookup cancellation, passive-zone normalization, frontend and notice bytes. It does not independently exercise those specific backend regressions: city lookup remains disabled in this account-free fixture. Those behaviors retain their separate backend tests; the full backend suite and native worker qualification are not repeated here. Manifest requirements, guard implementation, Core image, declared dependencies and loading sequence remain unchanged. There is no `skip-pip`, loader patch or network-response stub.

## Separate historical evidence

The completed [prepared-dependency run 39492348166](https://github.com/jmhjr/HomeCircle/actions/runs/39492348166) used source `c367ee6ccb3224e1b47bcea96611be188cd24ff3` for the harness and the older published 112-member beta-20 package. Its six phases established operational continuity and a successful separately retained newest-guard repair. They also observed the automatic restored guard falling from three/blocked to two/unblocked. The controller correctly returned `confirmed_safety_issue`, exit 1; the diagnostic gate recognized completion while keeping safety acceptance and stable-release approval false. Its receipt and fixture remain unchanged historical evidence. They do not qualify this new 113-member preview.

The first unprepared attempt remains distinct:

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

Run all standalone contracts with `python3 -B -m unittest discover -s native-release1-haos -p 'test_*.py'` from the fixture's parent folder. They execute standard-library controller/preparer/gate and ZIP-provenance checks, with no Core/native imports on the Mac. The new candidate's actual Linux run is still required before claiming its prepared operational restore. No CI run, release publication or tag is created by preparing this folder.

A reviewed Linux runner supplies `--candidate-zip native-release1-haos/payload/homecircle.zip`, its exact 40-character QA `--branch-commit` and a fresh `--output` path to `native-release1-haos/run_host.sh`. The branch remains the existing `codex/native-amd64-validation` validation branch. The gate requires exact candidate source/ZIP/member count, the unchanged beta-20 version and explicit unpublished-preview provenance in addition to the six-phase outcome contracts. Only the diagnostic gate's own completion status can be green when the known rollback remains; its safety result stays false.

Primary contracts: [Core bootstrap](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/bootstrap.py), [Core requirements](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/requirements.py), [Core package helper](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/util/package.py), [Supervisor restore payload](https://github.com/home-assistant/supervisor/blob/2026.10.2/supervisor/backups/backup.py), [Supervisor archive module](https://github.com/home-assistant/supervisor/blob/2026.10.2/supervisor/homeassistant/module.py), [Recorder](https://github.com/home-assistant/core/tree/2026.10.2/homeassistant/components/recorder) and [QMP `set_link`](https://www.qemu.org/docs/master/interop/qemu-qmp-ref.html#command-set_link).
