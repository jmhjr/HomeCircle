"""Freeze public source/package inputs into a new directory; never launch them."""

import argparse
import gzip
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tarfile

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("affected_input_driver", HERE / "driver.py")
D = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D)
TOOLS = ("driver.py", "run_native.sh", "requirements_support.py", "verify_results.py", "CORE-GRAPH.json")


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def public_files(source, export_raw):
    export = json.loads(export_raw, object_pairs_hook=D.unique)
    D.check(type(export) is dict and set(export) == {"schema", "source", "count", "files"}
            and type(export["schema"]) is int and export["schema"] == 1
            and type(export["count"]) is int and 300 <= export["count"] <= 1024
            and type(export["files"]) is dict and len(export["files"]) == export["count"],
            "complete_public_export_required")
    D.check(source.is_dir() and not source.is_symlink(), "public_source_directory_required")
    found = {}
    for path in source.rglob("*"):
        D.check(not path.is_symlink(), "source_symlink_refused")
        if path.is_file():
            name = path.relative_to(source).as_posix()
            D.check(D.safe_name(name) and name not in found, "source_name_refused")
            found[name] = D.read(path)
    D.check(set(found) == set(export["files"]), "complete_public_export_file_set_required")
    for name, raw in found.items():
        D.check(export["files"][name] == {**D.fingerprint(raw), "git_blob": D.git_blob(raw)},
                "public_export_bytes_refused")
    D.check(sum(map(len, found.values())) <= D.LIMIT, "source_total_refused")
    return export, found


def prepare(source, export_raw, package_raw, inventory_raw, selectors_raw, output):
    export, files = public_files(source, export_raw)
    selectors = json.loads(selectors_raw, object_pairs_hook=D.unique)
    D.check(type(selectors) is list and selectors and all(type(name) is str for name in selectors),
            "selected_modules_required")
    D.check(all(name in files for name in selectors), "selected_modules_missing")
    functions = D.expected_functions(files, selectors)
    inventory = json.loads(inventory_raw, object_pairs_hook=D.unique)
    D.check(type(inventory) is dict and set(inventory) == {"archive_sha256", "files", "version"}
            and inventory["archive_sha256"] == D.sha(package_raw), "final_package_inventory_required")
    packed = io.BytesIO()
    with gzip.GzipFile(fileobj=packed, mode="wb", filename="", mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            for name, raw in sorted(files.items()):
                item = tarfile.TarInfo(name)
                item.mode, item.mtime, item.size = 0o644, 0, len(raw)
                archive.addfile(item, io.BytesIO(raw))
    source_inventory = encoded({name: D.fingerprint(raw) for name, raw in sorted(files.items())})
    controls = {"schema": 1, "frozen": True, "source_commit": export["source"], "source_files": len(files),
        "source_sha256": D.sha(packed.getvalue()), "source_inventory_sha256": D.sha(source_inventory),
        "source_export_sha256": D.sha(export_raw), "driver_sha256": D.sha(D.read(HERE / "driver.py")),
        "package_sha256": D.sha(package_raw), "package_inventory_sha256": D.sha(inventory_raw),
        "version": inventory["version"], "release_files": len(inventory["files"]),
        "selected_modules": selectors, "expected_functions": functions}
    control_raw = encoded(controls)
    payload = {"config.json": control_raw, "source.tgz": packed.getvalue(),
               "source-inventory.json": source_inventory, "source-export.json": export_raw,
               "homecircle.zip": package_raw, "inventory.json": inventory_raw}
    D.check(not output.exists() and not output.is_symlink(), "fresh_owned_preparation_required")
    temporary = output.with_name(output.name + ".preparing")
    D.check(not temporary.exists() and not temporary.is_symlink(), "fresh_owned_temporary_required")
    temporary.mkdir(mode=0o700, parents=False)
    try:
        (temporary / "payload").mkdir(mode=0o700)
        for name in TOOLS:
            (temporary / name).write_bytes(D.read(HERE / name))
        for name, raw in payload.items():
            (temporary / "payload" / name).write_bytes(raw)
        (temporary / "CONFIG.sha256").write_text(D.sha(control_raw) + "\n")
        # Run only standard-library structural/hash functions, never runtime modes.
        checked = D.configuration(temporary / "payload", D.sha(control_raw))
        checked_files, _ = D.inputs(temporary / "payload", checked)
        D.check(set(checked_files) == set(files), "prepared_source_binding_refused")
        frozen = {name: D.fingerprint(raw) for name, raw in payload.items()}
        receipt = {"schema": 1, "scope": D.SCOPE, "source_commit": controls["source_commit"],
                   "source_files": len(files), "selected_modules": selectors,
                   "selected_base_functions": len(functions), "config_sha256": D.sha(control_raw),
                   "payload": frozen, "tools": {name: D.fingerprint(D.read(HERE / name)) for name in TOOLS},
                   "native_execution_performed": False, "workflow_dispatch": False,
                   "publication_performed": False, "legal_clearance_claimed": False}
        # Completion receipt is written last and publication happens after validation.
        (temporary / "PREPARED.json").write_bytes(encoded(receipt))
        temporary.rename(output)
    except BaseException:
        shutil.rmtree(temporary)
        raise
    return receipt


def main():
    parser = argparse.ArgumentParser()
    for name in ("source", "source-export", "archive", "inventory", "tests", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    receipt = prepare(args.source, D.read(args.source_export), D.read(args.archive),
                      D.read(args.inventory), D.read(args.tests), args.output)
    print(json.dumps({"source_files": receipt["source_files"],
                      "selected_base_functions": receipt["selected_base_functions"],
                      "config_sha256": receipt["config_sha256"], "native_execution_performed": False}))


if __name__ == "__main__":
    main()
