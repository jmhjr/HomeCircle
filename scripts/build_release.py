"""Build a deterministic integration-only ZIP after building the local frontend."""

import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TIMESTAMP = (2020, 1, 1, 0, 0, 0)
PYTHON_ROOTS = {"_vendor_findmy", "_findmy_runtime"}
RETIRED_LOCAL_MACOS_FILES = {
    "_vendor_findmy/plist.py",
    "_vendor_findmy/__main__.py",
}
EXCLUDED_PARTS = {
    "__pycache__",
    "tests",
    "test",
    "fixtures",
    "labs",
    "lab",
    "work",
    "state",
    "offline",
    "node_modules",
    "private",
    "secrets",
    "diagnostics",
}
FIXED_FILES = {
    "manifest.json",
    "strings.json",
    "frontend/homecircle-card.js",
    "frontend/LEAFLET-LICENSE.txt",
    "brand/icon.png",
}
REQUIRED_FILES = FIXED_FILES | {
    "LICENSE",
    "__init__.py",
    "config_flow.py",
    "frontend.py",
    "translations/en.json",
    "_vendor_findmy/__init__.py",
    "_vendor_findmy/LICENSE.md",
    "_vendor_findmy/README.md",
    "_vendor_findmy/cloudkit/proto/cloudkit.proto",
    "_vendor_findmy/cloudkit/proto/cuttlefish.proto",
    *(f"_vendor_findmy/keychain/roots/{name}.crt" for name in (101, 102, 103, 500)),
}
REQUIRED_RUNTIME_FILES = {
    "_findmy_runtime/__init__.py",
    "_findmy_runtime/provider.py",
    "_findmy_runtime/worker.py",
    "_findmy_runtime/PROVENANCE.md",
    "_findmy_runtime/emulator/LICENSE",
    *(
        f"_findmy_runtime/emulator/{name}.py"
        for name in ("__init__", "adi_run", "harness", "macho", "stubs")
    ),
}


class ReleaseError(ValueError):
    """Release validation failed before an archive or HA process was used."""


def allowed_member(name):
    """Explicit package roots/assets; generated state and lab trees never qualify."""
    if type(name) is not str or not name or "\\" in name or "\x00" in name:
        return False
    if name in RETIRED_LOCAL_MACOS_FILES:
        return False
    path = PurePosixPath(name)
    if (
        path.is_absolute()
        or path.as_posix() != name
        or any(
            part in {".", ".."}
            or part.startswith(".")
            or part.casefold() in EXCLUDED_PARTS
            for part in path.parts
        )
    ):
        return False
    if name in FIXED_FILES or name == "LICENSE":
        return True
    if len(path.parts) == 2 and path.parts[0] == "translations":
        return re.fullmatch(r"[A-Za-z0-9_-]+\.json", path.name) is not None
    python = re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*\.py", path.name) is not None
    if (
        python
        and not path.name.startswith("test_")
        and not path.name.endswith("_test.py")
    ):
        return len(path.parts) == 1 or path.parts[0] in PYTHON_ROOTS
    if path.parts[0] == "_vendor_findmy":
        return path.suffix in {".proto", ".crt"} or path.name in {
            "LICENSE.md",
            "README.md",
        }
    if path.parts[0] == "_findmy_runtime":
        return name in {
            "_findmy_runtime/PROVENANCE.md",
            "_findmy_runtime/LICENSE",
            "_findmy_runtime/LICENSE.md",
            "_findmy_runtime/emulator/LICENSE",
        }
    return False


def _read_file(path):
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ReleaseError("Release inputs must not contain symbolic links")
    if not path.is_file():
        raise ReleaseError("Required release input is missing")
    return path.read_bytes()


