# HomeCircle Reference Implementation v1

Frozen from available local artifacts on 2026-09-27. This is a behavior baseline, not a claim that a fresh live-production export was captured.

## Evidence sets

1. Production-era V2: preserved September V2 dashboard YAML/JSON, residence classifier, zone definitions, map/label modules, and Google migration files. The migration record describes the Google main view and preserved Mapy rollback view. The local final Google YAML is retained privately as the best available migration-era artifact, not verified against today's live configuration.
2. Later extracted Family Map Card: source, tests, setup files, examples, build metadata, license/notices and handoff documents. The latest handoff records beta 19 verified in a separate test clone, with production unchanged and physical tablet acceptance still separate. Some README installation/version text is older; the inventory distinguishes source behavior from prior validation claims.
3. Separate Life360 Family integration source/tests: retained privately as source-provider context, not imported into HomeCircle. Its direct people/pet APIs and authentication are deliberately excluded from the product architecture.

The live configuration mount was unavailable during bootstrap. No live dashboard export, new physical-device test or current screenshot was captured. The snapshot is not a complete HA backup and is not a one-step restore package.

## Storage

Raw files and absolute provenance paths are in a restricted sibling task work directory, outside this repository. The private manifest lists original path, relative snapshot path, byte count and SHA-256. Copies are byte-for-byte verified and original hashes are checked again after bootstrap. Do not publish that manifest or the raw snapshot.

`current-v2.example.yaml` below is a manually authored generic layout reference, not an executable copy of production YAML. It contains no keys, household coordinates, addresses, real entity IDs or photographs. Use the feature inventory plus private snapshot for parity work; do not mistake the example for the original.

## Preservation rule

Never edit the frozen snapshot to develop HomeCircle. Work in the new backend/frontend directories, compare behavior against the reference, and update inventory status when a feature is accepted. Keep the production V2 and existing clone deployments unchanged until a separately selected rollout.
