"""Native Linux frozen final-candidate package and offline regression checks."""

import sys

import argparse
import ast
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
import shutil
import subprocess
import tarfile
import time
import traceback
import xml.etree.ElementTree as ET
import zipfile


SOURCE_SHA = INVENTORY_SHA = CHECKER_SHA = None
SOURCE_COMMIT = None
SOURCE_PREFIX = ""
COUNT = None
PINS = None
BUILDER_SHA = '2d7de50e282fde632e5e57bb7bd3a9dfcd4516ba5a9754094097d8b7a5679578'
VALIDATOR_SHA = "20c0466b4fa70a83c5f282bfcd07b0d2e6f5a3a1a09bf90072649441b2ad7f37"
CONSTRAINTS_SHA = "7baa9a8f39ddeb9c5bb60a1036f6d5e33f4b84267f151f53cc2b95ef031a21b5"
CORE = "2026.10.2"
MINIMUM_CORE = "2026.9.4"
VERSION = '1.0.0-rc.1'
LIMIT = 64 * 1024**2
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


def load_pins(path, expected_sha):
    """Reviewed immutable configuration; placeholder or ambiguous pins fail closed."""
    def unique(pairs):
        value = {}
        for key, item in pairs:
            check(key not in value, "duplicate_config_key_refused")
            value[key] = item
        return value

    value = json.loads(read_pinned(path, expected_sha, 64 * 1024), object_pairs_hook=unique)
    fields = {"schema", "candidate_source_commit", "candidate_source_prefix", "source_sha256",
              "source_inventory_sha256", "source_files", "driver_sha256", "checker_sha256", "version",
              "expected_release_files", "minimum_backend_passed", "required_backend_tests", "frontend_tests",
              "package_sha256", "package_inventory_sha256", "canonical_package_sha256", "requirements_helper_sha256"}
    check(isinstance(value, dict) and set(value) == fields and type(value["schema"]) is int and value["schema"] == 1, "config_schema_refused")
    for key in ("source_sha256", "source_inventory_sha256", "driver_sha256", "checker_sha256",
                "package_sha256", "package_inventory_sha256", "canonical_package_sha256", "requirements_helper_sha256"):
        check(isinstance(value[key], str) and re.fullmatch(r"[0-9a-f]{64}", value[key]), "config_pin_refused")
    check(sha(Path(__file__).read_bytes()) == value["driver_sha256"], "driver_pin_refused")
    check(isinstance(value["candidate_source_commit"], str)
          and re.fullmatch(r"[0-9a-f]{40}", value["candidate_source_commit"]), "source_commit_refused")
    prefix = value["candidate_source_prefix"]
    check(isinstance(prefix, str) and (prefix == "" or re.fullmatch(r"[A-Za-z0-9_./-]+/", prefix))
          and not prefix.startswith("/") and not {".", ".."}.intersection(prefix.split("/")), "source_prefix_refused")
    check(type(value["source_files"]) is int and 327 <= value["source_files"] <= 1024,
          "source_count_config_refused")
    check(value["version"] == VERSION and value["expected_release_files"] == 112
          and type(value["expected_release_files"]) is int
          and value["frontend_tests"] == 126 and type(value["frontend_tests"]) is int,
          "candidate_scope_refused")
    check(type(value["minimum_backend_passed"]) is int
          and 1443 <= value["minimum_backend_passed"] <= 2400, "backend_minimum_refused")
    required, seen = value["required_backend_tests"], set()
    check(isinstance(required, list) and 2 <= len(required) <= 54, "required_tests_config_refused")
    for item in required:
        check(isinstance(item, dict) and set(item) == {"class", "function"}
              and isinstance(item["class"], str) and re.fullmatch(r"tests\.[A-Za-z0-9_.]{1,160}", item["class"])
              and isinstance(item["function"], str) and re.fullmatch(r"test_[A-Za-z0-9_]{1,115}", item["function"]),
              "required_test_name_refused")
        identity = (item["class"], item["function"])
        check(identity not in seen, "required_test_duplicate_refused")
        seen.add(identity)
    return value


def configure(value):
    global SOURCE_SHA, INVENTORY_SHA, CHECKER_SHA, SOURCE_COMMIT, SOURCE_PREFIX, COUNT, PINS
    PINS = value
    SOURCE_SHA = value["source_sha256"]
    INVENTORY_SHA = value["source_inventory_sha256"]
    CHECKER_SHA = value["checker_sha256"]
    SOURCE_COMMIT = value["candidate_source_commit"]
    SOURCE_PREFIX = value["candidate_source_prefix"]
    COUNT = value["source_files"]


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
        check(sha(files.get(name, b"")) == expected, "reviewed_release_tools_required")
    manifest = json.loads(files["custom_components/homecircle/manifest.json"])
    check(manifest.get("version") == VERSION and manifest.get("requirements") == REQUIREMENTS,
          "manifest_version_or_requirements_refused")
    for name in ("frontend/homecircle-card/package.json", "frontend/homecircle-card/package-lock.json"):
        value = json.loads(files[name])
        check(value.get("version") == VERSION, "frontend_metadata_version_refused")
        if name.endswith("package-lock.json"):
            check(value.get("lockfileVersion") == 3 and value.get("packages", {}).get("", {}).get("version") == VERSION,
                  "frontend_lock_version_refused")
    hacs = json.loads(files["hacs.json"])
    check(hacs.get("zip_release") is True and hacs.get("filename") == "homecircle.zip"
          and hacs.get("homeassistant") == MINIMUM_CORE and hacs.get("hide_default_branch") is True,
          "hacs_release_metadata_refused")
    return files



