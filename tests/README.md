# Acceptance plan

Milestone 1–3 flow/lifecycle, normalization and authorization tests run against HA Core 2026.9.4. See [validation evidence](../docs/MILESTONE-3-VALIDATION.md) and [test commands](../docs/DEVELOPMENT.md). The matrix below includes future milestones; automated tests do not imply real provider or physical-display acceptance. Separate browser evidence covers the initial card.

| Area | Required cases |
|---|---|
| Configuration | Discover people; active vs associated trackers; explicit fallback; cancel; duplicate entry; edit; removed entity; reload |
| Provider independence | No Life360 installed; two independent tracking sources; no provider credentials or direct network clients |
| Presence | Home, Away, evidenced Driving, Unknown/Unavailable; driving precedence; locationless Home |
| Residences | Member at primary house and at assigned dorm both count Home; house-only Home focus excludes dorm; ordinary places remain Away |
| Location | Null, zero, range limits, missing accuracy, invalid values, source conflicts; unavailable points cannot focus |
| Freshness | Report time separate from HA observation time; unknown timestamps; stale driving visibly qualified |
| Optional fields | Battery/charging absent; battery zero; explicitly mapped sensors; unknown speed unit hidden |
| Card | Member focus; group expand/collapse; category focus; empty categories; overview reset; two independent card instances |
| UI setup | Fresh HA/HACS install through card display without editing YAML; options survive restart |
| Packaging | Bundle registration once; upgrade/unload/removal; no damage to unrelated resources |
| Privacy | No raw states in logs/diagnostics; no personal artifacts in source/release; optional network providers disclosed |
| Display | Portrait overflow, keyboard/touch focus, missing-data labels; physical DAKboard/TouchHub later and separately |

The generic fixture in `fixtures/household.example.json` matches the milestone 1 selection snapshot. Synthetic numeric coordinates used by tests are explicitly zero via HA attribute constants; they are fictional test data, never a household location. No privacy checker exception is needed.
