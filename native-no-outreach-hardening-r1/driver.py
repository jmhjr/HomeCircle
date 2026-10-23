"""Exact-source affected-provider checks; actual HA imports execute only on Linux."""
import argparse
import ast
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
SCOPE = "native_current_core_affected_provider_pytest_only"
VERSION_PATTERN = r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.]+)?"


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
    check(set(value) == {"schema", "frozen", "source_commit", "source_files", "source_sha256", "source_inventory_sha256",
                        "source_export_sha256", "driver_sha256", "package_sha256", "package_inventory_sha256",
                        "version", "release_files", "selected_modules", "expected_functions"}
          and type(value["schema"]) is int and value["schema"] == 1, "config_schema_refused")
    check(value["frozen"] is True, "frozen_control_required")
    check(type(value["source_commit"]) is str and re.fullmatch(r"[a-f0-9]{40}", value["source_commit"]) is not None,
          "final_source_commit_required")
    for key in ("source_sha256", "source_inventory_sha256", "source_export_sha256", "driver_sha256",
                "package_sha256", "package_inventory_sha256"):
        check(type(value[key]) is str and re.fullmatch(r"[a-f0-9]{64}", value[key]) is not None, "final_input_pin_required")
    check(type(value["source_files"]) is int and 300 <= value["source_files"] <= 1024,
          "final_source_count_required")
    check(type(value["version"]) is str and re.fullmatch(VERSION_PATTERN, value["version"])
          and type(value["release_files"]) is int and 100 <= value["release_files"] <= 256,
          "final_package_scope_required")
    modules = value["selected_modules"]
    check(type(modules) is list and 1 <= len(modules) <= 32
          and all(type(item) is str and re.fullmatch(r"tests/test_[a-z0-9_]+\.py", item) for item in modules)
          and len(modules) == len(set(modules)),
          "selected_modules_refused")
    expected = value["expected_functions"]
    check(type(expected) is list and 1 <= len(expected) <= 2048, "expected_functions_refused")
    seen = set()
    allowed = {name.removesuffix(".py").replace("/", ".") for name in modules}
    for item in expected:
        check(type(item) is dict and set(item) == {"class", "function"}
              and type(item["class"]) is str and type(item["function"]) is str
              and ".".join(item["class"].split(".")[:2]) in allowed
              and re.fullmatch(r"tests\.test_[a-z0-9_]+(?:\.[A-Za-z_][A-Za-z0-9_]*)?", item["class"])
              and re.fullmatch(r"test_[A-Za-z0-9_]{1,180}", item["function"]), "expected_function_refused")
        identity = (item["class"], item["function"])
        check(identity not in seen, "expected_function_duplicate_refused")
        seen.add(identity)
    read(Path(__file__), value["driver_sha256"])
    read(HERE / "requirements_support.py", HELPER)
    return value


def safe_name(name):
    if type(name) is not str:
        return False
    path = PurePosixPath(name)
    return (isinstance(name, str) and name == path.as_posix() and path.parts
        and not path.is_absolute() and not {".", "..", ".git"}.intersection(path.parts)
        and not any(char in name for char in "\\\0\n\r"))


