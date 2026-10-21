"""New procedure barriers and private transfer refusal contracts; no guest work."""
import base64
import ast
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import tarfile
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

import accept_procedure as gate
import controller
import guard_transfer as transfer
import test_phases as fixtures
from test_inherited import dependencies


def bundle():
    return transfer.canonical({'schema':1,'files':{
        'ledger.json':base64.b64encode(b'fictional-test-bytes').decode(),
        'ledger.lock':'','account-'+transfer.IDENTITY+'.lock':''}})


def entry_helpers():
    tree=ast.parse((controller.ROOT/'guest_helper/homecircle_safe_restore_qa/__init__.py').read_bytes())
    nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))
           and n.name in {'entry_scope','ensure_entry_scope','wait_for'}]
    namespace={'asyncio':asyncio,'check':controller.require}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'actual_helper_entry_scope','exec'),namespace)
    return namespace


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
            phases[name]['served_bundle_sha256']='77f429fb1908acc21cde2c89614f05f12c60a09bb37fa6ca78a1830ec07c6f91'
        public={'schema':1,'outcome':'passed','phases':8,'failure_or_final_stage':'safe_disabled_restore_complete',
            'failure_code':None,'failure_type':None,'actual_core':'2026.10.2','actual_supervisor':'2026.10.3',
            'current_core_image':{'identity_model':'containerd_index_with_verified_stored_oci_chain','official_index_digest':'sha256:45f009d6ff1061971102e81f0802cf2762bdd5c5007231c938bd36030cbd0a12','verified_oci_config_digest':'sha256:e1acee126eee45b3007494ad7f806d12535dc7d733624b681ed29a505f8c2b98','stored_objects_hashed':3,'image_rootfs_matches_verified_config':True},
            'core_actions':[{'action':a,'result':'ok','supervisor_running':True,'relevant_core_jobs_idle':True} for a in ['stop','start','stop','start','stop','start','stop','stop','start','stop','start','stop']],
            'network_transitions':['closed_before_restore','reopen_after_repaired_disabled','closed_before_final_restart'],
            'network_boundary':{'link_closed':True,'closed_probe_connected':False,'closed_probe_observations':5},
            'provenance':{'candidate_zip_sha256':gate.CANDIDATE,'candidate_files':113,
                'candidate_source_commit':'91ae59106a661143b770d7a3564d363c7c11a7dd','release_published':False},
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
    def test_actual_entry_scope_accepts_only_normal_enabled_system_entries(self):
        observe=entry_helpers()['entry_scope']
        def entry(domain,source='system',disabled=None):
            return SimpleNamespace(domain=domain,source=source,disabled_by=disabled,
                                   title='PRIVATE-CANARY',data={'PRIVATE-CANARY':'not exported'})
        base=[entry('hassio'),entry('backup'),entry('analytics')]
        scope=observe(base)
        self.assertTrue(scope['system_entries_ready'] and scope['entry_scope_allowed'])
        self.assertEqual(scope['domains'],{'homecircle':0,'hassio':1,'backup':1,'analytics':1,'other':0})
        self.assertTrue(observe(base+[entry('homecircle','user')])['system_entries_ready'])
        cases=[base+[entry('backup')],[entry('hassio'),entry('backup','user')],
               [entry('hassio'),entry('backup','system','user')],
               base+[entry('PRIVATE-CANARY','PRIVATE-CANARY')],
               base+[entry('homecircle','system')],[entry('hassio','user'),entry('backup')],
               base+[entry('homecircle','user'),entry('homecircle','user')]]
        for entries in cases:
            with self.subTest(entries=len(entries)):
                value=observe(entries)
                self.assertFalse(value['entry_scope_allowed'] or value['system_entries_ready'])
                self.assertNotIn('PRIVATE',json.dumps(value))
        self.assertFalse(observe([entry('hassio')])['system_entries_ready'])
        with self.assertRaises(controller.Refused):observe(base*9)

    def test_tagged_system_analytics_creation_requires_no_consent_or_entry_metadata_assumptions(self):
        # Exact tagged upstream method body only; no Core import or actual analytics call.
        source='async def async_step_system(\n    self, user_input: dict[str, Any] | None = None\n) -> ConfigFlowResult:\n    """Handle the initial step."""\n    return self.async_create_entry(title="Analytics", data={})\n'
        self.assertEqual(hashlib.sha256(source.encode()).hexdigest(),'829fa02c77069df0ac0573a17734ac23579bb5d8bcd31626d333fdd124edc9f6')
        namespace={}
        exec(compile('from __future__ import annotations\n'+source,'tagged_analytics_system_flow','exec'),namespace)
        calls=[]
        def create_entry(**kwargs):calls.append(kwargs);return kwargs
        result=asyncio.run(namespace['async_step_system'](SimpleNamespace(async_create_entry=create_entry)))
        self.assertEqual(calls,[{'title':'Analytics','data':{}}]);self.assertEqual(result,calls[0])
        def entry(domain,source='system',disabled=None):
            return SimpleNamespace(domain=domain,source=source,disabled_by=disabled,
                title='PRIVATE-CANARY',data={'preferences':'PRIVATE-CANARY'},options={'enabled':True},unique_id='PRIVATE-CANARY')
        observe=entry_helpers()['entry_scope'];base=[entry('hassio'),entry('backup')]
        good=observe(base+[entry('analytics')])
        self.assertTrue(good['system_entries_ready'] and good['entry_scope_allowed'])
        self.assertEqual(good['sources'],{'system':3,'user':0,'other':0})
        self.assertEqual(good['domains']['analytics'],1)
        for analytics in ([entry('analytics','user')],[entry('analytics','import')],
                          [entry('analytics',disabled='user')],[entry('analytics'),entry('analytics')],
                          [entry('analytics'),entry('PRIVATE-CANARY','system')]):
            value=observe(base+analytics)
            self.assertFalse(value['entry_scope_allowed'] or value['system_entries_ready'])
            self.assertNotIn('PRIVATE',json.dumps(value))
        self.assertFalse(observe(base)['system_entries_ready'])

    def test_public_entry_scope_projects_only_finite_counts_and_strict_types(self):
        scope=entry_helpers()['entry_scope']([
            SimpleNamespace(domain='hassio',source='system',disabled_by=None),
            SimpleNamespace(domain='backup',source='system',disabled_by=None),
            SimpleNamespace(domain='analytics',source='system',disabled_by=None)])
        self.assertEqual(controller.public_entry_scope(scope),scope)
        cases=[{**scope,'PRIVATE-CANARY':'body'}, {**scope,'total':True},
               {**scope,'total':17},{**scope,'system_entries_ready':'PRIVATE-CANARY'},
               {**scope,'domains':{**scope['domains'],'other':True}},
               {**scope,'sources':{'system':1,'user':0,'other':0}},
               {**scope,'domains':{'PRIVATE-CANARY':2}}]
        for value in cases:
            self.assertIsNone(controller.public_entry_scope(value))
        for value in (scope,{**scope,'PRIVATE-CANARY':'body'}):
            with tempfile.TemporaryDirectory() as name:
                host=controller.Controller(type('Args',(),{'branch_commit':'a'*40})())
                host.public=Path(name);host.config_path='/mnt/data/supervisor/homeassistant'
                host.guest_write=Mock();host.guest=Mock()
                failed={'schema':1,'token':host.phase_token,'phase':'initialize','generation':host.generation,
                    'branch_commit':'a'*40,'outcome':'failed','stage':'system_entries_ready',
                    'failure_code':'qa_only_owned_or_system_entries','failure_type':'Refused','entry_scope':value}
                host.guest_read=Mock(return_value=controller.canonical(failed))
                with self.assertRaisesRegex(controller.Refused,'^guest_acceptance_failed$'):host.phase('initialize')
                retained=json.loads((Path(name)/'initialize.json').read_bytes())
                self.assertEqual('entry_scope' in retained,value is scope)
                self.assertNotIn('PRIVATE',json.dumps(retained))

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


class EntryReadinessContracts(unittest.IsolatedAsyncioTestCase):
    async def test_actual_wait_observes_delayed_backup_and_refuses_invalid_or_expired_scope(self):
        functions=entry_helpers();hassio=SimpleNamespace(domain='hassio',source='system',disabled_by=None)
        backup=SimpleNamespace(domain='backup',source='system',disabled_by=None)
        analytics=SimpleNamespace(domain='analytics',source='system',disabled_by=None)
        states=iter(([hassio,analytics],[hassio,backup,analytics]));receipt={}
        hass=SimpleNamespace(config_entries=SimpleNamespace(async_entries=lambda:next(states)))
        await functions['ensure_entry_scope'](hass,receipt)
        self.assertTrue(receipt['entry_scope']['system_entries_ready'])
        invalid=SimpleNamespace(domain='backup',source='user',disabled_by=None)
        hass.config_entries.async_entries=lambda:[hassio,invalid]
        with self.assertRaisesRegex(controller.Refused,'^qa_only_owned_or_system_entries$'):
            await functions['ensure_entry_scope'](hass,receipt)
        self.assertFalse(receipt['entry_scope']['entry_scope_allowed'])
        async def expire(predicate,seconds):
            self.assertEqual(seconds,60);self.assertFalse(predicate());raise TimeoutError()
        functions['wait_for']=expire;hass.config_entries.async_entries=lambda:[hassio]
        with self.assertRaises(TimeoutError):await functions['ensure_entry_scope'](hass,receipt)
        self.assertEqual(receipt['entry_scope']['domains']['backup'],0)


    async def test_actual_readiness_waits_for_analytics_and_refuses_wrong_system_scope(self):
        functions=entry_helpers()
        def entry(domain,source='system',disabled=None):return SimpleNamespace(domain=domain,source=source,disabled_by=disabled)
        base=[entry('hassio'),entry('backup')];states=iter((base,base+[entry('analytics')]))
        receipt={};hass=SimpleNamespace(config_entries=SimpleNamespace(async_entries=lambda:next(states)))
        await functions['ensure_entry_scope'](hass,receipt)
        self.assertEqual(receipt['entry_scope']['domains']['analytics'],1)
        self.assertEqual(receipt['entry_scope']['sources']['system'],3)
        for analytics in (entry('analytics','user'),entry('analytics',disabled='user')):
            hass.config_entries.async_entries=lambda:base+[analytics]
            with self.assertRaisesRegex(controller.Refused,'^qa_only_owned_or_system_entries$'):
                await functions['ensure_entry_scope'](hass,receipt)
            self.assertFalse(receipt['entry_scope']['entry_scope_allowed'])
        async def expire(predicate,seconds):
            self.assertEqual(seconds,60);self.assertFalse(predicate());raise TimeoutError()
        functions['wait_for']=expire;hass.config_entries.async_entries=lambda:base
        with self.assertRaises(TimeoutError):await functions['ensure_entry_scope'](hass,receipt)
        self.assertEqual(receipt['entry_scope']['domains']['analytics'],0)


def diagnostic_helpers():
    source=(controller.ROOT/'guest_helper/homecircle_safe_restore_qa/__init__.py').read_bytes()
    tree=ast.parse(source)
    selected=[]
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'SETUP_STEPS','PERSON_NAMES','TRACKERS','PLACE'} for t in node.targets):
            selected.append(node)
        elif isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in {'setup_mark','checked_step','create_homecircle'}:
            selected.append(node)
    namespace={'check':controller.require,'ConfigEntryState':SimpleNamespace(LOADED='loaded'),'SOURCE_USER':'user'}
    exec(compile(ast.Module(body=selected,type_ignores=[]),'actual_setup_diagnostics','exec'),namespace)
    return namespace,tree


