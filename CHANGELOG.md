# Changelog

## 0.1.0-beta.3

- Show report ages in minutes, hours and days with visible stale indicators.
- Add explicit Person/Pet settings and separate pet Home/Away freshness thresholds.
- Preserve supporting sensor mappings when editing member settings.

## 0.1.0-beta.2

- Responsive member layout and larger map zoom touch targets.
- Preserve tile-failure notice during member/category selection and clear it after a successful tile-loading cycle.
- Initial real-source acceptance with iPhone, Life360 and existing separate Pet GPS integration.

## 0.1.0-beta.4

- Per-source location report timestamp mappings, preserving legacy single-source settings.

## Unreleased


### Added
- HomeCircle project scaffold and provider-independent product definition.
- ADR-001: standard Home Assistant entities are the location-provider boundary.
- Frozen local reference snapshot with source hashes; public generic reference specification.
- V0.1 feature scope, acceptance criteria, privacy checks, and main/feature-branch workflow.

- Milestone 1 config/options/reconfigure flows with HA entity selectors, explicit tracker confirmation, primary Home, ordinary places and per-member additional residences.
- Atomic selection persistence, duplicate-entry prevention, validation of removed/disabled selections, state subscriptions, automatic options reload and cleanup on unload.
- Missing-source repair notice and recovery; renamed sources require explicit reselection.
- Local development manifest and English translations; maintainer and repository fields completed during release preparation.
- Pinned HA 2026.9.4 test environment, focused HA flow tests and separate-process restart validation with synthetic sources.

- Milestone 2 normalized member records, Home/Away/Driving/Unavailable counts and separate primary-house/all-residence/overview focus sets.
- Source and timestamp provenance, coordinate validation/conflict handling, optional explicit battery/charging/speed/driving/report-sensor mappings, and automatic aging without provider polling.
- Synthetic regression coverage for residence counts, locationless presence, stale driving, source switching, unknown timestamps, overlapping zones and optional values.
- Reproducible disposable browser launcher; frontend missing-dependency and custom-component import-root issues resolved.

### Status
Development integration only. Card and authenticated frontend access are implemented. Packaged Core lifecycle validation passes; actual HACS acceptance and public release remain pending. Production V2 is unchanged.

### Milestone 3 development — 0.0.3-dev1

- Add permission-checked normalized websocket snapshots and owned Lovelace resource registration.
- Bundle Leaflet with its license; ship the initial dark responsive card and visual editor.
- Add category/member/overview focus, overlapping-marker selection, per-card visibility, and optional disclosed OSM tiles.
- Verify UI-only card installation, recovery, portrait layout and independent card instances with synthetic data.

### Release preparation

- Set jmhjr maintainer/repository metadata and configure ZIP-based HACS distribution.
- Add deterministic package builder, archive inventory and isolated package lifecycle validation.
- Record user-confirmed physical DAKboard touch, unavailable-state and recovery checks.
- Support explicit private LAN binding for disposable physical-display QA, keeping loopback as the default.

### Official HA validation

- Pass unmodified Core 2026.9.4 hassfest with no invalid integrations or warnings.
- Declare HTTP dependency, UI-only config schema and required manifest ordering.

### Public development review

- Label the repository experimental and publish it for development review.
- Pass all nine official HACS remote validation checks after privacy review.
- Use the maintainer GitHub no-reply address in published branch history.

## 0.1.0-beta.1 — development prerelease

First experimental packaged prerelease for disposable HACS acceptance. Includes the integration, bundled card, visual editor and original brand icon. Official HA and HACS repository validation passed before packaging. Real-provider acceptance and production rollout remain pending.
