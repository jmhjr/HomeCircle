"""Linux-only public-file guard on one hash-pinned, PAX-free 326-file snapshot."""

import sys

if sys.platform != "linux":
    raise SystemExit("linux_required")

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import signal
import subprocess
import tarfile
import tempfile
import time


SOURCE_SHA = "fce0ec0a5c40c55791c4d3fa3d154c30c11ab9e23d279b9fdeadb0155113196d"
INVENTORY_SHA = "fb1c5224cc5f9aa12479651c418e516b2acfad17e4f905f69231aa05ea91ff46"
CHECKER_SHA = "dd5f420d47781f31ce011212b1201f21d1c347a2e6feac8ca3882094c486ad51"
COUNT = 326
MAXIMUM_BYTES = 64 * 1024**2
RULES = {
    "Google key", "private key", "JWT token", "numeric coordinate field", "street address",
    "private network address", "credential assignment", "private/runtime path",
    "unreviewed media/archive/secret artifact", "unreviewed binary file", "binary content",
    "non-example entity identifier", "symlink requires review", "reviewed asset changed; review required",
}


class Refused(RuntimeError):
    pass


class Terminated(BaseException):
    pass


def check(condition, label):
    if not condition:
        raise Refused(label)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pinned_file(path, expected, maximum):
    check(re.fullmatch(r"[0-9a-f]{64}", expected) is not None, "final_input_pins_required")
    check(path.is_file() and not path.is_symlink() and path.stat().st_size <= maximum, "input_path_refused")
    raw = path.read_bytes()
    check(digest(raw) == expected, "input_hash_refused")
    return raw


