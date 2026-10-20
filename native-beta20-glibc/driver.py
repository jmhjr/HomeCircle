"""Fixed-input, Linux-only Ubuntu/glibc qualification of published beta 20."""

import sys

if sys.platform != "linux":
    raise SystemExit("linux_required")

import argparse
import ast
import asyncio
import ctypes
import gzip
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import signal
import stat
import struct
import subprocess
import tarfile
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET
import zipfile


SOURCE_SHA = "261aeb3219071a44e1c6ca53f2f18e26624ae450a641d29be32450ee265d4818"
INVENTORY_SHA = "be693aef2f7a049cc4c0752179069664c86e444e24cc9fb01393d40f5d1288b1"
RELEASE_SHA = "fc0b365d9688459504f874af5c38393e24145d657f15f1def8ada9184f363285"
RELEASE_INVENTORY_SHA = "5e724f69ff20a711dd87b2a39ed96818781813bb6f1e7b3addedc6e048593d77"
CONSTRAINTS_SHA = "7baa9a8f39ddeb9c5bb60a1036f6d5e33f4b84267f151f53cc2b95ef031a21b5"
NATIVE_SHA = "4aa7e0763bef2e6a52d5a891167e551126d922d46a836d002696f89a4f2e7485"
LIFECYCLE_SHA = "11da124b436f30337cd4ea6b4b9b49b6b0dd4aba7dd3402d23d6df73d5ddcf6d"
STARTUP_SHA = "3714a31ea0f87b8c77086a4a28a3a4e93a396d3359dacd87ec6d2a0e7eeb3519"
OLD_SHA = "f0477a91e78181fe1f8d80ada176a1739e10a7502abe7ee6ee2240571280d1f5"
CORE = "2026.10.2"
VERSION = "0.1.0-beta.20"
PLUGIN = "0.13.373"
LIMIT = 64 * 1024**2
COUNT = 327
REQUIREMENTS = ["life360==7.2.0", "protobuf>=6.32.0,<8.0.0", "anisette==1.2.4",
                "unicorn==2.1.4", "srp==1.0.22", "beautifulsoup4==4.13.3"]
DEADLINE = 0.0
CURRENT_STAGE = "inputs"
LAST_PIP_STEP = None
STARTUP_FAILURE = None
PROBE_FAILURE = None
PROBE_PHASES = frozenset({
    "startup", "import", "dependency_copy", "dependency_resolution", "fixture",
    "normal_open", "limits", "normal_check", "normal_close", "cancel_open",
    "native_loop", "cancel_close", "cleanup", "complete",
})
PROBE_TYPES = frozenset({
    "ValueError", "ModuleNotFoundError", "ImportError", "AssertionError", "PermissionError",
    "FileNotFoundError", "OSError", "RuntimeError", "TypeError", "AttributeError", "KeyError",
    "NameError", "IdentityUnavailable", "ReleaseError", "TimeoutError", "MemoryError",
    "ProcessLookupError", "NotImplementedError", "OverflowError", "SyntaxError",
    "IndentationError", "RecursionError", "JSONDecodeError",
})
PROBE_MODULES = frozenset({
    "validate_ha_restart", "validate_release", "build_release", "platform_validate_candidate",
    "unicorn", "life360", "google", "google.protobuf", "anisette", "srp", "bs4", "packaging",
    "packaging.requirements", "packaging.specifiers",
})
PROBE_CODES = frozenset({
    "platform_candidate_hash_refused", "platform_core_constraints_refused", "platform_core_python_refused",
    "platform_dependency_version_refused", "platform_native_probe_refused", "platform_python_version_refused",
    "linux_lifecycle_cancellation_refused", "linux_lifecycle_candidate_changed",
    "linux_lifecycle_candidate_hash_refused", "linux_lifecycle_candidate_inventory_refused",
    "linux_lifecycle_check_refused", "linux_lifecycle_cleanup_refused",
    "linux_lifecycle_dependency_resolution_refused", "linux_lifecycle_dependency_version_refused",
    "linux_lifecycle_limits_refused", "linux_lifecycle_linux_required", "linux_lifecycle_native_loop_refused",
    "linux_lifecycle_open_refused", "linux_lifecycle_pipe_contract_refused", "linux_lifecycle_probe_refused",
    "linux_lifecycle_probe_timeout", "linux_lifecycle_provider_import_refused",
    "linux_lifecycle_spawn_contract_refused", "linux_lifecycle_worker_cleanup_refused",
})
SAFE_CHILD_CODES = frozenset({
    "startup_script_hash_refused", "startup_loaded_version_refused", "startup_arguments_required",
    "linux_runtime_refused", "ubuntu_release_refused", "active_glibc_version_refused",
    "musl_runtime_refused", "active_libc_mapping_refused", "native_elf_amd64_refused",
    "core_version_refused", "test_dependencies_refused", "core_origin_refused",
    "core_environment_origin_refused", "installed_core_constraints_refused", "unicorn_version_refused",
    "unicorn_loaded_library_refused", "tree_path_refused", "tree_symlink_refused",
    "tree_special_file_refused", "tree_bytes_changed", "input_path_refused", "input_hash_refused",
})


