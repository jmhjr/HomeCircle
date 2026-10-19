# Account-free GSA controls — October 14, 2026

The refusal diagnostics are installed and HomeCircle loaded after the approved
restart. These subsequent controls did not use owner credentials or reopen the
owner's saved session or item records. No additional HA restart was performed.

## Request-body and environment controls

A bounded helper compared a junk body with an SRP-init-shaped plist, using a
reserved nonexistent account and an ephemeral SRP public value. The latter
deliberately omitted machine-authentication data. Both requests received HTTP 503
and HTML from HA. The same controls from the Mac also received 503/HTML. TLS and
hostname verification remained enabled using the installed integration's
fingerprint-checked Apple trust context. Redirects and retries were disabled.

Because that plist omitted machine authentication, it was not a complete sign-in
availability test. It does not establish a global Apple outage or account state.

## Disposable machine-authentication controls

One fresh disposable Android ADI client provisioned successfully using the existing
public library cache. Its single SRP init, again for the reserved nonexistent
account, received HTTP 503/HTML. No password proof or verification request was sent.
Its identity/provisioning state was kept in memory and not exported or saved.

A second disposable client tested the header difference with a stronger control:
the same ephemeral public value, frozen machine-authentication body, account
identifier and other request headers were used twice, changing only the GSA
client-info bundle from Android Music to akd. Both received 503/HTML. The helper
verified equal bodies and other headers before sending the second request, with
a strict two-request cap. Provisioning again completed; no owner data was used.

This comparison did not authenticate an owner account and did not reach MobileMe,
settings, CloudKit, recovery or reports. Its negative result gives no basis to
change the installed GSA label or ask for another unchanged owner login.

## Existing-session route

The earlier selected-item report baseline accepted the original saved credential
and decoded a report. The HomeCircle migration path can copy existing selected
item material and preserve entity identities without a fresh Apple login. Its
preflight validates SDK restoration, rather than making a live report request.
It also changes registry ownership and disables the prototype after copying, so
it must not be launched as an incidental diagnostic.

Before proposing that move, a private selected-item report probe now supports the
configured native profile and the installed source. It restores cached provider
state, blocks provisioning/network activity during header generation, disables
fresh authentication fallback, and permits only bounded selected-item report
requests. Profile changes occur only in the isolated in-memory provider. The
source vault, identities and key files are never saved. After explicit scoped approval, the live check succeeded on October 14: HTTP
200 across five bounded report requests, with a decoded selected-item report.
The report was not classified as within the preceding hour. No source vault
writes, fresh authentication, provisioning or migration occurred.

The probe's synthetic boundary self-test passed. All 15 existing profile and
migration tests passed. The live result now confirms saved-session report compatibility with the
installed profile at the time of this check. It does not prove fresh location
delivery or resolve fresh sign-in/service-grant failures. Private helpers and
results remain outside the release tree.

After separate explicit owner approval, the existing account was migrated through
HomeCircle's options flow on October 14. One account and both existing trackers
were adopted. Registry verification confirmed preserved entity IDs, expected
HomeCircle ownership/unique-ID mapping and unchanged disabled flags. The prototype
entry is disabled, and SHA-256 verification confirmed its original session vault
and key files remain byte-for-byte unchanged. A separate encrypted HomeCircle
copy is now used for polling.

Live HomeCircle diagnostics after the migration reported `connected`, two
available trackers out of two discovered, a successful API poll, and no polling
error. This confirms the migrated runtime's report access; it does not establish
recent physical movement or fresh report delivery. No fresh Apple sign-in or
Keychain recovery was performed. The existing Undo prototype migration option
provides the rollback path while the original prototype and vault remain intact.

## Post-migration freshness check

During the owner's travel check, the Backpack entity remained available with a
report roughly 144 minutes old and no report newer than the migration. A second
scheduled API poll completed successfully; provider diagnostics still reported
connected, both trackers available, and no error. Successful polling therefore
must not be presented as proof of fresh tracking.

