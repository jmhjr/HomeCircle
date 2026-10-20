"""Linux-only setup and safe summary for the frozen native AMD64 rehearsal."""

import sys

if sys.platform != "linux":
    raise SystemExit("linux_required")

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import platform
import stat
import subprocess
import zipfile


QA = Path("/qa")
CORE = "2026.10.2"
CONSTRAINTS_SHA = "7baa9a8f39ddeb9c5bb60a1036f6d5e33f4b84267f151f53cc2b95ef031a21b5"
CANDIDATE = "f0477a91e78181fe1f8d80ada176a1739e10a7502abe7ee6ee2240571280d1f5"
DRIVER_SHA = "c910ef815d34eb4379bf3f0e1fd6dad31d95986a287b9e32263f9b87b60de373"
PINNED = {
    "published-homecircle.zip": "5f20d536e1b5378bef7f0b972bbfbc7ced911063aea16a0a8f56d2ffa1210cd2",
    "recorded-patch.zip": "0362a71b0d12e12bbe38c20192f130f505011500e9a1d31a3531547c5055d80a",
    "homecircle-candidate.zip": CANDIDATE,
    "homecircle-inventory.json": "81a0b14cbdc28cc421a9690d6efac295a9e05300626ae30743f24b69197403a3",
    "scripts/validate_candidate_upgrade.py": "c1c0b903d47e3fee90a4c377e493ee555e6df3bf5f75b2d3cbce394fb30e2bdf",
    "scripts/validate_recovery_restart.py": "acb71afbf58424939ab736e350bbef9b37f582af15c4eb508186ea3f54509e1f",
    "scripts/validate_release.py": "20c0466b4fa70a83c5f282bfcd07b0d2e6f5a3a1a09bf90072649441b2ad7f37",
    "scripts/validate_ha_restart.py": "3714a31ea0f87b8c77086a4a28a3a4e93a396d3359dacd87ec6d2a0e7eeb3519",
    "scripts/build_release.py": "0c1ac7f979817bd5fc2cd4a4101571931488d6972bc6f181a26ac21edcf8c7d0",
    "amd64-upgrade-recovery/run_validation.py": DRIVER_SHA,
}
REQUIREMENTS = [
    "life360==7.2.0", "protobuf>=6.32.0,<8.0.0", "anisette==1.2.4",
    "unicorn==2.1.4", "srp==1.0.22", "beautifulsoup4==4.13.3",
]


class Refused(RuntimeError):
    pass


def check(condition, label):
    if not condition:
        raise Refused(label)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path):
    check(path.stat().st_size <= 2 * 1024**2, "json_size_refused")
    return json.loads(path.read_text())


def write_json(path, value):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def check_inputs():
    for name, expected in PINNED.items():
        path = QA / name
        check(path.is_file() and not path.is_symlink(), "input_path_refused")
        check(digest(path.read_bytes()) == expected, "input_hash_refused")
    inventory = read_json(QA / "homecircle-inventory.json")
    files = inventory.get("files")
    check(inventory.get("archive_sha256") == CANDIDATE, "inventory_archive_refused")
    check(isinstance(files, dict) and len(files) == 112, "inventory_count_refused")
    for name in ("homecircle-candidate.zip", "published-homecircle.zip", "recorded-patch.zip"):
        with zipfile.ZipFile(QA / name) as archive:
            check(json.loads(archive.read("manifest.json"))["requirements"] == REQUIREMENTS,
                  "manifest_requirements_refused")
    with zipfile.ZipFile(QA / "homecircle-candidate.zip") as archive:
        names = archive.namelist()
        check(len(names) == len(set(names)) == 112 and set(names) == set(files), "zip_names_refused")
        for info in archive.infolist():
            name, raw = info.filename, archive.read(info)
            path = PurePosixPath(name)
            check(not path.is_absolute() and ".." not in path.parts and "\\" not in name,
                  "zip_path_refused")
            check(not info.is_dir() and not stat.S_ISLNK(info.external_attr >> 16), "zip_type_refused")
            check(files[name] == {"bytes": len(raw), "sha256": digest(raw)}, "zip_bytes_refused")
    return files


def check_tree(files):
    root = QA / "custom_components/homecircle"
    check(root.is_dir() and not root.is_symlink(), "source_root_refused")
    actual = {}
    for path in root.rglob("*"):
        check(not path.is_symlink(), "source_symlink_refused")
        if path.is_file() and "__pycache__" not in path.parts:
            raw = path.read_bytes()
            actual[path.relative_to(root).as_posix()] = {"bytes": len(raw), "sha256": digest(raw)}
    check(actual == files, "source_bytes_refused")


def core_constraints():
    check(platform.machine() == "x86_64", "amd64_required")
    check(importlib.metadata.version("homeassistant") == CORE, "core_version_refused")
    check(platform.python_version() == "3.14.6", "python_version_refused")
    spec = importlib.util.find_spec("homeassistant")
    check(spec is not None and spec.origin is not None, "core_origin_refused")
    origin = Path(spec.origin).resolve()
    check(origin == Path("/usr/src/homeassistant/homeassistant/__init__.py"), "core_origin_refused")
    path = origin.with_name("package_constraints.txt")
    check(digest(path.read_bytes()) == CONSTRAINTS_SHA, "core_constraints_refused")
    return path


def versions():
    return dict(sorted((item.metadata["Name"], item.version) for item in importlib.metadata.distributions()))


