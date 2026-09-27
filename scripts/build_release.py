"""Build a deterministic integration-only ZIP after building the local frontend."""

import ast
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    subprocess.run(
        ["npm", "ci", "--prefix", str(ROOT / "frontend/homecircle-card")], check=True
    )
    subprocess.run(
        ["npm", "run", "build", "--prefix", str(ROOT / "frontend/homecircle-card")],
        check=True,
    )
    source = ROOT / "custom_components/homecircle"
    files = sorted(
        [
            *source.glob("*.py"),
            source / "manifest.json",
            source / "strings.json",
            *source.glob("translations/*.json"),
            source / "frontend/homecircle-card.js",
            source / "frontend/LEAFLET-LICENSE.txt",
            source / "brand/icon.png",
        ]
    )
    payload = {path.relative_to(source).as_posix(): path.read_bytes() for path in files}
    payload["LICENSE"] = (ROOT / "LICENSE").read_bytes()
    manifest = json.loads(payload["manifest.json"])
    assert manifest["domain"] == "homecircle"
    frontend_ast = ast.parse(payload["frontend.py"])
    frontend_version = next(
        ast.literal_eval(node.value)
        for node in frontend_ast.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "VERSION"
            for target in node.targets
        )
    )
    assert frontend_version == manifest["version"], (
        "Frontend resource version must match manifest"
    )
    assert (
        manifest["codeowners"]
        and manifest["documentation"]
        and manifest["issue_tracker"]
    )
    output = ROOT / "release"
    output.mkdir(exist_ok=True)
    archive = output / "homecircle.zip"
    inventory = {}
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        for name, content in sorted(payload.items()):
            info = zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zipped.writestr(info, content)
            inventory[name] = {
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
    report = {
        "version": manifest["version"],
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "files": inventory,
    }
    (output / "inventory.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"Built {archive.name}: {len(payload)} files; SHA256 {report['archive_sha256']}"
    )


if __name__ == "__main__":
    main()
