from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CuratedSafetyNotes:
    fa: tuple[str, ...]
    en: tuple[str, ...]

    def __post_init__(self) -> None:
        if not 2 <= len(self.fa) <= 5 or len(self.fa) != len(self.en):
            raise ValueError("Curated safety notes must contain 2 to 5 bilingual items")
        if any(not note.strip() for note in (*self.fa, *self.en)):
            raise ValueError("Curated safety notes must not contain empty items")


_DUMBBELL_BENCH_PRESS = CuratedSafetyNotes(
    fa=(
        "کتف‌هاتو عقب و پایین نگه دار؛ نذار موقع پرس شونه‌ها بیان جلو و فشار سینه رو بدزدن.",
        "دمبل‌ها رو تا جایی پایین بیار که سینه خوب کش بیاد، ولی جلوی شونه تحت فشار بد قرار نگیره.",
        "مچ رو تقریباً روی آرنج نگه دار؛ نذار دمبل‌ها بیش‌ازحد داخل یا بیرون فرار کنن.",
        "بالا که میای فقط دمبل رو هل نده؛ فکر کن دو بازوت رو داری به سمت هم جمع می‌کنی.",
    ),
    en=(
        "Keep your shoulder blades back and down; do not let the shoulders roll forward and "
        "take tension away from the chest.",
        "Lower the dumbbells far enough to get a good chest stretch without forcing the front "
        "of the shoulder into an uncomfortable position.",
        "Keep the wrists roughly stacked over the elbows instead of letting the dumbbells drift "
        "too far in or out.",
        "As you press, think about bringing the upper arms toward each other rather than only "
        "pushing the dumbbells upward.",
    ),
)

_BARBELL_BENCH_PRESS = CuratedSafetyNotes(
    fa=(
        "کتف‌هاتو عقب و پایین قفل کن؛ نذار شونه بیاد جلو و فشار سینه رو بدزده.",
        "هالتر رو کنترل‌شده بیار پایین؛ از روی سینه ضربه نزن که وزنه پرت بشه بالا.",
        "آرنج‌هاتو نه کامل بچسبون به بدن نه ۹۰ درجه باز کن؛ یه زاویه طبیعی بین این دوتا نگه دار.",
        "برای عضله‌سازی قوس خیلی زیاد لازم نیست؛ یه قوس طبیعی نگه دار تا دامنه خوب سینه حفظ بشه.",
    ),
    en=(
        "Set the shoulder blades back and down so the shoulders do not roll forward and steal "
        "tension from the chest.",
        "Lower the bar under control and do not bounce it off the chest.",
        "Do not pin the elbows against the torso or flare them straight out; keep a comfortable "
        "angle between the two.",
        "For hypertrophy, an exaggerated powerlifting arch is unnecessary; keep a natural arch "
        "that still allows a productive chest range of motion.",
    ),
)

_BARBELL_INCLINE_BENCH_PRESS = CuratedSafetyNotes(
    fa=(
        "شیب نیمکت رو خیلی زیاد نکن؛ حدود ۳۰ درجه برای درگیر نگه داشتن بالاسینه انتخاب خوبیه.",
        "هالتر رو سمت قسمت بالاتر سینه پایین بیار، نه سمت شکم.",
        "آرنج‌هاتو یه مقدار جمع‌تر از پرس صاف نگه دار؛ نذار کامل به طرفین باز بشن.",
        "پایین حرکت عجله نکن؛ کشش بالاسینه رو بگیر و بعد پرس کن.",
    ),
    en=(
        "Do not set the bench too steep; around 30 degrees is a strong starting point for "
        "keeping the emphasis on the upper chest.",
        "Lower the bar toward the upper chest rather than toward the abdomen.",
        "Keep the elbows slightly more tucked than in a flat press instead of flaring them "
        "straight out.",
        "Do not rush the bottom; control the descent, feel the upper-chest stretch, then press.",
    ),
)

_BARBELL_DECLINE_BENCH_PRESS = CuratedSafetyNotes(
    fa=(
        "پاهاتو محکم قفل کن که روی نیمکت سر نخوری و بدنت ثابت بمونه.",
        "هالتر رو سمت پایین سینه بیار، نه بالای سینه.",
        "پایین رفتن رو کنترل کن؛ وزنه سنگین نباید باعث بشه هالتر رو روی سینه بکوبی.",
        "اگه پایین حرکت جلوی شونه فشار بد می‌گیری، دامنه رو زورکی بیشتر نکن.",
    ),
    en=(
        "Secure the legs firmly so you do not slide on the decline bench.",
        "Bring the bar toward the lower chest rather than the upper chest.",
        "Control the descent; heavier weight is not a reason to bounce the bar off the chest.",
        "If the bottom position creates uncomfortable front-shoulder stress, do not force "
        "additional depth.",
    ),
)

_DUMBBELL_INCLINE_BENCH_PRESS = CuratedSafetyNotes(
    fa=(
        "شیب نیمکت رو حوالی ۳۰ درجه نگه دار؛ خیلی بالاتر بری سرشونه جلو بیشتر وارد حرکت میشه.",
        "پایین حرکت بذار دمبل‌ها تا یه کشش خوب و قابل‌کنترل تو بالاسینه پایین بیان.",
        "آرنج‌ها رو متوسط جمع کن و موقع بالا رفتن دمبل‌ها رو بالا و کمی به سمت عقب پرس کن.",
        "بالای حرکت دمبل‌ها رو به هم نکوب؛ فشار سینه رو حفظ کن.",
    ),
    en=(
        "Keep the bench around 30 degrees; much steeper angles increasingly shift work toward "
        "the front delts.",
        "At the bottom, allow a deep but controlled upper-chest stretch.",
        "Keep a moderate elbow tuck and press the dumbbells upward with a slight backward path.",
        "Do not smash the dumbbells together at the top; keep tension on the chest.",
    ),
)

_DECLINE_DUMBBELL_BENCH_PRESS = CuratedSafetyNotes(
    fa=(
        "دمبل‌ها رو کنار قسمت پایین سینه فرود بیار، نه نزدیک گردن و شونه.",
        "پایین حرکت دنبال رکورد دامنه نباش؛ کشش خوب سینه کافیه، نه کشش دردناک شونه.",
        "بالا که میای فکر کن دو بازوت دارن به سمت هم جمع میشن، نه اینکه فقط دمبل‌ها رو هل بدی.",
    ),
    en=(
        "Lower the dumbbells beside the lower chest rather than toward the neck or shoulders.",
        "Do not chase maximum depth; a strong chest stretch is useful, but a painful shoulder "
        "stretch is not.",
        "On the way up, think about bringing the upper arms toward each other instead of only "
        "pushing the dumbbells.",
    ),
)

_DUMBBELL_LYING_HAMMER_PRESS = CuratedSafetyNotes(
    fa=(
        "کف دست‌ها رو روبه‌روی هم نگه دار، ولی آرنج‌ها رو کامل به پهلو نچسبون؛ وگرنه حرکت "
        "زیادی پشت‌بازویی میشه.",
        "دمبل‌ها رو تا یه کشش خوب و قابل‌کنترل تو سینه پایین بیار.",
        "موقع پرس فکر کن بازوهات رو داری به هم نزدیک می‌کنی، نه اینکه فقط وزنه رو بالا ببری.",
    ),
    en=(
        "Keep a neutral grip, but do not pin the elbows tightly to the torso or the movement "
        "will become overly triceps-dominant.",
        "Lower the dumbbells until you get a strong but controlled chest stretch.",
        "As you press, think about bringing the upper arms toward each other rather than simply "
        "lifting the weight.",
    ),
)

_DUMBBELL_INCLINE_HAMMER_PRESS = CuratedSafetyNotes(
    fa=(
        "شیب نیمکت رو حوالی ۳۰ درجه نگه دار تا حرکت زیادی سرشونه‌ای نشه.",
        "گریپ خنثی رو نگه دار ولی آرنج‌ها رو بیش‌ازحد به بدن نچسبون.",
        "دمبل رو مستقیم سقف پرت نکن؛ بالا و کمی عقب پرس کن.",
        "پایین حرکت رو کوتاه نکن؛ کشش کنترل‌شده بالاسینه بخش مهم حرکته.",
    ),
    en=(
        "Keep the incline around 30 degrees so the press does not become overly front-delt "
        "dominant.",
        "Maintain the neutral grip without excessively pinning the elbows to the torso.",
        "Do not press straight toward the ceiling; use a slightly upward-and-back path.",
        "Do not shorten the bottom range; a controlled upper-chest stretch is an important part "
        "of the movement.",
    ),
)

_LEVER_LYING_CHEST_PRESS = CuratedSafetyNotes(
    fa=(
        "دستگاه رو طوری تنظیم کن که دستگیره‌ها تقریباً روبه‌روی وسط سینه باشن.",
        "پشت و کتف‌هاتو روی پد ثابت نگه دار؛ موقع پرس شونه رو جلو ننداز.",
        "بذار آرنج‌ها تا جایی عقب برن که سینه خوب کش بیاد ولی شونه اذیت نشه.",
        "به‌جای فقط هل دادن دسته‌ها، فکر کن آرنج‌هات رو داری به سمت هم می‌بری.",
    ),
    en=(
        "Adjust the machine so the handles line up roughly with the middle of the chest.",
        "Keep the back and shoulder blades stable against the pad instead of rolling the "
        "shoulders forward.",
        "Let the elbows travel back far enough for a good chest stretch without irritating the "
        "shoulders.",
        "Instead of only pushing the handles, think about bringing the elbows toward each other.",
    ),
)

_LEVER_INCLINE_HAMMER_CHEST_PRESS = CuratedSafetyNotes(
    fa=(
        "ارتفاع صندلی رو جوری تنظیم کن که دستگیره‌ها جلوی بالاسینه قرار بگیرن، نه جلوی صورت.",
        "سینه بالا و شونه‌ها پایین؛ نذار حرکت تبدیل به پرس سرشانه بشه.",
        "برگشت دستگاه رو ول نکن؛ قسمت منفی حرکت رو کنترل کن.",
        "پایین حرکت یه کشش خوب و بدون درد تو بالاسینه بگیر.",
    ),
    en=(
        "Set the seat so the handles line up with the upper chest rather than the face.",
        "Keep the chest up and shoulders down so the movement does not turn into a shoulder "
        "press.",
        "Do not let the machine pull you back; control the eccentric portion.",
        "Use the bottom position to get a strong, pain-free upper-chest stretch.",
    ),
)

_MACHINE_CHEST_PRESS = CuratedSafetyNotes(
    fa=(
        "صندلی رو جوری تنظیم کن که دسته‌ها تقریباً هم‌سطح وسط سینه باشن.",
        "شونه‌ها رو روی پد نگه دار و نذار آخر تکرار از پد جدا و به جلو پرت بشن.",
        "وزنه‌ای بزن که بتونی پایین حرکت رو کامل و کنترل‌شده بگیری؛ نصفه زدن با وزنه بیشتر "
        "ارزش نداره.",
        "موقع پرس فکر کن آرنج‌ها رو داری به سمت هم هل میدی.",
    ),
    en=(
        "Adjust the seat so the handles sit roughly at mid-chest height.",
        "Keep the shoulders against the pad instead of letting them roll forward at the end "
        "of each rep.",
        "Use a load that lets you control the bottom range; heavier partial reps are not "
        "automatically better.",
        "As you press, think about driving the elbows toward each other.",
    ),
)

_DUMBBELL_FLY = CuratedSafetyNotes(
    fa=(
        "آرنج یه خم کوچیک داشته باشه و همون زاویه رو کل حرکت نگه دار؛ هی خم و صافش نکنی که "
        "حرکت تبدیل به پرس بشه.",
        "دست‌ها رو باز کن تا سینه حسابی کش بیاد، نه تا جایی که جلوی شونه درد بگیره.",
        "تصور کن داری یه بشکه بزرگ رو بغل می‌کنی؛ مسیر دست‌ها باید قوسی باشه.",
        "بالای حرکت دمبل‌ها رو به هم نکوب؛ نزدیک شدن بازوها مهم‌تر از برخورد دمبل‌هاست.",
    ),
    en=(
        "Keep a slight bend in the elbows and maintain roughly the same angle throughout the "
        "rep so the fly does not turn into a press.",
        "Open the arms until the chest gets a strong stretch, not until the front of the "
        "shoulder becomes painful.",
        "Imagine hugging a large barrel so the arms follow a smooth arc.",
        "Do not bang the dumbbells together at the top; bringing the upper arms together is "
        "what matters.",
    ),
)

_DUMBBELL_INCLINE_FLY = CuratedSafetyNotes(
    fa=(
        "شیب نیمکت رو پایین نگه دار؛ حدود ۲۰ تا ۳۰ درجه کافیه.",
        "وزنه سبک‌تر بردار و واقعاً کشش بالاسینه رو حس کن.",
        "آرنج نیمه‌خم و تقریباً ثابت بمونه؛ با خم کردن آرنج حرکت رو تبدیل به پرس نکن.",
        "اینجا کیفیت تکرار خیلی مهم‌تر از عدد دمبله.",
    ),
    en=(
        "Use a modest incline; roughly 20 to 30 degrees is enough.",
        "Use a lighter load and prioritize a clear upper-chest stretch.",
        "Keep the elbows softly bent and mostly fixed instead of turning the movement into a "
        "press.",
        "Rep quality matters much more here than the number printed on the dumbbell.",
    ),
)

_DECLINE_DUMBBELL_FLY = CuratedSafetyNotes(
    fa=(
        "مسیر دست‌ها رو کمی به سمت پایین سینه ببند.",
        "آرنج‌ها رو نرم و تقریباً ثابت نگه دار تا حرکت تبدیل به پرس نشه.",
        "قسمت پایین حرکت رو آروم برو؛ با وزنه سنگین دنبال کشش وحشیانه شونه نباش.",
    ),
    en=(
        "Bring the arms together on a path slightly toward the lower chest.",
        "Keep a soft, mostly fixed elbow angle so the fly does not become a press.",
        "Move slowly through the bottom range and do not chase an extreme shoulder stretch with "
        "heavy dumbbells.",
    ),
)

_FLAT_BENCH_CABLE_FLY = CuratedSafetyNotes(
    fa=(
        "نیمکت رو دقیقاً وسط دو کابل تنظیم کن تا فشار دو طرف برابر باشه.",
        "شروع حرکت بذار بازوها کمی از خط بدن عقب‌تر برن و سینه خوب کش بیاد.",
        "فکر کن دو بازوت رو داری به هم می‌رسونی، نه فقط دستگیره‌ها رو.",
        "بالای حرکت رو سریع رد نکن؛ کابل اونجا هم هنوز روی سینه فشار داره.",
    ),
    en=(
        "Place the bench centrally between the cables so both sides load evenly.",
        "At the start, allow the upper arms to move slightly behind the torso for a controlled "
        "chest stretch.",
        "Think about bringing the upper arms together rather than merely touching the handles.",
        "Do not rush through the top; the cable can still keep tension on the chest there.",
    ),
)

_CABLE_STANDING_FLY = CuratedSafetyNotes(
    fa=(
        "یه پا رو جلو بذار و تنه رو محکم نگه دار؛ نذار کابل بدنتو عقب و جلو بکشه.",
        "خم آرنج رو تقریباً ثابت نگه دار؛ اگه آرنج هی خم میشه داری حرکت رو تبدیل به پرس می‌کنی.",
        "دست‌ها می‌تونن آخر حرکت کمی از هم رد بشن، ولی فقط تا وقتی شونه راحت باشه.",
        "برگشت رو آروم انجام بده و بذار سینه دوباره کش بیاد.",
    ),
    en=(
        "Use a staggered stance and keep the torso stable instead of letting the cables rock "
        "the body back and forth.",
        "Keep the elbow bend mostly fixed; repeatedly bending the elbows turns the fly into a "
        "press.",
        "The hands may cross slightly at the finish if it remains comfortable for the shoulders.",
        "Control the return and allow the chest to lengthen again.",
    ),
)

_PEC_DECK_FLY = CuratedSafetyNotes(
    fa=(
        "صندلی رو جوری تنظیم کن که آرنج‌ها تقریباً هم‌سطح وسط سینه باشن.",
        "پشت و شونه‌ها رو روی پد نگه دار؛ برای بستن حرکت شونه رو جلو ننداز.",
        "عقب حرکت رو الکی کوتاه نکن؛ تا جایی برو که سینه خوب کش بیاد و شونه راحت باشه.",
        "به‌جای فشار دادن دستگیره‌ها، فکر کن آرنج‌هات رو داری به هم نزدیک می‌کنی.",
    ),
    en=(
        "Adjust the seat so the elbows sit roughly level with the middle of the chest.",
        "Keep the back and shoulders against the pad instead of rolling the shoulders forward "
        "to finish the rep.",
        "Do not unnecessarily shorten the stretched position; go back far enough for a strong "
        "chest stretch while the shoulders remain comfortable.",
        "Instead of squeezing the handles, think about bringing the elbows toward each other.",
    ),
)

_DUMBBELL_FLY_ON_EXERCISE_BALL = CuratedSafetyNotes(
    fa=(
        "اینجا وزنه‌پرستی نکن؛ چون توپ ناپایداره دمبل سبک‌تر انتخاب کن.",
        "پاها رو محکم روی زمین بذار و قبل از شروع فلای تنه رو ثابت کن.",
        "خم آرنج رو تقریباً ثابت نگه دار و فقط تا کشش قابل‌کنترل پایین برو.",
        "اگه برای ثابت موندن داری با کل بدن می‌جنگی، وزنه زیادی سنگینه.",
    ),
    en=(
        "Do not chase heavy dumbbells here; the unstable surface makes a lighter load more "
        "appropriate.",
        "Plant the feet firmly and stabilize the torso before starting the fly.",
        "Keep the elbow bend mostly fixed and lower only into a range you can control.",
        "If your whole body is fighting to stay balanced, the load is too heavy for the purpose "
        "of the exercise.",
    ),
)

_DUMBBELL_INCLINE_FLY_ON_EXERCISE_BALL = CuratedSafetyNotes(
    fa=(
        "اول بدنت رو روی توپ کامل ثابت کن، بعد زاویه بالاسینه رو بساز.",
        "دمبل سبک بردار و حرکت رو آروم و بدون عجله انجام بده.",
        "آرنج نرم و تقریباً ثابت بمونه؛ تمرکز روی باز و بسته شدن بازوها باشه.",
        "چون هم شیب داری هم سطح ناپایداره، دنبال حداکثر عمق نباش؛ کشش قابل‌کنترل کافیه.",
    ),
    en=(
        "Stabilize the body on the ball first, then establish the incline position.",
        "Use light dumbbells and keep the movement smooth and controlled.",
        "Keep a soft, mostly fixed elbow angle and focus on opening and closing the upper arms.",
        "Because both the incline and the unstable surface increase the demand, do not chase "
        "maximum depth; a controlled stretch is enough.",
    ),
)

