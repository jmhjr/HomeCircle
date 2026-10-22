"""Fixed enabled-start evidence schema; no Core/provider imports or I/O."""
import re

INIT_SHA = '1044e86e5ed15dccc73094cf14037c4df51095a0f2cd44e16515b42130c76aa0'
BOUNDARY_CHECKS = (
    'installed_before_runtime_setup', 'patches_intact', 'deny_all_external_aiohttp',
    'deny_all_apple_transports', 'provider_transport_attempts_measured', 'recovery_attempt_seams_measured',
)
BOUNDARY_COUNTS = (
    'life360_sessions_created', 'life360_requests_denied', 'apple_legacy_requests_denied',
    'apple_bounded_requests_denied', 'apple_report_requests_denied', 'other_external_requests_denied',
    'recovery_before_dispatch_calls', 'recovery_command_calls', 'recovery_transport_attempts_denied',
    'supervisor_requests_allowed', 'qa_static_requests_allowed',
)
EXTRA_KEYS = frozenset({
    'runtime_loaded_source_sha256', 'runtime_selection_checked', 'actual_findmy_session_restored',
    'synthetic_photo_preserved', 'static_served_bundle_matches', 'startup_boundary', 'prepared_dependencies',
    'qa_manifest_only_difference', 'qa_manifest_sha256',
})


def require(ok, label):
    if not ok:
        raise ValueError(label)


def digest(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def boundary_proof(value):
    require(type(value) is dict and set(value) == {'schema', 'boundary_revision', *BOUNDARY_CHECKS, *BOUNDARY_COUNTS},
            'enabled_boundary_exact_shape_required')
    require(type(value['schema']) is int and value['schema'] == 1
            and type(value['boundary_revision']) is int and value['boundary_revision'] == 1,
            'enabled_boundary_revision_required')
    require(all(value[name] is True for name in BOUNDARY_CHECKS), 'enabled_boundary_checks_required')
    require(all(type(value[name]) is int and 0 <= value[name] <= 1000000 for name in BOUNDARY_COUNTS),
            'enabled_boundary_count_type_required')
    require(value['life360_sessions_created'] > 0 and value['life360_requests_denied'] > 0
            and sum(value[name] for name in ('apple_legacy_requests_denied', 'apple_bounded_requests_denied',
                                           'apple_report_requests_denied')) > 0,
            'nonvacuous_saved_provider_attempts_required')
    require(all(value[name] == 0 for name in ('recovery_before_dispatch_calls', 'recovery_command_calls',
                                             'recovery_transport_attempts_denied')),
            'startup_recovery_attempt_refused')
    return dict(value)


def enabled_phase_proof(receipt, dependency_fixture, manifest_sha):
    require(type(receipt) is dict and EXTRA_KEYS <= receipt.keys(), 'enabled_phase_proofs_required')
    require(receipt['runtime_loaded_source_sha256'] == INIT_SHA, 'loaded_candidate_source_required')
    require(all(receipt[name] is True for name in ('runtime_selection_checked', 'actual_findmy_session_restored',
                'synthetic_photo_preserved', 'static_served_bundle_matches', 'qa_manifest_only_difference')),
            'enabled_runtime_data_proofs_required')
    require(digest(manifest_sha) and receipt['qa_manifest_sha256'] == manifest_sha, 'qa_manifest_binding_required')
    dependencies = receipt['prepared_dependencies']
    require(type(dependencies) is dict and set(dependencies) == {
        'inventoried_non_bytecode_bytes_checked', 'origins_config_deps', 'normal_bootstrap_library',
        'inventory_sha256', 'inventory_scope'}, 'prepared_dependency_phase_shape_required')
    require(all(dependencies[key] is True for key in ('inventoried_non_bytecode_bytes_checked',
            'origins_config_deps', 'normal_bootstrap_library'))
            and type(dependency_fixture) is dict and digest(dependency_fixture.get('inventory_sha256'))
            and dependencies['inventory_sha256'] == dependency_fixture['inventory_sha256']
            and dependencies['inventory_scope'] == 'dependency_regular_files_excluding_generated_bytecode',
            'prepared_dependency_phase_binding_required')
    result = {key: receipt[key] for key in EXTRA_KEYS}
    result['startup_boundary'] = boundary_proof(receipt['startup_boundary'])
    result['prepared_dependencies'] = dict(dependencies)
    return result
