"""
rank_resources.py — deterministic resource ranking script.

Ranks a list of resources by relevance to the topic and grade level.
No LLM call — pure scoring function. Called by ContentAgent.

Usage:
    from skills.content_fetch.scripts.rank_resources import rank_resources
    ranked = rank_resources(resources, topic="quadratic equations", grade_level=8)
"""

from __future__ import annotations


# Source trust scores (higher = more reliable for education)
_SOURCE_TRUST = {
    "Khan Academy": 1.0,
    "Wikipedia": 0.85,
    "CK-12": 0.9,
    "PhET": 0.9,
    "YouTube": 0.7,
}

# Type preference (video preferred first, then interactive, then article)
_TYPE_ORDER = {"video": 3, "interactive": 2, "exercise": 2, "article": 1}


def rank_resources(
    resources: list[dict],
    topic: str,
    grade_level: int,
    prefer_type: str = "video",
) -> list[dict]:
    """
    Score and rank resources by:
    1. Topic relevance (keyword match)
    2. Source trust
    3. Type preference (video first)
    4. Difficulty match to grade level
    """

    def _topic_score(r: dict) -> float:
        topic_lower = topic.lower()
        title_lower = r.get("title", "").lower()
        desc_lower = r.get("description", "").lower()
        if topic_lower in title_lower:
            return 1.0
        words = [w for w in topic_lower.split() if len(w) > 3]
        matches = sum(1 for w in words if w in title_lower or w in desc_lower)
        return matches / max(len(words), 1)

    def _grade_match(r: dict) -> float:
        difficulty = r.get("difficulty", "intermediate")
        if grade_level <= 5:
            return 1.0 if difficulty == "beginner" else 0.5
        elif grade_level <= 8:
            return 1.0 if difficulty == "intermediate" else 0.7
        else:
            return 1.0 if difficulty in ("intermediate", "advanced") else 0.6

    def _score(r: dict) -> float:
        trust = _SOURCE_TRUST.get(r.get("source", ""), 0.6)
        type_score = _TYPE_ORDER.get(r.get("type", "article"), 1) / 3.0
        prefer_bonus = 0.2 if r.get("type") == prefer_type else 0.0
        return (
            _topic_score(r) * 0.4
            + trust * 0.3
            + _grade_match(r) * 0.2
            + type_score * 0.1
            + prefer_bonus
        )

    return sorted(resources, key=_score, reverse=True)
