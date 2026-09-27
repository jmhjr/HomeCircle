"""Exercise real HA Person source switching with fictional inputs and a release ZIP."""

import asyncio
from datetime import timedelta
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


async def run(directory):
    from homeassistant import bootstrap, loader
    from homeassistant.config_entries import SOURCE_USER
    from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
    from homeassistant.core import HomeAssistant
    from homeassistant.util import dt

    phone = "device_tracker.example_phone"
    cloud = "device_tracker.example_cloud"
    router = "device_tracker.example_router"
    person = "person.example_member"
    report = "sensor.example_phone_report"
    trackers = [phone, cloud, router]
    hass = HomeAssistant(directory)
    loader.async_setup(hass)
    assert await bootstrap.async_from_config_dict(
        {
            "homeassistant": {
                "name": "Example source switching",
                ATTR_LATITUDE: 0.0,
                ATTR_LONGITUDE: 0.0,
                "time_zone": "UTC",
                "unit_system": "metric",
                "elevation": 0,
            },
            "http": {"server_host": "127.0.0.1", "server_port": 18128},
            "person": [
                {
                    "id": "example_member",
                    "name": "Example Member",
                    "device_trackers": trackers,
                }
            ],
            "zone": [],
        },
        hass,
    )
    try:
        await hass.async_start()

        async def gps(entity, state, offset):
            hass.states.async_set(
                entity,
                state,
                {
                    "source_type": "gps",
                    ATTR_LATITUDE: offset,
                    ATTR_LONGITUDE: offset,
                },
            )
            await hass.async_block_till_done()

        async def network(state):
            hass.states.async_set(router, state, {"source_type": "router"})
            await hass.async_block_till_done()

        await gps(phone, "not_home", 1.0)
        await gps(cloud, "not_home", 2.0)
        await network("home")
        old_report = dt.utcnow() - timedelta(hours=2)
        hass.states.async_set(
            report, old_report.isoformat(), {"device_class": "timestamp"}
        )
        flow = hass.config_entries.flow
        result = await flow.async_init("homecircle", context={"source": SOURCE_USER})
        for data in [
            {"people": [person], "primary_home": "zone.home", "places": []},
            {"trackers": trackers, "configure_sensors": True},
            {"location_reported_at": report, "location_report_source": phone},
            {},
        ]:
            result = await flow.async_configure(result["flow_id"], data)
            assert not result.get("errors"), result.get("errors")
        assert result["type"] == "create_entry"
        await hass.async_block_till_done()
        entry = result["result"]

        def check(label, source, presence, located, freshness=None):
            household = entry.runtime_data.household
            assert len(household.members) == 1
            member = household.members[0]
            assert member.id == person
            assert hass.states.get(person).attributes.get("source") == source, label
            assert member.active_source_entity == source, label
            assert member.presence == presence, label
            assert (
                household.counts[presence] == 1 and sum(household.counts.values()) == 1
            )
            assert member.focusable is located, (label, member.issues)
            assert len(household.focus_ids["overview"]) == int(located)
            if freshness:
                assert member.location.evidence.freshness == freshness, label
                if freshness == "unknown":
                    assert member.location.evidence.reported_at is None
                elif freshness == "stale":
                    assert member.location.evidence.reported_at == old_report
            print(
                f"PASS: {label}; one member; {presence}; focusable={located}; freshness={freshness}",
                flush=True,
            )

        check("Router Home with two conflicting GPS candidates", router, "home", False)
        await network("not_home")
        await gps(phone, "not_home", 3.0)
        check("Phone GPS takes over after router leaves", phone, "away", True, "stale")
        await gps(cloud, "not_home", 4.0)
        check(
            "Newer cloud GPS takes over without borrowing phone timestamp",
            cloud,
            "away",
            True,
            "unknown",
        )
        hass.states.async_set(cloud, "unavailable")
        await hass.async_block_till_done()
        check("Cloud unavailable falls back to phone", phone, "away", True, "stale")
        await network("home")
        check(
            "Router Home with conflicting away GPS excludes map focus",
            router,
            "home",
            False,
        )
        await gps(phone, "home", 0.0)
        check(
            "Router Home with matching supplemental phone GPS",
            router,
            "home",
            True,
            "stale",
        )
        hass.states.async_set(
            report, dt.utcnow().isoformat(), {"device_class": "timestamp"}
        )
        await hass.async_block_till_done()
        check(
            "Explicit new phone report clears stale evidence",
            router,
            "home",
            True,
            "fresh",
        )
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        check(
            "Reload preserves one member and source-bound mapping",
            router,
            "home",
            True,
            "fresh",
        )
    finally:
        await hass.async_stop()


def main():
    if len(sys.argv) == 2:
        asyncio.run(run(sys.argv[1]))
        return
    with tempfile.TemporaryDirectory(prefix="homecircle-sources-") as directory:
        target = Path(directory) / "custom_components/homecircle"
        target.mkdir(parents=True)
        with zipfile.ZipFile(ROOT / "release/homecircle.zip") as archive:
            for name in archive.namelist():
                assert not Path(name).is_absolute() and ".." not in Path(name).parts
            archive.extractall(target)
        subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), directory],
            cwd=directory,
            check=True,
            timeout=120,
        )
    print("Multi-source checks passed; disposable configuration removed.")


if __name__ == "__main__":
    main()
