"""Offline context/state/cleanup contracts; no Docker, guest or native calls."""
import copy
import importlib.util
import json
from pathlib import Path
import shlex
import unittest


ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prepared_storage_context', ROOT / 'storage_context.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
NONCE = '1' * 32
TOKEN = '2' * 32
BRANCH = '3' * 40
CID = 'a' * 64


def response(value=b'', exitcode=0, stderr=b'', truncated=False, signal=None):
    return {'stdout': json.dumps(value).encode() if type(value) is not bytes else value,
            'exitcode': exitcode, 'stderr': stderr, 'truncated': truncated, 'signal': signal}


class FakeGuest:
    def __init__(self, action='seed', arguments=(TOKEN, 'before_restore', BRANCH)):
        self.calls = []
        self.created = False
        self.name = 'homecircle-saved-storage-' + action + '-' + NONCE
        self.core = {'id': 'b' * 64, 'image': g.IMAGE, 'running': False,
                     'started': '2026-10-21T00:00:00Z', 'restarts': 0}
        self.image = {'id': g.IMAGE, 'arch': 'amd64', 'os': 'linux', 'version': '2026.10.2'}
        self.owned = {'id': CID, 'name': '/' + self.name, 'image': g.IMAGE, 'running': False,
                      'label': NONCE, 'network': 'none', 'readonly': True, 'caps': ['ALL'],
                      'added_caps': None, 'security': ['no-new-privileges'], 'privileged': False,
                      'mounts': [{'Type': 'bind', 'Source': g.CONFIG,
                                  'Destination': '/data/homeassistant', 'RW': True}],
                      'ports': {}, 'user': '0:0', 'entrypoint': ['python3'],
                      'command': ['-B', '-', action, *arguments]}
        self.native = response(b'synthetic-private-bundle')
        self.create_failure = False
        self.create_reply = (CID + '\n').encode()
        self.remove_failure = False
        self.lost_remove = False
        self.remove_ack_failed = False
        self.core_reads = 0
        self.core_change = False

    def __call__(self, command, timeout, capture):
        self.calls.append((command, timeout, capture))
        assert 1 < timeout <= 60 and capture is True
        parts = shlex.split(command)
        assert parts[:3] == ['/usr/bin/timeout', '-s', 'KILL']
        assert int(parts[3]) < timeout
        argv = parts[4:]
        if '<' in argv:
            index = argv.index('<')
            assert argv[index:] == ['<', g.SOURCE]
            argv = argv[:index]
        assert argv[0] == '/usr/bin/docker'
        if argv[1:4] == ['inspect', '--type', 'container']:
            if argv[4] == 'homeassistant':
                self.core_reads += 1
                value = copy.deepcopy(self.core)
                if self.core_change and self.core_reads > 1:
                    value['started'] = '2026-10-21T01:00:00Z'
                return response(value)
            assert self.created and argv[4] == self.name
            return response(self.owned)
        if argv[1:3] == ['image', 'inspect']:
            return response(self.image)
        if argv[1:3] == ['container', 'ls']:
            return response((CID + '\n').encode() if self.created else b'')
        if argv[1] == 'create':
            self.created = True
            return response(b'', exitcode=1, stderr=b'private-canary') if self.create_failure else response(self.create_reply)
        if argv[1] == 'start':
            assert self.created
            return self.native
        if argv[1] == 'rm':
            assert self.created and argv[-1] == CID
            if self.remove_failure:
                return response(b'', exitcode=1, stderr=b'private-canary')
            if not self.lost_remove:
                self.created = False
            if self.remove_ack_failed:
                return response(b'', exitcode=1, stderr=b'private-canary')
            return response((CID + '\n').encode())
        raise AssertionError('unreviewed command')


