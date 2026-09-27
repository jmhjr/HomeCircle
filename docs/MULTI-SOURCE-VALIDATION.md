# Multiple trackers on one person — beta 3

## Method

Ran the beta 3 release package in fresh Home Assistant Core 2026.9.4 storage. One real HA Person entity had three fictional device trackers: phone GPS, cloud GPS and router presence. HA's Person integration selected the active source in response to tracker events; the check did not manually set the person's source or state. HomeCircle was configured through its actual config flow.

The phone report timestamp was explicitly mapped to the phone tracker. GPS source observation updates did not change that report timestamp. No real iPhone, Life360 or eero service was contacted. This checks the standard entity boundary, not those providers' network behavior.

## Results

| Scenario | Presence | Map focus | Report evidence |
| --- | --- | --- | --- |
| Router Home, two differing away GPS candidates | Home | Withheld | No usable location |
| Router leaves; phone GPS updates | Away | Phone position | Stale phone report |
| Cloud GPS becomes newest | Away | Cloud position | Unknown; phone timestamp not reused |
| Cloud becomes unavailable | Away | Phone position | Original stale phone report |
| Router returns Home while phone GPS remains away | Home | Withheld due to conflict | Conflicting location excluded from focus |
| Phone GPS reports Home, matching router | Home | Supplemental phone position | Original stale phone report |
| Explicit phone report timestamp updates | Home | Supplemental phone position | Fresh |
| HomeCircle reload | Home | Same position | Mapping and fresh evidence preserved |

Every checkpoint contained exactly one member, exactly one counted status and the expected overview focus set. Eight checkpoints passed. The temporary loopback instance was removed afterward. Ruff formatting and lint checks passed for the reproducible validator.

Run after building the release ZIP:

```sh
python scripts/validate_multi_source.py
```

Use the project's Home Assistant test environment. The validator uses loopback port 18128 and creates its own temporary configuration.

## Meaning for setup

Assign multiple trackers for an individual to one HA person, then explicitly select those trackers in HomeCircle. Router presence can keep a person Home even when GPS reports away. HomeCircle omits ambiguous or conflicting map focus rather than selecting an arbitrary GPS candidate. It can use an unambiguous supplemental GPS position when the active router source has none.

Beta 3 supports one location-report timestamp/source mapping per member. If the displayed location changes to another source, its report age stays unknown unless the mapping describes that source. This is an existing limitation, not automatic per-tracker timestamp mapping.

The checks validate the freshness evidence consumed by the card; they were not a new browser-label or physical-touch test. Prior card and DAKboard acceptance is in [beta 3 validation](BETA3-VALIDATION.md). The real-source test dashboard and production HA were unchanged. Real departure/return remains deferred.