class Refused(RuntimeError):
    """Only fixed public labels may enter the sanitized failure receipt."""


class Terminated(BaseException):
    pass


def check(condition, label):
    if not condition:
        raise Refused(label)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fingerprint(raw):
    return {"bytes": len(raw), "sha256": sha(raw)}


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def read_pinned(path, expected, maximum=LIMIT):
    check(path.is_file() and not path.is_symlink() and path.stat().st_size <= maximum,
          "input_path_refused")
    raw = path.read_bytes()
    check(sha(raw) == expected, "input_hash_refused")
    return raw


def inputs(directory):
    """Check every raw USTAR record and byte before extraction or local imports."""
    raw = read_pinned(directory / "source.tgz", SOURCE_SHA)
    inventory = json.loads(read_pinned(directory / "source-inventory.json", INVENTORY_SHA, 2 * 1024**2))
    check(isinstance(inventory, dict) and len(inventory) == COUNT, "source_inventory_refused")
    for name, item in inventory.items():
        check(isinstance(name, str), "source_name_refused")
        path = PurePosixPath(name)
        check(name == path.as_posix() and path.parts and not path.is_absolute()
              and all(part not in {".", "..", ".git"} for part in path.parts)
              and not any(char in name for char in "\\\0\r\n"), "source_name_refused")
        check(isinstance(item, dict) and set(item) == {"bytes", "sha256"}
              and type(item["bytes"]) is int and 0 <= item["bytes"] <= LIMIT
              and isinstance(item["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", item["sha256"]),
              "source_inventory_entry_refused")
    maximum = LIMIT + COUNT * 1024 + 10240
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        tar = stream.read(maximum + 1)
    check(len(tar) <= maximum and len(tar) % 512 == 0, "source_tar_size_refused")
    offset, count = 0, 0
    while offset + 512 <= len(tar):
        header = tar[offset:offset + 512]
        if header == bytes(512):
            check(len(tar) - offset >= 1024 and not any(tar[offset:]), "source_tar_trailer_refused")
            break
        check(header[156:157] in {b"0", b"\0"} and header[257:263] == b"ustar\0",
              "source_tar_metadata_refused")
        encoded = header[124:136].strip(b"\0 ")
        check(bool(encoded) and all(byte in b"01234567" for byte in encoded), "source_tar_number_refused")
        size = int(encoded, 8)
        check(size <= LIMIT, "source_tar_member_size_refused")
        offset += 512 + ((size + 511) // 512) * 512
        check(offset <= len(tar), "source_tar_truncation_refused")
        count += 1
    else:
        raise Refused("source_tar_terminator_required")
    check(count == COUNT, "source_tar_count_refused")
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        members = archive.getmembers()
        check(not archive.pax_headers and len(members) == COUNT
              and sum(member.size for member in members) <= LIMIT, "source_members_refused")
        for member in members:
            check(member.isfile() and not member.issym() and not member.islnk() and not member.pax_headers
                  and member.name in inventory and member.name not in files, "source_member_refused")
            with archive.extractfile(member) as stream:
                content = stream.read()
            check(fingerprint(content) == inventory[member.name], "source_member_bytes_refused")
            files[member.name] = content
    check(set(files) == set(inventory), "source_names_refused")
    raw = read_pinned(directory / "published-homecircle.zip", RELEASE_SHA, 2 * 1024**2)
    release_inventory = json.loads(read_pinned(directory / "published-inventory.json",
                                              RELEASE_INVENTORY_SHA, 2 * 1024**2))
    payload = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = archive.infolist()
        names = [item.filename for item in members]
        check(len(names) == len(set(names)) == 112 and names == sorted(names) and not archive.comment,
              "release_archive_names_refused")
        for member in members:
            path = PurePosixPath(member.filename)
            mode = member.external_attr >> 16
            check(path.parts and not path.is_absolute() and ".." not in path.parts
                  and "\\" not in member.filename and not member.is_dir()
                  and stat.S_IFMT(mode) == stat.S_IFREG and stat.S_IMODE(mode) == 0o644
                  and member.create_system == 3 and member.date_time == (2020, 1, 1, 0, 0, 0)
                  and not member.extra and not member.comment and not member.flag_bits & 1
                  and member.compress_type == zipfile.ZIP_DEFLATED
                  and 0 <= member.file_size <= 16 * 1024**2, "release_archive_metadata_refused")
            payload[member.filename] = archive.read(member)
    check(release_inventory == {"version": VERSION, "archive_sha256": RELEASE_SHA,
                                "files": {name: fingerprint(content) for name, content in payload.items()}},
          "release_inventory_refused")
    manifest = json.loads(payload["manifest.json"])
    check(manifest.get("version") == VERSION and manifest.get("requirements") == REQUIREMENTS,
          "release_manifest_refused")
    for name, content in payload.items():
        if name.startswith("frontend/"):
            continue
        source_name = "LICENSE" if name == "LICENSE" else "custom_components/homecircle/" + name
        check(files.get(source_name) == content, "published_source_delta_refused")
    for name, pin in (("platform_validate_candidate.py", NATIVE_SHA),
                      ("platform_validate_linux_lifecycle.py", LIFECYCLE_SHA),
                      ("validate_ha_restart.py", STARTUP_SHA)):
        check(sha(files["scripts/" + name]) == pin, "validator_source_hash_refused")
    read_pinned(directory / "core-constraints.txt", CONSTRAINTS_SHA, 2 * 1024**2)
    return files, payload


def extract(files, tree):
    check(not tree.exists() and not tree.is_symlink(), "fresh_tree_required")
    tree.mkdir(mode=0o700, parents=True)
    for name, raw in files.items():
        target = tree / name
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        target.write_bytes(raw)


def tree_unchanged(files, tree):
    check(tree.is_dir() and not tree.is_symlink(), "tree_path_refused")
    actual = {}
    for path in tree.rglob("*"):
        check(not path.is_symlink(), "tree_symlink_refused")
        if path.is_file():
            actual[path.relative_to(tree).as_posix()] = path.read_bytes()
        else:
            check(path.is_dir(), "tree_special_file_refused")
    check(actual == files, "tree_bytes_changed")


def runtime_files(files, payload):
    result = {name: raw for name, raw in files.items()
              if not name.startswith("custom_components/homecircle/")}
    result.update({"custom_components/homecircle/" + name: raw for name, raw in payload.items()})
    return result


def run_owned(command, *, cwd, log, limit):
    remaining = min(limit, DEADLINE - time.monotonic())
    check(remaining > 0, "driver_deadline_expired")
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C.UTF-8",
           "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
           "PIP_CONFIG_FILE": "/dev/null", "PIP_DISABLE_PIP_VERSION_CHECK": "1"}
    with log.open("wb") as stream:
        child = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                 stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = child.wait(timeout=remaining)
        except BaseException:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait(timeout=10)
            raise
        try:
            os.killpg(child.pid, 0)
        except ProcessLookupError:
            pass
        else:
            os.killpg(child.pid, signal.SIGKILL)
            raise Refused("owned_child_descendants_not_reaped")
    check(log.stat().st_size <= 32 * 1024**2, "child_log_size_refused")
    return code


def elf(path):
    raw = path.read_bytes()
    check(len(raw) >= 64 and raw[:6] == b"\x7fELF\x02\x01"
          and struct.unpack_from("<H", raw, 18)[0] == 62, "native_elf_amd64_refused")
    return fingerprint(raw)


def environment(*, dependencies):
    check(platform.system() == "Linux" and platform.machine() == "x86_64"
          and platform.python_version() == "3.14.6", "linux_runtime_refused")
    release = {}
    for line in Path("/etc/os-release").read_text().splitlines():
        if "=" in line:
            name, value = line.split("=", 1)
            release[name] = value.strip('"')
    check(release.get("ID") == "ubuntu" and release.get("VERSION_ID") == "24.04", "ubuntu_release_refused")
    libc = ctypes.CDLL("libc.so.6")
    libc.gnu_get_libc_version.restype = ctypes.c_char_p
    version = libc.gnu_get_libc_version().decode("ascii")
    check(version == "2.39", "active_glibc_version_refused")
    mappings = []
    for line in Path("/proc/self/maps").read_text().splitlines():
        parts = line.split(maxsplit=5)
        if len(parts) == 6 and parts[5].startswith("/"):
            mappings.append(Path(parts[5]))
    check(not any("musl" in path.name for path in mappings), "musl_runtime_refused")
    libraries = {path.resolve() for path in mappings if path.name == "libc.so.6"}
    check(len(libraries) == 1, "active_libc_mapping_refused")
    result = {"system": "Linux", "machine": "x86_64", "os": "ubuntu", "os_version": "24.04",
              "python": "3.14.6", "active_libc": "glibc", "active_libc_version": version,
              "libc_elf": elf(next(iter(libraries))), "python_elf": elf(Path("/proc/self/exe").resolve())}
    if dependencies:
        check(importlib.metadata.version("homeassistant") == CORE, "core_version_refused")
        check(importlib.metadata.version("pytest-homeassistant-custom-component") == PLUGIN
              and importlib.metadata.version("findmy") == "0.10.2", "test_dependencies_refused")
        spec = importlib.util.find_spec("homeassistant")
        check(spec is not None and spec.origin is not None, "core_origin_refused")
        origin = Path(spec.origin).resolve()
        check(origin.is_relative_to(Path(sys.prefix).resolve()), "core_environment_origin_refused")
        check(sha(origin.with_name("package_constraints.txt").read_bytes()) == CONSTRAINTS_SHA,
              "installed_core_constraints_refused")
        import unicorn
        check(unicorn.__version__ == "2.1.4", "unicorn_version_refused")
        roots = Path(unicorn.__file__).resolve().parent
        native = {Path(line.split(maxsplit=5)[5]).resolve()
                  for line in Path("/proc/self/maps").read_text().splitlines()
                  if len(line.split(maxsplit=5)) == 6 and "/libunicorn.so" in line.split(maxsplit=5)[5]}
        check(len(native) == 1 and all(path.is_relative_to(roots) for path in native),
              "unicorn_loaded_library_refused")
        result.update({"core": CORE, "core_origin_in_active_venv": True,
                       "constraints_sha256": CONSTRAINTS_SHA, "pytest_plugin": PLUGIN,
                       "unicorn": "2.1.4", "unicorn_native_elf": elf(next(iter(native)))})
    return result


def closure(path):
    from packaging.requirements import Requirement
    from packaging.specifiers import SpecifierSet
    queue, found = list(REQUIREMENTS), {}
    while queue:
        requirement = Requirement(queue.pop())
        if requirement.marker and not requirement.marker.evaluate({"extra": ""}):
            continue
        package = importlib.metadata.distribution(requirement.name)
        check(requirement.specifier.contains(package.version, prereleases=True), "dependency_version_refused")
        python = package.metadata.get("Requires-Python")
        check(not python or SpecifierSet(python).contains(platform.python_version()), "dependency_python_refused")
        name = package.metadata["Name"].lower().replace("_", "-")
        if name not in found:
            found[name] = package.version
            queue.extend(package.requires or ())
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            requirement = Requirement(line)
            name = requirement.name.lower().replace("_", "-")
            check(name not in found or requirement.specifier.contains(found[name], prereleases=True),
                  "dependency_core_constraint_refused")
    check(len(found) == 24, "dependency_closure_count_refused")
    return dict(sorted(found.items()))


def pip_install(args, requirements, name, limit):
    global LAST_PIP_STEP
    check(name in {"dependencies", "core-components"}, "pip_step_refused")
    LAST_PIP_STEP = name
    command = [sys.executable, "-I", "-B", "-m", "pip", "--isolated", "install", "--no-input",
               "--no-cache-dir", "--disable-pip-version-check", "--index-url", "https://pypi.org/simple",
               "--constraint", str(args.payload / "core-constraints.txt"), *requirements]
    check(run_owned(command, cwd=args.runtime_tree, log=args.results / (name + "-private.log"), limit=limit) == 0,
          "dependency_install_refused")


def core_component_requirements(payload):
    spec = importlib.util.find_spec("homeassistant")
    check(spec is not None and spec.origin is not None, "core_origin_refused")
    core = Path(spec.origin).parent
    base = core / "components"
    # Bootstrap imports several optional components before setup. Read its
    # declared roots without importing bootstrap until their wheels are ready.
    from homeassistant.const import BASE_PLATFORMS
    module = ast.parse((core / "bootstrap.py").read_bytes())
    def domain_set(node):
        if isinstance(node, ast.Name) and node.id == "BASE_PLATFORMS":
            return set(BASE_PLATFORMS)
        if isinstance(node, ast.Set):
            result = set()
            for item in node.elts:
                if isinstance(item, ast.Starred):
                    result.update(domain_set(item.value))
                else:
                    check(isinstance(item, ast.Constant) and isinstance(item.value, str),
                          "bootstrap_domain_expression_refused")
                    result.add(item.value)
            return result
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub):
            return domain_set(node.left) - domain_set(node.right)
        raise Refused("bootstrap_domain_expression_refused")
    roots, preimports, seen = set(), set(), set()
    for node in module.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
                and target.id in {"CORE_INTEGRATIONS", "DEFAULT_INTEGRATIONS"} for target in node.targets):
            roots.update(domain_set(node.value))
            seen.update(target.id for target in node.targets if isinstance(target, ast.Name))
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module == "components":
            preimports.update(alias.name for alias in node.names)
    check({"CORE_INTEGRATIONS", "DEFAULT_INTEGRATIONS"} <= seen, "bootstrap_domain_roots_refused")
    queue = list(roots | set(json.loads(payload["manifest.json"])["dependencies"]) | {"http", "person", "zone"})
    found, requirements = set(), set()
    # Importing default_config does not set up all its optional dependencies.
    # Only preload these modules' own declared wheels; actual setup roots below
    # retain their full hard-dependency graph.
    for domain in preimports:
        check(re.fullmatch(r"[a-z][a-z0-9_]{0,79}", domain) is not None, "core_component_name_refused")
        path = base / domain / "manifest.json"
        check(path.is_file() and not path.is_symlink(), "core_component_manifest_refused")
        requirements.update(json.loads(path.read_bytes()).get("requirements", ()))
    while queue:
        domain = queue.pop()
        check(re.fullmatch(r"[a-z][a-z0-9_]{0,79}", domain) is not None, "core_component_name_refused")
        if domain in found:
            continue
        found.add(domain)
        check(len(found) <= 256, "core_component_count_refused")
        path = base / domain / "manifest.json"
        check(path.is_file() and not path.is_symlink(), "core_component_manifest_refused")
        manifest = json.loads(path.read_bytes())
        queue.extend(manifest.get("dependencies", ()))
        requirements.update(manifest.get("requirements", ()))
    return sorted(requirements)


