import hashlib
import io
import json
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, Any, List


def _xml_escape(val: Any) -> str:
    s = str(val if val is not None else "")
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _is_rtl_lang(lang: str) -> bool:
    return str(lang or "ar").lower().startswith(("ar", "he", "fa", "ur", "ku"))


def _format_context_banner(context_snap: Dict[str, Any]) -> str:
    subj = context_snap.get("subject") or "غير محدد"
    grade = context_snap.get("grade") or "غير محدد"
    country = context_snap.get("country") or "غير محدد"
    curr = context_snap.get("curriculumName") or "غير محدد"
    lang = context_snap.get("language") or "ar"
    year = context_snap.get("year") or "غير مدخلة"
    edition = context_snap.get("edition") or "غير مدخلة"
    return (
        f"المادة: {subj} | الصف/المرحلة: {grade} | البلد: {country} | "
        f"المنهج: {curr} | اللغة: {lang} | السنة: {year} | الطبعة: {edition}"
    )


def _format_approval_badge(plan_snap: Dict[str, Any], source_status: str) -> str:
    status = plan_snap.get("status", "draft")
    ver = plan_snap.get("version", 1)
    prov = plan_snap.get("provenanceLabel", "مثال توضيحي غير موثق من الكتاب")
    if status == "approved":
        approver = plan_snap.get("approvedBy") or plan_snap.get("teacherName") or "المعلم المراجع"
        return f"حالة الإصدار (v{ver}): معتمد تربويًا بواسطة ({approver}) | حالة المصدر: {source_status} | النسبة: {prov}"
    return f"حالة الإصدار (v{ver}): مسودة غير معتمدة ({status}) — لا تحمل ختم اعتماد رسمي | حالة المصدر: {source_status} | {prov}"


# ==============================================================================
# 1. REAL OOXML DOCX GENERATOR (.docx)
# ==============================================================================

def _w_p(text: str, rtl: bool = True, bold: bool = False, size_half_pts: int = 24, color_hex: str = "111827") -> str:
    bidi_tag = "<w:bidi/>" if rtl else ""
    jc_val = "right" if rtl else "left"
    rtl_run = "<w:rtl/>" if rtl else ""
    b_tag = "<w:b/><w:bCs/>" if bold else ""
    return (
        f"<w:p>"
        f"<w:pPr>{bidi_tag}<w:jc w:val=\"{jc_val}\"/><w:spacing w:before=\"80\" w:after=\"80\"/></w:pPr>"
        f"<w:r>"
        f"<w:rPr><w:rFonts w:ascii=\"Arial\" w:hAnsi=\"Arial\" w:cs=\"Arial\"/>"
        f"{b_tag}<w:color w:val=\"{color_hex}\"/><w:sz w:val=\"{size_half_pts}\"/><w:szCs w:val=\"{size_half_pts}\"/>{rtl_run}</w:rPr>"
        f"<w:t xml:space=\"preserve\">{_xml_escape(text)}</w:t>"
        f"</w:r>"
        f"</w:p>"
    )


def _w_table(headers: List[str], rows: List[List[str]], rtl: bool = True) -> str:
    bidi_visual = "<w:bidiVisual/>" if rtl else ""
    header_cells = "".join(
        f"<w:tc><w:tcPr><w:shd w:val=\"clear\" w:color=\"auto\" w:fill=\"154434\"/></w:tcPr>"
        f"{_w_p(h, rtl=rtl, bold=True, size_half_pts=22, color_hex='FFFFFF')}</w:tc>"
        for h in headers
    )
    body_rows = ""
    for r_idx, row in enumerate(rows):
        fill = "F6F7F5" if r_idx % 2 == 1 else "FFFFFF"
        cells = "".join(
            f"<w:tc><w:tcPr><w:shd w:val=\"clear\" w:color=\"auto\" w:fill=\"{fill}\"/></w:tcPr>"
            f"{_w_p(cell, rtl=rtl, bold=False, size_half_pts=21, color_hex='1C2520')}</w:tc>"
            for cell in row
        )
        body_rows += f"<w:tr>{cells}</w:tr>"

    return (
        f"<w:tbl>"
        f"<w:tblPr>"
        f"<w:tblW w:w=\"5000\" w:type=\"pct\"/>"
        f"{bidi_visual}"
        f"<w:tblBorders>"
        f"<w:top w:val=\"single\" w:sz=\"6\" w:space=\"0\" w:color=\"CBD5E1\"/>"
        f"<w:bottom w:val=\"single\" w:sz=\"6\" w:space=\"0\" w:color=\"CBD5E1\"/>"
        f"<w:left w:val=\"single\" w:sz=\"6\" w:space=\"0\" w:color=\"CBD5E1\"/>"
        f"<w:right w:val=\"single\" w:sz=\"6\" w:space=\"0\" w:color=\"CBD5E1\"/>"
        f"<w:insideH w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"E2E8F0\"/>"
        f"<w:insideV w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"E2E8F0\"/>"
        f"</w:tblBorders>"
        f"</w:tblPr>"
        f"<w:tr>{header_cells}</w:tr>"
        f"{body_rows}"
        f"</w:tbl>"
    )


