import "./globals.css";
import React from "react";
import { AppShellProvider } from "../components/AppShell";

export const metadata = {
  title: "مساعد المدرس — تخطيط الدروس والمناهج لأي مادة وسياق",
  description: "أداة عمل للمدرس لإعداد الدروس والخطط اليومية والأسبوعية وخطة خمسة أيام ومراجعتها وتصدير DOCX وPDF وPPTX.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl">
      <body>
        <AppShellProvider>{children}</AppShellProvider>
      </body>
    </html>
  );
}

