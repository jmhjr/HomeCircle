"""Reused strict archive, backup, requirements, ownership and OCI contracts."""
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock,patch
import zipfile
import controller
import reset_fresh_config
ROOT=Path(__file__).resolve().parent
class ArchiveContracts(unittest.TestCase):

    def archive(self, members):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            for name, value in members:
                archive.writestr(name, value)
        return buffer.getvalue()

    def inspect(self, raw, count):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'input.zip'
            path.write_bytes(raw)
            return controller.check_archive(path, controller.sha(raw), count)

    def test_exact_inventory_is_derived_from_bytes(self):
        self.assertEqual(self.inspect(self.archive([('__init__.py', b'example')]), 1), {'__init__.py': {'bytes': 7, 'sha256': controller.sha(b'example')}})

    def test_parent_and_absolute_names_are_refused(self):
        for name in ('../outside', '/outside', 'normal\\outside'):
            with self.subTest(name=name), self.assertRaises(controller.Refused):
                self.inspect(self.archive([(name, b'example')]), 1)

    def test_duplicate_members_cannot_hide_archive_contents(self):
        with self.assertWarns(UserWarning):
            raw = self.archive([('one', b'first'), ('one', b'second')])
        with self.assertRaises(controller.Refused):
            self.inspect(raw, 1)

    def test_archive_pin_is_mandatory(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'input.zip'
            path.write_bytes(self.archive([('one', b'example')]))
            with self.assertRaises(controller.Refused):
                controller.check_archive(path, '0' * 64, 1)

class PublicDiagnostics(unittest.TestCase):

    def test_core_version_projection_excludes_arbitrary_response_strings(self):
        for value in ('2026.10.2', 'landingpage'):
            self.assertEqual(controller.public_core_version(value), value)
        for value in (None, {}, 'private-value', '2026.10.2 private-value', 'https://example.invalid'):
            self.assertIsNone(controller.public_core_version(value))

    def test_supervisor_projection_excludes_arbitrary_private_fields(self):
        value = {'result': 'ok', 'data': {'healthy': True, 'supported': False, 'state': 'running', 'ip_address': 'PRIVATE-CANARY', 'token': 'PRIVATE-CANARY', 'version': 'PRIVATE-CANARY'}}
        projected = controller.public_supervisor_state(value)
        self.assertEqual(projected, {'result': 'ok', 'healthy': True, 'supported': False, 'state': 'running'})
        self.assertNotIn('PRIVATE-CANARY', json.dumps(projected))

    def test_root_info_state_and_version_exclude_host_identifiers(self):
        value = {'result': 'ok', 'data': {'state': 'running', 'supervisor': '2026.10.0', 'supported': True, 'hostname': 'PRIVATE-CANARY', 'machine_id': 'PRIVATE-CANARY'}}
        self.assertEqual(controller.public_root_state(value), {'result': 'ok', 'state': 'running', 'supervisor_version': '2026.10.0', 'supported': True})

    def test_http_projection_refuses_invalid_types_and_unbounded_values(self):
        self.assertEqual(controller.public_http_probe({'active_port': True, 'status': 600, 'response_bytes': -1, 'expected_bytes': 32 * 1024 ** 2 + 1, 'tls': 'PRIVATE-CANARY', 'body_matches': 1, 'response_sha256': 'PRIVATE-CANARY', 'expected_sha256': 'A' * 64, 'location_category': 'https://PRIVATE-CANARY/'}), {})
        for value in (None, [], 'PRIVATE-CANARY'):
            self.assertEqual(controller.public_http_probe(value), {})

class ManagementJobs(unittest.TestCase):

    def project(self, jobs):
        return controller.public_jobs({'result': 'ok', 'data': {'jobs': jobs}})

    def test_not_started_nested_core_job_blocks_readiness(self):
        jobs = self.project([{'name': 'unrelated_background_task', 'done': False, 'child_jobs': [{'name': 'home_assistant_core_start', 'done': None, 'child_jobs': []}]}])
        self.assertFalse(controller.core_jobs_idle(jobs))

    def test_unrelated_perpetual_job_does_not_block_completed_core(self):
        jobs = self.project([{'name': 'unrelated_background_task', 'done': False}, {'name': 'home_assistant_core_install', 'done': True}])
        self.assertTrue(controller.core_jobs_idle(jobs))

    def test_unknown_job_identity_is_not_silently_accepted_as_idle(self):
        with self.assertRaises(controller.Refused):
            self.project([{'name': None, 'done': False}])

    def test_large_tree_is_refused_instead_of_truncated(self):
        with self.assertRaises(controller.Refused):
            self.project([{'name': 'unrelated_background_task', 'done': True}] * 257)

class BackupContracts(unittest.TestCase):

    def setUp(self):
        self.identifier = 'a' * 32
        self.job = {'uuid': self.identifier, 'name': 'backup_manager_partial_backup', 'done': True, 'errors': [], 'child_jobs': []}
        self.value = {'result': 'ok', 'data': {'jobs': [self.job]}}

    def test_matching_completed_job_excludes_error_messages(self):
        self.job['private'] = 'PRIVATE-CANARY'
        self.assertEqual(controller.exact_job(self.value, self.identifier, self.job['name']), {'name': self.job['name'], 'done': True, 'error_count': 0, 'nodes': 1})

    def test_nested_error_is_not_hidden_by_successful_parent(self):
        self.job['child_jobs'] = [{'uuid': 'b' * 32, 'name': 'backup_store_homeassistant', 'done': True, 'errors': [{'message': 'PRIVATE-CANARY'}], 'child_jobs': []}]
        result = controller.exact_job(self.value, self.identifier, self.job['name'])
        self.assertEqual(result['error_count'], 1)
        self.assertNotIn('PRIVATE-CANARY', json.dumps(result))

    def test_legacy_error_field_and_unstarted_child_are_observed(self):
        self.job['child_jobs'] = [{'uuid': 'b' * 32, 'done': None, 'errors': [], 'error': {'secret': 'PRIVATE-CANARY'}}]
        result = controller.exact_job(self.value, self.identifier, self.job['name'])
        self.assertFalse(result['done'])
        self.assertEqual(result['error_count'], 1)

    def test_other_completed_backup_cannot_replace_exact_operation(self):
        with self.assertRaises(controller.Refused):
            controller.exact_job(self.value, 'b' * 32, self.job['name'])

    def test_duplicate_job_id_is_refused(self):
        self.value['data']['jobs'].append(dict(self.job))
        with self.assertRaises(controller.Refused):
            controller.exact_job(self.value, self.identifier, self.job['name'])

    def test_database_exclusion_or_full_scope_is_refused(self):
        info = {'result': 'ok', 'data': {'slug': 'abcd1234', 'type': 'partial', 'homeassistant': controller.CORE, 'homeassistant_exclude_database': False, 'protected': False, 'compressed': False}}
        self.assertTrue(controller.backup_info(info, 'abcd1234')['database_included'])
        for key, invalid in (('type', 'full'), ('homeassistant_exclude_database', True), ('homeassistant', 'landingpage')):
            changed = {'result': 'ok', 'data': {**info['data'], key: invalid}}
            with self.subTest(key=key), self.assertRaises(controller.Refused):
                controller.backup_info(changed, 'abcd1234')

    def test_nested_backup_failure_diagnostics_exclude_raw_messages_and_unknown_types(self):
        self.job['child_jobs'] = [{'uuid': 'b' * 32, 'name': 'backup_store_homeassistant', 'done': True, 'errors': [{'type': 'HomeAssistantBackupError', 'message': 'Preparing backup of Home Assistant Core failed due to: Error during pre-backup: Could not lock database within 30 PRIVATE-CANARY'}, {'type': 'PRIVATE-CANARY', 'message': 'PRIVATE-CANARY'}], 'child_jobs': []}]
        result = controller.public_backup_failure_jobs(self.value, self.identifier, self.job['name'])
        self.assertEqual(result[0]['binding'], 'exact_operation')
        errors = result[0]['nodes'][1]['errors']
        self.assertEqual(errors[0], {'type': 'HomeAssistantBackupError', 'categories': ['core_backup_start_rejected', 'core_pre_backup_hook_failed', 'recorder_lock_timeout']})
        self.assertEqual(errors[1], {'type': 'unclassified', 'categories': []})
        self.assertNotIn('PRIVATE-CANARY', json.dumps(result))

    def test_recent_failure_jobs_are_labeled_without_an_exact_returned_id(self):
        result = controller.public_backup_failure_jobs(self.value, None, self.job['name'])
        self.assertEqual(result[0]['binding'], 'recent_backup_job')

    def test_backup_failure_diagnostic_tree_is_bounded_without_silent_truncation(self):
        self.job['child_jobs'] = [{'uuid': 'b' * 32, 'done': True, 'errors': []}] * 256
        with self.assertRaises(controller.Refused):
            controller.public_backup_failure_jobs(self.value, self.identifier, self.job['name'])

    def test_cli_and_condition_categories_never_copy_dynamic_arguments_or_reasons(self):
        for message, expected in (('unknown command "PRIVATE-CANARY"', 'cli_unexpected_positional_or_command'), ('accepts 1 arg(s), received 2 PRIVATE-CANARY', 'cli_positional_count'), ('unexpected non-JSON response PRIVATE-CANARY', 'cli_http_non_json'), ('Not enough free space PRIVATE-CANARY', 'supervisor_free_space')):
            result = controller.backup_error_categories({'message': message})
            with self.subTest(expected=expected):
                self.assertEqual(result['categories'], [expected])
                self.assertNotIn('PRIVATE-CANARY', json.dumps(result))
def dependencies(complete=True):
    closure = {name: {'available': True, 'version': controller.DIRECT.get(name, '1.0'), 'metadata_system_origin': True, 'constraints_satisfied': True, 'python_satisfied': True} for name in controller.CLOSURE}
    direct = {name: {**closure[name], 'satisfies_requirement': True, 'loaded_module_present': name == 'life360', 'origin_probe': 'loaded_module' if name == 'life360' else 'import_spec', 'module_system_origin': True} for name in controller.DIRECT}
    if not complete:
        for name in ('life360', 'anisette', 'unicorn', 'srp'):
            closure[name] = {'available': False, 'version': None, 'metadata_system_origin': False, 'constraints_satisfied': False, 'python_satisfied': False}
            direct[name] = {**closure[name], 'satisfies_requirement': False, 'loaded_module_present': False, 'origin_probe': 'unavailable', 'module_system_origin': False}
    return {'schema': 1, 'core': controller.CORE, 'python': '3.14.6', 'constraints_sha256': controller.CONSTRAINTS_SHA, 'constraints_match': True, 'docker_environment': True, 'ordinary_pip_target_unset': True, 'config_deps_empty': True, 'direct': direct, 'closure': closure, 'closure_count': 24, 'closure_graph_checked': complete, 'skip_pip': False, 'provider_or_native_imports_requested_by_probe': False}

def fresh_reset():
    return {'files': 2, 'bytes': 200, 'children': 2, 'owner_accounts_found': False, 'candidate_previously_present': False, 'fresh_config_reset': True, 'mount_directory_preserved': True}

def instance():
    obj = controller.Controller(SimpleNamespace(candidate_zip=ROOT / 'payload/homecircle.zip', branch_commit='1' * 40, output=Path('/unused')))
    obj.inventories = {'candidate': {'__init__.py': {'bytes': 1, 'sha256': 'a' * 64}, 'frontend/homecircle-card.js': {'bytes': 2, 'sha256': 'b' * 64}}}
    return obj

class ExactPayload(unittest.TestCase):

    def test_real_local_payload_is_exact_and_inventory_is_complete(self):
        expected = json.loads((ROOT / 'payload/inventory.json').read_bytes())
        self.assertEqual(controller.check_archive(ROOT / 'payload/homecircle.zip', controller.CANDIDATE_SHA, 113), expected['files'])
        self.assertEqual(hashlib.sha256((ROOT / 'payload/homecircle.zip').read_bytes()).hexdigest(), expected['archive_sha256'])
        with zipfile.ZipFile(ROOT / 'payload/homecircle.zip') as archive:
            self.assertEqual(json.loads(archive.read('manifest.json'))['version'], '0.1.0-beta.20')

    def test_wrong_hash_count_paths_and_duplicate_members_are_refused(self):
        for entries, count, digest in (([('../outside', 'x')], 1, None), ([('/outside', 'x')], 1, None), ([('good', 'x')], 2, None), ([('good', 'x')], 1, '0' * 64)):
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'source.zip'
                with zipfile.ZipFile(path, 'w') as archive:
                    for name, data in entries:
                        archive.writestr(name, data)
                with self.subTest(entries=entries, count=count), self.assertRaises(controller.Refused):
                    controller.check_archive(path, digest or controller.sha(path.read_bytes()), count)
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, 'w') as archive, self.assertWarns(UserWarning):
            archive.writestr('one', 'first')
            archive.writestr('one', 'second')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'source.zip'
            path.write_bytes(raw.getvalue())
            with self.assertRaises(controller.Refused):
                controller.check_archive(path, controller.sha(raw.getvalue()), 1)

