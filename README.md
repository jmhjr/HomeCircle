# HomeCircle

Development toward **HomeCircle 1.0.0** is tracked in the [1.0 release plan](docs/RELEASE-1.0-PLAN.md). This source branch is preparing unpublished qualification candidate 1.0.0-rc.1; it includes corrections after beta 20 and has no published RC asset yet. The published beta 20 package and its historical validation remain unchanged.

Family location and presence for Home Assistant, independent of the tracking provider.

**Experimental development software — not a stable release.**

Use a test Home Assistant dashboard. Beta 20 hardens polling, native-worker cleanup, recovery safeguards and explicitly selected item identity continuity. It retains optional HA-only Apple Find My, existing HA trackers, Life360, places, pictures and source report times. Background iPhone departure/return and stable release gates remain open. See the [changelog](CHANGELOG.md).

**Status: experimental beta 20 prerelease; stable release gates remain open.** HomeCircle is a working name; public naming remains a release decision.

HomeCircle consumes standard HA `person` and `device_tracker` entities, with optional explicitly selected supporting sensors. Optional direct Life360 and Apple Find My connections use the built in tracker provider contract. Existing HA trackers remain selectable without a HomeCircle provider account.

See [beta 20 validation](docs/BETA20-VALIDATION.md) for the versioned package boundary and remaining acceptance. Historical live Find My proof belongs to [beta 19](docs/BETA19-VALIDATION.md). Earlier features and their release checks are recorded in [beta 18 validation](docs/BETA18-VALIDATION.md).

## Start here

- [First-release checklist](docs/RELEASE-1.0-FIRST-RELEASE-TRACKER.md), [HAOS support target](docs/RELEASE-1.0-SUPPORT-PROPOSAL.md) and [no-contact distribution decision record](docs/RELEASE-1.0-NO-OUTREACH-DECISION.md)
- [First-release user guide](docs/RELEASE-1.0-USER-GUIDE.md), [maintenance and recovery](docs/RELEASE-1.0-MAINTENANCE.md), [privacy/support](docs/RELEASE-1.0-PRIVACY-SUPPORT.md) and [troubleshooting](docs/RELEASE-1.0-TROUBLESHOOTING.md)

- [Per-source report times](docs/PER-SOURCE-REPORTS.md)
- [Beta 16 validation](docs/BETA16-VALIDATION.md), [beta 15 candidate validation](docs/BETA15-CANDIDATE-VALIDATION.md), [current release readiness](docs/CURRENT-RELEASE-READINESS.md), and [earlier direct Life360 validation](docs/DIRECT-LIFE360-CANDIDATE-VALIDATION.md)

- [Step-by-step setup: iPhone, Life360, pets and supporting sensors](docs/SETUP.md)

- [Product and 1.0 scope](docs/PRODUCT.md)
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

## Experimental release

