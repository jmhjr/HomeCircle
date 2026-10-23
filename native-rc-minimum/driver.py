"""Exact development preview: native minimum-Core focused tests and four Core processes."""

import argparse
import ast
import asyncio
import fcntl
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import platform
import re
import shutil
import signal
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
SOURCE_COMMIT = 'c7b31c5a82431a6b16d8b7208f9423626b95bd4b'
SOURCE_CONFIG_SHA = 'ac7cc366445c143f9942c771b601256ec85708ebcb5e8530d93ed6e95a88ef12'
SUPPORT_SHA = 'f6c7554aaa33e3e7c220e5f2cbc645e6bc9115791af9ffd777b038abc868e15d'
CORE = "2026.9.4"
PYTHON = "3.14.6"
CONSTRAINTS_SHA = "962c9ccaf398e0b92b10ac9f765ac0f17e22238adc4e768deebc051ee8b60651"
RELEASE_SHA = '4f94a18e2f7862e9bd7f4c85250e5f10e4b8e1292ea9d7b263b441d2e1b77dd9'
INVENTORY_SHA = 'e4bc34e3921e75157402cf643f87ed658d95c76505a448abb393fd90a304db12'
STARTUP_SHA = '3714a31ea0f87b8c77086a4a28a3a4e93a396d3359dacd87ec6d2a0e7eeb3519'
VALIDATOR_SHA = '20c0466b4fa70a83c5f282bfcd07b0d2e6f5a3a1a09bf90072649441b2ad7f37'
VERSION = '1.0.0-rc.1'
PHASES = ("create", "restart", "remove", "removed")
TESTS = {'tests/test_activity.py::test_changes_only_and_report_time_separate_from_observation': 1, 'tests/test_activity.py::test_retention_cap_and_source_projection': 1, 'tests/test_activity.py::test_reload_keeps_history_but_starts_new_observation_boundary': 1, 'tests/test_activity.py::test_load_allowlists_fields_members_and_values': 1, 'tests/test_activity.py::test_failed_load_disables_persistence_without_overwrite': 1, 'tests/test_activity.py::test_withheld_position_clears_map_source_and_does_not_publish_coordinates': 1, 'tests/test_activity.py::test_quiet_retention_cleanup_is_scheduled_without_new_events': 1, 'tests/test_activity.py::test_close_ignores_late_request_results_and_state_callbacks': 1, 'tests/test_activity.py::test_freshness_churn_preserves_arrivals_requests_and_reload': 1, 'tests/test_activity.py::test_total_cap_evicts_freshness_before_significant_events': 1, 'tests/test_activity.py::test_arrival_survives_reload_retention_and_detects_gap_changes': 1, 'tests/test_activity.py::test_arrival_unknown_initial_place_and_changed_place_during_restart': 1, 'tests/test_activity.py::test_arrival_load_allowlists_private_fields_and_rejects_invalid_state': 1, 'tests/test_activity.py::test_unavailable_gap_preserves_checkpoint_but_does_not_invent_new_arrival': 1, 'tests/test_activity.py::test_reload_away_baseline_allows_the_next_observed_arrival': 1, 'tests/test_activity.py::test_unversioned_startup_checkpoints_are_not_treated_as_arrivals': 1, 'tests/test_activity_projection.py::test_projected_item_observes_named_place_without_losing_saved_history': 1, 'tests/test_activity_projection.py::test_projected_item_and_original_member_history_survive_next_restart': 1, 'tests/test_activity_projection.py::test_changed_saved_selection_still_invalidates_prior_projected_history': 1, 'tests/test_activity_projection.py::test_setup_projects_new_item_before_loading_and_observing_activity': 1}


class Refused(RuntimeError):
    pass


def check(condition, code):
    if not condition:
        raise Refused(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path, expected=None, maximum=64 * 1024**2):
    check(
        path.is_file() and not path.is_symlink() and path.stat().st_size <= maximum,
        "input_type_refused",
    )
    value = path.read_bytes()
    check(expected is None or sha(value) == expected, "input_hash_refused")
    return value


