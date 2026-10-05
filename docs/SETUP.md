# Set up HomeCircle

Use a test Home Assistant instance running the validated Core 2026.9.4 baseline. Published beta 16 is an experimental prerelease; broader Core compatibility has not been established. New people and pets use the Person-first screens below; existing tracker-only members remain supported. HomeCircle can use existing Home Assistant trackers or optionally connect to Life360 directly.

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

Every new HomeCircle member, including a pet, needs a Home Assistant Person record. Create one in HomeCircle setup, or open Settings → People first. Follow HA's [Person setup](https://www.home-assistant.io/integrations/person/). HomeCircle links the chosen tracker to that Person when you save. Multiple sources for one individual belong to one Person rather than duplicate household members.

For a pet, create a Home Assistant Person for the pet, then choose its existing tracker and set **Member type** to Pet. Older tracker-only pets remain usable and can be moved to a Person from HomeCircle Options.

Check your Home zone in Settings → Areas, labels & zones → Zones. You can create missing zones there or while setting up HomeCircle. HomeCircle distinguishes:

- **Primary family home:** applies to all members; the Home map button focuses this house.
- **Additional residences:** apply to the selected member and count as Home for that member.
- **Places shown while Away:** labels such as work or school; these do not count as Home.

On the household screen, choose **Create a new home or place zone** to set a name, map location, radius, and use. The flow returns to your household selections. A new primary home or Away place is selected automatically. For **Another home for a member**, select the new zone on that member's **Other homes** screen. You can also choose **Create another home zone** directly on a member's screen; it returns with that zone selected for the member. Creating a zone adds it to Home Assistant immediately, even if you later close HomeCircle setup.

A member at an additional residence can count Home while being outside the Home button's map focus. Everyone includes all usable positions.

## 3. Install through HACS

