# Milestone 2 normalization contract

Internal Python data contract, tested against HA 2026.9.4. No public WebSocket API, new recorder entities, dashboard or frontend bundle is created by this milestone.

## Sources and authority

Each selected person produces one immutable `Member`. Person state remains the presence authority; selected device trackers can supply optional coordinates. HomeCircle does not reimplement HA tracker priorities, infer relationships from entity names, refresh providers, or read unselected tracker/sensor states. It may retain the active tracker ID reported by the person as provenance.

`HomeCircleRuntime.household` contains normalized members, category counts, primary-home member IDs and map-focus ID sets. Runtime is recomputed on selected state/registry changes, zone-catalog changes, and a local 30-second clock tick. The clock is needed to age explicit timestamps even when the source stays silent. All listeners, clock callbacks, current state references and the normalized snapshot are cleared on unload. There is no history store.

## Presence and places

- Missing/unknown/unavailable person: Unavailable, no map position, never rescued by an optional tracker or sensor.
- An unavailable selected residence that the person reports occupying: classification unavailable until that zone returns or selection is repaired. Missing ordinary-place metadata does not erase otherwise valid presence.
- Driving requires an explicitly selected binary sensor reporting `on` and an explicit driving-report timestamp classified fresh. Driving takes precedence over Home; residence remains a separate field.
- Otherwise, membership in primary Home or a member's additional residence means Home; other valid person presence means Away.
- Modern HA `in_zones` identifiers are matched to selected zone IDs. Overlapping matches choose primary Home first, then additional residences in selection order, then ordinary places. All matched primary-home membership remains distinct.
- Legacy `home` maps only to `zone.home`, never to an unrelated selected primary zone. A legacy named zone is accepted only when that name identifies exactly one zone in HA's current zone catalog, and that ID is selected. Ambiguous/unresolved labels are flagged and never guessed as a residence. Unselected zone names are read solely to detect this ambiguity; their coordinates are not read for normalization.

Home counts include all assigned residences and locationless Home members. Default Home focus includes only Home members at primary Home with a usable, non-conflicting position. `all_residences` is a separate explicit focus set. Driving members are excluded from Home counts and Home focus even if residence metadata says they are near Home. Overview excludes unavailable, missing-coordinate and conflicting-coordinate members.

## Coordinates and conflicts

Coordinates must be finite, non-boolean numbers in latitude/longitude range. Zero is valid. Missing/invalid/negative accuracy is null without discarding an otherwise valid position.

A person coordinate corroborated by the explicitly selected active GPS tracker is marked `active_gps`, with tracker provenance. Other person coordinates are marked `ha_person`; when the active source was not selected, they carry `location_source_unverified`, not a GPS-report claim. A known selected active tracker without coordinates suppresses HA's synthesized legacy Home point. This keeps locationless Home truthful.

If person coordinates are absent/unusable, an available selected active GPS tracker is preferred; otherwise exactly one eligible selected GPS tracker can supplement coordinates. Multiple fallback GPS candidates yield no position and an ambiguity flag. Tracker presence never overrides person presence. Disagreeing person/active-tracker coordinates, or supplemental GPS presence/zone membership conflicts, are exposed as issues and excluded from focus sets. A stale but valid position can remain as explicitly stale evidence; coordinate validity is not a freshness guarantee.

## Explicit evidence and optional fields

The optional `supporting` map is added per member without changing config-entry version 1. Existing milestone 1 entries need no migration.

| Key | Selected HA entity | Interpretation |
|---|---|---|
| `battery` | sensor | Finite 0–100 with `%` unit; zero preserved |
| `charging` | binary_sensor | `on`/`off`; other/missing values unknown |
| `speed` | sensor | Nonnegative finite value with `m/s`, `km/h` or `mph`; unit retained, never converted by provider heuristics |
| `driving` | binary_sensor | Explicit `on`/`off`; speed/Away never imply driving |
| `driving_reported_at` | sensor | Timezone-aware ISO timestamp for the driving report |
| `location_reported_at` | sensor | Timezone-aware ISO timestamp for one explicitly identified location source |
| `location_report_source` | this person or selected tracker | Exact source described by the location timestamp; required together with it |

The user is responsible for selecting sensors whose semantics match the labels. HomeCircle does not invent provider-specific report, battery, speed or driving attributes. Optional fields may all remain empty. Options preserve mappings unless the optional evidence step is opened and fields cleared. Invalid/deleted mappings or a removed bound tracker route back through evidence selection before saving.

Every evidence object keeps `observed_at` (HA state observation) separate from `reported_at` (explicit report sensor), plus source entity, report sensor, freshness and report-status reason. HA `last_updated` is never converted into a GPS report timestamp. Presence evidence remains observation-only; a location timestamp is not proof of fresh authoritative person presence.

The development freshness threshold is five minutes. Timestamps more than 60 seconds in the future, naive datetimes, invalid values and unavailable sources yield unknown freshness. Small clock skew up to 60 seconds is tolerated. An explicit report older than five minutes is stale. A location timestamp is used only when its configured source matches the chosen coordinate source; switching sources cannot reuse a different source's timestamp.

Driving status is `current`, `last_reported`, `unverified`, or `unknown`. A stale `on` remains last-reported evidence but cannot label the member currently Driving. An `on` without a trustworthy timestamp is unverified and also cannot label current Driving. Battery, charging and speed observations retain unknown report freshness unless a future extension explicitly supplies their report evidence. Address/travel enrichment remains absent.

## Privacy and limitations

All state reads are local to HA. Normalization adds no provider clients, outbound calls, telemetry, or precise-location recorder entities. The runtime exposes only selected normalized fields; raw source state references remain internal and are not logged or exported. Milestone 3 exposes an explicit permission-checked display projection; see [FRONTEND](FRONTEND.md).

Normalization tests use only synthetic sources and deliberately fictional coordinates. They do not establish real-provider freshness, real GPS accuracy, physical dashboard usability or release readiness.
