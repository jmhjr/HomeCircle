# Beta 20 readiness and provenance audit

Reviewed October 20, 2026. This engineering audit reconciles the release record,
checks source origins and notices, and prepares additive corrections. It does
not approve a stable release or determine third-party permission. No owner
credentials, production/V2 configuration or Mac Python were used.

## Exact reviewed release

- Published experimental prerelease: [v0.1.0-beta.20](https://github.com/jmhjr/HomeCircle/releases/tag/v0.1.0-beta.20).
- Source/tag: `d02a9bdb9027cb51c99165a09ba50d5b175f5fb9`, 327 reviewed source files.
- `homecircle.zip`: 112 members, 604,937 bytes, SHA-256
  `fc0b365d9688459504f874af5c38393e24145d657f15f1def8ada9184f363285`.
- Public `inventory.json`: 16,674 bytes, SHA-256
  `5e724f69ff20a711dd87b2a39ed96818781813bb6f1e7b3addedc6e048593d77`.

A fresh public download matched the inventory and member bytes. The ZIP has no
Apple installer/library, Unicorn binary/wheel or font files. Existing FindMy,
OpenTagViewer, emulator and Leaflet notices were independently compared with
pinned upstream text. The GrandSlam omission below is separate from those
successes. The published tag, ZIP and inventory remain immutable.

## Completed evidence and corrected readiness claims

| Completed scope | Evidence | Practical limit |
| --- | --- | --- |
| Exact beta 20 packaging | [39460044306](https://github.com/jmhjr/HomeCircle/actions/runs/39460044306): native amd64 Core 2026.9.4/musl, 1,443 backend passes and one named optional skip, 110 frontend passes, 327-file privacy check, deterministic archive/public-byte comparisons | Synthetic package acceptance; minimum Core does not imply all later versions |
| Genuine HACS release delivery and rollback | [39461573392](https://github.com/jmhjr/HomeCircle/actions/runs/39461573392): native KVM HAOS 18.3, Core/Supervisor 2026.10.2, HACS 2.0.5; eight real release phases and 45 controller contracts | Explicitly selected fictional members, real restarts, preserved identities/settings and served bundle; newest recovery guard preserved manually |
| Active Ubuntu/glibc runtime | [39474571811](https://github.com/jmhjr/HomeCircle/actions/runs/39474571811): Ubuntu 24.04 amd64/glibc 2.39, source-built Python 3.14.6/Core 2026.10.2; 48 harness contracts, native lifecycle, real create/restart, 1,443 backend passes and one named optional skip | One actual target and recorded synthetic paths; QA-derived copies and four earlier failures remain in the [full record](BETA20-GLIBC-VALIDATION.md) |
| Source/dependency notice inventory | [Vendored origins](BETA20-VENDORED-ORIGINS.md) and [dependency inventory](BETA20-DEPENDENCY-INVENTORY.md): pinned origins, 24 observed distributions/six direct requirements, metadata/wheel hashes and bundled Leaflet comparison | Not a full HA/OS or every nested-component license audit; not permission or source-obligation clearance |

[Current readiness](CURRENT-RELEASE-READINESS.md) and the
[stable checklist](STABLE-RELEASE-CHECKLIST.md) now identify beta 20 and distinguish
completed HACS/glibc scopes from remaining work. Older checkpoints and failed
attempts are retained as dated evidence. Earlier frozen-parent backup/recovery
results are not relabelled as exact beta 20 repetitions. Synthetic managed
transport does not establish owner-account, production or physical-display
acceptance. Prepared disabled-entry partial-backup restore does not establish
ordinary enabled-entry or full-system restore.

## Confirmed findings and separate correction

1. **Bundled GrandSlam notice omitted.** Pinned comparisons identify a 13-line
   client-format docstring and a nine-line CBC unpadding/comment block retained
   through FindMy. The corresponding [GrandSlam license](https://github.com/nythepegasus/grandslam/blob/e2321633f493f6c1d9146e8d85ad6d57ba490708/LICENSE)
   is absent from beta 20's SDK notice. The correction appends the exact MIT text
   with its literal unfilled year/name fields and records the parent lineage;
   no author or date is invented. Ownership/permission adequacy remains open.
2. **Fetched Unicorn wheel notice gap.** The inspected `unicorn==2.1.4` wheel
   includes native shared/static libraries without standalone license text.
   Its shared library byte-matches the actual qualified CI library. The
   [bindings metadata](https://github.com/unicorn-engine/unicorn/blob/2.1.4/bindings/python/pyproject.toml)
   says BSD; the [native core](https://github.com/unicorn-engine/unicorn/blob/2.1.4/README.md)
   specifies GPLv2. The candidate supplies the pinned complete `COPYING` as
   supplemental material. Binding attribution, corresponding-source/source-offer
   and combined distribution obligations remain unresolved. No BSD text or
   source offer is invented, and the downloaded wheel itself is not amended.
3. **Fetched pyelftools wheel omits referenced Construct notice.** The inspected
   `pyelftools==0.33` wheel carries Construct code but lacks its referenced MIT
   license. The candidate retains the exact [pinned Construct notice](https://github.com/eliben/pyelftools/blob/v0.33/elftools/construct/LICENSE).
   Final installed-artifact verification and any upstream packaging remedy
   remain open. These two fetched-wheel findings are distinct from bundled
   HomeCircle source: neither dependency binary/code is inside its release ZIP.
4. **Fixture provenance claim became stale.** The verified FindMy 0.10.2 wheel
   notice remains exactly retained at the start of the combined SDK license,
   which now also includes inherited notices. The correction replaces the false
   whole-file equality claim/assertion with exact retained-notice checks. The
   parity fixture, tests and runtime code are unchanged.
5. **Life360 terms pointer became stale.** The scope checklist now points to the
   [official newer terms](https://legal.corp.life360.com/hc/en-us/articles/42963368361239-Life360-Terms-of-Service-2026-8)
   and I.B.10, replacing the earlier 2025.1/III.B.10 current-reference claim.
   The official title says “2026/8” while the page body says updated April 14,
   2026. Both labels are recorded without inventing a different effective date;
   applicability and authorization still need assessment.

The separate [correction commit `9466eef`](https://github.com/jmhjr/HomeCircle/commit/9466eef45ecac16f05f25d4455d705383f7c91ff)
on `codex/beta20-notice-corrections` changes exactly five text files from the
published source. It adds `_findmy_runtime/LICENSE.md`, appends the GrandSlam
notice and provenance, and corrects the fixture provenance document. All
executable, configuration, frontend and fixture bytes remain unchanged.

[Native Linux run 39479412715](https://github.com/jmhjr/HomeCircle/actions/runs/39479412715),
validation revision `a28e669db04ec1972ad87b2fc88538d3c2297b67`, passed on Ubuntu
24.04 x86_64/CPython 3.12.3. The unchanged official collector, archive writer and
inspector built two identical notice-only previews. Only the two generated
frontend files absent from the source tag were seeded from the freshly
SHA-verified published ZIP; npm and the frontend were not rebuilt. Source scope
was 327 to 328 files with five text changes. The preview had 113 package members,
four changed/added notice-document paths and all 109 other members byte-identical
to published beta 20. Complete upstream notice text and fixture-document checks
passed. Preview: 613,863 bytes, SHA-256
`d2106e53249cff8786d74449660d43314f66bf6eb95acbac0fe77c35247937f5`.

The [summary](https://github.com/jmhjr/HomeCircle/blob/35d4c3d184b810694c1bdd66778587f08a6d2e5b/docs/BETA20-NOTICE-CORRECTION-SUMMARY.json) and
[preview inventory](https://github.com/jmhjr/HomeCircle/blob/35d4c3d184b810694c1bdd66778587f08a6d2e5b/docs/BETA20-NOTICE-CORRECTION-INVENTORY.json) are retained in the pinned validation record.
The downloaded two-JSON artifact `12289679595` was 7,302 bytes, SHA-256
`3f719cd0ab11406c670d61cbbe877df5636ad10a135d1940e77757c5ec4b67f1`,
matching GitHub's receipt. Its inventory was independently compared with the
published inventory and all changed candidate files. The preview ZIP was
removed, not uploaded, installed or published. This was packaging validation
with Python only on Linux; it started no Core/provider/Apple runtime and did not
rerun the backend suite. It does not create a new release or resolve the open
permission, source/distribution or eventual installed-notice questions.


## Source and dependency boundaries

HomeCircle-authored source uses its existing MIT notice. Vendored FindMy is
pinned to `7969003ca785658369b650f75d9e7ca519566bf6`; emulator source to
`2096d875dac6b5ed2347a9ae8c39c7251c0d6ed6`; inherited OpenTagViewer text to
`08a59cab551721afb9dc9f829ad31dae8d5bd400`. Fifty-nine downloaded upstream
blobs and all 71 released vendor/runtime members were checked. Adapted files
are identified as adapted, not upstream-identical. Gist ancestry has pinned
revisions but no explicit license in the enumerated source; protocol/format
similarities alone do not determine copied protected expression. Permission or
a documented independent-implementation basis remains a stable gate.

The six manifest requirements are Life360, protobuf, anisette, Unicorn, SRP and
Beautiful Soup. Their observed 24-distribution Linux closure is recorded with
exact versions and primary wheel evidence; ranged constraints can resolve
differently later. `findmy==0.10.2` was a validation reference, not a seventh
manifest requirement. `srp==1.0.22` is separately installed and namespaced, not
vendored equations; its wheel MIT text and conflicting BSD classifier are both
recorded. Anisette's blank metadata is supplemented by its actual MIT notice.
Setuptools' retained nested notices are distinguished from its top-level MIT
metadata. This inventory does not assert every inspected wheel was the exact
artifact installed in CI; Unicorn's native-library match is explicitly stronger.

Leaflet 1.9.4's complete BSD notice matches the lock-integrity-verified npm
archive and is present beside the bundled card. The other 67 non-root lockfile
entries are marked development-only; their inventory is metadata, not an
extracted-license audit. Build/test tools are outside the installable runtime.
Apple's downloaded CoreADI and public trust roots retain separate provenance,
software-license and service-use scope. The complete runtime must not be
described as exclusively MIT.

## External-service review

No account or location requests were made for this audit. The observations below
are source checks and public-policy comparisons, not live deployment clearance.

| Service | Static observation and primary policy | Remaining evidence/decision |
| --- | --- | --- |
| OSM street tiles | Standard tile URL, visible copyright attribution and `strict-origin-when-cross-origin`; no bulk/offline tile downloader or cache-disabling override found in the inspected tile path. [Tile policy](https://operations.osmfoundation.org/policies/tiles/) | Observe actual stable-build browser Referer/cache behavior and deployment use |
| Photon reverse geocoder | Opt-in, identifying HomeCircle user agent, persistent cache, deduplication, five-minute per-member retry, 20 requests/hour, sequential one-second spacing, bounded response/deadline. [Demo-server policy](https://github.com/komoot/photon#demo-server) | Assess deployment scale and availability; request bounds do not guarantee public-service acceptance |
| USGS imagery / IEM radar | Visible source credits in the inspected frontend. [USGS terms](https://www.usgs.gov/faqs/what-are-terms-uselicensing-map-services-and-data-national-map), [IEM terms](https://mesonet.agron.iastate.edu/disclaimer.php) | Confirm visible credits on the final stable display and continued provider/request scope |
| Apple software / iCloud | Runtime provenance pins public installer/library bytes and keeps executables outside the ZIP. [Published iTunes SLA](https://www.apple.com/legal/sla/docs/iTunes.pdf), [iCloud terms](https://www.apple.com/legal/internet-services/icloud/en/terms.html) | Establish the pinned installer's accompanying agreement and assess extraction/emulated use and service authorization. The published SLA's identity with that agreement is unverified; iCloud automation wording sits within an interference provision |
| Life360 | Optional direct/native and external-integration refresh/import paths remain distinct from provider-independent HA entities. [Official newer terms](https://legal.corp.life360.com/hc/en-us/articles/42963368361239-Life360-Terms-of-Service-2026-8) | Record applicable authorization/assessment and stable provider scope; account consent and an open-source client license do not settle service permission |

Raw public-policy evidence, where downloadable, has local dated hashes. The
USGS/Life360 raw HTTP downloads returned 403; their official pages were read
through the web tool, so no raw-content digest is claimed for those two pages.
No external author/provider was contacted. The audit neither establishes
infringement nor certifies permission or legal compliance.

## Remaining stable gates

The next concrete release inputs are: a disposition of the unresolved origin,
software/source/service and public-name questions; the final supported Core,
platform and provider scope; independent cryptographic/format assurance; and
controlled owner sign-in, item discovery and successful recovery without
deliberately consuming bad passcode attempts. Long multi-item, stale-source,
renewal, movement/latency and outage/recovery acceptance remain separate field
work. Fresh production installed-state upgrades, physical-display acceptance,
ordinary enabled-entry/full/add-on/encrypted/cloud restore and any automatic
anti-rollback design are still open. Preserve the newest guard manually under
the validated prepared procedure.

Before a later release, build and identify its own exact candidate and repeat
the checks appropriate to its changes. This audit and notice patch do not
rename beta 20, create a stable version, rewrite its historical evidence or
advance production. The [scope checklist](STABLE-SCOPE-AUDIT.md#licensing-and-service-terms-release-checklist)
records the unresolved dispositions.
