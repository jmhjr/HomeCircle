"""Independent bounded HACS receipt consumer; never imports a producer/helper."""
import argparse
import hashlib
import json
from pathlib import Path
import re

SOURCE = "b906d3ee51711d3455a497cc265fd3bc18f3adec"
CANDIDATE = "4f94a18e2f7862e9bd7f4c85250e5f10e4b8e1292ea9d7b263b441d2e1b77dd9"
BASELINE = "fc0b365d9688459504f874af5c38393e24145d657f15f1def8ada9184f363285"
PHASES = ("bootstrap_hacs", "fresh_download", "fresh", "fresh_remove", "fresh_removed", "baseline_download",
          "baseline", "upgrade_download", "upgraded", "restart", "rollback_download", "rollback", "reupgrade_download", "final")
SPEC = {
    "bootstrap_hacs": (None, None, False), "fresh_download": ("rc", None, True),
    "fresh": ("rc", "rc", False), "fresh_remove": (None, "rc", False), "fresh_removed": (None, None, False),
    "baseline_download": ("base", None, True), "baseline": ("base", "base", False),
    "upgrade_download": ("rc", "base", True), "upgraded": ("rc", "rc", False), "restart": ("rc", "rc", False),
    "rollback_download": ("base", "rc", True), "rollback": ("base", "base", False),
    "reupgrade_download": ("rc", "base", True), "final": ("rc", "rc", False),
}
PHASE_KEYS = {"schema", "phase", "outcome", "source_commit", "candidate_sha256", "baseline_sha256", "anchor_sha256",
    "branch_commit", "nonce_sha256", "core_version", "process", "hacs", "disk", "loaded", "frontend", "snapshot_sha256",
    "persisted_store_checked", "download_tag", "release_proof", "removed", "guard", "provider_requests_denied",
    "provider_accounts", "recovery_api_calls", "normal_requirements", "activity", "removed_activity_store"}
HOST_KEYS = {"schema", "outcome", "source_commit", "candidate_sha256", "baseline_sha256", "anchor_sha256", "branch_commit",
    "nonce_sha256", "phase_count", "core_version", "hacs_version", "actual_kvm", "provenance", "core_actions",
    "ephemeral_job_token", "oauth_onboarding", "direct_candidate_installs", "provider_accounts", "owner_accounts",
    "recovery_api_calls", "supervisor_backup_restore", "stopped_configuration_rollback", "guard_claim", "host_elapsed_seconds",
    "failure", "qemu_stopped", "private_workspace_removed", "cleanup_failed"}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def require(value, code):
    if not value:
        raise ValueError(code)


