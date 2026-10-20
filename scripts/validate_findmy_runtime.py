"""Check the built runtime outside the checkout; live modes require explicit flags.

Default: imports/readiness only, no network or machine state. Public acquisition
and anonymous provisioning use only newly created disposable storage. This tool
never signs into an Apple account or reads an existing Home Assistant directory.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import hmac
import importlib
import io
import json
import logging
import os
from pathlib import Path
import re
import selectors
import signal
import socket
import ssl
import subprocess
import sys
import tempfile
import time
from types import ModuleType
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MODES = {"readiness", "acquire", "provision"}
PHASES = {
    "package",
    "imports",
    "library",
    "worker",
    "provision",
    "otp",
    "vault",
    "restore",
    "complete",
}
MAX_OUTPUT = 16384
RUNTIME_STAGES = {
    "runtime",
    "library",
    "initialize",
    "lookup",
    "start_request",
    "start_native",
    "finish_request",
    "finish_native",
    "validate_state",
    "complete",
}
RUNTIME_FAILURES = {
    "library_unavailable",
    "native_unavailable",
    "http_refused",
    "response_shape",
    "apple_refused",
    "state_refused",
    "cleanup_failed",
    "cancelled",
    "timeout",
    "other",
}
RUNTIME_FIELDS = {
    "runtime_stage",
    "runtime_failure",
    "last_provision_http",
    "last_provision_apple_code",
    "last_provision_hsc",
}


def _runtime_projection(value):
    """Independently validate the provider's fixed scalar diagnostic contract."""
    if (
        type(value) is not dict
        or set(value)
        != {
            "schema",
            "stage",
            "request_count",
            "last_http",
            "last_apple_code",
            "last_apple_hsc",
            "failure",
        }
        or type(value["schema"]) is not int
        or value["schema"] != 1
        or type(value["stage"]) is not str
        or value["stage"] not in RUNTIME_STAGES
        or type(value["request_count"]) is not int
        or not 0 <= value["request_count"] <= 3
    ):
        raise ValueError("runtime_receipt_refused")
    result = {
        "runtime_stage": value["stage"],
        "runtime_failure": value["failure"],
        "last_provision_http": value["last_http"],
        "last_provision_apple_code": value["last_apple_code"],
        "last_provision_hsc": value["last_apple_hsc"],
    }
    _validate_runtime(result)
    return result


def _validate_runtime(value):
    stage, failure = value["runtime_stage"], value["runtime_failure"]
    if (
        type(stage) is not str
        or stage not in RUNTIME_STAGES | {"not_observed"}
        or failure is not None
        and (type(failure) is not str or failure not in RUNTIME_FAILURES)
    ):
        raise ValueError("runtime_receipt_refused")
    for name, minimum, maximum in (
        ("last_provision_http", 100, 599),
        ("last_provision_apple_code", -1000000, 1000000),
        ("last_provision_hsc", -1000000, 1000000),
    ):
        item = value[name]
        if item is not None and (
            type(item) is not int or not minimum <= item <= maximum
        ):
            raise ValueError("runtime_receipt_refused")
    if stage == "not_observed" and any(
        value[name] is not None for name in RUNTIME_FIELDS - {"runtime_stage"}
    ):
        raise ValueError("runtime_receipt_refused")


