# Retained earlier qualification attempts and diagnosis

This record preserves two failed full-suite attempts, one failed diagnostic attempt and one completed diagnostic. **Neither failed full run is accepted. The successful diagnostic is not release qualification.** The later accepted full run40010260549 has its separate [permanent record](https://github.com/jmhjr/HomeCircle/blob/32bea5d87f2baadb2e8763541fa916dcc1336da8/native-rc-current-evidence/INDEX.md).

All four attempts concern HomeCircle1.0.0-rc.1 on current Core2026.10.2/native Linux amd64. Their original source, QA head, event, attempt, workflow and artifact identities are retained rather than rewritten to the final source. They used the same112-member product package SHA4f94a18e2f7862e9bd7f4c85250e5f10e4b8e1292ea9d7b263b441d2e1b77dd9 and inventory SHAe4bc34e3921e75157402cf643f87ed658d95c76505a448abb393fd90a304db12.

## Exact attempts

| Attempt | Original source | Actual outcome | Original safe artifact |
| --- | --- | --- | --- |
| [Full R1:40002507530](https://github.com/jmhjr/HomeCircle/actions/runs/40002507530) | c7b31c5a82431a6b16d8b7208f9423626b95bd4b | Failed; strict private collection identity refusal, plus one city-test failure in unaccepted JUnit diagnostics |12523191531,7051 bytes,7 JSON members |
| [Full R2:40004476753](https://github.com/jmhjr/HomeCircle/actions/runs/40004476753) |1825410fe61ea29fdd5611bcadb6cb9b043f3fda | Failed; the same strict identity refusal and one city-test failure |12523193783,7051 bytes,7 JSON members |
| [Diagnostic R1:40007477641](https://github.com/jmhjr/HomeCircle/actions/runs/40007477641) |1825410fe61ea29fdd5611bcadb6cb9b043f3fda | Failed during offline diagnostic; only host receipt survived, so exact child failure trace is unavailable |12524752590,649 bytes,1 JSON member |
| [Diagnostic R2:40008762105](https://github.com/jmhjr/HomeCircle/actions/runs/40008762105) |1825410fe61ea29fdd5611bcadb6cb9b043f3fda | Diagnostic completed; collected all modules and executed only the city test, which failed with a bounded InvalidSpecError observation |12525063913,1749 bytes,2 JSON members |

Original artifact ZIP SHA256 values:

- `full-r1/artifact.zip`:9c27fdfeebc7879e5241b9d3b9d9d151070986916eb010879634b8de5aa3d3e8.
- `full-r2/artifact.zip`:37107bc9777ebb525d545b18c46701e61fb85cecf26b16cb509e8160c40ed5f9.
- `diagnostic-r1/artifact.zip`:c328ed9031c548ee27e4852a5209b89851121893216865ffdce3912eec18b8be.
- `diagnostic-r2/artifact.zip`:c4e1323fe96fda5fbff874bc532b128aad4c6f4e8700e37692241ffca635d397.

Both failed full runs retained an unaccepted diagnostic aggregate of1778 passing records,1 failing record and1 optional skip across1780 records. Their bounded public failure label names only `tests.test_city_lookup::test_unload_cancels_city_lookup_and_remove_deletes_cache`. These aggregate observations do not substitute for strict full collection/JUnit acceptance. The parser refused before any successful full acceptance, and no candidate artifact from those failed attempts is claimed here. All four host receipts observed offline execution and successful owned container/private-workspace cleanup; that observation does not change a run's failure or diagnostic-only status.

## What the diagnosis established and what changed

The successful bounded diagnostic collected1780 cases and all912 declared base functions, with no duplicate or invalid identities. The maximum full private name was2,097,225 characters, in `tests.test_findmy_report_service::test_report_response_framing_limits`. Its existing parameter exceeds the harness's interim2MiB per-name ceiling; other existing escaped-byte parameters already exceeded the first128KiB ceiling. Only public source-bound function labels and lengths were exported, never parameter strings.

The final producer removed the redundant per-name ceiling. Both complete private collection and JUnit inputs retain16MiB serialized-file bounds, the5000-case limit, full unmodified class/name comparison, unique identities, zero deselection, complete912-base coverage and exact collection/JUnit set and count equality. It did not accept an earlier aggregate, shorten or hash away identity differences, or weaken the zero-failure/one-named-skip success condition.

The bounded target diagnostic selected exactly1 city test after collecting all modules, with1779 deselected cases. It observed InvalidSpecError at original source182's `tests/test_city_lookup.py:252`, the autospec patch. Final sourceb906d3ee51711d3455a497cc265fd3bc18f3adec replaces that test fixture with an awaited direct recorder of each actual Store.key and asserts both the exact five keys and their count. This avoids autospec of the already fixture-mocked Home Assistant method. The final source differs fromC7 in only this test file; all401 other public source blobs and every integration/frontend/product package byte remain identical. The actual [TEST-ONLY-SOURCE-DELTA-r3.json](TEST-ONLY-SOURCE-DELTA-r3.json) is retained without modification. These are test/qualification-harness corrections, without a product behavior or candidate ZIP change.

Diagnostic R1 unnecessarily disabled pytest's terminal plugin and lost child telemetry on failure. The exact pinned pytest-homeassistant-custom-component0.13.373 public wheel has an unconditional `config.getoption("verbose")` read atplugins.py182, an option supplied by that terminal plugin. [DIAGNOSTIC-PLUGIN-OPTION-REVIEW.json](DIAGNOSTIC-PLUGIN-OPTION-REVIEW.json) retains the source and PyPI digest facts. This is the concrete source basis for restoring ordinary collect-only behavior; the original native child trace was not recovered, so the history does not claim that trace proved the cause. Diagnostic R2 restored the normal terminal plugin with private logs and added bounded child-finally progress and parent failure-summary retention. Its full-suite/frontend/release qualification flags stayed false.

The later final full run is accepted only in its separate record:1779 backend passes, one named optional public Apple-DMG fixture skip,126 frontend passes, complete912-base/private-identity agreement,54 required regressions,14 cause-verified old-vault red cases,402-file privacy and mandatory cleanup. That later result does not retroactively accept these earlier attempts or turn the successful diagnostic into qualification.

## Exactly20 retained files and verification scope

The20 files are this index; the four original artifact ZIPs plus their original root metadata and download verification records (12); the four actual pre-run root anchor files; the exact final test-only source-delta proof and pinned-plugin review (2); and a19-file SHA/size manifest. JSON receipts stay as their exact original bytes inside the original ZIPs; no extracted duplicates, replacement artifacts, private logs or new replay framework are included.

Before copying, each artifact's SHA matched both its saved GitHub artifact digest and separate root metadata; the successful/failure run, event, head, workflow, attempt and source matched the corresponding pre-run anchor and download record. Every member was an expected flat regular unencrypted JSON file, bounded and duplicate-free, and matched its locally extracted receipt bytes. Full artifacts contain only `failure-summary.json`, `frontend-summary.json`, `host.json`, `package-summary.json`, `privacy-summary.json`, `setup-summary.json`, and `source-summary.json`; Diagnostic R1 contains only `host.json`; Diagnostic R2 contains only `diagnostic.json` and `host.json`. Fixed failure classes/codes and bounded public function/line labels are retained without messages, raw tracebacks, locations, credentials, tokens or private parameter IDs.

The manifest verifies exact retained membership and bytes. Transport statements describe saved GitHub metadata and verified digests; this packaging made no fresh network requests and does not independently cryptographically authenticate GitHub. No tests, native execution, provider/account calls, Git mutation, polling or publication occurred while preparing this history. It does not establish HACS delivery, owner acceptance, another platform, restore/upgrade behavior, live-provider correctness or stable-release approval.
