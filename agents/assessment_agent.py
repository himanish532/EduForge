"""
AssessmentAgent — Generates quizzes and scores answers.

Day 2 upgrade:
  - Uses ProgressDBMCPServer via MCPClient to read prior performance
  - Emits A2A message to CurriculumAgent after scoring (Assessment→Curriculum flow)

Skill: quiz-generator
MCP tools used: get_student_progress, update_mastery, record_session_event
A2A output: assessment_result → CurriculumAgent
"""

from __future__ import annotations

from .base import AgentContext, BaseAgent
from .a2a import A2AMessage, get_router
from mcp_servers import ProgressDBMCPServer, MCPClient

ASSESSMENT_SYSTEM_PROMPT = """
You are an educational assessment specialist. Generate quizzes that test deep understanding,
not memorization.

Rules:
1. Create exactly 1 multiple-choice question on the topic: {topic}
2. Provide exactly 4 options (A, B, C, D). Only ONE is correct.
3. Difficulty matches mastery level: {difficulty} (student mastery: {mastery:.0%})
4. The explanation must teach, not just confirm the answer.
5. Keep language appropriate for grade {grade_level}.

Respond ONLY with valid JSON — no extra text, no markdown code fences:
{{
  "question": "...",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "correct_index": 0,
  "explanation": "...",
  "topic": "{topic}",
  "difficulty": "{difficulty}"
}}
""".strip()


class AssessmentAgent(BaseAgent):
    """
    Quiz generation agent with MCP-backed progress tracking and A2A output.
    """

    def __init__(self, api_key: str):
        super().__init__(api_key)
        # MCP Connection to Progress DB
        self._db_server = ProgressDBMCPServer()
        self._db_client = MCPClient(self._db_server)
        self._log(
            "mcp_connected",
            {
                "server": self._db_server.name,
                "tools": [t.name for t in self._db_client.list_tools()],
            },
        )

    def _get_difficulty(self, mastery: float) -> str:
        if mastery < 0.4:
            return "beginner"
        elif mastery < 0.75:
            return "intermediate"
        return "advanced"

    async def run(self, context: AgentContext, message: str) -> dict:
        self._log("assessment_start", {"topic": context.current_topic})

        # Fetch prior performance via MCP
        try:
            prior_progress = await self._db_client.call(
                "get_student_progress", student_id=context.student_id
            )
            # Merge MCP data into context mastery summary
            for topic, data in prior_progress.items():
                if topic not in context.mastery_summary:
                    context.mastery_summary[topic] = data.get("score", 0.0)
        except Exception as e:
            self._log("mcp_error", {"error": str(e)})

        topic = context.current_topic or context.subject
        mastery = context.mastery_summary.get(topic, 0.0)
        difficulty = self._get_difficulty(mastery)

        system_prompt = ASSESSMENT_SYSTEM_PROMPT.format(
            topic=topic,
            difficulty=difficulty,
            mastery=mastery,
            grade_level=context.grade_level,
        )

        prompt = f"{system_prompt}\n\nGenerate the quiz question now."
        raw = self._call_llm(prompt, json_output=True)

        try:
            quiz = self._parse_json(raw)
        except Exception as e:
            self._log("quiz_parse_error", {"error": str(e), "raw": raw[:200]})
            quiz = {
                "question": f"What is an important concept in {topic}?",
                "options": ["A. Option A", "B. Option B", "C. Option C", "D. Option D"],
                "correct_index": 0,
                "explanation": "Could not generate quiz. Please try again.",
                "topic": topic,
                "difficulty": difficulty,
            }

        # Record session event via MCP
        try:
            await self._db_client.call(
                "record_session_event",
                student_id=context.student_id,
                event_type="quiz",
                topic=topic,
                data={"difficulty": difficulty, "mastery_at_time": mastery},
            )
        except Exception:
            pass

        # A2A: emit assessment_result to CurriculumAgent
        # This is the A2A flow — Assessment notifies Curriculum of the quiz attempt
        a2a_message = A2AMessage(
            type="assessment_result",
            sender="AssessmentAgent",
            recipient="CurriculumAgent",
            payload={
                "student_id": context.student_id,
                "topic": topic,
                "difficulty": difficulty,
                "mastery_before": mastery,
                "quiz_generated": True,
            },
            requires_acknowledgment=False,
        )
        try:
            await get_router().send(a2a_message)
            self._log("a2a_sent", {"type": a2a_message.type, "recipient": "CurriculumAgent"})
        except Exception:
            pass  # A2A delivery failure is non-fatal for quiz generation

        # Format chat response
        opts = "\n".join(quiz.get("options", []))
        chat_response = f"**Quiz Time!** 🎯\n\n**{quiz['question']}**\n\n{opts}\n\n*Click an option in the quiz panel below, or type your answer.*"

        self._log("assessment_complete", {"topic": topic, "difficulty": difficulty})

        return {
            "response": chat_response,
            "quiz_data": quiz,
            "metadata": {
                "agent": "AssessmentAgent",
                "skill": "quiz-generator",
                "type": "quiz_generated",
                "mcp_server": self._db_server.name,
                "a2a_sent": True,
            },
        }

    async def score_answer(
        self,
        context: AgentContext,
        quiz: dict,
        selected_index: int,
    ) -> dict:
        """Score a submitted quiz answer and emit A2A result to CurriculumAgent."""
        topic = quiz.get("topic", context.current_topic)
        correct_index = quiz.get("correct_index", 0)
        is_correct = selected_index == correct_index
        score = 1.0 if is_correct else 0.0
        explanation = quiz.get("explanation", "")

        # Update mastery via MCP
        try:
            existing = context.mastery_summary.get(topic, 0.0)
            # Weighted average: new score counts 30%, prior mastery 70%
            new_mastery = existing * 0.7 + score * 0.3
            await self._db_client.call(
                "update_mastery",
                student_id=context.student_id,
                topic=topic,
                score=new_mastery,
                attempts=1,
            )
            context.mastery_summary[topic] = new_mastery
        except Exception as e:
            self._log("mastery_update_error", {"error": str(e)})

        # A2A: send scored result to CurriculumAgent
        a2a_message = A2AMessage(
            type="assessment_result",
            sender="AssessmentAgent",
            recipient="CurriculumAgent",
            payload={
                "student_id": context.student_id,
                "topic": topic,
                "score": score,
                "is_correct": is_correct,
                "mastery_updated": context.mastery_summary.get(topic, 0.0),
            },
            requires_acknowledgment=True,
        )
        try:
            await get_router().send(a2a_message)
        except Exception:
            pass

        feedback = (
            f"✅ **Correct!** {explanation}"
            if is_correct
            else f"❌ **Not quite.** The correct answer was **{quiz['options'][correct_index]}**.\n\n{explanation}"
        )

        return {
            "correct": is_correct,
            "score": score,
            "feedback": feedback,
            "updated_mastery": context.mastery_summary.get(topic, 0.0),
            "topic": topic,
        }
