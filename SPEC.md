# EduForge — Specification Document
**Version:** 1.0  
**Author:** Himanish Kopalle  
**Capstone Track:** Agents for Good  
**Submission Deadline:** July 6, 2026

---

## 1. Problem Statement

250 million children worldwide lack access to quality tutors. Static chatbots fail because learning requires:
- Adaptive explanation (meeting the student where they are)
- Assessment to confirm understanding
- Personalized curriculum progression
- Safe, age-appropriate content

EduForge is a multi-agent AI tutoring network that delivers a world-class personalized tutor to any student with internet access.

---

## 2. System Goals

| Goal | Metric |
|------|--------|
| Explain any concept in any subject | Tutor agent response quality ≥ 4/5 (LLM-judge) |
| Generate contextual quizzes | Quiz relevance score ≥ 4/5 |
| Personalize learning path | Curriculum adapts within 3 sessions |
| Ensure content safety | Zero unsafe outputs in eval dataset |
| Production-grade reliability | < 3s p95 latency per agent response |

---

## 3. Architecture Overview

### 3.1 Layers

```
[Student / Teacher UI]  ←→  [A2UI Generative Interface]
         ↓
[EduForge Orchestrator]  — context harness, intent routing, session state
         ↓ (routes by subject + intent)
┌─────────────┬──────────────────┬─────────────────┬──────────────┬──────────────┐
│ Tutor Agent │ Assessment Agent │ Curriculum Agent │ Content Agent│ Safety Agent │
└─────────────┴──────────────────┴─────────────────┴──────────────┴──────────────┘
         ↓ (MCP tool calls)
┌──────────────────┬──────────────────┬──────────────────┬──────────────────┐
│  Wikipedia MCP   │  Progress DB MCP │  Content MCP     │  CalDAV MCP      │
└──────────────────┴──────────────────┴──────────────────┴──────────────────┘
```

### 3.2 Data Flow

1. Student sends message → Orchestrator receives with full session context
2. Orchestrator classifies intent → routes to appropriate specialist agent(s)
3. Specialist agent calls relevant MCP tools → generates response
4. Safety Agent validates response → strips/flags unsafe content
5. Response returned to UI → session state updated in Progress DB

---

## 4. Agent Specifications

### 4.1 Orchestrator
- **Purpose:** Central router and context manager
- **Inputs:** Student message, session state, subject, grade level
- **Outputs:** Structured directive to specialist agent(s)
- **Context window budget:** 8K tokens (trimmed via sliding window)
- **Routing logic:** Intent classifier → {explain, quiz, progress, content, schedule}

### 4.2 Tutor Agent
- **Purpose:** Explain concepts using Socratic dialogue
- **Skill:** `subject-tutor`
- **Tools:** Wikipedia MCP (lookup), Content MCP (examples)
- **Persona:** Patient, encouraging, grade-appropriate language
- **Constraint:** Never give answers directly — guide through questions first

### 4.3 Assessment Agent
- **Purpose:** Generate quizzes, score answers, provide feedback
- **Skill:** `quiz-generator`
- **Tools:** Progress DB MCP (fetch prior quiz results)
- **Output format:** Structured JSON `{question, options[], correct_index, explanation}`
- **A2A:** Sends scored results to Curriculum Agent via A2A message

### 4.4 Curriculum Agent
- **Purpose:** Maintain and adapt the student's learning path
- **Skill:** `learning-path`
- **Tools:** Progress DB MCP (read/write mastery levels)
- **A2A:** Receives assessment results, updates topic mastery graph
- **Output:** Next recommended topic + reason

### 4.5 Content Agent
- **Purpose:** Fetch and summarize supplementary resources
- **Skill:** `content-fetch`
- **Tools:** Wikipedia MCP, Content MCP (YouTube/docs references)
- **Constraint:** Only READ access to external APIs, never write

### 4.6 Safety Agent
- **Purpose:** Filter all outbound content for age-appropriateness
- **Security pillar:** Pillar 4 (Application Logic Security)
- **Runs:** As a post-processing step on every agent response
- **On violation:** Redacts content, logs audit event, notifies orchestrator

---

## 5. MCP Server Specifications

### 5.1 Wikipedia MCP
- **Endpoint:** `tools/search_wikipedia(query: str) → str`
- **Endpoint:** `tools/get_article_summary(title: str) → str`
- **Rate limit:** 10 req/min per session

