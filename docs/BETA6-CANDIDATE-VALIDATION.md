# Beta 6 candidate validation — 2026-09-27

This is a local candidate for a possible experimental `v0.1.0-beta.6` prerelease. The currently published release remains beta 5. No stable release or production migration is implied.

## Change

When a displayed location has no genuine report-time sensor, the card now shows the source state's HA update age with a separate label while continuing to say the location report time is unknown. A mapped report time, such as the Life360 test source's sensor, retains its existing Reported label and freshness behavior. HA `last_updated` is an observation of an entity state write, not proof of when a phone obtained a GPS fix.

The live [within-person iPhone/Life360 source-switch check](BETA5-REAL-SOURCE-VALIDATION.md) confirmed that location follows the selected real tracker. The iPhone source has no mapped report-time sensor and did not borrow Life360's time; Life360's displayed report time matched its own sensor. The original three-member disposable HA setup was restored.

## Candidate checks

- 61 Python tests and 16 frontend tests passed, including the distinct HA-observation fallback and explicit-report preference. Ruff and Prettier checks passed.
- Official Home Assistant Core 2026.9.4 hassfest found one integration and zero invalid integrations.
- A clean 14-file release ZIP was built. Its SHA-256 is `474bae1efbd2b720d4de7c87b78f84f964d000a6b8911366cb0b668ae01c27ab`. The isolated Core install, version-only upgrade rehearsal, restart, normal entry removal, and post-removal restart passed. The version-only rehearsal does not establish migration from the published beta 5 package.
- The public-file guard found no flagged patterns in 83 files. Manual review remains part of release preparation.
- The updated development card was temporarily served by the disposable real-source HA dashboard under a cache-busted preview URL. Real Chrome confirmed the iPhone test member showed HA state update age plus unknown location report time, while the Life360 test member retained its Reported age. The user confirmed both labels were readable on the physical DAKboard. The exact published beta 5 card bytes and resource URL were restored afterward.

This candidate has not yet been published through HACS. Production HA and V2 were unchanged. Background iPhone behavior away from the LAN, real departure/return transitions, unattended provider failover, sustained availability and the distinct physical additional-residence count/focus check remain open.
