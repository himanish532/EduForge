"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import ChatInterface from "@/components/ChatInterface";

function TutorPageInner() {
  const params = useSearchParams();
  const subject = params.get("subject") || "general";
  const grade = parseInt(params.get("grade") || "8", 10);

  return <ChatInterface subject={subject} gradeLevel={grade} />;
}

export default function TutorPage() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center text-slate-400">Loading...</div>}>
      <TutorPageInner />
    </Suspense>
  );
}
