"""CLI and fit checks using synthetic front positions, without simulation files."""

import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# Only the yt reader is substituted when yt is unavailable. These tests do not
# exercise real simulation loading; they verify the fit, units, and terminal CLI.
if importlib.util.find_spec("yt") is None:
    sys.modules["yt"] = types.SimpleNamespace(set_log_level=lambda level: None)

import BurnRate
import BurnRateTerminal


class TerminalTests(unittest.TestCase):
    def test_fit_and_inches_conversion(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for index in (0, 1, 2):
                (folder / f"{index}cell").mkdir()
            def synthetic_front(path):
                time = int(path.name.replace("cell", ""))
                return time, 0.1 - 0.0254 * time
            with patch.object(BurnRate, "front_position", side_effect=synthetic_front):
                _, meters, inches, samples = BurnRate.calculate_burn_rate(folder)
            self.assertAlmostEqual(meters, 0.0254)
            self.assertAlmostEqual(inches, 1)
            self.assertEqual(samples, 3)

    def test_terminal_outputs_units_without_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            output = io.StringIO()
            with patch.object(sys, "argv", ["BurnRateTerminal.py", directory]), \
                 patch.object(BurnRateTerminal, "calculate_burn_rate",
                              return_value=(Path(directory), 0.0254, 1, 3)), \
                 patch.object(BurnRate, "append_result") as save, \
                 contextlib.redirect_stdout(output):
                self.assertEqual(BurnRateTerminal.main(), 0)
            self.assertIn("Burn rate: 0.0254 m/s", output.getvalue())
            self.assertIn("Burn rate: 1 in/s", output.getvalue())
            save.assert_not_called()
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_failure_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(sys, "argv", ["BurnRateTerminal.py", directory]), \
                 patch.object(BurnRateTerminal, "calculate_burn_rate",
                              side_effect=RuntimeError("No front found")), \
                 contextlib.redirect_stderr(io.StringIO()) as output:
                self.assertEqual(BurnRateTerminal.main(), 1)
            self.assertIn("No front found", output.getvalue())


if __name__ == "__main__":
    unittest.main()
