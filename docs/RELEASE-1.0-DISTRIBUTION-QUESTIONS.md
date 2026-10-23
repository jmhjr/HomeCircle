# Distribution basis and remaining maintainer decisions

Updated October 23, 2026. Both optional direct Apple Find My and Life360
connections remain in the candidate. The maintainer requested implementation
without contacting authors or providers. This plan requires no permission
letters, outreach campaign or invented external legal review. It records actual
public grants, notices, distribution facts and unresolved terms questions for a
concrete maintainer scope decision. It supplies no provider permission or legal
clearance. See the [release decision record](RELEASE-1.0-NO-OUTREACH-DECISION.md).

## Source-only delivery and published grants

The source-based HACS integration ZIP includes Python/protocol source, public
certificates, generated frontend text assets and retained notices. No dependency
wheel, native executable/library, Apple payload, container image, account export
or provisioned identity is bundled. HA resolves the declared dependencies
separately. Find My's optional setup can acquire the pinned Apple payload on the
user's installation; the public download and local execution are separate from
the source licenses.

The project [MIT license](../LICENSE), [SDK MIT/inherited notices](../custom_components/homecircle/_vendor_findmy/LICENSE.md),
[emulator MIT notice](../custom_components/homecircle/_findmy_runtime/emulator/LICENSE),
[dependency supplemental notices](../custom_components/homecircle/_findmy_runtime/LICENSE.md)
and the generated packaged `frontend/LEAFLET-LICENSE.txt` remain
available. Use the actual published OSS grants for their covered source and
preserve complete existing notices. Do not invent missing authors, years, BSD
terms or a source offer. A complete source notice is a factual distribution
measure; it does not license Apple's software or service access.

The specifically identified unused Mac record decryptor and sole CLI consumer
are [excluded from the current candidate](RELEASE-1.0-LOCAL-MACOS-EXCLUSION.md).
Their older gist-origin record remains dated history. GrandSlam publishes MIT
permission terms; its literal unfilled notice fields remain preserved rather
than guessed. No claim is made that a blank field automatically voids that grant
or that the exclusion clears the entire repository history.

## Facts, uncertainties and release dispositions

