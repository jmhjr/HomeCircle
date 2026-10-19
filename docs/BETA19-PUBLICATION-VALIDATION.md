# Beta 19 publication validation

Date: October 19, 2026. Published experimental prerelease; actual disposable
HACS beta 18 → beta 19 upgrade acceptance passed.

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

## Actual disposable HACS upgrade passed

A fresh disposable HA instance completed official HACS device OAuth with the
owner's approval. No production configuration or credentials were copied.
The instance used two fictional household members and configured no native
Apple accounts, so this checks HACS distribution and upgrade preservation
separately from the real-account acceptance above.

The baseline independently confirmed both HACS's installed
`v0.1.0-beta.18` and HA's loaded `0.1.0-beta.18` manifest, matching beta 18
served card bytes, the two fictional members and an unrelated frontend resource.
The actual upgrade then passed:

- HACS downloaded and recorded `v0.1.0-beta.19`.
- All 109 installed files matched the canonical published ZIP exactly, with
  SHA-256 `5f20d536e1b5378bef7f0b972bbfbc7ced911063aea16a0a8f56d2ffa1210cd2`.
- A real restart launched a new Core worker; an independent check confirmed
  HA loaded the `0.1.0-beta.19` manifest.
- Saved entry data and options, plus household counts, member identities,
  presence and focusability, remained unchanged.
- The owned card URL contained the beta 19 version and expected asset digest;
  HTTP-served card bytes matched the release. The unrelated resource survived.

Safe aggregate evidence is retained as `hacs-acceptance.json` in the ignored
release-validation directory. The HACS test made no production HA changes or
restarts. Cleanup also passed independently: the temporary configuration and
local authentication/device-flow files were removed, and the loopback server
stopped. Cleanup read or modified no production files; its safe receipt is
`hacs-cleanup.json`.
