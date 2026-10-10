# Roadmap

## 0 — Bootstrap (complete)

Project structure, reference inventory, private local snapshot, privacy rules, ADR-001, and Git workflow. Runtime directories are explicit placeholders. No deployment or release tag.

## 1 — HA integration and configuration (implemented and validated in disposable HA)

Implement manifest using the real public repository identity; pin development HA version; add config/options flows, translations, selection persistence and unload/reload. Discover people and source trackers using supported HA interfaces. Select primary Home and per-member additional residences plus ordinary places. Prevent duplicate entries and invalid selections. Do not write to source trackers or existing zones.

Acceptance: setup, cancel, reconfigure, restart, entity deletion and unload work in a disposable HA instance; no Life360 installation or credentials required. Exercise both a GPS-backed person and a locationless presence source.

Implementation and HA Core validation are recorded in [milestone 1 validation](MILESTONE-1-VALIDATION.md). Public repository identity, release manifest validation and actual HACS installation have since passed. Initial acceptance with independent iPhone and Life360 sources passed in a disposable instance; broader real-world behavior remains a V0.1 release gate. See [release validation](RELEASE-VALIDATION.md) and [beta 4 validation](BETA4-VALIDATION.md).

## 2 — Normalization and household rules (implemented)

Implement the draft contract and provenance rules. Cover unavailable, missing coordinates, valid zero coordinates, overlapping zones, driving evidence, unknown report times, source switching, and optional battery mappings. Test the dorm member counted Home while primary-house focus excludes that member.

Acceptance: focused unit and HA integration tests using only synthetic data; never fake source freshness. No direct provider imports or outbound provider calls.

Implemented internal contract and validation are recorded in [NORMALIZATION](NORMALIZATION.md) and [milestone 2 validation](MILESTONE-2-VALIDATION.md). The card and authenticated frontend data interface are implemented in milestone 3.

## 3 — Card and UI-only onboarding (implemented; acceptance recorded separately)

Implement card/editor, map with overlap expansion, member cards, Home/Away/Driving/Unavailable labels, category counts and focus, all-family reset, dark styling and portrait behavior. Register resource safely and provide a visual add-card/dashboard path; a card is sufficient for V0.1 if it can be added and configured entirely through HA UI. Select default map technology and licenses before implementation.

Acceptance: new installation reaches a usable dashboard without manual YAML; keyboard/touch and missing-data behavior work; member -> Home -> Away -> overview focus sequence preserves modes and labels. Multiple card instances do not interfere.

Implementation and precise validation scope are in [frontend setup](FRONTEND.md) and [milestone 3 validation](MILESTONE-3-VALIDATION.md).

## 4 — V0.1 stable-release gate

- Real public repository identity and required manifest/HACS metadata are complete.
- HACS custom-repository install, upgrade, removal and HA restart tested in a disposable instance.
- Core config flow, automatic first dashboard, and visual card editor require no provider account and no manual YAML in storage mode. Optional direct Life360 requires an account.
- Core works with at least two independently configured location sources, including one non-Life360 source.
- Run integration/unit/frontend checks plus current HACS validation and HA manifest validation.
- Audit source, generated bundle, archive and history for private data; include required licenses.
- Confirm privacy/network disclosure and optional feature failure behavior, including direct Life360's real-account failure and recovery if that feature ships in stable V0.1.
- Detect when a linked tracker is making an HA Person appear Home while the chosen mobile tracker reports Away. Show the active Person source and an actionable, admin-only explanation during setup and settings; link to HA's Person configuration. Do not silently override the Person state or change its tracker associations. Accept multiple trackers when they agree, and verify this warning against the Friday-style conflict before closing the iPhone field test.
- Observe a complete real departure and return on selected sources, genuine location-report freshness, and background iPhone behavior while away from the local network. Decide and validate the supported HA Core version range.
- Tag `v0.1.0` and create corresponding GitHub release only after these gates pass.

As of beta 16, the intended core setup, normalization, dashboard, and optional Life360 adapter are implemented and the published package has passed HACS and physical-display checks in their documented scopes. Real production Life360-backed and iPhone departure/return timelines are now verified through HA Recorder history and the HomeCircle dashboard. The iPhone's genuine GPS report time, its long daytime update gap, the Person-source conflict warning's real-case acceptance, unattended provider failure/recovery, and a supported Core version decision remain open. See [stable scope audit](STABLE-SCOPE-AUDIT.md) and [current release readiness](CURRENT-RELEASE-READINESS.md). No stable tag is approved.

