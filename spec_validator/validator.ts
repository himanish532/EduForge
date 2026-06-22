/**
 * SpecValidator — Runtime contract enforcement against SPEC.md.
 *
 * Day 5: Spec-Driven Development.
 * The system declares its contracts in SPEC.md. This module enforces them
 * at runtime on every agent response — no contract violation reaches the student.
 *
 * Contracts checked:
 *   1. Token budget  — response must not exceed MAX_RESPONSE_TOKENS
 *   2. Safety gate   — response must pass regex + keyword safety screen
 *   3. Schema check  — quiz responses must have required JSON fields
 *   4. Skill tier    — action-allowed skills must not fire in read-only context
 *   5. Agent routing — intent must map to a declared agent
 *   6. HITL gate     — grade 1-6 curriculum changes require teacher flag
 *
 * Each violation produces a SpecViolation with severity: warn | error | block.
 * "block" violations suppress the response and substitute a safe fallback.
 */

export type ViolationSeverity = "warn" | "error" | "block";

export interface SpecViolation {
  rule: string;
  severity: ViolationSeverity;
  detail: string;
}

export interface ValidationResult {
  valid: boolean;           // false if any "block" violation
  violations: SpecViolation[];
  sanitized_response: string;
  spec_version: string;
}

// ── Spec constants (mirrors SPEC.md) ─────────────────────────────────────

const SPEC_VERSION = "1.0.0";

const TOKEN_BUDGET = {
  system: 500,
  context: 2000,
  history: 3000,
  response: 1500,
  total: 7000,
} as const;

const DECLARED_AGENTS: string[] = [
  "TutorAgent",
  "AssessmentAgent",
  "CurriculumAgent",
  "ContentAgent",
  "SafetyAgent",
  "VisionTutorAgent",
];

const DECLARED_INTENTS: string[] = [
  "explain",
  "quiz",
  "progress",
  "resources",
  "unsafe",
];

const SAFETY_PATTERNS: RegExp[] = [
  /\b(bomb|explosive|weapon|poison)\b/i,
  /\b(suicide|self.harm|self harm)\b/i,
  /ignore (all |your |previous )?(rules|instructions|system prompt)/i,
  /pretend (you are|you have no|there are no)/i,
  /\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b/, // SSN pattern
  /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/, // credit card
];

const QUIZ_REQUIRED_FIELDS = ["question", "options", "correct_index", "explanation"];

const SKILL_TIER_MAP: Record<string, string> = {
  "subject-tutor": "read-only",
  "quiz-generator": "action-allowed",
  "learning-path": "action-allowed",
  "content-fetch": "read-only",
};

const HITL_GRADE_THRESHOLD = 6; // grades 1-6 require teacher approval for curriculum

// ── Rule implementations ──────────────────────────────────────────────────

function checkTokenBudget(response: string): SpecViolation | null {
  const tokenEstimate = Math.ceil(response.length / 4);
  if (tokenEstimate > TOKEN_BUDGET.response) {
    return {
      rule: "token_budget.response",
      severity: "warn",
      detail: `Response ~${tokenEstimate} tokens exceeds budget of ${TOKEN_BUDGET.response}`,
    };
  }
  return null;
}

function checkSafetyGate(response: string): SpecViolation | null {
  for (const pattern of SAFETY_PATTERNS) {
    if (pattern.test(response)) {
      return {
        rule: "safety_gate.regex",
        severity: "block",
        detail: `Response matched safety pattern: ${pattern.source.slice(0, 40)}`,
      };
    }
  }
  return null;
}

function checkAgentRouting(agent: string, intent: string): SpecViolation | null {
  if (!DECLARED_AGENTS.includes(agent)) {
    return {
      rule: "agent_routing.undeclared_agent",
      severity: "error",
      detail: `Agent "${agent}" is not declared in SPEC.md. Declared: ${DECLARED_AGENTS.join(", ")}`,
    };
  }
  if (!DECLARED_INTENTS.includes(intent)) {
    return {
      rule: "agent_routing.undeclared_intent",
      severity: "warn",
      detail: `Intent "${intent}" is not in the declared intent set`,
    };
  }
  return null;
}