def _pairs(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("runtime_receipt_refused")
        result[name] = value
    return result


def empty(mode="readiness"):
    return {
        "schema": 1,
        "mode": mode,
        "outcome": "unavailable",
        "phase": "package",
        "runtime_stage": "not_observed",
        "runtime_failure": None,
        "last_provision_http": None,
        "last_provision_apple_code": None,
        "last_provision_hsc": None,
        "package_sha256": None,
        "package_members": 0,
        "isolated_cwd": False,
        "packaged_imports": False,
        "emulator_imports": False,
        "library_verified": False,
        "cold_worker_ready": False,
        "provider_provisioned": False,
        "otp_generated": False,
        "cold_restore": False,
        "machine_id_stable": None,
        "identity_unchanged": None,
        "vault_roundtrip": False,
        "public_download_requests": 0,
        "provisioning_requests": 0,
        "worker_children": 0,
        "network_attempts_blocked": 0,
        "cleanup_ok": False,
        "account_requests": 0,
        "owner_data_read": False,
        "locations_accessed": False,
    }


def validate(value):
    if (
        type(value) is not dict
        or set(value) != set(empty())
        or type(value["schema"]) is not int
        or value["schema"] != 1
    ):
        raise ValueError("runtime_receipt_refused")
    if (
        type(value["mode"]) is not str
        or value["mode"] not in MODES
        or type(value["phase"]) is not str
        or value["phase"] not in PHASES
        or type(value["outcome"]) is not str
        or value["outcome"] not in {"ready", "unavailable"}
    ):
        raise ValueError("runtime_receipt_refused")
    if value["package_sha256"] is not None and (
        type(value["package_sha256"]) is not str
        or re.fullmatch(r"[0-9a-f]{64}", value["package_sha256"]) is None
    ):
        raise ValueError("runtime_receipt_refused")
    _validate_runtime(value)
    if value["mode"] != "provision" and value["runtime_stage"] != "not_observed":
        raise ValueError("runtime_receipt_refused")
    for name, maximum in {
        "package_members": 5000,
        "public_download_requests": 1,
        "provisioning_requests": 3,
        "worker_children": 8,
        "network_attempts_blocked": 64,
        "account_requests": 0,
    }.items():
        if type(value[name]) is not int or not 0 <= value[name] <= maximum:
            raise ValueError("runtime_receipt_refused")
    for name in (
        set(empty())
        - RUNTIME_FIELDS
        - {
            "schema",
            "mode",
            "outcome",
            "phase",
            "package_sha256",
            "package_members",
            "public_download_requests",
            "provisioning_requests",
            "worker_children",
            "network_attempts_blocked",
            "account_requests",
            "machine_id_stable",
            "identity_unchanged",
        }
    ):
        if type(value[name]) is not bool:
            raise ValueError("runtime_receipt_refused")
    if (
        any(
            value[name] is not None and type(value[name]) is not bool
            for name in ("machine_id_stable", "identity_unchanged")
        )
        or value["owner_data_read"] is not False
        or value["locations_accessed"] is not False
    ):
        raise ValueError("runtime_receipt_refused")
    if value["mode"] == "readiness" and any(
        value[name]
        for name in (
            "public_download_requests",
            "provisioning_requests",
            "worker_children",
            "library_verified",
            "otp_generated",
            "provider_provisioned",
            "vault_roundtrip",
            "cold_restore",
        )
    ):
        raise ValueError("runtime_receipt_refused")
    if value["mode"] == "acquire" and (
        value["provisioning_requests"]
        or value["provider_provisioned"]
        or value["otp_generated"]
        or value["vault_roundtrip"]
        or value["cold_restore"]
    ):
        raise ValueError("runtime_receipt_refused")
    if value["outcome"] == "ready":
        if (
            value["phase"] != "complete"
            or not all(
                value[name] is True
                for name in (
                    "isolated_cwd",
                    "packaged_imports",
                    "emulator_imports",
                    "cleanup_ok",
                )
            )
            or value["network_attempts_blocked"]
            or value["runtime_failure"] is not None
        ):
            raise ValueError("runtime_receipt_refused")
        if value["mode"] != "readiness" and not (
            value["library_verified"] and value["cold_worker_ready"]
        ):
            raise ValueError("runtime_receipt_refused")
        if value["mode"] == "provision" and (
            value["provisioning_requests"] != 3
            or not all(
                value[name] is True
                for name in (
                    "provider_provisioned",
                    "otp_generated",
                    "vault_roundtrip",
                    "cold_restore",
                    "machine_id_stable",
                    "identity_unchanged",
                )
            )
        ):
            raise ValueError("runtime_receipt_refused")
    return dict(value)


def _capture(command, cwd, timeout):
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    output, deadline = bytearray(), time.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while selector.get_map():
                if time.monotonic() >= deadline:
                    raise ValueError("runtime_probe_timeout")
                for key, _ in selector.select(
                    min(1, max(0, deadline - time.monotonic()))
                ):
                    data = os.read(key.fd, 4096)
                    if not data:
                        selector.unregister(key.fileobj)
                    else:
                        output.extend(data)
                        if len(output) > MAX_OUTPUT:
                            raise ValueError("runtime_probe_output_refused")
        process.wait(timeout=max(0.1, deadline - time.monotonic()))
        if process.returncode != 0 or len(output.splitlines()) != 1:
            raise ValueError("runtime_probe_output_refused")
        return validate(json.loads(output, object_pairs_hook=_pairs))
    finally:
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait()
        process.stdout.close()


def run_validation(archive, *, mode="readiness", inventory=None):
    result = empty(mode)
    try:
        if mode not in MODES:
            raise ValueError("runtime_mode_refused")
        scripts = str(Path(__file__).resolve().parent)
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        from validate_release import inspect_archive

        payload = inspect_archive(archive, inventory)
        result["package_sha256"] = hashlib.sha256(
            Path(archive).read_bytes()
        ).hexdigest()
        result["package_members"] = len(payload)
        with tempfile.TemporaryDirectory(
            prefix="homecircle-runtime-validation-"
        ) as directory:
            temporary = Path(directory)
            temporary.chmod(0o700)
            package, cwd = temporary / "package/homecircle", temporary / "work"
            package.mkdir(mode=0o700, parents=True)
            cwd.mkdir(mode=0o700)
            for name, raw in payload.items():
                target = package / name
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                target.write_bytes(raw)
            timeout = {"readiness": 90, "acquire": 720, "provision": 1000}[mode]
            child = _capture(
                [
                    sys.executable,
                    "-I",
                    "-B",
                    str(Path(__file__).resolve()),
                    "--_child",
                    mode,
                    str(package),
                ],
                cwd,
                timeout,
            )
            if child["mode"] != mode:
                raise ValueError("runtime_receipt_refused")
            child["package_sha256"], child["package_members"] = (
                result["package_sha256"],
                result["package_members"],
            )
            return validate(child)
    except BaseException:
        return validate(result)


def _child(mode, package):
    result = empty(mode)
    work, package = Path.cwd().resolve(), Path(package).resolve(strict=True)
    workers, providers = [], []
    current_host, addresses = [None], set()
    loop = asyncio.new_event_loop()
    # Core and test environments can install dependencies in a separate site
    # directory. Permit those active installed-package roots, never arbitrary
    # search paths or the checkout. Writes remain confined to disposable work.
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
    ca = ssl.get_default_verify_paths()
    ca_paths = tuple(Path(path).resolve() for path in (ca.cafile, ca.capath) if path)
    expected_worker = str(package / "_findmy_runtime/worker.py")
    original_resolve = socket.getaddrinfo

    def refuse():
        result["network_attempts_blocked"] = min(
            64, result["network_attempts_blocked"] + 1
        )
        raise PermissionError("runtime_probe_boundary")

    def resolve(host, port, *args, **kwargs):
        if host != current_host[0] or port != 443:
            refuse()
        values = original_resolve(host, port, *args, **kwargs)
        addresses.update(value[4] for value in values)
        return values

    def guard(event, args):
        if event == "socket.getaddrinfo" and (
            args[0] != current_host[0] or args[1] != 443
        ):
            refuse()
        if event == "socket.connect" and (
            current_host[0] is None or args[1] not in addresses
        ):
            refuse()
        if event in {
            "socket.bind",
            "socket.sendto",
            "socket.sendmsg",
            "socket.gethostbyname",
            "socket.gethostbyaddr",
        }:
            refuse()
        if event == "urllib.Request":
            if (
                mode == "readiness"
                or result["phase"] != "library"
                or args[0] != bootstrap.DMG_URL
                or result["public_download_requests"] >= 1
            ):
                refuse()
            result["public_download_requests"] += 1
        if event == "subprocess.Popen":
            if (
                mode == "readiness"
                or list(args[1]) != [sys.executable, "-B", expected_worker]
                or result["worker_children"] >= 8
            ):
                refuse()
            result["worker_children"] += 1
        if event in {"os.system", "os.posix_spawn"} or event.startswith("os.exec"):
            refuse()
        if event == "open":
            path, open_mode, flags = args
            if type(path) is int:
                return
            location = Path(os.fsdecode(path)).resolve()
            writing = (
                type(open_mode) is str
                and any(char in open_mode for char in "wax+")
                or type(flags) is int
                and flags
                & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
            )
            # asyncio opens stderr=DEVNULL with O_RDWR before the Popen audit.
            # This sink cannot modify an owner file; all other writes stay local.
            if (
                writing
                and location != Path(os.devnull)
                and not location.is_relative_to(work)
            ):
                raise PermissionError("runtime_probe_write_refused")
            if (
                not writing
                and location != Path(os.devnull)
                and not any(
                    location == root or location.is_relative_to(root)
                    for root in allowed + ca_paths
                )
            ):
                raise PermissionError("runtime_probe_read_refused")
        if event in {
            "os.remove",
            "os.rmdir",
            "os.mkdir",
            "os.chmod",
            "os.chown",
            "os.truncate",
            "os.link",
            "os.symlink",
            "os.utime",
            "os.rename",
        }:
            # These operations are used only by the temporary library cache/vault.
            # Relative dir-fd operations are anchored by the packaged implementations.
            for path in (
                args[:2]
                if event in {"os.rename", "os.link", "os.symlink"}
                else args[:1]
            ):
                if isinstance(path, (str, bytes)) and not Path(
                    os.fsdecode(path)
                ).resolve().is_relative_to(work):
                    raise PermissionError("runtime_probe_write_refused")

    logging.disable(logging.CRITICAL)
    sys.dont_write_bytecode = True
    socket.getaddrinfo = resolve
    sys.addaudithook(guard)
    with (
        contextlib.redirect_stdout(io.StringIO()),
        contextlib.redirect_stderr(io.StringIO()),
    ):
        try:
            result["phase"] = "imports"
            if (
                mode not in MODES
                or package != work.parent / "package/homecircle"
                or ROOT == work
                or work.is_relative_to(ROOT)
            ):
                raise ValueError("runtime_probe_isolation_refused")
            result["isolated_cwd"] = True
            # Match HA's absolute imports without executing the integration entrypoint.
            components = ModuleType("custom_components")
            components.__path__ = [str(package.parent)]
            namespace = ModuleType("custom_components.homecircle")
            namespace.__path__ = [str(package)]
            components.homecircle = namespace
            sys.modules["custom_components"] = components
            sys.modules["custom_components.homecircle"] = namespace
            original_socket = socket.socket

            class ImportSocket(original_socket):
                def __init__(self, *args, **kwargs):
                    raise OSError("offline_dependency_import")

            socket.socket = ImportSocket
            try:
                provider = importlib.import_module(
                    "custom_components.homecircle._findmy_runtime.provider"
                )
                worker_module = importlib.import_module(
                    "custom_components.homecircle._findmy_runtime.worker"
                )
                bootstrap = importlib.import_module(
                    "custom_components.homecircle._findmy_runtime.bootstrap"
                )
                unicorn = importlib.import_module("unicorn")
                if unicorn.__version__ != "2.1.4":
                    raise ValueError("runtime_dependency_refused")
                sys.path.insert(0, str(package / "_findmy_runtime/emulator"))
                emulator = [
                    importlib.import_module(name)
                    for name in ("macho", "harness", "stubs", "adi_run")
                ]
            finally:
                socket.socket = original_socket
            for item in (provider, worker_module, bootstrap, *emulator):
                if not Path(item.__file__).resolve().is_relative_to(package):
                    raise ValueError("runtime_probe_import_refused")
            if not all(
                callable(getattr(item, name, None))
                for item, name in (
                    (provider, "MacAnisetteProvider"),
                    (provider, "Worker"),
                    (provider, "new_identity"),
                    (worker_module, "Engine"),
                    (bootstrap, "ensure_library"),
                )
            ):
                raise ValueError("runtime_probe_import_refused")
            result["packaged_imports"] = result["emulator_imports"] = True

            class OwnedWorker(provider.Worker):
                def __init__(self):
                    super().__init__()
                    workers.append(self)

            provider.Worker = OwnedWorker
            base_http = provider.BoundedHttpSession

            class AuditedHTTP(base_http):
                async def request(self, method, url, **options):
                    index = result["provisioning_requests"]
                    if mode != "provision" or index >= 3:
                        refuse()
                    if index == 0:
                        if method != "GET" or url != provider.LOOKUP:
                            refuse()
                    elif (
                        method != "POST"
                        or provider._provision_url(url, ("start", "finish")[index - 1])
                        != url
                    ):
                        refuse()
                    result["provisioning_requests"] += 1
                    current_host[0] = urlsplit(url).hostname
                    try:
                        return await super().request(method, url, **options)
                    finally:
                        current_host[0] = None

            provider.BoundedHttpSession = AuditedHTTP

            async def execute():
                if mode == "readiness":
                    return
                result["phase"] = "library"
                current_host[0] = urlsplit(bootstrap.DMG_URL).hostname
                try:
                    library = await bootstrap.ensure_library(
                        work / "cache/legacy-libraries.bin"
                    )
                finally:
                    current_host[0] = None
                if (
                    hashlib.sha256(library.read_bytes()).hexdigest()
                    != bootstrap.LIBRARY_SHA256
                ):
                    raise ValueError("runtime_library_refused")
                result["library_verified"] = True
                result["phase"] = "worker"
                cold = OwnedWorker()
                try:
                    if await cold.open(library, provider.new_identity(), {}) != {
                        "provisioned": False
                    }:
                        raise ValueError("runtime_worker_refused")
                    result["cold_worker_ready"] = True
                finally:
                    await cold.close()
                if mode == "acquire":
                    return
                result["phase"] = "provision"
                machine = provider.MacAnisetteProvider(
                    libs_path=work / "cache/legacy-libraries.bin"
                )
                providers.append(machine)
                await machine._get_ani()
                result["provider_provisioned"] = True
                result["phase"] = "otp"
                first = await machine.get_headers(
                    machine.local_user_uuid, machine.device_uuid, machine.serial
                )
                result["otp_generated"] = bool(
                    first.get("X-Apple-I-MD") and first.get("X-Apple-I-MD-M")
                )
                mapping = machine.to_json()
                identity = (
                    machine.local_user_uuid,
                    machine.device_uuid,
                    machine.host_uuid,
                    machine.serial,
                )
                await machine.close()
                result["phase"] = "vault"
                vault_type = importlib.import_module(
                    "custom_components.homecircle.findmy_vault"
                ).Vault
                vault = vault_type(work / "fixture-vault")
                session = {
                    "account": {
                        "username": "synthetic@example.invalid",
                        "password": None,
                        "info": None,
                    },
                    "anisette": mapping,
                }
                await asyncio.to_thread(
                    vault.save_account,
                    session,
                    {"fixture": {"accessory": {}, "report": None}},
                )
                saved = await asyncio.to_thread(vault.load)
                if (
                    saved["session"]["anisette"] != mapping
                    or json.dumps(mapping).encode() in vault.data_path.read_bytes()
                ):
                    raise ValueError("runtime_vault_refused")
                result["vault_roundtrip"] = True
                result["phase"] = "restore"
                restored = provider.MacAnisetteProvider.from_json(
                    saved["session"]["anisette"],
                    libs_path=work / "cache/legacy-libraries.bin",
                )
                providers.append(restored)
                second = await restored.get_headers(
                    restored.local_user_uuid, restored.device_uuid, restored.serial
                )
                result["identity_unchanged"] = identity == (
                    restored.local_user_uuid,
                    restored.device_uuid,
                    restored.host_uuid,
                    restored.serial,
                )
                result["machine_id_stable"] = hmac.compare_digest(
                    first["X-Apple-I-MD-M"], second["X-Apple-I-MD-M"]
                )
                result["cold_restore"] = bool(second.get("X-Apple-I-MD"))
                await restored.close()

            loop.run_until_complete(execute())
            result["phase"] = "complete"
            result["outcome"] = "ready"
        except BaseException:
            result["outcome"] = "unavailable"
        finally:
            # Close must not erase the operation that failed. Never copy a raw reply.
            for item in providers:
                try:
                    snapshot = item.safe_diagnostics()
                    diagnostic = _runtime_projection(snapshot)
                    if result["runtime_failure"] is None and (
                        diagnostic["runtime_failure"] is not None
                        or snapshot["request_count"] > 0
                        or result["runtime_stage"] == "not_observed"
                    ):
                        result.update(diagnostic)
                except BaseException:
                    pass  # Optional diagnostics cannot alter runtime cleanup or output.

            async def cleanup():
                for item in providers:
                    await item.close()
                for item in workers:
                    await item.close()
                await loop.shutdown_default_executor()

            try:
                loop.run_until_complete(cleanup())
                result["cleanup_ok"] = all(item.process is None for item in workers)
            except BaseException:
                result["outcome"] = "unavailable"
            loop.close()
    try:
        result = validate(result)
    except Exception:
        result["outcome"] = "unavailable"
        try:
            result = validate(result)
        except Exception:
            result = empty(mode)
    print(json.dumps(result, allow_nan=False))


def main():
    # Private child invocation has exactly three arguments after the script name.
    if len(sys.argv) == 4 and sys.argv[1] == "--_child":
        _child(sys.argv[2], sys.argv[3])
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=ROOT / "release/homecircle.zip")
    parser.add_argument("--inventory", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--acquire-runtime", action="store_true")
    mode.add_argument("--provision-anonymous", action="store_true")
    args = parser.parse_args()
    selected = (
        "provision"
        if args.provision_anonymous
        else "acquire"
        if args.acquire_runtime
        else "readiness"
    )
    result = run_validation(args.archive, mode=selected, inventory=args.inventory)
    print(json.dumps(result, allow_nan=False))
    if result["outcome"] != "ready":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