def same(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(same(actual[key], value) for key, value in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(same(a, b) for a, b in zip(actual, expected, strict=True))
    return actual == expected


def fingerprint(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def read(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 1024**2, "bounded_regular_json_required")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    return json.loads(path.read_bytes(), object_pairs_hook=unique)


def accept(host, receipts, inventories, *, anchor_sha, branch, inputs):
    require(isinstance(inventories, dict) and set(inventories) == {"rc", "base"}
            and all(isinstance(value, dict) and len(value) == 112 for value in inventories.values()), "exact_independent_inventories")
    require(set(host) == HOST_KEYS and tuple(receipts) == PHASES, "complete_exact_receipts")
    common = {"schema": 1, "source_commit": SOURCE, "candidate_sha256": CANDIDATE, "baseline_sha256": BASELINE,
              "anchor_sha256": anchor_sha, "branch_commit": branch, "core_version": "2026.10.2"}
    require(all(same(host.get(key), value) for key, value in common.items()), "host_identity")
    required = {"outcome": "passed", "phase_count": 14, "hacs_version": "2.0.5", "actual_kvm": True,
        "ephemeral_job_token": True, "oauth_onboarding": False, "direct_candidate_installs": 0,
        "provider_accounts": 0, "owner_accounts": 0, "recovery_api_calls": 0, "supervisor_backup_restore": False,
        "stopped_configuration_rollback": True, "guard_claim": "synthetic_opaque_byte_preservation_only", "failure": None,
        "qemu_stopped": True, "private_workspace_removed": True, "cleanup_failed": False}
    require(all(same(host.get(key), value) for key, value in required.items()), "host_success_and_cleanup")
    require(type(host["host_elapsed_seconds"]) in (int, float) and 0 < host["host_elapsed_seconds"] <= 5640, "host_deadline")
    provenance = host["provenance"]
    require(isinstance(provenance, dict) and set(provenance) == {"source_commit", "source_files", "candidate_sha256", "inventory_sha256",
        "baseline_sha256", "baseline_inventory_sha256", "hacs_sha256", "haos_sha256", "helper_files", "controller_sha256", "donor_host_sha256", "anchor_sha256"}, "exact_provenance")
    require(same(provenance, inputs), "frozen_input_provenance")
    require(fingerprint(host["nonce_sha256"]), "run_nonce")
    actions = host["core_actions"]
    require(isinstance(actions, list) and len(actions) == 23, "finite_core_action_count")
    for index, action in enumerate(actions):
        expected = "stop" if index % 2 == 0 else "start"
        require(isinstance(action, dict) and set(action) == {"action", "result", "supervisor_running", "relevant_core_jobs_idle", "running_before", "running_after"}, "exact_core_action")
        require(same(action, {"action": expected, "result": "ok", "supervisor_running": True, "relevant_core_jobs_idle": True,
            "running_before": expected == "stop", "running_after": expected == "start"}), "normal_core_lifecycle")
    versions = {"rc": "1.0.0-rc.1", "base": "0.1.0-beta.20"}
    active = {"fresh", "baseline", "upgrade_download", "upgraded", "restart", "rollback_download", "rollback", "reupgrade_download", "final"}
    for name, value in receipts.items():
        require(isinstance(value, dict) and set(value) == PHASE_KEYS, "exact_phase_schema")
        fixed = {**common, "phase": name, "outcome": "passed", "nonce_sha256": host["nonce_sha256"],
                 "provider_requests_denied": 0, "provider_accounts": 0, "recovery_api_calls": 0}
        require(all(same(value.get(key), item) for key, item in fixed.items()), "phase_identity")
        process = value["process"]
        require(isinstance(process, dict) and set(process) == {"pid", "start_ticks"}
                and all(type(item) is int and item > 0 for item in process.values()), "real_core_process")
        disk, loaded, downloaded = SPEC[name]
        expected_disk = None if disk is None else {"version": versions[disk], "files": 112, "payload_sha256": sha(encoded(inventories[disk]))}
        expected_loaded = None if loaded is None else {"version": versions[loaded], "source_sha256": inventories[loaded]["__init__.py"]["sha256"]}
        require(same(value["disk"], expected_disk) and same(value["loaded"], expected_loaded), "installed_vs_loaded_bytes")
        require(same(value["hacs"], {"version": "2.0.5", "enabled": True, "queue_pending": 0, "installed": disk is not None,
             "installed_version": "v" + versions[disk] if disk else None}), "genuine_hacs_state")
        require(same(value["download_tag"], "v" + versions[disk] if downloaded else None)
                and value["release_proof"] is (disk is not None), "real_release_catalog_and_download")
        require(value["removed"] is (name in {"fresh_remove", "fresh_removed"}), "actual_removal_phases")
        require(value["removed_activity_store"] is (name in {"fresh_remove", "fresh_removed"}), "owned_activity_removal")
        activity = value["activity"]
        if name in active - {"fresh"}:
            require(isinstance(activity, dict) and set(activity) == {"count", "cohort_sha256", "retained"}
                and type(activity["count"]) is int and activity["count"] == 2 and activity["retained"] is True
                and fingerprint(activity["cohort_sha256"]), "two_durable_synthetic_activity_markers")
        else:
            require(activity is None, "activity_marker_scope")
        require(value["persisted_store_checked"] is (name in {"fresh", "baseline"}), "ordinary_store_persistence")
        expected_requirements = {"cryptography": "50.0.1", "srp": "1.0.22", "unicorn": "2.1.4"} if loaded == "rc" else None
        require(same(value["normal_requirements"], expected_requirements), "normal_core_dependency_versions")
        if name in active:
            bundle = inventories[loaded]["frontend/homecircle-card.js"]["sha256"]
            require(same(value["frontend"], {"bundle_sha256": bundle, "url": "/homecircle_static/homecircle-card.js?v=" + versions[loaded] + "&asset=" + bundle[:12], "served": True}), "actually_served_frontend")
            require(fingerprint(value["snapshot_sha256"]), "nonempty_snapshot_commitment")
        else:
            require(value["frontend"] is None and value["snapshot_sha256"] is None, "no_invented_active_snapshot")
        guard = value["guard"]
        if name in active - {"fresh"}:
            require(isinstance(guard, dict) and set(guard) == {"generation", "ledger_sha256", "witness_sha256", "byte_preservation_only"}, "exact_guard_pair")
            require(type(guard["generation"]) is int and guard["generation"] == (1 if name in {"baseline", "upgrade_download"} else 2)
                and guard["byte_preservation_only"] is True and fingerprint(guard["ledger_sha256"]) and fingerprint(guard["witness_sha256"]), "synthetic_opaque_guard_pair")
        else:
            require(guard is None, "guard_scope")
    for name in active - {"fresh"}:
        require(receipts[name]["snapshot_sha256"] == receipts["baseline"]["snapshot_sha256"], "explicit_identity_continuity")
        require(same(receipts[name]["activity"], receipts["baseline"]["activity"]), "activity_marker_continuity")
    for name in ("restart", "rollback_download", "rollback", "reupgrade_download", "final"):
        require(receipts[name]["guard"] == receipts["upgraded"]["guard"], "newest_ledger_and_witness_preserved")
    require(receipts["baseline"]["guard"] != receipts["upgraded"]["guard"], "guard_preservation_nonvacuous")
    for before, after in (("fresh_download", "fresh"), ("fresh_remove", "fresh_removed"), ("baseline_download", "baseline"), ("upgrade_download", "upgraded"), ("upgraded", "restart"), ("rollback_download", "rollback"), ("reupgrade_download", "final")):
        require(receipts[before]["process"]["start_ticks"] != receipts[after]["process"]["start_ticks"], "actual_restart_required")
    return {"schema": 1, "outcome": "passed", "source_commit": SOURCE, "candidate_sha256": CANDIDATE,
            "phases": 14, "fresh_install": True, "hacs_uninstall": True, "upgrade_restart_rollback": True,
            "guard_claim": "synthetic_opaque_byte_preservation_only", "cleanup": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("receipts", "candidate-inventory", "baseline-inventory", "expected-provenance", "output"):
        parser.add_argument("--" + key, required=True, type=Path)
    parser.add_argument("--anchor-sha256", required=True)
    parser.add_argument("--branch-commit", required=True)
    args = parser.parse_args()
    allowed = {name + ".json" for name in PHASES} | {"host.json"}
    actual = {path.name for path in args.receipts.iterdir()}
    require(allowed <= actual <= allowed | {"independent-review.json"}, "only_complete_success_receipts")
    inventories = {"rc": read(args.candidate_inventory)["files"], "base": read(args.baseline_inventory)["files"]}
    require(sha(args.candidate_inventory.read_bytes()) == "e4bc34e3921e75157402cf643f87ed658d95c76505a448abb393fd90a304db12"
        and sha(args.baseline_inventory.read_bytes()) == "5e724f69ff20a711dd87b2a39ed96818781813bb6f1e7b3addedc6e048593d77", "independent_inventory_pins")
    require(all(len(value) == 112 for value in inventories.values()), "exact_package_member_counts")
    result = accept(read(args.receipts / "host.json"), {name: read(args.receipts / (name + ".json")) for name in PHASES}, inventories,
                    anchor_sha=args.anchor_sha256, branch=args.branch_commit, inputs=read(args.expected_provenance))
    require(not args.output.exists(), "fresh_review_output")
    args.output.write_bytes(json.dumps(result, sort_keys=True, indent=2).encode() + b"\n")


if __name__ == "__main__":
    main()
