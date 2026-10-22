"""Private synthetic saved-storage witness; only fixed aggregates reach stdout.

Executed through stdin in a bounded, network-none Core-image context. This file
does not import Home Assistant, HomeCircle __init__, providers or native workers.
The actual SHA-bound Vault/Fernet and identity modules execute only on Linux.
"""
import asyncio
import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import sys
import tempfile
import time
import types

CONFIG = Path('/data/homeassistant')
CONTROL = CONFIG / 'homecircle-safe-restore-qa-control'
PACKAGE = CONFIG / 'custom_components/homecircle'
GUARD_ROOT = CONFIG / '.storage/homecircle_findmy/recovery_guard'
SOURCE_COMMIT = '91ae59106a661143b770d7a3564d363c7c11a7dd'
SOURCE_FILES = {
    'findmy_vault.py': '1959c143d36c4f06aff13d85aed2886c32161de86680fd0567427bda418e12f5',
    'findmy_identity.py': '0a020ad7f319b4d13686b7c2c177b762a4aabf30420164bf037cda1b8a7bc7c5',
    'findmy_recovery_guard.py': 'c8abe90b71c216e14d63b8d7382f377128aa0cce83ce53e553039fee3005ea6a'}
IDENTITY = 'a' * 64
ACCEPTED_TITLE = 'Synthetic saved storage verified'
PICTURE_ID = 'c' * 32
PICTURE = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAD0lEQVR4nGNgmPAAhCAUACTOBcF1AlBBAAAAAElFTkSuQmCC')
PICTURE_SHA256 = '3a51cbff9fe4d3958488319741b290925e0a0e22447ef2a03309427cfc7d3f0d'
ACTIONS = ('seed', 'mutate', 'validate_restored', 'validate_restart')
FINGERPRINTS = frozenset({'config_sha256', 'key_sha256', 'vault_sha256', 'payload_sha256',
                          'ledger_sha256', 'selection_sha256', 'credentials_sha256'})
NEGATIVES = ('missing_key', 'wrong_valid_key', 'invalid_base64_key', 'short_decoded_key',
    'tampered_cipher', 'truncated_cipher', 'key_permissions', 'vault_permissions',
    'key_symlink', 'vault_symlink', 'key_directory', 'vault_directory', 'foreign_ledger',
    'metadata_identity', 'metadata_selection', 'data_options_divergence',
    'registry_identity', 'duplicate_join')
STAGES = frozenset({'platform', 'arguments', 'job', 'sources', 'seed_preconditions', 'seed',
    'mutation_preconditions', 'mutation', 'guard', 'private_state', 'restored_baseline',
    'consistency', 'negative_cases', 'no_op', 'preservation', 'result', 'unrecognized'})
CHECKS = frozenset({'actual_fernet', 'account_identity_bound', 'selection_and_ledger_bound',
    'pair_private', 'passwordless_session', 'config_snapshots_equal', 'baseline_proof_preserved',
    'pair_matches_baseline', 'discriminating_mutation', 'no_op_pair_preserved',
    'main_store_preserved', 'clones_removed', 'negative_cases', 'selected_items',
    'deselected_commitments', 'guard_counter'})
_stage = 'platform'
_deadline = None

class Refused(RuntimeError):
    pass

def require(value):
    if not value:
        raise Refused('synthetic_storage_refused')

def stage(value):
    global _stage
    require(value in STAGES)
    _stage = value
    if _deadline is not None:
        require(time.monotonic() < _deadline)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()

def unique(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value)
        value[key] = item
    return value

def regular(path, *, private=True, maximum=2 * 1024**2, minimum=1):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.geteuid()
                and minimum <= info.st_size <= maximum and (not private or stat.S_IMODE(info.st_mode) == 0o600))
        stream = os.fdopen(descriptor, 'rb')
        descriptor = None
        with stream:
            raw = stream.read(maximum + 1)
    finally:
        if descriptor is not None:
            os.close(descriptor)
    require(minimum <= len(raw) <= maximum)
    return raw

def read_json(path):
    return json.loads(regular(path), object_pairs_hook=unique)

def managed_regular(path):
    # Only these two HA-owned stores use Home Assistant's public-file mode.
    require(path in {CONFIG / '.storage/core.config_entries', CONFIG / '.storage/core.entity_registry'})
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.geteuid()
                and 1 <= info.st_size <= 2 * 1024**2 and stat.S_IMODE(info.st_mode) in {0o600, 0o644})
        stream = os.fdopen(descriptor, 'rb')
        descriptor = None
        with stream:
            raw = stream.read(2 * 1024**2 + 1)
    finally:
        if descriptor is not None:
            os.close(descriptor)
    require(1 <= len(raw) <= 2 * 1024**2)
    return raw

def read_managed_json(path):
    return json.loads(managed_regular(path), object_pairs_hook=unique)

def directory(path, *, create=False, private=True):
    if create and not path.exists() and not path.is_symlink():
        path.mkdir(mode=0o700)
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) and not path.is_symlink() and info.st_uid == os.geteuid()
            and (stat.S_IMODE(info.st_mode) == 0o700 if private else not info.st_mode & 0o022))

