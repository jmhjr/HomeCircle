# Beta 20 vendored-source and inherited-notice review

Reviewed October 20, 2026 against source tag `d02a9bdb9027cb51c99165a09ba50d5b175f5fb9`
and the published 112-file `homecircle.zip`, SHA-256
`fc0b365d9688459504f874af5c38393e24145d657f15f1def8ada9184f363285`
(604,937 bytes). The 71 `_vendor_findmy/` and `_findmy_runtime/` archive members
match the pinned source bytes. This review made no package, account, provider,
production, tag or release-asset changes and ran no Mac Python.

One additional inherited-notice omission is confirmed: retained GrandSlam
documentation and implementation text has no accompanying GrandSlam notice in
beta 20. The FindMy, emulator and previously restored OpenTagViewer notices are
present. The gist ancestry and the unfilled GrandSlam copyright fields remain
permission/provenance decisions; this is a technical inventory, not a legal
clearance, infringement determination or external cryptographic audit.

## Direct vendored origins

| Retained material | Pinned primary source | What was checked | Notice result in beta 20 |
| --- | --- | --- | --- |
| FindMy SDK | [parawanderer/FindMy.py `7969003ca785658369b650f75d9e7ca519566bf6`](https://github.com/parawanderer/FindMy.py/tree/7969003ca785658369b650f75d9e7ca519566bf6) | All 53 corresponding SDK files/data: 24 byte-identical, 9 identical after private import-namespace rebasing, 20 adapted. Six additional package files comprise the local README/LICENSE and four local Python adapters/policy modules. | Complete [MIT notice](https://github.com/parawanderer/FindMy.py/blob/7969003ca785658369b650f75d9e7ca519566bf6/LICENSE.md), naming 2023 FindMy.py Contributors, retained exactly in `_vendor_findmy/LICENSE.md`. |
| Mach-O/ADI emulator | [sacca97/os-findmy-e `2096d875dac6b5ed2347a9ae8c39c7251c0d6ed6`, `tools/machoadi`](https://github.com/sacca97/os-findmy-e/tree/2096d875dac6b5ed2347a9ae8c39c7251c0d6ed6/tools/machoadi) | `macho.py` is byte-identical; `adi_run.py`, `harness.py` and `stubs.py` retain adaptations. The package initializer is local. | `emulator/LICENSE` is byte-identical to the [upstream MIT license](https://github.com/sacca97/os-findmy-e/blob/2096d875dac6b5ed2347a9ae8c39c7251c0d6ed6/LICENSE), naming 2026 sacca. |
| `plist.py` | FindMy file above, explicitly derived from [OpenTagViewer `08a59cab551721afb9dc9f829ad31dae8d5bd400`, `python/airtag_decryptor.py`](https://github.com/parawanderer/OpenTagViewer/blob/08a59cab551721afb9dc9f829ad31dae8d5bd400/python/airtag_decryptor.py) | HomeCircle file is byte-identical to the pinned FindMy file. Its author/origin header survives; the Python decryption/file helpers derive from OpenTagViewer. | Complete [OpenTagViewer MIT notice](https://github.com/parawanderer/OpenTagViewer/blob/08a59cab551721afb9dc9f829ad31dae8d5bd400/LICENSE.TXT), naming 2025 Shane B., retained exactly in the combined SDK license. |

Upstream raw files were checked against 59 pinned Git-tree blob hashes, including
the 55 FindMy blobs downloaded for comparison (the two upstream generated `.pyi`
files are not retained) and four emulator files. An adaptation is not represented
as upstream-identical or as an independent implementation.

## Confirmed GrandSlam notice omission

The pinned FindMy [credits](https://github.com/parawanderer/FindMy.py/blob/7969003ca785658369b650f75d9e7ca519566bf6/README.md#-credits)
identify GrandSlam. The public fork metadata identifies `JJTech0130/grandslam` as
the parent of `nythepegasus/grandslam`; the inspected 26-commit history includes
that parent lineage. The comparison uses [nythepegasus/grandslam revision
`e2321633f493f6c1d9146e8d85ad6d57ba490708`](https://github.com/nythepegasus/grandslam/tree/e2321633f493f6c1d9146e8d85ad6d57ba490708),
not a floating branch or an unrelated current Pypush license.

Two retained passages establish more than a shared endpoint or protocol-field
name. Ignoring indentation and blank lines, 13 consecutive lines of its
`gsa.py` client-format docstring (lines 200–212) match beta 20
`reports/anisette.py` lines 390–402. Nine consecutive implementation/comment
lines in `gsa.py` lines 325–334 match beta 20 `util/crypto.py` lines 33–42.
The latter HomeCircle file is itself identical to the pinned FindMy file.
The five matching request-envelope lines in `reports/account.py` are also
recorded but are not the basis for treating all protocol constants as copied
protected expression. [Pinned GrandSlam implementation](https://github.com/nythepegasus/grandslam/blob/e2321633f493f6c1d9146e8d85ad6d57ba490708/src/grandslam/gsa.py).

GrandSlam's [LICENSE](https://github.com/nythepegasus/grandslam/blob/e2321633f493f6c1d9146e8d85ad6d57ba490708/LICENSE)
contains the MIT permission terms and literal unfilled year/name fields. Beta
20's combined SDK license does not contain that source notice. Preserve its
exact text and pinned source in the next candidate; do not fill in a presumed
author/year or describe that retention as resolving ownership or permission.
The prepared append-only addition is `GRANDSLAM-NOTICE-ADDITION.md`; its notice
body is byte-identical to the downloaded upstream license. Any maintainer or
appropriate legal assessment of the unfilled fields remains a stable-release
gate. The published beta 20 ZIP must remain unchanged and its omission must be
described accurately until a later candidate is published.

## Gist ancestry: pinned, still unresolved

OpenTagViewer's header identifies the [airy10 gist](https://gist.github.com/airy10/5205dc851fbd0715fcd7a5cdde25e7c8/87ed8dcc14a31f1748cce3214d5793583e007d24).
The inspected revision is `87ed8dcc14a31f1748cce3214d5793583e007d24` (February
11, 2024), file blob `94d3ed26c2b957e18c2b473cfdc72137c283616c`. Its header
credits Matus and links the [YeapGuy predecessor](https://gist.github.com/YeapGuy/f473de53c2a4e8978bc63217359ca1e4/d573499d344732df0bff5ffb985cfd7093a94410),
inspected at revision `d573499d344732df0bff5ffb985cfd7093a94410` (January 29,
2024), file blob `44032b3c2f7aeeb14ffbf867216b00a8336f178d`.

Each inspected gist has one Swift source file; no explicit license or permission
notice was found in either file or the enumerated gist files. The Swift scripts
and Python descendants share the ordered encrypted-plist fields, AES-GCM flow,
BeaconStore key source and local record layout. The descendant Python program
is not a byte-identical Swift copy, and these protocol/format similarities alone
do not determine what protected expression remains or establish infringement.
The known author/origin links must survive. A permission or independently
documented implementation basis for any retained expression is still required;
the OpenTagViewer notice alone does not answer the earlier chain. No upstream
author was contacted and no permission was invented.

## SRP, downloaded binaries and protocol references

The local `util/srp.py` executes the installed `srp._pysrp` module under two
private namespaces. It does not vendor SRP equations; `srp==1.0.22` remains a
separately resolved runtime dependency, whose [official package
metadata](https://pypi.org/pypi/srp/1.0.22/json) identifies MIT and the
[cocagne/pysrp project](https://github.com/cocagne/pysrp). This does not eliminate
the inherited GrandSlam expression described above.

The inspected ZIP includes no `.so`, `.dylib`, `.dll`, wheel, DMG or nested
archive. Unicorn and Apple's CoreADI acquisition are separate runtime paths;
FindMy/emulator MIT notices do not license those binaries. The existing runtime
provenance correctly distinguishes the source emulator from Apple's library.
No Apple installer/library was downloaded for this review. Service authorization
and applicable installer/library terms remain separate from source-code
licensing and from successful technical execution.

The SDK also references OpenTagViewer, SideSign, InflatableDonkey and rustpush
for protocol facts. A link does not itself establish copied code or grant
distribution rights. This focused review does not replace the direct/transitive
dependency inventory or a complete source-history clearance of every credited
upstream research project.

## Confirmed provenance-document correction

`tests/fixtures/findmy_0102_gsa_reference.provenance.md` still says the FindMy
0.10.2 wheel license is byte-for-byte equal to the current combined SDK license;
its reproduction snippet asserts equality. The verified [published wheel](https://files.pythonhosted.org/packages/77/04/01dafe63681eb275918d7d9f9a7559160e05193d799e9731380aab3bde2a/findmy-0.10.2-py3-none-any.whl)
is still 54,993 bytes with SHA-256
`2b367c0d59db66905e7e93ba828144ce473499aba5bfa17e89844a3169ffdde6`.
Its license is the original 1,079-byte FindMy notice. Beta 20's SDK license also
contains the restored OpenTagViewer notice, so equality is false. Correct the
claim to exact retention of the original wheel notice within the combined
license, and change the reproduction assertion to `wheel_notice in
combined_license` while retaining the exact wheel-notice digest. Fixture bytes,
method parity and runtime behavior need no change.

## Evidence hashes

Fetched primary metadata and source on October 20, 2026. Receipts retain exact
URLs, byte counts, download timestamps and per-file hashes under
`vendor-evidence/`; no downloaded upstream program was executed.

| Evidence | SHA-256 |
| --- | --- |
| FindMy upstream license, also the wheel license | `51396fd82204e1d844bbff2019054d8c3712e53c3ed8485c9f19dd73990eb46e` |
| OpenTagViewer license | `e5d3404f06c194c08bfd18bfe4d42ece466f28098177b38c14aeb2bfe6b39597` |
| Emulator license | `d13de33ca644eb1350ca7ab815075d2499621f24dad01ee9be532360934483d6` |
| Beta 20 combined SDK license | `8f4ac3cf0c33477597d96c2f5025a5610272c2e0caf13b3973c4755af9a336de` |
| GrandSlam license | `002c2696d92b5c8cf956c11072baa58eaf9f6ade995c031ea635c6a1ee342ad1` |
| GrandSlam `gsa.py` | `d250c6a50b3182f4e96a1d52cd3aad3b2bac50c54f59db41c00c1d70495999c4` |
| OpenTagViewer Python decryptor | `d478fa7accd242c837f7c3f72028716b59b304a418057161a2f2ff5776222b00` |
| Retained `plist.py` | `5ef5c26787b342d46ad7b33800d7386ac02efd2910c49d705eade2328f47fe4e` |
| airy10 Swift file | `e84c94e2cdb8cb6753928c658dbf0a95bc23432b84c14613b74c1a093771efb9` |
| YeapGuy Swift file | `1c6c95a8a2d716ac4c5fca3edbbbb5979c2684d08c1d07428f01520d94ea7ec5` |
| Prepared GrandSlam notice addition | `0f425fcc2babce30b57ab5c499d5b662c6725fa7362ae89798d41049143f6213` |

Machine-readable receipts: `comparison.json`, `grandslam-line-comparison.json`,
`archive-notice-receipt.json`, `wheel-license-receipt.json`,
`fetch-receipt.json`, `source-fetch-receipt.json`,
`grandslam-source-receipt.json` and `chain-fetch-receipt.json`.
