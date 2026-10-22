# Replaying the ordinary restore review

This bundle preserves the exact offline evidence consumer and its retained native
receipts after the original GitHub artifact expires. It targets only
[QA commit 4957b3f](https://github.com/jmhjr/HomeCircle/tree/4957b3f44e84837e01af731286c0728a4127aea3/native-ordinary-rollback-restore),
the corresponding
[frozen workflow](https://github.com/jmhjr/HomeCircle/blob/4957b3f44e84837e01af731286c0728a4127aea3/.github/workflows/native-ordinary-rollback-restore.yml),
and [native run 39721983991](https://github.com/jmhjr/HomeCircle/actions/runs/39721983991).

The retained consumer reads all fixture bytes and hashes without importing or
executing the fixture. It does not repeat the VM experiment or contact GitHub,
Home Assistant or a provider. It binds all 113 unchanged product members to the
candidate ZIP and source inventory. Root metadata is a separately verified trust
record from the original GitHub download, stored outside the native artifact.

The successful result, if present in the published bundle, is limited to a
synthetic ordinary partial restore using the original product manifest and
ordinary Home Assistant requirement installation. The test environment supplies
a separate transport fence. It must prove guard counters **2 → 3 → 2 → 2**,
automatic review/blocking on both restored processes, and zero manual guard
exports, imports or owner acknowledgments after restore. It does not establish
real provider authentication, full encrypted cloud recovery, a full VM snapshot
rolling back both guard files, or a stable release.

The bundle contains the five immutable consumer files, its frozen file manifest,
the exact downloaded artifact ZIP, separately verified root metadata, and the
independent review output. Original artifact bytes and metadata are retained
unchanged. No raw credentials, vaults, ledger contents, test configuration,
coordinates, private logs or native VM archives are published.

Obtain the exact `native-ordinary-rollback-restore` directory and workflow from
the frozen QA commit above. Use a separate local copy; do not replace files in a
working Home Assistant installation. The evidence publication can be checked out
elsewhere. From that publication's repository root, point `--fixture-dir` and
`--workflow` to the frozen copy and run:

```sh
python3 -B native-ordinary-rollback-evidence/independent_ordinary.py \
  --fixture-dir /absolute/path/to/frozen-qa/native-ordinary-rollback-restore \
  --workflow /absolute/path/to/frozen-qa/.github/workflows/native-ordinary-rollback-restore.yml \
  --artifact-zip native-ordinary-rollback-evidence/evidence/native-result.zip \
  --metadata native-ordinary-rollback-evidence/evidence/root-metadata.json \
  --output fresh-ordinary-review.json
```

The output path must be new and outside the frozen fixture. Existing files are
never overwritten. The original consumer README retains its preparation-time
directory examples; the explicit paths above are the portable replay command.
Expected output is `outcome: passed` only when every independent binding and
typed schema check succeeds. Comparing the resulting context and receipt hashes
with the retained independent output verifies the replay; the collector file
hash itself is included in that output.

Before trusting a local bundle, compare its files with `FROZEN-COLLECTOR.json`
and the exact publication commit. Review the linked run and metadata provenance.
The frozen input map and source inventory are inputs to the consumer and are
also hash-pinned inside it. Editing those records is not a valid replay.
