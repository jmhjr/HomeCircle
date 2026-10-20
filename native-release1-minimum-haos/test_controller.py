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

    def test_actual_machine_image_reference_and_config_id_are_mandatory(self):
        obj=instance()
        for reference,image_id in ((controller.IMAGE_REFERENCE,controller.IMAGE_CONFIG_ID),
                                   ('ghcr.io/home-assistant/qemux86-64-homeassistant:2026.10.2',controller.IMAGE_CONFIG_ID),
                                   (controller.IMAGE_REFERENCE,'sha256:'+'0'*64)):
            obj.guest=Mock(return_value=json.dumps({'reference':reference,'image_id':image_id}).encode())
            if reference==controller.IMAGE_REFERENCE and image_id==controller.IMAGE_CONFIG_ID:
                self.assertTrue(obj.actual_core_image()['observed_config_id_matches'])
            else:
                with self.subTest(reference=reference),self.assertRaises(controller.Refused):obj.actual_core_image()

    def test_unproven_vm_cannot_reset_any_configuration(self):
        obj=instance();obj.stop_core=Mock()
        with self.assertRaisesRegex(controller.Refused,'fresh_owned_vm_reset_required'):obj.select_minimum_core()
        obj.stop_core.assert_not_called()

    def test_version_selection_error_has_one_mutation_and_no_retry(self):
        obj=instance();obj.kvm_confirmed=True;obj.qemu=Mock();obj.qemu.poll.return_value=None
        obj.private=Path('/private');obj.config_path='/mnt/data/supervisor/homeassistant';obj.core_version_before='2026.10.2'
        obj.stop_core=Mock();obj.core_running=Mock(return_value=False);obj.guest_write=Mock()
        obj.guest=Mock(side_effect=[json.dumps(fresh_reset()).encode(),b'{"result":"error"}'])
        with self.assertRaisesRegex(controller.Refused,'minimum_core_selection_api_refused'):obj.select_minimum_core()
        self.assertEqual(obj.version_change_requests,1)
        calls=[call for call in obj.guest.call_args_list if 'core update' in call.args[0]]
        self.assertEqual(len(calls),1);self.assertIn('--version 2026.9.4 --backup=false',calls[0].args[0])
        with self.assertRaisesRegex(controller.Refused,'fresh_selection_repeat_refused'):obj.select_minimum_core()
        self.assertEqual(obj.version_change_requests,1)

    def test_failed_core_stop_api_is_not_retried(self):
        obj=instance();obj.management_ready=Mock(return_value=True);obj.core_running=Mock(return_value=True)
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


if __name__ == '__main__':
    unittest.main()
