import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship
from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


def gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class EducationalContext(Base):
    """
    Explicit saved educational context with the 7 required fields:
    {subject, grade, country, curriculumName, language, year, edition}
    plus teacher & schedule settings.
    Unknown fields remain empty string '' with explicit warning instead of guessing.
    """
    __tablename__ = "educational_contexts"

    id = Column(String(64), primary_key=True, default=lambda: gen_id("ctx"))
    owner_id = Column(String(64), nullable=False, default="teacher_default", index=True)

    # The 7 explicit context fields
    subject = Column(String(200), nullable=False, default="")
    grade = Column(String(200), nullable=False, default="")
    country = Column(String(200), nullable=False, default="")
    curriculum_name = Column(String(300), nullable=False, default="")
    language = Column(String(32), nullable=False, default="ar")
    year = Column(String(64), nullable=False, default="")
    edition = Column(String(120), nullable=False, default="")

    # Teacher & School Settings
    ui_language = Column(String(32), nullable=False, default="ar")
    teacher_name = Column(String(200), nullable=False, default="")
    school_name = Column(String(200), nullable=False, default="")
    section_name = Column(String(120), nullable=False, default="")
    planning_date = Column(String(64), nullable=False, default="")
    school_days = Column(JSON, nullable=False, default=lambda: ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس"])
    holidays = Column(JSON, nullable=False, default=lambda: ["الجمعة", "السبت"])
    default_period_Minutes = Column(Integer, nullable=False, default=45)
    default_periods_count = Column(Integer, nullable=False, default=1)
    selected_tools = Column(JSON, nullable=False, default=lambda: ["سبورة", "أقلام ملوّنة", "مسطرة", "بطاقات تعليمية"])
    document_preferences = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "paperSize": "A4",
            "includeSourceBanner": True,
            "includeTeacherSignature": True,
            "fontFamily": "Arial",
            "mathDirection": "ltr",
        },
    )
    active_template_id = Column(String(64), nullable=True)

    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    # Relationships
    templates = relationship("PhaseTemplate", back_populates="context", cascade="all, delete-orphan")
    sources = relationship("CurriculumSource", back_populates="context", cascade="all, delete-orphan")
    lessons = relationship("Lesson", back_populates="context", cascade="all, delete-orphan")
    plans = relationship("Plan", back_populates="context", cascade="all, delete-orphan")
    exports = relationship("ExportTask", back_populates="context", cascade="all, delete-orphan")

    def snapshot_dict(self) -> dict:
        missing_fields = []
        field_map = {
            "subject": self.subject,
            "grade": self.grade,
            "country": self.country,
            "curriculumName": self.curriculum_name,
            "language": self.language,
            "year": self.year,
            "edition": self.edition,
        }
        for k, v in field_map.items():
            if not v or not str(v).strip():
                missing_fields.append(k)
        return {
            "contextId": self.id,
            "subject": self.subject,
            "grade": self.grade,
            "country": self.country,
            "curriculumName": self.curriculum_name,
            "language": self.language,
            "year": self.year,
            "edition": self.edition,
            "teacherName": self.teacher_name,
            "schoolName": self.school_name,
            "sectionName": self.section_name,
            "defaultPeriodMinutes": self.default_period_Minutes,
            "missingContextFields": missing_fields,
        }


