import os
import zipfile
import io
import pytest

# Use a clean test database for pytest
os.environ["DATABASE_URL"] = "sqlite:///./test_teacher_system.db"

from backend.app.main import (
    app,
    health_check,
    list_contexts,
    create_context,
    create_lesson,
    create_plan,
    get_plan,
    update_plan,
    approve_plan_version,
    execute_subject_tool,
    create_export_task,
    download_exported_file,
)
from backend.app.database import Base, engine, SessionLocal
from backend.app.schemas import (
    EducationalContextCreate,
    LessonCreate,
    PlanCreate,
    PlanUpdate,
    SubjectToolRequest,
    ExportCreateRequest,
)
from backend.app.services.pdf_service import inspect_and_extract_pdf
from fastapi import HTTPException


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_health_and_seed_contexts(db):
    data = health_check(db=db)
    assert data["status"] == "ok"
    assert data["databaseConnected"] is True

    ctx_res = list_contexts(db=db)
    items = ctx_res["items"]
    assert len(items) >= 2
    demo_ctx = [c for c in items if c["id"] == "ctx_math_iq_demo"][0]
    assert demo_ctx["year"] == ""
    assert demo_ctx["edition"] == ""
    assert "year" in demo_ctx["missingContextFields"]
    assert "edition" in demo_ctx["missingContextFields"]


def test_create_new_context_any_subject_and_country(db):
    new_ctx = create_context(
        payload=EducationalContextCreate(
            subject="التاريخ الحديث",
            grade="الصف العاشر",
            country="الأردن",
            curriculumName="منهج التاريخ الوطني",
            language="ar",
            year="2026",
            edition="الطبعة الثالثة",
            teacherName="د. سامي المنصور",
            schoolName="مدرسة عمان الثانوية",
            sectionName="أ",
            defaultPeriodMinutes=50,
            defaultPeriodsCount=1,
        ),
        db=db,
    )
    assert new_ctx["subject"] == "التاريخ الحديث"
    assert new_ctx["country"] == "الأردن"
    assert new_ctx["missingContextFields"] == []


def test_context_isolation_and_stale_write_rejection(db):
    # 1. Reject delayed write when X-Active-Context-Id mismatches payload contextId
    with pytest.raises(HTTPException) as exc_info:
        create_lesson(
            payload=LessonCreate(contextId="ctx_math_iq_demo", title="درس متأخر من سياق سابق"),
            x_active_context_id="ctx_arabic_lit_demo",
            db=db,
        )
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "STALE_CONTEXT_WRITE_BLOCKED"

    # 2. Reject linking a plan in Context 2 (Arabic Lit) to a source from Context 1 (Math)
    with pytest.raises(HTTPException) as exc_cross:
        create_plan(
            payload=PlanCreate(
                contextId="ctx_arabic_lit_demo",
                sourceId="src_demo_unverified",  # Belongs to ctx_math_iq_demo!
                title="خطة تحاول الربط بمصدر سياق آخر",
                planType="daily",
            ),
            x_active_context_id="ctx_arabic_lit_demo",
            db=db,
        )
    assert exc_cross.value.status_code == 400
    assert exc_cross.value.detail["code"] == "CROSS_CONTEXT_SOURCE_FORBIDDEN"


def test_subject_tools_and_math_zero_division_guard(db):
    # 1. Division by zero must be caught and rejected
    z_data = execute_subject_tool(
        payload=SubjectToolRequest(
            contextId="ctx_math_iq_demo",
            toolType="math_solver",
            title="فحص القسمة على صفر",
            inputs={"expression": "(25 + 5) / (6 - 6)", "claimedAnswer": "0"},
        ),
        db=db,
    )
    assert z_data["valid"] is False
    assert z_data["errorCode"] == "MATH_DIVISION_BY_ZERO"

    # 2. Wrong numerical answer detection
    w_data = execute_subject_tool(
        payload=SubjectToolRequest(
            contextId="ctx_math_iq_demo",
            toolType="math_solver",
            inputs={"expression": "8 * 7 + 4", "claimedAnswer": "55", "unit": "سم"},
        ),
        db=db,
    )
    assert w_data["valid"] is False
    assert w_data["errorCode"] == "MATH_ANSWER_MISMATCH"
    assert w_data["computedValue"] == "60"

    # 3. Literature open-ended analysis (no math forced!)
    l_data = execute_subject_tool(
        payload=SubjectToolRequest(
            contextId="ctx_arabic_lit_demo",
            toolType="text_analysis",
            inputs={
                "passage": "إذا الشعب يوماً أراد الحياة فلا بد أن يستجيب القدر",
                "authorOrSource": "أبو القاسم الشابي",
                "focus": "الصورة الشعرية ودلالة الإرادة",
            },
        ),
        db=db,
    )
    assert l_data["valid"] is True
    assert "محك" in l_data["rubric"]


