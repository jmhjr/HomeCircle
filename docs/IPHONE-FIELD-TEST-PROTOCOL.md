# iPhone departure and return field test

Use the next ordinary trip with the currently selected HA Person, Home Assistant phone tracker and Life360 tracker. Keep Person associations, HomeCircle selections, zones and automatic-request settings unchanged. This is a combined-source test; it cannot prove iPhone-only behavior when Life360 remains selected.

## Before the trip

Verify a recent successful private capture sample, expected selected/active sources, and capture deadline. Keep the recording Mac awake, running and connected to Home Assistant through the return. Check that the participant takes the tested phone. Note its current Location permission, Precise Location and Low Power Mode settings if available; record them without changing the baseline. Do not restart HA, update integrations, edit zones or request a location update just to improve the test result.

The current capture is bounded to the original 48-hour window. A recorder restart must preserve its absolute deadline. File cleanup runs only at recorder startup for its own files older than seven days. Capture is a private developer tool, not a shipped HomeCircle history feature or a background service guaranteed to survive Mac shutdown.

## Participant observations

After the trip, provide approximate physical departure and return times in Central time, to the nearest minute when possible. Record whether Home Assistant Companion or Life360 was opened, either app was refreshed, a manual location request was sent, phone location/energy settings changed, or the phone restarted. Note any known connectivity loss. These observations establish ground truth and identify manual intervention; app history alone does not establish them. If a dashboard is observed, note its time and displayed status/source rather than continuously operating it during the trip.

## Automated private evidence

Schema 2 records:

- Person, phone and cloud state categories; configured Person associations and active source mapped to anonymous slots.
- HA last-changed, last-updated and last-reported timestamps separately; tracker-supplied last-seen separately. Missing timestamps remain missing. A new HA update is not automatically a new GPS fix.
- Source and tracking types, GPS accuracy, numeric speed without guessed units, battery and driving attributes; configured supporting sensor values with update times.
- Membership in explicitly configured zones using anonymous aliases; selected-zone availability, radius and passive status. Zone and tracker coordinates remain opt-in and private.
- Normalized presence, conflict flags, map presence/origin, focusability, map visibility, full and compact source labels, evidence freshness/report status, driving status, counts, and location-request status/attempt/next-request times.
- Per-source sample times and snapshot time to expose sequential read skew; missing/read-failed trackers without discarding other successful reads. Failed normalized snapshots retain source evidence. Whole-capture failures remain explicit gaps.
- Integration version, installed card checksum and a settings checksum in the start record, so evidence is tied to its baseline.

Successful rounds are retained about every 15 seconds; requests and read failures can lengthen this. Short transitions may be missed. Reads are sequential, not atomic. Sleeping/offline/stopped capture creates unobserved intervals; no route or exact transition time should be inferred through a gap. Unknown places are categorized, unknown zone IDs are mapped to `other`, and unused attributes are omitted. These records support richer reduced replay, not an exact copy of HA state or rendered pixels. Source labels may contain member names. No raw responses, addresses, portraits, credentials or unrelated family history are saved.

## Analysis and acceptance

Compare physical observations with the first recorded phone, Person, Life360 and normalized transitions. Report source-to-source and physical-to-recorded delays as measured bounds, with sample skew/gaps stated. Inspect brief Home/Away alternations independently from persistent mismatches; do not invent a timing threshold after seeing results.

Check that Person presence remains authoritative, conflicting map points are withheld, active GPS source and card provider labels agree when verifiable, stale reports remain labeled stale, missing sources recover, and Home/Driving counts and primary-home focus remain consistent. Distinguish automatic location requests, a later HA tracker report and a genuinely new tracker-supplied GPS report. A request does not guarantee a fresh fix.

If the phone stays Away while Person remains Home, investigate exact configured associations, active source, zone membership, freshness and GPS accuracy before changing settings. If Life360 supplies the active position throughout, report successful combined-source behavior and leave isolated iPhone background tracking unproven. Physical DAKboard acceptance is a separate UI check.


## Generate the post-trip report

Use `scripts/analyze_field_capture.py` offline against the private capture directory. It accepts optional `--departure` and `--return` physical observation times in ISO format with timezone, plus `--uncertainty-seconds` (default 60 for approximate observations). The Markdown and companion JSON outputs are owner-only. Coordinates and raw source payloads are omitted from the report. Keep outputs under ignored work; do not publish participant observations or captured source labels.

```sh
work/ha-venv/bin/python scripts/analyze_field_capture.py \
  --records work/field-state-capture/records \
  --output work/field-state-capture/reports/post-trip.md
```

