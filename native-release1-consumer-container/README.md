# Original consumer entrypoint witness — prepared for review

Prepared only. No Docker resources, Core service, CI job or remote state were created by this preparation. `PREPARED.json` freezes all five runtime controls and four explicit target pin files. The initial pilot is **current-amd64**. The other three targets are prepared parameters; no target runs automatically.

The runtime uses the documented generic `ghcr.io/home-assistant/home-assistant` image by immutable digest/config identity. Static parent-folder receipts prove its complete filesystem layers and operational config except labels match the corresponding previously qualified machine image. The current/minimum 48 focused passes and 16 scripted Core processes are reused. This witness runs no test suite, native Apple worker or provider account.

## Files and trust

- `package_support.py` is byte-identical reviewed support, SHA-256 `e97e3f71fc9f7ceb9391f86e0178c59c3b88a2fafe5f397e25a9fb69fe568e59`. It checks the immutable public source/config/archive. No support code is patched.
- `payload/` is the unchanged five-file source/package input set from the verified package run: canonical `9bf03eb45d2cf43274074534e9dfe2de841f4011`, 337 public files; c453 development ZIP, 113 files; exact source/package inventories. The ZIP still reports `0.1.0-beta.20` and is not a release.
- Every target pins the generic image index, selected manifest/config, Core/Python/constraints, the prior endpoint's 24-package runtime closure and 21 startup versions, five Core startup source hashes, three final startup scripts and three architecture-specific s6 binary hashes.
- `common.py` handles bounded inputs, exact installed files, fixed failure projection and receipts. `driver.py` handles preparation and private phase control. `guest.py` is a finite temporary HA integration outside HomeCircle's 113 files. `process_probe.py` independently checks the actual process tree. `run_host.sh` owns Docker lifecycle and cleanup. Their exact bytes are bound by each reviewed target pin hash.
- `test_controls.py` contains standalone contracts only. The parent `prepare-inputs.py` generator and static inspection scripts are local preparation utilities, not acceptance service launchers.

## Finite phases

The launcher first verifies canonical Git source on native Linux with a local Unix-socket Docker daemon. It pulls/verifies the generic image and creates one uniquely labeled local named volume. An owned preparer mounts only that volume at `/config`, installs the frozen requirements under the interpreter-calculated normal `/config/deps` user site with active constraints, stages the exact ZIP and synthetic YAML/helper and verifies all hashes. Its bridge network is disconnected before acceptance. It remains only as a bounded offline volume-control sidecar so private phase files can be changed while the consumer is stopped.

The consumer uses the original image, `/init`, no CMD arguments, original environment/user/workdir, writable root and ordinary finite nonprivileged Docker capabilities. It gets no `--init`, replacement launcher, import path injection, host mount, host networking, published port, device, privileged flag or automatic restart policy. Both containers have exactly one verified owned named-volume mount. Consumer networking is `none`; the sidecar has no attached network during acceptance. Both capabilities are checked against the finite default Docker mask.

Two starts of that same consumer are the entire acceptance:

1. **first** — real s6/CLI startup; two fictional explicitly configured People/tracker sources; real HomeCircle flow and nonempty city-disabled options; actual loaded origins and all 113 files; exact card bytes over container loopback; saved entry/settings/source and resource URL/type digests persisted.
2. **restart** — after a clean Docker stop and change of the private phase input while stopped, start the same container/volume again. Verify saved continuity, loaded/served bytes, normal cache origins, then one legitimate entry unload/setup and drained old runtime.

Each start also needs independent `/proc` proof: native pinned s6 PID 1 and supervisor ancestry, exactly one actual Core process with `python3 -P -m homeassistant --config /config`, matching interpreter identity, `PYTHONMALLOC=mimalloc`, no `PYTHONPATH`/`PYTHONHOME` override, finite capabilities and final merged startup hashes. The helper's own receipt cannot substitute for this proof. Docker start timestamps must differ; both stops require exit 0, no OOM and no automatic restart.

