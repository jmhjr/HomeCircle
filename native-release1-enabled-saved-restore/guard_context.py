"""Owned offline Core-image context for unchanged synthetic guard transfers."""
import json
import math
from pathlib import Path
import re
import shlex
import sys
import time


IMAGE = 'sha256:45f009d6ff1061971102e81f0802cf2762bdd5c5007231c938bd36030cbd0a12'
CONFIG = '/mnt/data/supervisor/homeassistant'
SOURCE = '/mnt/data/homecircle-safe-restore-qa/guard-transfer.py'
TRANSFER = '/data/homeassistant/homecircle-safe-restore-qa-control/.newest-guard-private.json'
LABEL = 'org.homecircle.restore-guard-context'
CORE_FORMAT = '{"id":{{json .Id}},"image":{{json .Image}},"running":{{json .State.Running}},"started":{{json .State.StartedAt}},"restarts":{{json .RestartCount}}}'
IMAGE_FORMAT = '{"id":{{json .Id}},"arch":{{json .Architecture}},"os":{{json .Os}},"version":{{json (index .Config.Labels "io.hass.version")}}}'
OWN_FORMAT = '{"id":{{json .Id}},"name":{{json .Name}},"image":{{json .Image}},"running":{{json .State.Running}},"label":{{json (index .Config.Labels "org.homecircle.restore-guard-context")}},"network":{{json .HostConfig.NetworkMode}},"readonly":{{json .HostConfig.ReadonlyRootfs}},"caps":{{json .HostConfig.CapDrop}},"added_caps":{{json .HostConfig.CapAdd}},"security":{{json .HostConfig.SecurityOpt}},"privileged":{{json .HostConfig.Privileged}},"mounts":{{json .Mounts}},"ports":{{json .HostConfig.PortBindings}},"user":{{json .Config.User}},"entrypoint":{{json .Config.Entrypoint}},"command":{{json .Config.Cmd}}}'


class Refused(RuntimeError):
    pass


def check(value):
    if not value:
        raise Refused('guard_context_refused')


