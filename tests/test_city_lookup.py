"""City resolution stays opt-in, local-cached, source-bound and rate-limited."""

from copy import deepcopy
from types import SimpleNamespace
from datetime import timedelta
from unittest.mock import AsyncMock, patch
import pytest
from homeassistant.core import State
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.homecircle.city_lookup import CityLookup, parse_result, point_key
from custom_components.homecircle.api import reported_address


def runtime(enabled=True, address="Example street, Wisconsin"):
    origin = 0
    source = "device_tracker.example_phone"
    member = SimpleNamespace(
        id=source,
        place=None,
        focusable=True,
        location=SimpleNamespace(
            latitude=origin,
            longitude=origin,
            evidence=SimpleNamespace(source_entity=source),
        ),
    )
    return SimpleNamespace(
        config={
            "city_lookup_enabled": enabled,
            "members": {source: {"trackers": [source]}},
        },
        household=SimpleNamespace(members=[member]),
        states={
            source: State(
                source, "not_home", {"address": address, "source_type": "gps"}
            )
        },
    ), member


def store():
    return SimpleNamespace(
        async_load=AsyncMock(return_value=None), async_save=AsyncMock()
    )


@pytest.mark.parametrize(
    "data,expected",
    [
        (
            {
                "features": [
                    {"properties": {"street": "Example street", "city": "Example city"}}
                ]
            },
            {"street": "Example street", "city": "Example city"},
        ),
        (
            {
                "features": [
                    {
                        "properties": {
                            "osm_key": "place",
                            "osm_value": "town",
                            "name": "Example town",
                        }
                    }
                ]
            },
            {"street": None, "city": "Example town"},
        ),
        ({"features": [{"properties": {"county": "Example county"}}]}, None),
        ({"features": [{"properties": {"city": "bad\x00city"}}]}, None),
    ],
)
def test_result_requires_a_real_city_field(data, expected):
    assert parse_result(data) == expected


async def test_lookup_fills_missing_city_and_reuses_persisted_cache(hass):
    cache_store = store()
    lookup = CityLookup(hass, cache_store)
    await lookup.load()
    data, member = runtime()
    data.city_lookup = lookup
    lookup.fetch = AsyncMock(
        return_value={"city": "Example city", "street": "Other street"}
    )
    with patch(
        "custom_components.homecircle.city_lookup.asyncio.sleep", new=AsyncMock()
    ):
        await lookup.update(data)
        await lookup.update(data)
    assert lookup.fetch.await_count == 1
    assert reported_address(member, data) == "Example street, Example city"
    persisted = deepcopy(cache_store.async_save.call_args.args[0])
    cache_store.async_load.return_value = persisted
    restored = CityLookup(hass, cache_store)
    await restored.load()
    data.city_lookup = restored
    assert reported_address(member, data) == "Example street, Example city"
    data.config["city_lookup_enabled"] = False
    assert reported_address(member, data) == "Example street, Wisconsin"


async def test_lookup_skips_unselected_named_and_already_city_sources(hass):
    for mode in ("unselected", "named", "city", "disabled"):
        lookup = CityLookup(hass, store())
        data, member = runtime(enabled=mode != "disabled")
        if mode == "unselected":
            data.config["members"][member.id]["trackers"] = []
        if mode == "named":
            member.place = "Example place"
        if mode == "city":
            data.states[member.id] = State(
                member.id,
                "not_home",
                {"address": "Example street, Example city", "source_type": "gps"},
            )
        lookup.fetch = AsyncMock()
        if mode != "disabled":
            await lookup.update(data)
        else:
            lookup.schedule(data)
        lookup.fetch.assert_not_awaited()
        await lookup.close()


async def test_failed_lookup_preserves_address_and_limits_survive_restart(hass):
    lookup = CityLookup(hass, store())
    data, member = runtime()
    data.city_lookup = lookup
    lookup.fetch = AsyncMock(return_value=None)
    with patch(
        "custom_components.homecircle.city_lookup.asyncio.sleep", new=AsyncMock()
    ):
        await lookup.update(data)
        await lookup.update(data)
    assert lookup.fetch.await_count == 1
    assert reported_address(member, data) == "Example street, Wisconsin"
    now = dt_util.utcnow()
    lookup.requests = [(now - timedelta(minutes=1)).isoformat()] * 20
    lookup.attempts.clear()
    await lookup.update(data)
    assert lookup.fetch.await_count == 1
    lookup.requests = [(now - timedelta(hours=2)).isoformat()] * 200
    await lookup.update(data)
    assert lookup.fetch.await_count == 1


