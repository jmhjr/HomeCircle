"""Linux-only, offline exact-candidate provider.Worker lifecycle acceptance.

This deliberately refuses macOS before inspecting a package or launching Python
children. Run it in the disposable target Core environment. It uses a generated
Mach-O dispatcher, never an Apple binary, account, existing config or network.
The candidate files remain byte-for-byte unchanged; the child launcher replaces
only the expected synthetic-library digest/length and observes the real loader.
"""

from __future__ import annotations

import argparse
import asyncio
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import types

CANDIDATE_SHA256 = "f0477a91e78181fe1f8d80ada176a1739e10a7502abe7ee6ee2240571280d1f5"
CANDIDATE_MEMBERS = 112
PHASE = "startup"
PHASES = frozenset({
    "startup", "import", "dependency_copy", "dependency_resolution", "fixture",
    "normal_open", "limits", "normal_check", "normal_close", "cancel_open",
    "native_loop", "cancel_close", "cleanup", "complete",
})
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def linux_limits(raw):
    """Read the three limits the real child installs, in Linux /proc format."""
    labels = {
        "Max cpu time": ("cpu_seconds", "90", "90", "seconds"),
        "Max core file size": ("core_bytes", "0", "0", "bytes"),
        "Max address space": (
            "address_space_bytes", str(3072 * 1024**2), str(3072 * 1024**2), "bytes"
        ),
    }
    found = {}
    for line in raw.splitlines():
        for label, (name, soft, hard, units) in labels.items():
            if line.startswith(label + " "):
                values = line[len(label):].split()
                if values != [soft, hard, units]:
                    raise ValueError("linux_lifecycle_limits_refused")
                found[name] = {"soft": int(soft), "hard": int(hard), "units": units}
    if len(found) != len(labels):
        raise ValueError("linux_lifecycle_limits_refused")
    return found


def synthetic_cancel_image():
    """Complete open/check; loop only for the later ProvisioningStart call."""
    from platform_validate_candidate import synthetic_image

    image = bytearray(synthetic_image())
    # cmp edi, ProvisioningStart; je $; otherwise write success and return.
    # The taken branch loops on itself and consumes CPU until the parent cancels.
    image[0x979A0:] = bytes.fromhex(
        "81 ff 6c d8 6b 71 74 fe 48 8b 06 c7 00 00 00 00 00 31 c0 c3"
    )
    struct.pack_into("<Q", image, 80, len(image))  # __TEXT.filesize
    return bytes(image)


