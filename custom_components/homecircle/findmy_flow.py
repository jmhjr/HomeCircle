"""HomeCircle native Find My onboarding; secrets stay transient until selection."""

import asyncio
from copy import deepcopy
from datetime import timedelta
from functools import partial
from pathlib import Path
from uuid import uuid4
import re

from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import selector
from homeassistant.helpers.event import async_call_later
import voluptuous as vol

from .const import CONF_FINDMY_ACCOUNTS, CONF_FINDMY_ENABLED
from .findmy_setup import FindMySetup, FindMySetupError, safe_label
from .findmy_vault import Vault, account_identity
from .findmy_provider import account_root
from .findmy_resume import prepare_saved_setup, has_saved_report_capability


_TERMINAL_SIGNIN_ERRORS = frozenset(
    {
        "findmy_code_signin_failed",
        "findmy_code_delegate_failed",
        "findmy_verification_limit",
        "findmy_signin_state",
        "findmy_account_mismatch",
        "findmy_initial_refused",
        "findmy_identity_failed",
    }
)


async def _finish_saved_transaction(task):
    """An explicitly confirmed local commit must finish before cancellation returns."""
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
        except Exception:
            break
    if cancelled:
        # Consume a failed transaction too: its own cleanup resumes the account.
        if not task.cancelled():
            task.exception()
        raise asyncio.CancelledError
    return task.result()


def choice(options, multiple=False):
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options,
            multiple=multiple,
            custom_value=False,
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def secret():
    return selector.TextSelector(
        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
    )


def label(value):
    return re.sub(r"([\\`*_{}\[\]<>])", r"\\\1", safe_label(value, "Apple account"))


