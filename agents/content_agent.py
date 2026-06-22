"""
ContentAgent — Curates supplementary learning resources.

Day 2 upgrade:
  - Uses ContentMCPServer via MCPClient for resource discovery
  - Also calls WikipediaMCPServer for article references
  - READ-ONLY: no writes to any server

Skill: content-fetch
MCP tools used: find_resources (ContentMCP), search_wikipedia (WikipediaMCP)
"""

from __future__ import annotations

from .base import AgentContext, BaseAgent
from mcp_servers import ContentMCPServer, WikipediaMCPServer, MCPClient

CONTENT_SYSTEM_PROMPT = """
You are a resource librarian for an educational platform. Present the provided resources
in an engaging, helpful way for a Grade {grade_level} student studying {subject}.

For each resource, write one sentence explaining why it's useful for learning {topic}.
Keep the total response under 200 words.
""".strip()


class ContentAgent(BaseAgent):
    """ContentAgent — finds resources via Content MCP + Wikipedia MCP."""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self._content_server = ContentMCPServer()
        self._content_client = MCPClient(self._content_server)
        self._wiki_server = WikipediaMCPServer()
        self._wiki_client = MCPClient(self._wiki_server)
        self._log(
            "mcp_connected",
            {
                "servers": [self._content_server.name, self._wiki_server.name],
                "content_tools": [t.name for t in self._content_client.list_tools()],
                "wiki_tools": [t.name for t in self._wiki_client.list_tools()],
            },
        )

    async def run(self, context: AgentContext, message: str) -> dict:
        self._log("content_start", {"topic": context.current_topic})
        topic = context.current_topic or context.subject

        # MCP tool call: find curated resources
        try:
            resources = await self._content_client.call(
                "find_resources",
                topic=topic,
                subject=context.subject,
                grade_level=context.grade_level,
                resource_type="all",
            )
        except Exception as e:
            self._log("content_mcp_error", {"error": str(e)})
            resources = []

        # MCP tool call: supplement with Wikipedia articles
        wiki_titles: list[str] = []
        try:
            wiki_results = await self._wiki_client.call("search_wikipedia", query=topic, limit=2)
            wiki_titles = [r["title"] for r in wiki_results]
        except Exception:
            pass

        # Build response
        if resources:
            icon_map = {"video": "🎬", "article": "📄", "exercise": "✏️", "interactive": "🖱️"}
            lines = [f"**Resources for {topic}** 📖\n"]
            for r in resources[:3]:
                icon = icon_map.get(r.get("type", ""), "📚")
                lines.append(
                    f"{icon} **{r['title']}** _{r.get('source', '')}_ · {r.get('difficulty', '')} — {r.get('description', '')}"
                )
            if wiki_titles:
                lines.append(f"\n📖 **Also on Wikipedia:** {', '.join(wiki_titles)}")
            response = "\n".join(lines)
        else:
            wiki_line = f"\n📖 Wikipedia: {', '.join(wiki_titles)}" if wiki_titles else ""
            response = (
                f"I found some resources for **{topic}**:\n\n"
                f"🎬 **Khan Academy** — search for '{topic}' at khanacademy.org\n"
                f"📄 **Wikipedia** — en.wikipedia.org/wiki/{topic.replace(' ', '_')}"
                f"{wiki_line}"
            )

        self._log("content_complete", {"resource_count": len(resources)})

        return {
            "response": response,
            "resources": resources,
            "metadata": {
                "agent": "ContentAgent",
                "skill": "content-fetch",
                "readonly": True,
                "mcp_servers": [self._content_server.name, self._wiki_server.name],
            },
        }