def load_module(name, path, expected):
    read(path, expected)
    spec = importlib.util.spec_from_file_location(name, path)
    check(spec is not None and spec.loader is not None, "helper_import_refused")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


support = load_module(
    "minimum_package_support", HERE / "package_support.py", SUPPORT_SHA
)


def literal_codes(path):
    allowed = set()
    for node in ast.walk(ast.parse(path.read_bytes())):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        index = {"check": 1, "Refused": 0}.get(node.func.id)
        if index is not None and len(node.args) > index:
            value = node.args[index]
            if (
                isinstance(value, ast.Constant)
                and isinstance(value.value, str)
                and re.fullmatch(r"[a-z_]{1,100}", value.value)
            ):
                allowed.add(value.value)
    return allowed


SAFE_CODES = literal_codes(Path(__file__)) | literal_codes(HERE / "package_support.py")
SAFE_FAILURE_TYPES = {
    "Refused",
    "AssertionError",
    "TimeoutExpired",
    "ModuleNotFoundError",
    "OSError",
    "ValueError",
    "CancelledError",
    "OtherError",
}


def project_failure(value):
    result = {}
    if value.get("failure_type") in SAFE_FAILURE_TYPES:
        result["failure_type"] = value["failure_type"]
    if value.get("failure_code") in SAFE_CODES:
        result["failure_code"] = value["failure_code"]
    if value.get("mode") in {"prepare", "setup", "acceptance", "startup-child"}:
        result["mode"] = value["mode"]
    if value.get("focused_selector") in TESTS:
        result["focused_selector"] = value["focused_selector"]
    return result


def refusal_code(error, requirements=None):
    types = (Refused, support.Refused)
    if requirements is not None:
        types += (requirements.Refused,)
    if isinstance(error, types) and str(error) in SAFE_CODES:
        return str(error)
    return None


def configuration(path, expected):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            check(key not in result, "duplicate_pin_key_refused")
            result[key] = value
        return result

    value = json.loads(read(path, expected, 64 * 1024), object_pairs_hook=unique)
    fields = {
        "schema",
        "architecture",
        "machine",
        "image_repository",
        "image_digest",
        "image_id",
        "driver_sha256",
        "requirements_support_sha256",
    }
    check(
        isinstance(value, dict)
        and set(value) == fields
        and type(value["schema"]) is int
        and value["schema"] == 1,
        "pins_schema_refused",
    )
    arch = value["architecture"]
    check(
        arch in {"amd64", "arm64"}
        and value["machine"] == {"amd64": "x86_64", "arm64": "aarch64"}[arch],
        "architecture_refused",
    )
    check(
        value["image_repository"]
        == "ghcr.io/home-assistant/"
        + {"amd64": "qemux86-64-homeassistant", "arm64": "qemuarm-64-homeassistant"}[
            arch
        ],
        "image_repository_refused",
    )
    for key in ("image_digest", "image_id"):
        check(
            isinstance(value[key], str)
            and re.fullmatch(r"sha256:[0-9a-f]{64}", value[key]),
            "image_pin_refused",
        )
    for key in ("driver_sha256", "requirements_support_sha256"):
        check(
            isinstance(value[key], str) and re.fullmatch(r"[0-9a-f]{64}", value[key]),
            "helper_pin_refused",
        )
    check(
        sha(Path(__file__).read_bytes()) == value["driver_sha256"],
        "driver_hash_refused",
    )
    return value


def payload(args, pins):
    source = support.load_pins(args.payload / "source-config.json", SOURCE_CONFIG_SHA)
    check(
        source["candidate_source_commit"] == SOURCE_COMMIT
        and source["source_files"] == 402,
        "source_scope_refused",
    )
    support.configure(source)
    files = support.inputs(args.payload)
    check(
        sha(files["scripts/validate_ha_restart.py"]) == STARTUP_SHA
        and sha(files["scripts/validate_release.py"]) == VALIDATOR_SHA,
        "canonical_helper_refused",
    )
    read(args.payload / "homecircle.zip", RELEASE_SHA)
    read(args.payload / "inventory.json", INVENTORY_SHA)
    requirements = load_module(
        "minimum_requirements_support",
        HERE / "requirements_support.py",
        pins["requirements_support_sha256"],
    )
    SAFE_CODES.update(literal_codes(HERE / "requirements_support.py"))
    return files, requirements


