from sqlalchemy.orm import Session
from ..models import EducationalContext, PhaseTemplate, CurriculumSource, Lesson, Plan, PlanVersion, PlanReview
from .audit_service import audit_plan_and_context
import os
import hashlib
import json


def get_default_five_stage_phases(period_minutes: int = 45, periods_count: int = 1):
    """
    Returns the default 5-stage template derived from `photo_2026-10-31_15-58-11.jpg`:
    1. التهيئة
    2. التدريس (الشرح والتفسير)
    3. التدريب
    4. التقويم
    5. التوسعة والإثراء
    """
    scale = periods_count
    return [
        {
            "order": 1,
            "periodNumber": 1,
            "phaseName": "التهيئة",
            "materials": "توقّع نتاجات التعلّم / نشاط استهلالي",
            "sourceRef": "المقرّر / الدليل",
            "executorRole": "المعلّم يهيّئ المتعلّم",
            "teacherActivity": "يطرح سؤالًا أو موقفًا أو نصًا قصيرًا يستدعي المعرفة السابقة",
            "studentActivity": "يستذكر المفاهيم السابقة ويشارك توقعاته للدرس",
            "objective": "تهيئة المتعلّم للتعلّم الجديد",
            "minutes": 5 * scale,
            "isHomeEnrichment": False,
        },
        {
            "order": 2,
            "periodNumber": 1,
            "phaseName": "التدريس (الشرح والتفسير)",
            "materials": "تعلّم · الأمثلة الإضافية · تأكّد من فهمك",
            "sourceRef": "المقرّر / الدليل",
            "executorRole": "المعلّم يشرح وينمذج للمتعلّم بالمشاركة",
            "teacherActivity": "قراءة أو مناقشة أو استكشاف أو تجربة أو تفسير ونمذجة الإجراءات وفق المادة",
            "studentActivity": "يشارك في التفسير ويحل في مرحلة الممارسة الموجّهة",
            "objective": "تدريس المفاهيم وتعميق الفهم وممارسة موجّهة",
            "minutes": 15 * scale,
            "isHomeEnrichment": False,
        },
        {
            "order": 3,
            "periodNumber": 2 if periods_count == 2 else 1,
            "phaseName": "التدريب",
            "materials": "تدرّب وحلّ التمرينات · مسائل حياتيّة · فكّر · اكتب",
            "sourceRef": "المقرّر",
            "executorRole": "المتعلّم يتدرّب (المعلّم مراقب وميسّر)",
            "teacherActivity": "يتابع ممارسة المتعلمين المستقلة ويقدم تمايزًا ودعمًا عند الحاجة",
            "studentActivity": "تطبيق أو كتابة أو تحليل أو ممارسة مستقلة لمدى الطلاقة",
            "objective": "ممارسة مستقلة وقياس الفهم الأعمق",
            "minutes": 12 * scale,
            "isHomeEnrichment": False,
        },
        {
            "order": 4,
            "periodNumber": 2 if periods_count == 2 else 1,
            "phaseName": "التقويم",
            "materials": "مهمة تقويمية / مسائل / محك تقييم",
            "sourceRef": "الدليل أو المعلّم",
            "executorRole": "المعلّم يقوّم مدى تحقّق النتاجات",
            "teacherActivity": "يطبق أداة التقويم التكويني بمعيار تقييم واضح",
            "studentActivity": "يقدم دليلًا على اكتساب نتاجات التعلم",
            "objective": "التحقّق من اكتساب نتاجات التعلّم",
            "minutes": 8 * scale,
            "isHomeEnrichment": False,
        },
        {
            "order": 5,
            "periodNumber": 2 if periods_count == 2 else 1,
            "phaseName": "التوسعة والإثراء",
            "materials": "تدريبات إثرائية أو نقل أثر التعلم",
            "sourceRef": "الدليل أو المعلّم",
            "executorRole": "المتعلّم يتدرّب بمتابعة المعلّم",
            "teacherActivity": "يوجه نشاط التحدي أو البحث أو نقل التعلم لموقف جديد",
            "studentActivity": "ينجز نشاط التوسعة والإثراء لتعميق الطلاقة",
            "objective": "توسيع أو تعميق فهم المتعلّم أو زيادة طلاقته",
            "minutes": max(0, (period_minutes * periods_count) - (40 * scale)),
            "isHomeEnrichment": False,
        },
    ]


