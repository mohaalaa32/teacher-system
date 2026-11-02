import io
import json
import os
import re
import zipfile
import xml.etree.ElementTree as ET
import pytest

# Ensure isolated SQLite test database
os.environ["DATABASE_URL"] = "sqlite:///./test_journey_isolated.db"
os.environ["ENABLE_DEMO_SEED"] = "0"

from backend.app.database import Base, engine, SessionLocal
from backend.app.models import EducationalContext, Plan, Lesson, Chapter, CurriculumSource, ExportTask
from backend.app.schemas import (
    EducationalContextCreate,
    EducationalContextUpdate,
    ChapterCreate,
    LessonCreate,
    PlanCreate,
    ExportCreateRequest,
)
from backend.app.main import (
    list_contexts,
    get_dashboard_summary,
    create_context,
    get_context,
    update_context,
    create_chapter,
    create_lesson,
    create_plan,
    run_plan_audit_endpoint,
    approve_plan_version,
    create_export_task,
    download_exported_file,
    on_startup,
)
from backend.app.services.export_service import verify_exported_file_structure


@pytest.fixture(scope="module", autouse=True)
def isolated_db_setup():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_journey_isolated.db"):
        try:
            os.remove("./test_journey_isolated.db")
        except OSError:
            pass


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_clean_start_zero_counters_and_no_demo(db):
    """Verify system starts 100% clean with zero contexts and zero fake tasks."""
    res = list_contexts(db=db)
    assert len(res.get("items", [])) == 0

    dash = get_dashboard_summary(contextId=None, db=db)
    stats = dash.get("stats", {})
    assert stats.get("totalPlansCount") == 0
    assert stats.get("attentionCount") == 0
    assert len(dash.get("todayTasks", [])) == 0


def test_onboarding_name_persistence_and_settings_update(db):
    """
    Test user entering their name and context without hardcoded subjects,
    updating settings, and verifying persistence from database when localStorage is absent.
    """
    create_payload = EducationalContextCreate(
        subject="الفيزياء",
        grade="الرابع العلمي",
        country="العراق",
        curriculumName="المنهج العراقي الحديث",
        language="ar",
        year="2025-2026",
        edition="الطبعة الخامسة",
        teacherName="أ. زينب الكعبي",
        schoolName="ثانوية المتميزات",
        defaultPeriodMinutes=45,
        defaultPeriodsCount=1,
    )
    created = create_context(create_payload, db=db)
    ctx_id = created["id"]
    assert created["teacherName"] == "أ. زينب الكعبي"
    assert created["subject"] == "الفيزياء"

    # Simulate client fetching context without any localStorage (fresh session / incognito)
    fetched = get_context(ctx_id, db=db)
    assert fetched["teacherName"] == "أ. زينب الكعبي"

    # Update settings to modify teacherName (e.g. obtaining title 'د.')
    update_payload = EducationalContextUpdate(
        subject="الفيزياء",
        grade="الرابع العلمي",
        country="العراق",
        curriculumName="المنهج العراقي الحديث",
        language="ar",
        year="2025-2026",
        edition="الطبعة الخامسة",
        teacherName="د. زينب الكعبي",
        schoolName="ثانوية المتميزات",
        defaultPeriodMinutes=45,
        defaultPeriodsCount=1,
        expectedVersion=created["version"],
    )
    updated = update_context(ctx_id, update_payload, db=db)
    assert updated["teacherName"] == "د. زينب الكعبي"

    # Verify context list reflects updated name from DB
    res = list_contexts(db=db)
    items = res["items"]
    assert len(items) == 1
    assert items[0]["teacherName"] == "د. زينب الكعبي"

    # Verify persistence after server startup reboot simulation
    on_startup()
    reboot_db = SessionLocal()
    try:
        reboot_res = list_contexts(db=reboot_db)
        assert len(reboot_res["items"]) == 1
        assert reboot_res["items"][0]["teacherName"] == "د. زينب الكعبي"
        # Verify NO demo contexts returned
        demo_cnt = reboot_db.query(EducationalContext).filter(
            EducationalContext.id.in_(["ctx_math_iq_demo", "ctx_arabic_lit_demo"])
        ).count()
        assert demo_cnt == 0
    finally:
        reboot_db.close()


