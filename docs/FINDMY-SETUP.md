# Apple Find My setup

Apple Find My is an **experimental beta 19 feature**. HA-only sign-in, fresh item discovery, passwordless restart and automatic report delivery passed on the tested HA OS Raspberry Pi. See [packaging validation](FINDMY-BETA19-PACKAGING-VALIDATION.md) for the tested scope and release checks.

HomeCircle connects to Apple from Home Assistant. No physical Mac, terminal, separate helper, or manual YAML is required. Apple can change these undocumented services, and access may be unavailable even when the Apple app works.

## Add an account and select items

1. In Home Assistant, open **Settings → Devices & services → HomeCircle → Configure → Apple Find My accounts → Add an Apple account**.
2. Set an account label and review **Allow this Apple sign-in and Find My key recovery**. Before showing the password form, HomeCircle prepares its local identity runtime, downloading and verifying public Apple software when needed. Each connection has its own client identity. See [runtime provenance](../custom_components/homecircle/_findmy_runtime/PROVENANCE.md).
3. Enter your Apple account email and password in **Sign in to Apple**. If Apple requests verification, choose a method and enter the newest code in Home Assistant. A verification code is different from a device unlock passcode.
4. For fresh discovery, **Choose a trusted device** whose unlock passcode you know, then enter it in **Recover Find My item keys**. Recovery reads key material needed to discover items without joining a new Keychain trust peer. The unreleased stable candidate allows up to three refused or uncertain proof submissions per authenticated account, retained across setup restarts, and never retries a passcode automatically. Local preparation or sign-in failures are classified separately.
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

## Upgrade backups and rollback for the unreleased candidate

For a manual package/storage copy before upgrading, stop Home Assistant Core
and take a consistent, protected copy of the integration package and its Home
Assistant storage. Normal live Supervisor backups instead require Core and
Recorder running; use the prepared protocol below for the tested restore ordering.
Keep the account vault
and its adjacent encryption key together with the matching configuration entries,
entity registry, settings, history and uploaded pictures. Copying only the vault
or only the package is not a complete restoration plan.

Published beta 19 does not preserve the newer encrypted identity ledger when it
saves an account. After using this candidate, rolling back only its package can
therefore lose identity evidence for omitted items. Restore the matching package
and storage backup together, with Core stopped, before starting the older version.
Previously disconnected connections and older reports may return with that backup.

Preserve the **newest** separate recovery-safeguard directory when restoring an
older account backup: `.storage/homecircle_findmy/recovery_guard`. Restoring an
older safeguard can forget submissions made after the backup. HomeCircle cannot
detect every manual storage rollback, and restoring storage never resets Apple's
server-side attempt allowance. If the latest safeguard is unavailable or an
exchange's outcome is uncertain, review that uncertainty before another recovery
attempt; do not retry passcodes to test the backup.

These manual-copy steps describe the earlier tested disposable restoration
boundary. The prepared Supervisor protocol below adds a separate native HAOS
partial-restore result; candidate HACS delivery, production and physical-display
acceptance remain separate.

## Prepared Supervisor backups

Supervisor automatically starts Core after restoring Home Assistant data. A
restore command does not leave a stopped interval in which to replace the newest
recovery safeguard. Copying the safeguard back only after an enabled connection
has started is too late to establish that boundary.

The disposable rehearsal uses a deliberately prepared Home Assistant partial
backup, including Recorder's database:

1. Disable the HomeCircle configuration entry through Home Assistant, wait for
   it to unload, and confirm the disabled state and pending registry/resource
   changes have reached storage. Leave Core and Recorder running for Supervisor's normal backup hooks.
2. Create the Home Assistant backup with its database included. Before restoring
   an older backup, retain the newest recovery-safeguard directory separately,
   outside the storage that will be replaced, with its private permissions intact.
3. Restore the prepared backup and verify HomeCircle remains disabled on the
   automatically started Core. Do not re-enable the entry yet.
4. Stop Core, restore and verify the separately retained newest safeguard, then
   start Core and verify the entry is still disabled. Re-enable HomeCircle only
   after this preservation check succeeds.
5. Verify the restored selections, identities, dashboard and current card bytes.
   Confirm the safeguard's actual status before considering another recovery
   exchange. A previously blocked safeguard must remain blocked; do not test a
   backup by submitting passcodes.

Disabling HomeCircle intentionally removes its owned card resource. Re-enabling
creates the current resource again; its ID can change. Unrelated resource IDs
must remain intact.

This is a prepared partial-backup protocol. It does not establish a safe ordering
for an ordinary backup that contains an enabled HomeCircle entry, full-system or
add-on restoration, or owner-account recovery. It adds no automatic rollback
detection and does not reset Apple's server-side allowance. If the newest
safeguard is unavailable or its integrity is uncertain, retain that uncertainty
and review recovery before any further proof submission.

The [October 20 native HAOS rehearsal](LINUX-HAOS-VALIDATION.md#october-20-guarded-supervisor-backup-and-recorder-restore)
passed this prepared protocol with synthetic data, including actual Recorder
history rollback, renewed recording across restart and a guard that stayed
blocked at three. It used no owner account or production configuration.


### Enabled-backup investigation during 1.0 preparation

The [first enabled-entry experiment](ENABLED-RESTORE-VALIDATION.md) completed a
real Supervisor partial backup and restore and observed the exact older guard
at two unresolved exchanges on automatic startup, replacing the separately
observed newer blocked guard at three. Its later operational startup check timed
out; manual repair was not reached. This is observed guard rollback with
incomplete operational qualification, not acceptance of an ordinary enabled
restore. The prepared disabled-entry protocol above remains the established
ordering. A prepared-dependency offline followup does not qualify default
online dependency reinstallation or full-system recovery.


The [prepared enabled-entry followup](ENABLED-RESTORE-PREPARED.md) subsequently
completed settings, identity and Recorder restoration, followed by successful
manual newest-guard repair and restart. It also confirmed the old guard returning
before repair. This does not remove the manual preservation requirement or
broaden the prepared disabled-entry backup protocol above.

The [exact development-preview investigation](RELEASE-1.0-HAOS-RESTORE.md) then
repeated all six managed phases with the newer 113-file package and reproduced
the same guard rollback. Operational restoration and separate manual repair
passed; ordinary and prepared enabled-restore safety remain unaccepted. Keep
using the prepared disabled-entry ordering and preserve the newest safeguard.
