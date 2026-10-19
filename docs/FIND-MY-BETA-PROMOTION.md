# Find My promotion history

This is a historical planning and research record. Current release scope and
acceptance are recorded in [beta 19 validation](BETA19-VALIDATION.md) and
[the October 19 packaging record](FINDMY-BETA19-PACKAGING-VALIDATION.md).
The historical Android identity and prototype migration checkpoints below do not
describe the newly packaged Mac identity runtime. Public migration routes are
omitted under the maintainer scope decision at the end of this document.

The maintainer selected inclusion in the next HomeCircle beta, rather than a separately released Find My integration. Development is isolated on `codex/findmy-beta`, based on published beta 18 plus its validation record. This is a promotion checkpoint, not a release or a claim that onboarding is distributable. The existing installation, account sessions, item keys and tracker history are preserved.

## Intended supported beta path

- Linux HA OS with a native Python provider; no Mac, Terminal/SSH, manual key copying or user source compilation. Declare other installation types separately.
- HomeCircle settings offers Find My accounts. Each account has independent authentication, encrypted local storage, polling, failure state and reauthentication. No fixed item/account count limit; disclose practical Apple/host limits.
- Account owner completes Apple verification and separately consents to Keychain recovery. Do not present broader account trust access as a one-item location read. Credentials/passcodes/codes stay transient and never enter config entries, diagnostics, URLs or logs.
- Discover supported items, distinguish already configured items, select additional items and retain stable identities. Item names and manually selected types do not prove ownership.
- Preserve actual source-report times, uncertainty, delayed/empty reports and coarse battery categories. Polling and HA observation times never become new location-report times.
- Show tracked items separately from people and household counts, with their pictures and Details. Ordinary HA trackers continue to work independently.

## Migration and release gates

1. Resolve exporter redistribution before copying upstream Rust code or publishing helper binaries/images. Review the separate dependency license and corresponding-source obligations; do not apply HomeCircle's MIT license to upstream work.
2. Adapt the tested polling/vault flow to HomeCircle-managed accounts. Maintain a guarded mapping from legacy config entries and registered tracker identities. Demonstrate migration and rollback in disposable HA before touching a live vault or entity registry. No replacement `_2` entities, lost history, new enrollment or silently widened account scope.
3. Use native HA flow cancellation/expiry and independent account sessions. Survive HA/host restarts, and prevent one account from blocking another.
4. Add account-specific recovery/health diagnostics with allowlisted status codes. Test stale/empty reports, rotating-key windows, concurrency and shutdown.
5. Build the actual release package, repeat install/upgrade/restart/removal, validate privacy/source/license inventory, and obtain Claude's full privacy/security/bug review before publication. Real multi-account and unattended outage recovery remain separate acceptance gates.

## Dependency audit, October 11, 2026

