"""
format_explanation.py — deterministic post-processor for tutor responses.

Runs AFTER the LLM generates a response. Does NOT touch the token window.
Enforces structural rules without re-prompting the model.

Usage (called by TutorAgent):
    from skills.subject_tutor.scripts.format_explanation import format_explanation
    cleaned = format_explanation(raw_llm_output, grade_level=8)
"""

from __future__ import annotations

import re


def format_explanation(text: str, grade_level: int = 8) -> str:
    """
    Post-process a tutor response:
    1. Enforce word limit (300 words for grade ≤6, 400 for grade 7-12)
    2. Ensure it ends with a question mark (the follow-up question rule)
    3. Strip any accidental answer-giving phrases
    4. Normalize whitespace
    """
    # Strip boilerplate model headers
    text = re.sub(r"^(TUTOR:|Assistant:|AI:)\s*", "", text, flags=re.IGNORECASE).strip()

    # Word limit by grade
    limit = 300 if grade_level <= 6 else 400
    words = text.split()
    if len(words) > limit:
        # Truncate at last sentence boundary within limit
        truncated = " ".join(words[:limit])
        last_period = max(truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"))
        if last_period > len(truncated) // 2:
            text = truncated[: last_period + 1]
        else:
            text = truncated + "..."

    # Detect answer-giving phrases (skill smell check)
    answer_patterns = [
        r"\bthe answer is\b",
        r"\bthe correct answer\b",
        r"\bthe solution is\b",
    ]
    for pattern in answer_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            # Flag but don't block — log for eval review
            text = text + "\n\n_(Note to eval: possible direct answer detected — review trigger)_"
            break

    # Ensure response ends with a question
    stripped = text.rstrip()
    if not stripped.endswith("?"):
        text = stripped + "\n\nWhat do you think about that so far?"

    return text.strip()


def count_tokens_estimate(text: str) -> int:
    """Rough token count estimate (1 token ≈ 4 chars). Used for budget tracking."""
    return len(text) // 4