def candidate_inputs(directory, files, bundle=None):
    """Bind the immutable level9 candidate; require its canonical rebuild identity."""
    raw=read_pinned(directory/'homecircle.zip',PINS['package_sha256'])
    inventory_raw=read_pinned(directory/'inventory.json',PINS['package_inventory_sha256'],2*1024**2)
    inventory=json.loads(inventory_raw)
    check(type(inventory) is dict and set(inventory)=={'archive_sha256','files','version'}
          and inventory['archive_sha256']==PINS['package_sha256'] and inventory['version']==VERSION
          and type(inventory['files']) is dict and len(inventory['files'])==112,
          'candidate_inventory_refused')
    body={}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        check(len(archive.infolist())==112,'candidate_member_count_refused')
        for member in archive.infolist():
            name=member.filename
            path=PurePosixPath(name)
            check(name==path.as_posix() and path.parts and not path.is_absolute()
                  and not {'.','..','.git'}.intersection(path.parts)
                  and not any(c in name for c in "\\\0\n\r")
                  and not member.is_dir() and (member.external_attr>>16)&0o170000!=0o120000
                  and name not in body and 0<=member.file_size<=LIMIT,'candidate_member_refused')
            content=archive.read(member)
            check(fingerprint(content)==inventory['files'].get(name),'candidate_member_bytes_refused')
            source_name='LICENSE' if name=='LICENSE' else 'custom_components/homecircle/'+name
            if not name.startswith('frontend/'):
                check(files.get(source_name)==content,'candidate_git_source_refused')
            else:
                check(name.removeprefix('frontend/') in FRONTEND,'candidate_frontend_scope_refused')
                if bundle is not None:
                    check(fingerprint(content)==bundle[name.removeprefix('frontend/')],
                          'candidate_rebuilt_frontend_refused')
            body[name]=content
    check(set(body)==set(inventory['files']) and sum(len(v) for v in body.values())<=LIMIT,
          'candidate_payload_scope_refused')
    return raw,inventory_raw,body


def install_candidate(tree,body,files):
    readme=tree/'custom_components/homecircle/README.md'
    check(not readme.is_symlink() and readme.read_bytes()==files['custom_components/homecircle/README.md'],
          'source_only_readme_refused')
    root=tree/'custom_components/homecircle'
    for name,content in body.items():
        target=root/name
        check(not target.is_symlink(),'candidate_install_symlink_refused')
        target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        target.write_bytes(content)
    candidate_installed(tree,body,files)


def candidate_installed(tree,body,files):
    readme=tree/'custom_components/homecircle/README.md'
    check(not readme.is_symlink() and readme.read_bytes()==files['custom_components/homecircle/README.md'],
          'source_only_readme_refused')
    root=tree/'custom_components/homecircle'
    actual={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and p!=readme}
    check(actual==body and not any(p.is_symlink() for p in root.rglob('*')),
          'exact_candidate_install_refused')


def requirements_helper():
    path=Path(__file__).with_name('requirements_support.py')
    read_pinned(path,PINS['requirements_helper_sha256'])
    spec=importlib.util.spec_from_file_location('full_package_requirements',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def verify_git_source(files, directory):
    """Read exact public-file blobs from the canonical commit; never touch its index."""
    check(directory is not None and directory.is_dir() and not directory.is_symlink(), "source_git_directory_required")
    environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C.UTF-8",
                   "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"}
    def git(*arguments):
        result = subprocess.run(["git", "-C", str(directory), *arguments], stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=environment,
                                check=False, timeout=15)
        check(result.returncode == 0, "source_git_object_refused")
        return result.stdout
    check(git("rev-parse", "--verify", SOURCE_COMMIT + "^{commit}").decode().strip() == SOURCE_COMMIT,
          "source_git_commit_refused")
    for name, content in files.items():
        check(git("cat-file", "blob", SOURCE_COMMIT + ":" + SOURCE_PREFIX + name) == content,
              "source_git_blob_mismatch")
    return {"candidate_source_commit": SOURCE_COMMIT, "canonical_commit_blobs_verified": len(files),
            "candidate_source_prefix": SOURCE_PREFIX, "public_inventory_scope_only": True}


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


def frontend_inventory(tree):
    found = {}
    for name in FRONTEND:
        path = tree / "custom_components/homecircle/frontend" / name
        check(path.is_file() and not path.is_symlink() and path.stat().st_size <= 16 * 1024**2,
              "frontend_bundle_path_refused")
        found[name] = fingerprint(path.read_bytes())
    return found


def frontend_matches(tree, expected):
    check(frontend_inventory(tree) == expected, "frontend_bundle_bytes_changed")


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


def frontend(args, files):
    source_unchanged(files, args.tree)
    check(args.first_frontend is not None and args.first_frontend.is_dir(), "first_frontend_required")
    actual = frontend_inventory(args.tree)
    for name in FRONTEND:
        first = args.first_frontend / name
        check(first.is_file() and not first.is_symlink()
              and fingerprint(first.read_bytes()) == actual[name], "frontend_reproducibility_refused")
    license_path = args.tree / "frontend/homecircle-card/node_modules/leaflet/LICENSE"
    check(license_path.is_file() and sha(license_path.read_bytes()) == actual["LEAFLET-LICENSE.txt"]["sha256"],
          "leaflet_notice_copy_refused")
    check(args.npm_log.is_file() and args.npm_log.stat().st_size <= 32 * 1024**2, "npm_log_refused")
    text = args.npm_log.read_text()
    for key, count in (("tests", 126), ("pass", 126), ("fail", 0), ("cancelled", 0), ("skipped", 0), ("todo", 0)):
        check(re.findall(r"^# " + key + r" ([0-9]+)\s*$", text, re.MULTILINE) == [str(count)],
              "frontend_test_counts_refused")
    privacy_result = json.loads((args.results / "privacy-summary.json").read_bytes())
    check(privacy_result.get("outcome") == "passed" and privacy_result.get("files_checked") == COUNT
          and privacy_result.get("checker_sha256") == CHECKER_SHA, "prior_source_privacy_required")
    safe = {"schema": 1, "outcome": "passed", "completed": True, "frontend_tests_passed": 126,
            "frontend_tests_failed": 0, "frontend_reproducible": True, "frontend_bundle": actual,
            "leaflet_notice_matches_dependency": True, "source_sha256": SOURCE_SHA,
            "source_inventory_sha256": INVENTORY_SHA, "source_files": COUNT,
            "candidate_source_commit": SOURCE_COMMIT, "privacy": privacy_result,
            "owner_accounts_used": False, "release_candidate_validation": True}
    atomic_json(args.results / "frontend-summary.json", safe)


