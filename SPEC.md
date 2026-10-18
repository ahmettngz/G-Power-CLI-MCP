# DAVRANIŞSAL SPESİFİKASYON (`SPEC.md`) — Konu 2: Eşleştirilmiş Çift t-Testi (`t-paired`)

Bu belge, **Clean Room (Temiz Oda)** mimarisi kapsamında **Oturum 1 (Teardown Sprint)** çıktısı olarak hazırlanmıştır ve **Oturum 2 (Kodlama)** oturumuna aktarılan **tek** belgedir. Herhangi bir ham kaynak kodu veya decompiler çıktısı içermez; yalnızca matematiksel, algoritmik ve davranışsal spesifikasyonu tanımlar.

---

## 1. Kapsam ve CLI / JSON Sözleşmesi

### 1.1 Test Kimliği
- **Konu #2:** *t testi, eşleştirilmiş ortalama (önce ve sonra tansiyon)*
- **G*Power Karşılığı:** `t tests` $\rightarrow$ `Means: Difference between two dependent means (matched pairs)`
- **CLI Alt Komutu:** `--test t-paired`
- **Desteklenen Modlar:**
  1. `--mode a-priori`: Verilen $\alpha$, hedef güç ($1-\beta$), etki büyüklüğü ($d_z$) ve kuyruk sayısı (`tails`) için gereken minimum örneklem çifti sayısını (`n_total`) ve gerçekleşen gücü (`actual_power`) hesaplar.
  2. `--mode post-hoc`: Verilen $\alpha$, örneklem çifti sayısı (`n_total`), etki büyüklüğü ($d_z$) ve kuyruk sayısı (`tails`) için ulaşılan istatistiksel gücü (`power` / `actual_power`) hesaplar.

### 1.2 CLI Çağrı Biçimi
```bash
# A-priori mod (doğrudan dz veya d ile)
gpower-clone --test t-paired --mode a-priori --tails 2 --dz 0.5 --alpha 0.05 --power 0.95

# Post-hoc mod (doğrudan dz ve n ile)
gpower-clone --test t-paired --mode post-hoc --tails 2 --dz 0.5 --alpha 0.05 --n 34

# Önce ve sonra tansiyon grup parametrelerinden dz hesaplayarak çalıştırma
gpower-clone --test t-paired --mode a-priori --tails 2 --mean1 140 --mean2 136 --sd1 10 --sd2 10 --corr 0.5 --alpha 0.05 --power 0.90
```

### 1.3 Standart Çıktı (Tek Satır JSON)
- **`a-priori` çıktısı:**
  `{"test":"t-paired","mode":"a-priori","tails":2,"dz":0.5,"alpha":0.05,"n_total":54,"actual_power":0.950212,"power":0.950212,"critical":2.005746,"df":53,"ncp":3.6742346}`
- **`post-hoc` çıktısı:**
  `{"test":"t-paired","mode":"post-hoc","tails":2,"dz":0.5,"alpha":0.05,"n_total":34,"power":0.8077775,"actual_power":0.8077775,"critical":2.0345153,"df":33,"ncp":2.9154759}`
- **Geçersiz girdide (çıkış kodu `!= 0`):**
  `{"error":"<açıklama>"}`

---

## 2. Matematiksel ve Algoritmik Kurallar

### 2.1 Etki Büyüklüğü ($d_z$) Hesaplama Kuralları
1. **Farklardan Hesaplama (`mean_dz`, `sd_dz`):**
   - Koşul: $\sigma_z > 10^{-12}$
   - Formül (işaret korunur): $d_z = \mu_z / \sigma_z$
2. **Grup Parametrelerinden Hesaplama — Önce ve Sonra Tansiyon (`mean1`, `mean2`, `sd1`, `sd2`, `corr`):**
   - Koşullar: $\sigma_1 > 10^{-12}$, $\sigma_2 > 10^{-12}$ ve $-0.99999999 < \rho \le 0.99999999$
   - Formül (mutlak fark kullanılır):
     $$\sigma_z = \sqrt{\sigma_1^2 + \sigma_2^2 - 2\rho\sigma_1\sigma_2}, \qquad d_z = \frac{|\mu_1 - \mu_2|}{\sigma_z}$$

