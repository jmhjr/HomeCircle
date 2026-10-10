# Current candidate and October 8–10 change record

This consolidates the recent HomeCircle work and all current source changes since the last committed baseline. The dated implementation log begins October 9; no separate October 8 milestone is asserted. This candidate is packaged as beta 17; the previously published beta 16 archive remains unchanged. Historical checks in other documents apply to their dated builds.

## Implementation inventory

| Area | Current behavior | Source and validation |
| --- | --- | --- |
| Tracker reconciliation | Keep configured Person links, active source and explicit HomeCircle selections distinct. Explain conflicts, withhold conflicting positions, preserve source-specific report times and simplify provider labels to Home Assistant/Life360. | `normalize.py`, `selection.py`, `api.py`, card model; normalization, conflict and restart regressions |
| Person settings | Details edits HomeCircle selection without changing HA Person links. Explicit Assign/Add links remain supported and are disclosed on review. YAML-managed Persons can retain unlinked selections. | `config_flow.py`, translations; real UI-created and YAML Person flow tests |
| Person Details | Long press and a visible details action open source evidence, report/update times, troubleshooting, HA history and settings. Refresh details reads HA data. Dialog scrolling, focus and closing behavior are covered. | `member-dialog.js`, `settings-dialog.js`; member detail and lifecycle tests |
| Settings lifecycle | Cancellation handles late flow creation and translation loading. Back cannot create overlapping replacement flows or replace a pending Continue. | `settings-dialog.js`; lifecycle and permission tests |
| Home screen | Clearer map totals, hidden/missing positions, low-battery emphasis, charging suppression, quieter stale styling, compact spacing, non-redundant place labels and an outlined kiosk icon. | Card/model/styles; browser checks and recorded participant acceptance |
| Reported address | Outside defined places, show the address supplied by the exact usable map tracker, with stale/unverified wording. No geocoding request is added. | `normalize.py`, `model.js`; address and source-provenance tests |
| Map interaction | Street/Satellite switching, browser-local background, centered-pin zoom, a dark-blue zoom pill, person focus at overview plus three levels, empty-category preservation, draggable height, compact footer and the Street/Radar/Satellite pill. | Card/styles; real Leaflet lifecycle regressions, preview/browser checks and earlier participant acceptance |
| Map continuity | Coordinate updates move markers without refitting or stopping animation. Selection changes and the recenter icon fit the selected positions. Temporary connection failures retain last received data with a warning; permission failures clear it. | `card.js`; moving-marker, recovery, reconnect and authorization tests |
| Location requests | Opt-in Home Assistant phone requests, bounded selected-person checks, and explicit compatible Life360 family refresh. Successful dispatch does not establish delivery or a new GPS fix. | `location_requests.py`, `selection_refresh.py`, `family_refresh.py`, provider adapter and API; permissions, failure, concurrent reservation, source-switch and restart tests |
| Current request policy | Per-tracker requests share persisted 50-attempt rolling 24-hour budgets. Family refresh has a separate persisted 50-attempt Circle budget. Deliberate cooldowns are one minute. Automatic phone attempts wait at least 15 minutes and pause after three unanswered automatic attempts; pause state persists separately from the daily budget. | Request modules/runtime/translations; exact boundary, silent-phone 90-minute, failed persistence and real-entry reload tests |
| Recent activity | Locally retain observed status, source and freshness changes plus request outcomes, limited to seven days/100 events per member, with at most 25 freshness entries. Display latest five with expansion. Preserve permission boundaries, observation-session gaps and persistence failure feedback. | `activity.py`, runtime/API/dialog; storage, permissions, cleanup and separate-process checks |
| Radar | Opt-in IEM NEXRAD observed mosaics and HRRR prediction frames. Past 30 minutes uses five-minute steps; Future two hours uses 15-minute steps. Show local dated frame times and forecast model initialization. Default opacity is 40%; opacity/legend controls are optional browser-local settings. | `radar.js`, `weather-frames.js`; pinned URL/time, buffering, forecast validity and cleanup tests |
| Radar recovery | Remove layers before clearing Leaflet listeners to prevent blank tiles on subsequent zoom. Clear cached times on toggle, fall back to untimed imagery on metadata failure, refresh on visibility resume, recheck expired metadata and rebuild future frames. Preserve visible radar until an animation frame is ready. | Radar/card lifecycle regressions; synthetic preview and earlier live Safari radar/zoom checks |
| Field tooling | Private state retention, optional coordinate projection, explicit gaps, source/update/report provenance, offline transition analysis and synthetic capture-to-report rehearsal. | `retain_field_states.py`, `analyze_field_capture.py`; capture, analysis and rehearsal tests; [field protocol](IPHONE-FIELD-TEST-PROTOCOL.md) |

## Current validation and deployment

- 234 Python tests passed in the pinned Home Assistant environment; 86 frontend tests passed against the built card.
- Ruff, frontend formatting, public-file privacy guard and whitespace checks passed.
- The isolated packaged Core install, upgrade, restart, removal and post-removal restart checks passed, preserving unrelated resources.
- All 25 integration archive files match the current live installation. The served card hash, healthy six-member snapshot, diagnostics and location-request fields were verified after the planned restart. The recenter icon refinement required no second restart; the subsequent refresh/activity patch uses a planned backend restart.
- HomeCircle settings and unrelated dashboard resources were preserved. Request counters were not reset. The private field recorder retained its original end time and was given a new package/card baseline; restart and recording boundaries must be treated as gaps.
- The participant confirmed “All pass” on the physical DAKboard for the latest feedback/activity patch. Live Safari/API checks confirmed one family request, fixed completed outcomes, automatic clearing, and bounded activity with significant events retained. Earlier physical acceptance remains attached to its dated builds in [release readiness](CURRENT-RELEASE-READINESS.md). The iPhone-only trip remains open.

Current archive SHA-256: `f37e304d85aad6e302b2d37e64e4d8f20d91bdacd2c1bd3db3df709887c36359`.

## Independent review and next work

Claude Opus 5.5 reviewed a sanitized current-source snapshot with read-only tools. It did not execute tests or inspect private field records. The reviewer findings about silent Person linking, automatic request exhaustion, coordinate-driven map resets, radar time recovery, temporary snapshot failures and opacity during buffering were checked against source and addressed in the current patch.

Family-refresh outcomes are now latched only during the two-minute observation window, then frozen. Completed or failed feedback expires after five minutes without resetting budgets. State and periodic observers collect outcomes even without an open dashboard. Freshness activity is capped at 25 entries and evicted before other events at the 100-event limit. Remaining suggestions include improving touch/accessibility and radar disclosure in the editor, and clearer person detail wording. They are not all implemented merely because they were recommended.

Adaptive stale reporting is proposed, not enabled. A bounded rolling history of 30–50 natural reports per tracker/context could support a recommendation; ten reports would be low confidence. Avoid learning outages or forced-refresh behavior as normal, retain a fallback, cap changes and allow an override. A longer Life360 at-home threshold remains provisional; the people cutoff is still five minutes. HA entity timestamps do not substitute for a genuine GPS fix time.

A combined-source departure/return was observed, using retained Life360 times as reference rather than participant-confirmed physical event times. Sleep/recording gaps prevent exact HomeCircle delay claims. This does not complete the iPhone-only field test, which remains open. Raw states, precise times/coordinates, capture/proxy artifacts, credentials, backup configurations and screenshots remain private and are not publication inputs.

No stable release is approved. Source publication on the development branch does not replace a HACS prerelease or its assets.
