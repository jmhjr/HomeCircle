"""Atomic, provider-independent household configuration through HA selectors."""

from copy import deepcopy
from collections import Counter
import re
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from life360 import Life360Error, LoginError, RateLimited, Unauthorized

from .const import (
    DOMAIN,
    CONF_LIFE360_ACCOUNT,
    CONF_MEMBERS,
    CONF_PEOPLE,
    CONF_TRACKER_PEOPLE,
    CONF_PETS,
    CONF_PLACES,
    CONF_PRIMARY_HOME,
    CONF_RESIDENCES,
    CONF_TRACKERS,
    CONF_DISPLAY_NAME,
    CONF_SHOW_ON_MAP,
    CONF_AUTO_REQUEST_LOCATION,
)
from .normalize import normalize_household, normalize_member
from .selection import (
    SUPPORTING_DOMAINS,
    household_errors,
    member_errors,
    supporting_errors,
    tracker_suggestions,
    trackers_assigned_elsewhere,
    person_tracker_references,
    selectable,
    selected_entities,
)
from . import frontend
from .life360_direct import validate_account
from .tracker_providers import disconnected_owned_entities
from . import tracker_providers
from .zone_setup import async_create_zone, zone_error
from .person_setup import (
    async_create_person,
    async_link_tracker,
    has_person_entity,
    person_name_error,
    tracker_link_error,
)


def entity_selector(domain: str, multiple: bool = True):
    return selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain=domain,
            multiple=multiple,
        )
    )


def battery_selector(hass, selected: str | None = None):
    """Offer sensors with battery metadata, plus an existing saved mapping."""
    candidates = {
        state.entity_id
        for state in hass.states.async_all("sensor")
        if state.attributes.get("device_class") == "battery"
        or (
            state.attributes.get("unit_of_measurement") == "%"
            and not state.attributes.get("device_class")
        )
    }
    if selected:
        candidates.add(selected)
    return selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain="sensor", include_entities=sorted(candidates), multiple=False
        )
    )


def entity_label(hass, entity_id: str | None) -> str:
    """Use HA names, distinguishing trackers whose displayed names collide."""
    if not entity_id:
        return "none"
    state = hass.states.get(entity_id)
    if state and state.name != entity_id:
        name = state.name
        if entity_id.startswith("device_tracker.") and any(
            other.entity_id != entity_id and other.name.casefold() == name.casefold()
            for other in hass.states.async_all("device_tracker")
        ):
            return f"{name} ({entity_id})"
        return name
    return entity_id


def tracker_selector(hass):
    """Show entity IDs in the picker when HA gives trackers the same name."""
    trackers = hass.states.async_all("device_tracker")
    names = Counter(state.name.casefold() for state in trackers)
    if not any(count > 1 for count in names.values()):
        return entity_selector("device_tracker")
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                {"value": state.entity_id, "label": entity_label(hass, state.entity_id)}
                for state in trackers
            ],
            multiple=True,
            custom_value=True,
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


STATUS_SENSOR_KEYS = ("battery", "charging", "speed", "driving", "driving_reported_at")
LEGACY_REPORT_KEYS = ("location_reported_at", "location_report_source")
STATUS_SENSOR_LABELS = {
    "battery": "Battery",
    "charging": "Charging",
    "speed": "Speed",
    "driving": "Driving",
    "driving_reported_at": "Driving report time",
}
CONFIRM_SAME_ACCOUNT = "confirm_same_account"


def life360_account_schema(*, legacy_replacement: bool = False):
    """Use the same credential form for first setup, replacement, and repair."""
    return vol.Schema(
        {
            vol.Required("method", default="password"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=["password", "token"])
            ),
            vol.Optional("username"): selector.TextSelector(),
            vol.Required("secret"): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            **(
                {
                    vol.Optional(
                        CONFIRM_SAME_ACCOUNT, default=False
                    ): selector.BooleanSelector()
                }
                if legacy_replacement
                else {}
            ),
        }
    )


async def checked_life360_account(user_input):
    """Return a verified account or a safe, user-facing failure code."""
    method = user_input.get("method")
    username = (user_input.get("username") or "").strip()
    secret = (user_input.get("secret") or "").strip()
    if (
        method not in ("password", "token")
        or not secret
        or (method == "password" and not username)
    ):
        return None, "invalid_credentials"
    account = {"method": method, "username": username, "secret": secret}
    try:
        identity = await validate_account(account)
    except (LoginError, Unauthorized):
        return None, "invalid_auth"
    except RateLimited:
        return None, "rate_limited"
    except (Life360Error, TimeoutError, OSError):
        return None, "cannot_connect"
    except (KeyError, TypeError, ValueError):
        return None, "unexpected_response"
    if isinstance(identity, str):
        account["account_id_hash"] = identity
    return account, None


async def life360_continuity_error(
    previous, account, confirmed: bool, *, verify_old: bool = True
) -> str | None:
    """Compare known identities; ask for attestation only if old auth cannot be checked."""
    if not previous:
        return None
    old_identity = previous.get("account_id_hash")
    if not old_identity and verify_old:
        try:
            old_identity = await validate_account(previous)
        except (
            LoginError,
            Unauthorized,
            RateLimited,
            Life360Error,
            TimeoutError,
            OSError,
            KeyError,
            TypeError,
            ValueError,
        ):
            old_identity = None
    if isinstance(old_identity, str):
        return (
            "different_account"
            if account.get("account_id_hash") != old_identity
            else None
        )
    return None if confirmed else "same_account_confirmation_required"


def review_label(hass, entity_id: str) -> str:
    """Keep names on one line and prevent entity names from shaping Markdown."""
    return markdown_label(entity_label(hass, entity_id))


def markdown_label(value: str) -> str:
    """Keep user-provided labels from shaping the review Markdown."""
    label = " ".join(value.split())
    return re.sub(r"([\\`*_{}\[\]<>])", r"\\\1", label)


def tracker_advice(
    hass, associated: list[str], active: str | None
) -> tuple[str | None, str]:
    """Suggest one linked source from observable capabilities, without guessing ownership."""
    candidates = list(dict.fromkeys([*associated, *([active] if active else [])]))
    if not candidates:
        return None, (
            "No tracker is linked to this Home Assistant person. Open the picker to "
            "choose their phone or location tracker, or leave it empty to use "
            "the person record alone. Confirm ownership before selecting."
        )

    details = []
    for entity_id in candidates:
        state = hass.states.get(entity_id)
        available = state is not None and state.state not in ("unknown", "unavailable")
        gps = state is not None and state.attributes.get("source_type") == "gps"
        coordinates = state is not None and all(
            isinstance(state.attributes.get(key), (int, float))
            and not isinstance(state.attributes.get(key), bool)
            for key in ("latitude", "longitude")
        )
        rank = 0 if not available else (4 if gps and coordinates else 3 if gps else 1)
        if available and coordinates and not gps:
            rank = 2
        capability = (
            "unavailable now"
            if not available
            else "GPS position available"
            if gps and coordinates
            else "GPS tracker; no position now"
            if gps
            else "position available; source type unconfirmed"
            if coordinates
            else "Home/Away presence only"
        )
        if entity_id == active:
            capability += "; currently used by the HA person"
        details.append((entity_id, rank, capability))

    best_rank = max(rank for _, rank, _ in details)
    best = [entity_id for entity_id, rank, _ in details if rank == best_rank]
    suggested = None
    if best_rank > 0:
        suggested = active if active in best else best[0] if len(best) == 1 else None
    if suggested:
        headline = f"Suggested tracker: **{review_label(hass, suggested)}**."
    elif best_rank == 0:
        headline = "No linked tracker is available right now; review the choices below."
    else:
        headline = "Several linked trackers look equally suitable; choose the one you trust most."
    lines = [
        headline,
        "Choose one tracker for a clear location source. This is a suggestion based on "
        "the current HA state, not a measure of update reliability or GPS report time.",
        "Linked trackers:",
        *(
            f"- {review_label(hass, entity_id)} — {capability}"
            for entity_id, _, capability in details
        ),
    ]
    return suggested, "\n\n".join(lines[:2]) + "\n\n" + "\n".join(lines[2:])


