"""Offline replay of retained, already accepted minimum-Core evidence.

Needs the immutable QA checkout's native-rc-minimum input files. Never runs them.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
SOURCE = "c7b31c5a82431a6b16d8b7208f9423626b95bd4b"
HEAD = "93c68c83d49275026539309a2dc49e712ed97071"
RUN = 40002540583
ARTIFACT = "955d6a4d4fba2b61aa650b133647ea1ff6744c32840d716c5ca3814ce893b58e"
CONSUMER = "5742f95ca99b32aa0dfc06c4b97b15d8a316bac7030bc778cd4ac89153854a51"
CONTROL = "0ce3f8318f46235fdd952812833fa7b0516d7f07a750440150257deac61988b3"
INPUTS = "8b26b5ea700e5684ce6904fc98af2e3af6ee482a5994e355fc7a5205d4120bbc"
ANCHORS = "ed938d3758555c85624989770e861957d4489aeadf5d913ccd07f4a14a7a4471"
WORKFLOW = "d194ed562140a390ab83436355301456df33d849225dab5ee356b0b9862f5e47"
RECEIPTS = {"host.json", "lifecycle-summary.json", "setup-summary.json", "source-summary.json"}


def check(value, code):
    if not value:
        raise ValueError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def same(actual, expected):
    return json.dumps(actual, sort_keys=True, separators=(",", ":"), allow_nan=False) == json.dumps(
        expected, sort_keys=True, separators=(",", ":"), allow_nan=False)


def regular(root, name):
    path = PurePosixPath(name)
    check(path.parts and not path.is_absolute() and ".." not in path.parts and "\\" not in name, "relative_path_required")
    target = root
    for part in path.parts:
        target = target / part
        check(not target.is_symlink(), "symlink_refused")
    check(stat.S_ISREG(target.stat().st_mode), "regular_file_required")
    return target


def raw_at(root, name, expected=None):
    path = regular(root, name)
    check(path.stat().st_size <= 16 * 1024**2, "bounded_public_input")
    raw = path.read_bytes()
    check(expected is None or sha(raw) == expected, "frozen_file_hash_refused")
    return raw


def unique(pairs):
    value = {}
    for key, item in pairs:
        check(key not in value, "duplicate_json_key")
        value[key] = item
    return value


def read(root, name, expected=None):
    return json.loads(raw_at(root, name, expected), object_pairs_hook=unique)


def replay(checkout, manifest_sha):
    manifest = read(HERE, "MANIFEST.json", manifest_sha)
    check(set(manifest) == {"schema", "scope", "files"} and manifest["schema"] == 1
          and len(manifest["files"]) == 19, "exact_retained_manifest")
    actual = set()
    for path in HERE.rglob("*"):
        check(not path.is_symlink(), "retained_tree_symlink")
        if path.is_file() and "__pycache__" not in path.parts:
            actual.add(path.relative_to(HERE).as_posix())
    check(actual == set(manifest["files"]) | {"MANIFEST.json"}, "exact_twenty_retained_files")
    for name, expected in manifest["files"].items():
        raw = raw_at(HERE, name)
        check(same(expected, {"bytes": len(raw), "sha256": sha(raw)}), "retained_file_bytes_changed")
    expected_artifacts = {"rc-minimum-validation-receipts": {"id": 12522208110, "safe_members": 4, "zip_sha256": ARTIFACT}}
    metadata = read(HERE, "ROOT-METADATA.json")
    check(same(metadata, {"schema": 1, "artifact_id": 12522208110, "artifact_name": "rc-minimum-validation-receipts",
        "artifact_zip_sha256": ARTIFACT, "branch": "codex/native-amd64-validation", "conclusion": "success",
        "event": "push", "github_digest_verified": True, "head_sha": HEAD, "run_attempt": 1, "run_id": RUN,
        "status": "completed", "workflow_path": ".github/workflows/native-rc-minimum.yml", "workflow_sha256": WORKFLOW}), "saved_metadata_binding")
    anchors = read(HERE, "RUN-ANCHORS.json", ANCHORS)
    check(anchors["frozen"] is True and anchors["source_commit"] == SOURCE and anchors["qa_head"] == HEAD
          and anchors["run_id"] == RUN and anchors["run_attempt"] == 1 and anchors["event"] == "push"
          and anchors["input_map_sha256"] == INPUTS and anchors["input_count"] == 12
          and anchors["workflow_sha256"] == WORKFLOW and anchors["artifact_name"] == metadata["artifact_name"], "pre_run_anchor_binding")
    downloaded = read(HERE, "DOWNLOAD-VERIFICATION.json")
    check(same(downloaded, {"schema": 1, "artifacts": expected_artifacts, "event": "push",
        "github_digests_verified": True, "owner_instance_actions": 0, "qa_head": HEAD, "run_attempt": 1,
        "run_id": RUN, "source": SOURCE}), "saved_download_binding")
    transport = read(HERE, "TRANSPORT-ACCEPTED.json")
    check(same(transport.get("artifacts"), expected_artifacts) and transport.get("observed_conclusion") == "success"
          and transport.get("original_download_verification_sha256") == sha(raw_at(HERE, "DOWNLOAD-VERIFICATION.json"))
          and transport.get("source") == SOURCE and transport.get("run_id") == RUN
          and transport.get("qa_head") == HEAD and transport.get("github_digests_verified") is True,
          "saved_fresh_transport_binding")
    raw_at(HERE, "artifact.zip", ARTIFACT)
    with zipfile.ZipFile(HERE / "artifact.zip") as archive:
        members = archive.infolist()
        check(len(members) == 4 and {item.filename for item in members} == RECEIPTS, "exact_artifact_members")
        for item in members:
            check(not item.is_dir() and item.file_size <= 2 * 1024**2
                  and stat.S_IFMT(item.external_attr >> 16) in {0, stat.S_IFREG}, "safe_artifact_member")
            check(archive.read(item) == raw_at(HERE, "receipts/" + item.filename), "artifact_receipt_bytes_changed")
    inputs = read(HERE, "INPUTS.json", INPUTS)
    control = read(HERE, "CONSUMER-CONTROL.json", CONTROL)
    check(inputs["source_commit"] == SOURCE and inputs["fixture_name"] == "native-rc-minimum"
          and len(inputs["files"]) == 12 and len(control["frozen_inputs"]) == 11, "frozen_input_map_binding")
    check({name: item for name, item in inputs["files"].items() if not name.startswith(".github/")}
          == control["frozen_inputs"], "original_consumer_inputs_match")
    committed_inputs = {}
    for name, expected in inputs["files"].items():
        full_name = name if name.startswith(".github/") else "native-rc-minimum/" + name
        raw = raw_at(checkout, full_name)
        check(same(expected, {"bytes": len(raw), "sha256": sha(raw)}), "external_QA_input_changed")
        committed_inputs[full_name] = expected
    raw_at(HERE, "verify_results.py", CONSUMER)
    root_raw, peer_raw = raw_at(HERE, "ROOT-ACCEPTED.json"), raw_at(HERE, "PEER-ACCEPTED.json")
    check(root_raw == peer_raw, "root_peer_acceptance_bytes_differ")
    peer = read(HERE, "PEER-REPLAY-VERIFICATION.json")
    check(peer.get("outcome") == "accepted" and peer.get("root_acceptance_byte_identical") is True
          and peer.get("acceptance_sha256") == sha(root_raw) and peer.get("consumer_sha256") == CONSUMER
          and peer.get("consumer_control_sha256") == CONTROL and peer.get("run_anchors_sha256") == ANCHORS
          and peer.get("input_map_sha256") == INPUTS and peer.get("artifact_zip_sha256") == ARTIFACT
          and peer.get("run_id") == RUN and peer.get("qa_head") == HEAD
          and same(peer.get("actual_committed_inputs_verified"), committed_inputs), "peer_saved_review_binding")
    with tempfile.TemporaryDirectory(prefix="homecircle-minimum-replay-") as temporary:
        temp = Path(temporary)
        for name in control["frozen_inputs"]:
            source = regular(checkout, "native-rc-minimum/" + name)
            target = temp / "harness" / name
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        for name in ("CORE-GRAPH.json", "STARTUP-VERSIONS.json"):
            shutil.copyfile(HERE / name, temp / name)
        spec = importlib.util.spec_from_file_location("original_minimum_consumer", HERE / "verify_results.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.HERE = temp
        accepted = module.consume(HERE / "CONSUMER-CONTROL.json", CONTROL, HERE / "receipts")
    check(same(accepted, json.loads(root_raw, object_pairs_hook=unique)), "original_consumer_replay_mismatch")
    return {"schema": 1, "outcome": "accepted", "run_id": RUN, "qa_head": HEAD,
        "source_commit": SOURCE, "package_sha256": control["archive_sha256"], "artifact_zip_sha256": ARTIFACT,
        "external_input_files_checked": 12, "retained_files_checked": 20,
        "focused_passed": 20, "separate_core_processes": 4,
        "transport_basis": "retained GitHub metadata and saved verified digest; no fresh network request",
        "original_consumer_byte_identical": True, "root_peer_acceptance_matched": True,
        "new_native_execution": False, "network_requests": 0, "provider_imports": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qa-checkout", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(replay(args.qa_checkout, args.manifest_sha256), sort_keys=True))


if __name__ == "__main__":
    main()

