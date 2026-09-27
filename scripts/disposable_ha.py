"""Launch a disposable browser QA instance with a minimal HA Core worker.

Only synthetic sources and temporary storage; loopback HTTP by default. Ctrl-C stops HA
and removes its temporary config. HA-initiated restarts retain that config.
"""

import argparse
import ipaddress
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lan-address", help="Explicit private IPv4 address for physical display QA"
    )
    args = parser.parse_args()
    hosts = ["127.0.0.1"]
    if args.lan_address:
        address = ipaddress.ip_address(args.lan_address)
        if (
            address.version != 4
            or not address.is_private
            or address.is_loopback
            or address.is_unspecified
        ):
            parser.error("Use a specific private LAN IPv4 address")
        hosts.append(str(address))
    from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
    from homeassistant.components.http.config import (
        HTTP_STORAGE_SCHEMA,
        STORAGE_VERSION,
        STORAGE_MINOR_VERSION,
    )
    from homeassistant.util import dt as dt_util

    with tempfile.TemporaryDirectory(prefix="homecircle-browser-") as directory:
        config_dir = Path(directory)
        components = config_dir / "custom_components"
        components.mkdir()
        for domain, source in (
            ("homecircle", ROOT / "custom_components/homecircle"),
            ("example_sources", ROOT / "tests/ha_fixture"),
        ):
            (components / domain).symlink_to(source, target_is_directory=True)
        # JSON is valid YAML. Every coordinate here is a synthetic test constant.
        config = {
            "homeassistant": {
                "name": "HomeCircle Disposable QA",
                ATTR_LATITUDE: 0.0,
                ATTR_LONGITUDE: 0.0,
                "elevation": 0,
                "unit_system": "metric",
                "time_zone": "UTC",
            },
            "frontend": {},
            "example_sources": {},
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
                {
                    "name": "Example Residence",
                    ATTR_LATITUDE: 1.0,
                    ATTR_LONGITUDE: 0.0,
                    "radius": 100,
                },
                {
                    "name": "Example Work",
                    ATTR_LATITUDE: 2.0,
                    ATTR_LONGITUDE: 0.0,
                    "radius": 100,
                },
            ],
        }
        (config_dir / "configuration.yaml").write_text(json.dumps(config))
        # Pinned-HA test fixture only: stable explicit bindings prevent HA's
        # five-minute YAML trial from reverting to an all-interface listener.
        storage = config_dir / ".storage"
        storage.mkdir()
        stable_http = dict(
            HTTP_STORAGE_SCHEMA({"server_host": hosts, "server_port": 18124}),
            created_at=dt_util.utcnow().isoformat(),
            error=None,
            error_message=None,
        )
        (storage / "http").write_text(
            json.dumps(
                {
                    "version": STORAGE_VERSION,
                    "minor_version": STORAGE_MINOR_VERSION,
                    "key": "http",
                    "data": {
                        "stable": stable_http,
                        "pending": None,
                        "yaml_migration_done": True,
                    },
                }
            )
        )
        for host in hosts:
            print(f"Disposable HA: http://{host}:18124 (Ctrl-C cleans up)", flush=True)
        while True:
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(ROOT / "scripts/browser_ha_worker.py"),
                    directory,
                ],
                cwd=config_dir,
            )
            try:
                code = process.wait()
            except KeyboardInterrupt:
                process.send_signal(signal.SIGINT)
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                break
            print(f"Disposable HA process exited with status {code}", flush=True)
            if code not in (0, 100):
                raise SystemExit(code)
            # Standalone development Core may exit cleanly for a UI restart.
            # Keep its isolated config until the launcher is explicitly stopped.
            print("Restarting with the same disposable storage", flush=True)
    print("Disposable HA stopped; temporary configuration removed.")


if __name__ == "__main__":
    main()
