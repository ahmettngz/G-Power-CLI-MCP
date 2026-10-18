# KANIT DEFTERİ (`LEDGER.md`) — Teardown Sprint (Oturum 1)

- **Hedef Binary:** `GPowerNT.exe` (G*Power 3.1.9.7 Windows x86 PE32)
- **SHA-256:** `c63e6a133eb6372932f810c08cc33dc35a06d1ddb658f897bd6c34a754efc812`
- **Tersine Mühendislik Altyapısı:** `rea-agents@4.0.1` + `Ghidra 12.1.4` (`jdk-21.0.10.7-hotspot`)
- **Konu #2 (`t-paired`):** *t testi, eşleştirilmiş ortalama (önce ve sonra tansiyon)*
  - G*Power Test Ailesi: `"t tests"` (`0x4d2a30`)
  - G*Power İstatistiksel Test Adı: `"Means: Difference between two dependent means (matched pairs)"` (`0x4dcf10`, string `@ 0x5cb56c`)
  - Kapsanan Analiz Modları:
    - **`a-priori`:** `"A priori: Compute required sample size - given \alpha, power, and effect size"` (`mode = 0`)
    - **`post-hoc`:** `"Post hoc: Compute achieved power - given \alpha, sample size, and effect size"` (`mode = 2`)

---

## Etiket Sistemi
- **`[DOK]` (Dokümantasyon):** G*Power 3.1 resmi kılavuzu ve Faul, Erdfelder, Lang & Buchner (2007, 2009) makalelerinde yer alan formüller.
- **`[REA]` (Binary Kanıtı):** `rea-agents` ve Ghidra 12.1.4 ile `GPowerNT.exe` içerisinden çıkarılan fonksiyon adresleri, sanal tablo (`vftable`) slotları, `.data` sabitleri ve 5–15 satırlık kısa kanıt kesitleri.
- **`[AJAN]` (Sentez / Çıkarım):** Dokümantasyon ile binary kanıtlarının birleştirilmesiyle elde edilen çıkarımlar.

---

## 1. Sınıf Hiyerarşisi ve Sanal Tablo (`vftable`) Yapısı

- **`[REA]` MSVC RTTI Kalıtım Zinciri:**
  - `PowerAnalysis` (`vftable @ 0x5c68b8`, `RTTI TypeDescriptor @ 0x60c8a4`, ctor `@ 0x496e50`)
    - $\rightarrow$ `PowerT` (`vftable @ 0x5ca2d8`, `RTTI @ 0x60cd90`, ctor `@ 0x4d2530`)
      - $\rightarrow$ `PowerTOneMean` (`vftable @ 0x5caa80`, `RTTI @ 0x60ce28`, ctor `@ 0x4db820`)
        - $\rightarrow$ **`PowerTPairedMean`** (`vftable @ 0x5cac60`, `RTTI @ 0x60ce88`, clone/ctor `@ 0x4dc9d0`)
  - İstatistiksel Dağılım Sınıfı: **`TDistribution`** (`vftable @ 0x5c4a20`, `RTTI @ 0x60c7b4`, CDF `@ 0x4fa7e0`, Quantile `@ 0x4fb8c0`)
  - Etki Büyüklüğü ($d_z$) Hesaplayıcı Sınıfı: **`CEff_T_PairedMeans`** (`vftable @ 0x5d67b4`, `RTTI @ 0x60d9dc`, `OnCalculate @ 0x52e370`)

```c
// [REA] Kanıt — Procedure: 0x4dc9d0 (PowerTPairedMean::clone / nesne kurulumu)
puVar2 = (undefined4 *)operator_new(0x368);
if (puVar2 != (undefined4 *)0x0) {
  FUN_004db820(in_ECX);               // PowerTOneMean constructor (0x4db820)
  *puVar2 = PowerTPairedMean::vftable; // 0x5cac60
  puVar2[0xd8] = 0xffffffff;          // this + 0x360 = -1 (parametrik eşleştirilmiş t-testi)
  FUN_004dc230();                     // initDefaults (0x4dc230)
}
```

- **`[AJAN]` Mimari Çıkarım:**
  `PowerTOneMean`, `PowerTPairedMean` ve Wilcoxon işaretli sıra testleri aynı C++ temel sınıfını (`PowerTOneMean`) paylaşır. `PowerTPairedMean` içinde `this + 0x358 == 0` (`isWilcoxon = false`) ve `this + 0x35c == 0` (`areIndex = 0`) olarak ayarlanır.

---

## 2. Varsayılan Parametreler (`[REA]`)

