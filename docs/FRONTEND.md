# Card and frontend interface

The current experimental prerelease is beta 18. Start with the [complete setup guide](SETUP.md). See [ADR-002](adr/ADR-002-map-and-frontend.md) for library, licensing, network and authorization decisions.

## UI-only setup

1. In the disposable HA instance, add HomeCircle in Settings → Devices & services. Select or create HA People, assign their trackers, and choose the primary house and additional places.
2. First setup creates a HomeCircle dashboard and card if none exists. Open it from the sidebar. If the card does not appear immediately after resource registration, refresh the browser once.
3. To add another card, choose Edit dashboard → Add card → HomeCircle. Use the visual editor for title, visible members and map background; save and choose Done. No provider account, map key, resource YAML or card YAML is required for the core path.

The tested automatic resource path is HA's storage mode. Existing YAML resource collections are preserved and are not covered by UI-only onboarding. A YAML-managed resource collection must add the module URL `/homecircle_static/homecircle-card.js?v=0.1.0-beta.18` through its own configuration and update the version after an upgrade. Release ZIPs include the built card; source checkouts require a frontend build.

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


## Import saved Life360 places

In HomeCircle settings, choose **Import places from Life360**, select a saved connection and Circle, then select places. HomeCircle can use either its own optional Life360 connection or an enabled connection from the separate Life360 integration. Authorization remains on the HA server and is never sent to the card. Failed authorization must be repaired in the connection's integration.

The preview excludes invalid locations, places at existing zone centers, and places matching the Primary Home name. Repeated names receive suggested suffixes and each selection is reviewed on a map with its radius in meters. The card picker supports individual checkboxes, Select all, Clear selection, and a local name filter. During map review, Skip this place removes the current place without validating its fields, then proceeds to the next review. If every selected place is skipped, the flow exits without creating zones. No zones are created until final confirmation. The import creates editable HA zones and adds them as HomeCircle place labels. It leaves Primary Home and existing zones unchanged. To count an imported zone as Home for a member, assign it separately under Other homes.

This is a one-time import using the unofficial Life360 API, not ongoing synchronization. Zones remain in HA after removing HomeCircle. If creation fails partway, created zones remain; retry completes the remaining places. Cancelling before confirmation makes no zone changes. Cancelling after a partial failure keeps created zones but does not save the HomeCircle draft. The importer uses one existing account at a time and retrieves only its chosen Circle's places.


## Automatic GPS selection

HomeCircle defaults to **Freshest reliable GPS** for Person members, including saved configurations without an explicit selection mode. It ranks only explicitly selected, available GPS trackers with valid coordinates and verified report timestamps. Per-source report sensors take precedence over a tracker's `last_seen`; HA entity update times alone are never used for ranking. Fresh reports outrank stale reports. Among reports within 60 seconds of the newest, HA's active selected GPS tracker is preferred. Otherwise the newest report wins. If every verified report is stale, HomeCircle follows HA Person rather than letting an old alternative change Home/Away. Existing pet freshness settings continue to apply. Without any verified GPS report times, HomeCircle falls back to HA Person behavior.

The chosen GPS coordinates determine HomeCircle zone classification, address and default battery attributes. Explicit supporting sensors keep precedence. HA Person state, tracker links and active-source selection are unchanged. Details shows a source-selection reason separately from HA's active source. Set **Location tracker selection → Follow HA Person** in member settings to opt out. Tracker-only members continue to use their explicitly assigned tracker.


## Pictures for tracker-only members

Open HomeCircle settings → Person and tracker settings, select a tracker-only member, then choose **Change picture**. Upload a JPG, PNG, or GIF up to 10 MB, adjust **Zoom** and drag the circular preview (or use the horizontal and vertical sliders), then choose **Save picture**. **Reset crop** restores a centered fit of the whole photo. Zoom supports 0.5×–8×, with white padding when zoomed out. Cropping happens locally in your browser; only the resulting 512 × 512 JPG is uploaded, with transparent areas filled white. Selecting a file or adjusting its crop does not upload it until you save. The upload uses Home Assistant's authenticated native image service; photos remain on your HA server. HomeCircle stores only the image reference for the selected member. Native HA image links can be viewed without login by anyone holding the link; treat them as private. No picture data goes to tracking providers or external image services.

**Remove picture** clears the custom reference on save, restoring the tracker’s original picture or initials. It does not delete HA’s uploaded image. Uploads remain in HA if setup is cancelled or HomeCircle is removed. Existing HA Person pictures continue to be managed in People settings. Saved tracker pictures persist through details edits and HA reloads. The member details dialog shows the same picture beside its title; missing or failed pictures fall back to initials. Refresh details updates the displayed picture.

Tracker battery categories (Full, Medium, Low, Very Low) are shown separately
from numeric battery percentages. Cards label categories as last-reported data;
details shows the source's battery report time. Low and Very Low use warning
styling. Missing categories remain unknown, and unselected trackers cannot
supply battery data.

Reported address labels use Street, City for every tracker provider, omitting
US state and ZIP components when identifiable. If the report contains a street
and state with no city, show the street alone; do not invent a city. External city lookup requires the separate opt-in below. Named configured places remain the preferred label.
Fresh reports say At; stale or unverified reports say Last reported.

## Optional city lookup

HomeCircle settings → City lookup enables Photon without an account or API key.
The switch starts off. Enabling sends selected usable tracker coordinates to
photon.komoot.io when HomeCircle is viewed, only outside named places and when
the tracker does not report a city. Names, entity IDs, timestamps and account
credentials are not sent. Provider street text is preferred; Photon can supply
a street when the tracker has none. Missing results preserve the reported
address fallback, and lookups never change GPS report times or presence.

The HA-local cache uses hashed coordinate cells of approximately 11 metres,
reuses results for up to seven days and holds at most 256 entries. Limits are
persisted before requests: at most 20 requests per hour and 200 per rolling
day, at least one second between requests and five minutes between attempts
for each member. HTTP requests time out after eight seconds, do not follow
redirects and accept at most 64 KiB. Unloading cancels pending work. Disable
the switch to stop requests and stop projecting lookup results. The cached
addresses remain in HA's local storage until subsequently expired/pruned.
Removing the integration deletes its city cache. Coordinate hashes are not
anonymization; treat cached addresses as private. Private map background does
not disable this independently enabled lookup.

Photon is a public demo service and may throttle requests or be unavailable;
it provides no availability guarantee. Street and city data attribution is
shown on the card. See https://github.com/komoot/photon#demo-server and
https://www.openstreetmap.org/copyright.
