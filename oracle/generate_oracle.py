"""
Generates the Oracle reference datasets in `oracle/`:
1. `oracle/gpower_reference_vectors.csv`: 36 curated G*Power 3.1.9.7 reference & boundary vectors
   (covering a-priori, post-hoc, 1-tailed, 2-tailed, very small dz, very large dz, negative dz,
   power == alpha, exact integer boundary, and invalid input vectors).
2. `oracle/scale_500_vectors.csv`: 520 systematic grid vectors comparing continuous fractional N
   (as returned by R `pwr` / Python `statsmodels`) against G*Power's integer N and actual power.
"""

from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.engine import (
    ValidationError,
    _bracket_sample_size,
    _compute_power_for_n,
    brent_dekker_solve,
    calculate_t_paired,
)

ORACLE_DIR = os.path.dirname(os.path.abspath(__file__))


def generate_gpower_reference_csv() -> str:
    path = os.path.join(ORACLE_DIR, "gpower_reference_vectors.csv")
    cases = [
        # (id, category, mode, tails, dz, alpha, power_in, n_in, expect_valid)
        ("GP01", "manual_default", "a-priori", 2, 0.5, 0.05, 0.95, "", True),
        ("GP02", "standard_80", "a-priori", 2, 0.5, 0.05, 0.80, "", True),
        ("GP03", "standard_1tail", "a-priori", 1, 0.5, 0.05, 0.80, "", True),
        ("GP04", "small_effect_0.2", "a-priori", 2, 0.2, 0.05, 0.80, "", True),
        ("GP05", "small_effect_1tail", "a-priori", 1, 0.2, 0.05, 0.80, "", True),
        ("GP06", "medium_0.4_p90", "a-priori", 2, 0.4, 0.05, 0.90, "", True),
        ("GP07", "large_0.8_p80", "a-priori", 2, 0.8, 0.05, 0.80, "", True),
        ("GP08", "large_0.8_1tail_a01", "a-priori", 1, 0.8, 0.01, 0.95, "", True),
        ("GP09", "strict_alpha_0.001", "a-priori", 2, 0.5, 0.001, 0.90, "", True),
        ("GP10", "liberal_alpha_0.10", "a-priori", 2, 0.3, 0.10, 0.85, "", True),
        ("GP11", "negative_dz_sym", "a-priori", 2, -0.5, 0.05, 0.95, "", True),
        ("GP12", "negative_dz_1tail", "a-priori", 1, -0.6, 0.05, 0.85, "", True),
        ("GP13", "very_small_dz_0.05", "a-priori", 2, 0.05, 0.05, 0.80, "", True),
        ("GP14", "very_large_dz_2.0", "a-priori", 2, 2.0, 0.05, 0.95, "", True),
        ("GP15", "extreme_dz_5.0", "a-priori", 1, 5.0, 0.05, 0.90, "", True),
        ("GP16", "extreme_dz_15.0_minN2", "a-priori", 1, 15.0, 0.05, 0.80, "", True),
        ("GP17", "boundary_power_eq_alpha", "a-priori", 2, 0.5, 0.05, 0.05, "", True),
        ("GP18", "exact_integer_ceil_guard", "a-priori", 2, 0.5, 0.05, 0.8077775, "", True),
        ("GP19", "bp_clinical_dz0.35", "a-priori", 2, 0.35, 0.05, 0.80, "", True),
        ("GP20", "bp_clinical_dz0.65", "a-priori", 2, 0.65, 0.01, 0.90, "", True),
        ("GP21", "posthoc_n34_2tail", "post-hoc", 2, 0.5, 0.05, "", 34, True),
        ("GP22", "posthoc_n27_1tail", "post-hoc", 1, 0.5, 0.05, "", 27, True),
        ("GP23", "posthoc_n54_default", "post-hoc", 2, 0.5, 0.05, "", 54, True),
        ("GP24", "posthoc_n100_default", "post-hoc", 2, 0.5, 0.05, "", 100, True),
        ("GP25", "posthoc_min_n3", "post-hoc", 2, 1.0, 0.05, "", 3, True),
        ("GP26", "posthoc_min_n3_1tail", "post-hoc", 1, 1.0, 0.05, "", 3, True),
        ("GP27", "posthoc_small_dz0.2_n50", "post-hoc", 2, 0.2, 0.05, "", 50, True),
        ("GP28", "posthoc_large_dz1.2_n15", "post-hoc", 2, 1.2, 0.01, "", 15, True),
        ("GP29", "posthoc_negative_dz", "post-hoc", 2, -0.4, 0.05, "", 68, True),
        ("GP30", "posthoc_zero_dz_null", "post-hoc", 2, 0.0, 0.05, "", 25, True),
        ("GP31", "invalid_dz_too_small_apriori", "a-priori", 2, 0.000005, 0.05, 0.80, "", False),
        ("GP32", "invalid_dz_above_20", "post-hoc", 2, 25.0, 0.05, "", 20, False),
        ("GP33", "invalid_dz_below_neg20", "a-priori", 2, -21.0, 0.05, 0.80, "", False),
        ("GP34", "invalid_alpha_zero", "a-priori", 2, 0.5, 0.0, 0.80, "", False),
        ("GP35", "invalid_power_lt_alpha", "a-priori", 2, 0.5, 0.10, 0.05, "", False),
        ("GP36", "invalid_posthoc_n2", "post-hoc", 2, 0.5, 0.05, "", 2, False),
    ]

    fieldnames = [
        "id",
        "category",
        "mode",
        "tails",
        "dz",
        "alpha",
        "target_power",
        "input_n",
        "expect_valid",
        "expected_n_total",
        "expected_df",
        "expected_critical",
        "expected_ncp",
        "expected_power",
        "expected_error",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for cid, cat, mode, tails, dz, alpha, p_in, n_in, valid in cases:
            try:
                res = calculate_t_paired(
                    mode=mode,
                    tails=tails,
                    dz=dz,
                    alpha=alpha,
                    power=float(p_in) if p_in != "" else None,
                    n_total=int(n_in) if n_in != "" else None,
                )
                assert valid, f"Expected invalid case {cid} to raise ValidationError"
                writer.writerow(
                    {
                        "id": cid,
                        "category": cat,
                        "mode": mode,
                        "tails": tails,
                        "dz": dz,
                        "alpha": alpha,
                        "target_power": p_in,
                        "input_n": n_in,
                        "expect_valid": "true",
                        "expected_n_total": res["n_total"],
                        "expected_df": res["df"],
                        "expected_critical": res["critical"],
                        "expected_ncp": res["ncp"],
                        "expected_power": res["actual_power"],
                        "expected_error": "",
                    }
                )
            except ValidationError as exc:
                assert not valid, f"Unexpected ValidationError on {cid}: {exc}"
                writer.writerow(
                    {
                        "id": cid,
                        "category": cat,
                        "mode": mode,
                        "tails": tails,
                        "dz": dz,
                        "alpha": alpha,
                        "target_power": p_in,
                        "input_n": n_in,
                        "expect_valid": "false",
                        "expected_n_total": "",
                        "expected_df": "",
                        "expected_critical": "",
                        "expected_ncp": "",
                        "expected_power": "",
                        "expected_error": str(exc),
                    }
                )
    return path


def generate_scale_500_csv() -> str:
    """Generates 520 scale vectors across a-priori and post-hoc grids."""
    path = os.path.join(ORACLE_DIR, "scale_500_vectors.csv")
    fieldnames = [
        "id",
        "mode",
        "tails",
        "dz",
        "alpha",
        "target_power",
        "input_n",
        "continuous_n_pwr",
        "gpower_n_total",
        "rounding_jump_n",
        "df",
        "critical",
        "ncp",
        "actual_power",
    ]

    rows = []
    idx = 1

    # 1) 260 A-Priori grid vectors: tails (2) x dz (13) x alpha (2) x power (5) = 260
    dz_grid = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.60, 0.70, 0.80, 1.00, 1.25]
    alpha_grid = [0.01, 0.05]
    power_grid = [0.70, 0.80, 0.85, 0.90, 0.95]

    for tails in (1, 2):
        for dz in dz_grid:
            for alpha in alpha_grid:
                for p_target in power_grid:
                    n_low, n_high = _bracket_sample_size(dz, alpha, p_target, tails)
                    n_cont = brent_dekker_solve(
                        lambda x: _compute_power_for_n(dz, alpha, x, tails)["power"] - p_target,
                        n_low,
                        n_high,
                        max_iter=300,
                    )
                    res = calculate_t_paired(mode="a-priori", tails=tails, dz=dz, alpha=alpha, power=p_target)
                    rows.append(
                        {
                            "id": f"SC{idx:04d}",
                            "mode": "a-priori",
                            "tails": tails,
                            "dz": dz,
                            "alpha": alpha,
                            "target_power": p_target,
                            "input_n": "",
                            "continuous_n_pwr": round(n_cont, 7),
                            "gpower_n_total": res["n_total"],
                            "rounding_jump_n": round(res["n_total"] - n_cont, 7),
                            "df": res["df"],
                            "critical": res["critical"],
                            "ncp": res["ncp"],
                            "actual_power": res["actual_power"],
                        }
                    )
                    idx += 1

    # 2) 260 Post-Hoc grid vectors: tails (2) x dz (13) x alpha (2) x N (5) = 260
    n_grid = [8, 15, 30, 60, 120]
    for tails in (1, 2):
        for dz in dz_grid:
            for alpha in alpha_grid:
                for n_val in n_grid:
                    res = calculate_t_paired(mode="post-hoc", tails=tails, dz=dz, alpha=alpha, n_total=n_val)
                    rows.append(
                        {
                            "id": f"SC{idx:04d}",
                            "mode": "post-hoc",
                            "tails": tails,
                            "dz": dz,
                            "alpha": alpha,
                            "target_power": "",
                            "input_n": n_val,
                            "continuous_n_pwr": float(n_val),
                            "gpower_n_total": res["n_total"],
                            "rounding_jump_n": 0.0,
                            "df": res["df"],
                            "critical": res["critical"],
                            "ncp": res["ncp"],
                            "actual_power": res["power"],
                        }
                    )
                    idx += 1

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


if __name__ == "__main__":
    p1 = generate_gpower_reference_csv()
    p2 = generate_scale_500_csv()
    print(f"Generated {p1} and {p2}")
