/**
 * /api/multimodal — Vision-based question answering.
 *
 * Day 4: Multimodal inputs via Gemini 2.0 Flash vision.
 * Accepts a base64-encoded image + student question.
 * Gemini analyzes the image (math problem, diagram, science figure, etc.)
 * and provides a Socratic tutoring response.
 *
 * Zero cost overhead: uses the same Gemini 2.0 Flash model already in use
 * — no separate vision API, no extra billing tier.
 *
 * POST body:
 *   {
 *     image_base64: string,    // base64-encoded image (no data: prefix)
 *     mime_type: string,       // "image/jpeg" | "image/png" | "image/webp"
 *     question: string,        // student's question about the image
 *     subject: string,
 *     grade_level: number
 *   }
 *
 * Response:
 *   {
 *     response: string,
 *     detected_topic: string,
 *     subject_detected: string,
 *     agent: "VisionTutorAgent",
 *     safe: boolean
 *   }
 */

import { NextRequest, NextResponse } from "next/server";

const GEMINI_API_KEY = process.env.GEMINI_API_KEY ?? "";

interface MultimodalRequest {
  image_base64: string;
  mime_type?: string;
  question: string;
  subject: string;
  grade_level: number;
}

const SAFETY_PATTERNS = [
  /\b(bomb|weapon|explosive|poison|suicide|self.harm)\b/i,
  /ignore (your|all|previous) (rules|instructions|system prompt)/i,
  /pretend you (are|have no)/i,
];

function safetyCheck(text: string): boolean {
  return !SAFETY_PATTERNS.some((p) => p.test(text));
}

function buildVisionSystemPrompt(subject: string, gradeLevel: number): string {
  const grade =
    gradeLevel <= 5 ? "elementary" : gradeLevel <= 8 ? "middle school" : "high school";

  return `You are an expert ${subject} tutor for ${grade} students (grade ${gradeLevel}).
A student has shared an image with you — it may be a math problem, a science diagram,
a history map, a coding snippet, or any educational image.

Your task:
1. Briefly describe what you see in the image (1-2 sentences).
2. Identify the topic or concept shown (e.g. "quadratic equations", "cell diagram").
3. Guide the student toward understanding using Socratic questioning — DO NOT just solve it for them.
4. End with exactly ONE follow-up question to check their understanding.

Keep your response under 300 words. Use warm, encouraging language appropriate for grade ${gradeLevel}.

Return your response in this JSON format:
{
  "detected_topic": "brief topic name",
  "subject_detected": "${subject}",
  "response": "your full tutoring response here"
}`;
}

function extractJSON(text: string): Record<string, string> {
  const cleaned = text.replace(/```json\n?/g, "").replace(/```\n?/g, "").trim();
  try {
    return JSON.parse(cleaned);
  } catch {
    const s = cleaned.indexOf("{");
    const e = cleaned.lastIndexOf("}") + 1;
    if (s !== -1 && e > s) return JSON.parse(cleaned.slice(s, e));
    throw new Error("No JSON in response");
  }
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  if (!GEMINI_API_KEY) {
    return NextResponse.json(
      { error: "GEMINI_API_KEY not configured" },
      { status: 500 }
    );
  }

  let body: MultimodalRequest;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const {
    image_base64,
    mime_type = "image/jpeg",
    question,
    subject = "general",
    grade_level = 8,
  } = body;

  if (!image_base64) {
    return NextResponse.json({ error: "image_base64 is required" }, { status: 400 });
  }
  if (!question?.trim()) {
    return NextResponse.json({ error: "question is required" }, { status: 400 });
  }

  const systemPrompt = buildVisionSystemPrompt(subject, grade_level);

  // Gemini multimodal request: text + inlineData image part
  const geminiBody = {
    contents: [
      {
        parts: [
          { text: `${systemPrompt}\n\nSTUDENT QUESTION: ${question}` },
          {
            inlineData: {
              mimeType: mime_type,
              data: image_base64,
            },
          },
        ],
      },
    ],
    generationConfig: {
      maxOutputTokens: 800,
      temperature: 0.7,
    },
  };

  const geminiRes = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${GEMINI_API_KEY}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(geminiBody),
    }
  );

  if (!geminiRes.ok) {
    const err = await geminiRes.json();
    return NextResponse.json(
      { error: "Gemini vision API error", detail: err.error?.message },
      { status: 502 }
    );
  }

  const geminiData = await geminiRes.json();
  const rawText =
    geminiData.candidates?.[0]?.content?.parts?.[0]?.text?.trim() ?? "";

  if (!rawText) {
    return NextResponse.json(
      { error: "Empty response from vision model" },
      { status: 502 }
    );
  }

  // Parse structured JSON response from the model
  let parsed: Record<string, string>;
  try {
    parsed = extractJSON(rawText);
  } catch {
    // Fallback: treat raw text as the response
    parsed = {
      detected_topic: subject,
      subject_detected: subject,
      response: rawText,
    };
  }

  const response = parsed.response ?? rawText;
  const safe = safetyCheck(response);
  const safeResponse = safe
    ? response
    : "I can only help with educational content. Let me know what subject you'd like to explore!";

  return NextResponse.json({
    response: safeResponse,
    detected_topic: parsed.detected_topic ?? subject,
    subject_detected: parsed.subject_detected ?? subject,
    agent: "VisionTutorAgent",
    safe,
    metadata: {
      model: "gemini-2.5-flash",
      multimodal: true,
      grade_level,
      subject,
    },
  });
}
