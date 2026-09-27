# HomeCircle

Family location and presence for Home Assistant, independent of the tracking provider.

**Experimental development software — not a stable release.**

Use a disposable or test Home Assistant instance. Published beta 4 passed HACS install, upgrade, removal and reinstall checks, plus initial real-provider and touch-display checks. Beta 5 addresses snapshot retries and unloaded-entry resource cleanup; its published HACS upgrade/removal acceptance is tracked separately. Broader field acceptance remains open. No stable release or production migration is approved.

**Status: milestones 1–3 development integration; development prerelease; not production-ready.** HomeCircle is a working name; public naming remains a release decision. The existing V2 dashboard remains the reference system. Development does not replace, install over, or change it.

HomeCircle consumes standard HA `person` and `device_tracker` entities, with optional explicitly selected supporting sensors. Life360, the Companion app, and other tracking integrations remain independently managed sources. HomeCircle will never require a Life360 account or token.

## Start here

- [Per-source report times](docs/PER-SOURCE-REPORTS.md)
- [Beta 4 release-readiness audit](docs/BETA4-RELEASE-AUDIT.md) and [beta 5 fixes](docs/POST-BETA4-FIXES.md)

- [Step-by-step setup: iPhone, Life360, pets and supporting sensors](docs/SETUP.md)

- [Product and V0.1 boundary](docs/PRODUCT.md)
- [Feature inventory and reference evidence](reference/feature-inventory.md)
- [Architecture](docs/ARCHITECTURE.md) and [ADR-001](docs/adr/ADR-001-provider-independence.md)
- [Roadmap and acceptance gates](docs/ROADMAP.md)
- [Development and Git workflow](docs/DEVELOPMENT.md)
- [Privacy and security](docs/PRIVACY.md)
- [Normalization contract](docs/NORMALIZATION.md)
- [Multiple-tracker switching validation](docs/MULTI-SOURCE-VALIDATION.md)
- [Milestone 2 validation](docs/MILESTONE-2-VALIDATION.md)
- [Milestone 1 validation and limitations](docs/MILESTONE-1-VALIDATION.md)
- [Historical bootstrap validation](docs/BOOTSTRAP-VALIDATION.md)

## Release preparation

Maintainer: [@jmhjr](https://github.com/jmhjr). The repository is public for development review and HACS custom-repository testing. The beta 5 candidate follows [v0.1.0-beta.4](https://github.com/jmhjr/HomeCircle/releases/tag/v0.1.0-beta.4). See [beta 4 validation](docs/BETA4-VALIDATION.md), the [beta 4 release-readiness audit](docs/BETA4-RELEASE-AUDIT.md), [post-beta 4 fixes](docs/POST-BETA4-FIXES.md), and the [historical release preparation record](docs/RELEASE-VALIDATION.md).

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

Install through HACS; add HomeCircle in HA; select people and their associated trackers; choose Home and additional places; add a card through a visual editor. No manual YAML is required in the target onboarding flow. Entity/place selection is implemented for disposable development testing. Presence normalization and household rules are implemented. The card/editor and resource registration are implemented and browser-tested. Remaining release gates are tracked in the validation report.

The reference is **HomeCircle Reference Implementation v1**, frozen from available local V2 artifacts and later extracted-card source. Raw household files are held outside this Git repository in a restricted local snapshot. Public reference files contain generic examples only. See [reference provenance](reference/dashboard/README.md) for the distinction between production V2 and later clone work.

MIT licensed. No upstream implementation is copied into the new runtime. Any future code reuse must retain its original license and third-party notices.

The initial card and authenticated snapshot interface are implemented in development prerelease `0.1.0-beta.4`. See [frontend setup](docs/FRONTEND.md) and [milestone 3 validation](docs/MILESTONE-3-VALIDATION.md). No production rollout is included.
