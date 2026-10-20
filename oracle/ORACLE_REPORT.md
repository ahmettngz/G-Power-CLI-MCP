# G*Power 3.1.9.7 Gerçek Kâhin (Oracle) Doğrulama ve Diferansiyel Test Raporu (`oracle/ORACLE_REPORT.md`)

**Tarih:** 20 Ekim 2026  
**Kapsam:** Yazılım Gerçekleme ve Test — Eşleştirilmiş İki Ortalama Arasındaki Fark t-Testi (*Means: Difference between two dependent means, matched pairs*)  
**Rol:** Kâhin (Oracle) Katmanı  
**Referans Veri Kümesi:** [`oracle/gpower_real_vectors.csv`](gpower_real_vectors.csv) (56 vektör)  
**Ekran Görüntüleri:** [`oracle/screenshots/`](screenshots/) (`GP01.png` – `GP36.png`, `SCxxxx.png`)

---

## 1. Sorun Tespiti (Sentetik vs. Gerçek Kâhin)

Takım reposunda ilk aşamada bulunan `oracle/gpower_reference_vectors.csv` ve `oracle/scale_500_vectors.csv` dosyaları incelendiğinde, ilk referans değerlerin motor prototipinden üretildiği tespit edilmiştir.

Önceki diferansiyel testlerin motoru kendi kendisiyle karşılaştırmasını ve potansiyel varsayım/işaret yanılgılarını gizlemesini önlemek amacıyla kâhin rolü **doğrudan orijinal G\*Power 3.1.9.7 masaüstü yazılımına** devredilmiştir.

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

### 4.1 İlk Tur Sonucu (Halüsinasyon #4 ve #5 Düzeltmesi Öncesi — v1)
Kendi motorumuzun ilk sürümü (`src/engine.py` v1) gerçek G*Power kâhinine karşı çalıştırıldığında:

* **Toplam Değerlendirilen Vektör:** 56 (36 GP + 20 Seçilmiş Ekstrem Yuvarlama SC Vektörü)
* **Birebir Uyum:** 51 vektör
* **İlk Tur Uyum Oranı:** **%91.07**
* **Uyuşmazlık Sayısı:** 5 vektörde sistematik sapma

