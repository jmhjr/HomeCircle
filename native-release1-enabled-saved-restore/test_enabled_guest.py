"""Source-bound helper contracts with stdlib stubs; never import HA or providers."""
import ast
import asyncio
import base64
import hashlib
import json
from pathlib import Path
import stat
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
HELPER = HERE / 'guest_helper/homecircle_safe_restore_qa/__init__.py'
SOURCE = HELPER.read_text()
TREE = ast.parse(SOURCE)


def load_helpers():
    names = {'Refused', 'check', 'digest', 'package_at', 'assert_enabled', 'current_entry',
             'startup_receipt', 'runtime_details', 'dependency_fixture_at'}
    constants = {'DOMAIN', 'CANDIDATE', 'ORIGINAL_MANIFEST', 'PHOTO_ID', 'PHOTO_PNG',
                 'PHOTO_SHA256', 'IMAGE_API_SHA256', 'PHASES', 'DEPS_SITE'}
    nodes = [node for node in TREE.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
             and node.name in names or isinstance(node, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id in constants for t in node.targets)]
    env = {'Path': Path, 'json': json, 'hashlib': hashlib, 'sys': sys, 'stat': stat,
           'asyncio': asyncio, 'base64': base64,
           'ConfigEntryState': types.SimpleNamespace(LOADED=object(), NOT_LOADED=object())}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(HELPER), 'exec'), env)
    return env


def boundary_value():
    return dict(schema=1, boundary_revision=1, installed_before_runtime_setup=True, patches_intact=True,
        deny_all_external_aiohttp=True, deny_all_apple_transports=True,
        provider_transport_attempts_measured=True, recovery_attempt_seams_measured=True,
        life360_sessions_created=1, life360_requests_denied=1, apple_legacy_requests_denied=1,
        apple_bounded_requests_denied=0, apple_report_requests_denied=0,
        other_external_requests_denied=0, recovery_before_dispatch_calls=0,
        recovery_command_calls=0, recovery_transport_attempts_denied=0,
        supervisor_requests_allowed=0, qa_static_requests_allowed=2)