- **`[REA]` `PowerTPairedMean::initDefaults` (`0x4dc230`, `vftable[46 / +0x0b8]`):**
  - Kuyruk sayısı (`this + 0x2a9`): `0` (`Two-tailed` varsayılan; `1` = `One-tailed`)
  - Etki büyüklüğü $d_z$ (`this + 0xd8`): `0x3fe0000000000000` (`0.5`)
  - $\alpha$ hata olasılığı (`this + 0xb0`): `0x3fa999999999999a` (`0.05`)
  - Güç $1-\beta$ (`this + 0xb8`): `0x3fee666666666666` (`0.95`)
  - Toplam örneklem büyüklüğü $N$ (`this + 0xe8`): `0x4059000000000000` (`100.0`)

---

## 3. Serbestlik Derecesi ($\text{df}$) ve Ölçek Sabiti (`[DOK]` & `[REA]`)

- **`[DOK]` Formül:** $\text{df} = N - 1$
- **`[REA]` Binary Kanıtı (`0x4db950`, `vftable[73 / +0x124]` ve `.data @ 0x6096a8`):**
  `0x6096a8` adresindeki 4 elemanlı `double` dizisi `(1.0, 1.0, 1.5, 0.954929658551372)` değerlerini taşır (`[0] = 1.0` parametrik t-testi, diğerleri Wilcoxon ARE katsayıları). `PowerTPairedMean` için `this + 0x35c == 0` ve `this + 0x358 == 0` olduğundan `df = 1.0 * N - 1.0 = N - 1.0` hesaplanır:

```c
// [REA] Kanıt — Procedure: 0x4db950 (PowerTOneMean::computeDf)
float10 FUN_004db950(double param_1) {
  double dVar1;
  int in_ECX;
  dVar1 = (&DAT_006096a8)[*(int *)(in_ECX + 0x35c)] * param_1 - 1.0;
  if ((*(char *)(in_ECX + 0x358) != '\0') && (dVar1 = floor(dVar1), dVar1 <= 1.0)) {
    dVar1 = 1.0;
  }
  return (float10)dVar1;
}
```

---

## 4. Merkezî Olmama Parametresi ($\delta$ / `ncp`) ve Etki Büyüklüğü ($d_z$) (`[DOK]` & `[REA]` & `[AJAN]`)

- **`[DOK]` Formül:**
  $$d_z = \frac{|\mu_1 - \mu_2|}{\sqrt{\sigma_1^2 + \sigma_2^2 - 2\rho\sigma_1\sigma_2}} = \frac{\mu_z}{\sigma_z}, \qquad \delta = d_z \cdot \sqrt{N}$$
- **`[REA]` Merkezî Olmama Parametresi (`0x4dbdc0`, `vftable[20 / +0x050]`):**
  `0x4bdee0` fonksiyonu toplam $N$'yi `param_2 = N * 0.5` ve `param_3 = N * 0.5` olarak gönderir; `0x4dbdc0` içinde `(param_2 + param_3) * 1.0 = N` karekökü alınarak $d_z$ ile çarpılır:

```c
// [REA] Kanıt — Procedure: 0x4dbdc0 (PowerTOneMean::computeNcp)
float10 FUN_004dbdc0(double param_1, double param_2, double param_3) {
  int in_ECX;
  double dVar1;
  dVar1 = (param_2 + param_3) * (&DAT_006096a8)[*(int *)(in_ECX + 0x35c)];
  dVar1 = SQRT(dVar1);
  return (float10)(dVar1 * param_1);
}
```

- **`[REA]` Etki Büyüklüğü Hesaplayıcı Diyaloğu (`CEff_T_PairedMeans::OnCalculate @ 0x52e370`):**
  Kılavuzda belirtilmeyen önemli bir detay olarak:
  - Farklardan hesaplama modunda (`tdm_inmode == 0`): `dz = mean_dz / sd_dz` (**işaret korunur**).
  - Grup parametrelerinden hesaplama modunda (`tdm_inmode == 1`, önce/sonra tansiyon): `dz = ABS(mean1 - mean2) / sqrt(sd1^2 + sd2^2 - 2*corr*sd1*sd2)` (**mutlak değer** kullanılır).

