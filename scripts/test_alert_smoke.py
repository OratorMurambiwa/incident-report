"""Regression for smoke-test observers selecting recurring alert fingerprints."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('alert_smoke', Path(__file__).with_name('smoke-auto-detection.py'))
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class AlertOccurrenceTests(unittest.TestCase):
    def test_previous_resolved_occurrence_is_not_current(self):
        old = {'starts_at': '2026-11-06T12:00:00+00:00', 'status': 'RESOLVED'}
        with patch.object(smoke, 'db', return_value=old):
            self.assertIsNone(smoke.observation('same-fingerprint', '2026-11-07T12:00:00Z'))

    def test_current_occurrence_normalizes_postgres_timestamp_precision(self):
        row = {'starts_at': '2026-11-07T12:00:00.123456+00:00', 'status': 'RECEIVED'}
        with patch.object(smoke, 'db', return_value=row):
            self.assertEqual(smoke.observation('fingerprint', '2026-11-07T12:00:00.123456789Z'), row)

    def test_current_webhook_not_delivered_yet(self):
        with patch.object(smoke, 'db', return_value=None):
            self.assertIsNone(smoke.observation('fingerprint', '2026-11-07T12:00:00Z'))


if __name__ == '__main__':
    unittest.main()
