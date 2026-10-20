"""Bounded host/receipt contracts only; no HA, native package or guest imports."""
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

import controller
import reset_fresh_config

ROOT = Path(__file__).resolve().parent


def dependencies(complete=True):
    closure = {name: {'available': True, 'version': controller.DIRECT.get(name, '1.0'),
                     'metadata_system_origin': True, 'constraints_satisfied': True, 'python_satisfied': True} for name in controller.CLOSURE}
    direct = {name: {**closure[name], 'satisfies_requirement': True, 'loaded_module_present': name == 'life360',
                   'origin_probe': 'loaded_module' if name == 'life360' else 'import_spec',
                   'module_system_origin': True} for name in controller.DIRECT}
    if not complete:
        for name in ('life360', 'anisette', 'unicorn', 'srp'):
            closure[name] = {'available': False, 'version': None, 'metadata_system_origin': False, 'constraints_satisfied': False, 'python_satisfied': False}
            direct[name] = {**closure[name], 'satisfies_requirement': False, 'loaded_module_present': False,
                            'origin_probe': 'unavailable', 'module_system_origin': False}
    return {'schema': 1, 'core': controller.CORE, 'python': '3.14.6', 'constraints_sha256': controller.CONSTRAINTS_SHA,
            'constraints_match': True, 'docker_environment': True, 'ordinary_pip_target_unset': True,
            'config_deps_empty': True, 'direct': direct, 'closure': closure, 'closure_count': 24,
            'closure_graph_checked': complete, 'skip_pip': False,
            'provider_or_native_imports_requested_by_probe': False}


def fresh_reset():
    return {'files': 2, 'bytes': 200, 'children': 2, 'owner_accounts_found': False,
            'candidate_previously_present': False, 'fresh_config_reset': True, 'mount_directory_preserved': True}


def instance():
    obj = controller.Controller(SimpleNamespace(candidate_zip=ROOT/'payload/homecircle.zip', branch_commit='1'*40, output=Path('/unused')))
    obj.inventories = {'candidate': {'__init__.py': {'bytes': 1, 'sha256': 'a'*64},
        'frontend/homecircle-card.js': {'bytes': 2, 'sha256': 'b'*64}}}
    return obj


def phase(obj, name='initialize', start=100):
    return {'schema': 1, 'core_version': controller.CORE, 'candidate_archive_sha256': controller.CANDIDATE_SHA,
            'package_files_count': 113, 'package_payload_sha256': controller.sha(controller.canonical(obj.inventories['candidate'])),
            'entry_loaded': True, 'entry_disabled': False, 'nonempty_options': True,
            'static_served_bundle_matches': True, 'persisted_storage_checked': True,
            'persistent_people': 2, 'explicit_trackers': 2, 'provider_accounts_configured': False, 'owner_accounts_used': False,
            'loaded_source_sha256': 'a'*64, 'served_bundle_sha256': 'b'*64,
            'snapshot_sha256': 'c'*64, 'runtime_config_sha256': 'd'*64, 'owned_resource_id_sha256': 'e'*64,
            'normal_dependencies': dependencies(), 'process': {'pid': 42, 'start_ticks': start}, 'phase': name}


class ExactPayload(unittest.TestCase):
    def test_real_local_payload_is_exact_and_inventory_is_complete(self):
        expected = json.loads((ROOT/'payload/inventory.json').read_bytes())
        self.assertEqual(controller.check_archive(ROOT/'payload/homecircle.zip', controller.CANDIDATE_SHA, 113), expected['files'])
        self.assertEqual(hashlib.sha256((ROOT/'payload/homecircle.zip').read_bytes()).hexdigest(), expected['archive_sha256'])
        with zipfile.ZipFile(ROOT/'payload/homecircle.zip') as archive:
            self.assertEqual(json.loads(archive.read('manifest.json'))['version'], '0.1.0-beta.20')

    def test_wrong_hash_count_paths_and_duplicate_members_are_refused(self):
        for entries, count, digest in (([('../outside', 'x')], 1, None), ([('/outside', 'x')], 1, None),
                                       ([('good', 'x')], 2, None), ([('good', 'x')], 1, '0'*64)):
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder)/'source.zip'
                with zipfile.ZipFile(path, 'w') as archive:
                    for name, data in entries:
                        archive.writestr(name, data)
                with self.subTest(entries=entries, count=count), self.assertRaises(controller.Refused):
                    controller.check_archive(path, digest or controller.sha(path.read_bytes()), count)
        raw=io.BytesIO()
        with zipfile.ZipFile(raw, 'w') as archive, self.assertWarns(UserWarning):
            archive.writestr('one', 'first')
            archive.writestr('one', 'second')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.zip';path.write_bytes(raw.getvalue())
            with self.assertRaises(controller.Refused):
                controller.check_archive(path,controller.sha(raw.getvalue()),1)


