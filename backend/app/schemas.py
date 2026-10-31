from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EducationalContextCreate(BaseModel):
    subject: str = Field(default="", description="المادة الدراسية (مثال: الرياضيات، اللغة العربية، التاريخ، الفيزياء...)")
    grade: str = Field(default="", description="الصف أو المرحلة الدراسية")
    country: str = Field(default="", description="البلد")
    curriculumName: str = Field(default="", description="اسم المنهج")
    language: str = Field(default="ar", description="لغة السياق والمحتوى")
    year: str = Field(default="", description="السنة الدراسية أو سنة الكتاب")
    edition: str = Field(default="", description="رقم أو اسم الطبعة")
    uiLanguage: str = Field(default="ar", description="لغة الواجهة")
    teacherName: str = Field(default="")
    schoolName: str = Field(default="")
    sectionName: str = Field(default="")
    planningDate: str = Field(default="")
    schoolDays: List[str] = Field(default_factory=lambda: ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس"])
    holidays: List[str] = Field(default_factory=lambda: ["الجمعة", "السبت"])
    defaultPeriodMinutes: int = Field(default=45, ge=5, le=240)
    defaultPeriodsCount: int = Field(default=1, ge=1, le=2)
    selectedTools: List[str] = Field(default_factory=lambda: ["سبورة", "أقلام ملوّنة", "مسطرة", "بطاقات تعليمية"])
    documentPreferences: Dict[str, Any] = Field(default_factory=dict)


class EducationalContextUpdate(EducationalContextCreate):
    expectedVersion: Optional[int] = Field(default=None, description="لمنع استبدال تعديل أحدث بتعديل قديم")


class PhaseItemSchema(BaseModel):
    order: int = 1
    periodNumber: int = Field(default=1, ge=1, le=2)
    phaseName: str
    materials: str = ""
    sourceRef: str = "المقرّر / الدليل"
    executorRole: str = ""
    teacherActivity: str = ""
    studentActivity: str = ""
    objective: str = ""
    minutes: int = Field(default=5, ge=0)
    isHomeEnrichment: bool = False


class PhaseTemplateCreate(BaseModel):
    contextId: str
    name: str
    description: str = ""
    isDefault: bool = False
    periodsCount: int = Field(default=1, ge=1, le=2)
    periodMinutes: int = Field(default=45, ge=5, le=240)
    phases: List[PhaseItemSchema]


class SourceMetadataUpdate(BaseModel):
    contextId: str
    title: str
    bookYear: str = ""
    edition: str = ""
    sourceUrl: str = ""
    isOfficialClaimed: bool = False
    officialEvidence: str = ""
    reviewerName: str = ""
    reviewNotes: str = ""
    verificationStatus: Optional[str] = None
    indexApproved: Optional[bool] = None
    expectedVersion: Optional[int] = None


class SourcePageUpdate(BaseModel):
    contextId: str
    printedPageNumber: str = ""
    correctedText: str = ""
    humanReviewed: bool = True


class ChapterCreate(BaseModel):
    contextId: str
    sourceId: str
    title: str
    orderIndex: int = 1
    pdfStartPage: Optional[int] = None
    printedStartPage: str = ""
    isDocumented: bool = False


class LessonCreate(BaseModel):
    contextId: str
    sourceId: Optional[str] = None
    chapterId: Optional[str] = None
    title: str
    codeOrOrder: str = "1"
    pdfPageNumber: Optional[int] = None
    printedPageNumber: str = ""
    contentOrigin: str = "authored_example"
    objectives: List[str] = Field(default_factory=list)
    priorKnowledge: str = ""
    activities: List[Dict[str, Any]] = Field(default_factory=list)
    questionsAndSolutions: List[Dict[str, Any]] = Field(default_factory=list)
    evaluationCriteria: str = ""
    keyTermsOrQuotes: List[Dict[str, Any]] = Field(default_factory=list)


class LessonUpdate(LessonCreate):
    expectedVersion: Optional[int] = None


class PlanCreate(BaseModel):
    contextId: str
    sourceId: Optional[str] = None
    primaryLessonId: Optional[str] = None
    secondaryLessonId: Optional[str] = None
    title: str
    planType: str = "daily"  # daily | weekly | five_day
    teacherName: str = ""
    schoolName: str = ""
    sectionName: str = ""
    planningDate: str = ""
    lessonsCount: int = Field(default=1, ge=1, le=2)
    periodsCount: int = Field(default=1, ge=1, le=2)
    periodMinutes: int = Field(default=45, ge=5, le=240)
    objectives: List[str] = Field(default_factory=list)
    priorKnowledge: str = ""
    teacherRole: str = ""
    studentRole: str = ""
    teachingTools: List[str] = Field(default_factory=list)
    phases: List[Dict[str, Any]] = Field(default_factory=list)
    formativeAssessment: str = ""
    differentiation: str = ""
    homework: str = ""
    homeEnrichmentMinutes: int = Field(default=0, ge=0)
    referencesNote: str = ""
    planningNotes: str = ""
    subjectItems: List[Dict[str, Any]] = Field(default_factory=list)
    scheduleDays: List[Dict[str, Any]] = Field(default_factory=list)
    slides: List[Dict[str, Any]] = Field(default_factory=list)
    presentationSettings: Dict[str, Any] = Field(default_factory=dict)
    contentOrigin: str = "authored_example"


class PlanUpdate(PlanCreate):
    expectedVersion: Optional[int] = None


class PlanCopyCrossContextRequest(BaseModel):
    sourceContextId: str
    targetContextId: str
    reviewerNote: str = ""


class SubjectToolRequest(BaseModel):
    contextId: str
    toolType: str  # math_solver | text_analysis | historical_timeline | science_experiment | worksheet_generator
    title: str = ""
    inputs: Dict[str, Any] = Field(default_factory=dict)


class ExportCreateRequest(BaseModel):
    contextId: str
    planId: Optional[str] = None
    planVersion: Optional[int] = None
    exportFormat: str  # docx | pdf | pptx | report_pdf | report_docx | bundle_zip
    dateFrom: Optional[str] = None
    dateTo: Optional[str] = None
    planTypeFilter: Optional[str] = None

