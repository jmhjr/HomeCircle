"""Cache installer only: reap owned Linux descendants before the outer guard."""

import argparse
import ctypes
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

COMMAND_SECONDS = 630
DRAIN_SECONDS = 10
CLEANUP_SECONDS = 5


def require(condition):
    if not condition:
        raise RuntimeError("cache_child_boundary_refused")


def enable_subreaper():
    require(sys.platform == "linux" and os.getpgrp() == os.getpid())
    require(hasattr(os, "pidfd_open") and hasattr(signal, "pidfd_send_signal"))
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.restype = ctypes.c_int
    require(
        libc.prctl(
            36,
            ctypes.c_ulong(1),
            ctypes.c_ulong(0),
            ctypes.c_ulong(0),
            ctypes.c_ulong(0),
        )
        == 0
    )
    enabled = ctypes.c_int()
    require(
        libc.prctl(
            37,
            ctypes.byref(enabled),
            ctypes.c_ulong(0),
            ctypes.c_ulong(0),
            ctypes.c_ulong(0),
        )
        == 0
    )
    require(enabled.value == 1)


def direct_children():
    raw = Path(f"/proc/self/task/{os.getpid()}/children").read_text()
    values = raw.split()
    require(len(values) <= 512 and all(value.isdecimal() for value in values))
    return [int(value) for value in values]


def signal_owned(signum, sent):
    """pidfds prevent PID reuse; only this wrapper's direct children are signaled."""
    for pid in direct_children():
        descriptor = None
        try:
            descriptor = os.pidfd_open(pid)
            fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
            require(int(fields[1]) == os.getpid())
            identity = (pid, int(fields[19]))
            if identity not in sent:
                signal.pidfd_send_signal(descriptor, signum)
                sent.add(identity)
        except (ProcessLookupError, FileNotFoundError):
            pass
        finally:
            if descriptor is not None:
                os.close(descriptor)


def run(
    command,
    *,
    command_seconds=COMMAND_SECONDS,
    drain_seconds=DRAIN_SECONDS,
    cleanup_seconds=CLEANUP_SECONDS,
):
    require(
        0 < command_seconds <= COMMAND_SECONDS
        and 0 < drain_seconds <= DRAIN_SECONDS
        and 0 < cleanup_seconds <= CLEANUP_SECONDS
    )
    enable_subreaper()
    primary = subprocess.Popen(command, stdin=subprocess.DEVNULL)
    adopted = 0

    def observe():
        nonlocal adopted
        primary.poll()  # Popen alone owns the primary command's wait status.
        if primary.returncode is None:
            for pid in direct_children():
                if pid == primary.pid:
                    continue
                try:
                    found, _ = os.waitpid(pid, os.WNOHANG)
                    adopted += bool(found)
                except ChildProcessError:
                    pass
            return False
        while True:
            try:
                found, _ = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                return True  # ECHILD, not a process-list inference.
            if not found:
                return False
            adopted += 1

    command_limit = time.monotonic() + command_seconds
    while primary.poll() is None and time.monotonic() < command_limit:
        observe()
        time.sleep(0.01)
    timed_out = primary.poll() is None
    drained = observe()
    drain_limit = time.monotonic() + drain_seconds
    while not timed_out and not drained and time.monotonic() < drain_limit:
        time.sleep(0.01)
        drained = observe()
    descendant_deadline = not timed_out and not drained
    if not drained:
        # Reaching either deadline always fails, even if owned cleanup succeeds.
        for signum, portion in ((signal.SIGTERM, 0.4), (signal.SIGKILL, 0.6)):
            limit = time.monotonic() + cleanup_seconds * portion
            sent = set()
            while not drained and time.monotonic() < limit:
                signal_owned(signum, sent)
                time.sleep(0.01)
                drained = observe()
    successful = (
        primary.returncode == 0
        and not timed_out
        and not descendant_deadline
        and drained
    )
    return {
        "schema": 1,
        "stage": "cache_install",
        "outcome": "passed" if successful else "failed",
        "subreaper_verified": True,
        "primary_exit_code": primary.returncode,
        "primary_timed_out": timed_out,
        "adopted_children_reaped": adopted,
        "descendant_deadline_exceeded": descendant_deadline,
        "owned_descendants_drained": drained,
    }


def write_receipt(path, value):
    require(
        path.parent.is_dir()
        and not path.parent.is_symlink()
        and not path.exists()
        and not path.is_symlink()
    )
    temporary = path.with_suffix(".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as output:
        json.dump(value, output, sort_keys=True)
        output.write("\n")
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    require(command[:3] == ["uv", "pip", "install"] and len(command) > 3)
    try:
        receipt = run(command)
    except Exception:
        receipt = {
            "schema": 1,
            "stage": "cache_install",
            "outcome": "failed",
            "failure_code": "cache_child_wrapper_refused",
        }
    write_receipt(args.receipt, receipt)
    raise SystemExit(0 if receipt["outcome"] == "passed" else 1)


if __name__ == "__main__":
    main()
