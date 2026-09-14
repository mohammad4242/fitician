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
  RECENT_AUTHENTICATION_REQUIRED: entry(
    text("تأیید دوباره هویت لازم است", "Recent sign-in required"),
    text("برای ادامه، دوباره وارد حساب شوید.", "Sign in again to continue."),
  ),
  INVALID_REAUTHENTICATION: entry(
    text("تأیید هویت انجام نشد", "Reauthentication failed"),
    text("رمز عبور درست نیست.", "The password is not correct."),
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
  FOOD_PHOTO_STORAGE_UNAVAILABLE: entry(
    text("ذخیره‌سازی عکس در دسترس نیست", "Photo storage unavailable"),
    text("ذخیره‌سازی عکس غذا فعلاً در دسترس نیست. بعداً دوباره تلاش کنید.", "Food photo storage is temporarily unavailable. Try again later."),
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
  REQUEST_FAILED: entry(
    text("درخواست ساخت برنامه انجام نشد", "Plan request failed"),
    text("درخواست ساخت برنامه انجام نشد. اتصال یا سرویس را بررسی کن و دوباره تلاش کن.", "The plan request failed. Check the connection or service and try again."),
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
  ACCOUNT_DELETION_NOT_ENABLED: entry(
    text("حذف حساب فعلاً در دسترس نیست", "Account deletion is unavailable"),
    text("حذف حساب هنوز برای این محیط فعال نشده است.", "Account deletion is not enabled for this environment yet."),
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
