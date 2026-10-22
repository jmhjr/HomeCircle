# Exact fixed candidate full native package validation

Canonical source `3c33160c67e53956ab52298ffc10ccc9992132f0` and the original fixed candidate package `f181e6300f15d8977817a552db90d35caf0edc869067ebeea815c7be1df0248e`
are qualified by [native run 39865496620](https://github.com/jmhjr/HomeCircle/actions/runs/39865496620)
for the scoped current-Core container/package suite described here. This is an
unreleased same-version `0.1.0-beta.20` candidate; no product change was made in
this validation milestone.

## Evidence and observed result

- QA head `69be6211e24609fc3f020dd8407acb25b99c175a`; event `push`, attempt 1; workflow `.github/workflows/native-fixed-package.yml` with SHA-256
  `bf076fd90a4690b7c571ff6c102aa61af45bb660685047c3eac65fc01e0fa6f0`. All 14 pinned inputs were checked before harness imports.
- The native workflow passed all 42 standalone harness contracts. The separate
  corrected frozen evidence consumer passed 20 finite positive/adversarial contracts.
- All 1,732 backend cases passed, all 54 required regression functions passed,
  and no backend case failed. Exactly one optional retained-public-installer
  case was skipped: `tests.test_findmy_runtime_bootstrap::test_retained_public_apple_dmg_fixed_ranges`. The installer fixture was absent; this result does
  not replace independent real-format or live recovery assurance.
- All 122 frontend TAP cases passed without failures/skips. Two frontend builds
  matched each other, the candidate's exact generated assets and the Leaflet
  notice. All 381 canonical public Git files were byte-verified and passed the
  privacy checker with zero flags; manual review remains separate.
- All 14 pinned older-vault negative cases reproduced their verified failure
  causes in a separate public-file-only copy. It was removed before the green
  suite; the accepted source/test tree stayed unchanged.
- The six narrow JSON receipts and the separately uploaded original candidate
  artifact passed byte-identical root/peer independent replay. The receipt
  artifact is `12463951940` / `ab2a5e8089c1036b4ce26b7a8dfd3569ed2f7183acc4489a5e23caeea52746ea`; the
  candidate artifact is `12464092121` /
  `bd97e246e345df5174277245b90cb75574954207193a3a3dc6707dc5cd047714`. Both artifact digests were verified
  against separately obtained GitHub metadata.
- [Permanent evidence and portable replay](https://github.com/jmhjr/HomeCircle/blob/f1cf62bca163b8adf59ec6dc497ee581fd8d7e8b/native-fixed-package-evidence/INDEX.md)
  retain the artifacts, both metadata records, frozen harness/consumer and source catalog.

The original frozen R1 evidence consumer refused this packet because it expected
a redundant privacy `source_files` key. The unchanged producer's privacy receipt
uses `files_checked: 381`; its six-receipt schema and the native outcome were not
changed. R2 removed that consumer-only expectation, retained the original refusal
and source-justified amendment, and added a producer-AST schema regression. The
accepted R2 root/peer replay used the same native run, frozen harness and dual
artifact bytes. No native rerun was performed or needed for that correction.

## Runtime and archive identity

Execution used native Linux/amd64 and pinned Core 2026.10.2 with Python 3.14.6,
pytest-homeassistant-custom-component 0.13.373, Node 23.7.0 and npm 10.9.2.
The image registry digest was
`sha256:45f009d6ff1061971102e81f0802cf2762bdd5c5007231c938bd36030cbd0a12`;
Core constraints SHA-256 was
`7baa9a8f39ddeb9c5bb60a1036f6d5e33f4b84267f151f53cc2b95ef031a21b5`.
The actual product 24-package closure and reviewed Core component/default-auth
requirement graph/versions were verified. Dependency preparation completed before
verified network disconnection; all backend pytest and negative cases ran offline.
No owner accounts or production configuration were used. The owned container and
private workspace were removed, including raw logs. The working test instance
remained running; protected working files/refs were preserved and no new Mac
Python crash report appeared.

The input candidate ZIP `f181e6300f15d8977817a552db90d35caf0edc869067ebeea815c7be1df0248e` uses compression level 6; its unchanged
inventory is `8ea456beb9b2eaaf4ba50639532b8dafabe0e02d1e13a77a59525f1c249c7447`. All 113 candidate member bytes were verified in
the public source/test tree. Its exact Git-bound source-only `README.md` was
additionally retained and checked before/after; this is not a pure 113-file
installed directory.

The unchanged canonical builder uses compression level 9 and reproducibly built
`acfcda419a817032c38a463505f686b0f6ab49e69a8f1603d9b2ff43f24e442b` from the same 113 member names and bytes. That canonical archive
has a distinct byte identity and was reported separately. The original f181 ZIP
and 8ea inventory were the tested/exported candidate; neither was silently
replaced or promoted by the canonical rebuild. No version substitution occurred.

## Scope and remaining gates

The earlier full-package result remains tied to minimum Core 2026.9.4 and old
012a/98a runtime bytes. This run adds the complete current-Core suite for the exact
fixed candidate. The [ordinary restore](RELEASE-1.0-FIXED-ORDINARY-RESTORE.md) and
[private installation-copy upgrade](RELEASE-1.0-PRIVATE-UPGRADE.md) retain their
separate scopes. This package run repeats neither experiment and adds no new
HAOS lifecycle, HACS delivery, live provider authentication/renewal, live recovery,
field, cloud/full-system restore, RC or stable-release acceptance.

The advertised platform/upgrade contract, provider permissions and source/license
obligations, specialist security/format disposition, remaining owner acceptance
and all other open release-plan gates remain open unless separately completed or
explicitly excluded. No merge, production upgrade, stable tag or release is
authorized by this result.
