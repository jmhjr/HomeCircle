# HomeCircle integration

HomeCircle consumes Home Assistant people and device trackers for household presence and location. Beta 11 also offers an optional direct Life360 connection that creates ordinary Home Assistant device trackers. Existing trackers remain usable without a HomeCircle Life360 account. Neither path requires manual YAML.

Development target: HA Core 2026.9.4 and Python 3.14.2+. Beta 11 is an experimental prerelease for test Home Assistant instances; it has not been installed on the live server. HomeCircle does not create a separate location history store. Direct tracker states may be retained by Home Assistant Recorder according to the user's settings.

Build the frontend before starting HA. See [development](../../docs/DEVELOPMENT.md), [setup](../../docs/SETUP.md), and [direct Life360 candidate validation](../../docs/DIRECT-LIFE360-CANDIDATE-VALIDATION.md).
