import re
from collections.abc import Mapping, Sequence
from uuid import uuid4

from fastapi import HTTPException
from fastapi.responses import JSONResponse

CORRELATION_ID_HEADER = "X-Correlation-ID"
_SAFE_REQUEST_ID = r"^[A-Za-z0-9._:-]{1,128}$"
_SAFE_CODE = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,100}$"
_SAFE_META_KEYS = frozenset(
    {
        "current_state",
        "eligible_packages",
        "entitlement",
        "maximum_weeks",
        "missing_fields",
        "problems",
        "reason_codes",
        "requested_weeks",
        "reset_at",
        "retry_after_seconds",
        "safety_status",
    }
)

_STATUS_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_SERVER_ERROR",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
}

_MESSAGES = {
    "AUTH_INVALID_CREDENTIALS": "ایمیل یا رمز عبور درست نیست.",
    "AUTH_OTP_INVALID_OR_EXPIRED": "کد واردشده معتبر نیست یا منقضی شده است.",
    "AUTH_EMAIL_ALREADY_REGISTERED": "این ایمیل قبلاً ثبت شده است.",
    "AUTH_SESSION_EXPIRED": "نشست شما منقضی شده است. دوباره وارد حساب شوید.",
    "AUTHENTICATION_REQUIRED": "برای ادامه دوباره وارد حساب شوید.",
    "BEARER_AUTHENTICATION_REQUIRED": "برای ادامه باید وارد حساب شوید.",
    "AUTH_RATE_LIMITED": "درخواست‌های ورود زیاد است. کمی بعد دوباره تلاش کنید.",
    "AUTH_GOOGLE_FAILED": "ورود با گوگل انجام نشد. دوباره تلاش کنید.",
    "AUTH_APPLE_FAILED": "ورود با اپل انجام نشد. دوباره تلاش کنید.",
    "AUTH_PASSWORD_RESET_INVALID": "لینک بازنشانی رمز عبور معتبر نیست یا منقضی شده است.",
    "AUTH_EMAIL_VERIFICATION_INVALID": "لینک تأیید ایمیل معتبر نیست یا منقضی شده است.",
    "TRUSTED_ORIGIN_REQUIRED": "ارسال امن درخواست انجام نشد. دوباره تلاش کنید.",
    "PROFILE_INCOMPLETE": "برای ادامه، اطلاعات پروفایل را کامل کنید.",
    "PROFILE_WEIGHT_REQUIRED": "وزن در پروفایل ثبت نشده است. ابتدا وزن را تکمیل کنید.",
    "PROFILE_HEIGHT_REQUIRED": "قد در پروفایل ثبت نشده است. ابتدا قد را تکمیل کنید.",
    "AGE_NOT_SUPPORTED": "فیتیشن در حال حاضر برای افراد ۱۸ سال و بالاتر ارائه می‌شود.",
    "AGE_OUT_OF_RANGE": "تاریخ تولد واردشده پشتیبانی نمی‌شود.",
    "PROFILE_NOT_FOUND": "پروفایل فیتنس پیدا نشد.",
    "PROFILE_ALREADY_EXISTS": "پروفایل فیتنس قبلاً ساخته شده است.",
    "PRODUCT_MODE_REQUIRED": "ابتدا مسیر فیتیشن را انتخاب کنید.",
    "HOME_TRAINING_SETUP_REQUIRED": "ابتدا تجهیزات و setup تمرین خانگی را مشخص کنید.",
    "PREFERRED_WEEKDAYS_INVALID": "روزهای انتخابی تمرین معتبر نیستند.",
    "WORKOUT_GENERATION_IN_PROGRESS": (
        "ساخت برنامه تمرینی در حال انجام است. بعداً دوباره بررسی کنید."
    ),
    "WORKOUT_GENERATION_COOLDOWN": "ساخت برنامه تازه انجام شده است. کمی بعد دوباره تلاش کنید.",
    "WORKOUT_GENERATION_UNSUPPORTED": "با اطلاعات فعلی، ساخت برنامه ایمن ممکن نیست.",
    "WORKOUT_PLAN_NOT_FOUND": "برنامه تمرینی پیدا نشد.",
    "WORKOUT_ACTIVE_PLAN_NOT_FOUND": "برنامه تمرینی فعالی وجود ندارد.",
    "WORKOUT_PLAN_NOT_EXECUTABLE": "این نسخه از برنامه در وضعیت قابل اجرا نیست.",
    "NUTRITION_PROFILE_INCOMPLETE": "برای ادامه، اطلاعات تغذیه را در پروفایل کامل کنید.",
    "NUTRITION_PROFILE_NOT_FOUND": "پروفایل تغذیه ثبت نشده است.",
    "NUTRITION_PLAN_NOT_FOUND": "هنوز برنامه غذایی هفتگی ساخته نشده است.",
    "ACTIVE_NUTRITION_PLAN_NOT_FOUND": "هنوز برنامه غذایی تأییدشده و فعالی وجود ندارد.",
    "SAFETY_DECISION_NOT_FOUND": "ارزیابی ایمنی هنوز ثبت نشده است.",
    "SAFETY_SCREEN_REQUIRED": "پیش از ادامه، ارزیابی ایمنی را کامل کنید.",
    "NUTRITION_ESTIMATE_BLOCKED": "با اطلاعات فعلی، برآورد تغذیه‌ای قابل انجام نیست.",
    "BODY_PHOTO_INVALID": "این عکس برای تحلیل بدن قابل استفاده نیست.",
    "BODY_PHOTO_SESSION_NOT_FOUND": "نشست عکس بدن پیدا نشد.",
    "BODY_PHOTO_SESSION_STATE_INVALID": "وضعیت این نشست تغییر کرده است. آن را دوباره باز کنید.",
    "BODY_ANALYSIS_NOT_FOUND": "تحلیل بدن پیدا نشد.",
    "BODY_ANALYSIS_NOT_READY": "این نشست هنوز برای تحلیل آماده نیست.",
    "BODY_ANALYSIS_PROVIDER_UNAVAILABLE": "سرویس تحلیل بدن فعلاً در دسترس نیست.",
    "missing_body_analysis_inputs": "اطلاعات لازم برای تحلیل بدن کامل نیست.",
    "measurement_confirmation_required": "پیش از تحلیل، اندازه‌گیری‌های فعلی را تأیید کنید.",
    "MEASUREMENT_CONFIRMATION_REQUIRED": "تأیید کنید اندازه‌گیری‌های فعلی مربوط به این اسکن هستند.",
    "COACH_ROLE_REQUIRED": "این عملیات فقط برای مربی در دسترس است.",
    "PHYSICIAN_ROLE_REQUIRED": "این عملیات فقط برای پزشک در دسترس است.",
    "SPECIALIST_RELATIONSHIP_REQUIRED": "این متخصص به پرونده موردنظر دسترسی ندارد.",
    "REVIEW_ALREADY_COMPLETED": "این بررسی قبلاً تکمیل شده است.",
    "REVIEW_INVALID_STATE": "این بررسی دیگر در وضعیت قابل انجام نیست.",
    "ENTITLEMENT_REQUIRED": "برای استفاده از این قابلیت، دسترسی لازم را فعال کنید.",
    "ENTITLEMENT_QUOTA_EXCEEDED": "سهم استفاده از این قابلیت تمام شده است.",
    "ACCESS_TERM_TOO_SHORT": "مدت انتخاب‌شده بیشتر از سقف دسترسی مجاز است.",
    "VALIDATION_ERROR": "اطلاعات واردشده را بررسی و موارد مشخص‌شده را اصلاح کنید.",
    "BAD_REQUEST": "درخواست معتبر نیست. اطلاعات را بررسی کنید.",
    "UNAUTHORIZED": "نشست شما منقضی شده است. دوباره وارد حساب شوید.",
    "FORBIDDEN": "برای این عملیات دسترسی لازم وجود ندارد.",
    "NOT_FOUND": "مورد درخواست‌شده پیدا نشد.",
    "CONFLICT": "این عملیات با وضعیت فعلی سازگار نیست.",
    "RATE_LIMITED": "درخواست‌های زیادی ارسال شده است. کمی بعد دوباره تلاش کنید.",
    "BAD_GATEWAY": "سرویس نتوانست درخواست را کامل کند. دوباره تلاش کنید.",
    "SERVICE_UNAVAILABLE": "سرویس موقتاً در دسترس نیست. کمی بعد دوباره تلاش کنید.",
    "INTERNAL_SERVER_ERROR": "خطای غیرمنتظره‌ای رخ داد. دوباره تلاش کنید.",
}