class SetupDiagnosticContracts(unittest.IsolatedAsyncioTestCase):
    def test_catalog_and_actual_markers_are_exact_and_private_values_are_refused(self):
        functions,tree=diagnostic_helpers()
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='setup_mark']
        self.assertTrue(calls)
        for node in calls:
            self.assertEqual(len(node.args),2)
            self.assertIsInstance(node.args[1],ast.Constant)
            self.assertIs(type(node.args[1].value),str)
        self.assertEqual({n.args[1].value for n in calls}|{'unclassified'},functions['SETUP_STEPS'])
        self.assertEqual(functions['SETUP_STEPS'],controller.SETUP_STEPS)
        self.assertEqual(len(controller.SETUP_STEPS),25)
        for value in controller.SETUP_STEPS:
            self.assertEqual(controller.public_setup_step(value),value)
        class PrivateString(str):pass
        for value in ('bare_private_canary','person_registry/PRIVATE-CANARY',{},[],None,True,1,PrivateString('person_registry')):
            self.assertIsNone(controller.public_setup_step(value))
            progress={};functions['setup_mark'](progress,value)
            self.assertEqual(progress,{'step':'unclassified'})
        functions['setup_mark'](None,'person_registry')

    def test_actual_failed_phase_retains_only_fixed_step_without_private_body(self):
        for phase,stage,value in [('initialize','persistent_setup',value) for value in
                ('person_registry','bare_private_canary',None,{'private':'PRIVATE-CANARY'})]+[
                ('initialize','guard_two','person_registry'),
                ('initial_restart','persistent_setup','person_registry')]:
            with tempfile.TemporaryDirectory() as name:
                host=controller.Controller(type('Args',(),{'branch_commit':'a'*40})())
                host.public=Path(name);host.config_path='/mnt/data/supervisor/homeassistant'
                host.guest_write=Mock();host.guest=Mock()
                host.phases=[{}]*controller.PHASES.index(phase)
                receipt={'schema':1,'token':host.phase_token,'phase':phase,'generation':host.generation,
                    'branch_commit':'a'*40,'outcome':'failed','stage':stage,'failure_code':None,
                    'failure_type':'TimeoutError','setup_step':value,'private':'PRIVATE-CANARY'}
                host.guest_read=Mock(return_value=controller.canonical(receipt))
                with self.assertRaisesRegex(controller.Refused,'^guest_acceptance_failed$'):host.phase(phase)
                public=json.loads((Path(name)/(phase+'.json')).read_bytes())
                self.assertEqual(public.get('setup_step'),'person_registry' if phase=='initialize' and stage=='persistent_setup' and value=='person_registry' else None)
                self.assertNotIn('CANARY',json.dumps(public));self.assertNotIn('canary',json.dumps(public))
                self.assertEqual(public['failure_type'],'TimeoutError')

    def test_actual_helper_exception_body_omits_stale_step_and_private_error_message(self):
        functions,tree=diagnostic_helpers()
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Rehearsal')
        run=next(n for n in cls.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='run')
        handler=next(n for n in ast.walk(run) if isinstance(n,ast.ExceptHandler) and isinstance(n.type,ast.Name) and n.type.id=='Exception')
        code=compile(ast.Module(body=handler.body,type_ignores=[]),'actual_helper_exception_body','exec')
        for stage,progress,expected in [('persistent_setup',{'step':'flow_entry_loaded'},'flow_entry_loaded'),
                ('guard_two',{'step':'flow_entry_loaded'},None),('persistent_setup',{},None)]:
            receipt={};namespace={'receipt':receipt,'stage':stage,'setup_progress':progress,
                'error':TimeoutError('PRIVATE-CANARY /owner/private'),'Refused':controller.Refused,'_LOGGER':Mock()}
            exec(code,namespace)
            self.assertEqual(receipt.get('setup_step'),expected)
            self.assertEqual(receipt['failure_type'],'TimeoutError')
            self.assertNotIn('CANARY',json.dumps(receipt));self.assertNotIn('/owner/private',json.dumps(receipt))
        keywords=[n for n in ast.walk(run) if isinstance(n,ast.keyword) and n.arg=='progress']
        self.assertTrue(keywords)
        self.assertTrue(all(isinstance(n.value,ast.Name) and n.value.id=='setup_progress' for n in keywords))

    async def test_actual_person_registry_states_load_and_options_waits_keep_specific_steps(self):
        async def exercise(timeout_at):
            functions,_=diagnostic_helpers();registry=SimpleNamespace(entities={});states=[];calls=[]
            entry=SimpleNamespace(entry_id='synthetic',state='loaded',runtime_data=object(),options={})
            async def create_person(hass,name,device_trackers):
                self.assertEqual(device_trackers,[])
                entity_id='person.synthetic_'+str(len(states))
                registry.entities[entity_id]=SimpleNamespace(domain='person',entity_id=entity_id)
                states.append(SimpleNamespace(name=name,entity_id=entity_id))
            results=iter(['assign_tracker','member','assign_tracker','member','confirm','create_entry'])
            async def flow_init(*args,**kwargs):calls.append(('flow_init',args,kwargs));return {'step_id':'household','flow_id':'f'}
            async def configure(*args):
                calls.append(('configure',args));step=next(results)
                return {'type':'create_entry','result':entry} if step=='create_entry' else {'step_id':step,'flow_id':'f'}
            async def options_init(*args):return {'step_id':'init','flow_id':'o'}
            async def options_configure(identifier,data):
                if 'next_step_id' in data:return {'step_id':'city_lookup','flow_id':'o'}
                entry.runtime_data=object();entry.options=dict(data);return {'type':'create_entry'}
            hass=SimpleNamespace(config_entries=SimpleNamespace(async_entries=lambda domain:[],
                flow=SimpleNamespace(async_init=flow_init,async_configure=configure),
                options=SimpleNamespace(async_init=options_init,async_configure=options_configure)),
                states=SimpleNamespace(async_all=lambda domain:states))
            waits=0;progress={}
            async def wait(predicate,seconds=120):
                nonlocal waits
                waits+=1;self.assertEqual(seconds,120)
                if waits==timeout_at:raise TimeoutError('PRIVATE-CANARY')
                self.assertTrue(predicate())
            functions.update(async_create_person=create_person,wait_for=wait)
            try:
                result=await functions['create_homecircle'](hass,registry,progress=progress)
                return progress,waits,result,calls
            except TimeoutError:
                return progress,waits,None,calls
        for index,expected in enumerate(('person_registry','person_states','flow_entry_loaded','options_entry_loaded'),1):
            progress,waits,result,calls=await exercise(index)
            self.assertIsNone(result);self.assertEqual(waits,index);self.assertEqual(progress['step'],expected)
            self.assertNotIn('CANARY',json.dumps(progress))
        progress,waits,result,calls=await exercise(None)
        self.assertEqual(waits,4);self.assertEqual(len(result[1]),2)
        self.assertEqual(result[0].options,{'city_lookup_enabled':False})
        self.assertEqual(len(calls),7)


if __name__=='__main__':unittest.main()


def person_diagnostic_functions():
    tree=ast.parse((controller.ROOT/'guest_helper/homecircle_safe_restore_qa/__init__.py').read_bytes())
    names={'public_person_sources','observe_person_sources','person_sources','setup_mark'}
    nodes=[node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))
           and node.name in names or isinstance(node,ast.Assign) and any(
               isinstance(target,ast.Name) and target.id in {'TRACKERS','SETUP_STEPS'} for target in node.targets)]
    namespace={}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'actual_person_source_diagnostics','exec'),namespace)
    return namespace,tree


