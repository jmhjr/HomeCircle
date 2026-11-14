# HomeCircle 1.0.1

Maintenance release for Home Assistant Core 2026.11 compatibility. Publication readback and live store installation remain separate from the engineering checks below.

## Changes

Home Assistant Core 2026.11 replaced its internal zone and person storage containers. HomeCircle 1.0.0's removed zone import prevents integration startup and the dashboard card from loading. The older Person tuple lookup also fails with the new PersonData container.

This release adapts those two helpers to the new containers while preserving the earlier runtime shapes. Editable-Person restrictions, tracker ownership, append-only links, entity-ID collision handling and normal zone creation retain their existing behavior. Dependencies, minimum Core 2026.9.4, supported platforms, provider operations, recovery safeguards and saved-data formats are unchanged.

## Install or upgrade

1. Create a Home Assistant backup that includes configuration and the history you need, and protect it as private account/location data.
2. Install **v1.0.1** through **Settings → Marketplace** on Core 2026.11+, or HACS on supported Core 2026.9.4–2026.10.x. Follow the [installation and upgrade guide](INSTALLATION.md). The release's `homecircle.zip` is the manual-install alternative.
3. Restart Home Assistant. Refresh the browser if the old card remains visible.
4. Confirm the HomeCircle version, household and detail panels. Existing selections and accounts should remain in place. Do not reconnect accounts or start passcode recovery to fix a cached frontend.

The installable ZIP contains integration files at its root. For a manual installation, unpack into `custom_components/homecircle`, preserving Home Assistant's existing configuration and private storage. Do not extract it into `.storage` or restore individual account files.

## Validation

The package contains 112 files. Two canonical builds produced identical ZIP and inventory bytes. Compared with the exact anonymously downloaded published 1.0.0 ZIP, 107 members match byte for byte; only the two helpers, manifest, frontend resource version and compiled card differ. No dependencies, licenses, native runtime, stored data or extra files changed.

- Archive SHA-256: `deecf2cbbc746bf4912d71a986a12f67b6af7674670c98ec923b2fb5a1800767`.
- Inventory SHA-256: `9a141d57d51ca15a7483d879e189647a80da4f3c43b2e1567a59bfda9e99a670`.
- Core 2026.10.4: 151 focused zone/person/config-flow/frontend/release-package tests passed, without failures or skips.
- Frontend: 126 tests passed; independent bundle rebuild matched; formatting passed.
- Exact 1.0.1 ZIP on actual Core 2026.11.1: 25 standalone API/lifecycle checks passed, including real ZoneData/PersonData, identity/collision/editability rules, static resource, dashboard and unload.
- Genuine exact-package upgrade: published 1.0.0 on Core 2026.10.4 → 1.0.1 on Core 2026.11.1 → a separate 2026.11.1 restart passed. The same disposable synthetic configuration retained entry/resource identities, selections/options and an existing activity marker; HTTP card bytes/version/hash, dashboard and unrelated resources matched expectations.
- Ruff, privacy guard, source diff checks and independent read-only package/source review passed.

The actual-Core runs used native macOS/Python 3.14.7 with disposable synthetic storage and no provider accounts. External network access was blocked; the HTTP checks used numeric loopback only. The published 1.0.0 baseline was verified against its recorded SHA-256, rather than fabricated by changing the candidate's version. This maintenance release does not rerun the entire original 1.0 provider, native-platform, HACS or restore matrix. The first-release privacy, unofficial-provider, recovery and support limits continue to apply.

The same two helper files were verified in a bounded local deployment on Core 2026.11.1: startup, dashboard and existing Life360/Find My detail panels worked; saved-state fingerprints and earlier activity were preserved. That deployment retained the 1.0.0 label with the local patch. It is not a claim of 1.0.1 HACS delivery acceptance.

The focused compatibility fix received independent read-only Codex review. Claude review was unavailable because its existing session could not authenticate; the maintainer explicitly authorized proceeding without that review. No successful Claude review is claimed.