Add the physical times after the participant supplies them; do not invent times from tracker history. Inspect all brief flips rather than accepting the first matching event as a stable transition. Delays are intervals that include both sequential-sample uncertainty and the supplied physical-observation uncertainty. Gap-crossing or missing-source transitions do not receive bounded-delay estimates. Malformed records are flagged and break continuity. Sample counts are not durations, and no observed trip means no departure/return acceptance.


## Automatic-request interpretation

Opt-in requests apply only when the selected Home Assistant Mobile App tracker supplies the normalized location. With Life360 as map source, this feature does not request the selected iPhone. Eligibility follows 15 quiet minutes using HA last_reported (or last_updated fallback); a 30-second periodic check can dispatch later. Automatic attempts are at least 15 minutes apart and pause after three unanswered automatic attempts until a later HA tracker report. The pause persists separately from the 50-attempt rolling 24-hour budget; deliberate requests retain their one-minute cooldown. Reservations are persisted before dispatch. Failed sends consume the cap; failed limit persistence prevents sending. A restart preserves the cap and labels the response to an earlier attempt unverified.

“Last request attempted” does not confirm phone delivery. “A later tracker report arrived” establishes an HA report after the attempt; it does not establish that the request caused it or that GPS coordinates/report time are new. Compare the separate tracker-supplied GPS timestamp, HA report time and recorded request outcome. These behaviors were tested with synthetic data; no real requests were sent as part of tonight's review.

## Selection-triggered checks

Selecting a stale person card now triggers a bounded check of its exact map source. HomeCircle-owned Life360 checks read cloud reports; external Life360 trackers can receive an update request through their installed integration action, and an opted-in Home Assistant phone source can receive a location request. Phone and external Life360 requests use persisted one-minute/50-per-day limits. During the ordinary passive departure/return observation, leave the dashboard in overview and avoid selecting stale person cards. If a selection is made, note its time and displayed feedback so it can be distinguished from an unprompted phone report. The private capture now retains the last selection-check time, trigger and outcome alongside the existing phone-request status. Only a newer report from the same source confirms newer evidence; a source switch or successful request dispatch does not establish a new GPS fix.

The Recent activity section in person Details now provides a second, HA-hosted record of normalized status, map-source and freshness changes, automatic request attempts and selection-check outcomes. It starts at feature activation and survives restarts, marking each new observation session. Retention is seven days or 100 events per member; saved-configuration changes reset it. It contains no coordinates or routes and does not replace participant-confirmed departure/return times or the private field capture. Opening Details/Refresh details only reads saved observations; leave Everyone selected for passive observation.

October 9 prompted family-refresh comparison: one command per exact selected Life360 source using existing gates/limits; participant A/participant B/participant C requested, participant D fresh, participant E cooldown. participant C produced newer reports within two minutes; participant A/participant B did not. A later user-confirmed Life360-opening phase showed newer reports for all five without further commands. The private comparison files record these intervention windows; exclude them from passive-trip claims. Existing source settings and recorder deadline were preserved. Persistent request reservations from the test remain subject to the existing rolling cooldown/caps. Native phone request and exact app-opening time were not captured.

October 10 authorized Circle-refresh comparison: Life360 closed on participant A's iPhone; 301.9-second quiet baseline, one accepted native Circle `smartRealTime/start` request with `requestTrace: false`, then 121.1-second observation. Four of five selected Life360 sources supplied newer report timestamps; participant A did not. Exclude the prompted comparison interval retained in private evidence from passive-trip claims. Exact source associations, HA refresh reservations, tracker settings and ordinary recorder setup were preserved. Private evidence: `work/circle-refresh-comparison.json`. No new GPS fix or all-member freshness was established.

The new explicit Refresh family locations action is another prompted intervention. Avoid it during passive trip observation; if used, record the click time and Updated/Unchanged outcomes. Requests affect the entire selected Life360 Circle and share persisted caps with per-person requests. Implementation activation required Home Assistant restarts; treat restart gaps and Person fallback as observation-session boundaries, not departure/return events.

October 10 current policy supersedes earlier request limits: individual and automatic requests share a per-tracker 50-attempt rolling 24-hour cap; deliberate requests have a one-minute cooldown, while automatic requests now wait at least 15 minutes and pause after three unanswered attempts; family refresh has its own 50-attempt rolling cap and one-minute cooldown. Managed cloud selection checks also reserve against the persisted tracker cap. Provider failure backoff and the automatic 15-minute quiet threshold remain. Ordinary provider polling is not a location request. Preserve all earlier prompted comparison windows and restart boundaries when interpreting the field capture.