Source inspection found that the explicit-key SDK fetch path files all keys as
primary, whereas its rolling-accessory path separates primary and secondary
keys. A private, selected-Backpack-only check routed secondary keys into the
secondary field without changing the selected key window, saved session or
installed code. It was capped at eight report requests with authentication
fallback and provisioning blocked. The actual run used five requests, received
HTTP 200, decoded a report, and found neither a within-hour report nor one newer
than the saved report. No vault writes occurred. This negative result does not
justify deploying a routing change or establish the cause of staleness.

The owner reports a recent update in Apple's Find My app. That comparison is
important, but the exact app status and availability through the queried report
service remain to be distinguished. No live location values were exported by
these diagnostics. Fresh report delivery remains unverified.

## Fresh-setup platform controls after migration

The owner explicitly redirected work to resolving fresh Apple setup. The saved
account migration is a continuity path, not fresh-onboarding acceptance. No owner
password/code request or protected native API call was repeated in these controls.

New account-free edge controls used a junk request body and the installed verified
Apple TLS trust context, with redirects/retries disabled. Installed compact and
spaced Android Music labels both received 503/HTML. The exact spaced Pixel 7 /
Android / akd profile cited upstream also received 503/HTML. A documented Mac /
macOS / akd label received 404 with an empty body. Separating the model and OS
fields gave 503/HTML for Mac-model/Android-OS and 404 for Pixel-model/macOS-OS.
These are observed header-sensitive edge outcomes, not authenticated setup or
proof of Apple's implementation/policy.

A stronger two-request HA control then provisioned a fresh disposable Android
identity using the cached public libraries, froze one CPD, and sent the same SRP
init for a reserved nonexistent account twice. It changed only the client-info
header: installed Android Music received HTTP 503/HTML; the documented Mac label
received HTTP 200 with a decoded GSA response, ec=-80045, hsc=500, and no SRP
challenge. Equal bodies/other headers were verified before the second send.
No password proof, verification, MobileMe, settings, CloudKit, recovery, report
request or owner record was involved; disposable identity state was not saved.

This confirms that changing to the tested Mac label moves this synthetic request
past one refusal but does not establish usable authentication. Conversely,
Android-labelled requests remain blocked in these current controls despite prior
successful owner authentication and upstream Android-workaround reports. The
results do not establish a global Apple outage, exact owner-attempt HTTP status,
or that all Android implementations fail. No production profile change is
justified by them.

The already-completed native Mac tests remain separate evidence: generic AOSKit
returned no required headers, AuthKit returned local Cocoa4099, and the approved
account-scoped getter did not expose a primary account or call AOSKit. None is a
working genuine-native identity control. Third-party wrappers backed by the same
Android ADI provider do not supply that missing comparison merely by running on a
Mac. No private entitlement injection, Apple-process impersonation or system
security changes were attempted.

Fresh setup remains unresolved. Its acceptance gates are successful fresh
GSA/verification, usable Find My report grant, authorized item storage access,
nonempty validated recovery keys, selected-item discovery, and independent report
retrieval. Existing-session polling satisfies neither fresh grant issuance nor
fresh discovery/recovery. Another unchanged owner login or passcode attempt is
not supported by the current controls.

## Native authentication source follow-up

After the owner's instruction to pursue native authentication, a metadata-only
inventory inspected current framework loading, public export names and Objective-C
method signatures without authentication/account calls. No loadable CoreADI
framework or tested C ADI exports were exposed to the current process. The native
AuthKit controller's default connection configuration uses the user service,
correct anisette Mach name and remote/exported interfaces; it does not select the
system service. The system akd service is also loaded and declares that Mach name.

A distinct source-checked helper explicitly selected the system service through
AuthKit's ordinary connection configuration, with no added entitlements or process
identity changes. Exactly one authentication getter call, with provisioning=false,
returned Cocoa4099 and no data/OTP/machine ID. It emitted only boolean presence and
bounded error metadata, captured/discarded native stdout/stderr, and accessed no
account session, vault, Find My key or location. This rules out that tested
connection-context change as a working source; it does not identify the service's
internal rejection check.

A separate minimal client, based on Dadoum/apple-crates adid-proxy and its exact
message constants/encoding, queried only the production realm's provisioning
status through the native adid service. One status RPC returned ADI code -45070.
No token request, account enumeration, provisioning, synchronization or erase
operation was sent. The error leaves provisioning state unknown; it must not be
reported as proof the Mac is unprovisioned. No explicit network request occurred.