_BAND_HIGH_FLY = CuratedSafetyNotes(
    fa=(
        "کش رو بالا ببند و دست‌ها رو پایین و داخل بیار، سمت پایین سینه.",
        "از همون شروع حرکت یه مقدار کشش روی باند داشته باش؛ نقطه شروع کاملاً شل نباشه.",
        "تنه رو تاب نده؛ اگه برای بستن دست‌ها باید بدنتو پرت کنی جلو، مقاومت زیادیه.",
        "برگشت رو کنترل کن؛ نذار کش دست‌هاتو با ضربه بکشه عقب.",
    ),
    en=(
        "Anchor the band high and bring the arms down and inward toward the lower chest.",
        "Keep some tension in the band from the starting position instead of beginning "
        "completely slack.",
        "Do not swing the torso; if you must throw the body forward to finish the rep, the "
        "resistance is too high.",
        "Control the return instead of letting the band snap the arms backward.",
    ),
)

_PUSH_UP = CuratedSafetyNotes(
    fa=(
        "بدنت از سر تا پاشنه یه خط بمونه؛ شکم و باسن رو سفت نگه دار و کمر رو آویزون نکن.",
        "دست‌ها کمی بازتر از عرض شونه و آرنج‌ها مایل باشن، نه اینکه کامل به طرفین باز بشن.",
        "سینه رو بین دست‌ها پایین ببر؛ فقط سر و گردن رو نزدیک زمین نکن.",
        "اگه شنا عادی برات خیلی آسونه، مقاومت یا سختی حرکت رو بیشتر کن تا ست واقعاً چالش‌برانگیز "
        "بمونه.",
    ),
    en=(
        "Keep the body in one line from head to heel by bracing the abs and glutes instead of "
        "letting the hips sag.",
        "Place the hands slightly wider than shoulder width and let the elbows track diagonally "
        "rather than flaring straight out.",
        "Lower the chest between the hands instead of merely dropping the head and neck toward "
        "the floor.",
        "If regular push-ups are very easy, increase the resistance or difficulty so the set "
        "remains genuinely challenging.",
    ),
)

_INCLINE_PUSH_UP = CuratedSafetyNotes(
    fa=(
        "کل بدن رو صاف نگه دار؛ فقط دست‌ها بالاترن، قرار نیست کمرت وسط حرکت خم بشه.",
        "سینه رو به لبه سطح نزدیک کن، نه صورت رو.",
        "ارتفاع رو جوری انتخاب کن که ست هنوز برات سخت باشه؛ سطح خیلی بلند حرکت رو بیش‌ازحد آسون "
        "می‌کنه.",
    ),
    en=(
        "Keep the whole body straight; only the hands are elevated, so do not fold at the hips.",
        "Bring the chest toward the edge of the support rather than leading with the face.",
        "Choose a height that still makes the set challenging; a very high surface can make the "
        "exercise too easy.",
    ),
)

_DEEP_PUSH_UP = CuratedSafetyNotes(
    fa=(
        "دست‌ها رو روی دو سطح مرتفع بذار تا پایین حرکت سینه بتونه از خط دست‌ها پایین‌تر بره.",
        "مزیت اصلی این حرکت همون کشش اضافه پایینه؛ نصفه زدن بخش مهم حرکت رو حذف می‌کنه.",
        "پایین رفتن رو کنترل کن و شکم و باسن رو سفت نگه دار.",
        "اگه عمق بیشتر جلوی شونه درد ایجاد می‌کنه، دامنه رو کمتر کن؛ عمق بیشتر به هر قیمتی بهتر "
        "نیست.",
    ),
    en=(
        "Use elevated handles or supports so the chest can travel below the level of the hands.",
        "The extra stretched range is a major reason to use this variation, so shallow reps "
        "remove much of its benefit.",
        "Control the descent and keep the abs and glutes braced.",
        "If greater depth causes front-shoulder pain, reduce the range; deeper is not "
        "automatically better at any cost.",
    ),
)

_ROTATIONAL_PUSH_UP = CuratedSafetyNotes(
    fa=(
        "اول یه شنا کامل بزن، بعد بچرخ؛ چرخش رو جای نصفه زدن شنا نذار.",
        "موقع چرخش کل تنه با هم بچرخه؛ کمر رو جداگانه نپیچون.",
        "برای فشار سینه کیفیت قسمت شنا مهم‌تر از نمایشی کردن چرخشه.",
    ),
    en=(
        "Complete the push-up first, then rotate; do not use the rotation as an excuse to "
        "shorten the push-up.",
        "Rotate the torso as one unit rather than twisting only through the lower back.",
        "For chest training, the quality of the push-up matters more than making the rotation "
        "dramatic.",
    ),
)

_CHEST_DIPS = CuratedSafetyNotes(
    fa=(
        "یه مقدار تنه رو جلو بده تا فشار بیشتر سمت سینه بمونه.",
        "شونه‌ها رو از گوش دور نگه دار؛ پایین حرکت شونه‌هاتو ول نکن بالا بیان.",
        "تا جایی پایین برو که سینه خوب کش بیاد ولی جلوی شونه درد نگیره.",
        "از ته حرکت تاب نخور و با ضربه خودتو بالا پرت نکن.",
    ),
    en=(
        "Use a slight forward torso lean to keep more emphasis on the chest.",
        "Keep the shoulders away from the ears instead of letting them shrug upward at the "
        "bottom.",
        "Descend far enough for a good chest stretch without creating front-shoulder pain.",
        "Do not swing out of the bottom or use momentum to launch yourself upward.",
    ),
)

_V_BAR_CLOSE_GRIP_BENCH_PRESS = CuratedSafetyNotes(
    fa=(
        "گریپ خنثی و نزدیک رو حفظ کن، ولی آرنج‌هاتو کامل به بدن نچسبون تا فشار فقط روی "
        "پشت‌بازو نیفته.",
        "هالتر رو کنترل‌شده سمت وسط سینه پایین بیار؛ با ضربه از روی سینه برش نگردون.",
        "مچ‌هاتو روی ساعد نگه دار و نذار V-bar توی پایین حرکت مچت رو به عقب خم کنه.",
        "اگه مسیر میله یا شونه‌هات ناپایدار شد، قبل از نزدیک شدن به ناتوانی ست رو تموم کن.",
    ),
    en=(
        "Keep the close neutral grip, but do not pin the elbows tightly to the torso or the "
        "press will become mostly triceps.",
        "Lower the bar toward the mid-chest under control instead of bouncing it off the chest.",
        "Keep the wrists stacked over the forearms and do not let the V-bar bend them backward "
        "at the bottom.",
        "If the bar path or shoulders become unstable, end the set before reaching failure.",
    ),
)

_PUSH_UP_VARIATIONS = CuratedSafetyNotes(
    fa=(
        "برای نسخه عمیق فقط از دو سطح کاملاً محکم استفاده کن؛ صندلی لق اینجا ریسک افتادن دارد.",
        "در نسخه شیب‌دار یا عمیق، سینه را پایین ببر و چانه را جلو نده تا فشار از مسیر درست خارج "
        "نشود.",
        "در عمق اضافه آهسته پایین برو؛ اگر جلوی شونه یا مچ اذیت شد، عمق را کمتر کن.",
        "لگن را هم‌راستا نگه دار و بین تغییر نسخه‌ها با عجله جای دست و پا را عوض نکن.",
    ),
    en=(
        "For the deep variation, use two completely stable supports; a slipping chair makes the "
        "setup unsafe.",
        "In both the incline and deep variations, lower the chest instead of reaching the chin "
        "forward.",
        "Move slowly into the extra depth; reduce the range if the front of the shoulder or "
        "wrists become uncomfortable.",
        "Keep the hips aligned and do not rush the hand or foot setup when switching between "
        "variations.",
    ),
)

_BARBELL_BENCH_PRESS_VARIATIONS = CuratedSafetyNotes(
    fa=(
        "قبل از شروع دقیقاً شیب نیمکت و گریپ همین نسخه را مشخص کن؛ وسط ست تنظیمات را عوض نکن.",
        "هالتر را به سمت بخش مناسب سینه همان نسخه پایین بیاور و مسیرش را به سمت گردن یا شکم "
        "منحرف نکن.",
        "در هر تنوع کتف‌ها را روی نیمکت ثابت نگه دار و اگر مسیر میله ناپایدار شد، ست را ادامه "
        "نده.",
    ),
    en=(
        "Confirm the bench angle and grip for the selected variation before starting; do not "
        "change the setup mid-set.",
        "Lower the bar toward the appropriate chest area for that variation without drifting "
        "toward the neck or abdomen.",
        "Keep the shoulder blades supported on the bench for every variation and stop if the bar "
        "path becomes unstable.",
    ),
)


CURATED_SAFETY_NOTES: dict[str, CuratedSafetyNotes] = {
    "dumbbell-bench-press": _DUMBBELL_BENCH_PRESS,
    "fedb-0025-barbell-bench-press": _BARBELL_BENCH_PRESS,
    "fedb-0033-barbell-decline-bench-press": _BARBELL_DECLINE_BENCH_PRESS,
    "fedb-0047-barbell-incline-bench-press": _BARBELL_INCLINE_BENCH_PRESS,
    "fedb-0301-decline-dumbbell-bench-press": _DECLINE_DUMBBELL_BENCH_PRESS,
    "fedb-0302-decline-dumbbell-fly": _DECLINE_DUMBBELL_FLY,
    "fedb-0308-dumbbell-fly": _DUMBBELL_FLY,
    "fedb-0314-dumbbell-incline-bench-press": _DUMBBELL_INCLINE_BENCH_PRESS,
    "fedb-0319-dumbbell-incline-fly": _DUMBBELL_INCLINE_FLY,
    "fedb-0321-dumbbell-incline-hammer-press": _DUMBBELL_INCLINE_HAMMER_PRESS,
    "fedb-0340-dumbbell-lying-hammer-press": _DUMBBELL_LYING_HAMMER_PRESS,
    "fedb-0493-incline-push-up": _INCLINE_PUSH_UP,
    "fedb-0577-lever-lying-chest-press": _LEVER_LYING_CHEST_PRESS,
    "fedb-0620-flat-bench-cable-fly": _FLAT_BENCH_CABLE_FLY,
    "fedb-1269-cable-standing-fly": _CABLE_STANDING_FLY,
    "fedb-1274-deep-push-up": _DEEP_PUSH_UP,
    "fedb-1277-dumbbell-fly-on-exercise-ball": _DUMBBELL_FLY_ON_EXERCISE_BALL,
    "fedb-1278-dumbbell-incline-fly-on-exercise-ball": _DUMBBELL_INCLINE_FLY_ON_EXERCISE_BALL,
    "fedb-1299-lever-incline-hammer-chest-press": _LEVER_INCLINE_HAMMER_CHEST_PRESS,
    "fedb-drv-band-high-fly-resistance-band-high-fly": _BAND_HIGH_FLY,
    "fedb-drv-chest-dips-chest-dips": _CHEST_DIPS,
    "fedb-drv-lever-pec-deck-fly-pec-deck-fly": _PEC_DECK_FLY,
    "fedb-drv-push-ups-push-up": _PUSH_UP,
    "fedb-drv-rotate-push-up-female-rotational-push-up": _ROTATIONAL_PUSH_UP,
    "owner-10b53230907d-incline-dumbbell-bench-press": _DUMBBELL_INCLINE_BENCH_PRESS,
    "owner-1f8e38bb4987-v-bar-close-grip-bench-press": _V_BAR_CLOSE_GRIP_BENCH_PRESS,
    "owner-58fc33e9ee2f-barbell-bench-press": _BARBELL_BENCH_PRESS,
    "owner-70511e2a29d7-barbell-bench-press": _BARBELL_BENCH_PRESS,
    "owner-8f222e61e93c-pec-deck-fly": _PEC_DECK_FLY,
    "owner-94176702df28-barbell-bench-press": _BARBELL_BENCH_PRESS,
    "owner-9cfaf45c29f4-push-up-variations-decline-and-deep": _PUSH_UP_VARIATIONS,
    "owner-a7f5c2f31bca-pec-deck-fly": _PEC_DECK_FLY,
    "owner-cb58d2dbac7f-dumbbell-bench-press": _DUMBBELL_BENCH_PRESS,
    "owner-db0d7c3471db-pec-deck-fly": _PEC_DECK_FLY,
    "owner-ed7a7bc1b137-barbell-bench-press-variations": _BARBELL_BENCH_PRESS_VARIATIONS,
    "machine-chest-press": _MACHINE_CHEST_PRESS,
    "pec-deck-fly": _PEC_DECK_FLY,
}


_BARBELL_BENT_OVER_ROW = CuratedSafetyNotes(
    fa=(
        "از لگن خم شو، نه از کمر؛ شکم رو سفت کن و زاویه تنه رو تا آخر ست تقریباً ثابت نگه دار.",
        "هالتر رو سمت دنده‌های پایین و بالای شکم بکش؛ "
        "آرنج‌ها رو عقب ببر، نه اینکه فقط با دست وزنه رو بکشی.",
        "پایین حرکت اجازه بده کتف‌ها کمی جلو برن و پشت کش بیاد، ولی کمرت گرد نشه.",
        "اگه هر تکرار داری تنه رو بالا میاری و هالتر رو پرت می‌کنی، "
        "وزنه برای یه Row تمیز زیادی سنگینه.",
    ),
    en=(
        "Hinge from the hips, not the lower back; brace your abs and keep your torso angle almost "
        "unchanged through the set.",
        "Pull the bar toward the lower ribs and upper abdomen; drive the elbows back instead of "
        "lifting the weight with your hands.",
        "Let the shoulder blades reach slightly at the bottom so the back can lengthen, but do not "
        "round the lower back.",
        "If your torso rises and the bar gets thrown on every rep, the weight is too heavy for a "
        "clean row.",
    ),
)

_BARBELL_UNDERHAND_ROW = CuratedSafetyNotes(
    fa=(
        "آرنج‌ها رو نزدیک‌تر به بدن نگه دار و هالتر رو سمت ناف و دنده‌های پایین بکش "
        "تا مسیر لت حفظ بشه.",
        "مچ‌هات رو نشکن و حرکت رو تبدیل به جلو بازو نکن؛ دست‌ها فقط اتصالن، آرنج‌ها رو عقب بکش.",
        "زاویه تنه رو ثابت نگه دار؛ با لگن تاب نده که هالتر بالا بیاد.",
        "پایین حرکت بذار لت کش بیاد، ولی شکم سفت و کمر خنثی بمونه.",
    ),
    en=(
        "Keep the elbows closer to your body and pull the bar toward the navel and lower ribs to "
        "keep the lat path.",
        "Keep the wrists straight and do not turn the row into a curl; the hands connect you to "
        "the "
        "bar while the elbows drive back.",
        "Keep the torso angle steady instead of swinging the hips to get the bar higher.",
        "Let the lats lengthen at the bottom while the abs stay braced and the spine stays "
        "neutral.",
    ),
)

_SEATED_CABLE_ROW_V_GRIP = CuratedSafetyNotes(
    fa=(
        "تو برگشت دست‌ها رو جلو ببر و بذار کتف‌ها باز بشن تا لت کش بیاد؛ ولی کمرت رو گرد نکن.",
        "آرنج‌ها رو نزدیک بدن عقب ببر و دسته رو سمت ناف و پایین شکم بکش.",
        "آخر حرکت سینه رو بالا نگه دار و پشت رو جمع کن، ولی شونه‌هاتو سمت گوش بالا ننداز.",
        "بدنت رو مثل تاب جلو و عقب نکن؛ اگه بدون تاب دسته نمیاد، وزنه زیادی سنگینه.",
    ),
    en=(
        "Reach the hands forward on the return and let the shoulder blades spread so the lats "
        "can lengthen, without rounding your back.",
        "Drive the elbows close to your body and pull the handle toward the navel and lower "
        "abdomen.",
        "Keep the chest lifted and squeeze the back at the finish, but do not shrug toward the "
        "ears.",
        "Do not rock back and forth like a pendulum; if the handle needs momentum, the weight "
        "is too "
        "heavy.",
    ),
)

_SEATED_CABLE_ROW_WIDE_GRIP = CuratedSafetyNotes(
    fa=(
        "آرنج‌ها رو یه مقدار بازتر نگه دار و میله رو سمت بالای شکم بکش تا پشت میانی بیشتر "
        "وارد کار بشه.",
        "تو برگشت بذار کتف‌ها از هم فاصله بگیرن؛ دامنه رو نصفه نکن.",
        "موقع کشیدن کتف‌ها رو به هم نزدیک کن، ولی شونه‌ها رو بالا ننداز.",
        "تنه رو ثابت نگه دار؛ این حرکت قرار نیست با عقب پرت کردن بدن تبدیل به Row کل بدن بشه.",
    ),
    en=(
        "Keep the elbows slightly wider and pull the bar toward the upper abdomen to bring more "
        "mid-back into the movement.",
        "Let the shoulder blades move apart on the return instead of cutting the range short.",
        "Bring the shoulder blades together as you pull, but do not lift the shoulders toward the "
        "ears.",
        "Keep the torso steady; this row should not become a full-body throw backward.",
    ),
)

_CABLE_SEATED_HIGH_ROW = CuratedSafetyNotes(
    fa=(
        "سینه رو بالا و تنه رو ثابت نگه دار؛ دسته رو با عقب پرت کردن بدن نکش.",
        "آرنج‌ها رو عقب و کمی بیرون ببر و دسته رو سمت بالای شکم بکش.",
        "آخر حرکت کتف‌ها رو جمع کن، ولی شونه‌هاتو سمت گوش بالا نکش.",
        "تو برگشت اجازه بده پشت دوباره کش بیاد و وزنه رو ول نکن.",
    ),
    en=(
        "Keep your chest up and torso steady; do not use a backward body throw to move the handle.",
        "Take the elbows back and slightly out, pulling the handle toward the upper abdomen.",
        "Squeeze the shoulder blades at the finish, but do not shrug the shoulders toward the "
        "ears.",
        "Let the back lengthen again on the return and keep the weight under control.",
    ),
)

_LEVER_HIGH_ROW = CuratedSafetyNotes(
    fa=(
        "صندلی رو جوری تنظیم کن که دستگیره و مسیر آرنج با پشتت جور باشه؛ برای رسیدن به دسته "
        "شونه‌هات رو جمع نکن.",
        "تو شروع حرکت بذار کتف‌ها کمی جلو برن و پشت کش بیاد، بعد آرنج‌ها رو عقب و پایین بکش.",
        "اگه هدفت پشت بالاست، آرنج رو یه مقدار بازتر ببر و آخر حرکت کتف‌ها رو جمع کن.",
        "سینه و تنه رو ثابت نگه دار؛ با کمر و لگن به دستگاه ضربه نزن.",
    ),
    en=(
        "Set the seat so the handles and elbow path fit your back; do not pinch the shoulders "
        "back just to reach the handles.",
        "Let the shoulder blades reach slightly at the start, then drive the elbows back and down.",
        "For more upper-back emphasis, take the elbows a little wider and squeeze the shoulder "
        "blades at the finish.",
        "Keep the chest and torso supported; do not jerk the machine with your lower back or hips.",
    ),
)

