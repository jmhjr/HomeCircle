# Independent fixed-candidate full package review: corrective consumer R2

The frozen R1 consumer refused the completed native run because it incorrectly
required a redundant `source_files` field in privacy receipts. The producer had
always emitted `files_checked` instead. R1 code, its before-evidence protocol and
its refusal remain unchanged. This R2 revision is an explicit correction made
after artifact examination; it is not represented as a before-evidence freeze.
Only `privacy_expected` changes, matching the literal pre-frozen emitter shape.
The 381 checked files, zero flags and all source/checker hashes remain mandatory.
An independent AST-only producer-schema contract checks the shape without
importing the producer. Top-level and embedded privacy reject any added field,
changed count, changed source/checker hash or failure flag.

This standard-library consumer verifies a new native full package run for canonical
source `3c33160c67e53956ab52298ffc10ccc9992132f0`. Its exact 381-file source catalog
was generated directly from Git objects without using working-tree bytes.

The immutable input remains `f181e6300f15d8977817a552db90d35caf0edc869067ebeea815c7be1df0248e`
with inventory `8ea456beb9b2eaaf4ba50639532b8dafabe0e02d1e13a77a59525f1c249c7447`.
Its 113 uncompressed members bind to 111 literal canonical source members and two
unchanged generated frontend assets. The level-6 input archive is not replaced.
The canonical level-9 build has separate digest
`acfcda419a817032c38a463505f686b0f6ab49e69a8f1603d9b2ff43f24e442b` and must have the
same payload and reproducible archive bytes. Both identities remain explicit.

The source/test tree intentionally retains only the integration's canonical
`README.md` in addition to the 113 package members. Its exact Git fingerprint is
required before/after testing. No other extra runtime file is allowed. The
candidate ZIP itself contains exactly 113 members; this source-only exception
does not add a file to the candidate artifact.

Acceptance requires exactly six success receipts, 1732 backend passes, zero
failures or duplicate cases, one exact pre-existing optional Apple DMG fixture
skip, all 54 required functions including real HA setup, 14 cause-verified old
vault failures, 122 frontend passes, reproducible frontend/notice bytes, source
privacy over all 381 files with zero flags, and verified offline execution and
owned-container cleanup. The entire six-receipt nested schema is strict.

The native runtime is pinned Core 2026.10.2, Python 3.14.6, AMD64 image 45f009d6,
and pytest-homeassistant-custom-component 0.13.373. The consumer independently
checks the 24-name dependency closure against the exact public Core constraints,
all direct integration pins and the allowed protobuf range. It requires the same
component/auth graph and declared versions already verified in the prior accepted
current-Core setup receipt. The constraints source is the official
[Core 2026.10.2 file](https://raw.githubusercontent.com/home-assistant/core/2026.10.2/homeassistant/package_constraints.txt);
its SHA256 must equal the native image's pinned 7baa9a8f digest.

Two independently verified GitHub artifact metadata records are required. One
binds `fixed-package-validation-receipts`; the other binds
`unreleased-fixed-candidate`. They must identify the same exact successful run,
QA head, event and attempt, but different artifact IDs. The second artifact must
contain only the original f181 ZIP and 8ea inventory. A substituted acfc archive
is refused even if its artifact metadata digest is updated consistently.

QA head `69be6211e24609fc3f020dd8407acb25b99c175a`, run `39865496620`, attempt 1 and
event `push` were frozen in R1 before artifact examination. R2 retains those exact
anchors; different native anchors are refused. The 20 contract tests use fictional records and
the public preparation bytes; they are not native acceptance evidence.

```sh
python3 -B -m unittest test_independent_package -v
python3 -B independent_package.py \
  --fixture-dir ../harness --workflow ../workflow-r1.yml \
  --artifact-zip RESULTS/artifact.zip --metadata RESULTS/ROOT-METADATA.json \
  --candidate-artifact-zip RESULTS/candidate-artifact.zip \
  --candidate-metadata RESULTS/ROOT-CANDIDATE-METADATA.json \
  --output FRESH-INDEPENDENT-REVIEW.json
```

This review imports no fixture, Home Assistant, provider or native SDK modules.
It does not independently qualify an ordinary restore, an upgrade, provider
authentication, HACS delivery or a stable release. Those results remain separate.
