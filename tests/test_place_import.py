"""Import previews, cancellation, duplicate protection and retry behavior."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.data_entry_flow import FlowResultType, InvalidData

from custom_components.homecircle.place_import import parse_places
from tests.test_config_flow import create, start_options


PLACES = [
    {
        "name": "Example Park",
        ATTR_LATITUDE: "1",
        ATTR_LONGITUDE: "2",
        "radius": "152.4",
    },
    {"name": "Example Park", ATTR_LATITUDE: "3", ATTR_LONGITUDE: "4", "radius": "76.2"},
    {"name": "Home", ATTR_LATITUDE: "0", ATTR_LONGITUDE: "0", "radius": "100"},
    {"name": "Bad place", ATTR_LATITUDE: "nan", ATTR_LONGITUDE: "0", "radius": "100"},
]


async def test_paused_place_import_never_opens_provider_fetch(hass, household):
    from custom_components.homecircle.provider_controls import async_get_controls

    entry, flow = await begin(hass, household)
    controls = await async_get_controls(hass, entry.entry_id)
    with (
        patch.object(hass.config_entries, "async_reload", new=AsyncMock()),
        patch("custom_components.homecircle.place_import.fetch", new=AsyncMock()) as fetch,
    ):
        await controls.async_set_paused("life360", True)
        flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"account": "0"})
    assert flow["errors"] == {"base": "provider_paused"}
    fetch.assert_not_awaited()


async def test_pause_cancels_and_drains_inflight_place_fetch(hass, household):
    from custom_components.homecircle.provider_controls import async_get_controls

    entry, flow = await begin(hass, household)
    controls = await async_get_controls(hass, entry.entry_id)
    entered, drained = asyncio.Event(), asyncio.Event()

    async def pending(*_args):
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            await asyncio.sleep(0)
            drained.set()

    with (
        patch.object(hass.config_entries, "async_reload", new=AsyncMock()),
        patch("custom_components.homecircle.place_import.fetch", side_effect=pending),
    ):
        task = asyncio.create_task(hass.config_entries.options.async_configure(flow["flow_id"], {"account": "0"}))
        await entered.wait()
        await controls.async_set_paused("life360", True)
        result = await task
        assert result["errors"] == {"base": "provider_paused"}
        assert drained.is_set()
    hass.config_entries.options.async_abort(flow["flow_id"])
    assert not controls._operations


async def test_denied_place_fetch_persists_stop_and_repeated_form_cannot_retry(hass, household):
    from life360 import Unauthorized
    from custom_components.homecircle.provider_controls import ProviderControls, async_get_controls

    entry, flow = await begin(hass, household)
    with (
        patch.object(hass.config_entries, "async_reload", new=AsyncMock()),
        patch("custom_components.homecircle.place_import.fetch", new=AsyncMock(side_effect=Unauthorized("fictional", None))) as fetch,
    ):
        for _ in range(2):
            flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"account": "0"})
            assert flow["errors"] == {"base": "provider_paused"}
        await hass.async_block_till_done()
    fetch.assert_awaited_once()
    assert (await async_get_controls(hass, entry.entry_id)).paused("life360")
    restored = ProviderControls(hass, entry.entry_id)
    await restored.async_load()
    assert restored.paused("life360")


def test_parse_places_rejects_bad_values_and_discards_private_extras():
    rows = parse_places(PLACES + [None, {}, {**PLACES[0], "radius": True}])
    assert len(rows) == 3
    assert rows[0] == {
        "name": "Example Park",
        "location": {ATTR_LATITUDE: 1.0, ATTR_LONGITUDE: 2.0, "radius": 152.4},
    }


async def begin(hass, household):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = await create(hass, household)
    home = hass.states.get("zone.home")
    hass.states.async_set(
        "zone.home",
        "0",
        {
            **home.attributes,
            "friendly_name": "Home",
            ATTR_LATITUDE: 0.0,
            ATTR_LONGITUDE: 0.0,
        },
    )
    saved = MockConfigEntry(
        domain="life360",
        options={
            "accounts": {
                "Example connection": {
                    "enabled": True,
                    "authorization": "Bearer synthetic-token",
                }
            }
        },
    )
    saved.add_to_hass(hass)
    flow = await start_options(hass.config_entries.options, entry, "import_places")
    return entry, flow


async def choose(hass, flow):
    manager = hass.config_entries.options
    with patch(
        "custom_components.homecircle.place_import.fetch",
        AsyncMock(
            side_effect=[[{"id": "synthetic-circle", "name": "Example circle"}], PLACES]
        ),
    ) as fetch:
        flow = await manager.async_configure(flow["flow_id"], {"account": "0"})
        flow = await manager.async_configure(flow["flow_id"], {"circle": "0"})
    assert fetch.await_count == 2
    return flow


async def review(hass, flow):
    manager = hass.config_entries.options
    flow = await manager.async_configure(flow["flow_id"], {"places": ["0", "1"]})
    for name, lat, lon in [("Example Park", 1.0, 2.0), ("Example Park (2)", 3.0, 4.0)]:
        flow = await manager.async_configure(
            flow["flow_id"],
            {
                "name": name,
                "location": {ATTR_LATITUDE: lat, ATTR_LONGITUDE: lon, "radius": 100.0},
            },
        )
    assert flow["step_id"] == "import_place_confirm"
    return flow


async def test_preview_empty_selection_and_cancel_make_no_zones(hass, household):
    entry, flow = await begin(hass, household)
    original = dict(entry.options)
    with patch(
        "custom_components.homecircle.place_import.async_create_zone", AsyncMock()
    ) as create_zone:
        flow = await choose(hass, flow)
        assert flow["description_placeholders"] == {
            "available": "2",
            "existing": "1",
            "invalid": "1",
        }
        picker = next(iter(flow["data_schema"].schema.values()))
        assert [o["value"] for o in picker.config["options"]] == ["0", "1"]
        with pytest.raises(InvalidData):
            await hass.config_entries.options.async_configure(
                flow["flow_id"], {"places": ["2"]}
            )
        flow = await hass.config_entries.options.async_configure(
            flow["flow_id"], {"places": []}
        )
        assert flow["errors"] == {"base": "place_import_empty"}
        flow = await review(hass, flow)
        assert "Bearer" not in str(flow)
        hass.config_entries.options.async_abort(flow["flow_id"])
        create_zone.assert_not_awaited()
    assert entry.options == original


async def test_import_creates_reviewed_zones_only_after_confirmation(hass, household):
    entry, flow = await begin(hass, household)
    before = dict(entry.options or entry.data)
    flow = await choose(hass, flow)
    flow = await review(hass, flow)
    flow = await hass.config_entries.options.async_configure(
        flow["flow_id"], {"confirm": False}
    )
    assert flow["errors"] == {"base": "place_import_confirm"}
    with patch(
        "custom_components.homecircle.place_import.async_create_zone",
        AsyncMock(side_effect=["zone.example_import", "zone.example_import_2"]),
    ) as create_zone:
        flow = await hass.config_entries.options.async_configure(
            flow["flow_id"], {"confirm": True}
        )
    assert flow["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert create_zone.await_count == 2
    assert entry.options["primary_home"] == before["primary_home"]
    assert entry.options["members"] == before["members"]
    assert entry.options["places"] == [
        *before["places"],
        "zone.example_import",
        "zone.example_import_2",
    ]


async def test_partial_failure_retries_only_remaining_zones(hass, household):
    _, flow = await begin(hass, household)
    flow = await review(hass, await choose(hass, flow))
    with patch(
        "custom_components.homecircle.place_import.async_create_zone",
        AsyncMock(side_effect=["zone.example_import", None, "zone.example_import_2"]),
    ) as create_zone:
        flow = await hass.config_entries.options.async_configure(
            flow["flow_id"], {"confirm": True}
        )
        assert flow["errors"] == {"base": "place_import_create"}
        flow = await hass.config_entries.options.async_configure(
            flow["flow_id"], {"confirm": True}
        )
        assert create_zone.await_count == 3
        assert create_zone.await_args_list[0].args[1] == "Example Park"
        assert create_zone.await_args_list[2].args[1] == "Example Park (2)"
    assert flow["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()


async def test_new_conflict_blocks_import_before_any_writes(hass, household):
    _, flow = await begin(hass, household)
    flow = await review(hass, await choose(hass, flow))
    hass.states.async_set(
        "zone.example_concurrent",
        "0",
        {"friendly_name": "Concurrent zone", ATTR_LATITUDE: 3.0, ATTR_LONGITUDE: 4.0},
    )
    with patch(
        "custom_components.homecircle.place_import.async_create_zone", AsyncMock()
    ) as create_zone:
        flow = await hass.config_entries.options.async_configure(
            flow["flow_id"], {"confirm": True}
        )
        assert flow["errors"] == {"base": "place_import_changed"}
        create_zone.assert_not_awaited()


async def test_fetch_failure_exposes_no_raw_exception(hass, household):
    _, flow = await begin(hass, household)
    with patch(
        "custom_components.homecircle.place_import.fetch",
        AsyncMock(side_effect=ValueError("private-response")),
    ):
        flow = await hass.config_entries.options.async_configure(
            flow["flow_id"], {"account": "0"}
        )
    assert flow["errors"] == {"base": "place_import_fetch"}
    assert "private-response" not in str(flow)


async def test_real_zone_creation_preserves_existing_zones(hass, household):
    entry, flow = await begin(hass, household)
    primary_before = dict(hass.states.get("zone.home").attributes)
    flow = await review(hass, await choose(hass, flow))
    flow = await hass.config_entries.options.async_configure(
        flow["flow_id"], {"confirm": True}
    )
    await hass.async_block_till_done()
    assert flow["type"] == FlowResultType.CREATE_ENTRY
    assert len(entry.options["places"]) == 3
    for zone_id in entry.options["places"][-2:]:
        state = hass.states.get(zone_id)
        assert state is not None
        assert state.attributes["radius"] == 100.0
        assert state.attributes["passive"] is False
    assert hass.states.get("zone.home").attributes == primary_before


async def test_edited_duplicate_names_are_rejected(hass, household):
    _, flow = await begin(hass, household)
    flow = await choose(hass, flow)
    manager = hass.config_entries.options
    flow = await manager.async_configure(flow["flow_id"], {"places": ["0", "1"]})
    flow = await manager.async_configure(
        flow["flow_id"],
        {
            "name": "Example Park (2)",
            "location": {ATTR_LATITUDE: 1.0, ATTR_LONGITUDE: 2.0, "radius": 100.0},
        },
    )
    assert flow["step_id"] == "import_place_edit"
    assert flow["errors"] == {"base": "zone_already_exists"}


async def test_skipping_first_place_continues_without_validating_its_fields(
    hass, household
):
    _, flow = await begin(hass, household)
    flow = await choose(hass, flow)
    manager = hass.config_entries.options
    flow = await manager.async_configure(flow["flow_id"], {"places": ["0", "1"]})
    flow = await manager.async_configure(flow["flow_id"], {"skip": True})
    assert flow["step_id"] == "import_place_edit"
    assert flow["description_placeholders"] == {"number": "1", "total": "1"}
    flow = await manager.async_configure(
        flow["flow_id"],
        {
            "name": "Example Park (2)",
            "location": {ATTR_LATITUDE: 3.0, ATTR_LONGITUDE: 4.0, "radius": 100.0},
        },
    )
    assert flow["step_id"] == "import_place_confirm"
    assert flow["description_placeholders"]["summary"] == "• Example Park (2) — 100 m"
    with patch(
        "custom_components.homecircle.place_import.async_create_zone",
        AsyncMock(return_value="zone.example_kept"),
    ) as create_zone:
        flow = await manager.async_configure(flow["flow_id"], {"confirm": True})
    await hass.async_block_till_done()
    assert create_zone.await_count == 1
    assert create_zone.await_args.args[1] == "Example Park (2)"


async def test_skipping_last_place_keeps_previously_reviewed_places(hass, household):
    _, flow = await begin(hass, household)
    flow = await choose(hass, flow)
    manager = hass.config_entries.options
    flow = await manager.async_configure(flow["flow_id"], {"places": ["0", "1"]})
    flow = await manager.async_configure(
        flow["flow_id"],
        {
            "name": "Example Park",
            "location": {ATTR_LATITUDE: 1.0, ATTR_LONGITUDE: 2.0, "radius": 100.0},
        },
    )
    flow = await manager.async_configure(flow["flow_id"], {"skip": True})
    assert flow["step_id"] == "import_place_confirm"
    assert flow["description_placeholders"]["summary"] == "• Example Park — 100 m"


async def test_skipping_every_place_exits_without_creating_zones(hass, household):
    entry, flow = await begin(hass, household)
    original = dict(entry.options)
    flow = await choose(hass, flow)
    manager = hass.config_entries.options
    flow = await manager.async_configure(flow["flow_id"], {"places": ["0", "1"]})
    with patch(
        "custom_components.homecircle.place_import.async_create_zone", AsyncMock()
    ) as create_zone:
        flow = await manager.async_configure(flow["flow_id"], {"skip": True})
        flow = await manager.async_configure(flow["flow_id"], {"skip": True})
        create_zone.assert_not_awaited()
    assert flow["type"] == FlowResultType.ABORT
    assert flow["reason"] == "place_import_skipped"
    assert entry.options == original


async def test_zone_added_during_selection_returns_review_error(hass, household):
    _, flow = await begin(hass, household)
    flow = await choose(hass, flow)
    hass.states.async_set(
        "zone.example_race", "0", {ATTR_LATITUDE: 1.0, ATTR_LONGITUDE: 2.0}
    )
    result = await hass.config_entries.options.async_configure(
        flow["flow_id"], {"places": ["0"]}
    )
    assert result["errors"] == {"base": "place_import_changed"}
    assert result["step_id"] == "import_place_select"


async def test_unexpected_and_disabled_external_account_shapes_are_skipped(hass):
    from custom_components.homecircle.place_import import connections
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from homeassistant.config_entries import ConfigEntryDisabler

    for value in (
        [{}],
        "unsupported",
        {"example": None},
        {"example": {"authorization": 3}},
    ):
        entry = MockConfigEntry(domain="life360", options={"accounts": value})
        entry.add_to_hass(hass)
    entry = MockConfigEntry(
        domain="life360",
        disabled_by=ConfigEntryDisabler.USER,
        options={"accounts": {"example": {"authorization": "synthetic"}}},
    )
    entry.add_to_hass(hass)
    assert connections(hass, {}) == []
