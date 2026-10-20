# Exact development preview: current Core lifecycle

Verified October 20, 2026. [Native run 39494419279](https://github.com/jmhjr/HomeCircle/actions/runs/39494419279)
passed on **amd64 and ARM64**, using official Core **2026.10.2** images,
CPython **3.14.6** and their pinned active constraints. Each matching native
runner passed **12 focused regressions, zero failures and zero skips**, then
**four separate real Core processes**: create, restart, remove and removed.
These are repeated cases across two targets, not 24 new distinct regressions.

Product source is `9bf03eb45d2cf43274074534e9dfe2de841f4011`; validation controls
are `457622bdfaab2d145e4df3473cdcbf9513ce5b9f`. All 337 canonical source blobs and the exact 113 installed
package members were checked. The ZIP is 614,209 bytes, SHA-256
`c4530d94be3b2996f8d6c8948db88a51868566047d68558eefde7967f270a861`;
its inventory SHA-256 is
`9bdfba997d5437d354673a98c8b78d3875d459499281bca3e20bc629369dcb6b`.
It retains the beta 20 version label but is an **unreleased development preview**,
not the published beta 20 package or a released RC.

The processes execute the unchanged canonical lifecycle helpers, including
reload, unload and setup. Loaded module paths and bytes match the installed
package. The served card matches SHA-256
`80b2727d18a0b8edb052c47d2c718850adf19bf5d35c2af6c3eb86c07f1f6cac`.
Saved entry, settings and selected-source identity agree after restart, as do
resource URL/type semantics. Owned resource-ID persistence is deliberately not
claimed because unloading can recreate that resource. Removal clears the owned
entry/static bundle and retains the unrelated resource.

The focused cases cover passive-zone precedence, independently canceled cache
writes, actual caller cancellation, failed-save disposition, raw-error canary
suppression and the exact-path/license privacy exception. Both targets installed
the 24-distribution integration dependency closure and the explicitly prepared
Core startup requirements. All acceptance runs had their container networks
disconnected after dependency preparation. Owned configurations, containers and
private workspaces were removed successfully.

The [retained narrow receipts](RELEASE-1.0-CURRENT-LIFECYCLE.json) include independent artifact-digest,
ZIP CRC/member-byte, architecture pin, source, job and scope verification.
No raw test/Core logs, account credentials or owner configuration were collected.

## Scope

This establishes scripted Core process lifecycle in official QA containers.
It does not establish the ordinary consumer Container entrypoint, managed HAOS,
HACS delivery, a new upgrade/restore rehearsal, native Apple worker execution,
real-account participation, mobile/physical-display acceptance or stable release
approval. Historical native-worker results remain attached to their own unchanged
inputs and targets. The full backend suite was not repeated: the
[exact-source minimum-Core qualification](RELEASE-1.0-CORE-VALIDATION.md) already
passed 1,452 backend and 110 frontend tests. The
[compatibility disposition](RELEASE-1.0-COMPATIBILITY.md) tracks the remaining cells.
