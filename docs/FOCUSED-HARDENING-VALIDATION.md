# Stable preparation: focused hardening review

October 19, 2026. Local uncommitted candidate on `codex/ruby-person-card`, based
on `373203a85da0e1f9c4d7d3c2eabfd31663475bee`. This follows the
[recovery and identity checkpoint](RECOVERY-IDENTITY-VALIDATION.md). The published
experimental release remains beta 19. No live Home Assistant configuration,
Apple account, commit, push, version, tag or publication was changed.

## Confirmed findings and fixes

| Area | Reproduction and resulting behavior |
| --- | --- |
| Worker dependency discovery | A child with ordinary Python paths could miss Unicorn installed through Core's private dependency directory. The parent now resolves only the installed Unicorn package in an executor and passes its exact package path through private IPC. The child loads that package, including its relative/native imports, without copying the parent's search path. A real child with a synthetic package under a `/config/deps`-shaped directory verifies the boundary. This does not qualify HAOS or Container native execution. |
| Verified library bytes | The worker hashed one read but the emulator reopened the path. A pathname-replacement regression demonstrates the gap. The worker now reads a bounded regular file through one no-follow descriptor, checks its size/stability/digest and passes those exact immutable bytes to the emulator. No second library-path read occurs. |
| Unchanged vault writes | Repeated saves of identical minimized state changed ciphertext and replaced/fsynced the file. Canonical JSON comparison now skips encryption and replacement after validating the existing vault. Changes to tokens, reports, cursors, selections, identity preferences and JSON scalar types still persist. Unreadable or unsafe storage still fails closed. |
| Emulator entropy | Both default and Mac-specific random hooks returned fixed words/patterns. They now use the host OS-backed `secrets` source, with fixed errors and no deterministic fallback on failure. Actual Unicorn hook tests inject distinct entropy and verify each request consumes it. |
| Emulator memory bounds | Scratch, object and heap cursors could exceed their mapped regions. Two individually permitted 128 KiB provisioning inputs could consume all scratch space before dispatcher metadata overwrote guest objects. Allocators now reject exhaustion without advancing cursors; combined aligned input/metadata budgets are checked before writes. Output reads and random-buffer requests are bounded. Exact-fit, one-byte-over, sentinel and ordinary-operation controls cover the boundary. |
| Recovery signatures | Actual recovery accepted a bottle with an invalid escrow signature or an invalid supplied sponsor signature. Key-share unwrapping could use material with a failed sender signature. HomeCircle's recovery path now requires the escrow signature and any known sponsor signature to verify, and its key-share path requires a known verified sender. Low-level diagnostic helper modes remain explicitly non-enforcing by default; they are not the integration's key-use path. |
| Bottle tag length | Detached bottle tags were accepted after truncation to 4, 12 or 15 bytes. That format's existing writer emits 16 bytes; its reader now requires all 16. The separate PCS format's intentional 12-byte tag is unchanged. This is format-specific validation, not a universal change to every GCM construction. |
| Recovery CPU work | The inner blob supplied a 32-bit PBKDF2 count with no work cap, and key derivation ran inline in the async recovery method. Counts now must be between 1 and 1,000,000; this is an explicit local resource policy, not an Apple protocol maximum. The existing writer's 10,000 iterations remain supported. Recovery offloads and cancellation-drains the bounded derivation before returning, preserving verified-proof/error boundaries without a detached passcode worker. |
| Cancellation failure logging | Python 3.14 shield observers could log a late failed task after caller cancellation, before subsequent exception retrieval. Synthetic canaries reproduce this on cancelled recovery work, commits, vault writes and cleanup. A non-raising outcome observer is now shielded instead; work drains and the appropriate original cancellation or error is preserved without that automatic log. |
| Cleanup and key lifetime | A failed or cancelled session close could skip sibling transports; a failed worker close could leave transient identity/cache references on a closed provider. Cleanup now attempts and drains owned resources, preserves failure/cancellation and retains failed worker ownership for retry while clearing transient provider state. The earlier broad-key/cache cleanup is revalidated; no memory-zeroization guarantee is claimed. |

