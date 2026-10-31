"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useTeacherApp, WorkflowStepper } from "../../components/AppShell";

export default function PresentationsPage() {
  const { activeContext, activeContextId, apiFetch } = useTeacherApp();
  const [plans, setPlans] = useState<any[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<string>("");
  const [slides, setSlides] = useState<any[]>([]);
  const [activeSlideIdx, setActiveSlideIdx] = useState<number>(2); // Default Slide 3 as in `العروض التقديمية.png`
  const [presTitle, setPresTitle] = useState<string>("درس تجريبي أ");
  const [textDirection, setTextDirection] = useState<string>("rtl");
  const [layoutStyle, setLayoutStyle] = useState<string>("title_and_content");
  const [exporting, setExporting] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<string>("");

  const loadPlans = async (keepId?: string) => {
    try {
      const res = await apiFetch(`/api/plans?contextId=${encodeURIComponent(activeContextId)}`);
      const list = res.items || [];
      setPlans(list);
      const targetId = keepId || selectedPlanId || (list[0] && list[0].id) || "";
      const found = list.find((p: any) => p.id === targetId) || list[0];
      if (found) {
        bindPlanSlides(found);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const bindPlanSlides = (pln: any) => {
    setSelectedPlanId(pln.id);
    setPresTitle(pln.title || "عرض الدرس");
    const defaultSlides =
      pln.slides && pln.slides.length > 0
        ? pln.slides
        : [
            { order: 1, title: pln.title || "درس تجريبي أ", content: `${activeContext?.subject} · ${activeContext?.grade} · ${activeContext?.country}` },
            { order: 2, title: "أهداف الحصة", content: (pln.objectives || []).join("\n") || "أهداف الدرس القابلة للملاحظة والقياس." },
            {
              order: 3,
              title: "ناقش طريقة التفكير",
              content: "أدخل مهمة مناسبة للمادة بعد مراجعة المصدر، ثم اطلب من الطلاب تفسير خطواتهم.\nسؤال النقاش: ما سبب اختيارك لهذه الخطوة؟",
            },
            { order: 4, title: "قارن الاستراتيجيات", content: "بالأقلام الملوّنة والبطاقات: ميّز خطوات كل طريقة ثم ناقش أوجه التشابه والاختلاف." },
            { order: 5, title: "تقويم ختامي", content: pln.formativeAssessment || "اطلب من الطالب شرح اختياره لإحدى الخطوات، ثم سجّل ملاحظة مرتبطة بالهدف." },
          ];
    setSlides(defaultSlides);
    setActiveSlideIdx(Math.min(2, defaultSlides.length - 1));
  };

  useEffect(() => {
    if (activeContextId) loadPlans();
  }, [activeContextId]);

  const currentPlan = plans.find((p) => p.id === selectedPlanId) || null;
  const activeSlide = slides[activeSlideIdx] || { title: "شريحة", content: "" };

  const handleSaveSlidesToPlan = async () => {
    if (!currentPlan) return;
    try {
      const updated = await apiFetch(`/api/plans/${currentPlan.id}`, {
        method: "PUT",
        body: JSON.stringify({
          ...currentPlan,
          slides,
          presentationSettings: {
            title: presTitle,
            slidesCount: slides.length,
            textDirection,
            layoutStyle,
            companionTools: (activeContext?.selectedTools || []).join("، "),
          },
          expectedVersion: currentPlan.version,
        }),
      });
      setFeedback(`تم حفظ بنية الشرائح وإعدادات العرض في الخطة (v${updated.version}).`);
      await loadPlans(updated.id);
    } catch (err: any) {
      setFeedback(err.message);
    }
  };

  const handleExportPptx = async () => {
    if (!currentPlan) return;
    setExporting(true);
    try {
      await handleSaveSlidesToPlan();
      const res = await apiFetch("/api/exports", {
        method: "POST",
        body: JSON.stringify({
          contextId: activeContextId,
          planId: currentPlan.id,
          exportFormat: "pptx",
        }),
      });
      window.open(res.downloadUrl, "_blank");
      setFeedback(
        `تم توليد وتنزيل ملف العرض (${res.fileName}) بصيغة OOXML PPTX حقيقية بنصوص وعناصر قابلة للتحرير في PowerPoint!`
      );
    } catch (err: any) {
      setFeedback(err.message);
    } finally {
      setExporting(false);
    }
  };

  const moveSlide = (idx: number, dir: -1 | 1) => {
    const target = idx + dir;
    if (target < 0 || target >= slides.length) return;
    const next = [...slides];
    const tmp = next[idx];
    next[idx] = next[target];
    next[target] = tmp;
    setSlides(next);
    setActiveSlideIdx(target);
  };

  return (
    <div>
      <div className="breadcrumb-line">
        مُعلّم {activeContext?.subject || "المادة"} / مساحة المعلم / العروض التقديمية
      </div>
      <h1 className="page-title">العروض التقديمية</h1>
      <p className="page-subtitle">
        جهّز بنية عرض لمادة {activeContext?.subject || "المادة"} يمكن تحرير محتواه وعناصره النصية في PowerPoint بعد التصدير.
      </p>

      <div className="info-banner">
        <span>
          ⓘ تُصدّر الشرائح كعناصر نصية وأشكال OOXML قابلة للتحرير الفعلي في PowerPoint مع احترام اتجاه اللغة (RTL/LTR).
        </span>
      </div>

      <WorkflowStepper activeStep={7} />

      <div className="warning-banner">
        <span>
          ⚠ معاينة بعد تصحيح التقويم · العرض مرتبط بـ «{currentPlan?.title || "درس تجريبي أ"}»، ومصدر المنهج يُوسم بحسب حالة توثيقه.
        </span>
      </div>

      {/* Top Action Bar matching `العروض التقديمية.png` */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px", marginBottom: "16px" }}>
        <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
          <button type="button" className="btn btn-primary" disabled={exporting} onClick={handleExportPptx}>
            🖥 {exporting ? "جارٍ تجهيز ملف PPTX..." : "إعداد وتنزيل عرض PPTX قابل للتحرير"}
          </button>
          <button type="button" className="btn btn-secondary" onClick={handleSaveSlidesToPlan}>
            ↻ تحديث وحفظ المعاينة
          </button>
          <span className="badge badge-success">{slides.length} شرائح · معاينة حية</span>
        </div>

        <select
          aria-label="اختيار الخطة للعرض التقديمي"
          className="form-select"
          style={{ width: "auto" }}
          value={selectedPlanId}
          onChange={(e) => {
            const found = plans.find((p) => p.id === e.target.value);
            if (found) bindPlanSlides(found);
          }}
        >
          {plans.map((p) => (
            <option key={p.id} value={p.id}>
              {p.title} (v{p.version})
            </option>
          ))}
        </select>
      </div>

      {feedback && (
        <div className="info-banner" style={{ borderColor: "var(--primary-green)", color: "var(--primary-green)" }}>
          <span>✓ {feedback}</span>
        </div>
      )}

      {/* 3-Column Layout matching `العروض التقديمية.png`: Slide Structure (Right) | Slide Preview & Editor (Center) | Presentation Settings (Left) */}
      <div className="three-col-presentation-grid">
        {/* Column 1: Slide Structure List */}
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
            <div>
              <h3 style={{ fontSize: "1.05rem", fontWeight: 800 }}>بنية الشرائح</h3>
              <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>قابلة للترتيب والتحرير</p>
            </div>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ padding: "4px 8px", fontSize: "0.76rem" }}
              onClick={() => {
                const next = [
                  ...slides,
                  { order: slides.length + 1, title: `شريحة ${slides.length + 1}`, content: "محتوى جديد قابل للتحرير." },
                ];
                setSlides(next);
                setActiveSlideIdx(next.length - 1);
              }}
            >
              + شريحة
            </button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {slides.map((s, idx) => {
              const isCurrent = idx === activeSlideIdx;
              return (
                <div
                  key={idx}
                  onClick={() => setActiveSlideIdx(idx)}
                  style={{
                    padding: "10px 12px",
                    borderRadius: "10px",
                    border: isCurrent ? "2px solid var(--primary-green)" : "1px solid var(--border-color)",
                    backgroundColor: isCurrent ? "var(--primary-tint-bg)" : "#fbfcfb",
                    cursor: "pointer",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.72rem", color: "var(--text-muted)", marginBottom: "2px" }}>
                    <span>شريحة {idx + 1}</span>
                    <span>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          moveSlide(idx, -1);
                        }}
                        style={{ border: "none", background: "transparent", cursor: "pointer", paddingInline: "3px" }}
                      >
                        ↑
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          moveSlide(idx, 1);
                        }}
                        style={{ border: "none", background: "transparent", cursor: "pointer", paddingInline: "3px" }}
                      >
                        ↓
                      </button>
                    </span>
                  </div>
                  <div style={{ fontWeight: 800, fontSize: "0.9rem" }}>{s.title}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Column 2: Selected Slide Preview + Editable Content Fields */}
        <div>
          <div className="card">
            <h3 style={{ fontSize: "1.1rem", fontWeight: 800, marginBottom: "2px" }}>معاينة الشريحة المحدّدة</h3>
            <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginBottom: "12px" }}>
              شريحة {activeSlideIdx + 1} من {slides.length} · نموذج تربوي عام لمادة {activeContext?.subject}
            </p>

            {/* Visual Slide Canvas matching `العروض التقديمية.png` */}
            <div
              dir={textDirection}
              style={{
                border: "1px solid var(--border-color)",
                borderRadius: "12px",
                padding: "22px",
                backgroundColor: "#ffffff",
                minHeight: "230px",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  paddingBottom: "8px",
                  borderBottom: "2px solid var(--primary-green)",
                  fontSize: "0.78rem",
                  color: "var(--primary-green)",
                  fontWeight: 700,
                }}
              >
                <span>
                  مُعلّم {activeContext?.subject} · {presTitle}
                </span>
                <span>
                  0{activeSlideIdx + 1} / 0{slides.length}
                </span>
              </div>

              <div style={{ marginBlock: "16px" }}>
                <h2 style={{ fontSize: "1.5rem", fontWeight: 800, marginBottom: "8px" }}>{activeSlide.title}</h2>
                <p style={{ fontSize: "0.92rem", color: "var(--text-secondary)", whiteSpace: "pre-line", marginBottom: "12px" }}>
                  {activeSlide.content?.split("\n")[0] || ""}
                </p>
                <div
                  style={{
                    padding: "12px 16px",
                    borderRadius: "10px",
                    backgroundColor: "var(--primary-tint-bg)",
                    color: "var(--primary-green)",
                    fontWeight: 800,
                    fontSize: "0.95rem",
                  }}
                >
                  {activeSlide.content?.split("\n").slice(1).join(" · ") || "ما سبب اختيارك لهذه الخطوة؟"}
                </div>
              </div>

              <div style={{ fontSize: "0.74rem", color: "var(--warning-text)" }}>
                {currentPlan?.provenanceLabel || "محتوى تجريبي — غير موثّق · لا يحتوي على مسألة رسمية مختلقة"}
              </div>
            </div>
          </div>

          <div className="card">
            <h3 style={{ fontSize: "1.05rem", fontWeight: 800, marginBottom: "2px" }}>تحرير محتوى الشريحة</h3>
            <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginBottom: "12px" }}>
              حقول نصية تتحول إلى أشكال وعناصر نصية قابلة للتحرير في ملف PPTX المصدّر
            </p>

            <div className="form-group">
              <label className="form-label">العنوان</label>
              <input
                className="form-input"
                value={activeSlide.title || ""}
                onChange={(e) => {
                  const next = [...slides];
                  next[activeSlideIdx] = { ...next[activeSlideIdx], title: e.target.value };
                  setSlides(next);
                }}
              />
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">المحتوى · نص قابل للتحرير</label>
              <textarea
                className="form-textarea"
                value={activeSlide.content || ""}
                onChange={(e) => {
                  const next = [...slides];
                  next[activeSlideIdx] = { ...next[activeSlideIdx], content: e.target.value };
                  setSlides(next);
                }}
              />
            </div>
          </div>
        </div>

        {/* Column 3: Presentation Settings matching `العروض التقديمية.png` */}
        <div className="card">
          <h3 style={{ fontSize: "1.1rem", fontWeight: 800, marginBottom: "12px" }}>إعدادات العرض</h3>

          <div className="form-group">
            <label className="form-label">عنوان العرض</label>
            <input
              className="form-input"
              value={presTitle}
              onChange={(e) => setPresTitle(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">عدد الشرائح</label>
            <input className="form-input" readOnly value={`${slides.length} شرائح`} />
          </div>

          <div className="form-group">
            <label className="form-label">اتجاه النص</label>
            <select
              className="form-select"
              value={textDirection}
              onChange={(e) => setTextDirection(e.target.value)}
            >
              <option value="rtl">العربية · من اليمين إلى اليسار (RTL)</option>
              <option value="ltr">من اليسار إلى اليمين (LTR)</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">تخطيط الشريحة</label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
              <button
                type="button"
                className={`btn ${layoutStyle === "title_and_content" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setLayoutStyle("title_and_content")}
                style={{ padding: "8px", fontSize: "0.8rem" }}
              >
                عنوان ومحتوى
              </button>
              <button
                type="button"
                className={`btn ${layoutStyle === "comparison" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setLayoutStyle("comparison")}
                style={{ padding: "8px", fontSize: "0.8rem" }}
              >
                مقارنة
              </button>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">الوسائل المصاحبة</label>
            <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginBottom: "8px" }}>
              {(activeContext?.selectedTools || []).join("، ")}. يمكن استخدام الشرائح كمرجع تحضير إذا لم يتوفر جهاز عرض.
            </p>
            <span className="badge badge-success">محتوى مقصود للتحرير</span>
          </div>

          <p style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
            تُحفظ النصوص وعناصر المحتوى في ملف PPTX كأشكال نصية قابلة للتحرير الكامل، وليست صورًا مسطحة.
          </p>
        </div>
      </div>

      <div className="info-banner">
        <span>
          ⓘ النصوص التربوية أماكن مخصّصة لمحتوى يراجعه المعلم. عند وجود معادلات رياضية تُفصل باتجاه LTR مستقل.
        </span>
      </div>

      <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
        <Link href="/export-package" className="btn btn-primary" onClick={handleSaveSlidesToPlan}>
          ← إضافة العرض إلى الحزمة والتصدير
        </Link>
        <button type="button" className="btn btn-secondary" onClick={handleSaveSlidesToPlan}>
          حفظ إعدادات العرض
        </button>
      </div>
    </div>
  );
}

