# Stable V0.1 scope audit — 2026-10-04

This is a pre-release review, not approval to tag `v0.1.0`. It compares the intended [product](PRODUCT.md) and [roadmap](ROADMAP.md) with beta 16 source, automated tests, and the [published validation record](BETA16-VALIDATION.md). Older milestone and beta validation reports are dated evidence, not current installation instructions.

## Intended capabilities

| V0.1 capability | Implementation and evidence | Audit result |
| --- | --- | --- |
| Provider-independent core using existing HA people and trackers | `config_flow.py`, `selection.py`, `normalize.py`; independent iPhone and Life360 source checks in [release validation](RELEASE-VALIDATION.md) | Implemented; one real HA-entity Life360 departure/return now verified |
| Person-first people and pets, tracker assignment, places, and edit shortcuts | `config_flow.py`, `person_setup.py`, `zone_setup.py`; flow tests and [fresh-install findings](USABILITY-FINDINGS-2026-10-04.md) | Implemented; existing tracker-only members retain a conversion path |
| Home/Away/Driving/Unavailable, residence counts, primary-house focus, source and timestamp provenance | `normalize.py`; normalization tests and [contract](NORMALIZATION.md) | Implemented; one real Driving/Away/Home timeline now verified |
| Automatic first dashboard, card/editor, map focus, overlap handling, scrollable member list, kiosk, and map visibility control | `dashboard_setup.py`, `frontend.py`, card source; [beta 16 candidate](BETA16-CANDIDATE-VALIDATION.md) and [published validation](BETA16-VALIDATION.md) | Implemented; browser and physical DAKboard checks passed on the published package bytes |
| Optional direct Life360, shared provider contract, safe health/repair flow | `tracker_providers.py`, `life360_direct.py`, the tracker platform and diagnostics modules; provider tests and [direct-account validation](DIRECT-LIFE360-CANDIDATE-VALIDATION.md) | Implemented; unsupported API and unattended real failure/recovery remain field risks |
| HACS package, setup, upgrade, restart, and normal removal | Manifest, `hacs.json`, release scripts; [beta 16 validation](BETA16-VALIDATION.md) and earlier [beta 4 removal check](BETA4-VALIDATION.md) | Implemented and checked in documented scopes; repeat full lifecycle for the stable candidate |
| Authenticated access, privacy, licensing, and network disclosure | `api.py`, `frontend.py`, `diagnostics.py`, [privacy rules](PRIVACY.md), [map decision](adr/ADR-002-map-and-frontend.md) | Implemented for beta; repeat source, generated bundle, archive, history, and dependency/license review on the stable candidate |

The source review found no feature in the V0.1 scope at the time of this audit that was wholly absent from beta 16. The subsequently requested HA Person source-conflict explanation is not implemented in the published beta 16; a working-tree candidate adds it and needs real-case acceptance. The Python suite and 29 frontend tests passed during the original audit. Automated checks and earlier field snapshots do not establish the remaining field behavior below.

## Gates still open before a stable tag

Real departure/return presence transitions are complete for one production Life360-backed HA tracker and the selected Mobile App iPhone. [Current release readiness](CURRENT-RELEASE-READINESS.md) records both timelines and their different timestamp confidence. The iPhone had an eleven-hour HA state update gap and no independent GPS report time. These trips do not exercise the optional direct Life360 connection.

1. Establish genuine iPhone GPS report-time evidence and investigate its long daytime update gap; the production October 5 presence transitions passed but continuous reporting is unverified. The disposable server's lack of an external URL prevents its away-from-LAN test. A prior Friday trip exposed an HA Person repeatedly marked Home by an unselected stationary tracker while the iPhone was Away. Validate the new source-conflict explanation against that configuration; no historical card snapshots were retained for Friday. Do not expose household routes in public validation.
2. Exercise an unattended real provider outage and recovery. Confirm that unaffected trackers continue, that HomeCircle does not mislabel stale/unavailable data, and that a recovered source returns without losing selections. The paused-integration and fictional fallback rehearsals cover narrower cases.
3. Choose the supported HA Core version range and validate it. Tests and HACS metadata currently establish Core 2026.9.4 as the baseline, not every later release.
4. Build the exact stable candidate, rerun automated, HACS/hassfest, package, privacy/history/license, install/upgrade/restart/removal, browser, and physical-display checks. Then review the release notes and README in the tagged snapshot before publication.
5. Decide the stable public name and confirm that optional direct Life360, with its unsupported API and disclosed limitations, belongs in stable V0.1. Its adapter is implemented; direct-connection movement and provider failure acceptance are incomplete.

## Documentation reconciliation

The original product and [ADR-001](adr/ADR-001-provider-independence.md) predated the optional direct Life360 decision and beta 13 Person-first pet flow. The current documents now identify the provider connection as optional, preserve the HA entity boundary, and describe the Person-first flow. The setup and frontend guides now use beta 16 and the current dashboard and street-tile defaults. Historical validation files retain their dated claims. The [current release readiness](CURRENT-RELEASE-READINESS.md) remains the running field-test record.
