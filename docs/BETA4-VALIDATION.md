# Beta 4 validation

Published experimental prerelease: https://github.com/jmhjr/HomeCircle/releases/tag/v0.1.0-beta.4

## Package and isolated checks

- 60 Python and 12 frontend tests passed.
- Pinned Core 2026.9.4 hassfest found one integration and zero invalid integrations.
- The packaged lifecycle passed install, upgrade fixture, separate-process restart and removal, preserving unrelated resources.
- A separate disposable Core instance passed eight actual HA Person source-switching checkpoints using fictional phone, cloud and router trackers. Per-source fresh/stale timestamps, unknown evidence, fallback and integration reload passed.
- The new setup screens were previously walked through in an isolated browser: selecting, saving and reopening a mapping, then adding a second source with a separate empty field.

## Actual HACS upgrade

The existing real-source disposable instance at port 18125 was confirmed running published beta 3 before the upgrade. Its installed component and full HomeCircle settings were backed up privately. HACS downloaded beta 4 and every installed package file matched the release ZIP.

After HA restarted, HACS recorded beta 4. All HomeCircle data and options remained byte-for-byte equivalent as parsed JSON, including Ruby's Pet settings (1440 minutes at Home, 5 minutes away) and every existing supporting sensor mapping. Three separate test records remained map-focusable. Exactly one owned beta 4 frontend resource remained, and the served JavaScript matched the release ZIP.

The browser showed the real-source card with three Home members, Ruby's Pet label and report age, iPhone's unknown report time and Life360's current report age. The integration details page showed version `0.1.0-beta.4`; Options displayed the new **Configure report times for each source** switch for the saved iPhone member. The Options draft was closed without saving any changes. Existing beta 3 mappings therefore remain in their legacy format and continue to work; per-source conversion on these live records has not been performed.

The user could not initially reach the beta 4 page from the DAKboard. Inspection found that the existing HomeCircle Test button in the assigned Kitchen TouchHub still targeted the earlier synthetic test instance. Its URL was updated to the real-source beta 4 test page while preserving the other dock items. The saved button target was read back, and DAKboard reported that connected displays will update after its Refresh Displays action. Physical page loading and touch acceptance are pending user confirmation; the cloud editor and desktop browser do not substitute for a DAKboard tap. The beta 4 Options switch was verified in the desktop browser, not yet on the physical display. The real departure/return check remains deferred. Production HA was unchanged. No private source settings, coordinates or screenshot were committed to GitHub.
