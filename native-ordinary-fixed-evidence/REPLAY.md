# Replay the exact retained evidence

Use a fresh disposable checkout containing this evidence directory and its
unchanged sibling native-ordinary-fixed-restore fixture. The native fixture and
workflow are from QA commit 3c0091e17e3e1283b609d7a484dc4e20128436a0; its 30 inputs
are bound in INPUTS.json. The consumer reads bounded AST literals and never
imports or runs the native fixture. The artifact contains only five public JSON
receipts. Root GitHub metadata is kept separately and bound to its digest.

Verify all seven collector files against PROTOCOL-FREEZE.json before execution.
The collector itself is 8d6108a5b3ec3c4d764148ae017acea0e14a35e929e1ac8a51f8675b1ff0aeb5.
Then, from the repository root:

    python3 -B native-ordinary-fixed-evidence/independent_ordinary.py --fixture-dir native-ordinary-fixed-restore --workflow .github/workflows/native-ordinary-fixed-restore.yml --artifact-zip native-ordinary-fixed-evidence/artifact.zip --metadata native-ordinary-fixed-evidence/ROOT-METADATA.json --output /tmp/homecircle-person-activity-review.json

Compare the result byte-for-byte with INDEPENDENT-REVIEW.json. No VM, provider
authentication, owner account, recovery proof or network request is needed for
this local replay. Run the 17 finite consumer contracts from the evidence
directory only after supplying the fixture/workflow layout expected by those
tests, or invoke the frozen parser directly as above.
