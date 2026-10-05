# HomeCircle card

Native custom element and visual HA editor; bundled Leaflet 1.9.4, no CDN scripts. Build from this directory with `npm ci && npm run build`. `npm test` runs focused selection, overlap, missing-data and privacy checks. Node 23.7.0/npm 11.1.0 were used for the original development validation.

Generated module and Leaflet license go to the integration's frontend directory (ignored local build products). A release archive must include both. HomeCircle registers the module in storage-mode Lovelace and creates a first dashboard and card when none exists; additional cards can be added from the visual picker. Configure title, member visibility and map background in the editor. No YAML is needed for this path. Refresh the browser once if an already-open dashboard has cached its resource list.

Street tiles default to on for new cards. They send viewed map areas and client network metadata to OpenStreetMap, with attribution in the card; the Private map background disables those tile requests. Allowlisted Life360 portraits can make separate image requests when available. See [ADR-002](../../docs/adr/ADR-002-map-and-frontend.md) and [privacy](../../docs/PRIVACY.md).

Home means every assigned residence for counts; map Home focus means primary house only. Locationless members still appear. Unknown report times remain unknown. Member selection, category buttons and Everyone reset are independent in every card. A grouped marker opens a list of individually selectable members at overlapping screen positions.

Card member visibility is presentation only; HA permissions are checked server-side. All selected source/zone read permissions are required to retrieve a household. No data is stored in localStorage or cookies by this card.
