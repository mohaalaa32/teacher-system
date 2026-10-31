import hashlib
import io
import json
import os
import re
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Optional

from fastapi import (
    FastAPI,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import Base, engine, get_db, SessionLocal, DATABASE_URL
from .models import (
    EducationalContext,
    PhaseTemplate,
    CurriculumSource,
    SourcePage,
    Chapter,
    Lesson,
    Plan,
    PlanVersion,
    PlanReview,
    ExportTask,
    utcnow,
    gen_id,
)
from .schemas import (
    EducationalContextCreate,
    EducationalContextUpdate,
    PhaseTemplateCreate,
    SourceMetadataUpdate,
    SourcePageUpdate,
    ChapterCreate,
    LessonCreate,
    LessonUpdate,
    PlanCreate,
    PlanUpdate,
    PlanCopyCrossContextRequest,
    SubjectToolRequest,
    ExportCreateRequest,
)
from .services.audit_service import audit_plan_and_context, run_subject_tool
from .services.pdf_service import inspect_and_extract_pdf
from .services.export_service import (
    generate_plan_docx_bytes,
    generate_plan_pptx_bytes,
    generate_plan_pdf_bytes,
    verify_exported_file_structure,
)
from .services.seed_service import ensure_initial_seed_data, get_default_five_stage_phases

STORAGE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "storage"))
UPLOADS_DIR = os.path.join(STORAGE_ROOT, "uploads")
EXPORTS_DIR = os.path.join(STORAGE_ROOT, "exports")
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)

app = FastAPI(
    title="مساعد المدرس لأي مادة ومنهج وسياق تعليمي — FastAPI Backend",
    description="خدمة Python FastAPI مستقلة مع دعم SQLite/PostgreSQL وعزل السياقات وتدقيق المحتوى التخصصي وتوليد DOCX/PDF/PPTX الفعلي.",
    version="1.0.0",
)

ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001",
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Content-Disposition"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_initial_seed_data(db)
    finally:
        db.close()


