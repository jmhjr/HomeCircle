"""Owned consumer preparation and finite private phase control; no test execution."""

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import secrets
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent


def bootstrap(path, expected):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise RuntimeError("driver_pin_hash_refused")
    values = json.loads(raw)
    common = HERE / "common.py"
    if (
        hashlib.sha256(common.read_bytes()).hexdigest()
        != values["controls"]["common.py"]
    ):
        raise RuntimeError("driver_common_refused")
    spec = importlib.util.spec_from_file_location("consumer_common", common)
    c = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(c)
    values = c.pins(path, expected)
    c.controls(HERE, values)
    return c, values


def source(c, directory):
    support = c.load("consumer_package_support", HERE / "package_support.py", c.SUPPORT)
    support.configure(
        support.load_pins(directory / "source-config.json", c.SOURCE_CONFIG)
    )
    files = support.inputs(directory)
    c.read(directory / "homecircle.zip", c.ARCHIVE)
    c.read(directory / "inventory.json", c.INVENTORY)
    return support, files


def cache_command(wanted, executable, constraints):
    """Use both fixed official image sources without inheriting an index config."""
    return [
        "uv",
        "pip",
        "install",
        "--no-config",
        "--prefix",
        "/config/deps",
        "--python",
        executable,
        "--index-url",
        "https://pypi.org/simple",
        "--extra-index-url",
        "https://wheels.home-assistant.io/musllinux-index/",
        "--index-strategy",
        "unsafe-first-match",
        "--constraint",
        str(constraints),
        *[name + "==" + version for name, version in sorted(wanted.items())],
    ]


def seed_config_version(c, config, version):
    """Bind only a newly owned synthetic config to its exact prepared Core."""
    c.check(version in {"2026.9.4", "2026.10.2"}, "prepared_config_version_refused")
    marker = config / ".HA_VERSION"
    try:
        with marker.open("x", encoding="utf8") as stream:
            stream.write(version)
    except FileExistsError:
        c.check(False, "prepared_config_version_refused")
    c.check(
        c.read(marker, limit=64) == version.encode(),
        "prepared_config_version_refused",
    )


def setup(c, values, args):
    args.setup_stage = "preparer_boundary"
    status = dict(
        line.split(":", 1)
        for line in Path("/proc/self/status").read_text().splitlines()
        if ":" in line
    )
    c.check(
        status["CapBnd"].strip() == values["capability_mask"]
        and int(status["CapEff"].strip(), 16) & ~int(values["capability_mask"], 16)
        == 0,
        "preparer_finite_default_capabilities_refused",
    )
    c.check(
        sys.platform == "linux"
        and platform.machine() == values["machine"]
        and platform.python_version() == values["python"]
        and importlib.metadata.version("homeassistant") == values["core"],
        "preparer_runtime_refused",
    )
    args.setup_stage = "startup_identity"
    root = Path("/usr/src/homeassistant/homeassistant")
    c.read(root / "package_constraints.txt", values["constraints_sha256"])
    for name, expected in values["startup_scripts"].items():
        c.read(Path("/") / name, expected)
    for name, expected in values["startup_sources"].items():
        c.read(root / name, expected)
    args.setup_stage = "source_inputs"
    support, files = source(c, args.payload)
    args.setup_stage = "source_extract"
    support.extract(files, Path("/qa/source"))
    sys.path.insert(
        0, "/qa/source/scripts"
    )  # Preparation inspector only, never the acceptance service.
    args.setup_stage = "package_inspection"
    inspector = c.load(
        "consumer_release_inspector",
        Path("/qa/source/scripts/validate_release.py"),
        "20c0466b4fa70a83c5f282bfcd07b0d2e6f5a3a1a09bf90072649441b2ad7f37",
    )
    body = inspector.inspect_archive(
        args.payload / "homecircle.zip", args.payload / "inventory.json"
    )
    c.check(len(body) == 113, "preparer_package_count_refused")
    args.setup_stage = "fixture_staging"
    config = Path("/config")
    c.check(not any(config.iterdir()), "fresh_owned_volume_required")
    control = config / c.CONTROL
    control.mkdir(mode=0o700)
    for name in values["controls"]:
        shutil.copyfile(HERE / name, control / name)
    shutil.copyfile(args.pins, control / "pins.json")
    shutil.copyfile(args.payload / "inventory.json", control / "inventory.json")
    target = config / "custom_components/homecircle"
    for name, raw in body.items():
        path = target / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_bytes(raw)
    c.installed(
        target, json.loads(c.read(control / "inventory.json", c.INVENTORY))["files"]
    )
    qa = config / "custom_components" / c.DOMAIN
    qa.mkdir(mode=0o700)
    shutil.copyfile(HERE / "guest.py", qa / "__init__.py")
    (qa / "manifest.json").write_text(
        json.dumps(
            {
                "domain": c.DOMAIN,
                "name": "Disposable consumer entrypoint witness",
                "version": "0.0.0",
                "dependencies": [
                    "frontend",
                    "http",
                    "image_upload",
                    "lovelace",
                    "person",
                    "websocket_api",
                    "zone",
                ],
                "requirements": [],
                "codeowners": [],
            }
        )
    )
    (config / "configuration.yaml").write_text(
        "homeassistant:\n  name: Example consumer household\n  latitude: 0\n  longitude: 0\n  elevation: 0\n  unit_system: metric\n  time_zone: UTC\nhttp:\n  server_host: 127.0.0.1\n  server_port: 18123\nperson:\n  - id: consumer_example_a\n    name: Consumer Example A\n    device_trackers: [device_tracker.consumer_example_phone]\n  - id: consumer_example_b\n    name: Consumer Example B\n    device_trackers: [device_tracker.consumer_example_router]\nzone: []\nhomecircle_consumer_qa:\n  disposable: true\n"
    )
    seed_config_version(c, config, values["core"])
    args.setup_stage = "cache_layout"
    env = dict(os.environ, PYTHONUSERBASE="/config/deps")
    cache = (
        subprocess.check_output(
            [sys.executable, "-m", "site", "--user-site"], env=env, timeout=15
        )
        .decode()
        .strip()
    )
    c.check(
        cache == "/config/deps/lib/python3.14/site-packages",
        "normal_cache_layout_refused",
    )
    wanted = values["dependency_versions"] | values["startup_versions"]
    command = cache_command(wanted, sys.executable, root / "package_constraints.txt")
    args.setup_stage = "cache_install"
    c.check(
        support.run_owned(
            [
                sys.executable,
                "-I",
                "-B",
                str(HERE / "cache_child.py"),
                "--receipt",
                str(control / "cache-child-summary.json"),
                "--",
                *command,
            ],
            cwd=config,
            log=control / "cache-install-private.log",
            limit=660,
        )
        == 0,
        "cache_preparation_refused",
    )
    child = json.loads(c.read(control / "cache-child-summary.json", limit=4096))
    c.check(
        set(child)
        == {
            "schema",
            "stage",
            "outcome",
            "subreaper_verified",
            "primary_exit_code",
            "primary_timed_out",
            "adopted_children_reaped",
            "descendant_deadline_exceeded",
            "owned_descendants_drained",
        }
        and child["schema"] == 1
        and child["stage"] == "cache_install"
        and child["outcome"] == "passed"
        and type(child["primary_exit_code"]) is int
        and child["primary_exit_code"] == 0
        and child["subreaper_verified"] is True
        and child["primary_timed_out"] is False
        and type(child["adopted_children_reaped"]) is int
        and 0 <= child["adopted_children_reaped"] <= 100000
        and child["descendant_deadline_exceeded"] is False
        and child["owned_descendants_drained"] is True,
        "cache_child_reaping_refused",
    )
    args.setup_stage = "cache_versions"
    actual = {
        item.metadata["Name"].lower().replace("_", "-"): item.version
        for item in importlib.metadata.distributions(path=[cache])
    }
    c.check(
        all(actual.get(name) == version for name, version in wanted.items()),
        "prepared_cache_versions_refused",
    )
    args.setup_stage = "source_recheck"
    support.source_unchanged(files, Path("/qa/source"))
    args.setup_stage = "setup_receipt"
    runtime = {
        "schema": 1,
        "token": secrets.token_hex(32),
        "pins_sha256": args.pins_sha,
        "cache_site": cache,
    }
    c.atomic(control / "runtime-inputs.json", runtime)
    c.atomic(control / "phase.json", {"phase": "first", "token": runtime["token"]})
    c.atomic(
        control / "setup-summary.json",
        {
            **c.base_receipt(values),
            "outcome": "passed",
            "dependency_packages_pinned": 24,
            "startup_requirements_pinned": 21,
            "prepared_distributions": len(wanted),
            "canonical_public_source_files": len(files),
            "package_files_verified": 113,
            "config_cache_path_verified": True,
            "prepared_config_version_verified": True,
            "startup_sources_and_scripts_verified": True,
            "preparer_finite_default_capabilities_verified": True,
            "cache_child_reaping_verified": True,
        },
    )


