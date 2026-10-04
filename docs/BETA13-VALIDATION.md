# Beta 13 release validation

HomeCircle `0.1.0-beta.13` is a published experimental prerelease. Its production installation uses the separate HomeCircle Beta Test dashboard; the frozen V2 dashboard is unchanged. Physical DAKboard acceptance remains open.

## Candidate checks passed

- 150 Python tests and 28 card tests; Ruff, Prettier, `git diff --check`, and the public-file privacy guard.
- Home Assistant Core 2026.9.4 official hassfest: one integration, zero invalid integrations.
- Deterministic 21-file `homecircle.zip` with SHA-256 `eb8b6c4a7b475314f3aee7308e748bd38e38c0af9a8f3cd0dc11faf633d830c1`; every file hash matches `inventory.json`. The archive includes the compiled card, Leaflet license, and project license.
- Disposable package installation, synthetic version upgrade, separate-process restart, integration removal, and post-removal restart passed. The installed static card matched the archive; the HomeCircle dashboard and unrelated Lovelace resource behaved as expected.
- The published beta 12 ZIP matched its recorded SHA-256. A saved fictional beta 12 household survived replacement by this candidate and a separate-process restart.
- A disposable Home Assistant browser setup created a fictional pet Person, assigned a pet GPS tracker, configured the member, and saved. The HomeCircle member and Home Assistant Person tracker link remained after a separate-process restart. The dashboard dialog's Person, tracker, member, and Back screens were exercised. See [fresh-install findings](USABILITY-FINDINGS-2026-10-04.md).
- The exact candidate ZIP replaced the development package in that disposable instance. After restart and browser refresh, the card showed `HomeCircle - Beta 13`, both saved members and their map positions, and street tiles. Home Assistant served card JavaScript identical to the ZIP (`a06b1bd94dc57cab4c6e62f5a46bb89489c83b57576a892205182509a29a65ef` SHA-256). The previous component was kept in ignored local work storage for rollback.

## Published release and HACS checks

- PR #1 merged into `main` at `494e40d`; the [beta 13 prerelease](https://github.com/jmhjr/HomeCircle/releases/tag/v0.1.0-beta.13) targets that commit. Publicly downloaded ZIP and inventory matched the reviewed local files byte for byte. Their SHA-256 hashes are `eb8b6c4a7b475314f3aee7308e748bd38e38c0af9a8f3cd0dc11faf633d830c1` and `4b089c4e6847f8e9b423921c83339f8bf10787b18df43d6e3210e6920ef16c8c`.
- The existing disposable HACS installation upgraded from beta 12 to the selected beta 13 release. After a separate-process Home Assistant restart, HACS recorded beta 13, all 21 installed package files matched the public ZIP, and the served card JavaScript matched it. The two saved fictional members, street tiles, `HomeCircle - Beta 13` title, map positions, and task-based settings choices appeared. The saved household data and options hash was unchanged across restart.
- Before the production beta update, a named Home Assistant backup was completed in This system and Home Assistant Cloud. Production HACS downloaded beta 13 and Home Assistant restarted. Settings → Devices & services reported loaded HomeCircle version `0.1.0-beta.13`; the served card hash matched the public ZIP. The separate HomeCircle Beta Test dashboard retained six members and five map positions. After source integrations finished starting, battery and tracker report details returned. Browser checks passed Ruby focus → Everyone reset, the dashboard settings dialog and per-member choices, and Kiosk view → Exit kiosk. The existing custom card title remained `HomeCircle iPhone Test` by design. No household options were saved during these checks.

## Still to verify

- Confirm the changed dashboard controls on the physical DAKboard before treating its wall display as accepted. Browser checks do not establish physical touch behavior.

Real departure/return and unattended provider failure or credential-expiry checks remain outside this release's completed evidence. The frozen V2 dashboard is unchanged.
