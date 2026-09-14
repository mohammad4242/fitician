import type { ErrorCatalogEntry, LocalizedErrorCopy } from "./types";

const text = (fa: string, en: string): LocalizedErrorCopy => ({ fa, en });
const entry = (
  title: LocalizedErrorCopy,
  message: LocalizedErrorCopy,
  action?: LocalizedErrorCopy,
  audiences?: ErrorCatalogEntry["audiences"],
): ErrorCatalogEntry => ({
  title,
  message,
  ...(action === undefined ? {} : { action }),
  ...(audiences === undefined ? {} : { audiences }),
});

export const ERROR_CATALOG: Readonly<Record<string, ErrorCatalogEntry>> = {
  AUTH_INVALID_CREDENTIALS: entry(
    text("ورود انجام نشد", "Sign-in failed"),
    text("ایمیل یا رمز عبور درست نیست.", "The email or password is incorrect."),
  ),
  AUTH_OTP_INVALID_OR_EXPIRED: entry(
    text("کد ورود معتبر نیست", "Invalid sign-in code"),
    text("کد ورود معتبر نیست یا منقضی شده است.", "The code is invalid or has expired."),
  ),
  AUTH_EMAIL_ALREADY_REGISTERED: entry(
    text("حساب موجود است", "Account already exists"),
    text("این ایمیل قبلاً ثبت شده است.", "An account already exists for this email."),
  ),
  AUTH_SESSION_EXPIRED: entry(
    text("نشست منقضی شده است", "Session expired"),
    text("نشست شما منقضی شده است. دوباره وارد شوید.", "Your session has expired. Sign in again."),
  ),
  AUTH_RATE_LIMITED: entry(
    text("درخواست‌های زیاد", "Too many requests"),
    text("درخواست‌های ورود زیاد است. کمی بعد دوباره تلاش کنید.", "Too many sign-in requests. Try again later."),
  ),
  AUTH_GOOGLE_FAILED: entry(
    text("ورود با گوگل انجام نشد", "Google sign-in failed"),
    text("ورود با گوگل انجام نشد. دوباره تلاش کنید.", "Google sign-in could not be completed. Try again."),
  ),
  AUTH_APPLE_FAILED: entry(
    text("ورود با اپل انجام نشد", "Apple sign-in failed"),
    text("ورود با اپل انجام نشد. دوباره تلاش کنید.", "Apple sign-in could not be completed. Try again."),
  ),
  AUTH_GOOGLE_ACCOUNT_CONFLICT: entry(
    text("ورود با گوگل انجام نشد", "Google sign-in conflict"),
    text("این حساب گوگل به حساب دیگری متصل است.", "This Google account is linked to another account."),
  ),
  AUTH_APPLE_ACCOUNT_CONFLICT: entry(
    text("ورود با اپل انجام نشد", "Apple sign-in conflict"),
    text("این حساب اپل به حساب دیگری متصل است.", "This Apple account is linked to another account."),
  ),
  AUTHENTICATION_REQUIRED: entry(
    text("ورود لازم است", "Sign-in required"),
    text("برای ادامه دوباره وارد حساب شوید.", "Sign in again to continue."),
  ),
  BEARER_AUTHENTICATION_REQUIRED: entry(
    text("ورود لازم است", "Sign-in required"),
    text("برای ادامه باید وارد حساب شوید.", "You must be signed in to continue."),
  ),
  TRUSTED_ORIGIN_REQUIRED: entry(
    text("درخواست امن نیست", "Untrusted request"),
    text("ارسال امن درخواست انجام نشد. دوباره تلاش کنید.", "The request did not come from a trusted origin."),
  ),
  PROFILE_INCOMPLETE: entry(
    text("پروفایل کامل نیست", "Profile incomplete"),
    text("برای ادامه، اطلاعات پروفایل را کامل کنید.", "Complete your profile to continue."),
  ),
  PROFILE_WEIGHT_REQUIRED: entry(
    text("وزن پروفایل لازم است", "Weight is required"),
    text(
      "برنامه تمرینی ساخته نشد چون وزن شما در پروفایل ثبت نشده است. ابتدا وزن را در پروفایل تکمیل کنید.",
      "The workout plan could not be created because your profile weight is missing. Add your weight first.",
    ),
  ),
  PROFILE_HEIGHT_REQUIRED: entry(
    text("قد پروفایل لازم است", "Height is required"),
    text("برای ادامه، قد خود را در پروفایل ثبت کنید.", "Add your height to your profile to continue."),
  ),
  AGE_NOT_SUPPORTED: entry(
    text("سن پشتیبانی نمی‌شود", "Age not supported"),
    text("فیتیشن در حال حاضر برای افراد ۱۸ سال و بالاتر ارائه می‌شود.", "Fitician is currently available for people aged 18 and above."),
  ),
  AGE_OUT_OF_RANGE: entry(
    text("تاریخ تولد معتبر نیست", "Date of birth not supported"),
    text("تاریخ تولد واردشده پشتیبانی نمی‌شود.", "The entered date of birth is not supported."),
  ),
  PROFILE_NOT_FOUND: entry(
    text("پروفایل پیدا نشد", "Profile not found"),
    text("پروفایل فیتنس پیدا نشد.", "The fitness profile was not found."),
  ),
  PROFILE_ALREADY_EXISTS: entry(
    text("پروفایل قبلاً ساخته شده است", "Profile already exists"),
    text("پروفایل فیتنس قبلاً ساخته شده است.", "The fitness profile already exists."),
  ),
  PRODUCT_MODE_REQUIRED: entry(
    text("مسیر محصول انتخاب نشده است", "Product path required"),
    text("ابتدا مسیر فیتیشن را انتخاب کنید.", "Choose a Fitician path first."),
  ),
  HOME_TRAINING_SETUP_REQUIRED: entry(
    text("تجهیزات تمرین خانگی لازم است", "Home setup required"),
    text("برای تمرین خانگی، تجهیزات و setup تمرین را مشخص کنید.", "Choose a home-training setup first."),
  ),
  PREFERRED_WEEKDAYS_INVALID: entry(
    text("روزهای تمرین معتبر نیستند", "Training days are invalid"),
    text("تعداد روزهای انتخابی باید با تعداد روزهای تمرین برابر باشد.", "Selected weekdays must match your training days."),
  ),
  WORKOUT_GENERATION_IN_PROGRESS: entry(
    text("ساخت برنامه در حال انجام است", "Workout generation in progress"),
    text("ساخت برنامه تمرینی در حال انجام است. پس از پایان دوباره بررسی کنید.", "Your workout plan is still being generated. Check again when it finishes."),
  ),
  WORKOUT_GENERATION_COOLDOWN: entry(
    text("کمی صبر کنید", "Please wait"),
    text("ساخت برنامه تازه انجام شده است. کمی بعد دوباره تلاش کنید.", "A workout plan was generated recently. Try again later."),
  ),
  WORKOUT_GENERATION_UNSUPPORTED: entry(
    text("ساخت برنامه ممکن نیست", "Workout generation is not available"),
    text("با اطلاعات فعلی، ساخت برنامه ایمن ممکن نیست. اطلاعات تمرینی و تجهیزات را بررسی کنید.", "A safe workout plan cannot be generated with the current inputs. Check your training details and equipment."),
  ),
  WORKOUT_PLAN_NOT_FOUND: entry(
    text("برنامه تمرینی پیدا نشد", "Workout plan not found"),
    text("برنامه تمرینی پیدا نشد.", "The workout plan was not found."),
  ),
  WORKOUT_ACTIVE_PLAN_NOT_FOUND: entry(
    text("برنامه فعال پیدا نشد", "Active workout plan not found"),
    text("برنامه تمرینی فعالی وجود ندارد.", "There is no active workout plan."),
  ),
  WORKOUT_PLAN_NOT_EXECUTABLE: entry(
    text("برنامه قابل اجرا نیست", "Workout plan is not executable"),
    text("این نسخه از برنامه در وضعیت قابل اجرا نیست.", "This workout plan version is not executable."),
  ),
  NUTRITION_PROFILE_INCOMPLETE: entry(
    text("پروفایل تغذیه کامل نیست", "Nutrition profile incomplete"),
    text("برای ادامه، اطلاعات تغذیه را در پروفایل کامل کنید.", "Complete your nutrition profile to continue."),
  ),
  NUTRITION_PROFILE_NOT_FOUND: entry(
    text("پروفایل تغذیه پیدا نشد", "Nutrition profile not found"),
    text("پروفایل تغذیه ثبت نشده است.", "The nutrition profile was not found."),
  ),
  NUTRITION_PLAN_NOT_FOUND: entry(
    text("برنامه غذایی پیدا نشد", "Nutrition plan not found"),
    text("هنوز برنامه غذایی هفتگی ساخته نشده است.", "A weekly nutrition plan has not been created yet."),
  ),
  ACTIVE_NUTRITION_PLAN_NOT_FOUND: entry(
    text("برنامه غذایی فعال پیدا نشد", "Active nutrition plan not found"),
    text("هنوز برنامه غذایی تأییدشده و فعالی وجود ندارد.", "There is no approved active nutrition plan yet."),
  ),
  SAFETY_DECISION_NOT_FOUND: entry(
    text("ارزیابی ایمنی ثبت نشده است", "Safety assessment is missing"),
    text("ارزیابی ایمنی هنوز ثبت نشده است. ابتدا ارزیابی ایمنی را کامل کنید.", "The safety assessment has not been recorded yet. Complete it first."),
    undefined,
    {
      physician: {
        message: text(
          "بررسی این برنامه ممکن نیست چون ارزیابی ایمنی کاربر هنوز ثبت نشده است.",
          "This plan cannot be reviewed because the member's safety assessment has not been recorded.",
        ),
      },
    },
  ),
  SAFETY_SCREEN_REQUIRED: entry(
    text("ارزیابی ایمنی لازم است", "Safety assessment required"),
    text("پیش از ادامه، ارزیابی ایمنی را کامل کنید.", "Complete the safety assessment before continuing."),
  ),
  NUTRITION_ESTIMATE_BLOCKED: entry(
    text("برآورد تغذیه‌ای ممکن نیست", "Nutrition estimate unavailable"),
    text("با اطلاعات فعلی، برآورد تغذیه‌ای قابل انجام نیست.", "A nutrition estimate cannot be created from the current information."),
  ),
  BODY_PHOTO_INVALID: entry(
    text("عکس بدن معتبر نیست", "Invalid body photo"),
    text("این عکس برای تحلیل بدن قابل استفاده نیست. عکس دیگری انتخاب کنید.", "This photo cannot be used for body analysis. Choose another photo."),
  ),
  BODY_PHOTO_SESSION_NOT_FOUND: entry(
    text("نشست عکس پیدا نشد", "Photo session not found"),
    text("نشست عکس بدن پیدا نشد.", "The body-photo session was not found."),
  ),
  BODY_PHOTO_SESSION_STATE_INVALID: entry(
    text("وضعیت نشست معتبر نیست", "Photo session state changed"),
    text("وضعیت این نشست تغییر کرده است. آن را دوباره باز کنید.", "This photo session changed state. Open it again."),
  ),
  BODY_ANALYSIS_NOT_FOUND: entry(
    text("تحلیل بدن پیدا نشد", "Body analysis not found"),
    text("تحلیل بدن پیدا نشد.", "The body analysis was not found."),
  ),
  BODY_ANALYSIS_NOT_READY: entry(
    text("تحلیل هنوز آماده نیست", "Body analysis is not ready"),
    text("این نشست هنوز برای تحلیل آماده نیست. عکس‌ها و اطلاعات لازم را تکمیل کنید.", "This session is not ready for analysis. Complete the required photos and information."),
  ),
  BODY_ANALYSIS_PROVIDER_UNAVAILABLE: entry(
    text("تحلیل بدن موقتاً در دسترس نیست", "Body Analysis provider unavailable"),
    text("تحلیل بدن فعلاً در دسترس نیست. بعداً دوباره تلاش کنید.", "Body analysis is temporarily unavailable. Try again later."),
    text("دوباره تلاش کنید", "Try again"),
    {
      admin: {
        message: text(
          "سرویس ارائه‌دهنده تحلیل بدن در دسترس نیست.",
          "The Body Analysis provider is unavailable.",
        ),
      },
    },
  ),
  MEASUREMENT_CONFIRMATION_REQUIRED: entry(
    text("تأیید اندازه‌گیری لازم است", "Measurement confirmation required"),
    text("تأیید کنید اندازه‌گیری‌های فعلی مربوط به این اسکن هستند.", "Confirm that the current measurements represent this scan."),
  ),
  COACH_ROLE_REQUIRED: entry(
    text("دسترسی مربی لازم است", "Coach access required"),
    text("این عملیات فقط برای مربی در دسترس است.", "This operation is available only to a coach."),
  ),
  PHYSICIAN_ROLE_REQUIRED: entry(
    text("دسترسی پزشک لازم است", "Physician access required"),
    text("این عملیات فقط برای پزشک در دسترس است.", "This operation is available only to a physician."),
  ),
  SPECIALIST_RELATIONSHIP_REQUIRED: entry(
    text("دسترسی به پرونده وجود ندارد", "Specialist relationship required"),
    text("این متخصص به پرونده موردنظر دسترسی ندارد.", "This specialist does not have access to the requested case."),
  ),
  REVIEW_ALREADY_COMPLETED: entry(
    text("بررسی قبلاً تکمیل شده است", "Review already completed"),
    text("این بررسی قبلاً تکمیل شده است.", "This review has already been completed."),
  ),
  REVIEW_INVALID_STATE: entry(
    text("وضعیت بررسی تغییر کرده است", "Review state changed"),
    text("این بررسی دیگر در وضعیت قابل انجام نیست. پرونده را دوباره بازخوانی کنید.", "This review is no longer in an actionable state. Reload the case."),
  ),
  ENTITLEMENT_REQUIRED: entry(
    text("دسترسی لازم فعال نیست", "Access is required"),
    text("برای استفاده از این قابلیت، دسترسی لازم را فعال کنید.", "Activate the required access to use this feature."),
    text("مشاهده بسته‌ها", "View packages"),
  ),
  ENTITLEMENT_QUOTA_EXCEEDED: entry(
    text("سهم استفاده تمام شده است", "Usage quota reached"),
    text("سهم استفاده از این قابلیت تمام شده است. پس از بازنشانی سهم دوباره تلاش کنید.", "Your usage quota is exhausted. Try again after it resets."),
  ),
  ACCESS_TERM_TOO_SHORT: entry(
    text("مدت دسترسی معتبر نیست", "Access term is invalid"),
    text("مدت انتخاب‌شده بیشتر از سقف دسترسی مجاز است.", "The selected access term exceeds the allowed maximum."),
  ),
  VALIDATION_ERROR: entry(
    text("اطلاعات معتبر نیست", "Invalid information"),
    text("اطلاعات واردشده را بررسی و موارد مشخص‌شده را اصلاح کنید.", "Check the entered information and correct the highlighted fields."),
  ),
  OFFLINE: entry(
    text("اتصال اینترنت در دسترس نیست", "You are offline"),
    text("اتصال اینترنت در دسترس نیست. پس از اتصال دوباره تلاش کنید.", "The internet connection is unavailable. Try again when you are connected."),
  ),
  NETWORK_ERROR: entry(
    text("ارتباط با سرویس برقرار نشد", "Network request failed"),
    text("ارتباط با سرویس برقرار نشد. دوباره تلاش کنید.", "The service could not be reached. Try again."),
  ),
  REQUEST_TIMEOUT: entry(
    text("پاسخ سرویس طول کشید", "Request timed out"),
    text("پاسخ سرویس بیش از حد طول کشید. دوباره تلاش کنید.", "The service took too long to respond. Try again."),
  ),
  REQUEST_ABORTED: entry(
    text("درخواست لغو شد", "Request cancelled"),
    text("درخواست لغو شد.", "The request was cancelled."),
  ),
  INTERNAL_SERVER_ERROR: entry(
    text("خطای غیرمنتظره", "Unexpected error"),
    text("انجام این عملیات با خطای غیرمنتظره روبه‌رو شد. دوباره تلاش کنید.", "The operation encountered an unexpected error. Try again."),
  ),
  BAD_REQUEST: entry(
    text("درخواست معتبر نیست", "Invalid request"),
    text("درخواست معتبر نیست. اطلاعات را بررسی کنید.", "The request is invalid. Check the information and try again."),
  ),
  UNAUTHORIZED: entry(
    text("ورود لازم است", "Sign-in required"),
    text("نشست شما منقضی شده است. دوباره وارد حساب شوید.", "Your session has expired. Sign in again."),
  ),
  FORBIDDEN: entry(
    text("دسترسی وجود ندارد", "Access denied"),
    text("برای این عملیات دسترسی لازم وجود ندارد.", "You do not have access to this operation."),
  ),
  NOT_FOUND: entry(
    text("پیدا نشد", "Not found"),
    text("مورد درخواست‌شده پیدا نشد.", "The requested item was not found."),
  ),
  CONFLICT: entry(
    text("وضعیت تغییر کرده است", "State conflict"),
    text("این عملیات با وضعیت فعلی سازگار نیست. دوباره اطلاعات را دریافت کنید.", "This operation is not valid for the current state. Reload and try again."),
  ),
  RATE_LIMITED: entry(
    text("درخواست‌های زیادی ارسال شده است", "Too many requests"),
    text("درخواست‌های زیادی ارسال شده است. کمی بعد دوباره تلاش کنید.", "Too many requests were sent. Try again later."),
  ),
  BAD_GATEWAY: entry(
    text("سرویس پاسخ مناسبی نداد", "Service response unavailable"),
    text("سرویس نتوانست درخواست را کامل کند. دوباره تلاش کنید.", "The service could not complete the request. Try again."),
  ),
  SERVICE_UNAVAILABLE: entry(
    text("سرویس موقتاً در دسترس نیست", "Service temporarily unavailable"),
    text("سرویس موقتاً در دسترس نیست. کمی بعد دوباره تلاش کنید.", "The service is temporarily unavailable. Try again later."),
  ),
};

export const ERROR_FIELD_LABELS: Readonly<Record<string, LocalizedErrorCopy>> = {
  weight_kg: text("وزن", "Weight"),
  current_weight_kg: text("وزن", "Weight"),
  height_cm: text("قد", "Height"),
  date_of_birth: text("تاریخ تولد", "Date of birth"),
  birth_date: text("تاریخ تولد", "Date of birth"),
  training_days: text("تعداد روزهای تمرین", "Training days"),
  training_days_per_week: text("تعداد روزهای تمرین", "Training days"),
  session_duration_minutes: text("زمان جلسه تمرین", "Session duration"),
  plan_duration_weeks: text("مدت برنامه", "Plan duration"),
  preferred_weekdays: text("روزهای انتخابی تمرین", "Preferred weekdays"),
  email: text("ایمیل", "Email"),
  password: text("رمز عبور", "Password"),
};

export const RUNTIME_ERROR_CATALOG = ERROR_CATALOG;
