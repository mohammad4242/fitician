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


def get_curated_safety_notes(slug: str) -> CuratedSafetyNotes | None:
    return CURATED_SAFETY_NOTES.get(slug)