class EnabledGuestContracts(unittest.TestCase):
    def setUp(self):
        self.g = load_helpers()

    def refused(self, function, *args):
        with self.assertRaises(self.g['Refused']):
            function(*args)

    def runtime_fixture(self, root):
        product = root / 'custom_components/homecircle'
        product.mkdir(parents=True)
        product_source = product / '__init__.py'
        product_source.write_bytes(b'exact source91 fixture')
        (product / 'frontend').mkdir()
        bundle = b'synthetic exact card bytes'
        (product / 'frontend/homecircle-card.js').write_bytes(bundle)
        image_source = root / 'image_api.py'
        image_source.write_bytes(b'official image API source')
        self.g['IMAGE_API_SHA256'] = self.g['digest'](image_source.read_bytes())
        image_dir = root / 'image'
        photo = image_dir / self.g['PHOTO_ID'] / 'original'
        photo.parent.mkdir(parents=True)
        photo.write_bytes(self.g['PHOTO_PNG'])
        class Runtime:
            pass
        class FindMy:
            pass
        class Life360:
            pass
        runtime = Runtime()
        joins = [{'entity_id': 'device_tracker.item_' + str(i), 'kind': 'item', 'unique_id': 'homecircle_findmy_' + str(i)} for i in range(2)]
        joins += [{'entity_id': 'device_tracker.person_' + str(i), 'kind': 'person', 'unique_id': 'homecircle_life360_' + str(i)} for i in range(2)]
        options = {'members': {row['entity_id']: dict(kind=row['kind'], display_name='Synthetic ' + str(i), show_on_map=True)
                               for i, row in enumerate(joins)}}
        options['members'][joins[2]['entity_id']]['picture_id'] = self.g['PHOTO_ID']
        runtime.config = options
        runtime.household = object()
        findmy = FindMy()
        findmy.clients = {'account': object()}
        findmy.vaults = {'account': object()}
        findmy.trackers = {'account': {'one': types.SimpleNamespace(report={'latitude': 0}),
                                     'two': types.SimpleNamespace(report={'latitude': 1})}}
        life360 = Life360()
        life360.trackers = {str(i): types.SimpleNamespace(unique_id='homecircle_life360_' + str(i)) for i in range(2)}
        runtime.managed_trackers = {'findmy': findmy, 'life360': life360}
        projected = [dict(id=row['entity_id'], kind=row['kind'], name=options['members'][row['entity_id']]['display_name'],
                          map_visible=True, picture='/api/image/serve/' + self.g['PHOTO_ID'] + '/512x512'
                          if row['kind'] == 'person' else None) for row in joins]
        product_module = types.ModuleType('custom_components.homecircle')
        product_module.__file__ = str(product_source)
        product_module.__path__ = []
        product_module.HomeCircleRuntime = Runtime
        product_module.api = types.SimpleNamespace(snapshot=lambda rt: {'members': projected})
        product_module.frontend = types.SimpleNamespace(resource_url=lambda: '/homecircle_static/homecircle-card.js?v=fixture')
        findmy_module = types.ModuleType('custom_components.homecircle.findmy_provider')
        findmy_module.DirectFindMy = FindMy
        life_module = types.ModuleType('custom_components.homecircle.life360_direct')
        life_module.DirectLife360 = Life360
        image_module = types.ModuleType('homeassistant.components.image_upload')
        image_module.__file__ = str(image_source)
        components = types.ModuleType('homeassistant.components')
        components.__path__ = []
        components.image_upload = image_module
        parent = types.ModuleType('homeassistant')
        parent.__path__ = []
        custom = types.ModuleType('custom_components')
        custom.__path__ = []
        modules = {'custom_components': custom, 'custom_components.homecircle': product_module,
                   findmy_module.__name__: findmy_module, life_module.__name__: life_module,
                   'homeassistant': parent, 'homeassistant.components': components,
                   image_module.__name__: image_module}
        entry = types.SimpleNamespace(disabled_by=None, state=self.g['ConfigEntryState'].LOADED,
                                      runtime_data=runtime, options=options)
        record = dict(id=self.g['PHOTO_ID'], filesize=len(self.g['PHOTO_PNG']), content_type='image/png',
                      name='synthetic.png', uploaded_at='2026-01-01T00:00:00+00:00')
        collection = types.SimpleNamespace(image_dir=image_dir, async_items=lambda: [record])
        class Hass:
            config = types.SimpleNamespace(components={'homecircle'}, path=lambda p: str(root / p))
            http = types.SimpleNamespace(server_port=8123, context=None)
            data = {'image_upload': collection}
            states = types.SimpleNamespace(get=lambda key: object())
            async def async_add_executor_job(self, function, *args):
                return function(*args)
        class Content:
            def __init__(self, body): self.body = body
            async def iter_chunked(self, size): yield self.body
        class Response:
            status = 200
            def __init__(self, body): self.content = Content(body)
            async def __aenter__(self): return self
            async def __aexit__(self, *args): return False
        class Session:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): return False
            def get(self, url, **kwargs):
                return Response(self.photo_body if url.endswith('/original') else bundle)
            photo_body = self.g['PHOTO_PNG']
        self.g['aiohttp'] = types.SimpleNamespace(ClientTimeout=lambda **kw: None,
                                                 ClientSession=lambda **kw: Session())
        self.g['startup_boundary'] = types.SimpleNamespace(snapshot=boundary_value)
        inputs = {'candidate_inventory': {'__init__.py': {'sha256': self.g['digest'](product_source.read_bytes())}}}
        return dict(hass=Hass(), entry=entry, selection={'joins': joins}, inputs=inputs,
                    modules=modules, projected=projected, photo=photo, record=record, Session=Session)

    def run_runtime(self, fixture):
        with patch.dict(sys.modules, fixture['modules']):
            return asyncio.run(self.g['runtime_details'](*(fixture[key] for key in ('hass', 'entry', 'selection', 'inputs'))))

    def test_five_enabled_names(self):
        self.assertEqual(self.g['PHASES'], ('baseline_enabled', 'mutated_enabled', 'automatic_restored_enabled',
                                          'repaired_storage_enabled', 'restart_enabled'))

    def test_install_precedes_valid_setup_scheduling_and_return(self):
        setup = next(n for n in TREE.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'async_setup')
        self.assertIsInstance(setup.body[0], ast.If)
        self.assertIsInstance(setup.body[1], ast.Try)
        self.assertEqual(ast.unparse(setup.body[1].body[0]), 'startup_boundary.install(hass)')
        self.assertFalse(any(isinstance(n, ast.Await) for n in ast.walk(setup)))
        self.assertEqual(setup.body[-1].value.value, True)
        self.assertNotIn('async_set_disabled_by', SOURCE)

    def test_install_failure_writes_only_fixed_metadata_and_refuses_setup(self):
        setup = next(n for n in TREE.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'async_setup')
        class BoundaryFailure(OSError): pass
        def install(hass): raise BoundaryFailure('PRIVATE_IMPORT_CANARY')
        observed = []
        env = dict(DOMAIN='homecircle_safe_restore_qa', CONTROL='qa-control', Path=Path,
                   startup_boundary=types.SimpleNamespace(install=install, StartupBoundaryRefused=BoundaryFailure),
                   write_json=lambda path,value: observed.append((path,value)),
                   process=lambda: {'pid':1,'start_ticks':2})
        exec(compile(ast.Module(body=[setup],type_ignores=[]),str(HELPER),'exec'),env)
        hass=types.SimpleNamespace(config=types.SimpleNamespace(config_dir='/owned'))
        self.assertIs(asyncio.run(env['async_setup'](hass,{'homecircle_safe_restore_qa':{'disposable':True}})),False)
        self.assertEqual(observed,[(Path('/owned/qa-control/startup-install-failure.json'),
            dict(schema=1,outcome='failed',stage='startup_boundary_install',failure_type='StartupBoundaryRefused',failure_code='qa_startup_boundary_install_failed',
                 process={'pid':1,'start_ticks':2}))])
        self.assertNotIn('CANARY',repr(observed))

    def test_automatic_private_details_follow_consumed_grant(self):
        poll = next(n for n in ast.walk(TREE) if isinstance(n, ast.AsyncFunctionDef) and n.name == 'poll')
        source = ast.unparse(poll)
        self.assertLess(source.index('consume_closed_boot_grant'), source.index('runtime_details('))
        self.assertLess(source.index('consume_closed_boot_grant'), source.index('guard_files,'))
        self.assertIn('prepared_dependencies', source)

    def test_disclosed_manifest_is_only_product_delta(self):
        with tempfile.TemporaryDirectory() as t, ZipFile(HERE / 'payload/homecircle.zip') as archive:
            root = Path(t)
            product = root / 'custom_components/homecircle'
            archive.extractall(product)
            inventory = {name: {'bytes': len(archive.read(name)), 'sha256': self.g['digest'](archive.read(name))}
                         for name in archive.namelist()}
            original = self.g['ORIGINAL_MANIFEST']
            manifest = {**original, 'dependencies': [*original['dependencies'], self.g['DOMAIN']]}
            (product / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
            result = self.g['package_at'](root, {'candidate_inventory': inventory})
            self.assertTrue(result['qa_manifest_only_difference'])
            self.assertEqual(result['package_payload_sha256'], self.g['digest'](inventory))
            for mutation in ('source', 'manifest', 'extra'):
                if mutation == 'source':
                    p = product / '__init__.py'; before = p.read_bytes(); p.write_bytes(before + b'\n')
                elif mutation == 'manifest':
                    p = product / 'manifest.json'; before = p.read_bytes(); p.write_bytes(before.replace(b'beta.20', b'beta.21'))
                else:
                    p = product / 'foreign.py'; before = None; p.write_bytes(b'foreign')
                self.refused(self.g['package_at'], root, {'candidate_inventory': inventory})
                p.unlink() if before is None else p.write_bytes(before)

    def test_enabled_runtime_source_selection_photo_and_http(self):
        with tempfile.TemporaryDirectory() as t:
            value = self.run_runtime(self.runtime_fixture(Path(t)))
        self.assertTrue(value['actual_findmy_session_restored'])
        self.assertTrue(value['synthetic_photo_preserved'])
        self.assertTrue(value['runtime_selection_checked'])
        self.assertTrue(value['static_served_bundle_matches'])

    def test_disabled_entry_refuses(self):
        with tempfile.TemporaryDirectory() as t:
            f = self.runtime_fixture(Path(t)); f['entry'].disabled_by = 'user'
            with self.assertRaises(self.g['Refused']): self.run_runtime(f)

    def test_unloaded_entry_refuses(self):
        with tempfile.TemporaryDirectory() as t:
            f = self.runtime_fixture(Path(t)); f['entry'].state = self.g['ConfigEntryState'].NOT_LOADED
            with self.assertRaises(self.g['Refused']): self.run_runtime(f)

    def test_missing_provider_lifecycle_refuses(self):
        with tempfile.TemporaryDirectory() as t:
            f = self.runtime_fixture(Path(t)); del f['entry'].runtime_data.managed_trackers['life360']
            with self.assertRaises(self.g['Refused']): self.run_runtime(f)

    def test_nonrestored_apple_client_refuses(self):
        with tempfile.TemporaryDirectory() as t:
            f = self.runtime_fixture(Path(t)); f['entry'].runtime_data.managed_trackers['findmy'].clients.clear()
            with self.assertRaises(self.g['Refused']): self.run_runtime(f)

    def test_missing_saved_report_refuses(self):
        with tempfile.TemporaryDirectory() as t:
            f = self.runtime_fixture(Path(t)); f['entry'].runtime_data.managed_trackers['findmy'].trackers['account']['one'].report = {}
            with self.assertRaises(self.g['Refused']): self.run_runtime(f)

    def test_changed_runtime_settings_refuse(self):
        with tempfile.TemporaryDirectory() as t:
            f = self.runtime_fixture(Path(t)); f['entry'].runtime_data.config = {'members': {}}
            with self.assertRaises(self.g['Refused']): self.run_runtime(f)

    def test_changed_loaded_source_refuses(self):
        with tempfile.TemporaryDirectory() as t:
            f = self.runtime_fixture(Path(t)); f['inputs']['candidate_inventory']['__init__.py']['sha256'] = '0' * 64
            with self.assertRaises(self.g['Refused']): self.run_runtime(f)

    def test_changed_projected_selection_refuses(self):
        with tempfile.TemporaryDirectory() as t:
            f = self.runtime_fixture(Path(t)); f['projected'].pop()
            with self.assertRaises(self.g['Refused']): self.run_runtime(f)

    def test_changed_photo_setting_refuses(self):
        with tempfile.TemporaryDirectory() as t:
            f = self.runtime_fixture(Path(t)); f['entry'].options['members']['device_tracker.person_0']['picture_id'] = 'd' * 32
            with self.assertRaises(self.g['Refused']): self.run_runtime(f)

    def test_changed_photo_metadata_refuses(self):
        with tempfile.TemporaryDirectory() as t:
            f = self.runtime_fixture(Path(t)); f['record']['filesize'] += 1
            with self.assertRaises(self.g['Refused']): self.run_runtime(f)

    def test_changed_photo_bytes_refuse(self):
        with tempfile.TemporaryDirectory() as t:
            f = self.runtime_fixture(Path(t)); f['photo'].write_bytes(b'foreign')
            with self.assertRaises(self.g['Refused']): self.run_runtime(f)

    def test_wrong_served_image_bytes_refuse(self):
        with tempfile.TemporaryDirectory() as t:
            f = self.runtime_fixture(Path(t)); f['Session'].photo_body = b'foreign'
            with self.assertRaises(self.g['Refused']): self.run_runtime(f)

    def test_nonvacuous_boundary_accepts(self):
        self.g['startup_boundary'] = types.SimpleNamespace(snapshot=boundary_value)
        self.assertEqual(self.g['startup_receipt'](), boundary_value())

    def test_zero_apple_attempts_refuse(self):
        value = boundary_value(); value['apple_legacy_requests_denied'] = 0
        self.g['startup_boundary'] = types.SimpleNamespace(snapshot=lambda: value)
        self.refused(self.g['startup_receipt'])

    def test_zero_life360_attempts_refuse(self):
        value = boundary_value(); value['life360_requests_denied'] = 0
        self.g['startup_boundary'] = types.SimpleNamespace(snapshot=lambda: value)
        self.refused(self.g['startup_receipt'])

    def test_recovery_dispatch_refuses(self):
        value = boundary_value(); value['recovery_before_dispatch_calls'] = 1
        self.g['startup_boundary'] = types.SimpleNamespace(snapshot=lambda: value)
        self.refused(self.g['startup_receipt'])

    def test_recovery_command_refuses(self):
        value = boundary_value(); value['recovery_command_calls'] = 1
        self.g['startup_boundary'] = types.SimpleNamespace(snapshot=lambda: value)
        self.refused(self.g['startup_receipt'])

    def test_replaced_boundary_refuses(self):
        value = boundary_value(); value['patches_intact'] = False
        self.g['startup_boundary'] = types.SimpleNamespace(snapshot=lambda: value)
        self.refused(self.g['startup_receipt'])

    def test_unbounded_counter_refuses(self):
        value = boundary_value(); value['life360_requests_denied'] = 1000001
        self.g['startup_boundary'] = types.SimpleNamespace(snapshot=lambda: value)
        self.refused(self.g['startup_receipt'])

    def test_foreign_boundary_field_refuses(self):
        value = boundary_value(); value['private_credential'] = 'CANARY'
        self.g['startup_boundary'] = types.SimpleNamespace(snapshot=lambda: value)
        self.refused(self.g['startup_receipt'])

    def test_all_24_dependency_metadata_origins_are_checked(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); deps = root / 'deps'; deps.mkdir(); (deps / 'marker').write_bytes(b'fixture')
            inventory = {'marker': {'bytes': 7, 'sha256': self.g['digest'](b'fixture')}}
            fixture = dict(inventory_sha256=self.g['digest'](inventory), inventory_files=1, inventory_bytes=7,
                           closure={str(i): '1' for i in range(24)})
            site = deps / 'lib/python3.14/site-packages'; site.mkdir(parents=True)
            self.g['DEPS_SITE'] = site.resolve()
            self.g['dependency_packages'] = lambda: {'direct': dict(available=True, satisfies_requirement=True,
                                                                  origin_config_deps=True, metadata_error=False)}
            observed = []
            def distribution(name):
                observed.append(name)
                return types.SimpleNamespace(version='1', locate_file=lambda unused: site)
            self.g['metadata'] = types.SimpleNamespace(distribution=distribution)
            with patch.object(sys, 'path', [str(site.resolve()), '/ordinary/site-packages']):
                value = self.g['dependency_fixture_at'](root, dict(dependency_fixture=fixture, dependency_inventory=inventory))
            self.assertTrue(value['origins_config_deps'])
            self.assertEqual(len(observed), 24)
            fixture['closure'].pop('0')
            with patch.object(sys, 'path', [str(site.resolve()), '/ordinary/site-packages']):
                self.refused(self.g['dependency_fixture_at'], root, dict(dependency_fixture=fixture, dependency_inventory=inventory))


if __name__ == '__main__':
    unittest.main()
