"""Bounded stdlib contracts; no provider/native imports or VM execution."""
import ast
import asyncio
import importlib.util
from pathlib import Path
import types
import unittest

import controller as c

ROOT=Path(__file__).resolve().parent


def boundary_module():
    path=ROOT/'guest_helper/_ordinary_boundary.py'
    spec=importlib.util.spec_from_file_location('_ordinary_boundary_contract',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module._state={'installed':True,'counts':dict.fromkeys(module.COUNTERS,0),
        'patches':[],'loaded':set(),'life360_sessions':set()}
    return module


class OrdinaryContracts(unittest.TestCase):
    def test_frozen_candidate_binding(self):
        self.assertEqual(c.checked_binding(c.PINS),c.PINS)
        self.assertEqual(c.CANDIDATE_FILES,113)

    def test_binding_rejects_boolean_file_count(self):
        with self.assertRaises(c.Refused):c.checked_binding({**c.PINS,'candidate_files':True})

    def test_binding_rejects_unprepared_packet(self):
        with self.assertRaises(c.Refused):c.checked_binding({**c.PINS,'prepared':False})

    def test_binding_rejects_private_extra(self):
        with self.assertRaises(c.Refused):c.checked_binding({**c.PINS,'secret':'synthetic'})

    def test_all_product_zip_bytes_match_frozen_inventory(self):
        import json
        actual=c.check_archive(ROOT/'payload/homecircle.zip',c.CANDIDATE_SHA,113)
        self.assertEqual(actual,json.loads((ROOT/'payload/inventory.json').read_bytes())['files'])

    def test_prepare_never_mutates_manifest(self):
        source=(ROOT/'controller.py').read_text();tree=ast.parse(source)
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Controller')
        fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='prepare')
        calls=[n for n in ast.walk(fn) if isinstance(n,ast.Call)]
        self.assertFalse(any(isinstance(n.func,ast.Attribute) and n.func.attr in {'write_text','write_bytes','append'} for n in calls))
        self.assertIn('ordinary_qa_dependency_forbidden',ast.get_source_segment(source,fn))

    def test_prepared_dependency_install_forbidden(self):
        with self.assertRaises(c.Refused):object.__new__(c.Controller).prepare_dependencies()

    def test_guard_export_and_import_forbidden(self):
        value=object.__new__(c.Controller)
        for fn in (value.preserve_latest_guard,value.fresh_restore_control):
            with self.assertRaises(c.Refused):fn()

    def test_parent_initializer_installs_fence(self):
        tree=ast.parse((ROOT/'guest_helper/__init__.py').read_bytes())
        self.assertIsInstance(tree.body[1],ast.ImportFrom)
        self.assertEqual(tree.body[1].names[0].name,'_ordinary_boundary')
        self.assertEqual(tree.body[2].value.func.attr,'install')

    def test_fence_imports_no_product(self):
        tree=ast.parse((ROOT/'guest_helper/_ordinary_boundary.py').read_bytes())
        imports=[n for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))]
        self.assertFalse(any(isinstance(n,ast.ImportFrom) and n.module and n.module.startswith('custom_components.homecircle') for n in imports))

    def test_external_http_refused_before_transport(self):
        b=boundary_module()
        self.assertIsNone(b.local_kind('GET','https://example.invalid/account'))
        with self.assertRaises(b.StartupBoundaryRefused):b.deny('other_external_requests_denied','https://example.invalid/account')
        self.assertEqual(b._state['counts']['other_external_requests_denied'],1)

    def test_local_http_allowlist_is_exact(self):
        b=boundary_module()
        self.assertEqual(b.local_kind('GET','http://supervisor/network/info'),'supervisor_requests_allowed')
        self.assertEqual(b.local_kind('GET','http://127.0.0.1:8123/api/image/serve/'+'c'*32+'/original'),'qa_static_requests_allowed')
        for url in ('http://127.0.0.1:8124/api/image/serve/'+'c'*32+'/original','http://127.0.0.1:8123/auth/token',
            'http://user:pw@supervisor/network/info','https://supervisor/network/info'):
            self.assertIsNone(b.local_kind('GET',url))

    def test_socket_connect_and_dns_refused(self):
        b=boundary_module()
        for event,args in (('socket.connect',(None,('203.0.113.4',443))),
            ('socket.sendto',(None,('203.0.113.4',53))),('socket.getaddrinfo',('example.invalid',443,0,0,0))):
            with self.assertRaises(b.StartupBoundaryRefused):b.audit(event,args)
        self.assertEqual(b._state['counts']['socket_external_attempts_denied'],3)

    def test_ordinary_uv_install_observed_without_argument_changes(self):
        b=boundary_module()
        argv=[b.sys.executable,'-m','uv','pip','install','--quiet','life360==7.2.0',
            '--constraint','/usr/local/lib/python3.14/site-packages/homeassistant/package_constraints.txt']
        original=list(argv)
        b.audit('subprocess.Popen',(b.sys.executable,argv,None,{}))
        self.assertEqual(argv,original)
        self.assertEqual(b._state['counts']['ordinary_uv_installs_observed'],1)

    def test_real_guard_before_dispatch_is_observed_not_replaced(self):
        b=boundary_module();calls=[]
        class Attempt:
            async def before_dispatch(self):calls.append('real');return 7
        b.loaded(types.SimpleNamespace(RecoveryAttempt=Attempt),'guard')
        self.assertEqual(asyncio.run(Attempt().before_dispatch()),7)
        self.assertEqual(calls,['real'])
        self.assertEqual(b._state['counts']['recovery_before_dispatch_calls'],1)

    def test_escrow_recovery_never_reaches_original(self):
        b=boundary_module()
        class Escrow:
            async def _command(self,*args,**kwargs):raise AssertionError('original_transport_called')
        b.loaded(types.SimpleNamespace(AsyncEscrowProxy=Escrow),'escrow')
        with self.assertRaises(b.StartupBoundaryRefused):asyncio.run(Escrow()._command('recover'))
        self.assertEqual(b._state['counts']['recovery_command_calls'],1)

    def test_guard_seed_uses_saved_account_and_cache(self):
        source=(ROOT/'storage_transfer.py').read_text();tree=ast.parse(source)
        fn=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='guard_counter')
        body=ast.get_source_segment(source,fn)
        self.assertIn("account_metadata(record)[1]['account_identity']",body)
        self.assertIn('RecoveryGuard(GUARD_ROOT, WITNESS_ROOT)',body)
        self.assertIn('await guard.reset(identity)',body)
        self.assertIn('RecoveryGuardReviewRequired',body)

    def test_seed_guard_precedes_verified_title_update(self):
        from contextlib import asynccontextmanager
        source=ast.parse((ROOT/'storage_transfer.py').read_bytes())
        fn=next(n for n in source.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='guard_counter')
        class Guard:
            def __init__(self,*paths):self.count=0;self.reset_count=0
            async def reset(self,identity):self.reset_count+=1
            async def status(self,identity):
                return {'rejected':self.count,'uncertain':0,'pending':0,'verified':0,
                    'unresolved':self.count,'limit':3,'blocked':self.count>=3,'review_required':False}
            @asynccontextmanager
            async def attempt(self,identity):
                yield self
            async def before_dispatch(self):self.count+=1
            async def refused(self):pass
        guard=Guard()
        values={'config_store':lambda:{'data':{'entries':[{'domain':'homecircle','title':'Synthetic saved storage QA'}]}},
            'account_metadata':lambda record:('account',{'account_identity':'a'*64}),
            'require':lambda ok:self.assertTrue(ok),'GUARD_ROOT':'ledger','WITNESS_ROOT':'cache',
            'ACCEPTED_TITLE':'Synthetic saved storage verified'}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'guard_counter_contract','exec'),values)
        actual=asyncio.run(values['guard_counter'](types.SimpleNamespace(RecoveryGuard=lambda *paths:guard),2,advance=2))
        self.assertEqual(actual,2)
        self.assertEqual(guard.reset_count,1)

    def test_archive_requires_cache_absence_and_parent_helper_bytes(self):
        tree=ast.parse((ROOT/'controller.py').read_bytes())
        fn=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='inspect_backup')
        node=next(n for n in ast.walk(fn) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='script' for t in n.targets))
        program=ast.literal_eval(node.value)
        self.assertIn('require(not name.startswith("data/.cache/"))',program)
        self.assertIn('key=name[len(qa):]',program)
        self.assertIn('require(helper==inputs["helper_files_sha256"]',program)
        self.assertIn('require(not deps and inputs["dependency_fixture"] is None',program)
        ast.parse(program.replace('__BASELINE__','{}').replace('__JOINS__',"'a'"))


    def test_seed_stays_projection_equal_after_canonical_roundtrip(self):
        import json,re,zipfile
        from copy import deepcopy
        from unittest.mock import patch
        spec=importlib.util.spec_from_file_location('_ordinary_seed_contract',ROOT/'storage_transfer.py')
        seed=importlib.util.module_from_spec(spec);spec.loader.exec_module(seed)
        with zipfile.ZipFile(ROOT/'payload/homecircle.zip') as archive:
            identity_source=archive.read('findmy_identity.py')
            item_source=archive.read('findmy_items.py')
            provider_source=archive.read('findmy_provider.py')
            const_source=archive.read('const.py')
        identity_values={}
        exec(compile(identity_source,'<bound_pure_identity>','exec'),identity_values)
        identity=types.SimpleNamespace(**identity_values)
        real_token=seed.secrets.token_hex;calls=[]
        def adversarial_token(size):
            if size==16:
                calls.append(1)
                if len(calls) in (6,7,8):
                    return ('b','a','c')[len(calls)-6]*32
            return real_token(size)
        with patch.object(seed.secrets,'token_hex',side_effect=adversarial_token):
            record,selection,*_unused=seed.new_synthetic(identity)
        saved=json.loads(json.dumps(record['options'],sort_keys=True))
        account=next(iter(saved['findmy_accounts'].values()))
        self.assertEqual(list(account['items']),['a'*32,'b'*32])
        registry_rows={row['entity_id']:types.SimpleNamespace(platform='homecircle',unique_id=row['unique_id'])
            for row in selection['joins']}
        class Registry:
            def async_get(self,entity):return registry_rows.get(entity)
            def async_get_entity_id(self,domain,platform,unique):
                return next((key for key,row in registry_rows.items() if row.unique_id==unique),None)
        constants={}
        for node in ast.parse(const_source).body:
            if isinstance(node,ast.Assign):
                for target in node.targets:
                    if isinstance(target,ast.Name) and target.id.startswith('CONF_'):
                        try:constants[target.id]=ast.literal_eval(node.value)
                        except ValueError:pass
        item_fn=next(n for n in ast.parse(item_source).body if isinstance(n,ast.FunctionDef) and n.name=='item_config')
        tracker_fn=next(n for n in ast.parse(provider_source).body if isinstance(n,ast.FunctionDef) and n.name=='tracker_unique_id')
        values={'deepcopy':deepcopy,'er':types.SimpleNamespace(async_get=lambda hass:Registry()),
            'PREFIX':'homecircle_findmy_','re':re,'VaultError':ValueError,**constants}
        exec(compile(ast.Module(body=[tracker_fn,item_fn],type_ignores=[]),'<bound_pure_item_projection>','exec'),values)
        before=deepcopy(saved)
        self.assertEqual(values['item_config'](None,saved),saved)
        self.assertEqual(saved,before)


