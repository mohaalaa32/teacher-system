"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

export interface EducationalContextItem {
  id: string;
  subject: string;
  grade: string;
  country: string;
  curriculumName: string;
  language: string;
  year: string;
  edition: string;
  uiLanguage: string;
  teacherName: string;
  schoolName: string;
  sectionName: string;
  planningDate: string;
  schoolDays: string[];
  holidays: string[];
  defaultPeriodMinutes: number;
  defaultPeriodsCount: number;
  selectedTools: string[];
  documentPreferences: Record<string, any>;
  activeTemplateId?: string;
  missingContextFields: string[];
  version: number;
}

interface AppContextValue {
  contexts: EducationalContextItem[];
  activeContext: EducationalContextItem | null;
  activeContextId: string;
  loadingContext: boolean;
  switchContext: (ctxId: string) => void;
  refreshContexts: () => Promise<void>;
  apiFetch: (path: string, options?: RequestInit) => Promise<any>;
  openNewContextModal: () => void;
}

const TeacherAppContext = createContext<AppContextValue | null>(null);

export function useTeacherApp() {
  const ctx = useContext(TeacherAppContext);
  if (!ctx) {
    throw new Error("useTeacherApp must be used inside AppShellProvider");
  }
  return ctx;
}

const NAV_ITEMS = [
  { href: "/", labelAr: "لوحة المعلم", labelEn: "Dashboard", icon: "⊞" },
  { href: "/curriculum", labelAr: "المنهج", labelEn: "Curriculum", icon: "📖" },
  { href: "/lessons", labelAr: "اختيار الدرس", labelEn: "Lessons", icon: "☰" },
  { href: "/tools", labelAr: "الوسائل وأدوات المدرس", labelEn: "Teacher Tools & Aids", icon: "📏" },
  { href: "/settings", labelAr: "إعداد الخطة", labelEn: "Plan & Context Setup", icon: "⚙" },
  { href: "/daily-plan", labelAr: "الخطة اليومية", labelEn: "Daily Plan", icon: "📝" },
  { href: "/weekly-plan", labelAr: "الخطة الأسبوعية", labelEn: "Weekly Plan", icon: "🗓" },
  { href: "/five-day-plan", labelAr: "خطة خمسة أيام", labelEn: "Five-Day Plan", icon: "📅" },
  { href: "/review", labelAr: "مراجعة الخطة", labelEn: "Final Plan Review", icon: "✓" },
  { href: "/reports", labelAr: "التقارير", labelEn: "Reports", icon: "📊" },
  { href: "/presentations", labelAr: "العروض التقديمية", labelEn: "Presentations & PPTX", icon: "🖥" },
  { href: "/export-package", labelAr: "تصدير الحزمة", labelEn: "Export Package", icon: "📦" },
];

export const WORKFLOW_STEPS = [
  { step: 1, label: "المنهج", href: "/curriculum" },
  { step: 2, label: "الدرس", href: "/lessons" },
  { step: 3, label: "الوسائل", href: "/tools" },
  { step: 4, label: "الإعداد", href: "/settings" },
  { step: 5, label: "المراجعة", href: "/review" },
  { step: 6, label: "التقارير", href: "/reports" },
  { step: 7, label: "العروض", href: "/presentations" },
  { step: 8, label: "التصدير", href: "/export-package" },
];

