# Find My recovery diagnostics — October 14, 2026

## Deployment requirement — October 15, 2026

The owner requires fresh setup and ongoing operation to run entirely within the
Home Assistant environment, without access to a Mac. Mac UI automation, a native
Mac header broker and a hosted Mac therefore do not meet the requirement.
Their results below are research evidence only, not implementation candidates.
Machine authentication must be generated locally within HA; moving an external
broker to another machine would not satisfy this constraint.

The preserved report connection is an HA-contained runtime baseline. Onboarding
with an entirely new machine identity remains unvalidated: the isolated October
16 test completed verification but stopped at report-credential issuance.
Preserved-identity key recovery is confirmed in the acceptance below. The local candidate uses local
ADI authentication followed by one authenticated account-settings request for a
missing report credential. A successful login, a CloudKit token, or reuse of the
saved report grant does not establish that this candidate can issue a fresh
usable Find My report credential. It must be tested independently of discovery
and without replacing the working connection.

## Opt-in onboarding policy — October 16, 2026

A single HA-only initial-challenge control reached HTTP 200 and Apple status 0
with all five SRP challenge fields present after selecting a Windows AuthKit
client declaration. The Android ADI engine, its independent native identity,
the published FindMy 0.10.2 CPD defaults, serial `0`, account UUIDs and GSA user
agent were retained. No password proof, verification or item access was tested.
Fresh identities and time are confounds; this is evidence for the next stage,
not proof of complete onboarding or a conclusive cause for earlier refusals.

