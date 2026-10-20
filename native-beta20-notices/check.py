"""Linux-only, stdlib-only notice-candidate package validation; never install it."""

import sys
import platform

if sys.platform != "linux" or platform.machine() != "x86_64":
    raise SystemExit("Notice archive validation requires Linux x86_64.")

import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import ssl
import subprocess
import tempfile
import urllib.parse
import urllib.request

BASELINE = "d02a9bdb9027cb51c99165a09ba50d5b175f5fb9"
CONFIG_SHA256 = "5054d26097e12cc312dbca4c093a40c17e86834f7ee1129d2d20fd01eb1dae83"
ZIP_URL = "https://github.com/jmhjr/HomeCircle/releases/download/v0.1.0-beta.20/homecircle.zip"
ZIP_SHA256 = "fc0b365d9688459504f874af5c38393e24145d657f15f1def8ada9184f363285"
INTEGRATION = "custom_components/homecircle/"
ALLOWED = {
    INTEGRATION + "_vendor_findmy/LICENSE.md": "M",
    INTEGRATION + "_vendor_findmy/README.md": "M",
    INTEGRATION + "_findmy_runtime/PROVENANCE.md": "M",
    INTEGRATION + "_findmy_runtime/LICENSE.md": "A",
    "tests/fixtures/findmy_0102_gsa_reference.provenance.md": "M",
}
GENERATED = {"frontend/homecircle-card.js", "frontend/LEAFLET-LICENSE.txt"}
HELPERS = {
    "build_release": "0c1ac7f979817bd5fc2cd4a4101571931488d6972bc6f181a26ac21edcf8c7d0",
    "validate_release": "20c0466b4fa70a83c5f282bfcd07b0d2e6f5a3a1a09bf90072649441b2ad7f37",
    "validate_ha_restart": "3714a31ea0f87b8c77086a4a28a3a4e93a396d3359dacd87ec6d2a0e7eeb3519",
}
NOTICE_PINS = {
    "findmy": "51396fd82204e1d844bbff2019054d8c3712e53c3ed8485c9f19dd73990eb46e",
    "opentagviewer": "e5d3404f06c194c08bfd18bfe4d42ece466f28098177b38c14aeb2bfe6b39597",
    "emulator": "d13de33ca644eb1350ca7ab815075d2499621f24dad01ee9be532360934483d6",
    "grandslam": "002c2696d92b5c8cf956c11072baa58eaf9f6ade995c031ea635c6a1ee342ad1",
    "unicorn_gpl": "6f04ae8364d0079a192b14635f4b1da294ce18724c034c39a6a41d1b09df6100",
    "construct_mit": "f8d0c347a0dcc6ebe1671640dfae8d2411b6ded892e06a6764f8208b218b2af4",
}
NOTICE_MEMBERS = {
    "findmy": "_vendor_findmy/LICENSE.md",
    "opentagviewer": "_vendor_findmy/LICENSE.md",
    "grandslam": "_vendor_findmy/LICENSE.md",
    "emulator": "_findmy_runtime/emulator/LICENSE",
    "unicorn_gpl": "_findmy_runtime/LICENSE.md",
    "construct_mit": "_findmy_runtime/LICENSE.md",
}
FIXTURE = "tests/fixtures/findmy_0102_gsa_reference.py"
FIXTURE_SHA = "059fb9d6f6b9dfcc813961db6435e3bf71b21e782bdf47dacf2be8def94b4705"


class Refused(ValueError):
    """A fixed public failure code; do not expose command/network exceptions."""


def require(condition, code):
    if not condition:
        raise Refused(code)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(repo, *args):
    result = subprocess.run(
        ["git", "-C", str(repo), *args], check=False, capture_output=True,
        timeout=30, env={"PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"},
    )
    require(result.returncode == 0, "git_input_refused")
    require(len(result.stdout) <= 32 * 1024**2, "git_output_bound")
    return result.stdout