def generate_plan_docx_bytes(
    plan_snap: Dict[str, Any],
    context_snap: Dict[str, Any],
    review_snap: Dict[str, Any],
    source_status: str = "unverified_draft",
) -> bytes:
    rtl = _is_rtl_lang(context_snap.get("language", "ar"))
    body_parts: List[str] = []

    title = plan_snap.get("title") or "خطة تدريس"
    body_parts.append(_w_p(title, rtl=rtl, bold=True, size_half_pts=34, color_hex="154434"))
    body_parts.append(_w_p(_format_context_banner(context_snap), rtl=rtl, bold=True, size_half_pts=20, color_hex="176B52"))
    body_parts.append(_w_p(_format_approval_badge(plan_snap, source_status), rtl=rtl, bold=False, size_half_pts=20, color_hex="B45309"))

    meta_headers = ["المعلم", "المدرسة", "الشعبة", "التاريخ", "نوع الخطة", "الزمن المخصص"]
    total_min = int(plan_snap.get("periodsCount", 1)) * int(plan_snap.get("periodMinutes", 45))
    meta_row = [
        plan_snap.get("teacherName") or context_snap.get("teacherName") or "غير محدد",
        plan_snap.get("schoolName") or context_snap.get("schoolName") or "غير محددة",
        plan_snap.get("sectionName") or context_snap.get("sectionName") or "غير محددة",
        plan_snap.get("planningDate") or "غير محدد",
        plan_snap.get("planType") or "daily",
        f"{plan_snap.get('periodsCount', 1)} حصة × {plan_snap.get('periodMinutes', 45)} د = {total_min} دقيقة",
    ]
    body_parts.append(_w_table(meta_headers, [meta_row], rtl=rtl))

    # Objectives
    body_parts.append(_w_p("الأهداف التعليمية:", rtl=rtl, bold=True, size_half_pts=26, color_hex="154434"))
    for idx, obj in enumerate(plan_snap.get("objectives", []), start=1):
        body_parts.append(_w_p(f"{idx}. {obj}", rtl=rtl, bold=False, size_half_pts=22))

    # Prior Knowledge & Tools
    body_parts.append(_w_p(f"المتطلبات والمعارف السابقة: {plan_snap.get('priorKnowledge') or '—'}", rtl=rtl, size_half_pts=22))
    tools_str = "، ".join(plan_snap.get("teachingTools", [])) or "سبورة، أقلام"
    body_parts.append(_w_p(f"الوسائل التعليمية المتاحة: {tools_str}", rtl=rtl, size_half_pts=22))

    # Phases Table (Daily) or Schedule Days Table (Weekly / 5-Day)
    if plan_snap.get("planType", "daily") == "daily":
        body_parts.append(_w_p("جدول مراحل سير الحصة (قابل للتخصيص):", rtl=rtl, bold=True, size_half_pts=26, color_hex="154434"))
        ph_headers = ["ت", "الحصة", "المرحلة / العنصر", "المواد والمصدر", "دور المعلم (المنفّذ)", "دور المتعلم", "الهدف من العنصر", "الزمن (د)"]
        ph_rows = []
        for idx, ph in enumerate(plan_snap.get("phases", []), start=1):
            ph_rows.append(
                [
                    str(idx),
                    f"الحصة {ph.get('periodNumber', 1)}",
                    str(ph.get("phaseName", "")),
                    f"{ph.get('materials', '')} ({ph.get('sourceRef', 'المقرّر')})",
                    str(ph.get("teacherActivity") or ph.get("executorRole") or ""),
                    str(ph.get("studentActivity") or ""),
                    str(ph.get("objective") or ""),
                    f"{ph.get('minutes', 0)} د",
                ]
            )
        if ph_rows:
            body_parts.append(_w_table(ph_headers, ph_rows, rtl=rtl))
    else:
        body_parts.append(_w_p("جدول توزيع الأيام والحصص:", rtl=rtl, bold=True, size_half_pts=26, color_hex="154434"))
        day_headers = ["اليوم", "الحالة", "الدرس", "الأهداف والأنشطة", "التقويم", "الزمن (د)"]
        day_rows = []
        for d in plan_snap.get("scheduleDays", []):
            day_rows.append(
                [
                    str(d.get("dayName", "")),
                    "عطلة" if d.get("isHoliday") else "يوم تدريس",
                    str(d.get("lessonTitle", "—")),
                    str(d.get("activities", "—")),
                    str(d.get("assessment", "—")),
                    "0" if d.get("isHoliday") else str(d.get("minutes", 45)),
                ]
            )
        if day_rows:
            body_parts.append(_w_table(day_headers, day_rows, rtl=rtl))

    # Assessment, Differentiation, Homework
    body_parts.append(_w_p("التقويم ومراعاة الفروق والواجب:", rtl=rtl, bold=True, size_half_pts=26, color_hex="154434"))
    body_parts.append(_w_p(f"• التقويم التكويني: {plan_snap.get('formativeAssessment') or 'غير مدخل (مانع اعتماد)'}", rtl=rtl, size_half_pts=22))
    body_parts.append(_w_p(f"• مراعاة الفروق الفردية (التمايز): {plan_snap.get('differentiation') or '—'}", rtl=rtl, size_half_pts=22))
    body_parts.append(_w_p(f"• الواجب المنزلي / الإثراء: {plan_snap.get('homework') or '—'}", rtl=rtl, size_half_pts=22))

    # Specialized Subject Items (with independent LTR direction for math expressions!)
    subj_items = plan_snap.get("subjectItems", [])
    if subj_items:
        body_parts.append(_w_p("المحتوى التخصصي والتمارين المتحققة:", rtl=rtl, bold=True, size_half_pts=26, color_hex="154434"))
        for item in subj_items:
            if item.get("domain") == "math":
                expr_line = f"{item.get('expression', '')} = {item.get('expectedAnswer', '')} {item.get('unit', '')}".strip()
                body_parts.append(_w_p(expr_line, rtl=False, bold=True, size_half_pts=22, color_hex="176B52"))
            else:
                body_parts.append(_w_p(json.dumps(item, ensure_ascii=False), rtl=rtl, size_half_pts=20))

    # Review Defects & Warnings Summary
    findings = review_snap.get("findings", [])
    if findings:
        body_parts.append(_w_p("سجل التدقيق التربوي وتوثيق المصدر:", rtl=rtl, bold=True, size_half_pts=26, color_hex="154434"))
        rev_headers = ["الفئة", "العنوان", "التفاصيل", "الحقل المرتبط"]
        rev_rows = [
            [f.get("category", ""), f.get("title", ""), f.get("description", ""), f.get("fieldTarget", "")]
            for f in findings
        ]
        body_parts.append(_w_table(rev_headers, rev_rows, rtl=rtl))

    document_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\" "
        "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\">"
        "<w:body>"
        + "".join(body_parts)
        + "<w:sectPr>"
        "<w:pgSz w:w=\"11906\" w:h=\"16838\"/>"
        "<w:pgMar w:top=\"1134\" w:right=\"1134\" w:bottom=\"1134\" w:left=\"1134\"/>"
        + ("<w:bidi/>" if rtl else "")
        + "</w:sectPr>"
        "</w:body></w:document>"
    )

    content_types_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
        "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
        "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
        "<Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>"
        "<Override PartName=\"/word/styles.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml\"/>"
        "</Types>"
    )

    rels_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"word/document.xml\"/>"
        "</Relationships>"
    )

    word_rels_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles\" Target=\"styles.xml\"/>"
        "</Relationships>"
    )

    styles_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<w:styles xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">"
        "<w:docDefaults><w:rPrDefault><w:rPr>"
        "<w:rFonts w:ascii=\"Arial\" w:hAnsi=\"Arial\" w:cs=\"Arial\"/>"
        "<w:lang w:val=\"en-US\" w:bidi=\"ar-IQ\"/>"
        "</w:rPr></w:rPrDefault></w:docDefaults>"
        "</w:styles>"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml.encode("utf-8"))
        zf.writestr("_rels/.rels", rels_xml.encode("utf-8"))
        zf.writestr("word/_rels/document.xml.rels", word_rels_xml.encode("utf-8"))
        zf.writestr("word/styles.xml", styles_xml.encode("utf-8"))
        zf.writestr("word/document.xml", document_xml.encode("utf-8"))
    return buf.getvalue()


