"""Account-bound accessory continuity without retaining deselected tracking keys.

Only the encrypted account vault holds this ledger and its random HMAC secret.
The commitments prove equality of all three accessory secrets; names, Apple
record identifiers and registry history are never identity evidence.
"""

from copy import deepcopy
from hashlib import sha256
import hmac
import secrets


class IdentityError(ValueError):
    """Stored continuity cannot be safely applied to this account or selection."""


def authenticated_identity(session):
    """Require an authenticated DSID; an email alias is insufficient."""
    if not isinstance(session, dict):
        return None
    login = session.get("login", {})
    if not isinstance(login, dict) or login.get("state") != 3:
        return None
    data = login.get("data", {})
    if not isinstance(data, dict):
        return None
    dsid = data.get("dsid")
    if not (
        (type(dsid) is int and dsid > 0)
        or (isinstance(dsid, str) and 0 < len(dsid) <= 256 and dsid.strip())
    ):
        return None
    return sha256(("dsid:" + str(dsid)).encode()).hexdigest()


def accessory_material(exported):
    """Canonicalize the exact master key and both initial rolling-key seeds."""
    try:
        result = tuple(
            bytes.fromhex(exported[field]) for field in ("master_key", "skn", "sks")
        )
    except (KeyError, TypeError, ValueError):
        return None
    return result if tuple(map(len, result)) == (28, 32, 32) else None


def safe_metadata(metadata):
    """Keep display settings and stable IDs, never arbitrary accessory exports."""
    result = {
        key: deepcopy(metadata[key])
        for key in ("name", "type", "unique_id")
        if key in metadata
    }
    preferences = metadata.get("display_preferences")
    if isinstance(preferences, dict):
        result["display_preferences"] = {
            key: deepcopy(preferences[key])
            for key in (
                "kind",
                "trackers",
                "additional_residences",
                "display_name",
                "show_on_map",
                "picture_id",
                "supporting",
                "location_reports",
                "pet_home_minutes",
                "pet_away_minutes",
                "tracker_selection",
                "auto_request_location",
            )
            if key in preferences
        }
    return result


def validate_state(state, session):
    """Fail closed rather than rebind another account's encrypted identity ledger."""
    identity = authenticated_identity(session)
    try:
        if (
            not identity
            or state["version"] != 1
            or state["account_identity"] != identity
            or len(bytes.fromhex(state["secret"])) != 32
            or not isinstance(state["records"], dict)
            or set(state) != {"version", "account_identity", "secret", "records"}
        ):
            raise ValueError
        identifiers = set()
        for commitment, record in state["records"].items():
            if (
                len(bytes.fromhex(commitment)) != 32
                or set(record) != {"identifier", "metadata"}
                or not isinstance(record["identifier"], str)
                or not record["identifier"]
                or record["identifier"] in identifiers
                or not isinstance(record["metadata"], dict)
                or safe_metadata(record["metadata"]) != record["metadata"]
            ):
                raise ValueError
            identifiers.add(record["identifier"])
    except (KeyError, TypeError, ValueError, AttributeError):
        raise IdentityError("findmy_identity_unavailable") from None
    return deepcopy(state)


def commitment_for(state, exported):
    material = accessory_material(exported)
    if material is None:
        return None
    message = (
        b"HomeCircle accessory identity v1\0"
        + bytes.fromhex(state["account_identity"])
        + b"".join(material)
    )
    return hmac.new(bytes.fromhex(state["secret"]), message, sha256).hexdigest()


def new_state(session):
    identity = authenticated_identity(session)
    if identity is None:
        return None
    return {
        "version": 1,
        "account_identity": identity,
        "secret": secrets.token_hex(32),
        "records": {},
    }


def prepare_state(session, previous_items, metadata, state=None):
    """Create only an in-memory ledger, backfilling still-selected proven keys."""
    identity = authenticated_identity(session)
    if state is not None:
        result = validate_state(state, session)
    elif identity and any(
        accessory_material(item.get("accessory", {}))
        for item in previous_items.values()
    ):
        result = new_state(session)
    else:
        return None
    records = result["records"]
    for identifier, item in previous_items.items():
        commitment = commitment_for(result, item.get("accessory", {}))
        if commitment is None:
            continue
        record = records.get(commitment)
        if record and record["identifier"] != identifier:
            raise IdentityError("findmy_duplicate_item")
        if any(
            value["identifier"] == identifier and key != commitment
            for key, value in records.items()
        ):
            raise IdentityError("findmy_duplicate_item")
        records[commitment] = {
            "identifier": identifier,
            "metadata": safe_metadata(
                metadata.get(identifier, record["metadata"] if record else {})
            ),
        }
    return result


def resolve_identifier(exported, candidate, previous_items, state):
    """Use exact key equality; refuse ambiguous evidence and reused old IDs."""
    material = accessory_material(exported)
    matches = {
        identifier
        for identifier, item in previous_items.items()
        if material is not None
        and accessory_material(item.get("accessory", {})) == material
    }
    commitment = commitment_for(state, exported) if state else None
    if commitment and commitment in state["records"]:
        matches.add(state["records"][commitment]["identifier"])
    if len(matches) > 1:
        raise IdentityError("findmy_duplicate_item")
    if matches:
        return matches.pop()
    reserved = set(previous_items)
    if state:
        reserved.update(record["identifier"] for record in state["records"].values())
    if candidate in reserved:
        # A reused Apple identifier cannot inherit an old entity or preferences.
        if commitment is None:
            raise IdentityError("findmy_missing_item_identity")
        return sha256(
            ("new-accessory:" + candidate + ":" + commitment).encode()
        ).hexdigest()
    return candidate


def selection_state(session, items, metadata, state=None):
    """Remember chosen identities/preferences while storing only chosen raw keys."""
    return prepare_state(session, items, metadata, state)


def previous_metadata(state, identifier):
    if state:
        for record in state["records"].values():
            if record["identifier"] == identifier:
                return deepcopy(record["metadata"])
    return {}


def save_selection(vault, session, items, state):
    """Keep legacy two-argument callers unchanged when no ledger is available."""
    if state is None:
        vault.save_account(session, items)
    else:
        vault.save_account(session, items, identity_state=state)
