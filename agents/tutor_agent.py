"""
TutorAgent — Explains concepts through Socratic dialogue.

Day 2: WikipediaMCPServer via MCPClient (MCP pattern).
Day 4: Google Search Grounding — real-time web knowledge injected into every
       explanation, with cited sources returned to the student.
       Zero infra: grounding is a built-in Gemini API feature, no extra cost.

Skill: subject-tutor
MCP tools used: search_wikipedia, get_article_summary
Grounding: google_search (Gemini built-in)
"""

from __future__ import annotations

from .base import AgentContext, BaseAgent
from mcp_servers import WikipediaMCPServer, MCPClient

TUTOR_SYSTEM_PROMPT = """
You are a patient, encouraging AI tutor. Your teaching philosophy:
never give direct answers — guide students to discover answers themselves.

Rules:
1. Start by checking what the student already knows.
2. Explain using simple analogies for a grade {grade_level} student studying {subject}.
3. After every explanation, ask ONE focused follow-up question to confirm understanding.
4. If the student is stuck after 2 tries, give a scaffolded hint (not the answer).
5. Keep responses under 300 words.
6. Use warm, plain language. Celebrate curiosity.
7. Format with short paragraphs — no bullet points in explanations.

Current topic: {topic}
""".strip()


class TutorAgent(BaseAgent):
    """
    Socratic tutor agent.

    MCP Connection:
      - Connects to WikipediaMCPServer on init (handshake: lists available tools)
      - Calls search_wikipedia and get_article_summary during tutoring
    """

    def __init__(self, api_key: str):
        super().__init__(api_key)
        # MCP Discovery: connect to Wikipedia MCP server and list its tools
        self._wiki_server = WikipediaMCPServer()
        self._wiki_client = MCPClient(self._wiki_server)
        available_tools = self._wiki_client.list_tools()
        self._log(
            "mcp_connected",
            {
                "server": self._wiki_server.name,
                "tools": [t.name for t in available_tools],
            },
        )

    async def _fetch_wiki_context(self, topic: str) -> str:
        """Call Wikipedia MCP tools to get factual grounding for the explanation."""
        try:
            # MCP tool call 1: search for the topic
            search_results = await self._wiki_client.call("search_wikipedia", query=topic, limit=2)
            if not search_results:
                return ""

            best_title = search_results[0]["title"]

            # MCP tool call 2: fetch article summary
            summary = await self._wiki_client.call("get_article_summary", title=best_title)

            self._log("mcp_tool_called", {"tool": "get_article_summary", "title": best_title})
            return f"\n\nFACT-CHECK (Wikipedia — {best_title}):\n{summary}\nUse this to ensure accuracy. Do not copy it verbatim."

        except Exception as e:
            self._log("mcp_tool_error", {"error": str(e)})
            return ""

    async def run(self, context: AgentContext, message: str) -> dict:
        self._log("tutor_start", {"topic": context.current_topic})

        # Fetch Wikipedia context via MCP (Day 2)
        wiki_context = ""
        if context.current_topic:
            wiki_context = await self._fetch_wiki_context(context.current_topic)

        system_prompt = TUTOR_SYSTEM_PROMPT.format(
            grade_level=context.grade_level,
            subject=context.subject,
            topic=context.current_topic or context.subject,
        ) + wiki_context

        prompt = self._build_prompt(system_prompt, context, message)

        # Day 4: use search grounding for real-time accuracy
        grounded = self._call_llm_grounded(prompt)
        response = grounded["text"]
        sources = grounded["sources"]
        search_queries = grounded["search_queries"]

        self._log("tutor_complete", {
            "response_len": len(response),
            "grounded_sources": len(sources),
            "search_queries": search_queries,
        })

        return {
            "response": response,
            "sources": sources,
            "search_queries": search_queries,
            "metadata": {
                "agent": "TutorAgent",
                "skill": "subject-tutor",
                "topic": context.current_topic,
                "mcp_server": self._wiki_server.name,
                "wikipedia_used": bool(wiki_context),
                "grounded": True,
                "source_count": len(sources),
            },
        }
