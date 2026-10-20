# Beta 20 dependency and notice review

Reviewed October 20, 2026 against published `v0.1.0-beta.20`, source commit
`d02a9bdb9027cb51c99165a09ba50d5b175f5fb9`, and the exact public ZIP with SHA-256
`fc0b365d9688459504f874af5c38393e24145d657f15f1def8ada9184f363285`.
This is an engineering inventory and notice check. Distribution, licensing,
service-use and branding acceptance remain open.

## What is distributed

The 112-file HomeCircle ZIP contains HomeCircle source, a modified FindMy.py
source copy, four MIT emulator source files, public certificate roots, the
compiled card including Leaflet, and their packaged notices. The six Python
manifest requirements and their dependencies are fetched separately by Home
Assistant. The ZIP contains neither Unicorn binaries/wheels nor Apple's
proprietary runtime library. An authored wrapper, copied source and a separately
downloaded dependency retain distinct origins and licenses.

`findmy==0.10.2` was an online validation reference. It is not a declared manifest
requirement and is not one of the 24 distributions below. Runtime Find My code
comes from `_vendor_findmy`, with its own pinned-source provenance and local
adaptations.

The observed versions below come from the actual
[Ubuntu/Core qualification run](https://github.com/jmhjr/HomeCircle/actions/runs/39474571811).
This is the manifest dependency closure, not a complete list of Home Assistant,
test tooling, operating-system packages or every nested vendored component.
Future installations can resolve different versions within manifest and Core
constraints.

## Observed Python dependency inventory

For all 24 distributions, exact-version metadata and a compatible Linux/pure
wheel were fetched from PyPI. Downloaded bytes matched the primary metadata's
SHA-256, and license files were extracted as data without importing any package.
The CI receipt records installed versions rather than every wheel digest, so
these are not all claimed to be the precise artifacts installed in CI. The
Unicorn native shared library was additionally byte-matched to the actual
runtime fingerprint.

The wheel column lists notice locations relative to that wheel's top-level
`<distribution>.dist-info/`, except where specified. The accompanying
[machine-readable inventory](https://github.com/jmhjr/HomeCircle/blob/35d4c3d184b810694c1bdd66778587f08a6d2e5b/docs/BETA20-DEPENDENCY-INVENTORY.json) records complete artifact URLs, hashes, exact
member paths and metadata discrepancies. “Direct” means one of the six manifest
requirements; other entries were in the observed transitive closure.

| Distribution | Relation | License evidence | Notice locations in inspected wheel |
| --- | --- | --- | --- |
| [aiohappyeyeballs 2.7.1](https://pypi.org/project/aiohappyeyeballs/2.7.1/) | Transitive | PSF-2.0 | `licenses/LICENSE` |
| [aiohttp 3.14.5](https://pypi.org/project/aiohttp/3.14.5/) | Transitive | Apache-2.0 and MIT llhttp | `licenses/LICENSE.txt`, `licenses/vendor/llhttp/LICENSE` |
| [aiosignal 1.4.0](https://pypi.org/project/aiosignal/1.4.0/) | Transitive | Apache-2.0 | `licenses/LICENSE` |
| [anisette 1.2.4](https://pypi.org/project/Anisette/1.2.4/) | Direct | MIT from wheel; metadata blank | `licenses/LICENSE` |
| [appdirs 1.4.4](https://pypi.org/project/appdirs/1.4.4/) | Transitive | MIT | `LICENSE.txt` |
| [attrs 26.1.0](https://pypi.org/project/attrs/26.1.0/) | Transitive | MIT | `licenses/LICENSE` |
| [beautifulsoup4 4.13.3](https://pypi.org/project/beautifulsoup4/4.13.3/) | Direct | MIT | `licenses/LICENSE`, `licenses/AUTHORS` |
| [certifi 2026.10.19](https://pypi.org/project/certifi/2026.10.19/) | Transitive | MPL-2.0 CA-bundle notice | `licenses/LICENSE` |
| [frozenlist 1.8.0](https://pypi.org/project/frozenlist/1.8.0/) | Transitive | Apache-2.0 | `licenses/LICENSE` |
| [fs 2.4.16](https://pypi.org/project/fs/2.4.16/) | Transitive | MIT | `LICENSE` |
| [idna 3.20](https://pypi.org/project/idna/3.20/) | Transitive | BSD-3-Clause | `licenses/LICENSE.md` |
| [life360 7.2.0](https://pypi.org/project/life360/7.2.0/) | Direct | MIT | `licenses/LICENSE` |
| [multidict 7.1.0](https://pypi.org/project/multidict/7.1.0/) | Transitive | Apache-2.0 | `licenses/LICENSE` |
| [propcache 0.5.4](https://pypi.org/project/propcache/0.5.4/) | Transitive | Apache-2.0 | `licenses/LICENSE`, `licenses/NOTICE` |
| [protobuf 7.36.0](https://pypi.org/project/protobuf/7.36.0/) | Direct | BSD-3-Clause | `LICENSE` |
| [pyelftools 0.33](https://pypi.org/project/pyelftools/0.33/) | Transitive | Public-domain/Unlicense core; MIT Construct | `licenses/LICENSE`; referenced Construct notice absent |
| [setuptools 84.0.0](https://pypi.org/project/setuptools/84.0.0/) | Transitive through fs | MIT core; additional vendor licenses | `licenses/LICENSE`, nested vendor licenses and config notices |
| [six 1.17.0](https://pypi.org/project/six/1.17.0/) | Transitive | MIT | `LICENSE` |
| [soupsieve 3.0.3](https://pypi.org/project/soupsieve/3.0.3/) | Transitive | MIT | `licenses/LICENSE.md` |
| [srp 1.0.22](https://pypi.org/project/srp/1.0.22/) | Direct | MIT from wheel; BSD classifier conflicts | `LICENSE` |
| [typing-extensions 4.16.0](https://pypi.org/project/typing-extensions/4.16.0/) | Transitive | PSF-2.0 | `licenses/LICENSE` |
| [unicorn 2.1.4](https://pypi.org/project/unicorn/2.1.4/) | Direct | BSD-declared bindings; GPLv2 native core | No standalone license/notice member; see finding |
| [urllib3 2.8.0](https://pypi.org/project/urllib3/2.8.0/) | Transitive | MIT | `licenses/LICENSE.txt` |
| [yarl 1.25.1](https://pypi.org/project/yarl/1.25.1/) | Transitive | Apache-2.0 | `licenses/LICENSE`, `licenses/NOTICE` |

Setuptools is present through a runtime dependency. Its wheel retains nested
vendor notices, including packaging's Apache/BSD alternatives and
`setuptools/config/NOTICE` plus `_validate_pyproject/NOTICE` for MPL-2.0 and
BSD-3-Clause code. Its top-level MIT metadata does not describe all nested code.

## Bundled frontend and assets

[Leaflet 1.9.4](https://github.com/Leaflet/Leaflet/blob/v1.9.4/LICENSE) is
BSD-2-Clause. The published ZIP's `frontend/LEAFLET-LICENSE.txt` is byte-identical
to `package/LICENSE` in the npm archive after verifying the archive against the
source lockfile's SHA-512 integrity. The existing build copies that complete
notice alongside the bundled JavaScript. No Leaflet notice correction is needed.

The source lockfile has 68 non-root packages: Leaflet and 67 entries marked
development-only. Direct build/test tools are esbuild 0.25.10, jsdom 26.1.0 and
Prettier 3.6.2; their declared licenses in the lockfile are MIT. They are not
bundled as frontend runtime dependencies. The complete locked development list
is recorded in the inventory as metadata, not an extracted-license audit.

The ZIP has no font files; the card uses system fonts. Leaflet's stylesheet is
bundled. The separate HomeCircle brand icon and the copied Apple trust roots
retain their own provenance/service/branding review scope. Optional OSM, USGS
and weather/radar requests are external services, not bundled source; visible
attribution does not settle service-policy acceptance.

## Confirmed fetched-wheel findings and next-candidate actions

1. **Unicorn's binding metadata does not describe its native core.** The pinned
   [Python project metadata](https://github.com/unicorn-engine/unicorn/blob/2.1.4/bindings/python/pyproject.toml)
   declares BSD, while the pinned
   [core README](https://github.com/unicorn-engine/unicorn/blob/2.1.4/README.md)
   and [COPYING](https://github.com/unicorn-engine/unicorn/blob/2.1.4/COPYING)
   specify GPLv2. The inspected Linux wheel contains `unicorn/lib/libunicorn.so.2`
   and `libunicorn.a`, with no standalone LICENSE/COPYING/NOTICE member. Its
   shared library matches CI's actual native-library SHA-256
   `ddb196ec82b52e502c18e4a34478bf7b9f61c83c2ebaa95c74d8ded45a95da9c`.
   Keep native-core licensing, source availability and distribution implications
   open; review that scope before any stable distribution. A bindings-only BSD
   label is insufficient evidence to close it.
2. **pyelftools' inspected wheel omits its referenced Construct notice.** It
   includes `elftools/construct` code. Its main license refers to Construct's
   license, which is absent from the wheel. The pinned upstream
   [v0.33 Construct license](https://github.com/eliben/pyelftools/blob/v0.33/elftools/construct/LICENSE)
   is MIT with Tomer Filiba/Corbin Simpson attribution. Retain that complete
   notice with a future candidate's third-party materials and seek a corrected
   upstream distribution; verify the eventual installed artifact and notice
   paths together.

These are findings in fetched dependency artifacts. They are not missing
Unicorn/Construct files inside HomeCircle's ZIP, which carries neither
dependency. No new bundled-source notice omission was confirmed by this scoped
dependency check. The package's existing FindMy/OpenTagViewer and emulator
notices still require the separate source-provenance review.

Any notice addition or dependency change needs a new reviewed candidate,
archive checks and appropriate Linux validation. The published beta20 tag,
ZIP, source and dependencies were not changed by this review. Python execution
on the Mac, owner-account requests and production/V2 changes were not used.