def payload(source_path, inventory_path):
    """Validate both input hashes and every member before any extraction."""
    source = pinned_file(source_path, SOURCE_SHA, MAXIMUM_BYTES)
    encoded_inventory = pinned_file(inventory_path, INVENTORY_SHA, 2 * 1024**2)
    inventory = json.loads(encoded_inventory)
    check(isinstance(inventory, dict) and len(inventory) == COUNT, "inventory_count_refused")
    for name, item in inventory.items():
        path = PurePosixPath(name)
        check(bool(path.parts) and name == path.as_posix() and not path.is_absolute()
              and ".." not in path.parts and ".git" not in path.parts and "\\" not in name
              and "\n" not in name and "\r" not in name and "\0" not in name, "inventory_path_refused")
        check(isinstance(item, dict) and set(item) == {"bytes", "sha256"}
              and type(item["bytes"]) is int and 0 <= item["bytes"] <= MAXIMUM_BYTES
              and isinstance(item["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", item["sha256"]),
              "inventory_entry_refused")
    # tarfile deliberately hides PAX/GNU control records. Inspect raw headers
    # as well, so even empty or trailing metadata records cannot pass unnoticed.
    tar_limit = MAXIMUM_BYTES + COUNT * 1024 + 10240
    with gzip.GzipFile(fileobj=io.BytesIO(source)) as compressed:
        raw_tar = compressed.read(tar_limit + 1)
    check(len(raw_tar) <= tar_limit and len(raw_tar) % 512 == 0, "raw_tar_size_refused")
    offset, regular = 0, 0
    while offset + 512 <= len(raw_tar):
        header = raw_tar[offset:offset + 512]
        if header == bytes(512):
            check(len(raw_tar) - offset >= 1024 and not any(raw_tar[offset:]), "raw_tar_trailer_refused")
            break
        check(header[156:157] in {b"0", b"\0"} and header[257:263] == b"ustar\0",
              "raw_tar_metadata_refused")
        encoded_size = header[124:136].strip(b"\0 ")
        check(bool(encoded_size) and all(byte in b"01234567" for byte in encoded_size), "raw_tar_number_refused")
        size = int(encoded_size, 8)
        check(size <= MAXIMUM_BYTES, "raw_tar_member_size_refused")
        offset += 512 + ((size + 511) // 512) * 512
        check(offset <= len(raw_tar), "raw_tar_truncation_refused")
        regular += 1
    else:
        raise Refused("raw_tar_terminator_required")
    check(regular == COUNT, "raw_tar_count_refused")
    files = {}
    with tarfile.open(fileobj=io.BytesIO(source), mode="r:gz") as archive:
        check(not archive.pax_headers, "archive_pax_headers_refused")
        members = archive.getmembers()
        check(not archive.pax_headers, "archive_pax_headers_refused")
        check(len(members) == COUNT and sum(member.size for member in members) <= MAXIMUM_BYTES,
              "archive_size_refused")
        for member in members:
            check(member.isfile() and not member.issym() and not member.islnk()
                  and not member.pax_headers, "archive_metadata_refused")
            check(member.name in inventory and member.name not in files, "archive_names_refused")
            stream = archive.extractfile(member)
            check(stream is not None, "archive_read_refused")
            raw = stream.read()
            check(inventory[member.name] == {"bytes": len(raw), "sha256": digest(raw)}, "archive_bytes_refused")
            files[member.name] = raw
    check(set(files) == set(inventory), "archive_members_refused")
    check(digest(files.get("scripts/check_public_files.py", b"")) == CHECKER_SHA,
          "unchanged_public_checker_required")
    return files


def run_owned(command, *, cwd, env, limit):
    child = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        stdout, stderr = child.communicate(timeout=limit)
        check(len(stdout) <= 2 * 1024**2 and len(stderr) <= 2 * 1024**2, "child_output_size_refused")
        return child.returncode, stdout, stderr
    except BaseException:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.communicate(timeout=10)
        raise


def safe_output(stdout, stderr, names, exit_code):
    expected = f"Privacy guard checked {COUNT} files; "
    passed = expected + "no flagged patterns. Manual review still required."
    failed = expected + "review required."
    text = stdout.decode("utf-8")
    check(text in {passed + "\n", failed + "\n"}, "checker_stdout_contract_refused")
    found = []
    for line in stderr.decode("utf-8").splitlines():
        name, separator, rules = line.partition(": ")
        labels = rules.split(", ")
        check(separator and name in names and labels and all(label in RULES for label in labels),
              "checker_stderr_contract_refused")
        found.append({"path": name, "rules": labels})
    check((exit_code == 0 and not found and text == passed + "\n") or
          (exit_code == 1 and bool(found) and text == failed + "\n"), "checker_exit_contract_refused")
    lines = [item["path"] + ": " + ", ".join(item["rules"]) for item in found]
    return found, "\n".join([*lines, text.rstrip("\n")]) + "\n"


def atomic_json(path, value):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    check(not args.output.exists() and not args.output.is_symlink(), "fresh_output_required")
    args.output.mkdir(mode=0o700)
    output = args.output.resolve()
    started = time.monotonic()
    receipt = {"schema": 1, "outcome": "failed", "completed": False,
               "system": "Linux", "machine": platform.machine(), "expected_public_files": COUNT,
               "source_sha256": SOURCE_SHA, "inventory_sha256": INVENTORY_SHA,
               "public_checker_sha256": CHECKER_SHA, "checker_changed": False,
               "checker_exit": None, "private_workspace_removed": False,
               "owner_accounts_used": False, "network_used": False}
    private_path = None
    stage = "inputs"
    status = 1
    original_handlers = {}

    def terminate(_signal, _frame):
        raise Terminated()

    try:
        for signum in (signal.SIGTERM, signal.SIGHUP):
            original_handlers[signum] = signal.signal(signum, terminate)
        files = payload(args.source, args.inventory)
        git = shutil.which("git")
        check(git is not None, "git_required")
        with tempfile.TemporaryDirectory(prefix=".private-", dir=output) as private:
            private_path = Path(private)
            tree = private_path / "public"
            tree.mkdir(mode=0o700)
            for name, raw in files.items():
                target = tree / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                   "LC_ALL": "C.UTF-8", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
                   "PYTHONDONTWRITEBYTECODE": "1"}
            stage = "git_init"
            code, _, _ = run_owned([git, "init", "--template=", "--initial-branch=public-check"], cwd=tree, env=env, limit=30)
            check(code == 0, "git_init_refused")
            names_path = private_path / "names"
            names_path.write_bytes(b"\0".join(name.encode() for name in sorted(files)) + b"\0")
            stage = "git_add"
            code, _, _ = run_owned([git, "--literal-pathspecs", "add", "--force", "--pathspec-from-file=" + str(names_path),
                                    "--pathspec-file-nul"], cwd=tree, env=env, limit=30)
            check(code == 0, "git_add_refused")
            code, names, _ = run_owned([git, "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                                       cwd=tree, env=env, limit=30)
            actual = names.decode("utf-8").split("\0")
            check(code == 0 and actual[-1] == "" and len(actual[:-1]) == COUNT
                  and set(actual[:-1]) == set(files), "git_public_names_refused")
            stage = "privacy_guard"
            code, stdout, stderr = run_owned([sys.executable, "-I", "-B", str(tree / "scripts/check_public_files.py"), "--all"],
                                             cwd=tree, env=env, limit=120)
            receipt["checker_exit"] = code
            found, safe_log = safe_output(stdout, stderr, set(files), code)
            (output / "privacy.log").write_text(safe_log)
            receipt["flagged_paths_and_rules"] = found
            receipt["public_files_checked"] = COUNT
            check(all((tree / name).read_bytes() == raw for name, raw in files.items()), "public_source_changed")
            check(code == 0, "privacy_review_required")
            receipt.update({"outcome": "passed", "completed": True})
            stage = "complete"
            status = 0
    except BaseException as error:
        receipt.update({"outcome": "failed", "completed": False, "failure_stage": stage,
                        "failure_type": type(error).__name__})
        if isinstance(error, Refused):
            receipt["failure_code"] = str(error)
    finally:
        for signum, handler in original_handlers.items():
            signal.signal(signum, handler)
        receipt["private_workspace_removed"] = private_path is None or not private_path.exists()
        if not receipt["private_workspace_removed"]:
            receipt.update({"outcome": "failed", "completed": False, "failure_code": "private_cleanup_failed"})
            status = 1
        receipt["host_elapsed_seconds"] = round(time.monotonic() - started, 3)
        atomic_json(output / "privacy.json", receipt)
    print(json.dumps({"outcome": receipt["outcome"], "public_files_checked": receipt.get("public_files_checked"),
                      "private_workspace_removed": receipt["private_workspace_removed"]}))
    return status


if __name__ == "__main__":
    try:
        result = main()
    except BaseException as failure:
        # Bootstrap or receipt-write failures must never print a raw traceback.
        print(json.dumps({"outcome": "failed", "failure_type": type(failure).__name__}), file=sys.stderr)
        result = 1
    raise SystemExit(result)