def tree(repo, revision):
    records = {}
    for row in git(repo, "ls-tree", "-rz", "--full-tree", revision).split(b"\0"):
        if not row:
            continue
        header, raw_path = row.split(b"\t", 1)
        mode, kind, blob = header.decode("ascii").split()
        name = raw_path.decode("utf-8")
        path = PurePosixPath(name)
        require(not path.is_absolute() and path.as_posix() == name, "source_path_refused")
        require(all(part not in {".", ".."} for part in path.parts), "source_path_refused")
        require("\\" not in name and "\x00" not in name, "source_path_refused")
        require(kind == "blob" and mode in {"100644", "100755"}, "source_mode_refused")
        require(name not in records, "duplicate_source_path")
        records[name] = (mode, blob)
    return records


def blob(repo, revision, name):
    return git(repo, "show", f"{revision}:{name}")


class PublicReleaseRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlsplit(newurl)
        require(
            parsed.scheme == "https"
            and parsed.hostname in {"github.com", "release-assets.githubusercontent.com"}
            and parsed.port in {None, 443}
            and parsed.username is None and parsed.password is None,
            "release_redirect_refused",
        )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_release():
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), PublicReleaseRedirects(),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
    )
    request = urllib.request.Request(ZIP_URL, headers={"User-Agent": "HomeCircle-notice-archive-check"})
    with opener.open(request, timeout=30) as response:
        require(response.status == 200, "release_download_status")
        body = response.read(604938)
    require(len(body) == 604937 and digest(body) == ZIP_SHA256, "published_zip_pin_mismatch")
    return body


def read_config(path, expected_sha):
    require(re.fullmatch(r"[0-9a-f]{64}", expected_sha), "config_digest_missing")
    raw = path.read_bytes()
    require(len(raw) <= 128 * 1024 and digest(raw) == expected_sha, "config_digest_mismatch")
    config = json.loads(raw)
    require(config["schema"] == 1 and config["baseline_revision"] == BASELINE, "config_baseline_refused")
    require(re.fullmatch(r"[0-9a-f]{40}", config["candidate_revision"]), "candidate_revision_missing")
    files = config["candidate_files"]
    require(set(files) == set(ALLOWED), "config_paths_refused")
    for name, record in files.items():
        require(record["status"] == ALLOWED[name], "config_status_refused")
        require(re.fullmatch(r"[0-9a-f]{64}", record["sha256"]), "candidate_file_pin_missing")
        require(type(record["bytes"]) is int and 0 < record["bytes"] < 128 * 1024, "candidate_file_size_refused")
    require(set(config["notice_materials"]) == set(NOTICE_PINS), "notice_set_refused")
    for name, text in config["notice_materials"].items():
        require(type(text) is str and digest(text.encode()) == NOTICE_PINS[name], "notice_material_pin_mismatch")
    return config


def sha256_call(node, variable):
    return (
        isinstance(node, ast.Call) and not node.args and not node.keywords
        and isinstance(node.func, ast.Attribute) and node.func.attr == "hexdigest"
        and isinstance(node.func.value, ast.Call)
        and isinstance(node.func.value.func, ast.Attribute)
        and isinstance(node.func.value.func.value, ast.Name)
        and node.func.value.func.value.id == "hashlib"
        and node.func.value.func.attr == "sha256"
        and len(node.func.value.args) == 1 and not node.func.value.keywords
        and isinstance(node.func.value.args[0], ast.Name)
        and node.func.value.args[0].id == variable
    )


def inspect_fixture_provenance(body):
    snippets = re.findall(r"```python\n(.*?)\n```", body.decode(), flags=re.S)
    require(len(snippets) == 1, "fixture_snippet_count")
    parsed = ast.parse(snippets[0])  # Parse only: never execute the network snippet.
    assertions = [node.test for node in ast.walk(parsed) if isinstance(node, ast.Assert)]
    retained_digest = any(
        isinstance(test, ast.Compare) and sha256_call(test.left, "wheel_notice")
        and len(test.ops) == len(test.comparators) == 1 and isinstance(test.ops[0], ast.Eq)
        and isinstance(test.comparators[0], ast.Constant)
        and test.comparators[0].value == NOTICE_PINS["findmy"]
        for test in assertions
    )
    retained_prefix = any(
        isinstance(test, ast.Call) and isinstance(test.func, ast.Attribute)
        and isinstance(test.func.value, ast.Name) and test.func.value.id == "combined_notice"
        and test.func.attr == "startswith" and len(test.args) == 1 and not test.keywords
        and isinstance(test.args[0], ast.Name) and test.args[0].id == "wheel_notice"
        for test in assertions
    )
    require(retained_digest and retained_prefix, "fixture_notice_assertion_missing")
    return {"parsed_only": True, "wheel_notice_sha256_asserted": True, "original_notice_prefix_asserted": True}