### 2.2 Temel Dağılım Parametreleri ($\text{df}$, $\delta$, $t_{\text{crit}}$)
1. **Serbestlik Derecesi ($\text{df}$):** $\text{df} = N - 1$
2. **Merkezî Olmama Parametresi ($\delta$ / `ncp`):**
   - Güç hesabında kullanılan büyüklük: $|\delta| = \sqrt{N} \cdot |d_z|$
   - Raporlanan değer: $\delta = \sqrt{N} \cdot d_z$
3. **Kritik $t$ Değeri (`critical`):**
   Merkezî Student-$t$ dağılımının ters CDF fonksiyonu $F_{t,\text{df}}^{-1}$ kullanılarak:
   - Tek yönlü (`tails == 1`): $t_{\text{crit}} = F_{t,\text{df}}^{-1}(1 - \alpha)$
   - Çift yönlü (`tails == 2`): $t_{\text{crit}} = F_{t,\text{df}}^{-1}(1 - \alpha/2)$

### 2.3 İstatistiksel Güç (`Power`) Hesaplama Formülü
Merkezî olmayan $t$ dağılımının birikimli dağılım fonksiyonu $F_{t,\text{df},|\delta|}(x)$ kullanılarak:
- **Tek yönlü (`tails == 1`):**
  $$\text{Power}(N) = 1 - F_{t,\text{df},|\delta|}(t_{\text{crit}})$$
- **Çift yönlü (`tails == 2`):**
  $$\text{Power}(N) = \left[1 - F_{t,\text{df},|\delta|}(t_{\text{crit}})\right] + F_{t,\text{df},|\delta|}(-t_{\text{crit}})$$

### 2.4 `a-priori` Örneklem Büyüklüğü Arama Algoritması ve Yuvarlama Kuralı
1. **Alt Sınır (`minN`):** $N_{\min} = 2.0$ (arama başlangıç alt tabanı $2.000001 = 2 + 10^{-6}$).
2. **Başlangıç Tahmini ve Paranteze Alma (Bracketing):**
   $$N_{\text{guess}} = \max\!\left(2.0,\; \frac{(z_{1-\alpha/\text{tails}} + z_{\text{power}})^2}{d_z^2}\right)$$
   Hedef fonksiyon $f(N) = \text{Power}(N) - \text{Power}_{\text{target}}$ olmak üzere kök $[N_{\text{low}}, N_{\text{high}}]$ aralığına alınır.
3. **Sürekli Kök Çözücü (Brent-Dekker Algoritması):**
   $[N_{\text{low}}, N_{\text{high}}]$ aralığında $f(N_{\text{cont}}) = 0$ denklemi Brent-Dekker yöntemiyle çözülür (durma koşulu: $|0.5 \cdot (c - b)| \le 1.1102230246251565 \times 10^{-16} \cdot |b|$ veya $f(b) = 0.0$, maksimum `300` iterasyon).
4. **10 Ondalık Basamak Ön-Yuvarlamalı Tavan (`ceil`) Kuralı:**
   $$N_{\text{rounded}} = \frac{\lfloor N_{\text{cont}} \times 10^{10} + 0.5 \rfloor}{10^{10}}, \qquad N = \max\!\left(2,\; \lceil N_{\text{rounded}} \rceil\right)$$
5. **Gerçekleşen Güç (`actual_power`) Yeniden Hesabı:**
   Tam sayı $N$ üzerinden $\text{df} = N - 1$, $t_{\text{crit}}$, $\delta = \sqrt{N}\cdot d_z$ ve $\text{actual\_power} = \text{Power}(N)$ yeniden hesaplanır.

---

## 3. Gherkin Davranışsal Senaryoları (`Feature` / `Scenario`)

