# Real desktop-browser picture acceptance

Completed October 20, 2026, 20:15–20:21 UTC. The scoped desktop check passed for
real decoding/canvas, filename continuity, local upload failure/success, removal,
Back, close and native chooser cancellation. Completing a selection through the
native chooser remains unqualified; same-file decoding was exercised through a
transparent browser fixture injection.

## Exact scope

- Real Safari **27.2**, reported WebKit **605.1.15**. The user agent masks its
  platform/OS; it is not evidence of host architecture or the literal OS version.
- Unmodified isolated candidate `settings-dialog.js` SHA-256
  `cef3006b0e1b9e10a24b58631bdeddd26061176588cc37f7e33266e8f4cfffe5` and
  `picture-crop.js` SHA-256
  `399e08582d93722b3dae2df79327ffb00a74eda3dc26c826b133c31580679438`.
  Both hashes matched again after acceptance.
- Owned Node server bound only to **127.0.0.1:65276**, process 78674. A new owned
  Safari tab opened the synthetic test page. Its CSP allowed page resources and
  connections only from that loopback origin, plus local data/blob images.
- Generated 400×200 blue/orange PNG, SHA-256
  `0fca8defa31d84dfcd9320b6e53e9c0079f24b51cfbb630810758ef44a3f1584`.
  No household photograph, provider credential or real location was used.
- The source dialog/crop implementation ran in the browser. The harness supplied
  account-free settings flow responses and controlled loopback upload responses;
  it started no Home Assistant, native provider, emulator or account session.

## Observed acceptance

The 13 ordered browser receipts are retained in `server-receipt.json`, and
`verify.rb` checked their relationships into `acceptance.json`.

| Check | Real browser result |
| --- | --- |
| Decode and initial crop | PNG decoded through the actual `FileReader`/`Image` path; visible canvas, filename and zoom 1; canvas JPEG data URL length 11,939 |
| Zoom | Native slider/keyboard changed zoom to 4.25; canvas output changed to 11,579 characters; filename stayed visible |
| Reset crop | Reset returned zoom to 1 with the filename retained |
| Failed upload | Local HTTP 503 left filename and crop visible; product displayed “Could not upload this picture. Your crop is kept; try saving again.” |
| Same-file reload | Browser File/DataTransfer supplied the identical fixture filename again; actual image decode reloaded and zoom reset from 4.25 to 1; native file input was empty after decode |
| Successful save | Local HTTP 200 produced the synthetic HA image reference; crop/filename cleared; settings submitted only that image reference |
| Remove | A new pending crop's filename and canvas cleared immediately; the saved removal submitted an empty picture reference |
| Back | Receipt before Back had the active filename/crop; the next picture step had both cleared |
| Close | Receipts before close had the filename/crop; closed-dialog receipts had no filename or crop |
| Native chooser cancellation | Real Choose picture opened Safari's native file chooser; canceling it with an existing active crop preserved the filename and canvas |

Both upload attempts contained actual canvas-generated JPEG bytes, the expected
`homecircle-picture.jpg` filename and `image/jpeg` file type. Each browser file
was 13,434 bytes; each multipart request was 13,630 bytes. The server independently
recorded JPEG magic bytes and the multipart filename. No image decoder, canvas,
FileReader or image constructor was mocked.

Screenshots retained and visually checked:

- `crop-filename.png`: visible selected filename and actual crop.
- `reset-filename.png`: retained filename after reset.
- `failed-upload-filename.png`: retained filename/crop and the failed-upload
  explanation in the same dialog.
- `closed-state.png`: cleared dialog state and synthetic browser observations.

These screenshots contain only the local fictional test page, not an actual HA
household or other application content.

## Native-picker and harness limits

The in-app browser was unavailable, so the check used Safari through documented
native CUA controls. Safari's real chooser opened, navigated to the owned PNG,
showed its 400×200 preview and selected icon. Its Upload control remained disabled
through the available accessibility actions; Return, the exposed Open action and
double-click did not complete selection. The bounded attempts were canceled.
No cause or product defect is inferred from that UI limitation.

The test then used its visibly labelled **Load synthetic picture** fixture
control, which assigns a real browser `File` via `DataTransfer` and dispatches
the change event into the unchanged source. This qualifies actual browser
decoding, drawing and reloading, but **does not prove native chooser completion
or native same-file event suppression behavior**. The receipt field named
`nativeChanges` is a legacy harness label for observed DOM file-change events;
those successful load events were fixture-driven, not accepted native selections.

The harness's observation panel initially used `requestAnimationFrame`, which
was paused while Safari was in the background. The harness alone switched to a
microtask and the page was reloaded before the recorded cases. No product source
changed. Local test controls were inserted into the dialog solely to operate
the fixture while the modal made its background inert.

This adds one real desktop Safari scope. It does not establish native-picker
completion, mobile browsers, screen-reader acceptance, actual HA flow/storage,
HACS upgrade, a physical wall display or real account/provider behavior.

## Cleanup and preservation

The owned test tab was closed; the existing browser tabs were preserved. The
owned server received SIGTERM at **20:21:02 UTC**, exited zero, and its post-stop
listener inventory was empty. `listener-before-cleanup.txt` records the
loopback-only listener; `listener-after-cleanup.txt` is empty.

Only files under `work/release-1.0/picture-browser/` were written for this task.
The product source stayed frozen. `acceptance.json` records hashes for the
harness, fixture, receipts and screenshots. No package, source commit, release
asset or installed integration was changed.

## Independent native-picker A/B

A separate bounded Safari check compared a plain visible native image-file input
with the hidden-input plus visible-button pattern, using the same valid 400×200
PNG. Both opened the chooser and displayed the selected image, but retained a
disabled Upload control and did not complete one Return attempt. Cancel returned
zero files and no change event in both cases. The [A/B receipt](PICTURE-PICKER-AB.json)
records the exact cases and owned-tab/server cleanup. This gives no evidence of
a hidden-input regression; the shared environment/automation cause remains
unproven, and native selection completion remains unqualified.
