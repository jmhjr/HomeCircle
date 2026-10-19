"""Actual archive inspection and isolated marker imports; no live runtime modes."""

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_release as build  # noqa: E402
from test_release_package import fixture_source, write_member, manual_archive  # noqa: E402

SPEC = importlib.util.spec_from_file_location(
    "validate_findmy_runtime_test", ROOT / "scripts/validate_findmy_runtime.py"
)
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)
CANARY = "SYNTHETIC_PRIVATE_MARKER_MUST_NOT_ESCAPE"


def archive(tmp_path, extra="", *, launch_worker=False):
    source, license_path = fixture_source(tmp_path, runtime=True)
    provider = (
        """from pathlib import Path
from custom_components.homecircle._vendor_findmy.runtime_marker import READY
assert READY is True
assert __name__=='custom_components.homecircle._findmy_runtime.provider'
assert Path.cwd().name=='work'
assert Path(__file__).resolve().is_relative_to(Path.cwd().parent/'package/homecircle')
class MacAnisetteProvider: pass
class Worker:
    def __init__(self): self.process=None
    async def close(self): pass
class BoundedHttpSession: pass
def new_identity(): return {}
"""
        + extra
    )
    write_member(
        source,
        "__init__.py",
        b"raise RuntimeError('integration_entrypoint_must_not_run')\n",
    )
    write_member(source, "_vendor_findmy/__init__.py", b"")
    write_member(source, "_vendor_findmy/runtime_marker.py", b"READY=True\n")
    write_member(source, "_findmy_runtime/provider.py", provider.encode())
    write_member(source, "_findmy_runtime/worker.py", b"class Engine: pass\n")
    write_member(
        source,
        "_findmy_runtime/bootstrap.py",
        b"DMG_URL='https://secure-appldnld.apple.com/fixture'\nasync def ensure_library(path): raise RuntimeError('explicit_live_mode_not_run')\n",
    )
    if launch_worker:
        provider += """
import asyncio, json, sys
class Worker:
    def __init__(self): self.process=None
    async def open(self, library, identity, stores):
        self.process=await asyncio.create_subprocess_exec(
            sys.executable,'-B',str(Path(__file__).with_name('worker.py')),
            stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL)
        return json.loads(await self.process.stdout.readline())
    async def close(self):
        if self.process is not None:
            if self.process.returncode is None: self.process.kill()
            await self.process.wait()
            self.process=None
"""
        write_member(source, "_findmy_runtime/provider.py", provider.encode())
        write_member(
            source,
            "_findmy_runtime/worker.py",
            (
                "class Engine: pass\n"
                "if __name__=='__main__':\n"
                " import sys\n"
                f" print({CANARY!r},file=sys.stderr)\n"
                " print('{\"provisioned\":false}',flush=True)\n"
            ).encode(),
        )
        write_member(
            source,
            "_findmy_runtime/bootstrap.py",
            (
                "DMG_URL='https://secure-appldnld.apple.com/fixture'\n"
                f"LIBRARY_SHA256='{hashlib.sha256(b'fixture').hexdigest()}'\n"
                "async def ensure_library(path):\n"
                " path.parent.mkdir(parents=True,exist_ok=True)\n"
                " path.write_bytes(b'fixture')\n"
                " return path\n"
            ).encode(),
        )
    payload = build.collect_payload(source, license_path)
    path, _ = build.write_archive(payload, tmp_path / "release")
    return path, path.with_name("inventory.json")


def test_default_uses_validated_zip_and_fresh_packaged_imports(tmp_path):
    path, inventory = archive(tmp_path)
    result = subject.run_validation(path, inventory=inventory)
    assert result["outcome"] == "ready" and result["mode"] == "readiness"
    assert result["package_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert (
        result["packaged_imports"]
        and result["emulator_imports"]
        and result["isolated_cwd"]
        and result["cleanup_ok"]
    )
    assert (
        result["public_download_requests"]
        == result["provisioning_requests"]
        == result["worker_children"]
        == result["network_attempts_blocked"]
        == 0
    )
    assert result["owner_data_read"] is result["locations_accessed"] is False
    assert subject.validate(result) == result


def test_actual_marker_worker_can_redirect_stderr_to_devnull(tmp_path):
    path, inventory = archive(tmp_path, launch_worker=True)
    result = subject.run_validation(path, mode="acquire", inventory=inventory)
    assert result["outcome"] == "ready" and result["phase"] == "complete"
    assert result["library_verified"] and result["cold_worker_ready"]
    assert result["worker_children"] == 1 and result["cleanup_ok"]
    assert result["public_download_requests"] == result["provisioning_requests"] == 0
    assert result["network_attempts_blocked"] == 0
    assert CANARY not in json.dumps(result)


