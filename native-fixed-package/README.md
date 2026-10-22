# Exact fixed-candidate native package validation

This isolated native Linux/amd64 container harness binds canonical source
`3c33160c67e53956ab52298ffc10ccc9992132f0` (381 public Git files) and the exact
113-member candidate archive
`f181e6300f15d8977817a552db90d35caf0edc869067ebeea815c7be1df0248e` with inventory
`8ea456beb9b2eaaf4ba50639532b8dafabe0e02d1e13a77a59525f1c249c7447`.
It makes no source/ref changes, owner-account calls or working-instance changes.
The workflow must verify every frozen harness input before importing any helper.
`prepare_payload.py` is a separate public-source preparation tool, not a native
acceptance shortcut. Configuration pins bind the driver and requirement helper
before their first use.

The original candidate was produced with compression level 6. The unchanged
canonical builder uses level 9 and produces archive
`acfcda419a817032c38a463505f686b0f6ab49e69a8f1603d9b2ff43f24e442b` from the same
113 member names/bytes. Both identities are required separately. The canonical
build is repeated and inspected; it never replaces the input candidate.
Tests verify all 113 candidate member bytes in the source/test tree, with only
its exact Git-bound source-only `README.md` additionally retained. Every other
unexpected product-tree file is refused, apart from ordinary Python bytecode.
The exported `homecircle.zip` and `inventory.json` remain the original f181/8ea
bytes. No stable version substitution, stable release or new delivery claim is
made.

The pinned current-Core image is Linux/amd64 Core 2026.10.2, Python 3.14.6,
registry digest `45f009d6ff1061971102e81f0802cf2762bdd5c5007231c938bd36030cbd0a12`
and image ID `e1acee126eee45b3007494ad7f806d12535dc7d733624b681ed29a505f8c2b98`.
Its constraints hash is `7baa9a8f39ddeb9c5bb60a1036f6d5e33f4b84267f151f53cc2b95ef031a21b5`.
The test plugin is exactly 0.13.373. Product requirements retain their 24-package
closure; the reviewed helper derives the actual Core component/default-auth
requirements without setting integrations up. Dependency preparation happens
online before the container network is explicitly disconnected. Both setup and
acceptance verify the same requirement graph and installed versions. Backend
acceptance, including all pytest execution, occurs after disconnection.

The frontend uses Node 23.7.0 and the source lockfile in private npm configuration
and cache directories. It must build twice to identical assets, pass exactly122
TAP cases with zero failures/skips, and match the candidate's two frontend member
hashes and Leaflet notice. The source privacy checker must inspect all381 public
Git files unchanged, with no flagged patterns; this is not a substitute for
manual review.

The complete backend collection must pass at least1732 cases and all54 required
functions: the prior50 plus all four projected-activity regression functions.
Exactly one skip is permitted:
`tests.test_findmy_runtime_bootstrap::test_retained_public_apple_dmg_fixed_ranges`.
The optional retained public installer is absent from the canonical source copy;
no installer or owner data is copied to make it pass. Duplicate/ambiguous JUnit
records, additional skips and missing required functions refuse acceptance.
The earlier14 pinned-vault baseline failures must still reproduce their verified
causes in an independent public-file-only copy, removed before the green suite.
Red/green execution shares a900-second budget. Bounded failure labels never
export raw JUnit parameters, exception text or logs.

Docker must be local Linux/amd64. The freshly named/labeled container has no host
bind mounts or port forwarding, dropped capabilities, no new privileges and no
healthcheck. Cleanup acts only on the proved-owned container, removes the private
workspace, and is required even after failure. Only six fixed success summaries
are retained: host, source, privacy, frontend, setup and package. A bounded fixed
failure summary may accompany failure. Raw dependency/backend/npm logs stay in
the private workspace and are removed. Exported candidate assets are explicitly
unreleased.

This is full native container/package test execution. It is not a managed HAOS
lifecycle, HACS delivery, real provider authentication, live recovery, field
acceptance, upgrade or stable-release qualification. Previous ordinary restore
and private installation-copy upgrade records retain their separate scopes.

Safe host contracts use only stdlib and verified public release-tool source:

```sh
python3 -I -B -m unittest discover -s harness -p test_driver.py -v
bash -n harness/run_host.sh
```

Do not run the native launcher on the Mac. The workflow owns native execution;
source preparation and the contracts import no HA/provider/native dependencies.
