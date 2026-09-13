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


def get_curated_safety_notes(slug: str) -> CuratedSafetyNotes | None:
    return CURATED_SAFETY_NOTES.get(slug)