class PersonSourceDiagnosticContracts(unittest.IsolatedAsyncioTestCase):
    def test_actual_observer_reports_each_independent_fixed_index_fault_without_values(self):
        functions,_=person_diagnostic_functions()
        people=['person.PRIVATE-CANARY-a','person.PRIVATE-CANARY-b']
        trackers=functions['TRACKERS']
        fields=('person_present','tracker_present','person_home','tracker_home',
                'source_matches_selected','configured_link_matches_selected')
        for index in (0,1):
            for fault in ('none',*fields):
                values={person:SimpleNamespace(state='home',attributes={'source':tracker,'private':'PRIVATE-CANARY'})
                        for person,tracker in zip(people,trackers,strict=True)}
                values.update({tracker:SimpleNamespace(state='home',attributes={'private':'PRIVATE-CANARY'}) for tracker in trackers})
                links={person:[tracker] for person,tracker in zip(people,trackers,strict=True)}
                if fault=='person_present':values.pop(people[index])
                elif fault=='tracker_present':values.pop(trackers[index])
                elif fault=='person_home':values[people[index]].state='PRIVATE-CANARY'
                elif fault=='tracker_home':values[trackers[index]].state='PRIVATE-CANARY'
                elif fault=='source_matches_selected':values[people[index]].attributes['source']='device_tracker.PRIVATE-CANARY'
                elif fault=='configured_link_matches_selected':links[people[index]]=['device_tracker.PRIVATE-CANARY']
                functions['entities_in_person']=lambda hass,person:links[person]
                result=functions['observe_person_sources'](SimpleNamespace(states=SimpleNamespace(get=values.get)),people)
                self.assertEqual(set(result),{'0','1'})
                self.assertEqual(result[str(1-index)],dict.fromkeys(fields,True))
                expected=dict.fromkeys(fields,True)
                if fault!='none':expected[fault]=False
                if fault=='person_present':expected.update(person_home=False,source_matches_selected=False)
                if fault=='tracker_present':expected['tracker_home']=False
                self.assertEqual(result[str(index)],expected)
                self.assertNotIn('CANARY',json.dumps(result))
        self.assertIsNone(functions['observe_person_sources'](None,people[:1]))
        self.assertIsNone(functions['observe_person_sources'](None,tuple(people)))

    def test_actual_helper_and_host_projectors_refuse_unknown_shape_types_and_canaries(self):
        functions,_=person_diagnostic_functions()
        fields=('person_present','tracker_present','person_home','tracker_home',
                'source_matches_selected','configured_link_matches_selected')
        valid={index:dict.fromkeys(fields,True) for index in ('0','1')}
        class PrivateDict(dict):pass
        invalid=[None,[],True,PrivateDict(valid),{'person.PRIVATE-CANARY':valid['0'],'1':valid['1']}]
        for change in ('extra_index','missing_index','extra_field','missing_field','int_boolean','private_value','dict_subclass'):
            value=deepcopy(valid)
            if change=='extra_index':value['2']=value['0']
            elif change=='missing_index':del value['1']
            elif change=='extra_field':value['0']['PRIVATE-CANARY']=False
            elif change=='missing_field':del value['0']['person_home']
            elif change=='int_boolean':value['0']['person_home']=1
            elif change=='private_value':value['0']['person_home']='PRIVATE-CANARY'
            else:value['0']=PrivateDict(value['0'])
            invalid.append(value)
        for project in (functions['public_person_sources'],controller.public_person_sources):
            self.assertEqual(project(valid),valid)
            self.assertIsNot(project(valid),valid)
            for value in invalid:self.assertIsNone(project(value))
        helper_node=next(node for node in ast.parse((controller.ROOT/'guest_helper/homecircle_safe_restore_qa/__init__.py').read_bytes()).body
                         if isinstance(node,ast.FunctionDef) and node.name=='public_person_sources')
        host_node=next(node for node in ast.parse((controller.ROOT/'controller.py').read_bytes()).body
                       if isinstance(node,ast.FunctionDef) and node.name=='public_person_sources')
        self.assertEqual(ast.dump(helper_node),ast.dump(host_node))

    async def test_actual_wait_keeps_predicate_timeout_error_identity_and_diagnostic_fault_disposition(self):
        functions,_=person_diagnostic_functions();trackers=functions['TRACKERS']
        people=['person.PRIVATE-CANARY-a','person.PRIVATE-CANARY-b']
        values={person:SimpleNamespace(state='home',attributes={'source':tracker})
                for person,tracker in zip(people,trackers,strict=True)}
        values.update({tracker:SimpleNamespace(state='home',attributes={}) for tracker in trackers})
        hass=SimpleNamespace(states=SimpleNamespace(get=values.get))
        functions['entities_in_person']=lambda hass,person:[trackers[people.index(person)]]
        async def succeeds(predicate):self.assertTrue(predicate())
        functions['wait_for']=succeeds;progress={}
        await functions['person_sources'](hass,people,progress=progress)
        self.assertEqual(progress,{'step':'person_sources'})
        values[people[0]].attributes['source']='device_tracker.PRIVATE-CANARY'
        failure=TimeoutError('PRIVATE-CANARY /owner/path')
        async def expires(predicate):self.assertFalse(predicate());raise failure
        functions['wait_for']=expires;progress={}
        with self.assertRaises(TimeoutError) as caught:await functions['person_sources'](hass,people,progress=progress)
        self.assertIs(caught.exception,failure)
        self.assertFalse(progress['person_sources']['0']['source_matches_selected'])
        self.assertTrue(progress['person_sources']['1']['source_matches_selected'])
        self.assertNotIn('CANARY',json.dumps(progress))
        functions['observe_person_sources']=Mock(side_effect=OSError('PRIVATE-CANARY'))
        progress={}
        with self.assertRaises(TimeoutError) as caught:await functions['person_sources'](hass,people,progress=progress)
        self.assertIs(caught.exception,failure);self.assertEqual(progress,{'step':'person_sources'})
        functions['observe_person_sources'].reset_mock()
        with self.assertRaises(TimeoutError):await functions['person_sources'](hass,people)
        functions['observe_person_sources'].assert_not_called()
        for error in (OSError('PRIVATE-CANARY'),asyncio.CancelledError()):
            async def other_failure(predicate):raise error
            functions['wait_for']=other_failure;progress={}
            with self.assertRaises(type(error)) as caught:await functions['person_sources'](hass,people,progress=progress)
            self.assertIs(caught.exception,error);self.assertEqual(progress,{'step':'person_sources'})
        # The actual wait call still supplies exactly the original predicate, no timeout override.
        original=next(node for node in ast.parse((controller.ROOT/'guest_helper/homecircle_safe_restore_qa/__init__.py').read_bytes()).body
                      if isinstance(node,ast.AsyncFunctionDef) and node.name=='person_sources')
        wait=next(node for node in ast.walk(original) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='wait_for')
        self.assertEqual(len(wait.args),1);self.assertEqual(wait.keywords,[])

    def test_actual_helper_and_host_failure_paths_require_exact_person_source_scope(self):
        functions,tree=person_diagnostic_functions()
        fields=('person_present','tracker_present','person_home','tracker_home',
                'source_matches_selected','configured_link_matches_selected')
        valid={index:dict.fromkeys(fields,False) for index in ('0','1')}
        malformed=deepcopy(valid);malformed['0']['source_matches_selected']='PRIVATE-CANARY'
        cls=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='Rehearsal')
        run=next(node for node in cls.body if isinstance(node,ast.AsyncFunctionDef) and node.name=='run')
        handler=next(node for node in ast.walk(run) if isinstance(node,ast.ExceptHandler) and isinstance(node.type,ast.Name) and node.type.id=='Exception')
        code=compile(ast.Module(body=handler.body,type_ignores=[]),'actual_person_failure_handler','exec')
        cases=[('initialize','persistent_setup','person_sources',valid,True),
               ('initialize','guard_two','person_sources',valid,False),
               ('initial_restart','persistent_setup','person_sources',valid,False),
               ('initialize','persistent_setup','snapshot',valid,False),
               ('initialize','persistent_setup','person_sources',malformed,False),
               ('initialize','persistent_setup','person_sources',None,False)]
        for phase,stage,step,observation,expected in cases:
            receipt={};namespace={'receipt':receipt,'stage':stage,'name':phase,
                'setup_progress':{'step':step,'person_sources':observation},
                'error':TimeoutError('PRIVATE-CANARY'),'Refused':controller.Refused,'_LOGGER':Mock(),
                'public_person_sources':functions['public_person_sources']}
            exec(code,namespace)
            self.assertEqual(receipt.get('person_sources'),valid if expected else None)
            self.assertNotIn('CANARY',json.dumps(receipt))
            with tempfile.TemporaryDirectory() as directory:
                host=controller.Controller(type('Args',(),{'branch_commit':'a'*40})())
                host.public=Path(directory);host.config_path='/mnt/data/supervisor/homeassistant'
                host.guest_write=Mock();host.guest=Mock();host.phases=[{}]*controller.PHASES.index(phase)
                body={'schema':1,'token':host.phase_token,'phase':phase,'generation':host.generation,
                      'branch_commit':'a'*40,'outcome':'failed','stage':stage,'setup_step':step,
                      'person_sources':observation,'failure_type':'TimeoutError','private':'PRIVATE-CANARY'}
                host.guest_read=Mock(return_value=controller.canonical(body))
                with self.assertRaisesRegex(controller.Refused,'^guest_acceptance_failed$'):host.phase(phase)
                public=json.loads((Path(directory)/(phase+'.json')).read_bytes())
                self.assertEqual(public.get('person_sources'),valid if expected else None)
                self.assertNotIn('CANARY',json.dumps(public))


PERSON_UPDATE_SOURCE = 'async def _update_data(self, item: dict, update_data: dict) -> dict:\n    """Return a new updated data object."""\n    update_data = self.UPDATE_SCHEMA(update_data)\n\n    user_id: str | None = update_data.get(CONF_USER_ID)\n\n    if user_id is not None and user_id != item.get(CONF_USER_ID):\n        await self._validate_user_id(user_id)\n\n    return {**item, **update_data}\n'
PERSON_UPDATE_SOURCE_SHA = '8832cf3109c0badb9827d4e8b9c5c928266f36f08b67650b5d6f9ba642cf33d5'
PERSON_UPDATE_FIELDS_SOURCE = 'UPDATE_FIELDS: VolDictType = {\n    probatio.Optional(CONF_NAME): probatio.All(str, probatio.Length(min=1)),\n    probatio.Optional(CONF_USER_ID): probatio.Any(str, None),\n    probatio.Optional(CONF_DEVICE_TRACKERS, default=list): probatio.All(\n        probatio.EnsureList(), cv.entities_domain(DEVICE_TRACKER_DOMAIN)\n    ),\n    probatio.Optional(CONF_PICTURE): probatio.Any(str, None),\n}\n'
PERSON_UPDATE_FIELDS_SOURCE_SHA = 'ddb410cbfa72f36cbc926061a95ccab8e617059a30be7cfed5bd20c57c04b39b'


