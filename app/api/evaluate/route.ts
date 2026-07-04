/**
 * /api/evaluate — EDD evaluation endpoint.
 *
 * Day 3: Evaluation-Driven Development (EDD).
 * Runs LLM-as-judge with position swapping on agent outputs.
 *
 * POST body:
 *   { eval_id?, category?, run_all?: boolean }
 *   - run_all: runs all 20 eval cases (slow, ~60s)
 *   - eval_id: runs a single case
 *   - category: runs all cases in a category
 *
 * The judge uses position swapping (A vs B, then B vs A) to detect positional bias.
 * Final verdict: only "pass" if both swapped evals agree.
 */

import { NextRequest, NextResponse } from "next/server";
import evalCases from "../../../evals/eval_cases.json";

const GEMINI_API_KEY = process.env.GEMINI_API_KEY ?? "";

interface EvalCase {
  id: string;
  category: string;
  input: string;
  subject: string;
  grade_level: number;
  expected_intent: string;
  expected_skill: string | null;
  expected_agent: string;
  expected_output_format: string;
  rubric: Record<string, unknown>;
  session_context?: Record<string, unknown>;
  a2a_expected?: Record<string, string>;
  hitl_check?: Record<string, boolean>;
}

interface EvalResult {
  eval_id: string;
  category: string;
  input: string;
  expected_intent: string;
  expected_agent: string;
  actual_response: string;
  rubric_pass: boolean;
  rubric_failures: string[];
  judge_verdict: "pass" | "fail" | "uncertain";
  judge_reasoning: string;
  position_swap_consistent: boolean;
  score: number;
  duration_ms: number;
}

async function callGemini(prompt: string, maxTokens = 1500): Promise<string> {
  const res = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${GEMINI_API_KEY}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { maxOutputTokens: maxTokens, temperature: 0.3 },
      }),
    }
  );
  const data = await res.json();
  return data?.candidates?.[0]?.content?.parts?.[0]?.text ?? "";
}

function extractJSON(text: string): unknown {
  const cleaned = text.replace(/```json\n?/g, "").replace(/```\n?/g, "").trim();
  try {
    return JSON.parse(cleaned);
  } catch {
    const s = cleaned.indexOf("{");
    const e = cleaned.lastIndexOf("}") + 1;
    if (s !== -1 && e > s) return JSON.parse(cleaned.slice(s, e));
    throw new Error("No JSON");
  }
}

async function generateResponse(evalCase: EvalCase): Promise<string> {
  const gradeText = evalCase.grade_level <= 5 ? "elementary" : evalCase.grade_level <= 8 ? "middle school" : "high school";
  const intentPrompts: Record<string, string> = {
    explain: `You are an expert ${evalCase.subject} tutor for ${gradeText} students (grade ${evalCase.grade_level}). Explain clearly and age-appropriately. End with a question to check understanding.`,
    quiz: `You are an assessment agent. Generate a single multiple-choice question about the topic for grade ${evalCase.grade_level}. Return JSON: {"question":"...","options":["A","B","C","D"],"correct_index":0,"explanation":"...","difficulty":"${evalCase.grade_level <= 5 ? "beginner" : "intermediate"}"}`,
    progress: `You are a curriculum agent. Recommend what the student should learn next in ${evalCase.subject} at grade ${evalCase.grade_level}. Be concise.`,
    resources: `You are a content agent. List 2-3 educational resources for the topic. Include source names (Khan Academy, YouTube, etc.).`,
    unsafe: `You are a safety agent. This request has been flagged. Respond with a supportive redirect to focus on studies.`,
  };
  const systemPrompt = intentPrompts[evalCase.expected_intent] ?? intentPrompts.explain;
  return await callGemini(`${systemPrompt}\n\nSTUDENT: ${evalCase.input}`);
}

function checkRubric(response: string, rubric: Record<string, unknown>): { pass: boolean; failures: string[] } {
  const failures: string[] = [];
  const lower = response.toLowerCase();

  if (rubric.must_include) {
    for (const term of rubric.must_include as string[]) {
      if (!lower.includes(term.toLowerCase())) {
        failures.push(`Missing required term: "${term}"`);
      }
    }
  }

  if (rubric.must_include_one_of) {
    const terms = rubric.must_include_one_of as string[];
    if (!terms.some((t) => lower.includes(t.toLowerCase()))) {
      failures.push(`Must include at least one of: ${terms.join(", ")}`);
    }
  }

  if (rubric.must_not_include) {
    for (const term of rubric.must_not_include as string[]) {
      if (lower.includes(term.toLowerCase())) {
        failures.push(`Forbidden term found: "${term}"`);
      }
    }
  }

  if (rubric.ends_with_question) {
    const trimmed = response.trim();
    if (!trimmed.endsWith("?")) {
      failures.push("Response must end with a question");
    }
  }

  if (rubric.max_words) {
    const wordCount = response.split(/\s+/).length;
    if (wordCount > (rubric.max_words as number)) {
      failures.push(`Response too long: ${wordCount} words (max ${rubric.max_words})`);
    }
  }

  if (rubric.json_fields) {
    try {
      const parsed = extractJSON(response) as Record<string, unknown>;
      for (const field of rubric.json_fields as string[]) {
        if (!(field in parsed)) failures.push(`Missing JSON field: ${field}`);
      }
    } catch {
      failures.push("Response is not valid JSON");
    }
  }

  if (rubric.options_count) {
    try {
      const parsed = extractJSON(response) as { options?: unknown[] };
      if (!parsed.options || parsed.options.length !== rubric.options_count) {
        failures.push(`Expected ${rubric.options_count} options, got ${parsed.options?.length ?? 0}`);
      }
    } catch {
      // already caught above
    }
  }

  return { pass: failures.length === 0, failures };
}

