# Independent evidence replay for native run 39708377110

This consumer validates the retained public evidence from exactly native run
`39708377110`, attempt `1`, at QA commit
`9605b5fe280679c2b621973f862fdecadb4e8c53`. The native fixture and its workflow
remain frozen. The consumer performs local reads only and creates one new review
file; it does not run Home Assistant, import native providers, contact GitHub,
modify Git, start a VM, or change the original artifact.

The consumer closes a confirmed gap in the earlier scoped acceptor: mutually
consistent manifest or payload fingerprints could pass without matching the
reviewed files, and some nested metadata accepted foreign fields or loose types.
The new checks independently reconstruct the product inventory and deterministic
QA manifest, bind every controller/helper/guard/storage/reset/preparer hash to
the frozen inputs, and require the known nested public schemas and exact types.
The original scoped acceptor runs afterward, preserving its restore, history,
context, cleanup, startup-denial and qualification rules.

## Replay

Keep the original native fixture beside the published consumer directory:

```text
native-release1-enabled-saved-restore/
native-release1-enabled-evidence/
  independent_evidence.py
  INPUTS.json
  evidence/native-result.zip
  evidence/root-metadata.json
```

From the repository root, create a fresh review file:

```sh
python3 -B native-release1-enabled-evidence/independent_evidence.py \
  --fixture-dir native-release1-enabled-saved-restore \
  --artifact-zip native-release1-enabled-evidence/evidence/native-result.zip \
  --metadata native-release1-enabled-evidence/evidence/root-metadata.json \
  --output native-release1-enabled-evidence/replayed-review.json
```

`--fixture-dir` also supports the existing local prepared folder. `--workflow`
can select an explicit saved workflow file. Otherwise the consumer checks the
fixture's sibling `workflow.yml` or the repository's fixed workflow path.
The copied `INPUTS.json` must retain SHA-256
`f2694cd158c8c291499d9936e6faa0c3ae72d19e1e4fbb2b21baf4766ea4fc44`.
It binds all 27 native fixture files plus the workflow. The workflow's own
all-file verifier map must agree with those frozen files.

The artifact must contain exactly the six fixed JSON receipts. The consumer
rejects unknown names, duplicate entries, links, unsafe paths, oversized members,
duplicate JSON keys, nonfinite numbers and unknown nested public fields. Input
files are read without overwriting or extracting them. An existing output file
is refused.

## Separate root metadata

Metadata must come from a separately verified GitHub run and artifact download;
it must not be generated from the artifact's own receipts. The consumer checks
this supplied trust anchor but does not authenticate GitHub or download anything.
The root-supplied metadata has exactly these fields:

```json
{
  "schema": 1,
  "run_id": 39708377110,
  "run_attempt": 1,
  "head_sha": "9605b5fe280679c2b621973f862fdecadb4e8c53",
  "branch": "codex/native-amd64-validation",
  "event": "push",
  "workflow_path": ".github/workflows/native-release1-enabled-saved-restore.yml",
  "workflow_sha256": "4c8d41c10ce0c3845ef4009e6e743f10d3b5d9beeb31ad4dcfdffca9a4216c1a",
  "artifact_id": 12396467363,
  "artifact_name": "release1-instrumented-enabled-saved-restore",
  "artifact_zip_sha256": "b6063a5f1632db51b5e2daebb5f779d114a177f97353174f7657daf625ac4856",
  "github_digest_verified": true,
  "status": "completed",
  "conclusion": "success"
}
```

The root verified the GitHub artifact digest against the retained 10,239-byte ZIP.
The independent replay of that unchanged ZIP passed and is recorded in
`COLLECTOR-ACTUAL-REPLAY.json`. The record includes the collector's own SHA-256,
all six original receipt hashes, the frozen input/workflow bindings and the
original scoped acceptance result.

## Scope

A pass qualifies this run's **instrumented enabled synthetic partial restore**
under default Supervisor conditions, with explicit newest-guard repair. Its guard
sequence remains `2 → 3 → 2 → 3 → 3`. The first restored startup loaded the older
guard before repair. The consumer preserves the false gates for automatic guard
antirollback, ordinary uninstrumented restore safety, real provider authentication,
full/encrypted cloud backup and stable release approval.

Source/tool fingerprints are independently recomputed from the frozen files.
Dynamic synthetic guard, history and prepared-dependency inventory fingerprints
remain native observations: their required schema, consistent relationships and
source-bound checks are validated, while their deleted private source stores are
not reconstructed. This is a replay of the specified retained run. Future runs
and generic CI acceptance are outside this consumer revision's scope.

## Contracts

Run the 32 stdlib contracts without Home Assistant or provider imports:

```sh
python3 -B -m unittest discover \
  -s native-release1-enabled-evidence -p test_current_evidence.py -q
```

They cover the five demonstrated forgeries, every tool/source provenance field,
foreign nested private keys, exact count types, module-cache isolation, workflow
and input tampering, unsafe ZIP/JSON forms, separate run/artifact metadata,
startup and recovery rules, fresh review output and preservation of original
input bytes. The original native fixture's separate 186-contract result remains
unchanged.
