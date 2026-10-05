# HomeCircle

Family location and presence for Home Assistant, independent of the tracking provider.

**Experimental development software — not a stable release.**

Use a disposable or test Home Assistant dashboard. Published beta 16 keeps the map visible while the member list scrolls, prevents member details from overlapping, and includes the beta 15 driving-report improvement. Beta 14 added tracker source labels; beta 13 added Person-first setup and dashboard improvements. Existing tracker-only members remain supported. See the [changelog](CHANGELOG.md) for the other changes. Beta 16 passed the physical DAKboard check; broader field testing remains open. No stable release is approved.

**Status: beta 16 prerelease; stable release gates remain open.** HomeCircle is a working name; public naming remains a release decision. The existing V2 dashboard remains the reference system. The separate production beta-test installation does not replace or change it.

HomeCircle consumes standard HA `person` and `device_tracker` entities, with optional explicitly selected supporting sensors. An optional direct Life360 connection uses a built in tracker provider contract designed for more providers in later releases. Existing HA trackers remain selectable without a HomeCircle provider account.

## Start here

- [Per-source report times](docs/PER-SOURCE-REPORTS.md)
- [Beta 16 validation](docs/BETA16-VALIDATION.md), [beta 15 candidate validation](docs/BETA15-CANDIDATE-VALIDATION.md), [current release readiness](docs/CURRENT-RELEASE-READINESS.md), and [earlier direct Life360 validation](docs/DIRECT-LIFE360-CANDIDATE-VALIDATION.md)

- [Step-by-step setup: iPhone, Life360, pets and supporting sensors](docs/SETUP.md)

- [Product and V0.1 boundary](docs/PRODUCT.md)
- [Stable scope audit and remaining gates](docs/STABLE-SCOPE-AUDIT.md)
- [Feature inventory and reference evidence](reference/feature-inventory.md)
- [Architecture](docs/ARCHITECTURE.md) and [ADR-001](docs/adr/ADR-001-provider-independence.md)
- [Troubleshooting built in tracker providers](docs/TRACKER-PROVIDER-ISSUES.md)
- [Roadmap and acceptance gates](docs/ROADMAP.md)
- [Development and Git workflow](docs/DEVELOPMENT.md)
- [Privacy and security](docs/PRIVACY.md)
- [Normalization contract](docs/NORMALIZATION.md)
- [Multiple-tracker switching validation](docs/MULTI-SOURCE-VALIDATION.md)
- [Milestone 2 validation](docs/MILESTONE-2-VALIDATION.md)
- [Milestone 1 validation and limitations](docs/MILESTONE-1-VALIDATION.md)
- [Historical bootstrap validation](docs/BOOTSTRAP-VALIDATION.md)

## Release preparation

Maintainer: [@jmhjr](https://github.com/jmhjr). The repository is public for development review and HACS custom-repository testing. The current experimental prerelease is [v0.1.0-beta.16](https://github.com/jmhjr/HomeCircle/releases/tag/v0.1.0-beta.16). See [beta 16 validation](docs/BETA16-VALIDATION.md) and the [historical release preparation record](docs/RELEASE-VALIDATION.md).

## Repository

```text
HomeCircle/
├── README.md, LICENSE, CHANGELOG.md, hacs.json
├── docs/                  Product, architecture, roadmap, decisions, privacy, development
│   └── adr/               Architecture decision records
├── reference/
│   ├── dashboard/         Generic reference description and example YAML
│   ├── screenshots/       Sanitized capture policy; no household images
│   └── feature-inventory.md
├── custom_components/homecircle/   Configuration, normalization and lifecycle
├── frontend/homecircle-card/       Card/editor implementation boundary
├── tests/                 Acceptance plan and synthetic fixtures
├── scripts/               Public-file privacy check
└── .githooks/             Local pre-commit privacy check
```

## V0.1 outcome

Install through HACS; add HomeCircle in HA; select or create an HA Person for each new member, assign a tracker, and choose Home and additional places. First setup creates a dashboard and card if none exists; the visual editor supports additional cards. No manual YAML is required in the validated storage-mode onboarding flow. Optional direct Life360 trackers and older tracker-only members are supported. The remaining stable-release gates are tracked in the [scope audit](docs/STABLE-SCOPE-AUDIT.md).

The reference is **HomeCircle Reference Implementation v1**, frozen from available local V2 artifacts and later extracted-card source. Raw household files are held outside this Git repository in a restricted local snapshot. Public reference files contain generic examples only. See [reference provenance](reference/dashboard/README.md) for the distinction between production V2 and later clone work.

MIT licensed. No upstream implementation is copied into the new runtime. Any future code reuse must retain its original license and third-party notices.

The card and authenticated snapshot interface began in beta 4 and have continued through beta 16. See [frontend setup](docs/FRONTEND.md), [beta 16 validation](docs/BETA16-VALIDATION.md), and the [historical milestone 3 validation](docs/MILESTONE-3-VALIDATION.md). No V2 migration is included.