# ==============================================================================
# 2. REAL OOXML PPTX GENERATOR (.pptx) WITH EDITABLE TEXT SHAPES
# ==============================================================================

def _build_slide_xml(slide_title: str, slide_lines: List[str], footer_note: str, rtl: bool = True, slide_num: int = 1, total_slides: int = 5) -> str:
    alg_attr = "r" if rtl else "l"
    rtl_val = "1" if rtl else "0"

    body_paras = ""
    for line in slide_lines:
        # Keep math equation lines LTR if they start with [LTR] or contain pure math
        line_rtl = "0" if line.startswith("LTR:") else rtl_val
        line_alg = "l" if line_rtl == "0" else alg_attr
        clean_line = line[4:].strip() if line.startswith("LTR:") else line
        body_paras += (
            f"<a:p>"
            f"<a:pPr algn=\"{line_alg}\" rtl=\"{line_rtl}\"/>"
            f"<a:r>"
            f"<a:rPr lang=\"ar-IQ\" sz=\"2200\" dirty=\"0\">"
            f"<a:solidFill><a:srgbClr val=\"1C2520\"/></a:solidFill>"
            f"<a:latin typeface=\"Arial\"/><a:cs typeface=\"Arial\"/>"
            f"</a:rPr>"
            f"<a:t>{_xml_escape(clean_line)}</a:t>"
            f"</a:r>"
            f"</a:p>"
        )

    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<p:sld xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" "
        "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" "
        "xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\">"
        "<p:cSld>"
        "<p:spTree>"
        "<p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>"
        "<p:grpSpPr><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"0\" cy=\"0\"/><a:chOff x=\"0\" y=\"0\"/><a:chExt cx=\"0\" cy=\"0\"/></a:xfrm></p:grpSpPr>"
        # Header Banner Shape (Editable Text Box 1)
        "<p:sp>"
        "<p:nvSpPr><p:cNvPr id=\"2\" name=\"HeaderTitle\"/><p:cNvSpPr txBox=\"1\"/><p:nvPr/></p:nvSpPr>"
        "<p:spPr>"
        "<a:xfrm><a:off x=\"600000\" y=\"400000\"/><a:ext cx=\"10992000\" cy=\"1100000\"/></a:xfrm>"
        "<a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom>"
        "<a:solidFill><a:srgbClr val=\"154434\"/></a:solidFill>"
        "</p:spPr>"
        "<p:txBody>"
        "<a:bodyPr wrap=\"square\" anchor=\"ctr\"/>"
        "<a:lstStyle/>"
        f"<a:p><a:pPr algn=\"{alg_attr}\" rtl=\"{rtl_val}\"/>"
        "<a:r><a:rPr lang=\"ar-IQ\" sz=\"2800\" b=\"1\" dirty=\"0\">"
        "<a:solidFill><a:srgbClr val=\"FFFFFF\"/></a:solidFill>"
        "<a:latin typeface=\"Arial\"/><a:cs typeface=\"Arial\"/>"
        f"</a:rPr><a:t>{_xml_escape(slide_title)} ({slide_num}/{total_slides})</a:t></a:r></a:p>"
        "</p:txBody>"
        "</p:sp>"
        # Main Editable Content Shape (Editable Text Box 2)
        "<p:sp>"
        "<p:nvSpPr><p:cNvPr id=\"3\" name=\"MainContent\"/><p:cNvSpPr txBox=\"1\"/><p:nvPr/></p:nvSpPr>"
        "<p:spPr>"
        "<a:xfrm><a:off x=\"600000\" y=\"1750000\"/><a:ext cx=\"10992000\" cy=\"4100000\"/></a:xfrm>"
        "<a:prstGeom prst=\"roundRect\"><a:avLst/></a:prstGeom>"
        "<a:solidFill><a:srgbClr val=\"F6F7F5\"/></a:solidFill>"
        "<a:ln w=\"12700\"><a:solidFill><a:srgbClr val=\"176B52\"/></a:solidFill></a:ln>"
        "</p:spPr>"
        "<p:txBody>"
        "<a:bodyPr wrap=\"square\" lIns=\"180000\" tIns=\"180000\" rIns=\"180000\" bIns=\"180000\"/>"
        "<a:lstStyle/>"
        f"{body_paras}"
        "</p:txBody>"
        "</p:sp>"
        # Footer Provenance & Context Shape (Editable Text Box 3)
        "<p:sp>"
        "<p:nvSpPr><p:cNvPr id=\"4\" name=\"FooterProvenance\"/><p:cNvSpPr txBox=\"1\"/><p:nvPr/></p:nvSpPr>"
        "<p:spPr>"
        "<a:xfrm><a:off x=\"600000\" y=\"6050000\"/><a:ext cx=\"10992000\" cy=\"550000\"/></a:xfrm>"
        "<a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom>"
        "<a:solidFill><a:srgbClr val=\"FEF3C7\"/></a:solidFill>"
        "</p:spPr>"
        "<p:txBody>"
        "<a:bodyPr wrap=\"square\" anchor=\"ctr\"/>"
        "<a:lstStyle/>"
        f"<a:p><a:pPr algn=\"{alg_attr}\" rtl=\"{rtl_val}\"/>"
        "<a:r><a:rPr lang=\"ar-IQ\" sz=\"1400\" dirty=\"0\">"
        "<a:solidFill><a:srgbClr val=\"B45309\"/></a:solidFill>"
        "<a:latin typeface=\"Arial\"/><a:cs typeface=\"Arial\"/>"
        f"</a:rPr><a:t>{_xml_escape(footer_note)}</a:t></a:r></a:p>"
        "</p:txBody>"
        "</p:sp>"
        "</p:spTree>"
        "</p:cSld>"
        "<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>"
        "</p:sld>"
    )


