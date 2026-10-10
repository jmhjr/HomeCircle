# HomeCircle

Family location and presence for Home Assistant, independent of the tracking provider.

**Experimental development software — not a stable release.**

Use a test Home Assistant dashboard. Beta 17 adds clearer tracker evidence and person details, bounded location requests, Recent activity, improved map controls, and opt-in IEM radar with observed/forecast animation. It includes fixes from independent code review and passed the physical DAKboard check in its documented scope. Background iPhone departure/return testing remains open. See the [changelog](CHANGELOG.md).

**Status: beta 17 prerelease; stable release gates remain open.** HomeCircle is a working name; public naming remains a release decision.

HomeCircle consumes standard HA `person` and `device_tracker` entities, with optional explicitly selected supporting sensors. An optional direct Life360 connection uses a built in tracker provider contract designed for more providers in later releases. Existing HA trackers remain selectable without a HomeCircle provider account.

Beta 17 packages the reviewed work recorded in [October 8–10 changes](docs/RECENT-CHANGES-2026-10-10.md). See [beta 17 validation](docs/BETA17-VALIDATION.md) for release checks and remaining gaps.

## Start here

- [Per-source report times](docs/PER-SOURCE-REPORTS.md)
- [Beta 16 validation](docs/BETA16-VALIDATION.md), [beta 15 candidate validation](docs/BETA15-CANDIDATE-VALIDATION.md), [current release readiness](docs/CURRENT-RELEASE-READINESS.md), and [earlier direct Life360 validation](docs/DIRECT-LIFE360-CANDIDATE-VALIDATION.md)

- [Step-by-step setup: iPhone, Life360, pets and supporting sensors](docs/SETUP.md)

- [Product and V0.1 boundary](docs/PRODUCT.md)
- [Stable scope audit and remaining gates](docs/STABLE-SCOPE-AUDIT.md)
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

Maintainer: [@jmhjr](https://github.com/jmhjr). The repository is public for development review and HACS custom-repository testing. The current experimental prerelease is [v0.1.0-beta.17](https://github.com/jmhjr/HomeCircle/releases/tag/v0.1.0-beta.17). See [beta 17 validation](docs/BETA17-VALIDATION.md) and the [historical release preparation record](docs/RELEASE-VALIDATION.md).

## Repository

```text
HomeCircle/
├── README.md, LICENSE, CHANGELOG.md, hacs.json
├── docs/                  Product, architecture, roadmap, decisions, privacy, development
│   └── adr/               Architecture decision records
├── reference/             Archived design material; not build inputs
├── custom_components/homecircle/   Configuration, normalization and lifecycle
├── frontend/homecircle-card/       Card/editor implementation boundary
├── tests/                 Acceptance plan and synthetic fixtures
├── scripts/               Public-file privacy check
└── .githooks/             Local pre-commit privacy check
```

## V0.1 outcome

Install through HACS; add HomeCircle in HA; select or create an HA Person for each new member, assign a tracker, and choose Home and additional places. First setup creates a dashboard and card if none exists; the visual editor supports additional cards. No manual YAML is required in the validated storage-mode onboarding flow. Optional direct Life360 trackers and older tracker-only members are supported. The remaining stable-release gates are tracked in the [scope audit](docs/STABLE-SCOPE-AUDIT.md).

MIT licensed. No upstream implementation is copied into the new runtime. Any future code reuse must retain its original license and third-party notices.

The card and authenticated snapshot interface began in beta 4 and have continued through beta 17. See [frontend setup](docs/FRONTEND.md), [beta 16 validation](docs/BETA16-VALIDATION.md), and the [historical milestone 3 validation](docs/MILESTONE-3-VALIDATION.md).

External Life360 family refresh is off by default, including after upgrade. An administrator can enable **Allow Life360 family refresh** in HomeCircle Options after reviewing the saved-account and household-control disclosure in the [setup guide](docs/SETUP.md).
