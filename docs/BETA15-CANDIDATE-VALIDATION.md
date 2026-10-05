# Beta 15 candidate validation — 2026-10-04

HomeCircle now reads a selected GPS tracker's boolean `driving` attribute when no separate driving sensor is configured. It uses that same tracker's valid `last_seen` location report time to classify the flag. A fresh positive report shows Driving; an old positive report remains a last-reported note and does not enter the Driving count. Missing or malformed report times remain unverified. A selected driving sensor retains priority. Speed alone never establishes Driving.

The setup and Options status-sensor descriptions both explain this fallback and its freshness requirement. No household selection or tracker association is inferred from an entity name.

Candidate checks passed: 156 Python tests, 28 card tests, Ruff, the public-file guard, and `git diff --check`. The deterministic 21-file ZIP has SHA-256 `0c898ffc14df7f54cf1c6b356d14474566ac7faae6c2721075f26e1399e4b483`. A disposable Home Assistant package lifecycle passed creation, upgrade, separate-process restart, removal, and post-removal resource checks.

Production remains on beta 14. Live motion acceptance requires a fresh tracker report that actually says driving; the candidate tests do not establish that a provider will send one during a trip. Physical DAKboard acceptance is also pending.
