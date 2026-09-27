# Beta 3 validation

Published experimental prerelease: https://github.com/jmhjr/HomeCircle/releases/tag/v0.1.0-beta.3

- 57 Python tests and 12 frontend tests passed.
- Pinned Core 2026.9.4 hassfest: one integration, zero invalid.
- Packaged lifecycle passed: install, upgrade fixture, restart, entry removal and package removal; unrelated resources preserved.
- Actual published beta 2 code was restored and its served bundle verified before the HACS upgrade. HACS downloaded beta 3; all package files matched the release ZIP.
- After restart, HACS recorded beta 3, exactly one owned frontend resource remained, and the served bundle matched the ZIP.
- All saved HomeCircle data/options remained identical, including the pet settings entered during the prior preview and supporting sensor mappings. Three test records remained focusable. Pet thresholds remained 1440 minutes at home and 5 minutes away.
- Live browser showed unknown iPhone report time, a stale human report with an amber accent, and a pet report age in hours with Pet / Home status.

Physical DAKboard acceptance passed by user confirmation: readable report ages, amber stale indicators, and member selection followed by Everyone. The browser check separately verified one selected map position and restoration of all three positions.

Real departure/return remains deferred. Production HA was unchanged. Private component and settings backups remain available locally for rollback. No household configuration or screenshots were published to GitHub.
