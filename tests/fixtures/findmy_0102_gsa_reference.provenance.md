# Published GSA composer fixture provenance

Verified on October 19, 2026. The fixture itself was left unchanged.

- Source: [FindMy 0.10.2 PyPI metadata](https://pypi.org/pypi/findmy/0.10.2/json).
- Artifact: [findmy-0.10.2-py3-none-any.whl](https://files.pythonhosted.org/packages/77/04/01dafe63681eb275918d7d9f9a7559160e05193d799e9731380aab3bde2a/findmy-0.10.2-py3-none-any.whl), 54,993 bytes.
- Downloaded wheel SHA256, equal to the PyPI metadata digest:
  `2b367c0d59db66905e7e93ba828144ce473499aba5bfa17e89844a3169ffdde6`.
- Fixture: `findmy_0102_gsa_reference.py`, 3,297 bytes, SHA256
  `059fb9d6f6b9dfcc813961db6435e3bf71b21e782bdf47dacf2be8def94b4705`.

The complete method ASTs, including signatures, docstrings, and bodies, match
the verified wheel after excluding source-location attributes:

| Wheel member | Upstream method | Fixture method |
| --- | --- | --- |
| `findmy/reports/anisette.py` | `BaseAnisetteProvider.get_headers` | `PublishedProvider.get_headers` |
| `findmy/reports/anisette.py` | `BaseAnisetteProvider.get_cpd` | `PublishedProvider.get_cpd` |
| `findmy/reports/account.py` | `AsyncAppleAccount._gsa_request` | `PublishedAccount._gsa_request` |

The wheel's `findmy-0.10.2.dist-info/licenses/LICENSE.md` is byte-for-byte equal
to `custom_components/homecircle/_vendor_findmy/LICENSE.md` (SHA256
`51396fd82204e1d844bbff2019054d8c3712e53c3ed8485c9f19dd73990eb46e`).

The fixture bytes are also identical in its original commit `dc6c713`, the
published `v0.1.0-beta.19` source tag, and pre-fix HEAD `373203a`. The previously
asserted digest `336ae221bfa1e8a8630bfe398e64a8bf0205eb3f6aacff3605f708e0b39ba0fe`
did not identify that committed fixture. Its origin was not established.
Correcting the expected digest allows both existing synthetic init/complete
request-byte parity cases to execute; no runtime code or fixture was changed.

To reproduce the provenance comparison from the repository root with Python's
standard library (downloads public package files; does not install or execute
the wheel, construct a provider, or contact Apple):

```python
import ast
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile

metadata = json.load(urllib.request.urlopen("https://pypi.org/pypi/findmy/0.10.2/json"))
record = next(x for x in metadata["urls"] if x["filename"] == "findmy-0.10.2-py3-none-any.whl")
wheel = urllib.request.urlopen(record["url"]).read()
assert hashlib.sha256(wheel).hexdigest() == record["digests"]["sha256"] == (
    "2b367c0d59db66905e7e93ba828144ce473499aba5bfa17e89844a3169ffdde6"
)
fixture = Path("tests/fixtures/findmy_0102_gsa_reference.py").read_bytes()
assert hashlib.sha256(fixture).hexdigest() == (
    "059fb9d6f6b9dfcc813961db6435e3bf71b21e782bdf47dacf2be8def94b4705"
)

def method(tree, owner, name):
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == owner)
    node = next(n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name == name)
    return ast.dump(node, include_attributes=False)

with zipfile.ZipFile(io.BytesIO(wheel)) as archive:
    for member, owner, name, fixture_owner in (
        ("findmy/reports/anisette.py", "BaseAnisetteProvider", "get_headers", "PublishedProvider"),
        ("findmy/reports/anisette.py", "BaseAnisetteProvider", "get_cpd", "PublishedProvider"),
        ("findmy/reports/account.py", "AsyncAppleAccount", "_gsa_request", "PublishedAccount"),
    ):
        assert method(ast.parse(archive.read(member)), owner, name) == method(
            ast.parse(fixture), fixture_owner, name
        ), name
    assert archive.read("findmy-0.10.2.dist-info/licenses/LICENSE.md") == Path(
        "custom_components/homecircle/_vendor_findmy/LICENSE.md"
    ).read_bytes()
```

This verifies the fixture's derivation and the scope of its parity tests. It
does not establish Apple's acceptance, native-runtime compatibility, or a formal
security assessment.
