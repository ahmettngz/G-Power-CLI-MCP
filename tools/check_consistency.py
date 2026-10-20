import csv, math

rows = list(csv.DictReader(open("oracle/gpower_real_vectors.csv", encoding="utf-8")))
bad = 0
checked = 0
prev = None

for r in rows:
    id_ = r["id"]
    n = r.get("gpower_n_total", "").strip()
    df = r.get("gpower_df", "").strip()
    ncp = r.get("gpower_ncp", "").strip()
    dz = r.get("dz", "").strip()

    if not n or not n.lstrip("-").isdigit():
        print(f"{id_}: boş/okunamadı -> n_total={n!r}, message={r.get('gpower_message','')[:50]!r}")
        continue

    checked += 1
    n_i = int(n)
    problems = []
    if df and int(float(df)) != n_i - 1:
        problems.append(f"df={df} ama N-1={n_i-1}")
    if ncp and dz:
        expected = abs(float(dz)) * math.sqrt(n_i)
        if abs(abs(float(ncp)) - expected) > 1e-5:
            problems.append(f"ncp={ncp} ama dz*sqrt(N)={expected:.7f}")
    if r["mode"] == "post-hoc" and r.get("input_n") and int(float(r["input_n"])) != n_i:
        problems.append(f"post-hoc: input_n={r['input_n']} ama ekranda N={n_i}")

    sig = (n, df, ncp, r.get("gpower_critical"), r.get("gpower_power"))
    if prev == sig:
        problems.append("bir önceki satırla AYNI çıktı (bayat okuma şüphesi)")
    prev = sig

    if problems:
        bad += 1
        print(f"{id_} PROBLEM:", "; ".join(problems))

print(f"\nKontrol edilen: {checked}, problemli: {bad}")