"""Finite HTTP responses accept both plist encodings without altering XML fragments."""

import plistlib
from xml.parsers.expat import ExpatError

import pytest

from custom_components.homecircle._vendor_findmy.util.http import HttpResponse


@pytest.mark.parametrize("encoding", [plistlib.FMT_XML, plistlib.FMT_BINARY])
@pytest.mark.parametrize(
    "payload",
    [
        {"Response": {"Status": {"ec": 0, "hsc": 200}, "spim": "c3BpbQ=="}},
        {
            "Response": {
                "Status": {"ec": 0},
                "ptm": "cHRt",
                "tk": "dGs=",
                "X-Apple-I-MD-RINFO": "17106176",
            }
        },
        {"success": True, "errorCode": 0, "records": [{"metadata": b"synthetic"}]},
    ],
)
def test_http_plist_decodes_provisioning_and_escrow_shapes(encoding, payload):
    encoded = plistlib.dumps(payload, fmt=encoding)
    assert HttpResponse(200, encoded).plist() == payload


def test_http_plist_keeps_legacy_xml_fragment_support():
    payload = {"Response": {"Status": {"ec": 0, "hsc": 200}}}
    encoded = plistlib.dumps(payload)
    fragment = b"<plist" + encoded.split(b"<plist", 1)[1]
    assert not fragment.startswith(b"<?xml")
    assert HttpResponse(200, fragment).plist() == payload


@pytest.mark.parametrize("encoded", [b"bplist00", b"bplist00invalid"])
def test_http_plist_refuses_malformed_binary(encoded):
    with pytest.raises(plistlib.InvalidFileException):
        HttpResponse(200, encoded).plist()


@pytest.mark.parametrize("encoded", [b"<plist><dict>", b"<?xml invalid"])
def test_http_plist_refuses_malformed_xml(encoded):
    with pytest.raises(ExpatError):
        HttpResponse(200, encoded).plist()
