"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTeacherApp, WorkflowStepper } from "../../components/AppShell";

export default function FinalReviewPage() {
  const router = useRouter();
  const { activeContext, activeContextId, apiFetch } = useTeacherApp();
  const [plans, setPlans] = useState<any[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<string>("");
  const [correctionInput, setCorrectionInput] = useState<string>(
    "اطلب من الطالب شرح اختياره لإحدى الخطوات، ثم سجّل ملاحظة مرتبطة بالهدف."
  );
  const [feedback, setFeedback] = useState<string>("");
  const [approverName, setApproverName] = useState<string>("");

  const loadPlans = async (keepId?: string) => {
    try {
      const res = await apiFetch(`/api/plans?contextId=${encodeURIComponent(activeContextId)}`);
      const list = res.items || [];
      setPlans(list);
      const targetId = keepId || selectedPlanId || "pln_daily_demo_a";
      const found = list.find((p: any) => p.id === targetId) || list[0];
      if (found) {
        setSelectedPlanId(found.id);
        if (found.formativeAssessment) {
          setCorrectionInput(found.formativeAssessment);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (activeContextId) {
      loadPlans();
      setApproverName(activeContext?.teacherName || "أحمد علي");
    }
  }, [activeContextId, activeContext]);

  const currentPlan = plans.find((p) => p.id === selectedPlanId) || null;
  const review = currentPlan?.latestReview || {
    blockersCount: 1,
    warningsCount: 1,
    passedCount: 3,
    findings: [],
  };

  const blockers = (review.findings || []).filter((f: any) => f.category === "BLOCKER");
  const warnings = (review.findings || []).filter((f: any) => f.category === "SOURCE_WARNING");
  const passed = (review.findings || []).filter((f: any) => f.category === "PASSED");

  const handleApplyCorrectionAndReAudit = async () => {
    if (!currentPlan) return;
    try {
      const updated = await apiFetch(`/api/plans/${currentPlan.id}`, {
        method: "PUT",
        body: JSON.stringify({
          ...currentPlan,
          formativeAssessment: correctionInput.trim(),
          expectedVersion: currentPlan.version,
        }),
      });
      setFeedback(`تم تحديث حقل التقويم وإعادة فحص الاكتمال للإصدار (v${updated.version}).`);
      await loadPlans(updated.id);
    } catch (err: any) {
      setFeedback(err.message);
    }
  };

  const handleApprovePlan = async () => {
    if (!currentPlan) return;
    try {
      const approved = await apiFetch(
        `/api/plans/${currentPlan.id}/approve?contextId=${encodeURIComponent(activeContextId)}&approverName=${encodeURIComponent(
          approverName || "المعلم المراجع"
        )}`,
        { method: "POST" }
      );
      setFeedback(
        `تم اعتماد الإصدار المحفوظ (v${approved.approvedVersion}) بواسطة «${approved.approvedBy}». أي تعديل لاحق سيُنشئ إصدارًا جديدًا ويزيل الاعتماد عن النسخة الجديدة مع الاحتفاظ بسجل الإصدار المعتمد.`
      );
      await loadPlans(approved.id);
    } catch (err: any) {
      setFeedback(err.message);
    }
  };

  return (
    <div>
      <div className="breadcrumb-line">
        مُعلّم {activeContext?.subject || "المادة"} / مساحة المعلم / مراجعة الخطة
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
        <div>
          <h1 className="page-title">مراجعة الخطة</h1>
          <p className="page-subtitle">
            افصل بين اكتمال الخطة تربويًا وتوثيق مصدر المنهج؛ كل منهما يحتاج مراجعة مستقلة.
          </p>
        </div>

        <select
          aria-label="اختيار الخطة للمراجعة"
          className="form-select"
          style={{ width: "auto" }}
          value={selectedPlanId}
          onChange={(e) => setSelectedPlanId(e.target.value)}
        >
          {plans.map((p) => (
            <option key={p.id} value={p.id}>
              {p.title} ({p.planType === "daily" ? "يومية" : p.planType === "weekly" ? "أسبوعية" : "خمسة أيام"} · v{p.version})
            </option>
          ))}
        </select>
      </div>

      <div className="info-banner">
        <span>
          ⓘ نتائج فحص الاكتمال والتدقيق التخصصي والرياضي أدناه محسوبة فعليًا من محرك التدقيق في خلفية Python FastAPI.
        </span>
      </div>

      <WorkflowStepper activeStep={5} />

      {feedback && (
        <div className="info-banner" style={{ borderColor: "var(--primary-green)", color: "var(--primary-green)" }}>
          <span>✓ {feedback}</span>
        </div>
      )}

      {/* 3 Top Summary Cards matching `مراجعة الخطة.png` */}
      <div className="stats-grid-3">
        <div className="stat-card">
          <div className="stat-label">حقل يمنع اكتمال الخطة (عوائق الاعتماد)</div>
          <div className="stat-number" style={{ color: review.blockersCount > 0 ? "var(--blocker-text)" : "var(--text-main)" }}>
            {review.blockersCount}
          </div>
          <div className="stat-sub">
            {blockers[0]?.title || "لا توجد عوائق مانعة للاعتماد"}
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">تحذير يحتاج مراجعة مصدر (غير مانع)</div>
          <div className="stat-number" style={{ color: "var(--warning-text)" }}>
            {review.warningsCount}
          </div>
          <div className="stat-sub">المنهج غير موثّق / أمثلة مؤلفة</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">فحوص اكتمال ناجحة</div>
          <div className="stat-number" style={{ color: "var(--primary-green)" }}>
            {review.passedCount}
          </div>
          <div className="stat-sub">المدة والأهداف والوسائل والحساب</div>
        </div>
      </div>

      {/* Main Split matching `مراجعة الخطة.png`: Completeness Check Findings (2/3) & Draft Summary Sidebar (1/3) */}
      <div className="main-split-grid">
        <div className="card">
          <h3 style={{ fontSize: "1.2rem", fontWeight: 800, marginBottom: "2px" }}>نتائج فحص الاكتمال</h3>
          <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: "16px" }}>
            حالة المسودة الحالية ({currentPlan?.status === "approved" ? "معتمدة" : currentPlan?.status === "reviewed" ? "مراجعة" : "تحتاج تعديلًا / مسودة"}) · لا تُعدّ هذه الفحوص اعتمادًا تلقائيًا لمصدر الكتاب
          </p>

          {/* Group 1: Blockers & Passed Checks */}
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {(review.findings || []).map((f: any, idx: number) => {
              const isBlocker = f.category === "BLOCKER";
              const isWarning = f.category === "SOURCE_WARNING";
              const targetHref =
                f.fieldTarget === "sourceId" || f.fieldTarget === "context"
                  ? "/sources"
                  : currentPlan?.planType === "five_day"
                  ? "/five-day-plan"
                  : currentPlan?.planType === "weekly"
                  ? "/weekly-plan"
                  : "/daily-plan";

              return (
                <div
                  key={idx}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "14px 16px",
                    borderRadius: "12px",
                    border: "1px solid var(--border-subtle)",
                    backgroundColor: isBlocker ? "#fffafa" : isWarning ? "#fffdf5" : "#fbfcfb",
                    gap: "12px",
                  }}
                >
                  <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
                    <span
                      style={{
                        width: "34px",
                        height: "34px",
                        borderRadius: "8px",
                        backgroundColor: isBlocker
                          ? "var(--blocker-bg)"
                          : isWarning
                          ? "var(--warning-bg)"
                          : "var(--primary-tint-bg)",
                        color: isBlocker
                          ? "var(--blocker-text)"
                          : isWarning
                          ? "var(--warning-text)"
                          : "var(--primary-green)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontWeight: 800,
                        flexShrink: 0,
                      }}
                    >
                      {isBlocker ? "!" : isWarning ? "🛡" : "✓"}
                    </span>
                    <div>
                      <div style={{ fontWeight: 800, fontSize: "0.95rem", marginBottom: "2px" }}>{f.title}</div>
                      <div style={{ fontSize: "0.82rem", color: "var(--text-secondary)" }}>
                        {f.description}{" "}
                        {(isBlocker || isWarning) && (
                          <Link
                            href={targetHref}
                            style={{ color: "var(--primary-green)", fontWeight: 700, textDecoration: "none", marginInlineStart: "6px" }}
                          >
                            {isWarning ? "مراجعة المصدر ←" : "إصلاح الحقل ←"}
                          </Link>
                        )}
                      </div>
                    </div>
                  </div>

                  <span
                    className={`badge ${
                      isBlocker ? "badge-blocker" : isWarning ? "badge-warning" : "badge-success"
                    }`}
                  >
                    {isBlocker ? "مانع" : isWarning ? "تحذير" : "ناجح"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Left Column in RTL: Draft Summary & Approval Gate matching `مراجعة الخطة.png` */}
        <div className="card">
          <h3 style={{ fontSize: "1.1rem", fontWeight: 800, marginBottom: "6px" }}>ملخّص المسودة</h3>
          <div style={{ fontSize: "1.25rem", fontWeight: 800, marginBottom: "8px" }}>
            {currentPlan?.title || "درس تجريبي أ"}
          </div>

          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginBottom: "10px" }}>
            <span className="badge badge-warning">تجريبي — غير موثّق</span>
            <span
              className={`badge ${
                currentPlan?.status === "approved"
                  ? "badge-success"
                  : review.blockersCount > 0
                  ? "badge-blocker"
                  : "badge-neutral"
              }`}
            >
              الحالة:{" "}
              {currentPlan?.status === "approved"
                ? `معتمدة (v${currentPlan.approvedVersion})`
                : review.blockersCount > 0
                ? "تحتاج تعديلًا"
                : "مراجعة — جاهزة للاعتماد"}
            </span>
          </div>

          <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginBottom: "12px" }}>
            خطة {currentPlan?.planType === "daily" ? "يومية" : currentPlan?.planType === "weekly" ? "أسبوعية" : "خمسة أيام"} ·{" "}
            {currentPlan?.totalAllocatedMinutes || 45} دقيقة · {currentPlan?.sectionName || "الشعبة أ"}
            <br />
            {activeContext?.subject} · {activeContext?.grade} · {activeContext?.country}
          </p>

          {review.blockersCount > 0 ? (
            <div className="blocker-banner" style={{ marginBottom: "12px" }}>
              <span>⛔ غير مكتملة: أضف طريقة التقويم أو عالج العوائق قبل الاعتماد أو الانتقال إلى المخرجات المعتمدة.</span>
            </div>
          ) : (
            <div className="info-banner" style={{ marginBottom: "12px", borderColor: "var(--primary-green)", color: "var(--primary-green)" }}>
              <span>✓ لا توجد عوائق اعتماد! يمكنك اعتماد هذا الإصدار وتوليد المخرجات الآن.</span>
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <Link href="/daily-plan" className="btn btn-secondary" style={{ width: "100%" }}>
              العودة إلى حقل التقويم والمحرر
            </Link>

            <button
              type="button"
              className="btn btn-primary"
              disabled={review.blockersCount > 0}
              title={
                review.blockersCount > 0
                  ? "الزر معطل لوجود عائق اعتماد (مثل نقص التقويم التكويني أو تعارض الوقت)"
                  : "اعتماد الإصدار الحالي"
              }
              onClick={handleApprovePlan}
              style={{ width: "100%" }}
            >
              {currentPlan?.status === "approved"
                ? `✓ معتمدة (الإصدار v${currentPlan.approvedVersion})`
                : "اعتماد الإصدار المحفوظ"}
            </button>

            <button
              type="button"
              className="btn btn-secondary"
              disabled={review.blockersCount > 0}
              title={
                review.blockersCount > 0
                  ? "أكمل الحقول المانعة أولًا قبل إنشاء حزمة المخرجات المعتمدة"
                  : "الانتقال إلى تصدير الحزمة"
              }
              onClick={() => router.push("/export-package")}
              style={{ width: "100%" }}
            >
              إنشاء المخرجات الآن (DOCX / PDF / PPTX)
            </button>
          </div>
        </div>
      </div>

      {/* Bottom Interactive Correction Box matching `مراجعة الخطة.png` (`مثال تصحيح: إدخال طريقة تقويم`) */}
      <div className="card">
        <h3 style={{ fontSize: "1.15rem", fontWeight: 800, marginBottom: "2px" }}>
          تصحيح مباشر ومعاينة: إدخال طريقة تقويم
        </h3>
        <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: "14px" }}>
          مقارنة مرئية قبل التصحيح وبعده · يمكنك تطبيق التصحيح مباشرة على الخطة المحفوظة وإعادة فحص الاكتمال
        </p>

        <div className="equal-split-grid">
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
              <label className="form-label">طريقة التقويم الحالية في الخطة</label>
              <span className={`badge ${currentPlan?.formativeAssessment ? "badge-success" : "badge-blocker"}`}>
                {currentPlan?.formativeAssessment ? "مدخلة" : "قبل التصحيح · ناقص"}
              </span>
            </div>
            <textarea
              className={`form-textarea ${!currentPlan?.formativeAssessment ? "error-border" : ""}`}
              readOnly
              value={currentPlan?.formativeAssessment || "لم تُدخل طريقة تقويم"}
            />
          </div>

          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
              <label className="form-label">طريقة التقويم · صياغة قابلة للتطبيق الفوري</label>
              <span className="badge badge-success">بعد التصحيح · مثال محلول</span>
            </div>
            <textarea
              className="form-textarea"
              value={correctionInput}
              onChange={(e) => setCorrectionInput(e.target.value)}
            />
          </div>
        </div>

        <div className="warning-banner" style={{ marginTop: "12px", marginBottom: 0 }}>
          <span>
            🛡 بعد إدخال الطريقة يصبح فحص التقويم مكتملًا، لكن حالة المصدر تبقى معلّقة — غير موثّق حتى تكتمل مراجعة الكتاب في صفحة المصادر.
          </span>
        </div>
      </div>

      <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
        <button type="button" className="btn btn-primary" onClick={handleApplyCorrectionAndReAudit}>
          ↻ تطبيق التصحيح وإعادة فحص الاكتمال
        </button>
        <Link href="/reports" className="btn btn-secondary">
          متابعة بعد التصحيح إلى التقارير ←
        </Link>
      </div>
    </div>
  );
}
