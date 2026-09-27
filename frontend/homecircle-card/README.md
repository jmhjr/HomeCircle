# HomeCircle card

Native custom element and visual HA editor; bundled Leaflet 1.9.4, no CDN dependencies. Build from this directory with `npm ci && npm run build`. `npm test` runs focused selection, overlap, missing-data and privacy-default checks. Node 23.7.0/npm 11.1.0 were used for this development validation.

Generated module and Leaflet license go to `custom_components/homecircle/frontend/` (ignored local build products). A release archive must include both. HomeCircle registers the module in storage-mode Lovelace; add **HomeCircle** from the visual card picker. Configure title, member visibility and optional street tiles in the visual editor. No YAML is needed for this path. Refresh the browser once if an already-open dashboard has cached its resource list.

Street tiles default to off. Native HA card previews may make their own external requests; HomeCircle itself loads only its local module and authenticated snapshot until street tiles are enabled. See [ADR-002](../../docs/adr/ADR-002-map-and-frontend.md).

Home means every assigned residence for counts; map Home focus means primary house only. Locationless members still appear. Unknown report times remain unknown. Member selection, category buttons and Everyone reset are independent in every card. A grouped marker opens a list of individually selectable members at overlapping screen positions.

Card member visibility is presentation only; HA permissions are checked server-side. All selected source/zone read permissions are required to retrieve a household. No data is stored in localStorage or cookies by this card.
