# Development

## Current state

Milestones 1–3 implement selection flows, normalization, household counts/focus, an authenticated snapshot interface, and the initial card/editor. Use a disposable HA instance only. Public manifest URLs/codeowners are pending; `hacs.json` is not evidence of HACS validation. Do not install into production.

## Work sequence

Read PRODUCT, ADR-001, feature inventory and PRIVACY first. Implement one roadmap milestone per focused branch. Use a disposable HA instance with synthetic entities and preserve the reference source. No credentials, family entities, photos or raw snapshot files belong in fixtures.

Use Python 3.14.2+ with pinned Home Assistant Core 2026.9.4 and pytest-homeassistant-custom-component 0.13.367 from `requirements-test.txt`. This single version is the tested development target, not a broad compatibility claim. The frontend uses pinned Leaflet/esbuild and native custom elements. Release archive/HACS validation remains future work. The bootstrap privacy checker needs Python 3.10+ and Git. On a fresh clone, enable the local guard:

```sh
git config core.hooksPath .githooks
python3 scripts/check_public_files.py --all
```

If the system Git launcher is blocked by Xcode setup on this machine, the installed Command Line Tools Git executable can be used directly. Do not change Xcode licensing or developer-directory settings as part of this project.

## Git strategy

`main` is the stable integration branch. Use short-lived branches such as `feature/entity-selection`, `feature/normalized-presence`, and `fix/missing-location`. Review a focused diff and required checks before merging; avoid long-lived release/develop branches. Keep a clear changelog under Unreleased.

```sh
git switch -c feature/entity-selection
# Implement and validate with synthetic data, then review the diff.
git add <reviewed-files>
git commit -m "Add person selection flow"
```

The bootstrap initializes local `main`, enables the hook, and leaves files uncommitted for review. It creates no remote, commit, deployment, release or tag. Make the first commit after review; do not stage raw reference files.

Use semantic tags `vMAJOR.MINOR.PATCH`, beginning with `v0.1.0` after its release gates pass. Use prerelease tags such as `v0.1.0-beta.1` for tested prereleases. Keep manifest version (without the `v`) and release notes aligned. HACS release distribution also needs an actual GitHub release, not merely a Git tag.

Before creating a prerelease tag, merge the version's README, changelog, setup wording, and validation notes into `main`. HACS can display README content from the tagged snapshot, so a documentation update made after tagging may leave older version text on its repository page. Attach the tested installable ZIP to the GitHub prerelease, download that asset back, and compare its checksum with the tested package. Then select the release through HACS in a disposable Home Assistant instance, restart, and verify the loaded version, saved configuration, and card resource URL.

## Packaging and checks

Build the card into the integration directory; implement resource registration and a visual editor. Complete the existing development manifest with the selected public identity. English translations are included. Run full HACS and HA manifest validation at the release gate. Verify install/restart/upgrade/removal in the test instance; preserve unrelated dashboard resources. Audit generated files before release because build output is ignored during development.

Acceptance cases are in `tests/README.md`. A source check is not a physical TouchHub test. Record desktop browser, test HA instance, and physical device evidence separately. Production replacement requires a separate deliberate rollout with a backup and rollback plan.

## Milestone 1 checks

Run from the repository root:

```sh
python3.14 -m venv work/ha-venv
work/ha-venv/bin/python -m pip install -r requirements-test.txt
work/ha-venv/bin/python -m pytest
work/ha-venv/bin/python scripts/validate_ha_restart.py
python3 scripts/check_public_files.py --all
```

Tests use the real HA loader, selectors and flow manager with synthetic states. Pytest disables outbound sockets. The separate restart check launches two real Core processes, creates a temporary config directory, symlinks this integration, binds HTTP only to loopback port 18123, saves options, stops, restores the same storage, and removes that temporary directory afterward. Keep that port free. It does not read any existing HA config. The actual HA person integration consumes synthetic GPS and locationless router states; no provider account is used. Core may install its own declared dependencies on first use. Do not confuse this with testing real tracking providers or HACS.