def common(args, files, payload):
    tree_unchanged(files, args.tree)
    tree_unchanged(runtime_files(files, payload), args.runtime_tree)
    return {"schema": 1, "release_version": VERSION, "release_sha256": RELEASE_SHA,
            "release_inventory_sha256": RELEASE_INVENTORY_SHA, "release_files": 112,
            "source_sha256": SOURCE_SHA, "source_inventory_sha256": INVENTORY_SHA,
            "source_files": COUNT, "all_runtime_files_from_published_zip": True,
            "tagged_source_unchanged": True, "owner_accounts_used": False,
            "production_configuration_used": False}


def setup(args, files, payload):
    global CURRENT_STAGE
    CURRENT_STAGE = "runtime_environment"
    environment(dependencies=False)
    CURRENT_STAGE = "source_staging"
    extract(files, args.tree)
    extract(runtime_files(files, payload), args.runtime_tree)
    CURRENT_STAGE = "dependency_install"
    pip_install(args, ["homeassistant==" + CORE, *REQUIREMENTS,
                       "pytest-homeassistant-custom-component==" + PLUGIN, "findmy==0.10.2",
                       "home-assistant-frontend==20260930.4"], "dependencies", 1200)
    CURRENT_STAGE = "core_component_requirements"
    requirements = core_component_requirements(payload)
    if requirements:
        CURRENT_STAGE = "core_component_install"
        pip_install(args, requirements, "core-components", 240)
    CURRENT_STAGE = "pip_consistency"
    check(run_owned([sys.executable, "-I", "-B", "-m", "pip", "--isolated", "check"],
                    cwd=args.runtime_tree, log=args.results / "pip-check-private.log", limit=30) == 0,
          "installed_dependency_consistency_refused")
    CURRENT_STAGE = "setup_postconditions"
    result = common(args, files, payload)
    result.update({"outcome": "passed", "completed": True, "environment": environment(dependencies=True),
                   "installed_dependency_closure": closure(args.payload / "core-constraints.txt"),
                   "core_component_requirements": requirements})
    atomic_json(args.results / "setup-summary.json", result)


