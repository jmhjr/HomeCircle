# Provider safeguards: exact focused evidence

[Native run 39988121148](https://github.com/jmhjr/HomeCircle/actions/runs/39988121148)
passed on Linux/amd64, Core 2026.10.2/Python 3.14.6, attempt 1, push event at QA
8a57ce7618288eb0afbc023949084914a6f78885.

- Source c7b31c5a82431a6b16d8b7208f9423626b95bd4b: all 402 canonical Git blobs.
- Unreleased 1.0.0-rc.1 ZIP: 112 members, 110 literal and 2 generated frontend assets.
  SHA256 4f94a18e2f7862e9bd7f4c85250e5f10e4b8e1292ea9d7b263b441d2e1b77dd9.
- 26 selected modules,345 declared base functions,548 actual cases passed; zero
  failures, skips or deselection. Full collection identities matched JUnit.
- Actual dependencies/default-auth requirement graph and pinned image were checked.
  Tests ran after network disconnection; container and private workspace cleanup passed.
- Frontend 126 passes belong to the unchanged JavaScript source and reviewed generated
  asset bytes. This native packet does not claim it reran the frontend.
- No real accounts, production configuration, owner VM, KVM, managed-Core lifecycle,
  upgrade, restore, HACS install or stable-release action was used or qualified here.
  This is an affected-code run, not a repeated full backend suite or CPU matrix.

## Replay and transport

The five exact successful receipts are under receipts/. config.json is frozen at
SHA256 5303e76bf33e49747aca6fe4f589ebb5219c19dd41369db73cf18c008a19f664.
SOURCE-EXPORT.json binds all 402 public source names, lengths, SHA256 and Git blob IDs.
The source/package inputs and producer are retained in the same QA history under
native-no-outreach-hardening-r5; the source remains on codex/release-1.0.

The original downloaded artifact.zip and TRANSPORT.json are retained. The downloader
bound repository, exact workflow/head/branch/event, attempt 1, job success, artifact
ID and GitHub artifact digest before extracting only the five safe JSON files.
Compare the ZIP SHA256 to TRANSPORT.json; its five member bytes must match receipts/.
The standalone consumer verifies content, not GitHub transport:

    python3 verify_results.py --config config.json --config-sha 5303e76bf33e49747aca6fe4f589ebb5219c19dd41369db73cf18c008a19f664 --results receipts --output REPLAY.json

ACCEPTED.json is the root replay. The peer independently repeated the replay and
compared output bytes; that is a receipt replay, not an independent provider test.

## Retained unsuccessful attempts

Each failed-* directory retains the original digest-checked safe artifact ZIP
and transport metadata, including its producer refusal and cleanup.

- Run 39983494063: two immutable-data fixture errors and two background-poll
  synchronization assertions, plus resulting teardown errors.
- Run 39984541655: one remaining synthetic tracker identity was invalid, visible
  when the paused account correctly remained unloaded after restart.
- Run 39985564780: all 543 backend cases passed, but the producer rejected a proper
  65,624-character parameterized name against its old 1,024-character private cap.
  AMENDMENT.json records the narrow 128 KiB private-name bound correction, preserving
  complete identity equality/uniqueness. Long-name mutation and overbound contracts
  passed; private parameter text is not in these public diagnostics.
- Run 39986619782 then passed/was accepted with 543 cases for the preceding source.
  The final follow-up adds visible Pause/Resume for orphaned or explicitly selected
  external Life360 requests, with five new cases. The final 548-case result above
  qualifies that changed source/package.

Technical results do not create provider permission or legal clearance. Final
frozen-RC/full-suite/HACS/owner acceptance and maintainer distribution decisions
remain separate in the release plan. No permission request was sent.