The current local onboarding worker runs an independently modified HAtag binary. The upstream [HAtag repository](https://github.com/johncattrall/hatag) and original [export-findmy repository](https://github.com/thisiscam/export-findmy) expose no declared repository license; their GitHub repository metadata reports `license: null`. This does not establish redistribution permission. GitHub's [licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository) explains the distinction between a public fork and licensed redistribution.

HAtag pins [rustpush at 48afd8a3](https://github.com/johncattrall/rustpush/blob/48afd8a3a7319a2efd10e1f708e525deb2886013/LICENSE), whose license is SSPL v1. The inspected exception grants special rights to OpenBubbles; it does not name HomeCircle. No legal compatibility or blanket redistribution approval is claimed here. Obtain applicable permissions or replace the exporter, and keep third-party license obligations explicit.

No upstream Rust code, helper binary, Apple library, account data, vault or screenshot is added to this branch. Existing private source/test checkpoints remain available for a licensed migration. The replacement route below removes that exporter from the public candidate.

## Replacement decision and completed offline work

The maintainer confirmed no redistribution permission and selected replacement. The next-beta candidate now uses an isolated namespace for the MIT-licensed [parawanderer FindMy.py fork](https://github.com/parawanderer/FindMy.py/tree/7969003ca785658369b650f75d9e7ca519566bf6), pinned to the commit used by [OpenTagViewer's exporter](https://github.com/parawanderer/OpenTagViewer/blob/39f4a23993814ccd230139c464f300b9073bfa4f/python/pyproject.toml). Its license is included. No HAtag/export-findmy/rustpush code or binary is copied.

The pinned SDK passed 873 tests without an Apple account; its timeout tests use only a loopback HTTP server. The rest is synthetic protocol/crypto/state evidence, not real-account acceptance. An initial run blocked those loopback sockets; a dedicated run permitting only loopback passed. Vendoring includes source/protocol definitions and four publicly inspectable Apple escrow root certificates with exact hash checks in the privacy guard. Python imports are rebased to avoid replacing the original prototype's SDK.

A HomeCircle-owned transient onboarding adapter now exercises login/2FA, device-name selection, bounded passcode recovery, item discovery, explicit selected-only payloads, password removal and close cleanup. It calls the replacement's read-only recovery method, not trust enrollment, deletion or rename. This removes the Rust exporter's redistribution dependency. Native options integration, encrypted persistence/runtime polling, guarded legacy migration, item presentation and release packaging are implemented and covered by the checks below. These offline checks did not access an account or change the installed provider.

## Implemented candidate boundaries

- Native HA account onboarding provides explicit recovery consent, user-selected verification method, trusted-device names and serial suffixes, password-style fields, selected-item multi-select, item types and final confirmation.
- A 15-minute expiry and flow-manager removal cancel work and close transient sessions. Passwords are removed before export; codes and passcodes are never written to config entries or the session vault. SDK and ADI dependency logs are disabled because upstream debug messages include protected tokens.
- Reconnection retains the local Apple client identity, clears prior login tokens, checks the authenticated Apple account identifier before Keychain recovery, retains migrated item IDs by matching accessory keys, and preserves the actual last report. Reconnect uses existing selected keys and does not repeat passcode recovery; discovering additional items is a separate action. Only the new explicit selection is saved.
- Accounts poll independently, with at most two simultaneous account polls. A session expiry pauses that account and creates a Home Assistant issue directing the user to reconnect; other accounts continue. Reconnection pauses its existing poll before replacing its vault. Executor writes finish before cancellation can allow another writer.
- Items have their own category and do not contribute to household presence counts or household home focus. Item custom names and photos are retained across selection/reload. Disconnecting removes item cards and deletes the HomeCircle account store; tracker history remains. Integration removal deletes its native account stores, and startup removes orphaned native stores without touching prototype accounts.
- The optional prototype migration reads only the explicitly chosen account after consent. It validates SDK restoration, creates a separate encrypted copy while preserving the original prototype vault, keeps tracker entity IDs and history, disables its old entry, and changes entity platform ownership through HA's registry API. A pending registry metadata ledger permits rollback on startup if saving the new account was interrupted, or finishes registry migration if options were persisted first. Undo migration restores the existing prototype and removes the native session copy. The ledger contains registry identities, no Apple credentials or accessory keys. Busy prototype onboarding blocks migration.
- Release packaging includes the MIT SDK source, protobuf definitions, upstream license/provenance and public Apple escrow root certificates. It contains no HAtag/export-findmy Rust code or binary, no research checkout, and no real session or item keys.

## Release gates still open

This is a development candidate on `codex/findmy-beta`, not a published beta. Native HA tests use synthetic responses. Clean HA Core installation, real native Apple sign-in/discovery, session reuse after restart, a movement report from the replacement, and real prototype migration/Undo remain unverified. Linux identity-engine operation and an owner-approved read-only report query for two existing AirTags passed in the HA add-on environment. Both tags returned decoded reports; one was newer than its saved report. The original vault and active backend were unchanged. The installed beta18 and private prototype remain in place. Claude’s final read-only review found no code-level release blockers. Publication still requires the live acceptance gates in [the candidate validation record](BETA19-CANDIDATE-VALIDATION.md).

## Independent review remediation

Claude’s first review found reconnect/reload, household-flow continuation, session cleanup/minimization, dependency and crash-persistence blockers. The candidate now increments a session revision so HA reloads after committing options on reconnection; stages selected keys in memory until household validation completes; closes recovery state immediately; deletes native stores on disconnect/removal and prunes native orphans; stores the account email, stable report-service account identifier and token, plus client/identity provisioning state; declares anisette/SRP/BeautifulSoup directly; and uses an untouched prototype vault with a distinct native copy and an Undo path. The protobuf range >=6.32.0,<8.0.0 accepts both the older validator’s runtime and live Core 2026.10.1’s 7.36.0. Both runtime versions passed the SDK suite; the HomeCircle suite also passes with 7.36.0. Independent re-review and synthetic regression checks confirmed these fixes; live acceptance remains required before publication.

## HA framework and Linux checks

The anonymous identity-engine probe passed on the HA machine's Linux aarch64 Terminal & SSH environment, using Python 3.14 and protobuf's musllinux aarch64 wheel. It instantiated no Apple account and accessed no saved session, Keychain record or item data. This confirms engine operation in that environment, not a clean install in HA Core.

The actual HA 2026.9.4 entity registry refuses migration while an entity remains in `entity_sources`; entity removal clears that source. A restored unavailable state alone does not prevent migration. The regression test loads a native tracker, completes Undo through HA's real options manager and HomeCircle unload/reload, and verifies its original registry identity. Only enabling the absent private prototype is mocked; live prototype reactivation still needs acceptance.

Recovery and orphan cleanup failures now create repairs without preventing household/Life360 loading. Destructive account actions are hidden during unfinished household setup. The public identity-library cache initializes under a thread lock and writes atomically only when missing. Session revision changes use HA's post-commit reload ordering. Staged selected sessions expire after 15 minutes. Apple account aliases are checked using the authenticated stable identifier before protected recovery.

## Maintainer scope decision: no existing public users

The maintainer confirmed there are no existing users to migrate. Public beta onboarding will therefore omit prototype migration/Undo, and live migration is no longer a publication gate. The current local prototype and its protected vault remain a temporary development fallback while native authentication/tracking are validated. Remove migration routes and obsolete helper code before publication; do not delete protected fallback data without explicit approval. No native migration has been performed.