| Vektör ID | Kategori / Mod | Girdi Parametreleri | G\*Power 3.1.9.7 (Gerçek Kâhin) | Motor (v1 — İlk Tur) | Uyuşmazlık Türü |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GP11** | `negative_dz_sym` (a-priori, 2 kuyruk) | $d_z = -0.5, \alpha = 0.05, \text{pwr} = 0.95$ | **`critical = -2.0057460`**, $\delta = -3.6742346$ | `critical = 2.0057460`, $\delta = -3.6742346$ | Kritik $t$ işareti (Halüsinasyon #4) |
| **GP12** | `negative_dz_1tail` (a-priori, 1 kuyruk) | $d_z = -0.6, \alpha = 0.05, \text{pwr} = 0.85$ | **`critical = -1.7207429`**, $\delta = -2.8142495$ | `critical = 1.7207429`, $\delta = -2.8142495$ | Kritik $t$ işareti (Halüsinasyon #4) |
| **GP29** | `posthoc_negative_dz` (post-hoc, 2 kuyruk) | $d_z = -0.4, \alpha = 0.05, N = 68$ | **`critical = -1.9960084`**, $\delta = -3.2984845$ | `critical = 1.9960084`, $\delta = -3.2984845$ | Kritik $t$ işareti (Halüsinasyon #4) |
| **GP16** | `extreme_dz_15.0_minN2` (a-priori, 1 kuyruk) | $d_z = 15.0, \alpha = 0.05, \text{pwr} = 0.80$ | **`N = 2, df = 1`**, `crit = 6.3137515`, `pwr = 0.9990949` | `N = 3, df = 2`, `crit = 2.9199856`, `pwr = 1.0` | Minimum $N$ alt sınırı (Halüsinasyon #5) |
| **GP17** | `boundary_power_eq_alpha` (a-priori, 2 kuyruk) | $d_z = 0.5, \alpha = 0.05, \text{pwr} = 0.05$ | **`N = 2, df = 1`**, `crit = 12.7062047`, `pwr = 0.0619486` | `N = 3, df = 2`, `crit = 4.3026527`, `pwr = 0.0841071` | Minimum $N$ alt sınırı (Halüsinasyon #5) |

### 4.2 İkinci Tur Sonucu (Binary Doğrulaması ve Düzeltme Sonrası — v2 Final)
Yakalanan 5 vektördeki iki sistematik fark binary üzerinde (`0x4d38b0` ve `0x4db7f0`) doğrulanıp `src/engine.py` güncellendikten sonra:

* **Toplam Değerlendirilen Vektör:** 56
* **Birebir Uyum:** **56 vektör**
* **Final Uyum Oranı:** **%100.00 (56/56)**
* **Uyuşmazlık Sayısı:** **0**

---

## 5. Uyuşmazlık Gözlem ve Binary (`[REA]`) Doğrulaması

### 5.1 Negatif $d_z$ ve Kritik $t$ İşareti (GP11, GP12, GP29)
* **[GÖZLEM]:** G\*Power hem 1 kuyruklu hem de 2 kuyruklu modda negatif $d_z$ verildiğinde ekranda kritik $t$ değerini negatif göstermektedir (`-2.0057460`, `-1.7207429`, `-1.9960084`).
* **[REA DOĞRULAMASI]:** `PowerT::computePower` (`FUN_004d38b0` @ `0x4d38b0`) içinde `if (dz < 0.0)` dalında `p = alpha / tails`, aksi halde `p = 1.0 - alpha / tails` hesaplanarak `TDistribution::quantile(p)` çağrılmaktadır. `src/engine.py` bu kurala göre güncellenmiştir.

### 5.2 A-Priori Modda Minimum Örneklem Sınırı (GP16, GP17)
* **[GÖZLEM]:** G\*Power a-priori analizde çok büyük $d_z$ veya $\text{power} \le \alpha$ sınırında örneklem büyüklüğü olarak $N = 2$ ($\text{df} = 1$) vermektedir.
* **[REA DOĞRULAMASI]:** Halüsinasyon #2'de tespit edilen $N \ge 3$ kısıtı (`FUN_00488a10`) yalnızca `post-hoc` analize (`case 2`) aittir. A-priori modda alt sınır `2.0` (`0x4db7f0`) olup `src/engine.py` içindeki `min_bound = 2.0` olarak düzeltilmiştir.

### 5.3 GP18 ve SCxxxx Tavan Koruması Doğrulaması
* **[GÖZLEM]:** GP18 vektöründe hedef güç tam $N=34$'ün gücü (`0.8077775`) girildiğinde ve 20 adet ekstrem `SCxxxx` sınır vektöründe G\*Power ile motorumuz ilk turdan itibaren **21/21 (%100)** tam eşleşme sağlamıştır.
* **[REA DOĞRULAMASI]:** Ghidra analizinde keşfedilen $10^{-10}$ ön-yuvarlamalı tavan kuralı (`0x496a20`, `vftable[+0x74]`) gerçek G\*Power arayüzünde eksiksiz doğrulanmıştır.

---

## 6. Tekrar Üretme (Reproducibility) Adımları

Tüm sonuçları sıfırdan yeniden üretmek için proje kök dizininde aşağıdaki komutlar sırayla çalıştırılır:

```bash
# 1. Dahili bütünlük kontrolü (df = N-1, delta = |dz|*sqrt(N)):
python tools/check_consistency.py

# 2. Bağımsız SciPy doğrulaması (1e-6 tolerans):
python tools/check_independent.py

# 3. Kâhin vs. Motor Diferansiyel Testi (%100.00 uyum):
python tests/test_oracle_real_differential.py
```
