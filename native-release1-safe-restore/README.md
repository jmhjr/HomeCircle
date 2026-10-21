# Exact C453 preview: explicit disabled-entry partial-restore witness

Prepared for review only. No VM, CI or product change was made by preparing this
folder. This is one fresh native amd64/KVM HAOS 18.3 guest, actual Supervisor/Core
2026.10.2 and CPython 3.14.6. The immutable input is canonical product source
`9bf03eb45d2cf43274074534e9dfe2de841f4011` (337 public source files), packaged as
614,209 bytes / 113 members, SHA-256
`c4530d94be3b2996f8d6c8948db88a51868566047d68558eefde7967f270a861`.
It remains an unreleased same-version `0.1.0-beta.20` preview.

This prepares a tested **explicit procedure**, not automatic anti-rollback.
Historical enabled B/C restores really rolled the local guard back from three
to two; those failures remain preserved and are not reclassified by this work.
The new workflow must require plain controller exit zero, all eight procedure
observations, the separate acceptance gate and complete owned cleanup. A green
diagnostic investigation cannot substitute for those facts.

## Narrow sequence

The exact phases are `initialize`, `initial_restart`, `quarantine`, `mutate`,
`automatic_disabled`, `repaired_disabled`, `reenabled`, `restart`.

1. Ordinary Core requirements install the exact six direct dependencies and
   verify the 24-package declared closure under actual current constraints.
   There is no dependency preloader, config-local cache/library, pip target
   override or skip-pip. A missing direct package before initial candidate setup
   is mandatory. A separate supported Core restart proves two distinct current
   managed processes before the backup exercise.
2. Real HomeCircle config/options flows create two fictional Persons with
   explicit trackers, nonempty options and one fictional selected place. A
   generated 2×2 PNG is added through Home Assistant's actual image-upload
   collection, then assigned through its Person collection. Actual image and
   Person module bytes must match the reviewed official 2026.10.2 source hashes.
   The fixture checks persistent image metadata, original file bytes, Person
   selection and an actual loopback HTTP image response. This is API fixture
   setup, not browser upload or user authentication acceptance. City lookup is off.
3. Disable HomeCircle through HA's entry API, wait for unload and actual storage
   persistence, keep Core/Recorder running and create one supported local
   uncompressed/unprotected Home Assistant partial backup including the database.
   Inspect the actual archive for exact C bytes, disabled entry, database and
   count-two old guard, with no stale automatic-boot barrier.
4. While the entry stays disabled, mutate settings and commit post-backup history.
   One more synthetic guard reservation/refusal creates three unresolved/rejected
   local observations and a block, with no pending/uncertain state. These are
   fictional local accounting outcomes; no recovery SDK or Apple proof is called.
   Stop Core and retain the newest guard privately on the controller host outside
   the entire guest. Export checks exact standalone product guard bytes and its
   actual API, bounded regular files, no links and private ownership/modes.
5. Close the sole named VM NIC before actual Supervisor restore. Supervisor's
   first automatically restored process must remain disabled/unloaded, with no
   candidate module imported, the same persisted snapshot and the exact old
   guard bytes. This inert observation precedes guard status queries, repair or
   enable. It is tied to backed-up generation/token/branch and a new process.
6. Stop Core, verify the old and independent host-newest fingerprints, then
   promote the newest guard with strict private bounds/modes/ownership. The
   temporary guest transfer file is placed in the restored private QA-control
   folder only after restore, maps correctly into Supervisor's `/data/homeassistant`
   mount and is removed after promotion. The authoritative copy remains on the
   host until cleanup. Start Core with the NIC still closed; require the entry
   still disabled, then verify actual guard API three/blocked, pending/uncertain
   zero. A missing/stale/tampered guard or failed transfer stops the procedure.
