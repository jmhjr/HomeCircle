# No-contact distribution approach and release decision record

Updated October 23, 2026. The maintainer requested implementation without
contacting upstream authors or providers. This records that approach and the
remaining release decisions. It is not a stable-release approval, a permission
letter, a legal opinion or a claim that a lawyer reviewed HomeCircle.

## Chosen implementation scope

Keep the provider-independent Home Assistant People/tracker path and both
optional direct connections. Apple Find My and Life360 are unofficial
connections. Users must use accounts and data they are lawfully entitled to
access. Household consent and account ownership matter, but neither is described
as an Apple or Life360 permission grant.

Distribute the source-based HACS integration ZIP, including its generated
frontend text assets and retained notices. Do not bundle dependency wheels,
native executables/libraries, Apple installer/library payloads, provisioned
identities, account data or a prebuilt container. Home Assistant resolves the
declared dependencies separately. The Find My runtime can download the pinned
Apple payload on the user's installation; this remains disclosed and does not
make that payload open source.

HomeCircle provides no hosted account relay, telemetry or support-upload
service. Credentials and household storage stay in the user's HA installation;
enabled direct providers and optional external map/image/city services still
receive the requests described in [privacy and support](RELEASE-1.0-PRIVACY-SUPPORT.md).
No service is presented as real-time tracking, emergency monitoring or a safety
guarantee. Provider references identify compatibility without claiming
affiliation or endorsement. No provider approval or logo right is asserted.

The current source candidate implements administrator **Manage direct
connections** in Options, with **Connection** (`provider`) and **Action**
(`action`) fields. Choose **Pause** or **Resume**; `connection_status` describes
saved provider state, paused-account count and storage availability without
account identifiers. A successful control save ends the flow without saving a
stale household draft. Pause retains saved accounts, identities, selections and
history and is normally persisted across restart.

Apple access denial stops only that account; healthy Apple siblings can
continue. Life360 denial stops that provider. Resume deliberately allows the
chosen provider again, including accounts paused after denial; it does not
acknowledge a recovery warning, reset its counters or submit a device passcode.
HomeCircle does not retry authentication to work around a denial.

A failed save blocks requests in the current process and returns the fixed
storage error instead of success. Total disk-write failure cannot promise
persistence after that process is lost. Controls cover HomeCircle polling and
its manual/auxiliary requests. Another Life360 integration keeps its own polling
and controls. No hosted remote kill switch is provided.

Affected runtime results must name their exact source and scope in the draft PR validation record. Frozen RC/HACS qualification and maintainer release decisions remain separate in the [active tracker](RELEASE-1.0-FIRST-RELEASE-TRACKER.md). Accepting residual risk does not resolve an
unknown license term or supply missing provider authorization.

## Facts already recorded

| Fact | Evidence and boundary |
| --- | --- |
| The project and retained source components publish OSS grants | HomeCircle's [MIT license](../LICENSE), the [vendored SDK notice](../custom_components/homecircle/_vendor_findmy/LICENSE.md) and the [emulator notice](../custom_components/homecircle/_findmy_runtime/emulator/LICENSE) are retained. The complete existing supplemental notices remain in the source. These grants concern the covered source; they do not license Apple's binary or provider services. |
| The complete GrandSlam MIT text is retained literally | Its [pinned public MIT notice](https://github.com/nythepegasus/grandslam/blob/e2321633f493f6c1d9146e8d85ad6d57ba490708/LICENSE), including unfilled fields, remains in the packaged SDK notice. No names, years or additional terms are invented. The blank fields do not by themselves show that no OSS grant exists. |
| The unused Mac utility and its sole CLI consumer are excluded | [Exclusion record](RELEASE-1.0-LOCAL-MACOS-EXCLUSION.md). This addresses the specifically identified current source/package path; it does not rewrite older archives or claim whole-history clearance. |
| Dependency notices and observed delivery are separately recorded | [Notice witness](RELEASE-1.0-NOTICE-INSTALLATION.md) and [dated distribution observations](RELEASE-1.0-DISTRIBUTION-OBSERVATIONS.json). Complete existing notice text remains unchanged. Final changed-candidate archive/installed checks are still required. |
| The no-contact implementation request is explicit | This October 23 direction replaces mandatory outreach or permission-letter collection as the preparation path. No author/provider contact is required by this plan, and none is represented as having occurred. |
| Prior technical results keep their original scope | Dated AI, package, upgrade and restore records remain unchanged. They do not become legal findings or results for the new Pause/Resume changes. |

## Remaining maintainer release decisions

| Topic | Actual basis and uncertainty to record | Decision status |
| --- | --- | --- |
| Source notices and provenance | Use the published grants and literal notices for covered retained expression. Preserve the documented origin chain and current exclusions; do not invent a missing author's identity or substitute an experimental label for a grant. | Final source/archive checks and explicit maintainer disposition pending. No permission letter is a prerequisite imposed by this plan. |
| Unicorn | Core COPYING is GPLv2. The binding metadata says BSD, but the inspected pinned tree did not supply a standalone binding notice. HomeCircle supplies existing supplemental text and distributes no Unicorn wheel/native library. Separate dependency download and child-process execution do not themselves settle combined-work or source-delivery obligations. | Record the basis for the actual source-only distribution and any accepted residual uncertainty or actual scope restriction. Do not invent BSD terms or assert GPL compliance by checkbox. |
| Apple binary | The pinned iTunes12.8.3 installer and CoreADI slice are identified in [runtime provenance](../custom_components/homecircle/_findmy_runtime/PROVENANCE.md). The exact accompanying agreement has not been established as identical to the separately published iTunes SLA. Extraction/emulated use remains a distinct question. | Record the actual basis, remaining uncertainty and chosen scope before release. No Apple grant or clearance is asserted. |
| Apple/Life360 services | Keep the applicable dated terms and actual login, polling, discovery, import and refresh behavior visible. Account success, low request volume, user consent, a public download and another project's code license do not establish provider authorization. | Record the maintainer's inclusion/restriction/defer decision and residual service risk. Keeping both providers in the candidate is not final release acceptance of these questions. |
| Controls and public scope | Administrator Pause/Resume, stop-on-denial, truthful staleness, local support/privacy and non-affiliation wording must match the shipped behavior. No approval, certification or logo right may be claimed. | Source implementation present; runtime evidence must remain source-bound. Final owner acceptance, RC/HACS qualification and maintainer release approval remain pending. |

A maintainer disposition may identify the factual basis, accept stated residual
uncertainty, restrict an optional path or defer it. It must name the actual
source/artifact, included behavior, evidence and remaining limits. This record
does not choose that final outcome automatically. Further factual research can
continue without outreach. If the current basis is insufficient for the intended
distribution, change the actual scope rather than asserting a grant that is not
in the evidence.

The [distribution questions](RELEASE-1.0-DISTRIBUTION-QUESTIONS.md),
[seven-item tracker](RELEASE-1.0-FIRST-RELEASE-TRACKER.md) and
[release plan](RELEASE-1.0-PLAN.md) carry the remaining technical and maintainer
actions. No stable tag, public RC asset, production upgrade, provider request or
contact follows merely from this document.
