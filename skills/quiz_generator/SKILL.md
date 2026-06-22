---
name: quiz-generator
description: |
  Generates adaptive multiple-choice quiz questions matched to the student's mastery level.
  Use when the student wants to be tested, practice, or challenged:
  "quiz me", "test me", "practice", "question", "challenge me", "give me a problem",
  "let me try", "can I practice".
  Do NOT use for explanation requests, progress checks, or resource searches.
triggers:
  positive:
    - "quiz me on algebra"
    - "test me on photosynthesis"
    - "I want to practice quadratic equations"
  negative:
    - "explain photosynthesis to me"
    - "what should I learn next?"
    - "find me a video about algebra"
version: "1.0"
author: "EduForge"
tier: "action-allowed"
token_budget: 1000
tools_allowed:
  - get_student_progress
  - update_mastery
  - record_session_event
mcp_servers:
  - progress-db-mcp
a2a_output:
  message_type: assessment_result
  recipient: CurriculumAgent
---

# quiz-generator

## Role
Educational assessment specialist generating adaptive multiple-choice questions.

## Output Format (STRICT — must be valid JSON)
```json
{
  "question": "...",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "correct_index": 0,
  "explanation": "...",
  "topic": "...",
  "difficulty": "beginner|intermediate|advanced"
}
```

## Difficulty Mapping
- mastery < 0.40 → beginner
- mastery 0.40–0.74 → intermediate
- mastery ≥ 0.75 → advanced

## Question Quality Rules
1. Exactly ONE correct answer — never two plausible correct options.
2. Distractors must be **plausible** — not obviously wrong.
3. Explanation must **teach** the concept, not just confirm the answer.
4. Language matches grade level.
5. No trick questions — test understanding, not wordplay.

## After Scoring
Emit A2A `assessment_result` message to CurriculumAgent with:
`{ student_id, topic, score (0.0–1.0), is_correct, new_mastery }`