def review_duration(minutes: int | float) -> str:
    """Show the configured pet threshold in units people can scan."""
    for interval, unit in ((1440, "day"), (60, "hour")):
        if minutes % interval == 0:
            amount = minutes / interval
            return f"{amount:g} {unit}{'' if amount == 1 else 's'}"
    return f"{minutes:g} min"


def current_position(hass, draft, person_id, member):
    """Use the same source decision as the dashboard for an unsaved member."""
    states = {state.entity_id: state for state in hass.states.async_all()}
    zone_names = {
        entity_id: state.name
        for entity_id, state in states.items()
        if entity_id.startswith("zone.")
    }
    return normalize_member(
        person_id, member, draft, states, zone_names, dt_util.utcnow()
    )


def position_guidance(hass, person_id, current, member) -> str:
    """Explain the current effective position source without guessing associations."""
    if "tracker_presence_conflict" in current.issues and current.residence:
        away_trackers = [
            tracker_id
            for tracker_id in member[CONF_TRACKERS]
            if (tracker := hass.states.get(tracker_id)) is not None
            and tracker.attributes.get("source_type") == "gps"
            and tracker.state == "not_home"
        ]
        if away_trackers:
            active = current.active_source_entity
            active_text = (
                f" Active HA Person source: {review_label(hass, active)}."
                if active
                else " The active HA Person source is unknown."
            )
            trackers = ", ".join(review_label(hass, item) for item in away_trackers)
            return (
                f"Tracker conflict: {review_label(hass, person_id)} is at a "
                "configured residence, "
                f"but the last HA state for selected GPS tracker {trackers} says "
                f"Away.{active_text} "
                "HomeCircle follows the HA Person for Home/Away and omits this "
                "conflicting map position. Review linked devices in "
                "[Home Assistant People settings](/config/person). "
                "Keep trackers that travel with this Person; HomeCircle will not "
                "change HA links automatically. Check update times because "
                "either state may be old; the GPS report time may be unknown."
            )
    if current.location is None:
        return (
            "No usable map position right now. Check this tracker's GPS state "
            "before saving."
            if person_id.startswith("device_tracker.")
            else "No usable map position right now. Check the Home Assistant "
            "Person or select a GPS tracker before saving."
        )
    source = current.location.evidence.source_entity
    if source == person_id and not person_id.startswith("device_tracker."):
        active = current.active_source_entity
        active_text = (
            f" Its active tracker is {review_label(hass, active)}." if active else ""
        )
        return (
            f"Current map position comes from the Home Assistant Person "
            f"({review_label(hass, person_id)}).{active_text} A selected tracker's "
            "report-time sensor will be used only if that tracker later drives "
            "the map."
        )
    return f"Current map position comes from {review_label(hass, source)}."


def review_summary(hass, draft: dict[str, Any], pending_links=None) -> dict[str, str]:
    """Describe the exact unsaved household selections in the final form."""
    places = ", ".join(review_label(hass, place) for place in draft[CONF_PLACES])
    current = normalize_household(
        draft,
        {state.entity_id: state for state in hass.states.async_all()},
        dt_util.utcnow(),
    )
    current_members = {member.id: member for member in current.members}
    members = []
    for person_id in [
        *draft.get(CONF_PEOPLE, []),
        *draft.get(CONF_TRACKER_PEOPLE, []),
        *draft.get(CONF_PETS, []),
    ]:
        member = draft[CONF_MEMBERS][person_id]
        supporting = member.get("supporting", {})
        status = ", ".join(
            f"{STATUS_SENSOR_LABELS[key]}: {review_label(hass, supporting[key])}"
            for key in STATUS_SENSOR_KEYS
            if supporting.get(key)
        )
        reports = dict(member.get("location_reports", {}))
        legacy_source = supporting.get("location_report_source")
        legacy_timestamp = supporting.get("location_reported_at")
        if legacy_source and legacy_timestamp:
            reports.setdefault(legacy_source, legacy_timestamp)
        report_text = ", ".join(
            f"{review_label(hass, source)} → {review_label(hass, sensor)}"
            for source, sensor in reports.items()
        )
        trackers = ", ".join(
            review_label(hass, tracker) for tracker in member[CONF_TRACKERS]
        )
        residences = ", ".join(
            review_label(hass, zone) for zone in member[CONF_RESIDENCES]
        )
        kind = (
            " (Pet tracker)"
            if person_id in draft.get(CONF_PETS, [])
            else " (Person tracker)"
            if person_id in draft.get(CONF_TRACKER_PEOPLE, [])
            else " (Pet)"
            if member.get("kind") == "pet"
            else ""
        )
        label = member.get(CONF_DISPLAY_NAME) or entity_label(hass, person_id)
        lines = [
            f"**{markdown_label(label)}{kind}**",
            f"- Trackers: {trackers or 'Person presence only'}",
            f"- Other homes: {residences or 'None'}",
            f"- Status sensors: {status or 'None mapped'}",
            f"- Location report times: {report_text or 'None mapped'}",
        ]
        if links := (pending_links or {}).get(person_id):
            lines.append(
                "- Will link to this HA Person: "
                + ", ".join(review_label(hass, tracker) for tracker in links)
            )
        if member.get("kind") == "pet":
            lines.append(
                "- Pet timing: "
                f"home {review_duration(member['pet_home_minutes'])}, "
                f"away {review_duration(member['pet_away_minutes'])}"
            )
        if member.get(CONF_SHOW_ON_MAP) is False:
            lines.append(
                "- Everyone map: marker hidden; selecting this member or a status "
                "category still shows their position. Member card and presence "
                "count remain."
            )
        current_member = current_members.get(person_id)
        if current_member and current_member.location is None:
            lines.append(
                f"- {position_guidance(hass, person_id, current_member, member)}"
            )
        elif current_member and current_member.location:
            source = current_member.location.evidence.source_entity
            lines.append(
                f"- {position_guidance(hass, person_id, current_member, member)}"
            )
            if reports and source not in reports:
                lines.append(
                    "- Current location report time: no sensor mapped for the "
                    f"source driving the map ({review_label(hass, source)})."
                )
        members.append("\n".join(lines))
    return {
        "primary_home": review_label(hass, draft[CONF_PRIMARY_HOME]),
        "places": places or "None",
        "members": "\n\n".join(members)
        or "No members selected yet. After connecting a tracker account, reopen Options when its trackers appear.",
    }


