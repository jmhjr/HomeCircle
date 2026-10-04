# Set up HomeCircle

Use a test Home Assistant instance running Core 2026.9.4 or later. HomeCircle beta 11 is an experimental prerelease. It can use existing Home Assistant trackers or optionally connect to Life360 directly.

## 1. Get a working source into Home Assistant

If using an existing tracker, open Settings → Devices & services → Entities before adding HomeCircle and confirm that it exists, is enabled, and has a usable state. Check the source integration first if it is unavailable. A direct Life360 connection can be set up before its trackers appear.

| Source | What you need in HA | What HomeCircle can display |
| --- | --- | --- |
| iPhone | Companion app connected to this test instance, with its location tracker enabled | Location/presence; optional battery sensor |
| Life360 | An existing Home Assistant tracker, or a direct Life360 account connection in HomeCircle | Location/presence and report time that the tracker supplies |
| Pet GPS | A separately installed integration that actually exposes the pet's device tracker | Pet location/presence and optional supporting sensors |
| Router presence, including an existing eero source | An existing HA integration exposing a device tracker | Home/Away presence; a router-only source may have no map position |

For iPhone, connect the Companion app to the intended test server and follow its [location setup](https://companion.home-assistant.io/docs/core/location/). iOS controls background reporting. A server reachable only on your home network cannot receive phone updates while the phone is away from that network. HomeCircle does not create remote access. See the [Companion sensor documentation](https://companion.home-assistant.io/docs/core/sensors/) for battery and other available sensors.

Direct Life360 connection is optional; pet GPS still needs its own tracker source. In our acceptance setup, a separate existing pet integration supplied the pet tracker; that integration is not distributed with HomeCircle. If no pet tracker exists in HA, resolve its provider connection first. A missing pet tracker cannot be fixed by selecting Pet in HomeCircle.

## 2. Create people and places

For a Home Assistant Person, open Settings → People, create or edit the record, and assign its tracker. Follow HA's [Person setup](https://www.home-assistant.io/integrations/person/). You can instead select an existing tracker directly as a person in HomeCircle. Multiple sources for one individual belong to one person's record or selection rather than duplicate household members.

For a pet, select its existing tracker directly under **Pet trackers** in HomeCircle. A Home Assistant Person record is no longer required. Existing pets configured through Person records can remain there.

Check your Home zone in Settings → Areas, labels & zones → Zones. Create additional zones you need. HomeCircle distinguishes:

- **Primary family home:** applies to all members; the Home map button focuses this house.
- **Additional residences:** apply to the selected member and count as Home for that member.
- **Ordinary places:** labels such as work; do not count as a residence.

A member at an additional residence can count Home while being outside the Home button's map focus. Everyone includes all usable positions.

## 3. Install through HACS

1. With HACS already configured on the test instance, open its custom repositories menu.
2. Add `https://github.com/jmhjr/HomeCircle` with type **Integration**. See [HACS custom repositories](https://www.hacs.dev/docs/faq/custom_repositories/).
3. Open HomeCircle in HACS, enable beta/prerelease versions, and download **v0.1.0-beta.11**.
4. Restart Home Assistant.
5. Open Settings → Devices & services → Add integration → HomeCircle.

The release ZIP includes the card. There is no separate card download or manual resource entry for the tested storage-mode dashboard setup. GitHub source archives are not the installable release ZIP.

### Pet setup

The setup flow has separate **People** and **Pet trackers** fields. Select an existing `device_tracker` for each pet; a Person record is not required. You may set up a household with only pets. Each pet then gets an **Other homes** screen, pet location timing, and optional sensor/report-time screens. The tracker selected on the first screen remains that pet's source; it cannot be replaced on the member screen. Existing pets configured through HA Person records continue through **People** and retain their saved settings. This path passed a disposable Home Assistant UI walkthrough and an isolated upgrade rehearsal from the published beta 10 ZIP. It has not been installed on the live server.

### Direct Life360 setup

If your Life360 trackers already exist in Home Assistant, select those entities under **Home Assistant People**, **People trackers**, or **Pet trackers** as appropriate. You do not need to connect a Life360 account in HomeCircle. A **People trackers** selection creates a person member from an existing tracker without a separate HA Person record.

When a separate Life360 integration is already present, the household screen warns that connecting the same account directly may create another set of trackers and additional provider requests. Existing and HomeCircle-created trackers have distinct Home Assistant identities, so you can keep both connections during a switch. Select only one tracker for each member and disconnect the route you no longer need after checking the replacement.

To connect Life360 directly, turn on **Connect a Life360 account directly** on the household screen. Enter either an email and password or an access token. Some Life360 accounts with a verified phone number cannot use password sign-in; see the [Life360 integration maintainer's authorization guidance](https://github.com/pnbruckner/ha-life360#account-authorization-methods). HomeCircle saves the credential in HA config entry storage, then creates HA `device_tracker` entities for members it discovers. Life360 may delay the Circle/member list for several minutes, so the first save may show no members. When the trackers appear under Settings → Devices & services → Entities, reopen HomeCircle Options and choose the intended members under **People trackers** or **Pet trackers**. The admin card keeps a setup reminder until at least one HomeCircle-created tracker is explicitly selected; existing household members and external trackers do not clear it. You can mix them with existing HA People, pet trackers and other providers. HomeCircle prevents adding a tracker as a separate person or pet when a selected HA Person is explicitly linked to it or currently uses it as the active source. A matching display name alone is never treated as proof of ownership.

HomeCircle Options shows whether the direct account is still waiting for trackers or how many trackers have appeared and are reporting. It checks for newly added Circle members again during normal operation, so you do not need to restart Home Assistant to discover them. If Life360 delays the member list, leave the account connected and reopen Options after a few minutes.

If the account has available trackers but none is explicitly selected in HomeCircle, an admin's card says to finish setup in Options. The prompt clears after a tracker from that account is chosen. It does not choose a member automatically because the account owner must confirm which tracker belongs to whom.

If Life360 rejects the saved sign-in, Home Assistant opens a reauthentication repair prompt. Enter a credential for the same Life360 account. HomeCircle compares the account identity saved by recent setups and rejects a different verified account. Older development setups without a saved identity ask you to confirm that the replacement belongs to the same account before keeping the household selections. For a persistent connection or discovery problem, use the [tracker provider issue workflow](TRACKER-PROVIDER-ISSUES.md) and HomeCircle's sanitized HA diagnostics. Do not share raw provider logs or location data.

To disconnect the direct account, open HomeCircle Options and turn off **Connect a Life360 account directly**. First replace any selected HomeCircle Life360 trackers with another source, and remove any exact HA Person links to those trackers. The setup flow prevents disconnecting while a selected member still uses or is linked to a HomeCircle-owned tracker.

If the password or token changes, open HomeCircle Options, select **Replace saved Life360 sign-in**, and enter the new credential for the same account. Saved member selections remain in place. For an older development setup without a saved account identity, HomeCircle compares the old and new sign-ins when the old one still works. If it cannot check the old sign-in, the form asks you to confirm they belong to the same account. To switch to a different Life360 account, remove this HomeCircle setup and create a new household so old tracker selections are not carried across.

This direct path uses Life360's undocumented API through the `life360` Python client. Sign-in, Circle discovery and polling may be rate limited or change without notice. Only the account owner should provide a credential; do not paste it into issues, screenshots or chat. HomeCircle does not set a Recorder exclusion: Home Assistant's Recorder settings determine whether the new tracker states and locations are retained. Review those settings before connecting. Direct connection passed live-account checks in a disposable Home Assistant setup; movement on the real server remains untested.

## 4. Choose the household

1. Under **People**, **People trackers**, and **Pet trackers**, select the records or entities for the intended household members.
2. Select **Primary family home** and any **Ordinary places**.
3. On each member's **Choose trackers and places** screen, review the suggested single tracker and the listed GPS or presence capabilities. Check its owner and choose another tracker if appropriate. The suggestion reflects the current HA state, not measured reporting reliability. If names repeat, compare entity IDs. Existing multi-tracker selections are preserved when editing; leaving trackers empty permits person-only presence.
4. Select any additional residences for that member.
5. Set **Member type** to `person` or `pet`. Pet records are not detected automatically.
6. For pets, set the location freshness thresholds on the next **Pet location timing** screen.
7. Enable **Set up battery and motion sensors** if you have supporting sensors. Enable **Set up location report times** if a selected source exposes a genuine report-time sensor. Those choices open separate screens.
8. Repeat for each member. The **Review and save household** screen lists the selected homes, trackers, sensors, report times and pet timing. Submit to save; closing the flow discards the draft.

## 5. Add optional battery and report-time sensors

These fields select existing HA entities. An attribute on a tracker is not itself a selectable sensor.

| HomeCircle field | Required meaning |
| --- | --- |
| Battery percentage sensor | Numeric battery percentage with `%` units |
| Charging binary sensor | On/off charging state for this member |
| Speed sensor | Numeric speed in m/s, km/h or mph |
| Driving binary sensor | On/off driving evidence |
| Driving report timestamp sensor | Actual timestamp for that driving report; needs a driving binary sensor |

The **Status sensors** screen contains the five fields above. The separate **Location report time** screen visits each selected tracker and the person source; choose a genuine timestamp sensor for that source, or leave it empty. Older single-source mappings remain supported and are guided through the per-source screen when edited. See [per-source report times](PER-SOURCE-REPORTS.md) and [multiple-source checks](MULTI-SOURCE-VALIDATION.md).

Match each timestamp to the source named on its screen. A timestamp for a different source cannot establish the age of the active location.

Beta 10 reads valid `battery_level`, `battery_charging` and GPS `last_seen` attributes from the selected tracker when explicit sensors are not configured. Explicit sensor mappings take priority. Other provider attributes may need a separately configured HA template sensor. Verify an attribute's meaning in that provider's documentation before building a helper; there is no universal Life360/pet attribute recipe. Preserve unavailable values rather than replacing them with zero or the current time. If no genuine report timestamp is available, leave it unmapped: **Location report time unknown** is the correct result. HA's `last_changed` and `last_updated` are not GPS fix times.

To add mappings later, open HomeCircle's Options, continue to that member, and enable the appropriate status-sensor or report-time switch. Clearing a field on its screen removes that mapping. Skipping the screen preserves existing mappings.

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
- **Stale report:** inspect the actual source report age. HomeCircle polls only built in provider connections that you enabled; it does not poll independently installed tracking integrations.
- **Missing-source repair notice:** allow sources to finish starting, then use Options to replace removed or renamed entities if necessary.
- **Card missing after install:** restart HA, refresh the browser, and confirm the integration completed setup. UI-only resource registration was tested with storage-mode dashboards; YAML-managed resources need separate handling.

HACS upgrades require a restart. To uninstall from a test instance, first remove the HomeCircle integration entry in Settings → Devices & services, then uninstall HomeCircle in HACS and restart HA. Removing the entry deletes its saved HomeCircle selections; reinstall requires setup again. Keep a Home Assistant backup before testing removal. Source integrations and their entities are managed separately. The normal removal/reinstall sequence passed in [beta 4 validation](BETA4-VALIDATION.md); other removal orders have not been accepted yet.

## Validation scope

See [beta 11 validation](DIRECT-LIFE360-CANDIDATE-VALIDATION.md) for this release's tested scope. A full real departure/return test remains open.
