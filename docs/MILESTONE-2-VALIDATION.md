# Milestone 2 validation

Validated 2026-09-27 against Home Assistant Core 2026.9.4 and Python 3.14.7. Internal development version: `0.0.2-dev1`. No compatibility claim beyond this baseline.

## Automated checks

- **51 passing tests**: retained selection/privacy checks, focused normalization cases, and added HA flow/runtime tests.
- Home at primary/additional residences, ordinary-place Away, locationless Home, overlapping memberships and distinct primary-house/all-residence focus sets.
- Unavailable person precedence, deleted residence, zero/missing/non-finite/out-of-range coordinates, invalid accuracy, legacy synthesized Home coordinates, GPS supplementation, conflicting and ambiguous sources.
- Explicit timestamps versus HA observations, stale/invalid/future/naive reports, report-to-source binding after switching sources, stale driving becoming last-reported evidence without current Driving classification.
- Optional battery zero, charging false, speed with declared units, absence/invalid optional data, UI evidence mapping validation/persistence/clearing.
- Real HA timer aging with simulated clock advance; state updates recompute counts; unload removes state/registry/time callbacks and clears normalization.
- Outbound sockets disabled during pytest. No provider credentials or Life360 dependency.

**Separate-process Core acceptance passed:** the restart runner started two real HA Core processes with shared disposable storage. It checked persisted options, reload/unload, and moved an actual HA person from primary Home to an assigned synthetic residence. Home count remained two while primary-house focus became empty (the other Home member was locationless). Both processes passed, and temporary storage was removed.

## Browser acceptance

The earlier frontend stall was traced to missing `pymicro-vad`/`pyspeex-noise` dependencies needed by HA's service-list endpoint. Pinned dependencies were built inside the ignored virtual environment using already-installed Command Line Tools compilers. No Xcode license, system compiler selection or Xcode settings were changed.

The browser launcher now uses HA's standard CLI with the temporary configuration directory as its working directory. This prevents the repository's `custom_components` package from hiding the temporary test-source component. Stable loopback HTTP settings are seeded only in the new disposable storage, preventing HA's new YAML migration trial from reverting to a general network listener.

Observed in the real HA frontend: successful household setup with GPS and locationless people; configured versus active tracker suggestions; ordinary place and per-member residence selection; saved Options values; Options cancellation; integration Reload success; Reconfigure success; and the optional evidence form with all fields optional. Browser testing covers normal desktop and initial narrow layouts, not a physical kiosk or finished HomeCircle card.

Browser restart did **not** pass: the Mac CLI process exited with status `-11` (SIGSEGV) during the restart check. The native crash cause has not been isolated. Its temporary configuration was removed by the launcher. Deleted-entity recovery is covered by automated HA tests, but its browser acceptance remains incomplete after this crash. These are open browser acceptance gates, not integration passes.

## Scope and handoff

The normalized snapshot is internal runtime data. A card, authenticated frontend interface, HACS install/upgrade/removal, physical-display acceptance and real-provider tests remain later gates. Public manifest identity fields remain pending. No public repository identity was fabricated.

All work is in the original repository on the unborn `feature/normalized-presence` branch. The initial scaffold and milestone 1 implementation were preserved. No commit, stage, tag, publication, deployment, production HA access or V2 modification occurred.

See [NORMALIZATION](NORMALIZATION.md) for exact data semantics and [DEVELOPMENT](DEVELOPMENT.md) for commands. Browser screenshots are separate handoff artifacts, outside the source repository; no household data was used.

## Milestone 3 follow-up

The browser restart/recovery gaps above are now resolved in the minimal Core test worker; see [milestone 3 validation](MILESTONE-3-VALIDATION.md). The historical standalone CLI native crash remains an environment limitation.