def get_interactive_class_flow_phases():
    """
    Returns the 5-row class flow shown in `الخطة اليومية.png`:
    تمهيد (5 د) + تمثيل بصري (8 د) + نشاط موجّه (15 د) + مناقشة (10 د) + ختام وتقويم (7 د) = 45 د.
    """
    return [
        {
            "order": 1,
            "periodNumber": 1,
            "phaseName": "تمهيد",
            "materials": "سبورة، بطاقات",
            "sourceRef": "المعلّم / المقرّر",
            "executorRole": "المعلّم يهيّئ المتعلّم",
            "teacherActivity": "يطرح سؤالًا تشخيصيًا يحرّره لاحقًا",
            "studentActivity": "يشرح المعرفة السابقة",
            "objective": "استدعاء المتطلبات السابقة",
            "minutes": 5,
            "isHomeEnrichment": False,
        },
        {
            "order": 2,
            "periodNumber": 1,
            "phaseName": "تمثيل بصري",
            "materials": "سبورة، أقلام ملوّنة، مسطرة",
            "sourceRef": "المقرّر",
            "executorRole": "المعلّم يعرض وينمذج",
            "teacherActivity": "يعرض فكرة يحدّدها على السبورة",
            "studentActivity": "يلاحظ ويصف التمثيل",
            "objective": "بناء التمثيل البصري للمفهوم",
            "minutes": 8,
            "isHomeEnrichment": False,
        },
        {
            "order": 3,
            "periodNumber": 1,
            "phaseName": "نشاط موجّه",
            "materials": "بطاقات تعليمية",
            "sourceRef": "المقرّر / الدليل",
            "executorRole": "المتعلّم يعمل بتوجيه المعلّم",
            "teacherActivity": "يوجّه مهمة يختار محتواها",
            "studentActivity": "يشرح خطوات التفكير",
            "objective": "ممارسة موجّهة وتفسير الاستدلال",
            "minutes": 15,
            "isHomeEnrichment": False,
        },
        {
            "order": 4,
            "periodNumber": 1,
            "phaseName": "مناقشة",
            "materials": "بطاقات تعليمية، سبورة",
            "sourceRef": "المعلّم",
            "executorRole": "حوار صفي بإشراف المعلّم",
            "teacherActivity": "يقارن استراتيجيات بالبطاقات",
            "studentActivity": "يناقش طريقة زميله",
            "objective": "مقارنة الاستراتيجيات وتصويب التصورات الشائعة",
            "minutes": 10,
            "isHomeEnrichment": False,
        },
        {
            "order": 5,
            "periodNumber": 1,
            "phaseName": "ختام وتقويم",
            "materials": "أداة تقويم تكويني",
            "sourceRef": "المعلّم / الدليل",
            "executorRole": "المعلّم يقوّم المتعلّم",
            "teacherActivity": "يحدّد طريقة التقويم في الحقل أدناه",
            "studentActivity": "يقدّم دليلًا على فهمه",
            "objective": "التحقق من تحقق أهداف الحصة",
            "minutes": 7,
            "isHomeEnrichment": False,
        },
    ]