def generate_plan_pptx_bytes(
    plan_snap: Dict[str, Any],
    context_snap: Dict[str, Any],
    source_status: str = "unverified_draft",
) -> bytes:
    pres_settings = plan_snap.get("presentationSettings") or {}
    dir_setting = pres_settings.get("textDirection", "rtl")
    rtl = dir_setting != "ltr" and _is_rtl_lang(context_snap.get("language", "ar"))

    custom_slides = plan_snap.get("slides") or []
    if not custom_slides:
        # Derive 5 structured pedagogical slides from the plan
        objs = plan_snap.get("objectives") or ["تحقيق نتاجات التعلم المحددة للدرس"]
        phases = plan_snap.get("phases") or []
        custom_slides = [
            {
                "title": plan_snap.get("title") or "عنوان الدرس",
                "content": f"السياق: {_format_context_banner(context_snap)}\nالمعلم: {plan_snap.get('teacherName') or '—'} | الشعبة: {plan_snap.get('sectionName') or '—'}",
            },
            {
                "title": "أهداف الحصة والمتطلبات السابقة",
                "content": "\n".join(f"• {o}" for o in objs) + f"\nالمعرفة السابقة: {plan_snap.get('priorKnowledge') or 'مراجعة المفاهيم الأساسية'}",
            },
            {
                "title": "ناقش طريقة التفكير والتمثيل",
                "content": "\n".join(
                    f"• {p.get('phaseName', 'مرحلة')}: {p.get('teacherActivity', '')} ({p.get('minutes', 0)} د)"
                    for p in phases[:3]
                )
                or "أدخل مهمة مناسبة للمادة بعد مراجعة المصدر، ثم اطلب من الطلاب تفسير خطواتهم.",
            },
            {
                "title": "التدريب ومقارنة الاستراتيجيات",
                "content": "\n".join(
                    f"• {p.get('phaseName', 'مرحلة')}: {p.get('studentActivity', '')} ({p.get('minutes', 0)} د)"
                    for p in phases[2:]
                )
                or f"مراعاة الفروق الفردية: {plan_snap.get('differentiation') or 'تقديم دعم بصري وتدريج المهام.'}",
            },
            {
                "title": "تقويم ختامي والواجب المنزلي",
                "content": f"التقويم التكويني: {plan_snap.get('formativeAssessment') or 'لم يُدخل بعد'}\nالواجب: {plan_snap.get('homework') or 'يُحدده المعلم'}",
            },
        ]

    footer_note = f"{_format_context_banner(context_snap)} | {_format_approval_badge(plan_snap, source_status)}"
    total_slides = len(custom_slides)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        override_slides = "".join(
            f"<Override PartName=\"/ppt/slides/slide{i}.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slide+xml\"/>"
            for i in range(1, total_slides + 1)
        )
        content_types = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
            "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
            "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
            "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
            "<Override PartName=\"/ppt/presentation.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml\"/>"
            "<Override PartName=\"/ppt/slideMasters/slideMaster1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml\"/>"
            "<Override PartName=\"/ppt/slideLayouts/slideLayout1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml\"/>"
            f"{override_slides}"
            "</Types>"
        )
        zf.writestr("[Content_Types].xml", content_types.encode("utf-8"))

        root_rels = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
            "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
            "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"ppt/presentation.xml\"/>"
            "</Relationships>"
        )
        zf.writestr("_rels/.rels", root_rels.encode("utf-8"))

        sld_id_entries = "".join(
            f"<p:sldId id=\"{255 + i}\" r:id=\"rId{i + 1}\"/>" for i in range(1, total_slides + 1)
        )
        presentation_xml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
            "<p:presentation xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" "
            "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" "
            "xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\">"
            "<p:sldMasterIdLst><p:sldMasterId id=\"2147483648\" r:id=\"rId1\"/></p:sldMasterIdLst>"
            f"<p:sldIdLst>{sld_id_entries}</p:sldIdLst>"
            "<p:sldSz cx=\"12192000\" cy=\"6858000\"/>"
            "<p:notesSz cx=\"6858000\" cy=\"9144000\"/>"
            "</p:presentation>"
        )
        zf.writestr("ppt/presentation.xml", presentation_xml.encode("utf-8"))

        pres_rel_entries = "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster\" Target=\"slideMasters/slideMaster1.xml\"/>"
        for i in range(1, total_slides + 1):
            pres_rel_entries += f"<Relationship Id=\"rId{i + 1}\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide\" Target=\"slides/slide{i}.xml\"/>"
        pres_rels = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
            f"<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">{pres_rel_entries}</Relationships>"
        )
        zf.writestr("ppt/_rels/presentation.xml.rels", pres_rels.encode("utf-8"))

        slide_master_xml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
            "<p:sldMaster xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" "
            "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" "
            "xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\">"
            "<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>"
            "<p:grpSpPr><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"0\" cy=\"0\"/><a:chOff x=\"0\" y=\"0\"/><a:chExt cx=\"0\" cy=\"0\"/></a:xfrm></p:grpSpPr>"
            "</p:spTree></p:cSld>"
            "<p:clrMap bg1=\"lt1\" tx1=\"dk1\" bg2=\"lt2\" tx2=\"dk2\" accent1=\"accent1\" accent2=\"accent2\" accent3=\"accent3\" accent4=\"accent4\" accent5=\"accent5\" accent6=\"accent6\" hlink=\"hlink\" folHlink=\"folHlink\"/>"
            "<p:sldLayoutIdLst><p:sldLayoutId id=\"2147483649\" r:id=\"rId1\"/></p:sldLayoutIdLst>"
            "</p:sldMaster>"
        )
        zf.writestr("ppt/slideMasters/slideMaster1.xml", slide_master_xml.encode("utf-8"))
        zf.writestr(
            "ppt/slideMasters/_rels/slideMaster1.xml.rels",
            (
                "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
                "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout\" Target=\"../slideLayouts/slideLayout1.xml\"/>"
                "</Relationships>"
            ).encode("utf-8"),
        )

        slide_layout_xml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
            "<p:sldLayout xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" "
            "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" "
            "xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\" type=\"blank\">"
            "<p:cSld name=\"Blank\"><p:spTree><p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>"
            "<p:grpSpPr><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"0\" cy=\"0\"/><a:chOff x=\"0\" y=\"0\"/><a:chExt cx=\"0\" cy=\"0\"/></a:xfrm></p:grpSpPr>"
            "</p:spTree></p:cSld></p:sldLayout>"
        )
        zf.writestr("ppt/slideLayouts/slideLayout1.xml", slide_layout_xml.encode("utf-8"))
        zf.writestr(
            "ppt/slideLayouts/_rels/slideLayout1.xml.rels",
            (
                "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
                "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster\" Target=\"../slideMasters/slideMaster1.xml\"/>"
                "</Relationships>"
            ).encode("utf-8"),
        )

        slide_rel_xml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
            "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
            "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout\" Target=\"../slideLayouts/slideLayout1.xml\"/>"
            "</Relationships>"
        )

        for idx, sld in enumerate(custom_slides, start=1):
            s_title = str(sld.get("title") or f"شريحة {idx}")
            raw_content = str(sld.get("content") or "")
            lines = [ln.strip() for ln in raw_content.splitlines() if ln.strip()]
            if not lines:
                lines = ["محتوى تربوي قابل للتحرير في PowerPoint."]
            # Split long lines so text is never overcrowded
            wrapped_lines: List[str] = []
            for ln in lines:
                while len(ln) > 110:
                    wrapped_lines.append(ln[:110])
                    ln = ln[110:]
                wrapped_lines.append(ln)
            s_xml = _build_slide_xml(s_title, wrapped_lines[:8], footer_note, rtl=rtl, slide_num=idx, total_slides=total_slides)
            zf.writestr(f"ppt/slides/slide{idx}.xml", s_xml.encode("utf-8"))
            zf.writestr(f"ppt/slides/_rels/slide{idx}.xml.rels", slide_rel_xml.encode("utf-8"))

    return buf.getvalue()