An additional compatibility lead used Apple's official iTunes12.8.3 download,
not a third-party binary. The disk image was mounted read-only, the installer
package verified as signed Apple Software, and only its CoreADI framework was
extracted into the ignored private lab. Full-framework strict signature
verification passed for all architectures after extracting the bundle's required
resources/signature files. The initial binary-only verification had lacked those
resources; it was not accepted as verified. No installer or old daemon was run,
no Apple app was patched, and no security setting or entitlement was changed.

Rosetta was already installed. An x86_64 helper loaded this genuine Mac library
and found its dispatcher/version exports. A sandbox blocked network access,
existing user files outside the private native-control folder, writes outside
that folder, and connections to system adid/AuthKit. Additional explicit denies
covered system ADI/Keychain stores before the second compatibility attempt. The
source-based dispatcher ABI/payload test passed with synthetic inputs.
Initialization returned dispatch code -45076, so the normal-order helper stopped
before selecting state or issuing further operations. A separate path-first
attempt returned the same dispatch error and stopped before initialization or
status/token requests. The private state folder remained empty. These errors under
the sandbox do not isolate library compatibility, calling-contract or sandbox
causes; no unrestricted run was used to turn the experiment into a private-data
read. The image was detached afterwards.

The legacy load result is not successful Anisette generation or successful fresh
setup. No owner credentials/codes were used, no GSA/delegate/CloudKit/recovery
request was sent in this native follow-up, and the migrated HA configuration and
vault were not changed. A working native identity comparison and subsequent Find
My grant issuance remain unmeasured.

References: [native adid client](https://github.com/Dadoum/apple-crates/blob/main/adid-proxy/src/lib.rs),
[dispatcher contract](https://github.com/Dadoum/apple-crates/blob/main/adi/src/core_adi.rs),
[official Apple package](https://support.apple.com/en-us/106374).

## Requested original HAtag path retest on the Mac

The owner explicitly requested the previous working login path. Local source
verification identifies it as johncattrall/hatag, forked from thisiscam/export-findmy,
with johncattrall/rustpush pinned to
48afd8a3a7319a2efd10e1f708e525deb2886013. The exporter/key-discovery login is distinct
from the original Python report-service login and from reusing a saved session.

A guarded Mac-native build reused the pinned source and lockfile offline, in a
separate source tree and cloned build cache. Comparison against the retained
October11 main.rs showed only the existing auth-probe switch, rejection of its
combination with enrollment, and an early return immediately after
login_email_pass. The original authentication request/profile/provider code and
original working binary were not replaced. The guards prevent later verification,
MobileMe, Keychain enrollment and item export in this probe.

The first Mac run used a reserved nonexistent account, original SideStore service,
and fresh private temporary identity. It stopped in the Anisette stage before
Apple login. A public service client-info GET subsequently returned HTTP200/JSON;
that public response did not prove provisioning or header generation worked.
A single diagnostic repeat captured only fixed error categories/bounded codes.
This repeat reached Apple authentication and received -80045, with no next-step
marker and no reported TLS failure. The first failure was therefore not evidence
of an enduring total SideStore outage. No owner credentials or saved session,
identity, peer, accessory key or location records were opened; both temporary
identities were removed. New temporary identities were used, so this was not a
retest of fresh authentication under the original saved exporter identity.

This requested old-path test did not restore fresh setup. It independently
reproduced a current Apple authentication refusal on the Mac with the original
pinned login implementation. It does not establish that the device used to type
verification codes caused the earlier failures, nor does it justify an unchanged
owner-password/code attempt or reenrollment.

## Upstream context

The current [OpenTagViewer maintainer discussion](https://github.com/parawanderer/OpenTagViewer/issues/248)
distinguishes the Android GSA workaround from missing Find My service grants,
reports an older session still fetching locations, and does not establish a
fresh-login Find My fix. The discussion's earlier inference that delegate status
1 means an account was never activated was corrected by a later contributor.
These are external reports, not proof of this account's exact refusal cause.