async def test_options_enable_and_disable_city_lookup(hass):
    entry = MockConfigEntry(
        domain="homecircle",
        data={"people": [], "members": {}, "primary_home": "zone.home", "places": []},
    )
    entry.add_to_hass(hass)
    for enabled in (True, False):
        flow = await hass.config_entries.options.async_init(entry.entry_id)
        assert "city_lookup" in flow["menu_options"]
        flow = await hass.config_entries.options.async_configure(
            flow["flow_id"], {"next_step_id": "city_lookup"}
        )
        assert flow["step_id"] == "city_lookup"
        result = await hass.config_entries.options.async_configure(
            flow["flow_id"], {"city_lookup_enabled": enabled}
        )
        assert result["data"]["city_lookup_enabled"] is enabled
        assert entry.options["city_lookup_enabled"] is enabled
        await hass.async_block_till_done()


def test_point_keys_are_bounded_and_not_plain_coordinates():
    origin = 0
    assert len(point_key(origin, origin)) == 64
    assert point_key(float("nan"), origin) is None
    assert point_key(999, origin) is None


async def test_storage_failure_blocks_coordinate_transmission(hass):
    saved = store()
    saved.async_save.side_effect = OSError()
    lookup = CityLookup(hass, saved)
    data, _ = runtime()
    lookup.fetch = AsyncMock()
    await lookup.update(data)
    lookup.fetch.assert_not_awaited()
    assert lookup.closed


@pytest.mark.parametrize("oversized", [False, True])
async def test_transport_reads_fragmented_body_with_size_bound(hass, oversized):
    import json

    raw = json.dumps({"features": [{"properties": {"city": "Example city"}}]}).encode()
    chunks = [raw[:7], raw[7:20], raw[20:]]
    if oversized:
        chunks = [b" " * 65536, raw]

    class Content:
        async def iter_chunked(self, size):
            for chunk in chunks:
                yield chunk

    class Response:
        status = 200
        content = Content()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    from unittest.mock import Mock

    session = Mock()
    session.get.return_value = Response()
    with patch(
        "custom_components.homecircle.city_lookup.async_get_clientsession",
        return_value=session,
    ):
        result = await CityLookup(hass, store()).fetch(0, 0)
    assert result == (None if oversized else {"city": "Example city", "street": None})
    assert session.get.call_args.kwargs["allow_redirects"] is False


async def test_unload_cancels_city_lookup_and_remove_deletes_cache(hass):
    import asyncio
    from custom_components.homecircle import async_remove_entry

    lookup = CityLookup(hass, store())
    started = asyncio.Event()

    async def waiting():
        started.set()
        await asyncio.Event().wait()

    lookup.task = asyncio.create_task(waiting())
    await started.wait()
    await lookup.close()
    assert lookup.closed and lookup.task.cancelled()
    entry = MockConfigEntry(domain="homecircle")
    with (
        patch(
            "custom_components.homecircle.frontend.async_unregister", new=AsyncMock()
        ),
        patch(
            "custom_components.homecircle.dashboard_setup.async_remove_untouched_dashboard",
            new=AsyncMock(),
        ),
        patch(
            "homeassistant.helpers.storage.Store.async_remove", new=AsyncMock()
        ) as remove,
    ):
        await async_remove_entry(hass, entry)
    assert remove.await_count == 4  # Also removes the Find My migration ledger.


@pytest.mark.parametrize(
    "city,region", [("New York", "NY"), ("Washington", "DC"), ("Georgia", "VT")]
)
async def test_provided_city_matching_region_does_not_transmit(hass, city, region):
    from custom_components.homecircle.city_lookup import address_parts

    value = f"Example street, {city}, {region}"
    assert address_parts(value) == ("Example street", city)
    lookup = CityLookup(hass, store())
    data, _ = runtime(address=value)
    lookup.fetch = AsyncMock()
    await lookup.update(data)
    lookup.fetch.assert_not_awaited()


async def test_structured_cached_city_is_projected_separately(hass):
    from custom_components.homecircle.api import reported_city

    lookup = CityLookup(hass, store())
    data, member = runtime()
    data.city_lookup = lookup
    lookup.cache[point_key(0, 0)] = {
        "city": "Georgia",
        "street": "Other street",
        "saved_at": dt_util.utcnow().isoformat(),
    }
    assert reported_address(member, data) == "Example street, Georgia"
    assert reported_city(member, data) == "Georgia"
    data.config["city_lookup_enabled"] = False
    assert reported_city(member, data) is None


async def test_non_gps_sources_are_never_sent_and_future_budgets_are_retained(hass):
    lookup = CityLookup(hass, store())
    data, member = runtime()
    data.states[member.id] = State(member.id, "home", {"source_type": "router"})
    lookup.fetch = AsyncMock()
    await lookup.update(data)
    lookup.fetch.assert_not_awaited()
    future = dt_util.utcnow() + timedelta(hours=1)
    lookup.requests = [future.isoformat()] * 20
    lookup.prune(dt_util.utcnow())
    assert len(lookup.requests) == 20
    key = point_key(0, 0)
    lookup.cache[key] = {
        "city": "Example city",
        "street": "bad\x00street",
        "saved_at": dt_util.utcnow().isoformat(),
    }
    lookup.prune(dt_util.utcnow())
    assert key not in lookup.cache


