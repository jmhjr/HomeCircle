# Apple Find My setup

Apple Find My is an **experimental beta 19 feature**. HA-only sign-in, fresh item discovery, passwordless restart and automatic report delivery passed on the tested HA OS Raspberry Pi. See [packaging validation](FINDMY-BETA19-PACKAGING-VALIDATION.md) for the tested scope and release checks.

HomeCircle connects to Apple from Home Assistant. No physical Mac, terminal, separate helper, or manual YAML is required. Apple can change these undocumented services, and access may be unavailable even when the Apple app works.

## Add an account and select items

1. In Home Assistant, open **Settings → Devices & services → HomeCircle → Configure → Apple Find My accounts → Add an Apple account**.
2. Set an account label and review **Allow this Apple sign-in and Find My key recovery**. Before showing the password form, HomeCircle prepares its local identity runtime, downloading and verifying public Apple software when needed. Each connection has its own client identity. See [runtime provenance](../custom_components/homecircle/_findmy_runtime/PROVENANCE.md).
3. Enter your Apple account email and password in **Sign in to Apple**. If Apple requests verification, choose a method and enter the newest code in Home Assistant. A verification code is different from a device unlock passcode.
4. For fresh discovery, **Choose a trusted device** whose unlock passcode you know, then enter it in **Recover Find My item keys**. Recovery reads key material needed to discover items without joining a new Keychain trust peer. Setup allows three recovery attempts and does not retry a passcode automatically.
5. In **Choose Find My items**, explicitly select the items to expose to Home Assistant. On **Set item types**, choose **AirTag**, **AirPods**, or **Other Find My item** for each selection. Apple may omit the type; the chosen type is your classification.
6. Review **Save selected Find My items** and confirm **Save this account and these selected items**. During initial household setup, finish saving within 15 minutes; expiry discards the unfinished edit.

Each selected item gets its own ordinary HA `device_tracker` and appears in HomeCircle's item category. Items do not count as household people. Unselected item keys are discarded when setup closes.

## Manage an existing account

Open **Apple Find My accounts → Manage an Apple account**, then choose the account:

| Action | What it does |
| --- | --- |
| **Reconnect existing items** | Signs in to the same Apple account and reuses its saved item keys. It does not ask for a device unlock passcode. |
| **Discover or change selected items** | Runs Apple sign-in and full key recovery to discover items, then asks you to select which ones to keep. A trusted device's unlock passcode is needed. |
| **Manage saved items without signing in** | Changes the selection among keys already saved locally. It does not discover new items or renew an expired Apple session. Normal report polling continues or resumes after saving. |

Reconnecting keeps the existing connection until the replacement is confirmed. **Disconnect this account** removes its HomeCircle session and item keys; existing HA history and backups remain under your control.

## Read location reports honestly

Normal polling checks Apple about every five minutes. It cannot force an AirTag to produce a new location. Reports can arrive later than in the Apple app, and a successful poll can return no newer usable report. HomeCircle keeps the last usable location with its original source time in that case.

Use the source report time and estimated accuracy when judging a position. An HA update is not a new location fix. Reports do not promise real-time or exact tracking.

## Storage and troubleshooting

The local encrypted account vault retains your account identifier/email, selected item keys, client identity and provisioning state, and the report-service token. Its decryption key is stored alongside it, so protect HA storage and backups. Passwords, verification codes and device unlock passcodes stay transient. Authorized household viewers can see selected item locations; HA Recorder retains tracker history according to your settings. See [privacy and security](PRIVACY.md#apple-find-my-connection).

For failures, use the UI message and sanitized HA diagnostics, which expose allowlisted status and aggregate counts. A service refusal alone does not establish an incorrect password or waiting period. Keep credentials, vaults, raw replies and location screenshots out of support reports. If offered, **Retry Find My item discovery** reuses the recovered keys in memory without asking for the passcode again.
