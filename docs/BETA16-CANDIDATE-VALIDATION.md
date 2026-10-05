# Beta 16 candidate validation

Validated 2026-10-04. This is a staged beta candidate, not a published HACS release or a stable-release approval.

Beta 16 keeps the map visible while the member list scrolls outside kiosk mode. Members hidden from Everyone can still be shown by selecting their card or a status category. The setup review and guide now explain that distinction.

## Checks completed

- 29 frontend tests and 157 Home Assistant tests passed. Ruff, Prettier, the public-file guard, and the release build passed.
- A browser preview with 16 fictional members confirmed independent member-list scrolling in standard and full-screen layouts.
- A disposable Home Assistant instance loaded beta 16. Hiding a fictional member reduced Everyone to one map position; selecting the member showed one position, and selecting Away showed both. The setting survived a dashboard reload.
- Independent Claude review found a short-screen layout risk and two outdated descriptions. The fixes were re-reviewed with no blocking findings. A 640-by-480 browser check measured a visible map and a 180-pixel scrollable member list; a narrow 320-pixel check also kept both reachable.
- The rebuilt candidate was staged on the separate production HomeCircle beta-test installation with the prior beta 15 directory backed up. After a Home Assistant restart, the browser showed the Beta 16 title, saved members, a visible map, and working member and Everyone controls. The existing V2 dashboard was not changed.
- The overlap correction was rebuilt and installed. After the final Home Assistant restart and a fresh page load, all six member rows kept their content height with no overlap; the member list measured 333 pixels high with 722 pixels of scrollable content, and the map remained 220 pixels high. Selecting a member showed one map position and Everyone restored five.

The live browser check exposed compressed member grid rows that let card details overlap. The grid now keeps each row at its content height while the member list scrolls. A content hash in the owned Lovelace resource URL makes displays fetch the corrected bundle even though the beta version number has not changed; its file read runs outside Home Assistant's event loop. Claude reviewed the correction and found the blocking-call risk, which was fixed before the final build. The full Home Assistant test suite, 29 frontend tests, Ruff, Prettier, and the public-file guard passed after that fix.

The final package contains 21 files and has SHA-256 `ec63aa699160b0e844ef4f717c2520ff259eb2b3f502c0cd3f2f4b8ba5c493fa`.

## Physical display acceptance

The user refreshed the physical DAKboard and confirmed that member cards and their data no longer overlap. The member list scrolled while the map stayed visible, and selecting one member then Everyone worked. The beta 16 GitHub/HACS prerelease was still unpublished at this checkpoint.