class NormalDependencyContracts(unittest.TestCase):
    def test_missing_baseline_and_satisfied_final_are_distinct(self):
        self.assertFalse(controller.project_dependencies(dependencies(False),False)['direct']['unicorn']['available'])
        with self.assertRaises(controller.Refused):
            controller.project_dependencies(dependencies(False),True)
        self.assertTrue(controller.project_dependencies(dependencies(),True)['closure_graph_checked'])

    def test_wrong_environment_preload_or_skip_flags_are_refused(self):
        for field,value in (('core','2026.10.2'),('python','3.14.7'),('constraints_sha256','0'*64),
                            ('constraints_match',False),('docker_environment',False),('ordinary_pip_target_unset',False),
                            ('config_deps_empty',False),('skip_pip',True),('closure_graph_checked',False),
                            ('closure_count',True),('schema',True),('provider_or_native_imports_requested_by_probe',True)):
            body=dependencies();body[field]=value
            with self.subTest(field=field),self.assertRaises(controller.Refused):
                controller.project_dependencies(body,True)

    def test_bad_metadata_versions_types_and_origins_are_refused(self):
        for mutate in (
            lambda body:body['closure']['unicorn'].update(metadata_system_origin=False),
            lambda body:body['closure']['unicorn'].update(constraints_satisfied=False),
            lambda body:body['closure']['unicorn'].update(python_satisfied=False),
            lambda body:body['closure']['unicorn'].update(version='private canary'),
            lambda body:body['closure']['unicorn'].update(version='bare_private_canary'),
            lambda body:body['closure']['unicorn'].update(available=1),
            lambda body:body['direct']['unicorn'].update(version='2.2.0'),
            lambda body:body['direct']['unicorn'].update(module_system_origin=False),
            lambda body:body['direct']['unicorn'].update(origin_probe='loaded_module'),
            lambda body:body['direct']['unicorn'].update(available=False),
            lambda body:body['direct'].pop('unicorn'),
        ):
            body=dependencies();mutate(body)
            with self.subTest(body=body),self.assertRaises(controller.Refused):
                controller.project_dependencies(body,True)

    def test_unknown_private_fields_are_not_projected(self):
        body=dependencies();body['private_path']='private-canary'
        body['direct']['life360']['private_value']='private-canary'
        self.assertNotIn('private-canary',json.dumps(controller.project_dependencies(body,True)))


