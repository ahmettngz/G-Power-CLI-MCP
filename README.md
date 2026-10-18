# GPower CLI-API (t-paired)

This project was developed for the **Software Implementation and Testing (Yazılım Gerçekleme ve Test)** course taught by **Dr. Nurettin Şenyer** ([@seyyah](https://github.com/seyyah)). It is a clean-room reimplementation of the paired-samples t-test calculation engine (`t-paired`) as a command-line tool, MCP server, HTTP API, and clinical agent.

**Implemented Layers:** CLI + MCP Server + AI Agent (Topic 2: Paired Samples t-Test)

## Purpose of the Assignment

Statistical power analysis tools used in healthcare and clinical research mostly rely on desktop graphical interfaces (GUI). For an AI agent to use a GUI-only tool, it has to take screenshots and click coordinates on the screen, which consumes thousands of tokens per query and is prone to reading errors.

The main goal of this assignment is to reverse the traditional workflow (going from binary code to evidence, from evidence to specification, and from specification to clean code) and bring this calculation engine into the agent era by placing it behind a low-token CLI, an MCP server, and a natural-language agent interface.

## Assigned Task (Topic 2)

Our team was assigned **Topic 2: Paired Samples t-Test (`t-paired` - difference between two dependent means, e.g., pre- and post-treatment blood pressure)** for both **a-priori** (computing required sample size `N`) and **post-hoc** (computing achieved statistical power) modes.

What we did step by step:
1. Examined the target binary (`GPowerNT.exe` v3.1.9.7, SHA-256: `c63e6a133eb6372932f810c08cc33dc35a06d1ddb658f897bd6c34a754efc812`) using REA and Ghidra 12.1.4 to extract the underlying formulas, stopping criteria, rounding rules, and input boundaries into `LEDGER.md`.
2. Wrote the behavioral specification and test scenarios in Gherkin format inside `SPEC.md`.
3. Rewrote the calculation engine from scratch in Python following the clean-room rule, and wrapped it with a CLI, MCP server, REST API, and clinical agent.
4. Verified the outputs against reference and scale test vectors (`oracle/` and `tests/`).

## How to Use

No external library installation is required to run the core engine and CLI (Python 3.10+ standard library is sufficient).

### 1. CLI Usage

**A-priori mode (calculate required sample size N):**
```bash
python src/cli.py --test t-paired --mode a-priori --tails 2 --dz 0.5 --alpha 0.05 --power 0.95
```
On Windows, you can also use the batch wrapper directly:
```powershell
.\gpower-clone.bat --test t-paired --mode a-priori --tails 2 --dz 0.5 --alpha 0.05 --power 0.95
```

**Post-hoc mode (calculate achieved power):**
```bash
python src/cli.py --test t-paired --mode post-hoc --tails 2 --dz 0.5 --alpha 0.05 --n 34
```

**Calculating directly from pre/post group parameters (mean1, mean2, sd1, sd2, corr):**
```bash
python src/cli.py --test t-paired --mode a-priori --tails 2 --mean1 140 --mean2 136 --sd1 10 --sd2 10 --corr 0.5 --alpha 0.05 --power 0.90
```

### 2. Clinical Agent Usage

To ask a clinical question in natural language (Turkish or English):
```bash
python src/agent.py "Aynı hastalarda tedavi öncesi ve sonrası tansiyon için dz = 0.5, alpha = 0.05 ve %80 güç ile çift yönlü testte kaç hasta gerekir?"
```

To run the 10-question benchmark set:
```bash
python src/agent.py --benchmark
```

### 3. MCP Server and HTTP API Usage

To start the MCP server (JSON-RPC over stdio):
```bash
python src/mcp_server.py
```

To start the local HTTP REST API server:
```bash
python src/api_server.py --port 8080
```

### 4. Running Tests

```bash
python -m unittest discover -s tests -v
```

## References and Attribution

This project was created for the **Yazılım Gerçekleme ve Test** course given by **Dr. Nurettin Şenyer** (https://github.com/seyyah).
Reference statistical software and methodology:
- Faul, F., Erdfelder, E., Lang, A.-G., & Buchner, A. (2007). *G*Power 3: A flexible statistical power analysis program for the social, behavioral, and biomedical sciences.* Behavior Research Methods, 39, 175-191.
- Faul, F., Erdfelder, E., Buchner, A., & Lang, A.-G. (2009). *Statistical power analyses using G*Power 3.1: Tests for correlation and regression analyses.* Behavior Research Methods, 41, 1149-1160.

---

# GPower CLI-API (t-paired) - Türkçe

Bu proje, **Dr. Nurettin Şenyer** ([@seyyah](https://github.com/seyyah)) tarafından verilen **Yazılım Gerçekleme ve Test** dersi ödevi kapsamında geliştirilmiştir. Eşleştirilmiş örneklem t-testi (`t-paired`) hesaplama motorunun temiz oda (clean room) kurallarıyla komut satırı aracı (CLI), MCP sunucusu, HTTP API ve klinik ajan olarak yeniden yazılmış halidir.

**Gerçekleştirilen Katmanlar:** CLI + MCP Sunucusu + AI Ajanı (2. Konu: Eşleştirilmiş Ortalama t-Testi)

## Ödevin Amacı

Sağlık ve klinik araştırmalarda kullanılan istatistiksel güç analizi araçları genellikle yalnızca grafik arayüz (GUI) üzerinden çalışır. Bir yapay zeka ajanının sadece arayüzü olan bir programı kullanabilmesi için sürekli ekran görüntüsü alması ve ekranda tıklama yapması gerekir. Bu durum her sorguda binlerce token harcanmasına ve okuma hatalarına yol açar.

Bu ödevin amacı; klasik yazılım geliştirme sürecini tersine çevirerek (koddan kanıta, kanıttan spesifikasyona ve oradan temiz koda giderek) mevcut hesaplama motorunu az token harcayan bir CLI, bir MCP sunucusu ve doğal dille soru sorulabilen bir ajan yapısının arkasına taşımaktır.

## Ödev İçin İstenilen Görev (2. Konu)

Takımımıza **2. Konu: t testi, eşleştirilmiş ortalama (önce ve sonra tansiyon)** test ailesinin **a-priori** (örneklem büyüklüğü `N` hesaplama) ve **post-hoc** (ulaşılan gücü hesaplama) modları verilmiştir.

Süreç boyunca yaptıklarımız:
1. Hedef uygulama (`GPowerNT.exe` v3.1.9.7, SHA-256: `c63e6a133eb6372932f810c08cc33dc35a06d1ddb658f897bd6c34a754efc812`) REA ve Ghidra 12.1.4 ile incelenerek kullanılan formüller, durma kriterleri, yuvarlama kuralları ve sınır değerleri kanıtlarıyla `LEDGER.md` dosyasına çıkarıldı.
2. Elde edilen bulgulardan Gherkin formatında `SPEC.md` davranışsal spesifikasyon dosyası oluşturuldu.
3. Temiz oda kuralına uygun olarak sadece `SPEC.md` referans alınarak hesaplama motoru, CLI, MCP sunucusu, REST API ve klinik ajan Python ile sıfırdan yazıldı.
4. Üretilen sonuçlar referans ve ölçek veri setleriyle (`oracle/` ve `tests/`) test edilerek doğrulandı.

## Kullanım

Uygulamayı çalıştırmak için harici bir kütüphane kurulumuna gerek yoktur (Python 3.10+ standart kütüphanesi yeterlidir).

### 1. CLI Kullanımı

**A-priori modu (gereken örneklem büyüklüğü N hesabı):**
```bash
python src/cli.py --test t-paired --mode a-priori --tails 2 --dz 0.5 --alpha 0.05 --power 0.95
```
Windows üzerinde doğrudan `.bat` dosyasıyla da çalıştırabilirsiniz:
```powershell
.\gpower-clone.bat --test t-paired --mode a-priori --tails 2 --dz 0.5 --alpha 0.05 --power 0.95
```

**Post-hoc modu (ulaşılan istatistiksel güç hesabı):**
```bash
python src/cli.py --test t-paired --mode post-hoc --tails 2 --dz 0.5 --alpha 0.05 --n 34
```

**Önce ve sonra grup parametrelerinden (mean1, mean2, sd1, sd2, corr) doğrudan hesaplama:**
```bash
python src/cli.py --test t-paired --mode a-priori --tails 2 --mean1 140 --mean2 136 --sd1 10 --sd2 10 --corr 0.5 --alpha 0.05 --power 0.90
```

### 2. Klinik Ajan Kullanımı

Doğal dille (Türkçe veya İngilizce) soru sormak için:
```bash
python src/agent.py "Aynı hastalarda tedavi öncesi ve sonrası tansiyon için dz = 0.5, alpha = 0.05 ve %80 güç ile çift yönlü testte kaç hasta gerekir?"
```

10 soruluk değerlendirme setini çalıştırmak için:
```bash
python src/agent.py --benchmark
```

### 3. MCP Sunucusu ve HTTP API Kullanımı

MCP sunucusunu başlatmak için:
```bash
python src/mcp_server.py
```

Yerel HTTP REST API sunucusunu başlatmak için:
```bash
python src/api_server.py --port 8080
```

### 4. Testleri Çalıştırma

```bash
python -m unittest discover -s tests -v
```

## Kaynakça ve Atıf

Bu proje, **Dr. Nurettin Şenyer** (https://github.com/seyyah) tarafından yürütülen **Yazılım Gerçekleme ve Test** dersi kapsamında eğitim amacıyla oluşturulmuştur.
İncelenen orijinal aracın yazarları:
- Faul, F., Erdfelder, E., Lang, A.-G., & Buchner, A. (2007). *G*Power 3: A flexible statistical power analysis program for the social, behavioral, and biomedical sciences.* Behavior Research Methods, 39, 175-191.
- Faul, F., Erdfelder, E., Buchner, A., & Lang, A.-G. (2009). *Statistical power analyses using G*Power 3.1: Tests for correlation and regression analyses.* Behavior Research Methods, 41, 1149-1160.
