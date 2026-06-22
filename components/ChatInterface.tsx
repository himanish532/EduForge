"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ArrowLeft,
  BookOpen,
  Brain,
  ChevronRight,
  Loader2,
  Send,
  Shield,
  Sparkles,
  User,
} from "lucide-react";
import Link from "next/link";
import clsx from "clsx";
import QuizCard, { type QuizData, type QuizResult } from "./QuizCard";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  agent?: string;
  intent?: string;
  quizData?: QuizData;
  timestamp: number;
}

interface SessionContext {
  student_id: string;
  session_summary: string;
  recent_history: { role: string; content: string }[];
  mastery_summary: Record<string, number>;
  current_topic: string;
}

interface ChatInterfaceProps {
  subject: string;
  gradeLevel: number;
}

const SUBJECT_LABELS: Record<string, string> = {
  math: "Mathematics",
  science: "Science",
  history: "History",
  english: "English",
  coding: "Coding",
  geography: "Geography",
  general: "General",
};

const AGENT_COLORS: Record<string, string> = {
  TutorAgent: "text-blue-600 bg-blue-50",
  AssessmentAgent: "text-green-600 bg-green-50",
  CurriculumAgent: "text-purple-600 bg-purple-50",
  ContentAgent: "text-amber-600 bg-amber-50",
  SafetyAgent: "text-red-600 bg-red-50",
};

const INTENT_ICONS: Record<string, string> = {
  explain: "💡",
  quiz: "🎯",
  progress: "📊",
  resources: "📚",
  unsafe: "🛡️",
};

const SUGGESTED_PROMPTS: Record<string, string[]> = {
  math: [
    "Explain quadratic equations to me",
    "Quiz me on algebra",
    "What should I learn next?",
    "Show me resources for calculus",
  ],
  science: [
    "How does photosynthesis work?",
    "Quiz me on the periodic table",
    "What should I learn next?",
    "Find videos about gravity",
  ],
  history: [
    "Tell me about World War II",
    "Quiz me on ancient civilizations",
    "What's my learning path?",
    "Find resources on the Renaissance",
  ],
  coding: [
    "Explain recursion to me",
    "Quiz me on Python basics",
    "What should I learn next?",
    "Show me resources for algorithms",
  ],
  default: [
    "Explain a concept to me",
    "Quiz me on something",
    "Show my learning progress",
    "Find learning resources",
  ],
};

function generateStudentId(): string {
  return `student-${Math.random().toString(36).slice(2, 9)}`;
}