class PhaseContracts(unittest.TestCase):
    def test_both_observations_preserve_identity_and_have_different_processes(self):
        obj=instance();first=obj.accept_phase('initialize',phase(obj));obj.phases.append(first)
        second=obj.accept_phase('restart',phase(obj,'restart',200))
        self.assertEqual(first['snapshot_sha256'],second['snapshot_sha256'])
        self.assertNotEqual(first['process']['start_ticks'],second['process']['start_ticks'])

    def test_unloaded_unselected_empty_unsaved_or_wrong_bytes_are_refused(self):
        for field,value in (('entry_loaded',False),('entry_disabled',True),('nonempty_options',False),
                            ('persisted_storage_checked',False),('explicit_trackers',1),('persistent_people',1),
                            ('provider_accounts_configured',True),('owner_accounts_used',True),('core_version','2026.10.2'),
                            ('package_files_count',112),('loaded_source_sha256','0'*64),('served_bundle_sha256','0'*64)):
            obj=instance();body=phase(obj);body[field]=value
            with self.subTest(field=field),self.assertRaises(controller.Refused):
                obj.accept_phase('initialize',body)

    def test_each_restart_identity_and_same_process_change_is_refused(self):
        for field in ('snapshot_sha256','runtime_config_sha256','owned_resource_id_sha256'):
            obj=instance();obj.phases.append(obj.accept_phase('initialize',phase(obj)))
            body=phase(obj,'restart',200);body[field]='0'*64
            with self.subTest(field=field),self.assertRaises(controller.Refused):
                obj.accept_phase('restart',body)
        obj=instance();obj.phases.append(obj.accept_phase('initialize',phase(obj)))
        with self.assertRaises(controller.Refused):
            obj.accept_phase('restart',phase(obj,'restart',100))

    def test_bare_valid_looking_private_failure_labels_do_not_escape(self):
        obj=instance();obj.config_path='/owned';obj.guest_write=Mock();obj.start_core=Mock();obj.guest=Mock()
        canary='bare_private_canary'
        body={'schema':1,'phase':'initialize','token':obj.phase_token,'branch_commit':'1'*40,
              'outcome':'failed','stage':canary,'failure_type':canary,'failure_code':canary}
        obj.guest_read=Mock(return_value=json.dumps(body).encode())
        with tempfile.TemporaryDirectory() as folder:
            obj.public=Path(folder)
            with self.assertRaisesRegex(controller.Refused,'guest_acceptance_failed'):obj.phase('initialize')
            public=(Path(folder)/'initialize.json').read_text()
            self.assertNotIn(canary,public)
            self.assertEqual(json.loads(public)['stage'],'unrecognized_stage')
            self.assertEqual(json.loads(public)['failure_type'],'unrecognized_failure_type')
        known=controller.failure_projection({'stage':'ordinary_managed_requirements','failure_type':'ValueError',
                                             'failure_code':'qa_normal_dependency_environment'})
        self.assertEqual(known['stage'],'ordinary_managed_requirements')
        self.assertEqual(known['failure_code'],'qa_normal_dependency_environment')

    def test_unknown_receipt_fields_do_not_escape(self):
        obj=instance();body=phase(obj);body['private']='private-canary'
        self.assertNotIn('private-canary',json.dumps(obj.accept_phase('initialize',body)))

    def test_candidate_cannot_be_staged_before_actual_minimum_core(self):
        obj=instance();obj.container_core_version_after='2026.10.2';obj.stop_core=Mock()
        with self.assertRaises(controller.Refused):obj.prepare(obj.inventories['candidate'])
        obj.stop_core.assert_not_called()

    def test_stale_phase_receipt_is_not_progress(self):
        obj=instance();obj.config_path='/owned';obj.guest_write=Mock();obj.start_core=Mock();obj.guest=Mock()
        body={'schema':1,'phase':'initialize','token':'0'*32,'branch_commit':'1'*40,'outcome':'passed'}
        obj.guest_read=Mock(return_value=json.dumps(body).encode())
        with self.assertRaises(controller.Refused):obj.phase('initialize')
        self.assertEqual(obj.phases,[])


