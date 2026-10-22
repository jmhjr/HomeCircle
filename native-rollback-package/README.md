# Native recovery rollback candidate validation

This packet validates the exact canonical HomeCircle candidate selected after the
recovery continuity fix. It produces an **unreleased development preview retaining
version `0.1.0-beta.20`**. It does not publish a release or tag, install into an owner
instance, authenticate an account, submit a device passcode, or validate an HAOS
restore. The separate ordinary-restore experiment supplies that evidence.

The packet adapts the qualified `native-release1-package` fixture from the vault
disconnect milestone. Its official Linux/x86_64 Docker image remains
`ghcr.io/home-assistant/qemux86-64-homeassistant@sha256:414dce485b4eebd9f929f293f7252340bada5715fc4a48b2b954d79195ed3019`,
Core `2026.9.4`, Python `3.14.6`, package constraints
`962c9ccaf398e0b92b10ac9f765ac0f17e22238adc4e768deebc051ee8b60651`,
`pytest-homeassistant-custom-component==0.13.367`, and reference `findmy==0.10.2`.
The six direct requirements and 24-package runtime closure are unchanged.

Only the required backend function bound changes in the driver, from 36 to 52.
The previous 36 required regressions remain mandatory; every new top-level guard,
recovery integration and recovery flow regression is appended when the source is
frozen. The actual suite must pass at least 1698 cases, with no failures and only
the existing named optional Apple DMG range skip. The 122 frontend tests, two
byte-identical builds, exact 113-member integration package, fourteen exact
source-bound original-vault failures, privacy checks, network-disconnected backend
phase, child/process ownership, narrow summaries, cleanup, and deadlines remain
unchanged. The launcher uses a distinct owned Docker name and ownership label so
this packet can run independently of the ordinary HAOS restore experiment.

Before extraction, the driver compares every inventoried byte with a Git blob in
the configured exact canonical commit. The new freeze step includes all regular
canonical blobs, including release documentation, rather than silently retaining
the historical 337-file subset. Safe paths, source bounds, immutable tool hashes,
manifest requirements, package scope, and source/package equality remain checked.
Original baseline-vault bytes and all fourteen cause identities are unchanged.

The payload directory must contain exactly `baseline-vault.py`, `config.json`,
`source-inventory.json`, and `source.tgz`. Unfrozen preparation deliberately leaves
source and configuration pins invalid and lacks the archive/inventory; it cannot
qualify a result. Root freezes source after the product changes and reviews are
complete, then pins the resulting configuration hash in the reviewed workflow.
The workflow triggers only on pushes to `codex/native-amd64-validation` changing
`native-rollback-package/**` or its new workflow path. It has no manual dispatch.

Standalone contracts use only standard-library helpers:

```sh
python3 -B -m unittest discover -s native-rollback-package -p test_driver.py -v
bash -n native-rollback-package/run_host.sh
```

The native launcher runs only after exact source freezing and root publication:

```sh
bash native-rollback-package/run_host.sh \
  --payload native-rollback-package/payload \
  --pins-sha FINAL_CONFIG_SHA256 \
  --source-repository "$GITHUB_WORKSPACE" \
  --output native-rollback-package-results
```

Receipt and development-preview artifacts retain seven-day expiry. Only fixed
counts, hashes, versions, public required-test identities and safe failure labels
are exported; private test logs, XML bodies, environment data, account state and
exception text remain inside the disposable private workspace and are removed.
Preparation contracts alone are not native runtime qualification.

The reporting-only R2 revision preserves a bounded failed package summary before
strict JUnit uniqueness/outcome acceptance. Pytest teardown failures can create a
second record for the same test identity; that still fails acceptance, while the
summary now retains complete record counts and up to twelve source-bound public
class/function labels per failure/duplicate kind. Parameter values, XML bodies,
exception text and unknown test identities are never exported. This changes no
product source, backend test, dependency, original-vault cause gate or success
criterion. The earlier failed run remains separate evidence.