_CHEST_SUPPORTED_ROW = CuratedSafetyNotes(
    fa=(
        "سینه رو واقعاً به پد بچسبون؛ اگه هر تکرار از پد جدا میشی داری مزیت اصلی حرکت رو از "
        "بین می‌بری.",
        "پایین حرکت بذار کتف‌ها جلو برن و پشت کش بیاد؛ لازم نیست از اول تا آخر کتف رو قفل نگه داری.",
        "آرنج‌ها رو عقب ببر و فکر کن با پشت داری وزنه رو جابه‌جا می‌کنی، نه با جلو بازو.",
        "بالای حرکت پشت رو جمع کن، ولی شونه‌هات رو سمت گوش بالا ننداز.",
    ),
    en=(
        "Keep your chest genuinely against the pad; lifting off on every rep removes the main "
        "benefit of the movement.",
        "Let the shoulder blades reach at the bottom so the back can lengthen; they do not need to "
        "stay locked for the whole set.",
        "Drive the elbows back and think about moving the weight with your back, not your biceps.",
        "Squeeze the back at the top, but do not shrug the shoulders toward the ears.",
    ),
)

_DUMBBELL_INCLINE_ROW = CuratedSafetyNotes(
    fa=(
        "سینه رو به نیمکت بچسبون و نذار برای بالا آوردن دمبل از پد جدا بشه.",
        "آرنج‌ها رو حدود ۴۵ تا ۶۰ درجه باز کن و دمبل رو سمت دنده‌ها و بالای شکم بکش.",
        "پایین حرکت دست‌ها رو کامل‌تر جلو بده تا کتف‌ها باز بشن و پشت کش بیاد.",
        "بالا دمبل رو با جلو بازو جمع نکن؛ آرنج رو عقب ببر و پشت رو منقبض کن.",
    ),
    en=(
        "Keep your chest against the bench and do not lift off the pad to raise the dumbbells.",
        "Let the elbows travel about 45 to 60 degrees out and pull the dumbbells toward the ribs "
        "and upper abdomen.",
        "Reach the hands farther forward at the bottom so the shoulder blades spread and the back "
        "can lengthen.",
        "Do not finish by curling the dumbbells with the biceps; drive the elbows back and "
        "contract the back.",
    ),
)

_DUMBBELL_HAMMER_INCLINE_ROW = CuratedSafetyNotes(
    fa=(
        "گریپ خنثی رو نگه دار و آرنج‌ها رو نزدیک‌تر به تنه عقب ببر تا مسیر لت حفظ بشه.",
        "دمبل‌ها رو سمت دنده‌های پایین و لگن بکش، نه مستقیم سمت شونه‌ها.",
        "پایین حرکت دست‌ها رو جلو بده تا لت خوب کش بیاد، ولی سینه از نیمکت جدا نشه.",
        "وزنه رو با تاب و ضربه بالا نبر؛ کل مزیت این حرکت ثبات و حذف تقلبه.",
    ),
    en=(
        "Keep the neutral grip and drive the elbows closer to the torso to keep the lat path.",
        "Pull the dumbbells toward the lower ribs and hips rather than straight toward the "
        "shoulders.",
        "Reach the hands forward at the bottom to lengthen the lats, while keeping the chest "
        "on the "
        "bench.",
        "Do not swing or jerk the weights up; the value of this row is its stable, strict setup.",
    ),
)

_CAMBERED_LYING_ROW = CuratedSafetyNotes(
    fa=(
        "سینه رو روی نیمکت نگه دار؛ برای بلند کردن میله نیم‌تنه رو از پد بلند نکن.",
        "آرنج‌ها رو عقب ببر و میله رو سمت زیر سینه یا بالای شکم بکش.",
        "بالا کتف‌ها رو جمع کن و شونه‌ها رو سمت گوش بالا ننداز.",
        "پایین حرکت دست‌ها رو کامل کن و پشت رو کش بده، ولی میله رو با ضربه از زمین نکن.",
    ),
    en=(
        "Keep your chest on the bench; do not lift the torso off the pad to clear the bar.",
        "Drive the elbows back and pull the bar toward the lower chest or upper abdomen.",
        "Squeeze the shoulder blades at the top without shrugging toward the ears.",
        "Finish the reach at the bottom to lengthen the back, but do not yank the bar off the "
        "floor.",
    ),
)

_DUMBBELL_BENT_OVER_ROW = CuratedSafetyNotes(
    fa=(
        "از لگن خم شو و شکمت رو سفت نگه دار؛ زاویه تنه قرار نیست با هر تکرار بالا و پایین بشه.",
        "برای لت، آرنج‌ها رو نزدیک‌تر به بدن نگه دار و دمبل‌ها رو سمت لگن و دنده‌های پایین بکش.",
        "پایین حرکت بذار کتف‌ها جلو برن و لت کش بیاد، ولی کمرت گرد نشه.",
        "اگه برای بالا آوردن دمبل مجبور شدی تنه رو پرت کنی، وزنه زیادی سنگینه.",
    ),
    en=(
        "Hinge from the hips and brace your abs; the torso angle should not rise and fall on every "
        "rep.",
        "For a lat-focused path, keep the elbows closer to the body and pull the dumbbells toward "
        "the hips and lower ribs.",
        "Let the shoulder blades reach at the bottom so the lats can lengthen, but do not round "
        "the "
        "lower back.",
        "If you have to throw the torso to lift the dumbbells, the weight is too heavy.",
    ),
)

_SINGLE_ARM_CABLE_ROW = CuratedSafetyNotes(
    fa=(
        "اول دست رو جلو بده و بذار لت کش بیاد، بعد آرنج رو سمت جیب عقب بکش.",
        "شونه رو موقع کشیدن سمت گوش نبر؛ آرنج باید عقب بره، نه شونه بالا.",
        "یه مقدار حرکت طبیعی کتف خوبه، ولی کل تنه رو نچرخون که حرکت تبدیل به Twist بشه.",
        "برگشت رو آروم انجام بده؛ نصف ارزش این حرکت همون کشش کنترل‌شده جلوئه.",
    ),
    en=(
        "Reach the arm forward first to let the lat lengthen, then drive the elbow toward the back "
        "pocket.",
        "Do not shrug during the pull; the elbow should travel back instead of the shoulder "
        "rising.",
        "Some natural scapular movement is useful, but do not rotate the whole torso into a twist.",
        "Take the return slowly; much of this exercise's value is the controlled reach forward.",
    ),
)

_TWISTING_SEATED_ROW = CuratedSafetyNotes(
    fa=(
        "تو برگشت اجازه بده کتف و بالای تنه یه مقدار طبیعی جلو بچرخه تا لت کش بیاد.",
        "موقع کشیدن آرنج رو سمت لگن ببر و همزمان تنه رو فقط به اندازه کنترل‌شده برگردون.",
        "لگن و کمر پایین رو ثابت نگه دار؛ چرخش رو از کمرت ندزد.",
        "اگه حرکت بیشتر شبیه چرخوندن بدن شده تا Row، وزنه رو سبک‌تر کن.",
    ),
    en=(
        "On the return, allow a small natural reach of the shoulder blade and upper torso so the "
        "lat can lengthen.",
        "As you pull, guide the elbow toward the hip and return the torso only as much as you can "
        "control.",
        "Keep the pelvis and lower back steady; do not create the rotation by twisting through the "
        "lumbar spine.",
        "If the movement looks more like turning the body than a row, reduce the weight.",
    ),
)

_LEVER_T_BAR_ROW = CuratedSafetyNotes(
    fa=(
        "تنه رو محکم نگه دار و دسته رو سمت بالای شکم بکش؛ با لگن وزنه رو پرت نکن.",
        "تو برگشت بذار دست‌ها کامل‌تر جلو برن و پشت کش بیاد.",
        "آرنج‌ها رو عقب ببر و بالای حرکت کتف‌ها رو جمع کن.",
        "اگه هر تکرار شونه‌هات رو بالا میندازی، وزنه رو کم کن و پشت رو دوباره درگیر کن.",
    ),
    en=(
        "Keep the torso braced and pull the handle toward the upper abdomen; do not throw the "
        "weight with your hips.",
        "Let the hands reach farther forward on the return so the back can lengthen.",
        "Drive the elbows back and squeeze the shoulder blades at the top.",
        "If your shoulders rise on every rep, lower the weight and reconnect with the back.",
    ),
)

_LEVER_REVERSE_T_BAR_ROW = CuratedSafetyNotes(
    fa=(
        "آرنج‌ها رو یه مقدار بازتر ببر و دسته رو کمی بالاتر سمت بالای شکم بکش تا پشت بالا "
        "بیشتر درگیر بشه.",
        "قبل از کشیدن شونه‌هاتو سمت گوش بالا نبر؛ آرنج‌ها باید حرکت رو هدایت کنن.",
        "بالا کتف‌ها رو به هم نزدیک کن و پایین دوباره اجازه بده باز بشن.",
        "تنه رو ثابت نگه دار؛ دامنه اضافه رو با تاب دادن بدن نساز.",
    ),
    en=(
        "Take the elbows slightly wider and pull the handle a little higher toward the upper "
        "abdomen to involve more upper back.",
        "Set the shoulders away from the ears before pulling; let the elbows lead the movement.",
        "Bring the shoulder blades together at the top, then let them spread again on the return.",
        "Keep the torso steady instead of creating extra range by swinging the body.",
    ),
)

_DUMBBELL_REAR_DELT_ROW = CuratedSafetyNotes(
    fa=(
        "آرنج‌ها رو بازتر نگه دار و دمبل‌ها رو سمت بالای سینه بکش؛ اینجا قرار نیست آرنج "
        "بچسبه به پهلو.",
        "فکر کن آرنج‌ها رو از هم باز و عقب می‌بری، نه اینکه فقط دمبل رو با دست جمع کنی.",
        "سینه رو روی نیمکت نگه دار و برای بالا آوردن وزنه از پد جدا نشو.",
        "شونه‌ها رو سمت گوش بالا ننداز؛ فشار رو روی پشت بالا و پشت شونه نگه دار.",
    ),
    en=(
        "Keep the elbows wider and pull the dumbbells toward the upper chest; the elbows should "
        "not hug the sides here.",
        "Think about opening the elbows apart and back instead of simply curling the dumbbells "
        "with "
        "the hands.",
        "Keep the chest on the bench and do not lift off the pad to raise the weight.",
        "Keep the shoulders away from the ears and the effort in the upper back and rear "
        "shoulders.",
    ),
)

_DUMBBELL_ROTATIONAL_ROW = CuratedSafetyNotes(
    fa=(
        "اول یه Hip Hinge محکم بساز و زاویه تنه رو ثابت نگه دار؛ چرخش دست نباید باعث "
        "چرخیدن کل بدنت بشه.",
        "دمبل‌ها رو سمت دنده‌های پایین بکش و همزمان کف دست رو نرم و طبیعی بچرخون؛ مچ رو "
        "زورکی نپیچون.",
        "آرنج‌ها رو عقب ببر و بالای حرکت پشت رو جمع کن.",
        "برگشت رو کنترل کن و همزمان کف دست رو به حالت شروع برگردون؛ حرکت نباید ضربه‌ای باشه.",
    ),
    en=(
        "Build a strong hip hinge and keep the torso angle steady; the hand rotation should not "
        "rotate your whole body.",
        "Pull the dumbbells toward the lower ribs while turning the palms smoothly and "
        "naturally; do not force the wrists.",
        "Drive the elbows back and squeeze the back at the top.",
        "Control the return and rotate the palms back to the start without making the movement "
        "jerky.",
    ),
)

_CABLE_PULLDOWN = CuratedSafetyNotes(
    fa=(
        "بالا اجازه بده دست‌ها کامل‌تر برن و لت کش بیاد؛ نصفه برگشتن یعنی نصف کردن یکی از "
        "بهترین بخش‌های حرکت.",
        "سینه رو بالا نگه دار و آرنج‌ها رو پایین و سمت دنده‌ها بکش؛ فقط با دست میله رو "
        "نکش.",
        "میله رو از جلوی بدن سمت بالای سینه بیار؛ پشت گردن نبر.",
        "کمی مایل شدن طبیعیه، ولی هر تکرار خودتو عقب پرت نکن که Pulldown تبدیل به Row بشه.",
    ),
    en=(
        "Let the hands travel higher on the return so the lats can lengthen; cutting the return "
        "short removes one of the most useful parts of the exercise.",
        "Keep the chest lifted and drive the elbows down toward the ribs instead of pulling "
        "the bar with the hands alone.",
        "Bring the bar to the upper chest in front of the body; do not pull it behind the neck.",
        "A small lean is fine, but do not throw yourself backward on every rep and turn the "
        "pulldown into a row.",
    ),
)

_CLOSE_GRIP_LAT_PULLDOWN = CuratedSafetyNotes(
    fa=(
        "بالای حرکت بذار شونه و بازوها بالا برن تا لت واقعاً کش بیاد، ولی وزنه رو ول نکن.",
        "آرنج‌ها رو پایین و سمت لگن بکش؛ تصور کن می‌خوای آرنج رو ببری تو جیب عقب.",
        "سینه رو بالا نگه دار ولی بدنت رو زیاد عقب نبر؛ این حرکت رو قایقی نکن.",
        "دسته رو با جلو بازو جمع نکن؛ مسیر آرنج رو هدایت کن و دست‌ها رو فقط اتصال وزنه بدون.",
    ),
    en=(
        "Let the shoulders and arms rise at the top so the lats can lengthen, while keeping the "
        "weight under control.",
        "Drive the elbows down toward the hips; imagine sending them toward the back pockets.",
        "Keep the chest lifted without leaning far back; do not turn this into a seated row.",
        "Guide the elbow path instead of curling the handle with the biceps; let the hands stay "
        "the connection to the weight.",
    ),
)

_REVERSE_GRIP_LAT_PULLDOWN = CuratedSafetyNotes(
    fa=(
        "گریپ زیر دست رو فقط تا جایی بگیر که مچت راحت باشه؛ مچ رو به عقب نشکن.",
        "آرنج‌ها رو نزدیک‌تر به بدن پایین بکش و دسته رو سمت بالای سینه بیار.",
        "حرکت رو تبدیل به جلو بازو نکن؛ آرنج باید پایین بیاد، نه اینکه فقط دست جمع بشه.",
        "بالا کنترل‌شده کشش لت رو بگیر و اجازه نده وزنه دستت رو ناگهانی بکشه.",
    ),
    en=(
        "Use the underhand grip only as far as your wrists stay comfortable; do not bend them "
        "backward.",
        "Pull the elbows down closer to the body and bring the handle toward the upper chest.",
        "Do not turn the movement into a heavy curl; the elbows should travel down instead of only "
        "the hands closing.",
        "Control the lat stretch at the top and do not let the weight yank the arms upward.",
    ),
)

_WIDE_GRIP_CABLE_LAT_PULLDOWN = CuratedSafetyNotes(
    fa=(
        "دست‌هات رو فقط کمی بازتر از عرض شونه بگیر؛ خیلی باز گرفتن قرار نیست جادویی لت رو "
        "بیشتر درگیر کنه.",
        "بالا اجازه بده لت کامل‌تر کش بیاد و آرنج‌ها صاف‌تر بشن.",
        "میله رو از جلو سمت بالای سینه بکش و آرنج‌ها رو پایین بیار؛ پشت گردن نبر.",
        "بدنت رو با هر تکرار عقب پرت نکن؛ وزنه‌ای بزن که Pulldown همون Pulldown بمونه.",
    ),
    en=(
        "Use a grip only slightly wider than shoulder width; going much wider does not magically "
        "make the lats work more.",
        "Let the lats lengthen at the top and allow the elbows to straighten more fully.",
        "Pull the bar in front of you toward the upper chest and bring the elbows down; do "
        "not pull behind the neck.",
        "Do not throw the torso backward on every rep; choose a weight that keeps the movement a "
        "pulldown.",
    ),
)

_ONE_ARM_LAT_PULLDOWN = CuratedSafetyNotes(
    fa=(
        "بالا دست رو کامل‌تر ببر و بذار لت همون سمت کش بیاد.",
        "آرنج رو پایین و سمت لگن بکش؛ فکر کن آرنج قراره به جیب عقب برسه.",
        "شونه رو موقع کشیدن سمت گوش بالا نبر.",
        "برای چند سانت دامنه بیشتر کل تنه رو نچرخون؛ حرکت اصلی باید از شونه و آرنج بیاد.",
    ),
    en=(
        "Reach the arm higher at the top so the lat on that side can lengthen.",
        "Pull the elbow down toward the hip; imagine sending it toward the back pocket.",
        "Do not let the shoulder rise toward the ear as you pull.",
        "Do not rotate the whole torso for a few extra centimeters; the movement should come "
        "from the "
        "shoulder and elbow.",
    ),
)

_BAND_KNEELING_LAT_PULLDOWN = CuratedSafetyNotes(
    fa=(
        "از همون بالای حرکت روی کش یه مقدار تنش داشته باش؛ شروع کاملاً شل نباشه.",
        "دست رو بالا بده تا لت کش بیاد، بعد آرنج رو سمت لگن پایین بکش.",
        "بدنت رو به پهلو خم نکن که کش پایین بیاد؛ تنه رو محکم نگه دار.",
        "برگشت رو کنترل کن و نذار کش دستت رو ناگهانی بالا بکشه.",
    ),
    en=(
        "Keep some tension in the band at the top; do not start with it completely slack.",
        "Reach the hand upward to lengthen the lat, then pull the elbow down toward the hip.",
        "Do not bend sideways to make the band travel lower; keep the torso firm.",
        "Control the return and do not let the band suddenly pull the hand back up.",
    ),
)

_CABLE_STRAIGHT_ARM_PULLDOWN = CuratedSafetyNotes(
    fa=(
        "آرنج‌ها یه خم خیلی کم داشته باشن و تقریباً همون زاویه رو کل حرکت نگه دار؛ هی آرنج "
        "خم نشه که حرکت پشت‌بازویی بشه.",
        "بالا اجازه بده دست‌ها برن و لت کامل کش بیاد، ولی برای دامنه بیشتر کمرت رو گود "
        "نکن.",
        "فکر کن آرنج‌هات رو توی یه قوس به سمت ران‌ها می‌کشی، نه اینکه فقط میله رو با دست "
        "پایین فشار بدی.",
        "پایین حرکت لت رو جمع کن و بعد کنترل‌شده برگرد؛ وزنه رو رها نکن.",
    ),
    en=(
        "Keep a small bend in the elbows and hold roughly the same angle throughout; do not keep "
        "bending them until the movement becomes a triceps pressdown.",
        "Let the arms travel up so the lats can fully lengthen, but do not arch the lower back for "
        "extra range.",
        "Think about drawing the elbows in an arc toward the thighs instead of simply pressing the "
        "bar down with the hands.",
        "Squeeze the lats at the bottom, then return under control without letting the weight go.",
    ),
)

