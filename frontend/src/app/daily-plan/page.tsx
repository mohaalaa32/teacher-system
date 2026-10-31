"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useTeacherApp, WorkflowStepper } from "../../components/AppShell";

const SUBJECT_SUGGESTIONS = [
  {
    title: "اطلب تفسير الاستدلال",
    desc: "على السبورة: اطلب من الطالب شرح سبب اختيار كل خطوة أو دليل، لا النتيجة فقط.",
    phaseTarget: 2,
  },
  {
    title: "ناقش تصوّرًا شائعًا",
    desc: "بالبطاقات: اجمع تفسيرات الطلاب وناقش اختلافها دون افتراض خطأ مسبق بعينه.",
    phaseTarget: 3,
  },
  {
    title: "استخدم تمثيلًا بصريًا أو خريطة مفاهيم",
    desc: "بالسبورة والمسطرة والألوان: مثّل الفكرة التي يختارها المعلم بعد مراجعة المصدر.",
    phaseTarget: 1,
  },
  {
    title: "قارن بين استراتيجيتين أو وجهتي نظر",
    desc: "بالأقلام الملوّنة: ميّز خطوات كل طريقة ثم ناقش أوجه التشابه والاختلاف.",
    phaseTarget: 3,
  },
];

export default function DailyPlanPage() {
  const { activeContext, activeContextId, apiFetch } = useTeacherApp();
  const [plans, setPlans] = useState<any[]>([]);
  const [lessons, setLessons] = useState<any[]>([]);
  const [templates, setTemplates] = useState<any[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<string>("");
  const [feedback, setFeedback] = useState<string>("");
  const [exportingFmt, setExportingFmt] = useState<string>("");

  // Editable Plan Fields
  const [title, setTitle] = useState<string>("درس تجريبي أ");
  const [primaryLessonId, setPrimaryLessonId] = useState<string>("");
  const [secondaryLessonId, setSecondaryLessonId] = useState<string>("");
  const [lessonsCount, setLessonsCount] = useState<number>(1);
  const [periodsCount, setPeriodsCount] = useState<number>(1);
  const [periodMinutes, setPeriodMinutes] = useState<number>(45);
  const [objectivesText, setObjectivesText] = useState<string>("");
  const [priorKnowledge, setPriorKnowledge] = useState<string>("");
  const [phases, setPhases] = useState<any[]>([]);
  const [formativeAssessment, setFormativeAssessment] = useState<string>("");
  const [differentiation, setDifferentiation] = useState<string>("");
  const [homework, setHomework] = useState<string>("");
  const [homeEnrichmentMinutes, setHomeEnrichmentMinutes] = useState<number>(15);
  const [planVersion, setPlanVersion] = useState<number>(1);
  const [planStatus, setPlanStatus] = useState<string>("draft");

  const loadData = async (keepPlanId?: string) => {
    try {
      const [pRes, lRes, tRes] = await Promise.all([
        apiFetch(`/api/plans?contextId=${encodeURIComponent(activeContextId)}&planType=daily`),
        apiFetch(`/api/lessons?contextId=${encodeURIComponent(activeContextId)}`),
        apiFetch(`/api/templates?contextId=${encodeURIComponent(activeContextId)}`),
      ]);
      const pList = pRes.items || [];
      setPlans(pList);
      setLessons(lRes.items || []);
      setTemplates(tRes.items || []);

      const targetId = keepPlanId || selectedPlanId || "pln_daily_demo_a";
      const found = pList.find((x: any) => x.id === targetId) || pList[0];
      if (found) {
        bindPlanToForm(found);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const bindPlanToForm = (pln: any) => {
    setSelectedPlanId(pln.id);
    setTitle(pln.title || "خطة يومية");
    setPrimaryLessonId(pln.primaryLessonId || "");
    setSecondaryLessonId(pln.secondaryLessonId || "");
    setLessonsCount(pln.lessonsCount || 1);
    setPeriodsCount(pln.periodsCount || 1);
    setPeriodMinutes(pln.periodMinutes || 45);
    setObjectivesText((pln.objectives || []).join("\n"));
    setPriorKnowledge(pln.priorKnowledge || "");
    setPhases(pln.phases || []);
    setFormativeAssessment(pln.formativeAssessment || "");
    setDifferentiation(pln.differentiation || "");
    setHomework(pln.homework || "");
    setHomeEnrichmentMinutes(pln.homeEnrichmentMinutes || 0);
    setPlanVersion(pln.version || 1);
    setPlanStatus(pln.status || "draft");
  };

  useEffect(() => {
    if (activeContextId) loadData();
  }, [activeContextId]);

  const totalAllocated = periodsCount * periodMinutes;
  const inClassSum = phases
    .filter((p) => !p.isHomeEnrichment)
    .reduce((acc, p) => acc + (Number(p.minutes) || 0), 0);
  const timeDiff = totalAllocated - inClassSum;

  const handleApplyTemplate = (tplId: string) => {
    const tpl = templates.find((t) => t.id === tplId);
    if (!tpl) return;
    setPeriodsCount(tpl.periodsCount || 1);
    setPeriodMinutes(tpl.periodMinutes || 45);
    setPhases(JSON.parse(JSON.stringify(tpl.phases || [])));
    setFeedback(`تم تطبيق القالب «${tpl.name}» — يمكنك تحرير أسماء المراحل ومحتواها وأزمنتها بحرية.`);
  };

  const handleSaveTemplateFromCurrent = async () => {
    const customName = prompt("أدخل اسم القالب الجديد لحفظه ضمن هذا السياق:", `قالب مخصص — ${activeContext?.subject}`);
    if (!customName) return;
    try {
      await apiFetch("/api/templates", {
        method: "POST",
        body: JSON.stringify({
          contextId: activeContextId,
          name: customName,
          description: "قالب مراحل مخصص من المعلم",
          isDefault: false,
          periodsCount,
          periodMinutes,
          phases,
        }),
      });
      setFeedback(`تم حفظ القالب «${customName}» بنجاح لإعادة استخدامه.`);
      await loadData(selectedPlanId);
    } catch (err: any) {
      setFeedback(err.message);
    }
  };

  const handleSaveDraft = async () => {
    const currentPlan = plans.find((p) => p.id === selectedPlanId);
    const payload = {
      contextId: activeContextId,
      sourceId: currentPlan?.sourceId || null,
      primaryLessonId: primaryLessonId || null,
      secondaryLessonId: lessonsCount === 2 ? secondaryLessonId || null : null,
      title,
      planType: "daily",
      teacherName: activeContext?.teacherName || "أحمد علي",
      schoolName: activeContext?.schoolName || "",
      sectionName: activeContext?.sectionName || "الشعبة أ",
      planningDate: activeContext?.planningDate || "2026-10-11",
      lessonsCount,
      periodsCount,
      periodMinutes,
      objectives: objectivesText
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean),
      priorKnowledge,
      teacherRole: currentPlan?.teacherRole || "",
      studentRole: currentPlan?.studentRole || "",
      teachingTools: activeContext?.selectedTools || ["سبورة", "أقلام ملوّنة"],
      phases,
      formativeAssessment,
      differentiation,
      homework,
      homeEnrichmentMinutes: Number(homeEnrichmentMinutes) || 0,
      referencesNote: currentPlan?.referencesNote || "",
      planningNotes: currentPlan?.planningNotes || "",
      subjectItems: currentPlan?.subjectItems || [],
      scheduleDays: [],
      slides: currentPlan?.slides || [],
      presentationSettings: currentPlan?.presentationSettings || {},
      contentOrigin: currentPlan?.contentOrigin || "authored_example",
      expectedVersion: planVersion,
    };

    try {
      if (selectedPlanId) {
        const updated = await apiFetch(`/api/plans/${selectedPlanId}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
        setFeedback(`تم حفظ المسودة (الإصدار v${updated.version}) وفحصها تلقائيًا.`);
        await loadData(updated.id);
      } else {
        const created = await apiFetch("/api/plans", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        setFeedback("تم إنشاء وحفظ الخطة اليومية الجديدة.");
        await loadData(created.id);
      }
    } catch (err: any) {
      setFeedback(`خطأ أثناء الحفظ: ${err.message}`);
    }
  };

  const handleQuickExport = async (fmt: "docx" | "pdf") => {
    if (!selectedPlanId) return;
    setExportingFmt(fmt);
    try {
      await handleSaveDraft();
      const res = await apiFetch("/api/exports", {
        method: "POST",
        body: JSON.stringify({
          contextId: activeContextId,
          planId: selectedPlanId,
          exportFormat: fmt,
        }),
      });
      window.open(res.downloadUrl, "_blank");
      setFeedback(`تم توليد وتنزيل ملف ${fmt.toUpperCase()} الحقيقي بنجاح.`);
    } catch (err: any) {
      setFeedback(err.message);
    } finally {
      setExportingFmt("");
    }
  };

  const insertSuggestion = (sug: (typeof SUBJECT_SUGGESTIONS)[0]) => {
    const next = [...phases];
    const targetIdx = Math.min(sug.phaseTarget, next.length - 1);
    if (targetIdx >= 0 && next[targetIdx]) {
      next[targetIdx] = {
        ...next[targetIdx],
        teacherActivity: `${next[targetIdx].teacherActivity} — ${sug.title}: ${sug.desc}`.trim(),
      };
      setPhases(next);
      setFeedback(`تم إدراج المقترح «${sug.title}» في المرحلة رقم ${targetIdx + 1} للمراجعة.`);
    }
  };

  return (
    <div>
      <div className="breadcrumb-line">
        مُعلّم {activeContext?.subject || "المادة"} / مساحة المعلم / الخطة اليومية
      </div>
      <h1 className="page-title">الخطة اليومية</h1>
      <p className="page-subtitle">
        مسودة قابلة للتحرير لـ «{title}». راجع الحقول المطلوبة وتوازن الزمن قبل إعداد المخرجات.
      </p>

      <div className="info-banner">
        <span>
          ⓘ تدعم الخطة درسًا أو درسين، وحصة واحدة ({periodMinutes} د) أو حصتين ({periodMinutes * 2} د)، مع قوالب مراحل قابلة للتخصيص.
        </span>
      </div>

      <WorkflowStepper activeStep={4} />

      {/* Top Action Bar matching `الخطة اليومية.png` */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "10px",
          marginBottom: "14px",
        }}
      >
        <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
          <Link href="/review" className="btn btn-primary">
            ✓ مراجعة الخطة
          </Link>
          <button type="button" className="btn btn-secondary" onClick={handleSaveDraft}>
            حفظ مسودة · قاعدة البيانات
          </button>
          <span className={`badge ${!formativeAssessment.trim() || timeDiff !== 0 ? "badge-warning" : "badge-success"}`}>
            {!formativeAssessment.trim()
              ? "مسودة تجريبية · تقويم ناقص"
              : timeDiff !== 0
              ? `تعارض وقت (${inClassSum}/${totalAllocated} د)`
              : `مكتملة الأركان · الإصدار v${planVersion}`}
          </span>
        </div>

        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <select
            aria-label="اختيار خطة يومية محفوظة"
            className="form-select"
            style={{ width: "auto" }}
            value={selectedPlanId}
            onChange={(e) => {
              const found = plans.find((p) => p.id === e.target.value);
              if (found) bindPlanToForm(found);
            }}
          >
            {plans.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title} (v{p.version})
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="warning-banner">
        <span>
          ⚠ سجل منهج تجريبي · تجريبي — غير موثّق. جميع صياغات الخطة أدناه أمثلة يحرّرها المعلم؛ ليست نصوصًا أو تمارين من كتاب رسمي.
        </span>
      </div>

      {feedback && (
        <div className="info-banner" style={{ borderColor: "var(--primary-green)", color: "var(--primary-green)" }}>
          <span>✓ {feedback}</span>
        </div>
      )}

      {/* Main Split matching `الخطة اليومية.png`: Plan Editor Cards (2/3) & Subject Suggestions Sidebar (1/3) */}
      <div className="main-split-grid">
        <div>
          {/* Card 1: Plan Header & Objectives */}
          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px", flexWrap: "wrap", gap: "8px" }}>
              <div>
                <h3 style={{ fontSize: "1.15rem", fontWeight: 800 }}>بطاقة الخطة</h3>
                <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                  {activeContext?.teacherName || "أحمد علي"} | {activeContext?.sectionName || "الشعبة أ"} |{" "}
                  {activeContext?.planningDate || "2026-10-11"} | {totalAllocated} دقيقة ({periodsCount} حصة)
                </p>
              </div>
              <span className="badge badge-success">{title}</span>
            </div>

            {/* Support 1 or 2 Lessons and 1 or 2 Periods (Req #5) */}
            <div className="stats-grid-4" style={{ marginBottom: "12px" }}>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">عدد الدروس</label>
                <select
                  className="form-select"
                  value={lessonsCount}
                  onChange={(e) => setLessonsCount(Number(e.target.value))}
                >
                  <option value={1}>درس واحد</option>
                  <option value={2}>درسان في الخطة</option>
                </select>
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">عدد الحصص</label>
                <select
                  className="form-select"
                  value={periodsCount}
                  onChange={(e) => setPeriodsCount(Number(e.target.value))}
                >
                  <option value={1}>حصة واحدة ({periodMinutes} د)</option>
                  <option value={2}>حصتان ({periodMinutes * 2} د)</option>
                </select>
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">مدة الحصة (دقيقة)</label>
                <input
                  type="number"
                  min={10}
                  max={180}
                  className="form-input"
                  value={periodMinutes}
                  onChange={(e) => setPeriodMinutes(Math.max(5, Number(e.target.value) || 45))}
                />
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">الدرس الثاني (إن وُجد)</label>
                <select
                  className="form-select"
                  disabled={lessonsCount < 2}
                  value={secondaryLessonId}
                  onChange={(e) => setSecondaryLessonId(e.target.value)}
                >
                  <option value="">— اختر درسًا ثانيًا —</option>
                  {lessons.map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.title}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">أهداف التعلّم · صياغة قابلة للتحرير (كل سطر هدف)</label>
              <textarea
                className="form-textarea"
                value={objectivesText}
                onChange={(e) => setObjectivesText(e.target.value)}
              />
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">التحقّق من المتطلبات والمعارف السابقة</label>
              <input
                className="form-input"
                placeholder="أدخل سؤالًا تشخيصيًا مناسبًا للمحتوى بعد مراجعة المصدر..."
                value={priorKnowledge}
                onChange={(e) => setPriorKnowledge(e.target.value)}
              />
            </div>
          </div>

          {/* Card 2: Customizable Phases Table (`سير الحصة` / 5-Stage Learning Cycle) */}
          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px", marginBottom: "10px" }}>
              <div>
                <h3 style={{ fontSize: "1.15rem", fontWeight: 800 }}>سير الحصة ومراحل القالب القابلة للتخصيص</h3>
                <p style={{ fontSize: "0.78rem", color: timeDiff === 0 ? "var(--primary-green)" : "var(--blocker-text)", fontWeight: 700 }}>
                  مجموع أزمنة المراحل الصفية: {inClassSum} دقيقة من أصل {totalAllocated} دقيقة{" "}
                  {timeDiff === 0
                    ? "✓ (متوازن)"
                    : timeDiff > 0
                    ? `— متبقٍ ${timeDiff} دقيقة`
                    : `— تجاوز بمقدار ${Math.abs(timeDiff)} دقيقة!`}
                </p>
              </div>

              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                <select
                  aria-label="تطبيق قالب مراحل"
                  className="form-select"
                  style={{ width: "auto", fontSize: "0.8rem" }}
                  onChange={(e) => {
                    if (e.target.value) handleApplyTemplate(e.target.value);
                  }}
                  defaultValue=""
                >
                  <option value="" disabled>
                    اختر قالب مراحل جاهز...
                  </option>
                  {templates.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
                <button type="button" className="btn btn-secondary" style={{ padding: "6px 12px", fontSize: "0.78rem" }} onClick={handleSaveTemplateFromCurrent}>
                  حفظ كقالب للسياق
                </button>
              </div>
            </div>

            <div className="table-scroll-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>الحصة</th>
                    <th>المرحلة / العنصر (قابل للتعديل)</th>
                    <th>نشاط ودور المعلم</th>
                    <th>نشاط ودور الطالب</th>
                    <th>الزمن (دقيقة)</th>
                  </tr>
                </thead>
                <tbody>
                  {phases.map((ph, idx) => (
                    <tr key={idx}>
                      <td style={{ width: "85px" }}>
                        <select
                          aria-label={`الحصة للمرحلة ${idx + 1}`}
                          className="form-select"
                          style={{ padding: "5px 6px", fontSize: "0.8rem" }}
                          value={ph.periodNumber || 1}
                          onChange={(e) => {
                            const next = [...phases];
                            next[idx] = { ...next[idx], periodNumber: Number(e.target.value) };
                            setPhases(next);
                          }}
                        >
                          <option value={1}>الأولى</option>
                          <option value={2}>الثانية</option>
                        </select>
                      </td>
                      <td>
                        <input
                          aria-label={`اسم المرحلة ${idx + 1}`}
                          className="form-input"
                          style={{ fontWeight: 700, padding: "6px 8px" }}
                          value={ph.phaseName || ""}
                          onChange={(e) => {
                            const next = [...phases];
                            next[idx] = { ...next[idx], phaseName: e.target.value };
                            setPhases(next);
                          }}
                        />
                      </td>
                      <td>
                        <input
                          aria-label={`نشاط المعلم للمرحلة ${idx + 1}`}
                          className="form-input"
                          style={{ padding: "6px 8px" }}
                          value={ph.teacherActivity || ""}
                          onChange={(e) => {
                            const next = [...phases];
                            next[idx] = { ...next[idx], teacherActivity: e.target.value };
                            setPhases(next);
                          }}
                        />
                      </td>
                      <td>
                        <input
                          aria-label={`نشاط الطالب للمرحلة ${idx + 1}`}
                          className="form-input"
                          style={{ padding: "6px 8px" }}
                          value={ph.studentActivity || ""}
                          onChange={(e) => {
                            const next = [...phases];
                            next[idx] = { ...next[idx], studentActivity: e.target.value };
                            setPhases(next);
                          }}
                        />
                      </td>
                      <td style={{ width: "95px" }}>
                        <input
                          type="number"
                          min={0}
                          max={180}
                          aria-label={`زمن المرحلة ${idx + 1}`}
                          className="form-input"
                          style={{ padding: "6px 8px", color: "var(--primary-green)", fontWeight: 700 }}
                          value={ph.minutes ?? 0}
                          onChange={(e) => {
                            const val = Math.max(0, Number(e.target.value) || 0);
                            const next = [...phases];
                            next[idx] = { ...next[idx], minutes: val };
                            setPhases(next);
                          }}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "10px", flexWrap: "wrap", gap: "8px" }}>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ fontSize: "0.8rem", padding: "6px 12px" }}
                onClick={() =>
                  setPhases([
                    ...phases,
                    {
                      order: phases.length + 1,
                      periodNumber: periodsCount,
                      phaseName: "مرحلة مخصصة جديدة",
                      teacherActivity: "يوجه النشاط",
                      studentActivity: "يتفاعل وينفذ المهمة",
                      minutes: 5,
                      isHomeEnrichment: false,
                    },
                  ])
                }
              >
                + إضافة مرحلة
              </button>
              <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                الإثراء المنزلي ({homeEnrichmentMinutes} دقيقة) يُحسب خارج مجموع وقت الحصة الصفية ({totalAllocated} دقيقة).
              </span>
            </div>
          </div>

          {/* Card 3: Assessment, Differentiation & Homework matching `الخطة اليومية.png` */}
          <div className="card">
            <h3 style={{ fontSize: "1.15rem", fontWeight: 800, marginBottom: "12px" }}>التقويم ومراعاة الفروق</h3>

            <div className="form-group">
              <label className="form-label">التقويم التكويني *</label>
              <textarea
                className={`form-textarea ${!formativeAssessment.trim() ? "error-border" : ""}`}
                placeholder="أدخل طريقة تقويم مرتبطة بالأهداف..."
                value={formativeAssessment}
                onChange={(e) => setFormativeAssessment(e.target.value)}
              />
              {!formativeAssessment.trim() && (
                <div style={{ fontSize: "0.78rem", color: "var(--blocker-text)", marginTop: "4px", fontWeight: 700 }}>
                  مطلوب: أضف طريقة التقويم قبل اكتمال المراجعة واعتماد الخطة.
                </div>
              )}
            </div>

            <div className="form-group">
              <label className="form-label">مراعاة الفروق الفردية (التمايز) · صياغة قابلة للتحرير</label>
              <input
                className="form-input"
                value={differentiation}
                onChange={(e) => setDifferentiation(e.target.value)}
              />
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">الواجب المنزلي والتوسعة · يحرّره المعلم</label>
              <input
                className="form-input"
                placeholder="أدخل مهمة مناسبة بعد مراجعة المصدر؛ لا توجد تمارين رسمية مقترحة هنا..."
                value={homework}
                onChange={(e) => setHomework(e.target.value)}
              />
            </div>
          </div>
        </div>

        {/* Left Column in RTL: Subject Pedagogical Suggestions matching `الخطة اليومية.png` */}
        <div>
          <div className="card">
            <h3 style={{ fontSize: "1.1rem", fontWeight: 800, marginBottom: "2px" }}>
              مقترحات لمادة {activeContext?.subject || "المادة"}
            </h3>
            <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginBottom: "14px" }}>
              مرتبطة بالوسائل المتاحة · للمراجعة والتحرير
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {SUBJECT_SUGGESTIONS.map((sug, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: "14px",
                    borderRadius: "10px",
                    border: "1px solid var(--border-subtle)",
                    backgroundColor: "#fbfcfb",
                  }}
                >
                  <div style={{ fontWeight: 800, fontSize: "0.92rem", marginBottom: "4px" }}>{sug.title}</div>
                  <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: "10px" }}>
                    {sug.desc}
                  </p>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ padding: "5px 12px", fontSize: "0.8rem" }}
                    onClick={() => insertSuggestion(sug)}
                  >
                    إدراج بعد المراجعة
                  </button>
                </div>
              ))}
            </div>

            <div
              style={{
                marginTop: "14px",
                padding: "12px",
                borderRadius: "10px",
                backgroundColor: "var(--primary-tint-bg)",
                color: "var(--primary-green)",
                fontSize: "0.8rem",
                fontWeight: 600,
              }}
            >
              ✓ لا جهاز عرض مطلوب. تعتمد المسودة على {(activeContext?.selectedTools || []).join(" و")}.
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Action Bar matching `الخطة اليومية.png` */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <Link href="/review" className="btn btn-primary" onClick={handleSaveDraft}>
            ← انتقل إلى المراجعة النهائية
          </Link>
          <Link href="/five-day-plan" className="btn btn-secondary">
            عرض خطة خمسة أيام
          </Link>
          <Link href="/weekly-plan" className="btn btn-secondary">
            عرض الخطة الأسبوعية
          </Link>
        </div>

        <div style={{ display: "flex", gap: "8px" }}>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={!!exportingFmt}
            onClick={() => handleQuickExport("docx")}
          >
            {exportingFmt === "docx" ? "جارٍ التوليد..." : "تصدير DOCX قابل للتحرير"}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={!!exportingFmt}
            onClick={() => handleQuickExport("pdf")}
          >
            {exportingFmt === "pdf" ? "جارٍ التوليد..." : "تصدير PDF"}
          </button>
        </div>
      </div>
    </div>
  );
}
