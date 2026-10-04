# Beta 12 validation

HomeCircle `0.1.0-beta.12` adds a shorter setup path, focused tracker add/remove and member editing in Options, per-member map visibility, and an administrator Settings button on the card. This is an experimental prerelease. The existing Home Assistant entity source and optional direct Life360 connection remain available.

## Candidate checks

- 133 Python tests and 27 frontend tests passed, along with Ruff, Prettier, `git diff --check`, and the public-file privacy guard.
- The deterministic 18-file release ZIP has SHA-256 `41ced447ca1b1cdefcd90215c892094972830c6860daaaeb7d3678f01210d9c7`.
- Disposable Home Assistant Core package install, upgrade, restart, removal, and post-removal restart passed. A separate two-process offline Life360 restart passed with fictional account data.
- The published beta 11 ZIP matched its recorded SHA-256. A saved fictional household survived replacement of that package with beta 12 and a separate-process restart.
- In the disposable Home Assistant browser, the administrator Settings button opened the HomeCircle integration page. It was hidden in kiosk view and restored on exit.

## Published and installed

The [beta 12 prerelease](https://github.com/jmhjr/HomeCircle/releases/tag/v0.1.0-beta.12) contains `homecircle.zip` and `inventory.json`. Downloading both public assets returned bytes identical to the candidate files above.

Before the production update, Home Assistant showed beta 11 loaded. A named backup, `Before HomeCircle beta 12 - 2026-10-04`, completed in both this system and Home Assistant Cloud. The separate HomeCircle beta dashboard had six saved members and six map positions. Production continued to use existing Home Assistant entities; no direct Life360 account was connected in HomeCircle.

Production HACS downloaded beta 12. After a Home Assistant restart, its integration page showed `0.1.0-beta.12`. The card JavaScript served by Home Assistant matched the published ZIP byte for byte (SHA-256 `b4ec0e61c8584d65bb3427935d2d09860ce20549c42fa78818b1e33fffe573eb`). The dashboard retained six members and six map positions. Battery and report details returned after the source integrations finished starting. Browser checks confirmed one-member focus and Everyone restoring six positions, Settings opening the integration page, the add/remove/edit shortcuts in Options, and Settings disappearing in kiosk view and returning on exit. No household options were saved during these checks.

The physical DAKboard has not yet been checked for beta 12. Departure/return and natural credential-expiry field tests remain open. The frozen V2 dashboard was not edited.