export function WorkflowStepper({ activeStep }: { activeStep: number }) {
  return (
    <nav className="stepper-bar" aria-label="خطوات العمل">
      {WORKFLOW_STEPS.map((st) => {
        const isDone = st.step < activeStep;
        const isCurrent = st.step === activeStep;
        return (
          <Link
            key={st.step}
            href={st.href}
            className={`stepper-item ${isDone ? "done" : ""} ${isCurrent ? "active" : ""}`}
          >
            <span className="step-circle">{isDone ? "✓" : st.step}</span>
            <span>{st.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

export function AppShellProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [contexts, setContexts] = useState<EducationalContextItem[]>([]);
  const [activeContextId, setActiveContextId] = useState<string>("ctx_math_iq_demo");
  const [loadingContext, setLoadingContext] = useState<boolean>(true);
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(false);
  const [showModal, setShowModal] = useState<boolean>(false);

  // New Context Form State
  const [newCtxForm, setNewCtxForm] = useState({
    subject: "",
    grade: "",
    country: "",
    curriculumName: "",
    language: "ar",
    year: "",
    edition: "",
    teacherName: "",
    schoolName: "",
    sectionName: "",
    defaultPeriodMinutes: 45,
  });

  const refreshContexts = useCallback(async () => {
    try {
      const res = await fetch("/api/contexts", { cache: "no-store" });
      if (res.ok) {
        const data = await res.json();
        const list: EducationalContextItem[] = data.items || [];
        setContexts(list);
        const savedId = typeof window !== "undefined" ? window.localStorage.getItem("agy_active_context_id") : null;
        if (savedId && list.some((c) => c.id === savedId)) {
          setActiveContextId(savedId);
        } else if (list.length > 0 && !list.some((c) => c.id === activeContextId)) {
          setActiveContextId(list[0].id);
        }
      }
    } catch (err) {
      console.error("Failed loading contexts:", err);
    } finally {
      setLoadingContext(false);
    }
  }, [activeContextId]);

  useEffect(() => {
    refreshContexts();
  }, [refreshContexts]);

  const activeContext = contexts.find((c) => c.id === activeContextId) || contexts[0] || null;

  useEffect(() => {
    if (activeContext && typeof document !== "undefined") {
      const lang = activeContext.language || "ar";
      const isRtl = lang.toLowerCase().startsWith("ar") || lang.toLowerCase().startsWith("ku") || lang.toLowerCase().startsWith("fa") || lang.toLowerCase().startsWith("he");
      document.documentElement.lang = lang;
      document.documentElement.dir = isRtl ? "rtl" : "ltr";
    }
  }, [activeContext]);

  const switchContext = useCallback((ctxId: string) => {
    setActiveContextId(ctxId);
    if (typeof window !== "undefined") {
      window.localStorage.setItem("agy_active_context_id", ctxId);
    }
  }, []);

  const apiFetch = useCallback(
    async (path: string, options: RequestInit = {}) => {
      const currentCtxId = activeContext?.id || activeContextId;
      const headers = new Headers(options.headers || {});
      headers.set("X-Active-Context-Id", currentCtxId);
      if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
      }
      const res = await fetch(path, {
        ...options,
        headers,
        cache: "no-store",
      });
      const contentType = res.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        const json = await res.json();
        if (!res.ok) {
          throw new Error(json.message || `خطأ في الطلب (${res.status})`);
        }
        return json;
      }
      if (!res.ok) {
        throw new Error(`فشل الاتصال بالخادم (${res.status})`);
      }
      return res;
    },
    [activeContext, activeContextId]
  );

  const handleCreateContext = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const created = await apiFetch("/api/contexts", {
        method: "POST",
        body: JSON.stringify(newCtxForm),
      });
      await refreshContexts();
      switchContext(created.id);
      setShowModal(false);
    } catch (err: any) {
      alert(err.message);
    }
  };

  const uiIsRtl = !activeContext || (activeContext.language || "ar").startsWith("ar");

  return (
    <TeacherAppContext.Provider
      value={{
        contexts,
        activeContext,
        activeContextId: activeContext?.id || activeContextId,
        loadingContext,
        switchContext,
        refreshContexts,
        apiFetch,
        openNewContextModal: () => setShowModal(true),
      }}
    >
      <div className="app-shell">
        {/* Sidebar (#154434) */}
        <aside className={`app-sidebar ${sidebarOpen ? "open" : ""}`} aria-label="القائمة الجانبية">
          <div className="brand-header">
            <div>
              <div className="brand-title">
                {activeContext?.subject ? `مُعلّم ${activeContext.subject}` : "مساعد المدرس"}
              </div>
              <div className="brand-subtitle">مساحة التخطيط لأي مادة ومنهج</div>
            </div>
            <div className="brand-icon-box" aria-hidden="true">
              📖
            </div>
          </div>

          <div className="context-pill-card">
            <div className="context-pill-grade">{activeContext?.grade || "صف غير محدد"}</div>
            <div className="context-pill-sub">
              {activeContext?.subject || "مادة غير محددة"} · {activeContext?.country || "بلد غير محدد"}
            </div>
            <div style={{ marginTop: "8px", display: "flex", gap: "6px" }}>
              <select
                aria-label="تبديل السياق التعليمي"
                value={activeContext?.id || ""}
                onChange={(e) => switchContext(e.target.value)}
                style={{
                  width: "100%",
                  background: "rgba(0,0,0,0.22)",
                  color: "#fff",
                  border: "1px solid rgba(255,255,255,0.2)",
                  borderRadius: "6px",
                  padding: "5px 8px",
                  fontSize: "0.78rem",
                }}
              >
                {contexts.map((c) => (
                  <option key={c.id} value={c.id} style={{ color: "#111" }}>
                    {c.subject || "بدون مادة"} — {c.grade || "بدون صف"} ({c.country || "—"})
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => setShowModal(true)}
                title="إضافة سياق تعليمي جديد"
                style={{
                  background: "#226650",
                  color: "#fff",
                  border: "1px solid rgba(255,255,255,0.25)",
                  borderRadius: "6px",
                  padding: "4px 9px",
                  cursor: "pointer",
                  fontWeight: 700,
                }}
              >
                +
              </button>
            </div>
          </div>

          <nav className="sidebar-nav">
            {NAV_ITEMS.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={`sidebar-link ${isActive ? "active" : ""}`}
                >
                  <span aria-hidden="true">{item.icon}</span>
                  <span>{uiIsRtl ? item.labelAr : item.labelEn}</span>
                </Link>
              );
            })}

            <div className="sidebar-section-label">إدارة المصادر</div>
            <Link
              href="/sources"
              onClick={() => setSidebarOpen(false)}
              className={`sidebar-link ${pathname === "/sources" ? "active" : ""}`}
            >
              <span aria-hidden="true">📤</span>
              <span>استيراد كتاب المنهج</span>
            </Link>
          </nav>

          <div className="sidebar-source-status">
            <div style={{ fontWeight: 700, color: "#fff", marginBottom: "2px" }}>المصدر قيد المراجعة</div>
            <div style={{ color: "var(--sidebar-muted)" }}>
              {activeContext?.edition && activeContext?.year
                ? `الطبعة: ${activeContext.edition} · السنة: ${activeContext.year}`
                : "السجل التجريبي غير موثّق؛ لا يُعدّ كتابًا معتمدًا."}
            </div>
          </div>
        </aside>

        {/* Main Panel */}
        <div className="app-main">
          <header className="top-bar">
            <div className="top-bar-context-info">
              <button
                type="button"
                className="mobile-menu-btn"
                onClick={() => setSidebarOpen(!sidebarOpen)}
                aria-label="فتح القائمة الجانبية"
              >
                ☰ القائمة
              </button>
              <span>
                {activeContext?.subject || "المادة غير محددة"} · {activeContext?.grade || "الصف غير محدد"} ·{" "}
                {activeContext?.country || "البلد غير محدد"}
              </span>
              {activeContext?.missingContextFields && activeContext.missingContextFields.length > 0 && (
                <span className="badge badge-warning" title="الحقول غير المعروفة تُترك فارغة مع تنبيه بدل تخمينها">
                  تنبيه سياق: ينقص ({activeContext.missingContextFields.join("، ")})
                </span>
              )}
            </div>

            <div className="top-bar-user">
              <div className="avatar-circle">أ ع</div>
              <span>{activeContext?.teacherName || "أحمد علي · معلم تجريبي"}</span>
            </div>
          </header>

          <main className="page-container">{children}</main>

          <footer className="app-footer">
            <span>للتخطيط التربوي · توثيق المصدر مطلوب قبل الاستخدام الرسمي</span>
            <span>متصل بخدمة Python FastAPI · عزل السياقات مفعّل ({activeContext?.id})</span>
          </footer>
        </div>
      </div>

      {/* Modal for Creating a Brand New Context */}
      {showModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="إنشاء سياق تعليمي جديد"
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
            padding: "16px",
          }}
        >
          <div className="card" style={{ maxWidth: "560px", width: "100%", maxHeight: "90vh", overflowY: "auto" }}>
            <h2 style={{ marginBottom: "8px", fontSize: "1.2rem" }}>إضافة سياق تعليمي جديد (أي مادة ومنهج وبلد)</h2>
            <p style={{ fontSize: "0.84rem", color: "var(--text-secondary)", marginBottom: "14px" }}>
              الحقول غير المعروفة يمكن تركها فارغة وستُعلّم بتنبيه واضح بدل تخمينها.
            </p>
            <form onSubmit={handleCreateContext}>
              <div className="equal-split-grid">
                <div className="form-group">
                  <label className="form-label">المادة (subject)</label>
                  <input
                    className="form-input"
                    placeholder="مثال: التاريخ، الفيزياء، اللغة العربية..."
                    value={newCtxForm.subject}
                    onChange={(e) => setNewCtxForm({ ...newCtxForm, subject: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">الصف / المرحلة (grade)</label>
                  <input
                    className="form-input"
                    placeholder="مثال: الثاني المتوسط / العاشر..."
                    value={newCtxForm.grade}
                    onChange={(e) => setNewCtxForm({ ...newCtxForm, grade: e.target.value })}
                    required
                  />
                </div>
              </div>
              <div className="equal-split-grid">
                <div className="form-group">
                  <label className="form-label">البلد (country)</label>
                  <input
                    className="form-input"
                    placeholder="مثال: العراق، الأردن، مصر، السعودية..."
                    value={newCtxForm.country}
                    onChange={(e) => setNewCtxForm({ ...newCtxForm, country: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">اسم المنهج (curriculumName)</label>
                  <input
                    className="form-input"
                    placeholder="مثال: المنهج الوطني المطور"
                    value={newCtxForm.curriculumName}
                    onChange={(e) => setNewCtxForm({ ...newCtxForm, curriculumName: e.target.value })}
                  />
                </div>
              </div>
              <div className="stats-grid-3">
                <div className="form-group">
                  <label className="form-label">لغة السياق (language)</label>
                  <select
                    className="form-select"
                    value={newCtxForm.language}
                    onChange={(e) => setNewCtxForm({ ...newCtxForm, language: e.target.value })}
                  >
                    <option value="ar">العربية (RTL)</option>
                    <option value="en">English (LTR)</option>
                    <option value="ku">Kurdî (RTL)</option>
                    <option value="fr">Français (LTR)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">السنة (year - اختياري)</label>
                  <input
                    className="form-input"
                    placeholder="تُترك فارغة إن لم تُعرف"
                    value={newCtxForm.year}
                    onChange={(e) => setNewCtxForm({ ...newCtxForm, year: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">الطبعة (edition - اختياري)</label>
                  <input
                    className="form-input"
                    placeholder="تُترك فارغة إن لم تُعرف"
                    value={newCtxForm.edition}
                    onChange={(e) => setNewCtxForm({ ...newCtxForm, edition: e.target.value })}
                  />
                </div>
              </div>
              <div className="equal-split-grid">
                <div className="form-group">
                  <label className="form-label">اسم المدرس</label>
                  <input
                    className="form-input"
                    value={newCtxForm.teacherName}
                    onChange={(e) => setNewCtxForm({ ...newCtxForm, teacherName: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">المدرسة والشعبة</label>
                  <input
                    className="form-input"
                    value={newCtxForm.schoolName}
                    onChange={(e) => setNewCtxForm({ ...newCtxForm, schoolName: e.target.value })}
                  />
                </div>
              </div>
              <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end", marginTop: "12px" }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  إلغاء
                </button>
                <button type="submit" className="btn btn-primary">
                  حفظ وتفعيل السياق
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </TeacherAppContext.Provider>
  );
}

