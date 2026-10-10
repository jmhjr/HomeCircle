"""Run two real HA Core processes with disposable storage and synthetic sources.

No pytest storage mocks, existing HA configuration, or tracking providers.
This checks Core lifecycle/persistence; it is not browser or HACS acceptance.
"""

import asyncio
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]


async def run_phase(
    config_dir: str,
    phase: str,
    package_version: str | None = None,
    remove: bool = False,
) -> None:
    from homeassistant import bootstrap, loader
    from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
    from homeassistant.components.lovelace.const import LOVELACE_DATA
    from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
    from homeassistant.core import HomeAssistant

    hass = HomeAssistant(config_dir)
    loader.async_setup(hass)
    config = {
        "homeassistant": {
            "name": "Example test household",
            ATTR_LATITUDE: 0.0,
            ATTR_LONGITUDE: 0.0,
            "elevation": 0,
            "unit_system": "metric",
            "time_zone": "UTC",
        },
        "http": {"server_host": "127.0.0.1", "server_port": 18123},
        "person": [
            {
                "id": "example_member",
                "name": "Example Member",
                "device_trackers": ["device_tracker.example_phone"],
            },
            {
                "id": "example_second",
                "name": "Example Second",
                "device_trackers": ["device_tracker.example_router"],
            },
        ],
        "zone": [],
    }
    assert await bootstrap.async_from_config_dict(config, hass)
    try:
        await hass.async_start()
        hass.states.async_set(
            "device_tracker.example_phone",
            "home",
            {
                "source_type": "gps",
                ATTR_LATITUDE: 0.0,
                ATTR_LONGITUDE: 0.0,
            },
        )
        hass.states.async_set(
            "device_tracker.example_router",
            "home",
            {"source_type": "router", "in_zones": ["zone.home"]},
        )
        hass.states.async_set("zone.example_residence", "0")
        hass.states.async_set("zone.example_work", "0")
        await hass.async_block_till_done()
        from custom_components.homecircle.selection import tracker_suggestions

        assert tracker_suggestions(hass, "person.example_member") == (
            ["device_tracker.example_phone"],
            "device_tracker.example_phone",
        )
        assert hass.states.get("person.example_second").state == "home"
        assert (
            hass.states.get("person.example_second").attributes.get(ATTR_LATITUDE)
            is None
        )
        household = {
            "people": ["person.example_member", "person.example_second"],
            "primary_home": "zone.home",
            "places": ["zone.example_work"],
        }
        if phase == "create":
            manager = hass.config_entries.flow
            result = await manager.async_init(
                "homecircle", context={"source": SOURCE_USER}
            )
            result = await manager.async_configure(result["flow_id"], household)
            for tracker in [
                "device_tracker.example_phone",
                "device_tracker.example_router",
            ]:
                assert result["step_id"] == "assign_tracker"
                result = await manager.async_configure(
                    result["flow_id"], {"tracker": tracker}
                )
                assert result["step_id"] == "member"
                result = await manager.async_configure(
                    result["flow_id"], {"trackers": [tracker]}
                )
            result = await manager.async_configure(
                result["flow_id"], {"next_step_id": "confirm_save"}
            )
            entry = result["result"]
            await hass.async_block_till_done()
            # Persist an options override and verify it survives a separate process.
            manager = hass.config_entries.options
            result = await manager.async_init(entry.entry_id)
            result = await manager.async_configure(
                result["flow_id"], {"next_step_id": "household"}
            )
            result = await manager.async_configure(result["flow_id"], household)
            result = await manager.async_configure(
                result["flow_id"],
                {
                    "trackers": ["device_tracker.example_phone"],
                    "additional_residences": ["zone.example_residence"],
                },
            )
            result = await manager.async_configure(result["flow_id"], {"trackers": []})
            await manager.async_configure(
                result["flow_id"], {"next_step_id": "confirm_save"}
            )
            await hass.async_block_till_done()
        entries = hass.config_entries.async_entries("homecircle")
        assert len(entries) == 1
        entry = entries[0]
        assert entry.state == ConfigEntryState.LOADED
        activity = entry.runtime_data.activity
        if phase in ("create", "install"):
            from homeassistant.util import dt as dt_util

            activity.append(
                "person.example_member", "refresh", "checked", dt_util.utcnow()
            )
            await activity.save()
        else:
            assert any(
                event.get("value") == "checked"
                for event in activity.events["person.example_member"]
            )
        assert any(
            event["kind"] == "started"
            for event in activity.events["person.example_member"]
        )
        dashboards = hass.data[LOVELACE_DATA].dashboards
        assert "dashboard-homecircle" in dashboards
        dashboard_config = await dashboards["dashboard-homecircle"].async_load(False)
        assert dashboard_config["views"][0]["cards"] == [
            {
                "type": "custom:homecircle-card",
                "fill_screen": True,
                "map_tiles": "osm",
            }
        ]
        if package_version:
            import aiohttp
            import custom_components.homecircle as installed

            expected = Path(config_dir) / "custom_components/homecircle"
            assert Path(installed.__file__).resolve().parent == expected.resolve()
            resources = hass.data[LOVELACE_DATA].resources
            await resources.async_get_info()
            if phase == "create":
                await resources.async_create_item(
                    {"url": "/local/example_unrelated.js", "res_type": "module"}
                )
            items = resources.async_items()
            owned = [
                item for item in items if item["url"].startswith("/homecircle_static/")
            ]
            assert len(owned) == 1
            resource = urlsplit(owned[0]["url"])
            assert resource.path == "/homecircle_static/homecircle-card.js"
            query = parse_qs(resource.query)
            assert query.get("v") == [package_version]
            digest = hashlib.sha256(
                (expected / "frontend/homecircle-card.js").read_bytes()
            ).hexdigest()[:12]
            assert query.get("asset") == [digest]
            assert any(item["url"] == "/local/example_unrelated.js" for item in items)
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://127.0.0.1:18123" + owned[0]["url"]
                ) as response:
                    assert response.status == 200
                    assert (
                        await response.read()
                        == (expected / "frontend/homecircle-card.js").read_bytes()
                    )
        assert entry.runtime_data.config["members"]["person.example_member"][
            "additional_residences"
        ] == ["zone.example_residence"]
        assert (
            entry.runtime_data.config["members"]["person.example_second"]["trackers"]
            == []
        )
        assert not entry.runtime_data.missing
        assert entry.runtime_data.household.counts["home"] == 2
        assert entry.runtime_data.household.focus_ids["home"] == (
            "person.example_member",
        )
        # A member at their configured residence counts Home but leaves house focus.
        hass.states.async_set(
            "device_tracker.example_phone",
            "Example Residence",
            {
                "source_type": "gps",
                "in_zones": ["zone.example_residence"],
                ATTR_LATITUDE: 1.0,
                ATTR_LONGITUDE: 0.0,
            },
        )
        await hass.async_block_till_done()
        assert entry.runtime_data.household.counts["home"] == 2
        assert entry.runtime_data.household.focus_ids["home"] == ()
        assert entry.runtime_data.household.focus_ids["all_residences"] == (
            "person.example_member",
        )
        assert "life360" not in hass.config.components
        assert await hass.config_entries.async_reload(entry.entry_id)
        old_runtime = entry.runtime_data
        hass.states.async_remove("zone.example_residence")
        await hass.async_block_till_done()
        assert "zone.example_residence" in old_runtime.missing
        assert await hass.config_entries.async_unload(entry.entry_id)
        hass.states.async_set("zone.example_residence", "0")
        await hass.async_block_till_done()
        assert not old_runtime.states
        assert await hass.config_entries.async_setup(entry.entry_id)
        if remove:
            assert await hass.config_entries.async_remove(entry.entry_id)
            assert not hass.config_entries.async_entries("homecircle")
            from homeassistant.helpers.storage import Store

            assert (
                await Store(
                    hass, 1, f"homecircle.activity.{entry.entry_id}"
                ).async_load()
                is None
            )
            items = resources.async_items()
            assert not any(
                item["url"].startswith("/homecircle_static/") for item in items
            )
            assert any(item["url"] == "/local/example_unrelated.js" for item in items)
            assert hass.states.get("person.example_member") is not None
        print(
            json.dumps(
                {"phase": phase, "result": "passed", "entry_count": len(entries)}
            )
        )
    finally:
        await hass.async_stop()


def main():
    if len(sys.argv) == 3:
        asyncio.run(run_phase(sys.argv[1], sys.argv[2]))
        return
    with tempfile.TemporaryDirectory(prefix="homecircle-ha-") as directory:
        components = Path(directory) / "custom_components"
        components.mkdir()
        (components / "homecircle").symlink_to(
            ROOT / "custom_components/homecircle", target_is_directory=True
        )
        for phase in ("create", "restart"):
            subprocess.run(
                [sys.executable, __file__, directory, phase],
                check=True,
                timeout=120,
                cwd=ROOT,
            )
    print("Disposable HA storage removed; both Core processes passed.")


if __name__ == "__main__":
    main()