class FailureDiagnosticContracts(unittest.TestCase):
    def capture_probe_error(self,label):
        path=ROOT/'guest_helper/homecircle_safe_restore_qa/dependency_probe.py'
        tree=ast.parse(path.read_bytes())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='require')
        values={}
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(path.resolve()),'exec'),values)
        try:values['require'](False,label)
        except ValueError as error:return error
        raise AssertionError('probe_error_not_raised')

    def test_known_probe_valueerror_retains_only_bound_code_and_frame(self):
        error=self.capture_probe_error('qa_dependency_graph_version')
        projected=c._DIAGNOSTICS.project(error,c._DIAGNOSTIC_ROOT,type('Refused',(RuntimeError,),{}))
        self.assertEqual(projected['failure_type'],'ValueError')
        self.assertEqual(projected['failure_code'],'qa_dependency_graph_version')
        self.assertEqual(len(projected['frames']),1)
        self.assertEqual(projected['frames'][0]['source'],'dependency_probe')
        self.assertEqual(projected['frames'][0]['function'],'require')

    def test_private_valueerror_text_is_discarded(self):
        import json
        secret='https://example.invalid/?password=QA-PRIVATE-DO-NOT-RETAIN'
        error=self.capture_probe_error(secret)
        projected=c._DIAGNOSTICS.project(error,c._DIAGNOSTIC_ROOT,type('Refused',(RuntimeError,),{}))
        self.assertIsNone(projected['failure_code'])
        self.assertNotIn(secret,json.dumps(projected))
        self.assertNotIn('password',json.dumps(projected))
        self.assertLessEqual(len(projected['frames']),8)

    def test_unbound_frame_or_private_extra_is_refused(self):
        value={'failure_type':'ValueError','failure_code':None,
            'frames':[{'source':'dependency_probe','function':'private_unreviewed_name','line':1}]}
        with self.assertRaises(ValueError):c._DIAGNOSTICS.checked(value,c._DIAGNOSTIC_ROOT)
        with self.assertRaises(ValueError):c._DIAGNOSTICS.checked({**value,'secret':'private'},c._DIAGNOSTIC_ROOT)

    def test_dependency_diagnostic_metadata_refuses_unknown_package_and_version(self):
        rows={name:{'available':False,'version':None,'constraints_satisfied':False} for name in c.base.CLOSURE}
        self.assertEqual(c._DIAGNOSTICS.checked_metadata(rows,c._DIAGNOSTIC_ROOT),rows)
        with self.assertRaises(ValueError):
            c._DIAGNOSTICS.checked_metadata({**rows,'private_unknown':rows['protobuf']},c._DIAGNOSTIC_ROOT)
        rows['protobuf']={'available':True,'version':'https://example.invalid/?password=private','constraints_satisfied':False}
        with self.assertRaises(ValueError):c._DIAGNOSTICS.checked_metadata(rows,c._DIAGNOSTIC_ROOT)

    def test_dependency_diagnostic_version_redacts_unknown_input(self):
        path=ROOT/'guest_helper/homecircle_safe_restore_qa/dependency_probe.py'
        spec=importlib.util.spec_from_file_location('_ordinary_probe_contract',path)
        probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
        self.assertEqual(probe.public_version('7.36.0'),'7.36.0')
        for value in ('https://example.invalid/?secret=private','private',7.36,None):
            self.assertIsNone(probe.public_version(value))

    def test_failed_phase_is_projected_before_raising(self):
        import json,tempfile
        with tempfile.TemporaryDirectory() as folder:
            control=c.Controller(types.SimpleNamespace(branch_commit='b'*40,output=Path(folder)/'unused'))
            control.public=Path(folder);control.config_path='/synthetic'
            control.assert_network_closed=lambda:None
            control.guest_write=lambda *args:None
            control.guest=lambda *args:b''
            control.initial_managed_boot=lambda:None
            control.grant_closed_boot=lambda *args:None
            control.remaining=lambda maximum:1
            receipt={'schema':1,'token':control.phase_token,'phase':'baseline_enabled',
                'generation':'before_restore','branch_commit':'b'*40,'outcome':'failed',
                'stage':'normal_dependencies','failure_type':'ValueError',
                'failure_code':'qa_dependency_graph_version','frames':[],
                'dependency_metadata':{name:{'available':False,'version':None,'constraints_satisfied':False}
                    for name in c.base.CLOSURE},
                'private_secret':'QA-PRIVATE-DO-NOT-RETAIN'}
            control.guest_read=lambda *args:json.dumps(receipt).encode()
            with self.assertRaisesRegex(c.Refused,'ordinary_guest_phase_failed'):
                control.phase('baseline_enabled',start=True)
            public=json.loads((Path(folder)/'baseline_enabled.json').read_bytes())
            self.assertEqual(public['failure_code'],'qa_dependency_graph_version')
            self.assertEqual(public['stage'],'normal_dependencies')
            self.assertEqual(control.guest_failures,[public])
            self.assertNotIn('private_secret',public)


    def test_automatic_restored_failure_stops_after_one_bound_receipt(self):
        import json,tempfile
        with tempfile.TemporaryDirectory() as folder:
            control=c.Controller(types.SimpleNamespace(branch_commit='b'*40,output=Path(folder)/'unused'))
            control.public=Path(folder);control.config_path='/synthetic'
            control.phases=[{'process':{'start_ticks':1}},{'process':{'start_ticks':2}}]
            control.network_boundary={'link_closed':True}
            control.remaining=lambda maximum:1
            process={'pid':123,'start_ticks':3}
            receipt={'schema':1,'token':control.phase_token,'phase':'automatic_restored_enabled',
                'generation':'before_restore','branch_commit':'b'*40,'process':process,
                'outcome':'failed','closed_boot_grant_verified':False,'stage':'normal_dependencies','failure_type':'ValueError',
                'failure_code':'qa_dependency_graph_version','frames':[],
                'dependency_metadata':{name:{'available':False,'version':None,'constraints_satisfied':False}
                    for name in c.base.CLOSURE}}
            calls=[]
            def read(*args):calls.append(1);return json.dumps(receipt).encode()
            control.guest_read=read
            with self.assertRaisesRegex(c.Refused,'ordinary_guest_automatic_phase_failed'):
                control.restored_boot_barrier()
            self.assertEqual(calls,[1])
            public=json.loads((Path(folder)/'automatic_restored_enabled.json').read_bytes())
            self.assertEqual(public['process'],process)
            self.assertIs(public['closed_boot_grant_verified'],False)
            self.assertEqual(public['failure_code'],'qa_dependency_graph_version')
            self.assertEqual(control.guest_failures,[public])