## Later milestones

Beta 11 added tracker-only pet setup, optional direct Life360 tracking, and a shared provider contract; beta 13 then made HA Person records mandatory for newly added people and pets while preserving older tracker-only members. Beta 16 includes a kiosk view and physical DAKboard acceptance for its tested layout. The unreleased reconciled candidate now includes tracker-reported address display and opt-in IEM radar/HRRR forecast playback. Future candidates: driving estimates, a local distance-apart summary, additional built in tracker providers, recorded trip trails, traffic, and broader landscape polish. Each new provider needs separate credentials, setup, ownership, polling, failure handling, and real-account acceptance. Existing HA tracker selection remains available. These are planning buckets, not V0.1 stable prerequisites.

The [routes, traffic, and radar provider shortlist](FUTURE-MAP-SERVICES.md) records free allowances and license limits for future evaluation. IEM radar and HRRR forecasts are now selected for the opt-in candidate; routing and traffic remain research.

Optional alert setup should offer guided Home Assistant automation creation for arrivals, departures, stale or unavailable trackers, and low battery. The user chooses members, thresholds, and notification targets before saving. Use HA's existing automation and notification systems, avoid a separate HomeCircle alert service, and leave all alerts off until the user enables them.

### Recorded trip trails

- Let a user select a member and time range to view that member’s recorded tracker positions on the HomeCircle map. Use the explicitly selected tracker’s available Home Assistant history, keep current and historical positions visually distinct, and show report times when the source supplies them.
- Show gaps between reports rather than implying the exact roads traveled. If history is missing, excluded from Recorder, or too sparse to form a useful trail, explain that clearly. Keep this separate from future route planning and traffic estimates; do not send historical positions to an external routing service by default.

### Additional Life360 details and location requests — partially implemented

- When the selected tracker actually supplies them, show its Life360 place or address and time at the current location in member details. Keep the source and report time visible so an old address is not presented as current. The existing HA Life360 tracker exposes these fields; the optional direct adapter would need equivalent parsing before it can offer them.
- Add Wi-Fi status, location-sharing or unavailable reasons, and account connection health to administrator troubleshooting where the source exposes them. Wi-Fi enabled is not proof that the phone is connected to the home network. Do not make these provider-specific fields prerequisites for other tracker integrations.
- Implemented in the current candidate: separate Life360 location requests with progress, cooldowns and results that distinguish dispatch from a newer report. Ordinary details Refresh rereads Home Assistant state. The external integration and direct adapter retain separate capability checks; neither guarantees a new GPS fix.
- The current Life360 client does not provide a historical drive or route retrieval method. Use available HA Recorder samples for the planned trip trail, subject to the gaps and privacy rules above. Reassess provider capabilities before promising native Life360 drive events or route history.

### Member-card and map presentation — partially implemented

- Replace the visible Home, Away, Driving, and Unavailable words on person cards with distinct status icons. Keep the full status in each card's accessible name and provide a readable explanation on hover/focus where practical; meaning must not rely on color alone. Preserve the current state and freshness rules.
- Partially implemented: tracker-reported addresses appear on person cards outside defined places. Further map-label consistency and optional address lookup remain proposals. Show the same location identification on person cards and map labels: prefer a configured named residence or place, then a useful street and city label for a valid reported position when an address lookup is enabled. Use one consistent label for the same member on both surfaces. Keep unknown or unavailable locations explicit, avoid identifying a stale position as current, and do not show raw coordinates as a fallback. Decide lookup provider, cost, caching, and privacy controls before implementation.
- Implemented in the current candidate: a long press on a person card opens a details and troubleshooting dialog over the dashboard. It must not also trigger map focus. A visible details control provides keyboard and mouse access; administrators can continue to that person's settings using the same options flow, then return with Back. Show the HA Person and explicitly selected tracker states, coordinates, source, update and report times, and explain conflicts without implying that an HA state update proves a new GPS fix. Show refresh progress and its result. Open HA History in an overlay that closes back to HomeCircle; plotted trip trails remain a separate enhancement.

### Adaptive stale reporting — proposed, not implemented

Evaluate a bounded rolling history of 30–50 natural location reports per tracker and context, with lower-confidence learning from ten reports. Exclude forced refreshes and outages, preserve a fallback when evidence is insufficient, limit adjustments and allow a manual override. The current people cutoff remains five minutes; a longer Life360 at-home cutoff is only a proposal. HA timestamps must not be substituted for a genuine GPS fix time. Collect continuous passive evidence before enabling automatic threshold changes.
