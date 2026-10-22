"""Read-only collector contracts over synthetic ZIPs; no HA, Git, network or VM."""
import ast
import copy
from contextlib import redirect_stdout
import io
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import types
import unittest
import zipfile

import independent_evidence as e

FIXTURE = next(path for path in (e.HERE.parent / e.FIXTURE_NAME, e.HERE.parents[1] / e.FIXTURE_NAME)
               if path.is_dir())


def packet(bindings):
    """Reuse the frozen producer's synthetic packet, adding full public fields."""
    with bindings.modules() as m:
        tree = ast.parse(bindings.raw['test_saved_storage.py'])
        names = {'result','record','prepared_fixture','enabled_extra','packet'}
        nodes = [node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
        env = dict(c=m.controller,a=m.accept_saved_storage,ep=m.enabled_protocol,g=m.guard_context,
                   s=m.storage_context,PIN=m.controller.CANDIDATE_SHA)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'<frozen-synthetic-packet>','exec'),env)
        host, phases = env['packet']()
        c = m.controller
        host['provenance'] = bindings.provenance(c)
        host['current_core_image'] = dict(reference=c.IMAGE_REFERENCE,identity_model='containerd_index_with_verified_stored_oci_chain',
            observed_container_image_id=c.IMAGE_INDEX_DIGEST,observed_image_inspect_id=c.IMAGE_INDEX_DIGEST,
            official_index_digest=c.IMAGE_INDEX_DIGEST,selected_manifest_digest=c.IMAGE_MANIFEST_DIGEST,
            verified_oci_config_digest=c.IMAGE_CONFIG_ID,stored_objects_hashed=3,
            object_bytes={name:item[1] for name,item in c.IMAGE_OBJECTS.items()},
            containerd_address=c.CONTAINERD_ADDRESS,containerd_namespace=c.CONTAINERD_NAMESPACE,
            platform={'os':'linux','architecture':'amd64'},rootfs_layers=22,
            image_rootfs_matches_verified_config=True,repository_digest_checked=True)
        host['fresh_owned_config'] = dict(files=0,bytes=0,children=0,owner_accounts_found=False,
            candidate_previously_present=False,fresh_config_reset=True,mount_directory_preserved=True)
        host['network_boundary'] = dict(link_closed=True,before_probe_connected=True,closed_probe_connected=False,
            closed_probe_observations=9,guest_agent_remained_available=True)
        host['direct_candidate_installs'] = 1
        host['candidate_transport'] = 'stopped_verified_zip_files'
        host['host_elapsed_seconds'] = 1000.0
        for action in host['core_actions']:
            start=action['action']=='start'
            action.update(container_state_before='stopped' if start else 'running',
                container_state_after='running' if start else 'stopped',running_before=not start,running_after=start)
        for request in host['backup_requests']:
            request.update(stdout_json=True,api_error={'type':'unclassified','categories':[]},
                stderr_error={'type':'unclassified','categories':[]})
        host['backup'].update(result='ok',job=dict(name='backup_manager_partial_backup',done=True,error_count=0,nodes=2),
            type='partial',homeassistant_version=c.CORE,database_included=True,protected=False,compressed=False)
        host['backup']['archive']['archive_bytes']=10000
        host['restore'].update(result='ok',job=dict(name='backup_manager_partial_restore',done=True,error_count=0,nodes=2),
            qa_startup_boundary_required=True)
        host['prepared_dependency_fixture']['closure'].update({'life360':'7.2.0','anisette':'1.2.4','unicorn':'2.1.4',
            'srp':'1.0.22','beautifulsoup4':'4.13.3','protobuf':'6.33.0'})
        for phase in phases.values():
            phase['qa_manifest_sha256']=bindings.manifest_sha
            if 'package_payload_sha256' in phase:
                phase['package_payload_sha256']=bindings.payload_sha
        return {'host.json':host,**{name+'.json':value for name,value in phases.items()}}