def private_json(path):
    check(path.is_file() and not path.is_symlink() and path.stat().st_size <= 2 * 1024**2,
          "child_receipt_refused")
    return json.loads(path.read_bytes())


def native_result(path):
    value = private_json(path)
    check(value.get("outcome") == "passed" and value.get("core_version") == CORE
          and value.get("package_sha256") == RELEASE_SHA and value.get("package_members") == 112
          and value.get("machine") == "x86_64" and value.get("system") == "Linux"
          and value.get("python_version") == "3.14.6", "native_identity_refused")
    check(value.get("core_constraints_sha256") == CONSTRAINTS_SHA
          and value.get("core_constraint_mismatches") == []
          and len(value.get("installed_dependency_closure", {})) == 24, "native_dependencies_refused")
    for key in ("mandatory_imports", "synthetic_native_worker", "production_hash_refusal",
                "worker_processes_reaped", "cleanup_ok"):
        check(value.get(key) is True, "native_contract_refused")
    for key in ("network_allowed", "apple_binary_executed", "owner_data_read"):
        check(value.get(key) is False, "native_scope_refused")
    check(value.get("account_requests") == 0 and value.get("unicorn_version") == "2.1.4", "native_scope_refused")
    return {"actual_zip_native_worker": True, "mandatory_imports": True, "production_hash_refusal": True,
            "workers_reaped": True, "closure": value["installed_dependency_closure"]}


