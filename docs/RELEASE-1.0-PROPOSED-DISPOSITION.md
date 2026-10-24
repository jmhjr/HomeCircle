# HomeCircle 1.0 release decision

Status: maintainer approved; normal merge, stable publication and public-asset verification completed.

## Explicit final approval

On October 24, 2026 UTC (October 23 in America/Chicago), the maintainer replied
“Do it” to the final approval question to publish 1.0 with both optional,
unofficial providers and the documented limits. This records approval of prepared
source `89e25a406d893f99e9f6a173b149e3e7aaca4483` and the exact ZIP and inventory
below. The reviewed proposal is retained as the approved inclusion, support and
residual-uncertainty disposition. Approval does not establish provider permission
or legal clearance. At that approval checkpoint, merge, tag and publication had
not yet been executed; their subsequent result is recorded below.

## Verified publication

The [publication record](RELEASE-1.0-PUBLICATION.json) verifies stable release
`v1.0.0` (release ID `422522039`), published at `2026-10-24T04:48:06Z` from normal
merge `6984be7c6148c934e7f51e09e27db5b078fc022c`. The release is latest, not a
draft or prerelease. Both anonymously downloaded public assets match the exact
approved ZIP and inventory hashes below. The merged tree matches the approved
source. Prior releases and the original stable tag/source/artifact records remain
unchanged; this publication closure is a documentation-only follow-up.

## Exact package

Version: `1.0.0`. The integration ZIP contains 112 files.

- ZIP SHA-256: `a21aa690ed45aaa1e293fe33c6c9780f6a95ba6e7faa868e49856d4cd7fce932`.
- Inventory SHA-256: `fb5098b327e656a44156b0634e9521c46ed68cd46dd883a2d86590b89a44808f`.

Only the manifest version, frontend resource version and compiled card version differ from the qualified RC2 package. The other 109 packaged files match RC2 exactly. All notices and provider implementations are unchanged. The [preparation record](RELEASE-1.0-STABLE-PREPARATION.json) retains the checks and evidence boundaries.

## Approved distribution and support scope

Ship source-only HACS delivery with the existing notices and public OSS grants. Include standard Home Assistant People and trackers plus optional, unofficial Apple Find My and Life360 connections. No Apple payload, dependency wheel, native library or account identity is bundled. Keep the unused Mac utility and CLI excluded.

Support HAOS on Intel/AMD (amd64) and ARM64, minimum Core 2026.9.4 and current qualification target 2026.10.2. Home Assistant Container remains experimental. Retain administrator Pause/Resume, stop-on-denial behavior and the existing recovery safeguards.

The maintainer accepted the residual uncertainties recorded in the [no-contact decision](RELEASE-1.0-NO-OUTREACH-DECISION.md) for this exact source-only scope: Unicorn's binding/combined-work obligations, the exact Apple installer agreement and extraction/emulated use, and Apple/Life360 service authorization. Those uncertainties remain. The existing source grants, notices, separate dependency downloads and user consent do not establish provider permission or legal clearance. This disposition requires no outreach and asserts no new permission.

Retain the accepted limited Claude AI review and its missing independent producer-format vectors. The owner phone display check passed; source report age remains distinct from a Home Assistant update. New Find My position, natural long-term renewal and actual-photo persistence are unclaimed by this final round. Renewal may require a guided manual reconnect; uninterrupted sessions and fresh GPS reports are not promised. Older reports remain visibly marked, and the product provides no emergency guarantee.

## Actions authorized by final approval

The maintainer authorized the above inclusion and support disposition, merging the reviewed release pull request through the normal repository checks, and publishing tag `v1.0.0` with the exact ZIP and inventory above as the stable GitHub/HACS release. Normal merge, publication and anonymous public-byte verification are complete in the [publication record](RELEASE-1.0-PUBLICATION.json). Prior platform, HACS and runtime evidence retains its original scope; no new native run, HACS installation or platform result is created by approval or publication.

An everyday Home Assistant upgrade is a separate deployment decision and is not authorized here. The test instance remains on RC2 after publication; these unperformed deployments are separate from the completed first-release gates. No additional provider tests, recovery actions or outreach are authorized by this release decision.
