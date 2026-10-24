"""Synthetic worker trust boundaries; no Apple library, account, or network."""

import asyncio
import base64
import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import sys
import threading

import pytest

from custom_components.homecircle._findmy_runtime import provider, worker

PUBLIC_BYTES = b"synthetic-public-runtime"


@pytest.fixture
def library(tmp_path, monkeypatch):
    path = tmp_path / "public-runtime"
    path.write_bytes(PUBLIC_BYTES)
    monkeypatch.setattr(worker, "LIBRARY_BYTES", len(PUBLIC_BYTES))
    monkeypatch.setattr(
        worker, "LIBRARY_SHA256", hashlib.sha256(PUBLIC_BYTES).hexdigest()
    )
    return path


def test_verified_bytes_are_loaded_after_pathname_replacement(library, monkeypatch):
    original = worker.verified_library
    consumed = []

    def replace_after_verification(path):
        raw = original(path)
        Path(path).unlink()
        Path(path).write_bytes(b"untrusted replacement")
        return raw

    class CoreADI:
        def __init__(self, path=None, *, image_bytes=None):
            consumed.append(
                image_bytes if image_bytes is not None else Path(path).read_bytes()
            )
            self.stubs = SimpleNamespace(files={})

        def initialize(self):
            return SimpleNamespace(rc=0, ret=0, outputs={})

    monkeypatch.setattr(worker, "verified_library", replace_after_verification)
    monkeypatch.setitem(sys.modules, "adi_run", SimpleNamespace(CoreADI=CoreADI))
    monkeypatch.setattr(sys, "path", list(sys.path))
    engine = worker.Engine(str(library), "a" * 32, {})
    assert engine.engine.stubs.hostuuid == b"\xaa" * 16
    assert consumed == [PUBLIC_BYTES]
    assert library.read_bytes() == b"untrusted replacement"


@pytest.mark.parametrize("fault", ["symlink", "directory", "oversize", "corrupt"])
def test_library_refusal_precedes_emulator_or_dependency_import(
    library, monkeypatch, fault
):
    if fault == "symlink":
        saved = library.with_name("real-runtime")
        library.rename(saved)
        library.symlink_to(saved)
    elif fault == "directory":
        library.unlink()
        library.mkdir()
    elif fault == "oversize":
        library.write_bytes(PUBLIC_BYTES + b"excess")
    else:
        library.write_bytes(b"x" * len(PUBLIC_BYTES))
    if fault == "oversize":
        monkeypatch.setattr(
            worker.os,
            "fdopen",
            lambda *args, **kwargs: pytest.fail("Oversize library was read"),
        )
    monkeypatch.setattr(
        worker,
        "load_unicorn",
        lambda *args: pytest.fail("Unverified library reached emulator imports"),
    )
    with pytest.raises((OSError, ValueError)):
        worker.Engine(str(library), "a" * 32, {}, unicorn_package="/synthetic/unicorn")


def test_library_mutation_during_read_is_refused(library, monkeypatch):
    original = worker.os.fstat
    calls = []

    def fstat(descriptor):
        value = original(descriptor)
        calls.append(value)
        if len(calls) == 2:
            return SimpleNamespace(
                **{
                    key: getattr(value, key) + int(key == "st_ctime_ns")
                    for key in (
                        "st_dev",
                        "st_ino",
                        "st_size",
                        "st_mtime_ns",
                        "st_ctime_ns",
                    )
                }
            )
        return value

    monkeypatch.setattr(worker.os, "fstat", fstat)
    with pytest.raises(ValueError, match="^native_library_refused$"):
        worker.verified_library(str(library))
    assert len(calls) == 2


@pytest.mark.parametrize(
    "package", [None, "relative/unicorn", "/synthetic/other", "x" * 4097]
)
def test_explicit_dependency_location_is_bounded_absolute_and_package_specific(package):
    with pytest.raises(ValueError, match="^native_dependency_refused$"):
        worker.load_unicorn(package)


async def test_missing_parent_dependency_fails_before_child_spawn(monkeypatch):
    monkeypatch.setattr(provider.importlib.util, "find_spec", lambda name: None)
    spawn = AsyncMock()
    monkeypatch.setattr(provider.asyncio, "create_subprocess_exec", spawn)
    instance = provider.Worker()
    with pytest.raises(
        provider.IdentityUnavailable, match="^identity_worker_unavailable$"
    ):
        await instance.open("synthetic-runtime", {"host_uuid": "a" * 32}, {})
    spawn.assert_not_awaited()
    assert instance.process is None
    await instance.close()


async def test_worker_closed_during_dependency_lookup_never_spawns(monkeypatch):
    entered, release = threading.Event(), threading.Event()

    def resolve():
        entered.set()
        assert release.wait(3)
        return "/synthetic/unicorn"

    monkeypatch.setattr(provider, "_unicorn_package_directory", resolve)
    spawn = AsyncMock()
    monkeypatch.setattr(provider.asyncio, "create_subprocess_exec", spawn)
    instance = provider.Worker()
    opening = asyncio.create_task(
        instance.open("synthetic-runtime", {"host_uuid": "a" * 32}, {})
    )
    assert await asyncio.to_thread(entered.wait, 2)
    await instance.close()
    release.set()
    with pytest.raises(
        provider.IdentityUnavailable, match="^identity_worker_unavailable$"
    ):
        await opening
    spawn.assert_not_awaited()
    assert instance.process is None and instance._spawn is None


async def test_cancelled_failed_spawn_is_consumed_without_private_log(
    monkeypatch, caplog
):
    entered, release = asyncio.Event(), asyncio.Event()

    async def spawn(*args, **kwargs):
        entered.set()
        await release.wait()
        raise OSError("synthetic private spawn canary")

    monkeypatch.setattr(provider.asyncio, "create_subprocess_exec", spawn)
    instance = provider.Worker()
    opening = asyncio.create_task(
        instance.open("synthetic-runtime", {"host_uuid": "a" * 32}, {})
    )
    await entered.wait()
    opening.cancel()
    await asyncio.sleep(0)
    assert not opening.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await opening
    await asyncio.sleep(0)
    assert instance.process is None and instance._spawn is None
    assert "synthetic private spawn canary" not in caplog.text


async def test_cancelled_failed_wait_retains_retry_handle_without_private_log(caplog):
    entered, release = asyncio.Event(), asyncio.Event()

    async def wait():
        entered.set()
        await release.wait()
        raise OSError("synthetic private wait canary")

    child = SimpleNamespace(returncode=None, kill=lambda: None, wait=wait)
    instance = provider.Worker()
    instance.process = child
    closing = asyncio.create_task(instance.close())
    await entered.wait()
    closing.cancel()
    await asyncio.sleep(0)
    closing.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await closing
    await asyncio.sleep(0)
    assert instance.process is child
    assert "synthetic private wait canary" not in caplog.text
    child.wait = AsyncMock(return_value=-9)
    await instance.close()
    assert instance.process is None


async def test_cancelled_failed_initialize_cleanup_never_logs_private_error(
    tmp_path, monkeypatch, caplog
):
    entered, release = asyncio.Event(), asyncio.Event()

    async def transport_close():
        entered.set()
        await release.wait()
        raise OSError("synthetic private transport canary")

    child = SimpleNamespace(
        open=AsyncMock(side_effect=ValueError("synthetic initial failure")),
        close=AsyncMock(),
    )
    transport = SimpleNamespace(close=transport_close)
    monkeypatch.setattr(provider, "Worker", lambda: child)
    monkeypatch.setattr(provider, "BoundedHttpSession", lambda **kwargs: transport)
    instance = provider.MacAnisetteProvider(libs_path=tmp_path / "synthetic-cache")
    monkeypatch.setattr(
        instance, "_library", AsyncMock(return_value=tmp_path / "synthetic-runtime")
    )
    opening = asyncio.create_task(instance._get_ani())
    await entered.wait()
    opening.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await opening
    await asyncio.sleep(0)
    child.close.assert_awaited_once()
    assert instance._worker is None
    assert "synthetic private transport canary" not in caplog.text
    await instance.close()


def provisioned_provider(tmp_path):
    identity = provider.new_identity()
    identity["routing"] = 1
    instance = provider.MacAnisetteProvider(
        libs_path=tmp_path / "synthetic-cache",
        state={
            "identity": identity,
            "store": {"synthetic": base64.b64encode(b"synthetic-machine").decode()},
        },
    )
    instance._cache = {"otp": "synthetic-otp", "mid": "synthetic-mid"}
    instance._machine_id, instance._cache_window = "synthetic-mid", 1
    return instance