```c
// [REA] Kanıt — Procedure: 0x52e370 (CEff_T_PairedMeans::OnCalculate)
if (*(int *)(in_ECX + 0x110) == 0) {
  if (*(double *)(in_ECX + 0x4a0) <= 1e-12) { /* hata mesajı */ return; }
  dVar5 = *(double *)(in_ECX + 0x498) / *(double *)(in_ECX + 0x4a0);
} else {
  fVar3 = (float10)FUN_00572840(*(double *)(in_ECX + 0xf8));     // sd2^2
  fVar4 = (float10)FUN_00572840(*(undefined8 *)(in_ECX + 0xf0)); // sd1^2
  dVar5 = (double)(fVar4 + (float10)(double)fVar3) -
          (*(double *)(in_ECX + 0x100) + *(double *)(in_ECX + 0x100)) * *(double *)(in_ECX + 0xf0) * *(double *)(in_ECX + 0xf8);
  dVar5 = SQRT(dVar5);
  dVar5 = ABS(*(double *)(in_ECX + 0xe0) - *(double *)(in_ECX + 0xe8)) / dVar5;
}
```

---

## 5. Kritik $t$ ($t_{\text{crit}}$) ve Güç (`Power`) Hesabı (`[DOK]` & `[REA]`)

- **`[DOK]` Formül:**
  - Tek yönlü (`tails == 1`): $t_{\text{crit}} = F_{t,\text{df}}^{-1}(1 - \alpha)$, $\quad \text{Power} = 1 - F_{t,\text{df},|\delta|}(t_{\text{crit}})$
  - Çift yönlü (`tails == 2`): $t_{\text{crit}} = F_{t,\text{df}}^{-1}(1 - \alpha/2)$, $\quad \text{Power} = \left[1 - F_{t,\text{df},|\delta|}(t_{\text{crit}})\right] + F_{t,\text{df},|\delta|}(-t_{\text{crit}})$
- **`[REA]` Binary Kanıtı (`PowerT::computePowerCore @ 0x4d38b0`, `vftable[13 / +0x034]`):**

```c
// [REA] Kanıt — Procedure: 0x4d38b0 (PowerT::computePowerCore)
fVar2 = (float10)(**(code **)(*in_ECX + 0x124))(param_3, param_4); // df = N - 1 (0x4db950)
*(double *)(in_ECX + 0x38) = (double)fVar2;
(**(code **)(*(int *)in_ECX[0x16] + 0x2c))(0);                     // TDist->setNcp(0.0)
(**(code **)(*(int *)in_ECX[0x16] + 0x24))(1, *(undefined8 *)(in_ECX + 0x38)); // TDist->setDf(df)
dVar3 = 1.0 - (param_2 * 0.5) / ((double)((ulonglong)uVar1 << 0x20) + 1.0);
fVar2 = (float10)(**(code **)(*(int *)in_ECX[0x16] + 8))(dVar3);   // t_crit (0x4fb8c0)
*(double *)(in_ECX + 0x3e) = (double)fVar2;
fVar2 = (float10)(**(code **)(*in_ECX + 0x50))(ABS(param_1), param_3, param_4); // |ncp| (0x4dbdc0)
*(double *)(in_ECX + 0x40) = (double)fVar2;
(**(code **)(*(int *)in_ECX[0x16] + 0x2c))((double)fVar2);         // TDist->setNcp(|ncp|)
fVar2 = (float10)(**(code **)(*(int *)in_ECX[0x16] + 4))(*(undefined8 *)(in_ECX + 0x3e)); // F_nct(t_crit) (0x4fa7e0)
dVar3 = 1.0 - (double)fVar2;
if (*(char *)((int)in_ECX + 0x2a9) == '\0') {                      // 2-tailed: + F_nct(-t_crit)
  fVar2 = (float10)(**(code **)(*(int *)in_ECX + 4))(-*(double *)(in_ECX + 0x3e));
  dVar3 = dVar3 + (double)fVar2;
}
```

- **`[REA]` Merkezî Olmayan $t$ CDF Çekirdeği (`0x4fa7e0` $\rightarrow$ `0x4f9fa0`):**
  Lenth (1989) Algorithm AS 243 (Poisson ağırlıklı tamamlanmamış beta serisi) kullanır; seri `ABS(term) / ABS(sum) <= 5.551115123125783e-17` ($2^{-54}$) veya maksimum `50000` iterasyonda sonlanır.

---

## 6. Örneklem Büyüklüğü Arama Algoritması, Durma Koşulu ve Yuvarlama Kuralı (`[REA]` & `[AJAN]`)