### 5.2 Progress DB MCP
- **Endpoint:** `tools/get_student_progress(student_id: str) → dict`
- **Endpoint:** `tools/update_mastery(student_id: str, topic: str, score: float) → void`
- **Storage:** SQLite (local dev), PostgreSQL (production)

### 5.3 Content MCP
- **Endpoint:** `tools/find_resources(topic: str, type: str) → list[dict]`
- **Returns:** Title, URL, type (video/article/exercise), difficulty level

---

## 6. Agent Skills

Each skill is defined by a `SKILL.md` file and implemented as a callable module.

| Skill | Trigger phrase | Output |
|-------|---------------|--------|
| `subject-tutor` | "explain", "what is", "how does", "help me understand" | Socratic explanation + follow-up question |
| `quiz-generator` | "quiz me", "test me", "practice", "question" | JSON quiz object |
| `learning-path` | "what should I learn next", "my progress", "curriculum" | Next topic + mastery summary |
| `content-fetch` | "show me", "find resources", "video about", "examples of" | Curated resource list |

---

## 7. Security Architecture (Day 4)

### 7-Pillar Implementation

| Pillar | Implementation |
|--------|---------------|
| 1. Sandboxing | Each agent runs in isolated async context; no shared mutable state |
| 2. Input validation | All student inputs sanitized before passing to agents |
| 3. Output filtering | Safety Agent post-processes every response |
| 4. App logic security | MCP servers enforce read-only for Content Agent |
| 5. Identity & trust | Session tokens; teacher approval gate for curriculum changes |
| 6. Observability | Structured audit logs for every agent action |
| 7. Supply chain | Pinned dependencies; no agent can install packages at runtime |

---

## 8. Evaluation Framework (Day 4)

### 8.1 Metrics

| Metric | Method | Target |
|--------|--------|--------|
| Response quality | LLM-as-judge (1-5 rubric) | ≥ 4.0 |
| Quiz relevance | LLM-as-judge | ≥ 4.0 |
| Safety pass rate | Rule-based + LLM judge | 100% |
| Intent routing accuracy | Ground-truth dataset (50 samples) | ≥ 90% |
| Token budget adherence | Hard counter per session | < 8K |

### 8.2 Eval Dataset
- 50 student queries across 5 subjects × 5 grade levels
- 20 adversarial prompts (jailbreak attempts, off-topic requests)
- Stored in `evaluation/eval_dataset.json`

---

## 9. Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Backend | Python FastAPI (Vercel serverless) |
| Agent framework | Google ADK (google-adk) |
| LLM | Gemini 2.0 Flash |
| MCP | Custom FastMCP servers (Python) |
| State | SQLite (dev) / Vercel KV (prod) |
| Hosting | Vercel (frontend + Python API) |
| Auth | Vercel environment variables for API keys |

---

## 10. Deployment

```
GitHub repo → Vercel auto-deploy
├── / (Next.js frontend)
└── /api/* (Python serverless functions)
    ├── /api/chat      → Orchestrator + Tutor Agent
    ├── /api/quiz      → Assessment Agent
    ├── /api/curriculum → Curriculum Agent
    └── /api/safety    → Safety Agent (internal)
```

Environment variables required:
- `GEMINI_API_KEY` — Google AI Studio API key
- `DATABASE_URL` — (optional) production DB

---

## 11. Course Concept Coverage

| Day | Concept | Where Used |
|-----|---------|-----------|
| Day 1 | Agentic Engineering, Context Harness, AGENTS.md | Orchestrator, this SPEC.md |
| Day 1 | Conductor vs Orchestrator roles | Teacher human-in-the-loop gate |
| Day 2 | MCP Servers | Wikipedia, Progress DB, Content MCP |
| Day 2 | A2A Protocol | Assessment → Curriculum agent messaging |
| Day 2 | A2UI | Generative quiz UI, progress dashboard |
| Day 3 | Agent Skills (SKILL.md) | 4 skills: tutor, quiz, path, content |
| Day 3 | DAG Orchestration | Curriculum agent composes tutor + assessment skills |
| Day 3 | Skill Evaluation | Eval coverage checklist per skill |
| Day 4 | 7-Pillar Security | Safety agent, sandboxing, audit logs |
| Day 4 | Evaluation Pipeline | LLM-as-judge, intent drift detection |
| Day 5 | Spec-Driven Development | This document + AGENTS.md |
| Day 5 | Human-in-the-Loop | Teacher review gate for curriculum |
| Day 5 | AI-Generated Tests | Eval dataset auto-generation |
| Day 5 | Guardrails / Zero-Trust | Policy server, JIT downscoping |
