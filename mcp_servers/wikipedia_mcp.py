"""
Wikipedia MCP Server

Exposes Wikipedia search and article retrieval as MCP tools.
READ-ONLY — no writes. Rate limited to 10 req/min per SPEC.md.

Tools:
  - search_wikipedia(query) → list of matching article titles + snippets
  - get_article_summary(title) → plain-text article summary (≤500 chars)
  - get_article_section(title, section) → specific section text
"""

from __future__ import annotations

import time
import httpx

from .base import MCPServer, tool

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_SUMMARY_API = "https://en.wikipedia.org/api/rest_v1/page/summary"

# Simple in-memory rate limiter (10 req/min)
_request_times: list[float] = []
_RATE_LIMIT = 10
_RATE_WINDOW = 60.0


def _check_rate_limit() -> None:
    now = time.time()
    global _request_times
    _request_times = [t for t in _request_times if now - t < _RATE_WINDOW]
    if len(_request_times) >= _RATE_LIMIT:
        raise RuntimeError("Wikipedia MCP rate limit exceeded (10 req/min). Please wait.")
    _request_times.append(now)


class WikipediaMCPServer(MCPServer):
    """MCP server exposing Wikipedia as a knowledge tool for the Tutor and Content agents."""

    def __init__(self):
        super().__init__(
            name="wikipedia-mcp",
            description="Read-only access to Wikipedia for educational fact-checking and content retrieval.",
        )

    @tool(
        name="search_wikipedia",
        description="Search Wikipedia for articles matching a query. Returns titles and short snippets.",
        input_schema={
            "query": {"type": "string", "description": "The search query (e.g. 'quadratic equations')"},
            "limit": {"type": "integer", "description": "Max results to return (default 3, max 5)"},
        },
        output_description="List of {title, snippet} dicts",
    )
    async def search_wikipedia(self, query: str, limit: int = 3) -> list[dict]:
        _check_rate_limit()
        limit = min(limit, 5)
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                WIKIPEDIA_API,
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "format": "json",
                    "srlimit": limit,
                    "srprop": "snippet|titlesnippet",
                },
            )
            resp.raise_for_status()
            results = resp.json().get("query", {}).get("search", [])
            return [
                {
                    "title": r["title"],
                    "snippet": r.get("snippet", "").replace('<span class="searchmatch">', "").replace("</span>", ""),
                }
                for r in results
            ]

    @tool(
        name="get_article_summary",
        description="Get a concise summary of a Wikipedia article by its exact title.",
        input_schema={
            "title": {"type": "string", "description": "Exact Wikipedia article title"},
        },
        output_description="Plain-text article summary (up to 500 characters)",
    )
    async def get_article_summary(self, title: str) -> str:
        _check_rate_limit()
        safe_title = title.replace(" ", "_")
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(f"{WIKIPEDIA_SUMMARY_API}/{safe_title}")
            if resp.status_code == 404:
                return f"No Wikipedia article found for '{title}'."
            resp.raise_for_status()
            data = resp.json()
            extract = data.get("extract", "")
            return extract[:500] + ("..." if len(extract) > 500 else "")

    @tool(
        name="get_article_section",
        description="Get a specific section from a Wikipedia article.",
        input_schema={
            "title": {"type": "string", "description": "Exact Wikipedia article title"},
            "section": {"type": "string", "description": "Section title to retrieve (e.g. 'History', 'Applications')"},
        },
        output_description="Section text (up to 800 characters)",
    )
    async def get_article_section(self, title: str, section: str) -> str:
        _check_rate_limit()
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                WIKIPEDIA_API,
                params={
                    "action": "parse",
                    "page": title,
                    "prop": "sections|wikitext",
                    "format": "json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            sections = data.get("parse", {}).get("sections", [])
            match = next((s for s in sections if section.lower() in s.get("line", "").lower()), None)
            if not match:
                return f"Section '{section}' not found in '{title}'."
            # Return wikitext snippet as approximation
            wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")
            idx = wikitext.lower().find(section.lower())
            if idx == -1:
                return f"Section '{section}' content could not be extracted."
            return wikitext[idx : idx + 800].strip()
