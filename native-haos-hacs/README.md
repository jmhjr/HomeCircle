# Disposable native HAOS/HACS rehearsal

Prepared harness; a passing live result must come from its sanitized receipts.
Nothing in this folder establishes acceptance merely by being prepared.

The controller refuses macOS and non-AMD64 hosts, requires accessible `/dev/kvm`,
launches a new QEMU guest, and verifies QMP `query-kvm` reports both present and
enabled. It downloads the pinned official HAOS 18.3 OVA disk, verifies compressed
and expanded hashes, and creates an independent overlay and UEFI variables file.
There are no host directory mounts, forwarded network ports, SSH keys or existing
VMs. User-mode NAT permits the public downloads HAOS and HACS need; it is not an
outbound firewall. The test config has only fictional People and trackers, no
provider account and no production location source.

The fixture uses normal HAOS HTTP binding inside this private guest so that
Supervisor's supported internal TCP health checks work as well as its newer
Unix-socket transport. No guest port is forwarded onto the CI host. Before a
management action, the controller checks the supported root `/info` lifecycle
state is `running` and relevant Core install/start/update jobs are complete.
Each stop/start sends one request, validates its JSON result, and observes the
actual container state inside its original 180-second total bound. Reported
Supervisor and CLI versions are observed runtime values, separate from source
inspection of the official API.

The supplied HACS 2.0.5 asset must have SHA-256
`97be6b824a4f38e683728cc6dd72367f6b8bad0a43428b1b3b987a3087adf413`.
All HACS source bytes are extracted from that archive, without runtime patches.
The candidate and published baseline archives must retain their established
`f0477a91...` / `5f20d536...` pins and exact 112 / 109 file counts.

The job's temporary `contents: read` GitHub installation token is delivered only
to a protected file in the new guest, then used by a direct disposable HACS config
entry. No human GitHub token, owner account, Apple account or production HA access
is involved. Official HACS OAuth onboarding and browser interactions are not
tested. HACS must remain enabled with an empty global background queue; neither
GitHub quota responses nor HACS's reserve handling are changed.

The eight phases install the published beta 19 release through the real HACS
backend, restart managed Core, create explicit persistent synthetic selections
and nonempty options, record the actual candidate branch-selection limitation,
stop Core and install exact verified candidate ZIP files, restart, seed three local synthetic
recovery-safeguard refusals without a provider exchange, download the published
release again through HACS, restore the matching stopped persistent-state snapshot while
retaining the newest safeguard, restart, and finally reinstall the candidate's
verified ZIP files with Core stopped and restart to
verify the three submissions remain blocked. Each restart must produce a new
Core process start time; an on-disk download alone is insufficient.

The isolated branch's root `hacs.json` uses repository-archive mode, but retained
HACS 2.0.5 cannot select this nondefault branch for its manifest when the repository
has only prereleases: its catalog resolves the request back to `main`. The helper
records that actual selector result without changing HACS's catalog or downloader.
The 112 package files and candidate ZIP are unchanged. This tests actual HACS
published-baseline installation and redownload/rollback, with managed HAOS
activation of the candidate's exact ZIP files. Candidate HACS download, ordinary
release selection and release-ZIP transport remain open. The coherent rollback uses stopped
filesystem copies of `.storage` and `image`; it is not a Supervisor backup/restore
test, Recorder continuity proof or live Apple recovery test.

`run_host.sh` imposes an outer GNU timeout. The controller has its own monotonic
whole-job bound, per-operation and per-phase limits, plus reserved cleanup time.
It can stop only its own QEMU child with the matching process identity and nonce.
It removes the entire private workspace, guest disk, token, logs and snapshots
after stopping that child. Only narrow, validated synthetic phase summaries are
copied to `public-summary`; raw configuration and log files are never uploaded.

For the already-approved isolated public test branch, stage this folder as
`native-haos-hacs/` and `workflow.yml` as `.github/workflows/native-haos-hacs.yml`.
The workflow fetches and hash-verifies the official HACS archive in the ephemeral
Linux job. It accepts manual dispatch and pushes affecting only this harness or
its workflow on the isolated branch, with read-only repository permissions. It requires the
previously staged candidate/baseline inputs under `native-validation/payload/`.
It does not publish a release or tag, merge a branch, or modify production.
