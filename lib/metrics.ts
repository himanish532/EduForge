/**
 * EduForge Observability — In-memory metrics store.
 *
 * Day 5: MLOps observability without external services.
 * Tracks per-request telemetry in a module-level singleton (persists across
 * requests within one Vercel function instance). For production at scale,
 * this pattern would be backed by a time-series store — but for a prototype
 * demo it captures everything needed to demonstrate MLOps concepts.
 *
 * Metrics tracked:
 *   - request_count: total API calls
 *   - agent_distribution: how often each agent is routed to
 *   - intent_distribution: explain / quiz / progress / resources / unsafe
 *   - latency_p50/p95: response time percentiles
 *   - token_usage: total tokens consumed, average per request
 *   - safety_flag_rate: fraction of requests that hit safety block
 *   - spec_violation_rate: fraction with spec contract violations
 *   - rag_hit_rate: fraction where RAG retrieved relevant chunks
 *   - grounding_rate: fraction using search grounding
 *   - skill_distribution: which skills were activated
 */

export interface RequestMetric {
  timestamp: number;
  agent: string;
  intent: string;
  latency_ms: number;
  token_estimate: number;
  safe: boolean;
  grounded: boolean;
  rag_chunks: number;
  spec_violations: number;
  hitl_required: boolean;
  skill_used?: string;
}

// Module-level singleton — survives across requests in a warm function instance
const _metrics: RequestMetric[] = [];
const MAX_METRICS = 500; // cap memory usage

export function recordMetric(m: RequestMetric): void {
  _metrics.push(m);
  if (_metrics.length > MAX_METRICS) _metrics.shift();
}

export interface MetricsSummary {
  request_count: number;
  window_minutes: number;
  agent_distribution: Record<string, number>;
  intent_distribution: Record<string, number>;
  skill_distribution: Record<string, number>;
  latency: { p50_ms: number; p95_ms: number; avg_ms: number };
  tokens: { total: number; avg_per_request: number };
  safety_flag_rate: number;
  spec_violation_rate: number;
  rag_hit_rate: number;
  grounding_rate: number;
  hitl_rate: number;
  recent: RequestMetric[];
  spec_version: string;
  model: string;
}

function percentile(sorted: number[], p: number): number {
  if (sorted.length === 0) return 0;
  const idx = Math.ceil((p / 100) * sorted.length) - 1;
  return sorted[Math.max(0, idx)];
}

function dist(items: string[]): Record<string, number> {
  return items.reduce<Record<string, number>>((acc, k) => {
    acc[k] = (acc[k] ?? 0) + 1;
    return acc;
  }, {});
}

export function getMetricsSummary(windowMinutes = 60): MetricsSummary {
  const cutoff = Date.now() - windowMinutes * 60 * 1000;
  const window = _metrics.filter((m) => m.timestamp >= cutoff);
  const n = window.length;

  const latencies = window.map((m) => m.latency_ms).sort((a, b) => a - b);
  const totalTokens = window.reduce((s, m) => s + m.token_estimate, 0);

  return {
    request_count: n,
    window_minutes: windowMinutes,
    agent_distribution: dist(window.map((m) => m.agent)),
    intent_distribution: dist(window.map((m) => m.intent)),
    skill_distribution: dist(window.flatMap((m) => (m.skill_used ? [m.skill_used] : []))),
    latency: {
      p50_ms: Math.round(percentile(latencies, 50)),
      p95_ms: Math.round(percentile(latencies, 95)),
      avg_ms: n > 0 ? Math.round(latencies.reduce((s, v) => s + v, 0) / n) : 0,
    },
    tokens: {
      total: totalTokens,
      avg_per_request: n > 0 ? Math.round(totalTokens / n) : 0,
    },
    safety_flag_rate: n > 0 ? window.filter((m) => !m.safe).length / n : 0,
    spec_violation_rate: n > 0 ? window.filter((m) => m.spec_violations > 0).length / n : 0,
    rag_hit_rate: n > 0 ? window.filter((m) => m.rag_chunks > 0).length / n : 0,
    grounding_rate: n > 0 ? window.filter((m) => m.grounded).length / n : 0,
    hitl_rate: n > 0 ? window.filter((m) => m.hitl_required).length / n : 0,
    recent: window.slice(-10).reverse(),
    spec_version: "1.0.0",
    model: "gemini-2.5-flash",
  };
}

export function clearMetrics(): void {
  _metrics.length = 0;
}
