"""Transient, read-only Apple onboarding, without a Rust helper or trust enrollment."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from hashlib import sha256
import logging
from .findmy_vault import passwordless
from .findmy_profile import configure_account


_LOGGER = logging.getLogger(__name__)


def require_nonempty_report_grant(account, session=None):
    """A completed Apple login alone cannot authorize a Find My connection."""
    try:
        token = account.service_tokens.get("searchPartyToken")
        if not isinstance(token, str) or not token.strip():
            raise ValueError
        if session is not None:
            saved = session["login"]["data"]["mobileme_data"]["tokens"].get(
                "searchPartyToken"
            )
            if not isinstance(saved, str) or not saved.strip() or saved != token:
                raise ValueError
    except Exception:
        # This account is transient. Do not retain a password/PET while showing
        # a service-grant failure, or let a later step try recovery with it.
        for attribute in ("_password", "_recovery_pet", "_recovery_pet_at", "_gsa_pet_at"):
            if hasattr(account, attribute):
                setattr(account, attribute, None)
        raise FindMySetupError("findmy_report_access_unavailable") from None


def signin_error(error, stage):
    """Map failures to fixed codes; never expose exception text or responses."""
    if stage == "recovery":
        code = recovery_error(error)
        _LOGGER.warning("Find My setup failed: stage=recovery code=%s", code)
        return code
    from aiohttp import ClientError
    from ._vendor_findmy.errors import (
        InvalidCredentialsError,
        UnauthorizedError,
        AppleServiceUnavailableError,
        MobileMeDelegateError,
        UnhandledProtocolError,
        InvalidStateError,
    )

    if stage == "identity":
        code = "findmy_identity_failed"
    elif isinstance(error, TimeoutError):
        code = "findmy_signin_timeout"
    elif isinstance(error, (ClientError, OSError)):
        code = "findmy_signin_network"
    elif isinstance(error, AppleServiceUnavailableError):
        code = "findmy_apple_unavailable"
        status = error.status_code
        status = status if type(status) is int and 100 <= status <= 599 else None
        request = {"The Grand Slam request": "gsa", "The two-factor request": "verification"}.get(error.what, "unknown")
        retry = error.retry_after
        retry = int(retry) if type(retry) in (int, float) and 0 <= retry <= 86400 else None
        phase = getattr(error, "phase", None)
        phase = phase if phase in ("init", "complete") else None
        _LOGGER.warning(
            "Find My service refusal: request=%s http=%s retry_after_seconds=%s phase=%s",
            request, status, retry, phase,
        )
    elif isinstance(error, MobileMeDelegateError):
        code = "findmy_account_attention"
    elif isinstance(error, InvalidCredentialsError) and error.phase == "init":
        # This precedes password proof. It cannot establish that the supplied
        # password was wrong, even when Apple's library calls it credentials.
        code = "findmy_initial_refused"
    elif isinstance(error, (InvalidCredentialsError, UnauthorizedError)):
        code = (
            "findmy_credentials_rejected"
            if stage == "signin"
            else "findmy_recovery_failed"
        )
    elif isinstance(error, InvalidStateError):
        code = "findmy_signin_state"
    elif isinstance(error, UnhandledProtocolError):
        code = "findmy_apple_protocol"
    else:
        code = (
            "findmy_recovery_failed" if stage == "recovery" else "findmy_signin_failed"
        )
    if isinstance(error, InvalidCredentialsError):
        apple_code = error.status_code
        phase = error.phase
        _LOGGER.warning(
            "Find My Apple rejection: phase=%s apple_code=%s", phase, apple_code
        )
    _LOGGER.warning("Find My setup failed: stage=%s code=%s", stage, code)
    return code


class FindMySetupError(RuntimeError):
    """Only fixed error codes may reach the UI."""


def recovery_error(error):
    """Use structured outcomes, never a provider message or old diagnostics."""
    from aiohttp import ClientError
    from .findmy_identity import IdentityError
    from .findmy_recovery_guard import RecoveryGuardBlocked, RecoveryGuardStorageError
    from ._findmy_runtime.onboarding import RecoveryPETError
    from ._vendor_findmy.errors import UnauthorizedError
    from ._vendor_findmy.keychain.recovery import RecoveryProtocolError

    if isinstance(error, RecoveryGuardBlocked):
        return "findmy_recovery_limit"
    if isinstance(error, RecoveryGuardStorageError):
        return "findmy_recovery_storage"
    if isinstance(error, IdentityError):
        return str(error) if str(error) in {
            "findmy_identity_unavailable", "findmy_duplicate_item",
            "findmy_missing_item_identity",
        } else "findmy_identity_unavailable"
    if isinstance(error, RecoveryPETError):
        if error.reason == "transient" and type(error.http_status) is int and error.http_status == 429:
            return "findmy_recovery_rate_limited"
        return {
            "identity_mismatch": "findmy_account_mismatch",
            "transient": "findmy_recovery_transient",
            "protocol": "findmy_recovery_protocol",
        }.get(error.reason, "findmy_recovery_signin_required")
    if isinstance(error, RecoveryProtocolError):
        if error.dispatch_state == "not_dispatched" and error.reason == "transient":
            return "findmy_recovery_transient"
        return {
            "refused": "findmy_recovery_refused",
            "uncertain": "findmy_recovery_uncertain",
            "verified": "findmy_recovery_material_failed",
        }.get(error.dispatch_state, "findmy_recovery_protocol")
    if isinstance(error, (TimeoutError, ClientError, OSError)):
        return "findmy_recovery_transient"
    if isinstance(error, UnauthorizedError):
        return "findmy_recovery_signin_required"
    return "findmy_recovery_failed"


def log_identity_failure(account):
    """Record only the native provider's fixed, bounded diagnostic projection."""
    provider = getattr(account, "_anisette", None)
    if getattr(provider, "_homecircle_mac", False):
        try:
            safe = provider.safe_diagnostics()
        except Exception:
            return
        _LOGGER.warning("Find My identity unavailable: diagnostics=%s", safe)


