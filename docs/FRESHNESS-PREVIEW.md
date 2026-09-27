# Freshness development preview

Version: 0.1.0-beta.3.dev1. Installed only in the disposable real-source instance; public beta 2 assets and production are unchanged. HACS still records the last downloaded release as beta 2; this is a manually installed development preview, not a HACS upgrade or published release.

## Changes

- Report ages use minutes below one hour, whole hours below one day, then whole days. Invalid/future timestamps remain unknown.
- Stale member cards have an amber leading border and an explicit amber Stale label; fresh evidence removes the accent.
- Member Options explicitly choose Person or Pet. People retain the five-minute location threshold. Pets have adjustable thresholds from 1 to 10080 minutes: default 1440 minutes at any assigned residence and 5 minutes away. These affect location freshness only; driving evidence retains its existing rules.
- All report ages remain visible. A threshold does not generate a fresh GPS fix, assert safety, or change Home/Away state. Existing configurations remain Person unless explicitly changed.

## Validation

57 Python tests and 12 frontend tests passed, including pet home/away boundary behavior, unknown evidence, saved options, readable age units and stale styling recovery. Ruff, formatting and pinned Core 2026.9.4 hassfest passed.

Existing supporting mappings survived preview installation and Options save. Ruby was explicitly marked Pet with the default thresholds. Live UI showed Pet · Home and Reported 22 hours ago without a stale flag; a human Life360 report updated to two minutes old. iPhone location-report time remained unknown. No source reports or locations were fabricated.

Rollback: restore the saved beta 2 component directory from ignored work/beta2-before-freshness, restore saved household options from work/pre-freshness-options.json if needed, and restart this disposable instance. The local backup contains component code only; household options remain private. No new release was published. Physical departure/return remains deferred.
