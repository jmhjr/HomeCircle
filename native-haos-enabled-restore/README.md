# Native HAOS enabled-entry restore investigation

This disposable Linux x86_64/KVM experiment uses HAOS 18.3 and observed Core/Supervisor 2026.10.2. It extends the earlier disabled-entry backup experiment by retaining a genuinely **enabled** HomeCircle entry in a real Supervisor partial Home Assistant backup, including the actual Recorder database. Supervisor performs its supported restore and normal automatic Core startup without a helper disable/enable barrier.

The tested product is the exact published `v0.1.0-beta.20` source `d02a9bdb9027cb51c99165a09ba50d5b175f5fb9`, 112-file ZIP SHA-256 `fc0b365d9688459504f874af5c38393e24145d657f15f1def8ada9184f363285`. The helper and controller are separate QA files. They do not alter the integration, its manifest, Core's image, declared dependency ordering, guard implementation, provider responses or published assets.

## What constitutes a result

The experiment measures three separate results:

- `operational_restore_passed`: enabled-entry normal startup restores settings, explicit selections, Person/entity/dashboard/frontend identities, exact pre-backup committed history and a usable current frontend. Post-backup-only history must disappear, then new post-restore history must persist across repair and another genuine Core restart.
- `automatic_guard_antirollback_passed`: the first available helper observation of the restored process and later normal loaded-state observation retain the latest local count three/blocked state rather than decrease to backed-up count two. These observations use the actual product guard API and unchanged byte fingerprints; calling that API can import candidate modules. The first observation is at helper `async_setup`; it does **not** claim to precede HomeCircle import/setup or observe every startup event.
- `manual_newest_guard_repair_passed`: only after the automatic startup and operational result have been captured, stop Core, verify the observed older guard, copy the independently retained newest guard back, then prove blocked count three and continuity after two real starts.

If the restored guard falls from three to two, normal restoration can pass operationally while recovery rollback protection fails. The controller completes the separate manual repair rehearsal and emits **`outcome=confirmed_safety_issue` with exit status 1**, `ordinary_enabled_restore_safety_accepted=false` and an explicit issue label. A successful experiment is not a claim that ordinary self-contained restore is safe. Unexpected errors or failed cleanup emit `failed_or_incomplete`, also exit 1. Exit 0 is reserved for all acceptance conditions, including automatic protection. The workflow may acknowledge an exact completed diagnostic finding while keeping the product safety result false.

## Six bounded phases

1. `initialize`: actual HomeCircle config/options flows create two fictional Persons with explicitly selected registered trackers; city lookup is disabled and no provider account or prototype/migration entry exists. Preserve unrelated/frontend/dashboard identities, record and commit real history, and seed exactly two local fictional refusals through the actual recovery guard API.
2. `prebackup`: keep the entry enabled and loaded, wait for its nonempty options, Person/registry/dashboard/frontend storage to reach disk and verify unchanged identities. Create exactly one genuine live Supervisor partial backup with database exclusion explicitly false. Verify its actual uncompressed archive contains the exact candidate, an enabled entry, SQLite database and guard ledger count two with no pending/uncertain/verified attempts.
3. `mutate`: change an option through the real flow, record committed post-backup-only history, and add exactly one local fictional refusal so the newest guard is count three/blocked. Preserve its exact files and private history-window proof **outside `/config`**. No passcode or proof is sent.
4. Close the owned VM's sole external NIC through QMP, then perform exactly one supported Supervisor restore. QGA and local Docker/CLI remain available. The restored helper records the earliest available actual guard status, and the controller rotates QA instructions atomically with a fresh token/generation. `restored` verifies the normal enabled/loaded state, rollback evidence, identities, exact historical rows and new committed history. No guard repair occurs before these observations.
5. `repair`: stop Core and independently verify guard bytes match the observed restore. Only then copy the separately retained newest guard, start Core through the supported API, and verify status three/blocked plus unchanged identities and exact history.
6. `restart`: a second real managed stop/start verifies persistence and the retained count three. Recheck the external link remains closed, then stop and destroy the owned VM and all private runner state.

## Network and account limits

Initial official image/dependency installation and account-free setup use the VM's normal outbound NAT. Before restore, a bounded TCP connection to fixed non-provider address `1.1.1.1:443` must succeed as a positive control. The controller then issues one QMP `set_link` on the explicitly named sole NIC `qa-net0`; subsequent identical probes must fail while private QGA stays responsive. The VM link remains closed through automatic startup, observation, repair and restart. This external boundary survives Core container replacement and covers both IPv4 and IPv6 traffic through that NIC. There are no forwarded ports, host mounts, SSH or connections to an existing Home Assistant.

This qualifies a **cached-image, account-free, offline partial restore** only. Supervisor's own internet access is also interrupted; if that prevents its restore job, the attempt is retained as failed/incomplete. The harness does not bypass a Supervisor health condition or retry a mutating request. It does not test authenticated provider startup/report polling, Apple recovery, encrypted/cloud backups, full-system/apps restoration, physical devices or production histories.

No provider account, owner credential, recovery proof, GitHub token or private location is placed in the guest. The actual seed calls reserve and refuse a fictional local guard attempt; they contain no passcode/proof and do not invoke a provider method. The harness does **not** instrument every attempted HTTP/provider/recovery call, and receipt fields explicitly mark attempted-request counts **unmeasured**. Closed egress establishes that no external request can succeed during restore; account-free state and unchanged guard bytes are separate evidence, not a claimed measured zero-attempt count.

## Bounds, privacy and contracts

The existing native VM ownership, private socket, pinned HAOS image, exact returned backup job-tree, one-shot mutation and cleanup controls are preserved. Actual KVM must be confirmed. Core actions share a 180-second request/state envelope; backup/restore have 900/1200-second envelopes. Each fixture phase has 600 seconds plus 60 seconds receipt allowance. Total controller bound is 5520 seconds plus reserved cleanup time. The launcher owns the outer timeout. Unexpected failures never become an accepted diagnostic.

Public JSON contains only fixed labels, versions, hashes, counts and booleans. Raw archives, Recorder databases, entity IDs, history timestamps, account values, tokens, raw logs/HTTP responses and backup slugs remain private and are destroyed. Restored stale QA instructions cannot count as progress: receipt token, generation, phase and controller commit must match. Live replacement of generation inputs uses a staged file and atomic rename.

Run standalone controller contracts with `python3 -B -m unittest discover -s native-haos-enabled-restore -p test_controller.py`. They import only standard-library controller code, not Core, the fixture or Unicorn. The helper is syntax-checked separately without executing it. Offline contracts establish harness behavior; only real sanitized Linux receipts qualify the restore result.

## Primary contracts

- [Supervisor 2026.10.2 backup API](https://github.com/home-assistant/supervisor/blob/2026.10.2/supervisor/api/backups.py), [backup payload](https://github.com/home-assistant/supervisor/blob/2026.10.2/supervisor/backups/backup.py) and [manager](https://github.com/home-assistant/supervisor/blob/2026.10.2/supervisor/backups/manager.py): partial restore removes the old Core container and starts Core in its final stage.
- [Core 2026.10.2 Recorder](https://github.com/home-assistant/core/tree/2026.10.2/homeassistant/components/recorder): supported history reads, committed event queue, backup hooks and SQLite integrity checks.
- [QEMU QMP `set_link`](https://www.qemu.org/docs/master/interop/qemu-qmp-ref.html#command-set_link): named virtual NIC link status. A successful command alone is insufficient, so the harness also requires the real connectivity negative control.

Prepared source and contracts are not execution evidence. Publish an exact run/commit receipt and remaining safety disposition after native execution.
