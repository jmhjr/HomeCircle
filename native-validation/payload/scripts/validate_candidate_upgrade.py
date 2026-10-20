"""Rehearse the immutable published beta19 -> candidate transition in real Core.

Only newly created synthetic configuration is used. The installed source is
always extracted from the supplied ZIP, including the old source on rollback.
Apple report transport is replaced with an empty response; authentication and
live provider compatibility are deliberately outside this rehearsal.
"""

from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
from datetime import timedelta
import hashlib
import io
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile

from validate_release import inspect_archive

ROOT = Path(__file__).resolve().parents[1]
PUBLISHED_SHA256 = "5f20d536e1b5378bef7f0b972bbfbc7ced911063aea16a0a8f56d2ffa1210cd2"
ACCOUNT = "a" * 32
MEMBER = "person.example_member"


def digest(value):
    if not isinstance(value, bytes):
        value = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(value).hexdigest()


def install_archive(archive_path, directory, *, expected_sha256=None):
    """Validate then replace only the owned disposable integration directory."""
    if expected_sha256 and digest(Path(archive_path).read_bytes()) != expected_sha256:
        raise ValueError("Baseline archive hash does not match its recorded source")
    payload = inspect_archive(Path(archive_path))
    target = Path(directory) / "custom_components/homecircle"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    for name, content in payload.items():
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    (Path(directory) / "validation-package.json").write_text(
        json.dumps(
            {name: digest(content) for name, content in payload.items()}, sort_keys=True
        )
    )
    return {
        "archive_sha256": digest(Path(archive_path).read_bytes()),
        "files": len(payload),
        "version": json.loads(payload["manifest.json"])["version"],
        "payload_sha256": digest(
            {name: digest(content) for name, content in payload.items()}
        ),
    }


def persistent_snapshot(directory, destination):
    """Copy one stopped synthetic instance's complete HA persistent state."""
    destination.mkdir()
    for name in (".storage", "image"):
        source = directory / name
        if source.exists():
            shutil.copytree(source, destination / name)


def persistent_restore(directory, source):
    """Restore stopped account state while retaining the latest recovery guard."""
    guard_relative = Path(".storage/homecircle_findmy/recovery_guard")
    current_guard = directory / guard_relative
    backup_guard = source / guard_relative
    if backup_guard.exists() and not current_guard.exists():
        raise ValueError("Latest recovery safeguard unavailable for safe restoration")
    with tempfile.TemporaryDirectory(
        prefix="retained-recovery-guard-", dir=directory.parent
    ) as temporary:
        retained = Path(temporary) / "guard"
        if current_guard.exists():
            shutil.copytree(current_guard, retained)
        for name in (".storage", "image"):
            target = directory / name
            if target.exists():
                shutil.rmtree(target)
            if (source / name).exists():
                shutil.copytree(source / name, target)
        if retained.exists():
            if current_guard.exists():
                shutil.rmtree(current_guard)
            current_guard.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(retained, current_guard)


def restrict_network():
    """Allow the Core HTTP acceptance read on loopback and reject other sockets."""
    original = socket.socket.connect
    original_ex = socket.socket.connect_ex
    original_resolve = socket.getaddrinfo
    denied = []

    def allowed(address):
        return not isinstance(address, tuple) or address[0] in ("127.0.0.1", "::1")

    def connect(instance, address):
        if not allowed(address):
            denied.append("external_connect")
            raise OSError("External network disabled in synthetic upgrade rehearsal")
        return original(instance, address)

    def connect_ex(instance, address):
        if not allowed(address):
            denied.append("external_connect")
            raise OSError("External network disabled in synthetic upgrade rehearsal")
        return original_ex(instance, address)

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex

    def resolve(host, *args, **kwargs):
        if host not in (None, "127.0.0.1", "::1", "localhost", b"127.0.0.1", b"::1"):
            denied.append("external_resolve")
            raise OSError("External DNS disabled in synthetic upgrade rehearsal")
        return original_resolve(host, *args, **kwargs)

    socket.getaddrinfo = resolve
    return denied


