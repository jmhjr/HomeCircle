"""Atomic, provider-independent household configuration through HA selectors."""

from copy import deepcopy
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


def entity_selector(domain: str, multiple: bool = True):
    return selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain=domain,
            multiple=multiple,
        )
    )


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
        errors = {}
        if user_input is not None:
            values = {
                key: user_input.get(key, []) for key in (CONF_TRACKERS, CONF_RESIDENCES)
            }
            values.update(
                kind=user_input.get("kind", "person"),
                pet_home_minutes=user_input.get("pet_home_minutes", 1440),
                pet_away_minutes=user_input.get("pet_away_minutes", 5),
            )
            previous_reports = (
                self.draft[CONF_MEMBERS].get(person_id, {}).get("location_reports", {})
            )
            if previous_reports:
                values["location_reports"] = deepcopy(previous_reports)
            self.edit_reports = user_input.get("configure_reports", False) or bool(
                set(previous_reports) - {person_id, *values[CONF_TRACKERS]}
            )
            previous_supporting = (
                self.draft[CONF_MEMBERS].get(person_id, {}).get("supporting")
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
                if user_input.get("configure_sensors") or supporting_errors(
                    self.hass,
                    values.get("supporting", {}),
                    person_id,
                    values[CONF_TRACKERS],
                ):
                    return await self.async_step_supporting()
                return await self.next_member()
        defaults = self.draft[CONF_MEMBERS].get(
            person_id,
            {
                CONF_TRACKERS: associated or ([active] if active else []),
                CONF_RESIDENCES: [],
            },
        )
        schema = vol.Schema(
            {
                vol.Optional(CONF_TRACKERS): entity_selector("device_tracker"),
                vol.Optional(CONF_RESIDENCES): entity_selector("zone"),
                vol.Optional("kind", default="person"): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=["person", "pet"])
                ),
                vol.Optional("pet_home_minutes", default=1440): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=10080, step=1, mode="box", unit_of_measurement="min"
                    )
                ),
                vol.Optional("pet_away_minutes", default=5): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=10080, step=1, mode="box", unit_of_measurement="min"
                    )
                ),
                vol.Optional(
                    "configure_reports", default=False
                ): selector.BooleanSelector(),
                vol.Optional(
                    "configure_sensors", default=False
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
                "person": person_id,
                "associated": ", ".join(associated) or "—",
                "active": active or "—",
            },
        )

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
            description_placeholders={"source": source},
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
                if values:
                    member["supporting"] = values
                else:
                    member.pop("supporting", None)
                return await self.next_member()
        schema = vol.Schema(
            {
                **{
                    vol.Optional(key): entity_selector(domain, False)
                    for key, domain in SUPPORTING_DOMAINS.items()
                },
                vol.Optional("location_report_source"): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        include_entities=[person_id, *member[CONF_TRACKERS]]
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="supporting",
            errors=errors,
            description_placeholders={"person": person_id},
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
        return self.async_show_form(step_id="confirm", data_schema=vol.Schema({}))


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
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(),
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
        return self.async_create_entry(title="", data=self.draft)
