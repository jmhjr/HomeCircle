"""Independent ordinary-restore evidence consumer; standard library, no fixture imports."""
from __future__ import annotations
import argparse
import ast
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

HERE = Path(__file__).resolve().parent
SOURCE = "012a7e88d13970b2683b27d0824dac246c858179"
ZIP_SHA = "98a754ff2025761c2eb63d6422c9b17b76e2bdef2965c96fe353ab6c2c21fb20"
SOURCE_INVENTORY_SHA = "915f96349ff66e272843bab0c4a57c4698da352fea8a3de372588549ad590652"
HEAD = "4957b3f44e84837e01af731286c0728a4127aea3"
RUN = 39721983991
INPUTS_SHA = "9be711b6da7fa3c61326865da4d7cd997f6d429956fa538d49ad8b7063a1dd6d"
WORKFLOW = ".github/workflows/native-ordinary-rollback-restore.yml"
WORKFLOW_SHA = "277104fa67c7ff6e321cb0e7de5182dc13a89c9be4822d1de691e963694926e7"
FIXTURE_NAME = "native-ordinary-rollback-restore"
ARTIFACT = "ordinary-rollback-restore-receipts"
PHASES = ("baseline_enabled", "mutated_enabled", "automatic_restored_enabled", "restart_enabled")
RECEIPTS = frozenset({"host.json", *(name + ".json" for name in PHASES)})
META_KEYS = frozenset({"schema", "run_id", "run_attempt", "head_sha", "branch", "event",
    "workflow_path", "workflow_sha256", "artifact_id", "artifact_name", "artifact_zip_sha256",
    "github_digest_verified", "status", "conclusion"})

class EvidenceRefused(ValueError):
    """A fixed label only; never retain untrusted values or exception text."""


def need(ok, label):
    if not ok:
        raise EvidenceRefused(label)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def exact(value, keys, label):
    need(type(value) is dict and set(value) == set(keys), label)


def integer(value, lower, upper, label):
    need(type(value) is int and lower <= value <= upper, label)


def digest(value, label):
    need(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None, label)


def same(value, expected, label):
    # JSON encodes a float or boolean differently from an integer. Require both
    # the exact types and values recursively rather than Python's loose equality.
    if type(value) is not type(expected):
        raise EvidenceRefused(label)
    if type(expected) is dict:
        exact(value, expected, label)
        for key in expected:
            same(value[key], expected[key], label)
    elif type(expected) is list:
        need(len(value) == len(expected), label)
        for left, right in zip(value, expected):
            same(left, right, label)
    else:
        need(value == expected, label)


def strict_json(raw):
    need(type(raw) is bytes and 0 < len(raw) <= 1024**2, 'json_size_refused')
    def unique(pairs):
        value = {}
        for key, item in pairs:
            need(key not in value, 'duplicate_json_key_refused')
            value[key] = item
        return value
    def constant(_):
        raise EvidenceRefused('nonfinite_json_refused')
    try:
        value = json.loads(raw, object_pairs_hook=unique, parse_constant=constant)
    except EvidenceRefused:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise EvidenceRefused('json_encoding_refused') from None
    pending, count = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        need(count <= 20000 and depth <= 20, 'json_structure_bound_refused')
        if type(item) is dict:
            need(all(type(key) is str and len(key) <= 512 for key in item), 'json_key_bound_refused')
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            need(len(item) <= 4096, 'json_string_bound_refused')
        elif type(item) is float:
            need(math.isfinite(item), 'nonfinite_json_refused')
        else:
            need(item is None or type(item) in {bool, int}, 'json_type_refused')
    return value