def technical_versions():
    observed = {name: importlib.metadata.version(name) for name in ("cryptography", "srp", "unicorn")}
    check(observed == {"cryptography": "50.0.1", "srp": "1.0.22", "unicorn": "2.1.4"},
          "technical_dependency_version_refused")
    return observed


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


def build(args, files, bundle):
    builder, validator = release_tools(args.tree)
    frontend_matches(args.tree, bundle)
    candidate_raw,candidate_inventory_raw,candidate=candidate_inputs(args.payload,files,bundle)
    candidate_installed(args.tree,candidate,files)
    payload = builder.collect_payload(args.tree / "custom_components/homecircle", args.tree / "LICENSE")
    expected = {"LICENSE": files["LICENSE"]}
    prefix = "custom_components/homecircle/"
    for name, raw in files.items():
        if name.startswith(prefix) and builder.allowed_member(name[len(prefix):]):
            expected[name[len(prefix):]] = raw
    for name in FRONTEND:
        expected["frontend/" + name] = (args.tree / "custom_components/homecircle/frontend" / name).read_bytes()
    check(payload == expected == candidate and len(payload) == PINS["expected_release_files"],
          "release_payload_source_refused")
    check(json.loads(payload["manifest.json"])["requirements"] == REQUIREMENTS, "manifest_requirements_refused")
    check(validator.inspect_archive(args.payload/'homecircle.zip',args.payload/'inventory.json')==candidate,
          'candidate_release_inspection_refused')
    canonical_output=args.results/'canonical-build'
    path, inventory = builder.write_archive(payload, canonical_output)
    check(validator.inspect_archive(path, canonical_output/'inventory.json') == expected, "release_inspection_refused")
    second, _ = builder.write_archive(payload, args.results / "reproducibility")
    check(path.read_bytes() == second.read_bytes(), "release_reproducibility_refused")
    check(inventory["version"] == VERSION and inventory['archive_sha256']==PINS['canonical_package_sha256'],
          "canonical_release_identity_refused")
    check(path.read_bytes()==candidate_raw and
          (canonical_output/'inventory.json').read_bytes()==candidate_inventory_raw,
          'canonical_candidate_identity_refused')
    output=args.results/'release'
    output.mkdir(mode=0o700,exist_ok=True)
    (output/'homecircle.zip').write_bytes(candidate_raw)
    (output/'inventory.json').write_bytes(candidate_inventory_raw)
    return {"release_version": VERSION, "release_sha256": sha(candidate_raw),
            "release_inventory_sha256": sha(candidate_inventory_raw),
            "release_bytes": len(candidate_raw), "release_files": len(payload),
            "candidate_archive_rebuilt":False,"exact_candidate_bytes_installed":True,
            "nonruntime_source_only_files":["README.md"],
            "nonruntime_source_only_inventory":{"README.md":fingerprint(files['custom_components/homecircle/README.md'])},
            "candidate_compression_level":9,"canonical_compression_level":9,
            "canonical_rebuild_sha256":inventory['archive_sha256'],
            "canonical_rebuild_inventory_sha256":sha((canonical_output/'inventory.json').read_bytes()),
            "canonical_reproducible_archive":True,"candidate_payload_equals_canonical_payload":True,
            "package_matches_exact_source_and_built_frontend": True,
            "unchanged_builder_sha256": BUILDER_SHA, "unchanged_validator_sha256": VALIDATOR_SHA,
            "release_candidate_validation": True, "release_published": False,
            "version_substitutions_performed": False, "candidate_source_commit": SOURCE_COMMIT}


