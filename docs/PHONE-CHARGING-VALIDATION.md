# Phone charging status

This unpublished beta 17 development candidate accepts an explicitly selected sensor or binary sensor for the optional charging mapping. Battery-state reports Charging, Not Charging and Full map to true, false and false respectively; on/off remains supported. Unknown, unavailable and unrecognized reports remain unknown. This does not change driving parsing or location-source selection. Tracker battery_charging attributes remain the fallback when no explicit mapping exists.

The setup selector and validation both allow sensor and binary_sensor entities. Existing per-input read authorization, runtime state subscriptions and cleanup apply to the explicit mapping. No new location request or provider request is made.

For the active phone-only field test, the live registry confirmed the chosen mobile_app battery-state sensor belongs to the same device as the explicitly selected phone tracker. Other members and the HA Person association are preserved. A private restoration override retains this authorized charging mapping when the temporary phone-only tracker selections are restored. The recorder receives a new configuration baseline without extending its original deadline. Saving options resets local arrival/activity checkpoints by the existing full-configuration fingerprint contract; genuine tracker arrival evidence remains available.

Validation covers all recognized states, unavailable/unrecognized states, source evidence, settings acceptance and persistence, and removal from runtime subscriptions when the mapping is cleared. Backend suite: 268 tests pass. Production acceptance is recorded after activation. Published beta 17 assets are unchanged.

Live activation: the same-device sensor reports Charging and the HomeCircle snapshot reports charging true. The saved options differ only by this explicit charging mapping. Jim remains phone-only; the guarded restoration dry run passes and retains the new mapping. The private recorder is running with its original deadline. Candidate ZIP SHA-256: `eab735adfd1deba66c71a2d4a48544bab66d1dbdd51456776ef5a3b82f0311eb`. Physical DAKboard acceptance remains separate.
