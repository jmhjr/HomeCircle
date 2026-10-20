# Find My local identity runtime

HomeCircle's provider, IPC worker, download bootstrap and onboarding adapter are
maintained with HomeCircle. They contain no Apple account or provisioned identity
data. Every new account setup creates its own local device identifiers.

## Emulator

The four files in `emulator/` (`adi_run.py`, `harness.py`, `macho.py`,
`stubs.py`) come from
[sacca97/os-findmy-e](https://github.com/sacca97/os-findmy-e/tree/2096d875dac6b5ed2347a9ae8c39c7251c0d6ed6/tools/machoadi),
revision `2096d875dac6b5ed2347a9ae8c39c7251c0d6ed6`.
The upstream MIT license and copyright notice are retained in `emulator/LICENSE`.
Only the loader, execution harness, virtual system calls and ADI dispatch are
included. Upstream login, password persistence, insecure transport and diagnostic
commands are not used by HomeCircle.

The emulator runs in a child process. The parent supplies the exact public
library path and private machine state through bounded standard-input IPC.
The child denies networking, subprocesses and disk writes, uses real time and
has CPU/memory limits. The parent enforces operation deadlines and reaps the
child on cancellation. Machine material is serialized only into HomeCircle's
encrypted account vault after explicit item selection.

## Runtime dependencies and public Apple download

The Python Unicorn bindings are installed by Home Assistant from the pinned
manifest requirement `unicorn==2.1.4`. Unicorn provides separate licensing
information for its core and Python bindings:
[Unicorn license](https://github.com/unicorn-engine/unicorn/blob/2.1.4/COPYING).
No Unicorn binary or wheel is included in HomeCircle's release ZIP.

Apple's CoreADI library is not distributed in the release ZIP. On first setup,
HomeCircle downloads the pinned public iTunes 12.8.3 installer payload from
Apple's HTTPS download service. A fixed-range payload is independently
SHA-256 verified; a server ignoring Range requires verification of the complete
installer. The bootstrap reads only the expected regular CPIO member and its
x86_64 Mach-O slice, never materializing archive paths.

Installer SHA-256:
`dd08b9967db3e5847955fa168ce880303abf5f36de12abb2061e7ef1a25be214`.

Required library slice SHA-256:
`2eafc3c79c7f41a8afbfbeaaf23ee5dab5ad5bda55ec8e54dbc0ddf1d20ce630`.

The library is a locally cached Apple binary, separate from the MIT emulator.
The source license does not purport to license Apple's binary.
Its acquisition and platform acceptance must be included in release validation.

## Local hardening adaptations (unreleased stable candidate)

The worker authenticates one bounded, regular-file descriptor snapshot and passes
those exact immutable bytes to the emulator; the loader does not reopen the
library pathname. The parent resolves the installed Unicorn package in an
executor and passes only that package path to the child, including when Core
uses a private dependency directory. This is synthetic import coverage, not
qualification of native execution on every supported platform.

Default and Mac random hooks use the host OS-backed `secrets` source and fail
without a fallback pattern. Guest scratch, object and heap allocations are
bounded; combined provisioning inputs and dispatcher metadata must fit the
256 KiB scratch budget before writes. Guest output and random buffers are
bounded before host allocation/read. The child retains its existing operation
and process resource limits. Its Python audit hooks restrict ordinary Python
network, subprocess and write operations; they are not an OS sandbox for native
dependencies. See the repository's focused hardening validation for synthetic
controls and the still-open real Apple provisioning/platform acceptance.