def test_plan_audit_approval_and_revocation_on_edit(db):
    # 1. `pln_daily_demo_a` initially lacks `formativeAssessment`, so approval MUST be blocked
    with pytest.raises(HTTPException) as exc_app:
        approve_plan_version("pln_daily_demo_a", contextId="ctx_math_iq_demo", db=db)
    assert exc_app.value.status_code == 400
    assert exc_app.value.detail["code"] == "APPROVAL_BLOCKED_BY_DEFECTS"

    # 2. Fetch plan, fix `formativeAssessment`, and update
    pln = get_plan("pln_daily_demo_a", contextId="ctx_math_iq_demo", db=db)
    upd_payload = PlanUpdate(
        contextId=pln["contextId"],
        sourceId=pln["sourceId"],
        primaryLessonId=pln["primaryLessonId"],
        secondaryLessonId=pln["secondaryLessonId"],
        title=pln["title"],
        planType=pln["planType"],
        teacherName=pln["teacherName"],
        schoolName=pln["schoolName"],
        sectionName=pln["sectionName"],
        planningDate=pln["planningDate"],
        lessonsCount=pln["lessonsCount"],
        periodsCount=pln["periodsCount"],
        periodMinutes=pln["periodMinutes"],
        objectives=pln["objectives"],
        priorKnowledge=pln["priorKnowledge"],
        teacherRole=pln["teacherRole"],
        studentRole=pln["studentRole"],
        teachingTools=pln["teachingTools"],
        phases=pln["phases"],
        formativeAssessment="اطلب من الطالب شرح اختياره لإحدى الخطوات، ثم سجّل ملاحظة مرتبطة بالهدف.",
        differentiation=pln["differentiation"],
        homework=pln["homework"],
        homeEnrichmentMinutes=pln["homeEnrichmentMinutes"],
        referencesNote=pln["referencesNote"],
        planningNotes=pln["planningNotes"],
        subjectItems=pln["subjectItems"],
        scheduleDays=pln["scheduleDays"],
        slides=pln["slides"],
        presentationSettings=pln["presentationSettings"],
        contentOrigin=pln["contentOrigin"],
        expectedVersion=pln["version"],
    )

    updated_pln = update_plan("pln_daily_demo_a", payload=upd_payload, x_active_context_id="ctx_math_iq_demo", db=db)
    assert updated_pln["latestReview"]["blockersCount"] == 0
    assert updated_pln["latestReview"]["warningsCount"] >= 1

    # 3. Now approval succeeds even though source has a non-blocking warning
    approved_pln = approve_plan_version(
        "pln_daily_demo_a",
        contextId="ctx_math_iq_demo",
        approverName="أحمد علي",
        x_active_context_id="ctx_math_iq_demo",
        db=db,
    )
    assert approved_pln["status"] == "approved"
    assert approved_pln["approvedVersion"] == approved_pln["version"]

    # 4. Subsequent edit revokes approval on the new version while keeping previous version history
    upd_payload.title = "درس تجريبي أ — تعديل بعد الاعتماد"
    upd_payload.expectedVersion = approved_pln["version"]
    re_edited_pln = update_plan("pln_daily_demo_a", payload=upd_payload, x_active_context_id="ctx_math_iq_demo", db=db)
    assert re_edited_pln["version"] == approved_pln["version"] + 1
    assert re_edited_pln["status"] != "approved"
    assert re_edited_pln["approvedVersion"] == approved_pln["version"]


def test_pdf_upload_signature_validation_and_real_exports(db):
    # 1. Reject fake file renamed to .pdf
    with pytest.raises(ValueError) as exc_pdf:
        inspect_and_extract_pdf(b"<html>not a pdf</html>", "fake.pdf")
    assert "%PDF-" in str(exc_pdf.value)

    # 2. Export real DOCX, PDF, PPTX, Report PDF, and Bundle ZIP for version 2 (the approved version)
    for fmt in ["docx", "pdf", "pptx", "report_pdf", "bundle_zip"]:
        exp_data = create_export_task(
            payload=ExportCreateRequest(
                contextId="ctx_math_iq_demo",
                planId="pln_daily_demo_a",
                planVersion=2,
                exportFormat=fmt,
            ),
            x_active_context_id="ctx_math_iq_demo",
            db=db,
        )
        assert exp_data["structuralCheckPassed"] is True

        dl_res = download_exported_file(exp_data["id"], contextId="ctx_math_iq_demo", db=db)
        assert dl_res.status_code == 200
        assert len(dl_res.body) > 200
        if fmt == "pdf":
            assert dl_res.body.startswith(b"%PDF-1.7")
            # Round-trip test: inspect and extract the generated PDF
            insp = inspect_and_extract_pdf(dl_res.body, "curriculum_sample.pdf")
            assert insp["pageCount"] >= 1
            assert insp["extractionStatus"] == "extracted_text"
            assert len(insp["pages"]) >= 1
        elif fmt in ("docx", "pptx"):
            with zipfile.ZipFile(io.BytesIO(dl_res.body), "r") as zf:
                assert "[Content_Types].xml" in zf.namelist()