export default function ChatInterface({ subject, gradeLevel }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionCtx, setSessionCtx] = useState<SessionContext>({
    student_id: generateStudentId(),
    session_summary: "",
    recent_history: [],
    mastery_summary: {},
    current_topic: "",
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Welcome message on mount
  useEffect(() => {
    const welcome: Message = {
      id: "welcome",
      role: "assistant",
      content: `👋 Welcome to EduForge! I'm your AI tutor for **${SUBJECT_LABELS[subject] || subject}** at Grade **${gradeLevel}**.\n\nI'll guide you through concepts using questions rather than just giving you answers — that's how real learning sticks!\n\nWhat would you like to explore today?`,
      agent: "TutorAgent",
      timestamp: Date.now(),
    };
    setMessages([welcome]);
  }, [subject, gradeLevel]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || loading) return;

      const userMsg: Message = {
        id: `u-${Date.now()}`,
        role: "user",
        content: text.trim(),
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setLoading(true);

      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: text.trim(),
            subject,
            grade_level: gradeLevel,
            student_id: sessionCtx.student_id,
            session_summary: sessionCtx.session_summary,
            recent_history: sessionCtx.recent_history,
            mastery_summary: sessionCtx.mastery_summary,
            current_topic: sessionCtx.current_topic,
          }),
        });

        const data = await res.json();

        if (!res.ok) {
          throw new Error(data.error || "Server error");
        }

        // If intent is quiz, generate structured quiz via /api/quiz (A2UI flow)
        let quizData: QuizData | undefined;
        if (data.intent === "quiz") {
          try {
            const quizRes = await fetch("/api/quiz", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                topic: data.updated_context?.current_topic || subject,
                subject,
                grade_level: gradeLevel,
                mastery: sessionCtx.mastery_summary[data.updated_context?.current_topic || subject] ?? 0,
              }),
            });
            if (quizRes.ok) {
              const quizJson = await quizRes.json();
              quizData = quizJson.quiz as QuizData;
            }
          } catch {
            // Quiz generation failure is non-fatal — fall back to text response
          }
        }

        const assistantMsg: Message = {
          id: `a-${Date.now()}`,
          role: "assistant",
          content: data.response || "I had trouble generating a response. Please try again.",
          agent: data.agent,
          intent: data.intent,
          quizData,
          timestamp: Date.now(),
        };
        setMessages((prev) => [...prev, assistantMsg]);

        // Update session context from server response
        if (data.updated_context) {
          setSessionCtx((prev) => ({
            ...prev,
            ...data.updated_context,
          }));
        }
      } catch (err) {
        const errMsg: Message = {
          id: `err-${Date.now()}`,
          role: "assistant",
          content: "⚠️ I'm having trouble connecting right now. Please check that your API key is configured and try again.",
          agent: "System",
          timestamp: Date.now(),
        };
        setMessages((prev) => [...prev, errMsg]);
      } finally {
        setLoading(false);
        inputRef.current?.focus();
      }
    },
    [loading, subject, gradeLevel, sessionCtx]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const suggestions = SUGGESTED_PROMPTS[subject] || SUGGESTED_PROMPTS.default;
  const masteryEntries = Object.entries(sessionCtx.mastery_summary);

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="hidden lg:flex flex-col w-64 bg-white border-r border-slate-200 p-4">
        <Link
          href="/"
          className="flex items-center gap-2 text-slate-500 hover:text-slate-800 text-sm mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to home
        </Link>

        <div className="flex items-center gap-2 mb-6">
          <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <p className="font-semibold text-slate-800 text-sm">EduForge</p>
            <p className="text-xs text-slate-400">
              {SUBJECT_LABELS[subject]} · Grade {gradeLevel}
            </p>
          </div>
        </div>

        {/* Agent network status */}
        <div className="mb-6">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            Active Agents
          </p>
          {[
            { name: "Orchestrator", icon: Brain, desc: "Routes intent" },
            { name: "TutorAgent", icon: BookOpen, desc: "Explains concepts" },
            { name: "AssessmentAgent", icon: ChevronRight, desc: "Generates quizzes" },
            { name: "SafetyAgent", icon: Shield, desc: "Filters content" },
          ].map(({ name, icon: Icon, desc }) => (
            <div key={name} className="flex items-center gap-2 py-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-green-400" />
              <Icon className="w-3.5 h-3.5 text-slate-400" />
              <div>
                <p className="text-xs font-medium text-slate-700">{name}</p>
                <p className="text-xs text-slate-400">{desc}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Mastery tracker */}
        {masteryEntries.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
              Topic Mastery
            </p>
            {masteryEntries.slice(-5).map(([topic, score]) => (
              <div key={topic} className="mb-2">
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-600 truncate">{topic}</span>
                  <span className="text-slate-400 ml-2">{Math.round(score * 100)}%</span>
                </div>
                <div className="h-1.5 bg-slate-100 rounded-full">
                  <div
                    className="h-full bg-brand-500 rounded-full transition-all"
                    style={{ width: `${score * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="mt-auto pt-4 border-t border-slate-100">
          <p className="text-xs text-slate-400">
            Session ID: {sessionCtx.student_id.slice(-6)}
          </p>
          {sessionCtx.current_topic && (
            <p className="text-xs text-slate-400 mt-0.5">
              Topic: {sessionCtx.current_topic}
            </p>
          )}
        </div>
      </aside>

      {/* Main chat area */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Mobile header */}
        <header className="lg:hidden flex items-center gap-3 px-4 py-3 bg-white border-b border-slate-200">
          <Link href="/" className="text-slate-400 hover:text-slate-700">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <p className="font-semibold text-slate-800 text-sm">EduForge</p>
            <p className="text-xs text-slate-400">
              {SUBJECT_LABELS[subject]} · Grade {gradeLevel}
            </p>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={clsx("flex gap-3", msg.role === "user" ? "justify-end" : "justify-start")}
            >
              {msg.role === "assistant" && (
                <div className="w-8 h-8 rounded-full bg-brand-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Sparkles className="w-4 h-4 text-brand-600" />
                </div>
              )}

              <div className={clsx("max-w-[80%] space-y-1", msg.role === "user" ? "items-end" : "items-start")}>
                {/* Agent badge */}
                {msg.agent && msg.role === "assistant" && (
                  <div className="flex items-center gap-1.5 mb-1">
                    <span
                      className={clsx(
                        "text-xs font-medium px-2 py-0.5 rounded-full",
                        AGENT_COLORS[msg.agent] || "text-slate-500 bg-slate-100"
                      )}
                    >
                      {msg.agent}
                    </span>
                    {msg.intent && (
                      <span className="text-xs text-slate-400">
                        {INTENT_ICONS[msg.intent]} {msg.intent}
                      </span>
                    )}
                  </div>
                )}

                <div
                  className={clsx(
                    "rounded-2xl px-4 py-3 text-sm leading-relaxed",
                    msg.role === "user"
                      ? "bg-brand-600 text-white rounded-tr-sm"
                      : "bg-white border border-slate-200 text-slate-800 rounded-tl-sm shadow-sm"
                  )}
                >
                  {msg.role === "assistant" ? (
                    <div className="prose-chat">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                    </div>
                  ) : (
                    msg.content
                  )}
                </div>

                {/* A2UI: render interactive QuizCard when agent returns quiz data */}
                {msg.quizData && (
                  <QuizCard
                    quiz={msg.quizData}
                    studentId={sessionCtx.student_id}
                    topic={sessionCtx.current_topic || subject}
                    priorMastery={
                      sessionCtx.mastery_summary[sessionCtx.current_topic || subject] ?? 0
                    }
                    onResult={(result: QuizResult) => {
                      // Update mastery in session context after quiz scored
                      setSessionCtx((prev) => ({
                        ...prev,
                        mastery_summary: {
                          ...prev.mastery_summary,
                          [result.topic]: result.new_mastery,
                        },
                      }));
                    }}
                  />
                )}
              </div>

              {msg.role === "user" && (
                <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <User className="w-4 h-4 text-slate-500" />
                </div>
              )}
            </div>
          ))}

          {/* Loading indicator */}
          {loading && (
            <div className="flex gap-3 justify-start">
              <div className="w-8 h-8 rounded-full bg-brand-100 flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-4 h-4 text-brand-600" />
              </div>
              <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
                <div className="flex items-center gap-2 text-slate-400 text-sm">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Agents thinking...
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggested prompts (shown when only welcome message) */}
        {messages.length === 1 && (
          <div className="px-4 pb-3 flex flex-wrap gap-2">
            {suggestions.map((s) => (
              <button
                key={s}
                onClick={() => sendMessage(s)}
                className="text-xs bg-white border border-slate-200 text-slate-600 hover:border-brand-300 hover:text-brand-600 rounded-full px-3 py-1.5 transition-all"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Input area */}
        <div className="border-t border-slate-200 bg-white p-4">
          <div className="flex gap-2 max-w-4xl mx-auto">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Ask about ${SUBJECT_LABELS[subject]}...`}
              rows={1}
              className="flex-1 resize-none rounded-xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-300 focus:border-transparent bg-slate-50 placeholder:text-slate-400 max-h-32 overflow-y-auto"
              style={{ minHeight: "48px" }}
              disabled={loading}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || loading}
              className="w-12 h-12 rounded-xl bg-brand-600 text-white flex items-center justify-center hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all flex-shrink-0 shadow-sm"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          </div>
          <p className="text-center text-xs text-slate-400 mt-2">
            Every response passes through a Safety Agent · Enter to send
          </p>
        </div>
      </div>
    </div>
  );
}
