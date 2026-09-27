# Beta 4 release-readiness audit — 2026-09-27

This is an audit of the published experimental `v0.1.0-beta.4` release for HACS custom-repository testing. It is not approval for a stable release or production migration. The release tag points to `d6f5231d8e8e31fbc44e228b6a7572d835836796`. Code, manifest, HACS metadata and license files on current `main` are unchanged from that tag; subsequent commits have updated validation documents.

## Published package and metadata

- The published `homecircle.zip` and `inventory.json` matched a clean local rebuild byte for byte. The ZIP SHA-256 is `e6c05ae3ddeee76b2022df3ee9dabec011e193655fd9e0fea70bdc6dd2e29ba3`; its 14 entries match the published per-file inventory.
- The ZIP has HomeCircle's MIT license and Leaflet's BSD 2-Clause notice. The build copies the Leaflet notice from the pinned npm dependency. No provider credentials, private HA configuration, or household screenshots are package inputs.
- The manifest declares `0.1.0-beta.4`, the public maintainer, documentation and issue URLs, config flow, and required HA dependencies. `hacs.json` selects the release ZIP and hides default-branch downloads. The public GitHub repository has a description, topics and enabled issues. The release is published as a prerelease, not a stable release.
- The current [HACS publisher requirements](https://www.hacs.dev/docs/publish/start/) and [integration requirements](https://www.hacs.dev/docs/publish/integration/) were checked against these files. The unmodified official HACS action completed all nine checks with no ignored checks. This establishes custom-repository eligibility; it does not claim inclusion in HACS's default catalog.

## Validation rerun

- 60 Python and 12 frontend tests passed. Python Ruff and frontend Prettier checks passed.
- Official Home Assistant Core 2026.9.4 hassfest found one integration and zero invalid integrations.
- The cleanly rebuilt ZIP passed install, upgrade rehearsal, restart, entry removal, and post-package-removal restart in isolated Core processes. The separate published beta 4 HACS install → removal → reinstall check passed with fictional sources. See [beta 4 validation](BETA4-VALIDATION.md).
- The public-file privacy guard initially found no flagged patterns in 78 tracked files or any of the 14 published ZIP entries. The same pattern review found no flags in 170 reachable historical Git blobs. A manual inspection of the bundle's URL hosts found no private host; the only map tile host is OpenStreetMap. An independent manual review then found a likely real pet name, a display location label and a local test port in public validation prose. The current documents and beta 4 release notes were generalized. Earlier public commits remain reachable; the pattern guard did not catch those labels. These scans are conservative and do not prove the absence of every disclosure.
- Initial real-source iPhone, Life360 and separate Pet GPS test records remained usable after beta 4 upgrade and per-source report-mapping conversion. The user confirmed OpenStreetMap tiles and pet member → Everyone touch behavior on the DAKboard. A controlled tile failure/recovery browser test passed using fictional data. These are distinct from a real travel or long-duration provider check.

## Open V0.1 field acceptance

1. Observe real departure and return with the chosen provider sources; this was explicitly deferred.
2. Confirm iPhone background location updates when the phone is away from the local network.
3. Exercise real source switching within one person and verify that each displayed source uses its own report time.
4. Observe provider availability and report freshness over a sustained period, rather than a single snapshot.
5. Confirm the additional-residence count versus primary-house map focus on the physical display; automated Core coverage passed, but the distinct physical result was not confirmed.

## Independent Claude Opus 5.5 review

Claude Code 2.1.283 ran a read-only review of a separate copy containing only public tracked files and the extracted published beta 4 ZIP. Its result reported model `claude-opus-5-5`, no critical/high-severity code defect, and a beta-only verdict. The full review is saved privately with the development task; source inspection alone could not prove test or asset hashes, which the local checks above verified separately.

Claude identified these release risks. The first is reproducible: with a rejected snapshot, five subsequent `hass` updates caused five extra WebSocket requests in a focused local test. The card's 15-second timer remains, but the `hass` setter also retries whenever `_data` is empty. This should be fixed and tested in a later prerelease before a stable release. The other resource-lifecycle risks follow from source and pinned HA Core code: `async_unload_entry` deletes the owned Lovelace resource on each reload, and there is no `async_remove_entry` hook for removal of an entry that was not loaded. The normal HACS removal order passed; unload-failure and uninstall-first paths have not. A manually registered resource is deliberately user-owned and is not updated automatically; the frontend and setup guides now explain its version URL and removal order.

The legacy timestamp/source pair and new `location_reports` map intentionally coexist to preserve beta 3 settings. Explicit per-source values take precedence for their source. This is a documented compatibility choice, not an observed migration failure. The changelog, setup guide, frontend guide, normalization contract, and current release status were reconciled after the review.

## Release decision

Compatibility is verified against Core 2026.9.4, not other HA versions. A real non-admin account has not been checked for both allowed and denied household access in the UI. The public product name remains a release decision. Production V2 replacement requires separate user approval. These limits, the open field checks above, and the confirmed retry defect keep beta 4 experimental; a stable `v0.1.0` tag is not warranted yet.
