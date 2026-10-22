# Apple Find My setup

Apple Find My is an **experimental beta 19 feature**. HA-only sign-in, fresh item discovery, passwordless restart and automatic report delivery passed on the tested HA OS Raspberry Pi. See [packaging validation](FINDMY-BETA19-PACKAGING-VALIDATION.md) for the tested scope and release checks.

HomeCircle connects to Apple from Home Assistant. No physical Mac, terminal, separate helper, or manual YAML is required. Apple can change these undocumented services, and access may be unavailable even when the Apple app works.

## Add an account and select items

1. In Home Assistant, open **Settings → Devices & services → HomeCircle → Configure → Apple Find My accounts → Add an Apple account**.
2. Set an account label and review **Allow this Apple sign-in and Find My key recovery**. Before showing the password form, HomeCircle prepares its local identity runtime, downloading and verifying public Apple software when needed. Each connection has its own client identity. See [runtime provenance](../custom_components/homecircle/_findmy_runtime/PROVENANCE.md).
3. Enter your Apple account email and password in **Sign in to Apple**. If Apple requests verification, choose a method and enter the newest code in Home Assistant. A verification code is different from a device unlock passcode.
4. For fresh discovery, **Choose a trusted device** whose unlock passcode you know. If **Review recovery after setup or restore** appears, review its uncertainty before explicitly acknowledging that account; see the [recovery safeguard](#recovery-safeguard-in-the-unreleased-stable-candidate). Then enter the passcode in **Recover Find My item keys**. Recovery reads key material needed to discover items without joining a new Keychain trust peer. The unreleased stable candidate allows up to three refused or uncertain proof submissions per authenticated account, retained across setup restarts, and never retries a passcode automatically. Local preparation or sign-in failures are classified separately.
5. In **Choose Find My items**, explicitly select the items to expose to Home Assistant. On **Set item types**, choose **AirTag**, **AirPods**, or **Other Find My item** for each selection. Apple may omit the type; the chosen type is your classification. Current selections are prechecked, and confirmation lists items that will stop polling.
6. Review **Save selected Find My items** and confirm **Save this account and these selected items**. During initial household setup, finish saving within 15 minutes; expiry discards the unfinished edit.

Each selected item gets its own ordinary HA `device_tracker` and appears in HomeCircle's item category. Items do not count as household people. Unselected item keys are discarded when setup closes.

## Manage an existing account

Open **Apple Find My accounts → Manage an Apple account**, then choose the account:

| Action | What it does |
| --- | --- |
| **Reconnect existing items** | Signs in to the same Apple account and reuses its saved item keys. It does not ask for a device unlock passcode. |
| **Discover or change selected items** | Runs Apple sign-in and full key recovery to discover items, then asks you to select which ones to keep. A trusted device's unlock passcode is needed. |
| **Manage saved items without signing in** | Changes the selection among keys already saved locally. It does not discover new items or renew an expired Apple session. Normal report polling continues or resumes after saving. |

Reconnecting keeps the existing connection until the replacement is confirmed. **Disconnect this account** removes its HomeCircle session and item keys; existing HA history and backups remain under your control. Disconnect also deletes this connection’s local identity ledger, but retains the separate recovery safeguard.

## Read location reports honestly

Normal polling checks Apple about every five minutes. It cannot force an AirTag to produce a new location. Reports can arrive later than in the Apple app, and a successful poll can return no newer usable report. HomeCircle keeps the last usable location with its original source time in that case.

Use the source report time and estimated accuracy when judging a position. An HA update is not a new location fix. Reports do not promise real-time or exact tracking.

## Storage and troubleshooting

The local encrypted account vault retains your account identifier/email, selected item keys, client identity and provisioning state, and the report-service token. Its decryption key is stored alongside it, so protect HA storage and backups. Passwords, verification codes and device unlock passcodes stay transient. Authorized household viewers can see selected item locations; HA Recorder retains tracker history according to your settings. See [privacy and security](PRIVACY.md#apple-find-my-connection).

For failures, use the UI message and sanitized HA diagnostics, which expose allowlisted status and aggregate counts. A service refusal alone does not establish an incorrect password or waiting period. Keep credentials, vaults, raw replies and location screenshots out of support reports. If offered, **Retry Find My item discovery** reuses the recovered keys in memory without asking for the passcode again.

## Recovery safeguard in the unreleased stable candidate

Three refused or uncertain submissions open **Review the recovery safeguard**.
The counts describe this installation's observations, not Apple's remaining
allowance. A setup restart, reconnect or HA restart does not clear them. An
administrator can explicitly acknowledge and clear the local safeguard after
reviewing the intended trusted device and passcode. This neither resets Apple's
allowance nor submits another passcode. Active recovery must finish before reset.

The candidate also opens **Review recovery after setup or restore** when local
continuity cannot be verified. The first use and upgrade from an older safeguard
require this explicit review. Normal restarts retain a separate, account-bound
continuity witness; ordinary Home Assistant configuration backups exclude it.
Restoring a backup therefore blocks new device-passcode submissions even when
its saved count is below three. Removing cache files or copying only an older
ledger has the same safe result. Saved item tracking can continue. Acknowledging
one account clears only its local unresolved counts and establishes its current
continuity; it never signs in, submits a passcode or acknowledges other accounts.
The counts shown after restore may omit later submissions, and HomeCircle cannot
reconstruct them without an independently retained newer record.

This protection applies to backups containing the fixed candidate. A restore of
an older package can replace that code: reinstall the fixed candidate before
starting recovery. Whole-filesystem or VM snapshots that restore both ledger and
continuity witness are outside this ordinary-backup protection. No local file
can establish an external, rollback-proof counter.

A missing password or another required factor ends the attempt with a request to
sign in again. A transport failure after potential proof dispatch stays uncertain.
A verified exchange followed by a resumable material/key-download failure offers
**Finish recovering item keys**, using the same account and recovery record without
another proof. Once item keys are recovered, **Retry Find My item discovery** also
reuses them. Non-resumable material failures end the setup rather than presenting
another passcode form. These outcomes do not establish that a passcode was wrong.

Reselecting a previously omitted item preserves its proven tracker identity and
saved display settings when the encrypted identity ledger is still available.
Unselected tracking keys are absent from the active vault. No identity is inferred
from matching names; if proof is unavailable, HomeCircle cannot promise continuity.

## Historical manual-copy and package rollback — October 20–21, 2026

This section records the earlier pre-fix disposable trials. Their manual newest-
safeguard preservation requirement belongs to that historical procedure. The
[fixed-candidate checks below](#restore-checks-for-the-fixed-candidate) describe
the new continuity behavior. The [ordinary restore record](RELEASE-1.0-ORDINARY-RESTORE.md)
records its passed synthetic partial-restore validation and exact limits.

The manual-copy trials stopped Home Assistant Core and took a consistent,
protected copy of the package and Home Assistant storage. The account vault and
its adjacent encryption key stayed together with matching configuration entries,
entity registry, settings, history and uploaded pictures. Copying only the vault
or only the package did not provide a complete restoration plan. Live Supervisor
backups instead ran with Core and Recorder active for their normal backup hooks.

Published beta 19 did not preserve the newer encrypted identity ledger when it
saved an account. Package-only rollback after using the candidate could lose
identity evidence for omitted items. The historical rollback procedure restored
the matching package and storage together, with Core stopped, before starting
the older version. Previously disconnected connections and older reports could
return with that backup.

For those pre-fix trials, the procedure preserved the **newest** separate
`.storage/homecircle_findmy/recovery_guard` outside the older account backup.
Restoring an older safeguard could forget submissions made after the backup;
manual newest-ledger repair supplied that earlier boundary. No storage restore
reset Apple's server-side allowance. Passcode submissions were never used to
test a backup, and uncertain outcomes remained subject to explicit review.

These results were scoped disposable rehearsals. Candidate HACS delivery,
production, physical-display and owner-account recovery acceptance were separate.

## Historical prepared Supervisor protocol — October 20, 2026

Supervisor automatically started Core after restoring Home Assistant data. The
earlier pre-fix candidate had no stopped interval in which a newest safeguard
could be repaired before an enabled connection started. The tested partial-
backup fixture therefore used this deliberately prepared ordering:

1. It disabled the HomeCircle entry, waited for unload, and verified the disabled
   state and pending registry/resource changes in storage. Core and Recorder
   remained running for Supervisor's normal backup hooks.
2. It created the Home Assistant backup with its database included and retained
   the newest safeguard separately, outside the storage being replaced.
3. It restored that prepared backup and verified the automatically started Core
   still had HomeCircle disabled.
4. It stopped Core, restored and verified the separately retained newest
   safeguard, then started Core and verified the entry remained disabled before
   re-enabling HomeCircle.
5. It checked selections, identities, dashboard, current card bytes and the real
   guard status. A previously blocked guard remained blocked without submitting
   a passcode to test it.

Disabling HomeCircle removed its owned card resource; re-enabling created the
current resource again, possibly with a different ID. Unrelated resources stayed
intact. This prepared partial scope did not establish ordinary enabled, full-
system/add-on or owner-account restore safety, and supplied no automatic rollback
detection.

The [October 20 native HAOS rehearsal](LINUX-HAOS-VALIDATION.md#october-20-guarded-supervisor-backup-and-recorder-restore)
passed that historical protocol with synthetic data, including Recorder history
rollback, recording across restart and a guard blocked at three. No owner account
or production configuration was used.

### Historical enabled-backup investigations — October 20–21, 2026

The [first enabled-entry experiment](ENABLED-RESTORE-VALIDATION.md) completed a
real Supervisor partial backup/restore and observed the older guard at two on
automatic startup after a separately observed newer blocked guard at three.
Its later operational check timed out; manual repair was not reached. The
prepared disabled-entry ordering was the established boundary at that checkpoint.
Default online dependency reinstallation and full-system recovery were outside
that prepared-dependency offline result.

The [prepared enabled-entry followup](ENABLED-RESTORE-PREPARED.md) subsequently
completed settings, identity and Recorder restoration, followed by manual newest-
guard repair and restart. It again observed the old guard returning before repair.
The [exact development-preview investigation](RELEASE-1.0-HAOS-RESTORE.md) repeated
six managed phases with the 113-file package and reproduced the same rollback.
Those operational/manual-repair passes retained a negative automatic-safety
disposition. Their records are historical evidence for the defect addressed by
the [continuity-witness correction](RELEASE-1.0-ROLLBACK-PROTECTION.md).

## Restore checks for the fixed candidate

The [ordinary restore record](RELEASE-1.0-ORDINARY-RESTORE.md) validates this
fixed candidate in an isolated, synthetic same-host Home Assistant partial
restore on amd64 HAOS. All four phases passed with the unchanged product,
normal requirements and default Supervisor conditions. The first automatic
restored startup and its restart required recovery review and refused the real
guarded attempt before its body, without a manual guard import or acknowledgment.
[Retained public evidence](https://github.com/jmhjr/HomeCircle/blob/8f28d5da33b7094355e84d5c8a23ee78463cecf3/native-ordinary-rollback-evidence/INDEX.md),
including its portable replay, binds that result to the exact candidate.

The record also retains four failed fixture trials and their separate corrections.
R5 run 39721983991 supplies the accepted native result; package suites and the
earlier prepared/manual procedures keep their original, narrower scopes. Full
Home Assistant Person associations, HomeCircle activity history and other backup
variants remain separate acceptance cases.

1. **Verify the loaded fixed candidate.** Use the identified candidate/package
   record, restart Core after installation, and verify the loaded integration
   and served card. The shared beta version label alone does not identify this
   development package.
2. **Create a consistent normal backup.** Use Home Assistant's normal backup
   interface with Core and Recorder running, including the configuration and
   database for the intended partial-restore scope. Protect the account key and
   vault together with matching entries, registry, settings, history and pictures.
   Ordinary Home Assistant backups exclude the continuity witness under `.cache`;
   do not add a manual witness copy to that restore procedure.
3. **Check the code again after restore, before recovery.** An older archive can
   restore an older integration package as well as older data. If it contains
   pre-fix code, reinstall the fixed candidate and restart Core before starting
   any device-passcode recovery. A package download alone does not prove the fix
   is loaded.
4. **Inspect the restored tracking data first.** Check the selected trackers,
   identities, settings, pictures, dashboard and source report ages. Saved item
   tracking can continue without a fresh key-recovery exchange. No passcode
   submission is needed to test whether the backup restored correctly.
5. **Expect explicit recovery review when continuity was removed.** If new key
   discovery is actually needed, a restored account without its witness must
   show **Review recovery after setup or restore** before device-passcode entry,
   even when the displayed local count is below three. Do not automatically
   acknowledge the dialog, clear cache/ledger files or submit a passcode merely
   to test recovery. If that expected review is absent, or the loaded code is
   uncertain, stop the recovery flow and inspect diagnostics first.
6. **Acknowledge only after reviewing the real uncertainty.** The displayed counts
   may omit submissions made after the backup. Review the intended account,
   trusted device and any unresolved outcome before deliberately acknowledging
   that account. Acknowledgment resets only its local unresolved counts and
   establishes only its continuity witness. It does not sign in, submit a
   passcode, reset Apple's allowance or acknowledge another account.

A normal restart keeps a matching witness. Cache eviction safely requests review
again. HomeCircle cannot reconstruct missing later submissions from an older
backup. A full VM or complete configuration snapshot can restore both an older
ledger and its matching witness; detecting that joint rollback requires an
independent external monotonic anchor. This protection does not cover that
snapshot case or prove live provider authentication, session renewal, full-system
or encrypted/cloud restore, HACS delivery, or stable release acceptance.