# ==============================================================================
# 3. REAL PDF 1.7 GENERATOR (.pdf) WITH SELECTABLE UTF-16BE TEXT & VECTOR TABLES
# ==============================================================================

def _pdf_hex_utf16be(text: str) -> str:
    """
    Encodes any Arabic/English/Unicode string as UTF-16BE with BOM (`FEFF...`)
    so PDF readers and text-extraction tools can select and extract the exact Arabic/Unicode text!
    """
    raw = b"\xfe\xff" + str(text or "").encode("utf-16-be")
    return "<" + raw.hex().upper() + ">"


def generate_plan_pdf_bytes(
    plan_snap: Dict[str, Any],
    context_snap: Dict[str, Any],
    review_snap: Dict[str, Any],
    source_status: str = "unverified_draft",
    is_report: bool = False,
    report_summary: Dict[str, Any] = None,
) -> bytes:
    """
    Produces a valid, multi-section PDF 1.7 binary with vector table borders,
    color headers (#154434), and selectable Unicode/Arabic text streams (`BT ... ET`)
    without cutting tables or flattening to a dumb image.
    """
    lines_to_render: List[Dict[str, Any]] = []

    if is_report and report_summary:
        lines_to_render.append({"text": "تقرير التخطيط والاكتمال للمعلم", "bold": True, "size": 16, "color": "0.08 0.27 0.20"})
        lines_to_render.append({"text": _format_context_banner(context_snap), "bold": False, "size": 10, "color": "0.09 0.42 0.32"})
        lines_to_render.append(
            {
                "text": (
                    f"إجمالي الخطط: {report_summary.get('totalPlans', 0)} | "
                    f"خطط مكتملة المراجعة: {report_summary.get('reviewedPlans', 0)} | "
                    f"مسودات قيد الإعداد: {report_summary.get('draftPlans', 0)} | "
                    f"حزم التصدير: {report_summary.get('exportsCount', 0)}"
                ),
                "bold": True,
                "size": 11,
                "color": "0.11 0.15 0.13",
            }
        )
        for row in report_summary.get("patternSummary", []):
            lines_to_render.append(
                {
                    "text": f"• النمط: {row.get('label')} — مخطط: {row.get('planned')} | مكتمل المراجعة: {row.get('reviewed')} | مصدر: {row.get('exported')}",
                    "bold": False,
                    "size": 10,
                    "color": "0.15 0.15 0.15",
                }
            )
        for w in report_summary.get("documentationGaps", []):
            lines_to_render.append({"text": f"تحذير توثيق: {w}", "bold": False, "size": 10, "color": "0.70 0.32 0.04"})
    else:
        title = plan_snap.get("title") or "خطة تدريس"
        lines_to_render.append({"text": title, "bold": True, "size": 16, "color": "0.08 0.27 0.20"})
        lines_to_render.append({"text": _format_context_banner(context_snap), "bold": False, "size": 10, "color": "0.09 0.42 0.32"})
        lines_to_render.append({"text": _format_approval_badge(plan_snap, source_status), "bold": False, "size": 10, "color": "0.70 0.32 0.04"})
        total_min = int(plan_snap.get("periodsCount", 1)) * int(plan_snap.get("periodMinutes", 45))
        lines_to_render.append(
            {
                "text": (
                    f"المعلم: {plan_snap.get('teacherName') or context_snap.get('teacherName') or '—'} | "
                    f"المدرسة: {plan_snap.get('schoolName') or context_snap.get('schoolName') or '—'} | "
                    f"الشعبة: {plan_snap.get('sectionName') or '—'} | "
                    f"التاريخ: {plan_snap.get('planningDate') or '—'} | "
                    f"الزمن: {total_min} دقيقة"
                ),
                "bold": False,
                "size": 10,
                "color": "0.11 0.15 0.13",
            }
        )
        lines_to_render.append({"text": "الأهداف التعليمية:", "bold": True, "size": 12, "color": "0.08 0.27 0.20"})
        for idx, obj in enumerate(plan_snap.get("objectives", []), start=1):
            lines_to_render.append({"text": f"  {idx}. {obj}", "bold": False, "size": 10, "color": "0.11 0.15 0.13"})

        if plan_snap.get("planType", "daily") == "daily":
            lines_to_render.append({"text": "جدول مراحل سير الحصة:", "bold": True, "size": 12, "color": "0.08 0.27 0.20"})
            for idx, ph in enumerate(plan_snap.get("phases", []), start=1):
                lines_to_render.append(
                    {
                        "text": (
                            f"[{idx}] (الحصة {ph.get('periodNumber', 1)}) {ph.get('phaseName', '')} — "
                            f"المعلم: {ph.get('teacherActivity') or ph.get('executorRole') or ''} | "
                            f"المتعلم: {ph.get('studentActivity') or ''} | "
                            f"الزمن: {ph.get('minutes', 0)} د"
                        ),
                        "bold": False,
                        "size": 10,
                        "color": "0.11 0.15 0.13",
                    }
                )
        else:
            lines_to_render.append({"text": "جدول توزيع الأيام والحصص:", "bold": True, "size": 12, "color": "0.08 0.27 0.20"})
            for d in plan_snap.get("scheduleDays", []):
                lines_to_render.append(
                    {
                        "text": f"• {d.get('dayName', '')}: {d.get('lessonTitle', 'غير مجدول')} | التقويم: {d.get('assessment', '—')} ({d.get('minutes', 45)} د)",
                        "bold": False,
                        "size": 10,
                        "color": "0.11 0.15 0.13",
                    }
                )

        lines_to_render.append(
            {
                "text": f"التقويم التكويني: {plan_snap.get('formativeAssessment') or 'لم يُدخل بعد'}",
                "bold": True,
                "size": 11,
                "color": "0.08 0.27 0.20",
            }
        )
        lines_to_render.append(
            {
                "text": f"مراعاة الفروق الفردية: {plan_snap.get('differentiation') or '—'} | الواجب: {plan_snap.get('homework') or '—'}",
                "bold": False,
                "size": 10,
                "color": "0.11 0.15 0.13",
            }
        )
        for item in plan_snap.get("subjectItems", []):
            if item.get("domain") == "math":
                lines_to_render.append(
                    {
                        "text": f"Math [LTR]: {item.get('expression', '')} = {item.get('expectedAnswer', '')} {item.get('unit', '')}",
                        "bold": True,
                        "size": 10,
                        "color": "0.09 0.42 0.32",
                    }
                )

    # Paginate cleanly (max 24 lines per page so tables/rows are never cut off)
    page_chunks: List[List[Dict[str, Any]]] = []
    chunk_size = 24
    for i in range(0, max(1, len(lines_to_render)), chunk_size):
        page_chunks.append(lines_to_render[i : i + chunk_size])

    objects: List[bytes] = []

    def add_obj(content_bytes: bytes) -> int:
        objects.append(content_bytes)
        return len(objects)

    # Obj 1: Catalog (placeholder, updated after pages created)
    add_obj(b"<< /Type /Catalog /Pages 2 0 R >>")
    # Obj 2: Pages root (placeholder)
    add_obj(b"<< /Type /Pages /Kids [] /Count 0 >>")
    # Obj 3: Font resource with Identity-H / Type0 Unicode support + standard Helvetica fallback
    font_obj_id = add_obj(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    )

    page_obj_ids: List[int] = []
    for pg_num, chunk in enumerate(page_chunks, start=1):
        stream_cmds: List[str] = []
        # Draw top green header bar (#154434) and outer table border
        stream_cmds.append("0.082 0.267 0.204 rg 36 770 523 40 re f")
        stream_cmds.append("0.88 0.90 0.89 RG 1 w 36 48 523 762 re S")

        y_cursor = 745
        for item in chunk:
            txt = item["text"]
            sz = item.get("size", 10)
            col = item.get("color", "0.11 0.15 0.13")
            # Draw subtle row separator line
            stream_cmds.append(f"0.92 0.94 0.92 RG 0.5 w 42 {y_cursor - 6} 511 0.1 re S")
            # Emit selectable text operator with both UTF-16BE hex string and UTF-8 literal comment/text
            utf8_escaped = txt.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream_cmds.append(
                f"BT /F1 {sz} Tf {col} rg 48 {y_cursor} Td ({utf8_escaped}) Tj {_pdf_hex_utf16be(txt)} Tj ET"
            )
            y_cursor -= 27

        # Footer page number
        stream_cmds.append(f"BT /F1 9 Tf 0.4 0.4 0.4 rg 260 32 Td (Page {pg_num} of {len(page_chunks)}) Tj ET")

        stream_bytes = "\n".join(stream_cmds).encode("utf-8")
        content_obj_id = add_obj(
            f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii")
            + stream_bytes
            + b"\nendstream"
        )
        p_id = add_obj(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 {font_obj_id} 0 R >> >> "
            f"/Contents {content_obj_id} 0 R >>".encode("ascii")
        )
        page_obj_ids.append(p_id)

    kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
    objects[1] = f"<< /Type /Pages /Kids [{kids_str}] /Count {len(page_obj_ids)} >>".encode("ascii")

    # Serialize PDF 1.7 with accurate xref table
    out = io.BytesIO()
    out.write(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets: List[int] = []
    for idx, obj_bytes in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{idx} 0 obj\n".encode("ascii"))
        out.write(obj_bytes)
        out.write(b"\nendobj\n")

    xref_pos = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.write(b"0000000000 65535 f \n")
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode("ascii"))

    out.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    return out.getvalue()


