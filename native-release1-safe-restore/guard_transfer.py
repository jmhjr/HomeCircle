"""Private owned-guest guard transfer. Raw bundle is never a public receipt."""
import asyncio
import base64
import importlib.util
import re
import sys

# BEGIN byte-identical reviewed bounded observer
"""File-only prototype: bounded metadata from an escaping exact-source failure.

No tracing hooks, exception text, path output, content reads, or recovery calls.
The caller must already have loaded the SHA-bound standalone candidate module.
"""
import ast
import errno
import hashlib
import json
import os
from pathlib import Path
import stat
import types

SOURCE_SHA = 'c8abe90b71c216e14d63b8d7382f377128aa0cce83ce53e553039fee3005ea6a'
IDENTITY = 'a' * 64
ERRNOS = frozenset({'EACCES', 'EPERM', 'ELOOP', 'ENOTDIR', 'ENOENT', 'EIO',
                    'ENOSPC', 'EROFS', 'EMFILE', 'ENFILE', 'EINVAL', 'EBADF',
                    'EAGAIN', 'EEXIST', 'EINTR', 'ENAMETOOLONG', 'EDQUOT'})
ERROR_TYPES = frozenset({'RecoveryGuardStorageError', 'OSError', 'PermissionError',
                        'FileNotFoundError', 'NotADirectoryError', 'IsADirectoryError',
                        'FileExistsError', 'BlockingIOError', 'InterruptedError',
                        'ValueError', 'TypeError', 'KeyError', 'JSONDecodeError',
                        'UnicodeDecodeError', 'UnicodeEncodeError'})
ROLES = frozenset({'ancestor', 'config', 'storage', 'private_parent', 'guard_root',
                   'ledger', 'ledger_lock', 'account_lock', 'temporary_ledger', 'unknown'})
# Exact c8 source line spans, validated against its AST before any projection.
# Propagation/wrapper lines are deliberately absent from the public catalog.
POINTS = {
    '_root_fd': {
        (98, 98): ('directory', 'anchor_open'),
        (103, 107): ('directory', 'ancestor_open'),
        (112, 112): ('directory', 'directory_create'),
        (113, 113): ('directory', 'parent_fsync'),
        (116, 120): ('directory', 'created_directory_open'),
        (121, 121): ('directory', 'ancestor_close'),
        (123, 123): ('directory', 'directory_stat'),
        (127, 127): ('directory', 'private_directory_policy'),
        (130, 130): ('directory', 'directory_cleanup'),
    },
    '_check_file': {
        (135, 135): ('file', 'file_stat'),
        (142, 142): ('file', 'private_file_policy'),
    },
    '_open_lock': {
        (147, 147): ('lock', 'lock_open'),
        (150, 152): ('lock', 'lock_create'),
        (157, 157): ('lock', 'lock_race_open'),
        (162, 162): ('lock', 'lock_cleanup'),
    },
    '_try_account_lock': {
        (172, 172): ('lock', 'account_lock_acquire'),
        (174, 174): ('lock', 'account_busy_close'),
        (179, 179): ('lock', 'account_cleanup'),
        (183, 183): ('lock', 'account_cleanup'),
        (189, 189): ('directory', 'account_root_cleanup'),
    },
    '_read': {
        (198, 200): ('ledger', 'ledger_open'),
        (205, 206): ('ledger', 'ledger_size'),
        (207, 207): ('ledger', 'ledger_stream_open'),
        (209, 209): ('ledger', 'ledger_json'),
        (211, 211): ('ledger', 'ledger_schema'),
        (213, 213): ('ledger', 'ledger_version'),
        (215, 215): ('ledger', 'ledger_accounts'),
        (224, 224): ('ledger', 'ledger_entry_schema'),
        (229, 229): ('ledger', 'ledger_counters'),
        (234, 234): ('ledger', 'ledger_pending'),
        (238, 238): ('ledger', 'ledger_read_cleanup'),
    },
    '_unique_object': {(51, 51): ('ledger', 'ledger_duplicate_keys')},
    '_identity': {(43, 43): ('ledger', 'ledger_account_identity')},
    '_write': {
        (242, 247): ('ledger', 'temporary_ledger_create'),
        (250, 250): ('ledger', 'ledger_write_stream_open'),
        (252, 252): ('ledger', 'ledger_serialize'),
        (253, 253): ('ledger', 'ledger_flush'),
        (254, 254): ('ledger', 'ledger_file_fsync'),
        (255, 255): ('ledger', 'ledger_replace'),
        (256, 256): ('ledger', 'ledger_directory_fsync'),
        (259, 259): ('ledger', 'ledger_write_cleanup'),
        (261, 261): ('ledger', 'temporary_ledger_cleanup'),
    },
    '_transaction': {
        (270, 270): ('lock', 'ledger_lock_acquire'),
        (339, 339): ('transaction', 'transaction_cleanup'),
    },
}
STARTS = {'_root_fd': 87, '_check_file': 134, '_open_lock': 144,
          '_try_account_lock': 165, '_read': 196, '_unique_object': 47,
          '_identity': 41, '_write': 240, '_transaction': 265}
