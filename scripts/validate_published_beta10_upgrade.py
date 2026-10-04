"""Rehearse upgrading a saved household from the published beta 10 ZIP.

Uses only fictional Home Assistant state in disposable Core processes. The
candidate archive must carry its own version so this checks the
actual package upgrade and frontend resource replacement.
"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
BETA10_HASH = "99c2478d2016aeaf212adc895b86f6dfde37e489d1861eea365f38be1aea4ab9"
BETA10_VERSION = "0.1.0-beta.10"
CANDIDATE_VERSION = "0.1.0-beta.11"


def install(archive_path: Path, target: Path, expected_version: str) -> None:
    if target.exists():
        shutil.rmtree(target)  # Only the disposable directory created below.
    target.mkdir(parents=True)
    with zipfile.ZipFile(archive_path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["version"] == expected_version
        for name in archive.namelist():
            path = Path(name)
            assert not path.is_absolute() and ".." not in path.parts
            content = archive.read(name)
            destination = target / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)


def phase(directory: Path, name: str, version: str) -> None:
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/validate_release.py"),
            str(directory),
            name,
            version,
        ],
        cwd=directory,
        check=True,
        timeout=120,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--beta10-zip", required=True, type=Path)
    parser.add_argument(
        "--candidate-zip", type=Path, default=ROOT / "release/homecircle.zip"
    )
    args = parser.parse_args()
    assert hashlib.sha256(args.beta10_zip.read_bytes()).hexdigest() == BETA10_HASH
    with tempfile.TemporaryDirectory(prefix="homecircle-beta10-upgrade-") as temp:
        directory = Path(temp)
        target = directory / "custom_components/homecircle"
        install(args.beta10_zip, target, BETA10_VERSION)
        phase(directory, "install", BETA10_VERSION)
        install(args.candidate_zip, target, CANDIDATE_VERSION)
        phase(directory, "upgrade", CANDIDATE_VERSION)
        phase(directory, "restart", CANDIDATE_VERSION)
    print("Published beta 10 upgrade and restart passed; disposable storage removed.")


if __name__ == "__main__":
    main()