def lifecycle_result(path):
    value = private_json(path)
    check(value.get("outcome") == "passed" and value.get("package_sha256") == RELEASE_SHA
          and value.get("package_members") == 112 and value.get("machine") == "x86_64"
          and value.get("system") == "Linux" and value.get("python_version") == "3.14.6",
          "lifecycle_identity_refused")
    for key in ("normal_open_check_close", "active_native_cancellation", "parent_only_dependency_used",
                "production_spawn_contract", "production_pipe_contract", "worker_processes_reaped", "cleanup_ok"):
        check(value.get(key) is True, "lifecycle_contract_refused")
    for key in ("candidate_files_modified", "network_allowed", "apple_binary_executed", "owner_data_read"):
        check(value.get(key) is False, "lifecycle_scope_refused")
    check(value.get("account_requests") == 0 and value.get("unicorn_version") == "2.1.4",
          "lifecycle_scope_refused")
    limits = value.get("child_limits", {})
    for key, expected in (("cpu_seconds", 90), ("core_bytes", 0), ("address_space_bytes", 3 * 1024**3)):
        check(limits.get(key, {}).get("soft") == limits.get(key, {}).get("hard") == expected,
              "lifecycle_limits_refused")
    workers = value.get("worker_children", [])
    check(len(workers) == 2 and all(item.get("proc_absent") is True and type(item.get("exit_code")) is int
                                  for item in workers), "lifecycle_reap_refused")
    return {"actual_provider_lifecycle": True, "active_native_cancellation": True,
            "parent_only_dependency_used": True, "worker_limits_verified": True, "workers_reaped": 2}


