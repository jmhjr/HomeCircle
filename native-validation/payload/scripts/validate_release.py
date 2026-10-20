"""Validate the built ZIP in isolated real Core processes, without HACS or providers.

The earlier version is a version-only fixture, not a previously published release.
"""

import asyncio
import hashlib
import json
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

from validate_ha_restart import run_phase
from build_release import ReleaseError, TIMESTAMP, allowed_member, validate_payload

ROOT = Path(__file__).resolve().parents[1]
MAX_MEMBER_BYTES = 16 * 1024**2
MAX_ARCHIVE_BYTES = 64 * 1024**2


def inspect_archive(path, inventory_path=None):
    """Reject unsafe/incomplete packages before extraction or any HA startup."""
    payload = {}
    total = 0
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        names = [member.filename for member in members]
        if names != sorted(names) or len(names) != len(set(names)):
            raise ReleaseError("Release archive members must be unique and sorted")
        for member in members:
            mode = member.external_attr >> 16
            if (
                not allowed_member(member.filename)
                or member.is_dir()
                or stat.S_IFMT(mode) != stat.S_IFREG
                or stat.S_IMODE(mode) != 0o644
                or member.create_system != 3
                or member.date_time != TIMESTAMP
                or member.compress_type != zipfile.ZIP_DEFLATED
                or member.flag_bits & 1
                or member.extra
                or member.comment
                or not 0 <= member.file_size <= MAX_MEMBER_BYTES
            ):
                raise ReleaseError("Release archive contains an unsafe member")
            total += member.file_size
            if total > MAX_ARCHIVE_BYTES:
                raise ReleaseError("Release archive exceeds the size limit")
            payload[member.filename] = archive.read(member)
        if archive.comment:
            raise ReleaseError("Release archive contains unexpected metadata")
    manifest = validate_payload(payload)
    if inventory_path is not None:
        expected = {
            "version": manifest["version"],
            "archive_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            "files": {
                name: {
                    "bytes": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                }
                for name, content in payload.items()
            },
        }
        if json.loads(Path(inventory_path).read_text()) != expected:
            raise ReleaseError("Release inventory does not match the archive")
    return payload


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
    payload = inspect_archive(
        ROOT / "release/homecircle.zip", ROOT / "release/inventory.json"
    )
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
