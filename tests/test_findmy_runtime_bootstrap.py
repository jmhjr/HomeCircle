"""Pinned public-library acquisition; synthetic transport and no owner state."""

import asyncio
import gzip
import hashlib
import importlib.util
import io
from pathlib import Path
import threading
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "runtime_bootstrap_test",
    ROOT / "custom_components/homecircle/_findmy_runtime/bootstrap.py",
)
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)
CANARY = "SYNTHETIC_LEGACY_OR_FAILURE_VALUE"


@pytest.fixture
def artifact(monkeypatch):
    library = b"synthetic-public-library"
    framework = b"fat-header" + library + b"fat-tail"
    cpio = b"archive-header" + framework + b"archive-tail"
    payload = gzip.compress(cpio)
    dmg = b"disk-header" + payload + b"disk-tail"
    for name, value in {
        "DMG_BYTES": len(dmg),
        "DMG_SHA256": hashlib.sha256(dmg).hexdigest(),
        "PAYLOAD_OFFSET": len(b"disk-header"),
        "PAYLOAD_BYTES": len(payload),
        "PAYLOAD_SHA256": hashlib.sha256(payload).hexdigest(),
        "CPIO_BYTES": len(cpio),
        "CPIO_SHA256": hashlib.sha256(cpio).hexdigest(),
        "FRAMEWORK_OFFSET": len(b"archive-header"),
        "FRAMEWORK_BYTES": len(framework),
        "FRAMEWORK_SHA256": hashlib.sha256(framework).hexdigest(),
        "SLICE_OFFSET": len(b"fat-header"),
        "LIBRARY_BYTES": len(library),
        "LIBRARY_SHA256": hashlib.sha256(library).hexdigest(),
    }.items():
        monkeypatch.setattr(subject, name, value)
    return library, payload, dmg


class Response:
    def __init__(self, raw, *, status=206, headers=None, url=None):
        self.status, self.headers, self.url = (
            status,
            headers or {},
            url or subject.DMG_URL,
        )
        self.stream, self.closed = io.BytesIO(raw), False

    def getheader(self, name, default=None):
        return self.headers.get(name, default)

    def geturl(self):
        return self.url

    def read(self, limit):
        assert 1 <= limit <= 65536
        return self.stream.read(limit)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.closed = True


def install_response(monkeypatch, response):
    seen = []

    class Opener:
        def open(self, request, timeout):
            assert (
                request.full_url == subject.DMG_URL and timeout == subject.READ_SECONDS
            )
            headers = {name.lower(): value for name, value in request.header_items()}
            assert headers == {
                "range": f"bytes={subject.PAYLOAD_OFFSET}-{subject.PAYLOAD_OFFSET + subject.PAYLOAD_BYTES - 1}",
                "accept-encoding": "identity",
                "user-agent": "HomeCircle runtime bootstrap",
            }
            assert not seen
            seen.append(True)
            return response

    monkeypatch.setattr(subject, "_opener", Opener)
    return seen


def range_headers():
    return {
        "Content-Range": f"bytes {subject.PAYLOAD_OFFSET}-{subject.PAYLOAD_OFFSET + subject.PAYLOAD_BYTES - 1}/{subject.DMG_BYTES}",
        "Content-Length": str(subject.PAYLOAD_BYTES),
    }


@pytest.mark.parametrize("status", [200, 206])
def test_exact_range_or_full_fallback_are_verified_once(monkeypatch, artifact, status):
    library, payload, dmg = artifact
    response = Response(
        payload if status == 206 else dmg,
        status=status,
        headers=range_headers() if status == 206 else {"Content-Length": str(len(dmg))},
    )
    seen = install_response(monkeypatch, response)
    assert subject._download() == library and seen == [True] and response.closed


@pytest.mark.parametrize("status", [301, 302, 400, 401, 403, 429, 500])
def test_http_refusal_never_retries(monkeypatch, artifact, status):
    response = Response(b"", status=status)
    seen = install_response(monkeypatch, response)
    with pytest.raises(
        subject.BootstrapUnavailable, match="^identity_runtime_unavailable$"
    ):
        subject._download()
    assert seen == [True] and response.closed


