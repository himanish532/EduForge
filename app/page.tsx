"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  BookOpen,
  Brain,
  ChevronRight,
  FlaskConical,
  Globe,
  History,
  Lightbulb,
  Shield,
  Sparkles,
  Calculator,
} from "lucide-react";

const SUBJECTS = [
  { id: "math", label: "Mathematics", icon: Calculator, color: "bg-blue-50 border-blue-200 text-blue-700 hover:bg-blue-100" },
  { id: "science", label: "Science", icon: FlaskConical, color: "bg-green-50 border-green-200 text-green-700 hover:bg-green-100" },
  { id: "history", label: "History", icon: History, color: "bg-amber-50 border-amber-200 text-amber-700 hover:bg-amber-100" },
  { id: "english", label: "English", icon: BookOpen, color: "bg-purple-50 border-purple-200 text-purple-700 hover:bg-purple-100" },
  { id: "coding", label: "Coding", icon: Brain, color: "bg-rose-50 border-rose-200 text-rose-700 hover:bg-rose-100" },
  { id: "geography", label: "Geography", icon: Globe, color: "bg-teal-50 border-teal-200 text-teal-700 hover:bg-teal-100" },
];

const GRADES = Array.from({ length: 12 }, (_, i) => i + 1);

const FEATURES = [
  {
    icon: Sparkles,
    title: "Socratic Tutoring",
    desc: "Never just told answers — guided to discover them yourself through intelligent questioning.",
  },
  {
    icon: Brain,
    title: "Adaptive Quizzes",
    desc: "Assessments that match your mastery level, generated on-the-fly by the Assessment Agent.",
  },
  {
    icon: Lightbulb,
    title: "Personalized Path",
    desc: "A Curriculum Agent tracks your mastery and always knows what to teach you next.",
  },
  {
    icon: Shield,
    title: "Safe by Design",
    desc: "Every response passes through a Safety Agent before it reaches you. Always age-appropriate.",
  },
];

export default function HomePage() {
  const router = useRouter();
  const [subject, setSubject] = useState("");
  const [grade, setGrade] = useState<number>(8);

  const handleStart = () => {
    if (!subject) return;
    router.push(`/tutor?subject=${subject}&grade=${grade}`);
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-slate-800 text-lg">EduForge</span>
            <span className="text-xs bg-brand-100 text-brand-700 px-2 py-0.5 rounded-full font-medium">
              Agents for Good
            </span>
          </div>
          <div className="text-xs text-slate-400 hidden sm:block">
            Powered by Google Gemini · Multi-Agent AI
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-4 pt-16 pb-12 text-center">
        <div className="inline-flex items-center gap-2 bg-white border border-slate-200 rounded-full px-4 py-1.5 text-sm text-slate-600 mb-6 shadow-sm">
          <Sparkles className="w-3.5 h-3.5 text-brand-500" />
          Kaggle AI Agents Capstone · Agents for Good Track
        </div>
        <h1 className="text-4xl sm:text-5xl font-bold text-slate-900 mb-4 leading-tight">
          A world-class tutor
          <br />
          <span className="text-brand-600">for every student.</span>
        </h1>
        <p className="text-lg text-slate-500 max-w-xl mx-auto mb-10">
          EduForge is a multi-agent AI tutoring network that adapts to your
          learning style, grade level, and pace — for free.
        </p>

        {/* Setup card */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 max-w-2xl mx-auto text-left">
          <h2 className="font-semibold text-slate-800 mb-5">
            Start your session
          </h2>

          {/* Grade selector */}
          <div className="mb-6">
            <label className="text-sm font-medium text-slate-600 block mb-2">
              Your grade level
            </label>
            <div className="flex flex-wrap gap-2">
              {GRADES.map((g) => (
                <button
                  key={g}
                  onClick={() => setGrade(g)}
                  className={`w-10 h-10 rounded-lg text-sm font-medium border transition-all ${
                    grade === g
                      ? "bg-brand-600 text-white border-brand-600 shadow-sm"
                      : "bg-white text-slate-600 border-slate-200 hover:border-brand-300"
                  }`}
                >
                  {g}
                </button>
              ))}
            </div>
          </div>

          {/* Subject selector */}
          <div className="mb-8">
            <label className="text-sm font-medium text-slate-600 block mb-2">
              Choose a subject
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {SUBJECTS.map(({ id, label, icon: Icon, color }) => (
                <button
                  key={id}
                  onClick={() => setSubject(id)}
                  className={`flex items-center gap-2.5 p-3.5 rounded-xl border-2 text-sm font-medium transition-all ${
                    subject === id
                      ? "border-brand-500 bg-brand-50 text-brand-700 shadow-sm ring-2 ring-brand-200"
                      : color
                  }`}
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  {label}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={handleStart}
            disabled={!subject}
            className="w-full py-3.5 rounded-xl font-semibold text-white bg-brand-600 hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 shadow-sm"
          >
            Start Learning
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-4 pb-16">
        <h2 className="text-center text-sm font-semibold text-slate-400 uppercase tracking-widest mb-8">
          Powered by a 5-agent AI network
        </h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {FEATURES.map(({ icon: Icon, title, desc }) => (
            <div
              key={title}
              className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-md transition-shadow"
            >
              <div className="w-9 h-9 rounded-lg bg-brand-50 flex items-center justify-center mb-3">
                <Icon className="w-4.5 h-4.5 text-brand-600" />
              </div>
              <h3 className="font-semibold text-slate-800 text-sm mb-1">{title}</h3>
              <p className="text-xs text-slate-500 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Architecture badge */}
      <footer className="border-t border-slate-200 bg-white py-6 text-center text-xs text-slate-400">
        <p>
          Built with Google ADK · Gemini 2.0 Flash · Next.js · Vercel ·{" "}
          <a
            href="https://github.com/himanish532/EduForge"
            className="text-brand-500 hover:underline"
            target="_blank"
          >
            View on GitHub
          </a>
          {" · "}
          <a href="/admin" className="text-brand-500 hover:underline">
            Observability
          </a>
          {" · "}
          <a href="/progress" className="text-brand-500 hover:underline">
            Progress
          </a>
        </p>
        <p className="mt-1">
          Kaggle AI Agents Capstone 2026 — Agents for Good Track
        </p>
      </footer>
    </main>
  );
}
