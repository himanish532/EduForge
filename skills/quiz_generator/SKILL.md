# Skill: quiz-generator

**Trigger phrases:** "quiz me", "test me", "practice", "question", "challenge me"

**Description:**
Generates adaptive multiple-choice questions matched to the student's current mastery level.
Scores answers and sends results to CurriculumAgent via A2A message.

**Input:**
- `context.current_topic` — topic to quiz on
- `context.mastery_summary[topic]` — current mastery score (0.0-1.0)
- `context.grade_level` — determines language complexity

**Output format (strict JSON):**
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

**A2A output (after scoring):**
```json
{ "type": "assessment_result", "topic": "...", "score": 0.0-1.0, "student_id": "..." }
```

**Difficulty mapping:**
- mastery < 0.4 → beginner
- mastery 0.4-0.79 → intermediate  
- mastery ≥ 0.8 → advanced

**Quality principles:**
- One unambiguous correct answer
- Distractors must be plausible (not obviously wrong)
- Explanation must teach, not just confirm
- Language matches grade level

**Eval rubric (1-5):**
- 5: Relevant, appropriately difficult, clear, teaching explanation
- 4: Relevant and clear, explanation adequate
- 3: Relevant but too easy/hard for mastery level
- 2: Ambiguous question or trivial distractors
- 1: Incorrect or off-topic
