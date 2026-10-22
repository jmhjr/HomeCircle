# Replay the exact retained evidence

Use a fresh disposable checkout containing this evidence directory and its
unchanged sibling native-person-activity-restore fixture. The native fixture and
workflow are from QA commit 4b464723fe63bafc62f92e17e538e566278ee1c0; its 30 inputs
are bound in INPUTS.json. The consumer reads bounded AST literals and never
imports or runs the native fixture. The artifact contains only five public JSON
receipts. Root GitHub metadata is kept separately and bound to its digest.

Verify all six collector files against FROZEN-COLLECTOR.json before execution.
The collector itself is 1435f4c5c3fc6c968ef0a947d2ba5d3a84639498fda8816f04d5f180f1bcce17.
Then, from the repository root:

    python3 -B native-person-activity-evidence/independent_ordinary.py --fixture-dir native-person-activity-restore --workflow .github/workflows/native-person-activity-restore.yml --artifact-zip native-person-activity-evidence/artifact.zip --metadata native-person-activity-evidence/ROOT-METADATA.json --output /tmp/homecircle-person-activity-review.json

Compare the result byte-for-byte with INDEPENDENT-REVIEW.json. No VM, provider
authentication, owner account, recovery proof or network request is needed for
this local replay. Run the 17 finite consumer contracts from the evidence
directory only after supplying the fixture/workflow layout expected by those
tests, or invoke the frozen parser directly as above.