async def test_provider_failed_close_clears_data_but_retains_child_for_retry(tmp_path):
    instance = provisioned_provider(tmp_path)
    child = SimpleNamespace(
        close=AsyncMock(side_effect=OSError("synthetic close failure"))
    )
    instance._worker = child
    with pytest.raises(OSError, match="synthetic close failure"):
        await instance.close()
    assert instance._worker is child
    assert instance._cache is instance._machine_id is instance._cache_window is None
    assert instance._machine_state is None and instance._machine_identity == {}
    with pytest.raises(
        provider.IdentityUnavailable, match="identity_serialization_refused"
    ):
        instance.to_json()
    child.close.side_effect = None
    await instance.close()
    assert instance._worker is None and child.close.await_count == 2


async def test_provider_repeated_cancel_drains_data_cleanup_after_close_failure(
    tmp_path,
):
    instance = provisioned_provider(tmp_path)
    entered = asyncio.Event()

    async def failed_close():
        entered.set()
        raise OSError("synthetic close failure")

    child = SimpleNamespace(close=failed_close)
    instance._worker = child
    await instance._lock.acquire()
    closing = asyncio.create_task(instance.close())
    await entered.wait()
    closing.cancel()
    await asyncio.sleep(0)
    closing.cancel()
    await asyncio.sleep(0)
    assert not closing.done()
    instance._lock.release()
    with pytest.raises(asyncio.CancelledError):
        await closing
    assert instance._worker is child
    assert instance._cache is instance._machine_state is instance._machine_id is None
    assert instance._machine_identity == {}
    child.close = AsyncMock()
    await instance.close()


async def test_child_uses_exact_parent_package_from_core_deps_layout(
    tmp_path, monkeypatch, library
):
    runtime = tmp_path / "installed_component" / "_findmy_runtime"
    emulator = runtime / "emulator"
    emulator.mkdir(parents=True)
    source = Path(worker.__file__).read_text()
    source = source.replace(
        'LIBRARY_SHA256 = "2eafc3c79c7f41a8afbfbeaaf23ee5dab5ad5bda55ec8e54dbc0ddf1d20ce630"',
        f'LIBRARY_SHA256 = "{hashlib.sha256(PUBLIC_BYTES).hexdigest()}"',
    ).replace("LIBRARY_BYTES = 1676560", f"LIBRARY_BYTES = {len(PUBLIC_BYTES)}")
    (runtime / "worker.py").write_text(source)
    package = (
        tmp_path
        / "config"
        / "deps"
        / "lib"
        / "python3.14"
        / "site-packages"
        / "unicorn"
    )
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("from .nested import ORIGIN\n")
    (package / "nested.py").write_text("ORIGIN = 'synthetic-core-deps'\n")
    (emulator / "adi_run.py").write_text("""
from types import SimpleNamespace
import unicorn
assert unicorn.ORIGIN == 'synthetic-core-deps'
class CoreADI:
    def __init__(self, *, image_bytes):
        assert image_bytes == b'synthetic-public-runtime'
        self.stubs = SimpleNamespace(files={})
    def initialize(self):
        return SimpleNamespace(rc=0, ret=0, outputs={})
    def is_machine_provisioned(self, value):
        assert value == -2
        return SimpleNamespace(rc=0, ret=-45061, outputs={})
""")
    # Simulate HA's parent-only dependency lookup; this directory is never put
    # into PYTHONPATH or the child's ordinary sys.path.
    spec = importlib.util.spec_from_file_location(
        "unicorn", package / "__init__.py", submodule_search_locations=[str(package)]
    )
    monkeypatch.setattr(provider.importlib.util, "find_spec", lambda name: spec)
    monkeypatch.setattr(provider, "__file__", str(runtime / "provider.py"))
    before = list(sys.path)
    instance = provider.Worker()
    try:
        assert await instance.open(library, {"host_uuid": "a" * 32}, {}) == {
            "provisioned": False
        }
        assert list(sys.path) == before
        assert str(package.parent) not in sys.path
    finally:
        await instance.close()
    assert instance.process is None and instance._spawn is None
