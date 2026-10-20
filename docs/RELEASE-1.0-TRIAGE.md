# HomeCircle 1.0 roadmap follow-up triage

Reviewed October 20, 2026 against the isolated product candidate based on
`9466eef45ecac16f05f25d4455d705383f7c91ff`, including the separately reviewed
picture-filename correction. Four remaining beta 18 roadmap cases were inspected.
Two areas with confirmed implementation defects now have focused corrections;
the other cases retain their existing documented behavior and policy scope.
No provider/account requests or Home Assistant runtime were started for this
review. Source anchors below refer to the corrected isolated candidate.

| Case | Disposition | Result / remaining qualification |
| --- | --- | --- |
| Fresh GPS sources disagree and alternate | Existing selection rule; possible future policy refinement | Verified report times rank selected GPS sources, with HA's active selected source preferred within 60 seconds. No new hysteresis or blending proposed. Field accuracy remains acceptance work. |
| Passive zone in legacy pending-zone fallback | Confirmed defect; corrected | The fallback could classify a Person Home using a passive residence. The geometric fallback now skips passive zones, matching the default GPS path. Explicit HA Person membership keeps precedence. |
| Cached city projection GPS eligibility / cache retention on disable | Existing behavior plus deferred policy questions | Outbound lookup requires GPS; local cached projection can serve a selected usable non-GPS source at the same cell. Disable stops lookup-result projection and new transmission, while retaining local cache as disclosed. No policy changes made. |
| Disk-save cancellation during close/shutdown | Confirmed canceled-child cleanup and raw-diagnostic defects; corrected | Independently canceled save tasks no longer cancel integration unload. Owned work is drained, then true caller cancellation is propagated. Non-raising shield outcomes avoid raw storage-error diagnostics. Actual HA shutdown scheduling remains separate runtime validation. |

## Fresh GPS selection and oscillation

`normalize.py:346–384` ranks only explicitly selected available GPS trackers with
usable coordinates and verified source-report timestamps. It never substitutes
an HA update timestamp for a new GPS report. The newest fresh report normally
wins; `normalize.py:375–380` prefers HA's active selected source when it is within
60 seconds. This rule is described in `strings.json:59` and `strings.json:573`.

With two disagreeing fresh sources five seconds apart, alternating the HA active
source produces A → B → A. The pure-source probe confirms this, and the sequence
follows the disclosed rule. This review found no violated selection contract.
Holding a previous source, combining sources or adding disagreement thresholds
would be a new policy requiring explicit product criteria and field evidence.

Existing tests cover the stale active source losing, near-tie active preference,
unknown age/poll updates, unselected/non-GPS exclusion, all-stale fallback and
future report rejection (`tests/test_normalize.py`, tests named
`test_default_freshest_gps_beats_stale_ha_source_and_keeps_person_identity`,
`test_freshest_gps_near_tie_prefers_selected_ha_source`,
`test_freshest_gps_ignores_poll_updates_unknown_age_unselected_and_non_gps`,
`test_freshest_gps_all_stale_follows_person_without_claiming_freshness` and
`test_freshest_gps_uses_per_source_timestamp_sensor_and_rejects_future_time`).
Exact 60/61-second and repeated disagreement sequences are useful additional
acceptance cases if selection policy changes; they are not a reason to add a
new behavior for 1.0 now.

## Passive-zone fallback correction

The default geometric path already excluded passive zones
(`normalize.py:387–406`). The legacy `membership()` pending-zone fallback did
not. With explicit `tracker_selection=ha_person`, Person and selected GPS both
`not_home`, matching recent coordinates with known accuracy wholly inside one
selected passive residence, the old fallback returned that residence and the
Person counted Home. Passive geometry could also make an otherwise unique
active-zone match appear ambiguous.

The correction adds only `zone.attributes.get("passive")` to the fallback's
existing exclusion checks (`normalize.py:321–331`). It does not change accuracy,
freshness, chosen-source selection, explicit `in_zones` precedence, legacy Home
state, or selected-zone scope. The new
`test_legacy_pending_gps_skips_passive_residence_but_keeps_explicit_person_state`
at `tests/test_normalize.py:149` verifies passive residence stays Away, an ordinary
active residence still produces pending Home, and explicit Person membership
continues to produce Home even for the passive zone. Existing tests
`test_recent_gps_well_inside_new_zone_counts_as_home_while_ha_is_behind` and
`test_default_gps_zone_matching_uses_ha_accuracy_and_skips_passive` remain unchanged.

The actual new test body failed against the old implementation in the pure-source
probe (`roadmap-triage/before.json`, exit 1) and passed after the correction.
The probe supplies synthetic State/time/distance boundaries; full pytest with
real Home Assistant is required on the consolidated Linux candidate.

## Cached-city eligibility and retention

`city_lookup.py:162–182` requires an explicitly selected usable outside-place
position whose current source has `source_type=gps` before transmitting any
coordinates. `api.py:151–193` separately permits a cached street/city at that
point for a selected usable source without rechecking `source_type`. A synthetic
non-GPS source with an already populated same-cell cache projected the cached
city and made zero lookup requests. This is local reuse, not a new coordinate
transmission. Requiring GPS for that local projection remains a policy choice;
no missing authorization or outbound-GPS bypass was demonstrated.

Disable prevents scheduling/update (`city_lookup.py:151–165`) and cached lookup
projection (`api.py:163–167,187–188`). It leaves provider-reported address fallback
and local cache intact. The options description (`strings.json:783`) and
`docs/PRIVACY.md:61–63` disclose that retention and the distinct Private map tile
setting. Integration removal deletes the store (`__init__.py:332`). Existing
tests cover disable/projection, never transmitting non-GPS coordinates and
integration-removal cleanup (`tests/test_city_lookup.py:81,152,228,275,292`).

