# Beta 2 failure recovery and HACS upgrade — 2026-09-27

Published experimental release: https://github.com/jmhjr/HomeCircle/releases/tag/v0.1.0-beta.2

## Failure and recovery

An isolated real-browser harness used fictional source snapshots and a local HTTP tile endpoint. It initially returned HTTP 503, then valid image responses. No real location was sent to a map service.

Passed: tile failure preserves markers; member selection preserves the failure warning; unavailable source removes its marker and changes category counts; recovery restores its marker and Home count; Away and Everyone remain functional during failures; a successful tile-loading cycle clears the warning. This is browser acceptance with synthetic snapshots, complemented by HA Python normalization tests; it does not claim a live provider outage was induced.

Fixed a discovered bug: normal rendering previously overwrote the tile-error warning. The card now retains tile failure state through selection changes and resets it after successful loading or map disposal.

## Validation and upgrade

- 55 Python tests and 10 frontend tests passed; formatting/privacy checks passed.
- Official pinned Core 2026.9.4 hassfest: one integration, zero invalid.
- Packaged install, version-only upgrade rehearsal, restart, entry removal and package-removal restart passed in isolated Core processes.
- Actual HACS 2.0.5 upgrade from published beta 1 to published beta 2 passed in the existing disposable real-source HA instance.
- All installed package files matched the beta 2 ZIP. Household data/options survived restart unchanged; all three test records remained map-focusable.
- Exactly one owned resource referenced beta 2, and its served JavaScript matched the ZIP. The dashboard was switched to the published card and the temporary preview resource removed.

Production HA and original touch-test instance unchanged. No stable release approved. Physical departure/return remains deferred, physical touch acceptance of the new layout remains pending, and removal through HACS has not been tested.
