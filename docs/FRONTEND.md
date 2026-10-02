# Card and frontend interface

Experimental beta 6 prerelease. Start with the [complete setup guide](SETUP.md). See [ADR-002](adr/ADR-002-map-and-frontend.md) for library, licensing, network and authorization decisions.

## UI-only setup

1. In the disposable HA instance, add HomeCircle in Settings → Devices & services. Select existing people, sources, primary house and additional residences.
2. Settings → Dashboards → Add dashboard → New dashboard from scratch. Supply a title and create it.
3. Open the dashboard, choose Edit dashboard → Add card → Browse all cards → HomeCircle.
4. Use the visual editor for title, visible members and map background; save and choose Done. No provider account, map key, resource YAML or card YAML is required.

The tested automatic resource path is HA's storage mode. Existing YAML resource collections are preserved and are not covered by UI-only onboarding. A YAML-managed resource collection must add the module URL `/homecircle_static/homecircle-card.js?v=0.1.0-beta.6` through its own configuration. Release ZIPs include the built card; source checkouts require a frontend build.

## Display and interaction

The card is dark, responsive and uses initials rather than private photos. Every member has Home, Away, Driving or Unavailable status; counts use the same normalized records. A locationless Home member still counts. A member at another assigned residence counts Home while the Home map selection focuses only on the primary house. Everyone restores the complete usable-location subset.

Select member cards or map markers to focus. Markers whose screen positions overlap form a numbered group; activate it to choose an individual. All controls use native buttons, visible focus styling and keyboard activation. Each card owns its own focus and map. The visual editor can hide members from an individual card and its counts, without changing backend selections or permissions.

Beta 6 adds an optional **Fill wall display height** setting for a dedicated full-width panel view. It measures the remaining browser height below the card and lets the map expand into that space. Ordinary cards keep their previous fixed map height when the setting is off.
On a full-height card, **Kiosk view** hides the HA sidebar and top-bar controls in that browser session; **Exit kiosk** restores them. The URL records the kiosk choice so refresh retains it. The option changes presentation only and does not change HA permissions.

The default background makes no tile requests. Optional OSM tiles are disclosed in the editor and have visible attribution. Network failure retains presence and markers. There is no geocoding, routing, history, satellite view, weather, provider refresh or photo fetching.

## Authenticated data contract

HA websocket command `homecircle/snapshot` accepts only the command type and standard message ID. Every request checks the active user's read permission on all configured input entities/zones. Missing any permission returns `unauthorized` with no payload; unloaded integration returns `not_ready`.

Schema version 1 exposes normalized member ID/name/status/place label, primary-house flag, usable nullable location with origin/report metadata, optional battery/charging/speed/driving, issue codes, category counts and focus IDs. It does not expose config entries, raw state attributes, tokens, active unselected source IDs, photos, or precise location history. Known conflicting locations are omitted from the projection. The static JavaScript endpoint contains code only and does not grant household access.

Each connected card requests a current snapshot every 15 seconds. Requests time out after 10 seconds, clearing stale display data. Reconnection requests new data. Disconnect/unload clears retained current snapshots; late responses are discarded. No persistent browser storage is used. Unknown GPS report time is labelled explicitly, independently of HA observation times.

Beta 6 also shows the HA source-state update age when no valid location-report timestamp is available. It labels that age as an HA state update and keeps the location report time unknown. Attribute-only state updates and delayed phone uploads mean the HA time cannot prove when a GPS fix was obtained.

## Resource ownership

The backend serves a local versioned module and registers it with Lovelace's pinned storage collection API. A small HA storage record remembers the resource ID HomeCircle created. Beta 6 keeps that ID through automatic Options and Reconfigure reloads, including an unchanged Reconfigure save. A plain unload and removal of an unloaded entry clean up the owned resource; failed reload setup also cleans up after the entry lock is released. Unrelated/manual resources and YAML collections are preserved. If you registered the module manually, update its `?v=` URL after an upgrade; HomeCircle does not change user-owned resources. The static code route stays until HA restart after unload, but the data API returns no household while unloaded. HACS uninstall before entry removal still cannot invoke package cleanup. Actual HACS upgrade and normal removal checks are recorded in the beta release validation reports.