class NormalDependencyContracts(unittest.TestCase):

    def test_missing_baseline_and_satisfied_final_are_distinct(self):
        self.assertFalse(controller.project_dependencies(dependencies(False), False)['direct']['unicorn']['available'])
        with self.assertRaises(controller.Refused):
            controller.project_dependencies(dependencies(False), True)
        self.assertTrue(controller.project_dependencies(dependencies(), True)['closure_graph_checked'])

    def test_wrong_environment_preload_or_skip_flags_are_refused(self):
        for field, value in (('core', '2026.9.4'), ('python', '3.14.7'), ('constraints_sha256', '0' * 64), ('constraints_match', False), ('docker_environment', False), ('ordinary_pip_target_unset', False), ('config_deps_empty', False), ('skip_pip', True), ('closure_graph_checked', False), ('closure_count', True), ('schema', True), ('provider_or_native_imports_requested_by_probe', True)):
            body = dependencies()
            body[field] = value
            with self.subTest(field=field), self.assertRaises(controller.Refused):
                controller.project_dependencies(body, True)

    def test_bad_metadata_versions_types_and_origins_are_refused(self):
        for mutate in (lambda body: body['closure']['unicorn'].update(metadata_system_origin=False), lambda body: body['closure']['unicorn'].update(constraints_satisfied=False), lambda body: body['closure']['unicorn'].update(python_satisfied=False), lambda body: body['closure']['unicorn'].update(version='private canary'), lambda body: body['closure']['unicorn'].update(version='bare_private_canary'), lambda body: body['closure']['unicorn'].update(available=1), lambda body: body['direct']['unicorn'].update(version='2.2.0'), lambda body: body['direct']['unicorn'].update(module_system_origin=False), lambda body: body['direct']['unicorn'].update(origin_probe='loaded_module'), lambda body: body['direct']['unicorn'].update(available=False), lambda body: body['direct'].pop('unicorn')):
            body = dependencies()
            mutate(body)
            with self.subTest(body=body), self.assertRaises(controller.Refused):
                controller.project_dependencies(body, True)

    def test_unknown_private_fields_are_not_projected(self):
        body = dependencies()
        body['private_path'] = 'private-canary'
        body['direct']['life360']['private_value'] = 'private-canary'
        self.assertNotIn('private-canary', json.dumps(controller.project_dependencies(body, True)))

