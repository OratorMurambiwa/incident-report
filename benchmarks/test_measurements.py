import unittest
from measurements import percentile, summarize


class MeasurementTests(unittest.TestCase):
    def test_interpolated_tail_percentiles(self):
        self.assertAlmostEqual(percentile([10, 20, 30, 40], 95), 38.5)
        self.assertAlmostEqual(percentile([10, 20, 30, 40], 99), 39.7)

    def test_unsorted_samples_and_endpoints(self):
        self.assertEqual(percentile([30, 10, 20], 0), 10)
        self.assertEqual(percentile([30, 10, 20], 100), 30)
        self.assertEqual(percentile([15], 99), 15)

    def test_mean_and_units(self):
        self.assertEqual(summarize([10, 20, 30])['avg_ms'], 20)

    def test_invalid_measurements_rejected(self):
        for values, quantile in [([],95), ([1],101), ([1],-1), ([float('nan')],95), ([-1],95)]:
            with self.subTest(values=values, quantile=quantile), self.assertRaises(ValueError):
                percentile(values,quantile)


if __name__ == '__main__':
    unittest.main()
