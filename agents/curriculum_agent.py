"""
CurriculumAgent — Maintains and adapts the student's personalized learning path.

Skill: learning-path
A2A: Receives assessment_result from AssessmentAgent, updates mastery graph
"""

from __future__ import annotations

from .base import AgentContext, BaseAgent

CURRICULUM_SYSTEM_PROMPT = """
You are a personalized curriculum designer. Your job is to look at a student's mastery levels
and recommend their next learning step.

Mastery thresholds:
- < 0.4 → needs more practice
- 0.4 - 0.79 → progressing
- ≥ 0.8 × 3 attempts → mastered

Rules:
1. Recommend the next topic that is both unlocked AND has the lowest mastery.
2. If all topics are mastered, suggest an advanced challenge.
3. Never recommend skipping prerequisites.
4. Keep the explanation encouraging and motivating.
5. For grades 1-6: flag as requiring teacher approval.

Student: Grade {grade_level} | Subject: {subject}
Current mastery: {mastery}

Respond with JSON:
{{
  "next_topic": "...",
  "reason": "...",
  "encouragement": "1 sentence of personalized encouragement",
  "mastery_summary": {{ ... }},
  "requires_teacher_approval": true/false
}}
""".strip()


class CurriculumAgent(BaseAgent):

    async def run(self, context: AgentContext, message: str) -> dict:
        self._log("curriculum_start", {"mastery": context.mastery_summary})

        mastery_text = json_safe_mastery(context.mastery_summary)

        system_prompt = CURRICULUM_SYSTEM_PROMPT.format(
            grade_level=context.grade_level,
            subject=context.subject,
            mastery=mastery_text,
        )

        prompt = f"{system_prompt}\n\nStudent asks: {message}"
        raw = self._call_llm(prompt, json_output=True)

        try:
            data = self._parse_json(raw)
        except Exception:
            data = {
                "next_topic": context.current_topic or context.subject,
                "reason": "Continue exploring your current topic.",
                "encouragement": "You're making great progress — keep it up!",
                "mastery_summary": context.mastery_summary,
                "requires_teacher_approval": context.grade_level <= 6,
            }

        requires_approval = data.get("requires_teacher_approval", False)

        response = (
            f"**Your Learning Path** 📚\n\n"
            f"**Next up:** {data.get('next_topic', 'Continue current topic')}\n\n"
            f"**Why:** {data.get('reason', '')}\n\n"
            f"_{data.get('encouragement', '')}_"
        )

        if requires_approval:
            response += "\n\n> ⏳ Your teacher will review this curriculum update."

        self._log("curriculum_complete", {"next_topic": data.get("next_topic")})

        return {
            "response": response,
            "curriculum_data": data,
            "metadata": {
                "agent": "CurriculumAgent",
                "skill": "learning-path",
                "requires_teacher_approval": requires_approval,
            },
        }


def json_safe_mastery(mastery: dict) -> str:
    if not mastery:
        return "No mastery data yet — this is a new student."
    return ", ".join(f"{t}: {s:.0%}" for t, s in mastery.items())
