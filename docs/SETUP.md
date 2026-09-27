# Set up HomeCircle beta 3

Use a test Home Assistant instance running Core 2026.9.4 or later. HomeCircle is an experimental prerelease. It displays existing Home Assistant entities; tracking accounts and devices are set up separately.

## 1. Get a working source into Home Assistant

Before adding HomeCircle, open Settings → Devices & services → Entities and confirm that your tracker exists, is enabled, and has a usable state. Check the source integration first if it is unavailable.

| Source | What you need in HA | What HomeCircle can display |
| --- | --- | --- |
| iPhone | Companion app connected to this test instance, with its location tracker enabled | Location/presence; optional battery sensor |
| Life360 | A separately installed integration that exposes the intended member as a device tracker | The location/presence that integration supplies |
| Pet GPS | A separately installed integration that actually exposes the pet's device tracker | Pet location/presence and optional supporting sensors |
| Router presence, including an existing eero source | An existing HA integration exposing a device tracker | Home/Away presence; a router-only source may have no map position |

For iPhone, connect the Companion app to the intended test server and follow its [location setup](https://companion.home-assistant.io/docs/core/location/). iOS controls background reporting. A server reachable only on your home network cannot receive phone updates while the phone is away from that network. HomeCircle does not create remote access. See the [Companion sensor documentation](https://companion.home-assistant.io/docs/core/sensors/) for battery and other available sensors.

HomeCircle does not install or authenticate Life360 or pet integrations. Human Life360 support does not imply Pet GPS support. In our acceptance setup, a separate existing pet integration supplied the pet tracker; that integration is not distributed with HomeCircle. If no pet tracker exists in HA, stop here for that member and resolve the provider connection first. A missing pet tracker cannot be fixed by selecting Pet in HomeCircle.

## 2. Create people and places

In Settings → People, create or edit a person and assign their tracker. Follow HA's [Person setup](https://www.home-assistant.io/integrations/person/). Use one person per household member; multiple sources for one individual belong to that person's record rather than separate duplicate members.

Beta 3 also requires an HA person record for a pet. Create a record for the pet without creating a login account, and assign the pet tracker. You will label it Pet inside HomeCircle later.

Check your Home zone in Settings → Areas, labels & zones → Zones. Create additional zones you need. HomeCircle distinguishes:

- **Primary family home:** applies to all members; the Home map button focuses this house.
- **Additional residences:** apply to the selected member and count as Home for that member.
- **Ordinary places:** labels such as work; do not count as a residence.

A member at an additional residence can count Home while being outside the Home button's map focus. Everyone includes all usable positions.

## 3. Install through HACS

1. With HACS already configured on the test instance, open its custom repositories menu.
2. Add `https://github.com/jmhjr/HomeCircle` with type **Integration**. See [HACS custom repositories](https://www.hacs.dev/docs/faq/custom_repositories/).
3. Open HomeCircle in HACS, enable beta/prerelease versions, and download **v0.1.0-beta.3**.
4. Restart Home Assistant.
5. Open Settings → Devices & services → Add integration → HomeCircle.

The release ZIP includes the card. There is no separate card download or manual resource entry for the tested storage-mode dashboard setup. GitHub source archives are not the installable release ZIP.

## 4. Choose the household

1. Under **People**, select the person records you prepared, including the pet record.
2. Select **Primary family home** and any **Ordinary places**.
3. On each member's **Sources and residences** screen, confirm the associated trackers. Select only trackers for that member. Leaving trackers empty permits person-only presence.
4. Select any additional residences for that member.
5. Set **Member type** to `person` or `pet`. Pet records are not detected automatically.
6. For pets, review the freshness thresholds below.
7. Enable **Configure optional sensor mappings** if you have supporting sensor entities; otherwise continue.
8. Repeat for each member, then submit **Save household**. Changes remain a draft until this final save.

## 5. Add optional battery and report-time sensors

These fields select existing HA entities. An attribute on a tracker is not itself a selectable sensor.

| HomeCircle field | Required meaning |
| --- | --- |
| Battery percentage sensor | Numeric battery percentage with `%` units |
| Charging binary sensor | On/off charging state for this member |
| Speed sensor | Numeric speed in m/s, km/h or mph |
| Driving binary sensor | On/off driving evidence |
| Driving report timestamp sensor | Actual timestamp for that driving report; needs a driving binary sensor |
| Location report timestamp sensor | Actual timestamp when the location source reported its fix |
| Source described by the location timestamp | The exact selected tracker (or person) described by that timestamp |

Select the location timestamp **and** its source together. Do not bind a pet timestamp to a phone tracker. If the active source changes, a timestamp for another source cannot establish the age of the active location.

If the provider only exposes battery or report time as attributes, a separately configured HA template sensor may be needed. Verify the attribute's meaning in that provider's documentation before building a helper; there is no universal Life360/pet attribute recipe. Preserve unavailable values rather than replacing them with zero or the current time. If no genuine report timestamp is available, leave it unmapped: **Location report time unknown** is the correct result. HA's `last_changed` and `last_updated` are not GPS fix times.

To add mappings later, open HomeCircle's Options, continue to that member and enable **Configure optional sensor mappings**. Clearing a field on the sensor screen removes that mapping. Skipping that screen preserves existing mappings.

## 6. Understand freshness

| Member | Location becomes stale after |
| --- | --- |
| Person | Five minutes |
| Pet at any assigned residence | 1440 minutes (24 hours), by default |
| Pet away | Five minutes, by default |

Pet thresholds accept 1–10080 minutes. They affect location freshness only. Driving retains its five-minute evidence rule. Ages display in minutes, hours or days; stale reports have an amber label and leading border. Unknown time remains unknown.

A longer threshold does not wake a tracker, produce a new GPS fix, or establish that a pet is safe. Freshness does not change Home/Away status or household counts.

## 7. Add and check the card

Create a dashboard from scratch in Settings → Dashboards. Open it, select Edit dashboard → Add card → Browse all cards → HomeCircle. Choose a title and visible members, save, then Done. Use a full-width/panel view for a dedicated wall display if desired.

Keep the default private background for no external tile requests. Optional street tiles make requests to the external tile service for the displayed area.

Check these results:

- Each member appears once with the expected status.
- Tap a member: the map focuses their usable position. A presence-only member can count without a marker.
- Tap Everyone: all usable positions return.
- Open a numbered overlapping group and select a member.
- Battery and report ages agree with the selected source entities. Unknown values are acceptable when evidence is absent.
- Refresh the browser and verify the card still loads. On a wall display, repeat the taps physically.

## Troubleshooting and later changes

- **No people in the selector:** create enabled HA person records first, including one for the pet.
- **No pet tracker:** fix the separate provider integration; Member type does not create a tracker.
- **No map position:** check the active source for coordinates. Router presence alone may be locationless.
- **Sensor missing from picker:** check its entity domain and enabled state. Tracker attributes need separate sensors.
- **Stale report:** inspect the actual source report age; HomeCircle does not poll or refresh providers.
- **Missing-source repair notice:** allow sources to finish starting, then use Options to replace removed or renamed entities if necessary.
- **Card missing after install:** restart HA, refresh the browser, and confirm the integration completed setup. UI-only resource registration was tested with storage-mode dashboards; YAML-managed resources need separate handling.

HACS upgrades require a restart. Removing the HomeCircle integration deletes its household selections; reinstalling requires setup again. Keep a Home Assistant backup before testing removal. Source integrations and their entities are managed separately.

## Validation scope

See [the clean setup check](SETUP-VALIDATION.md) and [beta 3 acceptance](BETA3-VALIDATION.md). Synthetic setup checks do not establish provider compatibility or physical touch acceptance. Real departure/return testing remains deferred.