@app.middleware("http")
async def request_id_and_security_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:10]}"
    request.state.request_id = req_id
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response
    except Exception as exc:
        # Never leak stack tracebacks or secrets to the client
        return JSONResponse(
            status_code=500,
            headers={"X-Request-ID": req_id},
            content={
                "error": True,
                "code": "INTERNAL_SERVER_ERROR",
                "message": "حدث خطأ داخلي في الخادم. يرجى المحاولة مرة أخرى أو مراجعة معرف الطلب.",
                "requestId": req_id,
            },
        )


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    req_id = getattr(request.state, "request_id", f"req_{uuid.uuid4().hex[:10]}")
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("code", f"HTTP_{exc.status_code}")
        msg = detail.get("message", "تعذر إتمام الطلب.")
        extra = {k: v for k, v in detail.items() if k not in ("code", "message")}
    else:
        code = f"HTTP_{exc.status_code}"
        msg = str(detail)
        extra = {}
    return JSONResponse(
        status_code=exc.status_code,
        headers={"X-Request-ID": req_id},
        content={
            "error": True,
            "code": code,
            "message": msg,
            "requestId": req_id,
            **extra,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = getattr(request.state, "request_id", f"req_{uuid.uuid4().hex[:10]}")
    return JSONResponse(
        status_code=422,
        headers={"X-Request-ID": req_id},
        content={
            "error": True,
            "code": "VALIDATION_ERROR",
            "message": "بيانات الطلب غير صالحة؛ تحقق من الحقول المدخلة.",
            "requestId": req_id,
            "details": exc.errors(),
        },
    )


def verify_active_context_guard(
    payload_context_id: str,
    header_active_context_id: Optional[str],
):
    """
    Prevents a delayed save/load request from a previous context from writing into the currently active context!
    """
    if isinstance(header_active_context_id, str) and header_active_context_id.strip() != payload_context_id.strip():
        raise HTTPException(
            status_code=409,
            detail={
                "code": "STALE_CONTEXT_WRITE_BLOCKED",
                "message": "تم رفض الكتابة: الطلب قادم من سياق سابق لا يطابق السياق النشط حاليًا.",
                "payloadContextId": payload_context_id,
                "activeContextId": header_active_context_id,
            },
        )


def serialize_context(ctx: EducationalContext) -> dict:
    snap = ctx.snapshot_dict()
    return {
        "id": ctx.id,
        "subject": ctx.subject,
        "grade": ctx.grade,
        "country": ctx.country,
        "curriculumName": ctx.curriculum_name,
        "language": ctx.language,
        "year": ctx.year,
        "edition": ctx.edition,
        "uiLanguage": ctx.ui_language,
        "teacherName": ctx.teacher_name,
        "schoolName": ctx.school_name,
        "sectionName": ctx.section_name,
        "planningDate": ctx.planning_date,
        "schoolDays": ctx.school_days,
        "holidays": ctx.holidays,
        "defaultPeriodMinutes": ctx.default_period_Minutes,
        "defaultPeriodsCount": ctx.default_periods_count,
        "selectedTools": ctx.selected_tools,
        "documentPreferences": ctx.document_preferences,
        "activeTemplateId": ctx.active_template_id,
        "missingContextFields": snap["missingContextFields"],
        "version": ctx.version,
        "createdAt": ctx.created_at.isoformat() if ctx.created_at else None,
        "updatedAt": ctx.updated_at.isoformat() if ctx.updated_at else None,
    }


def serialize_source(src: CurriculumSource, include_details: bool = False) -> dict:
    data = {
        "id": src.id,
        "contextId": src.context_id,
        "title": src.title,
        "sourceType": src.source_type,
        "fileName": src.file_name,
        "fileSize": src.file_size,
        "sha256Fingerprint": src.sha256_fingerprint,
        "pageCount": src.page_count,
        "extractionStatus": src.extraction_status,
        "bookYear": src.book_year,
        "edition": src.edition,
        "sourceUrl": src.source_url,
        "isOfficialClaimed": src.is_official_claimed,
        "officialEvidence": src.official_evidence,
        "verificationStatus": src.verification_status,
        "reviewerName": src.reviewer_name,
        "reviewNotes": src.review_notes,
        "reviewedAt": src.reviewed_at.isoformat() if src.reviewed_at else None,
        "indexApproved": src.index_approved,
        "version": src.version,
        "createdAt": src.created_at.isoformat() if src.created_at else None,
    }
    if include_details:
        data["pages"] = [
            {
                "id": p.id,
                "pdfPageNumber": p.pdf_page_number,
                "printedPageNumber": p.printed_page_number,
                "extractedText": p.extracted_text,
                "correctedText": p.corrected_text,
                "needsOcrReview": p.needs_ocr_review,
                "ocrAmbiguities": p.ocr_ambiguities,
                "humanReviewed": p.human_reviewed,
            }
            for p in sorted(src.pages, key=lambda x: x.pdf_page_number)
        ]
        data["chapters"] = [
            {
                "id": c.id,
                "title": c.title,
                "orderIndex": c.order_index,
                "pdfStartPage": c.pdf_start_page,
                "printedStartPage": c.printed_start_page,
                "isDocumented": c.is_documented,
                "provenanceLabel": c.provenance_label,
            }
            for c in sorted(src.chapters, key=lambda x: x.order_index)
        ]
    return data


def serialize_lesson(les: Lesson) -> dict:
    return {
        "id": les.id,
        "contextId": les.context_id,
        "sourceId": les.source_id,
        "chapterId": les.chapter_id,
        "title": les.title,
        "codeOrOrder": les.code_or_order,
        "pdfPageNumber": les.pdf_page_number,
        "printedPageNumber": les.printed_page_number,
        "contentOrigin": les.content_origin,
        "provenanceLabel": les.provenance_label,
        "objectives": les.objectives,
        "priorKnowledge": les.prior_knowledge,
        "activities": les.activities,
        "questionsAndSolutions": les.questions_and_solutions,
        "evaluationCriteria": les.evaluation_criteria,
        "keyTermsOrQuotes": les.key_terms_or_quotes,
        "reviewStatus": les.review_status,
        "version": les.version,
        "updatedAt": les.updated_at.isoformat() if les.updated_at else None,
    }


def serialize_plan(pln: Plan) -> dict:
    latest_rev = None
    if pln.reviews:
        r = sorted(pln.reviews, key=lambda x: x.created_at or utcnow(), reverse=True)[0]
        latest_rev = {
            "id": r.id,
            "planVersion": r.plan_version,
            "overallStatus": r.overall_status,
            "blockersCount": r.blockers_count,
            "warningsCount": r.warnings_count,
            "passedCount": r.passed_count,
            "findings": r.findings,
            "reviewerName": r.reviewer_name,
            "createdAt": r.created_at.isoformat() if r.created_at else None,
        }
    return {
        "id": pln.id,
        "contextId": pln.context_id,
        "sourceId": pln.source_id,
        "primaryLessonId": pln.primary_lesson_id,
        "secondaryLessonId": pln.secondary_lesson_id,
        "title": pln.title,
        "planType": pln.plan_type,
        "status": pln.status,
        "contextSnapshot": pln.context_snapshot,
        "teacherName": pln.teacher_name,
        "schoolName": pln.school_name,
        "sectionName": pln.section_name,
        "planningDate": pln.planning_date,
        "lessonsCount": pln.lessons_count,
        "periodsCount": pln.periods_count,
        "periodMinutes": pln.period_minutes,
        "totalAllocatedMinutes": pln.total_allocated_minutes,
        "objectives": pln.objectives,
        "priorKnowledge": pln.prior_knowledge,
        "teacherRole": pln.teacher_role,
        "studentRole": pln.student_role,
        "teachingTools": pln.teaching_tools,
        "phases": pln.phases,
        "formativeAssessment": pln.formative_assessment,
        "differentiation": pln.differentiation,
        "homework": pln.homework,
        "homeEnrichmentMinutes": pln.home_enrichment_minutes,
        "referencesNote": pln.references_note,
        "planningNotes": pln.planning_notes,
        "subjectItems": pln.subject_items,
        "scheduleDays": pln.schedule_days,
        "slides": pln.slides,
        "presentationSettings": pln.presentation_settings,
        "contentOrigin": pln.content_origin,
        "provenanceLabel": pln.provenance_label,
        "version": pln.version,
        "approvedVersion": pln.approved_version,
        "approvedBy": pln.approved_by,
        "approvedAt": pln.approved_at.isoformat() if pln.approved_at else None,
        "latestReview": latest_rev,
        "updatedAt": pln.updated_at.isoformat() if pln.updated_at else None,
    }


# ==============================================================================
# HEALTH & READINESS ENDPOINT
# ==============================================================================

@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    dialect = "postgresql" if DATABASE_URL.startswith("postgres") else "sqlite"
    return {
        "status": "ok",
        "service": "teacher-system-fastapi",
        "databaseConnected": True,
        "databaseDialect": dialect,
        "timestamp": utcnow().isoformat(),
    }


# ==============================================================================
# CONTEXTS & SETTINGS ENDPOINTS
# ==============================================================================

@app.get("/api/contexts")
def list_contexts(db: Session = Depends(get_db)):
    ensure_initial_seed_data(db)
    contexts = db.query(EducationalContext).order_by(EducationalContext.created_at.asc()).all()
    return {"items": [serialize_context(c) for c in contexts]}


@app.post("/api/contexts", status_code=201)
def create_context(payload: EducationalContextCreate, db: Session = Depends(get_db)):
    ctx = EducationalContext(
        subject=payload.subject.strip(),
        grade=payload.grade.strip(),
        country=payload.country.strip(),
        curriculum_name=payload.curriculumName.strip(),
        language=payload.language.strip() or "ar",
        year=payload.year.strip(),
        edition=payload.edition.strip(),
        ui_language=payload.uiLanguage.strip() or "ar",
        teacher_name=payload.teacherName.strip(),
        school_name=payload.schoolName.strip(),
        section_name=payload.sectionName.strip(),
        planning_date=payload.planningDate.strip() or datetime.now().strftime("%Y-%m-%d"),
        school_days=payload.schoolDays or ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس"],
        holidays=payload.holidays or ["الجمعة", "السبت"],
        default_period_Minutes=payload.defaultPeriodMinutes,
        default_periods_count=payload.defaultPeriodsCount,
        selected_tools=payload.selectedTools or ["سبورة", "أقلام ملوّنة"],
        document_preferences=payload.documentPreferences
        or {
            "paperSize": "A4",
            "includeSourceBanner": True,
            "includeTeacherSignature": True,
            "fontFamily": "Arial",
            "mathDirection": "ltr",
        },
    )
    db.add(ctx)
    db.flush()

    default_tpl = PhaseTemplate(
        context_id=ctx.id,
        name="القالب الافتراضي: دورة التعلّم الخماسية (5 مراحل)",
        description="التهيئة، التدريس (الشرح والتفسير)، التدريب، التقويم، التوسعة والإثراء",
        is_default=True,
        periods_count=ctx.default_periods_count,
        period_minutes=ctx.default_period_Minutes,
        phases=get_default_five_stage_phases(ctx.default_period_Minutes, ctx.default_periods_count),
    )
    db.add(default_tpl)
    db.flush()
    ctx.active_template_id = default_tpl.id
    db.commit()
    db.refresh(ctx)
    return serialize_context(ctx)


@app.get("/api/contexts/{context_id}")
def get_context(context_id: str, db: Session = Depends(get_db)):
    ctx = db.query(EducationalContext).filter(EducationalContext.id == context_id).first()
    if not ctx:
        raise HTTPException(status_code=404, detail={"code": "CONTEXT_NOT_FOUND", "message": "السياق التعليمي غير موجود."})
    return serialize_context(ctx)


@app.put("/api/contexts/{context_id}")
def update_context(
    context_id: str,
    payload: EducationalContextUpdate,
    x_active_context_id: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    verify_active_context_guard(context_id, x_active_context_id)
    ctx = db.query(EducationalContext).filter(EducationalContext.id == context_id).first()
    if not ctx:
        raise HTTPException(status_code=404, detail={"code": "CONTEXT_NOT_FOUND", "message": "السياق التعليمي غير موجود."})

    if payload.expectedVersion is not None and payload.expectedVersion != ctx.version:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "VERSION_CONFLICT",
                "message": "تم تعديل إعدادات السياق في جلسة أحدث. يرجى تحديث الصفحة قبل الحفظ.",
                "currentVersion": ctx.version,
            },
        )

    # Note: Updating context settings applies to NEW plans only and NEVER mutates `context_snapshot` of existing plans!
    ctx.subject = payload.subject.strip()
    ctx.grade = payload.grade.strip()
    ctx.country = payload.country.strip()
    ctx.curriculum_name = payload.curriculumName.strip()
    ctx.language = payload.language.strip() or "ar"
    ctx.year = payload.year.strip()
    ctx.edition = payload.edition.strip()
    ctx.ui_language = payload.uiLanguage.strip() or "ar"
    ctx.teacher_name = payload.teacherName.strip()
    ctx.school_name = payload.schoolName.strip()
    ctx.section_name = payload.sectionName.strip()
    ctx.planning_date = payload.planningDate.strip()
    ctx.school_days = payload.schoolDays
    ctx.holidays = payload.holidays
    ctx.default_period_Minutes = payload.defaultPeriodMinutes
    ctx.default_periods_count = payload.defaultPeriodsCount
    ctx.selected_tools = payload.selectedTools
    if payload.documentPreferences:
        ctx.document_preferences = payload.documentPreferences
    ctx.version += 1
    ctx.updated_at = utcnow()

    db.commit()
    db.refresh(ctx)
    return serialize_context(ctx)


# ==============================================================================
# PHASE TEMPLATES ENDPOINTS
# ==============================================================================

@app.get("/api/templates")
def list_templates(contextId: str = Query(...), db: Session = Depends(get_db)):
    templates = (
        db.query(PhaseTemplate)
        .filter(PhaseTemplate.context_id == contextId)
        .order_by(PhaseTemplate.is_default.desc(), PhaseTemplate.created_at.asc())
        .all()
    )
    return {
        "items": [
            {
                "id": t.id,
                "contextId": t.context_id,
                "name": t.name,
                "description": t.description,
                "isDefault": t.is_default,
                "periodsCount": t.periods_count,
                "periodMinutes": t.period_minutes,
                "phases": t.phases,
                "version": t.version,
            }
            for t in templates
        ]
    }


@app.post("/api/templates", status_code=201)
def create_template(
    payload: PhaseTemplateCreate,
    x_active_context_id: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    verify_active_context_guard(payload.contextId, x_active_context_id)
    ctx = db.query(EducationalContext).filter(EducationalContext.id == payload.contextId).first()
    if not ctx:
        raise HTTPException(status_code=404, detail={"code": "CONTEXT_NOT_FOUND", "message": "السياق غير موجود."})

    tpl = PhaseTemplate(
        context_id=payload.contextId,
        name=payload.name.strip(),
        description=payload.description.strip(),
        is_default=payload.isDefault,
        periods_count=payload.periodsCount,
        period_minutes=payload.periodMinutes,
        phases=[p.model_dump() for p in payload.phases],
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return {
        "id": tpl.id,
        "contextId": tpl.context_id,
        "name": tpl.name,
        "description": tpl.description,
        "isDefault": tpl.is_default,
        "periodsCount": tpl.periods_count,
        "periodMinutes": tpl.period_minutes,
        "phases": tpl.phases,
    }


# ==============================================================================
# CURRICULUM SOURCES & PDF UPLOAD ENDPOINTS
# ==============================================================================

@app.get("/api/sources")
def list_sources(contextId: str = Query(...), db: Session = Depends(get_db)):
    sources = (
        db.query(CurriculumSource)
        .filter(CurriculumSource.context_id == contextId)
        .order_by(CurriculumSource.created_at.desc())
        .all()
    )
    return {"items": [serialize_source(s, include_details=True) for s in sources]}


@app.post("/api/sources/upload", status_code=201)
async def upload_source_pdf(
    contextId: str = Form(...),
    title: str = Form("مصدر منهج مرفوع"),
    bookYear: str = Form(""),
    edition: str = Form(""),
    sourceUrl: str = Form(""),
    file: UploadFile = File(...),
    x_active_context_id: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    verify_active_context_guard(contextId, x_active_context_id)
    ctx = db.query(EducationalContext).filter(EducationalContext.id == contextId).first()
    if not ctx:
        raise HTTPException(status_code=404, detail={"code": "CONTEXT_NOT_FOUND", "message": "السياق غير موجود."})

    # Sanitize filename to prevent path traversal (`../` or drive letters)
    raw_filename = os.path.basename(file.filename or "uploaded.pdf")
    safe_filename = re.sub(r"[^a-zA-Z0-9_\-\.\u0600-\u06FF ]", "_", raw_filename)
    if not safe_filename.lower().endswith(".pdf"):
        safe_filename += ".pdf"

    file_bytes = await file.read()
    try:
        inspection = inspect_and_extract_pdf(file_bytes, safe_filename)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail={"code": "INVALID_PDF_FILE", "message": str(ve)})

    stored_name = f"{contextId}_{uuid.uuid4().hex[:8]}_{safe_filename}"
    stored_path = os.path.join(UPLOADS_DIR, stored_name)
    with open(stored_path, "wb") as f_out:
        f_out.write(file_bytes)

    src = CurriculumSource(
        context_id=contextId,
        title=title.strip() or safe_filename,
        source_type="pdf_upload",
        file_name=safe_filename,
        file_path=stored_path,
        file_size=inspection["fileSize"],
        sha256_fingerprint=inspection["sha256Fingerprint"],
        mime_type="application/pdf",
        page_count=inspection["pageCount"],
        extraction_status=inspection["extractionStatus"],
        book_year=bookYear.strip(),
        edition=edition.strip(),
        source_url=sourceUrl.strip(),
        verification_status="pending_review",
        index_approved=False,
    )
    db.add(src)
    db.flush()

    for pg in inspection["pages"]:
        db.add(
            SourcePage(
                source_id=src.id,
                pdf_page_number=pg["pdfPageNumber"],
                printed_page_number=pg["printedPageNumber"],
                extracted_text=pg["extractedText"],
                corrected_text=pg["correctedText"],
                needs_ocr_review=pg["needsOcrReview"],
                ocr_ambiguities=pg["ocrAmbiguities"],
                human_reviewed=False,
            )
        )

    db.commit()
    db.refresh(src)
    return serialize_source(src, include_details=True)


@app.put("/api/sources/{source_id}")
def update_source_metadata(
    source_id: str,
    payload: SourceMetadataUpdate,
    x_active_context_id: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    verify_active_context_guard(payload.contextId, x_active_context_id)
    src = (
        db.query(CurriculumSource)
        .filter(CurriculumSource.id == source_id, CurriculumSource.context_id == payload.contextId)
        .first()
    )
    if not src:
        raise HTTPException(
            status_code=404,
            detail={"code": "SOURCE_NOT_FOUND_IN_CONTEXT", "message": "المصدر غير موجود ضمن هذا السياق."},
        )

    src.title = payload.title.strip()
    src.book_year = payload.bookYear.strip()
    src.edition = payload.edition.strip()
    src.source_url = payload.sourceUrl.strip()
    src.is_official_claimed = payload.isOfficialClaimed
    src.official_evidence = payload.officialEvidence.strip()
    src.reviewer_name = payload.reviewerName.strip()
    src.review_notes = payload.reviewNotes.strip()

    if payload.verificationStatus:
        if payload.verificationStatus == "human_verified":
            # Require year, edition, sourceUrl, and reviewerName before human verification!
            if not (src.book_year and src.edition and src.source_url and src.reviewer_name):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "INCOMPLETE_SOURCE_VERIFICATION_DATA",
                        "message": "لا يمكن اعتماد توثيق المصدر قبل إدخال السنة الدراسية والطبعة ورابط المصدر واسم المراجع.",
                    },
                )
            src.verification_status = "human_verified"
            src.reviewed_at = utcnow()
        else:
            src.verification_status = payload.verificationStatus

    if payload.indexApproved is not None:
        src.index_approved = payload.indexApproved

    src.version += 1
    src.updated_at = utcnow()
    db.commit()
    db.refresh(src)
    return serialize_source(src, include_details=True)


@app.put("/api/sources/{source_id}/pages/{page_id}")
def update_source_page_text(
    source_id: str,
    page_id: str,
    payload: SourcePageUpdate,
    x_active_context_id: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    verify_active_context_guard(payload.contextId, x_active_context_id)
    src = (
        db.query(CurriculumSource)
        .filter(CurriculumSource.id == source_id, CurriculumSource.context_id == payload.contextId)
        .first()
    )
    if not src:
        raise HTTPException(status_code=404, detail={"code": "SOURCE_NOT_FOUND", "message": "المصدر غير موجود."})

    pg = db.query(SourcePage).filter(SourcePage.id == page_id, SourcePage.source_id == src.id).first()
    if not pg:
        raise HTTPException(status_code=404, detail={"code": "PAGE_NOT_FOUND", "message": "الصفحة غير موجودة."})

    pg.printed_page_number = payload.printedPageNumber.strip()
    pg.corrected_text = payload.correctedText
    pg.human_reviewed = payload.humanReviewed
    pg.needs_ocr_review = False
    pg.updated_at = utcnow()
    db.commit()
    return {
        "id": pg.id,
        "pdfPageNumber": pg.pdf_page_number,
        "printedPageNumber": pg.printed_page_number,
        "extractedText": pg.extracted_text,
        "correctedText": pg.corrected_text,
        "needsOcrReview": pg.needs_ocr_review,
        "humanReviewed": pg.human_reviewed,
    }


@app.post("/api/chapters", status_code=201)
def create_chapter(
    payload: ChapterCreate,
    x_active_context_id: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    verify_active_context_guard(payload.contextId, x_active_context_id)
    src = (
        db.query(CurriculumSource)
        .filter(CurriculumSource.id == payload.sourceId, CurriculumSource.context_id == payload.contextId)
        .first()
    )
    if not src:
        raise HTTPException(
            status_code=400,
            detail={"code": "CROSS_CONTEXT_SOURCE_FORBIDDEN", "message": "لا يجوز ربط فصل بمصدر من سياق مختلف."},
        )

    is_doc = bool(payload.isDocumented and src.verification_status == "human_verified")
    prov = "فصل موثق من المصدر المعتمد" if is_doc else "مثال توضيحي غير موثق من الكتاب"
    ch = Chapter(
        context_id=payload.contextId,
        source_id=payload.sourceId,
        title=payload.title.strip(),
        order_index=payload.orderIndex,
        pdf_start_page=payload.pdfStartPage,
        printed_start_page=payload.printedStartPage.strip(),
        is_documented=is_doc,
        provenance_label=prov,
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)
    return {
        "id": ch.id,
        "contextId": ch.context_id,
        "sourceId": ch.source_id,
        "title": ch.title,
        "orderIndex": ch.order_index,
        "pdfStartPage": ch.pdf_start_page,
        "printedStartPage": ch.printed_start_page,
        "isDocumented": ch.is_documented,
        "provenanceLabel": ch.provenance_label,
    }


# ==============================================================================
# LESSONS ENDPOINTS (Create / Update / Duplicate / List)
# ==============================================================================

@app.get("/api/lessons")
def list_lessons(contextId: str = Query(...), q: Optional[str] = Query(default=None), db: Session = Depends(get_db)):
    query = db.query(Lesson).filter(Lesson.context_id == contextId)
    if q and q.strip():
        query = query.filter(Lesson.title.contains(q.strip()))
    lessons = query.order_by(Lesson.created_at.asc()).all()
    return {"items": [serialize_lesson(l) for l in lessons]}


@app.post("/api/lessons", status_code=201)
def create_lesson(
    payload: LessonCreate,
    x_active_context_id: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    verify_active_context_guard(payload.contextId, x_active_context_id)
    if payload.sourceId:
        src = (
            db.query(CurriculumSource)
            .filter(CurriculumSource.id == payload.sourceId, CurriculumSource.context_id == payload.contextId)
            .first()
        )
        if not src:
            raise HTTPException(
                status_code=400,
                detail={"code": "CROSS_CONTEXT_SOURCE_FORBIDDEN", "message": "لا يجوز ربط درس بمصدر من سياق مختلف."},
            )

    prov = (
        "مرتبط بصفحة موثقة من المصدر"
        if payload.contentOrigin == "documented_source" and (payload.pdfPageNumber or payload.printedPageNumber)
        else "مثال توضيحي غير موثق من الكتاب"
    )
    les = Lesson(
        context_id=payload.contextId,
        source_id=payload.sourceId,
        chapter_id=payload.chapterId,
        title=payload.title.strip(),
        code_or_order=payload.codeOrOrder.strip() or "1",
        pdf_page_number=payload.pdfPageNumber,
        printed_page_number=payload.printedPageNumber.strip(),
        content_origin=payload.contentOrigin,
        provenance_label=prov,
        objectives=payload.objectives,
        prior_knowledge=payload.priorKnowledge,
        activities=payload.activities,
        questions_and_solutions=payload.questionsAndSolutions,
        evaluation_criteria=payload.evaluationCriteria,
        key_terms_or_quotes=payload.keyTermsOrQuotes,
    )
    db.add(les)
    db.commit()
    db.refresh(les)
    return serialize_lesson(les)


@app.put("/api/lessons/{lesson_id}")
def update_lesson(
    lesson_id: str,
    payload: LessonUpdate,
    x_active_context_id: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    verify_active_context_guard(payload.contextId, x_active_context_id)
    les = db.query(Lesson).filter(Lesson.id == lesson_id, Lesson.context_id == payload.contextId).first()
    if not les:
        raise HTTPException(status_code=404, detail={"code": "LESSON_NOT_FOUND", "message": "الدرس غير موجود في هذا السياق."})

    if payload.expectedVersion is not None and payload.expectedVersion != les.version:
        raise HTTPException(
            status_code=409,
            detail={"code": "VERSION_CONFLICT", "message": "تم تعديل الدرس في نسخة أحدث.", "currentVersion": les.version},
        )

    if payload.sourceId:
        src = (
            db.query(CurriculumSource)
            .filter(CurriculumSource.id == payload.sourceId, CurriculumSource.context_id == payload.contextId)
            .first()
        )
        if not src:
            raise HTTPException(
                status_code=400,
                detail={"code": "CROSS_CONTEXT_SOURCE_FORBIDDEN", "message": "لا يجوز ربط درس بمصدر من سياق مختلف."},
            )

    les.source_id = payload.sourceId
    les.chapter_id = payload.chapterId
    les.title = payload.title.strip()
    les.code_or_order = payload.codeOrOrder.strip()
    les.pdf_page_number = payload.pdfPageNumber
    les.printed_page_number = payload.printedPageNumber.strip()
    les.content_origin = payload.contentOrigin
    les.provenance_label = (
        "مرتبط بصفحة موثقة من المصدر"
        if payload.contentOrigin == "documented_source" and (payload.pdfPageNumber or payload.printedPageNumber)
        else "مثال توضيحي غير موثق من الكتاب"
    )
    les.objectives = payload.objectives
    les.prior_knowledge = payload.priorKnowledge
    les.activities = payload.activities
    les.questions_and_solutions = payload.questionsAndSolutions
    les.evaluation_criteria = payload.evaluationCriteria
    les.key_terms_or_quotes = payload.keyTermsOrQuotes
    les.version += 1
    les.updated_at = utcnow()
    db.commit()
    db.refresh(les)
    return serialize_lesson(les)


@app.post("/api/lessons/{lesson_id}/duplicate", status_code=201)
def duplicate_lesson(
    lesson_id: str,
    contextId: str = Query(...),
    x_active_context_id: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    verify_active_context_guard(contextId, x_active_context_id)
    orig = db.query(Lesson).filter(Lesson.id == lesson_id, Lesson.context_id == contextId).first()
    if not orig:
        raise HTTPException(status_code=404, detail={"code": "LESSON_NOT_FOUND", "message": "الدرس الأصلي غير موجود."})

    copy_les = Lesson(
        context_id=contextId,
        source_id=orig.source_id,
        chapter_id=orig.chapter_id,
        title=f"{orig.title} (نسخة)",
        code_or_order=orig.code_or_order,
        pdf_page_number=orig.pdf_page_number,
        printed_page_number=orig.printed_page_number,
        content_origin=orig.content_origin,
        provenance_label=orig.provenance_label,
        objectives=list(orig.objectives or []),
        prior_knowledge=orig.prior_knowledge,
        activities=list(orig.activities or []),
        questions_and_solutions=list(orig.questions_and_solutions or []),
        evaluation_criteria=orig.evaluation_criteria,
        key_terms_or_quotes=list(orig.key_terms_or_quotes or []),
        review_status="draft",
    )
    db.add(copy_les)
    db.commit()
    db.refresh(copy_les)
    return serialize_lesson(copy_les)


# ==============================================================================
# SUBJECT TOOLS & MATH VERIFICATION ENDPOINT
# ==============================================================================

@app.post("/api/tools/execute")
def execute_subject_tool(payload: SubjectToolRequest, db: Session = Depends(get_db)):
    ctx = db.query(EducationalContext).filter(EducationalContext.id == payload.contextId).first()
    subject_name = ctx.subject if ctx else ""
    result = run_subject_tool(
        subject=subject_name,
        tool_type=payload.toolType,
        title=payload.title,
        inputs=payload.inputs,
    )
    return result


# ==============================================================================
# PLANS, VERSIONS, AUDIT & APPROVAL ENDPOINTS
# ==============================================================================

def _save_plan_version_and_review(db: Session, pln: Plan, ctx: EducationalContext) -> PlanReview:
    src_data = None
    if pln.source_id:
        src = db.query(CurriculumSource).filter(CurriculumSource.id == pln.source_id).first()
        if src:
            src_data = serialize_source(src)
    les_data = None
    if pln.primary_lesson_id:
        les = db.query(Lesson).filter(Lesson.id == pln.primary_lesson_id).first()
        if les:
            les_data = serialize_lesson(les)

    payload_dict = {
        "id": pln.id,
        "title": pln.title,
        "planType": pln.plan_type,
        "status": pln.status,
        "lessonsCount": pln.lessons_count,
        "periodsCount": pln.periods_count,
        "periodMinutes": pln.period_minutes,
        "objectives": pln.objectives,
        "priorKnowledge": pln.prior_knowledge,
        "teacherRole": pln.teacher_role,
        "studentRole": pln.student_role,
        "teachingTools": pln.teaching_tools,
        "phases": pln.phases,
        "formativeAssessment": pln.formative_assessment,
        "differentiation": pln.differentiation,
        "homework": pln.homework,
        "subjectItems": pln.subject_items,
        "scheduleDays": pln.schedule_days,
        "slides": pln.slides,
        "presentationSettings": pln.presentation_settings,
        "contentOrigin": pln.content_origin,
        "provenanceLabel": pln.provenance_label,
    }
    sha = hashlib.sha256(json.dumps(payload_dict, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    audit_res = audit_plan_and_context(payload_dict, pln.context_snapshot or ctx.snapshot_dict(), src_data, les_data)
    if pln.status != "approved":
        pln.status = audit_res["overallStatus"]

    pver = PlanVersion(
        plan_id=pln.id,
        context_id=pln.context_id,
        version_number=pln.version,
        status_at_save=pln.status,
        context_snapshot=pln.context_snapshot or ctx.snapshot_dict(),
        plan_payload=payload_dict,
        content_sha256=sha,
        reviewer_name=pln.teacher_name or ctx.teacher_name,
    )
    db.add(pver)

    rev = PlanReview(
        plan_id=pln.id,
        context_id=pln.context_id,
        plan_version=pln.version,
        overall_status=pln.status,
        blockers_count=audit_res["blockersCount"],
        warnings_count=audit_res["warningsCount"],
        passed_count=audit_res["passedCount"],
        findings=audit_res["findings"],
    )
    db.add(rev)
    db.flush()
    return rev


@app.get("/api/plans")
def list_plans(
    contextId: str = Query(...),
    planType: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Plan).filter(Plan.context_id == contextId)
    if planType and planType.strip():
        query = query.filter(Plan.plan_type == planType.strip())
    plans = query.order_by(Plan.updated_at.desc()).all()
    return {"items": [serialize_plan(p) for p in plans]}


@app.get("/api/plans/{plan_id}")
def get_plan(plan_id: str, contextId: str = Query(...), db: Session = Depends(get_db)):
    pln = db.query(Plan).filter(Plan.id == plan_id, Plan.context_id == contextId).first()
    if not pln:
        raise HTTPException(
            status_code=404,
            detail={"code": "PLAN_NOT_FOUND_IN_CONTEXT", "message": "الخطة غير موجودة ضمن السياق النشط."},
        )
    return serialize_plan(pln)


@app.post("/api/plans", status_code=201)
def create_plan(
    payload: PlanCreate,
    x_active_context_id: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    verify_active_context_guard(payload.contextId, x_active_context_id)
    ctx = db.query(EducationalContext).filter(EducationalContext.id == payload.contextId).first()
    if not ctx:
        raise HTTPException(status_code=404, detail={"code": "CONTEXT_NOT_FOUND", "message": "السياق غير موجود."})

    # Enforce strict context isolation on sourceId and lessonIds!
    if payload.sourceId:
        src = (
            db.query(CurriculumSource)
            .filter(CurriculumSource.id == payload.sourceId, CurriculumSource.context_id == payload.contextId)
            .first()
        )
        if not src:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "CROSS_CONTEXT_SOURCE_FORBIDDEN",
                    "message": "عزل السياقات: لا يجوز ربط خطة بمصدر منهج ينتمي إلى سياق آخر.",
                },
            )

    for lid in [payload.primaryLessonId, payload.secondaryLessonId]:
        if lid:
            les = db.query(Lesson).filter(Lesson.id == lid, Lesson.context_id == payload.contextId).first()
            if not les:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "CROSS_CONTEXT_LESSON_FORBIDDEN",
                        "message": "عزل السياقات: لا يجوز ربط خطة بدرس ينتمي إلى سياق آخر.",
                    },
                )

    phases = payload.phases if payload.phases else get_default_five_stage_phases(payload.periodMinutes, payload.periodsCount)
    prov = (
        "محتوى مرتبط بالمصدر"
        if payload.contentOrigin == "documented_source"
        else "مثال توضيحي غير موثق من الكتاب"
    )
    pln = Plan(
        context_id=payload.contextId,
        source_id=payload.sourceId,
        primary_lesson_id=payload.primaryLessonId,
        secondary_lesson_id=payload.secondaryLessonId,
        title=payload.title.strip(),
        plan_type=payload.planType,
        status="draft",
        context_snapshot=ctx.snapshot_dict(),
        teacher_name=payload.teacherName.strip() or ctx.teacher_name,
        school_name=payload.schoolName.strip() or ctx.school_name,
        section_name=payload.sectionName.strip() or ctx.section_name,
        planning_date=payload.planningDate.strip() or ctx.planning_date,
        lessons_count=payload.lessonsCount,
        periods_count=payload.periodsCount,
        period_minutes=payload.periodMinutes,
        total_allocated_minutes=payload.periodsCount * payload.periodMinutes,
        objectives=payload.objectives,
        prior_knowledge=payload.priorKnowledge,
        teacher_role=payload.teacherRole,
        student_role=payload.studentRole,
        teaching_tools=payload.teachingTools or ctx.selected_tools,
        phases=phases,
        formative_assessment=payload.formativeAssessment,
        differentiation=payload.differentiation,
        homework=payload.homework,
        home_enrichment_minutes=payload.homeEnrichmentMinutes,
        references_note=payload.referencesNote,
        planning_notes=payload.planningNotes,
        subject_items=payload.subjectItems,
        schedule_days=payload.scheduleDays,
        slides=payload.slides,
        presentation_settings=payload.presentationSettings
        or {
            "title": payload.title.strip(),
            "slidesCount": 5,
            "textDirection": "rtl",
            "layoutStyle": "title_and_content",
            "companionTools": "، ".join(payload.teachingTools or ctx.selected_tools),
        },
        content_origin=payload.contentOrigin,
        provenance_label=prov,
        version=1,
    )
    db.add(pln)
    db.flush()
    _save_plan_version_and_review(db, pln, ctx)
    db.commit()
    db.refresh(pln)
    return serialize_plan(pln)


@app.put("/api/plans/{plan_id}")
def update_plan(
    plan_id: str,
    payload: PlanUpdate,
    x_active_context_id: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    verify_active_context_guard(payload.contextId, x_active_context_id)
    pln = db.query(Plan).filter(Plan.id == plan_id, Plan.context_id == payload.contextId).first()
    if not pln:
        raise HTTPException(
            status_code=404,
            detail={"code": "PLAN_NOT_FOUND_IN_CONTEXT", "message": "الخطة غير موجودة ضمن السياق النشط."},
        )

    if payload.expectedVersion is not None and payload.expectedVersion != pln.version:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "VERSION_CONFLICT",
                "message": "تم تعديل الخطة في إصدار أحدث. يرجى إعادة تحميل الخطة لمنع فقدان التعديلات.",
                "currentVersion": pln.version,
            },
        )

    if payload.sourceId:
        src = (
            db.query(CurriculumSource)
            .filter(CurriculumSource.id == payload.sourceId, CurriculumSource.context_id == payload.contextId)
            .first()
        )
        if not src:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "CROSS_CONTEXT_SOURCE_FORBIDDEN",
                    "message": "عزل السياقات: لا يجوز ربط خطة بمصدر منهج ينتمي إلى سياق آخر.",
                },
            )

    ctx = db.query(EducationalContext).filter(EducationalContext.id == payload.contextId).first()

    # Any substantive edit after approval revokes approval on the new version while keeping the previous approved version in `plan_versions`!
    pln.source_id = payload.sourceId
    pln.primary_lesson_id = payload.primaryLessonId
    pln.secondary_lesson_id = payload.secondaryLessonId
    pln.title = payload.title.strip()
    pln.plan_type = payload.planType
    pln.teacher_name = payload.teacherName.strip()
    pln.school_name = payload.schoolName.strip()
    pln.section_name = payload.sectionName.strip()
    pln.planning_date = payload.planningDate.strip()
    pln.lessons_count = payload.lessonsCount
    pln.periods_count = payload.periodsCount
    pln.period_minutes = payload.periodMinutes
    pln.total_allocated_minutes = payload.periodsCount * payload.periodMinutes
    pln.objectives = payload.objectives
    pln.prior_knowledge = payload.priorKnowledge
    pln.teacher_role = payload.teacherRole
    pln.student_role = payload.studentRole
    pln.teaching_tools = payload.teachingTools
    pln.phases = payload.phases
    pln.formative_assessment = payload.formativeAssessment
    pln.differentiation = payload.differentiation
    pln.homework = payload.homework
    pln.home_enrichment_minutes = payload.homeEnrichmentMinutes
    pln.references_note = payload.referencesNote
    pln.planning_notes = payload.planningNotes
    pln.subject_items = payload.subjectItems
    pln.schedule_days = payload.scheduleDays
    pln.slides = payload.slides
    if payload.presentationSettings:
        pln.presentation_settings = payload.presentationSettings
    pln.content_origin = payload.contentOrigin
    pln.provenance_label = (
        "محتوى مرتبط بالمصدر"
        if payload.contentOrigin == "documented_source"
        else "مثال توضيحي غير موثق من الكتاب"
    )

    # Increment version and revoke `approved` status for the new edited version
    pln.version += 1
    pln.status = "draft"
    pln.updated_at = utcnow()

    _save_plan_version_and_review(db, pln, ctx)
    db.commit()
    db.refresh(pln)
    return serialize_plan(pln)


@app.post("/api/plans/{plan_id}/audit")
def run_plan_audit_endpoint(plan_id: str, contextId: str = Query(...), db: Session = Depends(get_db)):
    pln = db.query(Plan).filter(Plan.id == plan_id, Plan.context_id == contextId).first()
    if not pln:
        raise HTTPException(status_code=404, detail={"code": "PLAN_NOT_FOUND", "message": "الخطة غير موجودة."})
    ctx = db.query(EducationalContext).filter(EducationalContext.id == contextId).first()
    rev = _save_plan_version_and_review(db, pln, ctx)
    db.commit()
    db.refresh(pln)
    return serialize_plan(pln)


@app.post("/api/plans/{plan_id}/approve")
def approve_plan_version(
    plan_id: str,
    contextId: str = Query(...),
    approverName: str = Query(default="المعلم المراجع"),
    x_active_context_id: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    verify_active_context_guard(contextId, x_active_context_id)
    pln = db.query(Plan).filter(Plan.id == plan_id, Plan.context_id == contextId).first()
    if not pln:
        raise HTTPException(status_code=404, detail={"code": "PLAN_NOT_FOUND", "message": "الخطة غير موجودة."})
    ctx = db.query(EducationalContext).filter(EducationalContext.id == contextId).first()

    rev = _save_plan_version_and_review(db, pln, ctx)
    if rev.blockers_count > 0:
        db.commit()
        raise HTTPException(
            status_code=400,
            detail={
                "code": "APPROVAL_BLOCKED_BY_DEFECTS",
                "message": f"لا يمكن اعتماد الخطة لوجود {rev.blockers_count} عوائق اعتماد (مثل نقص التقويم أو تناقض الوقت أو خطأ تخصصي).",
                "blockersCount": rev.blockers_count,
                "findings": [f for f in rev.findings if f["category"] == "BLOCKER"],
            },
        )

    pln.status = "approved"
    pln.approved_version = pln.version
    pln.approved_by = approverName.strip() or ctx.teacher_name or "المعلم المراجع"
    pln.approved_at = utcnow()
    pln.context_snapshot = ctx.snapshot_dict()
    rev.overall_status = "approved"

    # Update the PlanVersion record for this version to reflect approval
    pver = (
        db.query(PlanVersion)
        .filter(PlanVersion.plan_id == pln.id, PlanVersion.version_number == pln.version)
        .order_by(PlanVersion.created_at.desc())
        .first()
    )
    if pver:
        pver.status_at_save = "approved"
        pver.context_snapshot = pln.context_snapshot

    db.commit()
    db.refresh(pln)
    return serialize_plan(pln)


@app.post("/api/plans/{plan_id}/copy-to-context", status_code=201)
def copy_plan_to_another_context(
    plan_id: str,
    payload: PlanCopyCrossContextRequest,
    db: Session = Depends(get_db),
):
    """
    Explicitly copies a plan to another context:
    - Creates a brand new Plan record in `targetContextId` with version=1
    - Clears previous approval (`status='draft'`, `approved_version=None`)
    - Unlinks the previous context's `source_id` and `lesson_ids`
    - Captures the target context's `context_snapshot` and re-runs specialized audit!
    """
    orig = db.query(Plan).filter(Plan.id == plan_id, Plan.context_id == payload.sourceContextId).first()
    if not orig:
        raise HTTPException(status_code=404, detail={"code": "SOURCE_PLAN_NOT_FOUND", "message": "الخطة الأصلية غير موجودة."})

    target_ctx = db.query(EducationalContext).filter(EducationalContext.id == payload.targetContextId).first()
    if not target_ctx:
        raise HTTPException(status_code=404, detail={"code": "TARGET_CONTEXT_NOT_FOUND", "message": "السياق الهدف غير موجود."})

    copied = Plan(
        context_id=target_ctx.id,
        source_id=None,  # Must re-link to a source belonging to target_ctx!
        primary_lesson_id=None,
        secondary_lesson_id=None,
        title=f"{orig.title} (منقول للمراجعة)",
        plan_type=orig.plan_type,
        status="draft",
        context_snapshot=target_ctx.snapshot_dict(),
        teacher_name=target_ctx.teacher_name or orig.teacher_name,
        school_name=target_ctx.school_name or orig.school_name,
        section_name=target_ctx.section_name or orig.section_name,
        planning_date=target_ctx.planning_date or orig.planning_date,
        lessons_count=orig.lessons_count,
        periods_count=orig.periods_count,
        period_minutes=target_ctx.default_period_Minutes or orig.period_minutes,
        total_allocated_minutes=orig.periods_count * (target_ctx.default_period_Minutes or orig.period_minutes),
        objectives=list(orig.objectives or []),
        prior_knowledge=orig.prior_knowledge,
        teacher_role=orig.teacher_role,
        student_role=orig.student_role,
        teaching_tools=list(orig.teaching_tools or []),
        phases=list(orig.phases or []),
        formative_assessment=orig.formative_assessment,
        differentiation=orig.differentiation,
        homework=orig.homework,
        home_enrichment_minutes=orig.home_enrichment_minutes,
        references_note="تم نسخ الخطة إلى سياق جديد — يتطلب ربط المصدر وإعادة التحقق",
        planning_notes=payload.reviewerNote or orig.planning_notes,
        subject_items=list(orig.subject_items or []),
        schedule_days=list(orig.schedule_days or []),
        slides=list(orig.slides or []),
        presentation_settings=dict(orig.presentation_settings or {}),
        content_origin="authored_example",
        provenance_label="مثال توضيحي غير موثق من الكتاب",
        version=1,
        approved_version=None,
    )
    db.add(copied)
    db.flush()
    _save_plan_version_and_review(db, copied, target_ctx)
    db.commit()
    db.refresh(copied)
    return serialize_plan(copied)


# ==============================================================================
# DASHBOARD SUMMARY & REPORTS ENDPOINTS
# ==============================================================================

@app.get("/api/dashboard")
def get_dashboard_summary(contextId: str = Query(...), db: Session = Depends(get_db)):
    ctx = db.query(EducationalContext).filter(EducationalContext.id == contextId).first()
    if not ctx:
        raise HTTPException(status_code=404, detail={"code": "CONTEXT_NOT_FOUND", "message": "السياق غير موجود."})

    plans = db.query(Plan).filter(Plan.context_id == contextId).order_by(Plan.updated_at.desc()).all()
    sources = db.query(CurriculumSource).filter(CurriculumSource.context_id == contextId).all()
    exports = db.query(ExportTask).filter(ExportTask.context_id == contextId).order_by(ExportTask.created_at.desc()).all()

    drafts_count = sum(1 for p in plans if p.status in ("draft", "needs_revision"))
    reviewed_or_approved_count = sum(1 for p in plans if p.status in ("reviewed", "approved"))
    unverified_sources = sum(1 for s in sources if s.verification_status != "human_verified")
    plans_with_blockers = sum(
        1 for p in plans if p.reviews and sorted(p.reviews, key=lambda r: r.created_at or utcnow(), reverse=True)[0].blockers_count > 0
    )

    attention_tasks_count = plans_with_blockers + (1 if unverified_sources > 0 or not sources else 0)

    today_tasks = []
    for p in plans:
        if p.reviews:
            latest_r = sorted(p.reviews, key=lambda r: r.created_at or utcnow(), reverse=True)[0]
            for f in latest_r.findings:
                if f["category"] == "BLOCKER":
                    today_tasks.append(
                        {
                            "id": f"task_{p.id}_{f['code']}",
                            "title": f["title"],
                            "subtitle": f"{p.title} · حقل مطلوب قبل اكتمال المراجعة",
                            "badge": "أولوية",
                            "badgeType": "blocker",
                            "targetRoute": f"/daily-plan?planId={p.id}",
                        }
                    )
    if unverified_sources > 0 or not sources:
        today_tasks.append(
            {
                "id": "task_source_verify",
                "title": "راجع بيانات مصدر المنهج",
                "subtitle": "توثيق المصدر معلّق؛ المراجعة التربوية لا تمنح اعتمادًا تلقائيًا للكتاب.",
                "badge": "معلّق",
                "badgeType": "warning",
                "targetRoute": "/sources",
            }
        )
    today_tasks.append(
        {
            "id": "task_prepare_pptx",
            "title": "جهّز عرضًا قابلًا للتحرير",
            "subtitle": "بعد استكمال المراجعة · مسودة عرض من 5 شرائح قابلة للتحرير",
            "badge": "لاحقًا",
            "badgeType": "neutral",
            "targetRoute": "/presentations",
        }
    )

    return {
        "context": serialize_context(ctx),
        "stats": {
            "attentionCount": attention_tasks_count,
            "draftsCount": drafts_count,
            "totalPlansCount": len(plans),
            "reviewedCount": reviewed_or_approved_count,
            "exportsCount": len(exports),
        },
        "todayTasks": today_tasks[:5],
        "recentPlans": [serialize_plan(p) for p in plans[:6]],
        "sources": [serialize_source(s) for s in sources],
        "recentExports": [
            {
                "id": e.id,
                "exportFormat": e.export_format,
                "fileName": e.file_name,
                "fileSize": e.file_size,
                "planVersion": e.plan_version,
                "reviewStatusSnapshot": e.review_status_snapshot,
                "createdAt": e.created_at.isoformat() if e.created_at else None,
            }
            for e in exports[:5]
        ],
    }


@app.get("/api/reports")
def get_reports_summary(
    contextId: str = Query(...),
    dateFrom: Optional[str] = Query(default=None),
    dateTo: Optional[str] = Query(default=None),
    planType: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    ctx = db.query(EducationalContext).filter(EducationalContext.id == contextId).first()
    if not ctx:
        raise HTTPException(status_code=404, detail={"code": "CONTEXT_NOT_FOUND", "message": "السياق غير موجود."})

    plans = db.query(Plan).filter(Plan.context_id == contextId).all()
    if isinstance(planType, str) and planType not in ("all", ""):
        plans = [p for p in plans if p.plan_type == planType]
    if isinstance(dateFrom, str) and dateFrom.strip():
        plans = [p for p in plans if (p.planning_date or "") >= dateFrom.strip()]
    if isinstance(dateTo, str) and dateTo.strip():
        plans = [p for p in plans if (p.planning_date or "") <= dateTo.strip()]

    exports = db.query(ExportTask).filter(ExportTask.context_id == contextId).all()
    sources = db.query(CurriculumSource).filter(CurriculumSource.context_id == contextId).all()

    total_plans = len(plans)
    reviewed_plans = sum(1 for p in plans if p.status in ("reviewed", "approved"))
    draft_plans = sum(1 for p in plans if p.status in ("draft", "needs_revision"))

    patterns = []
    for p_type, label in [
        ("daily", "يومية"),
        ("weekly", "أسبوعية"),
        ("five_day", "خمسة أيام"),
    ]:
        subset = [p for p in plans if p.plan_type == p_type]
        sub_ids = {p.id for p in subset}
        sub_exports = sum(1 for e in exports if e.plan_id in sub_ids)
        doc_tag = "موثّق" if any(s.verification_status == "human_verified" for s in sources) else "تجريبي — غير موثّق"
        patterns.append(
            {
                "planType": p_type,
                "label": f"{label} · {doc_tag}",
                "planned": len(subset),
                "reviewed": sum(1 for p in subset if p.status in ("reviewed", "approved")),
                "exported": sub_exports,
            }
        )

    doc_gaps = []
    if not any(s.verification_status == "human_verified" for s in sources):
        doc_gaps.append("سجل منهج تجريبي — غير موثّق. يظهر هذا التنبيه في التقرير ولا يُزال بفحص اكتمال الخطط.")
    snap = ctx.snapshot_dict()
    if snap["missingContextFields"]:
        doc_gaps.append(f"حقول سياق غير مدخلة: {'، '.join(snap['missingContextFields'])}")

    return {
        "context": serialize_context(ctx),
        "totalPlans": total_plans,
        "reviewedPlans": reviewed_plans,
        "draftPlans": draft_plans,
        "exportsCount": len(exports),
        "patternSummary": patterns,
        "documentationGaps": doc_gaps,
        "disclaimer": "المؤشرات تقيس تنظيم التخطيط واكتماله للمعلم فقط. لا توجد بيانات متعلمين ولا نسب نجاح طلاب مفترضة.",
    }


# ==============================================================================
# REAL EXPORTS (DOCX, PDF, PPTX, REPORT PDF, BUNDLE ZIP)
# ==============================================================================

@app.get("/api/exports")
def list_exports(contextId: str = Query(...), db: Session = Depends(get_db)):
    tasks = (
        db.query(ExportTask)
        .filter(ExportTask.context_id == contextId)
        .order_by(ExportTask.created_at.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": t.id,
                "contextId": t.context_id,
                "planId": t.plan_id,
                "planVersion": t.plan_version,
                "exportFormat": t.export_format,
                "fileName": t.file_name,
                "fileSize": t.file_size,
                "contentSha256": t.content_sha256,
                "reviewStatusSnapshot": t.review_status_snapshot,
                "sourceVerificationSnapshot": t.source_verification_snapshot,
                "contextSnapshot": t.context_snapshot,
                "structuralCheckPassed": t.structural_check_passed,
                "structuralCheckDetails": t.structural_check_details,
                "createdAt": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tasks
        ]
    }


@app.post("/api/exports", status_code=201)
def create_export_task(
    payload: ExportCreateRequest,
    x_active_context_id: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    verify_active_context_guard(payload.contextId, x_active_context_id)
    ctx = db.query(EducationalContext).filter(EducationalContext.id == payload.contextId).first()
    if not ctx:
        raise HTTPException(status_code=404, detail={"code": "CONTEXT_NOT_FOUND", "message": "السياق غير موجود."})

    sources = db.query(CurriculumSource).filter(CurriculumSource.context_id == payload.contextId).all()
    source_status = (
        "human_verified"
        if any(s.verification_status == "human_verified" for s in sources)
        else "unverified_draft"
    )

    plan_snap = {}
    context_snap = ctx.snapshot_dict()
    review_snap = {"findings": []}
    plan_ver_num = 1
    plan_id = payload.planId

    if plan_id:
        pln = db.query(Plan).filter(Plan.id == plan_id, Plan.context_id == payload.contextId).first()
        if not pln:
            raise HTTPException(
                status_code=404,
                detail={"code": "PLAN_NOT_FOUND_IN_CONTEXT", "message": "الخطة المطلوبة غير موجودة في هذا السياق."},
            )
        target_ver = payload.planVersion or pln.version
        pver = (
            db.query(PlanVersion)
            .filter(PlanVersion.plan_id == pln.id, PlanVersion.version_number == target_ver)
            .order_by(PlanVersion.created_at.desc())
            .first()
        )
        if pver:
            plan_snap = dict(pver.plan_payload)
            plan_snap["version"] = pver.version_number
            plan_snap["status"] = pver.status_at_save
            context_snap = dict(pver.context_snapshot or ctx.snapshot_dict())
            plan_ver_num = pver.version_number
        else:
            plan_snap = serialize_plan(pln)
            context_snap = dict(pln.context_snapshot or ctx.snapshot_dict())
            plan_ver_num = pln.version

        rev = (
            db.query(PlanReview)
            .filter(PlanReview.plan_id == pln.id, PlanReview.plan_version == plan_ver_num)
            .order_by(PlanReview.created_at.desc())
            .first()
        )
        if rev:
            review_snap = {"findings": rev.findings}
    else:
        # Use most recent plan in context if none specified
        first_pln = db.query(Plan).filter(Plan.context_id == payload.contextId).order_by(Plan.updated_at.desc()).first()
        if first_pln:
            plan_id = first_pln.id
            plan_snap = serialize_plan(first_pln)
            plan_ver_num = first_pln.version

    fmt = payload.exportFormat.lower().strip()
    timestamp_tag = datetime.now().strftime("%Y%m%d_%H%M%S")

    if fmt == "docx":
        file_bytes = generate_plan_docx_bytes(plan_snap, context_snap, review_snap, source_status)
        ext = "docx"
    elif fmt == "pptx":
        file_bytes = generate_plan_pptx_bytes(plan_snap, context_snap, source_status)
        ext = "pptx"
    elif fmt == "pdf":
        file_bytes = generate_plan_pdf_bytes(plan_snap, context_snap, review_snap, source_status, is_report=False)
        ext = "pdf"
    elif fmt == "report_pdf":
        rep_summary = get_reports_summary(
            contextId=payload.contextId,
            dateFrom=payload.dateFrom,
            dateTo=payload.dateTo,
            planType=payload.planTypeFilter,
            db=db,
        )
        file_bytes = generate_plan_pdf_bytes(
            plan_snap, context_snap, review_snap, source_status, is_report=True, report_summary=rep_summary
        )
        ext = "pdf"
    elif fmt == "report_docx":
        rep_summary = get_reports_summary(
            contextId=payload.contextId,
            dateFrom=payload.dateFrom,
            dateTo=payload.dateTo,
            planType=payload.planTypeFilter,
            db=db,
        )
        rep_plan_snap = {
            "title": "تقرير التخطيط والاكتمال للمعلم",
            "status": "reviewed",
            "version": 1,
            "planType": "daily",
            "periodsCount": 1,
            "periodMinutes": 45,
            "objectives": [
                f"إجمالي الخطط المحفوظة: {rep_summary['totalPlans']}",
                f"الخطط مكتملة المراجعة: {rep_summary['reviewedPlans']}",
                f"المسودات قيد الإعداد: {rep_summary['draftPlans']}",
            ],
            "phases": [],
            "formativeAssessment": rep_summary["disclaimer"],
            "provenanceLabel": "تقرير مشتق من بيانات التخطيط الفعلية",
        }
        file_bytes = generate_plan_docx_bytes(rep_plan_snap, context_snap, review_snap, source_status)
        ext = "docx"
    elif fmt == "bundle_zip":
        docx_b = generate_plan_docx_bytes(plan_snap, context_snap, review_snap, source_status)
        pdf_b = generate_plan_pdf_bytes(plan_snap, context_snap, review_snap, source_status, is_report=False)
        pptx_b = generate_plan_pptx_bytes(plan_snap, context_snap, source_status)
        rep_summary = get_reports_summary(contextId=payload.contextId, db=db)
        rep_pdf_b = generate_plan_pdf_bytes(
            plan_snap, context_snap, review_snap, source_status, is_report=True, report_summary=rep_summary
        )
        source_json_b = json.dumps(
            {
                "contextSnapshot": context_snap,
                "sourceVerificationStatus": source_status,
                "sources": [serialize_source(s) for s in sources],
                "planVersion": plan_ver_num,
                "exportedAt": utcnow().isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")

        z_buf = io.BytesIO()
        with zipfile.ZipFile(z_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("1_daily_plan_editable.docx", docx_b)
            zf.writestr("2_daily_plan_printable.pdf", pdf_b)
            zf.writestr("3_presentation_slides_editable.pptx", pptx_b)
            zf.writestr("4_planning_completion_report.pdf", rep_pdf_b)
            zf.writestr("5_curriculum_source_metadata.json", source_json_b)
        file_bytes = z_buf.getvalue()
        ext = "zip"
    else:
        raise HTTPException(status_code=400, detail={"code": "UNSUPPORTED_EXPORT_FORMAT", "message": f"صيغة التصدير غير مدعومة: {fmt}"})

    struct_check = verify_exported_file_structure(file_bytes, fmt)
    if not struct_check.get("passed"):
        raise HTTPException(
            status_code=500,
            detail={"code": "EXPORT_STRUCTURAL_VALIDATION_FAILED", "message": "فشل الفحص البنيوي للملف المصدّر."},
        )

    sha256_hex = hashlib.sha256(file_bytes).hexdigest()
    file_name = f"teacher_{fmt}_v{plan_ver_num}_{timestamp_tag}.{ext}"
    file_path = os.path.join(EXPORTS_DIR, f"{payload.contextId}_{uuid.uuid4().hex[:8]}_{file_name}")
    with open(file_path, "wb") as f_out:
        f_out.write(file_bytes)

    task = ExportTask(
        context_id=payload.contextId,
        plan_id=plan_id,
        plan_version=plan_ver_num,
        export_format=fmt,
        file_name=file_name,
        file_path=file_path,
        file_size=len(file_bytes),
        content_sha256=sha256_hex,
        review_status_snapshot=plan_snap.get("status", "draft"),
        source_verification_snapshot=source_status,
        context_snapshot=context_snap,
        structural_check_passed=True,
        structural_check_details=struct_check,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return {
        "id": task.id,
        "contextId": task.context_id,
        "planId": task.plan_id,
        "planVersion": task.plan_version,
        "exportFormat": task.export_format,
        "fileName": task.file_name,
        "fileSize": task.file_size,
        "contentSha256": task.content_sha256,
        "reviewStatusSnapshot": task.review_status_snapshot,
        "sourceVerificationSnapshot": task.source_verification_snapshot,
        "contextSnapshot": task.context_snapshot,
        "structuralCheckPassed": task.structural_check_passed,
        "structuralCheckDetails": task.structural_check_details,
        "downloadUrl": f"/api/exports/{task.id}/download?contextId={task.context_id}",
        "createdAt": task.created_at.isoformat() if task.created_at else None,
    }


@app.get("/api/exports/{export_id}/download")
def download_exported_file(
    export_id: str,
    contextId: str = Query(...),
    db: Session = Depends(get_db),
):
    task = db.query(ExportTask).filter(ExportTask.id == export_id, ExportTask.context_id == contextId).first()
    if not task or not os.path.isfile(task.file_path):
        raise HTTPException(
            status_code=404,
            detail={"code": "EXPORT_FILE_NOT_FOUND", "message": "الملف المصدّر غير موجود ضمن هذا السياق."},
        )

    mime_map = {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "report_docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "pdf": "application/pdf",
        "report_pdf": "application/pdf",
        "bundle_zip": "application/zip",
    }
    media_type = mime_map.get(task.export_format, "application/octet-stream")
    with open(task.file_path, "rb") as f_in:
        data = f_in.read()

    return Response(
        content=data,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{task.file_name}"',
            "X-Content-SHA256": task.content_sha256,
            "X-Plan-Version": str(task.plan_version),
        },
    )
