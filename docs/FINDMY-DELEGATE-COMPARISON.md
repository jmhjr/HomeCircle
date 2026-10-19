# Fresh service-token comparison — October 14, 2026

The saved-session baseline succeeded today, independently of fresh authentication.
The next isolated comparison targets the service delegation stage. The production
SDK now accepts an optional transient `delegate_client_info` override, with the
prior GSA-label fallback retained by default. No default profile was changed.

A private six-file candidate has been prepared. After one
fresh GSA/verification exchange, it requests MobileMe delegation first with the
existing Android Music label, then with the same Android device's akd label. The
comparison restores the same authenticated state and reuses the same machine
headers. Synthetic checks verify equal request bodies and Basic credentials;
only the service client-info label differs. Each delegate request disables
redirects/retries. The wrapper refuses another comparison on that account object.

The candidate observes token-presence booleans and bounded numeric statuses only.
After a successful comparison it runs the normal missing-CloudKit-token settings
hop, where needed, including the new Search Party presence diagnostic. It then
discards transient authentication state and closes the setup. Its replacement
recovery entry point never calls CloudKit zone access, escrow/recovery metadata,
device passcode submission, item discovery or report fetching. The user-facing
completion message tells the owner to close the setup. No account or item is saved.

This is a diagnostic candidate, not a release or a proven fix. Its files, manifest
of installed/candidate source hashes and synthetic tests remain in the ignored
private lab. The owner explicitly approved installation/restart and the protected
fresh-authentication scope after preparation. No protected session or item data
was opened during installation.

Validation: 529 HomeCircle tests, 873 SDK tests (five existing dependency warnings),
and four private synthetic comparison/cleanup tests passed. Ruff, whitespace and
the public-file privacy guard passed. Live HA configuration validation must occur
before any restart if the candidate is installed.

## Private installation and owner handoff

The six candidate files were installed with original-source hash checks, a
code-only rollback copy, and candidate hash verification. The existing working
prototype vault was not read or written. Live Home Assistant UI configuration
validation reported that configuration would not prevent startup. The approved
Core restart was then confirmed in the UI.

After restart, HomeCircle loaded and its Configure button became available.
Configure → Apple Find My accounts → Add an Apple account reached the blank Apple
email/password form successfully. No Apple credentials were entered and no Apple
login or delegate request was launched by the agent. The form is left open for
the owner; a phone can start the same path in its own HA session. Other unrelated
integrations were still finishing startup at handoff.

The owner should complete one private login/verification sequence, then close the
setup when the comparison-complete message appears. No device unlock passcode is
needed. Paired issuance and settings results remain unmeasured until that attempt.
A private allowlisted log filter is installed alongside the lab tooling for
extracting only the two profile outcomes and settings-presence/status flags.

## Initial-sign-in refusal before comparison

The owner's subsequent attempt displayed the service-refusal message on the
initial sign-in screen. The filtered current Core log contains
`stage=signin code=findmy_apple_unavailable` and no paired delegate or settings
observations. The comparison therefore has no live outcome. The current adapter
did not retain the exact HTTP status for this failure; the exception class covers
429 and 5xx responses. Its wording does not establish a temporary outage.

Two account-free controls from HA, with the current integration's verified TLS
trust context, returned HTTP 503 and HTML for both Android Music and Android akd
client-info labels. One additional control using the configured identity's
CFNetwork/Darwin user-agent versions also returned 503/HTML. These junk-body edge
controls reproduce a refusal without account credentials; they do not establish
the exact status of the owner's request, a general Apple outage, or the behavior
of a fully formed authenticated exchange.

The first control implementation omitted the integration's bundled legacy Apple
root, and its TLS verification failed locally. That control error was corrected
by using the integration's existing fingerprint-checked trust-context function.
The failed TLS controls are not evidence about the owner's login or a TLS defect
in the integration. Certificate and hostname verification remained enabled.

No owner login/code retry, provisioning request, vault access or HA restart was
performed during this investigation. The installed paired-test candidate remains
in place, stopping before recovery. A local adapter improvement now preserves
only the bounded HTTP status, fixed request category and bounded Retry-After
seconds for service-refusal exceptions. At that checkpoint the logging improvement
was local; 533 HomeCircle tests, Ruff and the privacy guard passed. Another unchanged
owner verification-code attempt is not justified by these results.

## Refusal diagnostic installation

After the owner's instruction to proceed, only `signin_error` was replaced in the
private installed setup candidate. AST comparison verified that every other
function, including the stop-before-recovery experiment, remained unchanged.
The prior code was saved for rollback and the installed bytes were hash-verified.
All 41 focused setup and private comparison tests passed.

The live HA configuration check passed before the approved restart was confirmed.
After restart, the HomeCircle detail page showed its loaded service entry with
Configure available. Unrelated integrations were still finishing startup. The
diagnostic addition is now installed and loaded. No Apple login was launched and
no protected vault was opened by the agent during this deployment. Fresh login
and the paired delegate comparison remain unresolved.

The independent October 14 report in
[FindMy.py issue 278](https://github.com/malmeloo/FindMy.py/issues/278) describes
missing Search Party issuance even with an Android akd label. That lowers the
expected yield of this variant. It neither measures this account's settings
response nor establishes Apple's authorization policy. A negative local result
would deprioritize this one label difference; it would not prove the need for a
particular platform, entitlement or enrollment operation.
