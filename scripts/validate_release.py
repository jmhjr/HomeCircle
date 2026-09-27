"""Validate the built ZIP in isolated real Core processes, without HACS or providers.

The earlier version is a version-only fixture, not a previously published release.
"""

import asyncio
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

from validate_ha_restart import run_phase

ROOT = Path(__file__).resolve().parents[1]


async def check_removed(directory):
    import aiohttp
    from homeassistant import bootstrap, loader
    from homeassistant.core import HomeAssistant
    from homeassistant.components.lovelace.const import LOVELACE_DATA

    hass = HomeAssistant(directory)
    loader.async_setup(hass)
    assert await bootstrap.async_from_config_dict(
        {
            "frontend": {},
            "lovelace": {},
            "http": {"server_host": "127.0.0.1", "server_port": 18123},
        },
        hass,
    )
    try:
        await hass.async_start()
        assert not hass.config_entries.async_entries("homecircle")
        resources = hass.data[LOVELACE_DATA].resources
        await resources.async_get_info()
        assert any(
            item["url"] == "/local/example_unrelated.js"
            for item in resources.async_items()
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://127.0.0.1:18123/homecircle_static/homecircle-card.js"
            ) as response:
                assert response.status == 404
        print(
            "Post-removal restart passed; unrelated resource preserved; static bundle absent."
        )
    finally:
        await hass.async_stop()


def main():
    if len(sys.argv) > 1:
        directory, phase, version = sys.argv[1:]
        if phase == "removed":
            asyncio.run(check_removed(directory))
        else:
            asyncio.run(
                run_phase(
                    directory,
                    "create" if phase == "install" else phase,
                    version,
                    phase == "remove",
                )
            )
        return
    with zipfile.ZipFile(ROOT / "release/homecircle.zip") as archive:
        payload = {name: archive.read(name) for name in archive.namelist()}
    version = json.loads(payload["manifest.json"])["version"]
    previous = "0.0.3-dev0"
    with tempfile.TemporaryDirectory(prefix="homecircle-release-") as directory:
        target = Path(directory) / "custom_components/homecircle"

        def install(older=False):
            if target.exists():
                shutil.rmtree(target)  # Only this newly created disposable directory.
            target.mkdir(parents=True)
            for name, content in payload.items():
                assert not Path(name).is_absolute() and ".." not in Path(name).parts
                if older and name == "manifest.json":
                    data = json.loads(content)
                    data["version"] = previous
                    content = json.dumps(data).encode()
                if older and name == "frontend.py":
                    content = content.replace(version.encode(), previous.encode())
                path = target / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)

        def run(phase, expected):
            subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    directory,
                    phase,
                    expected,
                ],
                cwd=directory,
                check=True,
                timeout=120,
            )

        install(older=True)
        run("install", previous)
        install()
        run("upgrade", version)
        run("restart", version)
        run("remove", version)
        shutil.rmtree(target)
        run("removed", version)
    print("Package lifecycle passed; all disposable configuration removed.")


if __name__ == "__main__":
    main()
