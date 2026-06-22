"""
/api/curriculum — Learning path endpoint.

Vercel Python serverless function.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from http.server import BaseHTTPRequestHandler
from agents.curriculum_agent import CurriculumAgent
from agents.safety_agent import SafetyAgent
from agents.base import AgentContext


def _cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Content-Type": "application/json",
    }


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        for k, v in _cors_headers().items():
            self.send_header(k, v)
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            result = asyncio.run(self._handle(body))
            self._respond(200, result)
        except Exception as e:
            self._respond(500, {"error": str(e)})

    async def _handle(self, body: dict) -> dict:
        api_key = os.environ["GEMINI_API_KEY"]
        context = AgentContext(
            student_id=body.get("student_id", "anonymous"),
            subject=body.get("subject", "general"),
            grade_level=int(body.get("grade_level", 8)),
            mastery_summary=body.get("mastery_summary", {}),
            current_topic=body.get("current_topic", ""),
        )

        agent = CurriculumAgent(api_key)
        result = await agent.run(context, body.get("message", "show my progress"))

        safety = SafetyAgent(api_key)
        safe_result = await safety.run(context, result.get("response", ""))

        return {
            **result,
            "response": safe_result.get("response", result.get("response")),
        }

    def _respond(self, status: int, data: dict):
        body = json.dumps(data).encode()
        self.send_response(status)
        for k, v in _cors_headers().items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass
