# Feature inventory

Evidence inspected at bootstrap: local production-era V2 migration notes and modules; extracted Family Map Card source and README; its September 26 beta 19 handoff; separate Life360 Family source. Historical live-test statements below come from those records and were not rerun. Production V2 and later test-clone improvements are distinct baselines. The live HA configuration mount was unavailable.

V0.1 is a planned stable release. **This table preserves the bootstrap reference inventory and historical targets; some rows were superseded by beta 11–16 decisions.** Use the [current product scope](../docs/PRODUCT.md) and [stable scope audit](../docs/STABLE-SCOPE-AUDIT.md) for release decisions. “Core” means required; “optional” means absence must not block the core; “later” means preserved as a documented requirement outside V0.1.

| Capability | Current implementation / evidence | HomeCircle target | V0.1 |
|---|---|---|---|
| Multiple family members | Legacy V2 member templates; extracted `family-dashboard-card.js` and configurable entity list | UI selection of HA people; normalized member records | Core |
| Provider independence | Extracted map accepts entities with coordinates; legacy/provider integration has Life360-specific fields and refresh paths | Consume HA person/device_tracker; no direct Life360 dependency or credentials | Core |
| Pet tracking | Separate provider has pet API/tracker support; extracted cards recognize pet flag, suppress speed and drive-home requests | Explicit tracker-only pet selection and kind, independent of provider | Later onboarding; preserve reference |
| Home/Away/Driving/Unavailable | `family-rules.js`: invalid/unknown/unavailable first, driving evidence second, residence then Away | Shared backend classification; optional explicit driving evidence; unavailable separate from Away | Core states; driving optional data |
| Multiple homes / dorm | Production V2 introduced per-member dorm residence; extracted `home_zones` generalizes it | Per-member primary/additional residences, plus non-residence places | Core |
| Home count vs focus | `matchesFocus` counts all configured residences but defaults Home focus to primary house; `focus_all_home_zones` optional | Preserve count-at-either-residence, focus-family-house default | Core |
| Battery/status | Extracted card reads battery and charging; low warning at <=20% when not charging; unknown displayed honestly | Optional selected HA sensors/attributes, normalized nullable fields; no Life360 assumption | Optional |
| Freshness | Extracted card uses `last_seen`; missing age is unknown/stale; home pets have longer threshold than people | Distinguish report vs observation time; configurable source-aware freshness; qualify stale driving | Core honest freshness; advanced policy later |
| Arrival/status-since | Extracted member card shows since/arrival metadata when available | Keep event provenance; never invent arrival from an unrelated HA update | Later |
| Address/location labels | V2 city/address helpers and map labels; extracted `member-travel.js` uses named zones/address lookup, backoff/cache | Zone/place label first, unavailable fallback; optional geocoding with disclosure | Core zone labels; geocoding later |
| Drive time / ETA | Extracted travel module estimates drive to primary house from last reported position; excludes pets/home/unavailable; not a prediction of coming home | Optional routing adapter with age, destination, cost and privacy disclosure; do not call estimate a confirmed arrival | Later |
| Speed | Extracted card requires explicit units; historical raw-provider conversion is approximate; pet speed omitted | Explicit units only, optional sensor mapping; no universal raw-provider multiplier | Later |
| Map grouping / spider | V2 inherited Mapy grouping/spider behavior; Google renderer expands groups for member focus; migration notes describe zoom 13 expansion / 12 collapse | Independently selectable overlapping markers and predictable expand/collapse; regression-test focus | Core usability; exact renderer parity later |
| Member focus | Migration notes and extracted renderer: hybrid/satellite with labels at zoom 18 | Keep clear member focus; renderer-specific zoom is a reference detail, not a cross-provider contract | Core focus |
| Summary/category focus | Home, On the Move, Away and Family Members; category/overview restores road map; empty category no action/disabled | Shared classifier, enabled states, correct subset and all-family reset | Core |
| History and zones | Reference has history range controls and HA zones; older migration did not separately verify historical trail content live | Optional authenticated HA history, no separate location archive | Core places; history later |
| Weather / radar | Extracted `map-overlays.js`, `azure-radar.js`, `radar-timeline.js`: current precipitation, optional animated forecast, timeline/legend, attribution and failure fallback | Opt-in services with explicit network/cost disclosure, graceful failure and teardown | Later |
| Traffic / map types | Google map controls expose traffic and map types | Optional provider-specific controls with clear defaults | Later |
| Portrait wall display | Legacy V2 layout and extracted native member cards; dark readable cards, summary and map; portrait retained in beta 19 | Responsive no-overflow layout and readable touch targets | Core |
| Landscape | Beta 19 handoff records compact CSS on test clone; physical tablet acceptance still separate | Preserve portrait while validating responsive variants | Basic responsive core; full parity later |
| DAKboard / TouchHub | Legacy display use and iframe troubleshooting history; embedding can differ from direct navigation; no new physical check here | Document direct/embedded setup and authentication; test actual device and origins | Later physical acceptance |
| Kiosk | Legacy Kiosk Mode dependency; newer `dashboard-kiosk.js` uses temporary Popover layer, Exit/Escape/disconnect cleanup; browser chrome remains | Optional presentation mode, safe exit; never treat kiosk as security | Later |
| Styling and labels | Extracted shared colors: Home green, Driving cyan, Away amber, Unavailable slate; rounded dark cards, initials/photo fallback, status border; labels suppress raw unknown values | Consistent status/labels across map, cards and summary; generic avatars, accessible non-color cues | Core; pixel parity later |
| Distance apart | Newer `family-distance.js` maximum great-circle separation, HA units; Everyone Home respects additional residences | Optional local metric clearly distinguished from road distance/live position | Later |
| Source refresh | Legacy stale-Life360 automation and newer optional provider update button; request success does not prove freshness | Source integration owns refresh; no Life360-specific core service calls | Excluded from core |
| HACS packaging | Extracted frontend has Dashboard-category packaging; separate provider is experimental; local docs mix earlier package versions and later beta notes | Single Integration package with bundled/registered frontend, tested upgrade/removal | Bundling implemented; HACS acceptance pending |
| Config flow | Existing provider flow authenticates its own source; extracted setup wizard generates YAML | HomeCircle flow selects existing HA entities and places, never authenticates tracking provider | Core; selection flow implemented, see validation |
| No manual YAML | Legacy dashboard and extracted wizard/examples still involve YAML/manual registration | UI config/options flow plus visual card editor and automatic resource registration | Implemented and browser-tested in storage mode |

## Regression contract

Count a member Home at either assigned residence; Home focus still selects the primary-house subset. After focusing a member, test Home, Away, On the Move and all-family overview. Keep unavailable separate, disable missing-coordinate focus, and do not show stale driving as fresh. Preserve portrait readability while testing grouping and summary buttons. Optional weather/routing/kiosk must not interfere with the presence view.

## Evidence limits

Earlier source handoffs report browser/test-clone checks, not a new physical DAKboard/TouchHub acceptance. Driving speed had no real moving-member acceptance in the inspected handoff. The DAKboard iframe diagnosis was historically provisional; do not assume current embed compatibility. Exact production deployment drift cannot be assessed without a later read-only live capture.