def collect_payload(source, license_path):
    """Collect only reviewed integration files; do not run frontend tooling."""
    source = Path(source)
    paths = [*source.glob("*.py"), *(source / "translations").glob("*.json")]
    for directory in sorted(PYTHON_ROOTS):
        root = source / directory
        if root.is_symlink():
            raise ReleaseError("Release inputs must not contain symbolic links")
        paths.extend(root.rglob("*"))
    paths.extend(source / name for name in FIXED_FILES)
    payload = {}
    for path in sorted(set(paths)):
        name = path.relative_to(source).as_posix()
        if path.is_symlink() and not any(
            part.startswith(".") or part.casefold() in EXCLUDED_PARTS
            for part in path.relative_to(source).parts
        ):
            raise ReleaseError("Release inputs must not contain symbolic links")
        if allowed_member(name) and not path.is_dir():
            payload[name] = _read_file(path)
    payload["LICENSE"] = _read_file(Path(license_path))
    validate_payload(payload)
    return payload


def _runtime_imports(name, tree):
    package = name.removesuffix(".py").split("/")[:-1]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [alias.name.split(".") for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[: len(package) - node.level + 1]
                modules = [base + (node.module.split(".") if node.module else [])]
            else:
                modules = [node.module.split(".")] if node.module else []
        else:
            continue
        for parts in modules:
            if parts[:2] == ["custom_components", "homecircle"]:
                parts = parts[2:]
            if parts and parts[0] == "_findmy_runtime":
                yield "/".join(parts)


def validate_payload(payload):
    if type(payload) is not dict or any(
        not allowed_member(name) or type(content) is not bytes
        for name, content in payload.items()
    ):
        raise ReleaseError("Release contains an unsupported member")
    if not REQUIRED_FILES <= payload.keys():
        raise ReleaseError("Release is missing a required integration asset")
    if (
        any(name.startswith("_findmy_runtime/") for name in payload)
        and not REQUIRED_RUNTIME_FILES <= payload.keys()
    ):
        raise ReleaseError("Release is missing required runtime files or provenance")
    manifest = json.loads(payload["manifest.json"])
    if manifest.get("domain") != "homecircle" or any(
        not manifest.get(key)
        for key in ("version", "codeowners", "documentation", "issue_tracker")
    ):
        raise ReleaseError("Release manifest metadata is incomplete")
    trees = {
        name: ast.parse(content, filename=name)
        for name, content in payload.items()
        if name.endswith(".py")
    }
    frontend_version = next(
        (
            ast.literal_eval(node.value)
            for node in trees["frontend.py"].body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "VERSION"
                for target in node.targets
            )
        ),
        None,
    )
    if frontend_version != manifest["version"]:
        raise ReleaseError("Frontend resource version must match manifest")
    for name, tree in trees.items():
        for module in _runtime_imports(name, tree):
            if module + ".py" not in payload and module + "/__init__.py" not in payload:
                raise ReleaseError("Release is missing an imported runtime module")
    return manifest


def write_archive(payload, output):
    """Write deterministic archive metadata and a complete content inventory."""
    manifest = validate_payload(payload)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    archive = output / "homecircle.zip"
    inventory = {}
    with zipfile.ZipFile(
        archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as zipped:
        for name, content in sorted(payload.items()):
            info = zipfile.ZipInfo(name, TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            zipped.writestr(info, content, compresslevel=9)
            inventory[name] = {
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
    report = {
        "version": manifest["version"],
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "files": inventory,
    }
    (output / "inventory.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    return archive, report


def main():
    subprocess.run(
        ["npm", "ci", "--prefix", str(ROOT / "frontend/homecircle-card")], check=True
    )
    subprocess.run(
        ["npm", "run", "build", "--prefix", str(ROOT / "frontend/homecircle-card")],
        check=True,
    )
    payload = collect_payload(ROOT / "custom_components/homecircle", ROOT / "LICENSE")
    archive, report = write_archive(payload, ROOT / "release")
    print(
        f"Built {archive.name}: {len(payload)} files; SHA256 {report['archive_sha256']}"
    )


if __name__ == "__main__":
    main()
