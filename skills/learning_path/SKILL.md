# Skill: learning-path

**Trigger phrases:** "what should I learn next", "my progress", "curriculum", "learning path", "what's next"

**Description:**
Maintains the student's topic mastery graph and recommends the optimal next learning step.
Sends curriculum updates through the human-in-the-loop teacher gate for grades 1-6.

**Input:**
- `context.mastery_summary` — full mastery graph {topic: score}
- `context.grade_level` — determines if teacher approval is required
- A2A: `assessment_result` messages from AssessmentAgent

**Output format:**
```json
{
  "next_topic": "...",
  "reason": "...",
  "encouragement": "...",
  "mastery_summary": { "topic": 0.0-1.0 },
  "requires_teacher_approval": true/false
}
```

**Mastery thresholds:**
- ≥ 0.8 across 3+ attempts = mastered (unlock next topic)
- 0.4-0.79 = progressing (more practice)
- < 0.4 = needs foundation work

**Human-in-the-loop rule:**
- Grades 1-6: all curriculum changes require teacher approval
- Grades 7-12: async notification only (non-blocking)

**Quality principles:**
- Never skip prerequisites
- Always explain WHY this is the next step
- Encouragement must feel personal, not generic