def runtime(pins):
    check(
        sys.platform == "linux" and platform.machine() == pins["machine"],
        "native_runtime_refused",
    )
    check(
        platform.python_version() == PYTHON
        and importlib.metadata.version("homeassistant") == CORE,
        "core_python_refused",
    )
    spec = importlib.util.find_spec("homeassistant")
    check(
        spec is not None
        and spec.origin is not None
        and Path(spec.origin).resolve()
        == Path("/usr/src/homeassistant/homeassistant/__init__.py"),
        "core_origin_refused",
    )
    path = Path(spec.origin).with_name("package_constraints.txt")
    read(path, CONSTRAINTS_SHA)
    return path


def tools(args, files):
    support.source_unchanged(files, args.tree)
    sys.path.insert(0, str(args.tree / "scripts"))
    module = load_module(
        "minimum_exact_release",
        args.tree / "scripts/validate_release.py",
        VALIDATOR_SHA,
    )
    body = module.inspect_archive(
        args.payload / "homecircle.zip", args.payload / "inventory.json"
    )
    check(
        len(body) == 112 and json.loads(body["manifest.json"])["version"] == VERSION,
        "package_scope_refused",
    )
    for name, content in body.items():
        if name in {"frontend/homecircle-card.js", "frontend/LEAFLET-LICENSE.txt"}:
            continue
        source_name = (
            "LICENSE" if name == "LICENSE" else "custom_components/homecircle/" + name
        )
        check(files.get(source_name) == content, "package_source_refused")
    return module, body


def exact_installed(target, body):
    check(target.is_dir() and not target.is_symlink(), "installed_root_refused")
    actual = {}
    for path in target.rglob("*"):
        check(not path.is_symlink(), "installed_link_refused")
        if path.is_file() and "__pycache__" not in path.parts:
            actual[path.relative_to(target).as_posix()] = path.read_bytes()
    check(actual == body, "installed_package_bytes_refused")


def install(target, body):
    check(
        not target.exists() and not target.is_symlink(), "fresh_installed_tree_required"
    )
    target.mkdir(mode=0o700, parents=True)
    for name, content in body.items():
        path = target / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_bytes(content)
    exact_installed(target, body)


def technical_versions():
    observed = {name: importlib.metadata.version(name) for name in ("cryptography", "srp", "unicorn")}
    check(observed == {"cryptography": "48.0.1", "srp": "1.0.22", "unicorn": "2.1.4"}, "technical_dependency_version_refused")
    return observed


def common_receipt(pins):
    return {
        "schema": 1,
        "candidate_source_commit": SOURCE_COMMIT,
        "release_sha256": RELEASE_SHA,
        "release_inventory_sha256": INVENTORY_SHA,
        "release_files": 112,
        "version": VERSION,
        "release_candidate_validation": True,
        "release_published": False,
        "core": CORE,
        "python": PYTHON,
        "machine": pins["machine"],
        "architecture": pins["architecture"],
        "constraints_sha256": CONSTRAINTS_SHA,
        "owner_accounts_used": False,
        "native_apple_worker_executed": False,
        "hacs_delivery_tested": False,
        "technical_dependency_versions": technical_versions(),
    }


