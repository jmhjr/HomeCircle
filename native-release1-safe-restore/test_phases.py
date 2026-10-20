"""Adapted proven backup/phase negative contracts, never native runtime imports."""
import base64
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock,patch
import controller
from test_inherited import dependencies
class ReusedPhaseContracts(unittest.TestCase):

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.host = controller.Controller(SimpleNamespace(branch_commit='a' * 40))
        self.host.public = Path(self.temporary.name)
        self.host.config_path = '/mnt/data/supervisor/homeassistant'
        self.host.guest_write = Mock()
        self.host.guest = Mock(return_value=b'')
        self.inventory = {'__init__.py': {'bytes': 7, 'sha256': controller.sha(b'example')}}
        self.inventory['frontend/homecircle-card.js'] = {'bytes':2,'sha256':'8'*64}
        self.host.inventories = {'candidate': self.inventory}
        self.receipt = {'schema': 1, 'token': self.host.phase_token, 'generation': self.host.generation, 'branch_commit': 'a' * 40, 'core_version': controller.CORE, 'candidate_archive_sha256': controller.CANDIDATE_SHA, 'phase': 'initialize', 'outcome': 'passed', 'owner_accounts_used': False, 'production_configuration_used': False, 'provider_request_attempt_counts_measured': False, 'recovery_proof_attempt_counts_measured':False, 'package_files_count': 113, 'package_payload_sha256': controller.sha(controller.canonical(self.inventory)), 'loaded_source_sha256': self.inventory['__init__.py']['sha256'], 'snapshot_sha256': 'b' * 64, 'quarantine_snapshot_sha256': None, 'owned_resource_id_sha256': '1' * 64, 'nonempty_options':True, 'nonempty_place_and_picture':True, 'static_served_bundle_matches':True, 'served_bundle_sha256':'8'*64, 'runtime_config_sha256':'9'*64, 'resource_url_type_sha256':'7'*64, 'normal_dependencies':dependencies(), 'process': {'pid': 123, 'start_ticks': 456}, 'entry_disabled': False, 'entry_loaded': True, 'guard': {'sha256': 'c' * 64, 'blocked': False, 'unresolved': 2, 'rejected': 2, 'pending':0, 'uncertain':0, 'api_status_checked': True}, 'recorder': {'prebackup_rows': 12, 'prebackup_sha256': 'd' * 64, 'prebackup_exact_match': True, 'postbackup_marker_rows': 0, 'postbackup_marker_absent': True, 'postrestore_rows': None, 'postrestore_sha256': None, 'postrestore_exact_match': None, 'integrity_ok': True, 'backup_platform_registered': True, 'commit_proven': True, 'no_backup_failure_issue': True}}

    def read(self):
        self.host.guest_read = Mock(return_value=controller.canonical(self.receipt))

    def captured(self, value, exitcode=0, error=b''):
        return {'exitcode': exitcode, 'signal': None, 'stdout': controller.canonical(value), 'stderr': error, 'truncated': False}

    def initialize(self):
        self.host.phases.append(self.host.accept_phase('initialize', self.receipt))

    def test_phase_atomicity_and_secret_projection_remain_narrow(self):
        self.receipt['private'] = self.receipt['guard']['private'] = 'PRIVATE-CANARY'
        self.read()
        self.host.phase('initialize')
        self.assertNotEqual(Path(self.host.guest_write.call_args.args[0]).name, 'phase.json')
        self.assertIn('; mv ', self.host.guest.call_args.args[0])
        public = (self.host.public / 'initialize.json').read_text()
        self.assertNotIn('PRIVATE-CANARY', public)
        self.assertNotIn(self.host.phase_token, public)

    def test_stale_backup_generation_or_nonce_cannot_count_as_progress(self):
        for key in ('generation', 'token'):
            with self.subTest(key=key):
                original = self.receipt[key]
                self.receipt[key] = 'stale'
                self.read()
                with self.assertRaises(controller.Refused):
                    self.host.phase('initialize')
                self.receipt[key] = original
        self.assertEqual(self.host.phases, [])

    def test_disabled_phase_cannot_report_loaded_homecircle(self):
        self.initialize()
        self.receipt.update(phase='quarantine', quarantine_snapshot_sha256='e' * 64)
        with self.assertRaises(controller.Refused):
            self.host.accept_phase('quarantine', self.receipt)

    def test_missing_disabled_boolean_cannot_satisfy_quarantine(self):
        self.initialize()
        self.receipt.update(entry_disabled=None, entry_loaded=False, quarantine_snapshot_sha256='e' * 64)
        with self.assertRaises(controller.Refused):
            self.host.accept_phase('quarantine', self.receipt)

    def test_quarantine_requires_actual_persisted_storage_proof_before_backup(self):
        self.initialize()
        self.receipt.update(entry_disabled=True, entry_loaded=False, loaded_source_sha256=None, quarantine_snapshot_sha256='e' * 64, persisted_storage_checked=False)
        self.receipt['guard'].update(api_status_checked=False, retained_bytes_checked=True)
        with self.assertRaisesRegex(controller.Refused, '^prebackup_persisted_storage_required$'):
            self.host.accept_phase('quarantine', self.receipt)
        self.receipt['persisted_storage_checked'] = True
        self.assertTrue(self.host.accept_phase('quarantine', self.receipt)['persisted_storage_checked'])

    def test_recorder_hook_and_committed_history_are_required(self):
        for key in ('backup_platform_registered', 'commit_proven', 'integrity_ok'):
            original = self.receipt['recorder'][key]
            self.receipt['recorder'][key] = False
            with self.subTest(key=key), self.assertRaises(controller.Refused):
                self.host.accept_phase('initialize', self.receipt)
            self.receipt['recorder'][key] = original

    def test_candidate_inventory_is_required_even_with_passing_helper(self):
        self.receipt['package_payload_sha256'] = '0' * 64
        with self.assertRaises(controller.Refused):
            self.host.accept_phase('initialize', self.receipt)

    def test_postrestore_guard_cannot_use_backed_up_zero_counter(self):
        self.initialize()
        self.host.latest_guard_sha256 = 'f' * 64
        self.receipt.update(entry_disabled=False, entry_loaded=True)
        self.receipt['owned_resource_id_sha256'] = '2' * 64
        self.receipt['recorder'].update(postrestore_rows=4, postrestore_sha256='e' * 64, postrestore_exact_match=True)
        with self.assertRaises(controller.Refused):
            self.host.accept_phase('reenabled', self.receipt)

    def test_restarted_recorder_rows_must_equal_postrestore_committed_rows(self):
        self.initialize()
        self.host.latest_guard_sha256 = 'f' * 64
        self.receipt['owned_resource_id_sha256'] = '2' * 64
        self.receipt['guard'].update(sha256='f' * 64, unresolved=3, rejected=3, blocked=True)
        self.receipt['recorder'].update(postrestore_rows=4, postrestore_sha256='e' * 64, postrestore_exact_match=True)
        self.host.phases.append(self.host.accept_phase('reenabled', self.receipt))
        self.receipt['process']['start_ticks'] += 1
        self.receipt['recorder']['postrestore_sha256'] = '9' * 64
        with self.assertRaises(controller.Refused):
            self.host.accept_phase('restart', self.receipt)

    def test_recreated_owned_resource_id_must_survive_restart(self):
        self.initialize()
        self.host.latest_guard_sha256 = 'f' * 64
        self.receipt['owned_resource_id_sha256'] = '2' * 64
        self.receipt['guard'].update(sha256='f' * 64, unresolved=3, rejected=3, blocked=True)
        self.receipt['recorder'].update(postrestore_rows=4, postrestore_sha256='e' * 64, postrestore_exact_match=True)
        self.host.phases.append(self.host.accept_phase('reenabled', self.receipt))
        self.receipt['process']['start_ticks'] += 1
        self.receipt['owned_resource_id_sha256'] = '3' * 64
        with self.assertRaisesRegex(controller.Refused, '^recreated_resource_restart_identity_changed$'):
            self.host.accept_phase('restart', self.receipt)

    def test_supported_backup_cli_mutation_is_not_retried_after_api_error(self):
        self.host.management_ready = Mock(return_value=True)
        failure = {'result': 'error', 'message': 'PRIVATE-CANARY', 'job_id': 'a' * 32}
        jobs = {'result': 'ok', 'data': {'jobs': [{'uuid': 'a' * 32, 'name': 'backup_manager_partial_backup', 'done': True, 'errors': [{'type': 'BackupFileExistError', 'message': 'PRIVATE-CANARY'}]}]}}
        self.host.guest = Mock(side_effect=[self.captured(failure, exitcode=1), controller.canonical(jobs)])
        with self.assertRaises(controller.Refused):
            self.host.backup_operation()
        commands = [call.args[0] for call in self.host.guest.call_args_list]
        self.assertEqual(sum((' backups new ' in command for command in commands)), 1)
        self.assertIn('--homeassistant-exclude-database=false', commands[0])
        self.assertIn('--location=.local', commands[0])
        self.assertNotIn('--location .local', commands[0])
        self.assertEqual(self.host.backup_requests[0]['exit_code'], 1)
        self.assertEqual(self.host.backup_requests[0]['result'], 'error')
        self.assertEqual(self.host.backup_requests[0]['jobs'][0]['binding'], 'exact_operation')
        self.assertNotIn('PRIVATE-CANARY', json.dumps(self.host.backup_requests))
        self.assertIsNone(self.host.backup)

    def test_successful_backup_accepts_a_normally_returning_void_core_validator(self):
        self.host.management_ready = Mock(return_value=True)
        self.host.managed_core = Mock(return_value=None)
        self.host.remaining = Mock(return_value=30)
        self.host.wait_backup_job = Mock(return_value={'done': True, 'error_count': 0, 'nodes': 1})
        self.host.guest = Mock(side_effect=[self.captured({'result': 'ok', 'data': {'job_id': 'a' * 32, 'slug': 'abcd1234'}}), controller.canonical({'result': 'ok', 'data': {'slug': 'abcd1234', 'type': 'partial', 'homeassistant': controller.CORE, 'homeassistant_exclude_database': False, 'protected': False, 'compressed': False}})])
        with patch.object(controller.time, 'monotonic', side_effect=[0] * 5 + [31]):
            self.host.backup_operation()
        self.host.managed_core.assert_called_once_with()
        self.assertEqual(self.host.guest.call_count, 2)
        self.assertTrue(self.host.backup['database_included'])

    def test_explicit_homeassistant_flag_selects_partial_restore(self):
        self.host.backup = {'slug': 'abcd1234'}
        self.host.management_ready = Mock(return_value=True)
        self.host.guest = Mock(side_effect=[self.captured({'result': 'error'}, exitcode=1), b'{"result":"ok","data":{"jobs":[]}}'])
        with self.assertRaises(controller.Refused):
            self.host.backup_operation(restore=True)
        commands = [call.args[0] for call in self.host.guest.call_args_list]
        self.assertIn('--homeassistant=true', commands[0])
        self.assertIn('--location=.local', commands[0])
        self.assertNotIn('--location .local', commands[0])
        self.assertEqual(sum((' backups restore ' in command for command in commands)), 1)

    def test_nonzero_child_with_ok_json_remains_a_failed_request(self):
        self.host.management_ready = Mock(return_value=True)
        self.host.guest = Mock(side_effect=[self.captured({'result': 'ok', 'data': {}}, exitcode=2), b'{"result":"ok","data":{"jobs":[]}}'])
        with self.assertRaises(controller.Refused):
            self.host.backup_operation()
        self.assertEqual(self.host.backup_requests[0]['exit_code'], 2)
        self.assertEqual(self.host.backup_requests[0]['result'], 'ok')
        self.assertIsNone(self.host.backup)

    def test_guest_capture_preserves_nonzero_exit_without_exporting_its_response(self):
        self.host.qga = Mock()
        self.host.qga.call.side_effect = [{'pid': 9}, {'exited': True, 'exitcode': 7, 'out-data': base64.b64encode(b'{"result":"error"}').decode(), 'err-data': base64.b64encode(b'PRIVATE-CANARY').decode()}]
        result = controller.Controller.guest(self.host, 'fixed-synthetic-command', capture=True)
        self.assertEqual(result['exitcode'], 7)
        self.assertEqual(json.loads(result['stdout'])['result'], 'error')
        self.assertEqual(self.host.backup_requests, [])

    def test_cleanup_before_vm_launch_removes_owned_private_workspace(self):
        private = self.host.public / 'owned-private'
        private.mkdir()
        self.host.private = private
        self.host.cleanup_vm()
        self.assertFalse(private.exists())
        self.assertFalse(self.host.cleanup['cleanup_failed'])