def control(c, values, args):
    folder = Path("/config") / c.CONTROL
    runtime = json.loads(c.read(folder / "runtime-inputs.json"))
    if args.mode == "restart":
        c.check((folder / "first-receipt.json").is_file(), "first_phase_required")
        c.atomic(folder / "phase.json", {"phase": "restart", "token": runtime["token"]})
        return
    deadline = time.monotonic() + 180
    while not (folder / (args.action + "-receipt.json")).is_file():
        c.check(not (folder / "guest-failure.json").exists(), "consumer_guest_failed")
        c.check(time.monotonic() < deadline, "consumer_phase_deadline")
        time.sleep(0.5)
    result = json.loads(c.read(folder / (args.action + "-receipt.json")))
    c.check(
        result.get("outcome") == "passed"
        and result.get("phase") == args.action
        and result.get("package_sha256") == c.ARCHIVE
        and result.get("token_sha256") == c.sha(runtime["token"].encode())
        and result.get("target") == values["target"],
        "consumer_phase_receipt_refused",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "setup", "wait", "restart"))
    parser.add_argument("--pins", type=Path, required=True)
    parser.add_argument("--pins-sha", required=True)
    parser.add_argument("--payload", type=Path)
    parser.add_argument("--repository", type=Path)
    parser.add_argument("--action", choices=("first", "restart"))
    args = parser.parse_args()
    c, values = bootstrap(args.pins, args.pins_sha)
    c.check(
        sys.platform == "linux" and platform.machine() == values["machine"],
        "native_host_required",
    )
    try:
        if args.mode == "prepare":
            support, files = source(c, args.payload)
            print(json.dumps(support.verify_git_source(files, args.repository)))
        elif args.mode == "setup":
            setup(c, values, args)
        else:
            c.check(args.action in {"first", "restart"}, "phase_action_required")
            if args.mode == "restart":
                args.action = "restart"
            control(c, values, args)
    except Exception as error:
        if args.mode != "prepare":
            c.atomic(
                Path("/qa/failure-summary.json"),
                c.safe_failure(
                    error, HERE, setup_stage=getattr(args, "setup_stage", None)
                ),
            )
        raise


if __name__ == "__main__":
    main()
