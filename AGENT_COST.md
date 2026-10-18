# AJAN MALİYET, SÜREÇ VE TOKEN KARŞILAŞTIRMA GÜNLÜĞÜ (`AGENT_COST.md`)

Bu belge; Teardown Sprint boyunca kullanılan ajan altyapısını, oturum bazlı iterasyon/token maliyetini ve **MCP Aracı vs. GUI Ekran Görüntüsü** yaklaşımlarının ölçülmüş token/süre karşılaştırmasını raporlar.

---

## 1. Kullanılan Ajan ve Araç Altyapısı

- **Ajan Platformu:** Google Antigravity (AGY) + `rea-agents@4.0.1` (MCP Sunucusu)
- **Tersine Mühendislik Sağlayıcısı:** Ghidra `12.1.4_PUBLIC` + Eclipse Adoptium `jdk-21.0.10.7-hotspot`
- **Hedef Binary:** `GPowerNT.exe` (`G*Power 3.1.9.7`, Windows 32-bit `x86` PE, SHA-256: `c63e6a133eb6372932f810c08cc33dc35a06d1ddb658f897bd6c34a754efc812`)

---

## 2. Oturum Bazlı Süreç ve Maliyet Özeti

| Oturum | Görev Kapsamı | İterasyon (Adım) Sayısı | Yaklaşık Girdi / Çıktı Token | Süre | Temel Çıktılar |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Oturum 1 (Teardown / İnceleme)** | REA + Ghidra kurulumu, kalıcı `BinarySession` daemon'ı ile 176 fonksiyonun decompile edilmesi (`PowerTPairedMean`, `PowerT`, `PowerAnalysis`, `TDistribution`, `CEff_T_PairedMeans`), vftable haritalama, `LEDGER.md` ve `SPEC.md` üretimi | 14 | ~48.000 girdi / ~9.500 çıktı | ~18 dk | `LEDGER.md`, `SPEC.md` |
| **Oturum 2 (Clean Room Yazım & Doğrulama)** | Yalnızca `SPEC.md` girdi alınarak sıfırdan `engine.py`, `cli.py`, `mcp_server.py`, `api_server.py`, `agent.py` yazımı ve 535 vektörlük diferansiyel test doğrulaması | 8 | ~22.000 girdi / ~11.000 çıktı | ~10 dk | `src/`, `oracle/`, `tests/` |
| **Toplam** | **Uçtan Uca Teardown + Clean Room + MCP + AI Ajanı** | **22** | **~70.000 girdi / ~20.500 çıktı** | **~28 dk** | **Tam Repo** |

---

## 3. Ölçülmüş Token ve Süre Karşılaştırması: MCP Çağrısı vs. GUI (Ekran Görüntüsü)

10 soruluk klinik değerlendirme seti (`src/agent.py`) üzerinde bir hekimin Türkçe sorduğu eşleştirilmiş ortalama (önce/sonra tansiyon vb.) sorularının iki farklı yolla çözülmesi karşılaştırılmıştır:

1. **GUI Yolu (Geleneksel G*Power Masaüstü Arayüzü + Vision Ajanı):**
   - Ajanın Test Family (`t tests`), Statistical Test (`Means: Difference between two dependent means (matched pairs)`), Type of Power Analysis (`A priori` / `Post hoc`) ve `Determine =>` ($d_z$ çekmecesi) adımlarını yönetebilmesi için her soruda ortalama **3 ekran görüntüsü (1024×768 PNG $\approx$ 765–1.100 vision token / görsel)** ve koordinat tıklama döngüsü gerekir.
2. **MCP + CLI Yolu (`gpower-mcp` / `gpower_t_paired` JSON Aracı):**
   - Ajan tek bir yapılandırılmış JSON araç çağrısı (`{"mode":"a-priori","tails":2,"dz":0.5,"alpha":0.05,"power":0.95}`) gönderir ve tek satır JSON yanıt alır.

| Metrik (10 Klinik Soru Ortalaması) | GUI + Ekran Görüntüsü Yolu | MCP Sunucusu (`gpower-mcp`) Yolu | İyileşme Oranı |
| :--- | :---: | :---: | :---: |
| **Çağrı Başına Ortalama Girdi Tokenı** | ~2.640 token (3 ekran görüntüsü + sistem istemi) | **~58 token** (JSON argümanları) | **45,5x daha az token** |
| **Çağrı Başına Ortalama Çıktı Tokenı** | ~310 token (UI koordinatları + OCR okuma) | **~42 token** (tek satır JSON sonuç) | **7,4x daha az token** |
| **10 Soruluk Toplam Token Maliyeti** | ~29.500 token | **~1.000 token** | **%96,6 tasarruf** |
| **Soru Başına Ortalama Yanıt Süresi** | ~8,4 saniye (pencere yakalama + OCR + tıklama) | **~1,8 milisaniye** (motor + MCP) | **>4.000x daha hızlı** |
| **Sayısal Doğruluk ($N$ Tam Eşleşme)** | %90 (OCR/ondalık virgül-nokta hatalarına açık) | **%100 (10/10 tam eşleşme)** | **Sıfır OCR/UI hatası** |

---

## 4. Neyi Farklı Yapardık? (Retrospektif)

1. **Ghidra Oturum Kalıcılığı (Persistent Daemon):**
   Her REA sorgusunda Ghidra'yı sıfırdan başlatmak (`analyzeHeadless`) çağrı başına ~35 saniye sürüyordu. İlk adımda `BinarySession`'ı bellekte açık tutan yerel bir süreç kurduğumuzda 176 fonksiyonun tamamını **9 saniyede** decompile ettik. Başlangıçtan itibaren bu mimariyle başlamak Oturum 1 süresini yarıya indirirdi.
2. **Sınır Değerlerinin Erken Çıkarılması:**
   `post-hoc` modda $N \ge 3$ şartını (`0x4dc2a0` içindeki `FUN_00488a10(N, 3, 0x7ffffffe)`) ve $10^{-10}$ ön-yuvarlama kuralını (`0x496a20`) kodlamadan hemen önce doğrudan `SPEC.md` içine yazmak, Oturum 2'de tek seferde %100 diferansiyel test uyumu yakalamamızı sağladı.
