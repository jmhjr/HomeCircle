# Changelog

## 0.1.0-beta.11 — experimental prerelease

- Let an existing Home Assistant device tracker be selected directly as a pet, without creating a Person record. The pet uses that tracker for presence and location, with its own residences, freshness limits and optional supporting sensors.
- Preserve custom pet freshness limits when reopening and saving Options without changing those fields.
- Offer optional direct Life360 account connection with password or access token. HomeCircle creates ordinary HA device trackers for discovered members; existing Life360 entities remain selectable without direct connection. People can also be selected from trackers without creating HA Person records.
- Route managed tracker connections through a provider registry so future built in sources can have separate credentials, setup steps, tracker ownership and lifecycle while sharing the existing HA entity and household model.
- Allow any registered tracker provider to complete account setup before its trackers appear, then choose members in Options after discovery.
- Route account repair to the provider that reported the authorization failure, so future connected tracker services can have separate reconnect forms.
- Keep the setup prompt visible until a tracker from the connected account is explicitly selected, even when other household members already exist.
- Prevent disconnecting a tracker account while a selected Home Assistant Person is configured to use, or currently reports from, one of its trackers.
- Report malformed Life360 location fields as an unexpected provider response while treating intentionally unshared locations as unavailable.
- Keep checking Life360 for newly added Circle members after initial discovery, track failures per member, and show tracker discovery status in HomeCircle Options.
- Classify provider failures with safe health codes, export sanitized Home Assistant diagnostics, and open a reauthentication repair flow when Life360 rejects a saved credential. Document the same issue workflow for future built in providers.
- Keep other Life360 members updating when one direct tracker is disabled or access to one Circle or member is denied. Stop retrying a rejected credential until it is repaired, cancel an active refresh on unload, and create TLS contexts off Home Assistant's event loop.
- Reject a tracker assigned to more than one household member.
- Recover saved direct trackers as unavailable during an offline restart, retry cleanly after a failed tracker-platform setup, and check account access when every member request is denied.
- Verify Life360 account continuity when replacing credentials or reconnecting; reject a different verified account while preserving selected trackers. For older development entries without a saved account identity, compare the old and new sign-ins when possible, or require explicit same-account confirmation when the old sign-in cannot be verified.

## 0.1.0-beta.10 — experimental prerelease

- Let a full-height HomeCircle card cover the viewport in kiosk mode, including HA's title bar and dashboard margins. Exit kiosk restores the ordinary view.
- Use a selected GPS tracker's valid `last_seen` location timestamp when no report-time sensor is configured. Keep the iPhone location report time unknown when that attribute is absent.
- Show battery level and charging state from the selected location tracker when no explicit supporting sensor is configured. Explicit sensor mappings retain priority.

## 0.1.0-beta.9 — release candidate

- Draw single and grouped member markers as pins whose tips identify the map location, leaving the avatars above the point.
- Fit the map with enough space for the taller pins and keep grouped avatars clear of zoom controls on narrow displays.

## 0.1.0-beta.8 — experimental prerelease

- Show HA person portraits or selected Life360 person and pet tracker portraits on member cards and map markers, with initials when an image is absent or fails to load. Limit external portrait requests to Life360 image hosts and omit the HA page referrer.

## 0.1.0-beta.7 — experimental prerelease

- Guide each member toward one linked tracker by showing current GPS/presence capability and the HA active source; leave equally suitable choices for the user. Existing saved selections remain intact during edits.
- Replace overlapping map counts with a compact member portrait cluster. Use HA-served pictures when available and initials otherwise; tapping the cluster still opens individual member choices.

## 0.1.0-beta.6 — experimental prerelease

- Make member setup easier to scan with household progress, readable Home Assistant entity names, clearer tracker and residence labels, and help beside each field. Show pet location timing on a separate pet-only step. Tracker suggestions and saved selections retain their existing behavior.
- Keep battery, charging, speed and driving sensors on a short status screen. Configure location report times on a separate screen for each source; guide older single-source timestamp mappings through that screen without discarding them.
- Show a readable draft summary before saving the household, including homes, trackers, optional sensors, source-specific report times and pet timing.
- When a location source has no genuine report-time sensor, show when Home Assistant last updated that source state while keeping the location report time explicitly unknown. HA observation time does not determine GPS freshness.
- Keep the owned dashboard card resource stable when saved HomeCircle settings trigger an automatic reload, while retaining cleanup on unload or failed setup.
- Keep the same owned dashboard resource when an unchanged Reconfigure save triggers a Home Assistant reload.
- Give member cards separate place, battery, and report-time labels; make stale reports easier to scan while keeping HA observation age distinct from an unknown location report time.
- On narrow card widths, place member status beneath the name, use two readable rows of category buttons, and shorten the map so the member list starts sooner.
- Keep keyboard focus on the selected member card after choosing a map marker or a member from an overlapping-marker group; keyboard activation scrolls the card into view without making touch activation jump the page.
- Preserve keyboard focus on clustered markers and expanded member choices when the map redraws, and expose whether a cluster is expanded.
- Offer an opt-in full-height wall-display layout so the map uses space below the card without hiding category controls or member cards.
- Offer a reversible kiosk control on full-height cards, with an optional URL setting that opens the page with Home Assistant navigation hidden in that browser.

## 0.1.0-beta.5

- Limit failed household snapshot retries to the regular refresh timer; reconnecting still refreshes immediately.
- Clean up an owned dashboard resource when a HomeCircle entry is removed while not loaded, using its persisted ownership ID. Removal remains safe for unrelated and manually registered resources.
- Add focused regressions for failed-request retries, scheduled refresh, reconnects and unloaded-entry cleanup. These changes are not in the published beta 4 ZIP.

## 0.1.0-beta.4

- Per-source location report timestamp mappings, preserving legacy single-source settings.

## 0.1.0-beta.3

- Show report ages in minutes, hours and days with visible stale indicators.
- Add explicit Person/Pet settings and separate pet Home/Away freshness thresholds.
- Preserve supporting sensor mappings when editing member settings.

## 0.1.0-beta.2

- Responsive member layout and larger map zoom touch targets.
- Preserve tile-failure notice during member/category selection and clear it after a successful tile-loading cycle.
- Initial real-source acceptance with iPhone, Life360 and existing separate Pet GPS integration.

## 0.1.0-beta.1 — development prerelease

First experimental packaged prerelease for disposable HACS acceptance. Includes the integration, bundled card, visual editor and original brand icon. Official HA and HACS repository validation passed before packaging. Real-provider acceptance and production rollout remained pending at that checkpoint.

## Development history before beta 1


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

### Status at that checkpoint
The card and authenticated frontend access were implemented. Packaged Core lifecycle validation passed; actual HACS acceptance and public release were still pending. Production V2 was unchanged.

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
