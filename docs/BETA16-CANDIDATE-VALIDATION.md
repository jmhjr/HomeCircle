# Beta 16 candidate validation

Validated 2026-10-04. This is a staged beta candidate, not a published HACS release or a stable-release approval.

Beta 16 keeps the map visible while the member list scrolls outside kiosk mode. Members hidden from Everyone can still be shown by selecting their card or a status category. The setup review and guide now explain that distinction.

## Checks completed

- 29 frontend tests and 157 Home Assistant tests passed. Ruff, Prettier, the public-file guard, and the release build passed.
- A browser preview with 16 fictional members confirmed independent member-list scrolling in standard and full-screen layouts.
- A disposable Home Assistant instance loaded beta 16. Hiding a fictional member reduced Everyone to one map position; selecting the member showed one position, and selecting Away showed both. The setting survived a dashboard reload.
- Independent Claude review found a short-screen layout risk and two outdated descriptions. The fixes were re-reviewed with no blocking findings. A 640-by-480 browser check measured a visible map and a 180-pixel scrollable member list; a narrow 320-pixel check also kept both reachable.
- The rebuilt candidate was staged on the separate production HomeCircle beta-test installation with the prior beta 15 directory backed up. After a Home Assistant restart, the browser showed the Beta 16 title, saved members, a visible map, and working member and Everyone controls. The existing V2 dashboard was not changed.

The rebuilt package contains 21 files and has SHA-256 `b10e9d686655fe0803d9c642168889374dd5129565692181ffb10389f63f2f9c`.

## Still required

The physical DAKboard must be refreshed and checked for non-kiosk scrolling with the map visible, member focus, Everyone reset, and kiosk behavior. Publication remains pending that user-operated display check.
