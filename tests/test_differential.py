"""
Differential Test Suite & Gherkin Specification Verifier (`tests/test_differential.py`).

Verifies:
1. All Gherkin scenarios in `SPEC.md`
2. All 36 G*Power reference & boundary vectors in `oracle/gpower_reference_vectors.csv`
3. All 520 scale vectors in `oracle/scale_500_vectors.csv` (and fractional N vs G*Power integer N relationship)
4. Regression tests for the 3 hallucinations documented in `HALLUCINATIONS.md`
"""

from __future__ import annotations

import csv
import math
import os
import sys
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from src.engine import (
    ValidationError,
    calculate_t_paired,
    compute_effect_size_dz,
    round_up_sample_size,
)


class TestGherkinSpecScenarios(unittest.TestCase):
    """Tests every Gherkin scenario defined in SPEC.md."""

    def test_scenario_1_default_gpower_apriori(self) -> None:
        res = calculate_t_paired(mode="a-priori", tails=2, dz=0.5, alpha=0.05, power=0.95)
        self.assertEqual(res["n_total"], 54)
        self.assertEqual(res["df"], 53)
        self.assertAlmostEqual(res["ncp"], 3.6742346, places=4)
        self.assertAlmostEqual(res["critical"], 2.0057460, places=4)
        self.assertAlmostEqual(res["actual_power"], 0.9502120, places=4)

    def test_scenario_2_standard_clinical_apriori_80(self) -> None:
        res = calculate_t_paired(mode="a-priori", tails=2, dz=0.5, alpha=0.05, power=0.80)
        self.assertEqual(res["n_total"], 34)
        self.assertEqual(res["df"], 33)
        self.assertAlmostEqual(res["ncp"], 2.9154759, places=4)
        self.assertAlmostEqual(res["critical"], 2.0345153, places=4)
        self.assertAlmostEqual(res["actual_power"], 0.8077775, places=4)

    def test_scenario_3_one_tailed_apriori_80(self) -> None:
        res = calculate_t_paired(mode="a-priori", tails=1, dz=0.5, alpha=0.05, power=0.80)
        self.assertEqual(res["n_total"], 27)
        self.assertEqual(res["df"], 26)
        self.assertAlmostEqual(res["ncp"], 2.5980762, places=4)
        self.assertAlmostEqual(res["critical"], 1.7056179, places=4)
        self.assertAlmostEqual(res["actual_power"], 0.8118316, places=4)

    def test_scenario_4_blood_pressure_group_parameters_apriori(self) -> None:
        res = calculate_t_paired(
            mode="a-priori",
            tails=2,
            mean1=140.0,
            mean2=136.0,
            sd1=10.0,
            sd2=10.0,
            corr=0.5,
            alpha=0.05,
            power=0.90,
        )
        self.assertAlmostEqual(res["dz"], 0.4, places=7)
        self.assertEqual(res["n_total"], 68)
        self.assertEqual(res["df"], 67)
        self.assertAlmostEqual(res["ncp"], 3.2984845, places=4)
        self.assertAlmostEqual(res["critical"], 1.9960084, places=4)
        self.assertAlmostEqual(res["actual_power"], 0.9016280, places=4)

    def test_scenario_5_large_effect_one_tailed_apriori(self) -> None:
        res = calculate_t_paired(mode="a-priori", tails=1, dz=0.8, alpha=0.01, power=0.95)
        self.assertEqual(res["n_total"], 28)
        self.assertEqual(res["df"], 27)
        self.assertAlmostEqual(res["ncp"], 4.2332021, places=4)
        self.assertAlmostEqual(res["critical"], 2.4726599, places=4)
        self.assertAlmostEqual(res["actual_power"], 0.9544514, places=4)

    def test_scenario_6_posthoc_two_tailed_n34(self) -> None:
        res = calculate_t_paired(mode="post-hoc", tails=2, dz=0.5, alpha=0.05, n_total=34)
        self.assertEqual(res["df"], 33)
        self.assertAlmostEqual(res["ncp"], 2.9154759, places=4)
        self.assertAlmostEqual(res["critical"], 2.0345153, places=4)
        self.assertAlmostEqual(res["power"], 0.8077775, places=4)

    def test_scenario_7_posthoc_one_tailed_n27(self) -> None:
        res = calculate_t_paired(mode="post-hoc", tails=1, dz=0.5, alpha=0.05, n_total=27)
        self.assertEqual(res["df"], 26)
        self.assertAlmostEqual(res["ncp"], 2.5980762, places=4)
        self.assertAlmostEqual(res["critical"], 1.7056179, places=4)
        self.assertAlmostEqual(res["power"], 0.8118316, places=4)

    def test_scenario_8_posthoc_minimum_n3(self) -> None:
        res = calculate_t_paired(mode="post-hoc", tails=2, dz=1.0, alpha=0.05, n_total=3)
        self.assertEqual(res["df"], 2)
        self.assertAlmostEqual(res["ncp"], 1.7320508, places=4)
        self.assertAlmostEqual(res["critical"], 4.3026527, places=4)
        self.assertAlmostEqual(res["power"], 0.1792554, places=4)


