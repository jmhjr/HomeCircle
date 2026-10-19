"""A separately authenticated, unused recovery PET bound to the current account."""
from __future__ import annotations

import hmac
import asyncio
from types import MethodType

from .._vendor_findmy.errors import UnauthorizedError
from .._vendor_findmy.reports.account import AsyncAppleAccount, LoginState
from .._vendor_findmy.reports.endpoint_policy import MAC_COREADI_V1


class SharedProvider:
    """Borrow the current identity without transferring its lifetime."""

    def __init__(self, owner):
        self.owner = owner

    def __getattr__(self, name):
        return getattr(self.owner, name)

    async def close(self):
        pass


async def fresh_recovery_pet(account):
    """Run just init/complete; never delegate or request another verification."""
    provider = account._anisette
    if not getattr(provider, "_homecircle_mac", False) or not account._password:
        raise UnauthorizedError("Recovery sign-in required")
    previous_adsid = account._login_state_data.get("adsid")
    previous_name = (account._account_info or {}).get("account_name")
    if not isinstance(previous_adsid, str) or not previous_adsid or not isinstance(previous_name, str) or not previous_name:
        raise UnauthorizedError("Recovery account binding unavailable")
    clone = AsyncAppleAccount(
        SharedProvider(provider), uid=provider.local_user_uuid, devid=provider.device_uuid,
        device_name="HomeCircle Find My", timeout=30, endpoint_policy=MAC_COREADI_V1,
    )
    clone._username, clone._password = account._username, account._password
    clone.gsa_client_info = account.gsa_client_info
    try:
        state = await clone._gsa_authenticate()
        if state != LoginState.AUTHENTICATED:
            raise UnauthorizedError("Recovery sign-in required")
        data, info = clone._login_state_data, clone._account_info or {}
        adsid, name, pet = data.get("adsid"), info.get("account_name"), data.get("idms_pet")
        if (
            not isinstance(adsid, str)
            or not hmac.compare_digest(adsid.encode(), previous_adsid.encode())
            or not isinstance(name, str)
            or name.strip().casefold() != previous_name.strip().casefold()
            or not isinstance(pet, str) or not 0 < len(pet) <= 8192
        ):
            raise UnauthorizedError("Recovery account binding refused")
        return pet
    except asyncio.CancelledError:
        raise
    except Exception:
        raise UnauthorizedError("Recovery sign-in unavailable") from None
    finally:
        clone._password = clone._username = clone._account_info = None
        clone._login_state_data.clear()
        await clone.close()


def bind_account(account):
    """One explicit recovery credential request uses the already owned identity."""
    account.request_pet = MethodType(fresh_recovery_pet, account)
