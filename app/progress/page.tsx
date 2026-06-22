"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, BookOpen, Target, Zap, CheckCircle, Clock, Brain } from "lucide-react";

interface MasteryTopic {
  topic: string;
  mastery: number;
  attempts: number;
  tier: "not-started" | "learning" | "practiced" | "mastered";
}

interface LessonResult {
  correlation_id: string;
  topic: string;
  explanation: string;
  quiz_data: {
    question: string;
    options: string[];
    correct_index: number;
    explanation: string;
    difficulty: string;
  } | null;
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

const SAMPLE_MASTERY: MasteryTopic[] = [
  { topic: "Fractions", mastery: 0.85, attempts: 6, tier: "mastered" },
  { topic: "Decimals", mastery: 0.72, attempts: 4, tier: "practiced" },
  { topic: "Percentages", mastery: 0.45, attempts: 2, tier: "learning" },
  { topic: "Algebra Basics", mastery: 0.3, attempts: 1, tier: "learning" },
  { topic: "Linear Equations", mastery: 0.0, attempts: 0, tier: "not-started" },
  { topic: "Quadratic Equations", mastery: 0.0, attempts: 0, tier: "not-started" },
];

const SUBJECTS = ["math", "science", "history", "coding", "english"];

function getTierColor(tier: string): string {
  switch (tier) {
    case "mastered": return "text-green-600 bg-green-50 border-green-200";
    case "practiced": return "text-blue-600 bg-blue-50 border-blue-200";
    case "learning": return "text-yellow-600 bg-yellow-50 border-yellow-200";
    default: return "text-gray-400 bg-gray-50 border-gray-200";
  }
}

function getMasteryBarColor(mastery: number): string {
  if (mastery >= 0.8) return "bg-green-500";
  if (mastery >= 0.5) return "bg-blue-500";
  if (mastery > 0) return "bg-yellow-500";
  return "bg-gray-200";
}

function TierBadge({ tier }: { tier: string }) {
  const icons: Record<string, React.ReactNode> = {
    mastered: <CheckCircle className="w-3 h-3" />,
    practiced: <Target className="w-3 h-3" />,
    learning: <Brain className="w-3 h-3" />,
    "not-started": <Clock className="w-3 h-3" />,
  };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded border ${getTierColor(tier)}`}>
      {icons[tier]}
      {tier.replace("-", " ")}
    </span>
  );
}

function DAGVisualizer({ nodes }: { nodes: LessonResult["nodes"] }) {
  const nodeLabels: Record<string, string> = {
    TutorNode: "Tutor",
    AssessmentNode: "Quiz",
    CurriculumNode: "Next Path",
  };
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {nodes.map((node, i) => (
        <div key={i} className="flex items-center gap-2">
          <div
            className={`px-3 py-2 rounded-lg border text-xs font-medium ${
              node.success
                ? "bg-green-50 border-green-200 text-green-700"
                : "bg-red-50 border-red-200 text-red-700"
            }`}
          >
            <div className="font-semibold">{nodeLabels[node.node_type] ?? node.node_type}</div>
            <div className="text-gray-400 font-normal">{Math.round(node.duration_ms)}ms</div>
          </div>
          {i < nodes.length - 1 && (
            <span className="text-gray-400 text-sm">→</span>
          )}
        </div>
      ))}
    </div>
  );
}

export default function ProgressPage() {
  const [subject, setSubject] = useState("math");
  const [gradeLevel, setGradeLevel] = useState(8);
  const [topic, setTopic] = useState("");
  const [lessonResult, setLessonResult] = useState<LessonResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [masteryTopics] = useState<MasteryTopic[]>(SAMPLE_MASTERY);

  async function startLesson() {
    if (!topic.trim()) return;
    setLoading(true);
    setError("");
    setLessonResult(null);
    try {
      const res = await fetch("/api/lesson", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: topic.trim(),
          student_id: "demo-student",
          subject,
          grade_level: gradeLevel,
          mastery_summary: Object.fromEntries(
            masteryTopics.map((t) => [t.topic.toLowerCase(), t.mastery])
          ),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "Lesson failed");
      setLessonResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="text-gray-400 hover:text-gray-600 transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Learning Progress</h1>
              <p className="text-xs text-gray-500">Curriculum path · Mastery tracker · DAG lesson workflow</p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Zap className="w-4 h-4 text-indigo-500" />
            Day 3 · Skills + DAG
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-8 space-y-8">
        {/* Mastery Overview */}
        <div className="bg-white rounded-xl border shadow-sm p-6">
          <div className="flex items-center gap-2 mb-4">
            <Target className="w-5 h-5 text-indigo-500" />
            <h2 className="font-semibold text-gray-900">Mastery Tracker</h2>
            <span className="text-xs text-gray-400 ml-auto">Subject: {subject}</span>
          </div>
          <div className="space-y-3">
            {masteryTopics.map((item) => (
              <div key={item.topic} className="flex items-center gap-4">
                <div className="w-36 text-sm text-gray-700 font-medium shrink-0">{item.topic}</div>
                <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${getMasteryBarColor(item.mastery)}`}
                    style={{ width: `${item.mastery * 100}%` }}
                  />
                </div>
                <div className="w-10 text-xs text-gray-500 text-right">{Math.round(item.mastery * 100)}%</div>
                <TierBadge tier={item.tier} />
              </div>
            ))}
          </div>
        </div>

        {/* Start Lesson via DAG */}
        <div className="bg-white rounded-xl border shadow-sm p-6">
          <div className="flex items-center gap-2 mb-4">
            <BookOpen className="w-5 h-5 text-indigo-500" />
            <h2 className="font-semibold text-gray-900">Start a Lesson</h2>
            <span className="text-xs text-gray-400 ml-auto">DAG: Tutor → Assessment → Curriculum</span>
          </div>

          <div className="grid grid-cols-3 gap-3 mb-4">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Subject</label>
              <select
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full text-sm border rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
              >
                {SUBJECTS.map((s) => (
                  <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Grade Level</label>
              <select
                value={gradeLevel}
                onChange={(e) => setGradeLevel(Number(e.target.value))}
                className="w-full text-sm border rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
              >
                {Array.from({ length: 12 }, (_, i) => i + 1).map((g) => (
                  <option key={g} value={g}>Grade {g}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Topic</label>
              <input
                type="text"
                placeholder="e.g. Photosynthesis"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && startLesson()}
                className="w-full text-sm border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
            </div>
          </div>

          <button
            onClick={startLesson}
            disabled={loading || !topic.trim()}
            className="w-full py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? "Running DAG lesson..." : "Start Lesson"}
          </button>

          {error && (
            <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}
        </div>

        {/* Lesson DAG Results */}
        {lessonResult && (
          <div className="space-y-4">
            {/* DAG Pipeline Visualization */}
            <div className="bg-white rounded-xl border shadow-sm p-6">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-gray-900 text-sm">DAG Execution</h3>
                <div className="flex items-center gap-4 text-xs text-gray-500">
                  <span>{lessonResult.total_tokens} tokens</span>
                  <span>{Math.round(lessonResult.total_duration_ms)}ms</span>
                  <span className="font-mono text-gray-400">{lessonResult.correlation_id.slice(0, 8)}</span>
                </div>
              </div>
              <DAGVisualizer nodes={lessonResult.nodes} />
            </div>

            {/* Explanation */}
            <div className="bg-white rounded-xl border shadow-sm p-6">
              <div className="flex items-center gap-2 mb-3">
                <BookOpen className="w-4 h-4 text-indigo-500" />
                <h3 className="font-semibold text-gray-900 text-sm">Explanation — TutorNode</h3>
                <span className="ml-auto text-xs text-gray-400">skill: subject-tutor</span>
              </div>
              <p className="text-gray-700 text-sm leading-relaxed whitespace-pre-wrap">
                {lessonResult.explanation}
              </p>
            </div>

            {/* Quiz */}
            {lessonResult.quiz_data && (
              <div className="bg-white rounded-xl border shadow-sm p-6">
                <div className="flex items-center gap-2 mb-3">
                  <Target className="w-4 h-4 text-indigo-500" />
                  <h3 className="font-semibold text-gray-900 text-sm">Quiz — AssessmentNode</h3>
                  <span className="ml-auto text-xs text-gray-400">skill: quiz-generator · {lessonResult.quiz_data.difficulty}</span>
                </div>
                <p className="font-medium text-gray-800 mb-3 text-sm">{lessonResult.quiz_data.question}</p>
                <div className="space-y-2">
                  {lessonResult.quiz_data.options.map((opt, i) => (
                    <div
                      key={i}
                      className={`p-3 rounded-lg border text-sm ${
                        i === lessonResult.quiz_data!.correct_index
                          ? "bg-green-50 border-green-300 text-green-800"
                          : "bg-gray-50 border-gray-200 text-gray-600"
                      }`}
                    >
                      {String.fromCharCode(65 + i)}. {opt}
                    </div>
                  ))}
                </div>
                <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-700">
                  <strong>Explanation:</strong> {lessonResult.quiz_data.explanation}
                </div>
              </div>
            )}

            {/* Next Topic */}
            {lessonResult.next_topic && (
              <div className="bg-white rounded-xl border shadow-sm p-6">
                <div className="flex items-center gap-2 mb-2">
                  <Zap className="w-4 h-4 text-indigo-500" />
                  <h3 className="font-semibold text-gray-900 text-sm">Next Topic — CurriculumNode</h3>
                  <span className="ml-auto text-xs text-gray-400">skill: learning-path</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-medium text-indigo-700">{lessonResult.next_topic}</span>
                  {lessonResult.requires_teacher_approval && (
                    <span className="text-xs bg-orange-50 text-orange-600 border border-orange-200 px-2 py-0.5 rounded">
                      Requires teacher approval (HITL)
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
