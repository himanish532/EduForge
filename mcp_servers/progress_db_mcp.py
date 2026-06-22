"""
Progress DB MCP Server

Exposes student progress data as MCP tools backed by SQLite (dev) / JSON file (Vercel).
Agents use this to read and write topic mastery scores.

Tools:
  - get_student_progress(student_id) → full mastery dict
  - update_mastery(student_id, topic, score, attempts) → void
  - get_session_history(student_id) → last 10 session events
  - record_session_event(student_id, event_type, topic, data) → void
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from .base import MCPServer, tool

# Use a JSON file store for portability (SQLite not writable on Vercel).
# In production this would be Vercel KV or PostgreSQL.
_STORE_PATH = Path(os.environ.get("PROGRESS_DB_PATH", "/tmp/eduforge_progress.json"))


def _load_store() -> dict:
    if _STORE_PATH.exists():
        try:
            return json.loads(_STORE_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_store(data: dict) -> None:
    try:
        _STORE_PATH.write_text(json.dumps(data, indent=2))
    except OSError:
        pass  # Read-only filesystem (e.g. some Vercel deployments) — graceful degradation


class ProgressDBMCPServer(MCPServer):
    """
    MCP server for reading and writing student mastery data.
    Curriculum and Assessment agents use this to track learning progress.
    """

    def __init__(self):
        super().__init__(
            name="progress-db-mcp",
            description="Student progress database — read/write topic mastery scores and session history.",
        )

    @tool(
        name="get_student_progress",
        description="Get the full mastery profile for a student, including all topic scores and attempts.",
        input_schema={
            "student_id": {"type": "string", "description": "Anonymous student identifier"},
        },
        output_description="Dict with mastery scores {topic: {score, attempts, last_updated}}",
    )
    async def get_student_progress(self, student_id: str) -> dict:
        store = _load_store()
        return store.get(student_id, {}).get("mastery", {})

    @tool(
        name="update_mastery",
        description="Update a student's mastery score for a topic after an assessment.",
        input_schema={
            "student_id": {"type": "string", "description": "Anonymous student identifier"},
            "topic": {"type": "string", "description": "The topic being assessed"},
            "score": {"type": "number", "description": "Score from 0.0 to 1.0"},
            "attempts": {"type": "integer", "description": "Number of attempts on this topic so far"},
        },
        output_description="Updated mastery entry",
    )
    async def update_mastery(
        self, student_id: str, topic: str, score: float, attempts: int = 1
    ) -> dict:
        score = max(0.0, min(1.0, score))
        store = _load_store()
        student = store.setdefault(student_id, {"mastery": {}, "history": []})
        existing = student["mastery"].get(topic, {})
        updated = {
            "score": score,
            "attempts": existing.get("attempts", 0) + attempts,
            "last_updated": time.time(),
        }
        student["mastery"][topic] = updated
        _save_store(store)
        return updated

    @tool(
        name="get_session_history",
        description="Get the last 10 session events for a student (topics studied, quizzes taken).",
        input_schema={
            "student_id": {"type": "string", "description": "Anonymous student identifier"},
        },
        output_description="List of session events [{type, topic, timestamp, data}]",
    )
    async def get_session_history(self, student_id: str) -> list[dict]:
        store = _load_store()
        return store.get(student_id, {}).get("history", [])[-10:]

    @tool(
        name="record_session_event",
        description="Record a session event (topic studied, quiz taken, resource viewed).",
        input_schema={
            "student_id": {"type": "string", "description": "Anonymous student identifier"},
            "event_type": {"type": "string", "description": "Event type: tutoring|quiz|resources|curriculum"},
            "topic": {"type": "string", "description": "Topic involved"},
            "data": {"type": "object", "description": "Additional event data"},
        },
        output_description="Recorded event",
    )
    async def record_session_event(
        self, student_id: str, event_type: str, topic: str, data: dict | None = None
    ) -> dict:
        store = _load_store()
        student = store.setdefault(student_id, {"mastery": {}, "history": []})
        event = {
            "type": event_type,
            "topic": topic,
            "timestamp": time.time(),
            "data": data or {},
        }
        student["history"].append(event)
        # Keep last 50 events only
        student["history"] = student["history"][-50:]
        _save_store(store)
        return event
