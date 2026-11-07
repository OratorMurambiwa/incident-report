import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('bench_runner', Path(__file__).resolve().parent.parent/'scripts'/'benchmark.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
RUN = '20261107t120000z_1234abcd'


class CleanupSafetyTests(unittest.TestCase):
    def test_only_strict_run_ids_become_database_names(self):
        self.assertEqual(runner.database_name(RUN), 'incidentiq_bench_'+RUN)
        for value in ('incidentiq', 'incidentiq_api_test', RUN+';DROP DATABASE incidentiq', '../'+RUN, ''):
            with self.subTest(value=value), self.assertRaises(ValueError):
                runner.database_name(value)

    def test_wrong_ownership_marker_refuses_drop(self):
        with patch.object(runner, 'admin', return_value='unrelated') as sql:
            with self.assertRaises(RuntimeError):
                runner.cleanup(RUN)
            self.assertFalse(any('DROP' in call.args[0] for call in sql.call_args_list))

    def test_active_connections_refuse_drop(self):
        with patch.object(runner, 'admin', side_effect=['incidentiq-benchmark:'+RUN, '1']) as sql:
            with self.assertRaises(RuntimeError):
                runner.cleanup(RUN)
            self.assertFalse(any('DROP' in call.args[0] for call in sql.call_args_list))

    def test_explicit_owned_idle_database_only(self):
        with patch.object(runner, 'admin', side_effect=['incidentiq-benchmark:'+RUN, '0', '']) as sql, patch('builtins.print'):
            runner.cleanup(RUN)
            self.assertEqual(sql.call_args.kwargs, {'db':'incidentiq_bench_'+RUN})
            self.assertIn('DROP DATABASE %I', sql.call_args.args[0])


if __name__=='__main__':
    unittest.main()