The cache's seven-day/256-entry bounds apply when `prune()` runs
(`city_lookup.py:124–149`). Expired records are excluded from loaded/projected
memory; physical disk erasure occurs with a later store write or integration
removal. There is no dedicated timer that purges a dormant disabled store.
Do not describe this as guaranteed physical deletion exactly seven days later.
Deleting on disable, rounding outbound coordinates and excluding members hidden
from Everyone would change the disclosed policy; no implementation change was
made here. A direct non-GPS cached-projection regression and disk-retention
acceptance would be needed if those policies change.

## Canceled disk child and caller cancellation

`save()` already shielded its disk write, and the
existing ordinary close test proved normal unload waits for it. However, if
that child write was independently canceled, old `close()` propagated its
`CancelledError` even with the close caller's cancellation count at zero. Since
`async_unload_entry()` awaits city close before provider/activity/frontend
cleanup (`__init__.py:283–315`), this conditional path could abort later cleanup.
The first update-task cancellation handler could also absorb cancellation of
the caller instead of reporting it.

Corrected `close()` (`city_lookup.py:250–281`) shields/drains both owned await
sites, treats an independently canceled child as finished, records true caller
cancellation, and re-raises it after draining. Existing suppression of ordinary
disk-save `Exception` remains exactly as before; the lookup is already closed.
No new I/O-error swallowing or retry policy was added.

A separate CPython 3.14 diagnostic problem was also confirmed: canceling an
outer shield while its inner disk task later fails could send the raw storage
exception to the loop's exception handler even when it was subsequently drained.
The initial cleanup correction still reproduced this pre-existing behavior.
The final `save()` (`city_lookup.py:239–248`) and both close drains now shield
`gather(..., return_exceptions=True)` outcomes, following the recovery guard's
existing local pattern. `save_task` still refers to the actual write. Direct
`save()` callers still receive the identical original exception; close explicitly
keeps its previous ordinary-I/O disposition. No global logger or loop-handler
suppression was added to product code.

Focused tests in the existing `tests/test_city_lookup.py` are:

- `test_close_waits_for_inflight_disk_save` (existing normal-drain control).
- `test_close_handles_independently_cancelled_disk_save`, before close and while
  close is waiting (two new cases).
- `test_close_preserves_caller_cancellation_after_draining`, during update and
  disk-save awaits (two new cases).
- `test_close_preserves_failed_save_cleanup_disposition` (one new case).
- `test_cancelled_city_save_failure_has_no_raw_loop_diagnostic`, with and without
  close-caller cancellation (two new cases). A synthetic storage-error canary
  must not reach the loop's exception handler; direct save must still raise the
  original error object.

`roadmap-triage/city-before.json` records both old independent-child failures,
caller cancellation being absorbed, and the preserved ordinary-I/O disposition.
`roadmap-triage/after.json` records normal independent-child completion, caller
cancellation after save drain and unchanged I/O behavior. Eight actual city test
bodies, including their parameter cases and the existing control, also pass in
the bounded pure-source harness with synthetic HA task creation. This does not
prove that a real HA shutdown independently cancels the save first or qualify
all shutdown timings. Root's real Linux Core run remains the runtime gate.

`roadmap-triage/shield-canary-before.txt` retains the CPython 3.14 regression
failure at the raw-diagnostic assertion before outcome shielding.
`roadmap-triage/after-python314.json` records eight extracted city cases passing
on native CPython 3.14.7; `after.json` records the corresponding 3.13.2 result.

An initial expanded probe was stopped while its deliberately blocked synthetic
write remained unreleased. The corrected harness releases that fixture and has
a five-second overall bound; this harness synchronization correction is not
evidence of a measured Core shutdown hang.

## Patch identity and validation boundary

The four runtime/test files below are the only additional product-source edits
made by this roadmap triage. `roadmap-triage/changes.json` retains the same hash
record. The separate picture fix is outside this table.

| File | Before SHA-256 (9466eef source) | Corrected SHA-256 |
| --- | --- | --- |
| `custom_components/homecircle/normalize.py` | `4dba58520c5252dc7ca48cac79df33ad4aec3b4404726bc5373b45078a5ac43d` | `e62fb2c583d3227ba70a2bd4771ef564bcd99be4993e0d2cf3ffcf5fb2ceeaf4` |
| `custom_components/homecircle/city_lookup.py` | `18ca5d48327fe0017ac2a6026a3dc9974b50ea18845c40b8c9a90edd1bc87b4c` | `cc3abdc01503d7e4ba1c1ab747c4d24d03dcc6167d467c4e170e5c56be1490e0` |
| `tests/test_normalize.py` | `3d14ebf48988d4d807cd175b91a2269cca797845f22bf46c50c35557a0425dd3` | `da1b71af11bb8b7946b1050d75fcf64594550512120456d85eda342de96a0c69` |
| `tests/test_city_lookup.py` | `b219400e7781ba9fb3e9c73b2eb742cf76fe92fd7f82c53bc91a2ec1656a4c1d` | `9a3849ac88c27e9e0fe5be3dcdc7fc928f1cb8b7125cd3d20c68ec2669549967` |

All four files pass native Ruff checks and format checks. Pure-source probes ran
with Mac Python 3.13/3.14 and standard-library boundaries only; they imported no Home
Assistant or native provider/emulator dependency. No version, package lock,
provider scope, published artifact or production installation was changed.
Full real-Core regression and independent review remain required before this
candidate's runtime corrections are accepted for release.
