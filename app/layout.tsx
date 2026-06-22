import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "EduForge — AI Tutoring Network",
  description:
    "A world-class AI tutor for every student, everywhere. Powered by Google Gemini and multi-agent AI.",
  openGraph: {
    title: "EduForge — AI Tutoring Network",
    description: "Personalized AI tutoring powered by multi-agent AI.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
