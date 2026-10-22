"""Finite adversarial schema controls; fictional values never qualify native work."""
from copy import deepcopy
import ast
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import independent_package as c


def example_bindings():
    return SimpleNamespace(source_sha='d' * 64, source_inventory_sha='e' * 64,
        config_sha='f' * 64, raw={'driver.py': b'reviewed fictional driver'},
        catalog=json.loads((c.HERE / 'SOURCE-INVENTORY.json').read_bytes()),
        required=json.loads((c.HERE / 'REQUIRED-TESTS.json').read_bytes()),
        graph=json.loads((c.HERE / 'EXPECTED-CORE-GRAPH.json').read_bytes()))


def examples(bindings):
    closure = {name: '1.0' for name in c.CLOSURE}
    closure.update(c.DIRECT)
    closure.update({'protobuf': '7.36.0', 'aiohttp': '3.14.5', 'attrs': '26.1.0',
        'certifi': '2026.10.19', 'propcache': '0.5.4', 'typing-extensions': '4.16.0',
        'urllib3': '2.8.0', 'yarl': '1.25.1', 'multidict': '7.1.0', 'setuptools': '84.0.0'})
    setup = c.setup_expected(bindings, closure)
    front = {'schema': 1, 'outcome': 'passed', 'completed': True,
        'frontend_tests_passed': 122, 'frontend_tests_failed': 0, 'frontend_reproducible': True,
        'frontend_bundle': {name.removeprefix('frontend/'): item for name, item in c.GENERATED.items()},
        'leaflet_notice_matches_dependency': True, **c.common_source(bindings),
        'privacy': c.privacy_expected(bindings), 'owner_accounts_used': False,
        'same_version_unreleased_development_preview': True}
    package = {**deepcopy(setup), 'backend': c.backend_expected(bindings),
        'backend_diagnostics': c.diagnostics_expected(), 'baseline_red': c.baseline_expected(),
        'minimum_backend_passed': 1732, 'backend_network_disconnected_required': True,
        'production_configuration_used': False, 'hacs_delivery_tested': False,
        'upgrade_recovery_repeated': False, 'full_managed_core_lifecycle': False}
    host = {'schema': 1, 'outcome': 'passed', 'runner_exit': 0, 'failure_or_final_stage': 'complete',
        'acceptance_actual_exit': 0, 'host_elapsed_seconds': 200.0, 'host_system': 'Linux',
        'host_architecture': 'x86_64', 'host_kernel': 'example-kernel', 'node_version': 'v23.7.0',
        'npm_version': '10.9.2', 'registry_digest': c.IMAGE_DIGEST, 'local_image_id': c.IMAGE_ID,
        **c.common_source(bindings), 'driver_sha256': c.sha(bindings.raw['driver.py']),
        'config_sha256': bindings.config_sha, 'core': c.CORE, 'candidate_zip_sha256': c.ZIP_SHA,
        'candidate_inventory_sha256': c.INVENTORY_SHA, 'canonical_rebuild_sha256': c.CANONICAL_SHA,
        'same_version_unreleased_development_preview': True, 'release_published': False,
        'container_stopped': True, 'container_removed': True, 'cleanup_failed': False,
        'private_workspace_removed': True, 'backend_network_disconnected': True,
        'release_assets_checked': True, 'owner_accounts_used': False,
        'production_configuration_used': False, 'hacs_delivery_tested': False,
        'full_managed_core_lifecycle': False, 'upgrade_recovery_repeated': False}
    return {'host.json': host, 'setup-summary.json': setup,
        'source-summary.json': {'schema': 1, 'outcome': 'passed', **c.common_source(bindings),
            'candidate_source_prefix': '', 'canonical_commit_blobs_verified': c.SOURCE_COUNT,
            'public_inventory_scope_only': True},
        'privacy-summary.json': c.privacy_expected(bindings), 'frontend-summary.json': front,
        'package-summary.json': package}


