# Beta 18 validation

Experimental prerelease `v0.1.0-beta.18`; no stable tag. See [October 11 changes](RECENT-CHANGES-2026-10-11.md), [changelog](../CHANGELOG.md), [setup](SETUP.md) and [privacy](PRIVACY.md). This record separates automated package evidence, independent static review and installed browser/field acceptance.

## Review scope

Reviewed every tracked and newly added main-repository source/test/document file since `66672c9`, plus the commits included since beta 17. Preserved frozen V2 and unrelated configuration. The separate Linux Find My prototype was captured in a private source/test/brand/document archive with hashes; Apple sessions/keys, personal photos/screenshots and runtime files are absent from the public package.

Claude performed a read-only privacy/security/bug review of the diff and new files. Initial blockers: all-stale verified GPS could replace an unknown-age HA Person source; a single HTTP read could truncate Photon responses; city names matching regions could be stripped and cause unnecessary lookup. Additional findings covered concurrent zone changes, malformed/disabled external Life360 accounts and expected shared-report source switches. All were corrected with regressions. Maintainer review also fixed entry-removal cache cleanup, cancellation, upload-after-Back submission, and native Markdown-name handling. Claude’s full recheck confirmed all six findings fixed and approved publication as an experimental prerelease, with no privacy/security blocker. The suggested primary-home form fix and HA GPS-accuracy matching were also implemented. The final focused recheck and exact archive checks are recorded below.

## Validation boundaries

The backend uses pinned HA Core 2026.9.4 and synthetic inputs with outbound sockets blocked. Frontend tests use jsdom/Leaflet and synthetic images. Package lifecycle uses isolated real Core processes; version-only baseline fixtures do not establish an actual published-HACS upgrade. Installed development browser checks cover picture/crop/Details, import selection/Skip, map focus, row alignment and city lookup. These checks do not certify physical DAKboard appearance of the final beta 18 package.

Known limitations: picker filename reset while cropping; publicly readable opaque native HA image links; native uploaded images retained after reference removal; optional Photon demo availability; city cache retained locally on disable; source oscillation and field accuracy follow-ups; genuine phone-report evidence, unattended provider recovery and broader Core compatibility still open. Private Find My onboarding/helper cleanup and real multiple-account acceptance remain outside this release.

No personal location data, screenshots, faces, credentials, raw replies or provider vaults are published. Existing history retains earlier participant first names as already documented; this is not a claim of historical anonymity.

## Exact candidate package checks

- 323 backend and 105 frontend tests passed. Ruff, frontend formatting, diff checks and the public-file privacy guard passed. The private Find My synthetic suite separately passed 63 tests; it is not packaged.
- Official HA Core 2026.9.4 hassfest validation passed with zero invalid integrations. The HACS validator passed for the existing public main repository; the final tagged release is checked separately after merge.
- The deterministic 28-file archive matches source and inventory byte for byte. Generated frontend, Leaflet license, original reviewed brand icon and all Python/translation/manifest files were inspected; no prototype, credentials, household markers or runtime data is included.
- Real isolated Core processes passed install, version-only upgrade, restart, removal and post-removal restart. Saved selection and unrelated resource survived; removed static resource stayed absent.
- Tested archive SHA-256: `2d53a48f993447ae1a863f712f88fab4bd8a9d73c01b0a7ee88b931be2bc07ae`.

## Published-HACS acceptance

A separate disposable instance installed published beta 17 through HACS and configured two fictional members. Publication, download-back checksum and actual beta 17 → 18 HACS upgrade results will be recorded after publication; this does not authorize or imply a production upgrade.

## Final independent sign-off

Claude completed the full recheck and then a focused check of the last fixes before publication. Final verdict: no blockers, cleared for beta 18. It verified Primary Home draft cleanup, HA accuracy/passive matching, GPS-only transmission, cached-street validation, rollback-resistant budgets and shielded-save unload/removal ordering. All reviews were read-only static reviews; the maintainer ran the suites and real Core checks separately. The review transcripts remain in the private local release evidence.

Nonblocking follow-ups: passive-zone consistency in the older HA-Person pending-zone fallback; cached address projection for a non-GPS source at an already cached cell (no new transmission); and cancellation of a native save task during HA shutdown. These are recorded in the roadmap.