def setup(args, pins, files, requirements):
    constraint = runtime(pins)
    support.extract(files, args.tree)
    _, body = tools(args, files)
    target = args.tree / "custom_components/homecircle/frontend"
    target.mkdir(mode=0o700, parents=True, exist_ok=True)
    for name in support.FRONTEND:
        (target / name).write_bytes(body["frontend/" + name])
    preparation = requirements.core_component_requirements(body)
    wanted = sorted(
        set(
            support.REQUIREMENTS
            + preparation["requirements"]
            + ["pytest-homeassistant-custom-component==0.13.367"]
        )
    )
    command = [
        "uv",
        "pip",
        "install",
        "--system",
        "--no-config",
        "--index-url",
        "https://pypi.org/simple",
        "--index-strategy",
        "unsafe-first-match",
        "--constraint",
        str(constraint),
        *wanted,
    ]
    check(
        support.run_owned(
            command,
            cwd=args.tree,
            log=args.results / "dependencies-private.log",
            limit=660,
        )
        == 0,
        "dependency_preparation_refused",
    )
    check(
        importlib.metadata.version("pytest-homeassistant-custom-component")
        == "0.13.367",
        "pytest_core_mismatch",
    )
    installed = support.closure(runtime(pins))
    declared = requirements.verify_declared_versions(preparation["requirements"])
    support.source_unchanged(files, args.tree)
    support.atomic_json(
        args.results / "setup-summary.json",
        {
            **common_receipt(pins),
            "outcome": "passed",
            "completed": True,
            "installed_dependency_closure": installed,
            "core_requirement_preparation": preparation,
            "startup_requirement_versions": declared,
        },
    )


def focused_result(path):
    check(
        path.is_file() and not path.is_symlink() and path.stat().st_size <= 2 * 1024**2,
        "junit_type_refused",
    )
    cases = list(ET.parse(path).getroot().iter("testcase"))
    counts, identities = {}, set()
    for case in cases:
        klass, name = case.attrib.get("classname", ""), case.attrib.get("name", "")
        check((klass, name) not in identities, "duplicate_junit_case_refused")
        identities.add((klass, name))
        base = name.split("[", 1)[0]
        key = klass.replace(".", "/") + ".py::" + base
        if klass == "tests.test_privacy_guard.PrivacyGuardTests":
            key = "tests/test_privacy_guard.py::PrivacyGuardTests::" + base
        check(key in TESTS, "unexpected_focused_test_refused")
        if any(case.find(tag) is not None for tag in ("error", "failure", "skipped")):
            error = Refused("focused_test_failed_or_skipped")
            error.focused_selector = key
            raise error
        counts[key] = counts.get(key, 0) + 1
    check(counts == TESTS, "missing_focused_case_refused")
    return {
        "passed": len(cases),
        "failed": 0,
        "skipped": 0,
        "cases_per_selector": counts,
        "full_backend_suite_repeated": False,
    }


def saved_identity(config):
    def stored(name):
        path = config / ".storage" / name
        return json.loads(read(path, maximum=2 * 1024**2))["data"]

    entries = [
        entry
        for entry in stored("core.config_entries")["entries"]
        if entry["domain"] == "homecircle"
    ]
    check(len(entries) == 1, "saved_entry_identity_refused")
    entry = entries[0]
    selected = {
        key: entry.get(key)
        for key in (
            "entry_id",
            "unique_id",
            "version",
            "minor_version",
            "data",
            "options",
        )
    }
    check(bool(entry.get("options")), "nonempty_options_required")
    resources = [
        {key: item.get(key) for key in ("url", "res_type")}
        for item in stored("lovelace_resources")["items"]
    ]
    resources.sort(key=lambda item: item["url"])
    check(
        any(item["url"] == "/local/example_unrelated.js" for item in resources),
        "unrelated_resource_missing",
    )
    check(
        any(
            item["url"].startswith("/homecircle_static/homecircle-card.js?")
            for item in resources
        ),
        "owned_resource_missing",
    )

    def digest(value):
        return sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())

    return {
        "saved_entry_settings_source_identity_sha256": digest(selected),
        "resource_url_type_semantics_sha256": digest(resources),
        "resource_id_persistence_claimed": False,
        "nonempty_options": True,
    }


