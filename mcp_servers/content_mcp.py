"""
Content MCP Server

Curated educational resource database exposed as MCP tools.
READ-ONLY — Content Agent cannot write to this server.

Tools:
  - find_resources(topic, subject, grade_level, resource_type) → list of resources
  - get_resource_details(resource_id) → full resource metadata

Resources are sourced from a curated catalog of free, openly accessible content.
In production this would query a vector DB of indexed educational resources.
"""

from __future__ import annotations

from .base import MCPServer, tool

# Curated catalog of free educational resources.
# In production: replaced by a vector DB search over indexed content.
_RESOURCE_CATALOG: list[dict] = [
    # Math
    {"id": "kh-quad", "topic": "quadratic equations", "subject": "math", "grade_min": 8, "grade_max": 12, "title": "Quadratic Equations", "source": "Khan Academy", "type": "video", "difficulty": "intermediate", "description": "Step-by-step video lessons on solving quadratic equations by factoring, completing the square, and the quadratic formula."},
    {"id": "kh-alg", "topic": "algebra", "subject": "math", "grade_min": 6, "grade_max": 10, "title": "Algebra Basics", "source": "Khan Academy", "type": "interactive", "difficulty": "beginner", "description": "Interactive exercises covering variables, expressions, equations, and inequalities."},
    {"id": "wp-calc", "topic": "calculus", "subject": "math", "grade_min": 10, "grade_max": 12, "title": "Calculus — Wikipedia", "source": "Wikipedia", "type": "article", "difficulty": "advanced", "description": "Comprehensive overview of differential and integral calculus with worked examples."},
    {"id": "kh-geom", "topic": "geometry", "subject": "math", "grade_min": 7, "grade_max": 10, "title": "Geometry", "source": "Khan Academy", "type": "video", "difficulty": "intermediate", "description": "Videos and exercises on angles, triangles, circles, and coordinate geometry."},
    {"id": "kh-trig", "topic": "trigonometry", "subject": "math", "grade_min": 9, "grade_max": 12, "title": "Trigonometry", "source": "Khan Academy", "type": "interactive", "difficulty": "intermediate", "description": "Interactive exploration of sine, cosine, tangent, and the unit circle."},
    # Science
    {"id": "kh-photo", "topic": "photosynthesis", "subject": "science", "grade_min": 5, "grade_max": 10, "title": "Photosynthesis", "source": "Khan Academy", "type": "video", "difficulty": "beginner", "description": "Animated explanation of how plants convert sunlight, water, and CO2 into glucose and oxygen."},
    {"id": "kh-periodic", "topic": "periodic table", "subject": "science", "grade_min": 7, "grade_max": 12, "title": "Periodic Table of Elements", "source": "Khan Academy", "type": "interactive", "difficulty": "beginner", "description": "Interactive periodic table with element properties, electron configurations, and trends."},
    {"id": "wp-gravity", "topic": "gravity", "subject": "science", "grade_min": 6, "grade_max": 12, "title": "Gravity — Wikipedia", "source": "Wikipedia", "type": "article", "difficulty": "intermediate", "description": "In-depth article on gravitational force, Newton's law, and general relativity."},
    {"id": "kh-cells", "topic": "cell biology", "subject": "science", "grade_min": 6, "grade_max": 10, "title": "Cell Biology", "source": "Khan Academy", "type": "video", "difficulty": "beginner", "description": "Videos on cell structure, organelles, mitosis, and cell division."},
    {"id": "kh-chem", "topic": "chemistry", "subject": "science", "grade_min": 9, "grade_max": 12, "title": "Chemistry of Life", "source": "Khan Academy", "type": "interactive", "difficulty": "intermediate", "description": "Atoms, molecules, chemical bonds, and reactions explained with interactive models."},
    # History
    {"id": "kh-ww2", "topic": "world war ii", "subject": "history", "grade_min": 7, "grade_max": 12, "title": "World War II Overview", "source": "Khan Academy", "type": "video", "difficulty": "intermediate", "description": "Comprehensive video series on the causes, major events, and consequences of WWII."},
    {"id": "wp-renaissance", "topic": "renaissance", "subject": "history", "grade_min": 7, "grade_max": 12, "title": "The Renaissance", "source": "Wikipedia", "type": "article", "difficulty": "intermediate", "description": "Detailed article on the European Renaissance, its art, science, and cultural impact."},
    {"id": "kh-ancient", "topic": "ancient civilizations", "subject": "history", "grade_min": 5, "grade_max": 9, "title": "Ancient Civilizations", "source": "Khan Academy", "type": "video", "difficulty": "beginner", "description": "Video series on ancient Egypt, Greece, Rome, Mesopotamia, and other early civilizations."},
    # English
    {"id": "kh-grammar", "topic": "grammar", "subject": "english", "grade_min": 4, "grade_max": 10, "title": "English Grammar", "source": "Khan Academy", "type": "interactive", "difficulty": "beginner", "description": "Grammar exercises covering parts of speech, sentence structure, punctuation, and style."},
    {"id": "kh-essay", "topic": "essay writing", "subject": "english", "grade_min": 7, "grade_max": 12, "title": "Essay Writing", "source": "Khan Academy", "type": "video", "difficulty": "intermediate", "description": "Videos on thesis statements, paragraph structure, argumentation, and revision."},
    # Coding
    {"id": "kh-python", "topic": "python", "subject": "coding", "grade_min": 6, "grade_max": 12, "title": "Intro to Python", "source": "Khan Academy", "type": "interactive", "difficulty": "beginner", "description": "Interactive Python exercises from variables and loops to functions and data structures."},
    {"id": "kh-algo", "topic": "algorithms", "subject": "coding", "grade_min": 9, "grade_max": 12, "title": "Algorithms", "source": "Khan Academy", "type": "video", "difficulty": "intermediate", "description": "Video series on sorting, searching, recursion, and Big-O complexity."},
    {"id": "wp-recursion", "topic": "recursion", "subject": "coding", "grade_min": 9, "grade_max": 12, "title": "Recursion — Wikipedia", "source": "Wikipedia", "type": "article", "difficulty": "intermediate", "description": "Clear explanation of recursion with code examples in multiple languages."},
]


