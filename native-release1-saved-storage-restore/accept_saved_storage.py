"""Strict five-phase disabled synthetic saved-storage acceptance; no enabled shortcut."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from storage_context import digest_value
from controller import PHASES, SOURCE_COMMIT, CANDIDATE_SHA, STORAGE_ACTIONS, project_storage_result, project_recorder, project_default_receipt
from guard_context import accept_contexts as accept_guard_contexts
from storage_context import accept_contexts as accept_storage_contexts

HOST_KEYS = frozenset({"default_conditions_disabled_synthetic_restore_qualified", "default_supervisor_conditions_used", "manual_newest_guard_repair_required","default_restore_conditions", "temporary_global_offline_conditions", "ordinary_default_supervisor_restore_qualified", "tested_default_conditions_disabled_saved_storage_restore", "unsupported_conditions_override_used", 'qemu_stopped', 'host_newest_guard_retained', 'network_transitions', 'actual_kvm_confirmed', 'direct_candidate_installs', 'host_elapsed_seconds', 'private_workspace_removed', 'provider_authentication_after_restore_tested', 'automatic_guard_antirollback', 'real_provider_accounts_configured', 'restore', 'full_system_restore_tested', 'full_encrypted_cloud_backup_tested', 'backup', 'storage_results', 'recovery_proof_attempt_counts_measured', 'actual_core', 'core_actions', 'failure_code', 'phases', 'provider_request_attempt_counts_measured', 'provider_session_renewal_tested', 'failure_type', 'schema', 'candidate_hacs_download_tested', 'actual_supervisor', 'provenance', 'storage_contexts', 'fresh_owned_config', 'tested_disabled_entry_saved_storage_restore', 'guard_transfer_contexts', 'owner_credentials_used', 'failure_or_final_stage', 'candidate_release_zip_transport_tested', 'current_core_image', 'backup_requests', 'normal_managed_dependencies', 'provider_activation_after_restore_tested', 'stable_release_approval', 'synthetic_saved_accounts_seeded', 'outcome', 'network_boundary', 'cleanup_failed', 'production_configuration_used', 'ordinary_enabled_restore_safety_accepted', 'candidate_transport', 'initial_managed_environment', 'prepared_dependency_preload_used', 'guard_repaired_before_storage_load'})
PHASE_KEYS = frozenset({'closed_boot_grant_verified','guard_repaired_before_storage_load', 'generation', 'entry_loaded', 'process', 'candidate_imported', 'package_files_count', 'nonempty_place', 'nonempty_options', 'phase', 'explicit_registry_joins_checked', 'package_payload_sha256', 'recovery_proof_attempt_counts_measured', 'recorder', 'provider_request_attempt_counts_measured', 'guard_counter', 'storage_raw_matches_expected', 'schema', 'selected_registry_joins', 'entry_disabled', 'outcome', 'ha_config_entry_saved'})
AUTOMATIC_KEYS = frozenset({'closed_boot_grant_verified','recovery_proof_attempt_counts_measured', 'guard_repaired_before_storage_load', 'generation', 'entry_loaded', 'guard_counter', 'schema', 'provider_request_attempt_counts_measured', 'phase', 'process', 'entry_disabled', 'selected_registry_joins', 'candidate_imported', 'outcome', 'ha_config_entry_saved', 'storage_raw_matches_expected', 'explicit_registry_joins_checked'})

FALSE_GATES = ("cleanup_failed", "real_provider_accounts_configured", "owner_credentials_used", "production_configuration_used",
    "normal_managed_dependencies", "prepared_dependency_preload_used", "ordinary_enabled_restore_safety_accepted",
    "automatic_guard_antirollback", "provider_activation_after_restore_tested", "provider_authentication_after_restore_tested",
    "provider_session_renewal_tested", "provider_request_attempt_counts_measured", "recovery_proof_attempt_counts_measured",
    "full_system_restore_tested", "full_encrypted_cloud_backup_tested", "stable_release_approval", "ordinary_default_supervisor_restore_qualified",
    "candidate_hacs_download_tested", "candidate_release_zip_transport_tested", "temporary_global_offline_conditions", "unsupported_conditions_override_used")

def require(ok, code):
    if not ok:
        raise ValueError(code)

def accept(host, phases):
    require(type(host) is dict and set(host) == HOST_KEYS and host.get("schema") == 1 and type(host["schema"]) is int
            and host.get("outcome") == "passed" and host.get("phases") == 5 and type(host["phases"]) is int
            and host.get("failure_or_final_stage") == "default_conditions_saved_storage_restore_complete"
            and host.get("failure_code") is None and host.get("failure_type") is None, "incomplete_saved_storage")
    require(type(phases) is dict and set(phases) == set(PHASES), "exact_five_phases_required")
    project_default_receipt(host.get("default_restore_conditions"), complete=True)
    require(digest_value(CANDIDATE_SHA), "qualified_candidate_binding_required")
    for key in ("actual_kvm_confirmed", "host_newest_guard_retained", "guard_repaired_before_storage_load",
                "tested_disabled_entry_saved_storage_restore", "synthetic_saved_accounts_seeded", "qemu_stopped", "private_workspace_removed",
                "tested_default_conditions_disabled_saved_storage_restore", "default_conditions_disabled_synthetic_restore_qualified", "default_supervisor_conditions_used", "manual_newest_guard_repair_required"):
        require(host.get(key) is True, "missing_required_host_gate")
    for key in FALSE_GATES:
        require(host.get(key) is False, "scope_or_cleanup_not_qualified")
    require(host.get("actual_core") == "2026.10.2" and host.get("actual_supervisor") == "2026.10.3"
            and host.get("initial_managed_environment") == {"api_core": "2026.10.2", "container_core": "2026.10.2", "supervisor": "2026.10.3"},
            "strict_managed_versions_required")
    image=host.get("current_core_image", {})
    require(image.get("identity_model") == "containerd_index_with_verified_stored_oci_chain"
            and image.get("official_index_digest") == "sha256:45f009d6ff1061971102e81f0802cf2762bdd5c5007231c938bd36030cbd0a12"
            and image.get("verified_oci_config_digest") == "sha256:e1acee126eee45b3007494ad7f806d12535dc7d733624b681ed29a505f8c2b98"
            and image.get("stored_objects_hashed") == 3 and type(image["stored_objects_hashed"]) is int
            and image.get("image_rootfs_matches_verified_config") is True, "verified_official_image_required")
    provenance=host.get("provenance", {})
    require(provenance.get("candidate_source_commit") == SOURCE_COMMIT and provenance.get("candidate_zip_sha256") == CANDIDATE_SHA
            and provenance.get("candidate_files") == 113 and type(provenance["candidate_files"]) is int
            and provenance.get("release_published") is False, "exact_candidate_required")
    require(host.get("network_transitions") == ["closed_before_saved_storage", "opened_for_default_restore", "closed_after_default_restore"]
            and host.get("network_boundary", {}).get("link_closed") is True
            and host["network_boundary"].get("closed_probe_connected") is False
            and type(host["network_boundary"].get("closed_probe_observations")) is int
            and host["network_boundary"]["closed_probe_observations"] >= 5, "scoped_default_restore_network_required")
    actions=host.get("core_actions", [])
    expected_actions=["stop","start","stop","start","stop","start","stop","stop","start","stop","start","stop"]
    require(type(actions) is list and [value.get("action") for value in actions] == expected_actions
            and all(value.get("result") == "ok" and value.get("supervisor_running") is True
                    and value.get("relevant_core_jobs_idle") is True for value in actions), "managed_controls_incomplete")
    requests=host.get("backup_requests", [])
    require(type(requests) is list and len(requests)==2 and [value.get("action") for value in requests]==["create","restore"]
            and all(value.get("result")=="ok" and value.get("exit_code")==0 and type(value["exit_code"]) is int
                    and value.get("exact_job_id_returned") is True and value.get("output_truncated") is False
                    and value.get("signal") is None for value in requests), "backup_operations_incomplete")
    archive=host.get("backup", {}).get("archive", {})
    for key in ("database_included", "candidate_match", "disabled_entry", "saved_pair_included", "saved_config_included",
                "saved_selection_included", "saved_registry_joins_included"):
        require(archive.get(key) is True, "saved_storage_archive_unproven")
    restoration=host.get("restore", {})
    require(restoration.get("host_copy_outside_entire_guest") is True
            and restoration.get("repaired_before_storage_load") is True
            and restoration.get("restored_old_guard_sha256")==archive.get("guard_sha256")
            and digest_value(archive.get("guard_sha256")) and digest_value(restoration.get("promoted_newest_guard_sha256"))
            and restoration.get("promoted_newest_guard_sha256") != archive.get("guard_sha256"), "newest_guard_retention_required")
    accept_guard_contexts(host.get("guard_transfer_contexts"))
    accept_storage_contexts(host.get("storage_contexts"))
    storage=host.get("storage_results")
    require(type(storage) is dict and set(storage)==set(STORAGE_ACTIONS), "four_storage_actions_required")
    for action in STORAGE_ACTIONS:
        project_storage_result(storage[action], action)
    previous_ticks=0
    first_record=None
    restored_record=None
    for name in PHASES:
        phase=phases[name]
        require(type(phase) is dict and set(phase) == (AUTOMATIC_KEYS if name == "automatic_restored_disabled" else PHASE_KEYS)
                and type(phase.get("schema")) is int and phase["schema"]==1
                and phase.get("phase")==name and phase.get("outcome")=="passed"
                and phase.get("generation")== ("before_restore" if name in PHASES[:3] else "after_restore"), "phase_identity_wrong")
        require(phase.get("entry_disabled") is True and phase.get("entry_loaded") is False
                and phase.get("candidate_imported") is False and phase.get("ha_config_entry_saved") is True
                and phase.get("closed_boot_grant_verified") is True and phase.get("storage_raw_matches_expected") is True
                and phase.get("explicit_registry_joins_checked") is True and phase.get("selected_registry_joins")==4
                and type(phase["selected_registry_joins"]) is int
                and phase.get("provider_request_attempt_counts_measured") is False
                and phase.get("recovery_proof_attempt_counts_measured") is False, "disabled_unimported_storage_required")
        count=2 if name in {"baseline_disabled", "automatic_restored_disabled"} else 3
        require(phase.get("guard_counter")==count and type(phase["guard_counter"]) is int
                and phase.get("guard_repaired_before_storage_load") is (name in PHASES[3:]), "guard_order_wrong")
        process=phase.get("process")
        require(type(process) is dict and set(process)=={"pid","start_ticks"}
                and all(type(value)is int and value>0 for value in process.values())
                and process["start_ticks"]>previous_ticks, "distinct_core_processes_required")
        previous_ticks=process["start_ticks"]
        if name=="automatic_restored_disabled":
            require("recorder" not in phase, "automatic_boot_must_be_inert")
            continue
        require(phase.get("package_files_count")==113 and type(phase["package_files_count"]) is int
                and digest_value(provenance.get("candidate_payload_sha256"))
                and phase.get("package_payload_sha256") == provenance["candidate_payload_sha256"]
                and phase.get("nonempty_options") is True and phase.get("nonempty_place") is True, "nonempty_saved_configuration_required")
        record=project_recorder(phase.get("recorder"))
        if first_record is None:
            first_record=record
        require(record["prebackup_rows"]==first_record["prebackup_rows"]
                and record["prebackup_sha256"]==first_record["prebackup_sha256"], "prebackup_history_changed")
        if name=="mutated_disabled":
            require(record["postbackup_marker_rows"]>0 and record["postbackup_marker_absent"] is False, "postbackup_mutation_not_proven")
        else:
            require(record["postbackup_marker_rows"]==0 and record["postbackup_marker_absent"] is True, "postbackup_rows_survived")
        if name in PHASES[3:]:
            require(record["postrestore_exact_match"] is True and type(record["postrestore_rows"]) is int
                    and record["postrestore_rows"]>0, "new_history_missing")
            if restored_record is not None:
                require(record["postrestore_rows"]==restored_record["postrestore_rows"]
                        and record["postrestore_sha256"]==restored_record["postrestore_sha256"], "new_history_restart_changed")
            restored_record=record
    return {"schema":1,"outcome":"passed","tested_disabled_entry_saved_storage_restore":True,
            "tested_default_conditions_disabled_saved_storage_restore":True, "temporary_global_offline_conditions":False,
            "default_conditions_disabled_synthetic_restore_qualified":True, "default_supervisor_conditions_used":True,
            "manual_newest_guard_repair_required":True, "unsupported_conditions_override_used":False, "ordinary_default_supervisor_restore_qualified":False,
            "ordinary_enabled_restore_safety_accepted":False,"automatic_guard_antirollback":False,
            "provider_authentication_after_restore_tested":False,"full_encrypted_cloud_backup_tested":False,"stable_release_approval":False}

if __name__=="__main__":
    root=Path(sys.argv[1])
    value=accept(json.loads((root/"host.json").read_bytes()), {name:json.loads((root/(name+".json")).read_bytes()) for name in PHASES})
    print(json.dumps(value,sort_keys=True))
