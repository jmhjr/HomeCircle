"""Bounded offline Core 9.4 native/backend/upgrade/recovery acceptance."""

import sys

if sys.platform != "linux":
    raise SystemExit("linux_required")

import hashlib
import importlib.util
import json
from pathlib import Path
import re
from types import ModuleType
import xml.etree.ElementTree as ET


QA = Path("/qa")
OUTPUT = QA / "results/core94-suite"
DRIVER_SHA = "b5868eb974456b36f1fedbccea59f3b9a76a4bddba264806dc9c4c481ad8877c"
CANDIDATE = "f0477a91e78181fe1f8d80ada176a1739e10a7502abe7ee6ee2240571280d1f5"
CONSTRAINTS = "962c9ccaf398e0b92b10ac9f765ac0f17e22238adc4e768deebc051ee8b60651"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load_setup():
    # The native host hash-pins this helper before copying it into the container.
    spec = importlib.util.spec_from_file_location("native_core94_setup", QA / "setup_container.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_driver():
    path = QA / "run_validation_core94.py"
    raw = path.read_bytes()
    if digest(raw) != DRIVER_SHA:
        raise ValueError("core94_driver_hash_refused")
    module = ModuleType("frozen_core94_driver")
    module.__file__ = str(path)
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def backend_result(driver, path, *, require_pass=True):
    driver.check(path.is_file() and path.stat().st_size < 16 * 1024**2, "backend_xml_refused")
    root = ET.fromstring(path.read_bytes())
    cases = root.findall(".//testcase")
    failed = [case for case in cases if case.find("failure") is not None or case.find("error") is not None]
    skipped = [case for case in cases if case.find("skipped") is not None]
    labels = []
    for case in failed[:3]:
        classname = case.attrib.get("classname", "")
        function = case.attrib.get("name", "").split("[", 1)[0]
        if (classname.startswith("tests.") and re.fullmatch(r"[A-Za-z0-9_.]{1,180}", classname)
                and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,119}", function)):
            labels.append({"class": classname, "function": function})
    result = {"passed": len(cases) - len(failed) - len(skipped), "failed": len(failed),
              "skipped": len(skipped), "failure_labels": labels}
    if require_pass:
        suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
        driver.check(bool(suites) and all(int(item.attrib.get("errors", "-1")) == 0 and
                     int(item.attrib.get("failures", "-1")) == 0 for item in suites), "backend_suite_errors")
        driver.check(result["passed"] == 1443 and not failed and len(skipped) == 1, "backend_counts_refused")
        driver.check(skipped[0].attrib.get("name") == "test_retained_public_apple_dmg_fixed_ranges"
                     and skipped[0].attrib.get("classname") == "tests.test_findmy_runtime_bootstrap",
                     "backend_skip_refused")
    return result


def native_result(driver, path):
    value = driver.read_json(path)
    driver.check(value.get("outcome") == "passed" and value.get("core_version") == "2026.9.4",
                 "native_outcome_refused")
    driver.check(value.get("package_sha256") == CANDIDATE and value.get("package_members") == 112,
                 "native_candidate_refused")
    driver.check(value.get("machine") == "x86_64" and value.get("system") == "Linux", "native_arch_refused")
    driver.check(value.get("core_constraints_sha256") == CONSTRAINTS and
                 value.get("core_constraint_mismatches") == [], "native_constraints_refused")
    driver.check(len(value.get("installed_dependency_closure", {})) == 24, "native_closure_refused")
    for key in ("mandatory_imports", "synthetic_native_worker", "production_hash_refusal",
                "worker_processes_reaped", "cleanup_ok"):
        driver.check(value.get(key) is True, "native_contract_refused")
    for key in ("network_allowed", "apple_binary_executed", "owner_data_read"):
        driver.check(value.get(key) is False, "native_network_refused")
    driver.check(value.get("account_requests") == 0 and value.get("unicorn_version") == "2.1.4",
                 "native_runtime_refused")
    return {"actual_packaged_native_worker": True, "production_hash_refusal": True,
            "native_worker_reaped": True, "active_dependency_packages": 24}


def lifecycle_result(driver, path):
    value = driver.read_json(path)
    driver.check(value.get("outcome") == "passed" and value.get("package_sha256") == CANDIDATE
                 and value.get("package_members") == 112, "lifecycle_outcome_refused")
    driver.check(value.get("machine") == "x86_64" and value.get("system") == "Linux",
                 "lifecycle_arch_refused")
    for key in ("normal_open_check_close", "active_native_cancellation", "parent_only_dependency_used",
                "production_spawn_contract", "production_pipe_contract", "worker_processes_reaped", "cleanup_ok"):
        driver.check(value.get(key) is True, "lifecycle_contract_refused")
    for key in ("candidate_files_modified", "network_allowed", "apple_binary_executed", "owner_data_read"):
        driver.check(value.get(key) is False, "lifecycle_network_refused")
    driver.check(value.get("account_requests") == 0 and value.get("unicorn_version") == "2.1.4",
                 "lifecycle_runtime_refused")
    limits = value.get("child_limits", {})
    for key, expected in (("cpu_seconds", 90), ("core_bytes", 0), ("address_space_bytes", 3 * 1024**3)):
        driver.check(limits.get(key, {}).get("soft") == limits.get(key, {}).get("hard") == expected,
                     "lifecycle_limits_refused")
    workers = value.get("worker_children", [])
    driver.check(len(workers) == 2 and all(item.get("proc_absent") is True and
                 isinstance(item.get("exit_code"), int) for item in workers), "lifecycle_reap_refused")
    return {"actual_provider_lifecycle": True, "active_native_cancellation": True,
            "parent_only_dependency_used": True, "worker_limits_verified": True, "workers_reaped": 2}


def upgrade_result(driver, path):
    value = driver.read_json(path)
    driver.check(value.get("outcome") == "passed" and value.get("completed") is True,
                 "upgrade_driver_outcome_refused")
    driver.check(value.get("driver_sha256") == DRIVER_SHA and value.get("candidate_sha256") == CANDIDATE
                 and value.get("candidate_changed") is False, "upgrade_driver_input_refused")
    driver.check(value.get("environment", {}).get("core") == "2026.9.4", "upgrade_driver_core_refused")
    driver.check(value.get("upgrade_phases") == value.get("recovery_processes") == 20 and
                 value.get("network_probes_blocked") == 40, "upgrade_driver_counts_refused")
    driver.check(value.get("inputs_before") == value.get("inputs_after"), "upgrade_driver_post_inputs_refused")
    driver.check([item.get("job") for item in value.get("jobs", [])] ==
                 ["upgrade-published", "upgrade-recorded", "recovery"], "upgrade_driver_jobs_refused")
    return {"upgrade_phases": 20, "recovery_processes": 20, "network_probes_blocked": 40,
            "unexpected_network_attempts": 0, "apple_requests": 0}


def main():
    setup, driver = load_setup(), load_driver()
    driver.check(not OUTPUT.exists(), "fresh_suite_output_required")
    OUTPUT.mkdir(parents=True, mode=0o700)
    path = OUTPUT / "suite.json"
    receipt = {"schema": 1, "outcome": "in_progress", "completed": False,
               "core": "2026.9.4", "candidate_sha256": CANDIDATE,
               "current_stage": "inputs", "jobs": [], "owner_accounts_used": False,
               "production_configuration_used": False}
    helpers = {name: digest((QA / name).read_bytes()) for name in
               ("setup_container.py", "run_suite.py", "run_validation_core94.py")}
    stage = "inputs"
    try:
        with driver.termination_guard():
            files = setup.check_inputs()
            source = setup.public_source()
            setup.check_tree(files)
            setup.check_public_tree(source)
            setup.core_constraints()
            receipt["inputs_before"] = driver.check_inputs(QA)
            receipt["helper_hashes"] = helpers
            driver.write_json(path, receipt)
            archive = str(QA / "homecircle-candidate.zip")
            inventory = str(QA / "homecircle-inventory.json")
            stages = (
                ("native", [sys.executable, "-B", str(QA / "scripts/platform_validate_candidate.py"),
                 "--archive", archive, "--expected-sha256", CANDIDATE, "--inventory", inventory,
                 "--output", str(OUTPUT / "native.json")], 180,
                 lambda: native_result(driver, OUTPUT / "native.json")),
                ("lifecycle", [sys.executable, "-B", str(QA / "scripts/platform_validate_linux_lifecycle.py"),
                 "--archive", archive, "--inventory", inventory, "--output", str(OUTPUT / "lifecycle.json")], 120,
                 lambda: lifecycle_result(driver, OUTPUT / "lifecycle.json")),
                ("backend", [sys.executable, "-B", "-m", "pytest", "--junitxml", str(OUTPUT / "backend.xml")], 900,
                 lambda: backend_result(driver, OUTPUT / "backend.xml")),
                ("upgrade-recovery", [sys.executable, "-B", str(QA / "run_validation_core94.py"),
                 "--qa-root", str(QA), "--output", str(OUTPUT / "upgrade-recovery")], 5520,
                 lambda: upgrade_result(driver, OUTPUT / "upgrade-recovery/driver.json")),
            )
            for stage, command, limit, validate in stages:
                receipt["current_stage"] = stage
                driver.write_json(path, receipt)
                print(json.dumps({"stage": stage, "outcome": "started", "limit_seconds": limit}), flush=True)
                result = driver.run_owned_job(command, cwd=QA, log_path=OUTPUT / (stage + ".log"),
                                              limit=limit, validate=validate)
                receipt["jobs"].append({"job": stage, "outcome": "passed", **result})
                setup.check_inputs()
                setup.check_tree(files)
                setup.check_public_tree(source)
                driver.write_json(path, receipt)
            receipt["inputs_after"] = driver.check_inputs(QA)
            driver.check(receipt["inputs_after"] == receipt["inputs_before"], "suite_inputs_changed")
            driver.check(all(digest((QA / name).read_bytes()) == expected for name, expected in helpers.items()),
                         "suite_helpers_changed")
            receipt.update({"outcome": "passed", "completed": True, "current_stage": "complete",
                            "backend_passed": 1443, "backend_skipped": 1,
                            "native_worker_passed": True, "lifecycle_passed": True,
                            "upgrade_phases": 20, "recovery_processes": 20, "network_probes_blocked": 40,
                            "unexpected_network_attempts": 0, "apple_requests": 0})
            driver.write_json(path, receipt)
    except BaseException as error:
        receipt.update({"outcome": "failed", "completed": False, "failure_stage": stage,
                        "failure_type": type(error).__name__})
        if stage == "backend":
            try:
                receipt["backend_failure"] = backend_result(driver, OUTPUT / "backend.xml", require_pass=False)
            except Exception:
                pass
        driver.write_json(path, receipt)
        print(json.dumps({"outcome": "failed", "failure_stage": stage,
                          "failure_type": type(error).__name__}), flush=True)
        return 1
    print(json.dumps({"outcome": "passed", "completed": True}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