_STANDARD_PULL_UP = CuratedSafetyNotes(
    fa=(
        "پایین حرکت کامل کشیده شو، ولی شونه‌ها رو بی‌کنترل توی مفصل ول نکن.",
        "سینه رو بالا نگه دار و آرنج‌ها رو پایین بکش؛ فکر نکن فقط باید چونه رو از میله رد کنی.",
        "پا و لگن رو تاب نده؛ اگه برای هر تکرار باید کیپ بزنی، ست دیگه strict نیست.",
        "بالا گردنت رو به زور جلو نبر؛ بدنت رو بالا بکش، نه سرت رو سمت میله.",
    ),
    en=(
        "Reach a full hang at the bottom, but do not let the shoulders drop out of control.",
        "Keep the chest lifted and pull the elbows down; do not focus only on getting the chin "
        "over "
        "the bar.",
        "Keep the legs and hips still; if every rep needs a kip, the set is no longer strict.",
        "Do not crane the neck forward at the top; pull the body up instead of reaching the "
        "head to "
        "the bar.",
    ),
)

_WIDE_GRIP_PULL_UP = CuratedSafetyNotes(
    fa=(
        "دست رو اون‌قدر باز نگیر که دامنه‌ت نصف بشه؛ کمی بازتر از شونه برای اکثر آدم‌ها "
        "کافیه.",
        "پایین حرکت کشش کامل و کنترل‌شده بگیر.",
        "آرنج‌ها رو پایین بکش و سینه رو سمت میله ببر؛ فقط چونه رو جلو نده.",
        "تاب دادن پا و لگن رو حذف کن؛ اگه ست strict نمی‌مونه، تکرار یا سختی رو کم کن.",
    ),
    en=(
        "Do not grip so wide that you lose half the range; a little wider than the shoulders is "
        "enough for most people.",
        "Use a full, controlled stretch at the bottom.",
        "Pull the elbows down and bring the chest toward the bar instead of reaching the "
        "chin forward.",
        "Remove leg and hip swinging; reduce the reps or difficulty if the set cannot stay strict.",
    ),
)

_NEUTRAL_GRIP_CHIN_UP = CuratedSafetyNotes(
    fa=(
        "گریپ خنثی رو محکم بگیر ولی اجازه نده ساعد و جلو بازو کل حرکت رو بدزدن.",
        "آرنج‌ها رو نزدیک بدن پایین بکش و سینه رو بالا نگه دار.",
        "پایین حرکت دست‌ها رو کامل‌تر باز کن تا لت کش بیاد.",
        "پاها رو تاب نده و برای رسیدن بالا گردنت رو جلو نبر.",
    ),
    en=(
        "Hold the neutral grip firmly, but do not let the forearms and biceps take over the whole "
        "rep.",
        "Pull the elbows down close to the body and keep the chest lifted.",
        "Reach the arms more fully at the bottom so the lats can lengthen.",
        "Keep the legs still and do not reach the neck forward to get higher.",
    ),
)

_REVERSE_GRIP_CHIN_UP = CuratedSafetyNotes(
    fa=(
        "گریپ زیر دست رو جوری بگیر که مچت راحت بمونه؛ مچ رو زورکی نشکن.",
        "سینه رو بالا نگه دار و آرنج‌ها رو پایین و عقب بکش.",
        "حرکت رو تبدیل به یه جلو بازوی سنگین نکن؛ بدنت باید با کار پشت بالا بیاد.",
        "پایین حرکت کنترل‌شده کامل‌تر کشیده شو و با ضربه از ته حرکت برنگرد.",
    ),
    en=(
        "Use an underhand grip that keeps the wrists comfortable; do not force them into a bent "
        "position.",
        "Keep the chest lifted and pull the elbows down and back.",
        "Do not turn the exercise into a heavy biceps curl; let the back help lift the body.",
        "Lower into a controlled, fuller stretch and do not bounce out of the bottom.",
    ),
)

_BAND_ASSISTED_PULL_UP = CuratedSafetyNotes(
    fa=(
        "کش رو فقط اون‌قدر قوی انتخاب کن که بتونی تکرارهای تمیز بزنی؛ کش خیلی قوی کل فشار "
        "حرکت رو می‌دزده.",
        "پایین حرکت کامل و کنترل‌شده کشیده شو.",
        "آرنج‌ها رو پایین بکش و سینه رو بالا بیار؛ با پا روی کش بالا نپر.",
        "برگشت رو آروم انجام بده؛ نذار کش تو رو به پایین و بالا پرت کنه.",
    ),
    en=(
        "Choose only enough band assistance for clean reps; a very strong band can take away too "
        "much of the work.",
        "Reach a full, controlled stretch at the bottom.",
        "Pull the elbows down and bring the chest up; do not jump with the legs on the band.",
        "Lower slowly and do not let the band fling you through the movement.",
    ),
)

_BENCH_PULL_UP = CuratedSafetyNotes(
    fa=(
        "از پا فقط به اندازه‌ای کمک بگیر که تکرار تمیز کامل بشه؛ با پا خودتو کامل بالا پرت نکن.",
        "آرنج‌ها رو پایین بکش و اجازه بده پشت بخش اصلی کار رو انجام بده.",
        "پایین حرکت کنترل‌شده کشیده شو و بالا سینه رو سمت میله ببر.",
        "نیمکت باید کاملاً ثابت باشه؛ روی سطح لق یا لغزنده این حرکت رو اجرا نکن.",
    ),
    en=(
        "Use the legs only enough to complete a clean rep; do not launch yourself upward with the "
        "feet.",
        "Pull the elbows down and let the back do most of the work.",
        "Lower into a controlled stretch and bring the chest toward the bar as you rise.",
        "The bench must be completely stable; do not perform this on a loose or slippery surface.",
    ),
)

_COMMANDO_PULL_UP = CuratedSafetyNotes(
    fa=(
        "هر تکرار سرت رو یه سمت میله ببر و سمت‌ها رو منظم عوض کن تا حرکت یک‌طرفه نشه.",
        "آرنج‌ها رو پایین بکش؛ فقط با جلو بازو خودتو جمع نکن.",
        "لگن و دنده‌ها رو تا جای ممکن کنترل کن و حرکت رو تبدیل به پیچش شدید بدن نکن.",
        "با پا کیپ نزن؛ اگه بدون تاب نمی‌رسی بالا، حرکت رو سبک‌تر یا assisted کن.",
    ),
    en=(
        "Take your head to alternating sides of the bar on each rep so the movement does not "
        "become "
        "one-sided.",
        "Pull the elbows down instead of folding yourself up with the biceps alone.",
        "Keep the hips and ribs controlled and do not turn the exercise into a hard body twist.",
        "Do not kip with the legs; use an easier or assisted version if you cannot stay strict.",
    ),
)

_INVERTED_ROW_STRAPS = CuratedSafetyNotes(
    fa=(
        "بدنت از شونه تا پاشنه مثل تخته بمونه؛ باسنت وسط حرکت آویزون نشه.",
        "پایین حرکت بذار کتف‌ها باز بشن و دست‌ها کامل‌تر کشیده بشن.",
        "سینه رو سمت دسته‌ها بکش و بالا کتف‌ها رو جمع کن.",
        "برای سخت‌تر یا آسون‌تر کردن حرکت جای پا رو عوض کن، نه اینکه فرم رو خراب کنی.",
    ),
    en=(
        "Keep the body like a plank from shoulders to heels; do not let the hips sag during the "
        "rep.",
        "Let the shoulder blades spread and the arms reach more fully at the bottom.",
        "Pull the chest toward the handles and squeeze the shoulder blades at the top.",
        "Change the foot position to adjust difficulty instead of changing the form.",
    ),
)

_INVERTED_ROW_CHAIRS = CuratedSafetyNotes(
    fa=(
        "اول مطمئن شو صندلی‌ها واقعاً ثابت و غیرلغزنده‌ان؛ اینجا ایمنی از خود تکرار مهم‌تره.",
        "بدنت رو صاف نگه دار و باسن رو پایین ننداز.",
        "سینه رو به سمت تکیه‌گاه بکش و آرنج‌ها رو عقب ببر.",
        "پایین حرکت کنترل‌شده دست‌ها رو باز کن و با ضربه از پایین برنگرد.",
    ),
    en=(
        "First make sure both chairs are stable and non-slip; here the setup is more important "
        "than "
        "the rep.",
        "Keep the body straight and do not let the hips drop.",
        "Pull the chest toward the supports and drive the elbows back.",
        "Open the arms under control at the bottom and do not bounce out of the stretch.",
    ),
)

_RING_HIGH_ROW = CuratedSafetyNotes(
    fa=(
        "بدنت رو صاف و سفت نگه دار؛ برای رسیدن به رینگ لگن رو جلو عقب نکن.",
        "آرنج‌ها رو بالاتر و بازتر ببر و رینگ‌ها رو سمت بالای دنده‌ها و سینه بکش.",
        "پایین حرکت بذار کتف‌ها از هم فاصله بگیرن و بالا دوباره جمعشون کن.",
        "شونه‌ها رو سمت گوش بالا نکش؛ فشار رو روی پشت میانی نگه دار.",
    ),
    en=(
        "Keep the body straight and braced; do not move the hips back and forth to reach the "
        "rings.",
        "Take the elbows higher and wider and pull the rings toward the upper ribs and chest.",
        "Let the shoulder blades spread at the bottom and bring them together again at the top.",
        "Do not shrug toward the ears; keep the effort in the mid-back.",
    ),
)

_BAND_SEATED_ROW = CuratedSafetyNotes(
    fa=(
        "از همون شروع حرکت روی کش یه مقدار تنش داشته باش؛ کش شل شروع نشه.",
        "آرنج‌ها رو عقب بکش و دست‌ها رو سمت پایین شکم بیار.",
        "بالا پشت رو جمع کن و پایین دوباره اجازه بده کتف‌ها باز بشن.",
        "برگشت رو آروم کن؛ نذار کش دست‌هاتو با ضربه جلو بکشه.",
    ),
    en=(
        "Keep some band tension from the start; do not begin with a completely slack band.",
        "Drive the elbows back and bring the hands toward the lower abdomen.",
        "Squeeze the back at the finish, then let the shoulder blades spread again on the return.",
        "Slow the return and do not let the band snap the hands forward.",
    ),
)

_BAND_STRAIGHT_BACK_ROW = CuratedSafetyNotes(
    fa=(
        "تنه رو صاف و شکم رو سفت نگه دار؛ برای کشیدن کش عقب و جلو تاب نخور.",
        "آرنج‌ها رو نزدیک‌تر به بدن عقب ببر و دست‌ها رو سمت پایین شکم بکش.",
        "تو برگشت کتف‌ها رو کنترل‌شده باز کن تا پشت کش بیاد.",
        "اگه برای رسیدن به انتهای دامنه باید کل بدن رو عقب ببری، مقاومت کش زیادیه.",
    ),
    en=(
        "Keep the torso upright and abs braced; do not rock back and forth to stretch the band.",
        "Drive the elbows closer to the body and pull the hands toward the lower abdomen.",
        "Let the shoulder blades spread under control on the return so the back can lengthen.",
        "If you must lean your whole body back to finish the range, the band resistance is too "
        "high.",
    ),
)

_HYPEREXTENSION = CuratedSafetyNotes(
    fa=(
        "پد رو جوری تنظیم کن که لگنت آزادانه خم بشه؛ پد نباید حرکت Hip Hinge رو قفل کنه.",
        "پایین حرکت کنترل‌شده خم شو و شکمت رو سفت نگه دار؛ یه‌دفعه از کمر آویزون نشو.",
        "بالا فقط تا جایی بیا که تنه با پاهات تقریباً یه خط بشه؛ لازم نیست کمرت رو عقب بشکنی.",
        "وقتی وزن بدن آسون شد می‌تونی بار اضافه کنی، ولی دامنه و کنترل نباید قربانی وزنه بشه.",
    ),
    en=(
        "Set the pad so the hips can hinge freely; it should not block the hip hinge.",
        "Fold down under control with the abs braced; do not hang suddenly from the lower back.",
        "Rise only until the torso is roughly in line with the legs; there is no need to crank the "
        "lower back backward.",
        "Add load only when bodyweight is easy, and do not sacrifice range or control for heavier "
        "weight.",
    ),
)

_LEVER_BACK_EXTENSION = CuratedSafetyNotes(
    fa=(
        "دستگاه رو با محور حرکت بدنت تنظیم کن؛ تنظیم بد دستگاه می‌تونه کل حرکت رو بدقواره کنه.",
        "شکم رو سفت کن و حرکت رو آروم از خم به حالت خنثی برگردون.",
        "بالای حرکت بیش‌ازحد عقب نرو؛ صاف شدن کافیه، Hyperextension شدید لازم نیست.",
        "اگه برای حرکت دادن دستگاه مجبور شدی ضربه بزنی، وزنه زیادی سنگینه.",
    ),
    en=(
        "Align the machine with your body's movement axis; a poor setup can distort the whole "
        "exercise.",
        "Brace the abs and slowly return from the flexed position to neutral.",
        "Do not lean excessively backward at the top; returning to straight is enough.",
        "If you have to jerk the machine to move it, the weight is too heavy.",
    ),
)

_SMITH_MACHINE_DEADLIFT = CuratedSafetyNotes(
    fa=(
        "قبل از جدا کردن میله شکمت رو سفت کن و میله رو نزدیک بدن نگه دار.",
        "لگن و زانوها رو هماهنگ باز کن؛ وزنه رو با گرد کردن کمر از پایین نکش.",
        "بالا با باسن قفل کن، نه با پرت کردن لگن جلو و خم کردن کمر به عقب.",
        "اگه کمرت وسط تکرار شروع به گرد شدن می‌کنه، وزنه یا دامنه رو کم کن.",
    ),
    en=(
        "Brace before lifting the bar and keep it close to the body.",
        "Open the hips and knees together; do not pull the weight from the floor with a rounded "
        "back.",
        "Finish by locking out with the glutes, not by thrusting the hips forward and leaning the "
        "lower back backward.",
        "Reduce the load or range if the lower back starts rounding during the rep.",
    ),
)

_ROPE_LAT_PULLDOWN = CuratedSafetyNotes(
    fa=(
        "بالای حرکت دست‌ها و طناب رو کنترل‌شده بالا ببر تا لت کش بیاد؛ وزنه نباید دست‌ها رو پرت کنه.",
        "آرنج‌ها رو پایین و کمی عقب بکش و شونه‌ها رو از گوش دور نگه دار.",
        "تنه رو تقریباً ثابت نگه دار؛ با عقب کشیدن بدن مسیر طناب رو عوض نکن.",
        "پایین حرکت دستگیره‌ها رو کنار دنده‌ها بیار و بعد بدون ضربه برگردون.",
    ),
    en=(
        "Let the hands and rope rise under control so the lats can lengthen; do not let the weight "
        "throw the arms overhead.",
        "Pull the elbows down and slightly back while keeping the shoulders away from the ears.",
        "Keep the torso mostly still instead of leaning back to change the rope's path.",
        "Bring the rope ends beside the ribs at the bottom, then return without a jerk.",
    ),
)

_WIDE_NEUTRAL_LAT_PULLDOWN = CuratedSafetyNotes(
    fa=(
        "گریپ خنثی رو جوری بگیر که مچ‌ها در امتداد ساعد راحت بمونن؛ دسته رو به زور نچرخون.",
        "آرنج‌ها رو پایین و سمت دنده‌های پایین بکش و سینه رو بالا نگه دار.",
        "بالا اجازه بده دست‌ها کشیده‌تر بشن تا لت کش بیاد، ولی شونه‌ها رو بی‌کنترل رها نکن.",
        "تنه رو فقط کمی مایل کن و با تاب دادن بدن چند سانت دامنه اضافه نساز.",
    ),
    en=(
        "Use a neutral grip that keeps the wrists comfortably aligned with the forearms; do not "
        "force the handles to rotate.",
        "Pull the elbows down toward the lower ribs while keeping the chest lifted.",
        "Let the arms lengthen more at the top so the lats can stretch, without dropping the "
        "shoulders out of control.",
        "Use only a small torso lean and do not create extra range by swinging the body.",
    ),
)

_CLOSE_OVERHAND_LAT_PULLDOWN = CuratedSafetyNotes(
    fa=(
        "گریپ رو جوری بگیر که مچ و شونه‌هات راحت باشن؛ میله رو فقط به خاطر اسم حرکت زورکی "
        "نزدیک نکن.",
        "آرنج‌ها رو پایین و کمی عقب ببر و میله رو سمت بالای سینه بکش.",
        "سینه رو بالا نگه دار و نذار با عقب خم شدن زیاد، حرکت تبدیل به Row بشه.",
        "بالا برگشت رو آهسته انجام بده و اجازه بده لت کش بیاد، بدون اینکه وزنه دستت رو بکشه.",
    ),
    en=(
        "Choose a grip that keeps the wrists and shoulders comfortable; do not force a close path "
        "just because of the exercise name.",
        "Drive the elbows down and slightly back and pull the bar toward the upper chest.",
        "Keep the chest lifted and do not turn the pulldown into a row by leaning far backward.",
        "Take the return slowly and let the lats lengthen without letting the weight yank the "
        "arms.",
    ),
)

_LAT_PULLDOWN_VARIATIONS = CuratedSafetyNotes(
    fa=(
        "قبل از ست نوع دسته و گریپ همون نسخه رو مشخص کن؛ وسط تکرارها مسیر رو عوض نکن.",
        "در هر نسخه آرنج‌ها رو به سمت پایین هدایت کن و اجازه نده حرکت با تاب تنه جلو بره.",
        "بالا دامنه رو کنترل‌شده کامل‌تر کن تا لت کش بیاد، بدون اینکه شونه‌ها بی‌ثبات بشن.",
        "اگه فقط با تاب بدن یا جلو بازو تکرار کامل میشه، سختی یا وزنه رو کم کن.",
    ),
    en=(
        "Choose the handle and grip for the variation before the set; do not change the path "
        "mid-rep.",
        "In every variation, guide the elbows down and do not let torso momentum drive the rep.",
        "Use a controlled fuller return so the lats can lengthen without losing shoulder control.",
        "If the rep only works with body swing or biceps, reduce the difficulty or weight.",
    ),
)

