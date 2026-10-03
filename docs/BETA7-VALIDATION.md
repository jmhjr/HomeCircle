# Beta 7 validation — 2026-10-02

Version `0.1.0-beta.7` adds a guided one-tracker suggestion for each member and a portrait or initials map cluster for overlapping members. Existing saved multi-tracker selections remain intact when editing. Portraits are taken only from HA-served person or selected-tracker images; no family photos or location data are included in the public package.

## Candidate checks

- 70 Home Assistant Python tests and 21 frontend tests passed. Ruff, Prettier, Git whitespace, and the public-file privacy guard passed.
- Official Home Assistant Core 2026.9.4 hassfest reported one integration and zero invalid integrations.
- The deterministic 14-file `homecircle.zip` matches its source files and SHA-256 inventory. Archive contents passed the public-file privacy guard. ZIP SHA-256: `9de9ef10f28b47c072e536f64ffb1eff4243ddcffe9a05f2afa948ee6c794e7b`.
- Isolated Core install, version upgrade, restart, entry removal, and post-removal restart passed with unrelated dashboard resources preserved.
- An isolated published beta 6 ZIP to local beta 7 ZIP Core upgrade and restart preserved the saved household data and options.
- A synthetic browser preview showed four member initials at one position as a cluster. Selecting it exposed all four member choices. The existing keyboard-focus regression also passed.

## Still to check

An actual beta 6 to beta 7 HACS upgrade on the real-source disposable instance, physical DAKboard touch behavior, and any production upgrade are separate from these candidate checks. Production beta 6 and the existing V2 dashboard were unchanged.