def portrait_selection_functions(baseline=False):
    """Actual helper and tagged update body; schema defaults are a narrow model."""
    helper=ast.parse((controller.ROOT/'guest_helper/homecircle_safe_restore_qa/__init__.py').read_bytes())
    create=deepcopy(next(n for n in helper.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='create_portrait'))
    if baseline:
        create.body=[n for n in create.body if not (
            isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='selected_trackers' for t in n.targets)
            or isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name)
            and n.value.func.id=='check' and isinstance(n.value.args[-1],ast.Constant)
            and n.value.args[-1].value=='qa_portrait_person_selection')]
        call=next(n for n in ast.walk(create) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='async_update_item')
        data=call.args[1];assert isinstance(data,ast.Dict)
        pairs=[(key,value) for key,value in zip(data.keys,data.values,strict=True) if key.value!='device_trackers']
        data.keys=[key for key,value in pairs];data.values=[value for key,value in pairs]
    nodes=[n for n in helper.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'TRACKERS','SETUP_STEPS','PNG'} for t in n.targets)
           or isinstance(n,ast.FunctionDef) and n.name=='setup_mark']+[create]
    namespace={'base64':base64,'check':controller.require,'Path':Path,'digest':lambda raw:hashlib.sha256(raw).hexdigest()}
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),'actual_create_portrait','exec'),namespace)
    assert hashlib.sha256(PERSON_UPDATE_SOURCE.encode()).hexdigest()==PERSON_UPDATE_SOURCE_SHA
    assert hashlib.sha256(PERSON_UPDATE_FIELDS_SOURCE.encode()).hexdigest()==PERSON_UPDATE_FIELDS_SOURCE_SHA
    schema=ast.parse(PERSON_UPDATE_FIELDS_SOURCE).body[0].value
    tracker_markers=[key for key in schema.keys if isinstance(key,ast.Call) and key.args
                     and isinstance(key.args[0],ast.Name) and key.args[0].id=='CONF_DEVICE_TRACKERS']
    assert len(tracker_markers)==1
    marker=tracker_markers[0]
    assert isinstance(marker.func,ast.Attribute) and marker.func.attr=='Optional'
    assert len(marker.keywords)==1 and marker.keywords[0].arg=='default'
    assert isinstance(marker.keywords[0].value,ast.Name) and marker.keywords[0].value.id=='list'
    # This deliberately models only the tagged default, not the full probatio validator.
    def tagged_default_list_model(data):return {'device_trackers':[],**data}
    core={'CONF_USER_ID':'user_id'}
    exec(compile(PERSON_UPDATE_SOURCE,'tagged_PersonStorageCollection_update_data','exec'),core)
    return namespace,core['_update_data'],tagged_default_list_model


class PortraitSelectionContracts(unittest.IsolatedAsyncioTestCase):
    async def exercise_portrait(self,baseline=False,selection=None):
        functions,update_data,default_model=portrait_selection_functions(baseline)
        people=['person.synthetic_a','person.synthetic_b'];trackers=functions['TRACKERS']
        before={person:{'id':person,'name':'Synthetic','device_trackers':[tracker],'picture':None,'unrelated':'retained'}
                for person,tracker in zip(people,trackers,strict=True)}
        records=deepcopy(before);updates=[];models=[]
        class Collection:
            UPDATE_SCHEMA=staticmethod(default_model)
            async def async_update_item(self,identifier,data):
                updates.append((identifier,deepcopy(data)))
                models.append((data.get('device_trackers'),records[identifier]['device_trackers']))
                records[identifier]=await update_data(self,records[identifier],data)
        collection=Collection()
        async def create_image(data):
            self.assertEqual(set(data),{'file'});return {'id':'a'*32}
        async def executor(function):return function()
        async def wait(predicate):self.assertTrue(predicate())
        states=SimpleNamespace(get=lambda person:SimpleNamespace(attributes={'entity_picture':records[person]['picture']}))
        hass=SimpleNamespace(data={'image_upload':SimpleNamespace(async_items=lambda:[],async_create_item=create_image),
                                   'person':(None,collection)},states=states,async_add_executor_job=executor)
        functions.update({'entities_in_person':lambda hass,person:records[person]['device_trackers'] if selection is None else selection,
                          'wait_for':wait,'FileField':lambda *args:args,'CIMultiDict':dict,'CIMultiDictProxy':lambda value:value})
        with tempfile.TemporaryDirectory() as directory:
            image=Path(directory)/'synthetic-image-source.py';person=Path(directory)/'synthetic-person-source.py'
            image.write_bytes(b'synthetic-module-byte-guard');person.write_bytes(b'synthetic-person-byte-guard')
            functions.update({'image_component':SimpleNamespace(__file__=str(image)),'person_component':SimpleNamespace(__file__=str(person)),
                              'API_SOURCES':{'image_upload':hashlib.sha256(image.read_bytes()).hexdigest(),
                                             'person':hashlib.sha256(person.read_bytes()).hexdigest()}})
            import io
            functions['io']=io
            registry=SimpleNamespace(async_get=lambda entity:SimpleNamespace(unique_id=entity))
            try:await functions['create_portrait'](hass,people,registry)
            except controller.Refused as error:
                return records,before,updates,models,error
        return records,before,updates,models,None

    async def test_actual_picture_call_preserves_selected_tracker_under_tagged_default_transform(self):
        old,before,updates,_,error=await self.exercise_portrait(baseline=True)
        self.assertIsNone(error);self.assertEqual(set(updates[0][1]),{'picture'})
        self.assertEqual(old['person.synthetic_a']['device_trackers'],[])
        current,before,updates,models,error=await self.exercise_portrait()
        self.assertIsNone(error);self.assertEqual(set(updates[0][1]),{'picture','device_trackers'})
        self.assertEqual(current['person.synthetic_a']['device_trackers'],before['person.synthetic_a']['device_trackers'])
        self.assertEqual(current['person.synthetic_a']['picture'],'/api/image/serve/'+'a'*32+'/512x512')
        self.assertEqual(current['person.synthetic_a']['unrelated'],'retained')
        self.assertEqual(current['person.synthetic_b'],before['person.synthetic_b'])
        self.assertIsNot(models[0][0],models[0][1])

    async def test_actual_picture_call_refuses_missing_foreign_or_multiple_selection_before_update(self):
        functions,_,_=portrait_selection_functions();first,second=functions['TRACKERS']
        for selection in ([],[second],[first,second],['device_tracker.synthetic_foreign']):
            records,before,updates,_,error=await self.exercise_portrait(selection=selection)
            self.assertIsNotNone(error);self.assertEqual(str(error),'qa_portrait_person_selection')
            self.assertEqual(updates,[]);self.assertEqual(records,before)