def write_private(path, value, *, fresh=False):
    directory(path.parent, private=path.parent != CONFIG / '.storage')
    if path.exists() or path.is_symlink():
        require(not fresh)
        if path in {CONFIG / '.storage/core.config_entries', CONFIG / '.storage/core.entity_registry'}:
            managed_regular(path)
        else:
            regular(path)
    raw = canonical(value)
    descriptor, name = tempfile.mkstemp(prefix='.storage-qa-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if os.path.exists(name):
            os.unlink(name)

def no_managed_imports():
    require(not any(name == 'custom_components.homecircle' or name.startswith('custom_components.homecircle.')
                    or name == 'findmy' or name.startswith('findmy.') for name in sys.modules))

def load_products(inputs):
    require(sys.platform == 'linux' and inputs.get('source_commit') == SOURCE_COMMIT
            and inputs.get('storage_source_sha256') == SOURCE_FILES)
    raw = {name: regular(PACKAGE / name, private=False, maximum=1024**2) for name in SOURCE_FILES}
    require(all(sha(value) == SOURCE_FILES[name] for name, value in raw.items()))
    no_managed_imports()
    alias = '_homecircle_storage_qa_exact'
    require(alias not in sys.modules and not any(name.startswith(alias + '.') for name in sys.modules))
    package = types.ModuleType(alias)
    package.__path__ = []
    sys.modules[alias] = package
    modules = {}
    # Preload the only allowed relative import before loading the vault.
    for filename in ('findmy_identity.py', 'findmy_vault.py', 'findmy_recovery_guard.py'):
        name = alias + '.' + filename[:-3]
        module = types.ModuleType(name)
        module.__file__ = str(PACKAGE / filename)
        module.__package__ = alias
        sys.modules[name] = module
        exec(compile(raw[filename], str(PACKAGE / filename), 'exec'), module.__dict__)
        modules[filename] = module
    no_managed_imports()
    from cryptography.fernet import Fernet
    require(modules['findmy_vault.py'].Fernet is Fernet)
    return modules['findmy_vault.py'], modules['findmy_identity.py'], modules['findmy_recovery_guard.py']

def fingerprint_shape(value):
    require(type(value) is dict and set(value) == FINGERPRINTS
            and all(type(item) is str and re.fullmatch('[0-9a-f]{64}', item) for item in value.values()))
    return value

def proof_shape(value):
    require(type(value) is dict and set(value) == {'schema', 'baseline', 'mutation'}
            and type(value['schema']) is int and value['schema'] == 1)
    fingerprint_shape(value['baseline'])
    if value['mutation'] is not None:
        fingerprint_shape(value['mutation'])
        require(all(value['baseline'][name] != value['mutation'][name] for name in FINGERPRINTS))
    return value

def config_store():
    path = CONFIG / '.storage/core.config_entries'
    value = read_managed_json(path)
    require(type(value) is dict and value.get('version') == 1 and type(value.get('version')) is int
            and value.get('minor_version') == 5 and type(value.get('minor_version')) is int
            and value.get('key') == 'core.config_entries' and type(value.get('data')) is dict
            and type(value['data'].get('entries')) is list)
    return value

def entry_from(value):
    records = [entry for entry in value['data']['entries'] if entry.get('domain') == 'homecircle']
    require(len(records) == 1)
    record = records[0]
    require(record.get('disabled_by') is None and record.get('title') == ACCEPTED_TITLE
            and record.get('version') == 1 and type(record.get('version')) is int
            and record.get('minor_version') == 1 and type(record.get('minor_version')) is int and type(record.get('entry_id')) is str
            and re.fullmatch('[0-9a-f]{32}', record['entry_id']) and type(record.get('data')) is dict
            and type(record.get('options')) is dict and record['data'] == record['options'])
    return record

def account_metadata(record):
    accounts = record['options'].get('findmy_accounts')
    require(type(accounts) is dict and len(accounts) == 1)
    account_id, metadata = next(iter(accounts.items()))
    require(type(account_id) is str and re.fullmatch('[0-9a-f]{32}', account_id)
            and type(metadata) is dict and type(metadata.get('storage_id')) is str
            and re.fullmatch('[0-9a-f]{32}', metadata['storage_id'])
            and type(metadata.get('account_identity')) is str and re.fullmatch('[0-9a-f]{64}', metadata['account_identity'])
            and type(metadata.get('session_revision')) is int and metadata['session_revision'] >= 1
            and type(metadata.get('items')) is dict and len(metadata['items']) == 2)
    return account_id, metadata

def pair_root(record, *, create=False):
    _, metadata = account_metadata(record)
    parent = CONFIG / '.storage/homecircle_findmy'
    accounts = parent / 'homecircle_accounts'
    root = accounts / metadata['storage_id']
    for path in (parent, accounts, root):
        directory(path, create=create)
    return root

def selection_shape(value, entry_id):
    require(type(value) is dict and set(value) == {'schema', 'entry_id', 'joins'}
            and type(value['schema']) is int and value['schema'] == 1 and value['entry_id'] == entry_id
            and type(value['joins']) is list and len(value['joins']) == 4)
    ids, uniques, kinds = set(), set(), []
    for join in value['joins']:
        require(type(join) is dict and set(join) == {'entity_id', 'unique_id', 'config_entry_id', 'kind'}
                and join['config_entry_id'] == entry_id and join['kind'] in {'item', 'person'}
                and type(join['entity_id']) is str and re.fullmatch(r'device_tracker\.[a-z0-9_]{1,120}', join['entity_id'])
                and type(join['unique_id']) is str and re.fullmatch('[A-Za-z0-9_]{1,160}', join['unique_id']))
        ids.add(join['entity_id'])
        uniques.add(join['unique_id'])
        kinds.append(join['kind'])
    require(len(ids) == len(uniques) == 4 and kinds.count('item') == kinds.count('person') == 2)
    return value

def registry_projection(selection, registry):
    require(type(registry) is dict and type(registry.get('data')) is dict
            and type(registry['data'].get('entities')) is list)
    result = []
    for join in selection['joins']:
        matches = [entity for entity in registry['data']['entities'] if entity.get('entity_id') == join['entity_id']]
        require(len(matches) == 1)
        entity = matches[0]
        require(entity.get('platform') == 'homecircle' and entity.get('config_entry_id') == join['config_entry_id']
                and entity.get('unique_id') == join['unique_id'] and entity.get('disabled_by') is None)
        result.append({key: entity[key] for key in ('entity_id', 'unique_id', 'config_entry_id')})
    return sorted(result, key=lambda item: item['entity_id'])

def consistency(record, selection, payload, identity, registry=None):
    require(record['disabled_by'] is None and record['data'] == record['options'])
    selection_shape(selection, record['entry_id'])
    _, metadata = account_metadata(record)
    require(payload.get('version') == 2 and type(payload.get('items')) is dict and len(payload['items']) == 2
            and set(metadata['items']) == set(payload['items']) and type(payload.get('identity_state')) is dict)
    session = payload['session']
    require(session['account']['password'] is None and session['account']['info'] is None
            and identity.authenticated_identity(session) == metadata['account_identity']
            and set(session['login']['data']) == {'dsid', 'mobileme_data'}
            and set(session['login']['data']['mobileme_data']) == {'tokens'}
            and set(session['login']['data']['mobileme_data']['tokens']) == {'searchPartyToken'})
    ledger = identity.validate_state(payload['identity_state'], session)
    require(len(ledger['records']) == 3)
    selected_records = set()
    expected_items = []
    item_joins = {join['unique_id']: join for join in selection['joins'] if join['kind'] == 'item'}
    for identifier, saved in payload['items'].items():
        item = metadata['items'][identifier]
        commitment = identity.commitment_for(ledger, saved['accessory'])
        require(commitment in ledger['records'] and ledger['records'][commitment]['identifier'] == identifier
                and ledger['records'][commitment]['metadata'] == identity.safe_metadata(item)
                and item.get('unique_id') in item_joins and type(item.get('name')) is str and bool(item['name']))
        join = item_joins[item['unique_id']]
        require(item.get('display_preferences', {}).get('kind') == 'item'
                and item['display_preferences'].get('trackers') == [join['entity_id']]
                and bool(item['display_preferences'].get('display_name')))
        selected_records.add(commitment)
        expected_items.append(join['entity_id'])
    require(len(selected_records) == 2 and len(set(ledger['records']) - selected_records) == 1)
    options = record['options']
    require(options.get('people') == [] and options.get('pets') == []
            and sorted(options.get('items', [])) == sorted(expected_items)
            and sorted(options.get('people_trackers', [])) == sorted(join['entity_id'] for join in selection['joins'] if join['kind'] == 'person')
            and options.get('primary_home') == 'zone.home' and options.get('places') == ['zone.example_saved_storage']
            and type(options.get('display_name')) is str and bool(options['display_name'])
            and type(options.get('members')) is dict and set(options['members']) == {join['entity_id'] for join in selection['joins']})
    for join in selection['joins']:
        member = options['members'][join['entity_id']]
        require(type(member) is dict and member.get('kind') == join['kind']
                and member.get('trackers') == [join['entity_id']] and member.get('additional_residences') == []
                and type(member.get('show_on_map')) is bool and type(member.get('display_name')) is str
                and 0 < len(member['display_name'].strip()) <= 60
                and member.get('auto_request_location') is False and member.get('tracker_selection') == 'freshest_gps'
                and member.get('supporting') == {} and member.get('location_reports') == {})
        if join['kind'] == 'item':
            item = next(item for item in metadata['items'].values() if item['unique_id'] == join['unique_id'])
            require(item['display_preferences'] == member)
    credentials = options.get('life360_account')
    require(type(credentials) is dict and set(credentials) == {'method', 'username', 'secret', 'account_id_hash'}
            and credentials['method'] == 'token' and credentials['username'] == ''
            and type(credentials['secret']) is str and bool(credentials['secret'])
            and type(credentials['account_id_hash']) is str and re.fullmatch('[0-9a-f]{64}', credentials['account_id_hash']))
    if registry is not None:
        registry_projection(selection, registry)
    return True

def fingerprints(record, selection, payload, root):
    return {'config_sha256': sha(canonical({'data': record['data'], 'options': record['options']})),
        'key_sha256': sha(regular(root / 'session.key')), 'vault_sha256': sha(regular(root / 'session.vault')),
        'payload_sha256': sha(canonical(payload)), 'ledger_sha256': sha(canonical(payload['identity_state'])),
        'selection_sha256': sha(canonical(selection)),
        'credentials_sha256': sha(canonical(record['options']['life360_account']))}

def mutate_semantics(record, selection, payload, identity):
    """Only the deliberately synthetic postbackup state, before pair creation."""
    payload['session']['login']['data']['mobileme_data']['tokens']['searchPartyToken'] = 'QA-SESSION-MUTATED-' + secrets.token_hex(24)
    _, metadata = account_metadata(record)
    metadata['session_revision'] += 1
    identifier = next(iter(metadata['items']))
    old_unique = metadata['items'][identifier]['unique_id']
    join = next(item for item in selection['joins'] if item['unique_id'] == old_unique)
    old_entity = join['entity_id']
    join['entity_id'] = 'device_tracker.homecircle_saved_qa_' + secrets.token_hex(8)
    join['unique_id'] = 'homecircle_findmy_' + secrets.token_hex(32)
    metadata['items'][identifier]['unique_id'] = join['unique_id']
    metadata['items'][identifier]['display_preferences']['trackers'] = [join['entity_id']]
    member = record['options']['members'].pop(old_entity)
    member['trackers'] = [join['entity_id']]
    record['options']['members'][join['entity_id']] = member
    # Genuine HMAC commitments and the secret remain bound to the same keys.
    # Explicit selected metadata changes make the mutated ledger discriminating.
    payload['identity_state'] = identity.selection_state(payload['session'], payload['items'], metadata['items'], payload['identity_state'])
    record['options']['items'] = [item['entity_id'] for item in selection['joins'] if item['kind'] == 'item']
    record['options']['life360_account']['secret'] = 'QA-LIFE360-MUTATED-' + secrets.token_hex(32)
    record['data'] = deepcopy(record['options'])

async def guard_counter(module, expected, *, advance=0):
    guard = module.RecoveryGuard(GUARD_ROOT)
    value = await guard.status(IDENTITY)
    require(value == {'rejected': expected - advance, 'uncertain': 0, 'pending': 0,
        'verified': 0, 'unresolved': expected - advance, 'limit': 3, 'blocked': expected - advance >= 3})
    for _ in range(advance):
        async with guard.attempt(IDENTITY) as attempt:
            await attempt.before_dispatch()
            await attempt.refused()
    value = await guard.status(IDENTITY)
    require(value == {'rejected': expected, 'uncertain': 0, 'pending': 0, 'verified': 0,
                      'unresolved': expected, 'limit': 3, 'blocked': expected >= 3})
    return expected

def accessory():
    # Recent pairing bounds native rolling-key derivation during this finite QA run.
    paired_at = (datetime.now(timezone.utc) - timedelta(days=1)).replace(microsecond=0).isoformat()
    return {'type': 'accessory', 'master_key': secrets.token_hex(28),
        'skn': secrets.token_hex(32), 'sks': secrets.token_hex(32), 'paired_at': paired_at,
        'name': 'Synthetic saved accessory', 'model': 'AirTag', 'identifier': secrets.token_hex(16),
        'alignment_date': None, 'alignment_index': 0, 'group_identifier': None, 'serial_number': None}

def new_synthetic(identity):
    entry_id, account_id = secrets.token_hex(16), secrets.token_hex(16)
    session = {'type': 'account', 'ids': {'uid': secrets.token_hex(16), 'devid': secrets.token_hex(16)},
        'anisette': {'type': 'aniRemote', 'url': 'https://example.invalid'},
        'account': {'username': 'synthetic-' + secrets.token_hex(8) + '@example.invalid',
                          'password': 'QA-DO-NOT-PERSIST-' + secrets.token_hex(16), 'info': {'private': 'QA-REMOVE'}},
        'login': {'state': 3, 'data': {'dsid': str(10**15 + secrets.randbelow(9 * 10**15)),
            'mobileme_data': {'tokens': {'searchPartyToken': 'QA-SESSION-' + secrets.token_hex(24),
                                       'otherGrant': 'QA-REMOVE'}}, 'profile': 'QA-REMOVE'}}}
    identifiers = [secrets.token_hex(16) for _ in range(3)]
    exported = {identifier: {'accessory': accessory(), 'report': {'latitude': 1.25, 'longitude': 2.5,
                    'last_seen': '2026-01-01T00:00:0' + str(index) + '+00:00', 'gps_accuracy': 10.0}}
                for index, identifier in enumerate(identifiers)}
    joins, metadata = [], {}
    for index, identifier in enumerate(identifiers):
        unique_id = 'homecircle_findmy_' + account_id + '_' + identifier
        entity_id = 'device_tracker.homecircle_saved_qa_' + secrets.token_hex(8)
        metadata[identifier] = {'name': 'Synthetic item ' + str(index + 1), 'type': 'airtag', 'unique_id': unique_id,
            'display_preferences': {'kind': 'item', 'trackers': [entity_id],
                'display_name': 'Synthetic item display ' + str(index + 1), 'show_on_map': True,
                'additional_residences': [], 'auto_request_location': False,
                'tracker_selection': 'freshest_gps', 'supporting': {}, 'location_reports': {}}}
        if index < 2:
            joins.append({'entity_id': entity_id, 'unique_id': unique_id, 'config_entry_id': entry_id, 'kind': 'item'})
    for _ in range(2):
        joins.append({'entity_id': 'device_tracker.homecircle_saved_qa_' + secrets.token_hex(8),
                      'unique_id': 'homecircle_life360_' + secrets.token_hex(16),
                      'config_entry_id': entry_id, 'kind': 'person'})
    ledger = identity.selection_state(session, exported, metadata)
    items = {identifier: exported[identifier] for identifier in identifiers[:2]}
    account = {'session_revision': 1, 'label': 'Synthetic saved Apple account',
               'account_identity': identity.authenticated_identity(session), 'storage_id': account_id,
               'items': {identifier: metadata[identifier] for identifier in items}}
    settings = {'findmy_accounts': {account_id: account}, 'findmy_enabled': True,
        'life360_account': {'method': 'token', 'username': '', 'secret': 'QA-LIFE360-' + secrets.token_hex(32),
                           'account_id_hash': sha(secrets.token_bytes(32))}, 'life360_direct': True,
        'items': [join['entity_id'] for join in joins if join['kind'] == 'item'],
        'people_trackers': [join['entity_id'] for join in joins if join['kind'] == 'person'],
        'people': [], 'pets': [], 'display_name': 'Synthetic saved storage household',
        'primary_home': 'zone.home', 'places': ['zone.example_saved_storage'],
        'members': {join['entity_id']: {'kind': join['kind'], 'trackers': [join['entity_id']],
            'additional_residences': [], 'display_name': 'Synthetic saved member ' + str(index + 1),
            'show_on_map': True, 'auto_request_location': False, 'tracker_selection': 'freshest_gps',
            'supporting': {}, 'location_reports': {}} for index, join in enumerate(joins)}}
    for item in account['items'].values():
        entity = next(join['entity_id'] for join in joins if join['unique_id'] == item['unique_id'])
        item['display_preferences'] = deepcopy(settings['members'][entity])
    first_person = next(join['entity_id'] for join in joins if join['kind'] == 'person')
    settings['members'][first_person]['picture_id'] = PICTURE_ID
    # Ledger metadata mirrors the explicit member preferences after selection.
    ledger = identity.selection_state(session, items, account['items'], ledger)
    record = {'created_at': '2026-01-01T00:00:00+00:00', 'modified_at': '2026-01-01T00:00:00+00:00',
        'data': deepcopy(settings), 'options': deepcopy(settings), 'disabled_by': None, 'domain': 'homecircle',
        'entry_id': entry_id, 'minor_version': 1, 'version': 1, 'source': 'user', 'title': 'Synthetic saved storage QA',
        'unique_id': 'homecircle', 'pref_disable_new_entities': False, 'pref_disable_polling': False,
        'discovery_keys': {}, 'subentries': []}
    selection = {'schema': 1, 'entry_id': entry_id, 'joins': joins}
    return record, selection, session, items, ledger

def new_registry_rows(selection):
    """Exact Core2026.10.2 storage fields; identity comes only from explicit joins."""
    selection_shape(selection, selection['entry_id'])
    now = datetime.now(timezone.utc).isoformat()
    return [{
        'aliases': [], 'aliases_v2': [], 'area_id': None, 'categories': {}, 'capabilities': None,
        'config_entry_id': join['config_entry_id'], 'config_subentry_id': None, 'created_at': now,
        'device_class': None, 'device_id': None, 'disabled_by': None, 'entity_category': None,
        'entity_id': join['entity_id'], 'hidden_by': None, 'icon': None, 'id': secrets.token_hex(16),
        'has_entity_name': False, 'labels': [], 'modified_at': now, 'name': None,
        'object_id_base': join['entity_id'].split('.', 1)[1], 'options': {},
        'original_device_class': None, 'original_icon': None, 'original_name': 'Synthetic saved tracker',
        'platform': 'homecircle', 'suggested_object_id': join['entity_id'].split('.', 1)[1],
        'supported_features': 0, 'translation_key': None, 'unique_id': join['unique_id'],
        'previous_unique_id': None, 'unit_of_measurement': None,
    } for join in selection['joins']]

def seed_registry(selection):
    """Write the four enabled registrations before the first managed startup."""
    path = CONFIG / '.storage/core.entity_registry'
    if path.exists() or path.is_symlink():
        registry = read_managed_json(path)
        require(type(registry) is dict and registry.get('version') == 1
                and registry.get('minor_version') == 23 and registry.get('key') == 'core.entity_registry'
                and type(registry.get('data')) is dict and type(registry['data'].get('entities')) is list
                and type(registry['data'].get('deleted_entities')) is list
                and type(registry['data'].get('settings')) is dict)
    else:
        registry = {'version': 1, 'minor_version': 23, 'key': 'core.entity_registry',
            'data': {'entities': [], 'deleted_entities': [], 'settings': {'entity_id_parts': None}}}
    rows = new_registry_rows(selection)
    ids = {row['entity_id'] for row in rows}
    unique_ids = {row['unique_id'] for row in rows}
    require(not any(row.get('entity_id') in ids or row.get('unique_id') in unique_ids
                    or row.get('config_entry_id') == selection['entry_id']
                    for row in [*registry['data']['entities'], *registry['data']['deleted_entities']]))
    registry['data']['entities'].extend(rows)
    registry_projection(selection, registry)
    write_private(path, registry)
    require(registry_projection(selection, read_managed_json(path)) == registry_projection(selection, registry))

def mutate_registry(previous, selection):
    """Apply only the fictional postbackup join mutation before managed startup."""
    selection_shape(previous, selection['entry_id'])
    selection_shape(selection, previous['entry_id'])
    path = CONFIG / '.storage/core.entity_registry'
    registry = read_managed_json(path)
    registry_projection(previous, registry)
    updated = deepcopy(registry)
    for old, new in zip(previous['joins'], selection['joins'], strict=True):
        require(old['kind'] == new['kind'] and old['config_entry_id'] == new['config_entry_id'])
        if old == new:
            continue
        require(not any(row.get('entity_id') == new['entity_id'] or row.get('unique_id') == new['unique_id']
                        for row in [*updated['data']['entities'], *updated['data'].get('deleted_entities', [])]))
        matches = [row for row in updated['data']['entities'] if row.get('entity_id') == old['entity_id']]
        require(len(matches) == 1)
        row = matches[0]
        row.update(entity_id=new['entity_id'], unique_id=new['unique_id'],
            suggested_object_id=new['entity_id'].split('.', 1)[1], object_id_base=new['entity_id'].split('.', 1)[1])
    registry_projection(selection, updated)
    write_private(path, updated)
    require(read_managed_json(path) == updated)

def seed_picture():
    """Seed a fictional image in Core's real image-upload store and directory."""
    require(sha(PICTURE) == PICTURE_SHA256)
    store = CONFIG / '.storage/image'
    require(not store.exists() and not store.is_symlink())
    image_root = CONFIG / 'image'
    directory(image_root, create=True)
    folder = image_root / PICTURE_ID
    require(not folder.exists() and not folder.is_symlink())
    directory(folder, create=True)
    original = folder / 'original'
    descriptor = os.open(original, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(PICTURE)
        stream.flush()
        os.fsync(stream.fileno())
    require(regular(original) == PICTURE)
    record = {'id': PICTURE_ID, 'filesize': len(PICTURE), 'content_type': 'image/png',
        'name': 'synthetic.png', 'uploaded_at': '2026-01-01T00:00:00+00:00'}
    write_private(store, {'version': 1, 'minor_version': 1, 'key': 'image', 'data': {'items': [record]}}, fresh=True)
    require(read_json(store)['data']['items'] == [record])

def snapshot(paths):
    result = {}
    for path in paths:
        info = path.lstat()
        if stat.S_ISREG(info.st_mode):
            content = regular(path, private=False, minimum=0)
        elif stat.S_ISLNK(info.st_mode):
            content = os.readlink(path).encode()
        else:
            content = None
        result[str(path)] = (info.st_mode, info.st_uid, info.st_gid, info.st_size, content)
    return result

def tree_snapshot(root):
    result = {}
    for path in [root, *root.rglob('*')]:
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        content = path.read_bytes() if stat.S_ISREG(info.st_mode) else os.readlink(path).encode() if stat.S_ISLNK(info.st_mode) else None
        result[relative] = (info.st_mode, info.st_size, content)
    return result

def main_paths(root):
    paths = [CONFIG / '.storage/core.config_entries', CONFIG / '.storage/core.entity_registry',
             CONTROL / 'storage-selection-private.json', CONTROL / 'storage-proof-private.json',
             root / 'session.key', root / 'session.vault']
    paths.extend(sorted(GUARD_ROOT.iterdir()))
    return paths

def no_op(vault, payload):
    before = [(path.read_bytes(), path.stat().st_ino, path.stat().st_mtime_ns)
              for path in (vault.key_path, vault.data_path)]
    vault.save_account(payload['session'], payload['items'], identity_state=payload['identity_state'])
    after = [(path.read_bytes(), path.stat().st_ino, path.stat().st_mtime_ns)
             for path in (vault.key_path, vault.data_path)]
    require(before == after)

def negative_cases(vault_module, identity, root, record, selection, payload, registry):
    # Every mutation lives in an independent newly-owned clone. Main state is
    # never passed as a fault destination, and no clone is exported.
    for case in NEGATIVES:
        stage('negative_cases')
        clone = Path(tempfile.mkdtemp(prefix='storage-negative-', dir=CONTROL))
        require(clone.parent == CONTROL)
        try:
            for name in ('session.key', 'session.vault'):
                descriptor = os.open(clone / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, 'wb') as stream:
                    stream.write(regular(root / name))
            altered_record, altered_selection, altered_registry = deepcopy(record), deepcopy(selection), deepcopy(registry)
            key, cipher = clone / 'session.key', clone / 'session.vault'
            if case == 'missing_key':
                key.unlink()
            elif case == 'wrong_valid_key':
                key.write_bytes(vault_module.Fernet.generate_key())
            elif case == 'invalid_base64_key':
                key.write_bytes(b'NOT-VALID-BASE64-!')
            elif case == 'short_decoded_key':
                key.write_bytes(b'YQ==')
            elif case == 'tampered_cipher':
                raw = bytearray(cipher.read_bytes())
                raw[len(raw) // 2] ^= 1
                cipher.write_bytes(raw)
            elif case == 'truncated_cipher':
                cipher.write_bytes(cipher.read_bytes()[:12])
            elif case in {'key_permissions', 'vault_permissions'}:
                (key if case == 'key_permissions' else cipher).chmod(0o644)
            elif case in {'key_symlink', 'vault_symlink'}:
                path = key if case == 'key_symlink' else cipher
                target = clone / 'private-target'
                path.rename(target)
                path.symlink_to(target.name)
            elif case in {'key_directory', 'vault_directory'}:
                path = key if case == 'key_directory' else cipher
                path.unlink()
                path.mkdir(mode=0o700)
            elif case == 'foreign_ledger':
                altered = deepcopy(payload)
                altered['identity_state']['account_identity'] = '0' * 64
                cipher.write_bytes(vault_module.Fernet(key.read_bytes()).encrypt(canonical(altered)))
            elif case == 'metadata_identity':
                next(iter(altered_record['options']['findmy_accounts'].values()))['account_identity'] = '0' * 64
                altered_record['data'] = deepcopy(altered_record['options'])
            elif case == 'metadata_selection':
                items = next(iter(altered_record['options']['findmy_accounts'].values()))['items']
                items['not_a_saved_item'] = items.pop(next(iter(items)))
                altered_record['data'] = deepcopy(altered_record['options'])
            elif case == 'data_options_divergence':
                altered_record['data']['display_name'] = 'deliberately different'
            elif case == 'registry_identity':
                entity = next(item for item in altered_registry['data']['entities'] if item['entity_id'] == selection['joins'][0]['entity_id'])
                entity['unique_id'] = 'foreign_registry_identity'
            elif case == 'duplicate_join':
                altered_selection['joins'][1] = deepcopy(altered_selection['joins'][0])
            before = tree_snapshot(clone)
            vault = vault_module.Vault(clone)
            if case in NEGATIVES[:13]:
                for operation in (lambda: vault.load(), lambda: vault.save_account(payload['session'], payload['items'], identity_state=payload['identity_state'])):
                    refused = False
                    try:
                        operation()
                    except vault_module.VaultError:
                        refused = True
                    require(refused and tree_snapshot(clone) == before)
            else:
                refused = False
                try:
                    consistency(altered_record, altered_selection, vault.load(), identity, altered_registry)
                except Refused:
                    refused = True
                require(refused and tree_snapshot(clone) == before)
        finally:
            require(clone.parent == CONTROL and not clone.is_symlink())
            shutil.rmtree(clone)
        require(not clone.exists() and not clone.is_symlink())
    return len(NEGATIVES)

def checks(action):
    validating = action.startswith('validate_')
    result = {name: True for name in ('actual_fernet', 'account_identity_bound', 'selection_and_ledger_bound',
              'pair_private', 'passwordless_session', 'config_snapshots_equal', 'baseline_proof_preserved')}
    result.update(pair_matches_baseline=action != 'mutate', discriminating_mutation=action == 'mutate',
        no_op_pair_preserved=validating, main_store_preserved=validating, clones_removed=validating,
        negative_cases=18 if validating else 0, selected_items=2, deselected_commitments=1,
        guard_counter=2 if action == 'seed' else 3)
    require(set(result) == CHECKS)
    return result

def public_result(action):
    require(action in ACTIONS)
    return {'schema': 1, 'action': action, 'outcome': 'passed', 'entry_disabled': False,
        'managed_candidate_imported': False, 'synthetic_only': True, 'source_files_verified': True,
        'storage_checks': checks(action), 'private_proof_written': action in {'seed', 'mutate'}}

def public_failure(value):
    return {'schema': 1, 'outcome': 'failed', 'stage': value if type(value) is str and value in STAGES else 'unrecognized'}

def run(action, token, generation, branch):
    stage('arguments')
    require(action in ACTIONS and type(token) is str and re.fullmatch('[0-9a-f]{32}', token)
            and generation == ('before_restore' if action in {'seed', 'mutate'} else 'after_restore')
            and type(branch) is str and re.fullmatch('[0-9a-f]{40}', branch))
    directory(CONTROL)
    stage('job')
    job = read_json(CONTROL / 'storage-job.json')
    require(job == {'schema': 1, 'action': action, 'token': token, 'generation': generation, 'branch_commit': branch}
            and type(job['schema']) is int)
    inputs = read_json(CONTROL / 'inputs.json')
    require(inputs.get('generation') == generation and inputs.get('branch_commit') == branch)
    stage('sources')
    vault_module, identity, guard_module = load_products(inputs)
    stage('private_state')
    store = config_store()
    proof_path = CONTROL / 'storage-proof-private.json'
    selection_path = CONTROL / 'storage-selection-private.json'
    if action == 'seed':
        stage('seed_preconditions')
        require(not any(entry.get('domain') == 'homecircle' for entry in store['data']['entries'])
                and not proof_path.exists() and not proof_path.is_symlink()
                and not selection_path.exists() and not selection_path.is_symlink())
        record, selection, session, items, ledger = new_synthetic(identity)
        stage('seed')
        root = pair_root(record, create=True)
        require(list(root.iterdir()) == [])
        vault = vault_module.Vault(root)
        vault.save_account(session, items, identity_state=ledger)
        payload = vault.load()
        consistency(record, selection, payload, identity)
        store['data']['entries'].append(record)
        write_private(CONFIG / '.storage/core.config_entries', store)
        write_private(selection_path, selection, fresh=True)
        seed_registry(selection)
        seed_picture()
        stage('guard')
        asyncio.run(guard_counter(guard_module, 2, advance=2))
        current = fingerprints(record, selection, payload, root)
        write_private(proof_path, {'schema': 1, 'baseline': current, 'mutation': None}, fresh=True)
    elif action == 'mutate':
        stage('mutation_preconditions')
        record = entry_from(store)
        selection = selection_shape(read_json(selection_path), record['entry_id'])
        root = pair_root(record)
        vault = vault_module.Vault(root)
        payload = vault.load()
        proof = proof_shape(read_json(proof_path))
        require(proof['mutation'] is None and fingerprints(record, selection, payload, root) == proof['baseline'])
        consistency(record, selection, payload, identity)
        stage('mutation')
        previous_selection = deepcopy(selection)
        mutate_semantics(record, selection, payload, identity)
        # This is an explicit fresh synthetic postbackup pair, not product repair.
        regular(root / 'session.key')
        regular(root / 'session.vault')
        (root / 'session.key').unlink()
        (root / 'session.vault').unlink()
        vault.save_account(payload['session'], payload['items'], identity_state=payload['identity_state'])
        payload = vault.load()
        consistency(record, selection, payload, identity)
        write_private(CONFIG / '.storage/core.config_entries', store)
        write_private(selection_path, selection)
        mutate_registry(previous_selection, selection)
        stage('guard')
        asyncio.run(guard_counter(guard_module, 3, advance=1))
        current = fingerprints(record, selection, payload, root)
        require(all(current[name] != proof['baseline'][name] for name in FINGERPRINTS))
        write_private(proof_path, {'schema': 1, 'baseline': proof['baseline'], 'mutation': current})
    else:
        stage('guard')
        asyncio.run(guard_counter(guard_module, 3))
        record = entry_from(store)
        selection = selection_shape(read_json(selection_path), record['entry_id'])
        root = pair_root(record)
        before = snapshot(main_paths(root))
        stage('restored_baseline')
        proof = proof_shape(read_json(proof_path))
        expected = proof_shape(read_json(CONTROL / 'storage-expected-private.json'))
        require(proof['mutation'] is None and expected['mutation'] is not None and proof['baseline'] == expected['baseline'])
        vault = vault_module.Vault(root)
        payload = vault.load()
        current = fingerprints(record, selection, payload, root)
        require(current == expected['baseline'] and all(current[name] != expected['mutation'][name] for name in FINGERPRINTS))
        registry = read_managed_json(CONFIG / '.storage/core.entity_registry')
        stage('consistency')
        consistency(record, selection, payload, identity, registry)
        joins = read_json(CONTROL / 'storage-joins-private.json')
        require(type(joins) is dict and set(joins) == {'schema', 'sha256'} and type(joins['schema']) is int and joins['schema'] == 1
                and joins['sha256'] == sha(canonical(registry_projection(selection, registry))))
        require(negative_cases(vault_module, identity, root, record, selection, payload, registry) == 18)
        stage('no_op')
        no_op(vault, payload)
        stage('preservation')
        require(snapshot(main_paths(root)) == before and fingerprints(record, selection, vault.load(), root) == current)
    stage('result')
    no_managed_imports()
    write_private(CONTROL / 'storage-result-private.json', {'schema': 1, 'action': action, **fingerprint_shape(current)})
    return public_result(action)

def main():
    global _deadline
    _deadline = time.monotonic() + 20
    try:
        require(sys.platform == 'linux' and os.geteuid() == 0)
        require(len(sys.argv) == 5)
        result = run(*sys.argv[1:])
    except BaseException:
        print(json.dumps(public_failure(_stage), sort_keys=True), flush=True)
        return 1
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
