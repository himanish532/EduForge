import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const GEMINI_API_KEY = process.env.GEMINI_API_KEY || "";

// Subject-aware system prompts — the orchestrator harness in the Next.js layer
function buildSystemPrompt(subject: string, gradeLevel: number, sessionSummary: string): string {
  return `You are a patient, encouraging AI tutor for a Grade ${gradeLevel} student studying ${subject}.

Teaching philosophy: Guide students to discover answers themselves through Socratic questioning.
Never give direct answers — ask questions that lead the student toward understanding.

Rules:
1. Always acknowledge what the student said first.
2. Use simple, age-appropriate analogies for a Grade ${gradeLevel} student.
3. After every explanation, ask ONE follow-up question.
4. Keep responses under 250 words.
5. Use warm, encouraging language. Celebrate curiosity.
6. Format with short paragraphs — no bullet points in explanations.

${sessionSummary ? `Session context: ${sessionSummary}` : ""}

You are one agent in a multi-agent system called EduForge. You are the TutorAgent.`;
}

function classifyIntent(message: string): string {
  const m = message.toLowerCase();
  if (/quiz|test me|practice|question me/.test(m)) return "quiz";
  if (/progress|next topic|curriculum|learning path|what should i/.test(m)) return "progress";
  if (/find|resource|video|show me|example/.test(m)) return "resources";
  return "explain";
}

function detectAgent(intent: string): string {
  const map: Record<string, string> = {
    explain: "TutorAgent",
    quiz: "AssessmentAgent",
    progress: "CurriculumAgent",
    resources: "ContentAgent",
  };
  return map[intent] || "TutorAgent";
}

// Agent-specific prompt adjustments
function agentPromptSuffix(intent: string, subject: string, topic: string, gradeLevel: number): string {
  if (intent === "quiz") {
    return `\n\nGenerate a single multiple-choice quiz question about "${topic || subject}". Format it clearly with A/B/C/D options. After the options, add a brief hint on how to think about it (don't reveal the answer).`;
  }
  if (intent === "progress") {
    return `\n\nThe student is asking about their learning progress or what to study next. Provide an encouraging response about their ${subject} learning journey and suggest a logical next step.`;
  }
  if (intent === "resources") {
    return `\n\nThe student wants learning resources. Suggest 2-3 specific, free resources (Khan Academy, Wikipedia, YouTube) for "${topic || subject}" at Grade ${gradeLevel} level. Be specific about what each resource covers.`;
  }
  return "";
}

// Simple safety check — runs on every response before returning to client
function safetyCheck(text: string): { safe: boolean; response: string } {
  const blockedPatterns = [
    /\b(bomb|weapon|explosive|poison|suicide|self.harm)\b/i,
    /ignore (your|all|previous) (rules|instructions|system prompt)/i,
    /pretend you (are|have no)/i,
  ];

  for (const pattern of blockedPatterns) {
    if (pattern.test(text)) {
      return {
        safe: false,
        response:
          "I'm here to help you learn! Let me know what subject you'd like to explore today.",
      };
    }
  }
  return { safe: true, response: text };
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { message, subject, grade_level, session_summary, recent_history, current_topic } = body;

    if (!message?.trim()) {
      return NextResponse.json({ error: "message is required" }, { status: 400 });
    }

    if (!GEMINI_API_KEY) {
      return NextResponse.json(
        { error: "GEMINI_API_KEY is not configured on the server." },
        { status: 500 }
      );
    }

    const gradeLevel = parseInt(grade_level, 10) || 8;
    const intent = classifyIntent(message);
    const agentName = detectAgent(intent);
    const topic = current_topic || subject;

    // Build prompt with context engineering harness
    const systemPrompt =
      buildSystemPrompt(subject, gradeLevel, session_summary || "") +
      agentPromptSuffix(intent, subject, topic, gradeLevel);

    // Construct conversation history (sliding window — last 5 exchanges)
    const history = (recent_history || []).slice(-10);
    const historyText =
      history.length > 0
        ? "\n\nPrevious conversation:\n" +
          history.map((m: { role: string; content: string }) => `${m.role.toUpperCase()}: ${m.content}`).join("\n")
        : "";

    const fullPrompt = `${systemPrompt}${historyText}\n\nSTUDENT: ${message}\n\nTUTOR:`;

    // Call Gemini API directly via REST
    const geminiRes = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ parts: [{ text: fullPrompt }] }],
          generationConfig: {
            maxOutputTokens: 800,
            temperature: 0.7,
          },
        }),
      }
    );

    if (!geminiRes.ok) {
      const err = await geminiRes.json();
      return NextResponse.json(
        { error: "Gemini API error", detail: err.error?.message },
        { status: 502 }
      );
    }

    const geminiData = await geminiRes.json();
    const rawResponse =
      geminiData.candidates?.[0]?.content?.parts?.[0]?.text?.trim() ||
      "I had trouble generating a response. Please try again.";

    // Safety check every response
    const { safe, response } = safetyCheck(rawResponse);

    // Update context for client to persist
    const updatedHistory = [
      ...history,
      { role: "user", content: message },
      { role: "assistant", content: response },
    ].slice(-10);

    return NextResponse.json({
      response,
      agent: agentName,
      intent,
      safe,
      updated_context: {
        recent_history: updatedHistory,
        current_topic: extractTopic(message, topic),
        session_summary: session_summary,
        mastery_summary: body.mastery_summary || {},
      },
      audit: {
        routing_confidence: 0.9,
        topic,
        agent: agentName,
      },
    });
  } catch (err) {
    console.error("[/api/chat] error:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}

function extractTopic(message: string, fallback: string): string {
  // Simple topic extraction — looks for "about X" patterns
  const match = message.match(/(?:about|explain|understand|learn)\s+([a-zA-Z\s]{3,40})/i);
  return match ? match[1].trim() : fallback;
}