def inputs(payload, config):
    check(payload.is_dir() and not payload.is_symlink()
          and {path.name for path in payload.iterdir()} == {
              "config.json", "source-inventory.json", "source.tgz", "source-export.json",
              "homecircle.zip", "inventory.json"}
          and all(path.is_file() and not path.is_symlink() for path in payload.iterdir()),
          "exact_payload_members_required")
    inventory = json_read(payload / "source-inventory.json", config["source_inventory_sha256"])
    check(type(inventory) is dict and len(inventory) == config["source_files"], "source_count_refused")
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
    selectors = config["selected_modules"]
    check(set(files) == set(inventory) and all(name in files for name in (*selectors,
        "tests/conftest.py", "pytest.ini", "custom_components/homecircle/__init__.py")),
        "source_archive_names_refused")
    export = json_read(payload / "source-export.json", config["source_export_sha256"])
    check(type(export) is dict and set(export) == {"schema", "source", "count", "files"}
          and type(export["schema"]) is int and export["schema"] == 1
          and export["source"] == config["source_commit"]
          and type(export["count"]) is int and export["count"] == len(files)
          and type(export["files"]) is dict
          and set(export["files"]) == set(files), "source_export_refused")
    for name, raw in files.items():
        check(export["files"][name] == {**fingerprint(raw), "git_blob": git_blob(raw)},
              "source_export_bytes_refused")
    check(expected_functions(files, selectors) == config["expected_functions"],
          "selected_source_functions_refused")
    package_raw = read(payload / "homecircle.zip", config["package_sha256"])
    package_inventory = json_read(payload / "inventory.json", config["package_inventory_sha256"])
    check(package_inventory.get("archive_sha256") == config["package_sha256"]
          and package_inventory.get("version") == config["version"], "package_inventory_refused")
    body = {}
    with zipfile.ZipFile(io.BytesIO(package_raw)) as archive:
        check(len(archive.infolist()) == config["release_files"]
              and len(package_inventory["files"]) == config["release_files"],
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
    manifest = json.loads(body["manifest.json"])
    check(manifest.get("domain") == "homecircle" and manifest.get("version") == config["version"]
          and type(manifest.get("requirements")) is list and 1 <= len(manifest["requirements"]) <= 64
          and all(type(item) is str and 1 <= len(item) <= 300 for item in manifest["requirements"]),
          "manifest_scope_refused")
    return files, body


def git_verify(repository, config, files):
    # Exact public source blobs; no working-tree/index/ref mutation.
    result = subprocess.run(["git", "ls-tree", "-rz", "--full-tree", config["source_commit"]],
        cwd=repository, capture_output=True, timeout=30, check=False)
    check(result.returncode == 0 and len(result.stdout) <= 2 * 1024**2, "canonical_git_tree_refused")
    actual = {}
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        metadata, encoded = record.split(b"\t", 1)
        mode, kind, oid = metadata.split()
        name = encoded.decode("utf-8")
        check(mode in {b"100644", b"100755"} and kind == b"blob" and safe_name(name)
              and name not in actual, "canonical_git_member_refused")
        actual[name] = oid.decode("ascii")
    check(set(actual) == set(files) and all(actual[name] == git_blob(raw) for name, raw in files.items()),
          "complete_canonical_git_blob_set_required")
    return {"source_git_verified": True, "complete_canonical_tree_verified": True, "source_files": len(files)}


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def expected_functions(files, selectors):
    """All statically declared pytest functions in the exact selected modules."""
    result = []
    for name in selectors:
        module = name.removesuffix(".py").replace("/", ".")
        tree = ast.parse(files[name], filename=name)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                result.append({"class": module, "function": node.name})
            elif isinstance(node, ast.ClassDef) and (node.name.startswith("Test") or any(
                (isinstance(base, ast.Attribute) and base.attr == "TestCase")
                or (isinstance(base, ast.Name) and base.id == "TestCase") for base in node.bases
            )):
                result.extend({"class": module + "." + node.name, "function": child.name}
                    for child in node.body if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and child.name.startswith("test_"))
    return sorted(result, key=lambda item: (item["class"], item["function"]))


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
    return {"schema": 1, "scope": SCOPE,
        "source_commit": config["source_commit"], "source_sha256": config["source_sha256"],
        "source_inventory_sha256": config["source_inventory_sha256"],
        "source_export_sha256": config["source_export_sha256"], "source_files": config["source_files"],
        "package_sha256": config["package_sha256"], "package_inventory_sha256": config["package_inventory_sha256"],
        "version": config["version"], "release_files": config["release_files"], "core": CORE,
        "full_backend_suite_repeated": False, "upgrade_validated": False,
        "full_managed_core_lifecycle": False, "hacs_delivery_tested": False,
        "kvm_used": False, "owner_accounts_used": False, "production_configuration_used": False}


def runtime_versions():
    versions = {name: importlib.metadata.version(name) for name in (
        "homeassistant", "pytest-homeassistant-custom-component", "life360", "protobuf",
        "anisette", "unicorn", "srp", "beautifulsoup4", "cryptography")}
    check(all(re.fullmatch(r"[A-Za-z0-9_.+!-]{1,100}", value) for value in versions.values()),
          "runtime_version_refused")
    return versions


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
        "runtime_versions": runtime_versions(),
        "source_files": len(files), "source_unchanged": True})


