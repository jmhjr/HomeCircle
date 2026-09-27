# Beta 5 non-admin access validation — 2026-09-27

This check used a fresh, loopback-only disposable Home Assistant Core 2026.9.4 instance. HACS installed the published `v0.1.0-beta.5` package. The HomeCircle entry selected two fictional people and their fictional phone/router trackers. No production or real-source HA user, entity, or dashboard was changed.

Two real Home Assistant users were created with non-admin accounts. A temporary custom HA permission group allowed the first account to read every HomeCircle-selected entity. A second group omitted read access to one selected router tracker. These groups existed only in the disposable instance. HA's standard non-admin groups normally permit entity reads; the restricted group was needed to exercise the selected-source permission boundary.

| Check | Allowed non-admin | Restricted non-admin |
| --- | --- | --- |
| HA credential login | Succeeded | Succeeded |
| `homecircle/snapshot` through HA WebSocket | Complete two-member fictional snapshot | `unauthorized`, with no household result payload |
| Chrome dashboard with the beta 5 card | Card displayed two members and map-position status | Card displayed zero members and the selected-source access error |

The browser check used each account's HA sign-in page and then the same temporary HomeCircle dashboard. It verified the card output after login, not just the WebSocket response. The denied account did not receive a partial household snapshot. The card's `hidden_members` option remains a display preference, not an access-control mechanism.

The disposable HA process was stopped, its temporary configuration removed, and its port verified closed. This closes the beta 5 non-admin selected-source acceptance check for Core 2026.9.4 and the fictional sources above. It does not establish behavior for every HA release, custom permission policy, or real provider source.
