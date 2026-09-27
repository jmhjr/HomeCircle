# ADR-002: Bundled Leaflet, optional street tiles, authenticated snapshots

Status: Implemented for milestone 3 development, 2026-09-27.

The card bundles Leaflet 1.9.4 (BSD-2-Clause), its stylesheet and license. It uses native custom elements with a visual editor; esbuild produces one local JavaScript module. No CDN script or remote font is loaded. Native buttons and textContent keep supplied names as text.

The default map shows geographically positioned markers on an unlabelled background without external requests. Users may opt in to OpenStreetMap street tiles in the visual editor. The disclosure appears before selection. Tile requests reveal viewed regions, client network metadata and the site origin; names and HA credentials are not sent. Basic presence continues if tiles fail. Browser caching and visible attribution remain enabled, referrer policy sends the origin, and there is no prefetch/offline download feature. Automated browser QA keeps external tiles disabled.

Sources checked 2026-09-27: [Leaflet downloads](https://leafletjs.com/download.html), [OSM tile usage policy](https://operations.osmfoundation.org/policies/tiles/), [OSMF privacy policy](https://osmfoundation.org/wiki/Privacy_Policy). Leaflet's full license is copied into the build. OSM data attribution links to its copyright/ODbL information when enabled.

`homecircle/snapshot` uses HA's authenticated websocket connection and checks read permission on every selected source and zone on every request. A user missing any required permission receives no household payload. The projection includes only normalized display data, never raw attributes or configuration. Card visibility controls are not access control. No history or browser persistent storage is added.

Each connected card refreshes every 15 seconds; a 10-second deadline clears unavailable data. Unload and denied requests clear the display. Card instances have separate focus, maps and bounded current snapshots. Backend evidence aging remains 30 seconds.

The integration registers one versioned local Lovelace module in storage mode and records ownership of its resource ID. It updates/removes only an owned resource whose path still matches; unrelated and manually registered resources are preserved. YAML resource collections are left untouched and are outside the UI-only onboarding acceptance target. Static code remains registered until HA restart after unload, contains no household data, and is harmless without the authenticated API.
