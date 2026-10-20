# Published beta 20 Ubuntu/glibc validation

This isolated Linux-only harness targets the exact published `v0.1.0-beta.20`
ZIP on native amd64 Ubuntu 24.04 with glibc, source-built CPython 3.14.6 and
Core 2026.10.2. Runtime acceptance is pending until a completed run and its
receipts are independently reviewed. Do not run Python from this harness on
macOS.

The host independently checks the public prerelease and tag, then downloads
the release ZIP and inventory through their canonical public URLs. Release
`418643687`, ZIP asset `659912694`, source commit
`d02a9bdb9027cb51c99165a09ba50d5b175f5fb9`, 604,937 bytes and SHA-256
`fc0b365d9688459504f874af5c38393e24145d657f15f1def8ada9184f363285`
must match. Inventory SHA-256 is
`5e724f69ff20a711dd87b2a39ed96818781813bb6f1e7b3addedc6e048593d77`.

The immutable 327-file tagged source supplies tests and validation scripts.
Its archive SHA-256 is
`261aeb3219071a44e1c6ca53f2f18e26624ae450a641d29be32450ee265d4818`;
its source inventory is
`be693aef2f7a049cc4c0752179069664c86e444e24cc9fb01393d40f5d1288b1`.
Every integration file used in acceptance comes from the published 112-file
ZIP. Neither the working checkout nor a rebuilt candidate substitutes for it.

The base image is the official Ubuntu 24.04 Linux/amd64 manifest
`sha256:a2d43bffc46670d7108bb3c0468c67c5557c4c92e83e1e34cbff1322ad1b94dc`.
CPython is built inside Linux from the official
[3.14.6 source release](https://www.python.org/downloads/release/python-3146/),
whose source tarball SHA-256 is
`143b1dddefaec3bd2e21e3b839b34a2b7fb9842272883c576420d605e9f30c63`.
Active libc, imported Core, Python and Unicorn native-library identity are
checked in the tested environment; an Ubuntu host label alone is insufficient.

Dependency setup uses exact Core 2026.10.2 constraints, SHA-256
`7baa9a8f39ddeb9c5bb60a1036f6d5e33f4b84267f151f53cc2b95ef031a21b5`,
and test plugin `0.13.373`, whose metadata targets that Core release. Declared
startup component requirements are installed before networking is disconnected.
Acceptance covers real synthetic Core/HomeCircle startup, the exact packaged
native worker and provider lifecycle, and the backend suite. Only the named
optional retained-Apple-installer fixture may be skipped. An isolated copy of
the lifecycle script has exactly two declared changes: the published ZIP hash,
and permission for glibc's `os.posix_spawn` audit event only when its executable
and arguments exactly match the already approved worker command. Unknown
process launches and the existing file and network restrictions remain
blocked. Acceptance requires one or two actual approved spawn events and no
denied unknown launches. Original and executed script hashes and both
substitution counts are recorded; the tagged script and product are unchanged.

The runtime build and test container are owned by this invocation. Acceptance
runs without external networking, host mounts, published ports or Linux
capabilities. Each phase and the whole invocation have fixed deadlines and
separate cleanup allowance. Only narrow synthetic JSON summaries are uploaded;
private temporary files, logs, test state and the owned runtime image are
removed. No owner account, GitHub credential or Apple binary enters the test
container. Production, V2, main, release tags/assets and existing harnesses are
outside its mutation scope.

This is one amd64/glibc/Core target. It does not certify installation methods,
all Core versions or ARM64 glibc, repeat HACS delivery, qualify owner account or
movement/physical-display behavior, or change the existing prepared backup
procedure and its limits. The separate
[publication/HACS result](https://github.com/jmhjr/HomeCircle/blob/e0535fa909cd44cdd0f3d9a83189a93a9e2843c7/docs/BETA20-PUBLICATION-VALIDATION.md)
retains its own scope. Normal enabled-entry/full-system restore and automatic
anti-rollback remain unqualified, as do the remaining stable release gates.