class Contracts(unittest.TestCase):
    def run_context(self, guest=None, action='seed', arguments=(TOKEN, 'before_restore', BRANCH)):
        guest = guest or FakeGuest(action, arguments)
        context = g.Context(guest, NONCE, action, arguments, clock=lambda: 0)
        return guest, context

    def test_seed_uses_exact_offline_image_context_and_preserves_raw_result(self):
        guest, context = self.run_context()
        self.assertEqual(context.run(), guest.native)
        self.assertEqual(context.record, g.public_success('seed'))
        creates = [shlex.split(command)[4:] for command, _, _ in guest.calls
                   if ' create ' in command]
        self.assertEqual(len(creates), 1)
        self.assertEqual(creates[0], ['/usr/bin/docker', 'create', '--pull=never', '--name', guest.name,
            '--label', g.LABEL + '=' + NONCE, '--network=none', '--cap-drop=ALL',
            '--security-opt=no-new-privileges', '--read-only', '--user=0:0', '--mount',
            'type=bind,src=' + g.CONFIG + ',dst=/data/homeassistant', '-i', '--entrypoint=python3',
            g.IMAGE, '-B', '-', 'seed', TOKEN, 'before_restore', BRANCH])
        self.assertFalse(guest.created)

    def test_all_four_actions_bind_token_generation_branch_and_stdin(self):
        for action in ('seed', 'mutate', 'validate_restored', 'validate_restart'):
            args = (TOKEN, 'before_restore' if action in ('seed', 'mutate') else 'after_restore', BRANCH)
            guest, context = self.run_context(action=action, arguments=args)
            self.assertEqual(context.run(), guest.native)
            self.assertEqual(context.record, g.public_success(action))
            self.assertEqual(guest.owned['command'], ['-B', '-', action, *args])
            self.assertTrue(any('< '+g.SOURCE in command for command, _, _ in guest.calls))

    def test_running_core_refuses_before_any_create(self):
        guest, context = self.run_context(); guest.core['running'] = True
        with self.assertRaises(g.Refused): context.run()
        self.assertFalse(any(' create ' in command for command, _, _ in guest.calls))

    def test_wrong_local_image_arch_or_managed_digest_refuses(self):
        for target, key, value in [('image', 'arch', 'arm64'), ('image', 'version', '2026.9.4'),
                                   ('core', 'image', 'sha256:' + '0' * 64)]:
            guest, context = self.run_context(); getattr(guest, target)[key] = value
            with self.assertRaises(g.Refused): context.run()
            self.assertFalse(guest.created)

    def test_unknown_security_or_mount_never_starts_or_removes_an_unverified_object(self):
        for key, value in [('security', ['apparmor=unconfined']), ('network', 'host'),
                           ('caps', []), ('mounts', []), ('label', 'foreign')]:
            guest, context = self.run_context(); guest.owned[key] = value
            with self.assertRaises(g.Refused): context.run()
            self.assertFalse(any(' start ' in command or ' rm ' in command for command, _, _ in guest.calls))
            self.assertIs(context.record.get('owned_container_removed'), False)

    def test_nonzero_native_result_is_returned_for_existing_safe_diagnostic_and_cleaned(self):
        guest, context = self.run_context()
        guest.native = response(b'', exitcode=1, stderr=b'private-canary')
        self.assertEqual(context.run(), guest.native)
        self.assertIs(context.record['owned_container_removed'], True)
        self.assertEqual(context.record['outcome'], 'failed_or_incomplete')
        self.assertNotIn('private-canary', json.dumps(context.record))

    def test_oversize_or_wrong_type_refuses_and_truncated_signal_capture_stays_failed(self):
        for native in [response(b'x' * (1024**2 + 1)),
                       response(b'', signal=False), response(b'', exitcode=True)]:
            guest, context = self.run_context(); guest.native = native
            with self.assertRaises(g.Refused): context.run()
            self.assertFalse(guest.created)
        for native in [response(b'', truncated=True), response(b'', exitcode=None, signal=9)]:
            guest, context = self.run_context(); guest.native = native
            self.assertEqual(context.run(), native)
            self.assertEqual(context.record['outcome'], 'failed_or_incomplete')
            self.assertFalse(guest.created)

    def test_lost_create_response_resolves_only_exact_owned_object_for_cleanup(self):
        for lost in (True, False):
            guest, context = self.run_context(); guest.create_failure = lost
            guest.create_reply = b'malformed-private-canary'
            with self.assertRaises(g.Refused): context.run()
            self.assertFalse(guest.created)
            self.assertIs(context.record['owned_container_removed'], True)
        guest, context = self.run_context(); guest.create_reply = ('f' * 64).encode()
        with self.assertRaises(g.Refused): context.run()
        self.assertTrue(guest.created)
        self.assertIs(context.record['owned_container_removed'], False)

    def test_remove_failure_or_false_success_cannot_claim_cleanup(self):
        for field in ('remove_failure', 'lost_remove'):
            guest, context = self.run_context(); setattr(guest, field, True)
            with self.assertRaises(g.Refused): context.run()
            self.assertIs(context.record['owned_container_removed'], False)
        guest, context = self.run_context(); guest.remove_ack_failed = True
        context.run()
        self.assertEqual(context.record, g.public_success('seed'))
        self.assertEqual(sum(' rm ' in command for command, _, _ in guest.calls), 1)

    def test_core_restart_during_transfer_invalidates_success(self):
        guest, context = self.run_context(); guest.core_change = True
        with self.assertRaises(g.Refused): context.run()
        self.assertFalse(context.record['managed_core_same_stopped_process'])

    def test_deadline_and_call_cap_refuse_without_mutating(self):
        guest, context = self.run_context(); context.calls = 18
        with self.assertRaises(g.Refused): context.run()
        self.assertEqual(guest.calls, [])
        now = [0]
        model = FakeGuest()
        def delayed(command, timeout, capture):
            value = model(command, timeout, capture)
            if model.core_reads == 2:
                now[0] = 61
            return value
        context = g.Context(delayed, NONCE, 'seed', (TOKEN, 'before_restore', BRANCH), clock=lambda: now[0])
        with self.assertRaises(g.Refused): context.run()
        self.assertNotEqual(context.record['outcome'], 'passed')
        guest, context = self.run_context(); context.deadline = 1
        with self.assertRaises(g.Refused): context.run()
        self.assertEqual(guest.calls, [])

    def test_wrong_action_generation_nonce_branch_or_argument_count_refuses(self):
        for nonce, action, args in [('private-canary', 'seed', (TOKEN, 'before_restore', BRANCH)),
            (NONCE, 'export', (TOKEN, 'before_restore', BRANCH)),
            (NONCE, 'seed', (TOKEN, 'after_restore', BRANCH)),
            (NONCE, 'validate_restored', (TOKEN, 'before_restore', BRANCH)),
            (NONCE, 'seed', (TOKEN, 'before_restore', 'private-canary')),
            (NONCE, 'seed', (TOKEN, 'before_restore')),
            (NONCE, 'seed', (TOKEN, 'before_restore', BRANCH, 'private-canary'))]:
            with self.subTest(action=action, args=args), self.assertRaises(g.Refused):
                g.Context(FakeGuest(), nonce, action, args)

    def test_strict_public_gate_requires_four_exact_ordered_success_records(self):
        good = [g.public_success(action) for action in ('seed','mutate','validate_restored','validate_restart')]
        g.accept_contexts(good)
        for bad in [good[:3], good[::-1], [dict(good[0], owned_container_removed=False), *good[1:]],
                    [dict(good[0], private_canary='private-canary'), *good[1:]], [*good,good[0]]]:
            with self.assertRaises(g.Refused):g.accept_contexts(bad)

    def test_storage_context_never_accepts_extra_mount_caps_or_rootfs_writes(self):
        for key,value in [('added_caps',['DAC_OVERRIDE']),('ports',{'80/tcp':[{'HostPort':'1'}]}),
                          ('readonly',False),('user','1000:1000'),('privileged',True),
                          ('entrypoint',['sh']),('command',['-B','-','seed'])]:
            guest,context=self.run_context();guest.owned[key]=value
            with self.subTest(key=key), self.assertRaises(g.Refused):context.run()
            self.assertFalse(any(' start ' in command for command,_,_ in guest.calls))


if __name__ == '__main__':
    unittest.main()
