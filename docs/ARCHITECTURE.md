# Architecture

## Boundaries

```text
Tracking integrations (Companion, Life360, other sources)
    -> HA person / device_tracker / zone + optional selected sensors
    -> HomeCircle selection, normalization, residence rules
    -> authenticated HA-facing data interface
    -> HomeCircle card and visual editor
```

The backend owns selection, normalized data, freshness metadata, and household/place rules. The frontend owns rendering and interaction. Neither layer imports Life360 API clients or requires provider credentials. Map, geocoding, routing, and weather are separate optional rendering/enrichment services, not location-source dependencies.

## Entity discovery and lifecycle

Use supported HA state and registry interfaces. Read `person` state and its active source where available; do not independently reimplement HA's tracker priority rules. Association discovery must distinguish the active source from all configured trackers. Verify the supported access path when implementing against a pinned HA version; fall back to explicit UI selection if full associations are unavailable. A selected GPS tracker may supplement coordinates without silently overriding authoritative person presence; retain provenance and expose conflicts.

Subscribe to relevant HA state changes. Unsubscribe on unload and rebuild mappings on reconfiguration. Handle removed/renamed entities, unknown/unavailable sources, unavailable zones, restarts, and locationless presence. Do not poll a tracking provider or trigger source-specific refresh services by default.

## Normalized member contract

| Field | Meaning |
|---|---|
| id, display_name, kind | Local member identity; person first, pet later |
| person_entity, tracker_entity | Explicit runtime selection; never actual household IDs in source |
| presence | `home`, `away`, `driving`, or `unavailable` |
| residence, place, primary_home | Separate residence classification and displayed place |
| location | Nullable latitude/longitude/accuracy; invalid or unavailable locations are not focusable |
| source_entity | Provenance of the reported presence/location |
| reported_at, observed_at | Actual source report time if known; HA observation time kept separate |
| freshness | `fresh`, `stale`, or `unknown`, with timestamp provenance |
| battery_percent, charging | Nullable, with explicit supporting-sensor mapping where needed |
| driving, speed, speed_unit | Optional evidence with units; missing values remain unknown |
| address, travel | Optional future enrichment with provenance and age |

Do not interpret HA `last_changed`/`last_updated` as proof of a fresh GPS report. Tracking providers expose different attributes; report-time, battery, charging, speed and driving are not guaranteed properties of every person/tracker. Use explicit optional mappings and preserve missing data. Known stale driving reports must say last reported; do not present them as current motion.

Classification follows unavailable first, then supported driving evidence, then configured residence, else Away. Residence and presence are separate so a driving report near a residence does not create inconsistent counts. Missing coordinates do not alone make a valid HA Home state unavailable. Coordinate validation must accept zero and reject missing/out-of-range/non-finite values. Match places by selected zone identifiers, not household-specific strings.

## Packaging decision

One development repository, one HACS **Integration** package. Build the card from `frontend/homecircle-card/` into a packaged `custom_components/homecircle/frontend/` directory. The integration must serve/register its resource idempotently and make the card available to the visual card picker/editor. Do not assume HACS automatically installs a separate Dashboard artifact from the same integration repository. Generated output and owned resource registration are implemented; HACS upgrade/removal remain release gates.

Milestone 1 includes a local development manifest, config/options/reconfigure flows, and English translations. Public documentation/issue URLs and code owners remain unset until the repository identity is supplied; the manifest is not yet release-complete.

## Data and network

HA authentication protects member data. No unauthenticated location endpoint, telemetry, independent location-history store, or logging of raw states. Runtime configuration belongs in HA config entries, never repository examples. Frontend memory caches must be bounded and cleared on unload. Document any recording implications for future sensor entities; avoid putting precise locations into new recorder attributes unnecessarily.

The core presence view must work without a paid map key. Select and license a default map renderer/provider in a follow-up decision, including attribution and network disclosure. Any cloud enrichment is opt-in and failure must not break presence. Browser map keys cannot be treated as secret once sent to the client; use origin/API restrictions and avoid exposing backend credentials.

## Official references

Checked during bootstrap on 2026-09-27; verify again against the supported versions when implementing:
- [HA Person](https://www.home-assistant.io/integrations/person/)
- [HA Device tracker](https://www.home-assistant.io/integrations/device_tracker/)
- [HACS integration requirements](https://hacs.dev/docs/publish/integration/)
- [HACS general requirements](https://hacs.dev/docs/publish/start/)

## Milestone 1 implementation

A single household config entry stores `people`, `primary_home`, `places`, and a `members` mapping keyed by person entity ID. Each member has explicit `trackers` and `additional_residences` lists. Primary Home applies to everyone; ordinary places and per-member residences stay separate. An ordinary place may be an additional residence for a particular member. Milestone 2 now derives counts and focus ID sets from these selections; milestone 3 renders them.

Setup saves one complete snapshot in entry data. Options saves a complete override in entry options, and `OptionsFlowWithReload` reloads after a successful change. Reconfigure reads the effective snapshot, replaces entry data, clears the override and reloads. In-progress drafts never mutate the entry, so Cancel is atomic. Final confirmation revalidates all selected entities. Lists can be emptied to remove mappings; removing a person removes their mappings from the effective configuration.

Discovery uses HA's public `entities_in_person` helper for configured trackers and the person state's `source` attribute for the active tracker. Suggestions are displayed separately and must be confirmed. Empty trackers means person-only operation. No entity-name matching, private person storage access, source reassignment or provider refresh occurs. Unavailable but registered/enabled entities can be selected; wrong domains, missing/unregistered and disabled entities are rejected.

Runtime data holds only current references to explicitly selected states, plus missing/unavailable sets. State and registry event subscriptions are removed on unload; cached states and repair notices are cleared. Missing sources retain their selections and create a repair notice that resolves if states return. Renames require explicit reselection in Options rather than guessing a replacement. The integration can load while sources are starting and recovers as their states appear.

HA 2026.9.4 can synthesize Home-zone coordinates for legacy locationless trackers. Modern trackers with explicit `in_zones` can remain coordinate-free while Home. Milestone 2 must preserve this provenance distinction instead of claiming every person coordinate is a GPS report. Milestone 2 implements this distinction in the internal normalized snapshot.

## Milestone 2 implementation

See [the normalization contract](NORMALIZATION.md) for the implemented fields, precedence, timestamp/source binding, conflict handling, optional sensor mappings and limitations. Counts and focus IDs share the same normalized records. A local clock ages report evidence; it never polls providers. Milestone 3 adds the permission-checked websocket projection documented in [FRONTEND](FRONTEND.md).

## Milestone 3 implementation

See [FRONTEND](FRONTEND.md) and [ADR-002](adr/ADR-002-map-and-frontend.md) for the actual card, resource ownership, authenticated projection and optional network behavior.
