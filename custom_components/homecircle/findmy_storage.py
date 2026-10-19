"""Remove only explicit HomeCircle-owned account stores, never prototype stores."""

import shutil
import re
from .findmy_provider import account_root
from .findmy_vault import VaultError


def delete_account(hass, metadata):
    if metadata.get("storage_id") == "legacy":
        raise VaultError("Legacy prototype storage is not owned by HomeCircle")
    root = account_root(hass, metadata)
    if not root.exists() and not root.is_symlink():
        return
    from .findmy_vault import Vault

    Vault(root)._check(root, directory=True)
    # Refuse unexpected trees rather than following any link or deleting arbitrary files.
    for child in root.iterdir():
        if child.name not in {"session.key", "session.vault"} and not re.fullmatch(
            r"\.session-[a-zA-Z0-9_-]+", child.name
        ):
            raise VaultError("Unexpected account recovery file")
        Vault(root)._check(child)
    shutil.rmtree(root)


def prune_orphans(hass, accounts):
    """Only this provider's private namespace is eligible; prototype accounts stay intact."""
    import re

    parent = account_root(hass, {"storage_id": "a" * 32}).parent
    if not parent.exists():
        return
    referenced = {
        account.get("storage_id")
        for account in accounts.values()
        if isinstance(account, dict)
    }
    for child in parent.iterdir():
        if re.fullmatch(r"[a-f0-9]{32}", child.name) and child.name not in referenced:
            delete_account(hass, {"storage_id": child.name})