def closure(constraints):
    from packaging.requirements import Requirement
    from packaging.specifiers import SpecifierSet

    queue, installed = list(REQUIREMENTS), {}
    while queue:
        requirement = Requirement(queue.pop())
        if requirement.marker and not requirement.marker.evaluate({"extra": ""}):
            continue
        item = importlib.metadata.distribution(requirement.name)
        check(requirement.specifier.contains(item.version, prereleases=True), "dependency_version_refused")
        python = item.metadata.get("Requires-Python")
        check(not python or SpecifierSet(python).contains(platform.python_version()), "dependency_python_refused")
        name = item.metadata["Name"].lower().replace("_", "-")
        if name not in installed:
            installed[name] = item.version
            queue.extend(item.requires or ())
    for line in constraints.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            requirement = Requirement(line)
            name = requirement.name.lower().replace("_", "-")
            check(name not in installed or requirement.specifier.contains(installed[name], prereleases=True),
                  "dependency_core_constraint_refused")
    return dict(sorted(installed.items()))


def setup():
    files = check_inputs()  # Fixed hashes precede extraction or package imports.
    constraints = core_constraints()
    root = QA / "custom_components/homecircle"
    check(not root.exists(), "fresh_source_required")
    root.mkdir(parents=True, mode=0o700)
    with zipfile.ZipFile(QA / "homecircle-candidate.zip") as archive:
        for name in files:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(name))
    check_tree(files)
    before = versions()
    with (QA / "results/dependency-install.log").open("x") as log:
        subprocess.run(
            ["uv", "pip", "install", "--system", "--no-config", "--index-url", "https://pypi.org/simple",
             "--index-strategy", "unsafe-first-match", "--constraint", str(constraints), *REQUIREMENTS],
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=780,
        )
    core_constraints()
    installed = closure(constraints)
    check_inputs()
    check_tree(files)
    value = {"outcome": "passed", "completed": True, "core": CORE,
             "python": platform.python_version(), "machine": platform.machine(),
             "constraints_sha256": CONSTRAINTS_SHA, "candidate_sha256": CANDIDATE,
             "candidate_files": 112, "installed_dependency_closure": installed,
             "package_versions_before": before, "package_versions_after": versions(),
             "pytest_required": False, "owner_accounts_used": False}
    write_json(QA / "results/setup.json", value)
    print(json.dumps({key: value[key] for key in (
        "outcome", "completed", "core", "python", "machine", "constraints_sha256",
        "candidate_sha256", "candidate_files", "installed_dependency_closure", "pytest_required",
        "owner_accounts_used")}))


def summary():
    files = check_inputs()
    check_tree(files)
    constraints = core_constraints()
    installed = closure(constraints)
    path = QA / "results/native-full/driver.json"
    value = read_json(path) if path.is_file() else {}
    passed = value.get("outcome") == "passed" and value.get("completed") is True
    if passed:
        check(value.get("driver_sha256") == DRIVER_SHA, "driver_receipt_refused")
        check(value.get("candidate_sha256") == CANDIDATE and value.get("candidate_changed") is False,
              "candidate_receipt_refused")
        check(value.get("owner_accounts_used") is False and value.get("account_requests") == 0,
              "owner_receipt_refused")
        check(value.get("upgrade_phases") == value.get("recovery_processes") == 20,
              "count_receipt_refused")
        check(value.get("network_probes_blocked") == 40, "probe_receipt_refused")
        check(value.get("inputs_before") == value.get("inputs_after"), "post_inputs_refused")
        check([item.get("job") for item in value.get("jobs", [])] ==
              ["upgrade-published", "upgrade-recorded", "recovery"], "jobs_receipt_refused")
    stages = {"inputs", "metadata", "upgrade-published", "upgrade-recorded", "recovery", "complete"}
    failure_types = {"Refused", "TimeoutExpired", "Terminated", "KeyboardInterrupt", "CalledProcessError"}
    print(json.dumps({
        "schema": 1, "acceptance_pass": passed,
        "outcome": "passed" if passed else "failed_or_incomplete",
        "candidate_sha256": CANDIDATE, "candidate_files": 112,
        "candidate_inputs_match": True, "core": CORE, "machine": platform.machine(),
        "python": platform.python_version(), "constraints_sha256": CONSTRAINTS_SHA,
        "installed_dependency_closure": installed,
        "upgrade_phases": 20 if passed else None, "recovery_processes": 20 if passed else None,
        "network_probes_blocked": 40 if passed else None,
        "failure_stage": value.get("failure_stage") if value.get("failure_stage") in stages else None,
        "failure_type": value.get("failure_type") if value.get("failure_type") in failure_types else None,
        "owner_accounts_used": False, "production_configuration_used": False,
        "full_managed_core_lifecycle": False, "apple_authentication": False,
        "production_backup_acceptance": False,
    }))


def main():
    check(platform.machine() == "x86_64", "amd64_required")
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("setup", "summary"))
    args = parser.parse_args()
    (QA / "results").mkdir(mode=0o700, exist_ok=True)
    try:
        setup() if args.mode == "setup" else summary()
    except BaseException as error:
        value = {"outcome": "failed", "completed": False,
                 "failure_type": type(error).__name__}
        if isinstance(error, Refused):
            value["failure_code"] = str(error)
        print(json.dumps(value))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