class GuardExportDiagnosticContracts(unittest.TestCase):
    def test_import_has_no_actions_and_actual_token_reader_is_bounded_and_link_safe(self):
        from contextlib import redirect_stdout,redirect_stderr
        import io
        raw=(controller.ROOT/'guard_transfer.py').read_bytes()
        with patch('os.open',side_effect=AssertionError('unexpected action')) as opened:
            exec(compile(raw,'guard_transfer_import_only','exec'),{'__name__':'guard_transfer_import_only'})
            opened.assert_not_called()
        token='b'*32
        proof={'schema':1,'token':token,'generation':'before_restore','branch_commit':'a'*40,'postbackup_window':{}}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'proof.json';path.write_bytes(transfer.canonical(proof))
            with patch.object(transfer,'EXPORT_PROOF',path):
                self.assertEqual(transfer.read_export_token(),token)
                stdout,stderr=io.StringIO(),io.StringIO();files=transfer.decode(bundle())
                with patch.object(transfer.sys,'argv',['-','export']),patch.object(transfer.sys,'platform','linux'), \
                        patch.object(transfer.os,'geteuid',return_value=0),patch.object(transfer,'blocked_status') as checked, \
                        patch.object(transfer,'private_files',return_value=files) as private,redirect_stdout(stdout),redirect_stderr(stderr):
                    transfer.cli()
                checked.assert_called_once_with();private.assert_called_once_with(transfer.GUARD)
                self.assertEqual(stdout.getvalue(),bundle().decode()+'\n');self.assertEqual(stderr.getvalue(),'')
                saved=path.read_bytes();path.write_bytes(b'x'*65537)
                with self.assertRaises(ValueError):transfer.read_export_token()
                path.write_bytes(saved);linked=Path(directory)/'hardlink';os.link(path,linked)
                with self.assertRaises(ValueError):transfer.read_export_token()
                linked.unlink();path.unlink();path.symlink_to(Path(directory)/'missing')
                with self.assertRaises(OSError):transfer.read_export_token()
                path.unlink();path.write_bytes(saved.replace(b'"schema":1',b'"schema":1,"schema":1'))
                with self.assertRaises(ValueError):transfer.read_export_token()

    def test_actual_export_wrapper_emits_only_known_token_stage_and_type_or_nothing(self):
        from contextlib import redirect_stdout,redirect_stderr
        import io
        token='b'*32
        proof={'schema':1,'token':token,'generation':'before_restore','branch_commit':'a'*40,'postbackup_window':{}}
        class PRIVATE_CANARY(ValueError):pass
        for stage,error in [('blocked_status',ValueError('PRIVATE-CANARY /private/path')),
                            ('blocked_status',PRIVATE_CANARY('PRIVATE-CANARY')),
                            ('private_files',OSError('PRIVATE-CANARY')),
                            ('encode',TypeError('PRIVATE-CANARY'))]:
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'proof.json';path.write_bytes(transfer.canonical(proof))
                stdout,stderr=io.StringIO(),io.StringIO()
                status=Mock(side_effect=error if stage=='blocked_status' else None)
                files=Mock(side_effect=error if stage=='private_files' else None,return_value={'ledger.json':b'PRIVATE-CANARY'})
                original=transfer.canonical
                canonical=Mock(side_effect=error) if stage=='encode' else original
                with patch.object(transfer,'EXPORT_PROOF',path),patch.object(transfer.sys,'argv',['-','export']), \
                        patch.object(transfer.sys,'platform','linux'),patch.object(transfer.os,'geteuid',return_value=0), \
                        patch.object(transfer,'blocked_status',status),patch.object(transfer,'private_files',files), \
                        patch.object(transfer,'canonical',canonical),redirect_stdout(stdout),redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as stopped:transfer.cli()
                self.assertEqual(stopped.exception.code,1);self.assertEqual(stdout.getvalue(),'')
                raw=stderr.getvalue().encode();observed=transfer.parse_export_failure(raw,token)
                self.assertEqual(observed,{'stage':stage,'failure_type':'unrecognized_failure_type' if type(error) is PRIVATE_CANARY else type(error).__name__})
                self.assertNotIn('CANARY',raw.decode());self.assertNotIn('/private/path',raw.decode())
                self.assertNotIn('Traceback',raw.decode())
        stdout,stderr=io.StringIO(),io.StringIO()
        with patch.object(transfer.sys,'argv',['-','export']),patch.object(transfer.sys,'platform','linux'), \
                patch.object(transfer.os,'geteuid',return_value=0),patch.object(transfer,'read_export_token',side_effect=ValueError('PRIVATE-CANARY')), \
                patch.object(transfer,'blocked_status',side_effect=RuntimeError('PRIVATE-CANARY')) as status,redirect_stdout(stdout),redirect_stderr(stderr):
            with self.assertRaises(SystemExit):transfer.cli()
            status.assert_called_once_with()
        self.assertEqual(stdout.getvalue(),stderr.getvalue());self.assertEqual(stderr.getvalue(),'')
        stdout,stderr=io.StringIO(),io.StringIO()
        with patch.object(transfer.sys,'argv',['-','export']),patch.object(transfer.sys,'platform','linux'), \
                patch.object(transfer.os,'geteuid',return_value=0),patch.object(transfer,'read_export_token',side_effect=ValueError('PRIVATE-CANARY')), \
                patch.object(transfer,'blocked_status'),patch.object(transfer,'private_files',return_value=transfer.decode(bundle())), \
                redirect_stdout(stdout),redirect_stderr(stderr):
            transfer.cli()
        self.assertEqual(stdout.getvalue(),bundle().decode()+'\n');self.assertEqual(stderr.getvalue(),'')

    def test_actual_parser_and_host_projection_refuse_unknown_json_token_types_and_canaries(self):
        token='b'*32
        valid={'schema':1,'kind':'homecircle_guard_export_failure','token':token,'stage':'blocked_status','failure_type':'ValueError'}
        encoded=transfer.canonical(valid)
        self.assertEqual(transfer.parse_export_failure(encoded,token),{'stage':'blocked_status','failure_type':'ValueError'})
        invalid=[b'',b'PRIVATE-CANARY traceback',b'{',b'x'*2049,encoded.replace(b'"schema":1',b'"schema":1,"schema":1')]
        for key,value in [('schema',True),('kind','PRIVATE-CANARY'),('token','c'*32),('stage','PRIVATE-CANARY'),('failure_type','PRIVATE-CANARY')]:
            body=dict(valid);body[key]=value;invalid.append(transfer.canonical(body))
        extra=dict(valid,private='PRIVATE-CANARY');invalid.append(transfer.canonical(extra))
        for raw in invalid:self.assertIsNone(transfer.parse_export_failure(raw,token))
        for badtoken in (None,'PRIVATE-CANARY','b'*31):self.assertIsNone(transfer.parse_export_failure(encoded,badtoken))
        result={'exitcode':17,'signal':None,'truncated':False,'stdout':b'PRIVATE-BUNDLE-CANARY','stderr':encoded}
        observed=controller.guard_export_observation(result,token)
        self.assertEqual(observed,{'exit_code':17,'signal':None,'output_truncated':False,'stdout_present':True,
                                  'stderr_present':True,'helper_failure':{'stage':'blocked_status','failure_type':'ValueError'}})
        self.assertNotIn(token,json.dumps(observed));self.assertNotIn('CANARY',json.dumps(observed))
        result['stderr']=b'PRIVATE-CANARY raw error';self.assertIsNone(controller.guard_export_observation(result,token)['helper_failure'])
        result.update(truncated=True,stdout=b'',stderr=b'')
        observed=controller.guard_export_observation(result,token)
        self.assertIsNone(observed['stdout_present']);self.assertIsNone(observed['stderr_present']);self.assertIsNone(observed['helper_failure'])
        for key,value in [('exit_code',True),('signal',999),('stdout_present',False),('helper_failure',{'stage':'PRIVATE-CANARY','failure_type':'ValueError'})]:
            body=dict(observed);body[key]=value;self.assertIsNone(controller.public_guard_export(body))

    def test_actual_same_export_command_and_failed_finish_keep_only_fixed_observation(self):
        from contextlib import redirect_stdout
        import io
        for success,truncated,signal_value in [(True,False,None),(False,False,None),(False,True,None),(False,False,9)]:
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);host=controller.Controller(type('Args',(),{'branch_commit':'a'*40})())
                host.config_path='/mnt/data/supervisor/homeassistant';host.private=root/'private';host.private.mkdir(mode=0o700)
                host.public=root/'public';host.public.mkdir();host.stop_core=Mock();host.guest_write=Mock()
                proof={'schema':1,'token':host.phase_token,'generation':'before_restore','branch_commit':'a'*40,
                       'postbackup_window':{'start':1.0,'end':2.0,'rows':5,'sha256':'a'*64}}
                host.guest_read=Mock(return_value=controller.canonical(proof));raw=bundle()
                host.latest_guard_sha256=transfer.fingerprint(transfer.decode(raw));host.backup_guard_sha256='0'*64
                diagnostic=transfer.canonical({'schema':1,'kind':'homecircle_guard_export_failure','token':host.phase_token,
                    'stage':'private_files','failure_type':'ValueError'})
                result={'exitcode':0 if success else None if signal_value else 17,'signal':signal_value,'truncated':truncated,
                        'stdout':raw if success else b'','stderr':b'' if success or truncated else diagnostic}
                host.run_guard_transfer=Mock(return_value=result)
                host.guest=Mock()
                if success:
                    host.preserve_latest_guard();self.assertTrue(host.host_guard_retained)
                    self.assertEqual(host.host_guard.read_bytes(),raw)
                    failure=None
                else:
                    with self.assertRaisesRegex(controller.Refused,'^guest_command_failed$') as caught:host.preserve_latest_guard()
                    failure=caught.exception;self.assertFalse(host.host_guard_retained)
                host.run_guard_transfer.assert_called_once_with('export')
                host.guest.assert_not_called()
                host.guest_write.assert_called_once_with(controller.GUEST_ROOT+'/guard-transfer.py',(controller.ROOT/'guard_transfer.py').read_bytes())
                host.cleanup_vm=Mock();host.cleanup={'qemu_stopped':True,'private_workspace_removed':True,'cleanup_failed':False}
                with redirect_stdout(io.StringIO()):host.finish(failure)
                public=json.loads((host.public/'host.json').read_bytes())
                self.assertEqual('guard_export' in public,not success)
                self.assertNotIn('CANARY',json.dumps(public));self.assertNotIn(host.phase_token,json.dumps(public))
                host.stage='initialize'
                with redirect_stdout(io.StringIO()):host.finish(controller.Refused('guest_command_failed'))
                self.assertNotIn('guard_export',json.loads((host.public/'host.json').read_bytes()))


# Exact-candidate standalone storage faults, in the same pure contract suite.
import errno
import stat
import sys
import threading
import types
import zipfile
with zipfile.ZipFile(controller.ROOT / 'payload/homecircle.zip') as storage_archive:
    STORAGE_RAW = storage_archive.read('findmy_recovery_guard.py')

class Proxy:
    def __init__(self, target, **replacements):
        self.target = target
        self.replacements = replacements

    def __getattr__(self, name):
        return self.replacements.get(name, getattr(self.target, name))


class GuardFailureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='owned-guard-diagnostic-')
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / '.storage/homecircle_findmy/recovery_guard'
        self.module = types.ModuleType('owned_exact_guard_fault_fixture')
        exec(compile(STORAGE_RAW, 'exact-candidate-guard', 'exec'), self.module.__dict__)
        self.guard = self.module.RecoveryGuard(self.root)
        async def seed():
            for _ in range(3):
                async with self.guard.attempt(transfer.IDENTITY) as attempt:
                    await attempt.before_dispatch()
                    await attempt.refused()
        asyncio.run(seed())
        self.binding = transfer.SourceBinding(self.guard, STORAGE_RAW)

    def tearDown(self):
        self.module.os = os
        self.temp.cleanup()

    def observed(self):
        try:
            asyncio.run(self.guard.status(transfer.IDENTITY))
        except self.module.RecoveryGuardStorageError as error:
            observation = self.binding.observe(error)
            self.assertIsNotNone(observation)
            self.assertEqual(transfer.public_observation(observation), observation)
            self.assertNotIn('private-canary', json.dumps(observation))
            return error, observation
        self.fail('actual_guard_fault_did_not_refuse')

    def assert_fields(self, observation, **expected):
        self.assertEqual({key: observation[key] for key in expected}, expected)

    def test_success_has_no_observation_or_changed_bytes_or_trace_hooks(self):
        before = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in self.root.iterdir()}
        hooks = (sys.gettrace(), threading.gettrace())
        result = asyncio.run(self.guard.status(transfer.IDENTITY))
        self.assertTrue(result['blocked'])
        self.assertEqual(result['rejected'], 3)
        self.assertEqual(before, {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                 for path in self.root.iterdir()})
        self.assertEqual(hooks, (sys.gettrace(), threading.gettrace()))

    def test_private_parent_and_guard_root_permission_predicates(self):
        for path, role in ((self.root.parent, 'private_parent'), (self.root, 'guard_root')):
            with self.subTest(role=role):
                path.chmod(0o755)
                _, value = self.observed()
                self.assert_fields(value, operation='directory', substage='private_directory_policy',
                                   role=role, node_kind='directory', owner_matches_uid=True,
                                   mode_matches=False, single_link=None, errno=None)
                path.chmod(0o700)

    def test_original_owner_check_is_distinct_from_mode(self):
        def fstat(descriptor):
            info = os.fstat(descriptor)
            fields = list(info)
            fields[4] = os.getuid() + 1
            return os.stat_result(fields)
        self.module.os = Proxy(os, fstat=fstat)
        _, value = self.observed()
        self.assert_fields(value, substage='private_directory_policy', role='private_parent',
                           mode_matches=True, owner_matches_uid=False)

    def test_ledger_and_lock_mode_policy_roles(self):
        for name, role in (('ledger.json', 'ledger'), ('ledger.lock', 'ledger_lock')):
            with self.subTest(role=role):
                path = self.root / name
                path.chmod(0o644)
                _, value = self.observed()
                self.assert_fields(value, substage='private_file_policy', role=role,
                                   node_kind='regular', owner_matches_uid=True,
                                   mode_matches=False, single_link=True)
                path.chmod(0o600)

    def test_original_regular_file_and_single_link_predicates(self):
        lock = self.root / 'ledger.lock'
        os.link(lock, self.base / 'owned-hardlink')
        _, value = self.observed()
        self.assert_fields(value, role='ledger_lock', node_kind='regular',
                           mode_matches=True, single_link=False)
        (self.base / 'owned-hardlink').unlink()
        lock.unlink()
        lock.mkdir(mode=0o600)
        _, value = self.observed()
        self.assert_fields(value, operation='lock', substage='lock_open',
                           role='ledger_lock', failure_type='IsADirectoryError',
                           node_kind=None, owner_matches_uid=None, mode_matches=None)

    def test_nonregular_ledger_is_reported_without_content_read(self):
        path = self.root / 'ledger.json'
        path.unlink()
        os.mkfifo(path, mode=0o600)
        _, value = self.observed()
        self.assert_fields(value, role='ledger', substage='private_file_policy',
                           node_kind='other', mode_matches=True, single_link=True)

    def test_parent_symlink_is_ancestor_open_error_without_stale_stat(self):
        target = self.root.parent.with_name('owned-private-parent')
        self.root.parent.rename(target)
        self.root.parent.symlink_to(target, target_is_directory=True)
        _, value = self.observed()
        self.assertEqual(value['role'], 'private_parent')
        self.assertEqual(value['substage'], 'ancestor_open')
        self.assertIn(value['errno'], {'ELOOP', 'ENOTDIR'})
        self.assert_fields(value, node_kind=None, owner_matches_uid=None, mode_matches=None)
        self.root.parent.unlink()
        target.rename(self.root.parent)

    def test_ledger_symlink_has_fixed_role_and_errno_only(self):
        path = self.root / 'ledger.json'
        target = self.base / 'owned-ledger-target'
        path.rename(target)
        path.symlink_to(target)
        _, value = self.observed()
        self.assert_fields(value, role='ledger', substage='ledger_open', errno='ELOOP',
                           node_kind=None, owner_matches_uid=None, mode_matches=None)

    def test_malformed_json_schema_and_counters_are_distinct(self):
        path = self.root / 'ledger.json'
        cases = [
            (b'{"private-canary":', 'ledger_json', 'JSONDecodeError'),
            (b'{"version":1,"version":1,"accounts":{}}', 'ledger_duplicate_keys', 'ValueError'),
            (b'[]', 'ledger_schema', 'ValueError'),
            (b'{"version":2,"accounts":{}}', 'ledger_version', 'ValueError'),
            (b'{"version":1,"accounts":[]}', 'ledger_accounts', 'ValueError'),
            (json.dumps({'version': 1, 'accounts': {'private-canary': {}}}).encode(),
             'ledger_account_identity', 'ValueError'),
            (json.dumps({'version': 1, 'accounts': {transfer.IDENTITY: {}}}).encode(),
             'ledger_entry_schema', 'ValueError'),
        ]
        for key, data, expected in (
                ('rejected', -1, 'ledger_counters'), ('pending', 'private-canary', 'ledger_pending')):
            item = dict(rejected=3, uncertain=0, verified=0, pending=None)
            item[key] = data
            cases.append((json.dumps({'version': 1, 'accounts': {transfer.IDENTITY: item}}).encode(),
                          expected, 'ValueError'))
        for raw, stage, kind in cases:
            with self.subTest(stage=stage):
                path.write_bytes(raw)
                _, value = self.observed()
                self.assert_fields(value, role='ledger', substage=stage, failure_type=kind,
                                   errno=None, node_kind=None)

    def test_ledger_size_rejection_does_not_read_or_export_content(self):
        (self.root / 'ledger.json').write_bytes(b' ' * (1024 * 1024 + 1))
        _, value = self.observed()
        self.assert_fields(value, role='ledger', substage='ledger_size', failure_type='ValueError')

    def test_actual_lock_open_and_flock_os_errors_retain_fixed_errno(self):
        original = os.open
        def denied(path, flags, *args, **kwargs):
            if path == 'ledger.lock':
                raise PermissionError(errno.EACCES, 'private-canary', '/private-canary')
            return original(path, flags, *args, **kwargs)
        self.module.os = Proxy(os, open=denied)
        error, value = self.observed()
        self.assertIsInstance(error.__context__, PermissionError)
        self.assert_fields(value, role='ledger_lock', substage='lock_open', errno='EACCES',
                           failure_type='PermissionError')
        self.module.os = os
        original_fcntl = self.module.fcntl
        def failed_flock(*args):
            raise OSError(errno.EIO, 'private-canary', '/private-canary')
        self.module.fcntl = Proxy(original_fcntl, flock=failed_flock)
        _, value = self.observed()
        self.assert_fields(value, substage='ledger_lock_acquire', role='ledger_lock', errno='EIO')

    def test_handled_missing_file_is_not_a_false_failure(self):
        (self.root / 'ledger.json').unlink()
        (self.root / 'ledger.lock').unlink()
        result = asyncio.run(self.guard.status(transfer.IDENTITY))
        self.assertEqual(result['rejected'], 0)
        self.assertFalse(result['blocked'])

    def test_cleanup_error_is_not_replaced_by_older_handled_policy_failure(self):
        (self.root / 'ledger.json').chmod(0o644)
        def failed_close(descriptor):
            info = os.fstat(descriptor)
            os.close(descriptor)
            if stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o644:
                raise OSError(errno.EIO, 'private-canary', '/private-canary')
        self.module.os = Proxy(os, close=failed_close)
        error, value = self.observed()
        self.assertIsInstance(error.__context__, OSError)
        self.assertIsInstance(error.__context__.__context__, self.module.RecoveryGuardStorageError)
        self.assert_fields(value, role='ledger', substage='ledger_read_cleanup', errno='EIO',
                           failure_type='OSError', node_kind=None, mode_matches=None)

    def test_wrapped_error_context_cycle_is_bounded_and_unknown(self):
        def denied(*args, **kwargs):
            raise OSError(errno.EACCES, 'private-canary')
        self.module.os = Proxy(os, open=denied)
        error, _ = self.observed()
        error.__context__ = error
        self.assertIsNone(self.binding.observe(error))

    def test_observer_performs_no_filesystem_calls_or_message_conversion(self):
        (self.root / 'ledger.json').chmod(0o644)
        try:
            asyncio.run(self.guard.status(transfer.IDENTITY))
        except self.module.RecoveryGuardStorageError as error:
            calls = []
            class NoIO:
                stat_result = os.stat_result
                def __getattr__(self, name):
                    calls.append(name)
                    raise AssertionError('observer_io_attempt')
            original = transfer.os
            transfer.os = NoIO()
            try:
                self.assertIsNotNone(self.binding.observe(error))
            finally:
                transfer.os = original
            self.assertEqual(calls, [])
        else:
            self.fail('fault_required')

    def test_wrong_source_modified_code_and_foreign_errors_are_unknown(self):
        with self.assertRaises(ValueError):
            transfer.SourceBinding(self.guard, STORAGE_RAW + b'\n')
        self.assertIsNone(self.binding.observe(ValueError('private-canary')))
        try:
            raise self.module.RecoveryGuardStorageError('private-canary')
        except self.module.RecoveryGuardStorageError as error:
            self.assertIsNone(self.binding.observe(error))
        original = self.module.RecoveryGuard._root_fd
        def replacement(self):
            return None
        self.module.RecoveryGuard._root_fd = replacement
        with self.assertRaises(ValueError):
            transfer.SourceBinding(self.guard, STORAGE_RAW)
        self.module.RecoveryGuard._root_fd = original

    def test_public_projection_rejects_unknown_fields_and_valid_looking_text(self):
        (self.root / 'ledger.json').chmod(0o644)
        _, value = self.observed()
        for key in value:
            for bad in ('private-canary', [], {}, 42):
                with self.subTest(key=key, bad=type(bad).__name__):
                    altered = dict(value, **{key: bad})
                    self.assertIsNone(transfer.public_observation(altered))
        self.assertIsNone(transfer.public_observation(dict(value, extra=False)))



class StorageExportIntegrationContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='owned-storage-export-')
        self.base = Path(self.temp.name).resolve()
        self.package = self.base / 'package'; self.package.mkdir()
        (self.package / 'findmy_recovery_guard.py').write_bytes(STORAGE_RAW)
        self.root = self.base / '.storage/homecircle_findmy/recovery_guard'
        module = types.ModuleType('owned_exact_export_seed')
        exec(compile(STORAGE_RAW, 'exact-export-seed', 'exec'), module.__dict__)
        guard = module.RecoveryGuard(self.root)
        async def seed():
            for _ in range(3):
                async with guard.attempt(transfer.IDENTITY) as attempt:
                    await attempt.before_dispatch(); await attempt.refused()
        asyncio.run(seed())
        self.token = 'b' * 32
        self.proof = self.base / 'proof.json'
        self.proof.write_bytes(transfer.canonical({'schema':1,'token':self.token,
            'generation':'before_restore','branch_commit':'a'*40,'postbackup_window':{}}))

    def tearDown(self):
        self.temp.cleanup()

    def invoke(self, failed=True):
        from contextlib import redirect_stdout, redirect_stderr
        import io
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(transfer,'PACKAGE',self.package),patch.object(transfer,'GUARD',self.root), \
                patch.object(transfer,'EXPORT_PROOF',self.proof),patch.object(transfer.sys,'argv',['-','export']), \
                patch.object(transfer.sys,'platform','linux'),patch.object(transfer.os,'geteuid',return_value=0), \
                redirect_stdout(stdout),redirect_stderr(stderr):
            if failed:
                with self.assertRaises(SystemExit) as error:transfer.cli()
                self.assertEqual(error.exception.code,1)
            else:
                transfer.cli()
        return stdout.getvalue().encode(), stderr.getvalue().encode()

    def test_actual_status_to_cli_to_host_preserves_only_exact_token_bound_stat_detail(self):
        self.root.parent.chmod(0o755)
        stdout, stderr = self.invoke()
        self.assertEqual(stdout,b'')
        labels=transfer.parse_export_failure(stderr,self.token)
        self.assertEqual(labels['stage'],'blocked_status')
        self.assertEqual(labels['failure_type'],'RecoveryGuardStorageError')
        detail=labels['storage_failure']
        self.assertEqual(detail,{'operation':'directory','substage':'private_directory_policy',
            'role':'private_parent','failure_type':'RecoveryGuardStorageError','errno':None,
            'node_kind':'directory','owner_matches_uid':True,'mode_matches':False,'single_link':None})
        value=controller.guard_export_observation({'exitcode':1,'signal':None,'truncated':False,
            'stdout':stdout,'stderr':stderr},self.token)
        self.assertEqual(value['helper_failure'],labels)
        self.assertIsNone(transfer.parse_export_failure(stderr,'c'*32))
        public=json.dumps(value)
        self.assertNotIn(str(self.base),public);self.assertNotIn(self.token,public)
        self.assertNotIn('Traceback',public)

    def test_source_binding_failure_omits_detail_and_keeps_original_failure(self):
        self.root.parent.chmod(0o755)
        with patch.object(transfer,'SourceBinding',side_effect=ValueError('PRIVATE-CANARY')):
            stdout,stderr=self.invoke()
        self.assertEqual(stdout,b'')
        self.assertEqual(transfer.parse_export_failure(stderr,self.token),
            {'stage':'blocked_status','failure_type':'RecoveryGuardStorageError'})
        self.assertNotIn(b'CANARY',stderr)

    def test_observer_failure_omits_detail_and_keeps_original_failure(self):
        self.root.parent.chmod(0o755)
        with patch.object(transfer.SourceBinding,'observe',side_effect=AssertionError('PRIVATE-CANARY')):
            stdout,stderr=self.invoke()
        self.assertEqual(stdout,b'')
        self.assertEqual(transfer.parse_export_failure(stderr,self.token),
            {'stage':'blocked_status','failure_type':'RecoveryGuardStorageError'})
        self.assertNotIn(b'CANARY',stderr)

    def test_actual_success_stdout_and_private_guard_bytes_are_unchanged(self):
        files=transfer.private_files(self.root)
        expected=transfer.canonical({'schema':1,'files':{name:base64.b64encode(raw).decode()
            for name,raw in files.items()}})+b'\n'
        # Only the Linux-root entry gate is emulated on macOS. Preserve the
        # actual private-file check against this temporary fixture's real UID.
        original_private_files = transfer.private_files
        real_uid = os.getuid()
        def local_private_files(root):
            with patch.object(transfer.os,'geteuid',return_value=real_uid):
                return original_private_files(root)
        with patch.object(transfer,'private_files',side_effect=local_private_files):
            stdout,stderr=self.invoke(failed=False)
        self.assertEqual(stdout,expected);self.assertEqual(stderr,b'')
        self.assertEqual(transfer.private_files(self.root),files)
        self.assertIsNone(transfer._export_storage_failure)

    def test_optional_metadata_is_strictly_scoped_and_rejects_canaries_and_bool_coercion(self):
        self.root.parent.chmod(0o755)
        _,stderr=self.invoke()
        labels=transfer.parse_export_failure(stderr,self.token)
        for key,value in [('stage','private_files'),('failure_type','ValueError')]:
            invalid=dict(labels,**{key:value})
            self.assertIsNone(transfer.export_failure_labels(invalid))
        for key,value in [('mode_matches',1),('owner_matches_uid',0),('role','PRIVATE-CANARY'),
                          ('errno','PRIVATE-CANARY'),('failure_type','PRIVATE-CANARY')]:
            invalid=dict(labels,storage_failure=dict(labels['storage_failure'],**{key:value}))
            self.assertIsNone(transfer.export_failure_labels(invalid))
        self.assertIsNone(transfer.export_failure_labels(dict(labels,private='PRIVATE-CANARY')))
        body=json.loads(stderr)
        duplicate=transfer.canonical(body).replace(b'"mode_matches":false',b'"mode_matches":false,"mode_matches":false')
        self.assertIsNone(transfer.parse_export_failure(duplicate,self.token))



