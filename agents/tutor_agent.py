"""
TutorAgent — Explains concepts through Socratic dialogue.

Skill: subject-tutor
Tools: Wikipedia MCP (via HTTP)
"""

from __future__ import annotations

import httpx

from .base import AgentContext, BaseAgent

TUTOR_SYSTEM_PROMPT = """
You are a patient, encouraging AI tutor. Your teaching philosophy:
never give direct answers — guide students to discover answers themselves.

Rules:
1. Start by acknowledging what the student said and checking prior knowledge.
2. Explain using simple analogies appropriate for a grade {grade_level} student.
3. After every explanation, ask ONE focused follow-up question to confirm understanding.
4. If the student is stuck after 2 tries, give a scaffolded hint (not the answer).
5. Keep responses under 300 words.
6. Use plain, warm language. Celebrate curiosity.
7. Format with short paragraphs — never use bullet points in explanations.

Current subject: {subject}
Current topic: {topic}
""".strip()


class TutorAgent(BaseAgent):
    """Socratic tutor agent backed by Gemini + Wikipedia lookup."""

    WIKIPEDIA_API = "https://en.wikipedia.org/api/rest_v1/page/summary"

    async def _fetch_wikipedia_summary(self, topic: str) -> str | None:
        """Lightweight Wikipedia lookup — simulates Wikipedia MCP tool call."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Wikipedia search
                search_url = "https://en.wikipedia.org/w/api.php"
                params = {
                    "action": "query",
                    "list": "search",
                    "srsearch": topic,
                    "format": "json",
                    "srlimit": 1,
                }
                resp = await client.get(search_url, params=params)
                data = resp.json()
                results = data.get("query", {}).get("search", [])
                if not results:
                    return None

                title = results[0]["title"]
                # Fetch summary
                summary_resp = await client.get(f"{self.WIKIPEDIA_API}/{title.replace(' ', '_')}")
                if summary_resp.status_code == 200:
                    return summary_resp.json().get("extract", "")[:500]
        except Exception:
            pass
        return None

    async def run(self, context: AgentContext, message: str) -> dict:
        self._log("tutor_start", {"topic": context.current_topic})

        # Optionally enrich with Wikipedia context (simulates MCP tool call)
        wiki_context = ""
        if context.current_topic:
            summary = await self._fetch_wikipedia_summary(context.current_topic)
            if summary:
                wiki_context = f"\n\nFACT CHECK (Wikipedia):\n{summary}\nUse this to ensure accuracy."
                self._log("wikipedia_lookup", {"topic": context.current_topic, "found": True})

        system_prompt = TUTOR_SYSTEM_PROMPT.format(
            grade_level=context.grade_level,
            subject=context.subject,
            topic=context.current_topic or "general",
        ) + wiki_context

        prompt = self._build_prompt(system_prompt, context, message)
        response = self._call_llm(prompt)

        self._log("tutor_complete", {"response_len": len(response)})

        return {
            "response": response,
            "metadata": {
                "agent": "TutorAgent",
                "skill": "subject-tutor",
                "topic": context.current_topic,
                "wikipedia_used": bool(wiki_context),
            },
        }
