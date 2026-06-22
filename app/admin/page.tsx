"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Activity,
  Shield,
  Zap,
  Brain,
  RefreshCw,
  Trash2,
  BookOpen,
  Search,
} from "lucide-react";

interface MetricsSummary {
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
  spec_version: string;
  model: string;
  recent: Array<{
    timestamp: number;
    agent: string;
    intent: string;
    latency_ms: number;
    token_estimate: number;
    safe: boolean;
    grounded: boolean;
    rag_chunks: number;
    spec_violations: number;
  }>;
}

function pct(rate: number) {
  return `${Math.round(rate * 100)}%`;
}

function StatCard({
  label,
  value,
  sub,
  icon,
  color = "indigo",
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ReactNode;
  color?: string;
}) {
  const colors: Record<string, string> = {
    indigo: "bg-indigo-50 text-indigo-600 border-indigo-100",
    green: "bg-green-50 text-green-600 border-green-100",
    amber: "bg-amber-50 text-amber-600 border-amber-100",
    red: "bg-red-50 text-red-600 border-red-100",
    blue: "bg-blue-50 text-blue-600 border-blue-100",
  };
  return (
    <div className={`rounded-xl border p-4 ${colors[color]}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium opacity-70">{label}</span>
        {icon}
      </div>
      <div className="text-2xl font-bold">{value}</div>
      {sub && <div className="text-xs opacity-60 mt-0.5">{sub}</div>}
    </div>
  );
}

function DistBar({
  label,
  data,
  total,
}: {
  label: string;
  data: Record<string, number>;
  total: number;
}) {
  const colors = [
    "bg-indigo-400",
    "bg-blue-400",
    "bg-teal-400",
    "bg-emerald-400",
    "bg-amber-400",
    "bg-red-400",
  ];
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  return (
    <div>
      <p className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wide">{label}</p>
      <div className="space-y-1.5">
        {entries.map(([key, count], i) => (
          <div key={key} className="flex items-center gap-2">
            <span className="w-32 text-xs text-gray-600 truncate">{key}</span>
            <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${colors[i % colors.length]}`}
                style={{ width: `${total > 0 ? (count / total) * 100 : 0}%` }}
              />
            </div>
            <span className="text-xs text-gray-400 w-6 text-right">{count}</span>
          </div>
        ))}
        {entries.length === 0 && (
          <p className="text-xs text-gray-400 italic">No data yet</p>
        )}
      </div>
    </div>
  );
}

