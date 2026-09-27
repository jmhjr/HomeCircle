# Post-beta 4 fixes — 2026-09-27

The published `v0.1.0-beta.4` tag and release ZIP remain unchanged. These working-tree changes address two findings from the [beta 4 audit](BETA4-RELEASE-AUDIT.md) for a future prerelease.

- A rejected household snapshot no longer retries on every ordinary HA `hass` update. The card still retries through its 15-second refresh timer and immediately after a changed or reconnected HA connection. A browser-component regression reproduces the rejected-request sequence and recovery.
- HomeCircle now has an entry-removal callback. It reads the saved resource ID when no runtime ID is present, removes only a matching owned card resource, and leaves unrelated or manually registered resources alone. A Core test covers removal of an entry that was already unloaded with a persisted registration.

The documented removal order remains: remove the HomeCircle integration entry, uninstall it in HACS, then restart HA. If the package has already been uninstalled and HA restarted, Home Assistant cannot call HomeCircle's removal code; that order still needs separate handling or recovery guidance. Resource replacement during an options reload is also still open.

Validation of this unreleased source: 61 Python tests and 14 frontend tests passed; Ruff and frontend formatting passed; Home Assistant Core 2026.9.4 hassfest found one integration and zero invalid integrations. A clean local build produced a 14-file ZIP, and its isolated Core install, version-only upgrade rehearsal, restart, entry removal and post-package-removal restart all passed. The ZIP is a local test artifact, not a GitHub release or HACS deployment. Real field-acceptance gates from the [beta 4 audit](BETA4-RELEASE-AUDIT.md) remain open.