def read_regular(path, maximum):
    path = Path(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(descriptor)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and 0 < before.st_size <= maximum,
             'local_regular_file_bound_refused')
        with os.fdopen(descriptor, 'rb') as stream:
            descriptor = None
            raw = stream.read(maximum + 1)
            after = os.fstat(stream.fileno())
        need((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
             (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
             and len(raw) == before.st_size, 'local_file_changed_refused')
        return raw
    finally:
        if descriptor is not None:
            os.close(descriptor)


def literal(raw, name):
    """Read a frozen literal, never import or execute packet Python."""
    assignments = {}
    for node in ast.parse(raw).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments.setdefault(target.id, []).append(node.value)
    def convert(node, trail):
        need(len(trail) <= 12, 'frozen_literal_reference_bound_refused')
        if isinstance(node, ast.Name):
            return resolve(node.id, trail)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id == 'frozenset' and len(node.args) == 1 and not node.keywords:
            return frozenset(convert(node.args[0], trail))
        if isinstance(node, ast.Dict):
            return {convert(key, trail): convert(value, trail) for key, value in zip(node.keys, node.values)}
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            constructor = {ast.Tuple: tuple, ast.List: list, ast.Set: set}[type(node)]
            return constructor(convert(child, trail) for child in node.elts)
        return ast.literal_eval(node)
    def resolve(key, trail):
        need(key not in trail and key in assignments, 'frozen_literal_reference_refused')
        values = [convert(node, (*trail, key)) for node in assignments[key]]
        need(bool(values) and all(type(value) is type(values[0]) and value == values[0] for value in values),
             'frozen_literal_refused')
        return values[0]
    return resolve(name, ())


class Bindings:
    def __init__(self, fixture, workflow=None):
        self.fixture = Path(fixture).resolve()
        need(self.fixture.is_dir() and not Path(fixture).is_symlink(), 'fixture_directory_refused')
        raw = read_regular(HERE / 'INPUTS.json', 128 * 1024)
        need(sha(raw) == INPUTS_SHA, 'independent_inputs_digest_refused')
        inputs = strict_json(raw)
        exact(inputs, {'schema', 'source_commit', 'fixture_name', 'files'}, 'independent_input_shape_refused')
        same(inputs['schema'], 1, 'independent_input_schema_refused')
        same(inputs['source_commit'], SOURCE, 'independent_input_source_refused')
        same(inputs['fixture_name'], FIXTURE_NAME, 'independent_fixture_name_refused')
        need(type(inputs['files']) is dict and len(inputs['files']) == 27, 'frozen_input_count_refused')
        self.raw = {}
        self.workflow = read_regular(workflow or self.fixture.parent / 'ordinary-workflow.yml', 128 * 1024)
        need(sha(self.workflow) == WORKFLOW_SHA, 'frozen_workflow_digest_refused')
        for name, entry in inputs['files'].items():
            exact(entry, {'bytes', 'sha256'}, 'frozen_input_record_refused')
            integer(entry['bytes'], 1, 64 * 1024**2, 'frozen_input_size_refused')
            digest(entry['sha256'], 'frozen_input_sha_refused')
            path = PurePosixPath(name)
            need(name == path.as_posix() and not path.is_absolute() and '..' not in path.parts
                 and '\\' not in name, 'frozen_input_path_refused')
            data = self.workflow if name == WORKFLOW else read_regular(self.fixture / name, 64 * 1024**2)
            need(len(data) == entry['bytes'] and sha(data) == entry['sha256'], 'frozen_input_bytes_refused')
            if name != WORKFLOW:
                self.raw[name] = data
        nodes = list(self.fixture.rglob('*'))
        need(not any(node.is_symlink() for node in nodes), 'fixture_symlink_refused')
        local = {node.relative_to(self.fixture).as_posix() for node in nodes if node.is_file()
                 and '__pycache__' not in node.parts and node.name != '.DS_Store'}
        need(local == set(self.raw), 'fixture_members_refused')
        maps = re.findall(r'^\s*expected = (\{[^\n]+\})$', self.workflow.decode(), re.MULTILINE)
        need(len(maps) == 1, 'workflow_map_refused')
        same(ast.literal_eval(maps[0]), {name: sha(data) for name, data in self.raw.items()},
             'workflow_input_map_refused')
        binding = strict_json(self.raw['candidate_binding.json'])
        same(binding, {'schema': 1, 'prepared': True, 'source_commit': SOURCE,
                       'candidate_sha256': ZIP_SHA, 'candidate_files': 113}, 'candidate_binding_refused')
        self.inventory = self.product()
        self.payload_sha = sha(canonical(self.inventory))
        self.helper = {name.removeprefix('guest_helper/'): sha(data) for name, data in self.raw.items()
                       if name.startswith('guest_helper/')}
        self.base = self.raw['legacy_controller.py']

    def product(self):
        raw = self.raw['payload/homecircle.zip']
        need(sha(raw) == ZIP_SHA, 'candidate_zip_refused')
        expected = strict_json(self.raw['payload/inventory.json'])
        exact(expected, {'version', 'archive_sha256', 'files'}, 'product_inventory_shape_refused')
        same(expected['version'], '0.1.0-beta.20', 'candidate_version_refused')
        same(expected['archive_sha256'], ZIP_SHA, 'candidate_archive_inventory_refused')
        inventory = {}
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            need(len(members) == len({member.filename for member in members}) == 113,
                 'candidate_members_refused')
            total = 0
            for member in members:
                path = PurePosixPath(member.filename)
                need(member.filename == path.as_posix() and not path.is_absolute() and '..' not in path.parts
                     and '\\' not in member.filename and not member.is_dir()
                     and not stat.S_ISLNK(member.external_attr >> 16) and not member.flag_bits & 1
                     and 0 <= member.file_size <= 32 * 1024**2, 'candidate_member_refused')
                total += member.file_size
                need(total <= 128 * 1024**2, 'candidate_expansion_refused')
                data = archive.read(member)
                inventory[member.filename] = {'bytes': len(data), 'sha256': sha(data)}
            manifest = strict_json(archive.read('manifest.json'))
        same(inventory, expected['files'], 'candidate_exact_inventory_refused')
        need('homecircle_safe_restore_qa' not in manifest['dependencies'], 'adapted_product_manifest_refused')
        source_raw = read_regular(HERE / 'SOURCE-INVENTORY.json', 256 * 1024)
        need(sha(source_raw) == SOURCE_INVENTORY_SHA, 'source_inventory_digest_refused')
        source = strict_json(source_raw)
        need(type(source) is dict and len(source) == 371, 'source_inventory_count_refused')
        generated = {
            'frontend/homecircle-card.js': {'bytes': 276650, 'sha256': '77f429fb1908acc21cde2c89614f05f12c60a09bb37fa6ca78a1830ec07c6f91'},
            'frontend/LEAFLET-LICENSE.txt': {'bytes': 1395, 'sha256': '53e8dc25862014e4324741ca18fbe3611e11d42ef69f59f86ea8c5389647d4cb'},
        }
        for name, entry in inventory.items():
            wanted = generated.get(name)
            if wanted is None:
                wanted = source.get('LICENSE' if name == 'LICENSE' else 'custom_components/homecircle/' + name)
            need(wanted is not None, 'candidate_source_member_missing')
            same(entry, wanted, 'candidate_source_bytes_refused')
        return inventory

    def provenance(self):
        return {'candidate_source_commit': SOURCE, 'candidate_zip_sha256': ZIP_SHA, 'candidate_files': 113,
            'candidate_payload_sha256': self.payload_sha, 'controller_branch_commit': HEAD,
            'controller_sha256': sha(self.raw['controller.py']), 'haos_version': '18.3',
            'haos_xz_sha256': literal(self.base, 'HAOS_XZ_SHA'), 'release_published': False,
            'helper_files_sha256': self.helper, 'storage_transfer_sha256': sha(self.raw['storage_transfer.py']),
            'storage_context_sha256': sha(self.raw['storage_context.py']),
            'reset_sha256': sha(self.raw['reset_fresh_config.py']), 'qa_manifest_adaptation': False,
            'unchanged_product_members': 113, 'prepared_dependency_preload': False,
            'environmental_parent_fence': True}


def metadata_check(value, artifact_sha):
    need(re.fullmatch('[0-9a-f]{40}', HEAD) is not None and type(RUN) is int and RUN > 0,
         'root_run_anchor_not_frozen')
    exact(value, META_KEYS, 'root_metadata_shape_refused')
    expected = dict(schema=1, run_id=RUN, run_attempt=1, head_sha=HEAD, branch='codex/native-amd64-validation',
        event='push', workflow_path=WORKFLOW, workflow_sha256=WORKFLOW_SHA, artifact_name=ARTIFACT,
        github_digest_verified=True, status='completed', conclusion='success')
    for name, wanted in expected.items():
        same(value[name], wanted, 'root_metadata_binding_refused')
    integer(value['artifact_id'], 1, 2**63 - 1, 'artifact_identity_refused')
    digest(value['artifact_zip_sha256'], 'artifact_digest_refused')
    same(value['artifact_zip_sha256'], artifact_sha, 'downloaded_artifact_digest_refused')


def artifact_receipts(raw):
    need(0 < len(raw) <= 2 * 1024**2, 'artifact_size_refused')
    values, fingerprints = {}, {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = archive.infolist()
        need(len(members) == 5 and {member.filename for member in members} == RECEIPTS,
             'five_exact_artifact_members_required')
        for member in members:
            need(not member.is_dir() and not stat.S_ISLNK(member.external_attr >> 16)
                 and not member.flag_bits & 1 and 0 < member.file_size <= 1024**2,
                 'artifact_member_type_refused')
            data = archive.read(member)
            values[member.filename] = strict_json(data)
            need(type(values[member.filename]) is dict, 'artifact_object_required')
            fingerprints[member.filename] = {'bytes': len(data), 'sha256': sha(data)}
    return values, fingerprints


def job(value, name):
    exact(value, {'name', 'done', 'error_count', 'nodes'}, 'job_shape_refused')
    same(value['name'], name, 'job_identity_refused')
    same(value['done'], True, 'job_incomplete')
    same(value['error_count'], 0, 'job_errors_refused')
    integer(value['nodes'], 1, 256, 'job_node_count_refused')


def dependencies(value, bindings):
    fixed = {'schema': 1, 'core': '2026.10.2', 'python': '3.14.6',
        'constraints_sha256': literal(bindings.base, 'CONSTRAINTS_SHA'), 'constraints_match': True,
        'docker_environment': True, 'ordinary_pip_target_unset': True, 'config_deps_empty': True,
        'closure_count': 24, 'closure_graph_checked': True, 'skip_pip': False,
        'provider_or_native_imports_requested_by_probe': False}
    exact(value, {*fixed, 'direct', 'closure'}, 'dependency_shape_refused')
    for key, expected in fixed.items():
        same(value[key], expected, 'normal_dependency_boundary_refused')
    closure = literal(bindings.base, 'CLOSURE')
    exact(value['closure'], closure, 'dependency_closure_names_refused')
    for item in value['closure'].values():
        exact(item, {'available', 'version', 'metadata_system_origin', 'constraints_satisfied', 'python_satisfied'},
              'dependency_closure_metadata_shape_refused')
        for key in ('available', 'metadata_system_origin', 'constraints_satisfied', 'python_satisfied'):
            same(item[key], True, 'dependency_closure_origin_refused')
        need(type(item['version']) is str and re.fullmatch('[0-9]{1,8}(?:[.][0-9]{1,8}){1,3}', item['version']),
             'dependency_version_refused')
    direct = literal(bindings.base, 'DIRECT')
    exact(value['direct'], direct, 'direct_dependency_names_refused')
    for name, version in direct.items():
        item = value['direct'][name]
        exact(item, {'available', 'version', 'satisfies_requirement', 'loaded_module_present',
                     'module_system_origin', 'origin_probe'}, 'direct_dependency_shape_refused')
        for key in ('available', 'satisfies_requirement', 'module_system_origin'):
            same(item[key], True, 'direct_dependency_origin_refused')
        same(item['version'], version, 'direct_dependency_version_refused')
        same(value['closure'][name]['version'], version, 'direct_closure_version_refused')
        need(item['origin_probe'] in {'loaded_module', 'import_spec'}, 'direct_origin_probe_refused')
        same(item['loaded_module_present'], item['origin_probe'] == 'loaded_module', 'direct_loaded_type_refused')


def boundary(value, restored):
    flags = {'installed_before_product_import', 'patches_intact', 'deny_all_external_aiohttp',
        'python_socket_audit_installed', 'product_manifest_unchanged', 'normal_requirement_subprocesses_unmodified'}
    counters = {'life360_sessions_created', 'life360_requests_denied', 'apple_legacy_requests_denied',
        'apple_bounded_requests_denied', 'apple_report_requests_denied', 'other_external_requests_denied',
        'recovery_before_dispatch_calls', 'recovery_command_calls', 'recovery_transport_attempts_denied',
        'supervisor_requests_allowed', 'qa_static_requests_allowed', 'socket_external_attempts_denied',
        'ordinary_uv_installs_observed'}
    exact(value, {'schema', 'boundary_revision', 'loaded_target_kinds', *flags, *counters}, 'boundary_shape_refused')
    same(value['schema'], 2, 'boundary_schema_refused')
    same(value['boundary_revision'], 2, 'boundary_revision_refused')
    same(value['loaded_target_kinds'], sorted(('life360', 'legacy', 'bounded', 'report', 'guard', 'escrow')),
         'boundary_hook_set_refused')
    for flag in flags:
        same(value[flag], True, 'boundary_flag_refused')
    for counter in counters:
        integer(value[counter], 0, 1000000, 'boundary_count_type_refused')
    need(value['life360_sessions_created'] >= 1 and value['life360_requests_denied'] >= 1
         and sum(value[key] for key in ('apple_legacy_requests_denied', 'apple_bounded_requests_denied',
                                       'apple_report_requests_denied')) >= 1, 'nonvacuous_provider_calls_required')
    for name in ('recovery_before_dispatch_calls', 'recovery_command_calls', 'recovery_transport_attempts_denied'):
        same(value[name], 0, 'recovery_dispatch_not_permitted')
    if restored is not None:
        need(value['ordinary_uv_installs_observed'] >= 1, 'ordinary_requirement_installer_not_observed')


def recorder(value, phase):
    flags = {'ready', 'prebackup_exact_match', 'integrity_ok', 'backup_platform_registered',
             'commit_proven', 'no_backup_failure_issue'}
    exact(value, {*flags, 'prebackup_rows', 'prebackup_sha256', 'postbackup_marker_rows',
        'postbackup_marker_absent', 'postrestore_rows', 'postrestore_sha256', 'postrestore_exact_match'},
        'recorder_shape_refused')
    for key in flags:
        same(value[key], True, 'recorder_required_flag_refused')
    integer(value['prebackup_rows'], 5, 128, 'recorder_baseline_count_refused')
    digest(value['prebackup_sha256'], 'recorder_baseline_hash_refused')
    mutated = phase == 'mutated_enabled'
    integer(value['postbackup_marker_rows'], 1 if mutated else 0, 128 if mutated else 0, 'recorder_mutation_refused')
    same(value['postbackup_marker_absent'], not mutated, 'recorder_marker_presence_refused')
    if phase in PHASES[2:]:
        integer(value['postrestore_rows'], 5, 128, 'recorder_restored_count_refused')
        digest(value['postrestore_sha256'], 'recorder_restored_hash_refused')
        same(value['postrestore_exact_match'], True, 'recorder_restored_match_refused')
    else:
        for key in ('postrestore_rows', 'postrestore_sha256', 'postrestore_exact_match'):
            same(value[key], None, 'premature_postrestore_history_refused')


PHASE_FLAGS = {'entry_loaded': True, 'entry_disabled': False, 'candidate_imported': True,
    'ha_config_entry_saved': True, 'closed_boot_grant_verified': True, 'storage_raw_matches_expected': True,
    'explicit_registry_joins_checked': True, 'product_manifest_unchanged': True,
    'actual_findmy_session_restored': True, 'runtime_selection_checked': True,
    'synthetic_photo_preserved': True, 'static_served_bundle_matches': True}
PHASE_KEYS = {'schema', 'phase', 'outcome', 'generation', 'process', 'selected_registry_joins', 'guard_counter',
    'recorder', 'normal_dependencies', 'startup_boundary', 'recovery_guard', 'unchanged_product_members', *PHASE_FLAGS}


def phases_check(phases, bindings):
    exact(phases, PHASES, 'four_phases_required')
    ticks = 0
    first = None
    for name in PHASES:
        value = phases[name]
        exact(value, PHASE_KEYS, 'phase_shape_refused')
        for key, expected in {'schema': 2, 'phase': name, 'outcome': 'passed',
            'generation': 'after_restore' if name == 'restart_enabled' else 'before_restore',
            'selected_registry_joins': 4, 'guard_counter': 3 if name == 'mutated_enabled' else 2,
            'unchanged_product_members': 113, **PHASE_FLAGS}.items():
            same(value[key], expected, 'phase_fixed_value_refused')
        exact(value['process'], {'pid', 'start_ticks'}, 'phase_process_shape_refused')
        integer(value['process']['pid'], 1, 2**31 - 1, 'phase_pid_refused')
        integer(value['process']['start_ticks'], ticks + 1, 2**63 - 1, 'phase_distinct_process_refused')
        ticks = value['process']['start_ticks']
        restored = name in PHASES[2:]
        same(value['recovery_guard'], {'identity_matches_saved_sdk_account': True,
            'counter': value['guard_counter'], 'blocked': restored or value['guard_counter'] >= 3,
            'review_required': restored, 'witness_absent': restored, 'attempt_refused_before_body': restored,
            'manual_guard_imports': 0, 'owner_acknowledgments_after_restore': 0}, 'guard_restore_block_refused')
        dependencies(value['normal_dependencies'], bindings)
        boundary(value['startup_boundary'], restored if name in (PHASES[0], PHASES[2]) else None)
        recorder(value['recorder'], name)
        if first is None:
            first = value['recorder']
        else:
            for field in ('prebackup_rows', 'prebackup_sha256'):
                same(value['recorder'][field], first[field], 'recorder_baseline_continuity_refused')
    for field in ('postrestore_rows', 'postrestore_sha256'):
        same(phases[PHASES[2]]['recorder'][field], phases[PHASES[3]]['recorder'][field],
             'recorder_postrestore_continuity_refused')


HOST_TRUE = {'actual_kvm_confirmed', 'ordinary_unmodified_product_partial_restore_qualified',
    'normal_managed_dependencies', 'product_manifest_unchanged', 'automatic_guard_rollback_block',
    'environmental_transport_instrumentation', 'qemu_stopped', 'private_workspace_removed'}
HOST_FALSE = {'prepared_dependency_preload_used', 'real_provider_accounts_configured', 'owner_credentials_used',
    'production_configuration_used', 'provider_authentication_after_restore_tested', 'provider_session_renewal_tested',
    'full_system_restore_tested', 'full_encrypted_cloud_backup_tested', 'stable_release_approval',
    'candidate_hacs_download_tested', 'cleanup_failed'}
HOST_ZERO = {'manual_guard_imports', 'guard_exports', 'owner_acknowledgments_after_restore'}
HOST_KEYS = {*HOST_TRUE, *HOST_FALSE, *HOST_ZERO, 'schema', 'outcome', 'phase_names', 'phases',
    'failure_or_final_stage', 'failure_type', 'failure_code', 'provenance', 'actual_core', 'actual_supervisor',
    'current_core_image', 'fresh_owned_config', 'core_actions', 'backup_requests', 'backup', 'restore',
    'storage_contexts', 'storage_results', 'normal_initial_requirement_window', 'default_restore_conditions',
    'network_boundary', 'network_transitions', 'host_elapsed_seconds', 'guest_failures'}


def default_conditions(value, bindings):
    flags = literal(bindings.base, 'DEFAULT_RECEIPT_BOOL_KEYS')
    fixed = {'schema': 1, 'mode': 'default_conditions_instrumented_enabled_saved_storage',
        'jobs_option_mutation_requests': 0, 'global_persisted_override': False,
        'unsupported_conditions_override': False, 'network_open_requests': 1, 'network_close_requests': 1,
        'maximum_cleanup_seconds': 90, 'maximum_network_readiness_seconds': 90}
    exact(value, {*flags, *fixed, 'network_info_requests'}, 'default_conditions_shape_refused')
    for key, expected in fixed.items():
        same(value[key], expected, 'default_conditions_fixed_value_refused')
    for key in flags:
        same(value[key], key not in {'foreign_options_refused', 'cleanup_failed'}, 'default_conditions_flag_refused')
    integer(value['network_info_requests'], 1, 18, 'default_readiness_request_bound_refused')


def image_check(value, bindings):
    def constant(name):
        return literal(bindings.base, name)
    same(value, {'reference': constant('IMAGE_REFERENCE'),
        'identity_model': 'containerd_index_with_verified_stored_oci_chain',
        'observed_container_image_id': constant('IMAGE_INDEX_DIGEST'),
        'observed_image_inspect_id': constant('IMAGE_INDEX_DIGEST'),
        'official_index_digest': constant('IMAGE_INDEX_DIGEST'),
        'selected_manifest_digest': constant('IMAGE_MANIFEST_DIGEST'),
        'verified_oci_config_digest': constant('IMAGE_CONFIG_ID'), 'stored_objects_hashed': 3,
        'object_bytes': {name: item[1] for name, item in constant('IMAGE_OBJECTS').items()},
        'containerd_address': constant('CONTAINERD_ADDRESS'), 'containerd_namespace': constant('CONTAINERD_NAMESPACE'),
        'platform': {'os': 'linux', 'architecture': 'amd64'}, 'rootfs_layers': 22,
        'image_rootfs_matches_verified_config': True, 'repository_digest_checked': True}, 'official_image_binding_refused')


def storage_check(host, bindings):
    actions = ('seed', 'mutate', 'validate_restored', 'validate_restart')
    same(host['storage_contexts'], [{'schema': 1, 'action': name, 'outcome': 'passed',
        'image': literal(bindings.raw['storage_context.py'], 'IMAGE'),
        'managed_core_same_stopped_process': True, 'local_image_verified': True,
        'owned_identity_security_mount_checked': True, 'offline_network_none': True,
        'bound_storage_transfer_stdin': True, 'owned_container_removed': True, 'maximum_total_seconds': 60}
        for name in actions], 'storage_context_ownership_refused')
    checks = literal(bindings.base, 'STORAGE_CHECKS')
    common = literal(bindings.base, 'COMMON_STORAGE_CHECKS')
    exact(host['storage_results'], actions, 'storage_actions_refused')
    for name in actions:
        expected = {**dict.fromkeys(common, True), **checks[name]}
        expected['guard_counter'] = 3 if name == 'mutate' else 2
        same(host['storage_results'][name], {'schema': 1, 'action': name, 'outcome': 'passed',
            'entry_disabled': False, 'managed_candidate_imported': False, 'synthetic_only': True,
            'source_files_verified': True, 'storage_checks': expected,
            'private_proof_written': name in {'seed', 'mutate'}}, 'storage_result_refused')


def host_check(host, bindings):
    exact(host, HOST_KEYS, 'host_shape_refused')
    for key, expected in {'schema': 2, 'outcome': 'passed', 'phase_names': list(PHASES), 'phases': 4,
        'failure_or_final_stage': 'ordinary_unmodified_product_restore_complete', 'failure_type': None,
        'failure_code': None, 'guest_failures': [], 'actual_core': '2026.10.2', 'actual_supervisor': '2026.10.3',
        **dict.fromkeys(HOST_TRUE, True), **dict.fromkeys(HOST_FALSE, False), **dict.fromkeys(HOST_ZERO, 0)}.items():
        same(host[key], expected, 'host_fixed_value_refused')
    same(host['provenance'], bindings.provenance(), 'independent_candidate_and_tools_binding_refused')
    image_check(host['current_core_image'], bindings)
    reset = host['fresh_owned_config']
    exact(reset, {'files', 'bytes', 'children', 'owner_accounts_found', 'candidate_previously_present',
                  'fresh_config_reset', 'mount_directory_preserved'}, 'fresh_config_shape_refused')
    for name, upper in (('files', 8192), ('bytes', 64 * 1024**2), ('children', 128)):
        integer(reset[name], 0, upper, 'fresh_config_count_refused')
    for name, expected in {'owner_accounts_found': False, 'candidate_previously_present': False,
        'fresh_config_reset': True, 'mount_directory_preserved': True}.items():
        same(reset[name], expected, 'fresh_config_proof_refused')
    same(host['normal_initial_requirement_window'], {'opened': True, 'closed': True,
        'normal_ha_requirement_install': True, 'maximum_seconds': 750}, 'ordinary_initial_window_refused')
    default_conditions(host['default_restore_conditions'], bindings)
    same(host['network_transitions'], ['closed_before_synthetic_seed', 'opened_for_ordinary_requirements',
        'closed_after_ordinary_requirements', 'opened_for_default_restore', 'closed_after_default_restore'],
        'two_bounded_network_windows_refused')
    network = host['network_boundary']
    exact(network, {'link_closed', 'before_probe_connected', 'closed_probe_connected',
                    'closed_probe_observations', 'guest_agent_remained_available'}, 'network_boundary_shape_refused')
    for key, expected in {'link_closed': True, 'before_probe_connected': True, 'closed_probe_connected': False,
                           'guest_agent_remained_available': True}.items():
        same(network[key], expected, 'network_boundary_flag_refused')
    integer(network['closed_probe_observations'], 5, 10000, 'network_closed_observations_refused')
    expected_actions = ['stop', 'start', 'stop', 'start', 'stop', 'start', 'stop', 'stop', 'start', 'stop']
    need(type(host['core_actions']) is list and len(host['core_actions']) == len(expected_actions),
         'core_actions_count_refused')
    for action, expected in zip(host['core_actions'], expected_actions):
        exact(action, {'action', 'result', 'supervisor_running', 'relevant_core_jobs_idle',
            'running_before', 'running_after', 'container_state_before', 'container_state_after'}, 'core_action_shape_refused')
        for key, wanted in {'action': expected, 'result': 'ok', 'supervisor_running': True,
            'relevant_core_jobs_idle': True, 'running_after': expected == 'start',
            'container_state_after': 'running' if expected == 'start' else 'stopped'}.items():
            same(action[key], wanted, 'core_action_fixed_value_refused')
        before = action['container_state_before']
        need(before in ({'stopped', 'not_created'} if expected == 'start' else {'running'}),
             'core_action_before_refused')
        same(action['running_before'], {'stopped': False, 'not_created': None, 'running': True}[before],
             'core_action_running_before_refused')
    need(type(host['backup_requests']) is list and len(host['backup_requests']) == 2, 'backup_request_count_refused')
    for request, action in zip(host['backup_requests'], ('create', 'restore')):
        same(request, {'action': action, 'exit_code': 0, 'signal': None, 'result': 'ok', 'stdout_json': True,
            'output_truncated': False, 'api_error': {'type': 'unclassified', 'categories': []},
            'stderr_error': {'type': 'unclassified', 'categories': []}, 'exact_job_id_returned': True},
            'backup_request_binding_refused')
    backup = host['backup']
    exact(backup, {'result', 'job', 'type', 'homeassistant_version', 'database_included',
                   'protected', 'compressed', 'archive'}, 'backup_shape_refused')
    for key, expected in {'result': 'ok', 'type': 'partial', 'homeassistant_version': '2026.10.2',
                           'database_included': True, 'protected': False, 'compressed': False}.items():
        same(backup[key], expected, 'backup_scope_refused')
    job(backup['job'], 'backup_manager_partial_backup')
    archive = backup['archive']
    archive_flags = {'saved_photo_bytes_included', 'qa_startup_boundary_archive_verified',
        'no_prepared_dependency_bytes', 'product_manifest_unchanged', 'cache_witness_excluded',
        'database_included', 'candidate_match', 'enabled_entry', 'saved_pair_included', 'saved_config_included',
        'saved_selection_included', 'saved_registry_joins_included'}
    exact(archive, {*archive_flags, 'archive_bytes', 'guard_sha256'}, 'backup_archive_shape_refused')
    for key in archive_flags:
        same(archive[key], True, 'backup_archive_proof_refused')
    integer(archive['archive_bytes'], 1, 128 * 1024**2, 'backup_archive_size_refused')
    digest(archive['guard_sha256'], 'backup_guard_fingerprint_refused')
    restoration = host['restore']
    exact(restoration, {'result', 'job', 'qa_startup_boundary_required'}, 'restore_shape_refused')
    same(restoration['result'], 'ok', 'restore_result_refused')
    same(restoration['qa_startup_boundary_required'], True, 'restore_boundary_required')
    job(restoration['job'], 'backup_manager_partial_restore')
    storage_check(host, bindings)
    elapsed = host['host_elapsed_seconds']
    need(type(elapsed) in {int, float} and math.isfinite(elapsed) and 0 < elapsed <= 5800,
         'host_elapsed_bound_refused')


def validate_receipts(values, bindings):
    exact(values, RECEIPTS, 'five_fixed_receipts_required')
    host_check(values['host.json'], bindings)
    phases_check({name: values[name + '.json'] for name in PHASES}, bindings)
    return {'schema': 1, 'outcome': 'passed', 'scope': 'ordinary_unmodified_product_synthetic_partial_restore',
        'automatic_restore_guard_block_verified': True, 'guard_counters': [2, 3, 2, 2],
        'manual_guard_repair_used': False, 'owner_acknowledgments_after_restore': 0,
        'all_113_product_bytes_unchanged': True, 'normal_managed_requirements_verified': True,
        'environmental_transport_instrumentation': True, 'recorder_continuity_verified': True,
        'real_provider_authentication_qualified': False, 'full_encrypted_cloud_backup_qualified': False,
        'full_VM_snapshot_rollback_qualified': False, 'stable_release_approval': False}


def review(artifact_zip, metadata, fixture_dir, workflow=None):
    bindings = Bindings(fixture_dir, workflow)
    raw = read_regular(artifact_zip, 2 * 1024**2)
    metadata = strict_json(read_regular(metadata, 64 * 1024))
    metadata_check(metadata, sha(raw))
    values, fingerprints = artifact_receipts(raw)
    result = validate_receipts(values, bindings)
    return {'schema': 1, 'outcome': 'passed', 'run_id': RUN, 'run_attempt': 1, 'head_sha': HEAD,
        'workflow_sha256': WORKFLOW_SHA, 'frozen_inputs_sha256': INPUTS_SHA, 'frozen_input_files_verified': 27,
        'artifact_id': metadata['artifact_id'], 'artifact_name': ARTIFACT, 'artifact_zip_sha256': sha(raw),
        'candidate_source_commit': SOURCE, 'candidate_zip_sha256': ZIP_SHA, 'product_files': 113,
        'literal_source_members': 111, 'previously_qualified_generated_frontend_members': 2,
        'source_inventory_sha256': SOURCE_INVENTORY_SHA, 'source_inventory_files': 371,
        'strict_nested_public_schema_checked': True, 'root_metadata_separate_from_artifact': True,
        'fixture_code_executed_or_imported': False, 'native_trial_repeated_by_collector': False,
        'collector_sha256': sha(read_regular(Path(__file__), 1024**2)), 'receipts': fingerprints,
        'scoped_acceptance': result}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-dir', type=Path, required=True)
    parser.add_argument('--artifact-zip', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--workflow', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        need(not args.output.exists() and not args.output.is_symlink(), 'fresh_output_required')
        need(not args.output.resolve().is_relative_to(args.fixture_dir.resolve()), 'fixture_output_refused')
        result = review(args.artifact_zip, args.metadata, args.fixture_dir, args.workflow)
        code = 0
    except EvidenceRefused as error:
        result = {'schema': 1, 'outcome': 'refused', 'failure_code': str(error)}
        code = 1
    except Exception:
        result = {'schema': 1, 'outcome': 'refused', 'failure_code': 'evidence_validation_refused'}
        code = 1
    try:
        with args.output.open('xb') as stream:
            os.chmod(args.output, 0o600)
            stream.write(json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode() + b'\n')
    except FileExistsError:
        print('{"schema":1,"outcome":"refused","failure_code":"fresh_output_required"}')
        return 1
    except OSError:
        print('{"schema":1,"outcome":"refused","failure_code":"output_write_refused"}')
        return 1
    print(json.dumps({'schema': 1, 'outcome': result['outcome'], 'failure_code': result.get('failure_code')}))
    return code


if __name__ == '__main__':
    raise SystemExit(main())

