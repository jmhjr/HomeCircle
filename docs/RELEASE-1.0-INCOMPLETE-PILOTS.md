# Consumer, ARM managed and restore-procedure pilot evidence

Eight consumer and seven local ARM negative results remain preserved below,
alongside five incomplete restore-procedure runs. Subsequent witnesses passed
the original consumer entrypoint with prepared normal-config dependencies on all
four proposed native endpoint/CPU cells. Exact-preview ARM managed and restore
acceptance remain open. The tested source is
`9bf03eb45d2cf43274074534e9dfe2de841f4011`; the intended candidate is the same
113-file `c4530d94be3b2996f8d6c8948db88a51868566047d68558eefde7967f270a861`
unreleased preview. Reaching a preparer or staging step does not establish that
HomeCircle loaded. Both direct providers remain in the intended 1.0 scope.

## Consumer Container: eight incomplete pilots

The first three native Linux `current-amd64` pilots stopped at the preparer,
with zero consumer acceptance starts. The fourth through eighth each reached one offline consumer
startup but refused before completing a service phase. None produced an accepted
first/restart phase. In all eight runs the owned containers, named volume and
private workspace were removed without a cleanup failure.

| Run | Observed result | Limit |
| --- | --- | --- |
| [39502196796](https://github.com/jmhjr/HomeCircle/actions/runs/39502196796) | 14 preparation contracts passed; preparer refused. | The fixed reason was not retained. The underlying cause is unknown; a confirmed diagnostic-projection gap was corrected separately. |
| [39503727211](https://github.com/jmhjr/HomeCircle/actions/runs/39503727211) | 17 contracts passed; `cache_install` refused with `owned_child_descendants_not_reaped`. | An owned process group remained visible after the primary exited. The guard killed that group and refused; the record does not classify the descendants or establish installer success. |
| [39505904554](https://github.com/jmhjr/HomeCircle/actions/runs/39505904554) | 24 contracts, including seven actual Linux fork/process cases, passed with zero skips. `cache_install` refused with `cache_preparation_refused`. | The real primary exited 1. The subreaper adopted and reaped one child and drained owned descendants within the limits. The failed package and underlying installer error were not retained. |
| [39507545357](https://github.com/jmhjr/HomeCircle/actions/runs/39507545357) | 26 contracts, including seven actual Linux process/fork cases, passed with zero skips. The real installer exited 0, drained descendants without a deadline and reached one offline consumer startup. | The guest refused `guest_cached_distribution_origin_refused`, wrapped as `consumer_guest_failed`. No phase or restart passed. The predicate combines version equality and cache-root origin; the failed package and failing half were not retained. |
| [39509292483](https://github.com/jmhjr/HomeCircle/actions/runs/39509292483) | 31 contracts, including seven actual Linux process/fork cases, passed with zero skips. The installer again exited 0; one offline consumer start reached the bounded diagnostic. | Sorted pin index 0 is `aiohappyeyeballs`: observed 2.7.1 matches its pin, with resolved metadata at the reviewed system root and cache-first path order. The cache-only harness assumption refused it; why metadata selected system remains unknown. No accepted phase or restart. |
| [39510994867](https://github.com/jmhjr/HomeCircle/actions/runs/39510994867) | 33 contracts, including seven actual Linux process/fork cases, passed with zero skips. The installer exited 0 and preboot cache enumeration checked all 45 exact expected versions. One offline consumer start reached the bounded diagnostic. | Sorted pin index 4 is `anisette==1.2.4`: metadata was missing, observed version unavailable and expected-version match false, with cache-first path order. The guest projected `OtherError` and the outer fixed code was `consumer_guest_failed`. No accepted phase or restart; all owned cleanup passed. |
| [39513706335](https://github.com/jmhjr/HomeCircle/actions/runs/39513706335) | 39 contracts, including seven actual Linux process/fork cases, passed with zero skips. The installer exited 0; one offline consumer start ran the revised marker-preparation source. | The guest retained only `OtherError`, with no fixed code, distribution diagnostic or exercise substage; the outer code was `consumer_guest_failed`. The setup marker receipt was not retained. Cause unknown; no origin-check completion, accepted phase or restart is inferred. All owned cleanup passed. |
| [39515362247](https://github.com/jmhjr/HomeCircle/actions/runs/39515362247) | 45 contracts, including seven actual Linux process/fork cases, passed with zero skips. The installer exited 0 and drained descendants; one offline consumer start reached `resource_identity`. | The guest projected `KeyError` with `OtherError`; the outer fixed code was `consumer_guest_failed`. The missing key text was not retained. No accepted phase, restart or setup-marker receipt; all owned cleanup passed. |

A separate source/anonymous-index check confirmed that the preparer omitted the
normal official Home Assistant wheel index. Five of 45 wanted pins lacked
eligible PyPI wheels while the official index advertised suitable wheels.
That is a confirmed preparation gap, not identification of the failed package
in an earlier run. The explicit official-index correction was then exercised in
run 39507545357 and its actual installer passed. The first consumer service still
refused the unchanged version/origin check; it did not complete acceptance.
The fifth diagnostic-only run identifies a correct pinned system distribution,
confirming the exact-cache-only harness assumption is too strict. It does not
explain why system metadata was selected despite cache-first order or establish
the origin/version of the remaining 44 pins. The separately reviewed correction
accepts only exact pinned versions at either exact approved root and records
cache/system counts. Its sixth runtime check still failed before an accepted service phase; it
cannot reclassify the earlier failures. No complete fresh consumer installation or
compatibility pass is inferred here. The full backend suite was not repeated.

The sixth result prompted a separate confirmed preparation diagnosis. Exact
Core `config.py` treats a missing `.HA_VERSION` as 0.7.7 and removes the legacy
`deps` cache; `bootstrap.py` calls that upgrade before mounting the normal cache.
The synthetic preparer wrote custom configuration and dependencies but omitted
this marker. Actual extracted-function checks with temporary files reproduce
missing/old-marker cache removal and preservation with each exact Core target.
The narrow runtime record did not directly observe deletion. An exclusive
exact-target marker/readback correction and exact official source checks were
reviewed and exercised in the seventh single pilot. That run still failed before
an accepted phase, with an unclassified guest error; its setup marker receipt
was not retained. This grants no startup or compatibility pass.
All 45 required versions, approved metadata roots and consumer startup controls
remain strict. The sixth missing-package receipt does not identify later pins or
retroactively determine an earlier opaque failure's cause.
The seventh result records no exercise substage or original error category beyond
`OtherError`; its cause remains unknown. The eighth diagnostic-only pilot retained
`resource_identity / KeyError` without messages or resource rows. Exact tagged
Core sources at both endpoints transform resource creation's `res_type` into
stored `type`; the QA mapper incorrectly read the former stored key. Executing
that actual transformation on known-valid synthetic records reproduces the old
mapper's `KeyError`. A one-read correction preserves the semantic `res_type`
projection, with checks for URL/type changes, ordering and ID independence.
These pure checks use a schema stub and add no HA runtime pass. The actual
missing key text remains unobserved, and this source-confirmed defect does not
assign causes to earlier opaque failures. The correction subsequently passed
the following scoped current-amd64 pilot and three native followups. Fresh online
consumer resolution remains outside their prepared-cache scope.

## Scoped consumer followup: four native cells passed

[Run 39516737435](https://github.com/jmhjr/HomeCircle/actions/runs/39516737435),
at QA `efd83d36ae3d1b95c6cf5c73913023d34ca21a69`, passed all 47 zero-skip
standalone contracts, including seven actual Linux fork/process cases, then
completed startup, clean stop, restart and final clean stop through the
unmodified official Core 2026.10.2 amd64 consumer image. Native `s6-svscan` PID1,
the normal Core supervisor/CLI, mimalloc environment, exact startup files and
absence of import-path overrides were verified. The two Core process identities
differ across restart.

The exact 113-file C453 installation, loaded HomeCircle module origins and served
frontend matched. Two explicit synthetic Person/tracker selections, nonempty
options and entry/settings/source/resource URL-type fingerprints persisted;
resource-ID persistence is not claimed. The restart phase exercised integration
unload/setup. Setup retained the exact-Core marker readback and 45 prepared pins;
both phases resolved all 45 at the approved normal cache root (cache 45/system 0).
The actual installer exited 0 and drained owned descendants without a deadline.
Both containers were offline during acceptance; both containers, the owned named
volume and private workspace were removed with no cleanup failure.

Artifact 12308785057 is 4,616 bytes, SHA-256
`e5e0c728a7a204aa79c61bdf540e5306d46df97cd853d91342d7e5c7ef42e8c4`,
with exactly eight JSON receipts. Independent checks bound API/head/job identity,
ZIP size/digest/CRC/member bytes, all 19 committed fixtures, workflow/pins and
strict receipt projections. This qualifies the standard entrypoint with prepared
normal-config dependencies on current amd64. It adds no fresh online dependency
resolution, provider account/native worker, HACS, managed HAOS or stable-release
acceptance. No full backend or focused product suite was repeated. The eight
older negatives retain their original limits and causes; this pass does not
retroactively reclassify them.

The remaining three cells passed in one automatic matrix
[run 39517742934](https://github.com/jmhjr/HomeCircle/actions/runs/39517742934),
QA `ff0850d8acd8b6cf0c58ed6df79678e8eeae23c5`. Actual job names and native
runner labels, exact committed workflow and all 19 unchanged fixtures were
verified; the cached workflow display name was not used as identity.

| Target | Native runner | Narrow artifact / bytes | SHA-256 |
| --- | --- | --- | --- |
| Core 2026.9.4 / amd64 | ubuntu-24.04 | 12308069935 / 4,617 | `2040bd4b489789bbe057128cf005f2969e201e60ed6b20cd943c41393329e76b` |
| Core 2026.9.4 / ARM64 | ubuntu-24.04-arm | 12308407045 / 4,612 | `a8556c81116b77818ccbbe8596d98c5d1b017bb9205e12d67e4f9d1b25e6d243` |
| Core 2026.10.2 / ARM64 | ubuntu-24.04-arm | 12308169666 / 4,612 | `80d5e786a129f4bc77d1786740e743ffdbf16556ad5b52009b110bf5b3530b9d` |

Each target passed the same 47 zero-skip contracts, including seven actual Linux
fork/process cases, before two original-entrypoint service starts and clean
stops. All 113 installed bytes, loaded module origins, served frontend, explicit
selections, nonempty settings/source/resource URL-type continuity and restart
unload/setup passed. Marker readback and all 45 exact resolved versions passed;
each first/restart phase observed cache 45/system 0. Original s6/HA CLI, allocator,
startup-file and no-import-override proofs passed, as did offline acceptance and
all owned cleanup. The three jobs retain exactly 24 fixed JSON receipts.

Together the four scoped cells add eight service starts and 32 narrow receipts.
The 188 standalone-contract executions repeat the same 47-case harness on four
native targets; they are not 188 distinct product tests. No full or focused
product suite was repeated. All four witnesses use prepared normal-config
dependencies and grant no fresh online consumer resolution, managed HAOS,
provider/native-worker, HACS or stable-release acceptance. The eight older
consumer negatives remain preserved.

## Local ARM managed attempts: no accepted phase

The first owned ARM64/HVF attempt verified its fresh managed current-Core target
and stored OCI chain before candidate staging, then failed at `initial` with
`guest_phase_failed`. No accepted initial or restart receipt survived. Its helper
failure detail was not collected before cleanup, so the underlying stage/code and
cause cannot be reconstructed. A separate finite diagnostic projection/collector
correction was reviewed without guessing a product change.

The second fresh owned attempt failed at `continuation_preflight` with
`host_command_failed`, before candidate staging or any recorded managed Core
action. It produced no accepted phase. The exact API error was not retained;
launch timing does not prove the cause. These are two distinct negative attempts,
not a successful ARM compatibility witness.

The third fresh owned attempt passed its bounded read-only guest readiness
protocol after an earlier host-nonzero read, then failed at
`stopped_exact_candidate_staging` with `host_command_failed`. One managed stop
command was launched, but no completed Core action or accepted phase was
recorded. Readiness is a transport observation, not stop/start or candidate
acceptance. The exact later API error/cause remains unknown.

The fourth owned current-Core attempt passed its 49-action native-HVF bootstrap,
strict stored OCI content/layer checks and a positive readiness observation.
One managed Core stop/start completed, but the initial helper refused at
`entry_domains / qa_unexpected_entry_domain`, bound to its exact source/control.
The actual unexpected domain name was not retained; the underlying cause is
unknown. A separate confirmed fixture gap is that stock default configuration
storage was overlaid without the reviewed fresh-owned configuration reset. That
gap does not establish which domain caused the refusal. No initial/restart phase
was accepted. Its cleanup passed without force.

The fifth current-Core attempt performed the fresh owned reset: 24 files,
335,158 bytes and 13 children, with the mount retained and no owner/prior
candidate. The bootstrap recorded 49 host actions and retained an earlier
read-only failure while waiting for guest readiness. The continuation recorded
200 calls with zero read-only transport failures. Exact Core/Supervisor
2026.10.2, HAOS 18.3, native
HVF, stored OCI content and 22 layers were bound; one Core stop/start completed.
The initial helper still refused at `entry_domains / qa_unexpected_entry_domain`.
Its source-bound counts directly record Backup 1, Hassio 1, HomeCircle 0 and
other domain 1, with all three entries system-sourced. The actual additional
domain identity and disabled status remain unobserved. Zero phases were
accepted; fresh reset alone did not resolve this scope refusal. Private raw bytes
were unavailable after cleanup, and readiness age was not rechecked after
completion; retained controller hashes do not establish those deleted bytes.

The sixth current-Core preparation failed before starting its owned VM:
`preboot_export / exact_preboot_export_script_required / ValueError`. Exactly ten
host calls included one stopped owned import and one stopped owned deletion;
there was no VM start, export, network change, guest command, readiness receipt
or Core action. The frozen renderer used `preboot.utm` while its driver required
`preboot-readback.utm`, a source-confirmed QA preparation mismatch. No candidate
or helper phase ran. All four owned resource cleanup checks passed, without
force. A clean guest shutdown was not applicable because this guest never
started. The retained controller registry hash matches the original five;
raw post-cleanup registry output was not retained by that report. This is a
bootstrap-only negative result, with no product-runtime diagnosis.

The first separate minimum-Core ARM64 attempt selected Core 2026.9.4 from
2026.10.2 through one supported version request. The observed state was
`not_created`, followed by exactly one supported start; actual stored OCI content
and all 22 RootFS layers were bound. A fresh owned reset inspected 24 files and
retained no-owner/no-prior-candidate/mount-preserved proof. The controller recorded
317 host calls and four completed stop/start controls across selection and
candidate staging. The initial helper still refused
`entry_domains / qa_unexpected_entry_domain`, bound to source/control, without
retaining the unexpected domain. No phase or restart was accepted. This shows
that fresh reset alone did not avoid the entry-scope failure; it establishes no
product cause or minimum ARM compatibility pass.

For the five started current-Core attempts and first minimum-Core attempt, the
receipts record graceful owned shutdown, no force,
owned-VM deletion, private-file removal and no remaining owned process/listener.
The original VM inventory and inspected QA disk metadata were unchanged.
Uninspected original disk/snapshot contents are not claimed verified. The
readiness protocol for a future attempt must establish a positive read-only guest
transport observation before continuation; preparation alone is not a pass.

## Explicit restore procedure: five incomplete runs

The first account-free procedure run,
[39511219817](https://github.com/jmhjr/HomeCircle/actions/runs/39511219817), failed
in runner tool setup at the combined KVM read/write predicate, before the
79-contract suite or VM/procedure started. It produced no artifact. The exact
owner/mode and read-versus-write condition were not retained; firmware absence
is not established. A separate reviewed bootstrap correction added the
previously qualified runner access grant and independent device/read/write and
firmware checks.

The second run,
[39511882430](https://github.com/jmhjr/HomeCircle/actions/runs/39511882430), passed
that bootstrap and all 79 zero-skip contracts, then failed at
`disposable_configuration` with `guest_command_failed`. It accepted no helper
phase or procedure. The narrow receipt records the exact current Core image,
fresh synthetic reset and three completed preliminary Core controls
(stop/start/stop); those do not establish candidate installation or restore.
Read-only source review confirmed that preparation repeated an exclusive
workspace creation after the main path had already created that directory. A
separate correction checks the existing private directory, link status, root
ownership and exact mode instead. The original fresh creation remains required.
Exact guest stderr was not retained. QEMU stopped and private workspace cleanup
passed. Artifact 12305713938 is 2,662 bytes, SHA-256
`c716852e7e3264025125c6757a3ccea191c72fdc190f1483cfbbeeaa5006cd89`,
with exactly one `host.json` receipt.

The third run,
[39513194235](https://github.com/jmhjr/HomeCircle/actions/runs/39513194235), passed
all 80 zero-skip contracts and completed one byte-verified C453 installation plus
four preliminary stop/start controls. Initialization then failed with
`qa_only_owned_or_system_entries`; the host reported
`initialize / guest_acceptance_failed`, with zero accepted phases. Artifact
12306930911 is 2,915 bytes, SHA-256
`591f0028285f114188106e1943803938a69161a9fe5e189bc16bec53a0e7c689`,
with `host.json` and failed `initialize.json`. QEMU and private workspace cleanup
passed. No HomeCircle flow, guard exercise, backup or restore was accepted.

Both official Core endpoint sources confirm a legitimate Backup system entry
that the previous QA policy excluded. The started-event discovery dispatcher
also creates it asynchronously. A minimal reviewed correction requires exactly
one enabled system Hassio and Backup entry, allows at most one synthetic
user-source HomeCircle entry and rejects foreign/source/disabled/duplicate
cases, with bounded read-only discovery readiness and count-only diagnostics.
The old actual entry domains remain unobserved; this source-confirmed QA defect
does not identify which entry triggered an earlier runtime failure.

The fourth run,
[39515218270](https://github.com/jmhjr/HomeCircle/actions/runs/39515218270), passed
all 83 zero-skip contracts, installed the exact 113-file preview and completed
four preliminary stop/start controls. Initialization refused at
`system_entries_ready / qa_only_owned_or_system_entries`. Its finite projection
records Backup 1, Hassio 1, HomeCircle 0 and other domain 1, with all three
entries system-sourced. The legitimate pair is present; the actual additional
domain's identity remains unobserved. No phase, restore or guard exercise was
accepted. Artifact 12307388657 is 3,003 bytes, SHA-256
`79e95d91f306fba590f494b6513738666e0ddd6c09794cefc4bbc3a956df6abc`,
with exactly `host.json` and failed `initialize.json`. QEMU stopped and private
workspace cleanup passed. The Backup policy correction alone did not complete
the fixture; this result does not justify accepting arbitrary system entries.

Separate exact Core sources at both endpoints confirm that ordinary default
bootstrap also creates an Analytics system entry. The QA policy excluded that
normal domain. A minimal policy correction was separately reviewed and exercised in the fifth
run, with explicit source, count and enabled-state checks; arbitrary system
entries stay refused.
This source finding does not identify the actual additional domain or its
disabled status in the fourth restore run or fifth ARM attempt. No Analytics
consent, preferences, scheduling or product behavior is changed by preparation.

The fifth run,
[39517488285](https://github.com/jmhjr/HomeCircle/actions/runs/39517488285), passed
all 85 zero-skip contracts and its actual entry-scope/readiness gate: Analytics 1,
Backup 1, Hassio 1, HomeCircle 0 and other 0, all three system-sourced. These
counts were captured before HomeCircle creation; they do not describe state at
the later timeout or identify an earlier unretained OTHER domain.
Initialization then timed out at `persistent_setup / TimeoutError`, without a
fixed failure code or precise substep. That region covers Person/registry/state,
configuration and loaded/options waits, portrait/resource/source operations,
snapshots and active details. The exact await and cause remain unknown. No
product fix, deadline increase or acceptance relaxation follows from this result.

It installed the exact 113-file preview and completed four preliminary Core
controls, but accepted zero phases. Backup, guard transfer, restore, repair and
re-enable were not reached. Artifact 12309295933 is 3,004 bytes, SHA-256
`0ccc964faf393f923936cb8214d3b45dd26b44f4d6128d29cd953a767c8385a9`,
with exactly `host.json` and failed `initialize.json`. Independent checks bound
all 16 published inputs, actual source/control provenance and the unchanged
procedure gate. QEMU stopped and private workspace cleanup passed.

All five results remain negative. The procedure gate rejects the incomplete
second through fifth receipts. New preparation or a running followup adds no
accepted restore result.
Ordinary enabled-restore safety, automatic antirollback and stable-release
approval remain false, and provider request-attempt counts remain unmeasured.

At this checkpoint the newer current ARM attempt 7 and minimum ARM attempt 4
profiles are prepared and unrun. Their preparation adds no runtime acceptance.

## Evidence and remaining disposition

[Machine-readable evidence](RELEASE-1.0-INCOMPLETE-PILOTS.json) preserves each
consumer run's exact independent verification, narrow artifact member bindings
and result, including the later scoped consumer pass, plus the five incomplete procedure records. It also records byte/hash bindings and limited public
projections of the six current and one minimum ARM host/failure records, including the third readiness record. Raw private logs,
credentials and owner configurations are excluded.

The actual [minimum-Core amd64 managed pass](RELEASE-1.0-MINIMUM-HAOS.md) and
[QA-container lifecycle checks](RELEASE-1.0-COMPATIBILITY.md) retain their separate
successful scopes. The prepared-cache consumer entrypoint scope is complete across four cells;
exact-preview ARM managed acceptance and broader release gates remain open. These pilots used no owner/provider accounts, add no
native Apple-worker acceptance and grant no stable release approval.
