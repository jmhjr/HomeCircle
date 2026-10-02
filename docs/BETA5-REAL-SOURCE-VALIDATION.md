# Beta 5 real-source test validation — 2026-09-27

This check used the existing disposable, real-source Home Assistant Core 2026.9.4 instance. Production HA and the existing V2 dashboard were unchanged. The HomeCircle package and selected entry settings were backed up privately in ignored local work storage before the upgrade; no account credentials, entity IDs, coordinates or screenshots are included here.

## HACS upgrade

- Preflight showed HACS and the installed manifest on beta 4, three focusable test members, one Pet member, two displayed report timestamps and one owned beta 4 Lovelace resource.
- HACS downloaded the published beta 5 release. Every installed package file matched the release ZIP. After the test HA restarted, HACS reported beta 5 and the saved HomeCircle data and options were unchanged, including per-source report mappings and Pet settings.
- All three members remained focusable, including the Pet member; two report timestamps remained displayed. Exactly one owned resource used `?v=0.1.0-beta.5`, and the JavaScript served by HA matched the release ZIP byte for byte.

These checks confirm the current snapshot and saved mapping state. They do not simulate real departure/return, background updates away from the LAN, or within-person provider switching.

## Installed-card browser retry check

The beta 5 card bytes served by this HA instance were copied into a loopback-only browser harness and checked against the published ZIP. In real Chrome, a fictional rejected snapshot made one request; five ordinary HA `hass` updates made zero extra requests. The captured 15-second refresh callback made one retry, and a replacement connection recovered with a valid fictional snapshot. The harness contained no real household data. Its local server was stopped after the check.

## Physical display

The DAKboard HomeCircle Test button was previously configured for this disposable real-source page. After refreshing it, the user confirmed that beta 5 showed all three members and street tiles on the physical display. The user tapped the Pet member and Everyone, confirming that the map focused the member and returned to all three positions. This is physical touch acceptance for that flow. A later additional-residence count versus primary-house focus check passed with the local beta 6 card preview; see [candidate validation](BETA6-CANDIDATE-VALIDATION.md).

## Live Life360 away-state check

While a real Life360 member was away, the disposable HA instance showed the official Life360 tracker as `not_home` with coordinates and a recently updated state. A temporary HA person and fourth HomeCircle test member selected that tracker. HomeCircle's authenticated snapshot classified the member as Away, kept the member map-focusable, and used the selected tracker's coordinates. The other three test members stayed selected.

On the physical DAKboard, the user refreshed the HomeCircle Test page and confirmed four members with the temporary member marked Away. Tapping that member focused the map; Everyone returned to all four positions. The temporary person was then deleted and the exact original three-member HomeCircle options and snapshot were verified restored. Production HA was unchanged. No coordinates, tracker identifiers, or screenshots are published here.

This confirms a live Away snapshot and physical focus/reset behavior with a real Life360 source. It does not establish a departure transition, return transition, background iPhone update, or sustained provider availability.

## Within-person real-source switch

A temporary HA person in the disposable instance selected the existing iPhone and Life360 GPS trackers for the same individual. Both feeds had coordinates, and their current positions differed. The test selected the iPhone source, switched the HA person's associated tracker to Life360, then switched back to iPhone. Each phase used live provider state, not a substituted fictional tracker state.

HomeCircle's location matched the active tracker's coordinates in all three phases. The iPhone phase had no configured location-report sensor and its report time remained unknown. The Life360 phase used its own configured timestamp sensor; HomeCircle's reported time matched that sensor. Switching back restored the iPhone position and unknown report time, without borrowing Life360's timestamp. The original three-member HomeCircle options and snapshot were verified restored, and the temporary HA person was removed. This checks a controlled within-person source switch, not unattended provider failover or a physical-display source-switch interaction.

The iPhone `mobile_app` tracker exposed no location-report timestamp attribute or same-device timestamp sensor in this test instance. Its HA state update time is available, but that records when HA last updated the source state rather than proving when iOS obtained the GPS fix. Current iOS Companion App [location documentation](https://companion.home-assistant.io/docs/core/location/) describes event and background-triggered updates; this check does not establish a continuous real-time iPhone feed.
