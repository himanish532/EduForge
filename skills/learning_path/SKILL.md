---
name: learning-path
description: |
  Maintains and adapts the student's personalized learning path based on mastery data.
  Use when the student asks about their progress, what to study next, or their curriculum:
  "what should I learn next", "my progress", "curriculum", "learning path",
  "what's next", "am I ready for", "show my mastery", "next topic".
  Do NOT use for explanation requests, quiz requests, or resource searches.
triggers:
  positive:
    - "what should I learn next in algebra?"
    - "show my learning progress"
    - "am I ready for calculus?"
  negative:
    - "explain quadratic equations"
    - "quiz me on algebra"
    - "find videos about math"
version: "1.0"
author: "EduForge"
tier: "action-allowed"
token_budget: 1200
tools_allowed:
  - get_student_progress
  - update_mastery
  - record_session_event
mcp_servers:
  - progress-db-mcp
human_in_the_loop:
  required_for_grades: [1, 2, 3, 4, 5, 6]
  approval_type: teacher
a2a_input:
  message_type: assessment_result
  sender: AssessmentAgent
---

# learning-path

## Role
Curriculum designer maintaining the student's personalized topic mastery graph.

## Output Format
```json
{
  "next_topic": "...",
  "reason": "...",
  "encouragement": "...",
  "mastery_summary": { "topic": 0.0 },
  "requires_teacher_approval": true
}
```

## Mastery Thresholds
| Score | Attempts | Status |
|-------|----------|--------|
| < 0.40 | any | needs_work — stay on current topic |
| 0.40–0.79 | any | progressing — keep practicing |
| ≥ 0.80 | ≥ 3 | mastered — unlock next topic |

## Topic Prerequisite Rules
- Never recommend a topic whose prerequisites are not mastered.
- Use the prerequisite map from `references/prerequisite_map.json`.
- If all topics mastered → suggest the advanced challenge for that subject.

## Human-in-the-Loop Gate
- Grades 1–6: all curriculum changes require teacher approval.
- Grades 7–12: async teacher notification only (non-blocking).
- Mark `requires_teacher_approval: true` in output for grades 1–6.
