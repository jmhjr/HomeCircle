# Current-Core focused qualification, prepared for review

This folder prepares one native amd64 and one native ARM64 check of the exact development preview on Core 2026.10.2 / Python 3.14.6. No Docker container, Linux Core process, workflow or remote job has been launched by this preparation. `PREPARED.json` records the final driver, launcher, helper and architecture pin hashes. This is preparation evidence, not a runtime pass.

## Exact input and provenance

- Canonical public source: `9bf03eb45d2cf43274074534e9dfe2de841f4011`, 337 files.
- Downloaded run 39490732759 preview: 113-file ZIP, SHA-256 `c4530d94be3b2996f8d6c8948db88a51868566047d68558eefde7967f270a861`; inventory SHA-256 `9bdfba997d5437d354673a98c8b78d3875d459499281bca3e20bc629369dcb6b`.
- `payload/` contains the unchanged source archive/inventory/config and the downloaded ZIP/inventory. The preview still reports `0.1.0-beta.20`; it is not a new published release.
- `package_support.py` is a byte-identical copy of the previously validated native release1 package driver, SHA-256 `e97e3f71fc9f7ceb9391f86e0178c59c3b88a2fafe5f397e25a9fb69fe568e59`. Its minimum-Core metadata assertion remains 2026.9.4; the new driver independently checks the actual 2026.10.2 runtime.
- `requirements_support.py` retains six previously reviewed requirement-graph function bodies from `7482f5e:native-beta20-glibc/driver.py`. `requirements-helper-provenance.json` records the upstream revision, source hash, individual function hashes and generated helper hash. The local header supplies their standard-library imports, including `Path`.
- Lifecycle helper and release inspector are loaded from the exact canonical source, with fixed SHA-256 checks. Product source and the downloaded package are never edited.

## Finite acceptance scope

Online preparation verifies native host/daemon/container architecture, the official image/config identity, Python/Core versions and active Core constraints. It installs the exact declared dependency closure and the bounded test helper requirement. All acceptance then runs after the owned container is disconnected from its bridge network, with no host mounts or published ports.

Acceptance runs 12 focused cases: three passive-zone/GPS normalization cases; eight city-save, cancellation and raw-diagnostic cases; and one exact-license privacy guard case. The XML result must contain every expected case exactly once, with no skips, errors or failures. The complete backend suite is not repeated.

Four fresh real Core processes then execute the unchanged canonical lifecycle checks:

1. **create** — create and load a synthetic integration, check the ZIP-installed module paths and bytes, served card bytes, settings and source choices; exercise canonical reload/unload/setup checks.
2. **restart** — load the saved entry in a new process, repeat the canonical checks and compare saved identity, version, data/options, settings/source selections and semantic resource catalog with create.
3. **remove** — load and check the saved entry in a new process, then remove it through the canonical helper.
4. **removed** — delete only the owned integration code and start a final process; the canonical release inspector checks the removed entry, absent frontend URL and retained unrelated resource.

The installed runtime contains the exact 113 ZIP files. The canonical 337 source bytes are checked before and after acceptance. Each process uses a fresh runner instance against the same owned synthetic configuration. An exclusive nonblocking lifecycle lock prevents concurrent access. Resource URL/type continuity is checked; resource ID persistence is not claimed because the deliberate unload/setup checks can recreate an owned resource.

## Boundaries and receipts

`run_host.sh` requires Linux, an exact native CPU match, a local Unix-socket Docker context, GNU timeout and a fresh output directory. It owns a uniquely named/labeled container, verifies that identity before cleanup, uses no credentials or owner configuration, limits the container to two CPUs / 4 GiB / 512 PIDs and drops capabilities. Each child has a fixed deadline; the host work has a 2,100-second aggregate deadline, followed by bounded cleanup. Preparation is capped at 720 seconds, acceptance at 720 seconds; individual lifecycle processes at 120 seconds and focused tests at 180 seconds. These are stage caps within the aggregate bound, not additive runtime promises.

Raw Core/test logs, temporary configuration and intermediate files stay in the private workspace. Only structured allowlisted source/setup/lifecycle/failure/host receipts are collected. Helper refusal reasons retain only fixed codes declared in verified source. A focused failure retains only its exact predefined selector, with parameter strings, XML bodies, arbitrary exception text and storage canaries excluded. Cleanup stops and removes only the verified owned container and removes the private workspace. Passing requires successful acceptance, offline acceptance, verified source and successful cleanup.

This checks scripted real Core process lifecycle in an official QA container. It does not claim standard consumer Container entrypoint behavior, managed HAOS service behavior, HACS delivery, another upgrade/recovery rehearsal, native Apple worker execution, provider/account acceptance, mobile or physical-display acceptance, or a final RC artifact. Those remain separate scoped evidence in `../COMPATIBILITY-DISPOSITION.md` and the release plan.

## Local preparation checks

`standalone-contracts.txt` records the standalone contracts. They cover strict pins, architecture mapping, exact installed files, focused test accounting, bounded ownership/offline launcher rules, safe failure projection, and a synthetic Core tree that executes the actual requirement-graph helper. `local-preflight.json` records successful 337-file canonical Git verification for both architecture configs and exact 113-file package inspection. These checks import no real Home Assistant, execute no native provider code and use no Docker.

## Future native Linux invocation

After independent review, use the architecture's SHA-256 value from `PREPARED.json` as the out-of-band `--pins-sha`; do not derive trust from an unreviewed replacement pin file. Run from this folder on the matching native Linux host, with a Git repository containing the exact canonical commit:

```bash
bash run_host.sh --payload "$PWD/payload" --output /tmp/homecircle-current-amd64 \
  --pins "$PWD/pins-amd64.json" --pins-sha REVIEWED_AMD64_PINS_SHA256 \
  --source-repository /path/to/reviewed/HomeCircle
```

For native ARM64 use `pins-arm64.json`, its independently reviewed SHA-256 and a fresh `/tmp/homecircle-current-arm64` output directory. Architecture mismatch refuses the run; no emulation fallback exists. The same driver and payload serve both cells. Public receipts are written to the output directory's `public-summary/`. No workflow is created here.
