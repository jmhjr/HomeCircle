"""Finite RC HACS qualification in one newly owned native Linux HAOS guest."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import sys
import tarfile
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import donor_host as d
from protocol import (ACTIVE, BASELINE, BASE_INVENTORY, BASE_TAG, BASE_VERSION, CANDIDATE, CORE,
    DISK, DOWNLOADS, HACS, HACS_SHA, INVENTORY, LOADED, PHASES, PHASE_KEYS, SOURCE, TAG, VERSION,
    anchor_at, canonical, check, digest, same)

HERE = Path(__file__).resolve().parent
for key, value in {"ROOT": HERE, "CANDIDATE_SHA": CANDIDATE, "RELEASE_COMMIT": SOURCE,
    "RELEASE_VERSION": VERSION, "RELEASE_TAG": TAG, "BASELINE_VERSION": BASE_VERSION,
    "BASELINE_TAG": BASE_TAG, "BASELINE_SHA": BASELINE, "PHASES": PHASES}.items():
    setattr(d, key, value)
Refused = d.Refused


def files_at(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        check(not path.is_symlink(), "input_tree_symlink")
        if path.is_file() and "__pycache__" not in path.parts:
            raw = path.read_bytes()
            result[path.relative_to(directory).as_posix()] = {"bytes": len(raw), "sha256": digest(raw)}
    return result


def inventory_at(path, expected_sha, archive_path, archive_sha):
    check(path.is_file() and not path.is_symlink() and digest(path.read_bytes()) == expected_sha, "inventory_identity")
    document = json.loads(path.read_bytes())
    actual = d.check_archive(archive_path, archive_sha, 112)
    check(document.get("files") == actual and document.get("archive_sha256") == archive_sha, "inventory_payload")
    return actual


def phase_check(name, receipt, *, anchor_sha, branch, nonce, inventories):
    check(isinstance(receipt, dict) and set(receipt) == PHASE_KEYS, "phase_exact_schema")
    fixed = {"schema": 1, "phase": name, "outcome": "passed", "source_commit": SOURCE,
        "candidate_sha256": CANDIDATE, "baseline_sha256": BASELINE, "anchor_sha256": anchor_sha,
        "branch_commit": branch, "nonce_sha256": digest(nonce.encode()), "core_version": CORE,
        "provider_requests_denied": 0, "provider_accounts": 0, "recovery_api_calls": 0}
    check(all(type(receipt.get(key)) is type(value) and receipt[key] == value for key, value in fixed.items()), "phase_binding")
    process = receipt["process"]
    check(isinstance(process, dict) and set(process) == {"pid", "start_ticks"}
          and all(type(value) is int and value > 0 for value in process.values()), "phase_process")
    disk, loaded = DISK[name], LOADED[name]
    if disk:
        check(same(receipt["disk"], {"version": VERSION if disk == "candidate" else BASE_VERSION, "files": 112,
             "payload_sha256": digest(inventories[disk])}), "phase_disk")
    else:
        check(receipt["disk"] is None, "phase_absent_disk")
    if loaded:
        check(receipt["loaded"] == {"version": VERSION if loaded == "candidate" else BASE_VERSION,
            "source_sha256": inventories[loaded]["__init__.py"]["sha256"]}, "phase_loaded")
    else:
        check(receipt["loaded"] is None, "phase_unloaded")
    expected_tag = TAG if disk == "candidate" else BASE_TAG if disk == "baseline" else None
    check(receipt["hacs"] == {"version": HACS, "enabled": True, "queue_pending": 0,
          "installed": disk is not None, "installed_version": expected_tag}, "phase_hacs")
    check(receipt["download_tag"] == DOWNLOADS.get(name), "phase_download")
    check(receipt["release_proof"] is (disk is not None), "phase_catalog_proof")
    check(receipt["removed"] is (name in {"fresh_remove", "fresh_removed"}), "phase_removal")
    check(receipt["persisted_store_checked"] is (name in {"fresh", "baseline"}), "phase_persisted_store")
    check(receipt["removed_activity_store"] is (name in {"fresh_remove", "fresh_removed"}), "phase_activity_removal")
    activity = receipt["activity"]
    if name in ACTIVE - {"fresh"}:
        check(isinstance(activity, dict) and set(activity) == {"count", "cohort_sha256", "retained"}
              and type(activity["count"]) is int and activity["count"] == 2 and activity["retained"] is True
              and isinstance(activity["cohort_sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", activity["cohort_sha256"]), "phase_activity_cohort")
    else:
        check(activity is None, "phase_activity_scope")
    if name in ACTIVE:
        bundle = inventories[loaded]["frontend/homecircle-card.js"]["sha256"]
        version = VERSION if loaded == "candidate" else BASE_VERSION
        check(receipt["frontend"] == {"bundle_sha256": bundle,
            "url": "/homecircle_static/homecircle-card.js?v=" + version + "&asset=" + bundle[:12], "served": True}, "phase_frontend")
        check(isinstance(receipt["snapshot_sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", receipt["snapshot_sha256"]), "phase_snapshot")
    else:
        check(receipt["snapshot_sha256"] is None and receipt["frontend"] is None, "phase_no_snapshot")
    if loaded == "candidate":
        check(receipt["normal_requirements"] == {"cryptography": "50.0.1", "srp": "1.0.22", "unicorn": "2.1.4"}, "phase_requirements")
    else:
        check(receipt["normal_requirements"] is None, "phase_requirement_scope")
    if name in ACTIVE and name != "fresh":
        guard = receipt["guard"]
        generation = 1 if name in {"baseline", "upgrade_download"} else 2
        check(isinstance(guard, dict) and set(guard) == {"generation", "ledger_sha256", "witness_sha256", "byte_preservation_only"}
            and type(guard["generation"]) is int and guard["generation"] == generation and guard["byte_preservation_only"] is True
            and all(isinstance(guard[key], str) and re.fullmatch(r"[0-9a-f]{64}", guard[key]) for key in ("ledger_sha256", "witness_sha256")), "phase_guard_pair")
    else:
        check(receipt["guard"] is None, "phase_no_guard")
    return receipt


class Controller(d.Controller):
    def __init__(self, args):
        super().__init__(args)
        self.anchor = anchor_at(args.release_anchor, args.release_anchor_sha256)
        for key, value in {"RELEASE_ID": self.anchor["release_id"], "RELEASE_ASSET_ID": self.anchor["asset_id"],
                           "RELEASE_ASSET_BYTES": self.anchor["asset_bytes"]}.items():
            setattr(d, key, value)

    def prepare(self, candidate_inventory, baseline_inventory):
        self.stage = "fresh_disposable_configuration"
        self.stop_core()
        self.guest("umask 077; mkdir -m 700 " + d.GUEST_ROOT, 30)
        staging = self.private / "staging"
        shutil.copytree(HERE / "guest_helper", staging / "custom_components")
        with d.zipfile.ZipFile(self.args.hacs_zip) as archive:
            archive.extractall(staging / "custom_components/hacs")
        archive_path = self.private / "staging.tgz"
        with tarfile.open(archive_path, "w:gz", format=tarfile.PAX_FORMAT) as archive:
            archive.add(staging / "custom_components", arcname="custom_components")
        self.guest_write(d.GUEST_ROOT + "/staging.tgz", archive_path.read_bytes())
        self.guest("set -eu; umask 077; tar -xzf " + d.GUEST_ROOT + "/staging.tgz -C " + self.config_path
            + "; mkdir -m 700 " + self.config_path + "/" + d.CONTROL + " " + self.config_path + "/" + d.RESULTS
            + "; mkdir -p " + self.config_path + "/www", 60)
        inputs = {"schema": 1, "source_commit": SOURCE, "candidate_sha256": CANDIDATE, "baseline_sha256": BASELINE,
            "inventory_sha256": INVENTORY, "anchor": self.anchor, "anchor_sha256": self.args.release_anchor_sha256,
            "candidate_inventory": candidate_inventory, "baseline_inventory": baseline_inventory, "core_version": CORE,
            "branch": d.REPOSITORY, "branch_commit": self.args.branch_commit}
        self.guest_write(self.config_path + "/" + d.CONTROL + "/inputs.json", canonical(inputs))
        token = os.environ.pop("GITHUB_TOKEN")
        check(isinstance(token, str) and 20 <= len(token) <= 1024 and "\n" not in token, "ephemeral_job_token")
        self.guest_write(self.config_path + "/" + d.CONTROL + "/github-token", token.encode())
        token = None
        self.token_injected = True
        configuration = {"homeassistant": {"name": "Synthetic HACS qualification", "time_zone": "UTC"},
            "frontend": {}, "http": {}, "lovelace": {}, "person": {}, "zone": {}, "websocket_api": {},
            "image_upload": {}, "homecircle_hacs_release_qa": {"disposable": True}}
        self.guest_write(self.config_path + "/configuration.yaml", canonical(configuration))
        self.guest_write(self.config_path + "/www/example_hacs_unrelated.js", b"/* synthetic unrelated HACS asset */\n")
        self.guest("set -eu; chmod 600 " + self.config_path + "/" + d.CONTROL + "/* " + self.config_path
            + "/configuration.yaml; rm " + d.GUEST_ROOT + "/staging.tgz", 30)

    def phase(self, name, start=False):
        self.stage = name
        instruction = {"schema": 1, "token": self.nonce, "phase": name,
                       "branch": d.REPOSITORY, "branch_commit": self.args.branch_commit}
        # Publish a complete instruction by rename; never expose a truncate gap.
        path = self.config_path + "/" + d.CONTROL + "/phase.json"
        temporary = path + "." + secrets.token_hex(8)
        self.guest_write(temporary, canonical(instruction))
        self.guest("set -eu; chmod 600 " + temporary + "; mv " + temporary + " " + path, 30)
        if start:
            self.guest("find " + self.config_path + "/custom_components/homecircle -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || test ! -d " + self.config_path + "/custom_components/homecircle", 30)
            self.start_core()
        end = time.monotonic() + self.remaining(660)
        receipt_path = self.config_path + "/" + d.RESULTS + "/" + name + ".json"
        while time.monotonic() < end:
            exists = self.guest("if test -f " + receipt_path + "; then printf yes; else printf no; fi", 10)
            if exists == b"yes":
                receipt = json.loads(self.guest_read(receipt_path))
                if receipt.get("outcome") != "passed":
                    failure = receipt.get("failure", {})
                    safe = {"stage": failure.get("stage") if failure.get("stage") in {"inputs", "hacs_ready", "config_entry_remove", "hacs_uninstall", "hacs_catalog", "persistent_state", "hacs_download", "installed_bytes"} else None,
                            "type": failure.get("type") if failure.get("type") in {"Refused", "ValueError", "TypeError", "RuntimeError", "TimeoutError", "OSError", "KeyError", "AttributeError"} else "OtherError",
                            "code": failure.get("code") if isinstance(failure.get("code"), str) and re.fullmatch(r"qa_[a-z0-9_]{1,76}", failure["code"]) else None}
                    d.write_json(self.public / "failure.json", {"schema": 1, "phase": name, "failure": safe})
                    raise Refused("guest_phase_refused")
                projected = phase_check(name, receipt, anchor_sha=self.args.release_anchor_sha256,
                    branch=self.args.branch_commit, nonce=self.nonce, inventories=self.inventories)
                d.write_json(self.public / (name + ".json"), projected)
                self.phases.append(projected)
                print("hacs_rc_phase=" + name + ":passed", flush=True)
                return
            time.sleep(1)
        raise Refused("guest_phase_deadline")

    def profile_copy(self, name, *, restore=False, keep_guard=False):
        self.stop_core()
        root = d.GUEST_ROOT + "/" + name
        config = self.config_path
        if not restore:
            self.guest("set -eu; umask 077; mkdir -m 700 " + root + "; cp -a " + config + "/.storage " + root + "/.storage; "
                "if test -d " + config + "/image; then cp -a " + config + "/image " + root + "/image; fi", 60)
            return
        prefix = ""
        suffix = ""
        if keep_guard:
            prefix = ("mkdir -m 700 " + d.GUEST_ROOT + "/newest; cp -a " + config + "/.storage/homecircle_findmy/recovery_guard " + d.GUEST_ROOT + "/newest/ledger; "
                      "cp -a " + config + "/.cache/homecircle_findmy/recovery_guard " + d.GUEST_ROOT + "/newest/witness; ")
            suffix = ("mkdir -p " + config + "/.storage/homecircle_findmy " + config + "/.cache/homecircle_findmy; "
                      "rm -rf " + config + "/.storage/homecircle_findmy/recovery_guard " + config + "/.cache/homecircle_findmy/recovery_guard; "
                      "cp -a " + d.GUEST_ROOT + "/newest/ledger " + config + "/.storage/homecircle_findmy/recovery_guard; "
                      "cp -a " + d.GUEST_ROOT + "/newest/witness " + config + "/.cache/homecircle_findmy/recovery_guard; ")
        self.guest("set -eu; umask 077; " + prefix + "rm -rf " + config + "/.storage " + config + "/image; cp -a "
            + root + "/.storage " + config + "/.storage; if test -d " + root + "/image; then cp -a " + root + "/image "
            + config + "/image; fi; " + suffix + ("rm -f " + config + "/" + d.CONTROL + "/baseline.json" if not keep_guard else "true"), 60)
        if keep_guard:
            self.rollback_restored = True

    def run(self):
        check(sys.platform == "linux" and os.uname().machine == "x86_64", "native_linux_amd64_required")
        check(Path("/dev/kvm").exists() and os.access("/dev/kvm", os.R_OK | os.W_OK), "accessible_kvm_required")
        check(re.fullmatch(r"[0-9a-f]{40}", self.args.branch_commit), "qa_branch_commit")
        check(not self.args.output.exists() and not self.args.output.is_symlink(), "fresh_output")
        self.args.output.mkdir(mode=0o700, parents=True)
        self.public = self.args.output / "public-summary"
        self.public.mkdir(mode=0o700)
        self.private = Path(tempfile.mkdtemp(prefix="private-", dir=self.args.output))
        candidate = inventory_at(self.args.inventory, INVENTORY, self.args.candidate_zip, CANDIDATE)
        baseline = inventory_at(self.args.baseline_inventory, BASE_INVENTORY, self.args.baseline_zip, BASELINE)
        self.inventories = {"candidate": candidate, "baseline": baseline}
        d.check_archive(self.args.hacs_zip, HACS_SHA, None)
        self.provenance = {"source_commit": SOURCE, "source_files": 402, "candidate_sha256": CANDIDATE,
            "inventory_sha256": INVENTORY, "baseline_sha256": BASELINE, "baseline_inventory_sha256": BASE_INVENTORY,
            "hacs_sha256": HACS_SHA, "haos_sha256": d.HAOS_XZ_SHA, "helper_files": files_at(HERE / "guest_helper"),
            "controller_sha256": digest(Path(__file__).read_bytes()), "donor_host_sha256": digest((HERE / "donor_host.py").read_bytes()),
            "anchor_sha256": self.args.release_anchor_sha256}
        self.verify_published_release()
        self.start_vm(self.download_haos())
        self.wait_managed()
        self.prepare(candidate, baseline)
        self.phase("bootstrap_hacs", start=True)
        self.profile_copy("clean-hacs")
        self.phase("fresh_download", start=True)
        self.stop_core()
        self.phase("fresh", start=True)
        self.phase("fresh_remove")
        self.stop_core()
        self.phase("fresh_removed", start=True)
        self.profile_copy("clean-hacs", restore=True)
        self.phase("baseline_download", start=True)
        self.stop_core()
        self.phase("baseline", start=True)
        self.profile_copy("baseline")
        self.phase("upgrade_download", start=True)
        self.stop_core()
        self.phase("upgraded", start=True)
        self.stop_core()
        self.phase("restart", start=True)
        self.phase("rollback_download")
        self.profile_copy("baseline", restore=True, keep_guard=True)
        self.phase("rollback", start=True)
        self.phase("reupgrade_download")
        self.stop_core()
        self.phase("final", start=True)
        by_name = {receipt["phase"]: receipt for receipt in self.phases}
        check(tuple(by_name) == PHASES, "all_phases_required")
        check(all(by_name[name]["snapshot_sha256"] == by_name["baseline"]["snapshot_sha256"] for name in ACTIVE - {"fresh"}), "snapshot_continuity")
        check(all(by_name[name]["activity"] == by_name["baseline"]["activity"] for name in ACTIVE - {"fresh"}), "activity_marker_continuity")
        check(all(by_name[name]["guard"] == by_name["upgraded"]["guard"] for name in ("restart", "rollback_download", "rollback", "reupgrade_download", "final")), "newest_guard_pair_continuity")
        for before, after in (("fresh_download", "fresh"), ("fresh_remove", "fresh_removed"), ("baseline_download", "baseline"),
                              ("upgrade_download", "upgraded"), ("upgraded", "restart"), ("rollback_download", "rollback"), ("reupgrade_download", "final")):
            check(by_name[before]["process"]["start_ticks"] != by_name[after]["process"]["start_ticks"], "fresh_core_process_required")
        self.stop_core()
        self.stage = "acceptance_complete"
        self.acceptance = True

    def finish(self, failure):
        self.cleanup_vm()
        passed = self.acceptance and failure is None and not self.cleanup["cleanup_failed"]
        receipt = {"schema": 1, "outcome": "passed" if passed else "failed_or_incomplete", "source_commit": SOURCE,
            "candidate_sha256": CANDIDATE, "baseline_sha256": BASELINE, "anchor_sha256": self.args.release_anchor_sha256,
            "branch_commit": self.args.branch_commit, "nonce_sha256": digest(self.nonce.encode()), "phase_count": len(self.phases),
            "core_version": CORE, "hacs_version": HACS, "actual_kvm": self.kvm_confirmed, "provenance": self.provenance,
            "core_actions": self.core_actions, "ephemeral_job_token": self.token_injected, "oauth_onboarding": False,
            "direct_candidate_installs": self.direct_installs, "provider_accounts": 0, "owner_accounts": 0,
            "recovery_api_calls": 0, "supervisor_backup_restore": False, "stopped_configuration_rollback": self.rollback_restored,
            "guard_claim": "synthetic_opaque_byte_preservation_only", "host_elapsed_seconds": round(time.monotonic() - self.started, 3),
            "failure": {"stage": self.stage, "type": type(failure).__name__,
                "code": str(failure) if isinstance(failure, (Refused, ValueError)) and re.fullmatch(r"[a-z0-9_]{1,80}", str(failure)) else None} if failure else None,
            **self.cleanup}
        if self.public:
            d.write_json(self.public / "host.json", receipt)
        return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("candidate-zip", "inventory", "baseline-zip", "baseline-inventory", "hacs-zip", "release-anchor", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--release-anchor-sha256", required=True)
    parser.add_argument("--branch-commit", required=True)
    args = parser.parse_args()
    controller = Controller(args)
    for event in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(event, lambda *_args: (_ for _ in ()).throw(Refused("host_interrupted")))
    failure = None
    try:
        controller.run()
    except BaseException as error:
        failure = error
    return controller.finish(failure)


if __name__ == "__main__":
    raise SystemExit(main())
