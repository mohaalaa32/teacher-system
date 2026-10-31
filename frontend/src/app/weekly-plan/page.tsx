"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useTeacherApp, WorkflowStepper } from "../../components/AppShell";

export default function WeeklyPlanPage() {
  const { activeContext, activeContextId, apiFetch } = useTeacherApp();
  const [plan, setPlan] = useState<any>(null);
  const [days, setDays] = useState<any[]>([]);
  const [dailyPlans, setDailyPlans] = useState<any[]>([]);
  const [feedback, setFeedback] = useState<string>("");

  const loadWeekly = async () => {
    try {
      const [wRes, dRes] = await Promise.all([
        apiFetch(`/api/plans?contextId=${encodeURIComponent(activeContextId)}&planType=weekly`),
        apiFetch(`/api/plans?contextId=${encodeURIComponent(activeContextId)}&planType=daily`),
      ]);
      setDailyPlans(dRes.items || []);
      let found = wRes.items?.[0];
      if (!found) {
        const sDays = activeContext?.schoolDays || ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس"];
        const hDays = activeContext?.holidays || ["الجمعة", "السبت"];
        const builtDays = [
          ...sDays.map((dName, idx) => ({
            dayName: dName,
            isHoliday: false,
            lessonTitle: `حصة ${dName} — ${activeContext?.subject}`,
            linkedDailyPlanId: dRes.items?.[idx]?.id || "",
            activities: "التهيئة والتدريس والتدريب",
            assessment: "تقويم تكويني يومي",
            minutes: activeContext?.defaultPeriodMinutes || 45,
          })),
          ...hDays.map((hName) => ({
            dayName: hName,
            isHoliday: true,
            lessonTitle: "عطلة رسمية",
            linkedDailyPlanId: "",
            activities: "—",
            assessment: "—",
            minutes: 0,
          })),
        ];
        found = await apiFetch("/api/plans", {
          method: "POST",
          body: JSON.stringify({
            contextId: activeContextId,
            title: `الخطة الأسبوعية — ${activeContext?.subject || "المادة"}`,
            planType: "weekly",
            periodMinutes: activeContext?.defaultPeriodMinutes || 45,
            periodsCount: 1,
            objectives: ["توزيع دروس الأسبوع على أيام الدوام الفعلية مع مراعاة العطل."],
            formativeAssessment: "بطاقات خروج يومية وملاحظة أداء الطلاب.",
            scheduleDays: builtDays,
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
    if (activeContextId) loadWeekly();
  }, [activeContextId]);

  const activeSchoolDays = days.filter((d) => !d.isHoliday);
  const holidaysCount = days.filter((d) => d.isHoliday).length;
  const totalWeeklyMinutes = activeSchoolDays.reduce((acc, d) => acc + (Number(d.minutes) || 0), 0);

  const moveDayRow = (idx: number, dir: -1 | 1) => {
    const target = idx + dir;
    if (target < 0 || target >= days.length) return;
    const next = [...days];
    const tmp = next[idx];
    next[idx] = next[target];
    next[target] = tmp;
    setDays(next);
  };

  const handleSaveWeekly = async () => {
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
      setFeedback(`تم حفظ الخطة الأسبوعية (الإصدار v${updated.version}) وحساب مجموع الزمن (${totalWeeklyMinutes} دقيقة).`);
    } catch (err: any) {
      setFeedback(err.message);
    }
  };

  return (
    <div>
      <div className="breadcrumb-line">
        مُعلّم {activeContext?.subject || "المادة"} / مساحة المعلم / الخطة الأسبوعية
      </div>
      <h1 className="page-title">الخطة الأسبوعية</h1>
      <p className="page-subtitle">
        توزيع الدروس والحصص والعطل على أيام الأسبوع الفعلية بحسب إعداد السياق، مع تعديل ونقل وربط الخطط اليومية وحساب مجموع الوقت.
      </p>

      <div className="info-banner">
        <span>
          ⓘ أيام الدوام والعطل مستمدة من إعداد السياق ({(activeContext?.schoolDays || []).join("، ")})؛ يمكنك تبديل أي يوم إلى عطلة أو نقل الحصة بين الأيام.
        </span>
      </div>

      <WorkflowStepper activeStep={4} />

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
        <Link
          href="/five-day-plan"
          style={{
            padding: "10px",
            borderRadius: "8px",
            color: "var(--text-secondary)",
            fontWeight: 600,
            textAlign: "center",
            textDecoration: "none",
          }}
        >
          خمسة أيام تدريس
        </Link>
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
          أسبوعية (الدوام الفعلي والعطل)
        </div>
      </div>

      {feedback && (
        <div className="info-banner" style={{ borderColor: "var(--primary-green)", color: "var(--primary-green)" }}>
          <span>✓ {feedback}</span>
        </div>
      )}

      <div className="stats-grid-3">
        <div className="stat-card">
          <div className="stat-label">أيام الدوام الفعلية</div>
          <div className="stat-number">{activeSchoolDays.length} أيام</div>
          <div className="stat-sub">مقابل {holidaysCount} أيام عطلة</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">خطط يومية مرتبطة</div>
          <div className="stat-number">
            {days.filter((d) => d.linkedDailyPlanId).length} خطط
          </div>
          <div className="stat-sub">ربط مباشر بالخطط اليومية المحفوظة</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">مجموع الوقت الأسبوعي الصحيح</div>
          <div className="stat-number">{totalWeeklyMinutes} دقيقة</div>
          <div className="stat-sub">العطل الرسمية خارج مجموع وقت التدريس</div>
        </div>
      </div>

      <div className="card">
        <h3 style={{ fontSize: "1.15rem", fontWeight: 800, marginBottom: "12px" }}>
          جدول الأسبوع الفعلي (تعديل، نقل، تحديد عطلة، وربط خطة يومية)
        </h3>

        <div className="table-scroll-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>اليوم</th>
                <th>حالة اليوم</th>
                <th>الدرس / الموضوع</th>
                <th>ربط بخطة يومية</th>
                <th>الأنشطة والتقويم</th>
                <th>الزمن (د)</th>
                <th>نقل</th>
              </tr>
            </thead>
            <tbody>
              {days.map((d, idx) => (
                <tr key={idx} style={{ opacity: d.isHoliday ? 0.65 : 1 }}>
                  <td style={{ fontWeight: 800 }}>{d.dayName}</td>
                  <td>
                    <select
                      aria-label={`حالة يوم ${d.dayName}`}
                      className="form-select"
                      style={{ padding: "5px 8px", fontSize: "0.8rem" }}
                      value={d.isHoliday ? "holiday" : "school"}
                      onChange={(e) => {
                        const isHol = e.target.value === "holiday";
                        const next = [...days];
                        next[idx] = {
                          ...next[idx],
                          isHoliday: isHol,
                          minutes: isHol ? 0 : activeContext?.defaultPeriodMinutes || 45,
                        };
                        setDays(next);
                      }}
                    >
                      <option value="school">يوم دوام</option>
                      <option value="holiday">عطلة</option>
                    </select>
                  </td>
                  <td>
                    <input
                      aria-label={`درس يوم ${d.dayName}`}
                      className="form-input"
                      disabled={d.isHoliday}
                      style={{ padding: "6px 8px" }}
                      value={d.lessonTitle || ""}
                      onChange={(e) => {
                        const next = [...days];
                        next[idx] = { ...next[idx], lessonTitle: e.target.value };
                        setDays(next);
                      }}
                    />
                  </td>
                  <td>
                    <select
                      aria-label={`ربط خطة ليوم ${d.dayName}`}
                      className="form-select"
                      disabled={d.isHoliday}
                      style={{ padding: "5px 8px", fontSize: "0.8rem" }}
                      value={d.linkedDailyPlanId || ""}
                      onChange={(e) => {
                        const next = [...days];
                        next[idx] = { ...next[idx], linkedDailyPlanId: e.target.value };
                        setDays(next);
                      }}
                    >
                      <option value="">— بدون ربط —</option>
                      {dailyPlans.map((dp) => (
                        <option key={dp.id} value={dp.id}>
                          {dp.title}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      aria-label={`تقويم يوم ${d.dayName}`}
                      className="form-input"
                      disabled={d.isHoliday}
                      style={{ padding: "6px 8px" }}
                      value={d.assessment || ""}
                      onChange={(e) => {
                        const next = [...days];
                        next[idx] = { ...next[idx], assessment: e.target.value };
                        setDays(next);
                      }}
                    />
                  </td>
                  <td style={{ width: "85px" }}>
                    <input
                      type="number"
                      min={0}
                      max={180}
                      disabled={d.isHoliday}
                      aria-label={`زمن يوم ${d.dayName}`}
                      className="form-input"
                      style={{ padding: "6px 8px", fontWeight: 700 }}
                      value={d.isHoliday ? 0 : d.minutes ?? 45}
                      onChange={(e) => {
                        const next = [...days];
                        next[idx] = { ...next[idx], minutes: Math.max(0, Number(e.target.value) || 0) };
                        setDays(next);
                      }}
                    />
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: "4px" }}>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        style={{ padding: "4px 8px" }}
                        onClick={() => moveDayRow(idx, -1)}
                        title="نقل للأعلى"
                      >
                        ↑
                      </button>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        style={{ padding: "4px 8px" }}
                        onClick={() => moveDayRow(idx, 1)}
                        title="نقل للأسفل"
                      >
                        ↓
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
        <button type="button" className="btn btn-primary" onClick={handleSaveWeekly}>
          حفظ الخطة الأسبوعية
        </button>
        <Link href="/review" className="btn btn-secondary">
          انتقل إلى المراجعة النهائية
        </Link>
      </div>
    </div>
  );
}

