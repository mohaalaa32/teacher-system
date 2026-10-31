import pytest
from backend.app.services.audit_service import audit_plan_and_context, run_subject_tool, safe_eval_math_expression


def test_math_safe_eval_and_zero_division():
    assert safe_eval_math_expression("5 + 15 + 12 + 8 + 5") == 45.0
    assert safe_eval_math_expression("(18 - 6) * 3 / 4") == 9.0
    with pytest.raises(ZeroDivisionError):
        safe_eval_math_expression("100 / (5 - 5)")


def test_audit_time_contradiction_and_two_periods():
    # Two periods of 45 minutes = 90 minutes expected
    plan_data = {
        "planType": "daily",
        "periodsCount": 2,
        "periodMinutes": 45,
        "objectives": ["هدف أول"],
        "formativeAssessment": "مهمة تقويمية واضحة",
        "teachingTools": ["سبورة"],
        "phases": [
            {"phaseName": "التهيئة", "minutes": 10, "isHomeEnrichment": False},
            {"phaseName": "التدريس", "minutes": 30, "isHomeEnrichment": False},
            {"phaseName": "التدريب", "minutes": 25, "isHomeEnrichment": False},
            {"phaseName": "التقويم", "minutes": 15, "isHomeEnrichment": False},
            {"phaseName": "التوسعة", "minutes": 5, "isHomeEnrichment": False},  # Sum = 85 != 90!
            {"phaseName": "إثراء منزلي خارج المجموع", "minutes": 20, "isHomeEnrichment": True},
        ],
    }
    ctx_data = {
        "subject": "الفيزياء",
        "grade": "الرابع العلمي",
        "country": "العراق",
        "curriculumName": "الفيزياء",
        "language": "ar",
        "year": "2026",
        "edition": "الأولى",
    }
    res_mismatch = audit_plan_and_context(plan_data, ctx_data)
    assert res_mismatch["canApprove"] is False
    codes = [f["code"] for f in res_mismatch["findings"]]
    assert "TIME_DISTRIBUTION_MISMATCH" in codes

    # Fix the 5th phase to 10 minutes so in-class sum = 90 (while home enrichment 20 min remains excluded)
    plan_data["phases"][4]["minutes"] = 10
    res_valid = audit_plan_and_context(plan_data, ctx_data)
    assert res_valid["canApprove"] is True
    codes_valid = [f["code"] for f in res_valid["findings"]]
    assert "TIME_DISTRIBUTION_VALID" in codes_valid


def test_history_and_science_tools():
    hist_bad = run_subject_tool(
        "التاريخ",
        "historical_timeline",
        "أحداث تاريخية",
        {
            "events": [
                {"year": "1958", "event": "إعلان الجمهورية", "evidence": "وثيقة رسمية"},
                {"year": "1921", "event": "تأسيس الدولة الحديثة", "evidence": "محاضر تاريخية"},
            ]
        },
    )
    assert hist_bad["valid"] is False
    assert hist_bad["errorCode"] == "HISTORY_CHRONOLOGY_ERROR"

    sci_ok = run_subject_tool(
        "الكيمياء",
        "science_experiment",
        "تأثير درجة الحرارة على الذوبانية",
        {
            "hypothesis": "تزداد ذوبانية الملح بارتفاع درجة الحرارة",
            "variables": "المستقل: الحرارة | التابع: كمية المذاب",
            "unit": "g/100mL",
            "safety": "ارتداء القفازات والنظارات الواقية",
        },
    )
    assert sci_ok["valid"] is True
    assert "g/100mL" in sci_ok["editableOutput"]