_MESSAGE_CODES = {
    "apple authentication failed": "AUTH_APPLE_FAILED",
    "authentication required": "AUTHENTICATION_REQUIRED",
    "bearer authentication required": "BEARER_AUTHENTICATION_REQUIRED",
    "email is already registered": "AUTH_EMAIL_ALREADY_REGISTERED",
    "google authentication failed": "AUTH_GOOGLE_FAILED",
    "invalid email or password": "AUTH_INVALID_CREDENTIALS",
    "invalid or expired otp": "AUTH_OTP_INVALID_OR_EXPIRED",
    "invalid or expired refresh token": "AUTH_SESSION_EXPIRED",
    "invalid or expired reset token": "AUTH_PASSWORD_RESET_INVALID",
    "invalid or expired verification token": "AUTH_EMAIL_VERIFICATION_INVALID",
    "body analysis is temporarily unavailable": "BODY_ANALYSIS_PROVIDER_UNAVAILABLE",
    "too many authentication requests": "AUTH_RATE_LIMITED",
}

_FIELD_LABELS = {
    "weight_kg": "وزن",
    "current_weight_kg": "وزن",
    "height_cm": "قد",
    "date_of_birth": "تاریخ تولد",
    "birth_date": "تاریخ تولد",
    "training_days": "تعداد روزهای تمرین",
    "training_days_per_week": "تعداد روزهای تمرین",
    "session_duration_minutes": "زمان جلسه تمرین",
    "plan_duration_weeks": "مدت برنامه",
    "preferred_weekdays": "روزهای انتخابی تمرین",
    "email": "ایمیل",
    "password": "رمز عبور",
}


