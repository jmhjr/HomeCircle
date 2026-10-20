"""New procedure barriers and private transfer refusal contracts; no guest work."""
import base64
import ast
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import tarfile
import unittest
from unittest.mock import Mock, patch

import accept_procedure as gate
import controller
import guard_transfer as transfer
import test_phases as fixtures
from test_inherited import dependencies


def bundle():
    return transfer.canonical({'schema':1,'files':{
        'ledger.json':base64.b64encode(b'fictional-test-bytes').decode(),
        'ledger.lock':'','account-'+transfer.IDENTITY+'.lock':''}})


def synthetic_success():
    """Explicitly synthetic gate fixture; never a runtime receipt."""
    case=fixtures.ReusedPhaseContracts()
    case.setUp()
    try:
        host=case.host
        body=case.receipt
        phases={}
        def add(name):
            body['phase']=name
            value=host.accept_phase(name,deepcopy(body))
            phases[name]=value
            host.phases.append(value)
        add('initialize')
        body['process']['start_ticks']=457
        add('initial_restart')
        body.update(entry_disabled=True,entry_loaded=False,quarantine_snapshot_sha256='e'*64,persisted_storage_checked=True)
        body['guard']['api_status_checked']=False
        body['guard']['retained_bytes_checked']=True
        add('quarantine')
        body['snapshot_sha256']='0'*64
        body['guard'].update(sha256='f'*64,unresolved=3,rejected=3,blocked=True,api_status_checked=True)
        body['recorder'].update(postbackup_marker_rows=4,postbackup_marker_absent=False)
        add('mutate')
        automatic={'schema':1,'phase':'automatic_disabled','outcome':'passed','entry_disabled':True,'entry_loaded':False,
            'candidate_imported':False,'process':{'pid':123,'start_ticks':458},'snapshot_sha256':'b'*64,
            'quarantine_snapshot_sha256':'e'*64,'guard':{'sha256':'c'*64,'unresolved':2,'rejected':2,
            'pending':0,'uncertain':0,'blocked':False,'api_status_checked':False,'retained_bytes_checked':True},
            'provider_request_attempt_counts_measured':False,'recovery_proof_attempt_counts_measured':False}
        phases['automatic_disabled']=automatic
        host.phases.append(automatic)
        host.after_restore_barrier=host.guard_repaired=True
        host.network_boundary={'link_closed':True}
        host.generation='after_restore'
        body['snapshot_sha256']='b'*64
        body['process']['start_ticks']=459
        body['recorder'].update(postbackup_marker_rows=0,postbackup_marker_absent=True)
        body['normal_dependencies_before_enable']=dependencies(False)
        add('repaired_disabled')
        body.update(entry_disabled=False,entry_loaded=True,owned_resource_id_sha256='2'*64)
        body['recorder'].update(postrestore_rows=4,postrestore_sha256='e'*64,postrestore_exact_match=True)
        add('reenabled')
        body['process']['start_ticks']=460
        add('restart')
        # Match exact real frontend pin rather than this small controller fixture's digest.
        for name in ('initialize','initial_restart','reenabled','restart'):
            phases[name]['served_bundle_sha256']='80b2727d18a0b8edb052c47d2c718850adf19bf5d35c2af6c3eb86c07f1f6cac'
        public={'schema':1,'outcome':'passed','phases':8,'failure_or_final_stage':'safe_disabled_restore_complete',
            'failure_code':None,'failure_type':None,'actual_core':'2026.10.2','actual_supervisor':'2026.10.2',
            'current_core_image':{'identity_model':'containerd_index_with_verified_stored_oci_chain','official_index_digest':'sha256:45f009d6ff1061971102e81f0802cf2762bdd5c5007231c938bd36030cbd0a12','verified_oci_config_digest':'sha256:e1acee126eee45b3007494ad7f806d12535dc7d733624b681ed29a505f8c2b98','stored_objects_hashed':3,'image_rootfs_matches_verified_config':True},
            'core_actions':[{'action':a,'result':'ok','supervisor_running':True,'relevant_core_jobs_idle':True} for a in ['stop','start','stop','start','stop','start','stop','stop','start','stop','start','stop']],
            'network_transitions':['closed_before_restore','reopen_after_repaired_disabled','closed_before_final_restart'],
            'network_boundary':{'link_closed':True,'closed_probe_connected':False,'closed_probe_observations':5},
            'provenance':{'candidate_zip_sha256':gate.CANDIDATE,'candidate_files':113,
                'candidate_source_commit':'9bf03eb45d2cf43274074534e9dfe2de841f4011','release_published':False},
            'backup_requests':[{'action':name,'result':'ok','exit_code':0,'exact_job_id_returned':True,
                'output_truncated':False,'signal':None} for name in ('create','restore')],
            'backup':{'archive':{'disabled_entry':True,'database_included':True,'candidate_match':True,'guard_sha256':'c'*64}},
            'restore':{'host_copy_outside_entire_guest':True,'repaired_before_enable':True,
                'restored_old_guard_sha256':'c'*64,'promoted_newest_guard_sha256':'f'*64}}
        for key in ('actual_kvm_confirmed','host_newest_guard_retained','guard_repaired_before_enable',
                    'normal_managed_dependencies','tested_disabled_entry_partial_restore_procedure',
                    'qemu_stopped','private_workspace_removed'):public[key]=True
        for key in ('cleanup_failed','prepared_dependency_preload_used','ordinary_enabled_restore_safety_accepted',
                    'automatic_guard_antirollback','provider_request_attempt_counts_measured','recovery_proof_attempt_counts_measured',
                    'owner_credentials_used','provider_accounts_configured','production_configuration_used',
                    'full_encrypted_cloud_backup_tested','stable_release_approval','candidate_hacs_download_tested',
                    'candidate_release_zip_transport_tested'):public[key]=False
        return public,phases
    finally:
        case.doCleanups()


