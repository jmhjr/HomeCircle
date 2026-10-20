# Exact development preview: minimum-Core managed HAOS witness

This separate fixture is prepared for one fresh native Linux amd64/KVM guest:
HAOS 18.3, Supervisor 2026.10.2, Core **2026.9.4**, CPython 3.14.6. It has not run.
It uses the exact same-version unreleased `0.1.0-beta.20` preview, source
`9bf03eb45d2cf43274074534e9dfe2de841f4011`, 113-member ZIP SHA-256
`c4530d94be3b2996f8d6c8948db88a51868566047d68558eefde7967f270a861`.
This is managed dependency/setup/start/restart compatibility evidence. It does
not repeat the full backend suite, native worker or six-phase restore experiment.

The new code is restricted to its own QA folder. The existing C453 prepared
restore fixture, historical evidence, product source and root working files
remain unchanged. The parent folder's `CHANGE-MAP.md` records the reviewed
proposal and runtime barriers; source readback files are evidence, not runtime
success. No CI run or VM action occurs when preparing or testing this folder.

## Managed minimum-Core selection

The pinned HAOS disk is the same fresh 18.3 artifact used by the completed KVM
experiments. Actual QMP KVM acceleration, guest platform and the managed `/config`
mount are mandatory. Fresh official stable metadata currently chooses Core
2026.10.2, so this fixture separately observes that initial installation before
stopping it. It never installs HomeCircle into the initial newer Core.

Only the proven newly owned guest's bounded, account-free generated Core config
is retained privately and reset, while Core is stopped. The config mount itself
is preserved. Owner/user entries, credentials, candidate files, unexpected
ownership, symlinks, hardlinks, special files and excessive sizes are refused.
No existing guest, host configuration or owner installation can be selected.

There is at most one ordinary explicit target request:
`ha core update --version 2026.9.4 --backup=false --raw-json`. It runs while Core
is stopped. The CLI JSON result is only evidence that selection completed; Core
is then started and its actual container, running module/version, Python,
constraints and managed mount must independently match before candidate staging.
A failed target request or unavailable image is not retried or substituted.
This controlled empty-config version selection is not production downgrade or
storage-migration acceptance. Consumer documentation recommends backup restore
for real downgrades.

The official machine-image reference is
`ghcr.io/home-assistant/qemux86-64-homeassistant:2026.9.4`, index
`sha256:414dce485b4eebd9f929f293f7252340bada5715fc4a48b2b954d79195ed3019`.
Its Linux/amd64 manifest config ID is
`sha256:560be76a9ee5019c1b557241db8d1127550f21fba952a1a976c3d186f9b2cd9e`.
Actual running container reference and config ID must match before candidate
staging and after both observations. Core constraints must hash to
`962c9ccaf398e0b92b10ac9f765ac0f17e22238adc4e768deebc051ee8b60651`.

The actual CLI add-on version must be 2026.09.0. Actual update/start/stop help is
checked and the resolved executed `ha` binary is fingerprinted. The add-on image
version is not relabeled as a CLI source/application version. The reviewed CLI
reference has no generic `--version` flag, so none is assumed.

## Two observations and ordinary requirements

`initialize` starts the exact 113-file integration through normal managed Core.
The helper's real config and options flows create two fictional Persons with
explicitly registered and selected trackers. Settings remain nonempty and city
lookup is off. There is no provider/prototype/migration entry or managed provider
tracker, and no account, credential, passcode or recovery proof is supplied.
Both Life360 and Find My remain in the intended 1.0 scope; this fixture does not
qualify their authenticated behavior.

No pip/uv installer is called by this harness. There is no dependency preloader,
loader or image patch, changed manifest requirement, skip-pip flag or network
response stub. The real minimum-Core requirement manager performs normal
resolution. Before candidate setup, a bounded metadata-only child records the
six direct requirements. At least one must be absent, then all must be satisfied
after the real flow, before this witness claims normal installation. Packages
already supplied by the base image are recorded as such, not counted as new
downloads.

The helper checks the six manifest requirements and their actual 24-name
transitive dependency graph, applicable Core constraints and Requires-Python.
Metadata must originate in the actual system site-packages roots, with no
config-local dependency files and no custom pip target. An actually loaded
module's origin is distinguished from an unloaded package's import-spec origin.
The metadata/import-spec probe deliberately imports no provider or native
module; ordinary product loading can import its normal dependencies.

The first observation requires real on-disk entry/Person/registry/dashboard and
resource persistence, nonempty options, exact installed/loaded source and an
actual loopback HTTP 200 response matching all frontend bundle bytes. It retains
only hashes/counts/booleans/versions, with fixture identities kept private.

After normal online dependency setup succeeds, a positive connection control to
fixed non-provider `1.1.1.1:443` must succeed, then QMP closes the sole owned VM
NIC. A negative control and private guest-agent responsiveness must pass.
The controller stops Core and stages the `restart` instruction while stopped,
then performs one supported managed start. The second observation requires a
different real Core process with the same persisted selections/settings,
entry/registry/dashboard/resource identities, package/served bytes and accepted
dependency versions. A second closed-link control must pass before final stop
and owned QEMU/private-state cleanup. This is an offline restart after normal
online dependency setup, not offline reinstall or replacement-container recovery.

## Outcomes, bounds and retained data

Only `host.json`, `initialize.json` and `restart.json` may be retained publicly.
Exit 0 requires both observations and successful owned cleanup. Every unexpected
failure, timeout, target mismatch or cleanup failure returns nonzero with a
finite source-derived stage/code and fixed exception-type catalogs, plus bounded
dependency diagnostics when available. Unknown valid-looking labels are replaced
with fixed unrecognized sentinels or omitted; they are never copied as strings.
Nothing is converted into a known-safety-exception success. This experiment
makes no restore-safety or stable-release acceptance claim.

Initial package installation and synthetic setup use ordinary outbound NAT;
restart is offline through the VM's sole NIC. Provider/recovery request attempt
counts remain unmeasured. No port is forwarded and no host/shared folder,
GitHub token, owner state or existing HA instance is mounted. Private serial and
command logs, the retained fresh boot config, database/configuration, identities
and tokens stay within the disposable owned state and are destroyed. No private
raw data is included in public receipts.

The inherited controller deadline is 5,520 seconds with a 120-second cleanup
allowance; the unchanged outer runner uses 5,700 seconds and a 45-second kill
allowance. Every host/guest operation, dependency/setup wait, version transition
and phase shares that finite monotonic deadline. The inherited QEMU cleanup
requires the owned PID/start time/nonce before signals and removes private state
only after QEMU stops.

Run standalone contracts from this folder's parent with
`python3 -B -m unittest discover -s native-release1-minimum-haos -p 'test_*.py'`.
They execute standard-library host/reset/receipt logic only; no HA or native
packages are imported on the Mac. Independent review and an actual native run
are required before claiming this cell passed.

A reviewed Linux runner supplies the exact local `payload/homecircle.zip`, its
40-character QA branch commit and a fresh output path to `run_host.sh`. The
fixture does not create a release, tag, workflow or HACS authorization.

Primary source contracts: [stable targets](https://version.home-assistant.io/stable.json),
[explicit Core version selection](https://www.home-assistant.io/common-tasks/os/#running-a-specific-version),
[CLI update command](https://github.com/home-assistant/cli/blob/5.6.0/cmd/core_update.go),
[Supervisor update/start/stop](https://github.com/home-assistant/supervisor/blob/2026.10.2/supervisor/homeassistant/core.py),
[minimum-Core requirements](https://github.com/home-assistant/core/blob/2026.9.4/homeassistant/requirements.py).
