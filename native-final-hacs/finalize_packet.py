"""Finalize only a separately sealed preparation and an exact public RC anchor.

Pure files only: never publishes, uses Git/network, imports HA, or operates a VM.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys

HERE = Path(__file__).resolve().parent
PAYLOAD = ("controller.py", "donor_host.py", "protocol.py", "run_host.sh",
           "test_donor_contracts.py", "test_contracts.py", "verify_results.py",
           "finalize_packet.py", "workflow.template.yml")
PREFIX = "native-final-hacs"
WORKFLOW = ".github/workflows/native-final-hacs.yml"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def check(value, code):
    if not value:
        raise ValueError(code)


def file_at(root, name):
    relative = PurePosixPath(name)
    check(relative.parts and not relative.is_absolute() and ".." not in relative.parts
          and "\\" not in name, "preparation_relative_path")
    path = root
    for part in relative.parts:
        path /= part
        check(not path.is_symlink(), "preparation_symlink")
    check(stat.S_ISREG(path.stat().st_mode), "preparation_regular_file")
    return path


def document(path):
    check(path.is_file() and not path.is_symlink() and path.stat().st_size <= 1024**2, "bounded_manifest")
    return json.loads(path.read_bytes())


def finalize(manifest_sha, anchor, anchor_sha, output):
    raw = (HERE / "PREPARATION-MANIFEST.json").read_bytes()
    check(sha(raw) == manifest_sha, "externally_pinned_preparation_manifest")
    manifest = json.loads(raw)
    check(set(manifest) == {"schema", "source_commit", "contracts", "files", "donor_provenance", "scope"}
          and manifest["schema"] == 1 and manifest["contracts"] == {"donor": 45, "current": 16, "total": 61},
          "sealed_preparation_schema")
    actual = set()
    for path in HERE.rglob("*"):
        check(not path.is_symlink(), "preparation_tree_symlink")
        if path.is_dir():
            continue
        check(stat.S_ISREG(path.stat().st_mode), "preparation_tree_special_file")
        name = path.relative_to(HERE).as_posix()
        if "__pycache__" not in path.parts and name != "PREPARATION-MANIFEST.json":
            actual.add(name)
    check(actual == set(manifest["files"]), "sealed_preparation_exact_file_set")
    for name, expected in manifest["files"].items():
        data = file_at(HERE, name).read_bytes()
        check(expected == {"bytes": len(data), "sha256": sha(data)}, "sealed_preparation_file_changed")
    # All local imports occur only after the entire preparation map was checked.
    sys.path.insert(0, str(HERE))
    import protocol as p
    value = p.anchor_at(anchor, anchor_sha)
    check(manifest["source_commit"] == p.SOURCE == value["source_commit"], "one_final_source")
    check(not output.exists() and not output.is_symlink(), "fresh_final_packet")
    output.mkdir(mode=0o700, parents=True)
    packet = output / PREFIX
    packet.mkdir(mode=0o700)
    for name in PAYLOAD:
        shutil.copyfile(file_at(HERE, name), packet / name)
    shutil.copytree(HERE / "guest_helper", packet / "guest_helper",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (packet / "release-anchor.json").write_bytes(anchor.read_bytes())
    helpers = {}
    for name in manifest["files"]:
        if name.startswith("guest_helper/"):
            helpers[name[len("guest_helper/"):]] = manifest["files"][name]
    provenance = {"source_commit": p.SOURCE, "source_files": 402, "candidate_sha256": p.CANDIDATE,
        "inventory_sha256": p.INVENTORY, "baseline_sha256": p.BASELINE, "baseline_inventory_sha256": p.BASE_INVENTORY,
        "hacs_sha256": p.HACS_SHA, "haos_sha256": "fae6a728768cc10aff60d4820bfcd40d64cd77fab82c8bd92af13b3d9d414090",
        "helper_files": helpers, "controller_sha256": manifest["files"]["controller.py"]["sha256"],
        "donor_host_sha256": manifest["files"]["donor_host.py"]["sha256"], "anchor_sha256": anchor_sha}
    (packet / "expected-provenance.json").write_bytes(p.canonical(provenance) + b"\n")
    inputs = {"schema": 1, "source_commit": p.SOURCE, "files": {}}
    for path in sorted(packet.rglob("*")):
        if path.is_file():
            data = path.read_bytes()
            inputs["files"][path.relative_to(packet).as_posix()] = {"bytes": len(data), "sha256": sha(data)}
    inputs_raw = p.canonical(inputs) + b"\n"
    (packet / "INPUTS.json").write_bytes(inputs_raw)
    template = (HERE / "workflow.template.yml").read_text()
    check(template.count("__FROZEN_INPUTS_SHA256__") == 1 and template.count("__RELEASE_ANCHOR_SHA256__") == 2,
          "workflow_exact_placeholders")
    rendered = template.replace("__FROZEN_INPUTS_SHA256__", sha(inputs_raw)).replace("__RELEASE_ANCHOR_SHA256__", anchor_sha)
    check("__FROZEN_" not in rendered and "__RELEASE_" not in rendered, "no_pending_workflow_inputs")
    workflow = output / WORKFLOW
    workflow.parent.mkdir(mode=0o700, parents=True)
    workflow.write_text(rendered)
    receipt = {"schema": 1, "source_commit": p.SOURCE, "candidate_sha256": p.CANDIDATE,
        "preparation_manifest_sha256": manifest_sha, "release_anchor_sha256": anchor_sha,
        "input_map_sha256": sha(inputs_raw), "input_files": len(inputs["files"]),
        "workflow_path": WORKFLOW, "workflow_sha256": sha(workflow.read_bytes()),
        "contracts": manifest["contracts"], "native_execution": False, "publication": False}
    (output / "FINALIZATION.json").write_bytes(p.canonical(receipt) + b"\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preparation-manifest-sha256", required=True)
    parser.add_argument("--release-anchor", type=Path, required=True)
    parser.add_argument("--release-anchor-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(finalize(args.preparation_manifest_sha256, args.release_anchor,
        args.release_anchor_sha256, args.output), sort_keys=True))


if __name__ == "__main__":
    main()

