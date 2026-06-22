"""
DAG Orchestrator — Directed Acyclic Graph lesson workflow.

Day 3 concept: DAG Orchestration (Section 7 of whitepaper).
State routing in a DAG does NOT rely on accumulating execution history in the LLM prompt.
Instead, each node receives a structured schema from the previous node (file message bus).

EduForge lesson DAG:
  START
    ↓
  TutorNode    — explains the topic via subject-tutor skill
    ↓ (structured output: explanation + key concepts)
  AssessmentNode — generates quiz via quiz-generator skill
    ↓ (structured output: quiz + score if answered)
  CurriculumNode — updates learning path via learning-path skill
    ↓ (structured output: next topic + encouragement)
  END

Each node:
  - Receives a structured NodeInput (not raw conversation history)
  - Produces a structured NodeOutput
  - The DAG controller routes NodeOutput → next NodeInput
  - No node sees another node's internal reasoning
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .base import AgentContext, BaseAgent
from .tutor_agent import TutorAgent
from .assessment_agent import AssessmentAgent
from .curriculum_agent import CurriculumAgent
from .safety_agent import SafetyAgent
from skills.registry import get_registry
from skills.learning_path.scripts.mastery_calculator import get_next_topic


# ---------------------------------------------------------------------------
# DAG node state schemas — the "file message bus" between nodes
# ---------------------------------------------------------------------------

@dataclass
class NodeInput:
    """Structured input passed to each DAG node."""
    node_id: str
    topic: str
    student_id: str
    subject: str
    grade_level: int
    mastery_summary: dict[str, float]
    prior_output: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class NodeOutput:
    """Structured output from each DAG node — passed to the next node as NodeInput.prior_output."""
    node_id: str
    node_type: str
    response: str
    structured_data: dict[str, Any]
    token_estimate: int
    duration_ms: float
    skill_used: str = ""
    success: bool = True
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "response": self.response,
            "structured_data": self.structured_data,
            "token_estimate": self.token_estimate,
            "duration_ms": self.duration_ms,
            "skill_used": self.skill_used,
            "success": self.success,
        }


# ---------------------------------------------------------------------------
# DAG Nodes
# ---------------------------------------------------------------------------

class TutorNode:
    """
    DAG Node 1 — Explains the topic using subject-tutor skill.
    Output: explanation text + key_concepts extracted.
    """

    NODE_TYPE = "TutorNode"

    def __init__(self, api_key: str):
        self._agent = TutorAgent(api_key)
        self._safety = SafetyAgent(api_key)
        self._registry = get_registry()

    async def run(self, node_input: NodeInput) -> NodeOutput:
        start = time.time()
        context = AgentContext(
            student_id=node_input.student_id,
            subject=node_input.subject,
            grade_level=node_input.grade_level,
            mastery_summary=node_input.mastery_summary,
            current_topic=node_input.topic,
        )

        # Load skill body (Level 2 progressive disclosure)
        loaded = self._registry.load_skill("subject-tutor")
        if loaded:
            context.active_skill_body = loaded.to_prompt_injection()

        message = f"Please explain {node_input.topic} to me."
        result = await self._agent.run(context, message)
        safety = await self._safety.run(context, result.get("response", ""))
        response = safety.get("response", result.get("response", ""))

        return NodeOutput(
            node_id=f"tutor-{node_input.correlation_id[:8]}",
            node_type=self.NODE_TYPE,
            response=response,
            structured_data={
                "topic": node_input.topic,
                "wikipedia_used": result.get("metadata", {}).get("wikipedia_used", False),
                "key_concepts": [node_input.topic],  # simplified; could extract via NLP
            },
            token_estimate=len(response) // 4,
            duration_ms=(time.time() - start) * 1000,
            skill_used="subject-tutor",
        )


class AssessmentNode:
    """
    DAG Node 2 — Generates a quiz using quiz-generator skill.
    Receives TutorNode output as context. Output: quiz_data.
    """

    NODE_TYPE = "AssessmentNode"

    def __init__(self, api_key: str):
        self._agent = AssessmentAgent(api_key)
        self._safety = SafetyAgent(api_key)
        self._registry = get_registry()

    async def run(self, node_input: NodeInput) -> NodeOutput:
        start = time.time()
        context = AgentContext(
            student_id=node_input.student_id,
            subject=node_input.subject,
            grade_level=node_input.grade_level,
            mastery_summary=node_input.mastery_summary,
            current_topic=node_input.topic,
            # Session summary carries forward from TutorNode — protected attention
            session_summary=f"Student just learned about {node_input.topic}.",
        )

        # Load skill body
        loaded = self._registry.load_skill("quiz-generator")
        if loaded:
            context.active_skill_body = loaded.to_prompt_injection()

        result = await self._agent.run(context, "generate a quiz on what I just learned")
        safety = await self._safety.run(context, result.get("response", ""))
        response = safety.get("response", result.get("response", ""))

        return NodeOutput(
            node_id=f"assessment-{node_input.correlation_id[:8]}",
            node_type=self.NODE_TYPE,
            response=response,
            structured_data={
                "quiz_data": result.get("quiz_data"),
                "topic": node_input.topic,
                "a2a_sent": result.get("metadata", {}).get("a2a_sent", False),
            },
            token_estimate=len(response) // 4,
            duration_ms=(time.time() - start) * 1000,
            skill_used="quiz-generator",
        )


class CurriculumNode:
    """
    DAG Node 3 — Updates learning path using learning-path skill + prerequisite map.
    Receives AssessmentNode output. Output: next_topic recommendation.
    """

    NODE_TYPE = "CurriculumNode"

    def __init__(self, api_key: str):
        self._agent = CurriculumAgent(api_key)
        self._registry = get_registry()

    async def run(self, node_input: NodeInput) -> NodeOutput:
        start = time.time()

        # Use deterministic mastery_calculator script (no LLM needed for this step)
        next_topic_data = get_next_topic(
            subject=node_input.subject,
            grade_level=node_input.grade_level,
            mastery_summary=node_input.mastery_summary,
        )

        context = AgentContext(
            student_id=node_input.student_id,
            subject=node_input.subject,
            grade_level=node_input.grade_level,
            mastery_summary=node_input.mastery_summary,
            current_topic=node_input.topic,
        )

        loaded = self._registry.load_skill("learning-path")
        if loaded:
            context.active_skill_body = loaded.to_prompt_injection()

        result = await self._agent.run(context, "What should I learn next?")

        next_topic = next_topic_data.get("label", node_input.topic) if next_topic_data else node_input.topic
        requires_approval = node_input.grade_level <= 6

        return NodeOutput(
            node_id=f"curriculum-{node_input.correlation_id[:8]}",
            node_type=self.NODE_TYPE,
            response=result.get("response", ""),
            structured_data={
                "next_topic": next_topic,
                "next_topic_id": next_topic_data.get("id") if next_topic_data else None,
                "requires_teacher_approval": requires_approval,
                "mastery_summary": node_input.mastery_summary,
            },
            token_estimate=len(result.get("response", "")) // 4,
            duration_ms=(time.time() - start) * 1000,
            skill_used="learning-path",
        )


# ---------------------------------------------------------------------------
# DAG Controller
# ---------------------------------------------------------------------------

@dataclass
class LessonDAGResult:
    """Final output of a complete lesson DAG run."""
    correlation_id: str
    topic: str
    nodes: list[NodeOutput]
    total_tokens: int
    total_duration_ms: float
    success: bool = True

    def to_dict(self) -> dict:
        return {
            "correlation_id": self.correlation_id,
            "topic": self.topic,
            "nodes": [n.to_dict() for n in self.nodes],
            "total_tokens": self.total_tokens,
            "total_duration_ms": self.total_duration_ms,
            "success": self.success,
            # Extract key outputs for frontend
            "explanation": next(
                (n.response for n in self.nodes if n.node_type == "TutorNode"), ""
            ),
            "quiz_data": next(
                (
                    n.structured_data.get("quiz_data")
                    for n in self.nodes
                    if n.node_type == "AssessmentNode"
                ),
                None,
            ),
            "next_topic": next(
                (
                    n.structured_data.get("next_topic")
                    for n in self.nodes
                    if n.node_type == "CurriculumNode"
                ),
                None,
            ),
            "requires_teacher_approval": next(
                (
                    n.structured_data.get("requires_teacher_approval", False)
                    for n in self.nodes
                    if n.node_type == "CurriculumNode"
                ),
                False,
            ),
        }


class LessonDAG:
    """
    DAG controller for the EduForge lesson workflow.

    Routes structured state between nodes without leaking one node's
    internal reasoning into the next node's context window.
    """

    def __init__(self, api_key: str):
        self._tutor = TutorNode(api_key)
        self._assessment = AssessmentNode(api_key)
        self._curriculum = CurriculumNode(api_key)

    async def run(
        self,
        topic: str,
        student_id: str,
        subject: str,
        grade_level: int,
        mastery_summary: dict[str, float],
    ) -> LessonDAGResult:
        """
        Execute the full lesson DAG: Tutor → Assessment → Curriculum.
        State flows through NodeInput/NodeOutput — never through raw conversation history.
        """
        correlation_id = str(uuid.uuid4())
        nodes: list[NodeOutput] = []
        start_total = time.time()

        base_input = NodeInput(
            node_id="start",
            topic=topic,
            student_id=student_id,
            subject=subject,
            grade_level=grade_level,
            mastery_summary=mastery_summary,
            correlation_id=correlation_id,
        )

        try:
            # Node 1: Tutor
            tutor_output = await self._tutor.run(base_input)
            nodes.append(tutor_output)

            # Node 2: Assessment (receives tutor output as prior_output)
            assessment_input = NodeInput(
                node_id="assessment",
                topic=topic,
                student_id=student_id,
                subject=subject,
                grade_level=grade_level,
                mastery_summary=mastery_summary,
                prior_output=tutor_output.to_dict(),
                correlation_id=correlation_id,
            )
            assessment_output = await self._assessment.run(assessment_input)
            nodes.append(assessment_output)

            # Node 3: Curriculum (receives assessment output as prior_output)
            curriculum_input = NodeInput(
                node_id="curriculum",
                topic=topic,
                student_id=student_id,
                subject=subject,
                grade_level=grade_level,
                mastery_summary=mastery_summary,
                prior_output=assessment_output.to_dict(),
                correlation_id=correlation_id,
            )
            curriculum_output = await self._curriculum.run(curriculum_input)
            nodes.append(curriculum_output)

        except Exception as e:
            return LessonDAGResult(
                correlation_id=correlation_id,
                topic=topic,
                nodes=nodes,
                total_tokens=sum(n.token_estimate for n in nodes),
                total_duration_ms=(time.time() - start_total) * 1000,
                success=False,
            )

        return LessonDAGResult(
            correlation_id=correlation_id,
            topic=topic,
            nodes=nodes,
            total_tokens=sum(n.token_estimate for n in nodes),
            total_duration_ms=(time.time() - start_total) * 1000,
            success=True,
        )