class PhaseTemplate(Base):
    """
    Customizable phase template per context.
    Supports the 5-stage default from photo_2026-10-31_15-58-11.jpg:
    1. التهيئة
    2. التدريس (الشرح والتفسير)
    3. التدريب
    4. التقويم
    5. التوسعة والإثراء
    as well as interactive/literature/history/science templates and custom user templates.
    """
    __tablename__ = "phase_templates"

    id = Column(String(64), primary_key=True, default=lambda: gen_id("tpl"))
    context_id = Column(String(64), ForeignKey("educational_contexts.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, default="")
    is_default = Column(Boolean, nullable=False, default=False)
    periods_count = Column(Integer, nullable=False, default=1)
    period_minutes = Column(Integer, nullable=False, default=45)
    phases = Column(JSON, nullable=False, default=list)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    context = relationship("EducationalContext", back_populates="templates")


class CurriculumSource(Base):
    """
    Curriculum Source (Book/Guide PDF or Manual Source Record) strictly isolated by context_id.
    Stores SHA-256 fingerprint, edition, book_year, verification_status, reviewer_name, reviewed_at.
    """
    __tablename__ = "curriculum_sources"

    id = Column(String(64), primary_key=True, default=lambda: gen_id("src"))
    context_id = Column(String(64), ForeignKey("educational_contexts.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    source_type = Column(String(64), nullable=False, default="unverified_example")  # pdf_upload | unverified_example | external_reference
    file_name = Column(String(300), nullable=False, default="")
    file_path = Column(String(500), nullable=False, default="")
    file_size = Column(Integer, nullable=False, default=0)
    sha256_fingerprint = Column(String(128), nullable=False, default="")
    mime_type = Column(String(100), nullable=False, default="")
    page_count = Column(Integer, nullable=False, default=0)
    extraction_status = Column(String(64), nullable=False, default="no_file")  # extracted_text | requires_ocr_or_manual | no_file
    book_year = Column(String(64), nullable=False, default="")
    edition = Column(String(120), nullable=False, default="")
    source_url = Column(String(500), nullable=False, default="")
    is_official_claimed = Column(Boolean, nullable=False, default=False)
    official_evidence = Column(Text, nullable=False, default="")
    verification_status = Column(String(64), nullable=False, default="pending_review")  # unverified_draft | pending_review | human_verified | rejected
    reviewer_name = Column(String(200), nullable=False, default="")
    review_notes = Column(Text, nullable=False, default="")
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    index_approved = Column(Boolean, nullable=False, default=False)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    context = relationship("EducationalContext", back_populates="sources")
    pages = relationship("SourcePage", back_populates="source", cascade="all, delete-orphan")
    chapters = relationship("Chapter", back_populates="source", cascade="all, delete-orphan")


class SourcePage(Base):
    """
    Stores both PDF page number and printed page number separately, plus extracted/corrected text
    and ambiguous OCR tokens (names, quotes, dates, signs, exponents, fractions).
    """
    __tablename__ = "source_pages"

    id = Column(String(64), primary_key=True, default=lambda: gen_id("pg"))
    source_id = Column(String(64), ForeignKey("curriculum_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    pdf_page_number = Column(Integer, nullable=False)
    printed_page_number = Column(String(32), nullable=False, default="")
    extracted_text = Column(Text, nullable=False, default="")
    corrected_text = Column(Text, nullable=False, default="")
    needs_ocr_review = Column(Boolean, nullable=False, default=False)
    ocr_ambiguities = Column(JSON, nullable=False, default=list)
    human_reviewed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    source = relationship("CurriculumSource", back_populates="pages")


class Chapter(Base):
    """
    Documented chapter linked to a CurriculumSource. Never fabricated from memory.
    """
    __tablename__ = "chapters"

    id = Column(String(64), primary_key=True, default=lambda: gen_id("ch"))
    context_id = Column(String(64), ForeignKey("educational_contexts.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(String(64), ForeignKey("curriculum_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    order_index = Column(Integer, nullable=False, default=1)
    pdf_start_page = Column(Integer, nullable=True)
    printed_start_page = Column(String(32), nullable=False, default="")
    is_documented = Column(Boolean, nullable=False, default=False)
    provenance_label = Column(String(120), nullable=False, default="مثال توضيحي غير موثق من الكتاب")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    source = relationship("CurriculumSource", back_populates="chapters")
    lessons = relationship("Lesson", back_populates="chapter")


class Lesson(Base):
    """
    Lesson record strictly scoped to context_id.
    Separates authored content ('مثال توضيحي غير موثق من الكتاب') from documented source content.
    """
    __tablename__ = "lessons"

    id = Column(String(64), primary_key=True, default=lambda: gen_id("les"))
    context_id = Column(String(64), ForeignKey("educational_contexts.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(String(64), ForeignKey("curriculum_sources.id", ondelete="SET NULL"), nullable=True, index=True)
    chapter_id = Column(String(64), ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True, index=True)

    title = Column(String(300), nullable=False)
    code_or_order = Column(String(64), nullable=False, default="1")
    pdf_page_number = Column(Integer, nullable=True)
    printed_page_number = Column(String(32), nullable=False, default="")
    content_origin = Column(String(64), nullable=False, default="authored_example")  # documented_source | authored_example
    provenance_label = Column(String(160), nullable=False, default="مثال توضيحي غير موثق من الكتاب")

    objectives = Column(JSON, nullable=False, default=list)
    prior_knowledge = Column(Text, nullable=False, default="")
    activities = Column(JSON, nullable=False, default=list)
    questions_and_solutions = Column(JSON, nullable=False, default=list)
    evaluation_criteria = Column(Text, nullable=False, default="")
    key_terms_or_quotes = Column(JSON, nullable=False, default=list)

    review_status = Column(String(64), nullable=False, default="draft")  # draft | needs_revision | reviewed | approved
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    context = relationship("EducationalContext", back_populates="lessons")
    chapter = relationship("Chapter", back_populates="lessons")


class Plan(Base):
    """
    Supports daily (1 or 2 lessons, 1 or 2 periods), weekly (actual school days & holidays),
    and five_day (5 distinct teaching days).
    Uses optimistic concurrency via `version` and stores `context_snapshot` on every version/approval.
    """
    __tablename__ = "plans"

    id = Column(String(64), primary_key=True, default=lambda: gen_id("pln"))
    context_id = Column(String(64), ForeignKey("educational_contexts.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(String(64), ForeignKey("curriculum_sources.id", ondelete="SET NULL"), nullable=True, index=True)
    primary_lesson_id = Column(String(64), ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True)
    secondary_lesson_id = Column(String(64), ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True)

    title = Column(String(300), nullable=False)
    plan_type = Column(String(32), nullable=False, default="daily")  # daily | weekly | five_day
    status = Column(String(64), nullable=False, default="draft")  # draft | needs_revision | reviewed | approved

    # Snapshot of context fields at creation/last approval so editing context later never alters historical plans silently
    context_snapshot = Column(JSON, nullable=False, default=dict)

    teacher_name = Column(String(200), nullable=False, default="")
    school_name = Column(String(200), nullable=False, default="")
    section_name = Column(String(120), nullable=False, default="")
    planning_date = Column(String(64), nullable=False, default="")

    # Lessons & Periods configuration
    lessons_count = Column(Integer, nullable=False, default=1)  # 1 or 2
    periods_count = Column(Integer, nullable=False, default=1)  # 1 or 2
    period_minutes = Column(Integer, nullable=False, default=45)  # e.g. 45
    total_allocated_minutes = Column(Integer, nullable=False, default=45)

    # Pedagogical fields
    objectives = Column(JSON, nullable=False, default=list)
    prior_knowledge = Column(Text, nullable=False, default="")
    teacher_role = Column(Text, nullable=False, default="")
    student_role = Column(Text, nullable=False, default="")
    teaching_tools = Column(JSON, nullable=False, default=list)
    phases = Column(JSON, nullable=False, default=list)
    formative_assessment = Column(Text, nullable=False, default="")
    differentiation = Column(Text, nullable=False, default="")
    homework = Column(Text, nullable=False, default="")
    home_enrichment_minutes = Column(Integer, nullable=False, default=0)  # explicitly excluded from class period sum
    references_note = Column(Text, nullable=False, default="")
    planning_notes = Column(Text, nullable=False, default="")

    # Subject-specific content & verification items (math equations, literature quotes, history events, etc.)
    subject_items = Column(JSON, nullable=False, default=list)

    # Weekly / Five-day schedule items
    schedule_days = Column(JSON, nullable=False, default=list)

    # Presentation slides linked to this plan
    slides = Column(JSON, nullable=False, default=list)
    presentation_settings = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "title": "",
            "slidesCount": 5,
            "textDirection": "rtl",
            "layoutStyle": "title_and_content",
            "companionTools": "سبورة، أقلام ملوّنة، مسطرة، بطاقات تعليمية",
        },
    )

    content_origin = Column(String(64), nullable=False, default="authored_example")
    provenance_label = Column(String(160), nullable=False, default="مثال توضيحي غير موثق من الكتاب")

    version = Column(Integer, nullable=False, default=1)
    approved_version = Column(Integer, nullable=True)
    approved_by = Column(String(200), nullable=False, default="")
    approved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    context = relationship("EducationalContext", back_populates="plans")
    versions = relationship("PlanVersion", back_populates="plan", cascade="all, delete-orphan")
    reviews = relationship("PlanReview", back_populates="plan", cascade="all, delete-orphan")


class PlanVersion(Base):
    """
    Immutable historical snapshot of a saved/approved plan version.
    Exports bind to a specific (plan_id, version_number) so later edits do not mutate previous exports.
    """
    __tablename__ = "plan_versions"

    id = Column(String(64), primary_key=True, default=lambda: gen_id("pver"))
    plan_id = Column(String(64), ForeignKey("plans.id", ondelete="CASCADE"), nullable=False, index=True)
    context_id = Column(String(64), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    status_at_save = Column(String(64), nullable=False, default="draft")
    context_snapshot = Column(JSON, nullable=False, default=dict)
    plan_payload = Column(JSON, nullable=False, default=dict)
    content_sha256 = Column(String(128), nullable=False, default="")
    reviewer_name = Column(String(200), nullable=False, default="")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    plan = relationship("Plan", back_populates="versions")


class PlanReview(Base):
    """
    Stores the result of an independent/automated specialized review for a specific plan version.
    Separates blockers ('BLOCKER') from source warnings ('SOURCE_WARNING') and passed checks ('PASSED').
    """
    __tablename__ = "plan_reviews"

    id = Column(String(64), primary_key=True, default=lambda: gen_id("rev"))
    plan_id = Column(String(64), ForeignKey("plans.id", ondelete="CASCADE"), nullable=False, index=True)
    context_id = Column(String(64), nullable=False, index=True)
    plan_version = Column(Integer, nullable=False)
    overall_status = Column(String(64), nullable=False)  # draft | needs_revision | reviewed | approved
    blockers_count = Column(Integer, nullable=False, default=0)
    warnings_count = Column(Integer, nullable=False, default=0)
    passed_count = Column(Integer, nullable=False, default=0)
    findings = Column(JSON, nullable=False, default=list)
    reviewer_name = Column(String(200), nullable=False, default="محرك التدقيق التخصصي المستقل")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    plan = relationship("Plan", back_populates="reviews")


class ExportTask(Base):
    """
    Tracks real generated files (DOCX, PDF, PPTX, Report PDF, Package ZIP/Bundle) tied to a specific PlanVersion.
    """
    __tablename__ = "export_tasks"

    id = Column(String(64), primary_key=True, default=lambda: gen_id("exp"))
    context_id = Column(String(64), ForeignKey("educational_contexts.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(String(64), ForeignKey("plans.id", ondelete="SET NULL"), nullable=True, index=True)
    plan_version = Column(Integer, nullable=False, default=1)
    export_format = Column(String(32), nullable=False)  # docx | pdf | pptx | report_pdf | report_docx | bundle_zip
    file_name = Column(String(300), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False, default=0)
    content_sha256 = Column(String(128), nullable=False, default="")
    review_status_snapshot = Column(String(64), nullable=False, default="draft")
    source_verification_snapshot = Column(String(64), nullable=False, default="unverified_draft")
    context_snapshot = Column(JSON, nullable=False, default=dict)
    structural_check_passed = Column(Boolean, nullable=False, default=False)
    structural_check_details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    context = relationship("EducationalContext", back_populates="exports")
