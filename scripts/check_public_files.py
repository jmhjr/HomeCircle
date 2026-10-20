#!/usr/bin/env python3
"""Conservative content guard. Reports paths/rules only, never matching values."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CLT_GIT = Path('/Library/Developer/CommandLineTools/usr/bin/git')
GIT = os.environ.get('HOMECIRCLE_GIT') or (str(CLT_GIT) if sys.platform == 'darwin' and CLT_GIT.exists() else 'git')

def git(*args):
    return subprocess.check_output([GIT, *args], cwd=ROOT)

RULES = [
    ('Google key', re.compile(r'AIza[0-9A-Za-z_-]{30,}')),
    ('private key', re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
    ('JWT token', re.compile(r'eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}')),
    ('numeric coordinate field', re.compile(r'''(?im)["']?\b(?:latitude|longitude|lat|lng)\b["']?\s*[:=]\s*["']?-?\d+(?:\.\d+)?''')),
    ('street address', re.compile(r'(?i)\b\d{1,6}\s+(?:[A-Za-z]+\s+){1,4}(?:Street|St|Road|Rd|Lane|Ln|Drive|Dr|Avenue|Ave|Court|Ct|Boulevard|Blvd)\b')),
    ('private network address', re.compile(r'\b(?:192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b')),
    ('credential assignment', re.compile(r'''(?im)["']?\b(?:api_key|access_token|refresh_token|password|subscription_key)\b["']?\s*[:=]\s*["']?[A-Za-z0-9_+/=-]{16,}''')),
]
ENTITIES = re.compile(r'\b(?:person|device_tracker|zone|sensor|button)\.[a-z][a-z0-9_]*')
BLOCKED_EXT = {'.png', '.jpg', '.jpeg', '.webp', '.heic', '.zip', '.gz', '.tar', '.db', '.key', '.pem', '.mp4'}

REVIEWED_BINARY_FILES = {
    # Public Apple escrow root certificates from the pinned MIT FindMy SDK.
    'custom_components/homecircle/_vendor_findmy/keychain/roots/101.crt':
        '5644c142208dd4bf7ad770902f70d6730b8571164fd874d9ae5168807b32f766',
    'custom_components/homecircle/_vendor_findmy/keychain/roots/102.crt':
        'd4eaa88170b8aee18fceff68698310d4c2ab4ceb48179d99206a53ac73e8a4eb',
    'custom_components/homecircle/_vendor_findmy/keychain/roots/103.crt':
        'fdba6f3365d617b9eb799d2f48851b1a85c62cf366c36797e539b3c4c2c3bdc6',
    'custom_components/homecircle/_vendor_findmy/keychain/roots/500.crt':
        '654bfb656d80a715559034c7fe08e637b335e770c84ec05cd90475e8bbc59eb0',
    # Original geometric icon, rendered by build_brand.py and visually reviewed.
    'custom_components/homecircle/brand/icon.png':
        'bf85530d7362dbfbe796c1f1b944483ccdc8c0693d0c39411b1156b1860d28a5',
}

REVIEWED_LICENSE_FILES = {
    # Complete pinned public notices, including the GNU license's FSF address.
    # Any byte or path change still requires a new explicit privacy review.
    'custom_components/homecircle/_findmy_runtime/LICENSE.md':
        'd0d08d053daacc07d9357fbdae0fefb972eec9ae6a14cada17695d6f5c1f28e4',
}

def violations(name, data):
    if name in REVIEWED_BINARY_FILES:
        return [] if hashlib.sha256(data).hexdigest() == REVIEWED_BINARY_FILES[name] else ['reviewed asset changed; review required']
    if name in REVIEWED_LICENSE_FILES:
        return [] if hashlib.sha256(data).hexdigest() == REVIEWED_LICENSE_FILES[name] else ['reviewed notice changed; review required']
    issues = []
    if any(part in {'.private', 'private', '.storage', 'node_modules'} for part in Path(name).parts):
        issues.append('private/runtime path')
    if Path(name).suffix.lower() in BLOCKED_EXT:
        issues.append('unreviewed media/archive/secret artifact')
    try:
        content = data.decode('utf-8')
    except UnicodeDecodeError:
        return issues + ['unreviewed binary file']
    if '\0' in content:
        issues.append('binary content')
    for label, pattern in RULES:
        if pattern.search(content):
            issues.append(label)
    for entity in ENTITIES.findall(content):
        domain, value = entity.split('.', 1)
        if entity != 'zone.home' and not value.startswith('example_'):
            # Technical filenames can look like entity IDs; only these are approved.
            if entity not in {'zone.attributes', 'zone.entity_id', 'zone.target_zone'}:
                issues.append('non-example entity identifier')
                break
    return issues

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--staged', action='store_true')
    group.add_argument('--all', action='store_true')
    args = parser.parse_args()
    if args.staged:
        names = git('diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z').decode().split('\0')
    else:
        names = git('ls-files', '--cached', '--others', '--exclude-standard', '-z').decode().split('\0')
    failed = False
    count = 0
    for name in sorted(set(filter(None, names))):
        path = ROOT / name
        if not args.staged and not path.exists():
            continue
        if path.is_symlink():
            found = ['symlink requires review']
        else:
            data = git('show', ':' + name) if args.staged else path.read_bytes()
            found = violations(name, data)
        count += 1
        if found:
            failed = True
            print(name + ': ' + ', '.join(found), file=sys.stderr)
    print(f'Privacy guard checked {count} files; ' + ('review required.' if failed else 'no flagged patterns. Manual review still required.'))
    return int(failed)

if __name__ == '__main__':
    sys.exit(main())
