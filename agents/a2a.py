"""
A2A Protocol — Agent-to-Agent interoperability layer.

Implements the A2A standard as described in the Day 2 whitepaper:
  - AgentCard: machine-readable agent identity (the "CV" of each agent)
  - A2AMessage: structured inter-agent message with correlation tracking
  - A2ARouter: dispatches messages to registered agent handlers

In a distributed deployment, the A2ARouter would route over HTTP/SSE.
Here it operates in-process (equivalent to stdio transport).

Key concept: A2A is NOT the same as an MCP tool call.
  - MCP tool: fire-and-forget, single structured request/response
  - A2A message: multi-turn, stateful, collaborative — agent can pause and negotiate
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable


# ---------------------------------------------------------------------------
# Agent Card — the standardised "CV" for each agent in the EduForge network
# ---------------------------------------------------------------------------

@dataclass
class AgentCapability:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class AgentCard:
    """
    Machine-readable agent identity per A2A spec.
    Every agent in EduForge exposes an AgentCard so the Orchestrator
    can discover it, understand its capabilities, and route to it.
    """

    agent_id: str
    name: str
    description: str
    version: str
    capabilities: list[AgentCapability]
    interaction_schema: dict[str, Any]
    security_policy: dict[str, Any] = field(default_factory=dict)
    endpoint: str = "in-process"  # "in-process" for local; URL for remote agents

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "endpoint": self.endpoint,
            "capabilities": [
                {"name": c.name, "description": c.description}
                for c in self.capabilities
            ],
            "interaction_schema": self.interaction_schema,
            "security_policy": self.security_policy,
        }


# Pre-defined Agent Cards for EduForge agents
AGENT_CARDS: dict[str, AgentCard] = {
    "TutorAgent": AgentCard(
        agent_id="eduforge.tutor.v1",
        name="TutorAgent",
        description="Explains educational concepts through Socratic dialogue.",
        version="1.0",
        capabilities=[
            AgentCapability(
                name="explain",
                description="Explain a concept at the appropriate grade level",
                input_schema={"topic": "string", "grade_level": "integer", "subject": "string"},
            )
        ],
        interaction_schema={"message_types": ["explain_request", "explain_response"]},
        security_policy={"readonly": True, "allowed_tools": ["search_wikipedia", "get_article_summary"]},
    ),
    "AssessmentAgent": AgentCard(
        agent_id="eduforge.assessment.v1",
        name="AssessmentAgent",
        description="Generates adaptive quizzes and scores student answers.",
        version="1.0",
        capabilities=[
            AgentCapability(
                name="generate_quiz",
                description="Generate a quiz question for a topic at a given mastery level",
                input_schema={"topic": "string", "mastery": "float", "grade_level": "integer"},
            ),
            AgentCapability(
                name="score_answer",
                description="Score a student's quiz answer",
                input_schema={"question": "string", "answer": "string", "correct_index": "integer"},
            ),
        ],
        interaction_schema={"message_types": ["quiz_request", "assessment_result"]},
        security_policy={"allowed_tools": ["get_student_progress", "update_mastery"]},
    ),
    "CurriculumAgent": AgentCard(
        agent_id="eduforge.curriculum.v1",
        name="CurriculumAgent",
        description="Maintains and adapts the student's personalized learning path.",
        version="1.0",
        capabilities=[
            AgentCapability(
                name="update_path",
                description="Update learning path based on assessment results",
                input_schema={"student_id": "string", "topic": "string", "score": "float"},
            )
        ],
        interaction_schema={"message_types": ["assessment_result", "curriculum_update"]},
        security_policy={"allowed_tools": ["get_student_progress", "update_mastery", "record_session_event"]},
    ),
    "ContentAgent": AgentCard(
        agent_id="eduforge.content.v1",
        name="ContentAgent",
        description="Curates supplementary learning resources.",
        version="1.0",
        capabilities=[
            AgentCapability(
                name="find_resources",
                description="Find free educational resources for a topic",
                input_schema={"topic": "string", "subject": "string", "grade_level": "integer"},
            )
        ],
        interaction_schema={"message_types": ["resource_request", "resource_response"]},
        security_policy={"readonly": True, "allowed_tools": ["find_resources", "search_wikipedia"]},
    ),
    "SafetyAgent": AgentCard(
        agent_id="eduforge.safety.v1",
        name="SafetyAgent",
        description="Content safety filter — post-processes all agent outputs.",
        version="1.0",
        capabilities=[
            AgentCapability(
                name="check_safety",
                description="Validate content for age-appropriateness",
                input_schema={"content": "string", "grade_level": "integer"},
            )
        ],
        interaction_schema={"message_types": ["safety_check_request", "safety_check_response"]},
        security_policy={"readonly": True, "allowed_tools": []},
    ),
}


# ---------------------------------------------------------------------------
# A2A Message — the envelope for inter-agent communication
# ---------------------------------------------------------------------------

@dataclass
class A2AMessage:
    """
    Structured message passed between agents via the A2A protocol.

    Unlike MCP tool calls (fire-and-forget), A2A messages support
    multi-turn stateful collaboration tracked by correlation_id.
    """

    type: str                          # e.g. "assessment_result", "curriculum_update"
    sender: str                        # sending agent name
    recipient: str                     # receiving agent name
    payload: dict[str, Any]           # message body
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    requires_acknowledgment: bool = False
    status: str = "pending"            # pending | delivered | acknowledged | failed

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "sender": self.sender,
            "recipient": self.recipient,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "status": self.status,
        }


# ---------------------------------------------------------------------------
# A2A Router — dispatches messages between registered agents
# ---------------------------------------------------------------------------

AgentHandler = Callable[[A2AMessage], Awaitable[dict]]


class A2ARouter:
    """
    In-process A2A router. In a distributed system this would route over HTTP/SSE.

    Agents register handlers for specific message types.
    The Orchestrator (or any agent) sends messages; the router delivers them.
    """

    def __init__(self):
        self._handlers: dict[str, dict[str, AgentHandler]] = {}
        self._message_log: list[A2AMessage] = []

    def register(self, agent_name: str, message_type: str, handler: AgentHandler) -> None:
        """Register an agent's handler for a specific message type."""
        if agent_name not in self._handlers:
            self._handlers[agent_name] = {}
        self._handlers[agent_name][message_type] = handler

    async def send(self, message: A2AMessage) -> dict | None:
        """
        Send an A2A message to the recipient agent.
        Returns the handler's response, or None if no handler registered.
        """
        self._message_log.append(message)
        agent_handlers = self._handlers.get(message.recipient, {})
        handler = agent_handlers.get(message.type)

        if handler is None:
            message.status = "failed"
            return None

        try:
            result = await handler(message)
            message.status = "delivered"
            return result
        except Exception as e:
            message.status = "failed"
            raise

    def get_agent_card(self, agent_name: str) -> AgentCard | None:
        """Discover an agent's capabilities via its AgentCard."""
        return AGENT_CARDS.get(agent_name)

    def list_agents(self) -> list[dict]:
        """List all registered agents and their cards — the A2A registry."""
        return [card.to_dict() for card in AGENT_CARDS.values()]

    def get_message_log(self) -> list[dict]:
        return [m.to_dict() for m in self._message_log]


# Singleton router used across all agents in a request lifecycle
_global_router = A2ARouter()


def get_router() -> A2ARouter:
    return _global_router