WRAPPERS = {'_transaction': (333, 335), '_try_account_lock': (184, 186)}
OPERATIONS = frozenset(value for points in POINTS.values() for value in points.values())
KEYS = frozenset({'operation', 'substage', 'role', 'failure_type', 'errno',
                  'node_kind', 'owner_matches_uid', 'mode_matches', 'single_link'})


def public_observation(value):
    """No permissive string or numeric fallback, including on unknown failures."""
    if type(value) is not dict or set(value) != KEYS:
        return None
    if any(type(value[key]) is not str for key in ('operation', 'substage', 'role', 'failure_type')) \
            or (value['operation'], value['substage']) not in OPERATIONS \
            or value['role'] not in ROLES or value['failure_type'] not in ERROR_TYPES \
            or (value['errno'] is not None and type(value['errno']) is not str) \
            or value['errno'] not in ERRNOS | {None, 'other_errno'} \
            or (value['node_kind'] is not None and type(value['node_kind']) is not str) \
            or value['node_kind'] not in {None, 'directory', 'regular', 'symlink', 'other'}:
        return None
    if any(value[key] is not None and type(value[key]) is not bool
           for key in ('owner_matches_uid', 'mode_matches', 'single_link')):
        return None
    if value['substage'] not in {'private_directory_policy', 'private_file_policy'} \
            and any(value[key] is not None for key in
                    ('node_kind', 'owner_matches_uid', 'mode_matches', 'single_link')):
        return None
    if value['substage'] == 'private_directory_policy' and value['single_link'] is not None:
        return None
    return dict(value)