The full setup candidate selects `windows_onboarding_v1` only for an explicit
new sign-in or reconnect. It uses separate declarations for GSA, verification,
delegation, settings, escrow and CloudKit, following the service split reported
in [anisette-v3-server issue 61](https://github.com/Dadoum/anisette-v3-server/issues/61).
Fresh verification completed in the isolated test below, but no usable tracking
grant was obtained. The existing settings
request bundle is retained with its explicit accountsd declaration; later
service stages still need live validation.

The fixed policy marker survives passwordless session serialization. Unmarked
saved report connections keep their existing behavior. Reconnect clones the
saved identity and does not overwrite the original store before explicit item
confirmation. There are no automatic profile fallbacks, password retries or
expired-credential renewals in the selected policy. One post-code SRP
continuation is allowed when Apple accepted verification without a usable PET;
another challenge returns to a bounded user-controlled verification step.
Consumed-code failures end the attempt and close transient authentication.

Acceptance still requires password and server-proof validation, explicit
verification, a usable report grant, read-only key recovery, selected item
confirmation and a fresh report. A successful challenge or unit test alone
does not establish those results.

The selected policy uses direct, verified HTTPS with finite request deadlines,
bounded headers and bodies, and no automatic redirect, cookie, compression or
retry path. Its local provisioning adapter allows one lookup/start/finish batch
with a maximum of three Apple requests. Closing it stops HTTP and refuses later
callbacks. Native VM execution remains in the existing executor: Python cannot
forcibly terminate a stuck native thread, so late workers stay tracked and a
cleanup timeout is an explicit failure. User time at a verification form is
excluded from the per-operation native deadline.

Live acceptance on October 16 succeeded for reconnecting the existing account:
the owner entered credentials in HA, the flow reached item selection, and the
same two saved items were confirmed. The reloaded provider reported connected,
two available trackers, a post-save API success and no error. Thus the new
credential works for report requests with the preserved item keys. This does
not yet establish fresh item-key recovery or guarantee a newer location report.
The final source passed 729 offline tests, lint, the public-file scan and HA's
configuration check before restart. A public-code rollback copy was retained.

The subsequent owner-driven Discover test also succeeded, using the preserved
machine identity and a new transient recovery client. Sign-in reached the
trusted-device picker only after zone access and recovery-record listing passed.
The owner selected a device and submitted its unlock passcode directly in HA.
The guarded flow then reached a freshly discovered item list, which requires
nonempty newly recovered keys; saved item keys are not an unlock fallback.
The same two existing items were selected and saved. After reload, diagnostics
again showed connected, two available trackers, a newer API-success timestamp
and no error. This validates recovery, discovery, encrypted persistence and
report requests for this account within HA, without a Mac or new Keychain-peer
enrollment. It does not validate a completely new machine identity or guarantee
newer physical-location reports. Only screenshots and allowlisted health flags
were retained for this test; passwords, passcodes, raw keys and locations were
not exported.

## Fresh identity and restart control — October 16, 2026

An isolated diagnostic used `FindMySetup.create(..., session=None,
onboarding=True)` after verifying that its pinned public library cache contains
only libraries, with no saved device or account state. It confirmed empty native
provider state before starting. It opened no existing HomeCircle account store,
created no configuration entry and retained no session, recovery key or location.
Twenty focused synthetic tests, lint, independent source review and HA's
configuration check passed before this separate diagnostic was loaded.

The owner entered credentials and a trusted-device verification code directly in
HA. The flow passed the initial challenge and completed the verification and
MobileMe delegation path, but no `searchPartyToken` was present. Its one
authenticated account-settings request returned HTTP 401. The settings body was
not parsed, so the absent settings-token/status diagnostic is not evidence of a
tokenless successful settings reply. Setup stopped before recovery records,
device unlock passcodes, item discovery or report queries. Its one-attempt guard
remains spent. Only fixed result flags and an allowlisted existing log warning
were collected; no further authentication request was made for analysis.

The reported stage `verification` includes the post-verification grant check.
It does not mean the verification code was rejected. The retained flags do not
establish whether the verification header-PET path or an SRP continuation ran.

The same HA restart separately restored the working production connection. An
automatic API success occurred after startup, followed by a later scheduled
success; both saved trackers remained available, with no provider error. Their
source report timestamps did not advance during this observation. This confirms
restart recovery and continued polling of the saved connection, not newer
physical-location delivery or persistence of the isolated fresh client.

Reference transports preserve authentication cookies across SRP and verification,
whereas the bounded onboarding transport currently discards them. This is a
source-backed compatibility difference, not a confirmed cause of the 401. The
OpenTagViewer authentication notes also support direct completion from a
verification header PET, while the published FindMy SDK always repeats SRP;
neither difference should be changed simultaneously in the next control. The
next candidate preserves bounded, instance-only authentication cookies in RAM
while leaving the current verification path and endpoint profiles fixed.

That isolated cookie control passed 32 transport tests and 26 HA flow tests,
lint and independent reviews. Its separate component passed HA's configuration
check. Cookies are limited to the existing GSA, verification, delegation and
settings routes, with separate Apple/iCloud domain families, a 15-minute lifetime
and finite jar/header budgets. Closing or cancelling clears its RAM jar and
refuses late repopulation. It does not change native provisioning, separate
recovery clients, saved report clients or production source. Its new guard does
not reset the first control's spent guard.

The new control records fixed token-source/continuation, credential-presence,
HTTP-status and cookie-count diagnostics before recovery can reset them. It
exports no cookie names/values, raw headers, account identifiers or credentials.
The consent switch is initially off. A new owner-driven live test is required;
offline checks do not establish fresh report access or cookie causality. New
machine material, time and server state remain confounds in a fresh control.

The owner subsequently ran that cookie control. Code validation returned HTTP
200; the flow used the response-header PET, with zero post-code SRP
continuations. Delegation supplied nonempty MME and CloudKit credentials but no
Search Party credential, and the settings request again returned HTTP 401. The
account transport received zero `Set-Cookie` headers across its two initial SRP
requests, one trusted-device validation, one delegation and one settings request.
It therefore had no cookies to preserve or replay in this observed path; cookie
discarding cannot explain this attempt. This does not establish that every Apple
authentication path is cookie-free. Its RAM jar was confirmed empty and stopped
after cleanup. Recovery and item report queries were not attempted, neither old
store nor guard was changed, and no further Apple request was made for analysis.

The now-confirmed header-PET path makes the published SDK's post-code SRP
sequence a focused next control. It must keep the same client profiles and
transport, retain the pre-validation account context, allow only one bounded
continuation and stop if another challenge is returned. It must never fall back
to the withheld header PET after an SRP refusal or invalid proof. This remains an
alternative protocol test, not an established fix for credential issuance.

The separate post-code SRP controller passed 48 helper tests and 32 real HA
flow-manager tests, lint and independent review. Its eight deployed files match
the frozen candidate, while all thirteen production files and both prior test
guards remain unchanged. HA's configuration check passed. The new flow is left
unstarted so the owner can launch it from the iPhone; its consent switch defaults
to off. It allows at most two extra GSA requests for one SRP continuation. Apple
may push another code with a new challenge, but the test stops before HomeCircle
separately requests another code. No live acceptance is claimed for this control.

The owner ran that control from the iPhone on October 17. Verification returned
HTTP 200, and the one post-code SRP continuation completed successfully with a
verified SRP PET and matching account identity. The header PET was deliberately
withheld. The account made four SRP requests in total, then one delegation and
one settings request. Delegation again supplied MME and CloudKit credentials
without a Search Party credential; settings returned HTTP 401. No authentication
cookies were received. Recovery, selected-item access and persistence were never
reached; transient clients and hooks were closed and both earlier guards remained
unchanged. No additional Apple request was made to analyze the retained flags.

This result shows that skipping post-code SRP is not a sufficient explanation for
the failed fresh grant. It does not identify why delegation omitted that grant or
why the settings request was refused. The abort screen incorrectly said post-code
authentication stopped: its static text conflicted with the successful retained
continuation flags. The authorization failure itself was correctly classified.
The diagnostic source now selects fixed wording from that outcome; 37 HA flow
tests include formatting both actual translation resources for successful SRP,
repeat challenges, failed SRP and absent telemetry. This wording correction is
not deployed and does not change authentication or the completed test evidence.

Source comparison identifies a separate untested variable: the original SDK
constructed a fresh local provider using Anisette's default native declaration,
whereas the current fresh onboarding branch explicitly selects a newer model,
OS and application declaration. A restored provider need not follow the same
creation branch. Comparing the original native declaration while keeping the
bounded loader, TLS, endpoint policies, independent IDs, serial, cookies and
post-code SRP fixed is a targeted next control. It would test a public recipe
difference, not establish an identity-age or trust explanation. No protected
saved identity was inspected to infer its historical configuration.
An isolated helper for this comparison passed 37 offline tests, lint and
independent review. Tests use the real configuration and request composers with
fake engines: the original declaration is the sole provider change, GSA request
composition stays fixed, and the current TLS and provisioning gate remain
selected. It is source-only, with no new flow, deployment or live request. A
future controller still needs a new consent and one-attempt lifecycle.

The separate original-provisioning controller subsequently passed 43 real HA
flow tests, two reference-release lifecycle tests and 48 settings-observer tests,
lint and independent review. Its only intended protocol change from the completed
SRP control is the native declaration. A passive observer adds fixed format,
authentication-challenge and bounded plist-status categories from the existing
settings response; it sends no extra request and exports no raw response data.
Ten frozen component files were deployed while the thirteen production files and
six earlier guard/result files retained their hashes. The new guard is separate,
consent defaults to off, and the owner starts it from the iPhone. No fresh-grant
success is claimed before that owner-driven test.
HA's configuration check and restart both completed with exit zero. The existing
connection recovered with two available trackers, a post-restart API success and
no provider error. The new integration was verified in the picker without
starting its flow; its storage directory remained absent. These deployment
checks establish readiness for the iPhone test, not fresh credential issuance or
newer physical-location delivery.

The owner then ran the original-provisioning control. The original native
declaration remained selected, verification returned HTTP 200 and the one
post-code SRP continuation authenticated with a verified PET and matching
identity. Delegation again returned MME and CloudKit credentials without Search
Party access. The single settings response was HTTP 401: a 901-byte plist whose
localized error classified as unauthorized, with no HTTP authentication
challenge scheme or bounded top-level numeric status. This was an application
rejection response from that settings endpoint; it does not establish why the
credential was refused. No cookies were issued. The native references were
released after closure, both other cleanup checks passed, and recovery/item
access were never reached. No extra request was made for retained-result analysis.

The original native declaration alone did not resolve fresh report-credential
issuance. CloudKit token presence is still distinct from CloudKit acceptance:
the report guard runs before container initialization or zone access. Thus the
settings HTTP 401 is not evidence of a CloudKit API HTTP 401. The next useful
read-only control would separately initialize the SearchParty container and
retrieve the named BeaconStore zone metadata using the existing transient MME
and CloudKit pair, with at most two requests and no recovery, device passcode,
enrollment, announcement, item records, location query or saved session. Search
Party remains mandatory before report polling or persistence.

Historical ordering deserves care: the original prototype ran Rust recovery,
Keychain enrollment and item export before a separate Python report login.
That chronology does not prove enrollment created the report grant. The retained
upstream sequence already observed Search Party in delegation before recovery,
and the exporter later omitted device announcement. There is no demonstrated
missing post-recovery token-minting step to justify adding those mutations.

## Isolated HA-only check — October 15, 2026

The first owner attempt in the private HA-only check stopped at Apple sign-in
with HTTP 503. Verification, delegation and the account-settings candidate were
not reached. No account/session was saved or item accessed. The initial check
did not preserve the exact GSA init/complete phase, so its absence must not be
replaced by an inferred password verdict or a claim of a general Apple outage.

Two subsequent account-free requests from HA used the same public Android
client profile and a fixed invalid body, without account details, ADI data or
provisioning. Both identity and gzip negotiation returned HTTP 503 and HTML.
Thus this refusal is reproducible without owner credentials; changing that
compression header alone did not open the public route. Earlier local evidence
had already shown this profile-level refusal, and should have been checked
before asking the owner to repeat sign-in.

The private check now tests this public route once after consent and before
showing credential fields. Only the known 401/404 invalid-body responses allow
the diagnostic sign-in to proceed; unexpected responses stop with a bounded
HTTP result and an explicit statement that no account sign-in was attempted.
Passing this route check would not establish authentication, credential issuance,
item recovery or report access. Passive sign-in diagnostics now retain only a
fixed init/complete phase, response-kind category and bounded retry delay, and
clear prior HTTP status before a new request. No automatic owner retry was added.

Validation: 71 offline tests, Ruff and the public-file privacy guard passed.
Private probe version 0.0.2 was installed and HA's configuration check passed.
After restart, the live HA flow's public check returned 503 and stopped before
credential entry. Its completed flow was closed. Existing HomeCircle source
hashes were unchanged; no saved account material was opened or modified by
these account-free checks.

The original HomeCircle connection remains separate. Fresh HA-only setup and
the proposed account-settings source of report credentials remain unverified.

## Public endpoint and HTTP protocol controls — October 15, 2026

The next investigation used no owner account, saved session, ADI initialization,
provisioning or Find My data. The standalone controls ran inside HA's Terminal
add-on, with HTTPX/HTTP2 dependencies in a separate scratch environment; Core's
packages and the installed integration were not changed.

An account-free public lookup following the header shape in
[xtool PR348](https://github.com/xtool-org/xtool/pull/348) returned HTTP 200 and a
valid URL bag. Its `gsService` was the existing fixed GSA endpoint, and the start
and finish provisioning targets matched the existing GSA guard. No returned URL
was followed. This result provides no identified endpoint correction for the
current sign-in refusal. The lookup descriptor is public protocol metadata, not
a Mac-native authentication source or a proposed Mac dependency.

Two HTTPX controls used identical public Android headers and the fixed invalid
body, with new verified TLS contexts/connections, no proxies/cookies/redirects
or retries, bounded reads and 15-second process deadlines. Actual HTTP/1.1
returned HTTP 503/HTML. Forced HTTP/2 failed before an HTTP status or negotiated
response version was available; it did not demonstrate an accepted route. A
subsequent verified TLS-only handshake advertised `h2` and `http/1.1`; Apple
selected HTTP/1.1. That handshake sent no HTTP request. HTTP/2 therefore supplies
no demonstrated fix on this endpoint/network path, and the failure is not
specific to aiohttp alone.

Source comparison found no missing CPD platform/client-info field in SideSign or
xtool: those clients put client-info in the outer HTTP header. PR348's additional
ADI resync is triggered by a parsed GSA `hsc=434` response carrying server
intermediate metadata; the current bare HTTP 503 provides no such signal and
does not justify resync, fresh provisioning or another owner sign-in.

No fresh credential issuance, item-storage access or report retrieval was tested
by these public controls. The working saved tracking connection remains separate.

Validation: the combined private component and public-control suite passed 104
offline tests. Ruff and the public-file privacy guard passed. This count includes
the actual HA flow tests; `unittest` discovery alone does not collect those
pytest-style cases. The installed private component remains version 0.0.2.

## Windows-library backend candidate — October 15, 2026

A different authentication-library origin is now a concrete research candidate.
[AltServer-Linux PR1](https://github.com/hinatamaxxx/AltServer-Linux/pull/1) loads
Apple's actual Windows iCloud libraries under Wine. This differs from changing a
Windows client header over Android-generated authentication data. The upstream
Find My discussion does not document Windows-library provenance well enough to
establish that the genuine Windows-library route has already been ruled out.

The PR's reported successful AltStore refresh used an established environment.
Its clean-state test reached authentication initialization only. Neither result
establishes SearchParty credential issuance or Find My access. Its unmodified
amd64 Wine32 packaging and Windows export preparation do not meet this project's
HA ARM64 requirement.

Static inspection has removed the need for a Windows computer to obtain the two
version-specific libraries. The Apple installer linked in
[AltServer's source](https://github.com/rileytestut/AltServer-Windows/blob/bd3d7abc58abf6bd332ed256d15307839e498711/AltServer/AltServerApp.cpp#L1929)
contains the required `iCloud_main.dll` 261.7.0.49 with the PR's exact SHA-256.
The later installer linked by
[AltStore's documentation](https://faq.altstore.io/altstore-classic/how-to-install-altstore-windows)
contains the exact required CoreADI 4.17 artifact. The earlier CoreADI has the
same version number but a different hash; version checks alone are insufficient.
The candidate therefore needs the earlier full runtime trees with the verified
later CoreADI replacement, as in the PR's exporter. Both installers were fetched
from Apple over verified HTTPS without redirects and decoded as archives. No
Apple installer or DLL was executed, no identity was provisioned, and no owner
credential, session, item or location was accessed.

[Hangover](https://github.com/AndreRH/hangover) supplies a possible native ARM64
Wine/WoW64 execution path for the PE32 helper, without a Mac/Windows host or global
binary-format registration. A private loader-only candidate has been prepared;
its purpose is to test library loading and exports, before any authentication
function. Static file matching is not a runtime compatibility result. Full MSI
directory/resource mapping, dependency verification, native network-denial tests,
an image build and an actual HA loader run remain acceptance gates.

The HA Terminal add-on reported 1,853,014,016 bytes free on its `/data` filesystem
and about 1.9 GiB of available memory before any build. Bounded public HTTP range
reads of the Hangover release tar's Debian control records found that
`hangover-wine` alone declares 2,429,734 KiB installed (about 2.3 GiB), exceeding
that free space before other dependencies. These were metadata reads, without
executing any release code or downloading/verifying the complete tar; a future
build must still verify the pinned full-archive SHA-256. Total image/build
scratch usage remains unmeasured. No image build or add-on installation was
started. This is a storage block for this candidate, not evidence of an ARM64
incompatibility or an explanation for the earlier Apple HTTP 503. The existing
saved tracking connection remains separate.

The static inspector passed six synthetic tests. The separate loader candidate
passed 29 synthetic tests and independent source review, including the actual
HA option-file permission correction: Supervisor's root-only mode file is read
with strict bounds, then all user/group IDs are dropped before runtime access.
These checks do not compile or execute its native filter or Windows helper.
Ruff and the public-file privacy guard passed. No owner retry or deployment of
the Windows candidate was performed.

## Initial recovery correction

The setup adapter previously ignored the SDK unlock return value. An empty key
list could therefore set `keys_recovered` and advance to accessory discovery.
The adapter now rejects an empty result, keeps recovery incomplete and records
only a boolean key-presence diagnostic. A nonempty list establishes presence,
not cryptographic validity or authorization to Find My storage.

The existing account-settings request now records whether its response contains
a nonempty string Search Party token. This does not import or persist that token,
overwrite an existing report session, or issue an additional request. A new
settings attempt clears the prior observation before sending its request.

Validation: 528 HomeCircle tests and 873 SDK tests passed. The SDK suite emitted
five existing dependency deprecation warnings. Ruff and the public-file privacy
guard passed. These are local changes; no deployment or Home Assistant restart
was performed as part of this correction.

A private selected-item report baseline probe has also been prepared and tested
with synthetic inputs. Its live execution is pending the protected-data scope
confirmation. It requires an existing encrypted session, item keys and cached
local provisioning/library data. It blocks provisioning network activity and
authentication fallback, restricts report requests to the fixed report endpoint,
disables redirects/retries, and caps requests at eight batches. It emits status
and report-presence/recency flags, without coordinates or exact timestamps.
Source vault files are never saved. No protected vault was opened for preparation.

This correction does not resolve or establish the cause of the observed storage
authorization failure.

## Fresh setup must hold a report credential

A completed Apple password/verification exchange is insufficient to save a
working connection. The fresh setup adapter now checks for a nonempty Search
Party report credential before selected-item persistence, and rejects a
serialized credential that differs from the one held by the transient account.
Missing report access ends that attempt with a fixed message instead of sending
the owner back to a verification-code or device-passcode field. The existing
connection is not replaced by this failure.

The authenticated account-settings response is now a second credential source,
separate from MobileMe delegation. When the fresh delegate lacks report access,
setup makes one settings request with retries and redirects disabled. The shared
parser validates HTTP success, service status and any returned account identity
before importing a missing Search Party credential. It preserves an existing
valid report credential and reuses the same response for CloudKit acquisition.
It does not repeat this request later in that delegation. The account-identity
guard runs before this hop.

This acquisition path has passed synthetic tests and independent source review;
Apple has not yet been observed issuing a live usable grant through it. Neither
a nonempty token nor HTTP 200 alone proves that a selected item's report can be
fetched and decrypted. The complete HomeCircle suite passed 609 tests after the
change; the privacy guard passed without changing its rules.

These source changes are not deployed acceptance of fresh Apple onboarding.

## Approved saved-session baseline

After explicit scope approval, the selected-item baseline ran against the
original prototype's encrypted saved session. Exact-name selection first stopped
locally with zero requests; matching the selected item's full name then succeeded.
Apple returned HTTP 200 over five bounded report requests, and the selected item's
report was decoded. The report-within-the-last-hour flag was false. Coordinates,
exact timestamps, raw identifiers, keys and credentials were not emitted or saved.
No new authentication, provisioning request, CloudKit request or source-vault save
was performed by the probe.

This establishes that the preserved report credential and selected accessory keys
remain usable today. It does not prove recent location delivery, fresh token
issuance, or access to the CloudKit storage used by recovery. The experiment used
the replacement report decoder/transport with the original saved material; it was
not an unchanged execution of the original installed polling client.

The next investigation should focus on fresh service-token issuance/storage access
without discarding this working saved-session capability or requesting another
device passcode merely to repeat the same failing path.

## Native authentication capability — October 15, 2026

One explicitly approved account-scoped AOSKit call completed on the current
macOS 27.2 host. The framework and method were available, the supplied account
identifier was accepted by the helper, and the call returned without an
Objective-C exception. Neither recognized OTP nor machine-ID header was present.
This establishes that this exact invocation cannot supply the native credentials
needed by the proposed route; it does not establish why they were absent or
whether another native interface or host could succeed. The original encrypted
vault and key passed their before/after hash checks. No new login, explicit
network request, account enumeration or Home Assistant change was made.

The first wrapper attempt stopped before launching the helper because a rebuild
had left the executable with broader permissions than the wrapper permits. The
permission was corrected before the single native call. The wrapper now checks
the executable before opening the vault, distinguishes fixed local failure
categories, and preserves uncertainty if a launched child's result cannot be
validated. Twenty synthetic parser, transport and preservation tests pass.

New contributor experiments independently report fresh Search Party token
issuance and successful report retrieval using genuine native Mac authentication
headers. One used an older Intel Mac; another used an Apple Silicon Mac on
macOS 26.4. The latter also reports no headers from one macOS 27.0.1 host, but
that single-host comparison does not establish an operating-system cause.
These are [upstream experimental reports](https://github.com/parawanderer/OpenTagViewer/issues/248#issuecomment-6186435577),
not successful local onboarding. They report that the same native header source
must accompany report requests; replacing it with Android Anisette was rejected.

The researched native broker would need to preserve the Mac's own identity
through sign-in, delegation and report fetching. It could not pass through the
current Android profile override or assume that copying a token alone is
sufficient. This route is now outside the owner's deployment requirement.
Fresh credential issuance, usable report retrieval and fresh accessory discovery
remain separate acceptance checks for any HA-contained replacement.

## Independent CloudKit metadata diagnostic — October 17, 2026

The isolated `homecircle_cloudkit_check` component is staged in the HA config
and is visible in the post-restart integration picker; it has not been run. It preserves the last original-provisioning
control's authentication path and replaces its report-access gate only within
the diagnostic instance. After sign-in it requires both existing MME and
CloudKit delegates before attempting the Find My container and a named
`BeaconStore` zone-metadata request. It does not invoke the settings fallback,
refresh a missing CloudKit token, recover keys, enroll, read item records, query
locations, or save an account connection. Every outcome terminates the flow.

The instance transport allows only the two exact metadata endpoints in order,
with retries and redirects disabled. Successful metadata access requires a
container user identifier, an explicit SUCCESS operation result, the named
zone, and transport closure. HTTP 200 alone, an absent operation result, or a
PARTIAL result is insufficient. Private response values remain transient; the
persistent diagnostic schema accepts fixed categories, flags, and bounded
numeric statuses only. A separate exclusive submission marker prevents reuse.

Twenty-five synthetic tests pass, including the real SDK's container and zone
wire construction and the HA flow manager's terminal and forbidden-route
behavior. Ruff passes. Installation hash checks confirmed all 86 production
source assets and eight earlier diagnostic marker/result files unchanged.
No new Apple requests were made during preparation. HA Core configuration
validation passed. The restart was requested, HA reconnected, and the diagnostic
appeared in the integration picker while other integrations continued startup.
The earlier browser block affected a failed tab; the existing HA sidebar opened
the terminal successfully. No flow was started in the browser: the owner will
open it on their phone. Owner sign-in and live metadata results remain pending.
Metadata success would still not establish SearchParty report authorization
or completed onboarding.

The owner completed this isolated metadata attempt on their phone. Verification
returned HTTP 200, post-code SRP authenticated with matching identity, and MME
and CloudKit delegates were present; the SearchParty delegate was absent.
The single CloudKit container request returned HTTP 401. No zone request or
settings fallback ran, and transport/helper cleanup flags passed. This refutes
a settings-gate-only explanation for this attempt; it does not distinguish a
credential rejection from request identity, entitlement or policy differences.
The next source comparison is the current Windows accountsd delegate declaration
versus the published SDK's native accountsd declaration, keeping the other
stages fixed. No further Apple requests were made during result analysis.

## Upstream account/device onboarding comparison — October 17, 2026

The owner requested installation of `malmeloo/hass-FindMy` and observation of
its onboarding. Upstream HEAD matched the previously researched public commit
`b2e678516bfa76e1663605cadba1a802ae0a2cdc`, pinned to FindMy 0.10.2. The earlier
non-persisting comparison component was backed up before replacing its code.
Upstream source is retained except for passive onboarding observation and
omission of the password field from the serialized account entry. Login, 2FA,
Anisette and delegate requests retain the SDK's original implementations and
arguments. Successful account onboarding saves the normal session in HA.

The observer records bounded numeric GSA/HTTP statuses, fixed flow stages,
login state and token-presence booleans in `.storage/findmy_onboarding_observation`.
It does not retain submitted inputs, email, passwords, verification codes,
headers, machine-authentication fields, session values, keys or locations.
Sensitive SDK and flow logging is disabled rather than enabling debug traces.
The diagnostic list is capped at 128 events. Eleven synthetic checks cover the
HA initial menu, upstream call/response forwarding, failed telemetry, privacy
and session persistence with password omission. Ruff passes.

This integration separates Apple account setup from importing tracker key files.
It does not itself retrieve official AirTag keys from Apple during account
onboarding. An account entry alone also does not prove a report credential is
present; the observer separately checks that flag. No tracker key import or
protected account-store read was performed during preparation, and the owner
will start the account flow on their phone after HA preflight/restart.

HA Core configuration validation subsequently passed, HA reconnected after the
requested restart, and the integration picker showed `FindMy` separately from
`HomeCircle Find My Prototype`. No browser flow was started. Owner handoff:
open Add integration, choose FindMy, then Apple Account, and leave the optional
remote Anisette URL empty to exercise the integrated provider. Live onboarding
and tracker-key import remain unverified.

The first owner-driven upstream account attempt returned HTTP 200 with GSA
initial-challenge status -80045. No password-proof operation followed; the
account remained LOGGED_OUT. Upstream displayed its generic invalid-auth
message. This response does not establish an incorrect password. No 2FA,
delegation, tracker-key import or account creation was reached. The observer
recorded only the bounded status/stage schema; no new request was made during
analysis. Separating key import remains viable structurally, but it cannot
resolve this earlier account-authentication rejection by itself.

## Hybrid authentication with separate key import — October 17, 2026

The owner authorized combining the HomeCircle login path with upstream's
separate tracker-key import. The isolated FindMy flow now constructs a fresh
HomeCircle account with its Windows GSA/verification policy, the previously
verified original native-provisioning declaration, and the post-code SRP
control. Only the outbound service-delegate client-info declaration is replaced
with the upstream Mac accountsd declaration. Other headers, payload and IDs are
forwarded unchanged. No global HomeCircle policy or working account is changed.

The flow calls authentication and delegation directly, bypassing recovery and
settings fallback. It refuses another verification challenge, requires a
nonempty SearchParty report token before saving, and checks that the serialized
account round-trips through upstream FindMy 0.10.2 in memory. UUIDs, login data
and provisioning state must survive that comparison; non-default provider
identities or serials are rejected. The password is omitted. This proves format
compatibility only, not actual report authorization: no key import or report
query occurs during onboarding. Authentication alone still cannot finish setup.

A new exclusive `.storage/findmy_hybrid_attempt.json` marker permits one login
submission. No prior guard is reset. Status observations remain value-free in
the existing bounded trace. The earlier upstream rejection and source component
were archived before deployment. Nineteen offline checks pass, including the
actual upstream session roundtrip, missing-token and failed-roundtrip refusal,
verification continuation behavior, delegate-only header replacement, marker
exclusivity and cleanup on helper failure. Ruff and the public-file privacy
check pass. All 85 checked HomeCircle source assets were unchanged by deployment.
No existing account store, tracker keys or locations were accessed.

The hybrid's HA configuration check passed. HA reconnected after restart and
FindMy appeared in the integration picker. The new attempt marker was still
absent and all 20 staged component files matched the validated source. No
browser flow was started and no new Apple account requests were made during
preparation. The owner must close the old login and start a fresh FindMy Apple
Account flow on their phone; live token issuance and actual report access remain
unverified.

The first owner-driven hybrid attempt returned GSA HTTP 200 with initial
challenge status -90010, rather than upstream's earlier -80045. No password
proof, verification or delegate exchange ran. Thus the upstream Mac delegate
declaration remains untested by this attempt. All deployed component hashes
matched the tested source, and the transient account closed. No account or
tracker key was saved. The numeric code's meaning is unestablished; the retained
trace contains no accompanying Apple status text/subcode, so password failure,
throttling or any other specific cause cannot be concluded. No guard was reset
or new Apple request submitted during analysis.

## Initial-challenge comparison and bounded status capture — October 17, 2026

All 13 core files matched the deployment freeze used by the control that
completed verification; all three copied authentication helpers matched that
control byte for byte. A synthetic comparison through the actual GSA request
builder confirmed equal URL, headers, body, request options and return data
through the hybrid observer for identical inputs. This is source/request-builder
equivalence, not equality of actual historical credentials, machine state,
request times or Apple decisions. No historical raw request was replayed.

The observer now classifies Status `ec`, `hsc`, `sc`, `subcode`, bounded retry
seconds, challenge field shape and fixed categories for known status messages.
Unrecognized text is retained only as a category and bounded length, never raw
text. Parsing is capped at 64 KiB. The response remains unchanged for its caller.

A separate FindMy menu item, **Initial challenge diagnostics**, accepts only the
owner's Apple email. It prepares the same fresh native/GSA path and issues one
initial challenge using the original SRP public-value construction. Its transport
independently rejects password-proof, verification, delegate and repeated
requests. Even an accepted challenge terminates without a password proof. The
new `.storage/findmy_initial_status_attempt.json` guard is separate; the spent
hybrid guard was verified unchanged. Anonymous provisioning may precede the one
account request. No account, provisioning state, item keys or locations are saved.
Thirty-one offline checks, Ruff and the public-file privacy check pass. The
owner starts the next diagnostic on their phone after HA preflight/restart.

HA configuration validation passed for the initial-only diagnostic. HA
reconnected after restart and FindMy appeared in the picker. Deployed source
hashes and the earlier hybrid guard were rechecked unchanged, and the new
initial-only guard was absent. No browser flow or Apple account request was
started during preparation. Live status metadata remains pending owner input.


### Owner result and a new request-format lead

The owner-driven initial-only test returned HTTP 200, Status ec -90010 and hsc
200. All SRP challenge fields were absent. There was no retry interval or numeric
subcode. The temporary account closed; no password proof, verification or
delegation ran. The diagnostic guard is now spent and was not reset.

Apple supplied a 45-character message which the exact-match classifier did not
recognize. Only its length/category was retained, so its exact text cannot be
recovered from this observation. This is a diagnostic limitation.

[Loadstar PR 9](https://github.com/SirReaDy/loadstar/pull/9), at commit
83d7e8e13ba7bc0266acdd42980475db170d6d33, provides a new independent implementation
lead. Its failure catalogue labels -90010 at init as client rejection. This is
that project's classification, not an official Apple definition or proof of our
local cause. Its documented message has 45 characters, matching our length;
that match is an inference and does not establish our actual message.

A source comparison identifies four concrete request-format differences:
Loadstar uses string CPD flags instead of plist booleans, restricts machine fields
in CPD to three named headers plus locale, accepts text/x-xml-plist instead of
*/*, and includes X-Xcode-Version and X-Apple-App-Info on every GSA request.
These differences are candidates for a bounded offline-prepared control, not
proven fixes. Its separate resync mechanism requires hsc 434; our hsc 200 does
not provide that signal. Do not apply resync speculatively.

The next useful experiment is an isolated init-only request-format control with
machine binding held fixed and no password proof. It must not change production
polling or conflate an accepted initial challenge with Find My report access.
No additional Apple request, deployment, guard reset or account-store access
occurred during this result analysis. Public reference source and bounded
comparison notes were saved privately for review.


### Isolated request-format control prepared

A separate FindMy menu entry, **Initial request-format control**, uses the same
initial-only flow with its own exclusive `.storage/findmy_request_format_attempt.json`
guard. It applies four explicit wire changes: string CPD flags, the reference CPD
field selection, plist Accept, and the two reference authentication headers. It
leaves the request email, SRP public value, protocol list, client-info, user-agent
and selected machine values unchanged. It is a named request-shape bundle, not
an experiment isolating the effect of each individual field.

The previous attempt identity was not retained. This test therefore uses a new
in-memory provisioned identity and cannot be represented as a paired comparison
against that exact historical identity. No identity fields are rewritten by the
format adapter. Earlier guards remain spent and untouched. The transport permits
one init only and additionally rejects extra proof fields, absent machine fields,
wrong routes, and repeated requests. A valid challenge also stops without proof.
The response classifier now recognizes the independently documented generic
45-character message without retaining arbitrary server strings.

Thirty-eight offline tests passed, covering exact format transformation,
unchanged machine/public values and request options, blocked proof/routes/repeats,
separate guard, cleanup and no session export. Ruff and the public-file privacy
check (248 files) passed. The prior FindMy component was backed up before the
five-file deployment. No HomeCircle production source or earlier guard was
modified; runtime readiness and owner result are recorded separately.

HA configuration validation passed and HA reconnected after restart. The new
email-only request-format form was verified in the real UI, then the desktop
flow was closed for owner use from the phone. No email was entered, the new
guard remains absent, and no account challenge has run during preparation.
HomeCircle appeared with its existing two entities after initialization; no
claim about current location freshness was made.


### Owner request-format result: initial challenge accepted

The owner-driven request-format control returned HTTP 200, Status ec 0, hsc 200,
and all bounded challenge fields (s, B, i, c), with protocol s2k. The initial-only
flow stopped as designed and the temporary account closed. No password proof,
verification, delegate request, account save, item keys or locations were accessed.
Deployed source hashes and both earlier guards were verified unchanged; the
request-format guard is now spent. The bounded trace was archived privately.

This is direct live evidence that the new request format can obtain a usable
initial challenge in HA. The earlier format returned -90010. Because the runs
used different ephemeral identities and occurred at different times, this does
not isolate causation to the format bundle or any one changed field. Do not
reset the guard to repeat this successful initial-only test.

The next useful milestone is a separately guarded, owner-driven authentication
continuation using the accepted request format, with bounded status observation
at each stage. It must evaluate password proof, verification and delegate token
issuance separately; initial challenge success establishes none of those and
cannot establish report access. Preserve the existing production session.


### Authentication request-format continuation prepared

A separate owner-driven **Authentication request-format control** extends the
accepted four-part format to init and complete, including post-code SRP. It
preserves all supplied SRP proof fields and machine values. The initial-only
format is factored into the same transformation and byte-equivalence tested.
An independent `findmy_auth_format_attempt.json` exclusive guard leaves all
three earlier guards spent and unchanged. The test uses a fresh in-memory
identity; no previous account or provisioning store is read.

The transport permits at most two init and two complete requests (one initial
exchange and one post-code exchange), one request per verification method/stage,
one postdata call and one delegate call. Settings, escrow, CloudKit and report
routes are blocked. No retry guard is reset. A repeated challenge stops through
the existing continuation guard. The flow checks credential presence then
closes and aborts without export or account creation. Credential presence does
not establish report authorization. No tracker keys or device passcodes are
used. Only fixed stage names, bounded status classifications and token-presence
flags are observed; credentials and account sessions are not retained.

42 offline tests passed. Ruff and the privacy check passed. The prior FindMy
component was backed up before deployment; HomeCircle source is untouched.
Live sign-in, verification and delegation remain pending owner input.

HA configuration validation passed and HA reconnected after restart. The new
authentication menu item and credential form were verified in the real UI with
no credentials entered. Deployed hashes were verified; the new attempt guard
remains absent. The owner must start this control from their phone.


### Authentication continuation owner result

The owner attempt passed both initial GSA requests (ec 0; complete hsc 409),
trusted-device code validation (HTTP 200), and post-code GSA init/complete
(ec 0; complete hsc 200). The continuation control reported authenticated,
identity_bound true and srp_pet_verified true, with exactly one continuation.
The delegate exchange was reached and returned HTTP 200, after which the code
submission path raised and surfaced the generic findmy_code_signin_failed UI.
The transient account closed and no session was saved. Source hashes and the
three earlier guards were verified unchanged; the authentication guard is spent.

This trace establishes successful code validation and post-code authentication.
It does not establish successful delegate authorization. The observer retained
only delegate HTTP status, not bounded plist application statuses, token-presence
flags in the raw delegate response, parsing shape or a fixed exception category.
Therefore application-level rejection and local parsing/state failure cannot be
distinguished from this record. No raw response is retained to reconstruct them.
The next diagnostic needs bounded delegate response structure/status and fixed
exception categories captured before cleanup, with no raw strings or tokens.
Do not repeat sign-in until that instrumentation is in place. No new request,
guard reset or runtime code change occurred during this result analysis.


### Delegate response and exception capture prepared

**Delegate response diagnostics** uses the same bounded authentication control
with a separate exclusive `findmy_delegate_diagnostics_attempt.json` guard.
The request-format transform and authentication transport ASTs match the last
owner attempt; only observation and flow selection/guard differ. All four prior
guards remain spent and unchanged. No production HomeCircle source was modified.

Delegate responses are classified before the SDK consumes them: bounded HTTP
and plist statuses, body byte count/parse result, top/service structure types,
localized-error categories/lengths, DSID type/nonempty, service-data and tokens
shape/count, and known token type/nonempty flags. No raw remote message, account
identifier, token value, unrecognized field name or response body is retained.
Parsing is capped at 512 KiB and classification failures do not replace the
response. This capture addresses the actual fields read by the delegate parser.

Caught sign-in, verification and continuation exceptions are recorded before
cleanup, with fixed categories, bounded status, an allowlist of missing field
names, and the final eight trusted module/function/line frames. No exception
text, code source lines, locals or arguments are retained. Unknown remote text
remains a length/category; diagnostics cannot promise to explain every possible
Apple response, but they now cover the known parser failure boundaries.

54 offline tests passed, including application rejection, absent service-data,
missing DSID, invalid/oversized plist, incorrect types, secret-value exclusion,
response preservation, failure observation before cleanup and distinct guard.
Ruff and public-file privacy checks passed. The prior component was backed up
before deployment. Runtime readiness is tracked separately; no new sign-in was
submitted while preparing this instrumentation.

HA configuration validation passed and HA reconnected after restart. The
Delegate response diagnostics menu and credential form were verified in the
real UI. No credentials were entered and the new guard is still absent. The
desktop flow was closed so the owner can start from their phone.


### Diagnostic overwrite correction

A later blocked login flow overwrote the sole compatibility observation record,
so the prior delegate diagnostic attempt cannot be reconstructed from that file.
The consumed guard only proves an attempt was claimed, not its 2FA outcome.
This storage design was insufficient and has been corrected.

Each flow now gets a random local observation ID and its own atomic HA Store
under `findmy_onboarding_observation_<id>`. Saves for a flow are serialized with
a per-flow async lock and snapshot current events inside the lock. Separate
flows cannot replace one another's records. The compatibility pointer is updated
only after a real attempt guard is claimed, so menu visits and blocked retries
do not overwrite it. Failure details are saved before cleanup. A successful
initial diagnostic write is required before session construction and Apple
requests; storage failure consumes the guard but stops safely without a sign-in.

A separate **Delegate diagnostics (retained)** entry uses a new exclusive guard;
all five earlier guards remain consumed and unchanged. The accepted request
transform and authentication transport ASTs are unchanged. Fifty-seven offline
tests passed, including preservation across blocked/later flows and rejection
before network when initial storage fails. Ruff and privacy checks passed.
No passwords, codes, account identifiers, token values or raw responses are
added to the records. Prior component source was backed up before deployment.

HA configuration validation passed and HA reconnected after restart. The new
retained form was verified, and a separate schema-2 flow record was confirmed
on HA storage. Opening this form did not change the compatibility observation
file hash. The desktop form was closed; no credentials were entered, no Apple
request was sent and the new attempt guard is still absent.


### Retained owner result: delegate application rejection

The per-flow record was retained and archived successfully. Trusted-device code
validation returned HTTP 200. Both post-code GSA requests returned ec 0, and
complete hsc 200. The SRP control verified the PET and retained identity binding.

The delegate HTTP response was 200, but its parsed dictionary had top-level
status 1, no localizedError or description, no DSID and no delegates dictionary.
It was a 348-byte response with two top-level fields. The exception was the
expected MobileMeDelegateError, status 1, at _login_mobileme, while the account
remained AUTHENTICATED. This establishes application-level delegate refusal in
this attempt, not a wrong verification code or local plist parsing failure.
It does not establish why Apple refused the request; the raw response and
unrecognized field names/values were deliberately not retained. In particular,
absence of localizedError does not independently establish account terms state.

The transient account closed, no session was saved, and no keys or locations
were accessed. Earlier guards and deployed source hashes were verified unchanged.
The new retained guard is consumed. No extra request or runtime mutation was
made during result analysis. Next analysis should focus on the delegate request
and PET/client binding, preserving the now-successful initial/2FA request path.


### Delegate request and PET/client binding audit

A synthetic execution of the actual pinned upstream and hybrid delegate builders
found equivalent endpoint, headers, auth and plist payload when canonical account
name equals submitted login. Both copy the same PET into Basic auth and plist
password and retain the same account client ID. The deliberate hybrid retry and
redirect controls differ from upstream defaults. When canonical name differs,
the only semantic request differences are the Basic-auth username and apple-id:
upstream uses the submitted login, HomeCircle uses Apple's returned account name.
This does not establish whether the owner's two names differed in the last run.
No protected saved account was read and no network request was made by this audit.

A primary-source export-findmy worklog reports status 1 after a change to V2
delegate format without validation data. Our body already uses the legacy shape,
so that particular regression does not explain our captured request. The report
is not an official Apple status-code definition. See
https://gist.github.com/stek29/4b15b02cf420223cc4c5b11e4870f5e0 and
https://github.com/stek29/rustpush/commit/0f5bb1f .

**Original-login delegate control** changes only the delegate Basic username and
matching plist apple-id to the submitted login. GSA, 2FA, PET, device/client IDs,
headers and request budgets retain their previous paths. Before transmission,
RAM-only checks require matching auth/body login copies, the same nonempty PET
in auth/body/account state, matching account client ID and matching ADSID header.
The trace retains only equality/presence flags and capped PET age, never values.
If the names are equal, this control makes no semantic username change; its
result is then diagnostic evidence, not an isolated intervention effect.

Top-level status-message classification has also been added. Existing per-flow
record retention remains intact. A new exclusive guard leaves all six earlier
guards unchanged. Sixty-six offline tests passed, including live-class inert
transport installation, submitted-login-only transformation, refusal of binding
mismatch, response privacy, account-reference cleanup and guard isolation.
Ruff and privacy checks passed. Source backup was made before deployment.
No new Apple sign-in has been submitted during preparation.

HA configuration validation passed; HA reconnected and the Original-login
delegate control form was verified in the real UI, with credentials left empty.
The desktop form was closed for phone use. Deployed hashes match; the new guard
remains absent and no new Apple sign-in was submitted during preparation.


### Original-login owner result: alias hypothesis excluded

The retained owner trace confirms exact equality between submitted and canonical
account names. Auth/body username copies, PET copies, account client ID and ADSID
header binding all matched. The fresh SRP PET was less than one second old at
the delegate request. This control therefore made no effective username change.

Trusted-device validation and verified post-code SRP succeeded again. Apple
returned delegate HTTP 200 with top-level plist status 1, no DSID or delegates,
and no localizedError. The 348-byte, two-field dictionary contained an unrecognized
49-character top-level status-message. Its raw text was not retained; length alone
must not be used to reconstruct or assert its content. This remains a diagnostic
limitation if that message distinguishes the refusal's reason.

The explicit alias selection, mismatched credential copies and obviously stale
PET explanations are excluded for this attempt. Successful SRP verification
still does not prove that Apple accepts the client/provisioning identity for
MobileMe delegation. The precise Apple refusal reason remains unestablished.
The temporary account closed, no account session was saved and no items or
locations were accessed. The trace was archived and deployed source hashes
verified; no new Apple request or runtime change occurred during analysis.


### Cross-stage machine/provisioning identity audit

Read-only source comparison verified the installed setup/profile/account/anisette/
endpoint-policy files against this checkout. Ten executable synthetic checks
confirmed the actual header mappings without starting the native VM, reading
protected state or contacting Apple. The native engine generates its own
local-user and device IDs. FindMy's provider preserves its OTP and machine
material but constructs device and local-user headers from account UUIDs;
the pinned upstream SDK does the same. Distinct native/account IDs therefore
are not a newly introduced mutation or sufficient evidence of a bug.

The accepted GSA format omits the local-user header from CPD and carries the
account device header plus native OTP/machine material. Delegation carries the
full SDK-generated header set. The retained SRP control checks provider/account
IDs and native engine/device fields before/after the post-code exchange; its
successful binding flags refute an unexpected switch during that interval.
They do not prove native/account ID equality or Apple's acceptance of the
resulting binding. Actual per-request secret header equality was not recorded.

The explicit declaration split is provisioning MacBookPro13,2/macOS/Xcode,
GSA/2FA Windows/akd, and effective delegation MacBookPro18,3/macOS/accountsd.
The latter is imposed by HybridHttp after the endpoint policy selected Windows
accountsd. Source inspection found no late reprovisioning or account-ID rewrite
in that delegate path; native headers are refreshed from the cached provider.
Earlier Windows-delegate controls obtained MME and CloudKit tokens but no
SearchParty token. Their request shape/time/identity differed from current runs,
so they are motivation for a control rather than a matched proof.

The next bounded comparison should keep the now-accepted GSA/2FA path, native
and account identities, PET and delegate body fixed, and change only the delegate
client-info declaration from forced Mac to the existing Windows accountsd policy.
Do not swap account IDs after SRP or claim that a declaration mismatch alone
explains the failure. This audit made no runtime changes, guard resets or new
Apple requests, and did not read the working saved account or tracker data.


### Windows delegate control prepared

A separate **Windows delegate control** selects the existing Windows accountsd
client-info declaration at the delegate transport boundary. This is the only
wire change relative to the preceding submitted-login control. GSA format,
verification, native recipe, account/native ID handling, PET binding checks,
submitted-login choice, request limits and per-flow records remain in place.
The account seed/endpoint policy already selected this Windows delegate profile;
the control stops replacing it with the forced Mac declaration on the wire.

Sixty-nine offline tests passed. The actual transport comparison confirms that
removing the client-info field makes both captured requests equal, including
identical body bytes, auth, remaining headers and retry options. Inert real-class
installation preserves account/provider IDs and does not initialize native code.
A new exclusive `findmy_windows_delegate_attempt.json` guard leaves all seven
prior guards untouched. Source backup was made before four-file deployment.
Ruff and the public-file privacy check passed.

This uses a fresh ephemeral identity, as preceding no-save tests did, so it is
not a matched historical identity comparison and does not establish causation
from a future success alone. MME/CloudKit credential issuance, SearchParty token
issuance and actual report access remain separate milestones. No account session
is saved and no recovery, item keys or locations are accessed by this control.
No new Apple sign-in request was made during preparation.

HA configuration validation passed and HA reconnected after restart. The Windows
delegate control menu and credential form were verified in the real UI. The
desktop form was closed with inputs empty for owner phone use. Deployed hashes
match, the new guard remains absent, and no Apple sign-in request was submitted.


### Windows delegate owner result: delegation succeeds, tracking credential missing

The retained owner record confirms Windows accountsd was selected. Initial SRP,
trusted-device code validation and post-code SRP succeeded. All submitted-login,
PET-copy, client-ID and ADSID checks passed; PET age was less than one second.
The delegate response was HTTP 200 with top-level and service status 0, a
nonempty DSID, service-data and a three-field tokens dictionary. MME and CloudKit
token values were nonempty strings; searchPartyToken was absent. The account
reached LOGGED_IN and the explicit credential check then stopped as designed.

This is live evidence that this Windows delegate route can authenticate and
issue partial service credentials in HA. Earlier Mac controls returned status 1.
Fresh ephemeral identities and timing still differ across runs; this is not a
same-identity paired causal proof. It reproduces the earlier partial-grant state
with the now-accepted GSA format and retained diagnostic records.

Both pinned upstream and local fetch_raw_reports require searchPartyToken;
MME/CloudKit token presence cannot substitute for it or establish report access.
No settings fallback, key recovery or report fetch ran. The transient account
closed and no session was saved. Source hashes and earlier guards remain
unchanged; the new guard is consumed. No new Apple request was sent during
analysis. Further investigation must target tracking-service grant acquisition,
accounting for the prior unsuccessful settings-hop experiments, rather than
repeating 2FA or claiming completed onboarding.

### Windows settings request control (prepared October 17)

The Windows delegate control authenticated and returned MME and CloudKit tokens,
but not SearchParty. A source audit found that earlier get_account_settings
controls selected the Mac accountsd policy and reused CloudKit operation headers.
Those HTTP 401 results therefore do not test an otherwise identical Windows
settings request. This is a concrete untested request-format bundle; it is not
proof that platform declarations caused either the 401 or the missing grant.

The separate private Windows settings control preserves the accepted GSA format,
post-code SRP continuation, native declaration and Windows delegation. After a
successful delegate exchange it sends at most one empty-body settings POST with
DSID/MME Basic authentication, the existing Windows accountsd declaration,
iCloudHelper user agent, plist accept type and the same provider's machine
headers. It removes CloudKit-specific operation headers. There are no retries,
redirects, alternative profiles or requests for tracker keys, recovery, enrollment,
records or locations. If SearchParty is already present, the settings call is
skipped. The result is only a presence check; no returned credential is persisted
or treated as proven report access. The transient account closes on every result.

The new menu has an explicit scope/consent screen and a separate exclusive
findmy_windows_settings_attempt.json guard. Earlier spent guards remain intact.
Bounded diagnostics retain HTTP status, response type/size, known status/message
categories, token counts and known token presence/type, and returned account-ID
comparison flags. Raw identifiers, credentials, header values and response bodies
are excluded. Per-flow atomic evidence storage and fail-before-network behavior
remain selected. No working HomeCircle source or saved identity is altered.

Validation: 78 synthetic offline tests passed, lint passed, and the public-file
privacy check passed for 248 files. Deployment preserved 86 production source
hashes and all eight earlier guard hashes. The control's Apple requests remain
zero until the owner submits the new consent and sign-in flow. Runtime readiness
is recorded separately in the private windows-settings-validation.json artifact.

Primary-source comparisons: the published get_account_settings example uses an
empty body and DSID/MME authentication; it documents CloudKit acquisition, not a
guaranteed SearchParty grant:
https://github.com/horrorho/InflatableDonkey/blob/master/CloudKit.md .
The current legacy MobileMe example requests an empty com.apple.mobileme delegate
and obtains the report token from that response; no separate SearchParty token
minting endpoint is demonstrated there:
https://github.com/biemster/FindMy/blob/main/pypush_gsa_icloud.py .
The research does not establish that a generic iCloud token can substitute for
SearchParty, nor that settings alone can overcome its absence.

HA Core configuration check passed; HA reconnected after restart and the new
Windows settings grant check consent form was verified with its checkbox off.
The desktop flow was closed for the owner to open a fresh flow from the phone.
No Apple request was made during deployment or UI verification.

The owner ran the Windows settings control. Retained flow 39b11c6cf5fe4d5b9c775c65903c6323 shows
initial SRP challenge HTTP 200, ec 0, hsc 200 and all required challenge fields.
The first SRP complete/password-proof request returned HTTP 503 with a 190-byte
non-plist response. No numeric Apple application status or retry interval was
available in the retained classification. Verification, delegation and settings
were never reached. The transient account closed; no account session, keys or
locations were saved/accessed. This attempt does not test the Windows settings
hypothesis and does not establish a wrong password, account lockout or rate
limit. The one-attempt guard is consumed and preserved. No new request, guard
reset or retry was made during result analysis.

### One controlled retry after the settings-control SRP HTTP 503

The owner explicitly resumed Apple setup after stopping work. A separate menu,
Windows settings check — retry after 503, preserves the same protocol and consent
screen and uses findmy_windows_settings_retry1_attempt.json. It does not delete
or reset the consumed settings guard or any prior guard. This is one owner-driven
retry, not an automatic HTTP retry. The existing request caps, isolated fresh
identity, memory-only credentials, per-flow diagnostics, no-account-save rule,
and no recovery/keys/location scope remain selected. The 503 attempt's evidence
remains archived. Eighty offline tests, lint and the 248-file public privacy check
passed. Deployment preserved all 86 production source hashes and nine earlier
guard hashes. Apple setup success and actual settings acceptance remain unproven.

Retry readiness: HA Core check passed, HA reconnected after restart, the retry
menu and unchecked consent screen were verified, and the desktop flow closed.
The new retry guard remains absent; all nine earlier guard hashes are preserved.
No new Apple request was made during this preparation.

The owner ran the controlled retry. Retained record 58414e5e9be4424a9beb91f9ce751e6c
confirms accepted initial SRP/password proof, trusted-code validation HTTP 200,
and one verified post-code SRP continuation with stable identity. Windows
MobileMe delegation returned HTTP 200, top/service status zero, and MME/CloudKit
credentials without SearchParty. The dedicated Windows settings request then
returned HTTP 200 and a 13,206-byte plist. No top status or localized error was
present. Its tokens dictionary had three fields; MME and CloudKit were nonempty
strings, SearchParty absent. No known returned DSID field was present, so no
returned-account binding was independently confirmed by that response. This
establishes settings HTTP acceptance for the Windows request bundle, not a
tracking grant or report access. The temporary account closed. No session,
tracker keys, recovery, enrollment or locations were accessed/saved. The retry
guard is consumed and preserved; there was no new request during analysis.

The owner's phone rendered the bare windows_settings_result abort key. The
matching live/local English translation contains that key and its outcome
placeholder, so a missing deployed English entry is ruled out. Client/cache or
translation-resolution behavior was not isolated; do not call the cause proven.
The underlying bounded evidence was retained independently of UI translation.
Further repetition of this unchanged Windows settings request is not justified
by the missing-token result. A separate source comparison must identify a
credential-grant difference before another account test.

### Read-only service-grant comparison after accepted Windows settings

The accepted Windows result establishes that a freshly issued DSID/MME pair can
reach get_account_settings from HA. It does not establish that the pair is
entitled to SearchParty. Both delegation and settings exposed three token fields
and lacked SearchParty. Token counts alone cannot reveal the unclassified third
token. The diagnostic evidence excludes a rejected code, stale PET copy or
failed settings HTTP authentication for this particular completed attempt.
Neither the source comparison nor the retained responses establish Apple's
reason for omitting the report grant.

The accepted-format controls retain Windows/akd GSA and verification declarations.
Their successful Windows accountsd delegation/settings is distinct from the
Mac-accountsd delegate controls, which returned top status 1. Earlier standalone
Mac init composers inspected in coherent-init and default-serial controls used
boolean CPD flags, full/older CPD layout and Accept */*. They did not use the
current accepted-format transform. The combination of the corrected format and
a Mac/akd GSA declaration is not represented by these retained controls. This is
an untested combination in the inspected evidence, not a claim that all possible
historical experiments have been reconstructed.

The pinned Loadstar implementation uses the string-flag/selected-machine-field
format with a Mac/akd fallback identity. That independent source supports testing
the combination but does not demonstrate issuance of SearchParty. Its fallback
is MacBookPro13,2/macOS13.1; our counterfactual uses the SDK-style
MacBookPro18,3/macOS13.4.1/akd declaration, with the existing user agent unchanged.
Do not present these as byte-identical reference clients. No Xcode process name
is introduced in the GSA client-info header. The existing native provisioning
recipe is a separate declaration and remains untouched.

An executable synthetic audit captured the actual local GSA request composer for
init and complete and applied the accepted-format transform. The counterfactual
then changes only the case-insensitive X-Mme-Client-Info field from Windows/akd
to Mac/akd. Seventeen checks pass: request bodies, public value/password proof,
challenge, selected machine fields, account IDs, endpoint, retry and redirect
policy remain fixed; no ADI engine starts and no network runs. Artifact:
work/findmy-replacement/upstream-onboarding/grant-profile-audit.json .
The audit script is source-only, not a deployed transport or a live test.

The next justified account experiment would first test only the initial challenge
using this Mac/akd declaration plus the already accepted request format. If that
challenge fails, stop before password proof. Only an accepted challenge would
justify a separately scoped full Mac-declared authentication/delegation control.
Do not mutate device IDs between phases, substitute MME/CloudKit credentials for
SearchParty, bypass the report guard or perform recovery to guess at this grant.
The source review found no demonstrated separate SearchParty minting endpoint in
the inspected legacy MobileMe implementations. This is not proof none exists.
No new Apple request, private account/session/key read, guard reset, runtime
deployment or HA restart occurred during this source audit. Eighty-six production
source hashes and nine prior guard hashes remain unchanged.

Primary sources reviewed:
https://github.com/SirReaDy/loadstar/blob/83d7e8e13ba7bc0266acdd42980475db170d6d33/packages/apple/src/domain/config.ts
https://github.com/stek29/rustpush/blob/0f5bb1f/src/auth.rs
The RustPush compatibility branch selects legacy delegate format when validation
data is absent. Our current path already uses that legacy format; switching to
V2 without validation data is not supported by this comparison.

### Mac-declared accepted-format initial control prepared

The owner authorized the proposed initial-only Mac-declared check. A separate
FindMy menu entry, Mac-declared initial challenge (HA only), uses a distinct
findmy_mac_request_format_attempt.json guard and an email-only scope disclosure.
The transport inherits the existing one-init allowlist and accepted request
transform. It replaces only the case-insensitive GSA client-info field with
MacBookPro18,3/macOS13.4.1/AuthKit/akd. The existing user agent, native provisioning
recipe, generated account IDs, selected CPD machine fields and SRP public value
remain unchanged. The response is classified and discarded; password proof,
verification, delegation, settings, recovery, enrollment, keys and locations are
not permitted. No account session is read or saved. Anonymous provisioning may
perform its existing bounded requests before the single GSA init.

Eighty-five offline tests, lint and the 248-file public privacy check passed.
Tests establish a header-only difference from the accepted Windows request,
identical request bodies, a blocked second init and blocked complete/delegate/
settings requests, a distinct guard and closure without login or export. The
result reuses the existing request_format_result translation key to avoid adding
another abort message dependency on the phone. Deployment preserved 86 production
source hashes and ten earlier guard hashes; all previous attempts remain intact.
No Apple request has been made during preparation. HA runtime readiness is
recorded in work/findmy-replacement/upstream-onboarding/mac-initial-validation.json.

Mac initial runtime readiness: HA Core check passed, HA reconnected after restart,
and the new email-only form and disclosure were verified. No input was submitted
on desktop; the flow was closed for the owner phone test. New guard remains
absent, and no Apple request was made during preparation.

The owner completed the Mac-declared accepted-format init control. Retained
record e4a25ce58b2342729ec9ee7d3cc817bf reports HTTP 200, Apple ec -80045,
hsc 500, an 850-byte plist and generic_retry_later message category. All required
challenge fields were absent. The transient account closed; no password proof,
verification, delegation, settings, account session save, keys or locations were
attempted. The new guard is consumed and preserved. No extra request was made
for this result analysis.

The corrected request format alone did not make this fresh Mac-declared client
acceptable. This rules out proceeding with full authentication for this exact
combination. It does not establish an incorrect password (none was used), a
specific account lockout, rate limit, or Apple's internal meaning of -80045.
Comparison with separate accepted Windows attempts supports investigating client/
machine context, but time and fresh identity differ across attempts, so it is
not a same-session causal proof of platform policy. Do not restart the same
profile-testing loop or retry this guard. A new candidate needs a distinct
source-backed difference before another account request.

### Machine-authentication context audit after the Mac init refusal

Read-only local source and retained derived records confirm that fresh HA
onboarding runs Android ADI via the Python anisette engine. Its configured Mac
native label and the service Windows/Mac client-info fields are declarations;
they do not load macOS AuthKit or transform the binary backend. The local
provider takes native OTP/machine material but rebuilds account-facing device ID
and MD-LU from separate account UUIDs. Routing info is 17106176 in both the
installed engine's get_data output and the provider default, so a local routing
mismatch is not demonstrated. Pinned FindMy.py also separates these identifiers;
that difference is not, by itself, evidence of a HomeCircle defect.

Pinned V3 source (stek29/apple-private-apis b96e584) derives the provisioning
identifier, UUID device ID and hex SHA256 local-user identifier from one persistent
16-byte seed. Those identities remain paired through provisioning and service
header generation. Machine material and routing info are returned by the provider.
This is an implementation-level comparison beyond swapping service labels.
However earlier aligned-ID/raw-local-user controls already rejected init with
-80045/hsc500 using the older composer. Repeating piecemeal ID alignment is not a
new fix, and combining it with another request format remains unproven.

The public export-findmy source selects a remote V3 provider and iPhone-style
client configuration with no macOS validation data. Its application code exports
accessory keys and contains no searchPartyToken reference. It therefore cannot
be treated as independent proof that fresh report authorization works for this
account. Key discovery/export and SearchParty report access remain separate gates.
Public source snapshots and checksums were saved in the private
machine-context-reference directory; none of that external source was executed.
The mutable export-findmy main branch was archived with a content checksum; it
is not represented as a pinned commit.

A source-only Python seed-binding model was prepared for further offline work,
explicitly not a complete V3 provider/GSA implementation. Fourteen synthetic
checks validate the UUID and SHA256 reference vector, shared seed binding,
provider machine/OTP/routing forwarding, exclusion of unrelated IDs and fields,
and rejection of malformed seed/provider inputs. No real seed, provisioning
record, account session or credential was read. No VM or native API was started.
Artifacts: machine-context-audit.json, machine_context_candidate.py and
machine-context-candidate-validation.json under the private onboarding work area.

The next implementation milestone is an offline end-to-end reference comparison
of a full seed-bound provider and its pinned GSA composer, including request
context and all post-code/delegate transitions. Only then should a separately
scoped anonymous-provisioning/init check be considered. It must preserve the
working connection and never patch an identity after authentication starts.
No live code changed, HA restart, guard reset or Apple request occurred during
this audit; 86 production source hashes, deployed diagnostic hashes and ten
prior guard hashes remain unchanged. The consumed Mac control guard is preserved.
No specific Apple policy or internal definition of -80045 has been established.

### Whole-flow V3 comparison (offline)

Pinned apple-private-apis at b96e584a25ac88fa5317811b207c678cfdb1b155 and RustPush
0f5bb1f source snapshots were archived with checksums. The comparison covers
provisioning identity, GSA init/complete, trusted-code verification, PET choice
and legacy delegation. The reference was modeled in Python without running Rust,
starting ADI, reading protected state or contacting Apple. Socket connection was
blocked; all local account HTTP methods used synthetic responses.

Twenty-four checks pass against actual local _gsa_request, verification-header
and _login_mobileme composers, plus the earlier fourteen seed-binding checks.
This is wire/transition evidence, not SRP cryptographic or live end-to-end proof.
Verification comparison executes the core identity/context header path; the
reference's additional Fetch/CDP/browser presentation fields were source-audited,
not asserted field-for-field by the core model. Delegate client-id was normalized
to a fixture for envelope comparison: Rust generates a fresh UUID per delegate
request, while the local SDK uses its account UUID. This generator difference
remains in the recorded stage matrix and is not declared a causal defect.

The major result is that a provider-only replacement would not reproduce V3:
its export configuration selects imessage/Messages/MobileSMS context, includes
machine material on GSA HTTP headers as well as CPD, uses a richer CPD with typed
booleans and extra context, and preserves one request UUID across the init and
complete pair. Our accepted-format transformer selects iCloud and string flags,
removes the extra CPD fields, and places selected machine material only in CPD.
String flags are thus not a universal property of all referenced Apple clients;
the prior Loadstar recipe and the V3 recipe are distinct source-backed bundles.
Mixing either recipe's fragments is not reference equivalence.

V3 uses a verification header PET when returned, otherwise repeating SRP. Our
current diagnostic helper deliberately suppresses that PET and runs one verified
SRP continuation. Earlier owner cookie/header-PET and post-code-SRP controls both
failed to obtain SearchParty, so toggling only this PET choice again is not new.
Legacy delegation is already selected locally, matching the no-validation-data
branch. Enabling V2 without validation data is not supported by this comparison.
The upstream delegate source has debug logging of decrypted SPD; any later
executable adapter must avoid inheriting such output. No external source was
executed in this audit.

The recorded decision is to use a separate, pinned full-context adapter rather
than attach a V3 provider to format_gsa_request. Before another owner request,
that adapter needs bounded provisioning/transport and token-transition tests,
strict no-persistence/cleanup controls, disabled credential logging and an
anonymous/init-only first stage. This comparison alone is insufficient to
justify another owner password/2FA trial. Artifacts: v3_wire_reference.py,
compare_v3_flow.py and v3-flow-comparison.json in the private onboarding work area.
No runtime deployment, restart, account request or spent-guard reset occurred.

### Separate V3 initial adapter built and tested offline

The owner authorized building the distinct adapter. The private v3-adapter folder
now contains a seed-context implementation, pinned-context GSA recipe and an
asynchronous initial adapter. It performs lookup, one ordered V3 WebSocket
identifier/start/finish/success sequence, one provider-header fetch and one GSA
init through mandatory injected IO. There is no default HTTP/socket transport,
HA form, filesystem persistence, VM/native call or executable password/verification/
delegation/recovery/report flow. Thus it is not deployed or owner-test ready.

The adapter preserves the seed-derived identifiers and imessage/Messages/
MobileSMS context, sends machine fields in GSA headers and rich CPD, and retains
the pinned boolean/integer CPD types. Mixed service contexts are refused. Endpoint
and operation limits are enforced inside the request boundary, including rejection
of a complete/password-proof body at the otherwise allowed GSA URL. Provisioning
URLs must match exact HTTPS Apple host/path rules, provider frames follow one
strict sequence, response/frame/header sizes are capped, and redirects/retries
are disabled in the injected IO contract. All actual live TLS/network enforcement
still depends on the not-yet-implemented transport; do not claim a live boundary
was verified by a synthetic IO fixture.

Forty-five tests passed with socket/DNS operations forbidden, and lint passed.
They cover complete synthetic provisioning-to-init replay, all five HTTP failure
points, HTTP 301/401/503 without retries, malicious bag/provider targets, frame
order, oversized responses, malformed machine material, missing challenge fields,
cancellation, concurrent submission, deadline expiry, and late WebSocket closure.
A cleanup race discovered by these tests was fixed: a socket returned after
closure cannot repopulate the adapter. Cleanup drops transient references and
closes the owned IO with finite timeouts; a failed close produces a fixed flag
and changes a would-be successful result to cleanup_failed. This is reference
release, not a guarantee of physical byte erasure in Python memory.

Typed CPD flags were compared with the pinned Rust source, and the fixture
verifies identical provisioning/provider/service seed binding. No SRP server
math or encrypted SPD authentication is exercised: an SRP public value is supplied
by the caller and no password proof is sent. Test data are synthetic. No public
reference Rust code was executed. Diagnostics contain fixed events/statuses only.

The next required implementation is bounded real HTTP/WebSocket IO and an
explicitly selected HA-local V3 provider, then a separate HA controller/guard and
email-only scope/consent form. Do not silently select a public provider or claim
this changes the Android backend into native macOS authentication. The working
connection remains untouched. Validation: v3-adapter-validation.json and
v3-adapter-tests.xml. No Apple request, deployment, restart or guard reset was
performed. Eighty-six production source hashes, installed diagnostic hashes and
ten prior guard hashes remain unchanged; the spent Mac-init guard is preserved.


### HA-local V3 executable initial-control preparation

The separate underscore v3_adapter package now has verified-TLS HTTPS transport,
a RAM-only provider interface and an owned ADI subprocess. The provider interface
opens no listener and never resolves its internal routing name. Apple transport
allows only one lookup, provisioning start, provisioning finish and GSA init;
redirects, retries, proof requests and other destinations are refused. The worker
uses existing SHA-pinned public ADI libraries, blocks Python socket connections,
disables logging, and exports only bounded JSON IPC replies. This is process
isolation with application-level network blocking, not an OS sandbox guarantee.

The seed binds provider identifier, device UUID and SHA256 local-user value.
The ADI identifier follows the pinned Dadoum V3 server algorithm: uppercase UUID
truncated to 16 characters, including hyphens. The backend remains Android ADI;
this does not establish native Apple-device trust or Find My authorization.

A separate HA email-and-consent form consumes a new one-attempt guard before
preflight and writes bounded observations before any network work. No password,
code, account session, recovery, enrollment, tracker key or location is accessed.
The isolated worker is terminated and transient references released on completion,
failure, cancellation or flow removal. No ADI state file is exported.

153 offline tests passed, including 60 adapter/transport/worker tests and 8 new
controller tests. All native/Apple exchanges were synthetic. Controller checks
cover consent, one-use guard, persistence failure, preflight refusal, cancellation,
exception sanitization and real decorated entry tracing. HTTP checks exercise
TLS verification, route limits and response caps with mocked exchange/DNS.
No real ADI execution or Apple request has yet verified this new path.

The diagnostic component has been backed up before deployment. Production
HomeCircle source hashes and eleven prior spent guards were preserved. The new
guard is findmy_v3_local_initial_attempt.json and is not reset by this workflow.
See v3-local-validation.json and v3-local-tests.xml in private research evidence.

HA configuration check passed. After restart, the installed HA-local V3 menu and
email-only form were verified in the browser with consent unchecked. No test was
submitted and the new guard remains absent. The desktop form was closed for the
owner to start the check from their phone. Fresh onboarding remains unproven.


### HA-local V3 owner result

Owner-submitted observation c17d03d7e87146d1ab93436abeae50ab confirms public
library/API preflight passed, Apple lookup/start/finish each returned HTTP 200,
and the RAM-local provider returned machine headers. GSA init returned HTTP 200
with Apple code -80045 and no usable challenge. Cleanup reported references
cleared and transport close successful. Four Apple requests were made; the
headers step was local IPC, not a fifth Apple request. No password proof, code,
account persistence, keys or locations were attempted. The guard is consumed.

Thus this particular seed-bound V3 context on HA-local Android ADI still fails
before password proof. Successful provisioning does not prove Apple accepts
that device/service context for account authentication. This does not establish
a wrong password or explain Apple's undocumented code. The matching rejection
weakens the theory that provider location or seed-binding alone is sufficient.
Next investigate differences against the known challenge-ready Windows control
offline before proposing another live account attempt.


### Offline comparison after HA-local V3 rejection

Actual Windows and V3 composers were replayed with equal synthetic SRP and
machine inputs, with socket/DNS blocked. Eighteen assertions passed and six
source hashes matched installed files. Endpoint/protocol and SRP init fields
match. Fourteen HTTP fields and twenty-one CPD fields differ. The accepted
Windows composer has nine CPD keys with string flags and iCloud service; V3 has
twenty-five with bool flags, imessage context, machine fields in HTTP and body,
and additional upgrade/capability declarations. The V3 pinned composer does not
include timezone in GSA headers or CPD, so this review did not find a missing
timezone defect. Historical requests were not matched for identity/time.

The next control should retain HA-local V3 provisioning/seed/transport and use
the complete previously accepted Windows GSA format for init only, rather than
change an OS label beside imessage declarations. This isolates the GSA-format
bundle from the V3 machine route, not each individual field. A separate guarded
implementation and owner launch remain required. No new Apple/native execution,
deployment, account-store access or spent-guard reset occurred. Private details:
WINDOWS-V3-INITIAL-ANALYSIS.md and windows-v3-initial-comparison.json.


### HA-local V3 plus complete Windows GSA control

A WindowsInitialAdapter overrides only initial request composition. V3
provisioning/profile, seed binding, local worker/transport and all request/cleanup
budgets remain inherited. The composer reproduces the entire accepted Windows
GSA init presentation: nine CPD fields, iCloud service, four string flags,
Windows/akd declaration, accepted user agent and Xcode-auth headers. It excludes
the richer Messages context and HTTP machine headers.

163 offline tests passed. Differential tests compare the candidate with the actual
accepted Windows account composer and formatter for both headers and plist body.
Replays confirm provisioning-stage equality, success/refusal result handling,
separate guard selection, no automatic persistence, per-stage failures, cleanup
and repeat refusal. Socket/DNS operations are blocked in new tests.

A separately named email-and-consent form and guard were deployed after backup.
Twelve earlier guards are preserved. No Apple/native test was launched during
preparation, and production source hashes remain unchanged. New guard:
findmy_v3_windows_initial_attempt.json. This is a request-format bundle control,
not a proof of an individual causal field or tracking authorization.

HA configuration check passed and the restarted HA displayed the exact new menu
and email-only consent form. The checkbox was unchecked and no form was
submitted. The new guard remains absent; the desktop flow was closed for phone
use. Screenshot: v3-windows-ready.png. Apple acceptance remains unproven.


### HA-local V3 plus Windows request: challenge accepted

Owner-submitted observation 4c7b6561f49046828614173dab3c9fd9 records successful
preflight, lookup/start/finish HTTP200, local header generation and GSA init
HTTP200 with ec0 and challenge_ready=true. Cleanup reported cleared references
and successful transport close. Four Apple requests; no password proof, code,
account session persistence, tracker keys or locations. New guard is consumed.

The phone displayed the untranslated v3_windows_initial_result abort key. This
is a result-presentation defect; the saved result establishes challenge readiness.
The HA-local V3 provider can therefore produce machine context that Apple's
initial challenge accepts with the complete Windows GSA presentation. The prior
Messages presentation was refused, but separate identities/times prevent assigning
the change to one field. This is not full sign-in or SearchParty authorization.
Next milestone is a separately guarded owner-driven authentication continuation
with this provisioning/GSA recipe, preserving identity through verification and
reporting credential presence. Do not replay the consumed init-only check or
reuse its released ephemeral identity. No new account request was made in analysis.


### HA-local V3 full authentication control prepared

A separately guarded diagnostic uses the accepted Windows GSA formatter with
one seed-bound HA-local V3 provider and owned RAM-only ADI worker. Existing SDK
SRP/server-proof validation, trusted-device/SMS verification, principal/PET checks
and one Windows accountsd delegate exchange remain responsible for authentication.
A usable verification-header PET is accepted through the existing validator; if
absent, the SDK permits one post-code SRP continuation. No forced header-PET
withholding is used in this new path. A repeat challenge stops without another
code request. No settings, recovery, enrollment, keys or reports are permitted.

Native OTP refresh stays on the same worker/seed, with a 30-second cache and a
twelve-call cap. The original initial-only worker retains its one-OTP default;
only the full-auth child entry point selects twelve. Account/device/provider and
endpoint policy binding are checked before auth and verification steps; changed
machine material on refresh is refused. The per-flow lifetime remains 15 minutes.
Auth transport caps plus three provisioning requests bound Apple traffic to
fourteen requests with no automatic retries. Cookies and account secrets stay
in RAM; only bounded stage/status, binding and credential-presence flags are saved.
The test closes even if the tracking credential is present, and cannot export
or create an account entry. Public libraries remain the only existing ADI input.

183 offline tests passed. New cases cover actual accepted-composer equality,
provisioning, cached/refreshed machine material, identity mutation, OTP caps,
changed machine rejection, cancellation, cleanup, full-flow guard selection,
consent bypass refusal, missing/present grant without persistence, and unapproved
endpoint refusal. Native worker replay checks one, three and twelve OTP limits
with synthetic ADI. Existing SRP, pushed-code and verified-transport regression
suites also passed. No new Apple/native request was made during preparation.

The diagnostic component was backed up before deployment. Production HomeCircle
source hashes and thirteen earlier consumed guards were preserved. New guard:
findmy_v3_auth_attempt.json. The owner must submit credentials directly in the
HA-local V3 full sign-in check form. Full authentication and report authorization
remain unproven until the owner test. Evidence: v3-auth-tests.xml and
v3-auth-validation.json in private research.

HA configuration check passed. After restart, the full-auth menu and form loaded
with an empty email, masked password control and unchecked consent. The desktop
flow was closed without submission; the full-auth guard remains absent. The owner
can start from their phone. Screenshot: v3-auth-ready.png. Full authentication
and tracking-credential presence have not yet been tested against Apple.


### HA-local V3 full-auth owner result: login succeeds, report grant absent

Observation 258a2bb047f34908a2b89f7d4df30c3f records successful provisioning,
GSA init ec0/hsc200 and password proof ec0/hsc409 leading to REQUIRE_2FA.
Trusted-device code validation returned HTTP200. A usable response-header PET
and heartbeat were accepted; no post-code SRP continuation was needed. The one
Windows accountsd delegation returned HTTP200, top status0 and service status0.
Three token fields were returned: MME and CloudKit were nonempty; SearchParty
was absent. LOGGED_IN was reached, then the presence-only test stopped. Seven
Apple requests were recorded: three provisioning, init, complete, code validation
and delegate. The provider-header step was local, and the already-pushed code
required no separate code-request network call.

Delegate bindings matched submitted/canonical login, account client ID, ADSID
header and PET copies; recorded PET age was zero seconds. The verification PET
prefix did not equal ADSID. The SDK treats this prefix as opaque in the current
validation response, so this flag alone is not evidence of a wrong-account token;
the resulting delegate exchange was accepted. No raw tokens were saved.

Account close, machine-reference cleanup and worker/transport close all reported
success. No account/session, recovery, enrollment, tracker keys or locations were
saved/accessed. The full-auth guard is consumed. No new Apple requests were made
during result analysis. This establishes working HA-only fresh authentication
with this recipe, but no SearchParty report authorization. It reproduces the
prior Windows partial-grant outcome on the V3-local machine route.

Next investigate SearchParty credential issuance and the provenance of the
original working connection, rather than repeat credential/2FA or assume keys
can replace a report grant. Earlier Windows account-settings controls already
returned MME/CloudKit without SearchParty; repeating that alone is not new evidence.


### SearchParty credential provenance audit

Official/current account code gets the report credential from the full MobileMe
delegate token map; no separate tracker-key-to-report-token request was found.
Two synthetic actual-parser controls preserve a supplied SearchParty token and
retain its absence when other tokens arrive. No filtering defect was shown.
Earlier successful account-settings controls also lacked SearchParty.

Historical preserved-Python-identity reconnect and Discover acceptance includes
new sign-in, recovery and accepted reports, beyond old cached-session success.
The bounded evidence does not retain the exact first successful issuance wire
response. Rust exporter identity and Python report-session identity are separate
artifacts. Provider issue61 demonstrates trusted-device login/MME/keychain sync,
not fresh SearchParty issuance. Identity/history remains a hypothesis.

Next discriminator: isolated preserved-Python-identity authentication, clearing
account credentials and measuring grant presence immediately after delegation,
before settings/recovery. Preserve the working connection and do not confuse
this with restoring Rust state. No such control was launched here. No Apple/native
call, account-store read, runtime edit or guard reset occurred in the audit.
Private evidence: SEARCHPARTY-CREDENTIAL-PROVENANCE.md and
searchparty-provenance-audit.json.


### Preserved Python identity authentication discriminator prepared

The diagnostic copies only the single active HomeCircle Python account's saved
ADI BytesIO input, UID/device identifiers and public provider profile from RAM.
It never opens the encrypted vault, account token map, tracker items or locations,
and never calls account/provider.to_json or the live VM's export functions.
It refuses zero/multiple source accounts, closed/non-local providers, missing
saved state or oversized input. The owner enters the same Apple credentials in HA.

An owned subprocess restores the cloned ADI archive plus pinned public libraries,
checks is_provisioned, and calls only native request_otp. It has no provisioning
start/finish or export command; Python socket calls are blocked. Original SDK
account UID-to-base64-LU and uppercase device-ID mapping is retained. It uses
the same accepted Windows GSA/verification and Windows accountsd delegate route
as the fresh V3 control. OTP cache/cap and fifteen-minute flow expiry are retained.
No source vault or active account is replaced; only credential-presence/status
flags are saved immediately after delegation, before any settings/recovery.
A separate guard is spent before reading machine state or sending credentials.

192 offline tests passed. New controls include poison-field source objects that
refuse account-token/key access, non-destructive BytesIO copy, ambiguity refusal,
restored header layout, cleared account login, source preservation, separate
owner guard, and a fake native child proving unprovisioned refusal and forbidden
provisioning commands. All exchanges were synthetic; no real machine snapshot
was read or Apple/native call made during preparation.

Production source hashes and fourteen prior guards were preserved. The diagnostic
component was backed up before deployment. New guard:
findmy_preserved_auth_attempt.json. The experiment has not run yet. Private
validation: preserved-auth-tests.xml and preserved-auth-validation.json.

HA configuration check passed. After restart the preserved-identity menu and
credential/consent form loaded with empty fields and consent unchecked. It was
closed without submission. No machine snapshot was read and the guard remains
absent. Screenshot: preserved-auth-ready.png. Original two-login chronology was
clarified for the owner: Rust key recovery and a separate Python report login;
GSA plus delegate within the latest test are stages of one authentication.


### Preserved Python identity owner result: trusted login, restricted token set

Observation 7b460c30d21a4d088eb50e28cd31d458 confirms the active client's saved
ADI identity was copied without opening a vault, account tokens or items. The
isolated worker reported already provisioned; new provisioning was forbidden.
GSA init and complete returned ec0/hsc200. No 2FA prompt or code-validation call
was needed, unlike the fresh V3 case. Windows accountsd delegation returned
HTTP200, top status0 and service status0 with three token fields: MME/CloudKit
nonempty and SearchParty absent. Submitted/canonical login, PET copies, client ID
and ADSID-header bindings matched; PET age was zero seconds. Three Apple
requests occurred: init, complete, delegate. Cleanup closed the transient account
and worker and cleared copied machine references. No source store replacement,
key recovery or report request occurred. The guard remains consumed.

This weakens the preceding identity-history hypothesis: even the preserved
identity, recognized without another code challenge, did not receive SearchParty
under the current Windows authentication/delegation bundle. Machine reuse alone
is insufficient. It does not prove that historical server policy is unchanged
or that a Mac declaration would be accepted. Fresh Mac GSA and Windows-PET/Mac
delegate controls already failed, so do not repeat those as if untested.

The next offline discriminator is the original working report client's complete
service-context bundle versus the current Windows bundle, including GSA, PET
source and delegate declaration. Any preserved-identity/original-context live
control must be separately guarded and must account for earlier -80045/status1
results. No additional login was launched while reading this result.

### Offline original Python report-context audit

Pinned original FindMy 0.10.2 source differs materially from the current Windows
control even when the Python ADI identity is preserved: original GSA sends 15 CPD
fields with Boolean flags; the current formatter sends nine with string flags,
omitting time/timezone, Apple locale, local-user ID, routing and serial. Client
service declarations and supplemental GSA headers also differ. A synthetic
composer replay confirms these format differences and unchanged SRP parameters;
it is not evidence that any one difference causes a missing grant.

No separate later SearchParty-token request was found in the original SDK login.
Key recovery and report authentication were independent sessions in the original
prototype. PET source and Mac delegate label controls have already been tried;
the latest no-code preserved-identity result also uses a GSA-derived PET. Do not
repeat these as new hypotheses. The existing original-SDK continuation candidate
is the remaining bounded original-context discriminator, initially init/proof
only with the preserved Python identity. It was not deployed or launched here.
All 86 production file hashes remained unchanged. Private comparison and source
hash evidence: upstream-onboarding/ORIGINAL-REPORT-CONTEXT-COMPARISON.md and
original-context-comparison.json. Historical source provenance is not a raw wire
capture of the first successful login.

### Original Python SDK authentication control prepared

The separate FindMy diagnostic component now has an original-SDK init/proof-only
control. A dedicated child loads the SHA-pinned original 0.10.2 wheel and copies
only the active Python report client's serialized ADI state and UID/device IDs
from HA RAM on owner submission. It reads no account vault or stored tokens. It
uses the original SDK's full GSA CPD/profile/serial composition and verified Apple
TLS context, with a fresh transport per operation. Cached engine loading and OTP
generation deny machine networking; the engine's unconditional provision call
is replaced by a check that the loaded identity is already provisioned.

A new exclusive findmy_original_python_auth_attempt.json guard permits at most
one init and one complete. Calling only _gsa_authenticate stops before requesting
verification, delegation, recovery or item reports. Apple can independently send
a code with its challenge. Stage records include only operation, bounded numeric
Apple ec/hsc, HTTP status, counts and fixed outcome/boundary flags. Passwords,
SRP bodies, machine headers and intermediate grants are not exported or logged.
The child is killed/reaped on timeout or cancellation and closes its transient
account after normal completion. No saved session is replaced.

Validation: 197 flow/adapter cases, 16 continuation cases, actual pinned-SDK
integration with network denied, Ruff and public privacy guard passed. Eight
component files were deployed with rollback copies; 86 production hashes and
15 existing attempt guards were preserved. Configuration check exited zero.
The new attempt remains unconsumed until owner submission.

### Original Python SDK owner result: initial challenge refused

Observation 4a6409c287cf4e70a39a116cbce159f8 records one original-SDK GSA init
request using the preserved Python machine identity. Apple returned transport
HTTP200 with protocol ec -80045 and embedded hsc500. No complete/password-proof
request occurred. No verification was requested, no delegation was attempted and
no account was saved. This does not establish whether the password is correct.
The isolated probe returned a bounded rejected result through normal cleanup;
there is no independent native-process cleanup receipt beyond the parent wrapper
success path. No tokens, keys or locations were requested or retained.

This closes the previously untested preserved-Python-identity plus original-SDK
GSA-format control: it now has a live refusal, not merely a synthetic fixture.
Do not propose another identical original-path retry as a new discriminator. It
does not establish the cause of -80045 or prove that historical server behavior
is unchanged. Combined with the Windows control on the same source identity,
two distinct barriers remain: original GSA presentation is refused before proof;
Windows presentation reaches authentication/delegation but lacks SearchParty.
A routine password or 2FA retry does not distinguish those barriers.

The per-flow record was archived privately. All 86 production component hashes,
eight diagnostic deployment hashes and 15 earlier attempt guards match their
baseline. The new guard is consumed and was not reset. No additional account
request was launched while analyzing the owner result.

### SearchParty research: distinguish successful HA context from original SDK

The October18 research audit identifies three separate bundles: original SDK Mac
GSA, frozen successful HA Windows GSA, and reduced-format Windows diagnostics.
Six frozen HA source files match their deployment manifest. The successful HA
composer sends full CPD with Boolean flags and legacy GSA headers under Windows
akd, whereas current diagnostics trim CPD, stringify flags and add headers. The
latest preserved-identity/original-SDK refusal tested Mac GSA, so it does not
close the frozen-Windows-format discriminator. This is source/acceptance evidence,
not a raw successful wire capture or proof that format caused the missing grant.

A new offline lab implements eight combinations of flag types, context fields
and supplemental GSA headers while retaining Windows service declaration, user
agent and SRP fields. Sixteen init/complete fixture cases run with networking
denied. Both candidate frozen-Windows outputs equal the actual frozen HA
composer's parsed plist and headers. A single-attempt injected-transport gate
refuses retries, incomplete challenges, delegation and reports. Evidence helpers
separate verified proof from status and distinguish eleven fixed token categories
without saving token values or dynamic names. They never equate token presence
with usable report authorization.

Current official upstream account.py matches the retained 0.10.2 source.
OpenTagViewer's older delegate documentation differs from its pinned code; that
code uses accountsd, so an akd delegate-label swap is not a demonstrated fix.
The published October Windows workaround demonstrates MME/Keychain, not
SearchParty. Detailed sources, pinned revisions, limitations and a staged live
plan are in private upstream-onboarding/grant-research-20261018/
RESEARCH-AND-TEST-PLAN.md. Validation: 240 tests including 43 new cases, Ruff and
public scan passed. No new Apple requests, account-state reads, native calls,
HA changes, restarts, deployment or guard resets occurred. The next candidate is
implemented offline; a new HA form and guarded live attempt remain to be added.

### Frozen Windows HA authentication control deployed

A separately guarded HA flow reproduces the successful frozen HA GSA wire
context: Windows akd, all 15 CPD fields, Boolean flags, serial zero, legacy Accept
and no supplemental Xcode/app-info GSA headers. An isolated child uses the pinned
original SDK for SRP and full CPD composition; its only GSA composer is matched
against the frozen HA outputs. The existing RAM-only snapshot selects the active
Python ADI identity without reading account tokens, vaults or items. The child
restores existing provisioning only; it cannot provision a new identity.

The new findmy_frozen_windows_auth_attempt.json guard is distinct from all spent
controls. At most one init and one complete are allowed, with fresh verified
transports, no redirects/retries, and refusal of malformed successful challenges
before password KDF. Only _gsa_authenticate runs: no verification request/submission,
delegation, settings, recovery or reports. Apple may automatically send a code
with its challenge. hsc409 after a verified proof is classified as verification
required even if the original SDK omitted that interpretation; ambiguous statuses
are stopped rather than labelled authenticated. No follow-up request is made.

Both stages record bounded numeric status and fixed wire assertions: Windows
GSA, full Boolean CPD, legacy headers, matching UID/device binding and serial zero.
The parent's strict validator refuses missing, inconsistent or additional fields.
Credentials, machine headers and proofs stay transient; no account is persisted.
Timeout/cancellation reaps the owned child. Validation: 259 flow/adapter cases,
16 continuation cases, actual pinned SDK with denied networking/native fixtures,
Ruff and public scan pass. Independent checks were run in parallel; live Apple
attempts remain sequential to preserve attribution and avoid overlapping account
sessions. Seven diagnostic files were deployed with rollback copies; production
files and all 16 earlier attempt guards were preserved. Activation/readiness is
recorded in private frozen-windows-validation.json. No Apple attempt ran while
preparing or opening the form.

### Frozen Windows owner result: authentication completed

Observation aebb93c795a449ed97586c74845ebe73 confirms GSA init and complete both
returned transport HTTP200, ec0 and hsc200. The original SDK returned AUTHENTICATED
only after server-proof verification and SPD decryption; the bounded result is
therefore authentication_complete. Both wire assertions confirm Windows GSA,
full Boolean CPD, legacy headers, bound UID/device identity and serial zero.
There were exactly two GSA requests, no verification request or submission,
no delegation, no account persistence and no item/report access.

This establishes that the frozen successful HA GSA context can authenticate now
using the preserved Python identity. The previous original-SDK Mac control was
refused at init; the current result isolates acceptance of this Windows bundle,
not which individual field caused that difference. Reduced Windows controls had
also authenticated, so this is not proof that full CPD restores a SearchParty
grant. The next discriminator is one Windows MobileMe delegate exchange following
this exact GSA context, capturing all eleven fixed grant categories before any
settings, recovery or fallback. The transient PET was cleared when this bounded
worker ended; continuation requires a separately guarded owner-driven attempt,
not reuse of a saved credential from this probe.

The final flow snapshot's false MME/CloudKit/SearchParty flags reflect no flow
account being retained. They are not evidence that Apple omitted these grants:
no delegate request occurred. The private record was archived, all 86 production
files, seven diagnostic deployment files, four dependencies and 16 earlier guards
matched their baselines; the new guard is consumed and was not reset. No further
Apple request was launched during result analysis.


### Frozen Windows service-grant control prepared

A separate owner-driven flow repeats the accepted frozen Windows GSA format and,
only after verified authentication, permits one Windows accountsd MobileMe
exchange. It records presence of eleven fixed token categories and an unknown
field count; no token names or values are exported. Transport status, bounded
Apple status, response format, identity binding and cleanup are recorded
separately. Credential presence alone does not prove Find My report access.

The fresh findmy_frozen_grants_attempt.json guard leaves all 17 prior guards
unchanged. The child allows at most three sequential Apple requests, stops if
verification is required, and denies settings, recovery, keys, reports and
persistence. Credentials and machine headers remain transient. Timeout or
cancellation reaps the child. The pinned SDK fixture caught and corrected its
response interface difference before deployment: HttpResponse stores raw bytes
in _content, rather than content.

Validation: 275 offline cases, two actual pinned-SDK header/cleanup cases with
synthetic SRP proof and denied network/native access, Ruff and the public scan
passed. Independent offline checks ran in parallel. Eight diagnostic files were
deployed with rollback copies; 86 production files and all earlier attempt guards
were preserved. No Apple request ran during preparation. Activation and form
readiness are recorded in private frozen-grants-validation.json.


### Frozen Windows owner result: partial service grants

Observation c71b5f14bed0476cb1da7e387a2d306b completed both GSA operations
with transport HTTP200, ec0 and hsc200, then one Windows accountsd delegate
exchange with HTTP200, top status0 and service status0. The response was a plist
dictionary without a localized error. It contained three token fields: MME and
CloudKit were present, one unclassified token field was counted, and SearchParty,
all six tested device/friends Find My categories, key transparency and Maps were
absent. No dynamic token names or values were retained.

All canonical-login, PET, client-ID, ADSID, identity, machine and routing binding
checks passed. This reproduces the partial grant despite the full frozen Windows
GSA context; authentication success did not restore the tracking credential.
The broader missing category pattern is an investigative clue, not proof of an
account restriction or a specific Apple policy. The result alone does not identify
why Apple returned this subset.

Exactly three Apple requests occurred. Verification, settings, recovery, keys,
locations and account persistence were not attempted. Child account cleanup and
transport closure passed. The observation was archived; all 86 production files,
eight diagnostic files, five dependencies and 17 earlier guards matched their
baselines. The new guard is consumed and was not reset. The owner's phone showed
the raw abort translation key; the recorded result above is authoritative. No
additional Apple request was made while analyzing this result.


### New HA-only candidate: emulated macOS CoreADI

Public-source review identified sacca97/os-findmy-e revision
2096d875dac6b5ed2347a9ae8c39c7251c0d6ed6. It emulates the macOS library on
Linux instead of changing the declaration of an Android-produced proof. The
author reports SearchParty issuance and report acceptance; those claims remain
unverified here, including a README inconsistency about tag-report proof.

Static review found integration work required: upstream provisioning disables
TLS verification, login persistence saves passwords by default, Unicorn is
missing from the requirements, emulator execution is unbounded, extraction needs
path validation, and the provider lacks serialization. The candidate must be
adapted in isolation before any HA deployment or Apple request. The next gate is
an offline, restricted-child Mac-CoreADI initialization and runtime feasibility
check. The private coreadi-emulation-review/REVIEW.md records exact source paths,
findings and staged gates. Public sources were downloaded and syntax-parsed only;
no upstream code, Apple call, provisioning, credential read, HA mutation or guard
reset occurred during this review.


### macOS CoreADI offline emulator feasibility passed on HA Linux

The pinned x86_64 macOS CoreADI slice executed under Unicorn2.1.4 on the actual
HA Terminal & SSH add-on (Linux ARM64/musl/Python3.14). Two cold runs returned
Initialize rc0/status1 and the expected unprovisioned status-45061. Dispatch
runtime was0.105–0.109seconds; peak RSS44.8–44.9MiB. An initial wrong-architecture
wheel was corrected before these successful runs. HA Core process integration
has not been exercised.

The isolated child has CPU, address-space and parent wall-clock limits. Network
creation/connect/send calls were blocked by Linux seccomp and Python audit hooks;
a direct libc socket call confirmed denial. File-write and nested subprocess
checks were denied; a synthetic real-clock rollover and timeout/reaping check
passed. No provisioned OTP was generated. Virtual state stayed in memory.

No provisioning/login tool, Apple request, credential read, Core restart or
backend registration occurred. The offline bundle is separate from custom
components. All86 production files,8 deployed diagnostic files,5 dependencies
and17 prior attempt guards matched their baselines; the last service-grant guard
remains consumed. The next gate is bounded anonymous provisioning with verified
TLS. Runtime feasibility does not prove token issuance or tracking access.


### Emulated Mac anonymous provisioning accepted inside HA

One guarded attempt used the tested Mac-CoreADI emulator on HA Terminal & SSH
(Linux ARM64/musl). All3 allowed requests, lookup/start/finish, returned HTTP200;
start and finish returned ec0. Native provisioning and the final provisioned check
passed. A fresh offline process restored the protected anonymous state and again
confirmed provisioned status. No account request, key or location access occurred.

The adapted transport retained hostname/certificate verification, default verify
flags and pinned Apple roots. It permits only the fixed lookup and two exact
Apple MidService operations; no retries, redirects or proxy use. Ten offline
cases passed before launch. Anonymous machine state stays only in HA, separate
from the installed components and working production account. The consumed guard
was not reset. All86 production files,8 diagnostic files,5 dependencies and17
older guard baselines still match; the later service-grant guard remains consumed.

This confirms anonymous provisioning feasibility without a Mac, not account
login or SearchParty issuance. The next candidate is an owner-driven account
sign-in/grant check using this exact saved emulated machine. The bounded result
and receipt are in private coreadi-emulation-review/anonymous-result.json and
anonymous-validation.json. No HA Core restart or backend registration occurred.


### Emulated Mac owner sign-in/grant diagnostic prepared

A separately guarded HA flow binds sign-in to the exact anonymous machine state
that provisioned successfully. The Mac library, emulator, helper sources, SDK and
anonymous state are pinned. Native routing is checked against the stored identity;
the identity's UID/device/serial and Mac declaration are used throughout GSA,
verification and delegation. The local OTP subprocess has no network/write path,
uses the live clock and returns headers only over private IPC, never to a file.

The account worker uses the original pinned SDK for SRP; its only HTTP endpoints
are GSA, trusted-device push/validation and MobileMe delegation. It allows at most
7 requests: init/proof, optional one push and one code validation, post-code
init/proof, then one delegation. A second verification challenge stops the test.
Only the owner enters credentials/code in HA; the code step waits at most240seconds.
Credentials, SPD and returned grants stay transient. No account session is saved.
There is no provisioning, settings, recovery, Keychain, item-key or report path.

The owned worker group is killed/reaped on flow removal or expiry, including its
native child. The strict IPC schema permits fixed status fields and11 token-family
presence flags only. The new findmy_mac_coreadi_auth_attempt.json guard does not
reset earlier controls. Source/production baselines and anonymous state are
retained in private mac-auth-validation.json with rollback copies.

Validation:289 flow/adapter cases and lint pass. Two actual pinned-SDK constructor/
cleanup fixtures pass with synthetic SRP drivers and denied sockets; they are not
live authentication proof. The HA Terminal & SSH helper generated OTP/MID locally
with matched native routing and no Apple request. Fifteen diagnostic files were
deployed; all86 production files and20 protected guard/machine records were
preserved. HA Core activation and its own preflight/form readiness are recorded
in the private receipt. No diagnostic Apple sign-in request ran during preparation.


HA Core preflight initially stopped in the local OTP child before account access.
Bounded parent/child error records were added, retaining no raw stderr, headers or
credentials. A proposed allocator-preload workaround was not supported by the
record and was removed. Increasing the isolated worker/native child's virtual
address-space allowance from1536 to3072MiB cleared this startup failure; CPU and
wall-clock budgets remain. Exact startup error text was not retained, so the
record supports the tested budget correction rather than a specific native
allocator error diagnosis.

The actual Core flow now reaches its empty credential/unchecked-consent form only
after the pinned-SDK/TLS/native-header preflight succeeds. Production HomeCircle
loaded with2 entities after restart. All saved production, diagnostic, dependency
and20 protected guard/machine hashes were reverified. The new live-attempt guard
is still absent. No diagnostic Apple request ran during these local checks; the
owner's fresh credentials are required before the guarded sign-in can begin.


### Emulated Mac owner result: GSA accepted, challenge issued, no code submitted

Observation a69e2b59e8344f7eadc3850485c45d86 shows init HTTP200/ec0/hsc200,
complete HTTP200/ec0/hsc409, followed by trusted-device push HTTP200. The owner
received a code. The worker stopped as transport_refused before the code-entry
step, so code_submitted is false. No delegation or tracking access occurred;
cleanup and transport closure passed. The result was archived and all baselines
matched. The consumed guard was not reset.

Review found a concrete SDK-compatibility defect: its trusted-device push accepts
a successful HTTP response and returns text, whereas the Mac worker required a
plist. The old bounded record does not retain content kind, so it cannot prove
which body or transport-body check triggered the stop. The worker now accepts
bounded non-plist successful push bodies. GSA, code validation and delegation
keep strict parsing/proof requirements; a valid plist push error is still checked.
No response body or arbitrary error text is retained.

Schema2 records fixed response-kind and failure-category enums to separate format,
encoding, oversize, HTTP, TLS and connection failures next time. Four regression
cases cover successful text/JSON/HTML push responses and strict non-plist GSA
refusal. All293 tests, pinned-SDK synthetic-driver fixtures and lint pass. Four
diagnostic files were deployed with rollback copies. A distinct retry1 guard is
used; all21 earlier guard/machine records are protected. No Apple request ran
during preparation. Activation and fresh owner-form readiness are recorded in
private mac-code-response-validation.json. A fresh attempt needs new owner input;
the previous verification code/session is not retained or reused.

### Emulated Mac code-response retry: service grant returned

The owner-driven HA-only retry completed all seven bounded requests: initial SRP authentication, trusted-device challenge request, successful code validation, post-code SRP authentication, and MobileMe delegation. The challenge-request response was HTML-like with HTTP 200; accepting this successful non-plist response allowed the flow to reach the code form. Delegation returned HTTP 200 with top-level and service status zero, including SearchParty, MME and CloudKit credentials. This establishes credential issuance, not report access or location retrieval. All credentials remained in memory and were discarded; no account session, tracker keys or locations were saved. Cleanup and transport closure passed. Production, deployed diagnostic, dependency and previously protected guard/machine hashes matched their baselines. The retry guard is spent and has not been reset.

The next distinct milestone is a bounded report-access check using the same emulated Mac identity and a fresh owner-driven sign-in. Tracker-key discovery or recovery remains a separate step and must preserve the existing production account.

### Prepared: one synthetic report-service authorization query

Following the successful emulated Mac service-grant check, the isolated diagnostic now supports one report-service request after fresh owner-driven authentication and successful SearchParty delegation. It uses a newly random 32-byte synthetic hashed-key ID and a one-minute window, with no production account or real tracker keys read. The total cap is eight Apple requests, including at most one code submission and one report request; no automatic retry or reauthentication is allowed. Verified TLS, the same anonymous Mac machine identity, private-memory credentials, fixed diagnostic fields and cleanup limits remain enforced. HTTP 200 alone is not success: a recognized JSON `acsnLocations.statusCode` of 200 and an empty payload list are required. This validates only a synthetic query; it does not prove usable real tracker keys, decryption or fresh locations.

The new guard is separate from the spent service-grant guards. Diagnostic schema 3 retains only bounded numeric status and fixed booleans, never response bodies, credentials, synthetic IDs, encrypted report payloads or location values. The offline suite passes 313 tests, including successful and challenged paths, malformed/empty/refused responses, no-retry transport behavior, refusal without a successful grant, synthetic ID freshness, and IPC privacy constraints. The prior pinned SDK constructor/cleanup checks also pass. No live Apple request is made by preparation or preflight; the fresh owner form starts the account test.

### Confirmed: synthetic report-service query accepted in HA

The owner-driven emulated Mac report check completed in four Apple requests: initial challenge, successful password proof, successful MobileMe delegation including SearchParty, and one synthetic report query. No verification challenge was required on this attempt. The report endpoint returned HTTP 200 and recognized JSON with `acsnLocations.statusCode` 200 and an empty payload list. No machine-resynchronization or authentication-challenge header was present. TLS verification, same-machine binding, cleanup and transport closure passed. The diagnostic used no real tracker keys and accessed no actual locations. No account session or credentials were saved. The report guard is spent; no retry was started. Production, diagnostic, dependency and protected guard/machine hashes match their baselines.

This confirms Apple accepted the synthetic query under the emulated Mac credential, not that real AirTag reports can yet be fetched or decrypted. The next milestone is selecting an owned tag and establishing its usable key material through an isolated route, then validating one real report while preserving the existing production account.

### Prepared: selected Backpack keys with emulated Mac report authentication

The next isolated HA diagnostic reads the existing selected-item vault in memory, selects only the previously authorized Backpack, and binds that saved key source to the fresh sign-in by account DSID. It reuses no production account token. The selected key material remains in HA memory; no recovery, enrollment, production configuration write or session persistence is added. HA Core preflight verifies that the selected source is readable and derivable before showing the owner form. The Terminal add-on could not run that source check because a dependency was absent; that failed local invocation sent no Apple request.

The live check permits at most eight Apple requests including one report request, at most one trusted-device code submission, and no retry. The report query contains at most 200 derived public-key hashes for this single tag over a seven-day report window. Key coverage is intentionally limited near the saved alignment estimate and cannot establish absence from an empty result. The response must contain only requested key IDs, and decryption must authenticate and produce finite valid coordinates, nonnegative accuracy and a source report time in the requested history window. Only fixed flags, bounded report counts and a coarse newest-report age category leave the worker. Coordinates, raw reports, keys, account identifiers and credentials are not saved in diagnostic evidence. The independent attempt guard preserves the earlier successful synthetic-query result.

The offline suite passes 326 tests using the pinned SDK path, including real authenticated encryption/decryption with synthetic keys, tamper and invalid-time rejection, account/selection isolation, read-only vault behavior and symlink refusal. Production, dependency and previously protected machine/guard files remain at their captured hashes. Actual report retrieval and decryption for the owned tag remains unproven until the owner runs this new check.

### Backpack check: local parent import defect reproduced and fixed

The first owned-tag attempt recorded only a claimed attempt and the parent fallback outcome `unavailable`; no worker stage/count result survived, so this attempt does not establish whether authentication or a real report query completed. A deterministic local defect was reproduced separately: schema-4 result validation imported `tag_probe` by its standalone worker name inside the HA parent, where that module is not on `sys.path`. The prior tests had added the worker directory to their own import path and masked this mismatch. The validator now contains its fixed tag schema directly and does not import worker modules.

A regression launches an isolated Python process without the worker path and validates both a code-pending and final schema-4 result through a package import, while asserting `tag_probe` was never imported. The 328-test offline suite and Ruff pass. The parent also retains only fixed exception class, bounded source locations, recognized child event/schema and numeric process-exit metadata if result handling fails; raw child output and exception text remain excluded. The original failed guard and bounded observation are archived and preserved. A distinct retry guard is used for a fresh owner-driven test; no Apple request is launched by repair or preparation.

### Confirmed: real Backpack query accepted, no encrypted reports returned

The repaired owner-driven check completed four Apple requests: SRP initial challenge and successful completion, successful SearchParty delegation, then one report query. HTTP and recognized JSON report status were both 200. The saved tag source matched the signed-in account and selected Backpack uniquely; 200 derived public-key IDs were queried. Apple returned an empty payload list: zero encrypted, decrypted or invalid reports, with no resynchronization or authentication-challenge header. Cleanup, transport closure and protected/deployed baseline checks passed. No coordinates, raw payloads, keys or account session were saved; no retry was started.

This clears the local parent-validation defect and confirms request acceptance using real selected-tag key IDs. It does not validate the saved rolling-key alignment or actual location decryption. Because the single query covered only 200 candidate IDs, an empty result does not establish tag absence or lack of reports under other rolling keys. The next investigation should audit candidate-key coverage and saved alignment, then prepare a separately bounded broader search rather than repeating the identical query.

### Audited key coverage and prepared bounded full-range search

A network-free HA Core audit found that the previous candidate planner treated `get_max_index(now)` as an estimate of the current index, although the SDK defines it as the fastest-rollover upper bound. Combined with a 200-ID cap and lower-bound clipping, this omitted 479 possible lower indices in the captured snapshot. The audited interval, including the conservative 192-index padding, contained 864 primary indices and 11 secondary keys; the prior query contained 196 primary and four secondary keys. The snapshot contains only numeric coverage metadata and no keys, account IDs, exact dates or locations.

The new planner enumerates every key in the audited uncertainty interval, places all secondary keys first, and refuses a range that exceeds its explicit limits rather than truncating. Maximum 1,000 unique key IDs in at most five disjoint report requests of 200 IDs each; maximum twelve Apple requests including authentication and at most one code submission. It stops after the first usable authenticated report or any failure. No request is retried and no automatic reauthentication is added. The original account/key binding, read-only selected source, private-memory credentials/reports, cleanup boundaries and production preservation remain in force.

Diagnostic schema 5 records planned/queried key counts, planned/started batch counts, complete-range planning and completed-query flags, alongside bounded response/decryption metadata. It is validated in an isolated parent process without worker import paths. The 339-test suite verifies full inclusion of lower primary indices and secondary keys, disjoint batching, early stop, malformed/refused replies, oversized-range refusal, the five-request cap, no-result completeness requirements and both challenged/unchallenged authentication. Ruff and pinned SDK constructor/cleanup checks pass. Preparation sends no Apple requests; a fresh owner-driven form is required. Real location retrieval/decryption remains unproven.

### Confirmed: complete audited range queried, no reports returned

The owner-driven full-range check completed eight Apple requests: successful initial SRP, password-proof completion and SearchParty delegation, followed by all five report batches. All five transport responses were HTTP 200 with recognized JSON; the search continued only after application report status 200 and no invalid reports. All 875 planned unique key IDs were queried: 864 primary keys and 11 secondary keys. The saved source uniquely selected Backpack and matched the signed-in account. Apple returned no encrypted reports, so there was no decryption attempt, source-report timestamp or usable coordinate. No resynchronization or authentication challenge was reported. Cleanup, transport closure and protected/deployed baseline checks passed; no further Apple request was started. The attempt guard is spent and preserved.

This removes the earlier 200-ID truncation as the explanation for this particular audited range. It does not establish that the saved master/rolling keys or saved alignment still match the tag currently paired in Find My, nor that no reports exist outside that assumed range. The next useful investigation is a local-only comparison of selected key provenance and alignment against the last known working Backpack record before another account sign-in or report query.

### Confirmed: local Backpack key provenance and derivation parity

A network-blocked HA worker compared the selected current and earlier encrypted Backpack stores in memory. The account matched; the master key and both rolling seeds matched byte-for-byte. Item identifier and pairing-date metadata differed. The alignment differed by 213 indices and approximately 53 hours, but the audited search interval included both saved anchors and both secondary keys associated with the earlier anchor. Four sampled key sets derived by the pinned diagnostic SDK matched the installed production key implementation. Both saved reports were in the one-to-seven-day age category, with different source timestamps; neither is evidence of current location retrieval. Both encrypted source stores were unchanged throughout the audit.

The comparison made zero Apple requests and saved only equality flags, numeric alignment differences and coarse freshness categories. Production code, dependencies, anonymous machine state and all spent guards matched their baselines. The offline suite passes 347 tests and Ruff passes. These findings argue against migration key corruption, the sampled derivation implementation, or exclusion of the earlier alignment anchor as the explanation for empty results. They do not prove that the stored seeds still match the currently paired tag. The next investigation should distinguish fresh tag-key provenance from report-request context using the earlier working implementation, before another identical account/report test.

### Offline request-context comparison: original sequence path differs from diagnostic

A synthetic, network-denied test executed the actual `fetch_raw_reports` and sequence-key fetching methods extracted from the pinned FindMy 0.10.2 wheel and the current production source. Both produce identical request bodies for identical synthetic keys and a frozen clock. The production caller supplies sequences of keys to `fetch_location`, so the SDK constructs one fetch entry per key and puts every ID in `primaryIds`, including IDs generated from secondary keys. The diagnostic instead constructs one fetch entry per batch and separates IDs into `primaryIds` and `secondaryIds`. With three synthetic keys (two primary, one secondary), the original path produces three entries with three primary IDs and zero secondary IDs; the diagnostic produces one entry with two primary IDs and one secondary ID. The endpoint, client context, seven-day time window and set of IDs match. Tests also exercise the original path with 1 and 200 keys. This compares executable builders, not captured historical wire traffic; both SDK request forms exist, and the difference alone does not prove Apple treats them differently.

The report headers on both paths carry machine authentication; the original report call does not request the optional Xcode client-info headers. The diagnostic uses manually constructed Basic DSID/SearchParty authorization while the SDK delegates Basic encoding to its HTTP client. Transport defaults differ (aiohttp versus explicit `http.client`, including compression/connection defaults), and the anonymous machine/session provenance differs. These remain candidate contextual differences, not demonstrated causes of empty reports. Automatic retries for empty HTTP bodies in the SDK cannot explain the observed recognized JSON status-200 responses with empty report lists; those SDK responses return without retry.

Code tracing confirms normal production polling loads saved accessory material and updates alignment only after matching returned reports. It does not refresh master/rolling seeds. Protected discovery retrieves accessory records through the Keychain/CloudKit path and can export fresh master, rolling-secret and alignment data. Matching saved stores proves local consistency, not freshness against Apple's current records. A fresh key recovery is therefore not yet justified as the next action.

The next controlled live comparison should reuse one fresh authenticated session, the same selected-account-bound Backpack IDs and the same frozen time window. Compare the existing grouped/split-ID body with the original one-entry-per-key/all-primary body, each at most once and at most 200 identical public key IDs; stop on a usable authenticated report or any error/challenge. This is a proposed diagnostic, not deployed or run. Authentication plus two report requests would be bounded separately, with no automatic reauthentication, retries, enrollment or production writes. Only counts, statuses, format labels and coarse source-report age should be retained. Zero Apple requests were made by this comparison; production, dependencies, anonymous machine and spent guard baselines matched.

Validation: the complete isolated diagnostic suite passes 350 tests; Ruff passes for the new comparison and tests. The public privacy guard checks 248 files without flagged patterns. The synthetic comparison receipt is retained privately with source hashes; no credential, real key ID or location was read by these new tests.

### Prepared: paired Backpack request-format control

The isolated diagnostic now compares two report bodies in one authenticated emulated Mac session. It selects the first maximum 200 IDs from the same bounded full-range planner (secondary keys first, then ascending primary keys), verifies the selected Backpack belongs to the signed-in account, and freezes the IDs, seven-day window and report headers. It sends the existing grouped/split-ID body once, then the original SDK sequence body once: one fetch entry per ID, all IDs in `primaryIds`. The sequence builder is checked against execution of the pinned SDK methods with 200 synthetic keys. This is a sample of the uncertainty interval, not full-range coverage.

The test stops after the first usable authenticated report, or any transport, application, response-format, decryption or authentication-challenge failure. Maximum two report requests and nine Apple requests total, including at most one code submission. No automatic retry or reauthentication; existing spent guards remain untouched. A distinct one-use guard protects this attempt. Per-format evidence contains only fixed format labels, started/recognized flags, bounded status/counts and coarse source-report age, with strict schema 6 validation in both the child and isolated HA parent. Key IDs, raw responses, keys, coordinates, tokens and account identifiers are not retained. Existing source, machine and production stores remain unchanged. Owner credentials and any fresh verification code must be entered directly in the HA form; preparing or opening that form launches no account/report request.

Preparation validation: 370 offline tests pass, including both authentication paths, first/second-format success and failure, challenge/decryption stops, exact SDK body parity at 200 keys, a third-request refusal and isolated parent imports. Ruff and the 248-file public privacy check pass. The diagnostic bundle was copied with per-file verification, HA Core configuration check succeeded, and Core was restarted. Previous spent guards were preserved; the paired guard remains unclaimed before owner submission.

HA Core network-denied preflight completed successfully and the live form displayed the paired-test title, request bounds, per-format diagnostic scope and unchecked confirmation field. Post-restart protected baselines matched. No new Apple request was started during preparation; the form is ready for owner entry.

### Confirmed: both report request formats accepted and empty

The owner-run paired test completed five Apple requests: successful SRP initial challenge and password proof, successful SearchParty delegation, and both report formats. No verification code was required. Schema 6 evidence confirms both `grouped_split` and `sdk_sequence` queried the same selected 200-ID sample. Each returned HTTP 200, recognized JSON and application status 200, with zero encrypted, decrypted or invalid reports. The saved source matched the signed-in account. No resynchronization or authentication challenge was reported. TLS, same-machine binding, cleanup and transport closure passed. No coordinates, payloads, keys or account session were retained. The owner screenshot displayed the older full-range result wording; the recorded schema and per-format rows establish that this was the paired test.

Production, dependencies, diagnostic bundle and earlier protected machine/guard baselines matched. The paired guard is now spent, archived and protected; no retry or new Apple request was launched. This test does not support request grouping or primary/secondary placement as the explanation for empty results in the selected sample. It does not establish fresh tag-key provenance, current report availability or equivalent report behavior outside that sample. Next establish whether the currently paired Backpack has a recent report in Apple Find My, then use a separately scoped fresh key/alignment comparison if appropriate. Repeat sign-ins with the same stored data are not justified by this result.

### Native Find My freshness observation after paired test

Apple Find My displayed the selected Backpack as Nearby and Now. Only those fixed UI labels were retained; no map, address, coordinates, keys or other items were saved. This confirms the native app currently sees the selected item, but exposes no exact cloud-report timestamp and does not establish a current report on the HA report endpoint. The native app may synchronize on launch; its network traffic was not instrumented. No new HA account/report diagnostic was started. Protected production, dependency, diagnostic and spent-guard baselines matched.

Source tracing confirms protected fresh discovery is separate from ordinary report polling: `prepare_recovery` checks CloudKit zone access, `open_recovery` obtains recovery choices, and `discover` unlocks keychain material and fetches accessories before any selected-item export. The already successful report-authentication probe does not implement this protected discovery path, so a fresh key comparison cannot be obtained by repeating the paired report test. A future isolated comparison must stop at CloudKit metadata failure, require owner device/passcode entry only in HA if recovery is reached, compare only the selected accessory in memory, and omit the normal selected-item/account export that would replace saved state. Fresh keys were not acquired by this observation.

### Prepared: fresh-discovery CloudKit prerequisite using emulated Mac credentials

The first live prerequisite for a fresh key/alignment comparison now uses the successful HA-only emulated Mac authentication and freshly delegated MME/CloudKit tokens. It binds the sign-in to the saved Backpack account and unique selected label in HA memory, then allows exactly two ordered metadata targets: the SearchParty container initialization URL and the fixed shared gateway's named BeaconStore zone-retrieve URL. No server-supplied routing URL can receive a request in this checkpoint. There are no report requests, item-record fetches, Keychain recovery, passcode prompts, PET refreshes, enrollment or selected-item exports. Fresh key comparison remains pending successful metadata access and a separately implemented protected continuation; opening this form does not establish fresh key provenance.

The installed CloudKit implementation is imported under namespace stubs in a separate child interpreter without loading HomeCircle setup. All installed SDK Python sources are checked against a pinned manifest. Instance-local HTTP adapters force the bounded verified-TLS transport and refuse every other URL, redirects, retries, a third metadata request, and an out-of-order request. The parent authentication sequence remains capped at seven requests, with at most two additional metadata requests (nine total) and one code submission. The separate discovery guard is independent of all spent report guards.

Schema 7 retains only fixed discovery outcomes, account/zone/container flags, parser-presence flags, bounded HTTP status and fixed error categories, request counts and cleanup flags. It saves no bodies, credentials, user/routing identifiers, keys, coordinates or account session. A distinct network-denied subprocess verifies dependencies, UUID compatibility and strict TLS during HA preflight. The 386-test suite passes, plus the 16 discovery tests pass after the account-binding refinement. Tests execute the installed CloudKit request builder/parser with synthetic responses, verify named zone-retrieve operation type 201, both authentication paths, HTTP/transport failures, account mismatch and missing-token refusal, strict targets and isolated parent validation. Ruff and public privacy checks pass. Production and earlier protected baselines matched before deployment. No live Apple account or metadata request has started during preparation.

The first live local-only dependency preflight stopped before any Apple request: the generic SDK derives its CloudKit hardware ID by parsing the account device identifier as a UUID, but the existing emulated Mac identity carries a UDID-form identifier. A child-only client subclass now preserves that original device identifier in headers and the request device-identifier field while using the already provisioned host UUID for the separate hardware-ID field. No identity, provisioning state or production source was changed. This mapping is a diagnostic hypothesis, not proven Apple compatibility. The real SDK builder/parser fixture now verifies both fields for a UDID-form identity; all 16 focused tests pass. Preflight failure evidence contains only fixed stage/category fields.

After the child-only identity mapping correction, HA Core network-denied preflight passed and displayed the new CloudKit access-check form with the explicit metadata-only scope and unchecked confirmation. HomeCircle still appeared with two entities. All protected/deployed/dependency baselines matched; the new metadata guard remained unclaimed. No account or metadata request was launched by preparation.

### Fresh-discovery attempt stopped before CloudKit: authentication HTTP 429

The owner-run schema 7 checkpoint made two Apple requests. The initial SRP challenge returned HTTP 200 and Apple status zero. Password-proof completion returned HTTP 429; the strict transport stopped without delegation, verification or any CloudKit request. No protected recovery, device passcode, item records, fresh keys or locations were accessed. The result does not establish an incorrect password or a CloudKit authorization failure. Authentication transports closed and cleanup succeeded; the discovery cleanup default is false because no discovery client was created. TLS and same-machine checks passed.

The failed attempt and new guard were archived; the guard remains spent. Production, diagnostic, dependency and earlier protected machine/guard baselines matched. No retry, new provisioning, identity rotation or scheduled follow-up was launched. The diagnostic did not retain Retry-After, so neither the precise rate-limit scope nor a supported retry time is known. Additional account sign-ins should stop while rate limiting remains unresolved. Fresh CloudKit access and the key/alignment comparison remain untested.

### Offline follow-up: explicit 429 and bounded Retry-After diagnostics

Prepared locally, without deployment or another Apple request: GSA transport now distinguishes HTTP 429 as `rate_limited` and stops before reading an error payload or sending another request. Authentication events and CloudKit metadata rows can retain optional Retry-After evidence as a fixed category and bounded integer seconds only. Numeric seconds and UTC HTTP dates are supported; absent, malformed, oversized and waits exceeding seven days remain explicitly unknown/over-limit rather than being truncated. Raw headers are never retained. Existing saved event schemas remain readable.

The owner result presentation detects HTTP 429 at the actual authentication or metadata operation and displays a specific rate-limit notice, including a usable Retry-After interval if present. The interval is a minimum server hint, not a guarantee the next attempt succeeds. Missing historical headers are not reconstructed: the already recorded attempt still has no known cooldown. No timer, scheduled follow-up, automatic retry, identity rotation or guard reset was added. The current deployed bundle and all protected production/dependency/machine/spent-guard baselines match. These changes remain local pending review of a later manual test.

Validation: all 412 isolated diagnostic tests pass, including 26 new offline rate-limit cases. Ruff passes and the public privacy guard checks 248 files without flagged patterns. No deployed source, attempt guard or Apple account state was changed.
