# HomeCircle integration

HomeCircle consumes Home Assistant people and device trackers for household presence and location. HomeCircle also offers an optional direct Life360 connection that creates ordinary Home Assistant device trackers. Existing trackers remain usable without a HomeCircle Life360 account. Neither path requires manual YAML.

Validated baseline: HA Core 2026.9.4 and Python 3.14.2+. Beta 18 is an experimental prerelease. See its validation record for candidate checks and remaining acceptance gates. HomeCircle does not create a separate precise-location history store. Optional city lookup has a bounded local street/city cache and requires coordinate-sharing consent. Tracker photos use native HA image storage. Direct tracker states may be retained by Home Assistant Recorder according to the user's settings.

Build the frontend before starting HA. See [development](../../docs/DEVELOPMENT.md), [setup](../../docs/SETUP.md), and [direct Life360 candidate validation](../../docs/DIRECT-LIFE360-CANDIDATE-VALIDATION.md).
