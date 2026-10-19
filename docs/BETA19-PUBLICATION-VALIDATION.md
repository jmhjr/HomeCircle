# Beta 19 publication validation

Date: October 19, 2026. Published experimental prerelease; disposable HACS
upgrade acceptance is still pending.

## Published source and assets

[v0.1.0-beta.19](https://github.com/jmhjr/HomeCircle/releases/tag/v0.1.0-beta.19)
was published at 17:14:06 UTC as a GitHub prerelease, release ID `417544911`.
[PR #33](https://github.com/jmhjr/HomeCircle/pull/33) merged as
`45341808fc7fbfbefcfab9da44a2bea52049306c`; the release tag points to that same
commit. The release contains these exact tested assets:

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `homecircle.zip` | 575,816 | `5f20d536e1b5378bef7f0b972bbfbc7ced911063aea16a0a8f56d2ffa1210cd2` |
| `inventory.json` | 16,241 | `4592e16fd14eecbdaff7a689b4ae2bb262d925d2933c8188ec18974f5c118f54` |

Both assets were downloaded without authentication and matched the tested local
assets byte for byte. The ZIP contains 109 files. This verifies public asset
availability and integrity; it does not substitute for installing through HACS.

Safe receipts: `github-release.json`, `github-public-download.json` and
`github-merge.json` in the ignored release-validation directory.

## Actual HA acceptance already completed

The actual HA OS Raspberry Pi already runs HomeCircle `0.1.0-beta.19`, and all
109 installed files match the canonical published ZIP. Native Apple sign-in,
trusted-device recovery, explicit selection of two AirTags, decoded report
delivery and passwordless reuse after restart passed before publication.
The pre-password progress fix also passed on the real HA interface. Account,
machine, grant, selected-key and registry preservation checks passed without
duplicate trackers. No further production restart is required for publication.

The canonical ZIP differs from the original live-acceptance archive only by
extra empty EOF lines removed from two runtime files; Python ASTs including line
attributes are identical. The published
[beta 19 validation](https://github.com/jmhjr/HomeCircle/blob/45341808fc7fbfbefcfab9da44a2bea52049306c/docs/BETA19-VALIDATION.md)
and its technical packaging record preserve those separate proof scopes.

The accepted reports had existing source timestamps. New physical movement,
current-position freshness, delivery latency and recorder-history continuity
were not established by these checks. These are disclosed experimental-beta
limitations, not claims derived from a successful poll or report count.

## Disposable HACS upgrade pending

An actual disposable HACS `v0.1.0-beta.18` → `v0.1.0-beta.19` upgrade has not yet
completed. It is waiting for fresh HACS device OAuth authorization. No HACS
installation, upgrade or post-upgrade restart success is inferred from the
verified GitHub downloads or the already accepted production installation.

After authorization, record HACS's selected version, package download, restart,
loaded integration/card versions, preservation of the disposable instance's
saved configuration, and comparison of installed files with the published
inventory. Add that proof here once it exists.
