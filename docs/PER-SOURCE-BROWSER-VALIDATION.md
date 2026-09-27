# Per-source setup browser walkthrough

Checked the `0.1.0-beta.4.dev1` development package in a new temporary Home Assistant Core instance on loopback. The instance contained fictional Person/tracker entities and template timestamp sensors. It reused only the existing disposable test login; no real household or provider data was copied.

Through the actual HA browser UI:

1. Added HomeCircle and selected an example person and phone tracker.
2. Opened Options and enabled **Configure report times for each source**.
3. Saw a separate screen for the person source, left its timestamp empty, and advanced to the phone source.
4. Selected the fictional phone report sensor and saved the household. HA displayed **Options successfully saved**.
5. Reopened Options, added a second tracker, and revisited the per-source screens. The phone sensor was still selected. The newly added router source had its own empty timestamp field.
6. Saved again. The actual stored options contained both selected trackers, a mapping from the phone tracker to its report sensor, and no router mapping.
7. Closed the test browser tab and stopped the temporary HA instance; its configuration directory was removed.

This validates browser rendering, navigation, selection, saving and reopening. The second selected source was router presence without a GPS timestamp, so this walkthrough does not simulate a second live GPS report. The separate clean Core source-switching validation covers two GPS report sensors and source-specific freshness. Physical DAKboard checks for this preview and a published HACS upgrade remain pending. Production and the working real-source beta 3 instance were unchanged.