def load_helpers(source):
    scripts = source / "scripts"
    for module, expected in HELPERS.items():
        require(digest((scripts / f"{module}.py").read_bytes()) == expected, "helper_pin_mismatch")
        require(module not in sys.modules, "helper_module_preloaded")
    previous_path = list(sys.path)
    sys.path.insert(0, str(scripts))
    loaded = {}
    try:
        for name in ("build_release", "validate_release"):
            spec = importlib.util.spec_from_file_location(name, scripts / f"{name}.py")
            require(spec is not None and spec.loader is not None, "helper_import_refused")
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            loaded[name] = module
        for name in HELPERS:
            require(Path(sys.modules[name].__file__).resolve() == scripts / f"{name}.py", "helper_origin_mismatch")
        require(not any(name == "homeassistant" or name.startswith("homeassistant.") for name in sys.modules), "unexpected_core_import")
    finally:
        sys.path[:] = previous_path
    return loaded["build_release"], loaded["validate_release"]


def validate(config, repo, scratch):
    candidate = config["candidate_revision"]
    require(git(repo, "rev-parse", "--verify", f"{candidate}^{{commit}}").decode().strip() == candidate, "candidate_commit_mismatch")
    require(git(repo, "rev-parse", "--verify", "refs/tags/v0.1.0-beta.20^{commit}").decode().strip() == BASELINE, "release_tag_moved")
    git(repo, "merge-base", "--is-ancestor", BASELINE, candidate)
    before, after = tree(repo, BASELINE), tree(repo, candidate)
    require(len(before) == 327 and len(after) == 328, "source_file_count")
    changed = {name for name in set(before) | set(after) if before.get(name) != after.get(name)}
    require(changed == set(ALLOWED), "source_scope_exceeded")
    source = scratch / "candidate"
    source.mkdir()
    source_bytes = {}
    for name, (mode, _) in after.items():
        content = blob(repo, candidate, name)
        require(len(content) <= 16 * 1024**2, "source_member_size")
        if name in ALLOWED:
            pin = config["candidate_files"][name]
            status = "M" if name in before else "A"
            require(mode == "100644" and status == pin["status"], "candidate_mode_or_status")
            require(len(content) == pin["bytes"] and digest(content) == pin["sha256"], "candidate_file_pin_mismatch")
            content.decode("utf-8")
            require(b"\x00" not in content, "candidate_text_refused")
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        target.chmod(int(mode, 8) & 0o777)
        source_bytes[name] = content
    require(digest(source_bytes[FIXTURE]) == FIXTURE_SHA, "fixture_bytes_changed")
    fixture_receipt = inspect_fixture_provenance(source_bytes["tests/fixtures/findmy_0102_gsa_reference.provenance.md"])
    build, inspect = load_helpers(source)
    published = scratch / "published.zip"
    published.write_bytes(download_release())
    original = inspect.inspect_archive(published)
    require(len(original) == 112, "published_member_count")
    target = source / "custom_components/homecircle"
    for name in GENERATED:
        require(INTEGRATION + name not in after, "generated_source_unexpected")
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(original[name])
    payload = build.collect_payload(target, source / "LICENSE")
    require(len(payload) == 113, "preview_member_count")
    package_changes = {name for name in set(original) | set(payload) if original.get(name) != payload.get(name)}
    expected_changes = {name.removeprefix(INTEGRATION) for name in ALLOWED if name.startswith(INTEGRATION)}
    require(package_changes == expected_changes, "package_scope_exceeded")
    require(set(payload) - set(original) == {"_findmy_runtime/LICENSE.md"} and not (set(original) - set(payload)), "package_addition_scope")
    require(sum(original.get(name) == body for name, body in payload.items()) == 109, "unchanged_member_count")
    require(payload["_vendor_findmy/LICENSE.md"].startswith(original["_vendor_findmy/LICENSE.md"]), "original_combined_notice_modified")
    for name, text in config["notice_materials"].items():
        require(payload[NOTICE_MEMBERS[name]].count(text.encode()) == 1, "full_upstream_notice_missing_or_duplicated")
    previews = []
    reports = []
    for number in (1, 2):
        output = scratch / f"preview-{number}"
        archive, report = build.write_archive(payload, output)
        require(inspect.inspect_archive(archive, output / "inventory.json") == payload, "preview_archive_inspection")
        previews.append(archive.read_bytes())
        reports.append((output / "inventory.json").read_bytes())
    require(previews[0] == previews[1] and reports[0] == reports[1], "preview_not_deterministic")
    require(json.loads(payload["manifest.json"])["version"] == "0.1.0-beta.20", "preview_version_changed")
    for name in HELPERS:
        require(digest((source / "scripts" / f"{name}.py").read_bytes()) == HELPERS[name], "helper_changed_after_import")
    return {
        "outcome": "passed", "baseline_revision": BASELINE, "candidate_revision": candidate,
        "source_files_before": 327, "source_files_after": 328,
        "source_changed_paths": sorted(changed), "only_five_text_files_changed": True,
        "published_zip_sha256": ZIP_SHA256, "published_members": 112, "preview_members": 113,
        "package_changed_paths": sorted(package_changes), "unchanged_package_members": 109,
        "all_executable_config_frontend_and_fixture_bytes_unchanged": True,
        "preview_deterministic_within_run": True, "preview_sha256": digest(previews[0]),
        "preview_bytes": len(previews[0]), "helpers_unchanged": HELPERS,
        "full_notice_sha256": NOTICE_PINS, "fixture_provenance": fixture_receipt,
        "preview_uploaded_or_installed": False, "provider_or_apple_calls": False,
        "core_started": False, "production_configuration_used": False,
    }, json.loads(reports[0])


