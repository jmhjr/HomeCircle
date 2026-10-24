# HomeCircle enabled-candidate restart and passive observation

October 21, 2026. Source `91ae59106a661143b770d7a3564d363c7c11a7dd` completed a
normal enabled restart and a finite passive observation on the isolated ARM64
test instance. This records the existing, explicitly selected Apple and Life360
connections; it does not complete general account or release acceptance.

## Installation and preservation

[Native run 39683890536](https://github.com/jmhjr/HomeCircle/actions/runs/39683890536)
passed 1,698 backend cases, all 36 required regression functions and 122 frontend
cases, with zero failures and the existing optional fixture skip. The reproducible
113-member package changes only `findmy_vault.py` from previously installed
source `f4da650e6e460382c6ee1f70827bddac43bf2780`.

The reviewed installer completed normal managed Core stop/check/start in 35
seconds and 12 guest calls. Exact package readback and all 14 continuity checks
passed at all four readbacks. All nine protected files remained unchanged while
stopped. Saved account metadata, explicit selections, Person/tracker links,
registry ownership, key identity, household settings and the current recovery
ledger were preserved. The newest raw ledger was also retained outside the
entire VM and matched at all maintenance readbacks. No proof, login, guard reset or
recovery action was needed. The expired remote exposure stayed closed.

## Corrected passive window

The source-bound observer passed 32 zero-skip local contracts. One guest command
completed four samples spaced at least 30 seconds apart, using 21 local API GETs
within its 120-second observation and 150-second host bounds. The same Core
process, saved configuration, registry ownership and all 113 candidate files
remained verified. No manual refresh, provider request, reauthentication, service
call or retry was forced; normal startup and scheduled provider traffic remained
allowed. Household refresh stayed disabled.

All four samples showed both connections connected, successful normal API
polling after Core startup, one explicitly selected/present/available tracker per
provider, and the configured Person. The Apple selection was one saved AirTag;
Life360 had five registered trackers with one explicitly selected Person/tracker.

Find My's latest account poll was successful: one selected item returned a valid
report, with five logical SDK fetch calls and 14 decoded reports. These are
last-poll diagnostics, not measured HTTP request totals. No later successful Find My poll or
source timestamp advancement was observed inside this window; its selected report
remained at least five minutes old. Life360 normal API success and HA state-write
times advanced in samples two through four. Its selected source timestamp
advanced only in the final sample, which became less than five minutes old.
Timestamp advancement does not establish newer physical coordinates.

The first completed window is retained with its coverage gap: it verified
post-Core-start API success but omitted the saved Find My item from selected
entity checks, so its Find My source-time advancement was unmeasured. The corrected
window above joins the saved item through its actual stable tracker identity.
The signed-in dashboard retained both selected cards after restart without a
manual browser reload; this is a scoped display observation.

## Limits and next gates

Availability can use a saved report. A successful startup poll, HA update and
newer source timestamp are separate observations. This window did not qualify
movement parity, fresh authentication, credential renewal, long-term operation
or every provider/member selection.

The [default-condition restore witness](RELEASE-1.0-DEFAULT-RESTORE.md) separately
qualified disabled synthetic saved storage with manual newest-guard repair. This
enabled restart performed no restore. Enabled provider-vault restoration,
automatic guard antirollback, full-system/encrypted/cloud backup, final RC, HACS
delivery and stable approval remain unqualified. Retain the newest external guard
and repair it before re-enabling an older restored connection under the documented
procedure. Continue the [controlled account protocol](RELEASE-1.0-ACCOUNT-ACCEPTANCE.md).
[Machine-readable scope](RELEASE-1.0-ENABLED-CANDIDATE.json).