class ManagedVersionContracts(unittest.TestCase):
    def test_initial_gate_requires_independent_exact_api_container_and_supervisor_versions(self):
        tree=ast.parse((controller.ROOT/'controller.py').read_bytes())
        owner=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='Controller')
        run=next(node for node in owner.body if isinstance(node,ast.FunctionDef) and node.name=='run')
        statements=[node for node in run.body if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call)
            and isinstance(node.value.func,ast.Name) and node.value.func.id=='require'
            and any(isinstance(arg,ast.Constant) and arg.value=='current_managed_environment_required'
                    for arg in node.value.args)]
        self.assertEqual(len(statements),1)
        actual=compile(ast.Module(body=statements,type_ignores=[]),'actual_initial_version_gate','exec')
        fields={'core_version_before':'2026.10.2','container_core_version_before':'2026.10.2',
                'supervisor_version_observed':'2026.10.3'}
        exec(actual,{'self':SimpleNamespace(**fields),'CORE':controller.CORE,'require':controller.require})
        for field in fields:
            wrong='2026.10.2' if field=='supervisor_version_observed' else '2026.10.3'
            for invalid in (wrong,None,False,True,'PRIVATE-CANARY'):
                with self.subTest(field=field,invalid=invalid),self.assertRaises(controller.Refused):
                    exec(actual,{'self':SimpleNamespace(**dict(fields,**{field:invalid})),
                                 'CORE':controller.CORE,'require':controller.require})
            missing=SimpleNamespace(**fields);delattr(missing,field)
            with self.subTest(field=field,missing=True),self.assertRaises((AttributeError,controller.Refused)):
                exec(actual,{'self':missing,'CORE':controller.CORE,'require':controller.require})

    def test_public_acceptor_requires_exact_core2_and_supervisor3_independently(self):
        host,phases=synthetic_success()
        self.assertEqual(gate.accept(host,phases)['outcome'],'passed')
        for field,wrong in [('actual_core','2026.10.3'),('actual_supervisor','2026.10.2')]:
            for invalid in (wrong,None,False,True,'PRIVATE-CANARY'):
                changed=deepcopy(host);changed[field]=invalid
                with self.subTest(field=field,invalid=invalid),self.assertRaises(ValueError):
                    gate.accept(changed,phases)
            changed=deepcopy(host);del changed[field]
            with self.subTest(field=field,missing=True),self.assertRaises(ValueError):
                gate.accept(changed,phases)

    def test_initial_environment_finish_projection_has_only_fixed_public_version_fields(self):
        tree=ast.parse((controller.ROOT/'controller.py').read_bytes())
        owner=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='Controller')
        finish=next(node for node in owner.body if isinstance(node,ast.FunctionDef) and node.name=='finish')
        expressions=[value for node in ast.walk(finish) if isinstance(node,ast.Dict)
            for key,value in zip(node.keys,node.values)
            if isinstance(key,ast.Constant) and key.value=='initial_managed_environment']
        self.assertEqual(len(expressions),1)
        actual=compile(ast.Expression(body=expressions[0]),'actual_finish_version_projection','eval')
        fields={'core_version_before':'2026.10.2','container_core_version_before':'2026.10.2',
                'supervisor_version_observed':'2026.10.3'}
        expected={'api_core':'2026.10.2','container_core':'2026.10.2','supervisor':'2026.10.3'}
        namespace={'self':SimpleNamespace(**fields),'public_core_version':controller.public_core_version}
        self.assertEqual(eval(actual,namespace),expected)
        for private in (None,False,123,{},['PRIVATE-CANARY'],'PRIVATE-CANARY',
                        '2026.10.2 PRIVATE-CANARY','https://example.invalid/PRIVATE-CANARY'):
            values={field:private for field in fields}
            result=eval(actual,{'self':SimpleNamespace(**values),'public_core_version':controller.public_core_version})
            self.assertEqual(result,dict.fromkeys(expected))
            self.assertNotIn('PRIVATE-CANARY',json.dumps(result))



class ExportBoundaryStageContracts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='synthetic-guard-export-stage-')
        self.base=Path(self.temp.name).resolve()
        self.package=self.base/'package';self.package.mkdir()
        self.path=self.package/'findmy_recovery_guard.py';self.path.write_bytes(STORAGE_RAW)
        self.root=self.base/'.storage/homecircle_findmy/recovery_guard'
        self.module=types.ModuleType('exact_guard_export_stage_seed')
        exec(compile(STORAGE_RAW,'exact-export-stage-seed','exec'),self.module.__dict__)
        self.guard=self.module.RecoveryGuard(self.root)
        self.token='b'*32
        self.proof=self.base/'proof.json'
        self.proof.write_bytes(transfer.canonical({'schema':1,'token':self.token,'generation':'before_restore',
            'branch_commit':'a'*40,'postbackup_window':{}}))

    def tearDown(self):
        self.temp.cleanup()

    def seed(self,count=3):
        async def seed():
            for _ in range(count):
                async with self.guard.attempt(transfer.IDENTITY) as attempt:
                    await attempt.before_dispatch();await attempt.refused()
        asyncio.run(seed())

    def bytes_before(self):
        return {path.name:path.read_bytes()for path in self.root.iterdir()}

    def invoke(self,failed):
        from contextlib import redirect_stdout,redirect_stderr
        import io
        stdout,stderr=io.StringIO(),io.StringIO()
        original=transfer.private_files
        real_uid=os.getuid()
        def local_files(root):
            with patch.object(transfer.os,'geteuid',return_value=real_uid):
                return original(root)
        runner=asyncio.run
        with patch.object(transfer,'PACKAGE',self.package),patch.object(transfer,'GUARD',self.root), \
                patch.object(transfer,'EXPORT_PROOF',self.proof),patch.object(transfer.sys,'argv',['-','export']), \
                patch.object(transfer.sys,'platform','linux'),patch.object(transfer.os,'geteuid',return_value=0), \
                patch.object(transfer,'private_files',side_effect=local_files), \
                patch.object(transfer.asyncio,'run',wraps=runner)as calls,redirect_stdout(stdout),redirect_stderr(stderr):
            if failed:
                with self.assertRaises(SystemExit)as stopped:transfer.cli()
                self.assertEqual(stopped.exception.code,1)
            else:
                transfer.cli()
        return stdout.getvalue().encode(),stderr.getvalue().encode(),calls.call_count

    def assert_private_free(self,stderr,stage):
        labels=transfer.parse_export_failure(stderr,self.token)
        self.assertEqual(labels,{'stage':stage,'failure_type':'ValueError'})
        public=controller.guard_export_observation({'exitcode':1,'signal':None,'truncated':False,
            'stdout':b'','stderr':stderr},self.token)
        self.assertEqual(public['helper_failure'],labels)
        rendered=json.dumps(public)
        for private in ('PRIVATE-CANARY',str(self.base),self.token,'Traceback'):
            self.assertNotIn(private,rendered)
        self.assertEqual(set(labels),{'stage','failure_type'})

    def test_valid_exact_three_rejection_export_calls_status_once_without_guard_mutation(self):
        self.seed();before=self.bytes_before()
        stdout,stderr,calls=self.invoke(failed=False)
        self.assertEqual(calls,1);self.assertEqual(stderr,b'')
        self.assertEqual(transfer.decode(stdout.strip()),before)
        self.assertEqual(self.bytes_before(),before)
        self.assertEqual(transfer._export_stage,'encode')
        self.assertIsNone(transfer._export_storage_failure)

    def test_missing_symlink_hash_and_load_failures_have_precise_private_free_stages(self):
        self.seed();before=self.bytes_before()
        for fault,stage in [('missing','guard_module_file'),('symlink','guard_module_file'),
                            ('hash','guard_module_hash'),('load','guard_module_load')]:
            with self.subTest(fault=fault):
                if self.path.is_symlink()or self.path.exists():self.path.unlink()
                self.path.write_bytes(STORAGE_RAW)
                if fault=='missing':self.path.unlink()
                elif fault=='symlink':
                    other=self.package/'synthetic_source.py';other.write_bytes(STORAGE_RAW)
                    self.path.unlink();self.path.symlink_to(other)
                elif fault=='hash':self.path.write_bytes(STORAGE_RAW+b'\n')
                if fault=='load':
                    with patch.object(transfer.importlib.util,'module_from_spec',side_effect=ValueError('PRIVATE-CANARY')):
                        stdout,stderr,calls=self.invoke(failed=True)
                else:stdout,stderr,calls=self.invoke(failed=True)
                self.assertEqual(stdout,b'');self.assertEqual(calls,0)
                self.assert_private_free(stderr,stage)
                self.assertEqual(self.bytes_before(),before)

    def test_returned_two_rejection_status_is_refused_at_validation_without_mutation(self):
        self.seed(2);before=self.bytes_before()
        stdout,stderr,calls=self.invoke(failed=True)
        self.assertEqual(stdout,b'');self.assertEqual(calls,1)
        self.assert_private_free(stderr,'blocked_status_validation')
        self.assertEqual(self.bytes_before(),before)
        self.assertIsNone(transfer._export_storage_failure)

    def test_new_stage_catalog_and_host_projection_refuse_unlisted_or_private_metadata(self):
        for stage in ('guard_module_file','guard_module_hash','guard_module_load','blocked_status_validation'):
            value={'schema':1,'kind':'homecircle_guard_export_failure','token':self.token,
                   'stage':stage,'failure_type':'ValueError'}
            self.assert_private_free(transfer.canonical(value),stage)
            self.assertIsNone(transfer.parse_export_failure(transfer.canonical(dict(value,private='PRIVATE-CANARY')),self.token))
            self.assertIsNone(transfer.export_failure_labels({'stage':stage,'failure_type':'ValueError','storage_failure':{}}))
        for stage in (None,False,1,'PRIVATE-CANARY','guard_module_file PRIVATE-CANARY'):
            self.assertIsNone(transfer.export_failure_labels({'stage':stage,'failure_type':'ValueError'}))

    def test_diagnostic_stage_assignments_preserve_original_actual_source_and_status_checks(self):
        tree=ast.parse(Path(transfer.__file__).read_bytes())
        expected={'actual_guard': 'a8e6df5a304a4ed8e8e2d7c5cdf69e4e30b03860d93f6b952480c770b7fa7ac3', 'blocked_status': 'df270636257fde6605a6de668242df5e7e60793b3bf27357f089d25b318eb4ec'}
        for name,digest in expected.items():
            node=next(node for node in tree.body if isinstance(node,ast.FunctionDef)and node.name==name)
            for statement in node.body:
                if isinstance(statement,ast.Global):statement.names.remove('_export_stage')
            node.body=[statement for statement in node.body if not(isinstance(statement,ast.Assign)
                and len(statement.targets)==1 and isinstance(statement.targets[0],ast.Name)
                and statement.targets[0].id=='_export_stage')]
            self.assertEqual(hashlib.sha256(ast.dump(node).encode()).hexdigest(),digest)
        status=next(node for node in tree.body if isinstance(node,ast.FunctionDef)and node.name=='blocked_status')
        calls=[node for node in ast.walk(status)if isinstance(node,ast.Call)
               and isinstance(node.func,ast.Attribute)and node.func.attr=='status']
        self.assertEqual(len(calls),1)



