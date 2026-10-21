"""HomeCircle native Find My onboarding; secrets stay transient until selection."""

import asyncio
from contextlib import AsyncExitStack
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
from .findmy_vault import Vault, VaultError, account_identity
from .findmy_provider import account_root
from .findmy_resume import prepare_saved_setup, has_saved_report_capability
from .findmy_identity import (
    IdentityError,
    accessory_material,
    prepare_state,
    previous_metadata,
    save_selection,
    selection_state,
)


_TERMINAL_SIGNIN_ERRORS = frozenset(
    {
        "findmy_code_signin_failed",
        "findmy_code_delegate_failed",
        "findmy_verification_limit",
        "findmy_signin_state",
        "findmy_account_mismatch",
        "findmy_initial_refused",
        "findmy_identity_failed",
        "findmy_recovery_signin_required",
        "findmy_recovery_rate_limited",
        "findmy_recovery_material_failed",
    }
)


# These errors can follow successful code consumption before recovery opens.
# Keep them terminal only at the code step; later recovery retries keep their
# existing stage, proof accounting and recovered-material handling.
_CONSUMED_CODE_RECOVERY_ERRORS = frozenset(
    {
        "findmy_account_mismatch",
        "findmy_duplicate_item",
        "findmy_identity_unavailable",
        "findmy_missing_item_identity",
        "findmy_no_recovery_device",
        "findmy_recovery_failed",
        "findmy_recovery_limit",
        "findmy_recovery_material_failed",
        "findmy_recovery_protocol",
        "findmy_recovery_rate_limited",
        "findmy_recovery_refused",
        "findmy_recovery_signin_required",
        "findmy_recovery_storage",
        "findmy_recovery_transient",
        "findmy_recovery_uncertain",
    }
)


def _ends_signin(error, retry_step):
    return type(error) is str and (
        error in _TERMINAL_SIGNIN_ERRORS
        or retry_step == "findmy_code" and error in _CONSUMED_CODE_RECOVERY_ERRORS
    )


