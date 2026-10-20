# Installed integration notice witness

Verified October 20, 2026 against the exact development preview, source
`9bf03eb45d2cf43274074534e9dfe2de841f4011`, ZIP SHA-256
`c4530d94be3b2996f8d6c8948db88a51868566047d68558eefde7967f270a861`.
This closes the integration-package notice-presence check. Source, distribution
and service-use dispositions remain in the [release plan](RELEASE-1.0-PLAN.md).

The [managed HAOS run](RELEASE-1.0-HAOS-RESTORE.md) checked every installed
non-bytecode package member against the canonical 113-file inventory in all six
phases. The whole installed inventory, encoded as sorted compact JSON, has
SHA-256 `823ce2f1c0447687d70f9da20c98ee59c920c158048d20c8c139c0747c60e69b`.
Each retained phase receipt has this same digest and count. Recomputing it from
the [pinned preview inventory](https://github.com/jmhjr/HomeCircle/blob/3dca89da40ce6478b2d793ace7af6146ffed0e5a/native-release1-minimum-core/payload/inventory.json)
independently bound these installed notice members:

| Path inside the installed HomeCircle directory | Bytes | SHA-256 |
| --- | --- | --- |
| `_vendor_findmy/LICENSE.md` | 3,784 | `f18c0397abd455385e63fc78f33860b61f19b762d5e82115dd6bef8fd3c9d1d0` |
| `_findmy_runtime/LICENSE.md` | 20,800 | `d0d08d053daacc07d9357fbdae0fefb972eec9ae6a14cada17695d6f5c1f28e4` |

The first retains the inherited FindMy/OpenTagViewer notices and the corrected
GrandSlam text. The second supplies pinned Unicorn native-core COPYING and
Construct notice text with its provenance and unresolved-obligation notes.
Their installed bytes equal the reviewed correction, not an invented replacement
notice. [Narrow phase receipts](RELEASE-1.0-HAOS-RESTORE.json) retain the aggregate
proof; the inventory identifies each exact path and hash.

This verifies supplemental notice material inside HomeCircle's installed
integration directory. It does not repair the fetched dependency wheels'
individual notice layouts or settle bindings attribution, corresponding-source,
origin/permission, installer-agreement, service-use or branding questions.
The [provenance audit](BETA20-READINESS-PROVENANCE-AUDIT.md) and
[dependency inventory](BETA20-DEPENDENCY-INVENTORY.md) retain those separate
findings. The published beta 20 archive remains unchanged; this result belongs
to the unreleased 113-file preview.