class GuestStagingOwnerContracts(unittest.TestCase):
    def actual_prepared_archive(self,filtered):
        import io
        from types import MethodType
        with tempfile.TemporaryDirectory(prefix='synthetic-actual-staging-')as directory:
            candidate=controller.ROOT/'payload/homecircle.zip'
            inventory=json.loads((controller.ROOT/'payload/inventory.json').read_bytes())['files']
            host=controller.Controller(SimpleNamespace(branch_commit='a'*40,candidate_zip=candidate))
            host.private=Path(directory).resolve();host.config_path='/mnt/data/supervisor/homeassistant'
            writes={};host.stop_core=Mock();host.verify_candidate=Mock()
            host.guest_write=lambda path,raw:writes.__setitem__(path,raw)
            def guest(command,seconds):
                if command.startswith('sha256sum '):
                    return (hashlib.sha256(writes[controller.GUEST_ROOT+'/staging.tgz']).hexdigest()+'  staging.tgz\n').encode()
                return b''
            host.guest=guest
            if not filtered:
                tree=ast.parse((controller.ROOT/'controller.py').read_bytes())
                cls=next(node for node in tree.body if isinstance(node,ast.ClassDef)and node.name=='Controller')
                method=next(node for node in cls.body if isinstance(node,ast.FunctionDef)and node.name=='prepare')
                removed=0
                for node in ast.walk(method):
                    if isinstance(node,ast.Call)and isinstance(node.func,ast.Attribute)and node.func.attr=='add':
                        previous=len(node.keywords);node.keywords=[key for key in node.keywords if key.arg!='filter']
                        removed+=previous-len(node.keywords)
                self.assertEqual(removed,1)
                namespace=dict(controller.__dict__)
                exec(compile(ast.Module(body=[method],type_ignores=[]),'actual_pre_fix_prepare','exec'),namespace)
                host.prepare=MethodType(namespace['prepare'],host)
            mask=os.umask(0o077)
            try:host.prepare(inventory)
            finally:os.umask(mask)
            raw=writes[controller.GUEST_ROOT+'/staging.tgz']
            with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz')as archive:
                return {item.name:{'uid':item.uid,'gid':item.gid,'uname':item.uname,'gname':item.gname,
                    'mode':item.mode,'type':item.type,'size':item.size,'linkname':item.linkname,
                    'pax_ownership':{key:value for key,value in item.pax_headers.items()if key in {'uid','gid','uname','gname'}},
                    'payload':archive.extractfile(item).read()if item.isfile()else None}for item in archive.getmembers()}

    def test_actual_prepare_root_ownership_fixes_foreign_private_metadata_without_payload_or_mode_changes(self):
        self.assertNotEqual(os.getuid(),0,'nonroot_native_contract_caller_required')
        before=self.actual_prepared_archive(False);after=self.actual_prepared_archive(True)
        self.assertEqual(set(before),set(after))
        for name in before:
            with self.subTest(name=name):
                self.assertEqual(before[name]['uid'],os.getuid())
                self.assertEqual(before[name]['gid'],os.getgid())
                self.assertEqual({key:after[name][key]for key in ('uid','gid','uname','gname','pax_ownership')},
                                 {'uid':0,'gid':0,'uname':'','gname':'','pax_ownership':{}})
                for key in ('mode','type','size','linkname','payload'):
                    self.assertEqual(before[name][key],after[name][key])
        self.assertEqual(before['custom_components']['mode'],0o700)
        self.assertEqual(before['custom_components/homecircle']['mode'],0o700)
        self.assertEqual(before['custom_components/homecircle/findmy_recovery_guard.py']['mode'],0o600)
        inventory=json.loads((controller.ROOT/'payload/inventory.json').read_bytes())['files']
        self.assertEqual(len(inventory),113)
        for name,expected in inventory.items():
            raw=after['custom_components/homecircle/'+name]['payload']
            self.assertEqual({'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},expected)
        self.assertEqual(hashlib.sha256(after['custom_components/homecircle/findmy_recovery_guard.py']['payload']).hexdigest(),transfer.MODULE_SHA)

    def test_ownership_filter_removes_numeric_names_and_pax_overrides_preserving_all_other_metadata(self):
        item=tarfile.TarInfo('custom_components/homecircle/synthetic.py')
        item.uid=1001;item.gid=1002;item.uname='PRIVATE-CANARY';item.gname='PRIVATE-CANARY'
        item.mode=0o600;item.size=3;item.mtime=123.25;item.type=tarfile.REGTYPE
        item.pax_headers={'uid':'1001','gid':'1002','uname':'PRIVATE-CANARY','gname':'PRIVATE-CANARY',
                          'mtime':'123.25','comment':'synthetic retained metadata'}
        preserved={key:getattr(item,key)for key in ('name','mode','type','size','mtime','linkname','devmajor','devminor')}
        result=controller.guest_staging_owner(item)
        self.assertIs(result,item)
        self.assertEqual((item.uid,item.gid,item.uname,item.gname),(0,0,'',''))
        self.assertEqual(item.pax_headers,{'mtime':'123.25','comment':'synthetic retained metadata'})
        self.assertEqual({key:getattr(item,key)for key in preserved},preserved)

    def test_serialized_pax_ownership_cannot_override_normalized_root_headers(self):
        import io
        item=tarfile.TarInfo('custom_components/homecircle/synthetic.py')
        item.uid=item.gid=0;item.uname=item.gname=''
        item.mode=0o600;item.size=3
        item.pax_headers={'uid':'1001','gid':'1002','uname':'PRIVATE-CANARY','gname':'PRIVATE-CANARY'}
        def roundtrip(value):
            stream=io.BytesIO()
            with tarfile.open(fileobj=stream,mode='w',format=tarfile.PAX_FORMAT)as archive:
                archive.addfile(value,io.BytesIO(b'abc'))
            with tarfile.open(fileobj=io.BytesIO(stream.getvalue()),mode='r:')as archive:
                member=archive.getmembers()[0]
                return member,archive.extractfile(member).read()
        unfiltered,payload=roundtrip(deepcopy(item))
        self.assertEqual((unfiltered.uid,unfiltered.gid),(1001,1002))
        normalized,payload2=roundtrip(controller.guest_staging_owner(deepcopy(item)))
        self.assertEqual((normalized.uid,normalized.gid,normalized.uname,normalized.gname),(0,0,'',''))
        self.assertEqual(normalized.mode,0o600);self.assertEqual(payload,payload2)
        self.assertFalse(set(normalized.pax_headers)&{'uid','gid','uname','gname'})

    def test_ownership_filter_refuses_links_special_members_and_outside_owned_staging_scope(self):
        for name,kind in [('custom_components/homecircle/link',tarfile.SYMTYPE),
                          ('custom_components/homecircle/link',tarfile.LNKTYPE),
                          ('custom_components/homecircle/fifo',tarfile.FIFOTYPE),
                          ('custom_components/homecircle/device',tarfile.CHRTYPE),
                          ('../private',tarfile.REGTYPE),('/private',tarfile.REGTYPE),
                          ('other/synthetic.py',tarfile.REGTYPE),('custom_components/../private',tarfile.REGTYPE)]:
            item=tarfile.TarInfo(name);item.type=kind;item.uid=1001
            with self.subTest(name=name,kind=kind),self.assertRaises(controller.Refused):
                controller.guest_staging_owner(item)
            self.assertEqual(item.uid,1001)
