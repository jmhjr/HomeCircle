# Setup guide validation — beta 3

The guide was checked against the beta 3 config/options flow, field labels, normalization rules and frontend documentation. HA Person and Companion documentation and HACS custom-repository documentation are linked in the guide.

## Clean installation check

A fresh temporary Core 2026.9.4 configuration used the built beta 3 release ZIP, with fictional phone and pet trackers and supporting sensors. No household configuration or provider credentials were copied. The instance listened only on loopback and was removed after validation.

Using HA's actual flow manager, the check followed household → member → optional evidence → next member → optional evidence → final save. It verified:

- A new household can select existing person records and trackers.
- Person/Pet type and default pet freshness settings save successfully.
- Battery mappings produce the expected percentage for both members.
- A pet report timestamp bound to its tracker produces fresh evidence.
- The phone's unmapped report timestamp remains unknown.
- Both members count Home.
- Editing members while skipping the optional sensor screen preserves mappings.
- Saved options survive a separate Core process restart.
- Exactly one owned frontend resource is registered and serves the release bundle.

This was an actual clean Core installation and config-flow check, not a new HACS download or a browser click-through. HACS and physical-display evidence are recorded separately in [beta 3 validation](BETA3-VALIDATION.md). External provider sign-in and template-helper creation were not repeated. Attribute-based helper recipes remain provider-specific, and the guide explicitly leaves missing evidence unknown.

No runtime code changed. The existing real-source disposable instance and production HA were unchanged. Real departure/return testing remains deferred.
