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
import re
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


def public_distribution_version(value):
    """The existing numeric-release bound excludes private/local version text."""
    if isinstance(value, str) and re.fullmatch(
        r"[0-9]{1,8}(?:\.[0-9]{1,8}){1,3}", value
    ):
        return value
    return "unavailable"


def distribution_failure(index, expected, distribution, cache, search_path):
    """Project only a fixed sorted pin index, numeric version and origin enums."""
    if type(index) is not int or not 0 <= index < 45:
        raise RuntimeError("distribution_diagnostic_index_refused")
    system = Path("/usr/local/lib/python3.14/site-packages")
    try:
        version = distribution.version if distribution is not None else None
    except Exception:
        version = None
    try:
        origin = Path(distribution.locate_file("")).resolve()
    except Exception:
        origin = None
    roots = [str(cache), str(system)]
    positions = [
        next(
            (offset for offset, value in enumerate(search_path) if value == root), None
        )
        for root in roots
    ]
    comparable = all(position is not None for position in positions)
    return {
        "sorted_package_index": index,
        "observed_version": public_distribution_version(version),
        "expected_version_matches": isinstance(version, str) and version == expected,
        "origin": "missing"
        if distribution is None
        else "cache"
        if origin == cache
        else "system"
        if origin == system
        else "other",
        "cache_precedes_system": comparable and positions[0] < positions[1],
        "system_precedes_cache": comparable and positions[1] < positions[0],
    }


EXERCISE_STAGES = frozenset(
    {
        "unclassified",
        "imports",
        "phase_request",
        "runtime",
        "resolved_dependencies",
        "synthetic_trackers",
        "person_sources",
        "resources",
        "flow_start",
        "flow_household",
        "flow_assign_tracker",
        "flow_member",
        "flow_confirm",
        "flow_create",
        "flow_loaded",
        "options_flow",
        "entry_state",
        "source_selection",
        "loaded_files",
        "resource_identity",
        "served_frontend",
        "disk_identity",
        "restart_identity",
        "unload_setup",
        "receipt",
    }
)
EXERCISE_EXCEPTION_TYPES = frozenset(
    {
        "AssertionError",
        "AttributeError",
        "FileNotFoundError",
        "ImportError",
        "IndexError",
        "KeyError",
        "ModuleNotFoundError",
        "OSError",
        "PermissionError",
        "RuntimeError",
        "TimeoutError",
        "TypeError",
        "ValueError",
        "OtherError",
    }
)