def staged_frontend(args):
    summary = json.loads((args.payload / "frontend-summary.json").read_bytes())
    check(summary.get("outcome") == "passed" and summary.get("completed") is True
          and summary.get("source_sha256") == SOURCE_SHA and summary.get("source_inventory_sha256") == INVENTORY_SHA
          and summary.get("candidate_source_commit") == SOURCE_COMMIT and summary.get("source_files") == COUNT
          and summary.get("frontend_tests_passed") == 126 and summary.get("frontend_tests_failed") == 0
          and summary.get("frontend_reproducible") is True, "staged_frontend_summary_refused")
    bundle = summary.get("frontend_bundle")
    check(isinstance(bundle, dict) and set(bundle) == set(FRONTEND), "staged_frontend_inventory_refused")
    for name in FRONTEND:
        metadata = bundle[name]
        check(isinstance(metadata, dict) and set(metadata) == {"bytes", "sha256"}
              and type(metadata["bytes"]) is int and 0 <= metadata["bytes"] <= 16 * 1024**2
              and isinstance(metadata["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", metadata["sha256"]),
              "staged_frontend_fingerprint_refused")
        check(fingerprint((args.payload / name).read_bytes()) == metadata, "staged_frontend_bytes_refused")
    return bundle


def setup(args, files):
    path = constraints()
    extract(files, args.tree)
    target = args.tree / "custom_components/homecircle/frontend"
    target.mkdir(mode=0o700, parents=True, exist_ok=True)
    bundle = staged_frontend(args)
    for name in FRONTEND:
        (target / name).write_bytes((args.payload / name).read_bytes())
    frontend_matches(args.tree, bundle)
    _raw,_inventory,candidate=candidate_inputs(args.payload,files,bundle)
    install_candidate(args.tree,candidate,files)
    result = build(args, files, bundle)
    helpers=requirements_helper()
    graph=helpers.core_component_requirements(candidate)
    wanted=sorted(set(REQUIREMENTS+graph['requirements']+
        ['pytest-homeassistant-custom-component==0.13.373','findmy==0.10.2']))
    command = ["uv", "pip", "install", "--system", "--no-config", "--index-url", "https://pypi.org/simple",
               "--index-strategy", "unsafe-first-match", "--constraint", str(path), *wanted]
    check(run_owned(command, cwd=args.tree, log=args.results / "dependency-private.log", limit=660) == 0,
          "dependency_install_refused")
    installed = closure(constraints())
    check(importlib.metadata.version("pytest-homeassistant-custom-component") == "0.13.373"
          and importlib.metadata.version("findmy") == "0.10.2", "test_dependency_version_refused")
    versions=helpers.verify_declared_versions(graph['requirements'])
    source_unchanged(files, args.tree)
    candidate_installed(args.tree,candidate,files)
    result.update({"schema": 1, "outcome": "passed", "completed": True, "core": CORE,
                   "python": platform.python_version(), "machine": platform.machine(),
                   "constraints_sha256": CONSTRAINTS_SHA, "installed_dependency_closure": installed,
                   "core_requirement_graph":graph,"startup_requirement_versions":versions,
                   "technical_dependency_versions":technical_versions(),
                   "pytest_homeassistant_custom_component":"0.13.373",
                   "source_sha256": SOURCE_SHA, "source_inventory_sha256": INVENTORY_SHA,
                   "source_files": COUNT, "candidate_source_commit": SOURCE_COMMIT,
                   "owner_accounts_used": False})
    atomic_json(args.results / "setup-summary.json", result)


def public_test_catalog(files):
    """Permit diagnostic names only when present in the bound public source."""
    catalog = set()
    for path, raw in files.items():
        if not re.fullmatch(r"tests/(?:[A-Za-z0-9_]+/)*test_[A-Za-z0-9_]+[.]py", path):
            continue
        module = path[:-3].replace("/", ".")
        tree = ast.parse(raw)
        pending = [(tree.body, module)]
        while pending:
            nodes, classname = pending.pop()
            for node in nodes:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and re.fullmatch(
                        r"test_[A-Za-z0-9_]{1,115}", node.name):
                    catalog.add((classname, node.name))
                elif isinstance(node, ast.ClassDef) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,79}", node.name):
                    pending.append((node.body, classname + "." + node.name))
    check(1 <= len(catalog) <= 5000, "diagnostic_public_test_catalog_refused")
    return catalog


def backend_diagnostics(path, catalog):
    """Count rejected JUnit records without exporting parameters or trace text."""
    check(path.is_file() and not path.is_symlink() and path.stat().st_size <= 16 * 1024**2,
          "backend_xml_refused")
    root = ET.fromstring(path.read_bytes())
    cases = root.findall(".//testcase")
    check(1 <= len(cases) <= 5000, "backend_diagnostic_case_bound_refused")
    counts = {"case_records": len(cases), "passed": 0, "failed": 0, "skipped": 0,
              "error_records": 0, "failure_records": 0, "ambiguous_outcome_records": 0,
              "duplicate_records": 0, "duplicate_identities": 0,
              "unclassified_failure_records": 0, "unclassified_duplicate_identities": 0}
    identities, failures, duplicates = {}, {}, {}
    for case in cases:
        identity = (case.attrib.get("classname"), case.attrib.get("name"))
        identities[identity] = identities.get(identity, 0) + 1
        error = case.find("error") is not None
        failure = case.find("failure") is not None
        skipped = case.find("skipped") is not None
        counts["error_records"] += int(error)
        counts["failure_records"] += int(failure)
        counts["failed"] += int(error or failure)
        counts["skipped"] += int(skipped)
        counts["passed"] += int(not (error or failure or skipped))
        counts["ambiguous_outcome_records"] += int(int(error) + int(failure) + int(skipped) > 1)
        if error or failure:
            label = (identity[0], (identity[1] or "").split("[", 1)[0])
            if label in catalog:
                failures[label] = failures.get(label, 0) + 1
            else:
                counts["unclassified_failure_records"] += 1
    for identity, occurrences in identities.items():
        if occurrences < 2:
            continue
        counts["duplicate_records"] += occurrences - 1
        counts["duplicate_identities"] += 1
        label = (identity[0], (identity[1] or "").split("[", 1)[0])
        if label in catalog:
            duplicates[label] = duplicates.get(label, 0) + occurrences
        else:
            counts["unclassified_duplicate_identities"] += 1
    def labels(values):
        return [{"class": classname, "function": function, "case_records": count}
                for (classname, function), count in sorted(values.items())[:12]]
    return {"schema": 1, "scope": "unaccepted_junit_record_diagnostics", "acceptance_qualified": False,
            **counts, "failure_labels": labels(failures), "duplicate_labels": labels(duplicates),
            "failure_label_functions": len(failures), "duplicate_label_functions": len(duplicates),
            "maximum_label_functions_per_kind": 12, "raw_test_parameters_exported": False,
            "raw_failure_text_exported": False, "public_source_bound_labels": True}


def backend_with_diagnostics(path, files, result, destination, collection=None):
    """Save a failed aggregate before strict outcome/uniqueness acceptance."""
    result["backend_diagnostics"] = backend_diagnostics(path, public_test_catalog(files))
    atomic_json(destination, result)
    return backend_result(path, collection=collection,
                          expected=full_expected_functions(files) if collection is not None else None)


def full_expected_functions(files):
    """All collectable base functions declared in the complete frozen test tree."""
    expected = set()
    for name, raw in files.items():
        if re.fullmatch(r"tests/(?:[A-Za-z0-9_]+/)*test_[A-Za-z0-9_]+[.]py", name) is None:
            continue
        module = name.removesuffix(".py").replace("/", ".")
        for node in ast.parse(raw).body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                expected.add((module, node.name))
            elif isinstance(node, ast.ClassDef) and (node.name.startswith("Test") or any(
                isinstance(base, ast.Attribute) and base.attr == "TestCase"
                or isinstance(base, ast.Name) and base.id == "TestCase" for base in node.bases
            )):
                expected.update((module + "." + node.name, child.name) for child in node.body
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("test_"))
    check(1 <= len(expected) <= 5000, "full_declared_function_bound_refused")
    return expected


