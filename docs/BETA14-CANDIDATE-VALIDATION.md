# Beta 14 release validation — 2026-10-04

Production beta 13 displayed `Tracker: Ruby` because the selected tracker has the Home Assistant friendly name `Ruby`. Home Assistant's device page identifies that tracker as belonging to the Life360 Pet GPS integration. No HomeCircle member or tracker selection was changed during this check.

Beta 14 reads the selected source entity's Home Assistant registry platform and adds its integration name when the tracker name alone does not supply it. For the observed source, the expected label is `Tracker: Ruby · Life360 Pet GPS`. Unknown or unregistered trackers retain their existing `Tracker: <name>` label. The source remains the entity selected by HomeCircle's location logic; the label does not infer an association from a person's or pet's name.

Candidate checks: 151 Python tests and 28 frontend tests passed. Ruff and Prettier checks passed. The public-file guard found no flagged patterns. The deterministic 21-file release ZIP has SHA-256 `8612ad5e39c48671cd3c80c9c3b7205e82dd45922bd486b5dae83d5aa21c1340`. A disposable Home Assistant package lifecycle passed create, upgrade, restart, removal, and post-removal resource checks.

PR #4 merged at `0307f5e`. The [beta 14 prerelease](https://github.com/jmhjr/HomeCircle/releases/tag/v0.1.0-beta.14) targets that merge. Publicly downloaded ZIP and inventory matched the reviewed local assets byte for byte. Production HACS downloaded beta 14, and a full Home Assistant restart loaded integration version `0.1.0-beta.14`. The existing separate beta dashboard retained six members and five map positions. Once source integrations reconnected, Ruby's live card showed `Tracker: Ruby · Life360 Pet GPS`, battery 11%, and its location report age; the other member source labels and report details remained visible. No household or tracker settings were changed. The earlier production backup remains available. The frozen V2 dashboard was not modified.

Physical DAKboard acceptance for beta 14 remains open. A browser check does not establish touch behavior on the physical display.
