# Skill: content-fetch

**Trigger phrases:** "find", "show me", "video about", "resources for", "examples of", "reference"

**Description:**
Curates 2-3 supplementary learning resources for the current topic, matched to grade level.
READ-ONLY access — this agent cannot write to any store.

**Input:**
- `context.current_topic` — topic to find resources for
- `context.grade_level` — difficulty filter
- `context.subject` — subject area

**Output format:**
```json
{
  "resources": [
    {
      "title": "...",
      "description": "1 sentence",
      "type": "video|article|exercise|interactive",
      "difficulty": "beginner|intermediate|advanced",
      "source": "Khan Academy|Wikipedia|YouTube|etc"
    }
  ],
  "summary": "..."
}
```

**Constraints:**
- ONLY free, openly accessible content
- At least 1 video resource if available
- No login-required content
- READ-ONLY: cannot write to Progress DB or any external service

**Quality principles:**
- Resources must directly relate to the topic
- Difficulty must match grade level
- Prefer well-known, trusted sources
- 2-3 resources is the sweet spot (not overwhelming)
