"""Independently consume four fixed minimum-Core receipts; no runtime imports."""

import argparse
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
FILES = {"source-summary.json", "setup-summary.json", "lifecycle-summary.json", "host.json"}
CLOSURE_KEYS = set("aiohappyeyeballs aiohttp aiosignal anisette appdirs attrs beautifulsoup4 certifi frozenlist fs idna life360 multidict propcache protobuf pyelftools setuptools six soupsieve srp typing-extensions unicorn urllib3 yarl".split())
PINNED_CLOSURE = {"life360": "7.2.0", "anisette": "1.2.4", "unicorn": "2.1.4", "srp": "1.0.22",
    "beautifulsoup4": "4.13.3", "protobuf": "6.32.0", "aiohttp": "3.14.3", "attrs": "26.1.0",
    "propcache": "0.5.2", "yarl": "1.24.5", "setuptools": "81.0.0"}
MINIMUM_CLOSURE = {"certifi": (2021, 5, 30), "typing-extensions": (4, 16, 0),
                   "urllib3": (2, 0), "multidict": (6, 4, 2)}
COMMON_FIELDS = {"schema", "candidate_source_commit", "release_sha256", "release_inventory_sha256",
    "release_files", "version", "release_candidate_validation", "release_published", "core", "python",
    "machine", "architecture", "constraints_sha256", "owner_accounts_used", "native_apple_worker_executed",
    "hacs_delivery_tested", "technical_dependency_versions"}


class Refused(ValueError):
    pass


