"""
AssessmentAgent — Generates quizzes and scores answers.

Skill: quiz-generator
A2A: Emits assessment_result messages to CurriculumAgent
"""

from __future__ import annotations

import json

from .base import AgentContext, BaseAgent

ASSESSMENT_SYSTEM_PROMPT = """
You are an educational assessment specialist. Generate quizzes that test deep understanding,
not memorization.

Rules:
1. Create exactly 1 multiple-choice question on the student's current topic.
2. Provide exactly 4 options (A, B, C, D). Only ONE is correct.
3. Match difficulty to the student's mastery level.
4. The explanation must teach, not just confirm the answer.
5. Keep the question clear and unambiguous.

Student grade: {grade_level} | Subject: {subject} | Topic: {topic}
Mastery level: {mastery}

Respond ONLY with valid JSON — no extra text:
{{
  "question": "...",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "correct_index": 0,
  "explanation": "...",
  "topic": "{topic}",
  "difficulty": "beginner|intermediate|advanced"
}}
""".strip()

SCORING_SYSTEM_PROMPT = """
A student answered a quiz question. Evaluate their answer and provide warm, educational feedback.

Question: {question}
Correct answer: {correct_option}
Student's answer: {student_answer}

Respond with JSON:
{{
  "correct": true/false,
  "score": 0.0-1.0,
  "feedback": "encouraging, educational feedback in 2-3 sentences",
  "hint": "if wrong: a helpful hint toward the right answer (don't reveal it)"
}}
""".strip()


class AssessmentAgent(BaseAgent):

    async def run(self, context: AgentContext, message: str) -> dict:
        self._log("assessment_start", {"message": message[:80]})

        # Detect if this is a quiz request or an answer to a prior quiz
        msg_lower = message.lower()
        is_answer = any(w in msg_lower for w in ["answer is", "i think", "my answer", "option", " a ", " b ", " c ", " d "])

        if is_answer:
            return await self._score_answer(context, message)
        else:
            return await self._generate_quiz(context)

    async def _generate_quiz(self, context: AgentContext) -> dict:
        mastery = context.mastery_summary.get(context.current_topic, 0.0)
        if mastery < 0.4:
            difficulty = "beginner"
        elif mastery < 0.7:
            difficulty = "intermediate"
        else:
            difficulty = "advanced"

        system_prompt = ASSESSMENT_SYSTEM_PROMPT.format(
            grade_level=context.grade_level,
            subject=context.subject,
            topic=context.current_topic or context.subject,
            mastery=f"{mastery:.0%}",
        )

        prompt = f"{system_prompt}\n\nGenerate a {difficulty} quiz question."
        raw = self._call_llm(prompt, json_output=True)

        try:
            quiz = self._parse_json(raw)
        except Exception:
            quiz = {
                "question": f"What is an important concept in {context.current_topic}?",
                "options": ["A. Option A", "B. Option B", "C. Option C", "D. Option D"],
                "correct_index": 0,
                "explanation": "Please try again — I had trouble generating a quiz.",
                "topic": context.current_topic,
                "difficulty": difficulty,
            }

        self._log("quiz_generated", {"topic": context.current_topic, "difficulty": difficulty})

        # Format a readable response for the chat UI
        opts = "\n".join(quiz.get("options", []))
        response = f"**Quiz Time!** 🎯\n\n{quiz['question']}\n\n{opts}"

        return {
            "response": response,
            "quiz_data": quiz,
            "metadata": {
                "agent": "AssessmentAgent",
                "skill": "quiz-generator",
                "type": "quiz_generated",
            },
        }

    async def _score_answer(self, context: AgentContext, student_answer: str) -> dict:
        # In a real implementation, we'd look up the pending quiz from session state.
        # For now, acknowledge the answer and give constructive feedback.
        response = (
            "Thanks for your answer! To get full scoring, please use the quiz panel "
            "where you can click your chosen option. Keep up the great work! 💪"
        )
        return {
            "response": response,
            "metadata": {"agent": "AssessmentAgent", "type": "answer_acknowledged"},
        }