Maintainer: [@jmhjr](https://github.com/jmhjr). Version `v0.1.0-beta.20` is experimental. Use the installable ZIP from [GitHub releases](https://github.com/jmhjr/HomeCircle/releases), then follow [HACS setup](docs/SETUP.md). See [beta 20 validation](docs/BETA20-VALIDATION.md) for the package, inherited evidence and limits.

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

HomeCircle is MIT licensed. Bundled third-party SDK, emulator and frontend components retain their original licenses and notices. See the [Find My runtime provenance](custom_components/homecircle/_findmy_runtime/PROVENANCE.md).

The card and authenticated snapshot interface began in beta 4 and continue in beta 19. See [frontend setup](docs/FRONTEND.md), [beta 16 validation](docs/BETA16-VALIDATION.md), and the [historical milestone 3 validation](docs/MILESTONE-3-VALIDATION.md).

Family location refresh uses explicitly assigned supported trackers and is off by default, including after upgrade. An administrator can enable **Allow family location refresh** in HomeCircle Options after reviewing the saved-account and household-control disclosure in the [setup guide](docs/SETUP.md).

Person cards show **Since** from the selected tracker’s genuine arrival timestamp when supported, or a saved HomeCircle observation of arrival into a named place. Times use Home Assistant’s time zone; earlier days include the date. Missing or mismatched evidence shows **Since unknown**. The tooltip identifies tracker evidence or an observed arrival and any observation gap. This time is separate from the latest tracker report.

**Since after restart:** Genuine Life360 trackers supply their own arrival time, separately from their latest report. Other trackers use a locally saved observed arrival into a configured place. A restart preserves the saved time when the place still matches; the tooltip notes that uninterrupted presence during the gap is unconfirmed. A changed place during the gap remains unknown until a new arrival is observed. Initial unknown times are not fabricated. Changes to saved HomeCircle configuration reset observation checkpoints.

## Direct connections, privacy and licensing

Standard HA People and trackers remain usable without a HomeCircle provider
account. The direct Apple Find My and Life360 connections are optional and
unofficial. Use only accounts and data you are lawfully entitled to access;
HomeCircle does not authorize access to another person's account or location.
Provider names identify compatibility. HomeCircle is not affiliated with or
endorsed by Apple or Life360, and claims no provider approval or logo right.

HomeCircle provides no hosted account relay, telemetry or support-upload
service. Saved account data stays in your Home Assistant installation, subject
to its storage and backup access. Enabled provider connections and optional
map, portrait and city services still make the requests described in
[privacy and support](docs/RELEASE-1.0-PRIVACY-SUPPORT.md). Reports can be stale,
access can be denied and unofficial interfaces can change. Do not rely on
HomeCircle for emergency response or a person's safety.

The source-based HACS package includes Python/protocol source, public
certificates, generated frontend text assets and retained OSS notices. It does
not bundle dependency wheels, native executables/libraries, Apple payloads or a
container image. HA installs declared dependencies separately, and the optional
Find My setup can download its pinned Apple runtime payload locally. The
published OSS grants apply to their covered code; they do not license Apple's
binary or provider services. See the [distribution basis and remaining
maintainer decisions](docs/RELEASE-1.0-DISTRIBUTION-QUESTIONS.md).

The current source candidate implements administrator **Manage direct
connections** with **Pause** and **Resume**, plus account/provider stops after
access denial. Open Options, choose the saved connection and an action; saved
accounts, identities, selections and history are kept. Resume deliberately
allows requests for that provider again, including denied accounts, and does not
reset Find My recovery safeguards. The affected native checks and final RC/HACS
qualification are pending in the [active tracker](docs/RELEASE-1.0-FIRST-RELEASE-TRACKER.md);
source implementation is not a native pass. See the
[decision record](docs/RELEASE-1.0-NO-OUTREACH-DECISION.md). For help, use
[SUPPORT.md](SUPPORT.md) or [private security reporting](SECURITY.md); no raw
account file, backup or diagnostic upload is required.

## Experimental Apple Find My

Beta 19 brings HA-only AirTag reporting into HomeCircle using a pinned MIT Python SDK and a local identity runtime. Setup prepares the runtime before asking for Apple credentials, creates an independent identity for each account, and saves only explicitly selected items in an encrypted account store. Accounts poll independently and items appear in their own category. No Mac, terminal, separate helper or manual YAML is required.

Packaged Apple sign-in, fresh discovery and selection, passwordless restart, and automatic decoded report delivery passed on the tested HA OS Raspberry Pi with two selected items. Broader platform and account coverage remain experimental. Report time and estimated accuracy stay visible because Apple reports can be delayed; new physical movement, current-position freshness and delivery latency have not been proven. See [packaging validation](docs/FINDMY-BETA19-PACKAGING-VALIDATION.md) for evidence and limitations.

The [Find My setup guide](docs/FINDMY-SETUP.md) covers Apple sign-in, trusted-device recovery, item selection, reconnect options and local storage.
