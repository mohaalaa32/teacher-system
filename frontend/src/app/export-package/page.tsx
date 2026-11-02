"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useTeacherApp, WorkflowStepper } from "../../components/AppShell";

const PACKAGE_ITEMS = [
  {
    id: "docx",
    title: "الخطة اليومية القابلة للتحرير",
    desc: "ملف OOXML DOCX بجداول وفقرات قابلة للتحرير واتجاه RTL/LTR",
    badge: "DOCX",
  },
  {
    id: "pdf",
    title: "نسخة قراءة وطباعة من الخطة اليومية",
    desc: "ملف PDF 1.7 بنص قابل للتحديد وجداول متجهية",
    badge: "PDF",
  },
  {
    id: "pptx",
    title: "عرض تقديمي قابل للتحرير",
    desc: "شرائح تربوية بنصوص وعناصر وأشكال OOXML قابلة للتحرير في PowerPoint",
    badge: "PPTX",
  },
  {
    id: "report_pdf",
    title: "تقرير التخطيط والاكتمال",
    desc: "ملخص الخطط والمراجعات ونواقص التوثيق دون نسب نجاح طلاب مفترضة",
    badge: "PDF",
  },
  {
    id: "bundle_zip",
    title: "حزمة شاملة (تشمل سجل بيانات المصدر JSON + جميع الملفات)",
    desc: "جميع الملفات الأربعة مع سجل بيانات المصدر وبصمة الإصدار في أرشيف واحد",
    badge: "ZIP + JSON",
  },
];

