# Release preparation — 2026-09-27

## Identity and distribution

Maintainer: `@jmhjr`. Development repository: https://github.com/jmhjr/HomeCircle (private).
Manifest documentation and issue URLs target this repository. Version remains `0.0.3-dev1`; no release tag or public release is approved by this preparation.

HACS distribution is configured for `homecircle.zip`, with default-branch downloads hidden because generated frontend files are deliberately untracked. The ZIP contains integration files at its root, including the compiled frontend, Leaflet license and project MIT license. `scripts/build_release.py` rebuilds from the npm lockfile and writes a deterministic archive plus per-file SHA256 inventory under ignored `release/`.

HACS requires a public GitHub repository and a real GitHub release for release assets. Private repository creation does not fulfill that gate. See [HACS general requirements](https://www.hacs.dev/docs/publish/start/) and [integration requirements](https://www.hacs.dev/docs/publish/integration/).

## Passed locally

- 54 Python tests and 9 frontend tests.
- Five isolated real HA Core processes using copied archive contents, not the source symlink: install, upgrade, restart, entry removal, and restart after package deletion.
- Imported integration path verified inside disposable configuration.
- Served frontend bytes match the installed ZIP bundle.
- Household selections and options survive upgrade/restart; owned frontend resource URL changes to the installed version without duplicates.
- An unrelated dashboard resource survives upgrade and removal.
- Removing the integration entry clears its resource without deleting HA people. After deleting only the disposable package and restarting, its static URL returns 404.
- Upgrade starts from a version-only `0.0.3-dev0` fixture made from current code. This is an update-mechanism rehearsal, not evidence of migration from a published older release or an older data schema.
- Local manifest/HACS field checks, Ruff, Prettier, source privacy guard and archive inventory review.

Run `work/ha-venv/bin/python scripts/build_release.py`, then `work/ha-venv/bin/python scripts/validate_release.py` in the pinned development environment.

## Physical display acceptance

User-operated DAKboard OS 4.14 display, using the LAN-accessible disposable HA instance and fictional sources:

- Member/category/Everyone selection, grouped-marker selection and scrolling passed by user confirmation.
- Unavailable scenario and subsequent Home recovery passed by user confirmation.
- Initial unavailable report was investigated: changing the scenario correctly removed the marker, but an already-empty map looked unchanged. Scenario buttons were renamed with a `Simulate` prefix to distinguish them from category filters; browser verification confirmed one marker -> zero -> recovery.
- The explicit secondary-residence count/focus acceptance result was not separately confirmed; automated Core coverage passes.
- Production HA was not modified. Temporary DAKboard launch block and dock entry remain for the ongoing test session. Test credentials, network addresses and screenshots are excluded from Git.

## Still required before V0.1

- Actual HACS custom-repository download/install/update/removal after a separately approved public release.
- Current official HACS validation and Home Assistant hassfest acceptance, including any brands requirements. Local field checks do not substitute for these validators.
- Two independently configured real tracking sources, including a non-Life360 source; fictional GPS/router fixtures do not satisfy this gate.
- Optional external tile failure acceptance.
- Separate production rollout approval.

No production rollout or V0.1 readiness is claimed.
