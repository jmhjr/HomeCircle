# Beta 8 validation — 2026-10-02

Version `0.1.0-beta.8` adds HA and Life360 person and pet portraits to member cards and map markers. Initials remain when no image is available or loading fails. HomeCircle accepts HA-served images and two exact Life360 image hosts; the browser sends no HA page referrer with portrait requests. No family photos or real location values are included in the public package.

## Candidate checks

- 70 Home Assistant Python tests and 21 frontend tests passed. Ruff, Prettier, Git whitespace, and the public-file privacy guard passed.
- A deterministic 14-file `homecircle.zip` was built from the lockfile. Its files and archive SHA-256 match `inventory.json`; archive contents had no public-file privacy flags. ZIP SHA-256: `987c8469dee18a9bcca909f66a02e63790a3b26891f6a12dfa76892a81c9ab60`.
- Isolated Core install, upgrade, restart, entry removal, and post-removal restart passed with unrelated dashboard resources preserved.
- An isolated upgrade from the published beta 7 ZIP to the beta 8 candidate ZIP passed with the saved household retained through restart, then entry removal and post-removal restart passed.
- An independent read-only Claude Opus 5.5 review and follow-up check found no publication blocker. It verified the source-to-ZIP correspondence and version alignment. One nonblocking hardening item remains: the backend accepts dot segments in HA-local picture paths before its external-image path check; the card rejects those paths. No external host is added by that behavior.

## Remaining verification

- Confirm the published GitHub assets match the validated local ZIP and inventory byte for byte.
- Upgrade a disposable HACS installation and check real HA and Life360 image loading on the DAKboard. Local tests establish image selection and fallback logic, not delivery by the two external image hosts on that display.

This is an experimental prerelease. Stable-release readiness and broader tracking-source behavior remain governed by [current release readiness](CURRENT-RELEASE-READINESS.md).
