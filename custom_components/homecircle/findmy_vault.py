"""Local encrypted session store; the Apple password is never persisted."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import stat
import tempfile
from hashlib import sha256

from cryptography.fernet import Fernet


_PRESERVE_IDENTITY = object()


class VaultError(RuntimeError):
    """The local store cannot be safely opened."""


def passwordless(state: dict) -> dict:
    result = copy.deepcopy(state)
    result["account"]["password"] = None
    result["account"]["info"] = None
    if "login" in result:
        old = result["login"].get("data", {})
        token = old.get("mobileme_data", {}).get("tokens", {}).get("searchPartyToken")
        result["login"]["data"] = {
            "dsid": old.get("dsid"),
            "mobileme_data": {"tokens": {"searchPartyToken": token}},
        }
    return result


def account_identity(state):
    """Use Apple's stable authenticated identifier, rather than an email alias."""
    dsid = state.get("login", {}).get("data", {}).get("dsid")
    if dsid is not None:
        return sha256(("dsid:" + str(dsid)).encode()).hexdigest()
    # Compatibility for pre-login/transient synthetic records. A real logged-in
    # session always has dsid; migration's SDK preflight also validates its shape.
    return sha256(state["account"]["username"].strip().casefold().encode()).hexdigest()


class Vault:
    def __init__(self, root: Path):
        self.root = root
        self.key_path = root / "session.key"
        self.data_path = root / "session.vault"

    def _check(self, path: Path, directory: bool = False) -> None:
        info = path.lstat()
        kind = stat.S_ISDIR if directory else stat.S_ISREG
        if not kind(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
            raise VaultError("Unsafe session storage permissions or file type")

    def _cipher(self, create: bool = False) -> Fernet:
        if not self.root.exists() and create:
            self.root.mkdir(mode=0o700, parents=True)
        self._check(self.root, directory=True)
        if not self.key_path.exists():
            if not create or self.data_path.exists():
                raise VaultError("Session encryption key is missing")
            fd = os.open(self.key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(Fernet.generate_key())
                stream.flush()
                os.fsync(stream.fileno())
        self._check(self.key_path)
        key = self.key_path.read_bytes()
        try:
            return Fernet(key)
        except ValueError:
            raise VaultError(
                "Session encryption key is invalid; it was not replaced"
            ) from None

    def load(self) -> dict:
        try:
            cipher = self._cipher()
            self._check(self.data_path)
        except OSError:
            raise VaultError(
                "Session store is unreadable; it was not replaced"
            ) from None
        try:
            data = json.loads(cipher.decrypt(self.data_path.read_bytes()))
            if (
                data["version"] not in (1, 2)
                or data["session"]["account"]["password"] is not None
            ):
                raise ValueError
            if data["version"] == 2:
                if not isinstance(data["items"], dict) or not data["items"]:
                    raise ValueError
                for identifier, item in data["items"].items():
                    if not isinstance(identifier, str) or not isinstance(
                        item["accessory"], dict
                    ):
                        raise ValueError
                if "identity_state" in data:
                    from .findmy_identity import validate_state

                    validate_state(data["identity_state"], data["session"])
            return data
        except Exception:
            raise VaultError(
                "Session store is unreadable; it was not replaced"
            ) from None

    def save(self, session: dict, accessory: dict, report: dict | None = None) -> None:
        if self.data_path.exists() or self.data_path.is_symlink():
            existing = self.load()
            if existing["version"] != 1:
                raise VaultError("Use account-aware storage for multiple accessories")
        payload = {
            "version": 1,
            "session": passwordless(session),
            "accessory": accessory,
            "report": report,
        }
        self._write(payload)

    def save_account(
        self, session: dict, items: dict, *, identity_state=_PRESERVE_IDENTITY
    ) -> None:
        if not items:
            raise VaultError(
                "An account must contain at least one explicitly selected item"
            )
        if identity_state is _PRESERVE_IDENTITY:
            identity_state = None
            if self.data_path.exists() or self.data_path.is_symlink():
                identity_state = self.load().get("identity_state")
        payload = {"version": 2, "session": passwordless(session), "items": items}
        if identity_state is not None:
            from .findmy_identity import validate_state

            payload["identity_state"] = validate_state(identity_state, session)
        self._write(payload)

    def _write(self, payload: dict) -> None:
        cipher = self._cipher(create=True)
        serialized = json.dumps(payload, sort_keys=True).encode()
        if self.data_path.exists() or self.data_path.is_symlink():
            # Validate existing recovery state even when no write is necessary.
            existing = self.load()
            if json.dumps(existing, sort_keys=True).encode() == serialized:
                return
        encrypted = cipher.encrypt(serialized)
        fd, filename = tempfile.mkstemp(prefix=".session-", dir=self.root)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(encrypted)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(filename, self.data_path)
            directory_fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if os.path.exists(filename):
                os.unlink(filename)