def ensure_initial_seed_data(db: Session, force: bool = False):
    """
    Seeds demo illustrative data ONLY if explicitly enabled via ENABLE_DEMO_SEED="1" environment variable,
    or when called with force=True in automated test suites.
    By default, the system starts clean and empty so the user can enter their own name and context.
    """
    if not force and os.getenv("ENABLE_DEMO_SEED", "0").lower() not in ("1", "true"):
        return

    existing = db.query(EducationalContext).first()
    if existing:
        return

    # --- Context 1: Illustrative Reference Context ---
    ctx1 = EducationalContext(
        id="ctx_math_iq_demo",
        subject="الرياضيات",
        grade="الصف الأول المتوسط",
        country="العراق",
        curriculum_name="منهج الرياضيات للمرحلة المتوسطة (سجل تجريبي)",
        language="ar",
        year="",  # Left empty intentionally as in screenshot (`غير مدخلة`) instead of guessing!
        edition="",  # Left empty intentionally as in screenshot (`غير مدخلة`) instead of guessing!
        ui_language="ar",
        teacher_name="أحمد علي · معلم تجريبي",
        school_name="مدرسة المتفوقين المتوسطة (نموذج تجريبي)",
        section_name="الشعبة أ",
        planning_date="2026-10-11",
        school_days=["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس"],
        holidays=["الجمعة", "السبت"],
        default_period_Minutes=45,
        default_periods_count=1,
        selected_tools=["سبورة", "أقلام ملوّنة", "مسطرة", "بطاقات تعليمية"],
    )
    db.add(ctx1)
    db.flush()

    tpl_default = PhaseTemplate(
        id="tpl_five_stage_default",
        context_id=ctx1.id,
        name="القالب الافتراضي: دورة التعلّم الخماسية (5 مراحل)",
        description="التهيئة، التدريس (الشرح والتفسير)، التدريب، التقويم، التوسعة والإثراء — قابل للتخصيص لحصة أو حصتين",
        is_default=True,
        periods_count=1,
        period_minutes=45,
        phases=get_default_five_stage_phases(45, 1),
    )
    tpl_two_periods = PhaseTemplate(
        id="tpl_five_stage_two_periods",
        context_id=ctx1.id,
        name="قالب حصتين (90 دقيقة): دورة التعلّم الخماسية (الحصة الأولى والثانية)",
        description="مطابق لجدول الصورة الأولى (الحصة الأولى: التهيئة والتدريس | الحصة الثانية: التدريب والتقويم والتوسعة والإثراء)",
        is_default=False,
        periods_count=2,
        period_minutes=45,
        phases=get_default_five_stage_phases(45, 2),
    )
    tpl_interactive = PhaseTemplate(
        id="tpl_interactive_flow",
        context_id=ctx1.id,
        name="قالب سير الحصة التفاعلي (تمهيد، تمثيل بصري، نشاط موجّه، مناقشة، ختام وتقويم)",
        description="5 + 8 + 15 + 10 + 7 = 45 دقيقة كما في شاشة الخطة اليومية",
        is_default=False,
        periods_count=1,
        period_minutes=45,
        phases=get_interactive_class_flow_phases(),
    )
    db.add_all([tpl_default, tpl_two_periods, tpl_interactive])
    ctx1.active_template_id = tpl_default.id

    src1 = CurriculumSource(
        id="src_demo_unverified",
        context_id=ctx1.id,
        title="سجل منهج تجريبي",
        source_type="unverified_example",
        file_name="كتاب-تجريبي.pdf",
        extraction_status="no_file",
        book_year="",
        edition="",
        source_url="",
        is_official_claimed=False,
        verification_status="pending_review",
        reviewer_name="",
        review_notes="سجل مخصص لتوضيح رحلة التخطيط، وليس نسخة من كتاب رسمي. بانتظار رفع ملف PDF وإدخال السنة والطبعة ورابط المصدر.",
        index_approved=False,
    )
    db.add(src1)
    db.flush()

    les_a = Lesson(
        id="les_demo_a",
        context_id=ctx1.id,
        source_id=src1.id,
        title="درس تجريبي أ",
        code_or_order="1",
        content_origin="authored_example",
        provenance_label="مثال توضيحي غير موثق من الكتاب",
        objectives=[
            "أن يشرح الطالب طريقة تفكيره في نشاط يحدّده المعلم.",
            "أن يقارن بين استراتيجيتين في مهمة يختارها المعلم.",
        ],
        prior_knowledge="مراجعة العمليات الحسابية الأساسية والتمثيل على مستقيم الأعداد.",
        activities=[
            {"title": "اطلب تفسير الاستدلال", "description": "على السبورة: اطلب من الطالب شرح سبب اختيار كل خطوة، لا النتيجة فقط."},
            {"title": "ناقش تصوّرًا شائعًا", "description": "بالبطاقات: اجمع تفسيرات الطلاب وناقش اختلافها دون افتراض خطأ رياضي بعينه."},
        ],
        questions_and_solutions=[
            {"question": "احسب ناتج (15 + 9) / 3 مع توضيح أولويات العمليات", "expression": "(15 + 9) / 3", "solution": "8", "provenance": "مثال توضيحي غير موثق من الكتاب"}
        ],
        evaluation_criteria="قدرة الطالب على تعليل خطوات الحل شفهياً وكتابياً ومقارنة طريقتين للحل.",
        review_status="draft",
    )
    les_b = Lesson(
        id="les_demo_b",
        context_id=ctx1.id,
        source_id=src1.id,
        title="درس تجريبي ب",
        code_or_order="2",
        content_origin="authored_example",
        provenance_label="مثال توضيحي غير موثق من الكتاب",
        objectives=[
            "أن يمثّل الطالب العلاقة الرياضية تمثيلًا بصريًا بالمسطرة والألوان.",
            "أن يتحقق من معقولية الناتج العددي.",
        ],
        prior_knowledge="تمثيل المقادير ومقارنتها.",
        evaluation_criteria="تفسير شفهي لطريقة التفكير والتمثيل البصري.",
        review_status="reviewed",
    )
    les_c = Lesson(
        id="les_demo_c",
        context_id=ctx1.id,
        source_id=src1.id,
        title="درس تجريبي ج",
        code_or_order="3",
        content_origin="authored_example",
        provenance_label="مثال توضيحي غير موثق من الكتاب",
        objectives=[
            "أن يوظف الطالب البطاقات التعليمية لمقارنة استراتيجيتين لحل المسألة.",
        ],
        prior_knowledge="خطوات حل المسألة وتفسير المعطيات.",
        evaluation_criteria="مقارنة استراتيجيتين وتبرير الاختيار.",
        review_status="reviewed",
    )
    db.add_all([les_a, les_b, les_c])
    db.flush()

    # Plan 1: Daily Plan (`درس تجريبي أ`) matching `الخطة اليومية.png` & `مراجعة الخطة.png`
    plan_daily_a = Plan(
        id="pln_daily_demo_a",
        context_id=ctx1.id,
        source_id=src1.id,
        primary_lesson_id=les_a.id,
        title="درس تجريبي أ",
        plan_type="daily",
        status="needs_revision",
        context_snapshot=ctx1.snapshot_dict(),
        teacher_name="أحمد علي · اسم تجريبي",
        school_name="مدرسة المتفوقين المتوسطة (نموذج تجريبي)",
        section_name="الشعبة أ · تجريبية",
        planning_date="2026-10-11",
        lessons_count=1,
        periods_count=1,
        period_minutes=45,
        total_allocated_minutes=45,
        objectives=[
            "أن يشرح الطالب طريقة تفكيره في نشاط يحدّده المعلم.",
            "أن يقارن بين استراتيجيتين في مهمة يختارها المعلم.",
        ],
        prior_knowledge="سؤال تشخيصي لاستدعاء المعرفة السابقة حول ترتيب العمليات.",
        teacher_role="يهيئ المتعلم، يعرض الفكرة على السبورة، يوجه المهمة، ويقارن الاستراتيجيات.",
        student_role="يشرح المعرفة السابقة، يلاحظ التمثيل، يشرح خطوات التفكير، ويناقش طريقة زميله.",
        teaching_tools=["سبورة", "أقلام ملوّنة", "مسطرة", "بطاقات تعليمية"],
        phases=get_interactive_class_flow_phases(),
        formative_assessment="",  # Intentionally empty initially to match `مراجعة الخطة.png` blocker (`طريقة التقويم التكويني مفقودة`)!
        differentiation="قدّم دعمًا بصريًا إضافيًا عند الحاجة، واطلب تبريرًا أعمق من الطلاب المستعدين.",
        homework="مهمة تطبيقية يحددها المعلم بعد مراجعة المصدر (مثال توضيحي غير موثق من الكتاب).",
        home_enrichment_minutes=15,
        references_note="سجل منهج تجريبي — غير موثّق",
        planning_notes="مسودة قابلة للتحرير لدرس تجريبي أ. راجع الحقول المطلوبة قبل إعداد المخرجات.",
        subject_items=[
            {
                "domain": "math",
                "expression": "(15 + 9) / 3",
                "expectedAnswer": "8",
                "claimedAnswer": "8",
                "unit": "",
                "provenance": "مثال توضيحي غير موثق من الكتاب",
            }
        ],
        slides=[
            {"order": 1, "title": "درس تجريبي أ", "content": "معلم رياضيات · الصف الأول المتوسط · العراق\nمحتوى تجريبي — غير موثّق"},
            {"order": 2, "title": "أهداف الحصة", "content": "• أن يشرح الطالب طريقة تفكيره في نشاط يحدّده المعلم.\n• أن يقارن بين استراتيجيتين في مهمة يختارها المعلم."},
            {"order": 3, "title": "ناقش طريقة التفكير", "content": "أدخل مهمة رياضية مناسبة بعد مراجعة المصدر، ثم اطلب من الطلاب تفسير خطواتهم.\nسؤال النقاش: ما سبب اختيارك لهذه الخطوة؟"},
            {"order": 4, "title": "قارن الاستراتيجيات", "content": "بالأقلام الملوّنة والبطاقات: ميّز خطوات كل طريقة ثم ناقش أوجه التشابه والاختلاف."},
            {"order": 5, "title": "تقويم ختامي", "content": "اطلب من الطالب شرح اختياره لإحدى الخطوات، ثم سجّل ملاحظة مرتبطة بالهدف."},
        ],
        content_origin="authored_example",
        provenance_label="مثال توضيحي غير موثق من الكتاب",
    )

    # Plan 2: Completed Daily Plan (`درس تجريبي ب`)
    plan_daily_b = Plan(
        id="pln_daily_demo_b",
        context_id=ctx1.id,
        source_id=src1.id,
        primary_lesson_id=les_b.id,
        title="درس تجريبي ب",
        plan_type="daily",
        status="reviewed",
        context_snapshot=ctx1.snapshot_dict(),
        teacher_name="أحمد علي · اسم تجريبي",
        school_name="مدرسة المتفوقين المتوسطة (نموذج تجريبي)",
        section_name="الشعبة أ · تجريبية",
        planning_date="2026-10-10",
        lessons_count=1,
        periods_count=1,
        period_minutes=45,
        total_allocated_minutes=45,
        objectives=les_b.objectives,
        prior_knowledge=les_b.prior_knowledge,
        teaching_tools=["سبورة", "مسطرة", "أقلام ملوّنة"],
        phases=get_default_five_stage_phases(45, 1),
        formative_assessment="تفسير شفهي لطريقة التفكير والتمثيل البصري على السبورة وفق معيار دقة التمثيل.",
        differentiation="تدرج في الأمثلة البصرية مع نشاط إثرائي للمتمكنين.",
        homework="حل نشاط تدريبي مؤلف (مثال توضيحي غير موثق من الكتاب).",
        content_origin="authored_example",
        provenance_label="مثال توضيحي غير موثق من الكتاب",
    )

    # Plan 3: Five-Day Plan (`خطة خمسة أيام`) matching `خطة خمسة أيام.png`
    plan_five_day = Plan(
        id="pln_five_day_demo",
        context_id=ctx1.id,
        source_id=src1.id,
        primary_lesson_id=les_a.id,
        title="سجل منهج تجريبي — خطة خمسة أيام",
        plan_type="five_day",
        status="draft",
        context_snapshot=ctx1.snapshot_dict(),
        teacher_name="أحمد علي · اسم تجريبي",
        school_name="مدرسة المتفوقين المتوسطة (نموذج تجريبي)",
        section_name="الشعبة أ · معلم تجريبي",
        planning_date="2026-10-09",
        lessons_count=2,
        periods_count=1,
        period_minutes=45,
        total_allocated_minutes=225,
        objectives=[
            "توزيع حصص مرن لخمسة أيام تدريس متميزة بحسب جدول المعلم.",
            "تحقيق أهداف الدروس (أ، ب، ج) ومتابعة التقويم التكويني لكل يوم.",
        ],
        teaching_tools=["سبورة", "أقلام ملوّنة", "مسطرة", "بطاقات تعليمية"],
        formative_assessment="متابعة يومية لأداء المتعلمين وفق معايير كل حصة.",
        schedule_days=[
            {
                "dayNumber": 1,
                "dayName": "الأحد",
                "isHoliday": False,
                "lessonId": "les_demo_a",
                "lessonTitle": "درس تجريبي أ",
                "linkedDailyPlanId": "pln_daily_demo_a",
                "objectives": "شرح طريقة التفكير ومقارنة استراتيجيتين",
                "activities": "سبورة وأقلام ملوّنة وبطاقات",
                "assessment": "",
                "statusBadge": "تقويم ناقص",
                "minutes": 45,
            },
            {
                "dayNumber": 2,
                "dayName": "الاثنين",
                "isHoliday": False,
                "lessonId": "les_demo_b",
                "lessonTitle": "درس تجريبي ب",
                "linkedDailyPlanId": "pln_daily_demo_b",
                "objectives": "تمثيل بصري والتحقق من معقولية الناتج",
                "activities": "سبورة ومسطرة",
                "assessment": "تفسير شفهي لطريقة التفكير · تجريبي",
                "statusBadge": "جاهز للمراجعة",
                "minutes": 45,
            },
            {
                "dayNumber": 3,
                "dayName": "الثلاثاء",
                "isHoliday": False,
                "lessonId": "les_demo_c",
                "lessonTitle": "درس تجريبي ج",
                "linkedDailyPlanId": "",
                "objectives": "مقارنة استراتيجيتين لحل المسألة",
                "activities": "بطاقات وأقلام ملوّنة",
                "assessment": "مقارنة استراتيجيتين · تجريبي",
                "statusBadge": "جاهز للمراجعة",
                "minutes": 45,
            },
            {
                "dayNumber": 4,
                "dayName": "الأربعاء",
                "isHoliday": False,
                "lessonId": "",
                "lessonTitle": "",
                "linkedDailyPlanId": "",
                "objectives": "",
                "activities": "اختر الوسائل بعد تحديد الدرس",
                "assessment": "",
                "statusBadge": "غير مجدول",
                "minutes": 45,
            },
            {
                "dayNumber": 5,
                "dayName": "الخميس",
                "isHoliday": False,
                "lessonId": "",
                "lessonTitle": "",
                "linkedDailyPlanId": "",
                "objectives": "",
                "activities": "اختر الوسائل بعد تحديد الدرس",
                "assessment": "",
                "statusBadge": "غير مجدول",
                "minutes": 45,
            },
        ],
        content_origin="authored_example",
        provenance_label="مثال توضيحي غير موثق من الكتاب",
    )

    # Plan 4: Weekly Plan (`الخطة الأسبوعية`) with actual school days & holidays
    plan_weekly = Plan(
        id="pln_weekly_demo",
        context_id=ctx1.id,
        source_id=src1.id,
        primary_lesson_id=les_b.id,
        secondary_lesson_id=les_c.id,
        title="الخطة الأسبوعية الشاملة — الأسبوع الأول",
        plan_type="weekly",
        status="reviewed",
        context_snapshot=ctx1.snapshot_dict(),
        teacher_name="أحمد علي · اسم تجريبي",
        school_name="مدرسة المتفوقين المتوسطة (نموذج تجريبي)",
        section_name="الشعبة أ",
        planning_date="2026-10-11",
        lessons_count=2,
        periods_count=1,
        period_minutes=45,
        total_allocated_minutes=225,
        objectives=[
            "توزيع دروس الأسبوع على أيام الدوام الفعلية مع مراعاة أيام العطل.",
            "ربط الخطط اليومية بالجدول الأسبوعي والتحقق من مجموع الأزمنة.",
        ],
        teaching_tools=["سبورة", "أقلام ملوّنة", "مسطرة", "بطاقات تعليمية"],
        formative_assessment="بطاقات خروج يومية وملاحظة أداء الطلاب في التدريب المستقل.",
        schedule_days=[
            {"dayName": "الأحد", "isHoliday": False, "lessonTitle": "درس تجريبي أ (الحصة 1)", "linkedDailyPlanId": "pln_daily_demo_a", "activities": "التهيئة والتدريس", "assessment": "سؤال تشخيصي وتطبيق موجه", "minutes": 45},
            {"dayName": "الاثنين", "isHoliday": False, "lessonTitle": "درس تجريبي أ (الحصة 2)", "linkedDailyPlanId": "pln_daily_demo_a", "activities": "التدريب والتقويم", "assessment": "حل مسألة حياتية", "minutes": 45},
            {"dayName": "الثلاثاء", "isHoliday": False, "lessonTitle": "درس تجريبي ب", "linkedDailyPlanId": "pln_daily_demo_b", "activities": "تمثيل بصري بالمسطرة", "assessment": "تفسير شفهي للتمثيل", "minutes": 45},
            {"dayName": "الأربعاء", "isHoliday": False, "lessonTitle": "درس تجريبي ج", "linkedDailyPlanId": "", "activities": "مقارنة استراتيجيتين بالبطاقات", "assessment": "مقارنة مكتوبة", "minutes": 45},
            {"dayName": "الخميس", "isHoliday": False, "lessonTitle": "مراجعة وتوسعة وإثراء", "linkedDailyPlanId": "", "activities": "تدريبات إثرائية شاملة", "assessment": "اختبار قصير تكويني", "minutes": 45},
            {"dayName": "الجمعة", "isHoliday": True, "lessonTitle": "عطلة رسمية", "linkedDailyPlanId": "", "activities": "—", "assessment": "—", "minutes": 0},
            {"dayName": "السبت", "isHoliday": True, "lessonTitle": "عطلة رسمية", "linkedDailyPlanId": "", "activities": "—", "assessment": "—", "minutes": 0},
        ],
        content_origin="authored_example",
        provenance_label="مثال توضيحي غير موثق من الكتاب",
    )

    db.add_all([plan_daily_a, plan_daily_b, plan_five_day, plan_weekly])
    db.flush()

    # Save initial versions & reviews for seeded plans
    for pln in [plan_daily_a, plan_daily_b, plan_five_day, plan_weekly]:
        payload_dict = {
            "id": pln.id,
            "title": pln.title,
            "planType": pln.plan_type,
            "status": pln.status,
            "periodsCount": pln.periods_count,
            "periodMinutes": pln.period_minutes,
            "objectives": pln.objectives,
            "priorKnowledge": pln.prior_knowledge,
            "teachingTools": pln.teaching_tools,
            "phases": pln.phases,
            "formativeAssessment": pln.formative_assessment,
            "differentiation": pln.differentiation,
            "homework": pln.homework,
            "subjectItems": pln.subject_items,
            "scheduleDays": pln.schedule_days,
            "slides": pln.slides,
            "contentOrigin": pln.content_origin,
            "provenanceLabel": pln.provenance_label,
        }
        sha = hashlib.sha256(json.dumps(payload_dict, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        db.add(
            PlanVersion(
                plan_id=pln.id,
                context_id=ctx1.id,
                version_number=1,
                status_at_save=pln.status,
                context_snapshot=ctx1.snapshot_dict(),
                plan_payload=payload_dict,
                content_sha256=sha,
                reviewer_name=ctx1.teacher_name,
            )
        )
        audit_res = audit_plan_and_context(
            payload_dict,
            ctx1.snapshot_dict(),
            source_data={"title": src1.title, "verificationStatus": src1.verification_status, "isOfficialClaimed": False},
        )
        db.add(
            PlanReview(
                plan_id=pln.id,
                context_id=ctx1.id,
                plan_version=1,
                overall_status=audit_res["overallStatus"],
                blockers_count=audit_res["blockersCount"],
                warnings_count=audit_res["warningsCount"],
                passed_count=audit_res["passedCount"],
                findings=audit_res["findings"],
            )
        )

    # --- Context 2: Isolated Arabic Literature Context (Demonstrating Multi-Subject & Non-Math Support) ---
    ctx2 = EducationalContext(
        id="ctx_arabic_lit_demo",
        subject="اللغة العربية والأدب",
        grade="الصف الثاني المتوسط",
        country="العراق",
        curriculum_name="منهج اللغة العربية والنصوص الأدبية",
        language="ar",
        year="",
        edition="",
        ui_language="ar",
        teacher_name="زينب حسن · معلمة لغة عربية",
        school_name="ثانوية دجلة للبنات",
        section_name="الشعبة ب",
        planning_date="2026-10-12",
        school_days=["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس"],
        holidays=["الجمعة", "السبت"],
        default_period_Minutes=45,
        default_periods_count=1,
        selected_tools=["سبورة", "بطاقات نصوص", "أوراق عمل"],
    )
    db.add(ctx2)
    db.flush()

    tpl_lit = PhaseTemplate(
        id="tpl_arabic_lit_default",
        context_id=ctx2.id,
        name="قالب درس الأدب والنصوص (5 مراحل قابلة للتخصيص)",
        description="التهيئة النصية، القراءة التفسيرية والشرح، التدريب والتحليل التذوقي، التقويم بمحك أدبي، التوسعة والإثراء",
        is_default=True,
        periods_count=1,
        period_minutes=45,
        phases=get_default_five_stage_phases(45, 1),
    )
    db.add(tpl_lit)
    ctx2.active_template_id = tpl_lit.id

    les_lit = Lesson(
        id="les_arabic_1",
        context_id=ctx2.id,
        title="تحليل نص أدبي: قيمة العلم والعمل (مثال توضيحي)",
        code_or_order="1",
        content_origin="authored_example",
        provenance_label="مثال توضيحي غير موثق من الكتاب",
        objectives=[
            "أن يستخلص المتعلم الفكرة الرئيسة والأفكار الفرعية من النص مستشهدًا بعبارات دالة.",
            "أن يبيّن الصورة البيانية وأثرها في المعنى وفق محك التذوق الأدبي.",
        ],
        prior_knowledge="التمييز بين التعبير الحقيقي والتعبير المجازي.",
        evaluation_criteria="محك تقييم مفتوح: سلامة الاستشهاد من النص، وضوح التفسير، وسلامة التراكيب اللغوية.",
        review_status="reviewed",
    )
    db.add(les_lit)
    db.flush()

    plan_lit = Plan(
        id="pln_arabic_daily_1",
        context_id=ctx2.id,
        primary_lesson_id=les_lit.id,
        title="خطة درس تحليل نص: قيمة العلم والعمل",
        plan_type="daily",
        status="reviewed",
        context_snapshot=ctx2.snapshot_dict(),
        teacher_name=ctx2.teacher_name,
        school_name=ctx2.school_name,
        section_name=ctx2.section_name,
        planning_date="2026-10-12",
        lessons_count=1,
        periods_count=1,
        period_minutes=45,
        total_allocated_minutes=45,
        objectives=les_lit.objectives,
        prior_knowledge=les_lit.prior_knowledge,
        teaching_tools=["سبورة", "بطاقات نصوص", "أوراق عمل"],
        phases=get_default_five_stage_phases(45, 1),
        formative_assessment="كتابة فقرة تحليلية قصيرة تُقيّم وفق محك (الفكرة، الشاهد النصي، سلامة اللغة) دون فرض إجابة مغلقة وحيدة.",
        differentiation="توفير مفاتيح معجمية للطلاب الذين يحتاجون دعمًا، ومقارنة أسلوبية للمتمكنين.",
        homework="اختيار بيت أو عبارة وتحليل دلالتها اللغوية (مثال توضيحي غير موثق من الكتاب).",
        subject_items=[
            {
                "domain": "literature",
                "quote": "العلم يبني بيوتاً لا عماد لها — مثال تدريبي",
                "attributedTo": "أحمد شوقي (مثال استشهادي للمراجعة)",
                "rubric": "محك تقييم التفسير الأدبي المفتوح: الاستشهاد + الدلالة + سلامة اللغة",
                "provenance": "مثال توضيحي غير موثق من الكتاب",
            }
        ],
        content_origin="authored_example",
        provenance_label="مثال توضيحي غير موثق من الكتاب",
    )
    db.add(plan_lit)
    db.commit()