def full_pytest(collection, arguments):
    """Only the offline Linux child imports pytest; all parameters stay private."""
    constraints()
    import pytest

    class CollectionProbe:
        deselected = 0

        def pytest_deselected(self, items):
            self.deselected += len(items)

        def pytest_collection_finish(self, session):
            cases = []
            for item in session.items:
                # Match pytest JUnit's address handling: :: inside a parameter
                # is data, rather than a class/function separator.
                address, bracket, parameter = item.nodeid.partition("[")
                parts = address.split("::")
                parts[0] = parts[0].removesuffix(".py").replace("/", ".")
                if bracket:
                    parts[-1] += "[" + parameter
                cases.append({"class": ".".join(parts[:-1]), "name": parts[-1]})
            atomic_json(Path(collection), {"schema": 1, "cases": cases, "deselected": self.deselected})

    return pytest.main(arguments, plugins=[CollectionProbe()])


FULL_WRAPPER = (
    "import importlib.util,sys; "
    "s=importlib.util.spec_from_file_location('homecircle_full_collection_driver',sys.argv[1]); "
    "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
    "raise SystemExit(m.full_pytest(sys.argv[2],sys.argv[3:]))"
)


def full_collection_result(path, cases, expected):
    check(path.is_file() and not path.is_symlink() and path.stat().st_size <= 16 * 1024**2,
          "full_collection_file_refused")
    def unique(pairs):
        value = {}
        for key, item in pairs:
            check(key not in value, "full_collection_duplicate_key_refused")
            value[key] = item
        return value
    value = json.loads(path.read_bytes(), object_pairs_hook=unique)
    check(type(value) is dict and set(value) == {"schema", "cases", "deselected"}
          and type(value["schema"]) is int and value["schema"] == 1
          and type(value["deselected"]) is int and value["deselected"] == 0
          and type(value["cases"]) is list and 1 <= len(value["cases"]) <= 5000,
          "full_collection_shape_or_deselection_refused")
    wanted, observed_functions = set(), set()
    for item in value["cases"]:
        check(type(item) is dict and set(item) == {"class", "name"}
              and type(item["class"]) is str and type(item["name"]) is str
              and len(item["name"]) <= 128 * 1024, "full_collection_identity_refused")
        identity = (item["class"], item["name"])
        function = (item["class"], item["name"].split("[", 1)[0])
        check(identity not in wanted and function in expected, "full_collection_identity_refused")
        wanted.add(identity)
        observed_functions.add(function)
    check(observed_functions == expected, "full_collection_declared_function_missing")
    actual = {(case.attrib.get("classname"), case.attrib.get("name")) for case in cases}
    check(actual == wanted and len(cases) == len(wanted), "full_collection_junit_identity_mismatch")
    return {"collected_cases": len(wanted), "declared_base_functions": len(expected),
        "deselected": 0, "exact_identities_match_junit": True, "raw_parameter_ids_exported": False}


def backend_result(path, *, collection=None, expected=None):
    check(path.is_file() and path.stat().st_size <= 16 * 1024**2, "backend_xml_refused")
    root = ET.fromstring(path.read_bytes())
    cases = root.findall(".//testcase")
    identities = [(case.attrib.get("classname"), case.attrib.get("name")) for case in cases]
    check(len(identities) == len(set(identities)), "duplicate_backend_case_refused")
    failed = [case for case in cases if case.find("error") is not None or case.find("failure") is not None]
    skipped = [case for case in cases if case.find("skipped") is not None]
    check(not any(case in skipped for case in failed), "ambiguous_backend_outcome_refused")
    labels = []
    for case in failed[:3]:
        classname = case.attrib.get("classname", "")
        function = case.attrib.get("name", "").split("[", 1)[0]
        if classname.startswith("tests.") and re.fullmatch(r"[A-Za-z0-9_.]{1,180}", classname) \
                and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,119}", function):
            labels.append({"class": classname, "function": function})
    passing = {(case.attrib.get("classname", ""), case.attrib.get("name", "").split("[", 1)[0])
               for case in cases if case not in failed and case not in skipped}
    required = [{**item, "passed": (item["class"], item["function"]) in passing}
                for item in PINS["required_backend_tests"]]
    result = {"passed": len(cases) - len(failed) - len(skipped), "failed": len(failed), "skipped": len(skipped),
            "required_regressions": required, "failure_labels": labels,
            "skip_identities":[{'class':'tests.test_findmy_runtime_bootstrap',
                                'function':'test_retained_public_apple_dmg_fixed_ranges'}
                if case.attrib.get('classname')=='tests.test_findmy_runtime_bootstrap'
                   and case.attrib.get('name')=='test_retained_public_apple_dmg_fixed_ranges'
                else {'class':'unclassified','function':'unclassified'} for case in skipped]}
    check((collection is None) == (expected is None), "full_collection_pair_required")
    if collection is not None:
        result["collection"] = full_collection_result(collection, cases, expected)
    return result, skipped