_DUMBBELL_PULLOVER = CuratedSafetyNotes(
    fa=(
        "آرنج‌ها رو کمی خم نگه دار و زاویه‌شون رو وسط حرکت هی عوض نکن.",
        "دمبل رو فقط تا جایی پشت سر ببر که دنده‌ها و کمرت کنترل بمونن؛ برای دامنه بیشتر کمرت "
        "رو گود نکن.",
        "دمبل رو با یه قوس از پشت سر به بالای سینه برگردون و فشار رو از لت بگیر، نه با باز و "
        "بسته کردن آرنج.",
        "دامنه‌ای رو انتخاب کن که شونه‌هات راحت بمونن؛ پایین حرکت مکث و ضربه نزن.",
    ),
    en=(
        "Keep a slight bend in the elbows and do not keep changing that angle during the rep.",
        "Lower the dumbbell behind the head only as far as you can control the ribs and lower "
        "back; "
        "do not arch for extra range.",
        "Bring the dumbbell back over the chest in an arc and use the lats instead of repeatedly "
        "opening and closing the elbows.",
        "Use a shoulder-comfortable range and do not bounce or jerk at the bottom.",
    ),
)

_STANDING_CABLE_ROW = CuratedSafetyNotes(
    fa=(
        "پاها رو محکم بکار و شکمت رو سفت کن تا کابل تو رو جلو نکشه.",
        "میله رو با عقب بردن آرنج‌ها سمت پایین سینه و بالای شکم بکش؛ فقط دست‌ها رو خم نکن.",
        "تو برگشت اجازه بده کتف‌ها کنترل‌شده جلو برن، ولی تنه و کمرت جمع نشه.",
        "برای جابه‌جا کردن وزنه به عقب و جلو تاب نخور؛ اگه لازم شد مقاومت رو کم کن.",
    ),
    en=(
        "Set a stable stance and brace the abs so the cable does not pull you forward.",
        "Pull the bar toward the lower chest and upper abdomen by driving the elbows back, not by "
        "only bending the hands.",
        "Let the shoulder blades reach forward under control on the return without collapsing the "
        "torso or lower back.",
        "Do not rock back and forth to move the weight; reduce the resistance if you need to.",
    ),
)

_SEATED_HIGH_CABLE_ROPE_ROW = CuratedSafetyNotes(
    fa=(
        "سینه رو بالا و تنه رو ثابت نگه دار و طناب رو سمت بالای سینه بکش.",
        "آرنج‌ها رو کمی باز و بالا ببر؛ آخر حرکت کتف‌ها رو جمع کن، نه اینکه شونه‌ها رو بالا بندازی.",
        "تو برگشت دست‌ها رو کنترل‌شده جلو بده تا پشت دوباره کش بیاد.",
        "برای رسیدن طناب به سینه عقب پرت نشو؛ مسیر رو با آرنج‌ها بساز.",
    ),
    en=(
        "Keep the chest lifted and torso steady while pulling the rope toward the upper chest.",
        "Take the elbows slightly out and up; squeeze the shoulder blades at the finish instead of "
        "shrugging.",
        "Reach the hands forward under control on the return so the back can lengthen again.",
        "Do not throw the body backward to bring the rope to the chest; create the path with the "
        "elbows.",
    ),
)

_SEATED_HIGH_ROW = CuratedSafetyNotes(
    fa=(
        "سینه رو بالا و تنه رو ثابت نگه دار؛ دسته رو با عقب پرت کردن بدن نکش.",
        "آرنج‌ها رو عقب و کمی باز ببر و دسته رو سمت بالای سینه هدایت کن.",
        "بالا کتف‌ها رو جمع کن، ولی شونه‌ها رو سمت گوش بالا ننداز.",
        "تو برگشت دامنه رو کنترل کن و بذار کتف‌ها دوباره از هم فاصله بگیرن.",
    ),
    en=(
        "Keep the chest up and torso steady; do not use a backward body throw to move the handle.",
        "Take the elbows back and slightly out and guide the handle toward the upper chest.",
        "Squeeze the shoulder blades at the top without shrugging toward the ears.",
        "Control the return and let the shoulder blades move apart again.",
    ),
)

_DUMBBELL_HIGH_ROW = CuratedSafetyNotes(
    fa=(
        "از لگن خم شو و زاویه تنه رو ثابت نگه دار؛ ستون فقراتت رو خنثی و شکمت رو سفت نگه دار.",
        "آرنج‌ها رو باز و عقب ببر و دمبل‌ها رو سمت دنده‌های بالایی بکش، نه مستقیم سمت شونه‌ها.",
        "پایین حرکت دمبل‌ها رو کنترل‌شده پایین ببر و اجازه بده پشت بالا کمی کش بیاد.",
        "برای بالا آوردن دمبل‌ها تنه رو پرت نکن؛ اگه لازم شد وزنه رو سبک‌تر کن.",
    ),
    en=(
        "Hinge from the hips and keep the torso angle steady with a neutral spine and braced abs.",
        "Drive the elbows out and back and pull the dumbbells toward the upper ribs rather than "
        "straight toward the shoulders.",
        "Lower the dumbbells under control and let the upper back lengthen slightly at the bottom.",
        "Do not throw the torso to raise the dumbbells; reduce the weight if needed.",
    ),
)

_CABLE_UPRIGHT_ROW = CuratedSafetyNotes(
    fa=(
        "میله رو نزدیک بدن بالا بکش و فقط تا ارتفاعی برو که شونه‌هات راحت می‌مونن؛ لازم نیست "
        "آرنج‌ها خیلی بالاتر از شونه برن.",
        "مچ‌ها رو صاف نگه دار و موقع بالا کشیدن شونه‌ها رو سمت گوش نبر.",
        "تنه رو ثابت نگه دار و برای بالا آوردن میله تاب نخور.",
        "اگه جلوی شونه گیر می‌کنه یا حس ناپایداری داری، دامنه و وزنه رو کم کن.",
    ),
    en=(
        "Keep the bar close and raise it only as high as your shoulders stay comfortable; the "
        "elbows do not need to go far above the shoulders.",
        "Keep the wrists straight and do not shrug toward the ears as you lift.",
        "Keep the torso steady and do not swing to raise the bar.",
        "Reduce the range and weight if the front of the shoulder catches or feels unstable.",
    ),
)

_CONFLICTING_PULL_UP = CuratedSafetyNotes(
    fa=(
        "قبل از اجرا فریم و هویت حرکت رو چک کن؛ اگر حرکت Pull-Up نیست، این نکات رو روی نسخه "
        "دیگه‌ای اعمال نکن.",
        "اگر نسخه Pull-Up اجرا می‌کنی، پایین حرکت با شونه‌های درگیر کنترل‌شده کشیده شو.",
        "آرنج‌ها رو پایین بکش و سینه رو بالا بیار؛ گردنت رو جلو نبر.",
        "کیپ و چرخش شدید بدن نداشته باش؛ اگه فرم ثابت نمی‌مونه، حرکت رو assisted یا سبک‌تر کن.",
    ),
    en=(
        "Check the video frame and exercise identity before starting; do not apply these cues to a "
        "different movement.",
        "If the movement is a pull-up, use a controlled hang at the bottom with the shoulders "
        "engaged.",
        "Pull the elbows down and bring the chest up instead of reaching the neck forward.",
        "Do not kip or twist hard; use an assisted or easier version if you cannot stay "
        "controlled.",
    ),
)

_BACK_WORKOUT_COMPILATION = CuratedSafetyNotes(
    fa=(
        "قبل از هر ست مشخص کن دقیقاً کدوم بخش و کدوم حرکت رو اجرا می‌کنی؛ این ویدیو یک حرکت "
        "واحد نیست.",
        "برای هر حرکت مسیر واقعی آرنج و کتف همون حرکت رو دنبال کن؛ یک فرم ثابت رو به همه "
        "بخش‌ها تحمیل نکن.",
        "هر بار که دستگاه یا کابل عوض میشه، صندلی و مسیر حرکت رو دوباره تنظیم و چک کن.",
        "فقط بخش‌هایی رو اجرا کن که هویت و مسیرشون واضح و قابل کنترل باشه؛ فریم مبهم رو تقلید نکن.",
    ),
    en=(
        "Identify the exact section and exercise before each set; this video is not one single "
        "movement.",
        "Follow the actual elbow and scapular path of each exercise instead of applying one "
        "form to "
        "every section.",
        "Recheck the seat, machine, and cable path whenever the setup changes.",
        "Perform only sections with a clear, controllable identity and path; do not imitate an "
        "unclear frame.",
    ),
)


CURATED_BACK_SAFETY_NOTES: dict[str, CuratedSafetyNotes] = {
    "barbell-bent-over-row": _BARBELL_BENT_OVER_ROW,
    "owner-e0c26a271aac-barbell-bent-over-row": _BARBELL_BENT_OVER_ROW,
    "fedb-0027-barbell-underhand-bent-over-row": _BARBELL_UNDERHAND_ROW,
    "fedb-0208-seated-cable-row-v-grip": _SEATED_CABLE_ROW_V_GRIP,
    "owner-2a5de4dc7ba3-seated-cable-row": _SEATED_CABLE_ROW_V_GRIP,
    "owner-1228b1ee2349-seated-cable-row-close-neutral-grip": _SEATED_CABLE_ROW_V_GRIP,
    "fedb-0218-seated-cable-row-wide-grip": _SEATED_CABLE_ROW_WIDE_GRIP,
    "fedb-0213-cable-seated-high-row-v-bar": _CABLE_SEATED_HIGH_ROW,
    "fedb-0581-lever-high-row": _LEVER_HIGH_ROW,
    "chest-supported-row": _CHEST_SUPPORTED_ROW,
    "fedb-0327-dumbbell-incline-row": _DUMBBELL_INCLINE_ROW,
    "owner-196c37935776-dumbbell-chest-supported-row": _DUMBBELL_INCLINE_ROW,
    "owner-802adbd216bf-incline-dumbbell-row": _DUMBBELL_INCLINE_ROW,
    "fedb-1330-dumbbell-hammer-grip-incline-bench-row": _DUMBBELL_HAMMER_INCLINE_ROW,
    "fedb-0248-cambered-bar-lying-row": _CAMBERED_LYING_ROW,
    "fedb-0293-dumbbell-bent-over-row": _DUMBBELL_BENT_OVER_ROW,
    "single-arm-cable-row": _SINGLE_ARM_CABLE_ROW,
    "fedb-0861-cable-one-arm-twisting-seated-row": _TWISTING_SEATED_ROW,
    "fedb-drv-lever-t-bar-row-lever-t-bar-row": _LEVER_T_BAR_ROW,
    "fedb-1349-lever-reverse-t-bar-row": _LEVER_REVERSE_T_BAR_ROW,
    "fedb-1328-dumbbell-lying-rear-delt-row": _DUMBBELL_REAR_DELT_ROW,
    "fedb-1329-dumbbell-palm-rotational-bent-over-row": _DUMBBELL_ROTATIONAL_ROW,
    "fedb-0198-cable-pulldown": _CABLE_PULLDOWN,
    "owner-0a8f98e8fb45-lat-pulldown": _CABLE_PULLDOWN,
    "owner-3838601de93e-seated-cable-lat-pulldown": _CABLE_PULLDOWN,
    "fedb-0974-cable-close-grip-lat-pulldown": _CLOSE_GRIP_LAT_PULLDOWN,
    "owner-69f576423434-close-grip-lat-pulldown": _CLOSE_GRIP_LAT_PULLDOWN,
    "owner-985a6b89a33a-seated-close-grip-cable-lat-pulldown": _CLOSE_GRIP_LAT_PULLDOWN,
    "owner-435983d4e255-close-neutral-lat-pulldown-lower-lats": _CLOSE_GRIP_LAT_PULLDOWN,
    "owner-435983d4e255-close-neutral-grip-lat-pulldown-lower-lats": _CLOSE_GRIP_LAT_PULLDOWN,
    "fedb-0207-reverse-grip-cable-lat-pulldown": _REVERSE_GRIP_LAT_PULLDOWN,
    "fedb-0673-reverse-grip-machine-lat-pulldown": _REVERSE_GRIP_LAT_PULLDOWN,
    "owner-2be5b59c8936-underhand-lat-pulldown-entire-lats": _REVERSE_GRIP_LAT_PULLDOWN,
    (
        "fedb-drv-cable-bar-lateral-pulldown-wide-shoulder-grip-"
        "wide-grip-cable-lat-pulldown"
    ): _WIDE_GRIP_CABLE_LAT_PULLDOWN,
    "owner-68e61505aafd-wide-overhand-lat-pulldown-upper-lats": _WIDE_GRIP_CABLE_LAT_PULLDOWN,
    "owner-a4a25c322a76-wide-neutral-grip-lat-pulldown-entire-lats": _WIDE_NEUTRAL_LAT_PULLDOWN,
    "owner-da3c8c259901-close-overhand-lat-pulldown-lower-lats": _CLOSE_OVERHAND_LAT_PULLDOWN,
    "fedb-2616-cable-one-arm-lateral-pulldown": _ONE_ARM_LAT_PULLDOWN,
    "fedb-0983-band-kneeling-one-arm-pulldown": _BAND_KNEELING_LAT_PULLDOWN,
    "fedb-0238-cable-straight-arm-pulldown": _CABLE_STRAIGHT_ARM_PULLDOWN,
    "cable-pullover": _CABLE_STRAIGHT_ARM_PULLDOWN,
    "owner-e94b2c4b4eaa-cable-bent-over-straight-arm-pulldown": _CABLE_STRAIGHT_ARM_PULLDOWN,
    "owner-1762510e543b-seated-cable-rope-pulldown": _ROPE_LAT_PULLDOWN,
    "owner-1762510e543b-seated-cable-rope-pullover": _ROPE_LAT_PULLDOWN,
    "owner-6870f0f21141-seated-rope-cable-lat-pulldown": _ROPE_LAT_PULLDOWN,
    "owner-7a5d1aac09bf-lat-pulldown-variations": _LAT_PULLDOWN_VARIATIONS,
    "owner-7229b1ea15b7-dumbbell-pullover": _DUMBBELL_PULLOVER,
    "fedb-0651-shoulder-width-pull-up": _STANDARD_PULL_UP,
    "fedb-drv-chin-ups-pull-ups-pull-up-chin-up": _STANDARD_PULL_UP,
    "fedb-1429-pull-up-wide-grip": _WIDE_GRIP_PULL_UP,
    "fedb-0253-chin-ups-narrow-parallel-grip": _NEUTRAL_GRIP_CHIN_UP,
    "fedb-2327-reverse-grip-pull-up": _REVERSE_GRIP_CHIN_UP,
    "fedb-2987-close-grip-chin-up": _REVERSE_GRIP_CHIN_UP,
    "fedb-0970-band-assisted-pull-up": _BAND_ASSISTED_PULL_UP,
    "fedb-0570-bench-pull-up": _BENCH_PULL_UP,
    "fedb-drv-commando-pull-up-commando-pull-up": _COMMANDO_PULL_UP,
    "fedb-0498-inverted-row-with-straps": _INVERTED_ROW_STRAPS,
    "fedb-0499-inverted-row-between-chairs": _INVERTED_ROW_CHAIRS,
    "fedb-drv-ring-high-row-ring-high-row": _RING_HIGH_ROW,
    "fedb-0990-band-seated-row": _BAND_SEATED_ROW,
    "fedb-3144-band-straight-back-seated-row": _BAND_STRAIGHT_BACK_ROW,
    "fedb-0489-45-degree-hyperextension": _HYPEREXTENSION,
    "fedb-0573-lever-back-extension": _LEVER_BACK_EXTENSION,
    "fedb-0752-smith-machine-deadlift": _SMITH_MACHINE_DEADLIFT,
    "owner-b7ab76b15fd4-standing-cable-row-with-straight-bar": _STANDING_CABLE_ROW,
    "owner-b7ab76b15fd4-cable-bent-over-row": _STANDING_CABLE_ROW,
    "owner-baf4e3c97566-seated-high-cable-rope-row": _SEATED_HIGH_CABLE_ROPE_ROW,
    "owner-91d806ba40f4-seated-high-row": _SEATED_HIGH_ROW,
    "owner-a0d34387c231-bent-over-dumbbell-high-row": _DUMBBELL_HIGH_ROW,
    "owner-d111c927f0e6-cable-upright-row": _CABLE_UPRIGHT_ROW,
    "owner-d111c927f0e6-cable-bent-over-row": _CABLE_UPRIGHT_ROW,
    (
        "owner-d11b62b4dd71-shoulder-width-pull-up-dumbbell-front-raise-"
        "conflicting-frames"
    ): _CONFLICTING_PULL_UP,
    "owner-3a346817b851-back-workout-compilation": _BACK_WORKOUT_COMPILATION,
}

CURATED_SAFETY_NOTES.update(CURATED_BACK_SAFETY_NOTES)


_SHOULDER_DUMBBELL_LATERAL_RAISE = CuratedSafetyNotes(
    fa=(
        (
            'آرنج رو حرکت بده، نه دمبل رو؛ دست فقط وزنه رو نگه می‌داره و آرنج باید '
            'مسیر حرکت رو هدایت کنه.'
        ),
        (
            'بازو رو یه ذره جلوتر از خط کاملاً کنار بدن بالا ببر؛ این مسیر برای '
            'خیلی‌ها طبیعی‌تره و شونه راحت‌تر حرکت می‌کنه.'
        ),
        (
            'شست رو زورکی سمت زمین نچرخون؛ کف دست تقریباً خنثی بمونه و نذار حرکت '
            'تبدیل به «خالی کردن پارچ آب» بشه.'
        ),
        (
            'اگه برای بالا بردن دمبل شونه‌هاتو تا گوش بالا می‌کشی یا تنه رو تاب میدی، '
            'وزنه زیادی سنگینه.'
        ),
        (
            'بالا رفتن مهمه، ولی پایین اومدن رو مفت از دست نده؛ دمبل رو کنترل‌شده '
            'برگردون.'
        ),
    ),
    en=(
        (
            'Lead the movement with the elbows rather than thinking about lifting the '
            'dumbbells with the hands.'
        ),
        (
            'Raise the arms slightly forward of a perfectly lateral line if that '
            'matches a comfortable natural shoulder path.'
        ),
        (
            'Do not aggressively turn the thumbs downward; keep a mostly neutral hand '
            'position rather than using an exaggerated pouring position.'
        ),
        (
            'If the shoulders shrug toward the ears or the torso has to swing, the '
            'load is too heavy for a clean lateral raise.'
        ),
        'Control the eccentric instead of simply dropping the dumbbells.',
    ),
)

