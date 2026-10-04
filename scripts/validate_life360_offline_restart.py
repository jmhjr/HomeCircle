#!/usr/bin/env python3
"""Check direct tracker recovery across two disposable HA Core processes.

The Life360 replies and credential are fictional. No provider network call is made.
"""

import asyncio
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]


async def run_phase(config_dir: str, phase: str) -> None:
    from homeassistant import bootstrap, loader
    from homeassistant.config_entries import ConfigEntryState, SOURCE_USER
    from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
    from homeassistant.core import HomeAssistant

    raw = {
        "id": "example-member",
        "location": {ATTR_LATITUDE: "1", ATTR_LONGITUDE: "2"},
    }

    class FakeAPI:
        async def get_circles(self):
            return [{"id": "example-circle"}]

        async def get_circle_members(self, _circle):
            return [raw]

        async def get_circle_member(self, _circle, _member):
            return raw

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
        "http": {"server_host": "127.0.0.1", "server_port": 18126},
    }
    provider = (
        {"return_value": FakeAPI()}
        if phase == "create"
        else {"side_effect": OSError("fictional offline startup")}
    )
    with (
        patch(
            "custom_components.homecircle.config_flow.validate_account",
            new_callable=AsyncMock,
            return_value="example-account-fingerprint",
        ),
        patch(
            "custom_components.homecircle.life360_direct.authorized_client",
            new_callable=AsyncMock,
            **provider,
        ),
    ):
        assert await bootstrap.async_from_config_dict(config, hass)
        try:
            await hass.async_start()
            if phase == "create":
                manager = hass.config_entries.flow
                result = await manager.async_init(
                    "homecircle", context={"source": SOURCE_USER}
                )
                selection = {
                    "people": [],
                    "primary_home": "zone.home",
                    "life360_direct": True,
                }
                result = await manager.async_configure(result["flow_id"], selection)
                result = await manager.async_configure(
                    result["flow_id"],
                    {"method": "token", "secret": "fictional-token"},
                )
                result = await manager.async_configure(result["flow_id"], {})
                await hass.async_block_till_done()
                entry = result["result"]
                tracker = entry.runtime_data.managed_trackers["life360"].trackers[
                    "example-member"
                ]
                assert hass.states.get(tracker.entity_id).attributes[ATTR_LATITUDE] == 1
                options = hass.config_entries.options
                result = await options.async_init(entry.entry_id)
                result = await options.async_configure(
                    result["flow_id"],
                    {**selection, "people_trackers": [tracker.entity_id]},
                )
                result = await options.async_configure(result["flow_id"], {})
                assert result["step_id"] == "confirm"
                await options.async_configure(result["flow_id"], {})
                await hass.async_block_till_done()
            entries = hass.config_entries.async_entries("homecircle")
            assert len(entries) == 1
            entry = entries[0]
            assert entry.state is ConfigEntryState.LOADED
            client = entry.runtime_data.managed_trackers["life360"]
            tracker = client.trackers["example-member"]
            assert entry.runtime_data.config["people_trackers"] == [tracker.entity_id]
            if phase == "restart_offline":
                assert hass.states.get(tracker.entity_id).state == "unavailable"
                assert client.health_snapshot().state == "network_error"
                assert tracker.entity_id in entry.runtime_data.unavailable
            print(json.dumps({"phase": phase, "result": "passed"}))
        finally:
            await hass.async_stop()


def main() -> None:
    if len(sys.argv) == 3:
        asyncio.run(run_phase(sys.argv[1], sys.argv[2]))
        return
    with tempfile.TemporaryDirectory(prefix="homecircle-life360-restart-") as directory:
        components = Path(directory) / "custom_components"
        components.mkdir()
        (components / "homecircle").symlink_to(
            ROOT / "custom_components/homecircle", target_is_directory=True
        )
        for phase in ("create", "restart_offline"):
            subprocess.run(
                [sys.executable, __file__, directory, phase],
                check=True,
                timeout=120,
                cwd=ROOT,
            )
    print("Disposable HA storage removed; both Core processes passed.")


if __name__ == "__main__":
    main()
