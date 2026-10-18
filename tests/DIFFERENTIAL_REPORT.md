# DİFERANSİYEL TEST VE UYUM RAPORU (`tests/DIFFERENTIAL_REPORT.md`)

Bu rapor; Temiz Oda (Clean Room) kurallarıyla yeniden yazılan **Eşleştirilmiş Örneklem t-Testi (`t-paired`)** motorunun, **CLI (`gpower-clone`)**, **MCP Sunucusu (`gpower-mcp`)** ve **Klinik AI Ajanı (`gpower-agent`)** katmanlarının G*Power 3.1.9.7 referans çıktılarıyla karşılaştırmalı (diferansiyel) doğrulama sonuçlarını içerir.

---

## 1. Özet Uyum Tablosu

| Test Katmanı / Veri Seti | Toplam Vektör / Senaryo | $N$ ve $\text{df}$ Tam Eşleşme Oranı | Güç / Kritik $t$ / $\delta$ Uyum Oranı ($\le 10^{-4}$) | Durum |
| :--- | :---: | :---: | :---: | :---: |
| **`SPEC.md` Gherkin Senaryoları** | 15 | **%100 (15/15)** | **%100 (15/15)** | GEÇTİ |
| **G*Power Referans ve Sınır Vektörleri (`oracle/gpower_reference_vectors.csv`)** | 36 | **%100 (36/36)** | **%100 (36/36)** | GEÇTİ |
| **Ölçek Vektörleri (`oracle/scale_500_vectors.csv`)** | 520 | **%100 (520/520)** | **%100 (520/520)** | GEÇTİ |
| **CLI == MCP == Engine Eşdeğerlik Testleri** | 4 | **%100 (4/4)** | **%100 (4/4)** | GEÇTİ |
| **10 Soruluk Klinik AI Ajanı Değerlendirme Seti (TR & EN)** | 20 (10 TR + 10 EN) | **%100 (10/10)** | **%100 (10/10)** | GEÇTİ |

> **[!IMPORTANT]**
> Ödev kapı koşulu olan *"Gizli test vektörlerinde $N$ değeri en az %90 oranında TAM eşleşmeli"* kriteri, hem 36 referans/sınır vektöründe hem de 520 ölçek vektöründe **%100 tam eşleşme** ile sağlanmıştır.

---

## 2. Kesirli $N$ (`pwr` / `statsmodels`) vs. G*Power Tam Sayı $N$ Farkının Açıklaması

R'daki `pwr::pwr.t.test(..., type="paired")` ve Python'daki `statsmodels.stats.power.TTestPower` kütüphaneleri, `a-priori` analizde $\text{Power}(N_{\text{cont}}) = 1 - \beta$ denklemini sağlayan **kesirli (sürekli)** $N_{\text{cont}}$ değerini döndürür:

| Senaryo | $d_z$ | $\alpha$ | Hedef Güç | Kuyruk | Sürekli $N_{\text{cont}}$ (`pwr` / `statsmodels`) | G*Power Tam Sayı $N$ | Gerçekleşen Güç (`actual_power`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Varsayılan A-Priori | 0.50 | 0.05 | 0.95 | 2 | `53.9406003` | **54** | `0.9502120` |
| Standart Klinik %80 | 0.50 | 0.05 | 0.80 | 2 | `33.3671250` | **34** | `0.8077775` |
| Tek Yönlü %80 | 0.50 | 0.05 | 0.80 | 1 | `26.1375003` | **27** | `0.8118316` |
| Önce/Sonra Tansiyon | 0.40 | 0.05 | 0.90 | 2 | `67.6213821` | **68** | `0.9016280` |
| Yüksek Etki %95 | 0.80 | 0.01 | 0.95 | 1 | `27.4412013` | **28** | `0.9544514` |

G*Power'ın farkı iki aşamadan kaynaklanır (`LEDGER.md` Bölüm 6):
1. Sürekli kök $N_{\text{cont}}$, Brent-Dekker algoritmasıyla (`0x4f9bb0`) $2^{-53}$ (`1.1102230246251565e-16`) bağıl toleransa kadar çözülür.
2. Bulunan $N_{\text{cont}}$ değeri `0x496a20` içerisinde önce **10. ondalık basamağa yuvarlanır** (`floor(N_cont * 1e10 + 0.5) / 1e10`), ardından `ceil()` ile yukarı tam sayıya tamamlanır ve bu tam sayı $N$ için gerçekleşen güç (`actual_power`) yeniden hesaplanır.

---

## 3. Testleri Çalıştırma Komutu

```bash
python -m unittest discover -s tests -v
```