_SHOULDER_ONE_ARM_DUMBBELL_LATERAL_RAISE = CuratedSafetyNotes(
    fa=(
        (
            'با دست آزاد یه جای ثابت رو بگیر؛ ثبات بیشتر یعنی لازم نیست با کل بدن '
            'دمبل رو پرت کنی بالا.'
        ),
        'آرنج رو بیرون و یه ذره جلو هدایت کن؛ دست و مچ دنبال آرنج بیان.',
        (
            'لگن رو هر تکرار به یه سمت پرت نکن؛ اگه lean می‌دی، زاویه‌اش رو ثابت نگه '
            'دار.'
        ),
        (
            'پایین حرکت عجله نکن؛ برگشت کنترل‌شده همون جاییه که خیلیا کل فشار حرکت رو '
            'دور می‌ریزن.'
        ),
    ),
    en=(
        (
            'Hold a stable support with the free hand; extra stability means you do '
            'not need to throw the dumbbell up with your whole body.'
        ),
        (
            'Guide the elbow out and slightly forward, with the hand and wrist '
            'following the elbow.'
        ),
        (
            'Do not toss the hip to one side on every rep; if you use a lean, keep '
            'its angle consistent.'
        ),
        (
            'Do not rush the bottom; the controlled return is where many people give '
            'away the tension.'
        ),
    ),
)

_SHOULDER_SEATED_DUMBBELL_LATERAL_RAISE = CuratedSafetyNotes(
    fa=(
        (
            'نشسته بودن یعنی تقلب با پا و لگن کمتر؛ پس اگه هنوز داری دمبل رو پرت '
            'می‌کنی، وزنه رو کم کن.'
        ),
        'آرنج‌ها رو هدایت کن و دست‌ها رو یه ذره جلوتر از خط بدن بالا بیار.',
        (
            'شونه رو تا گوش بالا نکش؛ بازو باید بالا بره، نه اینکه کل کمربند شانه‌ای '
            'فقط شراگ کنه.'
        ),
        'دمبل رو پایین ننداز؛ قسمت منفی رو کنترل کن تا هر تکرار واقعاً حساب بشه.',
    ),
    en=(
        (
            'Sitting reduces leg and hip cheating, so lower the load if you are still '
            'throwing the dumbbells up.'
        ),
        (
            'Lead with the elbows and raise the hands slightly forward of the body '
            'line.'
        ),
        (
            'Do not hike the shoulders toward the ears; the arms should rise instead '
            'of turning the rep into a shrug.'
        ),
        'Do not drop the dumbbells; control the eccentric so every rep counts.',
    ),
)

_SHOULDER_CABLE_LATERAL_RAISE = CuratedSafetyNotes(
    fa=(
        (
            'اون‌قدر از دستگاه فاصله بگیر که پایین حرکت هم کابل هنوز کشش داشته باشه؛ '
            'شروع کاملاً شل یعنی بخشی از حرکت رو مفت از دست دادی.'
        ),
        (
            'به‌جای فکر کردن به بالا بردن دسته، فکر کن دستت رو داری از بدنت دور '
            'می‌کنی.'
        ),
        (
            'آرنج مسیر حرکت رو هدایت کنه و مچ فقط دنبالش بیاد؛ دسته رو با دست بالا '
            'نکش.'
        ),
        'تنه رو ثابت نگه دار و اجازه نده هر تکرار تبدیل به یه تاب کامل بدن بشه.',
        (
            'برگشت رو آروم انجام بده و بذار سرشانه کناری تا پایین حرکت زیر فشار '
            'بمونه.'
        ),
    ),
    en=(
        (
            'Stand far enough from the machine to keep the cable loaded at the '
            'bottom; a completely slack start gives away part of the movement.'
        ),
        (
            'Instead of thinking about lifting the handle, think about moving your '
            'hand away from your body.'
        ),
        (
            'Let the elbow lead and the wrist follow; do not lift the handle by '
            'pulling with the hand.'
        ),
        'Keep the torso steady and do not let every rep become a full-body swing.',
        (
            'Take the return slowly so the lateral delt stays loaded down to the '
            'bottom.'
        ),
    ),
)

_SHOULDER_ONE_ARM_CABLE_LATERAL_RAISE = CuratedSafetyNotes(
    fa=(
        (
            'پولی پایین باشه و از دستگاه اون‌قدر فاصله بگیر که از همون شروع حرکت کابل '
            'کشش داشته باشه.'
        ),
        (
            'دست می‌تونه پایین حرکت کمی جلوی بدن یا به سمت طرف مقابل بره تا دامنه '
            'کشیده‌تری بگیری، ولی فقط تا جایی که شونه راحت باشه.'
        ),
        'آرنج رو بیرون ببر؛ دسته نباید رهبر حرکت باشه.',
        (
            'بدنت رو برای هر تکرار به طرف مخالف پرت نکن؛ مقاومت رو جوری انتخاب کن که '
            'تنه تقریباً ثابت بمونه.'
        ),
    ),
    en=(
        (
            'Keep the pulley low and stand far enough away that the cable has tension '
            'from the start.'
        ),
        (
            'At the bottom, the hand can sit slightly in front of the body or toward '
            'the opposite side for a longer stretch, but only while the shoulder '
            'stays comfortable.'
        ),
        'Move the elbow outward; the handle should not lead the raise.',
        (
            'Do not throw the body toward the opposite side on each rep; choose '
            'resistance that lets the torso stay almost still.'
        ),
    ),
)

_SHOULDER_LEVER_LATERAL_RAISE = CuratedSafetyNotes(
    fa=(
        (
            'صندلی رو جوری تنظیم کن که محور دستگاه تقریباً با مفصل شونه‌ت هم‌راستا '
            'باشه؛ تنظیم بد دستگاه می‌تونه کل مسیر حرکت رو خراب کنه.'
        ),
        'فشار رو با آرنج‌ها به پد بده؛ به دست‌ها و گرفتن دسته‌ها وابسته نشو.',
        'شونه‌هات رو سمت گوش بالا نبر؛ آرنج‌ها باید از پهلو بالا برن.',
        (
            'پایین حرکت وزنه‌ها رو به هم نکوب؛ قبل از اینکه استک کامل آزاد بشه تکرار '
            'بعدی رو شروع کن تا فشار قطع نشه.'
        ),
    ),
    en=(
        (
            'Set the seat so the machine axis is roughly aligned with your shoulder '
            'joint; a poor setup can distort the whole path.'
        ),
        (
            'Drive the pads with the elbows rather than relying on the hands and '
            'handles.'
        ),
        (
            'Do not hike the shoulders toward the ears; let the elbows rise from the '
            'sides.'
        ),
        (
            'Do not let the stack slam at the bottom; start the next rep before the '
            'stack fully unloads so tension stays on.'
        ),
    ),
)

_SHOULDER_IRON_CROSS = CuratedSafetyNotes(
    fa=(
        (
            'دمبل سبک بردار؛ بازوی بلند تو این حرکت حتی وزنه کم رو هم خیلی سنگین '
            'می‌کنه.'
        ),
        (
            'اول با پاها و باز شدن لگن از اسکوات بلند شو؛ دمبل رو با تاب کمر و شونه '
            'بالا نبر.'
        ),
        (
            'وقتی به حالت ایستاده رسیدی، آرنج‌ها رو نرم نگه دار و بازوها رو به طرفین '
            'باز کن؛ مچ فقط دنبال آرنج بیاد.'
        ),
        (
            'شونه‌ها رو سمت گوش جمع نکن و هر تکرار رو با کنترل به اسکوات برگردون؛ این '
            'حرکت جای پرت کردن دمبل با مومنتوم نیست.'
        ),
    ),
    en=(
        (
            'Use light dumbbells; the long lever makes even a small load demanding in '
            'this movement.'
        ),
        (
            'Rise from the squat with the legs and hips first; do not lift the '
            'dumbbells by swinging the back and shoulders.'
        ),
        (
            'Once you are standing, keep the elbows soft and open the arms to the '
            'sides, with the wrists following the elbows.'
        ),
        (
            'Do not bunch the shoulders toward the ears, and return to the squat '
            'under control; this is not a movement for throwing the dumbbells with '
            'momentum.'
        ),
    ),
)

_SHOULDER_BARBELL_WIDE_GRIP_UPRIGHT_ROW = CuratedSafetyNotes(
    fa=(
        (
            'گریپ رو نسبتاً باز نگه دار؛ این حرکت با دست خیلی جمع معمولاً بیشتر جلو '
            'بازو و موقعیت بدتری برای شونه می‌سازه.'
        ),
        'آرنج‌ها رو بالا و بیرون هدایت کن و میله رو نزدیک بدن نگه دار.',
        (
            'لازم نیست میله رو تا زیر چونه بکشی؛ حوالی پایین سینه تا ارتفاعی که شونه '
            'راحت و آرنج‌ها نزدیک خط شونه‌ان کافیه.'
        ),
        (
            'اگه بالای حرکت جلوی شونه نیشگون یا درد می‌گیره، دامنه رو کوتاه کن؛ برای '
            'چند سانت بیشتر زور نزن.'
        ),
    ),
    en=(
        (
            'Use a relatively wide grip; taking the hands very close often shifts '
            'more work to the biceps and creates a less comfortable shoulder '
            'position.'
        ),
        'Guide the elbows up and out while keeping the bar close to the body.',
        (
            'You do not need to pull the bar under the chin; stop around the lower '
            'chest or wherever the shoulders stay comfortable and the elbows approach '
            'shoulder height.'
        ),
        (
            'If the front of the shoulder pinches or hurts at the top, shorten the '
            'range instead of forcing a few extra centimeters.'
        ),
    ),
)

_SHOULDER_DUMBBELL_UPRIGHT_ROW = CuratedSafetyNotes(
    fa=(
        (
            'دمبل‌ها رو مجبور نکن مثل هالتر تو یه خط ثابت حرکت کنن؛ بذار هر دست مسیر '
            'طبیعی خودش رو داشته باشه.'
        ),
        'آرنج‌ها رو بالا و بیرون ببر، ولی لازم نیست خیلی بالاتر از شونه برن.',
        'دمبل رو نزدیک بدن نگه دار و با مچ نکش بالا.',
        (
            'اگه برای رسیدن به بالا شونه درد می‌گیره یا باید مچ رو بد بچرخونی، دامنه '
            'رو همون‌جا تموم کن.'
        ),
    ),
    en=(
        (
            'Do not force the dumbbells to travel like a barbell on one fixed line; '
            'let each hand find its natural path.'
        ),
        (
            'Lift the elbows up and out, but they do not need to rise far above the '
            'shoulders.'
        ),
        (
            'Keep the dumbbells close to the body and do not pull them up with the '
            'wrists.'
        ),
        (
            'If the shoulder hurts near the top or the wrists need an awkward turn, '
            'end the range there.'
        ),
    ),
)

_SHOULDER_DUMBBELL_FRONT_RAISE = CuratedSafetyNotes(
    fa=(
        (
            'دمبل رو با تاب لگن شروع نکن؛ شکم رو سفت کن و بذار سرشانه جلویی خودش وزنه '
            'رو بلند کنه.'
        ),
        (
            'آرنج یه خم نرم داشته باشه و دمبل رو تقریباً تا ارتفاع شونه بالا بیار؛ '
            'لازم نیست هر تکرار بالای سرت بره.'
        ),
        (
            'گریپ خنثی یا شست کمی رو به بالا برای خیلی‌ها حس بهتری روی شونه می‌ده؛ مچ '
            'رو زورکی نچرخون.'
        ),
        'پایین آوردن رو کنترل کن؛ نذار دمبل آزاد روی ران سقوط کنه.',
    ),
    en=(
        (
            'Do not start the raise with a hip swing; brace the torso and let the '
            'front delt lift the weight.'
        ),
        (
            'Keep a soft elbow bend and raise the dumbbells roughly to shoulder '
            'height; they do not need to go overhead on every rep.'
        ),
        (
            'A neutral grip or slightly raised thumb position feels better for many '
            'shoulders; do not force the wrists to rotate.'
        ),
        (
            'Control the descent instead of letting the dumbbells fall onto the '
            'thighs.'
        ),
    ),
)

_SHOULDER_SEATED_DUMBBELL_FRONT_RAISE = CuratedSafetyNotes(
    fa=(
        (
            'پشتت رو ثابت نگه دار؛ مزیت نشسته بودن اینه که نتونی با لگن دمبل رو پرت '
            'کنی.'
        ),
        'بازو رو تا حدود ارتفاع شونه بالا بیار و گردنت رو جلو نده.',
        'مچ و آرنج رو تو یه مسیر راحت نگه دار؛ حرکت نباید تبدیل به پرس بشه.',
        'اگه آخر ست فقط با عقب دادن تنه دمبل بالا میره، ست تموم شده.',
    ),
    en=(
        (
            'Keep your back steady; the point of sitting is to stop the hips from '
            'throwing the dumbbell up.'
        ),
        'Raise the arm to about shoulder height and do not push the neck forward.',
        (
            'Keep the wrist and elbow on a comfortable path; the raise should not '
            'turn into a press.'
        ),
        (
            'If the dumbbell only rises when you lean back at the end of the set, the '
            'set is over.'
        ),
    ),
)

_SHOULDER_BARBELL_FRONT_RAISE = CuratedSafetyNotes(
    fa=(
        'قبل از شروع باسن و شکم رو سفت کن؛ هالتر نباید با تاب لگن از ران جدا بشه.',
        'میله رو با آرنج کمی نرم تا حدود ارتفاع شونه بالا بیار.',
        (
            'شونه رو سمت گوش بالا ننداز؛ اگه کول داره میله رو بلند می‌کنه وزنه رو کم '
            'کن.'
        ),
        'هالتر رو کنترل‌شده برگردون؛ قسمت پایین حرکت رو با سقوط وزنه خراب نکن.',
    ),
    en=(
        (
            'Brace the glutes and abs before starting; the bar should not leave the '
            'thighs through a hip swing.'
        ),
        'Raise the bar to about shoulder height with the elbows slightly soft.',
        (
            'Do not shrug toward the ears; lower the load if the traps are doing the '
            'lifting.'
        ),
        (
            'Return the bar under control instead of ruining the bottom with a free '
            'fall.'
        ),
    ),
)

_SHOULDER_CABLE_ONE_ARM_FRONT_RAISE = CuratedSafetyNotes(
    fa=(
        (
            'جوری بایست که پایین حرکت هم کابل کشش داشته باشه؛ کابل نباید اول تکرار شل '
            'باشه.'
        ),
        (
            'بازو رو جلو و کمی داخل مسیر طبیعی شونه بالا ببر؛ لازم نیست دقیقاً مثل '
            'خط‌کش مستقیم جلوی صورت حرکت کنه.'
        ),
        'تنه رو عقب نده که دسته بالا بره؛ اگه مجبور شدی لم بدی وزنه زیادیه.',
        'برگشت رو آروم کن و اجازه بده سرشانه جلویی تا پایین حرکت زیر فشار بمونه.',
    ),
    en=(
        (
            'Stand so the cable stays loaded at the bottom; it should not be slack at '
            'the start of the rep.'
        ),
        (
            'Raise the arm forward and slightly inward along a natural shoulder path; '
            'it does not need to travel like a ruler directly in front of the face.'
        ),
        (
            'Do not lean back to make the handle rise; if you need to recline, the '
            'load is too heavy.'
        ),
        'Slow the return so the front delt stays loaded down to the bottom.',
    ),
)

_SHOULDER_BAND_ONE_ARM_FRONT_RAISE = CuratedSafetyNotes(
    fa=(
        (
            'کش رو جوری زیر پا یا نقطه اتصال تنظیم کن که از شروع حرکت یه مقدار تنش '
            'داشته باشه.'
        ),
        'بدنت رو عقب نده و با لگن حرکت رو شروع نکن.',
        'دست رو تا ارتفاعی بالا ببر که هنوز شونه راحت و تنه ثابت باشه.',
        'برگشت رو کنترل کن؛ نذار کش دستت رو با ضربه پایین بکشه.',
    ),
    en=(
        (
            'Set the band under the foot or anchor so there is some tension from the '
            'start of the movement.'
        ),
        'Do not lean the body back or start the movement with the hips.',
        (
            'Raise the hand only as high as the shoulder stays comfortable and the '
            'torso stays still.'
        ),
        'Control the return instead of letting the band snap the hand down.',
    ),
)

_SHOULDER_SEATED_DUMBBELL_PRESS = CuratedSafetyNotes(
    fa=(
        (
            'آرنج‌ها رو دقیقاً صاف به بغل باز نکن؛ یه ذره جلوی بدن نگهشون دار تا تو '
            'مسیر طبیعی‌تر شونه پرس کنی.'
        ),
        (
            'پایین حرکت ساعدها تا جای ممکن زیر دمبل بمونن؛ اگه مچ خیلی داخل یا بیرون '
            'افتاده مسیرت رو اصلاح کن.'
        ),
        (
            'شکم رو سفت و دنده‌ها رو پایین نگه دار؛ پرس سرشانه رو با گود کردن کمر '
            'تبدیل به پرس بالاسینه نکن.'
        ),
        (
            'دمبل‌ها رو بالا به هم نکوب؛ تا جایی پرس کن که بازوها بالای سرت پایدار شن '
            'و فشار حفظ بشه.'
        ),
        (
            'عمق رو تا جایی بگیر که شونه راحت باشه؛ پایین‌تر رفتن به هر قیمتی امتیاز '
            'اضافه نداره.'
        ),
    ),
    en=(
        (
            'Do not flare the elbows straight out to the sides; keep them slightly in '
            'front so the press follows a more natural shoulder path.'
        ),
        (
            'Keep the forearms as close as possible to being under the dumbbells at '
            'the bottom; adjust if the wrists fall too far in or out.'
        ),
        (
            'Brace the abs and keep the ribs down; do not turn the shoulder press '
            'into an incline press by overextending the back.'
        ),
        (
            'Do not bang the dumbbells together overhead; press only as far as the '
            'arms stay stable above you and tension remains.'
        ),
        (
            'Use a depth your shoulders can control; going lower at any cost is not '
            'extra credit.'
        ),
    ),
)

_SHOULDER_ALTERNATING_DUMBBELL_PRESS = CuratedSafetyNotes(
    fa=(
        (
            'وقتی یه دست پرس می‌کنه، سمت دیگه بدنت رو نچرخون؛ شکم و لگن باید ثابت '
            'بمونن.'
        ),
        'آرنج رو کمی جلوی بدن نگه دار و دمبل رو بالا توی خط شونه stack کن.',
        'دست پایین رو بی‌کنترل روی شونه رها نکن؛ اون سمت هم باید پایدار بمونه.',
        (
            'اگه بدن با هر تکرار چپ و راست میشه، وزنه برای پرس تک‌دست تمیز زیادی '
            'سنگینه.'
        ),
    ),
    en=(
        (
            'Do not rotate the opposite side of the body while one arm presses; keep '
            'the abs and hips still.'
        ),
        (
            'Keep the elbow slightly in front of the body and stack the dumbbell over '
            'the shoulder at the top.'
        ),
        (
            'Do not let the lowered hand collapse onto the shoulder; that side must '
            'stay stable too.'
        ),
        (
            'If the body shifts side to side on every rep, the load is too heavy for '
            'a clean alternating press.'
        ),
    ),
)