class SourceBinding:
    """Bind the loaded function identities to the previously checked c8 bytes."""

    def __init__(self, guard, raw):
        if type(raw) is not bytes or hashlib.sha256(raw).hexdigest() != SOURCE_SHA:
            raise ValueError('diagnostic_source_refused')
        tree = ast.parse(raw)
        definitions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                   and node.name == 'RecoveryGuard')
        definitions.update({node.name: node for node in cls.body
                            if isinstance(node, ast.FunctionDef)})
        namespace = type(guard).status.__globals__
        self.storage_error = namespace['RecoveryGuardStorageError']
        self.root = guard.root
        self.codes = {}
        compiled = compile(raw, 'source-bound-diagnostic', 'exec')
        expected = {}
        def collect(code):
            for item in code.co_consts:
                if isinstance(item, types.CodeType):
                    expected[item.co_name] = item
                    collect(item)
        collect(compiled)
        for name, start in STARTS.items():
            function = namespace[name] if name.startswith('_unique') or name == '_identity' \
                else getattr(type(guard), name)
            code_start = start - 1 if name == '_check_file' else start
            if definitions[name].lineno != start or function.__code__.co_firstlineno != code_start \
                    or function.__code__ != expected[name] \
                    or function.__globals__ is not namespace:
                raise ValueError('diagnostic_source_refused')
            self.codes[function.__code__] = name
        self.uid = os.getuid()

    def frames(self, error):
        result, seen = [], set()
        trace = error.__traceback__
        for _ in range(64):
            if trace is None:
                return result
            if id(trace) in seen:
                return None
            seen.add(id(trace))
            name = self.codes.get(trace.tb_frame.f_code)
            if name is not None:
                result.append((name, trace.tb_lineno, trace.tb_frame))
            trace = trace.tb_next
        return None

    def role(self, name, frame, frames):
        if name == '_root_fd':
            current = frame.f_locals.get('current')
            if not isinstance(current, Path):
                return 'unknown'
            if current == self.root:
                return 'guard_root'
            if current == self.root.parent:
                return 'private_parent'
            if current == self.root.parent.parent:
                return 'storage'
            if current == self.root.parent.parent.parent:
                return 'config'
            return 'ancestor' if current in self.root.parents else 'unknown'
        if name in {'_read', '_unique_object', '_identity'}:
            return 'ledger'
        if name == '_write':
            return 'temporary_ledger'
        if name == '_try_account_lock':
            return 'account_lock'
        if name == '_transaction':
            return 'ledger_lock' if frames[-1][1] == 270 else 'unknown'
        if name == '_check_file':
            parents = frames[:-1]
            if not parents:
                return 'unknown'
            name, _, frame = parents[-1]
            if name == '_read':
                return 'ledger'
            if name == '_write':
                return 'temporary_ledger'
        if name == '_open_lock':
            value = frame.f_locals.get('name')
            if value == 'ledger.lock':
                return 'ledger_lock'
            if value == 'account-' + IDENTITY + '.lock':
                return 'account_lock'
        return 'unknown'

    def observe(self, error):
        if type(error) is not self.storage_error:
            return None
        seen = set()
        # Only unwrap exact product conversion sites. A later cleanup error is
        # classified as that error, never replaced by an older handled failure.
        for _ in range(8):
            if id(error) in seen:
                return None
            seen.add(id(error))
            frames = self.frames(error)
            if not frames:
                return None
            name, line, frame = frames[-1]
            wrapper = WRAPPERS.get(name)
            if type(error) is self.storage_error and wrapper is not None \
                    and wrapper[0] <= line <= wrapper[1]:
                error = error.__cause__ if error.__cause__ is not None else error.__context__
                if error is None:
                    return None
                continue
            break
        else:
            return None
        kind = type(error).__name__
        permitted = (type(error) is self.storage_error
                     or type(error) in {OSError, PermissionError, FileNotFoundError,
                         NotADirectoryError, IsADirectoryError, FileExistsError,
                         BlockingIOError, InterruptedError, ValueError, TypeError,
                         KeyError, json.JSONDecodeError, UnicodeDecodeError, UnicodeEncodeError})
        if not permitted or kind not in ERROR_TYPES:
            return None
        point = next((value for (first, last), value in POINTS[name].items()
                      if first <= line <= last), None)
        if point is None:
            return None
        code = None
        if isinstance(error, OSError):
            code = next((label for label in sorted(ERRNOS)
                         if getattr(errno, label, None) == error.errno), 'other_errno')
        value = dict(operation=point[0], substage=point[1],
                     role=self.role(name, frame, frames), failure_type=kind, errno=code,
                     node_kind=None, owner_matches_uid=None, mode_matches=None, single_link=None)
        # Read only the original stat_result at the exact rejecting policy line.
        # An info value from an earlier successful ancestor is never projected.
        if point[1] in {'private_directory_policy', 'private_file_policy'}:
            info = frame.f_locals.get('info')
            if type(info) is os.stat_result:
                value['node_kind'] = ('directory' if stat.S_ISDIR(info.st_mode) else
                    'regular' if stat.S_ISREG(info.st_mode) else
                    'symlink' if stat.S_ISLNK(info.st_mode) else 'other')
                value['owner_matches_uid'] = info.st_uid == self.uid
                value['mode_matches'] = stat.S_IMODE(info.st_mode) == (
                    0o700 if point[1] == 'private_directory_policy' else 0o600)
                if point[1] == 'private_file_policy':
                    value['single_link'] = info.st_nlink == 1
        return public_observation(value)

# END byte-identical reviewed bounded observer

PACKAGE = Path('/data/homeassistant/custom_components/homecircle')
GUARD = Path('/data/homeassistant/.storage/homecircle_findmy/recovery_guard')
MODULE_SHA = 'c8abe90b71c216e14d63b8d7382f377128aa0cce83ce53e553039fee3005ea6a'
IDENTITY = 'a' * 64
EXPORT_PROOF = Path('/data/homeassistant/homecircle-safe-restore-qa-control/external-proof.json')
EXPORT_STAGES = frozenset({'platform', 'arguments', 'diagnostic_token', 'blocked_status',
                          'private_files', 'encode', 'unrecognized_export_stage'})
EXPORT_FAILURE_TYPES = frozenset({'ValueError', 'RuntimeError', 'OSError', 'FileNotFoundError',
    'PermissionError', 'ImportError', 'ModuleNotFoundError', 'AttributeError', 'TypeError',
    'KeyError', 'JSONDecodeError', 'UnicodeDecodeError', 'TimeoutError', 'RecoveryGuardError',
    'RecoveryGuardBlocked', 'RecoveryGuardStorageError', 'unrecognized_failure_type'})
_export_stage = 'platform'
_export_token = None
_export_binding = None
_export_storage_failure = None


