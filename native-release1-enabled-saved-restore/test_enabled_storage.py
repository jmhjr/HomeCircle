"""Stdlib-only enabled seed contracts; no SDK/native/HA import or HTTP.

Actual from_json method bodies come from SHA-bound candidate members. Their
constructors are observation stubs here; native managed startup must separately
prove construction, provider activation and denied request attempts on Linux.
"""
import ast
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import stat
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile

import storage_transfer as storage

HERE = Path(__file__).resolve().parent


def candidate_source(member):
    inventory = json.loads((HERE / 'payload/inventory.json').read_bytes())
    if 'files' in inventory:
        inventory = inventory['files']
    with zipfile.ZipFile(HERE / 'payload/homecircle.zip') as archive:
        raw = archive.read(member)
    expected = inventory.get(member)
    if type(expected) is not dict or expected != {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}:
        raise ValueError('candidate_source_binding_refused')
    return raw


def actual_function(member, name, *, owner=None, namespace=None):
    tree = ast.parse(candidate_source(member))
    parent = tree if owner is None else next(node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == owner)
    function = deepcopy(next(node for node in parent.body
        if isinstance(node, ast.FunctionDef) and node.name == name))
    function.decorator_list = []
    function.returns = None
    for argument in [*function.args.posonlyargs, *function.args.args, *function.args.kwonlyargs]:
        argument.annotation = None
    module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    result = {} if namespace is None else dict(namespace)
    exec(compile(module, 'actual_candidate_stdlib_body', 'exec'), result)
    return result[name]


def exact_identity():
    raw = candidate_source('findmy_identity.py')
    if hashlib.sha256(raw).hexdigest() != storage.SOURCE_FILES['findmy_identity.py']:
        raise ValueError('identity_source_binding_refused')
    tree = ast.parse(raw)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [item.name.split('.')[0] for item in node.names] if isinstance(node, ast.Import) else [node.module]
            if not set(names) <= {'copy', 'hashlib', 'hmac', 'secrets'}:
                raise ValueError('stdlib_identity_only')
    namespace = {}
    exec(compile(tree, 'actual_stdlib_identity', 'exec'), namespace)
    return types.SimpleNamespace(**namespace)


class EnabledStorageContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.identity = exact_identity()

    def setUp(self):
        self.record, self.selection, session, items, ledger = storage.new_synthetic(self.identity)
        passwordless = actual_function('findmy_vault.py', 'passwordless', namespace={'copy': __import__('copy')})
        self.payload = {'version': 2, 'session': passwordless(session), 'items': items, 'identity_state': ledger}
        self.registry = {'data': {'entities': storage.new_registry_rows(self.selection)}}

    def test_enabled_record_and_registry_refuse_old_disabled_markers(self):
        self.record['title'] = storage.ACCEPTED_TITLE
        stored = {'data': {'entries': [self.record]}}
        self.assertIs(storage.entry_from(stored), self.record)
        self.assertIsNone(self.record['disabled_by'])
        self.assertTrue(storage.consistency(self.record, self.selection, self.payload, self.identity, self.registry))
        disabled = deepcopy(self.record)
        disabled['disabled_by'] = 'user'
        with self.assertRaises(storage.Refused):
            storage.entry_from({'data': {'entries': [disabled]}})
        for marker in ('config_entry', 'user', 'integration'):
            wrong = deepcopy(self.registry)
            wrong['data']['entities'][0]['disabled_by'] = marker
            with self.assertRaises(storage.Refused):
                storage.registry_projection(self.selection, wrong)
        self.assertFalse(storage.public_result('seed')['entry_disabled'])
        self.assertFalse(storage.public_result('validate_restored')['managed_candidate_imported'])

    def test_exact_account_and_remote_anisette_parsers_consume_complete_synthetic_state(self):
        session = self.payload['session']
        self.assertEqual(session['type'], 'account')
        self.assertEqual(set(session['ids']), {'uid', 'devid'})
        self.assertTrue(all(type(value) is str and value for value in session['ids'].values()))
        self.assertIsNone(session['account']['password'])
        self.assertIsNone(session['account']['info'])
        self.assertTrue(session['account']['username'].endswith('@example.invalid'))
        self.assertEqual(session['login']['state'], 3)
        dsid = session['login']['data']['dsid']
        self.assertTrue(type(dsid) is str and dsid.isascii() and dsid.isdigit() and len(dsid) == 16)
        calls = []

        class Captured:
            def __init__(self, *args, **kwargs):
                calls.append((args, kwargs))

        read = types.SimpleNamespace(files=types.SimpleNamespace(read_data_json=lambda value: value),
            http=types.SimpleNamespace(DEFAULT_TIMEOUT=30))
        remote = actual_function('_vendor_findmy/reports/anisette.py', 'from_json',
            owner='RemoteAnisetteProvider', namespace={'util': read, 'CLIENT_SERIAL': 'TEST',
                'CLIENT_IDENTITY': object(), 'DeviceIdentity': types.SimpleNamespace(from_json=lambda _: self.fail('unexpected identity'))})
        remote(Captured, session['anisette'])
        self.assertEqual(calls[0][0], ('https://example.invalid',))
        self.assertIs(calls[0][1]['allow_unverified_https'], False)
        routing = actual_function('_vendor_findmy/reports/anisette.py', 'get_provider_from_mapping',
            namespace={'RemoteAnisetteProvider': types.SimpleNamespace(from_json=lambda value: remote(Captured, value))})
        parsed = actual_function('_vendor_findmy/reports/account.py', 'from_json', owner='AsyncAppleAccount',
            namespace={'util': read, 'get_provider_from_mapping': routing})
        parsed(Captured, session, anisette_libs_path=Path('/synthetic/never-opened'))
        self.assertEqual(calls[1][0], ('https://example.invalid',))
        self.assertIsInstance(calls[2][0][0], Captured)
        self.assertEqual(calls[2][1], {'state_info': session})
        missing_type = deepcopy(session)
        missing_type.pop('type')
        with self.assertRaises(KeyError):
            parsed(Captured, missing_type)
        missing_anisette = deepcopy(session)
        missing_anisette.pop('anisette')
        with self.assertRaises(ValueError):
            parsed(Captured, missing_anisette)

    def test_exact_accessory_parser_accepts_recent_pairing_and_actual_key_lengths(self):
        captures = []

        class Captured:
            def __init__(self, **values):
                captures.append(values)

        read = types.SimpleNamespace(files=types.SimpleNamespace(read_data_json=lambda value: value))
        parser = actual_function('_vendor_findmy/accessory.py', 'from_json', owner='FindMyAccessory',
            namespace={'util': read, 'datetime': datetime})
        for item in self.payload['items'].values():
            parser(Captured, item['accessory'])
        self.assertEqual(len(captures), 2)
        for value in captures:
            self.assertEqual(tuple(len(value[name]) for name in ('master_key', 'skn', 'sks')), (28, 32, 32))
            self.assertTrue(timedelta(hours=23) < datetime.now(timezone.utc) - value['paired_at'] < timedelta(days=2))
            self.assertIsNotNone(value['paired_at'].tzinfo)
            self.assertIsNone(value['alignment_date'])
            self.assertEqual(value['alignment_index'], 0)
        damaged = deepcopy(next(iter(self.payload['items'].values()))['accessory'])
        damaged.pop('paired_at')
        with self.assertRaises(ValueError):
            parser(Captured, damaged)

    def test_enabled_registry_schema_carries_all_official_storage_fragment_fields(self):
        expected = {'aliases', 'aliases_v2', 'area_id', 'categories', 'capabilities', 'config_entry_id',
            'config_subentry_id', 'created_at', 'device_class', 'device_id', 'disabled_by', 'entity_category',
            'entity_id', 'hidden_by', 'icon', 'id', 'has_entity_name', 'labels', 'modified_at', 'name',
            'object_id_base', 'options', 'original_device_class', 'original_icon', 'original_name', 'platform',
            'suggested_object_id', 'supported_features', 'translation_key', 'unique_id', 'previous_unique_id',
            'unit_of_measurement'}
        rows = self.registry['data']['entities']
        self.assertEqual(len(rows), 4)
        self.assertEqual(len({row['id'] for row in rows}), 4)
        for row, join in zip(rows, self.selection['joins'], strict=True):
            self.assertEqual(set(row), expected)
            self.assertEqual({key: row[key] for key in ('entity_id', 'unique_id', 'config_entry_id')},
                {key: join[key] for key in ('entity_id', 'unique_id', 'config_entry_id')})
            self.assertIsNone(row['disabled_by'])
            self.assertIsNone(row['device_id'])
            self.assertEqual(row['platform'], 'homecircle')
            self.assertIsNotNone(datetime.fromisoformat(row['created_at']).tzinfo)

    def test_registry_seed_precedes_startup_and_preserves_unrelated_managed_rows(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            (root / '.storage').mkdir(mode=0o700)
            with patch.object(storage, 'CONFIG', root):
                storage.seed_registry(self.selection)
                path = root / '.storage/core.entity_registry'
                value = storage.read_managed_json(path)
                self.assertEqual((value['version'], value['minor_version'], value['key']), (1, 23, 'core.entity_registry'))
                self.assertEqual(len(storage.registry_projection(self.selection, value)), 4)
                with self.assertRaises(storage.Refused):
                    storage.seed_registry(self.selection)
                path.unlink()
                unrelated = {'entity_id': 'sensor.synthetic_unrelated', 'unique_id': 'unrelated', 'config_entry_id': 'other'}
                value['data']['entities'] = [unrelated]
                path.write_bytes(storage.canonical(value))
                path.chmod(0o644)
                storage.seed_registry(self.selection)
                saved = storage.read_managed_json(path)
                self.assertEqual(saved['data']['entities'][0], unrelated)
                self.assertEqual(len(saved['data']['entities']), 5)
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
                path.unlink()
                path.symlink_to(root / 'missing')
                with self.assertRaises((storage.Refused, OSError)):
                    storage.seed_registry(self.selection)

    def test_picture_seed_is_real_image_store_and_attaches_only_explicit_life360_member(self):
        pictured = [(entity, member) for entity, member in self.record['options']['members'].items() if member.get('picture_id')]
        self.assertEqual(len(pictured), 1)
        self.assertEqual(pictured[0][1]['picture_id'], storage.PICTURE_ID)
        self.assertIn(pictured[0][0], self.record['options']['people_trackers'])
        self.assertEqual(self.record['data'], self.record['options'])
        self.assertTrue(all('picture_id' not in item['display_preferences']
            for item in next(iter(self.record['options']['findmy_accounts'].values()))['items'].values()))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            (root / '.storage').mkdir(mode=0o700)
            with patch.object(storage, 'CONFIG', root):
                storage.seed_picture()
                saved = storage.read_json(root / '.storage/image')
                self.assertEqual((saved['version'], saved['minor_version'], saved['key']), (1, 1, 'image'))
                item = saved['data']['items'][0]
                self.assertEqual(set(item), {'id', 'filesize', 'content_type', 'name', 'uploaded_at'})
                self.assertEqual((item['id'], item['filesize'], item['content_type']),
                    (storage.PICTURE_ID, len(storage.PICTURE), 'image/png'))
                original = root / 'image' / storage.PICTURE_ID / 'original'
                self.assertEqual(storage.sha(storage.regular(original)), storage.PICTURE_SHA256)
                with self.assertRaises(storage.Refused):
                    storage.seed_picture()

    def test_postbackup_registry_mutation_precedes_startup_and_preserves_row_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            (root / '.storage').mkdir(mode=0o700)
            with patch.object(storage, 'CONFIG', root):
                storage.seed_registry(self.selection)
                path = root / '.storage/core.entity_registry'
                before = storage.read_managed_json(path)
                old_selection = deepcopy(self.selection)
                storage.mutate_semantics(self.record, self.selection, self.payload, self.identity)
                storage.mutate_registry(old_selection, self.selection)
                after = storage.read_managed_json(path)
                storage.registry_projection(self.selection, after)
                self.assertEqual([row['id'] for row in before['data']['entities']],
                    [row['id'] for row in after['data']['entities']])
                self.assertNotEqual(before['data']['entities'][0]['entity_id'], after['data']['entities'][0]['entity_id'])
                self.assertNotEqual(before['data']['entities'][0]['unique_id'], after['data']['entities'][0]['unique_id'])
                self.assertEqual(before['data']['entities'][1:], after['data']['entities'][1:])
                unchanged = path.read_bytes()
                with self.assertRaises(storage.Refused):
                    storage.mutate_registry(old_selection, self.selection)
                self.assertEqual(path.read_bytes(), unchanged)

    def test_all_18_clone_negatives_and_ledger_commitments_remain_unchanged(self):
        self.assertEqual(len(storage.NEGATIVES), 18)
        self.assertEqual(storage.NEGATIVES[-4:], ('metadata_selection', 'data_options_divergence', 'registry_identity', 'duplicate_join'))
        ledger = self.identity.validate_state(self.payload['identity_state'], self.payload['session'])
        selected = {self.identity.commitment_for(ledger, item['accessory']) for item in self.payload['items'].values()}
        self.assertEqual((len(selected), len(set(ledger['records']) - selected)), (2, 1))
        before = deepcopy(self.payload['identity_state'])
        storage.mutate_semantics(self.record, self.selection, self.payload, self.identity)
        registry = {'data': {'entities': storage.new_registry_rows(self.selection)}}
        self.assertTrue(storage.consistency(self.record, self.selection, self.payload, self.identity, registry))
        self.assertEqual(self.payload['identity_state']['secret'], before['secret'])
        self.assertEqual(set(self.payload['identity_state']['records']), set(before['records']))
        self.assertTrue(self.payload['session']['login']['data']['dsid'].isdigit())
        for action in ('validate_restored', 'validate_restart'):
            self.assertEqual(storage.checks(action)['negative_cases'], 18)


if __name__ == '__main__':
    unittest.main()