def startup_child(args, pins, files, requirements):
    runtime(pins)
    _, body = tools(args, files)
    check(
        args.config is not None
        and args.config.is_dir()
        and not args.config.is_symlink()
        and args.config.parent.resolve() == args.results.resolve()
        and args.config.name.startswith("core-private-"),
        "owned_configuration_required",
    )
    target = args.config / "custom_components/homecircle"
    sys.path.insert(0, str(args.config))
    if args.phase == "removed":
        check(not target.exists(), "removed_package_still_present")
        validator, _ = tools(args, files)
        asyncio.run(validator.check_removed(str(args.config)))
        result = {
            "removed_entry_and_static_bundle_absent": True,
            "unrelated_resource_preserved": True,
        }
    else:
        exact_installed(target, body)
        startup = load_module(
            "current_exact_startup",
            args.tree / "scripts/validate_ha_restart.py",
            STARTUP_SHA,
        )
        asyncio.run(
            startup.run_phase(
                str(args.config), args.phase, VERSION, args.phase == "remove"
            )
        )
        import custom_components.homecircle as integration
        from custom_components.homecircle import frontend

        check(
            Path(integration.__file__).resolve() == (target / "__init__.py").resolve()
            and frontend.VERSION == VERSION,
            "loaded_module_origin_or_version_refused",
        )
        for name in ("normalize", "city_lookup", "frontend"):
            module = __import__("custom_components.homecircle." + name, fromlist=[name])
            check(
                Path(module.__file__).resolve() == (target / (name + ".py")).resolve(),
                "changed_module_origin_refused",
            )
            read(Path(module.__file__), sha(body[name + ".py"]))
        exact_installed(target, body)
        result = {
            "exact_module_and_112_files": True,
            "canonical_reload_unload_setup": True,
            "served_exact_frontend": True,
            "served_frontend_sha256": sha(body["frontend/homecircle-card.js"]),
        }
        if args.phase in {"create", "restart"}:
            result["saved_identity"] = saved_identity(args.config)
        else:
            result["entry_removed_and_activity_deleted"] = True
    support.source_unchanged(files, args.tree)
    support.atomic_json(
        args.receipt,
        {**common_receipt(pins), "phase": args.phase, "outcome": "passed", **result},
    )


