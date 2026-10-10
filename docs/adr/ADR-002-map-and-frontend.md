# ADR-002: Bundled Leaflet, optional street tiles, authenticated snapshots

Status: Implemented for milestone 3 development, 2026-09-27.

The card bundles Leaflet 1.9.4 (BSD-2-Clause), its stylesheet and license. It uses native custom elements with a visual editor; esbuild produces one local JavaScript module. No CDN script or remote font is loaded. Native buttons and textContent keep supplied names as text.

The default map shows geographically positioned markers on an unlabelled background without external requests. Users may opt in to OpenStreetMap street tiles in the visual editor. The disclosure appears before selection. Tile requests reveal viewed regions, client network metadata and the site origin; names and HA credentials are not sent. Basic presence continues if tiles fail. Browser caching and visible attribution remain enabled, referrer policy sends the origin, and there is no prefetch/offline download feature. Automated browser QA keeps external tiles disabled.

## 2026-10-04 usability revision

The user chose street tiles as the default after testing the fresh-install dashboard. New cards and automatically created dashboards now use OpenStreetMap tiles. The editor and setup guide disclose the external tile request, and users can choose the private background. An explicit saved `map_tiles: none` choice remains private. Cards with no saved map choice adopt the new default when the frontend updates. The earlier paragraph records the milestone 3 decision; this revision supersedes its default and opt-in behavior.

Sources checked 2026-09-27: [Leaflet downloads](https://leafletjs.com/download.html), [OSM tile usage policy](https://operations.osmfoundation.org/policies/tiles/), [OSMF privacy policy](https://osmfoundation.org/wiki/Privacy_Policy). Leaflet's full license is copied into the build. OSM data attribution links to its copyright/ODbL information when enabled.

`homecircle/snapshot` uses HA's authenticated websocket connection and checks read permission on every selected source and zone on every request. A user missing any required permission receives no household payload. The projection includes only normalized display data, never raw attributes or configuration. Card visibility controls are not access control. Beta 17 adds bounded local activity without coordinates and browser-local presentation preferences; neither retains precise location history. See the privacy guide for fields and retention.

Each connected card refreshes every 15 seconds; a 10-second deadline flags temporary failures while retaining the last snapshot. Disconnect, changed user/connection, and denied requests clear household data. Card instances have separate focus, maps and bounded current snapshots. Backend evidence aging remains 30 seconds.

The integration registers one versioned local Lovelace module in storage mode and records ownership of its resource ID. It updates/removes only an owned resource whose path still matches; unrelated and manually registered resources are preserved. YAML resource collections are left untouched and are outside the UI-only onboarding acceptance target. Static code remains registered until HA restart after unload, contains no household data, and is harmless without the authenticated API.

### Later beta amendment — current defaults and optional radar

The October 4 revision changed new cards to use OpenStreetMap street tiles by default, with disclosure in setup/editor and a Private background that prevents external map traffic. The original default-private decision above is historical. Beta 17 adds optional USGS Satellite imagery and separately enabled IEM radar/HRRR forecasts. Tile providers receive viewed areas and network metadata; names and HA credentials are not sent. Radar starts off and Private mode prevents its requests. See [privacy](../PRIVACY.md) for the current behavior.