class ProcedureContracts(unittest.TestCase):
    def test_actual_prepare_reuses_only_the_fresh_private_workspace(self):
        tree=ast.parse(Path(controller.__file__).read_bytes())
        run=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='run')
        create=next(n.args[0] for n in ast.walk(run) if isinstance(n,ast.Call)
            and isinstance(n.func,ast.Attribute) and n.func.attr=='guest'
            and n.args and 'mkdir -m 700' in ast.unparse(n.args[0]))
        inventory=json.loads((controller.ROOT/'payload/inventory.json').read_bytes())['files']
        for case in ('good','missing','symlink','wrong_mode','wrong_owner'):
            with self.subTest(case=case),tempfile.TemporaryDirectory(prefix='homecircle-prepare-') as name:
                root=Path(name).resolve();workspace=root/'guest-control';private=root/'private';private.mkdir()
                config=root/'config';config.mkdir()
                host=controller.Controller(type('Args',(),{'branch_commit':'a'*40,
                    'candidate_zip':controller.ROOT/'payload/homecircle.zip'})())
                host.private=private;host.config_path=str(config);host.inventories={'candidate':inventory}
                host.stop_core=Mock()
                initial=eval(compile(ast.Expression(create),'actual-main-workspace-create','eval'),
                             {'GUEST_ROOT':str(workspace)})
                owner=0  # Explicit simulated guest UID; the local Mac owner is not a guest proof.
                def guest(command,limit):
                    if command==initial:
                        try:workspace.mkdir(mode=0o700)
                        except FileExistsError:raise controller.Refused('guest_command_failed') from None
                        return b''
                    if command.startswith('set -eu; test -d '):
                        self.assertIn('test ! -L '+str(workspace),command)
                        self.assertIn("stat -c '%u:%a' "+str(workspace),command)
                        self.assertTrue(command.endswith('= 0:700'))
                        if (not workspace.is_dir() or workspace.is_symlink()
                                or workspace.stat().st_mode&0o7777!=0o700 or owner!=0):
                            raise controller.Refused('guest_command_failed')
                        return b''
                    if command.startswith('sha256sum '):
                        return (hashlib.sha256((workspace/'staging.tgz').read_bytes()).hexdigest()+'  staging.tgz\n').encode()
                    if command.startswith('set -eu; umask 077; tar -xzf '):
                        with tarfile.open(workspace/'staging.tgz','r:gz') as archive:
                            self.assertTrue(all(x.name.startswith('custom_components') for x in archive.getmembers()))
                            archive.extractall(config,filter='data')
                        for child in (controller.CONTROL,controller.RESULTS):(config/child).mkdir(mode=0o700)
                        return b''
                    if command.startswith('set -eu; chmod 600 '):
                        for child in (config/'configuration.yaml',config/controller.CONTROL/'inputs.json'):child.chmod(0o600)
                        (workspace/'staging.tgz').unlink();return b''
                    if command.startswith('set -eu; find '):
                        return ('\n'.join(sorted(str(x) for x in (config/'custom_components/homecircle').rglob('*')
                            if x.is_file() and '__pycache__' not in x.parts and x.suffix!='.pyc'))+'\n').encode()
                    raise AssertionError('unexpected simulated guest command')
                def write(path,data):
                    target=Path(path);self.assertTrue(target.resolve().is_relative_to(root));target.write_bytes(data)
                host.guest=Mock(side_effect=guest);host.guest_write=Mock(side_effect=write)
                host.guest_read=Mock(side_effect=lambda path:Path(path).read_bytes())
                host.guest(initial,30)
                if case=='missing':workspace.rmdir()
                elif case=='symlink':
                    retained=root/'retained';workspace.rename(retained);workspace.symlink_to(retained,target_is_directory=True)
                elif case=='wrong_mode':workspace.chmod(0o755)
                elif case=='wrong_owner':owner=1000
                with patch.object(controller,'GUEST_ROOT',str(workspace)):
                    if case=='good':
                        host.prepare(inventory)
                        self.assertEqual(host.direct_installs,1)
                        self.assertEqual(len(list((config/'custom_components/homecircle').rglob('manifest.json'))),1)
                        self.assertTrue((config/controller.CONTROL/'inputs.json').is_file())
                        self.assertFalse((workspace/'staging.tgz').exists())
                    else:
                        with self.assertRaisesRegex(controller.Refused,'^guest_command_failed$'):host.prepare(inventory)
                        host.guest_write.assert_not_called()
                        self.assertFalse((private/'guest-staging').exists())
                host.stop_core.assert_called_once_with()

    def test_current_dependency_projector_accepts_current_pin_and_refuses_minimum_pin(self):
        value=dependencies()
        for group in ('direct','closure'):
            value[group]['protobuf']['version']='7.36.0'
        actual=controller.project_dependencies(value,True)
        self.assertEqual(actual['direct']['protobuf']['version'],'7.36.0')
        for group in ('direct','closure'):
            value[group]['protobuf']['version']='6.32.0'
        with self.assertRaisesRegex(controller.Refused,'^normal_direct_dependency_not_satisfied$'):
            controller.project_dependencies(value,True)

    def test_actual_dependency_observer_reads_single_probe_and_preserves_guest_protocol(self):
        host=object.__new__(controller.Controller)
        host.guest_write=Mock()
        host.guest=Mock(return_value=b'{"synthetic_probe_result":true}')
        actual=host.observe_dependencies()
        self.assertEqual(actual,{'synthetic_probe_result':True})
        host.guest_write.assert_called_once_with(
            controller.GUEST_ROOT+'/observe-dependencies.py',
            (controller.ROOT/'guest_helper/homecircle_safe_restore_qa/dependency_probe.py').read_bytes())
        host.guest.assert_called_once_with(
            '/usr/bin/docker exec -i homeassistant python3 -B - < '
            +controller.GUEST_ROOT+'/observe-dependencies.py',60)

    def test_complete_plain_procedure_keeps_automatic_safety_and_release_false(self):
        result=gate.accept(*synthetic_success())
        self.assertTrue(result['tested_disabled_entry_partial_restore_procedure'])
        self.assertFalse(result['ordinary_enabled_restore_safety_accepted'])
        self.assertFalse(result['stable_release_approval'])

    def test_diagnostic_green_or_failed_cleanup_cannot_pass(self):
        for key,value in [('outcome','confirmed_safety_issue'),('phases',7),('cleanup_failed',True),
                          ('qemu_stopped',False),('private_workspace_removed',False),('failure_code','fixed_failure')]:
            host,phases=synthetic_success();host[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):gate.accept(host,phases)

    def test_enabled_first_automatic_restore_is_refused(self):
        host,phases=synthetic_success();phases['automatic_disabled']['entry_disabled']=False
        with self.assertRaises(ValueError):gate.accept(host,phases)

    def test_stale_old_guard_missing_api_pending_and_uncertain_cannot_pass_repair(self):
        for key,value in [('sha256','c'*64),('unresolved',2),('blocked',False),('api_status_checked',False),('pending',1),('uncertain',1)]:
            host,phases=synthetic_success();phases['repaired_disabled']['guard'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):gate.accept(host,phases)

    def test_current_runtime_preload_source_and_network_scope_cannot_be_forgiven(self):
        for mutate in [lambda h,p:h.update(actual_core='2026.9.4'),lambda h,p:h.update(prepared_dependency_preload_used=True),
                       lambda h,p:h['provenance'].update(candidate_zip_sha256='0'*64),
                       lambda h,p:h.update(network_transitions=['closed_before_restore']),
                       lambda h,p:h['network_boundary'].update(link_closed=False)]:
            host,phases=synthetic_success();mutate(host,phases)
            with self.assertRaises(ValueError):gate.accept(host,phases)

    def test_history_settings_served_bytes_and_same_process_fail(self):
        for mutate in [lambda h,p:p['restart'].update(snapshot_sha256='0'*64),
                       lambda h,p:p['restart'].update(nonempty_place_and_picture=False),
                       lambda h,p:p['restart'].update(served_bundle_sha256='0'*64),
                       lambda h,p:p['restart']['recorder'].update(postrestore_sha256='0'*64),
                       lambda h,p:p['restart']['process'].update(start_ticks=p['reenabled']['process']['start_ticks'])]:
            host,phases=synthetic_success();mutate(host,phases)
            with self.assertRaises(ValueError):gate.accept(host,phases)

    def test_missing_phase_and_wrong_owned_resource_continuity_fail(self):
        host,phases=synthetic_success();phases.pop('automatic_disabled')
        with self.assertRaises(ValueError):gate.accept(host,phases)

    def test_legitimate_owned_id_reuse_is_allowed_when_url_type_and_restart_match(self):
        host,phases=synthetic_success()
        for name in ('reenabled','restart'):
            phases[name]['owned_resource_id_sha256']=phases['initialize']['owned_resource_id_sha256']
        self.assertEqual(gate.accept(host,phases)['outcome'],'passed')

    def test_automatic_observer_binds_exact_backed_up_generation_before_repair(self):
        for change in ({},{'token':'stale'},{'generation':'after_restore'},{'entry_loaded':True},
                       {'candidate_imported':True},{'guard_sha256':'f'*64},
                       {'process':{'pid':42,'start_ticks':100}},{'snapshot_sha256':'0'*64}):
            with tempfile.TemporaryDirectory() as name:
                host=controller.Controller(type('Args',(),{'branch_commit':'a'*40})())
                host.public=Path(name);host.config_path='/mnt/data/supervisor/homeassistant'
                host.network_boundary={'link_closed':True};host.host_guard_retained=True;host.backup_guard_sha256='c'*64
                host.restore={};host.phases=[{'snapshot_sha256':'b'*64},{},{'quarantine_snapshot_sha256':'e'*64},
                                            {'process':{'pid':42,'start_ticks':100}}]
                value={'schema':1,'token':host.phase_token,'generation':'before_restore','branch_commit':'a'*40,
                    'entry_disabled':True,'entry_loaded':False,'candidate_imported':False,
                    'process':{'pid':42,'start_ticks':200},'snapshot_sha256':'b'*64,
                    'quarantine_snapshot_sha256':'e'*64,'guard_sha256':'c'*64}|change
                host.guest_read=Mock(return_value=controller.canonical(value))
                host.guard_fingerprint=Mock(return_value='c'*64);host.assert_network_closed=Mock()
                if change:
                    with self.subTest(change=change),self.assertRaises(controller.Refused):host.restored_boot_barrier()
                    self.assertFalse(host.after_restore_barrier)
                else:
                    host.restored_boot_barrier()
                    self.assertTrue(host.after_restore_barrier)
                    retained=(Path(name)/'automatic_disabled.json').read_text()
                    self.assertNotIn(host.phase_token,retained)
                    self.assertFalse(json.loads(retained)['guard']['api_status_checked'])
        host,phases=synthetic_success();phases['restart']['owned_resource_id_sha256']='9'*64
        with self.assertRaises(ValueError):gate.accept(host,phases)

    def test_no_early_phase_or_network_reopen_can_touch_a_vm(self):
        host=controller.Controller(type('Args',(),{'branch_commit':'a'*40})())
        host.guest=Mock()
        for action in (lambda:host.phase('reenabled'),host.reopen_after_repaired_disabled,host.fresh_restore_control):
            with self.assertRaises(controller.Refused):action()
        host.guest.assert_not_called()

    def test_failure_projection_drops_bare_private_looking_values(self):
        value=controller.failure_projection({'stage':'bare_private_canary','failure_type':'BarePrivateCanary','failure_code':'bare_private_canary'})
        self.assertNotIn('canary',json.dumps(value).lower())


