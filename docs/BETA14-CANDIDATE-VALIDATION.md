# Beta 14 candidate validation — 2026-10-04

Production beta 13 displayed `Tracker: Ruby` because the selected tracker has the Home Assistant friendly name `Ruby`. Home Assistant's device page identifies that tracker as belonging to the Life360 Pet GPS integration. No HomeCircle member or tracker selection was changed during this check.

Beta 14 reads the selected source entity's Home Assistant registry platform and adds its integration name when the tracker name alone does not supply it. For the observed source, the expected label is `Tracker: Ruby · Life360 Pet GPS`. Unknown or unregistered trackers retain their existing `Tracker: <name>` label. The source remains the entity selected by HomeCircle's location logic; the label does not infer an association from a person's or pet's name.

Candidate checks: 151 Python tests and 28 frontend tests passed. Ruff and Prettier checks passed. The public-file guard found no flagged patterns. The deterministic 21-file release ZIP has SHA-256 `8612ad5e39c48671cd3c80c9c3b7205e82dd45922bd486b5dae83d5aa21c1340`. A disposable Home Assistant package lifecycle passed create, upgrade, restart, removal, and post-removal resource checks. Production installation and physical DAKboard acceptance have not yet been performed for beta 14.