export default function AdminPage() {
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [window, setWindow] = useState(60);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchMetrics = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/metrics?window=${window}`);
      if (res.ok) {
        setMetrics(await res.json());
        setLastRefresh(new Date());
      }
    } finally {
      setLoading(false);
    }
  }, [window]);

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 30000);
    return () => clearInterval(interval);
  }, [fetchMetrics]);

  async function clearMetrics() {
    await fetch("/api/metrics", { method: "DELETE" });
    await fetchMetrics();
  }

  const n = metrics?.request_count ?? 0;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="text-gray-400 hover:text-gray-600 transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-gray-900">EduForge Observability</h1>
              <p className="text-xs text-gray-500">Day 5 · MLOps · Spec-Driven Production Monitoring</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={window}
              onChange={(e) => setWindow(Number(e.target.value))}
              className="text-xs border rounded-lg px-2 py-1.5 bg-white focus:outline-none"
            >
              <option value={15}>Last 15 min</option>
              <option value={60}>Last 1 hour</option>
              <option value={360}>Last 6 hours</option>
            </select>
            <button
              onClick={fetchMetrics}
              disabled={loading}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 border rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>
            <button
              onClick={clearMetrics}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 border border-red-200 text-red-600 rounded-lg hover:bg-red-50 transition-colors"
            >
              <Trash2 className="w-3 h-3" />
              Clear
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        {/* Spec + model info banner */}
        <div className="bg-indigo-50 border border-indigo-100 rounded-xl px-5 py-3 flex items-center justify-between text-xs">
          <div className="flex items-center gap-4">
            <span className="text-indigo-700 font-semibold">SPEC v{metrics?.spec_version ?? "1.0.0"}</span>
            <span className="text-indigo-500">Model: {metrics?.model ?? "gemini-2.0-flash"}</span>
            <span className="text-indigo-500">Window: {window} min</span>
          </div>
          {lastRefresh && (
            <span className="text-indigo-400">
              Last refresh: {lastRefresh.toLocaleTimeString()}
            </span>
          )}
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            label="Total Requests"
            value={n}
            sub={`in last ${window} min`}
            icon={<Activity className="w-4 h-4" />}
            color="indigo"
          />
          <StatCard
            label="Avg Latency"
            value={`${metrics?.latency.avg_ms ?? 0}ms`}
            sub={`p95: ${metrics?.latency.p95_ms ?? 0}ms`}
            icon={<Zap className="w-4 h-4" />}
            color="blue"
          />
          <StatCard
            label="Safety Flag Rate"
            value={pct(metrics?.safety_flag_rate ?? 0)}
            sub="blocked responses"
            icon={<Shield className="w-4 h-4" />}
            color={
              (metrics?.safety_flag_rate ?? 0) > 0.05 ? "red" : "green"
            }
          />
          <StatCard
            label="Spec Violations"
            value={pct(metrics?.spec_violation_rate ?? 0)}
            sub="contract breaches"
            icon={<Brain className="w-4 h-4" />}
            color={
              (metrics?.spec_violation_rate ?? 0) > 0.1 ? "amber" : "green"
            }
          />
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            label="Token Usage"
            value={metrics?.tokens.total.toLocaleString() ?? "0"}
            sub={`~${metrics?.tokens.avg_per_request ?? 0} avg/req`}
            icon={<BookOpen className="w-4 h-4" />}
            color="indigo"
          />
          <StatCard
            label="RAG Hit Rate"
            value={pct(metrics?.rag_hit_rate ?? 0)}
            sub="queries with KB retrieval"
            icon={<Search className="w-4 h-4" />}
            color="blue"
          />
          <StatCard
            label="Grounding Rate"
            value={pct(metrics?.grounding_rate ?? 0)}
            sub="Google Search grounded"
            icon={<Zap className="w-4 h-4" />}
            color="green"
          />
          <StatCard
            label="HITL Rate"
            value={pct(metrics?.hitl_rate ?? 0)}
            sub="teacher approval needed"
            icon={<Shield className="w-4 h-4" />}
            color="amber"
          />
        </div>

        {/* Distribution charts */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div className="bg-white rounded-xl border shadow-sm p-5">
            <DistBar
              label="Agent Distribution"
              data={metrics?.agent_distribution ?? {}}
              total={n}
            />
          </div>
          <div className="bg-white rounded-xl border shadow-sm p-5">
            <DistBar
              label="Intent Distribution"
              data={metrics?.intent_distribution ?? {}}
              total={n}
            />
          </div>
          <div className="bg-white rounded-xl border shadow-sm p-5">
            <DistBar
              label="Skill Activations"
              data={metrics?.skill_distribution ?? {}}
              total={n}
            />
          </div>
        </div>

        {/* Recent requests table */}
        <div className="bg-white rounded-xl border shadow-sm">
          <div className="px-5 py-4 border-b flex items-center justify-between">
            <h3 className="font-semibold text-gray-900 text-sm">Recent Requests</h3>
            <span className="text-xs text-gray-400">last 10</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b bg-gray-50">
                  {["Time", "Agent", "Intent", "Latency", "Tokens", "Safe", "Grounded", "RAG", "Spec"].map(
                    (h) => (
                      <th
                        key={h}
                        className="px-4 py-2 text-left text-gray-500 font-medium"
                      >
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {(metrics?.recent ?? []).map((r, i) => (
                  <tr key={i} className="border-b hover:bg-gray-50">
                    <td className="px-4 py-2 text-gray-400">
                      {new Date(r.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="px-4 py-2 font-medium text-indigo-700">{r.agent}</td>
                    <td className="px-4 py-2 text-gray-600">{r.intent}</td>
                    <td className="px-4 py-2 text-gray-600">{r.latency_ms}ms</td>
                    <td className="px-4 py-2 text-gray-600">~{r.token_estimate}</td>
                    <td className="px-4 py-2">
                      <span
                        className={`px-1.5 py-0.5 rounded text-xs ${
                          r.safe
                            ? "bg-green-50 text-green-600"
                            : "bg-red-50 text-red-600"
                        }`}
                      >
                        {r.safe ? "✓" : "✗"}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      <span className={r.grounded ? "text-green-600" : "text-gray-300"}>
                        {r.grounded ? "✓" : "—"}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-gray-600">{r.rag_chunks}</td>
                    <td className="px-4 py-2">
                      <span
                        className={`px-1.5 py-0.5 rounded text-xs ${
                          r.spec_violations === 0
                            ? "bg-green-50 text-green-600"
                            : "bg-amber-50 text-amber-600"
                        }`}
                      >
                        {r.spec_violations === 0 ? "✓" : `${r.spec_violations}v`}
                      </span>
                    </td>
                  </tr>
                ))}
                {(metrics?.recent ?? []).length === 0 && (
                  <tr>
                    <td colSpan={9} className="px-4 py-8 text-center text-gray-400">
                      No requests recorded yet — start a chat session to see metrics.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