class StartupImportOrderContracts(unittest.TestCase):
    def test_actual_guard_lazy_import_discriminates_strict_startup_shape(self):
        import importlib,json,sys,tempfile,zipfile
        from unittest.mock import patch
        boundary=boundary_module()
        finder=boundary.BoundaryFinder()
        boundary._state.update(finder=finder,loaded=set(boundary.TARGETS.values())-{'guard'})
        boundary._state['counts'].update(life360_sessions_created=1,life360_requests_denied=1,
            apple_legacy_requests_denied=1)
        source_path=ROOT/'guest_helper/homecircle_safe_restore_qa/__init__.py'
        source=ast.parse(source_path.read_bytes())
        fn=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='startup_receipt')
        def check(ok,label):
            if not ok:raise c.Refused(label)
        values={'startup_boundary':types.SimpleNamespace(snapshot=boundary.snapshot),'check':check}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),str(source_path),'exec'),values)
        with tempfile.TemporaryDirectory() as folder:
            package=Path(folder).resolve()/'homecircle';package.mkdir(mode=0o700)
            with zipfile.ZipFile(ROOT/'payload/homecircle.zip') as archive:
                source=archive.read('findmy_recovery_guard.py')
            import hashlib
            inventory=json.loads((ROOT/'payload/inventory.json').read_bytes())['files']
            self.assertEqual(hashlib.sha256(source).hexdigest(),inventory['findmy_recovery_guard.py']['sha256'])
            (package/'findmy_recovery_guard.py').write_bytes(source)
            parent=types.ModuleType('custom_components');parent.__path__=[str(package.parent)]
            child=types.ModuleType('custom_components.homecircle');child.__path__=[str(package)]
            with patch.dict(sys.modules,{'custom_components':parent,'custom_components.homecircle':child,
                    'custom_components._ordinary_boundary':boundary}):
                sys.modules.pop('custom_components.homecircle.findmy_recovery_guard',None)
                sys.meta_path.insert(0,finder)
                try:
                    before=boundary.snapshot()
                    self.assertEqual(before['loaded_target_kinds'],sorted(set(boundary.TARGETS.values())-{'guard'}))
                    with self.assertRaisesRegex(c.Refused,'qa_startup_boundary_shape'):
                        values['startup_receipt']()
                    guard=importlib.import_module('custom_components.homecircle.findmy_recovery_guard')
                    self.assertEqual(Path(guard.__file__).resolve(),package/'findmy_recovery_guard.py')
                    after=values['startup_receipt']()
                    self.assertEqual(after['loaded_target_kinds'],sorted(boundary.TARGETS.values()))
                    self.assertEqual({k:v for k,v in before.items() if k!='loaded_target_kinds'},
                        {k:v for k,v in after.items() if k!='loaded_target_kinds'})
                    self.assertEqual(len(boundary._state['patches']),1)
                    self.assertEqual(boundary._state['patches'][0][1],'before_dispatch')
                finally:sys.meta_path.remove(finder)


