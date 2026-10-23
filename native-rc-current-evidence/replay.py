"""Offline replay of retained current-Core qualification; never runs its harness."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import stat

HERE = Path(__file__).resolve().parent
HEAD = "6dfca95d6c1032cadd0bd18d6afbcad7f709f255"
SOURCE = "b906d3ee51711d3455a497cc265fd3bc18f3adec"
RUN = 40010260549
CONSUMER = "683fb927cf38ec96629deede221fbd812e9e4f539fcb28ce343e8c632bc3e471"
ANCHORS = "8db9c2b3d21e1e73c524c9b2f79d60bd420e4253241c07ed587a953adc176ef5"
INPUTS = "06d3421d2862d1e4251a946689f4938bb00babee32ee6c78c0cd3eb36ae1efe3"
WORKFLOW = ".github/workflows/native-rc-current-r3.yml"
PREFIX = "native-rc-current-r3"


def check(value, code):
    if not value:
        raise ValueError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def regular(root, name):
    path = PurePosixPath(name)
    check(path.parts and not path.is_absolute() and not {".", ".."}.intersection(path.parts)
          and path.as_posix() == name and "\\" not in name, "relative_path_required")
    check(not root.is_symlink(), "root_symlink_refused")
    target = root
    for part in path.parts:
        target = target / part
        check(not target.is_symlink(), "symlink_refused")
    check(stat.S_ISREG(target.stat().st_mode) and target.stat().st_size <= 64 * 1024**2,
          "bounded_regular_public_input_required")
    return target


def raw_at(root, name, expected=None):
    raw = regular(root, name).read_bytes()
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
          and len(manifest["files"]) == 19, "exact_retained_manifest_required")
    actual = set()
    for path in HERE.rglob("*"):
        check(not path.is_symlink(), "retained_tree_symlink_refused")
        if path.is_file() and "__pycache__" not in path.parts:
            actual.add(path.relative_to(HERE).as_posix())
    check(actual == set(manifest["files"]) | {"MANIFEST.json"}, "exact_twenty_retained_files_required")
    for name, expected in manifest["files"].items():
        raw = raw_at(HERE, name)
        check(expected == {"bytes": len(raw), "sha256": sha(raw)}, "retained_file_bytes_changed")

    raw_at(HERE, "independent_package.py", CONSUMER)
    anchors = read(HERE, "RUN-ANCHORS.json", ANCHORS)
    inputs = read(HERE, "INPUTS.json", INPUTS)
    check(anchors["qa_head"] == HEAD and anchors["source_commit"] == SOURCE
          and anchors["run_id"] == RUN and inputs["source_commit"] == SOURCE
          and inputs["fixture_name"] == PREFIX and len(inputs["files"]) == 14,
          "frozen_QA_source_run_binding_refused")
    committed = {}
    for name, expected in inputs["files"].items():
        full_name = name if name == WORKFLOW else PREFIX + "/" + name
        raw = raw_at(checkout, full_name)
        check(expected == {"bytes": len(raw), "sha256": sha(raw)}, "external_QA_input_changed")
        committed[full_name] = expected

    root_raw = raw_at(HERE, "ROOT-ACCEPTED.json")
    check(root_raw == raw_at(HERE, "PEER-ACCEPTED.json"), "root_peer_acceptance_bytes_differ")
    metadata = read(HERE, "ROOT-METADATA.json")
    candidate_metadata = read(HERE, "ROOT-CANDIDATE-METADATA.json")
    expected_artifacts = {
        metadata["artifact_name"]: {"id": metadata["artifact_id"], "safe_members": 6,
                                    "zip_sha256": sha(raw_at(HERE, "artifact.zip"))},
        candidate_metadata["artifact_name"]: {"id": candidate_metadata["artifact_id"], "safe_members": 2,
                                    "zip_sha256": sha(raw_at(HERE, "candidate-artifact.zip"))},
    }
    downloaded = read(HERE, "DOWNLOAD-VERIFICATION.json")
    check(downloaded == {"schema": 1, "run_id": RUN, "qa_head": HEAD, "source": SOURCE,
          "event": "push", "run_attempt": 1, "github_digests_verified": True,
          "artifacts": expected_artifacts, "owner_instance_actions": 0, "observed_conclusion": "success"},
          "saved_download_binding_refused")
    transport = read(HERE, "TRANSPORT-ACCEPTED.json")
    check(transport.get("artifacts") == expected_artifacts and transport.get("observed_conclusion") == "success"
          and transport.get("original_download_verification_sha256") == sha(raw_at(HERE, "DOWNLOAD-VERIFICATION.json"))
          and transport.get("source") == SOURCE and transport.get("run_id") == RUN
          and transport.get("qa_head") == HEAD and transport.get("github_digests_verified") is True,
          "saved_transport_binding_refused")
    peer = read(HERE, "PEER-REPLAY-VERIFICATION.json")
    check(peer.get("outcome") == "accepted" and peer.get("root_acceptance_byte_identical") is True
          and peer.get("acceptance_sha256") == sha(root_raw) and peer.get("consumer_sha256") == CONSUMER
          and peer.get("run_anchors_sha256") == ANCHORS and peer.get("input_map_sha256") == INPUTS
          and peer.get("run_id") == RUN and peer.get("qa_head") == HEAD
          and peer.get("actual_committed_inputs_verified") == committed,
          "peer_saved_review_binding_refused")

    # Only the exact original stdlib consumer is imported. External QA drivers,
    # source modules, package builders and provider libraries are never imported.
    spec = importlib.util.spec_from_file_location("retained_current_consumer", HERE / "independent_package.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.load_run_anchors(HERE / "RUN-ANCHORS.json", ANCHORS)
    accepted = module.review(HERE / "artifact.zip", HERE / "ROOT-METADATA.json",
        HERE / "candidate-artifact.zip", HERE / "ROOT-CANDIDATE-METADATA.json",
        checkout / PREFIX, checkout / WORKFLOW, HERE / "INPUTS.json")
    check(encoded(accepted) == root_raw, "original_consumer_replay_bytes_differ")
    return {"schema": 1, "outcome": "accepted", "run_id": RUN, "qa_head": HEAD,
        "source_commit": SOURCE, "retained_files_checked": 20, "external_input_files_checked": 14,
        "original_consumer_byte_identical": True, "root_peer_acceptance_matched": True,
        "scoped_acceptance": accepted["scoped_acceptance"],
        "transport_basis": "retained GitHub metadata and saved verified digests; no fresh network request",
        "new_native_execution": False, "network_requests": 0, "provider_imports": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qa-checkout", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(replay(args.qa_checkout, args.manifest_sha256), sort_keys=True))


if __name__ == "__main__":
    main()