async def child_validation(package, work):
    """Exercise the extracted provider with real Linux pipes and owned children."""
    global PHASE
    if sys.platform != "linux":
        raise ValueError("linux_lifecycle_linux_required")
    package, work = Path(package).resolve(), Path(work).resolve()
    sys.dont_write_bytecode = True
    workers, children = [], []
    counters = {"network_operations_blocked": 0}
    allowed = (
        package, work, SCRIPTS, Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve(),
        *(Path(p).resolve() for p in sys.path
          if Path(p).name in {"site-packages", "dist-packages"}),
    )
    expected_worker = str(package / "_findmy_runtime/worker.py")
    launches = set()

    def guard(event, args):
        if event.startswith("socket.") and event != "socket.__new__":
            counters["network_operations_blocked"] += 1
            raise PermissionError("linux_lifecycle_network_refused")
        if event == "subprocess.Popen" and tuple(args[1]) not in launches:
            raise PermissionError("linux_lifecycle_process_refused")
        if event in {"os.system", "os.posix_spawn"} or event.startswith("os.exec"):
            raise PermissionError("linux_lifecycle_process_refused")
        if event != "open" or isinstance(args[0], int):
            return
        path, mode, flags = args
        location = Path(os.fsdecode(path)).resolve()
        writing = (
            isinstance(mode, str) and any(c in mode for c in "wax+")
            or isinstance(flags, int)
            and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
        )
        if location == Path(os.devnull):
            return
        roots = (work,) if writing else allowed
        if any(location == root or location.is_relative_to(root) for root in roots):
            return
        if not writing and any(
            location == Path(f"/proc/{child.pid}/{name}")
            for child in children for name in ("limits", "stat")
        ):
            return
        raise PermissionError("linux_lifecycle_file_refused")

    # asyncio's local wakeup socket already exists when this coroutine starts.
    sys.addaudithook(guard)
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        PHASE = "import"
        components = types.ModuleType("custom_components")
        components.__path__ = [str(package.parent)]
        namespace = types.ModuleType("custom_components.homecircle")
        namespace.__path__ = [str(package)]
        components.homecircle = namespace
        sys.modules["custom_components"] = components
        sys.modules["custom_components.homecircle"] = namespace
        provider = importlib.import_module(
            "custom_components.homecircle._findmy_runtime.provider"
        )
        if not Path(provider.__file__).resolve().is_relative_to(package):
            raise ValueError("linux_lifecycle_provider_import_refused")
        import unicorn

        unicorn_version = unicorn.__version__
        if unicorn_version != "2.1.4":
            raise ValueError("linux_lifecycle_dependency_version_refused")

        # Model Core's parent-only dependency path with the actual native wheel,
        # not a mock Unicorn package. The real provider resolver sees this path;
        # the -I child cannot discover it without the worker's explicit loader.
        PHASE = "dependency_copy"
        original_unicorn = Path(unicorn.__file__).resolve().parent
        dependency_root = work / "parent-only-deps/site-packages"
        dependency_root.mkdir(parents=True)
        copied_unicorn = dependency_root / "unicorn"
        shutil.copytree(original_unicorn, copied_unicorn,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for name in list(sys.modules):
            if name == "unicorn" or name.startswith("unicorn."):
                del sys.modules[name]
        sys.path.insert(0, str(dependency_root))
        PHASE = "dependency_resolution"
        resolved_unicorn = await asyncio.to_thread(provider._unicorn_package_directory)
        if resolved_unicorn != str(copied_unicorn):
            raise ValueError("linux_lifecycle_dependency_resolution_refused")

        PHASE = "fixture"
        image = synthetic_cancel_image()
        library = work / "synthetic-lifecycle.macho"
        library.write_bytes(image)
        fixture_digest = hashlib.sha256(image).hexdigest()
        launch = (
            "import importlib.util, pathlib, sys\n"
            f"spec=importlib.util.spec_from_file_location('lifecycle_worker',{expected_worker!r})\n"
            "worker=importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(worker)\n"
            f"worker.LIBRARY_BYTES={len(image)}\n"
            f"worker.LIBRARY_SHA256={fixture_digest!r}\n"
            "original_load=worker.load_unicorn\n"
            "def observed_load(package):\n"
            "    original_load(package)\n"
            f"    assert pathlib.Path(sys.modules['unicorn'].__file__).resolve().parent == pathlib.Path({str(copied_unicorn)!r})\n"
            f"    assert {str(dependency_root)!r} not in sys.path\n"
            "worker.load_unicorn=observed_load\n"
            "worker.main()\n"
        )
        command = (sys.executable, "-I", "-B", "-c", launch)
        launches.add(command)
        original_spawn = asyncio.create_subprocess_exec

        async def spawn(*args, **kwargs):
            if args != (sys.executable, "-B", expected_worker):
                raise ValueError("linux_lifecycle_spawn_contract_refused")
            if (
                kwargs.get("stdin") != asyncio.subprocess.PIPE
                or kwargs.get("stdout") != asyncio.subprocess.PIPE
                or kwargs.get("stderr") != asyncio.subprocess.DEVNULL
                or kwargs.get("limit") != provider.MAX_IPC + 1
            ):
                raise ValueError("linux_lifecycle_pipe_contract_refused")
            child = await original_spawn(*command, **kwargs)
            children.append(child)
            return child

        asyncio.create_subprocess_exec = spawn

        def reaped(child):
            return child.returncode is not None and not Path(f"/proc/{child.pid}").exists()

        def ticks(child):
            fields = Path(f"/proc/{child.pid}/stat").read_text().rsplit(")", 1)[1].split()
            return int(fields[11]) + int(fields[12])

        def worker():
            result = provider.Worker()
            workers.append(result)
            return result

        try:
            PHASE = "normal_open"
            normal = worker()
            if await normal.open(library, {"host_uuid": "a" * 32}, {}) != {"provisioned": True}:
                raise ValueError("linux_lifecycle_open_refused")
            first = normal.process
            PHASE = "limits"
            limits = linux_limits(Path(f"/proc/{first.pid}/limits").read_text())
            PHASE = "normal_check"
            if await normal.call({"op": "check"}) != {"provisioned": True}:
                raise ValueError("linux_lifecycle_check_refused")
            PHASE = "normal_close"
            await normal.close()
            await normal.close()
            normal_ok = normal.process is None and normal._spawn is None and reaped(first)

            PHASE = "cancel_open"
            cancelled = worker()
            if await cancelled.open(library, {"host_uuid": "b" * 32}, {}) != {"provisioned": True}:
                raise ValueError("linux_lifecycle_open_refused")
            second = cancelled.process
            baseline = ticks(second)
            calling = asyncio.create_task(cancelled.call({"op": "start", "spim": "YQ=="}))
            try:
                PHASE = "native_loop"
                # CPU progress proves this is cancellation of an active native
                # guest call, rather than cancellation before a child starts.
                async with asyncio.timeout(5):
                    while ticks(second) < baseline + 2:
                        if calling.done():
                            raise ValueError("linux_lifecycle_native_loop_refused")
                        await asyncio.sleep(0.02)
                PHASE = "cancel_close"
                calling.cancel()
                try:
                    await calling
                except asyncio.CancelledError:
                    pass
                else:
                    raise ValueError("linux_lifecycle_cancellation_refused")
            finally:
                if not calling.done():
                    calling.cancel()
                    await asyncio.gather(calling, return_exceptions=True)
            cancelled_ok = (
                cancelled.process is None and cancelled._spawn is None
                and cancelled._closed and reaped(second)
            )
        finally:
            try:
                cleanup = await asyncio.gather(
                    *(item.close() for item in workers), return_exceptions=True
                )
            finally:
                asyncio.create_subprocess_exec = original_spawn
            if any(isinstance(item, BaseException) for item in cleanup):
                PHASE = "cleanup"
                raise ValueError("linux_lifecycle_worker_cleanup_refused")
        if not normal_ok or not cancelled_ok or not all(reaped(item) for item in children):
            raise ValueError("linux_lifecycle_cleanup_refused")
    PHASE = "complete"
    return {
        "normal_open_check_close": normal_ok,
        "active_native_cancellation": cancelled_ok,
        "parent_only_dependency_used": True,
        "unicorn_version": unicorn_version,
        "production_spawn_contract": True,
        "production_pipe_contract": True,
        "child_limits": limits,
        "worker_children": [
            {"pid": item.pid, "exit_code": item.returncode, "proc_absent": reaped(item)}
            for item in children
        ],
        "worker_processes_reaped": all(reaped(item) for item in children),
        "fixture_sha256": fixture_digest,
        "candidate_files_modified": False,
        "network_allowed": False,
        "apple_binary_executed": False,
        "account_requests": 0,
        "owner_data_read": False,
        **counters,
    }


def run_validation(archive, *, inventory=None):
    """Fail closed before any process when the host or exact artifact differs."""
    if sys.platform != "linux":
        raise ValueError("linux_lifecycle_linux_required")
    archive = Path(archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != CANDIDATE_SHA256:
        raise ValueError("linux_lifecycle_candidate_hash_refused")
    from validate_release import inspect_archive

    payload = inspect_archive(archive, inventory)
    if len(payload) != CANDIDATE_MEMBERS:
        raise ValueError("linux_lifecycle_candidate_inventory_refused")
    with tempfile.TemporaryDirectory(prefix="homecircle-linux-lifecycle-") as directory:
        temporary = Path(directory)
        temporary.chmod(0o700)
        package, work = temporary / "package/homecircle", temporary / "work"
        work.mkdir(mode=0o700)
        for name, raw in payload.items():
            target = package / name
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            target.write_bytes(raw)
        child = subprocess.Popen(
            [sys.executable, "-I", "-B", str(Path(__file__).resolve()),
             "--_child", str(package), str(work)],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=work,
            start_new_session=True,
        )
        try:
            try:
                stdout, stderr = child.communicate(timeout=60)
            except subprocess.TimeoutExpired:
                raise ValueError("linux_lifecycle_probe_timeout") from None
            if child.returncode != 0 or stderr or len(stdout.splitlines()) != 1:
                try:
                    failure = json.loads(stderr)
                    phase, kind = failure["failure_stage"], failure["failure_type"]
                    if phase in PHASES and isinstance(kind, str) and kind.isidentifier() and len(kind) < 81:
                        raise ValueError(f"linux_lifecycle_probe_refused:{phase}:{kind}")
                except (KeyError, TypeError, json.JSONDecodeError):
                    pass
                raise ValueError("linux_lifecycle_probe_refused")
            result = json.loads(stdout)
            if any((package / name).read_bytes() != raw for name, raw in payload.items()):
                raise ValueError("linux_lifecycle_candidate_changed")
        except BaseException:
            # The new session contains only this probe and its two workers.
            # Cover interruption, probe failure and parsing errors as well as
            # timeout, including workers whose direct parent already exited.
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.communicate()
            raise
    return {
        "schema": 1, "outcome": "passed", "evidence_kind": "linux_actual_zip_provider_lifecycle",
        "package_sha256": CANDIDATE_SHA256, "package_members": len(payload),
        "python_version": sys.version.split()[0], "system": os.uname().sysname,
        "machine": os.uname().machine, "cleanup_ok": not temporary.exists(), **result,
    }


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--_child":
        try:
            result = asyncio.run(child_validation(sys.argv[2], sys.argv[3]))
        except Exception as error:
            # Fixed stage and exception class only; no input, path or state text.
            print(json.dumps({"failure_stage": PHASE, "failure_type": type(error).__name__}), file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_validation(args.archive, inventory=args.inventory)
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded)
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
