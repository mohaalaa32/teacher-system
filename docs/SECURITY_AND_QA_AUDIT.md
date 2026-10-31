# تقرير مراقبة الكود المستقلة والتدقيق الأمني (SECURITY & QA AUDIT)

أُجري هذا التدقيق لفحص العقود والأمن وعزل السياقات وجودة المستندات المصدّرة وبوابات الإطلاق.

---

## 1. مصفوفة فحص الأمن وعزل السياقات

| مجال التدقيق | آلية الحماية المنفذة | الملف / الموضع | اختبار التحقق الآلي | الحالة |
| :--- | :--- | :--- | :--- | :--- |
| **منع الكتابة المتأخرة عبر السياقات (Stale Context Write)** | مقارنة ترويسة `X-Active-Context-Id` مع `contextId` في الطلب؛ رفض الطلب برمز `409 STALE_CONTEXT_WRITE_BLOCKED` عند الاختلاف | [`backend/app/main.py`](../backend/app/main.py) (`verify_active_context_guard`) | `test_context_isolation_and_stale_write_rejection` في [`test_api.py`](../backend/tests/test_api.py) | ✅ ناجح |
| **منع ربط خطة بمصدر أو درس من سياق آخر** | استعلام يتحقق من تطابق `CurriculumSource.context_id == payload.contextId` قبل الحفظ؛ يرفض بـ `400 CROSS_CONTEXT_SOURCE_FORBIDDEN` | [`backend/app/main.py`](../backend/app/main.py) (`create_plan`, `update_plan`) | `test_context_isolation_and_stale_write_rejection` في [`test_api.py`](../backend/tests/test_api.py) | ✅ ناجح |
| **ثبات السياق التاريخي عند التعديل** | حفظ لقطة السياق السبعة `context_snapshot` داخل `PlanVersion` و`ExportTask` بحيث لا يغيّر تعديل السياق لاحقًا أي إصدار سابق | [`backend/app/models.py`](../backend/app/models.py) (`PlanVersion`, `ExportTask`) | `test_plan_audit_approval_and_revocation_on_edit` في [`test_api.py`](../backend/tests/test_api.py) | ✅ ناجح |
| **إلغاء الاعتماد عند التعديل اللاحق** | أي تعديل على خطة معتمدة يرفع رقم الإصدار `version += 1` ويعيد حالة الإصدار الجديد إلى مسودة/مراجعة مع بقاء الإصدار المعتمد محفوظًا في `plan_versions` | [`backend/app/main.py`](../backend/app/main.py) (`update_plan`) | `test_plan_audit_approval_and_revocation_on_edit` في [`test_api.py`](../backend/tests/test_api.py) | ✅ ناجح |
| **فحص التوقيع الفعلي لملف PDF ومنع Path Traversal** | فحص البايتات السحرية `%PDF-` في ترويسة الملف وتطهير اسم الملف بـ `os.path.basename` وتعبير نمطي آمن | [`backend/app/services/pdf_service.py`](../backend/app/services/pdf_service.py) (`inspect_and_extract_pdf`) | `test_pdf_upload_signature_validation_and_real_exports` في [`test_api.py`](../backend/tests/test_api.py) | ✅ ناجح |
| **منع تسريب Traceback والأسرار** | معالج استثناءات موحد يرجع رسالة عربية مفهومة ورمز خطأ ثابت ومعرف الطلب `X-Request-ID` فقط | [`backend/app/main.py`](../backend/app/main.py) (`request_id_and_security_middleware`) | مفحوص في جميع مسارات الأخطاء | ✅ ناجح |
| **منع القسمة على صفر والأخطاء العددية** | محلل AST رياضي آمن يفحص المقامات قبل القسمة ويرفع `MATH_DIVISION_BY_ZERO` ويقارن الحل العددي والوحدات | [`backend/app/services/audit_service.py`](../backend/app/services/audit_service.py) (`safe_eval_math_expression`) | `test_math_safe_eval_and_zero_division` في [`test_audit_and_math.py`](../backend/tests/test_audit_and_math.py) | ✅ ناجح |

---

## 2. فصل عوائق الإصدار/الاعتماد عن تحذيرات المصادر

1. **عوائق اعتماد الخطة (`BLOCKER`)**:
   - غياب طريقة التقويم التكويني (`MISSING_FORMATIVE_ASSESSMENT`).
   - تناقض مجموع أزمنة المراحل مع زمن الحصة/الحصتين (`TIME_DISTRIBUTION_MISMATCH`) أو وجود زمن سالب.
   - خطأ رياضي أو قسمة على صفر (`MATH_DIVISION_BY_ZERO`, `MATH_ANSWER_MISMATCH`) أو اضطراب تسلسل تاريخي (`HISTORY_CHRONOLOGY_INVALID`).
   - ادعاء الرسمية لمصدر منهج دون دليل ومراجعة بشرية (`UNVERIFIED_OFFICIAL_CLAIM`).
2. **تحذيرات المصادر غير المانعة لحفظ المسودة أو التصدير المعلّم (`SOURCE_WARNING`)**:
   - عدم رفع ملف PDF للكتاب الرسمي بعد أو بقاء المصدر قيد المراجعة (`SOURCE_PENDING_VERIFICATION`).
   - ترك حقول غير معروفة (مثل السنة أو الطبعة) فارغة بدل تخمينها (`INCOMPLETE_CONTEXT_FIELDS`).
   - وجود محتوى تدريبي مؤلف معلّم بـ «مثال توضيحي غير موثق من الكتاب» (`AUTHORED_ILLUSTRATIVE_CONTENT`).
   - حاجة صفحات PDF الممسوحة إلى مراجعة OCR بشرية (`SOURCE_REQUIRES_OCR_REVIEW`).

