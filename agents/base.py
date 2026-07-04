"""Base agent class — shared harness for all EduForge agents."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import google.generativeai as genai


@dataclass
class AgentContext:
    """Structured context passed to every agent — the context engineering harness."""

    student_id: str
    subject: str
    grade_level: int
    session_summary: str = ""
    recent_history: list[dict] = field(default_factory=list)
    mastery_summary: dict[str, float] = field(default_factory=dict)
    current_topic: str = ""
    # Day 3: active skill body injected by orchestrator (Level 2 progressive disclosure)
    active_skill_body: str = ""

    def to_prompt_block(self) -> str:
        """Serialise context into the token-efficient prompt block sent to the LLM."""
        history_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in self.recent_history[-5:]
        )
        mastery_text = ", ".join(
            f"{t}: {s:.0%}" for t, s in self.mastery_summary.items()
        ) or "No prior mastery recorded"

        return f"""
STUDENT CONTEXT:
- Grade: {self.grade_level} | Subject: {self.subject}
- Current topic: {self.current_topic or 'not set'}
- Session summary: {self.session_summary or 'New session'}
- Mastery: {mastery_text}

RECENT CONVERSATION:
{history_text or 'No prior exchanges'}
""".strip()

    def token_estimate(self) -> int:
        """Rough token count (1 token ≈ 4 chars)."""
        return len(self.to_prompt_block()) // 4


class BaseAgent:
    """
    Base class for all EduForge specialist agents.
    Wraps Gemini API calls with audit logging, error handling, and token budget enforcement.
    """

    MODEL = "gemini-2.5-flash"
    TOKEN_BUDGET = 7000  # total context budget per AGENTS.md
    MAX_RESPONSE_TOKENS = 1500

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(self.MODEL)
        self._audit_log: list[dict] = []

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def _log(self, event: str, data: dict[str, Any] | None = None) -> None:
        self._audit_log.append(
            {
                "timestamp": time.time(),
                "agent": self.name,
                "event": event,
                "data": data or {},
            }
        )

    def get_audit_log(self) -> list[dict]:
        return self._audit_log

    def _build_prompt(self, system_prompt: str, context: AgentContext, user_message: str) -> str:
        """
        Assemble the full prompt respecting the token budget from AGENTS.md.
        Day 3: injects active skill body (Level 2 progressive disclosure) when present.
        """
        context_block = context.to_prompt_block()
        skill_injection = context.active_skill_body if context.active_skill_body else ""
        return f"{system_prompt}{skill_injection}\n\n{context_block}\n\nSTUDENT: {user_message}"

    def _call_llm(self, prompt: str, json_output: bool = False) -> str:
        """Call Gemini with error handling. Returns raw text."""
        self._log("llm_call_start", {"prompt_length": len(prompt)})
        try:
            config = genai.types.GenerationConfig(
                max_output_tokens=self.MAX_RESPONSE_TOKENS,
                temperature=0.7,
            )
            response = self.model.generate_content(prompt, generation_config=config)
            result = response.text.strip()
            self._log("llm_call_success", {"response_length": len(result)})
            return result
        except Exception as e:
            self._log("llm_call_error", {"error": str(e)})
            raise

    def _call_llm_grounded(self, prompt: str) -> dict:
        """
        Day 4: Call Gemini with Google Search Grounding enabled.

        Grounding connects the model to real-time web search — no extra API key,
        no cost overhead beyond standard Gemini usage.

        Returns {"text": str, "sources": list[dict], "search_queries": list[str]}
        so callers can surface citations to the student.
        """
        self._log("llm_grounded_call_start", {"prompt_length": len(prompt)})
        try:
            grounded_model = genai.GenerativeModel(
                self.MODEL,
                tools=[{"google_search": {}}],
            )
            config = genai.types.GenerationConfig(
                max_output_tokens=self.MAX_RESPONSE_TOKENS,
                temperature=0.7,
            )
            response = grounded_model.generate_content(prompt, generation_config=config)
            text = response.text.strip()

            # Extract grounding metadata from the response
            sources: list[dict] = []
            search_queries: list[str] = []
            try:
                meta = response.candidates[0].grounding_metadata
                if meta:
                    for chunk in getattr(meta, "grounding_chunks", []):
                        web = getattr(chunk, "web", None)
                        if web:
                            sources.append({
                                "title": getattr(web, "title", ""),
                                "uri": getattr(web, "uri", ""),
                            })
                    for sq in getattr(meta, "web_search_queries", []):
                        search_queries.append(sq)
            except Exception:
                pass  # Grounding metadata is optional — degrade gracefully

            self._log(
                "llm_grounded_call_success",
                {"response_length": len(text), "sources": len(sources), "queries": search_queries},
            )
            return {"text": text, "sources": sources, "search_queries": search_queries}
        except Exception as e:
            self._log("llm_grounded_call_error", {"error": str(e)})
            # Fallback: plain LLM call without grounding
            return {"text": self._call_llm(prompt), "sources": [], "search_queries": []}

    def _parse_json(self, text: str) -> dict:
        """Extract JSON from LLM response, handling markdown code fences."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # Strip opening and closing fence lines
            text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Last-resort: try to find JSON object in the text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
            raise ValueError(f"Could not parse JSON from response: {text[:200]}")

    async def run(self, context: AgentContext, message: str) -> dict:
        """Override in subclasses. Returns a structured response dict."""
        raise NotImplementedError
