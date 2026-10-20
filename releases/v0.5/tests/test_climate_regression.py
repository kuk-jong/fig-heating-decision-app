"""Numerical regression and CSV integration tests; no Streamlit server required."""
import ast
from io import StringIO
from pathlib import Path
import unittest
import math
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "original_app.py"
# Load calculation definitions without executing the Streamlit UI.
ns = {"np": np, "pd": pd, "math": math}
tree = ast.parse(APP.read_text(encoding="utf-8"))
nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) or (isinstance(n, ast.Assign) and all(isinstance(t, ast.Name) for t in n.targets))]
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(APP), "exec"), ns)


def csv_file(dates, temperatures, region="해남군"):
    return StringIO(pd.DataFrame({"region": region, "date": dates, "min_temp": temperatures}).to_csv(index=False))


class ClimateRegressionTests(unittest.TestCase):
    def setUp(self):
        self.dates = pd.date_range("2022-01-01", "2024-12-31")
        self.truth = {"A": 11.0, "B": 12.0, "C": ns["ANGULAR_FREQUENCY"], "D": -1.8}
        self.temps = np.array([ns["simulated_min_temp"](self.truth, d) for d in self.dates])

    def test_recovers_center_amplitude_phase_and_constant_period(self):
        fit = ns["fit_climate_curve"](self.dates, self.temps)
        for k in self.truth:
            self.assertAlmostEqual(fit[k], self.truth[k], places=10)
        self.assertLess(fit["rmse"], 1e-10)

    def test_winter_only_fit_preserves_observed_mean_without_double_cooling(self):
        dates = pd.date_range("2025-11-01", "2026-02-28")
        y = np.array([ns["simulated_min_temp"](self.truth, d) for d in dates])
        y += np.random.default_rng(7).normal(0, 0.4, len(y))
        fit = ns["fit_climate_curve"](dates, y)
        fitted = np.array([ns["simulated_min_temp"](fit, d) for d in dates])
        self.assertAlmostEqual(float(y.mean()), float(fitted.mean()), places=10)
        self.assertGreater(fit["A"], float(y.mean()) + 1)

    def test_csv_uses_all_seasons_and_can_be_read_repeatedly(self):
        f = csv_file(self.dates, self.temps)
        for _ in range(2):
            fit, error = ns["climate_params_from_csv"](f, "해남군")
            self.assertIsNone(error)
            self.assertEqual(fit["months"], 12)
            self.assertEqual(fit["rows"], len(self.dates))
            self.assertAlmostEqual(fit["A"], 11.0, places=10)

    def test_invalid_rows_and_duplicate_dates(self):
        dates = list(self.dates[:365].strftime("%Y-%m-%d"))
        y = list(self.temps[:365])
        f = csv_file(dates + [dates[0], "bad", dates[1]], y + [y[0], 1.0, float("inf")])
        fit, error = ns["climate_params_from_csv"](f, "해남군")
        self.assertIsNone(error)
        self.assertEqual(fit["rows"], 365)
        self.assertEqual(fit["dropped_rows"], 2)
        self.assertEqual(fit["duplicate_rows"], 1)

    def test_invalid_data_returns_errors(self):
        samples = [StringIO("date,min_temp\n2025-01-01,0"),
                   csv_file(["2025-01-01"], [0]),
                   csv_file(pd.date_range("2025-01-01", periods=5), [1, 2, 3, 4, 5]),
                   csv_file(["bad"], [float("nan")])]
        for f in samples:
            model, error = ns["climate_params_from_csv"](f, "해남군")
            self.assertIsNone(model)
            self.assertTrue(error)
        self.assertIsNone(ns["climate_params_from_csv"](csv_file(self.dates, self.temps), "없는지역")[0])

    def test_constant_temperature_and_leap_year(self):
        fit = ns["fit_climate_curve"](self.dates, np.full(len(self.dates), 3.0))
        self.assertEqual(fit["B"], 0.0)
        self.assertEqual(fit["D"], 0.0)
        self.assertIsNone(fit["r_squared"])
        self.assertTrue(np.isfinite(ns["simulated_min_temp"](fit, "2024-02-29")))
        self.assertEqual(ns["climate_day"]("2024-01-01"), ns["climate_day"]("2025-01-01"))

    def test_heating_cost_uses_regressed_curve(self):
        args = dict(surface_area=100, u_val=2, target_temp=10, unit_fuel_cost=1100,
                    energy_source="면세유(경유)", climate_model=self.truth,
                    winter_total_yield=635, market_price=30000,
                    airtightness_factor=1, side_wing_factor_value=1)
        _, cost, hours = ns["winter_analysis"](**args)
        dates = pd.date_range(ns["WINTER_START"], ns["WINTER_END"])
        delta = np.maximum(10 - np.array([ns["simulated_min_temp"](self.truth, d) for d in dates]), 0)
        expected = int(float(np.sum(100 * 2 * delta * 14 / (8500 * .85) * 1100)))
        self.assertEqual(cost, expected)
        self.assertAlmostEqual(hours, float(np.mean(delta > 0) * 14))
        args["climate_model"] = {**self.truth, "A": self.truth["A"] + 3}
        self.assertLess(ns["winter_analysis"](**args)[1], cost)

    def test_defaults_are_labeled_and_use_fixed_period(self):
        for data in ns["REGION_DATA"].values():
            model = ns["default_climate_model"](data)
            self.assertEqual(model["source"], "legacy_assumptions")
            self.assertEqual(model["C"], ns["ANGULAR_FREQUENCY"])
            self.assertGreaterEqual(model["B"], 0)


if __name__ == "__main__":
    unittest.main()
