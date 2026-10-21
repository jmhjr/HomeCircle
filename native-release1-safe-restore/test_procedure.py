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