class SelectionFlow:
    """Shared draft editor; cancellation never modifies a config entry."""

    def start(self, config: dict[str, Any]) -> None:
        self.draft = deepcopy(dict(config))
        self.member_index = 0
        self.pending_connections = []
        self.single_edit = False
        self.remove_member_id = None
        self.remove_before_draft = None
        self.zone_return_step = None
        self.zone_household_prefill = None
        self.zone_member_prefill = None
        self.zone_created_hint = ""
        self.person_return_step = None
        self.person_household_prefill = None
        self.person_add_prefill = None
        self.add_tracker_person_id = None
        self.person_convert_prefill = None
        self.person_created_hint = ""
        self.pending_person_links = {}

    def member_ids(self) -> list[str]:
        return [
            *self.draft.get(CONF_PEOPLE, []),
            *self.draft.get(CONF_TRACKER_PEOPLE, []),
            *self.draft.get(CONF_PETS, []),
        ]

    async def async_step_household(self, user_input=None):
        errors = {}
        if user_input is not None and user_input.get("create_person"):
            self.person_return_step = "household"
            self.person_household_prefill = {
                key: value
                for key, value in user_input.items()
                if key != "create_person"
            }
            return await self.async_step_create_person()
        if user_input is not None and user_input.get("create_zone"):
            self.zone_return_step = "household"
            self.zone_household_prefill = {
                key: value for key, value in user_input.items() if key != "create_zone"
            }
            return await self.async_step_create_zone()
        if user_input is not None:
            if isinstance(self, HomeCircleOptionsFlow):
                shortcuts = [
                    key
                    for key in ("remove_tracker", "edit_member")
                    if user_input.get(key)
                ]
                changed_fields = (
                    CONF_PEOPLE,
                    CONF_TRACKER_PEOPLE,
                    CONF_PETS,
                    CONF_PRIMARY_HOME,
                    CONF_PLACES,
                    *(
                        provider.enabled_key
                        for provider in tracker_providers.TRACKER_PROVIDERS
                    ),
                    *(
                        provider.replace_key
                        for provider in tracker_providers.TRACKER_PROVIDERS
                    ),
                )
                empty_lists = {CONF_PEOPLE, CONF_TRACKER_PEOPLE, CONF_PETS, CONF_PLACES}
                if shortcuts and (
                    len(shortcuts) > 1
                    or any(
                        key in user_input
                        and user_input[key]
                        != self.draft.get(key, [] if key in empty_lists else False)
                        for key in changed_fields
                    )
                ):
                    errors["base"] = "shortcut_conflict"
                removed = user_input.get("remove_tracker")
                if removed and not errors:
                    selected = {
                        tracker
                        for member in self.draft[CONF_MEMBERS].values()
                        for tracker in member[CONF_TRACKERS]
                    }
                    if removed not in selected:
                        errors["remove_tracker"] = "invalid_entity"
                    else:
                        proposed = deepcopy(self.draft)
                        if removed in proposed.get(CONF_TRACKER_PEOPLE, []):
                            proposed[CONF_TRACKER_PEOPLE].remove(removed)
                            proposed[CONF_MEMBERS].pop(removed)
                        elif removed in proposed.get(CONF_PETS, []):
                            proposed[CONF_PETS].remove(removed)
                            proposed[CONF_MEMBERS].pop(removed)
                        else:
                            for member in proposed[CONF_MEMBERS].values():
                                if removed in member[CONF_TRACKERS]:
                                    member[CONF_TRACKERS].remove(removed)
                                    member.get("location_reports", {}).pop(
                                        removed, None
                                    )
                                    supporting = member.get("supporting", {})
                                    if (
                                        supporting.get("location_report_source")
                                        == removed
                                    ):
                                        supporting.pop("location_report_source", None)
                                        supporting.pop("location_reported_at", None)
                        household_issue = household_errors(self.hass, proposed)
                        if household_issue:
                            errors["remove_tracker"] = next(
                                iter(household_issue.values())
                            )
                        else:
                            self.draft = proposed
                            return await self.async_step_confirm()
                edit_member = user_input.get("edit_member")
                if edit_member:
                    if edit_member not in self.member_ids():
                        errors["edit_member"] = "invalid_entity"
                    elif not errors:
                        self.member_index = self.member_ids().index(edit_member)
                        self.single_edit = True
                        return await self.async_step_member()
        if user_input is not None and not errors:
            replace_keys = {
                provider.replace_key for provider in tracker_providers.TRACKER_PROVIDERS
            }
            shortcut_keys = {
                "remove_tracker",
                "edit_member",
                "create_person",
            }
            values = {
                **{
                    k: v
                    for k, v in user_input.items()
                    if k not in replace_keys | shortcut_keys
                },
                CONF_PEOPLE: user_input.get(CONF_PEOPLE, []),
                CONF_TRACKER_PEOPLE: user_input.get(
                    CONF_TRACKER_PEOPLE, self.draft.get(CONF_TRACKER_PEOPLE, [])
                ),
                CONF_PETS: user_input.get(CONF_PETS, self.draft.get(CONF_PETS, [])),
                CONF_PLACES: user_input.get(CONF_PLACES, []),
                **{
                    provider.enabled_key: bool(user_input.get(provider.enabled_key))
                    for provider in tracker_providers.TRACKER_PROVIDERS
                },
            }
            errors = household_errors(self.hass, values)
            if not errors:
                previous = self.draft.get(CONF_MEMBERS, {})
                saved_connections = {
                    provider.account_key: self.draft[provider.account_key]
                    for provider in tracker_providers.TRACKER_PROVIDERS
                    if values[provider.enabled_key]
                    and self.draft.get(provider.account_key)
                }
                self.draft = {
                    **values,
                    **saved_connections,
                    CONF_MEMBERS: {
                        person_id: previous[person_id]
                        for person_id in [
                            *values[CONF_PEOPLE],
                            *values[CONF_TRACKER_PEOPLE],
                            *values[CONF_PETS],
                        ]
                        if person_id in previous
                    },
                }
                self.zone_household_prefill = None
                self.zone_created_hint = ""
                self.person_household_prefill = None
                self.person_created_hint = ""
                self.member_index = 0
                self.pending_connections = [
                    provider
                    for provider in tracker_providers.TRACKER_PROVIDERS
                    if values[provider.enabled_key]
                    and (
                        not self.draft.get(provider.account_key)
                        or bool(user_input.get(provider.replace_key))
                    )
                ]
                return await self.async_step_next_connection()
        schema = vol.Schema(
            {
                **(
                    {
                        **(
                            {
                                vol.Optional("remove_tracker"): selector.SelectSelector(
                                    selector.SelectSelectorConfig(
                                        options=[
                                            {
                                                "value": tracker,
                                                "label": (
                                                    f"{self.draft[CONF_MEMBERS][tracker][CONF_DISPLAY_NAME]} ({tracker})"
                                                    if tracker
                                                    in self.draft[CONF_MEMBERS]
                                                    and self.draft[CONF_MEMBERS][
                                                        tracker
                                                    ].get(CONF_DISPLAY_NAME)
                                                    else entity_label(
                                                        self.hass, tracker
                                                    )
                                                ),
                                            }
                                            for tracker in dict.fromkeys(
                                                tracker
                                                for member in self.draft[
                                                    CONF_MEMBERS
                                                ].values()
                                                for tracker in member[CONF_TRACKERS]
                                            )
                                        ],
                                        custom_value=False,
                                        mode=selector.SelectSelectorMode.DROPDOWN,
                                    )
                                )
                            }
                            if any(
                                member[CONF_TRACKERS]
                                for member in self.draft[CONF_MEMBERS].values()
                            )
                            else {}
                        ),
                        **(
                            {
                                vol.Optional("edit_member"): selector.SelectSelector(
                                    selector.SelectSelectorConfig(
                                        options=[
                                            {
                                                "value": member_id,
                                                "label": self.draft[CONF_MEMBERS][
                                                    member_id
                                                ].get(CONF_DISPLAY_NAME)
                                                or entity_label(self.hass, member_id),
                                            }
                                            for member_id in self.member_ids()
                                        ],
                                        custom_value=False,
                                        mode=selector.SelectSelectorMode.DROPDOWN,
                                    )
                                )
                            }
                            if self.member_ids()
                            else {}
                        ),
                    }
                    if isinstance(self, HomeCircleOptionsFlow)
                    else {}
                ),
                vol.Optional(CONF_PEOPLE): entity_selector("person"),
                **(
                    {vol.Optional(CONF_TRACKER_PEOPLE): tracker_selector(self.hass)}
                    if self.draft.get(CONF_TRACKER_PEOPLE)
                    else {}
                ),
                **(
                    {vol.Optional(CONF_PETS): tracker_selector(self.hass)}
                    if self.draft.get(CONF_PETS)
                    else {}
                ),
                **{
                    vol.Optional(
                        provider.enabled_key,
                        default=bool(self.draft.get(provider.enabled_key)),
                    ): selector.BooleanSelector()
                    for provider in tracker_providers.TRACKER_PROVIDERS
                },
                **{
                    vol.Optional(
                        provider.replace_key, default=False
                    ): selector.BooleanSelector()
                    for provider in tracker_providers.TRACKER_PROVIDERS
                    if self.draft.get(provider.account_key)
                },
                (
                    vol.Optional(
                        CONF_PRIMARY_HOME, default=self.draft[CONF_PRIMARY_HOME]
                    )
                    if isinstance(self, HomeCircleOptionsFlow)
                    else vol.Required(CONF_PRIMARY_HOME)
                ): entity_selector("zone", False),
                vol.Optional(CONF_PLACES): entity_selector("zone"),
                vol.Optional("create_zone", default=False): selector.BooleanSelector(),
                vol.Optional(
                    "create_person", default=False
                ): selector.BooleanSelector(),
            }
        )
        entry = getattr(self, "config_entry", None)
        runtime = getattr(entry, "runtime_data", None)
        return self.async_show_form(
            step_id="household",
            data_schema=self.add_suggested_values_to_schema(
                schema,
                user_input
                if user_input is not None
                else self.person_household_prefill
                or self.zone_household_prefill
                or self.draft,
            ),
            errors=errors,
            description_placeholders={
                "tracker_status": tracker_providers.setup_status(
                    self.hass,
                    self.draft,
                    runtime.managed_trackers if runtime else None,
                ),
                "new_zone_hint": self.zone_created_hint,
                "new_person_hint": self.person_created_hint,
            },
        )

    async def async_step_create_zone(self, user_input=None):
        """Create a HA zone, then return to the interrupted selection form."""
        errors = {}
        if user_input is not None:
            name = user_input.get("name", "")
            location = user_input.get("location")
            if isinstance(location, dict):
                location = {"radius": 100, **location}
            use = user_input.get("use", "residence")
            error = zone_error(self.hass, name, location)
            if error:
                errors["name" if error != "invalid_zone_location" else "location"] = (
                    error
                )
            elif self.zone_return_step == "household" and use not in (
                "primary",
                "place",
                "residence",
            ):
                errors["use"] = "invalid_zone_use"
            else:
                zone_id = await async_create_zone(self.hass, name, location)
                if zone_id is None:
                    errors["base"] = "zone_creation_unavailable"
                elif self.zone_return_step == "member":
                    zone_label = markdown_label(name.strip())
                    prefill = self.zone_member_prefill or {}
                    prefill[CONF_RESIDENCES] = list(
                        dict.fromkeys([*prefill.get(CONF_RESIDENCES, []), zone_id])
                    )
                    self.zone_member_prefill = prefill
                    self.zone_created_hint = f"Created {zone_label} as another home."
                    self.zone_return_step = None
                    return await self.async_step_member()
                else:
                    zone_label = markdown_label(name.strip())
                    prefill = self.zone_household_prefill or deepcopy(self.draft)
                    if use == "primary":
                        prefill[CONF_PRIMARY_HOME] = zone_id
                        self.zone_created_hint = (
                            f"Created {zone_label} as primary home."
                        )
                    elif use == "place":
                        prefill[CONF_PLACES] = list(
                            dict.fromkeys([*prefill.get(CONF_PLACES, []), zone_id])
                        )
                        self.zone_created_hint = (
                            f"Created {zone_label} as a place label."
                        )
                    else:
                        self.zone_created_hint = (
                            f"Created {zone_label}. Select it under Other homes "
                            "for the member it belongs to."
                        )
                    self.zone_household_prefill = prefill
                    self.zone_return_step = None
                    return await self.async_step_household()
        fields = {
            vol.Required("name"): selector.TextSelector(),
            vol.Required("location"): selector.LocationSelector(
                selector.LocationSelectorConfig(radius=True)
            ),
        }
        if self.zone_return_step == "household":
            fields[vol.Required("use", default="place")] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "primary", "label": "Primary family home"},
                        {"value": "residence", "label": "Another home for a member"},
                        {"value": "place", "label": "Place shown while Away"},
                    ]
                )
            )
        return self.async_show_form(
            step_id="create_zone",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(fields),
                user_input
                if user_input is not None
                else {
                    "location": {
                        "latitude": self.hass.config.latitude,
                        "longitude": self.hass.config.longitude,
                        "radius": 100,
                    }
                },
            ),
            errors=errors,
        )

    async def async_step_create_person(self, user_input=None):
        """Create a storage-backed HA Person before assigning their tracker."""
        errors = {}
        if user_input is not None:
            name = user_input.get("name", "")
            error = person_name_error(self.hass, name)
            if error:
                errors["name"] = error
            else:
                person_id = await async_create_person(self.hass, name)
                if person_id is None:
                    errors["base"] = "person_creation_unavailable"
                else:
                    self.person_created_hint = f"Created {markdown_label(name.strip())} in Home Assistant People."
                    if self.person_return_step == "add_tracker_choice":
                        prefill = self.person_add_prefill or {}
                        prefill["person"] = person_id
                        self.person_add_prefill = prefill
                        self.person_return_step = None
                        return await self.async_step_add_tracker_choice()
                    if self.person_return_step == "convert_legacy_member":
                        prefill = self.person_convert_prefill or {}
                        prefill["person"] = person_id
                        self.person_convert_prefill = prefill
                        self.person_return_step = None
                        return await self.async_step_convert_legacy_member()
                    prefill = self.person_household_prefill or deepcopy(self.draft)
                    prefill[CONF_PEOPLE] = list(
                        dict.fromkeys([*prefill.get(CONF_PEOPLE, []), person_id])
                    )
                    self.person_household_prefill = prefill
                    self.person_return_step = None
                    return await self.async_step_household()
        return self.async_show_form(
            step_id="create_person",
            data_schema=vol.Schema({vol.Required("name"): selector.TextSelector()}),
            errors=errors,
        )

    async def async_step_next_connection(self):
        """Run each enabled provider's credential step before member setup."""
        if self.pending_connections:
            return await getattr(self, self.pending_connections[0].setup_step)()
        if not self.member_ids():
            return await self.async_step_confirm()
        return await self.open_member()

    async def open_member(self):
        """Assign a tracker before showing settings for a new HA Person."""
        person_id = self.member_ids()[self.member_index]
        if (
            person_id in self.draft.get(CONF_PEOPLE, [])
            and person_id not in self.draft[CONF_MEMBERS]
            and has_person_entity(self.hass, person_id)
        ):
            return await self.async_step_assign_tracker()
        return await self.async_step_member()

    async def async_step_assign_tracker(self, user_input=None):
        """Choose one tracker and stage its HA Person link until final save."""
        person_id = self.member_ids()[self.member_index]
        linked, active = person_tracker_references(self.hass, person_id)
        suggested, guidance = tracker_advice(self.hass, linked, active)
        errors = {}
        if user_input is not None:
            tracker_id = user_input.get("tracker")
            if not selectable(self.hass, tracker_id, "device_tracker"):
                errors["tracker"] = "invalid_entity"
            elif tracker_id in trackers_assigned_elsewhere(self.draft, person_id):
                errors["tracker"] = "duplicate_selection"
            elif tracker_id not in linked and (
                link_error := tracker_link_error(self.hass, person_id, tracker_id)
            ):
                errors["tracker"] = link_error
            if not errors:
                self.draft[CONF_MEMBERS][person_id] = {
                    CONF_TRACKERS: [tracker_id],
                    CONF_RESIDENCES: [],
                    "kind": "person",
                    "pet_home_minutes": 1440,
                    "pet_away_minutes": 5,
                }
                self.pending_person_links[person_id] = (
                    [] if tracker_id in linked else [tracker_id]
                )
                return await self.async_step_member()
        return self.async_show_form(
            step_id="assign_tracker",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {vol.Required("tracker"): entity_selector("device_tracker", False)}
                ),
                user_input if user_input is not None else {"tracker": suggested},
            ),
            errors=errors,
            description_placeholders={
                "person": entity_label(self.hass, person_id),
                "tracker_guidance": guidance,
            },
        )

    async def connection_saved(self, provider_id: str, account: dict[str, str]):
        """A provider form commits only to the in-progress draft."""
        if (
            not self.pending_connections
            or self.pending_connections[0].id != provider_id
        ):
            raise ValueError("Unexpected tracker provider setup step")
        provider = self.pending_connections.pop(0)
        self.draft[provider.account_key] = account
        return await self.async_step_next_connection()

    async def async_step_life360_account(self, user_input=None):
        """Verify an optional account before saving it in HA's config entry."""
        errors = {}
        previous = self.draft.get(CONF_LIFE360_ACCOUNT, {})
        legacy_replacement = bool(previous and not previous.get("account_id_hash"))
        if user_input is not None:
            account, error = await checked_life360_account(user_input)
            if not error:
                error = await life360_continuity_error(
                    previous,
                    account,
                    bool(user_input.get(CONFIRM_SAME_ACCOUNT)),
                )
            if error:
                errors[
                    CONFIRM_SAME_ACCOUNT
                    if error == "same_account_confirmation_required"
                    else "base"
                ] = error
            else:
                return await self.connection_saved("life360", account)
        return self.async_show_form(
            step_id="life360_account",
            data_schema=life360_account_schema(legacy_replacement=legacy_replacement),
            errors=errors,
        )

    async def async_step_member(self, user_input=None):
        person_id = self.member_ids()[self.member_index]
        if user_input is not None and user_input.get("create_zone"):
            self.zone_return_step = "member"
            self.zone_member_prefill = {
                key: value for key, value in user_input.items() if key != "create_zone"
            }
            return await self.async_step_create_zone()
        tracker_only_member = person_id in [
            *self.draft.get(CONF_TRACKER_PEOPLE, []),
            *self.draft.get(CONF_PETS, []),
        ]
        tracker_only_pet = person_id in self.draft.get(CONF_PETS, [])
        if tracker_only_member:
            active = suggested = person_id
            guidance = "This member uses the selected Home Assistant tracker directly."
        else:
            associated, active = tracker_suggestions(self.hass, person_id)
            suggested, guidance = tracker_advice(self.hass, associated, active)
        errors = {}
        if user_input is not None:
            previous = self.draft[CONF_MEMBERS].get(person_id, {})
            values = {
                CONF_TRACKERS: [person_id]
                if tracker_only_member
                else user_input.get(
                    CONF_TRACKERS,
                    previous.get(CONF_TRACKERS, [])
                    if person_id in self.pending_person_links
                    else [],
                ),
                CONF_RESIDENCES: user_input.get(CONF_RESIDENCES, []),
            }
            values.update(
                kind=(
                    "pet"
                    if tracker_only_pet
                    else "person"
                    if tracker_only_member
                    else user_input.get("kind", previous.get("kind", "person"))
                ),
                pet_home_minutes=previous.get("pet_home_minutes", 1440),
                pet_away_minutes=previous.get("pet_away_minutes", 5),
            )
            if (
                user_input.get(CONF_SHOW_ON_MAP, previous.get(CONF_SHOW_ON_MAP, True))
                is False
            ):
                values[CONF_SHOW_ON_MAP] = False
            if user_input.get(CONF_AUTO_REQUEST_LOCATION, False) is True:
                values[CONF_AUTO_REQUEST_LOCATION] = True
            if tracker_only_member:
                name = user_input.get(CONF_DISPLAY_NAME)
                if isinstance(name, str) and name.strip():
                    values[CONF_DISPLAY_NAME] = name.strip()
                elif name is not None and not isinstance(name, str):
                    values[CONF_DISPLAY_NAME] = name
            previous_reports = previous.get("location_reports", {})
            if previous_reports:
                values["location_reports"] = deepcopy(previous_reports)
            previous_supporting = previous.get("supporting") or {}
            self.edit_reports = (
                user_input.get("configure_reports", False)
                or bool(set(previous_reports) - {person_id, *values[CONF_TRACKERS]})
                or any(previous_supporting.get(key) for key in LEGACY_REPORT_KEYS)
            )
            if previous_supporting:
                values["supporting"] = previous_supporting
            # The supporting step can repair mappings after tracker changes.
            errors = member_errors(
                self.hass,
                {
                    k: v
                    for k, v in values.items()
                    if k not in ("supporting", "location_reports")
                },
                self.draft[CONF_PRIMARY_HOME],
                person_id,
            )
            if set(values[CONF_TRACKERS]) & trackers_assigned_elsewhere(
                self.draft, person_id
            ):
                errors["base" if tracker_only_member else CONF_TRACKERS] = (
                    "duplicate_selection"
                )
            if person_id in self.draft.get(CONF_PEOPLE, []) and has_person_entity(
                self.hass, person_id
            ):
                if (
                    not values[CONF_TRACKERS]
                    and not previous
                    and self.source == config_entries.SOURCE_USER
                ):
                    errors[CONF_TRACKERS] = "tracker_required"
            if not errors:
                self.draft[CONF_MEMBERS][person_id] = values
                # Details changes only HomeCircle's selection. Retain links
                # explicitly requested by Assign/Add, unless deselected here.
                if person_id in self.pending_person_links:
                    self.pending_person_links[person_id] = [
                        tracker
                        for tracker in self.pending_person_links[person_id]
                        if tracker in values[CONF_TRACKERS]
                    ]
                self.zone_member_prefill = None
                self.zone_created_hint = ""
                self.edit_sensors = bool(user_input.get("configure_sensors")) or bool(
                    supporting_errors(
                        self.hass,
                        {
                            key: previous_supporting[key]
                            for key in STATUS_SENSOR_KEYS
                            if key in previous_supporting
                        },
                        person_id,
                        values[CONF_TRACKERS],
                    )
                )
                self.edit_timing = bool(user_input.get("configure_timing")) or (
                    values["kind"] == "pet" and previous.get("kind") != "pet"
                )
                if values["kind"] == "pet" and self.edit_timing:
                    return await self.async_step_pet_freshness()
                return await self.after_member()
        defaults = {
            **self.draft[CONF_MEMBERS].get(
                person_id,
                {
                    CONF_TRACKERS: [suggested] if suggested else [],
                    CONF_RESIDENCES: [],
                },
            ),
            **(self.zone_member_prefill or {}),
        }
        position = current_position(
            self.hass,
            self.draft,
            person_id,
            values if user_input is not None else defaults,
        )
        fields = {vol.Optional(CONF_RESIDENCES): entity_selector("zone")}
        if not tracker_only_member:
            fields = {
                vol.Optional(CONF_TRACKERS): tracker_selector(self.hass),
                **fields,
                vol.Optional(
                    "kind", default=defaults.get("kind", "person")
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "person", "label": "Person"},
                            {"value": "pet", "label": "Pet"},
                        ]
                    )
                ),
            }
        else:
            fields = {
                vol.Optional(CONF_DISPLAY_NAME): selector.TextSelector(),
                **fields,
            }
        if tracker_only_pet or defaults.get("kind") == "pet":
            fields[vol.Optional("configure_timing", default=False)] = (
                selector.BooleanSelector()
            )
        fields.update(
            {
                vol.Optional(
                    CONF_SHOW_ON_MAP, default=True
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_AUTO_REQUEST_LOCATION,
                    default=defaults.get(CONF_AUTO_REQUEST_LOCATION, False),
                ): selector.BooleanSelector(),
                vol.Optional(
                    "configure_sensors", default=False
                ): selector.BooleanSelector(),
                vol.Optional(
                    "configure_reports", default=False
                ): selector.BooleanSelector(),
                vol.Optional("create_zone", default=False): selector.BooleanSelector(),
            }
        )
        schema = vol.Schema(fields)
        return self.async_show_form(
            step_id=(
                "pet_member"
                if tracker_only_pet
                else "tracker_member"
                if tracker_only_member
                else "member"
            ),
            errors=errors,
            data_schema=self.add_suggested_values_to_schema(
                schema,
                user_input if user_input is not None else defaults,
            ),
            description_placeholders={
                "person": entity_label(self.hass, person_id),
                "number": str(self.member_index + 1),
                "total": str(len(self.member_ids())),
                "active": entity_label(self.hass, active),
                "tracker_guidance": guidance,
                "position_guidance": position_guidance(
                    self.hass,
                    person_id,
                    position,
                    values if user_input is not None else defaults,
                ),
                "new_zone_hint": self.zone_created_hint,
            },
        )

    async def async_step_pet_member(self, user_input=None):
        """Use the tracker selected for this pet as its sole location source."""
        return await self.async_step_member(user_input)

    async def async_step_tracker_member(self, user_input=None):
        """Use the selected tracker for a person without a Person record."""
        return await self.async_step_member(user_input)

    async def async_step_pet_freshness(self, user_input=None):
        person_id = self.member_ids()[self.member_index]
        member = self.draft[CONF_MEMBERS][person_id]
        errors = {}
        if user_input is not None:
            values = {
                key: user_input.get(key, member[key])
                for key in ("pet_home_minutes", "pet_away_minutes")
            }
            errors = member_errors(self.hass, values, self.draft[CONF_PRIMARY_HOME])
            if not errors:
                member.update(values)
                return await self.after_member()
        schema = vol.Schema(
            {
                vol.Optional(
                    key, default=member.get(key, default)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=10080, step=1, mode="box", unit_of_measurement="min"
                    )
                )
                for key, default in (
                    ("pet_home_minutes", 1440),
                    ("pet_away_minutes", 5),
                )
            }
        )
        return self.async_show_form(
            step_id="pet_freshness",
            errors=errors,
            data_schema=self.add_suggested_values_to_schema(
                schema, user_input if user_input is not None else member
            ),
            description_placeholders={"person": entity_label(self.hass, person_id)},
        )

    async def after_member(self):
        if self.edit_sensors:
            self.edit_sensors = False
            return await self.async_step_supporting()
        return await self.next_member()

    async def next_member(self):
        if getattr(self, "edit_reports", False):
            self.edit_reports = False
            member_id = self.member_ids()[self.member_index]
            member = self.draft[CONF_MEMBERS][member_id]
            reports = member.setdefault("location_reports", {})
            supporting = member.get("supporting", {})
            source = supporting.pop("location_report_source", None)
            timestamp = supporting.pop("location_reported_at", None)
            if source and timestamp:
                reports.setdefault(source, timestamp)
            if not supporting:
                member.pop("supporting", None)
            current = current_position(self.hass, self.draft, member_id, member)
            effective = (
                current.location.evidence.source_entity if current.location else None
            )
            trackers = member[CONF_TRACKERS]
            self.report_sources = list(
                dict.fromkeys(
                    [
                        *([effective] if effective else []),
                        *(
                            item
                            for item in trackers
                            if member_id.startswith("device_tracker.")
                            or (state := self.hass.states.get(item)) is None
                            or state.state in ("unknown", "unavailable")
                            or state.attributes.get("source_type") == "gps"
                        ),
                        *reports,
                    ]
                )
            )
            self.report_index = 0
            self.report_effective = effective
            if not self.report_sources:
                return await self.async_step_no_report_sources()
            return await self.async_step_source_report()
        if self.single_edit:
            self.single_edit = False
            return await self.async_step_confirm()
        self.member_index += 1
        if self.member_index < len(self.member_ids()):
            return await self.open_member()
        return await self.async_step_confirm()

    async def async_step_no_report_sources(self, user_input=None):
        """Explain why a requested report-time step has no usable source."""
        if user_input is not None:
            return await self.next_member()
        return self.async_show_form(
            step_id="no_report_sources", data_schema=vol.Schema({})
        )

    async def async_step_source_report(self, user_input=None):
        person = self.member_ids()[self.member_index]
        member = self.draft[CONF_MEMBERS][person]
        source = self.report_sources[self.report_index]
        reports = member["location_reports"]
        errors = {}
        if user_input is not None:
            timestamp = user_input.get("timestamp")
            if timestamp and source not in [person, *member[CONF_TRACKERS]]:
                errors["timestamp"] = "invalid_report_source"
            elif timestamp and not selectable(self.hass, timestamp, "sensor"):
                errors["timestamp"] = "invalid_entity"
            else:
                if timestamp:
                    reports[source] = timestamp
                else:
                    reports.pop(source, None)
                self.report_index += 1
                if self.report_index == len(self.report_sources):
                    return await self.next_member()
                return await self.async_step_source_report()
        return self.async_show_form(
            step_id="source_report",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {vol.Optional("timestamp"): entity_selector("sensor", False)}
                ),
                user_input
                if user_input is not None
                else {"timestamp": reports.get(source)},
            ),
            errors=errors,
            description_placeholders={
                "source": entity_label(self.hass, source),
                "number": str(self.report_index + 1),
                "total": str(len(self.report_sources)),
                "purpose": (
                    "Current map source"
                    if source == self.report_effective
                    else "Home Assistant Person mapping, used when the Person drives the map"
                    if source == person and person in self.draft.get(CONF_PEOPLE, [])
                    else "Selected tracker mapping, used only if this tracker drives the map"
                    if source in member[CONF_TRACKERS]
                    else "Removed source mapping; leave empty to clear it"
                ),
            },
        )

    async def async_step_supporting(self, user_input=None):
        person_id = self.member_ids()[self.member_index]
        member = self.draft[CONF_MEMBERS][person_id]
        errors = {}
        if user_input is not None:
            values = {key: value for key, value in user_input.items() if value}
            errors = supporting_errors(
                self.hass, values, person_id, member[CONF_TRACKERS]
            )
            if not errors:
                legacy = {
                    key: member.get("supporting", {})[key]
                    for key in LEGACY_REPORT_KEYS
                    if key in member.get("supporting", {})
                }
                if values or legacy:
                    member["supporting"] = {**legacy, **values}
                else:
                    member.pop("supporting", None)
                return await self.next_member()
        schema = vol.Schema(
            {
                vol.Optional(key): (
                    battery_selector(
                        self.hass, member.get("supporting", {}).get("battery")
                    )
                    if key == "battery"
                    else entity_selector(SUPPORTING_DOMAINS[key], False)
                )
                for key in STATUS_SENSOR_KEYS
            }
        )
        return self.async_show_form(
            step_id="supporting",
            errors=errors,
            description_placeholders={"person": entity_label(self.hass, person_id)},
            data_schema=self.add_suggested_values_to_schema(
                schema,
                user_input if user_input is not None else member.get("supporting", {}),
            ),
        )

    async def async_step_confirm(self, user_input=None):
        return self.async_show_menu(
            step_id="confirm_remove"
            if self.remove_before_draft is not None
            else "confirm",
            menu_options=(
                ["confirm_back_remove", "confirm_save"]
                if self.remove_before_draft is not None
                else ["confirm_back", "confirm_edit_member", "confirm_save"]
            ),
            description_placeholders=review_summary(
                self.hass, self.draft, self.pending_person_links
            ),
        )

    async def async_step_confirm_remove(self, user_input=None):
        return await self.async_step_confirm()

    async def async_step_confirm_back_remove(self, user_input=None):
        """Cancel a scoped removal and show that member's tracker choices again."""
        if self.remove_before_draft is None:
            return await self.async_step_confirm()
        self.draft = self.remove_before_draft
        self.remove_before_draft = None
        return await self.async_step_remove_tracker_choice()

    async def async_step_confirm_back(self, user_input=None):
        """Revisit the most recent member without discarding any selections."""
        if not self.member_ids():
            return await self.async_step_household()
        self.member_index = len(self.member_ids()) - 1
        self.single_edit = True
        return await self.async_step_member()

    async def async_step_confirm_edit_member(self, user_input=None):
        """Jump to one member and return to review after editing it."""
        if user_input is not None:
            member_id = user_input.get("member")
            if member_id in self.member_ids():
                self.member_index = self.member_ids().index(member_id)
                self.single_edit = True
                return await self.async_step_member()
        return self.async_show_form(
            step_id="confirm_edit_member",
            data_schema=vol.Schema(
                {
                    vol.Required("member"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {
                                    "value": member_id,
                                    "label": self.draft[CONF_MEMBERS][member_id].get(
                                        CONF_DISPLAY_NAME
                                    )
                                    or entity_label(self.hass, member_id),
                                }
                                for member_id in self.member_ids()
                            ],
                            custom_value=False,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            errors={"member": "invalid_entity"} if user_input is not None else {},
        )

    async def async_step_confirm_save(self, user_input=None):
        """Validate the final draft before persisting it."""
        dependencies = selected_entities(self.draft)
        for person_id in self.draft.get(CONF_PEOPLE, []):
            linked, active = person_tracker_references(self.hass, person_id)
            dependencies.update(linked)
            if active:
                dependencies.add(active)
        if disconnected_owned_entities(
            er.async_get(self.hass), self.draft, dependencies
        ):
            result = await self.async_step_household()
            result["errors"] = {"base": "direct_trackers_selected"}
            return result
        # Recheck every selection: sources can disappear during a long flow.
        invalid = household_errors(self.hass, self.draft) or any(
            member_errors(self.hass, member, self.draft[CONF_PRIMARY_HOME], person_id)
            or bool(
                set(member[CONF_TRACKERS])
                & trackers_assigned_elsewhere(self.draft, person_id)
            )
            for person_id, member in self.draft[CONF_MEMBERS].items()
        )
        if invalid:
            result = await self.async_step_household()
            result["errors"] = {"base": "entities_changed"}
            return result
        for person_id, trackers in self.pending_person_links.items():
            for tracker_id in trackers:
                if link_error := tracker_link_error(self.hass, person_id, tracker_id):
                    result = await self.async_step_household()
                    result["errors"] = {"base": link_error}
                    return result
        for person_id, trackers in self.pending_person_links.items():
            for tracker_id in trackers:
                await async_link_tracker(self.hass, person_id, tracker_id)
        return self.save()


class HomeCircleConfigFlow(SelectionFlow, config_entries.ConfigFlow, domain=DOMAIN):
    """One household per HA instance; use options to edit it."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        self.start({CONF_PRIMARY_HOME: "zone.home"})
        return await self.async_step_household(user_input)

    async def async_step_reconfigure(self, user_input=None):
        entry = self._get_reconfigure_entry()
        self.start(entry.options or entry.data)
        return await self.async_step_household(user_input)

    async def async_step_reauth(self, entry_data):
        """Route an authorization failure to its registered tracker provider."""
        entry = self._get_reauth_entry()
        self.reauth_provider = tracker_providers.reauth_provider(
            dict(entry.options or entry.data),
            entry_data.get(tracker_providers.REAUTH_PROVIDER_KEY),
        )
        if self.reauth_provider is None:
            return self.async_abort(reason="provider_reauth_unavailable")
        return await getattr(self, self.reauth_provider.reauth_step)()

    async def async_step_reauth_confirm(self, user_input=None):
        errors = {}
        entry = self._get_reauth_entry()
        previous = (entry.options or entry.data).get(
            self.reauth_provider.account_key, {}
        )
        legacy_replacement = bool(previous and not previous.get("account_id_hash"))
        if user_input is not None:
            account, error = await checked_life360_account(user_input)
            if not error:
                error = await life360_continuity_error(
                    previous,
                    account,
                    bool(user_input.get(CONFIRM_SAME_ACCOUNT)),
                    verify_old=False,
                )
            if error:
                errors[
                    CONFIRM_SAME_ACCOUNT
                    if error == "same_account_confirmation_required"
                    else "base"
                ] = error
            else:
                account_key = self.reauth_provider.account_key
                data = {**entry.data, account_key: account}
                options = (
                    {**entry.options, account_key: account} if entry.options else {}
                )
                frontend.preserve_for_reload(self.hass, entry.entry_id)
                return self.async_update_reload_and_abort(
                    entry, data=data, options=options
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=life360_account_schema(legacy_replacement=legacy_replacement),
            errors=errors,
        )

    @callback
    def save(self):
        if self.source == config_entries.SOURCE_RECONFIGURE:
            entry = self._get_reconfigure_entry()
            # HA reloads after Reconfigure even when the saved selection is identical.
            frontend.preserve_for_reload(self.hass, entry.entry_id)
            return self.async_update_reload_and_abort(
                entry,
                data=self.draft,
                options={},
            )
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="HomeCircle", data=self.draft)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return HomeCircleOptionsFlow()


class HomeCircleOptionsFlow(SelectionFlow, config_entries.OptionsFlowWithReload):
    """Persist a complete selection snapshot; reload only after saving."""

    async def async_step_init(self, user_input=None):
        self.start(self.config_entry.options or self.config_entry.data)
        menu_options = ["add_tracker_choice", "household"]
        if self.member_ids():
            menu_options.insert(0, "tracker_member_choice")
        if self.draft.get(CONF_TRACKER_PEOPLE) or self.draft.get(CONF_PETS):
            menu_options.insert(-1, "convert_legacy_member")
        return self.async_show_menu(
            step_id="init",
            menu_options=menu_options,
        )

    async def async_step_tracker_member_choice(self, user_input=None):
        """Choose a person or tracker and the settings to open."""
        if user_input is not None:
            member_id = user_input.get("member")
            setting = user_input.get("setting")
            if member_id in self.member_ids() and setting in (
                "details",
                "sensors",
                "remove",
            ):
                self.member_index = self.member_ids().index(member_id)
                self.single_edit = True
                if setting == "details":
                    return await self.async_step_member()
                if setting == "remove":
                    if not self.draft[CONF_MEMBERS][member_id][CONF_TRACKERS]:
                        return self.async_show_form(
                            step_id="tracker_member_choice",
                            data_schema=self.tracker_member_settings_schema(),
                            errors={"setting": "no_trackers"},
                            description_placeholders={
                                "removable_members": self.removable_member_ids()
                            },
                        )
                    self.remove_member_id = member_id
                    return await self.async_step_remove_tracker_choice()
                return await self.async_step_supporting()
        return self.async_show_form(
            step_id="tracker_member_choice",
            data_schema=self.tracker_member_settings_schema(),
            errors={"base": "invalid_entity"} if user_input is not None else {},
            description_placeholders={"removable_members": self.removable_member_ids()},
        )

    def removable_member_ids(self):
        return ",".join(
            member_id
            for member_id in self.member_ids()
            if self.draft[CONF_MEMBERS][member_id][CONF_TRACKERS]
        )

    def tracker_member_settings_schema(self):
        return vol.Schema(
            {
                **self.member_choice_schema().schema,
                vol.Required("setting"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {
                                "value": "details",
                                "label": "Details, homes, and map visibility",
                            },
                            {"value": "sensors", "label": "Battery and status sensors"},
                            {"value": "remove", "label": "Remove a tracker"},
                        ],
                        custom_value=False,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )

    def member_choice_schema(self):
        return vol.Schema(
            {
                vol.Required("member"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {
                                "value": member_id,
                                "label": self.draft[CONF_MEMBERS][member_id].get(
                                    CONF_DISPLAY_NAME
                                )
                                or entity_label(self.hass, member_id),
                            }
                            for member_id in self.member_ids()
                        ],
                        custom_value=False,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )

    async def async_step_status_member(self, user_input=None):
        """Open battery and motion sensors without unrelated household fields."""
        if user_input is not None:
            member_id = user_input.get("member")
            if member_id in self.member_ids():
                self.member_index = self.member_ids().index(member_id)
                self.single_edit = True
                return await self.async_step_supporting()
        return self.async_show_form(
            step_id="status_member",
            data_schema=self.member_choice_schema(),
            errors={"member": "invalid_entity"} if user_input is not None else {},
        )

    async def async_step_edit_member_choice(self, user_input=None):
        if user_input is not None:
            member_id = user_input.get("member")
            if member_id in self.member_ids():
                self.member_index = self.member_ids().index(member_id)
                self.single_edit = True
                return await self.async_step_member()
        return self.async_show_form(
            step_id="edit_member_choice",
            data_schema=self.member_choice_schema(),
            errors={"member": "invalid_entity"} if user_input is not None else {},
        )

    async def async_step_add_tracker_choice(self, user_input=None):
        errors = {}
        if user_input is not None and user_input.get("create_person"):
            self.person_return_step = "add_tracker_choice"
            self.person_add_prefill = {
                key: value
                for key, value in user_input.items()
                if key != "create_person"
            }
            return await self.async_step_create_person()
        if user_input is not None:
            person_id = user_input.get("person")
            if not selectable(self.hass, person_id, "person"):
                errors["person"] = "invalid_entity"
            if not errors:
                self.add_tracker_person_id = person_id
                self.person_add_prefill = None
                return await self.async_step_add_tracker_assign()
        return self.async_show_form(
            step_id="add_tracker_choice",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Optional("person"): entity_selector("person", False),
                        vol.Optional(
                            "create_person", default=False
                        ): selector.BooleanSelector(),
                    }
                ),
                user_input if user_input is not None else self.person_add_prefill or {},
            ),
            errors=errors,
            description_placeholders={"new_person_hint": self.person_created_hint},
        )

    async def async_step_add_tracker_assign(self, user_input=None):
        """Choose a tracker only after an HA Person has been selected."""
        person_id = self.add_tracker_person_id
        if not selectable(self.hass, person_id, "person"):
            return await self.async_step_add_tracker_choice()
        errors = {}
        if user_input is not None:
            tracker_id = user_input.get("add_tracker")
            kind = user_input.get("add_tracker_kind", "person")
            if not selectable(self.hass, tracker_id, "device_tracker"):
                errors["add_tracker"] = "invalid_entity"
            if kind not in ("person", "pet"):
                errors["add_tracker_kind"] = "invalid_kind"
            if tracker_id in trackers_assigned_elsewhere(self.draft, person_id):
                errors["add_tracker"] = "duplicate_selection"
            if not errors and (
                link_error := tracker_link_error(self.hass, person_id, tracker_id)
            ):
                errors["add_tracker"] = link_error
            if not errors:
                if person_id not in self.draft[CONF_PEOPLE]:
                    self.draft[CONF_PEOPLE].append(person_id)
                previous = self.draft[CONF_MEMBERS].get(person_id, {})
                self.draft[CONF_MEMBERS][person_id] = {
                    **previous,
                    CONF_TRACKERS: list(
                        dict.fromkeys([*previous.get(CONF_TRACKERS, []), tracker_id])
                    ),
                    CONF_RESIDENCES: previous.get(CONF_RESIDENCES, []),
                    "kind": previous.get("kind", kind),
                    "pet_home_minutes": previous.get("pet_home_minutes", 1440),
                    "pet_away_minutes": previous.get("pet_away_minutes", 5),
                }
                self.pending_person_links.setdefault(person_id, []).append(tracker_id)
                self.member_index = self.member_ids().index(person_id)
                self.single_edit = True
                self.person_add_prefill = None
                return await self.async_step_member()
        return self.async_show_form(
            step_id="add_tracker_assign",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required("add_tracker"): entity_selector(
                            "device_tracker", False
                        ),
                        vol.Required(
                            "add_tracker_kind", default="person"
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=[
                                    {"value": "person", "label": "Person"},
                                    {"value": "pet", "label": "Pet"},
                                ]
                            )
                        ),
                    }
                ),
                user_input or {},
            ),
            errors=errors,
            description_placeholders={"person": entity_label(self.hass, person_id)},
        )

    async def async_step_convert_legacy_member(self, user_input=None):
        """Move a saved tracker-only member to an HA Person without losing settings."""
        legacy = [
            *self.draft.get(CONF_TRACKER_PEOPLE, []),
            *self.draft.get(CONF_PETS, []),
        ]
        errors = {}
        if user_input is not None and user_input.get("create_person"):
            self.person_return_step = "convert_legacy_member"
            self.person_convert_prefill = {
                key: value
                for key, value in user_input.items()
                if key != "create_person"
            }
            return await self.async_step_create_person()
        if user_input is not None:
            tracker_id = user_input.get("legacy_tracker")
            person_id = user_input.get("person")
            if tracker_id not in legacy:
                errors["legacy_tracker"] = "invalid_entity"
            if not selectable(self.hass, person_id, "person"):
                errors["person"] = "invalid_entity"
            elif person_id in self.member_ids():
                errors["person"] = "duplicate_selection"
            if not errors and (
                link_error := tracker_link_error(self.hass, person_id, tracker_id)
            ):
                errors["person"] = link_error
            if not errors:
                self.draft[CONF_TRACKER_PEOPLE] = [
                    item
                    for item in self.draft.get(CONF_TRACKER_PEOPLE, [])
                    if item != tracker_id
                ]
                self.draft[CONF_PETS] = [
                    item for item in self.draft.get(CONF_PETS, []) if item != tracker_id
                ]
                self.draft[CONF_PEOPLE].append(person_id)
                self.draft[CONF_MEMBERS][person_id] = self.draft[CONF_MEMBERS].pop(
                    tracker_id
                )
                self.pending_person_links[person_id] = [tracker_id]
                self.member_index = self.member_ids().index(person_id)
                self.single_edit = True
                self.person_convert_prefill = None
                return await self.async_step_member()
        return self.async_show_form(
            step_id="convert_legacy_member",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Optional("person"): entity_selector("person", False),
                        vol.Optional(
                            "create_person", default=False
                        ): selector.BooleanSelector(),
                        vol.Optional("legacy_tracker"): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=[
                                    {
                                        "value": item,
                                        "label": entity_label(self.hass, item),
                                    }
                                    for item in legacy
                                ],
                                mode=selector.SelectSelectorMode.DROPDOWN,
                            )
                        ),
                    }
                ),
                user_input
                if user_input is not None
                else self.person_convert_prefill or {},
            ),
            errors=errors,
            description_placeholders={"new_person_hint": self.person_created_hint},
        )

    async def async_step_remove_tracker_choice(self, user_input=None):
        member_id = self.remove_member_id
        member_trackers = (
            self.draft[CONF_MEMBERS][member_id][CONF_TRACKERS]
            if member_id in self.draft[CONF_MEMBERS]
            else None
        )
        if user_input is not None:
            if (
                member_trackers is not None
                and user_input.get("remove_tracker") not in member_trackers
            ):
                errors = {"remove_tracker": "invalid_entity"}
            else:
                previous_draft = deepcopy(self.draft)
                result = await self.async_step_household(user_input)
                if result["step_id"] != "household":
                    if (
                        self.remove_member_id is not None
                        and result["step_id"] == "confirm"
                    ):
                        self.remove_before_draft = previous_draft
                        return await self.async_step_confirm()
                    return result
                errors = {
                    key: value
                    for key, value in result.get("errors", {}).items()
                    if key in ("base", "remove_tracker")
                }
        else:
            errors = {}
        selected = (
            list(member_trackers)
            if member_trackers is not None
            else list(
                dict.fromkeys(
                    tracker
                    for member in self.draft[CONF_MEMBERS].values()
                    for tracker in member[CONF_TRACKERS]
                )
            )
        )
        return self.async_show_form(
            step_id="remove_tracker_choice",
            data_schema=vol.Schema(
                {
                    vol.Required("remove_tracker"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {
                                    "value": tracker,
                                    "label": (
                                        f"{self.draft[CONF_MEMBERS][tracker][CONF_DISPLAY_NAME]} ({tracker})"
                                        if tracker in self.draft[CONF_MEMBERS]
                                        and self.draft[CONF_MEMBERS][tracker].get(
                                            CONF_DISPLAY_NAME
                                        )
                                        else entity_label(self.hass, tracker)
                                    ),
                                }
                                for tracker in selected
                            ],
                            custom_value=False,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            errors=errors,
        )

    @callback
    def save(self):
        if self.draft != dict(self.config_entry.options):
            frontend.preserve_for_reload(self.hass, self.config_entry.entry_id)
        # Options hold the effective snapshot. Keep entry.data free of old
        # credentials after a replacement or disconnect as well.
        data = dict(self.config_entry.data)
        for provider in tracker_providers.TRACKER_PROVIDERS:
            if provider.account_key in self.draft:
                data[provider.account_key] = self.draft[provider.account_key]
            else:
                data.pop(provider.account_key, None)
        if data != dict(self.config_entry.data):
            self.hass.config_entries.async_update_entry(self.config_entry, data=data)
        return self.async_create_entry(title="", data=self.draft)
