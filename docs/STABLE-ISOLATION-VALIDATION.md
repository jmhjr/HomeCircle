# Stable preparation: combined failure isolation candidate

October 19, 2026. Uncommitted candidate on `codex/ruby-person-card`, based on
`373203a85da0e1f9c4d7d3c2eabfd31663475bee`. See the current
[stable checklist](STABLE-RELEASE-CHECKLIST.md) for unresolved work. No production
HA installation, Apple login, version, tag, commit, push or publication occurred.

## Changes after the polling checkpoint

GSA and recovery execute the installed `srp==1.0.22` pure-Python implementation in
two private fixed-mode namespaces. Each has RFC5054 compatibility enabled and its
required username-in-x setting. Ordinary dependency globals remain unchanged;
no mode change spans an await and no SRP equation is copied or reimplemented.
The actual installed implementation's SHA-256 was
`a1600e7ee7b2b7b203f9cad488fd7e0a441297597743ba5433ed9c5193e7a359`.
Twelve synthetic tests compare actual proofs with sequential references under
overlapping sign-in/recovery, two recoveries, failure/cancellation, poisoned
ordinary flags and independent external-thread changes. Fresh-process imports
also test selector independence and preservation of ordinary SRP flags.

Provider startup now catches construction/start errors per provider, cleans only
its resources and continues to other providers. A fixed, actionable Repair issue
survives while the partial entry is loaded and clears on successful retry/unload.
Failed providers are absent from managed clients; diagnostics show `not_loaded`
rather than a misleading connected placeholder. This preserves Find My's existing
pause/resume management contract. Cancellation remains terminal and drains current
and newly started cleanup before releasing map ownership, even under repeated
cancellation. Logs contain provider IDs and exception classes, not exception text
or account values. Real shared-startup regressions reproduce SDK-import failure,
prove successful siblings/later providers survive, and preserve registry rows.
The unchanged integration-wide normal unload loop remains separate from this
startup boundary.

The complete 1,065-byte pinned OpenTagViewer MIT notice was added to the existing
packaged SDK license, preserving existing notices. Its SHA-256 is
`e5d3404f06c194c08bfd18bfe4d42ece466f28098177b38c14aeb2bfe6b39597`.
The packaging regression uses actual derived code and notices with disposable
frontend fixtures, then builds/inspects a ZIP and verifies the complete inherited
notice. It requires no npm build or network on a fresh checkout. This closes the
specific missing-notice defect, not the remaining license/service-use gates.

## Candidate and validation

The local archive contains 110 files and retains manifest `0.1.0-beta.19` solely
because final versioning is not decided. SHA-256:

`3e6bcc3876aff7297c5f5a3ce93649d20e31339f44d587fe815db97a94bd5157`

This differs from the immutable published package. Frozen review inputs and the
published ZIP retain their original hashes. The Ruby source files retain the
hashes recorded in the handoff; no private research history, state or keys were
copied into source or package.

Final checks passed:

- **1,084 backend tests**, with one optional public-installer fixture test skipped;
  socket access is disabled in the suite. The adjusted notice-archive test also
  passed in the separate 29-case package suite without frontend build inputs.
- **109 frontend tests** and a frontend build; frontend source is unchanged by
  the subsequent SRP/startup/license work.
- Ruff across integration/tests, whitespace checks and the public-file guard
  across 293 files (automated pattern checks do not replace manual review).
- Exact 110-file archive/inventory/source matching and a fresh-process import of
  six selected entry/provider/SDK modules from the extracted ZIP with network
  connections prohibited; private SRP modes loaded and ordinary flags stayed
  unchanged.
- Separate-process disposable Core install, version-fixture upgrade, restart,
  removal and post-removal restart, preserving an unrelated frontend resource
  and removing the served integration bundle afterward. All temporary configs
  were removed. This is not an actual published-beta upgrade or HACS test.

Local checks do not establish actual Apple acceptance, a formal
cryptographic audit, the exact recovery-attempt policy, broad native platform
support, long-term reliability, an actual published-beta upgrade, or physical
display acceptance. The private backend loader requires a filesystem-backed
Python module; zipped/non-file installations remain unqualified.

Development receipts remain in `work/stable-isolation-validation/`, including
backend and package-lifecycle logs, extracted-ZIP import verification, candidate
archive/inventory and source hashes. These use synthetic data and no existing HA
configuration or Apple service.
