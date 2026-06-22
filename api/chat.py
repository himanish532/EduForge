"""
/api/chat — Main chat endpoint.

Vercel Python serverless function.
Receives a student message and returns the orchestrated agent response.
"""

from __future__ import annotations

import json
import os
import sys
import asyncio

# Add parent dir to path so we can import `agents`
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from http.server import BaseHTTPRequestHandler

from agents.orchestrator import Orchestrator
from agents.base import AgentContext


def _get_orchestrator() -> Orchestrator:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")
    return Orchestrator(api_key)


def _cors_headers() -> dict:
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

        except ValueError as e:
            self._respond(400, {"error": str(e)})
        except Exception as e:
            self._respond(500, {"error": "Internal server error", "detail": str(e)})

    async def _handle(self, body: dict) -> dict:
        message = body.get("message", "").strip()
        if not message:
            raise ValueError("message is required")

        # Reconstruct AgentContext from request body
        context = AgentContext(
            student_id=body.get("student_id", "anonymous"),
            subject=body.get("subject", "general"),
            grade_level=int(body.get("grade_level", 8)),
            session_summary=body.get("session_summary", ""),
            recent_history=body.get("recent_history", []),
            mastery_summary=body.get("mastery_summary", {}),
            current_topic=body.get("current_topic", ""),
        )

        orchestrator = _get_orchestrator()
        result = await orchestrator.process(context, message)

        # Return updated context fields so frontend can persist them
        result["updated_context"] = {
            "session_summary": context.session_summary,
            "recent_history": context.recent_history,
            "mastery_summary": context.mastery_summary,
            "current_topic": context.current_topic,
        }

        return result

    def _respond(self, status: int, data: dict):
        body = json.dumps(data).encode()
        self.send_response(status)
        for k, v in _cors_headers().items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # Suppress default access logs in Vercel
