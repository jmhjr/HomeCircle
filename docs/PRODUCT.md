# Product

HomeCircle is a provider-independent family location/presence platform for Home Assistant. Its audience is a household using an always-visible family dashboard, including portrait wall displays and optional DAKboard/TouchHub presentation.

The core turns configured HA location entities into a coherent household view. An optional built in Life360 connection can also create HA trackers using account credentials supplied in HomeCircle. No provider account is needed for the core. HomeCircle does not collect phone locations itself, guarantee continuous tracking, or replace the source services. Missing information must stay visibly unknown rather than be invented.

## V0.1

1. Install an integration package through HACS and add HomeCircle using HA's config flow.
2. Select or create an HA Person for each new person or pet, then assign and configure that member's tracker. Show associated/active `device_tracker` sources where HA exposes them; allow explicit tracker selection when association cannot be determined safely. Do not guess relationships from entity names. Preserve existing tracker-only members and their conversion path.
3. Select a primary Home zone and additional places. Additional residences are assigned per member; ordinary places such as Work are not automatically Home.
4. Normalize family member identity, presence, optional location, source, timestamp confidence, and optional battery/status data.
5. Create a HomeCircle dashboard and card during first setup when none exists; also allow adding a card through the UI. The visual editor and resource registration require no manual YAML in a storage-mode dashboard.
6. Provide member cards, a basic map, usable overlapping markers, category summaries, and member/category/overview focus in a readable portrait layout.

A member at their assigned dorm/second home counts as Home. The default At Home focus includes only members at the primary family house. An explicit future or V0.1 option may include all residences, but must not change the default. Apply the same classification to member labels and counts. Unavailable is separate from Away. Driving requires available evidence; it is not inferred from being Away.

Pets, optional direct Life360 trackers, source labels, battery, report times, and evidence-based driving are implemented in beta 16. A new pet needs an HA Person and an existing pet tracker; the Person record does not create a GPS source. Battery and driving evidence remain optional, never prerequisites for basic presence. Existing tracker-only members remain readable and can be moved to a Person without losing their settings.

## Beyond V0.1

Additional built in tracker providers, address enrichment, drive time/ETA, weather/radar, history, more map-provider choices, and distance-apart summaries follow in separate milestones. Beta 16 already includes pet onboarding and a kiosk view; their validated scope is recorded in the beta 16 reports. Preserve other reference behavior in the inventory until implemented and accepted.

## Experience and success

A household with existing HA people should finish core setup without editing YAML or supplying provider credentials. A non-GPS tracker still yields presence, with an honest unavailable map position. OpenStreetMap street tiles are the default for new cards and send viewed map areas to the tile service; the editor offers a private background. The reference remains usable until replacement is expressly selected. No automatic V2 migration, HA zone rewriting, or removal of existing cards is planned.