# Exact baseline source and test cases are rendered into reviewed driver constants.
BASELINE_SOURCE_COMMIT = 'fc0bba472cd60a06dac6bab30b7d011fd533624b'
BASELINE_VAULT_SHA = '7c6a846cefba6a34647d84b7738a93d85738a948da32fbf752a96c4e1cf4c0f2'
BASELINE_VAULT_NAME = "custom_components/homecircle/findmy_vault.py"
BASELINE_RED_CASES = (('tests.test_findmy_vault_hardening', 'test_malformed_key_refuses_load_and_save_without_replacement[load-invalid_base64]'), ('tests.test_findmy_vault_hardening', 'test_malformed_key_refuses_load_and_save_without_replacement[save-invalid_base64]'), ('tests.test_findmy_vault_hardening', 'test_malformed_key_refuses_load_and_save_without_replacement[save_account-invalid_base64]'), ('tests.test_findmy_vault_hardening', 'test_malformed_key_refuses_load_and_save_without_replacement[load-short_decoded]'), ('tests.test_findmy_vault_hardening', 'test_malformed_key_refuses_load_and_save_without_replacement[save-short_decoded]'), ('tests.test_findmy_vault_hardening', 'test_malformed_key_refuses_load_and_save_without_replacement[save_account-short_decoded]'), ('tests.test_findmy_vault_hardening', 'test_missing_or_unreadable_store_load_is_redacted_without_creating_files[missing_directory]'), ('tests.test_findmy_vault_hardening', 'test_missing_or_unreadable_store_load_is_redacted_without_creating_files[missing_vault]'), ('tests.test_findmy_vault_hardening', 'test_missing_or_unreadable_store_load_is_redacted_without_creating_files[key_read_error]'), ('tests.test_findmy_identity_continuity', 'test_explicit_disconnect_removes_only_confirmed_malformed_or_missing_owned_store[invalid_base64_key]'), ('tests.test_findmy_identity_continuity', 'test_explicit_disconnect_removes_only_confirmed_malformed_or_missing_owned_store[short_decoded_key]'), ('tests.test_findmy_identity_continuity', 'test_explicit_disconnect_removes_only_confirmed_malformed_or_missing_owned_store[missing_directory]'), ('tests.test_findmy_identity_continuity', 'test_explicit_disconnect_removes_only_confirmed_malformed_or_missing_owned_store[missing_vault]'), ('tests.test_findmy_identity_continuity', 'test_explicit_disconnect_removes_only_confirmed_malformed_or_missing_owned_store[key_read_error]'))


# No pytest/HA/cryptography import occurs at driver import time.
BASELINE_PROPERTY = "homecircle_expected_failure_cause"
BASELINE_TEST_SHAS = {
    "tests.test_findmy_vault_hardening": "3510bf41c01390fbebf848439deae353e0bfd934cc2c63deca242643be8030c2",
    "tests.test_findmy_identity_continuity": "423bf086c9cb468cc3822e85e32150af9924c8d173737783fcd25d8b574c0d87",
}
BASELINE_WRAPPER = (
    "import importlib.util,sys; "
    "s=importlib.util.spec_from_file_location('homecircle_baseline_driver',sys.argv[1]); "
    "m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m); "
    "raise SystemExit(m.baseline_pytest(sys.argv[2:]))"
)


def baseline_trace_matches(error, expected_type, codes, lines=()):
    """Inspect only the escaping exact exception and bound code identities."""
    if type(error) is not expected_type:
        return False
    seen = []
    current = error.__traceback__
    while current is not None:
        if len(seen) >= 64:
            return False
        seen.append((current.tb_frame.f_code, current.tb_lineno))
        current = current.tb_next
    return all(any(code is actual for actual, _ in seen) for code in codes) and all(
        any(code is actual and line == actual_line for actual, actual_line in seen) for code, line in lines
    )


def baseline_unwrap(function):
    """Resolve bounded functools.wraps chains without invoking custom properties."""
    seen = set()
    for _ in range(8):
        if type(function) is not type(baseline_unwrap) or id(function) in seen:
            return None
        seen.add(id(function))
        wrapped = function.__dict__.get("__wrapped__")
        if wrapped is None:
            return function
        function = wrapped
    return None


def baseline_failure_cause(function, identity, error):
    """Require the actual old-vault failure, or the exact confirmed-flow assert."""
    if identity not in BASELINE_RED_CASES:
        return False
    function = baseline_unwrap(function)
    if function is None:
        return False
    classname, case = identity
    test_path = Path.cwd() / (classname.replace(".", "/") + ".py")
    raw = read_pinned(test_path, BASELINE_TEST_SHAS[classname], 1024 * 1024)
    if Path(function.__code__.co_filename).resolve() != test_path.resolve():
        return False
    vault_path = Path.cwd() / BASELINE_VAULT_NAME
    read_pinned(vault_path, BASELINE_VAULT_SHA, 1024 * 1024)
    module = sys.modules.get("custom_components.homecircle.findmy_vault")
    if module is None or Path(module.__file__).resolve() != vault_path.resolve():
        return False
    vault = module.Vault
    if any(Path(getattr(vault, name).__code__.co_filename).resolve() != vault_path.resolve()
           for name in ("_check", "_cipher")):
        return False
    name = case.split("[", 1)[0]
    if function.__name__ != name:
        return False
    if name == "test_malformed_key_refuses_load_and_save_without_replacement":
        constructor = vault._cipher.__globals__["Fernet"].__init__
        return baseline_trace_matches(error, ValueError, (vault._cipher.__code__, constructor.__code__))
    if name == "test_missing_or_unreadable_store_load_is_redacted_without_creating_files":
        if case.endswith("[key_read_error]"):
            nested = [code for code in function.__code__.co_consts
                      if type(code) is type(function.__code__) and code.co_name == "read"]
            return len(nested) == 1 and baseline_trace_matches(
                error, PermissionError, (vault._cipher.__code__, nested[0]))
        return baseline_trace_matches(error, FileNotFoundError, (vault._check.__code__,))
    if name == "test_explicit_disconnect_removes_only_confirmed_malformed_or_missing_owned_store":
        tree = ast.parse(raw, filename=str(test_path))
        definitions = [node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == name]
        if len(definitions) != 1:
            return False
        candidates = []
        for node in ast.walk(definitions[0]):
            if not isinstance(node, ast.Assert):
                continue
            for call in ast.walk(node):
                if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                        and call.func.attr == "async_step_findmy_disconnect" and len(call.args) == 1
                        and isinstance(call.args[0], ast.Dict)
                        and len(call.args[0].keys) == len(call.args[0].values) == 1
                        and isinstance(call.args[0].keys[0], ast.Constant) and call.args[0].keys[0].value == "confirm"
                        and isinstance(call.args[0].values[0], ast.Constant) and call.args[0].values[0].value is True):
                    candidates.append(node.lineno)
        return len(candidates) == 1 and baseline_trace_matches(
            error, AssertionError, (), ((function.__code__, candidates[0]),))
    return False


