# Incomplete consumer Container and ARM managed pilots

These negative results qualify no consumer Container entrypoint or exact-preview
ARM managed startup/restart. The tested source is
`9bf03eb45d2cf43274074534e9dfe2de841f4011`; the intended candidate is the same
113-file `c4530d94be3b2996f8d6c8948db88a51868566047d68558eefde7967f270a861`
unreleased preview. Reaching a preparer or staging step does not establish that
HomeCircle loaded. Both direct providers remain in the intended 1.0 scope.

## Consumer Container: four incomplete pilots

The first three native Linux `current-amd64` pilots stopped at the preparer,
with zero consumer acceptance starts. The fourth reached one offline consumer
startup but refused before completing a service phase. None produced an accepted
first/restart phase. In all four runs the owned containers, named volume and
private workspace were removed without a cleanup failure.

| Run | Observed result | Limit |
| --- | --- | --- |
| [39502196796](https://github.com/jmhjr/HomeCircle/actions/runs/39502196796) | 14 preparation contracts passed; preparer refused. | The fixed reason was not retained. The underlying cause is unknown; a confirmed diagnostic-projection gap was corrected separately. |
| [39503727211](https://github.com/jmhjr/HomeCircle/actions/runs/39503727211) | 17 contracts passed; `cache_install` refused with `owned_child_descendants_not_reaped`. | An owned process group remained visible after the primary exited. The guard killed that group and refused; the record does not classify the descendants or establish installer success. |
| [39505904554](https://github.com/jmhjr/HomeCircle/actions/runs/39505904554) | 24 contracts, including seven actual Linux fork/process cases, passed with zero skips. `cache_install` refused with `cache_preparation_refused`. | The real primary exited 1. The subreaper adopted and reaped one child and drained owned descendants within the limits. The failed package and underlying installer error were not retained. |
| [39507545357](https://github.com/jmhjr/HomeCircle/actions/runs/39507545357) | 26 contracts, including seven actual Linux process/fork cases, passed with zero skips. The real installer exited 0, drained descendants without a deadline and reached one offline consumer startup. | The guest refused `guest_cached_distribution_origin_refused`, wrapped as `consumer_guest_failed`. No phase or restart passed. The predicate combines version equality and cache-root origin; the failed package and failing half were not retained. |

A separate source/anonymous-index check confirmed that the preparer omitted the
normal official Home Assistant wheel index. Five of 45 wanted pins lacked
eligible PyPI wheels while the official index advertised suitable wheels.
That is a confirmed preparation gap, not identification of the failed package
in an earlier run. The explicit official-index correction was then exercised in
run 39507545357 and its actual installer passed. The first consumer service still
refused the unchanged version/origin check; it did not complete acceptance.
A diagnostic-only follow-up is being prepared to identify the failing sorted pin
and safe version/origin category without relaxing that predicate. No exact package,
path-precedence cause, complete fresh consumer installation or compatibility pass
is inferred. Metadata availability is not runtime acceptance. The full backend
suite was not repeated by these pilots.

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

For both attempts the receipts record graceful owned shutdown, no force,
owned-VM deletion, private-file removal and no remaining owned process/listener.
The original VM inventory and inspected QA disk metadata were unchanged.
Uninspected original disk/snapshot contents are not claimed verified. The
readiness protocol for a future attempt must establish a positive read-only guest
transport observation before continuation; preparation alone is not a pass.

## Evidence and remaining disposition

[Machine-readable evidence](RELEASE-1.0-INCOMPLETE-PILOTS.json) preserves each
consumer run's exact independent verification, narrow artifact member bindings
and negative result. It also records byte/hash bindings and limited public
projections of the two local ARM host/failure receipts. Raw private logs,
credentials and owner configurations are excluded.

The actual [minimum-Core amd64 managed pass](RELEASE-1.0-MINIMUM-HAOS.md) and
[QA-container lifecycle checks](RELEASE-1.0-COMPATIBILITY.md) retain their separate
successful scopes. Consumer entrypoint acceptance and exact-preview ARM managed
acceptance remain open. These pilots used no owner/provider accounts, add no
native Apple-worker acceptance and grant no stable release approval.
