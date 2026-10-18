# GİRDİ / ÇIKTI VE ARAÇ SÖZLEŞMESİ (`CONTRACT.md`)

Bu belge; **CLI (`gpower-clone`)**, **MCP Sunucusu (`gpower-mcp`)**, **REST API (`gpower-api`)** ve **Klinik AI Ajanı (`gpower-agent`)** katmanlarının ortak girdi/çıktı sözleşmesini tanımlar.

---

## 1. CLI Sözleşmesi (`gpower-clone`)

### 1.1 Örnek Çağrılar

```bash
# 1. A-Priori Mod (Örneklem Büyüklüğü N Hesaplama)
gpower-clone --test t-paired --mode a-priori --tails 2 --dz 0.5 --alpha 0.05 --power 0.95

# (--d parametresi --dz ile eş anlamlı olarak da kabul edilir)
gpower-clone --test t-paired --mode a-priori --tails 2 --d 0.5 --alpha 0.05 --power 0.95

# 2. Post-Hoc Mod (Ulaşılan İstatistiksel Güç Hesaplama)
gpower-clone --test t-paired --mode post-hoc --tails 2 --dz 0.5 --alpha 0.05 --n 34

# 3. Önce ve Sonra Tansiyon Grup Parametrelerinden (mean1, mean2, sd1, sd2, corr) Hesaplama
gpower-clone --test t-paired --mode a-priori --tails 2 --mean1 140 --mean2 136 --sd1 10 --sd2 10 --corr 0.5 --alpha 0.05 --power 0.90
```

### 1.2 Başarılı Çıktı (Tek Satır JSON, Çıkış Kodu `0`)

- **A-Priori Mod Çıktısı:**
  ```json
  {"test":"t-paired","mode":"a-priori","tails":2,"dz":0.5,"alpha":0.05,"n_total":54,"actual_power":0.950212,"power":0.950212,"critical":2.005746,"df":53,"ncp":3.6742346}
  ```
- **Post-Hoc Mod Çıktısı:**
  ```json
  {"test":"t-paired","mode":"post-hoc","tails":2,"dz":0.5,"alpha":0.05,"n_total":34,"power":0.8077775,"actual_power":0.8077775,"critical":2.0345153,"df":33,"ncp":2.9154759}
  ```

### 1.3 Geçersiz Girdi Çıktısı (Tek Satır JSON, Çıkış Kodu `1`)

```json
{"error":"In an a priori analysis, the absolute value of the effect size be greater than 0.00001."}
```

---

## 2. MCP Sunucusu Araç Şeması (`src/mcp_server.py`)

MCP sunucusu (`stdio` üzerinden JSON-RPC 2.0) hesap mantığını kopyalamaz; doğrudan `src.engine` modülünü çağırır. Sunulan araçlar:

1. **`gpower_t_paired`:**
   - **Açıklama:** Eşleştirilmiş örneklem t-testi (`t-paired`) için `a-priori` (örneklem büyüklüğü $N$) veya `post-hoc` (ulaşılan güç) analizi yapar.
   - **Girdi Şeması (`inputSchema`):**
     - `mode` (`"a-priori"` | `"post-hoc"`, zorunlu)
     - `tails` (`1` | `2`, varsayılan: `2`)
     - `dz` (`number`, opsiyonel — verilmezse grup veya fark parametrelerinden hesaplanır)
     - `alpha` (`number`, varsayılan: `0.05`, geçerli aralık: `[1e-7, 0.9999999]`)
     - `power` (`number`, `a-priori` için zorunlu, geçerli aralık: `[alpha, 0.9999999]`)
     - `n_total` (`integer`, `post-hoc` için zorunlu, geçerli aralık: `[3, 2147483646]`)
     - `mean1`, `mean2`, `sd1`, `sd2`, `corr` (`number`, opsiyonel grup parametreleri)
     - `mean_dz`, `sd_dz` (`number`, opsiyonel fark parametreleri)
   - **Çıktı Şeması:** CLI ile birebir aynı JSON nesnesi (`n_total`, `actual_power`, `power`, `critical`, `df`, `ncp`, `dz`).

2. **`gpower_effect_size_dz`:**
   - **Açıklama:** Önce/sonra ölçümlerin ortalamaları, standart sapmaları ve korelasyonundan ($\mu_1, \mu_2, \sigma_1, \sigma_2, \rho$) veya farkların ortalaması ve standart sapmasından ($\mu_z, \sigma_z$) etki büyüklüğü $d_z$ değerini hesaplar.

---

## 3. Klinik AI Ajanı ve Sistem-1 Sınıflandırıcı Sözleşmesi (`src/agent.py`)

- **Desteklenen Karar Etiketleri:**
  `t2-indep`, `t-paired`, `anova-oneway`, `chi2-contingency`, `multireg-r2`, `ambiguous`, `unsupported`
- **Güven Eşiği Kuralı:**
  - Eğer `confidence < 0.75` ise veya etiket `ambiguous` / `unsupported` (ya da takım kapsamı dışındaki bir aile) ise ajan **sayı üretmez** ve araştırmacıdan netleştirme ister (`"clarification_required": true`).
  - Eğer etiket `t-paired` ve `confidence >= 0.75` ise ajan sorudan çıkardığı parametrelerle **MCP aracını (`gpower_t_paired`)** çağırır; tüm sayılar (`n_total`, `actual_power`, `critical`, `df`, `ncp`, `dz`) yalnızca hesap motorundan gelir.
