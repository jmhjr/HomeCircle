"""Owned Linux Core child: prepare the normal config-local library for offline restore."""
from __future__ import annotations

import asyncio
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import re
import signal
import stat
import subprocess
import sys

CORE = "2026.10.2"
CONSTRAINTS_SHA = "7baa9a8f39ddeb9c5bb60a1036f6d5e33f4b84267f151f53cc2b95ef031a21b5"
SITE = Path("/config/deps/lib/python3.14/site-packages")
REQUIREMENTS = ("life360==7.2.0", "protobuf>=6.32.0,<8.0.0", "anisette==1.2.4",
                "unicorn==2.1.4", "srp==1.0.22", "beautifulsoup4==4.13.3")


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def inventory(root):
    require(root.is_dir() and not root.is_symlink(), "qa_dependency_root")
    result, total = {}, 0
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), "qa_dependency_symlink")
        info = path.stat()
        require(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode), "qa_dependency_file_type")
        if path.is_dir():
            continue
        require(info.st_nlink == 1, "qa_dependency_hardlink")
        if "__pycache__" in path.parts:
            require(path.suffix == ".pyc", "qa_dependency_unrecognized_cache_file")
            continue
        require(path.stat().st_size <= 64 * 1024**2, "qa_dependency_member_size")
        raw = path.read_bytes()
        total += len(raw)
        require(total <= 96 * 1024**2 and len(result) < 8192, "qa_dependency_inventory_size")
        result[path.relative_to(root).as_posix()] = {"bytes": len(raw), "sha256": sha(raw)}
    require(bool(result), "qa_dependency_inventory_empty")
    return result, total


def closure():
    from packaging.requirements import Requirement
    from packaging.specifiers import SpecifierSet

    queue, found = list(REQUIREMENTS), {}
    while queue:
        requirement = Requirement(queue.pop())
        if requirement.marker and not requirement.marker.evaluate({"extra": ""}):
            continue
        package = metadata.distribution(requirement.name)
        require(Path(package.locate_file("")).resolve() == SITE, "qa_dependency_origin")
        require(requirement.specifier.contains(package.version, prereleases=True), "qa_dependency_version")
        python = package.metadata.get("Requires-Python")
        require(not python or SpecifierSet(python).contains(platform.python_version()), "qa_dependency_python")
        name = package.metadata["Name"].lower().replace("_", "-")
        require(re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,79}", name)
                and re.fullmatch(r"[A-Za-z0-9_.+-]{1,64}", package.version), "qa_dependency_metadata")
        if name not in found:
            found[name] = package.version
            queue.extend(package.requires or ())
    require(len(found) == 24, "qa_dependency_closure_count")
    return dict(sorted(found.items()))


def main():
    require(sys.platform == "linux" and platform.machine() == "x86_64"
            and platform.python_version() == "3.14.6", "qa_dependency_platform")
    from homeassistant.bootstrap import async_mount_local_lib_path
    from homeassistant.const import __version__
    from homeassistant.requirements import pip_kwargs
    from homeassistant.util.package import async_get_user_site, is_virtual_env
    from packaging.requirements import Requirement

    require(__version__ == CORE and not is_virtual_env(), "qa_dependency_core_runtime")
    constraints = Path(pip_kwargs("/config")["constraints"])
    require(constraints.is_file() and sha(constraints.read_bytes()) == CONSTRAINTS_SHA, "qa_dependency_constraints")
    computed_site = Path(asyncio.run(async_get_user_site("/config/deps")))
    require(computed_site == SITE and asyncio.run(async_mount_local_lib_path("/config")) == "/config/deps"
            and str(computed_site) in sys.path, "qa_normal_bootstrap_library")
    other_sites = [index for index, value in enumerate(sys.path)
                   if value.endswith("site-packages") and value != str(computed_site)]
    require(other_sites and all(sys.path.index(str(computed_site)) < index for index in other_sites),
            "qa_normal_bootstrap_path_order")
    root = Path("/config/deps")
    require(not root.is_symlink() and (not root.exists() or all(
        path.is_dir() and not path.is_symlink() for path in root.rglob("*"))), "qa_dependency_fresh_target")
    command = [sys.executable, "-m", "uv", "pip", "install", "--quiet", "--no-config",
               "--index-url", "https://pypi.org/simple", "--index-strategy", "unsafe-first-match",
               "--only-binary", ":all:", "--link-mode", "copy", "--constraint", str(constraints),
               "--target", str(SITE), *REQUIREMENTS]
    child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        require(child.wait(timeout=480) == 0, "qa_dependency_install")
    except BaseException:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=10)
        raise
    found = closure()
    for line in constraints.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            requirement = Requirement(line)
            name = requirement.name.lower().replace("_", "-")
            require(name not in found or requirement.specifier.contains(found[name], prereleases=True),
                    "qa_dependency_core_constraint")
    files, total = inventory(root)
    print(json.dumps({"schema": 1, "outcome": "passed", "core": CORE,
        "python": platform.python_version(), "constraints_sha256": CONSTRAINTS_SHA,
        "site": str(SITE), "normal_bootstrap_library": True, "virtual_env": False,
        "requirements": list(REQUIREMENTS), "closure": found, "closure_count": len(found),
        "inventory": files, "inventory_sha256": sha(canonical(files)),
        "inventory_files": len(files), "inventory_bytes": total,
        "inventory_scope": "dependency_regular_files_excluding_generated_bytecode"}, sort_keys=True))


if __name__ == "__main__":
    main()
