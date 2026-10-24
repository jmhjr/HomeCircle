"""A separately authenticated, unused recovery PET bound to the current account."""
from __future__ import annotations

import asyncio
import hmac
import math
import sys
from types import MethodType

from aiohttp import ClientError

from .._vendor_findmy.errors import (
    AppleServiceUnavailableError, InvalidCredentialsError, UnauthorizedError,
)
from .._vendor_findmy.reports.account import AsyncAppleAccount, LoginState
from .._vendor_findmy.reports.endpoint_policy import MAC_COREADI_V1


class RecoveryPETError(UnauthorizedError):
    """A local credential-refresh outcome, always before passcode-proof dispatch."""

    stage = "preproof"
    dispatch_state = "not_dispatched"
    server_verified = False

    def __init__(self, reason, *, http_status=None, auth_phase=None, retry_after=None):
        self.reason = reason if reason in {
            "missing_password", "factor_required", "identity_mismatch", "transient",
            "protocol", "credentials",
        } else "protocol"
        self.http_status = http_status if type(http_status) is int and 100 <= http_status <= 599 else None
        self.auth_phase = auth_phase if type(auth_phase) is str and auth_phase in ("init", "complete") else None
        self.retry_after_seconds = (
            math.ceil(retry_after)
            if type(retry_after) in (int, float) and 0 <= retry_after <= 86400 and math.isfinite(retry_after)
            else None
        )
        self.service_code = None
        super().__init__("Recovery credential refresh " + self.reason)


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
    if not account._password:
        raise RecoveryPETError("missing_password")
    if not getattr(provider, "_homecircle_mac", False):
        raise RecoveryPETError("protocol")
    previous_adsid = account._login_state_data.get("adsid")
    previous_name = (account._account_info or {}).get("account_name")
    if not isinstance(previous_adsid, str) or not previous_adsid or not isinstance(previous_name, str) or not previous_name:
        raise RecoveryPETError("identity_mismatch")
    clone = AsyncAppleAccount(
        SharedProvider(provider), uid=provider.local_user_uuid, devid=provider.device_uuid,
        device_name="HomeCircle Find My", timeout=30, endpoint_policy=MAC_COREADI_V1,
    )
    clone._username, clone._password = account._username, account._password
    clone.gsa_client_info = account.gsa_client_info
    try:
        state = await clone._gsa_authenticate()
        if state != LoginState.AUTHENTICATED:
            raise RecoveryPETError("factor_required")
        data, info = clone._login_state_data, clone._account_info or {}
        adsid, name, pet = data.get("adsid"), info.get("account_name"), data.get("idms_pet")
        if (
            not isinstance(adsid, str)
            or not hmac.compare_digest(adsid.encode(), previous_adsid.encode())
            or not isinstance(name, str)
            or name.strip().casefold() != previous_name.strip().casefold()
        ):
            raise RecoveryPETError("identity_mismatch")
        if not isinstance(pet, str) or not 0 < len(pet) <= 8192:
            raise RecoveryPETError("protocol")
        return pet
    except (asyncio.CancelledError, RecoveryPETError):
        raise
    except AppleServiceUnavailableError as error:
        raise RecoveryPETError(
            "transient", http_status=error.status_code,
            auth_phase=error.phase, retry_after=error.retry_after,
        ) from None
    except (OSError, TimeoutError, ClientError):
        raise RecoveryPETError("transient") from None
    except (InvalidCredentialsError, UnauthorizedError):
        raise RecoveryPETError("credentials") from None
    except Exception:
        raise RecoveryPETError("protocol") from None
    finally:
        primary_error = sys.exception() is not None
        clone._password = clone._username = clone._account_info = None
        clone._login_state_data.clear()
        try:
            await clone.close()
        except asyncio.CancelledError:
            if not primary_error:
                raise
        except Exception:
            # Cleanup must not replace the fixed original outcome or cancellation.
            if not primary_error:
                raise RecoveryPETError("protocol") from None


def bind_account(account):
    """One explicit recovery credential request uses the already owned identity."""
    account.request_pet = MethodType(fresh_recovery_pet, account)