async def run_core(directory, phase, expected_path, output_path):
    """Run one fresh interpreter against the extracted installed package."""
    from homeassistant import bootstrap, loader
    from homeassistant.components.lovelace.const import LOVELACE_DATA
    from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
    from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers import entity_registry as er
    from homeassistant.helpers.storage import Store
    from homeassistant.util import dt as dt_util

    directory = Path(directory)
    sys.path.insert(0, str(directory))
    from custom_components.homecircle._vendor_findmy import FindMyAccessory
    from custom_components.homecircle.findmy_setup import sdk
    from custom_components.homecircle.findmy_vault import Vault, account_identity
    from custom_components.homecircle.findmy_provider import account_root
    import custom_components.homecircle as installed

    assert (
        Path(installed.__file__).resolve().parent
        == (directory / "custom_components/homecircle").resolve()
    )
    installed_root = Path(installed.__file__).resolve().parent
    expected_package = json.loads((directory / "validation-package.json").read_text())
    assert {
        path.relative_to(installed_root).as_posix(): digest(path.read_bytes())
        for path in installed_root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    } == expected_package
    account_type, anisette_type, _, _ = sdk()
    report_calls = []

    async def empty_reports(self, keys, *args, **kwargs):
        report_calls.append(len(keys))
        return {}

    # Keep real session restoration, accessory decoding, key derivation,
    # provider polling, encrypted writes, tracker entities and Core lifecycle.
    # Only the final report request boundary is synthetic.
    account_type.fetch_location = empty_reports
    denied = restrict_network()
    port_path = directory / "validation-port.json"
    if port_path.exists():
        port = json.loads(port_path.read_text())
    else:
        with socket.socket() as port_socket:
            port_socket.bind(("127.0.0.1", 0))
            port = port_socket.getsockname()[1]
        port_path.write_text(json.dumps(port))
    hass = HomeAssistant(str(directory))
    loader.async_setup(hass)
    config = {
        "homeassistant": {
            "name": "Synthetic upgrade household",
            ATTR_LATITUDE: 0.0,
            ATTR_LONGITUDE: 0.0,
            "elevation": 0,
            "unit_system": "metric",
            "time_zone": "UTC",
        },
        "http": {"server_host": "127.0.0.1", "server_port": port},
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
        "zone": [
            {"name": "Example Work", ATTR_LATITUDE: 2.0, ATTR_LONGITUDE: 2.0},
            {"name": "Example Residence", ATTR_LATITUDE: 1.0, ATTR_LONGITUDE: 1.0},
        ],
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
            {
                "source_type": "router",
                "in_zones": ["zone.home"],
            },
        )
        await hass.async_block_till_done()
        if phase == "published_install":
            manager = hass.config_entries.flow
            result = await manager.async_init(
                "homecircle", context={"source": SOURCE_USER}
            )
            result = await manager.async_configure(
                result["flow_id"],
                {
                    "people": [MEMBER, "person.example_second"],
                    "primary_home": "zone.home",
                    "places": ["zone.example_work"],
                },
            )
            for tracker in (
                "device_tracker.example_phone",
                "device_tracker.example_router",
            ):
                assert result["step_id"] == "assign_tracker", result
                result = await manager.async_configure(
                    result["flow_id"], {"tracker": tracker}
                )
                result = await manager.async_configure(
                    result["flow_id"], {"trackers": [tracker]}
                )
            result = await manager.async_configure(
                result["flow_id"], {"next_step_id": "confirm_save"}
            )
            entry = result["result"]
            await hass.async_block_till_done()
            # Real image-upload collection and its on-disk portrait are included.
            from aiohttp.web_request import FileField
            from PIL import Image

            image = io.BytesIO()
            Image.new("RGB", (8, 8), "navy").save(image, "PNG")
            image.seek(0)
            picture = await hass.data["image_upload"].async_create_item(
                {
                    "file": FileField("file", "synthetic.png", image, "image/png", {}),
                }
            )
            account = account_type(
                anisette_type(),
                uid="synthetic-upgrade-user",
                devid="synthetic-upgrade-device",
            )
            session = account.to_json()
            await account.close()
            session["account"].update(
                {"username": "owner@example.invalid", "password": None}
            )
            session["login"] = {
                "state": 3,
                "data": {
                    "dsid": "synthetic-upgrade-owner",
                    "mobileme_data": {
                        "tokens": {"searchPartyToken": "synthetic-offline-grant"}
                    },
                },
            }
            items = {}
            for index, identifier in enumerate(("keys", "luggage"), 1):
                accessory = FindMyAccessory(
                    master_key=bytes([index]) * 28,
                    skn=bytes([index + 2]) * 32,
                    sks=bytes([index + 4]) * 32,
                    paired_at=dt_util.utcnow() - timedelta(days=2),
                    identifier="synthetic-" + identifier,
                    name="Example " + identifier,
                    model="AirTag",
                )
                items[identifier] = {
                    "accessory": accessory.to_json(),
                    "report": {
                        ATTR_LATITUDE: 0.2 * index,
                        ATTR_LONGITUDE: 0.2 * index,
                        "gps_accuracy": 12.0,
                        "last_seen": dt_util.utcnow().isoformat(),
                        "battery_status": "full",
                    },
                }
            metadata = {
                "storage_id": ACCOUNT,
                "label": "Synthetic account",
                "account_identity": account_identity(session),
                "items": {
                    identifier: {
                        "name": "Example " + identifier,
                        "type": "airtag",
                        "unique_id": "homecircle_findmy_synthetic_" + identifier,
                    }
                    for identifier in items
                },
            }
            root = account_root(hass, metadata, True)
            await hass.async_add_executor_job(Vault(root).save_account, session, items)
            saved = deepcopy(dict(entry.data))
            saved["findmy_accounts"] = {ACCOUNT: metadata}
            saved["members"][MEMBER].update(
                {
                    "additional_residences": ["zone.example_residence"],
                    "display_name": "Example customized member",
                    "picture_id": picture["id"],
                }
            )
            hass.config_entries.async_update_entry(entry, options=saved)
            assert await hass.config_entries.async_reload(entry.entry_id)
            await hass.async_block_till_done()
            saved = deepcopy(entry.runtime_data.config)
            for identifier, item_metadata in saved["findmy_accounts"][ACCOUNT][
                "items"
            ].items():
                entity_id = er.async_get(hass).async_get_entity_id(
                    "device_tracker", "homecircle", item_metadata["unique_id"]
                )
                saved["members"][entity_id].update(
                    {
                        "display_name": "My " + identifier,
                        "show_on_map": identifier != "luggage",
                        "picture_id": picture["id"],
                    }
                )
            hass.config_entries.async_update_entry(entry, options=saved)
            assert await hass.config_entries.async_reload(entry.entry_id)
            await hass.async_block_till_done()
            entry.runtime_data.activity.append(
                MEMBER, "refresh", "checked", dt_util.utcnow()
            )
            await entry.runtime_data.activity.save()
            # Reserve a synthetic prior request without issuing a location request.
            await Store(
                hass, 1, f"homecircle.location_requests.{entry.entry_id}"
            ).async_save(
                {
                    "requests": {
                        "device_tracker.example_phone": [dt_util.utcnow().isoformat()]
                    },
                    "automatic": {},
                }
            )
            assert await hass.config_entries.async_reload(entry.entry_id)
            await hass.async_block_till_done()

        entries = hass.config_entries.async_entries("homecircle")
        assert len(entries) == 1
        entry = entries[0]
        assert entry.state == ConfigEntryState.LOADED
        runtime = entry.runtime_data
        provider = runtime.managed_trackers["findmy"]
        # Background polls are awaited separately; Core's foreground drain does
        # not by itself establish a finished provider poll.
        await asyncio.gather(*provider.tasks.values())
        await hass.async_block_till_done()
        assert provider.states[ACCOUNT] == "connected", provider.states
        assert len(provider.trackers[ACCOUNT]) == 2
        assert len(runtime.config["people"]) == 2
        assert len(runtime.config["items"]) == 2
        assert runtime.household.counts["home"] == 2
        assert not runtime.missing, runtime.missing
        assert "life360" not in hass.config.components
        assert report_calls
        vault = Vault(account_root(hass, entry.options["findmy_accounts"][ACCOUNT]))
        data = await hass.async_add_executor_job(vault.load)
        if phase == "candidate_ledger":
            from custom_components.homecircle.findmy_identity import prepare_state

            ledger = prepare_state(
                data["session"],
                data["items"],
                entry.options["findmy_accounts"][ACCOUNT]["items"],
            )
            # Exercise the candidate's real encrypted write format without a
            # settings edit that would legitimately change the saved options.
            from functools import partial

            await hass.async_add_executor_job(
                partial(
                    vault.save_account,
                    data["session"],
                    data["items"],
                    identity_state=ledger,
                )
            )
            data = await hass.async_add_executor_job(vault.load)

        resources = hass.data[LOVELACE_DATA].resources
        await resources.async_get_info()
        if phase == "published_install":
            await resources.async_create_item(
                {"url": "/local/synthetic_unrelated.js", "res_type": "module"}
            )
        resource_items = list(resources.async_items())
        owned = [
            item
            for item in resource_items
            if item["url"].startswith("/homecircle_static/")
        ]
        assert len(owned) == 1
        card = directory / "custom_components/homecircle/frontend/homecircle-card.js"
        from urllib.parse import urlsplit, parse_qs

        manifest = json.loads(
            (directory / "custom_components/homecircle/manifest.json").read_text()
        )
        query = parse_qs(urlsplit(owned[0]["url"]).query)
        assert query == {
            "v": [manifest["version"]],
            "asset": [digest(card.read_bytes())[:12]],
        }
        import aiohttp

        async with aiohttp.ClientSession() as client:
            async with client.get(
                f"http://127.0.0.1:{port}" + owned[0]["url"]
            ) as response:
                assert (
                    response.status == 200
                    and await response.read() == card.read_bytes()
                )
            async with client.get(
                f"http://127.0.0.1:{port}/api/image/serve/"
                + runtime.config["members"][MEMBER]["picture_id"]
                + "/512x512"
            ) as response:
                assert response.status == 200 and (await response.read())
        dashboards = hass.data[LOVELACE_DATA].dashboards
        dashboard = await dashboards["dashboard-homecircle"].async_load(False)
        registry = er.async_get(hass)
        registry_projection = {
            entity.entity_id: {
                "unique_id": entity.unique_id,
                "id": entity.id,
                "name": entity.name,
            }
            for entity in registry.entities.values()
            if entity.platform == "homecircle"
        }
        picture_id = runtime.config["members"][MEMBER]["picture_id"]
        state = {
            "entry_id": entry.entry_id,
            "data": digest(dict(entry.data)),
            "options": digest(dict(entry.options)),
            "runtime_config": digest(runtime.config),
            "registry": digest(registry_projection),
            "session": digest(data["session"]),
            "items": digest(data["items"]),
            "key": digest(vault.key_path.read_bytes()),
            "picture_id": picture_id,
            "picture": digest(
                (directory / "image" / picture_id / "original").read_bytes()
            ),
            "dashboard": digest(dashboard),
            "unrelated_resources": digest(
                [item for item in resource_items if item not in owned]
            ),
            "owned_resource_id": owned[0]["id"],
            "requests": digest(
                await Store(
                    hass, 1, f"homecircle.location_requests.{entry.entry_id}"
                ).async_load()
            ),
            "checked_event": [
                event
                for event in runtime.activity.events[MEMBER]
                if event["kind"] == "refresh" and event["value"] == "checked"
            ],
        }
        assert state["checked_event"]
        if phase == "published_install":
            expected_path.write_text(json.dumps(state, sort_keys=True, indent=2) + "\n")
        else:
            expected = json.loads(expected_path.read_text())
            assert state == expected, {
                key: "changed" for key in state if state[key] != expected.get(key)
            }
        result = {
            "phase": phase,
            "result": "passed",
            "loaded_version": manifest["version"],
            "selected_people": 2,
            "selected_items": 2,
            "accounts": 1,
            "installed_package": str(Path(installed.__file__).resolve().parent),
            "card_sha256": digest(card.read_bytes()),
            "installed_package_files": len(expected_package),
            "installed_package_sha256": digest(expected_package),
            "preserved_state_sha256": digest(state),
            "identity_ledger": "present" if data.get("identity_state") else "absent",
            "identity_ledger_sha256": digest(data["identity_state"])
            if data.get("identity_state")
            else None,
            "blocked_external_connections": len(denied),
            "synthetic_report_fetch_calls": len(report_calls),
        }
        output_path.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    finally:
        await hass.async_stop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--published-zip",
        type=Path,
        default=ROOT / "work/beta19-claude-review/workspace/published-homecircle.zip",
    )
    parser.add_argument("--baseline-sha256", default=PUBLISHED_SHA256)
    parser.add_argument("--baseline-label", default="canonical_published_beta19")
    parser.add_argument(
        "--candidate-zip", type=Path, default=ROOT / "release/homecircle.zip"
    )
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--core-phase", nargs=4, metavar=("DIRECTORY", "PHASE", "EXPECTED", "OUTPUT")
    )
    args = parser.parse_args()
    if args.core_phase:
        directory, phase, expected, output = args.core_phase
        asyncio.run(run_core(directory, phase, Path(expected), Path(output)))
        return
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        output_dir = args.output_dir.resolve()
    else:
        output_dir = ROOT / "work/stable-platform-upgrade-validation/upgrade"
        output_dir.mkdir(parents=True, exist_ok=True)
    phases = []
    with tempfile.TemporaryDirectory(
        prefix="synthetic-core-", dir=output_dir
    ) as temporary:
        directory = Path(temporary)
        expected = directory / "expected.json"

        def run(phase):
            output = output_dir / (phase + ".json")
            log = output_dir / (phase + ".log")
            with log.open("w") as stream:
                subprocess.run(
                    [
                        sys.executable,
                        str(Path(__file__).resolve()),
                        "--core-phase",
                        str(directory),
                        phase,
                        str(expected),
                        str(output),
                    ],
                    cwd=directory,
                    check=True,
                    timeout=180,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                )
            result = json.loads(output.read_text())
            phases.append(result)
            print(
                json.dumps(
                    {
                        "phase": phase,
                        "result": result["result"],
                        "identity_ledger": result["identity_ledger"],
                    }
                ),
                flush=True,
            )
            return result

        published = install_archive(
            args.published_zip, directory, expected_sha256=args.baseline_sha256
        )
        run("published_install")
        published_backup = directory / "published_backup"
        persistent_snapshot(directory, published_backup)
        candidate = install_archive(args.candidate_zip, directory)
        run("candidate_upgrade")
        run("candidate_restart")
        ledger = run("candidate_ledger")
        assert ledger["identity_ledger"] == "present"
        run("candidate_ledger_restart")
        candidate_backup = directory / "candidate_backup"
        persistent_snapshot(directory, candidate_backup)
        install_archive(
            args.published_zip, directory, expected_sha256=args.baseline_sha256
        )
        rollback = run("package_only_rollback")
        assert rollback["identity_ledger"] == "absent", (
            "Recheck the documented old-writer limitation"
        )
        install_archive(args.candidate_zip, directory)
        assert run("package_only_reupgrade")["identity_ledger"] == "absent"
        persistent_restore(directory, candidate_backup)
        restored = run("candidate_backup_restore")
        assert restored["identity_ledger_sha256"] == ledger["identity_ledger_sha256"]
        install_archive(
            args.published_zip, directory, expected_sha256=args.baseline_sha256
        )
        persistent_restore(directory, published_backup)
        run("published_backup_rollback")
        install_archive(args.candidate_zip, directory)
        run("final_candidate_upgrade")
    assert digest(args.published_zip.read_bytes()) == published["archive_sha256"]
    assert digest(args.candidate_zip.read_bytes()) == candidate["archive_sha256"]
    summary = {
        "result": "passed_with_package_only_rollback_limit",
        "baseline_label": args.baseline_label,
        "published": published,
        "candidate": candidate,
        "phases": phases,
        "disposable_configuration_removed": True,
        "core_version": __import__("importlib.metadata", fromlist=["version"]).version(
            "homeassistant"
        ),
        "coverage": "Real separate Core processes; ZIP source transition, saved people/items/options/places, session/accessory keys, entity IDs, history event, request reservation, portrait file and HTTP, dashboard, resource ID and served card.",
        "transport": "Real account/session restoration and polling; only AsyncAppleAccount.fetch_location is an empty synthetic response. External sockets denied. No Apple authentication or live provider calls.",
        "rollback_limit": "Published beta19 polling drops the candidate identity ledger. Matching stopped package + complete persistent-state backup restores its prior ledger/state. This is synthetic filesystem restoration, not HA backup add-on acceptance. Backup restoration cannot restore or prove Apple service allowance; no recovery guard attempts were seeded or reset in this rehearsal.",
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n"
    )
    print(
        "Published beta19 source upgrade/restart and coherent backup rollback passed; package-only rollback loses the candidate ledger. Synthetic configuration removed."
    )


if __name__ == "__main__":
    main()
