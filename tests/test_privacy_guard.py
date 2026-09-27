"""Tests of bootstrap privacy guard, not HomeCircle runtime functionality."""
import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('guard', Path(__file__).resolve().parents[1] / 'scripts/check_public_files.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

class PrivacyGuardTests(unittest.TestCase):
    def test_generic_config_allowed(self):
        data = {'entity': 'person.example_member', 'location': None}
        self.assertEqual(guard.violations('example.json', json.dumps(data).encode()), [])

    def test_zero_coordinates_rejected(self):
        data = dict.fromkeys(('latitude', 'longitude'), int('0'))
        self.assertIn('numeric coordinate field', guard.violations('example.json', json.dumps(data).encode()))

    def test_unknown_entity_rejected(self):
        value = 'person.' + 'synthetic_unapproved'
        self.assertIn('non-example entity identifier', guard.violations('example.txt', value.encode()))

    def test_key_detection(self):
        value = 'AIza' + 'x' * 35
        self.assertIn('Google key', guard.violations('example.txt', value.encode()))

    def test_private_paths_and_binaries_rejected(self):
        self.assertIn('private/runtime path', guard.violations('.private/example.txt', b'example'))
        self.assertIn('unreviewed binary file', guard.violations('asset.dat', bytes([255, 254])))
        self.assertIn('unreviewed media/archive/secret artifact', guard.violations('asset.png', b'example'))

    def test_reviewed_brand_requires_exact_bytes_and_path(self):
        name = 'custom_components/homecircle/brand/icon.png'
        data = (Path(__file__).resolve().parents[1] / name).read_bytes()
        self.assertEqual(guard.violations(name, data), [])
        self.assertTrue(guard.violations(name, data + b'changed'))
        self.assertTrue(guard.violations('another.png', data))

if __name__ == '__main__':
    unittest.main()