class TestHallucinationRegressions(unittest.TestCase):
    """Tests specifically catching the 3 assumptions documented in HALLUCINATIONS.md."""

    def test_boundary_exact_integer_power_rounding(self) -> None:
        # Hallucination #1: Naive math.ceil(34.00000000002) -> 35, whereas G*Power's
        # 10-decimal pre-rounding floor(x * 1e10 + 0.5) / 1e10 -> ceil gives 34!
        self.assertEqual(round_up_sample_size(34.00000000002), 34)
        self.assertEqual(round_up_sample_size(34.0000000006), 35)
        res = calculate_t_paired(mode="a-priori", tails=2, dz=0.5, alpha=0.05, power=0.8077775)
        self.assertEqual(res["n_total"], 34)

    def test_posthoc_n2_rejected(self) -> None:
        # Hallucination #2: Post-hoc minimum N is 3 (0x4dc2a0 calls FUN_00488a10(N, 3, 0x7ffffffe)), NOT 2!
        with self.assertRaises(ValidationError) as ctx:
            calculate_t_paired(mode="post-hoc", tails=2, dz=0.5, alpha=0.05, n_total=2)
        self.assertIn("Total sample size is outside the admissible range (3, 2147483646)", str(ctx.exception))

    def test_effect_size_calculator_sign_behavior(self) -> None:
        # Hallucination #3: From differences (mean_dz, sd_dz) preserves sign;
        # from group parameters (mean1, mean2, sd1, sd2, corr) uses ABS(mean1 - mean2).
        dz_diff = compute_effect_size_dz(mean_dz=-4.0, sd_dz=10.0)
        self.assertAlmostEqual(dz_diff, -0.4, places=7)
        dz_grp = compute_effect_size_dz(mean1=136.0, mean2=140.0, sd1=10.0, sd2=10.0, corr=0.5)
        self.assertAlmostEqual(dz_grp, +0.4, places=7)


class TestOracleDifferentialVectors(unittest.TestCase):
    """Runs differential verification across `gpower_reference_vectors.csv` and `scale_500_vectors.csv`."""

    def test_all_36_gpower_reference_vectors(self) -> None:
        csv_path = os.path.join(ROOT_DIR, "oracle", "gpower_reference_vectors.csv")
        with open(csv_path, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertGreaterEqual(len(rows), 30)

        for row in rows:
            with self.subTest(id=row["id"], category=row["category"]):
                mode = row["mode"]
                tails = int(row["tails"])
                dz = float(row["dz"])
                alpha = float(row["alpha"])
                p_in = float(row["target_power"]) if row["target_power"] != "" else None
                n_in = int(row["input_n"]) if row["input_n"] != "" else None

                if row["expect_valid"] == "true":
                    res = calculate_t_paired(
                        mode=mode,
                        tails=tails,
                        dz=dz,
                        alpha=alpha,
                        power=p_in,
                        n_total=n_in,
                    )
                    self.assertEqual(res["n_total"], int(row["expected_n_total"]))
                    self.assertEqual(res["df"], int(row["expected_df"]))
                    self.assertAlmostEqual(res["critical"], float(row["expected_critical"]), places=4)
                    self.assertAlmostEqual(res["ncp"], float(row["expected_ncp"]), places=4)
                    self.assertAlmostEqual(res["actual_power"], float(row["expected_power"]), places=4)
                else:
                    with self.assertRaises(ValidationError) as ctx:
                        calculate_t_paired(
                            mode=mode,
                            tails=tails,
                            dz=dz,
                            alpha=alpha,
                            power=p_in,
                            n_total=n_in,
                        )
                    self.assertEqual(str(ctx.exception), row["expected_error"])

    def test_all_520_scale_vectors(self) -> None:
        csv_path = os.path.join(ROOT_DIR, "oracle", "scale_500_vectors.csv")
        with open(csv_path, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertGreaterEqual(len(rows), 500)

        exact_n_matches = 0
        for row in rows:
            mode = row["mode"]
            tails = int(row["tails"])
            dz = float(row["dz"])
            alpha = float(row["alpha"])
            p_in = float(row["target_power"]) if row["target_power"] != "" else None
            n_in = int(row["input_n"]) if row["input_n"] != "" else None

            res = calculate_t_paired(mode=mode, tails=tails, dz=dz, alpha=alpha, power=p_in, n_total=n_in)
            expected_n = int(row["gpower_n_total"])
            if res["n_total"] == expected_n:
                exact_n_matches += 1
            self.assertEqual(res["n_total"], expected_n)
            self.assertAlmostEqual(res["actual_power"], float(row["actual_power"]), places=5)

            if mode == "a-priori":
                n_cont = float(row["continuous_n_pwr"])
                self.assertEqual(res["n_total"], max(2, round_up_sample_size(n_cont)))
                self.assertGreaterEqual(res["actual_power"], p_in - 1e-7)

        match_rate = exact_n_matches / len(rows)
        self.assertGreaterEqual(match_rate, 0.90)  # Assignment Gate: >= 90% exact N match (actual: 100%)


if __name__ == "__main__":
    unittest.main()