def baseline_pytest(arguments):
    """Only the networkless baseline child imports pytest and attaches this hook."""
    import pytest

    sys.path.insert(0, str(Path.cwd()))

    class CauseProbe:
        @pytest.hookimpl(tryfirst=True)
        def pytest_runtest_makereport(self, item, call):
            if call.when != "call":
                return
            verified = False
            if call.excinfo is not None:
                try:
                    verified = baseline_failure_cause(
                        item.function, (item.function.__module__, item.name), call.excinfo.value)
                except Exception:
                    pass
            item.user_properties.append((BASELINE_PROPERTY, "verified" if verified else "refused"))

    return pytest.main(arguments, plugins=[CauseProbe()])


def backend_budget(deadline, maximum=900):
    remaining = int(deadline - time.monotonic())
    check(remaining >= 1, "combined_backend_deadline_refused")
    return min(remaining, maximum)


def baseline_red_result(path, code):
    check(code == 1 and path.is_file() and not path.is_symlink()
          and path.stat().st_size <= 16 * 1024**2, "baseline_red_exit_or_xml_refused")
    root = ET.fromstring(path.read_bytes())
    cases = root.findall(".//testcase")
    identities = [(item.attrib.get("classname"), item.attrib.get("name")) for item in cases]
    check(len(identities) == len(set(identities)) == len(BASELINE_RED_CASES)
          and set(identities) == set(BASELINE_RED_CASES), "baseline_red_exact_cases_refused")
    check(not root.findall(".//error") and not root.findall(".//skipped")
          and len(root.findall(".//failure")) == len(cases)
          and all(len(item.findall("failure")) == 1 for item in cases), "baseline_red_outcomes_refused")
    check(len(root.findall(".//property")) == len(cases), "baseline_red_cause_refused")
    for item in cases:
        groups = item.findall("properties")
        check(len(groups) == 1 and groups[0].attrib == {} and len(groups[0]) == 1,
              "baseline_red_cause_refused")
        prop = groups[0][0]
        check(prop.tag == "property" and prop.attrib == {"name": BASELINE_PROPERTY, "value": "verified"}
              and len(prop) == 0 and prop.text in (None, ""), "baseline_red_cause_refused")
    return {"schema": 1, "outcome": "passed", "cause_verified": True, "expected_failure_cases": len(cases),
            "all_expected_regressions_observed": True, "collection_errors": 0, "skipped": 0}


def baseline_red(args, files, bundle, deadline):
    """Run expected red tests in a public-file-only private copy, never green tree."""
    baseline = read_pinned(args.payload / "baseline-vault.py", BASELINE_VAULT_SHA, 1024 * 1024)
    check(BASELINE_VAULT_NAME in files and files[BASELINE_VAULT_NAME] != baseline,
          "baseline_and_fixed_vault_must_differ")
    tree = args.results / "baseline-private-source"
    check(not tree.exists() and not tree.is_symlink(), "fresh_baseline_tree_required")
    xml = args.results / "baseline-private.xml"
    source_unchanged(files, args.tree)
    try:
        extract({**files, BASELINE_VAULT_NAME: baseline}, tree)
        # Only the two already verified generated frontend assets may supplement
        # canonical public bytes. No .git, node_modules, cache, or untracked copy.
        frontend = tree / "custom_components/homecircle/frontend"
        frontend.mkdir(mode=0o700, parents=True, exist_ok=True)
        for name in FRONTEND:
            raw = (args.payload / name).read_bytes()
            check(fingerprint(raw) == bundle[name], "baseline_frontend_pin_refused")
            (frontend / name).write_bytes(raw)
        expected = set(files) | {"custom_components/homecircle/frontend/" + name for name in FRONTEND}
        check({path.relative_to(tree).as_posix() for path in tree.rglob("*") if path.is_file()} == expected
              and all(not path.is_symlink() for path in tree.rglob("*")), "baseline_copy_scope_refused")
        selectors = []
        for classname, name in BASELINE_RED_CASES:
            selectors.append(classname.replace(".", "/") + ".py::" + name)
        code = run_owned([sys.executable, "-B", "-c", BASELINE_WRAPPER, str(Path(__file__).resolve()), "--junitxml", str(xml), *selectors],
                         cwd=tree, log=args.results / "baseline-private.log", limit=backend_budget(deadline, 120))
        result = baseline_red_result(xml, code)
    finally:
        if tree.exists():
            check(tree.parent == args.results and not tree.is_symlink(), "baseline_cleanup_scope_refused")
            shutil.rmtree(tree)
        check(not tree.exists() and not tree.is_symlink(), "baseline_copy_cleanup_failed")
        source_unchanged(files, args.tree)
        frontend_matches(args.tree, bundle)
    return {**result, "baseline_source_commit": BASELINE_SOURCE_COMMIT,
            "baseline_vault_sha256": BASELINE_VAULT_SHA, "public_files_only_copy": True,
            "private_copy_removed": True, "fixed_source_unchanged": True,
            "provider_or_owner_accounts_used": False, "combined_red_green_deadline_seconds": 900}