class OwnedBlankResetContracts(unittest.TestCase):

    def test_reset_projection_rejects_owner_old_candidate_and_oversize_claims(self):
        for key, value in (('owner_accounts_found', True), ('candidate_previously_present', True), ('fresh_config_reset', False), ('mount_directory_preserved', False), ('bytes', 65 * 1024 ** 2), ('files', True)):
            body = fresh_reset()
            body[key] = value
            with self.subTest(key=key), self.assertRaises(controller.Refused):
                controller.checked_reset(body)

    def test_existing_owner_credentials_or_user_entry_is_refused(self):
        for name, body in (('auth', {'data': {'users': [{'is_owner': True, 'system_generated': False}]}}), ('auth_provider.homeassistant', {'data': {'users': [{'username': 'private-canary'}]}}), ('core.config_entries', {'data': {'entries': [{'domain': 'homecircle', 'source': 'user'}]}})):
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder).resolve()
                (root / '.storage').mkdir()
                (root / '.storage' / name).write_text(json.dumps(body))
                with patch.object(reset_fresh_config, 'CONFIG', root), self.subTest(name=name), self.assertRaises(ValueError):
                    reset_fresh_config.inspect_blank(root)

    def test_blank_system_only_store_is_accepted_without_moving_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            (root / '.storage').mkdir()
            (root / '.storage/auth').write_text(json.dumps({'data': {'users': [{'is_owner': False, 'system_generated': True}]}}))
            with patch.object(reset_fresh_config, 'CONFIG', root):
                result = reset_fresh_config.inspect_blank(root)
            self.assertEqual(result['files'], 1)
            self.assertFalse(result['owner_accounts_found'])
            self.assertTrue((root / '.storage/auth').exists())

    def test_symlink_hardlink_and_wrong_root_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            (root / 'one').write_text('safe')
            (root / 'link').symlink_to(root / 'one')
            with patch.object(reset_fresh_config, 'CONFIG', root), self.assertRaises(ValueError):
                reset_fresh_config.inspect_blank(root)
            (root / 'link').unlink()
            __import__('os').link(root / 'one', root / 'hard')
            with patch.object(reset_fresh_config, 'CONFIG', root), self.assertRaises(ValueError):
                reset_fresh_config.inspect_blank(root)
            with self.assertRaises(ValueError):
                reset_fresh_config.inspect_blank(root)