class CLIAndMutationContracts(unittest.TestCase):
    def test_actual_cli_version_flags_and_executable_digest_are_checked(self):
        obj=instance();obj.cli_version_observed='2026.09.0'
        obj.guest=Mock(side_effect=[b'Usage: --version --backup',b'Usage:',b'Usage:',('a'*64+'  /bin/ha').encode()])
        obj.verify_cli();self.assertEqual(obj.cli_capabilities['executed_binary_sha256'],'a'*64)
        obj=instance();obj.cli_version_observed='2026.08.0';obj.guest=Mock()
        with self.assertRaises(controller.Refused):obj.verify_cli()
        obj.guest.assert_not_called()
        obj=instance();obj.cli_version_observed='2026.09.0';obj.guest=Mock(return_value=b'Usage: --backup')
        with self.assertRaises(controller.Refused):obj.verify_cli()

    def test_actual_machine_image_requires_bound_index_manifest_and_config(self):
        fixture=image_fixture()
        obj=instance()
        with patch.multiple(controller,**fixture['constants']):
            obj.guest=Mock(side_effect=[json.dumps(fixture[name]).encode() for name in ('container','image','daemon')]
                           +[fixture['blobs'][name] for name in ('index','manifest','config')])
            result=obj.actual_core_image()
            self.assertEqual(result['verified_oci_config_digest'],fixture['constants']['IMAGE_CONFIG_ID'])
            self.assertEqual(result['observed_container_image_id'],fixture['constants']['IMAGE_INDEX_DIGEST'])
            self.assertEqual(result['stored_objects_hashed'],3)
            commands=[call.args[0] for call in obj.guest.call_args_list]
            self.assertEqual(len(commands),6)
            self.assertTrue(all('/usr/bin/ctr --address /run/containerd/containerd.sock --namespace moby content get ' in cmd
                                for cmd in commands[-3:]))
            self.assertTrue(all('.Config.Env' not in cmd for cmd in commands))

    def test_unproven_vm_cannot_reset_any_configuration(self):
        obj=instance();obj.stop_core=Mock()
        with self.assertRaisesRegex(controller.Refused,'fresh_owned_vm_reset_required'):obj.select_minimum_core()
        obj.stop_core.assert_not_called()

    def test_version_selection_error_has_one_mutation_and_no_retry(self):
        obj=instance();obj.kvm_confirmed=True;obj.qemu=Mock();obj.qemu.poll.return_value=None
        obj.private=Path('/private');obj.config_path='/mnt/data/supervisor/homeassistant';obj.core_version_before='2026.10.2'
        obj.stop_core=Mock();obj.core_container_state=Mock(return_value='stopped');obj.guest_write=Mock()
        obj.guest=Mock(side_effect=[json.dumps(fresh_reset()).encode(),b'{"result":"error"}'])
        with self.assertRaisesRegex(controller.Refused,'minimum_core_selection_api_refused'):obj.select_minimum_core()
        self.assertEqual(obj.version_change_requests,1)
        calls=[call for call in obj.guest.call_args_list if 'core update' in call.args[0]]
        self.assertEqual(len(calls),1);self.assertIn('--version 2026.9.4 --backup=false',calls[0].args[0])
        with self.assertRaisesRegex(controller.Refused,'fresh_selection_repeat_refused'):obj.select_minimum_core()
        self.assertEqual(obj.version_change_requests,1)

    def test_failed_core_stop_api_is_not_retried(self):
        obj=instance();obj.management_ready=Mock(return_value=True);obj.core_container_state=Mock(return_value='running')
        obj.guest=Mock(return_value=b'{"result":"error"}')
        with self.assertRaises(controller.Refused):obj.stop_core()
        self.assertEqual(obj.guest.call_count,1)

    def test_finish_rejects_bare_valid_looking_private_stage_type_and_code(self):
        canary='bare_private_canary'
        for error in (controller.Refused(canary),type(canary,(Exception,),{})()):
            obj=instance();obj.stage=canary;obj.cleanup_vm=Mock()
            with tempfile.TemporaryDirectory() as folder:
                obj.public=Path(folder)
                self.assertEqual(obj.finish(error),1)
                public=(Path(folder)/'host.json').read_text()
                self.assertNotIn(canary,public)
                self.assertEqual(json.loads(public)['failure_or_final_stage'],'unrecognized_stage')

    def test_cleanup_before_vm_launch_removes_only_private_workspace(self):
        with tempfile.TemporaryDirectory() as folder:
            obj=instance();obj.private=Path(folder)/'owned-private';obj.private.mkdir()
            obj.cleanup_vm()
            self.assertTrue(obj.cleanup['qemu_stopped']);self.assertTrue(obj.cleanup['private_workspace_removed'])
            self.assertFalse(obj.cleanup['cleanup_failed']);self.assertTrue(Path(folder).exists())

    def test_failure_and_cleanup_error_never_report_success_or_raw_exception(self):
        obj=instance();obj.acceptance=True;obj.phases=[{},{}];obj.cleanup_vm=Mock();obj.cleanup['cleanup_failed']=True
        self.assertEqual(obj.finish(None),1)
        with tempfile.TemporaryDirectory() as folder:
            obj=instance();obj.public=Path(folder);obj.cleanup_vm=Mock()
            self.assertEqual(obj.finish(ValueError('private-canary')),1)
            self.assertNotIn('private-canary',(Path(folder)/'host.json').read_text())


