# Exact-preview minimum-Core managed HAOS witness

[Run 39504506480](https://github.com/jmhjr/HomeCircle/actions/runs/39504506480)
passed on native Linux **amd64/KVM**, **HAOS 18.3**, Supervisor **2026.10.2**,
Core **2026.9.4** and CPython **3.14.6**. The two managed observations verified
normal dependency setup, startup, a real service restart, exact loaded and HTTP
served bytes, nonempty saved settings and persisted identities. All 40 preparation
contracts passed; the owned guest and private workspace were cleaned up.
This closes the minimum-Core amd64 managed startup/restart gap within this scope.

## Exact inputs and receipt binding

The tested source is `9bf03eb45d2cf43274074534e9dfe2de841f4011`; its 113-file,
614,209-byte ZIP is SHA-256
`c4530d94be3b2996f8d6c8948db88a51868566047d68558eefde7967f270a861`.
This is the unreleased development preview, still labeled `0.1.0-beta.20`,
not the published beta 20 asset or a released RC. Validation control commit was
`9ab476e6f652273e8ae7220084d767dd6b66b045`.

The independently checked artifact `12303375312` is 5,539 bytes, SHA-256
`fc6cac6f971bf6da609ee9354d923b2265cd1c478ce4cae543350c4a4e0e6a8c`.
It contains exactly `host.json`, `initialize.json` and `restart.json`.
[Machine-readable evidence](RELEASE-1.0-MINIMUM-HAOS.json) retains their semantic
contents, exact member byte/hash bindings, download checks and independent verdict.
Published QA inputs were independently checked against the frozen preparation.

## Observed managed behavior

The fresh owned guest initially ran Core 2026.10.2. Core was stopped and its
account-free configuration reset before one supported explicit selection of
2026.9.4. The observed `not_created` container state was followed by a supported
start and actual running target. The CLI's real version/update/start/stop
capabilities, Supervisor state, Core runtime, container and constraints were
checked before candidate staging. This is fresh disposable target selection,
not acceptance of downgrading an existing owner's configuration.

The Docker 29 content store reported the OCI index as its raw container/image ID.
The controller separately verified all three stored index → amd64 manifest →
configuration objects against pinned hashes, sizes and links, checked platform
and Core labels, and matched all 22 actual RootFS layers to the verified OCI
configuration. The raw index identity is not described as a configuration digest.
The same strict checks were enforced before staging and after both observations.

Normal managed requirement checking and installation remained enabled. Life360,
anisette and Unicorn were absent before staging; the six direct requirements and
24-package declared closure then met the target constraints. There was no
prepared dependency preload, `/config/deps` payload, skip-pip or pip-target override.
Life360's actual loaded module origin was checked. The other five direct module
origins were import-spec observations; closure metadata does not prove every
package or native worker executed.

Real config/options flows used two fictional Persons and two explicitly selected,
registered trackers. The enabled entry, nonempty city-disabled settings and
entry/entity/dashboard/resource/runtime-configuration identities persisted.
All 113 package files, the loaded integration and the actual loopback-served
frontend hash matched the candidate. Separate Core start ticks, rather than a
reused PID, proved two processes. Seven supported managed stop/start actions were
observed across preparation, acceptance and final cleanup.

Initial dependency setup used normal external access. Before the restart the
hypervisor's named external NIC was closed; one earlier positive and two closed
negative connectivity observations bound the network control while QGA remained
available. Core and QEMU stopped and the private workspace was removed.

## Acceptance limits

This run directly installed verified ZIP files while Core was stopped. It did
not test HACS, final RC release transport, historical installed-state migration,
backup/restore, integration removal or repeated native-worker execution. The
separate [prepared restore investigation](RELEASE-1.0-HAOS-RESTORE.md) still has
failed automatic guard anti-rollback protection; this startup witness does not
change that finding. No owner or provider account was configured. Provider-request
and recovery-proof attempt counts were not measured.

The earlier minimum witness failure remains retained separately, as do the
[unsuccessful consumer and ARM pilots](RELEASE-1.0-INCOMPLETE-PILOTS.md).
Other advertised cells, both providers' controlled acceptance and the final
versioned RC remain separate gates. No stable release approval is granted.
