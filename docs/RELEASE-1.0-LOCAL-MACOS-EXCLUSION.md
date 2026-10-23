# Exclusion of the unused local macOS decryptor and CLI

The first-release target is official HAOS, with the existing direct Apple Find My
CloudKit connection. The candidate removes these two legacy vendor files:

- custom_components/homecircle/_vendor_findmy/plist.py
- custom_components/homecircle/_vendor_findmy/__main__.py

The first reads local macOS Find My .record files and asks the macOS security
command for the BeaconStore key. Its header credits OpenTagViewer and an earlier
gist without an observed explicit license. The second is the sole importing
consumer and implements python -m findmy decrypt. Neither was used or exported
by the HomeCircle HAOS setup/recovery/discovery/report path.

Independent static reviews found exactly one incoming import to plist.py
(from __main__.py), none to __main__, and no dynamic loader targeting either.
The SDK's package exports, icloud.AsyncFindMyClient, crypto/recovery and report
modules remain unchanged. Remaining stdlib plistlib HTTP parsing is unrelated
and its tests remain in place.

## Candidate safeguards and checks

The current source omits both files. The integration-only release builder also
explicitly rejects both paths, so an old copied file cannot silently re-enter
the new ZIP. The existing release regression now checks absent source/package
paths, contaminated-input exclusion, rejection of injected archive members and
unchanged complete inherited notices. The existing SDK/log-isolation regression
also uses a fresh interpreter with an import finder that refuses either retired
module, then loads the supported SDK without making provider requests.
These revise existing cases rather than dropping tests or adding a broad matrix.

The candidate layout is 111 members: 109 literal source members and two generated
frontend assets. Its version and exact final source/ZIP/inventory are recorded
by the candidate freeze/qualification receipts. Before those checks run, the
source exclusion and static/import review are preparation evidence only; they
are not a completed native or HACS installation result.

All 72 retained primary Find My/recovery Python files match their pre-exclusion
c31c220 source bytes. The earlier Claude AI review and its limits therefore remain
applicable to the retained reviewed paths; no new recovery/crypto implementation
is introduced by this exclusion. The vendor README and package metadata are
separate explanatory/version changes.

## Rights and historical scope

This removes the specifically identified local utility from the new current
source and candidate ZIP; no retained expression from that identified file ships
in the new package. The earlier Git history, published beta archives and dated
113-member evidence stay unchanged and remain historical. This does not assert
that the whole source history has been legally cleared or that provider/software
permissions are granted. All inherited notices, including OpenTagViewer's, remain
retained. The separate Apple/Life360/Unicorn and other recorded distribution
questions keep their actual dispositions.
