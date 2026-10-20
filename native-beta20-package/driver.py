"""Linux-only, fixed-input beta 20 packaging and offline Core regression checks."""

import sys

if sys.platform != "linux":
    raise SystemExit("linux_required")

import argparse
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
import subprocess
import tarfile
import time
import xml.etree.ElementTree as ET
import zipfile


SOURCE_SHA = "261aeb3219071a44e1c6ca53f2f18e26624ae450a641d29be32450ee265d4818"
INVENTORY_SHA = "be693aef2f7a049cc4c0752179069664c86e444e24cc9fb01393d40f5d1288b1"
FROZEN_SHA = "f0477a91e78181fe1f8d80ada176a1739e10a7502abe7ee6ee2240571280d1f5"
FROZEN_INVENTORY_SHA = "81a0b14cbdc28cc421a9690d6efac295a9e05300626ae30743f24b69197403a3"
BUILDER_SHA = "0c1ac7f979817bd5fc2cd4a4101571931488d6972bc6f181a26ac21edcf8c7d0"
VALIDATOR_SHA = "20c0466b4fa70a83c5f282bfcd07b0d2e6f5a3a1a09bf90072649441b2ad7f37"
CHECKER_SHA = "dd5f420d47781f31ce011212b1201f21d1c347a2e6feac8ca3882094c486ad51"
CONSTRAINTS_SHA = "962c9ccaf398e0b92b10ac9f765ac0f17e22238adc4e768deebc051ee8b60651"
CORE = "2026.9.4"
OLD = b"0.1.0-beta.19"
VERSION = "0.1.0-beta.20"
COUNT = 327
LIMIT = 64 * 1024**2
CHANGED = {"manifest.json", "frontend.py", "frontend/homecircle-card.js"}
FRONTEND = ("homecircle-card.js", "LEAFLET-LICENSE.txt")
REQUIREMENTS = ["life360==7.2.0", "protobuf>=6.32.0,<8.0.0", "anisette==1.2.4",
                "unicorn==2.1.4", "srp==1.0.22", "beautifulsoup4==4.13.3"]


class Refused(RuntimeError):
    """A fixed label, never a command, response, private path or exception text."""


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
    check(re.fullmatch(r"[0-9a-f]{64}", expected) is not None, "final_pins_required")
    check(path.is_file() and not path.is_symlink() and path.stat().st_size <= maximum, "input_path_refused")
    raw = path.read_bytes()
    check(sha(raw) == expected, "input_hash_refused")
    return raw


def changed_bytes(name, raw):
    if name in CHANGED:
        check(raw.count(OLD) == 1, "version_substitution_count_refused")
        return raw.replace(OLD, VERSION.encode())
    return raw