class OwnedBlankResetContracts(unittest.TestCase):
    def test_reset_projection_rejects_owner_old_candidate_and_oversize_claims(self):
        for key,value in (('owner_accounts_found',True),('candidate_previously_present',True),
                          ('fresh_config_reset',False),('mount_directory_preserved',False),('bytes',65*1024**2),('files',True)):
            body=fresh_reset();body[key]=value
            with self.subTest(key=key),self.assertRaises(controller.Refused):controller.checked_reset(body)

    def test_existing_owner_credentials_or_user_entry_is_refused(self):
        for name,body in (('auth',{'data':{'users':[{'is_owner':True,'system_generated':False}]}}),
                          ('auth_provider.homeassistant',{'data':{'users':[{'username':'private-canary'}]}}),
                          ('core.config_entries',{'data':{'entries':[{'domain':'homecircle','source':'user'}]}})):
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder).resolve();(root/'.storage').mkdir();(root/'.storage'/name).write_text(json.dumps(body))
                with patch.object(reset_fresh_config,'CONFIG',root),self.subTest(name=name),self.assertRaises(ValueError):
                    reset_fresh_config.inspect_blank(root)

    def test_blank_system_only_store_is_accepted_without_moving_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();(root/'.storage').mkdir();(root/'.storage/auth').write_text(json.dumps({'data':{'users':[{'is_owner':False,'system_generated':True}]}}))
            with patch.object(reset_fresh_config,'CONFIG',root):
                result=reset_fresh_config.inspect_blank(root)
            self.assertEqual(result['files'],1);self.assertFalse(result['owner_accounts_found'])
            self.assertTrue((root/'.storage/auth').exists())

    def test_symlink_hardlink_and_wrong_root_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();(root/'one').write_text('safe');(root/'link').symlink_to(root/'one')
            with patch.object(reset_fresh_config,'CONFIG',root),self.assertRaises(ValueError):reset_fresh_config.inspect_blank(root)
            (root/'link').unlink();__import__('os').link(root/'one',root/'hard')
            with patch.object(reset_fresh_config,'CONFIG',root),self.assertRaises(ValueError):reset_fresh_config.inspect_blank(root)
            with self.assertRaises(ValueError):reset_fresh_config.inspect_blank(root)


def container_result(state=None, name='homeassistant', identifier='a'*64):
    stdout = b'' if state is None else json.dumps({'id':identifier,'name':name,'state':state}).encode()+b'\n'
    return {'exitcode':0,'signal':None,'stdout':stdout,'stderr':b'','truncated':False}


