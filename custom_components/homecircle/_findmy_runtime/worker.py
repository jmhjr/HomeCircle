"""Private, bounded IPC for the local emulator; no network or disk state writes.

The parent owns transport, provisioning consent, persistence and process lifetime.
Only a hash-verified public library and in-memory machine data enter this child.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import resource
import sys

LIMIT = 2 * 1024 * 1024
LIBRARY_SHA256 = "2eafc3c79c7f41a8afbfbeaaf23ee5dab5ad5bda55ec8e54dbc0ddf1d20ce630"


def blob(value, limit=1024 * 1024, *, allow_empty=False):
    if type(value) is not str or not (0 if allow_empty else 1) <= len(value) <= (limit * 4 // 3 + 8):
        raise ValueError("native_input_refused")
    result = base64.b64decode(value, validate=True)
    if not (0 if allow_empty else 1) <= len(result) <= limit:
        raise ValueError("native_input_refused")
    return result


def checked(result, *, missing=False):
    if result.rc != 0 or result.ret < 0 and not (missing and result.ret == -45061):
        raise ValueError("native_operation_refused")
    return result.outputs


def restrict(event, arguments):
    if event.startswith("socket.") or event in ("subprocess.Popen", "os.system"):
        raise PermissionError("native_local_only")
    if event == "open":
        mode, flags = arguments[1:3]
        if (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
            isinstance(flags, int)
            and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
        ):
            raise PermissionError("native_read_only")


class Engine:
    def __init__(self, library, host_uuid, stores):
        # This executable is invoked by absolute path and keeps no package-path
        # mutation in the HA process. Only its adjacent emulator is importable here.
        sys.path.insert(0, str(Path(__file__).parent / "emulator"))
        from adi_run import CoreADI

        path = Path(library)
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 16 * 1024**2:
            raise ValueError("native_library_refused")
        if hashlib.sha256(path.read_bytes()).hexdigest() != LIBRARY_SHA256:
            raise ValueError("native_library_refused")
        if type(host_uuid) is not str or len(host_uuid) != 32:
            raise ValueError("native_identity_refused")
        host = bytes.fromhex(host_uuid)
        if type(stores) is not dict or len(stores) > 32:
            raise ValueError("native_store_refused")
        self.engine = CoreADI(path=path)
        self.engine.stubs.hostuuid = host
        for name, value in stores.items():
            if (
                type(name) is not str or not 0 < len(name) <= 100
                or name in (".", "..", "adi.pb")
                or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for c in name)
            ):
                raise ValueError("native_store_refused")
            self.engine.stubs.files["/Users/Shared/adi/" + name] = bytearray(blob(value, allow_empty=True))
        checked(self.engine.initialize())
        self.session = None

    def run(self, message):
        op = message.get("op")
        if op == "check":
            result = self.engine.is_machine_provisioned(-2)
            checked(result, missing=True)
            return {"provisioned": result.ret == 0}
        if op == "start" and self.session is None:
            result = checked(self.engine.provisioning_start(-2, blob(message["spim"], 131072)))
            self.session = result["session_id"]
            return {"cpim": base64.b64encode(result["cpim"]).decode()}
        if op == "finish" and self.session is not None:
            checked(self.engine.provisioning_end(
                self.session, blob(message["ptm"], 131072), blob(message["tk"], 131072)
            ))
            routing = message["routing"]
            if type(routing) is not int or not 0 < routing < 2**64:
                raise ValueError("native_routing_refused")
            checked(self.engine.set_routing(-2, routing))
            if self.engine.is_machine_provisioned(-2).ret != 0:
                raise ValueError("native_provisioning_refused")
            self.session = None
            stores = {}
            for path, data in self.engine.stubs.files.items():
                if path.startswith("/Users/Shared/adi/") and path.rsplit("/", 1)[-1] != "adi.pb":
                    name = path.rsplit("/", 1)[-1]
                    if len(data) > 1024**2:
                        raise ValueError("native_store_refused")
                    stores[name] = base64.b64encode(data).decode()
            if not stores:
                raise ValueError("native_store_refused")
            return {"store": stores}
        if op == "otp":
            check = self.engine.is_machine_provisioned(-2)
            if check.rc != 0 or check.ret != 0:
                raise ValueError("native_provisioning_refused")
            routing = checked(self.engine.get_routing(-2))["routing"]
            if routing != message["routing"]:
                raise ValueError("native_routing_refused")
            result = checked(self.engine.request_otp(-2))
            return {key: base64.b64encode(result[key]).decode() for key in ("otp", "mid")}
        raise ValueError("native_command_refused")


def main():
    sys.dont_write_bytecode = True
    for name in ("ADI_FROZEN_TIME", "COREADI_PATH", "COREADI_DISPATCH"):
        os.environ.pop(name, None)
    resource.setrlimit(resource.RLIMIT_CPU, (90, 90))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    if sys.platform == "linux":
        resource.setrlimit(resource.RLIMIT_AS, (3072 * 1024**2, 3072 * 1024**2))
    sys.addaudithook(restrict)
    engine = None
    for _ in range(5):
        raw = sys.stdin.buffer.readline(LIMIT + 1)
        if not raw:
            return
        if len(raw) > LIMIT or not raw.endswith(b"\n"):
            raise ValueError("native_input_refused")
        message = json.loads(raw)
        if type(message) is not dict:
            raise ValueError("native_input_refused")
        if engine is None:
            if message.get("op") != "open":
                raise ValueError("native_command_refused")
            engine = Engine(message["library"], message["host_uuid"], message["store"])
            result = engine.run({"op": "check"})
        else:
            result = engine.run(message)
        output = json.dumps(result, separators=(",", ":"))
        if len(output) > LIMIT:
            raise ValueError("native_output_refused")
        print(output, flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # No traceback can disclose a provisioning response or local state.
        sys.exit(1)
