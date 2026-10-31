"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useTeacherApp, WorkflowStepper } from "../../components/AppShell";

export default function LessonsPage() {
  const { activeContext, activeContextId, apiFetch } = useTeacherApp();
  const [lessons, setLessons] = useState<any[]>([]);
  const [selectedLessonId, setSelectedLessonId] = useState<string>("");
  const [searchQ, setSearchQ] = useState<string>("");
  const [saveMessage, setSaveMessage] = useState<string>("");

  // Editable form state for selected lesson
  const [title, setTitle] = useState<string>("");
  const [objectives, setObjectives] = useState<string[]>([""]);
  const [priorKnowledge, setPriorKnowledge] = useState<string>("");
  const [evaluationCriteria, setEvaluationCriteria] = useState<string>("");
  const [printedPage, setPrintedPage] = useState<string>("");

  const loadLessons = async (keepId?: string) => {
    try {
      const res = await apiFetch(
        `/api/lessons?contextId=${encodeURIComponent(activeContextId)}&q=${encodeURIComponent(searchQ)}`
      );
      const list = res.items || [];
      setLessons(list);
      const targetId = keepId || selectedLessonId || (list[0] && list[0].id) || "";
      const found = list.find((l: any) => l.id === targetId) || list[0];
      if (found) {
        selectLessonObj(found);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const selectLessonObj = (les: any) => {
    setSelectedLessonId(les.id);
    setTitle(les.title || "");
    setObjectives(les.objectives && les.objectives.length > 0 ? les.objectives : ["", ""]);
    setPriorKnowledge(les.priorKnowledge || "");
    setEvaluationCriteria(les.evaluationCriteria || "");
    setPrintedPage(les.printedPageNumber || "");
  };

  useEffect(() => {
    if (activeContextId) loadLessons();
  }, [activeContextId, searchQ]);

  const currentLesson = lessons.find((l) => l.id === selectedLessonId) || null;

  const handleSaveLesson = async () => {
    if (!currentLesson) return;
    try {
      const updated = await apiFetch(`/api/lessons/${currentLesson.id}`, {
        method: "PUT",
        body: JSON.stringify({
          contextId: activeContextId,
          sourceId: currentLesson.sourceId,
          chapterId: currentLesson.chapterId,
          title: title.trim() || currentLesson.title,
          codeOrOrder: currentLesson.codeOrOrder,
          pdfPageNumber: currentLesson.pdfPageNumber,
          printedPageNumber: printedPage,
          contentOrigin: printedPage ? "documented_source" : "authored_example",
          objectives: objectives.filter((o) => o.trim() !== ""),
          priorKnowledge,
          activities: currentLesson.activities || [],
          questionsAndSolutions: currentLesson.questionsAndSolutions || [],
          evaluationCriteria,
          keyTermsOrQuotes: currentLesson.keyTermsOrQuotes || [],
          expectedVersion: currentLesson.version,
        }),
      });
      setSaveMessage("تم حفظ تعديلات الدرس في قاعدة البيانات بنجاح (يستمر بعد إعادة التحميل).");
      await loadLessons(updated.id);
    } catch (err: any) {
      setSaveMessage(`خطأ: ${err.message}`);
    }
  };

  const handleCreateNewLesson = async () => {
    try {
      const created = await apiFetch("/api/lessons", {
        method: "POST",
        body: JSON.stringify({
          contextId: activeContextId,
          title: `درس جديد ${lessons.length + 1}`,
          codeOrOrder: String(lessons.length + 1),
          objectives: ["أن يحقق المتعلم الهدف التعليمي الأول للدرس."],
          priorKnowledge: "مراجعة المتطلبات السابقة للدرس.",
          evaluationCriteria: "معيار تقييم واضح ومرتبط بالهدف.",
        }),
      });
      setSaveMessage("تم إنشاء درس جديد في السياق الحالي.");
      await loadLessons(created.id);
    } catch (err: any) {
      setSaveMessage(err.message);
    }
  };

  const handleDuplicateLesson = async () => {
    if (!currentLesson) return;
    try {
      const copied = await apiFetch(
        `/api/lessons/${currentLesson.id}/duplicate?contextId=${encodeURIComponent(activeContextId)}`,
        { method: "POST" }
      );
      setSaveMessage(`تم نسخ الدرس إلى «${copied.title}».`);
      await loadLessons(copied.id);
    } catch (err: any) {
      setSaveMessage(err.message);
    }
  };

  return (
    <div>
      <div className="breadcrumb-line">
        مُعلّم {activeContext?.subject || "المادة"} / مساحة المعلم / اختيار الدرس
      </div>
      <h1 className="page-title">اختيار الدرس</h1>
      <p className="page-subtitle">
        حدّد درسًا من السجل، ثم خصّص أهدافه ومعارفه السابقة ومعايير تقويمه قبل اختيار الوسائل.
      </p>

      <div className="info-banner">
        <span>
          ⓘ يمكنك إنشاء درس جديد، أو تعديل الدرس الحالي، أو نسخه، ويُحفظ التعديل مباشرة في قاعدة بيانات FastAPI.
        </span>
      </div>

      <WorkflowStepper activeStep={2} />

      <div className="warning-banner">
        <span>
          ⚠ سجل منهج تجريبي · {currentLesson?.provenanceLabel || "مثال توضيحي غير موثق من الكتاب"}. لا توجد أرقام فصول أو تمارين رسمية مختلقة.
        </span>
      </div>

      {saveMessage && (
        <div className="info-banner" style={{ borderColor: "var(--primary-green)", color: "var(--primary-green)" }}>
          <span>✓ {saveMessage}</span>
        </div>
      )}

      {/* Main Split matching `اختيار الدرس.png`: Available Lessons List & Selected Lesson Details */}
      <div className="equal-split-grid">
        {/* Right Column in RTL: Available Lessons */}
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <div>
              <h3 style={{ fontSize: "1.15rem", fontWeight: 800 }}>الدروس المتاحة</h3>
              <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                {lessons.length} سجلات داخل النطاق ({activeContext?.subject})
              </p>
            </div>
            <button type="button" className="btn btn-secondary" onClick={handleCreateNewLesson}>
              + درس جديد
            </button>
          </div>

          <div className="form-group">
            <label className="form-label">البحث عن درس</label>
            <input
              className="form-input"
              placeholder="اكتب اسم الدرس..."
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
            />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {lessons.map((les) => {
              const isSelected = les.id === selectedLessonId;
              return (
                <div
                  key={les.id}
                  onClick={() => selectLessonObj(les)}
                  style={{
                    padding: "14px 16px",
                    borderRadius: "12px",
                    border: isSelected ? "2px solid var(--primary-green)" : "1px solid var(--border-color)",
                    backgroundColor: isSelected ? "var(--primary-tint-bg)" : "#ffffff",
                    cursor: "pointer",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                    <span style={{ fontWeight: 800, fontSize: "1rem" }}>{les.title}</span>
                    <span style={{ color: isSelected ? "var(--primary-green)" : "var(--text-muted)", fontWeight: 700 }}>
                      {isSelected ? "✓ محدّد" : "○"}
                    </span>
                  </div>
                  <div style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginBottom: "8px" }}>
                    سجل منهج تجريبي {les.printedPageNumber ? `· ص ${les.printedPageNumber}` : ""}
                  </div>
                  <span className="badge badge-warning">{les.provenanceLabel}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Left Column in RTL: Selected Lesson Editable Details matching `اختيار الدرس.png` */}
        <div className="card">
          <h3 style={{ fontSize: "1.15rem", fontWeight: 800, marginBottom: "2px" }}>تفاصيل الدرس المحدّد</h3>
          <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginBottom: "12px" }}>
            أهداف ومعارف سابقة ومعايير تقويم قابلة للتحرير والحفظ الدائم
          </p>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <span className="badge badge-warning">
              {currentLesson?.provenanceLabel || "تجريبي — غير موثّق"}
            </span>
            <button type="button" className="btn btn-secondary" onClick={handleDuplicateLesson}>
              نسخ الدرس
            </button>
          </div>

          <div className="form-group">
            <label className="form-label">عنوان الدرس</label>
            <input
              className="form-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          <div className="equal-split-grid">
            <div className="form-group">
              <label className="form-label">نطاق الدرس</label>
              <input
                className="form-input"
                readOnly
                value={`${activeContext?.subject || "—"} · ${activeContext?.grade || "—"} · ${activeContext?.country || "—"}`}
              />
            </div>
            <div className="form-group">
              <label className="form-label">رقم الصفحة المطبوعة (اختياري)</label>
              <input
                className="form-input"
                placeholder="اربط برقم الصفحة بعد مراجعة الكتاب"
                value={printedPage}
                onChange={(e) => setPrintedPage(e.target.value)}
              />
            </div>
          </div>

          {objectives.map((obj, idx) => (
            <div className="form-group" key={idx}>
              <label className="form-label">الهدف التعليمي #{idx + 1} · صياغة قابلة للتحرير</label>
              <textarea
                className="form-textarea"
                style={{ minHeight: "66px" }}
                value={obj}
                onChange={(e) => {
                  const next = [...objectives];
                  next[idx] = e.target.value;
                  setObjectives(next);
                }}
              />
            </div>
          ))}

          <div className="form-group">
            <label className="form-label">المتطلبات والمعارف السابقة</label>
            <input
              className="form-input"
              value={priorKnowledge}
              onChange={(e) => setPriorKnowledge(e.target.value)}
              placeholder="أدخل المعارف السابقة المطلوبة للدرس..."
            />
          </div>

          <div className="form-group">
            <label className="form-label">معايير التقويم وأدلة التعلم الملائمة للمادة</label>
            <input
              className="form-input"
              value={evaluationCriteria}
              onChange={(e) => setEvaluationCriteria(e.target.value)}
              placeholder="محك تقييم أو معيار تحقق الهدف..."
            />
          </div>

          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginTop: "12px" }}>
            <button type="button" className="btn btn-primary" onClick={handleSaveLesson}>
              حفظ تفاصيل الدرس
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setObjectives([...objectives, "هدف تعليمي جديد قابل للتحرير."])}
            >
              + إضافة هدف
            </button>
          </div>

          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "10px" }}>
            هذه الأهداف يحررها المعلم ويكيفها وفق المادة؛ لا تُعرض كنصوص مقتبسة رسميًا إلا بعد توثيق المصدر.
          </div>
        </div>
      </div>

      <div className="card">
        <h3 style={{ fontSize: "1.05rem", fontWeight: 800, marginBottom: "4px" }}>الخطوة التالية: الوسائل التعليمية وأدوات المدرس</h3>
        <p style={{ fontSize: "0.84rem", color: "var(--text-secondary)" }}>
          اختر ما يتوفر فعلًا في الصف، واستخدم أدوات المادة التخصصية (تحليل نص، خط زمني، تجربة، أو مدقق المسائل الرياضية).
        </p>
      </div>

      <div style={{ display: "flex", gap: "10px" }}>
        <Link href="/tools" className="btn btn-primary">
          ← متابعة إلى الوسائل التعليمية
        </Link>
        <Link href="/curriculum" className="btn btn-secondary">
          تغيير المنهج
        </Link>
      </div>
    </div>
  );
}