def log_signin_failure(account):
    """Retain request-stage evidence without response or account identifiers."""
    getter = getattr(account, "signin_diagnostics", None)
    if not callable(getter):
        return
    try:
        raw = getter()
    except Exception:
        return
    if type(raw) is not dict:
        return

    def integer(name, low, high):
        value = raw.get(name)
        return value if type(value) is int and low <= value <= high else None

    phase = raw.get("phase")
    profile = raw.get("profile")
    media_type = raw.get("media_type")
    body_size = raw.get("body_size")
    safe = {
        "schema": 1,
        "phase": phase if type(phase) is str and phase in ("init", "complete") else None,
        "request_count": integer("request_count", 0, 8),
        "http": integer("http", 100, 599),
        "apple_code": integer("apple_code", -1000000, 1000000),
        "apple_hsc": integer("apple_hsc", -1000000, 1000000),
        "profile": profile if type(profile) is str and profile in (
            "mac_coreadi_v1", "windows_onboarding_v1", "legacy"
        ) else None,
        "media_type": media_type if type(media_type) is str and media_type in (
            "plist", "xml", "html", "json", "other", "missing"
        ) else None,
        "body_size": body_size if type(body_size) is str and body_size in (
            "empty", "small", "medium", "large"
        ) else None,
    }
    _LOGGER.warning("Find My sign-in diagnostics: %s", safe)


def sdk():
    """Isolate dependency logs and namespace from other installed FindMy integrations."""
    package = "custom_components.homecircle._vendor_findmy"

    def isolate_logs():
        # Parent.disabled does not stop child records from propagating. A sink
        # with propagation disabled also covers dependency loggers created later.
        namespaces = (package, "anisette")
        for namespace in namespaces:
            logger = logging.getLogger(namespace)
            logger.handlers[:] = [logging.NullHandler()]
            logger.propagate = False
            logger.disabled = True
            logger.setLevel(logging.CRITICAL + 1)
        # Existing descendants might have their own handlers or explicit levels.
        # Inspect only the in-memory registry, never module files on HA's loop.
        for name, logger in tuple(logging.Logger.manager.loggerDict.items()):
            if isinstance(logger, logging.Logger) and any(
                name.startswith(namespace + ".") for namespace in namespaces
            ):
                logger.handlers[:] = [logging.NullHandler()]
                logger.propagate = False
                logger.disabled = True

    isolate_logs()
    from ._vendor_findmy import AsyncAppleAccount, LocalAnisetteProvider, LoginState
    from ._vendor_findmy.icloud import AsyncFindMyClient

    isolate_logs()

    return AsyncAppleAccount, LocalAnisetteProvider, LoginState, AsyncFindMyClient


def safe_label(value, fallback, limit=80):
    if not isinstance(value, str):
        return fallback
    value = " ".join(value.split())[:limit]
    return value or fallback


def device_label(record):
    name = safe_label(record.device_name or record.device_model, "Trusted Apple device")
    serial = safe_label(record.serial, "")
    return f"{name} (ending {serial[-4:]})" if serial else name


def accessory_id(item):
    """Names and absent IDs must never merge unrelated accessories."""
    identifier = item.identifier
    if isinstance(identifier, str) and identifier:
        value = "id:" + identifier
    else:
        master = item.to_json().get("master_key")
        if not isinstance(master, str) or not master:
            raise FindMySetupError("findmy_missing_item_identity")
        value = "key:" + master
    return sha256(value.encode()).hexdigest()