The entropy choice follows Python's [documented OS-backed secrets source](https://docs.python.org/3.14/library/secrets.html).
The bottle tag change agrees with the producer and the cryptography library's
[full-tag default and truncation guidance](https://cryptography.io/en/latest/hazmat/primitives/symmetric-encryption/#cryptography.hazmat.primitives.ciphers.modes.GCM).
Offloading uses Python's [thread execution API](https://docs.python.org/3.14/library/asyncio-task.html#asyncio.to_thread);
thread/cancellation controls and actual encrypted round trips are tested locally.
These sources support the API choices, not Apple's proprietary format or live
service compatibility.

## Validation

The 112-file candidate retains manifest `0.1.0-beta.19` because final release
versioning is undecided. SHA-256:

`b52097c6f6f88e206ca9ef48618ad00984a95c49d4b588da883232981ab7f2de`

Final checks passed:

- **1,320 backend tests**, with one optional test skipped because the public
  Apple installer fixture is not retained. Network sockets are disabled by
  default. This includes 99 additional regressions after the prior checkpoint.
- **110 frontend tests**, the frontend build and Prettier. Frontend production
  source is unchanged by this hardening batch.
- Ruff across integration/tests, whitespace checks and the public-file guard
  across 308 files, with no flagged patterns. Automated scans do not replace
  manual privacy review.
- Exact archive/inventory/source matching and fresh-process imports of 13
  selected entry/provider/SDK/runtime modules from the extracted ZIP, with network
  connections prohibited and ordinary SRP globals preserved.
- Separate-process disposable Core install, version-fixture upgrade, restart,
  removal and post-removal restart. Unrelated resources survive; the removed
  integration's static bundle is absent. Temporary configurations are removed.
  This is not a canonical published-beta upgrade or HACS test.
- Repeated four-process encrypted-vault identity continuity after the vault-write
  change: omission/reselection restores proven IDs/preferences without retained
  omitted tracking keys, and changed-key/foreign-account controls are refused.
- Reciprocal source review and independent focused runs across runtime, recovery,
  vault and cancellation boundaries, with the resulting fixes included in the
  full run. This is not a formal cryptographic audit.

Focused tests include generated valid signed/sealed bottles and shares, forged
and missing signature controls, full/truncated tags, actual CBC/PBKDF2 recovery,
thread/lifetime and cancellation-log canaries, close failures/cancellation, changed/unchanged encrypted
vaults, and actual Unicorn execution of a tiny synthetic dispatcher through
worker IPC. No Apple executable, owner credential, private vault, location or
research-history input was used for the new reproductions. No wrong owner
passcodes or automatic live recovery requests were attempted.

The Ruby fix, prior polling/isolation/recovery/identity fixes and frozen published
ZIP/review evidence are preserved. Receipts, focused/full logs, source hashes and
snapshot, candidate archive/inventory and reproducible ZIP import checks are in
`work/stable-hardening-validation/`.

## Review decisions and remaining limits

A recovered bottle from a departed peer can still use the existing missing-sponsor
fallback, with its escrow signature enforced. Sponsor provenance is not established
in that case. Requiring a currently listed sponsor would change that compatibility
policy; it remains an independent cryptographic/product review item. In contrast,
key shares without a known verified sender are refused on the key-use path.

Scratch capacity stays 256 KiB. An individual IPC field's 128 KiB allowance is not
a combined provisioning allowance: aligned inputs, the 0x800-byte dispatcher buffer
and its parameter cells must fit together. Oversized combined requests are now
refused rather than corrupting the adjacent guest region. Actual Apple
provisioning-size compatibility remains unqualified.

The worker retains its existing operation deadline and process CPU/memory limits;
no speculative instruction cap was added without a native baseline. Python audit
hooks restrict normal Python network, subprocess and write operations; these are
not an OS sandbox for native dependencies. Bootstrap checks were reviewed without
finding an additional confirmed defect in this scope; its optional public installer
fixture remains absent. The fixed ten-iteration PCS derivation and fixed-count
unused enrollment writer do not share the recovery blob's unbounded work field.

Local synthetic checks do not establish exploitability, a formal cryptographic
audit, live Apple recovery/provisioning compatibility, HAOS/Container/amd64
acceptance, sustained field behavior, the real published/installed-state upgrade,
HACS or physical DAKboard acceptance. The [stable checklist](STABLE-RELEASE-CHECKLIST.md)
retains those gates and the licensing/service-use and final release decisions.
