# Beta 20 Ubuntu/glibc validation

Date: October 20, 2026. **Passed:** the exact published beta 20 release completed native amd64 Ubuntu 24.04/glibc 2.39 validation with source-built Python 3.14.6 and Core 2026.10.2. [Run 39474571811](https://github.com/jmhjr/HomeCircle/actions/runs/39474571811), at [revision d0fe7aaef635ea915ee70e8b10f612a1f481fae2](https://github.com/jmhjr/HomeCircle/commit/d0fe7aaef635ea915ee70e8b10f612a1f481fae2), passed 48 harness contracts, the actual native worker/provider lifecycle, two real Core startup processes and the backend suite: **1,443 passed, zero failed, one named optional skip**. Host work and cleanup completed in **423.300 seconds**. Downloaded receipts and artifact bytes were independently verified. All four earlier failed attempts are retained separately below.

## Exact published release

The tested release is the existing experimental [v0.1.0-beta.20 prerelease](https://github.com/jmhjr/HomeCircle/releases/tag/v0.1.0-beta.20), release `418643687`, from [source commit d02a9bdb9027cb51c99165a09ba50d5b175f5fb9](https://github.com/jmhjr/HomeCircle/commit/d02a9bdb9027cb51c99165a09ba50d5b175f5fb9). Public release/tag metadata and fresh unauthenticated asset downloads matched these pins:

| Input | Required SHA-256 |
| --- | --- |
| [homecircle.zip](https://github.com/jmhjr/HomeCircle/releases/download/v0.1.0-beta.20/homecircle.zip), asset `659912694`, 604,937 bytes, 112 files | `fc0b365d9688459504f874af5c38393e24145d657f15f1def8ada9184f363285` |
| [inventory.json](https://github.com/jmhjr/HomeCircle/releases/download/v0.1.0-beta.20/inventory.json), asset `659912698`, 16,674 bytes | `5e724f69ff20a711dd87b2a39ed96818781813bb6f1e7b3addedc6e048593d77` |
| Immutable 327-file tagged source archive | `261aeb3219071a44e1c6ca53f2f18e26624ae450a641d29be32450ee265d4818` |
| Tagged source inventory | `be693aef2f7a049cc4c0752179069664c86e444e24cc9fb01393d40f5d1288b1` |

Tagged source supplied unchanged tests and the original validation scripts. Every integration file in the runtime test tree matched the published ZIP, including its compiled frontend and notices. All 112 members and the original source were checked before and after acceptance. Two QA scripts used the explicitly derived execution copies described below; their complete derived bytes were checked, and all tagged test bytes and assertions remained unchanged. No rebuilt integration or earlier frozen parent substituted for the release. Earlier package, publication and genuine HACS evidence retain their separate scope in the [publication validation report](https://github.com/jmhjr/HomeCircle/blob/e0535fa909cd44cdd0f3d9a83189a93a9e2843c7/docs/BETA20-PUBLICATION-VALIDATION.md).

## Fixed runtime and provenance

The tested target was native Linux/amd64 **Ubuntu 24.04**, active **glibc 2.39**, source-built **CPython 3.14.6** and pip-installed **Core 2026.10.2**. It used a disposable container, separate from the earlier Alpine/musl and managed HAOS results.

| Runtime input | Pinned identity |
| --- | --- |
| Official Ubuntu 24.04 amd64 manifest | `sha256:a2d43bffc46670d7108bb3c0468c67c5557c4c92e83e1e34cbff1322ad1b94dc` |
| Ubuntu image configuration | `sha256:6277ab668b2ad3c3ab851d370faa1690d324b30db29d342527f61fed28f20f36` |
| [Official CPython 3.14.6 source tarball](https://www.python.org/ftp/python/3.14.6/Python-3.14.6.tar.xz) | `143b1dddefaec3bd2e21e3b839b34a2b7fb9842272883c576420d605e9f30c63` |
| [Core 2026.10.2 constraints](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/package_constraints.txt) | `7baa9a8f39ddeb9c5bb60a1036f6d5e33f4b84267f151f53cc2b95ef031a21b5` |
| Test dependency | `pytest-homeassistant-custom-component==0.13.373`, targeting Core 2026.10.2 |

CPython was compiled inside Linux with shared-library support and ensurepip. Online setup installed exact Core, the published manifest dependencies and declared Core startup requirements under the pinned constraints. Package consistency and the 24-package active manifest dependency closure passed. The source-derived startup preparation covered 111 requirement domains, 22 bootstrap preimport modules and 21 installed requirements, including default authentication/TOTP requirements. Five Core source fingerprints matched the official tag. Preparation and installed versions were checked again before and after acceptance and in both startup children. Requirement preparation did not activate additional integrations. Networking was disconnected and checked before acceptance; the test container had no host mounts, published ports or Linux capabilities.

The active libc's `gnu_get_libc_version()` reported 2.39 and its loaded process mapping passed verification. The actual libc, Python executable and imported Unicorn native library were fingerprinted as x86_64 ELF files, with no musl runtime. The native-worker and lifecycle probes used the same Python executable and real Unicorn 2.1.4 library, including the copied parent-only dependency path. These checks verified the active runtime beyond its Ubuntu branding.

| Observed provenance | Actual receipt value |
| --- | --- |
| Fifth-attempt run and workflow revision | `39474571811` / `d0fe7aaef635ea915ee70e8b10f612a1f481fae2`; completed successfully |
| Host kernel and native architecture | Linux `6.17.0-1022-azure`, `x86_64` |
| Source-built runtime image ID, distinct from base manifest | `sha256:818440837ffc75b3fd0da27291f60e59a98a6bfa153ac04d244e4c105c31940d` |
| Active Python ELF fingerprint | 17,680 bytes; `f10462f524c173b2e4a9da57e64183e4cf51a3c3d9dad115458ce56349df40e0` |
| Mapped libc ELF fingerprint and active version | glibc 2.39; 2,129,424 bytes; `3a15d66867d83762c7f2f1e37359cb8f6c5743edb369c65285cb0b1c4f7498bf` |
| Imported Unicorn ELF fingerprint | Unicorn 2.1.4; 24,507,432 bytes; `ddb196ec82b52e502c18e4a34478bf7b9f61c83c2ebaa95c74d8ded45a95da9c` |
| Setup closure, constraints and immutable-input comparison | Passed: 24-package manifest closure, 21 startup requirement versions, exact constraints/source/release pins |
| Lifecycle approved actual `posix_spawn` events / denied unknown spawn events | `2` / `0` |
| Backend QA full-guard probe: actual approved event / denied unknown events | `1` / `0` |

## Acceptance results

| Check | Verified evidence | Actual result |
| --- | --- | --- |
| Harness contracts | 48 Linux-only safety contracts, including wrong inputs/architecture/libc, strict receipts, approved skip, exact tagged helper dependency closure, both narrow spawn audit policies, one-use permits/eight-child ceiling and sanitized failures | Passed in 1.221 seconds |
| Dependency/import/native worker | Mandatory manifest imports; synthetic dispatcher through the actual packaged worker; production binary-hash refusal; no Apple binary/account; worker reaping | Passed |
| Provider lifecycle | Actual open/check/close, parent-only native dependency resolution, production pipes/spawn and active native-loop cancellation; two observed approved `posix_spawn` events and zero denied unknown events | Passed |
| Child limits and cleanup | CPU 90 seconds, core dumps disabled, address space 3 GiB; both lifecycle worker processes absent after cleanup | Passed; two workers reaped |
| Real Core startup and restart | Two separate Core processes using the unchanged tagged startup validator and exact published integration; explicit synthetic People/trackers and real config/options flow; loaded version `0.1.0-beta.20`, reload/unload/setup, saved options/activity and exact served frontend bytes | `create` and `restart` passed |
| Backend QA spawn proof | Exact full adapted guard with a natural asyncio marker-worker launch; one actual approved `posix_spawn`, zero denied unknown events, exact stdout, stderr redirected to DEVNULL, worker reaped and private fixture removed | Passed |
| Offline backend suite | Exactly one named optional skip: `tests.test_findmy_runtime_bootstrap::test_retained_public_apple_dmg_fixed_ranges` | 1,443 passed, zero failed, one skipped |
| Final integrity and owned cleanup | Same source/release/runtime/dependency fingerprints; container stopped/removed, private workspace and owned runtime image removed without cleanup failure | Passed |

The lifecycle validator historically pins the frozen parent archive and refuses all `os.posix_spawn` events. Its temporary execution copy had **exactly two declared semantic adaptations**: one archive-hash literal changed to the published beta 20 hash, and one audit block permitted `os.posix_spawn` only when the executable was the tested Python and the complete argument tuple matched an already approved worker launch. Other spawn/system/exec commands and all socket/file restrictions retained their refusals. The original script SHA-256 was `11da124b436f30337cd4ea6b4b9b49b6b0dd4aba7dd3402d23d6df73d5ddcf6d`; the executed copy was `7ced22241aa93016bbce4627e10bd0b74ca57ca914558fe6b77df9fc10733eb6`. Both substitution counts were exactly one. Tagged source and integration bytes remained unchanged. The test did not force a fork backend, add a working-directory override or alter production launch arguments. The two actual approved events and all existing worker/limits/IPC/cancellation/reaping checks passed.

The separate backend QA helper, `scripts/validate_findmy_runtime.py`, had **exactly one audit-block adaptation**. It permitted a spawn only for the tested Python and exact packaged-worker argument tuple, in explicit `acquire` or `provision` mode, with the existing eight-child budget. Each approved `Popen` supplied one pending permit, consumed once by the matching `posix_spawn`; wrong executable/arguments, a working-directory override, direct or repeated low-level spawns, readiness-mode launches and excess children remained refused. All other process, socket and file rules retained their refusals, and the public validator receipt schema was unchanged. The original 327-file tree remained immutable; runtime-tree checks compared this helper's full explicitly derived bytes instead of exempting it.

| Backend QA derivation | Verified SHA-256 / count |
| --- | --- |
| Original tagged helper | `b8c0d729517a6129c6fb53cc5076276267851dc68cc056196a80067f778b47d2` |
| Derived execution helper | `5c6569e757742853551c925d61d9c2fb710782cfa0a79be59ffa2f479079f030` |
| Entire adapted guard extracted for the focused probe | `f02d5f92b8549b04c02e831212f7ad01ba16691d9030bf4536e8e72f6907368e` |
| Exact audit-block substitutions | `1` |

The focused probe extracted and installed that entire adapted guard, then exercised the natural glibc asyncio launch without selecting a subprocess backend or changing its working directory. Its separate bounded receipt proved one actual approved event, exact worker output, DEVNULL stderr, worker reaping and private fixture removal. The unchanged full backend tests also passed separately. The derivation and actual-event receipts are `backend_qa_validator_adaptation` and `backend_qa_spawn_proof`.

The runtime build is bounded to 1,500 seconds. Each driver mode has a 1,500-second envelope; native, lifecycle, backend and two Core startup children have their own bounds. The additional focused backend QA proof has a 30-second child deadline. The host's 4,200-second work deadline caps remaining work, followed by at most 150 seconds for cleanup. The workflow has an additional outer timeout. These are limits, not measured run durations.

| Completion evidence | Actual receipt value |
| --- | --- |
| Overall result and host elapsed seconds | Passed; host/acceptance exit `0`; `423.300` seconds |
| Runtime build completion/stage | Source compilation and runtime import checks passed; build exit `0`, final build stage `import` |
| Container/network/image/private-workspace cleanup | Offline acceptance confirmed; container stopped/removed, owned image and private workspace removed; `cleanup_failed:false` |
| Sanitized artifact ID, exact members and ZIP bytes | [Artifact 12289960150](https://github.com/jmhjr/HomeCircle/actions/runs/39474571811/artifacts/12289960150); 7,824 bytes; exactly `host.json`, `setup-summary.json`, `glibc-summary.json` |
| Artifact ZIP SHA-256, metadata/log match and independent member verification | `e6999c4941839d4b133d20d8b804eb5620ab461d428674f7165ea15d645acad8`; API/upload-log digest, raw ZIP CRC and each extracted member's bytes verified |

Only the three narrow synthetic JSON summaries were uploaded. Raw configuration, Core/test logs, XML, temporary startup state and dependency-install output remained private and were removed with owned test state. No owner credentials, provider account, Apple binary or GitHub credential entered the runtime container. Python build and test execution ran inside Linux; no Mac Python was launched. Production, V2, the working source checkout, main and the published tag/assets were preserved.

## Retained failed attempts

### First attempt

[Run 39466038742](https://github.com/jmhjr/HomeCircle/actions/runs/39466038742), at [revision 70021d214fe5327439f35259bc2939c54bfd78d1](https://github.com/jmhjr/HomeCircle/commit/70021d214fe5327439f35259bc2939c54bfd78d1), **failed after 292.420 host seconds**. CPython source compilation/import checks and constrained setup passed, recording active glibc 2.39, Core 2026.10.2 and the 24-package dependency closure. The actual published-ZIP native-worker check also passed. Offline acceptance then stopped at `lifecycle_child_refused`, 1.998 seconds into that driver mode. **Core startup and the backend suite were not reached.** This partial result does not qualify the complete target.

The owned container stopped and was removed; the private workspace and owned runtime image were removed, with no cleanup failure. Sanitized artifact `12285047755` contains exactly four JSON members: `host.json`, `setup-summary.json`, `glibc-summary.json` and `failure-summary.json`. Its 4,230-byte ZIP matched SHA-256 `c087a0f3ef63404994b4276fe9af9587f1b848ce7956aa602e0e7fa6de0490b2`.

Independent source review confirmed a harness defect: the temporary lifecycle-script directory omitted the unchanged `validate_ha_restart.py` helper, although its copied archive validator imports that helper. The second attempt copied that exact tagged file too. Four focused contracts covering the real tagged local-import closure and finite failure projections raised the total from 19 to 23. The first child's stderr was not retained, so this confirmed defect is **not assigned as the sole observed runtime cause**. The first attempt's 19 then-existing contracts passed in 0.017 seconds.

### Second attempt

[Run 39467519131](https://github.com/jmhjr/HomeCircle/actions/runs/39467519131), at [revision 93de112338ab36a8cfc72042de3655493fdb15e3](https://github.com/jmhjr/HomeCircle/commit/93de112338ab36a8cfc72042de3655493fdb15e3), **failed after 311.430 host seconds**. Its 23 contracts passed in 0.080 seconds. Source-built runtime/setup and the actual published-ZIP native-worker check passed again. Offline acceptance stopped after 3.557 seconds at `lifecycle_child_refused`; the retained diagnostic identified `normal_open` / `IdentityUnavailable` inside `linux_lifecycle_probe_refused`. **Core startup and the backend suite were not reached.** This remains an incomplete target result.

Container, owned runtime image and private-workspace cleanup all passed. The exact four-member sanitized artifact `12285507431` was 4,348 bytes, SHA-256 `6cf0a60fac2e8743522c45b334aa27e3797a8ea86a33a61e74ee27f82c77c0ee`, containing the same four JSON filenames as the first attempt.

Independent review found a second QA policy conflict. [CPython 3.14.6](https://github.com/python/cpython/blob/v3.14.6/Lib/subprocess.py) can select `posix_spawn` for the lifecycle's expected asyncio launch on glibc, but the original audit rule rejects that event even for the approved worker. The passing generic native probe supplies a working directory, which prevents that fast path. The second run did not retain the actual rejected event, so the policy conflict is **not claimed as its sole observed cause**. The third attempt's narrow audit adaptation and five new guard contracts address this conflict, with actual approved-event counts required for acceptance.

### Third attempt

[Run 39469621154](https://github.com/jmhjr/HomeCircle/actions/runs/39469621154), at [revision 3958bfac107af85e4b7d551cc0ff690bec4fd27b](https://github.com/jmhjr/HomeCircle/commit/3958bfac107af85e4b7d551cc0ff690bec4fd27b), **failed after 366.190 host seconds**. All 28 contracts passed in 0.075 seconds. Source-built runtime/setup, the actual published-ZIP native worker and the complete provider lifecycle passed. The lifecycle recorded **two actual approved `posix_spawn` events and zero denied unknown launches**, along with cancellation, limits and both worker reaps. This provides the previously missing runtime evidence for the narrow audit adaptation.

Acceptance stopped after 55.999 seconds at `core_startup_child_refused`, in the `create` phase. Its retained `AssertionError` points to the unchanged startup validator's call to `bootstrap.async_from_config_dict`, before HomeCircle's setup flow began. **Core startup/restart did not pass and the backend suite was not reached.** Container, owned runtime image and private-workspace cleanup passed; the runtime had no external network. Artifact `12287420586` contains the same exact four JSON members, 4,645 ZIP bytes, SHA-256 `9265e8e839660ed27761c2be2f276f186ff3d2d00726f41aef6c07088f7842e7`.

Source review confirmed a separate setup-closure omission. Core 2026.10.2 enables its default authentication provider and TOTP MFA module during initial bootstrap. The [TOTP module's declared requirements](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/auth/mfa_modules/totp.py) include `pyotp==2.10.0` and `PyQRCode==1.2.1`, outside the component-manifest scan used by the first three attempts. These two requirements were absent from that scan's 18-item setup list. The fourth attempt derives and installs the default authentication requirements during online setup, then verifies their installed versions before disconnecting networking. Review also confirmed that [Core’s requirements manager](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/requirements.py) traverses both hard and after dependencies and adds discovery requirements from manifest keys. The revised preparation graph mirrors those exact declared rules, while preimport-only modules contribute only their own requirements. Preparing wheels does not set up additional integrations. Default authentication/MFA, the startup validator and its success assertion remain unchanged. The third run retained no underlying Core error category, so the confirmed omission is **not assigned as its sole observed cause**. Passive finite Core failure-category diagnostics are added for any subsequent failure; raw messages and private arguments remain excluded.

### Fourth attempt

[Run 39472367678](https://github.com/jmhjr/HomeCircle/actions/runs/39472367678), at [revision 93f623ee34a32dbace353678daf3c4644576268d](https://github.com/jmhjr/HomeCircle/commit/93f623ee34a32dbace353678daf3c4644576268d), **failed after 383.620 host seconds**. All 38 contracts passed in 0.066 seconds. Source-built runtime/setup, native worker and provider lifecycle passed, again recording two approved spawn events and zero denied unknown launches. The complete requirements preparation recorded 111 domains, 21 installed requirements and five Core source fingerprints matching the official tag. Both real Core processes, `create` and `restart`, **passed**, with beta 20 loaded, saved options/activity, reload/unload/setup and exact served frontend bytes; synthetic configuration was removed.

Acceptance stopped after 105.395 seconds at `backend_exit_refused`. The backend suite recorded **1,440 passed, three failed and the one named optional skip**. The public failure labels identify `tests.test_validate_findmy_runtime::test_actual_marker_worker_can_redirect_stderr_to_devnull` and two parameterizations of `test_provider_failure_projects_before_close_without_exception_text`. Full backend acceptance did not pass. Container, owned runtime image and private-workspace cleanup all passed, without external runtime networking. Artifact `12287504421` contains the same four JSON members, 7,677 ZIP bytes, SHA-256 `749ef34242ad2c69c583c2ef8ea1db60e2bbd2ed70b9c0c9933b20b65b77e7cb`.

Independent review confirmed the same glibc policy conflict in a separate QA helper, `scripts/validate_findmy_runtime.py`: its audit guard accepts the exact worker's `subprocess.Popen` event, then refuses every `os.posix_spawn` event. All three failing cases use that helper's synthetic marker-worker launch with no working-directory override. Individual assertion bodies and rejected events were not retained, so the confirmed conflict is **not assigned as the sole observed per-test cause**. The fifth attempt uses an explicitly derived, hash-bound execution copy of this QA helper. Its precise guard adaptation and actual-event proof are recorded separately; tagged originals, all backend tests/assertions and every published integration file remain unchanged. Runtime-tree integrity checks compare the complete derived helper bytes rather than exempting the file. No test is newly skipped or reclassified; the original named optional skip is retained. No fork backend or launch-directory change is forced.

Native/lifecycle failure diagnostics retain only bounded, allowlisted exception/phase/module identifiers and known public script basenames/line numbers before private logs are removed. Raw error text, paths and response bodies remain excluded. Product and tagged source bytes, the published ZIP and every acceptance/cleanup deadline remain unchanged through these QA corrections.

## Scope

This qualifies **one native amd64 Ubuntu 24.04/glibc 2.39/Python 3.14.6/Core 2026.10.2 target** for the exact published beta 20 bytes and recorded synthetic paths. It does not qualify every glibc distribution, ARM64 glibc, every Core version or installation method. It did not repeat managed HAOS, HACS delivery, the full upgrade/recovery matrix or Supervisor backup/Recorder restore; those earlier results retain their dated procedures and limitations.

Owner Apple sign-in/recovery, real provider behavior, movement/latency, long-term field use and physical-display acceptance remain outside this run. It adds no ordinary enabled-entry/full-system/add-on/encrypted/cloud restore or automatic anti-rollback guarantee. External assurance, provenance/licensing/service-use decisions and remaining [stable-release gates](https://github.com/jmhjr/HomeCircle/blob/v0.1.0-beta.20/docs/STABLE-RELEASE-CHECKLIST.md) remain open. Beta 20 remains an experimental prerelease.