def image_fixture(config_change=None, manifest_change=None, index_change=None):
    """Synthetic coherent OCI graph; patched pins test semantic checks beyond hashes."""
    diff_ids=['sha256:'+format(number,'064x') for number in range(22)]
    config={'architecture':'amd64','os':'linux','config':{'Labels':{'io.hass.arch':'amd64','io.hass.machine':'qemux86-64',
        'io.hass.type':'core','io.hass.version':'2026.9.4'}},'rootfs':{'type':'layers','diff_ids':diff_ids}}
    if config_change:config_change(config)
    config_raw=controller.canonical(config);config_id='sha256:'+controller.sha(config_raw)
    manifest={'schemaVersion':2,'mediaType':'application/vnd.oci.image.manifest.v1+json',
        'config':{'mediaType':'application/vnd.oci.image.config.v1+json','digest':config_id,'size':len(config_raw)},
        'layers':[{'mediaType':'application/vnd.oci.image.layer.v1.tar+zstd','digest':value,'size':1} for value in diff_ids]}
    if manifest_change:manifest_change(manifest)
    manifest_raw=controller.canonical(manifest);manifest_id='sha256:'+controller.sha(manifest_raw)
    index={'schemaVersion':2,'mediaType':'application/vnd.oci.image.index.v1+json','manifests':[
        {'mediaType':'application/vnd.oci.image.manifest.v1+json','digest':manifest_id,'size':len(manifest_raw),
         'platform':{'architecture':'amd64','os':'linux'}}]}
    if index_change:index_change(index)
    index_raw=controller.canonical(index);index_id='sha256:'+controller.sha(index_raw)
    return {'container':{'reference':controller.IMAGE_REFERENCE,'image_id':index_id},
        'image':{'Id':index_id,'RepoTags':[controller.IMAGE_REFERENCE],
            'RepoDigests':[controller.IMAGE_REFERENCE.rsplit(':',1)[0]+'@'+index_id],
            'Architecture':'amd64','Os':'linux','RootFS':{'Type':'layers','Layers':list(diff_ids)},
            'Descriptor':{'mediaType':'application/vnd.oci.image.index.v1+json','digest':index_id,'size':len(index_raw)}},
        'daemon':{'Address':controller.CONTAINERD_ADDRESS,'Namespaces':{'Containers':controller.CONTAINERD_NAMESPACE}},
        'blobs':{'index':index_raw,'manifest':manifest_raw,'config':config_raw},
        'constants':{'IMAGE_INDEX_DIGEST':index_id,'IMAGE_MANIFEST_DIGEST':manifest_id,'IMAGE_CONFIG_ID':config_id,
            'IMAGE_OBJECTS':{'index':(index_id,len(index_raw)),'manifest':(manifest_id,len(manifest_raw)),'config':(config_id,len(config_raw))}}}


def check_image_fixture(fixture):
    with patch.multiple(controller,**fixture['constants']):
        return controller.verify_stored_image_chain(*(fixture[name] for name in ('container','image','daemon','blobs')))


class StoredImageIdentityContracts(unittest.TestCase):
    def test_index_id_is_separate_from_verified_config_digest(self):
        fixture=image_fixture();result=check_image_fixture(fixture)
        self.assertNotEqual(result['observed_container_image_id'],result['verified_oci_config_digest'])
        self.assertTrue(result['image_rootfs_matches_verified_config'])

    def test_wrong_actual_blob_bytes_and_missing_or_extra_objects_are_refused(self):
        for name in ('index','manifest','config'):
            fixture=image_fixture();fixture['blobs'][name]+=b'\n'
            with self.subTest(name=name),self.assertRaises(controller.Refused):check_image_fixture(fixture)
        for name in ('missing','extra'):
            fixture=image_fixture()
            if name=='missing':fixture['blobs'].pop('config')
            else:fixture['blobs']['private']=b'canary'
            with self.assertRaises(controller.Refused):check_image_fixture(fixture)

    def test_validly_hashed_wrong_platform_or_config_link_is_refused(self):
        for fixture in (
            image_fixture(index_change=lambda value:value['manifests'][0]['platform'].update(architecture='arm64')),
            image_fixture(index_change=lambda value:value['manifests'][0].update(digest='sha256:'+'0'*64)),
            image_fixture(manifest_change=lambda value:value['config'].update(digest='sha256:'+'0'*64)),
            image_fixture(config_change=lambda value:value.update(architecture='arm64')),
            image_fixture(config_change=lambda value:value['config']['Labels'].update({'io.hass.version':'2026.10.2'})),
        ):
            with self.assertRaises(controller.Refused):check_image_fixture(fixture)

    def test_actual_platform_repository_descriptor_or_layer_mismatch_is_refused(self):
        for mutate in (
            lambda value:value['image'].update(Architecture='arm64'),
            lambda value:value['image'].update(Os='windows'),
            lambda value:value['image'].update(RepoDigests=[]),
            lambda value:value['image']['Descriptor'].update(digest='sha256:'+'0'*64),
            lambda value:value['image']['RootFS']['Layers'].reverse(),
            lambda value:value['container'].update(image_id=value['constants']['IMAGE_CONFIG_ID']),
            lambda value:value['container'].update(reference='ghcr.io/home-assistant/qemux86-64-homeassistant:2026.10.2'),
            lambda value:value['daemon'].update(Address='/unrelated/private.sock'),
            lambda value:value['daemon']['Namespaces'].update(Containers='other'),
        ):
            fixture=image_fixture();mutate(fixture)
            with self.assertRaises(controller.Refused):check_image_fixture(fixture)

    def test_unknown_containerd_location_is_refused_before_ctr_content_requests(self):
        fixture=image_fixture();fixture['daemon']['Address']='/unrelated/private.sock';obj=instance()
        obj.guest=Mock(side_effect=[json.dumps(fixture[name]).encode() for name in ('container','image','daemon')])
        with patch.multiple(controller,**fixture['constants']),self.assertRaises(controller.Refused):obj.actual_core_image()
        self.assertEqual(obj.guest.call_count,3)

    def test_public_image_projection_never_exports_extra_metadata(self):
        fixture=image_fixture();fixture['image']['private']='private-canary'
        self.assertNotIn('private-canary',json.dumps(check_image_fixture(fixture)))

    def test_public_core_versions_refuse_local_prerelease_and_bare_canaries(self):
        for value in ('2026.10.2+privatecanary','2026.10.2b1','2026.10.2rc1','bare_private_canary','2026.10.2-private'):
            self.assertIsNone(controller.public_core_version(value))
        for value in ('landingpage','2026.9.4','2026.10.2','2026.09.0'):
            self.assertEqual(controller.public_core_version(value),value)


