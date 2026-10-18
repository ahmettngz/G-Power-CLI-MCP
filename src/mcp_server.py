"""
Model Context Protocol (MCP) Server for Paired Samples t-Test Power Analysis.

Thin adapter over `src.engine` with zero duplicated calculation logic.
Supports JSON-RPC 2.0 over stdio (`initialize`, `tools/list`, `tools/call`, `ping`)
as well as direct in-process invocation via `call_mcp_tool(name, arguments)`.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List

if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.engine import ValidationError, calculate_t_paired, compute_effect_size_dz

MCP_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "gpower_t_paired",
        "description": (
            "Paired samples t-test ('Means: Difference between two dependent means (matched pairs)') "
            "power and sample size calculator. Supports 'a-priori' (compute required N) and "
            "'post-hoc' (compute achieved power) modes."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["a-priori", "post-hoc"],
                    "description": "'a-priori' to compute sample size N, or 'post-hoc' to compute achieved power.",
                },
                "tails": {
                    "type": "integer",
                    "enum": [1, 2],
                    "default": 2,
                    "description": "Number of tails (1 = one-tailed, 2 = two-tailed).",
                },
                "dz": {
                    "type": "number",
                    "description": "Effect size dz. Optional if group (mean1, mean2, sd1, sd2, corr) or difference (mean_dz, sd_dz) parameters are given.",
                },
                "alpha": {
                    "type": "number",
                    "default": 0.05,
                    "description": "Type I error probability alpha in [1e-7, 0.9999999].",
                },
                "power": {
                    "type": "number",
                    "description": "Target statistical power (1 - beta) in [alpha, 0.9999999] (required for a-priori).",
                },
                "n_total": {
                    "type": "integer",
                    "description": "Total number of matched pairs N in [3, 2147483646] (required for post-hoc).",
                },
                "mean_dz": {"type": "number", "description": "Mean of paired differences."},
                "sd_dz": {"type": "number", "description": "Standard deviation of paired differences (> 1e-12)."},
                "mean1": {"type": "number", "description": "Pre-measurement (Group 1) mean."},
                "mean2": {"type": "number", "description": "Post-measurement (Group 2) mean."},
                "sd1": {"type": "number", "description": "Pre-measurement (Group 1) SD (> 1e-12)."},
                "sd2": {"type": "number", "description": "Post-measurement (Group 2) SD (> 1e-12)."},
                "corr": {
                    "type": "number",
                    "description": "Correlation r between pre and post measurements in (-1+1e-8, 1-1e-8].",
                },
            },
            "required": ["mode"],
        },
    },
    {
        "name": "gpower_effect_size_dz",
        "description": (
            "Calculates Cohen's effect size dz for paired samples from either pre/post group "
            "parameters (mean1, mean2, sd1, sd2, corr) or difference parameters (mean_dz, sd_dz)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "mean_dz": {"type": "number"},
                "sd_dz": {"type": "number"},
                "mean1": {"type": "number"},
                "mean2": {"type": "number"},
                "sd1": {"type": "number"},
                "sd2": {"type": "number"},
                "corr": {"type": "number"},
            },
        },
    },
]


def call_mcp_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes an MCP tool by delegating directly to `src.engine`.
    Returns an MCP-compliant result dictionary with `content` and `structuredContent`.
    """
    try:
        if name == "gpower_t_paired":
            dz_val = arguments.get("dz", arguments.get("d"))
            n_val = arguments.get("n_total", arguments.get("n"))
            result = calculate_t_paired(
                mode=str(arguments.get("mode", "")),
                tails=int(arguments.get("tails", 2)),
                dz=dz_val,
                alpha=float(arguments.get("alpha", 0.05)),
                power=arguments.get("power"),
                n_total=n_val,
                mean_dz=arguments.get("mean_dz"),
                sd_dz=arguments.get("sd_dz"),
                mean1=arguments.get("mean1"),
                mean2=arguments.get("mean2"),
                sd1=arguments.get("sd1"),
                sd2=arguments.get("sd2"),
                corr=arguments.get("corr"),
            )
            return {
                "isError": False,
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False, separators=(",", ":")),
                    }
                ],
                "structuredContent": result,
            }

        if name == "gpower_effect_size_dz":
            dz = compute_effect_size_dz(
                mean_dz=arguments.get("mean_dz"),
                sd_dz=arguments.get("sd_dz"),
                mean1=arguments.get("mean1"),
                mean2=arguments.get("mean2"),
                sd1=arguments.get("sd1"),
                sd2=arguments.get("sd2"),
                corr=arguments.get("corr"),
            )
            payload = {"dz": round(dz, 7)}
            return {
                "isError": False,
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                    }
                ],
                "structuredContent": payload,
            }

        err_payload = {"error": f"Unknown MCP tool: {name}"}
        return {
            "isError": True,
            "content": [{"type": "text", "text": json.dumps(err_payload, ensure_ascii=False)}],
            "structuredContent": err_payload,
        }
    except ValidationError as exc:
        err_payload = {"error": str(exc)}
        return {
            "isError": True,
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(err_payload, ensure_ascii=False, separators=(",", ":")),
                }
            ],
            "structuredContent": err_payload,
        }


def handle_jsonrpc_request(request: Dict[str, Any]) -> Dict[str, Any] | None:
    """Processes a single JSON-RPC 2.0 request message for the MCP server."""
    req_id = request.get("id")
    method = request.get("method", "")
    params = request.get("params") or {}

    if method == "notifications/initialized":
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "gpower-t-paired-mcp", "version": "1.0.0"},
                "capabilities": {"tools": {}},
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": MCP_TOOLS},
        }

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments") or {}
        tool_res = call_mcp_tool(tool_name, arguments)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": tool_res,
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> None:
    """Runs the stdio JSON-RPC 2.0 MCP server loop."""
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = handle_jsonrpc_request(req)
            if resp is not None:
                sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                sys.stdout.flush()
        except Exception as exc:  # pragma: no cover
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse/execution error: {exc}"},
            }
            sys.stdout.write(json.dumps(err_resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