def require(ok):
    if not ok:
        raise ValueError('private_guard_transfer_refused')


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


def export_failure_labels(value):
    required = {'stage', 'failure_type'}
    if type(value) is not dict or set(value) not in (required, required | {'storage_failure'}):
        return None
    if type(value['stage']) is not str or value['stage'] not in EXPORT_STAGES \
            or type(value['failure_type']) is not str or value['failure_type'] not in EXPORT_FAILURE_TYPES:
        return None
    result = {key: value[key] for key in ('stage', 'failure_type')}
    if 'storage_failure' in value:
        if value['stage'] != 'blocked_status' or value['failure_type'] != 'RecoveryGuardStorageError':
            return None
        detail = public_observation(value['storage_failure'])
        if detail is None:
            return None
        result['storage_failure'] = detail
    return result


def parse_export_failure(raw, token):
    """Only a small exact schema with this fresh QA token; no raw-text fallback."""
    if type(raw) is not bytes or not 0 < len(raw) <= 2048 \
            or type(token) is not str or re.fullmatch(r'[0-9a-f]{32}', token) is None:
        return None
    try:
        value = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, TypeError, UnicodeDecodeError):
        return None
    required = {'schema', 'kind', 'token', 'stage', 'failure_type'}
    if type(value) is not dict or set(value) not in (required, required | {'storage_failure'}) \
            or type(value['schema']) is not int or value['schema'] != 1 \
            or value['kind'] != 'homecircle_guard_export_failure' or value['token'] != token:
        return None
    return export_failure_labels({key: value[key] for key in value if key in {'stage', 'failure_type', 'storage_failure'}})


def read_export_token():
    """Read only the existing proof already checked by the host before export."""
    descriptor = os.open(EXPORT_PROOF, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 < info.st_size <= 65536)
        raw = stream.read(65537)
    require(len(raw) <= 65536)
    proof = json.loads(raw, object_pairs_hook=unique)
    require(type(proof) is dict and set(proof) == {'schema', 'token', 'generation', 'branch_commit', 'postbackup_window'}
            and type(proof['schema']) is int and proof['schema'] == 1
            and proof['generation'] == 'before_restore' and type(proof['token']) is str
            and re.fullmatch(r'[0-9a-f]{32}', proof['token']) is not None)
    return proof['token']


def decode(raw):
    require(type(raw) is bytes and 0 < len(raw) <= 1024 * 1024)
    value = json.loads(raw, object_pairs_hook=unique)
    require(type(value) is dict and set(value) == {'schema', 'files'}
            and type(value['schema']) is int and value['schema'] == 1)
    files = value['files']
    expected = {'ledger.json', 'ledger.lock', 'account-' + IDENTITY + '.lock'}
    require(type(files) is dict and set(files) == expected)
    result = {}
    for name, encoded in files.items():
        require(type(encoded) is str and len(encoded) <= 700000)
        content = base64.b64decode(encoded, validate=True)
        require(len(content) <= 512 * 1024)
        result[name] = content
    require(result['ledger.lock'] == result['account-' + IDENTITY + '.lock'] == b'')
    return result


def fingerprint(files):
    return sha(canonical({name: {'bytes': len(raw), 'sha256': sha(raw)} for name, raw in files.items()}))


def read_private_bundle(path):
    info=path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.geteuid()
            and stat.S_IMODE(info.st_mode) == 0o600 and 0 < info.st_size <= 1024*1024)
    with path.open('rb') as stream:
        raw=stream.read(1024*1024+1)
    require(len(raw) <= 1024*1024)
    return raw


def private_files(root):
    require(root.is_dir() and not root.is_symlink())
    info = root.stat()
    require(info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o700)
    paths = list(root.iterdir())
    require(0 < len(paths) <= 16)
    files = {}
    for path in paths:
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                and info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o600
                and 0 <= info.st_size <= 512 * 1024
                and re.fullmatch(r'[a-zA-Z0-9_.-]{1,100}', path.name))
        with path.open('rb') as stream:
            files[path.name] = stream.read(512*1024+1)
        require(len(files[path.name]) <= 512*1024)
    decode(canonical({'schema': 1, 'files': {name: base64.b64encode(raw).decode() for name, raw in files.items()}}))
    return files


