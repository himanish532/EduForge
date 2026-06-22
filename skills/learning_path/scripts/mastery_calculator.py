"""
mastery_calculator.py — deterministic curriculum graph computation.

Runs without LLM. Computes next recommended topic from the mastery graph
and prerequisite map. Called by CurriculumAgent to get a data-driven recommendation.

Usage:
    from skills.learning_path.scripts.mastery_calculator import get_next_topic, get_mastery_summary
"""

from __future__ import annotations

import json
from pathlib import Path

_PREREQ_MAP_PATH = Path(__file__).parent.parent / "references" / "prerequisite_map.json"


def _load_prereq_map() -> dict:
    try:
        return json.loads(_PREREQ_MAP_PATH.read_text())
    except Exception:
        return {}


def get_next_topic(
    subject: str,
    grade_level: int,
    mastery_summary: dict[str, float],
    min_mastery_to_unlock: float = 0.8,
) -> dict | None:
    """
    Compute the next recommended topic using the prerequisite map.

    Returns the topic with lowest mastery that:
    1. Has all prerequisites mastered (score ≥ min_mastery_to_unlock)
    2. Is appropriate for the student's grade level

    Returns None if all topics are mastered.
    """
    prereq_map = _load_prereq_map()
    subject_data = prereq_map.get(subject, {})
    topics = subject_data.get("topics", [])

    if not topics:
        return None

    eligible = []
    for topic in topics:
        topic_id = topic["id"]
        # Grade gate
        if topic.get("grade_start", 1) > grade_level:
            continue
        # Prerequisite gate
        prereqs = topic.get("prerequisites", [])
        prereqs_met = all(
            mastery_summary.get(p, 0.0) >= min_mastery_to_unlock for p in prereqs
        )
        if not prereqs_met:
            continue
        current_mastery = mastery_summary.get(topic_id, 0.0)
        eligible.append({**topic, "current_mastery": current_mastery})

    if not eligible:
        return None

    # Sort: mastered topics last, then by lowest mastery first
    not_mastered = [t for t in eligible if t["current_mastery"] < min_mastery_to_unlock]
    mastered = [t for t in eligible if t["current_mastery"] >= min_mastery_to_unlock]

    if not_mastered:
        # Recommend lowest-mastery unlocked topic
        return min(not_mastered, key=lambda t: t["current_mastery"])
    else:
        # All unlocked topics mastered — suggest highest-mastery as "advanced challenge"
        return {**mastered[-1], "advanced_challenge": True}


def get_mastery_summary(
    subject: str,
    mastery_summary: dict[str, float],
) -> list[dict]:
    """
    Return all topics for a subject with their current mastery level.
    Used for the progress dashboard.
    """
    prereq_map = _load_prereq_map()
    subject_data = prereq_map.get(subject, {})
    topics = subject_data.get("topics", [])

    return [
        {
            "id": t["id"],
            "label": t["label"],
            "mastery": mastery_summary.get(t["id"], 0.0),
            "prerequisites": t.get("prerequisites", []),
            "grade_start": t.get("grade_start", 1),
        }
        for t in topics
    ]
