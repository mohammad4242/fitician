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
    "AUTH_APPLE_ACCOUNT_CONFLICT": "این حساب اپل به حساب دیگری متصل است.",
    "AUTH_APPLE_PLATFORM_UNSUPPORTED": "ورود با اپل فقط در iOS در دسترس است.",
    "AUTH_GOOGLE_ACCOUNT_CONFLICT": "این حساب گوگل به حساب دیگری متصل است.",
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
    "SHARED_PROFILE_NOT_FOUND": "اطلاعات پایه پروفایل ثبت نشده است.",
    "UNSUPPORTED_RESISTANCE_TRAINING_DAYS": "تعداد روزهای تمرین با سطح فعلی سازگار نیست.",
    "ACCOUNT_DELETION_NOT_ENABLED": "حذف حساب فعلاً در دسترس نیست. بعداً دوباره تلاش کنید.",
    "ADMIN_ROLE_REQUIRED": "این عملیات فقط برای مدیر در دسترس است.",
    "AI_CONFIGURATION_INVALID": "تنظیمات هوش مصنوعی معتبر نیست.",
    "AI_CREDENTIAL_STORAGE_ERROR": "ذخیره امن اعتبار هوش مصنوعی انجام نشد.",
    "AGENT_SERVICE_NOT_CONFIGURED": "سرویس Agent برای این قابلیت پیکربندی نشده است.",
    "AGENT_SERVICE_UNAVAILABLE": "سرویس Agent موقتاً در دسترس نیست.",
    "invalid_file_size": "حجم عکس بیشتر از حد مجاز است. عکس کوچک‌تری انتخاب کنید.",
    "invalid_geometry": "عکس باید مربعی و در اندازه مجاز باشد.",
    "unsupported_format": "فرمت این عکس پشتیبانی نمی‌شود.",
    "invalid_image": "فایل عکس معتبر نیست. عکس دیگری انتخاب کنید.",
    "image_too_large": "ابعاد عکس بیشتر از حد مجاز است. عکس کوچک‌تری انتخاب کنید.",
    "PROFILE_PHOTO_ACCESS_DENIED": "دسترسی به عکس پروفایل وجود ندارد.",
    "PROFILE_PHOTO_NOT_FOUND": "عکس پروفایل پیدا نشد.",
    "EXERCISE_SLUG_ALREADY_EXISTS": "این شناسه قبلاً استفاده شده است.",
    "PRODUCT_MODE_REQUIRED": "ابتدا مسیر فیتیشن را انتخاب کنید.",
    "HOME_TRAINING_SETUP_REQUIRED": "ابتدا تجهیزات و setup تمرین خانگی را مشخص کنید.",
    "PREFERRED_WEEKDAYS_INVALID": "روزهای انتخابی تمرین معتبر نیستند.",
    "WORKOUT_GENERATION_IN_PROGRESS": (
        "ساخت برنامه تمرینی در حال انجام است. بعداً دوباره بررسی کنید."
    ),
    "WORKOUT_GENERATION_COOLDOWN": "ساخت برنامه تازه انجام شده است. کمی بعد دوباره تلاش کنید.",
    "WORKOUT_GENERATION_FAILED": "ساخت برنامه تمرینی کامل نشد. دوباره تلاش کنید.",
    "WORKOUT_GENERATION_UNSUPPORTED": "با اطلاعات فعلی، ساخت برنامه ایمن ممکن نیست.",
    "WORKOUT_PLAN_NOT_FOUND": "برنامه تمرینی پیدا نشد.",
    "WORKOUT_ACTIVE_PLAN_NOT_FOUND": "برنامه تمرینی فعالی وجود ندارد.",
    "WORKOUT_PLAN_NOT_EXECUTABLE": "این نسخه از برنامه در وضعیت قابل اجرا نیست.",
    "NUTRITION_PROFILE_INCOMPLETE": "برای ادامه، اطلاعات تغذیه را در پروفایل کامل کنید.",
    "NUTRITION_PROFILE_NOT_FOUND": "پروفایل تغذیه ثبت نشده است.",
    "NUTRITION_PROFILE_REQUIRED": "ابتدا اطلاعات تغذیه را کامل کنید.",
    "NUTRITION_PRODUCT_MODE_REQUIRED": "این قابلیت فقط در مسیر تغذیه در دسترس است.",
    "SHARED_PROFILE_REQUIRED": "ابتدا اطلاعات پایه پروفایل را کامل کنید.",
    "STRUCTURED_EXERCISE_REQUIRED": "اطلاعات تمرین برای محاسبه برنامه لازم است.",
    "STRUCTURED_EXERCISE_NOT_FOUND": "اطلاعات تمرین ساختاریافته ثبت نشده است.",
    "NUTRITION_PLAN_NOT_FOUND": "هنوز برنامه غذایی هفتگی ساخته نشده است.",
    "NUTRITION_PLAN_NOT_SELECTED": "ابتدا همین برنامه غذایی را انتخاب کنید.",
    "NUTRITION_PLAN_NOT_READY": "این برنامه غذایی هنوز آماده شروع نیست.",
    "NUTRITION_PLAN_ALREADY_STARTED": "این برنامه غذایی قبلاً با تاریخ دیگری شروع شده است.",
    "NUTRITION_REFERENCE_PLAN_NOT_STARTABLE": "برنامه مقایسه‌ای قابل شروع نیست.",
    "ACTIVE_NUTRITION_PLAN_NOT_FOUND": "هنوز برنامه غذایی تأییدشده و فعالی وجود ندارد.",
    "TARGET_INFEASIBLE": "حداقل‌های علمی در بازه کالری انتخاب‌شده قابل جمع نیستند.",
    "NUTRITION_ESTIMATE_NOT_FOUND": "هنوز برآورد تغذیه‌ای ثبت نشده است.",
    "NUTRITION_ONBOARDING_BLOCKED": "برای حفظ ایمنی، ادامه این مسیر فقط با بررسی پزشک ممکن است.",
    "DIETARY_PATTERN_NOT_SUPPORTED_V1": "الگوی تغذیه‌ای انتخاب‌شده در نسخه فعلی پشتیبانی نمی‌شود.",
    "GOAL_RESELECTION_REQUIRED": "هدف فعلی با شرایط تمرینی ثبت‌شده سازگار نیست.",
    "PLAN_BUNDLE_NOT_FOUND": "بسته برنامه غذایی پیدا نشد.",
    "PLAN_SELECTION_INVALID": "انتخاب برنامه غذایی معتبر نیست.",
    "NUTRITION_INPUT_INVALID": "اطلاعات تغذیه‌ای معتبر نیست.",
    "FOOD_NOT_FOUND": "ماده غذایی پیدا نشد.",
    "FOOD_CATALOGUE_INVALID": "اطلاعات ماده غذایی معتبر نیست.",
    "FOOD_CATALOGUE_PRIMARY_NUTRIENTS_REQUIRED": (
        "برای تأیید ماده غذایی، مواد مغذی اصلی باید کامل باشند."
    ),
    "MEAL_NOT_FOUND": "وعده غذایی پیدا نشد.",
    "MEAL_CATALOGUE_INVALID": "اطلاعات وعده غذایی معتبر نیست.",
    "MEAL_CODE_ALREADY_EXISTS": "این کد وعده قبلاً استفاده شده است.",
    "MEAL_CODE_IMMUTABLE": "کد وعده پس از ایجاد قابل تغییر نیست.",
    "MEAL_FOOD_NOT_FOUND": "یکی از مواد غذایی انتخاب‌شده برای وعده پیدا نشد.",
    "MEAL_FOOD_NOT_VERIFIED": "وعده تأییدشده فقط می‌تواند از مواد غذایی تأییدشده استفاده کند.",
    "PREPARED_RECIPE_INVALID": "دستور تهیه وعده کامل نیست یا داده‌های لازم آن وجود ندارد.",
    "NUTRITION_PROGRAM_MEALS_INVALID": "یکی از وعده‌های انتخاب‌شده برای برنامه پیدا نشد.",
    "NUTRITION_PROGRAM_MEALS_UNVERIFIED": (
        "برنامه فعال فقط می‌تواند از وعده‌های تأییدشده استفاده کند."
    ),
    "NUTRITION_PROGRAM_STRUCTURE_INVALID": (
        "دسته‌بندی وعده‌های برنامه با ساختار انتخاب‌شده سازگار نیست."
    ),
    "NUTRITION_PROGRAM_SAVE_FAILED": "برنامه تغذیه‌ای ذخیره نشد. دوباره تلاش کنید.",
    "MEAL_REFERENCED": "این وعده در برنامه‌های موجود استفاده شده و قابل حذف نیست.",
    "meal_referenced": "این وعده در برنامه‌های موجود استفاده شده و قابل حذف نیست.",
    "PROGRAM_NOT_FOUND": "برنامه تغذیه‌ای پیدا نشد.",
    "NUTRITION_PROGRAM_INVALID": "اطلاعات برنامه تغذیه‌ای معتبر نیست.",
    "NUTRITION_PROGRAM_UNAVAILABLE": "برنامه غذایی فعالی برای این انتخاب وجود ندارد.",
    "FOOD_PRICE_REFRESH_INVALID": "تنظیمات به‌روزرسانی قیمت معتبر نیست.",
    "FOOD_PRICE_RESEARCH_FAILED": "قیمت‌یابی خودکار انجام نشد. دوباره تلاش کنید.",
    "SAFETY_DECISION_NOT_FOUND": "ارزیابی ایمنی هنوز ثبت نشده است.",
    "SAFETY_SCREEN_REQUIRED": "پیش از ادامه، ارزیابی ایمنی را کامل کنید.",
    "NUTRITION_ESTIMATE_BLOCKED": "با اطلاعات فعلی، برآورد تغذیه‌ای قابل انجام نیست.",
    "BODY_PHOTO_INVALID": "این عکس برای تحلیل بدن قابل استفاده نیست.",
    "BODY_PHOTO_SESSION_NOT_FOUND": "نشست عکس بدن پیدا نشد.",
    "BODY_PHOTO_SESSION_STATE_INVALID": "وضعیت این نشست تغییر کرده است. آن را دوباره باز کنید.",
    "BODY_ANALYSIS_NOT_FOUND": "تحلیل بدن پیدا نشد.",
    "BODY_ANALYSIS_NOT_READY": "این نشست هنوز برای تحلیل آماده نیست.",
    "BODY_ANALYSIS_PROVIDER_UNAVAILABLE": "سرویس تحلیل بدن فعلاً در دسترس نیست.",
    "BODY_ANALYSIS_STATE_INVALID": "وضعیت تحلیل بدن اجازه این عملیات را نمی‌دهد.",
    "BODY_PHOTO_SUBMISSION_INCOMPLETE": "سه عکس بدن و رضایت پردازش عملیاتی لازم است.",
    "missing_body_analysis_inputs": "اطلاعات لازم برای تحلیل بدن کامل نیست.",
    "measurement_confirmation_required": "پیش از تحلیل، اندازه‌گیری‌های فعلی را تأیید کنید.",
    "MEASUREMENT_CONFIRMATION_REQUIRED": "تأیید کنید اندازه‌گیری‌های فعلی مربوط به این اسکن هستند.",
    "ACTIVE_PLAN_DAY_NOT_FOUND": "روز برنامه غذایی فعال پیدا نشد.",
    "ACTIVE_PLAN_MEAL_NOT_FOUND": "وعده برنامه غذایی فعال پیدا نشد.",
    "ACTIVE_FREE_MEAL_NOT_FOUND": "وعده آزاد فعال برای این تاریخ پیدا نشد.",
    "CONSUMPTION_ENTRY_NOT_FOUND": "رکورد مصرف غذایی پیدا نشد.",
    "ENTRY_GRAMS_REQUIRED": "مقدار غذا را به گرم وارد کنید.",
    "USE_PLANNED_MEAL_ADJUSTMENT": (
        "برای تغییر این وعده از گزینه تنظیم وعده برنامه‌ریزی‌شده استفاده کنید."
    ),
    "PORTION_RATIO_REQUIRED": "نسبت مصرف وعده را وارد کنید.",
    "INVALID_DATE_RANGE": "بازه تاریخ انتخاب‌شده معتبر نیست.",
    "INVALID_IDEMPOTENCY_KEY": "کلید درخواست معتبر نیست.",
    "INVALID_STORAGE_KEY": "فایل موردنظر قابل دسترسی نیست.",
    "PRIVATE_ACCESS_TOKEN_REQUIRED": "دسترسی خصوصی به فایل معتبر نیست.",
    "RATE_LIMIT_EXCEEDED": "درخواست‌های زیادی ارسال شده است. کمی بعد دوباره تلاش کنید.",
    "THIRD_PARTY_PROCESSING_CONSENT_REQUIRED": (
        "برای تحلیل عکس غذا باید رضایت پردازش را تأیید کنید."
    ),
    "INVALID_FOOD_PHOTO": "عکس غذا معتبر نیست. عکس دیگری انتخاب کنید.",
    "UNRESOLVED_ITEMS_REQUIRE_EDIT": "پیش از ثبت، موارد شناسایی‌شده را اصلاح و تأیید کنید.",
    "FOOD_PHOTO_ESTIMATE_NOT_FOUND": "برآورد عکس غذا پیدا نشد.",
    "FOOD_PHOTO_ITEM_NOT_FOUND": "مورد انتخاب‌شده در برآورد عکس پیدا نشد.",
    "FOOD_PHOTO_ESTIMATION_DISABLED": "تحلیل عکس غذا در حال حاضر فعال نیست.",
    "FOOD_PHOTO_TOO_LARGE": "حجم عکس بیشتر از حد مجاز است. عکس کوچک‌تری انتخاب کنید.",
    "FOOD_PHOTO_STORAGE_UNAVAILABLE": "ذخیره‌سازی عکس غذا فعلاً در دسترس نیست.",
    "FOOD_PRICE_RESEARCH_NOT_CONFIGURED": "سرویس قیمت‌یابی برای این قابلیت پیکربندی نشده است.",
    "COACH_ROLE_REQUIRED": "این عملیات فقط برای مربی در دسترس است.",
    "SPECIALIST_RELATIONSHIP_REQUIRED": "این متخصص به پرونده موردنظر دسترسی ندارد.",
    "REVIEW_ALREADY_COMPLETED": "این بررسی قبلاً تکمیل شده است.",
    "REVIEW_INVALID_STATE": "این بررسی دیگر در وضعیت قابل انجام نیست.",
    "REVIEW_NOT_FOUND": "بررسی برنامه پیدا نشد.",
    "REVIEW_NOT_CLAIMED": "ابتدا باید بررسی را به نام خود ثبت کنید.",
    "REVIEW_ALREADY_CLAIMED": "این بررسی در اختیار مربی دیگری است.",
    "REVIEW_LEASE_EXPIRED": "مهلت بررسی تمام شده است. بررسی را دوباره دریافت کنید.",
    "STALE_DRAFT_REVISION": "نسخه پیش‌نویس تغییر کرده است. اطلاعات را دوباره دریافت کنید.",
    "INVALID_DRAFT": "پیش‌نویس برنامه با محدودیت‌های فعلی سازگار نیست.",
    "EXERCISE_NOT_ALLOWED": "یکی از حرکات انتخاب‌شده برای این برنامه مجاز نیست.",
    "REVIEW_ALREADY_APPROVED": "این بررسی قبلاً تأیید شده است.",
    "REVIEW_ALREADY_REJECTED": "این بررسی قبلاً رد شده است.",
    "REVIEW_EXPLANATION_REQUIRED": "برای رد برنامه، توضیح مربی لازم است.",
    "REVIEW_SUPERSEDED": "این بررسی با نسخه جدید برنامه جایگزین شده است.",
    "PLAN_STRUCTURE_CHANGED": "ساختار روزها و حرکت‌های برنامه نباید تغییر کند.",
    "PRESCRIPTION_MODE_MISMATCH": "نوع تجویز با اطلاعات حرکت انتخاب‌شده سازگار نیست.",
    "PLAN_GENERATION_NOT_FOUND": "داده ساخت برنامه پیدا نشد.",
    "NUTRITION_REVIEW_NOT_CREATED": "بررسی برنامه غذایی ایجاد نشد.",
    "REVIEW_ASSIGNED_TO_ANOTHER_PHYSICIAN": "این پرونده به پزشک دیگری اختصاص داده شده است.",
    "REVIEW_NOT_IN_PROGRESS": "بررسی در وضعیت قابل انجام نیست.",
    "REVIEW_ALREADY_ASSIGNED": "این بررسی قبلاً به پزشک دیگری اختصاص داده شده است.",
    "REVIEW_NOTES_REQUIRED": "برای این اقدام، یادداشت بررسی لازم است.",
    "INVALID_REVIEW_ACTION": "اقدام بررسی معتبر نیست.",
    "INVALID_REVIEW_TRANSITION": "تغییر وضعیت بررسی معتبر نیست.",
    "PLAN_HARD_INVARIANTS_FAILED": "برنامه با محدودیت‌های ایمنی سازگار نیست.",
    "INVALID_DAY_SELECTION": "انتخاب روزهای برنامه معتبر نیست.",
    "IDEAL_REFERENCE_PLAN_CANNOT_BE_EDITED": "برنامه مقایسه‌ای قابل ویرایش نیست.",
    "ACTIVE_PLAN_REQUIRED": "برای این عملیات باید یک برنامه غذایی فعال داشته باشید.",
    "LAB_DOCUMENT_NOT_FOUND": "سند آزمایش پیدا نشد.",
    "LAB_DOCUMENT_TOO_LARGE": "حجم سند آزمایش بیشتر از حد مجاز است.",
    "INVALID_LAB_DOCUMENT": "سند آزمایش معتبر نیست.",
    "INVALID_LAB_STORAGE_KEY": "سند آزمایش قابل دسترسی نیست.",
    "LAB_STORAGE_UNAVAILABLE": "ذخیره‌سازی اسناد آزمایش فعلاً در دسترس نیست.",
    "LAB_REQUEST_NOT_FOUND": "درخواست آزمایش پیدا نشد.",
    "MEDICAL_CONTEXT_NOT_FOUND": "اطلاعات پزشکی لازم برای بررسی پیدا نشد.",
    "INVALID_LAB_REQUEST_TRANSITION": "تغییر وضعیت درخواست آزمایش معتبر نیست.",
    "PHYSICIAN_ROLE_REQUIRED": "این عملیات فقط برای پزشک در دسترس است.",
    "INVALID_SUPPLEMENT_COMPOSITION": "ترکیب مکمل معتبر نیست.",
    "SUPPLEMENT_SAFETY_HARD_BLOCK": "این مکمل با شرایط ایمنی فعلی قابل تجویز نیست.",
    "SUPPLEMENT_UPPER_LIMIT_HARD_BLOCK": "مقدار مکمل از حد ایمن مجاز بیشتر است.",
    "VERIFIED_SUPPLEMENT_OR_PLAN_NOT_FOUND": "مکمل یا برنامه تأییدشده پیدا نشد.",
    "ASSIGNED_REVIEW_REQUIRED": "ابتدا بررسی برنامه را به نام خود ثبت کنید.",
    "SUPPLEMENT_ORDER_NOT_FOUND": "سفارش مکمل پیدا نشد.",
    "INVALID_SUPPLEMENT_ORDER_TRANSITION": "تغییر وضعیت سفارش مکمل معتبر نیست.",
    "ENTITLEMENT_REQUIRED": "برای استفاده از این قابلیت، دسترسی لازم را فعال کنید.",
    "ENTITLEMENT_QUOTA_EXCEEDED": "سهم استفاده از این قابلیت تمام شده است.",
    "ACCESS_TERM_TOO_SHORT": "مدت انتخاب‌شده بیشتر از سقف دسترسی مجاز است.",
    "NOTIFICATION_PROVIDER_MISMATCH": "ارائه‌دهنده اعلان با پلتفرم دستگاه سازگار نیست.",
    "NOTIFICATION_DEVICE_NOT_FOUND": "دستگاه اعلان پیدا نشد.",
    "TRAINING_STRUCTURE_NOT_FOUND": "ساختار تمرینی پیدا نشد.",
    "TRAINING_STRUCTURE_INVALID": "اطلاعات ساختار تمرینی معتبر نیست.",
    "TRAINING_STRUCTURE_REFERENCED": (
        "این ساختار به قالب‌های تمرینی متصل است و قابل تغییر یا حذف نیست."
    ),
    "TRAINING_TEMPLATE_NOT_FOUND": "قالب برنامه تمرینی پیدا نشد.",
    "TRAINING_TEMPLATE_INVALID": "اطلاعات قالب برنامه تمرینی معتبر نیست.",
    "TRAINING_TEMPLATE_SAVE_FAILED": "ذخیره قالب برنامه تمرینی انجام نشد. دوباره تلاش کنید.",
    "TRAINING_TEMPLATE_SLOT_NOT_FOUND": "جایگاه قالب برنامه تمرینی پیدا نشد.",
    "EXERCISE_NOT_FOUND": "حرکت پیدا نشد.",
    "WORKOUT_ACTIVE_CYCLE_NOT_FOUND": "چرخه تمرینی فعالی وجود ندارد.",
    "WORKOUT_CYCLE_NOT_FOUND": "چرخه تمرینی پیدا نشد.",
    "WORKOUT_CYCLE_NOT_COMPLETE": "چرخه تمرینی هنوز به پایان نرسیده است.",
    "WORKOUT_SESSION_NOT_FOUND": "جلسه تمرینی پیدا نشد.",
    "WORKOUT_SESSION_ALREADY_FINISHED": "این جلسه تمرینی قبلاً پایان یافته است.",
    "WORKOUT_SESSION_NOT_ACTIONABLE": "این جلسه تمرینی در وضعیت قابل انجام نیست.",
    "WORKOUT_CYCLE_EXERCISE_NOT_FOUND": "حرکت در چرخه تمرینی پیدا نشد.",
    "WORKOUT_CYCLE_INPUT_INVALID": "اطلاعات چرخه تمرینی معتبر نیست.",
    "WORKOUT_CYCLE_ALREADY_STARTED": "این برنامه قبلاً با تاریخ دیگری شروع شده است.",
    "WORKOUT_CYCLE_FEEDBACK_NOT_FOUND": "بازخورد چرخه تمرینی پیدا نشد.",
    "WORKOUT_WEEKLY_CHECKIN_NOT_FOUND": "چک‌این هفتگی این هفته پیدا نشد.",
    "WORKOUT_SESSION_DATE_CONFLICT": "جلسه دیگری برای این تاریخ برنامه‌ریزی شده است.",
    "WORKOUT_CHECKIN_INVALID": "اطلاعات چک‌این معتبر نیست.",
    "WORKOUT_REPLACEMENT_NOT_ALLOWED": "این جایگزینی برای برنامه فعلی مجاز نیست.",
    "WORKOUT_PLAN_DELETE_FAILED": "حذف این نسخه از برنامه مجاز نیست.",
    "TIMEZONE_INVALID": "منطقه زمانی معتبر نیست.",
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
    "apple authentication is only available on ios": "AUTH_APPLE_PLATFORM_UNSUPPORTED",
    "authentication required": "AUTHENTICATION_REQUIRED",
    "email is already registered": "AUTH_EMAIL_ALREADY_REGISTERED",
    "google authentication failed": "AUTH_GOOGLE_FAILED",
    "unable to use this google account": "AUTH_GOOGLE_ACCOUNT_CONFLICT",
    "unable to use this apple account": "AUTH_APPLE_ACCOUNT_CONFLICT",
    "invalid email or password": "AUTH_INVALID_CREDENTIALS",
    "invalid or expired otp": "AUTH_OTP_INVALID_OR_EXPIRED",
    "invalid or expired refresh token": "AUTH_SESSION_EXPIRED",
    "invalid or expired reset token": "AUTH_PASSWORD_RESET_INVALID",
    "invalid or expired verification token": "AUTH_EMAIL_VERIFICATION_INVALID",
    "body analysis is temporarily unavailable": "BODY_ANALYSIS_PROVIDER_UNAVAILABLE",
    "too many authentication requests": "AUTH_RATE_LIMITED",
    "account deletion is temporarily unavailable": "ACCOUNT_DELETION_NOT_ENABLED",
    "administrator access required": "ADMIN_ROLE_REQUIRED",
    "authentication is required": "AUTHENTICATION_REQUIRED",
    "bearer authentication required": "BEARER_AUTHENTICATION_REQUIRED",
    "body photo session is not ready for analysis": "BODY_ANALYSIS_NOT_READY",
    "body analysis not found": "BODY_ANALYSIS_NOT_FOUND",
    "body photo session not found": "BODY_PHOTO_SESSION_NOT_FOUND",
    "body photo session cannot be changed": "BODY_PHOTO_SESSION_STATE_INVALID",
    "body photo session cannot be submitted": "BODY_PHOTO_SESSION_STATE_INVALID",
    "completed fitness profile required": "PROFILE_INCOMPLETE",
    "exercise slug already exists": "EXERCISE_SLUG_ALREADY_EXISTS",
    "fitness profile already exists": "PROFILE_ALREADY_EXISTS",
    "fitness profile not found": "PROFILE_NOT_FOUND",
    "home training setup is required for home training": "HOME_TRAINING_SETUP_REQUIRED",
    "no active workout cycle": "WORKOUT_ACTIVE_CYCLE_NOT_FOUND",
    "no active workout plan": "WORKOUT_ACTIVE_PLAN_NOT_FOUND",
    "notification device not found": "NOTIFICATION_DEVICE_NOT_FOUND",
    "notification provider does not match the device platform": "NOTIFICATION_PROVIDER_MISMATCH",
    "preferred weekdays cannot exceed training days per week": "PREFERRED_WEEKDAYS_INVALID",
    "profile photo access is not allowed": "PROFILE_PHOTO_ACCESS_DENIED",
    "profile photo not found": "PROFILE_PHOTO_NOT_FOUND",
    "service temporarily unavailable": "SERVICE_UNAVAILABLE",
    "structure not found": "TRAINING_STRUCTURE_NOT_FOUND",
    "three body photos and operational consent are required": "BODY_PHOTO_SUBMISSION_INCOMPLETE",
    "workout cycle has not reached its end": "WORKOUT_CYCLE_NOT_COMPLETE",
    "workout cycle not found": "WORKOUT_CYCLE_NOT_FOUND",
    "workout cycle session is already finished": "WORKOUT_SESSION_ALREADY_FINISHED",
    "workout cycle session is not actionable": "WORKOUT_SESSION_NOT_ACTIONABLE",
    "workout cycle session not found": "WORKOUT_SESSION_NOT_FOUND",
    "workout plan exercise not found in current cycle": "WORKOUT_CYCLE_EXERCISE_NOT_FOUND",
    "workout plan generation is already in progress": "WORKOUT_GENERATION_IN_PROGRESS",
    "workout plan generation is cooling down": "WORKOUT_GENERATION_COOLDOWN",
    "workout plan is not executable": "WORKOUT_PLAN_NOT_EXECUTABLE",
    "workout plan not found": "WORKOUT_PLAN_NOT_FOUND",
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