def actual_guard():
    global _export_binding
    path = PACKAGE / 'findmy_recovery_guard.py'
    require(path.is_file() and not path.is_symlink())
    raw = path.read_bytes()
    require(sha(raw) == MODULE_SHA)
    # Exact standalone product module: no integration/native/provider import.
    spec = importlib.util.spec_from_file_location('owned_exact_recovery_guard', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    guard = module.RecoveryGuard(GUARD)
    _export_binding = None
    if _export_stage == 'blocked_status' and type(_export_token) is str \
            and re.fullmatch(r'[0-9a-f]{32}', _export_token):
        try:
            _export_binding = SourceBinding(guard, raw)
        except Exception:
            _export_binding = None
    return guard


def blocked_status():
    global _export_storage_failure
    try:
        status = asyncio.run(actual_guard().status(IDENTITY))
    except Exception as error:
        if _export_binding is not None:
            try:
                _export_storage_failure = public_observation(_export_binding.observe(error))
            except Exception:
                _export_storage_failure = None
        raise
    require(status['blocked'] is True and status['unresolved'] == status['rejected'] == 3
            and status['pending'] == status['uncertain'] == 0)


def main():
    global _export_stage, _export_token, _export_binding, _export_storage_failure
    _export_stage, _export_token = 'platform', None
    _export_binding, _export_storage_failure = None, None
    require(sys.platform == 'linux' and os.geteuid() == 0)
    _export_stage = 'arguments'
    require(len(sys.argv) in {2, 6})
    action = sys.argv[1]
    if action == 'export':
        require(len(sys.argv) == 2)
        _export_stage = 'diagnostic_token'
        try:
            _export_token = read_export_token()
        except Exception:
            _export_token = None
        _export_stage = 'blocked_status'
        blocked_status()
        _export_stage = 'private_files'
        files = private_files(GUARD)
        _export_stage = 'encode'
        print(canonical({'schema': 1, 'files': {name: base64.b64encode(raw).decode() for name, raw in files.items()}}).decode())
        return
    require(action == 'import' and len(sys.argv) == 6)
    path = Path(sys.argv[2])
    require(path == Path('/data/homeassistant/homecircle-safe-restore-qa-control/.newest-guard-private.json')
            and path.is_file() and not path.is_symlink() and path.stat().st_nlink == 1
            and stat.S_IMODE(path.stat().st_mode) == 0o600 and path.stat().st_uid == os.geteuid()
            and 0 < path.lstat().st_size <= 1024*1024)
    expected_raw, expected_old, expected_new = sys.argv[3:]
    require(all(re.fullmatch(r'[0-9a-f]{64}', value) for value in (expected_raw, expected_old, expected_new))
            and expected_old != expected_new)
    raw=read_private_bundle(path)
    require(sha(raw) == expected_raw)
    files = decode(raw)
    require(fingerprint(files) == expected_new and fingerprint(private_files(GUARD)) == expected_old)
    guard = actual_guard()
    root = guard._root_fd()  # Product's ancestor/mode/ownership checks, without reset.
    try:
        for name in private_files(GUARD):
            os.unlink(name, dir_fd=root)
        for name, content in files.items():
            descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=root)
            with os.fdopen(descriptor, 'wb') as output:
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
        os.fsync(root)
    finally:
        os.close(root)
    require(fingerprint(private_files(GUARD)) == expected_new)
    blocked_status()
    require(fingerprint(private_files(GUARD)) == expected_new)
    path.unlink()
    print(json.dumps({'schema': 1, 'outcome': 'passed', 'newest_guard_sha256': expected_new,
                      'blocked_api_status_checked': True, 'private_guest_transfer_removed': True}, sort_keys=True))


def cli():
    try:
        main()
    except Exception as error:
        if len(sys.argv) > 1 and sys.argv[1] == 'export':
            if type(_export_token) is str and re.fullmatch(r'[0-9a-f]{32}', _export_token):
                stage = _export_stage if type(_export_stage) is str and _export_stage in EXPORT_STAGES else 'unrecognized_export_stage'
                kind = type(error).__name__
                kind = kind if kind in EXPORT_FAILURE_TYPES else 'unrecognized_failure_type'
                labels = {'stage': stage, 'failure_type': kind}
                if stage == 'blocked_status' and kind == 'RecoveryGuardStorageError':
                    try:
                        detail = public_observation(_export_storage_failure)
                    except Exception:
                        detail = None
                    if detail is not None:
                        labels['storage_failure'] = detail
                print(json.dumps({'schema': 1, 'kind': 'homecircle_guard_export_failure', 'token': _export_token,
                                  **labels}, sort_keys=True), file=sys.stderr)
            raise SystemExit(1) from None
        raise


if __name__ == '__main__':
    cli()
