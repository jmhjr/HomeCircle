# Current Find My source and accepted AI review

The pre-exclusion implementation baseline is canonical source c31c220563ae55d469bbf530fa77dd2f80583910.
The [source manifest](RELEASE-1.0-ASSURANCE-SOURCE.json) binds 74 primary Find My/recovery
Python members plus 31 public context files to exact Git blob IDs and SHA-256 hashes.
All 74 primary members match the previously tested f181 candidate. The first-release qualification candidate excludes the unused local macOS plist.py/__main__.py pair; the final b906 source retains 70 primary Python files identical to this review baseline, removes the two unused Mac files, and changes findmy_flow.py and findmy_provider.py for connection controls. The historical review manifest remains unchanged; it is not an all-retained-files-unchanged declaration for the final candidate. See [the exact exclusion](RELEASE-1.0-LOCAL-MACOS-EXCLUSION.md). The
[change inventory](RELEASE-1.0-ASSURANCE-CHANGES.json) identifies six changed primary
files since the older 9bf03eb assurance handoff. Historical all-74-unchanged
statements apply to their historical snapshots.

## Completed review and maintainer decision

The [Claude AI review](RELEASE-1.0-CLAUDE-REVIEW.md) and its
[structured result](RELEASE-1.0-CLAUDE-REVIEW.json) report zero confirmed actionable
defects in the six changed paths and reached call chains. The reviewer disclosed
partial coverage, no code execution and no independent Apple-produced vectors.
Read/Glob/Grep were the only available tools; no account, provider, browser, shell,
write or MCP tool was available. All 382 supplied public Git files were verified
unchanged after review, and the owned temporary public copy was removed.

On October 22, 2026 the maintainer explicitly accepted Claude's AI review with
documented limits as the independent technical-review method for 1.0. This
supersedes the earlier qualified-human-review requirement for this release.
It does not assert that a human audit, independent producer-format proof, full
membership/revocation verification or comprehensive protocol assurance occurred.
The [six-question source follow-up](RELEASE-1.0-CLAUDE-QUESTION-TRIAGE.md) found no
confirmed fix; it corrects two overbroad assumptions while preserving test/coverage limits.

## Evidence and boundaries retained

Current-Core full-suite, ordinary Person/activity/Recorder partial restore and
private installation-copy upgrade remain separate exact-source/artifact records.
They are not protocol specifications. The local recovery witness does not protect
a joint ledger/cache filesystem or VM snapshot, and an old backup can restore
vulnerable older code. The supported ordinary partial-restore scope is explicit
in the [maintenance guide](RELEASE-1.0-MAINTENANCE.md).

The [final qualification record](RELEASE-1.0-FINAL-QUALIFICATION.md) separates the accepted 548-case controls run, accepted focused minimum-Core result, accepted full current-Core R3 result and accepted fourteen-phase genuine HACS delivery result. These checks do not enlarge Claude's disclosed coverage.

The accepted final RC receipts capture actual cryptography/srp/unicorn versions and the target's component/default-auth dependency graph. Current Core observed 50.0.1/1.0.22/2.1.4; minimum Core observed 48.0.1/1.0.22/2.1.4. Constraints alone would not establish those installed versions. Do not broaden the historical cryptographic report's runtime.

No credentials, private account replies, saved sessions, Apple libraries,
dependency binaries or personal locations are included in this public handoff.
The [distribution questions](RELEASE-1.0-DISTRIBUTION-QUESTIONS.md) remain a
separate gate. No provider permission or legal clearance is asserted here.
