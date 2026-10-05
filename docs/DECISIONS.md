# Decisions

| ID | Status | Decision |
|---|---|---|
| [ADR-001](adr/ADR-001-provider-independence.md) | Accepted | Standard HA entities define the location-provider boundary |

ADR-001's 2026-10-04 amendment records the approved optional direct Life360 adapter. It does not make a provider account necessary for core HomeCircle setup.

## Bootstrap conventions

- HomeCircle is the development name; public naming clearance remains open.
- Preserve existing V2 as HomeCircle Reference Implementation v1. Freeze raw local artifacts outside Git; publish only generic descriptions/examples.
- MIT for newly authored HomeCircle files. Retain upstream licenses/notices before importing any existing code.
- Main plus short-lived feature branches; semantic version release tags.
- A single Integration package with bundled frontend is the intended V0.1 delivery shape; published beta 4 packaging and HACS lifecycle have passed disposable-instance validation.

## Open decisions

Broader HA compatibility beyond the tested 2026.9.4 baseline, configurable freshness defaults across sources, the stable public product name, and production replacement remain open. Public repository identity and HACS release packaging are established for the experimental beta; do not extend those results into untested compatibility or production guarantees.

## Milestone 1 decisions

- One household config entry with explicit per-member tracker/residence lists.
- Use HA's public `entities_in_person` helper and distinguish it from active `source`.
- Persist complete options snapshots and use HA automatic reload; cancel leaves the saved entry unchanged.
- Retain missing selections with a repair notice; require explicit reselection after renames.
- The early development manifest was local-only; public URL and codeowner metadata have since been validated for the experimental HACS release.

## Milestone 2 decisions

- Immutable normalized members and one source of truth for counts/focus ID sets; internal runtime contract only.
- Modern zone IDs with unambiguous legacy-name fallback; primary-house focus excludes additional residences and conflicting/missing locations.
- Optional explicit sensor mappings; report timestamps bound to coordinate sources; no provider-specific attribute guessing.
- Five-minute development report freshness threshold, sixty-second future-clock tolerance and a thirty-second local aging tick. Untimed/stale driving cannot claim current Driving.
- Existing entries remain version 1; the optional supporting map is backward compatible.

## Milestone 3 implemented decisions

[ADR-002](adr/ADR-002-map-and-frontend.md) records bundled Leaflet, the original private map default, native card/editor, esbuild, permission-checked snapshots and resource ownership. The 2026-10-04 usability revision in that ADR changes new cards to street tiles by default. [Validation](MILESTONE-3-VALIDATION.md) records the original milestone 3 scope.
