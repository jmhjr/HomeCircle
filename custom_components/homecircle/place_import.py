"""User-reviewed one-time import of Life360 places into editable HA zones."""

from math import isfinite
import re
from urllib.parse import quote

import voluptuous as vol
from life360 import Life360
from life360.const import HOST
from homeassistant.helpers import selector

from .const import CONF_LIFE360_ACCOUNT, CONF_PLACES, CONF_PRIMARY_HOME
from .life360_direct import authorized_client, new_session
from .zone_setup import async_create_zone, zone_error


def markdown_name(value):
    return re.sub(r"([\\`*_{}\[\]<>])", r"\\\1", " ".join(value.split()))


def connections(hass, draft):
    """Keep authorization server-side and label saved accounts explicitly."""
    result = []
    if account := draft.get(CONF_LIFE360_ACCOUNT):
        result.append(("HomeCircle Life360 connection", {"direct": account}))
    for entry in hass.config_entries.async_entries("life360"):
        accounts = entry.options.get("accounts", {})
        if entry.disabled_by or not isinstance(accounts, dict):
            continue
        for label, account in accounts.items():
            if (
                isinstance(account, dict)
                and account.get("enabled", True)
                and isinstance(account.get("authorization"), str)
                and account["authorization"]
            ):
                result.append(
                    (f"Life360: {label}", {"authorization": account["authorization"]})
                )
    return result


async def fetch(connection, circle=None):
    """Bounded read-only requests using the existing connection; no raw logs."""
    async with await new_session() as session:
        api = (
            await authorized_client(session, connection["direct"])
            if "direct" in connection
            else Life360(session, 0, authorization=connection["authorization"])
        )
        if circle is None:
            return await api.get_circles()
        # The pinned client has no places method. Use its authenticated request path.
        data = await api._request(
            f"https://{HOST}/v3/circles/{quote(circle, safe='')}/places.json", False
        )
        if not isinstance(data, dict) or not isinstance(data.get("places"), list):
            raise ValueError("Invalid places response")
        return data["places"]


def parse_places(raw):
    """Retain only validated fields needed to create a zone, in flow memory."""
    result = []
    for place in raw:
        try:
            name = place["name"].strip()
            location = {k: float(place[k]) for k in ("latitude", "longitude", "radius")}
            valid = (
                bool(name)
                and len(name) <= 60
                and not any(ord(c) < 32 for c in name)
                and all(isfinite(n) for n in location.values())
                and -90 <= location["latitude"] <= 90
                and -180 <= location["longitude"] <= 180
                and 1 <= location["radius"] <= 100000
                and not any(isinstance(place[k], bool) for k in location)
            )
            if valid:
                result.append({"name": name, "location": location})
        except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
            continue
    return result


def same_center(a, b):
    """Detect essentially identical zone centers, not overlapping radii."""
    try:
        return (
            abs(float(a["latitude"]) - float(b["latitude"])) < 0.00001
            and abs(float(a["longitude"]) - float(b["longitude"])) < 0.00001
        )
    except (KeyError, TypeError, ValueError):
        return False


def existing_zone(hass, place, primary):
    for state in hass.states.async_all("zone"):
        if same_center(state.attributes, place["location"]):
            return state
        if (
            state.entity_id == primary
            and place["name"].casefold() == state.name.casefold()
        ):
            return state
    return None


def select_field(options, multiple=False):
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options,
            multiple=multiple,
            custom_value=False,
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