def backend_result(path, *, require_pass):
    check(path.is_file() and path.stat().st_size <= 16 * 1024**2, "backend_xml_refused")
    root = ET.fromstring(path.read_bytes())
    cases = root.findall(".//testcase")
    failed = [case for case in cases if case.find("error") is not None or case.find("failure") is not None]
    skipped = [case for case in cases if case.find("skipped") is not None]
    labels = []
    for case in failed[:3]:
        classname = case.attrib.get("classname", "")
        function = case.attrib.get("name", "").split("[", 1)[0]
        if classname.startswith("tests.") and re.fullmatch(r"[A-Za-z0-9_.]{1,180}", classname) \
                and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,119}", function):
            labels.append({"class": classname, "function": function})
    result = {"passed": len(cases) - len(failed) - len(skipped), "failed": len(failed),
              "skipped": len(skipped), "failure_labels": labels}
    if require_pass:
        suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
        check(bool(suites) and all(int(item.attrib.get("errors", "-1")) == 0
                                  and int(item.attrib.get("failures", "-1")) == 0 for item in suites),
              "backend_suite_errors_refused")
        check(result["passed"] == 1443 and not failed and len(skipped) == 1, "backend_counts_refused")
        check(skipped[0].attrib.get("name") == "test_retained_public_apple_dmg_fixed_ranges"
              and skipped[0].attrib.get("classname") == "tests.test_findmy_runtime_bootstrap", "backend_skip_refused")
    return result


def lifecycle_copy(args, files):
    original = files["scripts/platform_validate_linux_lifecycle.py"]
    before = ('CANDIDATE_SHA256 = "' + OLD_SHA + '"').encode()
    after = ('CANDIDATE_SHA256 = "' + RELEASE_SHA + '"').encode()
    check(original.count(before) == 1, "lifecycle_hash_adapter_count_refused")
    executed = original.replace(before, after)
    directory = args.results / "lifecycle-private"
    check(not directory.exists(), "fresh_lifecycle_adapter_required")
    directory.mkdir(mode=0o700)
    for name in ("platform_validate_candidate.py", "validate_release.py", "build_release.py", "validate_ha_restart.py"):
        (directory / name).write_bytes(files["scripts/" + name])
    path = directory / "platform_validate_linux_lifecycle.py"
    path.write_bytes(executed)
    return path, {"original_sha256": sha(original), "executed_sha256": sha(executed),
                  "only_candidate_hash_literal_changed": True, "substitutions": 1}


def probe_failure(log, stage, code):
    """Read a private traceback, exporting only finite public identifiers."""
    check(stage in {"native", "lifecycle"} and type(code) is int and -128 <= code <= 255,
          "probe_failure_arguments_refused")
    check(log.is_file() and not log.is_symlink() and log.stat().st_size <= 32 * 1024**2,
          "probe_failure_log_refused")
    with log.open("rb") as stream:
        stream.seek(max(0, log.stat().st_size - 65536))
        text = stream.read(65536).decode("utf-8", errors="replace")
    result = {"stage": stage, "exit_code": code}
    frames = []
    for line in text.splitlines():
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]{0,79}):(?: .*)?", line)
        if match and match[1] in PROBE_TYPES:
            result["failure_type"] = match[1]
        match = re.fullmatch(r"ModuleNotFoundError: No module named '([A-Za-z_][A-Za-z0-9_.]{0,179})'", line)
        if match and match[1] in PROBE_MODULES:
            result["missing_module"] = match[1]
        match = re.fullmatch(r"ValueError: ([a-z_]{1,100})", line)
        if match and match[1] in PROBE_CODES:
            result["failure_code"] = match[1]
        match = re.fullmatch(r"ValueError: linux_lifecycle_probe_refused:([a-z_]{1,40}):([A-Za-z_][A-Za-z0-9_]{0,79})", line)
        if match and match[1] in PROBE_PHASES and match[2] in PROBE_TYPES:
            result.update({"failure_code": "linux_lifecycle_probe_refused", "probe_phase": match[1],
                           "probe_failure_type": match[2]})
        match = re.fullmatch(r'  File "[^"\r\n]*/([A-Za-z_][A-Za-z0-9_]{0,79}\.py)", line ([0-9]{1,7}), in [^\r\n]+', line)
        if match and match[1] in {"platform_validate_linux_lifecycle.py", "platform_validate_candidate.py",
                                  "validate_release.py", "build_release.py", "validate_ha_restart.py"} \
                and 0 < int(match[2]) <= 1000000:
            frames.append({"script": match[1], "line": int(match[2])})
    result["public_frames"] = frames[-6:]
    return result