def need(value, code):
    if not value:
        raise Refused(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    value = {}
    for key, item in pairs:
        need(key not in value, "duplicate_json_key_refused")
        value[key] = item
    return value


def load(path, expected=None):
    need(path.is_file() and not path.is_symlink() and path.stat().st_size <= 2 * 1024**2, "input_type_refused")
    raw = path.read_bytes()
    need(expected is None or sha(raw) == expected, "input_hash_refused")
    return json.loads(raw, object_pairs_hook=unique), raw


def exact(actual, expected, code):
    # Canonical JSON equality distinguishes integers from booleans recursively.
    need(json.dumps(actual, sort_keys=True, separators=(",", ":"), allow_nan=False)
         == json.dumps(expected, sort_keys=True, separators=(",", ":"), allow_nan=False), code)


def common(control):
    return {"schema": 1, "candidate_source_commit": control["source_commit"],
        "release_sha256": control["archive_sha256"], "release_inventory_sha256": control["inventory_sha256"],
        "release_files": 112, "version": "1.0.0-rc.1", "release_candidate_validation": True,
        "release_published": False, "core": "2026.9.4", "python": "3.14.6", "machine": "x86_64",
        "architecture": "amd64", "constraints_sha256": "962c9ccaf398e0b92b10ac9f765ac0f17e22238adc4e768deebc051ee8b60651",
        "owner_accounts_used": False, "native_apple_worker_executed": False, "hacs_delivery_tested": False,
        "technical_dependency_versions": {"cryptography": "48.0.1", "srp": "1.0.22", "unicorn": "2.1.4"}}


def shape(value, fields, code):
    need(type(value) is dict and set(value) == fields, code)


def bound_common(value, expected, extra):
    shape(value, COMMON_FIELDS | set(extra), "receipt_shape_refused")
    exact({key: value[key] for key in COMMON_FIELDS}, expected, "receipt_binding_refused")


def version(value):
    need(type(value) is str and re.fullmatch(r"[0-9]+(?:[.][0-9]+){0,4}", value) is not None
         and len(value) <= 64, "dependency_version_shape_refused")
    parts = tuple(int(x) for x in value.split("."))
    return parts + (0,) * (5 - len(parts))


def verify(control, receipts, graph, startup):
    expected = common(control)
    exact(receipts["source-summary.json"], {"schema": 1, "outcome": "passed",
        "candidate_source_commit": control["source_commit"], "canonical_commit_blobs_verified": 402,
        "candidate_source_prefix": "", "public_inventory_scope_only": True}, "source_identity_refused")
    setup = receipts["setup-summary.json"]
    bound_common(setup, expected, {"outcome", "completed", "installed_dependency_closure",
        "core_requirement_preparation", "startup_requirement_versions"})
    exact({key: setup[key] for key in ("outcome", "completed")},
          {"outcome": "passed", "completed": True}, "setup_success_refused")
    exact(setup["core_requirement_preparation"], graph, "minimum_core_graph_refused")
    exact(setup["startup_requirement_versions"], startup, "minimum_startup_versions_refused")
    closure = setup["installed_dependency_closure"]
    shape(closure, CLOSURE_KEYS, "dependency_closure_names_refused")
    for name, value in closure.items():
        version(value)
        if name in PINNED_CLOSURE:
            exact(value, PINNED_CLOSURE[name], "dependency_pin_refused")
        if name in MINIMUM_CLOSURE:
            minimum = MINIMUM_CLOSURE[name]
            need(version(value) >= minimum + (0,) * (5 - len(minimum)), "dependency_lower_bound_refused")
    need(version(closure["typing-extensions"]) < (5, 0, 0, 0, 0), "dependency_upper_bound_refused")
    lifecycle = receipts["lifecycle-summary.json"]
    bound_common(lifecycle, expected, {"outcome", "completed", "focused_tests", "phases",
        "separate_core_processes", "owned_configuration_removed", "backend_network_disconnected_required",
        "real_core_process_lifecycle", "managed_haos_service_claimed", "normal_container_entrypoint_claimed",
        "owner_configuration_used", "upgrade_recovery_repeated"})
    exact({key: lifecycle[key] for key in lifecycle if key not in COMMON_FIELDS | {"focused_tests", "phases"}},
        {"outcome": "passed", "completed": True, "separate_core_processes": 4,
         "owned_configuration_removed": True, "backend_network_disconnected_required": True,
         "real_core_process_lifecycle": True, "managed_haos_service_claimed": False,
         "normal_container_entrypoint_claimed": False, "owner_configuration_used": False,
         "upgrade_recovery_repeated": False}, "lifecycle_success_refused")
    exact(lifecycle["focused_tests"], {"passed": 20, "failed": 0, "skipped": 0,
        "cases_per_selector": control["focused_selectors"], "full_backend_suite_repeated": False},
        "focused_exact_cases_refused")
    phases = lifecycle["phases"]
    need(type(phases) is list and len(phases) == 4, "four_phases_required")
    saved = []
    for value, phase in zip(phases, ("create", "restart", "remove", "removed")):
        extra = {"phase", "outcome"}
        result = {"phase": phase, "outcome": "passed"}
        if phase == "removed":
            result.update(removed_entry_and_static_bundle_absent=True, unrelated_resource_preserved=True)
        else:
            result.update(exact_module_and_112_files=True, canonical_reload_unload_setup=True,
                served_exact_frontend=True, served_frontend_sha256=control["frontend_sha256"])
            if phase in ("create", "restart"):
                identity = value.get("saved_identity")
                shape(identity, {"saved_entry_settings_source_identity_sha256", "resource_url_type_semantics_sha256",
                    "resource_id_persistence_claimed", "nonempty_options"}, "saved_identity_shape_refused")
                for key in ("saved_entry_settings_source_identity_sha256", "resource_url_type_semantics_sha256"):
                    need(type(identity[key]) is str and re.fullmatch(r"[0-9a-f]{64}", identity[key]) is not None,
                         "saved_identity_hash_refused")
                exact({key: identity[key] for key in ("resource_id_persistence_claimed", "nonempty_options")},
                    {"resource_id_persistence_claimed": False, "nonempty_options": True}, "saved_identity_flags_refused")
                result["saved_identity"] = identity
                saved.append(identity)
            else:
                result["entry_removed_and_activity_deleted"] = True
        extra.update(result)
        bound_common(value, expected, extra)
        exact({key: value[key] for key in extra}, result, "phase_success_refused")
    exact(saved[0], saved[1], "restart_identity_changed")
    host = receipts["host.json"]
    host_expected = {"schema": 1, "outcome": "passed", "runner_exit": 0, "failure_or_final_stage": "complete",
        "acceptance_actual_exit": 0, "host_elapsed_seconds": host.get("host_elapsed_seconds"),
        "host_system": "Linux", "host_machine": "x86_64", "architecture": "amd64", "host_kernel": host.get("host_kernel"),
        "registry_digest": "sha256:414dce485b4eebd9f929f293f7252340bada5715fc4a48b2b954d79195ed3019",
        "local_image_id": "sha256:560be76a9ee5019c1b557241db8d1127550f21fba952a1a976c3d186f9b2cd9e",
        "pins_sha256": control["pins_sha256"], "driver_sha256": control["driver_sha256"],
        "candidate_source_commit": control["source_commit"], "source_git_verified": True,
        "container_stopped": True, "container_removed": True, "cleanup_failed": False,
        "private_workspace_removed": True, "acceptance_network_disconnected": True,
        "owner_accounts_used": False, "production_configuration_used": False, "hacs_delivery_tested": False,
        "normal_container_entrypoint_claimed": False, "managed_haos_service_claimed": False,
        "full_backend_suite_repeated": False}
    exact(host, host_expected, "host_binding_success_cleanup_refused")
    need(type(host["host_elapsed_seconds"]) in (int, float) and 0 < host["host_elapsed_seconds"] <= 2100,
         "host_deadline_refused")
    need(type(host["host_kernel"]) is str and re.fullmatch(r"[A-Za-z0-9_.+-]{1,120}", host["host_kernel"]) is not None,
         "host_kernel_refused")
    return {"schema": 1, "outcome": "accepted", "scope": "minimum_core_2026_9_4_twenty_tests_four_core_processes",
        "source_commit": control["source_commit"], "source_files": 402, "package_sha256": control["archive_sha256"],
        "package_files": 112, "version": "1.0.0-rc.1", "focused_passed": 20, "failed": 0, "skipped": 0,
        "separate_core_processes": 4, "restart_identity_preserved": True, "offline_execution": True,
        "cleanup_required_and_observed": True, "full_backend_suite_repeated": False,
        "hacs_delivery_tested": False, "managed_haos_service_claimed": False, "provider_account_cases_repeated": False,
        "artifact_transport_verified_by_consumer": False, "owner_accounts_used": False, "release_published": False}


def consume(control_path, expected_sha, results):
    control, _ = load(control_path, expected_sha)
    shape(control, {"schema", "source_commit", "archive_sha256", "inventory_sha256", "driver_sha256",
        "pins_sha256", "frontend_sha256", "focused_selectors", "graph_sha256", "startup_versions_sha256",
        "frozen_inputs"}, "consumer_control_shape_refused")
    exact({key: control[key] for key in ("schema", "source_commit", "archive_sha256", "inventory_sha256")},
        {"schema": 1, "source_commit": "c7b31c5a82431a6b16d8b7208f9423626b95bd4b",
         "archive_sha256": "4f94a18e2f7862e9bd7f4c85250e5f10e4b8e1292ea9d7b263b441d2e1b77dd9",
         "inventory_sha256": "e4bc34e3921e75157402cf643f87ed658d95c76505a448abb393fd90a304db12"},
        "consumer_candidate_binding_refused")
    need(type(control["frozen_inputs"]) is dict and len(control["frozen_inputs"]) == 11, "frozen_input_map_refused")
    for name, fingerprint in control["frozen_inputs"].items():
        need(type(name) is str and not Path(name).is_absolute() and ".." not in Path(name).parts,
             "frozen_input_name_refused")
        path = HERE / "harness" / name
        need(path.is_file() and not path.is_symlink(), "frozen_input_missing")
        raw = path.read_bytes()
        exact({"bytes": len(raw), "sha256": sha(raw)}, fingerprint, "frozen_input_bytes_refused")
    graph, _ = load(HERE / "CORE-GRAPH.json", control["graph_sha256"])
    startup, _ = load(HERE / "STARTUP-VERSIONS.json", control["startup_versions_sha256"])
    need(results.is_dir() and not results.is_symlink() and {path.name for path in results.iterdir()} == FILES,
         "exact_four_receipts_required")
    receipts, fingerprints = {}, {}
    for name in sorted(FILES):
        receipts[name], raw = load(results / name)
        fingerprints[name] = {"bytes": len(raw), "sha256": sha(raw)}
    accepted = verify(control, receipts, graph, startup)
    accepted["receipts"] = fingerprints
    return accepted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--control-sha", required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        accepted = consume(args.control, args.control_sha, args.results)
        need(not args.output.exists() and not args.output.is_symlink() and args.output.parent.is_dir(), "fresh_output_required")
        with args.output.open("xb") as stream:
            stream.write((json.dumps(accepted, indent=2, sort_keys=True) + "\n").encode())
    except (Refused, OSError, ValueError, TypeError, KeyError):
        print(json.dumps({"schema": 1, "outcome": "refused"}))
        return 1
    print(json.dumps({"schema": 1, "outcome": "accepted", "focused_passed": 20}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