def zip_bytes(receipts, changes=None):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,value in receipts.items():
            body=e.canonical(value)
            item=zipfile.ZipInfo(name)
            item.external_attr=(stat.S_IFREG|0o600)<<16
            if changes:
                changed=changes(name,item,body)
                if changed is None:continue
                item,body=changed
            archive.writestr(item,body)
    return stream.getvalue()


def metadata(raw):
    return dict(schema=1,run_id=e.RUN,run_attempt=1,head_sha=e.HEAD,branch='codex/native-amd64-validation',
        event='push',workflow_path=e.WORKFLOW,workflow_sha256=e.WORKFLOW_SHA,artifact_id=123,
        artifact_name=e.ARTIFACT,artifact_zip_sha256=e.sha(raw),github_digest_verified=True,
        status='completed',conclusion='success')


class CurrentEvidenceContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bindings=e.Bindings(FIXTURE)

    def setUp(self):
        self.receipts=packet(self.bindings)

    def refuses(self, receipts=None):
        with self.assertRaises(e.EvidenceRefused):
            e.validate_receipts(receipts or self.receipts,self.bindings)

    def run_review(self, raw, meta=None):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);artifact=root/'artifact.zip';external=root/'metadata.json'
            artifact.write_bytes(raw);external.write_bytes(e.canonical(meta or metadata(raw)))
            return e.review(artifact,external,FIXTURE)

    def test_frozen_28_files_workflow_and_original_113_members_bind(self):
        self.assertEqual(len(self.bindings.raw),27)
        self.assertEqual(len(self.bindings.inventory),113)
        self.assertEqual(self.bindings.manifest_sha,'d11e8e93315d1f90c80eca1c0f091d67d6be27eb242e240423049d30543f7497')

    def test_full_synthetic_packet_accepts_only_instrumented_scope(self):
        result=e.validate_receipts(self.receipts,self.bindings)
        self.assertIs(result['instrumented_enabled_synthetic_restore_qualified'],True)
        self.assertIs(result['ordinary_uninstrumented_restore_qualified'],False)
        self.assertIs(result['automatic_guard_antirollback'],False)

    def test_complete_zip_and_separate_root_metadata_replay(self):
        result=self.run_review(zip_bytes(self.receipts))
        self.assertEqual(result['run_id'],e.RUN)
        self.assertEqual(len(result['receipts']),6)
        self.assertIs(result['native_trial_repeated_by_collector'],False)
        self.assertTrue(result['exact_source_and_tool_provenance_checked'])

    def test_all_twenty_provenance_values_are_bound_to_frozen_bytes(self):
        original=copy.deepcopy(self.receipts)
        for key,value in original['host.json']['provenance'].items():
            self.receipts=copy.deepcopy(original)
            replacement=not value if type(value)is bool else 0 if type(value)is int else {} if type(value)is dict else '0'*64
            self.receipts['host.json']['provenance'][key]=replacement
            with self.subTest(key=key):self.refuses()

    def test_original_manifest_arbitrary_digest_is_refused(self):
        self.receipts['host.json']['provenance']['original_manifest_sha256']='0'*64
        self.refuses()

    def test_coordinated_manifest_digest_forgery_is_refused(self):
        self.receipts['host.json']['provenance']['qa_manifest_sha256']='0'*64
        for name in e.PHASES:self.receipts[name+'.json']['qa_manifest_sha256']='0'*64
        self.refuses()

    def test_coordinated_payload_digest_forgery_is_refused(self):
        self.receipts['host.json']['provenance']['candidate_payload_sha256']='0'*64
        for name in e.PHASES:
            if 'package_payload_sha256' in self.receipts[name+'.json']:
                self.receipts[name+'.json']['package_payload_sha256']='0'*64
        self.refuses()

    def test_float_member_count_in_provenance_is_refused(self):
        self.receipts['host.json']['provenance']['unchanged_runtime_members']=112.0
        self.refuses()

    def test_nested_private_provenance_key_is_refused(self):
        self.receipts['host.json']['provenance']['private_canary']='PRIVATE-CANARY'
        self.refuses()

    def test_every_helper_hash_is_bound_not_self_declared(self):
        original=copy.deepcopy(self.receipts)
        helper=original['host.json']['provenance']['helper_files_sha256']
        for name in helper:
            self.receipts=copy.deepcopy(original)
            self.receipts['host.json']['provenance']['helper_files_sha256'][name]='0'*64
            with self.subTest(name=name):self.refuses()

    def test_foreign_nested_public_keys_are_refused(self):
        paths=[('provenance',),('current_core_image',),('network_boundary',),('backup',),('backup','archive'),
               ('restore',),('prepared_dependency_fixture',),('fresh_owned_config',)]
        original=copy.deepcopy(self.receipts)
        for path in paths:
            self.receipts=copy.deepcopy(original);target=self.receipts['host.json']
            for key in path:target=target[key]
            target['private_canary']='PRIVATE-CANARY'
            with self.subTest(path=path):self.refuses()
        for field in ('core_actions','backup_requests','storage_contexts','guard_transfer_contexts'):
            self.receipts=copy.deepcopy(original);self.receipts['host.json'][field][0]['private_canary']='PRIVATE-CANARY'
            with self.subTest(field=field):self.refuses()

    def test_foreign_nested_phase_keys_are_refused(self):
        original=copy.deepcopy(self.receipts)
        for field in ('startup_boundary','prepared_dependencies','recorder'):
            self.receipts=copy.deepcopy(original);self.receipts['baseline_enabled.json'][field]['private_canary']='PRIVATE-CANARY'
            with self.subTest(field=field):self.refuses()

    def test_known_counts_require_integer_types(self):
        original=copy.deepcopy(self.receipts)
        for path in [('direct_candidate_installs',),('network_boundary','closed_probe_observations'),
                     ('backup','archive','archive_bytes'),('backup','job','nodes'),('prepared_dependency_fixture','closure_count')]:
            self.receipts=copy.deepcopy(original);target=self.receipts['host.json']
            for key in path[:-1]:target=target[key]
            target[path[-1]]=True
            with self.subTest(path=path):self.refuses()

    def test_image_identity_nested_schema_and_hashes_are_exact(self):
        for field in ('observed_container_image_id','selected_manifest_digest','verified_oci_config_digest'):
            bad=copy.deepcopy(self.receipts);bad['host.json']['current_core_image'][field]='sha256:'+'0'*64
            with self.subTest(field=field):self.refuses(bad)

    def test_core_action_state_and_boolean_correspondence_required(self):
        bad=copy.deepcopy(self.receipts);bad['host.json']['core_actions'][1]['running_before']=True
        self.refuses(bad)

    def test_backup_request_error_labels_cannot_carry_arbitrary_text(self):
        self.receipts['host.json']['backup_requests'][0]['api_error']['categories']=['PRIVATE-CANARY']
        self.refuses()

    def test_postrestore_exact_history_requires_nonnull_fingerprint(self):
        for name in e.PHASES[3:]:self.receipts[name+'.json']['recorder']['postrestore_sha256']=None
        self.refuses()

    def test_nonvacuous_and_recovery_seam_rules_still_apply(self):
        for field,value in [('life360_requests_denied',0),('apple_legacy_requests_denied',0),('recovery_before_dispatch_calls',1)]:
            bad=copy.deepcopy(self.receipts);bad['automatic_restored_enabled.json']['startup_boundary'][field]=value
            with self.subTest(field=field):self.refuses(bad)

    def test_root_metadata_run_head_workflow_and_conclusion_are_fixed(self):
        raw=zip_bytes(self.receipts)
        for key,value in [('run_id',1),('run_attempt',True),('head_sha','0'*40),('branch','main'),('event','workflow_dispatch'),
                          ('workflow_sha256','0'*64),('workflow_path','other.yml'),('conclusion','failure'),('status','in_progress'),
                          ('artifact_name','other'),('artifact_id',True),('github_digest_verified',False)]:
            meta=metadata(raw);meta[key]=value
            with self.subTest(key=key),self.assertRaises(e.EvidenceRefused):self.run_review(raw,meta)

    def test_metadata_foreign_keys_and_wrong_artifact_digest_refuse(self):
        raw=zip_bytes(self.receipts)
        for meta in [dict(metadata(raw),private_canary='PRIVATE-CANARY'),dict(metadata(raw),artifact_zip_sha256='0'*64)]:
            with self.assertRaises(e.EvidenceRefused):self.run_review(raw,meta)

    def test_archive_requires_all_six_fixed_receipts(self):
        for receipt in e.RECEIPTS:
            raw=zip_bytes({name:value for name,value in self.receipts.items() if name!=receipt})
            with self.subTest(receipt=receipt),self.assertRaises(e.EvidenceRefused):self.run_review(raw)

    def test_traversal_symlink_and_foreign_zip_members_refuse(self):
        for kind in ('traversal','symlink','foreign'):
            def change(name,item,body):
                if name=='host.json':
                    if kind=='traversal':item.filename='../host.json'
                    if kind=='foreign':item.filename='private.json'
                    if kind=='symlink':item.external_attr=(stat.S_IFLNK|0o777)<<16
                return item,body
            with self.subTest(kind=kind),self.assertRaises(e.EvidenceRefused):self.run_review(zip_bytes(self.receipts,change))

    def test_duplicate_receipt_names_refuse(self):
        raw=zip_bytes(self.receipts)
        stream=io.BytesIO(raw)
        import warnings
        with warnings.catch_warnings(),zipfile.ZipFile(stream,'a') as archive:
            warnings.simplefilter('ignore',UserWarning)
            archive.writestr('host.json',e.canonical(self.receipts['host.json']))
        with self.assertRaises(e.EvidenceRefused):self.run_review(stream.getvalue())

    def test_duplicate_json_keys_and_nonfinite_numbers_refuse(self):
        for body in (b'{"schema":1,"schema":1}',b'{"schema":NaN}',b'{"schema":Infinity}'):
            def change(name,item,original):return item,body if name=='host.json' else original
            with self.assertRaises(e.EvidenceRefused):self.run_review(zip_bytes(self.receipts,change))

    def test_receipt_expansion_bound_is_checked_before_read(self):
        def change(name,item,body):return item,b' '*(1024**2+1) if name=='host.json' else body
        with self.assertRaises(e.EvidenceRefused):self.run_review(zip_bytes(self.receipts,change))

    def test_changed_frozen_input_map_refuses_before_import(self):
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/'INPUTS.json';file.write_bytes((e.HERE/'INPUTS.json').read_bytes()+b'\n')
            with self.assertRaisesRegex(e.EvidenceRefused,'frozen_inputs_hash_refused'):e.Bindings(FIXTURE,inputs_file=file)

    def test_changed_controller_and_workflow_bytes_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);fixture=root/e.FIXTURE_NAME
            shutil.copytree(FIXTURE,fixture,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            workflow=root/'workflow.yml';workflow.write_bytes(self.bindings.workflow_bytes)
            file=fixture/'controller.py';file.write_bytes(file.read_bytes()+b'\n')
            with self.assertRaisesRegex(e.EvidenceRefused,'frozen_input_bytes_refused'):e.Bindings(fixture,workflow)
            file.write_bytes(self.bindings.raw['controller.py']);workflow.write_bytes(self.bindings.workflow_bytes+b'\n')
            with self.assertRaisesRegex(e.EvidenceRefused,'workflow_bytes_refused'):e.Bindings(fixture,workflow)

    def test_frozen_modules_ignore_and_restore_stale_module_cache(self):
        previous=sys.modules.get('guard_transfer');poison=types.ModuleType('guard_transfer')
        sys.modules['guard_transfer']=poison
        try:
            with self.bindings.modules() as modules:
                self.assertIsNot(modules.guard_transfer,poison)
                self.assertEqual(e.sha(Path(modules.guard_transfer.__file__).read_bytes()),e.sha(self.bindings.raw['guard_transfer.py']))
            self.assertIs(sys.modules['guard_transfer'],poison)
        finally:
            if previous is None:sys.modules.pop('guard_transfer',None)
            else:sys.modules['guard_transfer']=previous

    def test_cli_writes_new_review_and_leaves_originals_byte_exact(self):
        raw=zip_bytes(self.receipts)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);artifact=root/'artifact.zip';external=root/'metadata.json';output=root/'review.json'
            artifact.write_bytes(raw);external.write_bytes(e.canonical(metadata(raw)))
            before=(artifact.read_bytes(),external.read_bytes())
            args=['--artifact-zip',str(artifact),'--metadata',str(external),'--output',str(output),'--fixture-dir',str(FIXTURE)]
            with redirect_stdout(io.StringIO()):self.assertEqual(e.main(args),0)
            first=output.read_bytes()
            with redirect_stdout(io.StringIO()):self.assertEqual(e.main(args),1)
            self.assertEqual(output.read_bytes(),first)
            self.assertEqual((artifact.read_bytes(),external.read_bytes()),before)

    def test_cli_refusal_does_not_echo_private_input_or_paths(self):
        with tempfile.TemporaryDirectory(prefix='PRIVATE-PATH-CANARY-') as directory:
            root=Path(directory);artifact=root/'artifact.zip';external=root/'metadata.json';output=root/'review.json'
            artifact.write_bytes(zip_bytes(self.receipts));external.write_bytes(b'{"PRIVATE-CANARY":1}')
            stream=io.StringIO()
            with redirect_stdout(stream):code=e.main(['--artifact-zip',str(artifact),'--metadata',str(external),
                '--output',str(output),'--fixture-dir',str(FIXTURE)])
            self.assertEqual(code,1)
            self.assertNotIn('PRIVATE',stream.getvalue()+output.read_text())

    def test_cli_output_write_failure_has_fixed_message_without_private_path(self):
        raw=zip_bytes(self.receipts)
        with tempfile.TemporaryDirectory(prefix='PRIVATE-PATH-CANARY-') as directory:
            root=Path(directory);artifact=root/'artifact.zip';external=root/'metadata.json'
            artifact.write_bytes(raw);external.write_bytes(e.canonical(metadata(raw)))
            stream=io.StringIO()
            with redirect_stdout(stream):code=e.main(['--artifact-zip',str(artifact),'--metadata',str(external),
                '--output',str(root/'absent/review.json'),'--fixture-dir',str(FIXTURE)])
            self.assertEqual(code,1)
            self.assertIn('review_output_write_refused',stream.getvalue())
            self.assertNotIn('PRIVATE',stream.getvalue())

    def test_cli_output_cannot_overwrite_either_original_input(self):
        raw=zip_bytes(self.receipts)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);artifact=root/'artifact.zip';external=root/'metadata.json'
            artifact.write_bytes(raw);external.write_bytes(e.canonical(metadata(raw)))
            before=artifact.read_bytes(),external.read_bytes()
            for output in (artifact,external):
                with redirect_stdout(io.StringIO()):code=e.main(['--artifact-zip',str(artifact),'--metadata',str(external),
                    '--output',str(output),'--fixture-dir',str(FIXTURE)])
                self.assertEqual(code,1)
                self.assertEqual((artifact.read_bytes(),external.read_bytes()),before)


if __name__=='__main__':
    unittest.main()
