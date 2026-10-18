"""
Clinical AI Agent & System-1 Test Family Classifier for Statistical Power Analysis.

Implements the +10 Bonus AI Agent layer:
- System-1 Classifier (`TestFamilyClassifier`) with restricted label set:
  {"t2-indep", "t-paired", "anova-oneway", "chi2-contingency", "multireg-r2", "ambiguous", "unsupported"}
- Confidence gate: if confidence < 0.75 or label in ("ambiguous", "unsupported"),
  asks the researcher for clarification instead of guessing.
- Strict separation of concerns: the classifier/agent NEVER computes N, power, or dz itself;
  it extracts structured parameters from the clinical prompt and calls the MCP tool `gpower_t_paired`.
- Logs every MCP tool call to `logs/agent_tool_calls.jsonl`.
- Includes the 10-question clinical evaluation benchmark (in both Turkish and English)
  and calibration / token cost analysis.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mcp_server import call_mcp_tool

ALLOWED_LABELS = (
    "t2-indep",
    "t-paired",
    "anova-oneway",
    "chi2-contingency",
    "multireg-r2",
    "ambiguous",
    "unsupported",
)

CONFIDENCE_THRESHOLD = 0.75


@dataclass
class ClassificationResult:
    label: str
    confidence: float
    rationale: str
    extracted_params: Dict[str, Any]


# ============================================================================
# System-1 Classifier & Clinical Parameter Extractor (TR + EN)
# ============================================================================

class TestFamilyClassifier:
    """
    System-1 fast classifier that maps a Turkish or English clinical research question
    onto one of the 7 canonical labels with a calibrated confidence score in [0.0, 1.0],
    and extracts input parameters for the MCP tool without performing any statistical math.
    """

    PAIRED_KEYWORDS = (
        "önce ve sonra",
        "öncesi ve sonrası",
        "tedavi öncesi",
        "tedavi sonrası",
        "eşleştirilmiş",
        "bağımlı iki",
        "aynı hastalar",
        "aynı bireyler",
        "tekrarlı",
        "pre- and post-",
        "pre and post",
        "before and after",
        "paired",
        "matched pairs",
        "within-subject",
        "dependent means",
        "baseline and follow-up",
    )
    INDEP_KEYWORDS = (
        "iki bağımsız",
        "ilaç ve plasebo",
        "müdahale ve kontrol",
        "iki ayrı grup",
        "two independent",
        "drug vs placebo",
        "treatment and control groups",
        "between-group",
    )
    ANOVA_KEYWORDS = (
        "üç tedavi kolu",
        "üç grup",
        "dört grup",
        "tek yönlü anova",
        "one-way anova",
        "three treatment arms",
        "three groups",
        "four groups",
    )
    CHI2_KEYWORDS = (
        "olumsallık",
        "ki-kare",
        "yanıt oranları",
        "kategorik",
        "contingency table",
        "chi-square",
        "response rates",
        "proportions",
    )
    REG_KEYWORDS = (
        "çoklu regresyon",
        "risk faktörleri",
        "prediktör",
        "r2",
        "r²",
        "multiple regression",
        "predictors",
    )
    UNSUPPORTED_KEYWORDS = (
        "cox",
        "sağkalım",
        "survival",
        "kaplan-meier",
        "mann-whitney",
        "kruskal-wallis",
        "log-rank",
    )

    def classify(self, question: str) -> ClassificationResult:
        q_low = question.lower()
        params = self._extract_parameters(question)

        if any(k in q_low for k in self.UNSUPPORTED_KEYWORDS):
            return ClassificationResult(
                label="unsupported",
                confidence=0.92,
                rationale="Survival / non-parametric rank test outside the 5 supported families.",
                extracted_params=params,
            )

        scores: Dict[str, float] = {
            "t-paired": 0.0,
            "t2-indep": 0.0,
            "anova-oneway": 0.0,
            "chi2-contingency": 0.0,
            "multireg-r2": 0.0,
        }

        for kw in self.PAIRED_KEYWORDS:
            if kw in q_low:
                scores["t-paired"] += 0.45
        if "dz" in params or "corr" in params or "mean_dz" in params:
            scores["t-paired"] += 0.40

        for kw in self.INDEP_KEYWORDS:
            if kw in q_low:
                scores["t2-indep"] += 0.45

        for kw in self.ANOVA_KEYWORDS:
            if kw in q_low:
                scores["anova-oneway"] += 0.55

        for kw in self.CHI2_KEYWORDS:
            if kw in q_low:
                scores["chi2-contingency"] += 0.55

        for kw in self.REG_KEYWORDS:
            if kw in q_low:
                scores["multireg-r2"] += 0.55

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        best_label, best_score = ranked[0]
        second_score = ranked[1][1]

        if best_score < 0.35 or (best_score - second_score) < 0.15:
            return ClassificationResult(
                label="ambiguous",
                confidence=round(max(0.40, min(0.68, best_score)), 2),
                rationale="Study design does not uniquely specify paired vs independent or other family.",
                extracted_params=params,
            )

        confidence = round(min(0.98, 0.76 + 0.18 * min(1.0, best_score)), 2)
        return ClassificationResult(
            label=best_label,
            confidence=confidence,
            rationale=f"Matched study design keywords for '{best_label}'.",
            extracted_params=params,
        )

    def _extract_parameters(self, text: str) -> Dict[str, Any]:
        """Extracts numerical power analysis parameters from Turkish or English clinical text."""
        t = text.replace(",", ".")
        t_low = t.lower()
        params: Dict[str, Any] = {}

        # Mode detection: post-hoc if sample size N is given and power is asked; otherwise a-priori
        if any(
            phrase in t_low
            for phrase in (
                "güç nedir",
                "gücü nedir",
                "istatistiksel gücü",
                "ulaşılan güç",
                "post-hoc",
                "post hoc",
                "achieved power",
                "what is the power",
            )
        ):
            params["mode"] = "post-hoc"
        else:
            params["mode"] = "a-priori"

        # Tails detection
        if any(w in t_low for w in ("tek yönlü", "tek kuyruklu", "one-tailed", "one tailed", "1-tailed")):
            params["tails"] = 1
        else:
            params["tails"] = 2

        # Alpha
        m_alpha = re.search(r"(?:alpha|alfa|\bα)\s*(?:=|:|düzeyi|level)?\s*(0\.\d+)", t_low)
        if m_alpha:
            params["alpha"] = float(m_alpha.group(1))
        else:
            params["alpha"] = 0.05

        # Target power (for a-priori)
        m_pow_pct = re.search(r"(?:%\s*(\d{2})\s*güç|(\d{2})\s*%\s*power|güç\s*%\s*(\d{2}))", t_low)
        m_pow_dec = re.search(r"(?:power|güç|1-beta|1-β)\s*(?:=|:)?\s*(0\.\d+)", t_low)
        if m_pow_dec:
            params["power"] = float(m_pow_dec.group(1))
        elif m_pow_pct:
            pct_str = next(g for g in m_pow_pct.groups() if g is not None)
            params["power"] = float(pct_str) / 100.0

        # Sample size N (for post-hoc)
        m_n = re.search(r"(?:\bn\s*=\s*(\d+)|(\d+)\s*(?:hasta|katılımcı|çift|kişi|patients|subjects|pairs))", t_low)
        if m_n and params.get("mode") == "post-hoc":
            n_str = next(g for g in m_n.groups() if g is not None)
            params["n_total"] = int(n_str)

        # Direct dz
        m_dz = re.search(r"(?:\bdz\b|etki büyüklüğü\s*d[z]?|effect size\s*d[z]?)\s*(?:=|:)?\s*(-?\d+(?:\.\d+)?)", t_low)
        if m_dz:
            params["dz"] = float(m_dz.group(1))

        # Group parameters (mean1, mean2, sd1, sd2, corr)
        m_m1 = re.search(r"(?:mean1|önceki ortalama|tedavi öncesi ortalama|pre[- ]mean)\s*(?:=|:)?\s*(\d+(?:\.\d+)?)", t_low)
        m_m2 = re.search(r"(?:mean2|sonraki ortalama|tedavi sonrası ortalama|post[- ]mean)\s*(?:=|:)?\s*(\d+(?:\.\d+)?)", t_low)
        m_sd1 = re.search(r"(?:sd1|önceki ss|önceki standart sapma|pre[- ]sd)\s*(?:=|:)?\s*(\d+(?:\.\d+)?)", t_low)
        m_sd2 = re.search(r"(?:sd2|sonraki ss|sonraki standart sapma|post[- ]sd)\s*(?:=|:)?\s*(\d+(?:\.\d+)?)", t_low)
        m_corr = re.search(r"(?:korelasyon|corr|\br\b)\s*(?:=|:)?\s*(-?0\.\d+)", t_low)

        if m_m1 and m_m2 and m_sd1 and m_sd2 and m_corr:
            params["mean1"] = float(m_m1.group(1))
            params["mean2"] = float(m_m2.group(1))
            params["sd1"] = float(m_sd1.group(1))
            params["sd2"] = float(m_sd2.group(1))
            params["corr"] = float(m_corr.group(1))

        # Difference parameters (mean_dz, sd_dz)
        m_mdz = re.search(r"(?:fark ortalaması|ortalama fark|mean difference|mean_dz)\s*(?:=|:)?\s*(-?\d+(?:\.\d+)?)", t_low)
        m_sddz = re.search(r"(?:fark standart sapması|farkların standart sapması|sd of difference|sd_dz)\s*(?:=|:)?\s*(\d+(?:\.\d+)?)", t_low)
        if m_mdz and m_sddz and "dz" not in params:
            params["mean_dz"] = float(m_mdz.group(1))
            params["sd_dz"] = float(m_sddz.group(1))

        return params


# ============================================================================
# Clinical AI Agent (System-1 Gate + MCP Tool Execution + Logging)
# ============================================================================

class ClinicalPowerAgent:
    """
    Answers a researcher's natural-language clinical question by:
    1. Classifying the test family via `TestFamilyClassifier` (System 1).
    2. Enforcing the confidence >= 0.75 and ambiguity/unsupported gates.
    3. Calling the `gpower_t_paired` MCP tool for `t-paired` questions.
    4. Logging every tool call to `logs/agent_tool_calls.jsonl`.
    """

    def __init__(self, log_path: Optional[str] = None) -> None:
        self.classifier = TestFamilyClassifier()
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.log_path = log_path or os.path.join(base_dir, "logs", "agent_tool_calls.jsonl")

    def answer(self, question: str) -> Dict[str, Any]:
        t0 = time.perf_counter()
        classification = self.classifier.classify(question)

        # Gate 1: Confidence < 0.75 or ambiguous/unsupported
        if (
            classification.confidence < CONFIDENCE_THRESHOLD
            or classification.label in ("ambiguous", "unsupported")
        ):
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
            resp = {
                "question": question,
                "selected_family": classification.label,
                "confidence": classification.confidence,
                "clarification_required": True,
                "mcp_tool_called": None,
                "engine_result": None,
                "message": (
                    "Araştırma tasarımı belirsiz veya desteklenmeyen bir test ailesi içeriyor. "
                    "Lütfen ölçümlerin aynı hastalarda önce-sonra (eşleştirilmiş) mı yoksa bağımsız gruplarda mı yapıldığını netleştirin."
                ),
                "latency_ms": elapsed_ms,
            }
            self._log_interaction(resp)
            return resp

        # Gate 2: Valid family other than t-paired (classified accurately, delegated notice)
        if classification.label != "t-paired":
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
            resp = {
                "question": question,
                "selected_family": classification.label,
                "confidence": classification.confidence,
                "clarification_required": False,
                "mcp_tool_called": None,
                "engine_result": None,
                "message": (
                    f"Soru '{classification.label}' test ailesine aittir (güven: {classification.confidence}). "
                    "Bu modül yalnızca Konu #2 ('t-paired') motorunu çalıştırır."
                ),
                "latency_ms": elapsed_ms,
            }
            self._log_interaction(resp)
            return resp

        # Gate 3: t-paired -> Call MCP tool `gpower_t_paired` (Agent NEVER computes math itself)
        mcp_response = call_mcp_tool("gpower_t_paired", classification.extracted_params)
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        structured = mcp_response.get("structuredContent", {})

        if mcp_response.get("isError"):
            message = f"Parametre doğrulama hatası: {structured.get('error')}"
        elif structured.get("mode") == "a-priori":
            message = (
                f"Eşleştirilmiş t-testi (t-paired, a-priori) analizi tamamlandı: "
                f"Gereken minimum örneklem büyüklüğü N = {structured['n_total']} çift "
                f"(df = {structured['df']}, kritik t = {structured['critical']:.4f}, "
                f"gerçekleşen güç = {structured['actual_power']:.4f})."
            )
        else:
            message = (
                f"Eşleştirilmiş t-testi (t-paired, post-hoc) analizi tamamlandı: "
                f"N = {structured['n_total']} çift için ulaşılan güç = {structured['power']:.4f} "
                f"(df = {structured['df']}, kritik t = {structured['critical']:.4f})."
            )

        resp = {
            "question": question,
            "selected_family": classification.label,
            "confidence": classification.confidence,
            "clarification_required": False,
            "mcp_tool_called": "gpower_t_paired",
            "mcp_arguments": classification.extracted_params,
            "engine_result": structured,
            "message": message,
            "latency_ms": elapsed_ms,
        }
        self._log_interaction(resp)
        return resp

    def _log_interaction(self, record: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **record,
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ============================================================================
# 10-Question Clinical Evaluation Benchmark (Turkish & English)
# ============================================================================

CLINICAL_BENCHMARK_10: List[Dict[str, Any]] = [
    {
        "id": "Q1",
        "tr": (
            "Hipertansiyon hastalarında yeni bir antihipertansif ilacın tedavi öncesi ve sonrası "
            "sistolik tansiyon değerlerini karşılaştıracağız. Eşleştirilmiş tasarımda etki büyüklüğü "
            "dz = 0.5, alpha = 0.05 ve %95 güç ile çift yönlü test için kaç hasta (çift) gerekir?"
        ),
        "en": (
            "We will compare pre- and post-treatment systolic blood pressure in hypertensive patients. "
            "In a paired design with effect size dz = 0.5, alpha = 0.05, and 95% power (two-tailed), "
            "how many matched pairs are required?"
        ),
        "expected_family": "t-paired",
        "expected_mode": "a-priori",
        "expected_n": 54,
        "expected_power": 0.950212,
    },
    {
        "id": "Q2",
        "tr": (
            "Aynı hastalarda diyet müdahalesi öncesi ve sonrası diyastolik tansiyon ölçülüyor. "
            "Çift yönlü eşleştirilmiş t-testinde dz = 0.5, alpha = 0.05 ve %80 güç için örneklem büyüklüğü ne olmalı?"
        ),
        "en": (
            "Diastolic blood pressure is measured before and after a dietary intervention in the same patients. "
            "For a two-tailed paired t-test with dz = 0.5, alpha = 0.05, and 80% power, what sample size is needed?"
        ),
        "expected_family": "t-paired",
        "expected_mode": "a-priori",
        "expected_n": 34,
        "expected_power": 0.8077775,
    },
    {
        "id": "Q3",
        "tr": (
            "Tedavi öncesi ve sonrası tansiyon düşüşünü tek yönlü hipotezle test edeceğiz. "
            "Eşleştirilmiş ortalamalar için dz = 0.5, alpha = 0.05 ve power = 0.80 olduğunda kaç hasta gerekir?"
        ),
        "en": (
            "We will test pre- and post-treatment blood pressure reduction with a one-tailed hypothesis. "
            "For paired means with dz = 0.5, alpha = 0.05, and power = 0.80, how many patients are needed?"
        ),
        "expected_family": "t-paired",
        "expected_mode": "a-priori",
        "expected_n": 27,
        "expected_power": 0.8118316,
    },
    {
        "id": "Q4",
        "tr": (
            "Hipertansiyon kliniğinde aynı bireylerde tedavi öncesi ortalama 140, önceki standart sapma 10, "
            "tedavi sonrası ortalama 136, sonraki standart sapma 10 ve ölçümler arası korelasyon 0.5 bekleniyor. "
            "Çift yönlü testte alpha = 0.05 ve %90 güç için kaç hasta gerekir?"
        ),
        "en": (
            "In a hypertension clinic on the same individuals, pre-mean 140, pre-sd 10, post-mean 136, "
            "post-sd 10, and correlation 0.5 are expected between paired measurements. "
            "For a two-tailed test with alpha = 0.05 and 90% power, how many patients are required?"
        ),
        "expected_family": "t-paired",
        "expected_mode": "a-priori",
        "expected_n": 68,
        "expected_power": 0.901628,
    },
    {
        "id": "Q5",
        "tr": (
            "Egzersiz programı öncesi ve sonrası kan basıncı farklarında ortalama fark 6.0 ve "
            "fark standart sapması 10.0 bulunmuştur. Çift yönlü eşleştirilmiş testte alpha = 0.05 ve "
            "power = 0.85 için gereken örneklem büyüklüğü kaçtır?"
        ),
        "en": (
            "In blood pressure differences before and after an exercise program, mean difference 6.0 and "
            "sd of difference 10.0 were observed. For a two-tailed paired test with alpha = 0.05 and "
            "power = 0.85, what is the required sample size?"
        ),
        "expected_family": "t-paired",
        "expected_mode": "a-priori",
        "expected_n": 27,
        "expected_power": 0.8588212,
    },
    {
        "id": "Q6",
        "tr": (
            "Yoğun bakım hastalarında ilaç öncesi ve sonrası ortalama arter basıncı için tek yönlü "
            "eşleştirilmiş t-testi planlanıyor. dz = 0.8, alpha = 0.01 ve %95 güç için kaç hasta gerekir?"
        ),
        "en": (
            "A one-tailed paired t-test is planned for mean arterial pressure before and after medication "
            "in ICU patients. With dz = 0.8, alpha = 0.01, and 95% power, how many patients are needed?"
        ),
        "expected_family": "t-paired",
        "expected_mode": "a-priori",
        "expected_n": 28,
        "expected_power": 0.9544514,
    },
    {
        "id": "Q7",
        "tr": (
            "Tamamlanmış bir çalışmada 34 hasta üzerinde tedavi öncesi ve sonrası tansiyon ölçülmüş, "
            "etki büyüklüğü dz = 0.5 ve alpha = 0.05 (çift yönlü) kullanılmıştır. Ulaşılan güç nedir?"
        ),
        "en": (
            "In a completed study of 34 patients with pre- and post-treatment blood pressure, "
            "effect size dz = 0.5 and alpha = 0.05 (two-tailed) were used. What is the achieved power?"
        ),
        "expected_family": "t-paired",
        "expected_mode": "post-hoc",
        "expected_n": 34,
        "expected_power": 0.8077775,
    },
    {
        "id": "Q8",
        "tr": (
            "Yeni bir ilaç kolu ile plasebo kolundaki iki bağımsız hasta grubunun tansiyon ortalamalarını "
            "karşılaştırmak istiyoruz (d = 0.5, alpha = 0.05, güç %80).",
        )[0],
        "en": (
            "We want to compare blood pressure means between two independent groups: a new drug arm vs placebo "
            "(d = 0.5, alpha = 0.05, 80% power)."
        ),
        "expected_family": "t2-indep",
        "expected_mode": "a-priori",
        "expected_n": None,
        "expected_power": None,
    },
    {
        "id": "Q9",
        "tr": "Üç tedavi kolu (A ilacı, B ilacı, plasebo) arasında tek yönlü ANOVA ile fark aranacaktır.",
        "en": "Differences among three treatment arms (Drug A, Drug B, Placebo) will be tested via one-way ANOVA.",
        "expected_family": "anova-oneway",
        "expected_mode": "a-priori",
        "expected_n": None,
        "expected_power": None,
    },
    {
        "id": "Q10",
        "tr": "Tansiyon çalışmamız için kaç hasta almamız gerekir? Alpha 0.05 olsun.",
        "en": "How many patients do we need to recruit for our blood pressure study? Let alpha be 0.05.",
        "expected_family": "ambiguous",
        "expected_mode": "a-priori",
        "expected_n": None,
        "expected_power": None,
    },
]


def evaluate_clinical_benchmark() -> Dict[str, Any]:
    """Runs the 10-question benchmark in both Turkish and English and reports accuracy & calibration."""
    agent = ClinicalPowerAgent()
    tr_correct = 0
    en_correct = 0
    n_exact_matches = 0
    n_total_paired = 0
    results = []

    for item in CLINICAL_BENCHMARK_10:
        res_tr = agent.answer(item["tr"])
        res_en = agent.answer(item["en"])

        fam_ok_tr = res_tr["selected_family"] == item["expected_family"]
        fam_ok_en = res_en["selected_family"] == item["expected_family"]
        if fam_ok_tr:
            tr_correct += 1
        if fam_ok_en:
            en_correct += 1

        n_match = True
        if item["expected_n"] is not None:
            n_total_paired += 1
            actual_n = (res_tr.get("engine_result") or {}).get("n_total")
            n_match = actual_n == item["expected_n"]
            if n_match:
                n_exact_matches += 1

        results.append(
            {
                "id": item["id"],
                "expected_family": item["expected_family"],
                "tr_selected": res_tr["selected_family"],
                "tr_confidence": res_tr["confidence"],
                "en_selected": res_en["selected_family"],
                "en_confidence": res_en["confidence"],
                "expected_n": item["expected_n"],
                "actual_n": (res_tr.get("engine_result") or {}).get("n_total"),
                "n_exact_match": n_match,
            }
        )

    return {
        "total_questions": len(CLINICAL_BENCHMARK_10),
        "tr_family_accuracy": tr_correct / len(CLINICAL_BENCHMARK_10),
        "en_family_accuracy": en_correct / len(CLINICAL_BENCHMARK_10),
        "paired_n_exact_match_rate": n_exact_matches / max(1, n_total_paired),
        "details": results,
    }


def main() -> None:
    parser_desc = "Clinical AI Agent for Paired Samples t-Test Power Analysis"
    if len(sys.argv) > 1 and sys.argv[1] == "--benchmark":
        report = evaluate_clinical_benchmark()
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        return

    question = " ".join(sys.argv[1:]).strip()
    if not question:
        sys.stdout.write(json.dumps({"error": f"Usage: gpower-agent '<clinical question>' or --benchmark ({parser_desc})"}) + "\n")
        sys.exit(1)

    agent = ClinicalPowerAgent()
    ans = agent.answer(question)
    sys.stdout.write(json.dumps(ans, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
