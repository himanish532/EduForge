"use client";

/**
 * QuizCard — A2UI Component
 *
 * Day 2 concept: A2UI (Agent-to-UI Interoperability).
 * The AssessmentAgent emits structured quiz_data JSON.
 * This component transforms that raw JSON into a safe, interactive UI.
 * The agent never generates HTML — it generates data; the UI renders it.
 *
 * This is the "Generative Display Window" pattern from the whitepaper.
 */

import { useState } from "react";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";
import clsx from "clsx";
import ReactMarkdown from "react-markdown";

export interface QuizData {
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
  topic: string;
  difficulty: "beginner" | "intermediate" | "advanced";
}

interface QuizCardProps {
  quiz: QuizData;
  studentId: string;
  topic: string;
  priorMastery: number;
  onResult: (result: QuizResult) => void;
}

export interface QuizResult {
  correct: boolean;
  score: number;
  feedback: string;
  new_mastery: number;
  topic: string;
}

const DIFFICULTY_STYLES = {
  beginner: "bg-green-50 text-green-700 border-green-200",
  intermediate: "bg-amber-50 text-amber-700 border-amber-200",
  advanced: "bg-red-50 text-red-700 border-red-200",
};

const OPTION_LETTERS = ["A", "B", "C", "D"];

export default function QuizCard({
  quiz,
  studentId,
  topic,
  priorMastery,
  onResult,
}: QuizCardProps) {
  const [selected, setSelected] = useState<number | null>(null);
  const [result, setResult] = useState<QuizResult | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSelect = async (index: number) => {
    if (selected !== null || loading) return;
    setSelected(index);
    setLoading(true);

    try {
      const res = await fetch("/api/quiz", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          quiz,
          selected_index: index,
          student_id: studentId,
          topic,
          prior_mastery: priorMastery,
        }),
      });
      const data = await res.json();
      setResult(data);
      onResult(data);
    } catch {
      setResult({
        correct: false,
        score: 0,
        feedback: "Could not score answer. Please try again.",
        new_mastery: priorMastery,
        topic,
      });
    } finally {
      setLoading(false);
    }
  };

  const getOptionStyle = (index: number) => {
    if (selected === null) {
      return "border-slate-200 bg-white hover:border-brand-300 hover:bg-brand-50 cursor-pointer";
    }
    if (index === quiz.correct_index) {
      return "border-green-400 bg-green-50 text-green-800";
    }
    if (index === selected && index !== quiz.correct_index) {
      return "border-red-400 bg-red-50 text-red-800";
    }
    return "border-slate-100 bg-slate-50 text-slate-400";
  };

  const masteryPercent = Math.round((result?.new_mastery ?? priorMastery) * 100);

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden my-2">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-slate-700">Quiz</span>
          <span
            className={clsx(
              "text-xs px-2 py-0.5 rounded-full border font-medium capitalize",
              DIFFICULTY_STYLES[quiz.difficulty] || DIFFICULTY_STYLES.beginner
            )}
          >
            {quiz.difficulty}
          </span>
        </div>
        <span className="text-xs text-slate-400">{quiz.topic}</span>
      </div>

      {/* Question */}
      <div className="px-4 py-4">
        <p className="text-sm font-medium text-slate-800 mb-4 leading-relaxed">
          {quiz.question}
        </p>

        {/* Options */}
        <div className="space-y-2">
          {quiz.options.map((option, index) => (
            <button
              key={index}
              onClick={() => handleSelect(index)}
              disabled={selected !== null || loading}
              className={clsx(
                "w-full text-left px-4 py-3 rounded-lg border-2 text-sm transition-all flex items-center gap-3",
                getOptionStyle(index)
              )}
            >
              <span
                className={clsx(
                  "w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0",
                  selected === null
                    ? "bg-slate-100 text-slate-500"
                    : index === quiz.correct_index
                    ? "bg-green-500 text-white"
                    : index === selected
                    ? "bg-red-500 text-white"
                    : "bg-slate-200 text-slate-400"
                )}
              >
                {loading && selected === index ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  OPTION_LETTERS[index]
                )}
              </span>
              <span>{option.replace(/^[A-D]\.\s*/, "")}</span>
              {selected !== null && index === quiz.correct_index && (
                <CheckCircle className="w-4 h-4 text-green-500 ml-auto flex-shrink-0" />
              )}
              {selected === index && index !== quiz.correct_index && (
                <XCircle className="w-4 h-4 text-red-500 ml-auto flex-shrink-0" />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Feedback */}
      {result && (
        <div
          className={clsx(
            "px-4 py-4 border-t text-sm",
            result.correct ? "border-green-100 bg-green-50" : "border-red-100 bg-red-50"
          )}
        >
          <div className="prose-chat mb-3">
            <ReactMarkdown>{result.feedback}</ReactMarkdown>
          </div>

          {/* Mastery progress */}
          <div className="flex items-center gap-3 mt-3 pt-3 border-t border-slate-200">
            <span className="text-xs text-slate-500 whitespace-nowrap">
              {quiz.topic} mastery
            </span>
            <div className="flex-1 h-2 bg-slate-200 rounded-full">
              <div
                className="h-full bg-brand-500 rounded-full transition-all duration-700"
                style={{ width: `${masteryPercent}%` }}
              />
            </div>
            <span className="text-xs font-semibold text-slate-600 whitespace-nowrap">
              {masteryPercent}%
            </span>
          </div>
        </div>
      )}

      {/* A2UI label */}
      <div className="px-4 py-2 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
        <span className="text-xs text-slate-400">A2UI · Generated by AssessmentAgent</span>
        {result && (
          <span className="text-xs text-slate-400">
            A2A → CurriculumAgent notified
          </span>
        )}
      </div>
    </div>
  );
}