@pytest.mark.parametrize(
    "behavior",
    ["range", "length", "encoding", "url", "truncated", "oversize", "corrupt"],
)
def test_response_mismatch_is_refused_and_closed(monkeypatch, artifact, behavior):
    _, raw, _ = artifact
    headers = range_headers()
    url = None
    if behavior == "range":
        headers["Content-Range"] = "bytes 0-1/2"
    if behavior == "length":
        headers["Content-Length"] = "1"
    if behavior == "encoding":
        headers["Content-Encoding"] = "gzip"
    if behavior == "url":
        url = "https://untrusted.invalid/"
    if behavior == "truncated":
        raw = raw[:-1]
    if behavior == "oversize":
        raw += b"x"
    if behavior == "corrupt":
        raw = b"x" + raw[1:]
    response = Response(raw, headers=headers, url=url)
    install_response(monkeypatch, response)
    with pytest.raises(subject.BootstrapUnavailable):
        subject._download()
    assert response.closed


def test_full_fallback_hash_checks_bytes_outside_selected_payload(
    monkeypatch, artifact
):
    _, _, raw = artifact
    response = Response(b"x" + raw[1:], status=200)
    install_response(monkeypatch, response)
    with pytest.raises(subject.BootstrapUnavailable):
        subject._download()
    assert response.closed


@pytest.mark.parametrize(
    "field", ["PAYLOAD_SHA256", "CPIO_SHA256", "FRAMEWORK_SHA256", "LIBRARY_SHA256"]
)
def test_each_extraction_layer_requires_its_exact_digest(monkeypatch, artifact, field):
    monkeypatch.setattr(subject, field, "0" * 64)
    with pytest.raises(subject.BootstrapUnavailable):
        subject._extract(artifact[1])


@pytest.mark.parametrize("mode", ["damaged", "trailing", "second_member", "expansion"])
def test_gzip_is_bounded_and_requires_one_complete_member(monkeypatch, artifact, mode):
    raw = artifact[1]
    if mode == "damaged":
        raw = b"broken"
    if mode == "trailing":
        raw += b"trailing"
    if mode == "second_member":
        raw += gzip.compress(b"other")
    if mode == "expansion":
        raw = gzip.compress(b"x" * (subject.CPIO_BYTES + 1))
    monkeypatch.setattr(subject, "PAYLOAD_BYTES", len(raw))
    monkeypatch.setattr(subject, "PAYLOAD_SHA256", hashlib.sha256(raw).hexdigest())
    with pytest.raises(subject.BootstrapUnavailable):
        subject._extract(raw)


def test_transport_has_verified_tls_no_proxies_or_redirects(monkeypatch):
    captured = []
    monkeypatch.setattr(
        subject.urllib.request,
        "build_opener",
        lambda *handlers: captured.extend(handlers),
    )
    subject._opener()
    proxy, https, redirect = captured
    assert proxy.proxies == {}
    assert (
        https._context.check_hostname
        and https._context.verify_mode.name == "CERT_REQUIRED"
    )
    with pytest.raises(subject.BootstrapUnavailable):
        redirect.redirect_request(None, None, 302, None, None, "https://other.invalid/")


def test_download_deadline_is_checked_after_reads(monkeypatch, artifact):
    response = Response(artifact[1], headers=range_headers())
    install_response(monkeypatch, response)
    values = iter([0, 0, subject.DOWNLOAD_SECONDS])
    monkeypatch.setattr(
        subject, "time", SimpleNamespace(monotonic=lambda: next(values))
    )
    with pytest.raises(subject.BootstrapUnavailable):
        subject._download()
    assert response.closed


