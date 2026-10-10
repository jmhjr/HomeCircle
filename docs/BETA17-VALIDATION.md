# Beta 17 validation

[v0.1.0-beta.17](https://github.com/jmhjr/HomeCircle/releases/tag/v0.1.0-beta.17) packages the reconciled dashboard, tracker evidence, location requests, activity and radar work. See the [change record](RECENT-CHANGES-2026-10-10.md) and [changelog](../CHANGELOG.md).

The behavior candidate passed 234 backend and 86 frontend tests, lint/format/privacy checks, isolated package install/upgrade/restart/removal, independent Claude Opus 5.5 source review with checked fixes, live browser/API checks and participant-reported physical DAKboard acceptance. Versioned package checks are recorded separately below. The maintainer authorized publication with the follow-up security recheck unfinished. Published download-back and HACS upgrade checks passed as recorded below.

This remains an experimental prerelease. The iPhone-only departure/return, trustworthy phone GPS report times, unattended provider recovery and broader supported-Core testing remain open. Adaptive stale thresholds are proposed, not enabled. The people cutoff remains five minutes. All raw field records, credentials and screenshots remain private.


## Versioned package checks before publication

- 238 backend and 86 frontend tests passed; Ruff, frontend formatting, public-file guard and diff checks passed.
- The deterministic 25-file ZIP passed source/inventory matching and a separate manual audit of generated files for private household markers.
- Separate real Core processes passed package create, versioned upgrade, restart, removal and post-removal restart. Saved selections and unrelated Lovelace resources survived; the owned resource and static module disappeared after removal/restart.
- Tested archive SHA-256: `d8180b672206784f3124ab9c16b73cbfb61db982cd83780f12163330c93f6a3d`.

## Security and privacy review

Claude Opus 5.5 performed a read-only static review of sanitized public source and the exact package. It identified privacy disclosure/default-consent issues and hardening opportunities. The release fixes add administrator opt-in for external Life360 family refresh (off by default, including upgrades), disclose reuse of the external integration's server-side authorization and ordinary viewer control permissions, stop no-op refresh attempts filling activity, escape native setup description names, and correct obsolete map/cache/data documentation. Public field summaries are qualitative and contain no coordinates, addresses or named places. The focused recheck was started against the rebuilt package but stopped at the reviewer account usage limit before returning a verdict. The maintainer explicitly authorized publishing the tested prerelease without waiting for that follow-up verdict. The initial review and implemented fixes are complete; this does not claim Claude approved the rebuilt package. Static review is separate from runtime and physical-display evidence.

## Published asset and HACS upgrade

The GitHub prerelease was published from merged main commit `44639cb`, with the tested `homecircle.zip` attached. Downloading the published asset back produced the identical SHA-256 above and identical bytes. No stable release was created and the tag/package were not rewritten.

A fresh disposable Home Assistant Core 2026.9.4 instance with official HACS 2.0.5 installed the published beta 16 release first and configured two explicitly fictional members. It then selected and downloaded published beta 17 through HACS and restarted Home Assistant. All 25 installed package files matched the published ZIP. The served card bytes and owned resource version/hash matched beta 17; member IDs, presence, usable-position flags and saved household data/options survived. An unrelated Lovelace resource was preserved, and HACS recorded `v0.1.0-beta.17` as installed.

This validates the actual published HACS upgrade in a disposable instance. The production installation was not upgraded by this publication, and the prior physical DAKboard acceptance remains evidence for the reconciled behavior candidate. The temporary HACS instance and configuration were removed after verification.
