# Beta 20 publication validation

Date: October 20, 2026. Published experimental prerelease for test Home Assistant instances. Native package validation, public asset verification and the actual disposable HACS upgrade, rollback and re-upgrade passed. No production rollout or stable-release approval is implied.

## Published source and assets

[v0.1.0-beta.20](https://github.com/jmhjr/HomeCircle/releases/tag/v0.1.0-beta.20) was published at 16:52:04 UTC as GitHub prerelease `418643687`. The tag points to [release commit d02a9bdb9027cb51c99165a09ba50d5b175f5fb9](https://github.com/jmhjr/HomeCircle/commit/d02a9bdb9027cb51c99165a09ba50d5b175f5fb9) on the separate release branch. All 327 public source blobs and modes match the prepared commit and its byte-verified inventory. Main, the working checkout, production and the frozen parent candidate were preserved.

| Public release asset | Asset ID | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| [homecircle.zip](https://github.com/jmhjr/HomeCircle/releases/download/v0.1.0-beta.20/homecircle.zip) | 659912694 | 604,937 | `fc0b365d9688459504f874af5c38393e24145d657f15f1def8ada9184f363285` |
| [inventory.json](https://github.com/jmhjr/HomeCircle/releases/download/v0.1.0-beta.20/inventory.json) | 659912698 | 16,674 | `5e724f69ff20a711dd87b2a39ed96818781813bb6f1e7b3addedc6e048593d77` |

Unauthenticated public downloads matched the reviewed assets byte for byte. ZIP local/central metadata, CRCs, member bytes and the complete inventory were independently checked. This proves publication and asset integrity; HACS installation requires separate acceptance.

The ZIP contains 112 integration files. Compared with the **unreleased 112-file parent** `f0477a91e78181fe1f8d80ada176a1739e10a7502abe7ee6ee2240571280d1f5`, exactly three members contain a single `0.1.0-beta.19` → `0.1.0-beta.20` substitution: `manifest.json`, `frontend.py` and `frontend/homecircle-card.js`. The other 109 members are identical. The compiled card embeds the manifest version. The **published beta 19 baseline is a different, earlier 109-file package**; it is not the frozen parent. See the [versioned validation boundary](https://github.com/jmhjr/HomeCircle/blob/v0.1.0-beta.20/docs/BETA20-VALIDATION.md).

## Native Linux package validation

[Run 39460044306](https://github.com/jmhjr/HomeCircle/actions/runs/39460044306) at [workflow revision 179f5fc7ac216106435c66ca431c7868d69f238c](https://github.com/jmhjr/HomeCircle/commit/179f5fc7ac216106435c66ca431c7868d69f238c) passed in **251.290 host seconds**:

- **110 frontend tests** passed. The rebuilt card matched the exact version-label substitution; Leaflet bytes were unchanged.
- **1,443 backend tests** passed on native x86_64 Core **2026.9.4** / Python **3.14.6** in the pinned Alpine/musl container. Only `tests.test_findmy_runtime_bootstrap::test_retained_public_apple_dmg_fixed_ranges`, the named optional retained-installer fixture, was skipped.
- The unchanged privacy checker examined **327 public files** with zero flagged patterns. Core constraints and the **24-package** installed dependency closure matched.
- The unchanged release builder and archive inspector produced and accepted the deterministic 112-file ZIP, with the three exact version changes above. Independent rebuilds matched.
- Backend acceptance ran with container networking disconnected. The owned container stopped and was removed; the private workspace was removed without cleanup failure.

Both downloaded CI artifact ZIPs matched their recorded digests and every extracted member. The four-summary artifact was 3,500 bytes, SHA-256 `5c91cb2d140cbb6ef79dd9e45a07586882f9b4c2ab592b2ffff451d1dab99a68`; the reviewed-release-assets artifact was 583,899 bytes, SHA-256 `4cb63bebed452c11b8ef6d2adeb5c1219fd8b73f95cd3ce1e7d008395a1785df`. Artifact uploads contained no raw configuration or test logs. This package run did not repeat all earlier upgrade/recovery scenarios or establish HACS delivery.

Two earlier setup failures remain part of the record:

| Run | Actual outcome and correction |
| --- | --- |
| [39458391500](https://github.com/jmhjr/HomeCircle/actions/runs/39458391500) | Failed after 0.510 seconds: npm rejected the same empty file as both user and global configuration. No container, backend result or release asset was produced. Two distinct private empty files corrected that harness defect. |
| [39458899622](https://github.com/jmhjr/HomeCircle/actions/runs/39458899622) | Frontend and privacy checks passed, then container input validation raised `PermissionError`; no backend result or release asset was produced. The exact failing path/UID was not retained, so no sole cause is assigned. Reviewed staging now streams bytes into container-owned files and checks ownership, readability and hashes before Python; safe failure diagnostics were also added. |

Both failed runs cleaned up their owned state. Candidate/source bytes, container isolation and acceptance deadlines were preserved through the corrections. No Mac Python was executed.

## Genuine HACS release delivery passed

[Run 39461573392](https://github.com/jmhjr/HomeCircle/actions/runs/39461573392) at [workflow revision 479c3627b9808ed212a1f3c1fe1a8dec0098fb81](https://github.com/jmhjr/HomeCircle/commit/479c3627b9808ed212a1f3c1fe1a8dec0098fb81) passed **all eight phases in 288.778 host seconds**, including preparation and cleanup. Its **45 controller contracts** also passed in 0.019 seconds. The earlier [contract-only run 39460449773](https://github.com/jmhjr/HomeCircle/actions/runs/39460449773) had separately passed the same 45 contracts; the subsequent eight-phase result establishes runtime delivery.

The fresh native x86_64/KVM guest ran official **HAOS 18.3**, managed **Core 2026.10.2**, observed **Supervisor 2026.10.2**, **CLI 2026.09.0** and unmodified official **HACS 2.0.5**. Actual KVM was confirmed. The owned guest used no host configuration mounts or forwarded host ports.

HACS genuinely downloaded published beta 19, upgraded to the published beta 20 ZIP, downloaded beta 19 for rollback, and downloaded beta 20 again for re-upgrade. **Direct candidate installs were zero.** No controller copy of the candidate ZIP, HACS source patch or catalog/default-branch adapter supplied the integration.

All phases passed with HACS enabled, zero pending tasks and installed-version metadata matching disk. The receipts distinguish replacement files from the code loaded in the existing process:

| Accepted phase | On-disk version | Loaded frontend version | Files | Process start ticks |
| --- | --- | --- | ---: | ---: |
| `bootstrap_hacs` | `0.1.0-beta.19` | Not loaded | 109 | 11924 |
| `baseline` | `0.1.0-beta.19` | `0.1.0-beta.19` | 109 | 14472 |
| `upgrade_download` | `0.1.0-beta.20` | `0.1.0-beta.19` | 112 | 17665 |
| `upgraded` | `0.1.0-beta.20` | `0.1.0-beta.20` | 112 | 19793 |
| `rollback_download` | `0.1.0-beta.19` | `0.1.0-beta.20` | 109 | 19793 |
| `rollback` | `0.1.0-beta.19` | `0.1.0-beta.19` | 109 | 22309 |
| `reupgrade_download` | `0.1.0-beta.20` | `0.1.0-beta.19` | 112 | 22309 |
| `final` | `0.1.0-beta.20` | `0.1.0-beta.20` | 112 | 24563 |

Upgrade, rollback and re-upgrade download phases retained the previous cached `frontend.VERSION`; later activation phases ran after real Core restarts and loaded the intended release. Start ticks distinguish new Core processes even when a PID is reused. The initializer's hash is identical across releases, so that hash alone does not prove activation.

Both baseline HACS downloads matched the canonical 109-file beta 19 ZIP `5f20d536e1b5378bef7f0b972bbfbc7ced911063aea16a0a8f56d2ffa1210cd2`. Every beta 20 disk phase matched all 112 members of `fc0b365d9688459504f874af5c38393e24145d657f15f1def8ada9184f363285`. Release proofs in **`upgrade_download`, `upgraded`, `reupgrade_download` and `final`** matched the genuine prerelease/tag, source commit, release ID `418643687`, asset ID `659912694`, size/digest and normal `zip_release:true` / `homecircle.zip` metadata. Supported HACS prerelease selection resolved the intended tag.

Two persistent synthetic People and two explicitly selected trackers, nonempty options/reload, entry data, registry identities, dashboard and owned/unrelated resource identities retained one snapshot across all seven persistent phases:

`adae813dc16364770b01e5c78d871e02e46bfbc40483d2a0578423c5f37aceae`

The baseline saved-store check passed. Baseline, upgraded, rollback and final activation checks served the exact corresponding card bytes and versioned resource URL. HTTP checks before each download described the existing active release, separately from disk checks after download. This is served-byte proof, not browser or physical-display acceptance.

Three local synthetic refusals seeded the recovery safeguard without a passcode proof or provider request. The matching stopped baseline storage/image restore separately retained the newest guard. Its hash remained:

`6a539827f2c55dc92c6221bc2edee2ad3e18ada0a2bccf607f2f502b9c309106`

The actual beta 20 guard API was checked in **`upgraded` and `final`**, reporting blocked with three unresolved and three rejected attempts. **`rollback_download`, `rollback` and `reupgrade_download` checked retained bytes only**; those legs do not add an API-status proof. The final beta 20 API check confirmed the same blocked safeguard after reinstallation and restart. Manual retention is an explicit procedure, not automatic rollback detection.

The owned QEMU process stopped, the private workspace was removed and no cleanup failure occurred. Private guest configuration, the ephemeral read-only token, disks, snapshots and logs were removed. No owner credentials, provider accounts or production configuration were used.

Sanitized artifact **12284135210** contains exactly nine JSON members: `host.json` and one receipt for each phase. Its **8,430-byte** ZIP matched SHA-256:

`996e5a724a74fbb990b81c0d39b1ea649009688ed3028773accf840cffaaaf03`

The digest matched GitHub metadata and the upload log. Independent review verified exact names, raw member bytes, CRCs and downloaded receipts. No raw configuration, token, signed download URL, API reply, private snapshot or guest log was included.

## Scope and remaining acceptance

This is experimental publication and synthetic disposable validation. HACS uses only an ephemeral read-only installation token; GitHub device OAuth onboarding and owner credentials are outside scope. Three local refusal records do not submit a passcode proof or establish Apple's remaining service allowance.

The HACS rehearsal's matching stopped-state restoration and manual newest-guard preservation are separate from the earlier [prepared Supervisor partial-backup/Recorder result](https://github.com/jmhjr/HomeCircle/blob/v0.1.0-beta.20/docs/LINUX-HAOS-VALIDATION.md#october-20-guarded-supervisor-backup-and-recorder-restore). Neither establishes automatic anti-rollback, ordinary enabled-entry/full-system/add-on/encrypted/cloud restore, production history or retention acceptance. Keep matching package/storage backups and follow the [backup and rollback guide](https://github.com/jmhjr/HomeCircle/blob/v0.1.0-beta.20/docs/FINDMY-SETUP.md#upgrade-backups-and-rollback-for-the-unreleased-candidate).

No new owner Apple sign-in/recovery, location accuracy, movement/latency, long-term field, physical-display or glibc Core acceptance is added. Earlier [beta 19 live evidence](https://github.com/jmhjr/HomeCircle/blob/v0.1.0-beta.20/docs/BETA19-VALIDATION.md) retains its dated scope. The ZIP includes inherited notices but no Apple binary, Unicorn wheel/native library, credentials, provisioned identity, selected keys or runtime state. External assurance, provenance, licensing, service-use and final stable-release decisions remain open in the [stable checklist](https://github.com/jmhjr/HomeCircle/blob/v0.1.0-beta.20/docs/STABLE-RELEASE-CHECKLIST.md) and [license/service checklist](https://github.com/jmhjr/HomeCircle/blob/v0.1.0-beta.20/docs/STABLE-SCOPE-AUDIT.md#licensing-and-service-terms-release-checklist).