def _topic_matches(resource: dict, topic: str) -> bool:
    topic_lower = topic.lower()
    return (
        topic_lower in resource["topic"]
        or resource["topic"] in topic_lower
        or any(word in resource["topic"] for word in topic_lower.split() if len(word) > 3)
    )


class ContentMCPServer(MCPServer):
    """
    MCP server exposing curated educational resource catalog.
    READ-ONLY — ContentAgent uses this to find supplementary materials.
    """

    def __init__(self):
        super().__init__(
            name="content-mcp",
            description="Curated catalog of free educational resources (Khan Academy, Wikipedia, etc.). READ-ONLY.",
        )

    @tool(
        name="find_resources",
        description="Find free educational resources for a topic, filtered by subject and grade level.",
        input_schema={
            "topic": {"type": "string", "description": "The learning topic (e.g. 'quadratic equations')"},
            "subject": {"type": "string", "description": "Subject area: math, science, history, english, coding"},
            "grade_level": {"type": "integer", "description": "Student's grade level (1-12)"},
            "resource_type": {"type": "string", "description": "Filter by type: video, article, interactive, or 'all'"},
        },
        output_description="List of matching resources with title, source, type, difficulty, description",
    )
    async def find_resources(
        self,
        topic: str,
        subject: str = "general",
        grade_level: int = 8,
        resource_type: str = "all",
    ) -> list[dict]:
        results = []
        for r in _RESOURCE_CATALOG:
            # Filter by subject
            if subject != "general" and r["subject"] != subject.lower():
                continue
            # Filter by grade level
            if not (r["grade_min"] <= grade_level <= r["grade_max"]):
                continue
            # Filter by topic relevance
            if not _topic_matches(r, topic):
                continue
            # Filter by resource type
            if resource_type != "all" and r["type"] != resource_type:
                continue
            results.append({k: r[k] for k in ("id", "title", "source", "type", "difficulty", "description")})

        # If no topic matches, return top resources for subject+grade
        if not results:
            results = [
                {k: r[k] for k in ("id", "title", "source", "type", "difficulty", "description")}
                for r in _RESOURCE_CATALOG
                if (subject == "general" or r["subject"] == subject.lower())
                and r["grade_min"] <= grade_level <= r["grade_max"]
            ][:3]

        return results[:4]  # Return max 4 resources

    @tool(
        name="get_resource_details",
        description="Get full metadata for a specific resource by its ID.",
        input_schema={
            "resource_id": {"type": "string", "description": "Resource ID from find_resources results"},
        },
        output_description="Full resource metadata",
    )
    async def get_resource_details(self, resource_id: str) -> dict | None:
        for r in _RESOURCE_CATALOG:
            if r["id"] == resource_id:
                return r
        return None
