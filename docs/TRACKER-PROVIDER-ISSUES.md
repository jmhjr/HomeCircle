# Built in tracker provider issue workflow

Life360 and future built in tracker providers may rely on unsupported APIs. HomeCircle must identify a failure before changing an adapter or asking for private account data. A working Home Assistant entity from another integration remains a supported fallback.

## What a user sees

An admin's HomeCircle card shows a short connection message when a built in tracker provider needs attention. Open **HomeCircle Options** to see the connection status and number of trackers found and reporting. If Home Assistant shows a **Reconnect Life360** repair prompt, use it to enter a new password or access token; household selections stay in place. For persistent failures, download HomeCircle diagnostics from Home Assistant's integration page. Diagnostics contain only a provider status code, aggregate tracker counts, and times of API success, error and retry. They do not contain credentials, member IDs, locations, addresses, or API responses. Shared cards used by non-admin viewers do not show account health.

| Status | What it establishes | Next check |
|---|---|---|
| `discovering` | Sign-in worked; no Circle member is available yet | Wait for another discovery cycle, then reopen Options |
| `auth_required` | Life360 rejected authorization | Complete the Home Assistant repair prompt |
| `rate_limited` | Provider asked HomeCircle to pause | Wait until the recorded retry time; do not repeatedly reconnect |
| `network_error` | Request timed out or transport failed | Check HA connectivity and retry time |
| `api_error` | Provider request failed without a more specific cause | Compare with upstream provider/client status after repeated failures |
| `unexpected_response` | Response shape no longer matches the adapter | Treat as a possible API change; open a sanitized issue |
| `partial` | Some members reported while others failed | Check each affected tracker in HA without sharing its location |
| `connected` | API calls succeeded | If a tracker is unavailable, check its sharing/location settings and report age |

These codes identify the failure stage. They do not prove why an unsupported service changed. A single rate limit or delayed member list should not be labeled an API break.

For Life360, a denied Circle or member request is isolated so other members can keep reporting. If no member reports successfully, HomeCircle checks whether the account profile is still accessible, at most once per ten minutes. A working profile leaves the failure as `api_error`; a rejected profile leads to one fresh sign-in check. HomeCircle opens the reauthentication prompt and stops credential retries only if that sign-in is rejected. A denial from the top-level Circle list instead pauses before retrying sign-in. A malformed member reply, including invalid coordinates in a location object, is marked `unexpected_response`; other members still get polled, and only the affected tracker becomes unavailable after its own outage limit. Missing location data or location sharing turned off leaves that tracker unavailable without labeling the reply an API change. A later valid reply restores it.

Discovery also isolates a malformed member listing or a failed Circle listing. HomeCircle keeps previously known Circle links during that failed pass, polls the known members, and retries discovery after one minute. A fully successful discovery can then remove memberships that really disappeared. Rate limiting still pauses all provider requests. On startup, previously registered direct trackers appear as unavailable until discovery succeeds, including after an offline restart. If the tracker platform fails to start, the parent HomeCircle entry may remain loaded; its diagnostics show `not_loaded`, and an integration reload retries platform setup.

Credential replacement and reauthentication compare a private fingerprint of the verified Life360 account when one was saved at initial setup. A different account is rejected so existing tracker selections cannot silently point to the wrong household. For an older development entry without a fingerprint, replacement through Options verifies both the saved and new sign-ins when possible. A verified mismatch is rejected even if the user selects the same-account confirmation. If the saved sign-in no longer works, HomeCircle requires explicit confirmation that the new credential is for the same account before retaining tracker selections. Reauthentication already follows a rejected sign-in, so it does not retry the old credential and requires this confirmation for an older entry. Either successful path saves the new account fingerprint. Confirmation cannot independently prove the identity of an expired old credential. To use a different Life360 account, remove the HomeCircle integration and set up a new household.

## Support and development triage

1. Record the HomeCircle version, Home Assistant version, time window, provider status code, and whether existing HA trackers still work. Ask for the sanitized diagnostics export. Do not request credentials, tokens, cookies, raw logs, Circle/member IDs, coordinates, addresses, screenshots containing locations, or full API replies.
2. Separate authorization, rate limiting, transport, discovery, and response-shape failures. Check the provider client's current upstream code and official maintainer reports before changing request behavior. Reproduce the failing stage with fictional responses in a disposable Home Assistant instance.
3. Fix only the provider adapter. Preserve the stable provider ID, tracker unique IDs, existing entity selections, and the common HA entity boundary. Add a regression for the actual failure, including retry and unavailable behavior. Keep errors as safe codes and avoid logging exception text or request URLs that may contain secrets.
4. Run the Python and frontend suites, privacy guard, package lifecycle, and published-release upgrade rehearsal. Test failed authorization and reauthentication without a real account. Test with a real account only when its owner can authorize the check; verify discovery, report time, restart, and Home/Away behavior separately. Browser or synthetic checks cannot close that field gate.
5. If the provider remains unusable, leave other providers and existing HA trackers functioning. Explain the status and fallback in the release note. Do not silently claim that a stale or unavailable tracker is Away.

## Requirement for each future provider

Register a separate connection, credential step, and reauthentication step in `tracker_providers.py`; create HA tracker entities; implement `async_start`, `async_stop`, and the allowlisted `ProviderHealth` snapshot. Start Home Assistant reauthentication with the failing provider's ID so a second connection cannot send the user to the wrong account form. Specify discovery and polling intervals, rate-limit backoff, stale-member behavior, and stable entity IDs. Add tests for successful discovery, delayed or partial discovery, auth failure, rate limiting, transport failure, changed response shape, restart, and removal. Never store or export raw provider responses.