def acceptance(args, pins, files, requirements):
    runtime(pins)
    _, body = tools(args, files)
    setup_receipt = json.loads(
        read(args.results / "setup-summary.json", maximum=2 * 1024**2)
    )
    check(
        setup_receipt.get("outcome") == "passed"
        and setup_receipt.get("release_sha256") == RELEASE_SHA,
        "setup_receipt_required",
    )
    check(
        support.closure(runtime(pins)) == setup_receipt["installed_dependency_closure"],
        "runtime_dependency_changed",
    )
    check(
        requirements.core_component_requirements(body)
        == setup_receipt["core_requirement_preparation"],
        "startup_graph_changed",
    )
    check(
        requirements.verify_declared_versions(
            setup_receipt["core_requirement_preparation"]["requirements"]
        )
        == setup_receipt["startup_requirement_versions"],
        "startup_versions_changed",
    )
    with (args.results / "lifecycle.lock").open("xb") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        xml = args.results / "focused-private.xml"
        command = [sys.executable, "-B", "-m", "pytest", "--junitxml", str(xml), *TESTS]
        code = support.run_owned(
            command, cwd=args.tree, log=args.results / "focused-private.log", limit=180
        )
        focused = focused_result(xml)
        check(code == 0, "focused_child_refused")
        phases = []
        with tempfile.TemporaryDirectory(
            prefix="core-private-", dir=args.results
        ) as directory:
            config = Path(directory)
            install(config / "custom_components/homecircle", body)
            for phase in PHASES:
                receipt = args.results / ("phase-" + phase + ".json")
                command = [
                    sys.executable,
                    "-I",
                    "-B",
                    str(Path(__file__).resolve()),
                    "startup-child",
                    "--payload",
                    str(args.payload),
                    "--tree",
                    str(args.tree),
                    "--results",
                    str(args.results),
                    "--pins",
                    str(args.pins),
                    "--pins-sha",
                    args.pins_sha,
                    "--config",
                    str(config),
                    "--phase",
                    phase,
                    "--receipt",
                    str(receipt),
                ]
                child_code = support.run_owned(
                    command,
                    cwd=config,
                    log=args.results / ("phase-" + phase + "-private.log"),
                    limit=120,
                )
                if child_code != 0:
                    error = Refused("core_phase_child_refused")
                    error.phase = phase
                    if receipt.is_file() and not receipt.is_symlink():
                        error.child_failure = project_failure(
                            json.loads(read(receipt, maximum=2 * 1024**2))
                        )
                    raise error
                value = json.loads(read(receipt, maximum=2 * 1024**2))
                check(
                    value.get("outcome") == "passed"
                    and value.get("phase") == phase
                    and value.get("release_sha256") == RELEASE_SHA,
                    "core_phase_receipt_refused",
                )
                phases.append(value)
                if phase == "remove":
                    shutil.rmtree(config / "custom_components/homecircle")
            check(
                phases[0]["saved_identity"] == phases[1]["saved_identity"],
                "restart_settings_source_identity_changed",
            )
        check(not config.exists(), "owned_configuration_cleanup_refused")
        support.source_unchanged(files, args.tree)
        check(
            support.closure(runtime(pins))
            == setup_receipt["installed_dependency_closure"],
            "final_dependencies_changed",
        )
        support.atomic_json(
            args.results / "lifecycle-summary.json",
            {
                **common_receipt(pins),
                "outcome": "passed",
                "completed": True,
                "focused_tests": focused,
                "phases": phases,
                "separate_core_processes": 4,
                "owned_configuration_removed": True,
                "backend_network_disconnected_required": True,
                "real_core_process_lifecycle": True,
                "managed_haos_service_claimed": False,
                "normal_container_entrypoint_claimed": False,
                "owner_configuration_used": False,
                "upgrade_recovery_repeated": False,
            },
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=("prepare", "setup", "acceptance", "startup-child")
    )
    for name in (
        "payload",
        "tree",
        "results",
        "pins",
        "git-directory",
        "config",
        "receipt",
    ):
        parser.add_argument(
            "--" + name,
            type=Path,
            required=name in {"payload", "tree", "results", "pins"},
        )
    parser.add_argument("--pins-sha", required=True)
    parser.add_argument("--phase", choices=PHASES)
    args = parser.parse_args()
    args.results.mkdir(mode=0o700, parents=True, exist_ok=True)
    started = time.monotonic()
    requirements = None
    try:
        pins = configuration(args.pins, args.pins_sha)
        check(
            sys.platform == "linux" and platform.machine() == pins["machine"],
            "native_linux_host_required",
        )
        files, requirements = payload(args, pins)
        if args.mode == "prepare":
            result = support.verify_git_source(files, args.git_directory)
            support.atomic_json(
                args.results / "source-summary.json",
                {"schema": 1, "outcome": "passed", **result},
            )
        elif args.mode == "setup":
            setup(args, pins, files, requirements)
        elif args.mode == "acceptance":
            acceptance(args, pins, files, requirements)
        else:
            check(
                args.phase is not None and args.receipt is not None,
                "phase_arguments_required",
            )
            startup_child(args, pins, files, requirements)
    except BaseException as error:
        failure = {
            "schema": 1,
            "outcome": "failed",
            "mode": args.mode,
            "failure_type": type(error).__name__
            if type(error).__name__
            in {
                "Refused",
                "AssertionError",
                "TimeoutExpired",
                "ModuleNotFoundError",
                "OSError",
                "ValueError",
                "CancelledError",
            }
            else "OtherError",
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
        safe_code = refusal_code(error, requirements)
        if safe_code is not None:
            failure["failure_code"] = safe_code
        if getattr(error, "focused_selector", None) in TESTS:
            failure["focused_selector"] = error.focused_selector
        if getattr(error, "phase", None) in PHASES:
            failure["phase"] = error.phase
        if isinstance(getattr(error, "child_failure", None), dict):
            failure["child_failure"] = project_failure(error.child_failure)
        support.atomic_json(
            args.receipt
            if args.mode == "startup-child" and args.receipt is not None
            else args.results / "failure-summary.json",
            failure,
        )
        print(json.dumps(failure), flush=True)
        return 1
    print(json.dumps({"outcome": "passed", "mode": args.mode}), flush=True)
    return 0


if __name__ == "__main__":
    for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(
            signum, lambda _signum, _frame: (_ for _ in ()).throw(InterruptedError())
        )
    raise SystemExit(main())
