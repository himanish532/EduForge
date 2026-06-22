"""
CurriculumAgent — Maintains and adapts the student's personalized learning path.

Day 2 upgrade:
  - Receives A2A messages from AssessmentAgent (assessment_result)
  - Uses ProgressDBMCPServer for persistent mastery storage

Skill: learning-path
MCP tools: get_student_progress, update_mastery, record_session_event
A2A input: assessment_result from AssessmentAgent
"""

from __future__ import annotations

from .base import AgentContext, BaseAgent
from .a2a import A2AMessage, get_router
from mcp_servers import ProgressDBMCPServer, MCPClient

CURRICULUM_SYSTEM_PROMPT = """
You are a personalized curriculum designer. Look at the student's mastery and recommend the next step.

Mastery thresholds:
- < 0.4 → needs foundational work
- 0.4-0.79 → progressing, keep practicing
- ≥ 0.8 across 3+ attempts → mastered, unlock next topic

Student: Grade {grade_level} | Subject: {subject}
Current mastery: {mastery}

Rules:
1. Recommend the next topic: lowest mastery that is unlocked.
2. If all topics mastered, suggest an advanced challenge.
3. Never skip prerequisites.
4. Grades 1-6 require teacher approval for curriculum changes.

Respond with JSON only:
{{
  "next_topic": "...",
  "reason": "...",
  "encouragement": "one warm sentence",
  "requires_teacher_approval": true/false
}}
""".strip()


class CurriculumAgent(BaseAgent):

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self._db_server = ProgressDBMCPServer()
        self._db_client = MCPClient(self._db_server)

        # Register A2A handler for assessment_result messages
        router = get_router()
        router.register("CurriculumAgent", "assessment_result", self._handle_assessment_result)
        self._log("a2a_registered", {"message_type": "assessment_result"})

    async def _handle_assessment_result(self, message: A2AMessage) -> dict:
        """
        A2A handler: receives scoring results from AssessmentAgent.
        Updates mastery in ProgressDB via MCP.
        """
        payload = message.payload
        student_id = payload.get("student_id", "anonymous")
        topic = payload.get("topic", "")
        score = payload.get("score")

        if score is not None and topic:
            try:
                await self._db_client.call(
                    "update_mastery",
                    student_id=student_id,
                    topic=topic,
                    score=score,
                    attempts=1,
                )
                self._log("a2a_mastery_updated", {"topic": topic, "score": score})
            except Exception as e:
                self._log("a2a_mastery_error", {"error": str(e)})

        return {"acknowledged": True, "topic": topic}

    async def run(self, context: AgentContext, message: str) -> dict:
        self._log("curriculum_start", {"mastery": context.mastery_summary})

        # Fetch full progress from ProgressDB via MCP
        try:
            db_progress = await self._db_client.call(
                "get_student_progress", student_id=context.student_id
            )
            for topic, data in db_progress.items():
                if topic not in context.mastery_summary:
                    context.mastery_summary[topic] = data.get("score", 0.0)
        except Exception as e:
            self._log("mcp_error", {"error": str(e)})

        mastery_text = (
            ", ".join(f"{t}: {s:.0%}" for t, s in context.mastery_summary.items())
            if context.mastery_summary
            else "No mastery data yet"
        )

        system_prompt = CURRICULUM_SYSTEM_PROMPT.format(
            grade_level=context.grade_level,
            subject=context.subject,
            mastery=mastery_text,
        )

        prompt = f"{system_prompt}\n\nStudent request: {message}"
        raw = self._call_llm(prompt, json_output=True)

        try:
            data = self._parse_json(raw)
        except Exception:
            data = {
                "next_topic": context.current_topic or context.subject,
                "reason": "Continue building on your current topic.",
                "encouragement": "You're making great progress — keep it up!",
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

        # Record session event via MCP
        try:
            await self._db_client.call(
                "record_session_event",
                student_id=context.student_id,
                event_type="curriculum",
                topic=data.get("next_topic", ""),
                data={"requires_approval": requires_approval},
            )
        except Exception:
            pass

        self._log("curriculum_complete", {"next_topic": data.get("next_topic")})

        return {
            "response": response,
            "curriculum_data": data,
            "metadata": {
                "agent": "CurriculumAgent",
                "skill": "learning-path",
                "requires_teacher_approval": requires_approval,
                "mcp_server": self._db_server.name,
            },
        }
