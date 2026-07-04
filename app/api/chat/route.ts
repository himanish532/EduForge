import { NextRequest, NextResponse } from "next/server";
import { knowledgeBase } from "../../../rag/knowledge_base";
import { specCheck } from "../../../spec_validator/validator";
import { recordMetric } from "../../../lib/metrics";

export const runtime = "nodejs";

const _requestStart = new WeakMap<Request, number>();

// ── RAG: keyword retrieval over curated knowledge base (Day 4) ──────────
function ragRetrieve(
  query: string,
  subject: string,
  gradeLevel: number,
  topK = 2
): Array<{ topic: string; text: string; source: string }> {
  const q = query.toLowerCase();
  const terms = q.split(/\s+/).filter((w) => w.length > 2);
  if (terms.length === 0) return [];

  const scored = knowledgeBase
    .filter((c) => {
      const subjectMatch = c.subject === subject.toLowerCase() || c.subject === "general";
      const [lo, hi] = c.grade_range.split("-").map(Number);
      const gradeMatch = gradeLevel >= lo && gradeLevel <= hi;
      return subjectMatch && gradeMatch;
    })
    .map((c) => {
      let score = 0;
      const haystack = (c.text + " " + c.topic).toLowerCase();
      for (const term of terms) {
        if (c.topic.toLowerCase().includes(term)) score += 3;
        const count = (haystack.match(new RegExp(term, "g")) ?? []).length;
        score += Math.log(1 + count);
      }
      return { ...c, score };
    })
    .filter((r) => r.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, topK);

  return scored;
}

function formatRAGContext(results: ReturnType<typeof ragRetrieve>): string {
  if (results.length === 0) return "";
  const lines = ["\n\n## Knowledge Base Context (RAG)\n"];
  for (const r of results) {
    lines.push(`**${r.topic}** (source: ${r.source})\n${r.text}\n`);
  }
  return lines.join("\n");
}

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

    const requestStart = Date.now();
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

    // Day 4: RAG — retrieve relevant knowledge chunks and inject into prompt
    const ragResults = ragRetrieve(message, subject, gradeLevel, 2);
    const ragContext = formatRAGContext(ragResults);

    const fullPrompt = `${systemPrompt}${ragContext}${historyText}\n\nSTUDENT: ${message}\n\nTUTOR:`;

    // Day 4: TutorAgent uses Search Grounding; other agents use plain Gemini
    const useGrounding = intent === "explain";

    const requestBody = useGrounding
      ? {
          contents: [{ parts: [{ text: fullPrompt }] }],
          tools: [{ googleSearch: {} }],
          generationConfig: { maxOutputTokens: 800, temperature: 0.7 },
        }
      : {
          contents: [{ parts: [{ text: fullPrompt }] }],
          generationConfig: { maxOutputTokens: 800, temperature: 0.7 },
        };

    const geminiRes = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${GEMINI_API_KEY}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
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

    // Extract grounding metadata (Day 4)
    const groundingMeta = geminiData.candidates?.[0]?.groundingMetadata;
    const sources: Array<{ title: string; uri: string }> =
      groundingMeta?.groundingChunks
        ?.filter((c: { web?: { title?: string; uri?: string } }) => c.web)
        .map((c: { web: { title?: string; uri?: string } }) => ({
          title: c.web.title ?? "",
          uri: c.web.uri ?? "",
        })) ?? [];
    const searchQueries: string[] = groundingMeta?.webSearchQueries ?? [];

    // Safety check every response (Day 1 layer)
    const { safe, response: safetyResponse } = safetyCheck(rawResponse);

    // Day 5: Spec Validator — runtime contract enforcement against SPEC.md
    const specResult = specCheck({
      response: safetyResponse,
      agent: agentName,
      intent,
      grade_level: gradeLevel,
    });
    const response = specResult.response;

    // Update context for client to persist
    const updatedHistory = [
      ...history,
      { role: "user", content: message },
      { role: "assistant", content: response },
    ].slice(-10);

    // Day 5: record telemetry before returning
    recordMetric({
      timestamp: Date.now(),
      agent: agentName,
      intent,
      latency_ms: Date.now() - requestStart,
      token_estimate: Math.ceil(response.length / 4),
      safe,
      grounded: useGrounding,
      rag_chunks: ragResults.length,
      spec_violations: specResult.spec_violations.length,
      hitl_required: specResult.hitl_required,
    });

    return NextResponse.json({
      response,
      agent: agentName,
      intent,
      safe,
      // Day 4: grounding metadata for citation rendering in UI
      grounding: useGrounding
        ? { sources, search_queries: searchQueries, grounded: true }
        : null,
      // Day 4: RAG metadata
      rag: ragResults.length > 0
        ? { chunks_used: ragResults.map((r) => r.topic), count: ragResults.length }
        : null,
      updated_context: {
        recent_history: updatedHistory,
        current_topic: extractTopic(message, topic),
        session_summary: session_summary,
        mastery_summary: body.mastery_summary || {},
      },
      // Day 5: spec validation metadata
      spec: {
        version: specResult.spec_version,
        violations: specResult.spec_violations,
        hitl_required: specResult.hitl_required,
      },
      audit: {
        routing_confidence: 0.9,
        topic,
        agent: agentName,
        grounded: useGrounding,
        safe,
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