def digest_value(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def public_success(action):
    return {'schema': 1, 'action': action, 'outcome': 'passed', 'image': IMAGE,
            'managed_core_same_stopped_process': True, 'local_image_verified': True,
            'owned_identity_security_mount_checked': True, 'offline_network_none': True,
            'unchanged_transfer_stdin': True, 'owned_container_removed': True,
            'maximum_total_seconds': 60}


def accept_contexts(values):
    check(type(values) is list and len(values) == 2)
    for value, action in zip(values, ('export', 'import')):
        check(type(value) is dict and json.dumps(value, sort_keys=True) == json.dumps(public_success(action), sort_keys=True))


class Context:
    def __init__(self, guest, nonce, action, arguments=(), clock=time.monotonic, maximum_seconds=60):
        check(type(nonce) is str and re.fullmatch('[0-9a-f]{32}', nonce) is not None
              and action in ('export', 'import') and type(arguments) is tuple)
        check((action == 'export' and arguments == ()) or
              (action == 'import' and len(arguments) == 4 and arguments[0] == TRANSFER
               and all(digest_value(value) for value in arguments[1:])
               and arguments[2] != arguments[3]))
        check(type(maximum_seconds) in (int, float) and 0 < maximum_seconds <= 60)
        self.guest, self.nonce, self.action, self.arguments, self.clock = guest, nonce, action, arguments, clock
        self.name = 'homecircle-restore-guard-' + action + '-' + nonce
        self.deadline = clock() + maximum_seconds
        self.calls = 0
        self.requested = False
        self.cid = None
        self.record = {'schema': 1, 'action': action, 'outcome': 'failed_or_incomplete',
                       'image': IMAGE, 'maximum_total_seconds': 60}

    def call(self, argv, *, reserve=20, maximum=6, source=False, capture=False):
        seconds = min(maximum, self.deadline - self.clock() - reserve)
        timeout = math.floor(seconds) - 1
        check(timeout >= 1 and self.calls < 18)
        command = shlex.join(['/usr/bin/timeout', '-s', 'KILL', str(timeout), *argv])
        if source:
            check(argv == ['/usr/bin/docker', 'start', '--attach', '--interactive', self.cid])
            command += ' < ' + shlex.quote(SOURCE)
        self.calls += 1
        returned_by = self.clock() + seconds
        result = self.guest(command, seconds, capture=True)
        check(self.clock() <= returned_by and self.clock() <= self.deadline)
        check(type(result) is dict and set(result) == {'exitcode', 'signal', 'stdout', 'stderr', 'truncated'}
              and type(result['stdout']) is bytes and len(result['stdout']) <= 1024 * 1024
              and type(result['stderr']) is bytes and len(result['stderr']) <= 2048
              and type(result['truncated']) is bool
              and (not result['truncated'] or result['stdout'] == result['stderr'] == b''))
        normal = (type(result['exitcode']) is int and 0 <= result['exitcode'] <= 255
                  and (result['signal'] is None or type(result['signal']) is int and result['signal'] == 0))
        signalled = (result['exitcode'] is None and type(result['signal']) is int
                     and 1 <= result['signal'] <= 64)
        check(normal or signalled)
        if capture:
            return result
        check(normal and result['exitcode'] == 0 and result['stderr'] == b'' and not result['truncated'])
        return result['stdout']

    def core(self, reserve=20):
        value = json.loads(self.call(['/usr/bin/docker', 'inspect', '--type', 'container', 'homeassistant',
                                     '--format', CORE_FORMAT], reserve=reserve))
        check(type(value) is dict and set(value) == {'id', 'image', 'running', 'started', 'restarts'}
              and digest_value(value['id']) and value['image'] == IMAGE and value['running'] is False
              and type(value['started']) is str and 0 < len(value['started']) <= 40
              and type(value['restarts']) is int and value['restarts'] >= 0)
        return value

    def names(self):
        raw = self.call(['/usr/bin/docker', 'container', 'ls', '--all', '--no-trunc', '--filter',
                         'name=^/' + self.name + '$', '--format', '{{.ID}}'], reserve=0, maximum=4)
        values = raw.decode().splitlines()
        check(len(values) <= 1 and all(digest_value(value) for value in values))
        return values

    def owned(self, reserve=20):
        value = json.loads(self.call(['/usr/bin/docker', 'inspect', '--type', 'container', self.name,
                                     '--format', OWN_FORMAT], reserve=reserve))
        check(type(value) is dict and set(value) == {'id', 'name', 'image', 'running', 'label', 'network',
              'readonly', 'caps', 'added_caps', 'security', 'privileged', 'mounts', 'ports', 'user', 'entrypoint', 'command'}
              and digest_value(value['id']) and (self.cid is None or value['id'] == self.cid)
              and value['name'] == '/' + self.name and value['image'] == IMAGE and value['label'] == self.nonce
              and value['network'] == 'none' and value['readonly'] is True and value['caps'] == ['ALL']
              and value['added_caps'] in (None, []) and value['security'] == ['no-new-privileges']
              and value['privileged'] is False and value['ports'] in (None, {}) and value['user'] == '0:0'
              and value['entrypoint'] == ['python3'] and value['command'] == ['-B', '-', self.action, *self.arguments]
              and type(value['running']) is bool)
        mounts = value['mounts']
        check(type(mounts) is list and len(mounts) == 1 and type(mounts[0]) is dict
              and mounts[0].get('Type') == 'bind' and mounts[0].get('Source') == CONFIG
              and mounts[0].get('Destination') == '/data/homeassistant' and mounts[0].get('RW') is True)
        return value

    def run(self):
        before = after = None
        result = None
        cleaned = False
        try:
            before = self.core()
            image = json.loads(self.call(['/usr/bin/docker', 'image', 'inspect', IMAGE, '--format', IMAGE_FORMAT]))
            check(image == {'id': IMAGE, 'arch': 'amd64', 'os': 'linux', 'version': '2026.10.2'})
            check(self.names() == [])
            self.requested = True
            raw = self.call(['/usr/bin/docker', 'create', '--pull=never', '--name', self.name,
                '--label', LABEL + '=' + self.nonce, '--network=none', '--cap-drop=ALL',
                '--security-opt=no-new-privileges', '--read-only', '--user=0:0', '--mount',
                'type=bind,src=' + CONFIG + ',dst=/data/homeassistant', '-i', '--entrypoint=python3',
                IMAGE, '-B', '-', self.action, *self.arguments])
            identifier = raw.decode().strip()
            check(digest_value(identifier))
            self.cid = identifier
            check(self.owned()['running'] is False)
            result = self.call(['/usr/bin/docker', 'start', '--attach', '--interactive', self.cid],
                               source=True, capture=True, maximum=25)
            check(self.owned()['running'] is False)
        finally:
            try:
                if self.requested:
                    values = self.names()
                    if values:
                        owned = self.owned(reserve=0)
                        check(values == [owned['id']])
                        try:
                            raw = self.call(['/usr/bin/docker', 'rm', '--force', '--volumes', owned['id']],
                                            reserve=0, maximum=4)
                        except Exception:
                            # No second mutation: the exact-name absence below
                            # resolves only a lost acknowledgement, never ownership.
                            pass
                        else:
                            check(raw.decode().strip() == owned['id'])
                    check(self.names() == [])
                cleaned = True
            finally:
                if before is not None:
                    after = self.core(reserve=0)
                self.record.update(managed_core_same_stopped_process=before is not None and before == after,
                                   owned_container_removed=cleaned)
        check(before == after and before is not None and cleaned and result is not None
              and self.clock() <= self.deadline)
        if result['exitcode'] == 0 and result['stderr'] == b'' and result['truncated'] is False:
            self.record = public_success(self.action)
        return result


if __name__ == '__main__':
    check(len(sys.argv) == 3 and sys.argv[1] == '--accept-public')
    path = Path(sys.argv[2])
    check(path.name == 'host.json' and path.is_file() and not path.is_symlink()
          and path.stat().st_size <= 256 * 1024)
    accept_contexts(json.loads(path.read_bytes()).get('guard_transfer_contexts'))
    print('Both bounded offline Core-image guard contexts passed.')
