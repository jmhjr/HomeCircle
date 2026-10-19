"""Opt-in service declarations for newly established HomeCircle accounts.

The Windows GSA declaration passed an initial-challenge check. Later declarations
are an upstream compatibility report, not proof of a complete HomeCircle login.
They do not describe the origin of the Android ADI libraries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Endpoint = Literal["gsa", "verification", "delegate", "settings", "escrow", "cloudkit"]

POLICY_ID = "windows_onboarding_v1"
MAC_POLICY_ID = "mac_coreadi_v1"
_WINDOWS = "<PC> <Windows;6.2(0,0);9200>"
_MAC = "<MacBookPro18,3> <Mac OS X;13.4.1;22F8>"
_AKD = "<com.apple.AuthKit/1 (com.apple.akd/1.0)>"
_ACCOUNTSD = "<com.apple.AOSKit/282 (com.apple.accountsd/113)>"
_SBD = "<com.apple.AuthKit/1 (com.apple.sbd/638.100.48)>"
_CLOUDKIT = "<com.apple.cloudkit.CloudKitDaemon/1970 (com.apple.cloudd/1970)>"


@dataclass(frozen=True)
class EndpointProfile:
    """One service's declaration; None retains its existing user agent."""

    client_info: str
    user_agent: str | None = None

    def apply(self, headers: dict[str, str]) -> dict[str, str]:
        """Replace case-insensitive declarations without leaving duplicate fields."""
        result = dict(headers)
        for name, value in (
            ("X-Mme-Client-Info", self.client_info),
            ("User-Agent", self.user_agent),
        ):
            if value is None:
                continue
            names = [key for key in result if key.lower() == name.lower()]
            target = names[0] if names else name
            for key in names:
                del result[key]
            result[target] = value
        return result


@dataclass(frozen=True)
class EndpointPolicy:
    """A versioned, immutable selection with no fallback between services."""

    identifier: str

    @property
    def name(self) -> str:
        """The fixed serialized policy marker."""
        return self.identifier

    def profile(self, endpoint: Endpoint) -> EndpointProfile:
        """Return only the explicitly selected endpoint's profile."""
        if self.identifier == MAC_POLICY_ID:
            platform = "<MacBookPro13,2> <macOS;13.1;22C65>"
            profiles = {
                "gsa": EndpointProfile(f"{platform} {_AKD}", "akd/1.0 CFNetwork/1404.0.5 Darwin/22.2.0"),
                "verification": EndpointProfile(f"{platform} {_AKD}", "akd/1.0 CFNetwork/1404.0.5 Darwin/22.2.0"),
                "delegate": EndpointProfile(f"{platform} {_ACCOUNTSD}"),
                "settings": EndpointProfile(f"{platform} {_ACCOUNTSD}"),
                "escrow": EndpointProfile(f"{platform} {_SBD}"),
                "cloudkit": EndpointProfile(f"{platform} {_CLOUDKIT}"),
            }
            try:
                return profiles[endpoint]
            except KeyError:
                raise ValueError("Unknown endpoint stage") from None
        if self.identifier != POLICY_ID:
            raise ValueError("Unknown endpoint policy")
        profiles = {
            "gsa": EndpointProfile(f"{_WINDOWS} {_AKD}", "akd/1.0 CFNetwork/978.0.7 Darwin/18.7.0"),
            # Fresh verification was not exercised by the upstream trusted-session
            # report. Select the same PET-side declaration explicitly, retain
            # required app/auth headers, and never try alternative profiles.
            "verification": EndpointProfile(f"{_WINDOWS} {_AKD}", "akd/1.0 CFNetwork/978.0.7 Darwin/18.7.0"),
            "delegate": EndpointProfile(f"{_WINDOWS} {_ACCOUNTSD}"),
            "settings": EndpointProfile(f"{_MAC} {_ACCOUNTSD}"),
            "escrow": EndpointProfile(f"{_WINDOWS} {_SBD}"),
            "cloudkit": EndpointProfile(f"{_MAC} {_CLOUDKIT}"),
        }
        try:
            return profiles[endpoint]
        except KeyError:
            raise ValueError("Unknown endpoint stage") from None


WINDOWS_ONBOARDING_V1 = EndpointPolicy(POLICY_ID)
MAC_COREADI_V1 = EndpointPolicy(MAC_POLICY_ID)


def restore_policy(value: object) -> EndpointPolicy | None:
    """Restore only the known marker; a missing marker preserves legacy behavior."""
    if value is None:
        return None
    if type(value) is str and value == MAC_POLICY_ID:
        return MAC_COREADI_V1
    if type(value) is not str or value != POLICY_ID:
        raise ValueError("Unknown saved endpoint policy")
    return WINDOWS_ONBOARDING_V1
