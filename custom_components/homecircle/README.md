# HomeCircle integration

HomeCircle consumes Home Assistant people and device trackers for household presence and location. Beta 16 also offers an optional direct Life360 connection that creates ordinary Home Assistant device trackers. Existing trackers remain usable without a HomeCircle Life360 account. Neither path requires manual YAML.

Validated baseline: HA Core 2026.9.4 and Python 3.14.2+. Beta 16 is an experimental prerelease. Its separate production beta-test dashboard has been installed and checked; the existing V2 dashboard remains unchanged. HomeCircle does not create a separate location history store. Direct tracker states may be retained by Home Assistant Recorder according to the user's settings.

Build the frontend before starting HA. See [development](../../docs/DEVELOPMENT.md), [setup](../../docs/SETUP.md), and [direct Life360 candidate validation](../../docs/DIRECT-LIFE360-CANDIDATE-VALIDATION.md).