@pytest.mark.asyncio
async def test_cache_is_atomic_owner_only_and_legacy_state_is_untouched(
    monkeypatch, artifact, tmp_path
):
    old = tmp_path / "legacy-libraries.bin"
    old.write_text(CANARY)
    calls = []

    def download():
        calls.append(True)
        return artifact[0]

    monkeypatch.setattr(subject, "_download", download)
    result = await subject.ensure_library(old)
    assert result == tmp_path / "coreadi" / subject.LIBRARY_NAME
    assert result.read_bytes() == artifact[0] and result.stat().st_mode & 0o777 == 0o600
    assert result.parent.stat().st_mode & 0o777 == 0o700
    assert old.read_text() == CANARY and calls == [True]
    assert await subject.ensure_library(old) == result and calls == [True]
    assert sorted(p.name for p in result.parent.iterdir()) == [subject.LIBRARY_NAME]


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["directory", "library"])
async def test_cache_symlinks_are_refused_without_touching_targets(
    monkeypatch, artifact, tmp_path, kind
):
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / subject.LIBRARY_NAME
    target.write_bytes(artifact[0])
    cache = tmp_path / "coreadi"
    if kind == "directory":
        cache.symlink_to(outside, target_is_directory=True)
    else:
        cache.mkdir()
        (cache / subject.LIBRARY_NAME).symlink_to(target)
    monkeypatch.setattr(subject, "_download", lambda: pytest.fail("network forbidden"))
    with pytest.raises(subject.BootstrapUnavailable):
        await subject.ensure_library(tmp_path / "legacy.bin")
    assert target.read_bytes() == artifact[0]


@pytest.mark.asyncio
async def test_failed_atomic_replace_keeps_previous_file_and_cleans_temp(
    monkeypatch, artifact, tmp_path
):
    cache = tmp_path / "coreadi"
    cache.mkdir()
    target = cache / subject.LIBRARY_NAME
    target.write_bytes(b"old-corrupt-cache")
    monkeypatch.setattr(subject, "_download", lambda: artifact[0])

    def fail(*args, **kwargs):
        raise OSError(CANARY)

    monkeypatch.setattr(subject.os, "replace", fail)
    with pytest.raises(
        subject.BootstrapUnavailable, match="^identity_runtime_unavailable$"
    ):
        await subject.ensure_library(tmp_path / "legacy.bin")
    assert target.read_bytes() == b"old-corrupt-cache" and list(cache.iterdir()) == [
        target
    ]


@pytest.mark.asyncio
async def test_concurrent_cache_initializers_download_once(
    monkeypatch, artifact, tmp_path
):
    started, release = threading.Event(), threading.Event()
    calls = []

    def download():
        calls.append(True)
        started.set()
        assert release.wait(5)
        return artifact[0]

    monkeypatch.setattr(subject, "_download", download)
    first = asyncio.create_task(subject.ensure_library(tmp_path / "legacy.bin"))
    assert await asyncio.to_thread(started.wait, 5)
    second = asyncio.create_task(subject.ensure_library(tmp_path / "legacy.bin"))
    release.set()
    assert (await first) == (await second) and calls == [True]


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [False, True])
async def test_double_cancel_waits_for_cache_job_and_preserves_cancel(
    monkeypatch, artifact, tmp_path, failure
):
    started, release, settled = threading.Event(), threading.Event(), threading.Event()

    def download():
        started.set()
        assert release.wait(5)
        settled.set()
        if failure:
            raise OSError(CANARY)
        return artifact[0]

    monkeypatch.setattr(subject, "_download", download)
    task = asyncio.create_task(subject.ensure_library(tmp_path / "legacy.bin"))
    assert await asyncio.to_thread(started.wait, 5)
    task.cancel()
    await asyncio.sleep(0)
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert settled.is_set()
    assert (tmp_path / "coreadi" / subject.LIBRARY_NAME).exists() is (not failure)


def test_retained_public_apple_dmg_fixed_ranges():
    dmg = ROOT / "work/findmy-replacement/native-control/iTunes12.8.3.dmg"
    if not dmg.exists():
        pytest.skip("Public Apple installer fixture is not retained")
    with dmg.open("rb") as source:
        assert hashlib.file_digest(source, "sha256").hexdigest() == subject.DMG_SHA256
        source.seek(subject.PAYLOAD_OFFSET)
        library = subject._extract(source.read(subject.PAYLOAD_BYTES))
    assert (
        len(library) == subject.LIBRARY_BYTES
        and hashlib.sha256(library).hexdigest() == subject.LIBRARY_SHA256
    )