_SHOULDER_SMITH_SEATED_PRESS = CuratedSafetyNotes(
    fa=(
        (
            'نیمکت رو جوری زیر مسیر اسمیت بذار که میله بدون جنگیدن با مسیر دستگاه '
            'جلوی صورت رد بشه و بالای شونه stack بشه.'
        ),
        (
            'آرنج‌ها رو کمی جلوتر از خط شونه نگه دار؛ مجبورشون نکن دقیقاً صاف به '
            'طرفین باز بشن.'
        ),
        (
            'شکم رو سفت کن و باسن رو روی نیمکت نگه دار؛ برای بالا بردن میله کمرت رو '
            'بیش‌ازحد گود نکن.'
        ),
        (
            'پایین حرکت رو تا دامنه‌ای ببر که ساعد و شونه هنوز کنترل خوبی دارن؛ مسیر '
            'ثابت اسمیت رو با زور روی مفصل تحمیل نکن.'
        ),
    ),
    en=(
        (
            'Place the bench under the Smith path so the bar can pass the face '
            'cleanly and stack over the shoulders at the top.'
        ),
        (
            'Keep the elbows slightly in front of the shoulder line instead of '
            'forcing them straight out to the sides.'
        ),
        (
            'Brace the abs and keep the hips on the bench; do not overarch the back '
            'to move the bar.'
        ),
        (
            'Lower only through a range where the forearms and shoulders stay '
            'controlled; do not force the machine’s fixed path onto the joint.'
        ),
    ),
)

_SHOULDER_MILITARY_PRESS = CuratedSafetyNotes(
    fa=(
        (
            'باسن و شکم رو قبل از هر تکرار سفت کن؛ بدن باید ستون حرکت باشه، نه فنر '
            'برای پرت کردن هالتر.'
        ),
        (
            'میله رو نزدیک صورت بالا ببر؛ اول سر یه ذره راه بده، بعد وقتی میله رد شد '
            'سرت رو دوباره زیر میله بیار.'
        ),
        (
            'بالای حرکت میله باید تقریباً روی شونه و وسط پا stack بشه، نه اینکه جلوی '
            'بدنت معلق بمونه.'
        ),
        (
            'اگه برای بالا بردن هالتر باید شدید عقب خم بشی، وزنه زیادیه و حرکت داره '
            'تبدیل به standing incline press میشه.'
        ),
    ),
    en=(
        (
            'Brace the glutes and abs before every rep; the body should be the base, '
            'not a spring for throwing the bar up.'
        ),
        (
            'Keep the bar close to the face; move the head slightly back, then bring '
            'it back under the bar once it clears.'
        ),
        (
            'At the top, the bar should stack roughly over the shoulders and mid-foot '
            'rather than hanging in front of the body.'
        ),
        (
            'If you have to lean far back to raise the bar, the load is too heavy and '
            'the press is becoming a standing incline press.'
        ),
    ),
)

_SHOULDER_ARNOLD_PRESS = CuratedSafetyNotes(
    fa=(
        (
            'چرخش دست رو نرم و همزمان با بالا رفتن انجام بده؛ دمبل رو تو پایین حرکت '
            'با زور نپیچون.'
        ),
        (
            'آرنج‌ها لازم نیست پایین حرکت کامل به هم بچسبن؛ تا جایی جمع کن که شونه '
            'راحت و تحت کنترل بمونه.'
        ),
        (
            'وقتی پرس می‌کنی، دمبل‌ها رو بالا و روی خط شونه ببر؛ کمرت رو برای کامل '
            'کردن تکرار گود نکن.'
        ),
        (
            'آرنولدی با وزنه کمتر ولی مسیر تمیز خیلی بهتر از دمبل سنگینیه که نصف '
            'چرخشش با تقلب انجام میشه.'
        ),
    ),
    en=(
        (
            'Rotate the hands smoothly as the dumbbells rise; do not force the turn '
            'at the bottom.'
        ),
        (
            'The elbows do not need to meet completely at the bottom; bring them in '
            'only as far as the shoulders stay comfortable and controlled.'
        ),
        (
            'As you press, take the dumbbells up over the shoulder line; do not arch '
            'the back to complete the rep.'
        ),
        (
            'A lighter Arnold press with a clean path is better than heavy dumbbells '
            'whose rotation is half completed with cheating.'
        ),
    ),
)

_SHOULDER_CLEAN_AND_PRESS = CuratedSafetyNotes(
    fa=(
        (
            'تو بخش کلین میله رو نزدیک بدن نگه دار؛ از خودت دورش نکن که مجبور شی با '
            'دست جمعش کنی.'
        ),
        (
            'میله رو روی جلوی شونه‌ها catch کن و اول تعادلت رو کامل بگیر، بعد پرس رو '
            'شروع کن.'
        ),
        (
            'کلین رو تبدیل به جلو بازوی هالتر نکن؛ نیرو باید از پا و لگن بیاد و بعد '
            'زیر میله بری.'
        ),
        (
            'تو پرس دنده‌ها رو پایین و شکم رو سفت نگه دار؛ برای رد کردن میله کمرت رو '
            'عقب نشکن.'
        ),
        (
            'اگه catch به‌هم‌ریخته‌ست، همون‌جا تکرار رو reset کن؛ از وضعیت خراب '
            'مستقیم پرس نزن.'
        ),
    ),
    en=(
        (
            'Keep the bar close during the clean; do not let it drift away and then '
            'collect it with the arms.'
        ),
        (
            'Catch the bar on the fronts of the shoulders and regain balance before '
            'starting the press.'
        ),
        (
            'Do not turn the clean into a barbell curl; drive it from the legs and '
            'hips, then get under the bar.'
        ),
        (
            'During the press, keep the ribs down and abs braced; do not break '
            'backward at the waist to clear the bar.'
        ),
        (
            'If the catch is messy, reset the rep there; do not press directly from a '
            'compromised position.'
        ),
    ),
)

_SHOULDER_EZ_BAR_ANTI_GRAVITY_PRESS = CuratedSafetyNotes(
    fa=(
        (
            'سینه و لگنت رو روی نیمکت ثابت نگه دار؛ این نسخه با ثبات تنه معنی داره، '
            'نه با تاب دادن کل بدن.'
        ),
        (
            'میله رو در مسیر کنترل‌شده بین نقطه شروع و سینه یا جلوی شونه حرکت بده؛ '
            'برای چند سانت بیشتر مسیر رو عوض نکن.'
        ),
        (
            'مچ‌ها رو تا جای ممکن خنثی و روی ساعد نگه دار؛ میله رو با خم کردن مچ به '
            'سمت خودت نکش.'
        ),
        (
            'اگه برای جدا کردن یا برگردوندن میله لگن و کمرت حرکت می‌کنن، وزنه زیادیه؛ '
            'تنه باید تکیه‌گاه بمونه.'
        ),
        (
            'پایین آوردن رو آهسته انجام بده و میله رو روی نقطه شروع کنترل کن؛ رها '
            'کردن منفی فشار حرکت رو می‌پرونه.'
        ),
    ),
    en=(
        (
            'Keep the chest and hips supported on the bench; this variation depends '
            'on a stable torso, not a full-body swing.'
        ),
        (
            'Move the bar through a controlled path between the start and the chest '
            'or front-shoulder position; do not change the path for a few extra '
            'centimeters.'
        ),
        (
            'Keep the wrists as neutral as possible and stacked over the forearms; do '
            'not pull the bar toward you by folding the wrists.'
        ),
        (
            'If the hips or lower back move to start or return the bar, the load is '
            'too heavy; the torso should remain the support.'
        ),
        (
            'Lower slowly and control the bar back to its start point; dropping the '
            'eccentric removes useful tension.'
        ),
    ),
)

_SHOULDER_REAR_DELT_FLY = CuratedSafetyNotes(
    fa=(
        (
            'فکر کن بازوهات رو داری به طرفین باز می‌کنی؛ فقط کتف‌ها رو با زور به هم '
            'نچسبون که پشت میانی کل حرکت رو بدزده.'
        ),
        (
            'آرنج یه خم نرم داشته باشه و همون زاویه تقریباً ثابت بمونه؛ حرکت رو تبدیل '
            'به Row نکن.'
        ),
        (
            'بازوها رو بیشتر به طرفین ببر، نه سمت لگن؛ مسیر سمت لگن لت رو بیشتر وارد '
            'بازی می‌کنه.'
        ),
        (
            'وقتی بازو تقریباً هم‌خط تنه شد کافیه؛ برای چند سانت بیشتر شونه رو عقب '
            'نپیچون.'
        ),
    ),
    en=(
        (
            'Think about opening the arms to the sides; do not crush the shoulder '
            'blades together and let the mid-back steal the movement.'
        ),
        (
            'Keep a soft, nearly fixed bend in the elbows so the fly does not become '
            'a row.'
        ),
        (
            'Take the arms more to the sides than toward the hips; the hip path '
            'brings the lats into play more.'
        ),
        (
            'Stop when the arms are roughly in line with the torso; do not twist the '
            'shoulder farther back for a few extra centimeters.'
        ),
    ),
)

_SHOULDER_INCLINE_REAR_LATERAL_RAISE = CuratedSafetyNotes(
    fa=(
        (
            'سینه رو به نیمکت بچسبون؛ اگه برای بالا آوردن دمبل از پد جدا میشی داری '
            'ثبات حرکت رو دور می‌ریزی.'
        ),
        'دمبل‌ها رو به طرفین باز کن، نه عقب سمت لگن.',
        (
            'کتف‌ها می‌تونن حرکت طبیعی داشته باشن، ولی آخر تکرار اونا رو با زور به هم '
            'له نکن.'
        ),
        (
            'وزنه سبک‌تر و بازوی تمیز بهتر از دمبل سنگینیه که حرکت رو تبدیل به Row '
            'می‌کنه.'
        ),
    ),
    en=(
        (
            'Keep the chest against the bench; lifting off the pad to raise the '
            'dumbbells gives away the stability of the setup.'
        ),
        'Open the dumbbells to the sides rather than back toward the hips.',
        (
            'The shoulder blades can move naturally, but do not forcefully crush them '
            'together at the end of the rep.'
        ),
        (
            'A lighter load and clean arm path beat heavy dumbbells that turn the '
            'movement into a row.'
        ),
    ),
)

_SHOULDER_CABLE_CROSSOVER_REVERSE_FLY = CuratedSafetyNotes(
    fa=(
        (
            'دست‌ها رو جلوی بدن کراس کن تا شروع حرکت rear delt کشیده‌تر باشه، ولی '
            'شونه رو بی‌کنترل جلو رها نکن.'
        ),
        'بازوها رو به طرفین باز کن؛ دستگیره‌ها رو سمت لگن نکش.',
        'آرنج‌ها نرم و تقریباً ثابت بمونن تا حرکت تبدیل به Row نشه.',
        (
            'آخر حرکت فقط تا جایی باز کن که rear delt هنوز کار می‌کنه؛ برای دامنه '
            'اضافه کتف‌ها رو با زور به هم نکوب.'
        ),
    ),
    en=(
        (
            'Cross the hands in front of the body for a longer rear-delt start, but '
            'do not let the shoulders collapse forward without control.'
        ),
        (
            'Open the arms to the sides instead of pulling the handles toward the '
            'hips.'
        ),
        (
            'Keep the elbows soft and nearly fixed so the movement does not become a '
            'row.'
        ),
        (
            'Open only as far as the rear delts are still working; do not force the '
            'shoulder blades together for extra range.'
        ),
    ),
)

_SHOULDER_LEVER_SEATED_REVERSE_FLY = CuratedSafetyNotes(
    fa=(
        'ارتفاع صندلی رو جوری تنظیم کن که دستگیره‌ها تقریباً هم‌سطح شونه باشن.',
        (
            'سینه رو روی پد ثابت نگه دار و با بازوها حرکت رو باز کن؛ تنه نباید عقب '
            'بپره.'
        ),
        (
            'به‌جای اینکه فقط کتف‌ها رو به هم فشار بدی، فکر کن آرنج‌ها رو داری از هم '
            'دور و عقب می‌بری.'
        ),
        (
            'برگشت رو کنترل کن و بذار rear delt دوباره کش بیاد؛ استک وزنه رو بین '
            'تکرارها نکوب.'
        ),
    ),
    en=(
        'Set the seat so the handles are roughly level with the shoulders.',
        (
            'Keep the chest on the pad and open the movement with the arms; the torso '
            'should not jump backward.'
        ),
        (
            'Instead of only squeezing the shoulder blades together, think about '
            'moving the elbows apart and back.'
        ),
        (
            'Control the return and let the rear delts lengthen again; do not slam '
            'the stack between reps.'
        ),
    ),
)

_SHOULDER_BARBELL_REAR_DELT_RAISE = CuratedSafetyNotes(
    fa=(
        (
            'از لگن خم شو و زاویه تنه رو ثابت نگه دار؛ بالا و پایین شدن تنه نباید '
            'وزنه رو جابه‌جا کنه.'
        ),
        (
            'آرنج‌ها رو به طرفین و عقب هدایت کن، نه اینکه میله رو با جلو بازو جمع '
            'کنی.'
        ),
        'تمرکز روی باز شدن بازوهاست؛ کتف‌ها رو با زور به هم قفل نکن.',
        'وزنه سبک نگه دار؛ rear delt raise با هالتر جای ego lifting نیست.',
    ),
    en=(
        (
            'Hinge from the hips and keep the torso angle steady; the torso should '
            'not move the weight up and down.'
        ),
        (
            'Guide the elbows out and back instead of gathering the bar with the '
            'biceps.'
        ),
        (
            'Focus on opening the arms; do not force the shoulder blades into a hard '
            'squeeze.'
        ),
        (
            'Keep the load light; a barbell rear-delt raise is not a place for ego '
            'lifting.'
        ),
    ),
)

_SHOULDER_DUMBBELL_REAR_DELT_ROW = CuratedSafetyNotes(
    fa=(
        (
            'آرنج‌ها رو باز نگه دار و به طرف بالا و بیرون بکش؛ اگه آرنج بچسبه به بدن '
            'حرکت بیشتر لت میشه.'
        ),
        'دمبل‌ها رو سمت بالای دنده‌ها بکش، نه سمت لگن.',
        (
            'گردنت رو خنثی و تنه رو ثابت نگه دار؛ برای بالا آوردن دمبل‌ها خودتو تکون '
            'نده.'
        ),
        'بالا rear delt رو جمع کن ولی شونه‌هاتو سمت گوش بالا نکش.',
    ),
    en=(
        (
            'Keep the elbows wide and pull them up and out; if they stay close to the '
            'body, the movement becomes more lat-dominant.'
        ),
        'Pull the dumbbells toward the upper ribs rather than toward the hips.',
        (
            'Keep the neck neutral and torso steady; do not move yourself to lift the '
            'dumbbells.'
        ),
        (
            'Contract the rear delts at the top without hiking the shoulders toward '
            'the ears.'
        ),
    ),
)

_SHOULDER_CABLE_REAR_DELT_ROW_WITH_ROPE = CuratedSafetyNotes(
    fa=(
        (
            'طناب رو سمت بالای سینه و صورت بکش، نه پایین شکم؛ مسیر پایین حرکت رو '
            'تبدیل به Row لت می‌کنه.'
        ),
        'آرنج‌ها رو باز و دور از بدن نگه دار تا پشت شونه واقعاً وارد کار بشه.',
        (
            'آخر حرکت طناب رو باز کن، ولی کمر رو عقب نده که چند سانت دامنه تقلبی '
            'بسازی.'
        ),
        'شونه‌ها رو بالا نکش؛ آرنج باید حرکت رو هدایت کنه.',
    ),
    en=(
        (
            'Pull the rope toward the upper chest and face, not the lower abdomen; a '
            'low path turns the movement into more of a lat row.'
        ),
        (
            'Keep the elbows wide and away from the body so the rear shoulder can do '
            'its share.'
        ),
        (
            'Separate the rope ends at the finish, but do not lean the back away to '
            'create fake range.'
        ),
        'Do not shrug; let the elbows lead the movement.',
    ),
)

_SHOULDER_BAND_STANDING_REAR_DELT_ROW = CuratedSafetyNotes(
    fa=(
        (
            'از شروع حرکت روی کش تنش داشته باش؛ کش شل یعنی اول تکرار تقریباً کاری '
            'انجام نمیدی.'
        ),
        'آرنج‌ها رو باز نگه دار و کش رو سمت بالای سینه بکش.',
        (
            'تنه رو عقب پرت نکن؛ اگه برای کشیدن باند باید کل بدن حرکت کنه مقاومت '
            'زیادیه.'
        ),
        'برگشت رو کنترل کن و نذار کش دست‌هاتو با ضربه جلو بکشه.',
    ),
    en=(
        (
            'Keep tension on the band from the start; a slack band means the first '
            'part of the rep does almost nothing.'
        ),
        'Keep the elbows wide and pull the band toward the upper chest.',
        (
            'Do not throw the torso backward; if the whole body has to move to pull '
            'the band, the resistance is too high.'
        ),
        'Control the return instead of letting the band snap the hands forward.',
    ),
)

_SHOULDER_BAND_BENT_OVER_REAR_LATERAL_RAISE = CuratedSafetyNotes(
    fa=(
        'از لگن خم شو و کمر رو ثابت نگه دار؛ زاویه تنه نباید هر تکرار عوض بشه.',
        'بازوها رو به طرفین باز کن و آرنج‌ها رو نرم نگه دار.',
        'کش رو جوری تنظیم کن که حتی پایین حرکت هم کمی تنش داشته باشه.',
        'بالا شونه‌هات رو سمت گوش جمع نکن؛ فشار باید پشت شونه بمونه.',
    ),
    en=(
        (
            'Hinge from the hips and keep the back steady; the torso angle should not '
            'change on every rep.'
        ),
        'Open the arms to the sides and keep the elbows soft.',
        (
            'Set the band so there is still some tension at the bottom of the '
            'movement.'
        ),
        (
            'Do not gather the shoulders toward the ears at the top; keep the effort '
            'in the rear delts.'
        ),
    ),
)

_SHOULDER_FACE_PULL = CuratedSafetyNotes(
    fa=(
        (
            'طناب رو سمت ابروها و بالای صورت بکش؛ اگه داری سمت شکم می‌کشی دیگه Face '
            'Pull نیست.'
        ),
        'آرنج‌ها رو باز نگه دار و آخر حرکت دو سر طناب رو دو طرف صورت جدا کن.',
        (
            'فقط Row نزن؛ آخر حرکت یه چرخش بیرونی نرم بده تا دست‌ها عقب‌تر از آرنج‌ها '
            'نریزن.'
        ),
        (
            'وزنه سبک‌تر بردار و حرکت رو تمیز نگه دار؛ Face Pull سنگین خیلی زود تبدیل '
            'به کشیدن طناب با کل بدن میشه.'
        ),
    ),
    en=(
        (
            'Pull the rope toward the eyebrows and upper face; if it travels toward '
            'the abdomen, it is no longer a face pull.'
        ),
        (
            'Keep the elbows wide and separate the rope ends to either side of the '
            'face at the finish.'
        ),
        (
            'Do not only row; add a smooth external rotation at the end so the hands '
            'do not collapse behind the elbows.'
        ),
        (
            'Use a lighter load and keep the movement clean; a heavy face pull '
            'quickly becomes a full-body rope pull.'
        ),
    ),
)