class ContainerLifecycleContracts(unittest.TestCase):
    def test_successful_listing_distinguishes_absence_stopped_and_running(self):
        self.assertEqual(controller.parse_core_container_state(container_result()),'not_created')
        for raw, expected in (('created','stopped'),('exited','stopped'),('running','running'),
                              ('paused','unknown'),('restarting','unknown'),('removing','unknown'),('dead','unknown')):
            self.assertEqual(controller.parse_core_container_state(container_result(raw)),expected)
        self.assertEqual(controller.parse_core_container_state(container_result('running','homeassistant-helper')),'not_created')

    def test_daemon_failure_truncation_and_malformed_listing_never_mean_absent(self):
        for key,value in (('exitcode',1),('exitcode',True),('signal',9),('stderr',b'private-canary'),
                          ('truncated',True),('stdout',b'not-json'),('stdout',b'[]'),('stdout',b'\xff'),('stdout',b'x'*65537)):
            result=container_result();result[key]=value
            with self.subTest(key=key):
                self.assertEqual(controller.parse_core_container_state(result),'unknown')
        self.assertEqual(controller.parse_core_container_state(container_result('running',identifier='not-a-docker-id')),'unknown')
        result=container_result('running');result['stdout']*=2
        self.assertEqual(controller.parse_core_container_state(result),'unknown')

    def test_state_transport_uses_bounded_all_container_listing_not_inspect_errors(self):
        obj=instance();obj.guest=Mock(return_value=container_result())
        self.assertEqual(obj.core_container_state(12),'not_created')
        command=obj.guest.call_args.args[0]
        self.assertIn('container ls --all --no-trunc',command)
        self.assertIn('{{json .Names}}',command)
        self.assertNotIn('inspect',command)
        self.assertEqual(obj.guest.call_args.kwargs,{'capture':True})

    def test_absent_container_requires_one_supported_start_and_actual_running_state(self):
        obj=instance();obj.management_ready=Mock(return_value=True)
        obj.core_container_state=Mock(side_effect=['not_created','running'])
        obj.guest=Mock(return_value=b'{"result":"ok"}')
        obj.start_core()
        self.assertEqual(obj.guest.call_count,1)
        self.assertEqual(obj.guest.call_args.args[0],controller.HA+' core start --raw-json')
        record=obj.core_actions[0]
        self.assertIsNone(record['running_before'])
        self.assertEqual(record['container_state_before'],'not_created')
        self.assertEqual(record['container_state_after'],'running')
        self.assertTrue(record['running_after'])

    def test_unknown_state_cannot_trigger_start_and_missing_state_cannot_trigger_stop(self):
        for action,state in (('start','unknown'),('stop','not_created'),('stop','unknown')):
            obj=instance();obj.management_ready=Mock(return_value=True)
            obj.core_container_state=Mock(return_value=state);obj.guest=Mock()
            with self.subTest(action=action,state=state),self.assertRaisesRegex(controller.Refused,'core_action_initial_state_refused'):
                obj.core_action(action)
            obj.guest.assert_not_called()

    def test_start_api_ok_without_running_state_is_incomplete_and_not_retried(self):
        obj=instance();obj.management_ready=Mock(return_value=True)
        obj.core_container_state=Mock(return_value='not_created');obj.guest=Mock(return_value=b'{"result":"ok"}')
        obj.remaining=Mock(return_value=0.02)
        with self.assertRaisesRegex(controller.Refused,'core_action_state_deadline_exceeded'):obj.start_core()
        self.assertEqual(obj.guest.call_count,1)
        self.assertEqual(obj.core_actions[0]['container_state_after'],'not_created')
        self.assertIsNone(obj.core_actions[0]['running_after'])

    def test_stopped_update_missing_container_reaches_supported_start_and_real_target_checks(self):
        obj=instance();obj.kvm_confirmed=True;obj.qemu=Mock();obj.qemu.poll.return_value=None
        obj.private=Path('/private');obj.config_path='/mnt/data/supervisor/homeassistant';obj.core_version_before='2026.10.2'
        obj.stop_core=Mock();obj.core_container_state=Mock(side_effect=['stopped','not_created']);obj.guest_write=Mock()
        obj.guest=Mock(side_effect=[json.dumps(fresh_reset()).encode(),b'{"result":"ok"}',b'{"result":"ok","data":{"version":"2026.9.4"}}'])
        obj.start_core=Mock();obj.managed_core=Mock();obj.real_container_version=Mock(return_value='2026.9.4')
        obj.management_ready=Mock(return_value=True);obj.actual_core_image=Mock(return_value={'actual':'image'})
        obj.observe_dependencies=Mock(return_value=dependencies(False))
        obj.select_minimum_core()
        self.assertEqual(obj.version_change_requests,1)
        self.assertEqual(obj.core_container_state_after_selection,'not_created')
        obj.start_core.assert_called_once()
        obj.managed_core.assert_called_once();obj.real_container_version.assert_called_once();obj.actual_core_image.assert_called_once()
        self.assertEqual(obj.container_core_version_after,'2026.9.4')

    def test_successful_selection_and_start_cannot_bypass_wrong_actual_target(self):
        obj=instance();obj.kvm_confirmed=True;obj.qemu=Mock();obj.qemu.poll.return_value=None
        obj.private=Path('/private');obj.config_path='/mnt/data/supervisor/homeassistant';obj.core_version_before='2026.10.2'
        obj.stop_core=Mock();obj.core_container_state=Mock(side_effect=['stopped','not_created']);obj.guest_write=Mock()
        obj.guest=Mock(side_effect=[json.dumps(fresh_reset()).encode(),b'{"result":"ok"}',b'{"result":"ok","data":{"version":"2026.10.2"}}'])
        obj.start_core=Mock();obj.managed_core=Mock();obj.real_container_version=Mock(return_value='2026.10.2')
        obj.management_ready=Mock(return_value=True);obj.actual_core_image=Mock();obj.observe_dependencies=Mock()
        obj.remaining=Mock(return_value=0.02)
        with self.assertRaisesRegex(controller.Refused,'actual_minimum_core_deadline_exceeded'):obj.select_minimum_core()
        obj.start_core.assert_called_once();obj.actual_core_image.assert_not_called();obj.observe_dependencies.assert_not_called()
        self.assertEqual(obj.direct_installs,0);self.assertEqual(obj.phases,[])


if __name__ == '__main__':
    unittest.main()
