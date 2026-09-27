# Release preparation — 2026-09-27

## Identity and distribution

Maintainer: `@jmhjr`. Development repository: https://github.com/jmhjr/HomeCircle (public experimental development repository).
Manifest documentation and issue URLs target this repository. Version remains `0.0.3-dev1`; no release tag or public release is approved by this preparation.

HACS distribution is configured for `homecircle.zip`, with default-branch downloads hidden because generated frontend files are deliberately untracked. The ZIP contains integration files at its root, including the compiled frontend, Leaflet license and project MIT license. `scripts/build_release.py` rebuilds from the npm lockfile and writes a deterministic archive plus per-file SHA256 inventory under ignored `release/`.

HACS requires a public GitHub repository and a real GitHub release for release assets. Public visibility is now approved; release assets and actual HACS installation acceptance are still pending. See [HACS general requirements](https://www.hacs.dev/docs/publish/start/) and [integration requirements](https://www.hacs.dev/docs/publish/integration/).

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
- Actual HACS installation and release-asset acceptance. Official HACS remote validation and Home Assistant hassfest now pass as recorded below.
- Two independently configured real tracking sources, including a non-Life360 source; fictional GPS/router fixtures do not satisfy this gate.
- Optional external tile failure acceptance.
- Separate production rollout approval.

No production rollout or V0.1 readiness is claimed.

## Official Home Assistant validator

Home Assistant Core **2026.9.4** official `script.hassfest` was run unmodified from the upstream release archive, matching the supported/tested HA version. All applicable integration plugins ran with no skipped plugins: **1 integration, 0 invalid integrations**, exit status 0, no warnings. This is the pinned Core validator, not a claim about a later beta/latest container.

Fixed the findings by explicitly declaring `http` in dependencies, adding `cv.config_entry_only_config_schema(DOMAIN)`, and ordering manifest keys as required. The 54 Python tests pass after these fixes. The package lifecycle checks were repeated against the rebuilt archive.

Reproduction from the repository root after unpacking the official Core release under ignored `work/official-validator/`:

```sh
PATH="$PWD/work/ha-venv/bin:$PATH" \
PYTHONPATH="$PWD/work/official-validator/core-2026.9.4" \
work/ha-venv/bin/python -m script.hassfest \
  --integration-path "$PWD/custom_components/homecircle" \
  --core-path "$PWD/work/official-validator/core-2026.9.4"
```

Official references: [hassfest for custom integrations](https://developers.home-assistant.io/blog/2020/04/16/hassfest/) and [Core 2026.9.4 validator source](https://github.com/home-assistant/core/tree/2026.9.4/script/hassfest). No production HA or DAKboard configuration was changed by this validation.

## HACS validation checkpoint

Ran the unmodified official HACS action entrypoint from integration revision `adb7d83e33d24325535fb43b8226572405143757` against the private GitHub repository on main. Used its pinned action dependencies (HA 2026.8.3, aiogithubapi 26.0.0) and official frontend package in a separate local environment. No checks were ignored and commenting was disabled.

Initial result: 4 of 9 failed. Added repository topics and an original local `brand/icon.png`, generated from geometric drawing code and visually reviewed. The privacy guard allows only that exact path and SHA256; changed bytes and other PNGs still fail. The package includes this asset (14 total files).

Final private-repository result: **7 of 9 passed**, exit status 1. Both remaining failures are public raw-file fetches returning no content for `hacs.json` and the integration manifest. Direct validation of both local files with the official HACS schema objects passed. This is not a full HACS pass or proof of public download/install behavior. Home Assistant 2026.9.4 hassfest still passes after the brand addition. Six privacy guard tests passed, including rejection of altered or relocated brand bytes.

A separate decision to make the development repository public is needed to finish remote validation and then package distribution testing. Repository source, commit history, maintainer identity and MIT license would become publicly visible. The release remains a development build; real-provider and optional tile-failure acceptance remain open. No stable V0.1 release or production rollout is implied.

## Public development checkpoint — 2026-09-27

Following user approval and a history review, the repository is public and explicitly labeled experimental. Reviewed 76 historical path/blob combinations and all 67 current source files. Original commit identities were rewritten to the maintainer's GitHub no-reply address before changing visibility; the current branch history was verified through GitHub. A recovery bundle remains only in ignored local work storage. Rewriting a branch does not guarantee deletion of old commit objects retained by GitHub.

The same unmodified official HACS action was rerun against public main with no ignored checks: **all 9 checks passed**, exit status 0. No release/tag was created. This verifies repository eligibility, not installation, upgrade or removal through HACS. Those tests and the real-provider and optional tile-failure gates remain open.
