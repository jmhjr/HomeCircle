# Card and frontend interface

The current experimental prerelease is beta 17. Start with the [complete setup guide](SETUP.md). See [ADR-002](adr/ADR-002-map-and-frontend.md) for library, licensing, network and authorization decisions.

## UI-only setup

1. In the disposable HA instance, add HomeCircle in Settings → Devices & services. Select or create HA People, assign their trackers, and choose the primary house and additional places.
2. First setup creates a HomeCircle dashboard and card if none exists. Open it from the sidebar. If the card does not appear immediately after resource registration, refresh the browser once.
3. To add another card, choose Edit dashboard → Add card → HomeCircle. Use the visual editor for title, visible members and map background; save and choose Done. No provider account, map key, resource YAML or card YAML is required for the core path.

The tested automatic resource path is HA's storage mode. Existing YAML resource collections are preserved and are not covered by UI-only onboarding. A YAML-managed resource collection must add the module URL `/homecircle_static/homecircle-card.js?v=0.1.0-beta.17` through its own configuration and update the version after an upgrade. Release ZIPs include the built card; source checkouts require a frontend build.

## Display and interaction

The card is dark and responsive. It uses an HA-served or allowlisted Life360 portrait when available and initials otherwise. Every member has Home, Away, Driving or Unavailable status; counts use the same normalized records. A locationless Home member still counts. A member at another assigned residence counts Home while the Home map selection focuses only on the primary house. Everyone restores usable locations except members whose Show on map setting is off; selecting one of those members or a status category can still show their position.

Select member cards or map markers to focus. Markers whose screen positions overlap form a portrait or initials group; activate it to choose an individual. Controls use native buttons, visible focus styling and keyboard activation. Each card owns its own focus and map. The visual editor can hide members from an individual card and its counts, without changing backend selections or permissions.

Beta 6 adds an optional **Fill wall display height** setting for a dedicated full-width panel view. It measures the remaining browser height below the card and lets the map expand into that space. Ordinary cards keep their previous fixed map height when the setting is off.
On a full-height card, **Kiosk view** covers the browser viewport and hides the HA sidebar and title bar in that browser session; **Exit kiosk** restores the ordinary dashboard layout. The URL records the kiosk choice so refresh retains it. Use a dedicated view with one HomeCircle card so other cards do not sit behind the kiosk overlay. The option changes presentation only and does not change HA permissions.

New cards use OpenStreetMap street tiles by default, with disclosure in the editor and visible attribution. The Private background makes no external tile requests. Tile failure retains presence and markers. The card makes no geocoding or routing request. Satellite imagery, optional radar/forecast playback, and bounded local Recent activity are available. A separately enabled built in provider can refresh its own HA trackers. Explicit selection requests use supported tracker actions; external Life360 family requests require the administrator opt-in described in the setup guide. Allowlisted Life360 portraits may load from Life360 image hosts when available.

## Authenticated data contract

HA websocket command `homecircle/snapshot` accepts only the command type and standard message ID. Every request checks the active user's read permission on all configured input entities/zones. Missing any permission returns `unauthorized` with no payload; unloaded integration returns `not_ready`.

Schema version 1 exposes normalized member ID/name/status/place label, primary-house flag, usable nullable location with origin/report metadata, optional battery/charging/speed/driving, issue codes, category counts and focus IDs. It does not expose config entries, raw state attributes, tokens or precise location history. Allowlisted portrait URLs and current selected-source diagnostic positions are projected. Conflicting positions remain available in Details for diagnosis while the normalized map position may be omitted. The active unselected source ID is exposed only to administrators; other viewers see a generic indication. The static JavaScript endpoint contains code only and does not grant household access.

In beta 11, the snapshot also supplies a short, allowlisted tracker connection status to Home Assistant admins. The card shows it when a built in provider is still connecting or needs attention, then clears it after recovery. When trackers are ready but the household has no selected members, the card prompts an admin to finish selection in Options and clears the prompt after a member is chosen. Other authorized viewers receive no provider status. No account identifiers, error text, tracker IDs, coordinates, or API replies are included in that status.

Each connected card requests a current snapshot every 15 seconds. Requests time out after 10 seconds. Temporary failures retain the last snapshot with a visible warning. A changed user or connection, authorization denial, or disconnect clears retained household data; late responses are discarded. Reconnection requests new data. Browser storage holds only map presentation preferences, height and optional radar controls; it does not persist household snapshots or enabled radar state. Unknown GPS report time is labelled explicitly, independently of HA observation times.

Beta 6 also shows the HA source-state update age when no valid location-report timestamp is available. It labels that age as an HA state update and keeps the location report time unknown. Attribute-only state updates and delayed phone uploads mean the HA time cannot prove when a GPS fix was obtained.

Beta 16 identifies the active location source by its tracker or HA Person name and, when useful, its registered integration. Its member list scrolls independently while the map remains visible. An administrator's cog opens the task-based HomeCircle Options flow over the dashboard; kiosk mode hides that cog.

## Resource ownership

The backend serves a local versioned module and registers it with Lovelace's pinned storage collection API. A small HA storage record remembers the resource ID HomeCircle created. Beta 6 keeps that ID through automatic Options and Reconfigure reloads, including an unchanged Reconfigure save. A plain unload and removal of an unloaded entry clean up the owned resource; failed reload setup also cleans up after the entry lock is released. Unrelated/manual resources and YAML collections are preserved. If you registered the module manually, update its `?v=` URL after an upgrade; HomeCircle does not change user-owned resources. The static code route stays until HA restart after unload, but the data API returns no household while unloaded. HACS uninstall before entry removal still cannot invoke package cleanup. Actual HACS upgrade and normal removal checks are recorded in the beta release validation reports.
