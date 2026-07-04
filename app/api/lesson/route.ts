/**
 * /api/lesson — DAG lesson workflow endpoint.
 *
 * Day 3: Triggers the Tutor → Assessment → Curriculum DAG.
 * POST body: { topic, student_id, subject, grade_level, mastery_summary }
 * Response: LessonDAGResult with explanation, quiz_data, next_topic
 */

import { NextRequest, NextResponse } from "next/server";
import { specCheck } from "../../../spec_validator/validator";

const GEMINI_API_KEY = process.env.GEMINI_API_KEY ?? "";

interface LessonRequest {
  topic: string;
  student_id: string;
  subject: string;
  grade_level: number;
  mastery_summary?: Record<string, number>;
}

interface QuizData {
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
  difficulty: string;
}

interface LessonResponse {
  correlation_id: string;
  topic: string;
  explanation: string;
  quiz_data: QuizData | null;
  next_topic: string | null;
  requires_teacher_approval: boolean;
  nodes: Array<{
    node_type: string;
    skill_used: string;
    token_estimate: number;
    duration_ms: number;
    success: boolean;
  }>;
  total_tokens: number;
  total_duration_ms: number;
  success: boolean;
}

async function callGemini(prompt: string): Promise<string> {
  const res = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${GEMINI_API_KEY}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { maxOutputTokens: 1500, temperature: 0.7 },
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
    const start = cleaned.indexOf("{");
    const end = cleaned.lastIndexOf("}") + 1;
    if (start !== -1 && end > start) return JSON.parse(cleaned.slice(start, end));
    throw new Error("No JSON found");
  }
}

async function runTutorNode(
  topic: string,
  subject: string,
  gradeLevel: number
): Promise<{ response: string; duration_ms: number }> {
  const start = Date.now();
  const prompt = `You are an expert ${subject} tutor for grade ${gradeLevel} students.
Explain "${topic}" clearly and age-appropriately. End with a question to check understanding.
Keep it under 300 words. Do NOT give the answer away — guide them to discover it.`;
  const response = await callGemini(prompt);
  return { response, duration_ms: Date.now() - start };
}

async function runAssessmentNode(
  topic: string,
  subject: string,
  gradeLevel: number
): Promise<{ response: string; quiz_data: QuizData | null; duration_ms: number }> {
  const start = Date.now();
  const difficulty = gradeLevel <= 5 ? "beginner" : gradeLevel <= 8 ? "intermediate" : "advanced";
  const prompt = `Generate a single multiple-choice quiz question about "${topic}" for grade ${gradeLevel} ${subject}.
Difficulty: ${difficulty}.

Return ONLY valid JSON in this exact format:
{
  "question": "...",
  "options": ["A", "B", "C", "D"],
  "correct_index": 0,
  "explanation": "...",
  "difficulty": "${difficulty}"
}`;
  const raw = await callGemini(prompt);
  let quiz_data: QuizData | null = null;
  try {
    quiz_data = extractJSON(raw) as QuizData;
  } catch {
    // Fallback quiz
    quiz_data = {
      question: `What is the most important concept in ${topic}?`,
      options: ["Understanding the basics", "Memorizing formulas", "Skipping ahead", "Asking a friend"],
      correct_index: 0,
      explanation: `Understanding the fundamentals of ${topic} is the foundation for all further learning.`,
      difficulty,
    };
  }
  return { response: raw, quiz_data, duration_ms: Date.now() - start };
}

async function runCurriculumNode(
  topic: string,
  subject: string,
  gradeLevel: number,
  masterySummary: Record<string, number>
): Promise<{ response: string; next_topic: string; requires_teacher_approval: boolean; duration_ms: number }> {
  const start = Date.now();
  const masteryText = Object.entries(masterySummary)
    .map(([t, s]) => `${t}: ${Math.round(s * 100)}%`)
    .join(", ") || "no prior mastery";
  const prompt = `You are a curriculum planner for grade ${gradeLevel} ${subject}.
The student just studied "${topic}". Current mastery: ${masteryText}.
Recommend exactly ONE next topic to study. Keep it grade-appropriate.
Return ONLY valid JSON: {"next_topic": "...", "reason": "..."}`;
  const raw = await callGemini(prompt);
  let next_topic = topic;
  try {
    const parsed = extractJSON(raw) as { next_topic: string };
    next_topic = parsed.next_topic ?? topic;
  } catch {
    next_topic = topic;
  }
  const requires_teacher_approval = gradeLevel <= 6;
  return { response: raw, next_topic, requires_teacher_approval, duration_ms: Date.now() - start };
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  if (!GEMINI_API_KEY) {
    return NextResponse.json({ error: "GEMINI_API_KEY not configured" }, { status: 500 });
  }

  let body: LessonRequest;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const { topic, student_id, subject, grade_level, mastery_summary = {} } = body;
  if (!topic || !subject || !grade_level) {
    return NextResponse.json({ error: "topic, subject, grade_level are required" }, { status: 400 });
  }

  const correlationId = crypto.randomUUID();
  const totalStart = Date.now();
  const nodes: LessonResponse["nodes"] = [];

  try {
    // Node 1: Tutor
    const tutorResult = await runTutorNode(topic, subject, grade_level);
    nodes.push({
      node_type: "TutorNode",
      skill_used: "subject-tutor",
      token_estimate: Math.floor(tutorResult.response.length / 4),
      duration_ms: tutorResult.duration_ms,
      success: true,
    });

    // Node 2: Assessment
    const assessmentResult = await runAssessmentNode(topic, subject, grade_level);
    nodes.push({
      node_type: "AssessmentNode",
      skill_used: "quiz-generator",
      token_estimate: Math.floor(assessmentResult.response.length / 4),
      duration_ms: assessmentResult.duration_ms,
      success: true,
    });

    // Node 3: Curriculum
    const curriculumResult = await runCurriculumNode(topic, subject, grade_level, mastery_summary);
    nodes.push({
      node_type: "CurriculumNode",
      skill_used: "learning-path",
      token_estimate: Math.floor(curriculumResult.response.length / 4),
      duration_ms: curriculumResult.duration_ms,
      success: true,
    });

    // Day 5: spec-validate each node's output
    const tutorSpec = specCheck({ response: tutorResult.response, agent: "TutorAgent", intent: "explain", grade_level });
    const curriculumSpec = specCheck({ response: curriculumResult.response, agent: "CurriculumAgent", intent: "progress", grade_level });

    const result: LessonResponse = {
      correlation_id: correlationId,
      topic,
      explanation: tutorSpec.response,
      quiz_data: assessmentResult.quiz_data,
      next_topic: curriculumResult.next_topic,
      requires_teacher_approval: curriculumResult.requires_teacher_approval || curriculumSpec.hitl_required,
      nodes,
      total_tokens: nodes.reduce((sum, n) => sum + n.token_estimate, 0),
      total_duration_ms: Date.now() - totalStart,
      success: true,
    };

    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json(
      {
        correlation_id: correlationId,
        topic,
        success: false,
        error: error instanceof Error ? error.message : "DAG execution failed",
        nodes,
        total_tokens: 0,
        total_duration_ms: Date.now() - totalStart,
      },
      { status: 500 }
    );
  }
}