export default function ExportPackagePage() {
  const { activeContext, activeContextId, apiFetch } = useTeacherApp();
  const [plans, setPlans] = useState<any[]>([]);
  const [exportsList, setExportsList] = useState<any[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<string>("");
  const [busyFormat, setBusyFormat] = useState<string>("");
  const [feedback, setFeedback] = useState<string>("");

  const loadData = async () => {
    try {
      const [pRes, eRes] = await Promise.all([
        apiFetch(`/api/plans?contextId=${encodeURIComponent(activeContextId)}`),
        apiFetch(`/api/exports?contextId=${encodeURIComponent(activeContextId)}`),
      ]);
      const pList = pRes.items || [];
      setPlans(pList);
      setExportsList(eRes.items || []);
      if (pList.length > 0 && !selectedPlanId) {
        setSelectedPlanId(pList[0].id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (activeContextId) loadData();
  }, [activeContextId]);

  const currentPlan = plans.find((p) => p.id === selectedPlanId) || null;

  const handleGenerateExport = async (fmt: string) => {
    setBusyFormat(fmt);
    setFeedback("");
    try {
      const created = await apiFetch("/api/exports", {
        method: "POST",
        body: JSON.stringify({
          contextId: activeContextId,
          planId: selectedPlanId || null,
          exportFormat: fmt,
        }),
      });
      setFeedback(
        `تم إنشاء وفحص الملف (${created.fileName}) للإصدار v${created.planVersion} بنجاح (البصمة SHA-256: ${created.contentSha256.slice(
          0,
          16
        )}...).`
      );
      window.open(created.downloadUrl, "_blank");
      await loadData();
    } catch (err: any) {
      setFeedback(`خطأ: ${err.message}`);
    } finally {
      setBusyFormat("");
    }
  };

  return (
    <div>
      <div className="breadcrumb-line">
        مُعلّم {activeContext?.subject || "المادة"} / مساحة المعلم / تصدير الحزمة
      </div>
      <h1 className="page-title">تصدير الحزمة والمستندات الفعلية</h1>
      <p className="page-subtitle">
        اجمع الخطة والعرض والتقرير وبيانات المصدر في ملفات حقيقية قابلة للفتح والتحرير، مرتبطة بإصدار محفوظ محدد مع الحفاظ على تنبيه التوثيق.
      </p>

      <div className="info-banner">
        <span>
          ⓘ يُصدّر كل ملف من إصدار محفوظ محدد (v{currentPlan?.version || 1}) ويُفحص بنيويًا (OOXML / PDF 1.7) قبل إتاحته للتنزيل. تعديل الخطة لاحقًا لا يغيّر الملفات المصدّرة سابقًا.
        </span>
      </div>

      <WorkflowStepper activeStep={8} />

      <div className="warning-banner">
        <span>
          ⚠ سجل منهج تجريبي — غير موثّق: تُرفق حالة التوثيق ولقطة السياق السبعة بكل المخرجات بصدق دون وضع ختم اعتماد كاذب على المسودات.
        </span>
      </div>

      {feedback && (
        <div className="info-banner" style={{ borderColor: "var(--primary-green)", color: "var(--primary-green)" }}>
          <span>✓ {feedback}</span>
        </div>
      )}

      {/* Main Split matching `تصدير الحزمة.png`: Included Outputs List (2/3) & Package Summary + Preparation Status (1/3) */}
      <div className="main-split-grid">
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px", flexWrap: "wrap", gap: "8px" }}>
            <div>
              <h3 style={{ fontSize: "1.15rem", fontWeight: 800 }}>المخرجات المشمولة القابلة للتوليد الفوري</h3>
              <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                اختر الخطة المراد تصديرها واضغط على أي صيغة لتوليد وتنزيل الملف الحقيقي
              </p>
            </div>

            {plans.length > 0 ? (
              <select
                aria-label="اختيار الخطة للتصدير"
                className="form-select"
                style={{ width: "auto" }}
                value={selectedPlanId}
                onChange={(e) => setSelectedPlanId(e.target.value)}
              >
                {plans.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title} (الإصدار v{p.version})
                  </option>
                ))}
              </select>
            ) : (
              <span className="badge badge-warning">لا توجد خطة محددة</span>
            )}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {PACKAGE_ITEMS.map((item) => (
              <div
                key={item.id}
                style={{
                  padding: "14px 16px",
                  borderRadius: "12px",
                  border: "1px solid var(--border-color)",
                  backgroundColor: "#fbfcfb",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: "12px",
                  flexWrap: "wrap",
                }}
              >
                <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                  <span style={{ color: "var(--primary-green)", fontWeight: 800, fontSize: "1.1rem" }}>☑</span>
                  <div>
                    <div style={{ fontWeight: 800, fontSize: "0.95rem" }}>{item.title}</div>
                    <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>{item.desc}</div>
                  </div>
                </div>

                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  <span className="badge badge-success">{item.badge}</span>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ padding: "6px 12px", fontSize: "0.8rem" }}
                    disabled={!!busyFormat || !currentPlan}
                    onClick={() => handleGenerateExport(item.id)}
                  >
                    {busyFormat === item.id ? "جارٍ التوليد..." : `توليد وتنزيل ${item.badge}`}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="card">
            <h3 style={{ fontSize: "1.1rem", fontWeight: 800, marginBottom: "4px" }}>ملخّص الحزمة</h3>
            <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginBottom: "14px" }}>
              5 عناصر مختارة · مرتبطة بالسياق النشط ({activeContext?.subject})
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "16px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: "0.88rem" }}>{currentPlan?.title || "لا توجد خطة محددة"}</div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                    الإصدار v{currentPlan?.version || 1} · {currentPlan?.totalAllocatedMinutes || 45} دقيقة
                  </div>
                </div>
                <span className="badge badge-neutral">خطة</span>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: "0.88rem" }}>المراجعة التربوية</div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                    حالة الخطة: {currentPlan?.status === "approved" ? "معتمدة" : currentPlan?.status || "مسودة"}
                  </div>
                </div>
                <span
                  className={`badge ${
                    currentPlan?.status === "approved" || currentPlan?.status === "reviewed"
                      ? "badge-success"
                      : "badge-warning"
                  }`}
                >
                  {currentPlan?.status === "approved" ? "معتمدة" : "معلّمة كمسودة"}
                </span>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: "0.88rem" }}>مراجعة المصدر</div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                    تُوثّق في ترويسة المستندات وسجل JSON
                  </div>
                </div>
                <span className="badge badge-warning">معلّق</span>
              </div>
            </div>

            <button
              type="button"
              className="btn btn-primary"
              style={{ width: "100%" }}
              disabled={!!busyFormat}
              onClick={() => handleGenerateExport("bundle_zip")}
            >
              📦 {busyFormat === "bundle_zip" ? "جارٍ تجميع الحزمة..." : "تجهيز وتنزيل الحزمة الكاملة (ZIP)"}
            </button>
          </div>

          <div className="card">
            <h3 style={{ fontSize: "1.05rem", fontWeight: 800, marginBottom: "6px" }}>حالة التجهيز والفحص البنيوي</h3>
            <span className="badge badge-success" style={{ marginBottom: "8px" }}>
              فحص OOXML وPDF 1.7 مفعّل
            </span>
            <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
              كل ملف مولّد يمر بفحص بنيوي مستقل يتحقق من صلاحية جداول وفقرات `word/document.xml`، وشرائح `ppt/slides/slide*.xml`، وهيكل `%PDF-1.7` قبل تسليمه.
            </p>
          </div>
        </div>
      </div>

      {/* Export Package History Table matching `تصدير الحزمة.png` */}
      <div className="card">
        <h3 style={{ fontSize: "1.15rem", fontWeight: 800, marginBottom: "4px" }}>سجل الحزم والملفات المصدّرة</h3>
        <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: "12px" }}>
          جميع عمليات التصدير المحفوظة فعليًا في قاعدة البيانات للسياق النشط ({exportsList.length} ملفات)
        </p>

        <div className="table-scroll-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>الملف المصدّر</th>
                <th>الصيغة والإصدار</th>
                <th>بصمة المحتوى (SHA-256)</th>
                <th>فحص البنية</th>
                <th>الإجراء</th>
              </tr>
            </thead>
            <tbody>
              {exportsList.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: "center", color: "var(--text-muted)" }}>
                    اضغط على أي زر تصدير أعلاه لتوليد ملف DOCX أو PDF أو PPTX أو حزمة كاملة.
                  </td>
                </tr>
              ) : (
                exportsList.map((ex) => (
                  <tr key={ex.id}>
                    <td style={{ fontWeight: 700 }}>{ex.fileName}</td>
                    <td>
                      <span className="badge badge-neutral">{ex.exportFormat.toUpperCase()}</span> · v{ex.planVersion}
                    </td>
                    <td style={{ fontFamily: "monospace", fontSize: "0.78rem" }}>
                      {ex.contentSha256?.slice(0, 18)}...
                    </td>
                    <td>
                      <span className="badge badge-success">
                        {ex.structuralCheckPassed ? "✓ سليم وقابل للفتح" : "فشل"}
                      </span>
                    </td>
                    <td>
                      <a
                        href={`/api/exports/${ex.id}/download?contextId=${encodeURIComponent(activeContextId)}`}
                        className="btn btn-secondary"
                        style={{ padding: "5px 12px", fontSize: "0.78rem" }}
                      >
                        تنزيل الملف الفعلي
                      </a>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div style={{ display: "flex", gap: "10px" }}>
        <Link href="/presentations" className="btn btn-secondary">
          ← العودة إلى العرض التقديمي
        </Link>
      </div>
    </div>
  );
}

