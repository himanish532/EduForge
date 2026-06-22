"""
ContentAgent — Fetches and curates supplementary learning resources.

Skill: content-fetch
Constraint: READ-ONLY access to all external sources
"""

from __future__ import annotations

import httpx

from .base import AgentContext, BaseAgent

CONTENT_SYSTEM_PROMPT = """
You are a resource librarian for an educational platform. Find the best free learning materials.

Rules:
1. Return 2-3 curated resources for the topic.
2. Prefer free, openly accessible content.
3. Include at least 1 video if possible.
4. Rate difficulty: beginner / intermediate / advanced.
5. Match resources to the student's grade level ({grade_level}).

Topic: {topic} | Subject: {subject}

Respond with JSON:
{{
  "resources": [
    {{
      "title": "...",
      "description": "1 sentence describing what this teaches",
      "type": "video|article|exercise|interactive",
      "difficulty": "beginner|intermediate|advanced",
      "source": "Khan Academy|Wikipedia|YouTube|etc"
    }}
  ],
  "summary": "1 sentence introducing these resources"
}}
""".strip()


class ContentAgent(BaseAgent):

    async def run(self, context: AgentContext, message: str) -> dict:
        self._log("content_start", {"topic": context.current_topic})

        topic = context.current_topic or context.subject

        # Try Wikipedia search for context (READ-ONLY MCP simulation)
        wiki_titles = await self._search_wikipedia(topic)

        system_prompt = CONTENT_SYSTEM_PROMPT.format(
            grade_level=context.grade_level,
            topic=topic,
            subject=context.subject,
        )

        hint = f"\n\nWikipedia articles found: {', '.join(wiki_titles)}" if wiki_titles else ""
        prompt = f"{system_prompt}{hint}\n\nFind resources for: {message}"
        raw = self._call_llm(prompt, json_output=True)

        try:
            data = self._parse_json(raw)
        except Exception:
            data = {
                "resources": [
                    {
                        "title": f"Khan Academy: {topic}",
                        "description": "Free video lessons and exercises",
                        "type": "video",
                        "difficulty": "beginner",
                        "source": "Khan Academy",
                    }
                ],
                "summary": f"Here are some resources to help you learn about {topic}.",
            }

        resources = data.get("resources", [])
        lines = [f"**Resources for {topic}** 📖\n", data.get("summary", ""), ""]
        for r in resources:
            icon = {"video": "🎬", "article": "📄", "exercise": "✏️", "interactive": "🖱️"}.get(r.get("type", ""), "📚")
            lines.append(f"{icon} **{r['title']}** _{r.get('source', '')}_ — {r.get('description', '')}")

        self._log("content_complete", {"resource_count": len(resources)})

        return {
            "response": "\n".join(lines),
            "resources": resources,
            "metadata": {
                "agent": "ContentAgent",
                "skill": "content-fetch",
                "readonly": True,
            },
        }

    async def _search_wikipedia(self, topic: str) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://en.wikipedia.org/w/api.php",
                    params={
                        "action": "query",
                        "list": "search",
                        "srsearch": topic,
                        "format": "json",
                        "srlimit": 3,
                    },
                )
                results = resp.json().get("query", {}).get("search", [])
                return [r["title"] for r in results]
        except Exception:
            return []