def diagnostics(**updates):
    value = {
        "schema": 1,
        "stage": "finish_native",
        "request_count": 3,
        "last_http": 200,
        "last_apple_code": 0,
        "last_apple_hsc": 200,
        "failure": "native_unavailable",
    }
    value.update(updates)
    return value


@pytest.mark.parametrize("hostile", [False, True])
def test_provider_failure_projects_before_close_without_exception_text(
    tmp_path, hostile
):
    snapshot = diagnostics(stage="initialize", request_count=0)
    if hostile:
        snapshot["private"] = CANARY
    path, inventory = archive(
        tmp_path,
        "\nclass MacAnisetteProvider:\n"
        f"    def __init__(self,**kwargs): self.diagnostic={snapshot!r}\n"
        f"    async def _get_ani(self): raise RuntimeError({CANARY!r})\n"
        "    def safe_diagnostics(self): return dict(self.diagnostic)\n"
        "    async def close(self): self.diagnostic.clear()\n",
        launch_worker=True,
    )
    result = subject.run_validation(path, mode="provision", inventory=inventory)
    assert result["outcome"] == "unavailable" and result["phase"] == "provision"
    assert result["runtime_stage"] == ("not_observed" if hostile else "initialize")
    assert result["runtime_failure"] == (None if hostile else "native_unavailable")
    assert result["last_provision_http"] == (None if hostile else 200)
    assert result["last_provision_apple_code"] == (None if hostile else 0)
    assert result["last_provision_hsc"] == (None if hostile else 200)
    assert result["cleanup_ok"] and result["network_attempts_blocked"] == 0
    assert result["provisioning_requests"] == 0
    assert CANARY not in json.dumps(result)


@pytest.mark.parametrize(
    "updates",
    [
        {"private": CANARY},
        {"schema": True},
        {"stage": CANARY},
        {"request_count": True},
        {"request_count": 4},
        {"last_http": True},
        {"last_http": 99},
        {"last_http": 600},
        {"last_apple_code": -1000001},
        {"last_apple_code": 1000001},
        {"last_apple_code": CANARY},
        {"last_apple_hsc": True},
        {"last_apple_hsc": -1000001},
        {"last_apple_hsc": 1000001},
        {"failure": CANARY},
        {"failure": {}},
    ],
)
def test_provider_diagnostic_contract_rejects_unknown_and_unbounded_fields(updates):
    with pytest.raises(ValueError, match="runtime_receipt_refused"):
        subject._runtime_projection(diagnostics(**updates))


@pytest.mark.parametrize(
    "http,code,hsc",
    [(None, None, None), (100, -1000000, -1000000), (599, 1000000, 1000000)],
)
def test_nullable_diagnostic_numbers_have_strict_inclusive_bounds(http, code, hsc):
    projected = subject._runtime_projection(
        diagnostics(last_http=http, last_apple_code=code, last_apple_hsc=hsc)
    )
    result = subject.empty("provision") | projected
    assert subject.validate(result) == result


def test_unobserved_runtime_cannot_claim_apple_status():
    result = subject.empty()
    result["last_provision_http"] = 200
    with pytest.raises(ValueError, match="runtime_receipt_refused"):
        subject.validate(result)


@pytest.mark.parametrize(
    "extra",
    [
        "raise RuntimeError('" + CANARY + "')\n",
        "import importlib\nimportlib.import_module(__package__+'.module_missing_from_zip')\n",
        "__file__='/unpackaged/location/provider.py'\n",
        "Path(__file__).write_text('" + CANARY + "')\n",
    ],
)
def test_broken_or_unisolated_package_is_unavailable_without_private_output(
    tmp_path, extra
):
    path, _ = archive(tmp_path, extra)
    result = subject.run_validation(path)
    assert result["outcome"] == "unavailable" and result["phase"] == "imports"
    assert CANARY not in json.dumps(result)
    assert result["public_download_requests"] == result["provisioning_requests"] == 0


def test_packaged_network_attempt_is_blocked_before_dns(tmp_path):
    path, _ = archive(
        tmp_path, "import socket\nsocket.create_connection(('example.invalid',443))\n"
    )
    result = subject.run_validation(path)
    assert (
        result["outcome"] == "unavailable" and result["network_attempts_blocked"] == 1
    )
    assert result["public_download_requests"] == result["provisioning_requests"] == 0


