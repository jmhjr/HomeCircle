# Beta 19 validation

Date: October 19, 2026. Experimental prerelease `0.1.0-beta.19`.

HomeCircle signs in to Apple, recovers selected Find My item keys and polls
location reports on Home Assistant without a physical Mac, a separate helper or
manual YAML. Follow the [Find My setup guide](FINDMY-SETUP.md).

## Tested package

The deterministic installable ZIP contains 109 files. Its SHA-256 is:

`5f20d536e1b5378bef7f0b972bbfbc7ced911063aea16a0a8f56d2ffa1210cd2`

A clean release checkout rebuilt this exact archive, including the frontend.
The [format-equivalence note](FINDMY-BETA19-PACKAGING-VALIDATION.md#canonical-release-artifact)
separates this canonical archive from the live-accepted archive's two EOF-only changes.
The archive contains the MIT SDK and emulator with their notices. It contains
no Apple library, account credentials, provisioned identity, item keys or local
research state. Required public Apple software is acquired and hash verified
on HA; see [runtime provenance](../custom_components/homecircle/_findmy_runtime/PROVENANCE.md).

## Checks completed before tagging

- The development checkout passed 1,019 backend tests. The clean release
  checkout passed 1,018 tests, with one optional test skipped because its retained
  public Apple installer fixture is deliberately absent. Network access is
  disabled in these tests.
- All 109 frontend tests passed in the clean checkout. Pinned frontend dependency
  installation reported no known vulnerabilities.
- All 873 retained upstream SDK tests passed against the release's vendored
  namespace, allowing only loopback and Unix sockets. Official HA Core 2026.9.4
  hassfest validated the release manifest with zero invalid integrations.
- Actual-ZIP import readiness and separate-process installation, upgrade,
  restart, removal and post-removal restart passed in disposable HA Core.
- Ruff, whitespace checks, public-file privacy checks and exact archive/source
  inventory validation passed. No research commit history is included in the
  release branch.
- The unchanged native runtime passed isolated public-library acquisition,
  anonymous provisioning, OTP generation and cold identity restoration. That
  control used no Apple account or real tracker data.

## Actual HA acceptance

The tested host runs HA Core 2026.10.2 and Python 3.14.7 on an HA OS Raspberry Pi
with aarch64. Disposable Core regression tests use Core 2026.9.4. These are the
validated environments. Compatibility outside them remains unverified.

The owner completed full Apple sign-in, verification and trusted-device recovery
through the packaged flow, explicitly selected two AirTags and saved them.
Independent checks confirmed the saved selection, matching tracker registry
entries, no duplicate trackers and no saved password or transient service grants.
Automatic polling returned valid decoded Apple reports for both selected items.

Passwordless reuse after a real HA restart passed. The saved identity, machine
state, report credential, item keys and tracker identities remained unchanged.
Source report times did not move backward. Recorder history rows were not read.

A pre-password spinner stall was reproduced and fixed: preparation that completes
immediately now returns the login form in the same response, without relying on
a later progress notification or replaying consent input. The same path opened
the empty login form immediately after installation and restart. Regression tests
also cover delayed progress, cancellation, missing tasks and setup expiry.

## Experimental limits

Apple's services are undocumented and can refuse requests or change behavior.
A service refusal does not by itself establish a wrong password or a waiting
period. Reports can be delayed, and polling cannot force a new AirTag fix.
The accepted polls returned usable reports with existing source timestamps;
current physical-position accuracy and movement latency were not established
by this acceptance cycle. HomeCircle preserves the original report time and
estimated accuracy, including when retaining an older usable location.

Account sessions and selected item keys are encrypted locally, with the
decryption key stored alongside the vault. Protect HA storage and backups.
Passwords, verification codes and device passcodes remain transient. See
[privacy](PRIVACY.md#apple-find-my-connection).

The detailed [packaging record](FINDMY-BETA19-PACKAGING-VALIDATION.md) separates
earlier research, synthetic controls and actual package acceptance. GitHub asset
download and HACS distribution checks follow prerelease creation; they are
recorded separately from these pre-tag checks.
