"""Read-only replay of one frozen instrumented native trial; stdlib only.

Root-supplied metadata is separate from the artifact and must already have been
verified against GitHub. This program performs no GitHub, Git, provider or VM
operations. It never imports Home Assistant or the guest helper.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import types
import zipfile

HERE = Path(__file__).resolve().parent
SOURCE = '91ae59106a661143b770d7a3564d363c7c11a7dd'
HEAD = '9605b5fe280679c2b621973f862fdecadb4e8c53'
RUN = 39708377110
INPUTS_SHA = 'f2694cd158c8c291499d9936e6faa0c3ae72d19e1e4fbb2b21baf4766ea4fc44'
WORKFLOW = '.github/workflows/native-release1-enabled-saved-restore.yml'
WORKFLOW_SHA = '4c8d41c10ce0c3845ef4009e6e743f10d3b5d9beeb31ad4dcfdffca9a4216c1a'
ARTIFACT = 'release1-instrumented-enabled-saved-restore'
FIXTURE_NAME = 'native-release1-enabled-saved-restore'
PHASES = ('baseline_enabled', 'mutated_enabled', 'automatic_restored_enabled',
          'repaired_storage_enabled', 'restart_enabled')
RECEIPTS = frozenset({'host.json', *(name + '.json' for name in PHASES)})
META_KEYS = frozenset({'schema', 'run_id', 'run_attempt', 'head_sha', 'branch', 'event',
    'workflow_path', 'workflow_sha256', 'artifact_id', 'artifact_name', 'artifact_zip_sha256',
    'github_digest_verified', 'status', 'conclusion'})


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


class Bindings:
    """Root all executable and product expectations in the frozen input map."""
    def __init__(self, fixture_dir, workflow_file=None, inputs_file=None):
        self.fixture = Path(fixture_dir).resolve()
        need(self.fixture.is_dir() and not Path(fixture_dir).is_symlink(), 'fixture_root_refused')
        raw_inputs = read_regular(inputs_file or HERE / 'INPUTS.json', 128 * 1024)
        need(sha(raw_inputs) == INPUTS_SHA, 'frozen_inputs_hash_refused')
        self.inputs = strict_json(raw_inputs)
        exact(self.inputs, {'schema', 'base', 'source', 'files'}, 'frozen_inputs_schema_refused')
        same(self.inputs['schema'], 1, 'frozen_inputs_schema_refused')
        need(self.inputs['base'] == '18cdbf68819608180289bcfff9723e3cd5754fe9'
             and self.inputs['source'] == SOURCE, 'frozen_inputs_source_refused')
        files = self.inputs['files']
        need(type(files) is dict and len(files) == 28, 'frozen_input_count_refused')
        candidates = [self.fixture.parent / 'workflow.yml', self.fixture.parent / WORKFLOW]
        workflow_path = Path(workflow_file) if workflow_file else next((p for p in candidates if p.is_file()), candidates[0])
        self.workflow_bytes = read_regular(workflow_path, 128 * 1024)
        need(sha(self.workflow_bytes) == WORKFLOW_SHA, 'workflow_bytes_refused')
        self.raw = {}
        for name, item in files.items():
            exact(item, {'bytes', 'mode', 'sha256'}, 'frozen_input_member_schema_refused')
            integer(item['bytes'], 1, 64 * 1024**2, 'frozen_input_member_size_refused')
            need(item['mode'] in {'100644', '100755'}, 'frozen_input_mode_refused')
            digest(item['sha256'], 'frozen_input_digest_refused')
            if name == WORKFLOW:
                raw = self.workflow_bytes
            else:
                relative = PurePosixPath(name)
                need(not relative.is_absolute() and '..' not in relative.parts
                     and relative.parts[0] == FIXTURE_NAME, 'frozen_input_path_refused')
                short = relative.relative_to(FIXTURE_NAME).as_posix()
                raw = read_regular(self.fixture / short, 64 * 1024**2)
                self.raw[short] = raw
            need(len(raw) == item['bytes'] and sha(raw) == item['sha256'], 'frozen_input_bytes_refused')
        local = {p.relative_to(self.fixture).as_posix() for p in self.fixture.rglob('*')
                 if p.is_file() and '__pycache__' not in p.parts and p.name != '.DS_Store'}
        need(local == set(self.raw), 'frozen_fixture_members_refused')
        need(not any(p.is_symlink() for p in self.fixture.rglob('*')), 'frozen_fixture_symlink_refused')
        maps = re.findall(r'^\s*expected = (\{[^\n]+\})$', self.workflow_bytes.decode(), re.MULTILINE)
        need(len(maps) == 1, 'workflow_verifier_map_refused')
        try:
            workflow_map = ast.literal_eval(maps[0])
        except (SyntaxError, ValueError):
            raise EvidenceRefused('workflow_verifier_map_refused') from None
        same(workflow_map, {name: sha(raw) for name, raw in self.raw.items()}, 'workflow_frozen_map_binding_refused')
        self.inventory = self.product_inventory()
        self.payload_sha = sha(canonical(self.inventory))
        with zipfile.ZipFile(io.BytesIO(self.raw['payload/homecircle.zip'])) as archive:
            original = archive.read('manifest.json')
        manifest = strict_json(original)
        need('homecircle_safe_restore_qa' not in manifest['dependencies'], 'original_manifest_dependency_refused')
        manifest['dependencies'].append('homecircle_safe_restore_qa')
        self.original_manifest_sha = sha(original)
        self.manifest_sha = sha((json.dumps(manifest, indent=2) + '\n').encode())
        self.helper = {name.removeprefix('guest_helper/'): sha(raw) for name, raw in self.raw.items()
                       if name.startswith('guest_helper/')}

    def product_inventory(self):
        raw = self.raw['payload/homecircle.zip']
        need(sha(raw) == '004c9bc4a968ad395e18033837cb42f5bd1d8719a8d90fc778fd20be4ff08f97', 'product_zip_binding_refused')
        inventory = {}
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            need(len(members) == 113 and len({m.filename for m in members}) == 113, 'product_member_count_refused')
            for member in members:
                path = PurePosixPath(member.filename)
                need(not path.is_absolute() and '..' not in path.parts and not member.is_dir()
                     and not stat.S_ISLNK(member.external_attr >> 16), 'product_member_path_refused')
                body = archive.read(member)
                inventory[member.filename] = {'bytes': len(body), 'sha256': sha(body)}
        expected = strict_json(self.raw['payload/inventory.json'])
        exact(expected, {'version', 'files', 'archive_sha256'}, 'product_inventory_schema_refused')
        same(expected['version'], '0.1.0-beta.20', 'product_inventory_version_refused')
        same(expected['archive_sha256'], sha(raw), 'product_inventory_archive_refused')
        same(inventory, expected['files'], 'product_inventory_binding_refused')
        return inventory

    @contextmanager
    def modules(self):
        names = ('guard_context', 'storage_context', 'guard_transfer', 'enabled_protocol', 'controller', 'accept_saved_storage')
        previous = {name: sys.modules.get(name) for name in names}
        loaded = {}
        old_path = list(sys.path)
        try:
            sys.path.insert(0, str(self.fixture))
            for name in names:
                module = types.ModuleType(name)
                module.__file__ = str(self.fixture / (name + '.py'))
                sys.modules[name] = module
                exec(compile(self.raw[name + '.py'], module.__file__, 'exec'), module.__dict__)
                loaded[name] = module
            yield types.SimpleNamespace(**loaded)
        finally:
            sys.path[:] = old_path
            for name, module in previous.items():
                if module is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = module

    def provenance(self, controller):
        result = dict(candidate_source_commit=SOURCE,
            candidate_zip_sha256=sha(self.raw['payload/homecircle.zip']), candidate_files=113,
            candidate_payload_sha256=self.payload_sha, release_published=False, controller_branch_commit=HEAD,
            controller_sha256=sha(self.raw['controller.py']), haos_version='18.3', haos_xz_sha256=controller.HAOS_XZ_SHA,
            helper_files_sha256=self.helper, dependency_preparer_sha256=sha(self.raw['prepare_dependencies.py']),
            qa_manifest_only_adaptation=True, unchanged_runtime_members=112,
            original_manifest_sha256=self.original_manifest_sha, qa_manifest_sha256=self.manifest_sha)
        for field, name in (('guard_transfer_sha256', 'guard_transfer.py'), ('guard_context_sha256', 'guard_context.py'),
                            ('storage_transfer_sha256', 'storage_transfer.py'), ('storage_context_sha256', 'storage_context.py'),
                            ('reset_sha256', 'reset_fresh_config.py')):
            result[field] = sha(self.raw[name])
        return result


def metadata_check(value, artifact_sha):
    exact(value, META_KEYS, 'root_metadata_schema_refused')
    fixed = dict(schema=1, run_id=RUN, run_attempt=1, head_sha=HEAD, branch='codex/native-amd64-validation',
        event='push', workflow_path=WORKFLOW, workflow_sha256=WORKFLOW_SHA, artifact_name=ARTIFACT,
        github_digest_verified=True, status='completed', conclusion='success')
    for key, wanted in fixed.items():
        same(value[key], wanted, 'root_metadata_binding_refused')
    integer(value['artifact_id'], 1, 2**63 - 1, 'artifact_id_refused')
    digest(value['artifact_zip_sha256'], 'artifact_digest_refused')
    need(value['artifact_zip_sha256'] == artifact_sha, 'artifact_zip_digest_refused')


def artifact_receipts(raw):
    need(type(raw) is bytes and 0 < len(raw) <= 2 * 1024**2, 'artifact_zip_size_refused')
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
        members = archive.infolist()
        need(len(members) == 6 and {m.filename for m in members} == RECEIPTS, 'six_fixed_receipts_required')
        result, fingerprints = {}, {}
        for member in members:
            need(not member.is_dir() and not stat.S_ISLNK(member.external_attr >> 16)
                 and not member.flag_bits & 1 and 0 < member.file_size <= 1024**2, 'artifact_member_type_refused')
            body = archive.read(member)
            result[member.filename] = strict_json(body)
            need(type(result[member.filename]) is dict, 'artifact_receipt_object_refused')
            fingerprints[member.filename] = {'bytes': len(body), 'sha256': sha(body)}
        archive.close()
        return result, fingerprints
    except EvidenceRefused:
        raise
    except (ValueError, OSError, zipfile.BadZipFile, RuntimeError):
        raise EvidenceRefused('artifact_zip_encoding_refused') from None


def dependency_fixture(value, controller):
    keys = {'schema', 'outcome', 'core', 'python', 'constraints_sha256', 'site', 'normal_bootstrap_library',
            'virtual_env', 'requirements', 'closure', 'closure_count', 'inventory_sha256', 'inventory_files',
            'inventory_bytes', 'inventory_scope'}
    exact(value, keys, 'dependency_public_schema_refused')
    for key, wanted in dict(schema=1, outcome='passed', core=controller.CORE, python='3.14.6',
        constraints_sha256=controller.CONSTRAINTS_SHA, site=controller.DEPS_SITE, normal_bootstrap_library=True,
        virtual_env=False, requirements=controller.REQUIREMENTS, closure_count=24,
        inventory_scope='dependency_regular_files_excluding_generated_bytecode').items():
        same(value[key], wanted, 'dependency_fixture_binding_refused')
    digest(value['inventory_sha256'], 'dependency_inventory_digest_refused')
    integer(value['inventory_files'], 1, 8192, 'dependency_inventory_count_refused')
    integer(value['inventory_bytes'], 1, 96 * 1024**2, 'dependency_inventory_bytes_refused')
    closure = value['closure']
    need(type(closure) is dict and len(closure) == 24 and controller.PACKAGE_NAMES <= closure.keys(), 'dependency_closure_shape_refused')
    for name, version in closure.items():
        need(type(name) is str and re.fullmatch('[a-z0-9][a-z0-9.-]{0,79}', name) is not None
             and type(version) is str and re.fullmatch('[A-Za-z0-9_.+-]{1,64}', version) is not None, 'dependency_metadata_refused')
    for name, version in {'life360':'7.2.0', 'anisette':'1.2.4', 'unicorn':'2.1.4', 'srp':'1.0.22', 'beautifulsoup4':'4.13.3'}.items():
        need(closure[name] == version, 'direct_dependency_version_refused')
    need(re.fullmatch(r'(?:6\.(?:3[2-9]|[4-9][0-9]|[1-9][0-9]{2,})(?:\.[0-9]+)*|7\.[0-9]+(?:\.[0-9]+)*)', closure['protobuf']) is not None,
         'protobuf_requirement_refused')


def job(value, name):
    exact(value, {'name', 'done', 'error_count', 'nodes'}, 'job_public_schema_refused')
    same(value['name'], name, 'job_identity_refused')
    same(value['done'], True, 'job_completion_refused')
    same(value['error_count'], 0, 'job_error_count_refused')
    integer(value['nodes'], 1, 256, 'job_nodes_refused')


def host_nested(host, bindings, modules):
    c = modules.controller
    same(host['provenance'], bindings.provenance(c), 'exact_frozen_provenance_required')
    same(host['unchanged_runtime_members'], 112, 'runtime_member_count_type_refused')
    dependency_fixture(host['prepared_dependency_fixture'], c)
    try:
        c.checked_reset(host['fresh_owned_config'])
    except Exception:
        raise EvidenceRefused('fresh_config_proof_refused') from None
    image = dict(reference=c.IMAGE_REFERENCE, identity_model='containerd_index_with_verified_stored_oci_chain',
        observed_container_image_id=c.IMAGE_INDEX_DIGEST, observed_image_inspect_id=c.IMAGE_INDEX_DIGEST,
        official_index_digest=c.IMAGE_INDEX_DIGEST, selected_manifest_digest=c.IMAGE_MANIFEST_DIGEST,
        verified_oci_config_digest=c.IMAGE_CONFIG_ID, stored_objects_hashed=3,
        object_bytes={name:value[1] for name,value in c.IMAGE_OBJECTS.items()},
        containerd_address=c.CONTAINERD_ADDRESS, containerd_namespace=c.CONTAINERD_NAMESPACE,
        platform={'os':'linux','architecture':'amd64'}, rootfs_layers=22,
        image_rootfs_matches_verified_config=True, repository_digest_checked=True)
    same(host['current_core_image'], image, 'exact_image_schema_and_identity_required')
    network = host['network_boundary']
    exact(network, {'link_closed','before_probe_connected','closed_probe_connected','closed_probe_observations','guest_agent_remained_available'}, 'network_public_schema_refused')
    for key,wanted in dict(link_closed=True,before_probe_connected=True,closed_probe_connected=False,guest_agent_remained_available=True).items():
        same(network[key], wanted, 'network_boundary_proof_refused')
    integer(network['closed_probe_observations'], 5, 10000, 'network_observation_count_refused')
    same(host['direct_candidate_installs'], 1, 'candidate_install_count_refused')
    same(host['candidate_transport'], 'stopped_verified_zip_files', 'candidate_transport_scope_refused')
    elapsed = host['host_elapsed_seconds']
    need(type(elapsed) in {int,float} and math.isfinite(elapsed) and 0 < elapsed <= 5800, 'host_elapsed_bound_refused')
    for action in host['core_actions']:
        exact(action, {'action','result','supervisor_running','relevant_core_jobs_idle','running_before','running_after',
                       'container_state_before','container_state_after'}, 'core_action_public_schema_refused')
        start = action['action'] == 'start'
        before = action['container_state_before']
        need(before in ({'stopped','not_created'} if start else {'running'}), 'core_before_state_refused')
        same(action['container_state_after'], 'running' if start else 'stopped', 'core_after_state_refused')
        same(action['running_before'], {'stopped':False,'running':True,'not_created':None}[before], 'core_before_boolean_refused')
        same(action['running_after'], start, 'core_after_boolean_refused')
    for request in host['backup_requests']:
        exact(request, {'action','exit_code','signal','result','stdout_json','output_truncated','api_error','stderr_error','exact_job_id_returned'}, 'backup_request_public_schema_refused')
        same(request['stdout_json'], True, 'backup_json_reply_required')
        for key in ('api_error','stderr_error'):
            same(request[key], {'type':'unclassified','categories':[]}, 'backup_request_error_category_refused')
    backup = host['backup']
    exact(backup, {'result','job','type','homeassistant_version','database_included','protected','compressed','archive'}, 'backup_public_schema_refused')
    for key,wanted in dict(result='ok',type='partial',homeassistant_version=c.CORE,database_included=True,protected=False,compressed=False).items():
        same(backup[key], wanted, 'backup_scope_refused')
    job(backup['job'], 'backup_manager_partial_backup')
    archive = backup['archive']
    bools = {'database_included','candidate_match','enabled_entry','saved_photo_bytes_included','qa_startup_boundary_archive_verified',
             'prepared_dependency_bytes_included','qa_manifest_only_difference','saved_pair_included','saved_config_included',
             'saved_selection_included','saved_registry_joins_included'}
    exact(archive, {*bools,'archive_bytes','guard_sha256'}, 'archive_public_schema_refused')
    for key in bools:
        same(archive[key], True, 'archive_required_proof_refused')
    integer(archive['archive_bytes'], 1, 128 * 1024**2, 'archive_byte_count_refused')
    digest(archive['guard_sha256'], 'archive_guard_digest_refused')
    restore = host['restore']
    exact(restore, {'result','job','qa_startup_boundary_required','restored_old_guard_sha256','promoted_newest_guard_sha256',
                    'host_copy_outside_entire_guest','repaired_before_storage_load','repaired_before_offline_validation'}, 'restore_public_schema_refused')
    same(restore['result'], 'ok', 'restore_result_refused')
    same(restore['qa_startup_boundary_required'], True, 'restore_boundary_required')
    job(restore['job'], 'backup_manager_partial_restore')


def validate_receipts(receipts, bindings):
    exact(receipts, RECEIPTS, 'six_fixed_receipts_required')
    host = receipts['host.json']
    phases = {name:receipts[name + '.json'] for name in PHASES}
    with bindings.modules() as modules:
        # The independently bound source/provenance and nested public schemas are
        # checked before the original narrower acceptance function is consulted.
        exact(host, modules.accept_saved_storage.HOST_KEYS, 'host_public_schema_refused')
        for name, phase in phases.items():
            keys = modules.accept_saved_storage.AUTOMATIC_KEYS if name == 'automatic_restored_enabled' else modules.accept_saved_storage.PHASE_KEYS
            exact(phase, keys, 'phase_public_schema_refused')
        host_nested(host, bindings, modules)
        for name, phase in phases.items():
            need(type(phase) is dict, 'phase_object_required')
            same(phase['qa_manifest_sha256'], bindings.manifest_sha, 'phase_manifest_binding_refused')
            same(phase['runtime_loaded_source_sha256'], bindings.inventory['__init__.py']['sha256'], 'phase_source_binding_refused')
            if name != 'automatic_restored_enabled':
                same(phase['package_payload_sha256'], bindings.payload_sha, 'phase_payload_binding_refused')
                record = phase['recorder']
                need(type(record) is dict, 'recorder_object_required')
                if name in PHASES[3:]:
                    digest(record['postrestore_sha256'], 'postrestore_history_digest_required')
        try:
            scoped = modules.accept_saved_storage.accept(host, phases)
        except Exception:
            raise EvidenceRefused('frozen_scoped_acceptance_refused') from None
        return scoped


def review(artifact_zip, metadata, fixture_dir, workflow_file=None, inputs_file=None):
    bindings = Bindings(fixture_dir, workflow_file, inputs_file)
    raw = read_regular(artifact_zip, 2 * 1024**2)
    supplied = strict_json(read_regular(metadata, 64 * 1024))
    metadata_check(supplied, sha(raw))
    receipts, fingerprints = artifact_receipts(raw)
    scoped = validate_receipts(receipts, bindings)
    return dict(schema=1,outcome='passed',collector_revision=1,run_id=RUN,run_attempt=1,head_sha=HEAD,
        candidate_source_commit=SOURCE,frozen_inputs_sha256=INPUTS_SHA,workflow_sha256=WORKFLOW_SHA,
        frozen_files_verified=28,artifact_id=supplied['artifact_id'],artifact_name=ARTIFACT,
        artifact_zip_sha256=sha(raw),receipts=fingerprints,strict_nested_public_schema_checked=True,
        exact_source_and_tool_provenance_checked=True,root_metadata_separate_from_artifact=True,
        native_trial_repeated_by_collector=False,frozen_native_fixture_modified=False,
        collector_sha256=sha(read_regular(Path(__file__),1024**2)),scoped_acceptance=scoped)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact-zip', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    candidates = [HERE.parent / FIXTURE_NAME, HERE.parents[1] / FIXTURE_NAME]
    default_fixture = next((path for path in candidates if path.is_dir()), candidates[0])
    parser.add_argument('--fixture-dir', type=Path, default=default_fixture)
    parser.add_argument('--workflow', type=Path)
    args = parser.parse_args(argv)
    try:
        need(not args.output.exists() and not args.output.is_symlink(), 'fresh_review_output_required')
        value = review(args.artifact_zip, args.metadata, args.fixture_dir, args.workflow)
        code = 0
    except EvidenceRefused as error:
        value = {'schema':1,'outcome':'refused','failure_code':str(error)}
        code = 1
    except Exception:
        value = {'schema':1,'outcome':'refused','failure_code':'evidence_validation_refused'}
        code = 1
    # An existing file is never overwritten, including either original input.
    try:
        with args.output.open('xb') as stream:
            os.chmod(args.output, 0o600)
            stream.write(json.dumps(value,indent=2,sort_keys=True,allow_nan=False).encode() + b'\n')
    except FileExistsError:
        print(json.dumps({'schema':1,'outcome':'refused','failure_code':'fresh_review_output_required'}))
        return 1
    except OSError:
        print(json.dumps({'schema':1,'outcome':'refused','failure_code':'review_output_write_refused'}))
        return 1
    print(json.dumps({'schema':1,'outcome':value['outcome'],'failure_code':value.get('failure_code')}))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
