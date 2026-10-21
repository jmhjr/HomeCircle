# Exact-source native Linux development-preview validation

This focused harness validates the canonical HomeCircle source selected for the 1.0 readiness work. It produces an **unreleased development preview retaining version `0.1.0-beta.20`**. It performs no version substitution, publication, tag update, owner-account operation, managed Core lifecycle, HACS delivery or additional identity provisioning smoke test.

The implementation adapts the proven `native-beta20-package` harness at `35d4c3d184b810694c1bdd66778587f08a6d2e5b`. It preserves its native Linux/x86_64 Docker boundary, ownership labels, private staging, capabilities restrictions, offline full-backend phase, child reaping, deadlines, summary projection and cleanup. Product source, new regressions and the reviewed privacy checker come from the root-selected canonical commit rather than the older frozen package.

## Immutable inputs

The initial payload directory must contain exactly:

- `config.json`: complete reviewed configuration based on `config.example.json`.
- `source.tgz`: deterministic, regular-file-only raw USTAR inside gzip, containing the actual public product source.
- `source-inventory.json`: exact relative name → `{bytes, sha256}` inventory for every source file.
- `baseline-vault.py`: exact original canonical vault bytes, pinned by the reviewed driver, used only in a separate private expected-failure copy.

The caller must pin the SHA-256 of `config.json` in its reviewed workflow. The configuration pins the driver itself, canonical source commit, source archive/inventory, actual source count and reviewed privacy checker. It also lists the new named backend regressions that must pass. Placeholders, ambiguous keys, changed version/package scope, invalid hashes, duplicate required tests and missing regressions fail closed. The source count is validated from the configuration, not assumed to remain 327/328.

Before extraction, the driver reads each inventoried source blob independently from the specified canonical Git commit and compares its exact bytes with the archive. It never changes that repository's files, index or HEAD. `candidate_source_prefix` normally stays empty; it can identify a canonical subtree if needed. This proves the **inventoried public-file scope** against the commit, not an inventory of every unrelated validation file in the repository. The workflow must fetch that exact commit object into its checkout before calling the launcher; a shallow checkout of a different branch may lack it.

Builder and validator retain their previously reviewed pins:

- `scripts/build_release.py`: `0c1ac7f979817bd5fc2cd4a4101571931488d6972bc6f181a26ac21edcf8c7d0`.
- `scripts/validate_release.py`: `20c0466b4fa70a83c5f282bfcd07b0d2e6f5a3a1a09bf90072649441b2ad7f37`.

The privacy checker's exact new hash is supplied in `checker_sha256`; no old-checker assumption is retained. The reviewed public-notice exception and its new regressions are part of the canonical source. This harness does not create or broaden an exception.

## Runtime and execution

The fixed official image is `ghcr.io/home-assistant/qemux86-64-homeassistant@sha256:414dce485b4eebd9f929f293f7252340bada5715fc4a48b2b954d79195ed3019`. The local daemon and container must actually be Linux/x86_64, with Core `2026.9.4`, CPython `3.14.6`, its known package constraints SHA-256 `962c9ccaf398e0b92b10ac9f765ac0f17e22238adc4e768deebc051ee8b60651`, test plugin `pytest-homeassistant-custom-component==0.13.367` and validation reference `findmy==0.10.2`. The reference package is a test dependency, not an added HomeCircle runtime requirement.

The driver checks all six unchanged direct manifest requirements and the actual 24-package transitive closure against Core constraints. Dependency installation uses a fresh owned container with internet access. It then disconnects that container from Docker's bridge and verifies there are **no attached networks**, both before and after the full backend suite. Existing recorded network-denial tests run unchanged as part of that suite. No host configuration, socket, token, directory or provider data is mounted into the container.

The phases are:

1. Independently verify all source hashes and canonical Git blobs; extract into a new private tree.
2. Run the exact reviewed public-file privacy checker on actual source before dependency directories or generated assets exist.
3. Install lockfile frontend dependencies, build twice, require exact byte equality for both generated frontend files, and run the existing 122 frontend tests with explicit TAP counts. Require Leaflet's bundled notice to match its dependency file exactly.
4. Stage only the pinned public source and verified generated frontend into the fresh official Core image. Use the unchanged official builder and validator to produce and inspect the 113-member integration-only package twice; require byte-identical ZIPs and exact equality to the canonical source plus built frontend.
5. Install the constrained test/runtime dependencies, verify versions/closure, then disconnect networking.
6. With networking already disconnected, first run the fourteen exact named malformed/missing-vault regressions against the original canonical vault in a fresh public-file-only copy, supplemented only by the two verified frontend assets. Require pytest exit 1 and exactly those fourteen JUnit failures, with no collection errors, skips or extra cases. Always remove that copy; never replace the fixed source. Then run the **full** backend pytest suite, including the root-named new regressions. Parse actual JUnit case results rather than require the old exact pass count. Require at least the configured baseline (minimum 1698), zero failures, every named required regression passed, and exactly the existing named optional skip `tests.test_findmy_runtime_bootstrap::test_retained_public_apple_dmg_fixed_ranges`. Additional/missing/changed skips fail. Duplicate or ambiguous JUnit cases fail.
7. Require all source bytes and generated frontend bytes unchanged, rebuild and revalidate the identical package after tests, collect only narrow summaries and exact resulting assets, stop/remove the owned container, and remove private state.

## Calling and review

After freezing the driver, fill `config.json`, calculate its final SHA-256, and call on the native Linux runner:

```sh
bash native-release1-package/run_host.sh \
  --payload native-release1-package/payload \
  --pins-sha FINAL_CONFIG_SHA256 \
  --source-repository "$GITHUB_WORKSPACE" \
  --output native-release1-package-results
```

The workflow owns the outer timeout and artifact publication. The launcher retains the proven 3300-second internal deadline with bounded operations and independent cleanup grace. No mutating retry was added. Missing ownership proof, failed cleanup, unexpected counts, missing regressions or an offline-state failure yields nonzero status and `failed_or_incomplete`.

`public-summary/` contains sanitized source/privacy/frontend/setup/package/host JSON. It exposes reviewed commit/hash/count/version/boolean evidence, required public test names and bounded failure labels; it excludes test logs, XML bodies, environment variables, configuration/state, tokens and exception messages. `release-assets/` is moved out of private storage only after successful acceptance and cleanup prerequisites. These assets remain a same-version development preview and must not replace the immutable published beta20 assets.

Run standalone preparation contracts with `python3 -B -m unittest discover -s native-release1-package -p test_driver.py`. Those contracts import only standard-library driver helpers, never Home Assistant or native libraries. `bash -n` checks launcher syntax. Actual backend/frontend/package qualification requires native Linux execution; preparation checks alone are not a release result.

This revision retains the previous 32 required functions and adds four (36 maximum; 37 refused). The expected-failure control and fixed full suite share one 900-second deadline. The original source is the docs-only canonical child `fc0bba472cd60a06dac6bab30b7d011fd533624b`; its vault bytes equal the previously qualified runtime. A successful red control demonstrates only the selected synthetic regressions, not an account operation. Private baseline logs and XML are never artifacts; its safe aggregate is in the existing package summary. All six receipt artifact members, container isolation, cleanup and outer deadlines remain unchanged. New native results are required for the fixed candidate.
