"""
Independent Verification Script for Real G*Power Oracle (`tools/check_independent.py`).

Verifies the authenticity and mathematical accuracy of the values extracted from G*Power 3.1.9.7
in `oracle/gpower_real_vectors.csv` using SciPy (scipy.stats.t, scipy.stats.nct) completely
independent of `src/engine.py` and G*Power itself.
"""

from __future__ import annotations

import csv
import math
import os
import sys

# Clean room rule: Do NOT import src/engine.py!
from scipy.stats import nct, t

ORACLE_CSV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "oracle",
    "gpower_real_vectors.csv",
)

TOLERANCE = 1e-6


def run_independent_checks(csv_path: str = ORACLE_CSV) -> dict:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Oracle CSV not found at {csv_path}")

    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    total_valid = 0
    passed_count = 0
    failed_count = 0
    results_summary = []

    print("=" * 80)
    print("BAĞIMSIZ DOĞRULAMA (SCIPY vs G*POWER 3.1.9.7 KÂHİN)")
    print("=" * 80)
    print(f"{'ID':<8} | {'Mode':<8} | {'Crit t':<10} | {'Power':<10} | {'Apriori Pwr>=Tgt':<16} | {'Sign Note':<20} | {'Status'}")
    print("-" * 80)

    for r in rows:
        vid = r["id"]
        msg = r.get("gpower_message", "").strip()
        n_str = r.get("gpower_n_total", "").strip()

        # Skip invalid / error vectors
        if msg or not n_str:
            continue

        total_valid += 1
        mode = r["mode"]
        tails = int(r["tails"])
        dz = float(r["dz"])
        alpha = float(r["alpha"])
        target_pwr_str = r.get("target_power", "").strip()
        target_pwr = float(target_pwr_str) if target_pwr_str else None

        n = int(n_str)
        df = int(r["gpower_df"])
        gp_crit = float(r["gpower_critical"])
        gp_pwr = float(r["gpower_power"])

        failures = []

        # 1. Independent critical t calculation
        if tails == 2:
            scipy_crit_abs = float(t.ppf(1.0 - alpha / 2.0, df))
        else:
            scipy_crit_abs = float(t.ppf(1.0 - alpha, df))

        diff_crit = abs(abs(gp_crit) - scipy_crit_abs)
        if diff_crit > TOLERANCE:
            failures.append(f"crit t diff: {diff_crit:.2e} (gp={gp_crit}, scipy={scipy_crit_abs})")

        # Sign analysis
        sign_note = "Normal (+)"
        if dz < 0:
            if gp_crit < 0:
                sign_note = "Neg dz -> Neg crit (-)"
            else:
                sign_note = "Neg dz -> Pos crit (+)"
        elif dz == 0:
            sign_note = "Zero dz (null)"

        # 2. Independent power calculation with noncentral t (nct)
        dz_abs = abs(dz)
        delta = dz_abs * math.sqrt(n)

        if delta == 0.0:
            scipy_power = alpha
        else:
            if tails == 2:
                scipy_power = float(nct.sf(scipy_crit_abs, df, delta) + nct.cdf(-scipy_crit_abs, df, delta))
            else:
                scipy_power = float(nct.sf(scipy_crit_abs, df, delta))

        diff_pwr = abs(gp_pwr - scipy_power)
        if diff_pwr > TOLERANCE:
            failures.append(f"power diff: {diff_pwr:.2e} (gp={gp_pwr}, scipy={scipy_power})")

        # 3. Check actual power >= target power in a-priori mode
        apriori_ok = "N/A"
        if mode == "a-priori" and target_pwr is not None:
            if gp_pwr >= (target_pwr - 1e-7):
                apriori_ok = f"OK ({gp_pwr:.4f}>={target_pwr:.4f})"
            else:
                apriori_ok = f"FAIL ({gp_pwr:.4f}<{target_pwr:.4f})"
                failures.append(f"actual power {gp_pwr} < target power {target_pwr}")

        status = "PASS" if not failures else "FAIL"
        if status == "PASS":
            passed_count += 1
        else:
            failed_count += 1

        crit_status = "OK" if diff_crit <= TOLERANCE else "ERR"
        pwr_status = "OK" if diff_pwr <= TOLERANCE else "ERR"

        print(
            f"{vid:<8} | {mode:<8} | {crit_status:<10} | {pwr_status:<10} | {apriori_ok:<16} | {sign_note:<20} | {status}"
        )
        if failures:
            print(f"   -> DETAY: {'; '.join(failures)}")

        results_summary.append({
            "id": vid,
            "status": status,
            "failures": failures,
            "scipy_crit": scipy_crit_abs,
            "gp_crit": gp_crit,
            "scipy_pwr": scipy_power,
            "gp_pwr": gp_pwr,
            "sign_note": sign_note,
        })

    print("-" * 80)
    print("ÖZET:")
    print(f"Toplam Değerlendirilen Geçerli Vektör: {total_valid}")
    print(f"Tam Bağımsız Uyum (PASS):            {passed_count}")
    print(f"Uyuşmazlık (FAIL):                   {failed_count}")
    rate = (passed_count / total_valid * 100.0) if total_valid > 0 else 0.0
    print(f"Bağımsız Doğrulama Başarı Oranı:      %{rate:.2f}")
    print("=" * 80)

    return {
        "total": total_valid,
        "passed": passed_count,
        "failed": failed_count,
        "rate": rate,
        "details": results_summary,
    }


if __name__ == "__main__":
    run_independent_checks()