The guest performs filesystem/metadata work through HA's executor and drains its own finite task on shutdown. Private phase files and a random per-volume nonce control the helper; no new HTTP control API or synthetic login account is added. The only HTTP probe is the exact card on `127.0.0.1:18123`.

## Limits, cleanup and receipts

Host work is capped at 2,100 seconds, with separately bounded cleanup. Preparation has a 660-second dependency child/720-second outer cap; each guest phase has a 120-second cap, each startup wait 180 seconds and each normal Docker stop 260 seconds. All remain subject to the host aggregate deadline. The s6 image's service grace period is 240 seconds. There is no alternate launcher, global dependency fallback or automatic rerun after failure.

Cleanup rechecks both labels/names/IDs/images, exact mounts and offline identities; it removes only the owned containers, named volume and private host workspace. Successful absence queries are required, including recovery of a create whose CLI response was interrupted. An uncertain owner/daemon response fails cleanup rather than authorizing an unrelated removal. The official image cache is retained; no image build/commit or global Docker prune occurs.

On success `public-summary/` has source and setup summaries, first/restart guest receipts, first/restart process receipts and a host cleanup summary. Failures may additionally retain fixed-schema failure summaries. Raw `/proc`, logs, nonce, phase files, synthetic configuration and cached packages stay in the owned private resources and are removed. Public receipts contain fixed labels, counts and hashes.

This is a **prepared-config-cache original-entrypoint witness**. Core still uses its normal bootstrap and dependency checks; `skip_pip` is not enabled. It does not establish fresh online dependency resolution, host-network discovery, Bluetooth/USB, a user's bind-mounted configuration, provider authentication, native worker acquisition, HACS/RC delivery or managed HAOS behavior. Normal cache availability, original s6 startup/capability behavior and clean CLI termination still require the future native pilot.

## Local checks and future pilot

Fourteen standalone contracts pass on Python 3.13 and 3.14: strict target/constraint/auth/CPU pins; tampering and symlink refusal; exact 113-file checks; real Core command discrimination; phase versus wait control; foreign/stale receipts; settings/source identity; private-canary failure projection; no new Core constructor/import path override; finite launcher volume/start/stop rules; async wait/cancellation/deadline behavior. The parent `LOCAL-PREFLIGHT.json` verifies all four controls/pins, canonical 337 Git blobs, 113 ZIP members/111 direct source comparisons and preservation of all 28 previous published harness files. No local Home Assistant import or Docker execution occurs.

After root and independent review, the initial native amd64 Linux pilot can use the reviewed current-amd64 pin SHA from `PREPARED.json`:

```bash
bash run_host.sh --payload "$PWD/payload" --output /tmp/homecircle-consumer-current-amd64 \
  --pins "$PWD/pins-current-amd64.json" --pins-sha REVIEWED_CURRENT_AMD64_PINS_SHA256 \
  --source-repository /path/to/reviewed/HomeCircle
```

Use a fresh output path. The launcher refuses a mismatched native CPU or preexisting output. Other endpoint/CPU witnesses use their separately reviewed pin file and output path only after the pilot has been assessed. No workflow is included or launched by this preparation.

## Separate diagnostic revision after first pilot

The first automatic pilot, run 39502196796 at QA commit 5869404, failed in preparation before any consumer start; cleanup passed. Its exact inputs and receipts remain in the parent folder. The failure's underlying reason is unconfirmed. This separate revision changes diagnostic projection only: the preparer may export fixed literal failure codes from the exact hash-pinned support file, plus one of eleven fixed setup stages. Unknown exception text, arbitrary stage strings and tampered support catalogs are refused or omitted. The guest has no support file and retains its existing four-control diagnostics. Seventeen standalone contracts include three reproduced pre-fix failures for support codes, stage projection and the actual main error path. No launcher, image, package, dependency command, process acceptance, lifecycle or cleanup behavior is changed. No revision has been executed or published by this preparation.