class PackageContracts(unittest.TestCase):
    def setUp(self):
        self.bindings = example_bindings()
        self.values = examples(self.bindings)

    def rejects(self, callback):
        value = deepcopy(self.values)
        callback(value)
        with self.assertRaises(c.EvidenceRefused):
            c.validate_receipts(value, self.bindings)

    def test_valid_fictional_six_receipt_schema_has_bounded_scope(self):
        result = c.validate_receipts(self.values, self.bindings)
        self.assertEqual(result['required_functions_passed'], 54)
        self.assertFalse(result['input_candidate_replaced_or_rebuilt'])
        self.assertFalse(result['ordinary_restore_qualified_by_this_run'])
        self.assertFalse(result['upgrade_qualified_by_this_run'])
        self.assertFalse(result['stable_release_approval'])

    def test_actual_frozen_preparation_binds_381_source_and_113_candidate_members(self):
        bindings = c.Bindings(c.HERE.parent / 'harness', c.HERE.parent / 'workflow-r1.yml')
        self.assertEqual(len(bindings.catalog), 381)
        self.assertEqual(len(bindings.product), 113)
        self.assertEqual(len(bindings.required), 54)
        self.assertEqual(c.sha(bindings.candidate), c.ZIP_SHA)
        self.assertEqual(c.sha(bindings.inventory_raw), c.INVENTORY_SHA)

    def test_full_counts_and_named_skip_cannot_be_substituted(self):
        for key, value in [('passed', 1731), ('failed', 1), ('skipped', 0), ('skipped', 2),
                           ('passed', 1732.0)]:
            with self.subTest(key=key, value=value):
                self.rejects(lambda v: v['package-summary.json']['backend'].__setitem__(key, value))
        self.rejects(lambda v: v['package-summary.json']['backend'].__setitem__('skip_identities',
            [{'class': 'tests.test_other', 'function': 'test_other'}]))

    def test_all_54_functions_including_real_setup_are_mandatory(self):
        self.rejects(lambda v: v['package-summary.json']['backend']['required_regressions'].pop())
        self.rejects(lambda v: v['package-summary.json']['backend']['required_regressions'][-1].__setitem__('passed', False))
        self.rejects(lambda v: v['package-summary.json']['backend']['required_regressions'].__setitem__(-1,
            deepcopy(v['package-summary.json']['backend']['required_regressions'][0])))

    def test_teardown_duplicates_errors_and_unclassified_cases_refuse(self):
        for key in ['duplicate_records', 'duplicate_identities', 'error_records',
                    'unclassified_failure_records', 'ambiguous_outcome_records']:
            with self.subTest(key=key):
                self.rejects(lambda v: v['package-summary.json']['backend_diagnostics'].__setitem__(key, 1))

    def test_old_vault_causal_red_proof_is_required(self):
        self.rejects(lambda v: v['package-summary.json']['baseline_red'].__setitem__('cause_verified', False))
        self.rejects(lambda v: v['package-summary.json']['baseline_red'].__setitem__('expected_failure_cases', 13))
        self.rejects(lambda v: v['package-summary.json']['baseline_red'].__setitem__('private_copy_removed', False))

    def test_core_graph_auth_sources_and_versions_cannot_drift(self):
        for section in ['setup-summary.json', 'package-summary.json']:
            self.rejects(lambda v: v[section]['core_requirement_graph']['default_auth_modules'].clear())
            self.rejects(lambda v: v[section]['startup_requirement_versions'].clear())
            self.rejects(lambda v: v[section].__setitem__('pytest_homeassistant_custom_component', '0.13.367'))

    def test_closure_names_ranges_and_cross_phase_identity_are_required(self):
        self.rejects(lambda v: v['setup-summary.json']['installed_dependency_closure'].pop('srp'))
        self.rejects(lambda v: v['setup-summary.json']['installed_dependency_closure'].__setitem__('protobuf', '8.0.0'))
        self.rejects(lambda v: v['setup-summary.json']['installed_dependency_closure'].__setitem__('protobuf', '6.31.9'))
        self.rejects(lambda v: v['package-summary.json']['installed_dependency_closure'].__setitem__('certifi', '1.1'))
        def coordinated(v):
            for section in ['setup-summary.json', 'package-summary.json']:
                v[section]['installed_dependency_closure']['aiohttp'] = '999.0'
        self.rejects(coordinated)

    def test_source_privacy_and_coordinated_hash_false_positive_refuse(self):
        self.rejects(lambda v: v['source-summary.json'].__setitem__('canonical_commit_blobs_verified', 380))
        self.rejects(lambda v: v['privacy-summary.json'].__setitem__('flagged_patterns', 1))
        def coordinated(v):
            for record in v.values():
                if 'source_sha256' in record:
                    record['source_sha256'] = 'a' * 64
        self.rejects(coordinated)

    def test_both_privacy_locations_refuse_extra_count_hash_and_flag_changes(self):
        for embedded in (False, True):
            for key, wrong in [('source_files', 381), ('files_checked', 380),
                               ('flagged_patterns', 1), ('checker_exit', 1),
                               ('checker_sha256', 'a' * 64), ('source_sha256', 'a' * 64),
                               ('source_inventory_sha256', 'a' * 64),
                               ('candidate_source_commit', 'b' * 40)]:
                def mutate(v):
                    target = v['frontend-summary.json']['privacy'] if embedded else v['privacy-summary.json']
                    target[key] = wrong
                with self.subTest(embedded=embedded, key=key):
                    self.rejects(mutate)

    def test_privacy_shape_matches_literal_pre_frozen_emitter_without_imports(self):
        bindings = c.Bindings(c.HERE.parent / 'harness', c.HERE.parent / 'workflow-r1.yml')
        module = ast.parse(bindings.raw['driver.py'])
        privacy = next(node for node in module.body
                       if isinstance(node, ast.FunctionDef) and node.name == 'privacy')
        dictionaries = [node.value for node in ast.walk(privacy)
                        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict)]
        self.assertEqual(len(dictionaries), 1)
        leaf_keys = {key.value for key in dictionaries[0].keys if isinstance(key, ast.Constant)}
        emitted = []
        for node in ast.walk(module):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == 'atomic_json' and len(node.args) == 2
                    and isinstance(node.args[1], ast.Dict)):
                continue
            if not any(isinstance(part, ast.Constant) and part.value == 'privacy-summary.json'
                       for part in ast.walk(node.args[0])):
                continue
            fixed = {key.value for key in node.args[1].keys if isinstance(key, ast.Constant)}
            spreads = [value for key, value in zip(node.args[1].keys, node.args[1].values)
                       if key is None]
            self.assertEqual(len(spreads), 1)
            self.assertIsInstance(spreads[0], ast.Call)
            self.assertIsInstance(spreads[0].func, ast.Name)
            self.assertEqual(spreads[0].func.id, 'privacy')
            emitted.append(fixed | leaf_keys)
        self.assertEqual(len(emitted), 1)
        self.assertEqual(set(c.privacy_expected(bindings)), emitted[0])
        self.assertNotIn('source_files', emitted[0])
        self.assertEqual(c.privacy_expected(bindings)['files_checked'], 381)

    def test_original_f181_and_canonical_acfc_must_remain_distinct(self):
        for section in ['setup-summary.json', 'package-summary.json']:
            self.rejects(lambda v: v[section].__setitem__('release_sha256', c.CANONICAL_SHA))
            self.rejects(lambda v: v[section].__setitem__('candidate_archive_rebuilt', True))
            self.rejects(lambda v: v[section].__setitem__('canonical_rebuild_sha256', c.ZIP_SHA))
            self.rejects(lambda v: v[section].__setitem__('candidate_payload_equals_canonical_payload', False))

    def test_only_exact_source_readme_exception_is_allowed(self):
        self.rejects(lambda v: v['package-summary.json']['nonruntime_source_only_files'].append('extra.py'))
        self.rejects(lambda v: v['package-summary.json']['nonruntime_source_only_inventory']['README.md'].__setitem__('sha256', 'b' * 64))
        self.rejects(lambda v: v['setup-summary.json']['nonruntime_source_only_files'].clear())

    def test_frontend_build_license_and_embedded_privacy_are_required(self):
        self.rejects(lambda v: v['frontend-summary.json'].__setitem__('frontend_tests_passed', 121))
        self.rejects(lambda v: v['frontend-summary.json'].__setitem__('frontend_reproducible', False))
        self.rejects(lambda v: v['frontend-summary.json']['frontend_bundle']['homecircle-card.js'].__setitem__('sha256', 'a' * 64))
        self.rejects(lambda v: v['frontend-summary.json']['privacy'].__setitem__('checker_exit', 1))

    def test_offline_cleanup_and_no_owner_flags_are_mandatory(self):
        for key, value in [('backend_network_disconnected', False), ('container_removed', False),
                           ('private_workspace_removed', False), ('cleanup_failed', True),
                           ('owner_accounts_used', True), ('upgrade_recovery_repeated', True)]:
            with self.subTest(key=key):
                self.rejects(lambda v: v['host.json'].__setitem__(key, value))

    def test_exact_nested_fields_and_scalar_types_refuse_loose_equivalence(self):
        self.rejects(lambda v: v['host.json'].__setitem__('runner_exit', False))
        self.rejects(lambda v: v['package-summary.json'].__setitem__('release_files', 113.0))
        self.rejects(lambda v: v['package-summary.json']['backend']['required_regressions'][0].__setitem__('passed', 1))
        self.rejects(lambda v: v['setup-summary.json'].__setitem__('hidden_extra', True))

    def test_duplicate_json_nonfinite_and_deep_inputs_refuse(self):
        for raw in [b'{"schema":1,"schema":1}', b'{"x":NaN}', b'{"x":1e9999}',
                    b'[' * 30 + b'0' + b']' * 30]:
            with self.subTest(raw=raw), self.assertRaises(c.EvidenceRefused):
                c.strict_json(raw)

    def test_metadata_is_exact_and_each_artifact_is_separately_bound(self):
        value = {'schema': 1, 'run_id': 123, 'run_attempt': 1, 'head_sha': 'a' * 40,
            'branch': 'codex/native-amd64-validation', 'event': 'push', 'workflow_path': c.WORKFLOW,
            'workflow_sha256': c.WORKFLOW_SHA, 'artifact_id': 77, 'artifact_name': c.ARTIFACT,
            'artifact_zip_sha256': 'b' * 64, 'github_digest_verified': True,
            'status': 'completed', 'conclusion': 'success'}
        with patch.object(c, 'HEAD', 'a' * 40), patch.object(c, 'RUN', 123), patch.object(c, 'EVENT', 'push'):
            c.metadata_check(value, 'b' * 64, c.ARTIFACT)
            for key, wrong in [('run_id', 123.0), ('event', 'workflow_dispatch'),
                               ('head_sha', 'c' * 40), ('github_digest_verified', False),
                               ('artifact_name', c.CANDIDATE_ARTIFACT)]:
                with self.subTest(key=key), self.assertRaises(c.EvidenceRefused):
                    c.metadata_check({**value, key: wrong}, 'b' * 64, c.ARTIFACT)
            with self.assertRaises(c.EvidenceRefused):
                c.metadata_check(value, 'c' * 64, c.ARTIFACT)

    def test_zip_duplicate_extra_missing_and_symlink_members_refuse(self):
        for kind in ['duplicate', 'extra', 'missing', 'link']:
            raw = io.BytesIO()
            with zipfile.ZipFile(raw, 'w') as archive:
                archive.writestr('a.json', '{}')
                if kind == 'duplicate':
                    archive.writestr('a.json', '{}')
                elif kind == 'extra':
                    archive.writestr('extra.json', '{}')
                elif kind == 'link':
                    info = zipfile.ZipInfo('b.json')
                    info.create_system = 3
                    info.external_attr = 0o120777 << 16
                    archive.writestr(info, 'a.json')
            with self.subTest(kind=kind), self.assertRaises(c.EvidenceRefused):
                c.zip_members(raw.getvalue(), {'a.json', 'b.json'}, 10000)

    def test_dual_artifact_replay_refuses_coordinated_uploaded_candidate_swap(self):
        def zipped(items):
            output = io.BytesIO()
            with zipfile.ZipFile(output, 'w') as archive:
                for name, raw in items.items():
                    archive.writestr(name, raw)
            return output.getvalue()
        self.bindings.candidate = b'fictional immutable candidate bytes'
        self.bindings.inventory_raw = b'fictional immutable inventory bytes'
        receipts = zipped({name: json.dumps(value).encode() for name, value in self.values.items()})
        def metadata(raw, name, identity):
            return {'schema': 1, 'run_id': 123, 'run_attempt': 1, 'head_sha': 'a' * 40,
                'branch': 'codex/native-amd64-validation', 'event': 'push', 'workflow_path': c.WORKFLOW,
                'workflow_sha256': c.WORKFLOW_SHA, 'artifact_id': identity, 'artifact_name': name,
                'artifact_zip_sha256': c.sha(raw), 'github_digest_verified': True,
                'status': 'completed', 'conclusion': 'success'}
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / 'receipts.zip').write_bytes(receipts)
            (base / 'metadata.json').write_text(json.dumps(metadata(receipts, c.ARTIFACT, 1)))
            with patch.object(c, 'Bindings', return_value=self.bindings), patch.object(c, 'HEAD', 'a' * 40), \
                    patch.object(c, 'RUN', 123), patch.object(c, 'EVENT', 'push'):
                for swapped in (False, True):
                    candidate = zipped({'homecircle.zip': b'substituted canonical archive' if swapped
                        else self.bindings.candidate, 'inventory.json': self.bindings.inventory_raw})
                    (base / 'candidate.zip').write_bytes(candidate)
                    (base / 'candidate-metadata.json').write_text(json.dumps(metadata(candidate, c.CANDIDATE_ARTIFACT, 2)))
                    args = (base / 'receipts.zip', base / 'metadata.json', base / 'candidate.zip',
                            base / 'candidate-metadata.json', base, base / 'workflow.yml')
                    if swapped:
                        with self.assertRaisesRegex(c.EvidenceRefused, 'uploaded_candidate_substitution_refused'):
                            c.review(*args)
                    else:
                        self.assertEqual(c.review(*args)['outcome'], 'passed')


if __name__ == '__main__':
    unittest.main()