async def test_close_waits_for_inflight_disk_save(hass):
    import asyncio

    saved = store()
    started, finish = asyncio.Event(), asyncio.Event()

    async def blocked_save(data):
        started.set()
        await finish.wait()

    saved.async_save.side_effect = blocked_save
    lookup = CityLookup(hass, saved)
    lookup.task = asyncio.create_task(lookup.save())
    await started.wait()
    closing = asyncio.create_task(lookup.close())
    await asyncio.sleep(0)
    assert not closing.done()
    finish.set()
    await closing
    assert lookup.save_task.done() and not lookup.save_task.cancelled()


@pytest.mark.parametrize("cancel_before_close", [True, False])
async def test_close_handles_independently_cancelled_disk_save(
    hass, cancel_before_close
):
    import asyncio

    saved = store()
    started = asyncio.Event()

    async def blocked_save(data):
        started.set()
        await asyncio.Event().wait()

    saved.async_save.side_effect = blocked_save
    lookup = CityLookup(hass, saved)
    lookup.task = asyncio.create_task(lookup.save())
    await started.wait()
    if cancel_before_close:
        lookup.save_task.cancel()
        await asyncio.sleep(0)
    closing = asyncio.create_task(lookup.close())
    if not cancel_before_close:
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert not closing.done()
        lookup.save_task.cancel()
    await closing
    assert lookup.closed and lookup.save_task.cancelled()
    assert not closing.cancelled()


@pytest.mark.parametrize("cancel_stage", ["update", "save"])
async def test_close_preserves_caller_cancellation_after_draining(hass, cancel_stage):
    import asyncio

    saved = store()
    started, finish = asyncio.Event(), asyncio.Event()
    update_draining = asyncio.Event()

    async def blocked_save(data):
        started.set()
        await finish.wait()

    saved.async_save.side_effect = blocked_save
    lookup = CityLookup(hass, saved)
    lookup.save_task = asyncio.create_task(saved.async_save({}))
    await started.wait()
    if cancel_stage == "update":

        async def blocked_update():
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                update_draining.set()
                await finish.wait()
                raise

        lookup.task = asyncio.create_task(blocked_update())
        await asyncio.sleep(0)
    closing = asyncio.create_task(lookup.close())
    if cancel_stage == "update":
        await update_draining.wait()
    else:
        await asyncio.sleep(0)
    assert not closing.done()
    closing.cancel()
    try:
        await asyncio.sleep(0)
        assert not closing.done()
        assert not lookup.save_task.cancelled()
        if cancel_stage == "update":
            assert not lookup.task.done()
    finally:
        finish.set()
    with pytest.raises(asyncio.CancelledError):
        await closing
    assert lookup.closed
    assert lookup.save_task.done() and not lookup.save_task.cancelled()
    if cancel_stage == "update":
        assert lookup.task.done()


async def test_close_preserves_failed_save_cleanup_disposition(hass):
    saved = store()
    saved.async_save.side_effect = OSError("synthetic store failure")
    lookup = CityLookup(hass, saved)
    with pytest.raises(OSError):
        await lookup.save()
    await lookup.close()
    assert lookup.closed


@pytest.mark.parametrize("cancel_close", [False, True])
async def test_cancelled_city_save_failure_has_no_raw_loop_diagnostic(
    hass, cancel_close
):
    import asyncio

    loop = asyncio.get_running_loop()
    original_handler = loop.get_exception_handler()
    diagnostics = []
    loop.set_exception_handler(lambda _loop, context: diagnostics.append(context))
    started, finish = asyncio.Event(), asyncio.Event()
    failure = OSError("synthetic private city storage failure canary")
    saved = store()

    async def blocked_save(data):
        started.set()
        await finish.wait()
        raise failure

    saved.async_save.side_effect = blocked_save
    lookup = CityLookup(hass, saved)
    lookup.task = asyncio.create_task(lookup.save())
    closing = None
    try:
        await started.wait()
        closing = asyncio.create_task(lookup.close())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        if cancel_close:
            closing.cancel()
            await asyncio.sleep(0)
        finish.set()
        if cancel_close:
            with pytest.raises(asyncio.CancelledError):
                await closing
        else:
            await closing
        assert lookup.closed and lookup.save_task.done()
        assert not lookup.save_task.cancelled()

        saved = store()
        saved.async_save.side_effect = failure
        direct = CityLookup(hass, saved)
        with pytest.raises(OSError) as raised:
            await direct.save()
        assert raised.value is failure
        await direct.close()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert not any(context.get("exception") is failure for context in diagnostics)
        assert not any("canary" in str(context) for context in diagnostics)
    finally:
        finish.set()
        if closing is not None:
            await asyncio.gather(closing, return_exceptions=True)
        loop.set_exception_handler(original_handler)
