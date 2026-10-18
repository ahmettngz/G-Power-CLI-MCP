# Oturum 1 (İnceleme / Teardown Sprint) İlk Prompt'u

```text
Hedefimiz "C:\Users\ahmet\Desktop\GPower_3.1.9.7_143\GPowerNT.exe" (G*Power 3.1.9.7 Windows x86) ikili dosyasını REA (rea-agents) ve Ghidra 12.1.4 kullanarak Temiz Oda (Clean Room) kurallarına göre incelemek (Oturum 1 — Teardown Sprint).

Takımımızın konusu: Konu #2 — "t testi, eşleştirilmiş ortalama (önce ve sonra tansiyon)" (G*Power'da "t tests" -> "Means: Difference between two dependent means (matched pairs)"), "a-priori" (örneklem büyüklüğü N hesaplama) ve "post-hoc" (ulaşılan güç hesaplama) modları.

Görevler:
1. REA + Ghidra ile GPowerNT.exe içindeki PowerTPairedMean, PowerTOneMean, PowerT, PowerAnalysis, TDistribution ve CEff_T_PairedMeans sınıflarını, vftable tablolarını ve fonksiyon adreslerini bul.
2. Kılavuzda yazmayan davranışları (yuvarlama kuralı, örneklem büyüklüğü arama algoritması ve durma koşulu, serbestlik derecesi df, merkezî olmama parametresi ncp, kritik t ve geçersiz girdi sınır kontrolleri) doğrudan binary'den çıkar.
3. Bulguları [DOK], [REA] (fonksiyon adresi ve kısa kanıt kesitleriyle) ve [AJAN] etiketleriyle LEDGER.md dosyasına yaz.
4. Oturum 2'ye aktarılacak tek belge olan SPEC.md dosyasını Gherkin (Feature/Scenario/Given/When/Then) formatında, hiçbir decompile kodu içermeyecek şekilde hazırla.
```
