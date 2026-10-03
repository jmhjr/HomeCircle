# Beta 10 candidate validation

Beta 10 is an unpublished candidate. Beta 9 remains the current public prerelease and the installed version on the production HomeCircle test dashboard. The existing V2 dashboard was not changed.

## Changes

- Full-height cards can cover the browser viewport in kiosk mode. The card removes dashboard margins and temporarily hides Home Assistant's title bar; Exit kiosk restores the ordinary page. The kiosk URL continues to reopen that view.
- When no explicit report-time sensor is selected, a GPS tracker's valid `last_seen` attribute supplies the location report time. An HA state update remains a separate observation and never substitutes for an absent GPS report timestamp.
- When no explicit battery or charging sensor is selected, the chosen location tracker's `battery_level` and `battery_charging` attributes supply those details. Explicit sensor mappings keep priority.

## Checks

- 75 Python tests and 22 frontend tests pass. Ruff, Prettier, and Git whitespace checks pass.
- The public-file guard checked 89 files without a flagged pattern.
- The deterministic 14-file ZIP passed isolated Home Assistant install, upgrade, restart, and removal checks.
- The archive SHA-256 is `99c2478d2016aeaf212adc895b86f6dfde37e489d1861eea365f38be1aea4ab9`. An independent local hash check matched the archive, every inventory entry, and all 14 source files.
- The kiosk card was briefly staged on the disposable real-source HA. Browser inspection at a narrow display size confirmed the card reached all viewport edges, the HA title bar was hidden, and Exit kiosk restored the normal page. The exact published beta 9 card bytes and dashboard resource URL were then restored.
- Claude Opus 5.5 reviewed a sanitized public-source copy read-only and returned PASS. It noted that other cards could remain keyboard focusable underneath a kiosk overlay; this candidate documents a dedicated single-card view. Its file-read-only review could not hash the ZIP, so the local hash check above closes that gap.
- Production HomeCircle and the DAKboard have not yet received beta 10. Their full-screen and metadata behavior still require a physical acceptance check after an approved release and upgrade.

## Boundary

`last_seen` is used only when it is a valid GPS location-report attribute. The selected iPhone tracker currently has no such attribute, so its location report time remains unknown. Home Assistant's state update age is still shown separately.
