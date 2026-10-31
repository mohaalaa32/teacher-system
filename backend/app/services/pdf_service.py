import hashlib
import re
import zlib
from typing import Dict, Any, List


MAX_PDF_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB limit
MAX_PDF_PAGES = 600


def detect_ocr_ambiguities(text: str) -> List[Dict[str, str]]:
    """
    Detects potentially ambiguous OCR tokens relevant to subjects:
    - Proper names / quotes / dates
    - Math signs, exponents, fractions
    - Broken or suspicious symbol sequences
    """
    ambiguities: List[Dict[str, str]] = []
    if not text or not text.strip():
        return [
            {
                "type": "scanned_or_empty_page",
                "snippet": "صفحة خالية من طبقة نصية",
                "reason": "يتطلب OCR أو تفريغًا يدويًا ومراجعة بشرية للنص والأعلام والمعادلات.",
            }
        ]

    # Check for fraction/exponent/sign patterns that might be inverted or ambiguous in RTL/LTR PDF extraction
    math_matches = re.findall(r"[\d]+[\/÷\^\-\+][\d]+", text)
    if math_matches:
        ambiguities.append(
            {
                "type": "math_symbols_and_fractions",
                "snippet": "، ".join(math_matches[:4]),
                "reason": "تحقق من اتجاه الإشارات والكسور والأسس (LTR) بعد الاستخراج.",
            }
        )

    # Check for dates/years
    date_matches = re.findall(r"\b(?:1\d{3}|20\d{2}|\d{1,2}/\d{1,2}/\d{2,4})\b", text)
    if date_matches:
        ambiguities.append(
            {
                "type": "dates_and_chronology",
                "snippet": "، ".join(date_matches[:4]),
                "reason": "تحقق من مطابقة التواريخ والأرقام للمصدر المطبوع.",
            }
        )

    # Check for quotes
    quote_matches = re.findall(r"[«\"]([^»\"]{5,80})[»\"]", text)
    if quote_matches:
        ambiguities.append(
            {
                "type": "quotes_and_attribution",
                "snippet": quote_matches[0][:60],
                "reason": "تحقق من دقة الاقتباس ونسبته وأسماء الأعلام.",
            }
        )

    return ambiguities


def _decode_pdf_literal_string(raw_bytes: bytes) -> str:
    # Handle UTF-16BE BOM if present
    if raw_bytes.startswith(b"\xfe\xff"):
        try:
            return raw_bytes[2:].decode("utf-16-be", errors="ignore")
        except Exception:
            pass
    try:
        return raw_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return raw_bytes.decode("latin-1", errors="ignore")


def _extract_text_from_pdf_stream(stream_data: bytes) -> str:
    chunks: List[str] = []
    # Match literal strings (...) and hex strings <...> inside BT ... ET blocks or stream
    for match in re.finditer(rb"\(([^()\\]*(?:\\.[^()\\]*)*)\)", stream_data):
        raw = match.group(1)
        # Unescape standard PDF escapes
        raw = raw.replace(b"\\(", b"(").replace(b"\\)", b")").replace(b"\\n", b"\n").replace(b"\\r", b"\r")
        txt = _decode_pdf_literal_string(raw).strip()
        if txt:
            chunks.append(txt)

    for match in re.finditer(rb"<([0-9A-Fa-f]{4,})>", stream_data):
        hex_bytes = match.group(1)
        if len(hex_bytes) % 2 == 0:
            try:
                raw = bytes.fromhex(hex_bytes.decode("ascii"))
                txt = _decode_pdf_literal_string(raw).strip()
                if txt and any(ch.isalnum() for ch in txt):
                    chunks.append(txt)
            except Exception:
                pass

    return " ".join(chunks)


def inspect_and_extract_pdf(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Validates actual PDF magic signature (%PDF-), size limits, and page count.
    Extracts text per page if textual streams exist, or marks `requires_ocr_or_manual`
    without ever inventing fake chapters or claiming successful extraction from filename alone.
    """
    if not file_bytes or len(file_bytes) < 8:
        raise ValueError("الملف المرفوع فارغ أو تالف.")

    if len(file_bytes) > MAX_PDF_SIZE_BYTES:
        raise ValueError(f"حجم الملف يتجاوز الحد المسموح به ({MAX_PDF_SIZE_BYTES // (1024 * 1024)} ميجابايت).")

    # Check actual PDF magic bytes at start of file (do not trust file extension!)
    header_window = file_bytes[:1024]
    if b"%PDF-" not in header_window[:16]:
        raise ValueError("توقيع الملف غير صالح: الملف المرفوع ليس ملف PDF حقيقيًا (%PDF- مفقود).")

    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    # Count `/Type /Page` (excluding `/Type /Pages`)
    page_matches = re.findall(rb"/Type\s*/Page\b(?!s)", file_bytes)
    page_count = len(page_matches)
    if page_count == 0:
        # Fallback check for /Count
        count_matches = re.findall(rb"/Count\s+(\d+)", file_bytes)
        if count_matches:
            page_count = max(int(c) for c in count_matches)
        else:
            page_count = 1

    if page_count > MAX_PDF_PAGES:
        raise ValueError(f"عدد صفحات الملف ({page_count}) يتجاوز الحد الأقصى المسموح ({MAX_PDF_PAGES} صفحة).")

    # Extract streams
    extracted_stream_texts: List[str] = []
    for stream_match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", file_bytes, re.DOTALL):
        raw_stream = stream_match.group(1)
        decompressed = raw_stream
        try:
            decompressed = zlib.decompress(raw_stream)
        except Exception:
            pass
        txt = _extract_text_from_pdf_stream(decompressed)
        if txt.strip():
            extracted_stream_texts.append(txt.strip())

    pages_result: List[Dict[str, Any]] = []
    has_meaningful_text = False

    for pg_idx in range(1, min(page_count, 50) + 1):
        stream_txt = extracted_stream_texts[pg_idx - 1] if pg_idx - 1 < len(extracted_stream_texts) else ""
        # Clean non-printable characters
        stream_txt = "".join(ch for ch in stream_txt if ch.isprintable() or ch in "\n\r\t")
        if len(stream_txt.strip()) >= 3:
            has_meaningful_text = True
            needs_ocr = False
        else:
            needs_ocr = True

        ambiguities = detect_ocr_ambiguities(stream_txt)
        pages_result.append(
            {
                "pdfPageNumber": pg_idx,
                "printedPageNumber": str(pg_idx),
                "extractedText": stream_txt if stream_txt.strip() else "",
                "correctedText": stream_txt if stream_txt.strip() else "",
                "needsOcrReview": needs_ocr or len(ambiguities) > 0,
                "ocrAmbiguities": ambiguities,
                "humanReviewed": False,
            }
        )

    extraction_status = "extracted_text" if has_meaningful_text else "requires_ocr_or_manual"

    return {
        "sha256Fingerprint": sha256_hash,
        "fileSize": len(file_bytes),
        "pageCount": page_count,
        "extractionStatus": extraction_status,
        "pages": pages_result,
    }

