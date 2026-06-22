/**
 * /api/rag — RAG retrieval endpoint.
 *
 * Day 4: Retrieval Augmented Generation.
 * Performs semantic search over the curated EduForge knowledge base.
 * Embeddings are pre-computed and stored in rag/embeddings.json.
 *
 * Since embeddings require Python + the file store, this route performs
 * keyword-based retrieval as the TypeScript layer (zero-infra compatible
 * with Vercel Edge). The Python embedding layer is available for local use.
 *
 * POST body: { query, subject?, grade_level?, top_k? }
 * Response: { results: [{chunk_id, topic, text, source, score}] }
 */

import { NextRequest, NextResponse } from "next/server";
import { knowledgeBase } from "../../../rag/knowledge_base";

export interface RAGResult {
  chunk_id: string;
  subject: string;
  topic: string;
  text: string;
  source: string;
  score: number;
}

/**
 * TF-IDF-lite keyword scoring: term frequency × log(1 + match count).
 * Good enough for a curated corpus of ~20 documents — no embedding needed.
 */
function keywordScore(query: string, text: string, topic: string): number {
  const q = query.toLowerCase();
  const t = (text + " " + topic).toLowerCase();
  const queryTerms = q.split(/\s+/).filter((w) => w.length > 2);
  if (queryTerms.length === 0) return 0;

  let score = 0;
  for (const term of queryTerms) {
    // Exact topic match is weighted heavily
    if (topic.toLowerCase().includes(term)) score += 3;
    // Count occurrences in text
    const count = (t.match(new RegExp(term, "g")) ?? []).length;
    score += Math.log(1 + count);
  }
  return score / queryTerms.length;
}

function gradeInRange(gradeRange: string, gradeLevel: number): boolean {
  const [lo, hi] = gradeRange.split("-").map(Number);
  return gradeLevel >= lo && gradeLevel <= hi;
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  let body: { query?: string; subject?: string; grade_level?: number; top_k?: number };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { query = "", subject, grade_level, top_k = 3 } = body;
  if (!query.trim()) {
    return NextResponse.json({ results: [] });
  }

  let chunks = knowledgeBase;

  // Subject filter (allow "general" chunks through always)
  if (subject) {
    chunks = chunks.filter(
      (c) => c.subject === subject.toLowerCase() || c.subject === "general"
    );
  }

  // Grade filter
  if (grade_level) {
    chunks = chunks.filter((c) => gradeInRange(c.grade_range, grade_level));
  }

  // Score and rank
  const scored = chunks
    .map((c) => ({
      chunk_id: c.chunk_id,
      subject: c.subject,
      topic: c.topic,
      text: c.text,
      source: c.source,
      score: keywordScore(query, c.text, c.topic),
    }))
    .filter((r) => r.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, top_k);

  return NextResponse.json({ results: scored });
}
