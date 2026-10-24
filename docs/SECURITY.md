# Security and support

For a suspected HomeCircle security vulnerability, use
[Report a vulnerability](https://github.com/jmhjr/HomeCircle/security/advisories/new)
on the repository's Security page. Private vulnerability reporting was enabled
and its enabled state was freshly verified through GitHub's API on October 23, 2026. GitHub describes this
private reporting channel in its
[reporting guide](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/report-privately).
Do not open a public issue containing exploit details or private account data.

Include the HomeCircle version and source/package hash when available, Home
Assistant version, installation method, affected behavior and a minimal synthetic
reproduction. Exclude passwords, verification codes, device passcodes, account
tokens, vaults, keys, full backups, raw provider responses, coordinates and
location screenshots. Redact diagnostics before submitting them, including in a
private report. A reproduction must not deliberately consume owner passcode
attempts or interfere with another account or device.

For ordinary setup questions and non-sensitive bugs, use
[HomeCircle issues](https://github.com/jmhjr/HomeCircle/issues).
Provide expected and actual behavior, environment versions and sanitized steps. Read diagnostics locally and quote only needed fixed status codes/counts; no diagnostic file, log or backup upload is required. HomeCircle provides no hosted account relay, telemetry or support-upload service and does not automatically transmit a report.
Check the [setup guide](SETUP.md), [privacy policy](PRIVACY.md) and
[Find My recovery/restore instructions](FINDMY-SETUP.md) first where applicable.

Published beta 20 remains experimental. HomeCircle 1.0 is in preparation; this
policy does not declare it released, certify provider interoperability or promise
a response time. The [release plan](RELEASE-1.0-PLAN.md) records current acceptance
and supported-platform decisions.
