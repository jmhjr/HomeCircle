# Troubleshoot HomeCircle safely

Use this guide with the exact named candidate/release and the [support proposal](RELEASE-1.0-SUPPORT-PROPOSAL.md). A provider error identifies a failed stage; it does not by itself prove a wrong password, an exhausted allowance or an upstream API change. Keep secrets and location data out of support reports.

| What you see | Safe next check |
| --- | --- |
| HomeCircle is not listed after HACS download | Restart HA, then use **Settings → Devices & services → Add integration**. HACS installs files; adding the integration creates the household. |
| Card is missing or a new saved tracker is not visible | Finish saving the household, close Options, allow a normal update and refresh the browser once. Check that the integration loaded and its HA tracker exists. Do not repeat provider recovery to refresh a card. |
| Settings cog is missing | Exit kiosk view and use an administrator account, or open the integration's Configure/Options page in HA. Kiosk changes presentation, not permissions. |
| No Person or pet tracker is selectable | Create/select the Person and verify that its actual tracker exists/enabled in HA. Pet type does not install a tracker provider. Entity names do not establish ownership. |
| Two trackers appear for one individual | Check the exact integration/entity IDs. Existing and direct provider connections can expose separate trackers. Keep the intended selection and change Person links deliberately; do not delete a working source before checking its replacement. |
| Home/Away looks different from the Home button's map focus | An additional residence counts as Home for that member, while the Home button focuses the primary family house. Away places label a location but do not count as Home. |
| Member counts but has no marker | A presence-only source can have no usable coordinates. Check the explicitly selected GPS source; do not manufacture coordinates or a current timestamp. |
| Map looks correct but report is stale | Read **Source location report**, not only HA state-update age. An old location can remain valid as the last report. Polling cannot force a newer Apple/Life360 location. |
| Address is unavailable | A named place or reported address may be absent. City lookup is a separate opt-in external coordinate service, not a requirement for location tracking. |
| **Since unknown** or continuity-unconfirmed arrival | There is no matching genuine arrival evidence, or an observation gap occurred. An HA update time is not a replacement arrival time. |
| Family refresh button is absent/unavailable | It is off by default. An administrator must enable **Allow family location refresh** and save. Eligible explicitly assigned sources, opt-ins, permissions and budgets still govern requests. |
| Private map still sends city requests | Private stops external tiles; separately enabled **City lookup** must be disabled to stop server-side Photon requests. |
| Photo still exists after Remove picture | Removing a reference does not delete the HA image asset, its opaque URL or old backups. Manage retained images separately. |

## Life360 connection states

Open HomeCircle Options for account status and discovered/reporting tracker counts. `discovering` can mean the member list has not appeared yet; allow several minutes and reopen Options, then explicitly assign the correct trackers. A working account profile does not imply every member is currently sharing location.

Use HA's **Reconnect Life360** repair or **Replace saved Life360 sign-in** for an expired/rejected credential for the same account. A verified different account is refused. Review the explicit same-account confirmation only where the older setup cannot be independently checked. Do not post or repeatedly replace a token to diagnose a delayed list.

For `rate_limited`, wait until the recorded retry time. For `network_error`, check HA connectivity and backoff. `partial` isolates affected members; `unexpected_response` may indicate a malformed/changed reply. Persistent `api_error` needs sanitized diagnostics, not an assumption that it is a true rate limit. Existing working HA trackers remain a fallback. The detailed [provider issue guide](TRACKER-PROVIDER-ISSUES.md) preserves the adapter's exact behavior.

## Apple sign-in, recovery and discovery

Use the newest code for the current sign-in, not a device unlock passcode. If the UI ends an attempt after a consumed code, follow that outcome; do not replay the same code automatically.

**Check Find My access** is a read-only item-storage check and needs no device passcode. **Finish recovering item keys** can resume verified recovery material in that still-open setup. **Retry Find My item discovery** can reuse recovered keys without another passcode. These are different stages; a post-recovery discovery failure is not evidence that the passcode failed.

At a refusal, uncertain submission or safeguard warning, stop. HomeCircle never retries a passcode automatically. Do not restart setup, delete files or clear the safeguard to obtain another attempt. **Review recovery after setup or restore** can be expected after first use, an old-safeguard upgrade, cache loss or an ordinary restore. Read [maintenance](RELEASE-1.0-MAINTENANCE.md) before account-specific acknowledgment; it cannot reset Apple's allowance or recover missing later counts.

Use **Reconnect existing items** when saved keys only need Apple sign-in renewed. **Manage saved items without signing in** selects among already saved keys; it cannot renew an expired session or discover a missing item. A previously cached report may remain while an account is offline. Read the genuine source age and diagnostics before calling it a current location.

If the loaded package is uncertain after rollback/restore, verify fixed code and restart before device-passcode recovery. If an expected safeguard review is absent or the first error is unclear, close the flow and report the safe status/stage. Do not supply credentials, a location screenshot or a full HA backup.
