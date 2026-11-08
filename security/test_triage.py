"""Regression tests for comparison accounting, not hardcoded vulnerability targets."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('triage', Path(__file__).with_name('triage.py'))
triage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(triage)


def report(packages, vulnerabilities):
    return {'Metadata': {'ImageID': 'sha256:test'}, 'CreatedAt': 'test',
            'Results': [{'Type': 'debian', 'Target': 'OS', 'Packages': packages,
                         'Vulnerabilities': vulnerabilities}]}


def vulnerability(package, cve='CVE-2026-test', severity='HIGH'):
    return {'PkgName': package, 'VulnerabilityID': cve, 'InstalledVersion': '1', 'Severity': severity}


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.policy = {'CVE-2026-test': {'exploit_conditions': 'test'}}

    def test_duplicate_binary_rows_are_retained_and_grouped_by_source(self):
        packages = [{'Name': n, 'Version': '1', 'SrcName': 'common'} for n in ['liba', 'libb']]
        before = report(packages, [vulnerability(p['Name']) for p in packages])
        result = triage.compare('worker', before, before, self.policy)
        self.assertEqual(result['before_ch_occurrences'], 2)
        self.assertEqual(result['before_unique_ch_cves'], 1)
        self.assertEqual(list(result['duplicate_source_groups'].values()), [2])
        self.assertEqual(len(result['rows']), 2)

    def test_updated_and_removed_packages_are_distinguished_by_inventory(self):
        before = report([], [vulnerability('updated'), vulnerability('removed')])
        after = report([{'Name': 'updated', 'Version': '2'}], [])
        result = triage.compare('worker', before, after, self.policy)
        self.assertEqual([r['disposition'] for r in result['rows']],
                         ['not detected in updated package', 'package absent from inventory'])

    def test_changed_severity_is_not_claimed_as_remediation(self):
        before = report([], [vulnerability('lib')])
        after = report([{'Name': 'lib', 'Version': '1'}], [vulnerability('lib', severity='MEDIUM')])
        row = triage.compare('worker', before, after, self.policy)['rows'][0]
        self.assertEqual(row['disposition'], 'present')
        self.assertEqual(row['after_severities'], ['MEDIUM'])

    def test_unknown_new_critical_finding_fails_review(self):
        with self.assertRaisesRegex(ValueError, 'unreviewed'):
            triage.compare('worker', report([], []), report([], [vulnerability('lib', 'CVE-new', 'CRITICAL')]), self.policy)

    def test_unreviewed_baseline_finding_fails_review(self):
        with self.assertRaises(KeyError):
            triage.compare('worker', report([], [vulnerability('lib', 'CVE-new')]), report([], []), self.policy)

    def test_os_versions_retain_security_revision_and_epoch(self):
        self.assertEqual(triage.package_version({'Version': '1.3.1', 'Epoch': 1, 'Release': '1+deb13u1'}), '1:1.3.1-1+deb13u1')

    def test_database_guard_rejects_modified_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'db').write_bytes(b'original')
            expected = {'db': {'bytes': 8, 'sha256': triage.digest(root / 'db')}}
            triage.verify_database(root, expected)
            (root / 'db').write_bytes(b'changed!')
            with self.assertRaisesRegex(ValueError, 'changed'):
                triage.verify_database(root, expected)


if __name__ == '__main__':
    unittest.main()
