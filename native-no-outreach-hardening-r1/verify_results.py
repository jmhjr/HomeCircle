"""Independent, stdlib-only consumer of narrow affected-provider receipts.

Does not import the producer or product, run tests, or verify GitHub transport.
The caller must independently bind workflow/run/attempt and artifact digest first.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
SCOPE = "native_current_core_affected_provider_pytest_only"
GRAPH_SHA = "55630f755ad3ed451e6ec94499ba8d682e584e2d4d4fcc9ae7f9f88283c9f79d"
CONSTRAINTS = "7baa9a8f39ddeb9c5bb60a1036f6d5e33f4b84267f151f53cc2b95ef031a21b5"
IMAGE_DIGEST = "sha256:45f009d6ff1061971102e81f0802cf2762bdd5c5007231c938bd36030cbd0a12"
IMAGE_ID = "sha256:e1acee126eee45b3007494ad7f806d12535dc7d733624b681ed29a505f8c2b98"
COMMON_FIELDS = {"schema", "scope", "source_commit", "source_sha256", "source_inventory_sha256",
    "source_export_sha256", "source_files", "package_sha256", "package_inventory_sha256", "version",
    "release_files", "core", "full_backend_suite_repeated", "upgrade_validated", "full_managed_core_lifecycle",
    "hacs_delivery_tested", "kvm_used", "owner_accounts_used", "production_configuration_used"}
FLAGS = {"full_backend_suite_repeated", "upgrade_validated", "full_managed_core_lifecycle",
    "hacs_delivery_tested", "kvm_used", "owner_accounts_used", "production_configuration_used"}
FILES = {"source-summary.json", "setup-summary.json", "candidate-summary.json", "focused-diagnostic.json", "host.json"}


class Refused(ValueError):
    """Only fixed failure codes are returned; raw result data stays local."""


def need(value, code):
    if not value:
        raise Refused(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, "duplicate_json_key_refused")
        result[key] = value
    return result


def load(path, expected=None):
    need(path.is_file() and not path.is_symlink() and path.stat().st_size <= 2 * 1024**2,
         "bounded_regular_input_required")
    raw = path.read_bytes()
    need(expected is None or sha(raw) == expected, "input_hash_refused")
    return json.loads(raw, object_pairs_hook=unique), raw


def config_read(path, expected):
    need(type(expected) is str and re.fullmatch(r"[a-f0-9]{64}", expected), "final_config_pin_required")
    config, _ = load(path, expected)
    fields = {"schema", "frozen", "source_commit", "source_files", "source_sha256", "source_inventory_sha256",
        "source_export_sha256", "driver_sha256", "package_sha256", "package_inventory_sha256", "version",
        "release_files", "selected_modules", "expected_functions"}
    need(type(config) is dict and set(config) == fields and type(config["schema"]) is int
         and config["schema"] == 1 and config["frozen"] is True, "frozen_config_required")
    for key, size in (("source_commit", 40), *((key, 64) for key in fields if key.endswith("sha256"))):
        need(type(config[key]) is str and re.fullmatch(r"[a-f0-9]{" + str(size) + "}", config[key]), "config_binding_refused")
    need(type(config["source_files"]) is int and 300 <= config["source_files"] <= 1024
         and type(config["release_files"]) is int and 100 <= config["release_files"] <= 256
         and type(config["version"]) is str and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.]+)?", config["version"]),
         "config_scope_refused")
    modules = config["selected_modules"]
    need(type(modules) is list and 1 <= len(modules) <= 32 and len(set(modules)) == len(modules)
         and all(type(name) is str and re.fullmatch(r"tests/test_[a-z0-9_]+\.py", name) for name in modules),
         "config_modules_refused")
    functions = config["expected_functions"]
    need(type(functions) is list and 1 <= len(functions) <= 2048, "config_functions_refused")
    allowed = {name.removesuffix(".py").replace("/", ".") for name in modules}
    seen = set()
    for item in functions:
        need(type(item) is dict and set(item) == {"class", "function"}
             and type(item["class"]) is str and type(item["function"]) is str
             and ".".join(item["class"].split(".")[:2]) in allowed
             and re.fullmatch(r"tests\.test_[a-z0-9_]+(?:\.[A-Za-z_][A-Za-z0-9_]*)?", item["class"])
             and re.fullmatch(r"test_[A-Za-z0-9_]{1,180}", item["function"]), "config_function_refused")
        identity = (item["class"], item["function"])
        need(identity not in seen, "config_duplicate_function_refused")
        seen.add(identity)
    need(functions == sorted(functions, key=lambda item: (item["class"], item["function"])), "config_function_order_refused")
    return config


def common(config):
    value = {key: config[key] for key in COMMON_FIELDS if key in config}
    value.update(schema=1, scope=SCOPE, core="2026.10.2", **{key: False for key in FLAGS})
    return value


def exact(value, wanted, code):
    # bool and int compare equal in Python; acceptance must preserve JSON types.
    need(type(value) is type(wanted), code)
    if type(wanted) is dict:
        need(set(value) == set(wanted), code)
        for key in wanted:
            exact(value[key], wanted[key], code)
    elif type(wanted) is list:
        need(len(value) == len(wanted), code)
        for actual, expected in zip(value, wanted):
            exact(actual, expected, code)
    else:
        need(value == wanted, code)


def verify(config, config_sha, receipts, graph):
    expected = common(config)
    source = {**expected, "outcome": "passed", "source_git_verified": True,
        "complete_canonical_tree_verified": True}
    exact(receipts["source-summary.json"], source, "source_receipt_refused")
    setup = receipts["setup-summary.json"]
    setup_extra = {"outcome", "completed", "python", "machine", "constraints_sha256",
        "pytest_homeassistant_custom_component", "core_requirement_graph", "startup_requirement_versions",
        "runtime_versions", "source_unchanged"}
    need(type(setup) is dict and set(setup) == COMMON_FIELDS | setup_extra, "setup_shape_refused")
    for key, value in expected.items():
        exact(setup[key], value, "setup_binding_refused")
    for key, value in {"outcome": "passed", "completed": True, "python": "3.14.6", "machine": "x86_64",
                       "constraints_sha256": CONSTRAINTS, "pytest_homeassistant_custom_component": "0.13.373",
                       "source_unchanged": True, "core_requirement_graph": graph}.items():
        exact(setup[key], value, "setup_runtime_or_graph_refused")
    startup = {name.split("[", 1)[0].lower().replace("_", "-"): version
        for declaration in graph["requirements"] for name, version in [declaration.split("==", 1)]}
    exact(setup["startup_requirement_versions"], dict(sorted(startup.items())), "startup_versions_refused")
    versions = setup["runtime_versions"]
    pinned = {"homeassistant": "2026.10.2", "pytest-homeassistant-custom-component": "0.13.373",
        "life360": "7.2.0", "anisette": "1.2.4", "unicorn": "2.1.4", "srp": "1.0.22",
        "beautifulsoup4": "4.13.3", "cryptography": "50.0.1"}
    need(type(versions) is dict and set(versions) == set(pinned) | {"protobuf"}, "runtime_versions_refused")
    for name, version in pinned.items():
        exact(versions[name], version, "runtime_version_pin_refused")
    need(type(versions["protobuf"]) is str and re.fullmatch(r"[67]\.[0-9]+\.[0-9]+", versions["protobuf"]),
         "protobuf_version_refused")
    need(int(versions["protobuf"].split(".")[0]) == 7 or tuple(map(int, versions["protobuf"].split("."))) >= (6, 32, 0),
         "protobuf_version_refused")
    candidate = receipts["candidate-summary.json"]
    candidate_extra = {"outcome", "completed", "passed", "failed", "skipped", "collected_cases_match_junit",
        "selected_base_functions", "selected_base_function_count", "selected_modules", "runtime_versions",
        "core_requirement_graph", "startup_requirement_versions", "source_unchanged"}
    need(type(candidate) is dict and set(candidate) == COMMON_FIELDS | candidate_extra, "candidate_shape_refused")
    for key, value in {**expected, "outcome": "passed", "completed": True, "failed": 0, "skipped": 0,
        "collected_cases_match_junit": True, "selected_modules": config["selected_modules"], "runtime_versions": versions,
        "core_requirement_graph": graph, "startup_requirement_versions": setup["startup_requirement_versions"],
        "source_unchanged": True, "selected_base_function_count": len(config["expected_functions"])}.items():
        exact(candidate[key], value, "candidate_binding_or_success_refused")
    functions = candidate["selected_base_functions"]
    need(type(functions) is list and len(functions) == len(config["expected_functions"]), "candidate_functions_refused")
    total = 0
    for actual, wanted in zip(functions, config["expected_functions"]):
        need(type(actual) is dict and set(actual) == {"class", "function", "variants_passed"}, "candidate_function_shape_refused")
        exact({key: actual[key] for key in ("class", "function")}, wanted, "candidate_function_binding_refused")
        need(type(actual["variants_passed"]) is int and 1 <= actual["variants_passed"] <= 4096, "candidate_variant_count_refused")
        total += actual["variants_passed"]
    need(type(candidate["passed"]) is int and 1 <= total <= 4096 and candidate["passed"] == total, "candidate_case_total_refused")
    diagnostic = receipts["focused-diagnostic.json"]
    diagnostic_expected = {"schema": 1, "scope": "unaccepted_focused_pytest_diagnostics", "acceptance_qualified": False,
        "pytest_exit": 0, "junit_available": True, "junit_parsed": True, "cases": diagnostic.get("cases"),
        "observed_cases": total, "failed_cases": 0, "skipped_cases": 0, "unmapped_case_count": 0,
        "error_nodes": 0, "failure_nodes": 0}
    exact(diagnostic, diagnostic_expected, "diagnostic_success_refused")
    need(type(diagnostic["cases"]) is list and len(diagnostic["cases"]) == total, "diagnostic_count_refused")
    counts = {}
    for item in diagnostic["cases"]:
        need(type(item) is dict and set(item) == {"class", "function", "failed", "skipped", "failure_locations"},
             "diagnostic_case_shape_refused")
        identity = (item["class"], item["function"])
        need(identity in {(x["class"], x["function"]) for x in functions}, "diagnostic_case_binding_refused")
        exact({key: item[key] for key in ("failed", "skipped", "failure_locations")},
              {"failed": False, "skipped": False, "failure_locations": []}, "diagnostic_case_success_refused")
        counts[identity] = counts.get(identity, 0) + 1
    need(counts == {(x["class"], x["function"]): x["variants_passed"] for x in functions}, "diagnostic_variant_total_refused")
    host = receipts["host.json"]
    host_expected = {"schema": 1, "scope": SCOPE, "outcome": "passed", "runner_exit": 0,
        "failure_or_final_stage": "complete", "source_commit": config["source_commit"], "config_sha256": config_sha,
        "image_digest": IMAGE_DIGEST, "expected_image_id": IMAGE_ID, "host_elapsed_seconds": host.get("host_elapsed_seconds"),
        "host_system": "Linux", "host_architecture": "x86_64", "core": "2026.10.2", "source_git_verified": True,
        "backend_network_disconnected": True, "container_stopped": True, "container_removed": True, "cleanup_failed": False,
        "private_workspace_removed": True, "full_backend_suite_repeated": False, "full_managed_core_lifecycle": False,
        "upgrade_validated": False, "kvm_used": False, "owner_accounts_used": False,
        "production_configuration_used": False, "release_published": False}
    exact(host, host_expected, "host_success_or_cleanup_refused")
    need(type(host["host_elapsed_seconds"]) in (int, float) and 0 < host["host_elapsed_seconds"] <= 1950,
         "bounded_host_duration_required")
    return {"schema": 1, "outcome": "accepted", "scope": SCOPE, "source_commit": config["source_commit"],
        "config_sha256": config_sha, "package_sha256": config["package_sha256"], "source_files": config["source_files"],
        "selected_modules": len(config["selected_modules"]), "selected_base_functions": len(functions), "passed": total,
        "failed": 0, "skipped": 0, "offline_test_phase": True, "cleanup_required_and_observed": True,
        "artifact_transport_verified_by_consumer": False, "producer_collection_assertion_consumed": True,
        "full_backend_suite_repeated": False, "upgrade_validated": False, "owner_accounts_used": False,
        "production_configuration_used": False, "release_published": False}


def consume(config_path, expected, results):
    config = config_read(config_path, expected)
    need(results.is_dir() and not results.is_symlink() and {path.name for path in results.iterdir()} == FILES,
         "exact_public_receipt_set_required")
    receipts, fingerprints = {}, {}
    for name in sorted(FILES):
        receipts[name], raw = load(results / name)
        fingerprints[name] = {"bytes": len(raw), "sha256": sha(raw)}
    graph, _ = load(HERE / "CORE-GRAPH.json", GRAPH_SHA)
    accepted = verify(config, expected, receipts, graph)
    accepted["receipts"] = fingerprints
    return accepted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--config-sha", required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = consume(args.config, args.config_sha, args.results)
        need(not args.output.exists() and not args.output.is_symlink() and args.output.parent.is_dir(), "fresh_output_required")
        with args.output.open("xb") as stream:
            stream.write((json.dumps(result, indent=2, sort_keys=True) + "\n").encode())
    except (Refused, OSError, ValueError, TypeError, KeyError):
        print(json.dumps({"schema": 1, "outcome": "refused", "scope": SCOPE}))
        return 1
    print(json.dumps({"outcome": "accepted", "passed": result["passed"], "scope": SCOPE}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