def exercise_diagnostic(error, stage):
    """Return only fixed stage and exact built-in error families; never values."""
    families = {
        AssertionError: "AssertionError",
        AttributeError: "AttributeError",
        FileNotFoundError: "FileNotFoundError",
        ImportError: "ImportError",
        IndexError: "IndexError",
        KeyError: "KeyError",
        ModuleNotFoundError: "ModuleNotFoundError",
        OSError: "OSError",
        PermissionError: "PermissionError",
        RuntimeError: "RuntimeError",
        TimeoutError: "TimeoutError",
        TypeError: "TypeError",
        ValueError: "ValueError",
    }
    return {
        "exercise_stage": stage
        if type(stage) is str and stage in EXERCISE_STAGES
        else "unclassified",
        "exception_type": families.get(type(error), "OtherError"),
    }


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
    distribution_check = {}
    exercise_stage = "unclassified"

    async def exercise():
        nonlocal exercise_stage
        exercise_stage = "imports"
        from homeassistant.components.lovelace.const import LOVELACE_DATA
        from homeassistant.config_entries import ConfigEntryState, SOURCE_USER
        from homeassistant.const import __version__ as core_version
        import aiohttp

        exercise_stage = "phase_request"
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
        exercise_stage = "runtime"
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

        def resolved_origins():
            cache = Path(runtime["cache_site"]).resolve()
            c.check(
                cache.is_relative_to(control.parent / "deps")
                and str(cache) in sys.path,
                "normal_config_cache_not_mounted",
            )
            system = Path("/usr/local/lib/python3.14/site-packages")
            counts = {"cache": 0, "system": 0}
            for index, (name, expected) in enumerate(sorted(versions.items())):
                try:
                    distribution = importlib.metadata.distribution(name)
                except importlib.metadata.PackageNotFoundError:
                    distribution_check.update(
                        distribution_failure(index, expected, None, cache, sys.path)
                    )
                    raise
                try:
                    c.check(
                        distribution.version == expected
                        and (origin := Path(distribution.locate_file("")).resolve())
                        in {cache, system},
                        "guest_cached_distribution_origin_refused",
                    )
                except c.Refused:
                    distribution_check.update(
                        distribution_failure(
                            index, expected, distribution, cache, sys.path
                        )
                    )
                    raise
                counts["cache" if origin == cache else "system"] += 1
            return counts

        exercise_stage = "resolved_dependencies"
        origin_counts = await hass.async_add_executor_job(resolved_origins)
        exercise_stage = "synthetic_trackers"
        for tracker, source_type in zip(TRACKERS, ("gps", "router"), strict=True):
            attrs = {"source_type": source_type, "in_zones": ["zone.home"]}
            if source_type == "gps":
                attrs.update(latitude=0.0, longitude=0.0, gps_accuracy=5)
            hass.states.async_set(tracker, "home", attrs)
        exercise_stage = "person_sources"
        await wait(
            lambda: all(
                hass.states.get(person) is not None
                and hass.states.get(person).attributes.get("source") == tracker
                for person, tracker in zip(PEOPLE, TRACKERS, strict=True)
            )
        )
        exercise_stage = "resources"
        resources = hass.data[LOVELACE_DATA].resources
        await resources.async_get_info()
        if phase == "first":
            c.check(
                not hass.config_entries.async_entries("homecircle"),
                "first_entry_collision",
            )
            exercise_stage = "flow_start"
            manager = hass.config_entries.flow
            result = await manager.async_init(
                "homecircle", context={"source": SOURCE_USER}
            )
            c.check(result["step_id"] == "household", "household_step_refused")
            exercise_stage = "flow_household"
            result = await manager.async_configure(
                result["flow_id"],
                {"people": list(PEOPLE), "primary_home": "zone.home", "places": []},
            )
            for tracker in TRACKERS:
                exercise_stage = "flow_assign_tracker"
                c.check(result["step_id"] == "assign_tracker", "assign_step_refused")
                result = await manager.async_configure(
                    result["flow_id"], {"tracker": tracker}
                )
                exercise_stage = "flow_member"
                c.check(result["step_id"] == "member", "member_step_refused")
                result = await manager.async_configure(
                    result["flow_id"],
                    {
                        "trackers": [tracker],
                        "additional_residences": [],
                        "kind": "person",
                    },
                )
            exercise_stage = "flow_confirm"
            c.check(result["step_id"] == "confirm", "confirm_step_refused")
            result = await manager.async_configure(
                result["flow_id"], {"next_step_id": "confirm_save"}
            )
            exercise_stage = "flow_create"
            c.check(result["type"] == "create_entry", "entry_flow_refused")
            entry = result["result"]
            exercise_stage = "flow_loaded"
            await wait(lambda: entry.state == ConfigEntryState.LOADED)
            exercise_stage = "options_flow"
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
            exercise_stage = "resources"
            c.check(
                not any(item["url"] == UNRELATED for item in resources.async_items()),
                "resource_collision",
            )
            await resources.async_create_item({"url": UNRELATED, "res_type": "module"})
        exercise_stage = "entry_state"
        entries = hass.config_entries.async_entries("homecircle")
        c.check(len(entries) == 1, "entry_count_refused")
        entry = entries[0]
        await wait(
            lambda: entry.state == ConfigEntryState.LOADED and bool(entry.options)
        )
        exercise_stage = "source_selection"
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
        exercise_stage = "loaded_files"
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
        exercise_stage = "resource_identity"
        selected = identity(entry)
        semantic_resources = sorted(
            (
                {"url": item["url"], "res_type": item["type"]}
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
        exercise_stage = "served_frontend"
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
            exercise_stage = "disk_identity"

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
            exercise_stage = "restart_identity"
            c.check(
                snapshot
                == json.loads(
                    await hass.async_add_executor_job(
                        c.read, control / "saved-identity.json"
                    )
                ),
                "restart_identity_changed",
            )
            exercise_stage = "unload_setup"
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
            exercise_stage = "unload_setup"
            await wait(lambda: entry.state == ConfigEntryState.LOADED)
            await hass.async_add_executor_job(installed_origins)
        exercise_stage = "receipt"
        await hass.async_add_executor_job(
            c.atomic,
            control / (phase + "-receipt.json"),
            {
                **c.base_receipt(values),
                "outcome": "passed",
                "phase": phase,
                "token_sha256": c.sha(runtime["token"].encode()),
                "normal_config_cache_mounted": True,
                "resolved_distributions_origin_checked": len(versions),
                "resolved_distributions_origin_counts": origin_counts,
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
            failure.update(exercise_diagnostic(error, exercise_stage))
            if distribution_check:
                failure["distribution_check"] = dict(distribution_check)
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
