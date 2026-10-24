# Proposed HomeCircle 1.0 release decision

Status: prepared for maintainer review; approval and stable publication are pending.

## Exact package

Version: `1.0.0`. The integration ZIP contains 112 files.

- ZIP SHA-256: `a21aa690ed45aaa1e293fe33c6c9780f6a95ba6e7faa868e49856d4cd7fce932`.
- Inventory SHA-256: `fb5098b327e656a44156b0634e9521c46ed68cd46dd883a2d86590b89a44808f`.

Only the manifest version, frontend resource version and compiled card version differ from the qualified RC2 package. The other 109 packaged files match RC2 exactly. All notices and provider implementations are unchanged. The [preparation record](RELEASE-1.0-STABLE-PREPARATION.json) retains the checks and evidence boundaries.

## Proposed distribution and support scope

Ship source-only HACS delivery with the existing notices and public OSS grants. Include standard Home Assistant People and trackers plus optional, unofficial Apple Find My and Life360 connections. No Apple payload, dependency wheel, native library or account identity is bundled. Keep the unused Mac utility and CLI excluded.

Support HAOS on Intel/AMD (amd64) and ARM64, minimum Core 2026.9.4 and current qualification target 2026.10.2. Home Assistant Container remains experimental. Retain administrator Pause/Resume, stop-on-denial behavior and the existing recovery safeguards.

Accept the residual uncertainties recorded in the [no-contact decision](RELEASE-1.0-NO-OUTREACH-DECISION.md) for this exact source-only scope: Unicorn's binding/combined-work obligations, the exact Apple installer agreement and extraction/emulated use, and Apple/Life360 service authorization. The existing source grants, notices, separate dependency downloads and user consent do not establish provider permission or legal clearance. This proposal requires no outreach and asserts no new permission.

Retain the accepted limited Claude AI review and its missing independent producer-format vectors. The owner phone display check passed; source report age remains distinct from a Home Assistant update. New Find My position, natural long-term renewal and actual-photo persistence are unclaimed by this final round. Renewal may require a guided manual reconnect; uninterrupted sessions and fresh GPS reports are not promised. Older reports remain visibly marked, and the product provides no emergency guarantee.

## Actions covered by final approval

Approve the above inclusion and support disposition, merge the reviewed release pull request through the normal repository checks, and publish tag `v1.0.0` with the exact ZIP and inventory above as the stable GitHub/HACS release. Verify the public asset bytes after publication and retain the original scope of prior platform, HACS and runtime evidence.

An everyday Home Assistant upgrade is a separate deployment decision. The test instance remains on RC2 during this review.
