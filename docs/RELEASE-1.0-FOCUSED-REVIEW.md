# Independent review of the 1.0 preparation fixes

Reviewed October 20, 2026, read-only against `work/release-1.0/product-candidate/`.
Comparison baseline: notice-correction commit
`9466eef45ecac16f05f25d4455d705383f7c91ff`. The inspected application baseline
files match the beta20 application source; the notice correction is separate.
No product file was edited by this reviewer.

## Disposition

No remaining blocking issue was found in the reviewed passive-zone, city-close,
picture-filename or privacy-guard changes. They are bounded fixes for confirmed
behavior. This is source review with the limited independent checks below, not
final release acceptance or proof of an actual Home Assistant shutdown cause.

## Passive-zone membership

The normalization change only excludes passive zones from the legacy geometric
fallback used when a Person reports `not_home` without explicit membership. It
does not change the earlier precedence of explicit `in_zones`, explicit `home`,
or unique named-place matching. The selected source, selected tracker set,
Person/source coordinate equality, report-age envelope, valid accuracy and
entire-accuracy-circle-inside-zone checks remain unchanged. Missing, unavailable
or invalid zones still fail the existing coordinate/radius checks before the new
attribute access.

The added behavioral regression distinguishes passive and active versions of the
same synthetic residence, and preserves explicit Person membership in a passive
residence. This distinction agrees with pinned Core behavior: Home Assistant
includes passive zones in its complete membership list but excludes them from
active-zone selection; Person copies the selected source's membership list.
Consequently, this fix must not be described as making passive zones impossible
to count as an explicitly selected residence. See the pinned
[Core zone implementation](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/components/zone/__init__.py#L155-L159)
and [Person source selection](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/components/person/__init__.py#L618-L628).

The existing tests for stale/inaccurate GPS, tracker-only members, source
association, source switching and explicit report evidence remain applicable.
Their real-HA rerun belongs to the separate frozen-source Linux validation.

## City lookup close and cancellation

The original close path could propagate an independently cancelled disk-save
child as cancellation of integration unload. The new close path shields and
drains the update task and save task separately. A cancelled child whose caller
has no cancellation request is consumed as completed child cleanup. When the
close caller is cancelled, its cancellation is retained and re-raised after both
owned drains finish; repeated caller cancellation does not cancel the underlying
write or escape the drain.

Ordinary save exceptions keep the original cleanup disposition: they are
retrieved and suppressed by close. The patch does not introduce a new policy for
propagating disk errors. Unexpected noncancellation failures from the update task
retain their earlier behavior. Since `async_unload_entry` awaits city close before
subsequent activity/provider/frontend cleanup, normal return from an independently
cancelled save now permits that later cleanup to proceed. The precise trigger for
the previously observed real-HA shutdown cancellation remains unproven; this
review does not attribute the actual incident solely to this defect.

Both drains await a non-raising `gather(return_exceptions=True)` envelope.
Independent child cancellation is therefore returned as an outcome, while a
`CancelledError` raised by the shield await marks cancellation of close itself.
The implementation does not classify child cancellation using an old nonzero
caller cancellation counter or erase caller cancellation state. It drains owned
work and propagates the actual close-caller cancellation, in keeping with
[Python's cleanup/cancellation guidance](https://docs.python.org/3.14/library/asyncio-task.html#task-cancellation).

Independent verification extracted the exact `CityLookup` class through Python's
AST without importing Home Assistant or a native provider. With real asyncio
tasks, synthetic stores and explicit event barriers, ten bounded cases passed:
child cancellation before/during close, ordinary write draining, caller
cancellation during update/save draining, repeated caller cancellation, ordinary
save failure, caller cancellation combined with a save failure or child
cancellation, and direct-save error identity. No raw loop diagnostic was emitted.

A diagnostic side effect was also checked against the exact baseline: CPython
3.14.7 can emit an asyncio shielded-future OSError diagnostic after the cancelled
update's original `save()` shield, even though close retrieves the save failure.
The baseline and intermediate cancellation-only fix each produced one event for
ordinary failed-save cleanup. This confirmed a distinct, pre-existing noisy
diagnostic/privacy defect; preserving a write after caller cancellation also
exposed it when that write failed. The final patch fixes it locally by wrapping
the original `save()` shield and both close drains in non-raising outcomes. The
actual write remains tracked in `save_task`; direct `save()` still raises the
identical original OSError. The final ten-case independent probe captured **zero
event-loop diagnostic events**, including both failing-write paths. No global
logging or exception-handler suppression was added to product code.

An initial independent probe left its own deliberately blocked update-finalizer
event unreleased; its standalone process was stopped with SIGTERM, exit 143.
The corrected fixture releases both owned barriers and passed all ten cases
with a hard outer watchdog. That fixture mistake is not product or CPython crash
evidence.

## Picture filename and cleanup

The visible chooser retains a separate filename using `textContent`, so arbitrary
filenames are not interpreted as HTML. The native input still clears its value
to permit selecting the same file again. Cropping, upload and server image-ID
validation remain unchanged; uploads still use the generated constant JPEG
filename rather than the user's original filename.

The current crop cleanup runs on accepted flow navigation and dialog close.
Clearing advances the crop generation, removes decoded image state and hides the
filename; detached or stale FileReader/Image completion cannot reactivate an old
crop. The existing late-upload guard prevents an upload completing after Back or
close from submitting to another flow step. The existing disclosure that native
uploaded images may remain after cancellation is unchanged.

The focused browser-DOM regression passed independently once. It covers visible
filename retention, reselection, native chooser invocation, picker cancellation,
decode failure, successful upload, removal, failed upload retention, navigation
during an upload and close cleanup. This is jsdom evidence, not real mobile
file-picker, physical-display or visual acceptance.

## Exact public-license privacy exception

The privacy scanner exception is limited to one repository-relative path and its
exact SHA-256: the supplemental public runtime notice at
`custom_components/homecircle/_findmy_runtime/LICENSE.md`, hash
`d0d08d053daacc07d9357fbdae0fefb972eec9ae6a14cada17695d6f5c1f28e4`.
Those bytes match the notice-correction baseline and contain the public FSF
postal address. Any changed byte at that path is refused. The same text at a
different path still receives all ordinary rules. Existing regex rules and the
main entry point's symlink refusal are unchanged.

All seven exact privacy unit checks passed independently. This avoids a false
positive for the already reviewed notice; it does not generally allow postal
addresses, unknown licenses or private content, nor provide legal clearance.

## Reviewed source hashes and remaining validation

| File relative to candidate | SHA-256 |
| --- | --- |
| `custom_components/homecircle/normalize.py` | `e62fb2c583d3227ba70a2bd4771ef564bcd99be4993e0d2cf3ffcf5fb2ceeaf4` |
| `tests/test_normalize.py` | `da1b71af11bb8b7946b1050d75fcf64594550512120456d85eda342de96a0c69` |
| `custom_components/homecircle/city_lookup.py` | `cc3abdc01503d7e4ba1c1ab747c4d24d03dcc6167d467c4e170e5c56be1490e0` |
| `tests/test_city_lookup.py` | `9a3849ac88c27e9e0fe5be3dcdc7fc928f1cb8b7125cd3d20c68ec2669549967` |
| `frontend/homecircle-card/src/settings-dialog.js` | `cef3006b0e1b9e10a24b58631bdeddd26061176588cc37f7e33266e8f4cfffe5` |
| `frontend/homecircle-card/test/lifecycle.test.mjs` | `59d0384c60fb13d3694533374be9414b566a492525bb354f79e2157d22b4a34f` |
| `custom_components/homecircle/frontend/homecircle-card.js` | `80b2727d18a0b8edb052c47d2c718850adf19bf5d35c2af6c3eb86c07f1f6cac` |
| `scripts/check_public_files.py` | `216331d16af8fb2ec636e1466303923ecfe32c76f78ea72f89d373c80c9713d2` |
| `tests/test_privacy_guard.py` | `4902e407d07162fe0c5a66c439b918c1cfa78a76378d81bb9f9894c6eb7689bc` |

The full exact-source Linux backend suite and final package/frontend checks are
separate controller-owned work. Their results must be attached to the final
frozen inventory; this review does not claim they have completed. Published
beta20 assets, the root dirty source tree and owner accounts were not changed by
this review.

## Independent review of the native package validation harness

The separate `backend-validation/native-release1-package` driver, launcher and
contracts were reviewed read-only. No additional blocking source finding was
identified. Its acceptance scope is an unreleased, same-version development
preview on the pinned minimum-Core native Linux container; it does not claim
managed Core lifecycle, HACS delivery, new provider acceptance or stable-release
approval.

The chain binds reviewed configuration to exact source/archive/inventory hashes,
the canonical commit's public-file blobs, unchanged release builder/validator,
the six manifest requirements and actual 24-package closure. It builds the
frontend twice, checks exact frontend bytes and 110 actual test counts, runs the
full backend suite with no attached Docker networks, checks the named optional
skip and configured required regressions, then checks source/frontend continuity
and an identical rebuilt package. Successful acceptance also requires actual
owned-container stop/removal and private-workspace cleanup. Narrow projected
summaries exclude raw test logs, exception messages, XML bodies and account state.

All eleven standalone harness contracts passed independently, and the launcher
passed `bash -n`. Reviewed SHA-256 values:

- Driver: `e97e3f71fc9f7ceb9391f86e0178c59c3b88a2fafe5f397e25a9fb69fe568e59`.
- Launcher: `da56796a39c021f9cc33603715f22279666776ffd2c7177e1acf1dea3fcf5462`.
- Contracts: `7ca2874e37857c2d82dab22f7977e4b986aa21c2b3ca86700e140282cb44cff7`.

The final configuration was not frozen at review time. It must pin the final
driver/source/checker hashes and name every new backend regression, including
passive-zone handling, cancelled-child/caller drains, failed-save disposition,
raw-diagnostic canary and the exact-license privacy exception. The two names in
the example configuration alone are not that final regression list. Actual
native execution, final configuration/commit review and sanitized result review
remain separate from these eleven preparation contracts.
