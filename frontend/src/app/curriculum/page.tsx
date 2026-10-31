"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useTeacherApp, WorkflowStepper } from "../../components/AppShell";

export default function CurriculumPage() {
  const { activeContext, activeContextId, apiFetch } = useTeacherApp();
  const [sources, setSources] = useState<any[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [newChapterTitle, setNewChapterTitle] = useState<string>("");
  const [newChapterPage, setNewChapterPage] = useState<string>("");
  const [feedback, setFeedback] = useState<string>("");

  const loadSources = async () => {
    try {
      const res = await apiFetch(`/api/sources?contextId=${encodeURIComponent(activeContextId)}`);
      const items = res.items || [];
      setSources(items);
      if (items.length > 0 && !selectedSourceId) {
        setSelectedSourceId(items[0].id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (activeContextId) loadSources();
  }, [activeContextId]);

  const filteredSources = sources.filter((s) => {
    const matchesQ = !searchQuery.trim() || s.title.includes(searchQuery.trim());
    const matchesStatus = statusFilter === "all" || s.verificationStatus === statusFilter;
    return matchesQ && matchesStatus;
  });

  const selectedSource = sources.find((s) => s.id === selectedSourceId) || filteredSources[0] || null;

  const handleAddChapter = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSource || !newChapterTitle.trim()) return;
    try {
      await apiFetch("/api/chapters", {
        method: "POST",
        body: JSON.stringify({
          contextId: activeContextId,
          sourceId: selectedSource.id,
          title: newChapterTitle.trim(),
          orderIndex: (selectedSource.chapters?.length || 0) + 1,
          pdfStartPage: newChapterPage ? parseInt(newChapterPage, 10) : null,
          printedStartPage: newChapterPage,
          isDocumented: selectedSource.verificationStatus === "human_verified",
        }),
      });
      setNewChapterTitle("");
      setNewChapterPage("");
      setFeedback("تمت إضافة الفصل وربطه بسجل المصدر المحدّد.");
      await loadSources();
    } catch (err: any) {
      setFeedback(err.message);
    }
  };

  return (
    <div>
      <div className="breadcrumb-line">
        مُعلّم {activeContext?.subject || "المادة"} / مساحة المعلم / المنهج
      </div>
      <h1 className="page-title">المنهج</h1>
      <p className="page-subtitle">
        اختر سجل المنهج لبدء التخطيط. يبقى المحتوى تجريبيًا حتى مراجعة مصدره وتوثيق طبعته وسنته.
      </p>

      <div className="info-banner">
        <span>
          ⓘ لا يتم استيراد أي فهرس رسمي وهمي من الذاكرة؛ الفصول والدروس المعروضة إما موثقة من ملف PDF المرفوع أو معلّمة بوضوح كمثال توضيحي.
        </span>
      </div>

      <WorkflowStepper activeStep={1} />

      {/* Search & Status Filter matching `المنهج.png` */}
      <div className="main-split-grid" style={{ marginBottom: "12px" }}>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label">البحث داخل سياق ({activeContext?.subject} · {activeContext?.grade})</label>
          <input
            className="form-input"
            placeholder="ابحث عن سجل منهج..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label">حالة المصدر</label>
          <select
            className="form-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">جميع السجلات المتاحة</option>
            <option value="human_verified">موثّق — مراجعة بشرية معتمدة</option>
            <option value="pending_review">معلّق — يتطلب مراجعة المصدر</option>
          </select>
        </div>
      </div>

      <div className="warning-banner">
        <span>
          ⚠ النطاق الحالي: {activeContext?.subject || "—"} للصف {activeContext?.grade || "—"} في {activeContext?.country || "—"}. اختيار سجل لا يعني توثيقه أو اعتماده رسميًا.
        </span>
      </div>

      {feedback && (
        <div className="info-banner" style={{ borderColor: "var(--primary-green)", color: "var(--primary-green)" }}>
          <span>✓ {feedback}</span>
        </div>
      )}

      {/* Main Split matching `المنهج.png`: Source Cards (Right/Main) & Selected Source Details (Left) */}
      <div className="main-split-grid">
        <div>
          {filteredSources.map((src) => {
            const isSelected = selectedSource?.id === src.id;
            return (
              <div
                key={src.id}
                onClick={() => setSelectedSourceId(src.id)}
                className="card"
                style={{
                  borderColor: isSelected ? "var(--primary-green)" : "var(--border-color)",
                  borderWidth: isSelected ? "2px" : "1px",
                  cursor: "pointer",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "stretch",
                  gap: "18px",
                  flexWrap: "wrap",
                }}
              >
                <div style={{ flex: 1, minWidth: "220px" }}>
                  <div style={{ display: "flex", gap: "8px", marginBottom: "10px", flexWrap: "wrap" }}>
                    <span
                      className={`badge ${
                        src.verificationStatus === "human_verified" ? "badge-success" : "badge-warning"
                      }`}
                    >
                      {src.verificationStatus === "human_verified" ? "موثّق — معتمد" : "تجريبي — غير موثّق"}
                    </span>
                    {isSelected && <span className="badge badge-success">تم الاختيار · حالة مرئية</span>}
                  </div>
                  <h2 style={{ fontSize: "1.3rem", fontWeight: 800, marginBottom: "6px" }}>{src.title}</h2>
                  <p style={{ fontSize: "0.86rem", color: "var(--text-secondary)", marginBottom: "10px" }}>
                    {src.reviewNotes || "سجل مخصّص لتوضيح رحلة التخطيط، وليس نسخة من كتاب رسمي."}
                  </p>
                  <div style={{ fontSize: "0.82rem", fontWeight: 700, marginBottom: "4px" }}>
                    {activeContext?.subject} · {activeContext?.grade} · {activeContext?.country}
                  </div>
                  <div style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                    {src.pageCount > 0
                      ? `ملف PDF مرفوع (${src.pageCount} صفحات) · البصمة: ${src.sha256Fingerprint?.slice(0, 12)}...`
                      : "بيانات المصدر غير مكتملة — بانتظار رفع الكتاب أو اعتماد الفهرس"}
                  </div>
                </div>

                {/* Book Cover Tile matching `المنهج.png` */}
                <div
                  style={{
                    width: "145px",
                    backgroundColor: "var(--sidebar-bg)",
                    color: "#fff",
                    borderRadius: "12px",
                    padding: "18px 14px",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    textAlign: "center",
                  }}
                >
                  <div style={{ fontSize: "1.4rem" }}>📖</div>
                  <div style={{ fontWeight: 800, fontSize: "1rem" }}>{src.title}</div>
                  <div style={{ fontSize: "0.75rem", color: "var(--sidebar-muted)" }}>
                    {activeContext?.grade} · {src.verificationStatus === "human_verified" ? "موثّق" : "غير موثّق"}
                  </div>
                </div>
              </div>
            );
          })}

          {/* What Transfers to Your Plan Card matching `المنهج.png` */}
          <div className="card">
            <h3 style={{ fontSize: "1.1rem", fontWeight: 800, marginBottom: "12px" }}>ما الذي ينتقل إلى خطتك؟</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                <span className="badge badge-success" style={{ padding: "8px" }}>📖</span>
                <div>
                  <div style={{ fontWeight: 700, fontSize: "0.9rem" }}>سياق المنهج المحدّد</div>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                    اسم السجل ونطاقه وحالة التحقق وبصمة المصدر (إن وُجدت).
                  </div>
                </div>
              </div>
              <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                <span className="badge badge-success" style={{ padding: "8px" }}>📄</span>
                <div>
                  <div style={{ fontWeight: 700, fontSize: "0.9rem" }}>دروس وفصول قابلة للتخطيط</div>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                    {selectedSource?.chapters?.length
                      ? `${selectedSource.chapters.length} فصول مسجلة مرتبطة بأرقام الصفحات.`
                      : "لا توجد فصول أو صفحات أو تمارين رسمية مختلقة في هذا النموذج."}
                  </div>
                </div>
              </div>
            </div>

            {/* Chapters List & Add Documented Chapter Form */}
            {selectedSource && (
              <div style={{ marginTop: "16px", paddingTop: "14px", borderTop: "1px solid var(--border-subtle)" }}>
                <h4 style={{ fontSize: "0.92rem", fontWeight: 700, marginBottom: "8px" }}>
                  الفصول المسجلة ضمن هذا المصدر ({selectedSource.chapters?.length || 0})
                </h4>
                {selectedSource.chapters && selectedSource.chapters.length > 0 ? (
                  <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "6px", marginBottom: "12px" }}>
                    {selectedSource.chapters.map((ch: any) => (
                      <li
                        key={ch.id}
                        style={{
                          padding: "8px 12px",
                          background: "#f9fbf9",
                          borderRadius: "8px",
                          border: "1px solid var(--border-subtle)",
                          display: "flex",
                          justifyContent: "space-between",
                          fontSize: "0.84rem",
                        }}
                      >
                        <span>
                          <strong>الفصل {ch.orderIndex}:</strong> {ch.title}{" "}
                          {ch.printedStartPage && `(ص ${ch.printedStartPage})`}
                        </span>
                        <span className={`badge ${ch.isDocumented ? "badge-success" : "badge-warning"}`}>
                          {ch.provenanceLabel}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "10px" }}>
                    لم يُسجّل أي فصل بعد. يمكنك إضافة فصل بعد مراجعة ملف المنهج المرفوع.
                  </p>
                )}

                <form onSubmit={handleAddChapter} style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  <input
                    className="form-input"
                    style={{ flex: 2, minWidth: "180px" }}
                    placeholder="عنوان الفصل (حسب الكتاب أو كمثال معلّم)..."
                    value={newChapterTitle}
                    onChange={(e) => setNewChapterTitle(e.target.value)}
                  />
                  <input
                    className="form-input"
                    style={{ flex: 1, minWidth: "100px" }}
                    placeholder="رقم الصفحة"
                    value={newChapterPage}
                    onChange={(e) => setNewChapterPage(e.target.value)}
                  />
                  <button type="submit" className="btn btn-secondary">
                    + تسجيل فصل
                  </button>
                </form>
              </div>
            )}
          </div>
        </div>

        {/* Selected Record Summary Panel matching `المنهج.png` */}
        <div className="card">
          <h3 style={{ fontSize: "1.1rem", fontWeight: 800, marginBottom: "2px" }}>السجل المحدّد</h3>
          <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginBottom: "12px" }}>
            تفاصيل المصدر قبل المتابعة
          </p>

          <span
            className={`badge ${
              selectedSource?.verificationStatus === "human_verified" ? "badge-success" : "badge-warning"
            }`}
            style={{ marginBottom: "10px" }}
          >
            {selectedSource?.verificationStatus === "human_verified" ? "موثّق — معتمد" : "تجريبي — غير موثّق"}
          </span>

          <div style={{ fontSize: "1.15rem", fontWeight: 800, marginBottom: "14px" }}>
            {selectedSource?.title || "سجل منهج تجريبي"}
          </div>

          <div className="form-group">
            <label className="form-label">المادة والصف</label>
            <input
              className="form-input"
              readOnly
              value={`${activeContext?.subject || "—"} · ${activeContext?.grade || "—"} · ${activeContext?.country || "—"}`}
            />
          </div>

          <div className="equal-split-grid">
            <div className="form-group">
              <label className="form-label">السنة الدراسية</label>
              <input
                className="form-input"
                readOnly
                value={selectedSource?.bookYear || activeContext?.year || "غير مدخلة"}
              />
            </div>
            <div className="form-group">
              <label className="form-label">الطبعة</label>
              <input
                className="form-input"
                readOnly
                value={selectedSource?.edition || activeContext?.edition || "غير مدخلة"}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">رابط المصدر</label>
            <input
              className="form-input"
              readOnly
              value={selectedSource?.sourceUrl || "لم يُضف مصدر"}
            />
            <div style={{ fontSize: "0.74rem", color: "var(--text-muted)", marginTop: "4px" }}>
              مراجعة المصدر مطلوبة قبل الاستخدام الرسمي.
            </div>
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              paddingTop: "10px",
              borderTop: "1px solid var(--border-subtle)",
            }}
          >
            <div>
              <div style={{ fontWeight: 700, fontSize: "0.86rem" }}>حالة التحقق</div>
              <div style={{ fontSize: "0.76rem", color: "var(--text-secondary)" }}>
                {selectedSource?.reviewerName
                  ? `راجعه: ${selectedSource.reviewerName}`
                  : "بانتظار بيانات المصدر ومراجعة مسؤول المنهج"}
              </div>
            </div>
            <span className="badge badge-warning">
              {selectedSource?.verificationStatus === "human_verified" ? "معتمد" : "معلّق"}
            </span>
          </div>
        </div>
      </div>

      {/* Bottom Notice & Action Bar matching `المنهج.png` */}
      <div className="card">
        <h3 style={{ fontSize: "1.05rem", fontWeight: 800, marginBottom: "4px" }}>قبل الاستخدام الرسمي</h3>
        <p style={{ fontSize: "0.84rem", color: "var(--text-secondary)" }}>
          أكمل السنة الدراسية والطبعة ورابط المصدر في مساحة «استيراد كتاب المنهج»، ثم اطلب مراجعة المصدر. تبقى حالة التحقق معلّقة ولا تتغيّر بمجرد اختيار المنهج.
        </p>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
        <div style={{ display: "flex", gap: "10px" }}>
          <Link href="/lessons" className="btn btn-primary">
            ← متابعة إلى اختيار الدرس
          </Link>
          <Link href="/" className="btn btn-secondary">
            العودة إلى لوحة المعلم
          </Link>
        </div>
        <Link href="/sources" className="btn btn-secondary">
          إدارة وتوثيق المصدر (PDF)
        </Link>
      </div>
    </div>
  );
}

