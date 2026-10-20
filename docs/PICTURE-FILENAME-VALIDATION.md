# Picture filename continuity correction

Prepared October 20, 2026 against the isolated exact
`9466eef45ecac16f05f25d4455d705383f7c91ff` source inventory (328 files).
Only `frontend/homecircle-card/src/settings-dialog.js` and its existing
`test/lifecycle.test.mjs` source changed; `scope.json` records before/after hashes.
Versions, lockfile and every other baseline source file are unchanged.

The native file input continues resetting after decode so the same file can be
selected again. A visible Choose picture button opens that input, while a
separate filename line follows the active crop. The filename remains visible
through zoom/reset and unsuccessful uploads, and is cleared on successful
upload, removal, navigation away, dialog close or failed decoding. Names use
`textContent` and wrap long unbroken filenames. The chooser is disabled during
decode/upload, alongside the native input. Leaving a picture step now clears
its crop immediately rather than retaining a close-event listener for every old
picture step.

The strengthened existing regression failed against the unchanged implementation
because the filename was absent (`regression-before.txt`), then passed after the
correction (`regression-after.txt`). It exercises:

- local decoding without network upload;
- filename after choosing, zooming, resetting and choosing the same file again;
- visible chooser activation and cancellation retaining the current crop name;
- malformed image decode clearing the name;
- successful upload and removal clearing the name while submitting only an HA
  image reference;
- failed upload retaining both crop and filename;
- Back during an outstanding upload clearing the abandoned name and preventing
  submission to a different step;
- closing a dialog clearing the current name.

Native Node 23.7.0/npm 11.1.0 on the Mac installed the unchanged lockfile with
`npm ci --no-audit --no-fund`. The build passed. The focused regression passed
(one test), and adjacent picture-crop plus Find My settings checks passed (six
tests). Both changed files passed Prettier. The complete frontend suite also passed: 110 tests, zero failures.
Focused before/after and full-suite logs are retained in the ignored local
validation workspace. Native Linux exact-source validation is still pending.

The chooser/file/image/canvas boundaries use the existing JSDOM harness. Its file
selection helper models the browser's same-file suppression unless the input
value was cleared. This is automated regression evidence, not real-browser,
screen-reader or physical-display acceptance. Those remain in the release plan.

The build generated `custom_components/homecircle/frontend/homecircle-card.js`
and `LEAFLET-LICENSE.txt` under this isolated candidate, and npm created its
local `node_modules`; none is an edit to a baseline source file. The parent can
rebuild deterministically and select only the reviewed source changes for the
canonical branch. The selected source changes are being consolidated onto the 1.0 development
branch. No published release asset or tag was changed.
