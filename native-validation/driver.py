"""Exact-source, native Linux focused pytest checks; no upgrade/KVM claim."""
import argparse
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET
import zipfile

HERE = Path(__file__).resolve().parent
LIMIT = 64 * 1024**2
CORE = "2026.10.2"
CONSTRAINTS = "7baa9a8f39ddeb9c5bb60a1036f6d5e33f4b84267f151f53cc2b95ef031a21b5"
HELPER = "91bb0d92bfeef8021184275369d8923e8b951d2cb7b85a31bd34414101e3a513"
SELECTORS = ("tests/test_activity_projection.py", "tests/test_activity.py",
             "tests/test_tracker_providers.py", "tests/test_tracker_provider_startup_isolation.py")
REQUIRED = {"test_projected_item_observes_named_place_without_losing_saved_history",
    "test_projected_item_and_original_member_history_survive_next_restart",
    "test_changed_saved_selection_still_invalidates_prior_projected_history",
    "test_setup_projects_new_item_before_loading_and_observing_activity"}


class Refused(RuntimeError):
    """Only fixed labels are eligible for public diagnostics."""


def check(ok, code):
    if not ok:
        raise Refused(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fingerprint(raw):
    return {"bytes": len(raw), "sha256": sha(raw)}


def read(path, expected=None, maximum=LIMIT):
    check(path.is_file() and not path.is_symlink() and path.stat().st_size <= maximum,
          "input_type_refused")
    raw = path.read_bytes()
    check(expected is None or sha(raw) == expected, "input_hash_refused")
    return raw


def unique(pairs):
    result = {}
    for key, value in pairs:
        check(key not in result, "duplicate_json_key_refused")
        result[key] = value
    return result


def json_read(path, expected=None):
    return json.loads(read(path, expected), object_pairs_hook=unique)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.with_suffix(".tmp").open("w") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.with_suffix(".tmp").replace(path)


def configuration(payload, expected):
    check(re.fullmatch(r"[a-f0-9]{64}", expected) is not None, "final_config_pin_required")
    value = json_read(payload / "config.json", expected)
    check(set(value) == {"schema", "source_commit", "source_sha256", "source_inventory_sha256",
                        "driver_sha256", "package_sha256", "package_inventory_sha256"}
          and type(value["schema"]) is int and value["schema"] == 1, "config_schema_refused")
    check(re.fullmatch(r"[a-f0-9]{40}", value["source_commit"]) is not None,
          "final_source_commit_required")
    for key in set(value) - {"schema", "source_commit"}:
        check(re.fullmatch(r"[a-f0-9]{64}", value[key]) is not None, "final_input_pin_required")
    read(Path(__file__), value["driver_sha256"])
    read(HERE / "requirements_support.py", HELPER)
    return value


def safe_name(name):
    path = PurePosixPath(name)
    return (isinstance(name, str) and name == path.as_posix() and path.parts
        and not path.is_absolute() and not {".", "..", ".git"}.intersection(path.parts)
        and not any(char in name for char in "\\\0\n\r"))


def inputs(payload, config):
    inventory = json_read(payload / "source-inventory.json", config["source_inventory_sha256"])
    check(type(inventory) is dict and 300 <= len(inventory) <= 1024, "source_count_refused")
    for name, item in inventory.items():
        check(safe_name(name) and type(item) is dict and set(item) == {"bytes", "sha256"}
            and type(item["bytes"]) is int and 0 <= item["bytes"] <= LIMIT
            and re.fullmatch(r"[a-f0-9]{64}", item["sha256"]) is not None,
            "source_inventory_refused")
    raw = read(payload / "source.tgz", config["source_sha256"])
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        check(not archive.pax_headers, "source_archive_metadata_refused")
        total = 0
        for member in archive:
            check(len(files) < len(inventory) and member.isfile() and not member.pax_headers
                  and member.name in inventory and member.name not in files
                  and member.size == inventory[member.name]["bytes"], "source_archive_member_refused")
            total += member.size
            check(total <= LIMIT, "source_archive_size_refused")
            with archive.extractfile(member) as stream:
                content = stream.read(member.size + 1)
            check(fingerprint(content) == inventory[member.name], "source_archive_bytes_refused")
            files[member.name] = content
    check(set(files) == set(inventory) and all(name in files for name in (*SELECTORS,
        "tests/conftest.py", "pytest.ini", "custom_components/homecircle/__init__.py")),
        "source_archive_names_refused")
    package_raw = read(payload / "homecircle.zip", config["package_sha256"])
    package_inventory = json_read(payload / "inventory.json", config["package_inventory_sha256"])
    check(package_inventory.get("archive_sha256") == config["package_sha256"]
          and package_inventory.get("version") == "0.1.0-beta.20", "package_inventory_refused")
    body = {}
    with zipfile.ZipFile(io.BytesIO(package_raw)) as archive:
        check(len(archive.infolist()) == 113 and len(package_inventory["files"]) == 113,
              "package_count_refused")
        total = 0
        for member in archive.infolist():
            check(safe_name(member.filename) and not member.is_dir()
                and (member.external_attr >> 16) & 0o170000 != 0o120000
                and member.filename not in body and member.file_size <= LIMIT,
                "package_member_refused")
            total += member.file_size
            check(total <= LIMIT, "package_total_refused")
            content = archive.read(member)
            check(fingerprint(content) == package_inventory["files"].get(member.filename),
                  "package_bytes_refused")
            source_name = ("LICENSE" if member.filename == "LICENSE" else
                           "custom_components/homecircle/" + member.filename)
            if not member.filename.startswith("frontend/"):
                check(files.get(source_name) == content, "package_source_binding_refused")
            body[member.filename] = content
    return files, body


def git_verify(repository, config, files):
    # Exact public source blobs; no working-tree/index/ref mutation.
    for name, content in files.items():
        result = subprocess.run(["git", "show", config["source_commit"] + ":" + name],
            cwd=repository, capture_output=True, timeout=10, check=False)
        check(result.returncode == 0 and result.stdout == content, "canonical_git_blob_refused")
    return {"source_git_verified": True, "source_files": len(files)}


def extract(tree, files, body):
    check(not tree.exists(), "fresh_tree_required")
    tree.mkdir(mode=0o700, parents=True)
    for name, content in files.items():
        path = tree / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_bytes(content)
    for name, content in body.items():
        path = tree / "custom_components/homecircle" / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_bytes(content)


def unchanged(tree, files, body):
    for name, content in files.items():
        check(read(tree / name) == content, "source_changed")
    for name, content in body.items():
        check(read(tree / "custom_components/homecircle" / name) == content,
              "installed_product_changed")


def runtime():
    check(sys.platform == "linux" and platform.machine() == "x86_64"
        and platform.python_version() == "3.14.6"
        and importlib.metadata.version("homeassistant") == CORE, "native_runtime_refused")
    spec = importlib.util.find_spec("homeassistant")
    constraint = Path(spec.origin).with_name("package_constraints.txt")
    read(constraint, CONSTRAINTS)
    return constraint


def helper():
    spec = importlib.util.spec_from_file_location("focused_requirements", HERE / "requirements_support.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def common(config):
    return {"schema": 1, "scope": "native_current_core_focused_pytest_only",
        "source_commit": config["source_commit"], "source_sha256": config["source_sha256"],
        "package_sha256": config["package_sha256"], "core": CORE,
        "full_backend_suite_repeated": False, "upgrade_validated": False,
        "kvm_used": False, "owner_accounts_used": False, "production_configuration_used": False}


def prepare(args, config, files, body):
    constraint = runtime()
    extract(args.tree, files, body)
    helpers = helper()
    graph = helpers.core_component_requirements(body)
    manifest = json.loads(body["manifest.json"])
    wanted = sorted(set(manifest["requirements"] + graph["requirements"] +
        ["pytest-homeassistant-custom-component==0.13.373", "findmy==0.10.2"]))
    with (args.results / "dependencies-private.log").open("wb") as log:
        result = subprocess.run(["uv", "pip", "install", "--system", "--no-config",
            "--index-url", "https://pypi.org/simple", "--index-strategy", "unsafe-first-match",
            "--constraint", str(constraint), *wanted], cwd=args.tree,
            stdout=log, stderr=subprocess.STDOUT, timeout=660, check=False)
    check(result.returncode == 0, "dependency_preparation_refused")
    check(importlib.metadata.version("pytest-homeassistant-custom-component") == "0.13.373",
          "pytest_core_mismatch")
    runtime()
    versions = helpers.verify_declared_versions(graph["requirements"])
    unchanged(args.tree, files, body)
    write(args.results / "setup-summary.json", {**common(config), "outcome": "passed",
        "completed": True, "python": platform.python_version(), "machine": platform.machine(),
        "constraints_sha256": CONSTRAINTS, "pytest_homeassistant_custom_component": "0.13.373",
        "core_requirement_graph": graph, "startup_requirement_versions": versions,
        "source_files": len(files), "source_unchanged": True})


def accept(args, config, files, body):
    runtime()
    setup = json_read(args.results / "setup-summary.json")
    check(setup.get("outcome") == "passed" and setup.get("source_commit") == config["source_commit"],
          "setup_receipt_required")
    unchanged(args.tree, files, body)
    xml = args.results / "focused-private.xml"
    with (args.results / "focused-private.log").open("wb") as log:
        result = subprocess.run([sys.executable, "-B", "-m", "pytest", "--junitxml", str(xml),
            *SELECTORS], cwd=args.tree, stdout=log, stderr=subprocess.STDOUT, timeout=240, check=False)
    write(args.results / "focused-diagnostic.json", focused_diagnostic(xml, result.returncode))
    check(result.returncode == 0, "focused_pytest_refused")
    cases, projected = focused_result(xml)
    unchanged(args.tree, files, body)
    write(args.results / "candidate-summary.json", {**common(config), "outcome": "passed",
        "completed": True, "passed": len(cases), "failed": 0, "skipped": 0,
        "required_projection_tests": sorted(projected), "real_async_setup_entry_test_passed": True,
        "selected_modules": list(SELECTORS), "cases": cases, "source_unchanged": True})


def focused_result(xml):
    read(xml, maximum=4 * 1024**2)
    root = ET.parse(xml).getroot()
    check(not list(root.iter("failure")) and not list(root.iter("error"))
          and not list(root.iter("skipped")), "focused_failure_or_skip_refused")
    cases, seen, projected = [], set(), set()
    allowed = {name.removesuffix(".py").replace("/", ".") for name in SELECTORS}
    for case in root.iter("testcase"):
        classname, name = case.attrib.get("classname", ""), case.attrib.get("name", "")
        check(classname in allowed and re.fullmatch(r"test_[A-Za-z0-9_\[\].-]{1,180}", name)
            and (classname, name) not in seen, "focused_case_identity_refused")
        seen.add((classname, name))
        if classname == "tests.test_activity_projection":
            projected.add(name)
        cases.append({"class": classname, "function": name, "passed": True})
    check(projected == REQUIRED and len(cases) >= 32, "focused_required_cases_missing")
    return cases, projected


def focused_diagnostic(xml, exit_code):
    """Project finite identities/outcomes only; never XML text or parameters."""
    result = {"schema": 1, "scope": "unaccepted_focused_pytest_diagnostics",
        "acceptance_qualified": False, "pytest_exit": exit_code,
        "junit_available": False, "junit_parsed": False, "cases": [],
        "observed_cases": 0, "failed_cases": 0, "skipped_cases": 0,
        "unmapped_case_count": 0, "error_nodes": 0, "failure_nodes": 0}
    if not xml.is_file() or xml.is_symlink() or xml.stat().st_size > 4 * 1024**2:
        return result
    result["junit_available"] = True
    try:
        root = ET.parse(xml).getroot()
    except (OSError, ET.ParseError):
        return result
    cases = list(root.iter("testcase"))
    if len(cases) > 256:
        return result
    allowed = {name.removesuffix(".py").replace("/", ".") for name in SELECTORS}
    result["junit_parsed"] = True
    result["observed_cases"] = len(cases)
    result["error_nodes"] = min(256, len(list(root.iter("error"))))
    result["failure_nodes"] = min(256, len(list(root.iter("failure"))))
    for case in cases:
        failed = case.find("failure") is not None or case.find("error") is not None
        skipped = case.find("skipped") is not None
        result["failed_cases"] += int(failed)
        result["skipped_cases"] += int(skipped)
        classname = case.attrib.get("classname", "")
        function = case.attrib.get("name", "").split("[", 1)[0]
        if classname not in allowed or re.fullmatch(r"test_[A-Za-z0-9_]{1,180}", function) is None:
            result["unmapped_case_count"] += 1
            continue
        details=[]
        for node in [*case.findall('failure'),*case.findall('error')]:
            frames=[]
            for filename,line in re.findall(r'(tests/test_[A-Za-z0-9_]+[.]py):([0-9]{1,5})',node.text or ''):
                if filename in SELECTORS:
                    frame={'file':filename,'line':int(line)}
                    if frame not in frames:frames.append(frame)
            kind=node.attrib.get('type','')
            details.append({'type':kind if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]{0,100}',kind) else 'unclassified',
                            'selected_source_frames':frames[:20]})
        result["cases"].append({"class": classname, "function": function,
                                "failed": failed, "skipped": skipped,'failure_locations':details})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("verify-host", "prepare", "accept"))
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--config-sha", required=True)
    parser.add_argument("--repository", type=Path)
    parser.add_argument("--tree", type=Path)
    parser.add_argument("--results", type=Path, required=True)
    args = parser.parse_args()
    args.results.mkdir(mode=0o700, parents=True, exist_ok=True)
    config = None
    try:
        config = configuration(args.payload, args.config_sha)
        files, body = inputs(args.payload, config)
        if args.mode == "verify-host":
            check(args.repository is not None, "canonical_repository_required")
            write(args.results / "source-summary.json", {**common(config), "outcome": "passed",
                **git_verify(args.repository, config, files)})
        elif args.mode == "prepare":
            prepare(args, config, files, body)
        else:
            accept(args, config, files, body)
        return 0
    except Exception as error:
        code = str(error) if type(error) is Refused else "focused_operation_refused"
        write(args.results / "failure-summary.json", {"schema": 1, "outcome": "failed_or_incomplete",
            "scope": "native_current_core_focused_pytest_only", "stage": args.mode,
            "failure_code": code, "release_published": False})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