def test_external_private_fixture_cannot_be_read(tmp_path):
    private = tmp_path / "unrelated-private-fixture"
    private.write_text(CANARY)
    path, _ = archive(
        tmp_path / "builder", "Path(" + repr(str(private)) + ").read_bytes()\n"
    )
    result = subject.run_validation(path)
    assert result["outcome"] == "unavailable" and result["owner_data_read"] is False
    assert CANARY not in json.dumps(result) and private.read_text() == CANARY


def test_invalid_archive_is_refused_before_child_creation(monkeypatch, tmp_path):
    path = manual_archive(tmp_path / "bad.zip", {"../escape.py": CANARY.encode()})
    monkeypatch.setattr(
        subject, "_capture", lambda *_: pytest.fail("child must not start")
    )
    assert subject.run_validation(path) == subject.empty()


@pytest.mark.parametrize("mode", ["acquire", "provision"])
def test_explicit_live_modes_reach_only_packaged_stub_not_real_download(tmp_path, mode):
    path, _ = archive(tmp_path)
    result = subject.run_validation(path, mode=mode)
    assert (
        result["mode"] == mode
        and result["outcome"] == "unavailable"
        and result["phase"] == "library"
    )
    assert (
        result["packaged_imports"]
        and result["public_download_requests"] == result["provisioning_requests"] == 0
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("private", CANARY),
        ("package_members", True),
        ("outcome", {}),
        ("phase", CANARY),
        ("owner_data_read", True),
        ("locations_accessed", True),
        ("public_download_requests", 2),
        ("worker_children", 9),
        ("account_requests", 1),
    ],
)
def test_receipt_rejects_hostile_fields_and_impossible_counts(field, value):
    result = subject.empty()
    result[field] = value
    with pytest.raises(ValueError):
        subject.validate(result)


@pytest.mark.parametrize(
    "flag,mode",
    [
        (None, "readiness"),
        ("--acquire-runtime", "acquire"),
        ("--provision-anonymous", "provision"),
    ],
)
def test_cli_modes_require_explicit_flags_without_running_them(
    monkeypatch, capsys, flag, mode
):
    seen = []

    def run(path, **options):
        seen.append(options)
        return subject.empty(options["mode"])

    monkeypatch.setattr(subject, "run_validation", run)
    monkeypatch.setattr(
        sys, "argv", ["validate_findmy_runtime.py", *([flag] if flag else [])]
    )
    with pytest.raises(SystemExit) as stopped:
        subject.main()
    assert stopped.value.code == 1
    result = json.loads(capsys.readouterr().out)
    assert result["mode"] == mode and seen == [{"mode": mode, "inventory": None}]


def test_missing_archive_prints_safe_failure_and_exits_nonzero(tmp_path):
    child = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(ROOT / "scripts/validate_findmy_runtime.py"),
            "--archive",
            str(tmp_path / "missing.zip"),
        ],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert child.returncode == 1 and child.stderr == b""
    result = json.loads(child.stdout)
    assert result == subject.empty()


def test_ready_public_cli_exits_normally(monkeypatch, capsys):
    monkeypatch.setattr(
        subject,
        "run_validation",
        lambda *args, **kwargs: subject.empty() | {"outcome": "ready"},
    )
    monkeypatch.setattr(sys, "argv", ["validate_findmy_runtime.py"])
    subject.main()
    assert json.loads(capsys.readouterr().out)["outcome"] == "ready"


def test_child_output_is_bounded_and_never_forwarded(tmp_path):
    with pytest.raises(ValueError, match="runtime_probe_output_refused"):
        subject._capture(
            [sys.executable, "-I", "-B", "-c", "print('" + CANARY + "'*2000)"],
            tmp_path,
            5,
        )


def test_child_duplicate_receipt_keys_are_refused(tmp_path):
    with pytest.raises(ValueError, match="runtime_receipt_refused"):
        subject._capture(
            [sys.executable, "-I", "-B", "-c", 'print(\'{"schema":1,"schema":1}\')'],
            tmp_path,
            5,
        )


def test_parent_timeout_kills_owned_child(tmp_path):
    with pytest.raises(ValueError, match="runtime_probe_timeout"):
        subject._capture(
            [sys.executable, "-I", "-B", "-c", "import time;time.sleep(30)"],
            tmp_path,
            0.05,
        )