class FindMySetup:
    """No credentials, passcodes or broader Keychain keys are saved by this object."""

    def __init__(self, account, client_factory, states):
        self.account = account
        self.client_factory = client_factory
        self.states = states
        self.client = None
        self.methods, self.records, self.accessories = [], [], {}
        self.factor = None
        self.closed = False
        self.unlock_attempts = 0
        self.recovery_guard = None
        self.recovery_guard_required = False
        self.recovery_outcome = None
        self.previous_items = {}
        self.discover_new = True
        self.account_guard = None
        self.keys_recovered = False
        self.zone_checker = None
        self.settings_pair_tested = False
        self.additional_verification = False
        self.verification_challenges = 0
        self.verification_exhausted = False

    @classmethod
    def create(cls, libraries, session=None, *, onboarding=True):
        account_type, provider_type, states, client_type = sdk()
        from ._vendor_findmy.reports.endpoint_policy import (
            MAC_COREADI_V1,
            WINDOWS_ONBOARDING_V1,
            restore_policy,
        )

        replace_legacy_identity = (
            onboarding and session is not None
            and session.get("anisette", {}).get("type") in {"aniLocal", "aniRemote"}
        )
        if session is None or replace_legacy_identity:
            # Explicit reconnect upgrades earlier development identities. The
            # saved report connection remains unchanged until confirmation;
            # account_guard still requires the same authenticated Apple DSID.
            if replace_legacy_identity:
                restore_policy(session.get("endpoint_policy"))
            if onboarding:
                from ._findmy_runtime.provider import MacAnisetteProvider

                provider = MacAnisetteProvider(libs_path=libraries)
            else:
                provider = provider_type(libs_path=libraries)
            account = account_type(
                provider,
                device_name="HomeCircle Find My",
                timeout=30,
                endpoint_policy=MAC_COREADI_V1 if onboarding else None,
                **({"uid": provider.local_user_uuid, "devid": provider.device_uuid}
                   if onboarding else {}),
            )
        else:
            # Reuse the local device and anisette identity without reusing auth tokens.
            state = deepcopy(session)
            state["account"]["password"] = None
            state["account"]["info"] = None
            state["login"] = {"state": 0, "data": {}}
            if onboarding:
                # This is an explicit fresh-credential reconnect, never the
                # saved report client. Leave the original session and IDs intact.
                restore_policy(state.get("endpoint_policy"))
                state["endpoint_policy"] = (
                    MAC_COREADI_V1.name
                    if state.get("anisette", {}).get("type") == "aniMac"
                    else WINDOWS_ONBOARDING_V1.name
                )
            account = account_type.from_json(state, anisette_libs_path=libraries)
        setup = cls(account, client_type.open, states)
        setup.recovery_guard_required = True
        configure_account(account)
        return setup

    async def login(self, username, password):
        if self.closed:
            raise FindMySetupError("findmy_setup_closed")
        self.additional_verification = False
        self.verification_challenges = 0
        self.verification_exhausted = False
        stage = "identity"
        try:
            async with asyncio.timeout(420):
                provider = getattr(self.account, "_anisette", None)
                if provider is not None:
                    # Restore/provision the account-bound provider without
                    # changing either side of its retained identity binding.
                    await provider._get_ani()
                stage = "signin"
                state = await self.account.login(username.strip(), password)
                if self.closed:
                    raise FindMySetupError("findmy_setup_closed")
                if state == self.states.REQUIRE_2FA:
                    stage = "verification"
                    self.methods = list(await self.account.get_2fa_methods())
                    return "factor"
                if state == self.states.LOGGED_IN:
                    if self.account_guard and not self.account_guard(
                        self.account.to_json()
                    ):
                        raise FindMySetupError("findmy_account_mismatch")
                    await self.ensure_report_access()
                    if self.previous_items and not self.discover_new:
                        self.account._password = None
                        self.restore_selected_items()
                        return "select"
                    stage = "recovery"
                    await self.prepare_recovery()
                    return "device"
            raise FindMySetupError("findmy_account_attention")
        except FindMySetupError:
            raise
        except Exception as error:
            if stage == "identity":
                log_identity_failure(self.account)
            elif stage == "signin":
                log_signin_failure(self.account)
            raise FindMySetupError(signin_error(error, stage)) from None

    async def prepare_identity(self):
        """Acquire public software and provision before asking for a password."""
        if self.closed:
            raise FindMySetupError("findmy_setup_closed")
        try:
            async with asyncio.timeout(720):
                await self.account._anisette._get_ani()
            if self.closed:
                raise FindMySetupError("findmy_setup_closed")
        except asyncio.CancelledError:
            raise
        except Exception:
            log_identity_failure(self.account)
            raise FindMySetupError("findmy_identity_failed") from None

    def factor_choices(self):
        return [
            {
                "value": str(i),
                "label": "Apple trusted-device code"
                if "Trusted" in type(method).__name__
                else "Apple SMS verification",
            }
            for i, method in enumerate(self.methods)
        ]

    async def request_code(self, index):
        try:
            self.factor = self.methods[int(index)]
            async with asyncio.timeout(60):
                await self.factor.request()
        except Exception:
            raise FindMySetupError("findmy_code_request_failed") from None

    async def verify_code(self, code):
        if self.verification_exhausted:
            raise FindMySetupError("findmy_verification_limit")
        if self.factor is None:
            raise FindMySetupError("findmy_code_request_failed")
        stage = "verification"
        try:
            async with asyncio.timeout(120):
                state = await self.factor.submit(code)
                if state == self.states.REQUIRE_2FA:
                    self.factor = None
                    self.additional_verification = True
                    self.verification_challenges += 1
                    if self.verification_challenges > 2:
                        self.verification_exhausted = True
                        raise FindMySetupError("findmy_verification_limit")
                    self.methods = list(await self.account.get_2fa_methods())
                    if not self.methods:
                        raise FindMySetupError("findmy_account_attention")
                    return "factor"
                if state != self.states.LOGGED_IN:
                    raise FindMySetupError("findmy_account_attention")
                self.additional_verification = False
                if self.account_guard and not self.account_guard(
                    self.account.to_json()
                ):
                    raise FindMySetupError("findmy_account_mismatch")
                await self.ensure_report_access()
                if self.previous_items and not self.discover_new:
                    self.restore_selected_items()
                    return "select"
                stage = "recovery"
                await self.prepare_recovery()
        except FindMySetupError:
            raise
        except Exception as error:
            from ._vendor_findmy.errors import InvalidCredentialsError

            phase = getattr(self.account, "_verification_stage", None)
            phase = phase if phase in ("validation", "reauthentication", "delegate", "complete") else "unknown"
            status = getattr(self.account, "_verification_http_status", None)
            status = status if type(status) is int and 100 <= status <= 599 else None
            apple_code = error.status_code if isinstance(error, InvalidCredentialsError) else None
            apple_code = apple_code if type(apple_code) is int and abs(apple_code) <= 1000000 else None
            srp = getattr(error, "phase", None)
            srp = srp if srp in ("init", "complete") else None
            login_state = getattr(self.account, "_verification_login_state", None)
            login_state = login_state if login_state in ("REQUIRE_2FA", "AUTHENTICATED", "LOGGED_IN") else None
            if phase == "reauthentication":
                log_signin_failure(self.account)
            _LOGGER.warning(
                "Find My verification failed: stage=%s phase=%s validation_http=%s apple_code=%s srp=%s login_state=%s",
                stage, phase, status, apple_code, srp, login_state,
            )
            if phase == "delegate":
                diagnostics = getattr(self.account, "_delegate_diagnostics", {})
                safe = {}
                for key in ("http", "top_status", "service_status"):
                    value = diagnostics.get(key)
                    safe[key] = value if type(value) is int and abs(value) <= 1000000 else None
                for key in ("pet_present", "localized_error_present", "unauthorized"):
                    value = diagnostics.get(key)
                    safe[key] = value if type(value) is bool else None
                _LOGGER.warning("Find My delegate failed: diagnostics=%s", safe)
            failure = {
                "reauthentication": "findmy_code_signin_failed",
                "delegate": "findmy_code_delegate_failed",
            }.get(phase, "findmy_code_failed")
            if stage == "recovery":
                failure = recovery_error(error)
            raise FindMySetupError(failure) from None

    async def ensure_report_access(self):
        """Check the normal settings response before declaring tracking unavailable."""
        try:
            token = self.account.service_tokens.get("searchPartyToken")
            if not isinstance(token, str) or not token.strip():
                # A new delegation may share the diagnostic dictionary with an
                # earlier attempt. Do not report its old response after a new
                # settings request fails before receiving an HTTP response.
                if getattr(self.account, "_settings_tokens_attempted", None) is False:
                    raw = getattr(self.account, "_recovery_diagnostics", None)
                    if isinstance(raw, dict):
                        for key in (
                            "settings_http",
                            "settings_status",
                            "settings_searchparty_token_present",
                        ):
                            raw.pop(key, None)
                async with asyncio.timeout(60):
                    await self.account.ensure_report_token()
        except Exception:
            # The fixed grant error covers absence, refusal and invalid replies.
            # Never retry authentication or expose dependency response text.
            pass
        try:
            require_nonempty_report_grant(self.account)
        except FindMySetupError:
            raw = getattr(self.account, "_recovery_diagnostics", None)
            raw = raw if isinstance(raw, dict) else {}
            attempted = getattr(self.account, "_settings_tokens_attempted", None)
            safe = {
                "settings_attempted": attempted if type(attempted) is bool else None,
                "report_grant_accepted": False,
            }
            try:
                held = self.account.service_tokens.get("searchPartyToken")
                safe["held_report_token_present"] = (
                    isinstance(held, str) and bool(held.strip())
                )
            except Exception:
                safe["held_report_token_present"] = None
            for key in (
                "delegate_searchparty_token_present",
                "settings_searchparty_token_present",
            ):
                value = raw.get(key)
                safe[key] = value if type(value) is bool else None
            value = raw.get("settings_http")
            safe["settings_http"] = (
                value if type(value) is int and 100 <= value <= 599 else None
            )
            value = raw.get("settings_status")
            safe["settings_status"] = (
                value if type(value) is int and abs(value) <= 1000000 else None
            )
            _LOGGER.warning(
                "Find My tracking credential unavailable: diagnostics=%s", safe
            )
            raise

    def restore_selected_items(self):
        from ._vendor_findmy import FindMyAccessory

        self.accessories = {
            identifier: FindMyAccessory.from_json(item["accessory"])
            for identifier, item in self.previous_items.items()
        }
        self.account._password = None

    async def check_zone_access(self):
        """Read zone metadata before asking for any device unlock passcode."""
        if self.closed:
            raise FindMySetupError("findmy_setup_closed")
        client = None
        try:
            async with asyncio.timeout(60):
                if self.zone_checker is not None:
                    await self.zone_checker()
                else:
                    from ._vendor_findmy.cloudkit.client import AsyncCloudKitClient
                    from ._vendor_findmy.errors import UnauthorizedError
                    client = AsyncCloudKitClient(self.account)
                    self.account._recovery_diagnostics["zone_profile"] = "1970"
                    self.account._recovery_diagnostics["zone_token_pair"] = "original"
                    self.account._recovery_diagnostics.pop("operation_http", None)
                    for key in tuple(self.account._recovery_diagnostics):
                        if key.startswith("route_"):
                            self.account._recovery_diagnostics.pop(key)
                    self.account._recovery_diagnostics.pop("zone_baseline_http", None)
                    try:
                        await client.zone_retrieve("BeaconStore")
                    except UnauthorizedError:
                        baseline = self.account._recovery_diagnostics.get("operation_http")
                        pair = getattr(self.account, "_settings_cloudkit_pair", None)
                        original = self.account.service_tokens
                        available = isinstance(pair, dict) and all(
                            isinstance(pair.get(key), str) and pair[key]
                            for key in ("mmeAuthToken", "cloudKitToken"))
                        changed = available and any(pair[key] != original.get(key)
                                                    for key in ("mmeAuthToken", "cloudKitToken"))
                        self.account._recovery_diagnostics["settings_pair_available"] = bool(available)
                        self.account._recovery_diagnostics["settings_pair_changed"] = bool(changed)
                        if baseline != 401 or self.settings_pair_tested or not changed:
                            raise
                        self.settings_pair_tested = True
                        await client.close()
                        # Replace only these two credentials for one read-only check.
                        # Keep all report tokens and restore the original map on failure.
                        merged = dict(original)
                        merged.update({key: pair[key] for key in ("mmeAuthToken", "cloudKitToken")})
                        self.account._login_state_data["mobileme_data"]["tokens"] = merged
                        accepted = False
                        try:
                            client = AsyncCloudKitClient(self.account)
                            self.account._recovery_diagnostics["zone_token_pair"] = "settings"
                            self.account._recovery_diagnostics["zone_baseline_http"] = baseline
                            self.account._recovery_diagnostics.pop("operation_http", None)
                            await client.zone_retrieve("BeaconStore")
                            accepted = True
                            _LOGGER.warning("Find My token pair comparison: baseline_http=401 settings_pair_http=200")
                        finally:
                            if not accepted:
                                self.account._login_state_data["mobileme_data"]["tokens"] = original
        except Exception:
            raw = getattr(self.account, "_recovery_diagnostics", {})
            safe = {}
            for key in ("cloudkit_http", "operation_http", "zone_baseline_http", "transport_http", "route_http"):
                value = raw.get(key)
                safe[key] = value if type(value) is int and 100 <= value <= 599 else None
            for key in ("mme_token_present", "cloudkit_token_present", "settings_pair_available", "settings_pair_changed",
                        "verification_pet_header_usable", "verification_hb_header_usable",
                        "verification_pet_matches_adsid", "verification_pet_matches_canonical", "verification_pet_matches_response_dsid",
                        "canonical_account_present", "canonical_matches_input", "delegate_mme_token_present", "delegate_cloudkit_token_present",
                        "delegate_searchparty_token_present", "settings_searchparty_token_present"):
                value = raw.get(key)
                safe[key] = value if type(value) is bool else None
            for key, allowed in (
                ("transport_protocol", ("HTTP/1.0", "HTTP/1.1", "HTTP/2", "other")),
                ("transport_error", ("none", "blocked_url", "ImportError", "ModuleNotFoundError", "ConnectError", "ReadTimeout", "SSLCertVerificationError", "other")),
                ("transport_body_kind", ("json", "plist", "html", "text", "protobuf", "empty", "unknown")),
                ("transport_media_type", ("json", "plist", "xml", "html", "text", "protobuf", "none", "other")),
                ("operation_media_type", ("json", "plist", "xml", "html", "text", "protobuf", "none", "other")),
                ("operation_body_kind", ("json", "plist", "html", "text", "protobuf", "empty", "unknown")),
                ("operation_body_size", ("empty", "small", "medium", "large", "oversize")),
                ("operation_server_family", ("apple", "cloudkit", "none", "other")),
                ("operation_auth_scheme", ("Basic", "Bearer", "none", "other")),
                ("operation_server_code", ("AUTHENTICATION_FAILED", "AUTHENTICATION_REQUIRED", "ACCESS_DENIED", "none", "other")),
            ):
                value = raw.get(key)
                safe[key] = value if value in allowed else None
            for key in ("operation_error_code", "operation_result_code"):
                value = raw.get(key)
                safe[key] = value if type(value) is int and abs(value) <= 1000000 else None
            for key in ("delegate_top_status", "delegate_service_status"):
                value = raw.get(key)
                safe[key] = value if type(value) is int and abs(value) <= 1000000 else None
            result = raw.get("verification_pet_header_result")
            safe["verification_pet_header_result"] = result if result in (
                "absent", "malformed", "conflicting", "missing_principal", "principal_mismatch", "usable"
            ) else None
            origin = raw.get("verification_token_source")
            safe["verification_token_source"] = origin if origin in ("response_headers", "srp") else None
            source = raw.get("cloudkit_token_source")
            safe["cloudkit_token_source"] = source if source in ("delegate", "settings", "unknown") else None
            pair_label = raw.get("zone_token_pair")
            safe["zone_token_pair"] = pair_label if pair_label in ("original", "settings") else None
            profile = raw.get("zone_profile")
            safe["zone_profile"] = profile if profile in ("1970", "479") else None
            safe["route_profile"] = raw.get("route_profile") if raw.get("route_profile") in ("1970", "479") else None
            safe["route_token_pair"] = raw.get("route_token_pair") if raw.get("route_token_pair") in (
                "original", "settings", "unknown") else None
            safe["route_kind"] = raw.get("route_kind") if raw.get("route_kind") in (
                "shared", "partition", "missing", "blocked") else None
            safe["route_error"] = raw.get("route_error") if raw.get("route_error") in (
                "none", "same_route", "unavailable", "blocked_baseline", "request_failed") else None
            _LOGGER.warning("Find My zone access failed: diagnostics=%s", safe)
            raise FindMySetupError("findmy_zone_denied" if safe.get("operation_http") == 401 else "findmy_zone_failed") from None
        finally:
            if client is not None:
                await client.close()

    async def prepare_recovery(self):
        await self.check_zone_access()
        await self.open_recovery()

    async def retry_discovery(self):
        if not self.keys_recovered:
            raise FindMySetupError("findmy_setup_closed")
        return await self.discover(None, None)

    async def open_recovery(self):
        if self.closed:
            raise FindMySetupError("findmy_setup_closed")
        if self.client:
            await self.client.close()
        self.account._recovery_diagnostics = {"phase": "client_open"}
        try:
            self.client = await self.client_factory(self.account)
            if self.closed:
                await self.client.close()
                raise FindMySetupError("findmy_setup_closed")
            self.account._recovery_diagnostics["phase"] = "escrow_records"
            options = await self.client.recovery_options()
        except Exception as error:
            raw = self.account._recovery_diagnostics
            phase = raw.get("phase")
            phase = phase if phase in ("client_open", "account_settings", "cloudkit_container", "cloudkit_function", "partition", "pet_refresh", "escrow_client", "escrow_records") else "unknown"
            safe = {"phase": phase}
            for key in ("settings_http", "cloudkit_http", "escrow_http", "operation_http"):
                value = raw.get(key)
                safe[key] = value if type(value) is int and 100 <= value <= 599 else None
            for key in ("mme_token_present", "cloudkit_token_present", "cloudkit_body_present", "cloudkit_json_object", "cloudkit_user_present", "database_gateway_present", "code_gateway_present", "settings_searchparty_token_present"):
                value = raw.get(key)
                safe[key] = value if type(value) is bool else None
            candidate = raw.get("settings_candidate")
            safe["settings_candidate"] = candidate if candidate in ("android", "ios_settings") else None
            status = raw.get("settings_status")
            safe["settings_status"] = status if type(status) is int and -100000 <= status <= 100000 else None
            value = raw.get("settings_tokens_present")
            safe["settings_tokens_present"] = value if type(value) is bool else None
            for key in ("database_url_shape", "share_url_shape"):
                value = raw.get(key)
                safe[key] = value if value in ("string", "object", "missing", "other") else None
            from ._findmy_runtime.onboarding import RecoveryPETError

            if isinstance(error, RecoveryPETError):
                reason = error.reason
                safe["recovery_credential_reason"] = reason if type(reason) is str and reason in (
                    "missing_password", "factor_required", "identity_mismatch",
                    "transient", "protocol", "credentials",
                ) else None
                status = error.http_status
                safe["recovery_credential_http"] = status if type(status) is int and 100 <= status <= 599 else None
                auth_phase = error.auth_phase
                safe["recovery_credential_phase"] = (
                    auth_phase if type(auth_phase) is str and auth_phase in ("init", "complete") else None
                )
                retry = error.retry_after_seconds
                safe["recovery_credential_retry_after_seconds"] = (
                    retry if type(retry) is int and 0 <= retry <= 86400 else None
                )
            name = type(error).__name__
            safe["error_class"] = name if name in (
                "AttributeError", "TypeError", "KeyError", "ValueError", "KeychainSessionError",
                "RecoveryPETError",
                "UnhandledProtocolError", "UnauthorizedError", "TimeoutError", "ClientError",
            ) else "other"
            site = error.__traceback__
            while site and site.tb_next:
                site = site.tb_next
            name = site.tb_frame.f_code.co_name if site else None
            safe["error_site"] = name if name in ("partition", "open_container", "open", "_require_partition", "invoke_function", "function_invoke", "_post_operation") else "other"
            value = raw.get("pet_source")
            safe["pet_source"] = value if value in ("recent_login", "reauthentication") else None
            _LOGGER.warning("Find My recovery bootstrap failed: diagnostics=%s", safe)
            self.account._password = None
            self.account._recovery_pet = None
            self.account._recovery_pet_at = None
            raise
        self.records = list(options.recoverable)
        if not self.records:
            raise FindMySetupError("findmy_no_recovery_device")

    def device_choices(self):
        return [
            {"value": str(i), "label": device_label(record)}
            for i, record in enumerate(self.records)
        ]

    async def _unlock(self, index, passcode):
        """Scope the durable proof guard to one authenticated account's unlock."""
        from .findmy_identity import authenticated_identity

        self.recovery_outcome = None
        guard = self.recovery_guard
        if guard is None and self.recovery_guard_required:
            raise FindMySetupError("findmy_recovery_storage")
        self.unlock_attempts += 1  # Invocation diagnostic, not Apple's attempt count.
        record = self.records[int(index)]
        if guard is None:
            return await self.client.unlock(record, passcode)
        identity = authenticated_identity(self.account.to_json())
        if identity is None or (
            self.account_guard and not self.account_guard(self.account.to_json())
        ):
            raise FindMySetupError("findmy_account_mismatch")
        self.account._homecircle_recovery_guard_required = True
        async with guard.attempt(identity) as attempt:
            self.account._homecircle_recovery_attempt = attempt
            try:
                keys = await self.client.unlock(record, passcode)
                self.recovery_outcome = getattr(attempt, "outcome", None)
                return keys
            except BaseException:
                self.recovery_outcome = getattr(attempt, "outcome", None) or (
                    "uncertain" if getattr(attempt, "ready", False)
                    else "not_dispatched"
                )
                raise
            finally:
                self.account._homecircle_recovery_attempt = None

    def can_resume_recovery(self, index):
        """Only the SDK's same-record verified in-memory material permits retry."""
        checker = getattr(self.client, "can_resume_unlock", None)
        try:
            return callable(checker) and checker(self.records[int(index)]) is True
        except (ValueError, TypeError, IndexError):
            return False

    async def discover(self, index, passcode):
        if self.closed:
            raise FindMySetupError("findmy_setup_closed")
        if (
            self.recovery_guard is None and not self.keys_recovered
            and self.unlock_attempts >= 3
        ):
            raise FindMySetupError("findmy_recovery_limit")
        self.account._recovery_diagnostics["unlock_phase"] = "unlock"
        try:
            async with asyncio.timeout(120):
                if not self.keys_recovered:
                    self.account._recovery_diagnostics.pop("recovered_keys_present", None)
                    keys = await self._unlock(index, passcode)
                    self.account._recovery_diagnostics["recovered_keys_present"] = bool(keys)
                    if not keys:
                        from ._vendor_findmy.keychain import KeychainSessionError

                        self.account._recovery_diagnostics["unlock_phase"] = "pcs_keys"
                        if self.recovery_outcome == "verified":
                            from ._vendor_findmy.keychain.recovery import RecoveryProtocolError

                            raise RecoveryProtocolError("material", "verified")
                        raise KeychainSessionError("Recovery returned no keychain keys")
                    self.keys_recovered = True
                self.account._recovery_diagnostics["unlock_phase"] = "accessories"
                found = await self.client.accessories()
                if self.closed:
                    raise FindMySetupError("findmy_setup_closed")
                from .findmy_identity import (
                    accessory_material, new_state, prepare_state, resolve_identifier,
                )

                session = self.account.to_json()
                self.identity_state = prepare_state(
                    session, self.previous_items, {}, getattr(self, "identity_state", None)
                )
                if self.identity_state is None and any(
                    accessory_material(item.to_json()) for item in found
                ):
                    self.identity_state = new_state(session)
                discovered = {}
                discovered_material = set()
                for item in found:
                    exported = item.to_json()
                    material = accessory_material(exported)
                    if material is not None:
                        if material in discovered_material:
                            raise FindMySetupError("findmy_duplicate_item")
                        discovered_material.add(material)
                    identifier = resolve_identifier(
                        exported, accessory_id(item), self.previous_items, self.identity_state
                    )
                    if identifier in discovered:
                        raise FindMySetupError("findmy_duplicate_item")
                    discovered[identifier] = item
                self.accessories = discovered
            return self.item_choices()
        except FindMySetupError:
            raise
        except Exception as error:
            raw = self.account._recovery_diagnostics
            phase = raw.get("unlock_phase")
            phases = ("unlock", "escrow_recovery", "srp_init", "srp_proof", "escrow_recover", "server_proof", "outer_decrypt", "inner_decrypt", "bottle_material", "peer_directory", "bottle_keys", "pcs_keys", "accessories")
            safe = {"phase": phase if phase in phases else "unknown"}
            present = raw.get("recovered_keys_present")
            safe["recovered_keys_present"] = present if type(present) is bool else None
            name = type(error).__name__
            safe["error_class"] = name if name in ("EscrowError", "RecoveryError", "KeychainSessionError", "CloudKitError", "UnauthorizedError", "UnhandledProtocolError", "InvalidTag", "InvalidSignature", "ValueError", "KeyError", "TypeError", "DecodeError", "TimeoutError") else "other"
            for key in ("escrow_http", "operation_http"):
                value = raw.get(key)
                safe[key] = value if type(value) is int and 100 <= value <= 599 else None
            value = raw.get("operation_type")
            safe["operation_type"] = value if type(value) is int and 0 <= value <= 10000 else None
            value = raw.get("escrow_code")
            safe["escrow_code"] = value if type(value) is int and abs(value) <= 1000000 else None
            _LOGGER.warning("Find My item recovery failed: diagnostics=%s", safe)
            code = recovery_error(error)
            if self.recovery_outcome == "uncertain" and isinstance(error, TimeoutError):
                code = "findmy_recovery_uncertain"
            if not self.keys_recovered and (
                code == "findmy_recovery_material_failed" or (
                    isinstance(error, TimeoutError) and self.recovery_outcome == "verified"
                )
            ):
                code = (
                    "findmy_recovery_resume" if self.can_resume_recovery(index)
                    else "findmy_recovery_material_failed"
                )
            raise FindMySetupError(code) from None
        finally:
            # Report fetching must never silently retry using a retained password.
            if hasattr(self.account, "_password"):
                self.account._password = None

    def item_choices(self):
        return [
            {"value": identifier, "label": safe_label(item.name, "Find My item")}
            for identifier, item in self.accessories.items()
        ]

    def selected_payload(self, chosen):
        if (
            self.closed
            or not chosen
            or len(chosen) != len(set(chosen))
            or any(identifier not in self.accessories for identifier in chosen)
        ):
            raise FindMySetupError("findmy_select_items")
        require_nonempty_report_grant(self.account)
        session = passwordless(self.account.to_json())
        require_nonempty_report_grant(self.account, session)
        items = {
            identifier: {
                "accessory": self.accessories[identifier].to_json(),
                "report": deepcopy(
                    self.previous_items.get(identifier, {}).get("report")
                ),
            }
            for identifier in chosen
        }
        from .findmy_identity import selection_state

        self.identity_state = selection_state(
            session, items, {}, getattr(self, "identity_state", None)
        )
        return session, items

    async def close(self):
        if self.closed:
            return
        self.closed = True
        self.keys_recovered = False
        self.account._homecircle_recovery_attempt = None
        self.identity_state = None
        self.accessories.clear()
        self.previous_items.clear()
        self.records.clear()
        self.methods.clear()
        self.factor = None
        if hasattr(self.account, "_password"):
            self.account._password = None
        try:
            if self.client:
                await self.client.close()
        except Exception:
            pass  # Dependency exception text can contain protected response data.
        finally:
            self.client = None
            try:
                await self.account.close()
            except Exception:
                pass
            finally:
                # selected_payload has already made its passwordless copy on
                # confirmation. A closed onboarding object has no further use
                # for PETs, verification tokens or its transient account data.
                for attribute in (
                    "_password", "_recovery_pet", "_recovery_pet_at",
                    "_gsa_pet_at", "_account_info", "_username",
                ):
                    if hasattr(self.account, attribute):
                        setattr(self.account, attribute, None)
                if hasattr(self.account, "_login_state_data"):
                    self.account._login_state_data = {}
                provider = getattr(self.account, "_anisette", None)
                for attribute in ("_ani_data", "_ani", "_state_blob"):
                    if provider is not None and hasattr(provider, attribute):
                        setattr(provider, attribute, None)
