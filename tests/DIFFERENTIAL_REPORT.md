# DİFERANSİYEL TEST VE UYUM RAPORU (`tests/DIFFERENTIAL_REPORT.md`)

Bu rapor; Temiz Oda (Clean Room) kurallarıyla yeniden yazılan **Eşleştirilmiş Örneklem t-Testi (`t-paired`)** motorunun, **CLI (`gpower-clone`)**, **MCP Sunucusu (`gpower-mcp`)** ve **Klinik AI Ajanı (`gpower-agent`)** katmanlarının gerçek **G\*Power 3.1.9.7** masaüstü kâhin çıktılarıyla (`oracle/gpower_real_vectors.csv` + 56 ekran görüntüsü) ve ölçek veri setleriyle karşılaştırmalı (diferansiyel) doğrulama sonuçlarını içerir.

---

## 1. Özet Uyum Tablosu

| Test Katmanı / Veri Seti | Toplam Vektör / Senaryo | İlk Tur (v1) Uyum Oranı | Final (v2) $N$ & $\text{df}$ Tam Eşleşme | Final (v2) Güç / $t_{\text{crit}}$ / $\delta$ Uyumu | Durum |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Gerçek G\*Power 3.1.9.7 GUI Kâhini (`oracle/gpower_real_vectors.csv` + 56 PNG)** | 56 | %91.07 (51/56) | **%100.00 (56/56)** | **%100.00 (56/56)** | GEÇTİ |
| **`SPEC.md` Gherkin Senaryoları** | 15 | %100.00 (15/15) | **%100.00 (15/15)** | **%100.00 (15/15)** | GEÇTİ |
| **G\*Power Referans ve Sınır Vektörleri (`oracle/gpower_reference_vectors.csv`)** | 36 | %100.00 (36/36) | **%100.00 (36/36)** | **%100.00 (36/36)** | GEÇTİ |
| **Ölçek Vektörleri (`oracle/scale_500_vectors.csv`)** | 520 | %100.00 (520/520) | **%100.00 (520/520)** | **%100.00 (520/520)** | GEÇTİ |
| **CLI == MCP == Engine Eşdeğerlik Testleri** | 4 | %100.00 (4/4) | **%100.00 (4/4)** | **%100.00 (4/4)** | GEÇTİ |
| **10 Soruluk Klinik AI Ajanı Değerlendirme Seti (TR & EN)** | 20 (10 TR + 10 EN) | %100.00 (20/20) | **%100.00 (20/20)** | **%100.00 (20/20)** | GEÇTİ |

> **[!IMPORTANT]**
> 1. Gerçek G\*Power 3.1.9.7 GUI kâhinine karşı yapılan ilk turda (`v1`) **51/56 (%91.07)** uyum elde edilmiş; fark çıkan 5 vektör (`GP11`, `GP12`, `GP29`, `GP16`, `GP17`) sayesinde **Halüsinasyon #4** ($d_z < 0$ için negatif `Critical t`) ve **Halüsinasyon #5** (`a-priori` modda minimum $N = 2$) yakalanıp düzeltilerek **56/56 (%100.00)** tam uyuma ulaşılmıştır. Detaylar [`oracle/ORACLE_REPORT.md`](../oracle/ORACLE_REPORT.md) ve [`HALLUCINATIONS.md`](../HALLUCINATIONS.md) içindedir.
> 2. Ödev kapı koşulu olan *"Gizli test vektörlerinde $N$ değeri en az %90 oranında TAM eşleşmeli"* kriteri **%100.00 tam eşleşme** ile sağlanmıştır.

---

## 2. Kesirli $N$ (`pwr` / `statsmodels`) vs. G*Power Tam Sayı $N$ Farkının Açıklaması

R'daki `pwr::pwr.t.test(..., type="paired")` ve Python'daki `statsmodels.stats.power.TTestPower` kütüphaneleri, `a-priori` analizde $\text{Power}(N_{\text{cont}}) = 1 - \beta$ denklemini sağlayan **kesirli (sürekli)** $N_{\text{cont}}$ değerini döndürür:

| Senaryo | $d_z$ | $\alpha$ | Hedef Güç | Kuyruk | Sürekli $N_{\text{cont}}$ (`pwr` / `statsmodels`) | G*Power Tam Sayı $N$ | Gerçekleşen Güç (`actual_power`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Varsayılan A-Priori (`GP01`) | 0.50 | 0.05 | 0.95 | 2 | `53.9406003` | **54** | `0.9502120` |
| Standart Klinik %80 (`GP02`) | 0.50 | 0.05 | 0.80 | 2 | `33.3671250` | **34** | `0.8077775` |
| Tek Yönlü %80 (`GP03`) | 0.50 | 0.05 | 0.80 | 1 | `26.1375003` | **27** | `0.8118316` |
| Önce/Sonra Tansiyon (`GP06`) | 0.40 | 0.05 | 0.90 | 2 | `67.6213821` | **68** | `0.9016280` |
| Yüksek Etki %95 (`GP08`) | 0.80 | 0.01 | 0.95 | 1 | `27.4412013` | **28** | `0.9544514` |

G*Power'ın farkı iki aşamadan kaynaklanır (`LEDGER.md` Bölüm 6):
1. Sürekli kök $N_{\text{cont}}$, Brent-Dekker algoritmasıyla (`0x4f9bb0`) $2^{-53}$ (`1.1102230246251565e-16`) bağıl toleransa kadar çözülür.
2. Bulunan $N_{\text{cont}}$ değeri `0x496a20` içerisinde önce **10. ondalık basamağa yuvarlanır** (`floor(N_cont * 1e10 + 0.5) / 1e10`), ardından `ceil()` ile yukarı tam sayıya tamamlanır ve bu tam sayı $N$ için gerçekleşen güç (`actual_power`) yeniden hesaplanır.

---

## 3. Testleri Çalıştırma Komutu

```bash
python -m unittest discover -s tests -v
python tests/test_oracle_real_differential.py
```