class PlaceImportFlow:
    """Options-flow steps; no zone writes until the final review is accepted."""

    async def async_step_import_places(self, user_input=None):
        if user_input is None:
            self.place_connections = connections(self.hass, self.draft)
        if not self.place_connections:
            return self.async_abort(reason="place_import_no_account")
        errors = {}
        if user_input is not None:
            index = int(user_input["account"])
            self.place_connection = self.place_connections[index][1]
            try:
                self.place_circles = await fetch(self.place_connection)
                if not self.place_circles:
                    raise ValueError("No circles")
            except Exception:
                errors["base"] = "place_import_fetch"
            else:
                return await self.async_step_import_place_circle()
        return self.async_show_form(
            step_id="import_places",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required("account"): select_field(
                        [
                            {"value": str(i), "label": label}
                            for i, (label, _) in enumerate(self.place_connections)
                        ]
                    )
                }
            ),
        )

    async def async_step_import_place_circle(self, user_input=None):
        errors = {}
        if user_input is not None:
            circle = self.place_circles[int(user_input["circle"])]
            try:
                raw = await fetch(self.place_connection, circle["id"])
                self.import_candidates = parse_places(raw)
                self.import_invalid = len(raw) - len(self.import_candidates)
                self.import_created = []
            except Exception:
                errors["base"] = "place_import_fetch"
            else:
                return await self.async_step_import_place_select()
        return self.async_show_form(
            step_id="import_place_circle",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required("circle"): select_field(
                        [
                            {
                                "value": str(i),
                                "label": c.get("name") or "Life360 circle",
                            }
                            for i, c in enumerate(self.place_circles)
                        ]
                    )
                }
            ),
        )

    async def async_step_import_place_select(self, user_input=None):
        available = [
            (i, p)
            for i, p in enumerate(self.import_candidates)
            if not existing_zone(self.hass, p, self.draft[CONF_PRIMARY_HOME])
        ]
        errors = {}
        if user_input is not None:
            chosen = user_input.get("places", [])
            if not chosen:
                errors["base"] = "place_import_empty"
            elif any(index not in {str(i) for i, _ in available} for index in chosen):
                errors["base"] = "place_import_changed"
            else:
                self.import_plan = []
                used_names = {
                    s.name.casefold() for s in self.hass.states.async_all("zone")
                }
                for index in chosen:
                    place = next(p for i, p in available if str(i) == index)
                    if any(
                        same_center(p["location"], place["location"])
                        for p in self.import_plan
                    ):
                        continue
                    name = place["name"]
                    suffix = 2
                    while name.casefold() in used_names:
                        name = f"{place['name'][:50]} ({suffix})"
                        suffix += 1
                    used_names.add(name.casefold())
                    self.import_plan.append(
                        {"name": name, "location": dict(place["location"])}
                    )
                self.import_index = 0
                return await self.async_step_import_place_edit()
        if not available:
            return self.async_abort(reason="place_import_none")
        repeated = {}
        options = []
        for i, p in available:
            name = p["name"]
            repeated[name] = repeated.get(name, 0) + 1
            label = f"{name} · {p['location']['radius']:g} m"
            if repeated[name] > 1:
                label += f" · item {repeated[name]}"
            options.append({"value": str(i), "label": label})
        return self.async_show_form(
            step_id="import_place_select",
            errors=errors,
            data_schema=vol.Schema(
                {vol.Required("places", default=[]): select_field(options, True)}
            ),
            description_placeholders={
                "available": str(len(available)),
                "existing": str(len(self.import_candidates) - len(available)),
                "invalid": str(self.import_invalid),
            },
        )

    async def async_step_import_place_edit(self, user_input=None):
        place = self.import_plan[self.import_index]
        errors = {}
        if user_input is not None and user_input.get("skip"):
            self.import_plan.pop(self.import_index)
            if not self.import_plan:
                return self.async_abort(reason="place_import_skipped")
            if self.import_index == len(self.import_plan):
                return await self.async_step_import_place_confirm()
            return await self.async_step_import_place_edit()
        if user_input is not None:
            name, location = user_input.get("name", ""), user_input.get("location")
            error = zone_error(self.hass, name, location)
            if not error and any(
                i != self.import_index
                and p["name"].casefold() == name.strip().casefold()
                for i, p in enumerate(self.import_plan)
            ):
                error = "zone_already_exists"
            if not error and any(
                i != self.import_index and same_center(p["location"], location)
                for i, p in enumerate(self.import_plan)
            ):
                error = "zone_already_exists"
            if not error and existing_zone(
                self.hass,
                {"name": name, "location": location},
                self.draft[CONF_PRIMARY_HOME],
            ):
                error = "zone_already_exists"
            if error:
                errors["base"] = error
            else:
                self.import_plan[self.import_index] = {
                    "name": name.strip(),
                    "location": location,
                }
                self.import_index += 1
                if self.import_index == len(self.import_plan):
                    return await self.async_step_import_place_confirm()
                return await self.async_step_import_place_edit()
        return self.async_show_form(
            step_id="import_place_edit",
            errors=errors,
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Optional("skip", default=False): selector.BooleanSelector(),
                        vol.Optional("name"): selector.TextSelector(),
                        vol.Optional("location"): selector.LocationSelector(
                            selector.LocationSelectorConfig(radius=True)
                        ),
                    }
                ),
                user_input or place,
            ),
            description_placeholders={
                "number": str(self.import_index + 1),
                "total": str(len(self.import_plan)),
            },
        )

    async def async_step_import_place_confirm(self, user_input=None):
        errors = {}
        if user_input is not None:
            if not user_input.get("confirm"):
                errors["base"] = "place_import_confirm"
            else:
                for place in self.import_plan:
                    if place.get("created"):
                        continue
                    error = zone_error(self.hass, place["name"], place["location"])
                    if error or existing_zone(
                        self.hass, place, self.draft[CONF_PRIMARY_HOME]
                    ):
                        errors["base"] = "place_import_changed"
                        break
                if not errors:
                    for place in self.import_plan:
                        if place.get("created"):
                            continue
                        try:
                            zone_id = await async_create_zone(
                                self.hass, place["name"], place["location"]
                            )
                        except Exception:
                            zone_id = None
                        if not zone_id:
                            errors["base"] = "place_import_create"
                            break
                        place["created"] = zone_id
                        self.import_created.append(zone_id)
                    if not errors:
                        self.draft[CONF_PLACES] = list(
                            dict.fromkeys(
                                [*self.draft.get(CONF_PLACES, []), *self.import_created]
                            )
                        )
                        return self.save()
        return self.async_show_form(
            step_id="import_place_confirm",
            errors=errors,
            data_schema=vol.Schema(
                {vol.Required("confirm", default=False): selector.BooleanSelector()}
            ),
            description_placeholders={
                "summary": "\n".join(
                    f"• {markdown_name(p['name'])} — {p['location']['radius']:g} m"
                    for p in self.import_plan
                )
            },
        )
