"""Private owned-guest guard transfer. Raw bundle is never a public receipt."""
import asyncio
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys

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
    if type(value) is not dict or set(value) != {'stage', 'failure_type'}:
        return None
    if type(value['stage']) is not str or value['stage'] not in EXPORT_STAGES \
            or type(value['failure_type']) is not str or value['failure_type'] not in EXPORT_FAILURE_TYPES:
        return None
    return {key: value[key] for key in ('stage', 'failure_type')}


def parse_export_failure(raw, token):
    """Only a small exact schema with this fresh QA token; no raw-text fallback."""
    if type(raw) is not bytes or not 0 < len(raw) <= 2048 \
            or type(token) is not str or re.fullmatch(r'[0-9a-f]{32}', token) is None:
        return None
    try:
        value = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, TypeError, UnicodeDecodeError):
        return None
    if type(value) is not dict or set(value) != {'schema', 'kind', 'token', 'stage', 'failure_type'} \
            or type(value['schema']) is not int or value['schema'] != 1 \
            or value['kind'] != 'homecircle_guard_export_failure' or value['token'] != token:
        return None
    return export_failure_labels({key: value[key] for key in ('stage', 'failure_type')})


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
    path = PACKAGE / 'findmy_recovery_guard.py'
    require(path.is_file() and not path.is_symlink() and sha(path.read_bytes()) == MODULE_SHA)
    # Exact standalone product module: no integration/native/provider import.
    spec = importlib.util.spec_from_file_location('owned_exact_recovery_guard', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.RecoveryGuard(GUARD)


def blocked_status():
    status = asyncio.run(actual_guard().status(IDENTITY))
    require(status['blocked'] is True and status['unresolved'] == status['rejected'] == 3
            and status['pending'] == status['uncertain'] == 0)


def main():
    global _export_stage, _export_token
    _export_stage, _export_token = 'platform', None
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
                print(json.dumps({'schema': 1, 'kind': 'homecircle_guard_export_failure', 'token': _export_token,
                                  'stage': stage, 'failure_type': kind}, sort_keys=True), file=sys.stderr)
            raise SystemExit(1) from None
        raise


if __name__ == '__main__':
    cli()
