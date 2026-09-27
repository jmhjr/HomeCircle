# Product

HomeCircle is a provider-independent family location/presence platform for Home Assistant. Its audience is a household using an always-visible family dashboard, including portrait wall displays and optional DAKboard/TouchHub presentation.

The product turns already configured HA location entities into a coherent household view. It does not collect phone locations, log into tracking services, guarantee continuous tracking, or replace those services. Missing information must stay visibly unknown rather than be invented.

## V0.1

1. Install an integration package through HACS and add HomeCircle using HA's config flow.
2. Discover and let the user select existing `person` entities. Show associated/active `device_tracker` sources where HA exposes them; allow explicit tracker selection when association cannot be determined safely. Do not guess relationships from entity names.
3. Select a primary Home zone and additional places. Additional residences are assigned per member; ordinary places such as Work are not automatically Home.
4. Normalize family member identity, presence, optional location, source, timestamp confidence, and optional battery/status data.
5. Add a HomeCircle card/dashboard through the UI, with a visual editor and resource registration that require no manual YAML.
6. Provide member cards, a basic map, usable overlapping markers, category summaries, and member/category/overview focus in a readable portrait layout.

A member at their assigned dorm/second home counts as Home. The default At Home focus includes only members at the primary family house. An explicit future or V0.1 option may include all residences, but must not change the default. Apply the same classification to member labels and counts. Unavailable is separate from Away. Driving requires available evidence; it is not inferred from being Away.

Pets remain a product requirement. Direct pet `device_tracker` selection is planned after the person-first V0.1 flow; V0.1 must not break or remove pet behavior from the existing reference installation. Battery and driving enhancements are optional mappings, never prerequisites for basic presence.

## Beyond V0.1

Pet onboarding, address enrichment, drive time/ETA, weather/radar, history, polished map-provider choices, distance-apart summaries, and physical kiosk parity follow in separate milestones. Preserve their reference behavior in the inventory until implemented and accepted.

## Experience and success

A household with existing HA people should finish setup without editing YAML, pasting provider credentials, or naming a tracking provider. A non-GPS tracker still yields presence, with an honest unavailable map position. The reference remains usable until replacement is expressly selected. No automatic migration, HA zone rewriting, or removal of existing cards is part of this bootstrap.
