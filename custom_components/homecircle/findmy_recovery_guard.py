"""Durable local recovery submissions, independent of selected account vaults.

These counters describe only this installation's observations. They do not describe
or reset an Apple server allowance. No owner credential or recovery key is stored.
Each account has an independently retained cache witness. Ordinary Home Assistant
backups exclude that cache, so restored ledgers require explicit owner review.
Rolling back both the ledger and witness, as in a full VM snapshot, needs an
external anchor and is outside this local safeguard's protection.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from uuid import uuid4

_LIMIT = 3
_MAX_COUNT = 2**63 - 1
_IDENTITY = re.compile(r"[0-9a-f]{64}")
_TOKEN = re.compile(r"[0-9a-f]{32}")
_SERVICE = "homecircle_findmy_recovery_guard"


class RecoveryGuardError(RuntimeError):
    """A fixed, safe local recovery failure."""


class RecoveryGuardBlocked(RecoveryGuardError):
    """Local unresolved submissions or an active attempt prevent this action."""

    code = "recovery_guard_blocked"


class RecoveryGuardReviewRequired(RecoveryGuardBlocked):
    """The local ledger has no independently retained continuity witness."""

    code = "recovery_guard_review"


class RecoveryGuardStorageError(RecoveryGuardError):
    """Local guard storage cannot be read or durably updated safely."""

    code = "recovery_guard_storage"


def _identity(value):
    if not isinstance(value, str) or _IDENTITY.fullmatch(value) is None:
        raise ValueError("A validated authenticated account identity is required")
    return value


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Ambiguous local recovery storage")
        result[key] = value
    return result


async def _execute(function, *args, cleanup=None):
    """Drain filesystem work on cancellation before transferring lock ownership."""
    # HA may log a shielded task's later exception after outer cancellation,
    # even if it is subsequently retrieved. Shield a non-raising outcome instead.
    job = asyncio.gather(asyncio.to_thread(function, *args), return_exceptions=True)
    try:
        result = (await asyncio.shield(job))[0]
    except asyncio.CancelledError:
        while not job.done():
            try:
                await asyncio.shield(job)
            except asyncio.CancelledError:
                continue
        result = job.result()[0]
        if isinstance(result, BaseException):
            raise result
        if cleanup is not None:
            await _execute(cleanup, result)
        raise
    if isinstance(result, BaseException):
        raise result
    return result


class RecoveryGuard:
    """Serialize each account's unlock and reserve submissions before dispatch."""

    def __init__(self, root: Path, witness_root: Path | None = None):
        self.root = Path(os.path.abspath(root))
        self.witness_root = Path(os.path.abspath(
            witness_root if witness_root is not None
            else self.root.parent / f".{self.root.name}-continuity"
        ))
        if (
            self.root == self.witness_root
            or self.root in self.witness_root.parents
            or self.witness_root in self.root.parents
        ):
            raise ValueError("Independent local recovery storage is required")
        self._locks: dict[str, asyncio.Lock] = {}

    def _root_fd(self, path=None, *, create=True):
        """Walk directory descriptors without following links, including parents."""
        path = self.root if path is None else path
        private = {path}
        creatable = {path} if create else set()
        if (
            path.name == "recovery_guard"
            and path.parent.name == "homecircle_findmy"
        ):
            private.add(path.parent)
            if create:
                creatable.update((path.parent, path.parent.parent))
        current = Path(path.anchor)
        descriptor = os.open(current, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for part in path.parts[1:]:
                current /= part
                try:
                    child = os.open(
                        part,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                        dir_fd=descriptor,
                    )
                except FileNotFoundError:
                    if current not in creatable:
                        raise
                    try:
                        os.mkdir(part, 0o700, dir_fd=descriptor)
                        os.fsync(descriptor)
                    except FileExistsError:
                        pass
                    child = os.open(
                        part,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                        dir_fd=descriptor,
                    )
                os.close(descriptor)
                descriptor = child
                info = os.fstat(descriptor)
                if current in private and (
                    info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700
                ):
                    raise RecoveryGuardStorageError("Unsafe local recovery storage")
            return descriptor
        except BaseException:
            os.close(descriptor)
            raise

    @staticmethod
    def _check_file(descriptor):
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_nlink != 1
        ):
            raise RecoveryGuardStorageError("Unsafe local recovery storage")

    def _open_lock(self, root, name):
        flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
        try:
            descriptor = os.open(name, flags, dir_fd=root)
        except FileNotFoundError:
            try:
                descriptor = os.open(
                    name, flags | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=root
                )
            except FileExistsError:
                # Another instance may create the permanent lock file between
                # lookup and exclusive creation. Reopen without creation flags;
                # combining concurrent O_CREAT/O_NOFOLLOW is racy on macOS.
                descriptor = os.open(name, flags, dir_fd=root)
        try:
            self._check_file(descriptor)
            return descriptor
        except BaseException:
            os.close(descriptor)
            raise

    def _try_account_lock(self, identity):
        root = None
        descriptor = None
        try:
            root = self._root_fd()
            descriptor = self._open_lock(root, f"account-{identity}.lock")
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                os.close(descriptor)
                return None
            return descriptor
        except RecoveryGuardError:
            if descriptor is not None:
                os.close(descriptor)
            raise
        except OSError:
            if descriptor is not None:
                os.close(descriptor)
            raise RecoveryGuardStorageError(
                "Local recovery storage is unavailable"
            ) from None
        finally:
            if root is not None:
                os.close(root)

    @staticmethod
    def _release(descriptor):
        if descriptor is not None:
            os.close(descriptor)

    def _read(self, root):
        try:
            descriptor = os.open(
                "ledger.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root
            )
        except FileNotFoundError:
            return {"version": 1, "accounts": {}}
        try:
            self._check_file(descriptor)
            if os.fstat(descriptor).st_size > 1024 * 1024:
                raise ValueError
            with os.fdopen(descriptor, "r", encoding="utf-8") as stream:
                descriptor = None
                payload = json.load(stream, object_pairs_hook=_unique_object)
            if not isinstance(payload, dict) or set(payload) != {"version", "accounts"}:
                raise ValueError
            if type(payload["version"]) is not int or payload["version"] not in (1, 2):
                raise ValueError
            if not isinstance(payload["accounts"], dict):
                raise ValueError
            for identity, entry in payload["accounts"].items():
                _identity(identity)
                keys = {
                    "rejected",
                    "uncertain",
                    "verified",
                    "pending",
                }
                if payload["version"] == 2:
                    keys.add("generation")
                if not isinstance(entry, dict) or set(entry) != keys:
                    raise ValueError
                if any(
                    type(entry[key]) is not int or not 0 <= entry[key] < 2**63
                    for key in ("rejected", "uncertain", "verified")
                ):
                    raise ValueError
                if entry["pending"] is not None and (
                    not isinstance(entry["pending"], str)
                    or _TOKEN.fullmatch(entry["pending"]) is None
                ):
                    raise ValueError
                if payload["version"] == 2 and entry["generation"] is not None and (
                    not isinstance(entry["generation"], str)
                    or _TOKEN.fullmatch(entry["generation"]) is None
                ):
                    raise ValueError
            return payload
        finally:
            if descriptor is not None:
                os.close(descriptor)

    def _write(self, root, payload):
        filename = f".ledger-{uuid4().hex}"
        descriptor = os.open(
            filename,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=root,
        )
        try:
            self._check_file(descriptor)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                descriptor = None
                json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(filename, "ledger.json", src_dir_fd=root, dst_dir_fd=root)
            os.fsync(root)
        finally:
            if descriptor is not None:
                os.close(descriptor)
            try:
                os.unlink(filename, dir_fd=root)
            except FileNotFoundError:
                pass

    @staticmethod
    def _entry_digest(identity, entry):
        encoded = json.dumps(
            {"identity": identity, "entry": entry},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _witness_matches(self, identity, entry):
        """Read without enrolling an account or repairing its witness."""
        if not entry.get("generation"):
            return False
        root = descriptor = None
        try:
            try:
                root = self._root_fd(self.witness_root, create=False)
                descriptor = os.open(
                    f"account-{identity}.json",
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                    dir_fd=root,
                )
            except FileNotFoundError:
                return False
            self._check_file(descriptor)
            if os.fstat(descriptor).st_size > 512:
                raise ValueError
            with os.fdopen(descriptor, "r", encoding="utf-8") as stream:
                descriptor = None
                payload = json.load(stream, object_pairs_hook=_unique_object)
            if (
                not isinstance(payload, dict)
                or set(payload) != {"version", "digest"}
                or type(payload["version"]) is not int
                or payload["version"] != 1
                or not isinstance(payload["digest"], str)
                or _IDENTITY.fullmatch(payload["digest"]) is None
            ):
                raise ValueError
            return payload["digest"] == self._entry_digest(identity, entry)
        finally:
            for opened in (descriptor, root):
                if opened is not None:
                    os.close(opened)

    def _write_witness(self, identity, entry):
        """Commit only one account after its new ledger bytes are durable."""
        root = descriptor = None
        temporary = f".witness-{uuid4().hex}"
        try:
            root = self._root_fd(self.witness_root)
            # Refuse existing unsafe destinations, even though replace itself
            # would not follow a symlink. An acknowledgement does not grant
            # permission to repair filesystem ownership or link violations.
            try:
                descriptor = os.open(
                    f"account-{identity}.json",
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                    dir_fd=root,
                )
            except FileNotFoundError:
                pass
            else:
                self._check_file(descriptor)
                os.close(descriptor)
                descriptor = None
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=root,
            )
            self._check_file(descriptor)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                descriptor = None
                json.dump(
                    {"version": 1, "digest": self._entry_digest(identity, entry)},
                    stream,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(
                temporary, f"account-{identity}.json", src_dir_fd=root, dst_dir_fd=root
            )
            os.fsync(root)
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if root is not None:
                try:
                    os.unlink(temporary, dir_fd=root)
                except FileNotFoundError:
                    pass
                os.close(root)

    @staticmethod
    def _status(entry, trusted):
        unresolved = (
            entry["rejected"] + entry["uncertain"]
            + int(entry["pending"] is not None)
        )
        return {
            "rejected": entry["rejected"],
            "uncertain": entry["uncertain"],
            "pending": int(entry["pending"] is not None),
            "verified": entry["verified"],
            "unresolved": unresolved,
            "limit": _LIMIT,
            "blocked": not trusted or unresolved >= _LIMIT,
            "review_required": not trusted,
        }

    def _transaction(self, identity, action, token=None, owns_account=False):
        root = ledger_lock = account_lock = None
        try:
            root = self._root_fd()
            ledger_lock = self._open_lock(root, "ledger.lock")
            fcntl.flock(ledger_lock, fcntl.LOCK_EX)
            payload = self._read(root)
            entry = payload["accounts"].get(
                identity,
                {
                    "rejected": 0, "uncertain": 0, "verified": 0,
                    "pending": None, "generation": None,
                },
            )
            trusted = payload["version"] == 2 and self._witness_matches(identity, entry)
            if not trusted and action != "reset":
                if action == "status":
                    return self._status(entry, False)
                raise RecoveryGuardReviewRequired(
                    "Local recovery history requires explicit review"
                )
            changed = False
            # A pending reservation whose account lock is free survived a crash.
            # Never reclassify another live attempt's reservation.
            if action in ("begin", "status") and entry["pending"] is not None:
                if not owns_account:
                    account_lock = self._try_account_lock(identity)
                if owns_account or account_lock is not None:
                    entry["uncertain"] = min(entry["uncertain"] + 1, _MAX_COUNT)
                    entry["pending"] = None
                    changed = True
            unresolved = (
                entry["rejected"]
                + entry["uncertain"]
                + int(entry["pending"] is not None)
            )
            if action in ("begin", "reserve"):
                if unresolved >= _LIMIT:
                    raise RecoveryGuardBlocked(
                        "Local recovery submissions require acknowledgement"
                    )
                if entry["pending"] is not None:
                    raise RecoveryGuardBlocked("Local recovery is already active")
                if action == "reserve":
                    entry["pending"] = token
                    changed = True
            elif action in ("rejected", "verified", "uncertain"):
                if entry["pending"] == token:
                    entry[action] = min(entry[action] + 1, _MAX_COUNT)
                    entry["pending"] = None
                    changed = True
            elif action == "abandon":
                if entry["pending"] == token:
                    entry["pending"] = None
                    changed = True
            elif action == "reset":
                entry["rejected"] = entry["uncertain"] = 0
                entry["pending"] = None
                changed = True
            if changed:
                if payload["version"] == 1:
                    for saved in payload["accounts"].values():
                        saved["generation"] = None
                    payload["version"] = 2
                entry["generation"] = uuid4().hex
                payload["accounts"][identity] = entry
                self._write(root, payload)
                self._write_witness(identity, entry)
                trusted = True
            return self._status(entry, trusted)
        except RecoveryGuardError:
            raise
        except (OSError, ValueError, TypeError, KeyError, UnicodeError):
            raise RecoveryGuardStorageError(
                "Local recovery storage is unavailable or invalid"
            ) from None
        finally:
            for descriptor in (account_lock, ledger_lock, root):
                if descriptor is not None:
                    os.close(descriptor)

    @asynccontextmanager
    async def attempt(self, identity):
        """Hold account ownership through unlock, including cancellation cleanup."""
        identity = _identity(identity)
        lock = self._locks.setdefault(identity, asyncio.Lock())
        async with lock:
            descriptor = None
            attempt = None
            try:
                while descriptor is None:
                    descriptor = await _execute(
                        self._try_account_lock, identity, cleanup=self._release
                    )
                    if descriptor is None:
                        await asyncio.sleep(0.05)
                await _execute(self._transaction, identity, "begin", None, True)
                attempt = RecoveryAttempt(self, identity)
                yield attempt
            finally:
                unwinding = sys.exception()
                try:
                    if attempt is not None:
                        attempt.active = False
                    if (
                        attempt is not None
                        and attempt.token is not None
                        and not attempt.finished
                    ):
                        try:
                            await attempt._record(
                                "uncertain" if attempt.ready else "abandon"
                            )
                        except RecoveryGuardReviewRequired:
                            # A failed dual-file commit leaves a deliberate
                            # mismatch. Never repair it during unwinding or
                            # obscure the original storage/cancellation failure.
                            if unwinding is None:
                                raise
                finally:
                    if descriptor is not None:
                        await _execute(self._release, descriptor)

    async def status(self, identity):
        """Read only local counters; a crashed pending submission stays unresolved."""
        return await _execute(self._transaction, _identity(identity), "status")

    async def reset(self, identity):
        """Acknowledge local unresolved counts; never reset a server allowance."""
        identity = _identity(identity)
        if self._locks.setdefault(identity, asyncio.Lock()).locked():
            raise RecoveryGuardBlocked("Local recovery is already active")
        descriptor = await _execute(
            self._try_account_lock, identity, cleanup=self._release
        )
        if descriptor is None:
            raise RecoveryGuardBlocked("Local recovery is already active")
        try:
            return await _execute(self._transaction, identity, "reset", None, True)
        finally:
            await _execute(self._release, descriptor)


class RecoveryAttempt:
    """Exactly one possible proof submission and its verified local outcome."""

    def __init__(self, guard, identity):
        self.guard = guard
        self.identity = identity
        self.token = None
        self.finished = False
        self.active = True
        self.ready = False
        self.outcome = None

    async def before_dispatch(self):
        if not self.active or self.token is not None or self.finished:
            raise RuntimeError("Recovery submission was already reserved")
        self.token = uuid4().hex
        await _execute(
            self.guard._transaction, self.identity, "reserve", self.token, True
        )
        # The SDK awaits this callback before sending the proof. If this await
        # fails or is cancelled, it cannot have dispatched and can be abandoned
        # durably while this process still knows the outcome. A crash cannot
        # establish that fact, so any pending record remains conservative.
        self.ready = True

    async def _finish(self, outcome):
        if not self.active or not self.ready or self.token is None or self.finished:
            raise RuntimeError("Recovery submission is not pending")
        await self._record(outcome)

    async def _record(self, outcome):
        def commit():
            self.guard._transaction(self.identity, outcome, self.token, True)
            # Publish the durable result even when cancellation arrives while
            # the executor transaction is completing and its await is drained.
            self.outcome = "abandoned" if outcome == "abandon" else outcome
            self.finished = True

        await _execute(commit)

    async def refused(self):
        await self._finish("rejected")

    async def verified(self):
        await self._finish("verified")


def get_recovery_guard(hass):
    """Keep the service independent of integration unload and account deletion."""
    if _SERVICE not in hass.data:
        hass.data[_SERVICE] = RecoveryGuard(
            Path(hass.config.path(".storage", "homecircle_findmy", "recovery_guard")),
            Path(hass.config.path(".cache", "homecircle_findmy", "recovery_guard")),
        )
    return hass.data[_SERVICE]
