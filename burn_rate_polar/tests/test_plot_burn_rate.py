import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from plot_burn_rate import angle_from_normal, group_conditions, load_measurements, parse_face


class OrientationTests(unittest.TestCase):
    def test_face_formats(self):
        for text, expected in [("100", (1, 0, 0)), ("(110)", (1, 1, 0)),
                               ("010", (0, 1, 0)), ("(1,-1,0)", (1, -1, 0)),
                               ("[10 1 0]", (10, 1, 0))]:
            self.assertEqual(parse_face(text), expected)
        for text in ("000", "10", "1010", "abc"):
            with self.assertRaises(ValueError):
                parse_face(text)

    def test_simple_format_keeps_both_sources_in_one_plot(self):
        path = Path(__file__).resolve().parents[1] / "examples" / "faces.csv"
        measurements = load_measurements(path)
        self.assertEqual(len(measurements), 10)
        self.assertEqual(set(group_conditions(measurements)), {(None, None)})
        self.assertEqual(measurements[-1].vector, (0, 1, 0))
        self.assertEqual(measurements[0].rate, 2.0)
        self.assertEqual(measurements[1].rate, 2.1)

    def test_simple_missing_rate_and_quoted_face(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "faces.csv"
            path.write_text('face,experimental_burn_rate,simulated_burn_rate\n'
                            '"(1,-1,0)",,2.5\n')
            rows = load_measurements(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].source, "simulation")
            self.assertEqual(rows[0].vector, (1, -1, 0))

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
