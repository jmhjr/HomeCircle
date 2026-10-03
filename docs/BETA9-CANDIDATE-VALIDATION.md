# Beta 9 candidate validation — 2026-10-02

Version `0.1.0-beta.9` is an unpublished candidate. Single and grouped map markers have a pointed tip anchored at the tracked location, with each avatar above that point. The map reserves room above markers and beside zoom controls, including on narrow layouts. This changes the HomeCircle map card only; no tracking source, person selection, presence calculation, or existing V2 dashboard is changed.

## Checks completed

- The disposable real-source HA instance served the candidate card under a distinct cache-busted preview URL. Its three saved members, street tiles, grouped portrait pin, and single pet portrait pin rendered in the authenticated browser. The group opened individual choices; pet focus, Everyone reset, and zoom worked. The instance was restored to exact published beta 8 card bytes and resource URL after the check.
- The frontend's 22 tests passed, including assertions that single and grouped pin tips anchor at their map coordinates and that fit padding leaves positive room in narrow cards. The 70 HA Python tests passed.
- The deterministic 14-file candidate ZIP has SHA-256 `78fb4fda181710ec568593bb522cbce8976169c1edeeb402580d43b61ee4d5b5`. Every archive member matches its source file and inventory byte for byte. The isolated Core install, upgrade, restart, removal, and post-removal restart passed. The public-file guard found no flagged patterns in candidate source.
- A published beta 8 to candidate beta 9 isolated upgrade preserved the saved household through restart and passed removal.
- Claude Opus 5.5 reviewed the initial candidate read-only and found that fixed map padding could break `fitBounds` in a narrow card. The candidate now scales padding to map dimensions and waits for a nonzero map size before fitting. A second read-only Opus 5.5 review found no remaining blocker for narrow-card fitting. Its minor gaps concerned resize test coverage and behavior after later card resizing.

## Still needed before publication

- Inspect the pin layout on the physical portrait DAKboard after a published HACS upgrade.

The current published experimental prerelease remains [beta 8](https://github.com/jmhjr/HomeCircle/releases/tag/v0.1.0-beta.8). Production HomeCircle remains on beta 8 in its separate test dashboard.
