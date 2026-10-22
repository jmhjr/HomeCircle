# Retained recovery-guard and ordinary-restore evidence

This directory retains public synthetic evidence for ordinary native HAOS
partial-restore run [39721983991](https://github.com/jmhjr/HomeCircle/actions/runs/39721983991)
and backend/package run [39715519894](https://github.com/jmhjr/HomeCircle/actions/runs/39715519894).
The ordinary artifact remains available here after Actions artifact expiration.
Follow [REPLAY.md](REPLAY.md) with the exact frozen QA fixture and workflow.

The unchanged 113-member product ZIP has SHA256
`98a754ff2025761c2eb63d6422c9b17b76e2bdef2965c96fe353ab6c2c21fb20`.
Runtime source is `012a7e88d13970b2683b27d0824dac246c858179`; backend source
`57b0aaa5c2c4b1a022e547347640173412e840f5` changes only test isolation.
Backend receipts and the independent source/package audit are under `backend/`.
The causal guard replay uses only synthetic local counters and no provider calls.

The collector's finite negative examples are fabricated. Its source inventory
contains public repository paths and hashes, not household entity identifiers.
The retained ZIP contains only the five fixed public JSON receipts verified by
the independent consumer. No HA backup, vault, key, database or raw trace is kept.

Acceptance is an ordinary unmodified-product synthetic same-host partial restore,
with external transport interception and normal managed requirements. It includes
automatic recovery blocking after cache-witness loss and across restart. It does
not qualify real provider authentication/renewal, Person/activity-history recovery,
full-system/encrypted/cloud restores, a snapshot restoring both guard files,
HACS delivery or a stable release. Earlier failed trials retain their outcomes
in the release documentation and their original QA commits.
