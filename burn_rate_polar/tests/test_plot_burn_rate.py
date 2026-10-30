import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from plot_burn_rate import angle_from_normal, group_conditions, load_measurements


class OrientationTests(unittest.TestCase):
    def test_known_directions_and_scaling(self):
        for vector, angle in [([1, 0, 0], 0), ([1, 1, 0], 45),
                              ([1, 1, 1], 54.735610317), ([0, 1, 0], 90),
                              ([-1, 0, 0], 180), ([10, 10, 0], 45)]:
            self.assertAlmostEqual(np.degrees(angle_from_normal(vector)), angle, places=6)
        self.assertAlmostEqual(angle_from_normal([0, 2, 0], [0, 1, 0]), 0)

    def test_invalid_vectors(self):
        for vector in ([0, 0, 0], [1, 2], [np.nan, 0, 0]):
            with self.assertRaises(ValueError):
                angle_from_normal(vector)

    def test_example_groups_keep_conditions_separate(self):
        path = Path(__file__).resolve().parents[1] / "examples" / "comparison.csv"
        groups = group_conditions(load_measurements(path))
        self.assertEqual(set(groups), {(100, 2), (200, 4)})
        for rows in groups.values():
            self.assertEqual({row.source for row in rows}, {"experiment", "simulation"})
        self.assertTrue(any(row.error is None for rows in groups.values() for row in rows))

    def test_validation_reports_csv_line(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text("source,u,v,w,heat_flux_kw_m2,cutoff_s,burn_rate_mm_s\n"
                            "experiment,0,0,0,100,2,3\n")
            with self.assertRaisesRegex(ValueError, "line 2"):
                load_measurements(path)


if __name__ == "__main__":
    unittest.main()
