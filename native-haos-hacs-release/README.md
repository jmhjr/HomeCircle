# Disposable native HAOS HACS release rehearsal

This Linux-only harness validates the separately versioned `0.1.0-beta.20` prerelease through unmodified official HACS 2.0.5 in a newly created HAOS 18.3 KVM guest with Core 2026.10.2. It does not operate the production installation or the historical harnesses. Do not execute any Python here on macOS.

The published prerelease and downloaded assets are verified; the actual eight-phase HACS rehearsal is still pending. The 45 offline controller contracts passed on native Linux in [run 39460449773](https://github.com/jmhjr/HomeCircle/actions/runs/39460449773); that does not establish HACS runtime acceptance. All immutable release pins are now finalized, and any missing or changed pin fails preflight before guest creation. The published tag is `v0.1.0-beta.20`, pointing exactly to release commit `d02a9bdb9027cb51c99165a09ba50d5b175f5fb9`. The host verifies the actual public tag, prerelease metadata, asset ID/size/digest, canonical release URL, and tag's normal `hacs.json` (`zip_release:true`, `filename:homecircle.zip`), then independently hashes the public asset.

The published ZIP is `homecircle.zip`, 604,937 bytes, SHA-256 `fc0b365d9688459504f874af5c38393e24145d657f15f1def8ada9184f363285` (release ID `418643687`, asset ID `659912694`). Its `inventory.json` SHA-256 is `5e724f69ff20a711dd87b2a39ed96818781813bb6f1e7b3addedc6e048593d77`. Publication metadata and the public download-back match those pins.

Native Linux package validation and the downloaded asset verify the exact 112 members and three version-only changes described here. The controller independently enforces the same relationship before starting a guest. The new 112-member ZIP must differ from frozen candidate `f0477a91e78181fe1f8d80ada176a1739e10a7502abe7ee6ee2240571280d1f5` only by byte-exact `0.1.0-beta.19` to `0.1.0-beta.20` substitutions in `manifest.json`, `frontend.py`, and the compiled `frontend/homecircle-card.js`. Its other 109 files must be identical. This separately versioned package does not change the original candidate.

The eight bounded phases are:

1. `bootstrap_hacs`: real HACS release-ZIP download of published beta 19; no HomeCircle code loaded yet.
2. `baseline`: real Core restart, synthetic supported Person/tracker/config/options setup, exact served bundle, and actual persisted-store checks. The controller then stops Core and retains the matching `.storage`/image snapshot privately.
3. `upgrade_download`: supported HACS prerelease selection and genuine beta 20 release-ZIP download. The receipt distinguishes beta 20 files from still-loaded beta 19 code.
4. `upgraded`: real restart, loaded beta 20 frontend constant, exact installed bytes and served bundle, persistent identity continuity, and three synthetic local recovery refusals.
5. `rollback_download`: genuine HACS beta 19 release-ZIP download while beta 20 remains loaded.
6. `rollback`: stop Core, restore the matching baseline state while separately retaining the newest guard, then restart beta 19. Published beta 19 checks guard bytes only; it does not exercise the candidate's new guard API.
7. `reupgrade_download`: genuine HACS beta 20 release-ZIP download while beta 19 remains loaded.
8. `final`: real restart, exact beta 20 package and served bundle, original identities, and actual guard API still blocked at three refusals.

Every phase requires enabled HACS and an empty queue. HACS metadata must match the package actually installed. Stable entry/options/Person/tracker/registry/dashboard/resource identities and the newest guard hash must match throughout; resource URLs may legitimately carry the new version. Fresh process start ticks and cached `frontend.VERSION` prove activation independently of disk replacement. No candidate ZIP is copied into the guest by the controller, and no HACS catalog/default-branch adapter is used.

Only the workflow's ephemeral read-only installation token enters the owned guest, through a mode-600 private file and a direct disposable HACS config entry. GitHub device OAuth onboarding is not covered. No owner GitHub or Apple credentials, provider accounts, passcodes, or production configuration are used. The three guard events are local refusal records, without proof generation or Apple/provider requests. This run does not repeat Supervisor backup/Recorder testing, general enabled-entry restore, uninstall, physical display acceptance, or live provider validation. The matching stopped-state restore and manual latest-guard preservation are explicit rehearsal steps, not automatic antirollback guarantees.

The guest has outbound user-mode NAT without forwarded host ports. Its process group, disks, firmware variables, serial/QEMU logs, HACS token and private snapshots are owned by this controller and removed during bounded cleanup. Only allowlisted synthetic JSON projections leave the VM. No raw config, token, archive, signed download URL, API response, or guest log is uploaded.

Bounds remain: 5,520-second controller work budget plus 120 seconds reserved cleanup; 1,500 seconds for initial managed readiness; 1,200 seconds for the single optional Core update; 180 seconds total for each one-shot stop/start; 600 seconds per guest phase and 660 seconds per host phase wait. The launcher adds a 5,700-second process timeout with 45-second kill grace. The CI job permits 125 minutes with separately bounded preparation/upload steps. Failed mutations are not retried.

`workflow.yml` is published only as `.github/workflows/native-haos-hacs-release.yml` on the isolated `codex/native-amd64-validation` branch. Its scoped paths and `contents:read` token do not authorize release, tag, main-branch or production writes. Root publication/review of the separately prepared prerelease is a distinct step. Offline tests run only in native Linux CI; a passing source review is not runtime evidence.
