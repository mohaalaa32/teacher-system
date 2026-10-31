"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTeacherApp, WorkflowStepper } from "../../components/AppShell";

export default function PlanSettingsPage() {
  const router = useRouter();
  const { activeContext, activeContextId, apiFetch, refreshContexts, openNewContextModal } = useTeacherApp();
  const [planningMode, setPlanningMode] = useState<"daily" | "weekly" | "five_day">("daily");
  const [templates, setTemplates] = useState<any[]>([]);
  const [feedback, setFeedback] = useState<string>("");

  // 7 Explicit Context Fields + Teacher & Schedule Settings
  const [subject, setSubject] = useState<string>("");
  const [grade, setGrade] = useState<string>("");
  const [country, setCountry] = useState<string>("");
  const [curriculumName, setCurriculumName] = useState<string>("");
  const [language, setLanguage] = useState<string>("ar");
  const [year, setYear] = useState<string>("");
  const [edition, setEdition] = useState<string>("");

  const [teacherName, setTeacherName] = useState<string>("");
  const [schoolName, setSchoolName] = useState<string>("");
  const [sectionName, setSectionName] = useState<string>("");
  const [planningDate, setPlanningDate] = useState<string>("");
  const [defaultPeriodMinutes, setDefaultPeriodMinutes] = useState<number>(45);
  const [defaultPeriodsCount, setDefaultPeriodsCount] = useState<number>(1);
  const [schoolDaysText, setSchoolDaysText] = useState<string>("الأحد، الاثنين، الثلاثاء، الأربعاء، الخميس");
  const [holidaysText, setHolidaysText] = useState<string>("الجمعة، السبت");
  const [objectivesText, setObjectivesText] = useState<string>(
    "أن يشرح الطالب طريقة تفكيره في نشاط يحدّده المعلم.\nأن يقارن بين استراتيجيتين في مهمة يختارها المعلم."
  );
  const [planningNote, setPlanningNote] = useState<string>("");
  const [pedagogicalAidEnabled, setPedagogicalAidEnabled] = useState<boolean>(true);

  useEffect(() => {
    if (activeContext) {
      setSubject(activeContext.subject || "");
      setGrade(activeContext.grade || "");
      setCountry(activeContext.country || "");
      setCurriculumName(activeContext.curriculumName || "");
      setLanguage(activeContext.language || "ar");
      setYear(activeContext.year || "");
      setEdition(activeContext.edition || "");
      setTeacherName(activeContext.teacherName || "");
      setSchoolName(activeContext.schoolName || "");
      setSectionName(activeContext.sectionName || "");
      setPlanningDate(activeContext.planningDate || "2026-10-11");
      setDefaultPeriodMinutes(activeContext.defaultPeriodMinutes || 45);
      setDefaultPeriodsCount(activeContext.defaultPeriodsCount || 1);
      setSchoolDaysText((activeContext.schoolDays || []).join("، "));
      setHolidaysText((activeContext.holidays || []).join("، "));
    }
  }, [activeContext]);

  useEffect(() => {
    async function loadTpls() {
      if (!activeContextId) return;
      try {
        const res = await apiFetch(`/api/templates?contextId=${encodeURIComponent(activeContextId)}`);
        setTemplates(res.items || []);
      } catch (e) {
        console.error(e);
      }
    }
    loadTpls();
  }, [activeContextId, apiFetch]);

  const handleSaveSettings = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!activeContext) return;
    try {
      const schoolDays = schoolDaysText
        .split(/[،,]/)
        .map((s) => s.trim())
        .filter(Boolean);
      const holidays = holidaysText
        .split(/[،,]/)
        .map((s) => s.trim())
        .filter(Boolean);

      await apiFetch(`/api/contexts/${activeContextId}`, {
        method: "PUT",
        body: JSON.stringify({
          subject,
          grade,
          country,
          curriculumName,
          language,
          year,
          edition,
          uiLanguage: language,
          teacherName,
          schoolName,
          sectionName,
          planningDate,
          schoolDays,
          holidays,
          defaultPeriodMinutes: Number(defaultPeriodMinutes),
          defaultPeriodsCount: Number(defaultPeriodsCount),
          selectedTools: activeContext.selectedTools || [],
          documentPreferences: activeContext.documentPreferences || {},
          expectedVersion: activeContext.version,
        }),
      });
      await refreshContexts();
      setFeedback("تم حفظ السياق التعليمي (بجميع حقوله السبعة) وإعدادات المعلم. تُطبّق الإعدادات على الخطط الجديدة دون تغيير الإصدارات السابقة بصمت.");
    } catch (err: any) {
      setFeedback(`خطأ: ${err.message}`);
    }
  };

  const handleOpenEditor = async () => {
    await handleSaveSettings();
    if (planningMode === "weekly") {
      router.push("/weekly-plan");
    } else if (planningMode === "five_day") {
      router.push("/five-day-plan");
    } else {
      router.push("/daily-plan");
    }
  };

  return (
    <div>
      <div className="breadcrumb-line">
        مُعلّم {activeContext?.subject || "المادة"} / مساحة المعلم / إعداد الخطة
      </div>
      <h1 className="page-title">إعداد الخطة والسياق التعليمي</h1>
      <p className="page-subtitle">
        اضبط السياق التعليمي (بسبعة حقول صريحة) وزمن الحصة وأهدافها، واختر نمط التخطيط المناسب قبل فتح المحرّر.
      </p>

      <div className="info-banner">
        <span>
          ⓘ تعديل السياق أو إعدادات الدوام هنا يُحفظ في قاعدة البيانات ويُطبّق على الخطط الجديدة دون إعادة تسمية أو تحريف الإصدارات المعتمدة سابقًا.
        </span>
        <button type="button" className="btn btn-secondary" onClick={openNewContextModal}>
          + سياق جديد مستقل
        </button>
      </div>

      <WorkflowStepper activeStep={4} />

      {/* Segmented Mode Switcher matching `إعداد الخطة.png` */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          backgroundColor: "#eef2ef",
          padding: "5px",
          borderRadius: "10px",
          marginBottom: "18px",
          border: "1px solid var(--border-color)",
        }}
      >
        {[
          { id: "daily", label: "يومية" },
          { id: "weekly", label: "أسبوعية" },
          { id: "five_day", label: "خمسة أيام" },
        ].map((tab) => {
          const active = planningMode === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setPlanningMode(tab.id as any)}
              style={{
                padding: "10px",
                borderRadius: "8px",
                border: "none",
                backgroundColor: active ? "#ffffff" : "transparent",
                color: active ? "var(--primary-green)" : "var(--text-secondary)",
                fontWeight: active ? 800 : 600,
                cursor: "pointer",
                fontSize: "0.9rem",
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {feedback && (
        <div className="info-banner" style={{ borderColor: "var(--primary-green)", color: "var(--primary-green)" }}>
          <span>✓ {feedback}</span>
        </div>
      )}

      {/* Main Split matching `إعداد الخطة.png`: Daily Session & Context Details (2/3) & Context Sidebar Cards (1/3) */}
      <div className="main-split-grid">
        <form className="card" onSubmit={handleSaveSettings}>
          <h3 style={{ fontSize: "1.15rem", fontWeight: 800, marginBottom: "2px" }}>
            تفاصيل الحصة والسياق التعليمي المحفوظ
          </h3>
          <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: "14px" }}>
            الحقول السبعة الصريحة: {"{subject, grade, country, curriculumName, language, year, edition}"} — الحقول غير المعروفة تُترك فارغة بدل تخمينها
          </p>

          {/* Row 1: Teacher, Grade, Section matching `إعداد الخطة.png` */}
          <div className="stats-grid-3">
            <div className="form-group">
              <label className="form-label">اسم المعلم</label>
              <input
                className="form-input"
                value={teacherName}
                onChange={(e) => setTeacherName(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">الصف / المرحلة (grade)</label>
              <input
                className="form-input"
                value={grade}
                onChange={(e) => setGrade(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">الشعبة والمدرسة</label>
              <input
                className="form-input"
                value={sectionName}
                onChange={(e) => setSectionName(e.target.value)}
              />
            </div>
          </div>

          {/* Row 2: Planning Date, Period Duration, Periods Count */}
          <div className="stats-grid-3">
            <div className="form-group">
              <label className="form-label">تاريخ التخطيط</label>
              <input
                type="date"
                className="form-input"
                value={planningDate}
                onChange={(e) => setPlanningDate(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">مدة الحصة الواحدة (دقيقة)</label>
              <select
                className="form-select"
                value={defaultPeriodMinutes}
                onChange={(e) => setDefaultPeriodMinutes(Number(e.target.value))}
              >
                <option value={45}>45 دقيقة (افتراضي)</option>
                <option value={40}>40 دقيقة</option>
                <option value={50}>50 دقيقة</option>
                <option value={60}>60 دقيقة</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">عدد الحصص (حصة أو حصتان)</label>
              <select
                className="form-select"
                value={defaultPeriodsCount}
                onChange={(e) => setDefaultPeriodsCount(Number(e.target.value))}
              >
                <option value={1}>حصة واحدة ({defaultPeriodMinutes} دقيقة)</option>
                <option value={2}>حصتان ({defaultPeriodMinutes * 2} دقيقة)</option>
              </select>
            </div>
          </div>

          {/* Row 3: The remaining Explicit Context Fields */}
          <div className="stats-grid-3">
            <div className="form-group">
              <label className="form-label">المادة (subject)</label>
              <input
                className="form-input"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">البلد (country)</label>
              <input
                className="form-input"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">لغة السياق (language)</label>
              <select
                className="form-select"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
              >
                <option value="ar">العربية (RTL)</option>
                <option value="en">English (LTR)</option>
                <option value="ku">Kurdî (RTL)</option>
                <option value="fr">Français (LTR)</option>
              </select>
            </div>
          </div>

          <div className="stats-grid-3">
            <div className="form-group">
              <label className="form-label">اسم المنهج (curriculumName)</label>
              <input
                className="form-input"
                value={curriculumName}
                onChange={(e) => setCurriculumName(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">السنة (year - فارغ إن لم يُعرف)</label>
              <input
                className="form-input"
                placeholder="غير مدخلة"
                value={year}
                onChange={(e) => setYear(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">الطبعة (edition - فارغ إن لم تُعرف)</label>
              <input
                className="form-input"
                placeholder="غير مدخلة"
                value={edition}
                onChange={(e) => setEdition(e.target.value)}
              />
            </div>
          </div>

          <div className="equal-split-grid">
            <div className="form-group">
              <label className="form-label">أيام الدوام الأسبوعية الفعلية</label>
              <input
                className="form-input"
                value={schoolDaysText}
                onChange={(e) => setSchoolDaysText(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">أيام العطل الأسبوعية</label>
              <input
                className="form-input"
                value={holidaysText}
                onChange={(e) => setHolidaysText(e.target.value)}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">الأهداف التعليمية · صياغة قابلة للتحرير</label>
            <textarea
              className="form-textarea"
              value={objectivesText}
              onChange={(e) => setObjectivesText(e.target.value)}
            />
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "4px" }}>
              راجع ارتباط الأهداف بمحتوى الدرس بعد توثيق المصدر.
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">ملاحظة تخطيطية</label>
            <textarea
              className="form-textarea"
              placeholder="أدخل احتياجات الصف والتعديلات المناسبة..."
              value={planningNote}
              onChange={(e) => setPlanningNote(e.target.value)}
            />
          </div>

          <div
            style={{
              padding: "12px 14px",
              borderRadius: "10px",
              border: "1px solid var(--border-subtle)",
              backgroundColor: "#f9fbf9",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "14px",
            }}
          >
            <div>
              <div style={{ fontWeight: 700, fontSize: "0.9rem" }}>المراجعة قبل إعداد المخرجات</div>
              <div style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                فحص اكتمال الحقول والزمن والأهداف؛ توثيق المصدر مسار منفصل ({templates.length} قوالب مراحل محفوظة)
              </div>
            </div>
            <span className="badge badge-success">مفعّلة</span>
          </div>

          <button type="submit" className="btn btn-secondary">
            حفظ إعدادات السياق والخطة
          </button>
        </form>

        <div>
          <div className="card">
            <h3 style={{ fontSize: "1.1rem", fontWeight: 800, marginBottom: "6px" }}>سياق الخطة</h3>
            <div style={{ fontWeight: 800, fontSize: "1rem", marginBottom: "8px" }}>درس تجريبي أ</div>
            <span className="badge badge-warning" style={{ marginBottom: "10px" }}>
              تجريبي — غير موثّق
            </span>
            <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginBottom: "12px" }}>
              سجل منهج تجريبي
              <br />
              {subject || "—"} · {grade || "—"} · {country || "—"}
            </p>
            <div
              style={{
                padding: "10px 12px",
                borderRadius: "8px",
                backgroundColor: "var(--primary-tint-bg)",
                marginBottom: "12px",
                fontSize: "0.82rem",
              }}
            >
              <strong>{activeContext?.selectedTools?.length || 4} وسائل مختارة:</strong>
              <br />
              {(activeContext?.selectedTools || []).join("، ")}
            </div>
            <Link href="/tools" className="btn btn-secondary" style={{ width: "100%" }}>
              تعديل الوسائل
            </Link>
          </div>

          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <h3 style={{ fontSize: "1.05rem", fontWeight: 800 }}>
                مساعدة تربوية لمادة {subject || "المادة"}
              </h3>
              <input
                type="checkbox"
                checked={pedagogicalAidEnabled}
                onChange={(e) => setPedagogicalAidEnabled(e.target.checked)}
                aria-label="تفعيل المقترحات التربوية"
              />
            </div>
            <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: "10px" }}>
              تفسير الاستدلال، مناقشة التصورات الشائعة، التمثيل البصري، ومقارنة الاستراتيجيات بما يلائم المادة.
            </p>
            <div className="info-banner" style={{ marginBottom: 0 }}>
              <span>ⓘ المقترحات للمراجعة والتحرير؛ لا تُضاف كمحتوى رسمي.</span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Mode Preview Cards matching `إعداد الخطة.png` */}
      <div className="equal-split-grid">
        <div className="card">
          <h3 style={{ fontSize: "1.05rem", fontWeight: 800, marginBottom: "4px" }}>معاينة النمط الأسبوعي</h3>
          <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: "8px" }}>
            نظرة إجمالية إلى الحصص بحسب جدول المعلم وأيام الدوام ({schoolDaysText})
          </p>
          <p style={{ fontSize: "0.82rem", color: "var(--text-main)" }}>
            اجمع حصص الأسبوع، وحدّد لكل حصة درسًا وزمنًا وطريقة تقويم. لا يفترض النموذج ترتيبًا رسميًا للدروس.
          </p>
        </div>

        <div className="card">
          <h3 style={{ fontSize: "1.05rem", fontWeight: 800, marginBottom: "4px" }}>معاينة نمط خمسة أيام</h3>
          <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: "8px" }}>
            توزيع قابل للتعديل، لا تسلسل رسمي للمنهج
          </p>
          <p style={{ fontSize: "0.82rem", color: "var(--text-main)" }}>
            الأحد: درس تجريبي أ · الاثنين: درس تجريبي ب · الثلاثاء: درس تجريبي ج · الأربعاء والخميس: حصتان قابلتان للجدولة.
          </p>
        </div>
      </div>

      <div style={{ display: "flex", gap: "10px" }}>
        <button type="button" className="btn btn-primary" onClick={handleOpenEditor}>
          ← فتح محرّر الخطة ({planningMode === "daily" ? "اليومية" : planningMode === "weekly" ? "الأسبوعية" : "خمسة أيام"})
        </button>
        <Link href="/tools" className="btn btn-secondary">
          العودة إلى الوسائل
        </Link>
      </div>
    </div>
  );
}