| Topic | Recorded basis | Remaining action |
| --- | --- | --- |
| Retained source and GrandSlam | The existing source/grant inventory and complete inherited notices remain. The unused Mac utility/CLI are excluded. [GrandSlam's pinned MIT notice](https://github.com/nythepegasus/grandslam/blob/e2321633f493f6c1d9146e8d85ad6d57ba490708/LICENSE) is preserved literally. | Verify the changed source/archive retains those notices and exclusions; record the maintainer's source/provenance basis and any residual uncertainty. No author letter is imposed as the only way to proceed. |
| Unicorn | Core COPYING is GPLv2. Binding metadata declares BSD, but the inspected pinned tree had no standalone binding notice; the inspected wheel included native libraries without standalone license members. No Unicorn wheel/native library is distributed by this HACS ZIP. | Record authoritative observed terms and the obligations/basis for this actual source-only delivery, including any remaining combined-work/source-delivery uncertainty. Separate installation and IPC alone do not answer it. Do not fabricate BSD text or mark the issue resolved solely because supplemental COPYING is present. |
| Construct and fetched dependencies | The complete pinned Construct notice is retained as supplemental text. The separately fetched pyelftools0.33 wheel's notice layout remains distinct. | Verify final users can find HomeCircle's retained notices and bind the final dependency inventory to actual installed artifacts. Do not claim that HomeCircle repaired an upstream wheel or that a future binary/container distribution is covered by this source-only decision. |
| Apple binary acquisition | Runtime pins iTunes12.8.3 installer SHA256 `dd08b9967db3e5847955fa168ce880303abf5f36de12abb2061e7ef1a25be214` and CoreADI slice `2eafc3c79c7f41a8afbfbeaaf23ee5dab5ad5bda55ec8e54dbc0ddf1d20ce630`. Neither ships in the integration ZIP. | Record the actual agreement/basis for the exact artifact and extraction/emulated-use scope, or explicitly record remaining uncertainty and the maintainer's scope restriction/acceptance. The separately published iTunes SLA has not been shown to be the pinned installer's agreement. No permission grant or legal conclusion is inferred. |
| Apple/Life360 services | Keep the dated official terms and actual login, polling, recovery/discovery, place-import and refresh behavior visible. Both connections are optional/unofficial. | Record the applicable reading, scope, residual uncertainty and maintainer's include/restrict/defer decision. User consent, account success, low volume or an OSS client license do not supply provider authorization. Mandatory outreach is not the selected implementation path. |
| Controls, privacy and branding | Current guides disclose local storage, no hosted account relay/telemetry/support uploads, separate external requests, stale reports, lawful access, no emergency guarantee and no provider affiliation/endorsement claim. | The source implements Manage direct connections, Pause/Resume and stop-on-denial. Complete affected native checks, reconcile the frozen artifact and record final wordmark/branding scope. No provider approval or logo right is claimed. Preserve actual map/geocoder/weather attribution and request-policy checks. |

Unresolved questions are not closed by checking a box, an experimental label or a
passing test. The maintainer may record a basis with stated residual uncertainty,
restrict an optional path, or defer it. That decision must match the actual
source/package and user disclosures; this document does not make it on the
maintainer's behalf. No stable release or new provider request is authorized by
adding the record.

## Primary reading checked October 22, 2026

- [Unicorn 2.1.4 core COPYING](https://github.com/unicorn-engine/unicorn/blob/2.1.4/COPYING),
  [Python metadata](https://github.com/unicorn-engine/unicorn/blob/2.1.4/bindings/python/pyproject.toml)
  and [bindings provenance](https://github.com/unicorn-engine/unicorn/blob/2.1.4/bindings/python/README.md):
  distinguish the core's license from the binding metadata and actual source
  delivery. Object-code source-delivery alternatives and combined-work scope
  need assessment for the chosen distribution; no source offer is invented.
- [Published iTunes SLA](https://www.apple.com/legal/sla/docs/iTunes.pdf):
  review sections 2.A–B and 3 for use, copying/reverse-engineering exceptions and
  transfer restrictions. Do not invent a blanket Apple-hardware-only condition
  from 2.A. This reading does not establish the exact installer's contract.
- [iCloud terms](https://www.apple.com/legal/internet-services/icloud/en/terms.html):
  review V.B.10 in its interference/disruption context, VI.A–B proprietary-use
  terms and VII.B account termination. VI.A–B are not an explicit standalone
  reverse-engineering clause. Applicability and permission remain questions.
- [Life360 terms labelled 2026/8](https://legal.corp.life360.com/hc/en-us/articles/42963368361239-Life360-Terms-of-Service-2026-8):
  its body says last updated April 14, 2026; retain both labels. Review I.B.10's
  authorized-access restriction, I.B.3's request-volume provision and I.C's
  limited access grant for this actual implementation. No authorization or
  new effective date is inferred.

## Distribution artifacts prepared as evidence

The [machine-readable observations](RELEASE-1.0-DISTRIBUTION-OBSERVATIONS.json) identify the
exact current integration notice members and fresh public dependency metadata.
Unicorn's public source candidate is
[`unicorn-2.1.4.tar.gz`](https://files.pythonhosted.org/packages/b2/1b/b4248aa8422e86de690cf8e85cf8feae4c33405a097d1ebe71570bdaa6f5/unicorn-2.1.4.tar.gz),
2,900,334 bytes, SHA-256
`00567a70e323f749b419cd86bee4f9115beab7ebba32194581c090cbb7c59cff`.
Its URL/digest came from primary PyPI metadata; the source archive was not
downloaded, built, reproduced against a native binary, or asserted to be
complete corresponding source for any proposed binary distribution.

The recorded public Unicorn wheel is 16,436,886 bytes with SHA-256
`9d6e6dea140560de4ebd8446661f7ef84a357d428c14a3ef09dacd306ec8c239`.
Its earlier inspection remains historical and is not asserted to be the exact
wheel installed by the latest native run. No binary, source offer, proprietary
Apple payload or provider credential is added to this packet.

For the final disposition retain the exact source/artifact, actual
runtime/dependency versions, included distribution and service behavior, dated
primary readings, completed checks, remaining uncertainty and maintainer scope
choice. Name any accepted limit or actual exclusion. Keep the technical evidence
and legal/permission conclusions distinct; no permission letter, lawyer review
or certification is represented as having occurred.