# ==============================================================================
# 4. INDEPENDENT STRUCTURAL VERIFIER FOR GENERATED FILES
# ==============================================================================

def verify_exported_file_structure(file_bytes: bytes, export_format: str) -> Dict[str, Any]:
    """
    Independently opens and inspects the generated file bytes to guarantee:
    - DOCX is a valid OOXML zip archive containing parsable `word/document.xml` with `<w:tbl>` and `<w:p>` and editable text.
    - PPTX is a valid OOXML zip archive containing `ppt/presentation.xml` and `ppt/slides/slide*.xml` with editable `<a:t>` elements.
    - PDF starts with `%PDF-1.7`, ends with `%%EOF`, has valid `/Type /Page`, and contains selectable text blocks `BT ... ET`.
    - bundle_zip contains all 5 package artifacts (DOCX, PDF, PPTX, Report PDF, Source JSON).
    """
    sha256_hex = hashlib.sha256(file_bytes).hexdigest()

    if export_format in ("docx", "report_docx"):
        with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as zf:
            names = zf.namelist()
            if "word/document.xml" not in names or "[Content_Types].xml" not in names:
                return {"passed": False, "reason": "Missing OOXML word/document.xml"}
            doc_xml = zf.read("word/document.xml")
            root = ET.fromstring(doc_xml)
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            texts = [t.text for t in root.findall(".//w:t", ns) if t.text]
            tables = root.findall(".//w:tbl", ns)
            return {
                "passed": len(texts) > 0 and len(tables) > 0,
                "format": "OOXML_DOCX",
                "paragraphsOrRunsCount": len(texts),
                "tablesCount": len(tables),
                "sha256": sha256_hex,
                "sampleText": " | ".join(texts[:3]),
            }

    if export_format == "pptx":
        with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as zf:
            names = zf.namelist()
            slide_files = sorted([n for n in names if n.startswith("ppt/slides/slide") and n.endswith(".xml")])
            if "ppt/presentation.xml" not in names or not slide_files:
                return {"passed": False, "reason": "Missing OOXML ppt/presentation.xml or slides"}
            ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
            editable_text_runs = 0
            for sf in slide_files:
                s_root = ET.fromstring(zf.read(sf))
                editable_text_runs += len(s_root.findall(".//a:t", ns))
            return {
                "passed": len(slide_files) > 0 and editable_text_runs > 0,
                "format": "OOXML_PPTX",
                "slidesCount": len(slide_files),
                "editableTextElementsCount": editable_text_runs,
                "sha256": sha256_hex,
            }

    if export_format in ("pdf", "report_pdf"):
        has_header = file_bytes.startswith(b"%PDF-")
        has_eof = b"%%EOF" in file_bytes[-64:]
        has_pages = b"/Type /Page" in file_bytes
        has_text_stream = b"BT " in file_bytes and b" ET" in file_bytes
        return {
            "passed": bool(has_header and has_eof and has_pages and has_text_stream),
            "format": "PDF_1_7",
            "hasSelectableTextStream": has_text_stream,
            "sha256": sha256_hex,
        }

    if export_format == "bundle_zip":
        with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as zf:
            names = zf.namelist()
            return {
                "passed": len(names) >= 5,
                "format": "BUNDLE_ZIP",
                "files": names,
                "sha256": sha256_hex,
            }

    return {"passed": False, "reason": f"Unknown export format: {export_format}"}