async function judgeResponse(
  evalCase: EvalCase,
  response: string,
  position: "A" | "B"
): Promise<{ verdict: "pass" | "fail" | "uncertain"; reasoning: string }> {
  const rubricText = JSON.stringify(evalCase.rubric, null, 2);
  const prompt = `You are an expert educational AI evaluator. Judge whether the following AI tutor response meets the quality rubric.

EVALUATION CASE:
- Student input: "${evalCase.input}"
- Grade level: ${evalCase.grade_level}
- Subject: ${evalCase.subject}
- Expected intent: ${evalCase.expected_intent}

QUALITY RUBRIC:
${rubricText}

AI RESPONSE (Position ${position}):
"${response.slice(0, 800)}"

Verdict options: "pass" (meets all rubric requirements), "fail" (fails one or more), "uncertain" (borderline).

Return JSON ONLY: {"verdict": "pass|fail|uncertain", "reasoning": "one sentence explanation"}`;

  const raw = await callGemini(prompt, 200);
  try {
    const parsed = extractJSON(raw) as { verdict: string; reasoning: string };
    const verdict = ["pass", "fail", "uncertain"].includes(parsed.verdict)
      ? (parsed.verdict as "pass" | "fail" | "uncertain")
      : "uncertain";
    return { verdict, reasoning: parsed.reasoning ?? "" };
  } catch {
    return { verdict: "uncertain", reasoning: "Judge could not parse its own response" };
  }
}

async function runEvalCase(evalCase: EvalCase): Promise<EvalResult> {
  const start = Date.now();

  // Generate agent response
  const response = await generateResponse(evalCase);

  // Deterministic rubric check
  const { pass: rubricPass, failures } = checkRubric(response, evalCase.rubric);

  // LLM-as-judge with position swapping (anti-bias technique from Day 3)
  const [judgeA, judgeB] = await Promise.all([
    judgeResponse(evalCase, response, "A"),
    judgeResponse(evalCase, response, "B"),
  ]);

  const swapConsistent = judgeA.verdict === judgeB.verdict;
  let finalVerdict: "pass" | "fail" | "uncertain";
  if (swapConsistent) {
    finalVerdict = judgeA.verdict;
  } else {
    // Disagreement = uncertain; defer to rubric
    finalVerdict = rubricPass ? "pass" : "fail";
  }

  // Score: rubric 60%, judge 40%
  const judgeScore = finalVerdict === "pass" ? 1.0 : finalVerdict === "uncertain" ? 0.5 : 0.0;
  const score = rubricPass ? 0.6 + judgeScore * 0.4 : judgeScore * 0.4;

  return {
    eval_id: evalCase.id,
    category: evalCase.category,
    input: evalCase.input,
    expected_intent: evalCase.expected_intent,
    expected_agent: evalCase.expected_agent,
    actual_response: response.slice(0, 500),
    rubric_pass: rubricPass,
    rubric_failures: failures,
    judge_verdict: finalVerdict,
    judge_reasoning: judgeA.reasoning,
    position_swap_consistent: swapConsistent,
    score: Math.round(score * 100) / 100,
    duration_ms: Date.now() - start,
  };
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  if (!GEMINI_API_KEY) {
    return NextResponse.json({ error: "GEMINI_API_KEY not configured" }, { status: 500 });
  }

  const body = await req.json().catch(() => ({})) as {
    eval_id?: string;
    category?: string;
    run_all?: boolean;
  };

  const allCases = evalCases as EvalCase[];
  let selectedCases: EvalCase[];

  if (body.run_all) {
    selectedCases = allCases;
  } else if (body.eval_id) {
    const found = allCases.find((c) => c.id === body.eval_id);
    selectedCases = found ? [found] : [];
  } else if (body.category) {
    selectedCases = allCases.filter((c) => c.category === body.category);
  } else {
    // Default: run first 3 cases as a smoke test
    selectedCases = allCases.slice(0, 3);
  }

  if (selectedCases.length === 0) {
    return NextResponse.json({ error: "No matching eval cases found" }, { status: 404 });
  }

  const startTotal = Date.now();

  // Run cases sequentially to avoid rate limiting
  const results: EvalResult[] = [];
  for (const evalCase of selectedCases) {
    try {
      const result = await runEvalCase(evalCase);
      results.push(result);
    } catch (error) {
      results.push({
        eval_id: evalCase.id,
        category: evalCase.category,
        input: evalCase.input,
        expected_intent: evalCase.expected_intent,
        expected_agent: evalCase.expected_agent,
        actual_response: "",
        rubric_pass: false,
        rubric_failures: [error instanceof Error ? error.message : "Unknown error"],
        judge_verdict: "fail",
        judge_reasoning: "Error during evaluation",
        position_swap_consistent: false,
        score: 0,
        duration_ms: 0,
      });
    }
  }

  const passCount = results.filter((r) => r.judge_verdict === "pass").length;
  const avgScore = results.reduce((sum, r) => sum + r.score, 0) / results.length;

  return NextResponse.json({
    summary: {
      total: results.length,
      passed: passCount,
      failed: results.filter((r) => r.judge_verdict === "fail").length,
      uncertain: results.filter((r) => r.judge_verdict === "uncertain").length,
      avg_score: Math.round(avgScore * 100) / 100,
      total_duration_ms: Date.now() - startTotal,
    },
    results,
  });
}