_SHOULDER_BATTLING_ROPES = CuratedSafetyNotes(
    fa=(
        (
            'زانوها نرم، شکم سفت و تنه ثابت؛ موج طناب نباید با بالا و پایین پریدن کل '
            'بدن ساخته بشه.'
        ),
        (
            'طناب رو مرگ‌وار فشار نده؛ گریپ زیادی سفت ساعد رو زودتر از سرشونه خسته '
            'می‌کنه.'
        ),
        'شونه‌ها رو تا گوش بالا نگه ندار؛ موج رو با ریتم دست و بازو بساز.',
        (
            'وقتی موج‌ها نصفه و نامنظم شدن ست رو تموم کن؛ کیفیت موج از ادامه دادن با '
            'فرم خراب مهم‌تره.'
        ),
    ),
    en=(
        (
            'Keep the knees soft, abs braced, and torso steady; the waves should not '
            'come from bouncing the whole body.'
        ),
        (
            'Do not crush the ropes with an excessively hard grip; your forearms '
            'should not fail before your shoulders can work.'
        ),
        (
            'Do not hold the shoulders up by the ears; create the waves with the '
            'rhythm of the hands and arms.'
        ),
        (
            'End the set when the waves become short and uneven; wave quality matters '
            'more than continuing with broken form.'
        ),
    ),
)

_SHOULDER_BEHIND_NECK_PRESS = CuratedSafetyNotes(
    fa=(
        (
            'این حرکت فقط وقتی معنی داره که بدون زور بتونی شونه‌ت رو توی این موقعیت '
            'باز و چرخیده نگه داری؛ کمبود موبیلیتی رو با وزنه جبران نکن.'
        ),
        (
            'میله رو فقط تا دامنه‌ای پایین بیار که شونه کاملاً راحت باشه؛ لازم نیست '
            'برای لمس پشت گردن یا کول زور بزنی.'
        ),
        (
            'گریپ خیلی جمع نکن و مچ‌ها رو زیر میله نگه دار؛ دست جمع نیاز شونه به چرخش '
            'بیرونی رو بیشتر می‌کنه.'
        ),
        (
            'شکم رو سفت و دنده‌ها رو پایین نگه دار؛ برای رد کردن میله گردنت رو جلو '
            'نده و کمرت رو بیش‌ازحد گود نکن.'
        ),
        (
            'اگه جلوی شونه نیشگون می‌گیره یا برای رسیدن به دامنه باید بدن رو زور بدی، '
            'پرس از جلو انتخاب منطقی‌تریه.'
        ),
    ),
    en=(
        (
            'This variation makes sense only if you can hold the shoulder open and '
            'rotated in this position without forcing it; do not use weight to '
            'compensate for limited mobility.'
        ),
        (
            'Lower the bar only through a range where the shoulder stays completely '
            'comfortable; do not force it to touch the back of the neck or traps.'
        ),
        (
            'Do not use an overly close grip, and keep the wrists under the bar; a '
            'close grip demands more external rotation from the shoulders.'
        ),
        (
            'Brace the abs and keep the ribs down; do not reach the neck forward or '
            'overarch the back to clear the bar.'
        ),
        (
            'If the front of the shoulder pinches or you have to force the position, '
            'a front-of-neck press is the more sensible choice.'
        ),
    ),
)

_SHOULDER_SEATED_CABLE_ROPE_LAT_PULLDOWN = CuratedSafetyNotes(
    fa=(
        (
            'ران‌هات رو زیر پد فیکس کن و کابل رو از همون اول تحت کشش نگه دار؛ وقتی '
            'صندلی ثابت باشه شونه کمتر مجبور میشه حرکت رو جبران کنه.'
        ),
        (
            'طناب رو به بالای سینه بکش و آرنج‌ها رو پایین و عقب هدایت کن؛ دسته رو با '
            'مچ نکش.'
        ),
        (
            'بالا رفتن طناب رو کامل و کنترل‌شده انجام بده تا سرشانه و لت در شروع '
            'تکرار زیر کشش باشن، ولی شونه رو بی‌اختیار بالا ننداز.'
        ),
        (
            'تنه رو تقریباً ثابت نگه دار و طناب رو پشت گردن نبر؛ اگه برای کشیدن بدن '
            'عقب می‌ره، وزنه سنگینه.'
        ),
    ),
    en=(
        (
            'Secure the thighs under the pad and keep the cable loaded from the '
            'start; a stable seat keeps the shoulders from compensating for the pull.'
        ),
        (
            'Pull the rope toward the upper chest and guide the elbows down and back; '
            'do not pull the handle with the wrists.'
        ),
        (
            'Allow a full, controlled return so the shoulders and lats are loaded at '
            'the start of the next rep, without shrugging uncontrollably.'
        ),
        (
            'Keep the torso almost still and do not pull the rope behind the neck; if '
            'you lean back to move it, the load is too heavy.'
        ),
    ),
)

_SHOULDER_SEATED_BARBELL_OVERHEAD_PRESS = CuratedSafetyNotes(
    fa=(
        (
            'قبل از ست قلاب‌ها و پایه‌های رک رو چک کن؛ توی پرس نشسته مسیر میله باید '
            'از جلوی صورت رد بشه، نه اینکه به سر و گردن نزدیک بشه.'
        ),
        'آرنج‌ها رو کمی جلوتر از خط شونه نگه دار و مچ‌ها رو روی ساعد stack کن.',
        (
            'دنده‌ها پایین و شکم سفت؛ برای رد کردن میله کمرت رو از پشتی نیمکت جدا نکن '
            'و بیش‌ازحد گود نکن.'
        ),
        (
            'میله رو تا دامنه‌ای پایین بیار که شونه راحت و کنترل‌شده بمونه، بعد برگشت '
            'رو آهسته انجام بده.'
        ),
        (
            'بعد از آخرین تکرار اول میله رو کامل روی قلاب‌ها بنشون، بعد از رک خارج '
            'شو.'
        ),
    ),
    en=(
        (
            'Check the rack hooks and supports before the set; in a seated press the '
            'bar should pass in front of the face, not close to the head and neck.'
        ),
        (
            'Keep the elbows slightly in front of the shoulder line and stack the '
            'wrists over the forearms.'
        ),
        (
            'Keep the ribs down and abs braced; do not lift away from the bench or '
            'overarch the back to clear the bar.'
        ),
        (
            'Lower the bar only through a range where the shoulder stays comfortable '
            'and controlled, then return slowly.'
        ),
        (
            'After the last rep, seat the bar fully on the hooks before moving out of '
            'the rack.'
        ),
    ),
)

_SHOULDER_WORKOUT_COMPILATION = CuratedSafetyNotes(
    fa=(
        (
            'این ویدیو چند حرکت جدا داره؛ قبل از هر ست مشخص کن نشر، پرس یا نسخه‌ای که '
            'می‌خوای اجرا کنی کدومه.'
        ),
        (
            'فرم یک حرکت رو به حرکت بعدی تعمیم نده؛ مسیر آرنج، گریپ و دامنه هر بخش '
            'فرق می‌کنه.'
        ),
        (
            'اگه نیمکت، زاویه بدن یا وضعیت دمبل عوض شد، وزنه و setup رو دوباره تنظیم '
            'کن؛ با تنظیم قبلی کورکورانه ادامه نده.'
        ),
        (
            'فریم هایلایت‌شده فقط عضله هدف رو نشان می‌ده و جای ویدیوی کامل رو '
            'نمی‌گیره؛ بخش مبهم رو تقلید نکن.'
        ),
    ),
    en=(
        (
            'This video contains several separate movements; identify whether you are '
            'doing a raise, press, or another variation before each set.'
        ),
        (
            "Do not carry one movement's form into the next; the elbow path, grip, "
            'and range differ between sections.'
        ),
        (
            'If the bench, body angle, or dumbbell position changes, reset the load '
            'and setup instead of continuing blindly.'
        ),
        (
            'The highlighted frame shows the target muscle but does not replace the '
            'full video; do not imitate an unclear section.'
        ),
    ),
)

_SHOULDER_STANDING_DUMBBELL_PRESS = CuratedSafetyNotes(
    fa=(
        (
            'پاها رو محکم و لگن رو خنثی نگه دار؛ پرس ایستاده نباید با عقب دادن لگن و '
            'گود کردن کمر جبران بشه.'
        ),
        (
            'آرنج‌ها رو کمی جلوی بدن نگه دار و دمبل‌ها رو در مسیر طبیعی شونه بالا '
            'ببر.'
        ),
        (
            'مچ‌ها رو روی ساعد stack کن و دمبل‌ها رو بالای شونه پایدار کن، نه جلوتر '
            'از بدنت.'
        ),
        (
            'اگه برای تمام کردن تکرار زانوها خم می‌شن یا بدن می‌پیچه، وزنه برای پرس '
            'تمیز سنگینه.'
        ),
        (
            'پایین آوردن رو کنترل کن و قبل از شروع تکرار بعدی اجازه بده هر دو شونه '
            'دوباره پایدار بشن.'
        ),
    ),
    en=(
        (
            'Keep the feet firm and pelvis neutral; do not compensate for the '
            'standing press by pushing the hips forward or arching the back.'
        ),
        (
            'Keep the elbows slightly in front of the body and raise the dumbbells '
            'along a natural shoulder path.'
        ),
        (
            'Stack the wrists over the forearms and stabilize the dumbbells over the '
            'shoulders rather than in front of the body.'
        ),
        (
            'If the knees dip or the body twists to finish a rep, the load is too '
            'heavy for a clean press.'
        ),
        (
            'Control the descent and let both shoulders become stable again before '
            'starting the next rep.'
        ),
    ),
)

_SHOULDER_BENCH_SUPPORTED_DUMBBELL_LATERAL_RAISE = CuratedSafetyNotes(
    fa=(
        (
            'سینه و شکمت رو به نیمکت تکیه بده تا لگن و کمر نتونن دمبل رو پرت کنن؛ اگه '
            'از پد جدا میشی وزنه زیاده.'
        ),
        (
            'آرنج‌ها رو کمی جلو و بیرون هدایت کن و دست‌ها رو با مسیر طبیعی شونه بالا '
            'بیار.'
        ),
        (
            'شونه‌ها رو سمت گوش نکش؛ کمی حرکت طبیعی کتف اشکال نداره، ولی شراگ نباید '
            'رهبر حرکت بشه.'
        ),
        (
            'در پایین حرکت عجله نکن و دمبل‌ها رو آزاد رها نکن؛ برگشت آهسته فشار '
            'سرشانه کناری رو نگه می‌داره.'
        ),
    ),
    en=(
        (
            'Keep the chest and abdomen supported on the bench so the hips and back '
            'cannot throw the dumbbells; if you lift off the pad, the load is too '
            'heavy.'
        ),
        (
            'Guide the elbows slightly forward and out, bringing the hands up along a '
            'natural shoulder path.'
        ),
        (
            'Do not pull the shoulders toward the ears; a little natural scapular '
            'movement is fine, but the shrug should not lead.'
        ),
        (
            'Do not rush the bottom or release the dumbbells; a slow return keeps the '
            'lateral delt loaded.'
        ),
    ),
)

_SHOULDER_COMPILATION_BENT_OVER_FRONT_RAISE = CuratedSafetyNotes(
    fa=(
        (
            'این ویدیو فریم‌های متفاوت از حرکت‌های سرشانه نشون می‌ده؛ قبل از ست مشخص '
            'کن واقعاً کدوم نسخه رو اجرا می‌کنی.'
        ),
        (
            'در فریم خم، زاویه تنه رو ثابت نگه دار و دمبل رو با تاب کمر بالا نبر؛ '
            'حرکت باید از شونه بیاد.'
        ),
        (
            'آرنج‌ها رو نرم نگه دار و بازوها رو در مسیر همون نسخه هدایت کن؛ مچ نباید '
            'حرکت رو بکشه.'
        ),
        (
            'اگه برای رسیدن به دامنه باید تنه رو بالا بیاری یا چند حرکت مختلف رو قاطی '
            'کنی، وزنه و دامنه مناسب نیست.'
        ),
    ),
    en=(
        (
            'This video shows different shoulder-movement frames; identify which '
            'variation you are actually doing before the set.'
        ),
        (
            'In the bent-over frame, hold the torso angle steady and do not swing the '
            'dumbbells with the back; the movement should come from the shoulder.'
        ),
        (
            'Keep the elbows soft and guide the arms along the path of that '
            'variation; the wrists should not pull the movement.'
        ),
        (
            'If you have to raise the torso to reach the range or mix several '
            'movements together, the load and range are not appropriate.'
        ),
    ),
)

CURATED_SHOULDER_SAFETY_NOTES: dict[str, CuratedSafetyNotes] = {
    'dumbbell-lateral-raise': _SHOULDER_DUMBBELL_LATERAL_RAISE,
    'fedb-0028-barbell-clean-and-press': _SHOULDER_CLEAN_AND_PRESS,
    'fedb-0041-barbell-front-raise': _SHOULDER_BARBELL_FRONT_RAISE,
    'fedb-0075-barbell-rear-delt-raise': _SHOULDER_BARBELL_REAR_DELT_RAISE,
    'fedb-0123-barbell-wide-grip-upright-row': _SHOULDER_BARBELL_WIDE_GRIP_UPRIGHT_ROW,
    'fedb-0128-battling-ropes': _SHOULDER_BATTLING_ROPES,
    'fedb-0154-cable-crossover-reverse-fly': _SHOULDER_CABLE_CROSSOVER_REVERSE_FLY,
    'fedb-0162-cable-one-arm-front-raise': _SHOULDER_CABLE_ONE_ARM_FRONT_RAISE,
    'fedb-0178-cable-lateral-raise': _SHOULDER_CABLE_LATERAL_RAISE,
    'fedb-0192-cable-one-arm-lateral-raise': _SHOULDER_ONE_ARM_CABLE_LATERAL_RAISE,
    'fedb-0203-cable-rear-delt-row-with-rope': _SHOULDER_CABLE_REAR_DELT_ROW_WITH_ROPE,
    'fedb-0289-seated-dumbbell-shoulder-press': _SHOULDER_SEATED_DUMBBELL_PRESS,
    'fedb-0310-dumbbell-front-raise': _SHOULDER_DUMBBELL_FRONT_RAISE,
    'fedb-0326-dumbbell-incline-rear-lateral-raise': _SHOULDER_INCLINE_REAR_LATERAL_RAISE,
    'fedb-0332-dumbbell-iron-cross': _SHOULDER_IRON_CROSS,
    'fedb-0334-dumbbell-lateral-raise': _SHOULDER_DUMBBELL_LATERAL_RAISE,
    'fedb-0355-dumbbell-one-arm-lateral-raise': _SHOULDER_ONE_ARM_DUMBBELL_LATERAL_RAISE,
    'fedb-0361-dumbbell-alternating-shoulder-press': _SHOULDER_ALTERNATING_DUMBBELL_PRESS,
    'fedb-0377-dumbbell-rear-delt-row': _SHOULDER_DUMBBELL_REAR_DELT_ROW,
    'fedb-0392-dumbbell-seated-front-raise': _SHOULDER_SEATED_DUMBBELL_FRONT_RAISE,
    'fedb-0396-dumbbell-seated-lateral-raise': _SHOULDER_SEATED_DUMBBELL_LATERAL_RAISE,
    'fedb-0437-dumbbell-upright-row': _SHOULDER_DUMBBELL_UPRIGHT_ROW,
    'fedb-0445-ez-barbell-anti-gravity-press': _SHOULDER_EZ_BAR_ANTI_GRAVITY_PRESS,
    'fedb-0553-military-press': _SHOULDER_MILITARY_PRESS,
    'fedb-0584-lever-lateral-raise': _SHOULDER_LEVER_LATERAL_RAISE,
    'fedb-0602-lever-seated-reverse-fly': _SHOULDER_LEVER_SEATED_REVERSE_FLY,
    'fedb-0765-smith-seated-shoulder-press': _SHOULDER_SMITH_SEATED_PRESS,
    'fedb-1017-band-one-arm-front-raise': _SHOULDER_BAND_ONE_ARM_FRONT_RAISE,
    'fedb-1022-band-standing-rear-delt-row': _SHOULDER_BAND_STANDING_REAR_DELT_ROW,
    'fedb-2137-dumbbell-arnold-press': _SHOULDER_ARNOLD_PRESS,
    (
        'fedb-drv-band-bent-over-rear-lateral-raise-band-bent-over-rear-lateral-raise'
    ): _SHOULDER_BAND_BENT_OVER_REAR_LATERAL_RAISE,
    (
        'fedb-drv-barbell-seated-behind-head-military-press-barbell-seated-behind-the-neck-press'
    ): _SHOULDER_BEHIND_NECK_PRESS,
    'face-pull': _SHOULDER_FACE_PULL,
    'owner-2f6026f53abb-seated-cable-rope-lat-pulldown': _SHOULDER_SEATED_CABLE_ROPE_LAT_PULLDOWN,
    'owner-3a30c79d77aa-kneeling-face-pull': _SHOULDER_FACE_PULL,
    'owner-43ec8f18aa72-seated-barbell-overhead-press': _SHOULDER_SEATED_BARBELL_OVERHEAD_PRESS,
    'owner-6ade15ad4ded-shoulder-workout-compilation': _SHOULDER_WORKOUT_COMPILATION,
    'owner-6b7757e85637-seated-cable-rope-face-pull': _SHOULDER_FACE_PULL,
    'owner-7918dc7f8d77-standing-dumbbell-shoulder-press': _SHOULDER_STANDING_DUMBBELL_PRESS,
    'owner-bf2134aafcda-neutral-grip-dumbbell-front-raise': _SHOULDER_DUMBBELL_FRONT_RAISE,
    'owner-dc4ac8c89e95-dumbbell-bent-over-rear-delt-fly': _SHOULDER_REAR_DELT_FLY,
    (
        'owner-e40dc9bd636b-dumbbell-incline-rear-lateral-raise'
    ): _SHOULDER_COMPILATION_BENT_OVER_FRONT_RAISE,
    (
        'owner-f9d1558c4263-bench-supported-dumbbell-lateral-raise'
    ): _SHOULDER_BENCH_SUPPORTED_DUMBBELL_LATERAL_RAISE,
    'rear-delt-fly': _SHOULDER_REAR_DELT_FLY,
    'smith-machine-shoulder-press': _SHOULDER_SMITH_SEATED_PRESS,
}

CURATED_SAFETY_NOTES.update(CURATED_SHOULDER_SAFETY_NOTES)


def get_curated_safety_notes(slug: str) -> CuratedSafetyNotes | None:
    return CURATED_SAFETY_NOTES.get(slug)
