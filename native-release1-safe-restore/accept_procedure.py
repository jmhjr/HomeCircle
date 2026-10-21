"""Plain operational procedure acceptance; no safety-negative green shortcut."""
import json
from pathlib import Path
import re
import sys

PHASES = ('initialize','initial_restart','quarantine','mutate','automatic_disabled',
          'repaired_disabled','reenabled','restart')
CANDIDATE = '004c9bc4a968ad395e18033837cb42f5bd1d8719a8d90fc778fd20be4ff08f97'


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def accept(host, phases):
    require(type(host) is dict and host.get('schema') == 1 and host.get('outcome') == 'passed'
            and host.get('phases') == 8 and host.get('failure_or_final_stage') == 'safe_disabled_restore_complete'
            and host.get('failure_code') is None and host.get('failure_type') is None, 'incomplete_procedure')
    require(set(phases) == set(PHASES), 'exact_eight_phases')
    for key in ('actual_kvm_confirmed','host_newest_guard_retained','guard_repaired_before_enable',
                'normal_managed_dependencies','tested_disabled_entry_partial_restore_procedure',
                'qemu_stopped','private_workspace_removed'):
        require(host.get(key) is True,'missing_required_host_gate')
    for key in ('cleanup_failed','prepared_dependency_preload_used','ordinary_enabled_restore_safety_accepted',
                'automatic_guard_antirollback','provider_request_attempt_counts_measured',
                'recovery_proof_attempt_counts_measured','owner_credentials_used','provider_accounts_configured',
                'production_configuration_used','full_encrypted_cloud_backup_tested','stable_release_approval',
                'candidate_hacs_download_tested','candidate_release_zip_transport_tested'):
        require(host.get(key) is False,'scope_or_cleanup_not_qualified')
    require(host.get('actual_core') == '2026.10.2'
            and host.get('actual_supervisor') == '2026.10.3', 'wrong_runtime')
    image=host.get('current_core_image',{})
    require(image.get('identity_model') == 'containerd_index_with_verified_stored_oci_chain'
            and image.get('official_index_digest') == 'sha256:45f009d6ff1061971102e81f0802cf2762bdd5c5007231c938bd36030cbd0a12'
            and image.get('verified_oci_config_digest') == 'sha256:e1acee126eee45b3007494ad7f806d12535dc7d733624b681ed29a505f8c2b98'
            and image.get('stored_objects_hashed') == 3 and image.get('image_rootfs_matches_verified_config') is True,
            'stored_current_image_required')
    actions=host.get('core_actions',[])
    require([x.get('action') for x in actions] == ['stop','start','stop','start','stop','start','stop','stop','start','stop','start','stop']
            and all(x.get('result') == 'ok' and x.get('supervisor_running') is True
                    and x.get('relevant_core_jobs_idle') is True for x in actions), 'managed_controls_incomplete')
    require(host.get('network_transitions') == ['closed_before_restore','reopen_after_repaired_disabled','closed_before_final_restart']
            and host.get('network_boundary',{}).get('link_closed') is True
            and host['network_boundary'].get('closed_probe_connected') is False
            and host['network_boundary'].get('closed_probe_observations',0) >= 5, 'network_procedure_not_proven')
    provenance = host.get('provenance',{})
    require(provenance.get('candidate_zip_sha256') == CANDIDATE and provenance.get('candidate_files') == 113
            and provenance.get('candidate_source_commit') == '91ae59106a661143b770d7a3564d363c7c11a7dd'
            and provenance.get('release_published') is False, 'exact_preview_input')
    requests = host.get('backup_requests',[])
    require(len(requests) == 2 and [x.get('action') for x in requests] == ['create','restore']
            and all(x.get('result') == 'ok' and x.get('exit_code') == 0 and x.get('exact_job_id_returned') is True
                    and x.get('output_truncated') is False and x.get('signal') is None for x in requests), 'backup_operations_incomplete')
    archive = host.get('backup',{}).get('archive',{})
    require(archive.get('disabled_entry') is True and archive.get('database_included') is True
            and archive.get('candidate_match') is True, 'prepared_partial_archive_unproven')
    restoration = host.get('restore',{})
    require(restoration.get('host_copy_outside_entire_guest') is True
            and restoration.get('repaired_before_enable') is True, 'host_retention_or_repair_unproven')
    old, newest = archive.get('guard_sha256'), restoration.get('promoted_newest_guard_sha256')
    require(all(isinstance(x,str) and re.fullmatch(r'[0-9a-f]{64}',x) for x in (old,newest))
            and old != newest and restoration.get('restored_old_guard_sha256') == old, 'distinct_guard_copies_required')
    before_enable=phases['repaired_disabled'].get('normal_dependencies_before_enable',{})
    require(before_enable.get('config_deps_empty') is True and before_enable.get('ordinary_pip_target_unset') is True
            and before_enable.get('core') == '2026.10.2' and before_enable.get('skip_pip') is False, 'normal_before_enable_probe_required')
    initial = phases['initialize']
    for name in PHASES:
        phase = phases[name]
        require(phase.get('schema') == 1 and phase.get('phase') == name and phase.get('outcome') == 'passed', 'phase_failed')
        active = name in {'initialize','initial_restart','reenabled','restart'}
        require(phase.get('entry_disabled') is (not active) and phase.get('entry_loaded') is active, 'entry_state_order')
        require(phase.get('provider_request_attempt_counts_measured') is False
                and phase.get('recovery_proof_attempt_counts_measured') is False, 'unmeasured_request_scope')
        guard = phase.get('guard',{})
        latest = name in {'mutate','repaired_disabled','reenabled','restart'}
        require(guard.get('sha256') == (newest if latest else old)
                and guard.get('unresolved') == guard.get('rejected') == (3 if latest else 2)
                and guard.get('pending') == guard.get('uncertain') == 0 and guard.get('blocked') is latest,
                'guard_timeline_wrong')
        if name in {'repaired_disabled','reenabled','restart'}:
            require(guard.get('api_status_checked') is True, 'actual_repaired_guard_api_required')
        if name == 'automatic_disabled':
            require(guard.get('api_status_checked') is False and phase.get('candidate_imported') is False, 'automatic_observation_not_inert')
        else:
            require(phase.get('nonempty_options') is True and phase.get('nonempty_place_and_picture') is True
                    and phase.get('package_files_count') == 113, 'real_nonempty_restored_settings')
            require(phase.get('recorder',{}).get('prebackup_exact_match') is True
                    and phase['recorder'].get('integrity_ok') is True and phase['recorder'].get('commit_proven') is True,
                    'committed_history_missing')
            history=phase['recorder']
            require(history.get('prebackup_rows') == initial['recorder']['prebackup_rows']
                    and history.get('prebackup_sha256') == initial['recorder']['prebackup_sha256'], 'prebackup_rows_changed')
            if name != 'mutate':
                require(history.get('postbackup_marker_rows') == 0 and history.get('postbackup_marker_absent') is True,
                        'postbackup_rows_not_removed')
            else:
                require(type(history.get('postbackup_marker_rows')) is int and history['postbackup_marker_rows'] > 0
                        and history.get('postbackup_marker_absent') is False, 'postbackup_mutation_missing')
        if name != 'mutate':
            require(phase.get('snapshot_sha256') == initial.get('snapshot_sha256'),'restored_selection_identity_changed')
        if active:
            require(isinstance(phase.get('resource_url_type_sha256'),str)
                    and re.fullmatch(r'[0-9a-f]{64}',phase['resource_url_type_sha256'])
                    and phase['resource_url_type_sha256'] == initial.get('resource_url_type_sha256'), 'owned_resource_url_type_changed')
            require(phase.get('static_served_bundle_matches') is True
                    and phase.get('served_bundle_sha256') == '77f429fb1908acc21cde2c89614f05f12c60a09bb37fa6ca78a1830ec07c6f91'
                    and phase.get('normal_dependencies',{}).get('closure_graph_checked') is True
                    and phase['normal_dependencies'].get('config_deps_empty') is True
                    and phase['normal_dependencies'].get('skip_pip') is False, 'normal_served_runtime_required')
    for before,after in [('initial_restart','quarantine'),('initial_restart','mutate'),('repaired_disabled','reenabled')]:
        require(phases[before]['process'] == phases[after]['process'], 'unexpected_managed_process_replacement')
    for before, after in [('initialize','initial_restart'),('mutate','automatic_disabled'),
                          ('automatic_disabled','repaired_disabled'),('reenabled','restart')]:
        require(phases[after]['process']['start_ticks'] > phases[before]['process']['start_ticks'], 'distinct_managed_processes_required')
    require(phases['restart']['owned_resource_id_sha256'] == phases['reenabled']['owned_resource_id_sha256']
            , 'reenabled_owned_resource_restart_continuity')
    require(phases['restart']['recorder']['postrestore_sha256'] == phases['reenabled']['recorder']['postrestore_sha256']
            and phases['restart']['recorder']['postrestore_exact_match'] is True, 'new_history_restart_missing')
    return {'schema':1,'outcome':'passed','tested_disabled_entry_partial_restore_procedure':True,
            'ordinary_enabled_restore_safety_accepted':False,'automatic_guard_antirollback':False,
            'provider_request_attempt_counts_measured':False,'recovery_proof_attempt_counts_measured':False,
            'stable_release_approval':False}


if __name__ == '__main__':
    root = Path(sys.argv[1])
    value = accept(json.loads((root/'host.json').read_bytes()),
                   {name:json.loads((root/(name+'.json')).read_bytes()) for name in PHASES})
    print(json.dumps(value,sort_keys=True))
