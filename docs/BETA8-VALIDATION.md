# Beta 8 validation — 2026-10-02

Version `0.1.0-beta.8` adds HA and Life360 person and pet portraits to member cards and map markers. Initials remain when no image is available or loading fails. HomeCircle accepts HA-served images and two exact Life360 image hosts; the browser sends no HA page referrer with portrait requests. No family photos or real location values are included in the public package.

## Candidate checks

- 70 Home Assistant Python tests and 21 frontend tests passed. Ruff, Prettier, Git whitespace, and the public-file privacy guard passed.
- A deterministic 14-file `homecircle.zip` was built from the lockfile. Its files and archive SHA-256 match `inventory.json`; archive contents had no public-file privacy flags. ZIP SHA-256: `987c8469dee18a9bcca909f66a02e63790a3b26891f6a12dfa76892a81c9ab60`.
- Isolated Core install, upgrade, restart, entry removal, and post-removal restart passed with unrelated dashboard resources preserved.
- An isolated upgrade from the published beta 7 ZIP to the beta 8 candidate ZIP passed with the saved household retained through restart, then entry removal and post-removal restart passed.
- An independent read-only Claude Opus 5.5 review and follow-up check found no publication blocker. It verified the source-to-ZIP correspondence and version alignment. One nonblocking hardening item remains: the backend accepts dot segments in HA-local picture paths before its external-image path check; the card rejects those paths. No external host is added by that behavior.

## Published assets

The [published prerelease](https://github.com/jmhjr/HomeCircle/releases/tag/v0.1.0-beta.8) is tagged at the reviewed beta 8 commit. Unauthenticated downloads of `homecircle.zip` and `inventory.json` matched the validated local files byte for byte. The published ZIP SHA-256 is `987c8469dee18a9bcca909f66a02e63790a3b26891f6a12dfa76892a81c9ab60`.

## Disposable HACS and touch display

- The real-source disposable HA installation upgraded from published beta 7 to published beta 8 through HACS and restarted. HACS and the integration both reported beta 8. All 14 installed package files matched the published inventory, and its three saved test members and street map loaded.
- In the authenticated browser, the Life360 member and pet had portraits in both cards and the map group; the iPhone member used initials. On the physical DAKboard, the user confirmed those portraits and fallback, then confirmed pet focus and Everyone reset still worked.

The separate production HomeCircle beta test remained on beta 7 during the disposable verification. Its HACS pre-release option was enabled, but HACS needed a repository information refresh before Home Assistant Settings listed beta 8 as an available update. It was then upgraded to beta 8 through HACS and restarted. An authenticated browser showed five saved members, four loaded portraits in member cards, one initials fallback for the iPhone member, Home 4, and Away 1. The user refreshed the production beta page on the physical DAKboard and confirmed that four photos appeared there too. The existing V2 dashboard was unchanged.

This is an experimental prerelease. Stable-release readiness and broader tracking-source behavior remain governed by [current release readiness](CURRENT-RELEASE-READINESS.md).
