"""Recognize a completed investigation without converting a safety finding to a pass."""

import argparse
import json
import re
from pathlib import Path

EXPECTED_ZIP = "c4530d94be3b2996f8d6c8948db88a51868566047d68558eefde7967f270a861"
EXPECTED_SOURCE = "9bf03eb45d2cf43274074534e9dfe2de841f4011"
EXPECTED_FILES = 113
EXPECTED_VERSION = "0.1.0-beta.20"


def evaluate(value, exit_code):
    def require(condition):
        if not condition:
            raise ValueError("incomplete_or_inconsistent_investigation")

    require(type(value) is dict and type(value.get("schema")) is int and value["schema"] == 1)
    require(value.get("diagnostic_completed") is True)
    require(value.get("prepared_dependency_enabled_partial_restore") is True
            and value.get("ordinary_default_dependency_reinstallation_tested") is False
            and value.get("ordinary_enabled_restore_safety_accepted") is False)
    fixture = value.get("prepared_dependency_fixture", {})
    require(fixture.get("outcome") == "passed" and fixture.get("core") == "2026.10.2"
            and fixture.get("constraints_sha256") == "7baa9a8f39ddeb9c5bb60a1036f6d5e33f4b84267f151f53cc2b95ef031a21b5"
            and type(fixture.get("closure_count")) is int and fixture["closure_count"] == 24
            and fixture.get("inventory_scope") == "dependency_regular_files_excluding_generated_bytecode"
            and isinstance(fixture.get("inventory_sha256"), str)
            and re.fullmatch(r"[0-9a-f]{64}", fixture["inventory_sha256"])
            and type(fixture.get("inventory_files")) is int and fixture["inventory_files"] > 0)
    archived = value.get("backup", {}).get("archive", {})
    require(archived.get("prepared_dependency_sha256") == fixture["inventory_sha256"]
            and archived.get("prepared_dependency_files") == fixture["inventory_files"])
    for key in (
        "operational_restore_passed", "manual_newest_guard_repair_passed",
        "actual_kvm_confirmed", "qemu_stopped", "private_workspace_removed",
        "enabled_entry_restore_tested", "automatic_guard_antirollback_tested",
    ):
        require(value.get(key) is True)
    for key in ("cleanup_failed", "provider_accounts_configured", "owner_credentials_used",
                "production_configuration_used", "guard_repair_before_first_enabled_boot"):
        require(value.get(key) is False)
    require(type(value.get("phases")) is int and value["phases"] == 6)
    require(value.get("failure_type") is None and value.get("failure_code") is None)
    provenance = value.get("provenance", {})
    require(provenance.get("candidate_zip_sha256") == EXPECTED_ZIP
            and provenance.get("candidate_source_commit") == EXPECTED_SOURCE
            and type(provenance.get("candidate_files")) is int
            and provenance["candidate_files"] == EXPECTED_FILES
            and provenance.get("candidate_version") == EXPECTED_VERSION
            and provenance.get("candidate_input_kind") == "pinned_local_unreleased_preview_zip"
            and provenance.get("same_version_unreleased_development_preview") is True
            and provenance.get("release_published") is False
            and type(provenance.get("candidate_package_validation_run")) is int
            and provenance["candidate_package_validation_run"] == 39490732759)
    boundary = value.get("network_boundary", {})
    require(boundary.get("before_probe_connected") is True
            and boundary.get("link_closed") is True
            and boundary.get("closed_probe_connected") is False
            and boundary.get("guest_agent_remained_available") is True)
    require(type(boundary.get("closed_probe_observations")) is int
            and boundary["closed_probe_observations"] >= 3)
    protected = value.get("automatic_guard_antirollback_passed")
    require(type(protected) is bool and type(exit_code) is int)
    require(value.get("prepared_enabled_restore_safety_accepted") is protected)
    if protected:
        require(exit_code == 0 and value.get("outcome") == "passed")
    else:
        require(exit_code == 1 and value.get("outcome") == "confirmed_safety_issue")
    return {
        "schema": 1,
        "investigation_completed": True,
        "controller_exit_code": exit_code,
        "controller_outcome": value["outcome"],
        "operational_restore_passed": True,
        "manual_newest_guard_repair_passed": True,
        "automatic_guard_antirollback_passed": protected,
        "ordinary_enabled_restore_safety_accepted": False,
        "prepared_enabled_restore_safety_accepted": protected,
        "prepared_dependency_enabled_partial_restore": True,
        "ordinary_default_dependency_reinstallation_tested": False,
        "stable_release_approval": False,
        "candidate_zip_sha256": EXPECTED_ZIP,
        "candidate_source_commit": EXPECTED_SOURCE,
        "candidate_files": EXPECTED_FILES,
        "candidate_version": EXPECTED_VERSION,
        "same_version_unreleased_development_preview": True,
        "release_published": False,
        "interpretation": (
            "observed_prepared_dependency_restore_scope_only" if protected
            else "older_backup_rolls_back_local_guard_requires_release_disposition"
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--exit-code", type=int, required=True)
    args = parser.parse_args()
    if not args.summary.is_file() or args.summary.is_symlink() or args.summary.stat().st_size > 256 * 1024:
        raise SystemExit("Investigation summary refused.")
    try:
        result = evaluate(json.loads(args.summary.read_bytes()), args.exit_code)
    except (ValueError, KeyError, TypeError):
        raise SystemExit("Investigation incomplete or inconsistent; acceptance refused.") from None
    (args.summary.parent / "investigation.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("Prepared-dependency investigation completed; restored safeguard protection=" +
          str(result["automatic_guard_antirollback_passed"]).lower())


if __name__ == "__main__":
    main()
