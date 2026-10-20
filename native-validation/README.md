# Native AMD64 validation handoff

Status: prepared locally; native execution has not started. The earlier emulated
AMD64 upgrade and recovery attempts remain failed and unqualified.

The payload contains the unchanged 112-file candidate, immutable published beta19
baseline, reconstructed retained-patch baseline, inventory, five transitively
required validation scripts and the frozen bounded Linux driver. It contains no
owner account, production configuration, location record or live authentication
material. `build_bundle.rb` verifies all ten fixed input hashes before copying.
The retained patch is a reconstructed baseline, not a current production snapshot.

Candidate ZIP SHA-256:
`f0477a91e78181fe1f8d80ada176a1739e10a7502abe7ee6ee2240571280d1f5`.
The candidate remains unpublished with manifest version `0.1.0-beta.19`.

## Execution options

Use an existing native x86_64 Linux machine with Docker, Bash, jq and GNU coreutils, or
the staged GitHub Actions workflow on Ubuntu 24.04 x64. The host and container
architecture checks refuse the ARM Mac. All Python executes inside the Linux
Core container. The container has a fresh disposable workspace and receives no
production mounts, Docker socket or owner credentials. Dependency downloads run
before the container is disconnected from networking for acceptance.

The unchanged driver runs both ten-phase upgrade/rollback sequences followed by
the full twenty-process recovery sequence. Original child deadlines remain
180 seconds for upgrade and 45 seconds for recovery; aggregate job bounds remain
2,100 / 2,100 / 1,200 seconds. A separate host deadline and owned-container cleanup
bound execution. Failure or missing receipts cannot produce acceptance.

For GitHub, stage `workflow.yml` as
`.github/workflows/native-amd64-validation.yml` and the runner files plus payload
as `native-validation/` on `codex/native-amd64-validation`. The job receives read
access to repository contents and publishes only its sanitized summary artifact.
No release, tag, production deployment, PR or merge is part of the job.

**The repository is public. Creating that test branch uploads the currently
unpublished candidate and its test inputs. No branch, commit or upload has been
created for this handoff.** The alternative is an existing private Linux runner
reachable through a user-supplied SSH destination.

## Scope

A passing native container run would qualify the frozen synthetic Core 2026.10.2
upgrade/rollback and recovery scenarios on native AMD64 Linux. It would not
establish native AMD64 HAOS-managed installation, Core 2026.9.4, glibc execution
of the integration, current production/HACS upgrades, live Apple recovery,
long-running provider acceptance or the remaining licensing/service-use gates.

Raw synthetic configurations remain in the disposable local workspace and are
excluded from the public artifact. Input pin receipts and safe summaries preserve
the distinction between a prepared job and an actual passing result.
