# Architecture

## Boundaries

```text
Existing HA integrations ───────────────────────────┐
HomeCircle managed tracker providers -> HA trackers ─┴─> HA person / device_tracker / zone + optional selected sensors
    -> HomeCircle selection, normalization, residence rules
    -> authenticated HA-facing data interface
    -> HomeCircle card and visual editor
```

The backend owns selection, normalized data, freshness metadata, and household/place rules. The frontend owns rendering and interaction. Existing Home Assistant entities remain the default boundary. Optional managed providers create ordinary HA trackers that enter the same selection and normalization path. The frontend never receives provider credentials. Map, geocoding, routing, and weather are separate optional rendering/enrichment services.

## Built in tracker provider contract

`tracker_providers.py` registers each managed provider with a stable ID, its own saved account and enable keys, a credential-flow step, a tracker entity ownership prefix, an HA platform, and a client factory. The client implements `async_start` and `async_stop`. The setup flow processes enabled providers' credential steps before member setup; each provider form verifies its own credentials and calls `connection_saved`. A provider can be disconnected independently, but a selected tracker that it owns must be replaced first. A single HomeCircle entry can connect multiple providers.

The HA entity registry and state machine are the shared data boundary. Provider adapters own authentication, discovery, polling, retries and translation into HA tracker state. They must never write directly into HomeCircle's household model, infer tracker ownership from names, or copy raw API responses into entity attributes. Existing third party tracker integrations remain selectable without a HomeCircle provider connection. New providers must add their own setup field translations, credential step, client, manifest dependency if needed, and contract tests. Provider IDs and tracker unique IDs must remain stable across upgrades.

Life360 is the first registered managed provider. Its existing `life360_account` storage key remains stable for development snapshots and upgrade tests. No network connection is created unless the user enables and verifies it. Additional providers must have independent credentials and failure handling so one service outage cannot disable unrelated tracking sources.

Each client also returns a typed, allowlisted health snapshot. HomeCircle Options uses its status code for guidance; HA diagnostics exports only that snapshot and aggregate counts. Authorization failure starts HA's reauthentication flow. See the [provider issue workflow](TRACKER-PROVIDER-ISSUES.md) for triage and release checks when an unsupported API changes.

## Entity discovery and lifecycle

Use supported HA state and registry interfaces. Read `person` state and its active source where available; do not independently reimplement HA's tracker priority rules. Association discovery must distinguish the active source from all configured trackers. Verify the supported access path when implementing against a pinned HA version; fall back to explicit UI selection if full associations are unavailable. A selected GPS tracker may supplement coordinates without silently overriding authoritative person presence; retain provenance and expose conflicts.

Subscribe to relevant HA state changes. Unsubscribe on unload and rebuild mappings on reconfiguration. Handle removed/renamed entities, unknown/unavailable sources, unavailable zones, restarts, and locationless presence. Each managed provider polls only when its connection is enabled; households using existing HA entities do no provider polling.

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

2026-10-04 setup revision: New people and pet members start with an HA Person. The flow can create a storage-backed Person, then has a separate tracker assignment step before member settings. A new tracker link is staged in the HomeCircle draft and added to the selected editable HA Person only on final save. Existing tracker-only members remain readable and have a conversion path that preserves their member settings. Creating a Person itself is an HA side effect that survives cancel, like creating a zone. A tracker already linked to another Person is rejected. Older tracker-only lists are shown only while saved legacy members remain; new setup does not offer those lists.

Runtime data holds only current references to explicitly selected states, plus missing/unavailable sets. State and registry event subscriptions are removed on unload; cached states and repair notices are cleared. Missing sources retain their selections and create a repair notice that resolves if states return. Renames require explicit reselection in Options rather than guessing a replacement. The integration can load while sources are starting and recovers as their states appear.

HA 2026.9.4 can synthesize Home-zone coordinates for legacy locationless trackers. Modern trackers with explicit `in_zones` can remain coordinate-free while Home. Milestone 2 must preserve this provenance distinction instead of claiming every person coordinate is a GPS report. Milestone 2 implements this distinction in the internal normalized snapshot.

## Milestone 2 implementation

See [the normalization contract](NORMALIZATION.md) for the implemented fields, precedence, timestamp/source binding, conflict handling, optional sensor mappings and limitations. Counts and focus IDs share the same normalized records. A local clock ages report evidence; it never polls providers. Milestone 3 adds the permission-checked websocket projection documented in [FRONTEND](FRONTEND.md).

## Milestone 3 implementation

See [FRONTEND](FRONTEND.md) and [ADR-002](adr/ADR-002-map-and-frontend.md) for the actual card, resource ownership, authenticated projection and optional network behavior.