def accept(args, config, files, body):
    runtime()
    setup = json_read(args.results / "setup-summary.json")
    check(setup.get("outcome") == "passed" and setup.get("completed") is True
          and all(setup.get(key) == value for key, value in common(config).items()),
          "setup_receipt_required")
    helpers = helper()
    graph = helpers.core_component_requirements(body)
    versions = helpers.verify_declared_versions(graph["requirements"])
    check(setup.get("core_requirement_graph") == graph
          and setup.get("startup_requirement_versions") == versions
          and setup.get("runtime_versions") == runtime_versions(), "setup_dependency_drift_refused")
    unchanged(args.tree, files, body)
    xml = args.results / "focused-private.xml"
    collection = args.results / "collection-private.json"
    child = ("import importlib.util,sys;"
             "s=importlib.util.spec_from_file_location('affected_pytest_driver',sys.argv[1]);"
             "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
             "raise SystemExit(m.pytest_child(sys.argv[2],sys.argv[3:]))")
    with (args.results / "focused-private.log").open("wb") as log:
        result = subprocess.run([sys.executable, "-B", "-c", child, str(Path(__file__)),
            str(collection), "--junitxml", str(xml), *config["selected_modules"]],
            cwd=args.tree, stdout=log, stderr=subprocess.STDOUT, timeout=600, check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PIP_NO_INDEX": "1", "UV_OFFLINE": "1"})
    write(args.results / "focused-diagnostic.json", focused_diagnostic(xml, result.returncode, config))
    check(result.returncode == 0, "focused_pytest_refused")
    cases, base_functions = focused_result(xml, collection, config)
    unchanged(args.tree, files, body)
    write(args.results / "candidate-summary.json", {**common(config), "outcome": "passed",
        "completed": True, "passed": len(cases), "failed": 0, "skipped": 0,
        "collected_cases_match_junit": True, "selected_base_functions": base_functions,
        "selected_base_function_count": len(base_functions), "selected_modules": config["selected_modules"],
        "runtime_versions": runtime_versions(), "core_requirement_graph": graph,
        "startup_requirement_versions": versions, "source_unchanged": True})


def pytest_child(collection, arguments):
    """Only this offline Linux subprocess imports pytest and actual HA fixtures."""
    runtime()
    import pytest

    class CollectionProbe:
        deselected = 0

        def pytest_deselected(self, items):
            self.deselected += len(items)

        def pytest_collection_finish(self, session):
            nodes = []
            for item in session.items:
                parts = item.nodeid.split("::")
                module = parts[0].removesuffix(".py").replace("/", ".")
                nodes.append({"class": ".".join([module, *parts[1:-1]]), "name": parts[-1]})
            write(Path(collection), {"schema": 1, "cases": nodes, "deselected": self.deselected})

    return pytest.main(arguments, plugins=[CollectionProbe()])


def collection_identities(path, config):
    value = json_read(path)
    check(type(value) is dict and set(value) == {"schema", "cases", "deselected"} and value["schema"] == 1
          and type(value["deselected"]) is int and value["deselected"] == 0
          and type(value["cases"]) is list and 1 <= len(value["cases"]) <= 4096,
          "focused_collection_refused")
    expected = {(item["class"], item["function"]) for item in config["expected_functions"]}
    identities, functions = set(), set()
    for item in value["cases"]:
        check(type(item) is dict and set(item) == {"class", "name"}
              and type(item["class"]) is str and type(item["name"]) is str
              and len(item["name"]) <= 1024, "focused_collection_identity_refused")
        base = item["name"].split("[", 1)[0]
        identity = (item["class"], item["name"])
        check((item["class"], base) in expected and identity not in identities,
              "focused_collection_identity_refused")
        identities.add(identity)
        functions.add((item["class"], base))
    check(functions == expected, "focused_selected_function_missing")
    return identities


def focused_result(xml, collection, config):
    read(xml, maximum=4 * 1024**2)
    root = ET.parse(xml).getroot()
    check(not list(root.iter("failure")) and not list(root.iter("error"))
          and not list(root.iter("skipped")), "focused_failure_or_skip_refused")
    wanted = collection_identities(collection, config)
    cases, seen, counts = [], set(), {}
    for case in root.iter("testcase"):
        classname, name = case.attrib.get("classname", ""), case.attrib.get("name", "")
        check((classname, name) in wanted and (classname, name) not in seen,
              "focused_case_identity_refused")
        seen.add((classname, name))
        identity = (classname, name.split("[", 1)[0])
        counts[identity] = counts.get(identity, 0) + 1
        cases.append((classname, name))
    check(seen == wanted, "focused_collected_cases_missing")
    base_functions = [{"class": module, "function": function, "variants_passed": count}
                      for (module, function), count in sorted(counts.items())]
    return cases, base_functions


def focused_diagnostic(xml, exit_code, config):
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
    if len(cases) > 4096:
        return result
    allowed = {item["class"] for item in config["expected_functions"]}
    result["junit_parsed"] = True
    result["observed_cases"] = len(cases)
    result["error_nodes"] = min(4096, len(list(root.iter("error"))))
    result["failure_nodes"] = min(4096, len(list(root.iter("failure"))))
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
                if filename in config["selected_modules"]:
                    frame={'file':filename,'line':int(line)}
                    if frame not in frames:frames.append(frame)
            kind=node.attrib.get('type','')
            details.append({'type':kind if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]{0,100}',kind) else 'unclassified',
                            'selected_source_frames':frames[:20],
                            'exception_kinds':sorted(set(re.findall(r'\b(?:ExceptionGroup|AssertionError|RuntimeError|TimeoutError|TypeError|KeyError|Failed|CancelledError)\b',(node.text or '')+' '+node.attrib.get('message','')))),
                            'fixture_source_frames':[{'file':name,'line':int(line)} for name,line in re.findall(r'(pytest_homeassistant_custom_component/[A-Za-z_]+[.]py):([0-9]{1,5})',node.text or '')][:20]})
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
            "scope": SCOPE, "stage": args.mode,
            "failure_code": code, "release_published": False})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
