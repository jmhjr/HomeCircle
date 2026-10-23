# Privacy choices and getting support

This first-release guide was updated October 23, 2026 for the maintainer’s no-contact implementation direction. It does not declare 1.0 released or replace the detailed [privacy record](PRIVACY.md), [security reporting policy](SECURITY.md) or [distribution decision record](RELEASE-1.0-NO-OUTREACH-DECISION.md). Newly implemented controls are identified separately from completed native validation.

## Decide who can see the household

HomeCircle reads the HA entities you explicitly select. An authorized household viewer can see selected member/item locations and report details. Treat household access as access to that configured household; hiding a card, excluding a member from Everyone or using kiosk mode is presentation, not a separate privacy boundary. Administrator-only setup/account-health details are not shown to ordinary viewers.

HomeCircle keeps source report time separate from HA observation time. A delayed report can remain visible as an older location; unavailable or unknown data is not proof that a member is Away. Home Assistant Recorder can retain coordinates, states and attributes according to your own Recorder settings. Removing HomeCircle does not erase that history or older backups.

Recent activity retains allowlisted observations, not a route: at most 100 events per member for seven days, with up to 25 freshness events. Current-arrival checkpoints are separate and can outlast that event window. A restart/unavailable gap can preserve a matching observed arrival while marking uninterrupted presence unconfirmed. Saved configuration changes reset the observation identity. No missing arrival time is invented.

## Account storage and backups

Direct Life360 credentials are saved in Home Assistant configuration storage. They are not encrypted by a separate HomeCircle vault. Apple passwords, verification codes and trusted-device passcodes remain transient. The minimized Find My vault saves the account identifier, selected item keys, client identity/provisioning material and report-service token. Its encryption key is stored beside the vault, so anyone with sufficient HA storage/backup access can recover it. Protect both as secrets.

Fresh Find My discovery temporarily recovers broader key material, then retains only explicitly selected tracking keys. A separate identity ledger can preserve keyed commitments and display settings for omitted items; it is not proof that an old name belongs to a newly discovered item. Disconnect deletes the active account store/identity ledger, but old backups and tracker history can remain.

The separate recovery safeguard contains a pseudonymous account hash and local counters, not passwords, item keys or locations. It deliberately survives cancellation, Disconnect and integration removal. Its ordinary-restore witness can be absent after a backup restore, requiring explicit account-specific review. These local counts are not Apple's remaining retry allowance. See [maintenance and recovery](RELEASE-1.0-MAINTENANCE.md).

## Optional connections and local control

Direct Apple Find My and Life360 connections are optional and unofficial. Use
only accounts and data you are lawfully entitled to access. Standard HA trackers
remain available without a direct HomeCircle account. HomeCircle is not
associated with or endorsed by either provider and claims no provider approval
or logo right. A provider can deny or change access; a displayed location can
be old. HomeCircle is not an emergency or safety-monitoring service.

HomeCircle has no hosted account relay, telemetry or support-upload service.
It does not automatically send household data or diagnostics to the maintainer.
Local storage does not mean every enabled feature is network-free: direct
providers and the separate optional services below receive their own requests.

The current source candidate implements **Manage direct connections** in
administrator Options. Choose **Saved connection** and **Action → Pause** or
**Resume**. The displayed connection status gives provider state, paused-account
count and storage availability without identifying accounts. Saved accounts,
identities, selections and history remain, and a normally saved pause survives
restart. A failed save instead reports **Direct requests are blocked now, but the
setting could not be saved. Check Home Assistant storage before restarting.**
Total disk-write failure cannot guarantee persistence after process loss.

Apple denial stops that account while healthy Apple accounts can continue;
Life360 denial stops the provider. Resume deliberately allows the selected
provider again, including accounts paused after denial. It does not acknowledge
recovery, reset its safeguard or send a device passcode. The controls cover
HomeCircle polling and its manual/auxiliary requests. Other integrations, external
tiles and separately enabled city lookup keep their own controls. There is no
hosted remote kill switch.

This describes source implementation, not a completed native result or a feature
proved in the published beta. Affected native checks and final RC/HACS
qualification remain pending in the [active tracker](RELEASE-1.0-FIRST-RELEASE-TRACKER.md).

## External requests are separate choices

| Feature | Information sent and control |
| --- | --- |
| Street map | Default OpenStreetMap tile requests reveal viewed tile area, network address and site origin. They do not send member names or HA credentials. Choose **Private · no external tiles** to stop external map tiles. |
| Satellite/radar | Selecting those layers uses their external imagery/weather services. The requested map area and network metadata can be visible to them. Private map mode prevents external layer requests. |
| City lookup | Off by default; only an administrator enables it. Photon receives selected exact coordinates and server network metadata to fill missing city/street data. Names, entity IDs, report times and credentials are not sent. **Private map mode does not disable this separate server-side option.** |
| Tracker portraits | Allowed Life360 portrait hosts receive image-request network metadata, without the HA page referrer. HA-served portraits stay on the HA origin. See the detailed privacy record for allowed hosts and retained images. |
| Direct providers | An enabled Apple/Life360 connection makes its own account/service requests. These optional unofficial paths can be limited or changed by the provider. |
| Location requests | Individual/automatic/family requests have separate settings, permissions and persisted budgets. Family refresh is off by default, including after upgrade. A cloud report check does not promise a phone GPS fix. |

City results and request budgets are stored locally with bounded retention. Coordinate-cell hashes are not anonymization; cached addresses and backups remain private. Disabling City lookup stops sending/projecting lookups but can leave the bounded local cache until pruning or removal.

Tracker-only picture cropping stays in the browser until Save; the resulting 512-pixel JPG uploads to HA's native image service. HomeCircle stores its image reference. No photo is sent to Photon or a tracker provider. Anyone holding a native HA opaque image URL can view it without login, so do not share those URLs. Clearing a reference, cancelling after upload or removing HomeCircle does not delete the uploaded HA asset. Person pictures remain managed in HA People.

## Support without sharing secrets

For an ordinary bug, use the repository's [issue tracker](https://github.com/jmhjr/HomeCircle/issues). Include the named HomeCircle version/source or package hash when known, HAOS/Core versions, installation method, short expected/actual behavior, time window and safe diagnostic status/counts. Read HomeCircle diagnostics locally on its HA integration page and quote only the fixed statuses, aggregate counts and bounded polling details needed for the issue. No diagnostic file, log or backup upload is required. HomeCircle does not send a support report automatically.

Do not include passwords, tokens, verification codes, device passcodes, vault/key files, backups, raw provider responses/logs, private item/member/account IDs, coordinates, addresses, location screenshots or opaque photo URLs. A private report is not a reason to supply those secrets. Never spend a device-passcode attempt to create a bug reproduction.

For a suspected security vulnerability, use the private reporting route described in [SECURITY.md](SECURITY.md); do not publish exploit details or account material in a public issue. Support does not promise a response time or provider availability. The [troubleshooting guide](RELEASE-1.0-TROUBLESHOOTING.md) identifies safe checks before reconnecting or changing selections.
