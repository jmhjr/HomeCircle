"""Bounded reset of only a controller-proven fresh owned guest's blank Core data."""
from pathlib import Path
import json
import os
import re
import stat
import sys

CONFIG = Path('/data/homeassistant')


def require(ok, label):
    if not ok:
        raise ValueError(label)


def inspect_blank(root):
    require(root == CONFIG and root.is_dir() and not root.is_symlink()
            and root.resolve() == root and root.stat().st_uid == os.geteuid(), 'fresh_config_root_refused')
    count = total = 0
    for path in root.rglob('*'):
        info = path.lstat()
        require(not path.is_symlink() and info.st_uid == os.geteuid()
                and (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)),
                'fresh_config_member_type_refused')
        if path.is_file():
            count += 1
            total += info.st_size
            require(info.st_nlink == 1 and info.st_size <= 32 * 1024**2
                    and count <= 8192 and total <= 64 * 1024**2, 'fresh_config_bounds_refused')
    require(not (root / 'custom_components/homecircle').exists(), 'fresh_config_candidate_present')
    entries = root / '.storage/core.config_entries'
    if entries.exists():
        values = json.loads(entries.read_bytes())['data']['entries']
        require(isinstance(values, list) and all(isinstance(item, dict) for item in values), 'fresh_entry_schema_refused')
        require(all(item.get('source') != 'user' and item.get('domain') not in
                    {'homecircle', 'homecircle_findmy', 'life360', 'icloud'} for item in values), 'fresh_user_entry_refused')
    auth = root / '.storage/auth'
    if auth.exists():
        users = json.loads(auth.read_bytes())['data']['users']
        require(isinstance(users, list) and all(isinstance(user, dict)
                and user.get('is_owner') is not True and user.get('system_generated') is True for user in users),
                'fresh_owner_account_refused')
    credentials = root / '.storage/auth_provider.homeassistant'
    if credentials.exists():
        require(json.loads(credentials.read_bytes())['data']['users'] == [], 'fresh_owner_credentials_refused')
    children = list(root.iterdir())
    require(len(children) <= 128, 'fresh_config_children_refused')
    return {'files': count, 'bytes': total, 'children': len(children), 'owner_accounts_found': False,
            'candidate_previously_present': False}


def reset(root, retained, nonce):
    require(isinstance(nonce, str) and re.fullmatch(r'[0-9a-f]{32}', nonce), 'owned_instance_nonce_refused')
    require(retained == Path('/data') / ('homecircle-minimum-owned-' + nonce)
            and not retained.exists() and not retained.is_symlink(), 'fresh_retained_path_refused')
    result = inspect_blank(root)
    retained.mkdir(mode=0o700)
    for path in list(root.iterdir()):
        os.replace(path, retained / path.name)
    require(not list(root.iterdir()), 'fresh_config_not_empty')
    config = {'homeassistant': {'name': 'Disposable Minimum Core Base', 'latitude': 0.0,
              'longitude': 0.0, 'elevation': 0, 'unit_system': 'metric', 'time_zone': 'UTC'},
              'http': {}, 'frontend': {}, 'websocket_api': {}, 'hassio': {}}
    path = root / 'configuration.yaml'
    path.write_text(json.dumps(config))
    path.chmod(0o600)
    result.update(fresh_config_reset=True, mount_directory_preserved=True)
    return result


def main():
    require(sys.platform == 'linux' and os.uname().machine == 'x86_64' and os.geteuid() == 0,
            'owned_linux_supervisor_required')
    require(len(sys.argv) == 2, 'owned_instance_nonce_required')
    nonce = sys.argv[1]
    result = reset(CONFIG, Path('/data') / ('homecircle-minimum-owned-' + nonce), nonce)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