def _is_safe(value: object, pattern: str) -> bool:
    return isinstance(value, str) and re.fullmatch(pattern, value) is not None


def _safe_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split())
    return normalized[:500] if normalized else None


def create_request_id(candidate: str | None = None) -> str:
    if isinstance(candidate, str) and re.fullmatch(_SAFE_REQUEST_ID, candidate) is not None:
        return candidate
    return uuid4().hex


def _safe_json_value(value: object) -> object | None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        list_result = [_safe_json_value(item) for item in value]
        return [item for item in list_result if item is not None]
    if isinstance(value, Mapping):
        dict_result: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                continue
            normalized = _safe_json_value(item)
            if normalized is not None:
                dict_result[key] = normalized
        return dict_result
    return None


def _safe_meta(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str) or key not in _SAFE_META_KEYS:
            continue
        normalized = _safe_json_value(item)
        if normalized is not None:
            result[key] = normalized
    return result


def _retryable_for_status(status_code: int) -> bool:
    return status_code in {408, 425, 429} or status_code >= 500


def _field_name(item: Mapping[str, object]) -> str | None:
    explicit = item.get("field")
    if isinstance(explicit, str) and explicit:
        return explicit[:100]
    location = item.get("loc")
    if not isinstance(location, Sequence) or isinstance(location, (str, bytes, bytearray)):
        return None
    parts = [
        str(part)
        for part in location
        if isinstance(part, (str, int)) and str(part) not in {"body", "query", "path"}
    ]
    return ".".join(parts)[:100] or None


def _field_code(item: Mapping[str, object]) -> str:
    raw = item.get("code") or item.get("type") or "invalid"
    code = _safe_text(raw)
    if code is None:
        return "invalid"
    if code == "missing" or code.endswith(".missing"):
        return "required"
    return code[:100]


def _field_message(field: str | None, code: str) -> str:
    label = _FIELD_LABELS.get(field or "", field or "این فیلد")
    normalized_code = code.lower()
    if code == "required" or "missing" in normalized_code:
        return f"{label} وارد نشده است."
    if any(part in normalized_code for part in ("greater", "less", "range", "between")):
        return f"{label} باید در بازه مجاز باشد."
    return f"{label} معتبر نیست."


def _normalize_fields(errors: object) -> list[dict[str, str | None]]:
    if not isinstance(errors, Sequence) or isinstance(errors, (str, bytes, bytearray)):
        return []
    result: list[dict[str, str | None]] = []
    for raw_item in errors:
        if not isinstance(raw_item, Mapping):
            continue
        field = _field_name(raw_item)
        code = _field_code(raw_item)
        result.append(
            {
                "field": field,
                "code": code,
                "message": _field_message(field, code),
            }
        )
    return result