def main():
    require(sys.platform == "linux" and platform.machine() == "x86_64", "linux_x86_64_required")
    require(sys.version_info[:2] == (3, 12), "python_312_required")
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    parser.add_argument("--config-sha256", default=CONFIG_SHA256)
    parser.add_argument("--output", type=Path, default=Path.cwd() / "notice-check-results")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    summary = {"schema": 1, "outcome": "failed", "failure_code": "unexpected_failure", "temporary_preview_removed": False}
    inventory = {"schema": 1, "outcome": "incomplete"}
    try:
        config = read_config(args.config, args.config_sha256)
        with tempfile.TemporaryDirectory(prefix="homecircle-notice-preview-") as temporary:
            summary, inventory = validate(config, args.repo.resolve(), Path(temporary))
            summary["temporary_preview_removed"] = False
        require(not Path(temporary).exists(), "temporary_preview_cleanup")
        summary.update({
            "schema": 1, "config_sha256": args.config_sha256, "temporary_preview_removed": True,
            "host": {"sys_platform": sys.platform, "system": platform.system(),
                     "machine": platform.machine(), "python": platform.python_version(),
                     "implementation": platform.python_implementation()},
            "acceptance_scope": "notice-only unversioned preview; not release or install acceptance",
        })
    except Refused as error:
        summary["outcome"] = "failed"
        summary["failure_code"] = str(error)
    except Exception:
        summary["outcome"] = "failed"
        summary["failure_code"] = "unexpected_failure"
    finally:
        for name, value in (("summary.json", summary), ("inventory.json", inventory)):
            (args.output / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    print("Notice archive validation: " + summary["outcome"])
    return 0 if summary["outcome"] == "passed" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Refused:
        raise SystemExit("Notice archive validation refused before execution.")
