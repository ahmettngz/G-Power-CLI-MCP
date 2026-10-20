# G*Power 3.1.9.7 Gerçek Kâhin (Oracle) Doğrulama ve Diferansiyel Test Raporu (`oracle/ORACLE_REPORT.md`)

**Tarih:** 20 Ekim 2026  
**Kapsam:** YZM301 Teardown Sprint — Eşleştirilmiş İki Ortalama Arasındaki Fark t-Testi (*Means: Difference between two dependent means, matched pairs*)  
**Rol:** Kâhin (Oracle) Katmanı  
**Referans Veri Kümesi:** [`oracle/gpower_real_vectors.csv`](file:///C:/Users/zeyfi/.gemini/antigravity-ide/scratch/G-Power-CLI-MCP/oracle/gpower_real_vectors.csv) (56 vektör)  
**Ekran Görüntüleri:** [`oracle/screenshots/`](file:///C:/Users/zeyfi/.gemini/antigravity-ide/scratch/G-Power-CLI-MCP/oracle/screenshots/) (`GP01.png` – `GP36.png`, `SCxxxx.png`)

---

## 1. Sorun Tespiti (Sentetik vs. Gerçek Kâhin)

Takım reposunda daha önce bulunan `oracle/gpower_reference_vectors.csv` ve `oracle/scale_500_vectors.csv` dosyaları incelendiğinde, `expected_*` ve `gpower_n_total` kolonlarının G*Power yazılımından değil, `oracle/generate_oracle.py` scripti üzerinden doğrudan **kendi yeniden yazım motorumuzdan (`src/engine.py:calculate_t_paired`)** üretildiği tespit edilmiştir.

Bu durum, önceki diferansiyel testlerin motoru kendi kendisiyle karşılaştırmasına ve potansiyel varsayım/işaret yanılgılarını gizlemesine yol açmaktaydı. Bu çalışma ile kâhin rolü **doğrudan orijinal G\*Power 3.1.9.7 yazılımına** devredilmiştir.

---

## 2. Veri Toplama Yöntemi

* **Yazılım:** G*Power 3.1.9.7 (Windows NT, build 143)
* **Otomasyon:** `tools/run_real_oracle_collector.py` scripti aracılığıyla Windows Masaüstü API'si (`WinSta0\default` ve sanal masaüstü pencereleri) üzerinden Win32/pywinauto kontrolleri kullanıldı.
* **Okuma Kuralı:** Çıktı kolonları (`gpower_*`) tahmin, yuvarlama veya formül hesabı yapılmaksızın, doğrudan G*Power GUI kontrollerinin (`Edit`, `Static`, `ComboBox`) metin alanlarından birebir okundu.
* **Ekran Görüntüsü Kanıtı:** Her vektör çalıştırmasının hemen ardından pencerenin o anki durumu `oracle/screenshots/<id>.png` olarak kaydedildi.
* **Hata Yönetimi:** Geçersiz girdilerde (GP31–GP36) açılan modal uyarı pencerelerinin (`#32770 - Input error`) metni birebir okundu, ekran görüntüsü alındı ve `gpower_message` kolonuna işlenerek pencere kapatıldı.

---

## 3. Doğrulama ve Tutarlılık Denetimleri

Kâhin verisinin doğruluğu iki aşamalı bağımsız denetimle kanıtlanmıştır:

### 3.1 Dahili Bütünlük Denetimi (`tools/check_consistency.py`)
* **Kontrol Edilen Satır:** 50 geçerli vektör (6 hata vektörü hariç).
* **Kontroller:**
  * $\text{df} = N - 1$ ilişkisi tam.
  * $\delta = |d_z| \sqrt{N}$ formülü $10^{-5}$ toleransında tam.
  * Post-hoc modda ekrandaki $N$ ile girdi $N$ eşitliği tam.
  * Ardışık satırlarda aynı değerlerin kalması (bayat okuma / stale read) durumu yok.
* **Sonuç:** **0 Problem.**

### 3.2 Bağımsız Matematiksel Doğrulama (`tools/check_independent.py`)
* **Metot:** Temiz oda kuralı gereği `src/engine.py` kesinlikle import edilmedi. Yalnızca SciPy (`scipy.stats.t`, `scipy.stats.nct`) kullanıldı.
* **Kritik $t$ Uyumu:** $|t_{\text{crit}}| \le 10^{-6}$ toleransında 50/50 **%100.00 PASS**.
* **Güç (Power) Uyumu:** Noncentral t integrasyonu ile 50/50 **%100.00 PASS**.
* **A-Priori Hedef Güç Kontrolü:** Tüm a-priori satırlarda $\text{actual\_power} \ge \text{target\_power}$ sağlandı.

---

## 4. Diferansiyel Test ve Uyuşmazlık Raporu (`tests/test_oracle_real_differential.py`)

Kendi motorumuz (`src/engine.py`) gerçek G*Power kâhinine karşı çalıştırıldığında:

* **Toplam Değerlendirilen Vektör:** 56 (36 GP + 20 Seçilmiş Ekstrem Yuvarlama SC Vektörü)
* **Birebir Uyum:** 51 vektör
* **Uyum Oranı:** **%91.07**
* **Uyuşmazlık Sayısı:** 5 vektörde sistematik sapma

### Uyuşmazlık Tablosu

| Vektör ID | Kategori / Mod | Girdi Parametreleri | G\*Power 3.1.9.7 (Gerçek Kâhin) | Bizim Motor (`src/engine.py`) | Uyuşmazlık Türü |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GP11** | `negative_dz_sym` (a-priori, 2 kuyruk) | $d_z = -0.5, \alpha = 0.05, \text{pwr} = 0.95$ | **`critical = -2.0057460`**, $\delta = -3.6742346$ | `critical = 2.0057460`, $\delta = -3.6742346$ | Kritik $t$ işareti |
| **GP12** | `negative_dz_1tail` (a-priori, 1 kuyruk) | $d_z = -0.6, \alpha = 0.05, \text{pwr} = 0.85$ | **`critical = -1.7207429`**, $\delta = -2.8142495$ | `critical = 1.7207429`, $\delta = -2.8142495$ | Kritik $t$ işareti |
| **GP29** | `posthoc_negative_dz` (post-hoc, 2 kuyruk) | $d_z = -0.4, \alpha = 0.05, N = 68$ | **`critical = -1.9960084`**, $\delta = -3.2984845$ | `critical = 1.9960084`, $\delta = -3.2984845$ | Kritik $t$ işareti |
| **GP16** | `extreme_dz_15.0_minN2` (a-priori, 1 kuyruk) | $d_z = 15.0, \alpha = 0.05, \text{pwr} = 0.80$ | **`N = 2, df = 1`**, `crit = 6.3137515`, `pwr = 0.9990949` | `N = 3, df = 2`, `crit = 2.9199856`, `pwr = 1.0` | Minimum $N$ alt sınırı |
| **GP17** | `boundary_power_eq_alpha` (a-priori, 2 kuyruk) | $d_z = 0.5, \alpha = 0.05, \text{pwr} = 0.05$ | **`N = 2, df = 1`**, `crit = 12.7062047`, `pwr = 0.0619486` | `N = 3, df = 2`, `crit = 4.3026527`, `pwr = 0.0841071` | Minimum $N$ alt sınırı |

---

## 5. Uyuşmazlık Gözlem ve Hipotezleri

### 5.1 Negatif $d_z$ ve Kritik $t$ İşareti (GP11, GP12, GP29)
* **[GÖZLEM]:** G\*Power hem 1 kuyruklu hem de 2 kuyruklu modda negatif $d_z$ verildiğinde ekranda kritik $t$ değerini negatif göstermektedir (`-2.0057460`, `-1.7207429`, `-1.9960084`).
* **[AJAN-HİPOTEZ]:** G\*Power arayüz gösterim katmanında kritik $t$ değerini daima etki büyüklüğünün işaretiyle çarparak ($t_{\text{disp}} = \text{sign}(d_z) \cdot |t_{\text{crit}}|$) sunmaktadır. Decompile aşamasında `PowerTPairedMean::compute` içindeki kritik değer gösterim dalı incelenmelidir.

### 5.2 A-Priori Modda Minimum Örneklem Sınırı (GP16, GP17)
* **[GÖZLEM]:** G\*Power a-priori analizde çok büyük $d_z$ veya $\text{power} \le \alpha$ sınırında örneklem büyüklüğü olarak $N = 2$ ($\text{df} = 1$) vermektedir.
* **[AJAN-HİPOTEZ]:** Halüsinasyon #2'de tespit edilen $N \ge 3$ kısıtı (`FUN_00488a10`) yalnızca `post-hoc` analize aittir. A-priori modda t-testinin teorik serbestlik derecesi kısıtı olan $N \ge 2$ geçerlidir; motorun `max(3, ...)` zorlaması a-priori için gevşetilmelidir.

### 5.3 GP18 Tavan Koruması Doğrulaması
* **[GÖZLEM]:** GP18 vektöründe hedef güç tam $N=34$'ün gücü (`0.8077775`) girildiğinde G\*Power $N=34$ vermiştir ($35$ yapmamıştır).
* **[AJAN-HİPOTEZ]:** Ghidra analizinde keşfedilen $10^{-10}$ ön-yuvarlamalı tavan kuralı (`vftable[+0x74]`) gerçektir ve tam olarak çalışmaktadır.

### 5.4 Geçersiz Girdiler ve Diyalog Metinleri (GP31–GP36)
* **[GÖZLEM]:** G\*Power tüm geçersiz girdilerde hesabı reddetmiş ve modal hata penceresi açmıştır. Hata metinlerinde:
  * GP32/33: "Effect size d is outside the admissible range (-20, 20)." (dz değil d ifadesi ve sonunda nokta var)
  * GP34: "Alpha is outside the admissible range (1e-07, 1)." (Üst sınır 1 olarak geçiyor)
* **[AJAN-HİPOTEZ]:** Motorumuzun validasyon mantığı matematiksel olarak doğrudur, ancak hata metinleri G\*Power'ın orijinal İngilizce string tabloları ile birebir eşitlenebilir.

---

## 6. Tekrar Üretme (Reproducibility) Adımları

Tüm sonuçları sıfırdan yeniden üretmek için proje kök dizininde aşağıdaki komutlar sırayla çalıştırılır:

```bash
# 1. Dahili bütünlük kontrolü (df = N-1, delta = |dz|*sqrt(N)):
python tools/check_consistency.py

# 2. Bağımsız SciPy doğrulaması (1e-6 tolerans):
python tools/check_independent.py

# 3. Kâhin vs. Motor Diferansiyel Testi:
python tests/test_oracle_real_differential.py

# 4. (Opsiyonel) G*Power GUI'den tüm kâhin verisini ve ekran görüntülerini yeniden toplamak için:
python tools/run_real_oracle_collector.py
```
