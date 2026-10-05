# Beta 16 published validation

[v0.1.0-beta.16](https://github.com/jmhjr/HomeCircle/releases/tag/v0.1.0-beta.16) is a public experimental prerelease. Beta 15 was tested but not published separately; its driving-report changes are included. The existing V2 dashboard remains unchanged.

The published 21-file `homecircle.zip` matched the tested local package byte for byte. SHA-256: `ec63aa699160b0e844ef4f717c2520ff259eb2b3f502c0cd3f2f4b8ba5c493fa`. The release tag points to the merged beta 16 code on `main`, whose tracked file tree matched the tested candidate. The package passed 157 Home Assistant tests, 29 frontend tests, Ruff, Prettier, and the public-file guard. Claude's final read-only review found no blocking issues after the fixes.

The exact candidate package was manually staged on the separate production HomeCircle beta-test installation with the prior beta 15 copy retained for rollback. After restart, the browser showed six non-overlapping member rows, a scrollable list, a visible map, and working member and Everyone controls. The user refreshed the physical DAKboard and confirmed no overlapping cards or data, scrolling with the map visible, and member and Everyone touch controls. These checks occurred before publication on the package that became the published asset.

HACS download of the newly published release was not separately exercised at this checkpoint; production was manually staged with matching package bytes. This prerelease is not stable-release approval or a migration of the V2 dashboard. See the [candidate validation](BETA16-CANDIDATE-VALIDATION.md) for the detailed test record.