def inputs(directory):
    """Validate raw USTAR records, hashes and all bytes before source extraction."""
    raw = read_pinned(directory / "source.tgz", SOURCE_SHA)
    inventory = json.loads(read_pinned(directory / "source-inventory.json", INVENTORY_SHA, 2 * 1024**2))
    check(isinstance(inventory, dict) and len(inventory) == COUNT, "source_inventory_count_refused")
    for name, item in inventory.items():
        path = PurePosixPath(name)
        check(isinstance(name, str) and name == path.as_posix() and path.parts and not path.is_absolute()
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
    for name, expected in (("scripts/build_release.py", BUILDER_SHA),
                           ("scripts/validate_release.py", VALIDATOR_SHA),
                           ("scripts/check_public_files.py", CHECKER_SHA)):
        check(sha(files.get(name, b"")) == expected, "unchanged_release_tools_required")
    frozen = read_pinned(directory / "frozen-candidate.zip", FROZEN_SHA)
    frozen_inventory = json.loads(read_pinned(directory / "frozen-inventory.json", FROZEN_INVENTORY_SHA, 2 * 1024**2))
    payload = {}
    with zipfile.ZipFile(io.BytesIO(frozen)) as archive:
        members = archive.infolist()
        names = [member.filename for member in members]
        check(len(names) == len(set(names)) == 112 and names == sorted(names) and not archive.comment,
              "frozen_archive_names_refused")
        for member in members:
            path = PurePosixPath(member.filename)
            mode = member.external_attr >> 16
            check(path.parts and not path.is_absolute() and ".." not in path.parts and "\\" not in member.filename
                  and not member.is_dir() and stat.S_IFMT(mode) == stat.S_IFREG
                  and stat.S_IMODE(mode) == 0o644 and member.create_system == 3
                  and member.date_time == (2020, 1, 1, 0, 0, 0) and not member.extra and not member.comment
                  and not member.flag_bits & 1 and member.compress_type == zipfile.ZIP_DEFLATED
                  and 0 <= member.file_size <= 16 * 1024**2, "frozen_archive_metadata_refused")
            payload[member.filename] = archive.read(member)
    check(frozen_inventory == {"version": OLD.decode(), "archive_sha256": FROZEN_SHA,
                                "files": {name: fingerprint(content) for name, content in payload.items()}},
          "frozen_inventory_refused")
    for name, content in payload.items():
        if name.startswith("frontend/"):
            continue
        source_name = "LICENSE" if name == "LICENSE" else "custom_components/homecircle/" + name
        check(files.get(source_name) == changed_bytes(name, content), "version_only_source_delta_required")
    for name in ("frontend/homecircle-card/package.json", "frontend/homecircle-card/package-lock.json"):
        value = json.loads(files[name])
        check(value.get("version") == VERSION, "frontend_metadata_version_refused")
        if name.endswith("package-lock.json"):
            check(value.get("lockfileVersion") == 3 and value.get("packages", {}).get("", {}).get("version") == VERSION,
                  "frontend_lock_version_refused")
    hacs = json.loads(files["hacs.json"])
    check(hacs.get("zip_release") is True and hacs.get("filename") == "homecircle.zip"
          and hacs.get("homeassistant") == CORE and hacs.get("hide_default_branch") is True,
          "hacs_release_metadata_refused")
    return files, payload


def extract(files, tree):
    check(not tree.exists() and not tree.is_symlink(), "fresh_source_required")
    tree.mkdir(mode=0o700, parents=True)
    for name, raw in files.items():
        target = tree / name
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        target.write_bytes(raw)


def source_unchanged(files, tree):
    for name, raw in files.items():
        target = tree / name
        check(target.is_file() and not target.is_symlink() and target.read_bytes() == raw, "public_source_changed")


def frontend_bytes(tree, frozen):
    for name in FRONTEND:
        path = tree / "custom_components/homecircle/frontend" / name
        check(path.is_file() and not path.is_symlink()
              and path.read_bytes() == changed_bytes("frontend/" + name, frozen["frontend/" + name]),
              "frontend_version_only_bytes_required")


def run_owned(command, *, cwd, log, limit):
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C.UTF-8",
           "PYTHONDONTWRITEBYTECODE": "1", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"}
    with log.open("wb") as stream:
        child = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                 stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = child.wait(timeout=limit)
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


def privacy(files, tree, results):
    log = results / "privacy-private.log"
    check(run_owned(["git", "init", "--template=", "--initial-branch=public-check"], cwd=tree, log=log, limit=30) == 0,
          "private_git_init_refused")
    names = results / "public-names.zlist"
    names.write_bytes(b"\0".join(name.encode() for name in sorted(files)) + b"\0")
    check(run_owned(["git", "--literal-pathspecs", "add", "--force", "--pathspec-from-file=" + str(names),
                     "--pathspec-file-nul"], cwd=tree, log=log, limit=30) == 0, "private_git_add_refused")
    code = run_owned([sys.executable, "-I", "-B", str(tree / "scripts/check_public_files.py"), "--all"],
                     cwd=tree, log=log, limit=120)
    expected = f"Privacy guard checked {COUNT} files; no flagged patterns. Manual review still required.\n"
    check(code == 0 and log.read_text() == expected, "public_privacy_guard_refused")
    source_unchanged(files, tree)
    return {"checker_sha256": CHECKER_SHA, "files_checked": COUNT, "checker_exit": 0, "flagged_patterns": 0}


def frontend(args, files, frozen):
    source_unchanged(files, args.tree)
    frontend_bytes(args.tree, frozen)
    check(args.npm_log.is_file() and args.npm_log.stat().st_size <= 32 * 1024**2, "npm_log_refused")
    text = args.npm_log.read_text()
    for key, count in (("tests", 110), ("pass", 110), ("fail", 0), ("cancelled", 0), ("skipped", 0), ("todo", 0)):
        check(re.findall(r"^# " + key + r" ([0-9]+)\s*$", text, re.MULTILINE) == [str(count)],
              "frontend_test_counts_refused")
    safe = {"schema": 1, "outcome": "passed", "completed": True, "frontend_tests_passed": 110,
            "frontend_tests_failed": 0, "compiled_card_exact_version_substitution": True,
            "leaflet_exact_frozen_bytes": True, "source_sha256": SOURCE_SHA,
            "source_inventory_sha256": INVENTORY_SHA, "source_files": COUNT,
            "privacy": privacy(files, args.tree, args.results), "owner_accounts_used": False}
    atomic_json(args.results / "frontend-summary.json", safe)


def constraints():
    check(platform.machine() == "x86_64" and platform.python_version() == "3.14.6", "container_platform_refused")
    check(importlib.metadata.version("homeassistant") == CORE, "core_version_refused")
    spec = importlib.util.find_spec("homeassistant")
    check(spec is not None and spec.origin is not None
          and Path(spec.origin).resolve() == Path("/usr/src/homeassistant/homeassistant/__init__.py"), "core_origin_refused")
    path = Path(spec.origin).with_name("package_constraints.txt")
    check(sha(path.read_bytes()) == CONSTRAINTS_SHA, "core_constraints_refused")
    return path


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


def release_tools(tree):
    sys.path.insert(0, str(tree / "scripts"))
    import build_release
    import validate_release

    check(sha(Path(build_release.__file__).read_bytes()) == BUILDER_SHA
          and sha(Path(validate_release.__file__).read_bytes()) == VALIDATOR_SHA, "release_tools_origin_refused")
    return build_release, validate_release


def build(args, frozen):
    builder, validator = release_tools(args.tree)
    payload = builder.collect_payload(args.tree / "custom_components/homecircle", args.tree / "LICENSE")
    expected = {name: changed_bytes(name, raw) for name, raw in frozen.items()}
    check(payload == expected and len(payload) == 112, "release_payload_delta_refused")
    check(json.loads(payload["manifest.json"])["requirements"] == REQUIREMENTS, "manifest_requirements_refused")
    output = args.results / "release"
    path, inventory = builder.write_archive(payload, output)
    check(validator.inspect_archive(path, output / "inventory.json") == expected, "release_inspection_refused")
    second, _ = builder.write_archive(payload, args.results / "reproducibility")
    check(path.read_bytes() == second.read_bytes(), "release_reproducibility_refused")
    check(inventory["version"] == VERSION, "release_version_refused")
    return {"release_version": VERSION, "release_sha256": inventory["archive_sha256"],
            "release_inventory_sha256": sha((output / "inventory.json").read_bytes()),
            "release_bytes": path.stat().st_size, "release_files": 112,
            "frozen_candidate_sha256": FROZEN_SHA, "version_only_changed_members": sorted(CHANGED),
            "identical_members": 109, "reproducible_archive": True,
            "unchanged_builder_sha256": BUILDER_SHA, "unchanged_validator_sha256": VALIDATOR_SHA}


def setup(args, files, frozen):
    path = constraints()
    extract(files, args.tree)
    target = args.tree / "custom_components/homecircle/frontend"
    target.mkdir(mode=0o700, parents=True, exist_ok=True)
    for name in FRONTEND:
        raw = (args.payload / name).read_bytes()
        check(raw == changed_bytes("frontend/" + name, frozen["frontend/" + name]), "copied_frontend_refused")
        (target / name).write_bytes(raw)
    frontend_bytes(args.tree, frozen)
    result = build(args, frozen)
    command = ["uv", "pip", "install", "--system", "--no-config", "--index-url", "https://pypi.org/simple",
               "--index-strategy", "unsafe-first-match", "--constraint", str(path), *REQUIREMENTS,
               "pytest-homeassistant-custom-component==0.13.367", "findmy==0.10.2"]
    check(run_owned(command, cwd=args.tree, log=args.results / "dependency-private.log", limit=660) == 0,
          "dependency_install_refused")
    installed = closure(constraints())
    check(importlib.metadata.version("pytest-homeassistant-custom-component") == "0.13.367"
          and importlib.metadata.version("findmy") == "0.10.2", "test_dependency_version_refused")
    source_unchanged(files, args.tree)
    result.update({"schema": 1, "outcome": "passed", "completed": True, "core": CORE,
                   "python": platform.python_version(), "machine": platform.machine(),
                   "constraints_sha256": CONSTRAINTS_SHA, "installed_dependency_closure": installed,
                   "source_sha256": SOURCE_SHA, "source_inventory_sha256": INVENTORY_SHA,
                   "source_files": COUNT, "owner_accounts_used": False})
    atomic_json(args.results / "setup-summary.json", result)


def backend_result(path):
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
    return {"passed": len(cases) - len(failed) - len(skipped), "failed": len(failed), "skipped": len(skipped),
            "failure_labels": labels}, skipped


def acceptance(args, files, frozen):
    source_unchanged(files, args.tree)
    frontend_bytes(args.tree, frozen)
    result = build(args, frozen)
    installed = closure(constraints())
    xml = args.results / "backend-private.xml"
    code = run_owned([sys.executable, "-B", "-m", "pytest", "--junitxml", str(xml)],
                     cwd=args.tree, log=args.results / "backend-private.log", limit=900)
    backend, skipped = backend_result(xml)
    result.update({"schema": 1, "outcome": "failed", "completed": False, "backend": backend})
    atomic_json(args.results / "package-summary.json", result)
    check(code == 0 and backend["passed"] == 1443 and backend["failed"] == 0 and backend["skipped"] == 1,
          "backend_counts_refused")
    check(skipped[0].attrib.get("name") == "test_retained_public_apple_dmg_fixed_ranges"
          and skipped[0].attrib.get("classname") == "tests.test_findmy_runtime_bootstrap", "backend_skip_refused")
    source_unchanged(files, args.tree)
    frontend_bytes(args.tree, frozen)
    check(build(args, frozen)["release_sha256"] == result["release_sha256"], "release_changed_after_tests")
    result.update({"outcome": "passed", "completed": True, "core": CORE, "python": platform.python_version(),
                   "machine": platform.machine(), "constraints_sha256": CONSTRAINTS_SHA,
                   "installed_dependency_closure": installed, "source_sha256": SOURCE_SHA,
                   "source_inventory_sha256": INVENTORY_SHA, "source_files": COUNT,
                   "backend_network_disconnected_required": True, "owner_accounts_used": False,
                   "production_configuration_used": False, "hacs_delivery_tested": False,
                   "upgrade_recovery_repeated": False, "full_managed_core_lifecycle": False})
    atomic_json(args.results / "package-summary.json", result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "frontend", "setup", "acceptance"))
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--tree", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--npm-log", type=Path)
    args = parser.parse_args()
    args.results.mkdir(mode=0o700, parents=True, exist_ok=True)
    started = time.monotonic()
    stage = "inputs"
    def terminate(_signum, _frame):
        raise Terminated()
    for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(signum, terminate)
    try:
        check(platform.machine() == "x86_64", "native_amd64_required")
        files, frozen = inputs(args.payload)
        stage = args.mode
        if args.mode == "prepare":
            extract(files, args.tree)
        elif args.mode == "frontend":
            frontend(args, files, frozen)
        elif args.mode == "setup":
            setup(args, files, frozen)
        else:
            acceptance(args, files, frozen)
    except BaseException as error:
        failure = {"schema": 1, "outcome": "failed", "completed": False, "mode": args.mode,
                   "failure_stage": stage, "failure_type": type(error).__name__,
                   "elapsed_seconds": round(time.monotonic() - started, 3)}
        if isinstance(error, Refused):
            failure["failure_code"] = str(error)
        atomic_json(args.results / "failure-summary.json", failure)
        print(json.dumps(failure), flush=True)
        return 1
    print(json.dumps({"outcome": "passed", "mode": args.mode, "source_files": COUNT}), flush=True)
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except BaseException as failure:
        print(json.dumps({"outcome": "failed", "failure_type": type(failure).__name__}), file=sys.stderr)
        code = 1
    raise SystemExit(code)
