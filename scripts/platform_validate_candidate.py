"""Offline, actual-ZIP native smoke check for each candidate platform.

Run this inside the target Core Python environment. No Apple binary, account,
existing HA configuration or network is used. A tiny synthetic x86_64 Mach-O
exercises the packaged worker's file verifier, resource limits, Unicorn loader,
guest dispatcher and bounded IPC. Only the expected fixture digest and length
are substituted in memory; genuine Apple execution is a separate acceptance gate.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys
import tempfile

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet


def synthetic_image():
    """Set the dispatcher's payload status to zero and return successfully."""
    dispatch = 0x979A0
    code = bytes.fromhex("48 8b 06 c7 00 00 00 00 00 31 c0 c3")
    size = dispatch + len(code)
    header = struct.pack("<8I", 0xFEEDFACF, 0x1000007, 3, 6, 1, 72, 0, 0)
    segment = struct.pack(
        "<II16sQQQQIIII", 0x19, 72, b"__TEXT", 0, 0x100000, 0, size, 7, 7, 0, 0
    )
    image = bytearray(size)
    image[: len(header)] = header
    image[len(header) : len(header) + len(segment)] = segment
    image[dispatch:] = code
    return bytes(image)


def active_core_constraints():
    """Read constraints beside the imported Core, including editable installs."""
    core = importlib.import_module("homeassistant")
    origin = getattr(core, "__file__", None)
    if not isinstance(origin, str) or not origin:
        raise ValueError("platform_core_constraints_refused")
    constraints = Path(origin).resolve().with_name("package_constraints.txt")
    try:
        return constraints.read_bytes()
    except OSError:
        raise ValueError("platform_core_constraints_refused") from None


def installed_requirements(requirements):
    """Check the installed active dependency closure and its Core constraints."""
    queue = list(requirements)
    seen, installed = set(), {}
    python_version = platform.python_version()
    while queue:
        raw = queue.pop()
        requirement = Requirement(raw)
        if requirement.marker and not requirement.marker.evaluate({"extra": ""}):
            continue
        distribution = importlib.metadata.distribution(requirement.name)
        version = distribution.version
        if not requirement.specifier.contains(version, prereleases=True):
            raise ValueError("platform_dependency_version_refused")
        python_specifier = distribution.metadata.get("Requires-Python")
        if python_specifier and not SpecifierSet(python_specifier).contains(
            python_version, prereleases=True
        ):
            raise ValueError("platform_python_version_refused")
        normalized = distribution.metadata["Name"].lower().replace("_", "-")
        installed[normalized] = version
        if normalized not in seen:
            seen.add(normalized)
            queue.extend(distribution.requires or ())

    core = importlib.metadata.distribution("homeassistant")
    core_python = core.metadata.get("Requires-Python")
    if core_python and not SpecifierSet(core_python).contains(python_version):
        raise ValueError("platform_core_python_refused")
    # Official Core images can expose distribution metadata under site-packages
    # while importing an editable source tree under /usr/src/homeassistant.
    constraints = active_core_constraints()
    mismatches = []
    for raw in constraints.decode().splitlines():
        raw = raw.split("#", 1)[0].strip()
        if not raw:
            continue
        requirement = Requirement(raw)
        name = requirement.name.lower().replace("_", "-")
        if name in installed and not requirement.specifier.contains(
            installed[name], prereleases=True
        ):
            mismatches.append(
                {
                    "package": name,
                    "installed": installed[name],
                    "constraint": str(requirement),
                }
            )
    return {
        "core_version": core.version,
        "core_requires_python": core_python,
        "core_constraints_sha256": hashlib.sha256(constraints).hexdigest(),
        "installed_dependency_closure": dict(sorted(installed.items())),
        "core_constraint_mismatches": mismatches,
    }


