# Install and set up the first-release candidate

These instructions describe the proposed first-release UI path. HomeCircle 1.0 is not yet published or approved. Use the exact RC or release named by the maintainer; the currently published beta remains experimental. A branch checkout or GitHub source-code archive is not the installable release ZIP. Read the [support proposal](RELEASE-1.0-SUPPORT-PROPOSAL.md) before choosing a system.

## Install through HACS

1. Make a Home Assistant backup and keep it outside the installation you are changing. Review [upgrade and recovery](RELEASE-1.0-MAINTENANCE.md).
2. In HACS, add `https://github.com/jmhjr/HomeCircle` as a custom repository of type **Integration** if it is not already present.
3. Open HomeCircle and choose Download/Redownload. Select the exact named release; an RC may require prereleases to be enabled. Confirm the version before downloading. Do not substitute the repository branch because a release is not yet offered.
4. Restart Home Assistant. Downloading files alone does not activate them.
5. Open **Settings → Devices & services → Add integration → HomeCircle**.

The named `homecircle.zip` includes the card. In the supported storage-mode path, no separate card download, resource YAML or card YAML is required. Adding the integration creates the household; installing the HACS files alone does not.

## Prepare people, trackers and places

An existing source must already work in Home Assistant. In **Settings → Devices & services → Entities**, check that its tracker is enabled and has the expected state. Presence-only/router trackers may have no map position. For an iPhone, connect the Companion app to the intended HA server and enable its location source. HomeCircle does not create remote access or change iOS background-reporting policy.

For each new person or pet, select or create a Home Assistant Person. A pet still needs its own working tracker integration; choosing Pet does not create one. HomeCircle can create a missing Person during setup, and that Person remains in HA if you cancel the flow.

Choose **Primary family home** and any **Places shown while Away**. Use **Other homes** for residences that count as Home for a particular member. An Away place such as school or work labels that location but does not make it Home. Zones created in setup become real HA zones immediately and can remain after cancellation.

On **Assign a tracker**, choose the tracker that actually belongs to that Person. Compare entity IDs when names repeat. A tracker already assigned to another Person must be reassigned there first. Start with the intended source and add other sources deliberately; HomeCircle does not infer ownership from names.

Under **Person and tracker settings**, choose member type, homes and optional sensors. **Freshest reliable GPS** compares only selected sources; **Follow HA Person** uses the Person-based selection policy. HA's active Person source can differ from HomeCircle's selected map source. Read the displayed source rather than assuming they are identical.

Optional battery, charging, motion and report-time mappings select existing HA sensors. A report-time sensor must describe that exact location source. Leave unknown values unmapped: HA state-change/update time is not a GPS fix time. Finish **Review and save household** and choose **Save household**.

## Choose direct connections deliberately

Apple Find My and Life360 are optional unofficial connections. Use only accounts
and location data you are lawfully entitled to access. HomeCircle does not claim
provider affiliation, endorsement or permission, and a successful sign-in is not
a guarantee of continued access or current reports. Existing HA trackers work
without a HomeCircle provider account. Read the
[local storage and external-request disclosures](RELEASE-1.0-PRIVACY-SUPPORT.md)
and [distribution decision record](RELEASE-1.0-NO-OUTREACH-DECISION.md) before
using a direct connection. Do not rely on HomeCircle for emergency response.

The current source candidate has administrator **Manage direct connections** in
Options. Choose **Connection** and **Action → Pause** or **Resume**.
Pause keeps saved accounts, identities, selections and history and normally
survives restart. Resume deliberately enables requests for that provider again,
including accounts stopped after denial; it does not reset Find My recovery
safeguards. If a storage error appears, the pause is not reported as saved.
See [pause/resume and recovery](RELEASE-1.0-MAINTENANCE.md). Affected runtime results must name the exact source in the draft PR. Final RC/HACS qualification remains separate in the [active tracker](RELEASE-1.0-FIRST-RELEASE-TRACKER.md); this is not a result for the published beta.

