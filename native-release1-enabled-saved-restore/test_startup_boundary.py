"""Stdlib contracts for the startup fence; no native/provider imports or sockets."""

import ast
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).parent / "guest_helper/homecircle_safe_restore_qa/startup_boundary.py"
STATIC = "http://127.0.0.1:18123/homecircle_static/homecircle-card.js?v=0.1.0-beta.20&asset=0123456789ab"
PHOTO = "http://127.0.0.1:18123/api/image/serve/cccccccccccccccccccccccccccccccc/original"


def loaded_boundary():
    spec = importlib.util.spec_from_file_location("_qa_startup_boundary_contract", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixtures():
    """The only SDK/session classes used by these contracts are local stubs."""
    events = []

    class Session:
        async def _request(self, method, url, *args, **kwargs):
            events.append(("forwarded", method, url, args, kwargs))
            return "local_reply"

    class Http:
        async def request(self, method, url, **kwargs):
            raise AssertionError("unfenced_apple_legacy")

    class Bounded:
        async def request(self, method, url, **kwargs):
            raise AssertionError("unfenced_apple_bounded")

    class Report:
        async def post(self, url, **kwargs):
            raise AssertionError("unfenced_apple_report")

    class Attempt:
        async def before_dispatch(self):
            events.append(("original_reservation",))

    class Escrow:
        async def _command(self, command, *args, **kwargs):
            events.append(("escrow_preparation", command))
            return "prepared"

    async def new_session():
        events.append(("real_session_factory",))
        return Session()

    module_values = {
        "aiohttp": {"ClientSession": Session},
        "custom_components": {},
        "custom_components.homecircle": {},
        "custom_components.homecircle.life360_direct": {"new_session": new_session},
        "custom_components.homecircle._vendor_findmy.util.http": {"HttpSession": Http},
        "custom_components.homecircle._vendor_findmy.util.onboarding_http": {"BoundedHttpSession": Bounded},
        "custom_components.homecircle.findmy_report_service": {"_ReportTransport": Report},
        "custom_components.homecircle.findmy_recovery_guard": {"RecoveryAttempt": Attempt},
        "custom_components.homecircle._vendor_findmy.keychain.escrow": {"AsyncEscrowProxy": Escrow},
    }
    modules = {}
    for name, values in module_values.items():
        module = modules[name] = ModuleType(name)
        module.__dict__.update(values)
        module.__path__ = []
    modules["custom_components.homecircle"].life360_direct = modules["custom_components.homecircle.life360_direct"]
    hass = SimpleNamespace(config=SimpleNamespace(components=set()), data={},
                           config_entries=SimpleNamespace(async_entries=lambda domain: []),
                           http=SimpleNamespace(server_port=18123))
    return SimpleNamespace(events=events, Session=Session, Http=Http, Bounded=Bounded,
                           Report=Report, Attempt=Attempt, Escrow=Escrow,
                           life360=modules["custom_components.homecircle.life360_direct"],
                           modules=modules, hass=hass)


class Contracts(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.boundary, self.fixture = loaded_boundary(), fixtures()
        self.environment = patch.dict(self.boundary.os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def install(self):
        with patch.dict(sys.modules, self.fixture.modules), patch.object(self.boundary.sys, "platform", "linux"):
            return self.boundary.install(self.fixture.hass)

    async def denied(self, awaitable, expected="qa_synthetic_provider_transport_denied"):
        with self.assertRaises(self.boundary.StartupBoundaryRefused) as caught:
            await awaitable
        self.assertEqual(str(caught.exception), expected)

    def test_module_import_is_stdlib_only_and_install_has_no_await(self):
        tree = ast.parse(SOURCE.read_text())
        imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
        self.assertEqual({name.name for node in imports if isinstance(node, ast.Import)
                          for name in node.names}, {"os", "sys"})
        self.assertEqual({node.module for node in imports if isinstance(node, ast.ImportFrom)},
                         {"urllib.parse", "weakref"})
        install = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "install")
        # Nested async wrappers may await their real local/session operations;
        # synchronous installation itself must not yield to candidate setup.
        without_wrappers = ast.FunctionDef(name="install", args=install.args,
            body=[node for node in install.body if not isinstance(node, ast.AsyncFunctionDef)],
            decorator_list=[])
        self.assertFalse(any(isinstance(node, ast.Await) for node in ast.walk(without_wrappers)))

    def test_install_returns_fixed_scalar_snapshot(self):
        actual = self.install()
        self.assertEqual(set(actual), {"schema", "boundary_revision", *self.boundary.COUNTERS, *self.boundary.CHECKS})
        self.assertEqual(actual["schema"], 1)
        self.assertEqual(actual["boundary_revision"], 1)
        self.assertTrue(all(actual[name] is True for name in self.boundary.CHECKS))
        self.assertTrue(all(type(actual[name]) is int and actual[name] == 0 for name in self.boundary.COUNTERS))
        self.assertEqual(len(self.boundary._state["patches"]), 7)

    def test_mac_install_refuses_before_native_imports(self):
        with patch.object(self.boundary.sys, "platform", "darwin"):
            with self.assertRaises(self.boundary.StartupBoundaryRefused):
                self.boundary.install(self.fixture.hass)
        self.assertIsNone(self.boundary._state)

    def test_loaded_component_refuses(self):
        self.fixture.hass.config.components.add("homecircle")
        with self.assertRaises(self.boundary.StartupBoundaryRefused):
            self.install()
        self.assertIsNone(self.boundary._state)

    def test_existing_runtime_refuses(self):
        self.fixture.hass.config_entries.async_entries = lambda domain: [SimpleNamespace(runtime_data=object())]
        with self.assertRaises(self.boundary.StartupBoundaryRefused):
            self.install()
        self.assertIsNone(self.boundary._state)

    def test_imported_but_not_setup_component_is_allowed(self):
        self.fixture.hass.config_entries.async_entries = lambda domain: [SimpleNamespace()]
        self.assertTrue(self.install()["installed_before_runtime_setup"])

    def test_duplicate_install_refuses_without_replacing_hooks(self):
        self.install()
        original = tuple(self.boundary._state["patches"])
        with self.assertRaises(self.boundary.StartupBoundaryRefused):
            self.install()
        self.assertEqual(tuple(self.boundary._state["patches"]), original)
        self.assertTrue(self.boundary.snapshot()["patches_intact"])

    def test_proxy_environment_refuses_case_insensitively(self):
        for name in ("HTTP_PROXY", "https_proxy", "All_Proxy"):
            with self.subTest(name=name), patch.dict(self.boundary.os.environ, {name: "https://private.invalid/secret"}):
                with self.assertRaises(self.boundary.StartupBoundaryRefused) as caught:
                    self.install()
                self.assertNotIn("private", str(caught.exception))
                self.assertIsNone(self.boundary._state)

    async def test_actual_life360_factory_is_used_then_transport_is_denied(self):
        self.install()
        session = await self.fixture.life360.new_session()
        self.assertIsInstance(session, self.fixture.Session)
        await self.denied(session._request("GET", "https://api.life360.invalid/private"))
        actual = self.boundary.snapshot()
        self.assertEqual(actual["life360_sessions_created"], 1)
        self.assertEqual(actual["life360_requests_denied"], 1)
        self.assertEqual(actual["other_external_requests_denied"], 0)
        self.assertEqual(self.fixture.events, [("real_session_factory",)])

    async def test_life360_session_cannot_use_supervisor_allowance(self):
        self.install()
        session = await self.fixture.life360.new_session()
        await self.denied(session._request("GET", "http://supervisor/core/info"))
        self.assertEqual(self.boundary.snapshot()["life360_requests_denied"], 1)
        self.assertEqual(self.boundary.snapshot()["supervisor_requests_allowed"], 0)

    async def test_all_other_external_aiohttp_requests_are_denied(self):
        self.install()
        session = self.fixture.Session()
        for url in ("https://apple.invalid/private", "http://example.invalid/private", "http://192.168.5.59:8123/api"):
            await self.denied(session._request("POST", url, headers={"Authorization": "private"}))
        self.assertEqual(self.boundary.snapshot()["other_external_requests_denied"], 3)
        self.assertEqual(self.fixture.events, [])

    async def test_supervisor_calls_are_local_only_without_redirects(self):
        self.install()
        session = self.fixture.Session()
        for url in ("http://supervisor/core/info", "http://172.30.32.2:80/network/info"):
            self.assertEqual(await session._request("GET", url, allow_redirects=True), "local_reply")
        self.assertEqual(self.boundary.snapshot()["supervisor_requests_allowed"], 2)
        self.assertTrue(all(event[4]["allow_redirects"] is False for event in self.fixture.events))

    async def test_explicit_proxy_refuses_allowed_local_call(self):
        self.install()
        await self.denied(self.fixture.Session()._request("GET", "http://supervisor/core/info",
                                                        proxy="https://outside.invalid"))
        self.assertEqual(self.fixture.events, [])

    async def test_late_ambient_proxy_refuses_allowed_local_call(self):
        self.install()
        with patch.dict(self.boundary.os.environ, {"HTTP_PROXY": "https://outside.invalid"}):
            await self.denied(self.fixture.Session()._request("GET", "http://supervisor/core/info"))
        self.assertEqual(self.fixture.events, [])

    async def test_exact_static_asset_and_exact_original_photo_are_allowed(self):
        self.install()
        session = self.fixture.Session()
        for url in (STATIC, PHOTO):
            self.assertEqual(await session._request("GET", url), "local_reply")
        self.assertEqual(self.boundary.snapshot()["qa_static_requests_allowed"], 2)
        self.assertTrue(all(event[4]["allow_redirects"] is False for event in self.fixture.events))

    async def test_local_allowance_is_narrow_and_malformed_targets_are_fixed_failures(self):
        self.install()
        urls = (
            "http://supervisor.evil.invalid/core/info", "https://supervisor/core/info",
            "http://supervisor:81/core/info", "http://user:private@supervisor/core/info",
            "http://supervisor/core/info#secret", "http://[invalid",
            STATIC.replace(":18123", ":18124"), STATIC.replace("127.0.0.1", "localhost"),
            STATIC.replace("0123456789ab", "INVALIDVALUE"), STATIC + "&asset=0123456789ab",
            STATIC.replace("?v=", "?bad&v="), STATIC.replace("0.1.0-beta.20", "1.0.0"),
            PHOTO + "?secret=private", PHOTO.replace("/original", "/512x512"),
            PHOTO.replace("cccccccccccccccccccccccccccccccc", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"),
            "http://127.0.0.1:18123/api/auth", "https://" + "a" * 4097,
        )
        session = self.fixture.Session()
        for url in urls:
            await self.denied(session._request("GET", url))
        await self.denied(session._request("POST", STATIC))
        await self.denied(session._request("POST", PHOTO))
        self.assertEqual(self.fixture.events, [])
        self.assertEqual(self.boundary.snapshot()["other_external_requests_denied"], len(urls) + 2)

    async def test_all_three_apple_transports_are_denied_before_originals(self):
        self.install()
        await self.denied(self.fixture.Http().request("GET", "https://anisette.example.invalid"))
        await self.denied(self.fixture.Bounded().request("POST", "https://gsa.apple.com/private"))
        await self.denied(self.fixture.Report().post("https://gateway.icloud.com/findmyservice/v2/fetch"))
        actual = self.boundary.snapshot()
        self.assertEqual([actual[name] for name in ("apple_legacy_requests_denied", "apple_bounded_requests_denied", "apple_report_requests_denied")], [1, 1, 1])
        self.assertEqual(self.fixture.events, [])

    async def test_recovery_http_endpoint_attempt_is_counted_separately(self):
        self.install()
        url = "https://synthetic.apple.invalid/escrowproxy/api/recover"
        await self.denied(self.fixture.Http().request("POST", url))
        await self.denied(self.fixture.Bounded().request("POST", url + "/"))
        await self.denied(self.fixture.Session()._request("POST", url))
        self.assertEqual(self.boundary.snapshot()["recovery_transport_attempts_denied"], 3)
        self.assertEqual(self.boundary.snapshot()["recovery_before_dispatch_calls"], 0)

    async def test_recovery_reservation_is_counted_and_refused_before_mutation(self):
        self.install()
        await self.denied(self.fixture.Attempt().before_dispatch(), "qa_synthetic_recovery_reservation_denied")
        self.assertEqual(self.boundary.snapshot()["recovery_before_dispatch_calls"], 1)
        self.assertEqual(self.fixture.events, [])

    async def test_recovery_command_is_counted_and_refused_before_original(self):
        self.install()
        await self.denied(self.fixture.Escrow()._command("recover", label="private"), "qa_synthetic_recovery_command_denied")
        self.assertEqual(self.boundary.snapshot()["recovery_command_calls"], 1)
        self.assertEqual(self.fixture.events, [])

    async def test_nonproof_escrow_preparation_is_preserved(self):
        self.install()
        self.assertEqual(await self.fixture.Escrow()._command("get_records"), "prepared")
        self.assertEqual(self.fixture.events, [("escrow_preparation", "get_records")])
        self.assertEqual(self.boundary.snapshot()["recovery_command_calls"], 0)

    def test_hook_replacement_refuses_snapshot(self):
        self.install()
        for owner, name, wrapper in self.boundary._state["patches"]:
            with self.subTest(name=name):
                setattr(owner, name, object())
                with self.assertRaises(self.boundary.StartupBoundaryRefused):
                    self.boundary.snapshot()
                setattr(owner, name, wrapper)
        self.assertTrue(self.boundary.snapshot()["patches_intact"])

    def test_snapshot_is_a_defensive_scalar_copy(self):
        first = self.install()
        first["life360_requests_denied"] = 999
        first["patches_intact"] = False
        second = self.boundary.snapshot()
        self.assertEqual(second["life360_requests_denied"], 0)
        self.assertIs(second["patches_intact"], True)
        self.assertTrue(all(type(value) in (int, bool) for value in second.values()))

    async def test_counter_overflow_refuses_without_forwarding(self):
        self.install()
        self.boundary._state["counts"]["other_external_requests_denied"] = self.boundary.LIMIT
        with self.assertRaises(self.boundary.StartupBoundaryRefused) as caught:
            await self.fixture.Session()._request("GET", "https://outside.invalid")
        self.assertEqual(str(caught.exception), "qa_startup_boundary_refused")
        self.assertEqual(self.fixture.events, [])

    def test_snapshot_before_install_refuses(self):
        with self.assertRaises(self.boundary.StartupBoundaryRefused):
            self.boundary.snapshot()


if __name__ == "__main__":
    unittest.main()
