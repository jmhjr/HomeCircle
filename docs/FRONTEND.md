# Card and frontend interface

Development version 0.0.3-dev1. See [ADR-002](adr/ADR-002-map-and-frontend.md) for library, licensing, network and authorization decisions.

## UI-only setup

1. In the disposable HA instance, add HomeCircle in Settings → Devices & services. Select existing people, sources, primary house and additional residences.
2. Settings → Dashboards → Add dashboard → New dashboard from scratch. Supply a title and create it.
3. Open the dashboard, choose Edit dashboard → Add card → Browse all cards → HomeCircle.
4. Use the visual editor for title, visible members and map background; save and choose Done. No provider account, map key, resource YAML or card YAML is required.

The tested automatic resource path is HA's storage mode. Existing YAML resource collections are preserved and are not covered by UI-only onboarding. Build the card before launching the development integration.

## Display and interaction

The card is dark, responsive and uses initials rather than private photos. Every member has Home, Away, Driving or Unavailable status; counts use the same normalized records. A locationless Home member still counts. A member at another assigned residence counts Home while the Home map selection focuses only on the primary house. Everyone restores the complete usable-location subset.

Select member cards or map markers to focus. Markers whose screen positions overlap form a numbered group; activate it to choose an individual. All controls use native buttons, visible focus styling and keyboard activation. Each card owns its own focus and map. The visual editor can hide members from an individual card and its counts, without changing backend selections or permissions.

The default background makes no tile requests. Optional OSM tiles are disclosed in the editor and have visible attribution. Network failure retains presence and markers. There is no geocoding, routing, history, satellite view, weather, provider refresh or photo fetching.

## Authenticated data contract

HA websocket command `homecircle/snapshot` accepts only the command type and standard message ID. Every request checks the active user's read permission on all configured input entities/zones. Missing any permission returns `unauthorized` with no payload; unloaded integration returns `not_ready`.

Schema version 1 exposes normalized member ID/name/status/place label, primary-house flag, usable nullable location with origin/report metadata, optional battery/charging/speed/driving, issue codes, category counts and focus IDs. It does not expose config entries, raw state attributes, tokens, active unselected source IDs, photos, or precise location history. Known conflicting locations are omitted from the projection. The static JavaScript endpoint contains code only and does not grant household access.

Each connected card requests a current snapshot every 15 seconds. Requests time out after 10 seconds, clearing stale display data. Reconnection requests new data. Disconnect/unload clears retained current snapshots; late responses are discarded. No persistent browser storage is used. Unknown GPS report time is labelled explicitly, independently of HA observation times.

## Resource ownership

The backend serves a local versioned module and registers it with Lovelace's pinned storage collection API. A small HA storage record remembers the resource ID HomeCircle created. Reload keeps one owned registration; unload removes it. Unrelated/manual resources and YAML collections are preserved. The static code route stays until HA restart after unload, but the data API returns no household while unloaded. Upgrade/removal through HACS remains a release gate.
