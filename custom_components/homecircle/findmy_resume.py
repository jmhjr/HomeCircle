"""Prepare an existing report connection without repeating Apple authentication.

This restores a capability already held by HomeCircle. It neither renews an
expired service token nor establishes access for a different Apple account.
"""

from copy import deepcopy

from .findmy_setup import FindMySetup, FindMySetupError, sdk
from .findmy_vault import passwordless


def has_saved_report_capability(session) -> bool:
    """Inspect structure only; token presence is not proof Apple will accept it."""
    if not isinstance(session, dict):
        return False
    account, login = session.get("account"), session.get("login")
    if not isinstance(account, dict) or account.get("password") is not None:
        return False
    if not isinstance(login, dict) or login.get("state") != 3:
        return False
    data = login.get("data")
    if not isinstance(data, dict):
        return False
    dsid, mobileme = data.get("dsid"), data.get("mobileme_data")
    if not isinstance(dsid, str) or not dsid.strip() or not isinstance(mobileme, dict):
        return False
    tokens = mobileme.get("tokens")
    if not isinstance(tokens, dict):
        return False
    token = tokens.get("searchPartyToken")
    return isinstance(token, str) and bool(token.strip())


async def _no_recovery(_account):
    raise FindMySetupError("findmy_saved_session_unavailable")


def prepare_saved_setup(session, previous_items, libraries):
    """Restore saved items locally for selection; this function makes no requests.

    This is local restoration, not validation of current Apple access. No
    password, CloudKit grant, escrow material or recovery client is carried
    into this report-only setup. Inputs remain untouched on failure.
    """
    if not has_saved_report_capability(session):
        raise FindMySetupError("findmy_saved_session_unavailable")
    if not isinstance(previous_items, dict) or not previous_items:
        raise FindMySetupError("findmy_saved_session_unavailable")

    account_type, _, states, _ = sdk()
    from ._vendor_findmy import FindMyAccessory

    try:
        items = deepcopy(previous_items)
        accessories = {}
        for identifier, item in items.items():
            if (
                not isinstance(identifier, str)
                or not identifier
                or not isinstance(item, dict)
                or not isinstance(item.get("accessory"), dict)
            ):
                raise ValueError
            accessories[identifier] = FindMyAccessory.from_json(item["accessory"])
        account = account_type.from_json(
            passwordless(session), anisette_libs_path=libraries
        )
    except (
        AssertionError,
        AttributeError,
        KeyError,
        TypeError,
        ValueError,
        OverflowError,
    ):
        raise FindMySetupError("findmy_saved_session_unavailable") from None

    # Restore exactly the identity saved with this report grant. This path has
    # no authentication or CloudKit step that needs a new transport profile.
    setup = FindMySetup(account, _no_recovery, states)
    setup.previous_items = items
    setup.accessories = accessories
    setup.discover_new = False
    return setup
