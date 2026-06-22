"""
score_quiz.py — deterministic quiz scoring script.

Runs deterministically — no LLM call needed for scoring.
Called by AssessmentAgent.score_answer() to compute mastery update.

Usage:
    from skills.quiz_generator.scripts.score_quiz import score_answer, update_mastery_score
"""

from __future__ import annotations


def score_answer(selected_index: int, correct_index: int) -> float:
    """Binary scoring: 1.0 if correct, 0.0 if wrong."""
    return 1.0 if selected_index == correct_index else 0.0


def update_mastery_score(prior_mastery: float, score: float, attempt_number: int) -> float:
    """
    Weighted mastery update.

    - Early attempts (1-3): new score counts 40% (learning fast)
    - Later attempts (4+): new score counts 20% (more stable estimate)

    This prevents a single lucky/unlucky attempt from skewing mastery too much.
    """
    if attempt_number <= 3:
        weight = 0.4
    else:
        weight = 0.2
    new_mastery = prior_mastery * (1 - weight) + score * weight
    return round(max(0.0, min(1.0, new_mastery)), 3)


def get_difficulty_label(mastery: float) -> str:
    if mastery < 0.4:
        return "beginner"
    elif mastery < 0.75:
        return "intermediate"
    return "advanced"


def mastery_tier(mastery: float, attempts: int) -> str:
    """
    Classify mastery level for curriculum purposes.
    Per AGENTS.md: topic is 'mastered' when score ≥ 0.8 across 3+ attempts.
    """
    if mastery >= 0.8 and attempts >= 3:
        return "mastered"
    elif mastery >= 0.4:
        return "progressing"
    return "needs_work"
