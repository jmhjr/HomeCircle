# Milestone 1 validation

Development target checked 2026-09-27: Home Assistant Core **2026.9.4**, CPython **3.14.7**, pytest-homeassistant-custom-component **0.13.367**. Only this HA version has been tested.

## Automated evidence

- **17 tests passed**: 12 HA flow/lifecycle cases (including parametrized invalid inputs) and the five preserved bootstrap privacy tests.
- Real HA loader and flow manager: setup, one-household enforcement, concurrent duplicate setup, cancellation of setup/options, member removal, cleared optional mappings, options reload and reconfiguration.
- Invalid/deleted selections, disabled entities, explicit rename recovery, deletion during the flow, missing-source repair creation/recovery, unavailable state and listener cleanup after unload.
- Synthetic GPS state with valid zero coordinates and locationless Home state are both accepted; no Life360 installation, credentials, provider service calls or outbound sockets in pytest.
- **Two separate real HA Core processes passed** using the same disposable on-disk storage: create/save options/stop, then start/restore/reload/unload. Actual HA person entities resolved their configured trackers and active sources from synthetic GPS and router states. Temporary storage was removed at completion. Loopback HTTP only; production HA was never accessed.
- Ruff 0.15.7 checks and formatting passed for new runtime/test code. Public-file privacy scan passed; this is a pattern guard plus manual source review, not proof against every possible secret.

The process-level check found that HA can synthesize Home-zone coordinates for a legacy Home tracker. The explicitly locationless scenario uses modern `in_zones` membership so its actual HA person has no coordinates. This is documented for milestone 2 provenance work.

## Historical browser attempt (resolved in milestone 2)

A separate local Core + HA frontend 20260826.7 instance was bound only to loopback port 18124, using ignored `work/ui-ha` storage, synthetic people and a disposable test user. HA onboarding displayed, but the frontend stalled on its own loading screen afterward. No HomeCircle browser form was reached in that attempt. Subsequent browser acceptance succeeded after repairing the disposable environment; see [milestone 2 validation](MILESTONE-2-VALIDATION.md). This frontend setup issue did not affect the separate-process Core tests. The browser tab was closed and the server stopped after the attempt. No production HA URL or storage was used.

## Scope and remaining gates

These checks establish selection/lifecycle behavior, not normalized household counts, map focus, driving/freshness classification, a finished card or real provider acceptance. Primary Home, ordinary places and per-member additional residences are persisted distinctly. Milestone 2 now implements and tests their classification; see [NORMALIZATION](NORMALIZATION.md).

The development manifest loads locally but has no public documentation URL, issue URL or code owner because no repository identity was supplied. No GitHub identity was invented. Full manifest/hassfest release validation and HACS installation/upgrade/removal are pending. No release, tag or production deployment is claimed.

All repository files remain uncommitted on the unborn `feature/entity-selection` branch. Existing bootstrap files were preserved. Xcode settings, production HA, V2 dashboards and the private reference snapshot were not modified.

## Official API references

Checked current official documentation and the installed pinned source:

- [Config flow and reconfigure](https://developers.home-assistant.io/docs/core/integration/config_flow/)
- [OptionsFlowWithReload](https://developers.home-assistant.io/docs/core/integration/options_flow/)
- [Config entry lifecycle](https://developers.home-assistant.io/docs/config_entries_index/)
- [Manifest requirements](https://developers.home-assistant.io/docs/creating_integration_manifest/)
- [HA Person](https://www.home-assistant.io/integrations/person/)
- [Person helper and source semantics in pinned Core](https://github.com/home-assistant/core/blob/2026.9.4/homeassistant/components/person/__init__.py)
- [Repairs](https://developers.home-assistant.io/docs/core/platform/repairs/)

The live documentation uses `probatio` examples in some places; HA 2026.9.4 still uses and accepts Voluptuous schemas throughout its built-in integrations. HomeCircle's selectors/schema are exercised by HA's actual flow manager.
