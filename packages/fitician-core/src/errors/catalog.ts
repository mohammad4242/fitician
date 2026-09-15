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
  AUTH_APPLE_PLATFORM_UNSUPPORTED: entry(
    text("ورود با اپل در دسترس نیست", "Apple sign-in is unavailable"),
    text("ورود با اپل فقط در iOS در دسترس است.", "Apple sign-in is available only on iOS."),
  ),
  AUTH_PASSWORD_RESET_INVALID: entry(
    text("لینک بازنشانی معتبر نیست", "Password reset link is invalid"),
    text("لینک بازنشانی رمز عبور معتبر نیست یا منقضی شده است.", "The password reset link is invalid or has expired."),
  ),
  AUTH_EMAIL_VERIFICATION_INVALID: entry(
    text("لینک تأیید معتبر نیست", "Verification link is invalid"),
    text("لینک تأیید ایمیل معتبر نیست یا منقضی شده است.", "The email verification link is invalid or has expired."),
  ),
  RECENT_AUTHENTICATION_REQUIRED: entry(
    text("تأیید دوباره هویت لازم است", "Recent sign-in required"),
    text("برای ادامه، دوباره وارد حساب شوید.", "Sign in again to continue."),
  ),
  INVALID_REAUTHENTICATION: entry(
    text("تأیید هویت انجام نشد", "Reauthentication failed"),
    text("رمز عبور درست نیست.", "The password is not correct."),
  ),
  auth_in_progress: entry(
    text("احراز هویت قبلی هنوز فعال است", "Authentication is already in progress"),
    text("برای این Agent یک فرایند احراز هویت دیگر در حال انجام است.", "Authentication is already in progress for this Agent."),
  ),
  auth_session_not_found: entry(
    text("نشست احراز هویت پیدا نشد", "Authentication session not found"),
    text("نشست احراز هویت پیدا نشد. دوباره شروع کنید.", "The authentication session was not found. Start again."),
  ),
  auth_session_expired: entry(
    text("نشست احراز هویت منقضی شده است", "Authentication session expired"),
    text("نشست احراز هویت منقضی شده است. دوباره شروع کنید.", "The authentication session has expired. Start again."),
  ),
  auth_input_not_expected: entry(
    text("ورودی احراز هویت در این مرحله لازم نیست", "Authentication input is not expected"),
    text("در این مرحله ورودی احراز هویت پذیرفته نمی‌شود.", "Authentication input is not expected at this stage."),
  ),
  auth_input_invalid: entry(
    text("ورودی احراز هویت معتبر نیست", "Authentication input is invalid"),
    text("کد احراز هویت معتبر نیست. آن را بررسی و دوباره وارد کنید.", "The authentication input is invalid. Check it and try again."),
  ),
  auth_unavailable: entry(
    text("احراز هویت موقتاً در دسترس نیست", "Authentication is unavailable"),
    text("احراز هویت فعلاً در دسترس نیست. بعداً دوباره تلاش کنید.", "Authentication is temporarily unavailable. Try again later."),
  ),
  auth_manual_only: entry(
    text("احراز هویت دستی لازم است", "Manual authentication is required"),
    text("این Agent فقط با احراز هویت دستی قابل اتصال است.", "This Agent requires manual authentication."),
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
  SHARED_PROFILE_NOT_FOUND: entry(
    text("اطلاعات پایه پیدا نشد", "Shared profile not found"),
    text("اطلاعات پایه پروفایل ثبت نشده است.", "The shared profile information has not been recorded."),
  ),
  UNSUPPORTED_RESISTANCE_TRAINING_DAYS: entry(
    text("تعداد روزهای تمرین پشتیبانی نمی‌شود", "Training-day count is not supported"),
    text("تعداد روزهای تمرین با سطح فعلی سازگار نیست.", "This training-day count is not supported for the current experience level."),
  ),
  PROFILE_PHOTO_ACCESS_DENIED: entry(
    text("دسترسی به عکس وجود ندارد", "Profile photo access denied"),
    text("دسترسی به عکس پروفایل وجود ندارد.", "You do not have access to this profile photo."),
  ),
  PROFILE_PHOTO_NOT_FOUND: entry(
    text("عکس پروفایل پیدا نشد", "Profile photo not found"),
    text("عکس پروفایل پیدا نشد.", "The profile photo was not found."),
  ),
  invalid_file_size: entry(
    text("حجم عکس مجاز نیست", "Image size is not allowed"),
    text("حجم عکس بیشتر از حد مجاز است. عکس کوچک‌تری انتخاب کنید.", "The image is larger than the allowed limit. Choose a smaller image."),
  ),
  invalid_geometry: entry(
    text("اندازه عکس معتبر نیست", "Image dimensions are invalid"),
    text("عکس باید مربعی و در اندازه مجاز باشد.", "The image must be square and within the allowed dimensions."),
  ),
  unsupported_format: entry(
    text("فرمت عکس پشتیبانی نمی‌شود", "Image format is not supported"),
    text("فرمت این عکس پشتیبانی نمی‌شود.", "This image format is not supported."),
  ),
  invalid_image: entry(
    text("عکس معتبر نیست", "Image is invalid"),
    text("فایل عکس معتبر نیست. عکس دیگری انتخاب کنید.", "The image file is invalid. Choose another image."),
  ),
  image_too_large: entry(
    text("عکس خیلی بزرگ است", "Image is too large"),
    text("ابعاد عکس بیشتر از حد مجاز است. عکس کوچک‌تری انتخاب کنید.", "The image dimensions exceed the allowed limit. Choose a smaller image."),
  ),
  EXERCISE_SLUG_ALREADY_EXISTS: entry(
    text("شناسه حرکت تکراری است", "Exercise slug already exists"),
    text("این شناسه قبلاً استفاده شده است.", "This exercise slug is already in use."),
  ),
  EXERCISE_NOT_FOUND: entry(
    text("حرکت پیدا نشد", "Exercise not found"),
    text("حرکت موردنظر پیدا نشد.", "The requested exercise was not found."),
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
  WORKOUT_GENERATION_FAILED: entry(
    text("ساخت برنامه ناموفق بود", "Workout generation failed"),
    text("ساخت برنامه تمرینی کامل نشد. دوباره تلاش کنید.", "The workout plan could not be generated. Try again."),
  ),
  BODYWEIGHT_ONLY_LEVEL_NOT_SUPPORTED: entry(
    text("سطح تمرین پشتیبانی نمی‌شود", "Workout level is not supported"),
    text(
      "برنامه تمرین فقط با وزن بدن در حال حاضر برای سطح ماه اول و مبتدی ارائه می‌شود.",
      "Bodyweight-only workout plans are currently available for First Month and Beginner levels.",
    ),
  ),
  BODYWEIGHT_TEMPLATE_DAYS_NOT_SUPPORTED: entry(
    text("تعداد روزهای تمرین پشتیبانی نمی‌شود", "Training-day count is not supported"),
    text(
      "برنامه تمرین با وزن بدن در حال حاضر برای ۲، ۳ یا ۴ روز در هفته طراحی شده است.",
      "Bodyweight workout plans are currently designed for 2, 3, or 4 days per week.",
    ),
  ),
  BODYWEIGHT_PULL_UP_BAR_REQUIRED: entry(
    text("میله بارفیکس لازم است", "Pull-up bar required"),
    text(
      "برای اجرای کامل این برنامه و تمرین عضلات پشت و زیربغل به میله بارفیکس نیاز دارید. میله بارفیکس را به تجهیزات اضافه کنید.",
      "A pull-up bar is needed to complete this plan and train your back and lats. Add a pull-up bar to your equipment.",
    ),
  ),
  BODYWEIGHT_TEMPLATE_EXERCISE_UNAVAILABLE: entry(
    text("حرکت مناسب پیدا نشد", "A suitable exercise is unavailable"),
    text(
      "با محدودیت‌های فعلی شما یکی از حرکات این برنامه قابل اجرا یا ایمن نیست. تجهیزات و محدودیت‌های تمرینی خود را بررسی کنید.",
      "One exercise in this plan cannot be performed safely with your current limitations. Check your equipment and training restrictions.",
    ),
  ),
  WORKOUT_SESSION_ACTION_FAILED: entry(
    text("تغییر وضعیت جلسه انجام نشد", "Workout session could not be updated"),
    text("تغییر وضعیت جلسه تمرین انجام نشد. دوباره تلاش کنید.", "The workout session could not be updated. Try again."),
  ),
  WORKOUT_REPLACEMENT_NOT_ALLOWED: entry(
    text("جایگزین حرکت مجاز نیست", "Exercise replacement is not allowed"),
    text("این حرکت جایگزین برای برنامه فعلی مجاز نیست.", "This exercise is not an allowed replacement for the current plan."),
  ),
  WORKOUT_CHECKIN_INVALID: entry(
    text("چک‌این معتبر نیست", "Check-in is invalid"),
    text("اطلاعات چک‌این معتبر نیست. موارد واردشده را بررسی کنید.", "The check-in is invalid. Review the submitted information."),
  ),
  WORKOUT_PLAN_DELETE_FAILED: entry(
    text("حذف نسخه برنامه انجام نشد", "Plan version could not be deleted"),
    text("حذف نسخه قدیمی برنامه انجام نشد. دوباره تلاش کنید.", "The old workout plan version could not be deleted. Try again."),
  ),
  WORKOUT_CYCLE_ALREADY_STARTED: entry(
    text("چرخه قبلاً شروع شده است", "Workout cycle already started"),
    text("این برنامه قبلاً با تاریخ دیگری شروع شده است.", "This plan has already been started with another date."),
  ),
  WORKOUT_CYCLE_INPUT_INVALID: entry(
    text("اطلاعات چرخه معتبر نیست", "Workout cycle input is invalid"),
    text("اطلاعات چرخه تمرینی معتبر نیست.", "The workout cycle information is invalid."),
  ),
  WORKOUT_CYCLE_FEEDBACK_NOT_FOUND: entry(
    text("بازخورد چرخه پیدا نشد", "Cycle feedback not found"),
    text("بازخورد چرخه تمرینی پیدا نشد.", "The workout cycle feedback was not found."),
  ),
  WORKOUT_WEEKLY_CHECKIN_NOT_FOUND: entry(
    text("چک‌این هفتگی پیدا نشد", "Weekly check-in not found"),
    text("چک‌این هفتگی این هفته پیدا نشد.", "The weekly check-in for this week was not found."),
  ),
  WORKOUT_SESSION_DATE_CONFLICT: entry(
    text("تاریخ جلسه تکراری است", "Workout session date conflict"),
    text("جلسه دیگری برای این تاریخ برنامه‌ریزی شده است.", "Another workout session is already scheduled for this date."),
  ),
  TIMEZONE_INVALID: entry(
    text("منطقه زمانی معتبر نیست", "Timezone is invalid"),
    text("منطقه زمانی معتبر نیست.", "The selected timezone is invalid."),
  ),
  WORKOUT_PDF_UNAVAILABLE: entry(
    text("دانلود PDF انجام نشد", "PDF download failed"),
    text("فایل PDF برنامه آماده نشد. دوباره تلاش کنید.", "The workout-plan PDF could not be prepared. Try again."),
  ),
  NUTRITION_PROFILE_INCOMPLETE: entry(
    text("پروفایل تغذیه کامل نیست", "Nutrition profile incomplete"),
    text("برای ادامه، اطلاعات تغذیه را در پروفایل کامل کنید.", "Complete your nutrition profile to continue."),
  ),
  NUTRITION_PROFILE_NOT_FOUND: entry(
    text("پروفایل تغذیه پیدا نشد", "Nutrition profile not found"),
    text("پروفایل تغذیه ثبت نشده است.", "The nutrition profile was not found."),
  ),
  NUTRITION_PROFILE_REQUIRED: entry(
    text("پروفایل تغذیه لازم است", "Nutrition profile required"),
    text("ابتدا اطلاعات تغذیه را کامل کنید.", "Complete your nutrition profile first."),
  ),
  NUTRITION_PRODUCT_MODE_REQUIRED: entry(
    text("مسیر تغذیه لازم است", "Nutrition path required"),
    text("این قابلیت فقط در مسیر تغذیه در دسترس است.", "This feature is available only in the nutrition path."),
  ),
  SHARED_PROFILE_REQUIRED: entry(
    text("اطلاعات پایه لازم است", "Basic profile information required"),
    text("ابتدا اطلاعات پایه پروفایل را کامل کنید.", "Complete your basic profile information first."),
  ),
  STRUCTURED_EXERCISE_NOT_FOUND: entry(
    text("اطلاعات تمرین پیدا نشد", "Exercise information not found"),
    text("اطلاعات تمرین ساختاریافته ثبت نشده است.", "Your structured exercise information has not been recorded."),
  ),
  NUTRITION_PLAN_NOT_SELECTED: entry(
    text("برنامه انتخاب نشده است", "Plan not selected"),
    text("ابتدا همین برنامه غذایی را انتخاب کنید.", "Select this nutrition plan first."),
  ),
  NUTRITION_PLAN_NOT_READY: entry(
    text("برنامه آماده نیست", "Plan is not ready"),
    text("این برنامه غذایی هنوز آماده شروع نیست.", "This nutrition plan is not ready to start yet."),
  ),
  NUTRITION_PLAN_ALREADY_STARTED: entry(
    text("برنامه قبلاً شروع شده است", "Plan already started"),
    text("این برنامه غذایی قبلاً با تاریخ دیگری شروع شده است.", "This nutrition plan has already been started on another date."),
  ),
  NUTRITION_REFERENCE_PLAN_NOT_STARTABLE: entry(
    text("برنامه مقایسه‌ای قابل شروع نیست", "Reference plan cannot start"),
    text("برنامه مقایسه‌ای قابل شروع نیست.", "The reference plan cannot be started."),
  ),
  TARGET_INFEASIBLE: entry(
    text("هدف‌های تغذیه‌ای شدنی نیستند", "Nutrition targets are infeasible"),
    text("حداقل‌های علمی در بازه کالری انتخاب‌شده قابل جمع نیستند.", "The scientific minimums cannot fit within the selected calorie range."),
  ),
  NUTRITION_ESTIMATE_NOT_FOUND: entry(
    text("برآورد تغذیه‌ای پیدا نشد", "Nutrition estimate not found"),
    text("هنوز برآورد تغذیه‌ای ثبت نشده است.", "A nutrition estimate has not been recorded yet."),
  ),
  NUTRITION_ONBOARDING_BLOCKED: entry(
    text("بررسی پزشک لازم است", "Physician review required"),
    text("برای حفظ ایمنی، ادامه این مسیر فقط با بررسی پزشک ممکن است.", "For safety, this path can continue only after physician review."),
  ),
  DIETARY_PATTERN_NOT_SUPPORTED_V1: entry(
    text("الگوی تغذیه پشتیبانی نمی‌شود", "Dietary pattern is not supported"),
    text("الگوی تغذیه‌ای انتخاب‌شده در نسخه فعلی پشتیبانی نمی‌شود.", "The selected dietary pattern is not supported in the current version."),
  ),
  PROGRAM_NOT_FOUND: entry(
    text("برنامه پیدا نشد", "Program not found"),
    text("برنامه تغذیه‌ای پیدا نشد.", "The nutrition program was not found."),
  ),
  NUTRITION_PLAN_NOT_FOUND: entry(
    text("برنامه غذایی پیدا نشد", "Nutrition plan not found"),
    text("هنوز برنامه غذایی هفتگی ساخته نشده است.", "A weekly nutrition plan has not been created yet."),
  ),
  ACTIVE_NUTRITION_PLAN_NOT_FOUND: entry(
    text("برنامه غذایی فعال پیدا نشد", "Active nutrition plan not found"),
    text("هنوز برنامه غذایی تأییدشده و فعالی وجود ندارد.", "There is no approved active nutrition plan yet."),
  ),
  ACTIVE_PLAN_REQUIRED: entry(
    text("برنامه فعال لازم است", "Active plan required"),
    text("برای انجام این کار باید یک برنامه تأییدشده و فعال داشته باشید.", "An approved active plan is required for this action."),
  ),
  ACTIVE_PLAN_DAY_NOT_FOUND: entry(
    text("روز برنامه پیدا نشد", "Plan day not found"),
    text("روز برنامه غذایی فعال پیدا نشد.", "The requested day was not found in the active nutrition plan."),
  ),
  ACTIVE_PLAN_MEAL_NOT_FOUND: entry(
    text("وعده برنامه پیدا نشد", "Plan meal not found"),
    text("وعده برنامه غذایی فعال پیدا نشد.", "The requested meal was not found in the active nutrition plan."),
  ),
  ACTIVE_FREE_MEAL_NOT_FOUND: entry(
    text("وعده آزاد پیدا نشد", "Free meal not found"),
    text("وعده آزاد فعال برای این تاریخ پیدا نشد.", "No active free meal was found for this date."),
  ),
  CONSUMPTION_ENTRY_NOT_FOUND: entry(
    text("رکورد مصرف پیدا نشد", "Consumption entry not found"),
    text("رکورد مصرف غذایی پیدا نشد.", "The food consumption entry was not found."),
  ),
  USE_PLANNED_MEAL_ADJUSTMENT: entry(
    text("تنظیم وعده برنامه‌ریزی‌شده لازم است", "Use the planned-meal adjustment"),
    text("برای تغییر این وعده از گزینه تنظیم وعده برنامه‌ریزی‌شده استفاده کنید.", "Use the planned-meal adjustment to change this meal."),
  ),
  PORTION_RATIO_REQUIRED: entry(
    text("نسبت مصرف لازم است", "Portion ratio required"),
    text("نسبت مصرف وعده را وارد کنید.", "Enter the consumed portion ratio."),
  ),
  INVALID_DATE_RANGE: entry(
    text("بازه تاریخ معتبر نیست", "Date range is invalid"),
    text("بازه تاریخ انتخاب‌شده معتبر نیست.", "The selected date range is invalid."),
  ),
  INVALID_IDEMPOTENCY_KEY: entry(
    text("کلید درخواست معتبر نیست", "Request key is invalid"),
    text("کلید درخواست معتبر نیست. دوباره تلاش کنید.", "The request key is invalid. Try again."),
  ),
  ENTRY_GRAMS_REQUIRED: entry(
    text("مقدار غذا لازم است", "Food amount is required"),
    text("مقدار غذا را به گرم وارد کنید.", "Enter the food amount in grams."),
  ),
  FOOD_PHOTO_PROVIDER_UNAVAILABLE: entry(
    text("تحلیل عکس غذا موقتاً در دسترس نیست", "Food photo provider unavailable"),
    text("تحلیل عکس غذا فعلاً در دسترس نیست. بعداً دوباره تلاش کنید.", "Food photo analysis is temporarily unavailable. Try again later."),
  ),
  FOOD_PHOTO_ESTIMATE_NOT_FOUND: entry(
    text("برآورد عکس پیدا نشد", "Photo estimate not found"),
    text("برآورد این عکس پیدا نشد یا دیگر در دسترس نیست.", "This photo estimate was not found or is no longer available."),
  ),
  FOOD_PHOTO_ESTIMATION_DISABLED: entry(
    text("تحلیل عکس فعال نیست", "Photo analysis is disabled"),
    text("تحلیل عکس غذا در حال حاضر فعال نیست.", "Food photo analysis is not currently enabled."),
  ),
  FOOD_PHOTO_TOO_LARGE: entry(
    text("عکس خیلی بزرگ است", "Photo is too large"),
    text("حجم عکس بیشتر از حد مجاز است. عکس کوچک‌تری انتخاب کنید.", "The photo is larger than the allowed limit. Choose a smaller photo."),
  ),
  FOOD_PHOTO_ITEM_NOT_FOUND: entry(
    text("مورد عکس پیدا نشد", "Photo item not found"),
    text("مورد انتخاب‌شده در برآورد عکس پیدا نشد.", "The selected item was not found in this photo estimate."),
  ),
  FOOD_PRICE_RESEARCH_NOT_CONFIGURED: entry(
    text("قیمت‌یابی پیکربندی نشده است", "Price research is not configured"),
    text("سرویس قیمت‌یابی برای این قابلیت پیکربندی نشده است.", "Price research is not configured for this feature."),
  ),
  FOOD_PRICE_REFRESH_INVALID: entry(
    text("تنظیمات به‌روزرسانی قیمت معتبر نیست", "Invalid price refresh settings"),
    text("تنظیمات به‌روزرسانی قیمت معتبر نیست.", "The price refresh settings are invalid. Review them and try again."),
  ),
  FOOD_PRICE_RESEARCH_FAILED: entry(
    text("قیمت‌یابی خودکار انجام نشد", "Automatic price research failed"),
    text("قیمت‌یابی خودکار انجام نشد. دوباره تلاش کنید.", "Automatic price research could not be completed. Try again."),
  ),
  FOOD_PHOTO_STORAGE_UNAVAILABLE: entry(
    text("ذخیره‌سازی عکس در دسترس نیست", "Photo storage unavailable"),
    text("ذخیره‌سازی عکس غذا فعلاً در دسترس نیست. بعداً دوباره تلاش کنید.", "Food photo storage is temporarily unavailable. Try again later."),
  ),
  INVALID_FOOD_PHOTO: entry(
    text("عکس غذا معتبر نیست", "Food photo is invalid"),
    text("عکس غذا معتبر نیست. عکس دیگری انتخاب کنید.", "The food photo is invalid. Choose another photo."),
  ),
  UNRESOLVED_ITEMS_REQUIRE_EDIT: entry(
    text("اصلاح موارد شناسایی‌شده لازم است", "Items need correction"),
    text("پیش از ثبت، موارد شناسایی‌شده را اصلاح و تأیید کنید.", "Correct and confirm the identified items before saving."),
  ),
  INVALID_STORAGE_KEY: entry(
    text("فایل قابل دسترسی نیست", "File is not accessible"),
    text("فایل موردنظر قابل دسترسی نیست. دوباره تلاش کنید.", "The requested file is not accessible. Try again."),
  ),
  PRIVATE_ACCESS_TOKEN_REQUIRED: entry(
    text("دسترسی فایل معتبر نیست", "File access is invalid"),
    text("دسترسی خصوصی به فایل معتبر نیست. دوباره تلاش کنید.", "Private file access is invalid. Try again."),
  ),
  THIRD_PARTY_PROCESSING_CONSENT_REQUIRED: entry(
    text("رضایت پردازش لازم است", "Processing consent required"),
    text("برای تحلیل عکس غذا باید رضایت پردازش را تأیید کنید.", "Confirm processing consent before analyzing the food photo."),
  ),
  RATE_LIMIT_EXCEEDED: entry(
    text("درخواست‌های زیادی ارسال شده است", "Too many requests"),
    text("درخواست‌های زیادی ارسال شده است. کمی بعد دوباره تلاش کنید.", "Too many requests were sent. Try again later."),
  ),
  NUTRITION_GENERATION_CONSTRAINT_UNMET: entry(
    text("ساخت برنامه کامل نشد", "Plan generation constraints"),
    text("ساخت برنامه با یکی از محدودیت‌های فعلی کامل نشد.", "The plan could not be generated because of one of the current constraints."),
  ),
  STRICT_BUDGET_EXCEEDED: entry(
    text("بودجه سخت‌گیرانه کافی نیست", "Strict budget exceeded"),
    text("هزینه برنامه‌ای که با شرایط فعلی ساخته شد از بودجه غذایی تعیین‌شده بیشتر است. بودجه را افزایش بده یا حالت بودجه را از سخت‌گیرانه به انعطاف‌پذیر تغییر بده.", "The generated plan exceeds your current strict food budget. Increase the budget or switch to flexible budget mode."),
  ),
  FLEXIBLE_BUDGET_CAP_EXCEEDED: entry(
    text("سقف بودجه انعطاف‌پذیر کافی نیست", "Flexible budget cap exceeded"),
    text("حتی با محدوده انعطاف‌پذیر بودجه، هزینه برنامه از سقف مجاز بیشتر شده است. بودجه غذایی را کمی افزایش بده.", "Even the flexible budget limit is not enough for the current plan. Increase your food budget."),
  ),
  NUTRIENT_UPPER_LIMIT_EXCEEDED: entry(
    text("سقف ایمن ریزمغذی رعایت نشد", "Safe nutrient limit exceeded"),
    text("برنامه ساخته‌شده از سقف ایمن یکی از ریزمغذی‌ها عبور کرده است، بنابراین فیتیشن آن را قبول نکرد.", "The generated plan exceeds the safe upper limit for at least one micronutrient, so it was rejected."),
  ),
  INSUFFICIENT_PRICE_COVERAGE: entry(
    text("پوشش قیمت کافی نیست", "Insufficient price coverage"),
    text("برای تعداد کافی از مواد غذایی، قیمت معتبر در دسترس نیست و بدون قیمت قابل اعتماد امکان ساخت برنامه وجود ندارد.", "Reliable prices are unavailable for enough foods to build the plan."),
  ),
  GOAL_RESELECTION_REQUIRED: entry(
    text("هدف نیاز به بازبینی دارد", "Goal review required"),
    text("هدف فعلی با شرایط تمرینی ثبت‌شده قابل برنامه‌ریزی نیست. هدف یا اطلاعات تمرینت را بررسی کن.", "The current goal is not compatible with the recorded training conditions. Review your goal or exercise information."),
  ),
  STRUCTURED_EXERCISE_REQUIRED: entry(
    text("اطلاعات تمرین لازم است", "Exercise information is required"),
    text("اطلاعات تمرین برای محاسبه و ساخت برنامه تغذیه کامل نیست.", "Exercise information is required before the nutrition plan can be generated."),
  ),
  PROTEIN_MINIMUM_EXCEEDS_CALORIE_BUDGET: entry(
    text("حداقل پروتئین با کالری سازگار نیست", "Protein minimum exceeds calorie budget"),
    text("حداقل پروتئین موردنیاز با کالری هدف فعلی قابل جمع نیست.", "The minimum protein requirement cannot fit within the current calorie target."),
  ),
  CARBOHYDRATE_MINIMUM_EXCEEDS_CALORIE_BUDGET: entry(
    text("حداقل کربوهیدرات با کالری سازگار نیست", "Carbohydrate minimum exceeds calorie budget"),
    text("حداقل کربوهیدرات موردنیاز با کالری هدف فعلی قابل جمع نیست.", "The minimum carbohydrate requirement cannot fit within the current calorie target."),
  ),
  FAT_MINIMUM_EXCEEDS_CALORIE_BUDGET: entry(
    text("حداقل چربی با کالری سازگار نیست", "Fat minimum exceeds calorie budget"),
    text("حداقل چربی موردنیاز با کالری هدف فعلی قابل جمع نیست.", "The minimum fat requirement cannot fit within the current calorie target."),
  ),
  PHYSICIAN_MANUAL_PLAN_REQUIRED: entry(
    text("بررسی پزشک لازم است", "Physician plan required"),
    text("با توجه به شرایط ثبت‌شده، ساخت خودکار برنامه مناسب نیست و برنامه باید توسط پزشک تنظیم یا بررسی شود.", "Based on the recorded conditions, an automatic plan is not appropriate and physician involvement is required."),
  ),
  UNSUPPORTED_OR_HARD_BLOCKED: entry(
    text("ساخت خودکار برنامه مجاز نیست", "Automatic planning unavailable"),
    text("با شرایط فعلی، ساخت خودکار برنامه تغذیه مجاز نیست.", "Automatic nutrition planning is unavailable under the current safety conditions."),
  ),
  USER_BUDGET_BELOW_MINIMUM_FEASIBLE: entry(
    text("بودجه برای حداقل‌های برنامه کافی نیست", "Budget below feasible minimum"),
    text("با بودجه فعلی، ساخت برنامه‌ای که حداقل‌های تعیین‌شده برای هدف شما را رعایت کند ممکن نشد.", "With your current budget, generating a plan that satisfies the required minimums for your goal was not possible."),
  ),
  NO_BUDGET_FEASIBLE_PLAN_FOUND: entry(
    text("برنامه سازگار با بودجه پیدا نشد", "No budget-feasible plan found"),
    text("با قیمت‌ها و کاتالوگ فعلی، برنامه سازگار در این بودجه پیدا نشد.", "With current prices and catalogue, no compatible plan was found in this budget."),
  ),
  PLAN_BUNDLE_NOT_FOUND: entry(
    text("بسته برنامه غذایی پیدا نشد", "Plan bundle not found"),
    text("بسته برنامه غذایی پیدا نشد.", "The nutrition plan bundle was not found."),
  ),
  PLAN_SELECTION_INVALID: entry(
    text("انتخاب برنامه معتبر نیست", "Plan selection is invalid"),
    text("انتخاب برنامه غذایی معتبر نیست.", "The selected nutrition plan is not valid."),
  ),
  NUTRITION_INPUT_INVALID: entry(
    text("اطلاعات تغذیه معتبر نیست", "Nutrition information is invalid"),
    text("اطلاعات تغذیه‌ای معتبر نیست. موارد واردشده را بررسی کنید.", "The nutrition information is invalid. Check the entered values."),
  ),
  FOOD_NOT_FOUND: entry(
    text("ماده غذایی پیدا نشد", "Food not found"),
    text("ماده غذایی پیدا نشد.", "The food was not found."),
  ),
  FOOD_CATALOGUE_INVALID: entry(
    text("اطلاعات ماده غذایی معتبر نیست", "Food catalogue entry is invalid"),
    text("اطلاعات ماده غذایی معتبر نیست. موارد مشخص‌شده را بررسی کنید.", "The food catalogue entry is invalid. Check the highlighted information."),
  ),
  FOOD_CATALOGUE_PRIMARY_NUTRIENTS_REQUIRED: entry(
    text("اطلاعات غذایی کامل نیست", "Primary nutrients are required"),
    text("برای تأیید ماده غذایی، مواد مغذی اصلی باید کامل باشند.", "The primary nutrients must be complete before this food can be verified."),
  ),
  MEAL_CATALOGUE_INVALID: entry(
    text("اطلاعات وعده معتبر نیست", "Meal catalogue entry is invalid"),
    text("اطلاعات وعده غذایی معتبر نیست. موارد مشخص‌شده را بررسی کنید.", "The meal catalogue entry is invalid. Check the highlighted information."),
  ),
  MEAL_CODE_ALREADY_EXISTS: entry(
    text("کد وعده تکراری است", "Meal code already exists"),
    text("این کد وعده قبلاً استفاده شده است.", "This meal code is already in use."),
  ),
  MEAL_CODE_IMMUTABLE: entry(
    text("کد وعده قابل تغییر نیست", "Meal code cannot be changed"),
    text("کد وعده پس از ایجاد قابل تغییر نیست.", "A meal code cannot be changed after creation."),
  ),
  MEAL_FOOD_NOT_FOUND: entry(
    text("ماده غذایی وعده پیدا نشد", "Meal food not found"),
    text("یکی از مواد غذایی انتخاب‌شده برای وعده پیدا نشد.", "One of the foods selected for this meal was not found."),
  ),
  MEAL_FOOD_NOT_VERIFIED: entry(
    text("ماده غذایی تأیید نشده است", "Meal food is not verified"),
    text("وعده تأییدشده فقط می‌تواند از مواد غذایی تأییدشده استفاده کند.", "A verified meal can use only verified foods."),
  ),
  PREPARED_RECIPE_INVALID: entry(
    text("دستور تهیه وعده معتبر نیست", "Prepared recipe is invalid"),
    text("دستور تهیه وعده کامل نیست یا داده‌های لازم آن وجود ندارد.", "The prepared recipe is incomplete or missing required data."),
  ),
  NUTRITION_PROGRAM_MEALS_INVALID: entry(
    text("وعده‌های برنامه معتبر نیستند", "Program meals are invalid"),
    text("یکی از وعده‌های انتخاب‌شده برای برنامه پیدا نشد.", "One of the meals selected for the program was not found."),
  ),
  NUTRITION_PROGRAM_MEALS_UNVERIFIED: entry(
    text("وعده برنامه تأیید نشده است", "Program meals are not verified"),
    text("برنامه فعال فقط می‌تواند از وعده‌های تأییدشده استفاده کند.", "An active program can use only verified meals."),
  ),
  NUTRITION_PROGRAM_STRUCTURE_INVALID: entry(
    text("ساختار برنامه معتبر نیست", "Program structure is invalid"),
    text("دسته‌بندی وعده‌های برنامه با ساختار انتخاب‌شده سازگار نیست.", "The program meal categories do not match the selected structure."),
  ),
  NUTRITION_PROGRAM_SAVE_FAILED: entry(
    text("ذخیره برنامه انجام نشد", "Program could not be saved"),
    text("برنامه تغذیه‌ای ذخیره نشد. دوباره تلاش کنید.", "The nutrition program could not be saved. Try again."),
  ),
  NUTRITION_PROGRAM_INVALID: entry(
    text("اطلاعات برنامه معتبر نیست", "Nutrition program is invalid"),
    text("اطلاعات برنامه تغذیه‌ای معتبر نیست. موارد واردشده را بررسی کنید.", "The nutrition program information is invalid. Check the entered values."),
  ),
  NUTRITION_PROGRAM_UNAVAILABLE: entry(
    text("برنامه غذایی در دسترس نیست", "Nutrition program is unavailable"),
    text("برنامه غذایی فعالی برای این انتخاب وجود ندارد.", "No active nutrition program is available for this selection."),
  ),
  meal_referenced: entry(
    text("وعده قابل حذف نیست", "Meal cannot be deleted"),
    text("این وعده در برنامه‌های موجود استفاده شده و قابل حذف نیست.", "This meal is used by existing programs and cannot be deleted."),
  ),
  MEAL_REFERENCED: entry(
    text("وعده قابل حذف نیست", "Meal cannot be deleted"),
    text("این وعده در برنامه‌های موجود استفاده شده و قابل حذف نیست.", "This meal is used by existing programs and cannot be deleted."),
  ),
  REQUEST_FAILED: entry(
    text("درخواست ساخت برنامه انجام نشد", "Plan request failed"),
    text("درخواست ساخت برنامه کامل نشد. دوباره تلاش کنید.", "The plan request could not be completed. Try again."),
  ),
  NUTRITION_PLAN_GENERATED: entry(
    text("برنامه ساخته شد", "Plan generated"),
    text("برنامه ساخته شد.", "Plan generated."),
  ),
  NUTRITION_PLAN_GENERATION_FAILED: entry(
    text("ساخت برنامه انجام نشد", "Plan generation failed"),
    text("ساخت برنامه انجام نشد. اطلاعات پروفایل را بررسی کن.", "Plan generation failed. Review your profile."),
  ),
  NUTRITION_PLAN_SAFETY_BLOCKED: entry(
    text("ساخت خودکار برنامه مجاز نیست", "Automatic planning is unavailable"),
    text("ساخت خودکار این برنامه به‌دلیل وضعیت ایمنی مجاز نیست.", "Automatic planning is unavailable because of the current safety status."),
  ),
  NUTRITION_PLAN_INFEASIBLE: entry(
    text("برنامه شدنی پیدا نشد", "No feasible plan found"),
    text("با محدودیت‌های فعلی برنامه ایمن و شدنی پیدا نشد.", "No safe feasible plan was found under the current constraints."),
  ),
  NUTRITION_TARGET_INFEASIBLE: entry(
    text("هدف‌های فعلی شدنی نیستند", "Targets are infeasible"),
    text("هدف‌های فعلی با حداقل‌های علمی قابل جمع نیستند.", "The current targets cannot satisfy the scientific minimums."),
  ),
  NUTRITION_PRICE_COVERAGE_UNAVAILABLE: entry(
    text("پوشش قیمت معتبر کافی نیست", "Reliable price coverage is insufficient"),
    text("پوشش قیمت معتبر برای ساخت برنامه کافی نیست.", "Reliable price coverage is insufficient to build a plan."),
  ),
  PLAN_REVIEW_IN_PROGRESS: entry(
    text("نسخه در حال بررسی است", "Revision is under review"),
    text("این نسخه در حال بررسی پزشک است و تا پایان بررسی نمی‌توان وعده‌های آن را تغییر داد.", "This revision is under physician review and cannot be changed until the review is complete."),
  ),
  STALE_PLAN_REVISION: entry(
    text("نسخه برنامه تغییر کرده است", "Plan revision changed"),
    text("نسخه برنامه تغییر کرده است. صفحه را به‌روزرسانی کنید و دوباره تلاش کنید.", "The plan revision changed. Refresh the page and try again."),
  ),
  MEAL_NOT_FOUND: entry(
    text("وعده پیدا نشد", "Meal not found"),
    text("وعده موردنظر دیگر در این نسخه وجود ندارد.", "This meal is no longer available in this revision."),
  ),
  MEAL_LOCKED: entry(
    text("وعده قفل است", "Meal is locked"),
    text("این وعده قفل است و ابتدا باید قفل آن را باز کنید.", "This meal is locked. Unlock it before editing."),
  ),
  INCOMPATIBLE_MEAL_REPLACEMENT: entry(
    text("جایگزین وعده سازگار نیست", "Incompatible meal replacement"),
    text("این وعده جایگزین با نقش وعده سازگار نیست.", "That meal is not compatible with this meal slot."),
  ),
  FOOD_REPLACEMENT_NOT_FOUND: entry(
    text("جایگزین غذا پیدا نشد", "Food replacement not found"),
    text("ماده غذایی انتخاب‌شده دیگر برای این جایگزینی در دسترس نیست.", "That ingredient replacement is no longer available."),
  ),
  PLAN_GENERATION_NOT_FOUND: entry(
    text("داده ساخت برنامه پیدا نشد", "Plan generation not found"),
    text("داده ساخت برنامه پیدا نشد. دوباره صفحه را بارگذاری کنید.", "The plan-generation record was not found. Reload the page."),
  ),
  NUTRITION_REVIEW_NOT_CREATED: entry(
    text("بررسی برنامه ایجاد نشد", "Nutrition review was not created"),
    text("بررسی برنامه غذایی ایجاد نشد. دوباره تلاش کنید.", "The nutrition-plan review was not created. Try again."),
  ),
  REVIEW_ASSIGNED_TO_ANOTHER_PHYSICIAN: entry(
    text("بررسی به پزشک دیگری اختصاص دارد", "Review is assigned to another physician"),
    text("این پرونده به پزشک دیگری اختصاص داده شده است و اکنون قابل اقدام نیست.", "This case is assigned to another physician and cannot be acted on now."),
  ),
  REVIEW_NOT_IN_PROGRESS: entry(
    text("بررسی در وضعیت قابل انجام نیست", "Review is not in progress"),
    text("این بررسی در وضعیت قابل انجام نیست. وضعیت پرونده را دوباره بررسی کنید.", "This review is not in an actionable state. Check the case status again."),
  ),
  REVIEW_ALREADY_ASSIGNED: entry(
    text("بررسی قبلاً اختصاص داده شده است", "Review is already assigned"),
    text("این بررسی قبلاً به پزشک دیگری اختصاص داده شده است.", "This review has already been assigned to another physician."),
  ),
  REVIEW_NOTES_REQUIRED: entry(
    text("یادداشت بررسی لازم است", "Review notes are required"),
    text("برای این اقدام، یادداشت بررسی لازم است.", "Review notes are required for this action."),
  ),
  INVALID_REVIEW_ACTION: entry(
    text("اقدام بررسی معتبر نیست", "Review action is invalid"),
    text("اقدام انتخاب‌شده برای این بررسی معتبر نیست.", "The selected action is not valid for this review."),
  ),
  INVALID_REVIEW_TRANSITION: entry(
    text("تغییر وضعیت بررسی معتبر نیست", "Review transition is invalid"),
    text("تغییر وضعیت بررسی با وضعیت فعلی سازگار نیست.", "This review cannot move to the selected status."),
  ),
  PLAN_HARD_INVARIANTS_FAILED: entry(
    text("برنامه با محدودیت‌های ایمنی سازگار نیست", "Plan safety constraints failed"),
    text("برنامه با محدودیت‌های ایمنی سازگار نیست و قابل ثبت نیست.", "The plan does not satisfy its safety constraints and cannot be saved."),
  ),
  INVALID_DAY_SELECTION: entry(
    text("انتخاب روز معتبر نیست", "Day selection is invalid"),
    text("انتخاب روزهای برنامه معتبر نیست.", "The selected plan days are invalid."),
  ),
  IDEAL_REFERENCE_PLAN_CANNOT_BE_EDITED: entry(
    text("برنامه مقایسه‌ای قابل ویرایش نیست", "Reference plan cannot be edited"),
    text("برنامه مقایسه‌ای قابل ویرایش نیست.", "The reference plan cannot be edited."),
  ),
  INVALID_LAB_STORAGE_KEY: entry(
    text("سند آزمایش قابل دسترسی نیست", "Lab document is not accessible"),
    text("سند آزمایش قابل دسترسی نیست. دوباره تلاش کنید.", "The lab document is not accessible. Try again."),
  ),
  INVALID_LAB_DOCUMENT: entry(
    text("سند آزمایش معتبر نیست", "Lab document is invalid"),
    text("سند آزمایش معتبر نیست. فایل دیگری انتخاب کنید.", "The lab document is invalid. Choose another file."),
  ),
  LAB_STORAGE_UNAVAILABLE: entry(
    text("ذخیره‌سازی آزمایش در دسترس نیست", "Lab storage unavailable"),
    text("ذخیره‌سازی اسناد آزمایش فعلاً در دسترس نیست. بعداً دوباره تلاش کنید.", "Lab-document storage is temporarily unavailable. Try again later."),
  ),
  LAB_DOCUMENT_TOO_LARGE: entry(
    text("حجم سند آزمایش زیاد است", "Lab document is too large"),
    text("حجم سند آزمایش بیشتر از حد مجاز است. فایل کوچک‌تری انتخاب کنید.", "The lab document is larger than the allowed limit. Choose a smaller file."),
  ),
  LAB_REQUEST_NOT_FOUND: entry(
    text("درخواست آزمایش پیدا نشد", "Lab request not found"),
    text("درخواست آزمایش پیدا نشد.", "The lab request was not found."),
  ),
  MEDICAL_CONTEXT_NOT_FOUND: entry(
    text("اطلاعات پزشکی پیدا نشد", "Medical context not found"),
    text("اطلاعات پزشکی لازم برای بررسی پیدا نشد.", "The medical context required for review was not found."),
  ),
  LAB_DOCUMENT_NOT_FOUND: entry(
    text("سند آزمایش پیدا نشد", "Lab document not found"),
    text("سند آزمایش پیدا نشد.", "The lab document was not found."),
  ),
  INVALID_LAB_REQUEST_TRANSITION: entry(
    text("تغییر وضعیت درخواست آزمایش معتبر نیست", "Lab request transition is invalid"),
    text("تغییر وضعیت درخواست آزمایش با وضعیت فعلی سازگار نیست.", "The lab request cannot move to the selected status."),
  ),
  INVALID_SUPPLEMENT_COMPOSITION: entry(
    text("ترکیب مکمل معتبر نیست", "Supplement composition is invalid"),
    text("ترکیب مکمل معتبر نیست و قابل ثبت نیست.", "The supplement composition is invalid and cannot be saved."),
  ),
  SUPPLEMENT_SAFETY_HARD_BLOCK: entry(
    text("تجویز مکمل از نظر ایمنی مجاز نیست", "Supplement is blocked for safety"),
    text("این مکمل با شرایط ایمنی فعلی قابل تجویز نیست.", "This supplement cannot be prescribed under the current safety conditions."),
  ),
  SUPPLEMENT_UPPER_LIMIT_HARD_BLOCK: entry(
    text("سقف ایمن مکمل رعایت نمی‌شود", "Supplement safe limit exceeded"),
    text("مقدار مکمل از حد ایمن مجاز بیشتر است.", "The supplement amount exceeds the safe upper limit."),
  ),
  VERIFIED_SUPPLEMENT_OR_PLAN_NOT_FOUND: entry(
    text("مکمل یا برنامه پیدا نشد", "Verified supplement or plan not found"),
    text("مکمل یا برنامه تأییدشده پیدا نشد.", "The verified supplement or nutrition plan was not found."),
  ),
  ASSIGNED_REVIEW_REQUIRED: entry(
    text("اختصاص بررسی لازم است", "Assigned review required"),
    text("ابتدا بررسی برنامه را به نام خود ثبت کنید.", "Claim the plan review before continuing."),
  ),
  SUPPLEMENT_ORDER_NOT_FOUND: entry(
    text("سفارش مکمل پیدا نشد", "Supplement order not found"),
    text("سفارش مکمل پیدا نشد.", "The supplement order was not found."),
  ),
  INVALID_SUPPLEMENT_ORDER_TRANSITION: entry(
    text("تغییر وضعیت سفارش مکمل معتبر نیست", "Supplement order transition is invalid"),
    text("تغییر وضعیت سفارش مکمل با وضعیت فعلی سازگار نیست.", "The supplement order cannot move to the selected status."),
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
  BODY_ANALYSIS_STATE_INVALID: entry(
    text("وضعیت تحلیل معتبر نیست", "Body analysis state is invalid"),
    text("وضعیت تحلیل بدن اجازه این عملیات را نمی‌دهد.", "The body analysis is not in a state that allows this operation."),
  ),
  MEASUREMENT_CONFIRMATION_REQUIRED: entry(
    text("تأیید اندازه‌گیری لازم است", "Measurement confirmation required"),
    text("تأیید کنید اندازه‌گیری‌های فعلی مربوط به این اسکن هستند.", "Confirm that the current measurements represent this scan."),
  ),
  missing_body_analysis_inputs: entry(
    text("اطلاعات تحلیل کامل نیست", "Body analysis inputs are incomplete"),
    text("اطلاعات لازم برای تحلیل بدن کامل نیست.", "The required body analysis information is incomplete."),
  ),
  measurement_confirmation_required: entry(
    text("تأیید اندازه‌گیری لازم است", "Measurement confirmation required"),
    text("پیش از تحلیل، اندازه‌گیری‌های فعلی را تأیید کنید.", "Confirm the current measurements before analysis."),
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
  REVIEW_NOT_FOUND: entry(
    text("بررسی برنامه پیدا نشد", "Workout review not found"),
    text("بررسی برنامه پیدا نشد.", "The workout review was not found."),
  ),
  REVIEW_NOT_CLAIMED: entry(
    text("بررسی به نام شما ثبت نشده است", "Review is not claimed"),
    text("ابتدا باید بررسی را به نام خود ثبت کنید.", "Claim the review before continuing."),
  ),
  REVIEW_ALREADY_CLAIMED: entry(
    text("بررسی در اختیار مربی دیگری است", "Review is claimed by another coach"),
    text("این بررسی در اختیار مربی دیگری است.", "This review is currently claimed by another coach."),
  ),
  REVIEW_LEASE_EXPIRED: entry(
    text("مهلت بررسی تمام شده است", "Review lease expired"),
    text("مهلت بررسی تمام شده است. بررسی را دوباره دریافت کنید.", "The review lease expired. Load the review again."),
  ),
  STALE_DRAFT_REVISION: entry(
    text("نسخه پیش‌نویس تغییر کرده است", "Draft revision changed"),
    text("نسخه پیش‌نویس تغییر کرده است. اطلاعات را دوباره دریافت کنید.", "The draft revision changed. Reload the review."),
  ),
  INVALID_DRAFT: entry(
    text("پیش‌نویس برنامه معتبر نیست", "Invalid workout draft"),
    text("پیش‌نویس برنامه با محدودیت‌های فعلی سازگار نیست.", "The workout draft is not compatible with the current constraints."),
  ),
  EXERCISE_NOT_ALLOWED: entry(
    text("حرکت برای برنامه مجاز نیست", "Exercise is not allowed"),
    text("یکی از حرکات انتخاب‌شده برای این برنامه مجاز نیست.", "One selected exercise is not allowed for this plan."),
  ),
  REVIEW_ALREADY_APPROVED: entry(
    text("بررسی قبلاً تأیید شده است", "Review already approved"),
    text("این بررسی قبلاً تأیید شده است.", "This review has already been approved."),
  ),
  REVIEW_ALREADY_REJECTED: entry(
    text("بررسی قبلاً رد شده است", "Review already rejected"),
    text("این بررسی قبلاً رد شده است.", "This review has already been rejected."),
  ),
  REVIEW_EXPLANATION_REQUIRED: entry(
    text("توضیح رد برنامه لازم است", "Rejection explanation required"),
    text("برای رد برنامه، توضیح مربی لازم است.", "A coach explanation is required to reject the plan."),
  ),
  REVIEW_SUPERSEDED: entry(
    text("بررسی با نسخه جدید جایگزین شده است", "Review was superseded"),
    text("این بررسی با نسخه جدید برنامه جایگزین شده است.", "This review was superseded by a newer plan version."),
  ),
  PLAN_STRUCTURE_CHANGED: entry(
    text("ساختار برنامه تغییر کرده است", "Plan structure changed"),
    text("ساختار روزها و حرکت‌های برنامه نباید تغییر کند.", "The plan days and exercise slots cannot be changed."),
  ),
  PRESCRIPTION_MODE_MISMATCH: entry(
    text("نوع تجویز سازگار نیست", "Prescription mode mismatch"),
    text("نوع تجویز با اطلاعات حرکت انتخاب‌شده سازگار نیست.", "The prescription mode does not match the selected exercise."),
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
  ACCOUNT_DELETION_NOT_ENABLED: entry(
    text("حذف حساب فعلاً در دسترس نیست", "Account deletion is unavailable"),
    text("حذف حساب هنوز برای این محیط فعال نشده است.", "Account deletion is not enabled for this environment yet."),
  ),
  NO_PENDING_DELETION: entry(
    text("درخواست حذف حساب وجود ندارد", "No pending account deletion"),
    text("درخواست حذف حسابی در انتظار نیست.", "There is no pending account deletion request."),
  ),
  GRACE_PERIOD_EXPIRED: entry(
    text("مهلت لغو حذف حساب تمام شده است", "Account deletion grace period expired"),
    text("مهلت لغو حذف حساب تمام شده است.", "The account deletion grace period has expired."),
  ),
  AI_CONFIGURATION_INVALID: entry(
    text("تنظیمات هوش مصنوعی معتبر نیست", "AI configuration is invalid"),
    text("تنظیمات هوش مصنوعی را بررسی کنید.", "Check the AI configuration."),
  ),
  AI_CREDENTIAL_STORAGE_ERROR: entry(
    text("ذخیره اعتبار انجام نشد", "Credential storage failed"),
    text("ذخیره امن اعتبار هوش مصنوعی انجام نشد.", "The AI credential could not be stored securely."),
  ),
  AGENT_SERVICE_NOT_CONFIGURED: entry(
    text("سرویس Agent پیکربندی نشده است", "Agent Service is not configured"),
    text("سرویس Agent هنوز پیکربندی نشده است.", "The Agent Service has not been configured."),
  ),
  AGENT_SERVICE_UNAVAILABLE: entry(
    text("سرویس Agent در دسترس نیست", "Agent Service unavailable"),
    text("سرویس Agent موقتاً در دسترس نیست.", "The Agent Service is temporarily unavailable."),
  ),
  not_configured: entry(
    text("سرویس هوش مصنوعی پیکربندی نشده است", "AI service is not configured"),
    text("سرویس هوش مصنوعی برای این قابلیت پیکربندی نشده است.", "The AI service is not configured for this feature."),
  ),
  timeout: entry(
    text("پاسخ سرویس هوش مصنوعی طول کشید", "AI service timed out"),
    text("پاسخ سرویس هوش مصنوعی بیش از حد طول کشید. دوباره تلاش کنید.", "The AI service took too long to respond. Try again."),
  ),
  connection_failure: entry(
    text("ارتباط با سرویس هوش مصنوعی برقرار نشد", "AI service connection failed"),
    text("ارتباط با سرویس هوش مصنوعی برقرار نشد. دوباره تلاش کنید.", "The AI service could not be reached. Try again."),
  ),
  unauthorized: entry(
    text("اعتبار سرویس هوش مصنوعی پذیرفته نشد", "AI service authorization failed"),
    text("اعتبار سرویس هوش مصنوعی پذیرفته نشد. تنظیمات سرویس را بررسی کنید.", "The AI service authorization was rejected. Check the service configuration."),
  ),
  rate_limited: entry(
    text("درخواست‌های سرویس هوش مصنوعی زیاد است", "AI service rate limited"),
    text("درخواست‌های سرویس هوش مصنوعی زیاد است. کمی بعد دوباره تلاش کنید.", "The AI service is receiving too many requests. Try again later."),
  ),
  provider_unavailable: entry(
    text("سرویس هوش مصنوعی در دسترس نیست", "AI service unavailable"),
    text("سرویس هوش مصنوعی موقتاً در دسترس نیست. دوباره تلاش کنید.", "The AI service is temporarily unavailable. Try again."),
  ),
  invalid_request: entry(
    text("درخواست سرویس هوش مصنوعی معتبر نیست", "AI service request is invalid"),
    text("درخواست سرویس هوش مصنوعی معتبر نیست. دوباره تلاش کنید.", "The AI service rejected the request. Try again."),
  ),
  malformed_response: entry(
    text("پاسخ سرویس هوش مصنوعی معتبر نیست", "AI service response is invalid"),
    text("پاسخ سرویس هوش مصنوعی معتبر نبود. دوباره تلاش کنید.", "The AI service returned an invalid response. Try again."),
  ),
  invalid_output: entry(
    text("خروجی سرویس هوش مصنوعی معتبر نیست", "AI service output is invalid"),
    text("خروجی سرویس هوش مصنوعی قابل استفاده نیست. دوباره تلاش کنید.", "The AI service returned unusable output. Try again."),
  ),
  refusal: entry(
    text("سرویس هوش مصنوعی درخواست را نپذیرفت", "AI service refused the request"),
    text("سرویس هوش مصنوعی نتوانست این درخواست را انجام دهد.", "The AI service could not complete this request."),
  ),
  model_not_found: entry(
    text("مدل هوش مصنوعی پیدا نشد", "AI model not found"),
    text("مدل انتخاب‌شدهٔ هوش مصنوعی در دسترس نیست.", "The selected AI model is not available."),
  ),
  location_unsupported: entry(
    text("موقعیت سرویس پشتیبانی نمی‌شود", "Service location is unsupported"),
    text("این سرویس در موقعیت فعلی پشتیبانی نمی‌شود.", "This service is not supported in the current location."),
  ),
  ADMIN_ROLE_REQUIRED: entry(
    text("دسترسی مدیر لازم است", "Administrator access required"),
    text("این عملیات فقط برای مدیر در دسترس است.", "This operation is available only to an administrator."),
  ),
  BODY_PHOTO_SUBMISSION_INCOMPLETE: entry(
    text("اطلاعات عکس‌ها کامل نیست", "Photo submission is incomplete"),
    text("سه عکس بدن و رضایت پردازش عملیاتی لازم است.", "Three body photos and operational processing consent are required."),
  ),
  NOTIFICATION_PROVIDER_MISMATCH: entry(
    text("ارائه‌دهنده اعلان معتبر نیست", "Notification provider mismatch"),
    text("ارائه‌دهنده اعلان با پلتفرم دستگاه سازگار نیست.", "The notification provider does not match the device platform."),
  ),
  NOTIFICATION_DEVICE_NOT_FOUND: entry(
    text("دستگاه اعلان پیدا نشد", "Notification device not found"),
    text("دستگاه اعلان پیدا نشد.", "The notification device was not found."),
  ),
  TRAINING_STRUCTURE_NOT_FOUND: entry(
    text("ساختار تمرینی پیدا نشد", "Training structure not found"),
    text("ساختار تمرینی پیدا نشد.", "The training structure was not found."),
  ),
  TRAINING_STRUCTURE_INVALID: entry(
    text("اطلاعات ساختار تمرینی معتبر نیست", "Training structure is invalid"),
    text("اطلاعات ساختار تمرینی معتبر نیست. موارد مشخص‌شده را بررسی کنید.", "The training structure information is invalid. Check the highlighted fields."),
  ),
  TRAINING_STRUCTURE_REFERENCED: entry(
    text("ساختار تمرینی قابل تغییر نیست", "Training structure is in use"),
    text("این ساختار به قالب‌های تمرینی متصل است و قابل تغییر یا حذف نیست.", "This training structure is used by templates and cannot be changed or deleted."),
  ),
  TRAINING_TEMPLATE_NOT_FOUND: entry(
    text("قالب برنامه تمرینی پیدا نشد", "Training template not found"),
    text("قالب برنامه تمرینی پیدا نشد.", "The training-program template was not found."),
  ),
  TRAINING_TEMPLATE_INVALID: entry(
    text("اطلاعات قالب برنامه معتبر نیست", "Training template is invalid"),
    text("اطلاعات قالب برنامه تمرینی معتبر نیست. موارد مشخص‌شده را بررسی کنید.", "The training-program template information is invalid. Check the highlighted fields."),
  ),
  TRAINING_TEMPLATE_SAVE_FAILED: entry(
    text("ذخیره قالب برنامه انجام نشد", "Training template could not be saved"),
    text("ذخیره قالب برنامه تمرینی انجام نشد. دوباره تلاش کنید.", "The training-program template could not be saved. Try again."),
  ),
  TRAINING_TEMPLATE_SLOT_NOT_FOUND: entry(
    text("جایگاه قالب پیدا نشد", "Training template slot not found"),
    text("جایگاه قالب برنامه تمرینی پیدا نشد.", "The training-template slot was not found."),
  ),
  WORKOUT_ACTIVE_CYCLE_NOT_FOUND: entry(
    text("چرخه تمرینی فعال نیست", "Active workout cycle not found"),
    text("چرخه تمرینی فعالی وجود ندارد.", "There is no active workout cycle."),
  ),
  WORKOUT_CYCLE_NOT_FOUND: entry(
    text("چرخه تمرینی پیدا نشد", "Workout cycle not found"),
    text("چرخه تمرینی پیدا نشد.", "The workout cycle was not found."),
  ),
  WORKOUT_CYCLE_NOT_COMPLETE: entry(
    text("چرخه هنوز کامل نشده است", "Workout cycle is not complete"),
    text("چرخه تمرینی هنوز به پایان نرسیده است.", "The workout cycle has not reached its end."),
  ),
  WORKOUT_SESSION_NOT_FOUND: entry(
    text("جلسه تمرینی پیدا نشد", "Workout session not found"),
    text("جلسه تمرینی پیدا نشد.", "The workout session was not found."),
  ),
  WORKOUT_SESSION_ALREADY_FINISHED: entry(
    text("جلسه قبلاً پایان یافته است", "Workout session already finished"),
    text("این جلسه تمرینی قبلاً پایان یافته است.", "This workout session has already finished."),
  ),
  WORKOUT_SESSION_NOT_ACTIONABLE: entry(
    text("جلسه قابل انجام نیست", "Workout session is not actionable"),
    text("این جلسه تمرینی در وضعیت قابل انجام نیست.", "This workout session is not in an actionable state."),
  ),
  WORKOUT_CYCLE_EXERCISE_NOT_FOUND: entry(
    text("حرکت چرخه پیدا نشد", "Workout cycle exercise not found"),
    text("حرکت در چرخه تمرینی پیدا نشد.", "The exercise was not found in the workout cycle."),
  ),
  BILLING_PROVIDER_UNAVAILABLE: entry(
    text("درگاه پرداخت موقتاً در دسترس نیست", "Payment provider unavailable"),
    text("درگاه پرداخت فعلاً در دسترس نیست. بعداً دوباره تلاش کنید.", "The payment provider is temporarily unavailable. Try again later."),
    text("دوباره تلاش کنید", "Try again"),
  ),
  BILLING_ORDER_NOT_FOUND: entry(
    text("سفارش پرداخت پیدا نشد", "Billing order not found"),
    text("سفارش پرداخت موردنظر پیدا نشد.", "The requested billing order was not found."),
  ),
  ACCESS_AUDIT_UNAVAILABLE: entry(
    text("تاریخچه دسترسی در دسترس نیست", "Access audit is unavailable"),
    text("تاریخچه تغییرات دسترسی دریافت نشد. دوباره تلاش کنید.", "The access change history could not be loaded. Try again."),
  ),
  ACCESS_USERS_UNAVAILABLE: entry(
    text("فهرست کاربران در دسترس نیست", "User access list is unavailable"),
    text("فهرست کاربران و دسترسی‌ها دریافت نشد. دوباره تلاش کنید.", "The user access list could not be loaded. Try again."),
  ),
  ACCESS_CAMPAIGN_NOT_FOUND: entry(
    text("کمپین پیدا نشد", "Campaign not found"),
    text("کمپین دسترسی موردنظر پیدا نشد.", "The requested access campaign was not found."),
  ),
  ACCESS_USER_NOT_FOUND: entry(
    text("کاربر پیدا نشد", "User not found"),
    text("کاربر موردنظر پیدا نشد.", "The requested user was not found."),
  ),
  ACCESS_GRANT_NOT_FOUND: entry(
    text("اعطای دسترسی پیدا نشد", "Access grant not found"),
    text("اعطای دسترسی موردنظر پیدا نشد.", "The requested access grant was not found."),
  ),
  ACCESS_CAMPAIGN_CONFLICT: entry(
    text("وضعیت کمپین اجازه این کار را نمی‌دهد", "Campaign state conflict"),
    text("این عملیات با وضعیت فعلی کمپین سازگار نیست.", "This operation is not valid for the campaign's current state."),
  ),
  ACCESS_CAMPAIGN_INVALID: entry(
    text("اطلاعات کمپین معتبر نیست", "Campaign details are invalid"),
    text("اطلاعات کمپین را بررسی و موارد مشخص‌شده را اصلاح کنید.", "Check the campaign details and correct the highlighted fields."),
  ),
  ACCESS_CAMPAIGN_WINDOW_OVERLAPS: entry(
    text("بازه کمپین تداخل دارد", "Campaign window overlaps"),
    text("این بازه با یک Signup Trial فعال دیگر تداخل دارد.", "This window overlaps another active Signup Trial."),
  ),
  ACCESS_CAMPAIGN_SEMANTICS_IMMUTABLE: entry(
    text("مشخصات کمپین قفل شده است", "Campaign details are locked"),
    text("پس از اولین ردیم، مشخصات اصلی کمپین قابل تغییر نیست.", "The campaign's core details cannot change after redemption."),
  ),
  ACCESS_CAMPAIGN_NOT_REDEEMABLE: entry(
    text("کمپین قابل استفاده نیست", "Campaign is not redeemable"),
    text("این کمپین در وضعیت فعلی قابل اعمال نیست.", "This campaign cannot be redeemed in its current state."),
  ),
  ACCESS_CAMPAIGN_KIND_INVALID: entry(
    text("نوع کمپین معتبر نیست", "Campaign kind is invalid"),
    text("نوع کمپین انتخاب‌شده معتبر نیست.", "The selected campaign kind is invalid."),
  ),
  ACCESS_GRANT_IDEMPOTENCY_CONFLICT: entry(
    text("درخواست اعطای دسترسی تکراری است", "Duplicate access request"),
    text("این کلید درخواست قبلاً برای عملیات دیگری استفاده شده است.", "This request key has already been used for another access operation."),
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
