"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useTeacherApp, WorkflowStepper } from "../../components/AppShell";

export default function ReportsPage() {
  const { activeContext, activeContextId, apiFetch } = useTeacherApp();
  const [dateFrom, setDateFrom] = useState<string>("2026-10-01");
  const [dateTo, setDateTo] = useState<string>("2026-10-31");
  const [planTypeFilter, setPlanTypeFilter] = useState<string>("all");
  const [report, setReport] = useState<any>(null);
  const [exporting, setExporting] = useState<string>("");
  const [feedback, setFeedback] = useState<string>("");

  const loadReport = async () => {
    try {
      const res = await apiFetch(
        `/api/reports?contextId=${encodeURIComponent(activeContextId)}&dateFrom=${encodeURIComponent(
          dateFrom
        )}&dateTo=${encodeURIComponent(dateTo)}&planType=${encodeURIComponent(planTypeFilter)}`
      );
      setReport(res);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (activeContextId) loadReport();
  }, [activeContextId]);

  const handleExportReport = async (fmt: "report_pdf" | "report_docx") => {
    setExporting(fmt);
    try {
      const res = await apiFetch("/api/exports", {
        method: "POST",
        body: JSON.stringify({
          contextId: activeContextId,
          exportFormat: fmt,
          dateFrom,
          dateTo,
          planTypeFilter,
        }),
      });
      window.open(res.downloadUrl, "_blank");
      setFeedback(`تم توليد وتنزيل التقرير بصيغة ${fmt === "report_pdf" ? "PDF" : "DOCX"} بنجاح.`);
      await loadReport();
    } catch (err: any) {
      setFeedback(err.message);
    } finally {
      setExporting("");
    }
  };

  const total = report?.totalPlans || 0;
  const reviewed = report?.reviewedPlans || 0;
  const drafts = report?.draftPlans || 0;
  const exportsCount = report?.exportsCount || 0;

  return (
    <div>
      <div className="breadcrumb-line">
        مُعلّم {activeContext?.subject || "المادة"} / مساحة المعلم / التقارير
      </div>
      <h1 className="page-title">التقارير</h1>
      <p className="page-subtitle">
        تقرير تخطيط واكتمال للمعلم، لا تقرير تحصيل أو أداء للطلاب (لا نسب نجاح طلاب مفترضة).
      </p>

      <div className="info-banner">
        <span>
          ⓘ الأرقام والجداول أدناه مشتقة فعليًا من خطط ومراجعات وتصديرات السياق النشط ({activeContext?.subject} · {activeContext?.grade}).
        </span>
      </div>

      <WorkflowStepper activeStep={6} />

      {/* Filter Bar matching `التقارير.png` */}
      <div
        className="card"
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr auto",
          gap: "12px",
          alignItems: "end",
          padding: "16px",
        }}
      >
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label">من · تاريخ</label>
          <input
            type="date"
            className="form-input"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
          />
        </div>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label">إلى · تاريخ</label>
          <input
            type="date"
            className="form-input"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
          />
        </div>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label">نوع الخطة</label>
          <select
            className="form-select"
            value={planTypeFilter}
            onChange={(e) => setPlanTypeFilter(e.target.value)}
          >
            <option value="all">جميع أنماط التخطيط</option>
            <option value="daily">يومية</option>
            <option value="weekly">أسبوعية</option>
            <option value="five_day">خمسة أيام</option>
          </select>
        </div>
        <button type="button" className="btn btn-primary" onClick={loadReport}>
          📊 عرض التقرير
        </button>
      </div>

      {feedback && (
        <div className="info-banner" style={{ borderColor: "var(--primary-green)", color: "var(--primary-green)" }}>
          <span>✓ {feedback}</span>
        </div>
      )}

      {/* 4 Stat Cards matching `التقارير.png` */}
      <div className="stats-grid-4">
        <div className="stat-card">
          <div className="stat-label">خطط محفوظة إجمالًا</div>
          <div className="stat-number">{total}</div>
          <div className="stat-sub">
            {activeContext?.subject} · {activeContext?.grade}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">خطط مكتملة المراجعة</div>
          <div className="stat-number">{reviewed}</div>
          <div className="stat-sub">لا يعني توثيق المحتوى تلقائيًا</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">مسودات قيد الإعداد</div>
          <div className="stat-number">{drafts}</div>
          <div className="stat-sub">تشمل المسودات التي تحتاج استكمال التقويم</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">حالات حزم تصدير</div>
          <div className="stat-number">{exportsCount}</div>
          <div className="stat-sub">ملفات فعلية مولّدة في هذا السياق</div>
        </div>
      </div>

      {/* Main Split matching `التقارير.png`: Progress Bars (2/3) & Report Preview Card (1/3) */}
      <div className="main-split-grid">
        <div className="card">
          <h3 style={{ fontSize: "1.15rem", fontWeight: 800, marginBottom: "2px" }}>من التخطيط إلى المخرجات</h3>
          <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: "16px" }}>
            التصدير يرتبط بإصدارات الخطط التي روجعت
          </p>

          {[
            { label: "إجمالي الخطط المحفوظة", val: total, max: Math.max(1, total) },
            { label: "مراجعة اكتمال منجزة", val: reviewed, max: Math.max(1, total) },
            { label: "حزم وملفات تصدير مولّدة", val: exportsCount, max: Math.max(1, total) },
          ].map((bar, idx) => {
            const pct = Math.min(100, Math.round((bar.val / bar.max) * 100));
            return (
              <div key={idx} style={{ marginBottom: "16px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", fontWeight: 700, marginBottom: "6px" }}>
                  <span>{bar.label}</span>
                  <span style={{ color: "var(--primary-green)" }}>{bar.val}</span>
                </div>
                <div style={{ height: "10px", backgroundColor: "#eef2ef", borderRadius: "999px", overflow: "hidden" }}>
                  <div
                    style={{
                      width: `${pct}%`,
                      height: "100%",
                      backgroundColor: "var(--sidebar-bg)",
                      borderRadius: "999px",
                    }}
                  />
                </div>
              </div>
            );
          })}

          <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: "10px" }}>
            {report?.disclaimer || "المؤشرات تقيس تنظيم التخطيط فقط. لا توجد بيانات متعلمين ولا استنتاجات عن التحصيل."}
          </div>
        </div>

        <div className="card">
          <h3 style={{ fontSize: "1.1rem", fontWeight: 800, marginBottom: "2px" }}>معاينة التقرير</h3>
          <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginBottom: "12px" }}>
            جاهز للتصدير الفعلي بصيغتي PDF وDOCX
          </p>

          <div
            style={{
              padding: "16px",
              borderRadius: "10px",
              border: "1px solid var(--border-subtle)",
              backgroundColor: "#fbfcfb",
              marginBottom: "14px",
            }}
          >
            <div style={{ fontWeight: 800, fontSize: "1.05rem", marginBottom: "4px" }}>تقرير التخطيط والاكتمال</div>
            <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: "8px" }}>
              {activeContext?.teacherName || "أحمد علي"}
              <br />
              {activeContext?.subject} · {activeContext?.grade} · {activeContext?.country}
            </div>
            <span className="badge badge-warning" style={{ marginBottom: "8px" }}>
              مخرج تخطيطي — حالة المصدر مسجلة
            </span>
            <div style={{ fontSize: "0.82rem", fontWeight: 700 }}>
              {total} خطط · {reviewed} مراجعات مكتملة · {exportsCount} حالة تصدير
            </div>
          </div>

          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={!!exporting}
              onClick={() => handleExportReport("report_pdf")}
              style={{ flex: 1 }}
            >
              {exporting === "report_pdf" ? "جارٍ التصدير..." : "تصدير تقرير PDF"}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={!!exporting}
              onClick={() => handleExportReport("report_docx")}
              style={{ flex: 1 }}
            >
              {exporting === "report_docx" ? "جارٍ التصدير..." : "تصدير DOCX"}
            </button>
          </div>
        </div>
      </div>

      {/* Pattern Summary Table matching `التقارير.png` */}
      <div className="card">
        <h3 style={{ fontSize: "1.15rem", fontWeight: 800, marginBottom: "4px" }}>ملخّص الأنماط</h3>
        <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: "12px" }}>
          مشتق من الخطط المحفوظة والتصديرات الفعلية ضمن السياق النشط
        </p>

        <div className="table-scroll-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>نمط الخطة</th>
                <th>مخطّط</th>
                <th>مكتمل المراجعة</th>
                <th>حالة تصدير مولّدة</th>
              </tr>
            </thead>
            <tbody>
              {(report?.patternSummary || []).map((row: any, idx: number) => (
                <tr key={idx}>
                  <td style={{ fontWeight: 700 }}>{row.label}</td>
                  <td>{row.planned}</td>
                  <td>{row.reviewed}</td>
                  <td style={{ color: "var(--primary-green)", fontWeight: 700 }}>{row.exported}</td>
                </tr>
              ))}
              <tr style={{ backgroundColor: "#f9fbf9", fontWeight: 800 }}>
                <td>الإجمالي</td>
                <td>{total}</td>
                <td>{reviewed}</td>
                <td style={{ color: "var(--primary-green)" }}>{exportsCount}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Documentation Gaps Warning Banner matching `التقارير.png` */}
      {(report?.documentationGaps || []).map((gap: string, idx: number) => (
        <div className="warning-banner" key={idx}>
          <span>🛡 تحذير المصدر: {gap}</span>
        </div>
      ))}

      <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
        <Link href="/presentations" className="btn btn-primary">
          ← إعداد العرض التقديمي (PPTX)
        </Link>
        <Link href="/review" className="btn btn-secondary">
          العودة إلى المراجعة
        </Link>
      </div>
    </div>
  );
}
