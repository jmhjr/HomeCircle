"""Independent /proc proof inside the original consumer; no HA/provider import."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import sys


def command(raw):
    return [item.decode("utf-8", "strict") for item in raw.rstrip(b"\0").split(b"\0")]


def is_core(argv):
    return (
        len(argv) == 6
        and Path(argv[0]).name in {"python3", "python3.14"}
        and argv[1:] == ["-P", "-m", "homeassistant", "--config", "/config"]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pins", type=Path, required=True)
    parser.add_argument("--pins-sha", required=True)
    parser.add_argument("--phase", choices=("first", "restart"), required=True)
    args = parser.parse_args()
    raw = args.pins.read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.pins_sha:
        raise RuntimeError("process_pin_hash_refused")
    values = json.loads(raw)
    path = args.pins.parent / "common.py"
    if hashlib.sha256(path.read_bytes()).hexdigest() != values["controls"]["common.py"]:
        raise RuntimeError("process_common_refused")
    spec = importlib.util.spec_from_file_location("consumer_process_common", path)
    c = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(c)
    c.controls(args.pins.parent, values)
    c.check(
        sys.platform == "linux"
        and platform.machine() == values["machine"]
        and platform.python_version() == values["python"],
        "process_runtime_refused",
    )
    for name, expected in values["startup_scripts"].items():
        c.read(Path("/") / name, expected)
    status = dict(
        line.split(":", 1)
        for line in Path("/proc/self/status").read_text().splitlines()
        if ":" in line
    )
    c.check(
        status["CapBnd"].strip() == values["capability_mask"]
        and int(status["CapEff"].strip(), 16) & ~int(values["capability_mask"], 16)
        == 0,
        "finite_default_capabilities_refused",
    )
    allowed = {"/" + name: digest for name, digest in values["native_s6"].items()}

    def native(pid, choices):
        executable = Path(f"/proc/{pid}/exe").resolve()
        c.check(str(executable) in choices, "native_s6_process_path_refused")
        c.read(executable, allowed[str(executable)])
        return executable.name

    init_names = {
        name for name in allowed if Path(name).name in {"s6-svscan", "s6-linux-init"}
    }
    pid1 = native(1, init_names)
    matches = []
    for item in Path("/proc").iterdir():
        if item.name.isdigit():
            try:
                if is_core(command((item / "cmdline").read_bytes())):
                    matches.append(item)
            except (ProcessLookupError, FileNotFoundError):
                pass
    c.check(len(matches) == 1, "single_original_core_process_required")
    core = matches[0]
    environment = dict(
        item.split(b"=", 1)
        for item in (core / "environ").read_bytes().split(b"\0")
        if b"=" in item
    )
    c.check(
        environment.get(b"PYTHONMALLOC") == b"mimalloc"
        and b"PYTHONPATH" not in environment
        and b"PYTHONHOME" not in environment,
        "core_allocator_or_import_override_refused",
    )
    c.check(
        c.sha((core / "exe").resolve().read_bytes())
        == c.sha(Path("/proc/self/exe").resolve().read_bytes()),
        "core_interpreter_identity_refused",
    )
    child = core
    seen = set()
    supervisor = False
    while child.name != "1":
        c.check(
            child.name not in seen and len(seen) < 16, "core_process_ancestry_refused"
        )
        seen.add(child.name)
        fields = (child / "stat").read_text().rsplit(")", 1)[1].split()
        parent = fields[1]
        c.check(parent.isdigit() and parent != "0", "core_not_descended_from_init")
        child = Path("/proc") / parent
        executable = (child / "exe").resolve()
        if executable.name == "s6-supervise":
            native(
                child.name,
                {name for name in allowed if Path(name).name == "s6-supervise"},
            )
            supervisor = True
    c.check(supervisor, "core_s6_supervisor_missing")
    identity = c.sha((core / "stat").read_bytes())
    result = {
        **c.base_receipt(values),
        "outcome": "passed",
        "phase": args.phase,
        "native_s6_pid1": pid1,
        "core_under_native_s6_supervisor": True,
        "core_exact_original_cli_arguments": True,
        "core_mimalloc_environment": True,
        "no_import_path_override": True,
        "finite_default_capabilities": True,
        "final_startup_files_exact": True,
        "core_process_identity_sha256": identity,
    }
    c.atomic(args.pins.parent / (args.phase + "-process.json"), result)
    print(json.dumps({"outcome": "passed", "phase": args.phase}))


if __name__ == "__main__":
    main()
