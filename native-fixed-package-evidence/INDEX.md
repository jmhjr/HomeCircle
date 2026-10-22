# Fixed-candidate full native package evidence

[Native run 39865496620](https://github.com/jmhjr/HomeCircle/actions/runs/39865496620)
passed on current Core 2026.10.2 / Python 3.14.6 / native Linux amd64.
Canonical source is 3c33160c67e53956ab52298ffc10ccc9992132f0; QA run head is
69be6211e24609fc3f020dd8407acb25b99c175a, push event, attempt 1.

All 1,732 backend tests, all 54 required regression functions and 122 frontend
tests passed. Zero tests failed. Exactly one pre-existing optional test was
skipped: tests.test_findmy_runtime_bootstrap::test_retained_public_apple_dmg_fixed_ranges
(the optional retained public installer fixture is absent). All 381 canonical
source files were byte-verified and privacy-checked with zero flags. The 42 host
contracts, 20 corrected consumer controls and 14 causal old-vault negative cases
are distinct checks, not additional native backend case counts.

The exact original tested/exported candidate ZIP is
f181e6300f15d8977817a552db90d35caf0edc869067ebeea815c7be1df0248e
with inventory 8ea456beb9b2eaaf4ba50639532b8dafabe0e02d1e13a77a59525f1c249c7447.
The unchanged canonical builder's compression-level-9 archive
acfcda419a817032c38a463505f686b0f6ab49e69a8f1603d9b2ff43f24e442b has the same
113 member bytes but a different archive identity. It was reported separately;
the level-6 input candidate was not replaced. The source/test tree retained the
single exact Git-bound nonruntime README outside the 113 candidate members.

- [INDEPENDENT-REVIEW.json](INDEPENDENT-REVIEW.json) is the byte-identical root/peer accepted R2 result.
- [PEER-AUDIT.json](PEER-AUDIT.json) records independent source, runtime receipt, dependency and cleanup findings.
- [PROTOCOL-FREEZE.json](PROTOCOL-FREEZE.json) and [INPUTS.json](INPUTS.json) bind the R2 consumer and all 14 previously frozen native harness/workflow inputs.
- [artifact.zip](artifact.zip) contains the six narrow public JSON receipts. GitHub artifact 12463951940 digest: ab2a5e8089c1036b4ce26b7a8dfd3569ed2f7183acc4489a5e23caeea52746ea.
- [candidate-artifact.zip](candidate-artifact.zip) contains only the original candidate ZIP and inventory. GitHub artifact 12464092121 digest: bd97e246e345df5174277245b90cb75574954207193a3a3dc6707dc5cd047714.
- The two ROOT metadata files were obtained separately from the artifact contents and bind those verified digests to the same completed successful run.
- [SCHEMA-AMENDMENT.json](SCHEMA-AMENDMENT.json) records the narrow consumer correction after artifact examination.
- [REFUSED-CONSUMER-R1.zip](REFUSED-CONSUMER-R1.zip) preserves the before-artifact R1 consumer/protocol and both original privacy_receipt_refused outputs without changes.
- [PACKAGING-IDENTITY-REVIEW.json](PACKAGING-IDENTITY-REVIEW.json) preserves the independent same-payload compression distinction.
- [REPLAY.md](REPLAY.md) gives the portable standard-library evidence replay.

The unchanged native producer emitted files_checked:381 without a redundant
source_files field in privacy receipts. R1 mistakenly required both fields.
R2 changed only privacy_expected to match the pre-frozen emitter, retaining all
count/hash/zero-flag gates and adding an AST-based producer-schema regression.
This was an explicit post-artifact consumer amendment. No product, harness,
workflow, native artifact or native run was changed or repeated.

This evidence qualifies only the current-Core full container/package/backend/
frontend suite for the unreleased same-version 0.1.0-beta.20 fixed candidate.
It adds no HAOS lifecycle, ordinary restore, upgrade, HACS delivery, live provider
authentication/renewal, field, cloud/full-system restore, final RC or stable
release acceptance. Prior minimum-Core full-package evidence remains tied to
old012a/98a. Other release-plan gates keep their separate dispositions.
The owned native container/private workspace were removed; the working owner
test instance was not used or changed.