def test_complete_teacher_journey_and_file_inspection(db):
    """
    Full teacher journey:
    1. Retrieve active context
    2. Import curriculum source & add lesson
    3. Create daily plan with 5 phases
    4. Review/audit plan and verify findings
    5. Approve plan version
    6. Export real DOCX, PPTX, PDF, and ZIP
    7. Deeply inspect actual file contents, text, XML structure, and verify they open cleanly.
    """
    # 1. Setup isolated context for this journey
    ctx = create_context(
        EducationalContextCreate(
            subject="الفيزياء",
            grade="الرابع العلمي",
            country="العراق",
            curriculumName="المنهج العراقي الحديث",
            language="ar",
            year="2025-2026",
            edition="الطبعة الخامسة",
            teacherName="د. زينب الكعبي",
            schoolName="ثانوية المتميزات",
            defaultPeriodMinutes=45,
            defaultPeriodsCount=1,
        ),
        db=db,
    )
    ctx_id = ctx["id"]

    # 2. Add Lesson
    les_payload = LessonCreate(
        contextId=ctx_id,
        title="الدرس الأول: الإزاحة الزاوية والسرعة الزاوية",
        codeOrOrder="1",
        pdfPageNumber=12,
        printedPageNumber="12-16",
        contentOrigin="authored_example",
    )
    les = create_lesson(payload=les_payload, x_active_context_id=ctx_id, db=db)
    lesson_id = les["id"]

    # 2. Create Daily Plan
    plan_payload = PlanCreate(
        contextId=ctx_id,
        title="خطة درس الإزاحة الزاوية والسرعة الزاوية",
        planType="daily",
        primaryLessonId=lesson_id,
        teacherName="د. زينب الكعبي",
        lessonsCount=1,
        periodsCount=1,
        periodMinutes=45,
        objectives=[
            "أن تعرّف الطالبة الإزاحة الزاوية بالراديان بدقة.",
            "أن تحسب السرعة الزاوية من العلاقة الرياضية المناسبة.",
        ],
        priorKnowledge="مفهوم الحركة الدائرية والسرعة الخطية من المرحلة السابقة.",
        phases=[
            {
                "phaseIndex": 0,
                "name": "التهيئة",
                "minutes": 5,
                "teacherRole": "طرح سؤال تحفيزي حول دوران عقارب الساعة وعجلة الدراجة.",
                "studentRole": "الملاحظة والإجابة عن الفروق بين الحركة الخطية والدائرية.",
                "pedagogicalAids": ["ساعة حائط", "سبورة"],
            },
            {
                "phaseIndex": 1,
                "name": "التدريس (الشرح والتفسير)",
                "minutes": 15,
                "teacherRole": "اشتقاق مفهوم الإزاحة الزاوية وتوضيح نصف القطر والزاوية المركزية.",
                "studentRole": "تدوين الملاحظات وتتبع خطوات الاشتقاق.",
                "pedagogicalAids": ["رسوم بيانية", "أقلام ملونة"],
            },
            {
                "phaseIndex": 2,
                "name": "التدريب",
                "minutes": 10,
                "teacherRole": "عرض مثال توضيحي ومتابعة حل الطالبات في مجموعات.",
                "studentRole": "حل المسألة في كراس النشاط ومقارنة النتائج.",
                "pedagogicalAids": ["بطاقات نشاط"],
            },
            {
                "phaseIndex": 3,
                "name": "التقويم",
                "minutes": 10,
                "teacherRole": "طرح مسألة تقويمية سريعة لجمع التغذية الراجعة.",
                "studentRole": "حل المسألة الفردية وتقديم الإجابة.",
                "pedagogicalAids": ["ورقة تقويم تكويني"],
            },
            {
                "phaseIndex": 4,
                "name": "التوسعة والإثراء",
                "minutes": 5,
                "teacherRole": "ربط السرعة الزاوية بحركة الأقمار الاصطناعية وتكليف الواجب.",
                "studentRole": "التفكير في التطبيقات العملية وتسجيل الواجب البيتي.",
                "pedagogicalAids": ["مقطع مرئي توضيحي"],
            },
        ],
        formativeAssessment="مسألة تقويمية: حساب الإزاحة الزاوية لقرص يدور بمعدل معلوم.",
        differentiation="مهمة إضافية للطلبة المتقدمين ودعم إرشادي لمن يحتاج تعزيزاً.",
        homework="حل أسئلة نهاية الدرس رقم 1 و 3 من الصفحة 16.",
    )
    plan_data = create_plan(payload=plan_payload, x_active_context_id=ctx_id, db=db)
    plan_id = plan_data["id"]

    # 3. Audit Plan
    audit_data = run_plan_audit_endpoint(plan_id, ctx_id, db=db)
    # Plan has objectives, priorKnowledge, phases (5+15+10+10+5 = 45m = 1x45), formativeAssessment -> 0 blockers
    assert audit_data["latestReview"]["blockersCount"] == 0, f"Expected 0 blockers, got: {audit_data['latestReview']['findings']}"

    # 4. Approve Plan Version
    approve_data = approve_plan_version(
        plan_id=plan_id,
        contextId=ctx_id,
        approverName="د. زينب الكعبي",
        x_active_context_id=ctx_id,
        db=db,
    )
    assert approve_data["status"] == "approved"

    # 5. Export to DOCX
    docx_task = create_export_task(
        payload=ExportCreateRequest(contextId=ctx_id, planId=plan_id, exportFormat="docx"),
        x_active_context_id=ctx_id,
        db=db,
    )
    docx_id = docx_task["id"]
    docx_response = download_exported_file(docx_id, ctx_id, db=db)
    docx_bytes = docx_response.body

    # Structural & Content inspection of DOCX
    docx_check = verify_exported_file_structure(docx_bytes, "docx")
    assert docx_check["passed"] is True
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
        doc_xml = zf.read("word/document.xml").decode("utf-8")
        assert "د. زينب الكعبي" in doc_xml, "Teacher name must be in the DOCX text"
        assert "الإزاحة الزاوية" in doc_xml, "Lesson title must be in the DOCX text"
        assert "التهيئة" in doc_xml, "Phase names must be in the DOCX text"

    # 6. Export to PPTX
    pptx_task = create_export_task(
        payload=ExportCreateRequest(contextId=ctx_id, planId=plan_id, exportFormat="pptx"),
        x_active_context_id=ctx_id,
        db=db,
    )
    pptx_id = pptx_task["id"]
    pptx_response = download_exported_file(pptx_id, ctx_id, db=db)
    pptx_bytes = pptx_response.body

    # Structural & Content inspection of PPTX
    pptx_check = verify_exported_file_structure(pptx_bytes, "pptx")
    assert pptx_check["passed"] is True
    assert pptx_check["slidesCount"] >= 5
    with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as zf:
        slide1_xml = zf.read("ppt/slides/slide1.xml").decode("utf-8")
        assert "الإزاحة الزاوية" in slide1_xml or "الفيزياء" in slide1_xml

    # 7. Export to PDF
    pdf_task = create_export_task(
        payload=ExportCreateRequest(contextId=ctx_id, planId=plan_id, exportFormat="pdf"),
        x_active_context_id=ctx_id,
        db=db,
    )
    pdf_id = pdf_task["id"]
    pdf_response = download_exported_file(pdf_id, ctx_id, db=db)
    pdf_bytes = pdf_response.body
    pdf_check = verify_exported_file_structure(pdf_bytes, "pdf")
    assert pdf_check["passed"] is True
    assert pdf_bytes.startswith(b"%PDF-1.7")

    # 8. Export to BUNDLE ZIP
    zip_task = create_export_task(
        payload=ExportCreateRequest(contextId=ctx_id, planId=plan_id, exportFormat="bundle_zip"),
        x_active_context_id=ctx_id,
        db=db,
    )
    zip_id = zip_task["id"]
    zip_response = download_exported_file(zip_id, ctx_id, db=db)
    zip_bytes = zip_response.body
    zip_check = verify_exported_file_structure(zip_bytes, "bundle_zip")
    assert zip_check["passed"] is True
    assert len(zip_check["files"]) >= 5


def test_cors_lan_regex():
    """Verify that the LAN CORS regex permits local network device origins."""
    lan_regex = r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(:\d+)?$"
    valid_lan_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.1.50:3000",
        "http://192.168.0.101:8000",
        "http://10.0.0.15:3000",
        "http://172.20.10.4:3000",
        "https://192.168.1.1:443",
    ]
    for origin in valid_lan_origins:
        assert re.match(lan_regex, origin), f"Origin should match LAN regex: {origin}"

    invalid_origins = [
        "http://evil-attacker.com",
        "http://malicious.org:3000",
        "http://192.168.1.50.attacker.com",
    ]
    for origin in invalid_origins:
        assert not re.match(lan_regex, origin), f"Origin should NOT match LAN regex: {origin}"