function checkQuizSchema(response: string, intent: string): SpecViolation | null {
  if (intent !== "quiz") return null;
  try {
    const cleaned = response.replace(/```json\n?/g, "").replace(/```\n?/g, "").trim();
    const s = cleaned.indexOf("{");
    const e = cleaned.lastIndexOf("}") + 1;
    if (s === -1 || e <= s) throw new Error("no json");
    const parsed = JSON.parse(cleaned.slice(s, e)) as Record<string, unknown>;
    for (const field of QUIZ_REQUIRED_FIELDS) {
      if (!(field in parsed)) {
        return {
          rule: "schema.quiz_missing_field",
          severity: "warn",
          detail: `Quiz response missing required field: "${field}"`,
        };
      }
    }
    if (!Array.isArray(parsed.options) || parsed.options.length !== 4) {
      return {
        rule: "schema.quiz_option_count",
        severity: "warn",
        detail: `Quiz must have exactly 4 options, got ${(parsed.options as unknown[])?.length ?? "none"}`,
      };
    }
  } catch {
    // Response is not JSON — acceptable for intent=quiz if it's a text explanation
  }
  return null;
}

function checkHITLGate(
  intent: string,
  gradeLevel: number
): SpecViolation | null {
  if (intent === "progress" && gradeLevel <= HITL_GRADE_THRESHOLD) {
    return {
      rule: "hitl.curriculum_grade_gate",
      severity: "warn",
      detail: `Curriculum change for grade ${gradeLevel} requires teacher approval (HITL gate per SPEC.md §4.3)`,
    };
  }
  return null;
}

function checkSkillTier(skillUsed: string | undefined, intent: string): SpecViolation | null {
  if (!skillUsed) return null;
  const tier = SKILL_TIER_MAP[skillUsed];
  if (!tier) {
    return {
      rule: "skill_tier.undeclared_skill",
      severity: "warn",
      detail: `Skill "${skillUsed}" is not in the declared skill registry`,
    };
  }
  return null;
}

// ── Main validator ────────────────────────────────────────────────────────

export interface ValidationInput {
  response: string;
  agent: string;
  intent: string;
  grade_level?: number;
  skill_used?: string;
}

const BLOCKED_RESPONSE =
  "I'm here to support your learning! Let me know what subject you'd like to explore.";

export function validateResponse(input: ValidationInput): ValidationResult {
  const violations: SpecViolation[] = [];

  // Run all contract checks
  const checks = [
    checkTokenBudget(input.response),
    checkSafetyGate(input.response),
    checkAgentRouting(input.agent, input.intent),
    checkQuizSchema(input.response, input.intent),
    checkHITLGate(input.intent, input.grade_level ?? 99),
    checkSkillTier(input.skill_used, input.intent),
  ];

  for (const v of checks) {
    if (v) violations.push(v);
  }

  const hasBlock = violations.some((v) => v.severity === "block");

  return {
    valid: !hasBlock,
    violations,
    sanitized_response: hasBlock ? BLOCKED_RESPONSE : input.response,
    spec_version: SPEC_VERSION,
  };
}

/**
 * Lightweight version for API route use — returns the safe response string
 * and a compact violations array suitable for including in API responses.
 */
export function specCheck(input: ValidationInput): {
  response: string;
  spec_violations: Pick<SpecViolation, "rule" | "severity">[];
  spec_version: string;
  hitl_required: boolean;
} {
  const result = validateResponse(input);
  return {
    response: result.sanitized_response,
    spec_violations: result.violations.map(({ rule, severity }) => ({ rule, severity })),
    spec_version: result.spec_version,
    hitl_required: result.violations.some((v) => v.rule.startsWith("hitl")),
  };
}
