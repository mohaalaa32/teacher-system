"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useTeacherApp } from "../../components/AppShell";

export default function SourcesImportPage() {
  const { activeContext, activeContextId, apiFetch } = useTeacherApp();
  const [sources, setSources] = useState<any[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<string>("");
  const [uploading, setUploading] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string>("");

  // Metadata Form State matching `استيراد كتاب المنهج.png`
  const [title, setTitle] = useState<string>("كتاب المنهج");
  const [bookYear, setBookYear] = useState<string>("");
  const [edition, setEdition] = useState<string>("");
  const [sourceUrl, setSourceUrl] = useState<string>("");
  const [reviewerName, setReviewerName] = useState<string>("");
  const [reviewNotes, setReviewNotes] = useState<string>("");
  const [selectedPageIdx, setSelectedPageIdx] = useState<number>(0);
  const [correctedPageText, setCorrectedPageText] = useState<string>("");
  const [printedPageNumber, setPrintedPageNumber] = useState<string>("1");

  const loadSources = async (keepId?: string) => {
    try {
      const res = await apiFetch(`/api/sources?contextId=${encodeURIComponent(activeContextId)}`);
      const list = res.items || [];
      setSources(list);
      const targetId = keepId || selectedSourceId || (list[0] && list[0].id) || "";
      const found = list.find((s: any) => s.id === targetId) || (list.length > 0 ? list[0] : null);
      if (found) {
        bindSource(found);
      } else {
        setSelectedSourceId("");
        setTitle(activeContext?.curriculumName || "كتاب المنهج");
      }
    } catch (e) {
      console.error(e);
    }
  };

  const bindSource = (src: any) => {
    setSelectedSourceId(src.id);
    setTitle(src.title || "سجل منهج");
    setBookYear(src.bookYear || "");
    setEdition(src.edition || "");
    setSourceUrl(src.sourceUrl || "");
    setReviewerName(src.reviewerName || "");
    setReviewNotes(src.reviewNotes || "");
    setSelectedPageIdx(0);
    if (src.pages && src.pages.length > 0) {
      setCorrectedPageText(src.pages[0].correctedText || src.pages[0].extractedText || "");
      setPrintedPageNumber(src.pages[0].printedPageNumber || "1");
    }
  };

  useEffect(() => {
    if (activeContextId) loadSources();
  }, [activeContextId]);

  const currentSource = sources.find((s) => s.id === selectedSourceId) || null;
  const currentPage = currentSource?.pages?.[selectedPageIdx] || null;

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setErrorMsg("");
    setFeedback("");
    try {
      const fd = new FormData();
      fd.append("contextId", activeContextId);
      fd.append("title", title || file.name);
      fd.append("bookYear", bookYear);
      fd.append("edition", edition);
      fd.append("sourceUrl", sourceUrl);
      fd.append("file", file);

      const created = await apiFetch("/api/sources/upload", {
        method: "POST",
        body: fd,
      });
      setFeedback(
        `تم رفع وفحص توقيع PDF بنجاح (${created.pageCount} صفحات · البصمة SHA-256: ${created.sha256Fingerprint.slice(
          0,
          16
        )}... · الحالة: ${
          created.extractionStatus === "extracted_text" ? "تم استخراج النص" : "يتطلب مراجعة OCR / تفريغًا يدويًا"
        }).`
      );
      await loadSources(created.id);
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleSaveMetadata = async (requestVerification: boolean) => {
    if (!currentSource) return;
    setErrorMsg("");
    setFeedback("");
    try {
      const updated = await apiFetch(`/api/sources/${currentSource.id}`, {
        method: "PUT",
        body: JSON.stringify({
          contextId: activeContextId,
          title,
          bookYear,
          edition,
          sourceUrl,
          isOfficialClaimed: requestVerification,
          officialEvidence: requestVerification ? `البلد: ${activeContext?.country} | الطبعة: ${edition} | الرابط: ${sourceUrl}` : "",
          reviewerName,
          reviewNotes,
          verificationStatus: requestVerification ? "human_verified" : "pending_review",
          indexApproved: requestVerification,
          expectedVersion: currentSource.version,
        }),
      });
      setFeedback(
        requestVerification
          ? `تم اعتماد توثيق المصدر ومراجعته البشرية بواسطة «${updated.reviewerName}»!`
          : "تم حفظ بيانات المصدر في قاعدة البيانات."
      );
      await loadSources(updated.id);
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  const handleSavePageCorrection = async () => {
    if (!currentSource || !currentPage) return;
    try {
      await apiFetch(`/api/sources/${currentSource.id}/pages/${currentPage.id}`, {
        method: "PUT",
        body: JSON.stringify({
          contextId: activeContextId,
          printedPageNumber,
          correctedText: correctedPageText,
          humanReviewed: true,
        }),
      });
      setFeedback(`تم حفظ تصحيح النص ورقم الصفحة المطبوعة (${printedPageNumber}) لصفحة PDF رقم ${currentPage.pdfPageNumber}.`);
      await loadSources(currentSource.id);
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  const canRequestVerification = Boolean(bookYear.trim() && edition.trim() && sourceUrl.trim() && reviewerName.trim());

  return (
    <div>
      <div className="breadcrumb-line">
        مُعلّم {activeContext?.subject || "المادة"} / إدارة المنهج / استيراد كتاب المنهج
      </div>
      <h1 className="page-title">استيراد كتاب المنهج والمصادر</h1>
      <p className="page-subtitle">
        مساحة مسؤول المنهج: رفع ملف PDF، فحص التوقيع الفعلي، معاينة وتصحيح النص المستخرج (OCR)، وتسجيل بيانات المصدر قبل طلب مراجعة مستقلة للتوثيق.
      </p>

      <div className="info-banner">
        <span>
          ⓘ يفحص الخادم توقيع الملف الفعلي (`%PDF-`) والحجم وعدد الصفحات ويحسب بصمة SHA-256، ويفصل بين رقم صفحة PDF ورقم الصفحة المطبوعة.
        </span>
      </div>

      <div style={{ display: "flex", gap: "8px", marginBottom: "14px", flexWrap: "wrap" }}>
        <span
          className={`badge ${
            currentSource?.verificationStatus === "human_verified" ? "badge-success" : "badge-warning"
          }`}
        >
          {currentSource?.verificationStatus === "human_verified" ? "موثّق ومعتمد" : "التحقق معلّق افتراضيًا"}
        </span>
        <span className="badge badge-neutral">سياق الإدارة · {activeContext?.subject} ({activeContext?.grade})</span>
      </div>

      <div className="warning-banner">
        <span>
          ⚠ رفع الملف وحده لا يمنحه توثيقًا تلقائيًا. السنة الدراسية والطبعة ورابط المصدر ونتيجة مراجعة المصدر ضرورية قبل أي اعتماد رسمي.
        </span>
      </div>

      {feedback && (
        <div className="info-banner" style={{ borderColor: "var(--primary-green)", color: "var(--primary-green)" }}>
          <span>✓ {feedback}</span>
        </div>
      )}

      {errorMsg && (
        <div className="blocker-banner">
          <span>⛔ {errorMsg}</span>
        </div>
      )}

      {/* Top Split matching `استيراد كتاب المنهج.png`: PDF Upload Box & Selected File Status */}
      <div className="equal-split-grid">
        <div className="card">
          <h3 style={{ fontSize: "1.1rem", fontWeight: 800, marginBottom: "2px" }}>رفع ملف PDF</h3>
          <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginBottom: "12px" }}>
            {currentSource?.pageCount > 0
              ? `تم رفع ملف (${currentSource.pageCount} صفحات)`
              : "الحالة الابتدائية · ارفع ملف PDF نصي أو ممسوح"}
          </p>

          <div
            style={{
              border: "2px dashed var(--border-color)",
              borderRadius: "12px",
              padding: "28px 18px",
              textAlign: "center",
              backgroundColor: "#fbfcfb",
            }}
          >
            <div style={{ fontSize: "1.8rem", marginBottom: "8px", color: "var(--primary-green)" }}>☁↑</div>
            <div style={{ fontWeight: 800, fontSize: "0.98rem", marginBottom: "4px" }}>
              اسحب ملف الكتاب هنا أو اختر ملفًا
            </div>
            <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginBottom: "14px" }}>
              PDF فقط · يُفحص التوقيع الفعلي (`%PDF-`) ولا تُضاف حالة توثيق تلقائيًا
            </div>
            <label className="btn btn-secondary" style={{ cursor: "pointer" }}>
              {uploading ? "جارٍ رفع وفحص الملف..." : "اختيار ملف PDF حقيقي"}
              <input
                type="file"
                accept=".pdf,application/pdf"
                onChange={handleFileUpload}
                style={{ display: "none" }}
              />
            </label>
          </div>
        </div>

        <div className="card">
          <h3 style={{ fontSize: "1.1rem", fontWeight: 800, marginBottom: "2px" }}>بعد اختيار ملف · بيانات البصمة والاستخراج</h3>
          <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginBottom: "12px" }}>
            {currentSource?.sha256Fingerprint
              ? `بصمة SHA-256: ${currentSource.sha256Fingerprint.slice(0, 24)}...`
              : "ملف توضيحي، لم يُرفع ملف PDF فعلي بعد"}
          </p>

          <div
            style={{
              padding: "16px",
              borderRadius: "12px",
              backgroundColor: "var(--primary-tint-bg)",
              border: "1px solid rgba(23, 107, 82, 0.25)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <div style={{ fontWeight: 800, fontSize: "0.95rem" }}>
                📄 {currentSource?.fileName || "كتاب-تجريبي.pdf"}
              </div>
              <span className="badge badge-neutral">
                {currentSource?.pageCount ? `${currentSource.pageCount} صفحات` : "تجريبي"}
              </span>
            </div>
            <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: "10px" }}>
              حالة الاستخراج:{" "}
              <strong>
                {currentSource?.extractionStatus === "extracted_text"
                  ? "PDF نصي (تم استخراج النص مع رقم الصفحة)"
                  : currentSource?.extractionStatus === "requires_ocr_or_manual"
                  ? "يتطلب OCR / تفريغًا يدويًا"
                  : "لا يوجد ملف مرفوع بعد"}
              </strong>
            </div>
            <span
              className={`badge ${
                currentSource?.verificationStatus === "human_verified" ? "badge-success" : "badge-warning"
              }`}
            >
              {currentSource?.verificationStatus === "human_verified" ? "تم اعتماد التوثيق" : "بانتظار بيانات المصدر والمراجعة"}
            </span>
          </div>
        </div>
      </div>

      {/* Middle Split matching `استيراد كتاب المنهج.png`: Required Source Metadata Form (2/3) & Scope + Review Workflow (1/3) */}
      <div className="main-split-grid">
        <div className="card">
          <h3 style={{ fontSize: "1.15rem", fontWeight: 800, marginBottom: "2px" }}>بيانات المصدر المطلوبة</h3>
          <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: "14px" }}>
            الحقول غير معبّأة عمدًا عند عدم معرفتها؛ لا توجد بيانات كتاب رسمية مفترضة أو مخمّنة
          </p>

          <div className="form-group">
            <label className="form-label">عنوان السجل</label>
            <input
              className="form-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          <div className="equal-split-grid">
            <div className="form-group">
              <label className="form-label">السنة الدراسية / سنة الكتاب *</label>
              <input
                className="form-input"
                placeholder="أدخل السنة بعد مراجعة المصدر..."
                value={bookYear}
                onChange={(e) => setBookYear(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">الطبعة *</label>
              <input
                className="form-input"
                placeholder="أدخل الطبعة كما تظهر في المصدر..."
                value={edition}
                onChange={(e) => setEdition(e.target.value)}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">رابط / مرجع المصدر *</label>
            <input
              className={`form-input ${!sourceUrl.trim() ? "error-border" : ""}`}
              placeholder="أدخل رابط المصدر أو رقم الوثيقة الرسمية الذي سيُراجع..."
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
            />
            {!sourceUrl.trim() && (
              <div style={{ fontSize: "0.75rem", color: "var(--blocker-text)", marginTop: "4px" }}>
                مثال تحقق: رابط المصدر مطلوب؛ لا يمكن طلب المراجعة واعتماد التوثيق بدونه.
              </div>
            )}
          </div>

          <div className="equal-split-grid">
            <div className="form-group">
              <label className="form-label">حالة التحقق · غير قابلة للاعتماد التلقائي</label>
              <input
                className="form-input"
                readOnly
                value={
                  currentSource?.verificationStatus === "human_verified"
                    ? "موثّق — تمت المراجعة البشرية"
                    : "معلّق — يتطلب مراجعة المصدر"
                }
              />
            </div>
            <div className="form-group">
              <label className="form-label">اسم/هوية المراجع *</label>
              <input
                className="form-input"
                placeholder="أدخل اسم المراجع البشري..."
                value={reviewerName}
                onChange={(e) => setReviewerName(e.target.value)}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">ملاحظات التحقق والأدلة</label>
            <textarea
              className="form-textarea"
              placeholder="أدخل ملاحظات مراجعة المصدر والأدلة بعد الفحص..."
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
            />
          </div>

          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
            <button type="button" className="btn btn-secondary" onClick={() => handleSaveMetadata(false)}>
              حفظ بيانات ناقصة (مسودة مصدر)
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={!canRequestVerification}
              title={
                !canRequestVerification
                  ? "أدخل السنة والطبعة ورابط المصدر واسم المراجع لتفعيل الاعتماد"
                  : "اعتماد مراجعة المصدر"
              }
              onClick={() => handleSaveMetadata(true)}
            >
              اعتماد مراجعة المصدر وتوثيق الفهرس
            </button>
          </div>
        </div>

        <div>
          <div className="card">
            <h3 style={{ fontSize: "1.05rem", fontWeight: 800, marginBottom: "10px" }}>نطاق المنهج المعزول</h3>
            <div className="form-group">
              <label className="form-label">المادة</label>
              <input className="form-input" readOnly value={activeContext?.subject || "—"} />
            </div>
            <div className="form-group" style={{ marginBottom: "6px" }}>
              <label className="form-label">الصف والبلد</label>
              <input
                className="form-input"
                readOnly
                value={`${activeContext?.grade || "—"} · ${activeContext?.country || "—"}`}
              />
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              المصدر معزول داخل هذا السياق ولا يختلط بسياقات أخرى.
            </div>
          </div>

          <div className="card">
            <h3 style={{ fontSize: "1.05rem", fontWeight: 800, marginBottom: "10px" }}>مسار مراجعة المصدر</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: "0.86rem" }}>1. إدخال بيانات المصدر</div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>السنة والطبعة والرابط مطلوبة</div>
                </div>
                <span className={`badge ${bookYear && edition && sourceUrl ? "badge-success" : "badge-blocker"}`}>
                  {bookYear && edition && sourceUrl ? "مكتمل" : "ناقص"}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: "0.86rem" }}>2. مراجعة مستقلة</div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>يفحص المراجع المصدر ويكتب ملاحظاته</div>
                </div>
                <span className={`badge ${reviewerName ? "badge-success" : "badge-warning"}`}>
                  {reviewerName ? "مدخل" : "بانتظار"}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: "0.86rem" }}>3. تسجيل نتيجة المراجعة</div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>لا توثيق تلقائيًا بمجرد رفع الملف</div>
                </div>
                <span
                  className={`badge ${
                    currentSource?.verificationStatus === "human_verified" ? "badge-success" : "badge-neutral"
                  }`}
                >
                  {currentSource?.verificationStatus === "human_verified" ? "موثّق" : "معلّق"}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Page Text & OCR Ambiguity Review Section (Req #4.12 & #7) */}
      {currentSource?.pages && currentSource.pages.length > 0 && (
        <div className="card">
          <h3 style={{ fontSize: "1.15rem", fontWeight: 800, marginBottom: "4px" }}>
            معاينة صفحات PDF واستخراج/تصحيح النص وفحص مواضع OCR الملتبسة
          </h3>
          <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: "12px" }}>
            يُحفظ رقم صفحة PDF ورقم الصفحة المطبوعة كلٌّ على حدة، مع تنبيه لمواضع الأعلام والتواريخ والاقتباسات والرموز والكسور.
          </p>

          <div className="equal-split-grid">
            <div className="form-group">
              <label className="form-label">اختر صفحة PDF للمعاينة والتصحيح</label>
              <select
                className="form-select"
                value={selectedPageIdx}
                onChange={(e) => {
                  const idx = Number(e.target.value);
                  setSelectedPageIdx(idx);
                  const pg = currentSource.pages[idx];
                  if (pg) {
                    setCorrectedPageText(pg.correctedText || pg.extractedText || "");
                    setPrintedPageNumber(pg.printedPageNumber || String(pg.pdfPageNumber));
                  }
                }}
              >
                {currentSource.pages.map((pg: any, idx: number) => (
                  <option key={pg.id} value={idx}>
                    صفحة PDF رقم {pg.pdfPageNumber} (الصفحة المطبوعة: {pg.printedPageNumber || "—"}) —{" "}
                    {pg.humanReviewed ? "تمت مراجعتها" : "تحتاج مراجعة"}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">رقم الصفحة المطبوعة المقابل لصفحة PDF #{currentPage?.pdfPageNumber}</label>
              <input
                className="form-input"
                value={printedPageNumber}
                onChange={(e) => setPrintedPageNumber(e.target.value)}
              />
            </div>
          </div>

          {currentPage?.ocrAmbiguities && currentPage.ocrAmbiguities.length > 0 && (
            <div className="warning-banner">
              <span>
                🔎 مواضع OCR تحتاج تدقيق المعلم:{" "}
                {currentPage.ocrAmbiguities.map((a: any) => `${a.type} (${a.snippet}) — ${a.reason}`).join(" | ")}
              </span>
            </div>
          )}

          <div className="form-group">
            <label className="form-label">النص المستخرج القابل للتصحيح البشري قبل اعتماد الفهرس:</label>
            <textarea
              className="form-textarea"
              value={correctedPageText}
              onChange={(e) => setCorrectedPageText(e.target.value)}
              placeholder="النص المستخرج من الصفحة أو التفريغ اليدوي للصفحة الممسوحة..."
            />
          </div>

          <button type="button" className="btn btn-primary" onClick={handleSavePageCorrection}>
            حفظ النص المصحح ورقم الصفحة المطبوعة
          </button>
        </div>
      )}

      {!canRequestVerification && (
        <div className="blocker-banner">
          <span>
            ⛔ لا يمكن إتمام طلب المراجعة الرسمية: السنة الدراسية والطبعة ورابط المصدر واسم المراجع غير مكتملة. تبقى حالة التحقق معلّقة.
          </span>
        </div>
      )}

      {/* Import & Source Review Log Table matching `استيراد كتاب المنهج.png` */}
      <div className="card">
        <h3 style={{ fontSize: "1.15rem", fontWeight: 800, marginBottom: "4px" }}>سجل الاستيراد ومراجعة المصدر</h3>
        <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: "12px" }}>
          سجل تدقيق مصادر السياق النشط ({activeContext?.subject})
        </p>

        <div className="table-scroll-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>السجل</th>
                <th>الملف وبصمته</th>
                <th>بيانات المصدر (سنة / طبعة / رابط)</th>
                <th>حالة التحقق</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((s) => (
                <tr key={s.id} onClick={() => bindSource(s)} style={{ cursor: "pointer" }}>
                  <td style={{ fontWeight: 700 }}>{s.title}</td>
                  <td>
                    {s.fileName || "لم يُختر ملف"}{" "}
                    {s.sha256Fingerprint ? `(${s.sha256Fingerprint.slice(0, 10)}...)` : ""}
                  </td>
                  <td>
                    {s.bookYear || s.edition
                      ? `السنة: ${s.bookYear || "—"} | الطبعة: ${s.edition || "—"}`
                      : "سنة / طبعة / رابط: غير مدخلة"}
                  </td>
                  <td>
                    <span
                      className={`badge ${
                        s.verificationStatus === "human_verified" ? "badge-success" : "badge-warning"
                      }`}
                    >
                      {s.verificationStatus === "human_verified"
                        ? `موثّق (${s.reviewerName})`
                        : "معلّق · غير موثّق"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div style={{ display: "flex", gap: "10px" }}>
        <Link href="/curriculum" className="btn btn-secondary">
          ← العودة إلى المنهج
        </Link>
      </div>
    </div>
  );
}

