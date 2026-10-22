"""Scoped five-receipt acceptor; external source/artifact binding is separate."""
import json
from pathlib import Path
import stat
import sys

# Explicitly add only this frozen directory, including under python -I.
sys.path.insert(0,str(Path(__file__).resolve().parent))

from controller import PHASES, CANDIDATE_FILES, CANDIDATE_SHA, SOURCE_COMMIT, _PERSON
from legacy_controller import Refused, project_default_receipt, require
from storage_context import accept_contexts


def accept(values):
    require(type(values) is dict and set(values)=={'host',*PHASES},'ordinary_five_receipts_required')
    host=values['host']
    require(host.get('schema')==2 and type(host['schema']) is int and host.get('outcome')=='passed'
        and host.get('phase_names')==list(PHASES) and type(host.get('phases')) is int and host['phases']==4,
        'ordinary_native_outcome_refused')
    for key in ('actual_kvm_confirmed','ordinary_unmodified_product_partial_restore_qualified',
        'normal_managed_dependencies','product_manifest_unchanged','automatic_guard_rollback_block',
        'environmental_transport_instrumentation','real_person_association_restore_qualified',
        'homecircle_activity_restore_qualified','qemu_stopped','private_workspace_removed'):
        require(host.get(key) is True,'ordinary_native_required_proof')
    for key in ('prepared_dependency_preload_used','real_provider_accounts_configured','owner_credentials_used',
        'production_configuration_used','provider_authentication_after_restore_tested','provider_session_renewal_tested',
        'full_system_restore_tested','full_encrypted_cloud_backup_tested','stable_release_approval',
        'candidate_hacs_download_tested','cleanup_failed'):
        require(host.get(key) is False,'ordinary_scope_or_cleanup_refused')
    for key in ('manual_guard_imports','guard_exports','owner_acknowledgments_after_restore'):
        require(type(host.get(key)) is int and host[key]==0,'ordinary_manual_repair_forbidden')
    require(host.get('actual_core')=='2026.10.2' and host.get('actual_supervisor')=='2026.10.3',
        'ordinary_runtime_version_refused')
    provenance=host.get('provenance')
    require(type(provenance) is dict and provenance.get('candidate_source_commit')==SOURCE_COMMIT
        and provenance.get('candidate_zip_sha256')==CANDIDATE_SHA
        and type(provenance.get('candidate_files')) is int and provenance['candidate_files']==CANDIDATE_FILES
        and provenance.get('qa_manifest_adaptation') is False and provenance.get('prepared_dependency_preload') is False
        and provenance.get('unchanged_product_members')==CANDIDATE_FILES,'ordinary_candidate_scope_refused')
    project_default_receipt(host.get('default_restore_conditions'),complete=True)
    accept_contexts(host.get('storage_contexts'))
    processes=[]
    for phase in PHASES:
        value=values[phase]
        require(value.get('schema')==2 and type(value['schema']) is int and value.get('phase')==phase
            and value.get('outcome')=='passed' and value.get('product_manifest_unchanged') is True
            and value.get('unchanged_product_members')==CANDIDATE_FILES
            and value.get('storage_raw_matches_expected') is True and value.get('selected_registry_joins')==4,
            'ordinary_phase_proof_refused')
        person=_PERSON.person_proof(value.get('person_associations'),phase)
        activity=_PERSON.activity_proof(value.get('homecircle_activity'),phase)
        if phase!=PHASES[0]:
            baseline=values[PHASES[0]]
            require(all(activity[key]==baseline['homecircle_activity'][key] for key in
                ('B_events','B_sha256','B_transitions')),'person_activity_baseline_cohort_required')
            require((person['saved_associations_sha256']==baseline['person_associations']['saved_associations_sha256'])
                is (phase!='mutated_enabled'),'person_activity_association_rollback_required')
        if phase in PHASES[2:]:
            require(all(activity[key]==values[PHASES[1]]['homecircle_activity'][key] for key in
                ('M_events','M_sha256','M_transitions')),'person_activity_mutation_cohort_required')
        if phase==PHASES[3]:
            require(all(activity[key]==values[PHASES[2]]['homecircle_activity'][key] for key in
                ('R_events','R_sha256','R_transitions')),'person_activity_restart_cohort_required')
        restored=phase in PHASES[2:]
        counter=3 if phase=='mutated_enabled' else 2
        expected={'identity_matches_saved_sdk_account':True,'counter':counter,'blocked':restored or counter>=3,
            'review_required':restored,'witness_absent':restored,'attempt_refused_before_body':restored,
            'manual_guard_imports':0,'owner_acknowledgments_after_restore':0}
        require(value.get('recovery_guard')==expected
            and all(type(value['recovery_guard'][k]) is type(v) for k,v in expected.items()),'ordinary_guard_block_required')
        process=value.get('process')
        require(type(process) is dict and set(process)=={'pid','start_ticks'}
            and all(type(v) is int and v>0 for v in process.values()),'ordinary_core_process_refused')
        processes.append(process['start_ticks'])
    require(processes==sorted(set(processes)),'ordinary_four_distinct_processes_required')
    require(host.get('backup',{}).get('archive',{}).get('cache_witness_excluded') is True,
        'ordinary_cache_witness_archive_exclusion_required')
    require(all(host.get('backup',{}).get('archive',{}).get(key) is True for key in
        ('saved_person_configuration_included','saved_person_registry_joins_included','saved_homecircle_activity_included')),
        'person_activity_actual_archive_required')
    return {'schema':2,'outcome':'passed','scope':'ordinary_unmodified_product_synthetic_person_activity_partial_restore',
        'environmental_transport_instrumentation':True,'automatic_restore_guard_block_verified':True,
        'manual_guard_repair_used':False,'real_person_association_restore_verified':True,
        'homecircle_activity_restore_verified':True,'real_provider_authentication_qualified':False,
        'full_encrypted_cloud_backup_qualified':False,'stable_release_approval':False}


def read(root):
    require(root.is_dir() and not root.is_symlink(),'ordinary_receipt_directory_refused')
    require({p.name for p in root.iterdir()}=={'host.json',*(p+'.json' for p in PHASES)},'ordinary_receipt_members_refused')
    values={}
    def unique(pairs):
        value={}
        for key,item in pairs:
            require(key not in value,'ordinary_duplicate_json_key')
            value[key]=item
        return value
    for name in ('host',*PHASES):
        path=root/(name+'.json');info=path.lstat()
        require(stat.S_ISREG(info.st_mode) and not path.is_symlink() and info.st_nlink==1
            and 0<info.st_size<=1024**2,'ordinary_receipt_file_refused')
        values[name]=json.loads(path.read_bytes(),object_pairs_hook=unique)
    return values


if __name__=='__main__':
    try:
        require(len(sys.argv)==2,'ordinary_receipt_arguments_refused')
        print(json.dumps(accept(read(Path(sys.argv[1]))),sort_keys=True))
    except (Refused,OSError,ValueError,KeyError,TypeError):
        print('{"schema":2,"outcome":"refused"}')
        raise SystemExit(1)