def native_child(package, work):
    """Import and exercise only public packaged code in disposable storage."""
    package, work = Path(package).resolve(), Path(work).resolve()
    dependency_roots = tuple(
        Path(entry).resolve()
        for entry in sys.path
        if Path(entry).name in {"site-packages", "dist-packages"}
    )
    allowed = (
        package,
        work,
        Path(sys.prefix).resolve(),
        Path(sys.base_prefix).resolve(),
        *dependency_roots,
    )
    counters = {"network_operations_blocked": 0}

    def guard(event, args):
        if event.startswith("socket.") and event != "socket.__new__":
            counters["network_operations_blocked"] += 1
            raise PermissionError("platform_network_refused")
        if event in {"os.system", "os.posix_spawn"} or event.startswith("os.exec"):
            raise PermissionError("platform_process_refused")
        if event == "open" and not isinstance(args[0], int):
            location = Path(os.fsdecode(args[0])).resolve()
            mode, flags = args[1:3]
            writing = (
                isinstance(mode, str)
                and any(c in mode for c in "wax+")
                or (
                    isinstance(flags, int)
                    and flags
                    & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
                )
            )
            if location == Path(os.devnull):
                return
            roots = (work,) if writing else allowed
            if not any(
                location == root or location.is_relative_to(root) for root in roots
            ):
                raise PermissionError("platform_file_refused")

    sys.dont_write_bytecode = True
    sys.addaudithook(guard)
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        for name in ("life360", "google.protobuf", "anisette", "unicorn", "srp", "bs4"):
            importlib.import_module(name)
        import unicorn

        worker = package / "_findmy_runtime/worker.py"
        image = synthetic_image()
        library = work / "synthetic-dispatcher.macho"
        library.write_bytes(image)
        fixture_sha256 = hashlib.sha256(image).hexdigest()
        launch = (
            "import importlib.util\n"
            f"spec=importlib.util.spec_from_file_location('platform_worker',{str(worker)!r})\n"
            "worker=importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(worker)\n"
            f"worker.LIBRARY_BYTES={len(image)}\n"
            f"worker.LIBRARY_SHA256={fixture_sha256!r}\n"
            "worker.main()\n"
        )
        message = {
            "op": "open",
            "library": str(library),
            "unicorn_package": str(Path(unicorn.__file__).resolve().parent),
            "host_uuid": "a" * 32,
            "store": {},
        }
        positive = subprocess.run(
            [sys.executable, "-I", "-B", "-c", launch],
            input=json.dumps(message) + "\n" + json.dumps({"op": "check"}) + "\n",
            text=True,
            capture_output=True,
            timeout=30,
            cwd=work,
            check=False,
        )
        native_ok = (
            positive.returncode == 0
            and not positive.stderr
            and positive.stdout.splitlines()
            == ['{"provisioned":true}', '{"provisioned":true}']
        )
        # The production verifier must refuse these non-Apple bytes unchanged.
        negative = subprocess.run(
            [sys.executable, "-I", "-B", str(worker)],
            input=json.dumps(message) + "\n",
            text=True,
            capture_output=True,
            timeout=30,
            cwd=work,
            check=False,
        )
        refused = (
            negative.returncode == 1 and not negative.stdout and not negative.stderr
        )
    return {
        "mandatory_imports": True,
        "unicorn_version": unicorn.__version__,
        "synthetic_native_worker": native_ok,
        "production_hash_refusal": refused,
        "worker_processes_reaped": positive.returncode is not None
        and negative.returncode is not None,
        "fixture_sha256": fixture_sha256,
        "network_operations_blocked": counters["network_operations_blocked"],
        "network_allowed": False,
        "apple_binary_executed": False,
        "account_requests": 0,
        "owner_data_read": False,
    }


def run_validation(archive, *, expected_sha256=None, inventory=None):
    """Bind offline native evidence to the validated candidate archive."""
    from validate_release import inspect_archive

    digest = hashlib.sha256(Path(archive).read_bytes()).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError("platform_candidate_hash_refused")
    payload = inspect_archive(archive, inventory)
    manifest = json.loads(payload["manifest.json"])
    dependencies = installed_requirements(manifest["requirements"])
    with tempfile.TemporaryDirectory(prefix="homecircle-platform-") as directory:
        temporary = Path(directory)
        temporary.chmod(0o700)
        package, work = temporary / "package/homecircle", temporary / "work"
        work.mkdir(mode=0o700)
        for name, raw in payload.items():
            target = package / name
            target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
            target.write_bytes(raw)
        child = subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                str(Path(__file__).resolve()),
                "--_child",
                str(package),
                str(work),
            ],
            capture_output=True,
            text=True,
            timeout=90,
            cwd=work,
            check=False,
        )
        if child.returncode != 0 or child.stderr or len(child.stdout.splitlines()) != 1:
            raise ValueError("platform_native_probe_refused")
        native = json.loads(child.stdout)
    passed = (
        all(
            native.get(name) is True
            for name in (
                "mandatory_imports",
                "synthetic_native_worker",
                "production_hash_refusal",
                "worker_processes_reaped",
            )
        )
        and native.get("network_allowed") is False
        and not dependencies["core_constraint_mismatches"]
    )
    return {
        "schema": 1,
        "outcome": "passed" if passed else "failed",
        "evidence_kind": "synthetic_native_actual_zip",
        "package_sha256": digest,
        "package_members": len(payload),
        "python_version": platform.python_version(),
        "system": platform.system(),
        "machine": platform.machine(),
        "libc": list(platform.libc_ver()),
        "cleanup_ok": not temporary.exists(),
        **dependencies,
        **native,
    }


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--_child":
        print(json.dumps(native_child(sys.argv[2], sys.argv[3]), sort_keys=True))
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_validation(
        args.archive, expected_sha256=args.expected_sha256, inventory=args.inventory
    )
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded)
    print(encoded, end="")
    return result["outcome"] != "passed"


if __name__ == "__main__":
    raise SystemExit(main())
