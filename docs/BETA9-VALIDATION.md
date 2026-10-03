# Beta 9 validation — 2026-10-02

Version `0.1.0-beta.9` is a published experimental prerelease. Single and grouped map markers have a pointed tip anchored at the tracked location, with each avatar above that point. The map reserves room above markers and beside zoom controls, including on narrow layouts. This changes the HomeCircle map card only; no tracking source, person selection, presence calculation, or existing V2 dashboard is changed.

## Checks completed

- The disposable real-source HA instance served the candidate card under a distinct cache-busted preview URL. Its three saved members, street tiles, grouped portrait pin, and single pet portrait pin rendered in the authenticated browser. The group opened individual choices; pet focus, Everyone reset, and zoom worked. The instance was restored to exact published beta 8 card bytes and resource URL after the check.
- The frontend's 22 tests passed, including assertions that single and grouped pin tips anchor at their map coordinates and that fit padding leaves positive room in narrow cards. The 70 HA Python tests passed.
- The deterministic 14-file candidate ZIP has SHA-256 `78fb4fda181710ec568593bb522cbce8976169c1edeeb402580d43b61ee4d5b5`. Every archive member matches its source file and inventory byte for byte. The isolated Core install, upgrade, restart, removal, and post-removal restart passed. The public-file guard found no flagged patterns in candidate source.
- A published beta 8 to candidate beta 9 isolated upgrade preserved the saved household through restart and passed removal.
- Claude Opus 5.5 reviewed the initial candidate read-only and found that fixed map padding could break `fitBounds` in a narrow card. The candidate now scales padding to map dimensions and waits for a nonzero map size before fitting. A second read-only Opus 5.5 review found no remaining blocker for narrow-card fitting. Its minor gaps concerned resize test coverage and behavior after later card resizing.

## Published assets and HACS checks

- The [beta 9 prerelease](https://github.com/jmhjr/HomeCircle/releases/tag/v0.1.0-beta.9) is tagged at commit `8c1c0ee`. Unauthenticated downloads of `homecircle.zip` and `inventory.json` matched the validated local files byte for byte.
- The real-source disposable instance upgraded from beta 8 to beta 9 through HACS and restarted. All installed package files and the served card matched the published ZIP; HACS reported beta 9. The three saved members, selections, and owned dashboard resource ID survived. Its authenticated browser showed the group and single Ruby pins, grouped choices, Ruby focus, and Everyone reset.
- The separate HomeCircle beta installation on production HA upgraded through HACS and restarted. Its authenticated browser showed Jim, Emma, Nikki, Ella, and Ruby, with a family group pin and a separate Ella pin. Ruby focus and Everyone reset passed. The user refreshed the physical DAKboard and confirmed both pointed pins and both touch actions. The V2 dashboard was unchanged.

This prerelease does not establish stable-release readiness or behavior across all tracking sources and displays. The remaining gates are listed in [current release readiness](CURRENT-RELEASE-READINESS.md).
