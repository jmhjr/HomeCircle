# Beta 12 validation

HomeCircle `0.1.0-beta.12` adds a shorter setup path, focused tracker add/remove and member editing in Options, per-member map visibility, and an administrator Settings button on the card. This is an experimental prerelease. The existing Home Assistant entity source and optional direct Life360 connection remain available.

## Candidate checks

- 133 Python tests and 27 frontend tests passed, along with Ruff, Prettier, `git diff --check`, and the public-file privacy guard.
- The deterministic 18-file release ZIP has SHA-256 `41ced447ca1b1cdefcd90215c892094972830c6860daaaeb7d3678f01210d9c7`.
- Disposable Home Assistant Core package install, upgrade, restart, removal, and post-removal restart passed. A separate two-process offline Life360 restart passed with fictional account data.
- The published beta 11 ZIP matched its recorded SHA-256. A saved fictional household survived replacement of that package with beta 12 and a separate-process restart.
- In the disposable Home Assistant browser, the administrator Settings button opened the HomeCircle integration page. It was hidden in kiosk view and restored on exit.

## Production installation

Pending release publication and production HACS upgrade. Record the loaded integration version, saved household, served card bytes, browser behavior, and physical DAKboard acceptance separately after installation. Departure/return and natural credential-expiry field tests remain open.
