"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useTeacherApp } from "../components/AppShell";

export default function DashboardPage() {
  const { activeContext, activeContextId, apiFetch } = useTeacherApp();
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let mounted = true;
    async function load() {
      setLoading(true);
      try {
        const res = await apiFetch(`/api/dashboard?contextId=${encodeURIComponent(activeContextId)}`);
        if (mounted) setSummary(res);
      } catch (e) {
        console.error(e);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    if (activeContextId) {
      load();
    } else {
      setLoading(false);
      setSummary(null);
    }
    return () => {
      mounted = false;
    };
  }, [activeContextId, apiFetch]);

  const stats = summary?.stats || {
    attentionCount: 0,
    draftsCount: 0,
    totalPlansCount: 0,
    reviewedCount: 0,
    exportsCount: 0,
  };

  return (
    <div>
      <div className="breadcrumb-line">
        مُعلّم {activeContext?.subject || "المادة"} / مساحة المعلم / لوحة المعلم
      </div>
      <h1 className="page-title">لوحة المعلم</h1>
      <p className="page-subtitle">
        نظرة واضحة إلى خططك ومهامك القادمة، في مساحة مخصّصة لمادة {activeContext?.subject || "المادة المختارة"} ({activeContext?.grade || "—"}).
      </p>

      <div className="info-banner">
        <span>
          ⓘ جميع الإحصاءات أدناه مشتقة حيًّا من قاعدة البيانات للسياق النشط ({activeContext?.id || "—"}) وليست أرقامًا ثابتة.
        </span>
      </div>

      {/* Hero Welcome Banner matching `لوحة المعلم.png` */}
      <div className="hero-banner-card">
        <div>
          <h2 style={{ fontSize: "1.45rem", fontWeight: 800, marginBottom: "6px" }}>
            مرحبًا {activeContext?.teacherName ? `أستاذ ${activeContext.teacherName}` : "بك"}، لنخطّط لحصة واضحة.
          </h2>
          <p style={{ fontSize: "0.9rem", color: "var(--sidebar-text)", marginBottom: "6px" }}>
            أكمل مراجعة الخطة اليومية، ثم جهّز عرضك وحزمة ملفاتك من مساحة واحدة.
          </p>
          <div style={{ fontSize: "0.78rem", color: "var(--sidebar-muted)" }}>
            {activeContext?.teacherName || "المعلم"} | تاريخ التخطيط: {activeContext?.planningDate || new Date().toISOString().split("T")[0]}
          </div>
        </div>
        <Link href="/daily-plan" className="btn btn-primary" style={{ backgroundColor: "#176B52", padding: "11px 22px" }}>
          ← ابدأ خطة جديدة
        </Link>
      </div>

      {/* 4 Derived Stat Cards matching `لوحة المعلم.png` */}
      <div className="stats-grid-4">
        <div className="stat-card">
          <div className="stat-label">مهام تحتاج انتباهك</div>
          <div className="stat-number">{loading ? "..." : stats.attentionCount}</div>
          <div className="stat-sub">تقويم ناقص + مراجعة مصدر</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">مسودات قيد الإعداد</div>
          <div className="stat-number">{loading ? "..." : stats.draftsCount}</div>
          <div className="stat-sub">من أصل {stats.totalPlansCount} خطط محفوظة</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">خطط مكتملة المراجعة</div>
          <div className="stat-number">{loading ? "..." : stats.reviewedCount}</div>
          <div className="stat-sub">مراجعة اكتمال، لا توثيق للمصدر</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">حزم التصدير المولّدة</div>
          <div className="stat-number">{loading ? "..." : stats.exportsCount}</div>
          <div className="stat-sub">ملفات DOCX / PDF / PPTX حقيقية</div>
        </div>
      </div>

      {/* Main Split: Today's Tasks (2/3) & Curriculum Source Status (1/3) */}
      <div className="main-split-grid">
        <div className="card">
          <h3 style={{ fontSize: "1.15rem", fontWeight: 800, marginBottom: "4px" }}>مهام اليوم</h3>
          <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginBottom: "14px" }}>
            ترتيب مقترح لإنهاء المسودات وفصل عوائق الاعتماد عن توثيق المصدر
          </p>

          {(!summary?.todayTasks || summary.todayTasks.length === 0) ? (
            <div style={{ textAlign: "center", padding: "26px 12px", color: "var(--text-secondary)" }}>
              <p style={{ marginBottom: "12px", fontSize: "0.9rem" }}>لا توجد مهام معلّقة حاليًا. بيئة العمل جاهزة لإعداد أول خطة.</p>
              <Link href="/daily-plan" className="btn btn-primary" style={{ fontSize: "0.84rem" }}>
                + إعداد خطة درس جديدة
              </Link>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {summary.todayTasks.map((t: any) => (
                <div
                  key={t.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "12px 14px",
                    borderRadius: "10px",
                    border: "1px solid var(--border-subtle)",
                    backgroundColor: "#fbfcfb",
                    gap: "12px",
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 700, fontSize: "0.92rem" }}>
                      <Link href={t.targetRoute || "/review"} style={{ color: "inherit", textDecoration: "none" }}>
                        {t.title}
                      </Link>
                    </div>
                    <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>{t.subtitle}</div>
                  </div>
                  <span
                    className={`badge ${
                      t.badgeType === "blocker"
                        ? "badge-blocker"
                        : t.badgeType === "warning"
                        ? "badge-warning"
                        : "badge-neutral"
                    }`}
                  >
                    {t.badge}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <h3 style={{ fontSize: "1.1rem", fontWeight: 800, marginBottom: "8px" }}>حالة مصدر المنهج</h3>
          {summary?.sources && summary.sources.length > 0 ? (
            <div>
              <span
                className={`badge ${
                  summary.sources[0].verificationStatus === "human_verified" ? "badge-success" : "badge-warning"
                }`}
                style={{ marginBottom: "10px" }}
              >
                {summary.sources[0].verificationStatus === "human_verified"
                  ? "موثّق — مراجعة بشرية معتمدة"
                  : "تجريبي — غير موثّق"}
              </span>
              <div style={{ fontWeight: 700, fontSize: "0.95rem", marginBottom: "6px" }}>
                {summary.sources[0].title}
              </div>
              <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginBottom: "14px" }}>
                {summary.sources[0].reviewNotes ||
                  "السنة الدراسية والطبعة والمصدر لم تُستكمل. يتطلب الاستخدام الرسمي مراجعة المصدر أولًا."}
              </p>
              <Link href="/sources" className="btn btn-secondary" style={{ width: "100%" }}>
                عرض بيانات المصدر واستيراد PDF
              </Link>
            </div>
          ) : (
            <div>
              <span className="badge badge-warning" style={{ marginBottom: "10px" }}>
                لا يوجد ملف منهج مرفوع
              </span>
              <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginBottom: "14px" }}>
                ارفع ملف PDF للمنهج في هذا السياق لتوثيق الفصول والدروس وأرقام الصفحات.
              </p>
              <Link href="/sources" className="btn btn-secondary" style={{ width: "100%" }}>
                رفع كتاب المنهج (PDF)
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Bottom Split: Recent Plans Table (2/3) & Recent Exports/Activity (1/3) */}
      <div className="main-split-grid">
        <div className="card">
          <h3 style={{ fontSize: "1.15rem", fontWeight: 800, marginBottom: "4px" }}>أحدث الخطط المحفوظة</h3>
          <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: "12px" }}>
            جميع السجلات أدناه معزولة ضمن السياق النشط ({activeContext?.subject || "—"} · {activeContext?.grade || "—"})
          </p>

          {(!summary?.recentPlans || summary.recentPlans.length === 0) ? (
            <div style={{ textAlign: "center", padding: "34px 14px", color: "var(--text-secondary)" }}>
              <p style={{ marginBottom: "12px", fontSize: "0.92rem" }}>
                لا توجد خطط محفوظة بعد في سياق ({activeContext?.subject || "المادة المحددة"}).
              </p>
              <Link href="/daily-plan" className="btn btn-primary">
                + إنشاء أول خطة يومية
              </Link>
            </div>
          ) : (
            <div className="table-scroll-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>الخطة</th>
                    <th>النمط</th>
                    <th>آخر تعديل</th>
                    <th>الحالة</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.recentPlans.map((p: any) => (
                    <tr key={p.id}>
                      <td style={{ fontWeight: 700 }}>
                        <Link
                          href={
                            p.planType === "five_day"
                              ? `/five-day-plan?planId=${p.id}`
                              : p.planType === "weekly"
                              ? `/weekly-plan?planId=${p.id}`
                              : `/daily-plan?planId=${p.id}`
                          }
                          style={{ color: "var(--text-main)", textDecoration: "none" }}
                        >
                          {p.title}
                        </Link>
                      </td>
                      <td>
                        {p.planType === "daily"
                          ? "يومية"
                          : p.planType === "weekly"
                          ? "أسبوعية"
                          : "خمسة أيام"}
                      </td>
                      <td>{p.planningDate || "—"}</td>
                      <td>
                        <span
                          className={`badge ${
                            p.status === "approved" || p.status === "reviewed"
                              ? "badge-success"
                              : p.status === "needs_revision"
                              ? "badge-blocker"
                              : "badge-neutral"
                          }`}
                        >
                          {p.status === "approved"
                            ? "معتمدة"
                            : p.status === "reviewed"
                            ? "مكتملة المراجعة"
                            : p.status === "needs_revision"
                            ? "تقويم ناقص / تحتاج تعديلًا"
                            : "مسودة"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div style={{ marginTop: "14px" }}>
            <Link href="/daily-plan" className="btn btn-secondary">
              ← متابعة المسودة اليومية
            </Link>
          </div>
        </div>

        <div className="card">
          <h3 style={{ fontSize: "1.1rem", fontWeight: 800, marginBottom: "4px" }}>النشاط الأخير والملفات</h3>
          <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: "12px" }}>
            آخر العمليات والملفات المولّدة في هذا السياق
          </p>

          {(!summary?.recentPlans || summary.recentPlans.length === 0) && (!summary?.recentExports || summary.recentExports.length === 0) ? (
            <div style={{ textAlign: "center", padding: "26px 12px", color: "var(--text-secondary)" }}>
              <p style={{ fontSize: "0.85rem" }}>لا يوجد نشاط مسجّل بعد في هذا السياق.</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {summary?.recentPlans?.[0] && (
                <div
                  style={{
                    padding: "10px 12px",
                    borderRadius: "8px",
                    border: "1px solid var(--border-subtle)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 700, fontSize: "0.86rem" }}>أحدث مسودة خطة</div>
                    <div style={{ fontSize: "0.76rem", color: "var(--text-secondary)" }}>
                      {summary.recentPlans[0].title} · محفوظة في قاعدة البيانات
                    </div>
                  </div>
                  <span className="badge badge-neutral">مسودة</span>
                </div>
              )}

              {activeContext?.selectedTools && (
                <div
                  style={{
                    padding: "10px 12px",
                    borderRadius: "8px",
                    border: "1px solid var(--border-subtle)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 700, fontSize: "0.86rem" }}>
                      اختيار {activeContext.selectedTools.length} وسائل تعليمية
                    </div>
                    <div style={{ fontSize: "0.76rem", color: "var(--text-secondary)" }}>
                      {activeContext.selectedTools.join("، ")}
                    </div>
                  </div>
                  <span className="badge badge-success">مفعّلة</span>
                </div>
              )}

              {(summary?.recentExports || []).map((ex: any) => (
                <div
                  key={ex.id}
                  style={{
                    padding: "10px 12px",
                    borderRadius: "8px",
                    border: "1px solid var(--border-subtle)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 700, fontSize: "0.84rem" }}>{ex.fileName}</div>
                    <div style={{ fontSize: "0.74rem", color: "var(--text-secondary)" }}>
                      الإصدار v{ex.planVersion} · {(ex.fileSize / 1024).toFixed(1)} KB
                    </div>
                  </div>
                  <a
                    href={`/api/exports/${ex.id}/download?contextId=${encodeURIComponent(activeContextId)}`}
                    className="badge badge-success"
                    style={{ textDecoration: "none" }}
                  >
                    تنزيل
                  </a>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

