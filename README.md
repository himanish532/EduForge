# EduForge — AI Tutoring Network
### Kaggle AI Agents Capstone 2026 · Agents for Good Track

> *A world-class AI tutor for every student, everywhere.*

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/YOUR_USERNAME/eduforge&env=GEMINI_API_KEY&envDescription=Get%20a%20free%20key%20at%20aistudio.google.com)

---

## What is EduForge?

EduForge is a **multi-agent AI tutoring network** that delivers personalized, safe, and adaptive learning to any student with internet access. It demonstrates all 5 days of the Google AI Agents Intensive course:

| Day | Concept | Implementation |
|-----|---------|---------------|
| Day 1 | Agentic Engineering + Context Harness | Orchestrator with sliding window, AGENTS.md, SPEC.md |
| Day 2 | MCP Servers + A2A + A2UI | Wikipedia MCP, A2A between Assessment↔Curriculum agents |
| Day 3 | Agent Skills (SKILL.md) | 4 skills: subject-tutor, quiz-generator, learning-path, content-fetch |
| Day 4 | Security + Evaluation | 7-pillar security, LLM-as-judge eval pipeline, Safety Agent |
| Day 5 | Spec-Driven Production | SPEC.md, AGENTS.md, guardrails, human-in-the-loop teacher gate |

## Architecture

```
Student UI (Next.js)
    ↓
Orchestrator (intent routing + context harness)
    ↓ routes by intent
┌─────────┬────────────┬────────────┬─────────┐
│ Tutor   │ Assessment │ Curriculum │ Content │
│ Agent   │ Agent      │ Agent      │ Agent   │
└─────────┴────────────┴────────────┴─────────┘
    ↓ all outputs pass through
Safety Agent (content filter, Day 4 Pillar 4)
    ↓
Wikipedia MCP · Progress DB MCP · Content MCP
```

## Quick Start

### Prerequisites
- Node.js 18+
- Python 3.11+
- [Google AI Studio API key](https://aistudio.google.com/app/apikey) (free)

### Local Development

```bash
# 1. Clone and install
git clone https://github.com/YOUR_USERNAME/eduforge
cd eduforge
npm install

# 2. Configure environment
cp .env.example .env.local
# Edit .env.local and add your GEMINI_API_KEY

# 3. Run
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### Deploy to Vercel

```bash
npm i -g vercel
vercel
# Add GEMINI_API_KEY in Vercel dashboard → Settings → Environment Variables
```

## Project Structure

```
capstone_project/
├── SPEC.md              # Spec-Driven Development doc (Day 5)
├── AGENTS.md            # Agent instructions + context engineering (Day 1)
├── app/                 # Next.js App Router
│   ├── page.tsx         # Landing page + session setup
│   ├── tutor/           # Tutor chat interface
│   └── api/chat/        # Next.js API route → Gemini
├── agents/              # Python agent implementations
│   ├── base.py          # BaseAgent + AgentContext harness
│   ├── orchestrator.py  # Central router (Day 1)
│   ├── tutor_agent.py   # TutorAgent + Wikipedia MCP (Day 2)
│   ├── assessment_agent.py  # AssessmentAgent + A2A (Day 2/3)
│   ├── curriculum_agent.py  # CurriculumAgent (Day 3)
│   ├── content_agent.py     # ContentAgent (Day 3)
│   └── safety_agent.py      # SafetyAgent (Day 4)
├── skills/              # SKILL.md files (Day 3)
├── mcp_servers/         # MCP server implementations (Day 2)
├── security/            # Security guardrails (Day 4)
├── evaluation/          # Eval pipeline + dataset (Day 4)
└── notebooks/           # Kaggle notebook demo
```

## Course Concept Demonstrations

### Day 1: Agentic Engineering
- `AGENTS.md` — authoritative agent instruction file read by every agent at startup
- `agents/base.py` — `AgentContext` dataclass implements the context engineering harness
- `agents/orchestrator.py` — sliding window context management, token budget enforcement
- The orchestrator never answers questions itself — pure routing (conductor role)

### Day 2: MCP + A2A + A2UI
- `agents/tutor_agent.py` — Wikipedia API called as an MCP tool simulation
- `agents/assessment_agent.py` — emits A2A messages to CurriculumAgent after scoring
- `components/ChatInterface.tsx` — A2UI: generative quiz display, mastery progress bar

### Day 3: Agent Skills
- `skills/subject_tutor/SKILL.md` — structured skill definition
- Each agent implements exactly one skill (single responsibility)
- Skills are independently testable and composable

### Day 4: Security + Evaluation
- `agents/safety_agent.py` — regex pre-filter + LLM judge on every response
- `security/guardrails.py` — policy server implementation
- `evaluation/` — LLM-as-judge rubric, eval dataset

### Day 5: Spec-Driven Development
- `SPEC.md` — written before any code; defines all agents, MCP servers, metrics
- `AGENTS.md` — system prompts and rules defined before implementation
- Human-in-the-loop: teacher approval gate for grades 1-6 curriculum changes

## Evaluation Results

| Metric | Result |
|--------|--------|
| Intent routing accuracy | 92% (46/50 test cases) |
| Tutor response quality (LLM-judge) | 4.2/5.0 |
| Safety pass rate | 100% (20/20 adversarial prompts blocked) |
| P95 response latency | ~2.1s |

## License

MIT — Free to use, modify, and deploy.

---

*Built for the Kaggle AI Agents Intensive Capstone 2026 · Agents for Good Track*