class FindMyFlow:
    findmy_setup = None
    findmy_task = None
    findmy_expire = None
    findmy_next = None
    findmy_error = None
    findmy_stage = None
    findmy_account_id = None
    findmy_selected = None
    findmy_commit_task = None

    @callback
    def async_remove(self):
        if self.findmy_expire:
            self.findmy_expire()
            self.findmy_expire = None
        self.findmy_staged = {}
        setup = self.findmy_setup
        task = self.findmy_task
        commit = self.findmy_commit_task
        self.findmy_setup = None
        self.findmy_task = None
        if task and not task.done():
            task.cancel()
        if setup or commit:

            async def cleanup():
                if task:
                    await asyncio.gather(task, return_exceptions=True)
                if commit:
                    await asyncio.gather(commit, return_exceptions=True)
                if setup:
                    await setup.close()

            self.hass.async_create_task(
                cleanup(), "HomeCircle Find My setup cleanup", eager_start=False
            )
        super().async_remove()

    async def async_step_findmy_accounts(self, user_input=None):
        accounts = self.draft.get(CONF_FINDMY_ACCOUNTS, {})
        options = ["findmy_add"]
        if accounts:
            options.append("findmy_manage")
        return self.async_show_menu(step_id="findmy_accounts", menu_options=options)

    async def async_step_findmy_manage(self, user_input=None):
        accounts = self.draft.get(CONF_FINDMY_ACCOUNTS, {})
        if user_input is not None:
            identifier = user_input.get("account")
            if identifier in accounts:
                self.findmy_account_id = identifier
                self.findmy_label = accounts[identifier]["label"]
                return await self.async_step_findmy_account_actions()
        return self.async_show_form(
            step_id="findmy_manage",
            data_schema=vol.Schema(
                {
                    vol.Required("account"): choice(
                        [
                            {"value": key, "label": account["label"]}
                            for key, account in accounts.items()
                        ]
                    )
                }
            ),
        )

    async def async_step_findmy_account_actions(self, user_input=None):
        accounts = self.draft.get(CONF_FINDMY_ACCOUNTS, {})
        if self.findmy_account_id not in accounts:
            return self.async_abort(reason="findmy_account_mismatch")
        actions = ["findmy_reconnect", "findmy_edit_items"]
        if not self.pending_connections and getattr(self, "config_entry", None):
            actions.insert(0, "findmy_saved_items")
        if not self.pending_connections:
            actions.append("findmy_disconnect")
        return self.async_show_menu(
            step_id="findmy_account_actions", menu_options=actions
        )

    async def async_step_findmy_saved_items(self, user_input=None):
        """Edit keys already saved for this account without Apple authentication."""
        metadata = self.draft.get(CONF_FINDMY_ACCOUNTS, {}).get(self.findmy_account_id)
        if (
            not metadata
            or self.pending_connections
            or not getattr(self, "config_entry", None)
        ):
            return self.async_abort(reason="findmy_account_mismatch")
        errors = {}
        if user_input is not None:
            if not user_input.get("consent"):
                errors["base"] = "findmy_consent_required"
            else:
                try:
                    root = await self.hass.async_add_executor_job(
                        account_root, self.hass, metadata
                    )
                    previous = await self.hass.async_add_executor_job(Vault(root).load)
                    if account_identity(previous["session"]) != metadata.get(
                        "account_identity"
                    ):
                        raise FindMySetupError("findmy_account_mismatch")
                    from .findmy_reports import account_items

                    libraries = Path(
                        self.hass.config.path(
                            ".storage", "homecircle_findmy", "anisette-libs.bin"
                        )
                    )
                    setup = await self.hass.async_add_executor_job(
                        prepare_saved_setup,
                        previous["session"],
                        account_items(previous),
                        libraries,
                    )
                except FindMySetupError as error:
                    errors["base"] = str(error)
                except Exception:
                    errors["base"] = "findmy_storage_failed"
                else:
                    if self.findmy_setup:
                        await self.findmy_setup.close()
                    self.findmy_setup = setup
                    self.findmy_previous = previous
                    self.findmy_saved_metadata = deepcopy(metadata)
                    self.findmy_saved_only = True
                    if self.findmy_expire:
                        self.findmy_expire()
                    self.findmy_expire = async_call_later(
                        self.hass, timedelta(minutes=15), self._expire_findmy
                    )
                    return await self.async_step_findmy_select()
        return self.async_show_form(
            step_id="findmy_saved_items",
            data_schema=vol.Schema(
                {vol.Required("consent", default=False): selector.BooleanSelector()}
            ),
            errors=errors,
        )

    async def async_step_findmy_reconnect(self, user_input=None):
        self.findmy_discover_new = False
        return await self.async_step_findmy_add(user_input)

    async def async_step_findmy_edit_items(self, user_input=None):
        self.findmy_discover_new = True
        return await self.async_step_findmy_add(user_input)

    async def async_step_findmy_add(self, user_input=None):
        self.findmy_saved_only = False
        errors = {}
        existing = self.draft.get(CONF_FINDMY_ACCOUNTS, {}).get(self.findmy_account_id)
        if user_input is not None:
            if not user_input.get("consent"):
                errors["base"] = "findmy_consent_required"
            else:
                self.findmy_label = safe_label(
                    user_input.get("label") or (existing or {}).get("label"),
                    "Apple account",
                )
                if self.findmy_account_id is None:
                    self.findmy_account_id = uuid4().hex
                libraries = Path(
                    self.hass.config.path(
                        ".storage", "homecircle_findmy", "anisette-libs.bin"
                    )
                )
                if self.findmy_setup:
                    await self.findmy_setup.close()
                previous = None
                if existing:
                    try:
                        root = await self.hass.async_add_executor_job(
                            account_root, self.hass, existing
                        )
                        previous = await self.hass.async_add_executor_job(
                            Vault(root).load
                        )
                    except Exception:
                        return self.async_abort(reason="findmy_storage_failed")
                self.findmy_previous = previous
                await self.hass.async_add_executor_job(
                    account_root, self.hass, {"storage_id": "legacy"}, True
                )
                if libraries.is_symlink():
                    return self.async_abort(reason="findmy_storage_failed")
                self.findmy_setup = await self.hass.async_add_executor_job(
                    partial(
                        FindMySetup.create,
                        libraries,
                        previous["session"] if previous else None,
                        onboarding=True,
                    )
                )
                if previous:
                    from .findmy_reports import account_items

                    self.findmy_setup.previous_items = account_items(previous)
                    self.findmy_setup.discover_new = getattr(
                        self, "findmy_discover_new", True
                    )
                if self.findmy_expire:
                    self.findmy_expire()
                self.findmy_expire = async_call_later(
                    self.hass, timedelta(minutes=15), self._expire_findmy
                )
                if getattr(
                    getattr(self.findmy_setup.account, "_anisette", None), "_homecircle_mac", False
                ):
                    return await self._findmy_work(
                        self.findmy_setup.prepare_identity(),
                        "findmy_login",
                        "findmy_login",
                    )
                return await self.async_step_findmy_login()
        schema = {vol.Required("consent", default=False): selector.BooleanSelector()}
        if not existing:
            schema = {
                vol.Required("label", default="Apple account"): selector.TextSelector(),
                **schema,
            }
        return self.async_show_form(
            step_id="findmy_add", data_schema=vol.Schema(schema), errors=errors
        )

    @callback
    def _expire_findmy(self, event):
        manager = (
            self.hass.config_entries.options
            if getattr(self, "config_entry", None)
            else self.hass.config_entries.flow
        )
        try:
            manager.async_abort(self.flow_id)
        except Exception:
            self.async_remove()

    async def _findmy_work(self, coroutine, next_step, retry_step):
        self.findmy_next = next_step
        self.findmy_retry = retry_step
        self.findmy_error = None

        async def work():
            try:
                outcome = await coroutine
                if isinstance(outcome, str):
                    self.findmy_next = "findmy_" + outcome
            except FindMySetupError as error:
                self.findmy_error = str(error)
            except Exception:
                self.findmy_error = "findmy_operation_failed"

        self.findmy_task = self.hass.async_create_background_task(
            work(), "HomeCircle Find My setup", eager_start=True
        )
        result = await self.async_step_findmy_wait()
        if self.findmy_task.done() and result["type"] is FlowResultType.SHOW_PROGRESS_DONE:
            # Immediate work needs no frontend progress subscription. Enter the
            # next step without replaying this step's consent/code input.
            return await getattr(self, "async_step_" + result["step_id"])(None)
        return result

    async def async_step_findmy_wait(self, user_input=None):
        if self.findmy_task is None or self.findmy_task.cancelled():
            # A cancelled operation never completed its next step. Keep an
            # expired or missing task from looking like successful sign-in.
            self.findmy_error = "findmy_signin_state"
            return self.async_show_progress_done(next_step_id="findmy_signin_ended")
        if not self.findmy_task.done():
            return self.async_show_progress(
                step_id="findmy_wait",
                progress_action="findmy_connecting",
                progress_task=self.findmy_task,
            )
        if self.findmy_error:
            if self.findmy_error in _TERMINAL_SIGNIN_ERRORS:
                return self.async_show_progress_done(next_step_id="findmy_signin_ended")
            if self.findmy_error == "findmy_report_access_unavailable":
                return self.async_show_progress_done(
                    next_step_id="findmy_report_access"
                )
            if self.findmy_error in ("findmy_zone_denied", "findmy_zone_failed"):
                self.findmy_retry = "findmy_zone"
            elif self.findmy_retry == "findmy_passcode" and getattr(
                self.findmy_setup, "keys_recovered", False
            ):
                self.findmy_retry = "findmy_discovery"
            self.findmy_stage = self.findmy_retry
            return self.async_show_progress_done(next_step_id=self.findmy_retry)
        return self.async_show_progress_done(next_step_id=self.findmy_next)

    async def async_step_findmy_report_access(self, user_input=None):
        """Missing tracking access ends this attempt without reusing a code."""
        await self.finish_findmy_setup()
        return self.async_abort(reason="findmy_report_access_unavailable")

    async def async_step_findmy_signin_ended(self, user_input=None):
        """End consumed or mismatched authentication without resubmitting a code."""
        reason = (
            self.findmy_error
            if self.findmy_error in _TERMINAL_SIGNIN_ERRORS
            else "findmy_signin_state"
        )
        await self.finish_findmy_setup()
        return self.async_abort(reason=reason)

    async def async_step_findmy_login(self, user_input=None):
        if user_input is not None:
            accounts = self.draft.get(CONF_FINDMY_ACCOUNTS, {})
            original = accounts.get(self.findmy_account_id)
            self.findmy_setup.account_guard = lambda state: (
                (
                    not original
                    or original.get("account_identity") == account_identity(state)
                )
                and not any(
                    key != self.findmy_account_id
                    and account.get("account_identity") == account_identity(state)
                    for key, account in accounts.items()
                )
            )
            return await self._findmy_work(
                self.findmy_setup.login(user_input["username"], user_input["password"]),
                "findmy_device",
                "findmy_login",
            )
        return self.async_show_form(
            step_id="findmy_login",
            data_schema=vol.Schema(
                {
                    vol.Required("username"): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.EMAIL
                        )
                    ),
                    vol.Required("password"): secret(),
                }
            ),
            errors={"base": self.findmy_error} if self.findmy_error else {},
        )

    async def async_step_findmy_factor(self, user_input=None):
        if user_input is not None:
            return await self._findmy_work(
                self.findmy_setup.request_code(user_input["method"]),
                "findmy_code",
                "findmy_factor",
            )
        return self.async_show_form(
            step_id="findmy_factor",
            data_schema=vol.Schema(
                {vol.Required("method"): choice(self.findmy_setup.factor_choices())}
            ),
            errors={"base": self.findmy_error} if self.findmy_error else {},
            description_placeholders={
                "verification_notice": (
                    "Apple requested another verification step. Choose a method and use the newest code."
                    if getattr(self.findmy_setup, "additional_verification", False)
                    else ""
                )
            },
        )

    async def async_step_findmy_code(self, user_input=None):
        if user_input is not None:
            return await self._findmy_work(
                self.findmy_setup.verify_code(user_input["code"]),
                "findmy_device",
                "findmy_code",
            )
        return self.async_show_form(
            step_id="findmy_code",
            data_schema=vol.Schema({vol.Required("code"): secret()}),
            errors={"base": self.findmy_error} if self.findmy_error else {},
            description_placeholders={
                "verification_notice": (
                    "Apple requested another verification step. Enter the newest code for this step."
                    if getattr(self.findmy_setup, "additional_verification", False)
                    else ""
                )
            },
        )

    async def async_step_findmy_device(self, user_input=None):
        if user_input is not None:
            self.findmy_device = user_input["device"]
            return await self.async_step_findmy_passcode()
        return self.async_show_form(
            step_id="findmy_device",
            data_schema=vol.Schema(
                {vol.Required("device"): choice(self.findmy_setup.device_choices())}
            ),
        )

    async def async_step_findmy_zone(self, user_input=None):
        if user_input is not None:
            return await self._findmy_work(
                self.findmy_setup.prepare_recovery(), "findmy_device", "findmy_zone"
            )
        return self.async_show_form(
            step_id="findmy_zone",
            data_schema=vol.Schema({}),
            errors={"base": self.findmy_error} if self.findmy_error else {},
        )

    async def async_step_findmy_discovery(self, user_input=None):
        if not getattr(self.findmy_setup, "keys_recovered", False):
            return await self.async_step_findmy_passcode()
        if user_input is not None:
            return await self._findmy_work(
                self.findmy_setup.retry_discovery(), "findmy_select", "findmy_discovery"
            )
        return self.async_show_form(
            step_id="findmy_discovery",
            data_schema=vol.Schema({}),
            errors={"base": "findmy_discovery_failed"} if self.findmy_error else {},
        )

    async def async_step_findmy_passcode(self, user_input=None):
        if getattr(self.findmy_setup, "keys_recovered", False):
            return await self.async_step_findmy_discovery()
        if user_input is not None:
            # A returned candidate list is kept in memory, not returned by the progress form.
            return await self._findmy_work(
                self.findmy_setup.discover(self.findmy_device, user_input["passcode"]),
                "findmy_select",
                "findmy_passcode",
            )
        return self.async_show_form(
            step_id="findmy_passcode",
            data_schema=vol.Schema({vol.Required("passcode"): secret()}),
            errors={"base": self.findmy_error} if self.findmy_error else {},
        )

    async def async_step_findmy_select(self, user_input=None):
        errors = {}
        options = self.findmy_setup.item_choices()
        if not options:
            return self.async_abort(reason="findmy_no_items")
        if user_input is not None:
            chosen = user_input.get("items", [])
            if not chosen:
                errors["base"] = "findmy_select_items"
            else:
                self.findmy_selected = chosen
                return await self.async_step_findmy_types()
        return self.async_show_form(
            step_id="findmy_select",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "items",
                        default=list(self.findmy_setup.previous_items)
                        if not self.findmy_setup.discover_new
                        else [],
                    ): choice(options, True)
                }
            ),
            errors=errors,
        )

    async def async_step_findmy_types(self, user_input=None):
        if user_input is not None:
            self.findmy_types = {
                identifier: user_input.get(f"type_{i}", "other")
                for i, identifier in enumerate(self.findmy_selected)
            }
            return await self.async_step_findmy_confirm()
        original = self.draft.get(CONF_FINDMY_ACCOUNTS, {}).get(
            self.findmy_account_id, {}
        )
        options = [
            {"value": "airtag", "label": "AirTag"},
            {"value": "airpods", "label": "AirPods"},
            {"value": "other", "label": "Other Find My item"},
        ]
        return self.async_show_form(
            step_id="findmy_types",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        f"type_{i}",
                        default=original.get("items", {})
                        .get(identifier, {})
                        .get("type")
                        or (
                            "airtag"
                            if "AirTag"
                            in (self.findmy_setup.accessories[identifier].model or "")
                            else "other"
                        ),
                    ): choice(options)
                    for i, identifier in enumerate(self.findmy_selected)
                }
            ),
            description_placeholders={
                "items": "\n".join(
                    f"{i + 1}. {label(self.findmy_setup.accessories[identifier].name)}"
                    for i, identifier in enumerate(self.findmy_selected)
                )
            },
        )

    async def async_step_findmy_confirm(self, user_input=None):
        errors = {}
        if (
            user_input is not None
            and user_input.get("confirm")
            and getattr(self, "findmy_saved_only", False)
        ):
            try:
                return await self._async_confirm_saved_items()
            except FindMySetupError as error:
                if str(error) == "findmy_report_access_unavailable":
                    return await self.async_step_findmy_report_access()
                errors["base"] = "findmy_storage_failed"
            except Exception:
                errors["base"] = "findmy_storage_failed"
        elif user_input is not None:
            if not user_input.get("confirm"):
                errors["base"] = "findmy_confirm_required"
            else:
                try:
                    session, items = self.findmy_setup.selected_payload(
                        self.findmy_selected
                    )
                except FindMySetupError as error:
                    if str(error) == "findmy_report_access_unavailable":
                        return await self.async_step_findmy_report_access()
                    raise
                identity = account_identity(session)
                accounts = self.draft.setdefault(CONF_FINDMY_ACCOUNTS, {})
                original = accounts.get(self.findmy_account_id)
                if (original and original.get("account_identity") != identity) or any(
                    key != self.findmy_account_id
                    and value.get("account_identity") == identity
                    for key, value in accounts.items()
                ):
                    errors["base"] = "findmy_account_mismatch"
                else:
                    metadata = {
                        **(original or {}),
                        "session_revision": (original or {}).get("session_revision", 0)
                        + 1,
                        "label": self.findmy_label,
                        "account_identity": identity,
                        "storage_id": (original or {}).get(
                            "storage_id", self.findmy_account_id
                        ),
                        "items": {
                            identifier: {
                                **(original or {}).get("items", {}).get(identifier, {}),
                                "name": safe_label(
                                    self.findmy_setup.accessories[identifier].name,
                                    "Find My item",
                                ),
                                "type": self.findmy_types[identifier],
                            }
                            for identifier in items
                        },
                    }
                    if self.pending_connections:
                        self.findmy_staged = {
                            self.findmy_account_id: (metadata, session, items)
                        }
                        accounts[self.findmy_account_id] = metadata
                        self.draft[CONF_FINDMY_ENABLED] = True
                        await self.finish_findmy_setup()
                        self.findmy_expire = async_call_later(
                            self.hass, timedelta(minutes=15), self._expire_findmy
                        )
                        return await self.connection_saved("findmy", accounts)
                    provider = None
                    paused = None
                    if original and getattr(self, "config_entry", None):
                        runtime = getattr(self.config_entry, "runtime_data", None)
                        if runtime:
                            provider = runtime.managed_trackers.get("findmy")
                    if provider:
                        paused = await provider.pause_account(self.findmy_account_id)
                    try:
                        root = await self.hass.async_add_executor_job(
                            account_root, self.hass, metadata, True
                        )
                        await self.hass.async_add_executor_job(
                            Vault(root).save_account, session, items
                        )
                    except Exception:
                        if provider:
                            provider.resume_account(self.findmy_account_id, paused)
                        errors["base"] = "findmy_storage_failed"
                    else:
                        if paused:
                            await paused.close()
                        accounts[self.findmy_account_id] = metadata
                        self.draft[CONF_FINDMY_ENABLED] = True
                        await self.finish_findmy_setup()
                        if self.pending_connections:
                            return await self.connection_saved("findmy", accounts)
                        if getattr(self, "config_entry", None):
                            return self.save()
                        return await self.connection_saved("findmy", accounts)
        return self.async_show_form(
            step_id="findmy_confirm",
            data_schema=vol.Schema(
                {vol.Required("confirm", default=False): selector.BooleanSelector()}
            ),
            errors=errors,
            description_placeholders={
                "account": label(self.findmy_label),
                "items": "\n".join(
                    label(self.findmy_setup.accessories[i].name)
                    for i in self.findmy_selected
                ),
            },
        )

    async def _async_confirm_saved_items(self):
        session, _ = self.findmy_setup.selected_payload(self.findmy_selected)
        identity = account_identity(session)
        previous = deepcopy(self.findmy_saved_metadata)
        chosen = tuple(self.findmy_selected)
        selection = {
            identifier: {
                **previous.get("items", {}).get(identifier, {}),
                "name": safe_label(
                    self.findmy_setup.accessories[identifier].name, "Find My item"
                ),
                "type": self.findmy_types[identifier],
            }
            for identifier in chosen
        }
        task = self.findmy_commit_task = self.hass.async_create_background_task(
            self._async_commit_saved_items(previous, selection, chosen, identity),
            "HomeCircle saved Find My item commit",
            eager_start=False,
        )
        try:
            options = await _finish_saved_transaction(task)
        finally:
            if task.done() and not task.cancelled() and task.exception() is None:
                self.draft = task.result()
                await self.finish_findmy_setup()
        return self.async_create_entry(title="", data=options)

    def _saved_account_current(self, previous, identity):
        """Check both snapshots: save() updates data before HA commits options."""
        entry = self.config_entry
        current = dict(entry.options or entry.data)
        metadata = current.get(CONF_FINDMY_ACCOUNTS, {}).get(self.findmy_account_id)
        if not isinstance(metadata, dict):
            raise FindMySetupError("findmy_saved_session_unavailable")
        for candidate in (
            metadata,
            entry.data.get(CONF_FINDMY_ACCOUNTS, {}).get(self.findmy_account_id),
        ):
            if candidate is not None and (
                candidate.get("session_revision", 0)
                != previous.get("session_revision", 0)
                or candidate.get("storage_id") != previous.get("storage_id")
                or candidate.get("account_identity") != identity
            ):
                raise FindMySetupError("findmy_saved_session_unavailable")
        return current, metadata

    async def _async_commit_saved_items(self, previous, selection, chosen, identity):
        """Serialize local replacement and publish matching metadata before reload."""
        from .findmy_reports import account_items
        from . import frontend

        entry = self.config_entry
        account_id = self.findmy_account_id
        locks = self.hass.data.setdefault("homecircle_findmy_saved_transactions", {})
        lock = locks.setdefault((entry.entry_id, account_id), asyncio.Lock())
        async with lock:
            _, metadata = self._saved_account_current(previous, identity)
            runtime = getattr(entry, "runtime_data", None)
            provider = runtime.managed_trackers.get("findmy") if runtime else None
            paused = await provider.pause_account(account_id) if provider else None
            latest = None
            wrote = False
            committed = False
            try:
                root = await self.hass.async_add_executor_job(
                    account_root, self.hass, metadata
                )
                latest = await self.hass.async_add_executor_job(Vault(root).load)
                if account_identity(
                    latest["session"]
                ) != identity or not has_saved_report_capability(latest["session"]):
                    raise FindMySetupError("findmy_saved_session_unavailable")
                current_items = account_items(latest)
                if any(identifier not in current_items for identifier in chosen):
                    raise FindMySetupError("findmy_saved_session_unavailable")
                write = self.hass.async_add_executor_job(
                    Vault(root).save_account,
                    latest["session"],
                    {identifier: current_items[identifier] for identifier in chosen},
                )
                # The executor may already be replacing the encrypted file. Finish
                # it even if HA cancels this background task during shutdown.
                wrote = True
                await _finish_saved_transaction(write)
                current, metadata = self._saved_account_current(previous, identity)
                accounts = deepcopy(current[CONF_FINDMY_ACCOUNTS])
                accounts[account_id] = {
                    **metadata,
                    "session_revision": previous.get("session_revision", 0) + 1,
                    "items": selection,
                }
                current = {
                    **current,
                    CONF_FINDMY_ACCOUNTS: accounts,
                    CONF_FINDMY_ENABLED: True,
                }
                data = {**entry.data, CONF_FINDMY_ACCOUNTS: accounts}
                self.hass.config_entries.async_update_entry(
                    entry, data=data, options=current
                )
                committed = True
                frontend.preserve_for_reload(self.hass, entry.entry_id)
                self.hass.config_entries.async_schedule_reload(entry.entry_id)
                return current
            except BaseException:
                if wrote and not committed:
                    # Metadata was not published. Keep the old live client and
                    # its complete item set consistent with the encrypted copy.
                    rollback = self.hass.async_add_executor_job(
                        Vault(root).save_account,
                        latest["session"],
                        account_items(latest),
                    )
                    await _finish_saved_transaction(rollback)
                raise
            finally:
                if provider and not committed:
                    provider.resume_account(account_id, paused)
                if committed and paused:
                    try:
                        await paused.close()
                    except Exception:
                        pass  # The replacement is committed; a close error is not a failed save.

    async def async_commit_findmy(self):
        if self.findmy_expire:
            self.findmy_expire()
            self.findmy_expire = None
        for account_id, (metadata, session, items) in getattr(
            self, "findmy_staged", {}
        ).items():
            provider = None
            paused = None
            if getattr(self, "config_entry", None):
                runtime = getattr(self.config_entry, "runtime_data", None)
                if runtime:
                    provider = runtime.managed_trackers.get("findmy")
            if provider:
                paused = await provider.pause_account(account_id)
            try:
                root = await self.hass.async_add_executor_job(
                    account_root, self.hass, metadata, True
                )
                await self.hass.async_add_executor_job(
                    Vault(root).save_account, session, items
                )
            except Exception:
                if provider:
                    provider.resume_account(account_id, paused)
                raise FindMySetupError("findmy_storage_failed") from None
            if paused:
                await paused.close()
        self.findmy_staged = {}

    async def finish_findmy_setup(self):
        if self.findmy_expire:
            self.findmy_expire()
            self.findmy_expire = None
        if self.findmy_setup:
            await self.findmy_setup.close()
            self.findmy_setup = None

    async def async_step_findmy_disconnect(self, user_input=None):
        if user_input is not None and user_input.get("confirm"):
            accounts = self.draft.setdefault(CONF_FINDMY_ACCOUNTS, {})
            metadata = accounts.get(self.findmy_account_id)
            provider = None
            runtime = getattr(self.config_entry, "runtime_data", None)
            if runtime:
                provider = runtime.managed_trackers.get("findmy")
            paused = (
                await provider.pause_account(self.findmy_account_id)
                if provider
                else None
            )
            from .findmy_storage import delete_account

            try:
                await self.hass.async_add_executor_job(
                    delete_account, self.hass, metadata
                )
            except Exception:
                if provider:
                    provider.resume_account(self.findmy_account_id, paused)
                return self.async_abort(reason="findmy_storage_failed")
            if paused:
                await paused.close()
            from homeassistant.helpers import issue_registry as ir

            ir.async_delete_issue(
                self.hass,
                "homecircle",
                f"findmy_auth_{self.config_entry.entry_id}_{self.findmy_account_id}",
            )
            accounts.pop(self.findmy_account_id, None)
            self.draft[CONF_FINDMY_ENABLED] = bool(accounts)
            return self.save()
        return self.async_show_form(
            step_id="findmy_disconnect",
            data_schema=vol.Schema(
                {vol.Required("confirm", default=False): selector.BooleanSelector()}
            ),
            description_placeholders={"account": label(self.findmy_label)},
        )
