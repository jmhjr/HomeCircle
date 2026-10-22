"""Independent full-package receipt consumer; standard library and frozen data only."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import stat
import tarfile
import zipfile

HERE = Path(__file__).resolve().parent
SOURCE = '3c33160c67e53956ab52298ffc10ccc9992132f0'
SOURCE_COUNT = 381
SOURCE_CATALOG_SHA = 'cde46764cb35999081519197d5ab8db582c7a6e6fd36cb6c10a6a65b12becd95'
ZIP_SHA = 'f181e6300f15d8977817a552db90d35caf0edc869067ebeea815c7be1df0248e'
ZIP_BYTES = 623447
INVENTORY_SHA = '8ea456beb9b2eaaf4ba50639532b8dafabe0e02d1e13a77a59525f1c249c7447'
CANONICAL_SHA = 'acfcda419a817032c38a463505f686b0f6ab49e69a8f1603d9b2ff43f24e442b'
CANONICAL_BYTES = 620358
GRAPH_SHA = '851049f5e908c558d9208aa02f900be1dcdbf823c6b50cb99d02364218c5133d'
REQUIRED_SHA = '1391e1b28de1dec68a3931910f8f79f8ba30ffd993fba533150330e9843592c6'
CANONICAL_INVENTORY_SHA = '16b3e05d0ac0804187f99d0562629a140972adc7ac0895a40cfdc8394724cd04'
HEAD = '69be6211e24609fc3f020dd8407acb25b99c175a'
RUN = 39865496620
EVENT = 'push'
INPUTS_SHA = 'da559866a520672101f701759545e3f38ed1432f68be54b4a3e71295b30f8836'
WORKFLOW_SHA = 'bf076fd90a4690b7c571ff6c102aa61af45bb660685047c3eac65fc01e0fa6f0'
INPUT_COUNT = 14
WORKFLOW = '.github/workflows/native-fixed-package.yml'
PREFIX = 'native-fixed-package'
ARTIFACT = 'fixed-package-validation-receipts'
CANDIDATE_ARTIFACT = 'unreleased-fixed-candidate'
CORE = '2026.10.2'
CONSTRAINTS = '7baa9a8f39ddeb9c5bb60a1036f6d5e33f4b84267f151f53cc2b95ef031a21b5'
IMAGE_DIGEST = 'sha256:45f009d6ff1061971102e81f0802cf2762bdd5c5007231c938bd36030cbd0a12'
IMAGE_ID = 'sha256:e1acee126eee45b3007494ad7f806d12535dc7d733624b681ed29a505f8c2b98'
BUILDER = '0c1ac7f979817bd5fc2cd4a4101571931488d6972bc6f181a26ac21edcf8c7d0'
VALIDATOR = '20c0466b4fa70a83c5f282bfcd07b0d2e6f5a3a1a09bf90072649441b2ad7f37'
CHECKER = '216331d16af8fb2ec636e1466303923ecfe32c76f78ea72f89d373c80c9713d2'
RECEIPTS = frozenset({'host.json', 'setup-summary.json', 'source-summary.json',
    'privacy-summary.json', 'frontend-summary.json', 'package-summary.json'})
META_KEYS = frozenset({'schema', 'run_id', 'run_attempt', 'head_sha', 'branch', 'event',
    'workflow_path', 'workflow_sha256', 'artifact_id', 'artifact_name', 'artifact_zip_sha256',
    'github_digest_verified', 'status', 'conclusion'})
SKIP = {'class': 'tests.test_findmy_runtime_bootstrap',
        'function': 'test_retained_public_apple_dmg_fixed_ranges'}
GENERATED = {
    'frontend/homecircle-card.js': {'bytes': 276650, 'sha256': '77f429fb1908acc21cde2c89614f05f12c60a09bb37fa6ca78a1830ec07c6f91'},
    'frontend/LEAFLET-LICENSE.txt': {'bytes': 1395, 'sha256': '53e8dc25862014e4324741ca18fbe3611e11d42ef69f59f86ea8c5389647d4cb'}}
CLOSURE = frozenset({'aiohappyeyeballs', 'aiohttp', 'aiosignal', 'anisette', 'appdirs',
    'attrs', 'beautifulsoup4', 'certifi', 'frozenlist', 'fs', 'idna', 'life360', 'multidict',
    'propcache', 'protobuf', 'pyelftools', 'setuptools', 'six', 'soupsieve', 'srp',
    'typing-extensions', 'unicorn', 'urllib3', 'yarl'})
DIRECT = {'life360': '7.2.0', 'anisette': '1.2.4', 'unicorn': '2.1.4',
          'srp': '1.0.22', 'beautifulsoup4': '4.13.3'}


class EvidenceRefused(ValueError):
    """Fixed labels only; untrusted field values and exception text stay private."""


def need(ok, label):
    if not ok:
        raise EvidenceRefused(label)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fp(raw):
    return {'bytes': len(raw), 'sha256': sha(raw)}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def same(actual, expected, label):
    need(type(actual) is type(expected), label)
    if type(expected) is dict:
        need(set(actual) == set(expected), label)
        for name, value in expected.items():
            same(actual[name], value, label)
    elif type(expected) in (list, tuple):
        need(len(actual) == len(expected), label)
        for left, right in zip(actual, expected):
            same(left, right, label)
    else:
        need(actual == expected, label)


def exact(value, keys, label):
    need(type(value) is dict and set(value) == set(keys), label)


def integer(value, low, high, label):
    need(type(value) is int and low <= value <= high, label)


def digest(value, label):
    need(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None, label)


def read(path, maximum=64 * 1024**2):
    path = Path(path)
    need(not path.is_symlink() and path.is_file() and 0 < path.stat().st_size <= maximum,
         'input_file_refused')
    return path.read_bytes()


def strict_json(raw):
    need(type(raw) is bytes and len(raw) <= 2 * 1024**2, 'json_size_refused')
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'duplicate_json_key_refused')
            result[key] = value
        return result
    def constant(_):
        raise EvidenceRefused('nonfinite_json_refused')
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError) as error:
        if type(error) is EvidenceRefused:
            raise
        raise EvidenceRefused('json_encoding_refused') from None
    count = 0
    def visit(item, depth):
        nonlocal count
        count += 1
        need(depth <= 24 and count <= 100_000, 'json_nesting_refused')
        if type(item) is dict:
            for child in item.values():
                visit(child, depth + 1)
        elif type(item) is list:
            for child in item:
                visit(child, depth + 1)
        elif type(item) is float:
            need(math.isfinite(item), 'nonfinite_json_refused')
        else:
            need(type(item) in (str, int, bool, type(None)), 'json_scalar_refused')
    visit(value, 0)
    return value


def safe_name(name):
    path = PurePosixPath(name)
    return (type(name) is str and name == path.as_posix() and not path.is_absolute()
        and path.parts and not {'.', '..', '.git'}.intersection(path.parts)
        and not any(char in name for char in '\\\0\r\n'))


def zip_members(raw, expected, maximum):
    need(type(raw) is bytes and 0 < len(raw) <= maximum, 'artifact_size_refused')
    files = {}
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            need(len(archive.infolist()) == len(expected), 'artifact_member_count_refused')
            total = 0
            for member in archive.infolist():
                need(safe_name(member.filename) and member.filename in expected
                    and member.filename not in files and not member.is_dir()
                    and not stat.S_ISLNK(member.external_attr >> 16) and not member.flag_bits & 1
                    and 0 < member.file_size <= maximum, 'artifact_member_refused')
                total += member.file_size
                need(total <= maximum, 'artifact_expansion_refused')
                files[member.filename] = archive.read(member)
    except (zipfile.BadZipFile, RuntimeError, OSError, NotImplementedError):
        raise EvidenceRefused('artifact_zip_refused') from None
    need(set(files) == set(expected), 'artifact_names_refused')
    return files


def metadata_check(value, artifact_sha, name):
    need(re.fullmatch('[0-9a-f]{40}', HEAD) is not None and type(RUN) is int and RUN > 0
         and EVENT in {'push', 'workflow_dispatch'}, 'run_anchor_not_frozen')
    exact(value, META_KEYS, 'metadata_schema_refused')
    fixed = {'schema': 1, 'run_id': RUN, 'run_attempt': 1, 'head_sha': HEAD,
        'branch': 'codex/native-amd64-validation', 'event': EVENT, 'workflow_path': WORKFLOW,
        'workflow_sha256': WORKFLOW_SHA, 'artifact_name': name,
        'artifact_zip_sha256': artifact_sha, 'github_digest_verified': True,
        'status': 'completed', 'conclusion': 'success'}
    for key, wanted in fixed.items():
        same(value[key], wanted, 'metadata_binding_refused')
    integer(value['artifact_id'], 1, 2**63 - 1, 'artifact_id_refused')
    digest(value['artifact_zip_sha256'], 'artifact_digest_refused')


class Bindings:
    def __init__(self, folder, workflow):
        self.folder = Path(folder).resolve()
        need(self.folder.is_dir() and not Path(folder).is_symlink(), 'fixture_root_refused')
        raw = read(HERE / 'INPUTS.json', 128 * 1024)
        need(sha(raw) == INPUTS_SHA, 'inputs_digest_refused')
        inputs = strict_json(raw)
        exact(inputs, {'schema', 'source_commit', 'fixture_name', 'files'}, 'inputs_schema_refused')
        same(inputs['schema'], 1, 'inputs_schema_refused')
        same(inputs['source_commit'], SOURCE, 'inputs_source_refused')
        same(inputs['fixture_name'], PREFIX, 'inputs_name_refused')
        need(type(inputs['files']) is dict and len(inputs['files']) == INPUT_COUNT,
             'input_count_refused')
        self.raw = {}
        workflow_raw = read(workflow, 256 * 1024)
        need(sha(workflow_raw) == WORKFLOW_SHA, 'workflow_digest_refused')
        for name, item in inputs['files'].items():
            need(safe_name(name), 'input_name_refused')
            exact(item, {'bytes', 'sha256'}, 'input_fingerprint_schema_refused')
            integer(item['bytes'], 1, 64 * 1024**2, 'input_bytes_refused')
            digest(item['sha256'], 'input_sha_refused')
            content = workflow_raw if name == WORKFLOW else read(self.folder / name)
            same(fp(content), item, 'input_bytes_mismatch')
            if name != WORKFLOW:
                self.raw[name] = content
        nodes = list(self.folder.rglob('*'))
        need(not any(path.is_symlink() for path in nodes), 'input_symlink_refused')
        actual = {path.relative_to(self.folder).as_posix() for path in nodes
                  if path.is_file() and '__pycache__' not in path.parts}
        need(actual == set(self.raw), 'input_members_refused')
        source_raw = read(HERE / 'SOURCE-INVENTORY.json', 256 * 1024)
        need(sha(source_raw) == SOURCE_CATALOG_SHA, 'source_catalog_digest_refused')
        self.catalog = strict_json(source_raw)
        need(type(self.catalog) is dict and len(self.catalog) == SOURCE_COUNT,
             'source_catalog_count_refused')
        source_inventory = strict_json(self.raw['payload/source-inventory.json'])
        same(source_inventory, self.catalog, 'source_inventory_catalog_mismatch')
        self.source_sha = sha(self.raw['payload/source.tgz'])
        self.source_inventory_sha = sha(self.raw['payload/source-inventory.json'])
        self.source_archive()
        matches = [raw for raw in self.raw.values() if sha(raw) == ZIP_SHA]
        need(len(matches) == 1, 'immutable_candidate_input_missing')
        self.candidate = matches[0]
        need(len(self.candidate) == ZIP_BYTES, 'immutable_candidate_size_refused')
        matches = [raw for raw in self.raw.values() if sha(raw) == INVENTORY_SHA]
        need(len(matches) == 1, 'immutable_candidate_inventory_missing')
        self.inventory_raw = matches[0]
        expected = strict_json(self.inventory_raw)
        exact(expected, {'version', 'archive_sha256', 'files'}, 'product_inventory_schema_refused')
        same(expected['version'], '0.1.0-beta.20', 'product_version_refused')
        same(expected['archive_sha256'], ZIP_SHA, 'product_archive_binding_refused')
        need(type(expected['files']) is dict and len(expected['files']) == 113,
             'product_count_refused')
        self.product = zip_members(self.candidate, expected['files'], 16 * 1024**2)
        for name, content in self.product.items():
            same(fp(content), expected['files'][name], 'product_inventory_bytes_refused')
            wanted = GENERATED.get(name)
            if wanted is None:
                wanted = self.catalog.get('LICENSE' if name == 'LICENSE'
                                          else 'custom_components/homecircle/' + name)
            same(fp(content), wanted, 'literal_source_or_generated_binding_refused')
        graph_raw = read(HERE / 'EXPECTED-CORE-GRAPH.json', 128 * 1024)
        need(sha(graph_raw) == GRAPH_SHA, 'expected_core_graph_digest_refused')
        self.graph = strict_json(graph_raw)
        required_raw = read(HERE / 'REQUIRED-TESTS.json', 128 * 1024)
        need(sha(required_raw) == REQUIRED_SHA, 'expected_required_digest_refused')
        self.required = strict_json(required_raw)
        need(type(self.required) is list and len(self.required) == 54
            and len({(item['class'], item['function']) for item in self.required}) == 54,
            'expected_required_functions_refused')
        self.config_sha = sha(self.raw['payload/config.json'])
        fixed_config = {'schema': 1, 'candidate_source_commit': SOURCE,
            'candidate_source_prefix': '', 'source_sha256': self.source_sha,
            'source_inventory_sha256': self.source_inventory_sha, 'source_files': SOURCE_COUNT,
            'driver_sha256': sha(self.raw['driver.py']), 'checker_sha256': CHECKER,
            'version': '0.1.0-beta.20', 'expected_release_files': 113,
            'minimum_backend_passed': 1732, 'required_backend_tests': self.required,
            'frontend_tests': 122, 'package_sha256': ZIP_SHA,
            'package_inventory_sha256': INVENTORY_SHA, 'canonical_package_sha256': CANONICAL_SHA,
            'requirements_helper_sha256': '91bb0d92bfeef8021184275369d8923e8b951d2cb7b85a31bd34414101e3a513'}
        same(strict_json(self.raw['payload/config.json']), fixed_config, 'bound_config_refused')

    def source_archive(self):
        raw = self.raw['payload/source.tgz']
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            expanded = stream.read(64 * 1024**2 + 1)
        need(len(expanded) <= 64 * 1024**2, 'source_expansion_refused')
        found = {}
        with tarfile.open(fileobj=io.BytesIO(expanded), mode='r:') as archive:
            need(not archive.pax_headers, 'source_tar_metadata_refused')
            for member in archive:
                need(member.isfile() and not member.pax_headers and member.name in self.catalog
                    and member.name not in found and member.size == self.catalog[member.name]['bytes'],
                    'source_tar_member_refused')
                with archive.extractfile(member) as stream:
                    content = stream.read(member.size + 1)
                same(fp(content), self.catalog[member.name], 'source_tar_bytes_refused')
                found[member.name] = True
        need(set(found) == set(self.catalog), 'source_tar_names_refused')


def closure_check(value):
    exact(value, CLOSURE, 'dependency_closure_names_refused')
    for version in value.values():
        need(type(version) is str and re.fullmatch('[0-9]{1,8}(?:[.][0-9]{1,8}){1,3}', version),
             'dependency_version_refused')
    for name, version in DIRECT.items():
        same(value[name], version, 'direct_dependency_version_refused')
    protobuf = tuple(int(part) for part in value['protobuf'].split('.'))
    need((6, 32) <= protobuf < (8,), 'protobuf_range_refused')
    constraints_raw = read(HERE / 'EXPECTED-CONSTRAINTS.txt', 128 * 1024)
    need(sha(constraints_raw) == CONSTRAINTS, 'expected_constraints_digest_refused')
    def numeric(version):
        parts = tuple(int(part) for part in version.split('.'))
        return parts + (0,) * (8 - len(parts))
    checked = set()
    for raw in constraints_raw.decode().splitlines():
        line = raw.split('#', 1)[0].strip()
        if not line:
            continue
        match = re.fullmatch(r'([A-Za-z0-9_.-]+)(.*)', line)
        need(match is not None, 'core_constraint_syntax_refused')
        name = match[1].lower().replace('_', '-')
        if name not in value:
            continue
        actual = numeric(value[name])
        for expression in match[2].split(','):
            item = re.fullmatch(r'(==|>=|<=|!=|>|<)([0-9]+(?:\.[0-9]+)*)', expression.strip())
            need(item is not None, 'core_numeric_constraint_refused')
            wanted = numeric(item[2])
            ok = {'==': actual == wanted, '>=': actual >= wanted, '<=': actual <= wanted,
                  '!=': actual != wanted, '>': actual > wanted, '<': actual < wanted}[item[1]]
            need(ok, 'dependency_core_constraint_refused')
        checked.add(name)
    need(checked == {'aiohttp', 'attrs', 'certifi', 'propcache', 'typing-extensions',
                     'urllib3', 'yarl', 'multidict', 'protobuf', 'setuptools'},
         'core_constraint_projection_refused')


def common_source(bindings):
    return {'candidate_source_commit': SOURCE, 'source_sha256': bindings.source_sha,
        'source_inventory_sha256': bindings.source_inventory_sha, 'source_files': SOURCE_COUNT}


def build_expected(bindings):
    return {'release_version': '0.1.0-beta.20', 'release_sha256': ZIP_SHA,
        'release_inventory_sha256': INVENTORY_SHA, 'release_bytes': ZIP_BYTES, 'release_files': 113,
        'candidate_archive_rebuilt': False, 'exact_candidate_bytes_installed': True,
        'candidate_compression_level': 6, 'canonical_compression_level': 9,
        'canonical_rebuild_sha256': CANONICAL_SHA,
        'canonical_rebuild_inventory_sha256': CANONICAL_INVENTORY_SHA,
        'canonical_reproducible_archive': True, 'candidate_payload_equals_canonical_payload': True,
        'package_matches_exact_source_and_built_frontend': True, 'unchanged_builder_sha256': BUILDER,
        'unchanged_validator_sha256': VALIDATOR, 'same_version_unreleased_development_preview': True,
        'release_published': False, 'version_substitutions_performed': False,
        'candidate_source_commit': SOURCE, 'nonruntime_source_only_files': ['README.md'],
        'nonruntime_source_only_inventory': {'README.md':
            bindings.catalog['custom_components/homecircle/README.md']}}


def privacy_expected(bindings):
    return {'schema': 1, 'outcome': 'passed', 'candidate_source_commit': SOURCE,
        'source_sha256': bindings.source_sha, 'source_inventory_sha256': bindings.source_inventory_sha,
        'checker_sha256': CHECKER, 'files_checked': SOURCE_COUNT, 'checker_exit': 0,
        'flagged_patterns': 0}


def setup_expected(bindings, closure):
    closure_check(closure)
    return {**build_expected(bindings), **common_source(bindings), 'schema': 1,
        'outcome': 'passed', 'completed': True, 'core': CORE, 'python': '3.14.6',
        'machine': 'x86_64', 'constraints_sha256': CONSTRAINTS,
        'installed_dependency_closure': closure,
        'core_requirement_graph': bindings.graph['core_requirement_graph'],
        'startup_requirement_versions': bindings.graph['startup_requirement_versions'],
        'pytest_homeassistant_custom_component': '0.13.373', 'owner_accounts_used': False}


def baseline_expected():
    return {'schema': 1, 'outcome': 'passed', 'cause_verified': True,
        'expected_failure_cases': 14, 'all_expected_regressions_observed': True,
        'collection_errors': 0, 'skipped': 0,
        'baseline_source_commit': 'fc0bba472cd60a06dac6bab30b7d011fd533624b',
        'baseline_vault_sha256': '7c6a846cefba6a34647d84b7738a93d85738a948da32fbf752a96c4e1cf4c0f2',
        'public_files_only_copy': True, 'private_copy_removed': True,
        'fixed_source_unchanged': True, 'provider_or_owner_accounts_used': False,
        'combined_red_green_deadline_seconds': 900}


def backend_expected(bindings):
    return {'passed': 1732, 'failed': 0, 'skipped': 1,
        'required_regressions': [{**item, 'passed': True} for item in bindings.required],
        'failure_labels': [], 'skip_identities': [SKIP]}


def diagnostics_expected():
    return {'schema': 1, 'scope': 'unaccepted_junit_record_diagnostics', 'acceptance_qualified': False,
        'case_records': 1733, 'duplicate_identities': 0, 'duplicate_label_functions': 0,
        'duplicate_labels': [], 'duplicate_records': 0, 'error_records': 0, 'failed': 0,
        'failure_label_functions': 0, 'failure_labels': [], 'failure_records': 0,
        'maximum_label_functions_per_kind': 12, 'passed': 1732, 'public_source_bound_labels': True,
        'raw_failure_text_exported': False, 'raw_test_parameters_exported': False, 'skipped': 1,
        'unclassified_duplicate_identities': 0, 'unclassified_failure_records': 0,
        'ambiguous_outcome_records': 0}


def validate_receipts(values, bindings):
    exact(values, RECEIPTS, 'six_receipts_required')
    same(values['source-summary.json'], {'schema': 1, 'outcome': 'passed', **common_source(bindings),
        'candidate_source_prefix': '', 'canonical_commit_blobs_verified': SOURCE_COUNT,
        'public_inventory_scope_only': True}, 'source_receipt_refused')
    same(values['privacy-summary.json'], privacy_expected(bindings), 'privacy_receipt_refused')
    frontend_bundle = {name.removeprefix('frontend/'): item for name, item in GENERATED.items()}
    same(values['frontend-summary.json'], {'schema': 1, 'outcome': 'passed', 'completed': True,
        'frontend_tests_passed': 122, 'frontend_tests_failed': 0, 'frontend_reproducible': True,
        'frontend_bundle': frontend_bundle, 'leaflet_notice_matches_dependency': True,
        **common_source(bindings), 'privacy': privacy_expected(bindings),
        'owner_accounts_used': False, 'same_version_unreleased_development_preview': True},
        'frontend_receipt_refused')
    setup = values['setup-summary.json']
    need(type(setup) is dict and 'installed_dependency_closure' in setup, 'setup_receipt_refused')
    closure = setup['installed_dependency_closure']
    same(setup, setup_expected(bindings, closure), 'setup_receipt_refused')
    package = {**setup_expected(bindings, closure),
        'backend': backend_expected(bindings), 'backend_diagnostics': diagnostics_expected(),
        'baseline_red': baseline_expected(), 'minimum_backend_passed': 1732,
        'backend_network_disconnected_required': True, 'production_configuration_used': False,
        'hacs_delivery_tested': False, 'upgrade_recovery_repeated': False,
        'full_managed_core_lifecycle': False}
    same(values['package-summary.json'], package, 'full_package_receipt_refused')
    host = values['host.json']
    fixed = {'schema': 1, 'outcome': 'passed', 'runner_exit': 0,
        'failure_or_final_stage': 'complete', 'acceptance_actual_exit': 0,
        'host_system': 'Linux', 'host_architecture': 'x86_64', 'node_version': 'v23.7.0',
        'npm_version': '10.9.2', 'registry_digest': IMAGE_DIGEST, 'local_image_id': IMAGE_ID,
        **common_source(bindings), 'driver_sha256': sha(bindings.raw['driver.py']),
        'config_sha256': bindings.config_sha, 'core': CORE, 'candidate_zip_sha256': ZIP_SHA,
        'candidate_inventory_sha256': INVENTORY_SHA, 'canonical_rebuild_sha256': CANONICAL_SHA,
        'same_version_unreleased_development_preview': True, 'release_published': False,
        'container_stopped': True, 'container_removed': True, 'cleanup_failed': False,
        'private_workspace_removed': True, 'backend_network_disconnected': True,
        'release_assets_checked': True, 'owner_accounts_used': False,
        'production_configuration_used': False, 'hacs_delivery_tested': False,
        'full_managed_core_lifecycle': False, 'upgrade_recovery_repeated': False}
    exact(host, {*fixed, 'host_kernel', 'host_elapsed_seconds'}, 'host_schema_refused')
    for key, wanted in fixed.items():
        same(host[key], wanted, 'host_receipt_refused')
    need(type(host['host_kernel']) is str and re.fullmatch('[A-Za-z0-9_.+-]{1,160}', host['host_kernel']),
         'host_kernel_refused')
    need(type(host['host_elapsed_seconds']) in (int, float)
         and math.isfinite(host['host_elapsed_seconds']) and 0 < host['host_elapsed_seconds'] <= 3600,
         'host_elapsed_refused')
    return {'outcome': 'passed', 'scope': 'native_current_core_full_package_suite_only',
        'backend_passed': 1732, 'backend_failed': 0, 'backend_only_named_optional_skip': True,
        'required_functions_passed': 54, 'frontend_passed': 122,
        'canonical_source_files_verified': SOURCE_COUNT, 'source_privacy_flags': 0,
        'cause_verified_old_vault_red_cases': 14, 'exact_input_candidate_verified': True,
        'input_candidate_replaced_or_rebuilt': False, 'canonical_rebuild_reported_separately': True,
        'nonruntime_source_only_files': ['README.md'], 'dependency_and_core_graph_verified': True,
        'backend_offline': True, 'cleanup_verified': True, 'ordinary_restore_qualified_by_this_run': False,
        'upgrade_qualified_by_this_run': False, 'provider_authentication_qualified': False,
        'hacs_delivery_qualified': False, 'stable_release_approval': False}


def review(artifact, metadata, candidate_artifact, candidate_metadata, folder, workflow):
    bindings = Bindings(folder, workflow)
    raw = read(artifact, 3 * 1024**2)
    candidate_raw = read(candidate_artifact, 3 * 1024**2)
    root_meta = strict_json(read(metadata, 64 * 1024))
    candidate_meta = strict_json(read(candidate_metadata, 64 * 1024))
    metadata_check(root_meta, sha(raw), ARTIFACT)
    metadata_check(candidate_meta, sha(candidate_raw), CANDIDATE_ARTIFACT)
    need(root_meta['artifact_id'] != candidate_meta['artifact_id'], 'artifact_identity_alias_refused')
    candidate = zip_members(candidate_raw, {'homecircle.zip', 'inventory.json'}, 3 * 1024**2)
    need(candidate['homecircle.zip'] == bindings.candidate
         and candidate['inventory.json'] == bindings.inventory_raw, 'uploaded_candidate_substitution_refused')
    receipt_raw = zip_members(raw, RECEIPTS, 3 * 1024**2)
    values = {name: strict_json(content) for name, content in receipt_raw.items()}
    acceptance = validate_receipts(values, bindings)
    return {'schema': 1, 'outcome': 'passed', 'run_id': RUN, 'run_attempt': 1, 'head_sha': HEAD,
        'event': EVENT, 'workflow_sha256': WORKFLOW_SHA, 'frozen_inputs_sha256': INPUTS_SHA,
        'frozen_inputs_verified': INPUT_COUNT, 'candidate_source_commit': SOURCE,
        'source_catalog_sha256': SOURCE_CATALOG_SHA, 'source_files': SOURCE_COUNT,
        'candidate_zip_sha256': ZIP_SHA, 'candidate_inventory_sha256': INVENTORY_SHA,
        'canonical_rebuild_sha256': CANONICAL_SHA, 'product_files': 113,
        'literal_source_members': 111, 'unchanged_generated_frontend_members': 2,
        'artifact_id': root_meta['artifact_id'], 'artifact_zip_sha256': sha(raw),
        'candidate_artifact_id': candidate_meta['artifact_id'],
        'candidate_artifact_zip_sha256': sha(candidate_raw),
        'receipts': {name: fp(content) for name, content in sorted(receipt_raw.items())},
        'root_metadata_separate_from_artifacts': True, 'fixture_or_provider_modules_imported': False,
        'collector_sha256': sha(read(Path(__file__), 1024**2)), 'scoped_acceptance': acceptance}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-dir', type=Path, required=True)
    parser.add_argument('--workflow', type=Path, required=True)
    parser.add_argument('--artifact-zip', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--candidate-artifact-zip', type=Path, required=True)
    parser.add_argument('--candidate-metadata', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    need(not args.output.exists() and not args.output.is_symlink(), 'fresh_output_required')
    try:
        result = review(args.artifact_zip, args.metadata, args.candidate_artifact_zip,
                        args.candidate_metadata, args.fixture_dir, args.workflow)
    except Exception as error:
        result = {'schema': 1, 'outcome': 'refused', 'failure_code':
                  str(error) if type(error) is EvidenceRefused else 'consumer_operation_refused'}
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'schema': 1, 'outcome': result['outcome']}))
    return 0 if result['outcome'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
