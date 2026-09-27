# Beta 5 prerelease validation — 2026-09-27

Published experimental prerelease: [v0.1.0-beta.5](https://github.com/jmhjr/HomeCircle/releases/tag/v0.1.0-beta.5). This release is for disposable or test Home Assistant instances, not stable or production use. The tag points to `297e7aa`. The attached 14-file `homecircle.zip` has SHA-256 `8f611e39bd40bddde119129397e1c0607e402681fda72cd9e7da18b1a4709d98`. Both published assets were downloaded again and matched the local build and inventory byte for byte.

## Source and package checks

- 61 Python and 15 frontend tests passed, including failed-snapshot retry, scheduled refresh, reconnect, unloaded-entry resource cleanup and manual-resource preservation.
- Ruff and Prettier checks passed. Official Home Assistant Core 2026.9.4 hassfest found one integration and zero invalid integrations. The official HACS publisher action passed all nine checks without ignored checks.
- The clean local release build contained 14 files. Every entry matched its inventory hash and passed the public-file guard. Its isolated Core install, version-only upgrade rehearsal, restart, normal entry removal and post-package-removal restart passed. The version-only rehearsal is not evidence of an older published code migration.
- Claude Code 2.1.283 reported `claude-opus-5-5` in an independent, read-only comparison of the post-beta-4 public source with the beta 4 baseline. It found no defect in the changed code and gave a conditional go for disposable beta 5 after the manifest, frontend, package and cache-URL versions were bumped. Those version changes and the focused tests passed before tagging. Claude did not execute tests or validate the published assets; the checks above did.

## Actual HACS upgrade and removal

A fresh loopback-only disposable Core 2026.9.4 instance used HACS and fictional phone/router sources. It downloaded the published beta 4 release, restarted, and configured a two-person HomeCircle household. HACS then downloaded published beta 5. Every installed file matched the beta 5 release ZIP. After restart, the saved HomeCircle data and options, member identities, counts and focus targets were preserved. HACS reported beta 5 installed, exactly one owned Lovelace resource used `?v=0.1.0-beta.5`, and the served JavaScript matched the release ZIP.

The HomeCircle entry was removed first, then HACS uninstalled the repository. After restart, the package and owned resource were absent and the old static URL returned 404. An unrelated Lovelace resource and HA person remained. The disposable instance was stopped and its temporary configuration removed.

An initial automation run used whole-snapshot equality and stopped after the upgrade because live snapshots include changing time-dependent fields. The assertion was narrowed to saved selections and stable household fields; a new disposable instance completed the full upgrade and removal sequence above. This was a test-harness correction, not an observed HomeCircle data loss.

## Open acceptance

The existing real-source disposable dashboard was subsequently [upgraded to beta 5 and checked](BETA5-REAL-SOURCE-VALIDATION.md). The user confirmed the three-member street map and Pet member → Everyone interactions on the physical DAKboard. A later live Life360 Away snapshot and temporary four-member DAKboard focus/reset check passed. A controlled switch between real iPhone and Life360 sources within one temporary HA person also passed for location and per-source report-time provenance; the original three-member test setup was restored. A separate [real non-admin login and selected-source permissions check](BETA5-NONADMIN-VALIDATION.md) passed with fictional sources in a disposable Core 2026.9.4 instance. Removing HACS before deleting the integration entry, then restarting, still cannot invoke HomeCircle cleanup. Options reloads can briefly replace the owned resource. Real departure/return transitions, background iPhone updates away from the LAN, unattended provider failover, sustained availability and physical additional-residence count/focus remain open. Production V2 was unchanged. No stable release or production migration is approved.
