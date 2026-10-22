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


if __name__=='__main__':unittest.main()