`work/` contains ignored environments and local diagnostics. Do not publish it. Optional lint/format tooling used here: Ruff 0.15.7. Only HomeCircle files and its new test runner were formatted; the bootstrap privacy checker was preserved.

The working branch is `feature/homecircle-card`. Because the bootstrap has no first commit, the branch is unborn and all scaffold/implementation files remain untracked and uncommitted. A conventional diff against main becomes possible after the separately authorized initial commit. No commit, staging, remote, tag, deployment or production migration is part of this milestone.

For manual UI testing, use a separate HA frontend instance and add HomeCircle under Settings > Devices & services. Select people and zones, review each member's trackers/residences, then confirm. Options edits the same selections; the entry menu also offers Reconfigure. Cancel before confirmation to discard the draft. Deleted or renamed entities must be removed or replaced in Options. Clearing optional lists removes those mappings.

## Milestone 2 and browser checks

The same pytest and separate-process commands now validate normalization as well. See [NORMALIZATION](NORMALIZATION.md) and [milestone 2 validation](MILESTONE-2-VALIDATION.md).

Optional browser environment (synthetic data only):

```sh
work/ha-venv/bin/python -m pip install -r requirements-browser.txt
work/ha-venv/bin/python scripts/disposable_ha.py
```

Open loopback port 18124, complete onboarding with a disposable test user, then add HomeCircle. The launcher uses a temporary directory and the same integration source via symlink; it never copies the repository into a replacement checkout or uses existing HA storage. Stop the launcher with Ctrl-C to remove the temporary config and test account. Clean Core exits and HA restart exit code 100 are relaunched against the same temporary storage; unexpected failures are not concealed.

This harness deliberately seeds only its new HTTP storage with stable loopback settings using the pinned HA schema, avoiding a five-minute trial reverting to a broader listener. This test-only fixture is not integration code and must never be pointed at an existing HA config. The launcher takes no external config-directory argument.

On this Mac, building the two pinned voice dependencies required the already-installed Command Line Tools `clang`/`clang++` paths and SDK path supplied only as environment variables for that pip invocation. System Xcode license/settings were unchanged. The optional missing-FFmpeg warning does not affect configuration tests; media/voice functionality is not being tested. Core reports a standalone installation-method warning; this is development QA, not a production deployment recommendation.

Browser restart and deleted-entity recovery now pass in the minimal Core worker. The broader standalone CLI crashed during interpreter shutdown on both tested Python distributions; its native cause remains unidentified. The test launcher uses `bootstrap.async_from_config_dict` and `hass.async_run` with the same real frontend/auth/storage; normal restart returned code 100 and restored both cards and Options. This is a disposable integration test environment, not supported installation-method certification.

## Frontend development

```sh
npm ci --prefix frontend/homecircle-card
npm run build --prefix frontend/homecircle-card
npm test --prefix frontend/homecircle-card
npm run format:check --prefix frontend/homecircle-card
```

The build outputs the local module and Leaflet license into the integration's ignored frontend directory. Include both in any reviewed release archive. Node 23.7.0/npm 11.1.0 were used here. Browser startup may install declared HA dependencies into the ignored virtual environment on first use. The temporary worker takes its generated JSON-compatible configuration from the parent and uses its directory as cwd; no existing HA config is accessed.

See [card setup](FRONTEND.md), [map/network decision](adr/ADR-002-map-and-frontend.md), and [current validation](MILESTONE-3-VALIDATION.md). Frontend tests cover lifecycle denial/disconnect, late responses, safe text rendering and selection logic; real HA browser checks cover the visual onboarding and map interaction path.

## Release preparation checkpoint

The initial reviewed commit establishes `main` from the previously unborn feature branch. Repository identity is now `jmhjr/HomeCircle`, initially private. See [release validation](RELEASE-VALIDATION.md) for completed archive lifecycle checks and remaining public HACS gates. Earlier milestone statements about untracked files and missing identity describe their historical checkpoints.
