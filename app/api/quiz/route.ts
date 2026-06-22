import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const GEMINI_API_KEY = process.env.GEMINI_API_KEY || "";

const QUIZ_SYSTEM_PROMPT = `You are an educational assessment specialist. Generate a single multiple-choice question.

Rules:
1. Exactly 4 options labeled A, B, C, D — only ONE is correct.
2. Match difficulty to mastery level.
3. Explanation must teach, not just confirm the answer.
4. Language appropriate for grade level.

Respond ONLY with valid JSON (no markdown, no extra text):
{
  "question": "...",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "correct_index": 0,
  "explanation": "...",
  "topic": "...",
  "difficulty": "beginner|intermediate|advanced"
}`;

function getDifficulty(mastery: number): string {
  if (mastery < 0.4) return "beginner";
  if (mastery < 0.75) return "intermediate";
  return "advanced";
}

function extractJSON(text: string): string {
  const fenceMatch = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (fenceMatch) return fenceMatch[1].trim();
  const objStart = text.indexOf("{");
  const objEnd = text.lastIndexOf("}");
  if (objStart !== -1 && objEnd > objStart) return text.slice(objStart, objEnd + 1);
  return text.trim();
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { topic, subject, grade_level, mastery } = body;

    if (!GEMINI_API_KEY) {
      return NextResponse.json({ error: "GEMINI_API_KEY not configured" }, { status: 500 });
    }

    const gradeLevel = parseInt(grade_level, 10) || 8;
    const masteryScore = parseFloat(mastery) || 0.0;
    const difficulty = getDifficulty(masteryScore);
    const quizTopic = topic || subject || "general";

    const prompt = `${QUIZ_SYSTEM_PROMPT}

Student: Grade ${gradeLevel} | Subject: ${subject} | Topic: ${quizTopic}
Mastery: ${(masteryScore * 100).toFixed(0)}% | Target difficulty: ${difficulty}

Generate the question now.`;

    const geminiRes = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: { maxOutputTokens: 600, temperature: 0.5 },
        }),
      }
    );

    if (!geminiRes.ok) {
      const err = await geminiRes.json();
      return NextResponse.json({ error: "Gemini API error", detail: err.error?.message }, { status: 502 });
    }

    const geminiData = await geminiRes.json();
    const rawText = geminiData.candidates?.[0]?.content?.parts?.[0]?.text ?? "";

    let quiz: Record<string, unknown>;
    try {
      quiz = JSON.parse(extractJSON(rawText));
    } catch {
      // Fallback quiz if parsing fails
      quiz = {
        question: `What is an important concept related to ${quizTopic}?`,
        options: ["A. Concept A", "B. Concept B", "C. Concept C", "D. Concept D"],
        correct_index: 0,
        explanation: "Please try again — I had trouble generating a quiz for this topic.",
        topic: quizTopic,
        difficulty,
      };
    }

    return NextResponse.json({ quiz, difficulty, topic: quizTopic });
  } catch (err) {
    console.error("[/api/quiz] error:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}

export async function PUT(req: NextRequest) {
  // Score a submitted answer — A2UI scoring endpoint
  try {
    const body = await req.json();
    const { quiz, selected_index, student_id, topic } = body;

    if (!quiz || selected_index === undefined) {
      return NextResponse.json({ error: "quiz and selected_index are required" }, { status: 400 });
    }

    const correct_index = quiz.correct_index ?? 0;
    const is_correct = selected_index === correct_index;
    const score = is_correct ? 1.0 : 0.0;

    // Weighted mastery update: new result counts 30%
    const prior_mastery = parseFloat(body.prior_mastery ?? "0") || 0.0;
    const new_mastery = prior_mastery * 0.7 + score * 0.3;

    const feedback = is_correct
      ? `✅ **Correct!** ${quiz.explanation}`
      : `❌ **Not quite.** The correct answer was **${quiz.options[correct_index]}**.\n\n${quiz.explanation}`;

    return NextResponse.json({
      correct: is_correct,
      score,
      feedback,
      new_mastery,
      topic: topic || quiz.topic,
      // A2A simulation: note that this would be sent as an A2A message to CurriculumAgent
      a2a_message: {
        type: "assessment_result",
        sender: "AssessmentAgent",
        recipient: "CurriculumAgent",
        payload: { student_id, topic: topic || quiz.topic, score, is_correct, new_mastery },
      },
    });
  } catch (err) {
    console.error("[/api/quiz PUT] error:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
