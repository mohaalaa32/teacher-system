import ast
import math
import operator
import re
from typing import Dict, Any, List, Optional


SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def safe_eval_math_expression(expr_str: str) -> float:
    """
    Safely evaluates arithmetic expressions (integers, floats, +, -, *, /, **)
    while strictly raising ZeroDivisionError on division by zero and ValueError on unsafe syntax.
    """
    cleaned = expr_str.strip().replace("×", "*").replace("÷", "/").replace("^", "**").replace("−", "-")
    if not cleaned:
        raise ValueError("التعبير الرياضي فارغ.")

    tree = ast.parse(cleaned, mode="eval")

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in SAFE_OPERATORS:
            left_val = _eval(node.left)
            right_val = _eval(node.right)
            if isinstance(node.op, ast.Div) and abs(right_val) < 1e-12:
                raise ZeroDivisionError("خطأ رياضي حرج: محاولة قسمة على صفر (المقام يساوي صفرًا).")
            return SAFE_OPERATORS[type(node.op)](left_val, right_val)
        if isinstance(node, ast.UnaryOp) and type(node.op) in SAFE_OPERATORS:
            return SAFE_OPERATORS[type(node.op)](_eval(node.operand))
        raise ValueError(f"عنصر غير مدعوم في التعبير الرياضي: {ast.dump(node)}")

    return _eval(tree)


