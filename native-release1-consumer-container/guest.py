"""Temporary finite QA integration inside the original HA consumer service."""

import asyncio
from collections.abc import Mapping
import importlib.metadata
import importlib.util
import inspect
import json
import os
from pathlib import Path
import platform
import sys

TRACKERS = (
    "device_tracker.consumer_example_phone",
    "device_tracker.consumer_example_router",
)
PEOPLE = ("person.consumer_example_a", "person.consumer_example_b")
UNRELATED = "/local/consumer_example_unrelated.js"


def plain(value):
    if isinstance(value, Mapping):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    return value


async def wait(predicate, limit=75):
    deadline = asyncio.get_running_loop().time() + limit
    while True:
        result = predicate()
        if inspect.isawaitable(result):
            result = await result
        if result:
            return
        if asyncio.get_running_loop().time() >= deadline:
            raise RuntimeError("guest_condition_deadline")
        await asyncio.sleep(0.2)


def identity(entry):
    return plain(
        {
            "entry_id": entry.entry_id,
            "unique_id": entry.unique_id,
            "version": entry.version,
            "minor_version": entry.minor_version,
            "data": entry.data,
            "options": entry.options,
        }
    )


async def async_setup(hass, config):
    if config.get("homecircle_consumer_qa", {}).get("disposable") is not True:
        return False
    from homeassistant.const import (
        EVENT_HOMEASSISTANT_STARTED,
        EVENT_HOMEASSISTANT_STOP,
    )

    control = Path(hass.config.config_dir) / ".homecircle-consumer-qa"

    def load_controls():
        runtime = json.loads((control / "runtime-inputs.json").read_bytes())
        pins_raw = (control / "pins.json").read_bytes()
        import hashlib

        if hashlib.sha256(pins_raw).hexdigest() != runtime["pins_sha256"]:
            raise RuntimeError("guest_pins_refused")
        values = json.loads(pins_raw)
        path = control / "common.py"
        if (
            hashlib.sha256(path.read_bytes()).hexdigest()
            != values["controls"]["common.py"]
        ):
            raise RuntimeError("guest_common_refused")
        spec = importlib.util.spec_from_file_location("consumer_guest_common", path)
        c = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(c)
        c.controls(control, values)
        c.read(Path(__file__), values["controls"]["guest.py"])
        return runtime, values, c

    runtime, values, c = await hass.async_add_executor_job(load_controls)
    task = None

    async def exercise():
        from homeassistant.components.lovelace.const import LOVELACE_DATA
        from homeassistant.config_entries import ConfigEntryState, SOURCE_USER
        from homeassistant.const import __version__ as core_version
        import aiohttp

        request = json.loads(
            await hass.async_add_executor_job(
                lambda: c.read(control / "phase.json", limit=4096)
            )
        )
        c.check(
            set(request) == {"phase", "token"}
            and request["phase"] in {"first", "restart"}
            and request["token"] == runtime["token"],
            "guest_phase_refused",
        )
        phase = request["phase"]
        c.check(
            sys.platform == "linux"
            and platform.machine() == values["machine"]
            and platform.python_version() == values["python"]
            and core_version == values["core"],
            "guest_runtime_refused",
        )
        c.check(
            os.environ.get("PYTHONMALLOC") == "mimalloc"
            and "PYTHONPATH" not in os.environ,
            "guest_allocator_or_import_override",
        )
        versions = values["dependency_versions"] | values["startup_versions"]

        def cached_origins():
            cache = Path(runtime["cache_site"]).resolve()
            c.check(
                cache.is_relative_to(control.parent / "deps")
                and str(cache) in sys.path,
                "normal_config_cache_not_mounted",
            )
            for name, expected in versions.items():
                distribution = importlib.metadata.distribution(name)
                c.check(
                    distribution.version == expected
                    and Path(distribution.locate_file("")).resolve() == cache,
                    "guest_cached_distribution_origin_refused",
                )

        await hass.async_add_executor_job(cached_origins)
        for tracker, source_type in zip(TRACKERS, ("gps", "router"), strict=True):
            attrs = {"source_type": source_type, "in_zones": ["zone.home"]}
            if source_type == "gps":
                attrs.update(latitude=0.0, longitude=0.0, gps_accuracy=5)
            hass.states.async_set(tracker, "home", attrs)
        await wait(
            lambda: all(
                hass.states.get(person) is not None
                and hass.states.get(person).attributes.get("source") == tracker
                for person, tracker in zip(PEOPLE, TRACKERS, strict=True)
            )
        )
        resources = hass.data[LOVELACE_DATA].resources
        await resources.async_get_info()
        if phase == "first":
            c.check(
                not hass.config_entries.async_entries("homecircle"),
                "first_entry_collision",
            )
            manager = hass.config_entries.flow
            result = await manager.async_init(
                "homecircle", context={"source": SOURCE_USER}
            )
            c.check(result["step_id"] == "household", "household_step_refused")
            result = await manager.async_configure(
                result["flow_id"],
                {"people": list(PEOPLE), "primary_home": "zone.home", "places": []},
            )
            for tracker in TRACKERS:
                c.check(result["step_id"] == "assign_tracker", "assign_step_refused")
                result = await manager.async_configure(
                    result["flow_id"], {"tracker": tracker}
                )
                c.check(result["step_id"] == "member", "member_step_refused")
                result = await manager.async_configure(
                    result["flow_id"],
                    {
                        "trackers": [tracker],
                        "additional_residences": [],
                        "kind": "person",
                    },
                )
            c.check(result["step_id"] == "confirm", "confirm_step_refused")
            result = await manager.async_configure(
                result["flow_id"], {"next_step_id": "confirm_save"}
            )
            c.check(result["type"] == "create_entry", "entry_flow_refused")
            entry = result["result"]
            await wait(lambda: entry.state == ConfigEntryState.LOADED)
            old = entry.runtime_data
            options = hass.config_entries.options
            result = await options.async_init(entry.entry_id)
            result = await options.async_configure(
                result["flow_id"], {"next_step_id": "city_lookup"}
            )
            result = await options.async_configure(
                result["flow_id"], {"city_lookup_enabled": False}
            )
            c.check(result["type"] == "create_entry", "options_flow_refused")
            await wait(
                lambda: (
                    entry.state == ConfigEntryState.LOADED
                    and bool(entry.options)
                    and entry.runtime_data is not old
                )
            )
            c.check(
                not any(item["url"] == UNRELATED for item in resources.async_items()),
                "resource_collision",
            )
            await resources.async_create_item({"url": UNRELATED, "res_type": "module"})
        entries = hass.config_entries.async_entries("homecircle")
        c.check(len(entries) == 1, "entry_count_refused")
        entry = entries[0]
        await wait(
            lambda: entry.state == ConfigEntryState.LOADED and bool(entry.options)
        )
        c.check(
            entry.options.get("city_lookup_enabled") is False
            and "life360" not in hass.config.components,
            "guest_account_or_city_scope_refused",
        )
        c.check(hass.config.skip_pip is False, "consumer_skip_pip_override_refused")
        c.check(
            entry.runtime_data.household.counts["home"] == 2
            and all(
                entry.runtime_data.config["members"][person]["trackers"] == [tracker]
                for person, tracker in zip(PEOPLE, TRACKERS, strict=True)
            ),
            "explicit_source_selection_refused",
        )
        inventory = json.loads(
            await hass.async_add_executor_job(
                lambda: c.read(control / "inventory.json", c.INVENTORY)
            )
        )["files"]
        target = Path(hass.config.config_dir) / "custom_components/homecircle"

        def installed_origins():
            c.check(
                Path(sys.modules["homeassistant"].__file__).resolve()
                == Path("/usr/src/homeassistant/homeassistant/__init__.py"),
                "guest_core_origin_refused",
            )
            c.installed(target, inventory)
            for name in ("__init__", "normalize", "city_lookup", "frontend"):
                module = sys.modules.get(
                    "custom_components.homecircle"
                    + ("." + name if name != "__init__" else "")
                )
                c.check(
                    module is not None
                    and Path(module.__file__).resolve()
                    == (target / (name + ".py")).resolve(),
                    "guest_loaded_origin_refused",
                )

        await hass.async_add_executor_job(installed_origins)
        selected = identity(entry)
        semantic_resources = sorted(
            (
                {"url": item["url"], "res_type": item["res_type"]}
                for item in resources.async_items()
            ),
            key=lambda item: item["url"],
        )
        c.check(
            any(item["url"] == UNRELATED for item in semantic_resources),
            "unrelated_resource_missing",
        )
        owned = [
            item
            for item in semantic_resources
            if item["url"].startswith("/homecircle_static/homecircle-card.js?")
        ]
        c.check(len(owned) == 1, "owned_resource_count_refused")
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://127.0.0.1:18123" + owned[0]["url"],
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                c.check(
                    response.status == 200
                    and c.sha(await response.read())
                    == inventory["frontend/homecircle-card.js"]["sha256"],
                    "served_frontend_refused",
                )
        snapshot = {
            "entry_settings_source_sha256": c.sha(
                json.dumps(selected, sort_keys=True, separators=(",", ":")).encode()
            ),
            "resource_url_type_sha256": c.sha(
                json.dumps(
                    semantic_resources, sort_keys=True, separators=(",", ":")
                ).encode()
            ),
        }
        if phase == "first":

            def saved_on_disk():
                try:
                    value = json.loads(
                        (control.parent / ".storage/core.config_entries").read_bytes()
                    )
                    candidate = next(
                        item
                        for item in value["data"]["entries"]
                        if item["entry_id"] == entry.entry_id
                    )
                    return all(
                        candidate.get(key) == item for key, item in selected.items()
                    )
                except (OSError, ValueError, KeyError, StopIteration):
                    return False

            await wait(lambda: hass.async_add_executor_job(saved_on_disk))
            await hass.async_add_executor_job(
                c.atomic, control / "saved-identity.json", snapshot
            )
        else:
            c.check(
                snapshot
                == json.loads(
                    await hass.async_add_executor_job(
                        c.read, control / "saved-identity.json"
                    )
                ),
                "restart_identity_changed",
            )
            old = entry.runtime_data
            c.check(
                await hass.config_entries.async_unload(entry.entry_id),
                "consumer_unload_refused",
            )
            c.check(not old.states, "consumer_unload_not_drained")
            c.check(
                await hass.config_entries.async_setup(entry.entry_id),
                "consumer_setup_refused",
            )
            await wait(lambda: entry.state == ConfigEntryState.LOADED)
            await hass.async_add_executor_job(installed_origins)
        await hass.async_add_executor_job(
            c.atomic,
            control / (phase + "-receipt.json"),
            {
                **c.base_receipt(values),
                "outcome": "passed",
                "phase": phase,
                "token_sha256": c.sha(runtime["token"].encode()),
                "normal_config_cache_mounted": True,
                "cached_distributions_origin_checked": len(versions),
                "nonempty_options": True,
                "explicit_people_and_trackers": 2,
                "exact_loaded_and_installed_files": 113,
                "served_frontend_sha256": inventory["frontend/homecircle-card.js"][
                    "sha256"
                ],
                "identity": snapshot,
                "resource_id_persistence_claimed": False,
                "unload_setup_checked": phase == "restart",
            },
        )

    async def run():
        try:
            async with asyncio.timeout(120):
                await exercise()
        except asyncio.CancelledError:
            raise
        except Exception as error:
            failure = await hass.async_add_executor_job(c.safe_failure, error, control)
            await hass.async_add_executor_job(
                c.atomic, control / "guest-failure.json", failure
            )

    async def started(_event=None):
        nonlocal task
        task = hass.async_create_background_task(run(), "consumer-entrypoint-witness")

    async def stopping(_event):
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stopping)
    if hass.is_running:
        await started()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, started)
    return True