class AtomicHandshakeContracts(unittest.TestCase):
    def publication_files(self,folder):
        import json,hashlib
        root=Path(folder).resolve()
        old=json.dumps({'schema':1,'proof':'old'},sort_keys=True).encode()
        new=json.dumps({'schema':1,'proof':'new-complete'},sort_keys=True).encode()
        target=root/'inputs.json';target.write_bytes(old);target.chmod(0o600)
        name='.inputs-atomic-'+'a'*32
        temporary=root/name;temporary.write_bytes(new);temporary.chmod(0o600)
        return root,target,temporary,old,new,hashlib.sha256(new).hexdigest()

    def test_old_guest_writer_exposes_a_truncate_gap(self):
        import base64,json,tempfile
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'inputs.json';path.write_bytes(b'{"schema":1,"proof":"old"}');path.chmod(0o600)
            gap=[];handles={}
            class QGA:
                def call(self,name,args):
                    if name=='guest-file-open':
                        handles[1]=path.open('wb')
                        try:json.loads(path.read_bytes())
                        except json.JSONDecodeError:gap.append(True)
                        return 1
                    if name=='guest-file-write':
                        raw=base64.b64decode(args['buf-b64']);handles[1].write(raw);return {'count':len(raw)}
                    if name=='guest-file-flush':handles[1].flush();return {}
                    if name=='guest-file-close':handles[1].close();return {}
                    raise AssertionError('unexpected_qga_call')
            control=object.__new__(c.Controller);control.qga=QGA();control.remaining=lambda maximum:1
            c.base.Controller.guest_write(control,str(path),b'{"schema":1,"proof":"new"}')
            self.assertEqual(gap,[True])
            self.assertEqual(json.loads(path.read_bytes())['proof'],'new')

    def test_atomic_publication_preserves_complete_old_and_new_json(self):
        import json,tempfile
        with tempfile.TemporaryDirectory() as folder:
            root,target,temporary,old,new,digest=self.publication_files(folder)
            with target.open('rb') as reader:
                self.assertEqual(c.control_publication.publish(root,temporary.name,digest),c.control_publication.RESULT)
                self.assertEqual(reader.read(),old)
            self.assertEqual(target.read_bytes(),new)
            self.assertEqual(json.loads(target.read_bytes())['proof'],'new-complete')
            self.assertFalse(temporary.exists())

    def test_atomic_publication_refuses_wrong_hash_without_replacement(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            root,target,temporary,old,_new,_digest=self.publication_files(folder)
            with self.assertRaises(ValueError):c.control_publication.publish(root,temporary.name,'0'*64)
            self.assertEqual(target.read_bytes(),old)
            self.assertTrue(temporary.exists())

    def test_post_grant_reload_uses_new_snapshot_and_checks_identity(self):
        source=ast.parse((ROOT/'guest_helper/homecircle_safe_restore_qa/__init__.py').read_bytes())
        fn=next(n for n in source.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='reload_granted_inputs')
        process={'pid':123,'start_ticks':4}
        old={'source_commit':'a'*40,'candidate_sha256':'c'*64,'branch_commit':'b'*40,'generation':'before_restore'}
        new={**old,'external_proof':{'postbackup_window':{'rows':6}}}
        phase={'schema':1,'token':'d'*32,'phase':'baseline_enabled','generation':'before_restore','branch_commit':'b'*40}
        request={**old,**{k:phase[k] for k in ('token','phase')},'purpose':'automatic_restore','process':process}
        class Hass:
            async def async_add_executor_job(self,function,*args):return function(*args)
        def check(ok,label):
            if not ok:raise ValueError(label)
        values={'inputs_at':lambda directory:new,'read_json':lambda path:dict(phase),
            'CONTROL':'control','process':lambda:dict(process),'check':check}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'<bound_reload_after_grant>','exec'),values)
        actual=asyncio.run(values['reload_granted_inputs'](Hass(),Path('/synthetic'),request,phase))
        self.assertIs(actual,new)
        self.assertNotIn('external_proof',old)
        new['branch_commit']='e'*40
        with self.assertRaisesRegex(ValueError,'qa_granted_inputs_changed'):
            asyncio.run(values['reload_granted_inputs'](Hass(),Path('/synthetic'),request,phase))

    def test_observer_projects_malformed_pregrant_and_stops(self):
        import json,os,re,secrets,stat,tempfile
        source_path=ROOT/'guest_helper/homecircle_safe_restore_qa/__init__.py'
        tree=ast.parse(source_path.read_bytes())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Rehearsal')
        poll=next(n for n in cls.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='poll')
        functions=[n for n in tree.body if isinstance(n,ast.FunctionDef)
            and n.name in {'closed_boot_request','consume_closed_boot_grant'}]
        with tempfile.TemporaryDirectory() as folder:
            directory=Path(folder).resolve();control=directory/c.CONTROL;control.mkdir(mode=0o700)
            phase={'schema':1,'token':'d'*32,'phase':'baseline_enabled',
                'generation':'before_restore','branch_commit':'b'*40}
            inputs={'source_commit':'a'*40,'candidate_sha256':c.CANDIDATE_SHA,
                'branch_commit':'b'*40,'generation':'before_restore'}
            process={'pid':123,'start_ticks':4}
            (control/'phase.json').write_text(json.dumps(phase))
            (control/'baseline.json').write_text('{}')
            grant=control/'closed-boot-grant.json';grant.write_bytes(b'{');grant.chmod(0o600)
            def write(path,value):path.write_text(json.dumps(value))
            def check(ok,label):
                if not ok:raise c.Refused(label)
            class Hass:
                is_running=True
                async def async_add_executor_job(self,function,*args):return function(*args)
            values={'inputs_at':lambda directory:dict(inputs),'read_json':lambda path:json.loads(path.read_bytes()),
                'write_json':write,'CONTROL':c.CONTROL,'PHASES':c.PHASES,
                'CANDIDATE':c.CANDIDATE_SHA,'process':lambda:dict(process),'current_entry':lambda hass:object(),
                'assert_enabled':lambda hass,entry:None,'check':check,'Refused':c.Refused,
                'failure_diagnostics':c._DIAGNOSTICS,'Path':Path,'__file__':str(source_path),
                '_LOGGER':types.SimpleNamespace(error=lambda *args:None),'asyncio':asyncio,
                'json':json,'os':os,'re':re,'secrets':secrets,'stat':stat}
            exec(compile(ast.Module(body=[*functions,poll],type_ignores=[]),str(source_path),'exec'),values)
            observer=types.SimpleNamespace(hass=Hass(),directory=directory,control=control)
            asyncio.run(values['poll'](observer))
            request=json.loads((control/'boot-request.json').read_bytes())
            failure=json.loads((control/'restore-barrier.json').read_bytes())
            self.assertEqual(request['purpose'],'automatic_restore')
            self.assertEqual(failure['outcome'],'failed')
            self.assertIs(failure['closed_boot_grant_verified'],False)
            self.assertEqual(failure['process'],process)
            self.assertEqual(failure['failure_type'],'JSONDecodeError')
            self.assertIsNone(failure['failure_code'])
            self.assertEqual(failure['stage'],'control')
            self.assertNotIn('message',failure)
            self.assertTrue(grant.exists())

    def test_pregrant_automatic_failure_rejects_stale_process(self):
        import json,tempfile
        with tempfile.TemporaryDirectory() as folder:
            control=c.Controller(types.SimpleNamespace(branch_commit='b'*40,output=Path(folder)/'unused'))
            control.public=Path(folder);control.config_path='/synthetic'
            control.phases=[{'process':{'start_ticks':1}},{'process':{'start_ticks':2}}]
            control.network_boundary={'link_closed':True};control.remaining=lambda maximum:1
            receipt={'schema':1,'token':control.phase_token,'phase':'automatic_restored_enabled',
                'generation':'before_restore','branch_commit':'b'*40,'process':{'pid':123,'start_ticks':2},
                'outcome':'failed','closed_boot_grant_verified':False,'stage':'control',
                'failure_type':'JSONDecodeError','failure_code':None,'frames':[]}
            control.guest_read=lambda path:json.dumps(receipt).encode()
            with self.assertRaisesRegex(c.Refused,'ordinary_first_restored_process_identity'):
                control.restored_boot_barrier()
            self.assertFalse((Path(folder)/'automatic_restored_enabled.json').exists())
            self.assertEqual(control.guest_failures,[])