7. Only that repaired-disabled observation permits a guarded NIC reopen and
   explicit HA API enable. Normal Core requirements can reinstall system packages
   discarded when Supervisor recreates Core. A metadata/origin probe before
   enable records what is actually missing; no reinstall claim is inferred from
   an API reply. Enabled setup must satisfy ordinary system origins, active
   constraints, normal pip target, empty `/config/deps` and the complete closure.
8. Close the NIC again, restart Core and verify the new process, guarded state,
   all 113 installed/loaded files, actual HTTP-served card/image bytes, persistent
   selections/settings/place/picture and Recorder history. Exact pre-backup rows
   return; post-backup markers disappear; new post-restore committed rows survive
   the final restart. Owned resource URL/type must match throughout. Its ID may
   change when re-enabled; no difference from the old ID is required. Its actual
   persisted re-enabled ID must survive the final restart, and unrelated IDs
   remain intact. End with observed Core stop, QEMU stop and private host/guest
   workspace deletion.

The deliberate network history is **close → reopen after repair → close**.
Positive/negative TCP controls and responsive QGA are required; uninterrupted
isolation is not claimed. All deadlines, uncertain Docker states and cleanup
failures remain failures. No mutation is retried, including backup and restore.

Normal Core startup creates system Backup and Analytics entries, and Supervisor
supplies its system Hassio entry. The helper waits up to 60 seconds for their normal discovery
flows, then requires exactly one enabled system entry of each kind. At most one
synthetic user-source HomeCircle entry is permitted; its enabled/disabled state
is checked separately by each procedure phase. Foreign domains, user-source
system entries, disabled system entries and duplicates refuse. Diagnostics contain
only fixed domain/source-category counts and readiness booleans; no raw entry
names, titles, IDs or configuration data are exported. Analytics entry setup is
separate from analytics sharing consent; the fixture does not call preference or
onboarding APIs. No zero-request claim follows from this entry policy. The prior
run recorded one unknown system domain; it did not retain that domain's identity.

On a failed initialization inside `persistent_setup`, optional `setup_step`
contains only one of 25 fixed source labels. It distinguishes Person registry and
state waits, flow/options load, portrait state, resource/source/snapshot work and
the two existing HTTP waits. No response text, exception message, entity/entry
metadata, ID, URL, path or arbitrary label is retained. Other stages and successful
receipts do not gain this field. A timeout label identifies the active await
region, not its cause. The fifth negative receipt lacked this observation, so
its exact timeout remains unknown. The sixth negative receipt identified
`person_sources`, without showing which part of that predicate was false.

Only a failed initialization at `persistent_setup / person_sources` may add
`person_sources`: exactly two fixed indices (`0`, `1`), each containing six
strict booleans: `person_present`, `tracker_present`, `person_home`,
`tracker_home`, `source_matches_selected` and `configured_link_matches_selected`.
They read the current states and configured Person links in one event-loop turn
after the existing wait raises `TimeoutError`. No names, IDs, state strings,
coordinates, timestamps or link values leave the helper. If observation itself
fails, it is omitted and the original timeout is re-raised. Both helper and
host reject unknown fields and types and omit the object outside that exact
failure scope. Success receipts are unchanged. This diagnoses a failed wait;
it does not establish a cause or alter a fixture, predicate, deadline or
acceptance criterion.

The seventh negative receipt observed only the first synthetic Person losing
its configured selection while both trackers remained present and Home. The
pinned Person update schema defaults an omitted `device_trackers` field to an
empty list; its own picture-update code explicitly carries that list forward.
The QA portrait call now first requires the current selection to equal its one
expected tracker, then carries a copy of that current list in the picture update.
This fixes the confirmed QA API mismatch without changing product behavior,
tracker state, source/state waits or timing. It does not reclassify any prior
negative run or prove the full restore procedure.

## Exact runtime and reuse

