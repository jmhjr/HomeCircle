"""Acquire one pinned Apple runtime privately; no archive extraction or identity.

The byte ranges below belong only to Apple's hash-pinned iTunes 12.8.3 DMG.
They select CoreADI.pkg/Payload, its regular framework member and the x86_64
slice. Each layer is independently hash checked; no archive paths are written.
No Apple library or provisioning state is distributed with HomeCircle.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
from pathlib import Path
import secrets
import ssl
import stat
import threading
import time
import urllib.request
import zlib

DMG_URL = "https://secure-appldnld.apple.com/itunes12/041-56365-20210413-79A5AC6D-6B0A-46EC-B399-5A381183E3BE/iTunes12.8.3.dmg"
DMG_BYTES = 291523996
DMG_SHA256 = "dd08b9967db3e5847955fa168ce880303abf5f36de12abb2061e7ef1a25be214"
PAYLOAD_OFFSET = 184678769
PAYLOAD_BYTES = 3471595
PAYLOAD_SHA256 = "8a6c068c95036326eb2d2885fa60912ed0f7229d0939ae92934a70a3bb6cf025"
CPIO_BYTES = 5105664
CPIO_SHA256 = "cfcc5496eba695bef8eddb00590f2bf8df36f0daddd2784dd81c6efd39928b8c"
FRAMEWORK_OFFSET = 1777873
FRAMEWORK_BYTES = 3327248
FRAMEWORK_SHA256 = "33ea5415997a50182fa0eef62c520ef2faa577ce84945a1afa24b2289ec2e085"
SLICE_OFFSET = 1650688
LIBRARY_BYTES = 1676560
LIBRARY_SHA256 = "2eafc3c79c7f41a8afbfbeaaf23ee5dab5ad5bda55ec8e54dbc0ddf1d20ce630"
DOWNLOAD_SECONDS = 600
READ_SECONDS = 15
LIBRARY_NAME = "CoreADI.x86_64"
_LOCK = threading.Lock()


class BootstrapUnavailable(RuntimeError):
    """Fixed failure only; never a URL, path, response or exception text."""


def _refuse():
    raise BootstrapUnavailable("identity_runtime_unavailable") from None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _refuse()


def _opener():
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        _NoRedirect(),
    )


def _extract(payload):
    if (
        type(payload) is not bytes
        or len(payload) != PAYLOAD_BYTES
        or hashlib.sha256(payload).hexdigest() != PAYLOAD_SHA256
    ):
        _refuse()
    try:
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
        archive = decoder.decompress(payload, CPIO_BYTES + 1)
    except zlib.error:
        _refuse()
    if (
        len(archive) != CPIO_BYTES
        or not decoder.eof
        or decoder.unused_data
        or decoder.unconsumed_tail
        or hashlib.sha256(archive).hexdigest() != CPIO_SHA256
    ):
        _refuse()
    framework = archive[FRAMEWORK_OFFSET : FRAMEWORK_OFFSET + FRAMEWORK_BYTES]
    if (
        len(framework) != FRAMEWORK_BYTES
        or hashlib.sha256(framework).hexdigest() != FRAMEWORK_SHA256
    ):
        _refuse()
    library = framework[SLICE_OFFSET : SLICE_OFFSET + LIBRARY_BYTES]
    if (
        len(library) != LIBRARY_BYTES
        or hashlib.sha256(library).hexdigest() != LIBRARY_SHA256
    ):
        _refuse()
    return library


def _download():
    """One public request: exact range, or exact complete-image fallback."""
    request = urllib.request.Request(
        DMG_URL,
        headers={
            "Range": f"bytes={PAYLOAD_OFFSET}-{PAYLOAD_OFFSET + PAYLOAD_BYTES - 1}",
            "Accept-Encoding": "identity",
            "User-Agent": "HomeCircle runtime bootstrap",
        },
    )
    started = time.monotonic()
    with _opener().open(request, timeout=READ_SECONDS) as response:
        status = response.status
        if response.geturl() != DMG_URL or response.getheader(
            "Content-Encoding", "identity"
        ).strip().lower() not in {"identity", ""}:
            _refuse()
        if status == 206:
            maximum, offset = PAYLOAD_BYTES, 0
            expected = f"bytes {PAYLOAD_OFFSET}-{PAYLOAD_OFFSET + PAYLOAD_BYTES - 1}/{DMG_BYTES}"
            if response.getheader("Content-Range") != expected:
                _refuse()
        elif status == 200:
            maximum, offset = DMG_BYTES, PAYLOAD_OFFSET
            if response.getheader("Content-Range") is not None:
                _refuse()
        else:
            _refuse()
        length = response.getheader("Content-Length")
        if length is not None and length != str(maximum):
            _refuse()
        digest, payload, total = hashlib.sha256(), bytearray(), 0
        while True:
            if time.monotonic() - started >= DOWNLOAD_SECONDS:
                _refuse()
            piece = response.read(min(65536, maximum + 1 - total))
            if time.monotonic() - started >= DOWNLOAD_SECONDS:
                _refuse()
            if type(piece) is not bytes:
                _refuse()
            if not piece:
                break
            end = total + len(piece)
            if end > maximum:
                _refuse()
            digest.update(piece)
            first, last = max(total, offset), min(end, offset + PAYLOAD_BYTES)
            if first < last:
                payload.extend(piece[first - total : last - total])
            total = end
        if total != maximum or status == 200 and digest.hexdigest() != DMG_SHA256:
            _refuse()
        return _extract(bytes(payload))


def _cached(directory):
    try:
        descriptor = os.open(
            LIBRARY_NAME, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory
        )
    except FileNotFoundError:
        return False
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size != LIBRARY_BYTES:
            return False
        with os.fdopen(descriptor, "rb", closefd=False) as source:
            raw = source.read(LIBRARY_BYTES + 1)
        after = os.fstat(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            _refuse()
        return (
            len(raw) == LIBRARY_BYTES
            and hashlib.sha256(raw).hexdigest() == LIBRARY_SHA256
        )
    finally:
        os.close(descriptor)


def _ensure(libraries):
    """Serialize cache initialization, never read or replace the legacy file."""
    if not isinstance(libraries, Path) or not libraries.is_absolute():
        _refuse()
    with _LOCK:
        libraries.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        base = libraries.parent.resolve(strict=True)
        parent = os.open(base, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        directory = None
        temporary = None
        try:
            try:
                os.mkdir("coreadi", mode=0o700, dir_fd=parent)
            except FileExistsError:
                pass
            directory = os.open(
                "coreadi", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent
            )
            target = base / "coreadi" / LIBRARY_NAME
            if _cached(directory):
                return target
            library = _download()
            if (
                type(library) is not bytes
                or len(library) != LIBRARY_BYTES
                or hashlib.sha256(library).hexdigest() != LIBRARY_SHA256
            ):
                _refuse()
            candidate = ".runtime-" + secrets.token_hex(16)
            descriptor = os.open(
                candidate,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory,
            )
            temporary = candidate
            with os.fdopen(descriptor, "wb") as output:
                output.write(library)
                output.flush()
                os.fsync(output.fileno())
            os.replace(
                temporary, LIBRARY_NAME, src_dir_fd=directory, dst_dir_fd=directory
            )
            temporary = None
            os.fsync(directory)
            if not _cached(directory):
                _refuse()
            return target
        finally:
            if temporary is not None and directory is not None:
                os.unlink(temporary, dir_fd=directory)
            if directory is not None:
                os.close(directory)
            os.close(parent)


async def ensure_library(libraries: Path) -> Path:
    """Complete a bounded cache operation even if its caller is cancelled."""

    async def job():
        # HA's shield wrapper logs exceptions from a future cancelled by its
        # caller. Consume private exception objects before this task completes.
        try:
            return True, await asyncio.to_thread(_ensure, libraries)
        except Exception:
            return False, None

    task = asyncio.create_task(job())
    try:
        success, path = await asyncio.shield(task)
    except asyncio.CancelledError:
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        if task.done() and not task.cancelled():
            task.exception()
        raise
    if not success:
        _refuse()
    return path
