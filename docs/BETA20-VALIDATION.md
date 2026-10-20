# Beta 20 prerelease validation boundary

October 20, 2026. Version `0.1.0-beta.20` is an experimental, separately versioned
derivative of the reviewed 112-file candidate whose manifest remains beta 19 and
whose ZIP SHA-256 is
`f0477a91e78181fe1f8d80ada176a1739e10a7502abe7ee6ee2240571280d1f5`.

## Package relationship

The installable beta 20 payload must contain the same 112 root-relative members.
Only `manifest.json`, `frontend.py` and `frontend/homecircle-card.js` may differ,
by the exact version change `0.1.0-beta.19` to `0.1.0-beta.20`. The card imports
the integration manifest, so its compiled version label changes too. The other
109 member bytes, including licenses, certificates and vendor/runtime source,
remain identical.
The frontend npm package and both lockfile version fields are aligned in source.

Build and archive inspection use the unchanged release builder/validator on Linux.
Frontend rebuilds must reproduce the reviewed card with only that version-label
change; the Leaflet license remains identical.
Python validation runs only on disposable Linux; no Mac Python is required.

## Inherited evidence and publication sequence

The [independent cryptographic review](INDEPENDENT-CRYPTO-VALIDATION.md),
[platform/upgrade review](PLATFORM-UPGRADE-RECOVERY-VALIDATION.md) and
[Linux/HAOS evidence](LINUX-HAOS-VALIDATION.md) identify the frozen parent candidate
and retain their exact dated scope. That candidate passed 1,443 backend tests
with one optional fixture skipped on the recorded Linux targets, native worker
and lifecycle checks, exact-baseline upgrade/recovery, managed HAOS activation,
and the separate prepared Supervisor partial-backup/Recorder protocol.

A versioned package must pass its Linux packaging/frontend/privacy checks before
publication. The actual public prerelease assets must then be downloaded back
and hash-checked. Genuine HACS release selection, asset download, installed
bytes, real restart/loaded version, saved selections/identities/resources,
rollback and newest-guard preservation remain distinct acceptance steps.

This tagged snapshot records the package and required sequence. Current
publication and delivery results are recorded on the isolated
[validation branch](https://github.com/jmhjr/HomeCircle/tree/codex/native-amd64-validation)
and in the GitHub prerelease notes once completed. No HACS pass is inferred from
the parent candidate's stopped manual installations.

## Upgrade and recovery boundary

Read [Find My backups and rollback](FINDMY-SETUP.md#upgrade-backups-and-rollback-for-the-unreleased-candidate)
before upgrading. Published beta 19 can drop the newer identity ledger after a
package-only rollback. Retain matching package/storage copies and independently
preserve the newest recovery safeguard.

Supervisor restores automatically start Core. The tested partial-backup protocol
therefore requires the backed-up HomeCircle entry to be disabled and unloaded,
verifies the disabled automatic restored boot, promotes the newest external
safeguard with Core stopped, checks another disabled boot and only then enables
the entry. This is manual safeguard preservation, not automatic anti-rollback.

## Remaining limits

This prerelease adds no new owner/Apple sign-in, recovery, location, movement or
physical-display acceptance. Historical beta 19 owner proof does not qualify
beta 20 owner recovery. Ordinary enabled-entry/full-system/add-on restore,
encrypted/cloud portability, production Recorder/retention, glibc Core,
multi-item long-term field behavior and external specialist/format assurance
remain open. HACS token setup does not establish OAuth onboarding.

The [licensing/service checklist](STABLE-SCOPE-AUDIT.md#licensing-and-service-terms-release-checklist)
remains open, including inherited provenance, Unicorn obligations, Apple and
Life360 service/provider terms and branding. Inherited notices remain included;
the package contains no Apple binary, provisioned identity, credentials,
selected-item keys or runtime state. This is not a stable-release approval.

The isolated release commit/tag preserves main, the existing working checkout,
frozen parent ZIP and production/V2. No stable version has been chosen.