1. With HACS already configured on the test instance, open its custom repositories menu.
2. Add `https://github.com/jmhjr/HomeCircle` with type **Integration**. See [HACS custom repositories](https://www.hacs.dev/docs/faq/custom_repositories/).
3. Open HomeCircle in HACS. In Download or Redownload, open **Need a different version?**, choose **Release**, select **v0.1.0-beta.16**, and download it. If HACS already offers beta 16 in the dialog, confirm that version before downloading. A branch commit is not the versioned release. Every HomeCircle release is currently a prerelease, so HACS can show the branch commit as its available version while beta updates are off. For future beta update checks, enable and turn on HACS's **HomeCircle pre-release** switch in Home Assistant's Entities settings; it is disabled by default. [HACS explains this switch](https://www.hacs.dev/docs/use/entities/switch/).
4. Restart Home Assistant.
5. Open Settings → Devices & services → Add integration → HomeCircle.

HACS downloads the files; **Add integration** creates the HomeCircle household and selections. Both steps are required. The release ZIP includes the card. There is no separate card download or manual resource entry for the tested storage-mode dashboard setup. GitHub source archives are not the installable release ZIP.

### Pet setup

Select or create a Home Assistant Person for each pet. The next screen asks for its `device_tracker`; then set **Member type** to Pet and configure its other homes, location timing, and optional sensors. You may set up a household with only pets. The chosen tracker remains that pet's source until you change its HomeCircle settings. Existing tracker-only pets remain usable until you move them to a Person.

### Direct Life360 setup

If your Life360 trackers already exist in Home Assistant, choose or create a Home Assistant Person for each member, then select that Person's existing Life360 tracker. You do not need to connect a Life360 account in HomeCircle. Home Assistant does not identify whether a tracker belongs to a person or pet; choose **Member type** yourself.

When a separate Life360 integration is already present, the household screen warns that connecting the same account directly may create another set of trackers and additional provider requests. Existing and HomeCircle-created trackers have distinct Home Assistant identities, so you can keep both connections during a switch. Select only one tracker for each member and disconnect the route you no longer need after checking the replacement.

To connect Life360 directly, turn on **Connect a Life360 account directly** on the household screen. Enter either an email and password or an access token. Some accounts with a verified phone number cannot use password sign-in; see the [Life360 integration maintainer's authorization guidance](https://github.com/pnbruckner/ha-life360#account-authorization-methods). HomeCircle saves the credential in HA config entry storage, then creates HA `device_tracker` entities for members it discovers. Life360 may delay the Circle/member list for several minutes, so the first save may show no members. When the trackers appear under Settings → Devices & services → Entities, reopen HomeCircle Options, choose **Add a tracker**, select or create a Person, then choose that Person's tracker. The admin card keeps a setup reminder until at least one HomeCircle-created tracker is explicitly selected; existing household members and external trackers do not clear it. You can mix Life360 with existing HA People, pet trackers and other providers. HomeCircle prevents linking a tracker already assigned to another Person. A matching display name alone is never treated as proof of ownership.

HomeCircle Options shows whether the direct account is still waiting for trackers or how many trackers have appeared and are reporting. It checks for newly added Circle members again during normal operation, so you do not need to restart Home Assistant to discover them. If Life360 delays the member list, leave the account connected and reopen Options after a few minutes.

If the account has available trackers but none is explicitly selected in HomeCircle, an admin's card says to finish setup in Options. The prompt clears after a tracker from that account is chosen. It does not choose a member automatically because the account owner must confirm which tracker belongs to whom.

If Life360 rejects the saved sign-in, Home Assistant opens a reauthentication repair prompt. Enter a credential for the same Life360 account. HomeCircle compares the account identity saved by recent setups and rejects a different verified account. Older development setups without a saved identity ask you to confirm that the replacement belongs to the same account before keeping the household selections. For a persistent connection or discovery problem, use the [tracker provider issue workflow](TRACKER-PROVIDER-ISSUES.md) and HomeCircle's sanitized HA diagnostics. Do not share raw provider logs or location data.

To disconnect the direct account, open HomeCircle Options and turn off **Connect a Life360 account directly**. First replace any selected HomeCircle Life360 trackers with another source, and remove any exact HA Person links to those trackers. The setup flow prevents disconnecting while a selected member still uses or is linked to a HomeCircle-owned tracker.

If the password or token changes, open HomeCircle Options, select **Replace saved Life360 sign-in**, and enter the new credential for the same account. Saved member selections remain in place. For an older development setup without a saved account identity, HomeCircle compares the old and new sign-ins when the old one still works. If it cannot check the old sign-in, the form asks you to confirm they belong to the same account. To switch to a different Life360 account, remove this HomeCircle setup and create a new household so old tracker selections are not carried across.

This direct path uses Life360's undocumented API through the `life360` Python client. Sign-in, Circle discovery and polling may be rate limited or change without notice. Only the account owner should provide a credential; do not paste it into issues, screenshots or chat. HomeCircle does not set a Recorder exclusion: Home Assistant's Recorder settings determine whether the new tracker states and locations are retained. Review those settings before connecting. Direct connection passed live-account checks in a disposable Home Assistant setup; movement on the real server remains untested.

## 4. Choose the household

1. Under **Home Assistant People**, choose a Person for each member, including pets. Use **Create a new Home Assistant Person** if one is missing. A newly created Person remains in Home Assistant even if you later cancel HomeCircle setup.
2. Select **Primary family home** and any **Places shown while Away**. Create a missing zone here if needed.
3. On **Assign a tracker**, choose the device that belongs to that Home Assistant Person. HomeCircle links a newly chosen tracker to the Person when you save. A tracker already linked to another Person must be reassigned there first. Suggested trackers reflect Home Assistant's configured links, not measured reporting reliability; compare entity IDs when names repeat.
4. On **Choose trackers and places**, configure the selected tracker and any additional residences for that member.
5. Set **Member type** to `person` or `pet`. A pet also needs a Home Assistant Person record; HomeCircle does not infer pet status from its tracker.
6. For pets, set the location freshness thresholds on the next **Pet location timing** screen.
7. Enable **Set up battery and motion sensors** if you have supporting sensors. Enable **Set up location report times** if a selected source exposes a genuine report-time sensor. Those choices open separate screens.
8. Repeat for each member. The **Review and save household** screen lists the selected homes, roles, trackers, sensors, report times and pet timing. Choose **Back to last member** or **Edit a member** to correct a draft selection, then **Save household**. Closing the flow discards the draft.

## 5. Add optional battery and report-time sensors

These fields select existing HA entities. An attribute on a tracker is not itself a selectable sensor.

| HomeCircle field | Required meaning |
| --- | --- |
| Battery percentage sensor | Numeric battery percentage with `%` units |
| Charging binary sensor | On/off charging state for this member |
| Speed sensor | Numeric speed in m/s, km/h or mph |
| Driving binary sensor | Optional on/off driving evidence; overrides the selected GPS tracker's driving flag |
| Driving report timestamp sensor | Actual timestamp for the selected driving sensor; needs a driving binary sensor |

The **Status sensors** screen contains the five fields above. The separate **Location report time** screen visits each selected tracker and the person source; choose a genuine timestamp sensor for that source, or leave it empty. Older single-source mappings remain supported and are guided through the per-source screen when edited. See [per-source report times](PER-SOURCE-REPORTS.md) and [multiple-source checks](MULTI-SOURCE-VALIDATION.md).

Match each timestamp to the source named on its screen. A timestamp for a different source cannot establish the age of the active location.

On the card, **Tracker: name** or **HA Person: name** identifies the source currently supplying the map position. **Reported** uses a genuine location timestamp from that source. **HA state updated** only says when Home Assistant last changed the source entity; it does not prove when the device obtained its location. If no genuine timestamp exists, the card says **Location report time unknown**.

Beta 10 reads valid `battery_level`, `battery_charging` and GPS `last_seen` attributes from the selected tracker when explicit sensors are not configured. Beta 16 also reads a selected GPS tracker's boolean `driving` attribute when no driving sensor is configured, using its `last_seen` to decide whether the report is current. Explicit sensor mappings take priority. Other provider attributes may need a separately configured HA template sensor. Verify an attribute's meaning in that provider's documentation before building a helper; there is no universal Life360/pet attribute recipe. Preserve unavailable values rather than replacing them with zero or the current time. If no genuine report timestamp is available, leave it unmapped: **Location report time unknown** is the correct result. HA's `last_changed` and `last_updated` are not GPS fix times.

To add mappings later, open HomeCircle's Options, continue to that member, and enable the appropriate status-sensor or report-time switch. Clearing a field on its screen removes that mapping. Skipping the screen preserves existing mappings.

For one change, use **Person and tracker settings** to choose someone first, then select their details, battery and status sensors, or **Remove a tracker**. The removal picker shows only trackers attached to that selection. Removing a tracker from HomeCircle leaves its Home Assistant Person link in place; change that link separately in Settings → People if needed. **Add a tracker** asks for its Home Assistant Person first, with an option to create one; the next screen asks for the tracker and member type, followed by that member's settings. Older tracker-only members remain usable; select **Move a tracker-only member to a Person** to keep their role, homes, and sensors while linking their tracker. These actions do not send you through every existing member. Review the result before saving. On a member's screen, turn off **Show on map** to keep the member and their presence count while leaving them out of **Everyone** and its map fit. Selecting that member or a status category still shows their map position. An administrator can select the **cog** in the card header to open these same HomeCircle options over the dashboard. The cog is hidden in kiosk view; exit kiosk first.

## 6. Understand freshness

| Member | Location becomes stale after |
| --- | --- |
| Person | Five minutes |
| Pet at any assigned residence | 1440 minutes (24 hours), by default |
| Pet away | Five minutes, by default |

Pet thresholds accept 1–10080 minutes. They affect location freshness only. Driving retains its five-minute evidence rule. Ages display in minutes, hours or days; stale reports have an amber label and leading border. Unknown time remains unknown.

A longer threshold does not wake a tracker, produce a new GPS fix, or establish that a pet is safe. Freshness does not change Home/Away status or household counts.

## 7. Add and check the card

After saving the HomeCircle integration, open the new HomeCircle dashboard in the sidebar. If you already have a HomeCircle card, setup keeps that dashboard instead of creating another. Refresh the page once if the newly registered card does not appear. For a separate dashboard, select Edit dashboard → Add card → By card → HomeCircle, then select Done to leave edit mode.

OpenStreetMap street tiles are on by default. Tile requests send the viewed map area, your network address, and site origin to OpenStreetMap; member names and Home Assistant credentials are not sent. To avoid external tile requests, edit the card and choose **Private · no external tiles** under Map background. Existing cards explicitly set to Private stay private.

Check these results:

- Each member appears once with the expected status.
- Tap a member: the map focuses their usable position. A presence-only member can count without a marker.
- Tap Everyone: all usable positions return.
- Open a numbered overlapping group and select a member.
- Battery and report ages agree with the selected source entities. Unknown values are acceptable when evidence is absent.
- Refresh the browser and verify the card still loads. On a wall display, repeat the taps physically.

## Troubleshooting and later changes

- **No people in the selector:** use **Create a new Home Assistant Person**, then assign that member's tracker. This applies to pets too.
- **No pet tracker:** fix the separate provider integration; Member type does not create a tracker.
- **No map position:** check the active source for coordinates. Router presence alone may be locationless.
- **Sensor missing from picker:** check its entity domain and enabled state. Tracker attributes need separate sensors.
- **Stale report:** inspect the actual source report age. HomeCircle polls only built in provider connections that you enabled; it does not poll independently installed tracking integrations.
- **Missing-source repair notice:** allow sources to finish starting, then use Options to replace removed or renamed entities if necessary.
- **Card missing after install:** restart HA, refresh the browser, and confirm the integration completed setup. UI-only resource registration was tested with storage-mode dashboards; YAML-managed resources need separate handling.

HACS upgrades require a restart. To uninstall from a test instance, first remove the HomeCircle integration entry in Settings → Devices & services, then uninstall HomeCircle in HACS and restart HA. Removing the entry deletes its saved HomeCircle selections; reinstall requires setup again. Keep a Home Assistant backup before testing removal. Source integrations and their entities are managed separately. The normal removal/reinstall sequence passed in [beta 4 validation](BETA4-VALIDATION.md); other removal orders have not been accepted yet.

## Validation scope

See [beta 16 validation](BETA16-VALIDATION.md) for this release's tested scope. The physical DAKboard check passed on the exact beta 16 package before publication. Full real departure/return and unattended provider failure/recovery tests remain open before a stable release.