```gherkin
Feature: Paired Samples t-Test Power and Sample Size Calculation (t-paired)
  As a biomedical researcher studying pre- and post-treatment blood pressure measurements
  I want to compute required sample sizes (a-priori) and achieved statistical power (post-hoc)
  So that my study design matches G*Power 3.1.9.7 within reference tolerances

  Background:
    Given the statistical test is "t-paired"
    And floating-point comparisons use tolerance 1e-4 for probabilities/parameters and exact match for integer N and df

  Scenario: Varsayilan G*Power A-Priori Analizi (Cift Yonlu, dz=0.5, alpha=0.05, power=0.95)
    Given the analysis mode is "a-priori"
    And the number of tails is 2
    And the effect size dz is 0.5
    And the significance level alpha is 0.05
    And the target power is 0.95
    When the calculation is executed
    Then the required total sample size N should be 54
    And the degrees of freedom df should be 53
    And the noncentrality parameter delta should be 3.6742346
    And the critical t value should be 2.0057460
    And the actual power should be 0.9502120

  Scenario: Standart Klinik A-Priori Analizi (Cift Yonlu, dz=0.5, alpha=0.05, power=0.80)
    Given the analysis mode is "a-priori"
    And the number of tails is 2
    And the effect size dz is 0.5
    And the significance level alpha is 0.05
    And the target power is 0.80
    When the calculation is executed
    Then the required total sample size N should be 34
    And the degrees of freedom df should be 33
    And the noncentrality parameter delta should be 2.9154759
    And the critical t value should be 2.0345153
    And the actual power should be 0.8077775

  Scenario: Tek Yonlu A-Priori Analizi (Tek Yonlu, dz=0.5, alpha=0.05, power=0.80)
    Given the analysis mode is "a-priori"
    And the number of tails is 1
    And the effect size dz is 0.5
    And the significance level alpha is 0.05
    And the target power is 0.80
    When the calculation is executed
    Then the required total sample size N should be 27
    And the degrees of freedom df should be 26
    And the noncentrality parameter delta should be 2.5980762
    And the critical t value should be 1.7056179
    And the actual power should be 0.8118316

  Scenario: Once ve Sonra Tansiyon Calismasi - Grup Parametrelerinden A-Priori Analiz
    Given the analysis mode is "a-priori"
    And the number of tails is 2
    And the pre-treatment systolic blood pressure mean1 is 140.0 with sd1 10.0
    And the post-treatment systolic blood pressure mean2 is 136.0 with sd2 10.0
    And the correlation between paired measurements corr is 0.5
    And the significance level alpha is 0.05
    And the target power is 0.90
    When the effect size dz and sample size calculation are executed
    Then the computed effect size dz should be 0.4000000
    And the required total sample size N should be 68
    And the degrees of freedom df should be 67
    And the noncentrality parameter delta should be 3.2984845
    And the critical t value should be 1.9960084
    And the actual power should be 0.9016280

  Scenario: Yuksek Etki Buyuklugunde Tek Yonlu A-Priori Analizi (dz=0.8, alpha=0.01, power=0.95)
    Given the analysis mode is "a-priori"
    And the number of tails is 1
    And the effect size dz is 0.8
    And the significance level alpha is 0.01
    And the target power is 0.95
    When the calculation is executed
    Then the required total sample size N should be 28
    And the degrees of freedom df should be 27
    And the noncentrality parameter delta should be 4.2332021
    And the critical t value should be 2.4726599
    And the actual power should be 0.9544514

  Scenario: 10 Ondalik Basamak On-Yuvarlamali Tavan (Ceil) Kurali Kontrolu
    Given the analysis mode is "a-priori"
    And the number of tails is 2
    And the effect size dz is 0.5
    And the significance level alpha is 0.05
    And the target power is 0.8077775
    When the calculation is executed
    Then the required total sample size N should be 34
    And the actual power should be 0.8077775

  Scenario: Cift Yonlu Post-Hoc Guc Analizi (N=34, dz=0.5, alpha=0.05)
    Given the analysis mode is "post-hoc"
    And the number of tails is 2
    And the effect size dz is 0.5
    And the significance level alpha is 0.05
    And the total sample size N is 34
    When the calculation is executed
    Then the degrees of freedom df should be 33
    And the noncentrality parameter delta should be 2.9154759
    And the critical t value should be 2.0345153
    And the achieved power should be 0.8077775

  Scenario: Tek Yonlu Post-Hoc Guc Analizi (N=27, dz=0.5, alpha=0.05)
    Given the analysis mode is "post-hoc"
    And the number of tails is 1
    And the effect size dz is 0.5
    And the significance level alpha is 0.05
    And the total sample size N is 27
    When the calculation is executed
    Then the degrees of freedom df should be 26
    And the noncentrality parameter delta should be 2.5980762
    And the critical t value should be 1.7056179
    And the achieved power should be 0.8118316

  Scenario: Minimum Post-Hoc Orneklem Buyuklugu Sinir Degeri (N=3, dz=1.0, alpha=0.05, Cift Yonlu)
    Given the analysis mode is "post-hoc"
    And the number of tails is 2
    And the effect size dz is 1.0
    And the significance level alpha is 0.05
    And the total sample size N is 3
    When the calculation is executed
    Then the degrees of freedom df should be 2
    And the noncentrality parameter delta should be 1.7320508
    And the critical t value should be 4.3026527
    And the achieved power should be 0.1792554

  Scenario: A-Priori Modda Cok Kucuk Etki Buyuklugu Hatasi (|dz| < 0.00001)
    Given the analysis mode is "a-priori"
    And the number of tails is 2
    And the effect size dz is 0.000005
    And the significance level alpha is 0.05
    And the target power is 0.80
    When the calculation is executed
    Then the calculation should fail with validation error "In an a priori analysis, the absolute value of the effect size be greater than 0.00001."

  Scenario: Etki Buyuklugu Araligi Disinda Hatasi (|dz| > 20)
    Given the analysis mode is "post-hoc"
    And the number of tails is 2
    And the effect size dz is 25.0
    And the significance level alpha is 0.05
    And the total sample size N is 20
    When the calculation is executed
    Then the calculation should fail with validation error "Effect size dz is outside the admissible range (-20, 20)"

  Scenario: Alpha Araligi Disinda Hatasi (alpha < 1e-7 veya alpha > 0.9999999)
    Given the analysis mode is "a-priori"
    And the number of tails is 2
    And the effect size dz is 0.5
    And the significance level alpha is 0.0
    And the target power is 0.80
    When the calculation is executed
    Then the calculation should fail with validation error "Alpha is outside the admissible range (1e-07, 0.9999999)"

  Scenario: Hedef Guc Alpha Degerinden Kucuk Hatasi (power < alpha)
    Given the analysis mode is "a-priori"
    And the number of tails is 2
    And the effect size dz is 0.5
    And the significance level alpha is 0.10
    And the target power is 0.05
    When the calculation is executed
    Then the calculation should fail with validation error "Power must be greater than or equal to alpha."

  Scenario: Post-Hoc Modda Gecersiz Orneklem Buyuklugu Hatasi (N < 3)
    Given the analysis mode is "post-hoc"
    And the number of tails is 2
    And the effect size dz is 0.5
    And the significance level alpha is 0.05
    And the total sample size N is 2
    When the calculation is executed
    Then the calculation should fail with validation error "Total sample size is outside the admissible range (3, 2147483646)"

  Scenario: Grup Parametrelerinden dz Hesabinda Gecersiz Korelasyon veya Standart Sapma
    Given the analysis mode is "a-priori"
    And the number of tails is 2
    And the pre-treatment systolic blood pressure mean1 is 140.0 with sd1 10.0
    And the post-treatment systolic blood pressure mean2 is 130.0 with sd2 10.0
    And the correlation between paired measurements corr is 1.0
    When the effect size dz and sample size calculation are executed
    Then the calculation should fail with validation error "Correlation lies outside of admissible range (-1+1e-8,1-1e-8)"
```