def normalize_validation_errors(
    errors: Sequence[Mapping[str, object]],
    request_id: str | None = None,
    *,
    code: str = "VALIDATION_ERROR",
    message: str | None = None,
) -> dict[str, object]:
    normalized_code = code if _is_safe(code, _SAFE_CODE) else "VALIDATION_ERROR"
    return {
        "code": normalized_code,
        "message": (
            message or _MESSAGES[normalized_code]
            if normalized_code in _MESSAGES
            else _MESSAGES["VALIDATION_ERROR"]
        ),
        "retryable": False,
        "fields": _normalize_fields(errors),
        "meta": {},
        "request_id": create_request_id(request_id),
    }


def _code_from_message(message: object) -> str | None:
    normalized = _safe_text(message)
    if normalized is None:
        return None
    return _MESSAGE_CODES.get(normalized.lower())


def _code_from_detail(status_code: int, detail: object) -> str:
    if isinstance(detail, Mapping):
        explicit = detail.get("code")
        if _is_safe(explicit, _SAFE_CODE):
            return explicit  # type: ignore[return-value]
        from_message = _code_from_message(detail.get("message"))
        if from_message is not None:
            return from_message
    elif isinstance(detail, str):
        from_message = _code_from_message(detail)
        if from_message is not None:
            return from_message
    return _STATUS_CODES.get(
        status_code,
        "INTERNAL_SERVER_ERROR" if status_code >= 500 else "BAD_REQUEST",
    )


def _message_for_code(code: str, status_code: int, provided: object) -> str:
    if code in _MESSAGES:
        return _MESSAGES[code]
    candidate = _safe_text(provided)
    if status_code >= 500:
        return _MESSAGES["INTERNAL_SERVER_ERROR"]
    if candidate is not None:
        lowered = candidate.lower()
        if not any(
            marker in lowered
            for marker in (
                "password",
                "token",
                "secret",
                "authorization",
                "cookie",
                "stack",
                "traceback",
                "select ",
                "/",
            )
        ):
            return candidate
    return _MESSAGES.get(code, _MESSAGES["BAD_REQUEST"])


def build_error_detail(
    status_code: int,
    detail: object,
    request_id: str | None = None,
    *,
    fields: object = None,
    meta: object = None,
    retryable: bool | None = None,
) -> dict[str, object]:
    detail_mapping = detail if isinstance(detail, Mapping) else {}
    code = _code_from_detail(status_code, detail)
    provided_message = detail_mapping.get("message") if detail_mapping else detail
    normalized_fields = _normalize_fields(
        fields if fields is not None else detail_mapping.get("fields")
    )
    if not normalized_fields and isinstance(detail_mapping.get("missing_fields"), Sequence):
        normalized_fields = [
            {
                "field": field,
                "code": "required",
                "message": _field_message(field, "required"),
            }
            for field in detail_mapping["missing_fields"]
            if isinstance(field, str) and field
        ]
    if (
        fields is None
        and not normalized_fields
        and isinstance(detail, Sequence)
        and not isinstance(detail, str)
    ):
        normalized_fields = _normalize_fields(detail)
        code = "VALIDATION_ERROR"
    detail_meta = _safe_meta(detail_mapping.get("meta"))
    for key in _SAFE_META_KEYS:
        if key in detail_mapping and key not in detail_meta:
            normalized = _safe_json_value(detail_mapping[key])
            if normalized is not None:
                detail_meta[key] = normalized
    detail_meta.update(
        {key: value for key, value in _safe_meta(meta).items() if key not in detail_meta}
    )
    result: dict[str, object] = {
        "code": code,
        "message": _message_for_code(code, status_code, provided_message),
        "retryable": _retryable_for_status(status_code) if retryable is None else retryable,
        "meta": detail_meta,
        "request_id": create_request_id(request_id),
    }
    if normalized_fields:
        result["fields"] = normalized_fields
    return result


def error_response(
    status_code: int,
    detail: object,
    request_id: str | None = None,
    *,
    headers: Mapping[str, str] | None = None,
    fields: object = None,
    meta: object = None,
    retryable: bool | None = None,
) -> JSONResponse:
    response_request_id = create_request_id(request_id)
    response = JSONResponse(
        status_code=status_code,
        content={
            "detail": build_error_detail(
                status_code,
                detail,
                response_request_id,
                fields=fields,
                meta=meta,
                retryable=retryable,
            )
        },
        headers=dict(headers or {}),
    )
    response.headers[CORRELATION_ID_HEADER] = response_request_id
    return response


def build_error_response(error: HTTPException, request_id: str | None = None) -> JSONResponse:
    return error_response(
        error.status_code,
        error.detail,
        request_id,
        headers=error.headers,
    )
