"""
Differential Test Suite comparing Engine against Real G*Power Oracle (`tests/test_oracle_real_differential.py`).

Compares outputs from `src.engine.calculate_t_paired` against real values extracted from
G*Power 3.1.9.7 in `oracle/gpower_real_vectors.csv`.
"""

from __future__ import annotations

import csv
import math
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from src.engine import ValidationError, calculate_t_paired

REAL_ORACLE_CSV = os.path.join(ROOT_DIR, "oracle", "gpower_real_vectors.csv")


def count_decimals(val_str: str) -> int:
    val_str = val_str.strip()
    if "." in val_str:
        return len(val_str.split(".")[1])
    return 0


def run_differential_test(csv_path: str = REAL_ORACLE_CSV) -> dict:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Oracle CSV not found at {csv_path}")

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    total_evaluated = 0
    total_passed = 0
    mismatches = []

    for row in reader:
        vec_id = row["id"]
        mode = row["mode"]
        tails = int(row["tails"]) if row["tails"] else 2
        dz = float(row["dz"]) if row["dz"] else None
        alpha = float(row["alpha"]) if row["alpha"] else None
        target_power = float(row["target_power"]) if row.get("target_power") else None
        input_n = int(row["input_n"]) if row.get("input_n") else None

        gp_n = row.get("gpower_n_total", "").strip()
        gp_df = row.get("gpower_df", "").strip()
        gp_crit = row.get("gpower_critical", "").strip()
        gp_ncp = row.get("gpower_ncp", "").strip()
        gp_pwr = row.get("gpower_power", "").strip()
        gp_msg = row.get("gpower_message", "").strip()

        # Skip rows not yet filled in oracle
        if not gp_n and not gp_msg:
            continue

        total_evaluated += 1
        row_passed = True

        # Case 1: G*Power raised an error / modal message
        if gp_msg:
            try:
                res = calculate_t_paired(
                    mode=mode,
                    tails=tails,
                    dz=dz,
                    alpha=alpha,
                    power=target_power,
                    n_total=input_n,
                )
                row_passed = False
                mismatches.append({
                    "id": vec_id,
                    "field": "error_handling",
                    "input": f"mode={mode}, tails={tails}, dz={dz}, alpha={alpha}, power={target_power}, n={input_n}",
                    "gpower_value": f"Error dialog: '{gp_msg}'",
                    "engine_value": f"Success: {res}",
                    "hypothesis": "[AJAN] Motor geçersiz girdiyi doğrulamak yerine sessizce hesaplamaya çalıştı.",
                })
            except (ValidationError, ValueError) as e:
                # Motor also rejected it
                pass
            if row_passed:
                total_passed += 1
            continue

        # Case 2: Normal calculation
        try:
            res = calculate_t_paired(
                mode=mode,
                tails=tails,
                dz=dz,
                alpha=alpha,
                power=target_power,
                n_total=input_n,
            )
        except Exception as e:
            total_evaluated += 1
            mismatches.append({
                "id": vec_id,
                "field": "execution",
                "input": f"mode={mode}, tails={tails}, dz={dz}, alpha={alpha}, power={target_power}, n={input_n}",
                "gpower_value": f"n={gp_n}, df={gp_df}, crit={gp_crit}",
                "engine_value": f"Exception: {e}",
                "hypothesis": "[AJAN] Motor geçerli G*Power girdisinde istisna fırlattı.",
            })
            continue

        # Compare n_total (exact)
        if gp_n != "" and gp_n != "UNREAD":
            expected_n = int(gp_n)
            if res["n_total"] != expected_n:
                row_passed = False
                mismatches.append({
                    "id": vec_id,
                    "field": "n_total",
                    "input": f"mode={mode}, tails={tails}, dz={dz}, alpha={alpha}, power={target_power}",
                    "gpower_value": str(expected_n),
                    "engine_value": str(res["n_total"]),
                    "hypothesis": "[AJAN] Sürekli N kök bulma durma kriteri veya tavan yuvarlama toleransında uyuşmazlık.",
                })

        # Compare df (exact)
        if gp_df != "" and gp_df != "UNREAD":
            expected_df = int(gp_df)
            if res["df"] != expected_df:
                row_passed = False
                mismatches.append({
                    "id": vec_id,
                    "field": "df",
                    "input": f"mode={mode}, tails={tails}, dz={dz}, alpha={alpha}",
                    "gpower_value": str(expected_df),
                    "engine_value": str(res["df"]),
                    "hypothesis": "[AJAN] Serbestlik derecesi (df = N - 1) tanımında veya N hesaplama hatasından kaynaklı fark.",
                })

        # Compare critical t (up to displayed decimals)
        if gp_crit != "" and gp_crit != "UNREAD":
            gp_crit_val = float(gp_crit)
            dec = count_decimals(gp_crit)
            tol = 10 ** (-dec)
            if abs(res["critical"] - gp_crit_val) > tol:
                row_passed = False
                mismatches.append({
                    "id": vec_id,
                    "field": "critical",
                    "input": f"mode={mode}, tails={tails}, dz={dz}, alpha={alpha}",
                    "gpower_value": gp_crit,
                    "engine_value": f"{res['critical']:.{dec}f}",
                    "hypothesis": "[AJAN] Student-t kritik değer ters CDF (ppf) hesaplama yaklaşımı veya işaret kuralı farkı.",
                })

        # Compare ncp (up to displayed decimals)
        if gp_ncp != "" and gp_ncp != "UNREAD":
            gp_ncp_val = float(gp_ncp)
            dec = count_decimals(gp_ncp)
            tol = 10 ** (-dec)
            if abs(res["ncp"] - gp_ncp_val) > tol:
                row_passed = False
                mismatches.append({
                    "id": vec_id,
                    "field": "ncp",
                    "input": f"mode={mode}, tails={tails}, dz={dz}, alpha={alpha}",
                    "gpower_value": gp_ncp,
                    "engine_value": f"{res['ncp']:.{dec}f}",
                    "hypothesis": "[AJAN] Noncentrality parameter delta = dz * sqrt(N) formülünde işaret veya ara duyarlık farkı.",
                })

        # Compare actual_power (up to displayed decimals)
        if gp_pwr != "" and gp_pwr != "UNREAD":
            gp_pwr_val = float(gp_pwr)
            dec = count_decimals(gp_pwr)
            tol = 10 ** (-dec)
            eng_pwr = res.get("actual_power", res.get("power"))
            if abs(eng_pwr - gp_pwr_val) > tol:
                row_passed = False
                mismatches.append({
                    "id": vec_id,
                    "field": "actual_power",
                    "input": f"mode={mode}, tails={tails}, dz={dz}, alpha={alpha}",
                    "gpower_value": gp_pwr,
                    "engine_value": f"{eng_pwr:.{dec}f}",
                    "hypothesis": "[AJAN] Noncentral t kümülatif dağılım fonksiyonu (nct cdf) kuyruk integrasyon duyarlık farkı.",
                })

        if row_passed:
            total_passed += 1

    rate = (total_passed / total_evaluated * 100.0) if total_evaluated > 0 else 0.0

    print("=" * 70)
    print("DİFERANSİYEL TEST RAPORU: KÂHİN (G*POWER 3.1.9.7) vs MOTOR (src.engine)")
    print("=" * 70)
    print(f"Toplam Değerlendirilen Vektör: {total_evaluated}")
    print(f"Birebir Uyum Sağlanan Vektör: {total_passed}")
    print(f"Uyum Oranı: %{rate:.2f}")
    print("-" * 70)

    if mismatches:
        print("UYUŞMAZLIKLAR:")
        for m in mismatches:
            print(f"- [{m['id']}] Alan: {m['field']}")
            print(f"  Girdi:        {m['input']}")
            print(f"  G*Power:      {m['gpower_value']}")
            print(f"  Bizim Motor:  {m['engine_value']}")
            print(f"  Hipotez:      {m['hypothesis']}")
            print()
    else:
        print("Hiçbir uyuşmazlık bulunamadı! Tüm değerler tam tolerans sınırları içinde eşleşti.")

    return {
        "total": total_evaluated,
        "passed": total_passed,
        "rate": rate,
        "mismatches": mismatches,
    }


if __name__ == "__main__":
    run_differential_test()