The official machine reference is
`ghcr.io/home-assistant/qemux86-64-homeassistant:2026.10.2`. The controller requires
actual stored OCI index `45f009d6ff1061971102e81f0802cf2762bdd5c5007231c938bd36030cbd0a12`,
amd64 manifest `e2efc1351b54b15dd3232fc9987316aa3e3cb22c15e6e369e73fd595b4338f2c`
and config `e1acee126eee45b3007494ad7f806d12535dc7d733624b681ed29a505f8c2b98`.
All three actual stored objects, platform/config links and actual image RootFS
must match before candidate staging and after subsequent managed observations.
Core constraints must hash to
`7baa9a8f39ddeb9c5bb60a1036f6d5e33f4b84267f151f53cc2b95ef031a21b5`.
Actual CLI capabilities and executed binary identity are observed separately
from the CLI add-on image version.

This separate fixture reuses reviewed archive/backup/Recorder contracts from
historical 39452393848 and C's prepared restore investigation, plus the strict
normal requirements, Docker29 OCI proof, known/unknown container state handling,
QMP link controls and owned cleanup from successful minimum run 39504506480.
The parent folder records exact inherited function/byte comparisons and the new
procedure-specific changes. Historical folders and product source are untouched.

The picture API source references are official tagged Core:
[image upload](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/components/image_upload/__init__.py),
[Person](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/components/person/__init__.py).
The parent `official/SOURCES.json` retains their exact SHA-256 values; the helper
requires the same module hashes in the guest before creating the synthetic image.

## Contracts, privacy and limits

Ninety-five standalone contracts currently pass without skips. They include
strict input/archive/OCI/dependency/blank-config checks; actual phase nonce and
disabled automatic-boot barriers; old/new guard timeline, pending/uncertain and
early-enable/network refusal; private bundle links/modes/size-before-read;
Recorder/served/settings failures; allowed owned-ID reuse; fixed canary-safe
failure projection and plain procedure gate, plus actual-method dependency-probe
transfer and current-constraint pin regressions, and actual preparation through
an existing private workspace with missing/link/mode/owner refusals. The actual
system-entry predicate, delayed discovery readiness and finite count-only failure
projection are also tested, including the exact tagged Analytics system-flow
body and delayed Analytics readiness. Four further contracts execute the actual
Person/setup waits with injected timeouts, the actual guest failure body and
controller projection, and fixed-catalog privacy checks. Four more execute the
actual boolean observer with independent faults at both indices, both exact
projectors with malformed/private canaries, the unchanged wait and original
exception identity, and both actual failure paths across allowed/refused scopes.
They do not import HA, a native
provider or run a VM. The future workflow must bind every committed input before
imports and require exactly the reviewed contract count with zero skips.

Two further contracts execute the actual QA portrait call and exact tagged
Person `_update_data` body, with a clearly limited source-derived model of the
schema's default empty tracker list. They reproduce the old picture-only call
clearing the selection, verify the explicit current-list payload preserves it
and the second Person, and refuse missing, foreign or multiple selections before
any Person update. The complete probatio validator and HA lifecycle are not run
by these standalone cases; actual managed acceptance remains required.

Public output is exactly nine fixed JSON names on success: `host.json` and the
eight phase names. Raw backup/database/configuration, guard bundle/account hashes,
nonce, Person/resource URLs, files and logs remain private and are deleted with owned resources.
Only finite labels, aggregate counts, public version values and fingerprints are
projected. Request-attempt counts remain explicitly **unmeasured**: account-free
state and egress denial are not request instrumentation.

Success qualifies this explicit disabled-entry local partial procedure plus its
ordinary current-amd64 managed lifecycle. It does not qualify ordinary enabled
restore safety, automatic guard preservation, server allowance, authenticated
providers, full-system/add-on/encrypted/cloud restore, ARM restore, consumer UI,
HACS/RC transport or a stable release. Both providers remain in 1.0 scope and need
their separately documented authenticated acceptance. The transfer channel here
is QA-only; a maintainer-supported private administrator preservation procedure
must be documented before consumer instructions or stage-4 disposition. If the
latest intact guard is unavailable, leave HomeCircle disabled and preserve that
uncertainty; never reset counts or infer remaining Apple allowance.