def acceptance(args, files):
    deadline = time.monotonic() + 900
    source_unchanged(files, args.tree)
    bundle = staged_frontend(args)
    frontend_matches(args.tree, bundle)
    red = baseline_red(args, files, bundle, deadline)
    result = build(args, files, bundle)
    installed = closure(constraints())
    setup_receipt=json.loads((args.results/'setup-summary.json').read_bytes())
    check(setup_receipt.get('outcome')=='passed' and setup_receipt.get('core')==CORE
          and setup_receipt.get('candidate_source_commit')==SOURCE_COMMIT
          and setup_receipt.get('release_sha256')==PINS['package_sha256'], 'setup_receipt_refused')
    helpers=requirements_helper()
    _raw,_inventory,candidate=candidate_inputs(args.payload,files,bundle)
    graph=helpers.core_component_requirements(candidate)
    versions=helpers.verify_declared_versions(graph['requirements'])
    check(graph==setup_receipt['core_requirement_graph']
          and versions==setup_receipt['startup_requirement_versions']
          and technical_versions()==setup_receipt['technical_dependency_versions'], 'core_requirement_continuity_refused')
    xml = args.results / "backend-private.xml"
    collection = args.results / "backend-collection-private.json"
    code = run_owned([sys.executable, "-B", "-c", FULL_WRAPPER, str(Path(__file__).resolve()),
                      str(collection), "--junitxml", str(xml)],
                     cwd=args.tree, log=args.results / "backend-private.log", limit=backend_budget(deadline))
    backend_budget(deadline)
    # Pytest may append a second case record after a teardown error. Keep its
    # bounded public identity/counts before the unchanged duplicate refusal.
    result.update({"schema": 1, "outcome": "failed", "completed": False, "baseline_red": red})
    backend, skipped = backend_with_diagnostics(xml, files, result, args.results / "package-summary.json", collection)
    result.update({"schema": 1, "outcome": "failed", "completed": False, "backend": backend, "baseline_red": red})
    atomic_json(args.results / "package-summary.json", result)
    check(code == 0 and backend["passed"] >= PINS["minimum_backend_passed"]
          and backend["failed"] == 0 and backend["skipped"] == 1, "backend_counts_refused")
    check(all(item["passed"] is True for item in backend["required_regressions"]), "required_backend_regression_missing")
    check(skipped[0].attrib.get("name") == "test_retained_public_apple_dmg_fixed_ranges"
          and skipped[0].attrib.get("classname") == "tests.test_findmy_runtime_bootstrap", "backend_skip_refused")
    source_unchanged(files, args.tree)
    frontend_matches(args.tree, bundle)
    check(build(args, files, bundle)["release_sha256"] == result["release_sha256"], "release_changed_after_tests")
    result.update({"outcome": "passed", "completed": True, "core": CORE, "python": platform.python_version(),
                   "machine": platform.machine(), "constraints_sha256": CONSTRAINTS_SHA,
                   "installed_dependency_closure": installed, "core_requirement_graph":graph,
                   "startup_requirement_versions":versions,
                   "technical_dependency_versions":technical_versions(),
                   "pytest_homeassistant_custom_component":"0.13.373",
                   "source_sha256": SOURCE_SHA,
                   "source_inventory_sha256": INVENTORY_SHA, "source_files": COUNT,
                   "candidate_source_commit": SOURCE_COMMIT, "minimum_backend_passed": PINS["minimum_backend_passed"],
                   "backend_network_disconnected_required": True, "owner_accounts_used": False,
                   "production_configuration_used": False, "hacs_delivery_tested": False,
                   "upgrade_recovery_repeated": False, "full_managed_core_lifecycle": False})
    atomic_json(args.results / "package-summary.json", result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "privacy", "frontend", "setup", "acceptance"))
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--tree", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--npm-log", type=Path)
    parser.add_argument("--first-frontend", type=Path)
    parser.add_argument("--pins-sha", required=True)
    parser.add_argument("--git-directory", type=Path)
    args = parser.parse_args()
    args.results.mkdir(mode=0o700, parents=True, exist_ok=True)
    started = time.monotonic()
    stage = "inputs"
    def terminate(_signum, _frame):
        raise Terminated()
    for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(signum, terminate)
    try:
        check(sys.platform == "linux" and platform.machine() == "x86_64", "native_linux_amd64_required")
        configure(load_pins(args.payload / "config.json", args.pins_sha))
        files = inputs(args.payload)
        stage = args.mode
        if args.mode == "prepare":
            source = verify_git_source(files, args.git_directory)
            extract(files, args.tree)
            atomic_json(args.results / "source-summary.json", {"schema": 1, "outcome": "passed", **source,
                        "source_sha256": SOURCE_SHA, "source_inventory_sha256": INVENTORY_SHA,
                        "source_files": COUNT})
        elif args.mode == "privacy":
            source_unchanged(files, args.tree)
            atomic_json(args.results / "privacy-summary.json", {"schema": 1, "outcome": "passed",
                        "source_sha256": SOURCE_SHA, "source_inventory_sha256": INVENTORY_SHA,
                        "candidate_source_commit": SOURCE_COMMIT, **privacy(files, args.tree, args.results)})
        elif args.mode == "frontend":
            frontend(args, files)
        elif args.mode == "setup":
            setup(args, files)
        else:
            acceptance(args, files)
    except BaseException as error:
        failure = {"schema": 1, "outcome": "failed", "completed": False, "mode": args.mode,
                   "failure_stage": stage, "failure_type": type(error).__name__,
                   "elapsed_seconds": round(time.monotonic() - started, 3)}
        if isinstance(error, Refused):
            failure["failure_code"] = str(error)
        if isinstance(error, OSError) and type(error.errno) is int and 0 <= error.errno <= 4095:
            failure["os_errno"] = error.errno
            if isinstance(error.filename, str):
                basename = Path(error.filename).name
                if basename in {"source.tgz", "source-inventory.json", "config.json", "frontend-summary.json",
                                "homecircle-card.js", "LEAFLET-LICENSE.txt", "driver.py", "homecircle.zip", "inventory.json", "requirements_support.py"}:
                    failure["input_basename"] = basename
        frames = []
        for frame, line in traceback.walk_tb(error.__traceback__):
            code = frame.f_code
            if code.co_filename == __file__ and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,79}", code.co_name):
                frames.append({"function": code.co_name, "line": line})
        failure["driver_frames"] = frames[-6:]
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
