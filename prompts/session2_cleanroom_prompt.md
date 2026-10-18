# Oturum 2 (Temiz Oda Kodlama / Clean Room Implementation) İlk Prompt'u

```text
Temiz Oda (Clean Room) Oturum 2'deyiz. Elimizde yalnızca SPEC.md ve CONTRACT.md belgeleri var; herhangi bir Ghidra veya decompile çıktısına erişimimiz yok.

SPEC.md içerisindeki matematiksel kuralları ve Gherkin kabul kriterlerini birebir karşılayan, GitHub'a yüklenmeye hazır bir Python projesi geliştir:
1. src/engine.py: Eşleştirilmiş örneklem t-testi (t-paired) için a-priori (N hesaplama, Brent-Dekker kök bulucu ve 1e-10 ön-yuvarlamalı ceil kuralı), post-hoc (güç hesaplama, Lenth AS 243 merkezî olmayan t CDF) ve grup/fark parametrelerinden (önce ve sonra tansiyon: mean1, mean2, sd1, sd2, corr) etki büyüklüğü dz hesaplama motoru.
2. src/cli.py: `gpower-clone --test t-paired --mode a-priori|post-hoc ...` sözleşmesine uygun, tek satır JSON çıktı ve geçersiz girdide `{"error":"..."}` + sıfırdan farklı çıkış kodu döndüren CLI.
3. src/mcp_server.py ve src/api_server.py: Aynı hesap motorunu çağıran ince MCP (Model Context Protocol) sunucusu ve REST API adaptörü.
4. src/agent.py: Hekimin Türkçe veya İngilizce sorduğu klinik soruyu Sistem-1 sınıflandırıcıyla (t2-indep, t-paired, anova-oneway, chi2-contingency, multireg-r2, ambiguous, unsupported; güven eşiği >= 0.75) sınıflandırıp MCP üzerinden motoru çağıran AI ajanı ve 10 soruluk değerlendirme seti.
5. oracle/ ve tests/: G*Power referans vektörleri, 500+ ölçek vektörü ve tüm Gherkin senaryolarını doğrulayan diferansiyel test paketi.
```