def startup_child(args):
    environment(dependencies=True)
    sys.path.insert(0, str(args.runtime_tree))
    path = args.runtime_tree / "scripts/validate_ha_restart.py"
    check(sha(path.read_bytes()) == STARTUP_SHA, "startup_script_hash_refused")
    spec = importlib.util.spec_from_file_location("exact_tag_startup", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    asyncio.run(module.run_phase(str(args.config), args.phase, VERSION))
    import custom_components.homecircle as integration
    from custom_components.homecircle import frontend
    check(Path(integration.__file__).resolve() ==
          (args.runtime_tree / "custom_components/homecircle/__init__.py").resolve()
          and frontend.VERSION == VERSION, "startup_loaded_version_refused")
    atomic_json(args.receipt, {"phase": args.phase, "outcome": "passed", "core": CORE,
                              "loaded_version": VERSION, "exact_published_source_imported": True,
                              "environment": environment(dependencies=True)})


def startup(args):
    global STARTUP_FAILURE
    records = []
    with tempfile.TemporaryDirectory(prefix="startup-private-", dir=args.results) as directory:
        config = Path(directory)
        config.chmod(0o700)
        components = config / "custom_components"
        components.mkdir(mode=0o700)
        (components / "homecircle").symlink_to(args.runtime_tree / "custom_components/homecircle", target_is_directory=True)
        for phase in ("create", "restart"):
            receipt = args.results / ("startup-" + phase + "-private.json")
            command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "startup-child",
                       "--payload", str(args.payload), "--tree", str(args.tree),
                       "--runtime-tree", str(args.runtime_tree), "--results", str(args.results),
                       "--config", str(config), "--phase", phase, "--receipt", str(receipt)]
            code = run_owned(command, cwd=args.runtime_tree,
                             log=args.results / ("startup-" + phase + "-private.log"), limit=90)
            if code != 0:
                if receipt.is_file():
                    STARTUP_FAILURE = {"phase": phase, **project_child_failure(private_json(receipt))}
                raise Refused("core_startup_child_refused")
            record = private_json(receipt)
            check(record.get("outcome") == "passed" and record.get("phase") == phase
                  and record.get("core") == CORE and record.get("loaded_version") == VERSION
                  and record.get("exact_published_source_imported") is True,
                  "core_startup_receipt_refused")
            check(record.get("environment") == environment(dependencies=True), "core_startup_runtime_refused")
            records.append({"phase": phase, "loaded_version": VERSION, "outcome": "passed"})
    check(not config.exists(), "startup_configuration_cleanup_refused")
    return {"separate_core_processes": records, "config_options_persistence": True,
            "reload_unload_setup": True, "served_published_bundle": True,
            "synthetic_configuration_removed": True, "script_sha256": STARTUP_SHA}


def acceptance(args, files, payload):
    global CURRENT_STAGE, PROBE_FAILURE
    CURRENT_STAGE = "acceptance_preconditions"
    result = common(args, files, payload)
    before = environment(dependencies=True)
    installed = closure(args.payload / "core-constraints.txt")
    setup_receipt = private_json(args.results / "setup-summary.json")
    check(setup_receipt.get("outcome") == "passed" and setup_receipt.get("completed") is True
          and setup_receipt.get("environment") == before
          and setup_receipt.get("installed_dependency_closure") == installed, "setup_receipt_refused")
    result.update({"outcome": "in_progress", "completed": False, "environment": before,
                   "installed_dependency_closure": installed, "current_stage": "native"})
    output = args.results / "glibc-summary.json"
    atomic_json(output, result)
    CURRENT_STAGE = "native"
    native = args.results / "native-private.json"
    code = run_owned([sys.executable, "-B", str(args.runtime_tree / "scripts/platform_validate_candidate.py"),
                     "--archive", str(args.payload / "published-homecircle.zip"), "--inventory",
                     str(args.payload / "published-inventory.json"), "--expected-sha256", RELEASE_SHA,
                     "--output", str(native)], cwd=args.runtime_tree, log=args.results / "native-private.log",
                    limit=180)
    if code != 0:
        PROBE_FAILURE = probe_failure(args.results / "native-private.log", "native", code)
        raise Refused("native_child_refused")
    result["native"] = native_result(native)
    check(result["native"]["closure"] == installed, "native_closure_changed")
    result["current_stage"] = "lifecycle"
    CURRENT_STAGE = "lifecycle"
    atomic_json(output, result)
    path, adaptation = lifecycle_copy(args, files)
    lifecycle = args.results / "lifecycle-private.json"
    code = run_owned([sys.executable, "-B", str(path), "--archive",
                     str(args.payload / "published-homecircle.zip"), "--inventory",
                     str(args.payload / "published-inventory.json"), "--output", str(lifecycle)],
                    cwd=args.runtime_tree, log=args.results / "lifecycle-private.log", limit=120)
    if code != 0:
        PROBE_FAILURE = probe_failure(args.results / "lifecycle-private.log", "lifecycle", code)
        raise Refused("lifecycle_child_refused")
    result["lifecycle"] = {**lifecycle_result(lifecycle), "validator_adaptation": adaptation}
    common(args, files, payload)
    result["current_stage"] = "core_startup"
    CURRENT_STAGE = "core_startup"
    atomic_json(output, result)
    result["core_startup"] = startup(args)
    common(args, files, payload)
    result["current_stage"] = "backend"
    CURRENT_STAGE = "backend"
    atomic_json(output, result)
    xml = args.results / "backend-private.xml"
    code = run_owned([sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider", "--junitxml", str(xml)],
                     cwd=args.runtime_tree, log=args.results / "backend-private.log", limit=900)
    result["backend"] = backend_result(xml, require_pass=False)
    atomic_json(output, result)
    check(code == 0, "backend_exit_refused")
    backend_result(xml, require_pass=True)
    CURRENT_STAGE = "acceptance_postconditions"
    common(args, files, payload)
    check(environment(dependencies=True) == before and closure(args.payload / "core-constraints.txt") == installed,
          "runtime_changed_after_acceptance")
    inputs(args.payload)
    result.update({"outcome": "passed", "completed": True, "current_stage": "complete",
                   "offline_container_boundary_required": True, "apple_binary_executed": False,
                   "account_requests": 0, "production_history_tested": False,
                   "upgrade_recovery_repeated": False, "hacs_delivery_repeated": False,
                   "managed_haos_tested": False})
    atomic_json(output, result)


def project_child_failure(value):
    """Keep only finite receipt fields; no child text, paths, or locals."""
    check(isinstance(value, dict), "startup_failure_receipt_refused")
    result = {}
    kind = value.get("failure_type")
    if isinstance(kind, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,79}", kind):
        result["failure_type"] = kind
    code = value.get("failure_code")
    if isinstance(code, str) and code in SAFE_CHILD_CODES:
        result["failure_code"] = code
    module = value.get("missing_module")
    if isinstance(module, str) and len(module) <= 180 \
            and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*", module):
        result["missing_module"] = module
    frames = []
    supplied_frames = value.get("public_frames", [])
    for frame in supplied_frames[-6:] if isinstance(supplied_frames, list) else []:
        if (isinstance(frame, dict) and frame.get("script") in {"driver.py", "validate_ha_restart.py"}
                and isinstance(frame.get("function"), str)
                and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,79}", frame["function"])
                and type(frame.get("line")) is int and 0 < frame["line"] <= 1000000):
            frames.append({key: frame[key] for key in ("script", "function", "line")})
    result["public_frames"] = frames
    return result