async def _finish_saved_transaction(task):
    """An explicitly confirmed local commit must finish before cancellation returns."""
    # Shield a non-raising outcome container. Python 3.14 otherwise logs a late
    # task failure after shield cancellation, before we can consume the error.
    pending = asyncio.gather(task, return_exceptions=True)
    cancellation = None
    while not pending.done():
        try:
            await asyncio.shield(pending)
        except asyncio.CancelledError as error:
            if cancellation is None:
                cancellation = error
    result = pending.result()[0]
    if cancellation is not None:
        raise cancellation
    if isinstance(result, BaseException):
        raise result
    return result


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

    def _findmy_config_entry(self):
        """Options and Reconfigure edit the same existing account ownership."""
        entry = getattr(self, "config_entry", None)
        if entry is None and getattr(self, "source", None) == "reconfigure":
            entry = self._get_reconfigure_entry()
        return entry

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
                setup = None
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
                    setup.identity_state = prepare_state(
                        previous["session"],
                        account_items(previous),
                        metadata.get("items", {}),
                        previous.get("identity_state"),
                    )
                except IdentityError as error:
                    if setup is not None:
                        await setup.close()
                    errors["base"] = str(error)
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
                from .findmy_recovery_guard import get_recovery_guard

                self.findmy_setup.recovery_guard = get_recovery_guard(self.hass)
                self.findmy_setup.recovery_guard_required = True
                if previous:
                    from .findmy_reports import account_items

                    self.findmy_setup.previous_items = account_items(previous)
                    try:
                        self.findmy_setup.identity_state = prepare_state(
                            previous["session"],
                            account_items(previous),
                            existing.get("items", {}),
                            previous.get("identity_state"),
                        )
                    except IdentityError as error:
                        await self.finish_findmy_setup()
                        return self.async_abort(reason=str(error))
                    self.findmy_setup.discover_new = getattr(
                        self, "findmy_discover_new", True
                    )
                if self.findmy_expire:
                    self.findmy_expire()
                self.findmy_expire = async_call_later(
                    self.hass, timedelta(minutes=15), self._expire_findmy
                )
                if getattr(
                    getattr(self.findmy_setup.account, "_anisette", None),
                    "_homecircle_mac",
                    False,
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
        if (
            self.findmy_task.done()
            and result["type"] is FlowResultType.SHOW_PROGRESS_DONE
        ):
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
            if _ends_signin(self.findmy_error, getattr(self, "findmy_retry", None)):
                return self.async_show_progress_done(next_step_id="findmy_signin_ended")
            if self.findmy_error == "findmy_report_access_unavailable":
                return self.async_show_progress_done(
                    next_step_id="findmy_report_access"
                )
            if self.findmy_error == "findmy_recovery_limit":
                return self.async_show_progress_done(
                    next_step_id="findmy_recovery_reset"
                )
            if self.findmy_error == "findmy_recovery_resume":
                return self.async_show_progress_done(
                    next_step_id="findmy_recovery_resume"
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
            if _ends_signin(self.findmy_error, getattr(self, "findmy_retry", None))
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
        guard = getattr(self.findmy_setup, "recovery_guard", None)
        if guard is not None:
            from .findmy_identity import authenticated_identity
            from .findmy_recovery_guard import RecoveryGuardStorageError

            identity = authenticated_identity(self.findmy_setup.account.to_json())
            if identity is None:
                return self.async_abort(reason="findmy_account_mismatch")
            try:
                status = await guard.status(identity)
            except RecoveryGuardStorageError:
                return self.async_abort(reason="findmy_recovery_storage")
            if status["blocked"]:
                return await self.async_step_findmy_recovery_reset()
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

    async def async_step_findmy_recovery_resume(self, user_input=None):
        """Retry verified in-memory recovery material without another proof."""
        if not self.findmy_setup or not self.findmy_setup.can_resume_recovery(
            self.findmy_device
        ):
            self.findmy_error = "findmy_recovery_material_failed"
            return await self.async_step_findmy_signin_ended()
        if user_input is not None:
            return await self._findmy_work(
                self.findmy_setup.discover(self.findmy_device, ""),
                "findmy_select",
                "findmy_recovery_resume",
            )
        return self.async_show_form(
            step_id="findmy_recovery_resume",
            data_schema=vol.Schema({}),
            errors={"base": self.findmy_error}
            if self.findmy_error not in (None, "findmy_recovery_resume")
            else {},
        )

    async def async_step_findmy_recovery_reset(self, user_input=None):
        """An administrator explicitly acknowledges only this local safeguard."""
        from .findmy_identity import authenticated_identity
        from .findmy_recovery_guard import (
            RecoveryGuardBlocked,
            RecoveryGuardStorageError,
        )

        if not self.findmy_setup or not self.findmy_setup.recovery_guard:
            return self.async_abort(reason="findmy_recovery_storage")
        identity = authenticated_identity(self.findmy_setup.account.to_json())
        if identity is None:
            return self.async_abort(reason="findmy_account_mismatch")
        guard = self.findmy_setup.recovery_guard
        errors = {}
        try:
            if user_input is not None:
                if not user_input.get("acknowledge"):
                    errors["base"] = "findmy_recovery_acknowledge"
                else:
                    await guard.reset(identity)
                    # A reset never resubmits the passcode or renews Apple auth.
                    self.findmy_error = None
                    return await self.async_step_findmy_passcode()
            status = await guard.status(identity)
        except RecoveryGuardBlocked:
            errors["base"] = "findmy_recovery_busy"
            try:
                status = await guard.status(identity)
            except RecoveryGuardStorageError:
                return self.async_abort(reason="findmy_recovery_storage")
        except RecoveryGuardStorageError:
            return self.async_abort(reason="findmy_recovery_storage")
        return self.async_show_form(
            step_id="findmy_recovery_reset",
            data_schema=vol.Schema(
                {vol.Required("acknowledge", default=False): selector.BooleanSelector()}
            ),
            errors=errors,
            description_placeholders={
                "rejected": str(status["rejected"]),
                "uncertain": str(status["uncertain"] + status["pending"]),
            },
        )

    async def async_step_findmy_select(self, user_input=None):
        errors = {}
        options = self.findmy_setup.item_choices()
        if not options:
            return self.async_abort(reason="findmy_no_items")
        if user_input is not None:
            chosen = user_input.get("items", [])
            available = {option["value"] for option in options}
            if (
                not chosen
                or len(chosen) != len(set(chosen))
                or any(identifier not in available for identifier in chosen)
            ):
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
                        else [
                            identifier
                            for identifier in self.findmy_setup.previous_items
                            if identifier in self.findmy_setup.accessories
                        ],
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
                        default={
                            **previous_metadata(
                                getattr(self.findmy_setup, "identity_state", None),
                                identifier,
                            ),
                            **original.get("items", {}).get(identifier, {}),
                        }.get("type")
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
            except (FindMySetupError, IdentityError) as error:
                if str(error) == "findmy_report_access_unavailable":
                    return await self.async_step_findmy_report_access()
                errors["base"] = (
                    str(error)
                    if isinstance(error, IdentityError)
                    else "findmy_storage_failed"
                )
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
                except (FindMySetupError, IdentityError) as error:
                    if str(error) == "findmy_report_access_unavailable":
                        return await self.async_step_findmy_report_access()
                    errors["base"] = str(error)
                    return self._findmy_confirm_form(errors)
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
                    try:
                        selection, identity_state = self._findmy_selection_metadata(
                            session, items, original or {}
                        )
                    except IdentityError as error:
                        return self._findmy_confirm_form({"base": str(error)})
                    metadata = {
                        **(original or {}),
                        "session_revision": (original or {}).get("session_revision", 0)
                        + 1,
                        "label": self.findmy_label,
                        "account_identity": identity,
                        "storage_id": (original or {}).get(
                            "storage_id", self.findmy_account_id
                        ),
                        "items": selection,
                    }
                    if self.pending_connections:
                        self.findmy_staged = {
                            **getattr(self, "findmy_staged", {}),
                            self.findmy_account_id: (
                                metadata,
                                session,
                                items,
                                identity_state,
                                deepcopy(original),
                            ),
                        }
                        accounts[self.findmy_account_id] = metadata
                        self.draft[CONF_FINDMY_ENABLED] = True
                        await self.finish_findmy_setup()
                        self.findmy_expire = async_call_later(
                            self.hass, timedelta(minutes=15), self._expire_findmy
                        )
                        return await self.connection_saved("findmy", accounts)
                    try:
                        task = self.findmy_commit_task = (
                            self.hass.async_create_background_task(
                                self._async_commit_discovered_items(
                                    original, metadata, session, items, identity_state
                                ),
                                "HomeCircle discovered Find My item commit",
                                eager_start=False,
                            )
                        )
                        return await _finish_saved_transaction(task)
                    except Exception:
                        errors["base"] = "findmy_storage_failed"
        return self._findmy_confirm_form(errors)

    def _findmy_confirm_form(self, errors):
        previous = (
            self.draft.get(CONF_FINDMY_ACCOUNTS, {})
            .get(self.findmy_account_id, {})
            .get("items", {})
        )
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
                "removed_items": "\n".join(
                    label(item.get("name", "Find My item"))
                    for identifier, item in previous.items()
                    if identifier not in self.findmy_selected
                )
                or "None",
            },
        )

    def _findmy_selection_metadata(self, session, items, original):
        from homeassistant.helpers import entity_registry as er
        from .findmy_provider import tracker_unique_id

        registry = er.async_get(self.hass)
        metadata = deepcopy(original.get("items", {}))
        for identifier, item in metadata.items():
            entity_id = registry.async_get_entity_id(
                "device_tracker",
                "homecircle",
                tracker_unique_id(self.findmy_account_id, identifier, item),
            )
            preferences = self.draft.get("members", {}).get(entity_id, {})
            if preferences.get("kind") == "item":
                item["display_preferences"] = deepcopy(preferences)
        state = prepare_state(
            session,
            getattr(self.findmy_setup, "previous_items", {}),
            metadata,
            getattr(self.findmy_setup, "identity_state", None),
        )
        selection = {
            identifier: {
                **previous_metadata(state, identifier),
                **metadata.get(identifier, {}),
                "name": safe_label(
                    self.findmy_setup.accessories[identifier].name, "Find My item"
                ),
                "type": self.findmy_types[identifier],
            }
            for identifier in items
        }
        state = selection_state(session, items, selection, state)
        return selection, state

    async def _async_commit_discovered_items(
        self, original, metadata, session, items, identity_state
    ):
        """Replace a refreshed selection with the same local transaction discipline."""
        from .findmy_reports import account_items
        from .findmy_storage import delete_account
        from . import frontend

        entry = getattr(self, "config_entry", None)
        account_id = self.findmy_account_id
        locks = self.hass.data.setdefault("homecircle_findmy_saved_transactions", {})
        lock = locks.setdefault(
            (entry.entry_id if entry else None, account_id), asyncio.Lock()
        )
        async with lock:
            if entry and original:
                current, _ = self._saved_account_current(
                    original, metadata["account_identity"]
                )
            elif entry:
                current = dict(entry.options or entry.data)
                if account_id in current.get(CONF_FINDMY_ACCOUNTS, {}) or any(
                    value.get("account_identity") == metadata["account_identity"]
                    for value in current.get(CONF_FINDMY_ACCOUNTS, {}).values()
                ):
                    raise FindMySetupError("findmy_account_mismatch")
            else:
                current = deepcopy(self.draft)
            runtime = getattr(entry, "runtime_data", None) if entry else None
            provider = (
                runtime.managed_trackers.get("findmy") if runtime and original else None
            )
            paused = await provider.pause_account(account_id) if provider else None
            latest = None
            wrote = committed = False
            created = False
            previous_draft = deepcopy(self.draft)
            try:
                root = await self.hass.async_add_executor_job(
                    account_root, self.hass, metadata, True
                )
                if original:
                    latest = await self.hass.async_add_executor_job(Vault(root).load)
                    if (
                        account_identity(latest["session"])
                        != metadata["account_identity"]
                    ):
                        raise FindMySetupError("findmy_account_mismatch")
                    current_items = account_items(latest)
                    identity_state = prepare_state(
                        session, current_items, {}, identity_state
                    )
                    # Preserve polling progress completed after the picker opened.
                    # A report or cursor never transfers to an unproven key set.
                    for identifier, selected in items.items():
                        saved = current_items.get(identifier, {})
                        material = accessory_material(selected["accessory"])
                        if (
                            material is not None
                            and accessory_material(saved.get("accessory", {}))
                            == material
                        ):
                            for field in ("report", "search_before"):
                                if field in saved:
                                    selected[field] = deepcopy(saved[field])
                else:
                    if await self.hass.async_add_executor_job(root.exists):
                        raise FindMySetupError("findmy_saved_session_unavailable")
                    created = True
                wrote = True
                await _finish_saved_transaction(
                    self.hass.async_add_executor_job(
                        save_selection, Vault(root), session, items, identity_state
                    )
                )
                if entry and original:
                    current, _ = self._saved_account_current(
                        original, metadata["account_identity"]
                    )
                elif entry:
                    current = dict(entry.options or entry.data)
                    if account_id in current.get(CONF_FINDMY_ACCOUNTS, {}) or any(
                        value.get("account_identity") == metadata["account_identity"]
                        for value in current.get(CONF_FINDMY_ACCOUNTS, {}).values()
                    ):
                        raise FindMySetupError("findmy_account_mismatch")
                accounts = deepcopy(current.get(CONF_FINDMY_ACCOUNTS, {}))
                accounts[account_id] = metadata
                self.draft = {
                    **current,
                    CONF_FINDMY_ACCOUNTS: accounts,
                    CONF_FINDMY_ENABLED: True,
                }
                if entry:
                    self.hass.config_entries.async_update_entry(
                        entry,
                        data={
                            **getattr(entry, "data", {}),
                            CONF_FINDMY_ACCOUNTS: accounts,
                        },
                        options=self.draft,
                    )
                    committed = True
                    frontend.preserve_for_reload(self.hass, entry.entry_id)
                    self.hass.config_entries.async_schedule_reload(entry.entry_id)
                    result = self.async_create_entry(title="", data=self.draft)
                else:
                    result = await self.connection_saved("findmy", accounts)
                committed = True
                await self.finish_findmy_setup()
                return result
            except BaseException:
                self.draft = previous_draft
                if (
                    wrote
                    and not committed
                    and latest is not None
                    and self._findmy_revision_current(
                        original, metadata["account_identity"]
                    )
                ):
                    await _finish_saved_transaction(
                        self.hass.async_add_executor_job(
                            partial(
                                Vault(root).save_account,
                                latest["session"],
                                account_items(latest),
                                identity_state=latest.get("identity_state"),
                            )
                        )
                    )
                elif (
                    wrote
                    and not committed
                    and created
                    and (
                        not entry
                        or not any(
                            value.get("storage_id") == metadata["storage_id"]
                            for snapshot in (entry.data, entry.options)
                            for value in snapshot.get(CONF_FINDMY_ACCOUNTS, {}).values()
                        )
                    )
                ):
                    await _finish_saved_transaction(
                        self.hass.async_add_executor_job(
                            delete_account, self.hass, metadata
                        )
                    )
                raise
            finally:
                owns_account = not entry or (
                    original
                    and self._findmy_revision_current(
                        original, metadata["account_identity"]
                    )
                )
                if provider and not committed and owns_account:
                    provider.resume_account(account_id, paused)
                if paused and (committed or not owns_account):
                    try:
                        await paused.close()
                    except Exception:
                        pass

    async def _async_confirm_saved_items(self):
        session, items = self.findmy_setup.selected_payload(self.findmy_selected)
        identity = account_identity(session)
        previous = deepcopy(self.findmy_saved_metadata)
        chosen = tuple(self.findmy_selected)
        selection, identity_state = self._findmy_selection_metadata(
            session, items, previous
        )
        task = self.findmy_commit_task = self.hass.async_create_background_task(
            self._async_commit_saved_items(
                previous, selection, chosen, identity, identity_state
            ),
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

    def _saved_account_current(self, previous, identity, account_id=None):
        """Check both snapshots: save() updates data before HA commits options."""
        entry = self._findmy_config_entry()
        if entry is None:
            raise FindMySetupError("findmy_saved_session_unavailable")
        account_id = account_id or self.findmy_account_id
        current = dict(entry.options or getattr(entry, "data", {}))
        metadata = current.get(CONF_FINDMY_ACCOUNTS, {}).get(account_id)
        if not isinstance(metadata, dict):
            raise FindMySetupError("findmy_saved_session_unavailable")
        stored = getattr(entry, "data", {})
        if (
            CONF_FINDMY_ACCOUNTS in stored
            and account_id not in stored[CONF_FINDMY_ACCOUNTS]
        ):
            raise FindMySetupError("findmy_saved_session_unavailable")
        for candidate in (
            metadata,
            getattr(entry, "data", {}).get(CONF_FINDMY_ACCOUNTS, {}).get(account_id),
        ):
            if candidate is not None and (
                candidate.get("session_revision", 0)
                != previous.get("session_revision", 0)
                or candidate.get("storage_id") != previous.get("storage_id")
                or candidate.get("account_identity") != identity
            ):
                raise FindMySetupError("findmy_saved_session_unavailable")
        return current, metadata

    def _findmy_revision_current(self, previous, identity, account_id=None):
        """Rollback belongs only to the configuration that authorized this write."""
        if not previous:
            return False
        try:
            self._saved_account_current(previous, identity, account_id)
        except FindMySetupError:
            return False
        entry = self._findmy_config_entry()
        return (
            entry is not None
            and self.hass.config_entries.async_get_entry(entry.entry_id) is entry
        )

    async def _async_commit_saved_items(
        self, previous, selection, chosen, identity, identity_state=None
    ):
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
                identity_state = prepare_state(
                    latest["session"], current_items, {}, identity_state
                )
                write = self.hass.async_add_executor_job(
                    save_selection,
                    Vault(root),
                    latest["session"],
                    {identifier: current_items[identifier] for identifier in chosen},
                    identity_state,
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
                if (
                    wrote
                    and not committed
                    and self._findmy_revision_current(previous, identity)
                ):
                    # Metadata was not published. Keep the old live client and
                    # its complete item set consistent with the encrypted copy.
                    if identity_state is not None:
                        rollback = self.hass.async_add_executor_job(
                            partial(
                                Vault(root).save_account,
                                latest["session"],
                                account_items(latest),
                                identity_state=latest.get("identity_state"),
                            )
                        )
                    else:
                        rollback = self.hass.async_add_executor_job(
                            Vault(root).save_account,
                            latest["session"],
                            account_items(latest),
                        )
                    await _finish_saved_transaction(rollback)
                raise
            finally:
                owns_account = self._findmy_revision_current(previous, identity)
                if provider and not committed and owns_account:
                    provider.resume_account(account_id, paused)
                if paused and (committed or not owns_account):
                    try:
                        await paused.close()
                    except Exception:
                        pass  # The replacement is committed; a close error is not a failed save.

    async def async_commit_findmy(self, finalizer=None):
        if self.findmy_expire:
            self.findmy_expire()
            self.findmy_expire = None
        staged = deepcopy(getattr(self, "findmy_staged", {}))
        if not staged:
            return await finalizer() if finalizer else None
        self._findmy_created_stores = []
        task = self.findmy_commit_task = self.hass.async_create_background_task(
            self._async_commit_staged_findmy(staged, finalizer),
            "HomeCircle staged Find My item commit",
            eager_start=False,
        )
        try:
            return await _finish_saved_transaction(task)
        except asyncio.CancelledError:
            # A new config flow's result never reached HA's manager. It has no
            # attached entry to retain the just-created report capabilities.
            if not self._findmy_config_entry():
                from .findmy_storage import delete_account

                for metadata in self._findmy_created_stores:
                    await _finish_saved_transaction(
                        self.hass.async_add_executor_job(
                            delete_account, self.hass, metadata
                        )
                    )
            raise

    async def _async_commit_staged_findmy(self, staged, finalizer):
        from .findmy_reports import account_items
        from .findmy_storage import delete_account
        from . import frontend

        entry = self._findmy_config_entry()
        locks = self.hass.data.setdefault("homecircle_findmy_saved_transactions", {})
        records = []
        committed = False
        async with AsyncExitStack() as stack:
            for account_id in sorted(staged):
                lock = locks.setdefault(
                    (entry.entry_id if entry else None, account_id), asyncio.Lock()
                )
                await stack.enter_async_context(lock)
            checker = getattr(self, "_findmy_snapshot_current", None)
            if checker and not checker():
                raise FindMySetupError("findmy_settings_changed")
            try:
                for account_id, packed in staged.items():
                    metadata, session, items, *extra = packed
                    identity_state = extra[0] if extra else None
                    original = extra[1] if len(extra) > 1 else None
                    if entry and original:
                        self._saved_account_current(
                            original, metadata["account_identity"], account_id
                        )
                    elif entry and account_id in (entry.options or entry.data).get(
                        CONF_FINDMY_ACCOUNTS, {}
                    ):
                        raise FindMySetupError("findmy_settings_changed")
                    runtime = getattr(entry, "runtime_data", None) if entry else None
                    provider = (
                        runtime.managed_trackers.get("findmy")
                        if runtime and original
                        else None
                    )
                    paused = (
                        await provider.pause_account(account_id) if provider else None
                    )
                    record = {
                        "account_id": account_id,
                        "metadata": metadata,
                        "original": original,
                        "provider": provider,
                        "paused": paused,
                        "latest": None,
                        "wrote": False,
                        "created": False,
                    }
                    records.append(record)
                    root = record["root"] = await self.hass.async_add_executor_job(
                        account_root, self.hass, metadata, True
                    )
                    existed = await self.hass.async_add_executor_job(root.exists)
                    if original:
                        latest = record[
                            "latest"
                        ] = await self.hass.async_add_executor_job(Vault(root).load)
                        if (
                            account_identity(latest["session"])
                            != metadata["account_identity"]
                        ):
                            raise FindMySetupError("findmy_account_mismatch")
                        current_items = account_items(latest)
                        identity_state = prepare_state(
                            session, current_items, {}, identity_state
                        )
                        for identifier, selected in items.items():
                            saved = current_items.get(identifier, {})
                            material = accessory_material(selected["accessory"])
                            if (
                                material is not None
                                and accessory_material(saved.get("accessory", {}))
                                == material
                            ):
                                for field in ("report", "search_before"):
                                    if field in saved:
                                        selected[field] = deepcopy(saved[field])
                    elif existed:
                        raise FindMySetupError("findmy_saved_session_unavailable")
                    record["created"] = not existed
                    record["wrote"] = True
                    await _finish_saved_transaction(
                        self.hass.async_add_executor_job(
                            save_selection, Vault(root), session, items, identity_state
                        )
                    )
                    if record["created"]:
                        self._findmy_created_stores.append(metadata)
                if checker and not checker():
                    raise FindMySetupError("findmy_settings_changed")
                for record in records:
                    if entry and record["original"]:
                        self._saved_account_current(
                            record["original"],
                            record["metadata"]["account_identity"],
                            record["account_id"],
                        )
                self._findmy_defer_save = entry is not None
                try:
                    result = await finalizer() if finalizer else None
                finally:
                    self._findmy_defer_save = False
                if finalizer and result.get("type") is not FlowResultType.CREATE_ENTRY:
                    raise FindMySetupError("findmy_settings_changed")
                if entry:
                    options = result["data"] if finalizer else self.draft
                    if getattr(self, "source", None) == "reconfigure":
                        # Core's helper publishes data/options and schedules one
                        # reload synchronously before returning its success abort.
                        frontend.preserve_for_reload(self.hass, entry.entry_id)
                        result = self.async_update_reload_and_abort(
                            entry, data=options, options={}
                        )
                    else:
                        self.hass.config_entries.async_update_entry(
                            entry,
                            data={
                                **entry.data,
                                CONF_FINDMY_ACCOUNTS: options.get(
                                    CONF_FINDMY_ACCOUNTS, {}
                                ),
                            },
                            options=options,
                        )
                    committed = True
                    reset = getattr(self, "_reset_findmy_snapshot", None)
                    if reset:
                        reset()
                    if getattr(self, "source", None) != "reconfigure":
                        frontend.preserve_for_reload(self.hass, entry.entry_id)
                        self.hass.config_entries.async_schedule_reload(entry.entry_id)
                committed = True
                self.findmy_staged = {}
                return result
            except BaseException:
                for record in reversed(records):
                    if not record["wrote"] or committed:
                        continue
                    original = record["original"]
                    if original and self._findmy_revision_current(
                        original,
                        record["metadata"]["account_identity"],
                        record["account_id"],
                    ):
                        latest = record["latest"]
                        await _finish_saved_transaction(
                            self.hass.async_add_executor_job(
                                partial(
                                    Vault(record["root"]).save_account,
                                    latest["session"],
                                    account_items(latest),
                                    identity_state=latest.get("identity_state"),
                                )
                            )
                        )
                    elif record["created"] and (
                        not entry
                        or not any(
                            value.get("storage_id") == record["metadata"]["storage_id"]
                            for snapshot in (entry.data, entry.options)
                            for value in snapshot.get(CONF_FINDMY_ACCOUNTS, {}).values()
                        )
                    ):
                        await _finish_saved_transaction(
                            self.hass.async_add_executor_job(
                                delete_account, self.hass, record["metadata"]
                            )
                        )
                raise
            finally:
                for record in records:
                    provider, paused = record["provider"], record["paused"]
                    owns_account = record["original"] and self._findmy_revision_current(
                        record["original"],
                        record["metadata"]["account_identity"],
                        record["account_id"],
                    )
                    if provider and not committed and owns_account:
                        provider.resume_account(record["account_id"], paused)
                    if paused and (committed or not owns_account):
                        try:
                            await paused.close()
                        except Exception:
                            pass

    async def finish_findmy_setup(self):
        if self.findmy_expire:
            self.findmy_expire()
            self.findmy_expire = None
        if self.findmy_setup:
            await self.findmy_setup.close()
            self.findmy_setup = None

    async def async_step_findmy_disconnect(self, user_input=None):
        if user_input is not None and user_input.get("confirm"):
            previous = deepcopy(
                self.draft.get(CONF_FINDMY_ACCOUNTS, {}).get(self.findmy_account_id)
            )
            if previous is None:
                return self.async_abort(reason="findmy_account_mismatch")
            task = self.findmy_commit_task = self.hass.async_create_background_task(
                self._async_disconnect_findmy(previous),
                "HomeCircle Find My disconnect",
                eager_start=False,
            )
            try:
                return await _finish_saved_transaction(task)
            except Exception:
                return self.async_abort(reason="findmy_storage_failed")
        return self.async_show_form(
            step_id="findmy_disconnect",
            data_schema=vol.Schema(
                {vol.Required("confirm", default=False): selector.BooleanSelector()}
            ),
            description_placeholders={"account": label(self.findmy_label)},
        )

    async def _async_disconnect_findmy(self, previous):
        from .findmy_storage import delete_account
        from . import frontend
        from homeassistant.helpers import issue_registry as ir

        entry = self.config_entry
        account_id = self.findmy_account_id
        locks = self.hass.data.setdefault("homecircle_findmy_saved_transactions", {})
        lock = locks.setdefault((entry.entry_id, account_id), asyncio.Lock())
        async with lock:
            current, metadata = self._saved_account_current(
                previous, previous["account_identity"]
            )
            provider = None
            runtime = getattr(entry, "runtime_data", None)
            if runtime:
                provider = runtime.managed_trackers.get("findmy")
            paused = await provider.pause_account(account_id) if provider else None
            latest = None
            deleted = committed = False
            try:
                root = await self.hass.async_add_executor_job(
                    account_root, self.hass, metadata
                )
                try:
                    latest = await self.hass.async_add_executor_job(Vault(root).load)
                except VaultError:
                    # Explicit disconnect remains a way to remove an unreadable
                    # owned store. delete_account still enforces path safety.
                    latest = None
                deleted = True
                await _finish_saved_transaction(
                    self.hass.async_add_executor_job(
                        delete_account, self.hass, metadata
                    )
                )
                current, _ = self._saved_account_current(
                    previous, previous["account_identity"]
                )
                accounts = deepcopy(current[CONF_FINDMY_ACCOUNTS])
                accounts.pop(account_id)
                self.draft = {
                    **current,
                    CONF_FINDMY_ACCOUNTS: accounts,
                    CONF_FINDMY_ENABLED: bool(accounts),
                }
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={**entry.data, CONF_FINDMY_ACCOUNTS: accounts},
                    options=self.draft,
                )
                committed = True
                ir.async_delete_issue(
                    self.hass,
                    "homecircle",
                    f"findmy_auth_{entry.entry_id}_{account_id}",
                )
                frontend.preserve_for_reload(self.hass, entry.entry_id)
                self.hass.config_entries.async_schedule_reload(entry.entry_id)
                return self.async_create_entry(title="", data=self.draft)
            except BaseException:
                if (
                    deleted
                    and not committed
                    and latest is not None
                    and self._findmy_revision_current(
                        previous, previous["account_identity"]
                    )
                ):
                    from .findmy_reports import account_items

                    await _finish_saved_transaction(
                        self.hass.async_add_executor_job(
                            partial(
                                Vault(root).save_account,
                                latest["session"],
                                account_items(latest),
                                identity_state=latest.get("identity_state"),
                            )
                        )
                    )
                raise
            finally:
                owns_account = self._findmy_revision_current(
                    previous, previous["account_identity"]
                )
                if provider and not committed and owns_account:
                    provider.resume_account(account_id, paused)
                if paused and (committed or not owns_account):
                    try:
                        await paused.close()
                    except Exception:
                        pass
