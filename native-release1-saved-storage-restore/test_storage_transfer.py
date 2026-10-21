"""Stdlib-only contracts. No local Vault/Fernet/HA/provider imports.

On the preparation Mac the exact stdlib identity source is selected explicitly
with HOMECIRCLE_STORAGE_IDENTITY_SOURCE and checked against its canonical Git
blob. On native CI the qualified candidate ZIP supplies that same pinned member.
Actual encryption/load/save/refusal is the separate Linux context witness.
"""
import ast
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile

import storage_transfer as storage

HERE = Path(__file__).resolve().parent

def exact_identity():
    chosen = os.environ.get('HOMECIRCLE_STORAGE_IDENTITY_SOURCE')
    if chosen is not None:
        path = Path(chosen)
        raw = path.read_bytes()
        root = HERE.parents[2]
        expected = subprocess.run(['git', '-C', str(root), 'cat-file', 'blob',
            '3da605c71330a7651d63040981ce90466d53768c:custom_components/homecircle/findmy_identity.py'],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=20).stdout
        if raw != expected or path.is_symlink():
            raise ValueError('exact_identity_git_binding_refused')
    else:
        with zipfile.ZipFile(HERE / 'payload/homecircle.zip') as archive:
            raw = archive.read('findmy_identity.py')
    if hashlib.sha256(raw).hexdigest() != storage.SOURCE_FILES['findmy_identity.py']:
        raise ValueError('exact_identity_source_refused')
    tree = ast.parse(raw)
    allowed = {'copy', 'hashlib', 'hmac', 'secrets'}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [item.name.split('.')[0] for item in node.names] if isinstance(node, ast.Import) else [node.module]
            if not set(names).issubset(allowed):
                raise ValueError('stdlib_identity_only')
    result = types.ModuleType('exact_stdlib_identity_contract')
    exec(compile(tree, 'exact_stdlib_identity_contract', 'exec'), result.__dict__)
    return result

def exact_selection_functions():
    chosen = os.environ.get('HOMECIRCLE_STORAGE_IDENTITY_SOURCE')
    if chosen is not None:
        raw = Path(chosen).with_name('selection.py').read_bytes()
        expected = subprocess.run(['git', '-C', str(HERE.parents[2]), 'cat-file', 'blob',
            '3da605c71330a7651d63040981ce90466d53768c:custom_components/homecircle/selection.py'],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=20).stdout
        if raw != expected:
            raise ValueError('exact_selection_git_binding_refused')
    else:
        with zipfile.ZipFile(HERE / 'payload/homecircle.zip') as archive:
            raw = archive.read('selection.py')
    if hashlib.sha256(raw).hexdigest() != 'bf87b91f662459ef539894bd908c28ea189ad91a29c49755169f4c0dff7b3562':
        raise ValueError('exact_selection_source_refused')
    functions = [node for node in ast.parse(raw).body if isinstance(node, ast.FunctionDef)
                 and node.name in {'selected_entities', 'household_errors', 'member_errors'}]
    for node in functions:
        node.decorator_list = []
        node.returns = None
        for argument in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]:
            argument.annotation = None
    module = ast.Module(body=functions, type_ignores=[])
    namespace = {'CONF_MEMBERS': 'members', 'CONF_ITEMS': 'items', 'CONF_PEOPLE': 'people',
        'CONF_TRACKER_PEOPLE': 'people_trackers', 'CONF_PETS': 'pets', 'CONF_PLACES': 'places',
        'CONF_PRIMARY_HOME': 'primary_home', 'CONF_RESIDENCES': 'additional_residences',
        'CONF_TRACKERS': 'trackers', 'CONF_DISPLAY_NAME': 'display_name', 'CONF_SHOW_ON_MAP': 'show_on_map',
        'CONF_AUTO_REQUEST_LOCATION': 'auto_request_location', 'entities_in_person': lambda *_: []}
    exec(compile(module, 'exact_selection_stdlib_AST_contract', 'exec'), namespace)
    return namespace

class StorageTransferContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.identity = exact_identity()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.root.chmod(0o700)
        self.record, self.selection, session, items, ledger = storage.new_synthetic(self.identity)
        # The product passwordless projection is exercised natively. This plain
        # fixture contains its explicit expected shape without importing Vault.
        session['account']['password'] = None
        session['account']['info'] = None
        data = session['login']['data']
        session['login']['data'] = {'dsid': data['dsid'],
            'mobileme_data': {'tokens': {'searchPartyToken': data['mobileme_data']['tokens']['searchPartyToken']}}}
        self.payload = {'version': 2, 'session': session, 'items': items, 'identity_state': ledger}
        self.registry = {'data': {'entities': [{**{key: join[key] for key in ('entity_id', 'unique_id', 'config_entry_id')},
            'platform': 'homecircle', 'disabled_by': 'config_entry'} for join in self.selection['joins']]}}

    def write(self, path, value):
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_bytes(value if type(value) is bytes else storage.canonical(value))
        path.chmod(0o600)

    def fingerprints(self):
        return {key: hashlib.sha256(key.encode()).hexdigest() for key in storage.FINGERPRINTS}

    def test_protocol_case_catalog_is_exact_and_nonduplicated(self):
        protocol = json.loads((HERE / 'storage_protocol.json').read_bytes())
        expected = ('missing_key', 'wrong_valid_key', 'invalid_base64_key', 'short_decoded_key',
            'tampered_cipher', 'truncated_cipher', 'key_permissions', 'vault_permissions',
            'key_symlink', 'vault_symlink', 'key_directory', 'vault_directory', 'foreign_ledger',
            'metadata_identity', 'metadata_selection', 'data_options_divergence', 'registry_identity', 'duplicate_join')
        self.assertEqual(storage.NEGATIVES, expected)
        self.assertEqual(len(set(storage.NEGATIVES)), 18)
        self.assertEqual(list(storage.NEGATIVES), protocol['negative_case_ids'])
        self.assertEqual(set(protocol['fingerprint_fields']), storage.FINGERPRINTS)
        self.assertEqual(set(protocol['check_keys']), storage.CHECKS)
        self.assertEqual(tuple(protocol['actions']), storage.ACTIONS)
        self.assertEqual(protocol['source_commit'], storage.SOURCE_COMMIT)
        for action in storage.ACTIONS:
            expected = {name: True for name in protocol['common_true_checks']}
            expected.update(protocol['action_checks'][action])
            self.assertEqual(storage.checks(action), expected)
            self.assertEqual(storage.public_result(action)['private_proof_written'], protocol['private_proof_written_by_action'][action])

    def test_actual_stdlib_identity_binds_two_selected_and_one_deselected_commitment(self):
        self.assertTrue(storage.consistency(self.record, self.selection, self.payload, self.identity, self.registry))
        ledger = self.payload['identity_state']
        selected = {self.identity.commitment_for(ledger, item['accessory']) for item in self.payload['items'].values()}
        self.assertEqual((len(selected), len(set(ledger['records']) - selected)), (2, 1))
        self.assertNotIn(next(record['identifier'] for key, record in ledger['records'].items() if key not in selected), self.payload['items'])

    def test_deselected_raw_tracking_material_is_absent_from_saved_items_and_ledger(self):
        captured = []
        original = storage.accessory
        def capture():
            value = original()
            captured.append(value)
            return value
        with patch.object(storage, 'accessory', side_effect=capture):
            _, _, _, items, ledger = storage.new_synthetic(self.identity)
        encoded = storage.canonical({'items': items, 'identity_state': ledger})
        self.assertEqual(len(captured), 3)
        self.assertTrue(all(value.encode() not in encoded for value in captured[2].values()), 'deselected raw keys must not be stored')
        self.assertTrue(all(value.encode() in encoded for value in captured[0].values()), 'selected raw keys belong only to selected item')

    def test_actual_product_selection_functions_accept_the_saved_config_shape(self):
        namespace = exact_selection_functions()
        settings = self.record['options']
        known = {join['entity_id'] for join in self.selection['joins']} | {'zone.home', 'zone.example_saved_storage'}
        namespace['selectable'] = lambda _hass, entity, domain: entity in known and entity.startswith(domain + '.')
        hass = types.SimpleNamespace(states=types.SimpleNamespace(get=lambda _: None))
        self.assertEqual(namespace['selected_entities'](settings), known)
        self.assertEqual(namespace['household_errors'](hass, settings), {})
        for entity, member in settings['members'].items():
            self.assertEqual(namespace['member_errors'](hass, member, settings['primary_home'], entity), {})
        self.assertEqual(self.record['unique_id'], 'homecircle')
        self.assertFalse(self.record['pref_disable_polling'])

    def test_mutation_keeps_real_ledger_bindings_and_updates_every_explicit_member_reference(self):
        before_record, before_selection, before_payload = deepcopy(self.record), deepcopy(self.selection), deepcopy(self.payload)
        storage.mutate_semantics(self.record, self.selection, self.payload, self.identity)
        registry = {'data': {'entities': [{**{key: join[key] for key in ('entity_id', 'unique_id', 'config_entry_id')},
            'platform': 'homecircle', 'disabled_by': 'config_entry'} for join in self.selection['joins']]}}
        self.assertTrue(storage.consistency(self.record, self.selection, self.payload, self.identity, registry))
        self.assertEqual(set(self.payload['identity_state']['records']), set(before_payload['identity_state']['records']))
        self.assertEqual(self.payload['identity_state']['secret'], before_payload['identity_state']['secret'])
        for old, new in ((before_record, self.record), (before_selection, self.selection),
                         (before_payload, self.payload), (before_payload['identity_state'], self.payload['identity_state']),
                         (before_record['options']['life360_account'], self.record['options']['life360_account'])):
            self.assertNotEqual(storage.sha(storage.canonical(old)), storage.sha(storage.canonical(new)))
        self.assertEqual(self.record['data'], self.record['options'])
        self.assertEqual(set(self.record['options']['members']), {join['entity_id'] for join in self.selection['joins']})

    def test_selection_requires_unique_explicit_item_and_person_joins(self):
        self.assertEqual([join['kind'] for join in self.selection['joins']], ['item', 'item', 'person', 'person'])
        for mutate in ('duplicate_entity', 'duplicate_unique', 'wrong_owner', 'wrong_kind', 'wrong_entry', 'extra_field'):
            value = deepcopy(self.selection)
            if mutate == 'duplicate_entity': value['joins'][1]['entity_id'] = value['joins'][0]['entity_id']
            elif mutate == 'duplicate_unique': value['joins'][1]['unique_id'] = value['joins'][0]['unique_id']
            elif mutate == 'wrong_owner': value['joins'][0]['config_entry_id'] = 'foreign'
            elif mutate == 'wrong_kind': value['joins'][0]['kind'] = 'person'
            elif mutate == 'wrong_entry': value['entry_id'] = 'foreign'
            else: value['joins'][0]['private'] = 'PRIVATE-CANARY'
            with self.subTest(mutate=mutate), self.assertRaises(storage.Refused):
                storage.selection_shape(value, self.record['entry_id'])

    def test_metadata_foreign_authenticated_identity_is_refused(self):
        value = deepcopy(self.record)
        next(iter(value['options']['findmy_accounts'].values()))['account_identity'] = '0' * 64
        value['data'] = deepcopy(value['options'])
        with self.assertRaises(storage.Refused):
            storage.consistency(value, self.selection, self.payload, self.identity, self.registry)

    def test_metadata_unknown_selected_identifier_is_refused(self):
        value = deepcopy(self.record)
        items = next(iter(value['options']['findmy_accounts'].values()))['items']
        items['foreign'] = items.pop(next(iter(items)))
        value['data'] = deepcopy(value['options'])
        with self.assertRaises(storage.Refused):
            storage.consistency(value, self.selection, self.payload, self.identity, self.registry)

    def test_data_options_divergence_is_refused(self):
        value = deepcopy(self.record)
        value['data']['display_name'] = 'different'
        with self.assertRaises(storage.Refused):
            storage.consistency(value, self.selection, self.payload, self.identity, self.registry)

    def test_persisted_entry_requires_HA_verified_title_and_disabled_identity(self):
        record = deepcopy(self.record)
        record['title'] = storage.ACCEPTED_TITLE
        store = {'data': {'entries': [record]}}
        self.assertIs(storage.entry_from(store), record)
        for field, value in (('title', 'Synthetic saved storage QA'), ('disabled_by', None),
                             ('version', True), ('minor_version', True)):
            altered = deepcopy(store)
            altered['data']['entries'][0][field] = value
            with self.subTest(field=field), self.assertRaises(storage.Refused):
                storage.entry_from(altered)

    def test_registry_identity_owner_disabled_missing_and_duplicate_are_refused(self):
        for field, replacement in (('unique_id', 'foreign'), ('config_entry_id', 'foreign'),
                                   ('platform', 'foreign'), ('disabled_by', None)):
            value = deepcopy(self.registry)
            value['data']['entities'][0][field] = replacement
            with self.subTest(field=field), self.assertRaises(storage.Refused):
                storage.registry_projection(self.selection, value)
        for entities in (self.registry['data']['entities'][1:], self.registry['data']['entities'] + self.registry['data']['entities'][:1]):
            with self.subTest(entities=len(entities)), self.assertRaises(storage.Refused):
                storage.registry_projection(self.selection, {'data': {'entities': entities}})

    def test_registry_projection_uses_only_explicit_joins_and_ignores_unselected_old_entry(self):
        extra = deepcopy(self.registry)
        extra['data']['entities'].append({'entity_id': 'device_tracker.old_unselected', 'unique_id': 'old',
            'config_entry_id': self.record['entry_id'], 'platform': 'homecircle', 'disabled_by': None})
        expected = sorted([{key: join[key] for key in ('entity_id', 'unique_id', 'config_entry_id')}
                           for join in self.selection['joins']], key=lambda item: item['entity_id'])
        self.assertEqual(storage.registry_projection(self.selection, extra), expected)

    def test_password_or_unfiltered_grants_are_refused(self):
        for kind in ('password', 'info', 'grant'):
            value = deepcopy(self.payload)
            if kind in {'password', 'info'}:
                value['session']['account'][kind] = 'PRIVATE-CANARY'
            else:
                value['session']['login']['data']['mobileme_data']['tokens']['other'] = 'PRIVATE-CANARY'
            with self.subTest(kind=kind), self.assertRaises(storage.Refused):
                storage.consistency(self.record, self.selection, value, self.identity, self.registry)

    def test_foreign_ledger_is_refused_by_actual_identity_validation(self):
        value = deepcopy(self.payload)
        value['identity_state']['account_identity'] = '0' * 64
        with self.assertRaises(self.identity.IdentityError):
            storage.consistency(self.record, self.selection, value, self.identity, self.registry)

    def test_exact_seven_hash_recipes_bind_options_credentials_and_selection(self):
        pair = self.root / 'pair'
        pair.mkdir(mode=0o700)
        self.write(pair / 'session.key', b'synthetic key bytes')
        self.write(pair / 'session.vault', b'synthetic encrypted bytes')
        value = storage.fingerprints(self.record, self.selection, self.payload, pair)
        self.assertEqual(set(value), storage.FINGERPRINTS)
        self.assertEqual(value['config_sha256'], storage.sha(storage.canonical({'data': self.record['data'], 'options': self.record['options']})))
        self.assertEqual(value['credentials_sha256'], storage.sha(storage.canonical(self.record['options']['life360_account'])))
        self.assertEqual(value['selection_sha256'], storage.sha(storage.canonical(self.selection)))
        self.assertEqual(value['ledger_sha256'], storage.sha(storage.canonical(self.payload['identity_state'])))

    def test_proof_requires_seven_distinct_mutation_fingerprints(self):
        baseline = self.fingerprints()
        mutation = {key: hashlib.sha256(('mutated-' + key).encode()).hexdigest() for key in baseline}
        self.assertEqual(storage.proof_shape({'schema': 1, 'baseline': baseline, 'mutation': mutation})['mutation'], mutation)
        for key in baseline:
            altered = dict(mutation, **{key: baseline[key]})
            with self.subTest(key=key), self.assertRaises(storage.Refused):
                storage.proof_shape({'schema': 1, 'baseline': baseline, 'mutation': altered})

    def test_proof_refuses_missing_extra_unknown_schema_and_raw_values(self):
        baseline = self.fingerprints()
        for value in ({'schema': True, 'baseline': baseline, 'mutation': None},
                      {'schema': 1, 'baseline': baseline, 'mutation': None, 'raw': 'PRIVATE-CANARY'},
                      {'schema': 1, 'baseline': {**baseline, 'key_sha256': 'PRIVATE-CANARY'}, 'mutation': None}):
            with self.subTest(value=value), self.assertRaises(storage.Refused):
                storage.proof_shape(value)

    def test_private_file_read_refuses_symlink_unsafe_mode_directory_and_large_input(self):
        path = self.root / 'private.json'
        self.write(path, b'{}')
        self.assertEqual(storage.regular(path), b'{}')
        with self.assertRaises(storage.Refused): storage.regular(path, maximum=1)
        path.chmod(0o644)
        with self.assertRaises(storage.Refused): storage.regular(path)
        path.chmod(0o600)
        link = self.root / 'link'
        link.symlink_to(path)
        with self.assertRaises(OSError): storage.regular(link)
        with self.assertRaises(storage.Refused): storage.regular(self.root)

    def test_private_json_duplicate_keys_are_refused(self):
        path = self.root / 'duplicate.json'
        self.write(path, b'{"schema":1,"schema":1}')
        with self.assertRaises(storage.Refused): storage.read_json(path)

    def test_atomic_private_write_keeps_mode_and_refuses_existing_symlink_or_fresh_collision(self):
        path = self.root / 'value.json'
        storage.write_private(path, {'value': 1}, fresh=True)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        storage.write_private(path, {'value': 2})
        self.assertEqual(storage.read_json(path), {'value': 2})
        with self.assertRaises(storage.Refused): storage.write_private(path, {'value': 3}, fresh=True)
        link = self.root / 'link.json'
        link.symlink_to(path)
        with self.assertRaises(OSError): storage.write_private(link, {'value': 3})
        self.assertEqual(storage.read_json(path), {'value': 2})

    def test_snapshot_preserves_empty_guard_lock_bytes(self):
        path = self.root / 'ledger.lock'
        self.write(path, b'')
        before = storage.snapshot([path])
        self.assertEqual(before[str(path)][-1], b'')
        self.assertEqual(storage.snapshot([path]), before)

    def test_no_op_requires_cipher_bytes_inode_and_timestamp_preservation(self):
        class Vault:
            key_path = self.root / 'session.key'
            data_path = self.root / 'session.vault'
            def save_account(inner, *_args, **_kwargs):
                pass
        self.write(Vault.key_path, b'key')
        self.write(Vault.data_path, b'cipher')
        storage.no_op(Vault(), self.payload)
        class Replacing(Vault):
            def save_account(inner, *_args, **_kwargs):
                temporary = self.root / 'replacement'
                temporary.write_bytes(inner.data_path.read_bytes())
                temporary.replace(inner.data_path)
        with self.assertRaises(storage.Refused): storage.no_op(Replacing(), self.payload)

    def test_source_mismatch_refuses_before_any_source_execution(self):
        for name in storage.SOURCE_FILES:
            self.write(self.root / name, b'raise RuntimeError("PRIVATE-CANARY")')
        inputs = {'source_commit': storage.SOURCE_COMMIT, 'storage_source_sha256': storage.SOURCE_FILES}
        with patch.object(storage, 'PACKAGE', self.root), patch.object(storage.sys, 'platform', 'linux'), self.assertRaises(storage.Refused):
            storage.load_products(inputs)
        self.assertFalse(any(name.startswith('_homecircle_storage_qa_exact') for name in storage.sys.modules))

    def test_source_shape_or_commit_refuses_before_read_or_import(self):
        for value in ({'source_commit': 'wrong', 'storage_source_sha256': storage.SOURCE_FILES},
                      {'source_commit': storage.SOURCE_COMMIT, 'storage_source_sha256': {}}):
            with patch.object(storage, 'regular') as read, patch.object(storage.sys, 'platform', 'linux'), self.assertRaises(storage.Refused):
                storage.load_products(value)
            read.assert_not_called()

    def test_existing_managed_namespace_is_refused_without_parsing_values(self):
        with patch.dict(storage.sys.modules, {'custom_components.homecircle': object()}), self.assertRaises(storage.Refused):
            storage.no_managed_imports()

    def test_public_success_has_only_fixed_keys_counts_and_action_flags(self):
        expected_keys = {'schema', 'action', 'outcome', 'entry_disabled', 'managed_candidate_imported',
            'synthetic_only', 'source_files_verified', 'storage_checks', 'private_proof_written'}
        for action in storage.ACTIONS:
            value = storage.public_result(action)
            self.assertEqual(set(value), expected_keys)
            self.assertEqual(set(value['storage_checks']), storage.CHECKS)
            self.assertEqual(value['storage_checks']['negative_cases'], 18 if action.startswith('validate_') else 0)
            self.assertEqual(value['private_proof_written'], action in {'seed', 'mutate'})
            self.assertNotIn('PRIVATE-CANARY', json.dumps(value))
            self.assertNotIn(self.record['entry_id'], json.dumps(value))

    def test_public_failure_never_renders_unknown_or_exception_text(self):
        class Hostile:
            def __str__(self):
                raise AssertionError('must not render')
        for value in ('PRIVATE-CANARY', Hostile(), {'private': 'PRIVATE-CANARY'}, True):
            self.assertEqual(storage.public_failure(value), {'schema': 1, 'outcome': 'failed', 'stage': 'unrecognized'})

    def test_cli_rejects_wrong_job_before_source_read_or_mutation(self):
        self.write(self.root / 'storage-job.json', {'schema': 1, 'action': 'seed', 'token': '0' * 32,
            'generation': 'before_restore', 'branch_commit': 'a' * 40})
        with patch.object(storage, 'CONTROL', self.root), patch.object(storage, 'load_products') as products, self.assertRaises(storage.Refused):
            storage.run('seed', '1' * 32, 'before_restore', 'a' * 40)
        products.assert_not_called()

    def test_invalid_cli_inputs_fail_before_private_io(self):
        for arguments in (('seed', 'private', 'before_restore', 'a' * 40), ('validate_restored', 'a' * 32, 'before_restore', 'a' * 40),
                          ('unknown', 'a' * 32, 'before_restore', 'a' * 40), ('seed', 'a' * 32, 'before_restore', 'private')):
            with self.subTest(arguments=arguments), patch.object(storage, 'read_json') as read, self.assertRaises(storage.Refused):
                storage.run(*arguments)
            read.assert_not_called()

    def test_control_flow_validates_guard_before_postrestore_vault_load(self):
        tree = ast.parse(Path(storage.__file__).read_bytes())
        run = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'run')
        otherwise = next(node for node in run.body if isinstance(node, ast.If) and ast.unparse(node.test) == "action == 'seed'").orelse[0].orelse
        calls = [ast.unparse(node) for node in otherwise]
        self.assertIn("stage('guard')", calls[0])
        self.assertIn('guard_counter(guard_module, 3)', calls[1])
        first_load = next(index for index, node in enumerate(calls) if 'vault.load()' in node)
        self.assertGreater(first_load, 1)

    def test_module_has_no_HA_provider_or_SDK_import_and_only_pinned_dynamic_sources(self):
        tree = ast.parse(Path(storage.__file__).read_bytes())
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import): names.extend(item.name for item in node.names)
            elif isinstance(node, ast.ImportFrom): names.append(node.module)
        self.assertFalse(any(name.startswith(('homeassistant', 'custom_components', 'findmy', 'life360')) for name in names))
        self.assertEqual(set(storage.SOURCE_FILES), {'findmy_vault.py', 'findmy_identity.py', 'findmy_recovery_guard.py'})
        self.assertNotIn('__init__.py', json.dumps(storage.SOURCE_FILES))

if __name__ == '__main__':
    unittest.main()
