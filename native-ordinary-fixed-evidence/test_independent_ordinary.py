"""Finite synthetic evidence-consumer contracts; no runtime qualification."""
from copy import deepcopy
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import zipfile

import independent_ordinary as c
from test_person_activity import values as person_activity_examples


def examples(bindings):
    """Schema-valid fictional records, never presented as native evidence."""
    direct = c.literal(bindings.base, 'DIRECT')
    dependencies = {'schema': 1, 'core': '2026.10.2', 'python': '3.14.6',
        'constraints_sha256': c.literal(bindings.base, 'CONSTRAINTS_SHA'), 'constraints_match': True,
        'docker_environment': True, 'ordinary_pip_target_unset': True, 'config_deps_empty': True,
        'closure_count': 24, 'closure_graph_checked': True, 'skip_pip': False,
        'provider_or_native_imports_requested_by_probe': False,
        'closure': {name: {'available': True, 'version': direct.get(name, '1.0'),
            'metadata_system_origin': True, 'constraints_satisfied': True, 'python_satisfied': True}
            for name in c.literal(bindings.base, 'CLOSURE')},
        'direct': {name: {'available': True, 'version': version, 'satisfies_requirement': True,
            'loaded_module_present': False, 'module_system_origin': True, 'origin_probe': 'import_spec'}
            for name, version in direct.items()}}
    boundary = {key: True for key in ('installed_before_product_import', 'patches_intact',
        'deny_all_external_aiohttp', 'python_socket_audit_installed', 'product_manifest_unchanged',
        'normal_requirement_subprocesses_unmodified')}
    boundary.update(dict.fromkeys(('life360_sessions_created', 'life360_requests_denied',
        'apple_legacy_requests_denied', 'apple_bounded_requests_denied', 'apple_report_requests_denied',
        'other_external_requests_denied', 'recovery_before_dispatch_calls', 'recovery_command_calls',
        'recovery_transport_attempts_denied', 'supervisor_requests_allowed', 'qa_static_requests_allowed',
        'socket_external_attempts_denied', 'ordinary_uv_installs_observed'), 0))
    boundary.update(schema=2, boundary_revision=2, life360_sessions_created=1, life360_requests_denied=1,
        apple_legacy_requests_denied=2, ordinary_uv_installs_observed=1,
        loaded_target_kinds=sorted(('life360', 'legacy', 'bounded', 'report', 'guard', 'escrow')))
    phases = {}
    for index, name in enumerate(c.PHASES):
        restored = index >= 2
        counter = 3 if index == 1 else 2
        record = dict.fromkeys(('ready', 'prebackup_exact_match', 'integrity_ok', 'backup_platform_registered',
                               'commit_proven', 'no_backup_failure_issue'), True)
        record.update(prebackup_rows=6, prebackup_sha256='a' * 64, postbackup_marker_rows=6 if index == 1 else 0,
            postbackup_marker_absent=index != 1, postrestore_rows=6 if restored else None,
            postrestore_sha256='b' * 64 if restored else None, postrestore_exact_match=True if restored else None)
        phases[name] = {'schema': 2, 'phase': name, 'outcome': 'passed',
            'generation': 'after_restore' if index == 3 else 'before_restore',
            'process': {'pid': 100 + index, 'start_ticks': 10 * (index + 1)}, 'selected_registry_joins': 4,
            'guard_counter': counter, 'unchanged_product_members': 113, **c.PHASE_FLAGS,
            'normal_dependencies': deepcopy(dependencies), 'startup_boundary': deepcopy(boundary), 'recorder': record,
            'recovery_guard': {'identity_matches_saved_sdk_account': True, 'counter': counter,
                'blocked': restored or counter >= 3, 'review_required': restored, 'witness_absent': restored,
                'attempt_refused_before_body': restored, 'manual_guard_imports': 0,
                'owner_acknowledgments_after_restore': 0}}
    for name, extra in person_activity_examples().items():
        phases[name].update(extra)
    image = {}
    # Capture the independent exact expected image without packet imports.
    with patch.object(c, 'same', side_effect=lambda actual, expected, label: image.update(expected)):
        c.image_check({}, bindings)
    flags = c.literal(bindings.base, 'DEFAULT_RECEIPT_BOOL_KEYS')
    default = {key: key not in {'foreign_options_refused', 'cleanup_failed'} for key in flags}
    default.update(schema=1, mode='default_conditions_instrumented_enabled_saved_storage',
        jobs_option_mutation_requests=0, global_persisted_override=False, unsupported_conditions_override=False,
        network_open_requests=1, network_close_requests=1, network_info_requests=1,
        maximum_cleanup_seconds=90, maximum_network_readiness_seconds=90)
    actions = ['stop', 'start', 'stop', 'start', 'stop', 'start', 'stop', 'stop', 'start', 'stop']
    core = [{'action': name, 'result': 'ok', 'supervisor_running': True, 'relevant_core_jobs_idle': True,
        'running_before': name == 'stop', 'running_after': name == 'start',
        'container_state_before': 'running' if name == 'stop' else 'stopped',
        'container_state_after': 'stopped' if name == 'stop' else 'running'} for name in actions]
    def job(name):
        return {'name': name, 'done': True, 'error_count': 0, 'nodes': 1}
    archive = dict.fromkeys(('saved_photo_bytes_included', 'qa_startup_boundary_archive_verified',
        'no_prepared_dependency_bytes', 'product_manifest_unchanged', 'cache_witness_excluded',
        'database_included', 'candidate_match', 'enabled_entry', 'saved_pair_included', 'saved_config_included',
        'saved_selection_included', 'saved_registry_joins_included', 'saved_person_configuration_included',
        'saved_person_registry_joins_included', 'saved_homecircle_activity_included'), True)
    archive.update(archive_bytes=100, guard_sha256='c' * 64)
    host = {'schema': 2, 'outcome': 'passed', 'phase_names': list(c.PHASES), 'phases': 4,
        'failure_or_final_stage': 'ordinary_unmodified_product_restore_complete', 'failure_type': None,
        'failure_code': None, 'guest_failures': [], 'actual_core': '2026.10.2', 'actual_supervisor': '2026.10.3',
        **dict.fromkeys(c.HOST_TRUE, True), **dict.fromkeys(c.HOST_FALSE, False), **dict.fromkeys(c.HOST_ZERO, 0),
        'provenance': bindings.provenance(), 'current_core_image': image,
        'fresh_owned_config': {'files': 1, 'bytes': 1, 'children': 1, 'owner_accounts_found': False,
            'candidate_previously_present': False, 'fresh_config_reset': True, 'mount_directory_preserved': True},
        'normal_initial_requirement_window': {'opened': True, 'closed': True,
            'normal_ha_requirement_install': True, 'maximum_seconds': 750}, 'default_restore_conditions': default,
        'network_transitions': ['closed_before_synthetic_seed', 'opened_for_ordinary_requirements',
            'closed_after_ordinary_requirements', 'opened_for_default_restore', 'closed_after_default_restore'],
        'network_boundary': {'link_closed': True, 'before_probe_connected': True, 'closed_probe_connected': False,
            'guest_agent_remained_available': True, 'closed_probe_observations': 10}, 'core_actions': core,
        'backup_requests': [{'action': name, 'exit_code': 0, 'signal': None, 'result': 'ok', 'stdout_json': True,
            'output_truncated': False, 'api_error': {'type': 'unclassified', 'categories': []},
            'stderr_error': {'type': 'unclassified', 'categories': []}, 'exact_job_id_returned': True}
            for name in ('create', 'restore')],
        'backup': {'result': 'ok', 'type': 'partial', 'homeassistant_version': '2026.10.2', 'database_included': True,
            'protected': False, 'compressed': False, 'job': job('backup_manager_partial_backup'), 'archive': archive},
        'restore': {'result': 'ok', 'job': job('backup_manager_partial_restore'), 'qa_startup_boundary_required': True},
        'host_elapsed_seconds': 100}
    checks = c.literal(bindings.base, 'STORAGE_CHECKS')
    common = c.literal(bindings.base, 'COMMON_STORAGE_CHECKS')
    names = ('seed', 'mutate', 'validate_restored', 'validate_restart')
    host['storage_contexts'] = [{'schema': 1, 'action': name, 'outcome': 'passed',
        'image': c.literal(bindings.raw['storage_context.py'], 'IMAGE'), 'managed_core_same_stopped_process': True,
        'local_image_verified': True, 'owned_identity_security_mount_checked': True, 'offline_network_none': True,
        'bound_storage_transfer_stdin': True, 'owned_container_removed': True, 'maximum_total_seconds': 60} for name in names]
    host['storage_results'] = {name: {'schema': 1, 'action': name, 'outcome': 'passed', 'entry_disabled': False,
        'managed_candidate_imported': False, 'synthetic_only': True, 'source_files_verified': True,
        'storage_checks': {**dict.fromkeys(common, True), **checks[name], 'guard_counter': 3 if name == 'mutate' else 2},
        'private_proof_written': name in {'seed', 'mutate'}} for name in names}
    return {'host.json': host, **{name + '.json': value for name, value in phases.items()}}


class ConsumerContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bindings = c.Bindings(Path('../fixture-r1'), Path('../workflow-r2.yml'))
        cls.values = examples(cls.bindings)

    def test_person_activity_archive_and_host_gates_are_required(self):
        for key in ('real_person_association_restore_qualified', 'homecircle_activity_restore_qualified'):
            changed = deepcopy(self.values); changed['host.json'][key] = False
            with self.subTest(key=key), self.assertRaises(c.EvidenceRefused):
                c.validate_receipts(changed, self.bindings)
        for key in ('saved_person_configuration_included', 'saved_person_registry_joins_included',
                    'saved_homecircle_activity_included'):
            changed = deepcopy(self.values); changed['host.json']['backup']['archive'][key] = False
            with self.subTest(key=key), self.assertRaises(c.EvidenceRefused):
                c.validate_receipts(changed, self.bindings)

    def test_valid_synthetic_schema_and_actual_frozen_bytes_pass_without_fixture_imports(self):
        before = set(sys.modules)
        self.assertEqual(c.validate_receipts(deepcopy(self.values), self.bindings)['outcome'], 'passed')
        self.assertEqual(len(self.bindings.inventory), 113)
        self.assertFalse({'controller', 'legacy_controller', 'accept_saved_storage'} & (set(sys.modules) - before))

    def test_known_coordinated_hash_and_float_false_positives_are_refused(self):
        mutations = []
        value = deepcopy(self.values); value['host.json']['provenance']['candidate_payload_sha256'] = 'f' * 64; mutations.append(value)
        value = deepcopy(self.values); value['host.json']['provenance']['original_manifest_sha256'] = 'f' * 64; mutations.append(value)
        value = deepcopy(self.values); value['baseline_enabled.json']['unchanged_product_members'] = 113.0; mutations.append(value)
        value = deepcopy(self.values); value['host.json']['provenance']['unchanged_product_members'] = 113.0; mutations.append(value)
        value = deepcopy(self.values); value['baseline_enabled.json']['normal_dependencies']['closure']['life360']['private_extra'] = 'PRIVATE-CANARY'; mutations.append(value)
        value = deepcopy(self.values); value['host.json']['guest_failures'] = [{'failure_type': 'ValueError'}]; mutations.append(value)
        for value in mutations:
            with self.subTest(), self.assertRaises(c.EvidenceRefused):
                c.validate_receipts(value, self.bindings)

    def test_restore_guard_manual_repair_and_false_admission_are_refused(self):
        for phase in c.PHASES[2:]:
            for field, changed in (('blocked', False), ('review_required', False), ('witness_absent', False),
                                   ('attempt_refused_before_body', False), ('manual_guard_imports', 1)):
                value = deepcopy(self.values);value[phase + '.json']['recovery_guard'][field] = changed
                with self.subTest(phase=phase, field=field), self.assertRaises(c.EvidenceRefused):
                    c.validate_receipts(value, self.bindings)

    def test_requirement_installer_observation_and_manifest_scope_are_required(self):
        for phase in (c.PHASES[0], c.PHASES[2]):
            value = deepcopy(self.values);value[phase + '.json']['startup_boundary']['ordinary_uv_installs_observed'] = 0
            with self.assertRaises(c.EvidenceRefused):c.validate_receipts(value, self.bindings)
        value = deepcopy(self.values);value['host.json']['backup']['archive']['cache_witness_excluded'] = False
        with self.assertRaises(c.EvidenceRefused):c.validate_receipts(value, self.bindings)

    def test_extra_nested_fields_and_loose_numeric_types_are_refused(self):
        for path, changed in ((('host.json', 'backup', 'job', 'nodes'), True),
                (('host.json', 'storage_contexts', 0, 'maximum_total_seconds'), 60.0),
                (('restart_enabled.json', 'recorder', 'private_extra'), 'PRIVATE-CANARY'),
                (('automatic_restored_enabled.json', 'process', 'private_extra'), 'PRIVATE-CANARY')):
            value = deepcopy(self.values);parent = value
            for key in path[:-1]:parent = parent[key]
            parent[path[-1]] = changed
            with self.subTest(), self.assertRaises(c.EvidenceRefused):c.validate_receipts(value, self.bindings)

    def test_json_duplicate_nonfinite_and_deep_payloads_are_refused(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'[' * 22 + b'0' + b']' * 22):
            with self.subTest(), self.assertRaises(c.EvidenceRefused):c.strict_json(raw)

    def test_zip_duplicate_or_extra_members_are_refused(self):
        for extra in ('host.json', 'private.json'):
            output = io.BytesIO()
            with zipfile.ZipFile(output, 'w') as archive:
                for name in c.RECEIPTS:archive.writestr(name, '{}')
                archive.writestr(extra, '{}')
            with self.subTest(), self.assertRaises(c.EvidenceRefused):c.artifact_receipts(output.getvalue())

    def test_root_metadata_requires_separate_exact_run_anchor(self):
        metadata = dict(schema=1, run_id=123, run_attempt=1, head_sha='a' * 40,
            branch='codex/native-amd64-validation', event='push', workflow_path=c.WORKFLOW,
            workflow_sha256=c.WORKFLOW_SHA, artifact_name=c.ARTIFACT, github_digest_verified=True,
            status='completed', conclusion='success', artifact_id=123, artifact_zip_sha256='b' * 64)
        with patch.object(c, 'HEAD', 'a' * 40), patch.object(c, 'RUN', 123), patch.object(c, 'EVENT', 'push'):
            c.metadata_check(metadata, 'b' * 64)
            for key, changed in (('run_id', 123.0), ('head_sha', 'c' * 40), ('github_digest_verified', False),
                                  ('artifact_zip_sha256', 'd' * 64)):
                with self.subTest(), self.assertRaises(c.EvidenceRefused):
                    c.metadata_check({**metadata, key: changed}, 'b' * 64)
            with self.assertRaises(c.EvidenceRefused):
                c.metadata_check({**metadata, 'event': 'workflow_dispatch'}, 'b' * 64)
        with patch.object(c, 'HEAD', 'a' * 40), patch.object(c, 'RUN', 123), patch.object(c, 'EVENT', 'workflow_dispatch'):
            c.metadata_check({**metadata, 'event': 'workflow_dispatch'}, 'b' * 64)
            with self.assertRaises(c.EvidenceRefused):
                c.metadata_check(metadata, 'b' * 64)
        with patch.object(c, 'HEAD', 'a' * 40), patch.object(c, 'RUN', 123), patch.object(c, 'EVENT', ''):
            with self.assertRaises(c.EvidenceRefused):
                c.metadata_check(metadata, 'b' * 64)


if __name__ == '__main__':
    unittest.main()
