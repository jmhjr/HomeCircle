# October 11 changes — beta 18

This captures the complete main-repository working tree since `66672c9`, plus release contents committed after beta 17. The [changelog](../CHANGELOG.md) covers earlier merged arrival persistence, mapped phone charging, assigned-tracker family refresh and selected-member map following. Frozen V2 reference assets and unrelated HA configuration are preserved. No private screenshots, photos, coordinates, account sessions or field captures are release inputs.

## Main integration and card

- `place_import.py`, options flow and settings dialog: existing saved Life360 account/Circle selection, validated places, multi-select, Select all/Clear/filter, map review/Skip, final confirmation, duplicate checks and partial retry. No real zones were created by implementation verification. Imported zones are ordinary places, and remain in HA after removal. Native and card flows are documented in the setup/frontend guides.
- `normalize.py`, selection, options and diagnostics: default freshest genuine GPS ranking, explicit Follow HA Person opt-out, exact-source evidence, five-minute ranking pool and 60-second active-source preference. If no verified source is fresh, fall back to HA Person rather than overriding current presence with an old alternative. GPS geometry determines HomeCircle zones without modifying HA Person associations. Explicit sensors retain priority; pet display cutoffs stay intact.
- `pictures.py`, image-upload dependency, options, `picture-crop.js` and avatar helper: validated native HA image IDs, browser-only crop until Save, 512-pixel JPG, zoom 0.5–8, drag/sliders/reset, white padding and failed-upload retry. Custom images apply to tracker-only members; native Person images remain separate. Photo references survive edits and are shown in Details; orphaned native images are retained.
- `city_lookup.py`, entry lifecycle, snapshot API, options and attribution: administrator opt-in, selected-coordinate-only Photon reverse queries, no key, persisted hourly/daily limits, local bounded cache, source/zone exclusions, failure fallback and unload cancellation. Lookups never change GPS freshness. Exact coordinates reach Photon; hashed cache keys do not anonymize places. Removing the integration deletes the store.
- Shared model: Street, City labels for every provider with state/ZIP omission, and coarse Full/Medium/Low/Very Low battery reports kept separate from numeric percentages.
- Card/map: fixed zoom 17 on member focus; Everyone/category fit stays dynamic. Equal-height cards within each grid row and pictures in refreshed Details.

## Separate private Find My experiment

The Linux HA OS prototype remains outside the public HomeCircle integration and release archive. Its source, tests, brand assets and onboarding records were checkpointed separately in a private local archive with per-file hashes. It supports account-oriented onboarding, multiple selected items per account, item-type overrides, entity naming, native configuration safeguards, and coarse battery reports. Movement/session tests and report-key-window investigation remain private. A forward rotating-key search-window fix prevents a reproduced missed report, with a synthetic key-alignment regression. It does not establish reliable uninterrupted tracking or stable multi-account acceptance. HomeCircle consumes its ordinary HA trackers; beta 18 does not include Apple authentication, the helper, vaults, keys or this provider.

The prototype's abandoned-setup helper lifecycle case remains a stable-readiness task in its private onboarding record. User pictures and conversion outputs are private assets, not Git fixtures.

## Review and validation

See [beta 18 validation](BETA18-VALIDATION.md) for the independent Claude privacy/security/bug review, fixes and exact package checks. Native browser tests checked upload/crop/details, grid alignment, fixed zoom, import selection/Skip and city lookup in the installed development candidate. Physical-display acceptance of beta 18 and broader Core compatibility are not inferred from those checks.

Known UI issue: the native picker can show “No file chosen” while its decoded crop remains selected. This is tracked in the roadmap and does not cause an early upload. Stable field/provider recovery gates remain open.

Independent review corrections: all-stale fallback, fragmented bounded HTTP reads, city/region ambiguity with structured lookup city evidence, concurrent-zone selection errors, disabled/malformed external Life360 accounts, expected shared-report source switches, local cache removal and upload-after-navigation guards. Native user labels are escaped for Markdown, while the card safely removes those escapes in text-only descriptions. Further fixes include removing a new Primary Home from saved Other homes, matching HA’s GPS accuracy margin and skipping passive zones, requiring GPS before coordinate transmission, rejecting invalid cached street text, retaining future request reservations on clock rollback, and waiting for pending cache writes before removal. Source oscillation and field accuracy cases remain in the roadmap.
