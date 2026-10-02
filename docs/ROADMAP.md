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

## 4 — V0.1 release gate

- Real public repository identity and required manifest/HACS metadata are complete.
- HACS custom-repository install, upgrade, removal and HA restart tested in a disposable instance.
- Config flow and visual card editor require no provider account and no manual YAML.
- Core works with at least two independently configured location sources, including one non-Life360 source.
- Run integration/unit/frontend checks plus current HACS validation and HA manifest validation.
- Audit source, generated bundle, archive and history for private data; include required licenses.
- Confirm privacy/network disclosure and optional feature failure behavior.
- User accepts replacement separately; no automatic production V2 migration.
- Tag `v0.1.0` and create corresponding GitHub release only after these gates pass.

As of experimental beta 6, snapshot retry, the beta 5 HACS upgrade/removal path, controlled within-person real-source switching, allowed/denied non-admin access, and the physical additional-residence count/focus snapshot have passed in their documented scopes. A full real departure/return timeline, background iPhone updates to the disposable instance outside the LAN, sustained availability, unattended failover, and the published beta 6 HACS upgrade remain open. See [current release readiness](CURRENT-RELEASE-READINESS.md). No stable tag or production migration is approved.

## Later milestones

V0.2 candidates: tracker-only pet setup, battery/charging refinements, configurable freshness, address display, driving estimates and local distance-apart summary. Later: history, traffic, weather/radar providers, full kiosk/DAKboard acceptance and landscape polish. These are planning buckets, not delivery promises. Maintain inventory status as scope changes.