class PersonActivityContracts(unittest.TestCase):
    def public_proofs(self,phase='baseline_enabled'):
        person={key:True for key in c._PERSON.PERSON_BOOLEANS}
        person.update(persons=1,configured_tracker_links=2,selected_tracker_links=1,
            saved_associations_sha256='a'*64,postbackup_tracker_absent=phase!='mutated_enabled',direct_person_state_writes=0)
        activity={key:True for key in c._PERSON.ACTIVITY_BOOLEANS}
        activity.update(B_events=24,B_sha256='a'*64,B_preserved=phase!='mutated_enabled',B_transitions=2,
            M_events=0 if phase=='baseline_enabled' else 24,M_sha256=None if phase=='baseline_enabled' else 'b'*64,
            M_absent=phase!='mutated_enabled',M_transitions=0 if phase=='baseline_enabled' else 2,
            R_events=0 if phase in c.PHASES[:2] else 24,R_sha256=None if phase in c.PHASES[:2] else 'c'*64,
            R_preserved=None if phase in c.PHASES[:2] else True,R_transitions=0 if phase in c.PHASES[:2] else 2,
            manual_activity_store_writes=0,direct_activity_appends=0)
        return person,activity

    def event_groups(self):
        return {('person.' if index==0 else 'device_tracker.')+'example_member_'+str(index):[
            {'kind':'started','observed_at':'2026-10-22T10:00:00+00:00'},
            {'kind':'presence','value':'away','observed_at':'2026-10-22T10:00:00+00:00'},
            {'kind':'source','value':None,'observed_at':'2026-10-22T10:00:00+00:00'},
            {'kind':'freshness','value':'unavailable','observed_at':'2026-10-22T10:00:00+00:00'}]
            for index in range(5)}

    def test_person_proof_rejects_collapsed_selection_and_direct_person_write(self):
        from copy import deepcopy
        person,_=self.public_proofs()
        self.assertEqual(c._PERSON.person_proof(person,c.PHASES[0]),person)
        for key,value in [('configured_tracker_links',1),('selected_tracker_links',True),
                ('direct_person_state_writes',1),('configured_active_selected_distinct',False)]:
            changed=deepcopy(person);changed[key]=value
            with self.assertRaises(ValueError):c._PERSON.person_proof(changed,c.PHASES[0])

    def test_activity_proof_requires_positive_disjoint_measured_cohorts(self):
        from copy import deepcopy
        for phase in c.PHASES:
            _,activity=self.public_proofs(phase)
            self.assertEqual(c._PERSON.activity_proof(activity,phase),activity)
        _,activity=self.public_proofs(c.PHASES[2])
        for key,value in [('R_events',0),('R_transitions',True),('M_sha256','a'*64),
                ('B_events',20),('direct_activity_appends',1),('startup_suffix_allowlisted',False)]:
            changed=deepcopy(activity);changed[key]=value
            with self.assertRaises((ValueError,TypeError)):c._PERSON.activity_proof(changed,c.PHASES[2])

    def test_activity_prefix_and_removed_mutation_are_discriminating(self):
        from copy import deepcopy
        baseline=self.event_groups();later=deepcopy(baseline)
        for events in later.values():events.append({'kind':'presence','value':'home','observed_at':'2026-10-22T10:00:01+00:00'})
        self.assertTrue(c._PERSON.preserved_prefix(later,baseline))
        self.assertEqual(c._PERSON.count_events(c._PERSON.suffix(later,baseline)),5)
        later[next(iter(later))][1]['value']='home'
        self.assertFalse(c._PERSON.preserved_prefix(later,baseline))
        self.assertFalse(c._PERSON.absent_events(later,baseline))

    def test_startup_suffix_refuses_unknown_fields_values_and_extra_started(self):
        from copy import deepcopy
        groups=self.event_groups();self.assertEqual(c._PERSON.observation_suffix(groups),groups)
        for mutation in ('field','value','started','timestamp'):
            changed=deepcopy(groups);events=changed[next(iter(changed))]
            if mutation=='field':events[1]['latitude']=1.0
            elif mutation=='value':events[1]['value']='invented_trip'
            elif mutation=='started':events.append(dict(events[0]))
            else:events[1]['observed_at']='2026-10-22T10:00:00'
            with self.assertRaises(ValueError):c._PERSON.observation_suffix(changed)

    def actual_activity_model(self):
        from datetime import datetime,timedelta,timezone
        from hashlib import sha256
        import json,zipfile
        from copy import deepcopy
        with zipfile.ZipFile(ROOT/'payload/homecircle.zip') as archive:
            source=archive.read('activity.py')
        cls=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='ActivityLog')
        now=[datetime(2026,10,22,10,0,tzinfo=timezone.utc)]
        selected={c._PERSON.TRACKER_A}
        values={'timedelta':timedelta,'sha256':sha256,'json':json,
            'RETENTION_DAYS':7,'MAX_EVENTS':100,'MAX_FRESHNESS_EVENTS':25,
            'KINDS':{'started','presence','source','freshness','refresh','automatic_refresh'},
            'VALUES':{'presence':{'home','away','driving','unavailable'},
                'freshness':{'fresh','stale','unknown','unavailable'},
                'refresh':{'requested'},'automatic_refresh':{'requested'}},
            'selected_entities':lambda config:selected,
            'dt_util':types.SimpleNamespace(utcnow=lambda:now[0],parse_datetime=datetime.fromisoformat)}
        exec(compile(ast.Module(body=[cls],type_ignores=[]),'<sha_bound_actual_activity_class>','exec'),values)
        class Store:
            def __init__(self,data=None):self.data=data;self.pending=[]
            async def async_load(self):return deepcopy(self.data)
            def async_delay_save(self,callback,delay):self.pending.append((callback,delay))
            def tick(self):self.data=deepcopy(self.pending[-1][0]())
        config={'primary_home':'zone.home','places':[],'members':{
            member:{'additional_residences':[]} for member in self.event_groups()}}
        def household(state='away'):
            return types.SimpleNamespace(members=[types.SimpleNamespace(id=member,place=None,focusable=True,
                presence=state if index==0 else 'away',location=types.SimpleNamespace(evidence=types.SimpleNamespace(
                    source_entity=c._PERSON.TRACKER_A,freshness='fresh',reported_at=None)))
                for index,member in enumerate(config['members'])])
        return values['ActivityLog'],Store,config,household,now

    def test_real_activity_class_uses_delayed_save_and_config_bound_load(self):
        from copy import deepcopy
        cls,Store,config,household,now=self.actual_activity_model()
        store=Store();log=cls(config,store)
        log.observe(household(),now[0]);now[0]+=__import__('datetime').timedelta(seconds=1)
        log.observe(household('home'),now[0]);now[0]+=__import__('datetime').timedelta(seconds=1)
        log.observe(household('away'),now[0]);store.tick()
        self.assertTrue(store.pending);self.assertTrue(all(delay==5 for _,delay in store.pending))
        self.assertEqual(c._PERSON.count_events(store.data['events']),22)
        c._PERSON.observation_suffix(store.data['events'])
        changed=deepcopy(config);changed['display_name']='Discriminating mutation'
        reset=cls(changed,Store(store.data));asyncio.run(reset.load())
        self.assertTrue(all(events==[] for events in reset.events.values()))

    def test_real_activity_restart_retains_exact_prefix_and_appends_boundary(self):
        from copy import deepcopy
        from datetime import timedelta
        cls,Store,config,household,now=self.actual_activity_model()
        store=Store();log=cls(config,store);log.observe(household(),now[0]);store.tick();B=deepcopy(store.data['events'])
        now[0]+=timedelta(seconds=1)
        restored_store=Store(store.data);restored=cls(config,restored_store);asyncio.run(restored.load())
        restored.observe(household(),now[0]);restored_store.tick()
        self.assertTrue(c._PERSON.preserved_prefix(restored.events,B))
        R=c._PERSON.suffix(restored.events,B)
        c._PERSON.observation_suffix(R)
        self.assertEqual(c._PERSON.count_events(R),20)
        damaged=deepcopy(restored.events);damaged[next(iter(B))][0]['observed_at']='2026-10-22T09:59:59+00:00'
        self.assertFalse(c._PERSON.preserved_prefix(damaged,B))

    def archive_values(self):
        from copy import deepcopy
        import hashlib,json
        groups=self.event_groups();first=next(iter(groups))
        groups[first].extend([{'kind':'presence','value':'home','observed_at':'2026-10-22T10:00:01+00:00'},
            {'kind':'presence','value':'away','observed_at':'2026-10-22T10:00:02+00:00'}])
        item={'id':'example_homecircle_restore_person','name':c._PERSON.PERSON_NAME,
            'user_id':None,'device_trackers':[c._PERSON.TRACKER_A,c._PERSON.TRACKER_B]}
        registry=[{'entity_id':entity,'unique_id':item['id'] if index==0 else entity.split('.',1)[1],
            'platform':'person' if index==0 else 'homecircle_safe_restore_qa','config_entry_id':None,'disabled_by':None}
            for index,entity in enumerate((c._PERSON.PERSON_ID,c._PERSON.TRACKER_A,c._PERSON.TRACKER_B))]
        options={'people':[c._PERSON.PERSON_ID],'members':{member:{} for member in groups}}
        options['members'][c._PERSON.PERSON_ID]={'trackers':[c._PERSON.TRACKER_A]}
        # Keep exactly five members while binding the separate Person identity.
        options['members'].pop(first)
        groups[c._PERSON.PERSON_ID]=groups.pop(first)
        payload={'fingerprint':hashlib.sha256(json.dumps(options,sort_keys=True,default=str).encode()).hexdigest(),
            'arrival_version':1,'arrivals':{},'events':groups}
        association={'item':item,'registry':registry,'selected':[c._PERSON.TRACKER_A]}
        baseline={'schema':1,'association':association,'payload':payload,'transitions':2}
        person={'key':'person','version':2,'data':{'items':[item]}}
        activity={'key':'homecircle.activity.'+'a'*32,'version':1,'data':payload}
        expected={'person_sha256':c._PERSON.digest(association),'B_sha256':c._PERSON.digest(groups),'B_events':22}
        return deepcopy((person,activity,baseline,registry,options,'a'*32,expected))

    def test_archive_binds_actual_person_registry_and_activity_members(self):
        import archive_person_activity as archive
        result=archive.validate_person_activity_archive(*self.archive_values())
        self.assertEqual(result,{'saved_person_configuration_included':True,
            'saved_person_registry_joins_included':True,'saved_homecircle_activity_included':True})

    def test_archive_rejects_person_link_registry_or_activity_tampering(self):
        import archive_person_activity as archive
        for mutation in ('person','registry','activity'):
            values=list(self.archive_values())
            if mutation=='person':values[0]['data']['items'][0]['device_trackers'].reverse()
            elif mutation=='registry':values[3].pop()
            else:values[1]['data']['events'][next(iter(values[1]['data']['events']))].pop()
            with self.assertRaises(ValueError):archive.validate_person_activity_archive(*values)

    def test_exact_selected_entities_excludes_unselected_person_links(self):
        import zipfile
        with zipfile.ZipFile(ROOT/'payload/homecircle.zip') as archive:
            source=ast.parse(archive.read('selection.py'))
        fn=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='selected_entities')
        values={'Mapping':dict,'Any':object,**{'CONF_'+key.upper():key for key in
            ('primary_home','places','people','people_trackers','pets','items','members','trackers','additional_residences')}}
        # Product spelling uses CONF_RESIDENCES for additional_residences.
        values['CONF_RESIDENCES']='additional_residences'
        values['CONF_TRACKER_PEOPLE']='people_trackers'
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'<actual_selected_entities>','exec'),values)
        config={'primary_home':'zone.home','places':[],'people':[c._PERSON.PERSON_ID],
            'people_trackers':[],'pets':[],'items':[],'members':{c._PERSON.PERSON_ID:{
                'trackers':[c._PERSON.TRACKER_A],'additional_residences':[]}}}
        selected=values['selected_entities'](config)
        self.assertIn(c._PERSON.PERSON_ID,selected);self.assertIn(c._PERSON.TRACKER_A,selected)
        self.assertNotIn(c._PERSON.TRACKER_B,selected);self.assertNotIn(c._PERSON.TRACKER_C,selected)

    def test_producer_has_no_direct_person_state_or_activity_store_writes(self):
        tree=ast.parse((ROOT/'guest_helper/homecircle_safe_restore_qa/person_activity.py').read_bytes())
        calls=[node for node in ast.walk(tree) if isinstance(node,ast.Call)]
        self.assertFalse(any(isinstance(node.func,ast.Attribute) and node.func.attr in {'append','save','async_save'}
            for node in calls))
        state_calls=[node for node in calls if isinstance(node.func,ast.Attribute) and node.func.attr=='async_set']
        self.assertEqual(len(state_calls),1);self.assertIsInstance(state_calls[0].args[0],ast.Name)
        self.assertEqual(state_calls[0].args[0].id,'tracker')
        managed=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='managed_data')
        opens=[node for node in ast.walk(managed) if isinstance(node,ast.Call)
            and isinstance(node.func,ast.Attribute) and node.func.attr=='open']
        self.assertEqual(len(opens),1)
        self.assertIn('O_RDONLY',ast.unparse(opens[0].args[1]))
        self.assertNotIn('O_WRONLY',ast.unparse(opens[0].args[1]))
        manifest=__import__('json').loads((ROOT/'guest_helper/homecircle_safe_restore_qa/manifest.json').read_bytes())
        self.assertIn('person',manifest['dependencies'])

    def test_failure_catalog_binds_new_finite_helper_diagnostics(self):
        allowed=c._DIAGNOSTICS.catalog(c._DIAGNOSTIC_ROOT)
        self.assertIn('person_activity',allowed['frames']);self.assertIn('person_activity_protocol',allowed['frames'])
        self.assertIn('qa_person_selection_nonconflation',allowed['codes'])
        self.assertIn('qa_activity_actual_api_projection',allowed['codes'])


if __name__=='__main__':unittest.main()
