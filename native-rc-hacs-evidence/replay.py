"""Offline replay of one retained successful HACS run; never runs its harness."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import stat
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
HEAD = "38e9b19264e79ef452a7f3131a163e174b783227"
SOURCE = "b906d3ee51711d3455a497cc265fd3bc18f3adec"
RUN = 40013210859
CONSUMER = "42557e371570b09150f1fb8b6963bd97d45c5e1f40f55db64ac018ae1233283a"
ANCHORS = "4a86cf771231ffc85f3b49f8894a83e55f7a9daec614551e5c7a3d6abc150c44"
INPUTS = "28d9ba9b435da845c20c086d19b104d4690e837ee2b18253912a56e1cd2a4668"
PUBLIC_ANCHOR = "8c4dbcf76cbab338de290dfbb6600f1fff83a037dbeea1d3f7181e36d5ed842f"
PREPARATION = "bb81812c1dd631d3e014b8e64b258cd3b019b88e347abfbad363efba7d1d297a"
WORKFLOW_SHA = "7d8c5c4eab56ee51c2afaf2ff879d204237cbc4d0bd32ac1e37f0dfa45123dbd"
WORKFLOW = ".github/workflows/native-final-hacs.yml"
PREFIX = "native-final-hacs"
PHASES = ("bootstrap_hacs", "fresh_download", "fresh", "fresh_remove", "fresh_removed",
          "baseline_download", "baseline", "upgrade_download", "upgraded", "restart",
          "rollback_download", "rollback", "reupgrade_download", "final")
RECEIPTS = {name + ".json" for name in PHASES} | {"host.json", "independent-review.json"}


def check(value, code):
    if not value:
        raise ValueError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def same(actual, expected):
    return json.dumps(actual, sort_keys=True, separators=(",", ":"), allow_nan=False) == json.dumps(
        expected, sort_keys=True, separators=(",", ":"), allow_nan=False)


def regular(root, name):
    path = PurePosixPath(name)
    check(path.parts and not path.is_absolute() and not {".", ".."}.intersection(path.parts)
          and path.as_posix() == name and "\\" not in name, "relative_path_required")
    check(not root.is_symlink(), "root_symlink_refused")
    target = root
    for part in path.parts:
        target = target / part
        check(not target.is_symlink(), "symlink_refused")
    check(stat.S_ISREG(target.stat().st_mode) and target.stat().st_size <= 2 * 1024**2,
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
        if path.is_dir():
            continue
        check(stat.S_ISREG(path.stat().st_mode), "retained_special_file_refused")
        if "__pycache__" not in path.parts:
            actual.add(path.relative_to(HERE).as_posix())
    check(actual == set(manifest["files"]) | {"MANIFEST.json"}, "exact_twenty_retained_files_required")
    for name, expected in manifest["files"].items():
        raw = raw_at(HERE, name)
        check(same(expected, {"bytes": len(raw), "sha256": sha(raw)}), "retained_file_bytes_changed")
    raw_at(HERE, "verify_results.py", CONSUMER)
    anchors = read(HERE, "RUN-ANCHORS.json", ANCHORS)
    inputs = read(HERE, "INPUTS.json", INPUTS)
    check(anchors["frozen"] is True and anchors["qa_head"] == HEAD and anchors["source_commit"] == SOURCE
          and anchors["run_id"] == RUN and anchors["run_attempt"] == 1 and anchors["event"] == "push"
          and anchors["workflow_path"] == WORKFLOW and anchors["workflow_sha256"] == WORKFLOW_SHA
          and anchors["input_count"] == 18 and inputs["source_commit"] == SOURCE
          and inputs["fixture_name"] == PREFIX and len(inputs["files"]) == 18,
          "frozen_QA_source_run_binding_refused")
    committed = {}
    for name, expected in inputs["files"].items():
        full_name = name if name == WORKFLOW else PREFIX + "/" + name
        raw = raw_at(checkout, full_name)
        check(same(expected, {"bytes": len(raw), "sha256": sha(raw)}), "external_QA_input_changed")
        committed[full_name] = expected
    public_anchor = read(HERE, "release-anchor.json", PUBLIC_ANCHOR)
    preparation = read(HERE, "PREPARATION-MANIFEST.json", PREPARATION)
    finalization = read(HERE, "FINALIZATION.json")
    provenance = read(HERE, "expected-provenance.json")
    inner = read(checkout, PREFIX + "/INPUTS.json", finalization["input_map_sha256"])
    check(finalization["source_commit"] == SOURCE and finalization["preparation_manifest_sha256"] == PREPARATION
          and finalization["release_anchor_sha256"] == PUBLIC_ANCHOR and finalization["workflow_sha256"] == WORKFLOW_SHA
          and finalization["input_files"] == 16 and len(inner["files"]) == 16
          and same(finalization["contracts"], {"donor": 45, "current": 16, "total": 61})
          and provenance["source_commit"] == SOURCE and provenance["anchor_sha256"] == PUBLIC_ANCHOR,
          "finalized_packet_binding_refused")
    for name, fingerprint in inner["files"].items():
        check(same(fingerprint, inputs["files"][name]), "inner_input_map_binding_refused")
        if name in preparation["files"]:
            check(same(fingerprint, preparation["files"][name]), "prepared_runtime_bytes_changed")
    check(raw_at(HERE, "expected-provenance.json") == raw_at(checkout, PREFIX + "/expected-provenance.json")
          and raw_at(HERE, "release-anchor.json") == raw_at(checkout, PREFIX + "/release-anchor.json"),
          "actual_runtime_anchor_bytes_changed")
    publication = read(HERE, "RC-PUBLICATION-READBACK.json")
    check(publication["source"] == SOURCE and publication["release_id"] == public_anchor["release_id"] == 422230061
          and publication["tag_resolves_exact_source"] is True and publication["prerelease"] is True
          and publication["draft"] is False and publication["stable_publication_performed"] is False,
          "saved_public_RC_identity_refused")
    for name, identity, size, fingerprint in (
            ("homecircle.zip", "asset_id", "asset_bytes", "candidate_sha256"),
            ("inventory.json", "inventory_asset_id", "inventory_bytes", "inventory_sha256")):
        asset = publication["assets"][name]
        check(asset["anonymous_download_verified"] is True and asset["id"] == public_anchor[identity]
              and asset["bytes"] == public_anchor[size] and asset["sha256"] == public_anchor[fingerprint],
              "saved_public_asset_binding_refused")
    raw_at(HERE, "candidate-inventory.json", "e4bc34e3921e75157402cf643f87ed658d95c76505a448abb393fd90a304db12")
    raw_at(HERE, "baseline-inventory.json", "5e724f69ff20a711dd87b2a39ed96818781813bb6f1e7b3addedc6e048593d77")

    metadata = read(HERE, "ROOT-METADATA.json")
    check(metadata["schema"] == 1 and metadata["run_id"] == RUN and metadata["run_attempt"] == 1
          and metadata["head_sha"] == HEAD and metadata["event"] == "push"
          and metadata["branch"] == "codex/native-amd64-validation" and metadata["workflow_path"] == WORKFLOW
          and metadata["workflow_sha256"] == WORKFLOW_SHA and metadata["github_digest_verified"] is True
          and metadata["status"] == "completed" and metadata["conclusion"] == "success"
          and metadata["artifact_name"] == "final-hacs-qualification-receipts"
          and type(metadata["artifact_id"]) is int and metadata["artifact_id"] > 0, "saved_success_metadata_refused")
    artifact_raw = raw_at(HERE, "artifact.zip", metadata["artifact_zip_sha256"])
    expected_artifacts = {metadata["artifact_name"]: {"id": metadata["artifact_id"], "safe_members": 16,
                                                   "zip_sha256": sha(artifact_raw)}}
    downloaded = read(HERE, "DOWNLOAD-VERIFICATION.json")
    check(same(downloaded, {"schema": 1, "run_id": RUN, "qa_head": HEAD, "source": SOURCE,
          "event": "push", "run_attempt": 1, "github_digests_verified": True,
          "artifacts": expected_artifacts, "owner_instance_actions": 0, "observed_conclusion": "success"}),
          "saved_download_binding_refused")
    transport = read(HERE, "TRANSPORT-ACCEPTED.json")
    check(same(transport.get("artifacts"), expected_artifacts) and transport.get("observed_conclusion") == "success"
          and transport.get("original_download_verification_sha256") == sha(raw_at(HERE, "DOWNLOAD-VERIFICATION.json"))
          and transport.get("source") == SOURCE and transport.get("run_id") == RUN
          and transport.get("qa_head") == HEAD and transport.get("github_digests_verified") is True,
          "saved_transport_binding_refused")
    root_raw = raw_at(HERE, "ROOT-INDEPENDENT-REVIEW.json")
    check(root_raw == raw_at(HERE, "PEER-INDEPENDENT-REVIEW.json"), "root_peer_acceptance_bytes_differ")
    peer = read(HERE, "PEER-REPLAY-VERIFICATION.json")
    check(peer.get("outcome") == "accepted" and peer.get("root_acceptance_byte_identical") is True
          and peer.get("acceptance_sha256") == sha(root_raw) and peer.get("consumer_sha256") == CONSUMER
          and peer.get("run_anchors_sha256") == ANCHORS and peer.get("input_map_sha256") == INPUTS
          and peer.get("run_id") == RUN and peer.get("qa_head") == HEAD
          and peer.get("artifact_zip_sha256") == sha(artifact_raw)
          and same(peer.get("actual_committed_inputs_verified"), committed), "peer_saved_review_binding_refused")

    # Import only the exact original stdlib receipt consumer, never QA/HA code.
    spec = importlib.util.spec_from_file_location("retained_HACS_consumer", HERE / "verify_results.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix="homecircle-HACS-retained-replay-") as temporary:
        temp = Path(temporary)
        total = 0
        with zipfile.ZipFile(io.BytesIO(artifact_raw)) as archive:
            members = archive.infolist()
            check(len(members) == 16 and {item.filename for item in members} == RECEIPTS, "exact_artifact_members_required")
            for item in members:
                check(not item.is_dir() and stat.S_IFMT(item.external_attr >> 16) in {0, stat.S_IFREG}
                      and not item.flag_bits & 1 and 0 < item.file_size <= 1024**2, "safe_JSON_member_required")
                total += item.file_size
                check(total <= 2 * 1024**2, "artifact_expansion_bound_required")
                content = archive.read(item)
                check(type(json.loads(content, object_pairs_hook=unique)) is dict, "JSON_object_required")
                with (temp / item.filename).open("xb") as stream:
                    stream.write(content)
        accepted = module.accept(module.read(temp / "host.json"),
            {name: module.read(temp / (name + ".json")) for name in PHASES},
            {"rc": module.read(HERE / "candidate-inventory.json")["files"],
             "base": module.read(HERE / "baseline-inventory.json")["files"]},
            anchor_sha=PUBLIC_ANCHOR, branch=HEAD, inputs=provenance)
        check(encoded(accepted) == root_raw == (temp / "independent-review.json").read_bytes(),
              "original_consumer_replay_bytes_differ")
    return {"schema": 1, "outcome": "accepted", "run_id": RUN, "qa_head": HEAD,
        "source_commit": SOURCE, "retained_files_checked": 20, "external_input_files_checked": 18,
        "original_consumer_byte_identical": True, "root_peer_acceptance_matched": True,
        "phases": 14, "artifact_members": 16, "guard_claim": "synthetic_opaque_byte_preservation_only",
        "activity_claim": "two_allowlisted_synthetic_marker_persistence_only",
        "transport_basis": "retained GitHub metadata and saved verified digest; no fresh network request",
        "new_native_execution": False, "network_requests": 0, "provider_imports": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qa-checkout", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(replay(args.qa_checkout, args.manifest_sha256), sort_keys=True))


if __name__ == "__main__":
    main()