1. **`[REA]` Başlangıç Tahmini ve Paranteze Alma (`0x4dc1b0` & `0x4d35e0`):**
   - `0x4dc130` (`vftable[+0x054]`) minimum örneklem sınırını `minN = 2.0` döndürür (`0x4d35e0` içinde alt taban `2.0 + 1e-6 = 2.000001`).
   - `0x4dc1b0` (`vftable[+0x128]`) normal yaklaşımla $N_{\text{guess}} = (z_{1-\alpha/\text{tails}} + z_{\text{power}})^2 / d_z^2$ hesaplar.
   - `0x4d35e0` (`vftable[+0x064]`) hedef güce ulaşılana kadar üst sınırı `dVar3 = dVar3 + dVar3` (ikiye katlama) ile genişletir.
2. **`[REA]` Brent-Dekker Kök Bulucu ve Durma Koşulu (`0x496aa0` $\rightarrow$ `0x4f9bb0`):**
   - `0x496aa0` fonksiyonu `FUN_004f9bb0(N_low, N_high, 1e-10, 300)` çağrısı yapar.
   - Ancak `0x4f9bb0` içerisindeki assembly (`0x4f9d91`) `1e-10` argümanını `[ESI + 0x8]` alanına kaydettikten sonra döngüde okumaz; `0x005c4390` adresindeki `1.1102230246251565e-16` ($2^{-53}$) sabitini kullanarak `ABS(0.5 * (c - b)) <= ABS(b) * 1.1102230246251565e-16` veya `f(b) == 0.0` olana dek (maksimum `300` iterasyon) tam IEEE-754 `double` hassasiyetinde kök bulur:

```c
// [REA] Kanıt — Procedure: 0x4f9bb0 (Brent-Dekker Root Solver)
dVar14 = ABS(dVar6) * 1.1102230246251565e-16; // [0x005c4390] = 2^-53
dVar13 = (dVar12 - dVar6) * 0.5;
if ((dStack_80 == 0.0) || (ABS(dVar13) <= dVar14)) {
  return (float10)dVar6;
}
```

3. **`[REA]` 10 Ondalık Basamak Ön-Yuvarlamalı Tavan (`ceil`) Kuralı (`0x496a20`, `vftable[29 / +0x074]`):**
   - Sürekli kök $N_{\text{cont}}$ bulunduktan sonra doğrudan `ceil` alınmaz; önce $10^{10}$ ile çarpılıp `floor(x + 0.5)` ile **10. ondalık basamağa yuvarlanır**, $10^{10}$'a bölünür ve ardından `ceil()` alınır:
     $$N = \left\lceil \frac{\lfloor N_{\text{cont}} \times 10^{10} + 0.5 \rfloor}{10^{10}} \right\rceil$$

```c
// [REA] Kanıt — Procedure: 0x496a20 (PowerAnalysis::roundUpSampleSize)
float10 FUN_00496a20(double param_1) {
  double dVar1;
  double *_Y;
  double local_48 [8];
  _Y = local_48;
  local_48[0] = param_1 * 10000000000.0 + 0.5;
  local_48[0] = floor(local_48[0]);
  modf(local_48[0], _Y);
  local_48[0] = local_48[0] / 10000000000.0;
  dVar1 = ceil(local_48[0]);
  return (float10)dVar1;
}
```

---

## 7. Sınır Değerleri ve Geçersiz Girdi Kontrolleri (`[REA]`)

- **`[REA]` `PowerTPairedMean::compute` (`0x4dc2a0`) ve Doğrulayıcı Fonksiyonlar:**
  - `a-priori` modda (`0x4db990`): `ABS(dz) < 1e-05` ise `"In an a priori analysis, the absolute value of the\neffect size be greater than 0.00001."`
  - Her iki modda (`0x4db990`, `0x487b70`): `dz < -20.0 || dz > 20.0` ise `"Effect size dz is outside the admissible range (-20, 20)"`
  - Her iki modda (`0x487530`): `alpha < 1e-07 || alpha > 0.9999999` ise `"Alpha is outside the admissible range (1e-07, 0.9999999)"`
  - `a-priori` modda (`0x488110`): `power < 1e-07 || power > 0.9999999` ise `"Power is outside the admissible range (1e-07, 0.9999999)"`
  - `a-priori` modda (`0x4880e0`): `power < alpha` ise `"Power must be greater than or equal to alpha."`
  - `post-hoc` modda (`0x4dc2a0` satır 2441 $\rightarrow$ `0x488a10`): `N < 3 || N > 2147483646` (`0x7ffffffe`) ise `"Total sample size is outside the admissible range (3, 2147483646)"`
  - Etki büyüklüğü diyaloğunda (`0x52e370`): `sd <= 1e-12` ise `"The standard deviation must be greater than 1e-12"`, `corr <= -0.99999999 || corr > 0.99999999` ise `"Correlation lies outside of admissible range (-1+1e-8,1-1e-8)"`.
