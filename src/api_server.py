"""
HTTP REST API Server for Paired Samples t-Test Power Analysis & Clinical AI Agent.

Exposes:
- GET  /health               -> Health check
- GET  /api/v1/tools         -> MCP & OpenAPI tool schema list
- POST /api/v1/calculate     -> Direct `t-paired` calculation (a-priori or post-hoc)
- POST /api/v1/effect-size   -> Calculate `dz` from group or difference parameters
- POST /api/v1/agent/ask     -> Ask a natural-language clinical question (TR/EN) via the AI Agent
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict

if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent import ClinicalPowerAgent, evaluate_clinical_benchmark
from src.mcp_server import MCP_TOOLS, call_mcp_tool

_AGENT = ClinicalPowerAgent()


class GPowerAPIHandler(BaseHTTPRequestHandler):
    """Lightweight standard-library HTTP REST handler wrapping the MCP/Engine layer."""

    def _send_json(self, status_code: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "service": "gpower-t-paired-api", "version": "1.0.0"})
            return
        if self.path in ("/api/v1/tools", "/api/v1/schema"):
            self._send_json(200, {"tools": MCP_TOOLS})
            return
        if self.path == "/api/v1/benchmark":
            self._send_json(200, evaluate_clinical_benchmark())
            return
        self._send_json(404, {"error": f"Endpoint not found: {self.path}"})

    def do_POST(self) -> None:  # noqa: N802
        content_len = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            data = json.loads(raw or "{}")
        except json.JSONDecodeError as exc:
            self._send_json(400, {"error": f"Invalid JSON body: {exc}"})
            return

        if self.path == "/api/v1/calculate":
            res = call_mcp_tool("gpower_t_paired", data)
            status = 400 if res.get("isError") else 200
            self._send_json(status, res.get("structuredContent", {}))
            return

        if self.path == "/api/v1/effect-size":
            res = call_mcp_tool("gpower_effect_size_dz", data)
            status = 400 if res.get("isError") else 200
            self._send_json(status, res.get("structuredContent", {}))
            return

        if self.path == "/api/v1/agent/ask":
            question = str(data.get("question", "")).strip()
            if not question:
                self._send_json(400, {"error": "Field 'question' is required."})
                return
            ans = _AGENT.answer(question)
            self._send_json(200, ans)
            return

        self._send_json(404, {"error": f"Endpoint not found: {self.path}"})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Start G*Power Clean-Room HTTP REST API server.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port number (default: 8080)")
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), GPowerAPIHandler)
    print(f"G*Power Clean-Room REST API listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
