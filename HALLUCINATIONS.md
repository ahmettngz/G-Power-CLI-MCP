# HALÜSİNASYON VE YANILGI GÜNLÜĞÜ (`HALLUCINATIONS.md`)

Bu belge, Teardown Sprint ve Clean Room yeniden yazım sürecinde ajanın veya standart istatistiksel varsayımların **yanıldığı en az 2 kritik noktayı**, bunların **nasıl fark edildiğini** ve **hangi test / REA kanıtıyla yakalandığını** kayıt altına alır.

---

## Halüsinasyon #1: Standart `math.ceil(N_cont)` Varsayımı vs. G*Power'ın $10^{-10}$ Ön-Yuvarlamalı `ceil` Kuralı

- **İlk Varsayım (Halüsinasyon):**
  Kılavuzdaki (`[DOK]`) açıklamalara dayanarak ajan ilk aşamada sürekli örneklem büyüklüğü $N_{\text{cont}}$ çözüldükten sonra doğrudan `math.ceil(N_cont)` ile yukarı yuvarlandığını varsaydı.
- **Nasıl Fark Edildi?**
  1. `GPowerNT.exe` üzerinde REA + Ghidra ile `PowerAnalysis::solveSampleSize` (`0x496aa0`) fonksiyonu incelendiğinde, kök bulunduktan sonra doğrudan `ceil()` çağrılmadığı, bunun yerine sanal tablo slotu `vftable[+0x074]` (`0x496a20`) üzerinden özel bir yuvarlama fonksiyonunun çağrıldığı görüldü:
     ```c
     local_48[0] = param_1 * 10000000000.0 + 0.5;
     local_48[0] = floor(local_48[0]);
     local_48[0] = local_48[0] / 10000000000.0;
     dVar1 = ceil(local_48[0]);
     ```
  2. Ayrıca `0x4f9bb0` (Brent-Dekker çözücüsü) incelendiğinde, fonksiyon imzasında `1e-10` tolerans parametresi geçilmesine rağmen assembly kodunda (`0x4f9d91`) bu parametrenin okunmadığı ve $2^{-53}$ (`1.1102230246251565e-16`) yarı makine epsilonuna kadar iterasyon yapıldığı ortaya çıktı.
- **Hangi Test Yakaladı?**
  `SPEC.md` içerisindeki **"Scenario: 10 Ondalik Basamak On-Yuvarlamali Tavan (Ceil) Kurali Kontrolu"** ve `tests/test_differential.py::test_boundary_exact_integer_power_rounding` testi:
  Hedef güç tam olarak $N=34$'ün ürettiği güç (`0.80777751866...`) veya sayısal çözücünün `34.00000000002` döndürdüğü sınır durumunda, saf `math.ceil(N_cont)` yanlışlıkla `N = 35` döndürürken, $10^{-10}$ ön-yuvarlamalı `ceil` kuralı G*Power ile birebir aynı şekilde `N = 34` döndürmektedir.

---

## Halüsinasyon #2: `Post-Hoc` Modda Minimum Örneklem Büyüklüğünün $N = 2$ ($\text{df} = 1$) Olduğu Varsayımı

- **İlk Varsayım (Halüsinasyon):**
  Matematiksel olarak eşleştirilmiş t-testinde serbestlik derecesi $\text{df} = N - 1 \ge 1$ olduğundan, hem istatistik literatürüne hem de `PowerTOneMean::getMinSampleSize` (`0x4dc130`, `return 2.0`) fonksiyonuna bakarak `post-hoc` modda da $N = 2$ girdisinin geçerli olacağı varsayıldı.
- **Nasıl Fark Edildi?**
  `PowerTPairedMean::compute` (`0x4dc2a0`) fonksiyonunun `case 2` (`post-hoc`) dalı decompile edildiğinde, satır 2441'de toplam örneklem büyüklüğü doğrulayıcısı `FUN_00488a10(N, 3, 0x7ffffffe)` çağrısının alt sınır olarak `2` değil, **sabit `3`** kullandığı keşfedildi!
- **Hangi Test Yakaladı?**
  `SPEC.md` içerisindeki **"Scenario: Post-Hoc Modda Gecersiz Orneklem Buyuklugu Hatasi (N < 3)"** ve `tests/test_differential.py::test_posthoc_n2_rejected`:
  `--mode post-hoc --n 2` verildiğinde G*Power `"Total sample size is outside the admissible range (3, 2147483646)"` hatası üretmektedir.

---

## Halüsinasyon #3: Farklardan $d_z$ Hesabı ile Grup Parametrelerinden $d_z$ Hesabının İşaret Davranışı

- **İlk Varsayım (Halüsinasyon):**
  Etki büyüklüğü penceresinde (`CEff_T_PairedMeans`) her iki hesaplama modunun da ($\mu_z/\sigma_z$ ve $(\mu_1-\mu_2)/\sigma_z$) aynı işaret kuralını (her ikisinde de mutlak değer veya her ikisinde de işaretli değer) kullandığı düşünüldü.
- **Nasıl Fark Edildi?**
  `CEff_T_PairedMeans::OnCalculate` (`0x52e370`) fonksiyonu decompile edildiğinde:
  - Mod 0 (`tdm_inmode == 0`, farklardan hesaplama): `dVar5 = mean_dz / sd_dz` (işaretli, `ABS` yok),
  - Mod 1 (`tdm_inmode == 1`, grup parametrelerinden hesaplama): `dVar5 = ABS(mean1 - mean2) / sqrt(...)` (`ABS` var!)
  olduğu doğrudan binary kanıtıyla (`[REA]`) tespit edildi.
- **Hangi Test Yakaladı?**
  `tests/test_differential.py::test_effect_size_calculator_sign_behavior` testi ile doğrulandı.