class PrivateTransferContracts(unittest.TestCase):
    def test_private_bundle_file_refuses_links_modes_and_oversize_before_read(self):
        with tempfile.TemporaryDirectory() as name:
            path=Path(name)/'bundle.json';path.write_bytes(bundle());path.chmod(0o600)
            self.assertEqual(transfer.read_private_bundle(path),bundle())
            link=Path(name)/'link';link.symlink_to(path)
            with self.assertRaises(ValueError):transfer.read_private_bundle(link)
            path.chmod(0o644)
            with self.assertRaises(ValueError):transfer.read_private_bundle(path)
            path.chmod(0o600)
            with path.open('wb') as stream:stream.truncate(1024*1024+1)
            with self.assertRaises(ValueError):transfer.read_private_bundle(path)

    def test_bundle_bytes_round_trip_and_fingerprint_uses_actual_bytes(self):
        files=transfer.decode(bundle())
        first=transfer.fingerprint(files);files['ledger.json']+=b'changed'
        self.assertNotEqual(first,transfer.fingerprint(files))

    def test_missing_extra_parent_absolute_and_duplicate_members_fail(self):
        body=json.loads(bundle())
        for name in ['../outside','/outside','extra']:
            altered=deepcopy(body);altered['files'][name]=''
            with self.assertRaises(ValueError):transfer.decode(transfer.canonical(altered))
        body['files'].pop('ledger.json')
        with self.assertRaises(ValueError):transfer.decode(transfer.canonical(body))
        with self.assertRaises(ValueError):transfer.decode(b'{"schema":1,"schema":1,"files":{}}')

    def test_malformed_oversized_data_and_nonempty_lock_fail(self):
        for raw in [b'x'*(1024*1024+1),b'{}',b'[]',b'{"schema":true,"files":{}}']:
            with self.assertRaises(ValueError):transfer.decode(raw)
        body=json.loads(bundle());body['files']['ledger.lock']='eA=='
        with self.assertRaises(ValueError):transfer.decode(transfer.canonical(body))
        body=json.loads(bundle());body['files']['ledger.json']='!invalid!'
        with self.assertRaises(ValueError):transfer.decode(transfer.canonical(body))

    def test_actual_private_files_refuse_symlink_hardlink_special_and_modes(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name).resolve()/'recovery_guard';root.mkdir(mode=0o700)
            for key,raw in transfer.decode(bundle()).items():
                path=root/key;path.write_bytes(raw);path.chmod(0o600)
            self.assertEqual(set(transfer.private_files(root)),set(transfer.decode(bundle())))
            ledger=root/'ledger.json';ledger.chmod(0o644)
            with self.assertRaises(ValueError):transfer.private_files(root)
            ledger.chmod(0o600);os.link(ledger,root/'hardlink')
            with self.assertRaises(ValueError):transfer.private_files(root)
            (root/'hardlink').unlink();(root/'symlink').symlink_to(ledger)
            with self.assertRaises(ValueError):transfer.private_files(root)
            (root/'symlink').unlink();os.mkfifo(root/'fifo')
            with self.assertRaises(ValueError):transfer.private_files(root)


if __name__=='__main__':unittest.main()