def container_result(state=None, name='homeassistant', identifier='a' * 64):
    stdout = b'' if state is None else json.dumps({'id': identifier, 'name': name, 'state': state}).encode() + b'\n'
    return {'exitcode': 0, 'signal': None, 'stdout': stdout, 'stderr': b'', 'truncated': False}

def image_fixture(config_change=None, manifest_change=None, index_change=None):
    """Synthetic coherent OCI graph; patched pins test semantic checks beyond hashes."""
    diff_ids = ['sha256:' + format(number, '064x') for number in range(22)]
    config = {'architecture': 'amd64', 'os': 'linux', 'config': {'Labels': {'io.hass.arch': 'amd64', 'io.hass.machine': 'qemux86-64', 'io.hass.type': 'core', 'io.hass.version': controller.CORE}}, 'rootfs': {'type': 'layers', 'diff_ids': diff_ids}}
    if config_change:
        config_change(config)
    config_raw = controller.canonical(config)
    config_id = 'sha256:' + controller.sha(config_raw)
    manifest = {'schemaVersion': 2, 'mediaType': 'application/vnd.oci.image.manifest.v1+json', 'config': {'mediaType': 'application/vnd.oci.image.config.v1+json', 'digest': config_id, 'size': len(config_raw)}, 'layers': [{'mediaType': 'application/vnd.oci.image.layer.v1.tar+zstd', 'digest': value, 'size': 1} for value in diff_ids]}
    if manifest_change:
        manifest_change(manifest)
    manifest_raw = controller.canonical(manifest)
    manifest_id = 'sha256:' + controller.sha(manifest_raw)
    index = {'schemaVersion': 2, 'mediaType': 'application/vnd.oci.image.index.v1+json', 'manifests': [{'mediaType': 'application/vnd.oci.image.manifest.v1+json', 'digest': manifest_id, 'size': len(manifest_raw), 'platform': {'architecture': 'amd64', 'os': 'linux'}}]}
    if index_change:
        index_change(index)
    index_raw = controller.canonical(index)
    index_id = 'sha256:' + controller.sha(index_raw)
    return {'container': {'reference': controller.IMAGE_REFERENCE, 'image_id': index_id}, 'image': {'Id': index_id, 'RepoTags': [controller.IMAGE_REFERENCE], 'RepoDigests': [controller.IMAGE_REFERENCE.rsplit(':', 1)[0] + '@' + index_id], 'Architecture': 'amd64', 'Os': 'linux', 'RootFS': {'Type': 'layers', 'Layers': list(diff_ids)}, 'Descriptor': {'mediaType': 'application/vnd.oci.image.index.v1+json', 'digest': index_id, 'size': len(index_raw)}}, 'daemon': {'Address': controller.CONTAINERD_ADDRESS, 'Namespaces': {'Containers': controller.CONTAINERD_NAMESPACE}}, 'blobs': {'index': index_raw, 'manifest': manifest_raw, 'config': config_raw}, 'constants': {'IMAGE_INDEX_DIGEST': index_id, 'IMAGE_MANIFEST_DIGEST': manifest_id, 'IMAGE_CONFIG_ID': config_id, 'IMAGE_OBJECTS': {'index': (index_id, len(index_raw)), 'manifest': (manifest_id, len(manifest_raw)), 'config': (config_id, len(config_raw))}}}

