"""Atomic, provider-independent household configuration through HA selectors."""

from copy import deepcopy
from collections import Counter
import re
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_MEMBERS,
    CONF_PEOPLE,
    CONF_PLACES,
    CONF_PRIMARY_HOME,
    CONF_RESIDENCES,
    CONF_TRACKERS,
)
from .selection import (
    SUPPORTING_DOMAINS,
    household_errors,
    member_errors,
    supporting_errors,
    tracker_suggestions,
    selectable,
)
from . import frontend


def entity_selector(domain: str, multiple: bool = True):
    return selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain=domain,
            multiple=multiple,
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


def review_label(hass, entity_id: str) -> str:
    """Keep names on one line and prevent entity names from shaping Markdown."""
    label = " ".join(entity_label(hass, entity_id).split())
    return re.sub(r"([\\`*_{}\[\]<>])", r"\\\1", label)


def tracker_advice(hass, associated: list[str], active: str | None) -> tuple[str | None, str]:
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


def review_summary(hass, draft: dict[str, Any]) -> dict[str, str]:
    """Describe the exact unsaved household selections in the final form."""
    places = ", ".join(review_label(hass, place) for place in draft[CONF_PLACES])
    members = []
    for person_id in draft[CONF_PEOPLE]:
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
        kind = " (Pet)" if member.get("kind") == "pet" else ""
        lines = [
            f"**{review_label(hass, person_id)}{kind}**",
            f"- Trackers: {trackers or 'Person presence only'}",
            f"- Other homes: {residences or 'None'}",
            f"- Status sensors: {status or 'None mapped'}",
            f"- Location report times: {report_text or 'None mapped'}",
        ]
        if kind:
            lines.append(
                "- Pet timing: "
                f"home {review_duration(member['pet_home_minutes'])}, "
                f"away {review_duration(member['pet_away_minutes'])}"
            )
        members.append("\n".join(lines))
    return {
        "primary_home": review_label(hass, draft[CONF_PRIMARY_HOME]),
        "places": places or "None",
        "members": "\n\n".join(members),
    }


class SelectionFlow:
    """Shared draft editor; cancellation never modifies a config entry."""

    def start(self, config: dict[str, Any]) -> None:
        self.draft = deepcopy(dict(config))
        self.member_index = 0

    async def async_step_household(self, user_input=None):
        errors = {}
        if user_input is not None:
            values = {**user_input, CONF_PLACES: user_input.get(CONF_PLACES, [])}
            errors = household_errors(self.hass, values)
            if not errors:
                previous = self.draft.get(CONF_MEMBERS, {})
                self.draft = {
                    **values,
                    CONF_MEMBERS: {
                        person_id: previous[person_id]
                        for person_id in values[CONF_PEOPLE]
                        if person_id in previous
                    },
                }
                self.member_index = 0
                return await self.async_step_member()
        schema = vol.Schema(
            {
                vol.Required(CONF_PEOPLE): entity_selector("person"),
                vol.Required(CONF_PRIMARY_HOME): entity_selector("zone", False),
                vol.Optional(CONF_PLACES): entity_selector("zone"),
            }
        )
        return self.async_show_form(
            step_id="household",
            data_schema=self.add_suggested_values_to_schema(
                schema,
                user_input if user_input is not None else self.draft,
            ),
            errors=errors,
        )

    async def async_step_member(self, user_input=None):
        person_id = self.draft[CONF_PEOPLE][self.member_index]
        associated, active = tracker_suggestions(self.hass, person_id)
        suggested, guidance = tracker_advice(self.hass, associated, active)
        errors = {}
        if user_input is not None:
            previous = self.draft[CONF_MEMBERS].get(person_id, {})
            values = {
                key: user_input.get(key, []) for key in (CONF_TRACKERS, CONF_RESIDENCES)
            }
            values.update(
                kind=user_input.get("kind", "person"),
                pet_home_minutes=previous.get("pet_home_minutes", 1440),
                pet_away_minutes=previous.get("pet_away_minutes", 5),
            )
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
            )
            if not errors:
                self.draft[CONF_MEMBERS][person_id] = values
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
                if values["kind"] == "pet":
                    return await self.async_step_pet_freshness()
                return await self.after_member()
        defaults = self.draft[CONF_MEMBERS].get(
            person_id,
            {
                CONF_TRACKERS: [suggested] if suggested else [],
                CONF_RESIDENCES: [],
            },
        )
        schema = vol.Schema(
            {
                vol.Optional(CONF_TRACKERS): tracker_selector(self.hass),
                vol.Optional(CONF_RESIDENCES): entity_selector("zone"),
                vol.Optional("kind", default="person"): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=["person", "pet"])
                ),
                vol.Optional(
                    "configure_sensors", default=False
                ): selector.BooleanSelector(),
                vol.Optional(
                    "configure_reports", default=False
                ): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(
            step_id="member",
            errors=errors,
            data_schema=self.add_suggested_values_to_schema(
                schema,
                user_input if user_input is not None else defaults,
            ),
            description_placeholders={
                "person": entity_label(self.hass, person_id),
                "number": str(self.member_index + 1),
                "total": str(len(self.draft[CONF_PEOPLE])),
                "active": entity_label(self.hass, active),
                "tracker_guidance": guidance,
            },
        )

    async def async_step_pet_freshness(self, user_input=None):
        person_id = self.draft[CONF_PEOPLE][self.member_index]
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
                vol.Optional(key, default=default): selector.NumberSelector(
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
            person = self.draft[CONF_PEOPLE][self.member_index]
            member = self.draft[CONF_MEMBERS][person]
            reports = member.setdefault("location_reports", {})
            supporting = member.get("supporting", {})
            source = supporting.pop("location_report_source", None)
            timestamp = supporting.pop("location_reported_at", None)
            if source and timestamp:
                reports.setdefault(source, timestamp)
            if not supporting:
                member.pop("supporting", None)
            self.report_sources = list(
                dict.fromkeys([person, *member[CONF_TRACKERS], *reports])
            )
            self.report_index = 0
            return await self.async_step_source_report()
        self.member_index += 1
        if self.member_index < len(self.draft[CONF_PEOPLE]):
            return await self.async_step_member()
        return await self.async_step_confirm()

    async def async_step_source_report(self, user_input=None):
        person = self.draft[CONF_PEOPLE][self.member_index]
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
            },
        )

    async def async_step_supporting(self, user_input=None):
        person_id = self.draft[CONF_PEOPLE][self.member_index]
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
                vol.Optional(key): entity_selector(SUPPORTING_DOMAINS[key], False)
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
        if user_input is not None:
            # Recheck every selection: sources can disappear during a long flow.
            invalid = household_errors(self.hass, self.draft) or any(
                member_errors(
                    self.hass, member, self.draft[CONF_PRIMARY_HOME], person_id
                )
                for person_id, member in self.draft[CONF_MEMBERS].items()
            )
            if invalid:
                result = await self.async_step_household()
                result["errors"] = {"base": "entities_changed"}
                return result
            return self.save()
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders=review_summary(self.hass, self.draft),
        )


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
        return await self.async_step_household(user_input)

    @callback
    def save(self):
        if self.draft != dict(self.config_entry.options):
            frontend.preserve_for_reload(self.hass, self.config_entry.entry_id)
        return self.async_create_entry(title="", data=self.draft)