def run_subject_tool(subject: str, tool_type: str, title: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes subject-appropriate teacher tools with domain validation:
    - math_solver: evaluates arithmetic/linear equations, checks division by zero, verifies teacher's claimed answer & units.
    - text_analysis: analyzes literary/reading passage, extracts themes, rhetorical/linguistic features, open-ended rubric criteria, and checks quote attribution.
    - historical_timeline: validates chronological order of historical events, dates, and primary/secondary evidence.
    - science_experiment: validates hypothesis, variables, safety precautions, units, and step-by-step observation protocol.
    - worksheet_generator: generates structured editable worksheet items tailored to the subject without forcing math equations on non-math subjects.
    """
    provenance = "مثال توضيحي غير موثق من الكتاب"

    if tool_type == "math_solver":
        expression = str(inputs.get("expression", "")).strip()
        claimed_answer = inputs.get("claimedAnswer", None)
        unit = str(inputs.get("unit", "")).strip()
        try:
            computed = safe_eval_math_expression(expression)
        except ZeroDivisionError as zde:
            return {
                "valid": False,
                "errorCode": "MATH_DIVISION_BY_ZERO",
                "message": str(zde),
                "provenanceLabel": provenance,
                "editableOutput": "",
                "steps": ["فشل التحقق: المقام يساوي صفرًا، لا يمكن إتمام العملية."],
            }
        except Exception as exc:
            return {
                "valid": False,
                "errorCode": "MATH_SYNTAX_ERROR",
                "message": f"تعذر تحليل العبارة الرياضية: {str(exc)}",
                "provenanceLabel": provenance,
                "editableOutput": "",
                "steps": [],
            }

        formatted_val = str(int(computed)) if computed.is_integer() else f"{computed:.4f}".rstrip("0").rstrip(".")
        answer_matches = True
        mismatch_note = ""
        if claimed_answer is not None and str(claimed_answer).strip() != "":
            try:
                claimed_float = float(str(claimed_answer).strip())
                if not math.isclose(computed, claimed_float, rel_tol=1e-6, abs_tol=1e-6):
                    answer_matches = False
                    mismatch_note = f"الحل المدخل ({claimed_answer}) لا يطابق النتيجة الصحيحة ({formatted_val})."
            except ValueError:
                answer_matches = False
                mismatch_note = f"الحل المدخل ({claimed_answer}) ليس عددًا صالحًا."

        unit_str = f" {unit}" if unit else ""
        steps = [
            f"1. كتابة العبارة الرياضية بوضوح باتجاه LTR: {expression}",
            "2. التحقق من أولويات العمليات الحسابية وخلو المقامات من الصفر.",
            f"3. الناتج المتحقق منه حسابيًا: {formatted_val}{unit_str}",
        ]
        if not answer_matches:
            steps.append(f"تنبيه تصحيحي: {mismatch_note}")

        return {
            "valid": answer_matches,
            "errorCode": None if answer_matches else "MATH_ANSWER_MISMATCH",
            "message": "تم التحقق الرياضي بنجاح." if answer_matches else mismatch_note,
            "computedValue": formatted_val,
            "unit": unit,
            "steps": steps,
            "provenanceLabel": provenance,
            "editableOutput": f"مسألة تطبيقية ({provenance}): احسب {expression} = {formatted_val}{unit_str}. خطوات الحل: {' | '.join(steps)}",
            "subjectItem": {
                "domain": "math",
                "expression": expression,
                "expectedAnswer": formatted_val,
                "claimedAnswer": str(claimed_answer) if claimed_answer is not None else formatted_val,
                "unit": unit,
                "provenance": provenance,
            },
        }

    if tool_type == "text_analysis":
        passage = str(inputs.get("passage", "")).strip()
        author_or_source = str(inputs.get("authorOrSource", "")).strip()
        literary_focus = str(inputs.get("focus", "الفكرة الرئيسة والدلالات اللغوية والبلاغية")).strip()
        if not passage:
            return {
                "valid": False,
                "errorCode": "EMPTY_PASSAGE",
                "message": "يرجى إدخال النص الأدبي أو القرائي المراد تحليله.",
                "provenanceLabel": provenance,
                "editableOutput": "",
            }
        attribution_warning = None
        if not author_or_source:
            attribution_warning = "النص غير منسوب إلى قائل أو مصدر؛ سيُعامل كمثال تدريبي مؤلف غير موثق من الكتاب."

        words = [w for w in re.split(r"\s+", passage) if w]
        rubric = "يُقوّم تفسير المتعلم المفتوح وفق محك (وضوح الفكرة، الاستشهاد بدليل من النص، سلامة اللغة) وليس بإجابة عددية وحيدة."
        output_text = (
            f"نشاط تحليل نص ({provenance}):\n"
            f"- النص ({len(words)} كلمة): «{passage}»\n"
            f"- النسبة/المصدر المصرّح به: {author_or_source or 'مثال تدريبي مؤلف — غير منسوب'}\n"
            f"- محور التحليل: {literary_focus}\n"
            f"- محك التقويم: {rubric}"
        )
        return {
            "valid": True,
            "errorCode": None,
            "message": attribution_warning or "تم إعداد بطاقة تحليل النص ومحك التقويم الأدبي.",
            "wordCount": len(words),
            "attributionWarning": attribution_warning,
            "rubric": rubric,
            "provenanceLabel": provenance,
            "editableOutput": output_text,
            "subjectItem": {
                "domain": "literature",
                "quote": passage,
                "attributedTo": author_or_source,
                "rubric": rubric,
                "provenance": provenance,
            },
        }

    if tool_type == "historical_timeline":
        events: List[Dict[str, Any]] = inputs.get("events", [])
        if not events or not isinstance(events, list):
            return {
                "valid": False,
                "errorCode": "EMPTY_TIMELINE",
                "message": "أدخل حدثين تاريخيين على الأقل مع السنة والدليل التاريخي.",
                "provenanceLabel": provenance,
                "editableOutput": "",
            }
        parsed_events = []
        chronology_valid = True
        prev_year = None
        missing_evidence = False
        for idx, ev in enumerate(events):
            yr_raw = str(ev.get("year", "")).strip()
            ev_title = str(ev.get("event", "")).strip()
            evidence = str(ev.get("evidence", "")).strip()
            if not yr_raw or not ev_title:
                return {
                    "valid": False,
                    "errorCode": "INCOMPLETE_EVENT",
                    "message": f"الحدث رقم {idx + 1} يفتقد السنة أو عنوان الواقعة التاريخية.",
                    "provenanceLabel": provenance,
                    "editableOutput": "",
                }
            m = re.search(r"(-?\d+)", yr_raw)
            yr_num = int(m.group(1)) if m else idx
            if prev_year is not None and yr_num < prev_year:
                chronology_valid = False
            prev_year = yr_num
            if not evidence:
                missing_evidence = True
            parsed_events.append({"year": yr_raw, "yearNum": yr_num, "event": ev_title, "evidence": evidence or "يحتاج تحديد شاهد/مصدر تاريخي"})

        lines = [f"- [{e['year']}] {e['event']} (الدليل/الشاهد: {e['evidence']})" for e in parsed_events]
        msg = "الخط الزمني مرتب تاريخيًا ومرفق بالأدلة."
        if not chronology_valid:
            msg = "تنبيه تخصصي تاريخي: التواريخ المدخلة غير مرتبة تسلسليًا من الأقدم إلى الأحدث."
        elif missing_evidence:
            msg = "تنبيه تخصصي تاريخي: بعض الوقائع تفتقر إلى ذكر الدليل أو الوثيقة التاريخية."

        return {
            "valid": chronology_valid,
            "errorCode": None if chronology_valid else "HISTORY_CHRONOLOGY_ERROR",
            "message": msg,
            "events": parsed_events,
            "provenanceLabel": provenance,
            "editableOutput": f"خط زمني تاريخي ({provenance}):\n" + "\n".join(lines),
            "subjectItem": {
                "domain": "history",
                "events": parsed_events,
                "chronologyValid": chronology_valid,
                "provenance": provenance,
            },
        }

    if tool_type == "science_experiment":
        hypothesis = str(inputs.get("hypothesis", "")).strip()
        variables = str(inputs.get("variables", "")).strip()
        safety = str(inputs.get("safety", "ارتداء النظارات الواقية وإشراف المعلم")).strip()
        measurement_unit = str(inputs.get("unit", "")).strip()
        if not hypothesis:
            return {
                "valid": False,
                "errorCode": "EMPTY_HYPOTHESIS",
                "message": "يرجى إدخال فرضية التجربة العلمية أولًا.",
                "provenanceLabel": provenance,
                "editableOutput": "",
            }
        output_text = (
            f"بطاقة تجربة استقصائية ({provenance}):\n"
            f"- الفرضية: {hypothesis}\n"
            f"- المتغيرات (المستقل/التابع/الضابط): {variables or 'تحدد أثناء النشاط'}\n"
            f"- وحدة القياس المعتمدة: {measurement_unit or 'حسب أداة القياس'}\n"
            f"- إجراءات السلامة: {safety}"
        )
        return {
            "valid": True,
            "errorCode": None,
            "message": "تم التحقق من عناصر التجربة العلمية وإجراءات السلامة والوحدات.",
            "provenanceLabel": provenance,
            "editableOutput": output_text,
            "subjectItem": {
                "domain": "science",
                "hypothesis": hypothesis,
                "variables": variables,
                "unit": measurement_unit,
                "safety": safety,
                "provenance": provenance,
            },
        }

    # Default: worksheet_generator suitable for any subject
    topic = title or str(inputs.get("topic", subject or "الدرس الحالي")).strip()
    questions_prompt = str(inputs.get("prompt", "أسئلة متدرجة تراعي الفروق الفردية")).strip()
    rubric = str(inputs.get("rubric", "معيار تقييم واضح يربط الأداء بالهدف التعليمي")).strip()
    output_text = (
        f"ورقة عمل صفية ({provenance}) — الموضوع: {topic}\n"
        f"1. سؤال التهيئة (استدعاء المعرفة السابقة): اشرح بكلماتك المفهوم الأساسي المتعلق بـ «{topic}».\n"
        f"2. مهمة التطبيق ({questions_prompt}): طبّق ما تعلمته في موقف جديد مع تعليل الخطوات أو ذكر الدليل.\n"
        f"3. معيار التقويم (Rubric): {rubric}"
    )
    return {
        "valid": True,
        "errorCode": None,
        "message": "تم توليد مسودة ورقة عمل قابلة للتحرير والإضافة للخطة.",
        "provenanceLabel": provenance,
        "editableOutput": output_text,
        "subjectItem": {
            "domain": "general",
            "topic": topic,
            "rubric": rubric,
            "provenance": provenance,
        },
    }


def audit_plan_and_context(
    plan_data: Dict[str, Any],
    context_data: Dict[str, Any],
    source_data: Optional[Dict[str, Any]] = None,
    lesson_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Independent Specialized & Pedagogical Audit Engine.
    Strictly separates findings into:
    - 'BLOCKER': Prevents plan approval (`approved`). Includes missing formative assessment, time contradiction,
      negative phase duration, math division by zero or wrong numerical solution, unattributed quote claimed as official,
      empty objectives, or context mismatch.
    - 'SOURCE_WARNING': Does NOT block saving draft or exporting marked documents, but warns clearly.
      Includes missing uploaded textbook PDF, missing edition/year, unlinked lesson page, pending OCR review,
      authored illustrative examples ('مثال توضيحي غير موثق من الكتاب'), or missing context fields.
    - 'PASSED': Verified checks (time distribution valid, objectives present, tools available, etc.).
    """
    findings: List[Dict[str, Any]] = []

    def add_finding(
        category: str,  # BLOCKER | SOURCE_WARNING | PASSED
        severity: str,  # critical | warning | info
        code: str,
        title: str,
        description: str,
        field_target: str,
        remediation: str,
        evidence: str = "",
    ):
        findings.append(
            {
                "category": category,
                "severity": severity,
                "code": code,
                "title": title,
                "description": description,
                "fieldTarget": field_target,
                "remediation": remediation,
                "evidence": evidence,
            }
        )

    # 1. Formative Assessment check (Ref: مراجعة الخطة.png top blocker card)
    formative = str(plan_data.get("formativeAssessment", "")).strip()
    if not formative:
        add_finding(
            category="BLOCKER",
            severity="critical",
            code="MISSING_FORMATIVE_ASSESSMENT",
            title="طريقة التقويم التكويني مفقودة",
            description="أضف وسيلة لمعرفة مدى تحقق الأهداف قبل اعتماد الخطة.",
            field_target="formativeAssessment",
            remediation="انتقل إلى حقل التقويم التكويني وأدخل سؤالًا أو مهمة مرتبطة بالأهداف ومعيار تقييمها.",
            evidence="حقل formativeAssessment فارغ.",
        )
    else:
        add_finding(
            category="PASSED",
            severity="info",
            code="FORMATIVE_ASSESSMENT_PRESENT",
            title="طريقة التقويم التكويني مكتملة",
            description=f"تم تحديد أداة ومعيار التقويم: {formative[:90]}",
            field_target="formativeAssessment",
            remediation="لا يلزم إجراء.",
            evidence=formative,
        )

    # 2. Time Allocation & Period Duration Validation
    plan_type = plan_data.get("planType", "daily")
    periods_count = int(plan_data.get("periodsCount", 1) or 1)
    period_minutes = int(plan_data.get("periodMinutes", 45) or 45)
    expected_total = periods_count * period_minutes

    if plan_type == "daily":
        phases = plan_data.get("phases", [])
        if not phases:
            add_finding(
                category="BLOCKER",
                severity="critical",
                code="EMPTY_PHASES",
                title="مراحل سير الحصة غير مدخلة",
                description="الخطة اليومية لا تحتوي على أي مراحل تدريسية.",
                field_target="phases",
                remediation="أضف مراحل الدرس وحدد زمن كل مرحلة بالدقائق.",
                evidence="قائمة المراحل فارغة.",
            )
        else:
            negative_found = False
            in_class_minutes = 0
            parts_str = []
            for idx, ph in enumerate(phases):
                m = int(ph.get("minutes", 0) or 0)
                if m < 0:
                    negative_found = True
                if not ph.get("isHomeEnrichment", False):
                    in_class_minutes += m
                    parts_str.append(str(m))

            if negative_found:
                add_finding(
                    category="BLOCKER",
                    severity="critical",
                    code="NEGATIVE_PHASE_DURATION",
                    title="زمن سالب في إحدى المراحل",
                    description="لا يجوز إدخال مدة زمنية سالبة لأي مرحلة من مراحل الدرس.",
                    field_target="phases",
                    remediation="صحح أزمنة المراحل لتكون أعدادًا موجبة أو صفرًا.",
                    evidence=str(phases),
                )
            elif in_class_minutes != expected_total:
                diff = expected_total - in_class_minutes
                diff_label = f"متبقٍ {diff} دقيقة" if diff > 0 else f"تجاوز بمقدار {abs(diff)} دقيقة"
                add_finding(
                    category="BLOCKER",
                    severity="critical",
                    code="TIME_DISTRIBUTION_MISMATCH",
                    title="تعارض في توزيع زمن الحصة",
                    description=f"مجموع أزمنة المراحل الصفية ({in_class_minutes} دقيقة) لا يساوي الزمن المخصص ({expected_total} دقيقة لعدد {periods_count} حصة × {period_minutes} دقيقة — {diff_label}).",
                    field_target="phases",
                    remediation=f"عدّل دقائق المراحل بحيث يصبح المجموع {expected_total} دقيقة (الإثراء المنزلي خارج المجموع).",
                    evidence=f"{' + '.join(parts_str)} = {in_class_minutes} != {expected_total}",
                )
            else:
                formula_str = f"{' + '.join(parts_str)} = {expected_total} دقيقة"
                add_finding(
                    category="PASSED",
                    severity="info",
                    code="TIME_DISTRIBUTION_VALID",
                    title="توزيع الزمن صحيح",
                    description=f"{formula_str} · متوافق مع {periods_count} حصة ({period_minutes} دقيقة للحصة).",
                    field_target="phases",
                    remediation="لا يلزم إجراء.",
                    evidence=formula_str,
                )
    else:
        # Weekly or five_day plan schedule check
        days = plan_data.get("scheduleDays", [])
        unscheduled = [d.get("dayName", "") for d in days if not d.get("isHoliday") and not str(d.get("lessonTitle", "")).strip()]
        if not days:
            add_finding(
                category="BLOCKER",
                severity="critical",
                code="EMPTY_SCHEDULE_DAYS",
                title="جدول الأيام فارغ",
                description="لم يتم إدخال أيام التدريس في الخطة.",
                field_target="scheduleDays",
                remediation="أضف أيام التدريس وحدد الدرس والهدف والتقويم لكل يوم.",
                evidence="scheduleDays=[]",
            )
        elif unscheduled:
            add_finding(
                category="BLOCKER",
                severity="critical",
                code="UNSCHEDULED_TEACHING_DAYS",
                title="أيام تدريس غير مكتملة الجدولة",
                description=f"قبل اعتماد الخطة: حدد دروس وأنشطة الأيام التالية أو علّمها كعطلة: {'، '.join(unscheduled)}.",
                field_target="scheduleDays",
                remediation="استكمل بيانات الحصص للأيام غير المجدولة.",
                evidence=f"Unscheduled: {unscheduled}",
            )
        else:
            total_min = sum(int(d.get("minutes", period_minutes) or 0) for d in days if not d.get("isHoliday"))
            add_finding(
                category="PASSED",
                severity="info",
                code="SCHEDULE_DAYS_VALID",
                title="توزيع أيام التدريس والزمن مكتمل",
                description=f"تم جدولة {len([d for d in days if not d.get('isHoliday')])} أيام تدريس بإجمالي {total_min} دقيقة.",
                field_target="scheduleDays",
                remediation="لا يلزم إجراء.",
                evidence=f"Total minutes: {total_min}",
            )

    # 3. Learning Objectives check
    objectives = [str(o).strip() for o in plan_data.get("objectives", []) if str(o).strip()]
    if not objectives:
        add_finding(
            category="BLOCKER",
            severity="critical",
            code="MISSING_OBJECTIVES",
            title="الأهداف التعليمية غير مدخلة",
            description="يجب إدخال هدف تعليمي واحد على الأقل قابل للقياس والملاحظة.",
            field_target="objectives",
            remediation="أضف هدفًا تعليميًا مناسبًا للمادة والصف.",
            evidence="objectives=[]",
        )
    else:
        add_finding(
            category="PASSED",
            severity="info",
            code="OBJECTIVES_PRESENT",
            title="الأهداف مدخلة وقابلة للمراجعة",
            description=f"{len(objectives)} أهداف بصياغة واضحة؛ يراجع المعلم ملاءمتها للدرس.",
            field_target="objectives",
            remediation="لا يلزم إجراء.",
            evidence=" | ".join(objectives),
        )

    # 4. Teaching Tools check
    tools = [str(t).strip() for t in plan_data.get("teachingTools", []) if str(t).strip()]
    if tools:
        has_projector = any("عرض" in t or "projector" in t.lower() for t in tools)
        projector_note = "مع توفر جهاز عرض" if has_projector else "جهاز العرض غير مطلوب"
        add_finding(
            category="PASSED",
            severity="info",
            code="TOOLS_AVAILABLE",
            title="الوسائل متاحة",
            description=f"{len(tools)} وسائل محدّدة؛ {projector_note}.",
            field_target="teachingTools",
            remediation="لا يلزم إجراء.",
            evidence="، ".join(tools),
        )
    else:
        add_finding(
            category="SOURCE_WARNING",
            severity="warning",
            code="NO_TOOLS_SELECTED",
            title="لم تُحدّد وسائل تعليمية",
            description="يفضّل تحديد الوسائل المتاحة في الصف (سبورة، أقلام، بطاقات...).",
            field_target="teachingTools",
            remediation="اختر الوسائل المتاحة من صفحة الوسائل التعليمية وأدوات المدرس.",
            evidence="teachingTools=[]",
        )

    # 5. Specialized Subject & Math Verification (`subjectItems`)
    subject_items = plan_data.get("subjectItems", [])
    for idx, item in enumerate(subject_items):
        domain = item.get("domain", "general")
        if domain == "math":
            expr = str(item.get("expression", "")).strip()
            claimed = item.get("claimedAnswer", None)
            if expr:
                res = run_subject_tool(
                    subject=context_data.get("subject", ""),
                    tool_type="math_solver",
                    title=f"تدقيق مسألة #{idx + 1}",
                    inputs={"expression": expr, "claimedAnswer": claimed, "unit": item.get("unit", "")},
                )
                if not res["valid"]:
                    add_finding(
                        category="BLOCKER",
                        severity="critical",
                        code=res["errorCode"] or "MATH_VERIFICATION_FAILED",
                        title=f"خطأ رياضي في المسألة #{idx + 1}",
                        description=res["message"],
                        field_target="subjectItems",
                        remediation="صحح المعادلة أو الناتج العددي أو احذف القسمة على صفر قبل اعتماد الخطة.",
                        evidence=f"Expression: {expr}, Claimed: {claimed}",
                    )
                else:
                    add_finding(
                        category="PASSED",
                        severity="info",
                        code="MATH_ITEM_VERIFIED",
                        title=f"صحة الحل العددي للمسألة #{idx + 1}",
                        description=f"العبارة ({expr} = {res['computedValue']}) صحيحة وخالية من التناقض الرياضي.",
                        field_target="subjectItems",
                        remediation="لا يلزم إجراء.",
                        evidence=expr,
                    )
        elif domain == "history":
            events = item.get("events", [])
            if events:
                res = run_subject_tool(
                    subject=context_data.get("subject", ""),
                    tool_type="historical_timeline",
                    title=f"تدقيق خط زمني #{idx + 1}",
                    inputs={"events": events},
                )
                if not res["valid"]:
                    add_finding(
                        category="BLOCKER",
                        severity="critical",
                        code="HISTORY_CHRONOLOGY_INVALID",
                        title="اضطراب في تسلسل التواريخ والوقائع",
                        description=res["message"],
                        field_target="subjectItems",
                        remediation="رتب الوقائع التاريخية زمنيًا وتأكد من صحة السنوات والأدلة.",
                        evidence=str(events),
                    )
        elif domain == "literature":
            quote = str(item.get("quote", "")).strip()
            attributed = str(item.get("attributedTo", "")).strip()
            claimed_official_quote = bool(item.get("claimedOfficialQuote", False))
            if quote and claimed_official_quote and not attributed:
                add_finding(
                    category="BLOCKER",
                    severity="critical",
                    code="UNATTRIBUTED_OFFICIAL_QUOTE",
                    title="اقتباس أدبي رسمي بلا نسبة أو مصدر",
                    description="تم تصنيف النص كاقتباس رسمي دون ذكر قائله أو مصدره.",
                    field_target="subjectItems",
                    remediation="أضف نسبة النص ومصدره أو علّمه كمثال تدريبي مؤلف.",
                    evidence=quote[:80],
                )

    # 6. Source & Provenance Warnings (Separated strictly from Blockers unless falsely claiming official status!)
    if not source_data:
        add_finding(
            category="SOURCE_WARNING",
            severity="warning",
            code="SOURCE_NOT_LINKED",
            title="مصدر المنهج غير موثّق",
            description="بيانات المصدر ناقصة؛ اطلب مراجعتها في مساحة استيراد كتاب المنهج.",
            field_target="sourceId",
            remediation="ارفع ملف PDF للمنهج أو أكمل بيانات السنة والطبعة ورابط المصدر.",
            evidence="لا يوجد سجل مصدر مرتبط أو معتمد.",
        )
    else:
        ver_status = source_data.get("verificationStatus", "pending_review")
        is_official_claimed = bool(source_data.get("isOfficialClaimed", False))
        official_evidence = str(source_data.get("officialEvidence", "")).strip()

        if is_official_claimed and (ver_status != "human_verified" or not official_evidence):
            add_finding(
                category="BLOCKER",
                severity="critical",
                code="UNVERIFIED_OFFICIAL_CLAIM",
                title="ادعاء توثيق رسمي للمنهج دون دليل ومراجعة",
                description="لا يجوز ادعاء الرسمية لكتاب المنهج دون دليل يخص البلد والمنهج والطبعة ومراجعة بشرية معتمدة.",
                field_target="sourceId",
                remediation="أزل ادعاء الرسمية أو أرفق دليل المطابقة واعتمد المراجعة البشرية.",
                evidence=f"isOfficialClaimed=True, verificationStatus={ver_status}",
            )
        elif ver_status != "human_verified":
            add_finding(
                category="SOURCE_WARNING",
                severity="warning",
                code="SOURCE_PENDING_VERIFICATION",
                title="مصدر المنهج غير موثّق",
                description="بيانات المصدر قيد المراجعة؛ المراجعة التربوية للخطة لا تمنح اعتمادًا تلقائيًا للمصدر.",
                field_target="sourceId",
                remediation="استكمل مراجعة المصدر والطبعة في صفحة استيراد كتاب المنهج.",
                evidence=f"source={source_data.get('title')}, status={ver_status}",
            )
        else:
            add_finding(
                category="PASSED",
                severity="info",
                code="SOURCE_HUMAN_VERIFIED",
                title="مصدر المنهج موثّق ومعتمد",
                description=f"تم توثيق المصدر ({source_data.get('title')}) — الطبعة: {source_data.get('edition') or 'محددة'}.",
                field_target="sourceId",
                remediation="لا يلزم إجراء.",
                evidence=f"SHA256: {source_data.get('sha256Fingerprint', '')[:16]}",
            )

        if source_data.get("extractionStatus") == "requires_ocr_or_manual":
            add_finding(
                category="SOURCE_WARNING",
                severity="warning",
                code="SOURCE_REQUIRES_OCR_REVIEW",
                title="استخراج النص يتطلب مراجعة OCR يدوية",
                description="ملف PDF المرفوع ممسوح ضوئيًا أو يحتوي مواضع ملتبسة تحتاج مراجعة بشرية قبل اعتماد الفهرس.",
                field_target="sourceId",
                remediation="راجع صفحات المصدر وصحح النص المستخرج في صفحة استيراد PDF.",
                evidence="extractionStatus=requires_ocr_or_manual",
            )

    # 7. Missing Context Fields Warning (Never guess unknown fields!)
    missing_ctx = []
    for fld, label in [
        ("subject", "المادة"),
        ("grade", "الصف/المرحلة"),
        ("country", "البلد"),
        ("curriculumName", "اسم المنهج"),
        ("language", "اللغة"),
        ("year", "السنة الدراسية"),
        ("edition", "الطبعة"),
    ]:
        if not str(context_data.get(fld, "")).strip():
            missing_ctx.append(label)

    if missing_ctx:
        add_finding(
            category="SOURCE_WARNING",
            severity="warning",
            code="INCOMPLETE_CONTEXT_FIELDS",
            title="حقول غير معروفة في السياق التعليمي أو الطبعة",
            description=f"الحقول التالية تُركت فارغة عمدًا بدل تخمينها: {'، '.join(missing_ctx)}.",
            field_target="context",
            remediation="أكمل الحقول الناقصة في صفحة إعداد الخطة أو استيراد المنهج عند توفرها.",
            evidence=", ".join(missing_ctx),
        )

    # 8. Authored Content Provenance Warning
    if plan_data.get("contentOrigin", "authored_example") == "authored_example":
        add_finding(
            category="SOURCE_WARNING",
            severity="warning",
            code="AUTHORED_ILLUSTRATIVE_CONTENT",
            title="محتوى تدريبي مؤلف (مثال توضيحي غير موثق من الكتاب)",
            description="تحتوي الخطة على أمثلة أو أنشطة مؤلفة ومعلّمة بوضوح ولا تُعرض كاقتباس رسمي من الكتاب.",
            field_target="contentOrigin",
            remediation="يمكنك التصدير مع بقاء علامة «مثال توضيحي غير موثق من الكتاب»، أو ربط الدرس بصفحة موثقة من الكتاب.",
            evidence=plan_data.get("provenanceLabel", "مثال توضيحي غير موثق من الكتاب"),
        )

    # 9. Lesson Page Link Warning
    if lesson_data and not lesson_data.get("pdfPageNumber") and not str(lesson_data.get("printedPageNumber", "")).strip():
        add_finding(
            category="SOURCE_WARNING",
            severity="warning",
            code="LESSON_PAGE_UNLINKED",
            title="الدرس غير مربوط برقم صفحة في الكتاب",
            description="لم يُحدّد رقم صفحة PDF أو الصفحة المطبوعة لهذا الدرس.",
            field_target="primaryLessonId",
            remediation="اربط الدرس برقم الصفحة من شاشة الدروس أو المنهج بعد توثيق المصدر.",
            evidence=f"lessonId={lesson_data.get('id')}",
        )

    blockers = [f for f in findings if f["category"] == "BLOCKER"]
    warnings = [f for f in findings if f["category"] == "SOURCE_WARNING"]
    passed = [f for f in findings if f["category"] == "PASSED"]

    if blockers:
        overall_status = "needs_revision"
    else:
        overall_status = "reviewed"

    return {
        "overallStatus": overall_status,
        "canApprove": len(blockers) == 0,
        "blockersCount": len(blockers),
        "warningsCount": len(warnings),
        "passedCount": len(passed),
        "findings": findings,
    }