def check_image_fixture(fixture):
    with patch.multiple(controller, **fixture['constants']):
        return controller.verify_stored_image_chain(*(fixture[name] for name in ('container', 'image', 'daemon', 'blobs')))

class StoredImageIdentityContracts(unittest.TestCase):

    def test_index_id_is_separate_from_verified_config_digest(self):
        fixture = image_fixture()
        result = check_image_fixture(fixture)
        self.assertNotEqual(result['observed_container_image_id'], result['verified_oci_config_digest'])
        self.assertTrue(result['image_rootfs_matches_verified_config'])

    def test_wrong_actual_blob_bytes_and_missing_or_extra_objects_are_refused(self):
        for name in ('index', 'manifest', 'config'):
            fixture = image_fixture()
            fixture['blobs'][name] += b'\n'
            with self.subTest(name=name), self.assertRaises(controller.Refused):
                check_image_fixture(fixture)
        for name in ('missing', 'extra'):
            fixture = image_fixture()
            if name == 'missing':
                fixture['blobs'].pop('config')
            else:
                fixture['blobs']['private'] = b'canary'
            with self.assertRaises(controller.Refused):
                check_image_fixture(fixture)

    def test_validly_hashed_wrong_platform_or_config_link_is_refused(self):
        for fixture in (image_fixture(index_change=lambda value: value['manifests'][0]['platform'].update(architecture='arm64')), image_fixture(index_change=lambda value: value['manifests'][0].update(digest='sha256:' + '0' * 64)), image_fixture(manifest_change=lambda value: value['config'].update(digest='sha256:' + '0' * 64)), image_fixture(config_change=lambda value: value.update(architecture='arm64')), image_fixture(config_change=lambda value: value['config']['Labels'].update({'io.hass.version': '2026.9.4'}))):
            with self.assertRaises(controller.Refused):
                check_image_fixture(fixture)

    def test_actual_platform_repository_descriptor_or_layer_mismatch_is_refused(self):
        for mutate in (lambda value: value['image'].update(Architecture='arm64'), lambda value: value['image'].update(Os='windows'), lambda value: value['image'].update(RepoDigests=[]), lambda value: value['image']['Descriptor'].update(digest='sha256:' + '0' * 64), lambda value: value['image']['RootFS']['Layers'].reverse(), lambda value: value['container'].update(image_id=value['constants']['IMAGE_CONFIG_ID']), lambda value: value['container'].update(reference='ghcr.io/home-assistant/qemux86-64-homeassistant:2026.9.4'), lambda value: value['daemon'].update(Address='/unrelated/private.sock'), lambda value: value['daemon']['Namespaces'].update(Containers='other')):
            fixture = image_fixture()
            mutate(fixture)
            with self.assertRaises(controller.Refused):
                check_image_fixture(fixture)

    def test_unknown_containerd_location_is_refused_before_ctr_content_requests(self):
        fixture = image_fixture()
        fixture['daemon']['Address'] = '/unrelated/private.sock'
        obj = instance()
        obj.guest = Mock(side_effect=[json.dumps(fixture[name]).encode() for name in ('container', 'image', 'daemon')])
        with patch.multiple(controller, **fixture['constants']), self.assertRaises(controller.Refused):
            obj.actual_core_image()
        self.assertEqual(obj.guest.call_count, 3)

    def test_public_image_projection_never_exports_extra_metadata(self):
        fixture = image_fixture()
        fixture['image']['private'] = 'private-canary'
        self.assertNotIn('private-canary', json.dumps(check_image_fixture(fixture)))

    def test_public_core_versions_refuse_local_prerelease_and_bare_canaries(self):
        for value in ('2026.10.2+privatecanary', '2026.10.2b1', '2026.10.2rc1', 'bare_private_canary', '2026.10.2-private'):
            self.assertIsNone(controller.public_core_version(value))
        for value in ('landingpage', '2026.9.4', '2026.10.2', '2026.09.0'):
            self.assertEqual(controller.public_core_version(value), value)

