"""Recognize a completed investigation without converting a safety finding to a pass."""

import argparse
import json
from pathlib import Path

EXPECTED_ZIP = "fc0b365d9688459504f874af5c38393e24145d657f15f1def8ada9184f363285"


def evaluate(value, exit_code):
    def require(condition):
        if not condition:
            raise ValueError("incomplete_or_inconsistent_investigation")

    require(type(value) is dict and value.get("schema") == 1)
    require(value.get("diagnostic_completed") is True)
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
    require(value.get("provenance", {}).get("candidate_zip_sha256") == EXPECTED_ZIP)
    boundary = value.get("network_boundary", {})
    require(boundary.get("before_probe_connected") is True
            and boundary.get("link_closed") is True
            and boundary.get("closed_probe_connected") is False
            and boundary.get("guest_agent_remained_available") is True)
    require(type(boundary.get("closed_probe_observations")) is int
            and boundary["closed_probe_observations"] >= 3)
    protected = value.get("automatic_guard_antirollback_passed")
    require(type(protected) is bool and type(exit_code) is int)
    require(value.get("ordinary_enabled_restore_safety_accepted") is protected)
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
        "ordinary_enabled_restore_safety_accepted": protected,
        "stable_release_approval": False,
        "interpretation": (
            "observed_restore_scope_only" if protected
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
    print("Investigation completed; ordinary restored safeguard protection=" +
          str(result["automatic_guard_antirollback_passed"]).lower())


if __name__ == "__main__":
    main()