## Connect Life360, if wanted

Existing Life360 trackers from another HA integration remain usable without a direct HomeCircle account. Avoid selecting duplicate trackers for the same member merely because two connections expose them.

To connect directly, enable **Connect a Life360 account directly** during household setup. In **Connect Life360**, choose email/password or access token. For a token, enter only its value; HomeCircle supplies Bearer authorization. Enter secrets only in Home Assistant, never in chat or a support report. HomeCircle does not provide a token-retrieval service. Some accounts cannot use password sign-in.

Member discovery can take several minutes. When the trackers appear, reopen HomeCircle Options, choose **Add a tracker**, select/create its Person and choose the correct tracker. The setup reminder stays until a tracker from that account is explicitly selected. No automatic name match completes that step.

Use **Replace saved Life360 sign-in** or HA's **Reconnect Life360** repair to replace credentials for the same account. A different verified account is rejected. Older entries may require same-account confirmation when the old sign-in cannot be checked. To switch accounts, follow the documented removal/new-household path rather than carrying old selections across accounts. See [troubleshooting](RELEASE-1.0-TROUBLESHOOTING.md).

## Connect Apple Find My, if wanted

Open **HomeCircle → Configure → Apple Find My accounts → Add an Apple account**. Read the sign-in/key-recovery disclosure. Runtime preparation happens before the password form and may download required public Apple software; no Mac, terminal or separate helper is required by this path.

Enter Apple credentials and the newest requested verification code only in Home Assistant. A verification code is different from a device unlock passcode. For new discovery, choose a recognized trusted device whose passcode you know. If **Review recovery after setup or restore** appears, read [the recovery procedure](RELEASE-1.0-MAINTENANCE.md) before acknowledging that account. Acknowledgment does not reset Apple's allowance or submit a passcode.

Enter the selected device's unlock passcode once. HomeCircle does not automatically retry it. Stop at a refusal, uncertain outcome or safeguard warning; do not repeatedly start setup to try again. If recovery succeeded but discovery failed, **Retry Find My item discovery** reuses material held in that setup without another passcode. Closing/expiring the flow drops that resumable state.

In **Choose Find My items**, select only the intended items, review their types and confirm **Save this account and these selected items**. Current selections are prechecked; deliberate unchecking stops polling and discards those tracking keys while retaining existing history/display settings. If household review follows, choose **Save household** too. Finish the unfinished household edit within 15 minutes.

Use **Reconnect existing items** to sign in again with saved keys, without a device-passcode recovery. **Manage saved items without signing in** stays local and selects among keys already saved; it cannot discover new items or renew an expired Apple session. The detailed [Find My guide](FINDMY-SETUP.md) retains the exact account/recovery limits.

## Check the dashboard

Open HomeCircle from the HA sidebar. First setup creates a dashboard if an existing HomeCircle card/dashboard is not already present. If a new card or saved tracker is not yet visible, close Options, allow a normal card update, then refresh the browser once. Repeating account recovery is not a card-refresh remedy.

Confirm that each member appears once, has the intended source and has the expected Home/Away state. Tap a member to focus its usable position; tap Everyone to fit included positions. A presence-only member can count without a marker. **Show on map** changes inclusion/presentation, not access permission.

Read **Source location report** separately from **HA state updated**. A good-looking map position can still be an old report. HomeCircle does not make an old Apple or Life360 report newer by polling it. **Since** describes genuine tracker arrival evidence or a saved local observation; after a gap, continuity can be unconfirmed. Unknown evidence remains unknown.

Street tiles are on by default. Choose **Private · no external tiles** in the card editor to avoid external map tiles. City lookup is a separate administrator opt-in and is not disabled by Private map mode. Family location refresh is off by default; an administrator must review and enable **Allow family location refresh** before using that feature. A cloud check or successful request does not guarantee a new phone GPS fix. See [privacy and support](RELEASE-1.0-PRIVACY-SUPPORT.md).
