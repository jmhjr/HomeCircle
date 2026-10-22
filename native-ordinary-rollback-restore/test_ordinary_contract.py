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
                'outcome':'failed','stage':'normal_dependencies','failure_type':'ValueError',
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
            self.assertEqual(public['failure_code'],'qa_dependency_graph_version')
            self.assertEqual(control.guest_failures,[public])


if __name__=='__main__':unittest.main()
