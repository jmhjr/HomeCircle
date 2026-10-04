# Beta 13 candidate validation

HomeCircle `0.1.0-beta.13` is a local experimental prerelease candidate. Published beta 12 remains the current HACS release. No production Home Assistant or physical DAKboard change is part of this candidate check.

## Candidate checks passed

- 150 Python tests and 28 card tests; Ruff, Prettier, `git diff --check`, and the public-file privacy guard.
- Home Assistant Core 2026.9.4 official hassfest: one integration, zero invalid integrations.
- Deterministic 21-file `homecircle.zip` with SHA-256 `eb8b6c4a7b475314f3aee7308e748bd38e38c0af9a8f3cd0dc11faf633d830c1`; every file hash matches `inventory.json`. The archive includes the compiled card, Leaflet license, and project license.
- Disposable package installation, synthetic version upgrade, separate-process restart, integration removal, and post-removal restart passed. The installed static card matched the archive; the HomeCircle dashboard and unrelated Lovelace resource behaved as expected.
- The published beta 12 ZIP matched its recorded SHA-256. A saved fictional beta 12 household survived replacement by this candidate and a separate-process restart.
- A disposable Home Assistant browser setup created a fictional pet Person, assigned a pet GPS tracker, configured the member, and saved. The HomeCircle member and Home Assistant Person tracker link remained after a separate-process restart. The dashboard dialog's Person, tracker, member, and Back screens were exercised. See [fresh-install findings](USABILITY-FINDINGS-2026-10-04.md).
- The exact candidate ZIP replaced the development package in that disposable instance. After restart and browser refresh, the card showed `HomeCircle - Beta 13`, both saved members and their map positions, and street tiles. Home Assistant served card JavaScript identical to the ZIP (`a06b1bd94dc57cab4c6e62f5a46bb89489c83b57576a892205182509a29a65ef` SHA-256). The previous component was kept in ignored local work storage for rollback.

## Still to verify before wider installation

- Publish the reviewed ZIP and inventory as a GitHub prerelease, then download both public assets and compare their bytes with this candidate.
- Install or upgrade through HACS, restart Home Assistant, and confirm the loaded version, served card, preserved household, and title. The local ZIP preview above does not test HACS distribution.
- Confirm the changed dashboard controls on the physical DAKboard before treating its wall display as accepted. Browser checks do not establish physical touch behavior.

Real departure/return and unattended provider failure or credential-expiry checks remain outside this release's completed evidence. The frozen V2 dashboard is unchanged.