def main():
    global DEADLINE, CURRENT_STAGE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("setup", "acceptance", "startup-child"))
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--tree", type=Path, required=True)
    parser.add_argument("--runtime-tree", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--phase", choices=("create", "restart"))
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    args.results.mkdir(mode=0o700, parents=True, exist_ok=True)
    started = time.monotonic()
    DEADLINE = started + 1500
    CURRENT_STAGE = "inputs"
    def terminate(_signum, _frame):
        raise Terminated()
    for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(signum, terminate)
    try:
        files, payload = inputs(args.payload)
        CURRENT_STAGE = args.mode
        if args.mode == "setup":
            setup(args, files, payload)
        elif args.mode == "acceptance":
            acceptance(args, files, payload)
        else:
            check(args.config is not None and args.phase is not None and args.receipt is not None,
                  "startup_arguments_required")
            common(args, files, payload)
            CURRENT_STAGE = "core_startup_" + args.phase
            startup_child(args)
    except BaseException as error:
        failure = {"schema": 1, "outcome": "failed", "completed": False, "mode": args.mode,
                   "failure_stage": CURRENT_STAGE, "failure_type": type(error).__name__,
                   "elapsed_seconds": round(time.monotonic() - started, 3)}
        if isinstance(error, Refused):
            failure["failure_code"] = str(error)
        if LAST_PIP_STEP is not None:
            failure["last_pip_step"] = LAST_PIP_STEP
        if STARTUP_FAILURE is not None:
            failure["startup_child_failure"] = STARTUP_FAILURE
        if PROBE_FAILURE is not None:
            failure["probe_child_failure"] = PROBE_FAILURE
        if isinstance(error, ModuleNotFoundError) and isinstance(error.name, str) and len(error.name) <= 180 \
                and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*", error.name):
            failure["missing_module"] = error.name
        if isinstance(error, OSError) and type(error.errno) is int and 0 <= error.errno <= 4095:
            failure["os_errno"] = error.errno
        frames = []
        for frame, line in traceback.walk_tb(error.__traceback__):
            filename = frame.f_code.co_filename
            if (filename in {__file__, str(args.runtime_tree / "scripts/validate_ha_restart.py")}
                    and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,79}", frame.f_code.co_name)):
                frames.append({"script": Path(filename).name, "function": frame.f_code.co_name, "line": line})
        failure["public_frames"] = frames[-6:]
        if args.mode == "startup-child" and args.receipt is not None:
            atomic_json(args.receipt, project_child_failure(failure))
        else:
            atomic_json(args.results / "failure-summary.json", failure)
        print(json.dumps(failure), flush=True)
        return 1
    print(json.dumps({"outcome": "passed", "mode": args.mode, "release_sha256": RELEASE_SHA}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
