# HomeCircle 1.0 controlled account acceptance

Prepared October 20, 2026 after the maintainer selected both direct Apple Find My
and Life360 for 1.0. This is a finite execution protocol, not a record of completed
account tests. The [release plan](RELEASE-1.0-PLAN.md) tracks the remaining
platform, assurance, service and release decisions separately.

## Before opening an account form

Identify the intended HA instance, whether it is disposable or used every day,
its installed HomeCircle revision and local changes, and the exact package to be
tested. The current development preview still displays `0.1.0-beta.20` despite
having different bytes from published beta 20. A version label alone cannot
identify it. Record the package and served card hashes privately; do not replace
an existing installation merely to begin this protocol.

Use a separate test household and storage where supported. First capture a
consistent protected backup and a tested restoration path for existing state.
Keep the newest Find My recovery guard separately under the
[prepared restore procedure](FINDMY-SETUP.md#prepared-supervisor-backups).
An enabled older backup can roll back that guard. A backup does not reset any
provider-side attempt allowance.

Record the owner-approved account and limited item/member selections privately.
Credentials, verification codes and trusted-device unlock passcodes are entered
only in HA's owner-facing forms. Do not put them in chat, command arguments,
screenshots, issue reports or public receipts. Confirm the chosen platform's
dependency/runtime checks and the applicable assurance/service decisions before
starting the corresponding provider exercise.

## Finite cases

| Area | Required observation | Acceptance boundary |
| --- | --- | --- |
| No-account setup | Create a household using explicitly chosen existing People/trackers and a nonempty setting | No credentials or YAML required; no associations inferred from names |
| Life360 connection | Owner signs in using the intended account; wait for discovery, then explicitly select the intended members in Options | Successful account validation is separate from discovery, selection and a new location report |
| Find My existing identity | Reconnect with the intended retained identity, discover/confirm the chosen items, reload and restart | Saved identity, selections and settings agree; report request success is separate from report freshness |
| Find My fresh identity | Exercise an independently identified fresh setup without replacing a working connection | Record provisioning, verification, usable report grant, key discovery and report stages separately; historical reconnect success does not qualify fresh setup |
| Find My recovery | If required and authorized, owner selects the intended trusted device and enters its correct passcode once in HA | Verify account/record binding, successful key recovery, explicit item confirmation and persistence; never submit a deliberately wrong passcode |
| Cancel/abandon | Exit before a proof or account-confirming save at the declared stage | Transient work finishes/closes and the original saved connection remains intact |
| Persistence | Reload, restart into the same protected storage and inspect the same selected members/items | Compare actual identifiers and saved settings; matching names alone are insufficient |
| Isolation | Observe a naturally failing/unavailable item or use a separately identified synthetic fault | Healthy siblings/providers continue; a synthetic fault is not a natural provider failure |
| Expiry/renewal | Observe the natural event if it occurs during the agreed field window | Keep absent events pending; do not invalidate a working credential or force repeated sign-ins to manufacture the case |
| Disconnect/removal | Exercise only against the disposable test connection after preserving recovery state | Selected-member protections, owned-resource cleanup, retained/deleted data and unaffected household behavior agree with the documented policy |

For each networked step, record only fixed stage/outcome categories, bounded
request counts where actually measured, cleanup, identity-equality booleans and
source-report age categories. A successful poll, API response, HA observation or
native app's “Now” label does not establish newer physical coordinates.

Stop a provider exercise on a rate limit, uncertain recovery dispatch, account
mismatch, unsupported format, cleanup failure or unexpected scope. Preserve the
outcome and current guard. Follow a usable server retry hint when present; an
absent hint does not justify an invented cooldown, identity rotation, automatic
retry or safeguard reset. A verified proof followed by a material failure is
distinct from a rejected passcode. Use a supported resumable continuation only
for the same authenticated account and exact record.

## Field and display follow-through

Agree on a finite observation window before starting it. The release-plan
proposal is seven consecutive days plus a real departure/return, a background
phone interval away from Wi-Fi, a quiet/stale-item interval, a controlled network
outage/recovery and a renewal observation if it occurs. Record source report time,
HA observation time and displayed freshness separately. Do not open a tracking
app or request extra reports during a passive observation unless that intervention
is explicitly part of the chosen case.

Check the final desktop/mobile and intended physical display with the same
identified build, including explicit selection, selected-member following,
keyboard/touch, overlap expansion and attribution. The scoped desktop
[picture checks](PICTURE-BROWSER-VALIDATION.md) do not establish completed native
file-picker selection, mobile behavior or physical-display acceptance.

## Receipt and endpoint

Keep detailed evidence private. A public receipt should contain the exact source
and artifact hashes, dated environment versions, named case, passed/failed/pending
status, scope, cleanup and limitations. Exclude account names/IDs, provider tokens,
keys, raw replies, entity identifiers tied to people, coordinates, photos and
location screenshots. Do not claim request counts if they were not measured.

Finish by removing only owned disposable test state, confirming the original
household still works, and recording the recovery endpoint. Retain the latest
recovery guard and protected backups according to the chosen restore plan.
Reconcile failures before beginning another account attempt. The final RC,
genuine HACS delivery and stable publication remain separate identified stages.
