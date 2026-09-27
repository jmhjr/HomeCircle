# Per-source report times — beta 4

Version: 0.1.0-beta.4. See [beta 4 validation](BETA4-VALIDATION.md) for release and HACS upgrade results.

## Configure

Open HomeCircle Options, choose the household, and enable **Configure report times for each source** for the member. After any optional battery/driving sensor screen, HomeCircle asks for a location-report timestamp sensor for the person and each selected tracker. Leave fields empty when a source has no genuine location-report timestamp.

For a typical phone/cloud combination, leave the person timestamp empty and select a separate actual report sensor for each tracker that supplies one. A source without a report sensor remains unknown when its position is used. Router presence does not acquire a GPS timestamp from this feature.

Save at the final household confirmation. Skipping report-time configuration preserves existing mappings. Clearing a field removes its mapping. Removing a tracker prompts you to clear its old mapping before saving. Cancellation leaves saved settings unchanged.

## Existing settings

Existing beta 3 single-source mappings still work without edits. Opening per-source configuration copies the old source/timestamp pair into the new mapping in the draft and removes the old pair from that draft. Saving commits the conversion. Other supporting sensor mappings and pet thresholds retain their existing behavior.

If both formats are present, the explicit per-source mapping takes priority for that source; the legacy pair can still cover its own source when no explicit mapping exists. To edit converted mappings, use **Configure report times for each source**, rather than the older timestamp/source pair in optional sensor mappings.

## Behavior

HomeCircle chooses the timestamp for the source of the displayed location, which may be a supplemental GPS source when HA's active source is a router. It never transfers another source's age. Missing or invalid timestamps remain unknown. Freshness thresholds, Home/Away counts and source-conflict handling are unchanged.

All mapped sources and sensors participate in state subscriptions, missing-entity checks and snapshot read-permission checks.

## Validation

- 60 Python tests and 12 frontend tests passed, including legacy behavior, mapping conversion, clear/removal validation, missing report evidence and read-permission denial.
- Eight checkpoints in a clean disposable Core instance passed using the development ZIP and actual HA Person source switching: stale phone, fresh cloud, cloud unavailable with fallback to stale phone, router conflicts, supplemental GPS, explicit new report and integration reload.
- Ruff and pinned Core 2026.9.4 hassfest passed.
- Packaged lifecycle validation passed with install, upgrade fixture, separate-process restart and removal.

The source-switching inputs in the clean Core test were fictional; no provider accounts or production configuration were changed. The new configuration screens passed an [isolated browser walkthrough](PER-SOURCE-BROWSER-VALIDATION.md): selection, save, reopen and addition of a second source. Later, the Life360 and pet test member mappings in the separate real-source disposable instance were converted through Options, then verified after restart. The published HACS upgrade and physical-display acceptance are tracked in [beta 4 validation](BETA4-VALIDATION.md).
