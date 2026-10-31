"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useTeacherApp, WorkflowStepper } from "../../components/AppShell";

export default function FiveDayPlanPage() {
  const { activeContext, activeContextId, apiFetch } = useTeacherApp();
  const [plan, setPlan] = useState<any>(null);
  const [days, setDays] = useState<any[]>([]);
  const [lessons, setLessons] = useState<any[]>([]);
  const [feedback, setFeedback] = useState<string>("");

  const loadFiveDayPlan = async () => {
    try {
      const [pRes, lRes] = await Promise.all([
        apiFetch(`/api/plans?contextId=${encodeURIComponent(activeContextId)}&planType=five_day`),
        apiFetch(`/api/lessons?contextId=${encodeURIComponent(activeContextId)}`),
      ]);
      setLessons(lRes.items || []);
      let found = pRes.items?.[0];
      if (!found) {
        const defaultDays = (activeContext?.schoolDays || ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس"])
          .slice(0, 5)
          .map((dName, i) => ({
            dayNumber: i + 1,
            dayName: dName,
            isHoliday: false,
            lessonTitle: i === 0 ? lRes.items?.[0]?.title || "درس تجريبي أ" : "",
            objectives: i === 0 ? "تحقيق أهداف اليوم الأول" : "",
            activities: "سبورة وأقلام ملوّنة وبطاقات",
            assessment: i === 0 ? "ملاحظة أداء المتعلمين" : "",
            minutes: activeContext?.defaultPeriodMinutes || 45,
          }));
        found = await apiFetch("/api/plans", {
          method: "POST",
          body: JSON.stringify({
            contextId: activeContextId,
            title: `خطة خمسة أيام — ${activeContext?.subject || "المادة"}`,
            planType: "five_day",
            periodMinutes: activeContext?.defaultPeriodMinutes || 45,
            periodsCount: 1,
            objectives: ["توزيع حصص مرن لخمسة أيام تدريس متميزة."],
            formativeAssessment: "متابعة التقويم اليومي لخمسة أيام تدريس.",
            scheduleDays: defaultDays,
          }),
        });
      }
      setPlan(found);
      setDays(found.scheduleDays || []);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (activeContextId) loadFiveDayPlan();
  }, [activeContextId]);

  const scheduledDaysCount = days.filter((d) => String(d.lessonTitle || "").trim() !== "").length;
  const readyForReviewCount = days.filter(
    (d) => String(d.lessonTitle || "").trim() !== "" && String(d.assessment || "").trim() !== ""
  ).length;
  const totalMinutes = days.reduce((acc, d) => acc + (Number(d.minutes) || 45), 0);

  const handleSaveFiveDayPlan = async () => {
    if (!plan) return;
    try {
      const updated = await apiFetch(`/api/plans/${plan.id}`, {
        method: "PUT",
        body: JSON.stringify({
          ...plan,
          scheduleDays: days,
          expectedVersion: plan.version,
        }),
      });
      setPlan(updated);
      setDays(updated.scheduleDays || []);
      setFeedback(`تم حفظ خطة الخمسة أيام (الإصدار v${updated.version}) بنجاح.`);
    } catch (err: any) {
      setFeedback(err.message);
    }
  };

  return (
    <div>
      <div className="breadcrumb-line">
        مُعلّم {activeContext?.subject || "المادة"} / مساحة المعلم / خطة خمسة أيام
      </div>
      <h1 className="page-title">خطة خمسة أيام</h1>
      <p className="page-subtitle">
        توزيع حصص مرن لخمسة أيام تدريس متميزة بحسب جدول المعلم، دون افتراض تسلسل رسمي للدروس أو تقويم غربي ثابت.
      </p>

      <div className="info-banner">
        <span>
          ⓘ لكل يوم من الأيام الخمسة اسم يوم قابل للتعديل بحسب إعداد الدوام، ودرس وأهداف وأنشطة وتقويم وزمن مستقل.
        </span>
      </div>

      <WorkflowStepper activeStep={4} />

      {/* Switcher between Five-Day & Weekly matching `خطة خمسة أيام.png` */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          backgroundColor: "#eef2ef",
          padding: "5px",
          borderRadius: "10px",
          marginBottom: "16px",
          border: "1px solid var(--border-color)",
        }}
      >
        <div
          style={{
            padding: "10px",
            borderRadius: "8px",
            backgroundColor: "#ffffff",
            color: "var(--primary-green)",
            fontWeight: 800,
            textAlign: "center",
          }}
        >
          خمسة أيام
        </div>
        <Link
          href="/weekly-plan"
          style={{
            padding: "10px",
            borderRadius: "8px",
            color: "var(--text-secondary)",
            fontWeight: 600,
            textAlign: "center",
            textDecoration: "none",
          }}
        >
          أسبوعية (تشمل أيام الدوام والعطل)
        </Link>
      </div>

      <div className="warning-banner">
        <span>
          ⚠ سجل منهج تجريبي · تجريبي — غير موثّق. الأيام ترتيب تخطيطي تجريبي؛ ليست توزيعًا رسميًا للمنهج.
        </span>
      </div>

      {feedback && (
        <div className="info-banner" style={{ borderColor: "var(--primary-green)", color: "var(--primary-green)" }}>
          <span>✓ {feedback}</span>
        </div>
      )}

      {/* 3 Summary Stat Cards matching `خطة خمسة أيام.png` */}
      <div className="stats-grid-3">
        <div className="stat-card">
          <div className="stat-label">حصص محدّد لها درس</div>
          <div className="stat-number">
            {scheduledDaysCount} من {days.length || 5}
          </div>
          <div className="stat-sub">جميع الدروس تجريبية — غير موثّقة</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">حصص جاهزة للمراجعة</div>
          <div className="stat-number">
            {readyForReviewCount} من {days.length || 5}
          </div>
          <div className="stat-sub">توثيق المصدر ما زال معلّقًا</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">إجمالي الزمن المحجوز</div>
          <div className="stat-number">{totalMinutes} دقيقة</div>
          <div className="stat-sub">
            {days.length || 5} حصص × {activeContext?.defaultPeriodMinutes || 45} دقيقة
          </div>
        </div>
      </div>

      {/* 5-Day Editable Schedule Table matching `خطة خمسة أيام.png` */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px", flexWrap: "wrap", gap: "8px" }}>
          <div>
            <h3 style={{ fontSize: "1.2rem", fontWeight: 800 }}>جدول الحصص (خمسة أيام تدريس)</h3>
            <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
              {activeContext?.sectionName || "الشعبة أ"} · {activeContext?.teacherName || "معلم"} · أسبوع يحدّده المعلم
            </p>
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ fontSize: "0.8rem", padding: "6px 12px" }}
            onClick={() => {
              const filled = days.map((d, idx) => ({
                ...d,
                lessonTitle: d.lessonTitle || lessons[idx % Math.max(1, lessons.length)]?.title || `درس اليوم ${idx + 1}`,
                activities: d.activities || "سبورة وأقلام ملوّنة وبطاقات",
                assessment: d.assessment || "سؤال تقويمي وملاحظة أداء مرتبطة بالهدف",
              }));
              setDays(filled);
              setFeedback("تم استكمال جدولة وتقويم الأيام الخمسة؛ اضغط حفظ المسودة لتثبيتها.");
            }}
          >
            استكمال جدولة الأيام الخمسة تلقائيًا للمراجعة
          </button>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {days.map((d, idx) => {
            const hasLesson = String(d.lessonTitle || "").trim() !== "";
            const hasAssessment = String(d.assessment || "").trim() !== "";
            return (
              <div
                key={idx}
                style={{
                  padding: "16px",
                  borderRadius: "12px",
                  border: "1px solid var(--border-color)",
                  backgroundColor: "#fbfcfb",
                  display: "grid",
                  gridTemplateColumns: "110px 1.2fr 1.2fr 1.2fr 130px",
                  gap: "12px",
                  alignItems: "center",
                }}
              >
                <div>
                  <input
                    aria-label={`اسم اليوم ${idx + 1}`}
                    className="form-input"
                    style={{ fontWeight: 800, padding: "5px 8px", marginBottom: "4px" }}
                    value={d.dayName || ""}
                    onChange={(e) => {
                      const next = [...days];
                      next[idx] = { ...next[idx], dayName: e.target.value };
                      setDays(next);
                    }}
                  />
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{d.minutes || 45} دقيقة</div>
                </div>

                <div>
                  <div style={{ fontSize: "0.74rem", color: "var(--text-muted)", marginBottom: "3px" }}>الدرس</div>
                  <input
                    aria-label={`درس اليوم ${idx + 1}`}
                    className="form-input"
                    placeholder="لم يُحدّد درس"
                    style={{ fontWeight: 700, padding: "6px 8px", marginBottom: "4px" }}
                    value={d.lessonTitle || ""}
                    onChange={(e) => {
                      const next = [...days];
                      next[idx] = { ...next[idx], lessonTitle: e.target.value };
                      setDays(next);
                    }}
                  />
                  <span className="badge badge-warning">تجريبي — غير موثّق</span>
                </div>

                <div>
                  <div style={{ fontSize: "0.74rem", color: "var(--text-muted)", marginBottom: "3px" }}>التحضير والأنشطة</div>
                  <input
                    aria-label={`أنشطة اليوم ${idx + 1}`}
                    className="form-input"
                    style={{ padding: "6px 8px" }}
                    value={d.activities || ""}
                    onChange={(e) => {
                      const next = [...days];
                      next[idx] = { ...next[idx], activities: e.target.value };
                      setDays(next);
                    }}
                  />
                </div>

                <div>
                  <div style={{ fontSize: "0.74rem", color: "var(--text-muted)", marginBottom: "3px" }}>التقويم التكويني</div>
                  <input
                    aria-label={`تقويم اليوم ${idx + 1}`}
                    className="form-input"
                    placeholder="لم تُحدّد طريقة التقويم"
                    style={{ padding: "6px 8px" }}
                    value={d.assessment || ""}
                    onChange={(e) => {
                      const next = [...days];
                      next[idx] = { ...next[idx], assessment: e.target.value };
                      setDays(next);
                    }}
                  />
                </div>

                <div style={{ textAlign: "end" }}>
                  <span
                    className={`badge ${
                      hasLesson && hasAssessment
                        ? "badge-success"
                        : hasLesson && !hasAssessment
                        ? "badge-blocker"
                        : "badge-neutral"
                    }`}
                    style={{ marginBottom: "6px" }}
                  >
                    {hasLesson && hasAssessment
                      ? "جاهز للمراجعة"
                      : hasLesson && !hasAssessment
                      ? "تقويم ناقص"
                      : "غير مجدول"}
                  </span>
                  <div>
                    <Link
                      href="/daily-plan"
                      style={{ fontSize: "0.78rem", color: "var(--primary-green)", fontWeight: 700, textDecoration: "none" }}
                    >
                      {hasLesson && hasAssessment ? "تحرير الحصة ←" : "استكمال الحصة ←"}
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {readyForReviewCount < days.length && (
        <div className="blocker-banner">
          <span>
            ⛔ قبل اكتمال الخطة: أضف تقويم الأيام الناقصة، وحدّد دروس الأيام غير المجدولة أو استكملها بالزر أعلاه.
          </span>
        </div>
      )}

      <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
        <Link href="/review" className="btn btn-primary" onClick={handleSaveFiveDayPlan}>
          ← مراجعة خطة الأيام
        </Link>
        <button type="button" className="btn btn-secondary" onClick={handleSaveFiveDayPlan}>
          حفظ مسودة · قاعدة البيانات
        </button>
      </div>
    </div>
  );
}
