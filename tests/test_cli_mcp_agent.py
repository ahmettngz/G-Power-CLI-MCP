"""
CLI, MCP Server, REST API Equivalence & Clinical AI Agent Benchmark Tests (`tests/test_cli_mcp_agent.py`).

Verifies:
1. CLI (`src/cli.py`) == MCP (`src/mcp_server.py`) == Engine (`src/engine.py`) output identity.
2. CLI exit codes and single-line JSON formatting for valid and invalid inputs.
3. MCP JSON-RPC 2.0 protocol (`initialize`, `tools/list`, `tools/call`).
4. 10-question Clinical AI Agent benchmark in both Turkish and English (`tr_family_accuracy == 1.0`,
   `en_family_accuracy == 1.0`, `paired_n_exact_match_rate == 1.0`).
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from src.agent import ClinicalPowerAgent, evaluate_clinical_benchmark
from src.cli import run_cli
from src.engine import calculate_t_paired
from src.mcp_server import call_mcp_tool, handle_jsonrpc_request


class TestCLIMCPEquivalence(unittest.TestCase):
    """Proves that CLI and MCP return the exact same JSON result from the shared engine."""

    def test_cli_and_mcp_identical_outputs_apriori(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = run_cli(
                ["--test", "t-paired", "--mode", "a-priori", "--tails", "2", "--dz", "0.5", "--alpha", "0.05", "--power", "0.95"]
            )
        self.assertEqual(code, 0)
        cli_json = json.loads(buf.getvalue().strip())

        mcp_res = call_mcp_tool(
            "gpower_t_paired",
            {"mode": "a-priori", "tails": 2, "dz": 0.5, "alpha": 0.05, "power": 0.95},
        )
        self.assertFalse(mcp_res["isError"])
        mcp_json = mcp_res["structuredContent"]

        engine_json = calculate_t_paired(mode="a-priori", tails=2, dz=0.5, alpha=0.05, power=0.95)
        self.assertEqual(cli_json, mcp_json)
        self.assertEqual(cli_json, engine_json)
        self.assertEqual(cli_json["n_total"], 54)

    def test_cli_and_mcp_identical_outputs_posthoc(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = run_cli(
                ["--test", "t-paired", "--mode", "post-hoc", "--tails", "1", "--d", "0.5", "--alpha", "0.05", "--n", "27"]
            )
        self.assertEqual(code, 0)
        cli_json = json.loads(buf.getvalue().strip())

        mcp_res = call_mcp_tool(
            "gpower_t_paired",
            {"mode": "post-hoc", "tails": 1, "dz": 0.5, "alpha": 0.05, "n_total": 27},
        )
        self.assertFalse(mcp_res["isError"])
        self.assertEqual(cli_json, mcp_res["structuredContent"])
        self.assertEqual(cli_json["n_total"], 27)
        self.assertAlmostEqual(cli_json["power"], 0.8118316, places=5)

    def test_cli_invalid_input_returns_nonzero_and_json_error(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = run_cli(
                ["--test", "t-paired", "--mode", "a-priori", "--tails", "2", "--dz", "0.0", "--alpha", "0.05", "--power", "0.80"]
            )
        self.assertNotEqual(code, 0)
        err_obj = json.loads(buf.getvalue().strip())
        self.assertIn("error", err_obj)
        self.assertIn("0.00001", err_obj["error"])

    def test_mcp_jsonrpc_protocol_lifecycle(self) -> None:
        init_resp = handle_jsonrpc_request({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        self.assertIsNotNone(init_resp)
        assert init_resp is not None
        self.assertEqual(init_resp["result"]["serverInfo"]["name"], "gpower-t-paired-mcp")

        list_resp = handle_jsonrpc_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        assert list_resp is not None
        tool_names = [t["name"] for t in list_resp["result"]["tools"]]
        self.assertIn("gpower_t_paired", tool_names)
        self.assertIn("gpower_effect_size_dz", tool_names)

        call_resp = handle_jsonrpc_request(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "gpower_t_paired",
                    "arguments": {"mode": "a-priori", "tails": 2, "dz": 0.5, "alpha": 0.05, "power": 0.80},
                },
            }
        )
        assert call_resp is not None
        self.assertEqual(call_resp["result"]["structuredContent"]["n_total"], 34)


class TestClinicalAIAgentBenchmark(unittest.TestCase):
    """Verifies the +10 Bonus Clinical AI Agent on the 10-question TR & EN benchmark."""

    def test_10_question_benchmark_tr_and_en(self) -> None:
        report = evaluate_clinical_benchmark()
        self.assertEqual(report["total_questions"], 10)
        self.assertEqual(report["tr_family_accuracy"], 1.0)
        self.assertEqual(report["en_family_accuracy"], 1.0)
        self.assertEqual(report["paired_n_exact_match_rate"], 1.0)

    def test_ambiguous_and_unsupported_questions_require_clarification(self) -> None:
        agent = ClinicalPowerAgent()
        amb = agent.answer("Tansiyon çalışmamız için kaç hasta gerekir?")
        self.assertEqual(amb["selected_family"], "ambiguous")
        self.assertTrue(amb["clarification_required"])
        self.assertIsNone(amb["engine_result"])

        unsup = agent.answer("Kaplan-Meier sağkalım analizi ve Cox regresyonu için kaç hasta gerekir?")
        self.assertEqual(unsup["selected_family"], "unsupported")
        self.assertTrue(unsup["clarification_required"])
        self.assertIsNone(unsup["engine_result"])


if __name__ == "__main__":
    unittest.main()