class ContainerLifecycleContracts(unittest.TestCase):

    def test_successful_listing_distinguishes_absence_stopped_and_running(self):
        self.assertEqual(controller.parse_core_container_state(container_result()), 'not_created')
        for raw, expected in (('created', 'stopped'), ('exited', 'stopped'), ('running', 'running'), ('paused', 'unknown'), ('restarting', 'unknown'), ('removing', 'unknown'), ('dead', 'unknown')):
            self.assertEqual(controller.parse_core_container_state(container_result(raw)), expected)
        self.assertEqual(controller.parse_core_container_state(container_result('running', 'homeassistant-helper')), 'not_created')

    def test_daemon_failure_truncation_and_malformed_listing_never_mean_absent(self):
        for key, value in (('exitcode', 1), ('exitcode', True), ('signal', 9), ('stderr', b'private-canary'), ('truncated', True), ('stdout', b'not-json'), ('stdout', b'[]'), ('stdout', b'\xff'), ('stdout', b'x' * 65537)):
            result = container_result()
            result[key] = value
            with self.subTest(key=key):
                self.assertEqual(controller.parse_core_container_state(result), 'unknown')
        self.assertEqual(controller.parse_core_container_state(container_result('running', identifier='not-a-docker-id')), 'unknown')
        result = container_result('running')
        result['stdout'] *= 2
        self.assertEqual(controller.parse_core_container_state(result), 'unknown')

    def test_state_transport_uses_bounded_all_container_listing_not_inspect_errors(self):
        obj = instance()
        obj.guest = Mock(return_value=container_result())
        self.assertEqual(obj.core_container_state(12), 'not_created')
        command = obj.guest.call_args.args[0]
        self.assertIn('container ls --all --no-trunc', command)
        self.assertIn('{{json .Names}}', command)
        self.assertNotIn('inspect', command)
        self.assertEqual(obj.guest.call_args.kwargs, {'capture': True})

    def test_absent_container_requires_one_supported_start_and_actual_running_state(self):
        obj = instance()
        obj.management_ready = Mock(return_value=True)
        obj.core_container_state = Mock(side_effect=['not_created', 'running'])
        obj.guest = Mock(return_value=b'{"result":"ok"}')
        obj.start_core()
        self.assertEqual(obj.guest.call_count, 1)
        self.assertEqual(obj.guest.call_args.args[0], controller.HA + ' core start --raw-json')
        record = obj.core_actions[0]
        self.assertIsNone(record['running_before'])
        self.assertEqual(record['container_state_before'], 'not_created')
        self.assertEqual(record['container_state_after'], 'running')
        self.assertTrue(record['running_after'])

    def test_unknown_state_cannot_trigger_start_and_missing_state_cannot_trigger_stop(self):
        for action, state in (('start', 'unknown'), ('stop', 'not_created'), ('stop', 'unknown')):
            obj = instance()
            obj.management_ready = Mock(return_value=True)
            obj.core_container_state = Mock(return_value=state)
            obj.guest = Mock()
            with self.subTest(action=action, state=state), self.assertRaisesRegex(controller.Refused, 'core_action_initial_state_refused'):
                obj.core_action(action)
            obj.guest.assert_not_called()

    def test_start_api_ok_without_running_state_is_incomplete_and_not_retried(self):
        obj = instance()
        obj.management_ready = Mock(return_value=True)
        obj.core_container_state = Mock(return_value='not_created')
        obj.guest = Mock(return_value=b'{"result":"ok"}')
        obj.remaining = Mock(return_value=0.02)
        with self.assertRaisesRegex(controller.Refused, 'core_action_state_deadline_exceeded'):
            obj.start_core()
        self.assertEqual(obj.guest.call_count, 1)
        self.assertEqual(obj.core_actions[0]['container_state_after'], 'not_created')
        self.assertIsNone(obj.core_actions[0]['running_after'])
