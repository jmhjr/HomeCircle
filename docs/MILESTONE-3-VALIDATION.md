# Milestone 3 validation

Validated 2026-09-27. Local development version 0.0.3-dev1; no release or production deployment.

## Implemented

- HA-authenticated `homecircle/snapshot` with per-request read checks on every selected source/zone; explicit normalized projection, no raw attributes/config/history.
- Versioned local card bundle and owned Lovelace resource lifecycle; unrelated, manual and YAML resources preserved.
- Native card/editor, bundled Leaflet and license, title/member visibility controls, optional disclosed OSM tiles (off by default).
- Member and category focus, primary-house Home focus, Everyone reset, selectable overlapping markers, dark portrait layout and honest missing/report-time labels.

## Automated evidence

- **54 Python tests pass** on HA Core 2026.9.4 / Python 3.14.7. They retain all prior flow/normalization tests and add real HA websocket projection/permission-denial/unload checks and resource ownership/reload/YAML preservation checks.
- **9 frontend tests pass**: count/focus distinction, hidden-member filtering, screen overlap, unknown/stale time labels, private map default, denial cleanup, disconnected/late-response handling, editor cleanup and text-only name rendering. DOM lifecycle tests use the actual built bundle; map interaction is checked in the browser.
- **Separate-process restart runner passes both phases**, retaining Options and count/focus behavior using real Core and disposable storage.
- Ruff, frontend formatting, JSON/local Markdown links and the public-file guard pass. Generated bundle and Leaflet license were inspected separately; they contain local code/vendor assets, no test household configuration or credentials.
- Python flow tests use disabled sockets by default; websocket tests enable a local aiohttp test server. Tests do not intentionally contact location providers. Browser QA uses only synthetic sources.

## Real HA browser evidence

- HomeCircle setup completes with GPS and locationless members and a member-specific residence.
- Automatic resource registration makes HomeCircle visible in the card picker. Created a new dashboard and added/configured/saved the card using the visual editor only; no resource/card YAML.
- Member → Home → Away → Everyone sequence produces the expected focus labels and retains counts.
- Two synthetic people at the same coordinates produce a group marker; expanding it permits selecting the second member.
- A member at an assigned second residence counts Home while Home focus reports zero usable primary-house positions when the other Home member is locationless.
- Two cards retain independent focus.
- Desktop 1280×900 and portrait 390×844 render without horizontal clipping; pointer and keyboard activation exercised. This is not physical kiosk/touch-device acceptance.
- Removing the synthetic residence raises a HomeCircle repair. Options displays the unknown selection; removing it and saving succeeds, clears the repair and reloads the integration.
- Browser-triggered restart exits with normal HA code **100** in the minimal Core worker, relaunches with the same disposable storage, and restores both cards, title, selections and saved repair correction. Post-restart Options confirms the residence removal persisted.
- Stopping the disposable instance clears both cards of member/map data and shows Home Assistant disconnected. The launcher removed temporary storage; both test ports were closed afterward.
- Latest bundle loads without HomeCircle console errors. External street tiles remained disabled; real OSM availability/failure behavior is not claimed from these checks.

## Test-environment finding

The broader standalone HA CLI crashed at Python interpreter shutdown with SIGSEGV, including in a second isolated Python 3.14.2 distribution. Changing only the launcher wrapper did not resolve it. Bare programmatic Core shutdown and the separate-process runner passed. The final browser launcher uses `bootstrap.async_from_config_dict` and `hass.async_run` in a small worker and passes the actual browser restart. No exceptions or abnormal exit codes are suppressed/reclassified as success. The broad CLI native cause remains unidentified; this is not a supported-installation-method certification. No Xcode license/developer-directory settings were changed.

## Remaining release gates

Public GitHub identity/manifest metadata; reviewed HACS release archive/install/upgrade/removal; real independent provider acceptance; broader HA compatibility; real tile-service/network-failure acceptance; physical display/touch acceptance. The existing V2/reference remains unchanged. A separate production rollout and authorization are required.

Work remains uncommitted in the original repository on unborn `feature/homecircle-card`. No staging, commit, remote, tag, publication, production HA access, V2 edit or private snapshot access occurred.
