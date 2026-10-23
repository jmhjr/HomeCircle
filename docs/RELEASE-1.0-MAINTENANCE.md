# Upgrade, restore, rollback and remove HomeCircle

These are candidate procedures for the proposed HAOS first-release scope. They do not approve a final RC or make an untested restore variant supported. Keep the [support proposal](RELEASE-1.0-SUPPORT-PROPOSAL.md) and your Home Assistant backup/recovery instructions available before changing the installation.

## Before an upgrade

Record your HomeCircle and HA versions and the release you intend to install. Back up Home Assistant through its normal backup interface, including configuration and Recorder/history when appropriate. Protect the backup as account and location data and retain a copy outside the machine being changed. Do not post it for support.

The proposed supported upgrade baseline is unmodified published beta 20. Earlier betas, manual source edits and locally patched development packages need a migration disposition. The private real-account installation-copy rehearsal used a particular development baseline; it does not make every beta-to-release path equivalent. A matching version label alone is insufficient for patched packages.

Download the exact named RC/release through HACS, then restart Home Assistant. Reopen HomeCircle and check the displayed version, household, selected entity identities, homes, pictures and source-report ages. Confirm that the existing providers and dashboard work before changing credentials or selections. HACS download completion alone does not prove the new code is loaded; use a maintainer's exact artifact/hash check if the installation is uncertain.

If only the browser looks stale, refresh it after HA has restarted. Do not remove/re-add a provider or submit another passcode to repair a cached card. Keep the pre-upgrade backup until the intended acceptance checks have passed.

## Qualified ordinary restore boundary

The accepted fixed-candidate trials cover same-host HAOS Supervisor partial backup/restore of Home Assistant configuration plus Recorder database, with the integration enabled, ordinary requirements and default Supervisor restore conditions. Those archives were uncompressed and unprotected. The first automatic restored startup and a later restart preserved the measured selections, Person associations, activity/Recorder cohorts and automatic guard refusal. The proof was synthetic; the private installation-copy upgrade is separate evidence.

A different backup format or destination is a different qualification case. Compressed/encrypted, cloud, full-system/add-on and fresh-machine variants remain unqualified for this first-release record. Do not turn off encryption just to match a test. Keep using appropriate HA backup protection; seek a recovery plan for a variant outside the stated scope. No backup can undo provider-side actions or reset Apple's retry allowance.

## After restoring a backup

1. Restore through Home Assistant's supported mechanism for that backup type. Keep configuration, registry, account storage, history and pictures together. Do not restore individual vault/guard files from different dates or manually copy the cache witness into the restore.
2. Verify the HomeCircle code/version after restore and restart. An older backup can restore older vulnerable code as well as older data. Install the fixed named candidate/release and restart before starting any device-passcode recovery.
3. Inspect the household first: explicit tracker selections and Person links, homes, pictures, dashboard, history and genuine source report age. Older reports and selections may return with the backup. Testing a restore requires no new passcode submission.
4. Saved Find My report polling can continue without a new key-recovery exchange. If fresh discovery is actually needed and continuity is missing, expect **Review recovery after setup or restore** before device-passcode entry. First use, upgrade from an old safeguard or cache cleanup can also produce this screen. Normal restarts preserve matching continuity and the existing counts.
5. Read the uncertainty before acknowledging. Restored local counts may omit later refused/uncertain submissions, and HomeCircle cannot reconstruct them. Review the actual account, trusted device and any unresolved outcome. Acknowledge only deliberately for that account; this clears its local unresolved safeguard and establishes local continuity, not Apple's allowance. It does not sign in or submit a passcode.
6. If the expected review is absent, the loaded code is uncertain or a warning/error appears, close the recovery flow and inspect sanitized diagnostics before proceeding. Do not clear files, reconnect repeatedly or enter a passcode merely to test the safeguard.

The separate recovery ledger and witness protect this ordinary configuration-restore boundary. A complete filesystem/VM snapshot can restore both an older ledger and its matching witness, so it cannot establish an external rollback-proof counter. An old package can also remove the fix. Keep these limits with the backup rather than treating a successful restore as permission to retry recovery.

## Roll back cautiously

Do not roll back only the integration package while leaving newer account/storage formats in place. Older packages may discard identity evidence or restore the original recovery-guard weakness. Before a rollback, keep a new protected backup and obtain a compatible package-and-data procedure for that exact baseline. Do not advertise a return to old beta code as a supported Find My recovery path.

If restoring an older complete Home Assistant backup is necessary, apply the code check and recovery-review procedure above before any new discovery. Retain source/entity identities and inspect existing history before saving changed selections. Never delete the safeguard or acknowledge it simply to make rollback appear successful.

## Pause, resume and access-denial controls

The current source candidate implements these administrator controls. Their
affected native checks and final RC/HACS qualification remain pending in the
[active tracker](RELEASE-1.0-FIRST-RELEASE-TRACKER.md); this is not a claim that
an older published beta has the controls.

1. Open HomeCircle Options and choose **Manage direct connections**.
2. Read the connection status. Choose **Saved connection**, then **Action →
   Pause** or **Resume**. Pause saves the stop independently of a household edit
   and normally remains in effect after restart. Accounts, tracker identities,
   selections, pictures and history are kept.
3. Resume deliberately allows requests again for the chosen provider, including
   accounts paused after denial. Review terms, account access and diagnostics
   first. Resume does not acknowledge recovery, reset Find My safeguards or
   submit a device passcode. Do not use it to repeatedly work around denial.
4. If **Direct requests are blocked now, but the setting could not be saved.
   Check Home Assistant storage before restarting.** appears, do not treat the
   operation as saved. Current-process requests are blocked; fix storage before
   relying on the state across a restart. Total disk-write failure cannot promise
   persistence after process loss.

Apple denial stops only the denied account; healthy Apple accounts can continue.
Life360 denial stops that provider. The controls cover HomeCircle polling and its
manual/auxiliary direct-provider calls. Another Life360 or HA integration and
optional map/city features keep their own controls. There is no hosted remote
kill switch. Disconnect below is the separate action for removing an account.

## Disconnect or remove

For Life360, replace any selected HomeCircle-owned sources first and remove exact HA Person links to those trackers. Then turn off **Connect a Life360 account directly** in Options. The flow prevents disconnect while selected/linked owned trackers remain in use.

For Find My, use **Apple Find My accounts → Manage an Apple account → Disconnect this account** and confirm. Polling/cards for that connection stop; active session, selected keys and its identity ledger are deleted. Existing Recorder history and backups remain. The separate recovery safeguard deliberately remains across Disconnect and integration removal.

For normal uninstall, back up first. Remove the HomeCircle integration entry in **Settings → Devices & services**, then uninstall its files in HACS and restart HA. Removing files first prevents the package's entry-cleanup code from running. Entry removal deletes its local activity, city-lookup and request-limit stores and owned account storage where safe; a cleanup problem produces a repair issue rather than silently overriding unsafe storage.

Only an untouched dashboard created by HomeCircle is removed automatically; user-edited or independently created dashboards/resources are preserved. HA People, their tracker links, zones, uploaded images, external tracker integrations, Recorder history and old backups are managed separately and can remain. Clearing a picture reference does not delete HA's uploaded image. Review these retained assets in HA if you intend to delete them. Reinstalling needs household setup again and does not erase retained recovery counts.
