# Stable preparation: polling isolation and test baseline

October 19, 2026. Local candidate on `codex/ruby-person-card`, based on
`373203a85da0e1f9c4d7d3c2eabfd31663475bee`. This is implementation evidence,
not stable-release approval. No version, tag, public release, live HA installation
or Apple account was changed in this work.

## Behavior

Account polling now isolates selected items, retains validated reports from
completed batches when a later batch fails, and resumes historical search only
past indices whose required primary and secondary keys completed. The existing
bounded historical/recent windows and conservative secondary-key alignment remain.
An item timeout no longer consumes another item's entire deadline. Requests remain
serial within an account; this adds no automatic authentication retry.

Malformed individual report rows, payloads, unknown hashes and failed report
GCM/curve validation are discarded before selecting a latest report. Valid older
records for the same key and valid neighboring keys remain usable. Invalid batch
envelopes and service/authentication failures still propagate at their appropriate
boundary. The repaired SDK sequence-key path is the path HomeCircle uses; this is
not a claim that every upstream rolling-accessory API has equivalent isolation.

A partial account result saves completed progress and updates healthy trackers
normally, with a partial provider health state. Failed items retain earlier usable
coordinates and receive failure status. Authentication expiry stops that account,
requires reconnection, and saves any completed progress. Cancellation drains a
pending vault write, including repeated cancellation, before reconnect/unload can
replace the old session. A vault-write failure is not reported as success or
immediately retried. Genuine source report time stays distinct from poll time.

The existing Ruby Person/item projection and strict-save fix is preserved byte for
byte; its 14 synthetic regressions remain included. The separate licensing/service
terms edits to the stable audit are also preserved.

## Fixture provenance

The two pre-existing endpoint-policy failures were a stale expected fixture hash.
A fresh official FindMy 0.10.2 PyPI wheel matched its published SHA-256. The fixture's
three complete method ASTs and the retained MIT license match that wheel; fixture
bytes are identical at their original commit, beta 19 tag, HEAD and working tree.
Only the expected digest was corrected. All 39 endpoint-policy cases now pass,
including both request-byte comparisons. See the [reproducible provenance
record](../tests/fixtures/findmy_0102_gsa_reference.provenance.md).

## Validation and limits

New regression coverage uses actual synthetic rotating accessories at 100 and
180 days, persisted-state reconstruction after a later timeout, no skipped failed
keys or secondary-key requirements, quiet and healthy items together, isolated
transport failure, auth expiry after valid results, and no timestamp regression.
Actual SDK parser/AES-GCM tests cover malformed rows and payloads, bad tags,
invalid curve points, unknown hashes and invalid top-level envelopes. Network
access is disabled. The new decoder cases fail against the original parser/decoder;
the historical-timeout regression fails against the original account poll.

The checkpoint passed **1,062 backend tests** with one optional public-installer
fixture test skipped, **109 frontend tests**, Ruff, whitespace checks and the
public-file guard (287 files). A local 109-file integration archive passed exact
inventory/source inspection plus separate-process install, upgrade, restart,
removal and post-removal restart in disposable HA Core. Its SHA-256 is
`947059feee038debb514bc1de7493a6487bad7d27282215ca00051d4f8b8615c`.
This checkpoint predates the separately recorded SRP/startup follow-up work.

Disposable package checks do not exercise an Apple account, native
runtime platform compatibility, an actual published-beta upgrade with retained
Find My keys, a long field run, movement latency or physical DAKboard acceptance.
Those remain release gates.

Private development receipts are retained under
`work/stable-milestone1-validation/`; frozen Claude inputs/reports and the canonical
published beta 19 ZIP remain unchanged. This local candidate retains the beta 19
manifest version and must not be mistaken for the immutable published package.
